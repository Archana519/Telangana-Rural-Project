import requests
import geopandas as gpd
import glob
from pathlib import Path

ROOT = Path(r"D:\Telangana_Rural_Project\Siddipet\Angadi_Kistapur")

boundary_file = glob.glob(
    str(ROOT / "raw" / "tgrac_master_admin" / "village_boundary_*.geojson")
)[0]

boundary = gpd.read_file(boundary_file).to_crs("EPSG:4326")

minx, miny, maxx, maxy = boundary.total_bounds

OUT = ROOT / "reference"
OUT.mkdir(parents=True, exist_ok=True)

LAYERS = {
    "tgrac_road_network": {
        "url": "https://tgrac.telangana.gov.in/arcgis/rest/services/SchoolGIS_Folder/Schools/MapServer/20",
        "fields": "OBJECTID,RD_TYPE,RD_SUB_TYP,PR_ROAD_ID,LENGTH,OWNER,ROAD_NAME,REMARKS,DISTRICT,MANDAL,RD_CODE"
    },
    "tgrac_anganwadi": {
        "url": "https://tgrac.telangana.gov.in/arcgis/rest/services/SchoolGIS_Folder/Schools/MapServer/2",
        "fields": "OBJECTID,District_Name,Mandal_Name,Village_Name,Habitation_Name,Anganwadi_Code,Anganwadi_Name,Total_Enrollment,No_of_Teachers,Class_rooms,Longitude,Latitude"
    }
}

geometry = f"{minx},{miny},{maxx},{maxy}"

for name, info in LAYERS.items():

    print("\n" + "=" * 70)
    print(name)
    print("=" * 70)

    params = {
        "f": "json",
        "where": "1=1",
        "geometry": geometry,
        "geometryType": "esriGeometryEnvelope",
        "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "returnGeometry": "true",
        "outFields": info["fields"],
        "outSR": "4326"
    }

    r = requests.get(
        info["url"] + "/query",
        params=params,
        timeout=60
    )

    print("STATUS:", r.status_code)

    data = r.json()

    if "error" in data:
        print("ERROR:", data["error"])
        continue

    features = data.get("features", [])
    print("FEATURES RETURNED:", len(features))

    if not features:
        continue

    rows = []

    for feature in features:
        attrs = feature.get("attributes", {})
        geom = feature.get("geometry")

        if geom is None:
            continue

        if "x" in geom and "y" in geom:
            from shapely.geometry import Point
            geometry_obj = Point(geom["x"], geom["y"])

        elif "paths" in geom:
            from shapely.geometry import LineString
            paths = geom["paths"]

            for path in paths:
                if len(path) >= 2:
                    rows.append({
                        **attrs,
                        "geometry": LineString(path)
                    })
            continue

        else:
            continue

        rows.append({
            **attrs,
            "geometry": geometry_obj
        })

    if not rows:
        print("No usable geometries.")
        continue

    gdf = gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:4326")

    # Exact village filtering
    village_union = boundary.geometry.union_all()

    inside = gdf[gdf.geometry.intersects(village_union)].copy()

    print("RECORDS AFTER VILLAGE-POLYGON FILTER:", len(inside))

    # Reproject for project GIS use
    inside_utm = inside.to_crs("EPSG:32644")

    output = OUT / f"{name}_angadi_kistapur.gpkg"

    inside_utm.to_file(
        output,
        layer=name,
        driver="GPKG"
    )

    print("SAVED:", output)