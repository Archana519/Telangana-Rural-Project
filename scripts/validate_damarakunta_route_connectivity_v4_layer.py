from pathlib import Path
import math
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from shapely.ops import nearest_points

# ============================================================
# DAMARAKUNTA V4 ROUTE CONNECTIVITY VALIDATOR
# Read-only inputs; separate validation outputs
# ============================================================

BASE = Path(r"D:\Telangana_Rural_Project\Siddipet\Damarakunta")
RESULTS = BASE / "results"
REFERENCE = BASE / "reference"
ALIGNED = BASE / "aligned"

ROUTES_PATH = RESULTS / "damarakunta_routes_v4.gpkg"
ROUTES_LAYER = "route_alternatives"

ROADS_PATH = REFERENCE / "tgrac_road_network.gpkg"
FACILITIES_PATH = REFERENCE / "damarakunta_priority_facilities.gpkg"
FACILITIES_LAYER = "priority_facilities"

MASK_PATH = ALIGNED / "damarakunta_prohibited_mask_10m.tif"
COST_PATH = ALIGNED / "damarakunta_cost_surface_10m.tif"
WORLDCOVER_PATH = ALIGNED / "damarakunta_worldcover_10m.tif"
SLOPE_PATH = ALIGNED / "damarakunta_slope_10m.tif"

# Optional: set to the exact path of your cadastral parcel file
# only after confirming its filename and layer.
PARCELS_PATH = REFERENCE / "tgrac_cadastral_parcels.gpkg"

OUT_CSV = RESULTS / "damarakunta_route_connectivity_validation_v4_layer.csv"
OUT_GPKG = RESULTS / "damarakunta_route_connectivity_validation_v4_layer.gpkg"
OUT_README = RESULTS / "damarakunta_route_connectivity_validation_v4_layer_README.txt"

ROAD_TOLERANCE_M = 15.0
FACILITY_TOLERANCE_M = 5.0
SLOPE_LIMIT_DEG = 25.0
SAMPLE_SPACING_M = 5.0


def require_file(path):
    if not path.exists():
        raise FileNotFoundError(f"Required input file not found: {path}")


def finite_float(value):
    try:
        value = float(value)
        return value if math.isfinite(value) else np.nan
    except (TypeError, ValueError):
        return np.nan


def raster_samples(dataset, points):
    values = []
    for point in points:
        try:
            value = float(next(dataset.sample([(point.x, point.y)]))[0])
            if dataset.nodata is not None and np.isclose(value, dataset.nodata):
                values.append(np.nan)
            else:
                values.append(value)
        except Exception:
            values.append(np.nan)
    return values


