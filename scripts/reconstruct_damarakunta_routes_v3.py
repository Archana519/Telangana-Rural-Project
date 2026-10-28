
from pathlib import Path
import heapq
import math

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.features import rasterize
from shapely.geometry import LineString, Point

# Damarakunta rural access-route reconstruction V3
# Generates planning candidates, not construction-ready roads.

BASE = Path(r"D:\Telangana_Rural_Project\Siddipet\Damarakunta")
REF = BASE / "reference"
ALIGNED = BASE / "aligned"
RESULTS = BASE / "results"

FACILITIES_PATH = REF / "damarakunta_priority_facilities.gpkg"
ROADS_PATH = REF / "tgrac_road_network.gpkg"
COST_PATH = ALIGNED / "damarakunta_cost_surface_10m.tif"
BLOCKED_PATH = ALIGNED / "damarakunta_prohibited_mask_10m.tif"
WORLDCOVER_PATH = ALIGNED / "damarakunta_worldcover_10m.tif"
SLOPE_PATH = ALIGNED / "damarakunta_slope_10m.tif"

OUT_GPKG = RESULTS / "damarakunta_routes_v3.gpkg"
OUT_CSV = RESULTS / "damarakunta_routes_v3_comparison.csv"
OUT_CHECKS = RESULTS / "damarakunta_routes_v3_facility_checks.csv"
OUT_README = RESULTS / "damarakunta_routes_v3_README.txt"

CRS = "EPSG:32644"
MAX_SNAP_M = 35.0
N_ALTERNATIVES = 3
MAX_EXPANSIONS = 500_000
ROAD_TOLERANCE_M = 15.0
BUILTUP_CLASS = 50
WATER_CLASS = 80
SLOPE_LIMIT_DEG = 25.0
CORRIDOR_RADIUS = 2
ALT_CORRIDOR_PENALTIES = (3.0, 7.0, 12.0)
MAX_ROUTE_OVERLAP_RATIO = 0.85
SQRT2 = math.sqrt(2.0)


def require_file(path):
    if not path.exists():
        raise FileNotFoundError(f"Missing required input: {path}")


def read_raster(path):
    with rasterio.open(path) as src:
        return (
            src.read(1),
            src.transform,
            src.crs,
            src.shape,
            src.nodata,
        )


def cell_xy(transform, row, col):
    x, y = rasterio.transform.xy(
        transform, row, col, offset="center"
    )
    return float(x), float(y)


def nearest_cell(mask, transform, x, y, max_distance):
    rows, cols = np.where(mask)
    if len(rows) == 0:
        return None

    xs, ys = rasterio.transform.xy(
        transform, rows, cols, offset="center"
    )
    xs = np.asarray(xs)
    ys = np.asarray(ys)

    distances_sq = (xs - x) ** 2 + (ys - y) ** 2
    index = int(np.argmin(distances_sq))
    distance = float(np.sqrt(distances_sq[index]))

    if distance > max_distance:
        return None

    return int(rows[index]), int(cols[index]), distance


def make_corridor(cells, shape, radius):
    result = np.zeros(shape, dtype=bool)
    for row, col in cells:
        result[
            max(0, row-radius):min(shape[0], row+radius+1),
            max(0, col-radius):min(shape[1], col+radius+1),
        ] = True
    return result


def path_to_line(cells, transform):
    coordinates = [
        cell_xy(transform, row, col)
        for row, col in cells
    ]
    if len(coordinates) == 1:
        x, y = coordinates[0]
        coordinates.append((x + 0.01, y + 0.01))
    return LineString(coordinates)


def dijkstra(start, traversable, cost, road_targets,
             penalty_corridor=None, corridor_penalty=0.0):
    """Find a least-cost path; prior route corridors are penalized, not blocked."""
    height, width = traversable.shape
    if penalty_corridor is None:
        penalty_corridor = np.zeros(traversable.shape, dtype=bool)
    else:
        penalty_corridor = penalty_corridor.copy()
    # Never penalize the origin itself. All other corridor cells remain traversable.
    penalty_corridor[start] = False
    targets = road_targets
    if not targets.any():
        return None, np.inf, 0

    dist = np.full(traversable.shape, np.inf, dtype=np.float64)
    parent = {}
    dist[start] = 0.0
    queue = [(0.0, start[0], start[1])]
    expansions = 0
    neighbours = [
        (-1, -1, SQRT2), (-1, 0, 1.0), (-1, 1, SQRT2),
        (0, -1, 1.0),                  (0, 1, 1.0),
        (1, -1, SQRT2),  (1, 0, 1.0),  (1, 1, SQRT2),
    ]
    end = None
    while queue:
        current, row, col = heapq.heappop(queue)
        if current != dist[row, col]:
            continue
        if targets[row, col]:
            end = (row, col)
            break
        expansions += 1
        if expansions >= MAX_EXPANSIONS:
            break
        for dr, dc, step in neighbours:
            nr, nc = row + dr, col + dc
            if not (0 <= nr < height and 0 <= nc < width):
                continue
            if not traversable[nr, nc]:
                continue
            step_cost = 0.5 * (float(cost[row, col]) + float(cost[nr, nc])) * step
            if penalty_corridor[nr, nc]:
                step_cost *= (1.0 + corridor_penalty)
            new_cost = current + step_cost
            if new_cost < dist[nr, nc]:
                dist[nr, nc] = new_cost
                parent[(nr, nc)] = (row, col)
                heapq.heappush(queue, (new_cost, nr, nc))
    if end is None:
        return None, np.inf, expansions
    cells = [end]
    while cells[-1] != start:
        previous = parent.get(cells[-1])
        if previous is None:
            return None, np.inf, expansions
        cells.append(previous)
    cells.reverse()
    return cells, float(dist[end]), expansions


