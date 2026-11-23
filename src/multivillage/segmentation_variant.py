"""Segmentation variant of the multi-settlement pipeline: StrongDINOv2Seg + OpenCV building instances instead of open footprints.

Used by `src.multivillage.run --variant segmentation --footprints <buildings_v8_*.gpkg>` and by scripts/run_village_end_to_end.py (any village).
It changes ONLY where the building footprints come from. Boundary, roads, facilities (places), land cover, DEM, cost surface, planner parameters,
the road-gap target rule, the penalty sweep and the omission scenarios are those of the village's open-data run (e.g. 01_ADILABAD), so the two runs differ in one factor.
Outputs go to DELIVERABLES_CONTRIBUTION_3_MULTI_VILLAGE/<folder>_SEGMENTATION/ (the open-data deliverables are never overwritten).

Satellite overlay figures carry the credit line required by the Esri World Imagery terms used for this project:
"Basemap imagery: Esri, Maxar, Earthstar Geographics, and the GIS User Community."
"""
from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import matplotlib
import numpy as np
import pandas as pd
import rasterio
from rasterio.windows import from_bounds
from shapely.geometry import box

matplotlib.use("Agg")
import matplotlib.pyplot as plt                                    # noqa: E402
from matplotlib.lines import Line2D                                # noqa: E402
from matplotlib.patches import Patch                               # noqa: E402

CREDIT = "Basemap imagery: Esri, Maxar, Earthstar Geographics, and the GIS User Community."
CRS = "EPSG:32644"
QCOL = {"PLAUSIBLE": "#2ca02c", "REVIEW": "#ffbf00", "UNRESOLVED_MERGE": "#d62728"}


# --------------------------------------------------------------------------------------------- footprints -> same schema as the open-data run
def load_footprints(path: str | Path, cell, v: dict) -> gpd.GeoDataFrame:
    """extract_buildings_v8 output (layer 'buildings') -> frame with the columns run.py / facilities.py expect.
    Kept: instances whose representative point is inside the study polygon and that were not rejected as no-data blobs.
    Quality classes are the Stage B ones (PLAUSIBLE / REVIEW / UNRESOLVED_MERGE); nothing is dropped by class, exactly as for Damarakunta."""
    b = gpd.read_file(path, layer="buildings").to_crs(CRS)
    need = {"quality_class", "area_m2", "mean_prob"}
    if not need <= set(b.columns):
        raise SystemExit(f"{path} lacks columns {sorted(need - set(b.columns))}: it must be the output of scripts/extract_buildings_v8.py")
    rp = b.geometry.representative_point()
    b = b[rp.within(cell)].copy()
    b["dataset"] = "StrongDINOv2Seg"
    b["confidence"] = b["mean_prob"].astype(float)
    b["id"] = b["bld_id"] if "bld_id" in b.columns else [f"B{i:05d}" for i in range(len(b))]
    b["area_m2"] = b.geometry.area
    small = v["min_house_area_m2"]
    b["quality_class_model"] = b["quality_class"]
    # same size rule as the open-data run (a shed/kiosk is not a house target); the penalty layer keeps every kept instance
    b.loc[b.area_m2 < small, "quality_class"] = "SMALL_EXCLUDED"
    return b.reset_index(drop=True)


