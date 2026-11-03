#!/usr/bin/env python
"""dk_stageB_c1_compare.py - C1 clustered-omission comparison (READ-ONLY on runs; writes ONE new folder <stageb-root>\\_c1_<label>).
Compares a baseline run with deterministic omission runs (omit_small / omit_merge). Omissions are SIMULATED target removals, not measured segmentation error.
Outputs: c1_scenario_comparison.csv, omitted_candidates.csv, c1_validation.csv, c1_summary.md, c1_comparison.png"""
import argparse, json, re, sys
from pathlib import Path
import numpy as np, pandas as pd
ap = argparse.ArgumentParser()
ap.add_argument("--stageb-root", required=True); ap.add_argument("--label", required=True)
ap.add_argument("--baseline", required=True, help="baseline run folder name"); ap.add_argument("--runs", nargs="+", required=True, help="C1 omission run folder names")
a = ap.parse_args(); root = Path(a.stageb_root); out = root / f"_c1_{a.label}"
if out.exists(): print("STOP: exists", out); sys.exit(1)
def load(r):
    d = root / r; return dict(ev=json.loads((d / "evaluation_summary.json").read_text()), ts=pd.read_csv(d / "target_status.csv", dtype={"cand_id": str}),
                              imp=pd.read_csv(d / "impact_flags.csv"), cn=pd.read_csv(d / "connectivity_checks.csv"), cfg=json.loads((d / "config_stageB.json").read_text()))
def overview(r, L):
    e, t, i = L["ev"], L["ts"], L["imp"]; hp, ind = e["houses_primary"], e["houses_independent_baseline"]
    h = i[i.kind == "house"].copy(); h["lob"] = h.len_other_PLAUSIBLE_m + h.len_other_REVIEW_m + h.len_other_UNRESOLVED_MERGE_m
    def g(s, col, f="sum"): 
        x = h[h.set == s][col]; return float(getattr(x, f)()) if len(x) else np.nan
    n = len(t); ok = int((t.primary_status == "ROUTED").sum())
    return dict(run=r, scenario=e["scenario"], slope_deg=e["slope_limit_deg"], cost=e["cost_scenario"], penalty_classes="+".join(e["building_quality"]), penalty_mult=L["cfg"]["args"]["building_mult"],
                perturb=(L["cfg"].get("perturbation") or {}).get("mode", "none"), perturb_frac=(L["cfg"].get("perturbation") or {}).get("frac", 0), seed=(L["cfg"].get("perturbation") or {}).get("seed", ""),
                n_targets=n, routed=ok, failed=n - ok, net_unique_len_m=hp["unique_len_m"], net_total_len_m=hp["total_len_m"], indep_unique_len_m=ind["unique_len_m"], indep_total_len_m=ind["total_len_m"],
                credit_unique_vs_indep_m=ind["unique_len_m"] - hp["unique_len_m"], credit_pct=100 * (ind["unique_len_m"] - hp["unique_len_m"]) / ind["unique_len_m"] if ind["unique_len_m"] else np.nan,
                net_unique_len_per_routed_m=hp["unique_len_m"] / ok if ok else np.nan, facility_unique_len_m=e["facilities_primary"]["unique_len_m"],
                facility_effect_on_house_len_m=e.get("facility_effect_on_house_unique_len_m", np.nan), attach_ROAD=e["attach_class_counts_primary_houses"].get("ROAD", 0),
                attach_FACILITY=e["attach_class_counts_primary_houses"].get("FACILITY_ROUTE", 0), attach_HOUSE=e["attach_class_counts_primary_houses"].get("HOUSE_ROUTE", 0),
                max_chain_depth=e["connectivity"]["max_chain_depth"], not_main_component=int((~L["cn"].reaches_main_road_component).sum()),
                net_routes_crossing_other_bldg=int((h[h.set == "network_primary"].n_other_polygons_crossed > 0).sum()), net_len_in_other_bldg_m=g("network_primary", "lob"),
                indep_len_in_other_bldg_m=g("independent_baseline", "lob"), net_len_penalised_cells_m=g("network_primary", "len_in_penalised_cells_m"),
                net_len_slope_gt10_m=g("network_primary", "len_slope_gt10_m"), net_len_in_repaired_parcels_m=g("network_primary", "len_in_repaired_parcels_m"))

