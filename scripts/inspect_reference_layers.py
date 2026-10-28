import requests

BASES = {
    "TGRAC_SCHOOLS": "https://tgrac.telangana.gov.in/arcgis/rest/services/SchoolGIS_Folder/Schools/MapServer",
    "TGRAC_HEALTH": "https://tgrac.telangana.gov.in/arcgis/rest/services/GovtHospitals_Folder/Health_Facilities_Query/MapServer",
    "TGRAC_ABADI": "https://tgrac.telangana.gov.in/arcgis/rest/services/Abadi_Folder/Abadi_Final/MapServer",
}

def inspect_service(name, url):
    print("\n" + "=" * 70)
    print(name)
    print(url)
    print("=" * 70)

    r = requests.get(url, params={"f": "json"}, timeout=60)
    print("STATUS:", r.status_code)

    if r.status_code != 200:
        print("ERROR:", r.text[:500])
        return

    data = r.json()

    print("NAME:", data.get("mapName") or data.get("name"))
    print("TYPE:", data.get("type"))
    print("CRS:", data.get("spatialReference", {}).get("wkid"))
    print("CAPABILITIES:", data.get("capabilities"))

    print("\nLAYERS:")
    for layer in data.get("layers", []):
        print(
            "  ID:", layer.get("id"),
            "| NAME:", layer.get("name")
        )

for name, url in BASES.items():
    inspect_service(name, url)