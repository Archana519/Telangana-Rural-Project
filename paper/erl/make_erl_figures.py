"""Figures for the ERL manuscript (Phase 1 / Stage B only). Writes 300 dpi PNGs to paper/erl/figures/.

    python paper/erl/make_erl_figures.py

Every plotted number is read from DELIVERABLES_DAMARAKUNTA_STAGE_B (read-only) or from the tracked TGRAC / candidate layers in Siddipet/Damarakunta.
No imagery basemap is used (the imagery licence for derived products is unresolved), so the maps show data layers only.
"""
from __future__ import annotations

import sys
from pathlib import Path

import geopandas as gpd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Patch  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
B = REPO / "DELIVERABLES_DAMARAKUNTA_STAGE_B" / "03_RESULTS_TABLES"
CT = B / "COMPARISON_TABLES"
OUT = Path(__file__).resolve().parent / "figures"
DPI = 300
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8, "axes.titlesize": 8.5, "axes.labelsize": 8, "xtick.labelsize": 7, "ytick.labelsize": 7,
                     "axes.spines.top": False, "axes.spines.right": False, "savefig.facecolor": "white"})
BLUE, ORANGE, GREEN, GREY, RED = "#1f78b4", "#d95f02", "#1b9e77", "#8c8c8c", "#c0392b"


def save(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / f"{name}.png"
    fig.savefig(p, dpi=DPI)
    plt.close(fig)
    print("wrote", p)


# ----------------------------------------------------------------------------------------------------- Fig 1: workflow
def fig_workflow():
    fig, ax = plt.subplots(figsize=(7.0, 3.6))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 54)
    ax.axis("off")

    def box(x, y, w, h, text, fc, fs=6.9):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.3,rounding_size=1.0", fc=fc, ec="#444444", lw=0.8))
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, linespacing=1.3)

    def arrow(x1, y1, x2, y2, head=True):
        ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>" if head else "-", mutation_scale=9, lw=0.9, color="#333333", shrinkA=0, shrinkB=0))

    c1, c2, c3, c4 = "#dbe9f6", "#fde9d4", "#dff2e7", "#eee5f5"
    box(1, 40, 18, 11, "Satellite imagery\n0.6 m, 3 bands", c1)
    box(25, 40, 22, 11, "StrongDINOv2Seg\nDINOv2 ViT-B/14 +\nFPN/ASPP decoder", c1)
    box(53, 40, 22, 11, "Instance extraction\ndistance transform,\nneck test (OpenCV)", c1)
    box(81, 40, 18, 11, "Targets\n163 houses,\n5 facilities", c1)
    for x1, x2 in ((19.5, 24.5), (47.5, 52.5), (75.5, 80.5)):
        arrow(x1, 45.5, x2, 45.5)
    box(1, 21, 28, 12, "Cost surface c(x), 10 m\nland cover + slope\n× footprint penalty μ\n(WorldCover, DEM, TGRAC roads)", c2, fs=6.6)
    box(35, 21, 29, 12, "Two-stage shared-network\nplanner: least-cost alternatives,\nmarginal-cost selection", c3, fs=6.7)
    box(70, 21, 29, 12, "Shared network and metrics:\nunique length, crossings,\nhouses connected", c3, fs=6.7)
    arrow(29.5, 27, 34.5, 27)
    arrow(64.5, 27, 69.5, 27)
    # targets -> planner (elbow)
    arrow(90, 39.5, 90, 36.5, head=False)
    arrow(90, 36.5, 49.5, 36.5, head=False)
    arrow(49.5, 36.5, 49.5, 33.8)
    box(35, 2, 29, 11, "Stress test: omit or add targets\n(random, smallest, merged blobs)", c4, fs=6.7)
    box(70, 2, 29, 11, "Omission impact: length change,\nhouseholds unserved, crossings", c4, fs=6.7)
    arrow(49.5, 20.4, 49.5, 13.6)
    arrow(64.5, 7.5, 69.5, 7.5)
    arrow(84.5, 20.4, 84.5, 13.6)
    save(fig, "fig1_workflow")


