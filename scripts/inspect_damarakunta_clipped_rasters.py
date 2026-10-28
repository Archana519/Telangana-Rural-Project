from pathlib import Path

import numpy as np
import rasterio

BASE = Path(r"D:\Telangana_Rural_Project\Siddipet\Damarakunta")

FILES = {
    "WorldCover": BASE / "raw" / "landcover" / "damarakunta_worldcover_clip.tif",
    "DEM": BASE / "raw" / "dem" / "damarakunta_dem_clip.tif",
}

for name, path in FILES.items():
    print("\n" + "=" * 60)
    print(name)
    print("Path:", path)

    with rasterio.open(path) as src:
        data = src.read(1, masked=True)
        valid = data.compressed()

        print("CRS:", src.crs)
        print("Dimensions:", src.width, "x", src.height)
        print("Bounds:", src.bounds)
        print("Pixel size:", src.res)
        print("NoData:", src.nodata)
        print("Masked pixels:", int(np.ma.getmaskarray(data).sum()))
        print("Valid pixels:", int(valid.size))

        if valid.size:
            print("Minimum:", float(valid.min()))
            print("Maximum:", float(valid.max()))

            if name == "WorldCover":
                values, counts = np.unique(valid, return_counts=True)
                print("Class counts:")
                for value, count in zip(values, counts):
                    print(f"  {value}: {count}")

            elif name == "DEM":
                print("Mean elevation:", float(valid.mean()))
                print("Elevation units must be verified from source metadata.")

print("\nInspection complete.")