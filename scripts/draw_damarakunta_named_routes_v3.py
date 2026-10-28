
from pathlib import Path
import warnings

import geopandas as gpd
import matplotlib.pyplot as plt
import rasterio
from rasterio.plot import reshape_as_image
from shapely.geometry import box

warnings.filterwarnings("ignore", category=UserWarning)

# ============================================================
# DAMARAKUNTA RURAL INFRASTRUCTURE PLANNING - V3 MAPS
# This script visualizes candidate routes and feasibility checks.
# It does NOT approve routes for construction.
# ============================================================

ROOT = Path(r"D:\Telangana_Rural_Project")
VILLAGE = ROOT / "Siddipet" / "Damarakunta"
RESULTS = VILLAGE / "results"
ALIGNED = VILLAGE / "aligned"
REFERENCE = VILLAGE / "reference"
STUDY_AREA = VILLAGE / "study_area"

# V3 outputs
ROUTES = RESULTS / "damarakunta_routes_v3.gpkg"
PARCEL_IMPACTS = RESULTS / "damarakunta_route_parcel_impacts_v3.gpkg"
OUT_MAP = RESULTS / "damarakunta_feasibility_map_v3.png"
OUT_ZOOM = RESULTS / "damarakunta_feasibility_zoom_v3.png"

# Input layers
IMAGERY = ALIGNED / "damarakunta_esri_highres_mosaic_0p6m.tif"
BOUNDARY = STUDY_AREA / "damarakunta_boundary.gpkg"
ROADS = REFERENCE / "tgrac_road_network.gpkg"
FACILITIES = REFERENCE / "damarakunta_priority_facilities.gpkg"

# Optional school-compound layer.
# The script searches the reference folder for likely matching files.
SCHOOL_COMPOUND_CANDIDATES = [
    REFERENCE / "damarakunta_school_compounds.gpkg",
    REFERENCE / "school_compounds.gpkg",
    REFERENCE / "tgrac_school_compounds.gpkg",
]

# ============================================================
# HELPERS
# ============================================================

def require_file(path, description):
    if not path.exists():
        raise FileNotFoundError(
            f"Missing {description}:\n{path}\n"
            "Check the filename and rerun the script."
        )


def read_vector(path, description):
    require_file(path, description)
    layer = gpd.read_file(path)

    if layer.empty:
        raise ValueError(f"{description} contains no features: {path}")

    return layer


def reproject_if_needed(gdf, target_crs):
    if gdf.crs is None:
        raise ValueError("A vector layer has no CRS; cannot safely overlay it.")

    if gdf.crs != target_crs:
        return gdf.to_crs(target_crs)

    return gdf


def find_column(gdf, candidates):
    lookup = {str(c).lower(): c for c in gdf.columns}

    for candidate in candidates:
        if candidate.lower() in lookup:
            return lookup[candidate.lower()]

    return None


def get_facility_label(row, name_col, type_col=None, id_col=None):
    name = str(row[name_col]) if name_col else "Facility"
    facility_type = str(row[type_col]) if type_col else ""

    if facility_type and facility_type.lower() not in ("nan", "none", ""):
        return f"{name}\n({facility_type})"

    if id_col and (not name or name.lower() in ("nan", "none", "")):
        return str(row[id_col])

    return name


def get_route_label(row):
    facility_col = find_column(
        gpd.GeoDataFrame(columns=list(row.index)),
        ["facility_name", "facility", "name", "facility_id"],
    )
    alt_col = find_column(
        gpd.GeoDataFrame(columns=list(row.index)),
        ["alternative", "alternative_id", "route_alt", "alt_id"],
    )

    facility = str(row[facility_col]) if facility_col else ""
    alternative = str(row[alt_col]) if alt_col else ""

    if not facility or facility.lower() == "nan":
        facility = "Candidate route"

    if alternative and alternative.lower() != "nan":
        return f"{facility} - {alternative}"

    return facility


