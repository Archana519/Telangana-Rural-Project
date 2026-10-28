import os
import numpy as np
import rasterio
from rasterio.windows import Window

PROJECT_ROOT = r"D:\Telangana_Rural_Project"

INPUT_FILE = os.path.join(
    PROJECT_ROOT,
    "Siddipet",
    "Damarakunta",
    "aligned",
    "damarakunta_model_input_rgb.tif"
)

OUTPUT_DIR = os.path.join(
    PROJECT_ROOT,
    "Siddipet",
    "Damarakunta",
    "predictions",
    "input_tiles"
)

TILE_SIZE = 560

print("=" * 80)
print("PHASE 25 - STEP 11I")
print("CREATE DAMARAKUNTA MODEL TILES")
print("=" * 80)

if not os.path.isfile(INPUT_FILE):
    print("\n[ERROR] Model input file not found:")
    print(INPUT_FILE)
    raise SystemExit(1)

os.makedirs(OUTPUT_DIR, exist_ok=True)

with rasterio.open(INPUT_FILE) as src:

    print("\nINPUT")
    print("-" * 80)
    print("File:", INPUT_FILE)
    print("Width:", src.width)
    print("Height:", src.height)
    print("Bands:", src.count)
    print("CRS:", src.crs)
    print("Resolution:", src.res)

    if src.count != 3:
        print("\n[ERROR] Expected 3 RGB bands.")
        raise SystemExit(1)

    width = src.width
    height = src.height

    tile_count = 0

    for y in range(0, height, TILE_SIZE):

        for x in range(0, width, TILE_SIZE):

            read_width = min(TILE_SIZE, width - x)
            read_height = min(TILE_SIZE, height - y)

            window = Window(
                x,
                y,
                read_width,
                read_height
            )

            data = src.read(
                indexes=[1, 2, 3],
                window=window
            )

            # Pad edge tiles to exactly 560 x 560
            padded = np.zeros(
                (3, TILE_SIZE, TILE_SIZE),
                dtype=np.uint8
            )

            padded[
                :,
                :read_height,
                :read_width
            ] = data

            tile_name = f"tile_{tile_count:03d}.tif"

            output_file = os.path.join(
                OUTPUT_DIR,
                tile_name
            )

            transform = rasterio.windows.transform(
                window,
                src.transform
            )

            profile = src.profile.copy()

            profile.update(
                driver="GTiff",
                width=TILE_SIZE,
                height=TILE_SIZE,
                count=3,
                dtype="uint8",
                transform=transform,
                compress="lzw",
                nodata=0
            )

            with rasterio.open(
                output_file,
                "w",
                **profile
            ) as dst:

                dst.write(padded)

            tile_count += 1

print("\nTILING INFORMATION")
print("-" * 80)
print("Tile size:", TILE_SIZE, "x", TILE_SIZE)
print("Total tiles:", tile_count)
print("Output directory:", OUTPUT_DIR)

print("\nTILE CHECK")
print("-" * 80)

tile_files = sorted(
    [
        f for f in os.listdir(OUTPUT_DIR)
        if f.lower().endswith(".tif")
    ]
)

print("TIFF files found:", len(tile_files))

if tile_files:

    sample_file = os.path.join(
        OUTPUT_DIR,
        tile_files[0]
    )

    with rasterio.open(sample_file) as sample:

        print("\nSample tile:", tile_files[0])
        print("Width:", sample.width)
        print("Height:", sample.height)
        print("Bands:", sample.count)
        print("CRS:", sample.crs)
        print("Data types:", sample.dtypes)
        print("Bounds:", sample.bounds)

        if (
            sample.width == TILE_SIZE
            and sample.height == TILE_SIZE
            and sample.count == 3
        ):
            print("Sample tile format: VALID")
        else:
            print("Sample tile format: INVALID")

print("\n" + "=" * 80)

if tile_count > 0 and len(tile_files) == tile_count:
    print("STATUS: DAMARAKUNTA MODEL TILING COMPLETED.")
else:
    print("STATUS: TILE OUTPUT REQUIRES INSPECTION.")

print("=" * 80)

print("\nPHASE 25 STEP 11I COMPLETED.")