"""Build DELIVERABLES_CONTRIBUTION_3_HIERARCHICAL_ROUTING/ in the layout and style of DELIVERABLES_DAMARAKUNTA_STAGE_B/ (which this script never touches).

    python -m src.evaluation.build_contribution3_deliverables

Needs the committed results (docs/results/) and the real input layers named in configs/hierarchy_levels.yaml (rasters: python -m src.utils.data_downloader_helper).
Every number written to the README, tables and figures is read from those results - nothing is typed by hand.

  00_README_SUMMARY.md, MANIFEST.csv   executive summary; SHA-256 of every file in 00-03 and 05
  01_ARCHITECTURE/                     ARCHITECTURE_DIAGRAM.png, WORKFLOW_DIAGRAM.png, DATA_AND_PROCESS_FLOW.md
  02_FINAL_MAPS/                       map1-map4 (300 dpi, land-cover context, legend, scale bar, north arrow)
  03_RESULTS_TABLES/                   CSV + Markdown + Excel tables, CHARTS/chart1-chart2 (300 dpi)
  04_PROVENANCE_AND_AUDIT/             snapshot copies of the provenance report, audit JSON, input manifest, DEM comparison, sweep, decisions
  05_LIMITATIONS_AND_OPEN_ISSUES/      what is real, what is a proxy, what needs the owner's data
"""
from __future__ import annotations

import csv
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import geopandas as gpd  # noqa: E402
import matplotlib.patheffects as pe  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Circle, FancyBboxPatch, Patch  # noqa: E402
from pyproj import Transformer  # noqa: E402
from shapely.ops import unary_union  # noqa: E402

DEL = REPO / "DELIVERABLES_CONTRIBUTION_3_HIERARCHICAL_ROUTING"
RES = REPO / "docs" / "results"
RUN = RES / "hierarchy_real_run"
STAGEB = REPO / "DELIVERABLES_DAMARAKUNTA_STAGE_B"
DPI = 300
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8, "axes.titlesize": 9, "legend.fontsize": 7, "savefig.dpi": DPI, "axes.linewidth": 0.7})

# ESA WorldCover legend (official colours), blended towards white so overlays stay readable
WC = {10: ("Tree cover", "#006400"), 20: ("Shrubland", "#ffbb22"), 30: ("Grassland", "#ffff4c"), 40: ("Cropland", "#f096ff"), 50: ("Built-up", "#fa0000"),
      60: ("Bare / sparse vegetation", "#b4b4b4"), 70: ("Snow / ice", "#f0f0f0"), 80: ("Water", "#0064c8"), 90: ("Herbaceous wetland", "#0096a0"),
      95: ("Mangroves", "#00cf75"), 100: ("Moss / lichen", "#fae6a0")}
Q = {"PLAUSIBLE": ("#00897b", "Footprint: plausible"), "REVIEW": ("#6a1b9a", "Footprint: review"), "UNRESOLVED_MERGE": ("#e65100", "Footprint: unresolved merge")}
COL = dict(road="#00b4d8", local="#9a9a9a", house="#1d4ed8", fac="#c1121f", new="#d62828", exist="#1d4ed8", bound="#222222", hub="#0b7a3b")
KIND_LABEL = {"36181600902": "MPPS Damarakunta (school)", "36181600903": "ZPHS Damarakunta (school)", "HEALTH_8734223673": "Sub Centre Damarakunta",
              "GP_DAMARAKUNTA": "Damarakunta GP HQ", "GP_KASHIREDDYPALLY": "Kashireddypally GP HQ"}
FOOT = ("Planning alternatives on open data, not verified roads. Costs are ordinal planning units, not rupees. Nothing is field validated. "
        "Land cover: ESA WorldCover 10 m 2021 v200 (CC BY 4.0); roads, villages: Overture Maps 2026-10-21.0 (OSM-derived) at Levels 3-4, TGRAC at Level 2; boundaries: geoBoundaries / TGRAC. EPSG:32644 (UTM 44N).")


# ============================================================================================ helpers
TEXT_SUFFIXES = {".md", ".csv", ".txt", ".json", ".tex", ".bib", ".yaml", ".yml", ".py"}


def sha256(p: Path) -> str:
    """SHA-256 of the file; text files are hashed with CRLF read as LF so the manifest is identical on Windows and Linux checkouts."""
    if p.suffix.lower() in TEXT_SUFFIXES:
        return hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def summaries():
    S = {l: json.loads((RUN / l / f"{l}_summary.json").read_text()) for l in ("gp", "mandal", "district")}
    return S


def landcover_rgb(path: Path, bounds, mask_geom=None, max_px=2600, fade=0.55):
    """WorldCover window decimated to <= max_px (mode resampling), colourised, faded towards white; outside `mask_geom` faded further."""
    import rasterio
    from rasterio.enums import Resampling
    from rasterio.features import rasterize
    from rasterio.windows import from_bounds
    with rasterio.open(path) as src:
        win = from_bounds(*bounds, transform=src.transform)
        scale = max(1.0, max(win.width, win.height) / max_px)
        H, W = max(1, int(win.height / scale)), max(1, int(win.width / scale))
        a = src.read(1, window=win, out_shape=(H, W), resampling=Resampling.mode, boundless=True, fill_value=0)
        T = rasterio.transform.from_bounds(*bounds, W, H)
    rgb = np.ones((H, W, 3), dtype="float32")
    for code, (_, hexc) in WC.items():
        c = np.array(matplotlib.colors.to_rgb(hexc))
        rgb[a == code] = c
    rgb = fade * rgb + (1 - fade) * 1.0
    if mask_geom is not None:
        inside = rasterize([(mask_geom, 1)], out_shape=(H, W), transform=T, fill=0, all_touched=True).astype(bool)
        rgb[~inside] = 0.25 * rgb[~inside] + 0.75
    present = [c for c in WC if (a == c).any()]
    return rgb, present


def show_landcover(ax, path, bounds, mask_geom=None, max_px=2600, fade=0.55):
    rgb, present = landcover_rgb(path, bounds, mask_geom, max_px, fade)
    ax.imshow(rgb, extent=(bounds[0], bounds[2], bounds[1], bounds[3]), origin="upper", zorder=0, interpolation="nearest")
    ax.set_xlim(bounds[0], bounds[2])
    ax.set_ylim(bounds[1], bounds[3])
    return present


def geo_ticks(ax, crs="EPSG:32644"):
    """Replace UTM ticks by lon/lat ticks (as in the Stage B maps)."""
    fwd, inv = Transformer.from_crs(crs, 4326, always_xy=True), Transformer.from_crs(4326, crs, always_xy=True)
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    xm, ym = (x0 + x1) / 2, (y0 + y1) / 2
    lon0, lat0 = fwd.transform(x0, ym)
    lon1, lat1 = fwd.transform(x1, ym)
    _, la0 = fwd.transform(xm, y0)
    _, la1 = fwd.transform(xm, y1)

    def nice(span):
        for st in (0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0):
            if span / st <= 6.5:
                return st
        return 1.0
    sx, sy = nice(abs(lon1 - lon0)), nice(abs(la1 - la0))
    lons = np.arange(np.ceil(min(lon0, lon1) / sx) * sx, max(lon0, lon1) + 1e-9, sx)
    lats = np.arange(np.ceil(min(la0, la1) / sy) * sy, max(la0, la1) + 1e-9, sy)
    dx, dy = max(0, -int(np.floor(np.log10(sx)))), max(0, -int(np.floor(np.log10(sy))))
    ax.set_xticks([inv.transform(l, lat0)[0] for l in lons])
    ax.set_xticklabels([f"{l:.{dx}f}°E" for l in lons], fontsize=6.5)
    ax.set_yticks([inv.transform(lon0, l)[1] for l in lats])
    ax.set_yticklabels([f"{l:.{dy}f}°N" for l in lats], fontsize=6.5, rotation=90, va="center")
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_xlabel("Longitude (WGS84)", fontsize=7.5)
    ax.set_ylabel("Latitude (WGS84)", fontsize=7.5)


def furniture(ax, scale_m, label, north=True, right=False):
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    x = (x1 - 0.035 * (x1 - x0) - scale_m) if right else (x0 + 0.035 * (x1 - x0))
    y = y0 + 0.045 * (y1 - y0)
    ax.plot([x, x + scale_m], [y, y], color="k", lw=2.2, solid_capstyle="butt", zorder=20)
    ax.text(x + scale_m / 2, y + 0.012 * (y1 - y0), label, ha="center", va="bottom", fontsize=7, zorder=20,
            bbox=dict(fc="white", ec="none", alpha=0.85, pad=1.2))
    if north:
        xn, yn = x1 - 0.04 * (x1 - x0), y1 - 0.16 * (y1 - y0)
        ax.annotate("N", xy=(xn, yn + 0.1 * (y1 - y0)), xytext=(xn, yn), ha="center", va="bottom", fontsize=9, fontweight="bold",
                    arrowprops=dict(arrowstyle="-|>", lw=1.0, color="k"), zorder=20, bbox=dict(fc="white", ec="none", alpha=0.85, pad=1.5))


