import os
import sys
import torch
import numpy as np
import rasterio

# --------------------------------------------------
# Paths
# --------------------------------------------------

sys.path.insert(
    0,
    r"D:\new_MPS\remoteSensingWebApp\project"
)

from model import StrongDINOv2Seg


BASE = r"D:\Telangana_Rural_Project\Siddipet\Damarakunta"

IMAGE_PATH = os.path.join(
    BASE,
    "predictions",
    "residential_diagnostic_tile.tif"
)

MASK_PATH = os.path.join(
    BASE,
    "predictions",
    "residential_diagnostic_mask.tif"
)

MODEL_PATH = (
    r"D:\new_MPS\remoteSensingWebApp"
    r"\checkpoints\best_model.pth"
)

DEVICE = torch.device("cpu")


# --------------------------------------------------
# Check input files
# --------------------------------------------------

if not os.path.exists(IMAGE_PATH):
    print("ERROR: Residential diagnostic tile not found:")
    print(IMAGE_PATH)
    raise SystemExit(1)

if not os.path.exists(MODEL_PATH):
    print("ERROR: Model checkpoint not found:")
    print(MODEL_PATH)
    raise SystemExit(1)


# --------------------------------------------------
# Load model
# --------------------------------------------------

print("Loading model...")

model = StrongDINOv2Seg()

checkpoint = torch.load(
    MODEL_PATH,
    map_location=DEVICE
)

model.load_state_dict(
    checkpoint["state_dict"],
    strict=False
)

model.to(DEVICE)
model.eval()

print("Model loaded.")
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


# --------------------------------------------------
# Read residential diagnostic tile
# --------------------------------------------------

print("\nReading residential tile...")

with rasterio.open(IMAGE_PATH) as src:

    image = src.read([1, 2, 3])

    profile = src.profile.copy()

print("Input shape:", image.shape)
print("Input dtype:", image.dtype)

# --------------------------------------------------
# Prepare model input
# --------------------------------------------------

image_float = (
    image.astype(np.float32) / 255.0
)

tensor = torch.from_numpy(
    image_float
).unsqueeze(0).to(DEVICE)

print(
    "Tensor shape:",
    tuple(tensor.shape)
)

print(
    "Tensor dtype:",
    tensor.dtype
)

print(
    "Tensor range:",
    float(tensor.min()),
    "to",
    float(tensor.max())
)


# --------------------------------------------------
# Run inference
# --------------------------------------------------

print("\nRunning inference...")

with torch.no_grad():

    output = model(tensor)

    # Handle possible output formats
    if isinstance(output, (tuple, list)):

        output = output[0]

    elif isinstance(output, dict):

        if "out" in output:

            output = output["out"]

        else:

            output = next(
                iter(output.values())
            )

    print(
        "Model output shape:",
        tuple(output.shape)
    )

    prediction = torch.argmax(
        output,
        dim=1
    )[0].cpu().numpy().astype(np.uint8)


print(
    "Prediction shape:",
    prediction.shape
)


# --------------------------------------------------
# Save prediction mask
# --------------------------------------------------

profile.update(
    count=1,
    dtype="uint8",
    compress="lzw"
)

with rasterio.open(
    MASK_PATH,
    "w",
    **profile
) as dst:

    dst.write(
        prediction,
        1
    )


print(
    "\nResidential prediction mask saved:"
)

print(MASK_PATH)


# --------------------------------------------------
# Class distribution
# --------------------------------------------------

print("\nClass distribution:")

class_names = [
    "Background",
    "Building",
    "Road",
    "Water",
    "Barren",
    "Forest",
    "Agriculture"
]

total = prediction.size

for class_id, name in enumerate(class_names):

    count = int(
        np.sum(
            prediction == class_id
        )
    )

    percentage = (
        count / total
    ) * 100

    print(
        f"{name}: "
        f"{count:,} "
        f"({percentage:.2f}%)"
    )


# --------------------------------------------------
# Finish
# --------------------------------------------------

print("\n----------------------------------------")
print("RESIDENTIAL MASK CREATION COMPLETED")
print("----------------------------------------")