
from pathlib import Path
import sys
import warnings

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio

from rasterio.enums import Resampling
from rasterio.windows import from_bounds, Window
from shapely.geometry import box

warnings.filterwarnings("ignore", category=UserWarning)


# ============================================================
# DAMARAKUNTA V5
# BUILDING + HOUSE + ROAD CONNECTIVITY REVIEW
#
# Existing V4 route data is READ-ONLY.
#
# Important:
# This script visualizes existing building footprints.
# It does not train a model or automatically detect houses
# from satellite pixels when no building layer is available.
#
# Connectivity is a preliminary nearest-road assessment,
# NOT proof of a usable physical road connection.
# ============================================================

BASE = Path(
    r"D:\Telangana_Rural_Project\Siddipet\Damarakunta"
)

RESULTS = BASE / "results"
IMAGE = BASE / "aligned" / "damarakunta_esri_highres_mosaic_0p6m.tif"
BOUNDARY = BASE / "study_area" / "damarakunta_boundary.gpkg"
ROADS = BASE / "reference" / "tgrac_road_network.gpkg"
ROUTES = RESULTS / "damarakunta_routes_v4.gpkg"
FACILITIES = BASE / "reference" / "damarakunta_priority_facilities.gpkg"

# Optional: enter the exact path of your building-footprint file.
# Example:
# BUILDINGS_SOURCE = BASE / "reference" / "village_buildings.gpkg"
#
# Leave as None to search for an existing building layer.
BUILDINGS_SOURCE = None

# Optional: set a layer name for a multi-layer GeoPackage.
# Leave as None to use the first suitable layer.
BUILDINGS_LAYER = None

OUT = RESULTS / "v5_building_review"
OUT.mkdir(parents=True, exist_ok=True)

OVERVIEW_PNG = OUT / "damarakunta_v5_all_buildings.png"
OVERVIEW_PDF = OUT / "damarakunta_v5_all_buildings.pdf"
INVENTORY_CSV = OUT / "damarakunta_v5_building_inventory.csv"
DETAIL_DIR = OUT / "building_details"
DETAIL_DIR.mkdir(parents=True, exist_ok=True)

MAX_OVERVIEW_DIMENSION = 5000
MAX_DETAIL_DIMENSION = 2400
DETAIL_DPI = 180

# Maximum number of individual close-up images to create.
# The inventory and overview still include all loaded buildings.
MAX_DETAIL_MAPS = 500

# Preliminary screening threshold, in metres.
# This is NOT a validated road-access standard.
NEAR_ROAD_THRESHOLD_M = 20.0

ROUTE_COLORS = {
    1: "#ff3028",
    2: "#00cfe8",
    3: "#ffe600",
}


# ============================================================
# GENERAL HELPERS
# ============================================================

def require_file(path):
    if not path.exists():
        raise FileNotFoundError(
            f"Required file not found: {path}"
        )


def read_layer(path, layer=None):
    if layer:
        return gpd.read_file(path, layer=layer)
    return gpd.read_file(path)


def clean_gdf(gdf, label):
    if gdf is None or gdf.empty:
        print(f"WARNING: {label} is empty.")
        return gdf

    if gdf.crs is None:
        raise ValueError(
            f"{label} has no CRS. Assign the correct CRS "
            "before using this layer."
        )

    gdf = gdf[
        gdf.geometry.notna()
        & ~gdf.geometry.is_empty
    ].copy()

    return gdf


def reproject(gdf, target_crs, label):
    if gdf is None or gdf.empty:
        return gdf

    gdf = clean_gdf(gdf, label)

    if gdf.crs != target_crs:
        gdf = gdf.to_crs(target_crs)

    return gdf


def choose_column(gdf, candidates):
    if gdf is None:
        return None

    lower = {
        str(c).lower(): c
        for c in gdf.columns
    }

    for candidate in candidates:
        if candidate.lower() in lower:
            return lower[candidate.lower()]

    return None


