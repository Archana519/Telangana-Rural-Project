import os
import pandas as pd
import numpy as np

# ============================================================
# PHASE 24 - SENSITIVITY ANALYSIS
# ============================================================

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
    "phase24_sensitivity_analysis.csv"
)

print("=" * 80)
print("PHASE 24 - SENSITIVITY ANALYSIS")
print("=" * 80)

# ============================================================
# 1. LOAD PHASE 19 DATA
# ============================================================

print("\nLoading Phase 19 multi-criteria results...")

mc = pd.read_csv(MULTI_CRITERIA_FILE)

print(f"Multi-criteria candidates: {len(mc)}")

print("\nLoading Phase 19 existing-road comparison...")

road = pd.read_csv(ROAD_COMPARISON_FILE)

print(f"Road-comparison candidates: {len(road)}")


# ============================================================
# 2. CREATE ROUTE ID
# ============================================================

mc["route_id"] = (
    mc["facility_id"].astype(str)
    + "_"
    + mc["candidate_route"].astype(str)
)

road["route_id"] = (
    road["facility_id"].astype(str)
    + "_"
    + road["candidate_route"].astype(str)
)


# ============================================================
# 3. MERGE REQUIRED DATA
# ============================================================

road_required = road[
    [
        "route_id",
        "estimated_new_connection_length_m",
        "existing_road_overlap_percentage",
        "route_class"
    ]
].copy()

df = pd.merge(
    mc,
    road_required,
    on="route_id",
    how="left"
)

