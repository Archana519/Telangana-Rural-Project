import os
import requests
import geopandas as gpd
import rasterio
from rasterio.mask import mask
import numpy as np
import planetary_computer

# ---------------------------------------------------------
# PATHS
# ---------------------------------------------------------

PROJECT = r"D:\Telangana_Rural_Project"

BOUNDARY = os.path.join(
    PROJECT,
    r"Siddipet\Damarakunta\study_area\damarakunta_boundary.gpkg"
)

OUT_DIR = os.path.join(
    PROJECT,
    r"Siddipet\Damarakunta\raw\imagery\sentinel2_20260429"
)

os.makedirs(OUT_DIR, exist_ok=True)

# ---------------------------------------------------------
# SENTINEL-2 SCENE
# ---------------------------------------------------------

SCENE_ID = (
    "S2A_MSIL2A_20260429T051241_R019_T43QHV_20260429T102710"
)

ITEM_URL = (
    "https://planetarycomputer.microsoft.com/api/stac/v1/"
    f"collections/sentinel-2-l2a/items/{SCENE_ID}"
)

# ---------------------------------------------------------
# LOAD STAC ITEM
# ---------------------------------------------------------

print("=" * 60)
print("DAMARAKUNTA SENTINEL-2 L2A DOWNLOAD")
print("=" * 60)

print("\nScene:")
print(SCENE_ID)

response = requests.get(
    ITEM_URL,
    timeout=60
)

response.raise_for_status()

item = response.json()

print("\nSTAC item: ACCESSIBLE")

print(
    "Cloud cover:",
    item["properties"].get("eo:cloud_cover")
)

# ---------------------------------------------------------
# LOAD BOUNDARY
# ---------------------------------------------------------

boundary = gpd.read_file(BOUNDARY)

print("\nBoundary CRS:", boundary.crs)
print("Boundary records:", len(boundary))

if boundary.empty:
    raise RuntimeError("Damarakunta boundary is empty.")

# ---------------------------------------------------------
# DOWNLOAD ONE BAND
# ---------------------------------------------------------

def download_band(band_name):

    asset = item["assets"][band_name]

    original_url = asset["href"]

    # Planetary Computer requires signed asset URLs
    signed_url = planetary_computer.sign(original_url)

    output = os.path.join(
        OUT_DIR,
        f"damarakunta_{band_name}.tif"
    )

    print("\n" + "-" * 60)
    print(f"Downloading {band_name}")
    print("Description:", asset.get("title"))
    print("Original URL available:", bool(original_url))
    print("Signed URL generated:", bool(signed_url))

    try:
        r = requests.get(
            signed_url,
            timeout=180
        )

        print("HTTP status:", r.status_code)

        r.raise_for_status()

    except requests.RequestException as e:
        print("\nDOWNLOAD FAILED")
        print("Band:", band_name)
        print("Error:", e)
        raise

    with open(output, "wb") as f:
        f.write(r.content)

    print("Saved:", output)
    print(
        "Size:",
        round(len(r.content) / (1024 * 1024), 2),
        "MB"
    )

    return output


# ---------------------------------------------------------
# DOWNLOAD B02 / B03 / B04
# ---------------------------------------------------------

b02_file = download_band("B02")
b03_file = download_band("B03")
b04_file = download_band("B04")

# ---------------------------------------------------------
# CLIP EACH BAND TO VILLAGE BOUNDARY
# ---------------------------------------------------------

def clip_band(input_file, output_file):

    print("\n" + "-" * 60)
    print("Clipping:")
    print(input_file)

    with rasterio.open(input_file) as src:

        print("Source CRS:", src.crs)
        print("Source resolution:", src.res)
        print("Source dtype:", src.dtypes)

        boundary_src = boundary.to_crs(src.crs)

        clipped, transform = mask(
            src,
            boundary_src.geometry,
            crop=True,
            nodata=0
        )

        profile = src.profile.copy()

        profile.update(
            height=clipped.shape[1],
            width=clipped.shape[2],
            transform=transform,
            count=1,
            compress="deflate",
            predictor=2
        )

        with rasterio.open(
            output_file,
            "w",
            **profile
        ) as dst:

            dst.write(
                clipped[0],
                1
            )

    print("Saved:", output_file)