def route_overlap_ratio(path_a, path_b):
    """Fraction of the shorter path's cells shared by both paths."""
    a, b = set(path_a), set(path_b)
    denominator = max(1, min(len(a), len(b)))
    return len(a & b) / denominator


def main():
    RESULTS.mkdir(parents=True, exist_ok=True)

    inputs = [
        FACILITIES_PATH, ROADS_PATH, COST_PATH,
        BLOCKED_PATH, WORLDCOVER_PATH, SLOPE_PATH,
    ]
    for path in inputs:
        require_file(path)

    outputs = [OUT_GPKG, OUT_CSV, OUT_CHECKS, OUT_README]
    existing = [str(path) for path in outputs if path.exists()]
    if existing:
        raise FileExistsError(
            "V2 outputs already exist. Rename or move these files first:\n"
            + "\n".join(existing)
        )

    cost, transform, crs, shape, _ = read_raster(COST_PATH)
    blocked, tr_b, crs_b, shape_b, _ = read_raster(BLOCKED_PATH)
    world, tr_w, crs_w, shape_w, _ = read_raster(WORLDCOVER_PATH)
    slope, tr_s, crs_s, shape_s, _ = read_raster(SLOPE_PATH)

    for label, tr, raster_crs, raster_shape in [
        ("blocked mask", tr_b, crs_b, shape_b),
        ("WorldCover", tr_w, crs_w, shape_w),
        ("slope", tr_s, crs_s, shape_s),
    ]:
        if tr != transform or raster_crs != crs or raster_shape != shape:
            raise ValueError(
                f"{label} is not aligned with the cost raster."
            )

    if str(crs) != CRS:
        raise ValueError(f"Expected {CRS}; found {crs}")

    facilities = gpd.read_file(FACILITIES_PATH).to_crs(CRS)
    roads = gpd.read_file(ROADS_PATH).to_crs(CRS)
    roads = roads[
        roads.geometry.notna() & ~roads.geometry.is_empty
    ].copy()

    if facilities.empty or roads.empty:
        raise ValueError("Facility or road layer is empty.")

    road_union = roads.geometry.union_all()
    road_shapes = [
        (geom, 1)
        for geom in roads.geometry
        if geom is not None and not geom.is_empty
    ]
    road_raster = rasterize(
        road_shapes,
        out_shape=shape,
        transform=transform,
        fill=0,
        all_touched=True,
        dtype="uint8",
    ).astype(bool)

    built = world == BUILTUP_CLASS
    water = world == WATER_CLASS
    prohibited = blocked.astype(bool)

    valid_cost = np.isfinite(cost) & (cost > 0)
    valid_slope = (
        np.isfinite(slope)
        & (slope >= 0)
        & (slope <= SLOPE_LIMIT_DEG)
    )

    traversable = (
        valid_cost & valid_slope & ~prohibited & ~built & ~water
    )

    # Existing roads can be destinations even if their cells overlap
    # a built-up land-cover pixel. Water/prohibited cells are not targets.
    road_targets = (
        road_raster & valid_cost & ~prohibited & ~water
    )

    if not traversable.any() or not road_targets.any():
        raise ValueError(
            "No usable traversable cells or mapped-road targets found."
        )

    route_records = []
    facility_checks = []

    for _, facility in facilities.iterrows():
        geom = facility.geometry
        if geom is None or geom.is_empty:
            continue
        if geom.geom_type != "Point":
            print("Skipping non-point facility:", geom.geom_type)
            continue

        fid = str(facility.get("facility_id", facility.get("id", "")))
        name = str(
            facility.get("facility_name", facility.get("name", "Unknown"))
        )
        ftype = str(
            facility.get("facility_type", facility.get("type", "Unknown"))
        )
        fx, fy = geom.x, geom.y

        # Preferred start: traversable land within the snap limit.
        start_result = nearest_cell(
            traversable, transform, fx, fy, MAX_SNAP_M
        )
        fallback = False

        if start_result is None:
            # Relax built-up restriction for the start cell only.
            fallback_mask = (
                valid_cost & valid_slope & ~prohibited & ~water
            )
            start_result = nearest_cell(
                fallback_mask, transform, fx, fy, MAX_SNAP_M
            )
            fallback = start_result is not None

        facility_road_distance = float(geom.distance(road_union))

        if start_result is None:
            facility_checks.append({
                "facility_id": fid,
                "facility_name": name,
                "facility_type": ftype,
                "status": "NO_START_CELL_WITHIN_SNAP_LIMIT",
                "facility_to_nearest_road_m": facility_road_distance,
                "note": "No usable cell found within the snap limit.",
            })
            continue

        sr, sc, snap_m = start_result
        start = (sr, sc)
        start_point = Point(
            *rasterio.transform.xy(
                transform, sr, sc, offset="center"
            )
        )
        start_to_road = float(start_point.distance(road_union))

        prior_corridor = np.zeros(shape, dtype=bool)
        previous_lines = []
        previous_paths = []
        generated = 0

        for alternative in range(1, N_ALTERNATIVES + 1):
            # First route is unpenalized. Later routes retry with increasing
            # soft penalties so they can go around, rather than being blocked by,
            # earlier routes.
            penalties_to_try = (0.0,) if alternative == 1 else ALT_CORRIDOR_PENALTIES
            accepted = None
            max_expansions_seen = 0
            for corridor_penalty in penalties_to_try:
                cells, total_cost, expansions = dijkstra(
                    start, traversable, cost, road_targets,
                    penalty_corridor=None if alternative == 1 else prior_corridor,
                    corridor_penalty=corridor_penalty,
                )
                max_expansions_seen = max(max_expansions_seen, expansions)
                if cells is None:
                    continue
                overlap = max(
                    (route_overlap_ratio(cells, old_path) for old_path in previous_paths),
                    default=0.0,
                )
                if alternative > 1 and overlap > MAX_ROUTE_OVERLAP_RATIO:
                    continue
                accepted = (cells, total_cost, expansions, overlap, corridor_penalty)
                break

            if accepted is None:
                route_records.append({
                    "facility_id": fid,
                    "facility_name": name,
                    "facility_type": ftype,
                    "alternative": alternative,
                    "status": "NO_DISTINCT_ROUTE_FOUND_AFTER_SOFT_PENALTY_RETRIES",
                    "route_length_m": np.nan,
                    "facility_to_start_snap_m": float(snap_m),
                    "facility_to_nearest_road_m": facility_road_distance,
                    "snap_plus_route_length_proxy_m": np.nan,
                    "accumulated_cost": np.nan,
                    "start_cell_to_road_m": start_to_road,
                    "end_cell_to_road_m": np.nan,
                    "endpoint_within_15m_of_road": False,
                    "builtup_cells": np.nan,
                    "water_cells": np.nan,
                    "max_sampled_slope_deg": np.nan,
                    "start_snap_used_fallback": fallback,
                    "search_expansions": max_expansions_seen,
                    "route_overlap_ratio_with_previous": np.nan,
                    "corridor_penalty_used": np.nan,
                    "facility_location_verification": (
                        "UNVERIFIED_DUPLICATE_SOURCE_COORDINATES"
                        if "health" in (fid + " " + name).lower()
                        else "NOT_INDEPENDENTLY_VERIFIED"
                    ),
                    "geometry": None,
                })
                continue

            cells, total_cost, expansions, overlap, corridor_penalty = accepted
            line = path_to_line(cells, transform)
            end_row, end_col = cells[-1]
            end_point = Point(*cell_xy(transform, end_row, end_col))
            end_distance = float(end_point.distance(road_union))
            built_count = int(sum(built[r, c] for r, c in cells))
            water_count = int(sum(water[r, c] for r, c in cells))
            max_slope = float(max(slope[r, c] for r, c in cells))
            length = float(line.length)

            status = "CANDIDATE_REQUIRES_VISUAL_REVIEW"
            if fallback:
                status = "CANDIDATE_REQUIRES_START_SNAP_REVIEW"
            if end_distance > ROAD_TOLERANCE_M:
                status = "CANDIDATE_ENDPOINT_NOT_CLOSE_ENOUGH_TO_MAPPED_ROAD"
            if built_count > 0 or water_count > 0:
                status = "CANDIDATE_LANDCOVER_CHECK_FAILED"

            route_records.append({
                "facility_id": fid,
                "facility_name": name,
                "facility_type": ftype,
                "alternative": alternative,
                "status": status,
                "route_length_m": length,
                "facility_to_start_snap_m": float(snap_m),
                "facility_to_nearest_road_m": facility_road_distance,
                "snap_plus_route_length_proxy_m": float(snap_m + length),
                "accumulated_cost": float(total_cost),
                "start_cell_to_road_m": start_to_road,
                "end_cell_to_road_m": end_distance,
                "endpoint_within_15m_of_road": end_distance <= ROAD_TOLERANCE_M,
                "builtup_cells": built_count,
                "water_cells": water_count,
                "max_sampled_slope_deg": max_slope,
                "start_snap_used_fallback": fallback,
                "search_expansions": expansions,
                "route_overlap_ratio_with_previous": float(overlap),
                "corridor_penalty_used": float(corridor_penalty),
                "facility_location_verification": (
                    "UNVERIFIED_DUPLICATE_SOURCE_COORDINATES"
                    if "health" in (fid + " " + name).lower()
                    else "NOT_INDEPENDENTLY_VERIFIED"
                ),
                "geometry": line,
            })
            previous_lines.append(line)
            previous_paths.append(cells)
            generated += 1
            prior_corridor |= make_corridor(cells, shape, CORRIDOR_RADIUS)
            prior_corridor[start] = False

        facility_checks.append({
            "facility_id": fid,
            "facility_name": name,
            "facility_type": ftype,
            "status": (
                "ROUTES_GENERATED" if generated
                else "NO_DISTINCT_ROUTE_GENERATED"
            ),
            "facility_to_start_snap_m": float(snap_m),
            "facility_to_nearest_road_m": facility_road_distance,
            "start_cell_to_road_m": start_to_road,
            "start_snap_used_fallback": fallback,
            "distinct_routes_generated": generated,
            "note": (
                "Candidate routes require imagery review and verification "
                "of facility location, land ownership, drainage and feasibility."
            ),
        })

    if not route_records:
        raise RuntimeError("No route records were produced.")

    # Save the full comparison, including failed alternatives.
    comparison = pd.DataFrame([
        {k: v for k, v in record.items() if k != "geometry"}
        for record in route_records
    ])
    comparison.to_csv(OUT_CSV, index=False)
    pd.DataFrame(facility_checks).to_csv(OUT_CHECKS, index=False)

    # Write only rows with valid line geometries to the GeoPackage.
    lines = [
        {k: v for k, v in record.items() if k != "geometry"}
        | {"geometry": record["geometry"]}
        for record in route_records
        if record.get("geometry") is not None
        and not record["geometry"].is_empty
    ]
    if lines:
        route_gdf = gpd.GeoDataFrame(
            lines, geometry="geometry", crs=CRS
        )
        route_gdf.to_file(
            OUT_GPKG, layer="route_alternatives", driver="GPKG"
        )

    OUT_README.write_text(
        f"""Damarakunta route reconstruction V3
===================================
CRS: {CRS}
Maximum facility snap distance: {MAX_SNAP_M} m
Mapped-road endpoint tolerance: {ROAD_TOLERANCE_M} m
Slope screening cap: {SLOPE_LIMIT_DEG} degrees

Outputs:
- {OUT_GPKG}
- {OUT_CSV}
- {OUT_CHECKS}

Important limitations:
- These are GIS-generated planning candidates, not construction-ready roads.
- Alternative routes use a soft cost penalty around previous routes; alternatives with >85% cell overlap are rejected.
- snap_plus_route_length_proxy_m is the straight-line facility snap plus route-line length; it is not a verified travel distance.
- WorldCover is 10 m land-cover data and cannot reliably identify individual roofs.
- A zero built-up cell count does not prove every building is avoided.
- The slope threshold is a computational screening setting, not an engineering standard.
- The health-centre record has conflicting source coordinates and must be verified before interpreting its route.
- Verify route alignments, facility coordinates, land ownership, drainage and field feasibility.
""",
        encoding="utf-8",
    )

    print("\nV3 processing complete.")
    print("Comparison CSV:", OUT_CSV)
    print("Facility checks:", OUT_CHECKS)
    print("Route GeoPackage:", OUT_GPKG)
    print("README:", OUT_README)
    print("\nRoute summary:")
    print(
        comparison[
            [
                "facility_id", "facility_name", "alternative", "status",
                "route_length_m", "snap_plus_route_length_proxy_m",
                "end_cell_to_road_m",
            ]
        ].to_string(index=False)
    )


if __name__ == "__main__":
    main()

