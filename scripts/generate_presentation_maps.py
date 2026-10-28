#!/usr/bin/env python
"""Generate presentation maps for the Damarakunta smart-village project.

Run from the project root (D:\\Telangana_Rural_Project) with the project .venv:
    .venv\\Scripts\\python.exe scripts\\generate_presentation_maps.py

The script never edits source data. It writes only to
Siddipet/Damarakunta/results/presentation_maps (override with --out).
A figure is skipped (not faked) when its required inputs are missing.
Without georeferenced satellite imagery no figure is drawn unless you pass
--fallback-worldcover, which draws a clearly labelled land-cover background
(NOT satellite imagery) for draft previews only.
"""
import argparse, glob, hashlib, json, os, sys, datetime, math, warnings
warnings.filterwarnings('ignore', category=Warning, module='rasterio')
import numpy as np
import geopandas as gpd
import rasterio
from rasterio.vrt import WarpedVRT
from rasterio.windows import from_bounds
from rasterio.transform import from_origin
from rasterio.enums import Resampling
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle
from shapely.geometry import box

CRS = "EPSG:32644"
ROOT = os.getcwd()
SCOPE = ROOT   # discovery root; narrowed to the village folder in main()
VIL = os.path.join("Siddipet", "Damarakunta")
IMG_EXT = (".tif", ".tiff", ".vrt", ".jp2")
SKIP_DIRS = {".venv", "__pycache__", ".git", "presentation_maps", "node_modules"}
C = dict(road="#FFD400", route="#00E5FF", alt="#FF9100", build="#FF2D95", bridge="#FF1744",
         dangle="#FFFFFF", fac="#76FF03", bound="#FFFFFF", arec="#00E5FF")
LOG = []

def log(m):
    print(m); LOG.append(m)

def sha256(p, n=1 << 20):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(n), b""): h.update(b)
    return h.hexdigest()

def walk(root, exts):
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in SKIP_DIRS]
        for f in fn:
            if f.lower().endswith(exts): yield os.path.join(dp, f)

def first(patterns, root=None):
    root = root or SCOPE
    for pat in patterns:
        hits = sorted(glob.glob(os.path.join(root, "**", pat), recursive=True),
                      key=os.path.getmtime, reverse=True)
        hits = [h for h in hits if not any(s in h.split(os.sep) for s in SKIP_DIRS)]
        if hits: return hits[0]
    return None

def scan_imagery(forced=None):
    """Return every readable 3+ band georeferenced raster with its bounds (EPSG:32644)."""
    cands = []
    paths = [forced] if forced else list(walk(SCOPE, IMG_EXT))
    for p in paths:
        try:
            with rasterio.open(p) as r:
                if r.count < 3 or r.crs is None: continue
                with WarpedVRT(r, crs=CRS) as v:
                    b = tuple(v.bounds); res = abs(v.transform.a)
                cands.append(dict(path=p, bands=r.count, res_m=round(res, 3), crs=str(r.crs), bounds=b))
        except Exception:
            continue
    log(f"Imagery candidates scanned: {len(cands)}")
    for c in sorted(cands, key=lambda c: c["res_m"])[:12]:
        log(f"  {c['path']} | bands={c['bands']} res={c['res_m']} m crs={c['crs']}")
    return cands

def choose_imagery(cands, extent, min_cov):
    """Finest raster covering >= min_cov of the extent; None if none qualifies."""
    ex = box(*extent); ok = []
    for c in cands:
        cov = box(*c["bounds"]).intersection(ex).area / ex.area
        if cov >= min_cov: ok.append(dict(c, coverage=round(cov, 3)))
    return sorted(ok, key=lambda c: c["res_m"])[0] if ok else None

def attribution_for(info, base):
    if info and info["res_m"] > 2:
        return "Context imagery only (%.0f m pixels; too coarse for individual buildings/narrow roads). " % info["res_m"] + base
    return base + (" Black = outside imagery coverage." if info and info["coverage"] < 0.999 else "")

