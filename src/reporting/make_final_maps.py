"""make_final_maps.py - the four final maps (300 dpi PNG) for the Damarakunta dissertation package.

  map1_imagery_boundary_roads.png      satellite imagery + village boundary + existing TGRAC roads
  map2_footprints_facilities_latlon.png  detected footprints (by quality class) + priority facilities with latitude/longitude labels
  map3_terrain_cost_landcover_slope.png  land cover, slope (with the 25 degree limit), ordinal cost surface, blocked cells
  map4_alternatives_vs_network.png     Stage A alternative routes versus the final shared network (routes.gpkg)

Every map carries a scale bar, north arrow, CRS and a statement that routes are unverified planning alternatives. Maps with imagery also carry the
imagery caution: the Esri World Imagery licence for thesis figures is unresolved (see inputs/METADATA.md), so these are review drafts.
usage: python src/reporting/make_final_maps.py --run-dir <stageB run folder> --out outputs/final_maps
"""
import sys as _sys
from pathlib import Path as _P
_sys.path.insert(0, str(_P(__file__).resolve().parents[1]))
import scenario_names as SN

import argparse
from pathlib import Path

import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from pyproj import Transformer
from rasterio.windows import from_bounds

ROOT = Path(__file__).resolve().parents[2]
V = ROOT / "Siddipet" / "Damarakunta"
IMG = V / "aligned" / "damarakunta_esri_highres_mosaic_0p6m.tif"
CAUTION = "Planning alternatives, not verified roads. Costs are ordinal planning units. EPSG:32644 (UTM 44N)."
IMG_NOTE = " Imagery: Esri World Imagery export (Vantor 60 cm layer; capture date 29 Apr 2026 at one sampled point, mosaic-wide dates not recorded); licence unresolved - review draft, do not redistribute."
WC = {10: ("Tree cover", "#2e7d32"), 20: ("Shrubland", "#8bc34a"), 30: ("Grassland", "#d4e157"), 40: ("Cropland", "#ffb300"),
      50: ("Built-up", "#d32f2f"), 60: ("Bare / sparse", "#bcaaa4"), 80: ("Water", "#1976d2")}
QC = {"PLAUSIBLE": "#00e676", "REVIEW": "#ffea00", "UNRESOLVED_MERGE": "#ff5252"}
TO_LL = Transformer.from_crs(32644, 4326, always_xy=True)
FROM_LL = Transformer.from_crs(4326, 32644, always_xy=True)


def read_img(bounds, max_px=2600):
    xmin, ymin, xmax, ymax = bounds
    with rasterio.open(IMG) as s:
        w = from_bounds(xmin, ymin, xmax, ymax, s.transform)
        sc = max_px / max(w.width, w.height)
        shape = (3, max(int(w.height * sc), 1), max(int(w.width * sc), 1))
        arr = s.read(window=w, out_shape=shape, boundless=True, fill_value=0).transpose(1, 2, 0)
    alpha = np.where(arr.sum(axis=2) == 0, 0, 255).astype("uint8")      # blank (no-data) corner stays transparent
    return np.dstack([arr, alpha]), (xmin, xmax, ymin, ymax)


