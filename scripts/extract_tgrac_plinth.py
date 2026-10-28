import requests
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union

PROJECT_ROOT = r"D:\Telangana_Rural_Project"

BOUNDARY = (
    PROJECT_ROOT
    + r"\Siddipet\Angadi_Kistapur\raw\tgrac_master_admin"
    + r"\village_boundary_20260930T115300Z.geojson"
)

OUTPUT_GPKG = (
    PROJECT_ROOT
    + r"\Siddipet\Angadi_Kistapur\reference"
    + r"\tgrac_plinth_angadi_kistapur.gpkg"
)

OUTPUT_CSV = (
    PROJECT_ROOT
    + r"\Siddipet\Angadi_Kistapur\reference"
    + r"\tgrac_plinth_angadi_kistapur.csv"
)

URL = (
    "https://tgrac.telangana.gov.in/"
    "arcgis/rest/services/Abadi_Folder/"
    "Abadi_Final/MapServer/20/query"
)

print("=" * 70)
print("TGRAC PLINTH EXTRACTION — ANGADI KISTAPUR")
print("=" * 70)

boundary = gpd.read_file(BOUNDARY).to_crs(4326)
village_geometry = boundary.geometry.iloc[0]

minx, miny, maxx, maxy = boundary.total_bounds

print("\nVillage bounding box:")
print("West :", minx)
print("South:", miny)
print("East :", maxx)
print("North:", maxy)

params = {
    "where": "1=1",
    "geometry": f"{minx},{miny},{maxx},{maxy}",
    "geometryType": "esriGeometryEnvelope",
    "inSR": "4326",
    "spatialRel": "esriSpatialRelIntersects",
    "outFields": "OBJECTID_1,TYPE,Area_SFt,GP_Name,Shape_Area",
    "returnGeometry": "true",
    "outSR": "4326",
    "f": "json",
    "resultRecordCount": 1000,
}

print("\nQuerying TGRAC...")

response = requests.get(URL, params=params, timeout=120)

print("HTTP STATUS:", response.status_code)

response.raise_for_status()

data = response.json()

if "error" in data:
    print("\nTGRAC ERROR:")
    print(data["error"])
    raise SystemExit(1)

features = data.get("features", [])

print("BBOX RECORDS RETURNED:", len(features))

records = []

skipped_no_geometry = 0
skipped_invalid_geometry = 0

for feature in features:

    geometry_data = feature.get("geometry")

    if not geometry_data:
        skipped_no_geometry += 1
        continue

    rings = geometry_data.get("rings")

    if not rings:
        skipped_invalid_geometry += 1
        continue

    try:

        polygons = []

        for ring in rings:

            if len(ring) < 4:
                continue

            polygon = Polygon(ring)

            if not polygon.is_empty and polygon.is_valid:
                polygons.append(polygon)

        if not polygons:
            skipped_invalid_geometry += 1
            continue

        if len(polygons) == 1:
            geometry = polygons[0]
        else:
            geometry = unary_union(polygons)

        attributes = feature.get("attributes", {})

        records.append(
            {
                **attributes,
                "geometry": geometry
            }
        )

    except Exception:
        skipped_invalid_geometry += 1

print("\nGeometry processing:")
print("Valid geometries:", len(records))
print("Skipped — no geometry:", skipped_no_geometry)
print("Skipped — invalid geometry:", skipped_invalid_geometry)

if not records:
    print("\nNo valid Plinth geometries were returned.")
    raise SystemExit(1)

plinth = gpd.GeoDataFrame(
    records,
    geometry="geometry",
    crs="EPSG:4326"
)

print("\nApplying exact village boundary filter...")

plinth = plinth[
    plinth.geometry.intersects(village_geometry)
].copy()

print("VILLAGE-FILTERED RECORDS:", len(plinth))

if len(plinth) == 0:
    print("\nNo Plinth polygons intersect the village boundary.")
    raise SystemExit(1)

plinth.to_file(
    OUTPUT_GPKG,
    layer="plinth",
    driver="GPKG"
)

plinth.drop(
    columns="geometry"
).to_csv(
    OUTPUT_CSV,
    index=False
)

print("\nSaved GeoPackage:")
print(OUTPUT_GPKG)

print("\nSaved CSV:")
print(OUTPUT_CSV)

print("\n" + "=" * 70)
print("PLINTH SUMMARY")
print("=" * 70)

print("Records:", len(plinth))

if "Area_SFt" in plinth.columns:
    total_area = plinth["Area_SFt"].fillna(0).sum()
    print("Total plinth area (sq ft):", round(total_area, 2))

if "TYPE" in plinth.columns:
    print("\nTypes:")
    print(
        plinth["TYPE"]
        .fillna("UNKNOWN")
        .value_counts()
        .to_string()
    )

if "GP_Name" in plinth.columns:
    print("\nGP names:")
    print(
        plinth["GP_Name"]
        .fillna("UNKNOWN")
        .value_counts()
        .to_string()
    )

print("\n" + "=" * 70)
print("EXTRACTION COMPLETED")
print("=" * 70)