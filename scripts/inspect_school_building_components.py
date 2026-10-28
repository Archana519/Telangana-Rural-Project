
import os
import numpy as np
import rasterio
from scipy import ndimage

BASE = r"D:\Telangana_Rural_Project\Siddipet\Damarakunta"
MASK_DIR = os.path.join(BASE, "predictions", "school_diagnostic_masks")

files = [
    "mpps_school_tile_mask.tif",
    "zphs_school_tile_mask.tif",
]

for filename in files:
    path = os.path.join(MASK_DIR, filename)

    with rasterio.open(path) as src:
        mask = src.read(1)
        pixel_area = abs(
            src.transform.a * src.transform.e
            - src.transform.b * src.transform.d
        )

    building = mask == 2
    labels, count = ndimage.label(
        building,
        structure=np.ones((3, 3), dtype=np.uint8)
    )

    sizes = np.bincount(labels.ravel())[1:]
    sizes = np.sort(sizes)[::-1]

    print("\n" + "=" * 50)
    print("FILE:", filename)
    print("Building pixels:", int(building.sum()))
    print("Building pixel area (m2):",
          round(int(building.sum()) * pixel_area, 2))
    print("Connected building-like regions:", int(count))
    print("Largest 10 regions (pixels):", sizes[:10].tolist())
    print("Largest 10 region areas (m2):",
          np.round(sizes[:10] * pixel_area, 2).tolist())
