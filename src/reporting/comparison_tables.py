"""comparison_tables.py - baseline versus proposed, connectivity and constraints, C2 ablation and C1 sensitivity, from one Stage B run folder.

Reads only <stageB root>/<run>/evaluation_summary.json, config_stageB.json, impact_flags.csv, connectivity_checks.csv, target_status.csv and
(optionally) outputs/connectivity/route_end_line_connectivity.csv. Writes CSV and Markdown tables to --out. Configurations are never mixed:
the primary (building penalty x4) and the P3 control (x1) have separate blocks, and every baseline is the one planned in the same run.
Lengths are metres on the 10 m grid; costs are ordinal planning units, not rupees. Omit/add runs are synthetic probes, not measured detector error.

usage: python src/reporting/comparison_tables.py --stageb-root <.../stageB> --out outputs/final_comparison
"""
import sys as _sys
from pathlib import Path as _P
_sys.path.insert(0, str(_P(__file__).resolve().parents[1]))
import scenario_names as SN

import argparse, csv, json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]


def load(run):
    ev = json.load(open(run / "evaluation_summary.json", encoding="utf-8"))
    cfg = json.load(open(run / "config_stageB.json", encoding="utf-8"))["args"]
    imp = pd.read_csv(run / "impact_flags.csv")
    return ev, cfg, imp


