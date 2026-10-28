from pathlib import Path
import numpy as np
from PIL import Image
import rasterio
from rasterio.transform import from_bounds

ROOT = Path(r"D:\Telangana_Rural_Project\Siddipet\Angadi_Kistapur")

input_file = ROOT / "raw" / "imagery" / "angadi_kistapur_full_village_tgrac_export.jpg"
output_file = ROOT / "aligned" / "angadi_kistapur_full_village_georeferenced.tif"

west = 78.715544010000045
south = 17.780966772000028
east = 78.752937406000072
north = 17.818360168000055

image = Image.open(input_file).convert("RGB")
array = np.array(image)

height, width = array.shape[:2]
transform = from_bounds(west, south, east, north, width, height)

with rasterio.open(
    output_file,
    "w",
    driver="GTiff",
    height=height,
    width=width,
    count=3,
    dtype=array.dtype,
    crs="EPSG:4326",
    transform=transform,
    compress="deflate"
) as dst:
    for band in range(3):
        dst.write(array[:, :, band], band + 1)

print("=== FULL VILLAGE GEOSPATIAL PREPARATION ===")
print("Input:", input_file)
print("Output:", output_file)
print("Size:", width, "x", height)
print("CRS: EPSG:4326")
print("Bounds:")
print(" West :", west)
print(" South:", south)
print(" East :", east)
print(" North:", north)
print("STATUS: Full-village GeoTIFF created successfully")