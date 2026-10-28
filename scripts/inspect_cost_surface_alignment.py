import rasterio
import numpy as np
from pathlib import Path
import json
import math

BASE = Path(r"D:\Telangana_Rural_Project\Siddipet\Angadi_Kistapur")

COST_PATH = (
    BASE / "aligned" /
    "angadi_kistapur_cost_surface.tif"
)

WORLDCOVER_PATH = (
    BASE / "aligned" /
    "angadi_kistapur_worldcover_utm44n.tif"
)

CANDIDATE_PATH = (
    BASE / "results" /
    "phase18_candidate_routes_with_paths.csv"
)

import pandas as pd

df = pd.read_csv(CANDIDATE_PATH)

with rasterio.open(COST_PATH) as cost_src, \
     rasterio.open(WORLDCOVER_PATH) as wc_src:

    cost = cost_src.read(1)
    wc = wc_src.read(1)

    print("=" * 80)
    print("COST SURFACE / WORLD COVER ALIGNMENT CHECK")
    print("=" * 80)

    print()
    print("COST TRANSFORM:")
    print(cost_src.transform)

    print()
    print("WORLD COVER TRANSFORM:")
    print(wc_src.transform)

    print()
    print("COST BOUNDS:")
    print(cost_src.bounds)

    print()
    print("WORLD COVER BOUNDS:")
    print(wc_src.bounds)

    print()
    print("COST RESOLUTION:")
    print(cost_src.res)

    print()
    print("WORLD COVER RESOLUTION:")
    print(wc_src.res)

    print()
    print("=" * 80)
    print("F003 CANDIDATE 1 SAMPLE CHECK")
    print("=" * 80)

    route = df[
        (df["facility_id"] == "F003") &
        (df["candidate_route"] == 1)
    ].iloc[0]

    path = json.loads(route["path_json"])

    # Check the first few path points
    for i, point in enumerate(path[:5]):

        x, y = point

        cost_row, cost_col = rasterio.transform.rowcol(
            cost_src.transform,
            x,
            y
        )

        wc_row, wc_col = rasterio.transform.rowcol(
            wc_src.transform,
            x,
            y
        )

        print()
        print("Point:", i)
        print("X:", round(x, 3))
        print("Y:", round(y, 3))

        print(
            "Cost pixel:",
            cost_row,
            cost_col
        )

        print(
            "WorldCover pixel:",
            wc_row,
            wc_col
        )

        if (
            0 <= cost_row < cost.shape[0]
            and 0 <= cost_col < cost.shape[1]
        ):

            print(
                "Cost value:",
                float(cost[cost_row, cost_col])
            )

        else:

            print("Cost value: OUTSIDE")

        if (
            0 <= wc_row < wc.shape[0]
            and 0 <= wc_col < wc.shape[1]
        ):

            print(
                "WorldCover value:",
                int(wc[wc_row, wc_col])
            )

        else:

            print("WorldCover value: OUTSIDE")

    print()
    print("=" * 80)
    print("COST SURFACE VALUE COUNTS")
    print("=" * 80)

    unique, counts = np.unique(
        cost,
        return_counts=True
    )

    for value, count in zip(unique, counts):

        if value >= 900:

            print(
                "Cost value:",
                float(value),
                "| Pixels:",
                int(count)
            )

    print()
    print("=" * 80)
    print("WORLD COVER VALUE COUNTS")
    print("=" * 80)

    unique, counts = np.unique(
        wc,
        return_counts=True
    )

    for value, count in zip(unique, counts):

        print(
            "WorldCover:",
            int(value),
            "| Pixels:",
            int(count)
        )

    print()
    print("=" * 80)
    print("DONE")
    print("=" * 80)