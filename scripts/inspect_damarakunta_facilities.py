
from pathlib import Path
import geopandas as gpd

base = Path(r"D:\Telangana_Rural_Project\Siddipet\Damarakunta")
reference = base / "reference"

files = [
    "school_compounds_utm44n.gpkg",
    "tgrac_health.gpkg",
    "tgrac_sub_centres.gpkg",
    "tgrac_anganwadi.gpkg",
]

for filename in files:
    path = reference / filename
    print("\n" + "=" * 65)
    print(filename)

    if not path.exists():
        print("FILE NOT FOUND")
        continue

    gdf = gpd.read_file(path)
    print("CRS:", gdf.crs)
    print("Feature count:", len(gdf))
    print("Geometry types:", gdf.geometry.geom_type.value_counts().to_dict())
    print("Columns:", list(gdf.columns))

    if len(gdf):
        print(gdf.drop(columns="geometry").to_string(index=False))

        projected = gdf.to_crs("EPSG:32644")
        for idx, geom in projected.geometry.items():
            if geom is not None and not geom.is_empty:
                point = geom if geom.geom_type == "Point" else geom.representative_point()
                print(
                    f"Feature {idx}: representative point "
                    f"E={point.x:.2f} m, N={point.y:.2f} m"
                )

print("\nInspection complete. No files were changed.")
