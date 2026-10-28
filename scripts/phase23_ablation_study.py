import os
import pandas as pd
import numpy as np


# =============================================================================
# PHASE 23 - ABLATION STUDY
# =============================================================================

PROJECT_ROOT = r"D:\Telangana_Rural_Project"

RESULTS_DIR = os.path.join(
    PROJECT_ROOT,
    "Siddipet",
    "Angadi_Kistapur",
    "results"
)

MULTI_CRITERIA_FILE = os.path.join(
    RESULTS_DIR,
    "phase19_multi_criteria_evaluation.csv"
)

ROAD_COMPARISON_FILE = os.path.join(
    RESULTS_DIR,
    "phase19_candidate_existing_road_comparison.csv"
)

OUTPUT_FILE = os.path.join(
    RESULTS_DIR,
    "phase23_ablation_study.csv"
)


print("=" * 80)
print("PHASE 23 - ABLATION STUDY")
print("=" * 80)


# =============================================================================
# LOAD DATA
# =============================================================================

print("\nLoading Phase 19 multi-criteria results...")

mc = pd.read_csv(MULTI_CRITERIA_FILE)

print(
    "Multi-criteria candidates:",
    len(mc)
)


print("\nLoading Phase 19 existing-road comparison...")

road = pd.read_csv(ROAD_COMPARISON_FILE)

print(
    "Road-comparison candidates:",
    len(road)
)


# =============================================================================
# CREATE ROUTE ID
# =============================================================================

mc["route_id"] = (
    mc["facility_id"].astype(str)
    + "_C"
    + mc["candidate_route"].astype(str)
)

road["route_id"] = (
    road["facility_id"].astype(str)
    + "_C"
    + road["candidate_route"].astype(str)
)


# =============================================================================
# KEEP ONLY REQUIRED ROAD COMPARISON COLUMNS
# =============================================================================

road_required = road[
    [
        "route_id",
        "estimated_new_connection_length_m",
        "existing_road_overlap_percentage",
        "route_class"
    ]
].copy()


# =============================================================================
# MERGE
# =============================================================================

df = pd.merge(
    mc,
    road_required,
    on="route_id",
    how="left"
)


# =============================================================================
# HANDLE POSSIBLE COLUMN-NAME SUFFIXES
# =============================================================================
#
# If the same column exists in both input files, pandas may create:
#
#     column_x
#     column_y
#
# We explicitly resolve that here.
# =============================================================================

if "estimated_new_connection_length_m" not in df.columns:

    if "estimated_new_connection_length_m_y" in df.columns:

        df["estimated_new_connection_length_m"] = (
            df["estimated_new_connection_length_m_y"]
        )

    elif "estimated_new_connection_length_m_x" in df.columns:

        df["estimated_new_connection_length_m"] = (
            df["estimated_new_connection_length_m_x"]
        )

    else:

        raise ValueError(
            "ERROR: estimated_new_connection_length_m "
            "was not found after merging Phase 19 files."
        )


if "existing_road_overlap_percentage" not in df.columns:

    if "existing_road_overlap_percentage_y" in df.columns:

        df["existing_road_overlap_percentage"] = (
            df["existing_road_overlap_percentage_y"]
        )

    elif "existing_road_overlap_percentage_x" in df.columns:

        df["existing_road_overlap_percentage"] = (
            df["existing_road_overlap_percentage_x"]
        )

    else:

        raise ValueError(
            "ERROR: existing_road_overlap_percentage "
            "was not found after merging Phase 19 files."
        )


# =============================================================================
# CHECK MERGE
# =============================================================================

print("\nMerged candidates:", len(df))

print(
    "Estimated new-road length column available:",
    "estimated_new_connection_length_m"
    in df.columns
)


# =============================================================================
# KEEP SAME EVALUABLE CANDIDATES
# =============================================================================
#
# This keeps the ablation comparison fair.
#
# Candidates with:
#   - low coverage
#   - water conflict
#   - missing cost
#   - missing new-road length
#
# are excluded from ranking.
# =============================================================================

df["evaluable"] = (
    (df["route_status"] == "EVALUABLE")
    &
    (df["water_samples"] == 0)
    &
    (df["mean_cost"].notna())
    &
    (df["estimated_new_connection_length_m"].notna())
)


