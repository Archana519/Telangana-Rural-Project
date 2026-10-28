import pickle
import geopandas as gpd
import numpy as np
import pandas as pd
from pathlib import Path
from scipy.spatial import cKDTree
from shapely.geometry import LineString
import heapq
import math
import json


BASE = Path(
    r"D:\Telangana_Rural_Project\Siddipet\Angadi_Kistapur"
)

GRAPH_PATH = (
    BASE / "derived" /
    "tgrac_road_graph.gpickle"
)

FACILITIES_PATH = (
    BASE / "reference" /
    "priority_facilities_angadi_kistapur.gpkg"
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
    "phase18_new_road_candidates.csv"
)

K = 5

# Search radius around each facility.
# We will generate several candidate endpoints
# on the existing road network.
SEARCH_RADIUS_M = 500.0


print("=" * 80)
print("GENERATING NEW ROAD CONNECTION CANDIDATES")
print("=" * 80)


# ------------------------------------------------------------
# Load road graph
# ------------------------------------------------------------

print()
print("Loading TGRAC road graph...")

with open(GRAPH_PATH, "rb") as f:
    G = pickle.load(f)


# ------------------------------------------------------------
# Load facilities
# ------------------------------------------------------------

print("Loading priority facilities...")

facilities = gpd.read_file(
    FACILITIES_PATH
)


# ------------------------------------------------------------
# Load cost surface
# ------------------------------------------------------------

print("Loading cost surface...")

import rasterio

cost_src = rasterio.open(
    COST_PATH
)

cost_array = cost_src.read(1)

cost_transform = cost_src.transform

cost_nodata = cost_src.nodata


# ------------------------------------------------------------
# Load WorldCover
# ------------------------------------------------------------

print("Loading WorldCover...")

wc_src = rasterio.open(
    WORLDCOVER_PATH
)

wc_array = wc_src.read(1)

wc_transform = wc_src.transform

wc_nodata = wc_src.nodata


# ------------------------------------------------------------
# Graph information
# ------------------------------------------------------------

nodes = list(G.nodes)

node_coords = np.array(
    [
        [float(node[0]), float(node[1])]
        for node in nodes
    ]
)

node_tree = cKDTree(
    node_coords
)


components = list(
    __import__("networkx").connected_components(G)
)

largest_component = max(
    components,
    key=len
)

largest_nodes = list(
    largest_component
)

largest_coords = np.array(
    [
        [float(node[0]), float(node[1])]
        for node in largest_nodes
    ]
)

largest_tree = cKDTree(
    largest_coords
)


print()
print("Graph nodes:", G.number_of_nodes())
print("Graph edges:", G.number_of_edges())
print("Connected components:", len(components))
print(
    "Largest component:",
    len(largest_component)
)


# ------------------------------------------------------------
# Helper: raster value at coordinate
# ------------------------------------------------------------

def raster_value(
    array,
    transform,
    x,
    y
):

    try:

        col, row = ~transform * (
            x,
            y
        )

        col = int(
            math.floor(col)
        )

        row = int(
            math.floor(row)
        )

        if (
            row < 0 or
            row >= array.shape[0] or
            col < 0 or
            col >= array.shape[1]
        ):
            return None

        return array[
            row,
            col
        ]

    except Exception:

        return None


# ------------------------------------------------------------
# Evaluate straight-line connection
# ------------------------------------------------------------