# --------------------------------------------------------------------------------------------- tables
def write_tables(S: dict, res: list, odir: Path, cfg: dict, quick: bool) -> dict:
    from src.multivillage import report as R
    main = next(r for r in res if r["spec"]["kind"] == "main")["out"]
    strat = R.strategies_table(main)
    strat.to_csv(odir / "routing_strategy_comparison.csv", index=False, lineterminator="\n")
    b = S["classified"]
    bs = b.groupby(["dataset", "quality_class"]).agg(polygons=("id", "size"), median_area_m2=("area_m2", "median")).round(1).reset_index()
    bs.to_csv(odir / "building_extraction_summary.csv", index=False, lineterminator="\n")
    S["fac_all"].drop(columns="geometry").to_csv(odir / "verified_facilities.csv", index=False, lineterminator="\n")
    two = strat[strat.strategy == "Two-stage shared plan"].iloc[0]
    ind = strat[strat.strategy == "Independent least-cost routes"].iloc[0]
    summary = dict(footprints_total=int(len(b)), footprints_used_for_penalty=int(len(S["houses_all"])), gap_targets=int(len(S["gap"])),
                   facilities_verified=int(len(S["fac"])), unique_len_two_stage_m=float(two.unique_len_m), unique_len_independent_m=float(ind.unique_len_m),
                   saving_vs_independent_pct=float(two.saving_vs_independent_pct), routed=int(two.targets_routed), targets=int(two.targets_total),
                   routes_crossing=int(two.routes_crossing_other_footprints), length_inside_other_footprints_m=float(two.length_inside_other_footprints_m),
                   quality_classes=b.quality_class.value_counts().to_dict())
    if not quick:
        sweep = R.sweep_table(res)
        sweep.to_csv(odir / "penalty_sensitivity.csv", index=False, lineterminator="\n")
        rows, g = R.omission_table(res, float(two.unique_len_m), len(S["gap"]))
        rows.to_csv(odir / "omission_runs.csv", index=False, lineterminator="\n")
        g.to_csv(odir / "omission_summary.csv", index=False, lineterminator="\n")
        drows = [r["row"] for r in res if r["spec"]["kind"] == "def"]
        if drows:
            pd.DataFrame(drows).sort_values("min_dist_to_road_m").to_csv(odir / "target_definition_sensitivity.csv", index=False, lineterminator="\n")
    open_dir = odir.parent / odir.name.removesuffix("_SEGMENTATION")      # the open-footprint run of the same village, when it exists
    if open_dir != odir and (open_dir / "routing_strategy_comparison.csv").exists():
        o = pd.read_csv(open_dir / "routing_strategy_comparison.csv").set_index("strategy")
        s = strat.set_index("strategy")
        rows = []
        for k in ("Independent least-cost routes", "Length-only control", "Roads-only shared reference", "Two-stage shared plan"):
            rows.append(dict(strategy=k, open_footprints_unique_m=o.loc[k, "unique_len_m"], segmentation_unique_m=s.loc[k, "unique_len_m"],
                             open_saving_pct=o.loc[k, "saving_vs_independent_pct"], segmentation_saving_pct=s.loc[k, "saving_vs_independent_pct"],
                             open_crossing=o.loc[k, "routes_crossing_other_footprints"], segmentation_crossing=s.loc[k, "routes_crossing_other_footprints"]))
        pd.DataFrame(rows).to_csv(odir / "comparison_open_vs_segmentation.csv", index=False, lineterminator="\n")
    (odir / "metrics_summary.json").write_text(json.dumps(summary, indent=2, default=float), encoding="utf-8")
    return summary


# --------------------------------------------------------------------------------------------- satellite overlays
def _read_rgb(mosaic: Path, extent, max_px=2400):
    """Read an RGB window (decimated to at most max_px on the long side) -> (array, extent actually read)."""
    with rasterio.open(mosaic) as s:
        win = from_bounds(*extent, transform=s.transform).round_offsets().round_lengths()
        win = win.intersection(rasterio.windows.Window(0, 0, s.width, s.height))
        sc = max(1.0, max(win.width, win.height) / max_px)
        shape = (3, max(1, int(win.height / sc)), max(1, int(win.width / sc)))
        arr = s.read([1, 2, 3], window=win, out_shape=shape, resampling=rasterio.enums.Resampling.average)
        ext = rasterio.windows.bounds(win, s.transform)
    return np.moveaxis(arr, 0, -1), (ext[0], ext[2], ext[1], ext[3])      # imshow extent = left, right, bottom, top


def _panel(ax, mosaic, extent, scale_m, north=True):
    img, ex = _read_rgb(mosaic, extent)
    ax.imshow(img, extent=ex, origin="upper", zorder=0)
    ax.set_xlim(extent[0], extent[2]); ax.set_ylim(extent[1], extent[3])
    x0, y0, x1, y1 = extent
    sx, sy = x0 + 0.04 * (x1 - x0), y0 + 0.05 * (y1 - y0)
    ax.plot([sx, sx + scale_m], [sy, sy], color="w", lw=3.0, zorder=20)
    ax.text(sx + scale_m / 2, sy + 0.015 * (y1 - y0), f"{scale_m / 1000:g} km" if scale_m >= 1000 else f"{scale_m:g} m", ha="center", color="w", fontsize=7, zorder=20,
            bbox=dict(fc="k", alpha=0.4, ec="none", pad=1))
    if north:
        ax.annotate("N", xy=(x1 - 0.05 * (x1 - x0), y1 - 0.03 * (y1 - y0)), xytext=(x1 - 0.05 * (x1 - x0), y1 - 0.11 * (y1 - y0)), ha="center", color="w", fontsize=9,
                    fontweight="bold", arrowprops=dict(arrowstyle="-|>", color="w", lw=1.4), zorder=20)
    ax.text(0.995, 0.005, CREDIT, transform=ax.transAxes, ha="right", va="bottom", fontsize=4.8, color="w", zorder=25, bbox=dict(fc="k", alpha=0.45, ec="none", pad=1))
    ax.set_xticks([]); ax.set_yticks([]); ax.set_xlabel(""); ax.set_ylabel("")