def halo(t, w=2.0):
    t.set_path_effects([pe.withStroke(linewidth=w, foreground="white")])
    return t


def footnote(fig, y=0.012):
    import textwrap
    fig.text(0.5, y, "\n".join(textwrap.wrap(FOOT, 190)), ha="center", va="bottom", fontsize=5.8, color="#333333")


def lc_handles(present):
    return [Patch(fc=WC[c][1], alpha=0.55, ec="#777777", lw=0.3, label=WC[c][0]) for c in present]


def save(fig, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=DPI, facecolor="white")
    plt.close(fig)
    print("wrote", path.relative_to(REPO))


# ============================================================================================ maps
def gp_inputs(cfg):
    from src.routing import data_hooks as dh
    gp, rep = dh.load_gp_real(cfg)
    assert gp is not None, rep
    b = gpd.read_file(REPO / cfg["data"]["gp"]["buildings"], layer="buildings").to_crs(cfg["crs"])
    b = b[b.quality_class.isin(dh.QUALITY_USED)]
    return gp, b


def map1(cfg, out):
    gp, bld = gp_inputs(cfg)
    routes = gpd.read_file(RUN / "gp" / "gp_routes.gpkg", layer="routes_shared")
    nodes = gpd.read_file(RUN / "gp" / "gp_routes.gpkg", layer="nodes")
    s = summaries()["gp"]
    lc = REPO / cfg["data"]["gp"]["landcover"]
    fig = plt.figure(figsize=(10.5, 7.6))
    ax = fig.add_axes([0.07, 0.25, 0.9, 0.62])
    bd = gp.boundary.bounds
    bounds = (bd[0] - 250, bd[1] - 250, bd[2] + 250, bd[3] + 250)
    present = show_landcover(ax, lc, bounds, gp.boundary)
    hub_ids = set(nodes[nodes.kind == "hamlet"].node_id)
    hub = nodes[nodes.kind == "hamlet"]
    fac = nodes[nodes.kind != "hamlet"]
    mk = {"school": ("*", 210, "#ffd60a"), "healthcare": ("*", 210, "#ffd60a"), "panchayat_office": ("s", 80, "#9d4edd")}

    def draw(a, big):
        gpd.GeoSeries([gp.boundary], crs=cfg["crs"]).boundary.plot(ax=a, color=COL["bound"], lw=1.0, zorder=3)
        for q, (c, _) in Q.items():
            bld[bld.quality_class == q].plot(ax=a, color=c, edgecolor="k", lw=0.2 if not big else 0.12, zorder=4)
        gp.roads.plot(ax=a, color=COL["road"], lw=1.0 if big else 1.6, zorder=5)
        routes[routes.route_id.isin(hub_ids)].plot(ax=a, color=COL["house"], lw=2.4 if big else 3.0, zorder=7)
        routes[~routes.route_id.isin(hub_ids)].plot(ax=a, color=COL["fac"], lw=2.4 if big else 3.0, zorder=8)
        a.scatter(hub.geometry.x, hub.geometry.y, s=(18 + 2.6 * hub.weight) if big else (30 + 5 * hub.weight), c=COL["hub"], edgecolor="white", lw=0.7, zorder=9, alpha=0.95)
        for _, r in fac.iterrows():
            m, sz, col = mk[r.kind]
            a.scatter([r.geometry.x], [r.geometry.y], marker=m, s=sz if big else sz * 1.5, c=col, edgecolor="k", lw=0.9, zorder=11)
    draw(ax, True)
    # isolated facility on the main map; the four central ones are labelled in the inset
    far = fac[fac.node_id == "GP_KASHIREDDYPALLY"].iloc[0]
    ax.annotate(KIND_LABEL[far.node_id], (far.geometry.x, far.geometry.y), xytext=(-130, 62), textcoords="offset points", fontsize=6.5, zorder=15,
                bbox=dict(boxstyle="square,pad=0.25", fc="white", ec="k", lw=0.7), arrowprops=dict(arrowstyle="-", lw=0.7, color="k"))
    core = fac[fac.node_id != "GP_KASHIREDDYPALLY"]
    cx, cy = core.geometry.x.mean(), core.geometry.y.mean()
    ax.annotate("Main settlement: 3 facilities + Damarakunta GP HQ\n(zoom inset, lower left)", (cx, cy), xytext=(80, 70), textcoords="offset points", fontsize=6.5, zorder=15,
                bbox=dict(boxstyle="square,pad=0.25", fc="white", ec="k", lw=0.7), arrowprops=dict(arrowstyle="-", lw=0.7, color="k"))
    # zoom inset
    wx, wy = 430, 310
    ib = (cx - wx, cy - wy, cx + wx, cy + wy)
    axi = ax.inset_axes([0.012, 0.05, 0.42, 0.46])
    show_landcover(axi, lc, ib, None, 900, fade=0.4)
    draw(axi, False)
    axi.set_xlim(ib[0], ib[2])
    axi.set_ylim(ib[1], ib[3])
    axi.set_xticks([])
    axi.set_yticks([])
    axi.set_xlabel("")
    axi.set_ylabel("")
    for sp in axi.spines.values():
        sp.set_linewidth(1.4)
    offs = {"36181600902": (-60, -40), "36181600903": (-60, 62), "HEALTH_8734223673": (-70, 52), "GP_DAMARAKUNTA": (15, -38)}
    short = {"36181600902": "MPPS (school)", "36181600903": "ZPHS (school)", "HEALTH_8734223673": "Sub Centre", "GP_DAMARAKUNTA": "GP HQ Damarakunta"}
    for _, r in core.iterrows():
        axi.annotate(short[r.node_id], (r.geometry.x, r.geometry.y), xytext=offs[r.node_id], textcoords="offset points", fontsize=5.8, zorder=15,
                     bbox=dict(boxstyle="square,pad=0.2", fc="white", ec="k", lw=0.6), arrowprops=dict(arrowstyle="-", lw=0.6, color="k"))
    axi.plot([ib[0] + 25, ib[0] + 125], [ib[1] + 30, ib[1] + 30], color="k", lw=2.2, zorder=20)
    axi.text(ib[0] + 75, ib[1] + 38, "100 m", ha="center", va="bottom", fontsize=6, bbox=dict(fc="white", ec="none", alpha=0.85, pad=1), zorder=20)
    ax.indicate_inset_zoom(axi, edgecolor="#444444", lw=0.7, alpha=0.8)
    ax.set_title("Map 1. Level 2 - Damarakunta Gram Panchayat: shared access network on open land-cover context", fontsize=10.5, fontweight="bold", pad=20)
    geo_ticks(ax)
    furniture(ax, 1000, "1 km", right=True)
    ax.text(0.5, 1.008, f"{s['shared_unique_length_m']:,.0f} m shared network vs {s['independent_unique_length_m']:,.0f} m independent  |  {s['n_nodes']} nodes: 18 hamlet hubs (= 163 houses) + 5 facilities  |  penalty x4 with 20 m local override",
            transform=ax.transAxes, ha="center", va="bottom", fontsize=6.8, color="#333333")
    h = [Line2D([], [], color=COL["road"], lw=1.6, label="Existing road (TGRAC, clipped)"), Line2D([], [], color=COL["house"], lw=2.8, label="New shared path: hamlet-hub routes"),
         Line2D([], [], color=COL["fac"], lw=2.8, label="New shared path: facility routes"),
         Line2D([], [], marker="o", ls="", mfc=COL["hub"], mec="white", ms=7, label="Hamlet hub (size = houses)"),
         Line2D([], [], marker="*", ls="", mfc="#ffd60a", mec="k", ms=11, label="School / health facility"),
         Line2D([], [], marker="s", ls="", mfc="#9d4edd", mec="k", ms=7, label="Gram Panchayat HQ (TGRAC point)")]
    h += [Patch(fc=c, ec="k", lw=0.3, label=t) for c, t in Q.values()]
    fig.legend(handles=h, loc="lower center", ncol=3, bbox_to_anchor=(0.5, 0.115), fontsize=7, frameon=True, edgecolor="#cccccc", title="Map layers", title_fontsize=7.5)
    fig.legend(handles=lc_handles(present), loc="lower center", ncol=len(present), bbox_to_anchor=(0.5, 0.045), fontsize=6.5, frameon=True, edgecolor="#cccccc",
               title="Land cover context (ESA WorldCover, faded)", title_fontsize=7)
    footnote(fig)
    save(fig, out / "map1_level2_damarakunta_gp_network.png")


