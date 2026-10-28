from pathlib import Path
import warnings

import geopandas as gpd
import pandas as pd

warnings.filterwarnings("ignore", category=UserWarning)

# ============================================================
# ACCESSIBILITY IMPROVEMENT EVALUATION V3
# Damarakunta, Markook Mandal, Siddipet District, Telangana
#
# This module evaluates geometric access gaps.
# It does NOT claim actual travel-time improvement or
# construction feasibility.
# ============================================================

ROOT = Path(r"D:\Telangana_Rural_Project")
BASE = ROOT / "Siddipet" / "Damarakunta"
REFERENCE = BASE / "reference"
RESULTS = BASE / "results"
RESULTS.mkdir(parents=True, exist_ok=True)

ROADS_FILE = REFERENCE / "tgrac_road_network.gpkg"
FACILITIES_FILE = REFERENCE / "damarakunta_priority_facilities.gpkg"
ROUTES_FILE = RESULTS / "damarakunta_routes_v3.gpkg"
FEASIBILITY_FILE = RESULTS / "damarakunta_route_feasibility_screening_v3.csv"
RANKING_FILE = RESULTS / "damarakunta_routes_v3_multi_criteria_ranking.csv"

OUTPUT_CSV = RESULTS / "damarakunta_accessibility_evaluation_v3.csv"
OUTPUT_GPKG = RESULTS / "damarakunta_accessibility_evaluation_v3.gpkg"
OUTPUT_SUMMARY = RESULTS / "damarakunta_accessibility_summary_v3.txt"


def find_column(df, candidates, required=True):
    """Find a column without depending on capitalization."""
    lookup = {str(c).strip().lower(): c for c in df.columns}

    for candidate in candidates:
        if candidate.lower() in lookup:
            return lookup[candidate.lower()]

    if required:
        raise ValueError(
            f"Required column not found. Tried {candidates}. "
            f"Available columns: {list(df.columns)}"
        )
    return None


def read_vector(path, label):
    if not path.exists():
        raise FileNotFoundError(f"{label} not found: {path}")

    gdf = gpd.read_file(path)

    if gdf.empty:
        raise ValueError(f"{label} contains no features: {path}")

    if gdf.crs is None:
        raise ValueError(f"{label} has no CRS: {path}")

    print(f"{label}: {len(gdf)} features, CRS={gdf.crs}")
    print(f"  Columns: {list(gdf.columns)}")
    return gdf


def nearest_distance(geometry, geometries):
    """Minimum planar distance in the projected CRS."""
    if geometry is None or geometry.is_empty:
        return None

    valid = [g for g in geometries if g is not None and not g.is_empty]
    if not valid:
        return None

    return float(min(geometry.distance(g) for g in valid))


def get_line_endpoints(line):
    """Return first and last endpoints of a LineString or MultiLineString."""
    if line is None or line.is_empty:
        return None, None

    if line.geom_type == "LineString":
        coords = list(line.coords)
        if not coords:
            return None, None
        from shapely.geometry import Point
        return Point(coords[0]), Point(coords[-1])

    if line.geom_type == "MultiLineString":
        parts = [part for part in line.geoms if not part.is_empty and len(part.coords)]
        if not parts:
            return None, None

        # Use the endpoints of the longest component for diagnostics.
        part = max(parts, key=lambda p: p.length)
        from shapely.geometry import Point
        return Point(part.coords[0]), Point(part.coords[-1])

    return None, None


def safe_number(value):
    try:
        number = float(value)
        if pd.isna(number):
            return None
        return number
    except (TypeError, ValueError):
        return None


