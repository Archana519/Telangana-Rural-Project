#!/usr/bin/env python
"""The paper's one visual flow figure: Telangana locator + an INPUT -> FINAL OUTPUT pair for each of the four study areas, at 300 dpi.

    python scripts/build_paper_flow_figure.py --source segmentation   # -> paper_eris/figures/fig_flow_study_areas.png (+ pdf); needs the StrongDINOv2Seg state of each area (your PC)
    python scripts/build_paper_flow_figure.py --dry-run               # report which inputs are present, render nothing
    python scripts/build_paper_flow_figure.py --source open --limit-targets 150 --out some.png   # layout PREVIEW from open footprints (stamped; never for the paper)

Layout: left column = Telangana state locator (district outlines, the four study locations with their typologies) and the shared legend; right column = four horizontal strips in the order
Damarakunta -> Adilabad -> Aswaraopeta -> Alampur, each strictly a pair [INPUT] -> [FINAL OUTPUT]:
  INPUT          Esri World Imagery 0.6 m + study-area boundary + existing road network;
  FINAL OUTPUT   the same imagery with the extracted building footprints (road-gap target houses in orange), the verified facilities (School, College, Hospital, Government Office, Anganwadi)
                 and the Stage B shared network of the zero-crossing 5 m clearance plan (blue: houses, red: facilities), scale bar and north arrow.
Imagery: the local Esri mosaic when present, otherwise the Esri World Imagery export service (same imagery, resampled); every panel and the footer carry the Esri credit.
Scenes come from src/multivillage/area_scenes.py (state + clearance pickles on your PC; Damarakunta: the committed Stage B layers and clearance network).
A figure built from open footprints or from a limited number of targets is stamped PREVIEW.
"""
from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

import geopandas as gpd
import matplotlib
import matplotlib.patches
import numpy as np
import requests
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from PIL import Image
from shapely.geometry import box

matplotlib.use("Agg")
import matplotlib.pyplot as plt                                                         # noqa: E402

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from src.multivillage import master_map as MM, pipeline_summary as PS                    # noqa: E402

CRS = "EPSG:32644"
OUT = REPO / "paper_eris" / "figures" / "fig_flow_study_areas.png"
CREDIT_SHORT = "© Esri, Maxar, Earthstar Geographics"
ROAD_GREY = "#e6e6e6"
STATE_ROWS = [("damarakunta", "Damarakunta", "Rural"), ("adilabad", "Adilabad", "Urban / semi-urban"), ("aswaraopeta", "Aswaraopeta", "Semi-urban / tribal fringe"), ("alampur", "Alampur", "Heritage / semi-urban")]
LOC = {"damarakunta": (78.7519, 17.7073), "adilabad": (78.5320, 19.6640), "aswaraopeta": (81.1281, 17.2409), "alampur": (78.1351, 15.8800)}     # lon, lat of the study area centres
ZOOM_ROWS = ("damarakunta",)          # rows drawn on the main settlement cluster instead of the whole polygon (the 18.5 km2 village is mostly farmland)
HOST_DISTRICTS = {"damarakunta": "Siddipet", "adilabad": "Adilabad", "aswaraopeta": "Bhadradri", "alampur": "Jogulamba"}


def locator(ax, log=print):
    from src.utils import data_downloader_helper as dl
    a1 = gpd.read_file(dl.http_download(dl.GB_BASE.format(lvl="ADM1"), dl.CACHE / "gb_IND_ADM1.geojson"))
    tel = a1[a1.shapeName.str.contains("Telang")].geometry.iloc[0]
    a2 = gpd.read_file(dl.http_download(dl.GB_BASE.format(lvl="ADM2"), dl.CACHE / "gb_IND_ADM2.geojson"))
    d = a2[a2.representative_point().within(tel)]
    gpd.GeoSeries([tel], crs=4326).plot(ax=ax, color="#eef3e8", edgecolor="none", zorder=1)
    host = d[d.shapeName.str.contains("|".join(HOST_DISTRICTS.values()), case=False)]
    host.plot(ax=ax, color="#ffe3a3", edgecolor="none", zorder=2)
    d.boundary.plot(ax=ax, color="#9a9a9a", lw=0.35, zorder=3)
    gpd.GeoSeries([tel], crs=4326).boundary.plot(ax=ax, color="k", lw=0.9, zorder=4)
    for i, (k, nm, ty) in enumerate(STATE_ROWS, 1):
        lon, lat = LOC[k]
        ax.plot(lon, lat, "o", ms=9, mfc="#d62728", mec="k", mew=0.7, zorder=6)
        ax.text(lon, lat, str(i), ha="center", va="center", fontsize=5.6, color="w", fontweight="bold", zorder=7)
    ax.set_title("Telangana: study locations", fontsize=6.4, loc="left", pad=2)
    ax.set_aspect(1.0 / np.cos(np.radians(17.8)))
    ax.set_xticks([]); ax.set_yticks([]); ax.set_xlabel(""); ax.set_ylabel("")
    for sp in ax.spines.values():
        sp.set_visible(False)


