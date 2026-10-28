import requests
import geopandas as gpd
from pyproj import Transformer

BOUNDARY = (
    r"D:\Telangana_Rural_Project\Siddipet\Damarakunta"
    r"\study_area\damarakunta_boundary.gpkg"
)

EXPORT_URL = (
    "https://tgrac.telangana.gov.in/arcgis/rest/services/"
    "MusiRiver/Musi_Basin_Web_Publication_Raster/MapServer/export"
)

LAYER_URL = (
    "https://tgrac.telangana.gov.in/arcgis/rest/services/"
    "MusiRiver/Musi_Basin_Web_Publication_Raster/MapServer/78"
)


# ============================================================
# READ VERIFIED DAMARAKUNTA BOUNDARY
# ============================================================

gdf = gpd.read_file(
    BOUNDARY,
    layer="village_boundary"
)

minx, miny, maxx, maxy = gdf.total_bounds


# ============================================================
# GET TGRAC SENTINEL CRS
# ============================================================

layer_response = requests.get(
    LAYER_URL,
    params={"f": "json"},
    timeout=30
)

layer_response.raise_for_status()

layer_info = layer_response.json()

target_wkt = (
    layer_info["extent"]
    ["spatialReference"]
    ["wkt"]
)


# ============================================================
# TRANSFORM DAMARAKUNTA BOUNDARY
# FROM EPSG:32644 TO TGRAC SENTINEL CRS
# ============================================================

transformer = Transformer.from_crs(
    "EPSG:32644",
    target_wkt,
    always_xy=True
)

corners = [
    (minx, miny),
    (minx, maxy),
    (maxx, miny),
    (maxx, maxy)
]

transformed = [
    transformer.transform(x, y)
    for x, y in corners
]

xs = [
    point[0]
    for point in transformed
]

ys = [
    point[1]
    for point in transformed
]

bbox = (
    f"{min(xs)},{min(ys)},"
    f"{max(xs)},{max(ys)}"
)


# ============================================================
# EXPORT PARAMETERS
# ============================================================

params = {
    "bbox": bbox,
    "bboxSR": target_wkt,
    "imageSR": "32644",
    "size": "500,500",
    "imageFormat": "png",
    "transparent": "false",
    "layers": "show:78",
    "f": "image"
}


# ============================================================
# RUN TEST
# ============================================================

print("=" * 80)
print("DAMARAKUNTA SENTINEL EXPORT TEST")
print("=" * 80)

print("\nDamarakunta UTM bounds:")
print(
    minx,
    miny,
    maxx,
    maxy
)

print("\nTransformed Sentinel bounds:")
print(bbox)


response = requests.get(
    EXPORT_URL,
    params=params,
    timeout=60
)


# ============================================================
# RESPONSE CHECK
# ============================================================

content_type = response.headers.get(
    "Content-Type",
    ""
).lower()

is_png = response.content.startswith(
    b"\x89PNG\r\n\x1a\n"
)


print("\nHTTP status:")
print(response.status_code)

print("\nContent-Type:")
print(
    content_type
    if content_type
    else "(not provided by server)"
)

print("\nResponse size:")
print(
    len(response.content),
    "bytes"
)

print("\nPNG signature detected:")
print(is_png)


# ============================================================
# FINAL RESULT
# ============================================================

if (
    response.status_code == 200
    and is_png
):

    print("\n" + "=" * 80)

    print(
        "STATUS: SENTINEL RASTER EXPORT TEST SUCCESSFUL."
    )

    print(
        "The TGRAC Sentinel layer returned "
        "a valid PNG image."
    )

    print(
        "Damarakunta-area imagery export is available."
    )

    print("=" * 80)

else:

    print("\n" + "=" * 80)

    print(
        "STATUS: SENTINEL RASTER EXPORT TEST FAILED."
    )

    print(
        "The response was not recognized as a valid PNG."
    )

    print(
        "\nFirst response bytes:"
    )

    print(
        response.content[:100]
    )

    print("=" * 80)