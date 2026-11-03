import time
import requests
import rasterio
import numpy as np
from pathlib import Path
from rasterio.transform import from_bounds
from rasterio.crs import CRS
import geopandas as gpd


# =========================================================
# PATHS
# =========================================================

boundary_file = Path(
    "Siddipet/Damarakunta/study_area/damarakunta_boundary.gpkg"
)

output_dir = Path(
    "Siddipet/Damarakunta/raw/imagery/esri_full_tiles"
)

output_dir.mkdir(parents=True, exist_ok=True)


# =========================================================
# ESRI WORLD IMAGERY EXPORT
# =========================================================

export_url = (
    "https://services.arcgisonline.com/"
    "ArcGIS/rest/services/World_Imagery/MapServer/export"
)


# =========================================================
# READ OFFICIAL DAMARAKUNTA BOUNDARY
# =========================================================

gdf = gpd.read_file(boundary_file)

if gdf.empty:
    raise RuntimeError(
        "Damarakunta boundary is empty."
    )

gdf = gdf.to_crs("EPSG:32644")

bounds = gdf.total_bounds

xmin, ymin, xmax, ymax = bounds


print("Damarakunta boundary")
print("--------------------")
print("xmin:", xmin)
print("ymin:", ymin)
print("xmax:", xmax)
print("ymax:", ymax)

print()
print(
    "Width:",
    xmax - xmin,
    "m"
)

print(
    "Height:",
    ymax - ymin,
    "m"
)


# =========================================================
# TILE SETTINGS
# =========================================================

# Each tile covers approximately:
# 1800 m x 1800 m
#
# Requested image:
# 3000 x 3000 pixels
#
# Resolution:
# 1800 / 3000 = 0.60 m/pixel

tile_ground_size = 1800.0
tile_pixels = 3000

expected_resolution = (
    tile_ground_size / tile_pixels
)

x_count = int(
    np.ceil(
        (xmax - xmin)
        / tile_ground_size
    )
)

y_count = int(
    np.ceil(
        (ymax - ymin)
        / tile_ground_size
    )
)


print()
print("Tile size:", tile_ground_size, "m")
print(
    "Pixels:",
    tile_pixels,
    "x",
    tile_pixels
)

print(
    "Expected resolution:",
    expected_resolution
)

print(
    "Columns:",
    x_count
)

print(
    "Rows:",
    y_count
)

print(
    "Total tiles:",
    x_count * y_count
)


# =========================================================
# REQUEST SETTINGS
# =========================================================

max_retries = 5

retry_wait_seconds = 10

request_timeout = 180


# =========================================================
# CREATE HTTP SESSION
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
# HELPER FUNCTION
# =========================================================

def validate_existing_tile(
    tile_file,
    expected_crs="EPSG:32644"
):

    try:

        with rasterio.open(tile_file) as src:

            if src.width <= 0:
                return False

            if src.height <= 0:
                return False

            if src.count < 3:
                return False

            if src.crs is None:
                return False

            if src.crs.to_string() != expected_crs:
                return False

            if not np.isfinite(src.res[0]):
                return False

            if not np.isfinite(src.res[1]):
                return False

            return True

    except Exception:

        return False


# =========================================================
# DOWNLOAD TILES
# =========================================================

tile_number = 0

successful_tiles = 0
skipped_tiles = 0


