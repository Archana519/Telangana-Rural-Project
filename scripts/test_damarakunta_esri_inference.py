from pathlib import Path
import sys

import numpy as np
import rasterio
import torch


# ============================================================
# PATHS
# ============================================================

MODEL_PROJECT = Path(
    r"D:\new_MPS\remoteSensingWebApp\project"
)

CHECKPOINT = Path(
    r"D:\new_MPS\remoteSensingWebApp\checkpoints\best_model.pth"
)

INPUT_DIR = Path(
    r"D:\Telangana_Rural_Project\Siddipet\Damarakunta"
    r"\predictions\esri_model_input_tiles"
)

OUTPUT_DIR = Path(
    r"D:\Telangana_Rural_Project\Siddipet\Damarakunta"
    r"\predictions\esri_test_masks"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# IMPORT MODEL
# ============================================================

sys.path.insert(
    0,
    str(MODEL_PROJECT)
)

from model import StrongDINOv2Seg


# ============================================================
# SETTINGS
# ============================================================

DEVICE = torch.device("cpu")

TEST_TILES = [
    "tile_0001.tif",
    "tile_0137.tif",
    "tile_0273.tif",
]

CLASS_NAMES = [
    "Ignore",
    "Background",
    "Building",
    "Road",
    "Water",
    "Barren",
    "Forest",
    "Agriculture",
]


# ============================================================
# START
# ============================================================

print("=" * 70)
print("DAMARAKUNTA ESRI STRONGDINOV2SEG TEST")
print("=" * 70)

print()
print("Device:", DEVICE)
print("Checkpoint:", CHECKPOINT)
print("Input:", INPUT_DIR)
print("Output:", OUTPUT_DIR)


# ============================================================
# CHECK FILES
# ============================================================

if not CHECKPOINT.exists():
    raise FileNotFoundError(
        f"Checkpoint not found: {CHECKPOINT}"
    )

for name in TEST_TILES:

    path = INPUT_DIR / name

    if not path.exists():
        raise FileNotFoundError(
            f"Input tile not found: {path}"
        )


# ============================================================
# LOAD MODEL
# ============================================================

print()
print("=" * 70)
print("LOADING STRONGDINOV2SEG")
print("=" * 70)

model = StrongDINOv2Seg()

checkpoint = torch.load(
    CHECKPOINT,
    map_location=DEVICE
)

if "state_dict" in checkpoint:

    state_dict = checkpoint["state_dict"]

    print()
    print(
        "Checkpoint epoch:",
        checkpoint.get("epoch")
    )

    print(
        "Training mIoU:",
        checkpoint.get("mIoU")
    )

    print(
        "Training mDice:",
        checkpoint.get("mDice")
    )

else:

    state_dict = checkpoint


missing, unexpected = model.load_state_dict(
    state_dict,
    strict=False
)

print()
print("Missing keys:", len(missing))
print("Unexpected keys:", len(unexpected))

if unexpected:
    print(
        "Unexpected keys:",
        unexpected
    )

model.to(DEVICE)
model.eval()

print()
print("Model loaded successfully.")


# ============================================================
# CLASS COUNTS
# ============================================================

total_counts = np.zeros(
    len(CLASS_NAMES),
    dtype=np.int64
)


# ============================================================
# RUN TEST TILES
# ============================================================

for tile_name in TEST_TILES:

    input_path = INPUT_DIR / tile_name

    print()
    print("-" * 70)
    print("Processing:", tile_name)
    print("-" * 70)

    # --------------------------------------------------------
    # READ IMAGE
    # --------------------------------------------------------

    with rasterio.open(input_path) as src:

        image = src.read(
            [1, 2, 3]
        )

        profile = src.profile.copy()

        print(
            "Input shape:",
            image.shape
        )

        print(
            "CRS:",
            src.crs
        )

        print(
            "Resolution:",
            src.res
        )

    # --------------------------------------------------------
    # SAME PREPROCESSING AS TRAINING
    # --------------------------------------------------------

    image = image.astype(
        np.float32
    ) / 255.0

    tensor = torch.from_numpy(
        image
    ).unsqueeze(0).to(
        DEVICE
    )

    # --------------------------------------------------------
    # INFERENCE
    # --------------------------------------------------------

    with torch.no_grad():

        output = model(
            tensor
        )

    # Handle possible tuple/dict outputs
    if isinstance(output, dict):

        if "out" in output:
            logits = output["out"]

        elif "logits" in output:
            logits = output["logits"]

        else:
            logits = next(
                value
                for value in output.values()
                if torch.is_tensor(value)
            )

    elif isinstance(output, (tuple, list)):

        logits = output[0]

    else:

        logits = output

    prediction = torch.argmax(
        logits,
        dim=1
    )[0].cpu().numpy().astype(
        np.uint8
    )

    # --------------------------------------------------------
    # COUNTS
    # --------------------------------------------------------

    unique, counts = np.unique(
        prediction,
        return_counts=True
    )

    print()
    print("Predicted classes:")

    tile_counts = np.zeros(
        len(CLASS_NAMES),
        dtype=np.int64
    )

    for cls, count in zip(
        unique,
        counts
    ):

        if cls < len(CLASS_NAMES):

            tile_counts[cls] = count
            total_counts[cls] += count

            percentage = (
                count
                / prediction.size
                * 100
            )

            print(
                f"{cls}: "
                f"{CLASS_NAMES[cls]:12s} "
                f"{count:8d} "
                f"({percentage:6.2f}%)"
            )

    # --------------------------------------------------------
    # SAVE MASK
    # --------------------------------------------------------

    output_path = (
        OUTPUT_DIR
        / tile_name.replace(
            ".tif",
            "_mask.tif"
        )
    )

    profile.update(
        {
            "count": 1,
            "dtype": "uint8",
            "nodata": 0,
        }
    )

    with rasterio.open(
        output_path,
        "w",
        **profile
    ) as dst:

        dst.write(
            prediction,
            1
        )

    print()
    print(
        "Mask saved:",
        output_path
    )


# ============================================================
# FINAL SUMMARY
# ============================================================

total_pixels = total_counts.sum()

print()
print("=" * 70)
print("3-TILE INFERENCE SUMMARY")
print("=" * 70)

print()
print("Total pixels:", total_pixels)

for cls, count in enumerate(
    total_counts
):

    if count > 0:

        percentage = (
            count
            / total_pixels
            * 100
        )

        print(
            f"{cls}: "
            f"{CLASS_NAMES[cls]:12s} "
            f"{count:10d} "
            f"({percentage:6.2f}%)"
        )


print()
print("=" * 70)

building_pct = (
    total_counts[2]
    / total_pixels
    * 100
)

road_pct = (
    total_counts[3]
    / total_pixels
    * 100
)

print(
    f"Building prediction: {building_pct:.4f}%"
)

print(
    f"Road prediction:     {road_pct:.4f}%"
)

print("=" * 70)

print()
print("Test inference completed.")
print("Masks:")
print(OUTPUT_DIR)