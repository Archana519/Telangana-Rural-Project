"""
Damarakunta Route Connectivity Validation - V3

Purpose:
- Check generated route endpoints against the facility point and existing road network.
- Measure endpoint-to-road and facility-to-route distances.
- Check whether the route geometry intersects existing road geometry.
- Save a CSV report and a GeoPackage containing the routes and validation fields.

Important:
This is geometric screening, not proof of navigable network topology, road access,
facility entrance access, land ownership, or construction feasibility.
"""

from pathlib import Path
import sys
import warnings

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point, LineString, MultiLineString
from shapely.ops import nearest_points

ROOT = Path(r"D:\Telangana_Rural_Project")
BASE = ROOT / "Siddipet" / "Damarakunta"

ROADS_PATH = BASE / "reference" / "tgrac_road_network.gpkg"
FACILITIES_PATH = BASE / "reference" / "damarakunta_priority_facilities.gpkg"
ROUTES_PATH = BASE / "results" / "damarakunta_routes_v3.gpkg"

OUT_CSV = BASE / "results" / "damarakunta_route_connectivity_validation_v3.csv"
OUT_GPKG = BASE / "results" / "damarakunta_route_connectivity_validation_v3.gpkg"
OUT_SUMMARY = BASE / "results" / "damarakunta_route_connectivity_validation_v3_README.txt"

# These are screening thresholds only, not engineering standards.
ROAD_ENDPOINT_TOLERANCE_M = 5.0
FACILITY_ENDPOINT_TOLERANCE_M = 5.0
CRS_EXPECTED = "EPSG:32644"


def stop(message):
    print(f"\nERROR: {message}")
    sys.exit(1)


def read_layer(path, label):
    if not path.exists():
        stop(
            f"Cannot find {label}:\n{path}\n"
            "Check the filename and folder path, then run the script again."
        )
    try:
        gdf = gpd.read_file(path)
    except Exception as exc:
        stop(f"Could not read {label}: {exc}")
    if gdf.empty:
        stop(f"{label} contains no features: {path}")
    if gdf.crs is None:
        stop(f"{label} has no CRS. Assign the correct CRS before measuring distances.")
    return gdf


def find_column(gdf, candidates, label, required=True):
    lookup = {str(c).lower(): c for c in gdf.columns}
    for candidate in candidates:
        if candidate.lower() in lookup:
            return lookup[candidate.lower()]
    if required:
        stop(
            f"Could not identify {label} column.\n"
            f"Available columns: {list(gdf.columns)}"
        )
    return None


def line_parts(geom):
    if geom is None or geom.is_empty:
        return []
    if geom.geom_type == "LineString":
        return [geom]
    if geom.geom_type == "MultiLineString":
        return list(geom.geoms)
    if geom.geom_type == "GeometryCollection":
        parts = []
        for item in geom.geoms:
            parts.extend(line_parts(item))
        return parts
    return []


def nearest_road_distance(point, roads_union):
    if point is None or point.is_empty:
        return None
    return float(point.distance(roads_union))


def nearest_route_endpoint_to_facility(route, facility):
    endpoints = [Point(route.coords[0]), Point(route.coords[-1])]
    distances = [float(p.distance(facility)) for p in endpoints]
    index = min(range(2), key=lambda i: distances[i])
    return endpoints[index], distances[index], 1 - index, endpoints[1 - index]


