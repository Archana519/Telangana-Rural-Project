import os
import pandas as pd
import numpy as np


# =============================================================================
# PHASE 19 - MULTI-CRITERIA CANDIDATE EVALUATION
# =============================================================================

PROJECT_ROOT = r"D:\Telangana_Rural_Project"

RESULTS_DIR = os.path.join(
    PROJECT_ROOT,
    "Siddipet",
    "Angadi_Kistapur",
    "results"
)

CANDIDATE_EVAL_FILE = os.path.join(
    RESULTS_DIR,
    "phase18_new_road_candidate_evaluation.csv"
)

ROAD_COMPARISON_FILE = os.path.join(
    RESULTS_DIR,
    "phase19_candidate_existing_road_comparison.csv"
)

OUTPUT_FILE = os.path.join(
    RESULTS_DIR,
    "phase19_multi_criteria_evaluation.csv"
)


print("=" * 80)
print("PHASE 19 - MULTI-CRITERIA CANDIDATE EVALUATION")
print("=" * 80)


# =============================================================================
# LOAD INPUT FILES
# =============================================================================

print("\nLoading candidate evaluation...")
candidate_df = pd.read_csv(CANDIDATE_EVAL_FILE)

print("Loading existing-road comparison...")
road_df = pd.read_csv(ROAD_COMPARISON_FILE)


print("\nCandidate evaluation columns:")
print(list(candidate_df.columns))

print("\nExisting-road comparison columns:")
print(list(road_df.columns))


# =============================================================================
# CREATE ROUTE ID
# =============================================================================

candidate_df["route_id"] = (
    candidate_df["facility_id"].astype(str)
    + "_C"
    + candidate_df["candidate_route"].astype(str)
)


# =============================================================================
# MERGE EXISTING ROAD INFORMATION
# =============================================================================

df = candidate_df.merge(
    road_df[
        [
            "route_id",
            "existing_road_overlap_percentage",
            "estimated_new_connection_length_m",
            "route_class"
        ]
    ],
    on="route_id",
    how="left"
)


# =============================================================================
# NUMERIC CONVERSION
# =============================================================================

numeric_columns = [
    "route_length_m",
    "mean_cost",
    "water_samples",
    "coverage_gap_percentage",
    "existing_road_overlap_percentage",
    "estimated_new_connection_length_m"
]

for col in numeric_columns:
    if col in df.columns:
        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        )


# =============================================================================
# WATER HARD CONSTRAINT
# =============================================================================

df["water_constraint"] = np.where(
    df["water_samples"].fillna(0) > 0,
    "WATER_CONFLICT",
    "NO_WATER_CONFLICT"
)


# =============================================================================
# COVERAGE UNCERTAINTY
# =============================================================================
# The candidate evaluation CSV already contains coverage_gap_percentage.
# Therefore we directly use that value.

df["coverage_uncertainty"] = (
    df["coverage_gap_percentage"]
    .fillna(100)
    .clip(0, 100)
)


# =============================================================================
# NEW ROAD NEED
# =============================================================================

df["new_road_need"] = (
    1.0
    -
    (
        df["existing_road_overlap_percentage"]
        .fillna(100)
        / 100.0
    )
)

df["new_road_need"] = df["new_road_need"].clip(
    0,
    1
)


# =============================================================================
# EVALUABLE CANDIDATES
# =============================================================================

df["evaluation_status"] = np.where(
    (
        (df["route_status"] == "EVALUABLE")
        &
        (df["water_samples"].fillna(0) == 0)
        &
        (df["mean_cost"].notna())
        &
        (df["estimated_new_connection_length_m"].notna())
    ),
    "EVALUATED",
    "NOT_EVALUATED"
)


# =============================================================================
# NORMALIZATION FUNCTION
# =============================================================================

def normalize_within_facility(group, column):

    values = group[column].astype(float)

    valid = values.notna()

    result = pd.Series(
        np.nan,
        index=group.index,
        dtype=float
    )

    if valid.sum() == 0:
        return result

    minimum = values[valid].min()
    maximum = values[valid].max()

    if maximum == minimum:
        result.loc[valid] = 0.0
    else:
        result.loc[valid] = (
            (values[valid] - minimum)
            /
            (maximum - minimum)
        )

    return result


# =============================================================================
# CREATE NORMALIZED CRITERIA
# =============================================================================

df["norm_route_length"] = np.nan
df["norm_mean_cost"] = np.nan
df["norm_new_connection_length"] = np.nan
df["norm_coverage_uncertainty"] = np.nan


for facility_id, group in df.groupby("facility_id"):

    evaluable = group[
        group["evaluation_status"] == "EVALUATED"
    ].copy()

    if len(evaluable) == 0:
        continue

    # ---------------------------------------------------------
    # Route length
    # ---------------------------------------------------------

    df.loc[
        evaluable.index,
        "norm_route_length"
    ] = normalize_within_facility(
        evaluable,
        "route_length_m"
    )

    # ---------------------------------------------------------
    # Mean cost
    # ---------------------------------------------------------

    df.loc[
        evaluable.index,
        "norm_mean_cost"
    ] = normalize_within_facility(
        evaluable,
        "mean_cost"
    )

    # ---------------------------------------------------------
    # New road connection length
    # ---------------------------------------------------------

    df.loc[
        evaluable.index,
        "norm_new_connection_length"
    ] = normalize_within_facility(
        evaluable,
        "estimated_new_connection_length_m"
    )

    # ---------------------------------------------------------
    # Coverage uncertainty
    # ---------------------------------------------------------

    coverage_values = (
        evaluable["coverage_uncertainty"]
    )

    if coverage_values.max() == coverage_values.min():

        df.loc[
            evaluable.index,
            "norm_coverage_uncertainty"
        ] = 0.0

    else:

        df.loc[
            evaluable.index,
            "norm_coverage_uncertainty"
        ] = (
            (
                coverage_values
                -
                coverage_values.min()
            )
            /
            (
                coverage_values.max()
                -
                coverage_values.min()
            )
        )


