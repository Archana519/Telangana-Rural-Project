
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString

BASE = Path(r"D:\Telangana_Rural_Project\Siddipet\Damarakunta")
RESULTS = BASE / "results"
REF = BASE / "reference"
STUDY = BASE / "study_area"

ROUTES_FILE = RESULTS / "damarakunta_least_cost_access_routes.gpkg"
ROADS_FILE = REF / "tgrac_road_network.gpkg"
BOUNDARY_FILE = STUDY / "damarakunta_boundary.gpkg"

OUT_CSV = RESULTS / "damarakunta_route_validation.csv"
OUT_GPKG = RESULTS / "damarakunta_validated_route_diagnostics.gpkg"

CRS = "EPSG:32644"
ROAD_BUFFER_M = 5.0


def main():
    for path in [ROUTES_FILE, ROADS_FILE, BOUNDARY_FILE]:
        if not path.exists():
            raise FileNotFoundError(path)

    if OUT_CSV.exists() or OUT_GPKG.exists():
        raise FileExistsError(
            "A validation output already exists. Review or rename it first."
        )

    routes = gpd.read_file(ROUTES_FILE).to_crs(CRS)
    roads = gpd.read_file(ROADS_FILE).to_crs(CRS)
    boundary = gpd.read_file(BOUNDARY_FILE).to_crs(CRS)

    area = boundary.geometry.union_all()

    road_lines = [
        geom for geom in roads.geometry
        if geom is not None and not geom.is_empty
    ]
    road_union = gpd.GeoSeries(road_lines, crs=CRS).union_all()
    road_buffer = road_union.buffer(ROAD_BUFFER_M)

    records = []
    diagnostic_geometries = []

    print("=" * 70)
    print("DAMARAKUNTA ACCESS ROUTE VALIDATION")
    print("=" * 70)

    for _, route in routes.iterrows():
        geom = route.geometry
        if geom is None or geom.is_empty:
            continue

        start = geom.interpolate(0)
        end = geom.interpolate(geom.length)

        start_road_distance = start.distance(road_union)
        end_road_distance = end.distance(road_union)

        overlap_geom = geom.intersection(road_buffer)
        overlap_length = overlap_geom.length
        route_length = geom.length

        overlap_pct = (
            100.0 * min(overlap_length, route_length) / route_length
            if route_length > 0 else 0.0
        )

        inside_length = geom.intersection(area).length
        inside_pct = (
            100.0 * inside_length / route_length
            if route_length > 0 else 0.0
        )

        record = {
            "facility_id": route.get("facility_id"),
            "facility_name": route.get("facility_name"),
            "facility_type": route.get("facility_type"),
            "route_length_m": round(route_length, 2),
            "start_distance_to_road_m": round(start_road_distance, 2),
            "end_distance_to_road_m": round(end_road_distance, 2),
            "start_within_5m_of_road": start_road_distance <= ROAD_BUFFER_M,
            "end_within_5m_of_road": end_road_distance <= ROAD_BUFFER_M,
            "route_length_within_5m_road_buffer_m": round(
                min(overlap_length, route_length), 2
            ),
            "approx_overlap_percent": round(overlap_pct, 1),
            "route_inside_boundary_percent": round(inside_pct, 1),
            "geometry_valid": geom.is_valid,
        }
        records.append(record)

        diagnostic_geometries.append({
            "facility_id": str(route.get("facility_id")),
            "facility_name": route.get("facility_name"),
            "route_length_m": round(route_length, 2),
            "start_road_distance_m": round(start_road_distance, 2),
            "end_road_distance_m": round(end_road_distance, 2),
            "overlap_pct": round(overlap_pct, 1),
            "inside_pct": round(inside_pct, 1),
            "geometry": geom,
        })

    report = pd.DataFrame(records)
    report.to_csv(OUT_CSV, index=False)

    if diagnostic_geometries:
        diagnostic_gdf = gpd.GeoDataFrame(
            diagnostic_geometries, geometry="geometry", crs=CRS
        )
        diagnostic_gdf.to_file(
            OUT_GPKG, layer="route_diagnostics", driver="GPKG"
        )

    print(report.to_string(index=False))
    print("\nCSV:", OUT_CSV)
    print("GeoPackage:", OUT_GPKG)
    print(
        "\nNote: overlap uses a 5 m buffer around mapped roads, "
        "so it is approximate and is not proof that a route is redundant."
    )


if __name__ == "__main__":
    main()