def valid_geometries(gdf):
    if gdf is None or gdf.empty:
        return gdf

    return gdf[
        gdf.geometry.notna()
        & ~gdf.geometry.is_empty
    ].copy()


def safe_csv(df, path):
    candidates = [
        path,
        path.with_name(path.stem + "_new.csv")
    ]

    for candidate in candidates:
        try:
            df.to_csv(candidate, index=False)
            print(f"CSV saved: {candidate}")
            return candidate
        except PermissionError:
            print(
                f"Cannot overwrite {candidate}. "
                "Close the CSV if it is open in Excel."
            )

    raise RuntimeError(
        "Could not save CSV. Close applications using it."
    )


# ============================================================
# SATELLITE IMAGE
# ============================================================

def read_rgb(window=None, max_dimension=5000):
    """
    Read RGB pixels directly from the original GeoTIFF.
    Returns image and the correct map extent.
    """

    with rasterio.open(IMAGE) as src:
        if src.count < 3:
            raise ValueError(
                "The raster needs at least 3 RGB bands."
            )

        if window is None:
            window = Window(
                0, 0, src.width, src.height
            )

        window = window.intersection(
            Window(0, 0, src.width, src.height)
        )

        if window.width <= 0 or window.height <= 0:
            raise ValueError("Invalid raster crop.")

        scale = min(
            1.0,
            max_dimension / max(
                window.width, window.height
            )
        )

        height = max(
            1, int(round(window.height * scale))
        )
        width = max(
            1, int(round(window.width * scale))
        )

        arr = src.read(
            indexes=[1, 2, 3],
            window=window,
            out_shape=(3, height, width),
            resampling=Resampling.bilinear
        )

        left, bottom, right, top = (
            rasterio.windows.bounds(
                window, src.transform
            )
        )

    arr = np.moveaxis(arr, 0, -1)

    # Scale non-8-bit imagery for display if necessary.
    if arr.dtype != np.uint8:
        display = np.zeros(
            arr.shape, dtype=np.uint8
        )

        for band in range(3):
            channel = arr[:, :, band].astype(float)
            finite = np.isfinite(channel)

            if not finite.any():
                continue

            low, high = np.percentile(
                channel[finite], [2, 98]
            )

            if high <= low:
                high = low + 1

            scaled = (
                (channel - low)
                / (high - low)
                * 255
            )

            display[:, :, band] = np.clip(
                np.nan_to_num(scaled),
                0, 255
            ).astype(np.uint8)

        arr = display
    else:
        arr = np.clip(arr, 0, 255).astype(np.uint8)

    extent = [left, right, bottom, top]
    return arr, extent


def read_rgb_bounds(bounds, max_dimension=2400):
    with rasterio.open(IMAGE) as src:
        clipped = (
            max(bounds[0], src.bounds.left),
            max(bounds[1], src.bounds.bottom),
            min(bounds[2], src.bounds.right),
            min(bounds[3], src.bounds.top),
        )

        if (
            clipped[0] >= clipped[2]
            or clipped[1] >= clipped[3]
        ):
            raise ValueError(
                "Building crop falls outside the raster."
            )

        window = from_bounds(
            *clipped,
            transform=src.transform
        ).round_offsets().round_lengths()

        window = window.intersection(
            Window(0, 0, src.width, src.height)
        )

    return read_rgb(
        window=window,
        max_dimension=max_dimension
    )


# ============================================================
# FIND AN EXISTING BUILDING FOOTPRINT LAYER
# ============================================================

