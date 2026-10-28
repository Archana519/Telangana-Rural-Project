"""Create read-only comparison maps for Damarakunta individual-house network planning.

Produces a side-by-side map of network-aware route additions vs independent routes,
using the existing GPKG, TGRAC reference roads, candidate footprints and imagery.
It does not modify source data or route layers.
"""
from pathlib import Path
import json
import sys

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.enums import Resampling
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

ROOT = Path(r"D:\Telangana_Rural_Project\Siddipet\Damarakunta")
OUT = ROOT / "results" / "individual_house_network_v1"
GPKG = OUT / "individual_house_network_v1.gpkg"
SUMMARY = OUT / "house_network_summary.json"
ROADS = ROOT / "reference" / "tgrac_road_network.gpkg"
BUILDINGS = ROOT / "results" / "v8_instances" / "buildings_v8_full.gpkg"
BOUNDARY = ROOT / "study_area" / "damarakunta_boundary.gpkg"
BACKGROUND = ROOT / "aligned" / "damarakunta_esri_highres_mosaic_0p6m.tif"
CRS = "EPSG:32644"
QUALITY_COLORS = {
    "PLAUSIBLE": "#20a464",
    "REVIEW": "#ff9f1c",
    "UNRESOLVED_MERGE": "#d62728",
    "UNKNOWN": "#9467bd",
}


def stop(msg):
    print("ERROR:", msg)
    raise SystemExit(1)

for p in (OUT, GPKG, SUMMARY, ROADS, BUILDINGS, BACKGROUND):
    if not p.exists():
        stop(f"Missing required input: {p}")

print("Reading shared-network planning layers (read-only)...")
try:
    net = gpd.read_file(GPKG, layer="routes_network_aware").to_crs(CRS)
    ind = gpd.read_file(GPKG, layer="routes_independent").to_crs(CRS)
    targets = gpd.read_file(GPKG, layer="house_target_status").to_crs(CRS)
except Exception as e:
    stop(f"Could not read expected GPKG layers: {e}")
roads = gpd.read_file(ROADS).to_crs(CRS)
buildings = gpd.read_file(BUILDINGS, layer="buildings").to_crs(CRS)
if "inside_village" in buildings.columns:
    buildings = buildings[buildings["inside_village"].astype(str).str.lower().isin(["true", "1"])]

if net.empty or ind.empty:
    stop(f"Route layer empty: network-aware={len(net)}, independent={len(ind)}")
if "quality_class" not in net.columns or "quality_class" not in ind.columns:
    stop("Expected quality_class field missing from route layers")

with open(SUMMARY, "r", encoding="utf-8") as f:
    summary = json.load(f)
net_unique = summary.get("unique_grid_edge_length_network_aware_m")
ind_unique = summary.get("unique_grid_edge_length_independent_m")
net_sum = summary.get("route_length_sum_network_aware_m")
ind_sum = summary.get("route_length_sum_independent_m")
reduction = summary.get("shared_network_unique_length_reduction_m")
if net_unique is not None and ind_unique not in (None, 0):
    reduction_pct = 100.0 * (float(ind_unique) - float(net_unique)) / float(ind_unique)
else:
    reduction_pct = None

# Plot bounds: study-area boundary if usable; else route/buildup extent.
boundary = None
if BOUNDARY.exists():
    try:
        b = gpd.read_file(BOUNDARY).to_crs(CRS)
        if not b.empty:
            boundary = b.geometry.union_all()
    except Exception as e:
        print(f"WARNING: could not read study-area boundary: {e}")
if boundary is not None and not boundary.is_empty:
    xmin, ymin, xmax, ymax = boundary.bounds
else:
    bounds = np.concatenate([net.total_bounds, ind.total_bounds, roads.total_bounds])
    xmin, ymin, xmax, ymax = bounds[0::2].min(), bounds[1::2].min(), bounds[0::2].max(), bounds[1::2].max()
padx = max((xmax - xmin) * 0.04, 30.0)
pady = max((ymax - ymin) * 0.04, 30.0)
full_bounds = (xmin - padx, ymin - pady, xmax + padx, ymax + pady)

print("Reading downsampled satellite backdrop...")
with rasterio.open(BACKGROUND) as src:
    if src.crs is None or src.crs.to_epsg() != 32644:
        print(f"WARNING: image CRS={src.crs}; assumed vector display CRS EPSG:32644")
    scale = min(1.0, 2600 / max(src.width, src.height))
    oh, ow = max(1, int(src.height * scale)), max(1, int(src.width * scale))
    count = min(3, src.count)
    img = src.read(list(range(1, count + 1)), out_shape=(count, oh, ow), resampling=Resampling.average)
    img_bounds = src.bounds
if img.shape[0] == 1:
    img = np.repeat(img, 3, axis=0)
img = np.moveaxis(img[:3], 0, -1)
if img.dtype != np.uint8:
    finite = img[np.isfinite(img)]
    lo, hi = np.percentile(finite, [2, 98]) if finite.size else (0, 1)
    img = np.clip((img.astype(float) - lo) / max(float(hi - lo), 1e-9), 0, 1)

