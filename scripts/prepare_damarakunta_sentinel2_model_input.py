import os
import numpy as np
import rasterio

# ---------------------------------------------------------
# PATHS
# ---------------------------------------------------------

PROJECT = r"D:\Telangana_Rural_Project"

INPUT_FILE = os.path.join(
    PROJECT,
    r"Siddipet\Damarakunta\raw\imagery\sentinel2_20260429\damarakunta_sentinel2_RGB_B04_B03_B02_10m.tif"
)

OUTPUT_FILE = os.path.join(
    PROJECT,
    r"Siddipet\Damarakunta\aligned\damarakunta_sentinel2_model_rgb_uint8.tif"
)

os.makedirs(
    os.path.dirname(OUTPUT_FILE),
    exist_ok=True
)

# ---------------------------------------------------------
# SENTINEL-2 L2A REFLECTANCE SCALE
# ---------------------------------------------------------

REFLECTANCE_SCALE = 10000.0

print("=" * 60)
print("DAMARAKUNTA SENTINEL-2 MODEL INPUT PREPARATION")
print("=" * 60)

print("\nInput:")
print(INPUT_FILE)

print("\nOutput:")
print(OUTPUT_FILE)

# ---------------------------------------------------------
# READ INPUT
# ---------------------------------------------------------

with rasterio.open(INPUT_FILE) as src:

    print("\nINPUT INSPECTION")
    print("Width:", src.width)
    print("Height:", src.height)
    print("Bands:", src.count)
    print("CRS:", src.crs)
    print("Resolution:", src.res)
    print("Dtype:", src.dtypes)
    print("Descriptions:", src.descriptions)

    data = src.read()

    profile = src.profile.copy()

# ---------------------------------------------------------
# CONVERT UINT16 REFLECTANCE TO UINT8
# ---------------------------------------------------------

print("\nCONVERTING UINT16 REFLECTANCE TO UINT8")

print("Reflectance scale:", REFLECTANCE_SCALE)

data_float = data.astype(np.float32)

# Convert Sentinel-2 scaled reflectance to 0-255
data_uint8 = np.clip(
    (data_float / REFLECTANCE_SCALE) * 255.0,
    0,
    255
).astype(np.uint8)

# ---------------------------------------------------------
# OUTPUT PROFILE
# ---------------------------------------------------------

profile.update(
    dtype="uint8",
    count=3,
    compress="deflate",
    predictor=2
)

# ---------------------------------------------------------
# SAVE MODEL INPUT
# ---------------------------------------------------------

with rasterio.open(
    OUTPUT_FILE,
    "w",
    **profile
) as dst:

    dst.write(data_uint8)

    dst.set_band_description(
        1,
        "B04 Red 10m uint8"
    )

    dst.set_band_description(
        2,
        "B03 Green 10m uint8"
    )

    dst.set_band_description(
        3,
        "B02 Blue 10m uint8"
    )

    dst.update_tags(
        source="Copernicus Sentinel-2 L2A",
        scene_id=(
            "S2A_MSIL2A_20260429T051241_R019_"
            "T43QHV_20260429T102710"
        ),
        conversion="uint16 reflectance to uint8",
        reflectance_scale="10000",
        spatial_resolution="10m",
        model_preprocessing="uint8 values 0-255"
    )

# ---------------------------------------------------------
# VERIFY OUTPUT
# ---------------------------------------------------------

print("\n" + "=" * 60)
print("OUTPUT INSPECTION")
print("=" * 60)

with rasterio.open(OUTPUT_FILE) as src:

    print("Width:", src.width)
    print("Height:", src.height)
    print("Bands:", src.count)
    print("CRS:", src.crs)
    print("Resolution:", src.res)
    print("Dtype:", src.dtypes)
    print("Bounds:", src.bounds)
    print("Descriptions:", src.descriptions)

    for i in range(1, src.count + 1):

        band = src.read(i)

        print(
            f"Band {i}: "
            f"min={band.min()} "
            f"max={band.max()} "
            f"mean={band.mean():.2f}"
        )

print("\n" + "=" * 60)
print("STATUS: MODEL-COMPATIBLE RGB CREATED")
print("=" * 60)