# =============================================================================
# MULTI-CRITERIA WEIGHTS
# =============================================================================

WEIGHT_ROUTE_LENGTH = 0.35
WEIGHT_MEAN_COST = 0.30
WEIGHT_NEW_CONNECTION = 0.20
WEIGHT_COVERAGE = 0.15


# =============================================================================
# MULTI-CRITERIA SCORE
# =============================================================================

df["multi_criteria_score"] = (
    WEIGHT_ROUTE_LENGTH
    *
    df["norm_route_length"]
    +
    WEIGHT_MEAN_COST
    *
    df["norm_mean_cost"]
    +
    WEIGHT_NEW_CONNECTION
    *
    df["norm_new_connection_length"]
    +
    WEIGHT_COVERAGE
    *
    df["norm_coverage_uncertainty"]
)


# =============================================================================
# RANK WITHIN EACH FACILITY
# =============================================================================

df["candidate_rank"] = np.nan


for facility_id, group in df.groupby("facility_id"):

    evaluable = group[
        group["evaluation_status"] == "EVALUATED"
    ].copy()

    if len(evaluable) == 0:
        continue

    evaluable = evaluable.sort_values(
        "multi_criteria_score"
    )

    ranks = pd.Series(
        range(1, len(evaluable) + 1),
        index=evaluable.index,
        dtype=float
    )

    df.loc[
        evaluable.index,
        "candidate_rank"
    ] = ranks


# =============================================================================
# ROUTE INTERPRETATION
# =============================================================================

def classify_route(row):

    if row["evaluation_status"] != "EVALUATED":
        return "NOT_EVALUATED"

    if row["multi_criteria_score"] <= 0.33:
        return "LOW_COMBINED_COST"

    elif row["multi_criteria_score"] <= 0.66:
        return "MEDIUM_COMBINED_COST"

    else:
        return "HIGH_COMBINED_COST"


df["route_interpretation"] = df.apply(
    classify_route,
    axis=1
)


# =============================================================================
# SORT
# =============================================================================

df = df.sort_values(
    [
        "facility_id",
        "evaluation_status",
        "candidate_rank"
    ],
    ascending=[
        True,
        True,
        True
    ]
)


# =============================================================================
# SAVE
# =============================================================================

os.makedirs(
    RESULTS_DIR,
    exist_ok=True
)

df.to_csv(
    OUTPUT_FILE,
    index=False
)


# =============================================================================
# DISPLAY RESULTS
# =============================================================================

print("\n" + "=" * 80)
print("PHASE 19 RESULTS")
print("=" * 80)


display_columns = [
    "route_id",
    "facility_id",
    "candidate_route",
    "route_length_m",
    "mean_cost",
    "estimated_new_connection_length_m",
    "existing_road_overlap_percentage",
    "coverage_uncertainty",
    "water_samples",
    "route_status",
    "evaluation_status",
    "multi_criteria_score",
    "candidate_rank",
    "route_interpretation"
]


print(
    df[display_columns].to_string(
        index=False
    )
)


# =============================================================================
# SUMMARY
# =============================================================================

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)

print(
    "\nTotal candidates:",
    len(df)
)

print(
    "Evaluated candidates:",
    (
        df["evaluation_status"] == "EVALUATED"
    ).sum()
)

print(
    "Not evaluated:",
    (
        df["evaluation_status"] == "NOT_EVALUATED"
    ).sum()
)

print(
    "Water conflicts:",
    (
        df["water_samples"].fillna(0) > 0
    ).sum()
)


# =============================================================================
# LOWEST-SCORE CANDIDATE PER FACILITY
# =============================================================================

print(
    "\nLowest-score evaluated candidate "
    "within each facility:"
)


for facility_id, group in df.groupby(
    "facility_id"
):

    evaluated = group[
        group["evaluation_status"] == "EVALUATED"
    ]

    if len(evaluated) == 0:

        print(
            f"{facility_id}: "
            "No evaluable candidate"
        )

        continue

    selected = evaluated.loc[
        evaluated["multi_criteria_score"].idxmin()
    ]

    print(
        f"{facility_id} | "
        f"{selected['route_id']} | "
        f"score={selected['multi_criteria_score']:.4f} | "
        f"rank={int(selected['candidate_rank'])}"
    )


# =============================================================================
# OUTPUT
# =============================================================================

print("\nOutput saved to:")

print(
    OUTPUT_FILE
)

print("\n" + "=" * 80)

print(
    "PHASE 19 MULTI-CRITERIA "
    "EVALUATION COMPLETED"
)

print("=" * 80)