# ----------------------------------------------------------------------------------------------------- Fig 2: study area
def fig_study_area():
    bnd = gpd.read_file(REPO / "Siddipet/Damarakunta/study_area/damarakunta_boundary.gpkg").to_crs(32644)
    roads = gpd.read_file(REPO / "Siddipet/Damarakunta/reference/derived/tgrac_road_network_clipped.gpkg").to_crs(32644)
    fac = gpd.read_file(REPO / "Siddipet/Damarakunta/reference/derived/damarakunta_priority_facilities_final_5.gpkg").to_crs(32644)
    bl = gpd.read_file(REPO / "Siddipet/Damarakunta/results/v8_instances/buildings_v8_full.gpkg", layer="buildings").to_crs(32644)
    bl = bl[bl.inside_village.astype(bool)]
    colours = {"PLAUSIBLE": GREEN, "REVIEW": "#e6ab02", "UNRESOLVED_MERGE": RED}
    fig, (a, b) = plt.subplots(1, 2, figsize=(7.2, 3.6), gridspec_kw=dict(width_ratios=[1.25, 1.0], wspace=0.12, left=0.01, right=0.995, top=0.93, bottom=0.2))
    bx0, by0, bx1, by1 = bnd.total_bounds
    for ax, ext, lw in ((a, (bx0 - 150, by0 - 150, bx1 + 150, by1 + 150), 0.7), (b, None, 0.9)):
        bnd.boundary.plot(ax=ax, color="#333333", lw=0.9, zorder=2)
        roads.plot(ax=ax, color="#4a90c2", lw=lw, zorder=3)
        for q, c in colours.items():
            s = bl[bl.quality_class == q]
            if len(s):
                s.plot(ax=ax, fc=c, ec="none" if ax is a else "#333333", lw=0.2, alpha=0.9 if ax is a else 0.75, zorder=4)
        fac.plot(ax=ax, marker="*", color="gold", edgecolor="k", markersize=60 if ax is b else 26, linewidth=0.6, zorder=6)
        ax.set_aspect("equal")
        ax.set_xlabel("")
        ax.set_ylabel("")
        ax.set_xticks([])
        ax.set_yticks([])
        for sp in ax.spines.values():
            sp.set_visible(False)
    a.set_xlim(bx0 - 150, bx1 + 150)
    a.set_ylim(by0 - 150, by1 + 150)
    # zoom window: bounding box of the dense settlement (centroid of facility points +/- margin)
    fx, fy = fac.geometry.x, fac.geometry.y
    zx0, zx1, zy0, zy1 = 260750, 261900, 1959000, 1960000
    zoom = bl[(bl.geometry.centroid.x.between(zx0, zx1)) & (bl.geometry.centroid.y.between(zy0, zy1))]
    cx, cy = zoom.geometry.centroid.x.median(), zoom.geometry.centroid.y.median()
    near = bl[np.hypot(bl.geometry.centroid.x - cx, bl.geometry.centroid.y - cy) < 800]       # the main settlement cluster
    bx0_, by0_, bx1_, by1_ = near.total_bounds
    mx, my = (bx0_ + bx1_) / 2, (by0_ + by1_) / 2
    hw = max((bx1_ - bx0_) / 2, (by1_ - by0_) / 2 / 0.8) + 110                                   # margin; panel aspect 1.25
    zx0, zx1, zy0, zy1 = mx - hw, mx + hw, my - hw * 0.8, my + hw * 0.8
    b.set_xlim(zx0, zx1)
    b.set_ylim(zy0, zy1)
    a.plot([zx0, zx1, zx1, zx0, zx0], [zy0, zy0, zy1, zy1, zy0], color="k", lw=0.9, zorder=7)
    a.set_title("(a) Village boundary, roads, detected footprints", loc="left")
    b.set_title("(b) Main settlement (zoom of box in a)", loc="left")
    # scale bars
    for ax, L, lab in ((a, 1000, "1 km"), (b, 200, "200 m")):
        x0, x1, y0, y1 = ax.get_xlim()[0], ax.get_xlim()[1], ax.get_ylim()[0], ax.get_ylim()[1]
        sx, sy = x0 + 0.05 * (x1 - x0), y0 + 0.05 * (y1 - y0)
        ax.plot([sx, sx + L], [sy, sy], color="k", lw=2, zorder=8)
        ax.text(sx + L / 2, sy + 0.015 * (y1 - y0), lab, ha="center", va="bottom", fontsize=7, zorder=8)
    handles = [Patch(fc=GREEN, label="Footprint: plausible"), Patch(fc="#e6ab02", label="Footprint: review"), Patch(fc=RED, label="Footprint: unresolved merge"),
               Line2D([0], [0], color="#4a90c2", lw=1.2, label="TGRAC road"), Line2D([0], [0], color="#333333", lw=1, label="Village boundary"),
               Line2D([0], [0], marker="*", color="none", markerfacecolor="gold", markeredgecolor="k", markersize=9, label="Facility (5)")]
    fig.legend(handles=handles, loc="lower center", ncol=3, frameon=False, fontsize=7, bbox_to_anchor=(0.5, 0.0))
    save(fig, "fig2_study_area")


