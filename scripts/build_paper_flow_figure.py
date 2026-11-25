#!/usr/bin/env python
"""The paper's one visual flow figure: Telangana locator + the input -> extraction -> output strip of each of the four study areas, at 300 dpi.

    python scripts/build_paper_flow_figure.py                    # -> paper_eris/figures/fig_flow_study_areas.png (+ a pdf copy)
    python scripts/build_paper_flow_figure.py --dry-run          # report which inputs are present, render nothing
    python scripts/build_paper_flow_figure.py --source segmentation   # require the StrongDINOv2Seg state (the paper figure); default auto = segmentation if present, else a PREVIEW from open footprints

Panel 1   Telangana state outline and district boundaries (geoBoundaries gbOpen IND ADM1 / ADM2, ODbL 1.0) with the four study locations and their settlement typologies.
Rows 2-5  Damarakunta -> Adilabad -> Aswaraopeta -> Alampur, each (a) INPUT: Esri World Imagery 0.6 m + existing road network; (b) EXTRACTION: StrongDINOv2Seg footprints (road-gap target houses in orange)
          + verified facilities of the five categories (School, College, Hospital, Government Office, Anganwadi); (c) OUTPUT: existing roads, Stage A independent routes (white dashed),
          Stage B shared network (blue houses, red facilities), zero-crossing 5 m clearance planning, scale bar, north arrow.
Imagery: the local Esri mosaic when present, otherwise the Esri World Imagery export service (same imagery, resampled); every panel and the footer carry the Esri credit.
Scenes come from src/multivillage/area_scenes.py (state + clearance pickles on your PC; Damarakunta: the committed Stage B layers and clearance network).
A figure built from open footprints is stamped PREVIEW and is not meant for the paper: re-run on the PC after the segmentation stages.
"""
from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

import geopandas as gpd
import matplotlib
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
STATE_ROWS = [("damarakunta", "Damarakunta", "Rural"), ("adilabad", "Adilabad", "Urban / semi-urban"), ("aswaraopeta", "Aswaraopeta", "Semi-urban / tribal fringe"), ("alampur", "Alampur", "Heritage / semi-urban")]
LOC = {"damarakunta": (78.7519, 17.7073), "adilabad": (78.5320, 19.6640), "aswaraopeta": (81.1281, 17.2409), "alampur": (78.1351, 15.8800)}     # lon, lat of the study area centres
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
    off = {"damarakunta": (0.5, 0.35), "adilabad": (-0.15, 0.3), "aswaraopeta": (0.35, -0.05), "alampur": (0.3, -0.3)}
    for i, (k, nm, ty) in enumerate(STATE_ROWS, 1):
        lon, lat = LOC[k]
        ax.plot(lon, lat, "o", ms=6, mfc="#d62728", mec="k", mew=0.6, zorder=6)
        dx, dy = off[k]
        ax.annotate(f"{i}  {nm}\n{ty}", (lon, lat), xytext=(lon + dx, lat + dy), fontsize=6.2, ha="left" if dx > 0 else "right", va="center", zorder=7,
                    bbox=dict(fc="w", ec="#999999", lw=0.4, pad=1.6, alpha=0.92), arrowprops=dict(arrowstyle="-", lw=0.5, color="k"))
    ax.set_title("Study locations in Telangana (districts outlined; study districts shaded)", fontsize=7.5, loc="left")
    ax.set_aspect(1.0 / np.cos(np.radians(17.8)))
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)


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


def nice_scale(width_m):
    ok = [s for s in (100, 200, 500, 1000, 2000) if s <= width_m / 4]
    return ok[-1] if ok else 100


def panel(ax, sc, ext, img, kind, scale_m):
    im, ex = img
    ax.imshow(im, extent=ex, origin="upper", zorder=0)
    ax.set_xlim(ext[0], ext[2]); ax.set_ylim(ext[1], ext[3])
    gpd.GeoSeries([sc.cell], crs=CRS).boundary.plot(ax=ax, color=MM.C_BOUND, lw=0.7, zorder=3)
    sc.roads.plot(ax=ax, color="#000000", lw=1.1, alpha=0.4, zorder=3.5)
    sc.roads.plot(ax=ax, color=MM.C_ROAD, lw=0.5, zorder=4)
    if kind == "extract":
        MM.draw_footprints(sc, ax, ext, False)
        MM.plot_facilities(sc, ax, ext, 26)
    elif kind == "output":
        MM.draw_routes(sc, ax, False)
        MM.plot_facilities(sc, ax, ext, 20)
        x0, y0, x1, y1 = ext
        sx, sy = x0 + 0.05 * (x1 - x0), y0 + 0.06 * (y1 - y0)
        ax.plot([sx, sx + scale_m], [sy, sy], color="k", lw=2.2, zorder=30, solid_capstyle="butt")
        ax.text(sx + scale_m / 2, sy + 0.02 * (y1 - y0), f"{scale_m / 1000:g} km" if scale_m >= 1000 else f"{scale_m:g} m", ha="center", fontsize=5.5, zorder=31, bbox=dict(fc="w", ec="none", alpha=0.85, pad=0.8))
        ax.annotate("N", xy=(x1 - 0.07 * (x1 - x0), y1 - 0.04 * (y1 - y0)), xytext=(x1 - 0.07 * (x1 - x0), y1 - 0.2 * (y1 - y0)), ha="center", fontsize=7, fontweight="bold", zorder=31,
                    arrowprops=dict(arrowstyle="-|>", color="k", lw=1.0), bbox=dict(fc="w", ec="none", alpha=0.7, pad=0.8))
    ax.text(0.99, 0.008, CREDIT_SHORT, transform=ax.transAxes, ha="right", va="bottom", fontsize=3.8, color="w", zorder=40, bbox=dict(fc="k", alpha=0.45, ec="none", pad=0.6))
    ax.set_xticks([]); ax.set_yticks([])


