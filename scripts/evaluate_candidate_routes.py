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

OUTPUT_PATH = (
    BASE / "results" /
    "phase18_candidate_route_evaluation.csv"
)


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


df = pd.read_csv(CANDIDATE_PATH)

print("Candidate routes:", len(df))

results = []

with rasterio.open(COST_PATH) as cost_src, \
     rasterio.open(WORLDCOVER_PATH) as wc_src:

    cost = cost_src.read(1)
    wc = wc_src.read(1)

    cost_transform = cost_src.transform
    wc_transform = wc_src.transform

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

        valid_costs = []

        water_samples = 0
        nodata_samples = 0
        outside_samples = 0

        land_classes = {}

        for x, y in samples:

            # --------------------------------------------------
            # WORLD COVER CHECK
            # --------------------------------------------------

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

                outside_samples += 1
                continue

            wc_value = int(
                wc[wc_row, wc_col]
            )

            land_classes[wc_value] = (
                land_classes.get(wc_value, 0) + 1
            )

            # Water = 80
            if wc_value == 80:

                water_samples += 1
                continue

            # WorldCover NoData = 0
            if wc_value == 0:

                nodata_samples += 1
                continue

            # --------------------------------------------------
            # COST SURFACE
            # --------------------------------------------------

            cost_row, cost_col = rasterio.transform.rowcol(
                cost_transform,
                x,
                y
            )

            if (
                cost_row < 0
                or cost_row >= cost.shape[0]
                or cost_col < 0
                or cost_col >= cost.shape[1]
            ):

                outside_samples += 1
                continue

            cost_value = float(
                cost[cost_row, cost_col]
            )

            # Cost 1000 can no longer automatically mean water.
            # WorldCover has already identified actual water.

            if (
                np.isfinite(cost_value)
                and cost_value < 1000
            ):

                valid_costs.append(cost_value)

        total_samples = len(samples)

        valid_samples = len(valid_costs)

        coverage_gap_samples = (
            nodata_samples +
            outside_samples
        )

        water_prohibited = (
            water_samples > 0
        )

        coverage_gap = (
            coverage_gap_samples > 0
        )

        if valid_samples > 0:

            mean_cost = float(
                np.mean(valid_costs)
            )

            max_cost = float(
                np.max(valid_costs)
            )

        else:

            mean_cost = np.nan
            max_cost = np.nan

        results.append({
            "facility_id":
                route["facility_id"],

            "facility_name":
                route["facility_name"],

            "facility_type":
                route["facility_type"],

            "candidate_route":
                int(route["candidate_route"]),

            "route_length_m":
                float(route["route_length_m"]),

            "total_samples":
                total_samples,

            "valid_cost_samples":
                valid_samples,

            "water_samples":
                water_samples,

            "nodata_samples":
                nodata_samples,

            "outside_samples":
                outside_samples,

            "coverage_gap_samples":
                coverage_gap_samples,

            "water_prohibited":
                water_prohibited,

            "coverage_gap":
                coverage_gap,

            "mean_cost":
                mean_cost,

            "max_cost":
                max_cost,

            "land_classes":
                json.dumps(land_classes)
        })


result_df = pd.DataFrame(results)


# ----------------------------------------------------------
# NORMALIZATION WITHIN EACH FACILITY
# ----------------------------------------------------------

result_df["length_norm"] = 0.0
result_df["cost_norm"] = 0.0

for facility_id, group in result_df.groupby(
    "facility_id"
):

    indices = group.index

    min_length = group["route_length_m"].min()
    max_length = group["route_length_m"].max()

    if max_length > min_length:

        result_df.loc[
            indices,
            "length_norm"
        ] = (
            group["route_length_m"] - min_length
        ) / (
            max_length - min_length
        )

    costs = group["mean_cost"]

    valid_cost_group = costs.dropna()

    if len(valid_cost_group) > 0:

        min_cost = valid_cost_group.min()
        max_cost = valid_cost_group.max()

        if max_cost > min_cost:

            result_df.loc[
                indices,
                "cost_norm"
            ] = (
                costs - min_cost
            ) / (
                max_cost - min_cost
            )


# ----------------------------------------------------------
# MULTI-CRITERIA SCORE
# ----------------------------------------------------------

result_df["combined_cost"] = (
    0.40 * result_df["length_norm"] +
    0.60 * result_df["cost_norm"]
)


# Actual water gets a large penalty.
result_df.loc[
    result_df["water_prohibited"],
    "combined_cost"
] += 100


# Coverage gaps are NOT treated as water.
# They receive a smaller diagnostic penalty so they
# are visible during route comparison.
result_df.loc[
    (~result_df["water_prohibited"]) &
    (result_df["coverage_gap"]),
    "combined_cost"
] += 0.25


result_df = result_df.sort_values(
    [
        "facility_id",
        "combined_cost"
    ]
)


result_df.to_csv(
    OUTPUT_PATH,
    index=False
)


print()
print("=" * 80)
print("PHASE 18 ROUTE EVALUATION")
print("=" * 80)

print()

print(
    result_df[
        [
            "facility_id",
            "candidate_route",
            "route_length_m",
            "mean_cost",
            "water_samples",
            "coverage_gap_samples",
            "water_prohibited",
            "coverage_gap",
            "combined_cost"
        ]
    ].to_string(index=False)
)

print()
print("Saved:")
print(OUTPUT_PATH)

print()
print("=" * 80)
print("DONE")
print("=" * 80)