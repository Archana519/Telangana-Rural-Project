#!/usr/bin/env python
"""Adilabad Urban: the five-map publication series, laid out like the Damarakunta Stage B maps
(DELIVERABLES_DAMARAKUNTA_STAGE_B/02_FINAL_MAPS/final_maps_1_to_5).

    map1_imagery_boundary_roads          0.6 m Esri imagery, study polygon, existing roads
    map2_footprints_facilities_latlon    detected built-up units + verified facilities, callouts with latitude / longitude
    map3_terrain_cost_landcover_slope    WorldCover, slope, composite cost surface C0, blocked cells
    map4_alternatives_vs_network         independent least-cost (Stage A first choice) routes vs the final shared network, window + central zoom
    map5_village_detail_shared_paths     central zone: primary shared network (mu = 4) vs building-avoiding network (buffer 7.1 m, mu = 100), crossings highlighted

Inputs (all produced by scripts/run_adilabad_end_to_end.py on your PC; none of them is in the git repository because the tiles, mosaic and
state files are git-ignored):
    data/villages/adilabad_urban/state_segmentation.pkl   footprints, facilities, routes of the segmentation run
    data/villages/adilabad_esri/aligned/adilabad_esri_highres_mosaic_0p6m.tif   the Esri mosaic (maps 1, 2, 4, 5; without it the maps use the land-cover background)
Output: DELIVERABLES_CONTRIBUTION_3_MULTI_VILLAGE/01_ADILABAD_SEGMENTATION/final_maps_1_to_5/*.png

    python scripts\\make_adilabad_map_series.py                      # all five maps
    python scripts\\make_adilabad_map_series.py --maps 2 5           # selected maps
    python scripts\\make_adilabad_map_series.py --out-dir D:\\maps    # elsewhere (the self-test uses this)

Map 5 needs one extra planner run (building-avoiding network: footprints buffered by 7.1 m, penalty 100); it is cached next to the state file.
Every imagery panel carries the credit line "Basemap imagery: Esri, Maxar, Earthstar Geographics, and the GIS User Community."
Costs are ordinal planning units; all routes are planning alternatives, not engineered roads.
"""
from __future__ import annotations

import argparse
import pickle
import sys
from pathlib import Path

import geopandas as gpd
import matplotlib
import numpy as np
import pandas as pd
import rasterio
from matplotlib.colors import ListedColormap
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from pyproj import Transformer
from rasterio.windows import from_bounds
from shapely.geometry import box
from shapely.ops import unary_union

matplotlib.use("Agg")
import matplotlib.pyplot as plt                                    # noqa: E402

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from src.multivillage import acquire as A, pipeline as PL, prepare as P      # noqa: E402

CRS = "EPSG:32644"
CREDIT = "Basemap imagery: Esri, Maxar, Earthstar Geographics, and the GIS User Community."
QCOL = {"PLAUSIBLE": "#2ca02c", "REVIEW": "#ffbf00", "UNRESOLVED_MERGE": "#d62728"}
FCOL = {"school": "#1f78b4", "health": "#e31a1c", "government": "#6a3d9a"}
FMARK = {"school": "*", "health": "P", "government": "s"}
WC = {10: ("#2e7d32", "Tree cover"), 20: ("#8bc34a", "Shrubland"), 30: ("#d4e157", "Grassland"), 40: ("#ffb000", "Cropland"), 50: ("#d62728", "Built-up"),
      60: ("#a0a0a0", "Bare / sparse"), 80: ("#1f78d1", "Water")}
TO_WGS = Transformer.from_crs(CRS, "EPSG:4326", always_xy=True)
FROM_WGS = Transformer.from_crs("EPSG:4326", CRS, always_xy=True)


