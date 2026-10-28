from pathlib import Path
import csv

import cv2
import numpy as np
import geopandas as gpd
import rasterio
from rasterio.features import shapes
from shapely.geometry import shape
from skimage.morphology import skeletonize


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(r"D:\Telangana_Rural_Project")

PREDICTION = (
    PROJECT_ROOT
    / "Siddipet"
    / "Angadi_Kistapur"
    / "predictions"
    / "angadi_kistapur_segmentation.tif"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "Siddipet"
    / "Angadi_Kistapur"
    / "derived"
)

BUILDING_GPKG = OUTPUT_DIR / "buildings.gpkg"
ROAD_GPKG = OUTPUT_DIR / "roads.gpkg"
ROAD_SKELETON_GPKG = OUTPUT_DIR / "road_skeleton.gpkg"

BUILDING_CSV = OUTPUT_DIR / "buildings.csv"
ROAD_CSV = OUTPUT_DIR / "roads.csv"

BUILDING_PREVIEW = OUTPUT_DIR / "building_mask.png"
ROAD_PREVIEW = OUTPUT_DIR / "road_mask.png"
SKELETON_PREVIEW = OUTPUT_DIR / "road_skeleton.png"


# ============================================================
# MODEL CLASS IDs
# ============================================================

BUILDING_CLASS = 1
ROAD_CLASS = 2


# ============================================================
# BUILDING EXTRACTION SETTINGS
# ============================================================

# Remove extremely small components.
# At approximately 2.03 m/pixel, 20 pixels is roughly 82 m².
MIN_BUILDING_PIXELS = 20


# ============================================================
# ROAD EXTRACTION SETTINGS
# ============================================================

# Morphological cleanup
ROAD_KERNEL_SIZE = 3

# Remove tiny road components.
MIN_ROAD_PIXELS = 20


# ============================================================
# UTILITY
# ============================================================

def save_binary_preview(mask, path):
    """
    Save a binary mask as a simple PNG for visual verification.
    """
    preview = (mask.astype(np.uint8) * 255)

    cv2.imwrite(
        str(path),
        preview
    )


# ============================================================
# BUILDING EXTRACTION
# ============================================================

def extract_buildings(prediction, transform, crs):

    print()
    print("=" * 70)
    print("BUILDING EXTRACTION")
    print("=" * 70)

    building_mask = (
        prediction == BUILDING_CLASS
    ).astype(np.uint8)

    print(
        "Raw building pixels:",
        int(building_mask.sum())
    )

    # Connected components
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
        building_mask,
        connectivity=8
    )

    building_records = []

    kept_mask = np.zeros_like(building_mask)

    building_id = 0

    for label_id in range(1, num_labels):

        area_pixels = int(
            stats[label_id, cv2.CC_STAT_AREA]
        )

        if area_pixels < MIN_BUILDING_PIXELS:
            continue

        component = (
            labels == label_id
        ).astype(np.uint8)

        # Convert raster component to polygon
        component_shapes = shapes(
            component,
            mask=component.astype(bool),
            transform=transform
        )

        polygons = []

        for geom, value in component_shapes:

            if value != 1:
                continue

            polygons.append(
                shape(geom)
            )

        if not polygons:
            continue

        polygon = polygons[0]

        if polygon.is_empty:
            continue

        if not polygon.is_valid:
            polygon = polygon.buffer(0)

        if polygon.is_empty:
            continue

        building_id += 1

        kept_mask[labels == label_id] = 1

        min_x = int(
            stats[label_id, cv2.CC_STAT_LEFT]
        )

        min_y = int(
            stats[label_id, cv2.CC_STAT_TOP]
        )

        width = int(
            stats[label_id, cv2.CC_STAT_WIDTH]
        )

        height = int(
            stats[label_id, cv2.CC_STAT_HEIGHT]
        )

        centroid_x, centroid_y = centroids[label_id]

        # Convert pixel centroid to UTM coordinates
        center_x, center_y = rasterio.transform.xy(
            transform,
            centroid_y,
            centroid_x,
            offset="center"
        )

        area_m2 = float(polygon.area)

        building_records.append(
            {
                "building_id": building_id,
                "pixel_area": area_pixels,
                "area_m2": area_m2,
                "bbox_width_px": width,
                "bbox_height_px": height,
                "centroid_x": float(center_x),
                "centroid_y": float(center_y),
                "geometry": polygon
            }
        )

    print(
        "Connected components:",
        num_labels - 1
    )

    print(
        "Buildings retained:",
        len(building_records)
    )

    print(
        "Minimum component:",
        MIN_BUILDING_PIXELS,
        "pixels"
    )

    return building_records, kept_mask


