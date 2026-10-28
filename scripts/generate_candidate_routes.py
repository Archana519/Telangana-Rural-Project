import pickle
import geopandas as gpd
import networkx as nx
from pathlib import Path
from scipy.spatial import cKDTree
import math
import csv
import json

BASE = Path(r"D:\Telangana_Rural_Project\Siddipet\Angadi_Kistapur")

GRAPH_PATH = BASE / "derived" / "tgrac_road_graph.gpickle"
FACILITIES_PATH = BASE / "reference" / "priority_facilities_angadi_kistapur.gpkg"

OUTPUT_PATH = (
    BASE / "results" / "phase18_candidate_routes_with_paths.csv"
)

K = 5

print("Loading road graph...")

with open(GRAPH_PATH, "rb") as f:
    G = pickle.load(f)

print("Loading priority facilities...")

facilities = gpd.read_file(FACILITIES_PATH)

nodes = list(G.nodes)

node_coords = [
    (float(node[0]), float(node[1]))
    for node in nodes
]

tree = cKDTree(node_coords)

components = list(nx.connected_components(G))

largest_component = max(components, key=len)

print()
print("Graph nodes:", G.number_of_nodes())
print("Graph edges:", G.number_of_edges())
print("Connected components:", len(components))
print("Largest component:", len(largest_component))

results = []

print()
print("=" * 75)
print("GENERATING CANDIDATE ROUTES WITH ACTUAL GRAPH PATHS")
print("=" * 75)

for _, facility in facilities.iterrows():

    facility_id = facility["facility_id"]
    facility_name = facility["facility_name"]
    facility_type = facility["facility_type"]

    point = facility.geometry

    fx = float(point.x)
    fy = float(point.y)

    distance, index = tree.query([fx, fy])

    start_node = nodes[index]

    # Make sure starting node belongs to largest component
    if start_node not in largest_component:

        largest_nodes = list(largest_component)

        largest_coords = [
            (float(n[0]), float(n[1]))
            for n in largest_nodes
        ]

        largest_tree = cKDTree(largest_coords)

        distance, index = largest_tree.query(
            [fx, fy]
        )

        start_node = largest_nodes[index]

    print()
    print("Facility:", facility_id, "-", facility_name)
    print("Start node:", start_node)
    print(
        "Facility-to-road distance:",
        round(float(distance), 2),
        "m"
    )

    # ----------------------------------------------------------
    # Select nearby target nodes
    # ----------------------------------------------------------

    search_k = min(15, len(nodes))

    distances, indices = tree.query(
        [float(start_node[0]), float(start_node[1])],
        k=search_k
    )

    target_nodes = []

    for idx in indices:

        node = nodes[int(idx)]

        if node in largest_component and node != start_node:
            target_nodes.append(node)

    target_nodes = target_nodes[:K]

    candidate_number = 0

    for target_node in target_nodes:

        try:

            path = nx.shortest_path(
                G,
                source=start_node,
                target=target_node,
                weight="length"
            )

            if len(path) < 2:
                continue

            route_length = 0.0

            # Calculate actual graph-path length
            for u, v in zip(path[:-1], path[1:]):

                edge_data = G.get_edge_data(u, v)

                if edge_data is None:
                    continue

                edge_length = edge_data.get("length")

                if edge_length is None:

                    ux, uy = u
                    vx, vy = v

                    edge_length = math.hypot(
                        vx - ux,
                        vy - uy
                    )

                route_length += float(edge_length)

            candidate_number += 1

            # Store the COMPLETE actual graph path
            path_json = json.dumps(
                [
                    [float(node[0]), float(node[1])]
                    for node in path
                ]
            )

            results.append({
                "facility_id": facility_id,
                "facility_name": facility_name,
                "facility_type": facility_type,
                "candidate_route": candidate_number,
                "start_x": float(start_node[0]),
                "start_y": float(start_node[1]),
                "target_x": float(target_node[0]),
                "target_y": float(target_node[1]),
                "facility_to_road_m": float(distance),
                "route_length_m": route_length,
                "number_of_nodes": len(path),
                "path_json": path_json
            })

            print(
                "Candidate",
                candidate_number,
                "| Length:",
                round(route_length, 2),
                "m",
                "| Nodes:",
                len(path)
            )

        except nx.NetworkXNoPath:

            print(
                "No path:",
                start_node,
                "->",
                target_node
            )

OUTPUT_PATH.parent.mkdir(
    parents=True,
    exist_ok=True
)

fieldnames = [
    "facility_id",
    "facility_name",
    "facility_type",
    "candidate_route",
    "start_x",
    "start_y",
    "target_x",
    "target_y",
    "facility_to_road_m",
    "route_length_m",
    "number_of_nodes",
    "path_json"
]

with open(
    OUTPUT_PATH,
    "w",
    newline="",
    encoding="utf-8"
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=fieldnames
    )

    writer.writeheader()
    writer.writerows(results)

print()
print("=" * 75)
print("DONE")
print("=" * 75)

print("Candidate routes generated:", len(results))
print("Saved to:")
print(OUTPUT_PATH)