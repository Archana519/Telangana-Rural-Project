import os
import json
import geopandas as gpd
from shapely.geometry import shape

# ============================================================
# PHASE 25 - STEP 11D
# SAVE DAMARAKUNTA VILLAGE BOUNDARY
# ============================================================

PROJECT_ROOT = r"D:\Telangana_Rural_Project"

VILLAGE_ROOT = os.path.join(
    PROJECT_ROOT,
    "Siddipet",
    "Damarakunta"
)

STUDY_AREA_DIR = os.path.join(
    VILLAGE_ROOT,
    "study_area"
)

INPUT_FILE = os.path.join(
    PROJECT_ROOT,
    "docs",
    "village_template",
    "damarakunta_boundary_tgrac_query.json"
)

OUTPUT_FILE = os.path.join(
    STUDY_AREA_DIR,
    "damarakunta_boundary.gpkg"
)

print("=" * 80)
print("PHASE 25 - STEP 11D")
print("SAVE DAMARAKUNTA VILLAGE BOUNDARY")
print("=" * 80)


# ============================================================
# 1. CHECK INPUT
# ============================================================

if not os.path.isfile(INPUT_FILE):

    print("\n[ERROR] TGRAC query result not found:")
    print(INPUT_FILE)

    raise SystemExit(1)


# ============================================================
# 2. READ TGRAC JSON
# ============================================================

with open(
    INPUT_FILE,
    "r",
    encoding="utf-8"
) as f:

    data = json.load(f)


features = data.get(
    "features",
    []
)

if len(features) == 0:

    print(
        "\n[ERROR] No boundary features found."
    )

    raise SystemExit(1)


# ============================================================
# 3. VALIDATE DAMARAKUNTA RECORD
# ============================================================

geometries = []
attributes_list = []

for feature in features:

    attributes = feature.get(
        "attributes",
        {}
    )

    village = str(
        attributes.get(
            "Village",
            ""
        )
    ).strip().upper()

    mandal = str(
        attributes.get(
            "Mandal",
            ""
        )
    ).strip().upper()

    district = str(
        attributes.get(
            "District",
            ""
        )
    ).strip().upper()

    geometry = feature.get(
        "geometry"
    )

    if (
        village == "DAMARAKUNTA"
        and mandal == "MARKOOK"
        and district == "SIDDIPET"
        and geometry is not None
    ):

        # ArcGIS polygon geometry
        shapely_geometry = shape(
            {
                "type": "Polygon",
                "coordinates": geometry["rings"]
            }
        )

        geometries.append(
            shapely_geometry
        )

        attributes_list.append(
            {
                "district": "Siddipet",
                "mandal": "Markook",
                "village": "Damarakunta",
                "tgrac_village_code":
                    attributes.get("Village_Code"),
                "tgrac_dmv_code":
                    attributes.get("DMV_Code")
            }
        )


if len(geometries) == 0:

    print(
        "\n[ERROR] Valid Damarakunta boundary "
        "record was not found."
    )

    raise SystemExit(1)


# ============================================================
# 4. CREATE GEODATAFRAME
# ============================================================

gdf = gpd.GeoDataFrame(
    attributes_list,
    geometry=geometries,
    crs="EPSG:32644"
)


# ============================================================
# 5. CREATE VILLAGE DIRECTORIES
# ============================================================

os.makedirs(
    STUDY_AREA_DIR,
    exist_ok=True
)

for directory in [
    "raw",
    os.path.join("raw", "imagery"),
    os.path.join("raw", "dem"),
    os.path.join("raw", "landcover"),
    "reference",
    "aligned",
    "derived",
    "predictions",
    "results"
]:

    os.makedirs(
        os.path.join(
            VILLAGE_ROOT,
            directory
        ),
        exist_ok=True
    )


# ============================================================
# 6. SAVE GPKG
# ============================================================

if os.path.exists(OUTPUT_FILE):

    os.remove(OUTPUT_FILE)


gdf.to_file(
    OUTPUT_FILE,
    layer="village_boundary",
    driver="GPKG"
)


# ============================================================
# 7. REOPEN AND VERIFY
# ============================================================

verified = gpd.read_file(
    OUTPUT_FILE,
    layer="village_boundary"
)


print("\n" + "=" * 80)
print("BOUNDARY VERIFICATION")
print("=" * 80)

print(
    "Records:",
    len(verified)
)

print(
    "CRS:",
    verified.crs
)

print(
    "Geometry types:",
    verified.geometry.geom_type.unique().tolist()
)

print(
    "Valid geometries:",
    int(
        verified.geometry.is_valid.sum()
    )
)

print(
    "Area (m²):",
    float(
        verified.geometry.area.sum()
    )
)

print(
    "Bounds:",
    verified.total_bounds.tolist()
)


# ============================================================
# 8. FINAL VALIDATION
# ============================================================

is_valid = (
    len(verified) == len(geometries)
    and verified.crs.to_epsg() == 32644
    and verified.geometry.notna().all()
    and verified.geometry.is_valid.all()
    and all(
        verified.geometry.geom_type
        == "Polygon"
    )
)

print("\n" + "=" * 80)

if is_valid:

    print(
        "STATUS: DAMARAKUNTA BOUNDARY SAVED "
        "AND VERIFIED SUCCESSFULLY."
    )

    print(
        "\nStudy-area boundary:"
    )

    print(
        OUTPUT_FILE
    )

    print(
        "\nVillage root:"
    )

    print(
        VILLAGE_ROOT
    )

else:

    print(
        "STATUS: BOUNDARY VERIFICATION FAILED."
    )

print(
    "\nPHASE 25 STEP 11D COMPLETED."
)