def discover_buildings():
    """
    Search GIS files for layers whose filenames or attributes
    indicate building footprints.

    The user can bypass discovery by setting BUILDINGS_SOURCE.
    """

    if BUILDINGS_SOURCE is not None:
        path = Path(BUILDINGS_SOURCE)

        if not path.exists():
            raise FileNotFoundError(
                f"Configured building layer not found: {path}"
            )

        layer = BUILDINGS_LAYER
        print(f"Using configured building source: {path}")

        gdf = read_layer(path, layer)
        return gdf, path, layer

    try:
        import fiona
    except ImportError:
        fiona = None

    extensions = {".gpkg", ".shp", ".geojson", ".json"}
    excluded = {
        "damarakunta_routes_v4.gpkg",
        "tgrac_road_network.gpkg",
        "damarakunta_boundary.gpkg",
        "damarakunta_priority_facilities.gpkg",
    }

    candidates = []

    for path in BASE.rglob("*"):
        if not path.is_file():
            continue

        if path.suffix.lower() not in extensions:
            continue

        if path.name.lower() in excluded:
            continue

        if OUT in path.parents:
            continue

        filename = path.stem.lower()

        name_score = 0
        for word, score in [
            ("building", 10),
            ("footprint", 12),
            ("house", 10),
            ("structure", 7),
            ("residential", 8),
        ]:
            if word in filename:
                name_score = max(name_score, score)

        if name_score == 0:
            continue

        layers = [None]

        if path.suffix.lower() == ".gpkg" and fiona:
            try:
                layers = list(fiona.listlayers(path))
            except Exception:
                layers = [None]

        for layer in layers:
            try:
                gdf = read_layer(path, layer)

                if gdf.empty or gdf.crs is None:
                    continue

                polygons = gdf.geometry.geom_type.isin(
                    ["Polygon", "MultiPolygon"]
                )

                polygon_fraction = (
                    float(polygons.mean())
                    if len(gdf)
                    else 0
                )

                if polygon_fraction < 0.5:
                    continue

                attribute_text = " ".join(
                    str(c).lower()
                    for c in gdf.columns
                )

                attribute_score = 0
                if "building" in attribute_text:
                    attribute_score += 3
                if "house" in attribute_text:
                    attribute_score += 3
                if "residential" in attribute_text:
                    attribute_score += 3

                score = name_score + attribute_score

                candidates.append(
                    (
                        score,
                        len(gdf),
                        path,
                        layer,
                        gdf
                    )
                )

            except Exception as exc:
                print(
                    f"Skipping candidate {path}: {exc}"
                )

    if not candidates:
        return None, None, None

    candidates.sort(
        key=lambda item: (item[0], item[1]),
        reverse=True
    )

    score, count, path, layer, gdf = candidates[0]

    print("\nBuilding layer candidates found:")
    for item in candidates:
        print(
            f"  {item[2]} | layer={item[3]} "
            f"| features={item[1]} | score={item[0]}"
        )

    print("\nSelected building source:")
    print(f"  File: {path}")
    print(f"  Layer: {layer}")
    print(f"  Features: {count}")

    print(
        "IMPORTANT: Confirm that the selected layer contains "
        "individual building footprints, not building points "
        "or unrelated polygons."
    )

    return gdf, path, layer


# ============================================================
# DRAWING HELPERS
# ============================================================

def draw_roads(ax, roads):
    if roads is None or roads.empty:
        return

    roads.plot(
        ax=ax,
        color="white",
        linewidth=2.0,
        alpha=0.9,
        zorder=3
    )

    roads.plot(
        ax=ax,
        color="#303030",
        linewidth=0.7,
        zorder=4
    )


def draw_boundary(ax, boundary):
    if boundary is not None and not boundary.empty:
        boundary.boundary.plot(
            ax=ax,
            color="#00FFFF",
            linewidth=1.8,
            zorder=8
        )


def draw_buildings(ax, buildings, id_col):
    if buildings is None or buildings.empty:
        return

    # Transparent fill allows the actual roof imagery to remain
    # visible. A thin outline marks each detected footprint.
    buildings.plot(
        ax=ax,
        facecolor="#ff5c36",
        edgecolor="#fff200",
        alpha=0.22,
        linewidth=0.65,
        zorder=5
    )

    if id_col:
        for _, row in buildings.iterrows():
            geom = row.geometry

            if geom is None or geom.is_empty:
                continue

            point = geom.representative_point()

            ax.annotate(
                str(row[id_col]),
                (point.x, point.y),
                fontsize=5,
                color="white",
                ha="center",
                va="center",
                bbox={
                    "facecolor": "black",
                    "alpha": 0.65,
                    "pad": 0.5
                },
                zorder=7
            )