def draw_base(ax, imagery, boundary, roads, facilities, compounds, extent=None):
    # Satellite imagery
    with rasterio.open(imagery) as src:
        if extent is None:
            bounds = src.bounds
        else:
            bounds = extent

        window = rasterio.windows.from_bounds(
            bounds.left, bounds.bottom, bounds.right, bounds.top,
            transform=src.transform,
        )
        window = window.round_offsets().round_lengths()

        data = src.read(
            indexes=[1, 2, 3],
            window=window,
            out_shape=(
                3,
                min(1800, max(1, int(window.height))),
                min(1800, max(1, int(window.width))),
            ),
            boundless=True,
        )

        image = reshape_as_image(data)

        if image.dtype != "uint8":
            image = image.astype("float32")
            low = image.min()
            high = image.max()
            if high > low:
                image = (255 * (image - low) / (high - low)).clip(0, 255)
            image = image.astype("uint8")

        ax.imshow(
            image,
            extent=[
                bounds.left, bounds.right,
                bounds.bottom, bounds.top,
            ],
            origin="upper",
        )

    # Study boundary
    boundary.boundary.plot(
        ax=ax, color="white", linewidth=1.2, zorder=3,
    )

    # Existing roads
    roads.plot(
        ax=ax, color="#00E5FF", linewidth=1.6,
        alpha=0.95, zorder=4,
    )

    # School compound boundaries, if available
    if compounds is not None and not compounds.empty:
        compounds.boundary.plot(
            ax=ax, color="#7CFC00", linewidth=1.5,
            alpha=0.95, zorder=5,
        )

    # Facility points
    facilities.plot(
        ax=ax, color="#FFD54F", edgecolor="black",
        linewidth=0.7, markersize=45, zorder=8,
    )


def draw_routes(ax, routes):
    # White casing keeps candidate lines visible over imagery.
    routes.plot(
        ax=ax, color="white", linewidth=5.0,
        alpha=0.90, zorder=6,
    )
    routes.plot(
        ax=ax, color="#FF00FF", linewidth=2.7,
        alpha=1.0, zorder=7,
    )


def draw_parcel_impacts(ax, impacts):
    if impacts is None or impacts.empty:
        return

    # Highlight parcel-intersection geometries.
    impacts.boundary.plot(
        ax=ax, color="#FFEB3B", linewidth=1.2,
        alpha=0.95, zorder=5,
    )


def label_facilities(ax, facilities):
    name_col = find_column(
        facilities,
        ["name", "facility_name", "school_name", "facility"],
    )
    type_col = find_column(
        facilities,
        ["facility_type", "type", "category", "amenity"],
    )
    id_col = find_column(
        facilities,
        ["facility_id", "id", "nin_id"],
    )

    for _, row in facilities.iterrows():
        point = row.geometry
        if point is None or point.is_empty:
            continue

        label = get_facility_label(row, name_col, type_col, id_col)
        ax.annotate(
            label,
            (point.x, point.y),
            xytext=(5, 6),
            textcoords="offset points",
            fontsize=7,
            color="white",
            bbox=dict(
                boxstyle="round,pad=0.2",
                facecolor="black",
                alpha=0.7,
                edgecolor="none",
            ),
            zorder=10,
        )


def set_map_extent(ax, boundary, padding_fraction=0.06):
    minx, miny, maxx, maxy = boundary.total_bounds
    dx = maxx - minx
    dy = maxy - miny

    ax.set_xlim(minx - dx * padding_fraction, maxx + dx * padding_fraction)
    ax.set_ylim(miny - dy * padding_fraction, maxy + dy * padding_fraction)


