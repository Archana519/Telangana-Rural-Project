import rasterio
import numpy as np
from pathlib import Path
from PIL import Image

src_file = Path(
    "Siddipet/Damarakunta/raw/imagery/"
    "esri_damarakunta_test_1km_georef.tif"
)

out_file = Path(
    "Siddipet/Damarakunta/results/"
    "esri_damarakunta_test_preview.jpg"
)

out_file.parent.mkdir(parents=True, exist_ok=True)

with rasterio.open(src_file) as src:
    data = src.read()

print("Input:")
print("Shape:", data.shape)
print("CRS:", src.crs)
print("Resolution:", src.res)

# Use RGB bands; ignore alpha band if present
rgb = data[:3].astype(np.float32)

# Convert each band independently to display range
rgb_out = np.zeros_like(rgb, dtype=np.uint8)

for i in range(3):
    band = rgb[i]

    low = np.percentile(band, 2)
    high = np.percentile(band, 98)

    if high <= low:
        high = low + 1

    scaled = (band - low) / (high - low)
    rgb_out[i] = np.clip(scaled * 255, 0, 255)

image = np.transpose(rgb_out, (1, 2, 0))

Image.fromarray(image).save(
    out_file,
    quality=95
)

print()
print("Preview created:")
print(out_file)