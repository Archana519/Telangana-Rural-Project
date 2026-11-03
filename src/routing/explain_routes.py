"""explain_routes.py - READ-ONLY explanation of why each Stage B route was chosen.

Reads one Stage B run folder (selection_summary.csv, route_edges.csv, route_alternatives.csv, shared_edge_per_target.csv,
connectivity_checks.csv, scenario_targets.csv, config_stageB.json) and the rasters recorded in its inputs manifest, and writes
  route_explanations.csv   one row per selected route, with the numbers behind the choice
  route_explanations.md    the same as short sentences
It never runs or changes the planner, so the planner hash is unaffected. Every statement is computed from files; nothing is inferred
about real roads. Costs are ordinal planning units, not rupees.

What the planner does (plan_network_v2.py docstring): at each step it picks the (target, candidate route) with the highest
weight / marginal unique cost, where the candidates are the target's Stage A alternatives and a fresh least-cost path to the current
network (roads plus routes already chosen). Marginal cost counts only edges not already in the network (shared-edge credit).

usage: python src/routing/explain_routes.py --run-dir <stageB run folder> --out <output folder>
"""
import argparse, csv, json
from pathlib import Path

import numpy as np
import rasterio

WC = {10: "tree cover", 20: "shrubland", 30: "grassland", 40: "cropland", 50: "built-up", 60: "bare/sparse", 80: "water", 0: "no data"}
SLOPE_MAX, SLOPE_WEIGHT = 10.0, 4.0   # from create_damarakunta_cost_surface.py: slope surcharge = clip(slope, 0, 10) / 10 * 4


def read_csv(p):
    return list(csv.DictReader(open(p, encoding="utf-8")))


