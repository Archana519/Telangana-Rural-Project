
from pathlib import Path
import numpy as np
import rasterio

base = Path(
    r"D:\Telangana_Rural_Project\Siddipet\Damarakunta"
)
aligned = base / "aligned"

files = {
    "WorldCover": aligned / "damarakunta_worldcover_10m.tif",
    "Slope": aligned / "damarakunta_slope_10m.tif",
    "Cost surface": aligned / "damarakunta_cost_surface_10m.tif",
    "Prohibited mask": aligned / "damarakunta_prohibited_mask_10m.tif",
}

for name, path in files.items():
    print(f"\n--- {name} ---")
    with rasterio.open(path) as src:
        arr = src.read(1)
        print("Exists:", path.exists())
        print("Shape:", arr.shape)
        print("CRS:", src.crs)
        print("NoData:", src.nodata)

        if name == "WorldCover":
            values, counts = np.unique(arr, return_counts=True)
            print("Class counts:", dict(zip(values.tolist(), counts.tolist())))
        elif name == "Slope":
            valid = np.isfinite(arr)
            if src.nodata is not None:
                valid &= arr != src.nodata
            valid &= (arr >= 0) & (arr <= 90)
            print("Valid slope pixels:", int(valid.sum()))
            if valid.any():
                print("Slope min/max:", float(arr[valid].min()),
                      float(arr[valid].max()))
        elif name == "Cost surface":
            valid = np.isfinite(arr)
            if src.nodata is not None:
                valid &= arr != src.nodata
            print("Valid cost pixels:", int(valid.sum()))
        elif name == "Prohibited mask":
            values, counts = np.unique(arr, return_counts=True)
            print("Mask value counts:", dict(zip(values.tolist(), counts.tolist())))