def densest(gap, w=1400.0, h=1000.0):
    pts = np.c_[gap.geometry.representative_point().x, gap.geometry.representative_point().y]
    best, arg = -1, None
    for cx, cy in pts[:: max(1, len(pts) // 250)]:
        n = int(((abs(pts[:, 0] - cx) < w / 2) & (abs(pts[:, 1] - cy) < h / 2)).sum())
        if n > best:
            best, arg = n, (cx, cy)
    return (arg[0] - w / 2, arg[1] - h / 2, arg[0] + w / 2, arg[1] + h / 2)


def satellite_overlays(S: dict, main: dict, mosaic: Path, odir: Path, dpi=300) -> list:
    """Four publication panels on the Esri imagery. Single-panel PNGs are written too so they can be placed in one IEEE column each."""
    cell, L = S["cell"], S["layers"]
    ext = (cell.bounds[0] - 100, cell.bounds[1] - 100, cell.bounds[2] + 100, cell.bounds[3] + 100)
    zext = densest(S["gap"])
    fig_dir = odir / "figures"; fig_dir.mkdir(parents=True, exist_ok=True)
    outs = []
    roads = L["roads"].geometry.intersection(cell)
    b = S["classified"]
    fcol = {"school": "#1f78b4", "health": "#d62728", "government": "#6a3d9a"}

    def draw_base(ax, e, zoom, show_targets=True):
        _panel(ax, mosaic, e, 200 if zoom else 1000)
        gpd.GeoSeries([cell], crs=CRS).boundary.plot(ax=ax, color="#ffeb3b", lw=1.1, zorder=3)
        roads.plot(ax=ax, color="#00e5ff", lw=0.5 if not zoom else 1.0, zorder=4)
        for q, c in QCOL.items():
            g = b[b.quality_class_model == q] if "quality_class_model" in b else b[b.quality_class == q]
            if len(g):
                g.plot(ax=ax, fc="none", ec=c, lw=0.35 if not zoom else 0.9, zorder=5)
        if show_targets:
            S["gap"].plot(ax=ax, fc="#ff7f0e", ec="none", alpha=0.55, zorder=6)

    # Figure 1: study window + zoom
    for tag, e, zoom in (("a", ext, False), ("b", zext, True)):
        fig, ax = plt.subplots(figsize=(5.2, 5.2 * (e[3] - e[1]) / (e[2] - e[0]) + 0.1))
        draw_base(ax, e, zoom)
        for k, c in fcol.items():
            f = S["fac"][S["fac"].facility_type == k]
            if len(f):
                f.plot(ax=ax, marker="*", color=c, edgecolor="w", markersize=(70 if zoom else 28), linewidth=0.4, zorder=8)
        fig.subplots_adjust(0.005, 0.005, 0.995, 0.995)
        p = fig_dir / f"sat_map1_{tag}.png"; fig.savefig(p, dpi=dpi); plt.close(fig); outs.append(p)
    # Figure 2: independent vs two-stage on the imagery, window + zoom
    G = main["geoms"]
    for key, color, name in (("indep", "#4da3ff", "independent"), ("two", "#ff3b30", "two_stage")):
        for tag, e, zoom in (("window", ext, False), ("zoom", zext, True)):
            fig, ax = plt.subplots(figsize=(5.2, 5.2 * (e[3] - e[1]) / (e[2] - e[0]) + 0.1))
            _panel(ax, mosaic, e, 200 if zoom else 1000)
            gpd.GeoSeries([cell], crs=CRS).boundary.plot(ax=ax, color="#ffeb3b", lw=1.0, zorder=3)
            roads.plot(ax=ax, color="#00e5ff", lw=0.5 if not zoom else 1.0, zorder=4)
            S["gap"].plot(ax=ax, fc="#ff7f0e", ec="none", alpha=0.6, zorder=6)
            gpd.GeoSeries([g for _, g, _, _ in G[key]], crs=CRS).plot(ax=ax, color=color, lw=1.0 if not zoom else 2.0, alpha=0.95 if key == "two" else 0.55, zorder=7)
            fig.subplots_adjust(0.005, 0.005, 0.995, 0.995)
            p = fig_dir / f"sat_map2_{name}_{tag}.png"; fig.savefig(p, dpi=dpi); plt.close(fig); outs.append(p)
    # a legend-only strip for captions / Word
    fig = plt.figure(figsize=(7.2, 0.9)); fig.legend(handles=[
        Line2D([0], [0], color="#ffeb3b", lw=1.5, label="Study-area boundary"), Line2D([0], [0], color="#00e5ff", lw=1.2, label="Existing road"),
        Patch(fc="none", ec=QCOL["PLAUSIBLE"], label="Detected building: Plausible"), Patch(fc="none", ec=QCOL["REVIEW"], label="Review"), Patch(fc="none", ec=QCOL["UNRESOLVED_MERGE"], label="Unresolved merge"),
        Patch(fc="#ff7f0e", alpha=0.6, label="Road-gap house (target)"), Line2D([0], [0], color="#4da3ff", lw=2, label="Independent routes"), Line2D([0], [0], color="#ff3b30", lw=2, label="Two-stage shared network")],
        loc="center", ncol=4, frameon=False, fontsize=7)
    p = fig_dir / "sat_legend.png"; fig.savefig(p, dpi=dpi); plt.close(fig); outs.append(p)
    return outs