# ------------------------------------------------------------------------------------------------ helpers
class Ctx:
    def __init__(self, a):
        self.cfg = A.load_cfg("adilabad_urban")
        self.ddir = A.data_dir(self.cfg)
        sp = Path(a.state) if a.state else self.ddir / "state_segmentation.pkl"
        if not sp.exists():
            sys.exit(f"{sp} not found: run scripts/run_adilabad_end_to_end.py --stage route first")
        self.state_path = sp
        self.S = pickle.load(open(sp, "rb"))
        self.mosaic = Path(a.mosaic) if a.mosaic else REPO / "data/villages/adilabad_esri/aligned/adilabad_esri_highres_mosaic_0p6m.tif"
        self.imagery = self.mosaic.exists() and not a.no_imagery
        self.out = Path(a.out_dir) if a.out_dir else REPO / "DELIVERABLES_CONTRIBUTION_3_MULTI_VILLAGE/01_ADILABAD_SEGMENTATION/final_maps_1_to_5"
        self.out.mkdir(parents=True, exist_ok=True)
        S = self.S
        self.cell = S["cell"]
        self.roads = S["layers"]["roads"].geometry.intersection(self.cell)
        self.main = next(r for r in S["results"] if r["spec"]["kind"] == "main")["out"]
        self.dpi = a.dpi
        if not self.imagery:
            print("NOTE: no imagery mosaic -> land-cover background (maps are NOT satellite maps)")

    def prep(self):
        if not hasattr(self, "_prep"):
            self._prep = P.prepare_rasters(self.cfg, self.cell, self.ddir, log=lambda *a: None)
            self._cost, self._inside = P.cost_surface(self.cfg, self._prep, self.cell)
        return self._prep, self._cost, self._inside


def ticks(ax, ext, n=3):
    """Latitude / longitude tick labels on a projected (EPSG:32644) axis, as on the Damarakunta maps."""
    x0, y0, x1, y1 = ext
    lon0, lat0 = TO_WGS.transform(x0, y0)
    lon1, lat1 = TO_WGS.transform(x1, y1)
    step = 0.005 if (lon1 - lon0) < 0.05 else 0.01
    lons = np.arange(np.ceil(lon0 / step) * step, lon1, step)[: 6]
    lats = np.arange(np.ceil(lat0 / step) * step, lat1, step)[: 6]
    ax.set_xticks([FROM_WGS.transform(l, (lat0 + lat1) / 2)[0] for l in lons])
    ax.set_xticklabels([f"{l:.3f}°E" for l in lons], fontsize=6)
    ax.set_yticks([FROM_WGS.transform((lon0 + lon1) / 2, l)[1] for l in lats])
    ax.set_yticklabels([f"{l:.3f}°N" for l in lats], fontsize=6, rotation=90, va="center")
    ax.grid(color="w", alpha=0.25, lw=0.4)
    ax.tick_params(length=2)
    ax.set_xlabel(""); ax.set_ylabel("")


def decor(ax, ext, scale_m, north=True):
    x0, y0, x1, y1 = ext
    sx, sy = x0 + 0.04 * (x1 - x0), y0 + 0.05 * (y1 - y0)
    ax.plot([sx, sx + scale_m], [sy, sy], color="k", lw=2.4, zorder=30, solid_capstyle="butt")
    ax.text(sx + scale_m / 2, sy + 0.015 * (y1 - y0), f"{scale_m / 1000:g} km" if scale_m >= 1000 else f"{scale_m:g} m", ha="center", va="bottom", fontsize=7, zorder=31,
            bbox=dict(fc="w", ec="none", alpha=0.8, pad=1))
    ax.set_xlabel(""); ax.set_ylabel("")
    if north:
        ax.annotate("N", xy=(x1 - 0.05 * (x1 - x0), y1 - 0.03 * (y1 - y0)), xytext=(x1 - 0.05 * (x1 - x0), y1 - 0.12 * (y1 - y0)), ha="center", fontsize=9, fontweight="bold",
                    arrowprops=dict(arrowstyle="-|>", color="k", lw=1.4), zorder=31, bbox=dict(fc="w", ec="none", alpha=0.7, pad=1))


