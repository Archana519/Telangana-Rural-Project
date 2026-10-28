from pathlib import Path
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling

ROOT = Path(r"D:\Telangana_Rural_Project\Siddipet\Angadi_Kistapur")

input_file = ROOT / "aligned" / "angadi_kistapur_full_village_georeferenced.tif"
output_file = ROOT / "aligned" / "angadi_kistapur_utm44n.tif"

src_crs = "EPSG:4326"
dst_crs = "EPSG:32644"

with rasterio.open(input_file) as src:

    transform, width, height = calculate_default_transform(
        src.crs,
        dst_crs,
        src.width,
        src.height,
        *src.bounds
    )

    profile = src.profile.copy()

    profile.update(
        crs=dst_crs,
        transform=transform,
        width=width,
        height=height,
        compress="deflate"
    )

    with rasterio.open(output_file, "w", **profile) as dst:

        for band in range(1, src.count + 1):

            reproject(
                source=rasterio.band(src, band),
                destination=rasterio.band(dst, band),
                src_transform=src.transform,
                src_crs=src.crs,
                dst_transform=transform,
                dst_crs=dst_crs,
                resampling=Resampling.bilinear
            )

print("=== UTM REPROJECTION ===")
print("Input :", input_file)
print("Output:", output_file)
print("Source CRS:", src_crs)
print("Target CRS:", dst_crs)
print("STATUS: UTM GeoTIFF created successfully")