import pandas as pd
import rasterio
import numpy as np
from pathlib import Path
import json
import math

BASE = Path(r"D:\Telangana_Rural_Project\Siddipet\Angadi_Kistapur")

CANDIDATE_PATH = (
    BASE / "results" /
    "phase18_candidate_routes_with_paths.csv"
)

COST_PATH = (
    BASE / "aligned" /
    "angadi_kistapur_cost_surface.tif"
)

WORLDCOVER_PATH = (
    BASE / "aligned" /
    "angadi_kistapur_worldcover_utm44n.tif"
)

df = pd.read_csv(CANDIDATE_PATH)

print("Routes:", len(df))

print()
print("Opening rasters...")

with rasterio.open(COST_PATH) as cost_src, \
     rasterio.open(WORLDCOVER_PATH) as wc_src:

    cost = cost_src.read(1)
    wc = wc_src.read(1)

    cost_transform = cost_src.transform
    wc_transform = wc_src.transform

    print("Cost CRS:", cost_src.crs)
    print("WorldCover CRS:", wc_src.crs)

    print("Cost size:", cost_src.width, "x", cost_src.height)
    print("WorldCover size:", wc_src.width, "x", wc_src.height)

    print()
    print("WorldCover classes:", sorted(
        np.unique(wc).tolist()
    ))

    def sample_edge(x1, y1, x2, y2, step_m=5.0):

        distance = math.hypot(
            x2 - x1,
            y2 - y1
        )

        count = max(
            2,
            int(math.ceil(distance / step_m)) + 1
        )

        xs = np.linspace(x1, x2, count)
        ys = np.linspace(y1, y2, count)

        return list(zip(xs, ys))

    print()
    print("=" * 80)
    print("WORLD COVER CHECK FOR COST=1000 ROUTE SAMPLES")
    print("=" * 80)

    for _, route in df.iterrows():

        path = json.loads(route["path_json"])

        samples = []

        for i in range(len(path) - 1):

            x1, y1 = path[i]
            x2, y2 = path[i + 1]

            samples.extend(
                sample_edge(
                    x1,
                    y1,
                    x2,
                    y2
                )
            )

        water = 0
        worldcover_nodata = 0
        outside_worldcover = 0
        usable_worldcover = 0
        cost_1000 = 0
        total = len(samples)

        classes = {}

        for x, y in samples:

            # Cost raster
            cost_row, cost_col = rasterio.transform.rowcol(
                cost_transform,
                x,
                y
            )

            if (
                0 <= cost_row < cost.shape[0]
                and 0 <= cost_col < cost.shape[1]
            ):

                cost_value = float(
                    cost[cost_row, cost_col]
                )

                if cost_value >= 1000:
                    cost_1000 += 1

            # WorldCover raster
            wc_row, wc_col = rasterio.transform.rowcol(
                wc_transform,
                x,
                y
            )

            if (
                wc_row < 0
                or wc_row >= wc.shape[0]
                or wc_col < 0
                or wc_col >= wc.shape[1]
            ):

                outside_worldcover += 1
                continue

            wc_value = int(
                wc[wc_row, wc_col]
            )

            classes[wc_value] = (
                classes.get(wc_value, 0) + 1
            )

            if wc_value == 80:
                water += 1

            elif wc_value == 0:
                worldcover_nodata += 1

            else:
                usable_worldcover += 1

        print()
        print(
            "Facility:",
            route["facility_id"],
            "| Candidate:",
            int(route["candidate_route"])
        )

        print(
            "Route length:",
            round(
                float(route["route_length_m"]),
                2
            ),
            "m"
        )

        print("Total samples:", total)
        print("Cost=1000 samples:", cost_1000)
        print("WorldCover WATER (80):", water)
        print("WorldCover NoData (0):", worldcover_nodata)
        print("Outside WorldCover:", outside_worldcover)
        print("Usable WorldCover:", usable_worldcover)

        print("WorldCover classes:", classes)

        if water > 0:
            print(">>> RESULT: ACTUAL WATER ENCOUNTERED")

        elif worldcover_nodata > 0 or outside_worldcover > 0:
            print(">>> RESULT: COVERAGE / NODATA ISSUE")

        else:
            print(">>> RESULT: NOT WATER")

print()
print("=" * 80)
print("DIAGNOSTIC COMPLETE")
print("=" * 80)