def background(ctx, ax, ext, alpha=1.0, max_px=2200):
    """Esri imagery window (decimated) or, without a mosaic, the WorldCover land cover."""
    if ctx.imagery:
        with rasterio.open(ctx.mosaic) as s:
            win = from_bounds(*ext, transform=s.transform).round_offsets().round_lengths().intersection(rasterio.windows.Window(0, 0, s.width, s.height))
            sc = max(1.0, max(win.width, win.height) / max_px)
            arr = s.read([1, 2, 3], window=win, out_shape=(3, max(1, int(win.height / sc)), max(1, int(win.width / sc))), resampling=rasterio.enums.Resampling.average)
            b = rasterio.windows.bounds(win, s.transform)
        ax.imshow(np.moveaxis(arr, 0, -1), extent=(b[0], b[2], b[1], b[3]), origin="upper", zorder=0, alpha=alpha)
        ax.text(0.995, 0.004, CREDIT, transform=ax.transAxes, ha="right", va="bottom", fontsize=4.6, color="w", zorder=40, bbox=dict(fc="k", alpha=0.45, ec="none", pad=1))
    else:
        prep, _, _ = ctx.prep()
        codes = sorted(WC)
        idx = np.zeros(prep["landcover"].shape, np.uint8)
        for i, c in enumerate(codes):
            idx[prep["landcover"] == c] = i
        mnx, mny, mxx, mxy = prep["bounds"]
        ax.imshow(idx, cmap=ListedColormap([WC[c][0] for c in codes]), vmin=0, vmax=len(codes) - 1, extent=(mnx, mxx, mny, mxy), origin="upper", alpha=0.7, interpolation="nearest", zorder=0)
    ax.set_xlim(ext[0], ext[2]); ax.set_ylim(ext[1], ext[3])


def window_ext(ctx, pad=100):
    b = ctx.cell.bounds
    return (b[0] - pad, b[1] - pad, b[2] + pad, b[3] + pad)


def central_zone(ctx, w=1500.0, h=1100.0):
    """Central urban zone = where the verified facilities are (their median), so the callouts have something to label."""
    f = ctx.S["fac"]
    cx, cy = float(f.geometry.x.median()), float(f.geometry.y.median())
    return (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)


def pick_callouts(ctx, ext, n=7):
    """Major facilities inside `ext` for labelled callouts: every government office, then health, then schools; only records with a
    coordinate not shared with another record (several Overture places carry an identical generic point and would give overlapping labels)."""
    f = ctx.S["fac"].copy()
    key = f.geometry.apply(lambda g: (round(g.x, 1), round(g.y, 1)))
    f = f[key.map(key.value_counts()) == 1]
    f = f[f.geometry.within(box(*ext))]
    f["pr"] = f.facility_type.map({"government": 0, "health": 1, "school": 2})
    f["hosp"] = f.name.str.contains("hospital|medical|institute|health", case=False, regex=True).astype(int)
    f = f.sort_values(["pr", "hosp"], ascending=[True, False]).head(n)
    return f


def callouts(ax, f, ext, col_x=1.04):
    """Boxed labels in one column right of the panel, ordered by latitude so the leader lines do not cross; the label carries the coordinates."""
    f = f.copy()
    f["y"] = f.geometry.y
    f = f.sort_values("y", ascending=False)
    n = len(f)
    ys = np.linspace(0.93, 0.07, max(n, 2))[:n]
    for (_, r), y in zip(f.iterrows(), ys):
        lon, lat = TO_WGS.transform(r.geometry.x, r.geometry.y)
        nm = r["name"] if isinstance(r["name"], str) else "facility"
        nm = nm if len(nm) <= 38 else nm[:36] + "…"
        ax.annotate(f"{nm} ({r.facility_type})\n{lat:.5f}°N, {lon:.5f}°E", xy=(r.geometry.x, r.geometry.y), xycoords="data", xytext=(col_x, y), textcoords="axes fraction",
                    fontsize=6.2, ha="left", va="center", bbox=dict(fc="w", ec=FCOL[r.facility_type], lw=1.0, boxstyle="square,pad=0.25"),
                    arrowprops=dict(arrowstyle="-", color=FCOL[r.facility_type], lw=0.8, shrinkA=0, shrinkB=2), zorder=50, annotation_clip=False)