def figure_legend(fig):
    h = [Line2D([0], [0], color=MM.C_BOUND, lw=1.6, label="Study-area boundary"), Line2D([0], [0], color=MM.C_ROAD, lw=1.6, label="Existing road"),
         Patch(fc="#ffffff", ec="#ffffff", alpha=0.45, label="Extracted footprint"), Patch(fc=MM.C_GAP, ec="#7a3a00", alpha=0.85, label="Road-gap target house"),
         Line2D([0], [0], color=MM.C_INDEP, lw=1.4, linestyle=(0, (4, 3)), label="Stage A: independent route"), Line2D([0], [0], color=MM.C_SHARED, lw=2, label="Stage B: shared network, houses"),
         Line2D([0], [0], color=MM.C_FAC, lw=2, label="Stage B: facility routes")]
    for k in ("school", "college", "health", "government", "anganwadi"):
        m, c, lab = MM.FSTYLE[k]
        h.append(Line2D([0], [0], marker=m, color="none", markerfacecolor=c, markeredgecolor="w", markersize=8, label={"school": "School", "college": "College", "health": "Hospital", "government": "Government office", "anganwadi": "Anganwadi"}[k]))
    MM.legend(fig, h, loc="lower center", ncol=6, fontsize=5.8, bbox_to_anchor=(0.5, 0.005), handlelength=1.8, columnspacing=1.0, borderpad=0.5)


def build(source: str, out: Path, dpi: int = 300, log=print) -> Path:
    from src.multivillage import area_scenes as AS
    scenes = {}
    for k, nm, ty in STATE_ROWS:
        log(f"scene {k} ...")
        scenes[k] = AS.scene_for(k, source, log)
    preview = any(getattr(s, "preview", False) for s in scenes.values())
    fig = plt.figure(figsize=(7.2, 10.6))
    gs = fig.add_gridspec(5, 3, left=0.045, right=0.995, top=0.985, bottom=0.075, hspace=0.07, wspace=0.025, height_ratios=[1.05, 1, 1, 1, 1])
    axl = fig.add_subplot(gs[0, :])
    locator(axl, log)
    for ri, (k, nm, ty) in enumerate(STATE_ROWS, 1):
        sc = scenes[k]
        ext = square_ext(sc.cell)
        img = imagery(sc, ext)
        scale = nice_scale(ext[2] - ext[0])
        for ci, (kind, ttl) in enumerate((("input", "(a) Input: Esri 0.6 m imagery + existing roads"), ("extract", "(b) StrongDINOv2Seg footprints + verified facilities"), ("output", "(c) Output: zero-crossing planned network"))):
            ax = fig.add_subplot(gs[ri, ci])
            panel(ax, sc, ext, img, kind, scale)
            if ri == 1:
                ax.set_title(ttl, fontsize=5.6, pad=2)
            if ci == 0:
                ax.set_ylabel(f"{ri + 0}. {nm}\n{ty}", fontsize=6.2, labelpad=3)
        st = sc.stats
        fig.text(0.995, gs[ri, 2].get_position(fig).y0 - 0.001, f"{nm}: Stage A {st['indep_m'] / 1000:.2f} km, Stage B {st['shared_m'] / 1000:.2f} km ({100 * (1 - st['shared_m'] / st['indep_m']):.1f}% shorter), "
                 f"{sum(v['routes_crossing'] for v in st['verify'].values())} building crossings; {st['n_gap']:,} targets, {len(sc.fac)} facilities; {st['area_km2']:.1f} km²", ha="right", va="top", fontsize=4.6)
    figure_legend(fig)
    fig.text(0.5, 0.0, f"Basemap imagery: Esri, Maxar, Earthstar Geographics, and the GIS User Community. Boundaries: geoBoundaries gbOpen (ODbL). Footprints are automatic detections; routes are planning alternatives; EPSG:32644.",
             ha="center", va="bottom", fontsize=4.4)
    if preview:
        fig.text(0.5, 0.5, "PREVIEW\nopen footprints: re-run on the PC\nafter the StrongDINOv2Seg stages", ha="center", va="center", fontsize=26, color="red", alpha=0.18, rotation=25, zorder=100)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=dpi)
    fig.savefig(out.with_suffix(".pdf"), dpi=dpi)
    plt.close(fig)
    log(f"wrote {out} ({'PREVIEW from open footprints' if preview else 'StrongDINOv2Seg'})")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", default="auto", choices=["auto", "segmentation", "open"])
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--dpi", type=int, default=300)
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
    build(a.source if a.source != "open" else "open", Path(a.out), a.dpi)


if __name__ == "__main__":
    main()
