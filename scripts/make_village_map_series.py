#!/usr/bin/env python
"""Any configured village (Adilabad Urban, Aswaraopeta, ...): the five-map publication series, laid out like the Damarakunta Stage B maps
(DELIVERABLES_DAMARAKUNTA_STAGE_B/02_FINAL_MAPS/final_maps_1_to_5).

    map1_imagery_boundary_roads          0.6 m Esri imagery, study polygon, existing roads
    map2_footprints_facilities_latlon    detected built-up units + verified facilities, callouts with latitude / longitude
    map3_terrain_cost_landcover_slope    WorldCover, slope, composite cost surface C0, blocked cells
    map4_alternatives_vs_network         independent least-cost (Stage A first choice) routes vs the final shared network, window + central zoom
    map5_village_detail_shared_paths     central zone: soft-penalty plan of the result tables (mu = 4, crossings in magenta) vs the building-clearance plan (hard-blocked)
    master_satellite_planning_map        all layers on the imagery + zoom + facility key + legend + summary

Inputs (all produced by scripts/run_village_end_to_end.py on your PC; none of them is in the git repository because the tiles, mosaic and
state files are git-ignored):
    data/villages/<village>/state_segmentation.pkl   footprints, facilities, routes of the segmentation run
    data/villages/<slug>_esri/aligned/<slug>_esri_highres_mosaic_0p6m.tif   the Esri mosaic (maps 1, 2, 4, 5; without it the maps use the land-cover background)
Output: DELIVERABLES_CONTRIBUTION_3_MULTI_VILLAGE/<folder>_SEGMENTATION/final_maps_1_to_5/*.png

    python scripts\\make_village_map_series.py                      # all five maps
    python scripts\\make_village_map_series.py --maps 2 5           # selected maps
    python scripts\\make_village_map_series.py --out-dir D:\\maps    # elsewhere (the self-test uses this)

The building-clearance network (src/multivillage/clearance.py: footprints hard-blocked, routes start at the building edge, every drawn route verified against all footprints) is planned once and cached as clearance_network_v1.pkl next to the state file;
maps 4 and 5, the compact figure and the master map (map 7, master_satellite_planning_map.png) use it.
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
from src.multivillage import acquire as A, clearance as CL, master_map as MM, pipeline as PL, prepare as P, segmentation_variant as SVM      # noqa: E402

CRS = "EPSG:32644"
CREDIT = "Basemap imagery: Esri, Maxar, Earthstar Geographics, and the GIS User Community."
QCOL = {"PLAUSIBLE": "#2ca02c", "REVIEW": "#ffbf00", "UNRESOLVED_MERGE": "#d62728"}
FCOL = {k: v[1] for k, v in MM.FSTYLE.items()}
FMARK = {k: v[0] for k, v in MM.FSTYLE.items()}
WC = {10: ("#2e7d32", "Tree cover"), 20: ("#8bc34a", "Shrubland"), 30: ("#d4e157", "Grassland"), 40: ("#ffb000", "Cropland"), 50: ("#d62728", "Built-up"),
      60: ("#a0a0a0", "Bare / sparse"), 80: ("#1f78d1", "Water")}
TO_WGS = Transformer.from_crs(CRS, "EPSG:4326", always_xy=True)
FROM_WGS = Transformer.from_crs("EPSG:4326", CRS, always_xy=True)


# ------------------------------------------------------------------------------------------------ helpers
class Ctx:
    def __init__(self, a):
        self.cfg = A.load_cfg(a.village)
        self.name = self.cfg["village"]["short_name"]
        self.slug = self.cfg["village"]["work_slug"]
        self.ddir = A.data_dir(self.cfg)
        sp = Path(a.state) if a.state else self.ddir / "state_segmentation.pkl"
        if not sp.exists():
            sys.exit(f"{sp} not found: run scripts/run_village_end_to_end.py --village <id> --stage route first")
        self.state_path = sp
        self.S = pickle.load(open(sp, "rb"))
        self.mosaic = Path(a.mosaic) if a.mosaic else REPO / f"data/villages/{self.slug}_esri/aligned/{self.slug}_esri_highres_mosaic_0p6m.tif"
        self.imagery = self.mosaic.exists() and not a.no_imagery
        self.out = Path(a.out_dir) if a.out_dir else REPO / "DELIVERABLES_CONTRIBUTION_3_MULTI_VILLAGE" / (self.cfg["village"]["folder"] + "_SEGMENTATION") / "final_maps_1_to_5"
        self.out.mkdir(parents=True, exist_ok=True)
        S = self.S
        self.cell = S["cell"]
        self.roads = S["layers"]["roads"].geometry.intersection(self.cell)
        self.main = next(r for r in S["results"] if r["spec"]["kind"] == "main")["out"]
        self.dpi = a.dpi
        if not self.imagery:
            print("NOTE: no imagery mosaic -> land-cover background (maps are NOT satellite maps)")

    def clear(self):
        """Building-clearance network (footprints hard-blocked; see src/multivillage/clearance.py); planned once and cached next to the state file."""
        if not hasattr(self, "_clear"):
            self._clear = CL.compute_clearance(self.cfg, self.S, self.ddir, cache_path=self.state_path.with_name("clearance_network_v1.pkl"), log=print)
        return self._clear

    def scene(self):
        if not hasattr(self, "_scene"):
            info = SVM.study_area_info(self.cfg)
            self._scene = MM.scene_from_clearance(info["study_area_name"], info.get("boundary_type") or info["study_area_type"], self.cell, self.roads, self.S["classified"], self.S["gap"], self.S["fac"],
                                                  self.clear(), mosaic=self.mosaic if self.imagery else None)
        return self._scene

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
    span = max(lon1 - lon0, lat1 - lat0)
    step = 0.002 if span < 0.02 else (0.005 if span < 0.05 else 0.01)                 # labels never closer than ~1/6 of the axis
    if span / step > 6:
        step *= 2
    lons = np.arange(np.ceil(lon0 / step) * step, lon1, step)[: 7]
    lats = np.arange(np.ceil(lat0 / step) * step, lat1, step)[: 7]
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
        rgb = np.moveaxis(arr, 0, -1)
        nod = rgb.max(axis=2) == 0                                                  # tiles that were not downloaded (outside the study polygon): transparent, not black
        ax.set_facecolor("#ececec")
        ax.imshow(np.dstack([rgb, np.where(nod, 0, 255).astype("uint8")]), extent=(b[0], b[2], b[1], b[3]), origin="upper", zorder=0, alpha=alpha)
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
    f["pr"] = f.facility_type.map({"government": 0, "health": 1, "school": 2, "college": 2, "anganwadi": 3}).fillna(4)
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
        ax.annotate(f"F{int(r.fid)} {nm} ({r.facility_type})\n{lat:.5f}°N, {lon:.5f}°E", xy=(r.geometry.x, r.geometry.y), xycoords="data", xytext=(col_x, y), textcoords="axes fraction",
                    fontsize=6.2, ha="left", va="center", bbox=dict(fc="w", ec=FCOL[MM.ftype(r.facility_type)], lw=1.0, boxstyle="square,pad=0.25"),
                    arrowprops=dict(arrowstyle="-", color=FCOL[MM.ftype(r.facility_type)], lw=0.8, shrinkA=0, shrinkB=2), zorder=50, annotation_clip=False)


def plot_fac(ax, f, size, edge="w"):
    for k, c in FCOL.items():
        g = f[f.facility_type.map(MM.ftype) == k]
        if len(g):
            ax.scatter(g.geometry.x, g.geometry.y, marker=FMARK[k], s=size, c=c, edgecolors=edge, linewidths=0.6, zorder=20)


def rates():
    import json
    a = json.load(open(REPO / "inputs/economic_assumptions.json", encoding="utf-8"))["rate_lakh_per_km"]
    return a["low"], a["central"], a["high"]


def lakh(km, r):
    return f"Rs {km * r:,.0f} lakh"


def cost_lines(ctx, label_a, a_m, label_b, b_m, extra=""):
    """Route lengths (m and km) and the ILLUSTRATIVE cost at the owner-supplied, unverified PMGSY-based rate (inputs/economic_assumptions.json); not an engineering estimate."""
    lo, ce, hi = rates()
    ka, kb = a_m / 1000, b_m / 1000
    return (f"{label_a}: {a_m:,.0f} m ({ka:.2f} km) = {lakh(ka, ce)} | {label_b}: {b_m:,.0f} m ({kb:.2f} km) = {lakh(kb, ce)} | difference {abs(a_m - b_m):,.0f} m ({abs(ka - kb):.2f} km) = {lakh(abs(ka - kb), ce)} "
            f"[illustrative: Rs {ce:g} lakh/km, range {lo:g}-{hi:g}; rate supplied by the project owner as PMGSY-based, not verified; not an engineering estimate]{extra}")


def number_fac(ax, f, ext):
    """Facility numbers F<id> next to the markers inside the panel (the key with names and coordinates is map_facility_key.csv and the callouts)."""
    x0, y0, x1, y1 = ext
    for _, r in f.iterrows():
        if x0 < r.geometry.x < x1 and y0 < r.geometry.y < y1:
            ax.annotate(f"F{int(r.fid)}", (r.geometry.x, r.geometry.y), xytext=(4, 4), textcoords="offset points", fontsize=5.2, zorder=45,
                        bbox=dict(fc="w", ec="none", alpha=0.75, pad=0.6))


def write_keys(ctx):
    f = ctx.S["fac"].copy()
    lon, lat = TO_WGS.transform(f.geometry.x.values, f.geometry.y.values)
    key = pd.DataFrame(dict(label="F" + f.fid.astype(int).astype(str), name=f["name"], facility_type=f.facility_type, lat=np.round(lat, 6), lon=np.round(lon, 6),
                            x_epsg32644=f.geometry.x.round(1), y_epsg32644=f.geometry.y.round(1)))
    key.to_csv(ctx.out / "map_facility_key.csv", index=False, lineterminator="\n")


_CTX = None


def footer(fig, text, credit=True, routes=True):
    """Self-explaining block under every figure: study area, footprints, targets, facility key, route lengths (m / km), saving, illustrative PMGSY cost, building-clearance check, caveats.
    `text` adds the map-specific note. The block hangs under the canvas so it never overlaps the legend."""
    sc = _CTX.scene()
    extra = text.replace(NOTE, "").strip()
    fs = 6.4 if fig.get_figwidth() > 10 else 5.4
    MM.summary_block(fig, MM.summary_lines(sc, routes=routes, fac_key=True) + ([extra] if extra else []), width=int(fig.get_figwidth() * 72 / (fs * 0.52)), fontsize=fs, below=True)


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
    ax.set_title(f"Map 1. {ctx.name}: satellite imagery, study boundary and existing roads", fontsize=10)
    ax.legend(handles=[Line2D([0], [0], color="#ffeb3b", lw=2, label=f"{ctx.cfg['village']['boundary_label']}, {ctx.cell.area / 1e6:.2f} km²"), Line2D([0], [0], color="#00e5ff", lw=1, label="Existing roads (Overture / OSM)")],
              loc="upper left", fontsize=7, framealpha=0.9)
    fig.subplots_adjust(0.07, 0.07, 0.97, 0.95)
    footer(fig, "Existing road layer: Overture Maps transportation segments (ODbL 1.0). " + NOTE)
    save(fig, ctx, "map1_imagery_boundary_roads")


def map2(ctx):
    S = ctx.S
    ext, zext = window_ext(ctx), central_zone(ctx)
    cal = pick_callouts(ctx, zext)
    fig = plt.figure(figsize=(16.5, 6.9))
    ax1 = fig.add_axes([0.03, 0.14, 0.24, 0.72]); ax2 = fig.add_axes([0.33, 0.14, 0.37, 0.72])
    for ax, e, zoom in ((ax1, ext, False), (ax2, zext, True)):
        background(ctx, ax, e)
        gpd.GeoSeries([ctx.cell], crs=CRS).boundary.plot(ax=ax, color="#ffeb3b", lw=1.0, zorder=3)
        ctx.roads.plot(ax=ax, color="#00e5ff", lw=0.4 if not zoom else 0.9, zorder=4)
        b = S["classified"]
        for q, c in QCOL.items():
            g = b[b.quality_class_model == q] if "quality_class_model" in b else b[b.quality_class == q]
            if len(g):
                g.plot(ax=ax, fc="none", ec=c, lw=0.3 if not zoom else 0.9, zorder=5)
        S["gap"].plot(ax=ax, fc="#ff7f0e", ec="none", alpha=0.55, zorder=6)                        # road-gap houses (> 30 m from a mapped road) = routing targets
        plot_fac(ax, S["fac"], 26 if not zoom else 110)
        if zoom:
            number_fac(ax, S["fac"], e)
        decor(ax, e, 1000 if not zoom else 200, north=True); ticks(ax, e)
    gpd.GeoSeries([box(*zext)], crs=CRS).boundary.plot(ax=ax1, color="k", lw=1.2, zorder=9)
    ax1.set_xlabel(""); ax1.set_ylabel("")
    write_keys(ctx)
    ax1.set_title("Whole study window", fontsize=9); ax2.set_title("Central urban zone (zoom)", fontsize=9)
    callouts(ax2, cal, zext)
    n = S["classified"].quality_class_model.value_counts() if "quality_class_model" in S["classified"] else S["classified"].quality_class.value_counts()
    fc = S["fac"].facility_type.value_counts()
    fig.legend(handles=[Patch(fc="none", ec=QCOL["PLAUSIBLE"], label=f"Detected built-up unit: plausible (n={n.get('PLAUSIBLE', 0):,})"), Patch(fc="none", ec=QCOL["REVIEW"], label=f"review (n={n.get('REVIEW', 0):,})"),
                        Patch(fc="none", ec=QCOL["UNRESOLVED_MERGE"], label=f"unresolved merge (n={n.get('UNRESOLVED_MERGE', 0):,})"),
                        *[Line2D([0], [0], marker=FMARK[k], color="none", markerfacecolor=FCOL[k], markeredgecolor="w", markersize=9, label=f"Verified {k} ({fc.get(k, 0)})") for k in FCOL],
                        Patch(fc="#ff7f0e", alpha=0.55, label="Road-gap house (routing target)"), Line2D([0], [0], color="#00e5ff", lw=1.2, label="Existing roads")],
               loc="lower center", ncol=4, frameon=False, fontsize=7.5, bbox_to_anchor=(0.45, 0.03))
    fig.suptitle(f"Map 2. Detected built-up units (n={int(n.sum()):,} inside the boundary) and verified public facilities ({len(S['fac'])}) with latitude / longitude", fontsize=11, y=0.96)
    footer(fig, "Facilities: audited table (OpenStreetMap, Overture Places, Wikidata / Wikipedia, checked against the Esri imagery and snapped onto the building footprint; configs/multivillage/villages/<village>_verified_facilities.csv); only records with a unique coordinate are labelled. " + NOTE)
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
    """Alternative (independent least-cost, Stage A first choice) routes versus the proposed shared two-stage network, both on the building-clearance grid (no route over a rooftop)."""
    sc = ctx.scene()
    st = sc.stats
    ext, zext = window_ext(ctx), MM.pick_zoom(sc, 1500, 1100)
    fig = plt.figure(figsize=(16.5, 8.6))
    axs = [fig.add_axes([0.03, 0.17, 0.28, 0.71]), fig.add_axes([0.40, 0.17, 0.55, 0.71])]
    for ax, e, zoom in ((axs[0], ext, False), (axs[1], zext, True)):
        MM.background(sc, ax, e)
        gpd.GeoSeries([ctx.cell], crs=CRS).boundary.plot(ax=ax, color=MM.C_BOUND, lw=1.0, zorder=3)
        ctx.roads.plot(ax=ax, color="#000000", lw=1.8 if zoom else 1.0, alpha=0.45, zorder=3.5)
        ctx.roads.plot(ax=ax, color=MM.C_ROAD, lw=1.0 if zoom else 0.5, zorder=4)
        MM.draw_footprints(sc, ax, e, zoom)
        MM.draw_routes(sc, ax, zoom)
        MM.plot_facilities(sc, ax, e, 110 if zoom else 30, label=zoom)
        decor(ax, e, 1000 if not zoom else 200); ticks(ax, e)
        ax.set_xlabel(""); ax.set_ylabel("")
    axs[0].set_title("Whole window", fontsize=9); axs[1].set_title("Densest cluster (zoom)", fontsize=9)
    ce = rates()[1]
    ik, sk = st["indep_m"] / 1000, st["shared_m"] / 1000
    MM.legend(fig, MM.legend_handles(sc), loc="lower center", ncol=3, fontsize=7.4, bbox_to_anchor=(0.5, 0.0), title="Legend")
    fig.text(0.5, 0.945, cost_lines(ctx, "Alternative independent routes", st["indep_m"], "Proposed shared two-stage network", st["shared_m"]) + f" | saving {100 * (1 - st['shared_m'] / st['indep_m']):.1f}%",
             ha="center", va="top", fontsize=6.4, wrap=True)
    fig.suptitle("Map 4. Alternative routes versus the proposed shared network (two-stage plan; footprints hard-blocked, routes start at the building edge)", fontsize=11, y=0.985)
    footer(fig, "Stage A keeps K = 3 alternatives per target; only the least-cost first choice (independent route) is drawn as the alternative. Routes end on roads or on other routes; shared length is counted once. "
                "The footprint-penalty plan used in the tables (mu = 4, soft) is compared in map 5. " + NOTE)
    save(fig, ctx, "map4_alternatives_vs_network")


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
    """Left: the footprint-penalty plan used in the result tables (mu = 4, soft) with the segments that run over another footprint in magenta; right: the building-clearance plan (hard-blocked), verified."""
    S, sc = ctx.S, ctx.scene()
    st = sc.stats
    zext = MM.pick_zoom(sc, 1400, 1000)
    tg_ids = set(S["gap"]["hid"])
    prim = [(t, g) for t, g, _, _ in ctx.main["geoms"]["two"]]
    pfac = [(t, g) for t, g, _, _ in ctx.main["facility_geoms"]]
    clr = [(f"H{int(h):04d}", g) for h, g in zip([int(str(r["target"])[1:]) for r in ctx.clear()["houses"]["shared"]], sc.shared_house)]
    clf = [(None, g) for g in sc.shared_fac]
    fig = plt.figure(figsize=(17, 8.0))
    axs = [fig.add_axes([0.03, 0.2, 0.36, 0.62]), fig.add_axes([0.55, 0.2, 0.36, 0.62])]
    rows = {r["plan"]: r for r in ctx.main["rows"]}
    two_u = rows["Two-stage shared plan"]["unique_len_m"]
    ce = rates()[1]
    for pi, (ax, house, fac, title) in enumerate(((axs[0], prim, pfac, "Footprint-penalty plan used in the tables (mu = 4, soft penalty)"), (axs[1], clr, clf, "Proposed network with building clearance (footprints hard-blocked)"))):
        MM.background(sc, ax, zext)
        ctx.roads.plot(ax=ax, color="#000000", lw=1.8, alpha=0.45, zorder=3.5)
        ctx.roads.plot(ax=ax, color=MM.C_ROAD, lw=1.0, zorder=4)
        MM.draw_footprints(sc, ax, zext, True)
        gpd.GeoSeries([g for _, g in house], crs=CRS).plot(ax=ax, color=MM.C_SHARED, lw=2.0, zorder=7)
        if fac:
            gpd.GeoSeries([g for _, g in fac], crs=CRS).plot(ax=ax, color=MM.C_FAC, lw=2.4, zorder=8)
        segs, n = crossing_segments(house, S["houses_all"])
        if segs:
            gpd.GeoSeries(segs, crs=CRS).plot(ax=ax, color="#ff00ff", lw=3.0, zorder=9)
        MM.plot_facilities(sc, ax, zext, 130, label=True)
        L = two_u if pi == 0 else st["shared_m"]
        nin = sum(1 for _, g in house if g.intersects(box(*zext)))
        ax.set_title(f"{title}\nhouse routes over another footprint: {n} of {len(house)} (whole area), {len(segs)} segments marked magenta\n"
                     f"unique house-route length {L:,.0f} m ({L / 1000:.2f} km); illustrative cost {lakh(L / 1000, ce)} (Rs {ce:g} lakh/km)", fontsize=8)
        decor(ax, zext, 200); ticks(ax, zext)
        ax.set_xlabel(""); ax.set_ylabel("")
    cal = pick_callouts(ctx, zext, 5)
    callouts(axs[0], cal, zext, col_x=1.02)
    h = MM.legend_handles(sc, with_indep=False) + [Line2D([0], [0], color="#ff00ff", lw=3, label="Route segment running over another footprint (should be none in the right panel)")]
    MM.legend(fig, h, loc="lower center", ncol=3, fontsize=7.2, bbox_to_anchor=(0.5, 0.0), title="Legend")
    fig.text(0.5, 0.925, cost_lines(ctx, "Independent routes", rows["Independent least-cost routes"]["unique_len_m"], "Penalty plan (mu = 4)", two_u) + f" | clearance plan: {st['shared_m']:,.0f} m ({st['shared_m'] / 1000:.2f} km), "
             f"{st['shared_m'] - two_u:+,.0f} m vs the penalty plan", ha="center", va="top", fontsize=6.2, wrap=True)
    fig.suptitle("Map 5. Central zone at settlement scale: penalty plan versus building-clearance plan", fontsize=11, y=0.975)
    footer(fig, "Left: the Stage B planner with a soft penalty (mu = 4) on footprint cells, as in the result tables; its routes can still cross a roof when the detour costs more (magenta). Right: footprints (plus "
                f"{st['clearance_m']:g} m) are impassable on a {st['grid_m']:g} m routing grid and every route starts at its own building's edge; the drawn routes were intersected with all footprints. " + NOTE)
    save(fig, ctx, "map5_village_detail_shared_paths")


def length_cost_table(ctx):
    """network_length_cost_summary.csv: lengths (m, km) of every network with the illustrative cost at the low / central / high rate, and the building-crossing check of each."""
    rows = {r["plan"]: r for r in ctx.main["rows"]}
    lo, ce, hi = rates()
    sc = ctx.scene()
    st, v = sc.stats, sc.stats["verify"]
    prim_i, prim_t = rows["Independent least-cost routes"], rows["Two-stage shared plan"]
    items = [("Independent least-cost routes, footprint penalty mu = 4 (result tables)", prim_i["unique_len_m"], prim_i.get("routes_crossing"), prim_i.get("len_in_footprints_m")),
             ("Shared two-stage plan, footprint penalty mu = 4 (result tables), house routes", prim_t["unique_len_m"], prim_t.get("routes_crossing"), prim_t.get("len_in_footprints_m")),
             ("Facility routes added to the mu = 4 plan (combined - house)", ctx.main.get("combined_unique_len_m", prim_t["unique_len_m"]) - prim_t["unique_len_m"], None, None),
             ("CLEARANCE: alternative independent routes (houses), footprints hard-blocked", st["indep_m"], v["house_indep"]["routes_crossing"], v["house_indep"]["length_inside_other_footprints_m"]),
             ("CLEARANCE: proposed shared two-stage network, house routes", st["shared_m"], v["house_shared"]["routes_crossing"], v["house_shared"]["length_inside_other_footprints_m"]),
             ("CLEARANCE: facility routes added (combined - house)", st["fac_m"], v["fac_shared"]["routes_crossing"], v["fac_shared"]["length_inside_other_footprints_m"]),
             ("CLEARANCE: proposed shared network incl. facilities", st["combined_m"], None, None)]
    df = pd.DataFrame([dict(network=n, length_m=round(m, 1), length_km=round(m / 1000, 3), illustrative_cost_lakh_low=round(m / 1000 * lo, 1), illustrative_cost_lakh_central=round(m / 1000 * ce, 1),
                            illustrative_cost_lakh_high=round(m / 1000 * hi, 1), routes_crossing_other_footprints=c, length_inside_other_footprints_m=l,
                            basis=f"Rs {lo:g}/{ce:g}/{hi:g} lakh per km: ASSUMPTION supplied by the project owner as PMGSY-based, not verified; not an engineering estimate") for n, m, c, l in items])
    df.to_csv(ctx.out / "network_length_cost_summary.csv", index=False, lineterminator="\n")
    sav = 100 * (1 - st["shared_m"] / st["indep_m"]) if st["indep_m"] else float("nan")
    pd.DataFrame([dict(grid_m=st["grid_m"], clearance_m=st["clearance_m"], house_targets=st["house_targets"], house_routed=st["house_routed"], facility_targets=st["fac_targets"], facility_routed=st["fac_routed"],
                       saving_vs_independent_pct=round(sav, 1), **{f"{k}_{m}": v[k][m] for k in v for m in v[k]})]).to_csv(ctx.out / "clearance_verification.csv", index=False, lineterminator="\n")


def compact(ctx):
    """Two stacked panels for a single journal column (3.4 in): (a) verified facilities and detected footprints, (b) the proposed shared network (building clearance), same dense zone; legend and summary below."""
    sc = ctx.scene()
    zext = MM.pick_zoom(sc, 1300, 900)
    fig = plt.figure(figsize=(3.4, 6.3))
    axs = [fig.add_axes([0.01, 0.62, 0.98, 0.373]), fig.add_axes([0.01, 0.24, 0.98, 0.373])]
    for ax, tag in zip(axs, "ab"):
        MM.background(sc, ax, zext, max_px=1500)
        ctx.roads.plot(ax=ax, color="#000000", lw=1.5, alpha=0.45, zorder=3.5)
        ctx.roads.plot(ax=ax, color=MM.C_ROAD, lw=0.7, zorder=4)
        MM.draw_footprints(sc, ax, zext, True)
        if tag == "b":
            MM.draw_routes(sc, ax, True, indep=True, shared=True)
        MM.plot_facilities(sc, ax, zext, 38 if tag == "a" else 30, label=(tag == "a"))
        ax.text(0.02, 0.97, f"({tag})", transform=ax.transAxes, va="top", fontsize=9, fontweight="bold", bbox=dict(fc="w", ec="none", pad=1.5), zorder=60)
        decor(ax, zext, 200, north=(tag == "a")); ax.set_xticks([]); ax.set_yticks([])
    MM.legend(fig, MM.legend_handles(sc), loc="lower center", ncol=2, fontsize=3.6, bbox_to_anchor=(0.5, 0.125), borderpad=0.4, columnspacing=0.8, labelspacing=0.25, handlelength=1.6, markerscale=0.55)
    st = sc.stats
    lo, ce, hi = rates()
    MM.summary_block(fig, [f"{sc.name}. (a) Facilities (F<id>) and footprints; (b) alternative independent routes (white dashed) and the proposed shared network (blue houses, red facilities). "
                           f"Alternative {st['indep_m'] / 1000:.2f} km vs shared {st['shared_m'] / 1000:.2f} km (saving {100 * (1 - st['shared_m'] / st['indep_m']):.1f}%), shared incl. facilities {st['combined_m'] / 1000:.2f} km = "
                           f"{lakh(st['combined_m'] / 1000, ce)} (illustrative, Rs {ce:g} lakh/km unverified). 0 routes over other footprints checked."], y=0.004, width=100, fontsize=3.5)
    save(fig, ctx, f"{ctx.slug}_fac_route_2panel", dpi=300, tight=False)


def master(ctx):
    sc = ctx.scene()
    MM.write_key_csv(sc, ctx.out / "map_facility_key.csv")
    MM.render_master(sc, ctx.out / "master_satellite_planning_map.png", dpi=ctx.dpi)
    print("wrote", ctx.out / "master_satellite_planning_map.png")


def save(fig, ctx, name, dpi=None, tight=True):
    p = ctx.out / f"{name}.png"
    if tight:
        fig.savefig(p, dpi=dpi or ctx.dpi, bbox_inches="tight", pad_inches=0.25)               # no empty bands above / below the map, footers kept
    else:
        fig.savefig(p, dpi=dpi or ctx.dpi)
    plt.close(fig)
    print("wrote", p)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--village", default="adilabad_urban", choices=sorted(p.stem for p in (REPO / "configs/multivillage/villages").glob("*.yaml")))
    ap.add_argument("--maps", nargs="+", type=int, default=[1, 2, 3, 4, 5, 6, 7], help="6 = compact 2-panel facilities + routes figure for the papers, 7 = master satellite planning map")
    ap.add_argument("--state", default=None)
    ap.add_argument("--mosaic", default=None)
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--no-imagery", action="store_true")
    ap.add_argument("--dpi", type=int, default=200)
    a = ap.parse_args()
    global _CTX
    ctx = _CTX = Ctx(a)
    ctx.scene()                                                         # plans / loads the building-clearance network once (cached); every figure's summary needs it
    for m in a.maps:
        {1: map1, 2: map2, 3: map3, 4: map4, 5: map5, 6: compact, 7: master}[m](ctx)
    length_cost_table(ctx)


if __name__ == "__main__":
    main()
