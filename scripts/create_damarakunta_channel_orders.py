import os
import numpy as np
import rasterio
import matplotlib.pyplot as plt


INPUT = r"D:\Telangana_Rural_Project\Siddipet\Damarakunta\raw\imagery\damarakunta_sentinel_feb2022.tif"

OUTPUT = r"D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\channel_order_comparison.png"


with rasterio.open(INPUT) as src:
    bands = src.read()

print("=" * 80)
print("DAMARAKUNTA CHANNEL ORDER COMPARISON")
print("=" * 80)

print("Input:", INPUT)
print("Shape:", bands.shape)
print("Dtype:", bands.dtype)

# Convert each band to 0-1 using percentile stretching
def stretch(band):
    low = np.percentile(band, 2)
    high = np.percentile(band, 98)

    result = (band.astype(np.float32) - low) / (high - low)

    return np.clip(result, 0, 1)


b1 = stretch(bands[0])
b2 = stretch(bands[1])
b3 = stretch(bands[2])


orders = [
    ("Band 1 - Band 2 - Band 3", [b1, b2, b3]),
    ("Band 1 - Band 3 - Band 2", [b1, b3, b2]),
    ("Band 2 - Band 1 - Band 3", [b2, b1, b3]),
    ("Band 2 - Band 3 - Band 1", [b2, b3, b1]),
    ("Band 3 - Band 1 - Band 2", [b3, b1, b2]),
    ("Band 3 - Band 2 - Band 1", [b3, b2, b1]),
]


fig, axes = plt.subplots(
    2,
    3,
    figsize=(15, 10)
)


for ax, (title, channels) in zip(
    axes.ravel(),
    orders
):

    rgb = np.stack(
        channels,
        axis=2
    )

    ax.imshow(rgb)
    ax.set_title(title)
    ax.axis("off")


plt.tight_layout()

plt.savefig(
    OUTPUT,
    dpi=150,
    bbox_inches="tight"
)

plt.close()


print("\nOutput:")
print(OUTPUT)

print("\nSTATUS: CHANNEL ORDER COMPARISON COMPLETED")