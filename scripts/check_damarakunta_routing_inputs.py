
from pathlib import Path
import rasterio

BASE = Path(r"D:\Telangana_Rural_Project\Siddipet\Damarakunta")

files = {
    "Cost surface": BASE / "aligned" / "damarakunta_cost_surface_10m.tif",
    "WorldCover": BASE / "aligned" / "damarakunta_worldcover_10m.tif",
    "Slope": BASE / "aligned" / "damarakunta_slope_10m.tif",
    "Prohibited mask": BASE / "aligned" / "damarakunta_prohibited_mask_10m.tif",
}

print("=" * 65)
print("DAMARAKUNTA ROUTING INPUT CHECK")
print("=" * 65)

datasets = {}

for name, path in files.items():
    print(f"\n{name}: {path.exists()}")
    if not path.exists():
        continue

    with rasterio.open(path) as src:
        datasets[name] = {
            "crs": src.crs,
            "width": src.width,
            "height": src.height,
            "transform": src.transform,
            "nodata": src.nodata,
        }

        print("CRS:", src.crs)
        print("Dimensions:", src.width, "x", src.height)
        print("Pixel size:", src.res)
        print("NoData:", src.nodata)

print("\nGrid alignment:")
if len(datasets) == len(files):
    first = next(iter(datasets.values()))
    for name, info in datasets.items():
        matches = (
            info["crs"] == first["crs"]
            and info["width"] == first["width"]
            and info["height"] == first["height"]
            and info["transform"] == first["transform"]
        )
        print(f"{name}: {'MATCH' if matches else 'MISMATCH'}")
else:
    print("Cannot compare grids: one or more files are missing.")

print("\nNo files were changed.")
