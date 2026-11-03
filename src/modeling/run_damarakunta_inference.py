import os
import sys

import numpy as np
import rasterio
import torch


# ------------------------------------------------------------------
# PROJECT PATHS
# ------------------------------------------------------------------

PROJECT_ROOT = r"D:\Telangana_Rural_Project"

MODEL_PROJECT = r"D:\new_MPS\remoteSensingWebApp"

TILE_DIR = os.path.join(
    PROJECT_ROOT,
    "Siddipet",
    "Damarakunta",
    "predictions",
    "input_tiles"
)

OUTPUT_DIR = os.path.join(
    PROJECT_ROOT,
    "Siddipet",
    "Damarakunta",
    "predictions",
    "segmentation_masks"
)

CHECKPOINT = os.path.join(
    MODEL_PROJECT,
    "checkpoints",
    "best_model.pth"
)

MODEL_FILE = os.path.join(
    MODEL_PROJECT,
    "project",
    "model.py"
)

os.makedirs(OUTPUT_DIR, exist_ok=True)


# ------------------------------------------------------------------
# ADD EXISTING MODEL PROJECT TO PYTHON PATH
# ------------------------------------------------------------------

if MODEL_PROJECT not in sys.path:
    sys.path.insert(0, MODEL_PROJECT)


from project.model import StrongDINOv2Seg


# ------------------------------------------------------------------
# CONFIGURATION
# ------------------------------------------------------------------

DEVICE = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
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

TILE_SIZE = 560


# ------------------------------------------------------------------
# HEADER
# ------------------------------------------------------------------

print("=" * 80)
print("PHASE 25 - DAMARAKUNTA STRONGDINOV2SEG INFERENCE")
print("=" * 80)


# ------------------------------------------------------------------
# CHECK FILES
# ------------------------------------------------------------------

print("\nPATH CHECK")
print("-" * 80)

print("Model file:", MODEL_FILE)
print("Model exists:", os.path.isfile(MODEL_FILE))

print("Checkpoint:", CHECKPOINT)
print("Checkpoint exists:", os.path.isfile(CHECKPOINT))

print("Tile directory:", TILE_DIR)
print("Tile directory exists:", os.path.isdir(TILE_DIR))


if not os.path.isfile(CHECKPOINT):

    print("\n[ERROR] Checkpoint not found.")
    raise SystemExit(1)


if not os.path.isdir(TILE_DIR):

    print("\n[ERROR] Tile directory not found.")
    raise SystemExit(1)


# ------------------------------------------------------------------
# FIND TILES
# ------------------------------------------------------------------

tile_files = sorted(
    [
        os.path.join(TILE_DIR, f)
        for f in os.listdir(TILE_DIR)
        if f.lower().endswith(".tif")
    ]
)


print("\nTILES")
print("-" * 80)

print("Number of tiles:", len(tile_files))


if len(tile_files) == 0:

    print("[ERROR] No TIFF tiles found.")
    raise SystemExit(1)


# ------------------------------------------------------------------
# LOAD MODEL
# ------------------------------------------------------------------

print("\nMODEL")
print("-" * 80)

print("Device:", DEVICE)

print("Loading StrongDINOv2Seg...")

model = StrongDINOv2Seg().to(DEVICE)


# ------------------------------------------------------------------
# LOAD CHECKPOINT
# ------------------------------------------------------------------

print("Loading checkpoint...")

checkpoint = torch.load(
    CHECKPOINT,
    map_location=DEVICE
)


# ------------------------------------------------------------------
# CHECKPOINT VALIDATION
# ------------------------------------------------------------------

if "state_dict" not in checkpoint:

    print("[ERROR] 'state_dict' not found in checkpoint.")

    print(
        "Available keys:",
        list(checkpoint.keys())
    )

    raise SystemExit(1)


# ------------------------------------------------------------------
# LOAD MODEL WEIGHTS
# ------------------------------------------------------------------
#
# strict=False is used because the checkpoint contains
# auxiliary-head parameters:
#
# aux1.weight
# aux1.bias
# aux2.weight
# aux2.bias
# aux3.weight
# aux3.bias
#
# The current StrongDINOv2Seg definition does not contain
# these auxiliary layers. They are therefore ignored for
# inference.
# ------------------------------------------------------------------

load_result = model.load_state_dict(
    checkpoint["state_dict"],
    strict=False
)


# ------------------------------------------------------------------
# REPORT CHECKPOINT LOADING
# ------------------------------------------------------------------

print("\nCHECKPOINT LOADING")
print("-" * 80)

print(
    "Missing keys:",
    len(load_result.missing_keys)
)

if len(load_result.missing_keys) > 0:

    print(
        "Missing key names:",
        load_result.missing_keys
    )


