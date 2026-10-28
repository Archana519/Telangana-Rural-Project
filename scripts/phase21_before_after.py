import os
import pandas as pd
import numpy as np


# =============================================================================
# PHASE 21 - BEFORE / AFTER CONNECTIVITY ANALYSIS
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
    "phase20_route_evaluation.csv"
)

OUTPUT_FILE = os.path.join(
    RESULTS_DIR,
    "phase21_before_after_connectivity.csv"
)


print("=" * 80)
print("PHASE 21 - BEFORE / AFTER CONNECTIVITY ANALYSIS")
print("=" * 80)


# =============================================================================
# LOAD PHASE 20 RESULTS
# =============================================================================

print("\nLoading Phase 20 route evaluation...")

df = pd.read_csv(INPUT_FILE)

print(
    "Total evaluated candidate records:",
    len(df)
)


# =============================================================================
# SELECT PLANNING CANDIDATES
# =============================================================================

selected = df[
    df["planning_status"] == "SELECTED_CANDIDATE_FOR_PLANNING"
].copy()

print(
    "Selected planning candidates:",
    len(selected)
)


# =============================================================================
# BEFORE CONNECTIVITY
# =============================================================================
#
# Before the proposed connection:
# facility-to-road distance is represented by the candidate route length.
#
# This is a planning comparison, not a measured network travel distance.
#


selected["before_connection_distance_m"] = (
    selected["route_length_m"]
)


# =============================================================================
# PROPOSED CONNECTION
# =============================================================================

selected["proposed_new_connection_m"] = (
    selected[
        "estimated_connection_length_m"
    ]
)


# =============================================================================
# AFTER CONNECTIVITY
# =============================================================================
#
# Once the proposed connection is constructed,
# the remaining facility-to-existing-road connection
# is treated as approximately zero for this planning model.
#
# This represents connection to the existing road network,
# NOT travel time through the entire road network.

selected["after_connection_distance_m"] = 0.0


# =============================================================================
# CONNECTIVITY IMPROVEMENT
# =============================================================================

selected["connectivity_distance_reduction_m"] = (
    selected["before_connection_distance_m"]
    -
    selected["after_connection_distance_m"]
)


# =============================================================================
# CONNECTIVITY GAIN PERCENTAGE
# =============================================================================

selected["connectivity_gain_percentage"] = np.where(
    selected["before_connection_distance_m"] > 0,

    (
        selected["connectivity_distance_reduction_m"]
        /
        selected["before_connection_distance_m"]
        *
        100.0
    ),

    0.0
)


# =============================================================================
# NEW ROAD REQUIREMENT
# =============================================================================

selected["new_road_required"] = np.where(
    selected["proposed_new_connection_m"] > 0,
    "YES",
    "NO"
)


# =============================================================================
# EXISTING ROAD OVERLAP
# =============================================================================

selected["existing_road_overlap_percentage"] = (
    selected[
        "existing_road_percentage"
    ]
)


# =============================================================================
# ACCESSIBILITY STATUS
# =============================================================================

selected["before_status"] = np.where(
    selected["before_connection_distance_m"] <= 25,
    "NEAR_EXISTING_ROAD",
    "CONNECTION_GAP"
)


selected["after_status"] = np.where(
    selected["after_connection_distance_m"] <= 1,
    "CONNECTED_TO_EXISTING_ROAD",
    "CONNECTION_GAP"
)


# =============================================================================
# CONNECTIVITY GAIN CLASS
# =============================================================================

def classify_gain(value):

    if value >= 75:
        return "HIGH_CONNECTIVITY_GAIN"

    elif value >= 50:
        return "MEDIUM_CONNECTIVITY_GAIN"

    else:
        return "DIRECT_CONNECTION_GAIN"


selected["connectivity_gain_class"] = (
    selected["connectivity_gain_percentage"]
    .apply(classify_gain)
)


# =============================================================================
# SELECT OUTPUT COLUMNS
# =============================================================================

output_columns = [
    "facility_id",
    "facility_name",
    "facility_type",

    "route_id",
    "candidate_route",

    "before_connection_distance_m",
    "proposed_new_connection_m",
    "after_connection_distance_m",

    "connectivity_distance_reduction_m",
    "connectivity_gain_percentage",

    "existing_road_overlap_percentage",

    "new_road_required",

    "before_status",
    "after_status",

    "connectivity_gain_class",

    "mean_cost",
    "multi_criteria_score"
]


result = selected[
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
print("PHASE 21 BEFORE / AFTER RESULTS")
print("=" * 80)

print(
    result.to_string(
        index=False
    )
)


# =============================================================================
# FACILITY SUMMARY
# =============================================================================

print("\n" + "=" * 80)
print("CONNECTIVITY IMPROVEMENT SUMMARY")
print("=" * 80)


for _, row in result.iterrows():

    print(
        f"\nFacility: {row['facility_id']}"
    )

    print(
        f"Name: {row['facility_name']}"
    )

    print(
        f"Before connection distance: "
        f"{row['before_connection_distance_m']:.2f} m"
    )

    print(
        f"Proposed new connection: "
        f"{row['proposed_new_connection_m']:.2f} m"
    )

    print(
        f"After connection distance: "
        f"{row['after_connection_distance_m']:.2f} m"
    )

    print(
        f"Connectivity distance reduction: "
        f"{row['connectivity_distance_reduction_m']:.2f} m"
    )

    print(
        f"Connectivity gain: "
        f"{row['connectivity_gain_percentage']:.2f}%"
    )

    print(
        f"New road required: "
        f"{row['new_road_required']}"
    )


# =============================================================================
# OVERALL SUMMARY
# =============================================================================

print("\n" + "=" * 80)
print("OVERALL SUMMARY")
print("=" * 80)

print(
    "\nFacilities evaluated:",
    len(result)
)

print(
    "Total proposed new-road connection:",
    f"{result['proposed_new_connection_m'].sum():.2f} m"
)

print(
    "Total connectivity distance reduction:",
    f"{result['connectivity_distance_reduction_m'].sum():.2f} m"
)

print(
    "Average connectivity gain:",
    f"{result['connectivity_gain_percentage'].mean():.2f}%"
)


# =============================================================================
# OUTPUT
# =============================================================================

print("\nOutput saved to:")
print(OUTPUT_FILE)

print("\n" + "=" * 80)
print("PHASE 21 BEFORE / AFTER ANALYSIS COMPLETED")
print("=" * 80)