def read_rgb(path, extent, max_px=4000):
    minx, miny, maxx, maxy = extent
    W0, H0 = maxx - minx, maxy - miny
    with rasterio.open(path) as r:
        with WarpedVRT(r, crs=CRS) as v0:
            res = abs(v0.transform.a)
        res = max(res, max(W0, H0) / max_px)
        width, height = int(math.ceil(W0 / res)), int(math.ceil(H0 / res))
        T = from_origin(minx, maxy, res, res)
        with WarpedVRT(r, crs=CRS, transform=T, width=width, height=height,
                       resampling=Resampling.bilinear, nodata=0) as v:
            arr = v.read([1, 2, 3])
    arr = np.moveaxis(arr, 0, -1).astype(float)
    if arr.max() > 255: arr = arr / np.percentile(arr, 99.5) * 255
    return np.clip(arr, 0, 255).astype(np.uint8)

WC = {10: "#006400", 20: "#ffbb22", 30: "#ffff4c", 40: "#f096ff", 50: "#fa0000", 60: "#b4b4b4", 80: "#0064c8"}
def read_worldcover(path, extent):
    with rasterio.open(path) as r:
        w = from_bounds(*extent, r.transform)
        a = r.read(1, window=w, boundless=True, fill_value=0)
    rgb = np.full(a.shape + (3,), 235, np.uint8)
    for k, h in WC.items():
        rgb[a == k] = [int(h[i:i + 2], 16) for i in (1, 3, 5)]
    return rgb

def load(path, layer=None):
    g = gpd.read_file(path, layer=layer) if layer else gpd.read_file(path)
    if g.crs is None: raise ValueError(f"{path} has no CRS")
    return g.to_crs(CRS)


def pick_buildings(a, L):
    """Return (GeoDataFrame, source_description). Never creates geometry; only selects an existing polygon layer."""
    import fiona
    if a.buildings:
        g = load(a.buildings, a.buildings_layer); return g, f"{a.buildings} [{a.buildings_layer}]"
    for pat, layer in (("buildings_v8_full.gpkg", "buildings"), ("buildings_v7_full.gpkg", "buildings"), ("candidate_buildings_full.gpkg", "candidate_buildings")):
        p = first([pat])
        if p: return load(p, layer), f"{p} [{layer}]"
    if L.get("candidates") is not None: return L["candidates"], "audit candidates layer"
    return None, None

BSTYLE = "outline"
def plot_buildings(ax, g, extent):
    """Outline-only (default) or transparent fill, with a dark halo so roofs stay visible. Merged blobs are orange."""
    g = clip(g, extent)
    g = g[g.geom_type.isin(["Polygon", "MultiPolygon"])]
    if g.empty: return []
    qc = None
    for col in ("quality_class", "flag", "status", "kind"):
        if col in g.columns: qc = col; break
    merged = g[g[qc].astype(str).str.contains("MERGE|BLOB|UNRESOLVED", case=False, na=False)] if qc else g.iloc[0:0]
    single = g.drop(merged.index)
    h = []
    for part, col, lab in ((single, "#FFEB3B", "Model-predicted building footprints (unverified)"),
                           (merged, "#FF9100", "Merged built-up blobs (not single buildings)")):
        if part.empty: continue
        if BSTYLE == "fill": part.plot(ax=ax, facecolor=col, edgecolor="none", alpha=0.25, zorder=7)
        part.boundary.plot(ax=ax, color="black", lw=2.4, alpha=0.55, zorder=7.1)
        part.boundary.plot(ax=ax, color=col, lw=1.1, zorder=7.2)
        h.append(Line2D([], [], color=col, lw=2, label=lab))
    return h

def scalebar(ax, extent):
    minx, miny, maxx, maxy = extent
    w = maxx - minx
    for L in (50, 100, 200, 250, 500, 1000, 2000, 5000):
        if L > w / 6: break
    x0, y0 = minx + 0.04 * w, miny + 0.05 * (maxy - miny)
    ax.add_patch(Rectangle((x0 - 0.01 * w, y0 - 0.02 * w), L + 0.06 * w, 0.075 * w, fc="white", ec="none", alpha=0.7, zorder=20))
    ax.plot([x0, x0 + L], [y0, y0], color="k", lw=4, zorder=21, solid_capstyle="butt")
    ax.plot([x0, x0 + L / 2], [y0, y0], color="white", lw=2, zorder=22, solid_capstyle="butt")
    ax.text(x0 + L / 2, y0 + 0.012 * w, f"{L} m" if L < 1000 else f"{L/1000:g} km", ha="center", fontsize=9, zorder=22, weight="bold")

