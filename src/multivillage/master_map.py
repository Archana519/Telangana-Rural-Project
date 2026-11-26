"""Self-explaining satellite planning maps (Damarakunta style) for any study area.

One `Scene` (footprints, road-gap target houses, verified facilities, existing roads, alternative / independent routes, proposed shared routes, numbers) is drawn as

* `render_master`  the all-in-one master planning map: whole study window + zoomed inset of the densest cluster + facility key + legend + summary block;
* `render_panel`   single-panel satellite figures (whole window or zoom; overview, independent routes, shared network), each with its own legend and summary lines.

Conventions (identical in every figure, so a colour never changes meaning):
    cyan solid      existing road (Overture / OSM / TGRAC)           white dashed  alternative = independent least-cost route (Stage A first choice)
    blue solid      proposed shared two-stage network, house routes  red solid     proposed shared network, facility routes
    orange fill     road-gap target house (routing target)           white fill    other detected footprint
    markers         star = school, cross = health (hospital / PHC / sub-centre), square = government office, triangle = anganwadi, diamond = other
    yellow outline  study-area boundary

The proposed and alternative routes come from `clearance.py` (footprints hard-blocked, lane from the building edge), so none of them runs over a rooftop; the
number checked is printed in each summary. Satellite panels carry the Esri credit. Costs: km x the owner-supplied, unverified PMGSY-based rate (illustrative only).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import geopandas as gpd
import matplotlib
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from pyproj import Transformer
from shapely.geometry import box

from . import segmentation_variant as SV

matplotlib.use("Agg")
import matplotlib.pyplot as plt                                    # noqa: E402

CRS = "EPSG:32644"
CREDIT = SV.CREDIT
TO_WGS = Transformer.from_crs(CRS, "EPSG:4326", always_xy=True)
FROM_WGS = Transformer.from_crs("EPSG:4326", CRS, always_xy=True)
C_ROAD, C_SHARED, C_FAC, C_INDEP, C_BOUND, C_GAP = "#00e5ff", "#2f5bff", "#e00000", "#ffffff", "#ffeb3b", "#ff7f0e"
FSTYLE = {"school": ("*", "#1f78b4", "School"), "college": ("h", "#00acc1", "College / higher education"), "health": ("P", "#e31a1c", "Hospital / health centre"), "government": ("s", "#6a3d9a", "Government / civic office"),
          "anganwadi": ("^", "#ff69b4", "Anganwadi / welfare centre"), "other": ("D", "#00897b", "Other public facility")}
NOTE = ("Footprints are automatic detections (unvalidated; merged roofs are flagged), not a census. Routes are planning alternatives, not engineered roads. "
        "EPSG:32644 (UTM 44N).")


def rates() -> tuple:
    p = Path(__file__).resolve().parents[2] / "inputs/economic_assumptions.json"
    a = json.loads(p.read_text(encoding="utf-8"))["rate_lakh_per_km"]
    return a["low"], a["central"], a["high"]


def lakh(km: float, r: float) -> str:
    return f"Rs {km * r:,.0f} lakh"


def ftype(t) -> str:
    return t if t in FSTYLE else "other"


@dataclass
class Scene:
    name: str                                   # exact study-area name
    boundary_label: str
    cell: object                                # shapely polygon, EPSG:32644
    roads: gpd.GeoSeries
    footprints: gpd.GeoDataFrame                # all detected footprints (quality_class[_model])
    gap: gpd.GeoDataFrame                       # road-gap target houses
    fac: gpd.GeoDataFrame                       # fid, name, facility_type, geometry (verified, used)
    indep_house: list = field(default_factory=list)
    shared_house: list = field(default_factory=list)
    indep_fac: list = field(default_factory=list)
    shared_fac: list = field(default_factory=list)
    stats: dict = field(default_factory=dict)   # see scene_from_clearance
    mosaic: Path | None = None
    routed_fids: set = field(default_factory=set)
    footprint_source: str = "StrongDINOv2Seg + OpenCV"
    routing_note: str = ""
    allow_service: bool = False


def scene_from_clearance(name, boundary_label, cell, roads, footprints, gap, fac, clear: dict, mosaic=None, footprint_source="StrongDINOv2Seg + OpenCV") -> Scene:
    H, F, U, V = clear["houses"], clear["facilities"], clear["unique"], clear["verify"]
    q = footprints["quality_class_model"] if "quality_class_model" in footprints else footprints["quality_class"]
    routed = {int(str(r["target"]).split(":")[1]) for r in F["shared"]}
    st = dict(n_footprints=len(footprints), quality=q.value_counts().to_dict(), n_gap=len(gap), house_targets=H["targets"], house_routed=len(H["shared"]), house_unreachable=len(H["unreachable"]) + len(H["fails"]),
              fac_targets=F["targets"], fac_routed=len(F["shared"]), fac_unrouted=len(F["unreachable"]) + len(F["fails"]),
              indep_m=U["house_indep_m"], shared_m=U["house_shared_m"], fac_m=max(0.0, U["combined_shared_m"] - U["house_shared_m"]), combined_m=U["combined_shared_m"], combined_indep_m=U["combined_indep_m"],
              roads_km=float(roads.length.sum()) / 1000, area_km2=cell.area / 1e6, verify=V, grid_m=clear["params"]["grid_m"], clearance_m=clear["params"]["clearance_m"])
    return Scene(name=name, boundary_label=boundary_label, cell=cell, roads=roads, footprints=footprints, gap=gap, fac=fac, indep_house=[r["geom"] for r in H["indep"]], shared_house=[r["geom"] for r in H["shared"]],
                 indep_fac=[r["geom"] for r in F["indep"]], shared_fac=[r["geom"] for r in F["shared"]], stats=st, mosaic=Path(mosaic) if mosaic else None, routed_fids=routed, footprint_source=footprint_source)


# ------------------------------------------------------------------------------------------------ drawing helpers
def ticks(ax, ext):
    x0, y0, x1, y1 = ext
    lon0, lat0 = TO_WGS.transform(x0, y0)
    lon1, lat1 = TO_WGS.transform(x1, y1)
    span = max(lon1 - lon0, lat1 - lat0)
    step = 0.002 if span < 0.02 else (0.005 if span < 0.05 else 0.01)
    if span / step > 6:
        step *= 2
    lons = np.arange(np.ceil(lon0 / step) * step, lon1, step)[:7]
    lats = np.arange(np.ceil(lat0 / step) * step, lat1, step)[:7]
    ax.set_xticks([FROM_WGS.transform(l, (lat0 + lat1) / 2)[0] for l in lons]); ax.set_xticklabels([f"{l:.3f}°E" for l in lons], fontsize=6)
    ax.set_yticks([FROM_WGS.transform((lon0 + lon1) / 2, l)[1] for l in lats]); ax.set_yticklabels([f"{l:.3f}°N" for l in lats], fontsize=6, rotation=90, va="center")
    ax.grid(color="w", alpha=0.25, lw=0.4); ax.tick_params(length=2)


def decor(ax, ext, scale_m, north=True):
    x0, y0, x1, y1 = ext
    sx, sy = x0 + 0.04 * (x1 - x0), y0 + 0.05 * (y1 - y0)
    ax.plot([sx, sx + scale_m], [sy, sy], color="k", lw=2.6, zorder=30, solid_capstyle="butt")
    ax.text(sx + scale_m / 2, sy + 0.015 * (y1 - y0), f"{scale_m / 1000:g} km" if scale_m >= 1000 else f"{scale_m:g} m", ha="center", va="bottom", fontsize=7, zorder=31, bbox=dict(fc="w", ec="none", alpha=0.85, pad=1))
    if north:
        ax.annotate("N", xy=(x1 - 0.05 * (x1 - x0), y1 - 0.03 * (y1 - y0)), xytext=(x1 - 0.05 * (x1 - x0), y1 - 0.12 * (y1 - y0)), ha="center", fontsize=9, fontweight="bold",
                    arrowprops=dict(arrowstyle="-|>", color="k", lw=1.4), zorder=31, bbox=dict(fc="w", ec="none", alpha=0.75, pad=1))


def esri_png(ext, px):
    """Esri World Imagery window through the export service, cached on disk (data/esri_cache/<hash>.png) so that a repeat run, or a demo without internet, reuses the exact same imagery.
    Returns the PNG bytes, or None when the window is neither cached nor reachable (the caller then draws the map without a basemap)."""
    import hashlib
    import os

    import requests
    d = Path(__file__).resolve().parents[2] / "data" / "esri_cache"
    f = d / (hashlib.md5(f"{[round(float(v), 1) for v in ext]}|{px}".encode()).hexdigest() + ".png")
    if f.exists():
        return f.read_bytes()
    if os.environ.get("DEMO_OFFLINE"):
        return None
    try:
        r = requests.get("https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/export", params=dict(bbox=",".join(map(str, ext)), bboxSR=32644, imageSR=32644, size=f"{px},{px}", format="png", f="image"),
                         headers={"User-Agent": "map-series/1.0"}, timeout=25)
        from PIL import Image
        import io
        Image.open(io.BytesIO(r.content)).verify()
        d.mkdir(parents=True, exist_ok=True)
        f.write_bytes(r.content)
        return r.content
    except Exception:
        return None


def background(sc: Scene, ax, ext, max_px=2400):
    ax.set_facecolor("#ececec")
    if sc.mosaic is not None and Path(sc.mosaic).exists():
        img, ex = SV._read_rgb(Path(sc.mosaic), ext, max_px=max_px)
        ax.imshow(img, extent=ex, origin="upper", zorder=0)
        ax.text(0.995, 0.004, CREDIT, transform=ax.transAxes, ha="right", va="bottom", fontsize=4.6, color="w", zorder=40, bbox=dict(fc="k", alpha=0.5, ec="none", pad=1))
    elif getattr(sc, "allow_service", False):                            # no local mosaic: the same Esri World Imagery through its export service (opt-in)
        import io

        from PIL import Image
        data = esri_png(ext, int(min(max_px, 2000)))
        if data is not None:
            ax.imshow(np.asarray(Image.open(io.BytesIO(data)).convert("RGBA")), extent=(ext[0], ext[2], ext[1], ext[3]), origin="upper", zorder=0)
            ax.text(0.995, 0.004, CREDIT, transform=ax.transAxes, ha="right", va="bottom", fontsize=4.6, color="w", zorder=40, bbox=dict(fc="k", alpha=0.5, ec="none", pad=1))
    ax.set_xlim(ext[0], ext[2]); ax.set_ylim(ext[1], ext[3])


def window_ext(sc: Scene, pad=100):
    b = sc.cell.bounds
    return (b[0] - pad, b[1] - pad, b[2] + pad, b[3] + pad)


def pick_zoom(sc: Scene, w=1300.0, h=950.0, exclude=None):
    """Densest cluster: window with the most road-gap houses plus 25 per verified facility (so the labelled facilities are in view)."""
    pts = [(p.x, p.y, 1.0) for p in sc.gap.geometry.representative_point()] + [(g.x, g.y, 25.0) for g in sc.fac.geometry]
    if exclude is not None:                                              # a second window: ignore the points already inside `exclude`
        pts = [q for q in pts if not (exclude[0] - w / 2 < q[0] < exclude[2] + w / 2 and exclude[1] - h / 2 < q[1] < exclude[3] + h / 2)] or pts
    if not pts:
        return window_ext(sc)
    a = np.array(pts)
    b = sc.cell.bounds
    best, arg = -1, None
    for cx, cy, _ in a[:: max(1, len(a) // 300)]:
        s = float(a[(abs(a[:, 0] - cx) < w / 2) & (abs(a[:, 1] - cy) < h / 2), 2].sum())
        if s > best:
            best, arg = s, (cx, cy)
    cx = min(max(arg[0], b[0] + w / 2), b[2] - w / 2) if b[2] - b[0] > w else (b[0] + b[2]) / 2
    cy = min(max(arg[1], b[1] + h / 2), b[3] - h / 2) if b[3] - b[1] > h else (b[1] + b[3]) / 2
    return (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)


def draw_footprints(sc: Scene, ax, ext, zoom, reg_alpha=0.35, gap_alpha=0.85, reg_lw=None, gap_lw=None):
    fp = sc.footprints
    gids = set(sc.gap["hid"]) if "hid" in sc.gap else set()
    box_ = box(*ext)
    near = fp[fp.geometry.intersects(box_)]
    if "hid" in near and gids:
        reg, gp = near[~near["hid"].isin(gids)], near[near["hid"].isin(gids)]
    else:
        reg, gp = near, sc.gap[sc.gap.geometry.intersects(box_)]
    if len(reg):
        reg.plot(ax=ax, fc="#ffffff", ec="#ffffff", alpha=reg_alpha, lw=reg_lw if reg_lw is not None else (0.3 if not zoom else 0.6), zorder=5)
    if len(gp):
        gp.plot(ax=ax, fc=C_GAP, ec="#7a3a00", alpha=gap_alpha, lw=gap_lw if gap_lw is not None else (0.2 if not zoom else 0.6), zorder=6)


STAGE_A_DASH = (0, (5, 3))


def draw_routes(sc: Scene, ax, zoom, indep=True, shared=True, lw_house=None, lw_fac=None, casing=True):
    """Stage A (independent alternatives): white dashed on a dark dashed underlay, drawn ABOVE the shared network so both stay visible. Stage B: blue house routes, red facility routes."""
    k = 1.0 if not zoom else 1.8
    lh = lw_house if lw_house is not None else 1.2 * k
    lf = lw_fac if lw_fac is not None else 1.6 * k
    if shared:
        if sc.shared_house:
            if casing:
                gpd.GeoSeries(sc.shared_house, crs=CRS).plot(ax=ax, color="#ffffff", lw=lh * 1.4, alpha=0.55, zorder=8)       # thin white casing so the blue reads on any imagery
            gpd.GeoSeries(sc.shared_house, crs=CRS).plot(ax=ax, color=C_SHARED, lw=lh, zorder=9)
        if sc.shared_fac:
            if casing:
                gpd.GeoSeries(sc.shared_fac, crs=CRS).plot(ax=ax, color="#ffffff", lw=lf * 1.4, alpha=0.6, zorder=9)
            gpd.GeoSeries(sc.shared_fac, crs=CRS).plot(ax=ax, color=C_FAC, lw=lf, zorder=10)
    if indep and sc.indep_house:
        lw = 1.1 if not zoom else 1.4
        geoms = sc.indep_house + sc.indep_fac
        gpd.GeoSeries(geoms, crs=CRS).plot(ax=ax, color="#000000", lw=lw + 0.9, linestyle=STAGE_A_DASH, alpha=0.55, zorder=10.8)
        gpd.GeoSeries(geoms, crs=CRS).plot(ax=ax, color=C_INDEP, lw=lw, linestyle=STAGE_A_DASH, alpha=1.0, zorder=11)


def plot_facilities(sc: Scene, ax, ext, size, label=False, edge_lw=0.7):
    f = sc.fac
    for k, (m, c, _) in FSTYLE.items():
        g = f[f.facility_type.map(ftype) == k]
        g = g[g.geometry.within(box(*ext))]
        if len(g):
            ax.scatter(g.geometry.x, g.geometry.y, marker=m, s=size, c=c, edgecolors="w", linewidths=edge_lw, zorder=20)
    if label:
        for _, r in f[f.geometry.within(box(*ext))].iterrows():
            ax.annotate(f"F{int(r.fid)}", (r.geometry.x, r.geometry.y), xytext=(5, 5), textcoords="offset points", fontsize=6, fontweight="bold", zorder=45, bbox=dict(fc="w", ec="none", alpha=0.8, pad=0.7))


def legend_handles(sc: Scene, with_routes=True, with_indep=True, with_shared=True):
    h = [Line2D([0], [0], color=C_BOUND, lw=2, label="Study-area boundary"),
         Line2D([0], [0], color=C_ROAD, lw=2, label="Existing road"),
         Patch(fc="#ffffff", ec="#ffffff", alpha=0.45, label="Detected footprint (other)"), Patch(fc=C_GAP, ec="#7a3a00", alpha=0.85, label="Road-gap target house (> 30 m from a road)")]
    if with_routes:
        if with_indep:
            h.append(Line2D([0], [0], color=C_INDEP, lw=1.6, linestyle=(0, (4, 3)), label="Alternative: independent least-cost route (Stage A first choice)"))
        if with_shared:
            h += [Line2D([0], [0], color=C_SHARED, lw=2.4, label="Proposed shared two-stage network: house routes"), Line2D([0], [0], color=C_FAC, lw=2.4, label="Proposed shared network: facility routes")]
    present = {ftype(t) for t in sc.fac.facility_type}
    for k, (m, c, lab) in FSTYLE.items():
        if k in present:
            h.append(Line2D([0], [0], marker=m, color="none", markerfacecolor=c, markeredgecolor="w", markersize=10, label=f"{lab} (n={int((sc.fac.facility_type.map(ftype) == k).sum())})"))
    return h


def legend(fig, handles, **kw):
    """Dark legend frame: white dashed routes, yellow boundary and cyan roads stay visible in the key as they are on the imagery."""
    lg = fig.legend(handles=handles, frameon=True, facecolor="#2b2b2b", edgecolor="#bbbbbb", labelcolor="white", framealpha=1.0, **kw)
    if lg.get_title() is not None:
        lg.get_title().set_color("white")
    return lg


def summary_lines(sc: Scene, routes=True, fac_key=False) -> list:
    s, (lo, ce, hi) = sc.stats, rates()
    q = s.get("quality", {})
    qtxt = ", ".join(f"{k.replace('_', ' ').lower()} {v:,}" for k, v in q.items())
    L = [f"Study area: {sc.name}; boundary: {sc.boundary_label}, {s['area_km2']:.2f} km². Detected footprints: {s['n_footprints']:,} ({qtxt}). Road-gap target houses: {s['n_gap']:,}; verified public facilities: {len(sc.fac)}; existing road length in the area: {s['roads_km']:.1f} km."]
    if routes and s.get("indep_m"):
        ik, sk, fk, ck = s["indep_m"] / 1000, s["shared_m"] / 1000, s["fac_m"] / 1000, s["combined_m"] / 1000
        sav = 100 * (1 - s["shared_m"] / s["indep_m"]) if s["indep_m"] else 0.0
        L.append(f"Routes (house targets routed {s['house_routed']:,} of {s['house_targets']:,}; unique length, shared sections counted once): alternative independent routes {s['indep_m']:,.0f} m ({ik:.2f} km) = {lakh(ik, ce)} | "
                 f"proposed shared network, houses {s['shared_m']:,.0f} m ({sk:.2f} km) = {lakh(sk, ce)} -> saving {sav:.1f}% ({s['indep_m'] - s['shared_m']:,.0f} m, {lakh((s['indep_m'] - s['shared_m']) / 1000, ce)}) | "
                 f"facility routes added {s['fac_m']:,.0f} m ({fk:.2f} km) | shared network incl. facilities {s['combined_m']:,.0f} m ({ck:.2f} km) = {lakh(ck, ce)}.")
        v = s["verify"]
        chk = sum(v[k]["routes_checked"] for k in v)
        crs_ = sum(v[k]["routes_crossing"] for k in v)
        crl = sum(v[k]["length_inside_other_footprints_m"] for k in v)
        L.append(f"Building clearance: footprints are hard-blocked with {s['clearance_m']:g} m clearance on a {s['grid_m']:g} m routing grid; each route starts at the edge of its own building. Checked {chk:,} drawn routes against all footprints: "
                 f"{crs_} cross another building ({crl:.1f} m inside other footprints). Unrouted: {s['house_targets'] - s['house_routed']} houses, {s['fac_unrouted']} facilities (no free lane / no path).")
    if fac_key and len(sc.fac):
        f = sc.fac.copy()
        f["t"] = f.facility_type.map(ftype)
        f["o"] = f.t.map({"health": 0, "government": 1, "school": 2, "college": 2, "anganwadi": 3, "other": 4})
        f = f.sort_values(["o", "fid"])
        items = [f"F{int(r.fid)} {r.t} {(r['name'] if isinstance(r['name'], str) else 'unnamed')[:40]}" for _, r in f.head(14).iterrows()]
        L.append("Facility key: " + "; ".join(items) + (f"; ... + {len(f) - 14} more (map_facility_key.csv)." if len(f) > 14 else "."))
    L.append(f"Costs: illustrative only = km x Rs {ce:g} lakh/km (range {lo:g}-{hi:g}); the rate is an owner-supplied, PMGSY-based assumption, NOT verified; not an engineering estimate; ordinal planning costs, not rupees. {NOTE} Footprints: {sc.footprint_source}.")
    return L


def wrap(text: str, width: int) -> str:
    import textwrap
    return "\n".join(textwrap.fill(t, width) for t in text.split("\n"))


def summary_block(fig, lines: list, y=0.008, width=330, fontsize=6.4, below=False):
    """Summary / explanation block. below=True hangs it under the canvas (saved with bbox_inches='tight') so it never overlaps a legend."""
    txt = "\n".join(wrap(l, width) for l in lines) + "\n" + CREDIT
    fig.text(0.012, -0.012 if below else y, txt, ha="left", va="top" if below else "bottom", fontsize=fontsize, linespacing=1.25, bbox=dict(fc="#f6f6f6", ec="#999999", lw=0.6, pad=3.5))


def facility_key(sc: Scene, ax, max_rows=26):
    """Facility key as a text panel: marker, label F<id>, type, name, routed or not (full list: map_facility_key.csv)."""
    ax.axis("off")
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    f = sc.fac.copy()
    f["t"] = f.facility_type.map(ftype)
    f["o"] = f.t.map({"health": 0, "government": 1, "school": 2, "college": 2, "anganwadi": 3, "other": 4})
    f = f.sort_values(["o", "fid"])
    ax.text(0.0, 1.0, f"Public facility key ({len(f)} verified)", fontsize=8, fontweight="bold", va="top")
    n = min(len(f), max_rows)
    ys = 0.955 - 0.0345 * np.arange(n + 1)
    for (y, (_, r)) in zip(ys, f.head(n).iterrows()):
        m, c, _ = FSTYLE[r.t]
        ax.scatter([0.03], [y], marker=m, s=46, c=c, edgecolors="k", linewidths=0.4, transform=ax.transAxes, clip_on=False)
        nm = r["name"] if isinstance(r["name"], str) else "(unnamed)"
        nm = nm if len(nm) <= 34 else nm[:32] + "…"
        ok = "routed" if int(r.fid) in sc.routed_fids else "not routed"
        ax.text(0.08, y, f"F{int(r.fid)} {r.t}: {nm} [{ok}]", fontsize=5.8, va="center", transform=ax.transAxes)
    if len(f) > n:
        ax.text(0.08, ys[-1], f"... + {len(f) - n} more: see map_facility_key.csv", fontsize=5.8, va="center", style="italic", transform=ax.transAxes)


def write_key_csv(sc: Scene, path):
    f = sc.fac.copy()
    lon, lat = TO_WGS.transform(f.geometry.x.values, f.geometry.y.values)
    pd.DataFrame(dict(label="F" + f.fid.astype(int).astype(str), name=f["name"], facility_type=f.facility_type, routed=f.fid.astype(int).isin(sc.routed_fids), lat=np.round(lat, 6), lon=np.round(lon, 6))).to_csv(path, index=False, lineterminator="\n")


# ------------------------------------------------------------------------------------------------ figures
def render_master(sc: Scene, out_png, dpi=200, zoom_ext=None):
    ext, zext = window_ext(sc), zoom_ext or pick_zoom(sc)
    W, Hh = ext[2] - ext[0], ext[3] - ext[1]
    fig = plt.figure(figsize=(17.5, 9.9))
    ax1 = fig.add_axes([0.02, 0.305, 0.30, 0.585]); ax2 = fig.add_axes([0.345, 0.305, 0.45, 0.585]); axk = fig.add_axes([0.815, 0.315, 0.18, 0.565])
    for ax, e, zoom in ((ax1, ext, False), (ax2, zext, True)):
        background(sc, ax, e)
        gpd.GeoSeries([sc.cell], crs=CRS).boundary.plot(ax=ax, color=C_BOUND, lw=1.2, zorder=3)
        sc.roads.plot(ax=ax, color="#000000", lw=2.2 if zoom else 1.5, alpha=0.5, zorder=3.5)
        sc.roads.plot(ax=ax, color=C_ROAD, lw=1.3 if zoom else 0.7, zorder=4)
        draw_footprints(sc, ax, e, zoom)
        draw_routes(sc, ax, zoom)
        plot_facilities(sc, ax, e, 150 if zoom else 38, label=zoom)
        decor(ax, e, 200 if zoom else 1000); ticks(ax, e)
        ax.set_xlabel(""); ax.set_ylabel("")
    gpd.GeoSeries([box(*zext)], crs=CRS).boundary.plot(ax=ax1, color="k", lw=1.5, zorder=9)
    for a_ in (ax1, ax2):
        a_.set_xlabel(""); a_.set_ylabel(""); a_.set_anchor("N")
    ax1.text(zext[0], zext[3], " zoom", color="k", fontsize=7, va="bottom", fontweight="bold", zorder=9, bbox=dict(fc="w", ec="none", alpha=0.8, pad=1))
    ax1.set_title("Whole study area", fontsize=10); ax2.set_title("Zoom: densest cluster of target houses and facilities", fontsize=10)
    facility_key(sc, axk)
    legend(fig, legend_handles(sc), loc="lower center", ncol=3, fontsize=7.6, bbox_to_anchor=(0.5, 0.125), title="Legend (same colours and line styles in every map)", title_fontsize=8)
    fig.suptitle(f"Master satellite planning map: {sc.name}", fontsize=14, y=0.975, fontweight="bold")
    s = sc.stats
    if s.get("indep_m"):
        fig.text(0.5, 0.935, f"Shared two-stage network (house routes) {s['shared_m'] / 1000:.2f} km vs independent alternatives {s['indep_m'] / 1000:.2f} km: saving {100 * (1 - s['shared_m'] / s['indep_m']):.1f}%; "
                 f"illustrative cost {lakh(s['shared_m'] / 1000, rates()[1])} vs {lakh(s['indep_m'] / 1000, rates()[1])} (Rs {rates()[1]:g} lakh/km, unverified)",
                 ha="center", va="center", fontsize=9)
    summary_block(fig, summary_lines(sc), y=0.006)
    Path(out_png).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=dpi)
    plt.close(fig)
    return Path(out_png)


def render_panel(sc: Scene, ext, out_png, kind: str, zoom: bool, dpi=300):
    """Single satellite panel with its own legend and summary: kind in {'overview', 'independent', 'two_stage'}."""
    ww, hh = ext[2] - ext[0], ext[3] - ext[1]
    fig = plt.figure(figsize=(7.4, 7.4 * hh / ww + 2.7))
    fh = fig.get_figheight()
    ax = fig.add_axes([0.03, 2.65 / fh, 0.94, 7.4 * hh / ww / fh * 0.94])
    background(sc, ax, ext)
    gpd.GeoSeries([sc.cell], crs=CRS).boundary.plot(ax=ax, color=C_BOUND, lw=1.0, zorder=3)
    sc.roads.plot(ax=ax, color="#000000", lw=1.8 if zoom else 1.2, alpha=0.45, zorder=3.5)
    sc.roads.plot(ax=ax, color=C_ROAD, lw=1.2 if zoom else 0.6, zorder=4)
    draw_footprints(sc, ax, ext, zoom)
    if kind == "independent":
        draw_routes(sc, ax, zoom, indep=True, shared=False)
    elif kind == "two_stage":
        draw_routes(sc, ax, zoom, indep=False, shared=True)
    plot_facilities(sc, ax, ext, 110 if zoom else 34, label=zoom)
    decor(ax, ext, 200 if zoom else 1000); ticks(ax, ext)
    ax.set_xlabel(""); ax.set_ylabel("")
    title = {"overview": "Footprints, road-gap target houses, facilities and existing roads", "independent": "Alternative independent least-cost routes (Stage A first choice)",
             "two_stage": "Proposed shared two-stage network"}[kind]
    ax.set_title(f"{sc.name}: {title} ({'zoom' if zoom else 'whole area'})", fontsize=8)
    legend(fig, legend_handles(sc, with_routes=kind != "overview", with_indep=kind == "independent", with_shared=kind == "two_stage"), loc="lower center", ncol=2, fontsize=6.4,
           bbox_to_anchor=(0.5, 1.28 / fh))
    lines = summary_lines(sc, routes=kind != "overview")
    if kind == "independent":
        lines = [lines[0]] + [l for l in lines[1:2]] if False else lines
    summary_block(fig, lines, y=0.006, width=185, fontsize=4.9)
    Path(out_png).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=dpi)
    plt.close(fig)
    return Path(out_png)


def render_legend_strip(sc: Scene, out_png, dpi=200):
    fig = plt.figure(figsize=(9.0, 1.6))
    legend(fig, legend_handles(sc), loc="center", ncol=3, fontsize=7)
    fig.savefig(out_png, dpi=dpi)
    plt.close(fig)
    return Path(out_png)
