
from pathlib import Path
import geopandas as gpd
from shapely.ops import nearest_points

BASE = Path(r"D:\Telangana_Rural_Project\Siddipet\Damarakunta")
REF = BASE / "reference"
RESULTS = BASE / "results"
CRS = "EPSG:32644"

facilities = gpd.read_file(
    REF / "damarakunta_priority_facilities.gpkg"
).to_crs(CRS)

roads = gpd.read_file(
    REF / "tgrac_road_network.gpkg"
).to_crs(CRS)

routes = gpd.read_file(
    RESULTS / "damarakunta_validated_route_diagnostics.gpkg"
).to_crs(CRS)

road_geometries = [
    (idx, row) for idx, row in roads.iterrows()
    if row.geometry is not None and not row.geometry.is_empty
]

def inspect_location(label, point):
    distances = [
        (point.distance(row.geometry), idx, row)
        for idx, row in road_geometries
    ]
    distances.sort(key=lambda x: x[0])

    print(f"\n{label}")
    for distance, idx, road in distances[:3]:
        nearest_on_road = nearest_points(point, road.geometry)[1]
        print(
            f"  Distance: {distance:.2f} m"
            f" | feature index: {idx}"
            f" | RD_TYPE: {road.get('RD_TYPE', 'Unknown')}"
            f" | RD_SUB_TYP: {road.get('RD_SUB_TYP', 'Unknown')}"
            f" | OWNER: {road.get('OWNER', 'Unknown')}"
            f" | ROAD_NAME: {road.get('ROAD_NAME', 'Unknown')}"
            f" | nearest road point: "
            f"({nearest_on_road.x:.2f}, {nearest_on_road.y:.2f})"
        )

print("NEAREST ROAD INSPECTION")
print("Distances are straight-line GIS distances, not travel distances.")

for _, facility in facilities.iterrows():
    point = facility.geometry
    name = facility["facility_name"]
    inspect_location(f"{name} — facility point", point)

    matches = routes[
        routes["facility_id"].astype(str)
        == str(facility["facility_id"])
    ]

    for _, route in matches.iterrows():
        line = route.geometry
        if line is None or line.is_empty or line.geom_type != "LineString":
            continue

        coords = list(line.coords)
        inspect_location(
            f"{name} — candidate route START",
            gpd.GeoSeries(
                [__import__("shapely").geometry.Point(coords[0])],
                crs=CRS
            ).iloc[0]
        )
        inspect_location(
            f"{name} — candidate route END",
            gpd.GeoSeries(
                [__import__("shapely").geometry.Point(coords[-1])],
                crs=CRS
            ).iloc[0]
        )

print("\nInspection complete. No files were modified.")
