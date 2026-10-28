import os
import numpy as np
import rasterio
import matplotlib.pyplot as plt


PROJECT_ROOT = r"D:\Telangana_Rural_Project"

IMAGE_FILE = os.path.join(
    PROJECT_ROOT,
    "Siddipet",
    "Damarakunta",
    "predictions",
    "input_tiles",
    "tile_000.tif"
)

MASK_FILE = os.path.join(
    PROJECT_ROOT,
    "Siddipet",
    "Damarakunta",
    "predictions",
    "segmentation_masks",
    "tile_000.tif"
)

OUTPUT_FILE = os.path.join(
    PROJECT_ROOT,
    "Siddipet",
    "Damarakunta",
    "results",
    "damarakunta_tile000_diagnostic.png"
)

os.makedirs(
    os.path.dirname(OUTPUT_FILE),
    exist_ok=True
)


CLASS_NAMES = {
    0: "Ignore",
    1: "Background",
    2: "Building",
    3: "Road",
    4: "Water",
    5: "Barren",
    6: "Forest",
    7: "Agriculture"
}


print("=" * 80)
print("DAMARAKUNTA VISUAL DIAGNOSTIC")
print("=" * 80)


print("\nINPUT CHECK")
print("-" * 80)

print("Image:", IMAGE_FILE)
print("Image exists:", os.path.isfile(IMAGE_FILE))

print("Mask:", MASK_FILE)
print("Mask exists:", os.path.isfile(MASK_FILE))


if not os.path.isfile(IMAGE_FILE):
    raise SystemExit("[ERROR] Image not found.")

if not os.path.isfile(MASK_FILE):
    raise SystemExit("[ERROR] Segmentation mask not found.")


# ------------------------------------------------------------------
# READ IMAGE
# ------------------------------------------------------------------

with rasterio.open(IMAGE_FILE) as src:

    image = src.read(
        indexes=[1, 2, 3]
    )

    bounds = src.bounds


image = np.transpose(
    image,
    (1, 2, 0)
)

image = image.astype(
    np.float32
) / 255.0


# ------------------------------------------------------------------
# READ MASK
# ------------------------------------------------------------------

with rasterio.open(MASK_FILE) as src:

    mask = src.read(1)


# ------------------------------------------------------------------
# MASK SUMMARY
# ------------------------------------------------------------------

print("\nSEGMENTATION SUMMARY")
print("-" * 80)

unique, counts = np.unique(
    mask,
    return_counts=True
)

total_pixels = mask.size

for cls, count in zip(unique, counts):

    percentage = (
        count / total_pixels * 100
    )

    print(
        f"{int(cls)} "
        f"{CLASS_NAMES.get(int(cls), 'Unknown'):<15} "
        f"{int(count):>10} pixels "
        f"{percentage:>8.2f}%"
    )


# ------------------------------------------------------------------
# CREATE SIMPLE CLASS MAP
# ------------------------------------------------------------------

class_map = np.zeros(
    (mask.shape[0], mask.shape[1], 3),
    dtype=np.float32
)

# Background
class_map[mask == 1] = [0.85, 0.85, 0.85]

# Building
class_map[mask == 2] = [1.0, 0.0, 0.0]

# Road
class_map[mask == 3] = [0.1, 0.1, 0.1]

# Water
class_map[mask == 4] = [0.0, 0.4, 1.0]

# Barren
class_map[mask == 5] = [0.7, 0.55, 0.3]

# Forest
class_map[mask == 6] = [0.0, 0.6, 0.0]

# Agriculture
class_map[mask == 7] = [0.8, 0.8, 0.0]


# ------------------------------------------------------------------
# CREATE FIGURE
# ------------------------------------------------------------------

fig, axes = plt.subplots(
    1,
    3,
    figsize=(18, 6)
)


# Original image
axes[0].imshow(image)

axes[0].set_title(
    "Damarakunta Input Tile"
)

axes[0].axis("off")


# Raw class mask
axes[1].imshow(
    mask,
    interpolation="nearest"
)

axes[1].set_title(
    "Model Segmentation Mask"
)

axes[1].axis("off")


# Colored mask
axes[2].imshow(
    class_map
)

axes[2].set_title(
    "Colored Segmentation"
)

axes[2].axis("off")


plt.suptitle(
    "Damarakunta Tile 000 Diagnostic"
)

plt.tight_layout()


plt.savefig(
    OUTPUT_FILE,
    dpi=200,
    bbox_inches="tight"
)

plt.close()


print("\nOUTPUT")
print("-" * 80)

print(
    "Diagnostic image:",
    OUTPUT_FILE
)

print("\n" + "=" * 80)
print(
    "STATUS: VISUAL DIAGNOSTIC CREATED."
)
print("=" * 80)