for row in range(y_count):

    for col in range(x_count):

        # -------------------------------------------------
        # CALCULATE TILE BOUNDING BOX
        # -------------------------------------------------

        tile_xmin = (
            xmin
            + col * tile_ground_size
        )

        tile_xmax = min(
            tile_xmin
            + tile_ground_size,
            xmax
        )

        tile_ymin = (
            ymin
            + row * tile_ground_size
        )

        tile_ymax = min(
            tile_ymin
            + tile_ground_size,
            ymax
        )

        tile_number += 1

        # -------------------------------------------------
        # FILE NAMES
        # -------------------------------------------------

        tile_name = (
            "damarakunta_esri_tile_"
            f"{tile_number:02d}.tif"
        )

        raw_file = (
            output_dir
            / f"raw_{tile_name}"
        )

        georef_file = (
            output_dir
            / tile_name
        )

        # -------------------------------------------------
        # TILE HEADER
        # -------------------------------------------------

        print()
        print("=" * 70)

        print(
            "Tile:",
            tile_number,
            "/",
            x_count * y_count
        )

        print(
            "Column:",
            col + 1,
            "/",
            x_count
        )

        print(
            "Row:",
            row + 1,
            "/",
            y_count
        )

        print(
            "BBOX:",
            tile_xmin,
            tile_ymin,
            tile_xmax,
            tile_ymax
        )

        # -------------------------------------------------
        # SKIP ALREADY COMPLETED TILE
        # -------------------------------------------------

        if georef_file.exists():

            print()
            print(
                "Tile already exists."
            )

            print(
                "Checking validity..."
            )

            if validate_existing_tile(
                georef_file
            ):

                print(
                    "VALID existing tile."
                )

                print(
                    "Skipping download."
                )

                skipped_tiles += 1

                continue

            else:

                print(
                    "Existing tile is invalid."
                )

                print(
                    "It will be downloaded again."
                )

        # -------------------------------------------------
        # ESRI REQUEST PARAMETERS
        # -------------------------------------------------

        params = {

            "bbox": (
                f"{tile_xmin},"
                f"{tile_ymin},"
                f"{tile_xmax},"
                f"{tile_ymax}"
            ),

            "bboxSR": "32644",

            "imageSR": "32644",

            "size": (
                f"{tile_pixels},"
                f"{tile_pixels}"
            ),

            "format": "tiff",

            "transparent": "false",

            "f": "image",
        }

        # -------------------------------------------------
        # DOWNLOAD WITH RETRIES
        # -------------------------------------------------

        response = None

        for attempt in range(
            1,
            max_retries + 1
        ):

            print()
            print(
                "Esri download attempt:",
                attempt,
                "/",
                max_retries
            )

            try:

                response = session.get(
                    export_url,
                    params=params,
                    timeout=request_timeout
                )

                print(
                    "HTTP status:",
                    response.status_code
                )

                print(
                    "Returned bytes:",
                    len(response.content)
                )

                if response.status_code == 200:

                    break

                print()
                print(
                    "Esri returned an error."
                )

                print(
                    response.text[:1000]
                )

            except requests.exceptions.RequestException as e:

                print()
                print(
                    "Network error:"
                )

                print(
                    str(e)
                )

            if attempt < max_retries:

                print()
                print(
                    "Waiting",
                    retry_wait_seconds,
                    "seconds before retry..."
                )

                time.sleep(
                    retry_wait_seconds
                )

        # -------------------------------------------------
        # CHECK DOWNLOAD RESULT
        # -------------------------------------------------

        if response is None:

            raise RuntimeError(
                f"No response received "
                f"for tile {tile_number}."
            )

        if response.status_code != 200:

            print()
            print(
                "Esri export failed "
                f"for tile {tile_number}."
            )

            print(
                "Final HTTP status:",
                response.status_code
            )

            print(
                "Response:"
            )

            print(
                response.text[:2000]
            )

            raise RuntimeError(
                "Stopping because the Esri "
                f"export failed for tile "
                f"{tile_number}."
            )

        # -------------------------------------------------
        # SAVE RAW TIFF
        # -------------------------------------------------

        raw_file.write_bytes(
            response.content
        )

        print()
        print(
            "Raw image saved:"
        )

        print(
            raw_file
        )

        # -------------------------------------------------
        # READ RETURNED IMAGE
        # -------------------------------------------------

        with rasterio.open(
            raw_file
        ) as src:

            data = src.read()

            print()
            print(
                "Returned image:"
            )

            print(
                "Width:",
                src.width
            )

            print(
                "Height:",
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
        # CHECK IMAGE DATA
        # -------------------------------------------------

        if data.ndim != 3:

            raise RuntimeError(
                f"Unexpected image dimensions "
                f"for tile {tile_number}: "
                f"{data.shape}"
            )

        if data.shape[0] < 3:

            raise RuntimeError(
                f"Tile {tile_number} has fewer "
                f"than 3 image bands."
            )

        # -------------------------------------------------
        # ADD GEOREFERENCE
        # -------------------------------------------------

        height = data.shape[1]
        width = data.shape[2]

        transform = from_bounds(
            tile_xmin,
            tile_ymin,
            tile_xmax,
            tile_ymax,
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

        # -------------------------------------------------
        # WRITE GEOREFERENCED TIFF
        # -------------------------------------------------

        with rasterio.open(
            georef_file,
            "w",
            **profile
        ) as dst:

            dst.write(data)

        print()
        print(
            "Georeferenced tile saved:"
        )

        print(
            georef_file
        )

        # -------------------------------------------------
        # VERIFY TILE
        # -------------------------------------------------

        with rasterio.open(
            georef_file
        ) as check:

            print()
            print(
                "Verification"
            )

            print(
                "------------"
            )

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
                "Dtype:",
                check.dtypes
            )

            print(
                "Bounds:",
                check.bounds
            )

            # ---------------------------------------------
            # BASIC VALIDATION
            # ---------------------------------------------

            if check.crs is None:

                raise RuntimeError(
                    f"Tile {tile_number} "
                    "has no CRS."
                )

            if check.count < 3:

                raise RuntimeError(
                    f"Tile {tile_number} "
                    "has fewer than 3 bands."
                )

            if check.width <= 0:

                raise RuntimeError(
                    f"Tile {tile_number} "
                    "has invalid width."
                )

            if check.height <= 0:

                raise RuntimeError(
                    f"Tile {tile_number} "
                    "has invalid height."
                )

        successful_tiles += 1

        print()
        print(
            "Tile",
            tile_number,
            "completed successfully."
        )


# =========================================================
# FINAL SUMMARY
# =========================================================

print()
print("=" * 70)

print(
    "FULL DAMARAKUNTA ESRI EXPORT COMPLETED"
)

print("=" * 70)

print()

print(
    "Total tiles:",
    x_count * y_count
)

print(
    "Newly downloaded:",
    successful_tiles
)

print(
    "Already existing/skipped:",
    skipped_tiles
)

print()

print(
    "Output folder:"
)

print(
    output_dir
)

print()

print(
    "Expected imagery resolution:",
    expected_resolution,
    "m/pixel"
)

print()

print(
    "All available tiles are now ready "
    "for the next processing stage."
)