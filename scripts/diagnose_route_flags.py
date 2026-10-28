"""diagnose_route_flags.py - READ-ONLY. For chosen routes in a plan_network_v2 run, print every vertex and every flagged sample
with its raster row/col and the raw value in each constraint raster, so a planner/audit disagreement can be located exactly."""
import argparse, math, os
import numpy as np, geopandas as gpd, rasterio
ROOT = r"D:\Telangana_Rural_Project\Siddipet\Damarakunta"
d = lambda *x: os.path.join(ROOT, *x)
ap = argparse.ArgumentParser()
ap.add_argument("--run-dir", required=True)
ap.add_argument("--targets", nargs="+", default=["C12", "C13"])
ap.add_argument("--layer", default="routes_network_aware")
ap.add_argument("--cost", default=d("aligned", "damarakunta_cost_surface_10m.tif"))
ap.add_argument("--prohibited", default=d("aligned", "damarakunta_prohibited_mask_10m.tif"))
ap.add_argument("--slope", default=d("aligned", "damarakunta_slope_10m.tif"))
ap.add_argument("--worldcover", default=d("aligned", "damarakunta_worldcover_10m.tif"))
ap.add_argument("--sample-m", type=float, default=0.5)
a = ap.parse_args()
R, nod = {}, {}
for k, p in (("cost", a.cost), ("prohib", a.prohibited), ("slope", a.slope), ("wcover", a.worldcover)):
    with rasterio.open(p) as s:
        R[k] = s.read(1); nod[k] = s.nodata
        if k == "cost": T, shape, crs = s.transform, s.shape, s.crs
print("grid", shape, "transform", tuple(T)[:6], "crs", crs, "nodata", nod)
def cell(x, y): return int(math.floor((y - T.f) / T.e)), int(math.floor((x - T.c) / T.a))
def vals(r, c):
    if not (0 <= r < shape[0] and 0 <= c < shape[1]): return "OUTSIDE"
    return {k: (float(R[k][r, c]) if np.isfinite(R[k][r, c]) else "nan") for k in R}
def flags(v):
    if v == "OUTSIDE": return ["outside_grid"]
    f = []
    cv = v["cost"]
    if cv == "nan" or cv == nod["cost"] or cv <= 0: f.append("cost_invalid")
    if v["prohib"] not in ("nan",) and v["prohib"] > 0: f.append("prohibited")
    if v["slope"] not in ("nan",) and v["slope"] > 10: f.append("slope>10")
    if v["wcover"] == 80: f.append("water")
    return f
g = gpd.read_file(os.path.join(a.run_dir, "network_v2.gpkg"), layer=a.layer)
for t in a.targets:
    rows = g[g.target == t]
    if rows.empty: print("\nno route for", t); continue
    ln = rows.iloc[0].geometry; co = list(ln.coords)
    print(f"\n=== {a.layer} {t}: length {ln.length:.1f} m, {len(co)} vertices (segment 0 and last = connectors)")
    for i, (x, y) in enumerate(co):
        r, c = cell(x, y); v = vals(r, c)
        print(f" v{i:<3} x={x:.2f} y={y:.2f} row={r} col={c} cellctr=({T.c+(c+.5)*T.a:.1f},{T.f+(r+.5)*T.e:.1f}) {flags(v) or 'ok'} {v}")
    seen = set()
    for k, ((x0, y0), (x1, y1)) in enumerate(zip(co, co[1:])):
        L = math.hypot(x1 - x0, y1 - y0); n = max(1, int(math.ceil(L / a.sample_m)))
        for j in range(n):
            f_ = (j + .5) / n; x, y = x0 + f_ * (x1 - x0), y0 + f_ * (y1 - y0); r, c = cell(x, y)
            fl = flags(vals(r, c))
            if fl and (k, r, c) not in seen:
                seen.add((k, r, c)); print(f"  seg{k} flagged cell row={r} col={c} {fl} {vals(r, c)}")