def square_ext(cell, pad=120.0):
    b = cell.bounds
    cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
    h = max(b[2] - b[0], b[3] - b[1]) / 2 + pad
    return (cx - h, cy - h, cx + h, cy + h)


def imagery(sc, ext, px=1500):
    """RGBA array for the square window: the local mosaic if present, else the Esri export service (same World Imagery)."""
    from src.multivillage import segmentation_variant as SV
    if sc.mosaic is not None and Path(sc.mosaic).exists():
        img, ex = SV._read_rgb(Path(sc.mosaic), ext, max_px=px)
        return img, ex
    r = None
    for _ in range(4):
        r = requests.get("https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/export", params=dict(bbox=",".join(map(str, ext)), bboxSR=32644, imageSR=32644, size=f"{px},{px}", format="png", f="image"),
                         headers={"User-Agent": "paper-flow-figure/1.0"}, timeout=90)
        try:
            return np.asarray(Image.open(io.BytesIO(r.content)).convert("RGBA")), (ext[0], ext[2], ext[1], ext[3])
        except Exception:
            continue
    raise RuntimeError("Esri imagery could not be obtained (no mosaic and the export service failed)")


def fit_square(ext, img, need=0.995):
    """Largest square window inside `ext` whose imagery has (almost) no no-data pixels, as close to the centre of `ext` as possible: no grey padding bars in the panels."""
    im, ex = img
    if im.shape[2] < 4:
        return ext
    a = im[..., 3] > 0
    if a.all() and ex[0] <= ext[0] + 1e-6 and ex[1] >= ext[2] - 1e-6 and ex[2] <= ext[1] + 1e-6 and ex[3] >= ext[3] - 1e-6:
        return ext
    H, W = a.shape
    px, py = (ex[1] - ex[0]) / W, (ex[3] - ex[2]) / H
    ii = np.pad(a.astype(np.int64).cumsum(0).cumsum(1), ((1, 0), (1, 0)))

    def frac(xl, yb, sd):
        c0, c1 = int(round((xl - ex[0]) / px)), int(round((xl + sd - ex[0]) / px))
        r0, r1 = int(round((ex[3] - (yb + sd)) / py)), int(round((ex[3] - yb) / py))
        if c0 < 0 or r0 < 0 or c1 > W or r1 > H or c1 <= c0 or r1 <= r0:
            return 0.0
        return (ii[r1, c1] - ii[r0, c1] - ii[r1, c0] + ii[r0, c0]) / ((c1 - c0) * (r1 - r0))

    S = ext[2] - ext[0]
    mx, my = (ext[0] + ext[2]) / 2, (ext[1] + ext[3]) / 2
    for sd in np.linspace(S, 0.3 * S, 36):
        cands = []
        for cx in np.linspace(ext[0] + sd / 2, ext[2] - sd / 2, 11):
            for cy in np.linspace(ext[1] + sd / 2, ext[3] - sd / 2, 11):
                if frac(cx - sd / 2, cy - sd / 2, sd) >= need:
                    cands.append(((cx - mx) ** 2 + (cy - my) ** 2, cx, cy))
        if cands:
            _, cx, cy = min(cands)
            return (cx - sd / 2, cy - sd / 2, cx + sd / 2, cy + sd / 2)
    return ext


def nice_scale(width_m):
    ok = [s for s in (100, 200, 500, 1000, 2000) if s <= width_m / 4]
    return ok[-1] if ok else 100


