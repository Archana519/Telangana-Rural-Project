#!/usr/bin/env python
"""Supplementary local-scale detail maps for Damarakunta.

Read-only on all project data. It imports drawing helpers and constants from Damarakunta_Final_Map_v4_1.py
(never runs its main()), reads the verified v4.1 package layers, and writes ONLY into a new, non-existing folder.
Selection of the two areas is data-driven and the script stops (exit 2) if the evidence is ambiguous.
"""
import sys, json, argparse, textwrap
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import Damarakunta_Final_Map_v4_1 as M
import numpy as np, geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.legend_handler import HandlerTuple
from shapely.ops import unary_union
from shapely.geometry import box
from PIL import Image
Image.MAX_IMAGE_PIXELS = None

NAME_MAIN = "Main settlement"          # displayed names; files use fixed slugs below
NAME_EAST = "Eastern cluster"
GAP_M, PAD_M, MIN_GROUP, MIN_EAST_OFFSET_M = 120.0, 60.0, 15, 1000.0
FIG_W, FIG_H, L, R, T, B = 18.0, 11.0, .06, .79, .90, .17
RATIO = (FIG_W*(R-L))/(FIG_H*(T-B))

def die(msg, code=2):
    print("STOP:", msg); sys.exit(code)

def check_crs(name, g):
    e = g.crs.to_epsg() if g.crs is not None else None
    if e != 32644: die(f"{name} CRS is {g.crs}, expected EPSG:32644", 3)

def find_groups(bld):
    u = unary_union([g.buffer(GAP_M/2) for g in bld.geometry])
    parts = list(u.geoms) if u.geom_type == "MultiPolygon" else [u]
    return [bld[bld.geometry.intersects(p)] for p in parts if bld.geometry.intersects(p).any()]

def stats(s, fac):
    x0, y0, x1, y1 = s.total_bounds
    w = box(x0-70, y0-70, x1+70, y1+70)
    names = [str(n) for n in fac[fac.geometry.intersects(w)]["facility_name_map"]] if len(fac) else []
    return dict(n=int(len(s)), centre_E=float(s.centroid.x.mean()), centre_N=float(s.centroid.y.mean()),
                extent_W_m=float(x1-x0), extent_H_m=float(y1-y0), facilities_in_extent=names,
                quality={str(k): int(v) for k, v in s.quality_class.value_counts().items()})

def window_for(s):
    x0, y0, x1, y1 = s.total_bounds; x0 -= PAD_M; y0 -= PAD_M; x1 += PAD_M; y1 += PAD_M
    w = max(x1-x0, 300.0); h = max(y1-y0, 300.0)
    if w/h < RATIO: w = h*RATIO
    else: h = w/RATIO
    cx, cy = (x0+x1)/2, (y0+y1)/2
    return (cx-w/2, cy-h/2, cx+w/2, cy+h/2)

def select(bld, fac):
    gs = sorted(find_groups(bld), key=lambda s: -len(s))
    info = [stats(s, fac) for s in gs]
    print(f"Footprint groups (gap {GAP_M:g} m): {len(gs)}")
    for i, d in enumerate(info[:6]):
        print(f"  group {i+1}: n={d['n']} centre=({d['centre_E']:.0f},{d['centre_N']:.0f}) extent={d['extent_W_m']:.0f}x{d['extent_H_m']:.0f} m facilities={d['facilities_in_extent']}")
    big = [i for i, d in enumerate(info) if d["n"] >= MIN_GROUP]
    if len(big) < 2: die("fewer than two groups reach the minimum size; cannot select two areas confidently")
    if len(info) > 1 and info[0]["n"] == info[1]["n"]: die("largest group is not unique")
    mi = 0
    if not info[mi]["facilities_in_extent"]: die("largest group contains no facility; cannot call it the main settlement")
    east = max((i for i in big if i != mi), key=lambda i: info[i]["centre_E"])
    if info[east]["centre_E"] < info[mi]["centre_E"] + MIN_EAST_OFFSET_M: die("no qualifying group lies at least 1 km east of the main settlement")
    return [(NAME_MAIN, "main_settlement", gs[mi], info[mi]), (NAME_EAST, "eastern_cluster", gs[east], info[east])]