def north(ax, extent):
    minx, miny, maxx, maxy = extent
    x = maxx - 0.05 * (maxx - minx); y = maxy - 0.14 * (maxy - miny); h = 0.09 * (maxy - miny)
    ax.annotate("", xy=(x, y + h), xytext=(x, y), arrowprops=dict(arrowstyle="-|>", color="k", lw=2), zorder=22)
    ax.text(x, y + h * 1.06, "N", ha="center", va="bottom", fontsize=13, weight="bold", zorder=22,
            bbox=dict(fc="white", ec="none", alpha=0.7, pad=1))

def canvas(extent, bg, title, attribution, subtitle=None):
    minx, miny, maxx, maxy = extent
    ar = (maxx - minx) / (maxy - miny)
    fig, ax = plt.subplots(figsize=(11, max(5, 11 / ar)))
    ax.imshow(bg, extent=(minx, maxx, miny, maxy), origin="upper", interpolation="bilinear", zorder=0)
    ax.set_xlim(minx, maxx); ax.set_ylim(miny, maxy); ax.set_aspect("equal")
    ax.set_xticks([]); ax.set_yticks([])
    ax.set_title(title, fontsize=15, weight="bold", pad=10 if not subtitle else 22)
    if subtitle: ax.text(0.5, 1.012, subtitle, transform=ax.transAxes, ha="center", fontsize=9.5)
    ax.text(0.995, 0.005, attribution, transform=ax.transAxes, ha="right", va="bottom", fontsize=7.5, zorder=25,
            bbox=dict(fc="white", ec="none", alpha=0.75, pad=2))
    scalebar(ax, extent); north(ax, extent)
    return fig, ax

def clip(g, extent):
    return g[g.intersects(box(*extent))]

def plot_lines(ax, g, color, lw, z, ls="-", casing=True):
    if g is None or g.empty: return
    if casing: g.plot(ax=ax, color="black", linewidth=lw + 1.6, zorder=z - 0.1, linestyle=ls)
    g.plot(ax=ax, color=color, linewidth=lw, zorder=z, linestyle=ls)

def legend(ax, handles, title="Legend"):
    ax.legend(handles=handles, loc="upper left", fontsize=8.5, framealpha=0.9, title=title, title_fontsize=9.5)