def panel(ax, sc, ext, img, kind, scale_m):
    """kind 'input': imagery + boundary + existing roads; kind 'output': footprints + verified facilities + Stage B shared network (+ scale bar, north arrow)."""
    im, ex = img
    ax.set_facecolor("#d9d9d9")
    ax.imshow(im, extent=ex, origin="upper", zorder=0)
    ax.set_xlim(ext[0], ext[2]); ax.set_ylim(ext[1], ext[3])
    gpd.GeoSeries([sc.cell], crs=CRS).boundary.plot(ax=ax, color=MM.C_BOUND, lw=0.8, zorder=3)
    dense = sc.stats["roads_km"] / max(sc.stats["area_km2"], 1e-6) > 15                 # a dense road layer would hide the imagery at this scale
    sc.roads.plot(ax=ax, color=ROAD_GREY, lw=0.25 if dense else 0.45, alpha=0.65, zorder=4)        # thin, light grey, no casing: the imagery stays visible
    if kind in ("mid", "output"):
        MM.draw_footprints(sc, ax, ext, False, reg_alpha=0.25, gap_alpha=0.75, reg_lw=0.15, gap_lw=0.15)
        if kind == "output":
            MM.draw_routes(sc, ax, False, indep=False, shared=True, lw_house=0.75, lw_fac=1.1, casing=False)
        MM.plot_facilities(sc, ax, ext, 40, edge_lw=0.4)
    if kind == "output":
        x0, y0, x1, y1 = ext
        sx, sy = x0 + 0.05 * (x1 - x0), y0 + 0.06 * (y1 - y0)
        ax.plot([sx, sx + scale_m], [sy, sy], color="k", lw=2.2, zorder=30, solid_capstyle="butt")
        ax.text(sx + scale_m / 2, sy + 0.02 * (y1 - y0), f"{scale_m / 1000:g} km" if scale_m >= 1000 else f"{scale_m:g} m", ha="center", fontsize=5.5, zorder=31, bbox=dict(fc="w", ec="none", alpha=0.85, pad=0.8))
        ax.annotate("N", xy=(x1 - 0.07 * (x1 - x0), y1 - 0.04 * (y1 - y0)), xytext=(x1 - 0.07 * (x1 - x0), y1 - 0.2 * (y1 - y0)), ha="center", fontsize=7, fontweight="bold", zorder=31,
                    arrowprops=dict(arrowstyle="-|>", color="k", lw=1.0), bbox=dict(fc="w", ec="none", alpha=0.7, pad=0.8))
    ax.text(0.99, 0.008, CREDIT_SHORT, transform=ax.transAxes, ha="right", va="bottom", fontsize=3.8, color="w", zorder=40, bbox=dict(fc="k", alpha=0.45, ec="none", pad=0.6))
    ax.set_xticks([]); ax.set_yticks([]); ax.set_xlabel(""); ax.set_ylabel("")


def figure_legend(fig, loc="lower left", anchor=(0.0, 0.0), ncol=1, fontsize=5.8):
    h = [Line2D([0], [0], color=MM.C_BOUND, lw=1.6, label="Study-area boundary"), Line2D([0], [0], color=ROAD_GREY, lw=1.6, label="Existing road"),
         Patch(fc="#ffffff", ec="#ffffff", alpha=0.45, label="Extracted building footprint"), Patch(fc=MM.C_GAP, ec="#7a3a00", alpha=0.85, label="Road-gap target house"),
         Line2D([0], [0], color=MM.C_SHARED, lw=2, label="Stage B shared network: houses"), Line2D([0], [0], color=MM.C_FAC, lw=2, label="Stage B shared network: facilities")]
    for k in ("school", "college", "health", "government", "anganwadi"):
        m, c, lab = MM.FSTYLE[k]
        h.append(Line2D([0], [0], marker=m, color="none", markerfacecolor=c, markeredgecolor="w", markersize=6.5, label={"school": "School", "college": "College", "health": "Hospital", "government": "Government office", "anganwadi": "Anganwadi"}[k]))
    return MM.legend(fig, h, loc=loc, ncol=ncol, fontsize=fontsize, bbox_to_anchor=anchor, handlelength=1.8, borderpad=0.6, labelspacing=0.45)


