"""make_charts.py - statistical graphs for the dissertation (300 dpi PNG) from the generated tables and one Stage B run.

  chart1_network_lengths.png            independent versus shared network lengths (and the duplicated length)
  chart2_material_savings.png           material quantities for each length and the saving (assumption-driven)
  chart3_cost_distribution.png          cost at the assumed Rs 75 lakh/km: independent, shared, saving (illustrative)
  chart4_spatial_accessibility.png      attachment classes, route-length and distance-to-road distributions, facility accessibility
  chart5_obstacle_avoidance_tradeoff.png  length versus building crossings for the x1, x4 and buffer scenarios

Everything is read from files; nothing is typed in. Cost and material charts are labelled illustrative because they rest on assumptions
(inputs/economic_assumptions.json), not project data. The x4 and x1 configurations are never mixed in one bar group without a label.
usage: python src/reporting/make_charts.py --stageb-root <.../stageB> --comparison outputs/final_comparison --out outputs/final_comparison/charts
"""
import sys as _sys
from pathlib import Path as _P
_sys.path.insert(0, str(_P(__file__).resolve().parents[1]))
import scenario_names as SN

import argparse
import json
from pathlib import Path

import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
V = ROOT / "Siddipet" / "Damarakunta"
BLUE, ORANGE, GREEN, RED, GREY, SKY = "#0072B2", "#E69F00", "#009E73", "#D55E00", "#7f7f7f", "#56B4E9"
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False, "axes.titlesize": 10, "axes.titleweight": "bold"})