def plot_fac(ax, f, size, edge="w"):
    for k, c in FCOL.items():
        g = f[f.facility_type == k]
        if len(g):
            ax.scatter(g.geometry.x, g.geometry.y, marker=FMARK[k], s=size, c=c, edgecolors=edge, linewidths=0.6, zorder=20)


def footer(fig, text, credit=True):
    fig.text(0.5, 0.012, text + (" " + CREDIT if credit else ""), ha="center", va="bottom", fontsize=6.2, wrap=True)


NOTE = ("Footprints are automatic StrongDINOv2Seg detections (unvalidated; merged roofs are flagged Unresolved merge), not a census. Planning alternatives, not engineered roads. "
        "Costs are ordinal planning units. EPSG:32644 (UTM 44N).")


# ------------------------------------------------------------------------------------------------ maps
def map1(ctx):
    ext = window_ext(ctx)
    fig, ax = plt.subplots(figsize=(8.2, 10.4))
    background(ctx, ax, ext)
    gpd.GeoSeries([ctx.cell], crs=CRS).boundary.plot(ax=ax, color="#ffeb3b", lw=1.6, zorder=3)
    ctx.roads.plot(ax=ax, color="#00e5ff", lw=0.6, zorder=4)
    decor(ax, ext, 1000); ticks(ax, ext)
    ax.set_title("Map 1. Adilabad Urban: satellite imagery, study boundary and existing roads", fontsize=10)
    ax.legend(handles=[Line2D([0], [0], color="#ffeb3b", lw=2, label="Study-area boundary (geoBoundaries ADM3, 17.75 km²)"), Line2D([0], [0], color="#00e5ff", lw=1, label="Existing roads (Overture / OSM)")],
              loc="upper left", fontsize=7, framealpha=0.9)
    fig.subplots_adjust(0.07, 0.07, 0.97, 0.95)
    footer(fig, "Existing road layer: Overture Maps transportation segments (ODbL 1.0). " + NOTE)
    save(fig, ctx, "map1_imagery_boundary_roads")


def map2(ctx):
    S = ctx.S
    ext, zext = window_ext(ctx), central_zone(ctx)
    cal = pick_callouts(ctx, zext)
    fig = plt.figure(figsize=(16.5, 8.2))
    ax1 = fig.add_axes([0.03, 0.10, 0.24, 0.78]); ax2 = fig.add_axes([0.33, 0.10, 0.37, 0.78])
    for ax, e, zoom in ((ax1, ext, False), (ax2, zext, True)):
        background(ctx, ax, e)
        gpd.GeoSeries([ctx.cell], crs=CRS).boundary.plot(ax=ax, color="#ffeb3b", lw=1.0, zorder=3)
        ctx.roads.plot(ax=ax, color="#00e5ff", lw=0.4 if not zoom else 0.9, zorder=4)
        b = S["classified"]
        for q, c in QCOL.items():
            g = b[b.quality_class_model == q] if "quality_class_model" in b else b[b.quality_class == q]
            if len(g):
                g.plot(ax=ax, fc="none", ec=c, lw=0.3 if not zoom else 0.9, zorder=5)
        plot_fac(ax, S["fac"], 26 if not zoom else 110)
        decor(ax, e, 1000 if not zoom else 200, north=True); ticks(ax, e)
    gpd.GeoSeries([box(*zext)], crs=CRS).boundary.plot(ax=ax1, color="k", lw=1.2, zorder=9)
    ax1.set_title("Whole study window", fontsize=9); ax2.set_title("Central urban zone (zoom)", fontsize=9)
    callouts(ax2, cal, zext)
    n = S["classified"].quality_class_model.value_counts() if "quality_class_model" in S["classified"] else S["classified"].quality_class.value_counts()
    fc = S["fac"].facility_type.value_counts()
    fig.legend(handles=[Patch(fc="none", ec=QCOL["PLAUSIBLE"], label=f"Detected built-up unit: plausible (n={n.get('PLAUSIBLE', 0):,})"), Patch(fc="none", ec=QCOL["REVIEW"], label=f"review (n={n.get('REVIEW', 0):,})"),
                        Patch(fc="none", ec=QCOL["UNRESOLVED_MERGE"], label=f"unresolved merge (n={n.get('UNRESOLVED_MERGE', 0):,})"),
                        *[Line2D([0], [0], marker=FMARK[k], color="none", markerfacecolor=FCOL[k], markeredgecolor="w", markersize=9, label=f"Verified {k} ({fc.get(k, 0)})") for k in FCOL],
                        Line2D([0], [0], color="#00e5ff", lw=1.2, label="Existing roads")], loc="lower center", ncol=4, frameon=False, fontsize=7.5, bbox_to_anchor=(0.45, 0.03))
    fig.suptitle(f"Map 2. Detected built-up units (n={int(n.sum()):,} inside the boundary) and verified public facilities ({len(S['fac'])}) with latitude / longitude", fontsize=11, y=0.96)
    footer(fig, "Facilities: Overture places, verified with the Damarakunta rule (a detected footprint within 20 m); only records with a unique coordinate are labelled. " + NOTE)
    save(fig, ctx, "map2_footprints_facilities_latlon")


