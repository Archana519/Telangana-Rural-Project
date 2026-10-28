
from pathlib import Path

import geopandas as gpd
import networkx as nx
from shapely.geometry import LineString, MultiLineString
from shapely.ops import unary_union

BASE = Path(r"D:\Telangana_Rural_Project\Siddipet\Damarakunta")
ROADS_FILE = BASE / "reference" / "tgrac_road_network.gpkg"
BOUNDARY_FILE = BASE / "study_area" / "damarakunta_boundary.gpkg"
OUTPUT_FILE = BASE / "derived" / "damarakunta_road_graph.gpickle"

CRS = "EPSG:32644"

# Tolerance is used only to round coordinates for graph-node identity.
# It does NOT move the original road geometries.
COORD_PRECISION = 2


def line_parts(geom):
    """Extract LineString parts from supported line geometries."""
    if geom is None or geom.is_empty:
        return []
    if isinstance(geom, LineString):
        return [geom]
    if isinstance(geom, MultiLineString):
        return list(geom.geoms)
    if hasattr(geom, "geoms"):
        parts = []
        for subgeom in geom.geoms:
            parts.extend(line_parts(subgeom))
        return parts
    return []


def node_id(x, y):
    return (round(float(x), COORD_PRECISION),
            round(float(y), COORD_PRECISION))


def main():
    if not ROADS_FILE.exists():
        raise FileNotFoundError(ROADS_FILE)
    if not BOUNDARY_FILE.exists():
        raise FileNotFoundError(BOUNDARY_FILE)

    roads = gpd.read_file(ROADS_FILE).to_crs(CRS)
    boundary = gpd.read_file(BOUNDARY_FILE).to_crs(CRS)

    area = boundary.geometry.union_all()

    # Clip roads to the study boundary before graph creation.
    clipped_lines = []
    for geom in roads.geometry:
        if geom is None or geom.is_empty:
            continue
        clipped = geom.intersection(area)
        clipped_lines.extend(line_parts(clipped))

    if not clipped_lines:
        raise ValueError("No road lines found inside the study boundary.")

    print("Clipped line parts:", len(clipped_lines))

    # Split lines at geometric intersections. This is more reliable than
    # connecting only the original vertices, although grade-separated
    # crossings still require additional information.
    noded = unary_union(clipped_lines)
    noded_lines = line_parts(noded)

    graph = nx.Graph()
    total_length = 0.0

    for line in noded_lines:
        coords = list(line.coords)
        for a, b in zip(coords[:-1], coords[1:]):
            u = node_id(a[0], a[1])
            v = node_id(b[0], b[1])

            if u == v:
                continue

            length = LineString([a, b]).length
            if length <= 0:
                continue

            total_length += length

            # Retain the shortest edge if coordinate rounding causes
            # duplicate node pairs.
            if graph.has_edge(u, v):
                graph[u][v]["length"] = min(
                    graph[u][v]["length"], length
                )
            else:
                graph.add_edge(u, v, length=length)

    if graph.number_of_nodes() == 0:
        raise ValueError("The graph contains no usable edges.")

    components = sorted(
        nx.connected_components(graph),
        key=len,
        reverse=True
    )

    print("\nDAMARAKUNTA ROAD GRAPH")
    print("CRS:", CRS)
    print("Nodes:", graph.number_of_nodes())
    print("Edges:", graph.number_of_edges())
    print("Connected components:", len(components))
    print("Largest component sizes:", [len(c) for c in components[:10]])
    print("Summed noded edge length (m):", round(total_length, 2))

    graph.graph["crs"] = CRS
    graph.graph["study_area"] = "Damarakunta"
    graph.graph["edge_weight"] = "length"
    graph.graph["coordinate_precision_m"] = COORD_PRECISION
    graph.graph["source"] = str(ROADS_FILE)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Never overwrite an existing graph without review.
    if OUTPUT_FILE.exists():
        raise FileExistsError(
            f"Output already exists: {OUTPUT_FILE}\n"
            "Rename or inspect it before running this script again."
        )

    # NetworkX graph persistence via pickle.
    import pickle
    with OUTPUT_FILE.open("wb") as f:
        pickle.dump(graph, f)

    print("Saved graph:", OUTPUT_FILE)
    print("Original road data was not changed.")


if __name__ == "__main__":
    main()