def draw_facilities(ax, facilities, name_col):
    if facilities is None or facilities.empty:
        return

    points = facilities.copy()

    # If a facility is stored as a polygon, use its interior point.
    non_points = ~points.geometry.geom_type.isin(
        ["Point", "MultiPoint"]
    )

    if non_points.any():
        points.loc[non_points, "geometry"] = (
            points.loc[non_points, "geometry"]
            .representative_point()
        )

    points.plot(
        ax=ax,
        color="#ff38d1",
        edgecolor="black",
        markersize=55,
        marker="*",
        zorder=10
    )

    if name_col:
        for _, row in points.iterrows():
            geom = row.geometry
            if geom is None or geom.is_empty:
                continue

            ax.annotate(
                str(row[name_col]),
                (geom.x, geom.y),
                xytext=(4, 4),
                textcoords="offset points",
                fontsize=7,
                color="white",
                bbox={
                    "facecolor": "black",
                    "alpha": 0.8,
                    "pad": 1.5
                },
                zorder=11
            )


def draw_routes(ax, routes, alt_col):
    if routes is None or routes.empty:
        return

    for _, row in routes.iterrows():
        geom = row.geometry

        if geom is None or geom.is_empty:
            continue

        alt = 1

        if alt_col:
            try:
                alt = int(row[alt_col])
            except (ValueError, TypeError):
                pass

        gpd.GeoSeries(
            [geom], crs=routes.crs
        ).plot(
            ax=ax,
            color=ROUTE_COLORS.get(alt, "#ffffff"),
            linewidth=2.2,
            zorder=9
        )


def configure_axes(ax):
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("Easting / X coordinate")
    ax.set_ylabel("Northing / Y coordinate")
    ax.ticklabel_format(
        style="plain", axis="both", useOffset=False
    )
    ax.grid(
        alpha=0.12,
        linestyle=":",
        linewidth=0.4
    )


# ============================================================
# PRELIMINARY BUILDING-TO-ROAD DISTANCES
# ============================================================

def calculate_nearest_roads(buildings, roads):
    """
    Calculate the shortest geometry distance from each building
    footprint to a road line in a projected metric CRS.

    This measures proximity only. It does not prove that a
    driveway, entrance, or legal/physical connection exists.
    """

    if buildings is None or buildings.empty:
        return pd.DataFrame()

    result = pd.DataFrame({
        "building_id": buildings["building_id"].astype(str)
    })

    result["nearest_road_distance_m"] = np.nan
    result["nearest_road_screening_status"] = (
        "NO_ROAD_LAYER"
    )

    if roads is None or roads.empty:
        return result

    try:
        metric_crs = buildings.estimate_utm_crs()

        if metric_crs is None:
            print(
                "WARNING: Cannot determine a metric CRS. "
                "Nearest-road distances will be unavailable."
            )
            return result

        b_metric = buildings.to_crs(metric_crs)
        r_metric = roads.to_crs(metric_crs)

        road_geometries = [
            geom
            for geom in r_metric.geometry
            if geom is not None and not geom.is_empty
        ]

        if not road_geometries:
            return result

        from shapely.ops import unary_union
        road_union = unary_union(road_geometries)

        distances = []
        statuses = []

        for geom in b_metric.geometry:
            if geom is None or geom.is_empty:
                distances.append(np.nan)
                statuses.append("INVALID_GEOMETRY")
                continue

            distance = float(geom.distance(road_union))
            distances.append(distance)

            if distance <= NEAR_ROAD_THRESHOLD_M:
                statuses.append(
                    "NEAR_MAPPED_ROAD_REVIEW_ACCESS"
                )
            else:
                statuses.append(
                    "FAR_FROM_MAPPED_ROAD_REVIEW"
                )

        result["nearest_road_distance_m"] = distances
        result["nearest_road_screening_status"] = statuses

    except Exception as exc:
        print(
            "WARNING: Nearest-road calculation failed: "
            f"{exc}"
        )

    return result