# ============================================================
# ROAD EXTRACTION
# ============================================================

def extract_roads(prediction, transform, crs):

    print()
    print("=" * 70)
    print("ROAD EXTRACTION")
    print("=" * 70)

    road_mask = (
        prediction == ROAD_CLASS
    ).astype(np.uint8)

    print(
        "Raw road pixels:",
        int(road_mask.sum())
    )

    # --------------------------------------------------------
    # Morphological cleanup
    # --------------------------------------------------------

    kernel = np.ones(
        (ROAD_KERNEL_SIZE, ROAD_KERNEL_SIZE),
        dtype=np.uint8
    )

    road_clean = cv2.morphologyEx(
        road_mask,
        cv2.MORPH_CLOSE,
        kernel
    )

    # Remove tiny disconnected components
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
        road_clean,
        connectivity=8
    )

    kept_mask = np.zeros_like(road_clean)

    road_records = []

    road_id = 0

    for label_id in range(1, num_labels):

        area_pixels = int(
            stats[label_id, cv2.CC_STAT_AREA]
        )

        if area_pixels < MIN_ROAD_PIXELS:
            continue

        component = (
            labels == label_id
        ).astype(np.uint8)

        component_shapes = shapes(
            component,
            mask=component.astype(bool),
            transform=transform
        )

        polygons = []

        for geom, value in component_shapes:

            if value != 1:
                continue

            polygons.append(
                shape(geom)
            )

        if not polygons:
            continue

        polygon = polygons[0]

        if polygon.is_empty:
            continue

        if not polygon.is_valid:
            polygon = polygon.buffer(0)

        if polygon.is_empty:
            continue

        road_id += 1

        kept_mask[labels == label_id] = 1

        centroid_x, centroid_y = centroids[label_id]

        center_x, center_y = rasterio.transform.xy(
            transform,
            centroid_y,
            centroid_x,
            offset="center"
        )

        road_records.append(
            {
                "road_id": road_id,
                "pixel_area": area_pixels,
                "area_m2": float(polygon.area),
                "centroid_x": float(center_x),
                "centroid_y": float(center_y),
                "geometry": polygon
            }
        )

    print(
        "Connected road components:",
        num_labels - 1
    )

    print(
        "Road components retained:",
        len(road_records)
    )

    return road_records, kept_mask


# ============================================================
# ROAD SKELETON
# ============================================================

def create_road_skeleton(road_mask, transform, crs):

    print()
    print("=" * 70)
    print("ROAD SKELETONIZATION")
    print("=" * 70)

    skeleton = skeletonize(
        road_mask.astype(bool)
    )

    skeleton = skeleton.astype(np.uint8)

    skeleton_pixels = int(
        skeleton.sum()
    )

    print(
        "Skeleton pixels:",
        skeleton_pixels
    )

    # Convert skeleton pixels to points.
    rows, cols = np.where(
        skeleton == 1
    )

    points = []

    for row, col in zip(rows, cols):

        x, y = rasterio.transform.xy(
            transform,
            int(row),
            int(col),
            offset="center"
        )

        points.append(
            {
                "row": int(row),
                "col": int(col),
                "x": float(x),
                "y": float(y),
                "geometry": shape(
                    {
                        "type": "Point",
                        "coordinates": (x, y)
                    }
                )
            }
        )

    print(
        "Skeleton points:",
        len(points)
    )

    return points, skeleton


# ============================================================
# SAVE BUILDINGS
# ============================================================

def save_buildings(records, crs):

    if not records:
        print("WARNING: No buildings to save.")
        return

    gdf = gpd.GeoDataFrame(
        records,
        geometry="geometry",
        crs=crs
    )

    gdf.to_file(
        BUILDING_GPKG,
        layer="buildings",
        driver="GPKG"
    )

    with open(
        BUILDING_CSV,
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        fieldnames = [
            "building_id",
            "pixel_area",
            "area_m2",
            "bbox_width_px",
            "bbox_height_px",
            "centroid_x",
            "centroid_y"
        ]

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames
        )

        writer.writeheader()

        for record in records:

            writer.writerow(
                {
                    key: record[key]
                    for key in fieldnames
                }
            )

    print()
    print("Buildings GeoPackage:")
    print(BUILDING_GPKG)

    print("Buildings CSV:")
    print(BUILDING_CSV)