def draw_one(out, title_name, slug, s, st, bld, roads, boundary, school_comp, fac, routes, img_path):
    bounds = window_for(s); win = box(*bounds)
    img, ib = M.read_satellite_crop(img_path, bounds, max_dim=6000)
    res = (ib[2]-ib[0])/img.shape[1]; zero = float((img.max(axis=2) <= 0).mean())
    fig = plt.figure(figsize=(FIG_W, FIG_H)); ax = fig.add_axes([L, B, R-L, T-B]); M.show_bg(ax, img, ib)
    bnd = gpd.GeoSeries([boundary], crs=M.CRS)
    bnd.boundary.plot(ax=ax, color="#111827", lw=3.6, zorder=1.9); bnd.boundary.plot(ax=ax, color="white", lw=1.6, zorder=2)
    if not roads.empty: roads.plot(ax=ax, color=M.EXISTING, lw=2.2, alpha=.97, zorder=3)
    for q in ("PLAUSIBLE", "REVIEW", "UNRESOLVED_MERGE", "UNKNOWN"):
        ss = bld[bld.quality_class == q]
        if not ss.empty: ss.boundary.plot(ax=ax, color=M.QCOL[q], lw=1.2, zorder=5)
    if not routes.empty: routes.plot(ax=ax, color=M.PROPOSED, lw=2.2, alpha=.95, zorder=7)
    sc_in = school_comp[school_comp.intersects(win)] if not school_comp.empty else school_comp
    if not sc_in.empty: sc_in.boundary.plot(ax=ax, color="#ed70ff", lw=1.6, linestyle="--", zorder=8)
    fin = fac[fac.geometry.intersects(win)] if len(fac) else fac
    mk = {"SCHOOL": "*", "HEALTH": "P", "ANGANWADI": "^", "GOVERNMENT": "s", "OTHER": "D"}
    offs = [(9, 9), (9, -18), (-20, 9), (-20, -18)]; key = []
    for k, (_, r) in enumerate(fin.iterrows()):
        p = M.get_point(r.geometry); cat = r["facility_category_map"]
        ax.scatter([p.x], [p.y], s=190 if cat in ("SCHOOL", "ANGANWADI") else 130, marker=mk.get(cat, "D"), c=M.FAC_COL[cat], edgecolors="#111827", linewidths=.9, zorder=12)
        ax.annotate(str(k+1), (p.x, p.y), xytext=offs[k % 4], textcoords="offset points", fontsize=11, fontweight="bold", color="white", zorder=13,
                    bbox=dict(boxstyle="round,pad=.2", fc="#101923", ec=M.FAC_COL[cat], lw=.8, alpha=.95))
        key.append(f"{k+1}  {r['facility_name_map']} [{cat}; source location unverified]")
    w = bounds[2]-bounds[0]; h = bounds[3]-bounds[1]
    bar = max(b for b in (20, 50, 100, 200, 500) if b <= .25*w)
    sx = bounds[2]-.04*w-bar; sy = bounds[1]+.06*h
    ax.plot([sx, sx+bar], [sy, sy], color="white", lw=7, solid_capstyle="butt", zorder=20); ax.plot([sx, sx+bar], [sy, sy], color="#111827", lw=3.5, solid_capstyle="butt", zorder=21)
    ax.text(sx+bar/2, sy+.012*h, f"{bar:g} m", ha="center", va="bottom", fontsize=10, color="white", fontweight="bold", bbox=dict(fc="#111827", ec="none", alpha=.85, pad=2), zorder=22)
    ax.text(.035, .955, "▲\nN", transform=ax.transAxes, ha="center", va="top", fontsize=14, fontweight="bold", color="white", bbox=dict(boxstyle="round,pad=.3", fc="#111827", ec="white", alpha=.9), zorder=22)
    ax.set_xlim(bounds[0], bounds[2]); ax.set_ylim(bounds[1], bounds[3]); ax.set_aspect("equal", adjustable="box")
    inview = bld[bld.geometry.intersects(win)]; qv = {k: int(v) for k, v in inview.quality_class.value_counts().items()}
    rv = int(routes.geometry.intersects(win).sum()) if not routes.empty else 0
    ax.set_title(f"DAMARAKUNTA — {title_name}: local-scale detail (supplementary view)\nModel-derived candidate footprints and proposed routes; unverified", fontsize=14, fontweight="bold", pad=10)
    ax.set_xlabel("Easting (m), EPSG:32644"); ax.set_ylabel("Northing (m), EPSG:32644"); ax.tick_params(labelsize=8); ax.grid(alpha=.14, lw=.4); ax.ticklabel_format(useOffset=False, style="plain")
    notes = ["IN VIEW", f"{len(inview)} candidate footprints:", "  " + ", ".join(f"{k} {v}" for k, v in sorted(qv.items())), f"{rv} proposed route features intersect the view.", "",
             "FACILITIES (source records, not independently verified)"] + (key if key else ["none in view"]) + ["",
             "NOTES", f"Imagery resampled to {res:.2f} m/pixel (native mosaic pixels shown without smoothing).",
             "Map grid north (EPSG:32644) differs from true north by about 0.7 deg.",
             "DRAFT: footprints and routes are model-derived and unverified; they are not field-confirmed houses, usable roads or land access.",
             "Red = proposed route alternative; cyan = existing reference road.",
             "Imagery source, acquisition date and licence: not documented in this package (licence review pending)."]
    fig.text(R+.015, T, "\n".join(sum((textwrap.wrap(t, 44) or [""] for t in notes), [])), fontsize=8.5, va="top", ha="left", linespacing=1.35)
    hs = list(M.legend_handles()); labs = [h_.get_label() for h_ in hs]
    hs.append((Line2D([0], [0], color="#111827", lw=3.6), Line2D([0], [0], color="white", lw=1.6))); labs.append("Village boundary")
    if not sc_in.empty: hs.append(Line2D([0], [0], color="#ed70ff", lw=1.5, linestyle="--")); labs.append("School compound (source layer)")
    fig.legend(hs, labs, handler_map={tuple: HandlerTuple(ndivide=None)}, loc="lower center", ncol=3, fontsize=8.2, frameon=True, bbox_to_anchor=((L+R)/2, .012), framealpha=.98)
    files = []
    for ext, kw in (("png", {"dpi": 600}), ("pdf", {"format": "pdf"})):
        fn = out/f"detail_{slug}.{ext}"; fig.savefig(fn, facecolor="white", **kw); print("Wrote:", fn); files.append(fn)
    plt.close(fig)
    return dict(slug=slug, name=title_name, window=[float(v) for v in bounds], res_m_per_px=float(res), zero_pixel_fraction=zero, in_view_quality=qv,
                routes_in_view=rv, facilities_in_view=[k_ for k_ in key], scale_bar_m=bar, files=[str(f) for f in files])

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--src-dir", default=str(M.ROOT/"results"/"final_output_validation_v4_1"))
    ap.add_argument("--out-dir", default=str(M.ROOT/"results"/"settlement_detail_maps_draft1"))
    ap.add_argument("--select-only", action="store_true", help="print the data-driven selection and planned windows; write nothing")
    a = ap.parse_args(); src, out = Path(a.src_dir), Path(a.out_dir)
    for f in ("candidate_footprints_for_review_v4_1.gpkg", "proposed_routes_with_metrics_v4_1.gpkg", "public_facilities_for_review.gpkg", "final_output_automated_audit_v4_1.json"):
        if not (src/f).exists(): die(f"source file missing: {src/f}")
    if not a.select_only and out.exists() and any(out.iterdir()): die(f"output folder is not empty: {out} (choose a new --out-dir; nothing overwritten)")
    bld = gpd.read_file(src/"candidate_footprints_for_review_v4_1.gpkg", layer="candidate_footprints")
    routes = gpd.read_file(src/"proposed_routes_with_metrics_v4_1.gpkg", layer="network_aware_routes")
    fac = gpd.read_file(src/"public_facilities_for_review.gpkg", layer="facilities")
    roads = M.read_gdf(M.P["roads"]); boundary = M.read_gdf(M.P["boundary"]).geometry.union_all()
    school_comp = M.read_gdf(M.ROOT/"reference"/"school_compounds_utm44n.gpkg", required=False)
    for n_, g_ in (("buildings", bld), ("routes", routes), ("facilities", fac), ("roads", roads)): check_crs(n_, g_)
    if not school_comp.empty: check_crs("school compounds", school_comp)
    audit = json.load(open(src/"final_output_automated_audit_v4_1.json", encoding="utf-8"))
    img_path = M.P["background"]; print("Imagery:", img_path)
    chosen = select(bld, fac)
    for nm, slug, s, st in chosen: print(f"SELECTED {nm}: n={st['n']} centre=({st['centre_E']:.0f},{st['centre_N']:.0f}) window={[round(v) for v in window_for(s)]}")
    if a.select_only: print("select-only: nothing written"); return
    out.mkdir(parents=True, exist_ok=False)
    recs = [draw_one(out, nm, slug, s, st, bld, roads, boundary, school_comp, fac, routes, img_path) for nm, slug, s, st in chosen]
    checks = []
    def chk(name, ok, ev): checks.append(dict(check=name, status="PASS" if ok else "FAIL", evidence=ev))
    chk("source layer counts equal the audit JSON", len(bld) == audit["source_buildings_inside_village"] and len(routes) == audit["targets_with_route_geometry"] and len(fac) == audit["facility_source_records_with_usable_geometry"], dict(buildings=len(bld), routes=len(routes), facilities=len(fac)))
    chk("all vector layers are EPSG:32644", True, "checked before drawing (script stops otherwise)")
    for r in recs:
        png, pdf = Path(r["files"][0]), Path(r["files"][1])
        im = Image.open(png); dpi = tuple(round(x) for x in im.info.get("dpi", (0, 0))); im.load()
        chk(f"{r['slug']} PNG opens, 600 dpi", dpi == (600, 600), dict(size_px=im.size, dpi=dpi, bytes=png.stat().st_size))
        chk(f"{r['slug']} PDF exists and has a PDF header", pdf.exists() and pdf.read_bytes()[:4] == b"%PDF", dict(bytes=pdf.stat().st_size))
        chk(f"{r['slug']} window has no all-zero pixels above 0.5%", r["zero_pixel_fraction"] <= .005, f"{100*r['zero_pixel_fraction']:.3f}%")
    for nm in ("buildings and routes spatially aligned with imagery", "individual footprints and routes distinguishable", "no clipped or overlapping labels, legend readable",
               "imagery georeferencing and licence"):
        checks.append(dict(check=nm, status="NOT VERIFIED", evidence="requires visual review of the rendered images / outside this script"))
    rep = dict(selection=[dict(name=nm, slug=sl, **st) for nm, sl, s, st in chosen], maps=recs, checks=checks, source_dir=str(src))
    (out/"detail_maps_validation.json").write_text(json.dumps(rep, indent=2, default=str), encoding="utf-8")
    print(json.dumps(checks, indent=2, default=str))

if __name__ == "__main__":
    main()
