import os
import rasterio
import numpy as np


FILE = r"D:\Telangana_Rural_Project\Siddipet\Damarakunta\raw\imagery\damarakunta_sentinel_feb2022.tif"


print("=" * 80)
print("DAMARAKUNTA SENTINEL BAND INSPECTION")
print("=" * 80)

print("\nFILE")
print("-" * 80)
print("File:", FILE)
print("Exists:", os.path.isfile(FILE))

if not os.path.isfile(FILE):
    raise SystemExit("[ERROR] GeoTIFF not found.")


with rasterio.open(FILE) as src:

    print("\nRASTER INFORMATION")
    print("-" * 80)

    print("Driver:", src.driver)
    print("Width:", src.width)
    print("Height:", src.height)
    print("Bands:", src.count)
    print("Dtype:", src.dtypes)
    print("CRS:", src.crs)
    print("Resolution:", src.res)
    print("Bounds:", src.bounds)
    print("NoData:", src.nodata)

    print("\nCOLOR INTERPRETATION")
    print("-" * 80)

    print(
        "Color interpretation:",
        src.colorinterp
    )

    print("\nBAND DESCRIPTIONS")
    print("-" * 80)

    print(
        "Descriptions:",
        src.descriptions
    )

    print("\nBAND TAGS")
    print("-" * 80)

    for band in range(1, src.count + 1):

        print(
            f"\nBand {band}:"
        )

        print(
            src.tags(band)
        )

    print("\nDATASET TAGS")
    print("-" * 80)

    print(src.tags())

    print("\nBAND STATISTICS")
    print("-" * 80)

    bands = []

    for band in range(1, src.count + 1):

        data = src.read(band)

        bands.append(
            data.astype(np.float64)
        )

        print(
            f"\nBand {band}"
        )

        print(
            "  Min:",
            data.min()
        )

        print(
            "  Max:",
            data.max()
        )

        print(
            "  Mean:",
            f"{data.mean():.4f}"
        )

        print(
            "  Std:",
            f"{data.std():.4f}"
        )

        print(
            "  Median:",
            f"{np.median(data):.4f}"
        )

        print(
            "  Percentile 1:",
            f"{np.percentile(data, 1):.4f}"
        )

        print(
            "  Percentile 99:",
            f"{np.percentile(data, 99):.4f}"
        )

    print("\nBAND CORRELATION")
    print("-" * 80)

    flat_bands = [
        band.reshape(-1)
        for band in bands
    ]

    correlation = np.corrcoef(
        flat_bands
    )

    print(correlation)


print("\n" + "=" * 80)
print("STATUS: BAND INSPECTION COMPLETED")
print("=" * 80)