def f(x, d=0.0):
    try:
        return float(x)
    except (TypeError, ValueError):
        return d


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    run = Path(a.run_dir)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    cfg = json.load(open(run / "config_stageB.json", encoding="utf-8"))["args"]
    man = {r["role"]: r["path"] for r in read_csv(run / "inputs_manifest_stageB.csv")}
    slope_limit, bmult = cfg["slope_limit_deg"], cfg["building_mult"]
    with rasterio.open(man["worldcover"]) as s:
        wc = s.read(1)
    with rasterio.open(man["slope"]) as s:
        slope = s.read(1).astype(float)
        slope[slope == s.nodata] = np.nan
    with rasterio.open(man["cost"]) as s:
        cost = s.read(1).astype(float)
        cost[cost == s.nodata] = np.nan
    pen = np.clip(np.nan_to_num(slope), 0, SLOPE_MAX) / SLOPE_MAX * SLOPE_WEIGHT

    sel = read_csv(run / "selection_summary.csv")
    edges = {}
    for r in read_csv(run / "route_edges.csv"):
        edges.setdefault((r["scope"], r["route_id"]), []).append(r)
    alts = {}
    for r in read_csv(run / "route_alternatives.csv"):
        alts.setdefault((r["scope"], r["target_id"]), []).append(r)
    share = {(r["scope"], r["target_id"]): r for r in read_csv(run / "shared_edge_per_target.csv")}
    conn = {r["target_id"]: r for r in read_csv(run / "connectivity_checks.csv")}
    tinfo = {r["planner_key"]: r for r in read_csv(run / "scenario_targets.csv")}

    nshared = len(read_csv(run / "shared_edge_accounting.csv"))
    rows, md = [], ["# Why each route was chosen", "",
                    "Run `%s` (slope limit %g degrees, building penalty x%g). Computed from the run files; costs are ordinal planning units, not rupees. "
                    "These are planning alternatives, not verified roads. Grid edges used by more than one route in this run: %d, so the network saving comes from routes ending on other routes or roads (attachment), not from overlapping edges." % (run.name, slope_limit, bmult, nshared), ""]
    for s in sel:
        key = (s["scope"], s["target_id"])
        tid = s["target_id"]
        E = edges.get(key, [])
        length = sum(f(e["len_m"]) for e in E)
        by_wc, smax, sw, n_pen, pen_extra, base_cost, slope_cost = {}, 0.0, 0.0, 0, 0.0, 0.0, 0.0
        for e in E:
            ra, ca, rb, cb, L, c = int(e["row_a"]), int(e["col_a"]), int(e["row_b"]), int(e["col_b"]), f(e["len_m"]), f(e["cost"])
            cls = int(wc[rb, cb])
            by_wc[cls] = by_wc.get(cls, 0.0) + L
            sb = np.nan_to_num(slope[rb, cb])
            smax = max(smax, float(sb)); sw += float(sb) * L
            expected = 0.5 * (cost[ra, ca] + cost[rb, cb]) * L
            sl = 0.5 * (pen[ra, ca] + pen[rb, cb]) * L
            slope_cost += sl; base_cost += expected - sl
            if np.isfinite(expected) and c > expected * 1.01 + 1e-6:
                n_pen += 1; pen_extra += c - expected
        alt = alts.get(key, [])
        chosen_alt = next((x["alt_rank"] for x in alt if x["identical_to_selected_route"] == "True"), "")
        other = [x for x in alt if x["alt_rank"] != chosen_alt]
        sh = share.get(key, {})
        total_cost, marg = f(s["cost"]), f(s["marginal_cost_when_added"])
        ind = next((x for x in alt if x["alt_rank"] == "1"), None)       # rank 1 = independent least-cost route to the roads
        save_cost = (f(ind["cost"]) - total_cost) if ind else None
        save_len = (f(ind["len_m"]) - f(s["len_m"])) if ind else None
        c = conn.get(tid, {})
        ti = tinfo.get(tid, {})
        mix = "; ".join("%s %.0f%%" % (WC.get(k, str(k)), 100 * v / length) for k, v in sorted(by_wc.items(), key=lambda kv: -kv[1])) if length else "no grid edges (target already on or next to the network)"
        if s["mode"].startswith("stageA_alt"):
            how = "its Stage A alternative rank %s" % chosen_alt if chosen_alt else "a Stage A alternative"
        elif s["mode"] == "attach_network":
            how = "a fresh least-cost path to the current network (roads plus routes already chosen)"
        else:
            how = s["mode"]
        why = ("Chosen at step %s as %s: it had the highest weight / marginal-cost score among all unserved targets' candidates at that step. "
               "Planner log: marginal cost %.1f, route cost %.1f, score %.4f. " % (s["step"], how, marg, total_cost, f(s["implied_score_weight_over_marginal"])))
        if ind is not None:
            why += ("Compared with the independent least-cost route to the roads (%.0f m, cost %.0f), this route is %.0f m and %.0f cost units %s. " % (
                f(ind["len_m"]), f(ind["cost"]), abs(save_len), abs(save_cost), "shorter and cheaper" if save_len > 0 and save_cost > 0 else
                "shorter" if save_len > 0 else "not shorter") if abs(save_cost) > 0.5 else
                "Same cost as the independent least-cost route to the roads. ")
        if other:
            why += "Other alternatives for this target: " + "; ".join("rank %s %.0f m, cost %.0f" % (x["alt_rank"], f(x["len_m"]), f(x["cost"])) for x in other) + ". "
        why += "Ground crossed: %s. Slope mean %.1f, max %.1f degrees (limit %g); slope surcharge is %.0f%% of base cost. " % (
            mix, (sw / length if length else 0.0), smax, slope_limit, 100 * slope_cost / max(base_cost + slope_cost, 1e-9))
        if n_pen:
            why += "%d edges entered penalised building cells (extra cost %.1f from the x%g penalty). " % (n_pen, pen_extra, bmult)
        if c.get("attach_class"):
            why += "Ends on %s%s%s." % (c["attach_class"], " " + c["attach_parent"] if c.get("attach_parent") else "",
                                        "" if c.get("reaches_main_road_component") == "True" else " (component not connected to the main road component inside the grid)")
        row = dict(scope=s["scope"], step=s["step"], target_id=tid, quality_class=ti.get("quality_class", ""), mode=s["mode"], alt_rank_used=s["alt_rank_used"],
                   len_m=round(length, 2), route_cost=round(total_cost, 2), marginal_cost=marg, saving_vs_independent_cost=None if save_cost is None else round(save_cost, 2), saving_vs_independent_len_m=None if save_len is None else round(save_len, 2),
                   equal_share_cost=sh.get("equal_share_cost", ""), landcover_mix=mix, slope_mean_deg=round(sw / length, 2) if length else 0,
                   slope_max_deg=round(smax, 2), slope_surcharge_share=round(slope_cost / max(base_cost + slope_cost, 1e-9), 3),
                   building_penalty_edges=n_pen, building_penalty_extra_cost=round(pen_extra, 2), attach_class=c.get("attach_class", ""),
                   attach_parent=c.get("attach_parent", ""), reaches_main_road_component=c.get("reaches_main_road_component", ""), explanation=why.strip())
        rows.append(row)
        md.append("- **%s %s** (%s): %s" % (s["scope"].replace("_phase", ""), tid, ti.get("quality_class", "-"), why.strip()))
    with open(out / "route_explanations.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    (out / "route_explanations.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("explained %d routes -> %s" % (len(rows), out))


if __name__ == "__main__":
    main()
