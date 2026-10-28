import sys
from pathlib import Path

import numpy as np
import rasterio
import torch
from PIL import Image
from torchvision import transforms

# Existing model
sys.path.insert(0, r"D:\new_MPS\remoteSensingWebApp\project")
from model import StrongDINOv2Seg


# --------------------------------------------------
# Paths
# --------------------------------------------------
IMAGE_PATH = Path(
    r"D:\Telangana_Rural_Project\Siddipet\Angadi_Kistapur\aligned\angadi_kistapur_utm44n.tif"
)

CHECKPOINT_PATH = Path(
    r"D:\new_MPS\remoteSensingWebApp\checkpoints\best_model.pth"
)


# --------------------------------------------------
# Basic checks
# --------------------------------------------------
print("=== REAL VILLAGE INFERENCE SMOKE TEST ===")

print("Image exists:", IMAGE_PATH.exists())
print("Checkpoint exists:", CHECKPOINT_PATH.exists())

if not IMAGE_PATH.exists():
    raise FileNotFoundError(IMAGE_PATH)

if not CHECKPOINT_PATH.exists():
    raise FileNotFoundError(CHECKPOINT_PATH)


# --------------------------------------------------
# Read GeoTIFF
# --------------------------------------------------
with rasterio.open(IMAGE_PATH) as src:
    image = src.read()
    print("\nGeoTIFF:")
    print("  Size:", src.width, "x", src.height)
    print("  Bands:", src.count)
    print("  CRS:", src.crs)
    print("  Dtype:", src.dtypes)
    print("  Resolution:", src.res)

# CHW -> HWC
image = np.transpose(image, (1, 2, 0))

print("  Array shape:", image.shape)
print("  Value range:", image.min(), "to", image.max())


# --------------------------------------------------
# Convert to RGB PIL image
# --------------------------------------------------
image = image.astype(np.uint8)
pil_image = Image.fromarray(image[:, :, :3], mode="RGB")


# --------------------------------------------------
# Same 560x560 input size used by the project
# --------------------------------------------------
transform = transforms.Compose([
    transforms.Resize((560, 560)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])

x = transform(pil_image).unsqueeze(0)

print("\nModel input:")
print("  Shape:", tuple(x.shape))
print("  Dtype:", x.dtype)


# --------------------------------------------------
# Create model
# --------------------------------------------------
print("\nCreating StrongDINOv2Seg...")

model = StrongDINOv2Seg()

checkpoint = torch.load(
    CHECKPOINT_PATH,
    map_location="cpu",
    weights_only=False
)

result = model.load_state_dict(
    checkpoint["state_dict"],
    strict=False
)

print("Missing keys:", len(result.missing_keys))
print("Unexpected keys:", len(result.unexpected_keys))

model.eval()


# --------------------------------------------------
# Inference
# --------------------------------------------------
print("\nRunning inference on CPU...")

with torch.no_grad():
    output = model(x)

print("Raw output type:", type(output))

if isinstance(output, dict):
    print("Output keys:", list(output.keys()))

    if "out" in output:
        logits = output["out"]
    else:
        logits = next(iter(output.values()))

elif isinstance(output, (tuple, list)):
    print("Number of outputs:", len(output))
    logits = output[0]

else:
    logits = output


print("Logits shape:", tuple(logits.shape))


# --------------------------------------------------
# Prediction
# --------------------------------------------------
prediction = torch.argmax(logits, dim=1)[0]

unique_classes = torch.unique(prediction).cpu().numpy().tolist()

print("\nPrediction:")
print("  Shape:", tuple(prediction.shape))
print("  Predicted classes:", unique_classes)

for cls in unique_classes:
    count = int((prediction == cls).sum().item())
    print(f"  Class {cls}: {count} pixels")

print("\n=== SMOKE TEST COMPLETED ===")