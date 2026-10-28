
from pathlib import Path
import geopandas as gpd
import networkx as nx
from shapely.geometry import LineString, MultiLineString

base = Path(r"D:\Telangana_Rural_Project\Siddipet\Damarakunta")
roads_path = base / "reference" / "tgrac_road_network.gpkg"
boundary_path = base / "study_area" / "damarakunta_boundary.gpkg"

roads = gpd.read_file(roads_path)
boundary = gpd.read_file(boundary_path)

print("=" * 60)
print("DAMARAKUNTA EXISTING ROAD NETWORK")
print("=" * 60)
print("Road CRS:", roads.crs)
print("Road features:", len(roads))
print("Geometry types:")
print(roads.geometry.geom_type.value_counts().to_dict())

if roads.crs != boundary.crs:
    roads = roads.to_crs(boundary.crs)

area = boundary.geometry.union_all()
roads_inside = roads[roads.geometry.intersects(area)].copy()

print("Features intersecting boundary:", len(roads_inside))
print("Boundary CRS:", boundary.crs)

# Count line parts and vertices, including multipart geometries.
parts = 0
vertices = 0
length_m = 0.0

for geom in roads_inside.geometry:
    if geom is None or geom.is_empty:
        continue

    if isinstance(geom, LineString):
        line_parts = [geom]
    elif isinstance(geom, MultiLineString):
        line_parts = list(geom.geoms)
    else:
        continue

    for line in line_parts:
        parts += 1
        vertices += len(line.coords)
        length_m += line.length

print("Line parts:", parts)
print("Total vertices:", vertices)
print("Total feature length inside/intersecting boundary (m):",
      round(length_m, 2))

# Diagnostic graph: connects matching rounded vertices only.
G = nx.Graph()

for geom in roads_inside.geometry:
    if geom is None or geom.is_empty:
        continue

    if isinstance(geom, LineString):
        line_parts = [geom]
    elif isinstance(geom, MultiLineString):
        line_parts = list(geom.geoms)
    else:
        continue

    for line in line_parts:
        coords = list(line.coords)
        for a, b in zip(coords[:-1], coords[1:]):
            u = (round(a[0], 2), round(a[1], 2))
            v = (round(b[0], 2), round(b[1], 2))
            if u != v:
                G.add_edge(u, v, length=line.length)

components = list(nx.connected_components(G))
print("Diagnostic graph nodes:", G.number_of_nodes())
print("Diagnostic graph edges:", G.number_of_edges())
print("Connected components:", len(components))

if components:
    sizes = sorted((len(c) for c in components), reverse=True)
    print("Largest component sizes:", sizes[:10])

print("\nInspection complete. No files were changed.")
