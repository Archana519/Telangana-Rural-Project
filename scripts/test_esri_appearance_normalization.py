from PIL import Image
import numpy as np
import torch
import sys
from pathlib import Path
import rasterio

sys.path.insert(0, r"D:\new_MPS\remoteSensingWebApp\project")
from model import StrongDINOv2Seg

TILE = Path(
    r"D:\Telangana_Rural_Project\Siddipet\Damarakunta"
    r"\predictions\esri_model_input_tiles\tile_0001.tif"
)

CHECKPOINT = Path(
    r"D:\new_MPS\remoteSensingWebApp\checkpoints\best_model.pth"
)

OUT_DIR = Path(
    r"D:\Telangana_Rural_Project\Siddipet\Damarakunta"
    r"\results\appearance_tests"
)
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------
# Read RGB tile
# ------------------------------------------------------------
with rasterio.open(TILE) as src:
    rgb = np.transpose(src.read([1, 2, 3]), (1, 2, 0))

print("=" * 80)
print("ESRI APPEARANCE / RADIOMETRIC NORMALIZATION TEST")
print("=" * 80)
print("Tile:", TILE)
print("Shape:", rgb.shape)
print("Original dtype:", rgb.dtype)

# ------------------------------------------------------------
# Method 1: Original
# ------------------------------------------------------------
original = rgb.copy()

# ------------------------------------------------------------
# Method 2: Percentile contrast normalization
# ------------------------------------------------------------
def percentile_normalize(image):
    out = np.zeros_like(image, dtype=np.float32)

    for c in range(3):
        channel = image[:, :, c].astype(np.float32)

        lo = np.percentile(channel, 2)
        hi = np.percentile(channel, 98)

        out[:, :, c] = (channel - lo) / (hi - lo + 1e-6)
        out[:, :, c] = np.clip(out[:, :, c], 0, 1)

    return (out * 255).astype(np.uint8)

contrast = percentile_normalize(rgb)

# ------------------------------------------------------------
# Method 3: Per-channel mean/std normalization
# ------------------------------------------------------------
def mean_std_normalize(image):
    out = np.zeros_like(image, dtype=np.float32)

    target_mean = 128.0
    target_std = 60.0

    for c in range(3):
        channel = image[:, :, c].astype(np.float32)

        mean = channel.mean()
        std = channel.std()

        out[:, :, c] = (
            (channel - mean) / (std + 1e-6)
        ) * target_std + target_mean

    out = np.clip(out, 0, 255)

    return out.astype(np.uint8)

meanstd = mean_std_normalize(rgb)

# ------------------------------------------------------------
# Save diagnostic images
# ------------------------------------------------------------
Image.fromarray(original).save(
    OUT_DIR / "original.png"
)

Image.fromarray(contrast).save(
    OUT_DIR / "contrast_normalized.png"
)

Image.fromarray(meanstd).save(
    OUT_DIR / "meanstd_normalized.png"
)

# ------------------------------------------------------------
# Load model
# ------------------------------------------------------------
model = StrongDINOv2Seg()

checkpoint = torch.load(
    CHECKPOINT,
    map_location="cpu"
)

missing, unexpected = model.load_state_dict(
    checkpoint["state_dict"],
    strict=False
)

model.eval()

print()
print("Checkpoint epoch:", checkpoint.get("epoch"))
print("Missing keys:", len(missing))
print("Unexpected keys:", len(unexpected))

names = [
    "Ignore",
    "Background",
    "Building",
    "Road",
    "Water",
    "Barren",
    "Forest",
    "Agriculture"
]

# ------------------------------------------------------------
# Prediction function
# ------------------------------------------------------------
def predict(name, image):

    image = image.astype(np.float32) / 255.0

    x = torch.from_numpy(
        image.transpose(2, 0, 1)
    ).unsqueeze(0)

    print()
    print("-" * 80)
    print("TEST:", name)
    print(
        "Input range:",
        float(x.min()),
        float(x.max())
    )

    with torch.no_grad():
        output = model(x)

    if isinstance(output, (tuple, list)):
        output = output[0]

    pred = torch.argmax(
        output,
        dim=1
    )[0].numpy()

    values, counts = np.unique(
        pred,
        return_counts=True
    )

    for value, count in zip(values, counts):

        label = (
            names[int(value)]
            if int(value) < len(names)
            else str(value)
        )

        percentage = (
            100.0 * count / pred.size
        )

        print(
            f"{label:12s} "
            f"{count:8d} "
            f"{percentage:7.2f}%"
        )


# ------------------------------------------------------------
# Run all three
# ------------------------------------------------------------
predict("original", original)
predict("contrast_normalized", contrast)
predict("meanstd_normalized", meanstd)

print()
print("=" * 80)
print("APPEARANCE NORMALIZATION TEST COMPLETED")
print("=" * 80)