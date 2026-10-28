import requests
import json

# ============================================================
# PHASE 25 - STEP 11C
# VERIFY DAMARAKUNTA VILLAGE BOUNDARY FROM TGRAC
# ============================================================

URL = (
    "https://tgrac.telangana.gov.in/arcgis/rest/services/"
    "AdministrativeInfoSystem_Folder/"
    "Administrative_Information_System/MapServer/27/query"
)

# First request: inspect the layer fields
FIELD_PARAMS = {
    "where": "1=1",
    "outFields": "*",
    "returnGeometry": "false",
    "resultRecordCount": 1,
    "f": "json"
}

print("=" * 80)
print("PHASE 25 - STEP 11C")
print("DAMARAKUNTA VILLAGE BOUNDARY VERIFICATION")
print("=" * 80)

try:

    response = requests.get(
        URL,
        params=FIELD_PARAMS,
        timeout=30
    )

    response.raise_for_status()

    layer_data = response.json()

except Exception as e:

    print("\n[ERROR] TGRAC request failed:")
    print(e)
    raise SystemExit(1)


if "error" in layer_data:

    print("\n[ERROR] TGRAC returned an error:")
    print(
        json.dumps(
            layer_data["error"],
            indent=2
        )
    )

    raise SystemExit(1)


features = layer_data.get(
    "features",
    []
)

if len(features) == 0:

    print(
        "\n[ERROR] No records returned from Village Boundary layer."
    )

    raise SystemExit(1)


attributes = features[0].get(
    "attributes",
    {}
)

print("\n[OK] Village Boundary layer is accessible.")

print("\nAvailable fields:")

for field in attributes.keys():

    print(
        " -",
        field
    )


# ============================================================
# QUERY ALL SIDDIPET / DAMARAKUNTA RECORDS
# ============================================================

QUERY_PARAMS = {
    "where": (
        "UPPER(Village) = 'DAMARAKUNTA'"
    ),
    "outFields": "*",
    "returnGeometry": "true",
    "returnZ": "false",
    "returnM": "false",
    "f": "json"
}

try:

    response = requests.get(
        URL,
        params=QUERY_PARAMS,
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

except Exception as e:

    print("\n[ERROR] Damarakunta query failed:")
    print(e)
    raise SystemExit(1)


if "error" in data:

    print("\n[ERROR] TGRAC returned an error:")
    print(
        json.dumps(
            data["error"],
            indent=2
        )
    )

    raise SystemExit(1)


features = data.get(
    "features",
    []
)

print(
    f"\n[OK] Damarakunta records returned: {len(features)}"
)


# ============================================================
# DISPLAY MATCHING RECORDS
# ============================================================

print("\n" + "=" * 80)
print("DAMARAKUNTA MATCHING RECORDS")
print("=" * 80)

valid_match = False

for i, feature in enumerate(
    features,
    start=1
):

    attrs = feature.get(
        "attributes",
        {}
    )

    geometry = feature.get(
        "geometry"
    )

    print(
        f"\nRecord {i}"
    )

    print(
        "Village:",
        attrs.get("Village")
    )

    print(
        "District:",
        attrs.get("District")
    )

    print(
        "Mandal:",
        attrs.get("Mandal")
    )

    print(
        "Geometry present:",
        geometry is not None
    )

    if geometry:

        rings = geometry.get(
            "rings",
            []
        )

        print(
            "Polygon rings:",
            len(rings)
        )

    village = str(
        attrs.get(
            "Village",
            ""
        )
    ).strip().upper()

    district = str(
        attrs.get(
            "District",
            ""
        )
    ).strip().upper()

    mandal = str(
        attrs.get(
            "Mandal",
            ""
        )
    ).strip().upper()

    if (
        village == "DAMARAKUNTA"
        and district == "SIDDIPET"
        and mandal == "MARKOOK"
        and geometry is not None
    ):

        valid_match = True


# ============================================================
# SAVE RAW TGRAC RESPONSE
# ============================================================

OUTPUT_FILE = (
    r"D:\Telangana_Rural_Project\docs\village_template"
    r"\damarakunta_boundary_tgrac_query.json"
)

with open(
    OUTPUT_FILE,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        data,
        f,
        indent=2
    )


print("\n" + "=" * 80)
print("RAW TGRAC RESULT")
print("=" * 80)

print(
    "Saved to:"
)

print(
    OUTPUT_FILE
)


# ============================================================
# FINAL STATUS
# ============================================================

if valid_match:

    print(
        "\nSTATUS: DAMARAKUNTA BOUNDARY VERIFIED."
    )

    print(
        "Village  : Damarakunta"
    )

    print(
        "Mandal   : Markook"
    )

    print(
        "District : Siddipet"
    )

    print(
        "Geometry : Polygon available"
    )

    print(
        "\nNEXT: Save the verified boundary "
        "as the second-village study-area layer."
    )

else:

    print(
        "\nSTATUS: DAMARAKUNTA RECORD FOUND, "
        "BUT DISTRICT/MANDAL MATCH REQUIRES REVIEW."
    )

print(
    "\nPHASE 25 STEP 11C CHECK COMPLETED."
)