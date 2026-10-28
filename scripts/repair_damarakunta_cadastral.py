import geopandas as gpd

INPUT = r"D:\Telangana_Rural_Project\Siddipet\Damarakunta\reference\damarakunta_cadastral.gpkg"
OUTPUT = r"D:\Telangana_Rural_Project\Siddipet\Damarakunta\reference\damarakunta_cadastral_valid.gpkg"

gdf = gpd.read_file(INPUT)

print("Input records:", len(gdf))
print("Invalid before:", (~gdf.geometry.is_valid).sum())

gdf["geometry"] = gdf.geometry.make_valid()

print("Invalid after:", (~gdf.geometry.is_valid).sum())

gdf.to_file(
    OUTPUT,
    layer="cadastral",
    driver="GPKG"
)

print("Saved:", OUTPUT)
print("Records saved:", len(gdf))