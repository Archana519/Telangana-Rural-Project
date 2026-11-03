from pathlib import Path
import heapq
import math
import warnings

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.features import rasterize
from shapely.geometry import LineString, Point
from shapely.ops import nearest_points

# Damarakunta rural access-route reconstruction V4
# Endpoint-aware planning candidates; NOT construction-ready roads.
#
# V4 changes:
# 1. Keeps V3 inputs and outputs untouched; writes new V4 output files.
# 2. Adds explicit facility-to-raster-start and raster-end-to-road connectors.
# 3. Builds a combined geometry that includes both connectors.
# 4. Reports connector lengths separately from raster-path length.
# 5. Checks actual line intersection with the mapped road geometry.
# 6. Flags straight-line connectors for visual/engineering review.
#
# Important: A straight connector is only a geometric proposal. It is NOT
# proof of legal access, building clearance, ownership, drainage feasibility,
# or a safe/constructible road. Review all connector segments on imagery.

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

OUT_GPKG = RESULTS / "damarakunta_routes_v4.gpkg"
OUT_CSV = RESULTS / "damarakunta_routes_v4_comparison.csv"
OUT_CHECKS = RESULTS / "damarakunta_routes_v4_facility_checks.csv"
OUT_README = RESULTS / "damarakunta_routes_v4_README.txt"

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
    x, y = rasterio.transform.xy(transform, row, col, offset="center")
    return float(x), float(y)


def nearest_cell(mask, transform, x, y, max_distance):
    rows, cols = np.where(mask)
    if len(rows) == 0:
        return None

    # Convert cell-centre coordinates to arrays. This is acceptable for this
    # study raster (679 x 432); it avoids introducing a new spatial-index dependency.
    xs, ys = rasterio.transform.xy(transform, rows, cols, offset="center")
    xs = np.asarray(xs, dtype=float)
    ys = np.asarray(ys, dtype=float)
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
            max(0, row - radius):min(shape[0], row + radius + 1),
            max(0, col - radius):min(shape[1], col + radius + 1),
        ] = True
    return result


def path_to_coordinates(cells, transform):
    return [cell_xy(transform, row, col) for row, col in cells]


def path_to_line(cells, transform):
    coordinates = path_to_coordinates(cells, transform)
    if len(coordinates) == 1:
        x, y = coordinates[0]
        coordinates.append((x + 0.01, y + 0.01))
    return LineString(coordinates)


def route_overlap_ratio(path_a, path_b):
    a, b = set(path_a), set(path_b)
    denominator = max(1, min(len(a), len(b)))
    return len(a & b) / denominator


def dijkstra(start, traversable, cost, road_targets,
             penalty_corridor=None, corridor_penalty=0.0):
    """Least-cost path from start to any target cell."""
    height, width = traversable.shape
    if penalty_corridor is None:
        penalty_corridor = np.zeros(traversable.shape, dtype=bool)
    else:
        penalty_corridor = penalty_corridor.copy()

    penalty_corridor[start] = False
    if not road_targets.any():
        return None, np.inf, 0

    dist = np.full(traversable.shape, np.inf, dtype=np.float64)
    parent = {}
    dist[start] = 0.0
    queue = [(0.0, start[0], start[1])]
    expansions = 0
    neighbours = [
        (-1, -1, SQRT2), (-1, 0, 1.0), (-1, 1, SQRT2),
        (0, -1, 1.0),                    (0, 1, 1.0),
        (1, -1, SQRT2),  (1, 0, 1.0),   (1, 1, SQRT2),
    ]

    end = None
    while queue:
        current, row, col = heapq.heappop(queue)
        if current != dist[row, col]:
            continue
        if road_targets[row, col]:
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

            step_cost = (
                0.5 * (float(cost[row, col]) + float(cost[nr, nc])) * step
            )
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


def deduplicate_coordinates(coords, tolerance=1e-8):
    result = []
    for coord in coords:
        xy = (float(coord[0]), float(coord[1]))
        if not result or math.hypot(
            xy[0] - result[-1][0], xy[1] - result[-1][1]
        ) > tolerance:
            result.append(xy)
    return result


def combine_route_geometry(facility_point, start_point, raster_line, road_point):
    """Combine proposed facility connector, raster path, and road connector."""
    coords = [(facility_point.x, facility_point.y)]

    # Include raster path coordinates; start_point is its first cell centre.
    coords.extend(list(raster_line.coords))
    coords.append((road_point.x, road_point.y))
    coords = deduplicate_coordinates(coords)

    if len(coords) < 2:
        raise ValueError("Combined route geometry has fewer than two coordinates.")
    return LineString(coords)


