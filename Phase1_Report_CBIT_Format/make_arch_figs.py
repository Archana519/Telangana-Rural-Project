"""Draw the nine-stage architecture (fig_arch_v2.png) and the detailed workflow (fig_flow_v2.png) into assets/.

Every box maps to a script or output recorded in DELIVERABLES_DAMARAKUNTA_STAGE_B/01_ARCHITECTURE/DATA_AND_PROCESS_FLOW.md.
Monochrome: dark gray = implemented and run; light gray = implemented, but inputs or evidence unverified or synthetic; white with dashed border = planned, not run.
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Patch

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
os.makedirs(OUT, exist_ok=True)
COL = {"ok": ("#cfcfcf", "#000000"), "part": ("#ececec", "#000000"), "plan": ("#ffffff", "#555555")}   # monochrome: dark gray = implemented and run, light gray = unverified or synthetic, white dashed = planned
plt.rcParams["font.family"] = "DejaVu Serif"


def box(ax, x, y, w, h, title, body="", st="ok", fs=8, tfs=9):
    fc, ec = COL[st]
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.05", fc=fc, ec=ec, lw=1.4, ls="--" if st == "plan" else "-"))
    ax.text(x + w / 2, y + h - 0.07, title, ha="center", va="top", fontsize=tfs, fontweight="bold")
    if body:
        ax.text(x + w / 2, y + h - 0.32, body, ha="center", va="top", fontsize=fs, linespacing=1.25)


def arrow(ax, a, b, ls="-"):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=11, lw=1.2, color="#333333", ls=ls))


def legend(ax, loc):
    ax.legend(bbox_to_anchor=(0.5, -0.045), handles=[Patch(fc=COL["ok"][0], ec=COL["ok"][1], label="Implemented and run"),
                       Patch(fc=COL["part"][0], ec=COL["part"][1], label="Implemented; inputs or evidence unverified / synthetic"),
                       Patch(fc=COL["plan"][0], ec=COL["plan"][1], ls="--", label="Planned, not run")],
              loc=loc, fontsize=7.5, frameon=True)


# ---------------------------------------------------------------- high-level architecture (A4 portrait)
fig, ax = plt.subplots(figsize=(6.3, 9.0)); ax.set_xlim(0, 6.3); ax.set_ylim(-0.9, 8.2); ax.axis("off")
stages = [
    ("1  Input data collection", "Imagery mosaic 0.6 m, TGRAC boundary and roads,\nbuilding candidates, facilities, land cover,\nDEM, cadastral parcels, school compounds", "part"),
    ("2  Geospatial preprocessing", "EPSG:32644, 10 m planning grid 432 x 679,\nboundary mask, land-cover and slope rasters", "ok"),
    ("3  Target preparation", "278 building candidates -> 165 inside -> 163 routing\ntargets (quality classes); 5 facility targets", "part"),
    ("4  Cost surface and constraints", "Ordinal cost C0, slope limit 25 deg, prohibited\ncells, building penalty x4, road goal cells", "ok"),
    ("5  Stage A: candidate routes", "319 house alternatives for 163 targets\n(K = 3 per target, least-cost search)", "ok"),
    ("6  Stage B: network selection", "Facilities first, then houses; marginal cost,\nunique length, shared-edge credit, 2 leaf-reroute passes", "ok"),
    ("7  Evaluation", "Independent / roads-only / length-only / straight-line\nbaselines; C2 ablation; C1 omit and add runs (synthetic)", "part"),
    ("8  GIS outputs and audit", "routes.gpkg, CSV/JSON summaries, manifests with\nSHA-256, acceptance tests, connectivity audit, maps", "ok"),
    ("9  C3 five-village transfer", "Planned only. Blocked until written approval\nof the Damarakunta completion gate", "plan"),
]
h, gap, x0, w = 0.78, 0.16, 0.25, 5.8
y = 8.2 - 0.2 - h
for i, (t, b, s) in enumerate(stages):
    box(ax, x0, y, w, h, t, b, s, fs=7.6, tfs=9.5)
    if i < len(stages) - 1:
        arrow(ax, (x0 + w / 2, y), (x0 + w / 2, y - gap + 0.01), ls=":" if i == 7 else "-")
    y -= h + gap
legend(ax, "lower center")
fig.savefig(os.path.join(OUT, "fig_arch_v2.png"), dpi=220, bbox_inches="tight"); plt.close(fig)

# ---------------------------------------------------------------- detailed workflow (A4 portrait): inputs | scripts | outputs
fig, ax = plt.subplots(figsize=(6.3, 9.6)); ax.set_xlim(0, 6.3); ax.set_ylim(-1.1, 8.6); ax.axis("off")
cols = [(0.05, 1.7, "Inputs"), (1.95, 1.95, "Scripts (run by hand)"), (4.1, 2.15, "Outputs")]
for x, w_, t in cols:
    ax.text(x + w_ / 2, 8.45, t, ha="center", fontsize=10, fontweight="bold")
rowsp = [
    ("TGRAC village query\n(raw JSON)", "save_damarakunta_\nboundary.py", "study_area/\ndamarakunta_boundary.gpkg", "ok"),
    ("Boundary, WorldCover clip,\n~30 m DEM clip", "align_damarakunta_\nterrain.py", "10 m WorldCover, 30 m DEM,\nslope 30 m and 10 m", "part"),
    ("WorldCover 10 m,\nslope 10 m", "create_damarakunta_\ncost_surface.py", "cost surface 2.09-12.0,\nprohibited mask", "ok"),
    ("v8 buildings (278), roads,\nfacilities, cadastral", "dk_stageA_prepare_r3.py", "candidates_master.csv;\nS1 101, merged 62, S2 163", "part"),
    ("Stage A tables, rasters,\nroads, facilities", "dk_stageB_run_v1_x.py\n+ plan_network_v2.py", "routes.gpkg (11 layers),\nselection_summary, route_edges", "ok"),
    ("Run folders", "dk_stageB_c1_*,\ndk_stageB_c2_ablation_*", "C1 reports, C2 ablation tables\n(C1 omit/add are synthetic)", "part"),
    ("Run folders and inputs", "dk_stageB_connectivity_*,\n*_diag_v1 scripts", "connectivity audit v2,\nboundary and road diagnostics", "ok"),
    ("Run folders", "dk_stageB_maps*.py", "maps and maps_v2\n(visual review pending)", "part"),
    ("Five more villages", "not started", "no outputs", "plan"),
]
bh, bg = 0.74, 0.17
y = 8.25 - bh
for i, (a, b, c, s) in enumerate(rowsp):
    box(ax, 0.05, y, 1.7, bh, "", "", s)
    ax.text(0.9, y + bh / 2, a, ha="center", va="center", fontsize=7)
    box(ax, 1.95, y, 1.95, bh, "", "", s)
    ax.text(2.925, y + bh / 2, b, ha="center", va="center", fontsize=6.8, family="DejaVu Sans Mono")
    box(ax, 4.1, y, 2.15, bh, "", "", s)
    ax.text(5.175, y + bh / 2, c, ha="center", va="center", fontsize=7)
    arrow(ax, (1.75, y + bh / 2), (1.95, y + bh / 2)); arrow(ax, (3.9, y + bh / 2), (4.1, y + bh / 2))
    y -= bh + bg
ax.text(3.15, -0.1, "Every Stage B run folder also writes config_stageB.json, inputs_manifest_stageB.csv and outputs_manifest.csv (SHA-256).", ha="center", fontsize=6.6)
legend(ax, "lower center")
fig.savefig(os.path.join(OUT, "fig_flow_v2.png"), dpi=220, bbox_inches="tight"); plt.close(fig)
print("figures written")
