import os
import numpy as np
import rasterio
from PIL import Image, ImageDraw

BASE = r"D:\Telangana_Rural_Project\Siddipet\Damarakunta"

IMAGE_PATH = os.path.join(
    BASE, "predictions", "residential_diagnostic_tile.tif"
)
MASK_PATH = os.path.join(
    BASE, "predictions", "residential_diagnostic_mask.tif"
)
OUTPUT_PATH = os.path.join(
    BASE, "results", "residential_visual_diagnostic_corrected.jpg"
)

# Verified mapping from utils.py:
# 0 Ignore, 1 Background, 2 Building, 3 Road,
# 4 Water, 5 Barren, 6 Forest, 7 Agriculture

with rasterio.open(IMAGE_PATH) as src:
    image = src.read([1, 2, 3])

with rasterio.open(MASK_PATH) as src:
    mask = src.read(1)

if image.shape[1:] != mask.shape:
    raise ValueError(
        f"Image and mask dimensions differ: {image.shape}, {mask.shape}"
    )

rgb = np.transpose(image, (1, 2, 0)).astype(np.uint8)

# Use a distinct color for each class.
colors = {
    0: (0, 0, 0),        # Ignore
    1: (70, 70, 70),     # Background
    2: (255, 0, 0),      # Building — red
    3: (0, 80, 255),     # Road — blue
    4: (0, 220, 255),    # Water — cyan
    5: (180, 130, 70),   # Barren — brown
    6: (0, 180, 0),      # Forest — green
    7: (255, 220, 0),    # Agriculture — yellow
}

names = {
    0: "Ignore",
    1: "Background",
    2: "Building",
    3: "Road",
    4: "Water",
    5: "Barren",
    6: "Forest",
    7: "Agriculture",
}

prediction = np.zeros_like(rgb)

for class_id, color in colors.items():
    prediction[mask == class_id] = color

# Overlay Building and Road predictions on the original imagery.
overlay = rgb.copy()

for class_id, color in [(2, (255, 0, 0)), (3, (0, 80, 255))]:
    selected = mask == class_id
    overlay[selected] = (
        0.55 * overlay[selected] + 0.45 * np.array(color)
    ).astype(np.uint8)

panels = [
    Image.fromarray(rgb),
    Image.fromarray(prediction),
    Image.fromarray(overlay),
]

width, height = panels[0].size
header = 65

canvas = Image.new("RGB", (width * 3, height + header), "white")
draw = ImageDraw.Draw(canvas)

titles = [
    "Original Esri imagery",
    "Prediction (correct IDs)",
    "Building red | Road blue",
]

for i, panel in enumerate(panels):
    canvas.paste(panel, (i * width, header))
    draw.text((i * width + 10, 8), titles[i], fill="black")

legend = "  ".join(
    f"{i}={names[i]}" for i in range(8)
)
draw.text((10, 38), legend, fill="black")

os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
canvas.save(OUTPUT_PATH, quality=95)

print("Corrected diagnostic saved:")
print(OUTPUT_PATH)
print("\nVerified-ID class distribution:")

for class_id in range(8):
    count = int((mask == class_id).sum())
    percentage = 100 * count / mask.size
    print(
        f"{class_id} {names[class_id]}: "
        f"{count:,} pixels ({percentage:.2f}%)"
    )