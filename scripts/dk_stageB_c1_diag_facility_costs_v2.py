#!/usr/bin/env python
"""dk_stageB_c1_diag_facility_costs.py - READ-ONLY cost cross-evaluation of facility routes between a baseline run and a C1 omission run.
Rebuilds both cost surfaces (base cost raster x building-penalty mask), and evaluates BOTH routes on BOTH surfaces with the planner's edge rule
(edge cost = 0.5*(c_u+c_v)*step length). First CALIBRATES against the costs reported in each run; if calibration fails, the rest is NOT trustworthy.
Writes ONE new folder <stageb-root>\\_c1_diag_facility_costs_<label>."""
import argparse, json, sys, math
from pathlib import Path
import numpy as np, pandas as pd, geopandas as gpd, rasterio
from rasterio.features import rasterize
ap = argparse.ArgumentParser()
ap.add_argument("--stageb-root", required=True); ap.add_argument("--label", required=True)
ap.add_argument("--baseline", required=True); ap.add_argument("--run", required=True)
ap.add_argument("--buildings", required=True); ap.add_argument("--cost-raster", required=True)
a = ap.parse_args(); root = Path(a.stageb_root); out = root / f"_c1_diag_facility_costs_{a.label}"
if out.exists(): print("STOP: exists", out); sys.exit(1)
cfg = {k: json.loads((root / v / "config_stageB.json").read_text())["args"] for k, v in dict(b=a.baseline, r=a.run).items()}
with rasterio.open(a.cost_raster) as s:
    cost = s.read(1).astype(float); tr = s.transform; shp = s.shape
    if s.nodata is not None: cost[cost == s.nodata] = np.nan
bl = gpd.read_file(a.buildings, layer="buildings"); bl["cid"] = pd.to_numeric(bl.cand_id, errors="coerce")
om = set(pd.read_csv(root / a.run / "perturbation_log.csv").cand_id.astype(int))
def surface(c, omitted):
    q = c["building_quality"].split(","); sub = bl[bl.quality_class.isin(q) & ~bl.cid.isin(omitted)]
    m = rasterize([(g, 1) for g in sub.geometry], out_shape=shp, transform=tr, fill=0, dtype="uint8").astype(bool) if len(sub) else np.zeros(shp, bool)
    return np.where(m, cost * c["building_mult"], cost), m
SB, MB = surface(cfg["b"], set()); SR, MR = surface(cfg["r"], om)
def cell(x, y): return int((y - tr.f) // tr.e), int((x - tr.c) // tr.a)
def is_centre(p):
    fx, fy = (p[0] - tr.c) / tr.a, (p[1] - tr.f) / tr.e
    return abs(fx - math.floor(fx) - 0.5) < 1e-6 and abs(fy - math.floor(fy) - 0.5) < 1e-6
def route_cost(g, S):
    """Planner rule (plan_network_v2.make_route): cost = sum over CELL-TO-CELL edges of 0.5*(c_u+c_v)*step + start_snap_m * c(first cell).
    The END connector (last cell centre -> snap point on the network) is NOT charged. Connectors = leading/trailing vertices that are not cell centres."""
    pts = list(g.coords); a0, a1 = 0, len(pts)
    start_conn = 0.0
    if not is_centre(pts[0]) and len(pts) > 1:
        start_conn = math.hypot(pts[1][0] - pts[0][0], pts[1][1] - pts[0][1]); a0 = 1
    if len(pts) - a0 > 1 and not is_centre(pts[-1]): a1 = len(pts) - 1
    core = pts[a0:a1]; tot = 0.0; L = 0.0
    for p, q in zip(core[:-1], core[1:]):
        (r1, c1), (r2, c2) = cell(*p), cell(*q); s_ = math.hypot(q[0] - p[0], q[1] - p[1]); tot += 0.5 * (S[r1, c1] + S[r2, c2]) * s_; L += s_
    r0, c0 = cell(*core[0]); tot += start_conn * S[r0, c0]
    return tot, L
def pen_len(g, M):
    pts = list(g.coords); L = 0.0
    for p, q in zip(pts[:-1], pts[1:]):
        r1, c1 = cell(*p); L += math.hypot(q[0] - p[0], q[1] - p[1]) if M[r1, c1] else 0.0
    return L
fb = gpd.read_file(root / a.baseline / "routes.gpkg", layer="routes_network_facilities").set_index("target_id")
fr = gpd.read_file(root / a.run / "routes.gpkg", layer="routes_network_facilities").set_index("target_id")
rows = []
for t in fb.index:
    gb, gr = fb.loc[t, "geometry"], fr.loc[t, "geometry"]
    cbb, Lb = route_cost(gb, SB); cbr, _ = route_cost(gb, SR); crb, Lr = route_cost(gr, SB); crr, _ = route_cost(gr, SR)
    rows.append(dict(facility=t, base_len=fb.loc[t, "len_m"], run_len=fr.loc[t, "len_m"], base_reported_cost=fb.loc[t, "cost"], run_reported_cost=fr.loc[t, "cost"],
                     calib_base_route_on_base_surface=cbb, calib_run_route_on_run_surface=crr,
                     calib_err_base=cbb - fb.loc[t, "cost"], calib_err_run=crr - fr.loc[t, "cost"],
                     base_route_on_run_surface=cbr, run_route_on_base_surface=crb,
                     base_route_len_in_omitted_penalty_cells_m=pen_len(gb, MB & ~MR), run_route_len_in_omitted_penalty_cells_m=pen_len(gr, MB & ~MR),
                     base_route_len_in_remaining_penalty_m=pen_len(gb, MR), run_route_len_in_remaining_penalty_m=pen_len(gr, MR)))
D = pd.DataFrame(rows); out.mkdir(parents=True); D.to_csv(out / "facility_cost_crossevaluation.csv", index=False)
cal = float(D[["calib_err_base", "calib_err_run"]].abs().max().max())
txt = [f"cells penalised in baseline surface: {int(MB.sum())}; in omission surface: {int(MR.sum())}; cells whose penalty was removed: {int((MB & ~MR).sum())}",
       f"CALIBRATION max |reconstructed - reported| = {cal:.4f} cost units ({'OK' if cal < 0.5 else 'NOT OK - do not trust the cross-evaluation'})", "", D.round(3).T.to_string()]
(out / "diagnosis_costs.txt").write_text("\n".join(txt)); print("\n".join(txt)); print("written:", out)
sys.exit(0 if cal < 0.5 else 3)
