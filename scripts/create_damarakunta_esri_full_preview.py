from pathlib import Path

import numpy as np
import rasterio
from PIL import Image


input_file = Path(
    "Siddipet/Damarakunta/aligned/"
    "damarakunta_esri_highres_mosaic_0p6m.tif"
)

output_file = Path(
    "Siddipet/Damarakunta/results/"
    "damarakunta_esri_full_preview.jpg"
)

output_file.parent.mkdir(
    parents=True,
    exist_ok=True
)


print("=" * 70)
print("DAMARAKUNTA ESRI FULL MOSAIC PREVIEW")
print("=" * 70)

with rasterio.open(input_file) as src:

    print()
    print("Input:", input_file)
    print("Size:", src.width, "x", src.height)
    print("Bands:", src.count)
    print("CRS:", src.crs)
    print("Resolution:", src.res)
    print("Bounds:", src.bounds)

    # Read RGB
    data = src.read([1, 2, 3]).astype(np.float32)


# ------------------------------------------------------------
# PERCENTILE STRETCH
# ------------------------------------------------------------

rgb = np.zeros_like(data, dtype=np.uint8)

for i in range(3):

    band = data[i]

    valid = band[np.isfinite(band)]

    low = np.percentile(valid, 2)
    high = np.percentile(valid, 98)

    print(
        f"Band {i+1}: "
        f"2%={low:.2f}, "
        f"98%={high:.2f}"
    )

    stretched = (
        (band - low)
        / (high - low + 1e-6)
        * 255
    )

    rgb[i] = np.clip(
        stretched,
        0,
        255
    ).astype(np.uint8)


# ------------------------------------------------------------
# RGB → PIL
# ------------------------------------------------------------

rgb_image = np.transpose(
    rgb,
    (1, 2, 0)
)

image = Image.fromarray(
    rgb_image,
    mode="RGB"
)


# ------------------------------------------------------------
# PREVIEW SIZE
# ------------------------------------------------------------

max_dimension = 3000

scale = min(
    1.0,
    max_dimension / max(image.size)
)

if scale < 1:

    new_size = (
        int(image.width * scale),
        int(image.height * scale)
    )

    image = image.resize(
        new_size,
        Image.Resampling.LANCZOS
    )


# ------------------------------------------------------------
# SAVE
# ------------------------------------------------------------

image.save(
    output_file,
    quality=95
)

print()
print("Preview size:", image.size)
print("Preview saved:")
print(output_file)

print()
print("=" * 70)
print("PREVIEW CREATED SUCCESSFULLY")
print("=" * 70)