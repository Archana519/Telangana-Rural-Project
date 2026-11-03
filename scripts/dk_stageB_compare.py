#!/usr/bin/env python
"""dk_stageB_compare.py - cross-run comparison of Stage B runs. Reads run folders only; writes ONE new folder
<stageB root>\\_compare_<label>\\ (exclusive creation, never overwrites). Model-derived planning proxies only; not INR, not field validated."""
import argparse, json, sys
from pathlib import Path
import pandas as pd

ap = argparse.ArgumentParser()
ap.add_argument("--stageb-root", required=True)
ap.add_argument("--runs", nargs="+", required=True, help="run folder names; first is the reference")
ap.add_argument("--label", required=True)
ap.add_argument("--determinism-pair", nargs=2, default=None, help="two run folders that should be identical")
a = ap.parse_args()
root = Path(a.stageb_root); out = root / f"_compare_{a.label}"
if out.exists():
    print("STOP: compare folder exists:", out); sys.exit(1)
rows, per = [], {}
for r in a.runs:
    d = root / r
    if not (d / "evaluation_summary.json").exists():
        print("STOP: missing", d); sys.exit(2)
    e = json.loads((d / "evaluation_summary.json").read_text()); t = pd.read_csv(d / "target_status.csv")
    per[r] = t
    hp, ind = e["houses_primary"], e["houses_independent_baseline"]
    rows.append(dict(run=r, scenario=e["scenario"], slope_limit_deg=e["slope_limit_deg"], cost_scenario=e["cost_scenario"], n_house=e["n_house_targets"],
                     house_routed=int((t.primary_status == "ROUTED").sum()), house_failed=int((t.primary_status == "FAILED").sum()),
                     houses_network_total_len_m=hp["total_len_m"], houses_network_unique_len_m=hp["unique_len_m"], houses_network_unique_cost=hp["unique_cost"],
                     houses_independent_total_len_m=ind["total_len_m"], houses_independent_unique_len_m=ind["unique_len_m"], houses_independent_total_cost=ind["total_cost"],
                     unique_len_reduction_vs_independent_m=ind["unique_len_m"] - hp["unique_len_m"],
                     facilities_unique_len_m=e["facilities_primary"]["unique_len_m"], combined_unique_len_m=e["combined_primary"]["unique_len_m"],
                     combined_independent_total_cost=e.get("combined_independent_baseline", {}).get("total_cost"),
                     houses_roads_only_ref_unique_len_m=e.get("houses_roads_only_reference", {}).get("unique_len_m"),
                     straight_len_m=e["houses_straight_line"]["total_len_m"], straight_infeasible=e["houses_straight_line"]["infeasible"],
                     attach_ROAD=e["attach_class_counts_primary_houses"].get("ROAD", 0), attach_FACILITY=e["attach_class_counts_primary_houses"].get("FACILITY_ROUTE", 0),
                     attach_HOUSE=e["attach_class_counts_primary_houses"].get("HOUSE_ROUTE", 0), max_chain_depth=e["connectivity"]["max_chain_depth"], cycles=e["connectivity"]["cycles"]))
S = pd.DataFrame(rows)
ref = per[a.runs[0]].set_index("cand_id")
pair = []
for r in a.runs[1:]:
    t = per[r].set_index("cand_id"); common = ref.index.intersection(t.index)
    x = pd.DataFrame(dict(run=r, cand_id=common, ref_len=ref.loc[common, "primary_len_m"].values, len=t.loc[common, "primary_len_m"].values,
                          ref_attach=ref.loc[common, "primary_attach_parent_key"].values, attach=t.loc[common, "primary_attach_parent_key"].values))
    x["len_diff_m"] = x["len"] - x["ref_len"]; x["attach_changed"] = x.ref_attach.astype(str) != x.attach.astype(str)
    x["stratum"] = ref.loc[common, "stratum"].values; pair.append(x)
P = pd.concat(pair) if pair else pd.DataFrame()
summ = P.groupby(["run", "stratum"]).agg(n=("cand_id", "size"), mean_len_diff_m=("len_diff_m", "mean"), attach_changed=("attach_changed", "sum")).reset_index() if len(P) else pd.DataFrame()
det = None
if a.determinism_pair:
    x, y = (pd.read_csv(root / n / "target_status.csv") for n in a.determinism_pair)
    c = [k for k in x.columns if k in y.columns]
    det = bool(x[c].equals(y[c]))
out.mkdir(parents=True)
for n, df in (("run_comparison.csv", S), ("target_level_vs_reference.csv", P), ("stratum_vs_reference.csv", summ)):
    with open(out / n, "xb") as f: f.write(df.to_csv(index=False, lineterminator="\n").encode())
with open(out / "compare_notes.txt", "xb") as f:
    f.write(("Reference run: %s\nDeterminism pair identical: %s\nNotes: costs are ordinal model units (not INR). 'unique length' is the planner's unique grid-edge length. "
             "Differences between scenarios mix target-set size and cost effects; compare like-for-like runs only. No field validation or legal-access claim.\n" % (a.runs[0], det)).encode())
pd.set_option("display.width", 250); print(S.T.to_string()); print("determinism identical:", det); print("written:", out)
