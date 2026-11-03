#!/usr/bin/env python
"""dk_stageB_maps_v2.py - vector-only publication maps for ONE Stage B run (no imagery: licence/provenance unresolved).
Fig 1: village overview + two zoom insets (footprints, route classes, facility routes, failed targets, boundary, scale bar, north arrow).
Fig 2: zoom comparison, independent least-cost routes vs network-aware routes onto the same goals (roads-only reference).
Writes PNG (300 dpi) + PDF into a NEW folder <run>\\maps_v2 (never overwrites). Model-derived planning alternatives; not verified roads."""
import argparse, json, sys
from pathlib import Path
import geopandas as gpd, matplotlib, numpy as np, pandas as pd
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle

ap = argparse.ArgumentParser()
ap.add_argument("--run-dir", required=True); ap.add_argument("--roads", required=True)
ap.add_argument("--boundary", default=None); ap.add_argument("--buildings", default=None)
ap.add_argument("--inset-a", type=float, nargs=4, default=[261200, 262000, 1958900, 1959600], metavar=("XMIN", "XMAX", "YMIN", "YMAX"))
ap.add_argument("--inset-b", type=float, nargs=4, default=[264350, 264750, 1958050, 1958550], metavar=("XMIN", "XMAX", "YMIN", "YMAX"))
ap.add_argument("--out-name", default="maps_v2")
a = ap.parse_args(); run = Path(a.run_dir); out = run / a.out_name
if out.exists(): print("STOP: exists", out); sys.exit(1)
village = run.parents[3]
cfg = json.loads((run / "config_stageB.json").read_text()); ev = json.loads((run / "evaluation_summary.json").read_text())
ts = pd.read_csv(run / "target_status.csv", dtype={"cand_id": str})
gp = run / "routes.gpkg"
def L(n):
    try: return gpd.read_file(gp, layer=n)
    except Exception: return None
roads = gpd.read_file(a.roads).to_crs(32644)
bpath = Path(a.boundary) if a.boundary else village / "study_area" / "damarakunta_boundary.gpkg"
bnd = gpd.read_file(bpath).to_crs(32644) if bpath.exists() else None
if bnd is None: print("WARNING: boundary file not found, not drawn:", bpath)
bf = Path(a.buildings) if a.buildings else (run / "buildings_perturbed.gpkg" if (run / "buildings_perturbed.gpkg").exists() else village / "results" / "v8_instances" / "buildings_v8_full.gpkg")
bld = gpd.read_file(bf, layer="buildings").to_crs(32644); bld["cand_id"] = bld.cand_id.astype(int).astype(str)
tg = L("targets_houses"); net = L("routes_network_houses"); fac = L("routes_network_facilities"); tf = L("targets_facilities")
ind = L("routes_independent_houses"); ref = L("routes_roads_only_houses")
bld = bld[bld.cand_id.isin(set(ts.cand_id))]
failed = tg[tg.cand_id.astype(str).isin(set(ts[ts.primary_status == "FAILED"].cand_id))] if tg is not None else None
QC = {"PLAUSIBLE": "#1b9e77", "REVIEW": "#d95f02", "UNRESOLVED_MERGE": "#7570b3"}
AC = {"ROAD": "#08306b", "HOUSE_ROUTE": "#6baed6", "FACILITY_ROUTE": "#2171b5"}
a_ = cfg["args"]; title = f"{a_['scenario']} | slope limit {a_['slope_limit_deg']:g}° | cost {a_['cost_scenario']} | {ev['n_house_targets']} house targets, {int((ts.primary_status=='ROUTED').sum())} routed, {int((ts.primary_status=='FAILED').sum())} failed"
if cfg.get("perturbation", {}) and cfg["perturbation"].get("mode", "none") != "none": title += f" | PERTURBATION {cfg['perturbation']['mode']} {cfg['perturbation']['frac']:.0%} seed {cfg['perturbation']['seed']}"
cap = ("Model-derived planning alternatives on a 10 m grid; not verified roads, no legal access or passability implied. Costs are ordinal. Slope derives from a ~30 m DEM interpolated to 10 m (no true 10 m terrain detail).\n"
       "Reference roads: TGRAC layer (may be incomplete). Building footprints are unverified model detections. Provisional settings: C1 built-up cost 3.0, repaired cadastral layer, equal facility weights, penalty classes PLAUSIBLE+REVIEW+UNRESOLVED_MERGE.")