def cross(imp, st, kind=None):
    g = imp[imp.set == st]
    if kind:
        g = g[g.kind == kind]
    n = g.n_other_polygons_crossed.fillna(0) > 0
    ln = g.len_other_PLAUSIBLE_m.fillna(0) + g.len_other_REVIEW_m.fillna(0) + g.len_other_UNRESOLVED_MERGE_m.fillna(0)
    return int(n.sum()), round(float(ln.sum()), 1)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stageb-root", required=True)
    ap.add_argument("--out", default=str(ROOT / "outputs" / "final_comparison"))
    ap.add_argument("--connectivity", default=str(ROOT / "outputs" / "connectivity" / "route_end_line_connectivity.csv"))
    a = ap.parse_args()
    root, out = Path(a.stageb_root), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    runs = {d.name: d for d in sorted(root.iterdir()) if d.is_dir() and (d / "evaluation_summary.json").exists() and not d.name.endswith("_rep")}   # _rep = reproducibility reruns, not extra seeds
    prim = {"x4 (primary)": SN.PRIMARY, "x1 (P3 control)": SN.P3}

    # ---------------------------------------------------------------- table 1: length reduction
    T1 = []
    for cfgname, rk in prim.items():
        if rk not in runs:
            continue
        ev, cfg, imp = load(runs[rk])
        ind = ev["houses_independent_baseline"]
        rows = [("Straight line (no terrain, 2 targets infeasible)", ev["houses_straight_line"]["total_len_m"], None, "straight_line_baseline"),
                ("Independent least-cost routes to the roads", ind["total_len_m"], ind["unique_len_m"], "independent_baseline"),
                ("Length-only control (shortest distance, same constraints)", ev["houses_length_only"]["total_len_m"], ev["houses_length_only"]["unique_len_m"], "length_only_baseline"),
                ("Roads-only shared reference (houses attach to roads only)", ev["houses_roads_only_reference"]["total_len_m"], ev["houses_roads_only_reference"]["unique_len_m"], "roads_only_reference"),
                ("Two-stage network-aware plan (proposed)", ev["houses_primary"]["total_len_m"], ev["houses_primary"]["unique_len_m"], "network_primary")]
        for name, tot, uni, st in rows:
            nc, ln = cross(imp, st, "house")
            T1.append(dict(configuration=cfgname, houses=ev["n_house_targets"], method=name, total_len_m=round(tot, 1), unique_len_m=None if uni is None else round(uni, 1),
                           duplicated_len_m=None if uni is None else round(tot - uni, 1),
                           reduction_vs_independent_unique_m=None if uni is None else round(ind["unique_len_m"] - uni, 1),
                           reduction_vs_independent_unique_pct=None if uni is None else round(100 * (ind["unique_len_m"] - uni) / ind["unique_len_m"], 1),
                           routes_crossing_other_footprints=nc, len_in_other_footprints_m=ln))
        T1.append(dict(configuration=cfgname, houses=ev["n_house_targets"], method="Facilities (%d), network-aware" % ev["n_facility_targets"], total_len_m=round(ev["facilities_primary"]["total_len_m"], 1),
                       unique_len_m=round(ev["facilities_primary"]["unique_len_m"], 1)))
        T1.append(dict(configuration=cfgname, houses=ev["n_house_targets"], method="Houses + facilities, network-aware (combined unique)", total_len_m=round(ev["combined_primary"]["total_len_m"], 1),
                       unique_len_m=round(ev["combined_primary"]["unique_len_m"], 1),
                       reduction_vs_independent_unique_m=round(ev["combined_independent_baseline"]["unique_len_m"] - ev["combined_primary"]["unique_len_m"], 1),
                       reduction_vs_independent_unique_pct=round(100 * (ev["combined_independent_baseline"]["unique_len_m"] - ev["combined_primary"]["unique_len_m"]) / ev["combined_independent_baseline"]["unique_len_m"], 1)))
    D1 = pd.DataFrame(T1)
    D1.to_csv(out / "table1_length_reduction.csv", index=False)

    # ---------------------------------------------------------------- table 2: C2 ablation
    T2 = []
    for name, d in runs.items():
        ev, cfg, _ = load(d)
        if "_final" in name and cfg.get("perturb", "none") == "none" and cfg["building_mult"] == 4.0 and cfg["slope_limit_deg"] == 25.0 and cfg["scenario"] == "S2" and cfg["cost_scenario"] == "C0" and cfg.get("avoid_buildings", "off") == "off" and cfg["building_quality"] == "PLAUSIBLE,REVIEW,UNRESOLVED_MERGE":
            T2.append(dict(run=name, alternatives_per_target_K=cfg["k"], leaf_reroute_passes=cfg["passes"], unique_len_m=round(ev["houses_primary"]["unique_len_m"], 3),
                           total_len_m=round(ev["houses_primary"]["total_len_m"], 3), saving_vs_independent_pct=round(100 * (ev["houses_independent_baseline"]["unique_len_m"] - ev["houses_primary"]["unique_len_m"]) / ev["houses_independent_baseline"]["unique_len_m"], 3)))
    D2 = pd.DataFrame(T2).sort_values(["alternatives_per_target_K", "leaf_reroute_passes", "run"]) if T2 else pd.DataFrame()
    D2.to_csv(out / "table2_c2_ablation.csv", index=False)

    # ---------------------------------------------------------------- table 3: connectivity and constraints
    line = pd.read_csv(a.connectivity) if Path(a.connectivity).exists() else None
    T3 = []
    for cfgname, rk in prim.items():
        if rk not in runs:
            continue
        ev, cfg, imp = load(runs[rk])
        c = ev["connectivity"]
        cc = pd.read_csv(runs[rk] / "connectivity_checks.csv")
        ng = imp[imp.set == "network_primary"]
        row = dict(configuration=cfgname, targets=c["routed_total"], failed=len(ev["failures_primary"]) + len(ev["failures_facilities"]), planner_verified_connected=c["planner_verified_connected"],
                   cell_graph_connected=c["cell_graph_connected"], reach_main_component_raster=c["reach_main_component"],
                   hard_constraint_violations=int(cc.hard_violations.fillna(0).sum()), routes_crossing_without_shared_cell=c["routes_with_crossing_no_shared_cell"], cycles=c["cycles"],
                   max_chain_depth=c["max_chain_depth"], network_len_slope_gt25_m=round(float(ng.len_slope_gt25_m.fillna(0).sum()), 1), network_len_slope_gt10_m=round(float(ng.len_slope_gt10_m.fillna(0).sum()), 1),
                   network_len_in_penalised_cells_m=round(float(ng.len_in_penalised_cells_m.fillna(0).sum()), 1),
                   network_routes_crossing_other_footprints_houses=cross(imp, "network_primary", "house")[0], network_routes_crossing_other_footprints_all=cross(imp, "network_primary")[0])
        if line is not None and rk == SN.PRIMARY:
            row["reach_main_component_road_lines"] = int(line.line_main_component_0p01m.sum())
        T3.append(row)
    D3 = pd.DataFrame(T3)
    D3.to_csv(out / "table3_connectivity_constraints.csv", index=False)

    # ---------------------------------------------------------------- table 4: C1 sensitivity
    base_ts = pd.read_csv(runs[prim["x4 (primary)"]] / "target_status.csv", dtype={"planner_key": str}) if prim["x4 (primary)"] in runs else None
    rows4 = []
    for name, d in runs.items():
        ev, cfg, _ = load(d)
        if "_final" not in name or cfg["building_mult"] != 4.0 or cfg["slope_limit_deg"] != 25.0 or cfg["scenario"] != "S2" or cfg["k"] != 3 or cfg["passes"] != 2 or cfg.get("avoid_buildings", "off") != "off" or cfg["cost_scenario"] != "C0":
            continue
        pt = cfg.get("perturb", "none")
        if pt == "none" and name != prim["x4 (primary)"]:
            continue
        label = "baseline (no perturbation)" if pt == "none" else ("omit %d%%" % round(cfg["perturb_frac"] * 100) if pt == "omit" else "add %d%%" % round(cfg["perturb_frac"] * 100) if pt == "add" else
                                                                         "omit merged blobs" if pt == "omit_merge" else "omit smallest %g%%" % cfg.get("small_pct", 25))
        ts = pd.read_csv(d / "target_status.csv", dtype={"planner_key": str})
        common = base_ts.merge(ts, on="planner_key", suffixes=("_b", "_p")) if base_ts is not None else None
        same = float((common.primary_attach_class_b == common.primary_attach_class_p).mean()) if common is not None and len(common) else np.nan
        dl = float((common.primary_len_m_p - common.primary_len_m_b).mean()) if common is not None and len(common) else np.nan
        routed = ev["houses_primary"]["n"]
        rows4.append(dict(perturbation=label, run=name, seed=cfg.get("perturb_seed") if pt in ("omit", "add") else "", house_targets_routed=routed, failed=len(ev["failures_primary"]),
                          unique_len_m=ev["houses_primary"]["unique_len_m"], unique_len_per_routed_m=ev["houses_primary"]["unique_len_m"] / max(routed, 1),
                          saving_vs_independent_pct=100 * (ev["houses_independent_baseline"]["unique_len_m"] - ev["houses_primary"]["unique_len_m"]) / ev["houses_independent_baseline"]["unique_len_m"],
                          routes_crossing_other_footprints=cross(load(d)[2], "network_primary", "house")[0], reach_main_component=ev["connectivity"]["reach_main_component"], targets_total=ev["connectivity"]["routed_total"],
                          share_common_targets_same_attach_class=same, mean_len_change_common_targets_m=dl))
    R4 = pd.DataFrame(rows4)
    R4.to_csv(out / "table4_c1_sensitivity_per_run.csv", index=False)
    agg = []
    for lab, g in R4.groupby("perturbation", sort=False):
        agg.append(dict(perturbation=lab, runs=len(g), house_targets_routed_mean=g.house_targets_routed.mean(), failed_max=g.failed.max(), unique_len_m_mean=g.unique_len_m.mean(),
                        unique_len_m_min=g.unique_len_m.min(), unique_len_m_max=g.unique_len_m.max(), unique_len_per_routed_m_mean=g.unique_len_per_routed_m.mean(),
                        saving_vs_independent_pct_mean=g.saving_vs_independent_pct.mean(), routes_crossing_other_footprints_mean=g.routes_crossing_other_footprints.mean(),
                        share_common_targets_same_attach_class_mean=g.share_common_targets_same_attach_class.mean(), mean_len_change_common_targets_m_mean=g.mean_len_change_common_targets_m.mean()))
    D4 = pd.DataFrame(agg).round(2)
    order = {"baseline (no perturbation)": 0, "omit 10%": 1, "omit 20%": 2, "add 10%": 3, "add 20%": 4}
    D4 = D4.sort_values("perturbation", key=lambda s: s.map(lambda v: order.get(v, 9)))
    D4.to_csv(out / "table4_c1_sensitivity.csv", index=False)

    # ---------------------------------------------------------------- table 6: obstacle avoidance trade-off
    xd = out / "building_crossings_summary.csv"
    xs = pd.read_csv(xd).set_index("run") if xd.exists() else None
    rows6 = []
    for name, d in runs.items():
        ev, cfg, imp = load(d)
        av = cfg.get("avoid_buildings", "off")
        if "_K1_" in name or "_K3_" in name or "_final" not in name or cfg["scenario"] != "S2" or cfg["cost_scenario"] != "C0" or cfg["slope_limit_deg"] != 25.0 or cfg.get("perturb", "none") != "none" or cfg["building_quality"] != "PLAUSIBLE,REVIEW,UNRESOLVED_MERGE":      # only the final-family S2 scenarios
            continue
        if cfg.get("perturb", "none") != "none" or cfg["scenario"] != "S2" or cfg["slope_limit_deg"] != 25.0 or cfg["k"] != 3 or cfg["passes"] != 2:
            continue
        if not ((av == "off" and cfg["building_mult"] in (1.0, 4.0)) or av == "buffer"):
            continue
        nc, ln = cross(imp, "network_primary", "house")
        label = {SN.P3: "x1, no penalty (P3 control)", SN.PRIMARY: "x4, penalty on footprint cells (primary)"}.get(name, "buffer %.1f m, penalty x%g" % (cfg.get("avoid_buffer_m", 7.1), cfg["building_mult"]))
        indu = ev["houses_independent_baseline"]["unique_len_m"]
        rows6.append(dict(scenario=label, run=name, penalty_multiplier=cfg["building_mult"], avoid_buildings=av, houses_routed=ev["houses_primary"]["n"], failed=len(ev["failures_primary"]) + len(ev["failures_facilities"]),
                          house_unique_len_m=round(ev["houses_primary"]["unique_len_m"], 1), independent_unique_len_m_same_config=round(indu, 1),
                          saving_vs_independent_pct=round(100 * (indu - ev["houses_primary"]["unique_len_m"]) / indu, 1), house_routes_crossing_other_footprints=nc, crossing_len_m=ln,
                          crossing_only_in_first_20m=int(xs.loc[name, "crossing_only_in_first_20m"]) if xs is not None and name in xs.index else "",
                          crossing_beyond_first_20m=int(xs.loc[name, "crossing_beyond_first_20m"]) if xs is not None and name in xs.index else "",
                          facility_unique_len_m=round(ev["facilities_primary"]["unique_len_m"], 1), reach_main_component=ev["connectivity"]["reach_main_component"], targets=ev["connectivity"]["routed_total"]))
    D6 = pd.DataFrame(rows6)
    if len(D6):
        D6 = D6.sort_values(["avoid_buildings", "penalty_multiplier"], key=lambda s_: s_.map(lambda v: {"off": 0, "buffer": 1}.get(v, v)))
    D6.to_csv(out / "table6_obstacle_avoidance.csv", index=False)

    # ---------------------------------------------------------------- markdown
    md = ["# Baseline versus proposed: comparison tables", "",
          "Source: `%s`. Lengths are metres on a 10 m planning grid; costs are ordinal planning units. The x4 and x1 configurations are kept apart, and each uses its own baselines. "
          "Omit/add runs are synthetic sensitivity probes, not measured detector error. Network results are planning alternatives, not verified roads." % root, "",
          "## Table 1. Unique road length: independent routes versus shared network", "", D1.fillna("").to_markdown(index=False), "",
          "Unique length counts a grid edge once. The independent routes duplicate edges that several houses share (duplicated length); the network-aware plan lets a route end on another route or road, so almost no grid edge is used twice.", ""]
    if len(D2):
        md += ["## Table 2. C2 ablation (primary x4 configuration)", "", D2.to_markdown(index=False), ""]
    md += ["## Table 3. Connectivity and constraint checks", "", D3.fillna("").to_markdown(index=False), "",
           "`reach_main_component_raster` is the planner's definition (the 6,149-cell main road component inside the village polygon); `reach_main_component_road_lines` uses the TGRAC road lines including the parts outside the polygon (see connectivity_resolution.md).", "",
           "## Table 4. C1 sensitivity to synthetic target omissions and additions (x4 configuration)", "", D4.fillna("").to_markdown(index=False), "",
           "Per-run rows are in `table4_c1_sensitivity_per_run.csv`. Compare `unique_len_per_routed_m`, not total length: removing targets removes routes, so a shorter network is not by itself more efficient.", ""]
    if len(D6):
        md += ["## Table 6. Obstacle avoidance: price and effect of keeping routes out of building footprints", "", D6.fillna("").to_markdown(index=False), "",
               "Hard blocking of footprint cells failed: all 163 house points lie inside their own blocked cell and the planner does not start from a blocked cell. "
               "The buffer scenarios hand the planner footprints buffered by 7.1 m (half a cell diagonal) with a large penalty. The effect saturates by x20; the remaining crossings are mostly at the start of a route, where the target sits among touching buildings.", ""]
    ee = out / "economic_impact.md"
    if ee.exists():
        md += ["## Table 5. Economic and material impact (illustrative; assumptions in inputs/economic_assumptions.json)", "", ee.read_text(encoding="utf-8").split("\n", 2)[2], ""]
    (out / "comparison_report.md").write_text("\n".join(md), encoding="utf-8")
    print(D1.to_string(index=False)); print(D3.T.to_string()); print(D4.to_string(index=False))


if __name__ == "__main__":
    main()
