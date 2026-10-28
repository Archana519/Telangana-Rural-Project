import os
import sys

import numpy as np
import rasterio
import torch

sys.path.insert(0, r"D:\new_MPS\remoteSensingWebApp\project")

from model import StrongDINOv2Seg


MODEL_PATH = r"D:\new_MPS\remoteSensingWebApp\checkpoints\best_model.pth"

INPUT_DIR = r"Siddipet\Damarakunta\predictions\school_diagnostic_tiles"
OUTPUT_DIR = r"Siddipet\Damarakunta\predictions\school_diagnostic_masks"

FILES = [
    "mpps_school_tile.tif",
    "zphs_school_tile.tif",
]


os.makedirs(OUTPUT_DIR, exist_ok=True)

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

print("Model loaded.")
print("Checkpoint epoch:", checkpoint.get("epoch"))
print("Training mIoU:", checkpoint.get("mIoU"))
print("Training mDice:", checkpoint.get("mDice"))


for filename in FILES:

    input_path = os.path.join(INPUT_DIR, filename)

    output_filename = filename.replace(
        ".tif",
        "_mask.tif"
    )

    output_path = os.path.join(
        OUTPUT_DIR,
        output_filename
    )

    print()
    print("Processing:", filename)

    with rasterio.open(input_path) as src:

        image = src.read()

        print("Input shape:", image.shape)

        image = image[:3]

        image = image.transpose(1, 2, 0)

        image = image.astype(np.float32) / 255.0

        tensor = torch.from_numpy(
            image
        ).permute(2, 0, 1).unsqueeze(0)

        with torch.no_grad():
            prediction = model(tensor)

        prediction = prediction.argmax(
            dim=1
        )[0].numpy().astype(np.uint8)

        profile = src.profile.copy()

        profile.update(
            driver="GTiff",
            height=prediction.shape[0],
            width=prediction.shape[1],
            count=1,
            dtype="uint8"
        )

        with rasterio.open(
            output_path,
            "w",
            **profile
        ) as dst:

            dst.write(prediction, 1)

    print("SAVED:", output_path)

print()
print("DONE")