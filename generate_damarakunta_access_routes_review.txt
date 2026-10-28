
from pathlib import Path
import heapq
import math

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.features import rasterize
from shapely.geometry import LineString, Point

BASE = Path(r"D:\Telangana_Rural_Project\Siddipet\Damarakunta")
REF = BASE / "reference"
ALIGNED = BASE / "aligned"
RESULTS = BASE / "results"

FACILITIES_FILE = REF / "damarakunta_priority_facilities.gpkg"
ROADS_FILE = REF / "tgrac_road_network.gpkg"
COST_FILE = ALIGNED / "damarakunta_cost_surface_10m.tif"
PROHIBITED_FILE = ALIGNED / "damarakunta_prohibited_mask_10m.tif"

ROUTES_FILE = RESULTS / "damarakunta_least_cost_access_routes.gpkg"
CSV_FILE = RESULTS / "damarakunta_least_cost_access_routes.csv"

CRS = "EPSG:32644"
MAX_START_SNAP_M = 100.0
MAX_ROUTE_CELLS = 183370


def nearest_valid_cell(point, valid, transform, max_distance_m):
    """Find a nearby traversable raster cell for a facility point."""
    row, col = rasterio.transform.rowcol(
        transform, point.x, point.y
    )

    height, width = valid.shape
    candidates = []

    max_cells = int(math.ceil(max_distance_m / 10.0))

    for rr in range(max(0, row - max_cells), min(height, row + max_cells + 1)):
        for cc in range(max(0, col - max_cells), min(width, col + max_cells + 1)):
            if not valid[rr, cc]:
                continue

            x, y = rasterio.transform.xy(transform, rr, cc, offset="center")
            distance = math.hypot(x - point.x, y - point.y)

            if distance <= max_distance_m:
                candidates.append((distance, rr, cc))

    if not candidates:
        return None

    candidates.sort()
    distance, rr, cc = candidates[0]
    return rr, cc, distance


def dijkstra_to_road(start, traversable, cost, road_cells, transform):
    """Find a minimum accumulated-cost path to any existing road cell."""
    height, width = traversable.shape
    sr, sc = start

    if road_cells[sr, sc]:
        return [(sr, sc)], 0.0

    distances = np.full((height, width), np.inf, dtype=np.float64)
    previous = {}
    distances[sr, sc] = 0.0
    queue = [(0.0, sr, sc)]

    neighbors = [
        (-1, 0), (1, 0), (0, -1), (0, 1),
        (-1, -1), (-1, 1), (1, -1), (1, 1),
    ]

    visited_count = 0

    while queue:
        current_cost, r, c = heapq.heappop(queue)

        if current_cost != distances[r, c]:
            continue

        visited_count += 1
        if visited_count > MAX_ROUTE_CELLS:
            break

        if road_cells[r, c]:
            path = [(r, c)]
            current = (r, c)

            while current != (sr, sc):
                current = previous[current]
                path.append(current)

            path.reverse()
            return path, current_cost

        for dr, dc in neighbors:
            nr, nc = r + dr, c + dc

            if not (0 <= nr < height and 0 <= nc < width):
                continue
            if not traversable[nr, nc]:
                continue

            # Avoid diagonal movement between two blocked side cells.
            if dr != 0 and dc != 0:
                if not traversable[r + dr, c] or not traversable[r, c + dc]:
                    continue

            step_distance = math.hypot(
                dr * transform.a, dc * transform.e
            )
            step_cost = step_distance * (cost[r, c] + cost[nr, nc]) / 2.0
            new_cost = current_cost + step_cost

            if new_cost < distances[nr, nc]:
                distances[nr, nc] = new_cost
                previous[(nr, nc)] = (r, c)
                heapq.heappush(queue, (new_cost, nr, nc))

    return None, None


