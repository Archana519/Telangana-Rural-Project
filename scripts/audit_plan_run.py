"""audit_plan_run.py - READ-ONLY, reproducible audit of a plan_network_v2 run (does not change the run).
Re-derives from the saved route geometries + the source rasters:
  1. hard-constraint violations, split into PATH samples, CONNECTOR samples (first/last segment) and DIAGONAL CORNER-SQUEEZES
  2. total / unique / overlap length per plan, by GEOMETRY (independent of the planner's own bookkeeping)
  3. attachment: where each route really ends (roads vs another route) within a tolerance, and connectivity to the roads
Writes <run-dir>/audit/{audit_summary.json,audit_routes.csv}; refuses to overwrite.
"""
import argparse, json, math, os, sys
from pathlib import Path
import numpy as np, geopandas as gpd, pandas as pd, rasterio
from shapely.geometry import Point
from shapely.ops import unary_union

ROOT = r"D:\Telangana_Rural_Project\Siddipet\Damarakunta"


def main():
    d = lambda *x: os.path.join(ROOT, *x)
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--cost", default=d("aligned", "damarakunta_cost_surface_10m.tif"))
    ap.add_argument("--prohibited", default=d("aligned", "damarakunta_prohibited_mask_10m.tif"))
    ap.add_argument("--slope", default=d("aligned", "damarakunta_slope_10m.tif"))
    ap.add_argument("--slope-limit-deg", type=float, default=10.0)
    ap.add_argument("--worldcover", default=d("aligned", "damarakunta_worldcover_10m.tif"))
    ap.add_argument("--water-class", type=int, default=80)
    ap.add_argument("--roads", default=d("reference", "tgrac_road_network.gpkg"))
    ap.add_argument("--tol-m", type=float, default=1.0, help="geometric tolerance for 'same place' (overlap and attachment)")
    ap.add_argument("--sample-m", type=float, default=0.5)
    a = ap.parse_args()
    run = Path(a.run_dir); out = run / "audit"
    if out.exists():
        sys.exit(f"{out} exists; remove it yourself or audit a different run (nothing overwritten)")

    def load(p, nm):
        if not p or not os.path.exists(p):
            print(f"NOTE: {nm} raster missing -> check skipped"); return None
        with rasterio.open(p) as s:
            arr = s.read(1).astype(float)
            if s.nodata is not None: arr[arr == s.nodata] = np.nan
            return arr, s.transform, s.crs
    C = load(a.cost, "cost"); T, crs, shape = C[1], C[2], C[0].shape
    layers = {"cost_invalid": lambda v: ~(np.isfinite(v) & (v > 0))}
    R = {"cost_invalid": C[0]}
    for nm, p, fn in (("prohibited", a.prohibited, lambda v: np.nan_to_num(v) > 0), ("slope", a.slope, lambda v: np.nan_to_num(v) > a.slope_limit_deg),
                      ("water", a.worldcover, lambda v: v == a.water_class)):
        x = load(p, nm)
        if x is None: continue
        if x[0].shape != shape or x[2] != crs or any(abs(u - v) > 1e-6 for u, v in zip(tuple(x[1])[:6], tuple(T)[:6])):
            print(f"NOTE: {nm} raster grid differs from cost -> skipped"); continue
        layers[nm] = fn; R[nm] = x[0]
    res = abs(T.a)

    def bad_at(x, y):
        c, r = int(math.floor((x - T.c) / T.a)), int(math.floor((y - T.f) / T.e))
        if not (0 <= r < shape[0] and 0 <= c < shape[1]): return ["outside_grid"]
        return [k for k, f in layers.items() if bool(f(np.array([R[k][r, c]]))[0])]

    def passable(r, c):
        return 0 <= r < shape[0] and 0 <= c < shape[1] and not any(bool(f(np.array([R[k][r, c]]))[0]) for k, f in layers.items())

    gp = run / "network_v2.gpkg"
    roads = gpd.read_file(a.roads).to_crs(crs.to_string()); roads = roads[roads.geometry.notna() & ~roads.geometry.is_empty]
    road_u = roads.geometry.union_all()
    summ, rows = {}, []
    for lyr in ("routes_network_aware", "routes_independent", "routes_straight_line"):
        try:
            g = gpd.read_file(gp, layer=lyr)
        except Exception:
            print(f"layer {lyr} absent"); continue
        invalid_geom = int((~g.geometry.is_valid).sum() + g.geometry.is_empty.sum())
        tot = viol_path = viol_conn = squeeze = 0
        geoms = []
        for _, row in g.iterrows():
            ln = row.geometry; geoms.append(ln)
            co = list(ln.coords); tot += ln.length
            vp = vc = sq = 0
            for k, ((x0, y0), (x1, y1)) in enumerate(zip(co, co[1:])):
                L = math.hypot(x1 - x0, y1 - y0); n = max(1, int(math.ceil(L / a.sample_m)))
                conn = (k == 0 or k == len(co) - 2) and lyr != "routes_straight_line"
                diag = abs(abs(x1 - x0) - res) < 1e-6 and abs(abs(y1 - y0) - res) < 1e-6
                for j in range(n):
                    f = (j + .5) / n; b = bad_at(x0 + f * (x1 - x0), y0 + f * (y1 - y0))
                    if b:
                        if conn: vc += 1
                        else: vp += 1
                if diag and not conn:
                    xm, ym = (x0 + x1) / 2, (y0 + y1) / 2
                    c0, r0 = int(math.floor((x0 - T.c) / T.a)), int(math.floor((y0 - T.f) / T.e))
                    c1, r1 = int(math.floor((x1 - T.c) / T.a)), int(math.floor((y1 - T.f) / T.e))
                    if not passable(r0, c1) or not passable(r1, c0): sq += 1
            viol_path += vp; viol_conn += vc; squeeze += sq
            rows.append(dict(plan=lyr, target=row.get("target"), length_m=round(ln.length, 1), path_samples_in_hard=vp,
                             connector_samples_in_hard=vc, diagonal_corner_squeezes=sq))
        total = float(sum(l.length for l in geoms))
        uni = float(unary_union(geoms).length) if geoms else 0.0
        tol_overlap = 0.0
        for i, l in enumerate(geoms):
            if i: tol_overlap += float(l.intersection(unary_union(geoms[:i]).buffer(a.tol_m)).length)
        s = dict(routes=len(g), invalid_or_empty_geometries=invalid_geom, total_len_m=round(total, 1), unique_len_geometric_m=round(uni, 1),
                 overlap_exact_m=round(total - uni, 1), overlap_within_tol_m=round(tol_overlap, 1),
                 hard_samples_on_path=viol_path, hard_samples_on_connectors=viol_conn, diagonal_corner_squeezes=squeeze)
        if lyr == "routes_network_aware":
            tt = g.set_index("target"); att = {}
            for t, ln in zip(g.target, geoms):
                end = Point(ln.coords[-1]); dr = float(end.distance(road_u))
                others = [(float(end.distance(o)), tt.index[i]) for i, o in enumerate(geoms) if tt.index[i] != t]
                do, ot = min(others) if others else (math.inf, None)
                where = "ROAD" if dr <= a.tol_m and dr <= do else (ot if do <= a.tol_m else "NONE_WITHIN_TOL")
                att[t] = dict(declared=str(tt.loc[t, "attach_to"]), inferred=where, d_road=round(dr, 2), d_other=round(do, 2))
            ok = {}
            for t in att:
                cur, seen = t, set()
                while cur not in seen and att.get(cur, {}).get("inferred") not in (None, "NONE_WITHIN_TOL", "ROAD"):
                    seen.add(cur); cur = att[cur]["inferred"]
                ok[t] = att.get(cur, {}).get("inferred") == "ROAD"
            s["attachments_declared_to_other_routes"] = sum(v["declared"] not in ("ROAD", "") for v in att.values())
            s["attachments_inferred_to_other_routes"] = sum(v["inferred"] not in ("ROAD", "NONE_WITHIN_TOL") for v in att.values())
            s["declared_vs_inferred_mismatch"] = {t: v for t, v in att.items() if v["declared"] != v["inferred"]}
            s["routes_connected_to_roads_by_geometry"] = sum(ok.values()); s["routes_not_connected"] = [t for t, v in ok.items() if not v]
        summ[lyr] = s
    out.mkdir(parents=True)
    (out / "audit_summary.json").write_text(json.dumps(dict(tol_m=a.tol_m, rasters_checked=list(layers), summary=summ), indent=2, default=str), encoding="utf-8")
    pd.DataFrame(rows).to_csv(out / "audit_routes.csv", index=False)
    print(json.dumps(summ, indent=1, default=str)); print("\nWrote", out)
    print("Interpretation: path samples in hard cells = TRUE violation of the cell path; connector samples = start/end stubs (target->first cell, last cell->network);",
          "corner squeezes = valid 8-connected step between two blocked cells (zero-width gap). Anything else visible in QGIS is rendering/generalisation.")

if __name__ == "__main__":
    main()
