from pathlib import Path

import numpy as np
import rasterio

BASE = Path(r"D:\Telangana_Rural_Project\Siddipet\Damarakunta")
ALIGNED = BASE / "aligned"

WORLD_PATH = ALIGNED / "damarakunta_worldcover_10m.tif"
SLOPE_PATH = ALIGNED / "damarakunta_slope_10m.tif"
OUTPUT_PATH = ALIGNED / "damarakunta_cost_surface_10m.tif"
BLOCKED_PATH = ALIGNED / "damarakunta_prohibited_mask_10m.tif"

LAND_COST = {
    10: 8.0,   # Tree cover
    20: 5.0,   # Shrubland
    30: 3.0,   # Grassland
    40: 6.0,   # Cropland
    50: 2.0,   # Built-up
    60: 4.0,   # Bare/sparse vegetation
}

WATER_CLASS = 80
INVALID_CLASS = 0

SLOPE_MAX_DEGREES = 10.0
SLOPE_WEIGHT = 4.0

with rasterio.open(WORLD_PATH) as wc_src, \
     rasterio.open(SLOPE_PATH) as slope_src:

    world = wc_src.read(1)
    slope = slope_src.read(1)

    if wc_src.crs != slope_src.crs:
        raise ValueError("WorldCover and slope CRS do not match.")

    if world.shape != slope.shape:
        raise ValueError("WorldCover and slope dimensions do not match.")

    if not np.allclose(wc_src.transform, slope_src.transform):
        raise ValueError("WorldCover and slope grids do not match.")

    if wc_src.crs.to_epsg() != 32644:
        raise ValueError("Expected EPSG:32644.")

    valid_slope = (
        np.isfinite(slope)
        & (slope != slope_src.nodata)
        & (slope >= 0)
        & (slope <= 90)
    )

    cost = np.full(world.shape, np.nan, dtype=np.float32)
    blocked = np.ones(world.shape, dtype=np.uint8)

    for class_id, base_cost in LAND_COST.items():
        land = world == class_id
        cost[land] = base_cost

    valid_land = (
        np.isin(world, list(LAND_COST.keys()))
        & valid_slope
    )

    slope_penalty = (
        np.clip(slope, 0, SLOPE_MAX_DEGREES)
        / SLOPE_MAX_DEGREES
    ) * SLOPE_WEIGHT

    cost[valid_land] += slope_penalty[valid_land]
    blocked[valid_land] = 0

    # Water and unknown/NoData pixels remain blocked.
    cost[world == WATER_CLASS] = np.nan
    cost[world == INVALID_CLASS] = np.nan

    # Invalid slope means no reliable terrain cost.
    cost[~valid_slope] = np.nan
    blocked[~valid_slope] = 1

    profile = wc_src.profile.copy()
    profile.update(
        dtype="float32",
        count=1,
        nodata=-9999.0,
        compress="lzw"
    )

    saved_cost = np.where(
        np.isfinite(cost),
        cost,
        -9999.0
    ).astype(np.float32)

    with rasterio.open(OUTPUT_PATH, "w", **profile) as dst:
        dst.write(saved_cost, 1)

    mask_profile = wc_src.profile.copy()
    mask_profile.update(
        dtype="uint8",
        count=1,
        nodata=255,
        compress="lzw"
    )

    with rasterio.open(BLOCKED_PATH, "w", **mask_profile) as dst:
        dst.write(blocked, 1)

    usable = np.isfinite(cost)

    print("=" * 65)
    print("DAMARAKUNTA COST SURFACE")
    print("=" * 65)
    print("CRS:", wc_src.crs)
    print("Grid:", world.shape[1], "x", world.shape[0])
    print("Pixel size:", wc_src.res)
    print("Usable pixels:", int(usable.sum()))
    print("Prohibited/invalid pixels:", int((~usable).sum()))
    print("Water pixels:", int((world == WATER_CLASS).sum()))
    print("WorldCover NoData pixels:", int((world == INVALID_CLASS).sum()))
    print("Invalid slope pixels:", int((~valid_slope).sum()))

    if usable.any():
        print("Minimum cost:", float(cost[usable].min()))
        print("Maximum cost:", float(cost[usable].max()))
        print("Mean cost:", float(cost[usable].mean()))

    print("\nCost raster:", OUTPUT_PATH)
    print("Prohibited mask:", BLOCKED_PATH)
    print("\nCost surface created.")