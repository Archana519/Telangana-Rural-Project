import requests
import geopandas as gpd
from shapely.geometry import shape
from pathlib import Path

# ---------------------------------------------------------
# Damarakunta verified village boundary
# ---------------------------------------------------------

boundary_file = (
    r"D:\Telangana_Rural_Project\Siddipet\Damarakunta"
    r"\study_area\damarakunta_boundary.gpkg"
)

output_dir = Path(
    r"D:\Telangana_Rural_Project\Siddipet\Damarakunta\reference"
)

output_dir.mkdir(parents=True, exist_ok=True)

boundary = gpd.read_file(boundary_file)

print("=== DAMARAKUNTA REFERENCE FEATURE EXTRACTION ===")
print("Boundary CRS:", boundary.crs)

# TGRAC services use EPSG:4326
boundary_wgs84 = boundary.to_crs("EPSG:4326")

minx, miny, maxx, maxy = boundary_wgs84.total_bounds

print("Boundary bounds:")
print("West :", minx)
print("South:", miny)
print("East :", maxx)
print("North:", maxy)

geometry = f"{minx},{miny},{maxx},{maxy}"

# ---------------------------------------------------------
# TGRAC reference layers
# ---------------------------------------------------------

LAYERS = {

    "tgrac_road_network": {
        "url":
        "https://tgrac.telangana.gov.in/arcgis/rest/services/"
        "SchoolGIS_Folder/Schools/MapServer/20"
    },

    "tgrac_anganwadi": {
        "url":
        "https://tgrac.telangana.gov.in/arcgis/rest/services/"
        "SchoolGIS_Folder/Schools/MapServer/2"
    },

    "tgrac_health": {
        "url":
        "https://tgrac.telangana.gov.in/arcgis/rest/services/"
        "GovtHospitals_Folder/Health_Facilities_Query/MapServer/0"
    },

    "tgrac_sub_centres": {
        "url":
        "https://tgrac.telangana.gov.in/arcgis/rest/services/"
        "GovtHospitals_Folder/Health_Facilities_Query/MapServer/6"
    }
}

# ---------------------------------------------------------
# Query and save each layer
# ---------------------------------------------------------

for name, info in LAYERS.items():

    print("\n" + "=" * 75)
    print(name.upper())
    print("=" * 75)

    params = {
        "f": "json",
        "where": "1=1",
        "geometry": geometry,
        "geometryType": "esriGeometryEnvelope",
        "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "returnGeometry": "true",
        "outFields": "*",
        "outSR": "4326"
    }

    try:

        response = requests.get(
            info["url"] + "/query",
            params=params,
            timeout=120
        )

        print("STATUS:", response.status_code)

        data = response.json()

        if "error" in data:
            print("ERROR:", data["error"])
            continue

        features = data.get("features", [])

        print("FEATURES RETURNED:", len(features))

        if not features:
            print("No features returned.")
            continue

        records = []

        for feature in features:

            attributes = feature.get("attributes", {})
            geometry_json = feature.get("geometry")

            record = attributes.copy()

            if geometry_json:

                # ArcGIS geometry → Shapely geometry
                if "x" in geometry_json and "y" in geometry_json:

                    geom = shape({
                        "type": "Point",
                        "coordinates": [
                            geometry_json["x"],
                            geometry_json["y"]
                        ]
                    })

                elif "paths" in geometry_json:

                    geom = shape({
                        "type": "MultiLineString",
                        "coordinates": geometry_json["paths"]
                    })

                else:
                    print("Unknown geometry type.")
                    continue

                record["geometry"] = geom
                records.append(record)

        if not records:
            print("No valid geometries created.")
            continue

        gdf = gpd.GeoDataFrame(
            records,
            geometry="geometry",
            crs="EPSG:4326"
        )

        # -------------------------------------------------
        # Reproject to project CRS
        # -------------------------------------------------

        gdf_utm = gdf.to_crs("EPSG:32644")
        boundary_utm = boundary.to_crs("EPSG:32644")

        # -------------------------------------------------
        # Keep only features intersecting actual boundary
        # -------------------------------------------------

        inside = gpd.sjoin(
            gdf_utm,
            boundary_utm[["geometry"]],
            how="inner",
            predicate="intersects"
        )

        if "index_right" in inside.columns:
            inside = inside.drop(columns=["index_right"])

        print(
            "FEATURES INSIDE DAMARAKUNTA BOUNDARY:",
            len(inside)
        )

        # -------------------------------------------------
        # Save GeoPackage
        # -------------------------------------------------

        gpkg_file = output_dir / f"{name}.gpkg"

        inside.to_file(
            gpkg_file,
            layer=name,
            driver="GPKG"
        )

        print("SAVED:", gpkg_file)

        # -------------------------------------------------
        # Save CSV for point layers
        # -------------------------------------------------

        if name != "tgrac_road_network":

            csv_file = output_dir / f"{name}.csv"

            csv_data = inside.copy()

            csv_data["longitude"] = (
                csv_data.to_crs("EPSG:4326").geometry.x
            )

            csv_data["latitude"] = (
                csv_data.to_crs("EPSG:4326").geometry.y
            )

            csv_data = csv_data.drop(
                columns=["geometry"]
            )

            csv_data.to_csv(
                csv_file,
                index=False
            )

            print("SAVED:", csv_file)

    except Exception as e:

        print("ERROR:", repr(e))


print("\n" + "=" * 75)
print("REFERENCE FEATURE EXTRACTION COMPLETE")
print("=" * 75)