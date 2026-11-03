import os
import geopandas as gpd
import rasterio
from rasterio.mask import mask

PROJECT = r"D:\Telangana_Rural_Project"
VILLAGE = os.path.join(
    PROJECT,
    "Siddipet",
    "Angadi_Kistapur"
)

dem_path = os.path.join(
    VILLAGE,
    "raw",
    "dem",
    "n17_e078_1arc_v3.tif"
)

boundary_path = os.path.join(
    VILLAGE,
    "raw",
    "tgrac_master_admin",
    "village_boundary_20260930T115300Z.geojson"
)

output_path = os.path.join(
    VILLAGE,
    "aligned",
    "angadi_kistapur_dem.tif"
)

os.makedirs(os.path.dirname(output_path), exist_ok=True)

print("Reading village boundary...")
boundary = gpd.read_file(boundary_path)

print("Boundary CRS:", boundary.crs)

with rasterio.open(dem_path) as src:

    print("DEM CRS:", src.crs)
    print("DEM bounds:", src.bounds)

    # Reproject boundary to DEM CRS
    boundary = boundary.to_crs(src.crs)

    geometries = boundary.geometry.values

    print("Clipping DEM to village boundary...")

    clipped, transform = mask(
        src,
        geometries,
        crop=True
    )

    profile = src.profile.copy()

    profile.update(
        height=clipped.shape[1],
        width=clipped.shape[2],
        transform=transform,
        compress="lzw"
    )

    with rasterio.open(output_path, "w", **profile) as dst:
        dst.write(clipped)

print()
print("DONE")
print("Output:", output_path)