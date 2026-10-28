"""Create high-resolution overview maps for Damarakunta individual-house route candidates.

Reads existing outputs only. Does not edit source data or route outputs.
Creates a 600-dpi PNG and a vector PDF (with a downsampled raster backdrop) in the
individual_house_routing_v1 output folder.
"""
from pathlib import Path
import sys
import numpy as np
import geopandas as gpd
import rasterio
from rasterio.enums import Resampling
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

ROOT = Path(r"D:\Telangana_Rural_Project\Siddipet\Damarakunta")
OUT = ROOT / "results" / "individual_house_routing_v1"
GPKG = OUT / "individual_house_routes_v1.gpkg"
ROADS = ROOT / "reference" / "tgrac_road_network.gpkg"
BUILDINGS = ROOT / "results" / "v8_instances" / "buildings_v8_full.gpkg"
BOUNDARY = ROOT / "study_area" / "damarakunta_boundary.gpkg"
BACKGROUND = ROOT / "aligned" / "damarakunta_esri_highres_mosaic_0p6m.tif"
CRS = "EPSG:32644"


def stop(msg):
    print("ERROR:", msg)
    raise SystemExit(1)

for p in (OUT, GPKG, ROADS, BUILDINGS, BACKGROUND):
    if not p.exists():
        stop(f"Missing required input: {p}")

print("Reading route layers...")
routes = gpd.read_file(GPKG, layer="house_routes").to_crs(CRS)
status = gpd.read_file(GPKG, layer="house_route_status_points").to_crs(CRS)
roads = gpd.read_file(ROADS).to_crs(CRS)
buildings = gpd.read_file(BUILDINGS, layer="buildings").to_crs(CRS)

if routes.empty:
    stop("house_routes layer is empty; no route lines to plot")
if "inside_village" in buildings.columns:
    buildings = buildings[buildings["inside_village"].astype(str).str.lower().isin(["true", "1"])]

# Plot extent from village boundary where available; otherwise from all house routes.
if BOUNDARY.exists():
    try:
        boundary = gpd.read_file(BOUNDARY).to_crs(CRS)
        boundary_geom = boundary.geometry.union_all()
        bounds = boundary_geom.bounds
        boundary_ok = True
    except Exception as e:
        print(f"WARNING: boundary layer could not be read ({e}); using route extent")
        boundary_ok = False
else:
    boundary_ok = False
if not boundary_ok:
    bounds = routes.total_bounds
xmin, ymin, xmax, ymax = bounds
padx = max((xmax - xmin) * 0.04, 30)
pady = max((ymax - ymin) * 0.04, 30)
xmin -= padx; xmax += padx; ymin -= pady; ymax += pady

# Read a reduced-resolution RGB image for a manageable, sharp-enough overview backdrop.
print("Reading downsampled satellite backdrop...")
with rasterio.open(BACKGROUND) as src:
    if src.crs is None or src.crs.to_epsg() != 32644:
        print(f"WARNING: imagery CRS is {src.crs}; map vectors are EPSG:32644")
    scale = min(1.0, 2600 / max(src.width, src.height))
    oh = max(1, int(src.height * scale)); ow = max(1, int(src.width * scale))
    count = min(3, src.count)
    image = src.read(list(range(1, count + 1)), out_shape=(count, oh, ow), resampling=Resampling.average)
    img_bounds = src.bounds
if image.shape[0] == 1:
    image = np.repeat(image, 3, axis=0)
image = np.moveaxis(image[:3], 0, -1)
# Robust display stretch handles imagery stored as uint16/float too.
if image.dtype != np.uint8:
    lo, hi = np.nanpercentile(image, [2, 98])
    image = np.clip((image.astype(float) - lo) / max(hi - lo, 1e-9), 0, 1)

colors = {"PLAUSIBLE": "#21a366", "REVIEW": "#ff9f1c", "UNRESOLVED_MERGE": "#d62728", "UNKNOWN": "#9467bd"}

