import time
import requests
import rasterio
import numpy as np
from pathlib import Path
from rasterio.transform import from_bounds
from rasterio.crs import CRS


# =========================================================
# TILE 12 BOUNDARY
# =========================================================

xmin = 264214.8855999997
ymin = 1960209.3078000005
xmax = 265592.3487999998
ymax = 1960912.0879999995


# =========================================================
# OUTPUT
# =========================================================

output_dir = Path(
    "Siddipet/Damarakunta/raw/imagery/"
    "esri_full_tiles/tile12_parts"
)

output_dir.mkdir(
    parents=True,
    exist_ok=True
)


# =========================================================
# ESRI EXPORT URL
# =========================================================

export_url = (
    "https://services.arcgisonline.com/"
    "ArcGIS/rest/services/World_Imagery/MapServer/export"
)


# =========================================================
# SPLIT TILE 12
# =========================================================

parts = 2

x_size = (xmax - xmin) / parts
y_size = (ymax - ymin) / parts

# 900 m approximately / 1500 pixels = 0.6 m/pixel
pixels = 1500


print("=" * 65)
print("DAMARAKUNTA TILE 12 SMALL-PART EXPORT")
print("=" * 65)

print()
print("Tile 12 bounds:")
print(xmin, ymin, xmax, ymax)

print()
print(
    "Part ground size:",
    x_size,
    "x",
    y_size,
    "m"
)

print(
    "Requested pixels:",
    pixels,
    "x",
    pixels
)

print(
    "Expected resolution:",
    x_size / pixels,
    "m/pixel"
)


# =========================================================
# HTTP SESSION
# =========================================================

session = requests.Session()

session.headers.update(
    {
        "User-Agent":
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "Chrome/154.0 Safari/537.36"
    }
)


# =========================================================
# EXPORT 4 PARTS
# =========================================================

part_number = 0

for row in range(parts):

    for col in range(parts):

        part_number += 1

        part_xmin = (
            xmin + col * x_size
        )

        part_xmax = (
            xmin + (col + 1) * x_size
        )

        part_ymin = (
            ymin + row * y_size
        )

        part_ymax = (
            ymin + (row + 1) * y_size
        )

        output_file = (
            output_dir
            / f"tile12_part_{part_number:02d}.tif"
        )

        print()
        print("-" * 65)

        print(
            "Part:",
            part_number,
            "/ 4"
        )

        print(
            "BBOX:",
            part_xmin,
            part_ymin,
            part_xmax,
            part_ymax
        )

        # -------------------------------------------------
        # SKIP VALID EXISTING PART
        # -------------------------------------------------

        if output_file.exists():

            try:

                with rasterio.open(
                    output_file
                ) as check:

                    if (
                        check.crs
                        and check.count >= 3
                        and check.width > 0
                        and check.height > 0
                    ):

                        print(
                            "Valid existing part."
                        )

                        print(
                            "Skipping."
                        )

                        continue

            except Exception:
                pass

        # -------------------------------------------------
        # REQUEST
        # -------------------------------------------------

        params = {

            "bbox": (
                f"{part_xmin},"
                f"{part_ymin},"
                f"{part_xmax},"
                f"{part_ymax}"
            ),

            "bboxSR": "32644",

            "imageSR": "32644",

            "size": (
                f"{pixels},"
                f"{pixels}"
            ),

            "format": "tiff",

            "transparent": "false",

            "f": "image",
        }

        success = False

        for attempt in range(1, 6):

            print(
                "Attempt:",
                attempt,
                "/ 5"
            )

            try:

                response = session.get(
                    export_url,
                    params=params,
                    timeout=180
                )

                print(
                    "HTTP status:",
                    response.status_code
                )

                print(
                    "Bytes:",
                    len(response.content)
                )

                if response.status_code == 200:

                    success = True
                    break

                print(
                    response.text[:500]
                )

            except requests.exceptions.RequestException as e:

                print(
                    "Network error:",
                    e
                )

            if attempt < 5:

                time.sleep(10)

        if not success:

            raise RuntimeError(
                f"Tile 12 part {part_number} "
                "failed after 5 attempts."
            )

        # -------------------------------------------------
        # READ RETURNED IMAGE
        # -------------------------------------------------

        data = None

        temporary_file = (
            output_dir
            / f"raw_tile12_part_{part_number:02d}.tif"
        )

        temporary_file.write_bytes(
            response.content
        )

        with rasterio.open(
            temporary_file
        ) as src:

            data = src.read()

            print(
                "Returned:",
                src.width,
                "x",
                src.height
            )

            print(
                "Bands:",
                src.count
            )

            print(
                "Dtypes:",
                src.dtypes
            )

        # -------------------------------------------------
        # GEOREFERENCE
        # -------------------------------------------------

        height = data.shape[1]
        width = data.shape[2]

        transform = from_bounds(
            part_xmin,
            part_ymin,
            part_xmax,
            part_ymax,
            width,
            height
        )

        profile = {

            "driver": "GTiff",

            "height": height,

            "width": width,

            "count": data.shape[0],

            "dtype": data.dtype,

            "crs": CRS.from_epsg(
                32644
            ),

            "transform": transform,

            "compress": "lzw",
        }

        with rasterio.open(
            output_file,
            "w",
            **profile
        ) as dst:

            dst.write(data)

        # -------------------------------------------------
        # VERIFY
        # -------------------------------------------------

        with rasterio.open(
            output_file
        ) as check:

            print()
            print("Verification:")
            print(
                "CRS:",
                check.crs
            )

            print(
                "Resolution:",
                check.res
            )

            print(
                "Size:",
                check.width,
                "x",
                check.height
            )

            print(
                "Bands:",
                check.count
            )

            print(
                "Bounds:",
                check.bounds
            )

        print()
        print(
            "Part",
            part_number,
            "completed."
        )


print()
print("=" * 65)
print("TILE 12 PART EXPORT COMPLETED")
print("=" * 65)

print()
print("Output:")
print(output_dir)