# ============================================================
# BUILDING INVENTORY
# ============================================================

def make_building_inventory(buildings, roads):
    if buildings is None or buildings.empty:
        report = pd.DataFrame([{
            "status": "NO_BUILDING_FOOTPRINT_LAYER_FOUND",
            "message": (
                "No suitable building polygon layer was found. "
                "House detection is required before building-level "
                "connectivity analysis can be performed."
            )
        }])

        safe_csv(
            report,
            OUT / "damarakunta_v5_building_inventory.csv"
        )
        return None

    buildings = valid_geometries(buildings)

    # Retain polygons only. Building points are not footprints.
    buildings = buildings[
        buildings.geometry.geom_type.isin(
            ["Polygon", "MultiPolygon"]
        )
    ].copy()

    if buildings.empty:
        print(
            "WARNING: The selected layer contains no polygons."
        )
        return None

    # Create stable output IDs without overwriting source data.
    buildings = buildings.reset_index(drop=True)
    buildings["building_id"] = [
        f"DMK_BLD_{i:05d}"
        for i in range(1, len(buildings) + 1)
    ]

    area_crs = buildings.estimate_utm_crs()

    if area_crs is not None:
        metric_buildings = buildings.to_crs(area_crs)
        buildings["footprint_area_m2"] = [
            float(g.area)
            for g in metric_buildings.geometry
        ]
    else:
        buildings["footprint_area_m2"] = np.nan

    distances = calculate_nearest_roads(
        buildings, roads
    )

    # Use the generated ID for a safe one-to-one merge.
    buildings = buildings.merge(
        distances,
        on="building_id",
        how="left"
    )

    buildings["building_type"] = (
        "BUILDING_TYPE_UNVERIFIED"
    )

    inventory_path = (
        OUT / "damarakunta_v5_building_inventory.csv"
    )

    table = buildings.drop(
        columns="geometry",
        errors="ignore"
    )

    safe_csv(table, inventory_path)

    print(
        f"Building footprints loaded: {len(buildings)}"
    )

    print(
        "Building types are unverified unless the source "
        "dataset explicitly identifies them."
    )

    return buildings


# ============================================================
# OVERVIEW MAP
# ============================================================

def create_overview(
    boundary,
    roads,
    routes,
    facilities,
    buildings
):
    print("Creating all-building overview...")

    image, extent = read_rgb(
        max_dimension=MAX_OVERVIEW_DIMENSION
    )

    with rasterio.open(IMAGE) as src:
        raster_footprint = box(
            src.bounds.left,
            src.bounds.bottom,
            src.bounds.right,
            src.bounds.top
        )

    fig, ax = plt.subplots(
        figsize=(16, 12),
        dpi=120
    )

    ax.imshow(
        image,
        extent=extent,
        origin="upper",
        interpolation="nearest",
        zorder=0
    )

    draw_roads(ax, roads)
    draw_boundary(ax, boundary)

    if buildings is not None and not buildings.empty:
        visible = gpd.clip(
            buildings, raster_footprint
        )
        draw_buildings(
            ax, visible, "building_id"
        )

    draw_routes(ax, routes, choose_column(
        routes, ["alternative", "alt", "route_id"]
    ))

    draw_facilities(
        ax,
        facilities,
        choose_column(
            facilities,
            ["facility_name", "name", "facility"]
        )
    )

    # Zoom to the village boundary when possible.
    if boundary is not None and not boundary.empty:
        minx, miny, maxx, maxy = boundary.total_bounds

        px = max(20, (maxx - minx) * 0.04)
        py = max(20, (maxy - miny) * 0.04)

        ax.set_xlim(
            max(extent[0], minx - px),
            min(extent[1], maxx + px)
        )
        ax.set_ylim(
            max(extent[2], miny - py),
            min(extent[3], maxy + py)
        )

    configure_axes(ax)

    ax.set_title(
        "Damarakunta V5 — Building and Road Review\n"
        "Yellow outlines: building footprints | "
        "Pink stars: priority facilities | "
        "Colored lines: V4 route alternatives\n"
        "Proximity does not prove physical access",
        fontsize=13,
        fontweight="bold"
    )

    fig.tight_layout()

    fig.savefig(
        OVERVIEW_PNG,
        dpi=300,
        bbox_inches="tight",
        facecolor="white"
    )

    fig.savefig(
        OVERVIEW_PDF,
        bbox_inches="tight",
        facecolor="white"
    )

    plt.close(fig)

    print(f"Overview PNG: {OVERVIEW_PNG}")
    print(f"Overview PDF: {OVERVIEW_PDF}")