# Use only polygon boundaries to keep map legible at village scale.
def draw_panel(ax, route_gdf, title, bounds):
    l, b, r, t = img_bounds.left, img_bounds.bottom, img_bounds.right, img_bounds.top
    ax.imshow(img, extent=(l, r, b, t), origin="upper", zorder=0)
    if boundary is not None and not boundary.is_empty:
        gpd.GeoSeries([boundary], crs=CRS).boundary.plot(ax=ax, color="white", linewidth=1.4, zorder=2)
    if not roads.empty:
        roads.plot(ax=ax, color="#00e5ff", linewidth=0.9, alpha=0.95, zorder=3)
    for q in ("UNRESOLVED_MERGE", "REVIEW", "PLAUSIBLE"):
        subset = buildings[buildings["quality_class"].astype(str) == q] if "quality_class" in buildings.columns else buildings.iloc[0:0]
        if not subset.empty:
            subset.boundary.plot(ax=ax, color=QUALITY_COLORS[q], linewidth=0.42, alpha=0.8, zorder=4)
    # Network-aware lines are incremental connectors to the current planned network;
    # independent lines are separate candidates to the original reference-road layer.
    for q in ("UNRESOLVED_MERGE", "REVIEW", "PLAUSIBLE"):
        subset = route_gdf[route_gdf["quality_class"].astype(str) == q]
        if not subset.empty:
            subset.plot(ax=ax, color=QUALITY_COLORS[q], linewidth=0.65, alpha=0.86, zorder=5)
    ax.set_xlim(bounds[0], bounds[2]); ax.set_ylim(bounds[1], bounds[3])
    ax.set_aspect("equal", adjustable="box")
    ax.set_title(title, fontsize=11, pad=8)
    ax.set_xlabel("Easting (m) — EPSG:32644", fontsize=8)
    ax.set_ylabel("Northing (m) — EPSG:32644", fontsize=8)
    ax.tick_params(labelsize=7)
    ax.grid(alpha=0.12, linewidth=0.3)


def make_figure(stem, bounds):
    width = max(bounds[2] - bounds[0], 1)
    height = max(bounds[3] - bounds[1], 1)
    aspect = height / width
    fig_h = max(7.4, min(12, 14 * aspect * 0.54))
    fig, axs = plt.subplots(1, 2, figsize=(16, fig_h), constrained_layout=True)
    net_title = "Network-aware shared planning\n" + (
        f"Unique grid-edge length: {float(net_unique):,.1f} m" if net_unique is not None else "Unique grid-edge length: unavailable")
    ind_title = "Independent house-to-reference-road routes\n" + (
        f"Unique grid-edge length: {float(ind_unique):,.1f} m" if ind_unique is not None else "Unique grid-edge length: unavailable")
    draw_panel(axs[0], net, net_title, bounds)
    draw_panel(axs[1], ind, ind_title, bounds)
    title = "Damarakunta — Individual-house route planning comparison"
    if reduction is not None and reduction_pct is not None:
        title += f"\nUnique grid-edge difference: {float(reduction):,.1f} m ({reduction_pct:.2f}% relative to independent baseline)"
    fig.suptitle(title, fontsize=14, fontweight="bold")
    handles = [
        Line2D([0], [0], color="#00e5ff", lw=2, label="Existing TGRAC reference roads"),
        Line2D([0], [0], color=QUALITY_COLORS["PLAUSIBLE"], lw=2, label="Route / footprint: PLAUSIBLE"),
        Line2D([0], [0], color=QUALITY_COLORS["REVIEW"], lw=2, label="Route / footprint: REVIEW"),
        Line2D([0], [0], color=QUALITY_COLORS["UNRESOLVED_MERGE"], lw=2, label="Route / footprint: UNRESOLVED_MERGE"),
    ]
    fig.legend(handles=handles, loc="lower center", ncol=4, frameon=True, fontsize=8, bbox_to_anchor=(0.5, -0.01))
    png = OUT / f"{stem}.png"
    pdf = OUT / f"{stem}.pdf"
    fig.savefig(png, dpi=600, bbox_inches="tight", pad_inches=0.15, facecolor="white")
    fig.savefig(pdf, format="pdf", bbox_inches="tight", pad_inches=0.15, facecolor="white")
    plt.close(fig)
    print("Wrote:", png)
    print("Wrote:", pdf)

print(f"Feature counts — network-aware: {len(net)}; independent: {len(ind)}; target points: {len(targets)}")
make_figure("individual_house_network_v1_comparison_map", full_bounds)

# Focus view over midpoint of all target route extent; helps separate dense village detail.
combined_bounds = np.array([net.total_bounds, ind.total_bounds])
rx0 = float(combined_bounds[:, 0].min()); ry0 = float(combined_bounds[:, 1].min())
rx1 = float(combined_bounds[:, 2].max()); ry1 = float(combined_bounds[:, 3].max())
cx, cy = (rx0 + rx1) / 2.0, (ry0 + ry1) / 2.0
half_x = min(max((rx1 - rx0) * 0.38, 350.0), 850.0)
half_y = min(max((ry1 - ry0) * 0.38, 350.0), 850.0)
focus_bounds = (cx - half_x, cy - half_y, cx + half_x, cy + half_y)
make_figure("individual_house_network_v1_comparison_focus", focus_bounds)

# Write an auditable table of layer sizes / comparison metrics without altering input tables.
report = OUT / "individual_house_network_v1_map_audit.txt"
report.write_text(
    "Damarakunta individual-house network planning map audit\n"
    f"network_aware_route_features={len(net)}\n"
    f"independent_route_features={len(ind)}\n"
    f"target_status_features={len(targets)}\n"
    f"network_route_length_sum_m={net_sum}\n"
    f"independent_route_length_sum_m={ind_sum}\n"
    f"network_unique_grid_edge_length_m={net_unique}\n"
    f"independent_unique_grid_edge_length_m={ind_unique}\n"
    f"unique_grid_edge_reduction_m={reduction}\n"
    f"unique_grid_edge_reduction_percent={reduction_pct}\n"
    "Important: all mapped route lines are unverified planning alternatives, not approved roads.\n",
    encoding="utf-8")
print("Wrote:", report)
print("Done. Existing GeoPackage layers, raster inputs and CSVs were read only; no originals modified.")