def save_map(fig, path):
    fig.savefig(path, dpi=250, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Saved map: {path}")


# ============================================================
# MAIN
# ============================================================

def main():
    print("Loading Damarakunta V3 mapping inputs...")

    require_file(ROUTES, "V3 candidate routes")
    require_file(PARCEL_IMPACTS, "V3 parcel-impact layer")
    require_file(IMAGERY, "satellite imagery")
    require_file(BOUNDARY, "study-area boundary")
    require_file(ROADS, "existing road network")
    require_file(FACILITIES, "priority facility points")

    boundary = read_vector(BOUNDARY, "study-area boundary")
    routes = read_vector(ROUTES, "V3 candidate routes")
    impacts = gpd.read_file(PARCEL_IMPACTS)
    roads = read_vector(ROADS, "existing road network")
    facilities = read_vector(FACILITIES, "priority facility points")

    target_crs = boundary.crs

    routes = reproject_if_needed(routes, target_crs)
    roads = reproject_if_needed(roads, target_crs)
    facilities = reproject_if_needed(facilities, target_crs)

    if not impacts.empty:
        impacts = reproject_if_needed(impacts, target_crs)

    # Clip roads to the village boundary for a clearer map.
    boundary_union = boundary.geometry.union_all()
    roads = roads[roads.geometry.intersects(boundary_union)].copy()
    roads["geometry"] = roads.geometry.intersection(boundary_union)
    roads = roads[~roads.geometry.is_empty].copy()

    # Clip the display of routes to the study area.
    routes["geometry"] = routes.geometry.intersection(boundary_union)
    routes = routes[~routes.geometry.is_empty].copy()

    # School compounds are optional because filenames vary between datasets.
    compounds = None
    for candidate in SCHOOL_COMPOUND_CANDIDATES:
        if candidate.exists():
            try:
                compounds = gpd.read_file(candidate)
                if not compounds.empty:
                    compounds = reproject_if_needed(compounds, target_crs)
                    compounds = compounds[
                        compounds.geometry.intersects(boundary_union)
                    ].copy()
                    print(f"Using school compounds: {candidate}")
                    break
            except Exception as exc:
                print(f"Could not load optional compound layer {candidate}: {exc}")

    # Full-village map
    fig, ax = plt.subplots(figsize=(15, 11))
    draw_base(
        ax, IMAGERY, boundary, roads, facilities, compounds,
    )
    draw_parcel_impacts(ax, impacts)
    draw_routes(ax, routes)
    label_facilities(ax, facilities)
    set_map_extent(ax, boundary)

    ax.set_title(
        "Damarakunta Rural Infrastructure Planning\n"
        "V3 Candidate Access Routes and Preliminary Parcel Screening",
        fontsize=14,
        weight="bold",
    )
    ax.set_xlabel("Easting (m)")
    ax.set_ylabel("Northing (m)")
    ax.grid(alpha=0.15, color="white")
    ax.set_aspect("equal", adjustable="box")

    fig.text(
        0.01, 0.01,
        "Existing roads: cyan | Candidate routes: magenta | "
        "Parcel-impact outlines: yellow | School compounds: green\n"
        "Preliminary GIS screening only. Facility coordinates, entrances, "
        "ownership, drainage, and construction feasibility require verification.",
        fontsize=8,
    )
    fig.tight_layout(rect=[0, 0.045, 1, 1])
    save_map(fig, OUT_MAP)

    # Zoomed map around the candidate routes
    if not routes.empty:
        minx, miny, maxx, maxy = routes.total_bounds
        dx = max(maxx - minx, 100)
        dy = max(maxy - miny, 100)
        zoom_bounds = box(
            minx - dx * 0.35,
            miny - dy * 0.35,
            maxx + dx * 0.35,
            maxy + dy * 0.35,
        ).bounds

        class Bounds:
            left, bottom, right, top = zoom_bounds

        fig, ax = plt.subplots(figsize=(15, 11))
        draw_base(
            ax, IMAGERY, boundary, roads, facilities, compounds,
            extent=Bounds,
        )
        draw_parcel_impacts(ax, impacts)
        draw_routes(ax, routes)
        label_facilities(ax, facilities)

        ax.set_xlim(zoom_bounds[0], zoom_bounds[2])
        ax.set_ylim(zoom_bounds[1], zoom_bounds[3])
        ax.set_title(
            "Damarakunta V3 Candidate Routes\n"
            "Zoomed View for Visual Review",
            fontsize=14,
            weight="bold",
        )
        ax.set_xlabel("Easting (m)")
        ax.set_ylabel("Northing (m)")
        ax.grid(alpha=0.15, color="white")
        ax.set_aspect("equal", adjustable="box")

        fig.text(
            0.01, 0.01,
            "Magenta lines are generated route candidates, not approved roads. "
            "Check facility entrances, existing-road connections, buildings, "
            "parcels, and drainage before selecting a route.",
            fontsize=8,
        )
        fig.tight_layout(rect=[0, 0.035, 1, 1])
        save_map(fig, OUT_ZOOM)
    else:
        print("No route geometries available for the zoomed map.")

    print("\nDAMARAKUNTA V3 MAP GENERATION COMPLETE")
    print(f"Routes displayed: {len(routes)}")
    print(f"Parcel-impact features: {len(impacts)}")
    print(f"Existing road features displayed: {len(roads)}")
    print(f"Full map: {OUT_MAP}")
    print(f"Zoom map: {OUT_ZOOM}")


if __name__ == "__main__":
    main()
