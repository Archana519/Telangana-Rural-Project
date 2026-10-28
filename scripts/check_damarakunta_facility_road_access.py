
from pathlib import Path
import geopandas as gpd
import pandas as pd

BASE = Path(r"D:\Telangana_Rural_Project\Siddipet\Damarakunta")
fac_path = BASE / "reference" / "damarakunta_priority_facilities.gpkg"
roads_path = BASE / "reference" / "tgrac_road_network.gpkg"
boundary_path = BASE / "study_area" / "damarakunta_boundary.gpkg"

facilities = gpd.read_file(fac_path).to_crs("EPSG:32644")
roads = gpd.read_file(roads_path).to_crs("EPSG:32644")
boundary = gpd.read_file(boundary_path).to_crs("EPSG:32644")

area = boundary.geometry.union_all()

# Restrict the road geometries to the study-area boundary.
clipped_geometries = []
for geom in roads.geometry:
    if geom is None or geom.is_empty:
        continue
    clipped = geom.intersection(area)
    if not clipped.is_empty and clipped.length > 0:
        clipped_geometries.append(clipped)

if not clipped_geometries:
    raise ValueError("No road lines intersect the study area.")

print("=" * 70)
print("DAMARAKUNTA FACILITY-TO-ROAD ACCESS DIAGNOSTIC")
print("=" * 70)
print("Facilities:", len(facilities))
print("Road geometries after clipping:", len(clipped_geometries))

results = []

for _, facility in facilities.iterrows():
    point = facility.geometry

    distances = [point.distance(road) for road in clipped_geometries]
    nearest_idx = min(range(len(distances)), key=distances.__getitem__)
    distance = distances[nearest_idx]
    nearest_road = clipped_geometries[nearest_idx]
    nearest_point = nearest_road.interpolate(
        nearest_road.project(point)
    )

    result = {
        "facility_id": facility["facility_id"],
        "facility_name": facility["facility_name"],
        "facility_type": facility["facility_type"],
        "inside_boundary": area.covers(point),
        "nearest_road_distance_m": round(distance, 2),
        "nearest_road_easting": round(nearest_point.x, 2),
        "nearest_road_northing": round(nearest_point.y, 2),
        "within_10m": distance <= 10,
        "within_25m": distance <= 25,
        "within_50m": distance <= 50,
    }
    results.append(result)

report = pd.DataFrame(results)

print("\nFacility access distances:")
print(report.to_string(index=False))

print("\nInterpretation:")
print("- These are straight-line distances to mapped existing roads.")
print("- They do not prove a usable entrance or an actual road connection.")
print("- Short distances can still be blocked by walls, buildings or terrain.")
print("- No source files were changed.")