print(
    "Evaluable candidates:",
    int(df["evaluable"].sum())
)


# =============================================================================
# NORMALIZATION FUNCTION
# =============================================================================

def minmax_normalize(series):

    minimum = series.min()
    maximum = series.max()

    if pd.isna(minimum) or pd.isna(maximum):

        return pd.Series(
            0.0,
            index=series.index
        )

    if maximum == minimum:

        return pd.Series(
            0.0,
            index=series.index
        )

    return (
        (series - minimum)
        /
        (maximum - minimum)
    )


# =============================================================================
# CREATE ABLATION SCORES
# =============================================================================
#
# All scores are calculated separately within each facility.
#
# Lower score = lower combined criterion value.
#
# FULL MODEL:
#   Length             35%
#   Mean cost          30%
#   New-road length    20%
#   Coverage           15%
#
# ABLATIONS:
#
#   1. FULL_MODEL
#   2. WITHOUT_COST
#   3. WITHOUT_NEW_ROAD_LENGTH
#   4. LENGTH_ONLY
#
# Removed criteria are redistributed proportionally among the remaining
# criteria.
# =============================================================================

all_results = []


for facility_id, group in df.groupby("facility_id"):

    group = group.copy()

    valid = group["evaluable"]

    if valid.sum() == 0:
        continue

    work = group.loc[valid].copy()


    # =========================================================================
    # NORMALIZE CRITERIA
    # =========================================================================

    work["length_norm_ablation"] = minmax_normalize(
        work["route_length_m"]
    )

    work["cost_norm_ablation"] = minmax_normalize(
        work["mean_cost"]
    )

    work["new_length_norm_ablation"] = minmax_normalize(
        work["estimated_new_connection_length_m"]
    )

    work["coverage_norm_ablation"] = minmax_normalize(
        work["coverage_gap_percentage"]
    )


    # =========================================================================
    # FULL MODEL
    # =========================================================================

    work["score_full_model"] = (
        0.35 * work["length_norm_ablation"]
        +
        0.30 * work["cost_norm_ablation"]
        +
        0.20 * work["new_length_norm_ablation"]
        +
        0.15 * work["coverage_norm_ablation"]
    )


    # =========================================================================
    # WITHOUT COST
    # =========================================================================
    #
    # Remaining original weights:
    #
    # Length      35%
    # New length  20%
    # Coverage    15%
    #
    # Total = 70%
    #
    # Redistributed proportionally.
    # =========================================================================

    work["score_without_cost"] = (
        (0.35 / 0.70)
        * work["length_norm_ablation"]

        +

        (0.20 / 0.70)
        * work["new_length_norm_ablation"]

        +

        (0.15 / 0.70)
        * work["coverage_norm_ablation"]
    )


    # =========================================================================
    # WITHOUT NEW-ROAD LENGTH
    # =========================================================================
    #
    # Remaining original weights:
    #
    # Length      35%
    # Cost        30%
    # Coverage    15%
    #
    # Total = 80%
    #
    # Redistributed proportionally.
    # =========================================================================

    work["score_without_new_road_length"] = (
        (0.35 / 0.80)
        * work["length_norm_ablation"]

        +

        (0.30 / 0.80)
        * work["cost_norm_ablation"]

        +

        (0.15 / 0.80)
        * work["coverage_norm_ablation"]
    )


    # =========================================================================
    # LENGTH ONLY
    # =========================================================================

    work["score_length_only"] = (
        work["length_norm_ablation"]
    )


    # =========================================================================
    # ADD MODEL RESULTS
    # =========================================================================

    for model_name, score_column in [

        (
            "FULL_MODEL",
            "score_full_model"
        ),

        (
            "WITHOUT_COST",
            "score_without_cost"
        ),

        (
            "WITHOUT_NEW_ROAD_LENGTH",
            "score_without_new_road_length"
        ),

        (
            "LENGTH_ONLY",
            "score_length_only"
        )

    ]:

        model_data = work.copy()

        model_data["ablation_model"] = model_name

        model_data["ablation_score"] = (
            model_data[score_column]
        )


        # Rank candidates within each facility

        model_data["ablation_rank"] = (
            model_data["ablation_score"]
            .rank(
                method="min",
                ascending=True
            )
        )


        all_results.append(
            model_data[
                [
                    "facility_id",
                    "facility_name",
                    "facility_type",

                    "route_id",
                    "candidate_route",

                    "route_length_m",
                    "mean_cost",

                    "estimated_new_connection_length_m",

                    "coverage_gap_percentage",

                    "existing_road_overlap_percentage",

                    "route_status",

                    "ablation_model",
                    "ablation_score",
                    "ablation_rank"
                ]
            ]
        )


