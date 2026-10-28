import requests

URL = (
    "https://tgrac.telangana.gov.in/arcgis/rest/services/"
    "LIS_Folder/LandInformationSystem_Query/MapServer/0/query"
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

try:
    data = r.json()
except Exception:
    print("Server response:")
    print(r.text[:2000])
    raise SystemExit

if "error" in data:
    print("ERROR:")
    print(data["error"])
    raise SystemExit

features = data.get("features", [])

print("Cadastral records returned:", len(features))

if not features:
    print("No cadastral records returned for Damarakunta.")
    raise SystemExit

print("\nFirst 5 records:")

for i, feature in enumerate(features[:5], 1):
    print("\nRecord", i)
    print(feature.get("attributes"))

print("\nGeometry available:",
      features[0].get("geometry") is not None)

print("\nDONE")