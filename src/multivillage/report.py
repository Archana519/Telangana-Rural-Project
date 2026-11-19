"""Deliverables for one study area: tables, maps, comparison with Damarakunta and the data-source audit.

    python -m src.multivillage.report --village adilabad_urban

Reads data/villages/<id>/state.pkl (written by src.multivillage.run) and DELIVERABLES_DAMARAKUNTA_STAGE_B (read-only, for the comparison).
"""
from __future__ import annotations

import argparse
import json
import pickle
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from matplotlib.colors import ListedColormap
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from shapely.geometry import box

from src.multivillage import acquire as A, prepare as P
from src.multivillage.run import out_dir
from src.multivillage.sources import Source, sha256_file, write_manifest
from src.utils import data_downloader_helper as dl

REPO = Path(__file__).resolve().parents[2]
B = REPO / "DELIVERABLES_DAMARAKUNTA_STAGE_B" / "03_RESULTS_TABLES"
DPI = 300
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8, "axes.titlesize": 9, "savefig.facecolor": "white"})
WC_COLORS = {10: "#9fc79f", 20: "#d8d0a0", 30: "#e7ecc0", 40: "#efe3b8", 50: "#c9c9c9", 60: "#e6dccf", 80: "#bcd7ea", 0: "#ffffff"}
WC_NAMES = {10: "Tree cover", 20: "Shrubland", 30: "Grassland", 40: "Cropland", 50: "Built-up", 60: "Bare / sparse", 80: "Water"}


def load(cfg):
    S = pickle.load(open(A.data_dir(cfg) / "state.pkl", "rb"))
    res = S["results"]
    main = next(r for r in res if r["spec"]["kind"] == "main")["out"]
    return S, res, main


# ------------------------------------------------------------------------------------------------ Damarakunta reference (read-only)
def damarakunta() -> dict:
    t1 = pd.read_csv(B / "COMPARISON_TABLES/table1_length_reduction.csv")
    x4 = t1[t1.configuration == "x4 (primary)"].set_index("method")
    x1 = t1[t1.configuration == "x1 (P3 control)"].set_index("method")
    t6 = pd.read_csv(B / "COMPARISON_TABLES/table6_obstacle_avoidance.csv").set_index("run")
    t4 = pd.read_csv(B / "COMPARISON_TABLES/table4_c1_sensitivity_per_run.csv")
    base = float(t4[t4.perturbation.str.startswith("baseline")].unique_len_m.iloc[0])
    return dict(x4=x4, x1=x1, t6=t6, t4=t4, base=base)


# ------------------------------------------------------------------------------------------------ tables
def strategies_table(main) -> pd.DataFrame:
    rows = pd.DataFrame(main["rows"])
    ind = float(rows.loc[rows.plan == "Independent least-cost routes", "unique_len_m"].iloc[0])
    keep = ["plan", "targets_routed", "targets_total", "total_len_m", "unique_len_m", "shared_len_m", "unique_cost", "routes_crossing", "len_in_footprints_m"]
    t = rows[keep].copy()
    t.insert(5, "saving_vs_independent_pct", [round(100 * (ind - u) / ind, 1) if p != "Straight line" else np.nan for p, u in zip(t.plan, t.unique_len_m)])
    return t.rename(columns={"plan": "strategy", "len_in_footprints_m": "length_inside_other_footprints_m", "routes_crossing": "routes_crossing_other_footprints"})


def sweep_table(res) -> pd.DataFrame:
    rows = [r["row"] for r in res if r["spec"]["kind"] == "penalty"]
    main = next(r for r in res if r["spec"]["kind"] == "main")["out"]
    two = [x for x in main["rows"] if x["plan"] == "Two-stage shared plan"][0]
    ind = [x for x in main["rows"] if x["plan"] == "Independent least-cost routes"][0]
    rows.append(dict(penalty_mode="centre-in-footprint", mu=4.0, targets=two["targets_total"], routed=two["targets_routed"], unique_len_m=two["unique_len_m"],
                     independent_unique_len_m=ind["unique_len_m"], saving_vs_independent_pct=round(100 * (ind["unique_len_m"] - two["unique_len_m"]) / ind["unique_len_m"], 1),
                     routes_crossing=two["routes_crossing"], len_in_footprints_m=two["len_in_footprints_m"], failed=main["two_failed"] if "two_failed" in main else len(main["fails"])))
    t = pd.DataFrame(rows)
    mu1 = t[(t.penalty_mode == "centre-in-footprint") & (t.mu == 1.0)].iloc[0]
    t["length_change_vs_mu1_pct"] = (100 * (t.unique_len_m - mu1.unique_len_m) / mu1.unique_len_m).round(1)
    t["crossing_len_change_vs_mu1_pct"] = (100 * (t.len_in_footprints_m - mu1.len_in_footprints_m) / mu1.len_in_footprints_m).round(1)
    return t.sort_values(["penalty_mode", "mu"]).reset_index(drop=True)


def omission_table(res, base_unique, n_gap) -> tuple:
    rows = pd.DataFrame([r["row"] for r in res if r["spec"]["kind"] == "omit"])
    rows["delta_len_pct"] = (100 * (rows.unique_len_m - base_unique) / base_unique).round(1)
    rows["len_per_routed_house_m"] = (rows.unique_len_m / rows.routed_houses).round(1)
    g = rows.groupby("group").agg(runs=("scenario", "count"), house_targets=("house_targets", "mean"), routed_houses=("routed_houses", "mean"),
                                  unserved=("unserved_vs_all_gap_houses", "mean"), coverage_pct=("coverage_pct", "mean"), unique_len_m=("unique_len_m", "mean"),
                                  delta_len_pct=("delta_len_pct", "mean"), delta_min=("delta_len_pct", "min"), delta_max=("delta_len_pct", "max"),
                                  len_per_routed_house_m=("len_per_routed_house_m", "mean"), saving_pct=("saving_vs_independent_pct", "mean"),
                                  routes_crossing=("routes_crossing", "mean")).round(1).reset_index()
    return rows, g


# ------------------------------------------------------------------------------------------------ maps
def _landcover(S, ddir):
    with rasterio.open(ddir / "worldcover_10m.tif") as s:
        return s.read(1), s.transform


