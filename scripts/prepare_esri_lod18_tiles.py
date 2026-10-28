from pathlib import Path
import csv
import rasterio
from rasterio.windows import Window
from rasterio.transform import xy


# ============================================================
# INPUT / OUTPUT
# ============================================================

INPUT_RASTER = Path(
    r"D:\Telangana_Rural_Project\Siddipet\Angadi_Kistapur\aligned\angadi_kistapur_esri_reference_lod18_utm44n.tif"
)

OUTPUT_DIR = Path(
    r"D:\Telangana_Rural_Project\Siddipet\Angadi_Kistapur\aligned\esri_lod18_tiles_560"
)

MANIFEST = OUTPUT_DIR / "tile_manifest.csv"

TILE_SIZE = 560
OVERLAP = 112
STRIDE = TILE_SIZE - OVERLAP


# ============================================================
# CALCULATE TILE START POSITIONS
# ============================================================

def get_starts(length):
    starts = list(range(0, length - TILE_SIZE + 1, STRIDE))

    # Always include the final edge
    starts.append(length - TILE_SIZE)

    return sorted(set(starts))


# ============================================================
# MAIN
# ============================================================

def main():

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with rasterio.open(INPUT_RASTER) as src:

        width = src.width
        height = src.height

        print("Input raster:")
        print("  Width :", width)
        print("  Height:", height)
        print("  CRS   :", src.crs)
        print("  Bands :", src.count)
        print("  Dtype :", src.dtypes[0])
        print()

        xs = get_starts(width)
        ys = get_starts(height)

        print("X starts:", xs)
        print("Y starts:", ys)
        print("Total tiles:", len(xs) * len(ys))
        print()

        manifest_rows = []

        tile_number = 0

        for row, y in enumerate(ys):
            for col, x in enumerate(xs):

                tile_number += 1

                window = Window(
                    col_off=x,
                    row_off=y,
                    width=TILE_SIZE,
                    height=TILE_SIZE
                )

                data = src.read(window=window)

                transform = src.window_transform(window)

                tile_name = (
                    f"tile_{tile_number:03d}"
                    f"_r{row:02d}_c{col:02d}.tif"
                )

                tile_path = OUTPUT_DIR / tile_name

                profile = src.profile.copy()

                profile.update(
                    {
                        "driver": "GTiff",
                        "height": TILE_SIZE,
                        "width": TILE_SIZE,
                        "transform": transform,
                        "compress": "lzw"
                    }
                )

                with rasterio.open(tile_path, "w", **profile) as dst:
                    dst.write(data)

                # Geographic / projected center of tile
                center_x, center_y = xy(
                    transform,
                    TILE_SIZE / 2,
                    TILE_SIZE / 2
                )

                manifest_rows.append(
                    {
                        "tile_id": tile_number,
                        "filename": tile_name,
                        "row": row,
                        "col": col,
                        "x_start": x,
                        "y_start": y,
                        "width": TILE_SIZE,
                        "height": TILE_SIZE,
                        "center_utm_x": center_x,
                        "center_utm_y": center_y
                    }
                )

                print(
                    f"[{tile_number:02d}/{len(xs) * len(ys)}] "
                    f"{tile_name} "
                    f"x={x}, y={y}"
                )

        # ----------------------------------------------------
        # Write manifest
        # ----------------------------------------------------

        fieldnames = [
            "tile_id",
            "filename",
            "row",
            "col",
            "x_start",
            "y_start",
            "width",
            "height",
            "center_utm_x",
            "center_utm_y"
        ]

        with open(
            MANIFEST,
            "w",
            newline="",
            encoding="utf-8"
        ) as f:

            writer = csv.DictWriter(
                f,
                fieldnames=fieldnames
            )

            writer.writeheader()
            writer.writerows(manifest_rows)

    print()
    print("=" * 60)
    print("TILING COMPLETED")
    print("=" * 60)
    print("Tiles created :", len(manifest_rows))
    print("Tile size     :", TILE_SIZE, "x", TILE_SIZE)
    print("Overlap       :", OVERLAP)
    print("Stride        :", STRIDE)
    print("Output folder :", OUTPUT_DIR)
    print("Manifest      :", MANIFEST)


if __name__ == "__main__":
    main()