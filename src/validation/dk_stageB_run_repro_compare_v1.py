#!/usr/bin/env python
"""dk_stageB_run_repro_compare_v1.py - READ-ONLY comparison of a reproduced Stage B run folder with an original run folder.

Compares (nothing is modified; a NEW output folder is created, an existing one is never overwritten):
  evaluation_summary.json numeric leaves (abs tol --tol), route_edges.csv (identity of grid edges + len/cost), selection_summary.csv (per scope/target: cand_id, mode, alt_rank_used, len_m, cost),
  scenario_targets.csv, acceptance_tests.csv (status per test_id), baselines.csv, inputs_manifest_stageB.csv (sha256 per role), routes.gpkg geometry per target (only if geopandas is importable).
Differences that are expected (run_key, start time, output paths) are not compared.
"""
import argparse, hashlib, json, sys
from pathlib import Path
import pandas as pd


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def leaves(o, p=""):
    if isinstance(o, dict):
        for k, v in o.items():
            if k in ("run_key",):
                continue
            yield from leaves(v, p + "/" + str(k))
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from leaves(v, f"{p}[{i}]")
    else:
        yield p, o


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--original", required=True)
    ap.add_argument("--repro", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--tol", type=float, default=1e-6)
    ap.add_argument("--geom-tol", type=float, default=0.01)
    a = ap.parse_args()
    o, r, out = Path(a.original), Path(a.repro), Path(a.out)
    if out.exists():
        sys.exit(f"stopping: {out} exists (never overwritten)")
    names = ["evaluation_summary.json", "route_edges.csv", "selection_summary.csv", "scenario_targets.csv", "acceptance_tests.csv", "baselines.csv", "inputs_manifest_stageB.csv", "config_stageB.json", "routes.gpkg"]
    for d in (o, r):
        if not d.is_dir():
            sys.exit(f"stopping: not a folder {d}")
    watched = {}
    for d in (o, r):
        for n in names:
            if (d / n).exists():
                watched[d / n] = sha(d / n)
    R = []

    def add(check, ok, detail=""):
        R.append(dict(check=check, result="MATCH" if ok else "DIFFERENT", detail=detail))

    # config args
    co, cr = json.loads((o / "config_stageB.json").read_text(encoding="utf-8")), json.loads((r / "config_stageB.json").read_text(encoding="utf-8"))
    ao, ar = co["args"], cr["args"]
    dk = sorted(k for k in set(ao) | set(ar) if ao.get(k) != ar.get(k))
    add("config args equal (expected differences: label)", set(dk) <= {"label"}, f"differing args: {dk}; runner versions {co.get('version')} vs {cr.get('version')}; planner sha equal {co.get('planner_sha256') == cr.get('planner_sha256')}")
    # inputs
    mo, mr = pd.read_csv(o / "inputs_manifest_stageB.csv").set_index("role"), pd.read_csv(r / "inputs_manifest_stageB.csv").set_index("role")
    bad = [k for k in mo.index if k in mr.index and mo.loc[k, "sha256"] != mr.loc[k, "sha256"]]
    add("input sha256 per role equal", not bad and set(mo.index) == set(mr.index), f"roles differing: {bad}; roles only in one: {sorted(set(mo.index) ^ set(mr.index))}")
    # evaluation summary
    eo, er = dict(leaves(json.loads((o / "evaluation_summary.json").read_text(encoding="utf-8")))), dict(leaves(json.loads((r / "evaluation_summary.json").read_text(encoding="utf-8"))))
    diffs = []
    for k in sorted(set(eo) | set(er)):
        x, y = eo.get(k, "<missing>"), er.get(k, "<missing>")
        if isinstance(x, (int, float)) and isinstance(y, (int, float)) and not isinstance(x, bool):
            if abs(x - y) > a.tol:
                diffs.append((k, x, y))
        elif x != y:
            diffs.append((k, x, y))
    add(f"evaluation_summary.json leaves equal (abs tol {a.tol:g})", not diffs, f"{len(eo)} leaves; {len(diffs)} differ: {diffs[:8]}")
    for k in ("/houses_primary/unique_len_m", "/houses_primary/total_len_m", "/combined_primary/unique_len_m", "/n_house_targets"):
        add(f"headline {k}", abs(eo.get(k, 0) - er.get(k, 1)) <= a.tol, f"original {eo.get(k)} reproduced {er.get(k)}")
    # edges
    key = ["scope", "route_id", "row_a", "col_a", "row_b", "col_b"]
    eo_, er_ = pd.read_csv(o / "route_edges.csv"), pd.read_csv(r / "route_edges.csv")
    m = eo_.merge(er_, on=key, how="outer", suffixes=("_o", "_r"), indicator=True)
    both = m[m._merge == "both"]
    add("route_edges.csv identical edge sets", (m._merge == "both").all() and len(eo_) == len(er_), f"rows {len(eo_)} vs {len(er_)}; only-original {(m._merge=='left_only').sum()}; only-repro {(m._merge=='right_only').sum()}; max |len diff| {(both.len_m_o-both.len_m_r).abs().max():.3g}; max |cost diff| {(both.cost_o-both.cost_r).abs().max():.3g}")
    # selection
    so, sr = pd.read_csv(o / "selection_summary.csv"), pd.read_csv(r / "selection_summary.csv")
    k2 = ["scope", "target_id"]
    ms = so.merge(sr, on=k2, how="outer", suffixes=("_o", "_r"), indicator=True)
    bs = ms[ms._merge == "both"]
    dif = bs[(bs.cand_id_o.fillna(-1) != bs.cand_id_r.fillna(-1)) | (bs.mode_o != bs.mode_r) | (bs.alt_rank_used_o != bs.alt_rank_used_r) | ((bs.len_m_o - bs.len_m_r).abs() > a.tol) | ((bs.cost_o - bs.cost_r).abs() > a.tol)]
    add("selection_summary.csv per target (cand, mode, alt rank, len, cost)", (ms._merge == "both").all() and dif.empty, f"rows {len(so)} vs {len(sr)}; unmatched {(ms._merge!='both').sum()}; differing targets {len(dif)}; step order equal {bool((bs.step_o == bs.step_r).all())}")
    # targets
    to, tr = pd.read_csv(o / "scenario_targets.csv"), pd.read_csv(r / "scenario_targets.csv")
    add("scenario_targets.csv equal", to.equals(tr), f"rows {len(to)} vs {len(tr)}")
    # tests
    ao_, ar_ = pd.read_csv(o / "acceptance_tests.csv"), pd.read_csv(r / "acceptance_tests.csv")
    mt = ao_[["test_id", "status"]].merge(ar_[["test_id", "status"]], on="test_id", how="outer", suffixes=("_o", "_r"))
    bt = mt[mt.status_o != mt.status_r]
    add("acceptance_tests.csv status per test_id", bt.empty, f"original {ao_.status.value_counts().to_dict()} reproduced {ar_.status.value_counts().to_dict()}; differing: {bt.to_dict('records')[:6]}")
    bo, br = pd.read_csv(o / "baselines.csv"), pd.read_csv(r / "baselines.csv")
    num = [c for c in bo.columns if bo[c].dtype.kind in "fi" and c in br.columns]
    add("baselines.csv numeric columns", bo.shape == br.shape and all(((bo[c].fillna(-9) - br[c].fillna(-9)).abs() <= a.tol).all() for c in num), f"shape {bo.shape} vs {br.shape}")
    # geometry
    try:
        import geopandas as gpd
        go, gr = gpd.read_file(o / "routes.gpkg", layer="routes_network_houses"), gpd.read_file(r / "routes.gpkg", layer="routes_network_houses")
        gm = go.merge(gr[["target_id", "geometry"]], on="target_id", how="outer", suffixes=("_o", "_r"))
        bad = [t for t, g1, g2 in zip(gm.target_id, gm.geometry_o, gm.geometry_r) if g1 is None or g2 is None or not g1.equals_exact(g2, a.geom_tol)]
        add(f"routes.gpkg routes_network_houses geometry per target (equals_exact tol {a.geom_tol} m)", not bad and len(go) == len(gr), f"rows {len(go)} vs {len(gr)}; differing targets {len(bad)}: {bad[:8]}")
    except Exception as e:
        R.append(dict(check="routes.gpkg geometry per target", result="NOT_CHECKED", detail=f"{type(e).__name__}: {e}"))
    out.mkdir(parents=True)
    D = pd.DataFrame(R); D.to_csv(out / "repro_comparison.csv", index=False)
    changed = [str(p) for p, h in watched.items() if sha(p) != h]
    pd.DataFrame([dict(check="inputs unchanged (sha256 before/after)", status="FAIL" if changed else "PASS", detail=f"{len(watched)} files")]).to_csv(out / "readonly_proof.csv", index=False)
    pd.DataFrame([(str(p), h) for p, h in watched.items()], columns=["file", "sha256"]).to_csv(out / "compared_file_hashes.csv", index=False)
    with pd.option_context("display.width", 250, "display.max_colwidth", 200):
        print(D.to_string(index=False))
    print("\ninputs unchanged:", not changed); print("output:", out)
    sys.exit(0 if (D.result != "DIFFERENT").all() and not changed else 1)


if __name__ == "__main__":
    main()