def map3(ctx):
    prep, cost, inside = ctx.prep()
    mnx, mny, mxx, mxy = prep["bounds"]
    ex = (mnx, mxx, mny, mxy)
    b = ctx.cell.bounds
    lim = (b[0] - 100, b[2] + 100, b[1] - 100, b[3] + 100)
    fig, axs = plt.subplots(2, 2, figsize=(13, 13.2))
    lc = prep["landcover"]
    codes = sorted(WC)
    idx = np.full(lc.shape, 0, np.uint8)
    for i, c in enumerate(codes):
        idx[lc == c] = i
    idx = np.ma.masked_where(~inside, idx)
    panels = [("Land cover (ESA WorldCover v200, 10 m)", idx, dict(cmap=ListedColormap([WC[c][0] for c in codes]), vmin=0, vmax=len(codes) - 1, interpolation="nearest")),
              ("Slope, 10 m grid (from 30 m Copernicus GLO-30)", np.ma.masked_where(~inside | ~np.isfinite(prep["slope"]), prep["slope"]), dict(cmap="YlOrRd", vmin=0, vmax=15)),
              ("Cost surface C0 (ordinal planning units, not rupees)", np.ma.masked_invalid(cost), dict(cmap="viridis", vmin=2, vmax=12)),
              ("Blocked cells inside the study window (water, invalid, slope > 25°)", np.ma.masked_where(~inside, np.where(np.isfinite(cost), 0, 1)), dict(cmap=ListedColormap(["#e0e0e0", "#d62728"]), vmin=0, vmax=1, interpolation="nearest"))]
    for ax, (title, arr, kw) in zip(axs.ravel(), panels):
        im = ax.imshow(arr, extent=ex, origin="upper", **kw)
        gpd.GeoSeries([ctx.cell], crs=CRS).boundary.plot(ax=ax, color="k", lw=0.8)
        ctx.roads.plot(ax=ax, color="#1f77b4", lw=0.35)
        ax.set_xlim(lim[0], lim[1]); ax.set_ylim(lim[2], lim[3]); ax.set_title(title, fontsize=9)
        decor(ax, (lim[0], lim[2], lim[1], lim[3]), 1000); ax.tick_params(labelsize=6)
        ax.ticklabel_format(style="plain")
        if title.startswith("Slope"):
            plt.colorbar(im, ax=ax, fraction=0.04, label="slope (degrees)")
        if title.startswith("Cost"):
            plt.colorbar(im, ax=ax, fraction=0.04, label="ordinal cost per 10 m (land cover + slope)")
        if "Land" in title:
            ax.legend(handles=[Patch(fc=WC[c][0], label=WC[c][1]) for c in codes], loc="lower right", fontsize=6)
    fig.suptitle("Map 3. Terrain, land-cover and constraint rasters used to build the cost surface", fontsize=11)
    footer(fig, "Blue lines: existing roads. Cost = land-cover base cost + slope surcharge (0 to 4 for slopes 0 to 10°); cells steeper than 25° are blocked. Land cover: ESA WorldCover v200 (CC BY 4.0); "
                "terrain: Copernicus GLO-30. Planning alternatives, not verified roads. EPSG:32644 (UTM 44N).", credit=False)
    fig.subplots_adjust(0.05, 0.06, 0.97, 0.94, 0.12, 0.14)
    save(fig, ctx, "map3_terrain_cost_landcover_slope")