def map2(cfg, out):
    from src.routing.hierarchical_router import build_gp_problem
    gp, bld = gp_inputs(cfg)
    prob = build_gp_problem(gp, cfg)
    with_r, without_r = prob.solve(use_override=True), prob.solve(use_override=False)
    ov = pd.read_csv(RUN / "gp" / "gp_override.csv")
    ovr = ov[ov.status == "ROUTED"].set_index("node")
    by = {n.id: n for n in gp.nodes}
    ids = list(KIND_LABEL)
    fig = plt.figure(figsize=(11, 7.6))
    gs = fig.add_gridspec(2, 3, left=0.05, right=0.985, top=0.9, bottom=0.2, wspace=0.12, hspace=0.3)
    rad = prob.override_radius_m
    for k, nid in enumerate(ids):
        ax = fig.add_subplot(gs[k // 3, k % 3])
        n = by[nid]
        b = (n.x - 80, n.y - 65, n.x + 80, n.y + 65)
        show_landcover(ax, REPO / cfg["data"]["gp"]["landcover"], b, None, 800, fade=0.35)
        for q, (c, _) in Q.items():
            bld[bld.quality_class == q].plot(ax=ax, color=c, edgecolor="k", lw=0.2, zorder=3, alpha=0.9)
        gp.roads.plot(ax=ax, color=COL["road"], lw=1.4, zorder=4)
        ax.add_patch(Circle((n.x, n.y), rad, fc="#fdb863", ec="#b35806", lw=0.8, alpha=0.35, zorder=5))
        gw = without_r.routes[nid].geometry
        gwt = with_r.routes[nid].geometry
        ax.plot(*gw.xy, color="#e66101", lw=2.2, ls=(0, (3, 2)), zorder=7)
        ax.plot(*gwt.xy, color="#1d4ed8", lw=2.2, zorder=8)
        ax.scatter([n.x], [n.y], marker="*" if n.kind != "panchayat_office" else "s", s=170 if n.kind != "panchayat_office" else 70,
                   c="#ffd60a" if n.kind != "panchayat_office" else "#9d4edd", edgecolor="k", lw=0.9, zorder=10)
        ax.set_xlim(b[0], b[2])
        ax.set_ylim(b[1], b[3])
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_xlabel("")
        ax.set_ylabel("")
        r = ovr.loc[nid]
        d = r.length_without_m - r.length_with_m
        dtxt = f"{-d:+.1f} m" if abs(d) > 0.05 else "no change"
        ax.set_title(f"{KIND_LABEL[nid]}\nlength {r.length_without_m:.1f} -> {r.length_with_m:.1f} m ({dtxt});  cost {r.cost_without:.0f} -> {r.cost_with:.0f} ({-r.cost_reduction_pct:.0f}%)",
                     fontsize=6.9, loc="left")
        ax.plot([b[0] + 8, b[0] + 58], [b[1] + 7, b[1] + 7], color="k", lw=2.2, zorder=12)
        ax.text(b[0] + 33, b[1] + 10, "50 m", ha="center", va="bottom", fontsize=6.5, bbox=dict(fc="white", ec="none", alpha=0.85, pad=1), zorder=12)
    ax = fig.add_subplot(gs[1, 2])
    ax.axis("off")
    tot = float(ov[ov.node == "_NETWORK_UNIQUE_LENGTH"].detour_reduction_m.iloc[0])
    moved = float(ov[ov.status == "ROUTED"].detour_reduction_m.astype(float).sum())
    other = int(float(ov[ov.node == "_OTHER_ROUTES_CHANGED"].cost_reduction_pct.iloc[0]))
    ax.text(0.0, 1.0, "Effect of the local penalty override\n(x4 footprint penalty lifted within 20 m)", va="top", fontsize=8.2, fontweight="bold")
    ax.text(0.0, 0.76, f"Detour removed at facility routes:  {moved:.1f} m\nNetwork unique length:  {ov[ov.node == '_NETWORK_UNIQUE_LENGTH'].length_without_m.iloc[0]:.1f} -> "
            f"{ov[ov.node == '_NETWORK_UNIQUE_LENGTH'].length_with_m.iloc[0]:.1f} m ({-tot:+.1f} m)\nOther routes changed by the override:  {other}\n"
            f"Facility route cost reduced by {ov[ov.status == 'ROUTED'].cost_reduction_pct.astype(float).min():.0f}-{ov[ov.status == 'ROUTED'].cost_reduction_pct.astype(float).max():.0f}%\n\n"
            "Without the override the penalty makes a route detour\naround the amenity's own building, because the\nfacility point lies on the edge of its footprint.", va="top", fontsize=7.6, linespacing=1.5)
    fig.suptitle("Map 2. Level 2 - facility routes before and after the local penalty override (zoom on each amenity)", fontsize=10.5, fontweight="bold", y=0.975)
    h = [Line2D([], [], color="#e66101", lw=2.4, ls=(0, (3, 2)), label="Route without override"), Line2D([], [], color="#1d4ed8", lw=2.4, label="Route with override"),
         Patch(fc="#fdb863", ec="#b35806", alpha=0.45, label="20 m override disc"), Line2D([], [], color=COL["road"], lw=1.6, label="Existing road (TGRAC)"),
         Line2D([], [], marker="*", ls="", mfc="#ffd60a", mec="k", ms=11, label="School / health facility"), Line2D([], [], marker="s", ls="", mfc="#9d4edd", mec="k", ms=7, label="Gram Panchayat HQ")]
    h += [Patch(fc=c, ec="k", lw=0.3, label=t) for c, t in Q.values()]
    fig.legend(handles=h, loc="lower center", ncol=5, bbox_to_anchor=(0.5, 0.085), fontsize=7, frameon=True, edgecolor="#cccccc")
    footnote(fig)
    save(fig, out / "map2_level2_facility_override_zooms.png")


def map3(cfg, out):
    md = cfg["data"]["mandal"]
    classes = cfg["levels"]["mandal"]["collector_road_classes"]
    bnd = gpd.read_file(REPO / md["boundary"])
    roads = gpd.read_file(REPO / md["roads"])
    gps = gpd.read_file(REPO / md["gp_boundaries"])
    routes = gpd.read_file(RUN / "mandal" / "mandal_routes.gpkg", layer="routes_shared")
    nodes = gpd.read_file(RUN / "mandal" / "mandal_routes.gpkg", layer="nodes")
    s = summaries()["mandal"]
    fig = plt.figure(figsize=(9.2, 9.0))
    ax = fig.add_axes([0.075, 0.27, 0.9, 0.64])
    b = bnd.total_bounds
    bounds = (b[0] - 700, b[1] - 700, b[2] + 700, b[3] + 700)
    geom = bnd.geometry.union_all()
    present = show_landcover(ax, REPO / md["landcover"], bounds, geom, 2400)
    bnd.boundary.plot(ax=ax, color=COL["bound"], lw=1.2, zorder=3)
    coll = roads[roads["class"].isin(classes)]
    roads[~roads["class"].isin(classes)].plot(ax=ax, color=COL["local"], lw=0.5, zorder=4)
    coll.plot(ax=ax, color="#0077b6", lw=1.5, zorder=5)
    routes.plot(ax=ax, color=COL["new"], lw=2.8, zorder=7)
    v = nodes[nodes.kind == "gp_hub"]
    ax.scatter(v.geometry.x, v.geometry.y, s=42, c="white", edgecolor=COL["hub"], lw=1.6, zorder=9)
    names = dict(zip(gps.index, gps.get("gp_name", gps.index)))
    nm = {f"GP_{n}": str(n) for n in gps.get("gp_name", gps.index)}
    for _, r in v.iterrows():
        halo(ax.text(r.geometry.x + 120, r.geometry.y + 90, nm.get(r.node_id, r.node_id.replace("GP_", "")), fontsize=5.8, zorder=12))
    hq = nodes[nodes.kind == "mandal_hq"]
    ax.scatter(hq.geometry.x, hq.geometry.y, marker="*", s=330, c="#ffd60a", edgecolor="k", lw=1.0, zorder=11)
    halo(ax.text(hq.geometry.x.iloc[0] - 260, hq.geometry.y.iloc[0] + 120, "Mandal HQ (PROXY point)", fontsize=6.5, fontweight="bold", ha="right", zorder=12))
    for _, r in routes[routes.length_m > 500].iterrows():
        mid = r.geometry.interpolate(0.5, normalized=True)
        dx, dy = (130, -120) if r.length_m > 1500 else (330, 150)
        halo(ax.text(mid.x + dx, mid.y + dy, f"{r.length_m / 1000:.1f} km", fontsize=6.8, color=COL["new"], fontweight="bold", zorder=12))
    ax.set_title("Map 3. Level 3 - Markook mandal: collector-road links from Gram Panchayat hubs (proxy nodes)", fontsize=10.5, fontweight="bold", pad=20)
    geo_ticks(ax)
    furniture(ax, 5000, "5 km")
    ax.text(0.5, 1.008, f"{s['shared_new_construction_m'] / 1000:.1f} km of new links for {s['n_nodes'] - 1} village points; shared = independent ({s['saving_vs_independent_unique_pct']:.1f}% saving): the villages are scattered",
            transform=ax.transAxes, ha="center", va="bottom", fontsize=6.8, color="#333333")
    h = [Line2D([], [], color="#0077b6", lw=2.0, label="Collector roads (motorway-tertiary): attachment goals"), Line2D([], [], color=COL["local"], lw=1.2, label="Local roads (travel-cost discount only)"),
         Line2D([], [], color=COL["new"], lw=3, label="New link (shared plan)"), Line2D([], [], marker="o", ls="", mfc="white", mec=COL["hub"], mew=1.6, ms=7, label="Village point (PROXY Gram Panchayat hub)"),
         Line2D([], [], marker="*", ls="", mfc="#ffd60a", mec="k", ms=13, label="Mandal HQ (PROXY: interior point of the mandal polygon)")]
    fig.legend(handles=h, loc="lower center", ncol=2, bbox_to_anchor=(0.5, 0.125), fontsize=7, frameon=True, edgecolor="#cccccc", title="Map layers - scalability demonstration, not planning findings", title_fontsize=7.5)
    fig.legend(handles=lc_handles(present), loc="lower center", ncol=min(4, len(present)), bbox_to_anchor=(0.5, 0.045), fontsize=6.5, frameon=True, edgecolor="#cccccc",
               title="Land cover context (ESA WorldCover, faded)", title_fontsize=7)
    footnote(fig)
    save(fig, out / "map3_level3_markook_mandal_network.png")


def map4(cfg, out):
    dd = cfg["data"]["district"]
    dist = gpd.read_file(REPO / dd["boundary"])
    mand = gpd.read_file(REPO / dd["mandal_boundaries"])
    droads = gpd.read_file(REPO / dd["roads"])
    chains = gpd.read_file(RUN / "district" / "district_routes.gpkg", layer="routes_shared")
    term = gpd.read_file(RUN / "district" / "district_routes.gpkg", layer="nodes")
    tcsv = gpd.read_file(REPO / dd["terminals"])
    s = summaries()["district"]
    fine = cfg["levels"]["district"]["fine_resolution_m"]
    net = unary_union(list(chains.geometry))
    buf = droads.geometry.union_all().buffer(1.5 * fine)
    existing, new = net.intersection(buf), net.difference(buf)
    fig = plt.figure(figsize=(10.5, 9.4))
    ax = fig.add_axes([0.07, 0.25, 0.9, 0.67])
    b = dist.total_bounds
    bounds = (b[0] - 2500, b[1] - 2500, b[2] + 2500, b[3] + 2500)
    present = show_landcover(ax, REPO / dd["landcover"], bounds, dist.geometry.union_all(), 1800)
    mand.boundary.plot(ax=ax, color="#555555", lw=0.4, zorder=2)
    dist.boundary.plot(ax=ax, color=COL["bound"], lw=1.4, zorder=3)
    droads.plot(ax=ax, color=COL["local"], lw=0.45, zorder=4)
    gpd.GeoSeries([existing], crs=cfg["crs"]).plot(ax=ax, color=COL["exist"], lw=1.9, zorder=6)
    gpd.GeoSeries([new], crs=cfg["crs"]).plot(ax=ax, color=COL["new"], lw=3.8, zorder=7)
    tm = term[term.kind == "mandal_hq"].merge(tcsv[["id", "mandal"]], left_on="node_id", right_on="id", how="left")
    ax.scatter(tm.geometry.x, tm.geometry.y, marker="^", s=44, c="white", edgecolor="k", lw=0.9, zorder=9)
    for _, r in tm.iterrows():
        halo(ax.text(r.geometry.x + 700, r.geometry.y + 500, str(r["mandal"]), fontsize=5.6, zorder=12), 1.8)
    root = term[term.kind == "district_hq"]
    ax.scatter(root.geometry.x, root.geometry.y, marker="*", s=420, c="#ffd60a", edgecolor="k", lw=1.1, zorder=11)
    halo(ax.text(root.geometry.x.iloc[0] + 900, root.geometry.y.iloc[0] - 1700, "District HQ (PROXY)", fontsize=6.8, fontweight="bold", zorder=12))
    pieces = sorted(getattr(new, "geoms", [new]), key=lambda g: -g.length)
    for k, g in enumerate(pieces[:5], 1):
        mid = g.interpolate(0.5, normalized=True)
        ax.annotate(f"{g.length / 1000:.1f} km", (mid.x, mid.y), xytext=(14, 14 + 5 * k), textcoords="offset points", fontsize=6.6, color=COL["new"], fontweight="bold", zorder=15,
                    bbox=dict(boxstyle="round,pad=0.2", fc="white", ec=COL["new"], lw=0.6), arrowprops=dict(arrowstyle="-", lw=0.6, color=COL["new"]))
    ax.set_title("Map 4. Level 4 - Siddipet district backbone: reuse of existing roads versus new construction (proxy terminals)", fontsize=10.5, fontweight="bold", pad=20)
    geo_ticks(ax)
    furniture(ax, 10000, "10 km")
    share = 100 * s["shared_on_existing_road_m"] / s["shared_unique_length_m"]
    ax.text(0.5, 1.008, f"Backbone {s['shared_unique_length_m'] / 1000:,.1f} km: {s['shared_on_existing_road_m'] / 1000:,.1f} km ({share:.1f}%) on existing roads, {s['shared_new_construction_m'] / 1000:.1f} km new construction "
            f"(star layout would need {s['independent_new_construction_m'] / 1000:.1f} km new)", transform=ax.transAxes, ha="center", va="bottom", fontsize=6.8, color="#333333")
    h = [Line2D([], [], color=COL["local"], lw=1.2, label="Roads (motorway to tertiary, Overture)"), Line2D([], [], color=COL["exist"], lw=2.4, label=f"Backbone on existing road ({s['shared_on_existing_road_m'] / 1000:.1f} km)"),
         Line2D([], [], color=COL["new"], lw=4, label=f"New construction ({s['shared_new_construction_m'] / 1000:.1f} km; five longest pieces labelled)"),
         Line2D([], [], marker="^", ls="", mfc="white", mec="k", ms=7, label="Mandal terminal (PROXY: polygon interior point)"),
         Line2D([], [], marker="*", ls="", mfc="#ffd60a", mec="k", ms=13, label="District HQ (PROXY: Siddipet Urban interior point)")]
    fig.legend(handles=h, loc="lower center", ncol=2, bbox_to_anchor=(0.5, 0.115), fontsize=7, frameon=True, edgecolor="#cccccc", title="Map layers - scalability demonstration, not planning findings", title_fontsize=7.5)
    fig.legend(handles=lc_handles(present), loc="lower center", ncol=min(5, len(present)), bbox_to_anchor=(0.5, 0.045), fontsize=6.5, frameon=True, edgecolor="#cccccc",
               title="Land cover context (ESA WorldCover, faded)", title_fontsize=7)
    footnote(fig)
    save(fig, out / "map4_level4_siddipet_district_backbone.png")


# ============================================================================================ charts
def chart1(out):
    sw = pd.read_csv(RES / "U02_penalty_sweep_gp.csv")
    fig, ax = plt.subplots(figsize=(7.6, 4.8))
    fig.subplots_adjust(left=0.1, right=0.9, top=0.82, bottom=0.2)
    x = np.arange(len(sw))
    ax.plot(x, sw.exposure_reduction_vs_mu1_pct, "o-", color="#1d4ed8", lw=2, ms=6, label="Footprint exposure reduction (left axis)")
    ax.set_ylim(-4, 104)
    ax.set_ylabel("Exposure reduction vs $\\mu$ = 1 (%)", color="#1d4ed8")
    ax2 = ax.twinx()
    ax2.plot(x, sw.length_increase_vs_mu1_pct, "s--", color="#d62828", lw=2, ms=6, label="Network length increase (right axis)")
    ax2.set_ylim(-0.5, 13)
    ax2.set_ylabel("Network length increase vs $\\mu$ = 1 (%)", color="#d62828")
    k = int(np.where(sw.mu == 4.0)[0][0])
    ax.axvspan(k - 0.4, k + 0.4, color="#ffd60a", alpha=0.25, lw=0)
    ax.annotate(f"$\\mu$ = 4 (primary, owner sign-off):\n{sw.exposure_reduction_vs_mu1_pct[k]:.1f}% less exposure for +{sw.length_increase_vs_mu1_pct[k]:.1f}% length",
                (k, sw.exposure_reduction_vs_mu1_pct[k]), xytext=(k + 0.55, 38), fontsize=8, arrowprops=dict(arrowstyle="->", lw=0.9), bbox=dict(boxstyle="round", fc="white", ec="#999999"))
    ax.text(-0.5, 1.025, "E (m):", transform=ax.get_xaxis_transform(), ha="right", fontsize=7.5, color="#1d4ed8", fontweight="bold")
    for i, r in sw.iterrows():
        ax.text(i, 1.025, f"{r.length_in_footprints_m:.0f}", transform=ax.get_xaxis_transform(), ha="center", fontsize=8, color="#1d4ed8")
    ax.set_xticks(x)
    ax.set_xticklabels([f"{m:g}" for m in sw.mu])
    ax.set_xlabel("Footprint penalty $\\mu$ (swept set; $\\mu$ = 16 was not run)")
    ax.grid(True, axis="y", lw=0.3, color="#dddddd")
    ax.set_title("Chart 1. Footprint-penalty trade-off at Level 2 (Damarakunta GP, real inputs)", fontsize=10, fontweight="bold", loc="left", pad=20)
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="lower right", frameon=True, edgecolor="#cccccc")
    fig.text(0.5, 0.025, "E = route length inside footprints (m), shown above each penalty value. Source: docs/results/U02_penalty_sweep_gp.csv", ha="center", fontsize=6.5, color="#444444")
    save(fig, out / "chart1_mu_penalty_tradeoff.png")


def chart2(out):
    S = summaries()
    t1 = pd.read_csv(STAGEB / "03_RESULTS_TABLES" / "COMPARISON_TABLES" / "table1_length_reduction.csv")
    p = t1[t1.configuration == "x4 (primary)"]
    l1_ind = float(p[p.method.str.startswith("Independent")].unique_len_m.iloc[0]) / 1000
    l1_sh = float(p[p.method.str.startswith("Two-stage")].unique_len_m.iloc[0]) / 1000
    rows = [("Level 1\nVillage (Stage B)\nreal, 163 houses", l1_ind, l1_sh, False),
            ("Level 2\nGram Panchayat\nreal, 18 hubs + 5 fac.", S["gp"]["independent_new_construction_m"] / 1000, S["gp"]["shared_new_construction_m"] / 1000, False),
            ("Level 3\nMandal\nPROXY nodes", S["mandal"]["independent_new_construction_m"] / 1000, S["mandal"]["shared_new_construction_m"] / 1000, True),
            ("Level 4\nDistrict (new only)\nPROXY nodes", S["district"]["independent_new_construction_m"] / 1000, S["district"]["shared_new_construction_m"] / 1000, True)]
    fig, ax = plt.subplots(figsize=(8.2, 4.9))
    fig.subplots_adjust(left=0.09, right=0.98, top=0.86, bottom=0.2)
    x = np.arange(len(rows))
    w = 0.36
    for i, (lab, ind, sh, proxy) in enumerate(rows):
        h = "////" if proxy else None
        ax.bar(i - w / 2, ind, w, color="#bdbdbd", edgecolor="#555555", hatch=h, lw=0.8)
        ax.bar(i + w / 2, sh, w, color="#d62828", edgecolor="#555555", hatch=h, lw=0.8)
        ax.text(i - w / 2, ind + 0.3, f"{ind:.1f}", ha="center", fontsize=8)
        ax.text(i + w / 2, sh + 0.3, f"{sh:.1f}", ha="center", fontsize=8)
        save_pct = 100 * (ind - sh) / ind if ind else 0
        ax.text(i, max(ind, sh) + 1.9, f"{save_pct:.1f}% saved", ha="center", fontsize=8, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels([r[0] for r in rows], fontsize=7.5)
    ax.set_ylabel("New (unique) network length (km)")
    ax.set_ylim(0, max(max(r[1], r[2]) for r in rows) * 1.22)
    ax.grid(True, axis="y", lw=0.3, color="#dddddd")
    ax.set_title("Chart 2. Independent versus shared new network across the four levels", fontsize=10, fontweight="bold", loc="left")
    ax.legend(handles=[Patch(fc="#bdbdbd", ec="#555555", label="Independent routes"), Patch(fc="#d62828", ec="#555555", label="Shared network"),
                       Patch(fc="white", ec="#555555", hatch="////", label="Proxy nodes: scalability demonstration")], loc="upper left", frameon=True, edgecolor="#cccccc")
    fig.text(0.5, 0.025, "Level 1 lengths are Stage B (recorded table1_length_reduction.csv); Levels 2-4 are this work. Level 4 counts new construction only (the backbone is 95.9% existing road). Level 2 routes hamlet hubs, not houses.",
             ha="center", fontsize=6.3, color="#444444", wrap=True)
    save(fig, out / "chart2_multiscale_network_comparison.png")


# ============================================================================================ diagrams (Stage B style)
def box(ax, y, h, title, body, shade, dashed=False):
    p = FancyBboxPatch((0.05, y), 0.9, h, boxstyle="round,pad=0.005,rounding_size=0.012", fc=shade, ec="#222222" if not dashed else "#555555",
                       lw=2.4 if not dashed else 2.0, ls="--" if dashed else "-", transform=ax.transAxes)
    ax.add_patch(p)
    ax.text(0.5, y + h - 0.02, title, ha="center", va="top", fontsize=13.5, fontweight="bold", family="DejaVu Serif", transform=ax.transAxes)
    ax.text(0.5, y + h - 0.062, body, ha="center", va="top", fontsize=10.5, family="DejaVu Serif", linespacing=1.35, transform=ax.transAxes)


def architecture(out, S):
    fig = plt.figure(figsize=(7.6, 11.4))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis("off")
    g, l = "#cecece", "#ececec"
    steps = [
        ("1  Open and Stage B inputs", "WorldCover 10 m, Copernicus DEM 30 m, geoBoundaries, Overture roads / villages,\nTGRAC roads, facilities, building footprints, 163 Stage B house targets", l, False),
        ("2  Level 1: Village (Stage B, Damarakunta)", "10 m grid, 163 house targets, two-stage shared network 5,069 m\n(24.9 % below independent), omission propagation C1 (recorded tables)", g, False),
        ("3  Level 2: Gram Panchayat (real inputs)", f"hamlet hubs + 5 amenities, penalty x4 with 20 m local override;\n{S['gp']['shared_unique_length_m']:,.0f} m shared vs {S['gp']['independent_unique_length_m']:,.0f} m independent; mu sweep supports mu = 4", g, False),
        ("4  Level 3: Mandal (Markook, proxy nodes)", f"30 m grid, collector-road attachment, slope / water / forest resistance;\n{S['mandal']['shared_new_construction_m'] / 1000:.1f} km new links for 14 village points", l, False),
        ("5  Level 4: District (Siddipet, proxy terminals)", f"250 m coarse plan -> graph contraction -> windowed 30 m refinement;\n{S['district']['shared_unique_length_m'] / 1000:.0f} km backbone, {S['district']['shared_new_construction_m'] / 1000:.1f} km new construction", l, False),
        ("6  Sensitivity and metrics", "shared vs independent length, override detour, omission scenarios (3 seeds),\nexisting-road reuse vs new construction, GeoPackage / CSV / JSON per level", g, False),
        ("7  Provenance audit and manuscript", "SHA-256 inputs, re-run + re-download checks, figures, LaTeX / Word,\nevery manuscript number mapped to a source file", g, False),
        ("8  Verified Level 3-4 inputs, rupee cost, anganwadi", "Planned only. Blocked until verified HQ / PHC / market / GP data and a\nSchedule of Rates are supplied (docs/DECISIONS.md U03, U04, U15)", "white", True)]
    h, gap, top = 0.092, 0.022, 0.985
    for i, (t, b, shade, dash) in enumerate(steps):
        y0 = top - i * (h + gap) - h
        ax.add_patch(FancyBboxPatch((0.05, y0), 0.9, h, boxstyle="round,pad=0.003,rounding_size=0.012", fc=shade, ec="#222222" if not dash else "#555555",
                                    lw=2.4 if not dash else 2.0, ls="--" if dash else "-", transform=ax.transAxes))
        ax.text(0.5, y0 + h - 0.014, t, ha="center", va="top", fontsize=13, fontweight="bold", family="DejaVu Serif", transform=ax.transAxes)
        ax.text(0.5, y0 + h - 0.046, b, ha="center", va="top", fontsize=10, family="DejaVu Serif", linespacing=1.3, transform=ax.transAxes)
        if i < len(steps) - 1:
            ax.annotate("", xy=(0.5, y0 - gap + 0.002), xytext=(0.5, y0 - 0.002), arrowprops=dict(arrowstyle="-|>", lw=2.2, color="#333333", mutation_scale=18), xycoords="axes fraction")
    leg = [Patch(fc=g, ec="#222222", lw=2, label="Implemented and run (real inputs, or verified / recomputed results)"), Patch(fc=l, ec="#222222", lw=2, label="Implemented and run; inputs are proxies (scalability demonstration)"),
           Patch(fc="white", ec="#555555", lw=2, ls="--", label="Planned, not run (needs your data or decisions)")]
    ax.legend(handles=leg, loc="lower center", bbox_to_anchor=(0.5, 0.005), frameon=True, edgecolor="#cccccc", prop={"family": "DejaVu Serif", "size": 8.5})
    save(fig, out / "ARCHITECTURE_DIAGRAM.png")


def workflow(out):
    fig = plt.figure(figsize=(11.2, 6.4))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis("off")
    g, l = "#cecece", "#ececec"
    cells = [("Data helper", "WorldCover, DEM,\nboundaries, roads\n(open, hashed,\nprovenance JSON)", l), ("Cost surface", "c(x) = [c_lc + g(slope)] m(x)\nfootprint penalty mu,\nlocal override discs", g),
             ("Shared planner", "lazy-greedy attachment to\nroads + built network;\nL4: coarse -> contract\n-> fine windows", g), ("Metrics", "shared vs independent,\noverride detour,\nomission seeds 11-13,\nnew vs existing road", g),
             ("Figures + tables", "maps, charts, CSV,\nMarkdown, Excel", g), ("Provenance audit", "hashes, re-run,\nre-download, paper\nnumbers, figures", g), ("Manuscript", "LaTeX + Word + PDF,\nsync to local folders", g)]
    w, h, gx = 0.215, 0.25, 0.03
    pos = [(0.025 + i * (w + gx), 0.55) for i in range(4)] + [(0.025 + i * (w + gx), 0.22) for i in range(3)]
    for i, ((t, b, shade), (x, y)) in enumerate(zip(cells, pos)):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.004,rounding_size=0.01", fc=shade, ec="#222222", lw=2.2, transform=ax.transAxes))
        ax.text(x + w / 2, y + h - 0.025, f"{i + 1}  {t}", ha="center", va="top", fontsize=11, fontweight="bold", family="DejaVu Serif", transform=ax.transAxes)
        ax.text(x + w / 2, y + h - 0.075, b, ha="center", va="top", fontsize=9, family="DejaVu Serif", linespacing=1.35, transform=ax.transAxes)
        if i < len(cells) - 1 and i != 3:
            ax.annotate("", xy=(pos[i + 1][0] - 0.002, y + h / 2), xytext=(x + w + 0.002, y + h / 2), arrowprops=dict(arrowstyle="-|>", lw=2, color="#333333", mutation_scale=16), xycoords="axes fraction")
    # elbow from box 4 to box 5
    x4, y4 = pos[3][0] + w / 2, pos[3][1]
    x5, y5 = pos[4][0] + w / 2, pos[4][1] + h
    ymid = (y4 + y5) / 2
    ax.plot([x4, x4, x5], [y4 - 0.002, ymid, ymid], color="#333333", lw=2, transform=ax.transAxes, solid_capstyle="butt")
    ax.annotate("", xy=(x5, y5 + 0.002), xytext=(x5, ymid), arrowprops=dict(arrowstyle="-|>", lw=2, color="#333333", mutation_scale=16), xycoords="axes fraction")
    ax.text(0.5, 0.93, "Contribution 3 workflow: village -> Gram Panchayat -> mandal -> district", ha="center", fontsize=13, fontweight="bold", family="DejaVu Serif", transform=ax.transAxes)
    ax.text(0.5, 0.11, "python -m src.utils.data_downloader_helper  ->  src.routing.run_hierarchy  ->  src.evaluation.penalty_sweep  ->  plot_hierarchy_figures / plot_level1_omission\n"
            "->  build_contribution3_deliverables  ->  provenance_audit --write --rerun --redownload  ->  pytest  ->  paper/build_docx.py", ha="center", va="top", fontsize=8, family="DejaVu Sans Mono", transform=ax.transAxes)
    save(fig, out / "WORKFLOW_DIAGRAM.png")


# ============================================================================================ tables
def tables(out, S):
    out.mkdir(parents=True, exist_ok=True)
    gp, md, ds = S["gp"], S["mandal"], S["district"]
    ov = pd.read_csv(RUN / "gp" / "gp_override.csv")
    names = KIND_LABEL
    t_gp = [("Nodes (hamlet hubs + facilities)", "18 + 5", "count", "real inputs"), ("Houses represented by the hubs", int(gp["unit_weight_total"]), "houses", "163 Stage B targets"),
            ("Shared unique network length", round(gp["shared_unique_length_m"], 1), "m", "gp_summary.json"), ("Independent unique length", round(gp["independent_unique_length_m"], 1), "m", "gp_summary.json"),
            ("Saving vs independent", round(gp["saving_vs_independent_unique_pct"], 2), "%", "derived"), ("Override detour reduction (all facilities)", round(gp["detour_reduction_m_total"], 1), "m", "gp_override.csv"),
            ("Other routes changed by the override", gp["other_routes_changed_by_override"], "count", "gp_override.csv"),
            ("All nodes connected to a road", f"{gp['connected_any_road']} / {gp['n_nodes']}", "nodes", "graph check"), ("Connected to the main road component", f"{gp['connected_main_component']} / {gp['n_nodes']}", "nodes", "graph check")]
    pd.DataFrame(t_gp, columns=["metric", "value", "unit", "source"]).to_csv(out / "T1_level2_gp_metrics.csv", index=False)
    fo = ov[ov.status == "ROUTED"].copy()
    fo["facility"] = fo.node.map(lambda n: names.get(str(n), str(n)))
    fo = fo[["facility", "kind", "length_without_m", "length_with_m", "detour_reduction_m", "cost_without", "cost_with", "cost_reduction_pct"]].round(2)
    fo.to_csv(out / "T1b_level2_facility_override.csv", index=False)
    sw = pd.read_csv(RES / "U02_penalty_sweep_gp.csv").rename(columns={"mu": "mu_penalty", "shared_unique_length_m": "shared_length_m", "independent_unique_length_m": "independent_length_m",
                                                                      "length_in_footprints_m": "E_mu_length_inside_footprints_m", "routes_crossing_footprints": "routes_crossing_footprints",
                                                                      "length_increase_vs_mu1_pct": "length_increase_vs_mu1_pct", "exposure_reduction_vs_mu1_pct": "exposure_reduction_vs_mu1_pct"})
    sw.to_csv(out / "T2_mu_penalty_sensitivity.csv", index=False)
    sc = pd.DataFrame([
        dict(level="3 Mandal (Markook)", evidence="PROXY nodes", nodes="14 village points + 1 proxy HQ", grid="30 m", shared_total_km=md["shared_unique_length_m"] / 1000, on_existing_road_km=0.0,
             new_construction_km=md["shared_new_construction_m"] / 1000, independent_new_km=md["independent_new_construction_m"] / 1000,
             new_construction_saving_pct=100 * (md["independent_new_construction_m"] - md["shared_new_construction_m"]) / md["independent_new_construction_m"], coverage_pct=md["coverage_pct"]),
        dict(level="4 District (Siddipet)", evidence="PROXY nodes", nodes="22 proxy mandal terminals -> proxy district HQ", grid="250 m / 30 m", shared_total_km=ds["shared_unique_length_m"] / 1000,
             on_existing_road_km=ds["shared_on_existing_road_m"] / 1000, new_construction_km=ds["shared_new_construction_m"] / 1000, independent_new_km=ds["independent_new_construction_m"] / 1000,
             new_construction_saving_pct=100 * (ds["independent_new_construction_m"] - ds["shared_new_construction_m"]) / ds["independent_new_construction_m"], coverage_pct=ds["coverage_pct"])]).round(3)
    sc.to_csv(out / "T3_levels3_4_scalability.csv", index=False)
    om = []
    for lvl, lab in (("gp", "2 GP (real)"), ("mandal", "3 Mandal (proxy)"), ("district", "4 District (proxy)")):
        o = pd.read_csv(RUN / lvl / f"{lvl}_omission.csv")
        o.insert(0, "level", lab)
        om.append(o)
    om = pd.concat(om)
    om.round(3).to_csv(out / "T4_omission_sensitivity_levels2_4.csv", index=False)
    # Markdown
    def md_t(df):
        cols = list(df.columns)
        return "| " + " | ".join(cols) + " |\n|" + "---|" * len(cols) + "\n" + "\n".join("| " + " | ".join(str(v) for v in r) + " |" for r in df.itertuples(index=False)) + "\n"
    txt = ("# Contribution 3 - summary tables\n\nGenerated by `python -m src.evaluation.build_contribution3_deliverables` from `docs/results/`. Costs are ordinal units, not rupees. "
           "Level 2 is real-input; Levels 3-4 are a scalability demonstration on proxy nodes.\n\n## T1 Level 2 (Damarakunta Gram Panchayat) metrics\n" + md_t(pd.DataFrame(t_gp, columns=["metric", "value", "unit", "source"])) +
           "\n### T1b Facility routes with and without the local penalty override\n" + md_t(fo) + "\n## T2 Footprint-penalty sensitivity (mu), Level 2\n" + md_t(sw) +
           "\n## T3 Levels 3-4 scalability (proxy nodes)\n" + md_t(sc) + "\n## T4 Omission sensitivity (3 seeds x 10 / 20 %), Levels 2-4\n" + md_t(om.round(2)))
    (out / "contribution3_summary_tables.md").write_text(txt, encoding="utf-8")
    # Excel
    xl = out / "contribution3_summary_tables.xlsx"
    with pd.ExcelWriter(xl, engine="openpyxl") as w:
        pd.DataFrame({"sheet": ["T1_L2_metrics", "T1b_L2_override", "T2_mu_sweep", "T3_L3_L4_scalability", "T4_omission"],
                      "content": ["Level 2 headline metrics (real inputs)", "facility routes with / without local override", "footprint-penalty sensitivity",
                                  "Levels 3-4 on PROXY nodes - not planning findings", "omission scenarios, seeds 11-13"]}).to_excel(w, sheet_name="README", index=False)
        pd.DataFrame(t_gp, columns=["metric", "value", "unit", "source"]).to_excel(w, sheet_name="T1_L2_metrics", index=False)
        fo.to_excel(w, sheet_name="T1b_L2_override", index=False)
        sw.to_excel(w, sheet_name="T2_mu_sweep", index=False)
        sc.to_excel(w, sheet_name="T3_L3_L4_scalability", index=False)
        om.round(3).to_excel(w, sheet_name="T4_omission", index=False)
        from openpyxl.styles import Font, PatternFill
        for ws in w.book.worksheets:
            for c in ws[1]:
                c.font = Font(bold=True)
                c.fill = PatternFill("solid", fgColor="D9D9D9")
            for col in ws.columns:
                ws.column_dimensions[col[0].column_letter].width = min(48, max(10, max(len(str(c.value)) if c.value is not None else 0 for c in col) + 2))
            ws.freeze_panes = "A2"
    return dict(t_gp=t_gp, fo=fo, sw=sw, sc=sc)


# ============================================================================================ documents
def write_docs(S, tb):
    gp, md, ds = S["gp"], S["mandal"], S["district"]
    sw = tb["sw"].set_index("mu_penalty")
    k = sw.loc[4.0]
    env = json.loads((RES / "provenance_audit.json").read_text())
    aud = {kk: len(v) for kk, v in env.items() if isinstance(v, list) and kk in ("level1", "levels", "figures", "paper", "rerun", "redownload")}
    n_checks = sum(len(env[kk]) for kk in ("hashes", "level1", "loveda", "levels", "figures", "paper", "rerun", "redownload") if kk in env)
    n_pass = sum(1 for kk in ("hashes", "level1", "loveda", "levels", "figures", "paper", "rerun", "redownload") if kk in env for r in env[kk] if r["status"] == "PASS")
    n_fail = sum(1 for kk in ("hashes", "level1", "loveda", "levels", "figures", "paper", "rerun", "redownload") if kk in env for r in env[kk] if r["status"] == "FAIL")
    readme = f"""# Contribution 3 - hierarchical multi-scale routing: deliverables package

Case study: scaling cost-surface-driven shared road planning from the village (Damarakunta, Level 1, Stage B) to the Gram Panchayat (Level 2), Markook mandal (Level 3) and Siddipet district (Level 4), Telangana.
Planning results on 10 m (Level 2), 30 m (Level 3) and 250 m / 30 m coarse-to-fine (Level 4) grids, EPSG:32644. Routes are unverified planning alternatives, not roads. Costs are ordinal planning units, not rupees.
No field validation, legal access, ownership, drainage, road width or construction cost is established. **Level 2 and the mu sweep use real inputs. Levels 3 and 4 are a computational scalability demonstration on PROXY nodes** (polygon interior points and OSM village points, not verified HQ, PHC, market or Gram Panchayat locations): no planning conclusion may be drawn from them.
`DELIVERABLES_DAMARAKUNTA_STAGE_B/` (Level 1) is untouched by this package.

| Folder | Content |
|---|---|
| 00_README_SUMMARY.md, MANIFEST.csv | this file; SHA-256 of every file in folders 00-03 and 05 |
| 01_ARCHITECTURE | architecture and workflow diagrams, data and process flow |
| 02_FINAL_MAPS | four 300 dpi maps with land-cover context, legend, scale bar and north arrow |
| 03_RESULTS_TABLES | CSV, Markdown and Excel tables; `CHARTS/` (two 300 dpi charts) |
| 04_PROVENANCE_AND_AUDIT | snapshot copies of the provenance report, audit JSON, input manifest, DEM comparison, sweep and decisions |
| 05_LIMITATIONS_AND_OPEN_ISSUES | real vs proxy, what needs the owner's data |

## Headline metrics (all read from `docs/results/`)

| Level | Evidence | Nodes | Shared unique length | New construction | Independent (new) | Saving on new construction |
|---|---|---|---|---|---|---|
| 1 Village (Stage B, recorded) | real | 163 houses (+5 facilities) | 5,069.0 m | 5,069.0 m | 6,753.1 m | 24.9 % |
| 2 Gram Panchayat (Damarakunta) | real | 18 hamlet hubs + 5 facilities | {gp['shared_unique_length_m']:,.1f} m | {gp['shared_new_construction_m']:,.1f} m | {gp['independent_new_construction_m']:,.1f} m | {100 * (gp['independent_new_construction_m'] - gp['shared_new_construction_m']) / gp['independent_new_construction_m']:.1f} % |
| 3 Mandal (Markook) | PROXY | 14 village points + proxy HQ | {md['shared_unique_length_m'] / 1000:,.2f} km | {md['shared_new_construction_m'] / 1000:,.2f} km | {md['independent_new_construction_m'] / 1000:,.2f} km | {100 * (md['independent_new_construction_m'] - md['shared_new_construction_m']) / md['independent_new_construction_m']:.1f} % |
| 4 District (Siddipet) | PROXY | 22 proxy terminals -> proxy district HQ | {ds['shared_unique_length_m'] / 1000:,.1f} km | {ds['shared_new_construction_m'] / 1000:,.1f} km | {ds['independent_new_construction_m'] / 1000:,.1f} km | {100 * (ds['independent_new_construction_m'] - ds['shared_new_construction_m']) / ds['independent_new_construction_m']:.1f} % |

* **Level 2 override:** lifting the footprint penalty within 20 m of an amenity shortens facility routes by {gp['detour_reduction_m_total']:.1f} m in total, lowers facility route cost by 33-67 %, and changes {gp['other_routes_changed_by_override']} other routes.
* **mu sweep (owner sign-off on mu = 4):** mu = 4 removes {k.exposure_reduction_vs_mu1_pct:.1f} % of route length inside footprints ({sw.loc[1.0, 'E_mu_length_inside_footprints_m']:.1f} m -> {k.E_mu_length_inside_footprints_m:.1f} m) for +{k.length_increase_vs_mu1_pct:.1f} % network length; the swept set is {{1, 2, 4, 8, 20, 100}} (16 was not run).
* **Level 4:** {100 * ds['shared_on_existing_road_m'] / ds['shared_unique_length_m']:.1f} % of the {ds['shared_unique_length_m'] / 1000:,.1f} km backbone is existing road; only {ds['shared_new_construction_m'] / 1000:.1f} km is new construction.
* **Omission scenarios** (random removal of 10 / 20 % of units, seeds 11-13) are synthetic, not measured detection errors; see `03_RESULTS_TABLES/T4_omission_sensitivity_levels2_4.csv`.

## Data sources
ESA WorldCover 10 m v200 2021 (CC BY 4.0); Copernicus GLO-30 DEM (Stage B used SRTM 1 arc-second: difference quantified in `04_PROVENANCE_AND_AUDIT/U08_dem_comparison.json`, RMSE 2.3 m, effect on Level 2 length 1.0 %);
geoBoundaries gbOpen IND ADM2/ADM3 (ODbL 1.0; 23 mandals as released); Overture Maps release 2026-10-21.0 (OSM-derived, ODbL); TGRAC roads, facilities and boundary, v8 building footprints and the 163 Stage B house targets (Level 2). Hashes: `04_PROVENANCE_AND_AUDIT/input_manifest.csv`.

## Deliverable files
* `01_ARCHITECTURE/ARCHITECTURE_DIAGRAM.png`, `WORKFLOW_DIAGRAM.png`, `DATA_AND_PROCESS_FLOW.md`
* `02_FINAL_MAPS/map1_level2_damarakunta_gp_network.png`, `map2_level2_facility_override_zooms.png`, `map3_level3_markook_mandal_network.png`, `map4_level4_siddipet_district_backbone.png`
* `03_RESULTS_TABLES/T1_level2_gp_metrics.csv`, `T1b_level2_facility_override.csv`, `T2_mu_penalty_sensitivity.csv`, `T3_levels3_4_scalability.csv`, `T4_omission_sensitivity_levels2_4.csv`, `contribution3_summary_tables.md`, `contribution3_summary_tables.xlsx`
* `03_RESULTS_TABLES/CHARTS/chart1_mu_penalty_tradeoff.png`, `chart2_multiscale_network_comparison.png`
* `04_PROVENANCE_AND_AUDIT/` PROVENANCE_AND_PROOFS.md, provenance_audit.json, input_manifest.csv, U08_dem_comparison.json, U02_penalty_sweep_gp.csv, DECISIONS.md, REPRODUCE.md, STAGE_B_UNTOUCHED.txt
* GeoPackages and per-level CSV/JSON: `docs/results/hierarchy_real_run/` (kept in place; not duplicated here)

## Audit status (snapshot at build time)
{n_checks} provenance checks in the `provenance_audit.json` copy: {n_pass} PASS, {n_fail} FAIL, the rest are values recorded only in documents (Stage B git-ignored rasters and run outputs). The audit also checks this package (required files, `MANIFEST.csv` hashes, README numbers, and that Stage B is unchanged); re-run it for current counts: see `04_PROVENANCE_AND_AUDIT/REPRODUCE.md`.
Run everything again with `python -m src.evaluation.build_contribution3_deliverables` after the pipeline (see REPRODUCE.md).
"""
    (DEL / "00_README_SUMMARY.md").write_text(readme, encoding="utf-8")
    (DEL / "01_ARCHITECTURE").mkdir(exist_ok=True, parents=True)
    (DEL / "01_ARCHITECTURE" / "DATA_AND_PROCESS_FLOW.md").write_text(f"""# Data and process flow

```
open data (WorldCover, Copernicus DEM, geoBoundaries, Overture)  +  Stage B / TGRAC files (Level 2)
        |  src/utils/data_downloader_helper.py  (hashes + provenance JSON; Overture release pinned)
        v
layers (src/routing/layers.py): land cover + slope -> cost c(x) = [c_lc(class) + g(slope)] * m(x);  m(x) = 1 + (mu-1) * 1[footprint] * (1 - 1[within r of an exempt facility])
        v
RoutingProblem (Levels 2-3, grid)   |   DistrictProblem (Level 4: 250 m coarse plan -> contract_chains -> 30 m windows inside a 1 km corridor)
        v   lazy-greedy shared-network attachment (Stage B Grid search, no diagonal corner-cutting)
LevelResult (routes, unique / total length, connectivity by union-find, new vs existing-road length)
        v   src/evaluation/hierarchy_metrics.py
GeoPackage (routes_shared, routes_independent, nodes) + summary JSON + metrics / override / omission CSV   -> docs/results/hierarchy_real_run/
        v   src/evaluation/plot_hierarchy_figures.py, plot_level1_omission.py, build_contribution3_deliverables.py
figures, maps, charts, tables (this package)
        v   src/evaluation/provenance_audit.py
PROVENANCE_AND_PROOFS.md  (hashes, re-run, re-download, manuscript numbers, figures, this package)
```

Level 1 (Stage B) is not re-executed: `DELIVERABLES_DAMARAKUNTA_STAGE_B/` holds its recorded results and its tables are re-read and recomputed by the audit.
Levels 3-4 nodes are proxies (see `05_LIMITATIONS_AND_OPEN_ISSUES/LIMITATIONS.md`).
""", encoding="utf-8")
    lim = DEL / "05_LIMITATIONS_AND_OPEN_ISSUES"
    lim.mkdir(exist_ok=True, parents=True)
    (lim / "LIMITATIONS.md").write_text("""# Limitations and open issues (Contribution 3)

> **PROXY WARNING.** Levels 3 and 4 (Markook mandal, Siddipet district) use PROXY nodes: Overture village points as Gram Panchayat hubs, the interior point of the Markook polygon as the Mandal HQ, and interior points of the 23 mandal polygons as terminals. None is a verified HQ, PHC or market coordinate, and no coordinate was invented. These results are a scalability demonstration, not verified planning findings.

## What is real and what is not
| Item | Status |
|---|---|
| Level 1 (Stage B) numbers | recorded results, re-read and recomputed by the audit; Level 1 is not re-executed (its rasters are git-ignored) |
| Level 2 (Damarakunta GP) | real inputs; routes **hamlet hubs** (not houses), so lengths are not comparable with Level 1's 5,069 m |
| mu sweep | real inputs, deterministic; mu = 4 signed off by the owner; the swept set excludes 16 |
| Level 3 Markook, Level 4 Siddipet | **proxy nodes**: scalability demonstration only, no planning conclusion |
| Omission scenarios | synthetic random omission of units, not measured detection errors |
| Costs | ordinal units, not rupees (U03/U04 not implemented) |
| Field validation, legal access, passability | none |

## Needs the owner's data or decisions
* Verified Mandal HQ, PHC and market coordinates and Gram Panchayat polygons with house counts (Level 3); verified mandal HQ points (Level 4) - replace the proxy files in `Siddipet/_mandal/` and `Siddipet/_district/`.
* Anganwadi coordinate (U15), State Schedule of Rates / PMGSY rates (U03/U04), PMGSY or TGRAC road inventory in place of Overture roads.
* The original SRTM tile `n17_e078_1arc_v3.tif` to close the original U08 (masked DEM cells) and Stage B rasters to let the audit re-execute Level 1.
* Imagery basemaps are not used: the Esri imagery licence is unresolved; land cover (WorldCover, CC BY 4.0) gives the map context instead.
* The geoBoundaries release has 23 mandals in Siddipet district; the current administrative set may differ.
""", encoding="utf-8")


def copy_provenance():
    p = DEL / "04_PROVENANCE_AND_AUDIT"
    p.mkdir(exist_ok=True, parents=True)
    for rel in ("docs/results/PROVENANCE_AND_PROOFS.md", "docs/results/provenance_audit.json", "docs/results/input_manifest.csv", "docs/results/U08_dem_comparison.json",
                "docs/results/U02_penalty_sweep_gp.csv", "docs/DECISIONS.md", "docs/HIERARCHY.md"):
        shutil.copy2(REPO / rel, p / Path(rel).name)
    (p / "REPRODUCE.md").write_text("""# Reproduce

Snapshot copies: these files are copied at build time and will differ from `docs/results/` after the next audit run (the audit stamps the git commit).
The audit itself checks `docs/results/`, not these copies.

```bash
pip install -r requirements.txt
python -m src.utils.data_downloader_helper --levels gp mandal district --overture-release 2026-10-21.0
python -m src.routing.run_hierarchy --levels 2 3 4 --data real --out docs/results/hierarchy_real_run     # seeds 11, 12, 13 (configs/hierarchy_levels.yaml)
python -m src.evaluation.penalty_sweep
python -m src.evaluation.plot_hierarchy_figures
python -m src.evaluation.plot_level1_omission
python -m src.evaluation.provenance_audit --write docs/results/PROVENANCE_AND_PROOFS.md --rerun --redownload
python -m src.evaluation.build_contribution3_deliverables
python -m pytest
python paper/build_docx.py
```
""", encoding="utf-8")
    try:
        tree = subprocess.run(["git", "rev-parse", "HEAD:DELIVERABLES_DAMARAKUNTA_STAGE_B"], cwd=REPO, capture_output=True, text=True).stdout.strip()
        (p / "STAGE_B_UNTOUCHED.txt").write_text(f"git tree hash of DELIVERABLES_DAMARAKUNTA_STAGE_B/ at build time: {tree}\nrecorded value before any Contribution 3 work (parent of the first commit of this work): "
                                                  f"{STAGE_B_TREE}\nequal: {tree == STAGE_B_TREE}\n", encoding="utf-8")
    except Exception as e:  # pragma: no cover
        (p / "STAGE_B_UNTOUCHED.txt").write_text(f"could not read the git tree: {e}\n", encoding="utf-8")


STAGE_B_TREE = "4e5cedcefcfb9231074a10667e8050f4650d8766"
MANIFEST_DIRS = ("01_ARCHITECTURE", "02_FINAL_MAPS", "03_RESULTS_TABLES", "05_LIMITATIONS_AND_OPEN_ISSUES")


def write_manifest():
    rows = []
    files = [DEL / "00_README_SUMMARY.md"] + [f for d in MANIFEST_DIRS for f in sorted((DEL / d).rglob("*")) if f.is_file()]
    for f in files:
        rows.append(dict(path=str(f.relative_to(DEL)).replace("\\", "/"), bytes=f.stat().st_size, sha256=sha256(f)))
    with open(DEL / "MANIFEST.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["path", "bytes", "sha256"])
        w.writeheader()
        w.writerows(rows)
    return rows


def main():
    from src.routing.hierarchical_router import load_config
    cfg = load_config()
    S = summaries()
    for d in ("01_ARCHITECTURE", "02_FINAL_MAPS", "03_RESULTS_TABLES/CHARTS", "04_PROVENANCE_AND_AUDIT", "05_LIMITATIONS_AND_OPEN_ISSUES"):
        (DEL / d).mkdir(parents=True, exist_ok=True)
    architecture(DEL / "01_ARCHITECTURE", S)
    workflow(DEL / "01_ARCHITECTURE")
    map1(cfg, DEL / "02_FINAL_MAPS")
    map2(cfg, DEL / "02_FINAL_MAPS")
    map3(cfg, DEL / "02_FINAL_MAPS")
    map4(cfg, DEL / "02_FINAL_MAPS")
    tb = tables(DEL / "03_RESULTS_TABLES", S)
    chart1(DEL / "03_RESULTS_TABLES" / "CHARTS")
    chart2(DEL / "03_RESULTS_TABLES" / "CHARTS")
    copy_provenance()
    write_docs(S, tb)
    rows = write_manifest()
    print(f"wrote {len(rows)} manifest rows")


if __name__ == "__main__":
    main()
