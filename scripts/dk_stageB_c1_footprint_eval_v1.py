"""dk_stageB_c1_footprint_eval_v1.py - READ-ONLY re-evaluation of route/footprint crossings against ONE fixed footprint set.
Why: the runner (v1.3) computes 'routes crossing other buildings' against the run's own reduced footprint set (omitted footprints removed),
so omission runs are not comparable with the baseline on that metric. This script scores every run's saved routes against the FULL baseline footprint set
and splits crossings into retained vs omitted footprints. Never modifies run folders; writes only to a NEW folder _c1_<label>."""
import argparse, sys, json
from pathlib import Path
import numpy as np, pandas as pd, geopandas as gpd

def eval_routes(routes, bld, omitted_ids):
    """routes: GeoDataFrame(cand_id, geometry). bld: GeoDataFrame(cand_id, geometry) = FULL footprint set.
    Returns per-route DataFrame. 'other' = any footprint whose cand_id != the route's own cand_id."""
    si = bld.sindex; om = set(int(x) for x in omitted_ids); rows = []
    bid = bld.cand_id.astype(int).to_numpy()
    for r in routes.itertuples():
        g = r.geometry; own = int(r.cand_id); lk = lo = 0.0; nk = no = 0
        if g is not None and not g.is_empty:
            for p in si.query(g, predicate="intersects"):
                b = int(bid[int(p)])
                if b == own: continue
                L = g.intersection(bld.geometry.iloc[int(p)]).length
                if L <= 1e-6: continue
                if b in om: lo += L; no += 1
                else: lk += L; nk += 1
        rows.append(dict(cand_id=own, route_len_m=float(g.length) if g is not None else 0.0, len_other_retained_m=lk, n_other_retained=nk, len_other_omitted_m=lo, n_other_omitted=no))
    return pd.DataFrame(rows, columns=["cand_id", "route_len_m", "len_other_retained_m", "n_other_retained", "len_other_omitted_m", "n_other_omitted"])

def summarise(df):
    n = len(df); full_len = df.len_other_retained_m + df.len_other_omitted_m
    return dict(routed=n,
                routes_crossing_retained=int((df.n_other_retained > 0).sum()), len_in_retained_m=float(df.len_other_retained_m.sum()),
                routes_crossing_omitted=int((df.n_other_omitted > 0).sum()), len_in_omitted_m=float(df.len_other_omitted_m.sum()),
                routes_crossing_any_full=int(((df.n_other_retained + df.n_other_omitted) > 0).sum()), len_in_any_full_m=float(full_len.sum()),
                crossing_any_full_per_routed=float(((df.n_other_retained + df.n_other_omitted) > 0).sum() / n) if n else float("nan"))

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--stageb-root", required=True); ap.add_argument("--buildings", required=True); ap.add_argument("--label", required=True)
    ap.add_argument("--baseline", required=True); ap.add_argument("--runs", nargs="+", required=True)
    ap.add_argument("--ref-comparison", required=True, help="existing c1_scenario_comparison.csv used ONLY to cross-check reproduction of the reported numbers")
    a = ap.parse_args(); root = Path(a.stageb_root); out = root / f"_c1_{a.label}"
    if out.exists(): sys.exit(f"refusing: {out} already exists")
    ref = pd.read_csv(a.ref_comparison).set_index("run")
    bld = gpd.read_file(a.buildings, layer="buildings"); bld["cand_id"] = pd.to_numeric(bld.cand_id).astype(int)
    out.mkdir(); S, P, V = [], [], []
    for r in [a.baseline] + a.runs:
        rt = gpd.read_file(root / r / "routes.gpkg", layer="routes_network_houses"); rt = rt[rt.scope.astype(str).str.startswith("network_primary")]
        b = bld.to_crs(rt.crs) if bld.crs != rt.crs else bld
        pl = root / r / "perturbation_log.csv"; om = []
        if r != a.baseline and pl.exists():
            d = pd.read_csv(pl); om = d[d.action.astype(str).str.startswith("OMIT")].cand_id.astype(int).tolist()
        df = eval_routes(rt, b, om); df.insert(0, "run", r); P.append(df)
        s = summarise(df); s.update(run=r, role="BASELINE" if r == a.baseline else "OMISSION", omitted=len(om)); S.append(s)
        # reproduction check: retained-only numbers must equal the previously reported (run-own-footprint) metrics
        e1 = int(ref.loc[r, "net_routes_crossing_other_bldg"]); e2 = float(ref.loc[r, "net_len_in_other_bldg_m"])
        ok = s["routes_crossing_retained"] == e1 and abs(s["len_in_retained_m"] - e2) < 0.01
        V.append(dict(id=f"F01 {r}", status="PASS" if ok else "FAIL", name="retained-footprint metrics reproduce the previously reported run metrics",
                      detail=f"count {s['routes_crossing_retained']} vs {e1}; len {s['len_in_retained_m']:.3f} vs {e2:.3f}"))
        V.append(dict(id=f"F02 {r}", status="PASS" if s["routed"] == int(ref.loc[r, "routed"]) else "FAIL", name="routed count equals reported", detail=f"{s['routed']} vs {int(ref.loc[r,'routed'])}"))
        if r == a.baseline:
            V.append(dict(id=f"F03 {r}", status="PASS" if s["routes_crossing_omitted"] == 0 and len(om) == 0 else "FAIL", name="baseline has no omitted footprints", detail=""))
    S = pd.DataFrame(S); P = pd.concat(P); Vd = pd.DataFrame(V)
    S.to_csv(out / "c1_footprint_crossings_full_set.csv", index=False); P.to_csv(out / "c1_footprint_crossings_per_route.csv", index=False); Vd.to_csv(out / "c1_footprint_validation.csv", index=False)
    pd.set_option("display.width", 250); print(S.round(3).to_string(index=False)); print(Vd[["id", "status", "detail"]].to_string(index=False)); print("written:", out)
    sys.exit(0 if (Vd.status == "PASS").all() else 3)