def map4(ctx):
    G = ctx.main["geoms"]
    ext, zext = window_ext(ctx), central_zone(ctx, 1500, 1100)
    fig = plt.figure(figsize=(16.5, 8.4))
    axs = [fig.add_axes([0.03, 0.10, 0.28, 0.80]), fig.add_axes([0.40, 0.10, 0.55, 0.80])]
    for ax, e, zoom in ((axs[0], ext, False), (axs[1], zext, True)):
        background(ctx, ax, e, alpha=0.85)
        gpd.GeoSeries([ctx.cell], crs=CRS).boundary.plot(ax=ax, color="#ffeb3b", lw=1.0, zorder=3)
        ctx.roads.plot(ax=ax, color="#00e5ff", lw=0.4 if not zoom else 0.9, zorder=4)
        gpd.GeoSeries([g for _, g, _, _ in G["indep"]], crs=CRS).plot(ax=ax, color="#ff9800", lw=0.8 if not zoom else 1.6, alpha=0.8, zorder=6)
        gpd.GeoSeries([g for _, g, _, _ in G["two"]], crs=CRS).plot(ax=ax, color="#1f4fff", lw=0.9 if not zoom else 1.8, zorder=7)
        fg = [g for _, g, _, _ in ctx.main["facility_geoms"]]
        if fg:
            gpd.GeoSeries(fg, crs=CRS).plot(ax=ax, color="#e00000", lw=1.2 if not zoom else 2.4, zorder=8)
        decor(ax, e, 1000 if not zoom else 200); ticks(ax, e)
    rows = {r["plan"]: r for r in ctx.main["rows"]}
    two, ind = rows["Two-stage shared plan"], rows["Independent least-cost routes"]
    axs[0].set_title("Whole window", fontsize=9); axs[1].set_title("Central urban zone (zoom)", fontsize=9)
    axs[1].legend(handles=[Line2D([0], [0], color="#ff9800", lw=2, label=f"Independent least-cost routes (Stage A first choice): {len(G['indep'])}, unique {ind['unique_len_m']:,.0f} m"),
                           Line2D([0], [0], color="#1f4fff", lw=2, label=f"Final shared network: house routes ({len(G['two'])}), unique {two['unique_len_m']:,.0f} m"),
                           Line2D([0], [0], color="#e00000", lw=2, label=f"Final network: facility routes ({len(fg)})"), Line2D([0], [0], color="#00e5ff", lw=1.2, label="Existing roads")],
                  loc="lower right", fontsize=7, framealpha=0.92)
    fig.suptitle("Map 4. Candidate routes versus the final shared network (two-stage plan, footprint penalty mu = 4)", fontsize=11, y=0.96)
    footer(fig, "Stage A keeps K = 3 alternatives per target; only the least-cost first choice (independent route) is stored and drawn. Routes end on roads or on other routes; shared length is counted once. " + NOTE)
    save(fig, ctx, "map4_alternatives_vs_network")


