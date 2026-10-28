import os
import numpy as np
import rasterio
import geopandas as gpd
from shapely.geometry import box

PROJECT_ROOT = r"D:\Telangana_Rural_Project"

IMAGE_FILE = os.path.join(
    PROJECT_ROOT,
    "Siddipet",
    "Damarakunta",
    "raw",
    "imagery",
    "damarakunta_sentinel_feb2022.tif"
)

BOUNDARY_FILE = os.path.join(
    PROJECT_ROOT,
    "Siddipet",
    "Damarakunta",
    "study_area",
    "damarakunta_boundary.gpkg"
)

print("=" * 80)
print("PHASE 25 - STEP 11G")
print("INSPECT DAMARAKUNTA SENTINEL GEOTIFF")
print("=" * 80)

if not os.path.isfile(IMAGE_FILE):
    print("\n[ERROR] Imagery file not found:")
    print(IMAGE_FILE)
    raise SystemExit(1)

if not os.path.isfile(BOUNDARY_FILE):
    print("\n[ERROR] Boundary file not found:")
    print(BOUNDARY_FILE)
    raise SystemExit(1)

with rasterio.open(IMAGE_FILE) as src:
    print("\nIMAGE INFORMATION")
    print("-" * 80)
    print("File:", IMAGE_FILE)
    print("Driver:", src.driver)
    print("Width:", src.width)
    print("Height:", src.height)
    print("Bands:", src.count)
    print("CRS:", src.crs)
    print("Data types:", src.dtypes)
    print("Resolution:", src.res)
    print("Bounds:", src.bounds)
    print("Transform:", src.transform)
    print("NoData:", src.nodata)
    print(
        "File size:",
        round(os.path.getsize(IMAGE_FILE) / (1024 * 1024), 2),
        "MB"
    )

    data = src.read()
    image_crs = str(src.crs)
    image_bounds = src.bounds

print("\nPIXEL VALUE CHECK")
print("-" * 80)

for band_index in range(data.shape[0]):
    band = data[band_index]

    valid = np.isfinite(band)

    print(f"Band {band_index + 1}:")
    print("  Min:", int(band[valid].min()))
    print("  Max:", int(band[valid].max()))
    print("  Mean:", round(float(band[valid].mean()), 2))
    print("  Non-zero pixels:", int(np.count_nonzero(band)))
    print("  Total pixels:", band.size)

print("\nRGB IMAGE CHECK")
print("-" * 80)

if data.shape[0] == 3:
    rgb_valid = np.logical_or.reduce([
        data[0] > 0,
        data[1] > 0,
        data[2] > 0
    ])

    valid_pixels = int(rgb_valid.sum())
    total_pixels = int(rgb_valid.size)

    coverage_percent = valid_pixels / total_pixels * 100

    print("RGB bands:", "YES")
    print("Valid RGB pixels:", valid_pixels)
    print("Total pixels:", total_pixels)
    print(
        "Valid pixel percentage:",
        round(coverage_percent, 2),
        "%"
    )
else:
    print("RGB bands:", "NO")
    coverage_percent = 0

boundary = gpd.read_file(
    BOUNDARY_FILE,
    layer="village_boundary"
)

print("\nBOUNDARY INFORMATION")
print("-" * 80)
print("Boundary CRS:", boundary.crs)
print("Boundary records:", len(boundary))
print(
    "Boundary geometry:",
    boundary.geometry.geom_type.tolist()
)
print(
    "Boundary area:",
    round(boundary.geometry.area.sum(), 2),
    "m²"
)
print(
    "Boundary bounds:",
    boundary.total_bounds.tolist()
)

print("\nSPATIAL REFERENCE CHECK")
print("-" * 80)

boundary_crs = str(boundary.crs)

print("Image CRS:", image_crs)
print("Boundary CRS:", boundary_crs)

if image_crs == boundary_crs:
    print("CRS MATCH: YES")
    crs_match = True
else:
    print("CRS MATCH: NO")
    crs_match = False

print("\nCOVERAGE CHECK")
print("-" * 80)

# Create image bounding rectangle using shapely.box
image_box = box(
    image_bounds.left,
    image_bounds.bottom,
    image_bounds.right,
    image_bounds.top
)

image_box_gdf = gpd.GeoDataFrame(
    {"id": [1]},
    geometry=[image_box],
    crs=src.crs
)

boundary_in_image_crs = boundary.to_crs(src.crs)

intersection = boundary_in_image_crs.geometry.intersection(
    image_box
)

intersection_area = intersection.area.sum()

boundary_area = boundary_in_image_crs.geometry.area.sum()

coverage = (
    intersection_area / boundary_area * 100
    if boundary_area > 0
    else 0
)

print(
    "Boundary area:",
    round(boundary_area, 2),
    "m²"
)

print(
    "Image intersection area:",
    round(intersection_area, 2),
    "m²"
)

print(
    "Boundary coverage:",
    round(coverage, 2),
    "%"
)

print("\n" + "=" * 80)

if (
    data.shape[0] == 3
    and crs_match
    and coverage >= 99.0
    and coverage_percent > 0
):
    print(
        "STATUS: DAMARAKUNTA IMAGERY PASSED "
        "TECHNICAL INSPECTION."
    )
else:
    print(
        "STATUS: IMAGERY REQUIRES "
        "FURTHER INSPECTION."
    )

print("=" * 80)

print("\nPHASE 25 STEP 11G COMPLETED.")