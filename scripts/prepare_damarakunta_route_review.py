
from pathlib import Path
import geopandas as gpd
import pandas as pd

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

# Keep roads within 250 m of at least one priority facility.
nearby_road_mask = roads.geometry.apply(
    lambda geom: any(
        geom.distance(point) <= 250
        for point in facilities.geometry
        if point is not None and not point.is_empty
    )
)
nearby_roads = roads.loc[nearby_road_mask].copy()

# Give each output a common set of review attributes.
facility_review = facilities[
    ["facility_id", "facility_name", "facility_type",
     "priority_group", "geometry"]
].copy()

road_review = nearby_roads[
    ["RD_TYPE", "RD_SUB_TYP", "OWNER", "ROAD_NAME", "geometry"]
].copy()
road_review["review_layer"] = "Existing road"

route_review = routes[
    ["facility_id", "facility_name", "route_length_m",
     "start_road_distance_m", "end_road_distance_m", "geometry"]
].copy()
route_review["review_layer"] = "Existing candidate route"

out = RESULTS / "damarakunta_route_review.gpkg"
if out.exists():
    raise FileExistsError(
        f"{out} already exists. Rename it before rerunning; "
        "this script will not overwrite it."
    )

facility_review.to_file(
    out, layer="facilities", driver="GPKG"
)
road_review.to_file(
    out, layer="nearby_roads", driver="GPKG"
)
route_review.to_file(
    out, layer="candidate_routes", driver="GPKG"
)

print("Review map layers created:", out)
print("Facilities:", len(facility_review))
print("Nearby road features:", len(road_review))
print("Candidate routes:", len(route_review))
print("CRS:", CRS)
print("No source files were modified.")