def evaluate_connection(
    x1,
    y1,
    x2,
    y2
):

    distance = math.hypot(
        x2 - x1,
        y2 - y1
    )

    if distance == 0:
        return (
            0.0,
            0.0,
            0,
            0
        )


    # Sample approximately every 5 m.
    sample_count = max(
        2,
        int(
            math.ceil(
                distance / 5.0
            )
        )
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


    costs = []

    water_samples = 0

    invalid_samples = 0


    for x, y in zip(xs, ys):

        cost_value = raster_value(
            cost_array,
            cost_transform,
            x,
            y
        )

        wc_value = raster_value(
            wc_array,
            wc_transform,
            x,
            y
        )


        if (
            cost_value is None or
            wc_value is None
        ):

            invalid_samples += 1

            continue


        if (
            wc_value == 80
        ):

            water_samples += 1


        if (
            wc_value == 0
        ):

            invalid_samples += 1

            continue


        if (
            cost_nodata is not None and
            cost_value == cost_nodata
        ):

            invalid_samples += 1

            continue


        if (
            cost_value >= 1000
        ):

            invalid_samples += 1

            continue


        costs.append(
            float(cost_value)
        )


    if len(costs) > 0:

        mean_cost = float(
            np.mean(costs)
        )

    else:

        mean_cost = 1000.0


    return (
        distance,
        mean_cost,
        water_samples,
        invalid_samples
    )


# ------------------------------------------------------------
# Generate candidates
# ------------------------------------------------------------

results = []


print()
print("=" * 80)
print("FACILITY → EXISTING ROAD CANDIDATES")
print("=" * 80)


for _, facility in facilities.iterrows():

    facility_id = (
        facility["facility_id"]
    )

    facility_name = (
        facility["facility_name"]
    )

    facility_type = (
        facility["facility_type"]
    )

    priority_group = (
        facility["priority_group"]
    )


    point = facility.geometry

    fx = float(point.x)

    fy = float(point.y)


    print()
    print(
        "Facility:",
        facility_id,
        "-",
        facility_name
    )

    # --------------------------------------------------------
    # Find road nodes within search radius
    # --------------------------------------------------------

    distances, indices = (
        largest_tree.query(
            [fx, fy],
            k=min(
                100,
                len(largest_nodes)
            )
        )
    )


    candidate_targets = []


    for distance, index in zip(
        np.atleast_1d(distances),
        np.atleast_1d(indices)
    ):

        distance = float(distance)

        if distance == 0:
            continue

        if distance > SEARCH_RADIUS_M:
            continue

        target_node = (
            largest_nodes[int(index)]
        )


        candidate_targets.append(
            (
                distance,
                target_node
            )
        )


    # Remove duplicate nodes
    unique_targets = {}

    for distance, node in candidate_targets:

        unique_targets[node] = distance


    candidate_targets = sorted(
        [
            (
                distance,
                node
            )
            for node, distance
            in unique_targets.items()
        ],
        key=lambda x: x[0]
    )


    # --------------------------------------------------------
    # Keep several spatially different targets
    # --------------------------------------------------------

    selected_targets = []

    minimum_target_separation = 25.0


    for distance, node in candidate_targets:

        if len(selected_targets) == 0:

            selected_targets.append(
                (
                    distance,
                    node
                )
            )

        else:

            node_x = float(node[0])
            node_y = float(node[1])

            too_close = False


            for _, selected_node in selected_targets:

                sx = float(
                    selected_node[0]
                )

                sy = float(
                    selected_node[1]
                )

                separation = math.hypot(
                    node_x - sx,
                    node_y - sy
                )


                if (
                    separation <
                    minimum_target_separation
                ):

                    too_close = True

                    break


            if not too_close:

                selected_targets.append(
                    (
                        distance,
                        node
                    )
                )


        if len(selected_targets) >= K:
            break


    # --------------------------------------------------------
    # Evaluate selected candidate connections
    # --------------------------------------------------------

    for candidate_number, (
        target_distance,
        target_node
    ) in enumerate(
        selected_targets,
        start=1
    ):

        tx = float(
            target_node[0]
        )

        ty = float(
            target_node[1]
        )


        (
            route_length,
            mean_cost,
            water_samples,
            invalid_samples
        ) = evaluate_connection(
            fx,
            fy,
            tx,
            ty
        )


        # ----------------------------------------------------
        # Candidate classification
        # ----------------------------------------------------

        if water_samples > 0:

            route_status = (
                "WATER_CROSSED"
            )

        elif invalid_samples > 0:

            route_status = (
                "COVERAGE_GAP"
            )

        else:

            route_status = (
                "VALID_CANDIDATE"
            )


        path_json = json.dumps(
            [
                [fx, fy],
                [tx, ty]
            ]
        )


        results.append({

            "facility_id":
                facility_id,

            "facility_name":
                facility_name,

            "facility_type":
                facility_type,

            "priority_group":
                priority_group,

            "candidate_route":
                candidate_number,

            "facility_x_m":
                fx,

            "facility_y_m":
                fy,

            "target_x_m":
                tx,

            "target_y_m":
                ty,

            "facility_to_target_distance_m":
                route_length,

            "mean_cost":
                mean_cost,

            "water_samples":
                water_samples,

            "coverage_gap_samples":
                invalid_samples,

            "route_status":
                route_status,

            "path_json":
                path_json
        })


        print(
            "Candidate",
            candidate_number,
            "| Distance:",
            round(
                route_length,
                2
            ),
            "m",
            "| Mean cost:",
            round(
                mean_cost,
                3
            ),
            "| Water:",
            water_samples,
            "| Coverage gap:",
            invalid_samples,
            "|",
            route_status
        )


# ------------------------------------------------------------
# Save results
# ------------------------------------------------------------

result_df = pd.DataFrame(
    results
)


OUTPUT_PATH.parent.mkdir(
    parents=True,
    exist_ok=True
)


result_df.to_csv(
    OUTPUT_PATH,
    index=False
)


print()
print("=" * 80)
print("DONE")
print("=" * 80)

print(
    "New-road candidates generated:",
    len(result_df)
)

print()
print("Saved:")
print(OUTPUT_PATH)

print()
print("=" * 80)