def safe_float(value):
    try:
        value = float(value)
        return value if np.isfinite(value) else np.nan
    except (TypeError, ValueError):
        return np.nan


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
            "V4 outputs already exist. They will not be overwritten.\n"
            "Move/rename these V4 files first if you intentionally want to rerun:\n"
            + "\n".join(existing)
        )

    cost, transform, crs, shape, nodata = read_raster(COST_PATH)
    blocked, tr_b, crs_b, shape_b, _ = read_raster(BLOCKED_PATH)
    world, tr_w, crs_w, shape_w, _ = read_raster(WORLDCOVER_PATH)
    slope, tr_s, crs_s, shape_s, _ = read_raster(SLOPE_PATH)

    for label, tr, raster_crs, raster_shape in [
        ("blocked mask", tr_b, crs_b, shape_b),
        ("WorldCover", tr_w, crs_w, shape_w),
        ("slope", tr_s, crs_s, shape_s),
    ]:
        if tr != transform or raster_crs != crs or raster_shape != shape:
            raise ValueError(f"{label} is not aligned with the cost raster.")

    if str(crs) != CRS:
        raise ValueError(f"Expected {CRS}; found {crs}")

    facilities = gpd.read_file(FACILITIES_PATH).to_crs(CRS)
    roads = gpd.read_file(ROADS_PATH).to_crs(CRS)
    roads = roads[
        roads.geometry.notna() & ~roads.geometry.is_empty
    ].copy()

    if facilities.empty or roads.empty:
        raise ValueError("Facility or road layer is empty.")

    # Clean road geometries and build union for nearest-point calculations.
    road_geometries = [
        geom for geom in roads.geometry
        if geom is not None and not geom.is_empty
    ]
    road_union = roads.geometry.union_all()
    road_shapes = [(geom, 1) for geom in road_geometries]
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
        np.isfinite(slope) & (slope >= 0) & (slope <= SLOPE_LIMIT_DEG)
    )
    traversable = valid_cost & valid_slope & ~prohibited & ~built & ~water

    # Destination cells are mapped-road raster cells that are usable under
    # the existing screening. We then connect the selected cell centre to
    # the nearest point on the actual road geometry.
    road_targets = road_raster & valid_cost & ~prohibited & ~water
    if not traversable.any() or not road_targets.any():
        raise ValueError("No usable traversable cells or mapped-road targets found.")

    route_records = []
    facility_checks = []

    for _, facility in facilities.iterrows():
        geom = facility.geometry
        if geom is None or geom.is_empty or geom.geom_type != "Point":
            continue

        fid = str(facility.get("facility_id", facility.get("id", "")))
        name = str(facility.get("facility_name", facility.get("name", "Unknown")))
        ftype = str(facility.get("facility_type", facility.get("type", "Unknown")))
        fx, fy = geom.x, geom.y

        start_result = nearest_cell(
            traversable, transform, fx, fy, MAX_SNAP_M
        )
        fallback = False

        if start_result is None:
            # Relax built-up restriction only for selecting a start cell.
            # The connector still needs visual review; no building clearance
            # is implied by this fallback.
            fallback_mask = valid_cost & valid_slope & ~prohibited & ~water
            start_result = nearest_cell(
                fallback_mask, transform, fx, fy, MAX_SNAP_M
            )
            fallback = start_result is not None

        facility_to_nearest_road = float(geom.distance(road_union))

        if start_result is None:
            facility_checks.append({
                "facility_id": fid,
                "facility_name": name,
                "facility_type": ftype,
                "status": "NO_START_CELL_WITHIN_SNAP_LIMIT",
                "facility_to_nearest_road_m": facility_to_nearest_road,
                "note": "No usable raster cell found within MAX_SNAP_M.",
            })
            continue

        sr, sc, snap_m = start_result
        start = (sr, sc)
        start_point = Point(*cell_xy(transform, sr, sc))

        prior_corridor = np.zeros(shape, dtype=bool)
        previous_paths = []
        generated = 0

        for alternative in range(1, N_ALTERNATIVES + 1):
            penalties_to_try = (
                (0.0,) if alternative == 1 else ALT_CORRIDOR_PENALTIES
            )
            accepted = None
            max_expansions_seen = 0

            for corridor_penalty in penalties_to_try:
                cells, total_cost, expansions = dijkstra(
                    start,
                    traversable,
                    cost,
                    road_targets,
                    penalty_corridor=(
                        None if alternative == 1 else prior_corridor
                    ),
                    corridor_penalty=corridor_penalty,
                )
                max_expansions_seen = max(max_expansions_seen, expansions)
                if cells is None:
                    continue

                overlap = max(
                    (
                        route_overlap_ratio(cells, old_path)
                        for old_path in previous_paths
                    ),
                    default=0.0,
                )
                if alternative > 1 and overlap > MAX_ROUTE_OVERLAP_RATIO:
                    continue

                accepted = (
                    cells, total_cost, expansions, overlap, corridor_penalty
                )
                break

            if accepted is None:
                route_records.append({
                    "facility_id": fid,
                    "facility_name": name,
                    "facility_type": ftype,
                    "alternative": alternative,
                    "status": "NO_DISTINCT_ROUTE_FOUND_AFTER_SOFT_PENALTY_RETRIES",
                    "raster_path_length_m": np.nan,
                    "facility_connector_length_m": float(snap_m),
                    "road_connector_length_m": np.nan,
                    "total_geometry_length_m": np.nan,
                    "facility_to_nearest_road_m": facility_to_nearest_road,
                    "facility_to_start_snap_m": float(snap_m),
                    "start_cell_to_road_m": float(start_point.distance(road_union)),
                    "end_cell_to_road_m": np.nan,
                    "route_to_road_geometry_m": np.nan,
                    "route_intersects_road": False,
                    "intersection_type": "NOT_AVAILABLE",
                    "intersection_length_m": 0.0,
                    "facility_connector_review": "REQUIRED_STRAIGHT_LINE_CONNECTOR",
                    "road_connector_review": "NOT_AVAILABLE",
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
                    "topology_verified": "NO",
                    "ownership_verified": "NO",
                    "construction_feasibility": "NOT_ASSESSED",
                    "geometry": None,
                })
                continue

            cells, total_cost, expansions, overlap, corridor_penalty = accepted
            raster_line = path_to_line(cells, transform)
            end_row, end_col = cells[-1]
            end_point = Point(*cell_xy(transform, end_row, end_col))

            # Snap endpoint to the nearest point on actual mapped road geometry.
            # This is a proposed connector, not a claim of legal/physical access.
            road_point = nearest_points(end_point, road_union)[1]
            facility_connector_length = float(geom.distance(start_point))
            road_connector_length = float(end_point.distance(road_point))
            end_cell_to_road = float(end_point.distance(road_union))

            combined_line = combine_route_geometry(
                geom, start_point, raster_line, road_point
            )

            built_count = int(sum(bool(built[r, c]) for r, c in cells))
            water_count = int(sum(bool(water[r, c]) for r, c in cells))
            sampled_slopes = [safe_float(slope[r, c]) for r, c in cells]
            sampled_slopes = [v for v in sampled_slopes if np.isfinite(v)]
            max_slope = max(sampled_slopes) if sampled_slopes else np.nan

            # Test actual geometry against mapped road geometry. A point touch
            # is recorded separately from line overlap.
            intersection = combined_line.intersection(road_union)
            route_intersects_road = not intersection.is_empty
            intersection_length = (
                float(intersection.length) if route_intersects_road else 0.0
            )
            if intersection.is_empty:
                intersection_type = "NO_INTERSECTION"
            elif intersection.geom_type in ("LineString", "MultiLineString"):
                intersection_type = (
                    "LINE_OVERLAP" if intersection_length > 0
                    else "LINE_INTERSECTION"
                )
            elif intersection.geom_type == "Point":
                intersection_type = "POINT_CONTACT_ONLY"
            elif intersection.geom_type == "MultiPoint":
                intersection_type = "MULTIPLE_POINT_CONTACTS"
            else:
                intersection_type = intersection.geom_type.upper()

            # Total geometry includes facility and road connectors. It is a
            # geometric proposal length, not a verified travel or construction length.
            raster_path_length = float(raster_line.length)
            total_geometry_length = float(combined_line.length)

            if built_count > 0 or water_count > 0:
                status = "CANDIDATE_LANDCOVER_CHECK_FAILED"
            elif fallback:
                status = "CANDIDATE_REQUIRES_START_SNAP_REVIEW"
            elif facility_connector_length > 0.01 or road_connector_length > 0.01:
                status = "CONNECTORS_REQUIRE_VISUAL_REVIEW"
            elif not route_intersects_road:
                status = "NO_ROAD_INTERSECTION_CONFIRMED"
            else:
                status = "CANDIDATE_REQUIRES_VISUAL_REVIEW"

            route_records.append({
                "facility_id": fid,
                "facility_name": name,
                "facility_type": ftype,
                "alternative": alternative,
                "status": status,
                "raster_path_length_m": raster_path_length,
                "facility_connector_length_m": facility_connector_length,
                "road_connector_length_m": road_connector_length,
                "total_geometry_length_m": total_geometry_length,
                "facility_to_nearest_road_m": facility_to_nearest_road,
                "facility_to_start_snap_m": float(snap_m),
                "start_cell_to_road_m": float(start_point.distance(road_union)),
                "end_cell_to_road_m": end_cell_to_road,
                "route_to_road_geometry_m": float(combined_line.distance(road_union)),
                "route_intersects_road": bool(route_intersects_road),
                "intersection_type": intersection_type,
                "intersection_length_m": intersection_length,
                "facility_connector_review": (
                    "REQUIRED_STRAIGHT_LINE_CONNECTOR"
                    if facility_connector_length > 0.01 else "NEGLIGIBLE"
                ),
                "road_connector_review": (
                    "REQUIRED_STRAIGHT_LINE_CONNECTOR"
                    if road_connector_length > 0.01 else "NEGLIGIBLE"
                ),
                "accumulated_cost": float(total_cost),
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
                "topology_verified": "NO",
                "ownership_verified": "NO",
                "construction_feasibility": "NOT_ASSESSED",
                "geometry": combined_line,
            })

            previous_paths.append(cells)
            prior_corridor |= make_corridor(cells, shape, CORRIDOR_RADIUS)
            prior_corridor[start] = False
            generated += 1

        facility_checks.append({
            "facility_id": fid,
            "facility_name": name,
            "facility_type": ftype,
            "status": "ROUTES_GENERATED" if generated else "NO_ROUTE_GENERATED",
            "facility_to_start_snap_m": float(snap_m),
            "facility_to_nearest_road_m": facility_to_nearest_road,
            "start_cell_to_road_m": float(start_point.distance(road_union)),
            "start_snap_used_fallback": fallback,
            "routes_generated": generated,
            "note": (
                "V4 includes geometric facility/road connectors. Inspect each "
                "connector against imagery; connectivity, ownership, drainage, "
                "building clearance and engineering feasibility remain unverified."
            ),
        })

    if not route_records:
        raise RuntimeError("No route records were produced.")

    comparison = pd.DataFrame([
        {k: v for k, v in record.items() if k != "geometry"}
        for record in route_records
    ])
    comparison.to_csv(OUT_CSV, index=False)
    pd.DataFrame(facility_checks).to_csv(OUT_CHECKS, index=False)

    lines = [
        {k: v for k, v in record.items() if k != "geometry"}
        | {"geometry": record["geometry"]}
        for record in route_records
        if record.get("geometry") is not None
        and not record["geometry"].is_empty
    ]
    if lines:
        route_gdf = gpd.GeoDataFrame(lines, geometry="geometry", crs=CRS)
        route_gdf.to_file(
            OUT_GPKG, layer="route_alternatives", driver="GPKG"
        )

    OUT_README.write_text(
        f"""Damarakunta route reconstruction V4
===================================
CRS: {CRS}
Maximum facility raster snap distance: {MAX_SNAP_M} m
Mapped-road endpoint screening tolerance: {ROAD_TOLERANCE_M} m
Slope screening cap: {SLOPE_LIMIT_DEG} degrees

Outputs:
- {OUT_GPKG}
- {OUT_CSV}
- {OUT_CHECKS}

V4 changes:
- Combined route geometry includes facility point, raster path, and a connector
  to the nearest point on the mapped road geometry.
- Facility connector, raster path, and road connector lengths are reported separately.
- Actual geometry intersection with mapped roads is classified.
- Existing V3 files are not overwritten.

Important limitations:
- Connectors are straight-line geometric proposals, not verified access paths.
- The code does not prove building clearance, land ownership, drainage feasibility,
  road width, construction feasibility, or legal right-of-way.
- A geometry intersection does not prove navigable network topology.
- WorldCover is 10 m land-cover data and cannot reliably identify individual roofs.
- A zero built-up cell count does not prove every building is avoided.
- The slope threshold is a computational screening setting, not an engineering standard.
- The health-centre record has conflicting source coordinates and must be verified.
- These outputs are planning candidates only and require imagery/engineering review.
""",
        encoding="utf-8",
    )

    print("\n=== DAMARAKUNTA ROUTE RECONSTRUCTION V4 COMPLETE ===")
    print("Routes/GeoPackage:", OUT_GPKG)
    print("Comparison CSV:", OUT_CSV)
    print("Facility checks:", OUT_CHECKS)
    print("README:", OUT_README)
    print("\nRoute summary:")
    columns = [
        "facility_name", "alternative", "status",
        "raster_path_length_m", "facility_connector_length_m",
        "road_connector_length_m", "total_geometry_length_m",
        "intersection_type",
    ]
    print(comparison[columns].to_string(index=False))


if __name__ == "__main__":
    main()