def _bg(ax, S, ddir, extent, alpha=0.75):
    lc, T = _landcover(S, ddir)
    codes = sorted(WC_COLORS)
    idx = np.zeros(lc.shape, np.uint8)
    for i, c in enumerate(codes):
        idx[lc == c] = i
    cm = ListedColormap([WC_COLORS[c] for c in codes])
    minx, miny, maxx, maxy = S["prep_meta"]["bounds"]
    ax.imshow(idx, cmap=cm, vmin=0, vmax=len(codes) - 1, extent=(minx, maxx, miny, maxy), origin="upper", interpolation="nearest", alpha=alpha, zorder=0)
    ax.set_xlim(extent[0], extent[2])
    ax.set_ylim(extent[1], extent[3])


def _decor(ax, extent, scale_m, north=True):
    x0, y0, x1, y1 = extent
    sx, sy = x0 + 0.04 * (x1 - x0), y0 + 0.05 * (y1 - y0)
    ax.plot([sx, sx + scale_m], [sy, sy], color="k", lw=2.2, zorder=20)
    ax.text(sx + scale_m / 2, sy + 0.012 * (y1 - y0), f"{scale_m / 1000:g} km" if scale_m >= 1000 else f"{scale_m:g} m", ha="center", va="bottom", fontsize=7, zorder=20)
    if north:
        ax.annotate("N", xy=(x1 - 0.05 * (x1 - x0), y1 - 0.03 * (y1 - y0)), xytext=(x1 - 0.05 * (x1 - x0), y1 - 0.11 * (y1 - y0)), ha="center", fontsize=9, fontweight="bold",
                    arrowprops=dict(arrowstyle="-|>", color="k", lw=1.4), zorder=20)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_xlabel("")
    ax.set_ylabel("")
    for s in ax.spines.values():
        s.set_linewidth(0.6)


