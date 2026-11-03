#!/usr/bin/env python
"""dk_stageB_c1_diag_facility.py - READ-ONLY diagnosis of facility-route differences between a baseline run and a C1 omission run.
Writes ONE new folder <stageb-root>\\_c1_diag_facility_<label>. Tests the hypothesis that facility routes change because omitted footprints were part of
the building-penalty layer (cost surface), not because of a bug. Does not change any existing file."""
import argparse, json, sys
from pathlib import Path
import numpy as np, pandas as pd, geopandas as gpd
from shapely.ops import unary_union
ap = argparse.ArgumentParser()
ap.add_argument("--stageb-root", required=True); ap.add_argument("--label", required=True)
ap.add_argument("--baseline", required=True); ap.add_argument("--run", required=True)
ap.add_argument("--buildings", required=True, help="original footprint layer used by the runner (buildings_v8_full.gpkg)")
a = ap.parse_args(); root = Path(a.stageb_root); out = root / f"_c1_diag_facility_{a.label}"
if out.exists(): print("STOP: exists", out); sys.exit(1)
b, r = root / a.baseline, root / a.run
cb, cr = json.loads((b / "config_stageB.json").read_text())["args"], json.loads((r / "config_stageB.json").read_text())["args"]
fb = gpd.read_file(b / "routes.gpkg", layer="routes_network_facilities"); fr = gpd.read_file(r / "routes.gpkg", layer="routes_network_facilities")
sb = pd.read_csv(b / "facility_status.csv", dtype={"facility_id": str}).set_index("facility_id"); sr = pd.read_csv(r / "facility_status.csv", dtype={"facility_id": str}).set_index("facility_id")
log = pd.read_csv(r / "perturbation_log.csv"); om = set(log.cand_id.astype(int))
bl = gpd.read_file(a.buildings); bl["cid"] = pd.to_numeric(bl["cand_id"], errors="coerce")
omf = bl[bl.cid.isin(om)]
print("route layer columns:", list(fb.columns))
idcol = next((c for c in ["facility_id", "target_id"] if c in fb.columns), None)
rows = []
for fid in sb.index:
    gb = fb[fb[idcol].astype(str).str.contains(str(fid))] if idcol else fb
    gr = fr[fr[idcol].astype(str).str.contains(str(fid))] if idcol else fr
    g1 = unary_union(list(gb.geometry)) if len(gb) else None; g2 = unary_union(list(gr.geometry)) if len(gr) else None
    haus = g1.hausdorff_distance(g2) if g1 is not None and g2 is not None else np.nan
    d_om = g1.distance(unary_union(list(omf.geometry))) if g1 is not None and len(omf) else np.nan
    n_cross = int(sum(g1.intersects(x) for x in omf.geometry)) if g1 is not None else 0
    rows.append(dict(facility_id=fid, name=sb.loc[fid, "facility_name"], base_len_m=sb.loc[fid, "len_m"], run_len_m=sr.loc[fid, "len_m"] if fid in sr.index else np.nan,
                     base_cost=sb.loc[fid, "cost"], run_cost=sr.loc[fid, "cost"] if fid in sr.index else np.nan, base_attach=sb.loc[fid, "attach_class"], run_attach=sr.loc[fid, "attach_class"] if fid in sr.index else "",
                     hausdorff_m=haus, geometry_identical=bool(haus == 0) if haus == haus else None, baseline_route_to_nearest_omitted_footprint_m=d_om, n_omitted_footprints_crossed_by_baseline_route=n_cross))
D = pd.DataFrame(rows); D["len_diff_m"] = D.run_len_m - D.base_len_m; D["cost_diff"] = D.run_cost - D.base_cost
out.mkdir(parents=True); D.to_csv(out / "facility_route_diff.csv", index=False)
pen_b = (cb["building_mult"], cb["building_quality"]); pen_r = (cr["building_mult"], cr["building_quality"])
txt = [f"baseline={a.baseline} penalty(mult,classes)={pen_b}", f"run={a.run} penalty(mult,classes)={pen_r}", f"omitted footprints={len(omf)} (classes: {omf.get('quality_class', pd.Series(dtype=str)).value_counts().to_dict()})", "",
       D.round(3).to_string(index=False), "",
       "READING: if a facility route changed, and either it crossed/neighbours an omitted footprint or the penalty multiplier is >1 for the omitted class, the change is a legitimate cost-surface effect: the omission also removes that footprint's penalty. If a route changed with NO omitted footprint nearby and no penalty, the invariance check exposes a real problem."]
(out / "diagnosis.txt").write_text("\n".join(txt)); print("\n".join(txt)); print("written:", out)
