import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling

input_path = r"D:\Telangana_Rural_Project\Siddipet\Angadi_Kistapur\aligned\angadi_kistapur_worldcover.tif"

output_path = r"D:\Telangana_Rural_Project\Siddipet\Angadi_Kistapur\aligned\angadi_kistapur_worldcover_utm44n.tif"

target_crs = "EPSG:32644"

print("Reading WorldCover...")
with rasterio.open(input_path) as src:

    transform, width, height = calculate_default_transform(
        src.crs,
        target_crs,
        src.width,
        src.height,
        *src.bounds
    )

    profile = src.profile.copy()

    profile.update(
        crs=target_crs,
        transform=transform,
        width=width,
        height=height,
        nodata=0,
        compress="lzw"
    )

    print("Reprojecting to EPSG:32644...")

    with rasterio.open(output_path, "w", **profile) as dst:

        reproject(
            source=rasterio.band(src, 1),
            destination=rasterio.band(dst, 1),
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=transform,
            dst_crs=target_crs,
            src_nodata=0,
            dst_nodata=0,
            resampling=Resampling.nearest
        )

print()
print("DONE")
print("Output:", output_path)
print("Size:", width, "x", height)