names = [a.baseline] + a.runs
LD = {r: load(r) for r in names}
ov = pd.DataFrame([overview(r, LD[r]) for r in names]).set_index("run")
base = ov.loc[a.baseline]
om = []
for r in a.runs:
    lg = pd.read_csv(root / r / "perturbation_log.csv"); lg.insert(0, "run", r); om.append(lg)
OM = pd.concat(om, ignore_index=True)
rows = []
for r in names:
    x = ov.loc[r]; n_om = int((OM.run == r).sum()) if r != a.baseline else 0
    d = dict(run=r, role="BASELINE" if r == a.baseline else "OMISSION", original_targets=int(base.n_targets), omitted=n_om, remaining=int(x.n_targets), routed=int(x.routed), genuine_failures=int(x.failed),
             not_main_component=int(x.not_main_component))
    for m in ["net_unique_len_m", "net_total_len_m", "indep_unique_len_m", "credit_unique_vs_indep_m", "credit_pct", "facility_unique_len_m", "attach_ROAD", "attach_FACILITY", "attach_HOUSE", "max_chain_depth",
              "net_routes_crossing_other_bldg", "net_len_in_other_bldg_m", "net_len_penalised_cells_m", "net_len_slope_gt10_m", "net_len_in_repaired_parcels_m"]:
        d[m] = float(x[m]); d[m + "_diff_abs"] = float(x[m] - base[m]); d[m + "_diff_pct"] = 100 * (x[m] - base[m]) / base[m] if base[m] else np.nan
    d["net_unique_len_per_routed_m"] = float(x.net_unique_len_per_routed_m); d["net_unique_len_per_routed_diff_pct"] = 100 * (x.net_unique_len_per_routed_m - base.net_unique_len_per_routed_m) / base.net_unique_len_per_routed_m
    d["crossing_routes_per_routed"] = float(x.net_routes_crossing_other_bldg / x.routed) if x.routed else np.nan
    rows.append(d)
CMP = pd.DataFrame(rows)
# ---- validation
V = []
def chk(i, ok, name, det="", fail="FAIL"): V.append(dict(id=i, status="PASS" if ok else fail, name=name, detail=det))
bt = set(LD[a.baseline]["ts"].cand_id.astype(str).str.split(".").str[0])
for r in a.runs:
    ts = LD[r]["ts"]; rt = set(ts.cand_id.astype(str).str.split(".").str[0]); o = OM[OM.run == r]; oi = set(o.cand_id.astype(int).astype(str))
    chk(f"C01 {r}", oi <= bt, "omitted IDs are all baseline targets", f"omitted={len(oi)}")
    chk(f"C02 {r}", len(oi) == len(o), "no duplicate omitted IDs")
    chk(f"C03 {r}", rt == bt - oi, "remaining targets = baseline minus omitted", f"remaining={len(rt)} baseline={len(bt)} omitted={len(oi)}")
    chk(f"C04 {r}", len(rt) + len(oi) == len(bt), "counts reconcile")
    chk(f"C05 {r}", not (set(ts[ts.primary_status != "ROUTED"].cand_id.astype(str).str.split(".").str[0]) & oi), "omitted targets are not counted as routing failures")
    cfgb, cfgr = LD[a.baseline]["cfg"]["args"], LD[r]["cfg"]["args"]
    same = {k: (cfgb.get(k) == cfgr.get(k)) for k in cfgb if k not in ("perturb", "perturb_frac", "perturb_seed", "small_pct", "label", "check_only", "village_root", "project_root", "planner")}
    bad = [k for k, v in same.items() if not v]
    chk(f"C06 {r}", not bad, "all non-perturbation settings equal the baseline", f"differs={bad}")
    chk(f"C07 {r}", abs(ov.loc[r, "facility_unique_len_m"] - base.facility_unique_len_m) < 0.011, "facility routes unchanged (facilities are planned first and are not omitted)", f"{ov.loc[r,'facility_unique_len_m']:.3f} vs {base.facility_unique_len_m:.3f}", fail="WARN")
    fin = np.isfinite(ov.loc[r, ["net_unique_len_m", "indep_unique_len_m", "credit_pct"]].astype(float)).all()
    chk(f"C08 {r}", bool(fin), "headline metrics finite")
