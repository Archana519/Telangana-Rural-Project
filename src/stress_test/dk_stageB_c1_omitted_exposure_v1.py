"""dk_stageB_c1_omitted_exposure_v1.py - READ-ONLY controlled contrast on the SAME footprints.
For each omission scenario, take the footprints that scenario omits and measure how much route length lies inside them:
  (A) in the BASELINE routes (planner knew the footprints; penalty applied if the baseline has one) - all baseline routes, and only routes of the retained targets
  (B) in the OMISSION run's routes (planner did not know them)
Caveat built into the outputs: route 'segments' are per-target NEW segments, so shared-edge attribution differs between runs; compare totals, not individual routes."""
import argparse, sys
from pathlib import Path
import pandas as pd, geopandas as gpd
sys.path.insert(0, str(Path(__file__).resolve().parent))
from dk_stageB_c1_footprint_eval_v1 import eval_routes

def exposure(rt, bld, omitted, keep=None):
    d = eval_routes(rt if keep is None else rt[rt.cand_id.astype(int).isin(keep)], bld, omitted)
    return dict(routes=len(d), routes_crossing_omitted=int((d.n_other_omitted > 0).sum()), len_in_omitted_m=float(d.len_other_omitted_m.sum()))

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--stageb-root", required=True); ap.add_argument("--buildings", required=True); ap.add_argument("--label", required=True)
    ap.add_argument("--baseline", required=True); ap.add_argument("--runs", nargs="+", required=True)
    ap.add_argument("--fp-summary", required=True, help="c1_footprint_crossings_full_set.csv from dk_stageB_c1_footprint_eval_v1 (reproduction cross-check)")
    a = ap.parse_args(); root = Path(a.stageb_root); out = root / f"_c1_{a.label}"
    if out.exists(): sys.exit(f"refusing: {out} already exists")
    fp = pd.read_csv(a.fp_summary).set_index("run")
    bld = gpd.read_file(a.buildings, layer="buildings"); bld["cand_id"] = pd.to_numeric(bld.cand_id).astype(int)
    def routes(r):
        g = gpd.read_file(root / r / "routes.gpkg", layer="routes_network_houses"); return g[g.scope.astype(str).str.startswith("network_primary")]
    rb = routes(a.baseline); b = bld.to_crs(rb.crs) if bld.crs != rb.crs else bld; rows, V = [], []
    for r in a.runs:
        d = pd.read_csv(root / r / "perturbation_log.csv"); om = d[d.action.astype(str).str.startswith("OMIT")].cand_id.astype(int).tolist()
        rr = routes(r); keep = set(rr.cand_id.astype(int))
        A_all = exposure(rb, b, om); A_keep = exposure(rb, b, om, keep); B = exposure(rr, b, om)
        rows.append(dict(run=r, omitted_footprints=len(om), retained_targets=len(keep),
                         baseline_all_routes=A_all["routes"], baseline_all_cross_omitted=A_all["routes_crossing_omitted"], baseline_all_len_in_omitted_m=A_all["len_in_omitted_m"],
                         baseline_retained_routes=A_keep["routes"], baseline_retained_cross_omitted=A_keep["routes_crossing_omitted"], baseline_retained_len_in_omitted_m=A_keep["len_in_omitted_m"],
                         omission_routes=B["routes"], omission_cross_omitted=B["routes_crossing_omitted"], omission_len_in_omitted_m=B["len_in_omitted_m"],
                         delta_len_vs_baseline_retained_m=B["len_in_omitted_m"] - A_keep["len_in_omitted_m"]))
        ok = B["routes_crossing_omitted"] == int(fp.loc[r, "routes_crossing_omitted"]) and abs(B["len_in_omitted_m"] - float(fp.loc[r, "len_in_omitted_m"])) < 0.01
        V.append(dict(id=f"X01 {r}", status="PASS" if ok else "FAIL", name="omission-run exposure reproduces footprint_eval summary", detail=f"{B['routes_crossing_omitted']} / {B['len_in_omitted_m']:.3f}"))
        V.append(dict(id=f"X02 {r}", status="PASS" if A_keep["routes"] == len(keep) and B["routes"] == len(keep) else "FAIL", name="retained-target route sets match", detail=f"{A_keep['routes']} vs {len(keep)}"))
    out.mkdir(); S = pd.DataFrame(rows); Vd = pd.DataFrame(V)
    S.to_csv(out / "c1_omitted_footprint_exposure.csv", index=False); Vd.to_csv(out / "c1_exposure_validation.csv", index=False)
    pd.set_option("display.width", 250); print(S.round(2).T.to_string()); print(Vd[["id", "status", "detail"]].to_string(index=False)); print("written:", out)
    sys.exit(0 if (Vd.status == "PASS").all() else 3)
