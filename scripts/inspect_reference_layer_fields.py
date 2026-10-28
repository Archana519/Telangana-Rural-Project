import requests

LAYERS = {
    "TGRAC_ROAD_NETWORK": (
        "https://tgrac.telangana.gov.in/arcgis/rest/services/"
        "SchoolGIS_Folder/Schools/MapServer/20"
    ),
    "TGRAC_ANGANWADI": (
        "https://tgrac.telangana.gov.in/arcgis/rest/services/"
        "SchoolGIS_Folder/Schools/MapServer/2"
    ),
    "TGRAC_HEALTH": (
        "https://tgrac.telangana.gov.in/arcgis/rest/services/"
        "GovtHospitals_Folder/Health_Facilities_Query/MapServer/0"
    ),
    "TGRAC_SUB_CENTRES": (
        "https://tgrac.telangana.gov.in/arcgis/rest/services/"
        "GovtHospitals_Folder/Health_Facilities_Query/MapServer/6"
    ),
    "TGRAC_ABADI_ROADS": (
        "https://tgrac.telangana.gov.in/arcgis/rest/services/"
        "Abadi_Folder/Abadi_Final/MapServer/1"
    ),
    "TGRAC_BUILDING_ROOF": (
        "https://tgrac.telangana.gov.in/arcgis/rest/services/"
        "Abadi_Folder/Abadi_Final/MapServer/10"
    ),
}

for name, url in LAYERS.items():

    print("\n" + "=" * 75)
    print(name)
    print(url)
    print("=" * 75)

    r = requests.get(
        url,
        params={"f": "json"},
        timeout=60
    )

    print("STATUS:", r.status_code)

    if r.status_code != 200:
        print("ERROR:", r.text[:500])
        continue

    data = r.json()

    print("LAYER NAME:", data.get("name"))
    print("TYPE:", data.get("type"))
    print("CRS:", data.get("extent", {}).get("spatialReference", {}).get("wkid"))
    print("GEOMETRY:", data.get("geometryType"))

    print("\nFIELDS:")

    for field in data.get("fields", []):
        print(
            "  ",
            field.get("name"),
            "|",
            field.get("type"),
            "|",
            field.get("alias")
        )

    print("\nMAX RECORD COUNT:", data.get("maxRecordCount"))
    print("CAPABILITIES:", data.get("capabilities"))