def furniture(ax, extent, bar_m, latlon_step=None):
    xmin, xmax, ymin, ymax = extent
    ax.set_xlim(xmin, xmax); ax.set_ylim(ymin, ymax); ax.set_aspect("equal")
    x0, y0 = xmin + 0.04 * (xmax - xmin), ymin + 0.05 * (ymax - ymin)
    ax.plot([x0, x0 + bar_m], [y0, y0], color="k", lw=4, solid_capstyle="butt", zorder=30)
    ax.plot([x0, x0 + bar_m], [y0, y0], color="w", lw=1.5, solid_capstyle="butt", zorder=31)
    ax.text(x0 + bar_m / 2, y0 + 0.012 * (ymax - ymin), "%g m" % bar_m if bar_m < 1000 else "%g km" % (bar_m / 1000), ha="center", fontsize=7, zorder=32,
            bbox=dict(fc="w", ec="none", alpha=0.7, pad=1))
    nx_, ny_ = xmax - 0.05 * (xmax - xmin), ymax - 0.14 * (ymax - ymin)
    ax.annotate("N", xy=(nx_, ny_ + 0.09 * (ymax - ymin)), xytext=(nx_, ny_), ha="center", fontsize=10, fontweight="bold", zorder=32,
                arrowprops=dict(arrowstyle="-|>", color="k", lw=1.5), bbox=dict(fc="w", ec="none", alpha=0.6, pad=1))
    if latlon_step:
        lon0, lat0 = TO_LL.transform(xmin, ymin); lon1, lat1 = TO_LL.transform(xmax, ymax)
        lons = np.arange(np.ceil(lon0 / latlon_step) * latlon_step, lon1, latlon_step)
        lats = np.arange(np.ceil(lat0 / latlon_step) * latlon_step, lat1, latlon_step)
        ym = (ymin + ymax) / 2; xm = (xmin + xmax) / 2
        ax.set_xticks([FROM_LL.transform(lo, TO_LL.transform(xm, ym)[1])[0] for lo in lons]); ax.set_xticklabels(["%.3f°E" % lo for lo in lons], fontsize=6)
        ax.set_yticks([FROM_LL.transform(TO_LL.transform(xm, ym)[0], la)[1] for la in lats]); ax.set_yticklabels(["%.3f°N" % la for la in lats], fontsize=6, rotation=90, va="center")
        ax.grid(color="w", alpha=0.35, lw=0.4)
    else:
        ax.ticklabel_format(useOffset=False, style="plain"); ax.tick_params(labelsize=6)


