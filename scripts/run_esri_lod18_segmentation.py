from pathlib import Path
import sys
import csv
import numpy as np
import torch
import rasterio
from rasterio.windows import Window
from rasterio.transform import xy

# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(r"D:\Telangana_Rural_Project")

TILES_DIR = (
    PROJECT_ROOT
    / "Siddipet"
    / "Angadi_Kistapur"
    / "aligned"
    / "esri_lod18_tiles_560"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "Siddipet"
    / "Angadi_Kistapur"
    / "predictions_esri_lod18"
)

MODEL_PROJECT = Path(r"D:\new_MPS\remoteSensingWebApp\project")

CHECKPOINT = (
    Path(r"D:\new_MPS\remoteSensingWebApp")
    / "checkpoints"
    / "best_model.pth"
)

IMAGE_SIZE = 560
NUM_CLASSES = 8

CLASS_NAMES = {
    0: "Ignore/No-data",
    1: "Background",
    2: "Building",
    3: "Road",
    4: "Water",
    5: "Barren",
    6: "Forest",
    7: "Agriculture",
}

# ImageNet normalization used for DINOv2-style models
MEAN = torch.tensor(
    [0.485, 0.456, 0.406],
    dtype=torch.float32
).view(1, 3, 1, 1)

STD = torch.tensor(
    [0.229, 0.224, 0.225],
    dtype=torch.float32
).view(1, 3, 1, 1)


# ============================================================
# IMPORT MODEL
# ============================================================

sys.path.insert(0, str(MODEL_PROJECT))

from model import StrongDINOv2Seg


# ============================================================
# MAIN
# ============================================================

