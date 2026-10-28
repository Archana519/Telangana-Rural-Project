
import os
import numpy as np
import rasterio

BASE = r"D:\Telangana_Rural_Project\Siddipet\Damarakunta"
MASK_DIR = os.path.join(BASE, "predictions", "school_diagnostic_masks")

class_names = {
    0: "Ignore",
    1: "Background",
    2: "Building",
    3: "Road",
    4: "Water",
    5: "Barren",
    6: "Forest",
    7: "Agriculture",
}

for filename in [
    "mpps_school_tile_mask.tif",
    "zphs_school_tile_mask.tif",
]:
    path = os.path.join(MASK_DIR, filename)

    with rasterio.open(path) as src:
        mask = src.read(1)

    values, counts = np.unique(mask, return_counts=True)

    print("\n", filename)
    print("Total pixels:", mask.size)

    for value, count in zip(values, counts):
        print(
            f"ID {value} ({class_names.get(int(value), 'Unknown')}): "
            f"{count} pixels ({count / mask.size * 100:.2f}%)"
        )