def scalebar(ax, length):
    x0, x1, y0, y1 = ax.get_xlim() + ax.get_ylim(); x, y = x0 + 0.05 * (x1 - x0), y0 + 0.05 * (y1 - y0)
    ax.plot([x, x + length], [y, y], color="k", lw=3, zorder=20, solid_capstyle="butt"); ax.text(x + length / 2, y + 0.012 * (y1 - y0), f"{length:g} m" if length < 1000 else f"{length/1000:g} km", ha="center", fontsize=7, zorder=20)
def north(ax):
    x0, x1, y0, y1 = ax.get_xlim() + ax.get_ylim(); x, y = x0 + 0.95 * (x1 - x0), y0 + 0.82 * (y1 - y0)
    ax.annotate("N", xy=(x, y + 0.1 * (y1 - y0)), xytext=(x, y), ha="center", va="bottom", fontsize=9, arrowprops=dict(arrowstyle="-|>", color="k"), zorder=20)
def frame(ax, box, ttl, fs=8):
    ax.set_xlim(box[0], box[1]); ax.set_ylim(box[2], box[3]); ax.set_aspect("equal"); ax.set_title(ttl, fontsize=fs + 1, loc="left")
    ax.ticklabel_format(style="plain", useOffset=False); ax.tick_params(labelsize=6); ax.set_xlabel("Easting (m), EPSG:32644", fontsize=6); ax.set_ylabel("Northing (m)", fontsize=6)
def draw(ax, box, detail, routes=None, routes_color=None):
    roads.plot(ax=ax, color="#666666", lw=1.0 if not detail else 1.8, zorder=2)
    if bnd is not None: bnd.boundary.plot(ax=ax, color="k", lw=1.0, ls="--", zorder=3)
    rl = routes if routes is not None else net
    if rl is not None and len(rl):
        if routes_color: rl.plot(ax=ax, color=routes_color, lw=1.8 if detail else 0.9, zorder=5)
        else:
            for k, c in AC.items():
                s = rl[rl.attach_class == k]
                if len(s): s.plot(ax=ax, color=c, lw=1.8 if detail else 0.9, zorder=5)
    if fac is not None and len(fac) and routes is None: fac.plot(ax=ax, color="#e31a1c", lw=2.8 if detail else 1.6, zorder=6)
    if detail:
        for q, c in QC.items():
            s = bld[bld.quality_class == q]
            if len(s): s.plot(ax=ax, facecolor=c, edgecolor="k", lw=0.3, alpha=0.8, zorder=4)
    elif tg is not None:
        for q, c in QC.items():
            s = tg[tg.quality_class == q]
            if len(s): s.plot(ax=ax, color=c, markersize=5, zorder=7)
    if tf is not None: tf.plot(ax=ax, color="k", marker="*", markersize=70 if detail else 45, zorder=8)
    if failed is not None and len(failed): failed.plot(ax=ax, color="#e31a1c", marker="X", markersize=40, edgecolor="k", zorder=9)
def legend_handles():
    h = [Patch(facecolor=c, edgecolor="k", label=f"{q} footprint/target") for q, c in QC.items()]
    h += [Line2D([0], [0], color=AC["ROAD"], lw=2, label="House route attached to reference road"), Line2D([0], [0], color=AC["HOUSE_ROUTE"], lw=2, label="House route attached to another house route"),
          Line2D([0], [0], color=AC["FACILITY_ROUTE"], lw=2, label="House route attached to a facility route"), Line2D([0], [0], color="#e31a1c", lw=3, label="Facility route"),
          Line2D([0], [0], color="#666666", lw=2, label="TGRAC reference road"), Line2D([0], [0], marker="*", color="k", ls="", markersize=9, label="Priority facility (identity unverified)"),
          Line2D([0], [0], marker="X", color="#e31a1c", markeredgecolor="k", ls="", label="Target not routed (hard-constraint start cell)")]
    if bnd is not None: h.append(Line2D([0], [0], color="k", ls="--", label="Village boundary"))
    return h
