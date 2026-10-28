import os
import requests
import geopandas as gpd
import rasterio
import numpy as np

from rasterio.transform import from_bounds
from PIL import Image
from io import BytesIO
from pyproj import Transformer


# ============================================================
# PHASE 25 - STEP 11F
# EXPORT DAMARAKUNTA SENTINEL IMAGERY
# ============================================================

PROJECT_ROOT = r"D:\Telangana_Rural_Project"

BOUNDARY_FILE = os.path.join(
    PROJECT_ROOT,
    "Siddipet",
    "Damarakunta",
    "study_area",
    "damarakunta_boundary.gpkg"
)

OUTPUT_DIR = os.path.join(
    PROJECT_ROOT,
    "Siddipet",
    "Damarakunta",
    "raw",
    "imagery"
)

OUTPUT_FILE = os.path.join(
    OUTPUT_DIR,
    "damarakunta_sentinel_feb2022.tif"
)

EXPORT_URL = (
    "https://tgrac.telangana.gov.in/arcgis/rest/services/"
    "MusiRiver/Musi_Basin_Web_Publication_Raster/MapServer/export"
)

LAYER_URL = (
    "https://tgrac.telangana.gov.in/arcgis/rest/services/"
    "MusiRiver/Musi_Basin_Web_Publication_Raster/MapServer/78"
)

TARGET_CRS = "EPSG:32644"

IMAGE_SIZE = 2048


print("=" * 80)
print("PHASE 25 - STEP 11F")
print("EXPORT DAMARAKUNTA SENTINEL IMAGERY")
print("=" * 80)


# ============================================================
# 1. CHECK BOUNDARY
# ============================================================

if not os.path.isfile(BOUNDARY_FILE):

    print("\n[ERROR] Boundary file not found:")
    print(BOUNDARY_FILE)

    raise SystemExit(1)


# ============================================================
# 2. READ BOUNDARY
# ============================================================

gdf = gpd.read_file(
    BOUNDARY_FILE,
    layer="village_boundary"
)

if gdf.empty:

    print("\n[ERROR] Boundary contains no features.")

    raise SystemExit(1)


print("\nBoundary CRS:")
print(gdf.crs)

print("\nBoundary area:")
print(
    round(
        gdf.geometry.area.sum(),
        2
    ),
    "m²"
)

minx, miny, maxx, maxy = gdf.total_bounds

print("\nDamarakunta UTM bounds:")
print(
    minx,
    miny,
    maxx,
    maxy
)


# ============================================================
# 3. GET SENTINEL LAYER CRS
# ============================================================

layer_response = requests.get(
    LAYER_URL,
    params={"f": "json"},
    timeout=30
)

layer_response.raise_for_status()

layer_info = layer_response.json()

target_wkt = (
    layer_info["extent"]
    ["spatialReference"]
    ["wkt"]
)


# ============================================================
# 4. TRANSFORM BOUNDARY TO SENTINEL CRS
# ============================================================

transformer = Transformer.from_crs(
    TARGET_CRS,
    target_wkt,
    always_xy=True
)

corners = [
    (minx, miny),
    (minx, maxy),
    (maxx, miny),
    (maxx, maxy)
]

transformed = [
    transformer.transform(x, y)
    for x, y in corners
]

xs = [
    point[0]
    for point in transformed
]

ys = [
    point[1]
    for point in transformed
]

bbox_minx = min(xs)
bbox_miny = min(ys)
bbox_maxx = max(xs)
bbox_maxy = max(ys)

bbox = (
    f"{bbox_minx},{bbox_miny},"
    f"{bbox_maxx},{bbox_maxy}"
)

print("\nSentinel export bounding box:")
print(bbox)


# ============================================================
# 5. CREATE OUTPUT DIRECTORY
# ============================================================

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)


# ============================================================
# 6. EXPORT SENTINEL IMAGE
# ============================================================

params = {
    "bbox": bbox,
    "bboxSR": target_wkt,
    "imageSR": TARGET_CRS,
    "size": f"{IMAGE_SIZE},{IMAGE_SIZE}",
    "imageFormat": "png",
    "transparent": "false",
    "layers": "show:78",
    "f": "image"
}

print("\nRequesting Sentinel imagery...")

response = requests.get(
    EXPORT_URL,
    params=params,
    timeout=180
)

print(
    "HTTP status:",
    response.status_code
)

print(
    "Response size:",
    len(response.content),
    "bytes"
)


# ============================================================
# 7. VERIFY PNG
# ============================================================

is_png = response.content.startswith(
    b"\x89PNG\r\n\x1a\n"
)

if response.status_code != 200:

    print("\n[ERROR] TGRAC export failed.")
    print(response.text[:2000])

    raise SystemExit(1)


if not is_png:

    print("\n[ERROR] Response is not a PNG image.")
    print(response.content[:200])

    raise SystemExit(1)


print(
    "[OK] Valid PNG image received."
)


# ============================================================
# 8. LOAD IMAGE
# ============================================================

image = Image.open(
    BytesIO(response.content)
)

image = image.convert(
    "RGB"
)

width, height = image.size

print("\nImage dimensions:")
print(
    width,
    "x",
    height
)


# ============================================================
# 9. CONVERT PIL IMAGE TO NUMPY ARRAY
# ============================================================

image_array = np.asarray(
    image,
    dtype=np.uint8
)

print("\nImage array shape:")
print(
    image_array.shape
)


# ============================================================
# 10. CREATE GEOTRANSFORM
# ============================================================

transform = from_bounds(
    minx,
    miny,
    maxx,
    maxy,
    width,
    height
)


# ============================================================
# 11. SAVE GEOTIFF
# ============================================================

print("\nSaving GeoTIFF...")

with rasterio.open(
    OUTPUT_FILE,
    "w",
    driver="GTiff",
    height=height,
    width=width,
    count=3,
    dtype="uint8",
    crs=TARGET_CRS,
    transform=transform,
    compress="lzw"
) as dst:

    # PIL/NumPy shape:
    # (height, width, bands)

    # Rasterio requires:
    # (bands, height, width)

    raster_array = np.transpose(
        image_array,
        (2, 0, 1)
    )

    dst.write(
        raster_array
    )


# ============================================================
# 12. VERIFY OUTPUT
# ============================================================

print("\nVerifying GeoTIFF...")

with rasterio.open(
    OUTPUT_FILE
) as src:

    print("\nOutput CRS:")
    print(src.crs)

    print("\nOutput size:")
    print(
        src.width,
        "x",
        src.height
    )

    print("\nNumber of bands:")
    print(src.count)

    print("\nResolution:")
    print(src.res)

    print("\nBounds:")
    print(src.bounds)

    print("\nData type:")
    print(src.dtypes)

    print("\nFile size:")
    print(
        round(
            os.path.getsize(OUTPUT_FILE)
            / (1024 * 1024),
            2
        ),
        "MB"
    )


# ============================================================
# 13. FINAL STATUS
# ============================================================

print("\n" + "=" * 80)

print(
    "STATUS: DAMARAKUNTA SENTINEL IMAGERY "
    "EXPORTED AND SAVED SUCCESSFULLY."
)

print("\nOutput:")
print(OUTPUT_FILE)

print("\nPHASE 25 STEP 11F COMPLETED.")

print("=" * 80)