def foot(fig, text):
    fig.text(0.5, 0.012, text, ha="center", fontsize=6.5, color="#333333", wrap=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--out", default=str(ROOT / "outputs" / "final_maps"))
    ap.add_argument("--avoid-run-dir", default=None, help="Stage B run folder of the building-avoiding scenario (v1.4 buffer); adds map 5 when given")
    a = ap.parse_args()
    run, out = Path(a.run_dir), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    bnd = gpd.read_file(V / "study_area" / "damarakunta_boundary.gpkg")
    roads = gpd.read_file(V / "reference" / "tgrac_road_network.gpkg")
    bld = gpd.read_file(V / "results" / "v8_instances" / "buildings_v8_full.gpkg", layer="buildings")
    bld = bld[bld.geometry.centroid.within(bnd.geometry.iloc[0])]
    fac = gpd.read_file(SN.FAC_LAYER, layer="priority_facilities")
    rg = lambda l: gpd.read_file(run / "routes.gpkg", layer=l)
    _fr = Path(a.avoid_run_dir) if a.avoid_run_dir else run       # Map 4 shows the FINAL network: the building-avoiding scenario when given
    rgf = lambda l: gpd.read_file(_fr / "routes.gpkg", layer=l)
    net_h, net_f, alts = rgf("routes_network_houses"), rgf("routes_network_facilities"), rgf("stageA_alternatives_houses")
    bxmin, bymin, bxmax, bymax = bnd.total_bounds
    vext = (bxmin - 80, bxmax + 80, bymin - 80, bymax + 80)
    sb = bld.total_bounds
    allx = list(sb[[0, 2]]) + [p.x for p in fac.geometry]; ally = list(sb[[1, 3]]) + [p.y for p in fac.geometry]
    sext = (min(allx) - 150, max(allx) + 150, min(ally) - 150, max(ally) + 150)
    fx, fy = [p.x for p in fac.geometry], [p.y for p in fac.geometry]
    _cx, _cy = float(np.median(fx)), float(np.median(fy))
    _mf = [(p_.x, p_.y) for p_ in fac.geometry if ((p_.x - _cx) ** 2 + (p_.y - _cy) ** 2) ** 0.5 < 1500]
    zext = (min(q[0] for q in _mf) - 330, max(q[0] for q in _mf) + 330, min(q[1] for q in _mf) - 300, max(q[1] for q in _mf) + 300)   # main settlement: facilities within 1.5 km plus 300 m
    inside = lambda g_, e_: e_[0] <= g_.x <= e_[1] and e_[2] <= g_.y <= e_[3]
    is_admin = lambda r_: str(r_.facility_type).startswith("Administrative")

    # ------------------------------------------------------------ map 1
    fig, ax = plt.subplots(figsize=(11, 7.4))
    arr, ext = read_img((vext[0], vext[2], vext[1], vext[3]))
    ax.imshow(arr, extent=(ext[0], ext[1], ext[2], ext[3]), origin="upper", interpolation="bilinear")
    roads.plot(ax=ax, color="#00e5ff", lw=0.9, zorder=5)
    bnd.boundary.plot(ax=ax, color="#ffeb3b", lw=1.8, zorder=6)
    furniture(ax, vext, 1000, latlon_step=0.02)
    ax.legend(handles=[Line2D([], [], color="#ffeb3b", lw=2, label="Village boundary (TGRAC)"), Line2D([], [], color="#00e5ff", lw=1.2, label="Existing roads (TGRAC; 44.7% of length lies outside the boundary)")],
              loc="upper left", fontsize=7, framealpha=0.9)
    ax.set_title("Map 1. Damarakunta: satellite imagery, village boundary and existing TGRAC roads", fontsize=10)
    foot(fig, CAUTION + IMG_NOTE)
    fig.savefig(out / "map1_imagery_boundary_roads.png", dpi=300, bbox_inches="tight"); plt.close(fig)

    # ------------------------------------------------------------ map 2
    try:
        import pandas as pd
        vf = pd.read_csv(ROOT / "outputs" / "verification" / "facility_verification.csv")
        verdict = dict(zip(vf.facility_id.astype(str), vf.verdict))
    except Exception:
        verdict = {}
    OFF = {"36181600902": (-175, -48), "36181600903": (-235, 12), "HEALTH_8734223673": (-60, 64), "GP_DAMARAKUNTA": (60, -70)}
    fig, axs = plt.subplots(1, 2, figsize=(13, 6.6), gridspec_kw=dict(width_ratios=[1.0, 1.05]))
    for k, (ax, ext_, bar, step, t) in enumerate(((axs[0], vext, 1000, 0.02, "Whole village"), (axs[1], zext, 100, 0.002, "Main settlement (zoom)"))):
        arr, e_ = read_img((ext_[0], ext_[2], ext_[1], ext_[3]), 2400)
        ax.imshow(arr, extent=(e_[0], e_[1], e_[2], e_[3]), origin="upper", interpolation="bilinear")
        roads.plot(ax=ax, color="#00e5ff", lw=0.8, zorder=4)
        for q, c in QC.items():
            g = bld[bld.quality_class == q]
            if len(g):
                g.plot(ax=ax, facecolor="none" if k else c, edgecolor=c, lw=1.0 if k else 0.4, zorder=6)
        for r in fac.itertuples():
            if not inside(r.geometry, ext_):
                continue
            ax.scatter([r.geometry.x], [r.geometry.y], marker="s" if is_admin(r) else "*", s=(60 if not k else 150) if is_admin(r) else (90 if not k else 230), c="#aa00ff" if is_admin(r) else "#ff1744", edgecolors="w", linewidths=0.8, zorder=10)
            if k:
                lon, lat = TO_LL.transform(r.geometry.x, r.geometry.y)
                v = verdict.get(str(r.facility_id), "")
                ax.annotate("%s (%s)\n%.5f°N, %.5f°E%s" % (r.facility_name, r.facility_type, lat, lon, "\nagreement check: " + v if v else ""), (r.geometry.x, r.geometry.y),
                            xytext=OFF.get(str(r.facility_id), (10, 10)), textcoords="offset points", fontsize=6.5, zorder=12,
                            arrowprops=dict(arrowstyle="-", color="#ff1744", lw=0.8), bbox=dict(fc="w", ec="#ff1744", alpha=0.92, pad=2))
        furniture(ax, ext_, bar, latlon_step=step)
        ax.set_title(t, fontsize=9)
    axs[0].legend(handles=[Patch(fc="none", ec=c, label="Footprint: %s (n=%d)" % (q.lower().replace("_", " "), int((bld.quality_class == q).sum()))) for q, c in QC.items()] +
                  [Line2D([], [], marker="*", color="w", mfc="#ff1744", mec="w", ms=11, label="School / health facility (%d)" % sum(not is_admin(r_) for r_ in fac.itertuples())),
                   Line2D([], [], marker="s", color="w", mfc="#aa00ff", mec="w", ms=8, label="Gram Panchayat HQ (TGRAC) (%d)" % sum(is_admin(r_) for r_ in fac.itertuples())), Line2D([], [], color="#00e5ff", lw=1.2, label="TGRAC roads")],
                  loc="lower right", fontsize=6.5, framealpha=0.92)
    fig.suptitle("Map 2. Detected building footprints (n=%d inside the boundary) and priority facilities with latitude/longitude" % len(bld), fontsize=10)
    foot(fig, "Footprints are automatic detections (AUTO_DETECTED_UNVERIFIED), not a census. The agreement check (verify_detections.py) compares with TGRAC tables, school compounds and Google Open Buildings; it is not accuracy. " + CAUTION + IMG_NOTE)
    fig.tight_layout(rect=(0, 0.05, 1, 0.96))
    fig.savefig(out / "map2_footprints_facilities_latlon.png", dpi=300, bbox_inches="tight"); plt.close(fig)

    # ------------------------------------------------------------ map 3
    def raster(name):
        with rasterio.open(V / "aligned" / name) as s:
            d = s.read(1).astype(float)
            if s.nodata is not None:
                d[d == s.nodata] = np.nan
            b = s.bounds
        return d, (b.left, b.right, b.bottom, b.top)
    wc, e = raster("damarakunta_worldcover_10m.tif")
    slope, _ = raster("damarakunta_slope_10m.tif")
    cost, _ = raster("damarakunta_cost_surface_10m.tif")
    blocked, _ = raster("damarakunta_prohibited_mask_10m.tif")
    wc = np.where(wc == 0, np.nan, wc)
    fig, axs = plt.subplots(2, 2, figsize=(11, 9.4))
    ext3 = (e[0], e[1], e[2], e[3])
    ids = list(WC)
    cm = ListedColormap([WC[i][1] for i in ids]); norm = BoundaryNorm([i - 5 for i in ids] + [ids[-1] + 5], cm.N)
    axs[0, 0].imshow(wc, extent=ext3, cmap=cm, norm=norm, interpolation="nearest")
    axs[0, 0].legend(handles=[Patch(fc=WC[i][1], label=WC[i][0]) for i in ids], fontsize=6, loc="lower right", framealpha=0.9)
    axs[0, 0].set_title("Land cover (ESA WorldCover, 10 m)", fontsize=8)
    im = axs[0, 1].imshow(slope, extent=ext3, cmap="YlOrRd", vmin=0, vmax=27, interpolation="nearest")
    plt.colorbar(im, ax=axs[0, 1], fraction=0.04, label="slope (degrees)")
    axs[0, 1].contour(np.flipud(slope), levels=[10, 25], extent=ext3, colors=["#6a1b9a", "k"], linewidths=0.6)
    axs[0, 1].set_title("Slope, 10 m grid (from 30 m DEM); contours 10° and 25°", fontsize=7.5)
    im = axs[1, 0].imshow(cost, extent=ext3, cmap="viridis", vmin=2, vmax=12, interpolation="nearest")
    plt.colorbar(im, ax=axs[1, 0], fraction=0.04, label="ordinal cost per 10 m (land cover + slope)")
    axs[1, 0].set_title("Cost surface C0 (ordinal planning units, not rupees)", fontsize=8)
    bl = np.where(np.isfinite(wc), np.where(blocked > 0, 1.0, 0.0), np.nan)
    axs[1, 1].imshow(bl, extent=ext3, cmap=ListedColormap(["#e0e0e0", "#b71c1c"]), vmin=0, vmax=1, interpolation="nearest")
    axs[1, 1].set_title("Blocked cells inside the village (water, no data, invalid slope)", fontsize=7.5)
    for ax in axs.ravel():
        bnd.boundary.plot(ax=ax, color="k", lw=0.8)
        roads.plot(ax=ax, color="#0277bd", lw=0.5)
        furniture(ax, (bxmin - 40, bxmax + 40, bymin - 40, bymax + 40), 1000)
    fig.suptitle("Map 3. Terrain, land-cover and constraint rasters used to build the cost surface", fontsize=10)
    foot(fig, "Blue lines: existing TGRAC roads. Cost = land-cover base cost + slope surcharge (0 to 4 for slopes 0 to 10°); cells steeper than 25° are blocked at run time. " + CAUTION)
    fig.tight_layout(rect=(0, 0.03, 1, 0.97))
    fig.savefig(out / "map3_terrain_cost_landcover_slope.png", dpi=300, bbox_inches="tight"); plt.close(fig)

    # ------------------------------------------------------------ map 4
    fig, axs = plt.subplots(1, 2, figsize=(13, 5.8))
    for ax, ext_, bar, t in ((axs[0], vext, 1000, "Whole village"), (axs[1], zext, 100, "Main settlement (zoom)")):
        arr, e_ = read_img((ext_[0], ext_[2], ext_[1], ext_[3]), 1800)
        ax.imshow(np.dstack([(arr[..., :3] * 0.55 + 90).clip(0, 255), arr[..., 3]]).astype("uint8"), extent=(e_[0], e_[1], e_[2], e_[3]), origin="upper")
        roads.plot(ax=ax, color="#00e5ff", lw=0.9, zorder=4)
        alts.plot(ax=ax, color="#ff9100", lw=0.7, alpha=0.8, zorder=5)
        net_h.plot(ax=ax, color="#ffffff", lw=2.2, zorder=6); net_h.plot(ax=ax, color="#2962ff", lw=1.2, zorder=7)
        net_f.plot(ax=ax, color="#ffffff", lw=3.0, zorder=8); net_f.plot(ax=ax, color="#d50000", lw=1.8, zorder=9)
        bnd.boundary.plot(ax=ax, color="#ffeb3b", lw=1.2, zorder=3)
        furniture(ax, ext_, bar, latlon_step=0.02 if t == "Whole village" else 0.002)
        ax.set_title(t, fontsize=9)
    axs[1].legend(handles=[Line2D([], [], color="#ff9100", lw=1.5, label="Stage A alternatives (%d candidate routes)" % len(alts)), Line2D([], [], color="#2962ff", lw=2, label="Final network: house routes (%d)" % len(net_h)),
                           Line2D([], [], color="#d50000", lw=2, label="Final network: facility routes (%d)" % len(net_f)), Line2D([], [], color="#00e5ff", lw=1.2, label="Existing TGRAC roads")],
                  loc="lower right", fontsize=7, framealpha=0.92)
    fig.suptitle("Map 4. Alternative candidate routes versus the final shared network (%s)" % _fr.name, fontsize=10)
    foot(fig, CAUTION + " Routes end on roads or on other routes; shared length is counted once." + IMG_NOTE)
    fig.tight_layout(rect=(0, 0.04, 1, 0.96))
    fig.savefig(out / "map4_alternatives_vs_network.png", dpi=300, bbox_inches="tight"); plt.close(fig)
    # ------------------------------------------------------------ map 5: village-level detail, primary versus building-avoiding network
    if a.avoid_run_dir:
        import pandas as pd
        avoid = Path(a.avoid_run_dir)
        bld_cls = gpd.read_file(V / "results" / "v8_instances" / "buildings_v8_full.gpkg", layer="buildings")
        gob = gpd.read_file(V / "reference" / "external" / "google_open_buildings_v3.gpkg")
        names = {str(r.facility_id): r for r in fac.itertuples()}
        short = {"36181600902": "MPPS Damarakunta (school)", "36181600903": "ZPHS Damarakunta (school)", "HEALTH_8734223673": "Sub Centre Damarakunta", "GP_DAMARAKUNTA": "Damarakunta Gram Panchayat HQ (TGRAC point)"}
        OFF5 = {"36181600902": (-190, -52), "36181600903": (-250, 16), "HEALTH_8734223673": (-70, 70), "GP_DAMARAKUNTA": (70, -80)}
        try:
            vf = pd.read_csv(ROOT / "outputs" / "verification" / "facility_verification.csv", dtype={"facility_id": str})
            verdict = dict(zip(vf.facility_id, vf.verdict))
        except Exception:
            verdict = {}
        fig, axs = plt.subplots(1, 2, figsize=(15.5, 7.8))
        for ax, rdir, title in ((axs[0], run, "Primary shared network (penalty x4 on footprint cells)"), (axs[1], avoid, "Building-avoiding shared network (buffer 7.1 m, penalty x100)")):
            arr, e_ = read_img((zext[0], zext[2], zext[1], zext[3]), 2600)
            ax.imshow(np.dstack([(arr[..., :3] * 0.6 + 80).clip(0, 255), arr[..., 3]]).astype("uint8"), extent=(e_[0], e_[1], e_[2], e_[3]), origin="upper")
            roads.plot(ax=ax, color="#00e5ff", lw=1.2, zorder=4)
            for q, c in QC.items():
                g = bld[bld.quality_class == q]
                if len(g):
                    g.plot(ax=ax, facecolor=c, edgecolor="k", lw=0.25, alpha=0.55, zorder=5)
            h_ = gpd.read_file(rdir / "routes.gpkg", layer="routes_network_houses")
            f_ = gpd.read_file(rdir / "routes.gpkg", layer="routes_network_facilities")
            allb = gpd.GeoSeries(bld_cls.geometry.unary_union, crs=32644)
            cross_parts = []
            for x in h_.itertuples():
                oth = bld_cls[bld_cls.cand_id != int(float(x.cand_id))].geometry.unary_union
                it = x.geometry.intersection(oth)
                if it.length > 0.01:
                    cross_parts.append(it)
            h_.plot(ax=ax, color="w", lw=3.2, zorder=6); h_.plot(ax=ax, color="#2962ff", lw=1.8, zorder=7)
            f_.plot(ax=ax, color="w", lw=4.2, zorder=8); f_.plot(ax=ax, color="#d50000", lw=2.6, zorder=9)
            if cross_parts:
                gpd.GeoSeries(cross_parts, crs=32644).plot(ax=ax, color="#ff00ff", lw=3.5, zorder=10)
            for fid, rr in names.items():
                if not inside(rr.geometry, zext):
                    continue
                lon, lat = TO_LL.transform(rr.geometry.x, rr.geometry.y)
                adm = is_admin(rr)
                ax.scatter([rr.geometry.x], [rr.geometry.y], marker="s" if adm else "*", s=170 if adm else 300, c="#aa00ff" if adm else "#ffd600", edgecolors="k", linewidths=1.0, zorder=12)
                ax.annotate("%s\n%.5f°N, %.5f°E" % (short.get(fid, rr.facility_name), lat, lon), (rr.geometry.x, rr.geometry.y), xytext=OFF5.get(fid, (50, -50)), textcoords="offset points",
                            fontsize=7, zorder=13, arrowprops=dict(arrowstyle="-", color="k", lw=0.8), bbox=dict(fc="w", ec="k", alpha=0.93, pad=2))
            furniture(ax, zext, 100, latlon_step=0.002)
            ax.set_title("%s\nhouse routes crossing another footprint: %d (%.0f m, magenta)" % (title, len(cross_parts), sum(c.length for c in cross_parts)), fontsize=9)
        fig.legend(handles=[Patch(fc=QC["PLAUSIBLE"], ec="k", alpha=0.6, label="Footprint: plausible"), Patch(fc=QC["REVIEW"], ec="k", alpha=0.6, label="Footprint: review"), Patch(fc=QC["UNRESOLVED_MERGE"], ec="k", alpha=0.6, label="Footprint: unresolved merge"),
                               Line2D([], [], color="#2962ff", lw=2.2, label="Final shared path: house routes"), Line2D([], [], color="#d50000", lw=2.8, label="Final shared path: facility routes"),
                               Line2D([], [], color="#ff00ff", lw=3.5, label="Route segment crossing another footprint"), Line2D([], [], color="#00e5ff", lw=1.4, label="Existing TGRAC road"),
                               Line2D([], [], marker="*", color="w", mfc="#ffd600", mec="k", ms=13, label="School / health facility (TGRAC coordinate)"),
                               Line2D([], [], marker="s", color="w", mfc="#aa00ff", mec="k", ms=9, label="Gram Panchayat HQ (TGRAC point)")],
                   loc="lower center", ncol=5, fontsize=7.5, framealpha=0.95, bbox_to_anchor=(0.5, 0.075))
        fig.suptitle("Map 5. Main settlement at village scale: buildings, facilities, existing roads and optimised shared paths", fontsize=11, fontweight="bold")
        foot(fig, "The anganwadi (unverified coordinate) is excluded at the project owner's request (inputs/EXCLUSIONS.md); the plan serves 5 facilities: 3 school/health points and 2 Gram Panchayat headquarters points (inputs/ADMIN_UTILITIES.md; MeeSeva and ESD centres have no located coordinate and are not included). Footprints are automatic detections (not a census). Routes enter touching clusters only where a target starts among adjacent buildings. " + CAUTION + IMG_NOTE)
        fig.tight_layout(rect=(0, 0.17, 1, 0.95))
        fig.savefig(out / "map5_village_detail_shared_paths.png", dpi=300, bbox_inches="tight"); plt.close(fig)
    print("maps written to", out)


if __name__ == "__main__":
    main()
