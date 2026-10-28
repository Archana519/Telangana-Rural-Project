import requests
from pathlib import Path

# Damarakunta boundary bounding box in EPSG:32644
xmin = 258814.8856
ymin = 1956609.3078
xmax = 265592.3488
ymax = 1960912.0880

# Approximate center
cx = (xmin + xmax) / 2
cy = (ymin + ymax) / 2

print("Damarakunta center:")
print("UTM 44N:", cx, cy)

# World Imagery service
url = "https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer"

# Identify request around the center
params = {
    "f": "json",
    "geometry": f"{cx},{cy}",
    "geometryType": "esriGeometryPoint",
    "sr": "32644",
    "layers": "all",
    "tolerance": 5,
    "mapExtent": f"{xmin},{ymin},{xmax},{ymax}",
    "imageDisplay": "1000,1000,96",
    "returnGeometry": "false"
}

print("\nChecking Esri World Imagery coverage...")
r = requests.get(url + "/identify", params=params, timeout=60)

print("HTTP status:", r.status_code)

if r.status_code != 200:
    print("ERROR: Esri service request failed.")
    print(r.text[:1000])
    raise SystemExit(1)

data = r.json()

print("\nIdentify response:")
print(data)

# Save response
out = Path("Siddipet/Damarakunta/results/esri_world_imagery_identify.json")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(r.text, encoding="utf-8")

print("\nSaved:")
print(out)