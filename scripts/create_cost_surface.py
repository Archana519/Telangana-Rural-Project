import rasterio
import numpy as np
from pathlib import Path

BASE = Path(r"D:\Telangana_Rural_Project\Siddipet\Angadi_Kistapur")

WORLD_COVER_PATH = (
    BASE / "aligned" /
    "angadi_kistapur_worldcover_utm44n.tif"
)

SLOPE_PATH = (
    BASE / "aligned" /
    "angadi_kistapur_slope_filled_10m.tif"
)

OUTPUT_PATH = (
    BASE / "aligned" /
    "angadi_kistapur_cost_surface.tif"
)

# WorldCover class -> base planning cost
LAND_COST = {
    10: 8.0,       # Tree cover
    20: 5.0,       # Shrubland
    30: 3.0,       # Grassland
    40: 6.0,       # Cropland
    50: 2.0,       # Built-up
    60: 4.0,       # Bare / sparse vegetation
}

WATER_CLASS = 80
NODATA_CLASS = 0

WATER_COST = 1000.0
INVALID_COST = 1000.0

SLOPE_MAX = 10.0
SLOPE_WEIGHT = 4.0


with rasterio.open(WORLD_COVER_PATH) as wc_src, \
     rasterio.open(SLOPE_PATH) as slope_src:

    world = wc_src.read(1)
    slope = slope_src.read(1)

    print("=" * 80)
    print("CREATING CORRECTED COST SURFACE")
    print("=" * 80)

    print("WorldCover shape:", world.shape)
    print("Slope shape:", slope.shape)

    if world.shape != slope.shape:
        raise ValueError(
            "WorldCover and slope dimensions do not match."
        )

    if wc_src.crs != slope_src.crs:
        raise ValueError(
            "WorldCover and slope CRS do not match."
        )

    if not np.allclose(
        wc_src.transform,
        slope_src.transform
    ):
        raise ValueError(
            "WorldCover and slope transforms do not match."
        )

    cost = np.full(
        world.shape,
        INVALID_COST,
        dtype=np.float32
    )

    # ----------------------------------------------------------
    # LAND-COVER BASE COST
    # ----------------------------------------------------------

    for class_value, class_cost in LAND_COST.items():

        mask = world == class_value

        cost[mask] = class_cost

    # ----------------------------------------------------------
    # SLOPE PENALTY
    # ----------------------------------------------------------

    valid_slope = np.isfinite(slope)

    clipped_slope = np.clip(
        slope,
        0,
        SLOPE_MAX
    )

    slope_penalty = (
        clipped_slope / SLOPE_MAX
    ) * SLOPE_WEIGHT

    # Add slope penalty only to valid land-cover pixels.
    valid_land = (
        valid_slope &
        np.isin(
            world,
            list(LAND_COST.keys())
        )
    )

    cost[valid_land] += slope_penalty[valid_land]

    # ----------------------------------------------------------
    # WATER REMAINS PROHIBITED
    # ----------------------------------------------------------

    water_mask = world == WATER_CLASS

    cost[water_mask] = WATER_COST

    # ----------------------------------------------------------
    # WORLDCOVER NODATA REMAINS INVALID
    # ----------------------------------------------------------

    nodata_mask = world == NODATA_CLASS

    cost[nodata_mask] = INVALID_COST

    # ----------------------------------------------------------
    # SAVE
    # ----------------------------------------------------------

    profile = wc_src.profile.copy()

    profile.update(
        dtype="float32",
        nodata=INVALID_COST,
        compress="lzw"
    )

    with rasterio.open(
        OUTPUT_PATH,
        "w",
        **profile
    ) as dst:

        dst.write(cost, 1)

    print()
    print("Output:", OUTPUT_PATH)

    print()
    print("Cost statistics:")

    usable = cost < 1000

    print(
        "Usable pixels:",
        int(np.sum(usable))
    )

    print(
        "Prohibited/invalid pixels:",
        int(np.sum(~usable))
    )

    print(
        "Minimum usable cost:",
        float(np.min(cost[usable]))
        if np.any(usable)
        else "None"
    )

    print(
        "Maximum usable cost:",
        float(np.max(cost[usable]))
        if np.any(usable)
        else "None"
    )

    print(
        "Mean usable cost:",
        float(np.mean(cost[usable]))
        if np.any(usable)
        else "None"
    )

    print()
    print("Water pixels:", int(np.sum(water_mask)))
    print("WorldCover NoData pixels:", int(np.sum(nodata_mask)))

    print()
    print("=" * 80)
    print("COST SURFACE CREATED")
    print("=" * 80)