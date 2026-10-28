import requests
from pathlib import Path
import rasterio
from rasterio.transform import from_bounds

# ---------------------------------------------------------
# Damarakunta test area
# ---------------------------------------------------------
cx = 262203.6172
cy = 1958760.6979

half = 500

xmin = cx - half
ymin = cy - half
xmax = cx + half
ymax = cy + half

# Requested output size
width = 1667
height = 1667

# ---------------------------------------------------------
# Esri World Imagery export
# ---------------------------------------------------------
url = (
    "https://services.arcgisonline.com/"
    "ArcGIS/rest/services/World_Imagery/MapServer/export"
)

params = {
    "bbox": f"{xmin},{ymin},{xmax},{ymax}",
    "bboxSR": "32644",
    "imageSR": "32644",
    "size": f"{width},{height}",
    "format": "tiff",
    "transparent": "false",
    "f": "image",
}

print("Damarakunta Esri corrected test export")
print("---------------------------------------")
print("BBOX:", xmin, ymin, xmax, ymax)
print("Requested size:", width, "x", height)
print()

response = requests.get(
    url,
    params=params,
    timeout=180
)

print("HTTP status:", response.status_code)
print("Returned bytes:", len(response.content))

if response.status_code != 200:
    print(response.text[:2000])
    raise SystemExit(1)

# ---------------------------------------------------------
# Save temporary raw image
# ---------------------------------------------------------
raw_file = Path(
    "Siddipet/Damarakunta/raw/imagery/"
    "esri_damarakunta_test_raw.tif"
)

raw_file.parent.mkdir(parents=True, exist_ok=True)
raw_file.write_bytes(response.content)

print("Raw image saved:", raw_file)

# ---------------------------------------------------------
# Read returned image and explicitly georeference it
# ---------------------------------------------------------
with rasterio.open(raw_file) as src:

    data = src.read()

    print()
    print("Returned image:")
    print("Width:", src.width)
    print("Height:", src.height)
    print("Bands:", src.count)
    print("Dtypes:", src.dtypes)

# ---------------------------------------------------------
# Create properly georeferenced GeoTIFF
# ---------------------------------------------------------
out = Path(
    "Siddipet/Damarakunta/raw/imagery/"
    "esri_damarakunta_test_1km_georef.tif"
)

transform = from_bounds(
    xmin,
    ymin,
    xmax,
    ymax,
    width,
    height
)

profile = {
    "driver": "GTiff",
    "height": height,
    "width": width,
    "count": data.shape[0],
    "dtype": data.dtype,
    "crs": "EPSG:32644",
    "transform": transform,
    "compress": "deflate",
}

with rasterio.open(out, "w", **profile) as dst:
    dst.write(data)

print()
print("Georeferenced GeoTIFF created:")
print(out)

# ---------------------------------------------------------
# Verify
# ---------------------------------------------------------
with rasterio.open(out) as src:

    print()
    print("FINAL VERIFICATION")
    print("------------------")
    print("Width:", src.width)
    print("Height:", src.height)
    print("Bands:", src.count)
    print("CRS:", src.crs)
    print("Resolution:", src.res)
    print("Bounds:", src.bounds)
    print("Dtype:", src.dtypes)
    print("Transform:", src.transform)