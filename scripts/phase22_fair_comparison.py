import os
import pandas as pd
import numpy as np


# =============================================================================
# PHASE 22 - FAIR BASELINE COMPARISON
# =============================================================================

PROJECT_ROOT = r"D:\Telangana_Rural_Project"

RESULTS_DIR = os.path.join(
    PROJECT_ROOT,
    "Siddipet",
    "Angadi_Kistapur",
    "results"
)

# Phase 18: actual facility-to-nearest existing TGRAC road
BASELINE_FILE = os.path.join(
    RESULTS_DIR,
    "phase18_facility_road_connections.csv"
)

# Phase 20: selected planning candidate routes
SELECTED_FILE = os.path.join(
    RESULTS_DIR,
    "phase20_route_evaluation.csv"
)

OUTPUT_FILE = os.path.join(
    RESULTS_DIR,
    "phase22_fair_comparison.csv"
)


print("=" * 80)
print("PHASE 22 - FAIR BASELINE COMPARISON")
print("=" * 80)


# =============================================================================
# LOAD PHASE 18 BASELINE
# =============================================================================

print("\nLoading Phase 18 existing-road baseline...")

baseline = pd.read_csv(BASELINE_FILE)

print(
    "Baseline facilities:",
    len(baseline)
)


# =============================================================================
# LOAD PHASE 20 SELECTED CANDIDATES
# =============================================================================

print("\nLoading Phase 20 selected planning candidates...")

selected = pd.read_csv(SELECTED_FILE)

# Keep only selected planning candidates if the column exists
if "planning_status" in selected.columns:
    selected = selected[
        selected["planning_status"]
        == "SELECTED_CANDIDATE_FOR_PLANNING"
    ].copy()

print(
    "Selected candidates:",
    len(selected)
)


# =============================================================================
# CHECK REQUIRED COLUMNS
# =============================================================================

required_baseline = [
    "facility_id",
    "facility_name",
    "facility_type",
    "facility_to_road_distance_m"
]

required_selected = [
    "facility_id",
    "candidate_route",
    "route_length_m",
    "estimated_new_connection_length_m",
    "existing_road_overlap_percentage"
]

for col in required_baseline:
    if col not in baseline.columns:
        raise ValueError(
            f"Missing column in Phase 18 file: {col}"
        )

for col in required_selected:
    if col not in selected.columns:
        raise ValueError(
            f"Missing column in Phase 20 file: {col}"
        )


# =============================================================================
# CREATE ROUTE ID
# =============================================================================

selected["route_id"] = (
    selected["facility_id"].astype(str)
    + "_C"
    + selected["candidate_route"].astype(str)
)


# =============================================================================
# FAIR MERGE
# =============================================================================

result = pd.merge(
    baseline[
        [
            "facility_id",
            "facility_name",
            "facility_type",
            "facility_to_road_distance_m"
        ]
    ],
    selected[
        [
            "facility_id",
            "route_id",
            "candidate_route",
            "route_length_m",
            "estimated_new_connection_length_m",
            "existing_road_overlap_percentage",
            "mean_cost",
            "combined_score"
        ]
    ],
    on="facility_id",
    how="inner"
)


# =============================================================================
# IMPORTANT:
# Only the selected candidate for each facility should remain.
# =============================================================================

result = result.drop_duplicates(
    subset=["facility_id"]
).copy()


# =============================================================================
# RENAME FOR CLARITY
# =============================================================================

result.rename(
    columns={
        "facility_to_road_distance_m":
            "existing_nearest_road_distance_m",

        "estimated_new_connection_length_m":
            "proposed_new_connection_length_m",

        "combined_score":
            "multi_criteria_score"
    },
    inplace=True
)


# =============================================================================
# BASELINE GAP STATUS
# =============================================================================

result["baseline_status"] = np.where(
    result["existing_nearest_road_distance_m"] <= 25,
    "ALREADY_NEAR_EXISTING_ROAD",
    "CONNECTION_GAP"
)


# =============================================================================
# PROPOSED CONNECTION STATUS
# =============================================================================

result["proposed_status"] = np.where(
    result["proposed_new_connection_length_m"] > 0,
    "PROPOSED_NEW_CONNECTION",
    "NO_NEW_CONNECTION"
)


# =============================================================================
# DESCRIPTIVE LENGTH COMPARISON
# =============================================================================
#
# This is NOT called "accessibility improvement".
#
# It simply compares:
#
# Existing:
#     facility -> nearest existing TGRAC road
#
# Proposed:
#     facility -> selected candidate road connection
#
# A positive value means the proposed connection is longer.
# A negative value means the proposed connection is shorter.
#

