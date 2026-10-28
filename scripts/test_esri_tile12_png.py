import requests
from pathlib import Path

xmin = 264214.8855999997
ymin = 1960209.3078000005
xmax = 264914.8855999997
ymax = 1960909.3078000005

width = 1200
height = 1200

url = (
    "https://services.arcgisonline.com/"
    "ArcGIS/rest/services/World_Imagery/MapServer/export"
)

params = {
    "bbox": f"{xmin},{ymin},{xmax},{ymax}",
    "bboxSR": "32644",
    "imageSR": "32644",
    "size": f"{width},{height}",
    "format": "png",
    "transparent": "false",
    "f": "image",
}

print("=" * 60)
print("DAMARAKUNTA TILE 12 PNG TEST")
print("=" * 60)

print("BBOX:", params["bbox"])
print("SIZE:", params["size"])
print("FORMAT:", params["format"])

response = requests.get(
    url,
    params=params,
    timeout=180
)

print()
print("HTTP status:", response.status_code)
print("Returned bytes:", len(response.content))
print("Content-Type:", response.headers.get("Content-Type"))

output = Path(
    "Siddipet/Damarakunta/results/"
    "tile12_png_test.png"
)

output.parent.mkdir(
    parents=True,
    exist_ok=True
)

if response.status_code == 200:
    output.write_bytes(response.content)

    print()
    print("SUCCESS")
    print("Saved:")
    print(output)

else:
    print()
    print("FAILED")
    print(response.text[:1000])