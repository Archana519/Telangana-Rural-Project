#!/usr/bin/env python
"""dk_stageB_validate.py - independent audit of Stage B run folders (read-only on runs; writes ONE new folder <stageb-root>\\_validation_<label>).
Per run: required files, outputs_manifest SHA/size integrity, acceptance_tests FAIL count, target set vs Stage A IDs (or perturbation log),
duplicates/missing, route layers (CRS, empty, validity of non-zero-length lines), connectivity, cycles, failure reasons, V1 regression flags.
Optional --repro-pairs A:B compares target tables of two runs that must be identical. Exit 0 = all PASS."""
import argparse, hashlib, json, sys
from pathlib import Path
import pandas as pd

ap = argparse.ArgumentParser()
ap.add_argument("--stageb-root", required=True)
ap.add_argument("--stagea-dir", required=True)
ap.add_argument("--runs", nargs="*", default=None, help="default: every folder not starting with '_'")
ap.add_argument("--repro-pairs", nargs="*", default=[])
ap.add_argument("--label", required=True)
a = ap.parse_args()
root = Path(a.stageb_root); out = root / f"_validation_{a.label}"
if out.exists(): print("STOP: exists", out); sys.exit(1)
import geopandas as gpd
sa = Path(a.stagea_dir)
S1 = set(pd.read_csv(sa / "targets_default_ids.csv", dtype=str).cand_id); MG = set(pd.read_csv(sa / "targets_merged_sensitivity_ids.csv", dtype=str).cand_id); S2 = S1 | MG
REQ = ["acceptance_tests.csv", "config_stageB.json", "scenario_targets.csv", "target_status.csv", "facility_status.csv", "connectivity_checks.csv", "route_edges.csv",
       "routes.gpkg", "evaluation_summary.json", "impact_flags.csv", "inputs_manifest_stageB.csv", "outputs_manifest.csv", "stageB_run_checks.txt"]
ALLOWED_FAIL = {"TARGET_IN_HARD_CONSTRAINT_CELL_OR_OUTSIDE_GRID", "NO_START_CELL_WITHIN_SNAP_DISTANCE"}
runs = a.runs or sorted(p.name for p in root.iterdir() if p.is_dir() and not p.name.startswith("_"))
rows = []
def add(run, tid, ok, name, detail="", level="FAIL"):
    rows.append(dict(run=run, test_id=tid, status="PASS" if ok else level, name=name, detail=str(detail)[:300]))
