
from pathlib import Path
import geopandas as gpd

BASE = Path(r"D:\Telangana_Rural_Project\Siddipet\Damarakunta")
REF = BASE / "reference"
RESULTS = BASE / "results"
CRS = "EPSG:32644"

files = {
    "facilities": REF / "damarakunta_priority_facilities.gpkg",
    "roads": REF / "tgrac_road_network.gpkg",
    "routes": RESULTS / "damarakunta_validated_route_diagnostics.gpkg",
}

for name, path in files.items():
    print(f"\n{'=' * 70}\n{name.upper()}: {path}")
    if not path.exists():
        print("FILE NOT FOUND")
        continue

    try:
        gdf = gpd.read_file(path).to_crs(CRS)
        print("CRS:", gdf.crs)
        print("Features:", len(gdf))
        print("Columns:", list(gdf.columns))

        if name == "facilities":
            print(gdf.drop(columns="geometry").to_string(index=False))
            for _, row in gdf.iterrows():
                geom = row.geometry
                print(
                    "FACILITY:",
                    row.get("facility_name", "Unknown"),
                    "| coordinates:",
                    geom.wkt if geom else None,
                )

        elif name == "roads":
            print("Road geometry types:", gdf.geom_type.value_counts().to_dict())
            print("Total feature length (m):", round(gdf.length.sum(), 2))

        elif name == "routes":
            cols = [
                c for c in [
                    "facility_name", "path_length_m", "status",
                    "start_distance_to_road_m", "end_distance_to_road_m",
                    "geometry"
                ] if c in gdf.columns
            ]
            print(gdf[cols].to_string(index=False))

            roads = gpd.read_file(files["roads"]).to_crs(CRS)
            road_union = roads.geometry.union_all()

            for _, row in gdf.iterrows():
                geom = row.geometry
                if geom is None or geom.is_empty:
                    continue
                print(
                    row.get("facility_name", "Unknown"),
                    "| route length:", round(geom.length, 2), "m",
                    "| start-to-road:", round(
                        geom.boundary.geoms[0].distance(road_union), 2
                    ) if geom.geom_type == "LineString" else "check geometry",
                    "| end-to-road:", round(
                        geom.boundary.geoms[-1].distance(road_union), 2
                    ) if geom.geom_type == "LineString" else "check geometry",
                )

    except Exception as exc:
        print("ERROR:", repr(exc))

print("\nInspection complete. No files were modified.")