def avoid_network(ctx, targets_house):
    cache = ctx.state_path.with_name("avoid_network_buf71_mu100.pkl")
    if cache.exists():
        return pickle.load(open(cache, "rb"))
    prep, cost, inside = ctx.prep()
    S, cfg = ctx.S, ctx.cfg
    p = PL.planner_params(cfg)
    foot = [g.buffer(7.1) for g in S["houses_all"].geometry]
    w = PL.World(cost, prep["transform"], prep["shape"], [g for g in ctx.roads], foot, 100.0)
    res = PL.pn().plan(w.grid, w.road_union, w.road_cells, targets_house, p, log=lambda *a: None)
    ftg = PL.make_targets(S["houses_all"].iloc[0:0], S["fac"].rename(columns={"name": "name"})[["fid", "name", "facility_type", "geometry"]])
    fres = PL.pn().plan(w.grid, w.road_union, w.road_cells, ftg, p, log=lambda *a: None)
    out = dict(house=[(r["target"], r["geom"]) for r in res["sel"].values()], fac=[(r["target"], r["geom"]) for r in fres["sel"].values()])
    pickle.dump(out, open(cache, "wb"))
    return out


def crossing_segments(routes, houses):
    """Parts of house routes that run through a footprint other than the route's own building (Stage B definition)."""
    sidx = houses.sindex
    segs, n = [], 0
    for tid, g in routes:
        hid = int(str(tid)[1:]) if str(tid).startswith("H") else None
        cand = houses.iloc[list(sidx.query(g, predicate="intersects"))]
        cand = cand[cand.hid != hid]
        if cand.empty:
            continue
        x = g.intersection(unary_union(list(cand.geometry)))
        if x.length > 1e-6:
            segs.append(x); n += 1
    return segs, n


def map5(ctx):
    S = ctx.S
    zext = central_zone(ctx, 1400, 1000)
    tg = PL.make_targets(S["gap"], None)
    prim = [(t, g) for t, g, _, _ in ctx.main["geoms"]["two"]]
    pfac = [(t, g) for t, g, _, _ in ctx.main["facility_geoms"]]
    av = avoid_network(ctx, tg)
    cal = pick_callouts(ctx, zext, 5)
    fig = plt.figure(figsize=(17, 8.8))
    axs = [fig.add_axes([0.03, 0.17, 0.36, 0.66]), fig.add_axes([0.55, 0.17, 0.36, 0.66])]
    for ax, house, fac, title in ((axs[0], prim, pfac, "Primary shared network (penalty x4 on footprint cells)"), (axs[1], av["house"], av["fac"], "Building-avoiding shared network (buffer 7.1 m, penalty x100)")):
        background(ctx, ax, zext, alpha=0.9)
        ctx.roads.plot(ax=ax, color="#00e5ff", lw=0.9, zorder=4)
        b = S["classified"]
        for q, c in QCOL.items():
            g = b[b.quality_class_model == q] if "quality_class_model" in b else b[b.quality_class == q]
            if len(g):
                g.plot(ax=ax, fc=c, ec=c, alpha=0.25, lw=0.5, zorder=5)
        gpd.GeoSeries([g for _, g in house], crs=CRS).plot(ax=ax, color="#1f4fff", lw=1.8, zorder=7)
        if fac:
            gpd.GeoSeries([g for _, g in fac], crs=CRS).plot(ax=ax, color="#e00000", lw=2.4, zorder=8)
        segs, n = crossing_segments(house, S["houses_all"])
        if segs:
            gpd.GeoSeries(segs, crs=CRS).plot(ax=ax, color="#ff00ff", lw=2.6, zorder=9)
        plot_fac(ax, S["fac"], 120, edge="k")
        inzone = sum(1 for _, g in house if g.intersects(box(*zext)))
        ax.set_title(f"{title}\nhouse routes crossing another footprint: {n} of {len(house)} (all routes in the window)", fontsize=8.5)
        decor(ax, zext, 200); ticks(ax, zext)
    callouts(axs[0], cal, zext, col_x=1.02)
    fig.legend(handles=[Patch(fc=QCOL["PLAUSIBLE"], alpha=0.4, label="Footprint: plausible"), Patch(fc=QCOL["REVIEW"], alpha=0.4, label="review"), Patch(fc=QCOL["UNRESOLVED_MERGE"], alpha=0.4, label="unresolved merge"),
                        Line2D([0], [0], color="#1f4fff", lw=2, label="Final shared path: house routes"), Line2D([0], [0], color="#e00000", lw=2, label="facility routes"),
                        Line2D([0], [0], color="#ff00ff", lw=2.5, label="Route segment crossing another footprint"), Line2D([0], [0], color="#00e5ff", lw=1.2, label="Existing road"),
                        *[Line2D([0], [0], marker=FMARK[k], color="none", markerfacecolor=FCOL[k], markeredgecolor="k", markersize=9, label=f"Verified {k}") for k in FCOL]],
               loc="lower center", ncol=5, frameon=True, fontsize=7.5, bbox_to_anchor=(0.5, 0.045))
    fig.suptitle("Map 5. Central urban zone at settlement scale: footprints, facilities, existing roads and optimised shared paths", fontsize=11, y=0.95)
    footer(fig, NOTE + " The building-avoiding network was planned for the same road-gap targets and facilities with footprints buffered by 7.1 m and penalty 100.")
    save(fig, ctx, "map5_village_detail_shared_paths")


