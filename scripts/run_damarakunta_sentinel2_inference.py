import os
import sys
import glob
import torch
import numpy as np
import rasterio

# ---------------------------------------------------------
# PATHS
# ---------------------------------------------------------

PROJECT = r"D:\Telangana_Rural_Project"

MODEL_PROJECT = r"D:\new_MPS\remoteSensingWebApp"

MODEL_FILE = os.path.join(
    MODEL_PROJECT,
    r"project\model.py"
)

CHECKPOINT = os.path.join(
    MODEL_PROJECT,
    r"checkpoints\best_model.pth"
)

INPUT_DIR = os.path.join(
    PROJECT,
    r"Siddipet\Damarakunta\predictions\sentinel2_input_tiles"
)

OUTPUT_DIR = os.path.join(
    PROJECT,
    r"Siddipet\Damarakunta\predictions\sentinel2_segmentation_masks"
)

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)

# ---------------------------------------------------------
# MODEL SETTINGS
# ---------------------------------------------------------

IMAGE_SIZE = 560
NUM_CLASSES = 8

CLASS_NAMES = [
    "Ignore",
    "Background",
    "Building",
    "Road",
    "Water",
    "Barren",
    "Forest",
    "Agriculture"
]

# ---------------------------------------------------------
# DEVICE
# ---------------------------------------------------------

DEVICE = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)

# ---------------------------------------------------------
# START
# ---------------------------------------------------------

print("=" * 60)
print("DAMARAKUNTA SENTINEL-2 STRONGDINOV2SEG INFERENCE")
print("=" * 60)

print("\nDevice:", DEVICE)

print("\nModel file:")
print(MODEL_FILE)

print("\nCheckpoint:")
print(CHECKPOINT)

print("\nInput directory:")
print(INPUT_DIR)

print("\nOutput directory:")
print(OUTPUT_DIR)

# ---------------------------------------------------------
# CHECK FILES
# ---------------------------------------------------------

if not os.path.exists(MODEL_FILE):
    raise FileNotFoundError(
        f"Model file not found:\n{MODEL_FILE}"
    )

if not os.path.exists(CHECKPOINT):
    raise FileNotFoundError(
        f"Checkpoint not found:\n{CHECKPOINT}"
    )

tile_files = sorted(
    glob.glob(
        os.path.join(
            INPUT_DIR,
            "*.tif"
        )
    )
)

if not tile_files:
    raise RuntimeError(
        "No Sentinel-2 model tiles found."
    )

print("\nTiles found:", len(tile_files))

for tile in tile_files:
    print(" -", os.path.basename(tile))

# ---------------------------------------------------------
# LOAD MODEL.PY
# ---------------------------------------------------------

print("\n" + "=" * 60)
print("LOADING STRONGDINOV2SEG")
print("=" * 60)

model_dir = os.path.dirname(MODEL_FILE)

if model_dir not in sys.path:
    sys.path.insert(
        0,
        model_dir
    )

from model import StrongDINOv2Seg

print("Model class imported successfully.")

# ---------------------------------------------------------
# CREATE MODEL
# ---------------------------------------------------------

model = StrongDINOv2Seg(
    
)

model = model.to(DEVICE)

# ---------------------------------------------------------
# LOAD CHECKPOINT
# ---------------------------------------------------------

print("\nLoading checkpoint...")

checkpoint = torch.load(
    CHECKPOINT,
    map_location=DEVICE
)

if "state_dict" in checkpoint:

    state_dict = checkpoint["state_dict"]

    model.load_state_dict(
        state_dict,
        strict=False
    )

    print("Checkpoint format: state_dict")

    if "epoch" in checkpoint:
        print(
            "Checkpoint epoch:",
            checkpoint["epoch"]
        )

    if "mIoU" in checkpoint:
        print(
            "Training mIoU:",
            checkpoint["mIoU"]
        )

    if "mDice" in checkpoint:
        print(
            "Training mDice:",
            checkpoint["mDice"]
        )

else:

    model.load_state_dict(
        checkpoint,
        strict=False
    )

    print("Checkpoint format: raw state_dict")

model.eval()

print("Model loaded successfully.")

# ---------------------------------------------------------
# TOTAL COUNTS
# ---------------------------------------------------------

total_pixels = 0

class_counts = np.zeros(
    NUM_CLASSES,
    dtype=np.int64
)

# ---------------------------------------------------------
# PROCESS TILES
# ---------------------------------------------------------

print("\n" + "=" * 60)
print("PROCESSING SENTINEL-2 TILES")
print("=" * 60)

