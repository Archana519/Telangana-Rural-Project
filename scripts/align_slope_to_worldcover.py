import rasterio
from rasterio.warp import reproject, Resampling

slope_path = r"D:\Telangana_Rural_Project\Siddipet\Angadi_Kistapur\aligned\angadi_kistapur_slope.tif"

reference_path = r"D:\Telangana_Rural_Project\Siddipet\Angadi_Kistapur\aligned\angadi_kistapur_worldcover_utm44n.tif"

output_path = r"D:\Telangana_Rural_Project\Siddipet\Angadi_Kistapur\aligned\angadi_kistapur_slope_utm44n_10m.tif"

print("Reading reference WorldCover grid...")

with rasterio.open(reference_path) as ref:

    width = ref.width
    height = ref.height
    transform = ref.transform
    crs = ref.crs

    profile = ref.profile.copy()

    profile.update(
        dtype="float32",
        count=1,
        nodata=-9999.0,
        compress="lzw"
    )

    print("Reference size:", width, "x", height)
    print("Reference resolution:", ref.res)
    print("Reference CRS:", crs)

    with rasterio.open(slope_path) as src:

        print("Reading slope...")
        print("Source CRS:", src.crs)
        print("Source size:", src.width, "x", src.height)

        destination = __import__("numpy").full(
            (height, width),
            -9999.0,
            dtype="float32"
        )

        print("Resampling slope to WorldCover grid...")

        reproject(
            source=src.read(1),
            destination=destination,
            src_transform=src.transform,
            src_crs=src.crs,
            src_nodata=-9999.0,
            dst_transform=transform,
            dst_crs=crs,
            dst_nodata=-9999.0,
            resampling=Resampling.bilinear
        )

    with rasterio.open(output_path, "w", **profile) as dst:
        dst.write(destination, 1)

print()
print("DONE")
print("Output:", output_path)
print("Size:", width, "x", height)