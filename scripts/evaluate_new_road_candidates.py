import pandas as pd
import numpy as np
import rasterio
from pathlib import Path
import json
import math


BASE = Path(
    r"D:\Telangana_Rural_Project\Siddipet\Angadi_Kistapur"
)

INPUT_PATH = (
    BASE / "results" /
    "phase18_new_road_candidates.csv"
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
    "phase18_new_road_candidate_evaluation.csv"
)


print("=" * 80)
print("EVALUATING NEW ROAD CANDIDATES - CORRECTED")
print("=" * 80)


# ------------------------------------------------------------
# Load candidate routes
# ------------------------------------------------------------

print()
print("Loading candidate routes...")

df = pd.read_csv(INPUT_PATH)


# ------------------------------------------------------------
# Load rasters
# ------------------------------------------------------------

print("Loading cost surface...")
cost_src = rasterio.open(COST_PATH)
cost_array = cost_src.read(1)

print("Loading WorldCover...")
wc_src = rasterio.open(WORLDCOVER_PATH)
wc_array = wc_src.read(1)


# ------------------------------------------------------------
# Raster sampling helper
# ------------------------------------------------------------

def get_pixel_value(array, transform, x, y):

    col, row = ~transform * (x, y)

    col = int(math.floor(col))
    row = int(math.floor(row))

    if (
        row < 0
        or row >= array.shape[0]
        or col < 0
        or col >= array.shape[1]
    ):
        return None

    return array[row, col]


# ------------------------------------------------------------
# Evaluate candidates
# ------------------------------------------------------------

results = []


for _, row in df.iterrows():

    path = json.loads(row["path_json"])

    x1 = float(path[0][0])
    y1 = float(path[0][1])

    x2 = float(path[1][0])
    y2 = float(path[1][1])

    route_length = math.hypot(
        x2 - x1,
        y2 - y1
    )

    sample_count = max(
        2,
        int(math.ceil(route_length / 5.0))
    )

    xs = np.linspace(
        x1,
        x2,
        sample_count
    )

    ys = np.linspace(
        y1,
        y2,
        sample_count
    )

    valid_costs = []

    water_samples = 0
    invalid_samples = 0

    builtup_samples = 0
    cropland_samples = 0
    vegetation_samples = 0

    for x, y in zip(xs, ys):

        cost_value = get_pixel_value(
            cost_array,
            cost_src.transform,
            x,
            y
        )

        wc_value = get_pixel_value(
            wc_array,
            wc_src.transform,
            x,
            y
        )

        # ----------------------------------------------------
        # Outside raster
        # ----------------------------------------------------

        if (
            cost_value is None
            or wc_value is None
        ):
            invalid_samples += 1
            continue

        wc_value = int(wc_value)

        # ----------------------------------------------------
        # NoData
        # ----------------------------------------------------

        if wc_value == 0:
            invalid_samples += 1
            continue

        # ----------------------------------------------------
        # Water
        # ----------------------------------------------------

        if wc_value == 80:
            water_samples += 1
            continue

        # ----------------------------------------------------
        # Land-cover categories
        # ----------------------------------------------------

        if wc_value == 50:
            builtup_samples += 1

        elif wc_value == 40:
            cropland_samples += 1

        elif wc_value in [10, 20, 30, 60]:
            vegetation_samples += 1

        # ----------------------------------------------------
        # Valid cost
        # ----------------------------------------------------

        if cost_value < 1000:

            valid_costs.append(
                float(cost_value)
            )

        else:

            invalid_samples += 1

    # --------------------------------------------------------
    # Statistics
    # --------------------------------------------------------

    if valid_costs:

        mean_cost = float(
            np.mean(valid_costs)
        )

    else:

        mean_cost = np.nan

    total_samples = max(
        sample_count,
        1
    )

    water_percentage = (
        water_samples /
        total_samples
    ) * 100

    coverage_gap_percentage = (
        invalid_samples /
        total_samples
    ) * 100

    builtup_percentage = (
        builtup_samples /
        total_samples
    ) * 100

    cropland_percentage = (
        cropland_samples /
        total_samples
    ) * 100

    vegetation_percentage = (
        vegetation_samples /
        total_samples
    ) * 100

    # --------------------------------------------------------
    # Candidate status
    # --------------------------------------------------------

    if water_samples > 0:

        route_status = "REJECT_WATER"

    elif coverage_gap_percentage > 50:

        route_status = "LOW_COVERAGE"

    else:

        route_status = "EVALUABLE"

    results.append({

        "facility_id":
            row["facility_id"],

        "facility_name":
            row["facility_name"],

        "facility_type":
            row["facility_type"],

        "priority_group":
            row["priority_group"],

        "candidate_route":
            int(row["candidate_route"]),

        "route_length_m":
            route_length,

        "mean_cost":
            mean_cost,

        "water_samples":
            water_samples,

        "water_percentage":
            water_percentage,

        "invalid_samples":
            invalid_samples,

        "coverage_gap_percentage":
            coverage_gap_percentage,

        "builtup_percentage":
            builtup_percentage,

        "cropland_percentage":
            cropland_percentage,

        "vegetation_percentage":
            vegetation_percentage,

        "route_status":
            route_status
    })


result_df = pd.DataFrame(results)


# ------------------------------------------------------------
# Normalize only EVALUABLE candidates
# ------------------------------------------------------------

result_df["length_norm"] = np.nan
result_df["cost_norm"] = np.nan
result_df["combined_score"] = np.nan


for facility_id, group in result_df.groupby(
    "facility_id"
):

    valid = group[
        group["route_status"] == "EVALUABLE"
    ]

    if len(valid) == 0:
        continue

    # --------------------------------------------------------
    # Length normalization
    # --------------------------------------------------------

    min_length = valid["route_length_m"].min()
    max_length = valid["route_length_m"].max()

    if max_length > min_length:

        result_df.loc[
            valid.index,
            "length_norm"
        ] = (
            valid["route_length_m"] -
            min_length
        ) / (
            max_length -
            min_length
        )

    else:

        result_df.loc[
            valid.index,
            "length_norm"
        ] = 0.0

    # --------------------------------------------------------
    # Cost normalization
    # --------------------------------------------------------

    min_cost = valid["mean_cost"].min()
    max_cost = valid["mean_cost"].max()

    if max_cost > min_cost:

        result_df.loc[
            valid.index,
            "cost_norm"
        ] = (
            valid["mean_cost"] -
            min_cost
        ) / (
            max_cost -
            min_cost
        )

    else:

        result_df.loc[
            valid.index,
            "cost_norm"
        ] = 0.0

    # --------------------------------------------------------
    # Equal-weight multi-criteria score
    # --------------------------------------------------------

    result_df.loc[
        valid.index,
        "combined_score"
    ] = (
        0.50 *
        result_df.loc[
            valid.index,
            "length_norm"
        ]
        +
        0.50 *
        result_df.loc[
            valid.index,
            "cost_norm"
        ]
    )


# ------------------------------------------------------------
# Save
# ------------------------------------------------------------

result_df.to_csv(
    OUTPUT_PATH,
    index=False
)


# ------------------------------------------------------------
# Display
# ------------------------------------------------------------

print()
print("=" * 80)
print("CORRECTED CANDIDATE EVALUATION")
print("=" * 80)

print(
    result_df[
        [
            "facility_id",
            "candidate_route",
            "route_length_m",
            "mean_cost",
            "water_percentage",
            "coverage_gap_percentage",
            "builtup_percentage",
            "cropland_percentage",
            "vegetation_percentage",
            "route_status",
            "combined_score"
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