def save(fig, out, name, note):
    fig.text(0.5, 0.005, note, ha="center", fontsize=6.5, color="#444444")
    fig.savefig(out / name, dpi=300, bbox_inches="tight"); plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stageb-root", required=True)
    ap.add_argument("--comparison", default=str(ROOT / "outputs" / "final_comparison"))
    ap.add_argument("--out", default=str(ROOT / "outputs" / "final_comparison" / "charts"))
    a = ap.parse_args()
    cmp_, out, sb = Path(a.comparison), Path(a.out), Path(a.stageb_root)
    out.mkdir(parents=True, exist_ok=True)
    t1 = pd.read_csv(cmp_ / "table1_length_reduction.csv")
    t5 = pd.read_csv(cmp_ / "table5_economic_material_impact.csv")
    t5b = pd.read_csv(cmp_ / "table5b_material_quantities.csv")
    t6 = pd.read_csv(cmp_ / "table6_obstacle_avoidance.csv")
    ass = json.load(open(ROOT / "inputs" / "economic_assumptions.json", encoding="utf-8"))
    p4 = t1[t1.configuration == "x4 (primary)"].set_index("method")
    ind_tot = p4.loc["Independent least-cost routes to the roads", "total_len_m"]
    ind_uni = p4.loc["Independent least-cost routes to the roads", "unique_len_m"]
    roads_only = p4.loc["Roads-only shared reference (houses attach to roads only)", "unique_len_m"]
    prop = p4.loc["Two-stage network-aware plan (proposed)", "unique_len_m"]
    av = t6[t6.run == SN.AVOID]
    avl = float(av.house_unique_len_m.iloc[0]) if len(av) else np.nan

    # ------------------------------------------------------------ chart 1
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.4), gridspec_kw=dict(width_ratios=[1.35, 1]))
    names = ["Independent\n(sum of routes)", "Independent\n(unique edges)", "Roads-only\nreference", "Shared, x4\n(proposed)", "Shared, x100\n(avoids buildings)"]
    vals = [ind_tot, ind_uni, roads_only, prop, avl]
    cols = [GREY, GREY, SKY, BLUE, GREEN]
    b = ax[0].bar(names, vals, color=cols, edgecolor="k", lw=0.5)
    for r, v in zip(b, vals):
        ax[0].text(r.get_x() + r.get_width() / 2, v + 120, "%.0f m" % v if np.isfinite(v) else "", ha="center", fontsize=8)
    ax[0].set_ylabel("length of house routes (m)"); ax[0].set_ylim(0, max(v for v in vals if np.isfinite(v)) * 1.15)
    ax[0].set_title("House-route length, 163 houses")
    ax[0].tick_params(axis="x", labelsize=7)
    ax[0].annotate("", xy=(3, prop), xytext=(1, ind_uni), arrowprops=dict(arrowstyle="->", color=RED, lw=1.5))
    ax[0].text(2.0, ind_uni + 450, "saving %.0f m (%.1f%%)\nvs unique independent" % (ind_uni - prop, 100 * (ind_uni - prop) / ind_uni), ha="center", color=RED, fontsize=8, fontweight="bold")
    dup = ind_tot - ind_uni
    ax[1].bar(["Independent"], [ind_uni], color=GREY, edgecolor="k", lw=0.5, label="unique edges")
    ax[1].bar(["Independent"], [dup], bottom=[ind_uni], color="#d9d9d9", edgecolor="k", lw=0.5, hatch="//", label="edges counted again (shared by several houses)")
    ax[1].bar(["Shared (x4)"], [prop], color=BLUE, edgecolor="k", lw=0.5)
    ax[1].text(0, ind_tot + 100, "%.0f m" % ind_tot, ha="center"); ax[1].text(1, prop + 100, "%.0f m" % prop, ha="center")
    ax[1].set_ylim(0, ind_tot * 1.35); ax[1].legend(fontsize=7, loc="upper right", frameon=False); ax[1].set_title("Why the sum overstates the saving")
    fig.suptitle("Chart 1. Comparative network lengths: independent routes versus the shared network", fontsize=11, fontweight="bold")
    save(fig, out, "chart1_network_lengths.png", "Lengths on a 10 m planning grid. The fair baseline is the unique independent length; counting every house route in full double-counts shared edges. Planning alternatives, not verified roads.")

    # ------------------------------------------------------------ chart 2
    m = t5b.set_index("length")
    A_, P_, B_ = m.loc["Independent routes, unique length (A)"], m.loc["Proposed shared network"], m.loc["Independent routes, total length (B)"]
    items = [("earthwork_m3", "Earthwork (m3)"), ("aggregate_loose_m3", "Aggregate, base and surfacing (m3, loose)"), ("gsb_subbase_loose_m3", "Sub-base material (m3, loose)"), ("bitumen_t", "Bitumen (t)")]
    fig, axs = plt.subplots(1, 4, figsize=(13, 4.0))
    for ax_, (k, lab) in zip(axs, items):
        ax_.bar(["Independent\n(unique)", "Shared\n(proposed)"], [A_[k], P_[k]], color=[GREY, BLUE], edgecolor="k", lw=0.5)
        ax_.bar(["Shared\n(proposed)"], [A_[k] - P_[k]], bottom=[P_[k]], color=GREEN, edgecolor="k", lw=0.5, hatch="//")
        ax_.text(1, A_[k] * 1.02, "saved\n%.0f" % (A_[k] - P_[k]) if k != "bitumen_t" else "saved\n%.1f" % (A_[k] - P_[k]), ha="center", color=GREEN, fontsize=8, fontweight="bold")
        ax_.set_title(lab, fontsize=8); ax_.set_ylim(0, A_[k] * 1.25); ax_.tick_params(axis="x", labelsize=7)
    fig.suptitle("Chart 2. Material conservation from sharing routes (illustrative; assumed cross-section)", fontsize=11, fontweight="bold")
    p_ = ass["pavement"]
    save(fig, out, "chart2_material_savings.png", "Assumed section: %.2f m carriageway, %.0f mm sub-base, %.0f mm WBM, %.0f mm bituminous surface, formation %.1f m, %.2f m earthwork depth. Not project data; replace with a design section and State SOR." % (
        p_["carriageway_width_m"], 1000 * p_["sub_base_gsb_thickness_m"], 1000 * p_["wbm_base_thickness_m"], 1000 * p_["bituminous_surface_thickness_m"], p_["formation_width_m"], p_["earthwork_average_depth_m"]))

    # ------------------------------------------------------------ chart 3
    ra = t5.iloc[0]
    rate = ass["rate_lakh_per_km"]
    fig, ax = plt.subplots(1, 4, figsize=(16, 4.3), gridspec_kw=dict(width_ratios=[1.1, 0.9, 1.0, 1.0]))
    cost_ind, cost_prop, sav = ra.baseline_cost_central_Rs_lakh, ra.proposed_cost_central_Rs_lakh, ra.cost_saving_central_Rs_lakh
    ax[0].bar(["Independent\n(unique length)", "Shared network\n(proposed)"], [cost_ind, cost_prop], color=[GREY, BLUE], edgecolor="k", lw=0.5)
    ax[0].bar(["Shared network\n(proposed)"], [sav], bottom=[cost_prop], color=GREEN, edgecolor="k", lw=0.5, hatch="//")
    ax[0].errorbar([0, 1], [cost_ind, cost_prop], yerr=[[cost_ind - cost_ind * rate["low"] / rate["central"]] * 2, [cost_ind * rate["high"] / rate["central"] - cost_ind, cost_prop * rate["high"] / rate["central"] - cost_prop]], fmt="none", ecolor="k", capsize=3, lw=0.8)
    ax[0].text(1, cost_ind * 1.03, "saving Rs %.0f lakh" % sav, ha="center", color=GREEN, fontweight="bold", fontsize=8)
    ax[0].set_ylabel("Rs lakh at Rs %.0f lakh/km" % rate["central"]); ax[0].set_title("Cost of the house routes"); ax[0].set_ylim(0, cost_ind * 1.2)
    wedges, _t, _a = ax[1].pie([cost_prop, sav], colors=[BLUE, GREEN], autopct=lambda v: "%.1f%%" % v, startangle=90, wedgeprops=dict(edgecolor="w"), textprops=dict(fontsize=8, color="w", fontweight="bold"))
    ax[1].legend(wedges, ["cost of shared network", "saved vs independent"], loc="lower center", bbox_to_anchor=(0.5, -0.12), fontsize=7.5, frameon=False)
    ax[1].set_title("Share of the independent cost")
    rates = [rate["low"], rate["central"], rate["high"]]
    sv = [ra.cost_saving_low_Rs_lakh, ra.cost_saving_central_Rs_lakh, ra.cost_saving_high_Rs_lakh]
    ax[2].bar(["Rs %.0f" % r for r in rates], sv, color=[SKY, GREEN, SKY], edgecolor="k", lw=0.5)
    for i, v in enumerate(sv):
        ax[2].text(i, v + 2, "%.0f" % v, ha="center", fontsize=8)
    ax[2].set_xlabel("assumed rate (lakh per km)"); ax[2].set_ylabel("saving (Rs lakh)"); ax[2].set_title("Sensitivity of the saving to the rate")
    cx4, cav = prop / 1000 * rate["central"], (avl / 1000 * rate["central"]) if np.isfinite(avl) else np.nan
    ax[3].bar(["Shared, x4", "Shared, building-\navoiding (x100)"], [cx4, cav], color=[BLUE, GREEN], edgecolor="k", lw=0.5)
    for i_, v_ in enumerate([cx4, cav]):
        ax[3].text(i_, v_ + 8, "%.0f" % v_, ha="center", fontsize=8)
    ax[3].set_ylabel("Rs lakh at Rs %.0f lakh/km" % rate["central"]); ax[3].set_title("Price of keeping routes out of footprints")
    ax[3].text(0.5, max(cx4, cav) * 1.12, "+Rs %.0f lakh for avoiding buildings" % (cav - cx4), ha="center", color=RED, fontweight="bold", fontsize=8); ax[3].set_ylim(0, max(cx4, cav) * 1.25)
    fig.suptitle("Chart 3. Cost distribution at the assumed PMGSY-based rate (illustrative)", fontsize=11, fontweight="bold")
    save(fig, out, "chart3_cost_distribution.png", "Rs %.0f lakh/km is a rate supplied by the project owner and not verified; error bars are +/-20%%. Based on unique-length saving of %.0f m (%.1f%%); the double-counted total minus the shared network (%.2f km) would overstate it about %.1f times. Not an engineering estimate." % (
        rate["central"], ra.length_saving_m, ra.length_saving_pct, t5.iloc[1].length_saving_m / 1000, t5.iloc[1].length_saving_m / ra.length_saving_m))

    # ------------------------------------------------------------ chart 4
    prim = sb / SN.PRIMARY
    ev = json.load(open(prim / "evaluation_summary.json", encoding="utf-8"))
    st = pd.read_csv(prim / "target_status.csv", dtype={"planner_key": str})
    fs = pd.read_csv(prim / "facility_status.csv", dtype={"facility_id": str})
    sel = pd.read_csv(prim / "selection_summary.csv", dtype={"target_id": str})
    houses = st[["planner_key", "x", "y", "dist_to_road_m", "stratum"]].copy()
    fig, axs = plt.subplots(2, 2, figsize=(11.5, 8.2))
    cls = ev["attach_class_counts_primary_houses"]
    axs[0, 0].pie(list(cls.values()), labels=["%s\n%d" % (k.replace("_", " ").lower(), v) for k, v in cls.items()], colors=[SKY, ORANGE, RED][:len(cls)], autopct="%1.0f%%", startangle=90,
                  wedgeprops=dict(edgecolor="w"), textprops=dict(fontsize=8))
    axs[0, 0].set_title("What each house route ends on (163 houses)")
    hl = sel[sel.scope == "house_phase"].len_m
    axs[0, 1].hist(hl, bins=np.arange(0, hl.max() + 10, 10), color=BLUE, edgecolor="w")
    axs[0, 1].axvline(hl.median(), color=RED, ls="--"); axs[0, 1].text(hl.median() + 3, axs[0, 1].get_ylim()[1] * 0.9, "median %.0f m" % hl.median(), color=RED, fontsize=8)
    axs[0, 1].set_xlabel("route length (m)"); axs[0, 1].set_ylabel("houses"); axs[0, 1].set_title("Length of each house route (shared network)")
    bins = [0, 10, 20, 1e9]; labs = ["<= 10 m", "10-20 m", "> 20 m"]
    cnt = pd.cut(houses.dist_to_road_m.astype(float), bins=bins, labels=labs, include_lowest=True).value_counts().reindex(labs)
    axs[1, 0].bar(labs, cnt.values, color=[GREEN, ORANGE, RED], edgecolor="k", lw=0.5)
    for i, v in enumerate(cnt.values):
        axs[1, 0].text(i, v + 1, str(v), ha="center", fontsize=8)
    axs[1, 0].set_xlabel("distance from the house to the nearest TGRAC road"); axs[1, 0].set_ylabel("houses"); axs[1, 0].set_title("Spatial distribution: how far houses are from an existing road")
    fac = gpd.read_file(SN.FAC_LAYER, layer="priority_facilities")
    hx, hy = houses.x.astype(float).values, houses.y.astype(float).values
    names, c250, c500, c1000 = [], [], [], []
    for r in fac.itertuples():
        d = np.hypot(hx - r.geometry.x, hy - r.geometry.y)
        _l = fs[fs.facility_id == str(r.facility_id)].len_m
        names.append(r.facility_name.replace(" (Damarakunta revenue village)", "").replace(", ", "\n").replace(" Gram Panchayat HQ", "\nGram Panchayat HQ") + ("\nroute %.0f m" % float(_l.iloc[0]) if len(_l) else ""))
        c250.append(int((d <= 250).sum())); c500.append(int((d <= 500).sum())); c1000.append(int((d <= 1000).sum()))
    x = np.arange(len(names)); w = 0.26
    axs[1, 1].bar(x - w, c250, w, label="within 250 m", color=GREEN, edgecolor="k", lw=0.4)
    axs[1, 1].bar(x, c500, w, label="within 500 m", color=SKY, edgecolor="k", lw=0.4)
    axs[1, 1].bar(x + w, c1000, w, label="within 1 km", color=BLUE, edgecolor="k", lw=0.4)
    axs[1, 1].set_xticks(x); axs[1, 1].set_xticklabels(names, fontsize=7); axs[1, 1].set_ylabel("house targets (straight line)"); axs[1, 1].legend(fontsize=7, frameon=False)
    axs[1, 1].set_title("Facility accessibility: houses near each facility")
    axs[1, 1].set_ylim(0, max(c1000) * 1.3)
    fig.suptitle("Chart 4. Spatial distribution and facility accessibility (primary x4 run)", fontsize=11, fontweight="bold")
    fig.tight_layout(rect=(0, 0.02, 1, 0.97))
    save(fig, out, "chart4_spatial_accessibility.png", "House targets are automatic detections, not a census. Facility counts are straight-line distances from the five facilities in the final layer (anganwadi excluded, two Gram Panchayat HQ points added; inputs/EXCLUSIONS.md, inputs/ADMIN_UTILITIES.md). Planning results, not field-verified.")

    # ------------------------------------------------------------ chart 5
    if len(t6):
        d6 = t6.copy()
        order = ["x1, no penalty (P3 control)", "x4, penalty on footprint cells (primary)"] + [s for s in d6.scenario if s.startswith("buffer")]
        d6 = d6.set_index("scenario").reindex([o for o in order if o in set(d6.scenario)]).reset_index()
        fig, ax = plt.subplots(1, 2, figsize=(12, 4.4))
        cl = [GREY, BLUE] + [GREEN] * (len(d6) - 2)
        short = [s.replace(", penalty on footprint cells (primary)", " (primary)").replace(", no penalty (P3 control)", " (control)").replace("buffer 7.1 m, penalty ", "buffer, ") for s in d6.scenario]
        b = ax[0].bar(short, d6.house_unique_len_m, color=cl, edgecolor="k", lw=0.5)
        for r_, v in zip(b, d6.house_unique_len_m):
            ax[0].text(r_.get_x() + r_.get_width() / 2, v + 60, "%.0f" % v, ha="center", fontsize=8)
        ax[0].set_ylabel("unique house-route length (m)"); ax[0].set_title("Length of the shared network"); ax[0].tick_params(axis="x", labelsize=7, rotation=15)
        ax[0].set_ylim(0, d6.house_unique_len_m.max() * 1.15)
        ex = d6.crossing_only_in_first_20m.replace("", np.nan).astype(float).fillna(0)
        lt = d6.crossing_beyond_first_20m.replace("", np.nan).astype(float).fillna(0)
        ax[1].bar(short, ex, color=ORANGE, edgecolor="k", lw=0.5, label="crossing only in the first 20 m (leaving a cluster of touching buildings)")
        ax[1].bar(short, lt, bottom=ex, color=RED, edgecolor="k", lw=0.5, label="crossing further along the route")
        for i, (e_, l_, n_) in enumerate(zip(ex, lt, d6.house_routes_crossing_other_footprints)):
            ax[1].text(i, e_ + l_ + 1, "%d routes\n%.0f m" % (n_, d6.crossing_len_m.iloc[i]), ha="center", fontsize=7)
        ax[1].set_ylabel("house routes crossing another footprint"); ax[1].set_title("Routes still crossing other buildings"); ax[1].legend(fontsize=6.5, frameon=False, loc="upper right")
        ax[1].tick_params(axis="x", labelsize=7, rotation=15); ax[1].set_ylim(0, max(60, (ex + lt).max() * 1.3))
        fig.suptitle("Chart 5. Keeping routes out of building footprints: price and limit", fontsize=11, fontweight="bold")
        save(fig, out, "chart5_obstacle_avoidance_tradeoff.png", "Buffer scenarios hand the planner footprints buffered by 7.1 m with a large penalty; hard blocking failed (every house point lies in its own blocked cell). The effect saturates by x20. Footprints are model detections.")
    print("charts written to", out)


if __name__ == "__main__":
    main()