def main():
    RESULTS.mkdir(parents=True, exist_ok=True)

    required = [
        FACILITIES_FILE, ROADS_FILE, COST_FILE, PROHIBITED_FILE
    ]
    for path in required:
        if not path.exists():
            raise FileNotFoundError(path)

    if ROUTES_FILE.exists() or CSV_FILE.exists():
        raise FileExistsError(
            "One or both output files already exist. Review or rename "
            "them before running again; existing results will not be overwritten."
        )

    facilities = gpd.read_file(FACILITIES_FILE).to_crs(CRS)
    roads = gpd.read_file(ROADS_FILE).to_crs(CRS)

    with rasterio.open(COST_FILE) as src:
        cost = src.read(1).astype(np.float64)
        transform = src.transform
        crs = src.crs
        nodata = src.nodata
        profile = src.profile.copy()

    with rasterio.open(PROHIBITED_FILE) as src:
        prohibited = src.read(1)
        if (
            src.crs != crs
            or src.width != cost.shape[1]
            or src.height != cost.shape[0]
            or src.transform != transform
        ):
            raise ValueError("Prohibited mask does not match cost grid.")

    if crs.to_string() != CRS:
        raise ValueError(f"Unexpected cost CRS: {crs}")

    valid = np.isfinite(cost)
    if nodata is not None:
        valid &= cost != nodata
    valid &= cost > 0
    valid &= prohibited == 0

    # Rasterize existing road lines on the same grid.
    road_shapes = [
        (geom, 1)
        for geom in roads.geometry
        if geom is not None and not geom.is_empty
        and geom.geom_type in ("LineString", "MultiLineString")
    ]

    road_cells = rasterize(
        road_shapes,
        out_shape=cost.shape,
        transform=transform,
        fill=0,
        all_touched=True,
        dtype="uint8",
    ).astype(bool)

    road_cells &= valid

    if not road_cells.any():
        raise ValueError(
            "No existing road cells overlap traversable cost-surface cells. "
            "Check road and raster alignment."
        )

    print("Traversable cells:", int(valid.sum()))
    print("Road target cells:", int(road_cells.sum()))
    print("Facilities:", len(facilities))

    route_records = []
    report_rows = []

    for _, facility in facilities.iterrows():
        point = facility.geometry
        label = facility["facility_name"]

        print(f"\nProcessing: {label}")

        if point is None or point.is_empty or point.geom_type != "Point":
            print("  SKIPPED: invalid facility point.")
            report_rows.append({
                "facility_id": facility["facility_id"],
                "facility_name": label,
                "status": "INVALID_FACILITY_GEOMETRY",
            })
            continue

        snapped = nearest_valid_cell(
            point, valid, transform, MAX_START_SNAP_M
        )

        if snapped is None:
            print("  NO ROUTE: no traversable cell within snap limit.")
            report_rows.append({
                "facility_id": facility["facility_id"],
                "facility_name": label,
                "status": "NO_VALID_START_CELL_WITHIN_100M",
            })
            continue

        sr, sc, snap_distance = snapped
        path, accumulated_cost = dijkstra_to_road(
            (sr, sc), valid, cost, road_cells, transform
        )

        if path is None:
            print("  NO ROUTE: no traversable path reached an existing road.")
            report_rows.append({
                "facility_id": facility["facility_id"],
                "facility_name": label,
                "status": "NO_TRAVERSABLE_PATH_FOUND",
                "start_snap_distance_m": round(snap_distance, 2),
            })
            continue

        coords = [
            rasterio.transform.xy(transform, r, c, offset="center")
            for r, c in path
        ]

        start_cell_point = Point(coords[0])
        road_endpoint = Point(coords[-1])
        path_geom = LineString(coords) if len(coords) >= 2 else None

        raster_path_length = 0.0
        for (r1, c1), (r2, c2) in zip(path[:-1], path[1:]):
            raster_path_length += math.hypot(
                (r2 - r1) * transform.e,
                (c2 - c1) * transform.a,
            )

        # A one-cell route is already on the rasterized road network.
        if path_geom is not None:
            route_records.append({
                "facility_id": str(facility["facility_id"]),
                "facility_name": label,
                "facility_type": facility["facility_type"],
                "start_snap_m": round(snap_distance, 2),
                "path_length_m": round(raster_path_length, 2),
                "accumulated_cost": round(accumulated_cost, 2),
                "path_cells": len(path),
                "geometry": path_geom,
            })

        report_rows.append({
            "facility_id": str(facility["facility_id"]),
            "facility_name": label,
            "facility_type": facility["facility_type"],
            "status": "ROUTE_FOUND",
            "start_snap_distance_m": round(snap_distance, 2),
            "facility_to_start_cell_m": round(point.distance(start_cell_point), 2),
            "path_length_m": round(raster_path_length, 2),
            "accumulated_cost": round(accumulated_cost, 2),
            "path_cells": len(path),
            "road_endpoint_easting": round(road_endpoint.x, 2),
            "road_endpoint_northing": round(road_endpoint.y, 2),
        })

        print("  Start-cell snap distance (m):", round(snap_distance, 2))
        print("  Raster path length (m):", round(raster_path_length, 2))
        print("  Accumulated cost:", round(accumulated_cost, 2))

    if route_records:
        route_gdf = gpd.GeoDataFrame(
            route_records, geometry="geometry", crs=CRS
        )
        route_gdf.to_file(
            ROUTES_FILE, layer="access_routes", driver="GPKG"
        )

    report = pd.DataFrame(report_rows)
    report.to_csv(CSV_FILE, index=False)

    print("\n" + "=" * 65)
    print("ROUTING SUMMARY")
    print("=" * 65)
    print(report.to_string(index=False))
    print("\nCSV report:", CSV_FILE)
    if route_records:
        print("Route GeoPackage:", ROUTES_FILE)
    else:
        print("No route GeoPackage created because no valid paths were found.")

    print(
        "\nInterpretation: routes are raster-based planning candidates. "
        "They need map inspection and validation before being treated as "
        "new road proposals. The 10 m grid limits positional precision."
    )


if __name__ == "__main__":
    main()