def draw_map(out_stem, dpi_png, show_background=True, max_extent=None):
    w, h = max(xmax - xmin, 100), max(ymax - ymin, 100)
    aspect = h / w
    figw = 14
    figh = max(8, min(15, figw * aspect))
    fig, ax = plt.subplots(figsize=(figw, figh), constrained_layout=True)
    if show_background:
        l, b, r, t = img_bounds.left, img_bounds.bottom, img_bounds.right, img_bounds.top
        ax.imshow(image, extent=(l, r, b, t), origin="upper", zorder=0)
    if boundary_ok:
        boundary.boundary.plot(ax=ax, color="white", linewidth=1.6, zorder=2)
    # Existing reference roads drawn prominently above the background.
    roads.plot(ax=ax, color="#00e5ff", linewidth=1.1, alpha=0.95, zorder=3)
    # Predicted building footprints; the quality indicates segmentation uncertainty.
    for q in ("UNRESOLVED_MERGE", "REVIEW", "PLAUSIBLE"):
        subset = buildings[buildings.get("quality_class", "UNKNOWN") == q] if "quality_class" in buildings.columns else buildings.iloc[0:0]
        if not subset.empty:
            subset.boundary.plot(ax=ax, color=colors[q], linewidth=0.65, alpha=0.9, zorder=4)
    # Draw routes by building-prediction quality, with thinner lines to reduce clutter.
    for q in ("UNRESOLVED_MERGE", "REVIEW", "PLAUSIBLE"):
        subset = routes[routes["quality_class"].astype(str) == q] if "quality_class" in routes.columns else routes.iloc[0:0]
        if not subset.empty:
            subset.plot(ax=ax, color=colors[q], linewidth=0.72, alpha=0.9, zorder=5)
    # Target points help see houses whose routes may be too short to see on the overview.
    for q in ("UNRESOLVED_MERGE", "REVIEW", "PLAUSIBLE"):
        if "quality_class" not in status.columns:
            continue
        subset = status[status["quality_class"].astype(str) == q]
        if not subset.empty:
            subset.plot(ax=ax, color=colors[q], markersize=5, alpha=0.9, zorder=6)
    ax.set_xlim(xmin, xmax); ax.set_ylim(ymin, ymax)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("Easting (m) — EPSG:32644")
    ax.set_ylabel("Northing (m) — EPSG:32644")
    ax.set_title("Damarakunta — Individual House-to-Existing-Road Route Candidates\n"
                 f"{len(routes)} generated route geometries; all routes remain unverified planning candidates", fontsize=14)
    handles = [
        Line2D([0], [0], color="#00e5ff", lw=2, label="Existing TGRAC reference roads"),
        Line2D([0], [0], color=colors["PLAUSIBLE"], lw=2, label="Route / footprint: PLAUSIBLE detection"),
        Line2D([0], [0], color=colors["REVIEW"], lw=2, label="Route / footprint: REVIEW detection"),
        Line2D([0], [0], color=colors["UNRESOLVED_MERGE"], lw=2, label="Route / footprint: UNRESOLVED_MERGE"),
    ]
    ax.legend(handles=handles, loc="lower left", framealpha=0.95, fontsize=9)
    ax.grid(alpha=0.18, linewidth=0.4)
    png = OUT / f"{out_stem}.png"
    pdf = OUT / f"{out_stem}.pdf"
    fig.savefig(png, dpi=dpi_png, bbox_inches="tight", pad_inches=0.15, facecolor="white")
    fig.savefig(pdf, format="pdf", bbox_inches="tight", pad_inches=0.15, facecolor="white")
    plt.close(fig)
    print("Wrote:", png)
    print("Wrote:", pdf)

# Overview extent is based on the study-area boundary if available.
draw_map("individual_house_routes_v1_overview", dpi_png=600, show_background=True)

# Also write a focused high-res route-only view around target locations to reduce full-village clutter.
# The focused view uses the middle of the route extent and a deterministic 1.6 km square window.
rx0, ry0, rx1, ry1 = routes.total_bounds
cx, cy = (rx0 + rx1) / 2, (ry0 + ry1) / 2
half = 800
fx0, fx1, fy0, fy1 = cx - half, cx + half, cy - half, cy + half
# Temporarily switch plotting extent; keep it bounded by the available study area.
old = (xmin, xmax, ymin, ymax)
xmin, xmax, ymin, ymax = fx0, fx1, fy0, fy1
draw_map("individual_house_routes_v1_focus", dpi_png=600, show_background=True)
xmin, xmax, ymin, ymax = old

# Exact source-candidate count left out by the 10 m2 filter.
print("\nChecking candidates excluded by routing filter...")
all_b = gpd.read_file(BUILDINGS, layer="buildings").to_crs(CRS)
inside = all_b[all_b["inside_village"].astype(str).str.lower().isin(["true", "1"])].copy() if "inside_village" in all_b.columns else all_b.copy()
inside["area_m2_numeric"] = __import__("pandas").to_numeric(inside.get("area_m2", inside.geometry.area), errors="coerce")
excluded = inside[inside["area_m2_numeric"] < 10]
excluded_csv = OUT / "candidates_excluded_by_min_area_v1.csv"
excluded.drop(columns="geometry").to_csv(excluded_csv, index=False)
print(f"Inside-village candidates: {len(inside)}; area < 10 m² and excluded: {len(excluded)}")
print("Excluded-candidate table:", excluded_csv)
print("Done. Existing route outputs were only read; no original files were modified.")