# =============================================================================
# CHECK RESULTS
# =============================================================================

if len(all_results) == 0:

    raise RuntimeError(
        "No evaluable candidates were available for the ablation study."
    )


# =============================================================================
# COMBINE
# =============================================================================

result = pd.concat(
    all_results,
    ignore_index=True
)


# =============================================================================
# MARK SELECTED CANDIDATE
# =============================================================================

result["selected"] = (
    result["ablation_rank"] == 1
)


# =============================================================================
# SAVE
# =============================================================================

result.to_csv(
    OUTPUT_FILE,
    index=False
)


# =============================================================================
# DISPLAY SELECTED ROUTES
# =============================================================================

print("\n" + "=" * 80)
print("ABLATION STUDY - SELECTED CANDIDATES")
print("=" * 80)


selected = result[
    result["selected"]
].copy()


for model_name in [

    "FULL_MODEL",
    "WITHOUT_COST",
    "WITHOUT_NEW_ROAD_LENGTH",
    "LENGTH_ONLY"

]:

    print(
        f"\n--- {model_name} ---"
    )

    model_selected = selected[
        selected["ablation_model"]
        == model_name
    ]


    for _, row in model_selected.iterrows():

        print(
            f"{row['facility_id']} | "
            f"{row['facility_name']} | "
            f"{row['route_id']} | "
            f"Score={row['ablation_score']:.4f} | "
            f"Length={row['route_length_m']:.2f} m | "
            f"Cost={row['mean_cost']:.3f}"
        )


# =============================================================================
# ROUTE SELECTION COMPARISON
# =============================================================================

print("\n" + "=" * 80)
print("ROUTE SELECTION COMPARISON")
print("=" * 80)


selection_table = selected[
    [
        "facility_id",
        "facility_name",
        "ablation_model",
        "route_id",
        "ablation_score"
    ]
].sort_values(
    [
        "facility_id",
        "ablation_model"
    ]
)


print(
    selection_table.to_string(
        index=False
    )
)


# =============================================================================
# MODEL SELECTION SUMMARY
# =============================================================================

print("\n" + "=" * 80)
print("MODEL SELECTION SUMMARY")
print("=" * 80)


for model_name in [

    "FULL_MODEL",
    "WITHOUT_COST",
    "WITHOUT_NEW_ROAD_LENGTH",
    "LENGTH_ONLY"

]:

    model_selected = selected[
        selected["ablation_model"]
        == model_name
    ]


    print(
        f"\n{model_name}: "
        f"{len(model_selected)} facility selections"
    )


    print(
        "Routes:",
        ", ".join(
            model_selected["route_id"].tolist()
        )
    )


# =============================================================================
# COUNT HOW MANY FACILITY SELECTIONS CHANGE
# =============================================================================

print("\n" + "=" * 80)
print("ROUTE-CHANGE SUMMARY")
print("=" * 80)


full_model_routes = (
    selected[
        selected["ablation_model"]
        == "FULL_MODEL"
    ]
    .set_index("facility_id")["route_id"]
)


for model_name in [

    "WITHOUT_COST",
    "WITHOUT_NEW_ROAD_LENGTH",
    "LENGTH_ONLY"

]:

    model_routes = (
        selected[
            selected["ablation_model"]
            == model_name
        ]
        .set_index("facility_id")["route_id"]
    )


    common_facilities = (
        full_model_routes.index
        .intersection(
            model_routes.index
        )
    )


    changed = sum(
        full_model_routes.loc[facility]
        !=
        model_routes.loc[facility]
        for facility in common_facilities
    )


    print(
        f"{model_name}: "
        f"{changed} of "
        f"{len(common_facilities)} "
        f"facility selections changed"
    )


# =============================================================================
# OUTPUT
# =============================================================================

print("\n" + "=" * 80)
print("PHASE 23 ABLATION STUDY COMPLETED")
print("=" * 80)

print("\nOutput saved to:")
print(OUTPUT_FILE)