def build(source: str, out: Path, dpi: int = 300, log=print, limit_targets=None) -> Path:
    from src.multivillage import area_scenes as AS
    scenes = {}
    for k, nm, ty in STATE_ROWS:
        log(f"scene {k} ...")
        scenes[k] = AS.scene_for(k, source, log, limit_targets)
    preview = any(getattr(s, "preview", False) for s in scenes.values())
    W, H = 7.2, 11.2
    fig = plt.figure(figsize=(W, H))
    left, cw, cgap = 0.075, 0.28, 0.02                          # three square panels per row: fractions of the figure width
    ch = cw * W / H                                              # panel height (fraction) for a square panel
    rgap, top0 = 0.034, 0.862
    # header band: Telangana locator (own band, never touches the column headers) and the key / legend beside it
    axl = fig.add_axes([left, 0.893, 0.15, 0.1])
    locator(axl, log)
    axl.set_title("", loc="left"); axl.set_title("")
    keyax = fig.add_axes([left + 0.17, 0.885, 0.74, 0.11]); keyax.axis("off")
    keyax.text(0.0, 0.97, "Study areas (numbered on the map; study districts shaded)", fontsize=5.8, fontweight="bold", va="top")
    keyax.text(0.0, 0.80, "   ".join(f"{i}  {nm} ({ty.lower()})" for i, (k, nm, ty) in enumerate(STATE_ROWS, 1)), fontsize=5.4, va="top")
    figure_legend(fig, loc="lower left", anchor=(left + 0.17, 0.888), ncol=4, fontsize=4.9)
    heads = ["(a) Input: 0.6 m imagery,\nstudy-area boundary, roads", "(b) StrongDINOv2Seg footprints\n+ verified facilities", "(c) Output: zero-crossing\nStage B shared network"]
    for ci, t in enumerate(heads):
        fig.text(left + ci * (cw + cgap) + cw / 2, top0 + 0.006, t, ha="center", va="bottom", fontsize=5.8, fontweight="bold", linespacing=1.2)
    for ri, (k, nm, ty) in enumerate(STATE_ROWS):
        sc = scenes[k]
        ext = square_ext(sc.cell)
        zoomed = k in ZOOM_ROWS
        if zoomed:                                   # the settlement-cluster window of the master planning map, made square (about 950 m)
            z = MM.pick_zoom(sc)
            cx, cy, hh = (z[0] + z[2]) / 2, (z[1] + z[3]) / 2, min(z[2] - z[0], z[3] - z[1]) / 2
            ext = (cx - hh, cy - hh, cx + hh, cy + hh)
        img = imagery(sc, ext)
        ext = fit_square(ext, img)                    # crop to imagery that exists: no grey or white padding in the frame
        scale = nice_scale(ext[2] - ext[0])
        y0 = top0 - ri * (ch + rgap) - ch
        axs = []
        for ci, kind in enumerate(("input", "mid", "output")):
            ax = fig.add_axes([left + ci * (cw + cgap), y0, cw, ch])
            panel(ax, sc, ext, img, kind, scale)
            ax.set_aspect("equal", adjustable="box")
            axs.append(ax)
        st = sc.stats
        sub = f"{ty}, settlement-cluster zoom" if zoomed else f"{ty}, {st['area_km2']:.1f} km$^2$"
        fig.text(0.032, y0 + ch / 2, f"{ri + 1}. {nm}\n{sub}", rotation=90, ha="center", va="center", fontsize=6.0, fontweight="bold", linespacing=1.3)
        axs[2].set_xlabel(f"Stage A {st['indep_m'] / 1000:.2f} km $\\rightarrow$ Stage B {st['shared_m'] / 1000:.2f} km ({100 * (1 - st['shared_m'] / st['indep_m']):.1f}% shorter)\n"
                          f"{sum(v['routes_crossing'] for v in st['verify'].values())} building crossings; {len(sc.fac)} verified facilities", fontsize=4.8, labelpad=3, linespacing=1.25)
    fig.text(0.075, 0.004, "Basemap imagery: Esri, Maxar, Earthstar Geographics, and the GIS User Community. Boundaries: geoBoundaries gbOpen (ODbL). Footprints are automatic detections; routes are planning alternatives, not engineered roads. EPSG:32644.", fontsize=4.6, va="bottom")
    if preview:
        fig.text(0.5, 0.5, "PREVIEW\nopen footprints / limited targets: re-run on the PC\nafter the StrongDINOv2Seg stages", ha="center", va="center", fontsize=26, color="red", alpha=0.18, rotation=25, zorder=100)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=dpi)
    fig.savefig(out.with_suffix(".pdf"), dpi=dpi)
    plt.close(fig)
    log(f"wrote {out} ({'PREVIEW' if preview else 'StrongDINOv2Seg'})")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", default="auto", choices=["auto", "segmentation", "open"])
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--limit-targets", type=int, default=None, help="PREVIEW only: plan the clearance network for the first N road-gap targets (stamped PREVIEW)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if a.dry_run:
        from src.multivillage import area_scenes as AS
        for k, nm, ty in STATE_ROWS:
            ar = PS.AREAS[k]
            if k == "damarakunta":
                need = [REPO / "Siddipet/Damarakunta/results/v8_instances/buildings_v8_full.gpkg", ar["maps"] / "clearance_network_v1.pkl", REPO / "configs/multivillage/villages/damarakunta_verified_facilities.csv"]
            else:
                d = REPO / "data" / "villages" / ar["config"]
                need = [d / "state_segmentation.pkl", d / "clearance_network_v1.pkl", d / "state.pkl"]
            print(f"{nm}: " + ", ".join(f"{p.name} {'OK' if p.exists() else 'absent'}" for p in need) + f", mosaic {'OK' if AS.mosaic_path(k).exists() else 'absent (Esri export service is used)'}")
        print("locator: geoBoundaries ADM1/ADM2 (downloaded and cached on first use)")
        return
    build(a.source, Path(a.out), a.dpi, limit_targets=a.limit_targets)


if __name__ == "__main__":
    main()
