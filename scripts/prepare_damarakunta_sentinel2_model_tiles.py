import os
import math
import rasterio
from rasterio.windows import Window

# ---------------------------------------------------------
# PATHS
# ---------------------------------------------------------

PROJECT = r"D:\Telangana_Rural_Project"

INPUT_FILE = os.path.join(
    PROJECT,
    r"Siddipet\Damarakunta\aligned\damarakunta_sentinel2_model_rgb_uint8.tif"
)

OUTPUT_DIR = os.path.join(
    PROJECT,
    r"Siddipet\Damarakunta\predictions\sentinel2_input_tiles"
)

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ---------------------------------------------------------
# MODEL TILE SIZE
# ---------------------------------------------------------

TILE_SIZE = 560

# ---------------------------------------------------------
# START
# ---------------------------------------------------------

print("=" * 60)
print("DAMARAKUNTA SENTINEL-2 MODEL TILING")
print("=" * 60)

print("\nInput:")
print(INPUT_FILE)

print("\nOutput directory:")
print(OUTPUT_DIR)

# ---------------------------------------------------------
# OPEN INPUT
# ---------------------------------------------------------

with rasterio.open(INPUT_FILE) as src:

    print("\nINPUT INSPECTION")
    print("Width:", src.width)
    print("Height:", src.height)
    print("Bands:", src.count)
    print("CRS:", src.crs)
    print("Resolution:", src.res)
    print("Dtype:", src.dtypes)

    width = src.width
    height = src.height

    # -----------------------------------------------------
    # CALCULATE TILE GRID
    # -----------------------------------------------------

    cols = math.ceil(width / TILE_SIZE)
    rows = math.ceil(height / TILE_SIZE)

    total_tiles = rows * cols

    print("\nTILE SIZE:")
    print(f"{TILE_SIZE} x {TILE_SIZE}")

    print("Columns:", cols)
    print("Rows:", rows)
    print("Total tiles:", total_tiles)

    tile_number = 0

    # -----------------------------------------------------
    # CREATE TILES
    # -----------------------------------------------------

    for row in range(rows):

        for col in range(cols):

            tile_number += 1

            xoff = col * TILE_SIZE
            yoff = row * TILE_SIZE

            read_width = min(
                TILE_SIZE,
                width - xoff
            )

            read_height = min(
                TILE_SIZE,
                height - yoff
            )

            window = Window(
                xoff,
                yoff,
                read_width,
                read_height
            )

            data = src.read(
                window=window
            )

            # -------------------------------------------------
            # CREATE 560 x 560 CANVAS
            # -------------------------------------------------

            padded = data.newbyteorder() if hasattr(
                data,
                "newbyteorder"
            ) else data

            import numpy as np

            padded = np.zeros(
                (
                    src.count,
                    TILE_SIZE,
                    TILE_SIZE
                ),
                dtype=data.dtype
            )

            padded[
                :,
                :read_height,
                :read_width
            ] = data

            # -------------------------------------------------
            # TILE TRANSFORM
            # -------------------------------------------------

            transform = src.window_transform(
                window
            )

            # -------------------------------------------------
            # OUTPUT PROFILE
            # -------------------------------------------------

            profile = src.profile.copy()

            profile.update(
                driver="GTiff",
                width=TILE_SIZE,
                height=TILE_SIZE,
                count=src.count,
                dtype="uint8",
                transform=transform,
                compress="deflate"
            )

            # -------------------------------------------------
            # OUTPUT FILE
            # -------------------------------------------------

            tile_name = (
                f"tile_{tile_number - 1:03d}.tif"
            )

            tile_path = os.path.join(
                OUTPUT_DIR,
                tile_name
            )

            # -------------------------------------------------
            # SAVE TILE
            # -------------------------------------------------

            with rasterio.open(
                tile_path,
                "w",
                **profile
            ) as dst:

                dst.write(padded)

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
                    tile_size="560x560",
                    original_width=str(read_width),
                    original_height=str(read_height),
                    padded=str(
                        read_width != TILE_SIZE
                        or read_height != TILE_SIZE
                    )
                )

            print(
                f"Created {tile_name}: "
                f"source={read_width}x{read_height} "
                f"output=560x560"
            )

# ---------------------------------------------------------
# FINAL VERIFICATION
# ---------------------------------------------------------

print("\n" + "=" * 60)
print("VERIFYING CREATED TILES")
print("=" * 60)

tile_files = sorted(
    [
        f
        for f in os.listdir(OUTPUT_DIR)
        if f.lower().endswith(".tif")
    ]
)

print("TIFF tiles found:", len(tile_files))

if len(tile_files) != total_tiles:
    raise RuntimeError(
        f"Expected {total_tiles} tiles, "
        f"but found {len(tile_files)}."
    )

# ---------------------------------------------------------
# INSPECT FIRST TILE
# ---------------------------------------------------------

sample_tile = os.path.join(
    OUTPUT_DIR,
    tile_files[0]
)

with rasterio.open(sample_tile) as src:

    print("\nSAMPLE TILE:")
    print("File:", tile_files[0])
    print("Width:", src.width)
    print("Height:", src.height)
    print("Bands:", src.count)
    print("CRS:", src.crs)
    print("Resolution:", src.res)
    print("Dtype:", src.dtypes)
    print("Bounds:", src.bounds)
    print("Descriptions:", src.descriptions)

    if (
        src.width != TILE_SIZE
        or src.height != TILE_SIZE
    ):
        raise RuntimeError(
            "Sample tile is not 560 x 560."
        )

print("\n" + "=" * 60)
print("STATUS: SENTINEL-2 MODEL TILING COMPLETED")
print("=" * 60)