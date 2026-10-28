
from pathlib import Path
import pickle

import geopandas as gpd
import networkx as nx
import pandas as pd
from shapely.geometry import Point

BASE = Path(r"D:\Telangana_Rural_Project\Siddipet\Damarakunta")

GRAPH_FILE = BASE / "derived" / "damarakunta_road_graph.gpickle"
FACILITY_FILE = BASE / "reference" / "damarakunta_priority_facilities.gpkg"
BOUNDARY_FILE = BASE / "study_area" / "damarakunta_boundary.gpkg"
OUTPUT_FILE = BASE / "results" / "damarakunta_graph_validation.csv"

CRS = "EPSG:32644"
MAX_SNAP_DISTANCE_M = 500.0


def main():
    for path in [GRAPH_FILE, FACILITY_FILE, BOUNDARY_FILE]:
        if not path.exists():
            raise FileNotFoundError(path)

    # Only load the graph created by your own trusted script.
    with GRAPH_FILE.open("rb") as f:
        graph = pickle.load(f)

    facilities = gpd.read_file(FACILITY_FILE).to_crs(CRS)
    boundary = gpd.read_file(BOUNDARY_FILE).to_crs(CRS)
    area = boundary.geometry.union_all()

    components = list(nx.connected_components(graph))
    component_by_node = {}
    component_sizes = {}

    for component_id, nodes in enumerate(
        sorted(components, key=len, reverse=True), start=1
    ):
        component_sizes[component_id] = len(nodes)
        for node in nodes:
            component_by_node[node] = component_id

    largest_component_id = max(
        component_sizes, key=component_sizes.get
    )

    nodes = list(graph.nodes)
    node_points = [Point(x, y) for x, y in nodes]

    print("=" * 68)
    print("DAMARAKUNTA ROAD GRAPH VALIDATION")
    print("=" * 68)
    print("Graph nodes:", graph.number_of_nodes())
    print("Graph edges:", graph.number_of_edges())
    print("Connected components:", len(components))
    print("Largest component nodes:", component_sizes[largest_component_id])
    print("Largest component ID:", largest_component_id)

    rows = []

    for _, facility in facilities.iterrows():
        point = facility.geometry

        distances = [
            point.distance(node_point) for node_point in node_points
        ]
        nearest_index = min(
            range(len(distances)), key=distances.__getitem__
        )

        nearest_node = nodes[nearest_index]
        snap_distance = distances[nearest_index]
        component_id = component_by_node[nearest_node]

        # A second diagnostic: closest node in the largest component.
        largest_nodes = [
            node for node in graph.nodes
            if component_by_node[node] == largest_component_id
        ]
        largest_distances = [
            point.distance(Point(node)) for node in largest_nodes
        ]
        largest_index = min(
            range(len(largest_distances)),
            key=largest_distances.__getitem__
        )

        largest_node = largest_nodes[largest_index]
        largest_distance = largest_distances[largest_index]

        rows.append({
            "facility_id": facility["facility_id"],
            "facility_name": facility["facility_name"],
            "facility_type": facility["facility_type"],
            "inside_boundary": area.covers(point),
            "nearest_graph_node_distance_m": round(snap_distance, 2),
            "nearest_node_component": component_id,
            "nearest_component_size": component_sizes[component_id],
            "nearest_node_in_largest_component":
                component_id == largest_component_id,
            "largest_component_nearest_node_distance_m":
                round(largest_distance, 2),
            "within_500m_of_largest_component":
                largest_distance <= MAX_SNAP_DISTANCE_M,
            "nearest_node_easting": round(nearest_node[0], 2),
            "nearest_node_northing": round(nearest_node[1], 2),
        })

    report = pd.DataFrame(rows)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    if OUTPUT_FILE.exists():
        raise FileExistsError(
            f"Output already exists: {OUTPUT_FILE}. "
            "Review or rename it before rerunning."
        )

    report.to_csv(OUTPUT_FILE, index=False)

    print("\nFacility results:")
    print(report.to_string(index=False))
    print("\nSaved report:", OUTPUT_FILE)
    print("No source files or graph data were modified.")
    print(
        "\nNote: nearest-node distances are straight-line distances. "
        "They do not prove a usable entrance or a valid road connection."
    )


if __name__ == "__main__":
    main()