# ============================================================
# SAVE ROADS
# ============================================================

def save_roads(records, crs):

    if not records:
        print("WARNING: No roads to save.")
        return

    gdf = gpd.GeoDataFrame(
        records,
        geometry="geometry",
        crs=crs
    )

    gdf.to_file(
        ROAD_GPKG,
        layer="roads",
        driver="GPKG"
    )

    with open(
        ROAD_CSV,
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        fieldnames = [
            "road_id",
            "pixel_area",
            "area_m2",
            "centroid_x",
            "centroid_y"
        ]

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames
        )

        writer.writeheader()

        for record in records:

            writer.writerow(
                {
                    key: record[key]
                    for key in fieldnames
                }
            )

    print()
    print("Road GeoPackage:")
    print(ROAD_GPKG)

    print("Road CSV:")
    print(ROAD_CSV)


# ============================================================
# SAVE SKELETON
# ============================================================

def save_skeleton(points, crs):

    if not points:
        print("WARNING: No skeleton points to save.")
        return

    gdf = gpd.GeoDataFrame(
        points,
        geometry="geometry",
        crs=crs
    )

    gdf.to_file(
        ROAD_SKELETON_GPKG,
        layer="road_skeleton",
        driver="GPKG"
    )

    print()
    print("Road skeleton:")
    print(ROAD_SKELETON_GPKG)


# ============================================================
# MAIN
# ============================================================

def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    if not PREDICTION.exists():

        raise FileNotFoundError(
            f"Prediction not found:\n{PREDICTION}"
        )

    print("=" * 70)
    print("PHASE 13 - BUILDING / ROAD EXTRACTION")
    print("=" * 70)

    print("Prediction:")
    print(PREDICTION)

    print()

    # --------------------------------------------------------
    # Read prediction
    # --------------------------------------------------------

    with rasterio.open(PREDICTION) as src:

        prediction = src.read(1)

        transform = src.transform

        crs = src.crs

        width = src.width
        height = src.height

        resolution_x = src.res[0]
        resolution_y = abs(src.res[1])

    print("Raster size:")
    print("  Width :", width)
    print("  Height:", height)

    print("CRS:", crs)

    print(
        "Resolution:",
        resolution_x,
        "x",
        resolution_y,
        "metres/pixel"
    )

    print()

    # --------------------------------------------------------
    # Extract buildings
    # --------------------------------------------------------

    building_records, building_mask = extract_buildings(
        prediction,
        transform,
        crs
    )

    # --------------------------------------------------------
    # Extract roads
    # --------------------------------------------------------

    road_records, road_mask = extract_roads(
        prediction,
        transform,
        crs
    )

    # --------------------------------------------------------
    # Skeleton
    # --------------------------------------------------------

    skeleton_points, skeleton_mask = create_road_skeleton(
        road_mask,
        transform,
        crs
    )

    # --------------------------------------------------------
    # Save previews
    # --------------------------------------------------------

    save_binary_preview(
        building_mask,
        BUILDING_PREVIEW
    )

    save_binary_preview(
        road_mask,
        ROAD_PREVIEW
    )

    save_binary_preview(
        skeleton_mask,
        SKELETON_PREVIEW
    )

    # --------------------------------------------------------
    # Save GIS data
    # --------------------------------------------------------

    save_buildings(
        building_records,
        crs
    )

    save_roads(
        road_records,
        crs
    )

    save_skeleton(
        skeleton_points,
        crs
    )

    # --------------------------------------------------------
    # Final summary
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("PHASE 13 EXTRACTION COMPLETED")
    print("=" * 70)

    print(
        "Buildings extracted:",
        len(building_records)
    )

    print(
        "Road components:",
        len(road_records)
    )

    print(
        "Road skeleton points:",
        len(skeleton_points)
    )

    print()
    print("Output directory:")
    print(OUTPUT_DIR)

    print()
    print("IMPORTANT:")
    print(
        "These are AI-derived buildings and roads. "
        "They are not treated as ground truth."
    )


if __name__ == "__main__":
    main()