def route_fields(route_row, route_geom, facility_geom, roads_union):
    parts = line_parts(route_geom)
    if not parts:
        return {
            "geometry_valid": False,
            "route_length_m": None,
            "facility_to_route_geometry_m": None,
            "endpoint_a_to_facility_m": None,
            "endpoint_b_to_facility_m": None,
            "chosen_facility_endpoint": None,
            "chosen_facility_endpoint_gap_m": None,
            "other_endpoint_to_road_m": None,
            "endpoint_a_to_road_m": None,
            "endpoint_b_to_road_m": None,
            "route_to_road_geometry_m": None,
            "route_intersects_existing_road": False,
            "road_intersection_length_m": 0.0,
            "road_endpoint_status": "INVALID_OR_NON_LINE_ROUTE",
            "facility_endpoint_status": "INVALID_OR_NON_LINE_ROUTE",
            "geometric_connection_status": "INVALID_OR_NON_LINE_ROUTE",
        }

    # A route feature should ideally be one continuous line. If multipart,
    # combine parts for distance/intersection screening and report its geometry type.
    from shapely.ops import unary_union
    route_line = unary_union(parts)

    endpoint_a = Point(parts[0].coords[0])
    endpoint_b = Point(parts[-1].coords[-1])
    # If the line is multipart, endpoint A/B are representative endpoints of
    # the first/last parts only; topology must be reviewed separately.
    d_a_fac = float(endpoint_a.distance(facility_geom))
    d_b_fac = float(endpoint_b.distance(facility_geom))
    if d_a_fac <= d_b_fac:
        chosen_fac_endpoint = endpoint_a
        chosen_fac_gap = d_a_fac
        other_endpoint = endpoint_b
        chosen_fac_label = "A"
    else:
        chosen_fac_endpoint = endpoint_b
        chosen_fac_gap = d_b_fac
        other_endpoint = endpoint_a
        chosen_fac_label = "B"

    d_a_road = nearest_road_distance(endpoint_a, roads_union)
    d_b_road = nearest_road_distance(endpoint_b, roads_union)
    other_endpoint_road_gap = nearest_road_distance(other_endpoint, roads_union)
    route_road_gap = float(route_line.distance(roads_union))
    intersection = route_line.intersection(roads_union)
    intersects = not intersection.is_empty
    intersection_length = float(intersection.length) if intersects else 0.0

    facility_gap_ok = chosen_fac_gap <= FACILITY_ENDPOINT_TOLERANCE_M
    road_gap_ok = other_endpoint_road_gap <= ROAD_ENDPOINT_TOLERANCE_M

    if facility_gap_ok:
        facility_status = "FACILITY_ENDPOINT_WITHIN_TOLERANCE"
    else:
        facility_status = "FACILITY_ENDPOINT_GAP_REMAINS"

    if road_gap_ok:
        road_status = "ROAD_ENDPOINT_WITHIN_TOLERANCE"
    else:
        road_status = "ROAD_ENDPOINT_GAP_REMAINS"

    if facility_gap_ok and road_gap_ok and intersects:
        connection_status = "POTENTIAL_GEOMETRIC_CONNECTION_REQUIRES_TOPOLOGY_REVIEW"
    elif facility_gap_ok and road_gap_ok:
        connection_status = "ENDPOINTS_NEAR_TARGETS_BUT_NO_LINE_INTERSECTION_CONFIRMED"
    elif not facility_gap_ok and not road_gap_ok:
        connection_status = "FACILITY_AND_ROAD_ENDPOINT_GAPS_REMAIN"
    elif not facility_gap_ok:
        connection_status = "FACILITY_ENDPOINT_GAP_REMAINS"
    else:
        connection_status = "ROAD_ENDPOINT_GAP_REMAINS"

    return {
        "geometry_valid": bool(route_geom.is_valid),
        "route_geometry_type": route_geom.geom_type,
        "route_length_m": float(route_geom.length),
        "facility_to_route_geometry_m": float(route_line.distance(facility_geom)),
        "endpoint_a_to_facility_m": d_a_fac,
        "endpoint_b_to_facility_m": d_b_fac,
        "chosen_facility_endpoint": chosen_fac_label,
        "chosen_facility_endpoint_gap_m": chosen_fac_gap,
        "other_endpoint_to_road_m": other_endpoint_road_gap,
        "endpoint_a_to_road_m": d_a_road,
        "endpoint_b_to_road_m": d_b_road,
        "route_to_road_geometry_m": route_road_gap,
        "route_intersects_existing_road": bool(intersects),
        "road_intersection_length_m": intersection_length,
        "road_endpoint_status": road_status,
        "facility_endpoint_status": facility_status,
        "geometric_connection_status": connection_status,
    }


