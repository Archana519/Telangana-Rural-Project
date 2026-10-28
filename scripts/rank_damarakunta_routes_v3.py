
from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================
# DAMARAKUNTA V3 - MULTI-CRITERIA ROUTE RANKING
#
# Reads existing V3 route comparison and feasibility outputs.
# Writes new ranking CSV files only.
#
# Lower score = better preliminary candidate.
# A top-ranked candidate is NOT construction approval.
# ============================================================

ROOT = Path(r"D:\Telangana_Rural_Project")
RESULTS = ROOT / "Siddipet" / "Damarakunta" / "results"

COMPARISON_CSV = RESULTS / "damarakunta_routes_v3_comparison.csv"
FEASIBILITY_CSV = RESULTS / "damarakunta_route_feasibility_screening_v3.csv"

OUTPUT_CSV = RESULTS / "damarakunta_routes_v3_multi_criteria_ranking.csv"
SUMMARY_CSV = RESULTS / "damarakunta_routes_v3_preferred_candidates.csv"

# Initial provisional weights. These require justification and sensitivity
# analysis before being presented as validated research weights.
WEIGHTS = {
    "route_length": 0.25,
    "accumulated_cost": 0.25,
    "road_connection": 0.15,
    "parcel_impact": 0.15,
    "compound_impact": 0.10,
    "slope": 0.10,
}

JOIN_KEYS = ["facility_id", "facility_name", "alternative"]

ROUTE_COLUMNS = [
    "facility_id",
    "facility_name",
    "facility_type",
    "alternative",
    "status",
    "route_length_m",
    "accumulated_cost",
    "end_cell_to_road_m",
    "max_sampled_slope_deg",
    "facility_location_verification",
]

FEASIBILITY_COLUMNS = [
    "facility_id",
    "facility_name",
    "alternative",
    "intersected_parcel_count",
    "school_compound_intersections",
    "ownership_clearance",
    "drainage_clearance",
    "building_clearance",
    "construction_feasibility",
    "overall_status",
]


def require_file(path):
    if not path.exists():
        raise FileNotFoundError(
            f"Required input file not found:\n{path}"
        )


def check_columns(df, required, filename):
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError(
            f"Missing columns in {filename}:\n{missing}"
        )


def normalize_penalty(series):
    """
    Normalize a metric to [0, 1].
    0 means the lowest observed penalty and 1 the highest.
    Missing values remain missing.
    """
    values = pd.to_numeric(series, errors="coerce")
    valid = values.dropna()

    result = pd.Series(np.nan, index=series.index, dtype=float)

    if valid.empty:
        return result

    low = valid.min()
    high = valid.max()

    if np.isclose(low, high):
        result.loc[valid.index] = 0.0
    else:
        result.loc[valid.index] = (
            (valid - low) / (high - low)
        )

    return result