def save(fig, out, name):
    for _a in fig.axes: _a.set_xlabel(''); _a.set_ylabel('')
    png = os.path.join(out, name + ".png")
    fig.savefig(png, dpi=300, bbox_inches="tight", facecolor="white")
    fig.savefig(os.path.join(out, name + ".pdf"), bbox_inches="tight", facecolor="white")
    plt.close(fig)
    log(f"WROTE {png} ({os.path.getsize(png)/1e6:.2f} MB) + PDF")
    return png

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--village-dir", default=VIL, help="village folder relative to the project root (e.g. Siddipet\\Damarakunta); outputs go to <village-dir>\\results\\presentation_maps")
    ap.add_argument("--buildings"); ap.add_argument("--buildings-layer")
    ap.add_argument("--building-style", choices=["outline", "fill"], default="outline")
    ap.add_argument("--imagery"); ap.add_argument("--boundary"); ap.add_argument("--roads")
    ap.add_argument("--facilities"); ap.add_argument("--audit"); ap.add_argument("--planner")
    ap.add_argument("--worldcover"); ap.add_argument("--out", default=None)
    ap.add_argument("--attribution", default="Imagery: source/licence to be confirmed (see README)")
    ap.add_argument("--min-coverage", type=float, default=0.8, help="min share of each map extent the imagery must cover (default 0.8; uncovered areas render black and the figure says so)")
    ap.add_argument("--pad", type=float, default=250.0, help="metres of padding around study features")
    ap.add_argument("--fallback-worldcover", action="store_true", help="DRAFT ONLY: use land-cover background, not satellite imagery")
    a = ap.parse_args()
    vroot = os.path.join(ROOT, a.village_dir)
    a.out = a.out or os.path.join(vroot, 'results', 'presentation_maps')
    global BSTYLE
    BSTYLE = a.building_style
    os.makedirs(a.out, exist_ok=True)
    used = {}
    global SCOPE
    SCOPE = vroot if os.path.isdir(vroot) else ROOT
    log(f'Village folder: {vroot} | discovery scope: {SCOPE}')
    roads_p = a.roads or first(["tgrac_road_network.gpkg", "*road_network*.gpkg"])
    fac_p = a.facilities or first(["*priority_facilities*.gpkg"])
    audit_p = a.audit or first([os.path.join("connectivity_audit_v1","ca1","connectivity_audit.gpkg"), "connectivity_audit.gpkg"])
    plan_p = a.planner or first(["network_v2.gpkg"])
    bound_p = a.boundary or first(["*boundary*.gpkg", "*boundary*.shp", "*village*boundary*.geojson"])
    wc_p = a.worldcover or first(["damarakunta_worldcover_10m.tif", "*worldcover*10m*.tif"])
    for k, v in dict(roads=roads_p, facilities=fac_p, audit=audit_p, planner=plan_p, boundary=bound_p, worldcover=wc_p).items():
        log(f"INPUT {k:10s}: {v or 'NOT FOUND'}"); used[k] = v
    roads = load(roads_p) if roads_p else None
    fac = load(fac_p) if fac_p else None
    bnd = load(bound_p) if bound_p else None
    # layers
    L = {}
    if audit_p:
        import fiona
        have = fiona.listlayers(audit_p); log(f"Audit layers: {have}")
        for n in ("candidates", "facilities", "road_segments", "dangling_ends", "inferred_bridges", "routes_at_attach_tol"):
            if n in have: L[n] = load(audit_p, n)
    P = {}
    if plan_p:
        import fiona
        have = fiona.listlayers(plan_p); log(f"Planner layers: {have}")
        for n in ("targets", "routes_network_aware", "stageA_alternatives"):
            if n in have: P[n] = load(plan_p, n)
    B, bsrc = pick_buildings(a, L)
    log(f"BUILDINGS: {bsrc or 'NONE FOUND'}"); used['buildings'] = bsrc
    # study extent: planner/audit/facility features + padding (never the whole mandal road layer)
    parts = [g for g in list(P.values()) + [B, L.get("facilities"), fac] if g is not None and not g.empty]
    if bnd is not None and not bnd.empty: parts = [bnd]   # the boundary defines the map frame
    if not parts: log("No study-area features found; cannot define extent."); sys.exit(1)
    tb = gpd.GeoSeries(pd_concat([g.geometry for g in parts]), crs=CRS).total_bounds
    ext = (tb[0] - a.pad, tb[1] - a.pad, tb[2] + a.pad, tb[3] + a.pad)
    log(f"Study extent EPSG:32644 (m): {tuple(round(float(x), 1) for x in ext)}")
    # imagery (chosen per figure, finest raster that covers the figure extent)
    cands = scan_imagery(a.imagery)
    info = choose_imagery(cands, ext, a.min_coverage)
    mode = "satellite" if info else None; bg = None; attrib = a.attribution
    if info:
        bg = read_rgb(info["path"], ext)
        attrib = attribution_for(info, a.attribution)
        log(f"IMAGERY figs 1/3/4: {info['path']} (res {info['res_m']} m, coverage {info['coverage']*100:.0f}%)")
        used["imagery"] = info; used["imagery_sha256"] = sha256(info["path"])
    elif a.fallback_worldcover and wc_p:
        bg = read_worldcover(wc_p, ext); mode = "worldcover"
        attrib = "DRAFT - NO SATELLITE IMAGERY. Background: ESA WorldCover 10 m (CC BY 4.0), land cover only"
        log("WARNING: no imagery covers the extent; using WorldCover DRAFT background.")
    else:
        best = sorted(cands, key=lambda c: c["res_m"])
        log(f"STOP: no raster covers {a.min_coverage*100:.0f}% of the study extent. Lower --min-coverage or pass --imagery PATH.")
        finish(a, used); sys.exit(2)
    tag = "" if mode == "satellite" else " [DRAFT: land-cover background]"
    # filter to extent
    R = clip(roads, ext) if roads is not None else None
    # Figure 1
    fig, ax = canvas(ext, bg, "Study Area Overview – Damarakunta, Markook Mandal, Siddipet" + tag, attrib)
    h = []
    if bnd is not None: bnd.boundary.plot(ax=ax, color=C["bound"], lw=2.2, zorder=6); h.append(Line2D([], [], color=C["bound"], lw=2.2, label="Study-area boundary"))
    else: log("Figure 1 note: no boundary layer found; none drawn (extent is feature bounds + padding).")
    if B is not None: h += plot_buildings(ax, B, ext)
    if R is not None and not R.empty: plot_lines(ax, R, C["road"], 2.0, 8); h.append(Line2D([], [], color=C["road"], lw=2.5, label="Existing mapped roads (TGRAC)"))
    fsrc = L.get("facilities") if L.get("facilities") is not None else fac
    if fsrc is not None and not fsrc.empty: fsrc.plot(ax=ax, color=C["fac"], edgecolor="black", markersize=70, marker="*", zorder=9); h.append(Line2D([], [], marker="*", ls="", mfc=C["fac"], mec="black", ms=11, label="Public facilities"))
    legend(ax, h); used["fig1"] = ["roads", "facilities", "boundary(if found)", "audit.candidates(if found)"]
    save(fig, a.out, "01_damarakunta_study_area_overview")
    # Figure 2
    cand = B
    if cand is None or cand.empty:
        log("SKIP Figure 2: building polygons (audit 'candidates' layer or model extraction GPKG) not found.")
    else:
        c = clip(cand, ext); cen = c.geometry.centroid
        # zoom window: the densest 500 m x 500 m block of polygons (so roofs are legible at 0.6 m)
        step, size = 125.0, 500.0
        gx = np.arange(ext[0], ext[2] - size + step, step); gy = np.arange(ext[1], ext[3] - size + step, step)
        best, bw = -1, None
        for x in gx:
            for y in gy:
                n = int(((cen.x >= x) & (cen.x < x + size) & (cen.y >= y) & (cen.y < y + size)).sum())
                if n > best: best, bw = n, (x, y)
        if best <= 0:
            log("SKIP Figure 2: no building polygons inside the study extent."); cand = None
        else:
            e2 = (bw[0], bw[1], bw[0] + size, bw[1] + size); keep = c
            log(f"Figure 2 zoom window (densest 500 m block, {best} polygons): {tuple(round(float(v),1) for v in e2)}")
    if cand is not None and not cand.empty:
        info2 = choose_imagery(cands, e2, a.min_coverage) if mode == "satellite" else None
        if mode == "satellite":
            info2 = info2 or info
            bg2 = read_rgb(info2["path"], e2); attrib2 = attribution_for(info2, a.attribution)
            log(f"IMAGERY fig 2: {info2['path']} (res {info2['res_m']} m)"); used["imagery_fig2"] = info2
        else:
            bg2 = read_worldcover(wc_p, e2); attrib2 = attrib
        fig, ax = canvas(e2, bg2, "Building Extraction and Road Network – Main Settlement" + tag, attrib2)
        hb2 = plot_buildings(ax, keep, e2)
        R2 = clip(roads, e2) if roads is not None else None
        if R2 is not None and not R2.empty: plot_lines(ax, R2, C["road"], 2.5, 8)
        legend(ax, hb2 + [Line2D([], [], color=C["road"], lw=2.5, label="Existing mapped roads")])
        save(fig, a.out, "02_building_extraction_road_network")
    # Figure 3
    if "routes_network_aware" not in P:
        log("SKIP Figure 3: planner GPKG with routes_network_aware not found.")
    else:
        fig, ax = canvas(ext, bg, "Proposed Rural Road Network (Planner Output)" + tag, attrib,
                         "Computed planning alternatives – not verified roads; routing cost units are not money")
        h = []
        if B is not None: h += plot_buildings(ax, B, ext)
        if R is not None and not R.empty: plot_lines(ax, R, C["road"], 2.0, 6); h.append(Line2D([], [], color=C["road"], lw=2.5, label="Existing mapped roads"))
        alt = P.get("stageA_alternatives")
        if alt is not None and not alt.empty: plot_lines(ax, alt, C["alt"], 1.4, 7, "--", casing=False); h.append(Line2D([], [], color=C["alt"], lw=2, ls="--", label="Stage-A alternative routes"))
        plot_lines(ax, P["routes_network_aware"], C["route"], 3.2, 8); h.append(Line2D([], [], color=C["route"], lw=3.5, label="Selected routes (network-aware planner)"))
        t = P.get("targets")
        if t is not None:
            for kind, mk, col, lab in (("FACILITY", "*", C["fac"], "Facility targets"), ("CLUSTER", "o", "white", "Building-cluster targets")):
                s = t[t["kind"] == kind] if "kind" in t else t
                if s.empty: continue
                pts = s.copy(); pts["geometry"] = pts.geometry.representative_point()
                pts.plot(ax=ax, marker=mk, color=col, edgecolor="black", markersize=95 if kind == "FACILITY" else 40, zorder=10)
                h.append(Line2D([], [], marker=mk, ls="", mfc=col, mec="black", ms=10, label=lab))
                if kind == "FACILITY":
                    for _, r in pts.iterrows(): ax.annotate(str(r.get("name", "")), (r.geometry.x, r.geometry.y), xytext=(6, 6), textcoords="offset points", fontsize=7.5, zorder=11, bbox=dict(fc="white", ec="none", alpha=0.75, pad=1))
        legend(ax, h)
        save(fig, a.out, "03_proposed_rural_road_network")
    # Figure 4
    if not L:
        log("SKIP Figure 4: connectivity_audit.gpkg not found (path: Siddipet/Damarakunta/results/connectivity_audit_v1/ca1/connectivity_audit.gpkg).")
    else:
        fig, ax = canvas(ext, bg, "Road Connectivity Audit (ca1)" + tag, attrib, "Inferred bridges are candidates requiring verification – proximity is not proven connectivity")
        h = []
        BB = L.get("candidates") if L.get("candidates") is not None else B
        if BB is not None: h += plot_buildings(ax, BB, ext)
        seg = L.get("road_segments", R)
        if seg is not None and not seg.empty: plot_lines(ax, clip(seg, ext), C["road"], 2.0, 6); h.append(Line2D([], [], color=C["road"], lw=2.5, label="Existing mapped road segments"))
        if "routes_at_attach_tol" in L: plot_lines(ax, clip(L["routes_at_attach_tol"], ext), C["route"], 2.4, 7); h.append(Line2D([], [], color=C["route"], lw=3, label="Recorded route geometries (attach tolerance)"))
        if "inferred_bridges" in L and not L["inferred_bridges"].empty: plot_lines(ax, clip(L["inferred_bridges"], ext), C["bridge"], 2.2, 8, "--"); h.append(Line2D([], [], color=C["bridge"], lw=2.5, ls="--", label="Inferred bridge candidates (require verification)"))
        if "dangling_ends" in L and not L["dangling_ends"].empty: clip(L["dangling_ends"], ext).plot(ax=ax, color=C["dangle"], edgecolor="black", markersize=26, zorder=9); h.append(Line2D([], [], marker="o", ls="", mfc=C["dangle"], mec="black", ms=7, label="Dangling endpoints"))
        if "facilities" in L and not L["facilities"].empty: L["facilities"].plot(ax=ax, color=C["fac"], edgecolor="black", markersize=80, marker="*", zorder=10); h.append(Line2D([], [], marker="*", ls="", mfc=C["fac"], mec="black", ms=11, label="Facility records"))
        legend(ax, h)
        save(fig, a.out, "04_damarakunta_connectivity_audit_satellite")
    finish(a, used)

def pd_concat(series):
    import pandas as pd
    return pd.concat(series, ignore_index=True)

def finish(a, used):
    prov = dict(generated=datetime.datetime.now().isoformat(timespec="seconds"), crs=CRS, inputs=used, log=LOG)
    p = os.path.join(a.out, "provenance.json")
    with open(p, "w", encoding="utf-8") as f: json.dump(prov, f, indent=2, default=str)
    log(f"Provenance: {p}")

if __name__ == "__main__":
    main()
