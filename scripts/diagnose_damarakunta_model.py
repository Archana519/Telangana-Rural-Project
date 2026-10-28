import os
import sys

import numpy as np
import rasterio
import torch
import torch.nn.functional as F


# ================================================================
# PATHS
# ================================================================

PROJECT_ROOT = r"D:\Telangana_Rural_Project"
MODEL_PROJECT = r"D:\new_MPS\remoteSensingWebApp"

TILE_FILE = os.path.join(
    PROJECT_ROOT,
    "Siddipet",
    "Damarakunta",
    "predictions",
    "input_tiles",
    "tile_000.tif"
)

CHECKPOINT = os.path.join(
    MODEL_PROJECT,
    "checkpoints",
    "best_model.pth"
)


# ================================================================
# MODEL
# ================================================================

if MODEL_PROJECT not in sys.path:
    sys.path.insert(0, MODEL_PROJECT)

from project.model import StrongDINOv2Seg


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


DEVICE = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)


# ================================================================
# HEADER
# ================================================================

print("=" * 80)
print("DAMARAKUNTA STRONGDINOV2SEG DIAGNOSTIC")
print("=" * 80)

print("\nINPUT FILE")
print("-" * 80)

print("Tile:", TILE_FILE)
print("Exists:", os.path.isfile(TILE_FILE))

print("Checkpoint:", CHECKPOINT)
print("Exists:", os.path.isfile(CHECKPOINT))


if not os.path.isfile(TILE_FILE):
    raise SystemExit("[ERROR] Tile not found.")

if not os.path.isfile(CHECKPOINT):
    raise SystemExit("[ERROR] Checkpoint not found.")


# ================================================================
# READ IMAGE
# ================================================================

print("\nIMAGE INSPECTION")
print("-" * 80)

with rasterio.open(TILE_FILE) as src:

    image = src.read(
        indexes=[1, 2, 3]
    )

    print("Shape:", image.shape)
    print("Dtype:", image.dtype)
    print("CRS:", src.crs)
    print("Resolution:", src.res)

    for band_index in range(3):

        band = image[band_index]

        print(
            f"Band {band_index + 1}: "
            f"min={band.min()} "
            f"max={band.max()} "
            f"mean={band.mean():.4f} "
            f"std={band.std():.4f}"
        )


# ================================================================
# PREPROCESS
# ================================================================

print("\nPREPROCESSING")
print("-" * 80)

image_hwc = np.transpose(
    image,
    (1, 2, 0)
)

image_float = (
    image_hwc.astype(np.float32) / 255.0
)

print(
    "Normalized min:",
    image_float.min()
)

print(
    "Normalized max:",
    image_float.max()
)

print(
    "Normalized mean:",
    image_float.mean()
)

print(
    "Normalized std:",
    image_float.std()
)


image_chw = np.transpose(
    image_float,
    (2, 0, 1)
)

tensor = torch.from_numpy(
    image_chw
).unsqueeze(0).to(DEVICE)


# ================================================================
# LOAD MODEL
# ================================================================

print("\nMODEL")
print("-" * 80)

print("Device:", DEVICE)

model = StrongDINOv2Seg().to(DEVICE)

checkpoint = torch.load(
    CHECKPOINT,
    map_location=DEVICE
)

load_result = model.load_state_dict(
    checkpoint["state_dict"],
    strict=False
)

model.eval()

print(
    "Missing keys:",
    load_result.missing_keys
)

print(
    "Unexpected keys:",
    load_result.unexpected_keys
)

print(
    "Checkpoint epoch:",
    checkpoint.get("epoch")
)

print(
    "Checkpoint mIoU:",
    checkpoint.get("mIoU")
)

print(
    "Checkpoint mDice:",
    checkpoint.get("mDice")
)


# ================================================================
# MODEL OUTPUT
# ================================================================

print("\nMODEL OUTPUT")
print("-" * 80)

with torch.no_grad():

    logits = model(tensor)

print(
    "Logits shape:",
    tuple(logits.shape)
)


# ================================================================
# LOGIT STATISTICS
# ================================================================

print("\nCLASS LOGIT STATISTICS")
print("-" * 80)

for cls in range(8):

    class_logits = logits[0, cls]

    print(
        f"{cls}: {CLASS_NAMES[cls]:<12} "
        f"mean={class_logits.mean().item():>10.5f} "
        f"std={class_logits.std().item():>10.5f} "
        f"min={class_logits.min().item():>10.5f} "
        f"max={class_logits.max().item():>10.5f}"
    )


# ================================================================
# SOFTMAX CONFIDENCE
# ================================================================

print("\nPREDICTION CONFIDENCE")
print("-" * 80)

probabilities = F.softmax(
    logits,
    dim=1
)

max_probability, prediction = torch.max(
    probabilities,
    dim=1
)

print(
    "Mean maximum probability:",
    max_probability.mean().item()
)

print(
    "Minimum maximum probability:",
    max_probability.min().item()
)

print(
    "Maximum maximum probability:",
    max_probability.max().item()
)


# ================================================================
# PREDICTION COUNTS
# ================================================================

print("\nPREDICTED CLASSES")
print("-" * 80)

prediction_np = (
    prediction
    .squeeze(0)
    .cpu()
    .numpy()
)

unique, counts = np.unique(
    prediction_np,
    return_counts=True
)

total = prediction_np.size

for cls, count in zip(unique, counts):

    percentage = (
        count / total * 100
    )

    print(
        f"{int(cls)}: "
        f"{CLASS_NAMES[int(cls)]:<12} "
        f"{int(count):>10} pixels "
        f"{percentage:>8.2f}%"
    )


# ================================================================
# CLASS-WISE MEAN PROBABILITY
# ================================================================

print("\nMEAN CLASS PROBABILITY")
print("-" * 80)

mean_probabilities = probabilities.mean(
    dim=(0, 2, 3)
).cpu().numpy()

for cls in range(8):

    print(
        f"{cls}: "
        f"{CLASS_NAMES[cls]:<12} "
        f"{mean_probabilities[cls]:.8f}"
    )


# ================================================================
# FINAL
# ================================================================

print("\n" + "=" * 80)
print("STATUS: DIAGNOSTIC COMPLETED")
print("=" * 80)