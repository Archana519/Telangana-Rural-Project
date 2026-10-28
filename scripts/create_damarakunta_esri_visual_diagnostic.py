from pathlib import Path
import numpy as np
import rasterio
from PIL import Image, ImageDraw

BASE = Path(r"D:\Telangana_Rural_Project\Siddipet\Damarakunta")

IMAGE_DIR = BASE / "predictions" / "esri_model_input_tiles"
MASK_DIR = BASE / "predictions" / "esri_test_masks"
OUTPUT_DIR = BASE / "results"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TILES = [
    "tile_0001",
    "tile_0137",
    "tile_0273",
]

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

COLORS = {
    0: (0, 0, 0),
    1: (80, 80, 80),
    2: (255, 0, 0),
    3: (255, 255, 0),
    4: (0, 0, 255),
    5: (180, 120, 60),
    6: (0, 180, 0),
    7: (255, 180, 0),
}


def read_rgb(path):
    with rasterio.open(path) as src:
        arr = src.read()

    arr = np.transpose(arr, (1, 2, 0))
    arr = arr[:, :, :3].astype(np.float32)

    out = np.zeros_like(arr, dtype=np.uint8)

    for c in range(3):
        band = arr[:, :, c]
        valid = band[np.isfinite(band)]

        if valid.size == 0:
            continue

        low = np.percentile(valid, 2)
        high = np.percentile(valid, 98)

        if high <= low:
            low = valid.min()
            high = valid.max()

        if high > low:
            scaled = (band - low) / (high - low)
            scaled = np.clip(scaled, 0, 1)
            out[:, :, c] = (scaled * 255).astype(np.uint8)
        else:
            out[:, :, c] = np.clip(band, 0, 255).astype(np.uint8)

    return out


def read_mask(path):
    with rasterio.open(path) as src:
        return src.read(1)


def colorize_mask(mask):
    h, w = mask.shape
    rgb = np.zeros((h, w, 3), dtype=np.uint8)

    for cls, color in COLORS.items():
        rgb[mask == cls] = color

    return rgb


def create_overlay(rgb, mask, alpha=0.45):
    mask_rgb = colorize_mask(mask)

    valid = mask > 0

    overlay = rgb.copy()

    overlay[valid] = (
        rgb[valid].astype(np.float32) * (1 - alpha)
        + mask_rgb[valid].astype(np.float32) * alpha
    ).astype(np.uint8)

    return overlay


def add_title(image, title):
    canvas = Image.new(
        "RGB",
        (image.width, image.height + 50),
        "white"
    )

    canvas.paste(image, (0, 50))

    draw = ImageDraw.Draw(canvas)
    draw.text((10, 15), title, fill="black")

    return canvas


def create_comparison(tile_name):

    image_path = IMAGE_DIR / f"{tile_name}.tif"
    mask_path = MASK_DIR / f"{tile_name}_mask.tif"

    print(f"\nProcessing {tile_name}")

    print(f"Image: {image_path}")
    print(f"Image exists: {image_path.exists()}")

    print(f"Mask: {mask_path}")
    print(f"Mask exists: {mask_path.exists()}")

    if not image_path.exists():
        raise FileNotFoundError(f"Missing image: {image_path}")

    if not mask_path.exists():
        raise FileNotFoundError(f"Missing mask: {mask_path}")

    rgb = read_rgb(image_path)
    mask = read_mask(mask_path)

    mask_rgb = colorize_mask(mask)
    overlay = create_overlay(rgb, mask)

    image_pil = Image.fromarray(rgb)
    mask_pil = Image.fromarray(mask_rgb)
    overlay_pil = Image.fromarray(overlay)

    image_pil = add_title(
        image_pil,
        f"{tile_name} - Original Esri RGB"
    )

    mask_pil = add_title(
        mask_pil,
        f"{tile_name} - StrongDINOv2Seg Prediction"
    )

    overlay_pil = add_title(
        overlay_pil,
        f"{tile_name} - Overlay"
    )

    width = rgb.shape[1]
    height = rgb.shape[0] + 50

    comparison = Image.new(
        "RGB",
        (width * 3, height),
        "white"
    )

    comparison.paste(image_pil, (0, 0))
    comparison.paste(mask_pil, (width, 0))
    comparison.paste(overlay_pil, (width * 2, 0))

    output_path = (
        OUTPUT_DIR /
        f"{tile_name}_esri_visual_diagnostic.jpg"
    )

    comparison.save(
        output_path,
        quality=95
    )

    print(f"Created: {output_path}")

    unique, counts = np.unique(mask, return_counts=True)

    print("\nPrediction summary:")

    for value, count in zip(unique, counts):

        name = CLASS_NAMES.get(
            int(value),
            f"Class_{value}"
        )

        percentage = (
            count /
            mask.size *
            100
        )

        print(
            f"  {int(value)} - "
            f"{name:12s}: "
            f"{count:8d} pixels "
            f"({percentage:6.2f}%)"
        )


def main():

    print("=" * 70)
    print("DAMARAKUNTA ESRI VISUAL DIAGNOSTIC")
    print("=" * 70)

    for tile in TILES:
        create_comparison(tile)

    print("\n" + "=" * 70)
    print("DIAGNOSTIC COMPLETED")
    print("=" * 70)


if __name__ == "__main__":
    main()