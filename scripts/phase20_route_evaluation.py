import os
import pandas as pd
import numpy as np


# =============================================================================
# PHASE 20 - ROUTE EVALUATION
# =============================================================================

PROJECT_ROOT = r"D:\Telangana_Rural_Project"

RESULTS_DIR = os.path.join(
    PROJECT_ROOT,
    "Siddipet",
    "Angadi_Kistapur",
    "results"
)

INPUT_FILE = os.path.join(
    RESULTS_DIR,
    "phase19_multi_criteria_evaluation.csv"
)

OUTPUT_FILE = os.path.join(
    RESULTS_DIR,
    "phase20_route_evaluation.csv"
)


print("=" * 80)
print("PHASE 20 - ROUTE EVALUATION")
print("=" * 80)


# =============================================================================
# LOAD PHASE 19 RESULTS
# =============================================================================

print("\nLoading Phase 19 results...")

df = pd.read_csv(INPUT_FILE)

print("Total candidate routes:", len(df))


# =============================================================================
# SELECT ONLY EVALUATED ROUTES
# =============================================================================

evaluated = df[
    df["evaluation_status"] == "EVALUATED"
].copy()

print(
    "Evaluated candidate routes:",
    len(evaluated)
)


# =============================================================================
# IDENTIFY LOWEST-SCORE ROUTE WITHIN EACH FACILITY
# =============================================================================

evaluated["selected_for_planning"] = False


for facility_id, group in evaluated.groupby(
    "facility_id"
):

    idx = group[
        "multi_criteria_score"
    ].idxmin()

    evaluated.loc[
        idx,
        "selected_for_planning"
    ] = True


# =============================================================================
# ROUTE CLASSIFICATION
# =============================================================================

def route_decision(row):

    if row["selected_for_planning"]:
        return "SELECTED_CANDIDATE_FOR_PLANNING"

    return "ALTERNATIVE_CANDIDATE"


evaluated["planning_status"] = evaluated.apply(
    route_decision,
    axis=1
)


# =============================================================================
# CALCULATE PLANNING METRICS
# =============================================================================

evaluated["estimated_connection_length_m"] = (
    evaluated[
        "estimated_new_connection_length_m"
    ]
)


evaluated["existing_road_percentage"] = (
    evaluated[
        "existing_road_overlap_percentage"
    ]
)


# =============================================================================
# SORT
# =============================================================================

evaluated = evaluated.sort_values(
    [
        "facility_id",
        "selected_for_planning",
        "multi_criteria_score"
    ],
    ascending=[
        True,
        False,
        True
    ]
)


# =============================================================================
# SAVE
# =============================================================================

evaluated.to_csv(
    OUTPUT_FILE,
    index=False
)


# =============================================================================
# DISPLAY
# =============================================================================

print("\n" + "=" * 80)
print("PHASE 20 ROUTE EVALUATION RESULTS")
print("=" * 80)


display_columns = [
    "route_id",
    "facility_id",
    "facility_name",
    "candidate_route",
    "route_length_m",
    "mean_cost",
    "estimated_connection_length_m",
    "existing_road_percentage",
    "coverage_uncertainty",
    "multi_criteria_score",
    "candidate_rank",
    "planning_status"
]


print(
    evaluated[
        display_columns
    ].to_string(index=False)
)


# =============================================================================
# SELECTED CANDIDATES SUMMARY
# =============================================================================

print("\n" + "=" * 80)
print("SELECTED CANDIDATE ROUTES FOR PLANNING")
print("=" * 80)


selected = evaluated[
    evaluated["selected_for_planning"] == True
]


for _, row in selected.iterrows():

    print(
        f"\nFacility: {row['facility_id']}"
    )

    print(
        f"Name: {row['facility_name']}"
    )

    print(
        f"Candidate: {row['route_id']}"
    )

    print(
        f"Route length: "
        f"{row['route_length_m']:.2f} m"
    )

    print(
        f"Estimated new connection: "
        f"{row['estimated_connection_length_m']:.2f} m"
    )

    print(
        f"Mean cost: "
        f"{row['mean_cost']:.3f}"
    )

    print(
        f"Existing-road overlap: "
        f"{row['existing_road_percentage']:.2f}%"
    )

    print(
        f"Multi-criteria score: "
        f"{row['multi_criteria_score']:.4f}"
    )


# =============================================================================
# SUMMARY
# =============================================================================

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)

print(
    "\nEvaluated routes:",
    len(evaluated)
)

print(
    "Selected planning candidates:",
    len(selected)
)

print(
    "Facilities covered:",
    selected["facility_id"].nunique()
)


# =============================================================================
# OUTPUT
# =============================================================================

print("\nOutput saved to:")
print(OUTPUT_FILE)

print("\n" + "=" * 80)
print("PHASE 20 ROUTE EVALUATION COMPLETED")
print("=" * 80)