print(
    "Unexpected keys:",
    len(load_result.unexpected_keys)
)

if len(load_result.unexpected_keys) > 0:

    print(
        "Unexpected key names:",
        load_result.unexpected_keys
    )


# ------------------------------------------------------------------
# EVALUATION MODE
# ------------------------------------------------------------------

model.eval()


print("\nCheckpoint epoch:", checkpoint.get("epoch"))

print(
    "Training mIoU:",
    checkpoint.get("mIoU")
)

print(
    "Training mDice:",
    checkpoint.get("mDice")
)

print("Model loaded successfully.")


# ------------------------------------------------------------------
# INFERENCE
# ------------------------------------------------------------------

print("\nINFERENCE")
print("-" * 80)


overall_counts = np.zeros(
    8,
    dtype=np.int64
)


for index, tile_file in enumerate(
    tile_files,
    start=1
):

    print(
        f"\n[{index}/{len(tile_files)}] "
        f"{os.path.basename(tile_file)}"
    )


    # --------------------------------------------------------------
    # READ TILE
    # --------------------------------------------------------------

    with rasterio.open(tile_file) as src:

        image = src.read(
            indexes=[1, 2, 3]
        )

        profile = src.profile.copy()


        print(
            "  Input shape:",
            image.shape
        )


        # ----------------------------------------------------------
        # CONVERT CHW UINT8
        # -> HWC FLOAT32 RGB
        # -> CHW FLOAT32 TENSOR
        #
        # Same normalization used during training:
        # float32 / 255.0
        # ----------------------------------------------------------

        image = np.transpose(
            image,
            (1, 2, 0)
        )


        image = image.astype(
            np.float32
        ) / 255.0


        image = np.transpose(
            image,
            (2, 0, 1)
        )


        tensor = torch.from_numpy(
            image
        ).unsqueeze(0).to(DEVICE)


        # ----------------------------------------------------------
        # MODEL PREDICTION
        # ----------------------------------------------------------

        with torch.no_grad():

            logits = model(tensor)


            prediction = torch.argmax(
                logits,
                dim=1
            )


        # ----------------------------------------------------------
        # CONVERT PREDICTION TO NUMPY
        # ----------------------------------------------------------

        prediction = (
            prediction
            .squeeze(0)
            .cpu()
            .numpy()
            .astype(np.uint8)
        )


        # ----------------------------------------------------------
        # COUNT CLASSES
        # ----------------------------------------------------------

        unique, counts = np.unique(
            prediction,
            return_counts=True
        )


        for cls, count in zip(
            unique,
            counts
        ):

            if 0 <= cls < 8:

                overall_counts[cls] += count


        # ----------------------------------------------------------
        # SAVE SEGMENTATION MASK
        # ----------------------------------------------------------

        output_file = os.path.join(
            OUTPUT_DIR,
            os.path.basename(tile_file)
        )


        profile.update(
            count=1,
            dtype="uint8",
            nodata=0
        )


        with rasterio.open(
            output_file,
            "w",
            **profile
        ) as dst:

            dst.write(
                prediction,
                1
            )


        # ----------------------------------------------------------
        # PRINT TILE RESULT
        # ----------------------------------------------------------

        print(
            "  Output:",
            output_file
        )


        print(
            "  Classes detected:",
            {
                CLASS_NAMES[int(c)]: int(n)
                for c, n in zip(
                    unique,
                    counts
                )
            }
        )


# ------------------------------------------------------------------
# OVERALL SUMMARY
# ------------------------------------------------------------------

print("\n" + "=" * 80)

print(
    "OVERALL DAMARAKUNTA SEGMENTATION SUMMARY"
)

print("=" * 80)


total_pixels = int(
    overall_counts.sum()
)


print(
    "\nTotal predicted pixels:",
    total_pixels
)


print(
    f"\n{'Class':<15}"
    f"{'Pixels':>15}"
    f"{'Percentage':>15}"
)


print("-" * 45)


for cls in range(8):

    count = int(
        overall_counts[cls]
    )


    percentage = (
        count / total_pixels * 100
        if total_pixels > 0
        else 0
    )


    print(
        f"{CLASS_NAMES[cls]:<15}"
        f"{count:>15}"
        f"{percentage:>14.2f}%"
    )


# ------------------------------------------------------------------
# OUTPUT LOCATION
# ------------------------------------------------------------------

print("\nOutput directory:")

print(
    OUTPUT_DIR
)


# ------------------------------------------------------------------
# FINAL STATUS
# ------------------------------------------------------------------

print("\n" + "=" * 80)

print(
    "STATUS: DAMARAKUNTA INFERENCE COMPLETED."
)

print("=" * 80)