import os
import numpy as np
import rasterio
from PIL import Image

PROJECT_ROOT = r"D:\Telangana_Rural_Project"

INPUT_FILE = os.path.join(
    PROJECT_ROOT,
    "Siddipet",
    "Damarakunta",
    "raw",
    "imagery",
    "damarakunta_sentinel_feb2022.tif"
)

OUTPUT_DIR = os.path.join(
    PROJECT_ROOT,
    "Siddipet",
    "Damarakunta",
    "aligned"
)

OUTPUT_FILE = os.path.join(
    OUTPUT_DIR,
    "damarakunta_model_input_rgb.tif"
)

print("=" * 80)
print("PHASE 25 - STEP 11H")
print("PREPARE DAMARAKUNTA IMAGERY FOR MODEL INPUT")
print("=" * 80)

if not os.path.isfile(INPUT_FILE):
    print("\n[ERROR] Input imagery not found:")
    print(INPUT_FILE)
    raise SystemExit(1)

os.makedirs(OUTPUT_DIR, exist_ok=True)

with rasterio.open(INPUT_FILE) as src:

    print("\nINPUT INFORMATION")
    print("-" * 80)
    print("Input file:", INPUT_FILE)
    print("Width:", src.width)
    print("Height:", src.height)
    print("Bands:", src.count)
    print("CRS:", src.crs)
    print("Resolution:", src.res)
    print("Data types:", src.dtypes)

    data = src.read()

    if src.count != 3:
        print("\n[ERROR] Expected 3 RGB bands.")
        raise SystemExit(1)

    rgb = np.transpose(data, (1, 2, 0))

    print("\nRGB ARRAY")
    print("-" * 80)
    print("Shape:", rgb.shape)
    print("Data type:", rgb.dtype)
    print("Minimum:", int(rgb.min()))
    print("Maximum:", int(rgb.max()))

    # Convert to uint8 RGB
    rgb = np.clip(rgb, 0, 255).astype(np.uint8)

    print("\nNORMALIZATION")
    print("-" * 80)
    print("Output type: uint8")
    print("Value range: 0-255")
    print("Normalization: RGB values retained in 8-bit range")

    profile = src.profile.copy()

    profile.update(
        driver="GTiff",
        dtype="uint8",
        count=3,
        compress="lzw",
        nodata=None
    )

    with rasterio.open(OUTPUT_FILE, "w", **profile) as dst:
        dst.write(np.transpose(rgb, (2, 0, 1)))

print("\nOUTPUT INFORMATION")
print("-" * 80)

with rasterio.open(OUTPUT_FILE) as out:

    print("Output file:", OUTPUT_FILE)
    print("Width:", out.width)
    print("Height:", out.height)
    print("Bands:", out.count)
    print("CRS:", out.crs)
    print("Resolution:", out.res)
    print("Data types:", out.dtypes)
    print("Bounds:", out.bounds)
    print(
        "File size:",
        round(os.path.getsize(OUTPUT_FILE) / (1024 * 1024), 2),
        "MB"
    )

print("\n" + "=" * 80)
print("STATUS: DAMARAKUNTA MODEL INPUT PREPARATION COMPLETED.")
print("=" * 80)

print("\nPHASE 25 STEP 11H COMPLETED.")