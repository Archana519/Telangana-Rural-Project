import requests
import geopandas as gpd
from shapely.geometry import shape

URL = (
    "https://tgrac.telangana.gov.in/arcgis/rest/services/"
    "LIS_Folder/LandInformationSystem_Query/MapServer/0/query"
)

OUTPUT = (
    r"D:\Telangana_Rural_Project\Siddipet\Damarakunta"
    r"\reference\damarakunta_cadastral.gpkg"
)

params = {
    "f": "json",
    "where": "UPPER(Village)='DAMARAKUNTA'",
    "outFields": "*",
    "returnGeometry": "true",
    "outSR": "4326",
    "resultRecordCount": 1000,
}

r = requests.get(URL, params=params, timeout=120)

print("HTTP:", r.status_code)

data = r.json()

if "error" in data:
    print("ERROR:", data["error"])
    raise SystemExit

features = data.get("features", [])

print("Records returned:", len(features))

records = []
no_geometry = 0

for f in features:
    attrs = f["attributes"]
    geom = f.get("geometry")

    if not geom:
        no_geometry += 1
        continue

    try:
        geometry = shape({
            "type": "Polygon",
            "coordinates": geom["rings"]
        })
    except Exception:
        no_geometry += 1
        continue

    attrs["geometry"] = geometry
    records.append(attrs)

print("Records with geometry:", len(records))
print("Records without/invalid geometry:", no_geometry)

gdf = gpd.GeoDataFrame(
    records,
    geometry="geometry",
    crs="EPSG:4326"
)

print("CRS:", gdf.crs)

print("\nGeometry types:")
print(gdf.geometry.geom_type.value_counts())

print("\nValid geometries:", gdf.geometry.is_valid.sum())

gdf.to_file(
    OUTPUT,
    layer="cadastral",
    driver="GPKG"
)

print("\nSaved:")
print(OUTPUT)

print("Records saved:", len(gdf))