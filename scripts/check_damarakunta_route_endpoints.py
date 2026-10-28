
import geopandas as gpd
from shapely.geometry import Point

BASE = r"D:\Telangana_Rural_Project\Siddipet\Damarakunta"

routes = gpd.read_file(
    BASE + r"\results\damarakunta_routes_v3.gpkg"
)

facilities = gpd.read_file(
    BASE + r"\reference\damarakunta_priority_facilities.gpkg"
).to_crs(routes.crs)

roads = gpd.read_file(
    BASE + r"\reference\tgrac_road_network.gpkg"
).to_crs(routes.crs)

def find_id_column(frame):
    for column in frame.columns:
        if column.lower() in {
            "facility_id", "facilityid", "id", "nin_id"
        }:
            return column
    raise ValueError(
        f"No facility ID column found. Columns: {list(frame.columns)}"
    )

route_id_col = find_id_column(routes)
facility_id_col = find_id_column(facilities)

road_geometries = [
    geom for geom in roads.geometry
    if geom is not None and not geom.is_empty
]

if not road_geometries:
    raise ValueError("No valid road geometries found.")

print("facility_id | alt | A-to-facility | B-to-facility | A-to-road | B-to-road")
print("-" * 95)

for _, route in routes.iterrows():
    route_id = str(route[route_id_col]).replace(".0", "")
    matches = facilities[
        facilities[facility_id_col].astype(str).str.replace(
            ".0", "", regex=False
        ) == route_id
    ]

    if matches.empty:
        print(f"{route_id} | {route.get('alternative')} | FACILITY NOT MATCHED")
        continue

    geometry = route.geometry
    if geometry is None or geometry.is_empty or geometry.geom_type != "LineString":
        print(f"{route_id} | {route.get('alternative')} | INVALID ROUTE GEOMETRY")
        continue

    facility_point = matches.geometry.iloc[0]
    coords = list(geometry.coords)
    endpoint_a = Point(coords[0])
    endpoint_b = Point(coords[-1])

    a_to_road = min(endpoint_a.distance(road) for road in road_geometries)
    b_to_road = min(endpoint_b.distance(road) for road in road_geometries)

    print(
        f"{route_id} | {route.get('alternative')} | "
        f"{endpoint_a.distance(facility_point):.2f} m | "
        f"{endpoint_b.distance(facility_point):.2f} m | "
        f"{a_to_road:.2f} m | {b_to_road:.2f} m"
    )