# ---- figure 1
if bnd is not None: bx = bnd.total_bounds; ov_box = (bx[0] - 150, bx[2] + 150, bx[1] - 150, bx[3] + 150)
else: b = tg.total_bounds; ov_box = (b[0] - 400, b[2] + 400, b[1] - 400, b[3] + 400)
fig = plt.figure(figsize=(11, 12)); gs = fig.add_gridspec(2, 2, height_ratios=[1.35, 1], hspace=0.22, wspace=0.18, left=0.07, right=0.97, top=0.94, bottom=0.2)
ax0 = fig.add_subplot(gs[0, :]); draw(ax0, ov_box, False); frame(ax0, ov_box, "Overview: network-aware plan with shared-edge credit")
for nm, bxx, col in (("A", a.inset_a, "#222222"), ("B", a.inset_b, "#222222")):
    ax0.add_patch(Rectangle((bxx[0], bxx[2]), bxx[1] - bxx[0], bxx[3] - bxx[2], fill=False, ec=col, lw=1.2, zorder=15)); ax0.text(bxx[0], bxx[3] + 10, nm, fontsize=9, weight="bold", zorder=15)
scalebar(ax0, 1000); north(ax0)
for k, (nm, bxx) in enumerate((("A", a.inset_a), ("B", a.inset_b))):
    ax = fig.add_subplot(gs[1, k]); draw(ax, bxx, True); frame(ax, bxx, f"Inset {nm}: footprints and routes"); scalebar(ax, 100 if (bxx[1] - bxx[0]) <= 500 else 200)
fig.suptitle(title, fontsize=10, y=0.975); fig.legend(handles=legend_handles(), loc="lower center", ncol=3, fontsize=7, frameon=False, bbox_to_anchor=(0.5, 0.045))
fig.text(0.07, 0.008, cap, fontsize=6, va="bottom", wrap=True)
out.mkdir()
for e in ("png", "pdf"): fig.savefig(out / f"fig1_overview_insets.{e}", dpi=300)
plt.close(fig)
# ---- figure 2
if ind is not None and (ref is not None or net is not None):
    cmp_net = ref if ref is not None else net
    fig, axs = plt.subplots(1, 2, figsize=(12, 6.8)); 
    for ax, lay, t in ((axs[0], ind, "Independent least-cost routes (each target to roads)"), (axs[1], cmp_net, "Network-aware routes (shared-edge credit)" + (", roads-only goal set" if ref is not None else ""))):
        draw(ax, a.inset_a, True, routes=lay, routes_color="#08306b"); frame(ax, a.inset_a, t); scalebar(ax, 100 if (a.inset_a[1] - a.inset_a[0]) <= 600 else 200); north(ax)
    fig.suptitle("Inset A: " + title, fontsize=9)
    fig.legend(handles=legend_handles()[:3] + [Line2D([0], [0], color="#08306b", lw=2, label="Planned route"), Line2D([0], [0], color="#666666", lw=2, label="TGRAC reference road"), Line2D([0], [0], marker="*", color="k", ls="", markersize=9, label="Priority facility")], loc="lower center", ncol=3, fontsize=7, frameon=False, bbox_to_anchor=(0.5, 0.05))
    fig.text(0.02, 0.005, cap, fontsize=5.5, va="bottom", wrap=True); fig.subplots_adjust(bottom=0.2, top=0.92)
    for e in ("png", "pdf"): fig.savefig(out / f"fig2_independent_vs_network_inset_A.{e}", dpi=300)
    plt.close(fig)
print("maps written:", out)
for p in sorted(out.iterdir()): print(f"  {p.stat().st_size:>10,} B  {p.name}")
