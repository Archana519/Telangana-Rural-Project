"""dk_stageB_c1_c07.py - facility-route invariance logic for C1 omission runs (versioned replacement for check C07 of dk_stageB_c1_compare.py v1).
Pure decision function + geometry helpers (importable by tests). Does not touch any run output."""
import math
import numpy as np

GEOM_TOL_M = 1e-6      # Hausdorff distance below which two facility routes are treated as identical
COST_TOL = 0.5         # calibration tolerance in ordinal cost units
OPT_TOL = 0.5          # tolerance when checking that the new route is not worse than the old route on the new surface

def classify_facility_change(hausdorff_m, penalty_mult, run_len_in_removed_m, base_len_in_removed_m, calib_err, run_cost_on_run, base_cost_on_run):
    """Returns (status, reason). Status: PASS (unchanged) | INFO (changed AND explained by removed penalty cells) | FAIL (changed without evidence, or evidence inconsistent).
    Rules:
      1. identical geometry -> PASS.
      2. geometry changed:
         a. penalty multiplier <= 1.0 (no penalty in the baseline) -> removed penalty cells cannot exist -> FAIL.
         b. no removed-penalty cell is used by the new route (run_len_in_removed_m <= 0) -> FAIL (no evidence).
         c. cost reconstruction not calibrated (|err| > COST_TOL) -> INFO only with a note that the optimality test was skipped.
         d. calibrated and new route costs more than the old route on the new surface (> OPT_TOL) -> FAIL (planner should not choose a worse route on its own surface).
         e. otherwise INFO (explained)."""
    if hausdorff_m is None or (isinstance(hausdorff_m, float) and math.isnan(hausdorff_m)):
        return "FAIL", "facility route missing in one run"
    if hausdorff_m <= GEOM_TOL_M:
        return "PASS", "facility geometry unchanged"
    if penalty_mult is None or penalty_mult <= 1.0:
        return "FAIL", f"geometry changed (Hausdorff {hausdorff_m:.3f} m) but the baseline has no building penalty (mult={penalty_mult}); no cost-surface cause exists"
    if run_len_in_removed_m is None or run_len_in_removed_m <= 0.0:
        return "FAIL", f"geometry changed (Hausdorff {hausdorff_m:.3f} m) but the new route uses no cell whose penalty was removed"
    if calib_err is None or abs(calib_err) > COST_TOL:
        return "INFO", f"geometry changed; new route uses {run_len_in_removed_m:.2f} m of removed-penalty cells; cost optimality test SKIPPED (calibration error {calib_err})"
    if run_cost_on_run > base_cost_on_run + OPT_TOL:
        return "FAIL", f"new route costs {run_cost_on_run:.3f} on the new surface, more than the old route ({base_cost_on_run:.3f}); inconsistent with least-cost planning"
    return "INFO", (f"geometry changed (Hausdorff {hausdorff_m:.3f} m); new route uses {run_len_in_removed_m:.2f} m of cells whose penalty was removed; "
                    f"cost on the new surface {run_cost_on_run:.3f} <= old route {base_cost_on_run:.3f}")

def make_helpers(cost_raster, buildings_gpkg, cfg_b, cfg_r, omitted_ids):
    import geopandas as gpd, pandas as pd, rasterio
    from rasterio.features import rasterize
    with rasterio.open(cost_raster) as s:
        cost = s.read(1).astype(float); tr = s.transform; shp = s.shape
        if s.nodata is not None: cost[cost == s.nodata] = np.nan
    bl = gpd.read_file(buildings_gpkg, layer="buildings"); bl["cid"] = pd.to_numeric(bl.cand_id, errors="coerce")
    def surface(c, omitted):
        q = c["building_quality"].split(","); sub = bl[bl.quality_class.isin(q) & ~bl.cid.isin(omitted)]
        m = rasterize([(g, 1) for g in sub.geometry], out_shape=shp, transform=tr, fill=0, dtype="uint8").astype(bool) if len(sub) and c["building_mult"] != 1.0 else np.zeros(shp, bool)
        return np.where(m, cost * c["building_mult"], cost), m
    SB, MB = surface(cfg_b, set()); SR, MR = surface(cfg_r, set(omitted_ids))
    def cell(x, y): return int((y - tr.f) // tr.e), int((x - tr.c) // tr.a)
    def is_centre(p):
        fx, fy = (p[0] - tr.c) / tr.a, (p[1] - tr.f) / tr.e
        return abs(fx - math.floor(fx) - 0.5) < 1e-6 and abs(fy - math.floor(fy) - 0.5) < 1e-6
    def route_cost(g, S):
        pts = list(g.coords); a0, a1 = 0, len(pts); sc = 0.0
        if not is_centre(pts[0]) and len(pts) > 1: sc = math.hypot(pts[1][0] - pts[0][0], pts[1][1] - pts[0][1]); a0 = 1
        if len(pts) - a0 > 1 and not is_centre(pts[-1]): a1 = len(pts) - 1
        core = pts[a0:a1]; tot = 0.0
        for p, q in zip(core[:-1], core[1:]):
            (r1, c1), (r2, c2) = cell(*p), cell(*q); tot += 0.5 * (S[r1, c1] + S[r2, c2]) * math.hypot(q[0] - p[0], q[1] - p[1])
        r0, c0 = cell(*core[0]); return tot + sc * S[r0, c0]
    def len_in(g, M):
        pts = list(g.coords); L = 0.0
        for p, q in zip(pts[:-1], pts[1:]):
            r1, c1 = cell(*p); L += math.hypot(q[0] - p[0], q[1] - p[1]) if M[r1, c1] else 0.0
        return L
    return dict(SB=SB, SR=SR, removed=MB & ~MR, route_cost=route_cost, len_in=len_in)
