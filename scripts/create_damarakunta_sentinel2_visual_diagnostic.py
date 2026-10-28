from pathlib import Path

import numpy as np
import rasterio
from PIL import Image, ImageDraw


# ============================================================
# DAMARAKUNTA SENTINEL-2 VISUAL DIAGNOSTIC
# ============================================================

BASE = Path(
    r"D:\Telangana_Rural_Project\Siddipet\Damarakunta"
)

IMAGE = (
    BASE
    / "aligned"
    / "damarakunta_sentinel2_model_rgb_uint8.tif"
)

MASK_DIR = (
    BASE
    / "predictions"
    / "sentinel2_segmentation_masks"
)

OUTPUT_DIR = BASE / "results"

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

OUTPUT = (
    OUTPUT_DIR
    / "damarakunta_sentinel2_diagnostic.png"
)


# ============================================================
# START
# ============================================================

print("=" * 80)
print("DAMARAKUNTA SENTINEL-2 VISUAL DIAGNOSTIC")
print("=" * 80)


# ============================================================
# INPUT CHECK
# ============================================================

print("\nINPUT CHECK")
print("-" * 80)

print("Sentinel-2 RGB:")
print(IMAGE)
print("Exists:", IMAGE.exists())

print("\nSegmentation mask directory:")
print(MASK_DIR)
print("Exists:", MASK_DIR.exists())


if not IMAGE.exists():
    raise FileNotFoundError(
        f"Sentinel-2 image not found:\n{IMAGE}"
    )

if not MASK_DIR.exists():
    raise FileNotFoundError(
        f"Mask directory not found:\n{MASK_DIR}"
    )


# ============================================================
# READ SENTINEL-2 RGB
# ============================================================

with rasterio.open(IMAGE) as src:

    rgb = src.read()

    profile = src.profile.copy()


print("\nIMAGE INFORMATION")
print("-" * 80)

print("Shape:", rgb.shape)
print("Width:", rgb.shape[2])
print("Height:", rgb.shape[1])
print("CRS:", profile.get("crs"))

transform = profile.get("transform")

if transform is not None:
    print(
        "Resolution:",
        abs(transform.a),
        abs(transform.e)
    )


# ============================================================
# CONVERT RGB TO DISPLAY IMAGE
# ============================================================

# Convert:
# (bands, height, width)
# to:
# (height, width, bands)

rgb = np.transpose(
    rgb,
    (1, 2, 0)
)

rgb = np.clip(
    rgb,
    0,
    255
).astype(np.uint8)


# ============================================================
# CONTRAST STRETCH
# ============================================================

display_rgb = np.zeros_like(rgb)

for c in range(3):

    band = rgb[:, :, c].astype(
        np.float32
    )

    low = np.percentile(
        band,
        2
    )

    high = np.percentile(
        band,
        98
    )

    if high > low:

        stretched = (
            (band - low)
            / (high - low)
            * 255.0
        )

    else:

        stretched = band

    display_rgb[:, :, c] = np.clip(
        stretched,
        0,
        255
    ).astype(np.uint8)


rgb_image = Image.fromarray(
    display_rgb,
    mode="RGB"
)


# ============================================================
# FIND SEGMENTATION MASKS
# ============================================================

mask_files = sorted(
    MASK_DIR.glob("*_mask.tif")
)


if not mask_files:

    raise FileNotFoundError(
        "No Sentinel-2 segmentation masks found in:\n"
        f"{MASK_DIR}"
    )


print("\nMASK FILES")
print("-" * 80)

for mask_file in mask_files:

    print(
        mask_file.name
    )


# ============================================================
# CLASS NAMES
# ============================================================

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


# ============================================================
# SEGMENTATION SUMMARY
# ============================================================

print("\nSEGMENTATION SUMMARY")
print("-" * 80)


total_counts = {}


for mask_file in mask_files:

    with rasterio.open(mask_file) as src:

        tile_mask = src.read(1)

    values, counts = np.unique(
        tile_mask,
        return_counts=True
    )

    total_pixels = tile_mask.size

    print(
        f"\nMask: {mask_file.name}"
    )

    for value, count in zip(
        values,
        counts
    ):

        value = int(value)
        count = int(count)

        total_counts[value] = (
            total_counts.get(
                value,
                0
            )
            + count
        )

        class_name = CLASS_NAMES.get(
            value,
            f"Unknown_{value}"
        )

        percentage = (
            count
            / total_pixels
            * 100
        )

        print(
            f"{value:2d} "
            f"{class_name:<15} "
            f"{count:10d} pixels "
            f"{percentage:7.2f}%"
        )


# ============================================================
# CREATE FULL-SIZE COMBINED MASK
# ============================================================

print("\nCOMBINING TILE MASKS")
print("-" * 80)

image_height = rgb.shape[0]
image_width = rgb.shape[1]


print(
    "Original image size:",
    image_width,
    "x",
    image_height
)


# Full image mask.
combined_mask = np.zeros(
    (
        image_height,
        image_width
    ),
    dtype=np.uint8
)


