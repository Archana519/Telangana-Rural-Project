from PIL import Image
import numpy as np
import torch
import sys
from pathlib import Path

sys.path.insert(0, r"D:\new_MPS\remoteSensingWebApp\project")
from model import StrongDINOv2Seg

ESRI_TILE = Path(
    r"D:\Telangana_Rural_Project\Siddipet\Damarakunta"
    r"\predictions\esri_model_input_tiles\tile_0001.tif"
)

CHECKPOINT = Path(
    r"D:\new_MPS\remoteSensingWebApp\checkpoints\best_model.pth"
)

OUT_DIR = Path(
    r"D:\Telangana_Rural_Project\Siddipet\Damarakunta"
    r"\results\scale_tests"
)
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------------
# Load Esri tile
# ------------------------------------------------------------------
import rasterio

with rasterio.open(ESRI_TILE) as src:
    arr = src.read([1, 2, 3])

# CHW -> HWC
rgb = np.transpose(arr, (1, 2, 0))

print("=" * 80)
print("ESRI SCALE-NORMALIZATION TEST")
print("=" * 80)
print("Original:", rgb.shape)
print("Resolution: 0.6 m/pixel")

# ------------------------------------------------------------------
# Create three scale/context versions
# ------------------------------------------------------------------
versions = {
    "original_560": rgb,
    "zoom_out_2x": np.array(
        Image.fromarray(rgb).resize((280, 280), Image.Resampling.BILINEAR)
    ),
    "zoom_out_4x": np.array(
        Image.fromarray(rgb).resize((140, 140), Image.Resampling.BILINEAR)
    ),
}

# Resize each back to model input size.
model_inputs = {}

for name, image in versions.items():
    image_560 = np.array(
        Image.fromarray(image).resize((560, 560), Image.Resampling.BILINEAR)
    )

    Image.fromarray(image_560).save(
        OUT_DIR / f"{name}_560.png"
    )

    model_inputs[name] = image_560

# ------------------------------------------------------------------
# Load model
# ------------------------------------------------------------------
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

# ------------------------------------------------------------------
# Run each test
# ------------------------------------------------------------------
for name, image in model_inputs.items():

    x = image.astype(np.float32) / 255.0
    x = torch.from_numpy(
        x.transpose(2, 0, 1)
    ).unsqueeze(0)

    print()
    print("-" * 80)
    print("TEST:", name)
    print("Input:", tuple(x.shape))
    print("Range:", float(x.min()), float(x.max()))

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

        percentage = 100.0 * count / pred.size

        print(
            f"{label:12s} "
            f"{count:8d} "
            f"{percentage:7.2f}%"
        )

print()
print("=" * 80)
print("SCALE TEST COMPLETED")
print("=" * 80)