for tile_index, tile_file in enumerate(
    tile_files,
    start=1
):

    tile_name = os.path.basename(
        tile_file
    )

    print(
        f"\n[{tile_index}/{len(tile_files)}] "
        f"{tile_name}"
    )

    # -----------------------------------------------------
    # READ TILE
    # -----------------------------------------------------

    with rasterio.open(tile_file) as src:

        image = src.read()

        profile = src.profile.copy()

        print(
            "Input shape:",
            image.shape
        )

        print(
            "Input dtype:",
            image.dtype
        )

        print(
            "CRS:",
            src.crs
        )

        print(
            "Resolution:",
            src.res
        )

        print(
            "Bounds:",
            src.bounds
        )

    # -----------------------------------------------------
    # VERIFY
    # -----------------------------------------------------

    if image.shape[0] != 3:
        raise RuntimeError(
            f"{tile_name}: expected 3 bands."
        )

    if (
        image.shape[1] != IMAGE_SIZE
        or image.shape[2] != IMAGE_SIZE
    ):
        raise RuntimeError(
            f"{tile_name}: expected "
            f"{IMAGE_SIZE}x{IMAGE_SIZE}."
        )

    # -----------------------------------------------------
    # MODEL PREPROCESSING
    #
    # Same preprocessing used by the existing model:
    #
    # uint8 RGB
    #       ↓
    # float32
    #       ↓
    # divide by 255
    #       ↓
    # CHW tensor
    # -----------------------------------------------------

    image_float = (
        image.astype(
            np.float32
        ) / 255.0
    )

    tensor = torch.from_numpy(
        image_float
    ).unsqueeze(0).to(DEVICE)

    # -----------------------------------------------------
    # INFERENCE
    # -----------------------------------------------------

    with torch.no_grad():

        output = model(
            tensor
        )

        # Handle models that return tuples/lists/dicts
        if isinstance(output, (tuple, list)):
            logits = output[0]

        elif isinstance(output, dict):

            if "out" in output:
                logits = output["out"]

            elif "logits" in output:
                logits = output["logits"]

            else:
                logits = next(
                    iter(output.values())
                )

        else:
            logits = output

        prediction = torch.argmax(
            logits,
            dim=1
        )

    prediction = (
        prediction
        .squeeze(0)
        .cpu()
        .numpy()
        .astype(np.uint8)
    )

    # -----------------------------------------------------
    # COUNT CLASSES
    # -----------------------------------------------------

    unique, counts = np.unique(
        prediction,
        return_counts=True
    )

    print("Predicted classes:")

    for class_id, count in zip(
        unique,
        counts
    ):

        if class_id < NUM_CLASSES:

            percentage = (
                count /
                prediction.size
            ) * 100.0

            print(
                f"  {class_id}: "
                f"{CLASS_NAMES[class_id]:12s} "
                f"{count:8d} "
                f"({percentage:6.2f}%)"
            )

            class_counts[
                class_id
            ] += count

    total_pixels += prediction.size

    # -----------------------------------------------------
    # SAVE MASK
    # -----------------------------------------------------

    output_file = os.path.join(
        OUTPUT_DIR,
        tile_name.replace(
            ".tif",
            "_mask.tif"
        )
    )

    mask_profile = profile.copy()

    mask_profile.update(
        dtype="uint8",
        count=1,
        compress="deflate"
    )

    with rasterio.open(
        output_file,
        "w",
        **mask_profile
    ) as dst:

        dst.write(
            prediction,
            1
        )

        dst.set_band_description(
            1,
            "StrongDINOv2Seg class prediction"
        )

        dst.update_tags(
            model="StrongDINOv2Seg",
            checkpoint=CHECKPOINT,
            source="Sentinel-2 L2A",
            scene=(
                "S2A_MSIL2A_20260429T051241T"
                "_R019_T43QHV_20260429T102710"
            )
        )

    print(
        "Saved mask:",
        output_file
    )

# ---------------------------------------------------------
# OVERALL RESULTS
# ---------------------------------------------------------

print("\n" + "=" * 60)
print("OVERALL SENTINEL-2 INFERENCE RESULTS")
print("=" * 60)

print(
    "Total predicted pixels:",
    total_pixels
)

for class_id in range(
    NUM_CLASSES
):

    count = class_counts[
        class_id
    ]

    percentage = (
        count /
        total_pixels *
        100.0
    )

    print(
        f"{CLASS_NAMES[class_id]:12s} "
        f"{count:10d} "
        f"{percentage:8.2f}%"
    )

# ---------------------------------------------------------
# BUILDING / ROAD SUMMARY
# ---------------------------------------------------------

building_percentage = (
    class_counts[2] /
    total_pixels *
    100.0
)

road_percentage = (
    class_counts[3] /
    total_pixels *
    100.0
)

print("\n" + "-" * 60)

print(
    "Building prediction:",
    f"{building_percentage:.4f}%"
)

print(
    "Road prediction:",
    f"{road_percentage:.4f}%"
)

print("-" * 60)

# ---------------------------------------------------------
# FINAL STATUS
# ---------------------------------------------------------

print("\n" + "=" * 60)
print("STATUS: SENTINEL-2 INFERENCE COMPLETED")
print("=" * 60)

print("\nMasks:")
print(OUTPUT_DIR)