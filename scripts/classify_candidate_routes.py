import pandas as pd
import geopandas as gpd
import networkx as nx
import json
from pathlib import Path
from shapely.geometry import LineString

BASE = Path(r"D:\Telangana_Rural_Project\Siddipet\Angadi_Kistapur")

CANDIDATE_PATH = (
    BASE / "results" /
    "phase18_candidate_routes_with_paths.csv"
)

ROAD_PATH = (
    BASE / "reference" /
    "tgrac_road_network_angadi_kistapur.gpkg"
)

OUTPUT_PATH = (
    BASE / "results" /
    "phase18_candidate_route_classification.csv"
)

df = pd.read_csv(CANDIDATE_PATH)

roads = gpd.read_file(ROAD_PATH)

print("=" * 80)
print("CANDIDATE ROUTE CLASSIFICATION")
print("=" * 80)

print()
print("Reference road features:", len(roads))

results = []

for _, route in df.iterrows():

    path = json.loads(route["path_json"])

    route_line = LineString(path)

    route_length = route_line.length

    # ------------------------------------------------------
    # Compare candidate route with existing TGRAC roads
    # ------------------------------------------------------

    covered_length = 0.0

    for _, road in roads.iterrows():

        intersection = route_line.intersection(
            road.geometry
        )

        if not intersection.is_empty:

            covered_length += intersection.length

    # Avoid counting overlapping road segments more than once.
    covered_length = min(
        covered_length,
        route_length
    )

    if route_length > 0:

        existing_percentage = (
            covered_length /
            route_length
        ) * 100

    else:

        existing_percentage = 0.0

    proposed_percentage = (
        100.0 -
        existing_percentage
    )

    # ------------------------------------------------------
    # Classification
    # ------------------------------------------------------

    if existing_percentage >= 90:

        route_class = "EXISTING_ROAD_CONNECTION"

    elif existing_percentage <= 10:

        route_class = "NEW_ROAD_PROPOSAL"

    else:

        route_class = "MIXED_EXISTING_AND_NEW"

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
            float(route_length),

        "existing_road_length_m":
            float(covered_length),

        "existing_road_percentage":
            float(existing_percentage),

        "proposed_new_road_length_m":
            float(
                max(
                    0,
                    route_length -
                    covered_length
                )
            ),

        "proposed_new_road_percentage":
            float(proposed_percentage),

        "route_class":
            route_class
    })


result_df = pd.DataFrame(results)

result_df = result_df.sort_values(
    [
        "facility_id",
        "candidate_route"
    ]
)

result_df.to_csv(
    OUTPUT_PATH,
    index=False
)

print()
print(
    result_df[
        [
            "facility_id",
            "candidate_route",
            "route_length_m",
            "existing_road_length_m",
            "existing_road_percentage",
            "proposed_new_road_length_m",
            "proposed_new_road_percentage",
            "route_class"
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