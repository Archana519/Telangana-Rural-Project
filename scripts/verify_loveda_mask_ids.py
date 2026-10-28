
import os
from collections import Counter

import cv2
import numpy as np

MASK_DIR = (
    r"D:\new_MPS\remoteSensingWebApp"
    r"\LoveDA Satellite Images Semantic Segmentation"
    r"\Train\Train\Rural\masks_png"
)

CLASS_NAMES = {
    0: "Ignore",
    1: "Background",
    2: "Building",
    3: "Road",
    4: "Water",
    5: "Barren",
    6: "Forest",
    7: "Agriculture",
}

if not os.path.isdir(MASK_DIR):
    raise FileNotFoundError(f"Mask directory not found: {MASK_DIR}")

files = sorted(
    f for f in os.listdir(MASK_DIR)
    if f.lower().endswith((".png", ".tif", ".tiff"))
)

print("Mask directory:", MASK_DIR)
print("Number of masks:", len(files))

pixel_counts = Counter()
mask_counts = Counter()
unexpected = []

for filename in files:
    path = os.path.join(MASK_DIR, filename)
    mask = cv2.imread(path, cv2.IMREAD_GRAYSCALE)

    if mask is None:
        print("Could not read:", filename)
        continue

    ids, counts = np.unique(mask, return_counts=True)

    for class_id, count in zip(ids, counts):
        pixel_counts[int(class_id)] += int(count)
        mask_counts[int(class_id)] += 1

        if int(class_id) not in CLASS_NAMES:
            unexpected.append((filename, int(class_id)))

total = sum(pixel_counts.values())
print("\nClass ID distribution across all pixels:")

for class_id in sorted(pixel_counts):
    count = pixel_counts[class_id]
    name = CLASS_NAMES.get(class_id, "UNEXPECTED")
    percentage = 100 * count / total if total else 0

    print(
        f"ID {class_id}: {name:12s} "
        f"{count:,} pixels ({percentage:.2f}%) "
        f"in {mask_counts[class_id]} masks"
    )

print("\nUnexpected IDs:", len(unexpected))
if unexpected:
    print("Examples:", unexpected[:20])