# Handle possible pandas suffixes
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
        raise KeyError(
            "estimated_new_connection_length_m column was not found."
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


print(f"\nMerged candidates: {len(df)}")

print(
    "Estimated new-road length column available:",
    "estimated_new_connection_length_m" in df.columns
)


# ============================================================
# 4. IDENTIFY EVALUABLE CANDIDATES
# ============================================================

df["evaluable"] = (
    (df["route_status"] == "EVALUABLE")
    & (df["water_samples"] == 0)
    & (df["mean_cost"].notna())
    & (df["estimated_new_connection_length_m"].notna())
)

eval_df = df[df["evaluable"]].copy()

print(f"Evaluable candidates: {len(eval_df)}")


# ============================================================
# 5. NORMALIZATION
# ============================================================
#
# Lower value = better
#
# Normalization is performed separately for each facility.
#
# normalized value:
# (value - minimum) / (maximum - minimum)
#
# If all values are identical, normalized value = 0.
# ============================================================

def normalize_within_facility(group, column):

    values = group[column].astype(float)

    minimum = values.min()
    maximum = values.max()

    if maximum == minimum:
        return pd.Series(
            np.zeros(len(group)),
            index=group.index
        )

    return (values - minimum) / (maximum - minimum)


eval_df["length_norm"] = (
    eval_df
    .groupby("facility_id", group_keys=False)
    .apply(
        lambda g: normalize_within_facility(
            g,
            "route_length_m"
        ),
        include_groups=False
    )
)

eval_df["cost_norm"] = (
    eval_df
    .groupby("facility_id", group_keys=False)
    .apply(
        lambda g: normalize_within_facility(
            g,
            "mean_cost"
        ),
        include_groups=False
    )
)

eval_df["new_road_norm"] = (
    eval_df
    .groupby("facility_id", group_keys=False)
    .apply(
        lambda g: normalize_within_facility(
            g,
            "estimated_new_connection_length_m"
        ),
        include_groups=False
    )
)

eval_df["coverage_norm"] = (
    eval_df
    .groupby("facility_id", group_keys=False)
    .apply(
        lambda g: normalize_within_facility(
            g,
            "coverage_gap_percentage"
        ),
        include_groups=False
    )
)


# ============================================================
# 6. DEFINE SENSITIVITY SCENARIOS
# ============================================================

scenarios = {

    # Original Phase 19 weights
    "BASELINE": {
        "length": 0.35,
        "cost": 0.30,
        "new_road": 0.20,
        "coverage": 0.15
    },

    # More importance to route length
    "LENGTH_FOCUSED": {
        "length": 0.50,
        "cost": 0.20,
        "new_road": 0.20,
        "coverage": 0.10
    },

    # More importance to land-cover/slope cost
    "COST_FOCUSED": {
        "length": 0.20,
        "cost": 0.50,
        "new_road": 0.20,
        "coverage": 0.10
    },

    # More importance to actual new-road construction length
    "NEW_ROAD_FOCUSED": {
        "length": 0.20,
        "cost": 0.20,
        "new_road": 0.50,
        "coverage": 0.10
    },

    # Equal importance to all four criteria
    "BALANCED": {
        "length": 0.25,
        "cost": 0.25,
        "new_road": 0.25,
        "coverage": 0.25
    }
}


# ============================================================
# 7. RUN SENSITIVITY ANALYSIS
# ============================================================

all_results = []

print("\n")
print("=" * 80)
print("SENSITIVITY ANALYSIS - SELECTED CANDIDATES")
print("=" * 80)

for scenario_name, weights in scenarios.items():

    temp = eval_df.copy()

    temp["sensitivity_score"] = (
        weights["length"] * temp["length_norm"]
        + weights["cost"] * temp["cost_norm"]
        + weights["new_road"] * temp["new_road_norm"]
        + weights["coverage"] * temp["coverage_norm"]
    )

    temp["sensitivity_rank"] = (
        temp
        .groupby("facility_id")["sensitivity_score"]
        .rank(
            method="min",
            ascending=True
        )
    )

    selected = temp[
        temp["sensitivity_rank"] == 1
    ].copy()

    selected["scenario"] = scenario_name

    all_results.append(
        selected[
            [
                "scenario",
                "facility_id",
                "facility_name",
                "facility_type",
                "priority_group",
                "candidate_route",
                "route_length_m",
                "mean_cost",
                "estimated_new_connection_length_m",
                "coverage_gap_percentage",
                "existing_road_overlap_percentage",
                "sensitivity_score",
                "sensitivity_rank"
            ]
        ]
    )

    print(f"\n--- {scenario_name} ---")

    print(
        f"Weights: "
        f"Length={weights['length']:.0%}, "
        f"Cost={weights['cost']:.0%}, "
        f"New-road={weights['new_road']:.0%}, "
        f"Coverage={weights['coverage']:.0%}"
    )

    for _, row in selected.sort_values("facility_id").iterrows():

        print(
            f"{row['facility_id']} | "
            f"{row['facility_name']} | "
            f"{row['candidate_route']} | "
            f"Score={row['sensitivity_score']:.4f} | "
            f"Length={row['route_length_m']:.2f} m | "
            f"Cost={row['mean_cost']:.3f}"
        )


# ============================================================
# 8. COMBINE RESULTS
# ============================================================

result_df = pd.concat(
    all_results,
    ignore_index=True
)


# ============================================================
# 9. SAVE RESULTS
# ============================================================

result_df.to_csv(
    OUTPUT_FILE,
    index=False
)


# ============================================================
# 10. ROUTE SELECTION COMPARISON
# ============================================================

print("\n")
print("=" * 80)
print("ROUTE SELECTION COMPARISON")
print("=" * 80)

comparison = result_df[
    [
        "facility_id",
        "facility_name",
        "scenario",
        "candidate_route",
        "sensitivity_score"
    ]
].sort_values(
    ["facility_id", "scenario"]
)

print(
    comparison.to_string(index=False)
)


# ============================================================
# 11. COMPARE AGAINST BASELINE
# ============================================================

baseline = (
    result_df[
        result_df["scenario"] == "BASELINE"
    ][
        [
            "facility_id",
            "candidate_route"
        ]
    ]
    .rename(
        columns={
            "candidate_route": "baseline_route"
        }
    )
)

print("\n")
print("=" * 80)
print("SENSITIVITY / ROUTE-CHANGE SUMMARY")
print("=" * 80)

for scenario_name in scenarios:

    if scenario_name == "BASELINE":
        continue

    scenario_routes = (
        result_df[
            result_df["scenario"] == scenario_name
        ][
            [
                "facility_id",
                "candidate_route"
            ]
        ]
        .rename(
            columns={
                "candidate_route": "scenario_route"
            }
        )
    )

    comparison_change = pd.merge(
        baseline,
        scenario_routes,
        on="facility_id",
        how="outer"
    )

    changed = (
        comparison_change["baseline_route"]
        != comparison_change["scenario_route"]
    ).sum()

    total = len(comparison_change)

    print(
        f"{scenario_name}: "
        f"{changed} of {total} facility selections changed"
    )


# ============================================================
# 12. MODEL SUMMARY
# ============================================================

print("\n")
print("=" * 80)
print("MODEL SUMMARY")
print("=" * 80)

for scenario_name in scenarios:

    scenario_rows = result_df[
        result_df["scenario"] == scenario_name
    ]

    routes = ", ".join(
        scenario_rows
        .sort_values("facility_id")["candidate_route"]
        .astype(str)
        .tolist()
    )

    print(
        f"{scenario_name}: "
        f"{len(scenario_rows)} facility selections"
    )

    print(
        f"Routes: {routes}"
    )


# ============================================================
# 13. FINAL STATUS
# ============================================================

print("\n")
print("=" * 80)
print("PHASE 24 SENSITIVITY ANALYSIS COMPLETED")
print("=" * 80)

print("\nOutput saved to:")
print(OUTPUT_FILE)