#!/usr/bin/env python
"""dk_stageB_final_tables.py - cross-run result tables (read-only on runs; writes ONE new folder <stageb-root>\\_final_<label>).
Groups (auto-detected by folder name):  primary = *_v11 without penalty label | penalty variants = *_P<n>_* | uncertainty = *_omit<p>_seed<s> / *_add<p>_seed<s>.
Also prints the non-main-road-component report. Model-derived proxies only; ordinal costs; no field validation."""
import argparse, json, re, sys
from pathlib import Path
import numpy as np, pandas as pd

ap = argparse.ArgumentParser()
ap.add_argument("--stageb-root", required=True); ap.add_argument("--label", required=True)
ap.add_argument("--primary-suffix", default="_v11"); ap.add_argument("--reference-run", default="S2_fac_C0_s25_v11")
a = ap.parse_args(); root = Path(a.stageb_root); out = root / f"_final_{a.label}"
if out.exists(): print("STOP: exists", out); sys.exit(1)
runs = sorted(p.name for p in root.iterdir() if p.is_dir() and not p.name.startswith("_") and not p.name.endswith("_rep"))   # *_rep = reproducibility repeats, audited by the validator, excluded here
primary = [r for r in runs if r.endswith(a.primary_suffix) and not re.search(r"_P\d|_omit\d|_add\d", r)]
pen = [r for r in runs if re.search(r"_P\d", r)]
unc = [r for r in runs if re.search(r"_(omit|add)\d+_seed\d+", r)]
print("primary:", primary, "\npenalty variants:", pen, "\nuncertainty runs:", len(unc))

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
LD = {r: load(r) for r in primary + pen + unc}
ov = pd.DataFrame([overview(r, LD[r]) for r in primary + pen + unc])
# strata long table
st = []
for r in primary:
    s = pd.read_csv(root / r / "evaluation_by_stratum.csv"); s.insert(0, "run", r); st.append(s)
strata = pd.concat(st) if st else pd.DataFrame()
# non-main-component report
nm = []
for r in primary + pen:
    L = LD[r]; c = L["cn"][(~L["cn"].reaches_main_road_component) & (L["cn"].kind == "house")]
    for x in c.itertuples():
        t = L["ts"][L["ts"].cand_id == str(x.cand_id).split(".")[0]].iloc[0]
        nm.append(dict(run=r, cand_id=t.cand_id, v1_house_id=t.v1_house_id, quality_class=t.quality_class, origin=t.origin, stratum=t.stratum, primary_status=t.primary_status,
                       attach_class=x.attach_class, attach_parent=x.attach_parent, chain_depth=x.chain_depth, chain_terminal=x.chain_terminal, road_component=x.road_component,
                       route_len_m=t.primary_len_m, dist_to_road_m=t.dist_to_road_m,
                       reason=f"route chain terminates on a TGRAC road cell that belongs to grid road component {x.road_component}, not the main component (1); disconnected inside the planning grid, link outside the grid unknown"))
NM = pd.DataFrame(nm)
# uncertainty aggregate + stability against the primary S2 reference
agg, stab = pd.DataFrame(), []
if unc and a.reference_run in LD:
    U = ov[ov.perturb != "none"].copy()
    ref = LD[a.reference_run]["ts"].set_index("cand_id")
    for r in unc:
        t = LD[r]["ts"].set_index("cand_id"); common = ref.index.intersection(t.index)
        ok = common[(ref.loc[common, "primary_status"] == "ROUTED") & (t.loc[common, "primary_status"] == "ROUTED")]
        dl = (t.loc[ok, "primary_len_m"] - ref.loc[ok, "primary_len_m"])
        same_cls = (t.loc[ok, "primary_attach_class"] == ref.loc[ok, "primary_attach_class"])
        stab.append(dict(run=r, n_common_routed=len(ok), mean_len_change_m=float(dl.mean()), median_abs_len_change_m=float(dl.abs().median()), share_len_changed_gt1m=float((dl.abs() > 1).mean()),
                         share_same_attach_class=float(same_cls.mean())))
    S = pd.DataFrame(stab); U = U.merge(S, on="run")
    cols = ["routed", "failed", "net_unique_len_m", "net_unique_len_per_routed_m", "credit_pct", "attach_HOUSE", "net_routes_crossing_other_bldg", "net_len_in_other_bldg_m", "mean_len_change_m", "share_same_attach_class"]
    agg = U.groupby(["perturb", "perturb_frac"])[cols].agg(["mean", "min", "max"]).round(2); agg.columns = ["_".join(c) for c in agg.columns]; agg = agg.reset_index()
    agg.insert(2, "n_seeds", U.groupby(["perturb", "perturb_frac"]).size().values)
out.mkdir()
def w(n, df):
    with open(out / n, "xb") as f: f.write(df.to_csv(index=False, lineterminator="\n").encode())
w("runs_overview.csv", ov); w("strata_primary_runs.csv", strata); w("non_main_component_targets.csv", NM)
if len(agg): w("uncertainty_aggregate.csv", agg)
if stab: w("uncertainty_target_stability.csv", pd.DataFrame(stab))
with open(out / "README_limitations.txt", "xb") as f:
    f.write(("Stage B final tables. Model-derived planning proxies only.\n"
             "- Slope comes from a ~30 m DEM interpolated to the 10 m grid; it is not genuine 10 m terrain detail.\n"
             "- Costs are ordinal model units, not INR; costs are not comparable across cost scenarios.\n"
             "- PROVISIONAL choices: C1 built-up land cost = 3.0; repaired cadastral layer (_valid); equal facility weights; penalty classes PLAUSIBLE+REVIEW+UNRESOLVED_MERGE x4.\n"
             "- Uncertainty experiments: 'omit' removes random scenario targets together with their footprints (missed detections); 'add' inserts synthetic translated copies of existing buildings (15-50 m) as a sensitivity test only; fixed seeds are in the run names.\n"
             "- Parcel metrics are parcel units crossed, never ownership or legal access. Facility identities are unverified. TGRAC roads may be incomplete; only in-grid road cells are goals.\n"
             "- No field validation, legal access, physical passability, construction savings or verified accessibility improvement is claimed.\n").encode())
pd.set_option("display.width", 250, "display.max_columns", 60)
print("\n== NON-MAIN-COMPONENT TARGETS"); print(NM.drop(columns="reason").to_string(index=False) if len(NM) else "none")
print("\n== PRIMARY"); print(ov[ov.run.isin(primary)][["run", "n_targets", "routed", "failed", "net_unique_len_m", "indep_unique_len_m", "credit_pct", "attach_HOUSE", "net_routes_crossing_other_bldg", "net_len_in_other_bldg_m"]].round(1).to_string(index=False))
print("\n== PENALTY VARIANTS (S2, 25 deg)"); pv = ov[ov.run.isin(pen + [a.reference_run])]
print(pv[["run", "penalty_classes", "penalty_mult", "net_unique_len_m", "credit_pct", "net_routes_crossing_other_bldg", "net_len_in_other_bldg_m", "net_len_penalised_cells_m"]].round(1).to_string(index=False))
if len(agg): print("\n== UNCERTAINTY (mean/min/max over seeds)"); print(agg.to_string(index=False))
print("\nwritten:", out)