def main():
    RESULTS.mkdir(parents=True, exist_ok=True)

    required = [
        ROUTES_PATH,
        ROADS_PATH,
        FACILITIES_PATH,
        MASK_PATH,
        COST_PATH,
        WORLDCOVER_PATH,
        SLOPE_PATH,
    ]
    for path in required:
        require_file(path)

    print("Loading V4 route layer...")
    routes = gpd.read_file(ROUTES_PATH, layer=ROUTES_LAYER)
    roads = gpd.read_file(ROADS_PATH)
    facilities = gpd.read_file(
        FACILITIES_PATH, layer=FACILITIES_LAYER
    )

    if routes.empty:
        raise ValueError("The V4 route layer contains no features.")

    if routes.crs is None or roads.crs is None or facilities.crs is None:
        raise ValueError("A required vector layer has no CRS.")

    roads = roads.to_crs(routes.crs)
    facilities = facilities.to_crs(routes.crs)

    routes = routes.reset_index(drop=True)
    roads = roads[
        roads.geometry.notna() & ~roads.geometry.is_empty
    ].copy()
    facilities = facilities[
        facilities.geometry.notna() & ~facilities.geometry.is_empty
    ].copy()

    if roads.empty:
        raise ValueError("The mapped road layer has no usable geometries.")

    road_union = roads.geometry.union_all()

    facility_by_id = {
        str(row["facility_id"]): row.geometry
        for _, row in facilities.iterrows()
    }

    # Load parcels only if the configured file actually exists.
    parcels = None
    if PARCELS_PATH.exists():
        try:
            parcels = gpd.read_file(PARCELS_PATH).to_crs(routes.crs)
            parcels = parcels[
                parcels.geometry.notna() & ~parcels.geometry.is_empty
            ].copy()
            print("Optional parcel layer loaded:", PARCELS_PATH.name)
        except Exception as exc:
            print("WARNING: Could not load optional parcel layer:", exc)
            parcels = None
    else:
        print(
            "NOTE: Optional parcel layer not found at configured path. "
            "Parcel impacts will be marked unavailable."
        )

    records = []
    output_geometries = []

    print("Opening aligned rasters...")
    with (
        rasterio.open(MASK_PATH) as mask_ds,
        rasterio.open(COST_PATH) as cost_ds,
        rasterio.open(WORLDCOVER_PATH) as wc_ds,
        rasterio.open(SLOPE_PATH) as slope_ds,
    ):
        raster_datasets = [mask_ds, cost_ds, wc_ds, slope_ds]

        for ds in raster_datasets:
            if ds.crs != mask_ds.crs:
                raise ValueError("Raster CRS mismatch detected.")
            if (
                ds.width != mask_ds.width
                or ds.height != mask_ds.height
                or ds.transform != mask_ds.transform
            ):
                raise ValueError(
                    "Raster grids differ. Stopping to avoid incorrect sampling."
                )

        mask_array = mask_ds.read(1)
        cost_array = cost_ds.read(1, masked=True)

        prohibited = mask_array == 1
        cost_nodata = np.ma.getmaskarray(cost_array)
        global_mask_cost_mismatches = int(
            np.count_nonzero(prohibited ^ cost_nodata)
        )

        for index, row in routes.iterrows():
            geom = row.geometry
            facility_id = str(row.get("facility_id", ""))
            facility = facility_by_id.get(facility_id)

            result = {
                "facility_id": facility_id,
                "facility_name": row.get("facility_name"),
                "facility_type": row.get("facility_type"),
                "alternative": row.get("alternative"),
                "source_status": row.get("status"),
                "route_geometry_length_m": np.nan,
                "facility_to_route_geometry_m": np.nan,
                "route_to_mapped_road_m": np.nan,
                "route_intersects_mapped_road": False,
                "road_intersection_type": "UNKNOWN",
                "road_intersection_length_m": 0.0,
                "facility_connection_screen": "UNKNOWN",
                "road_connection_screen": "UNKNOWN",
                "raster_sample_count": 0,
                "prohibited_mask_samples_value_1": 0,
                "cost_nodata_samples": 0,
                "cost_valid_samples": 0,
                "builtup_worldcover_samples_class_50": 0,
                "water_worldcover_samples_class_80": 0,
                "max_sampled_slope_degrees": np.nan,
                "slope_samples_over_25deg": 0,
                "global_mask_cost_grid_mismatches": (
                    global_mask_cost_mismatches
                ),
                "parcel_intersection_count": np.nan,
                "parcel_intersection_length_sum_m": np.nan,
                "parcel_screen_status": "PARCEL_LAYER_UNAVAILABLE",
                "facility_coordinate_independently_verified": "NO",
                "topology_verified": "NO",
                "ownership_verified": "NO",
                "construction_feasibility": "NOT_ASSESSED",
                "overall_status": "PRELIMINARY_GIS_SCREENING_ONLY",
            }

            if geom is None or geom.is_empty:
                result["road_connection_screen"] = "EMPTY_ROUTE_GEOMETRY"
                records.append(result)
                output_geometries.append(geom)
                continue

            result["route_geometry_length_m"] = float(geom.length)

            # Facility-to-route geometry distance.
            if facility is not None:
                facility_gap = float(facility.distance(geom))
                result["facility_to_route_geometry_m"] = facility_gap

                if facility_gap <= FACILITY_TOLERANCE_M:
                    result["facility_connection_screen"] = (
                        "WITHIN_TOLERANCE_ONLY_NOT_TOPOLOGY_PROOF"
                    )
                else:
                    result["facility_connection_screen"] = (
                        "FACILITY_ENDPOINT_GAP_REMAINS"
                    )
            else:
                result["facility_connection_screen"] = (
                    "FACILITY_ID_NOT_MATCHED"
                )

            # Actual route-geometry distance/intersection with mapped roads.
            road_gap = float(geom.distance(road_union))
            result["route_to_mapped_road_m"] = road_gap
            intersects = bool(geom.intersects(road_union))
            result["route_intersects_mapped_road"] = intersects

            if intersects:
                intersection = geom.intersection(road_union)
                result["road_intersection_type"] = intersection.geom_type
                result["road_intersection_length_m"] = float(
                    intersection.length
                )

                if intersection.length > 0:
                    result["road_connection_screen"] = (
                        "LINE_INTERSECTION_WITH_MAPPED_ROAD"
                    )
                else:
                    result["road_connection_screen"] = (
                        "POINT_CONTACT_ONLY"
                    )
            elif road_gap <= ROAD_TOLERANCE_M:
                result["road_intersection_type"] = "NO_INTERSECTION"
                result["road_connection_screen"] = (
                    "NEAR_ROAD_BUT_NO_INTERSECTION"
                )
            else:
                result["road_intersection_type"] = "NO_INTERSECTION"
                result["road_connection_screen"] = "ROAD_GAP_REMAINS"

            # Sample along the complete geometry at approximately 5 m intervals.
            route_length = float(geom.length)
            number_samples = max(
                2, int(math.ceil(route_length / SAMPLE_SPACING_M)) + 1
            )
            sample_points = [
                geom.interpolate(i / (number_samples - 1), normalized=True)
                for i in range(number_samples)
            ]
            result["raster_sample_count"] = len(sample_points)

            mask_values = raster_samples(mask_ds, sample_points)
            cost_values = raster_samples(cost_ds, sample_points)
            wc_values = raster_samples(wc_ds, sample_points)
            slope_values = raster_samples(slope_ds, sample_points)

            valid_mask = [v for v in mask_values if np.isfinite(v)]
            valid_cost = [v for v in cost_values if np.isfinite(v)]
            valid_wc = [v for v in wc_values if np.isfinite(v)]
            valid_slope = [v for v in slope_values if np.isfinite(v)]

            result["prohibited_mask_samples_value_1"] = sum(
                v == 1 for v in valid_mask
            )
            result["cost_valid_samples"] = len(valid_cost)
            result["cost_nodata_samples"] = (
                len(sample_points) - len(valid_cost)
            )
            result["builtup_worldcover_samples_class_50"] = sum(
                v == 50 for v in valid_wc
            )
            result["water_worldcover_samples_class_80"] = sum(
                v == 80 for v in valid_wc
            )

            if valid_slope:
                result["max_sampled_slope_degrees"] = max(valid_slope)
                result["slope_samples_over_25deg"] = sum(
                    v > SLOPE_LIMIT_DEG for v in valid_slope
                )

            # V4 parcel intersections must be calculated from V4 geometry.
            if parcels is not None:
                parcel_hits = parcels[parcels.geometry.intersects(geom)]
                result["parcel_intersection_count"] = len(parcel_hits)
                result["parcel_intersection_length_sum_m"] = sum(
                    float(geom.intersection(parcel_geom).length)
                    for parcel_geom in parcel_hits.geometry
                )
                result["parcel_screen_status"] = (
                    "INTERSECTIONS_FOUND"
                    if len(parcel_hits)
                    else "NO_INTERSECTION_FOUND"
                )

            records.append(result)
            output_geometries.append(geom)

    result_df = pd.DataFrame(records)
    result_gdf = gpd.GeoDataFrame(
        result_df, geometry=output_geometries, crs=routes.crs
    )

    # Write distinct outputs. Existing V3/V4 source layers are not modified.
    result_df.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")

    if OUT_GPKG.exists():
        OUT_GPKG.unlink()

    result_gdf.to_file(
        OUT_GPKG,
        layer="v4_connectivity_validation",
        driver="GPKG",
        index=False,
    )

    summary = result_df["road_connection_screen"].value_counts().to_dict()

    readme = [
        "DAMARAKUNTA V4 ROUTE CONNECTIVITY VALIDATION",
        "",
        f"Routes checked: {len(result_df)}",
        f"Mapped road tolerance (screening only): {ROAD_TOLERANCE_M} m",
        f"Facility distance tolerance (screening only): {FACILITY_TOLERANCE_M} m",
        f"Approximate raster sample spacing: {SAMPLE_SPACING_M} m",
        f"Global mask/cost NoData mismatch cells: {global_mask_cost_mismatches}",
        f"Road connection classifications: {summary}",
        "",
        "LIMITATIONS:",
        "- This script reads the V4 route_alternatives layer directly.",
        "- Raster samples are spaced approximately 5 m apart; not every pixel crossed is guaranteed to be sampled.",
        "- WorldCover 10 m classes do not verify individual roof/building clearance.",
        "- Geometric intersections do not prove navigable road-network topology.",
        "- Facility locations are not independently verified.",
        "- Ownership, legal right-of-way, drainage, road width, and construction feasibility are not established.",
        "- A near-road result is not equivalent to a connected route.",
        "- Outputs are preliminary GIS screening only.",
    ]
    OUT_README.write_text("\n".join(readme), encoding="utf-8")

    print("\n=== V4 ROUTE CONNECTIVITY VALIDATION COMPLETE ===")
    print("Routes checked:", len(result_df))
    print("Road connection screens:", summary)
    print("Global mask/cost mismatches:", global_mask_cost_mismatches)
    print("CSV:", OUT_CSV)
    print("GeoPackage:", OUT_GPKG)
    print("README:", OUT_README)
    print("\nIMPORTANT: These are preliminary screening results, not construction approval.")


if __name__ == "__main__":
    main()