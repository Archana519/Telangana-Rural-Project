import os
import numpy as np
import rasterio

PROJECT = r"D:\Telangana_Rural_Project"
VILLAGE = os.path.join(PROJECT, "Siddipet", "Angadi_Kistapur")

dem_path = os.path.join(
    VILLAGE,
    "aligned",
    "angadi_kistapur_dem.tif"
)

slope_path = os.path.join(
    VILLAGE,
    "aligned",
    "angadi_kistapur_slope.tif"
)

print("Reading DEM...")

with rasterio.open(dem_path) as src:

    dem = src.read(1).astype("float32")
    profile = src.profile.copy()

    nodata = src.nodata

    # Convert pixel size from degrees to approximate metres
    lat = (src.bounds.top + src.bounds.bottom) / 2.0

    pixel_width_m = (
        src.res[0] *
        111320 *
        np.cos(np.radians(lat))
    )

    pixel_height_m = src.res[1] * 111320

    print("Pixel width (m):", pixel_width_m)
    print("Pixel height (m):", pixel_height_m)

    # Replace NoData temporarily
    valid = dem != nodata

    safe_dem = dem.copy()
    safe_dem[~valid] = np.nan

    # Elevation gradients
    dz_dy, dz_dx = np.gradient(
        safe_dem,
        pixel_height_m,
        pixel_width_m
    )

    # Slope in degrees
    slope = np.degrees(
        np.arctan(
            np.sqrt(
                dz_dx ** 2 +
                dz_dy ** 2
            )
        )
    )

    slope = slope.astype("float32")

# Mark all invalid and NaN pixels as NoData
    slope[~np.isfinite(slope)] = -9999.0
    slope[~valid] = -9999.0

    profile.update(
        dtype="float32",
        count=1,
        nodata=-9999.0,
        compress="lzw"
    )

    with rasterio.open(slope_path, "w", **profile) as dst:
        dst.write(slope, 1)

print()
print("DONE")
print("Slope output:", slope_path)