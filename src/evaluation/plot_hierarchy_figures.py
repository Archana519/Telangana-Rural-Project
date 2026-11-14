"""Publication figures for Contribution 3 (300 dpi PNG), drawn only from committed results and the real input layers.

    python -m src.evaluation.plot_hierarchy_figures            # writes paper/figures/ and docs/results/hierarchy_real_run/figures/

Figure A  Level 2 (Damarakunta GP): shared network vs existing roads, hamlet hubs and facilities; local-override comparison
Figure B  footprint-penalty sensitivity (U02): exposure reduction vs network length, mu in the swept set {1, 2, 4, 8, 20, 100}
Figure C  scalability demonstration on PROXY nodes: Level 3 (Markook collector links) and Level 4 (Siddipet backbone: existing-road reuse vs new construction)

Data read: docs/results/hierarchy_real_run/{gp,mandal,district}/*_routes.gpkg, gp_override.csv, *_summary.json, docs/results/U02_penalty_sweep_gp.csv,
plus the road / footprint / boundary layers named in configs/hierarchy_levels.yaml. The only recomputation is the *without-override* routes in Figure A(c).
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import geopandas as gpd  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Circle, Patch  # noqa: E402

RUN = REPO / "docs" / "results" / "hierarchy_real_run"
DPI = 300
C = dict(road="#5f5f5f", local="#c9c9c9", foot="#bdbdbd", route="#d95f02", hub="#1b9e77", school="#7570b3", health="#e7298a",
         office="#66a61e", exist="#1f78b4", new="#e31a1c", bound="#333333", without="#d95f02", with_="#1f78b4", disc="#fdb863")
KIND = {"school": ("^", C["school"], "School"), "healthcare": ("P", C["health"], "Sub-centre"), "panchayat_office": ("s", C["office"], "Panchayat office")}

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 7, "axes.titlesize": 8, "axes.labelsize": 7, "legend.fontsize": 6,
                     "axes.linewidth": 0.6, "xtick.labelsize": 6, "ytick.labelsize": 6, "figure.dpi": 100, "savefig.dpi": DPI})


def _km_axes(ax, title=None, grid=True):
    ax.set_aspect("equal")
    f = matplotlib.ticker.FuncFormatter(lambda v, _: f"{v / 1000:.0f}" if abs(v / 1000 - round(v / 1000)) < 1e-6 else f"{v / 1000:.1f}")
    ax.xaxis.set_major_formatter(f)
    ax.yaxis.set_major_formatter(f)
    ax.set_xlabel("Easting, UTM 44N (km)")
    ax.set_ylabel("Northing (km)")
    if grid:
        ax.grid(True, lw=0.25, color="#dddddd")
    if title:
        ax.set_title(title, loc="left")


def _scalebar(ax, length_m, label):
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    x, y = x0 + 0.04 * (x1 - x0), y0 + 0.05 * (y1 - y0)
    ax.plot([x, x + length_m], [y, y], color="k", lw=1.6, solid_capstyle="butt", zorder=9)
    ax.text(x + length_m / 2, y + 0.012 * (y1 - y0), label, ha="center", va="bottom", fontsize=6, zorder=9)


def _north(ax):
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    x, y = x1 - 0.04 * (x1 - x0), y1 - 0.18 * (y1 - y0)
    ax.annotate("N", xy=(x, y + 0.11 * (y1 - y0)), xytext=(x, y), ha="center", va="bottom", fontsize=7, fontweight="bold",
                arrowprops=dict(arrowstyle="-|>", lw=0.8, color="k"), zorder=9)


def _label(ax, s):
    """Prefix the left title with the panel letter (keeps it clear of tick labels and legends)."""
    ax.set_title(f"{s}  {ax.get_title(loc='left')}", loc="left")


# ----------------------------------------------------------------------------------------------- Figure A
def figure_a(cfg, out: Path):
    from src.routing import data_hooks as dh
    from src.routing.hierarchical_router import build_gp_problem
    gp, rep = dh.load_gp_real(cfg)
    assert gp is not None, rep
    routes = gpd.read_file(RUN / "gp" / "gp_routes.gpkg", layer="routes_shared")
    nodes = gpd.read_file(RUN / "gp" / "gp_routes.gpkg", layer="nodes")
    ov = pd.read_csv(RUN / "gp" / "gp_override.csv")
    summ = json.loads((RUN / "gp" / "gp_summary.json").read_text())

    fig = plt.figure(figsize=(7.16, 6.6))
    gs = fig.add_gridspec(2, 3, height_ratios=[1.35, 1.0], hspace=0.38, wspace=0.42, left=0.15, right=0.985, top=0.95, bottom=0.10)
    ax = fig.add_subplot(gs[0, :])
    gpd.GeoSeries([gp.boundary], crs=cfg["crs"]).plot(ax=ax, facecolor="#f7f7f2", edgecolor=C["bound"], lw=0.7, zorder=0)
    gp.footprints.plot(ax=ax, color=C["foot"], lw=0, zorder=1)
    gp.roads.plot(ax=ax, color=C["road"], lw=0.7, zorder=2)
    routes.plot(ax=ax, color=C["route"], lw=1.5, zorder=4)
    hub = nodes[nodes.kind == "hamlet"]
    ax.scatter(hub.geometry.x, hub.geometry.y, s=14 + 2.2 * hub.weight, c=C["hub"], edgecolor="white", lw=0.5, zorder=6, alpha=0.95)
    for k, (mk, col, _) in KIND.items():
        f = nodes[nodes.kind == k]
        ax.scatter(f.geometry.x, f.geometry.y, marker=mk, s=40, c=col, edgecolor="k", lw=0.5, zorder=7)
    b = gp.boundary.bounds
    ax.set_xlim(b[0] - 150, b[2] + 150)
    ax.set_ylim(b[1] - 150, b[3] + 150)
    _km_axes(ax, "Level 2 - Damarakunta GP: shared network (real inputs, $\\mu$ = 4)")
    _scalebar(ax, 1000, "1 km")
    _north(ax)
    h = [Line2D([], [], color=C["road"], lw=0.9, label="Existing roads (TGRAC, clipped)"), Line2D([], [], color=C["route"], lw=1.8, label="Shared new network"),
         Patch(color=C["foot"], label="Building footprints (v8 candidates)"),
         Line2D([], [], marker="o", ls="", color=C["hub"], mec="white", ms=6, label="Hamlet hub (size = houses)")]
    h += [Line2D([], [], marker=mk, ls="", color=col, mec="k", ms=6, label=lab) for mk, col, lab in KIND.values()]
    ax.legend(handles=h, loc="lower right", ncol=2, frameon=True, framealpha=0.92, edgecolor="#cccccc", borderpad=0.5)
    _label(ax, "(a)")
    ax.text(0.012, 0.985, f"{summ['shared_unique_length_m']:,.0f} m shared vs {summ['independent_unique_length_m']:,.0f} m independent\n"
            f"{summ['n_nodes']} nodes (18 hubs = 163 houses, 5 facilities)", transform=ax.transAxes, ha="left", va="top", fontsize=6.5,
            bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="#cccccc", alpha=0.92))

    # (b) override comparison bars (ordinal route cost)
    axb = fig.add_subplot(gs[1, 0])
    rows = ov[ov.status == "ROUTED"].copy()
    names = {"36181600902": "MPPS\nschool", "36181600903": "ZPHS\nschool", "HEALTH_8734223673": "Sub-\ncentre", "GP_DAMARAKUNTA": "GP HQ\nDamarakunta", "GP_KASHIREDDYPALLY": "GP HQ\nKashireddy-\npally"}
    y = np.arange(len(rows))
    axb.barh(y + 0.18, rows.cost_without, 0.34, color=C["without"], label="without override")
    axb.barh(y - 0.18, rows.cost_with, 0.34, color=C["with_"], label="with override")
    for yi, (_, r) in zip(y, rows.iterrows()):
        axb.text(max(r.cost_without, r.cost_with) + 8, yi, f"-{r.cost_reduction_pct:.0f}%", va="center", fontsize=6)
    axb.set_yticks(y)
    axb.set_yticklabels([names.get(str(n), str(n)) for n in rows.node], fontsize=6)
    axb.invert_yaxis()
    axb.set_xlabel("Facility route cost (ordinal units)")
    axb.set_xlim(0, rows.cost_without.max() * 1.22)
    axb.legend(loc="upper right", frameon=False, fontsize=6)
    axb.set_title("Local penalty override", loc="left")
    _label(axb, "(b)")

    # (c) zoom maps: routes with and without override for the two facilities whose length changes
    prob = build_gp_problem(gp, cfg)
    with_r = prob.solve(mode="shared", use_override=True)
    without_r = prob.solve(mode="shared", use_override=False)
    nodes_by = {n.id: n for n in gp.nodes}
    changed = [n for n in rows.node.astype(str) if abs(without_r.routes[n].length_m - with_r.routes[n].length_m) > 1.0]
    for j, nid in enumerate(changed[:2]):
        a = fig.add_subplot(gs[1, 1 + j])
        n = nodes_by[nid]
        gp.footprints.plot(ax=a, color=C["foot"], lw=0, zorder=1)
        gp.roads.plot(ax=a, color=C["road"], lw=0.9, zorder=2)
        a.add_patch(Circle((n.x, n.y), prob.override_radius_m, fc=C["disc"], ec="none", alpha=0.45, zorder=1.5))
        for res_, col, ls, lab, zz in ((without_r, C["without"], (0, (3, 2)), "without", 4), (with_r, C["with_"], "-", "with", 5)):
            g = res_.routes[nid].geometry
            a.plot(*g.xy, color=col, lw=1.6, ls=ls, zorder=zz)
        mk, col, _ = KIND[n.kind]
        a.scatter([n.x], [n.y], marker=mk, s=45, c=col, edgecolor="k", lw=0.5, zorder=8)
        a.set_xlim(n.x - 75, n.x + 75)
        a.set_ylim(n.y - 60, n.y + 60)
        _km_axes(a, grid=False)
        a.set_xticks([])
        a.set_yticks([])
        a.set_xlabel("")
        a.set_ylabel("")
        dl = without_r.routes[nid].length_m - with_r.routes[nid].length_m
        short = {"36181600903": "ZPHS school", "GP_KASHIREDDYPALLY": "Kashireddypally"}.get(nid, nid)
        a.set_title(f"{short}: -{dl:.1f} m", loc="left", fontsize=6.5)
        _scalebar(a, 50, "50 m")
        _label(a, f"(c{j + 1})")
    fig.legend(handles=[Line2D([], [], color=C["without"], ls=(0, (3, 2)), lw=1.6, label="route without override"),
                        Line2D([], [], color=C["with_"], lw=1.6, label="route with override"),
                        Patch(color=C["disc"], alpha=0.45, label="20 m override disc (radius)"),
                        Patch(color=C["foot"], label="footprints")], loc="lower right", ncol=2, frameon=False, bbox_to_anchor=(0.985, 0.045), fontsize=6.5)
    return fig


# ----------------------------------------------------------------------------------------------- Figure B
def figure_b(out: Path):
    sw = pd.read_csv(REPO / "docs" / "results" / "U02_penalty_sweep_gp.csv")
    fig, (a, b) = plt.subplots(1, 2, figsize=(7.16, 2.9), gridspec_kw=dict(wspace=0.32, left=0.075, right=0.925, top=0.9, bottom=0.17))
    x, y = sw.length_increase_vs_mu1_pct, sw.exposure_reduction_vs_mu1_pct
    a.plot(x, y, "-", color="#999999", lw=1.0, zorder=1)
    a.scatter(x, y, s=28, c="#666666", zorder=2)
    k = sw[sw.mu == 4.0].iloc[0]
    a.scatter([k.length_increase_vs_mu1_pct], [k.exposure_reduction_vs_mu1_pct], s=95, facecolor="none", edgecolor=C["new"], lw=1.4, zorder=3)
    offs = {1.0: (7, 3), 2.0: (7, -10), 4.0: (-38, 5), 8.0: (-12, -13), 20.0: (-12, -13), 100.0: (-14, -13)}
    for _, r in sw.iterrows():
        a.annotate(f"$\\mu$={r.mu:g}", (r.length_increase_vs_mu1_pct, r.exposure_reduction_vs_mu1_pct), textcoords="offset points",
                   xytext=offs.get(r.mu, (5, -9)), fontsize=6.5, fontweight="bold" if r.mu == 4.0 else "normal")
    a.annotate(f"knee: {k.exposure_reduction_vs_mu1_pct:.1f}% less exposure\nfor +{k.length_increase_vs_mu1_pct:.1f}% length", (k.length_increase_vs_mu1_pct, k.exposure_reduction_vs_mu1_pct),
               xytext=(5.6, 32), fontsize=6.5, color=C["new"], arrowprops=dict(arrowstyle="->", color=C["new"], lw=0.8))
    a.set_xlabel("Network length increase vs $\\mu$ = 1 (%)")
    a.set_ylabel("Footprint exposure reduction vs $\\mu$ = 1 (%)")
    a.set_xlim(-0.8, 12.8)
    a.set_ylim(-5, 103)
    a.grid(True, lw=0.3, color="#e3e3e3")
    a.set_title("Trade-off curve", loc="left")
    _label(a, "(a)")
    xs = np.arange(len(sw))
    b.bar(xs, sw.length_in_footprints_m, 0.55, color="#7fb3d5")
    b.set_xticks(xs)
    b.set_xticklabels([f"{m:g}" for m in sw.mu])
    b.set_xlabel("Footprint penalty $\\mu$ (swept set {1, 2, 4, 8, 20, 100}; 16 was not run)")
    b.set_ylabel("Route length inside footprints $E(\\mu)$ (m)", color="#2c6e9b")
    b.set_ylim(0, 125)
    b.axvspan(1.5, 2.5, color=C["new"], alpha=0.08, lw=0)
    ax2 = b.twinx()
    ax2.plot(xs, sw.length_increase_vs_mu1_pct, "o-", color="#b4561a", lw=1.2, ms=4)
    ax2.set_ylim(0, 13)                                  # zero-based: no truncated axis
    ax2.set_ylabel("Network length increase vs $\\mu$ = 1 (%)", color="#b4561a")
    b.set_title("Exposure (bars) and length increase (line)", loc="left")
    _label(b, "(b)")
    return fig


# ----------------------------------------------------------------------------------------------- Figure C
def figure_c(cfg, out: Path):
    from shapely.ops import unary_union
    md, dd = cfg["data"]["mandal"], cfg["data"]["district"]
    classes = cfg["levels"]["mandal"]["collector_road_classes"]
    fig = plt.figure(figsize=(7.16, 4.6))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.0, 1.35], wspace=0.32, left=0.07, right=0.985, top=0.93, bottom=0.33)
    # ---- Level 3
    a = fig.add_subplot(gs[0, 0])
    bnd = gpd.read_file(REPO / md["boundary"])
    roads = gpd.read_file(REPO / md["roads"])
    coll = roads[roads["class"].isin(classes)]
    local = roads[~roads["class"].isin(classes)]
    routes = gpd.read_file(RUN / "mandal" / "mandal_routes.gpkg", layer="routes_shared")
    nodes = gpd.read_file(RUN / "mandal" / "mandal_routes.gpkg", layer="nodes")
    bnd.plot(ax=a, facecolor="#f7f7f2", edgecolor=C["bound"], lw=0.7, zorder=0)
    local.plot(ax=a, color=C["local"], lw=0.35, zorder=1)
    coll.plot(ax=a, color=C["road"], lw=0.9, zorder=2)
    routes.plot(ax=a, color=C["new"], lw=1.6, zorder=4)
    v = nodes[nodes.kind == "gp_hub"]
    a.scatter(v.geometry.x, v.geometry.y, s=14, facecolor="white", edgecolor=C["hub"], lw=1.0, zorder=6)
    hq = nodes[nodes.kind == "mandal_hq"]
    a.scatter(hq.geometry.x, hq.geometry.y, marker="*", s=90, c="#ffd92f", edgecolor="k", lw=0.5, zorder=7)
    b = bnd.total_bounds
    a.set_xlim(b[0] - 400, b[2] + 400)
    a.set_ylim(b[1] - 400, b[3] + 400)
    s3 = json.loads((RUN / "mandal" / "mandal_summary.json").read_text())
    _km_axes(a, "Level 3 - Markook mandal (proxy nodes)")
    _scalebar(a, 5000, "5 km")
    _north(a)
    a.legend(handles=[Line2D([], [], color=C["road"], lw=1.0, label="Collector roads (attachment goals)"), Line2D([], [], color=C["local"], lw=1.0, label="Local roads (cost discount only)"),
                      Line2D([], [], color=C["new"], lw=1.8, label=f"New links ({s3['shared_new_construction_m'] / 1000:.1f} km)"),
                      Line2D([], [], marker="o", ls="", mfc="white", mec=C["hub"], ms=5, label="Village point (proxy GP hub)"),
                      Line2D([], [], marker="*", ls="", mfc="#ffd92f", mec="k", ms=9, label="Mandal HQ (PROXY point)")], loc="upper center",
             bbox_to_anchor=(0.5, -0.15), frameon=False, ncol=1)
    _label(a, "(a)")
    # ---- Level 4
    d = fig.add_subplot(gs[0, 1])
    dist = gpd.read_file(REPO / dd["boundary"])
    mand = gpd.read_file(REPO / dd["mandal_boundaries"])
    droads = gpd.read_file(REPO / dd["roads"])
    chains = gpd.read_file(RUN / "district" / "district_routes.gpkg", layer="routes_shared")
    term = gpd.read_file(RUN / "district" / "district_routes.gpkg", layer="nodes")
    s4 = json.loads((RUN / "district" / "district_summary.json").read_text())
    fine = cfg["levels"]["district"]["fine_resolution_m"]
    net = unary_union(list(chains.geometry))
    buf = droads.geometry.union_all().buffer(1.5 * fine)
    existing, new = net.intersection(buf), net.difference(buf)
    dist.plot(ax=d, facecolor="#f7f7f2", edgecolor=C["bound"], lw=0.8, zorder=0)
    mand.boundary.plot(ax=d, color="#cccccc", lw=0.35, zorder=1)
    droads.plot(ax=d, color=C["local"], lw=0.4, zorder=2)
    gpd.GeoSeries([existing], crs=cfg["crs"]).plot(ax=d, color=C["exist"], lw=1.4, zorder=4)
    gpd.GeoSeries([new], crs=cfg["crs"]).plot(ax=d, color=C["new"], lw=3.2, zorder=5)
    tm = term[term.kind == "mandal_hq"]
    d.scatter(tm.geometry.x, tm.geometry.y, marker="^", s=20, c="white", edgecolor="k", lw=0.7, zorder=7)
    root = term[term.kind == "district_hq"]
    d.scatter(root.geometry.x, root.geometry.y, marker="*", s=110, c="#ffd92f", edgecolor="k", lw=0.6, zorder=8)
    b = dist.total_bounds
    d.set_xlim(b[0] - 1500, b[2] + 1500)
    d.set_ylim(b[1] - 1500, b[3] + 1500)
    share = 100 * s4["shared_on_existing_road_m"] / s4["shared_unique_length_m"]
    _km_axes(d, "Level 4 - Siddipet backbone (proxy terminals)")
    _scalebar(d, 10000, "10 km")
    _north(d)
    d.legend(handles=[Line2D([], [], color=C["local"], lw=1.0, label="Roads (motorway to tertiary, Overture)"),
                      Line2D([], [], color=C["exist"], lw=1.8, label=f"Backbone on existing road: {s4['shared_on_existing_road_m'] / 1000:.1f} km ({share:.1f}%)"),
                      Line2D([], [], color=C["new"], lw=2.6, label=f"New construction: {s4['shared_new_construction_m'] / 1000:.1f} km"),
                      Line2D([], [], marker="^", ls="", mfc="white", mec="k", ms=5, label="Mandal terminal (PROXY point)"),
                      Line2D([], [], marker="*", ls="", mfc="#ffd92f", mec="k", ms=9, label="District HQ (PROXY point)")], loc="upper center",
             bbox_to_anchor=(0.5, -0.15), frameon=False, ncol=1)
    _label(d, "(b)")
    fig.text(0.5, 0.01, "Scalability demonstration on proxy nodes - not planning findings. Roads: Overture Maps (OSM-derived); boundaries: geoBoundaries.",
             ha="center", fontsize=6.5, style="italic", color="#444444")
    return fig


# ----------------------------------------------------------------------------------------------- driver
FIGURES = {"figA_level2_gp_network": ("A", "figure_a"), "figB_penalty_sweep": ("B", "figure_b"), "figC_scalability_levels3_4": ("C", "figure_c")}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", nargs="+", default=[str(REPO / "paper" / "figures"), str(RUN / "figures")])
    a = ap.parse_args(argv)
    from src.routing.hierarchical_router import load_config
    cfg = load_config()
    outs = [Path(o) for o in a.out]
    for o in outs:
        o.mkdir(parents=True, exist_ok=True)
    made = []
    for name, (_, fn) in FIGURES.items():
        fig = {"figure_a": lambda: figure_a(cfg, outs[0]), "figure_b": lambda: figure_b(outs[0]), "figure_c": lambda: figure_c(cfg, outs[0])}[fn]()
        first = outs[0] / f"{name}.png"
        fig.savefig(first, dpi=DPI, facecolor="white")
        plt.close(fig)
        for o in outs[1:]:
            shutil.copy2(first, o / first.name)
        made.append(first)
        print("wrote", first)
    return made


if __name__ == "__main__":
    main()
