import os
import requests
import numpy as np
from PIL import Image
from io import BytesIO
import matplotlib.pyplot as plt
import geopandas as gpd
from pyproj import Transformer


BOUNDARY = r"D:\Telangana_Rural_Project\Siddipet\Damarakunta\study_area\damarakunta_boundary.gpkg"

OUTPUT_DIR = r"D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\band_tests"

os.makedirs(OUTPUT_DIR, exist_ok=True)

SERVICE_URL = (
    "https://tgrac.telangana.gov.in/arcgis/rest/services/"
    "MusiRiver/Musi_Basin_Web_Publication_Raster/MapServer/export"
)

TGRAC_CRS = "EPSG:4326"


print("=" * 80)
print("DAMARAKUNTA BAND COMBINATION TEST")
print("=" * 80)


# Read vector boundary correctly
boundary = gpd.read_file(BOUNDARY)

print("\nBOUNDARY")
print("-" * 80)
print("CRS:", boundary.crs)
print("Records:", len(boundary))

bounds = boundary.total_bounds

print("Bounds in UTM:")
print(bounds)


# Transform boundary bounds to WGS84
transformer = Transformer.from_crs(
    boundary.crs,
    TGRAC_CRS,
    always_xy=True
)

xmin, ymin = transformer.transform(
    bounds[0],
    bounds[1]
)

xmax, ymax = transformer.transform(
    bounds[2],
    bounds[3]
)

bbox = f"{xmin},{ymin},{xmax},{ymax}"

print("\nTGRAC BBOX")
print("-" * 80)
print(bbox)


combinations = [
    (0, 1, 2),
    (0, 2, 1),
    (1, 0, 2),
    (1, 2, 0),
    (2, 0, 1),
    (2, 1, 0),
]


images = []


for combo in combinations:

    print("\nTesting bandIds =", combo)

    params = {
        "f": "image",
        "bbox": bbox,
        "bboxSR": 4326,
        "imageSR": 32644,
        "size": "600,600",
        "format": "png",
        "bandIds": ",".join(map(str, combo)),
        "interpolation": "RSP_BilinearInterpolation",
        "layers": "show:78"
    }

    response = requests.get(
        SERVICE_URL,
        params=params,
        timeout=120
    )

    print("HTTP:", response.status_code)
    print("Bytes:", len(response.content))

    if response.status_code != 200:
        print("FAILED")
        continue

    if not response.content.startswith(b"\x89PNG"):
        print("FAILED: response is not PNG")
        continue

    image = Image.open(
        BytesIO(response.content)
    ).convert("RGB")

    image_array = np.asarray(image)

    print("Image shape:", image_array.shape)

    images.append(
        (combo, image_array)
    )

    output_file = os.path.join(
        OUTPUT_DIR,
        f"bands_{combo[0]}_{combo[1]}_{combo[2]}.png"
    )

    image.save(output_file)

    print("Saved:", output_file)


if not images:
    raise SystemExit(
        "\n[ERROR] No band combinations were successfully exported."
    )


# Create comparison figure

fig, axes = plt.subplots(
    2,
    3,
    figsize=(15, 10)
)


for ax, (combo, image_array) in zip(
    axes.ravel(),
    images
):

    ax.imshow(image_array)

    ax.set_title(
        f"bandIds = {combo}"
    )

    ax.axis("off")


plt.tight_layout()


comparison_file = os.path.join(
    OUTPUT_DIR,
    "damarakunta_band_comparison.png"
)


plt.savefig(
    comparison_file,
    dpi=150,
    bbox_inches="tight"
)

plt.close()


print("\n" + "=" * 80)
print("COMPARISON CREATED")
print("=" * 80)

print("Output:")
print(comparison_file)

print("\nSTATUS: BAND COMBINATION TEST COMPLETED")