def main():
    print("=== DAMARAKUNTA ROUTE CONNECTIVITY VALIDATION V3 ===")
    print("Loading project layers...")

    roads = read_layer(ROADS_PATH, "existing road network")
    facilities = read_layer(FACILITIES_PATH, "priority facilities")
    routes = read_layer(ROUTES_PATH, "V3 generated route alternatives")

    # Use the projected metric CRS from the study-area project.
    if roads.crs.to_string() != CRS_EXPECTED:
        print(f"Reprojecting roads from {roads.crs} to {CRS_EXPECTED}")
        roads = roads.to_crs(CRS_EXPECTED)
    if facilities.crs != roads.crs:
        facilities = facilities.to_crs(roads.crs)
    if routes.crs != roads.crs:
        routes = routes.to_crs(roads.crs)

    roads = roads[roads.geometry.notna() & ~roads.geometry.is_empty].copy()
    facilities = facilities[facilities.geometry.notna() & ~facilities.geometry.is_empty].copy()
    routes = routes[routes.geometry.notna() & ~routes.geometry.is_empty].copy()

    if roads.empty or facilities.empty or routes.empty:
        stop("One of the required layers has no usable geometries.")

    # Build a single geometry for road-distance/intersection checks.
    from shapely.ops import unary_union
    roads_union = unary_union(list(roads.geometry))

    fac_name_col = find_column(
        facilities,
        ["facility_name", "name", "NAME", "facility", "FACILITY_NAME"],
        "facility name",
        required=False,
    )
    fac_id_col = find_column(
        facilities,
        ["facility_id", "id", "NIN_ID", "OBJECTID", "fid"],
        "facility ID",
        required=False,
    )

    route_fac_name_col = find_column(
        routes,
        ["facility_name", "facility", "name", "target_name"],
        "route facility name",
        required=False,
    )
    route_fac_id_col = find_column(
        routes,
        ["facility_id", "target_id", "NIN_ID", "facility_code"],
        "route facility ID",
        required=False,
    )
    alt_col = find_column(
        routes,
        ["alternative", "alt", "route_alt", "candidate", "rank"],
        "route alternative",
        required=False,
    )

    # Prepare facility records for matching by ID/name.
    facility_records = []
    for idx, row in facilities.iterrows():
        name = str(row[fac_name_col]) if fac_name_col and pd.notna(row[fac_name_col]) else f"facility_{idx}"
        fid = str(row[fac_id_col]) if fac_id_col and pd.notna(row[fac_id_col]) else ""
        facility_records.append({"name": name, "id": fid, "geometry": row.geometry})

    output_rows = []
    output_geometries = []

    for idx, route_row in routes.iterrows():
        route_geom = route_row.geometry
        r_name = str(route_row[route_fac_name_col]) if route_fac_name_col and pd.notna(route_row[route_fac_name_col]) else ""
        r_id = str(route_row[route_fac_id_col]) if route_fac_id_col and pd.notna(route_row[route_fac_id_col]) else ""

        # Match exact facility ID first, then name, then nearest facility as a clearly flagged fallback.
        matches = []
        if r_id:
            matches = [f for f in facility_records if f["id"] and f["id"] == r_id]
        if not matches and r_name:
            matches = [f for f in facility_records if f["name"].strip().lower() == r_name.strip().lower()]
        match_method = "EXACT_ID" if matches and r_id else ("EXACT_NAME" if matches else "")

        if matches:
            facility = matches[0]
        else:
            # Some route layers may use a different label schema. Use nearest facility,
            # but mark the match as inferred and require manual review.
            facility = min(
                facility_records,
                key=lambda f: float(route_geom.distance(f["geometry"])),
            )
            match_method = "NEAREST_FACILITY_FALLBACK_REQUIRES_REVIEW"

        result = route_fields(route_row, route_geom, facility["geometry"], roads_union)
        result.update({
            "source_route_index": str(idx),
            "facility_name_matched": facility["name"],
            "facility_id_matched": facility["id"],
            "facility_match_method": match_method,
            "route_facility_name_source": r_name,
            "route_facility_id_source": r_id,
            "alternative": str(route_row[alt_col]) if alt_col and pd.notna(route_row[alt_col]) else "",
            "facility_coordinate_independently_verified": "NO",
            "topology_verified": "NO",
            "ownership_verified": "NO",
            "construction_feasibility": "NOT_ASSESSED",
            "screening_note": (
                "Geometric screening only; verify facility entrance, road topology, "
                "building clearance, drainage, ownership and engineering feasibility."
            ),
        })
        output_rows.append(result)
        output_geometries.append(route_geom)

    report = pd.DataFrame(output_rows)
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    report.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")

    # Save route geometries plus the validation attributes to a separate GeoPackage.
    result_gdf = gpd.GeoDataFrame(report, geometry=output_geometries, crs=roads.crs)
    # GeoPackage does not support all Python/pandas extension types; normalize columns.
    for col in result_gdf.columns:
        if col == "geometry":
            continue
        if pd.api.types.is_bool_dtype(result_gdf[col]):
            result_gdf[col] = result_gdf[col].astype("int64")
    result_gdf.to_file(OUT_GPKG, layer="route_connectivity_v3", driver="GPKG")

    summary = [
        "DAMARAKUNTA ROUTE CONNECTIVITY VALIDATION V3",
        "",
        f"Routes checked: {len(report)}",
        f"Existing road features read: {len(roads)}",
        f"Facility features read: {len(facilities)}",
        f"CRS used for distances: {roads.crs}",
        f"Road endpoint tolerance (screening only): {ROAD_ENDPOINT_TOLERANCE_M} m",
        f"Facility endpoint tolerance (screening only): {FACILITY_ENDPOINT_TOLERANCE_M} m",
        "",
        "Status counts:",
        report["geometric_connection_status"].value_counts(dropna=False).to_string(),
        "",
        "IMPORTANT LIMITATIONS",
        "- Geometric proximity is not proof of a connected or navigable road network.",
        "- The facility coordinate/entrance is not independently verified by this script.",
        "- This does not assess ownership, drainage, roof/building clearance, or construction feasibility.",
        "- Review the CSV and map candidate routes before drawing any conclusions.",
        "",
        f"CSV: {OUT_CSV}",
        f"GeoPackage: {OUT_GPKG}",
    ]
    OUT_SUMMARY.write_text("\n".join(summary), encoding="utf-8")

    print("\nValidation complete.")
    print(f"Routes checked: {len(report)}")
    print(f"CSV: {OUT_CSV}")
    print(f"GeoPackage: {OUT_GPKG}")
    print(f"Summary: {OUT_SUMMARY}")
    print("\nGeometric connection status counts:")
    print(report["geometric_connection_status"].value_counts(dropna=False).to_string())
    print("\nReminder: these are geometric screening results, not verified network connectivity.")


if __name__ == "__main__":
    main()
