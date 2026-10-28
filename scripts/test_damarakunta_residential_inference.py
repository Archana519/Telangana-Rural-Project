import sys
import torch
import rasterio
import numpy as np

sys.path.insert(0, r"D:\new_MPS\remoteSensingWebApp\project")

from model import StrongDINOv2Seg


MODEL_PATH = r"D:\new_MPS\remoteSensingWebApp\checkpoints\best_model.pth"

INPUT = (
    r"D:\Telangana_Rural_Project\Siddipet\Damarakunta"
    r"\predictions\residential_diagnostic_tile.tif"
)


print("Loading model...")

model = StrongDINOv2Seg()

checkpoint = torch.load(
    MODEL_PATH,
    map_location="cpu"
)

model.load_state_dict(
    checkpoint["state_dict"],
    strict=False
)

model.eval()

print("Checkpoint epoch:", checkpoint.get("epoch"))
print("Training mIoU:", checkpoint.get("mIoU"))
print("Training mDice:", checkpoint.get("mDice"))


print("\nReading residential tile...")

with rasterio.open(INPUT) as src:
    image = src.read([1, 2, 3])

print("Input shape:", image.shape)
print("Input dtype:", image.dtype)


image = image.astype(np.float32) / 255.0

x = torch.from_numpy(image).unsqueeze(0)

print("Tensor shape:", x.shape)


print("\nRunning inference...")

with torch.no_grad():
    output = model(x)

if isinstance(output, (tuple, list)):
    output = output[0]

prediction = output.argmax(1).squeeze().numpy()


print("\nPrediction complete.")

print("Prediction shape:", prediction.shape)

names = [
    "Background",
    "Building",
    "Road",
    "Water",
    "Barren",
    "Forest",
    "Agriculture"
]

total = prediction.size

print("\nClass distribution:")

for i, name in enumerate(names):
    count = int((prediction == i).sum())
    percentage = 100.0 * count / total

    print(
        f"{name}: {count} pixels "
        f"({percentage:.2f}%)"
    )