# ----------------------------------------------------------------------------------------------------- Fig 3: routing + trade-off
def fig_routing():
    t1 = pd.read_csv(CT / "table1_length_reduction.csv")
    t1 = t1[t1.configuration == "x4 (primary)"].set_index("method")
    pick = [("Independent least-cost routes to the roads", "Independent\nleast-cost routes"), ("Length-only control (shortest distance, same constraints)", "Length-only\ncontrol"),
            ("Roads-only shared reference (houses attach to roads only)", "Roads-only shared\nreference"), ("Two-stage network-aware plan (proposed)", "Two-stage plan\n(proposed)")]
    t6 = pd.read_csv(CT / "table6_obstacle_avoidance.csv")
    fig, (a, b) = plt.subplots(1, 2, figsize=(7.2, 3.1), gridspec_kw=dict(width_ratios=[1.0, 1.0], wspace=0.42, left=0.15, right=0.985, top=0.9, bottom=0.17))
    ys = np.arange(len(pick))[::-1]
    for y, (k, lab) in zip(ys, pick):
        tot, uni = float(t1.loc[k, "total_len_m"]), float(t1.loc[k, "unique_len_m"])
        prop = lab.startswith("Two")
        a.barh(y + 0.19, tot, height=0.34, color="#bdbdbd", ec="k", lw=0.4)
        a.barh(y - 0.19, uni, height=0.34, color=BLUE if prop else "#6a9bc3", ec="k", lw=0.4)
        a.text(tot + 120, y + 0.19, f"{tot:,.0f}", va="center", fontsize=6.5)
        a.text(uni + 120, y - 0.19, f"{uni:,.0f}", va="center", fontsize=6.5, fontweight="bold" if prop else None)
    a.set_yticks(ys)
    a.set_yticklabels([l for _, l in pick], fontsize=6.8)
    a.set_xlim(0, 12300)
    a.set_ylim(-1.15, 3.6)
    a.set_xlabel("Length for 163 houses (m)")
    a.set_title("(a) Total (grey) and unique (blue) length", loc="left")
    a.legend(handles=[Patch(fc="#bdbdbd", ec="k", lw=0.4, label="Total (shared edges counted per route)"), Patch(fc=BLUE, ec="k", lw=0.4, label="Unique (shared edges counted once)")],
             loc="lower right", frameon=False, fontsize=6.3, bbox_to_anchor=(1.02, -0.02))
    a.grid(True, axis="x", lw=0.3, color="#e6e6e6")
    lab = {"x1, no penalty (P3 control)": "μ = 1", "x4, penalty on footprint cells (primary)": "μ = 4", "buffer 7.1 m, penalty x20": "buffer, μ = 20",
           "buffer 7.1 m, penalty x100": "buffer, μ = 100", "buffer 7.1 m, penalty x1000": "buffer, μ = 1000"}
    for r in t6.itertuples():
        l = lab[r.scenario]
        c = BLUE if l == "μ = 4" else (GREY if l == "μ = 1" else GREEN)
        b.scatter(r.house_unique_len_m, r.crossing_len_m, s=46, c=c, edgecolor="k", lw=0.5, zorder=3, marker="o")
        txt = {"μ = 1": (f"μ = 1: {int(r.house_routes_crossing_other_footprints)} routes", (10, 4), "left", "bottom"),
               "μ = 4": (f"μ = 4: {int(r.house_routes_crossing_other_footprints)} routes", (10, -4), "left", "top"),
               "buffer, μ = 20": ("buffered footprints,\nμ = 20, 100, 1000:\n19 routes", (0, 16), "center", "bottom")}.get(l)
        if txt:
            b.annotate(txt[0], (r.house_unique_len_m, r.crossing_len_m), xytext=txt[1], textcoords="offset points", fontsize=6.3, ha=txt[2], va=txt[3])
    b.set_xlim(4400, 6900)
    b.set_ylim(0, 760)
    b.set_xlabel("Unique network length, houses (m)")
    b.set_ylabel("Route length inside other\nhouses' footprints (m)")
    b.grid(True, lw=0.3, color="#e6e6e6")
    b.set_title("(b) Length versus building exposure", loc="left")
    save(fig, "fig3_routing")


