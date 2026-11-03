
from pathlib import Path
import numpy as np
import rasterio

base = Path(r"D:\Telangana_Rural_Project\Siddipet\Damarakunta\aligned")

files = [
    "damarakunta_cost_surface_10m.tif",
    "damarakunta_prohibited_mask_10m.tif",
    "damarakunta_worldcover_10m.tif",
    "damarakunta_slope_10m.tif",
]

datasets = []
try:
    for name in files:
        ds = rasterio.open(base / name)
        datasets.append(ds)
        print(f"\n{name}")
        print("  Shape:", ds.shape)
        print("  CRS:", ds.crs)
        print("  Transform:", ds.transform)
        print("  NoData:", ds.nodata)

    cost, mask, world, slope = [ds.read(1) for ds in datasets]

    valid = np.isfinite(cost) & (cost > 0)
    if datasets[0].nodata is not None:
        valid &= cost != datasets[0].nodata

    blocked = np.isfinite(mask) & (mask > 0)

    print("\n--- CELL COUNTS ---")
    print("Valid cost share:", round(float(valid.mean()), 6))
    print("Blocked mask share:", round(float(blocked.mean()), 6))
    print("Valid cost AND blocked:", int((valid & blocked).sum()))
    print("Invalid cost AND unblocked:", int((~valid & ~blocked).sum()))

    print("\nWorldCover class counts:")
    classes, counts = np.unique(world, return_counts=True)
    print(dict(zip(classes.tolist(), counts.tolist())))

    print("\nProhibited-mask values:")
    values, counts = np.unique(mask, return_counts=True)
    print(dict(zip(values.tolist(), counts.tolist())))

    print("\n--- GRID ALIGNMENT ---")
    ref = datasets[0]
    for name, ds in zip(files[1:], datasets[1:]):
        print(
            name,
            "same shape:", ds.shape == ref.shape,
            "same CRS:", ds.crs == ref.crs,
            "same transform:", ds.transform == ref.transform,
        )
finally:
    for ds in datasets:
        ds.close()