# ============================================================
# INDIVIDUAL BUILDING CLOSE-UPS
# ============================================================

def create_building_details(
    buildings,
    roads,
    routes,
    boundary,
    facilities
):
    if buildings is None or buildings.empty:
        print(
            "Skipping individual house maps because no "
            "building-footprint layer is available."
        )
        return

    count = min(
        len(buildings),
        MAX_DETAIL_MAPS
    )

    print(
        f"Creating close-ups for {count} buildings..."
    )

    route_alt_col = choose_column(
        routes, ["alternative", "alt", "route_id"]
    )

    for index, (_, building) in enumerate(
        buildings.iloc[:count].iterrows(),
        start=1
    ):
        geom = building.geometry

        if geom is None or geom.is_empty:
            continue

        minx, miny, maxx, maxy = geom.bounds

        # Add context around the footprint.
        width = maxx - minx
        height = maxy - miny

        margin = max(
            width * 4,
            height * 4,
            25.0
        )

        requested_bounds = (
            minx - margin,
            miny - margin,
            maxx + margin,
            maxy + margin
        )

        try:
            image, extent = read_rgb_bounds(
                requested_bounds,
                max_dimension=MAX_DETAIL_DIMENSION
            )
        except Exception as exc:
            print(
                f"Skipping close-up for "
                f"{building['building_id']}: {exc}"
            )
            continue

        crop_box = box(
            extent[0], extent[2],
            extent[1], extent[3]
        )

        fig, ax = plt.subplots(
            figsize=(8, 8),
            dpi=100
        )

        ax.imshow(
            image,
            extent=extent,
            origin="upper",
            interpolation="nearest",
            zorder=0
        )

        roads_crop = (
            gpd.clip(roads, crop_box)
            if roads is not None and not roads.empty
            else roads
        )

        routes_crop = (
            gpd.clip(routes, crop_box)
            if routes is not None and not routes.empty
            else routes
        )

        boundary_crop = (
            gpd.clip(boundary, crop_box)
            if boundary is not None and not boundary.empty
            else boundary
        )

        buildings_crop = gpd.clip(
            buildings, crop_box
        )

        facilities_crop = (
            gpd.clip(facilities, crop_box)
            if facilities is not None and not facilities.empty
            else facilities
        )

        draw_roads(ax, roads_crop)
        draw_boundary(ax, boundary_crop)
        draw_buildings(
            ax, buildings_crop, "building_id"
        )
        draw_routes(
            ax, routes_crop, route_alt_col
        )
        draw_facilities(
            ax,
            facilities_crop,
            choose_column(
                facilities_crop,
                ["facility_name", "name", "facility"]
            )
        )

        # Highlight the current building with a stronger outline.
        gpd.GeoSeries(
            [geom], crs=buildings.crs
        ).boundary.plot(
            ax=ax,
            color="#00ff35",
            linewidth=2.0,
            zorder=12
        )

        ax.set_xlim(extent[0], extent[1])
        ax.set_ylim(extent[2], extent[3])

        configure_axes(ax)

        distance = building.get(
            "nearest_road_distance_m", np.nan
        )

        distance_text = (
            f"{distance:.1f} m"
            if pd.notna(distance)
            else "Unavailable"
        )

        ax.set_title(
            f"{building['building_id']}\n"
            f"Nearest mapped road: {distance_text} "
            "(proximity only)",
            fontsize=10,
            fontweight="bold"
        )

        fig.tight_layout()

        out_path = (
            DETAIL_DIR
            / f"{building['building_id']}.png"
        )

        fig.savefig(
            out_path,
            dpi=DETAIL_DPI,
            bbox_inches="tight",
            facecolor="white"
        )

        plt.close(fig)

        if index % 25 == 0:
            print(
                f"  Created {index}/{count} close-ups"
            )

    print(f"Building close-ups: {DETAIL_DIR}")

    if len(buildings) > MAX_DETAIL_MAPS:
        print(
            f"NOTE: {len(buildings)} buildings are in the "
            f"inventory, but only the first "
            f"{MAX_DETAIL_MAPS} received individual maps. "
            "Increase MAX_DETAIL_MAPS to generate more."
        )