def densest_window(gap: gpd.GeoDataFrame, w=1400.0, h=1000.0):
    pts = np.c_[gap.geometry.representative_point().x, gap.geometry.representative_point().y]
    best, arg = -1, None
    for cx, cy in pts[:: max(1, len(pts) // 250)]:
        n = int(((abs(pts[:, 0] - cx) < w / 2) & (abs(pts[:, 1] - cy) < h / 2)).sum())
        if n > best:
            best, arg = n, (cx, cy)
    return (arg[0] - w / 2, arg[1] - h / 2, arg[0] + w / 2, arg[1] + h / 2), best


def map1(S, cfg, odir, ddir):
    cell, L = S["cell"], S["layers"]
    ext = (*cell.bounds[:2], *cell.bounds[2:])
    pad = 150
    ext = (ext[0] - pad, ext[1] - pad, ext[2] + pad, ext[3] + pad)
    zext, nz = densest_window(S["gap"])
    fig, axs = plt.subplots(1, 2, figsize=(13, 7.0), gridspec_kw=dict(width_ratios=[1.0, 1.0], wspace=0.04, left=0.01, right=0.99, top=0.93, bottom=0.14))
    fac = S["fac"]
    fcol = {"school": "#1f78b4", "health": "#d62728", "government": "#6a3d9a"}
    for ax, e, zoom in ((axs[0], ext, False), (axs[1], zext, True)):
        _bg(ax, S, ddir, e)
        gpd.GeoSeries([cell], crs=A.CRS_WORK).boundary.plot(ax=ax, color="#222222", lw=1.3, zorder=3)
        L["roads"].geometry.intersection(cell).plot(ax=ax, color="#555555", lw=0.5 if not zoom else 0.9, zorder=4)
        S["houses_all"].plot(ax=ax, fc="#9a9a9a", ec="none" if not zoom else "#6a6a6a", lw=0.2, zorder=5)
        S["gap"].plot(ax=ax, fc="#ff7f0e", ec="#a04a00" if zoom else "none", lw=0.25, zorder=6)
        for k, c in fcol.items():
            f = fac[fac.facility_type == k]
            if len(f):
                f.plot(ax=ax, marker="*", color=c, edgecolor="k", markersize=(95 if zoom else 38), linewidth=0.5, zorder=8)
        _decor(ax, e, 200 if zoom else 1000)
    # zoom box in (a)
    zb = box(*zext)
    gpd.GeoSeries([zb], crs=A.CRS_WORK).boundary.plot(ax=axs[0], color="k", lw=1.2, zorder=9)
    for ax_ in axs:
        ax_.set_xlabel("")
        ax_.set_ylabel("")
    axs[0].set_title(f"(a) Study window: Adilabad Urban mandal polygon, {cell.area / 1e6:.2f} km$^2$", loc="left")
    axs[1].set_title(f"(b) Zoom: densest cluster of road-gap houses ({nz} gap houses in the box)", loc="left")
    handles = [Line2D([0], [0], color="#222222", lw=1.3, label="Study-area boundary (geoBoundaries ADM3)"), Line2D([0], [0], color="#555555", lw=0.8, label="Existing road (Overture / OSM)"),
               Patch(fc="#9a9a9a", label=f"Building footprint ({len(S['houses_all']):,}; area >= {cfg['village']['min_house_area_m2']} m$^2$, confidence >= {cfg['village']['min_conf']})"),
               Patch(fc="#ff7f0e", label=f"Road-gap house > {cfg['village']['min_dist_to_road_m']} m from a road ({len(S['gap']):,} routing targets)")]
    for k, c in fcol.items():
        handles.append(Line2D([0], [0], marker="*", color="none", markerfacecolor=c, markeredgecolor="k", markersize=10, label=f"Verified facility: {k} ({int((fac.facility_type == k).sum())})"))
    handles += [Patch(fc=WC_COLORS[c], label=f"WorldCover: {n}") for c, n in WC_NAMES.items() if c in (10, 30, 40, 50)]
    fig.legend(handles=handles, loc="lower center", ncol=4, frameon=False, fontsize=7.4)
    fig.suptitle("Adilabad (Tier 1: urban / peri-urban): boundary, existing roads, buildings and facilities", fontsize=11, y=0.985)
    fig.savefig(odir / "figures/map1_study_area.png", dpi=DPI)
    plt.close(fig)
    return zext


def map2(S, main, odir, ddir, zext):
    cell = S["cell"]
    G = main["geoms"]
    rows = {r["plan"]: r for r in main["rows"]}
    ind, two = rows["Independent least-cost routes"], rows["Two-stage shared plan"]
    fig = plt.figure(figsize=(15.5, 8.4))
    gs = fig.add_gridspec(2, 3, width_ratios=[1.0, 1.0, 0.95], wspace=0.03, hspace=0.2, left=0.01, right=0.99, top=0.80, bottom=0.085)
    ext = (cell.bounds[0] - 150, cell.bounds[1] - 150, cell.bounds[2] + 150, cell.bounds[3] + 150)
    spec = [(gs[:, 0], ext, False, "indep", "#1f77b4", "a"), (gs[:, 1], ext, False, "two", "#d62728", "b"), (gs[0, 2], zext, True, "indep", "#1f77b4", "c"), (gs[1, 2], zext, True, "two", "#d62728", "d")]
    for sl, e, zoom, key, color, tag in spec:
        ax = fig.add_subplot(sl)
        _bg(ax, S, ddir, e, alpha=0.5)
        gpd.GeoSeries([cell], crs=A.CRS_WORK).boundary.plot(ax=ax, color="#222222", lw=1.0, zorder=3)
        S["layers"]["roads"].geometry.intersection(cell).plot(ax=ax, color="#8a8a8a", lw=0.5 if not zoom else 0.9, zorder=4)
        S["houses_all"].plot(ax=ax, fc="#c8c8c8", ec="none" if not zoom else "#888888", lw=0.2, zorder=5)
        S["gap"].plot(ax=ax, fc="#ffbf80", ec="none", zorder=6)
        gpd.GeoSeries([g for _, g, _, _ in G[key]], crs=A.CRS_WORK).plot(ax=ax, color=color, lw=1.0 if not zoom else 1.8, alpha=0.9 if key == "two" else 0.4, zorder=7)
        _decor(ax, e, 200 if zoom else 1000, north=(not zoom) or tag == "c")
        r = ind if key == "indep" else two
        name = "Independent least-cost routes" if key == "indep" else "Two-stage shared plan (proposed)"
        if not zoom:
            ax.set_title(f"({tag}) {name}\ntotal {r['total_len_m']:,.0f} m, unique {r['unique_len_m']:,.0f} m\ncost {r['unique_cost']:,.0f} units\n"
                         f"{r['routes_crossing']} routes cross other\nfootprints ({r['len_in_footprints_m']:,.0f} m)", loc="left", fontsize=8)
        else:
            ax.set_title(f"({tag}) {name}\nzoom on the densest road-gap cluster", loc="left", fontsize=8)
    handles = [Line2D([0], [0], color="#1f77b4", lw=2, alpha=0.5, label="Independent routes (every house to a road; overlaps drawn on top of each other)"),
               Line2D([0], [0], color="#d62728", lw=2, label="Two-stage shared network (shared edges counted once)"), Line2D([0], [0], color="#8a8a8a", lw=1, label="Existing road"),
               Patch(fc="#c8c8c8", label="Building footprint"), Patch(fc="#ffbf80", label="Road-gap house (routing target)")]
    fig.legend(handles=handles, loc="lower center", ncol=3, frameon=False, fontsize=8)
    n = len([t for t in main["targets"] if t["kind"] == "HOUSE"])
    fig.suptitle(f"Adilabad: route comparison for {n:,} road-gap houses (cost in ordinal units; footprint penalty mu = 4; planning alternatives, not engineered roads)", fontsize=11, y=0.975)
    fig.savefig(odir / "figures/map2_network_comparison.png", dpi=DPI)
    plt.close(fig)


def fig3(sweep, omis_g, D, odir):
    fig, (a, b) = plt.subplots(1, 2, figsize=(11, 4.4), gridspec_kw=dict(wspace=0.3, left=0.07, right=0.985, top=0.9, bottom=0.14))
    cm = {"centre-in-footprint": "#1f77b4", "buffered 7.1 m": "#2ca02c"}
    off = {("centre-in-footprint", 1.0): (8, 4, "left"), ("centre-in-footprint", 4.0): (8, 4, "left"), ("centre-in-footprint", 20.0): (-8, -24, "right"),
           ("centre-in-footprint", 100.0): (8, 8, "left"), ("buffered 7.1 m", 20.0): (-10, 10, "right"), ("buffered 7.1 m", 100.0): (0, -32, "center")}
    for _, r in sweep.iterrows():
        a.scatter(r.unique_len_m, r.len_in_footprints_m, s=60, c=cm[r.penalty_mode], edgecolor="k", zorder=3)
        dx, dy, ha = off.get((r.penalty_mode, r.mu), (6, 5, "left"))
        a.annotate(f"{'buf. ' if r.penalty_mode.startswith('buf') else ''}mu={r.mu:g}\n{int(r.routes_crossing)} routes", (r.unique_len_m, r.len_in_footprints_m), xytext=(dx, dy), textcoords="offset points", fontsize=7, ha=ha)
    a.set_ylim(700, None)
    a.set_xlabel("Unique network length, houses (m)")
    a.set_ylabel("Route length inside other footprints (m)")
    a.set_title("(a) Footprint-penalty trade-off, Adilabad", loc="left")
    a.grid(True, lw=0.3, color="#e6e6e6")
    a.legend(handles=[Line2D([0], [0], marker="o", color="none", markerfacecolor=c, markeredgecolor="k", label=k) for k, c in cm.items()], frameon=False, fontsize=7.5)
    order = ["omit 10% (random)", "omit 20% (random)", "omit smallest 10%", "omit smallest 25%"]
    boff = {"omit 10% (random)": (10, 14, "left"), "omit smallest 10%": (10, -26, "left"), "omit 20% (random)": (10, 6, "left"), "omit smallest 25%": (-10, 10, "right")}
    for g in order:
        r = omis_g[omis_g.group == g]
        if r.empty:
            continue
        r = r.iloc[0]
        b.errorbar(r.unserved, r.delta_len_pct, yerr=[[r.delta_len_pct - r.delta_min], [r.delta_max - r.delta_len_pct]], fmt="o", color="#1f77b4" if "random" in g else "#d95f02", capsize=3, ms=7, mec="k")
        dx, dy, ha = boff[g]
        b.annotate(f"{g}\n{r.delta_len_pct:+.1f}%, {r.unserved:.0f} unserved", (r.unserved, r.delta_len_pct), xytext=(dx, dy), textcoords="offset points", fontsize=7, ha=ha)
    b.axhline(0, color="#888888", lw=0.7)
    b.set_xlabel("Road-gap houses left without a route (incl. baseline failures)")
    b.set_ylabel("Unique length change vs baseline (%)")
    b.set_title("(b) Omission sensitivity, Adilabad (mean and min-max over 5 seeds)", loc="left")
    b.grid(True, lw=0.3, color="#e6e6e6")
    b.margins(x=0.25, y=0.25)
    fig.savefig(odir / "figures/fig3_sensitivity.png", dpi=DPI)
    plt.close(fig)



# ------------------------------------------------------------------------------------------------ documents
def fetch_geoboundaries_meta(ddir: Path) -> dict:
    out = {}
    for lvl in ("ADM2", "ADM3"):
        f = ddir / f"geoBoundaries-IND-{lvl}-metaData.json"
        if not f.exists():
            dl.http_download(f"https://media.githubusercontent.com/media/wmgeolab/geoBoundaries/main/releaseData/gbOpen/IND/{lvl}/geoBoundaries-IND-{lvl}-metaData.json", f)
        out[lvl] = json.loads(f.read_text())
    return out


def build_sources(cfg, S, ddir) -> list:
    v, rel = cfg["village"], cfg["overture_release"]
    gm = fetch_geoboundaries_meta(ddir)
    ov = "https://overturemaps-us-west-2.s3.amazonaws.com/release/{rel}/theme={theme}/type={typ}/"
    src = []
    adm3 = dl.CACHE / "gb_IND_ADM3.geojson"
    src.append(Source("boundary", "study-area polygon (clips every layer and the planning grid)", "geoBoundaries gbOpen (wmgeolab); original source Pathways Data Pvt. Ltd. / lgdirectory.gov.in",
                      dl.GB_BASE.format(lvl="ADM3"), f"gbOpen IND ADM3, boundary year {gm['ADM3']['boundaryYear']}, built {gm['ADM3']['buildDate']}",
                      f"{gm['ADM3']['boundaryLicense']} (geoBoundaries metadata JSON)", "polygon (sub-district / mandal)",
                      note="administrative mandal polygon 'Adilabad Urban' as released; may differ from the current municipal limits; district polygon from ADM2 "
                           f"({dl.GB_BASE.format(lvl='ADM2')}, boundary year {gm['ADM2']['boundaryYear']})").fingerprint(adm3))
    src.append(Source("boundary (metadata)", "licence and provenance record of the boundary layer", "geoBoundaries", "https://media.githubusercontent.com/media/wmgeolab/geoBoundaries/main/releaseData/gbOpen/IND/ADM3/geoBoundaries-IND-ADM3-metaData.json",
                      "", "ODbL 1.0").fingerprint(ddir / "geoBoundaries-IND-ADM3-metaData.json"))
    lic_note = "licence per the Overture Maps documentation (docs.overturemaps.org/attribution), NOT re-verified from this sandbox (host unreachable); the per-record `license` field is empty"
    src.append(Source("roads", "existing road network = routing goal set", "Overture Maps Foundation (transportation theme; OSM-derived)", ov.format(rel=rel, theme="transportation", typ="segment"),
                      rel, "ODbL 1.0 (OpenStreetMap-derived); " + lic_note, "vector, subtype=road", note="all road classes inside the window are kept (Damarakunta used the TGRAC road layer)")
               .fingerprint(ddir / "roads.gpkg", len(S["layers"]["roads"])))
    bld = S["layers"]["buildings"]
    src.append(Source("buildings", "footprints: house targets and footprint-penalty layer", "Overture Maps Foundation (buildings theme): OpenStreetMap + Google Open Buildings v3 polygons",
                      ov.format(rel=rel, theme="buildings", typ="building"), f"{rel}; source records: Google Open Buildings version 2024-04-16; OpenStreetMap update years 2018-2026",
                      "per record: OpenStreetMap = ODbL 1.0; Google Open Buildings = CC BY 4.0 / ODbL 1.0; " + lic_note, "vector polygons",
                      note=f"{len(bld):,} polygons in the window: {int((bld.dataset == 'OpenStreetMap').sum()):,} OpenStreetMap, {int((bld.dataset == 'Google Open Buildings').sum()):,} Google; "
                           "every Overture record here has exactly one source").fingerprint(ddir / "buildings.gpkg", len(bld)))
    src.append(Source("facilities", "public facilities (schools, health, government) as extra targets", "Overture Maps Foundation (places theme)", ov.format(rel=rel, theme="places", typ="place"),
                      rel, "CDLA-Permissive-2.0; " + lic_note, "points", note="places within 4 km of the window; school / health / government categories selected, then verified (see verified_facilities.csv)")
               .fingerprint(ddir / "places_4km.gpkg", len(S["layers"]["places_4km"])))
    src.extend(S["prep_meta"]["sources"])
    src[-2].note = "Overture-independent; windowed read of the public AWS COG tile(s)"
    src.append(Source("slope", "slope term and the > 25 deg hard block", "derived from the Copernicus DEM (Sobel on the 30 m DEM, bilinear to 10 m: Stage B method)", "derived", "", "same as the DEM", "10 m",
                      ).fingerprint(ddir / "slope_10m.tif"))
    return src


def write_docs(cfg, S, res, main, tabs, odir, ddir):
    v = cfg["village"]
    cell, gap, houses, fac_all = S["cell"], S["gap"], S["houses_all"], S["fac_all"]
    D = damarakunta()
    # --- manifest
    sources = build_sources(cfg, S, ddir)
    write_manifest(sources, odir / "input_manifest.csv")
    # --- facilities
    L = S["layers"]
    ru = L["roads"].geometry.intersection(cell).union_all()
    f = fac_all[fac_all.inside_window].copy()
    f["dist_to_nearest_road_m"] = f.geometry.distance(ru).round(1)
    cols = ["id", "name", "facility_type", "taxonomy_primary", "confidence", "dataset", "addr_locality", "lon", "lat", "x_epsg32644", "y_epsg32644",
            "dist_to_nearest_footprint_m", "footprint_within_20m", "dist_to_nearest_road_m", "status", "manual_exclusion"]
    f[cols].rename(columns={"confidence": "overture_confidence"}).sort_values(["status", "facility_type", "name"]).to_csv(odir / "verified_facilities.csv", index=False, lineterminator="\n")
    # --- building summary
    b = S["classified"]
    bs = b.groupby(["dataset", "quality_class"]).agg(polygons=("id", "size"), median_area_m2=("area_m2", "median")).round(1).reset_index()
    bs.to_csv(odir / "building_extraction_summary.csv", index=False, lineterminator="\n")
    with rasterio.open(ddir / "worldcover_10m.tif") as s_:
        lc, T = s_.read(1), s_.transform
    rc = [rasterio.transform.rowcol(T, p.x, p.y) for p in houses.geometry.representative_point()]
    bu = float(np.mean([lc[r, c_] == 50 for r, c_ in rc]))
    rc = [rasterio.transform.rowcol(T, p.x, p.y) for p in gap.geometry.representative_point()]
    bu_gap = float(np.mean([lc[r, c_] == 50 for r, c_ in rc]))
    dam = pd.read_csv(B / "PRIMARY_RUN_S2_fac_C0_s25_final_x4/scenario_targets.csv")
    dam = dam[dam.planner_key.astype(str).str.startswith("C")]
    strat, sweep, omis_g = tabs["strat"], tabs["sweep"], tabs["omis_g"]
    rows = {r["plan"]: r for r in main["rows"]}
    two, ind, lo, ro, st = rows["Two-stage shared plan"], rows["Independent least-cost routes"], rows["Length-only control"], rows["Roads-only shared reference"], rows["Straight line"]
    fr = {r["plan"]: r for r in main["facility_rows"]}
    nH = two["targets_total"]
    rho = lambda r: 100 * (ind["unique_len_m"] - r["unique_len_m"]) / ind["unique_len_m"]
    # --- comparison with Damarakunta
    x4, x1, t4 = D["x4"], D["x1"], D["t4"]
    M = {"indep": "Independent least-cost routes to the roads", "lenonly": "Length-only control (shortest distance, same constraints)",
         "roads": "Roads-only shared reference (houses attach to roads only)", "plan": "Two-stage network-aware plan (proposed)", "line": "Straight line (no terrain, 2 targets infeasible)"}
    dp = x4.loc[M["plan"]]
    d_int = x4.loc[M["indep"]]
    base = D["base"]
    def dam_omit(name, routed_col="house_targets_routed"):
        r = t4[t4.perturbation == name]
        return dict(delta=100 * (r.unique_len_m.mean() - base) / base, unserved=163 - r[routed_col].mean(), routed=r[routed_col].mean(), rho=r.saving_vs_independent_pct.mean())
    def a_omit(group):
        r = omis_g[omis_g.group == group]
        return None if r.empty else r.iloc[0]
    sw = sweep.set_index(["penalty_mode", "mu"])
    s1, s4 = sw.loc[("centre-in-footprint", 1.0)], sw.loc[("centre-in-footprint", 4.0)]
    d1 = x1.loc[M["plan"]]
    cmp = [
        ("Settlement tier", "rural village (dispersed)", "urban / peri-urban mandal (dense)"),
        ("Study area (km2)", "18.47 (TGRAC village polygon)", f"{cell.area / 1e6:.2f} (geoBoundaries ADM3 'Adilabad Urban')"),
        ("Building source", "StrongDINOv2Seg candidates on 0.6 m Esri imagery (278 polygons, 165 inside)", f"Overture open footprints: OSM + Google Open Buildings ({len(S['classified']):,} polygons)"),
        ("Footprints used for the penalty layer", "165 candidates inside the boundary (all classes)", f"{len(houses):,} polygons (area >= {v['min_house_area_m2']} m2, confidence >= {v['min_conf']})"),
        ("House targets", "163 (all candidates)", f"{nH:,} (houses > {v['min_dist_to_road_m']} m from a road, = {100 * nH / len(houses):.1f}% of footprints)"),
        ("Median target footprint area (m2)", f"{dam.area_m2.median():.1f}", f"{gap.area_m2.median():.1f}"),
        ("Median target distance to nearest road (m)", f"{dam.dist_to_road_m.median():.1f}", f"{gap.dist_to_road_m.median():.1f}"),
        ("Facilities planned", "5 (TGRAC schools, sub-centre, GP HQ points)", f"{len(S['fac'])} verified of {int(fac_all.inside_window.sum())} candidates (Overture places)"),
        ("Houses routed", "163 of 163", f"{two['targets_routed']} of {nH}"),
        ("Independent routes: total / unique (m)", f"{d_int.total_len_m:,.1f} / {d_int.unique_len_m:,.1f}", f"{ind['total_len_m']:,.1f} / {ind['unique_len_m']:,.1f}"),
        ("Length-only control: unique (m)", f"{x4.loc[M['lenonly']].unique_len_m:,.1f}", f"{lo['unique_len_m']:,.1f}"),
        ("Roads-only shared reference: unique (m)", f"{x4.loc[M['roads']].unique_len_m:,.1f}", f"{ro['unique_len_m']:,.1f}"),
        ("Two-stage shared plan: unique (m)", f"{dp.unique_len_m:,.1f}", f"{two['unique_len_m']:,.1f}"),
        ("Saving vs independent (%)", f"{dp.reduction_vs_independent_unique_pct:.1f}", f"{rho(two):.1f}"),
        ("Roads-only shared saving (%)", f"{x4.loc[M['roads']].reduction_vs_independent_unique_pct:.1f}", f"{rho(ro):.1f}"),
        ("Length-only control vs independent (%)", f"{x4.loc[M['lenonly']].reduction_vs_independent_unique_pct:.1f}", f"{rho(lo):.1f}"),
        ("Unique length per routed house (m)", f"{dp.unique_len_m / 163:.1f}", f"{two['unique_len_m'] / two['targets_routed']:.1f}"),
        ("Routes crossing other footprints (two-stage)", f"{int(dp.routes_crossing_other_footprints)} of 163 ({100 * dp.routes_crossing_other_footprints / 163:.0f}%)", f"{two['routes_crossing']} of {two['targets_routed']} ({100 * two['routes_crossing'] / two['targets_routed']:.0f}%)"),
        ("Length inside other footprints (m)", f"{dp.len_in_other_footprints_m:,.1f}", f"{two['len_in_footprints_m']:,.1f}"),
        ("mu = 1 -> 4: unique length change (%)", f"{100 * (dp.unique_len_m - d1.unique_len_m) / d1.unique_len_m:+.1f}", f"{100 * (s4.unique_len_m - s1.unique_len_m) / s1.unique_len_m:+.1f}"),
        ("mu = 1 -> 4: routes crossing (n)", f"{int(d1.routes_crossing_other_footprints)} -> {int(dp.routes_crossing_other_footprints)}", f"{int(s1.routes_crossing)} -> {int(s4.routes_crossing)}"),
        ("Facility phase: unique length (m) / facilities", f"{x4.loc['Facilities (5), network-aware'].unique_len_m:,.1f} / 5", f"{fr['Facilities: two-stage']['unique_len_m']:,.1f} / {fr['Facilities: two-stage']['targets_routed']}"),
    ]
    for lab, key, pretty in (("omit 10% (random)", "omit 10%", "10% random omission"), ("omit 20% (random)", "omit 20%", "20% random omission"), ("omit smallest 10%", "omit smallest 10%", "smallest-10% omission"),
                             ("omit smallest 25%", "omit smallest 25%", "smallest-25% omission")):
        d = dam_omit(key)
        a = a_omit(lab)
        if a is not None:
            cmp.append((f"{pretty}: length change (%) / households unserved", f"{d['delta']:+.1f} / {d['unserved']:.0f} of 163", f"{a.delta_len_pct:+.1f} / {a.unserved:.0f} of {len(gap)}"))
    cdf = pd.DataFrame(cmp, columns=["metric", "Damarakunta (Phase 1 / Stage B, village)", "Adilabad (urban / peri-urban window)"])
    cdf.to_csv(odir / "comparison_vs_damarakunta.csv", index=False, lineterminator="\n")
    pickle.dump(dict(cdf=cdf, bu=bu, bu_gap=bu_gap), open(ddir / "docs_state.pkl", "wb"))
    (odir / "comparison_vs_damarakunta.md").write_text("# Adilabad vs Damarakunta\n\nDamarakunta numbers are read from `DELIVERABLES_DAMARAKUNTA_STAGE_B/03_RESULTS_TABLES/` (read-only).\n\n" + md_table(cdf, "{:,.1f}") + "\n", encoding="utf-8")
    return dict(bu=bu, bu_gap=bu_gap, bs=bs, cdf=cdf, sources=sources, fac=f)

def write_markdown(cfg, S, res, main, tabs, info, odir, ddir):
    v, cell, gap, houses = cfg["village"], S["cell"], S["gap"], S["houses_all"]
    fac_all, fac = S["fac_all"], S["fac"]
    f_in = fac_all[fac_all.inside_window]
    rec = S["rec"]
    cx, cy = cell.centroid.x, cell.centroid.y
    c_ll = gpd.GeoSeries([cell.centroid], crs=A.CRS_WORK).to_crs(4326).iloc[0]
    b = S["classified"]
    nb = len(b)
    src = info["sources"]
    main_rows = {r["plan"]: r for r in main["rows"]}
    two = main_rows["Two-stage shared plan"]
    rho_main = 100 * (main_rows['Independent least-cost routes']['unique_len_m'] - two['unique_len_m']) / main_rows['Independent least-cost routes']['unique_len_m']
    d_ = tabs['defs'].copy()
    prim = dict(min_dist_to_road_m=float(v['min_dist_to_road_m']), house_targets=two['targets_total'], routed=two['targets_routed'], unique_len_m=two['unique_len_m'],
                independent_unique_len_m=main_rows['Independent least-cost routes']['unique_len_m'], saving_vs_independent_pct=round(rho_main, 1), routes_crossing=two['routes_crossing'],
                len_in_footprints_m=two['len_in_footprints_m'], failed=len(main['fails']), unique_len_per_house_m=round(two['unique_len_m'] / two['targets_total'], 1))
    defs_tab = pd.concat([d_, pd.DataFrame([prim])]).sort_values('min_dist_to_road_m').reset_index(drop=True)
    defs_tab.to_csv(odir / 'target_definition_sensitivity.csv', index=False, lineterminator='\n')
    src_table = pd.DataFrame([dict(layer=x.layer, provider=x.provider, endpoint=x.url if len(x.url) < 160 else x.url[:157] + "...", release=x.release, licence=x.licence,
                                   resolution=x.resolution, sha256=x.sha256[:16] + "..." if x.sha256 else "", rows=x.rows) for x in src])
    cls = b.groupby("quality_class").size().to_dict()
    f_tab = f_in.groupby(["facility_type", "status"]).size().unstack(fill_value=0)
    main_rows = {r["plan"]: r for r in main["rows"]}
    two = main_rows["Two-stage shared plan"]
    audit = f"""# Data-source audit: Adilabad (Tier 1, urban / peri-urban) - Contribution 3, village 1

Everything below was read, hashed and counted by `python -m src.multivillage.run --village adilabad_urban`. Nothing here is field-verified.
The Phase 1 / Stage B deliverables (`DELIVERABLES_DAMARAKUNTA_STAGE_B/`, git tree `4e5cedcefcfb9231074a10667e8050f4650d8766`) are read-only inputs to the comparison.

## 1. Study window

| item | value |
|---|---|
| Name | {v['name']} |
| Administrative unit | {v['mandal']} mandal, {v['district']} district, {v['state']} (geoBoundaries ADM3 shape `{rec['shape_id']}`) |
| Why this window | the mandal polygon is {cell.area / 1e6:.2f} km2, inside the requested 15-20 km2 range and close to Damarakunta (18.47 km2); it is an administrative polygon, not a hand-drawn box |
| Centroid (WGS84) | {c_ll.y:.5f} N, {c_ll.x:.5f} E |
| Bounding box, EPSG:32644 (x_min, y_min, x_max, y_max, m) | {cell.bounds[0]:.1f}, {cell.bounds[1]:.1f}, {cell.bounds[2]:.1f}, {cell.bounds[3]:.1f} |
| Bounding box, WGS84 (lon_min, lat_min, lon_max, lat_max) | {rec['bounds_wgs84'][0]:.5f}, {rec['bounds_wgs84'][1]:.5f}, {rec['bounds_wgs84'][2]:.5f}, {rec['bounds_wgs84'][3]:.5f} |
| Area | {cell.area / 1e6:.2f} km2 |
| Planning grid | {S['prep_meta']['shape'][1]} x {S['prep_meta']['shape'][0]} cells at 10 m; {S['prep_meta']['inside_cells']:,} cells inside the polygon; {100 * S['prep_meta']['blocked_inside']:.2f}% of them blocked (water, slope > 25 degrees) |

Caveat: the geoBoundaries ADM3 layer is the 2018 Local Government Directory release; it may differ from the municipal limits in use today. The window therefore contains the urban core plus a rural/peri-urban fringe (about {100 * (1 - (lc_share(S, ddir))):.0f}% of cells are not WorldCover built-up).

## 2. Input layers, direct endpoints, licences, hashes

{md_table(src_table, "{:,.0f}")}

Full machine-readable version: `input_manifest.csv` (complete SHA-256 values, byte sizes, access time, notes).
Overture layers are read from the pinned release `{cfg['overture_release']}` by an anonymous S3 query (the endpoint above); the hash is that of the clipped extract written to `data/villages/{v['id']}/`, because a query result has no single file hash.
Licence status: ESA WorldCover (CC BY 4.0) and the Copernicus DEM are as stated by their providers; the geoBoundaries licence (ODbL 1.0) was read from its own metadata JSON; the Overture licences are from the Overture documentation, which could not be opened from this sandbox, so they are flagged "not re-verified". OSM-derived layers are ODbL (share-alike, attribution to OpenStreetMap contributors).
Not used: TGRAC (the Damarakunta road, facility and boundary source), Survey of India / BharatMaps, OSM Overpass / Nominatim, Zenodo and the Google Open Buildings site: none is reachable from the execution sandbox (checked), so no value was taken from them.

## 3. Facilities (schools, health, government offices)

Source: Overture `places` within 4 km of the window ({int(fac_all.shape[0])} school/health/government candidates, {len(f_in)} inside the window). Overture does not say whether a school or clinic is public, so private ones are included; anganwadis and sub-centres do not exist as categories.
Verification (the Damarakunta rules): inside the window; a detected footprint within 20 m of the point; and a manual review for mis-geocoded records (several records carry Pakistani place names, e.g. "Faisalabad", "Umerkot", "Jaranwala", "Mirpurkhas", and are excluded).

{md_table(f_tab.reset_index(), "{:,.0f}")}

Result: **{len(fac)} verified facilities** are used as targets in the facility phase ({int((fac.facility_type == 'school').sum())} schools, {int((fac.facility_type == 'health').sum())} health, {int((fac.facility_type == 'government').sum())} government). Every candidate with coordinates, distance to the nearest footprint and the reason for any exclusion is in `verified_facilities.csv`.
Unlike the Damarakunta anganwadi (371 m from the nearest footprint), the only candidate without a footprint within 20 m was a school ("Vivekananda High School", 20.5 m: it misses the rule by 0.5 m); in a dense urban fabric the 20 m test is weak evidence because nearly every point is within 20 m of some footprint.

## 4. Building footprints: which method and why

StrongDINOv2Seg inference was **not** run for Adilabad, for three documented reasons: (i) the model weights are not in the repository and their location was never recorded (the Stage B documentation says the same: "segmentation is not re-run because the model-weight location is not recorded"); (ii) the 0.6 m Esri World Imagery used for Damarakunta has an unresolved licence for derived products and cannot be fetched from this sandbox; (iii) no open sub-metre imagery is reachable (Sentinel-2, 10 m, cannot resolve houses). The brief allows verified open footprints in that case, so the footprints are the Overture buildings layer.

| item | value |
|---|---|
| Footprint polygons in the window | {nb:,} (OpenStreetMap {int((b.dataset == 'OpenStreetMap').sum()):,}; Google Open Buildings v3, version 2024-04-16: {int((b.dataset != 'OpenStreetMap').sum()):,}); every Overture record has exactly one source, so there are no duplicate polygons between the two |
| OSM edit years | mostly 2018 (the OSM building import), see `buildings.gpkg` |
| Confidence | Google polygons carry a model confidence (median {b[b.dataset != 'OpenStreetMap'].confidence.median():.2f}); OSM polygons are human-mapped and treated as 1.0 |
| Quality classes (heuristic, not verified) | {', '.join(f'{k} {v_:,}' for k, v_ in sorted(cls.items()))} |
| House footprints (area >= {v['min_house_area_m2']} m2, confidence >= {v['min_conf']}) | {len(houses):,} |
| Median footprint area | {houses.area_m2.median():.1f} m2 (Damarakunta candidates: 235.8 m2) |
| Proxy agreement check | not applicable in the Damarakunta sense (no independent detector to compare with). Instead: {100 * info['bu']:.1f}% of all house points, and {100 * info['bu_gap']:.1f}% of road-gap house points, fall on a WorldCover built-up cell - a land-cover consistency check, not an accuracy figure |

Consequence: footprints include non-residential buildings (no use type exists), so "house" means "building footprint of at least {v['min_house_area_m2']} m2" and the road-gap set contains some large structures (e.g. long barrack-like blocks visible on the maps).

## 5. How the Stage B workflow was applied, and every deviation

| Stage B step | Damarakunta | Adilabad (this run) | deviation |
|---|---|---|---|
| 1 boundary, roads, facilities | TGRAC village polygon, TGRAC roads and facilities | geoBoundaries mandal polygon, Overture roads (OSM) and places | different sources (TGRAC unreachable) |
| 2 land cover, DEM, slope | WorldCover 10 m; ~30 m DEM (SRTM-type, source unrecorded); Sobel slope | WorldCover 10 m; Copernicus GLO-30 30 m; Sobel slope (same method) | DEM product (documented RMSE 2.3 m between the two over Damarakunta) |
| 3 buildings | StrongDINOv2Seg + OpenCV instance extraction, 163 targets | open footprints (OSM + Google) | method (see section 4) |
| 4 cost surface | WorldCover resistance + slope term, slope > 25 degrees blocked, footprint penalty mu = 4 on cells whose centre lies inside a footprint | identical recipe and parameters (`configs/multivillage/common.yaml`) | none |
| 5 planner | `scripts/plan_network_v2.py` | the same file, imported unchanged; K = 3, passes = 2, snap 30 m, search limit 1,500 m, attach tolerance 15 m | none |
| targets | every candidate inside the boundary (163; 48 within 10 m of a road) | only buildings farther than {v['min_dist_to_road_m']} m from a road ({len(gap):,} of {len(houses):,}) | **dense fabric**: 75% of footprints are within 14 m of a road, and the planner's cost grows with the square of the number of targets (874 targets: about 6 minutes per plan; the full 2,190 houses > 20 m: reported in section 6). 30 m is the planner's own snap distance |
| facility phase | 5 facilities planned first, separately | {len(fac)} verified facilities planned in a separate phase | more facilities |
| sensitivity | mu = 1, 4 and buffered 20, 100, 1000; random and size-based omissions | mu = 1, 4, 20, 100 (plain), buffered 20 and 100; 10% and 20% random omission x 5 seeds, smallest 10% / 25% | seeds are 1-5 (Stage B's seeds are not recorded) |

## 6. Results at a glance

Two-stage shared plan: {two['unique_len_m']:,.0f} m of new corridor for {two['targets_routed']} of {two['targets_total']} road-gap houses, {rho_main:.1f}% less unique length than independent least-cost routes (Damarakunta: 24.9%). The full comparison with the four baselines is in `routing_strategy_comparison.csv`, the Damarakunta side-by-side in `comparison_vs_damarakunta.md`.

Sensitivity of the headline saving to the target definition (houses farther than D metres from an existing road; D = 30 m is the primary run):

{md_table(defs_tab, "{:,.1f}")}

## 7. Limitations specific to this run

* The study window is an administrative mandal polygon, not a revenue-village boundary; Overture/OSM roads and buildings are open crowd-sourced layers of unverified completeness (the OSM buildings are mostly from the 2018 import).
* Targets are building footprints of any use; schools, clinics and offices are not separated from houses in the road-gap set.
* The facility list comes from a commercial-places layer with visible geocoding errors; only a manual review separates the obvious ones, and private/public status is unknown.
* Costs are ordinal units, not rupees; routes are planning alternatives, not engineered roads; no field validation exists.
* The omission scenarios are synthetic removals of open footprints, not measured detection errors, and the footprints are not StrongDINOv2Seg output, so these results show how the Stage B planner behaves on a different building source, not how the segmenter would perform in Adilabad.
"""
    (odir / "00_DATA_SOURCE_AUDIT.md").write_text(audit, encoding="utf-8")
    return audit


def lc_share(S, ddir):
    with rasterio.open(ddir / "worldcover_10m.tif") as s_:
        lc = s_.read(1)
    from rasterio.features import rasterize
    inside = rasterize([(S["cell"], 1)], out_shape=lc.shape, transform=s_.transform, fill=0, all_touched=False, dtype="uint8").astype(bool)
    return float((lc[inside] == 50).mean())


# ------------------------------------------------------------------------------------------------ main
def md_table(df: pd.DataFrame, floatfmt="{:,.1f}") -> str:
    cols = list(df.columns)
    out = ["| " + " | ".join(cols) + " |", "|" + "|".join(["---"] * len(cols)) + "|"]
    for _, r in df.iterrows():
        out.append("| " + " | ".join("" if (isinstance(v, float) and np.isnan(v)) else (floatfmt.format(v) if isinstance(v, (float, np.floating)) else str(v)) for v in r) + " |")
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--village", required=True)
    a = ap.parse_args(argv)
    cfg = A.load_cfg(a.village)
    ddir, odir = A.data_dir(cfg), out_dir(cfg)
    S, res, main_out = load(cfg)
    D = damarakunta()
    strat = strategies_table(main_out)
    strat.to_csv(odir / "routing_strategy_comparison.csv", index=False, lineterminator="\n")
    sweep = sweep_table(res)
    base = float(strat.loc[strat.strategy == "Two-stage shared plan", "unique_len_m"].iloc[0])
    rows, omis_g = omission_table(res, base, len(S["gap"]))
    defs = pd.DataFrame([r["row"] for r in res if r["spec"]["kind"] == "def"]).sort_values("min_dist_to_road_m")
    sweep.to_csv(odir / "penalty_sensitivity.csv", index=False, lineterminator="\n")
    rows.to_csv(odir / "omission_runs.csv", index=False, lineterminator="\n")
    omis_g.to_csv(odir / "omission_summary.csv", index=False, lineterminator="\n")
    defs.to_csv(odir / "target_definition_sensitivity.csv", index=False, lineterminator="\n")
    zext = map1(S, cfg, odir, ddir)
    map2(S, main_out, odir, ddir, zext)
    fig3(sweep, omis_g, D, odir)
    tabs = dict(strat=strat, sweep=sweep, omis_g=omis_g, defs=defs, zext=zext)
    pickle.dump(tabs, open(ddir / "report_tables.pkl", "wb"))
    info = write_docs(cfg, S, res, main_out, tabs, odir, ddir)
    write_markdown(cfg, S, res, main_out, tabs, info, odir, ddir)
    print("tables and figures written to", odir)


if __name__ == "__main__":
    main()