for mask_file in mask_files:

    with rasterio.open(mask_file) as src:

        tile_mask = src.read(1)

    tile_height = tile_mask.shape[0]
    tile_width = tile_mask.shape[1]

    print(
        f"{mask_file.name}:",
        tile_width,
        "x",
        tile_height
    )


    # --------------------------------------------------------
    # Determine tile position
    # --------------------------------------------------------

    if mask_file.name == "tile_000_mask.tif":

        x_start = 0

    elif mask_file.name == "tile_001_mask.tif":

        x_start = 560

    else:

        print(
            "WARNING: Unknown tile name:",
            mask_file.name
        )

        continue


    # --------------------------------------------------------
    # Determine valid source dimensions
    # --------------------------------------------------------

    x_end = min(
        x_start + tile_width,
        image_width
    )

    y_end = min(
        tile_height,
        image_height
    )


    valid_width = (
        x_end - x_start
    )

    valid_height = y_end


    if valid_width <= 0:

        continue

    if valid_height <= 0:

        continue


    # --------------------------------------------------------
    # Copy only real image area
    # --------------------------------------------------------

    combined_mask[
        :valid_height,
        x_start:x_end
    ] = tile_mask[
        :valid_height,
        :valid_width
    ]


print(
    "Combined mask size:",
    combined_mask.shape[1],
    "x",
    combined_mask.shape[0]
)


# ============================================================
# CLASS COLORS FOR VISUALIZATION
# ============================================================

CLASS_COLORS = {

    0: (0, 0, 0),          # Ignore

    1: (0, 0, 0),          # Background

    2: (255, 0, 0),        # Building

    3: (255, 255, 0),      # Road

    4: (0, 120, 255),      # Water

    5: (180, 120, 60),     # Barren

    6: (0, 180, 0),        # Forest

    7: (255, 180, 0),      # Agriculture
}


# ============================================================
# CREATE SEGMENTATION IMAGE
# ============================================================

overlay = np.zeros(
    (
        image_height,
        image_width,
        3
    ),
    dtype=np.uint8
)


for class_id, color in CLASS_COLORS.items():

    pixels = (
        combined_mask
        == class_id
    )

    overlay[pixels] = color


overlay_image = Image.fromarray(
    overlay,
    mode="RGB"
)


# ============================================================
# CREATE RGB + SEGMENTATION OVERLAY
# ============================================================

rgb_for_overlay = (
    rgb_image.convert("RGBA")
)


mask_for_overlay = (
    overlay_image.convert("RGBA")
)


# Make only predicted classes visible.
#
# Background and Ignore remain transparent.
#
# Other predicted classes are semi-transparent.

alpha = np.where(
    combined_mask > 1,
    120,
    0
).astype(np.uint8)


mask_for_overlay.putalpha(
    Image.fromarray(
        alpha,
        mode="L"
    )
)


combined_image = Image.alpha_composite(
    rgb_for_overlay,
    mask_for_overlay
).convert("RGB")


# ============================================================
# CREATE THREE-PANEL DIAGNOSTIC
# ============================================================

width, height = rgb_image.size

canvas = Image.new(
    "RGB",
    (
        width * 3,
        height
    ),
    "white"
)


# Panel 1: RGB

canvas.paste(
    rgb_image,
    (0, 0)
)


# Panel 2: Segmentation

canvas.paste(
    overlay_image,
    (width, 0)
)


# Panel 3: RGB + segmentation

canvas.paste(
    combined_image,
    (width * 2, 0)
)


# ============================================================
# ADD PANEL LABELS
# ============================================================

draw = ImageDraw.Draw(
    canvas
)


# White label backgrounds

draw.rectangle(
    (0, 0, width, 35),
    fill=(255, 255, 255)
)

draw.rectangle(
    (
        width,
        0,
        width * 2,
        35
    ),
    fill=(255, 255, 255)
)

draw.rectangle(
    (
        width * 2,
        0,
        width * 3,
        35
    ),
    fill=(255, 255, 255)
)


# Labels

draw.text(
    (10, 10),
    "Sentinel-2 RGB",
    fill=(0, 0, 0)
)

draw.text(
    (width + 10, 10),
    "Segmentation",
    fill=(0, 0, 0)
)

draw.text(
    (width * 2 + 10, 10),
    "RGB + Segmentation",
    fill=(0, 0, 0)
)


# ============================================================
# SAVE DIAGNOSTIC
# ============================================================

canvas.save(
    OUTPUT,
    quality=95
)


# ============================================================
# OVERALL CLASS COUNTS
# ============================================================

print("\nOUTPUT")
print("-" * 80)

print(
    "Diagnostic image:"
)

print(OUTPUT)


print("\nOVERALL CLASS COUNTS")
print("-" * 80)


total_pixels = sum(
    total_counts.values()
)


for class_id in sorted(
    total_counts
):

    count = total_counts[
        class_id
    ]

    class_name = CLASS_NAMES.get(
        class_id,
        f"Unknown_{class_id}"
    )

    percentage = (
        count
        / total_pixels
        * 100
    )

    print(
        f"{class_name:<15} "
        f"{count:10d} "
        f"{percentage:7.2f}%"
    )


# ============================================================
# BUILDING / ROAD CHECK
# ============================================================

building_pixels = total_counts.get(
    2,
    0
)

road_pixels = total_counts.get(
    3,
    0
)


building_percentage = (
    building_pixels
    / total_pixels
    * 100
)

road_percentage = (
    road_pixels
    / total_pixels
    * 100
)


print("\nBUILDING / ROAD CHECK")
print("-" * 80)

print(
    f"Building prediction: "
    f"{building_percentage:.4f}%"
)

print(
    f"Road prediction: "
    f"{road_percentage:.4f}%"
)


# ============================================================
# FINAL STATUS
# ============================================================

print("\n" + "=" * 80)
print(
    "STATUS: SENTINEL-2 VISUAL DIAGNOSTIC CREATED"
)
print("=" * 80)