# ============================================================
# MAIN
# ============================================================

def main():
    for path in [IMAGE, BOUNDARY, ROADS, ROUTES]:
        require_file(path)

    with rasterio.open(IMAGE) as src:
        image_crs = src.crs

    if image_crs is None:
        raise ValueError(
            "Satellite raster has no CRS."
        )

    print("Reading village boundary...")
    boundary = reproject(
        read_layer(BOUNDARY),
        image_crs,
        "Boundary"
    )

    print("Reading existing roads...")
    roads = reproject(
        read_layer(ROADS),
        image_crs,
        "Roads"
    )

    print("Reading existing V4 route alternatives...")
    try:
        routes = reproject(
            read_layer(
                ROUTES,
                layer="route_alternatives"
            ),
            image_crs,
            "V4 routes"
        )
    except Exception:
        routes = reproject(
            read_layer(ROUTES),
            image_crs,
            "V4 routes"
        )

    facilities = None

    if FACILITIES.exists():
        try:
            facilities = reproject(
                read_layer(
                    FACILITIES,
                    layer="priority_facilities"
                ),
                image_crs,
                "Priority facilities"
            )
        except Exception as exc:
            print(
                f"WARNING: Facilities unavailable: {exc}"
            )

    print("Searching for building footprints...")
    raw_buildings, source_path, source_layer = (
        discover_buildings()
    )

    buildings = None

    if raw_buildings is not None:
        buildings = reproject(
            raw_buildings,
            image_crs,
            "Building footprints"
        )

        buildings = make_building_inventory(
            buildings,
            roads
        )

    else:
        print("\nNO BUILDING FOOTPRINT LAYER FOUND.")
        print(
            "The script cannot identify every house from "
            "the raster without a building-detection model "
            "or a supplied footprint dataset."
        )

        report = pd.DataFrame([{
            "status": "NO_BUILDING_FOOTPRINT_LAYER_FOUND",
            "message": (
                "Supply a polygon building-footprint layer "
                "or run a validated building segmentation model."
            )
        }])

        safe_csv(
            report,
            INVENTORY_CSV
        )

    create_overview(
        boundary,
        roads,
        routes,
        facilities,
        buildings
    )

    create_building_details(
        buildings,
        roads,
        routes,
        boundary,
        facilities
    )

    print("\n=== DAMARAKUNTA V5 REVIEW COMPLETE ===")
    print(f"Overview: {OVERVIEW_PNG}")
    print(f"Overview PDF: {OVERVIEW_PDF}")
    print(f"Inventory: {INVENTORY_CSV}")
    print(f"Building detail folder: {DETAIL_DIR}")

    print(
        "\nCAUTION: Nearest-road distance is a geometric "
        "proximity measure. It does not establish a road "
        "entrance, connected path, right of way, ownership, "
        "clearance, drainage suitability, or construction "
        "feasibility."
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("\nERROR: V5 map generation failed.")
        print(f"{type(exc).__name__}: {exc}")
        sys.exit(1)