# ----------------------------------------------------------------------------------------------------- Fig 4: omission
def fig_omission():
    t = pd.read_csv(CT / "table4_c1_sensitivity.csv").set_index("perturbation")
    base = float(t.loc["baseline (no perturbation)", "unique_len_m_mean"])
    base_per = float(t.loc["baseline (no perturbation)", "unique_len_per_routed_m_mean"])
    fam = {"omit 10%": ("Random 10 %", BLUE, "o"), "omit 20%": ("Random 20 %", BLUE, "o"), "omit smallest 10%": ("Smallest 10 %", ORANGE, "s"),
           "omit smallest 25%": ("Smallest 25 %", ORANGE, "s"), "omit merged blobs": ("Merged blobs", "#7570b3", "D"),
           "add 10%": ("Add 10 %", GREEN, "^"), "add 20%": ("Add 20 %", GREEN, "^")}
    rows = []
    for k, (lab, col, mk) in fam.items():
        r = t.loc[k]
        rows.append(dict(key=k, label=lab, col=col, mk=mk, U=max(0.0, 163 - float(r.house_targets_routed_mean)), d=100 * (r.unique_len_m_mean - base) / base,
                         lo=100 * (r.unique_len_m_min - base) / base, hi=100 * (r.unique_len_m_max - base) / base, per=float(r.unique_len_per_routed_m_mean), n=int(r.runs)))
    d = pd.DataFrame(rows)
    fig, (a, b) = plt.subplots(1, 2, figsize=(7.2, 3.2), gridspec_kw=dict(width_ratios=[1.12, 1.0], wspace=0.62, left=0.075, right=0.985, top=0.9, bottom=0.17))
    a.axhline(0, color="#888888", lw=0.7)
    off = {"omit 10%": 8, "omit smallest 10%": 2, "omit 20%": -4, "omit smallest 25%": -10, "omit merged blobs": -16}
    for r in d.itertuples():
        if r.n > 1:
            a.errorbar(r.U, r.d, yerr=[[r.d - r.lo], [r.hi - r.d]], fmt="none", ecolor=r.col, elinewidth=1, capsize=2.5, alpha=0.85, zorder=2)
        a.scatter(r.U, r.d, marker=r.mk, s=34, c=r.col, edgecolor="k", lw=0.5, zorder=3)
        if r.key.startswith("add"):
            a.annotate(f"{r.label}: {r.d:+.1f}%, U = 0", (r.U, r.d), xytext=(r.U + 5, r.d), ha="left", va="center", fontsize=6)
        else:
            a.annotate(f"{r.label}: {r.d:+.1f}%, U = {int(round(r.U))}", (r.U, r.d), xytext=(50, off[r.key]), ha="left", va="center", fontsize=6,
                       arrowprops=dict(arrowstyle="-", lw=0.5, color="#777777", shrinkA=1, shrinkB=3, relpos=(0, 0.5)))
    a.set_xlim(-4, 84)
    a.set_ylim(-38, 22)
    a.set_xlabel("Households left without a route, $U$ (of 163)")
    a.set_ylabel("Unique network length change (%)")
    a.grid(True, lw=0.3, color="#e6e6e6")
    a.set_title(f"(a) Shorter plan, more households lost\n(baseline {base:,.0f} m)", loc="left")
    ys = np.arange(len(d))[::-1]
    b.axvline(base_per, color="#666666", ls=(0, (4, 3)), lw=0.9)
    for y, r in zip(ys, d.itertuples()):
        b.hlines(y, base_per, r.per, color=r.col, lw=1.2, alpha=0.6)
        b.scatter(r.per, y, marker=r.mk, s=34, c=r.col, edgecolor="k", lw=0.5, zorder=3)
        right = r.per >= base_per
        b.text(r.per + (0.3 if right else -0.3), y, f"{r.per:.1f}", ha="left" if right else "right", va="center", fontsize=6.5)
    b.set_yticks(ys)
    b.set_yticklabels(d.label, fontsize=6.5)
    b.set_xlim(29.5, 37.4)
    b.set_ylim(-0.7, len(d) + 0.15)
    b.set_xlabel("Unique length per routed target (m)")
    b.text(base_per + 0.12, len(d) - 0.3, f"baseline {base_per:.1f} m", fontsize=6.5, color="#555555", va="center")
    b.grid(True, axis="x", lw=0.3, color="#e6e6e6")
    b.set_title("(b) Length per routed target", loc="left")
    save(fig, "fig4_omission")


def main():
    fig_workflow()
    fig_study_area()
    fig_routing()
    fig_omission()


if __name__ == "__main__":
    main()