def main():

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("PHASE 12 - VILLAGE SEGMENTATION")
    print("=" * 70)

    print("Tiles directory :", TILES_DIR)
    print("Checkpoint      :", CHECKPOINT)
    print("Output directory:", OUTPUT_DIR)
    print()

    # --------------------------------------------------------
    # Check paths
    # --------------------------------------------------------

    if not TILES_DIR.exists():
        raise FileNotFoundError(
            f"Tiles directory not found: {TILES_DIR}"
        )

    if not CHECKPOINT.exists():
        raise FileNotFoundError(
            f"Checkpoint not found: {CHECKPOINT}"
        )

    tile_files = sorted(TILES_DIR.glob("tile_*.tif"))

    if not tile_files:
        raise RuntimeError(
            "No tile TIFFs found in the tile directory."
        )

    print("Tiles found:", len(tile_files))

    # --------------------------------------------------------
    # Device
    # --------------------------------------------------------

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    print("Device:", device)

    if device.type == "cpu":
        print("WARNING: CPU inference may take considerable time.")

    print()

    # --------------------------------------------------------
    # Load model
    # --------------------------------------------------------

    print("Loading StrongDINOv2Seg...")

    model = StrongDINOv2Seg()

    checkpoint = torch.load(
        CHECKPOINT,
        map_location="cpu",
        weights_only=False
    )

    result = model.load_state_dict(
        checkpoint["state_dict"],
        strict=False
    )

    print("Checkpoint loaded.")
    print("Missing keys   :", len(result.missing_keys))
    print("Unexpected keys:", len(result.unexpected_keys))

    model.to(device)
    model.eval()

    # --------------------------------------------------------
    # Read first tile to establish output dimensions/metadata
    # --------------------------------------------------------

    with rasterio.open(tile_files[0]) as src:
        tile_width = src.width
        tile_height = src.height
        tile_crs = src.crs

    if tile_width != IMAGE_SIZE or tile_height != IMAGE_SIZE:
        raise RuntimeError(
            f"Unexpected tile size: "
            f"{tile_width} x {tile_height}"
        )

    # --------------------------------------------------------
    # Determine complete village raster extent
    # from tile positions
    # --------------------------------------------------------

    manifest_path = TILES_DIR / "tile_manifest.csv"

    if not manifest_path.exists():
        raise FileNotFoundError(
            f"Manifest not found: {manifest_path}"
        )

    with open(
        manifest_path,
        "r",
        encoding="utf-8"
    ) as f:
        rows = list(csv.DictReader(f))

    max_x = max(
        int(r["x_start"]) + IMAGE_SIZE
        for r in rows
    )

    max_y = max(
        int(r["y_start"]) + IMAGE_SIZE
        for r in rows
    )

    # --------------------------------------------------------
    # We need the original village raster transform
    # --------------------------------------------------------

    original_raster = (
        PROJECT_ROOT
        / "Siddipet"
        / "Angadi_Kistapur"
        / "aligned"
        / "angadi_kistapur_esri_reference_lod18_utm44n.tif"
    )

    with rasterio.open(original_raster) as src:
        original_transform = src.transform
        original_crs = src.crs
        original_width = src.width
        original_height = src.height

    if max_x != original_width or max_y != original_height:
        raise RuntimeError(
            "Tile coverage does not match original raster: "
            f"tiles={max_x}x{max_y}, "
            f"original={original_width}x{original_height}"
        )

    # --------------------------------------------------------
    # Accumulators
    #
    # Each pixel receives logits from every tile covering it.
    # Averaging logits reduces boundary effects from overlap.
    # --------------------------------------------------------

    logits_sum = np.zeros(
        (NUM_CLASSES, original_height, original_width),
        dtype=np.float32
    )

    logits_count = np.zeros(
        (original_height, original_width),
        dtype=np.float32
    )

    tile_prediction_rows = []

    # --------------------------------------------------------
    # Process tiles
    # --------------------------------------------------------

    for index, tile_path in enumerate(tile_files, start=1):

        print()
        print(
            f"[{index:02d}/{len(tile_files)}] "
            f"Processing {tile_path.name}"
        )

        # Find tile position
        matching = [
            r for r in rows
            if r["filename"] == tile_path.name
        ]

        if len(matching) != 1:
            raise RuntimeError(
                f"Manifest entry not found for {tile_path.name}"
            )

        row = matching[0]

        x_start = int(row["x_start"])
        y_start = int(row["y_start"])

        with rasterio.open(tile_path) as src:

            image = src.read()

        if image.shape != (3, IMAGE_SIZE, IMAGE_SIZE):
            raise RuntimeError(
                f"Unexpected image shape for "
                f"{tile_path.name}: {image.shape}"
            )

        # ----------------------------------------------------
        # Convert RGB uint8 -> normalized float tensor
        # ----------------------------------------------------

        image = image.astype(np.float32) / 255.0

        tensor = torch.from_numpy(image).unsqueeze(0)

    # No ImageNet normalization: training used RGB values divided by 255 only.

        tensor = tensor.to(device)

        # ----------------------------------------------------
        # Inference
        # ----------------------------------------------------

        with torch.no_grad():

            output = model(tensor)

            if isinstance(output, (tuple, list)):
                logits = output[0]
            else:
                logits = output

        if logits.ndim != 4:
            raise RuntimeError(
                f"Unexpected model output shape: "
                f"{tuple(logits.shape)}"
            )

        if logits.shape[1] != NUM_CLASSES:
            raise RuntimeError(
                f"Expected {NUM_CLASSES} classes, "
                f"got {logits.shape[1]}"
            )

        logits = logits.squeeze(0).cpu().numpy()

        # ----------------------------------------------------
        # Add tile logits to village accumulator
        # ----------------------------------------------------

        y_end = y_start + IMAGE_SIZE
        x_end = x_start + IMAGE_SIZE

        logits_sum[
            :,
            y_start:y_end,
            x_start:x_end
        ] += logits

        logits_count[
            y_start:y_end,
            x_start:x_end
        ] += 1.0

        # Tile-level prediction summary
        tile_pred = np.argmax(logits, axis=0)

        unique, counts = np.unique(
            tile_pred,
            return_counts=True
        )

        tile_counts = dict(
            zip(unique.tolist(), counts.tolist())
        )

        tile_prediction_rows.append(
            {
                "tile_id": index,
                "filename": tile_path.name,
                "x_start": x_start,
                "y_start": y_start,
                "building_pixels": tile_counts.get(2, 0),
                "road_pixels": tile_counts.get(3, 0),
                "water_pixels": tile_counts.get(4, 0),
                "forest_pixels": tile_counts.get(6, 0),
                "agriculture_pixels": tile_counts.get(7, 0),
            }
        )

        print(
            "  Building pixels:",
            tile_counts.get(2, 0)
        )

        print(
            "  Road pixels:",
            tile_counts.get(3, 0)
        )

    # --------------------------------------------------------
    # Check complete coverage
    # --------------------------------------------------------

    uncovered = np.sum(logits_count == 0)

    print()
    print("Uncovered pixels:", uncovered)

    if uncovered != 0:
        raise RuntimeError(
            f"{uncovered} pixels were not covered by tiles."
        )

    # --------------------------------------------------------
    # Average overlapping logits
    # --------------------------------------------------------

    logits_average = (
        logits_sum
        / logits_count[None, :, :]
    )

    # --------------------------------------------------------
    # Final class prediction
    # --------------------------------------------------------

    final_prediction = np.argmax(
        logits_average,
        axis=0
    ).astype(np.uint8)

    # --------------------------------------------------------
    # Save prediction GeoTIFF
    # --------------------------------------------------------

    prediction_tif = (
        OUTPUT_DIR
        / "angadi_kistapur_segmentation.tif"
    )

    with rasterio.open(
        prediction_tif,
        "w",
        driver="GTiff",
        height=original_height,
        width=original_width,
        count=1,
        dtype="uint8",
        crs=original_crs,
        transform=original_transform,
        compress="lzw",
        nodata=0
    ) as dst:

        dst.write(final_prediction, 1)

    # --------------------------------------------------------
    # Save class statistics
    # --------------------------------------------------------

    statistics_csv = (
        OUTPUT_DIR
        / "segmentation_class_statistics.csv"
    )

    with open(
        statistics_csv,
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.writer(f)

        writer.writerow(
            [
                "class_id",
                "class_name",
                "pixel_count",
                "percentage"
            ]
        )

        total_pixels = final_prediction.size

        for class_id in range(NUM_CLASSES):

            count = int(
                np.sum(final_prediction == class_id)
            )

            percentage = (
                count / total_pixels * 100.0
            )

            writer.writerow(
                [
                    class_id,
                    CLASS_NAMES[class_id],
                    count,
                    f"{percentage:.4f}"
                ]
            )

    # --------------------------------------------------------
    # Save tile summary
    # --------------------------------------------------------

    tile_csv = (
        OUTPUT_DIR
        / "tile_prediction_summary.csv"
    )

    with open(
        tile_csv,
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        fieldnames = [
            "tile_id",
            "filename",
            "x_start",
            "y_start",
            "building_pixels",
            "road_pixels",
            "water_pixels",
            "forest_pixels",
            "agriculture_pixels"
        ]

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames
        )

        writer.writeheader()
        writer.writerows(tile_prediction_rows)

    # --------------------------------------------------------
    # Final summary
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("SEGMENTATION COMPLETED")
    print("=" * 70)

    print("Tiles processed :", len(tile_files))
    print("Village size    :", original_width, "x", original_height)
    print("CRS             :", original_crs)
    print("Uncovered pixels:", uncovered)

    print()
    print("Final classes:")

    unique, counts = np.unique(
        final_prediction,
        return_counts=True
    )

    for class_id, count in zip(unique, counts):

        print(
            f"  {class_id} - "
            f"{CLASS_NAMES.get(class_id, 'Unknown'):12s}"
            f": {count:,} pixels"
        )

    print()
    print("Prediction GeoTIFF:")
    print(prediction_tif)

    print()
    print("Statistics:")
    print(statistics_csv)

    print()
    print("Tile summary:")
    print(tile_csv)


if __name__ == "__main__":
    main()
