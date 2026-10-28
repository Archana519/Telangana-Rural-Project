import rasterio
from rasterio.windows import from_bounds

INPUT = r"D:\Telangana_Rural_Project\Siddipet\Damarakunta\aligned\damarakunta_esri_highres_mosaic_0p6m.tif"

OUTPUT = r"D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\residential_diagnostic_tile.tif"

CENTER_X = 261686.77
CENTER_Y = 1958952.67

SIZE_M = 336.0   # 560 pixels × 0.6 m

half = SIZE_M / 2

xmin = CENTER_X - half
xmax = CENTER_X + half
ymin = CENTER_Y - half
ymax = CENTER_Y + half

with rasterio.open(INPUT) as src:

    window = from_bounds(
        xmin, ymin,
        xmax, ymax,
        transform=src.transform
    )

    window = window.round_offsets().round_lengths()

    data = src.read(
        indexes=[1, 2, 3],
        window=window,
        boundless=True,
        fill_value=0
    )

    profile = src.profile.copy()
    profile.update(
        driver="GTiff",
        height=data.shape[1],
        width=data.shape[2],
        count=3,
        dtype=data.dtype,
        transform=src.window_transform(window),
        crs=src.crs
    )

    with rasterio.open(OUTPUT, "w", **profile) as dst:
        dst.write(data)

print("Residential diagnostic tile created.")
print("Center:", CENTER_X, CENTER_Y)
print("Size:", data.shape[2], "x", data.shape[1])
print("Saved:", OUTPUT)