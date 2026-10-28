import os
import sys
import itertools
import numpy as np
import rasterio
import torch
import pandas as pd

MODEL_DIR = r"D:\new_MPS\remoteSensingWebApp\project"
CHECKPOINT = r"D:\new_MPS\remoteSensingWebApp\checkpoints\best_model.pth"

INPUT_TILE = (
    r"D:\Telangana_Rural_Project\Siddipet\Damarakunta"
    r"\predictions\input_tiles\tile_000.tif"
)

OUTPUT_DIR = (
    r"D:\Telangana_Rural_Project\Siddipet\Damarakunta"
    r"\results\channel_order_model_test"
)

os.makedirs(OUTPUT_DIR, exist_ok=True)

sys.path.insert(0, MODEL_DIR)

from model import StrongDINOv2Seg

DEVICE = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)

print("=" * 60)
print("DAMARAKUNTA CHANNEL ORDER MODEL TEST")
print("=" * 60)
print("Device:", DEVICE)
print("Input:", INPUT_TILE)
print("Checkpoint:", CHECKPOINT)

with rasterio.open(INPUT_TILE) as src:
    image = src.read()
    profile = src.profile

print("\nInput shape:", image.shape)
print("Input dtype:", image.dtype)

if image.shape[0] != 3:
    raise ValueError("Expected exactly 3 input bands.")

print("\nLoading StrongDINOv2Seg...")

model = StrongDINOv2Seg().to(DEVICE)

checkpoint = torch.load(
    CHECKPOINT,
    map_location=DEVICE,
    weights_only=False
)

load_result = model.load_state_dict(
    checkpoint["state_dict"],
    strict=False
)

print("Missing keys:", len(load_result.missing_keys))
print("Unexpected keys:", len(load_result.unexpected_keys))

model.eval()

print("Checkpoint epoch:", checkpoint.get("epoch"))
print("Training mIoU:", checkpoint.get("mIoU"))
print("Training mDice:", checkpoint.get("mDice"))

orders = list(itertools.permutations([0, 1, 2]))
results = []

print("\n" + "=" * 60)
print("TESTING ALL 6 CHANNEL ORDERS")
print("=" * 60)

with torch.no_grad():

    for order in orders:

        name = (
            f"Band {order[0] + 1} - "
            f"Band {order[1] + 1} - "
            f"Band {order[2] + 1}"
        )

        print("\nTesting:", name)

        reordered = image[list(order)]

        x = reordered.astype(np.float32) / 255.0

        x = torch.tensor(
            x,
            dtype=torch.float32
        ).unsqueeze(0).to(DEVICE)

        logits = model(x)

        if isinstance(logits, (tuple, list)):
            logits = logits[0]

        prediction = torch.argmax(
            logits,
            dim=1
        )[0].cpu().numpy()

        total_pixels = prediction.size

        counts = np.bincount(
            prediction.flatten(),
            minlength=8
        )

        percentages = (
            counts / total_pixels
        ) * 100.0

        building_pct = percentages[2]
        road_pct = percentages[3]

        print(
            f"Building: {building_pct:.4f}% | "
            f"Road: {road_pct:.4f}%"
        )

        results.append({
            "channel_order": name,
            "Building_percent": building_pct,
            "Road_percent": road_pct,
            "Water_percent": percentages[4],
            "Barren_percent": percentages[5],
            "Forest_percent": percentages[6],
            "Agriculture_percent": percentages[7],
            "Background_percent": percentages[1]
        })

        mask_path = os.path.join(
            OUTPUT_DIR,
            f"prediction_{order[0]+1}{order[1]+1}{order[2]+1}.tif"
        )

        mask_profile = profile.copy()
        mask_profile.update(
            count=1,
            dtype="uint8"
        )

        with rasterio.open(
            mask_path,
            "w",
            **mask_profile
        ) as dst:
            dst.write(
                prediction.astype(np.uint8),
                1
            )

df = pd.DataFrame(results)

csv_path = os.path.join(
    OUTPUT_DIR,
    "channel_order_model_results.csv"
)

df.to_csv(
    csv_path,
    index=False
)

print("\n" + "=" * 60)
print("FINAL RESULTS")
print("=" * 60)

print(
    df[
        [
            "channel_order",
            "Building_percent",
            "Road_percent",
            "Background_percent",
            "Barren_percent",
            "Agriculture_percent"
        ]
    ].to_string(index=False)
)

print("\nCSV saved:")
print(csv_path)

print("\nPrediction masks saved in:")
print(OUTPUT_DIR)

print("\nSTATUS: CHANNEL ORDER MODEL TEST COMPLETED")