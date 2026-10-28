import pandas as pd
import json
from pathlib import Path
import geopandas as gpd
from shapely.geometry import LineString


BASE = Path(
    r"D:\Telangana_Rural_Project\Siddipet\Angadi_Kistapur"
)

INPUT_PATH = (
    BASE / "results" /
    "phase18_new_road_candidate_evaluation.csv"
)

OUTPUT_PATH = (
    BASE / "results" /
    "phase18_new_road_candidates.gpkg"
)


print("=" * 80)
print("CREATING CANDIDATE ROUTE GEOPACKAGE")
print("=" * 80)


# ------------------------------------------------------------
# Load evaluated candidates
# ------------------------------------------------------------

print()
print("Loading candidate evaluation...")

df = pd.read_csv(INPUT_PATH)


# ------------------------------------------------------------
# Create geometries
# ------------------------------------------------------------

records = []


for _, row in df.iterrows():

    path = json.loads(
        row["path_json"]
    ) if "path_json" in df.columns else None

    # The evaluation CSV does not currently contain path_json.
    # Therefore reconstruct the line using the original
    # candidate CSV.

    records.append(row.to_dict())


# ------------------------------------------------------------
# Reload original candidate file to obtain coordinates
# ------------------------------------------------------------

candidate_path = (
    BASE / "results" /
    "phase18_new_road_candidates.csv"
)

candidate_df = pd.read_csv(candidate_path)


# ------------------------------------------------------------
# Merge evaluation + original candidate coordinates
# ------------------------------------------------------------

merge_columns = [
    "facility_id",
    "candidate_route"
]

coord_columns = [
    "facility_id",
    "candidate_route",
    "facility_x_m",
    "facility_y_m",
    "target_x_m",
    "target_y_m"
]

candidate_coords = candidate_df[
    coord_columns
].copy()


merged = df.merge(
    candidate_coords,
    on=merge_columns,
    how="left"
)


# ------------------------------------------------------------
# Build LineString geometry
# ------------------------------------------------------------

geometries = []

for _, row in merged.iterrows():

    facility_point = (
        float(row["facility_x_m"]),
        float(row["facility_y_m"])
    )

    target_point = (
        float(row["target_x_m"]),
        float(row["target_y_m"])
    )

    line = LineString([
        facility_point,
        target_point
    ])

    geometries.append(line)


# ------------------------------------------------------------
# Create GeoDataFrame
# ------------------------------------------------------------

gdf = gpd.GeoDataFrame(
    merged,
    geometry=geometries,
    crs="EPSG:32644"
)


# ------------------------------------------------------------
# Add useful GIS fields
# ------------------------------------------------------------

gdf["route_id"] = (
    gdf["facility_id"].astype(str)
    + "_C"
    + gdf["candidate_route"].astype(str)
)


gdf["candidate_type"] = (
    "NEW_ROAD_CONNECTION"
)


# ------------------------------------------------------------
# Reorder important fields
# ------------------------------------------------------------

preferred_columns = [
    "route_id",
    "facility_id",
    "facility_name",
    "facility_type",
    "priority_group",
    "candidate_route",
    "candidate_type",
    "route_length_m",
    "mean_cost",
    "coverage_gap_percentage",
    "water_percentage",
    "builtup_percentage",
    "cropland_percentage",
    "vegetation_percentage",
    "route_status",
    "length_norm",
    "cost_norm",
    "combined_score",
    "facility_x_m",
    "facility_y_m",
    "target_x_m",
    "target_y_m",
    "geometry"
]


existing_columns = [
    c for c in preferred_columns
    if c in gdf.columns
]


gdf = gdf[
    existing_columns
]


# ------------------------------------------------------------
# Save GeoPackage
# ------------------------------------------------------------

if OUTPUT_PATH.exists():
    OUTPUT_PATH.unlink()


gdf.to_file(
    OUTPUT_PATH,
    layer="candidate_routes",
    driver="GPKG"
)


# ------------------------------------------------------------
# Verification
# ------------------------------------------------------------

print()
print("=" * 80)
print("VERIFICATION")
print("=" * 80)

print()
print("Total candidate routes:", len(gdf))

print()
print("CRS:")
print(gdf.crs)

print()
print("Route counts by facility:")
print(
    gdf.groupby(
        "facility_id"
    ).size()
)

print()
print("Route status:")
print(
    gdf["route_status"].value_counts()
)

print()
print("Output:")
print(OUTPUT_PATH)

print()
print("=" * 80)
print("DONE")
print("=" * 80)