def main():
    print("\n=== DAMARAKUNTA ACCESSIBILITY EVALUATION V3 ===\n")

    roads = read_vector(ROADS_FILE, "Existing road network")
    facilities = read_vector(FACILITIES_FILE, "Priority facilities")
    routes = read_vector(ROUTES_FILE, "V3 route candidates")

    # The input layers must use a common projected CRS for metre distances.
    target_crs = roads.crs
    if not target_crs.is_projected:
        raise ValueError(
            f"Road CRS {target_crs} is not projected. "
            "Use the project's projected metric CRS, EPSG:32644."
        )

    facilities = facilities.to_crs(target_crs)
    routes = routes.to_crs(target_crs)

    # Combine road geometries for nearest-distance calculations.
    road_geometries = [
        geom for geom in roads.geometry
        if geom is not None and not geom.is_empty
    ]

    if not road_geometries:
        raise ValueError("No usable road geometries were found.")

    # Identify facility columns.
    facility_id_col = find_column(
        facilities, ["facility_id", "facilityid", "id", "nin_id"]
    )
    facility_name_col = find_column(
        facilities, ["facility_name", "name", "facility", "asset_name"]
    )
    facility_type_col = find_column(
        facilities, ["facility_type", "type", "category"], required=False
    )

    # Identify route columns.
    route_facility_id_col = find_column(
        routes, ["facility_id", "facilityid", "id", "nin_id"]
    )
    route_name_col = find_column(
        routes, ["facility_name", "name", "facility_name_route"],
        required=False
    )
    alternative_col = find_column(
        routes, ["alternative", "alt", "route_alternative"]
    )
    status_col = find_column(
        routes, ["status", "route_status"], required=False
    )

    # Reprojected geometries allow us to measure in metres.
    facilities = facilities.copy()
    routes = routes.copy()

    # Convert IDs to strings to avoid integer/float formatting mismatches.
    facilities["_join_id"] = facilities[facility_id_col].astype(str).str.replace(
        r"\.0$", "", regex=True
    )
    routes["_join_id"] = routes[route_facility_id_col].astype(str).str.replace(
        r"\.0$", "", regex=True
    )

    # Preserve duplicate source records instead of silently choosing one.
    facility_records = {}
    for _, row in facilities.iterrows():
        facility_records.setdefault(row["_join_id"], []).append(row)

    # Optional supporting tables.
    feasibility = None
    if FEASIBILITY_FILE.exists():
        feasibility = pd.read_csv(FEASIBILITY_FILE, dtype=str)
        feasibility_id_col = find_column(
            feasibility, ["facility_id", "facilityid", "id", "nin_id"]
        )
        feasibility_alt_col = find_column(
            feasibility, ["alternative", "alt", "route_alternative"]
        )
        feasibility["_join_id"] = feasibility[feasibility_id_col].astype(str).str.replace(
            r"\.0$", "", regex=True
        )
        feasibility["_join_alt"] = feasibility[feasibility_alt_col].astype(str).str.replace(
            r"\.0$", "", regex=True
        )

    ranking = None
    if RANKING_FILE.exists():
        ranking = pd.read_csv(RANKING_FILE, dtype=str)
        ranking_id_col = find_column(
            ranking, ["facility_id", "facilityid", "id", "nin_id"]
        )
        ranking_alt_col = find_column(
            ranking, ["alternative", "alt", "route_alternative"]
        )
        ranking["_join_id"] = ranking[ranking_id_col].astype(str).str.replace(
            r"\.0$", "", regex=True
        )
        ranking["_join_alt"] = ranking[ranking_alt_col].astype(str).str.replace(
            r"\.0$", "", regex=True
        )

    results = []
    output_geometries = []

    for route_index, route_row in routes.iterrows():
        route_geom = route_row.geometry
        facility_id = route_row["_join_id"]
        alternative = str(route_row[alternative_col])

        matching_facilities = facility_records.get(facility_id, [])

        # Route ID may have been stored differently in different source layers.
        # If the ID match fails, do not guess a facility by name.
        if not matching_facilities:
            print(
                f"WARNING: No matching facility ID for route "
                f"{facility_id}, alternative {alternative}. Skipping."
            )
            continue

        # Some source layers may contain duplicate records. Keep all distances
        # visible and select the closest matching point for geometric diagnostics.
        point_distances = []
        for facility_row in matching_facilities:
            geom = facility_row.geometry
            if geom is not None and not geom.is_empty:
                point_distances.append(
                    (float(route_geom.distance(geom)), facility_row)
                )

        if not point_distances:
            continue

        point_distances.sort(key=lambda item: item[0])
        facility_to_route_m, facility_row = point_distances[0]
        facility_point = facility_row.geometry

        facility_name = str(facility_row[facility_name_col])
        facility_type = (
            str(facility_row[facility_type_col])
            if facility_type_col else "NOT_AVAILABLE"
        )

        baseline_facility_to_road_m = nearest_distance(
            facility_point, road_geometries
        )
        route_to_road_m = nearest_distance(route_geom, road_geometries)

        endpoint_a, endpoint_b = get_line_endpoints(route_geom)

        if endpoint_a is not None and endpoint_b is not None:
            endpoint_a_to_road_m = nearest_distance(endpoint_a, road_geometries)
            endpoint_b_to_road_m = nearest_distance(endpoint_b, road_geometries)

            endpoint_a_to_facility_m = float(endpoint_a.distance(facility_point))
            endpoint_b_to_facility_m = float(endpoint_b.distance(facility_point))

            # Do not assume route orientation; identify endpoints geometrically.
            facility_side_endpoint_gap_m = min(
                endpoint_a_to_facility_m, endpoint_b_to_facility_m
            )
            road_side_endpoint_gap_m = min(
                endpoint_a_to_road_m, endpoint_b_to_road_m
            )
        else:
            endpoint_a_to_road_m = None
            endpoint_b_to_road_m = None
            endpoint_a_to_facility_m = None
            endpoint_b_to_facility_m = None
            facility_side_endpoint_gap_m = None
            road_side_endpoint_gap_m = None

        route_length_m = float(route_geom.length)

        # Endpoint-aware diagnostics: route geometry being near a facility and
        # near a road does not prove that its endpoints connect those features.
        # Evaluate both possible route orientations and choose the lower combined
        # facility-endpoint + road-endpoint gap.
        route_length_m = float(route_geom.length)

        if (
            endpoint_a is not None
            and endpoint_b is not None
            and endpoint_a_to_facility_m is not None
            and endpoint_b_to_facility_m is not None
            and endpoint_a_to_road_m is not None
            and endpoint_b_to_road_m is not None
        ):
            orientation_1 = endpoint_a_to_facility_m + endpoint_b_to_road_m
            orientation_2 = endpoint_b_to_facility_m + endpoint_a_to_road_m

            if orientation_1 <= orientation_2:
                facility_endpoint_gap_m = endpoint_a_to_facility_m
                road_endpoint_gap_m = endpoint_b_to_road_m
                facility_endpoint_label = "A"
                road_endpoint_label = "B"
            else:
                facility_endpoint_gap_m = endpoint_b_to_facility_m
                road_endpoint_gap_m = endpoint_a_to_road_m
                facility_endpoint_label = "B"
                road_endpoint_label = "A"

            endpoint_proxy_m = (
                facility_endpoint_gap_m + route_length_m + road_endpoint_gap_m
            )

            facility_endpoint_near = facility_endpoint_gap_m <= 15
            road_endpoint_near = road_endpoint_gap_m <= 5

            if facility_endpoint_near and road_endpoint_near:
                geometric_status = "POTENTIAL_ENDPOINT_CONNECTION_REQUIRES_NETWORK_REVIEW"
            elif not facility_endpoint_near and not road_endpoint_near:
                geometric_status = "FACILITY_AND_ROAD_ENDPOINT_GAPS_REMAIN"
            elif not facility_endpoint_near:
                geometric_status = "FACILITY_ENDPOINT_GAP_REMAINS"
            else:
                geometric_status = "ROAD_ENDPOINT_GAP_REMAINS"
        else:
            facility_endpoint_gap_m = None
            road_endpoint_gap_m = None
            facility_endpoint_label = "UNKNOWN"
            road_endpoint_label = "UNKNOWN"
            endpoint_proxy_m = None
            geometric_status = "INSUFFICIENT_ENDPOINT_GEOMETRY"

        # This compares a straight-line baseline with an endpoint-aware route
        # proxy only when both ends pass screening thresholds. It remains a
        # provisional geometric estimate, never a validated network benefit.
        if (
            endpoint_proxy_m is not None
            and baseline_facility_to_road_m is not None
            and facility_endpoint_gap_m <= 15
            and road_endpoint_gap_m <= 5
        ):
            proxy_gap_reduction_m = baseline_facility_to_road_m - endpoint_proxy_m
            reduction_status = "PROVISIONAL_ENDPOINT_PROXY_ONLY"
        else:
            proxy_gap_reduction_m = None
            reduction_status = "NOT_ESTIMATED_ENDPOINT_CONNECTION_NOT_ESTABLISHED"

        record = {
            "facility_id": facility_id,
            "facility_name": facility_name,
            "facility_type": facility_type,
            "alternative": alternative,
            "route_status": (
                str(route_row[status_col]) if status_col else "NOT_AVAILABLE"
            ),
            "route_length_m": route_length_m,
            "baseline_facility_to_existing_road_m": baseline_facility_to_road_m,
            "facility_to_route_geometry_m": facility_to_route_m,
            "route_geometry_to_existing_road_m": route_to_road_m,
            "endpoint_a_to_facility_m": endpoint_a_to_facility_m,
            "endpoint_b_to_facility_m": endpoint_b_to_facility_m,
            "endpoint_a_to_road_m": endpoint_a_to_road_m,
            "endpoint_b_to_road_m": endpoint_b_to_road_m,
            "nearest_facility_side_endpoint_gap_m": facility_side_endpoint_gap_m,
            "nearest_road_side_endpoint_gap_m": road_side_endpoint_gap_m,
            "chosen_facility_endpoint": facility_endpoint_label,
            "chosen_road_endpoint": road_endpoint_label,
            "chosen_facility_endpoint_gap_m": facility_endpoint_gap_m,
            "chosen_road_endpoint_gap_m": road_endpoint_gap_m,
            "facility_route_road_proxy_m": endpoint_proxy_m,
            "provisional_proxy_gap_reduction_m": proxy_gap_reduction_m,
            "proxy_reduction_status": reduction_status,
            "geometric_connection_status": geometric_status,
            "facility_source_record_count": len(matching_facilities),
            "facility_location_verification": "NOT_INDEPENDENTLY_VERIFIED",
            "network_continuity_verified": False,
            "travel_time_improvement_verified": False,
            "construction_feasibility": "NOT_ASSESSED_BY_THIS_MODULE",
            "interpretation_limit": (
                "Planar geometry only; not a validated road-network path, "
                "travel-time benefit, monetary cost, or construction approval."
            ),
        }

        # Add screening details when a matching record exists.
        if feasibility is not None:
            matched = feasibility[
                (feasibility["_join_id"] == facility_id)
                & (feasibility["_join_alt"] == alternative)
            ]
            if not matched.empty:
                for col in [
                    "intersected_parcel_count",
                    "school_compound_intersections",
                    "ownership_clearance",
                    "drainage_clearance",
                    "building_clearance",
                    "construction_feasibility",
                    "overall_status",
                ]:
                    actual = find_column(matched, [col], required=False)
                    if actual:
                        record[f"screening_{col}"] = matched.iloc[0][actual]

        # Add the current preliminary rank if available.
        if ranking is not None:
            matched_rank = ranking[
                (ranking["_join_id"] == facility_id)
                & (ranking["_join_alt"] == alternative)
            ]
            if not matched_rank.empty:
                for col in ["preliminary_score", "rank_within_facility"]:
                    actual = find_column(matched_rank, [col], required=False)
                    if actual:
                        record[f"ranking_{col}"] = matched_rank.iloc[0][actual]

        results.append(record)
        output_geometries.append(route_geom)

    if not results:
        raise RuntimeError(
            "No routes were evaluated. Check facility IDs and route layer schema."
        )

    output_df = pd.DataFrame(results)
    output_df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

    output_gdf = gpd.GeoDataFrame(
        output_df.copy(),
        geometry=output_geometries,
        crs=target_crs,
    )

    # Remove an old output before writing a fresh GeoPackage.
    if OUTPUT_GPKG.exists():
        OUTPUT_GPKG.unlink()

    output_gdf.to_file(OUTPUT_GPKG, layer="accessibility_evaluation", driver="GPKG")

    summary_lines = [
        "DAMARAKUNTA ACCESSIBILITY EVALUATION V3",
        "=======================================",
        f"Routes evaluated: {len(output_df)}",
        f"Facilities evaluated: {output_df['facility_id'].nunique()}",
        "",
        "Interpretation:",
        "- Baseline distance is straight-line distance from facility point to mapped road geometry.",
        "- Route-to-road distance is the minimum distance between candidate route and mapped road geometry.",
        "- Endpoint proxy uses the selected facility-side endpoint gap, route length, and opposite road-side endpoint gap.",
        "- Endpoint proximity thresholds (15 m to facility and 5 m to road) are screening rules, not proof of connectivity.",
        "- Proxy reductions are provisional and are not proof of network connectivity.",
        "- This module does not calculate travel time, population coverage, rupee cost, or construction feasibility.",
        "- Facility coordinates and entrances still require independent verification.",
        "",
        f"CSV: {OUTPUT_CSV}",
        f"GeoPackage: {OUTPUT_GPKG}",
    ]

    OUTPUT_SUMMARY.write_text("\n".join(summary_lines), encoding="utf-8")

    print("\n=== EVALUATION COMPLETE ===")
    print(f"Routes evaluated: {len(output_df)}")
    print(f"Facilities evaluated: {output_df['facility_id'].nunique()}")
    print(f"CSV saved: {OUTPUT_CSV}")
    print(f"GeoPackage saved: {OUTPUT_GPKG}")
    print(f"Summary saved: {OUTPUT_SUMMARY}")

    display_cols = [
        "facility_name",
        "alternative",
        "route_length_m",
        "baseline_facility_to_existing_road_m",
        "facility_to_route_geometry_m",
        "route_geometry_to_existing_road_m",
        "chosen_facility_endpoint_gap_m",
        "chosen_road_endpoint_gap_m",
        "geometric_connection_status",
    ]
    print("\nGeometric accessibility diagnostics:")
    print(output_df[display_cols].to_string(index=False))


if __name__ == "__main__":
    main()