def main():
    require_file(COMPARISON_CSV)
    require_file(FEASIBILITY_CSV)

    routes = pd.read_csv(COMPARISON_CSV)
    feasibility = pd.read_csv(FEASIBILITY_CSV)

    check_columns(routes, ROUTE_COLUMNS, COMPARISON_CSV.name)
    check_columns(feasibility, FEASIBILITY_COLUMNS, FEASIBILITY_CSV.name)

    # Make join-key types consistent and remove accidental whitespace.
    for column in ["facility_id", "facility_name"]:
        routes[column] = routes[column].astype("string").str.strip()
        feasibility[column] = (
            feasibility[column].astype("string").str.strip()
        )

    routes["alternative"] = pd.to_numeric(
        routes["alternative"], errors="coerce"
    )
    feasibility["alternative"] = pd.to_numeric(
        feasibility["alternative"], errors="coerce"
    )

    # The feasibility output should have exactly one record per candidate.
    duplicate_keys = feasibility.duplicated(JOIN_KEYS, keep=False)
    if duplicate_keys.any():
        duplicates = feasibility.loc[duplicate_keys, JOIN_KEYS]
        raise ValueError(
            "Duplicate facility/alternative keys in feasibility CSV:\n"
            + duplicates.to_string(index=False)
        )

    # Join the existing outputs; do not alter either source file.
    merged = routes.merge(
        feasibility[FEASIBILITY_COLUMNS],
        on=JOIN_KEYS,
        how="left",
        validate="one_to_one",
        indicator=True,
    )

    merged["feasibility_record_found"] = merged["_merge"].eq("both")
    merged.drop(columns=["_merge"], inplace=True)

    numeric_columns = [
        "route_length_m",
        "accumulated_cost",
        "end_cell_to_road_m",
        "max_sampled_slope_deg",
        "intersected_parcel_count",
        "school_compound_intersections",
    ]

    for column in numeric_columns:
        merged[column] = pd.to_numeric(
            merged[column], errors="coerce"
        )

    # Only successfully generated routes with required metrics are rankable.
    merged["candidate_generated"] = (
        merged["status"].eq("CANDIDATE_REQUIRES_VISUAL_REVIEW")
        & merged["route_length_m"].notna()
        & merged["accumulated_cost"].notna()
        & merged["feasibility_record_found"]
    )

    merged["preliminary_score"] = np.nan
    merged["rank_within_facility"] = pd.Series(
        pd.NA, index=merged.index, dtype="Int64"
    )

    criteria = {
        "route_length": "route_length_m",
        "accumulated_cost": "accumulated_cost",
        "road_connection": "end_cell_to_road_m",
        "parcel_impact": "intersected_parcel_count",
        "compound_impact": "school_compound_intersections",
        "slope": "max_sampled_slope_deg",
    }

    # Rank candidates independently within each facility.
    for _, group in merged.groupby("facility_id", dropna=False):
        valid = group.loc[group["candidate_generated"]].copy()

        if valid.empty:
            continue

        normalized_metrics = {}
        active_weights = {}

        for criterion, column in criteria.items():
            normalized = normalize_penalty(valid[column])

            if normalized.notna().any():
                normalized_metrics[criterion] = normalized
                active_weights[criterion] = WEIGHTS[criterion]

        total_weight = sum(active_weights.values())

        if total_weight <= 0:
            continue

        # Renormalize only across criteria with available values.
        scores = pd.Series(0.0, index=valid.index, dtype=float)

        for criterion, normalized in normalized_metrics.items():
            weight = active_weights[criterion] / total_weight
            scores += normalized.fillna(0.0) * weight * 100.0

        merged.loc[valid.index, "preliminary_score"] = scores

        # Stable sorting gives deterministic ranks for tied scores.
        ordered_indices = scores.sort_values(
            ascending=True, kind="stable"
        ).index

        for rank, index in enumerate(ordered_indices, start=1):
            merged.loc[index, "rank_within_facility"] = rank

    # Correctly handle missing ranks without evaluating pd.NA as a Boolean.
    merged["ranking_interpretation"] = "NOT_RANKABLE_NO_VALID_ROUTE"

    generated_mask = merged["candidate_generated"].fillna(False)
    ranked_mask = merged["rank_within_facility"].notna()

    merged.loc[
        generated_mask & ranked_mask,
        "ranking_interpretation",
    ] = "LOWER_PRELIMINARY_RANK_REQUIRES_REVIEW"

    top_mask = (
        generated_mask
        & merged["rank_within_facility"].eq(1).fillna(False)
    )

    merged.loc[
        top_mask,
        "ranking_interpretation",
    ] = "TOP_PRELIMINARY_CANDIDATE_REQUIRES_REVIEW"

    # Preserve unknown clearance values; do not assume they are approved.
    merged["decision_limitations"] = (
        "Preliminary ranking only. Facility entrance, ownership, drainage, "
        "building clearance, coordinate accuracy and accessibility gain "
        "are not fully verified. Cost is not monetary cost."
    )

    merged["facility_location_warning"] = (
        merged["facility_location_verification"].fillna("UNKNOWN")
    )

    # Add the weights used so results remain interpretable.
    merged["weight_route_length"] = WEIGHTS["route_length"]
    merged["weight_accumulated_cost"] = WEIGHTS["accumulated_cost"]
    merged["weight_road_connection"] = WEIGHTS["road_connection"]
    merged["weight_parcel_impact"] = WEIGHTS["parcel_impact"]
    merged["weight_compound_impact"] = WEIGHTS["compound_impact"]
    merged["weight_slope"] = WEIGHTS["slope"]

    merged = merged.sort_values(
        ["facility_name", "candidate_generated", "rank_within_facility"],
        ascending=[True, False, True],
        na_position="last",
        kind="stable",
    )

    RESULTS.mkdir(parents=True, exist_ok=True)
    merged.to_csv(OUTPUT_CSV, index=False)

    # One top preliminary candidate per facility when a route is rankable.
    preferred = merged.loc[
        merged["candidate_generated"]
        & merged["rank_within_facility"].eq(1).fillna(False)
    ].copy()

    preferred.to_csv(SUMMARY_CSV, index=False)

    display_columns = [
        "facility_name",
        "alternative",
        "route_length_m",
        "accumulated_cost",
        "end_cell_to_road_m",
        "intersected_parcel_count",
        "school_compound_intersections",
        "max_sampled_slope_deg",
        "preliminary_score",
        "rank_within_facility",
        "ranking_interpretation",
    ]

    print("\nDAMARAKUNTA V3 MULTI-CRITERIA RANKING COMPLETE")
    print(f"Candidate records read: {len(merged)}")
    print(
        "Generated routes rankable: "
        f"{int(merged['candidate_generated'].sum())}"
    )
    print(f"Facilities with ranked candidates: {len(preferred)}")
    print(f"\nProvisional weights: {WEIGHTS}")

    print("\nPreliminary top candidate per facility:")
    if preferred.empty:
        print("No candidates could be ranked. Check the input CSVs.")
    else:
        print(preferred[display_columns].to_string(index=False))

    print(f"\nFull ranking saved to:\n{OUTPUT_CSV}")
    print(f"\nTop-candidate summary saved to:\n{SUMMARY_CSV}")

    print(
        "\nIMPORTANT: Scores are relative to candidates for each facility. "
        "They are not probabilities, rupee costs, or proof of global "
        "optimality. Validate constraints and test alternative weights "
        "before making final route-selection claims."
    )


if __name__ == "__main__":
    main()
