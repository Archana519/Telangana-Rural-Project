"""dk_stageB_c2_ablation_summary_v1.py - READ-ONLY summary of the K x passes ablation runs and a runner-version reproduction check.
Reads existing run folders; writes only a NEW folder _c2_<label>. Nothing is re-run."""
import argparse, json, sys
from pathlib import Path
import numpy as np, pandas as pd, geopandas as gpd
ap = argparse.ArgumentParser(); ap.add_argument("--stageb-root", required=True); ap.add_argument("--label", required=True)
ap.add_argument("--reference", required=True, help="existing baseline run (e.g. S2_fac_C0_s25_v11)"); ap.add_argument("--same-config-control", required=True, help="K3_P2 run (same settings as reference)")
ap.add_argument("--runs", nargs="+", required=True)
a = ap.parse_args(); root = Path(a.stageb_root); out = root / f"_c2_{a.label}"
if out.exists(): sys.exit(f"refusing: {out} already exists")
def ld(r):
    d = root / r; return dict(ev=json.loads((d / "evaluation_summary.json").read_text()), cfg=json.loads((d / "config_stageB.json").read_text()), sel=pd.read_csv(d / "selection_summary.csv", dtype={"target_id": str}),
                              rh=gpd.read_file(d / "routes.gpkg", layer="routes_network_houses"), rf=gpd.read_file(d / "routes.gpkg", layer="routes_network_facilities"))
names = list(dict.fromkeys([a.reference, a.same_config_control] + a.runs)); L = {r: ld(r) for r in names}
def geom_same(r1, r2, layer):
    g1, g2 = L[r1][layer].set_index("target_id").geometry, L[r2][layer].set_index("target_id").geometry
    common = g1.index.intersection(g2.index); same = sum(1 for t in common if g1[t].hausdorff_distance(g2[t]) <= 1e-6)
    return same, len(common), len(g1), len(g2)
rows = []; V = []
for r in names:
    e, c, s = L[r]["ev"], L[r]["cfg"]["args"], L[r]["sel"]; hp, ind = e["houses_primary"], e["houses_independent_baseline"]; h = s[s.scope == "house_phase"]
    rows.append(dict(run=r, version=L[r]["cfg"].get("version"), k=c.get("k"), passes=c.get("passes"), houses_routed=len(h), house_unique_len_m=hp["unique_len_m"], house_total_len_m=hp["total_len_m"],
                     indep_unique_len_m=ind["unique_len_m"], credit_pct=100 * (ind["unique_len_m"] - hp["unique_len_m"]) / ind["unique_len_m"], facility_unique_len_m=e["facilities_primary"]["unique_len_m"],
                     max_chain_depth=e["connectivity"]["max_chain_depth"], houses_stageA_alt1=int((h["mode"] == "stageA_alt1").sum()), houses_stageA_alt2plus=int(h["mode"].astype(str).str.startswith("stageA_alt").sum() - (h["mode"] == "stageA_alt1").sum()),
                     houses_attach_network=int((h["mode"] == "attach_network").sum()), max_alt_rank_used=int(pd.to_numeric(s.alt_rank_used).max())))
    for lay, nm in (("rh", "houses"), ("rf", "facilities")):
        same, nc, n1, n2 = geom_same(r, a.same_config_control, lay)
        rows[-1][f"{nm}_geometry_identical_to_control"] = f"{same}/{nc}"
T = pd.DataFrame(rows)
# reproduction check: same-config control (current runner) vs the existing reference run
ref, ctl = a.reference, a.same_config_control
for lay, nm in (("rh", "houses"), ("rf", "facilities")):
    same, nc, n1, n2 = geom_same(ref, ctl, lay); V.append(dict(id=f"R01 {nm}", status="PASS" if same == nc == n1 == n2 else "FAIL", name=f"{ctl} routes identical to {ref} ({nm})", detail=f"{same}/{nc} identical; counts {n1} vs {n2}"))
for k_ in ("unique_len_m", "total_len_m"):
    d = abs(L[ref]["ev"]["houses_primary"][k_] - L[ctl]["ev"]["houses_primary"][k_]); V.append(dict(id=f"R02 {k_}", status="PASS" if d < 1e-6 else "FAIL", name="house unique/total length equal to reference", detail=f"abs diff {d:.9f} m"))
V.append(dict(id="R03", status="PASS" if L[ref]["cfg"]["args"].get("k") == L[ctl]["cfg"]["args"].get("k") and L[ref]["cfg"]["args"].get("passes") == L[ctl]["cfg"]["args"].get("passes") else "FAIL", name="control uses the same k and passes as the reference", detail=""))
out.mkdir(); T.to_csv(out / "c2_ablation_summary.csv", index=False); Vd = pd.DataFrame(V); Vd.to_csv(out / "c2_ablation_validation.csv", index=False)
pd.set_option("display.width", 260); print(T.round(3).T.to_string()); print(Vd[["id", "status", "detail"]].to_string(index=False)); print("written:", out)
sys.exit(0 if (Vd.status == "PASS").all() else 3)
