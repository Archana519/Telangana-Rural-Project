import geopandas as gpd
import networkx as nx
from shapely.geometry import LineString
from math import hypot

roads_path = r"D:\Telangana_Rural_Project\Siddipet\Angadi_Kistapur\reference\tgrac_road_network_angadi_kistapur.gpkg"

output_path = r"D:\Telangana_Rural_Project\Siddipet\Angadi_Kistapur\derived\tgrac_road_graph.gpickle"

print("Reading TGRAC roads...")

roads = gpd.read_file(roads_path)

if roads.crs.to_epsg() != 32644:
    roads = roads.to_crs("EPSG:32644")

G = nx.Graph()

print("Building road graph...")

for idx, row in roads.iterrows():

    geom = row.geometry

    if geom is None or geom.is_empty:
        continue

    if not isinstance(geom, LineString):
        continue

    coords = list(geom.coords)

    for i in range(len(coords) - 1):

        x1, y1 = coords[i]
        x2, y2 = coords[i + 1]

        node1 = (round(x1, 3), round(y1, 3))
        node2 = (round(x2, 3), round(y2, 3))

        length = hypot(
            node2[0] - node1[0],
            node2[1] - node1[1]
        )

        if length <= 0:
            continue

        G.add_node(node1, x=node1[0], y=node1[1])
        G.add_node(node2, x=node2[0], y=node2[1])

        G.add_edge(
            node1,
            node2,
            length=length
        )

print()
print("DONE")
print("Nodes:", G.number_of_nodes())
print("Edges:", G.number_of_edges())

components = list(nx.connected_components(G))

print("Connected components:", len(components))

if components:
    largest = max(len(c) for c in components)
    print("Largest component nodes:", largest)

import pickle

with open(output_path, "wb") as f:
    pickle.dump(G, f)
print("Graph saved to:")
print(output_path)