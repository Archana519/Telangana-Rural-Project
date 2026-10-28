import geopandas as gpd
import pandas as pd
from pathlib import Path


BASE = Path(
    r"D:\Telangana_Rural_Project\Siddipet\Angadi_Kistapur"
)

CANDIDATE_PATH = (
    BASE / "results" /
    "phase18_new_road_candidates.gpkg"
)

ROAD_PATH = (
    BASE / "reference" /
    "tgrac_road_network_angadi_kistapur.gpkg"
)

OUTPUT_PATH = (
    BASE / "results" /
    "phase19_candidate_existing_road_comparison.csv"
)


print("=" * 80)
print("COMPARING CANDIDATE ROUTES WITH EXISTING TGRAC ROADS")
print("=" * 80)


# ------------------------------------------------------------
# Load data
# ------------------------------------------------------------

print()
print("Loading candidate routes...")

candidates = gpd.read_file(
    CANDIDATE_PATH,
    layer="candidate_routes"
)

print("Loading TGRAC roads...")

roads = gpd.read_file(
    ROAD_PATH
)


# ------------------------------------------------------------
# Ensure same CRS
# ------------------------------------------------------------

if candidates.crs != roads.crs:

    roads = roads.to_crs(
        candidates.crs
    )


print()
print("Candidate CRS:", candidates.crs)
print("Road CRS:", roads.crs)


# ------------------------------------------------------------
# Create buffered existing-road network
#
# A candidate is considered spatially overlapping an
# existing road if it intersects a 3-metre buffer around
# the TGRAC road.
#
# This avoids the earlier exact-geometry comparison problem.
# ------------------------------------------------------------

print()
print("Creating 3-metre existing-road buffer...")

road_buffer = roads.geometry.buffer(
    3.0
)

road_union = road_buffer.union_all()


# ------------------------------------------------------------
# Compare each candidate
# ------------------------------------------------------------

results = []


for _, row in candidates.iterrows():

    geometry = row.geometry

    route_length = geometry.length

    overlap_geometry = geometry.intersection(
        road_union
    )

    overlap_length = (
        overlap_geometry.length
    )

    if route_length > 0:

        overlap_percentage = (
            overlap_length /
            route_length
        ) * 100

    else:

        overlap_percentage = 0.0


    new_connection_length = max(
        0.0,
        route_length -
        overlap_length
    )


    # --------------------------------------------------------
    # Classification
    # --------------------------------------------------------

    if overlap_percentage >= 80:

        route_class = (
            "MOSTLY_EXISTING_ROAD"
        )

    elif overlap_percentage >= 20:

        route_class = (
            "PARTIAL_EXISTING_OVERLAP"
        )

    else:

        route_class = (
            "PREDOMINANTLY_NEW_CONNECTION"
        )


    results.append({

        "route_id":
            row["route_id"],

        "facility_id":
            row["facility_id"],

        "facility_name":
            row["facility_name"],

        "facility_type":
            row["facility_type"],

        "candidate_route":
            row["candidate_route"],

        "route_status":
            row["route_status"],

        "route_length_m":
            route_length,

        "existing_road_overlap_m":
            overlap_length,

        "existing_road_overlap_percentage":
            overlap_percentage,

        "estimated_new_connection_length_m":
            new_connection_length,

        "route_class":
            route_class,

        "combined_score":
            row["combined_score"]
    })


# ------------------------------------------------------------
# Save CSV
# ------------------------------------------------------------

result_df = pd.DataFrame(
    results
)

result_df.to_csv(
    OUTPUT_PATH,
    index=False
)


# ------------------------------------------------------------
# Display summary
# ------------------------------------------------------------

print()
print("=" * 80)
print("PHASE 19 COMPARISON")
print("=" * 80)

print()

print(
    result_df[
        [
            "route_id",
            "facility_id",
            "candidate_route",
            "route_status",
            "route_length_m",
            "existing_road_overlap_percentage",
            "estimated_new_connection_length_m",
            "route_class"
        ]
    ].to_string(
        index=False
    )
)


print()
print("Route classification counts:")

print(
    result_df[
        "route_class"
    ].value_counts()
)


print()
print("Saved:")
print(OUTPUT_PATH)

print()
print("=" * 80)
print("DONE")
print("=" * 80)