VD = pd.DataFrame(V)
out.mkdir(parents=True)
CMP.to_csv(out / "c1_scenario_comparison.csv", index=False); OM.to_csv(out / "omitted_candidates.csv", index=False); VD.to_csv(out / "c1_validation.csv", index=False)
# non-main-component report
nm = []
for r in names:
    cn = LD[r]["cn"]; ts = LD[r]["ts"]; c = cn[(~cn.reaches_main_road_component) & (cn.kind == "house")]
    for x in c.itertuples():
        t = ts[ts.cand_id.astype(str).str.split(".").str[0] == str(x.cand_id).split(".")[0]].iloc[0]
        nm.append(dict(run=r, cand_id=t.cand_id, v1_house_id=t.v1_house_id, quality_class=t.quality_class, attach_class=x.attach_class, road_component=x.road_component, route_len_m=t.primary_len_m))
pd.DataFrame(nm).to_csv(out / "non_main_component_targets.csv", index=False)
# plots
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
lab = [("Baseline" if r == a.baseline else r.split("_s25_")[-1].replace("_", " ")) for r in names]
fig, ax = plt.subplots(1, 4, figsize=(14, 3.6))
for k, (col, ttl, u) in enumerate([("remaining", "Remaining targets", "count"), ("net_unique_len_m", "Network unique length", "m"), ("net_unique_len_per_routed_m", "Unique length per routed target", "m"), ("net_routes_crossing_other_bldg", "Routes crossing other footprints", "count")]):
    ax[k].bar(range(len(names)), CMP[col], color=["#555"] + ["#4a90d9"] * (len(names) - 1)); ax[k].set_xticks(range(len(names))); ax[k].set_xticklabels(lab, rotation=30, ha="right", fontsize=7)
    ax[k].set_title(ttl, fontsize=9); ax[k].set_ylabel(u, fontsize=8)
fig.suptitle("C1 simulated omissions (model-derived; not measured segmentation error)", fontsize=9); fig.tight_layout(); fig.savefig(out / "c1_comparison.png", dpi=200)
md = ["# C1 clustered-omission comparison (read-only summary)", "", "Omissions are simulated target removals. They are not measured false-negative rates. Costs are ordinal; no field validation; success of a run is not real-world feasibility.", "",
      CMP[["run", "role", "original_targets", "omitted", "remaining", "routed", "genuine_failures", "not_main_component", "net_unique_len_m", "net_unique_len_per_routed_m", "credit_pct", "net_routes_crossing_other_bldg", "net_len_in_other_bldg_m"]].round(2).to_markdown(index=False), "",
      "Validation: " + str(VD.status.value_counts().to_dict())]
(out / "c1_summary.md").write_text("\n".join(md))
print(CMP[["run", "omitted", "remaining", "routed", "genuine_failures", "not_main_component", "net_unique_len_m", "net_unique_len_per_routed_m", "credit_pct", "net_routes_crossing_other_bldg", "net_len_in_other_bldg_m", "facility_unique_len_m"]].round(2).to_string(index=False))
print(VD.to_string(index=False)); print("written:", out)
