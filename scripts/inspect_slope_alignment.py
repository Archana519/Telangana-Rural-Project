import rasterio
import numpy as np
from pathlib import Path

BASE = Path(r"D:\Telangana_Rural_Project\Siddipet\Angadi_Kistapur")

SLOPE_PATH = (
    BASE / "aligned" /
    "angadi_kistapur_slope_utm44n_10m.tif"
)

COST_PATH = (
    BASE / "aligned" /
    "angadi_kistapur_cost_surface.tif"
)

WORLD_PATH = (
    BASE / "aligned" /
    "angadi_kistapur_worldcover_utm44n.tif"
)

with rasterio.open(SLOPE_PATH) as slope_src, \
     rasterio.open(COST_PATH) as cost_src, \
     rasterio.open(WORLD_PATH) as world_src:

    slope = slope_src.read(1)
    cost = cost_src.read(1)
    world = world_src.read(1)

    print("=" * 80)
    print("SLOPE / COST / WORLDCOVER CHECK")
    print("=" * 80)

    print()
    print("Slope CRS:", slope_src.crs)
    print("Slope size:", slope_src.width, "x", slope_src.height)
    print("Slope resolution:", slope_src.res)
    print("Slope NoData:", slope_src.nodata)
    print("Slope bounds:", slope_src.bounds)

    print()
    print("Cost CRS:", cost_src.crs)
    print("Cost size:", cost_src.width, "x", cost_src.height)
    print("Cost NoData:", cost_src.nodata)

    print()
    print("WorldCover CRS:", world_src.crs)
    print("WorldCover size:", world_src.width, "x", world_src.height)

    print()
    print("=" * 80)
    print("F003 CANDIDATE 1 PIXELS")
    print("=" * 80)

    # Exact pixels found in the previous diagnostic
    pixels = [
        (73, 402),
        (72, 401)
    ]

    for row, col in pixels:

        print()
        print("Pixel:", row, col)

        print(
            "WorldCover:",
            int(world[row, col])
        )

        print(
            "Slope:",
            float(slope[row, col])
        )

        print(
            "Cost:",
            float(cost[row, col])
        )

    print()
    print("=" * 80)
    print("SLOPE VALUE SUMMARY")
    print("=" * 80)

    valid = slope[
        np.isfinite(slope) &
        (slope != -9999)
    ]

    print("Valid slope pixels:", len(valid))

    if len(valid) > 0:

        print("Minimum:", float(np.min(valid)))
        print("Maximum:", float(np.max(valid)))
        print("Mean:", float(np.mean(valid)))
        print("Median:", float(np.median(valid)))

    nodata_count = np.sum(slope == -9999)

    print("Slope NoData pixels:", int(nodata_count))

    print()
    print("=" * 80)
    print("DONE")
    print("=" * 80)