def compact(ctx):
    """Two stacked panels for a single journal column (3.4 in): (a) verified facilities and detected footprints, (b) the final shared network, same central zone."""
    S = ctx.S
    zext = central_zone(ctx, 1300, 900)
    G = ctx.main["geoms"]
    fig, axs = plt.subplots(2, 1, figsize=(3.4, 4.9))
    for ax, tag in zip(axs, "ab"):
        background(ctx, ax, zext, alpha=0.95, max_px=1500)
        ctx.roads.plot(ax=ax, color="#00e5ff", lw=0.6, zorder=4)
        if tag == "a":
            b = S["classified"]
            for q, c in QCOL.items():
                g = b[b.quality_class_model == q] if "quality_class_model" in b else b[b.quality_class == q]
                if len(g):
                    g.plot(ax=ax, fc="none", ec=c, lw=0.5, zorder=5)
            plot_fac(ax, S["fac"], 38)
        else:
            S["gap"].plot(ax=ax, fc="#ff7f0e", ec="none", alpha=0.55, zorder=6)
            gpd.GeoSeries([g for _, g, _, _ in G["two"]], crs=CRS).plot(ax=ax, color="#ff3b30", lw=1.3, zorder=7)
            fg = [g for _, g, _, _ in ctx.main["facility_geoms"]]
            if fg:
                gpd.GeoSeries(fg, crs=CRS).plot(ax=ax, color="#ffffff", lw=1.8, zorder=8)
        ax.text(0.02, 0.97, f"({tag})", transform=ax.transAxes, va="top", fontsize=9, fontweight="bold", bbox=dict(fc="w", ec="none", pad=1.5), zorder=60)
        decor(ax, zext, 200, north=(tag == "a")); ax.set_xticks([]); ax.set_yticks([])
    fig.subplots_adjust(0.01, 0.01, 0.99, 0.99, 0, 0.03)
    save(fig, ctx, "adilabad_fac_route_2panel", dpi=300)


def save(fig, ctx, name, dpi=None):
    p = ctx.out / f"{name}.png"
    fig.savefig(p, dpi=dpi or ctx.dpi)
    plt.close(fig)
    print("wrote", p)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--maps", nargs="+", type=int, default=[1, 2, 3, 4, 5, 6], help="6 = compact 2-panel facilities + routes figure for the papers")
    ap.add_argument("--state", default=None)
    ap.add_argument("--mosaic", default=None)
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--no-imagery", action="store_true")
    ap.add_argument("--dpi", type=int, default=200)
    a = ap.parse_args()
    ctx = Ctx(a)
    for m in a.maps:
        {1: map1, 2: map2, 3: map3, 4: map4, 5: map5, 6: compact}[m](ctx)


if __name__ == "__main__":
    main()