# ---------------------------------------------------------
# CLIPPED BAND OUTPUTS
# ---------------------------------------------------------

b02_clip = os.path.join(
    OUT_DIR,
    "damarakunta_B02_clipped_10m.tif"
)

b03_clip = os.path.join(
    OUT_DIR,
    "damarakunta_B03_clipped_10m.tif"
)

b04_clip = os.path.join(
    OUT_DIR,
    "damarakunta_B04_clipped_10m.tif"
)

clip_band(
    b02_file,
    b02_clip
)

clip_band(
    b03_file,
    b03_clip
)

clip_band(
    b04_file,
    b04_clip
)

# ---------------------------------------------------------
# CREATE RGB
#
# RED   = B04
# GREEN = B03
# BLUE  = B02
# ---------------------------------------------------------

print("\n" + "=" * 60)
print("CREATING SENTINEL-2 TRUE-COLOR RGB")
print("=" * 60)

print("Red   = B04")
print("Green = B03")
print("Blue  = B02")

with rasterio.open(b04_clip) as red_src, \
     rasterio.open(b03_clip) as green_src, \
     rasterio.open(b02_clip) as blue_src:

    red = red_src.read(1)
    green = green_src.read(1)
    blue = blue_src.read(1)

    # -----------------------------------------------------
    # VERIFY DIMENSIONS
    # -----------------------------------------------------

    if not (
        red.shape == green.shape == blue.shape
    ):
        raise RuntimeError(
            "B02/B03/B04 dimensions do not match."
        )

    # -----------------------------------------------------
    # CREATE RGB PROFILE
    # -----------------------------------------------------

    profile = red_src.profile.copy()

    profile.update(
        count=3,
        dtype="uint16",
        compress="deflate",
        predictor=2
    )

    rgb_file = os.path.join(
        OUT_DIR,
        "damarakunta_sentinel2_RGB_B04_B03_B02_10m.tif"
    )

    # -----------------------------------------------------
    # WRITE RGB
    # -----------------------------------------------------

    with rasterio.open(
        rgb_file,
        "w",
        **profile
    ) as dst:

        dst.write(
            red.astype(np.uint16),
            1
        )

        dst.write(
            green.astype(np.uint16),
            2
        )

        dst.write(
            blue.astype(np.uint16),
            3
        )

        # Band descriptions
        dst.set_band_description(
            1,
            "B04 Red 10m"
        )

        dst.set_band_description(
            2,
            "B03 Green 10m"
        )

        dst.set_band_description(
            3,
            "B02 Blue 10m"
        )

        # Dataset metadata
        dst.update_tags(
            source="Copernicus Sentinel-2 L2A",
            scene_id=SCENE_ID,
            acquisition_date="2026-04-29",
            cloud_cover="0.000516",
            processing="B04-B03-B02 RGB",
            spatial_resolution="10m"
        )

print("\nRGB file created:")
print(rgb_file)

# ---------------------------------------------------------
# FINAL INSPECTION
# ---------------------------------------------------------

print("\n" + "=" * 60)
print("FINAL RGB INSPECTION")
print("=" * 60)

with rasterio.open(rgb_file) as src:

    print("Width:", src.width)
    print("Height:", src.height)
    print("Bands:", src.count)
    print("CRS:", src.crs)
    print("Resolution:", src.res)
    print("Dtype:", src.dtypes)
    print("Bounds:", src.bounds)
    print("Descriptions:", src.descriptions)

    # -----------------------------------------------------
    # CHECK PIXEL VALUES
    # -----------------------------------------------------

    for i in range(1, src.count + 1):

        data = src.read(i)

        print(
            f"Band {i}: "
            f"min={data.min()} "
            f"max={data.max()} "
            f"mean={data.mean():.2f}"
        )

# ---------------------------------------------------------
# FINAL STATUS
# ---------------------------------------------------------

print("\n" + "=" * 60)
print("STATUS: SENTINEL-2 RGB READY")
print("=" * 60)