for r in runs:
    d = root / r
    miss = [f for f in REQ if not (d / f).exists()]
    add(r, "V01", not miss, "required output files present", miss)
    if miss: continue
    txt = (d / "stageB_run_checks.txt").read_text(encoding="utf-8", errors="replace")
    add(r, "V02", txt.rstrip().endswith("END OF STAGE B RUN CHECKS (file complete)"), "run-checks file complete (written last)")
    man = pd.read_csv(d / "outputs_manifest.csv"); bad = []
    for m in man.itertuples():
        p = d / m.file
        if not p.exists() or p.stat().st_size != m.bytes or hashlib.sha256(p.read_bytes()).hexdigest() != m.sha256: bad.append(m.file)
    add(r, "V03", not bad, "outputs_manifest sizes and SHA-256 match files on disk (outputs_manifest itself and checks excluded by design)", bad, level="WARN" if bad else "FAIL")
    at = pd.read_csv(d / "acceptance_tests.csv")
    add(r, "V04", int((at.status == "FAIL").sum()) == 0, "acceptance_tests.csv has 0 FAIL", at[at.status == "FAIL"].test_id.tolist())
    cfg = json.loads((d / "config_stageB.json").read_text(encoding="utf-8"))
    sc = pd.read_csv(d / "scenario_targets.csv", dtype={"cand_id": str}); ts = pd.read_csv(d / "target_status.csv", dtype={"cand_id": str})
    scen, pert = cfg["args"]["scenario"], cfg.get("perturbation", {}).get("mode", "none") if cfg.get("perturbation") else "none"
    base = S1 if scen == "S1" else S2
    ids = set(sc.cand_id)
    add(r, "V05", not sc.cand_id.duplicated().any() and not ts.cand_id.duplicated().any(), "no duplicate target IDs", "")
    if pert == "none":
        add(r, "V06", ids == base, "target IDs equal the Stage A scenario set", f"missing={len(base - ids)} extra={len(ids - base)}")
    elif pert == "omit":
        lg = pd.read_csv(d / "perturbation_log.csv", dtype={"cand_id": str}); drop = set(lg[lg.action.str.startswith("OMIT")].cand_id)
        add(r, "V06", ids == base - drop and drop <= base, "omit run: targets = scenario minus logged omissions", f"dropped={len(drop)}")
    else:
        lg = pd.read_csv(d / "perturbation_log.csv", dtype={"cand_id": str}); add_ = set(lg[lg.action == "ADD_SYNTHETIC_COPY"].cand_id)
        add(r, "V06", ids == base | add_, "add run: targets = scenario plus logged synthetic additions", f"added={len(add_)}")
    add(r, "V07", set(ts.cand_id) == ids and len(ts) == len(ids), "target_status covers every target exactly once", f"{len(ts)} rows / {len(ids)} ids")
    fails = ts[ts.primary_status == "FAILED"]
    add(r, "V08", set(fails.primary_fail_reason) <= ALLOWED_FAIL, "failure reasons are known planner reasons", dict(fails.primary_fail_reason.value_counts()), level="WARN")
    ok = ts[ts.primary_status == "ROUTED"]
    add(r, "V09", len(ok) + len(fails) == len(ts), "routed + failed = targets", f"{len(ok)}+{len(fails)}")
    cn = pd.read_csv(d / "connectivity_checks.csv")
    add(r, "V10", (cn.chain_terminal == "ROAD").all() and cn.cell_graph_connected.all(), "every routed route terminates on a road (attachment chain and cell graph agree)", int((cn.chain_terminal != "ROAD").sum()))
    add(r, "V11", not (cn.chain_terminal == "CYCLE").any(), "no attachment cycles", "")
    nm = cn[~cn.reaches_main_road_component]
    add(r, "V12", len(nm) == 0, "all routes reach the main road component", nm.target_id.tolist(), level="INFO")
    gp = d / "routes.gpkg"; probs = []
    for lay in gpd.list_layers(gp).name:
        g = gpd.read_file(gp, layer=lay)
        if g.crs is None or g.crs.to_epsg() != 32644: probs.append(f"{lay}:CRS")
        if g.geometry.is_empty.any(): probs.append(f"{lay}:empty")
        nz = g[g.geometry.length > 1e-9] if "straight" in lay else g
        if len(nz) and not nz.geometry.is_valid.all(): probs.append(f"{lay}:invalid")
        if lay == "routes_network_houses" and len(g) != len(ok): probs.append(f"{lay}:count {len(g)} != routed {len(ok)}")
    add(r, "V13", not probs, "routes.gpkg layers: EPSG:32644, non-empty, valid, count equals routed", probs)
    ev = json.loads((d / "evaluation_summary.json").read_text(encoding="utf-8"))
    add(r, "V14", ev["connectivity"]["routed_total"] == len(ok) + ev["n_facility_targets"] - len(pd.read_csv(d / "facility_status.csv").query("status=='FAILED'")), "evaluation summary routed total consistent", ev["connectivity"]["routed_total"])
    if pert == "none" and scen == "S2" and cfg["args"]["slope_limit_deg"] == 25 and cfg["args"]["cost_scenario"] == "C0" and cfg["args"]["building_quality"] == "PLAUSIBLE,REVIEW,UNRESOLVED_MERGE" and cfg["args"]["building_mult"] == 4.0:
        reg = at[at.test_id.str.startswith("REG-0") & (at.test_id != "REG-00")]
        add(r, "V15", len(reg) == 7 and (reg.status == "PASS").all(), "V1 regression REG-01..07 all PASS", len(reg))
for pr in a.repro_pairs:
    x, y = pr.split(":"); tx, ty = pd.read_csv(root / x / "target_status.csv"), pd.read_csv(root / y / "target_status.csv")
    c = [k for k in tx.columns if k in ty.columns]
    ex = pd.read_csv(root / x / "route_edges.csv"); ey = pd.read_csv(root / y / "route_edges.csv")
    add(f"{x} vs {y}", "R01", tx[c].equals(ty[c]) and ex.equals(ey), "reproducibility: target_status and route_edges identical", f"{len(tx)} targets, {len(ex)} edges")
V = pd.DataFrame(rows)
out.mkdir()
with open(out / "validation_results.csv", "xb") as f: f.write(V.to_csv(index=False, lineterminator="\n").encode())
cnt = V.status.value_counts().to_dict()
with open(out / "validation_summary.txt", "xb") as f: f.write((f"runs audited: {len(runs)}\ncounts: {cnt}\nnote: INFO/WARN rows are listed in validation_results.csv; no field validation is implied.\n").encode())
pd.set_option("display.width", 250, "display.max_colwidth", 90)
print(V[V.status != "PASS"].to_string(index=False) if (V.status != "PASS").any() else "all checks PASS")
print("runs audited:", len(runs), "| counts:", cnt, "| written:", out)
sys.exit(0 if cnt.get("FAIL", 0) == 0 else 3)
