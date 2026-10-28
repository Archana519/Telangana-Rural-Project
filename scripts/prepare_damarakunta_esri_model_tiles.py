from pathlib import Path

import math
import numpy as np
import rasterio
from rasterio.windows import Window


# ============================================================
# INPUT / OUTPUT
# ============================================================

input_file = Path(
    "Siddipet/Damarakunta/aligned/"
    "damarakunta_esri_highres_mosaic_0p6m.tif"
)

output_dir = Path(
    "Siddipet/Damarakunta/predictions/"
    "esri_model_input_tiles"
)

output_dir.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# MODEL INPUT SIZE
# ============================================================

TILE_SIZE = 560


print("=" * 70)
print("DAMARAKUNTA ESRI MODEL TILE PREPARATION")
print("=" * 70)


# ============================================================
# OPEN MOSAIC
# ============================================================

with rasterio.open(input_file) as src:

    print()
    print("Input:")
    print(input_file)

    print()
    print("Mosaic size:")
    print(src.width, "x", src.height)

    print("Bands:", src.count)
    print("CRS:", src.crs)
    print("Resolution:", src.res)
    print("Dtype:", src.dtypes)

    if src.count < 3:
        raise RuntimeError(
            "The mosaic does not contain 3 RGB bands."
        )

    if src.crs is None:
        raise RuntimeError(
            "The mosaic has no CRS."
        )

    # --------------------------------------------------------
    # TILE GRID
    # --------------------------------------------------------

    columns = math.ceil(
        src.width / TILE_SIZE
    )

    rows = math.ceil(
        src.height / TILE_SIZE
    )

    total_tiles = rows * columns

    print()
    print("Tile size:", TILE_SIZE, "x", TILE_SIZE)
    print("Columns:", columns)
    print("Rows:", rows)
    print("Total tiles:", total_tiles)


    # --------------------------------------------------------
    # CREATE TILES
    # --------------------------------------------------------

    tile_number = 0

    for row in range(rows):

        for col in range(columns):

            tile_number += 1

            xoff = col * TILE_SIZE
            yoff = row * TILE_SIZE

            actual_width = min(
                TILE_SIZE,
                src.width - xoff
            )

            actual_height = min(
                TILE_SIZE,
                src.height - yoff
            )

            window = Window(
                xoff,
                yoff,
                actual_width,
                actual_height
            )

            data = src.read(
                [1, 2, 3],
                window=window
            )

            # ------------------------------------------------
            # PAD EDGE TILES
            # ------------------------------------------------

            padded = np.zeros(
                (
                    3,
                    TILE_SIZE,
                    TILE_SIZE
                ),
                dtype=np.uint8
            )

            padded[
                :,
                :actual_height,
                :actual_width
            ] = data.astype(
                np.uint8
            )

            # ------------------------------------------------
            # GEOREFERENCE
            # ------------------------------------------------

            transform = rasterio.windows.transform(
                window,
                src.transform
            )

            output_file = (
                output_dir
                / f"tile_{tile_number:04d}.tif"
            )

            profile = {

                "driver": "GTiff",

                "height": TILE_SIZE,

                "width": TILE_SIZE,

                "count": 3,

                "dtype": "uint8",

                "crs": src.crs,

                "transform": transform,

                "compress": "lzw",

            }

            with rasterio.open(
                output_file,
                "w",
                **profile
            ) as dst:

                dst.write(padded)

            print(
                f"Tile {tile_number:04d}/{total_tiles}: "
                f"source={actual_width}x{actual_height} "
                f"-> output=560x560"
            )


print()
print("=" * 70)
print("MODEL TILE PREPARATION COMPLETED")
print("=" * 70)

print()
print("Output directory:")
print(output_dir)