result["proposed_minus_existing_m"] = (
    result["proposed_new_connection_length_m"]
    -
    result["existing_nearest_road_distance_m"]
)


result["proposed_vs_existing_change_percentage"] = np.where(
    result["existing_nearest_road_distance_m"] > 0,

    (
        result["proposed_minus_existing_m"]
        /
        result["existing_nearest_road_distance_m"]
        *
        100.0
    ),

    np.nan
)


# =============================================================================
# DESCRIPTIVE COMPARISON CATEGORY
# =============================================================================

def classify_comparison(row):

    difference = row["proposed_minus_existing_m"]

    if abs(difference) < 5:
        return "SIMILAR_CONNECTION_LENGTH"

    elif difference > 0:
        return "PROPOSED_CONNECTION_LONGER"

    else:
        return "PROPOSED_CONNECTION_SHORTER"


result["connection_length_comparison"] = result.apply(
    classify_comparison,
    axis=1
)


# =============================================================================
# CONNECTION NEED
# =============================================================================

result["connection_need"] = np.where(
    result["existing_nearest_road_distance_m"] > 25,
    "CONNECTION_GAP",
    "NEAR_EXISTING_ROAD"
)


# =============================================================================
# SELECT FINAL OUTPUT COLUMNS
# =============================================================================

output_columns = [
    "facility_id",
    "facility_name",
    "facility_type",

    "route_id",
    "candidate_route",

    "existing_nearest_road_distance_m",
    "proposed_new_connection_length_m",

    "proposed_minus_existing_m",
    "proposed_vs_existing_change_percentage",

    "existing_road_overlap_percentage",

    "baseline_status",
    "proposed_status",
    "connection_need",
    "connection_length_comparison",

    "route_length_m",
    "mean_cost",
    "multi_criteria_score"
]


result = result[
    output_columns
].copy()


# =============================================================================
# SAVE
# =============================================================================

result.to_csv(
    OUTPUT_FILE,
    index=False
)


# =============================================================================
# DISPLAY RESULTS
# =============================================================================

print("\n" + "=" * 80)
print("FAIR BASELINE COMPARISON RESULTS")
print("=" * 80)

print(
    result.to_string(
        index=False
    )
)


# =============================================================================
# FACILITY-LEVEL SUMMARY
# =============================================================================

print("\n" + "=" * 80)
print("FACILITY-LEVEL COMPARISON")
print("=" * 80)


for _, row in result.iterrows():

    print(
        f"\nFacility: {row['facility_id']}"
    )

    print(
        f"Name: {row['facility_name']}"
    )

    print(
        f"Existing nearest-road distance: "
        f"{row['existing_nearest_road_distance_m']:.2f} m"
    )

    print(
        f"Proposed new-road connection: "
        f"{row['proposed_new_connection_length_m']:.2f} m"
    )

    print(
        f"Difference: "
        f"{row['proposed_minus_existing_m']:.2f} m"
    )

    print(
        f"Percentage difference: "
        f"{row['proposed_vs_existing_change_percentage']:.2f}%"
    )

    print(
        f"Existing-road overlap: "
        f"{row['existing_road_overlap_percentage']:.2f}%"
    )

    print(
        f"Comparison: "
        f"{row['connection_length_comparison']}"
    )


# =============================================================================
# OVERALL SUMMARY
# =============================================================================

print("\n" + "=" * 80)
print("OVERALL SUMMARY")
print("=" * 80)

print(
    "\nFacilities compared:",
    len(result)
)

print(
    "Total existing nearest-road distance:",
    f"{result['existing_nearest_road_distance_m'].sum():.2f} m"
)

print(
    "Total proposed new-road connection:",
    f"{result['proposed_new_connection_length_m'].sum():.2f} m"
)

print(
    "Total proposed-minus-existing difference:",
    f"{result['proposed_minus_existing_m'].sum():.2f} m"
)

print(
    "Average percentage difference:",
    f"{result['proposed_vs_existing_change_percentage'].mean():.2f}%"
)


# =============================================================================
# OUTPUT
# =============================================================================

print("\nOutput saved to:")
print(OUTPUT_FILE)

print("\n" + "=" * 80)
print("PHASE 22 FAIR COMPARISON COMPLETED")
print("=" * 80)