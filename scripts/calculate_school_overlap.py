
import os

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.features import geometry_mask

BASE = r"D:\Telangana_Rural_Project\Siddipet\Damarakunta"

REFERENCE_FILE = os.path.join(
    BASE, "reference", "school_compounds_utm44n.gpkg"
)

MASK_DIR = os.path.join(
    BASE, "predictions", "school_diagnostic_masks"
)

BUILDING_CLASS_ID = 2

refs = gpd.read_file(REFERENCE_FILE)

print("Reference CRS:", refs.crs)
print("Reference records:", len(refs))

pairs = [
    ("MPPS DAMARAKUNTA", "mpps_school_tile_mask.tif"),
    ("ZPHS DAMARAKUNTA", "zphs_school_tile_mask.tif"),
]

for school_name, mask_file in pairs:
    print("\n" + "=" * 50)
    print("SCHOOL:", school_name)

    matches = refs[refs["School_Name"] == school_name]

    if matches.empty:
        print("ERROR: School polygon not found.")
        print("Available school names:", refs["School_Name"].tolist())
        continue

    row = matches.iloc[0]
    mask_path = os.path.join(MASK_DIR, mask_file)

    if not os.path.exists(mask_path):
        print("ERROR: Prediction mask not found:", mask_path)
        continue

    with rasterio.open(mask_path) as src:
        prediction = src.read(1)

        compound_mask = geometry_mask(
            [row.geometry],
            transform=src.transform,
            out_shape=prediction.shape,
            invert=True
        )

        pixel_area_m2 = abs(
            src.transform.a * src.transform.e
            - src.transform.b * src.transform.d
        )

    reference_pixels = int(compound_mask.sum())
    building_pixels = int(
        ((prediction == BUILDING_CLASS_ID) & compound_mask).sum()
    )

    coverage = (
        building_pixels / reference_pixels * 100
        if reference_pixels else 0
    )

    print("Reference area (m2):", round(row.geometry.area, 2))
    print("Raster pixel area (m2):", round(pixel_area_m2, 4))
    print("Reference pixels:", reference_pixels)
    print("Pixels predicted as Building inside polygon:", building_pixels)
    print("Reference-polygon coverage by Building predictions:",
          f"{coverage:.2f}%")

print("\n" + "=" * 50)
print("OVERLAP VALIDATION COMPLETE")
print("Note: This is coverage, not accuracy or IoU.")
