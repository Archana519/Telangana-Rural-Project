import pickle
import geopandas as gpd
import networkx as nx
import pandas as pd
from scipy.spatial import cKDTree
from pathlib import Path

BASE = Path(r"D:\Telangana_Rural_Project\Siddipet\Angadi_Kistapur")

GRAPH_PATH = BASE / "derived" / "tgrac_road_graph.gpickle"
FACILITIES_PATH = BASE / "reference" / "priority_facilities_angadi_kistapur.gpkg"

OUTPUT_PATH = (
    BASE / "results" /
    "phase18_facility_road_connections.csv"
)


print("Loading road graph...")

with open(GRAPH_PATH, "rb") as f:
    G = pickle.load(f)


print("Loading priority facilities...")

facilities = gpd.read_file(FACILITIES_PATH)


print()
print("Graph nodes:", G.number_of_nodes())
print("Graph edges:", G.number_of_edges())
print("Facilities:", len(facilities))


# ------------------------------------------------------------
# Extract graph node coordinates
# ------------------------------------------------------------

nodes = list(G.nodes)

node_coords = [
    (float(n[0]), float(n[1]))
    for n in nodes
]

tree = cKDTree(node_coords)


# ------------------------------------------------------------
# Determine connected components
# ------------------------------------------------------------

components = list(nx.connected_components(G))

component_lookup = {}

for component_id, component in enumerate(
    components,
    start=1
):

    for node in component:

        component_lookup[node] = component_id


largest_component_id = max(
    range(len(components)),
    key=lambda i: len(components[i])
) + 1


print()
print(
    "Connected components:",
    len(components)
)

print(
    "Largest component ID:",
    largest_component_id
)

print(
    "Largest component size:",
    len(
        components[
            largest_component_id - 1
        ]
    )
)


# ------------------------------------------------------------
# Facility → nearest graph node
# ------------------------------------------------------------

print()
print("=" * 70)
print(
    "FACILITY → NEAREST TGRAC ROAD GRAPH NODE"
)
print("=" * 70)


results = []


for _, row in facilities.iterrows():

    facility_id = row.get(
        "facility_id",
        "Unknown"
    )

    facility_name = row.get(
        "facility_name",
        "Unknown"
    )

    facility_type = row.get(
        "facility_type",
        "Unknown"
    )

    priority_group = row.get(
        "priority_group",
        "Unknown"
    )

    point = row.geometry

    x = float(point.x)
    y = float(point.y)


    # --------------------------------------------------------
    # Find nearest graph node
    # --------------------------------------------------------

    distance, index = tree.query(
        [x, y]
    )

    nearest_node = nodes[index]

    component_id = component_lookup[
        nearest_node
    ]


    is_largest_component = (
        component_id ==
        largest_component_id
    )


    print()

    print(
        "Facility ID:",
        facility_id
    )

    print(
        "Facility:",
        facility_name
    )

    print(
        "Type:",
        facility_type
    )

    print(
        "Priority group:",
        priority_group
    )

    print(
        "Facility coordinates:",
        round(x, 3),
        round(y, 3)
    )

    print(
        "Nearest graph node:",
        nearest_node
    )

    print(
        "Distance to graph node (m):",
        round(
            float(distance),
            2
        )
    )

    print(
        "Road component:",
        component_id
    )

    print(
        "Largest component:",
        "YES"
        if is_largest_component
        else "NO"
    )


    # --------------------------------------------------------
    # Store result
    # --------------------------------------------------------

    results.append({

        "facility_id":
            facility_id,

        "facility_name":
            facility_name,

        "facility_type":
            facility_type,

        "priority_group":
            priority_group,

        "facility_x_m":
            x,

        "facility_y_m":
            y,

        "nearest_graph_x_m":
            float(nearest_node[0]),

        "nearest_graph_y_m":
            float(nearest_node[1]),

        "facility_to_road_distance_m":
            float(distance),

        "road_component":
            component_id,

        "largest_component":
            bool(is_largest_component)
    })


# ------------------------------------------------------------
# Save CSV
# ------------------------------------------------------------

result_df = pd.DataFrame(results)


result_df.to_csv(
    OUTPUT_PATH,
    index=False
)


print()
print("=" * 70)
print("FACILITY → ROAD CONNECTION SUMMARY")
print("=" * 70)

print(
    result_df.to_string(
        index=False
    )
)


print()
print("Saved:")
print(OUTPUT_PATH)

print()
print("=" * 70)
print("DONE")
print("=" * 70)