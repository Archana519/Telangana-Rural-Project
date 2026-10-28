from pathlib import Path
from PIL import Image, ImageDraw
import rasterio
import numpy as np

BASE = Path(r"D:\Telangana_Rural_Project\Siddipet\Angadi_Kistapur")

imagery = BASE / "aligned" / "angadi_kistapur_utm44n.tif"
building_mask = BASE / "derived" / "building_mask.png"
road_mask = BASE / "derived" / "road_mask.png"

output = BASE / "derived" / "phase13_diagnostic.png"

print("=" * 70)
print("PHASE 13 - VISUAL DIAGNOSTIC")
print("=" * 70)

with rasterio.open(imagery) as src:
    arr = src.read([1, 2, 3])

arr = np.transpose(arr, (1, 2, 0))
arr = arr.astype(np.float32)

arr_min = arr.min()
arr_max = arr.max()

if arr_max > arr_min:
    arr = (arr - arr_min) / (arr_max - arr_min) * 255.0

arr = np.clip(arr, 0, 255).astype(np.uint8)

original = Image.fromarray(arr)

buildings = Image.open(building_mask).convert("L")
roads = Image.open(road_mask).convert("L")

size = original.size

buildings = buildings.resize(size, Image.Resampling.NEAREST)
roads = roads.resize(size, Image.Resampling.NEAREST)

building_rgb = Image.merge("RGB", (buildings, buildings, buildings))
road_rgb = Image.merge("RGB", (roads, roads, roads))

def add_label(img, label):
    img = img.copy()
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, 360, 45), fill=255)
    draw.text((10, 12), label, fill=0)
    return img

original = add_label(original, "ORIGINAL IMAGERY")
building_rgb = add_label(building_rgb, "PREDICTED BUILDING MASK")
road_rgb = add_label(road_rgb, "PREDICTED ROAD MASK")

combined = Image.new(
    "RGB",
    (size[0] * 3, size[1])
)

combined.paste(original, (0, 0))
combined.paste(building_rgb, (size[0], 0))
combined.paste(road_rgb, (size[0] * 2, 0))

combined.save(output)

print()
print("Diagnostic image created:")
print(output)
print()
print("Image size:", combined.size)
print()
print("=" * 70)
print("VISUAL DIAGNOSTIC COMPLETED")
print("=" * 70)