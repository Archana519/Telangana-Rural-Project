"""Re-run the EXISTING V4 route generator with candidate buildings burned into a COPY of WorldCover
as class 50 (built-up). Original V4 outputs and original WorldCover are never modified.
Candidate buildings are UNVERIFIED model predictions; routes are unverified planning alternatives."""
import argparse, hashlib, importlib.util, sys
from pathlib import Path
import numpy as np, geopandas as gpd, rasterio, fiona
from rasterio.features import rasterize

ROOT = Path(r"D:\Telangana_Rural_Project\Siddipet\Damarakunta")
V4_SCRIPT = Path(r"D:\Telangana_Rural_Project\scripts\reconstruct_damarakunta_routes_v4.py")
WC = ROOT / "aligned" / "damarakunta_worldcover_10m.tif"
CAND = ROOT / "results" / "v6_buildings" / "candidate_buildings_full.gpkg"
V4_GPKG = ROOT / "results" / "damarakunta_routes_v4.gpkg"
CRS, BUILT = "EPSG:32644", 50

ap = argparse.ArgumentParser()
ap.add_argument("--tag", default="burnin")
ap.add_argument("--min-area-m2", type=float, default=10.0)
ap.add_argument("--buffer-m", type=float, default=0.0)
ap.add_argument("--center-only", action="store_true",
                help="burn only cells whose centre is inside a footprint (default: any cell touched)")
a = ap.parse_args()

out_dir = ROOT / "results" / "v6_buildings" / f"routes_{a.tag}"
if out_dir.exists() and any(out_dir.iterdir()):
    sys.exit(f"{out_dir} already has files; choose a new --tag")
out_dir.mkdir(parents=True, exist_ok=True)

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()

before = {p: sha(p) for p in (V4_GPKG, WC)}

with rasterio.open(WC) as s:
    wc, prof = s.read(1), s.profile.copy()
    transform, shape = s.transform, wc.shape
cand = gpd.read_file(CAND).to_crs(CRS)
cand = cand[cand.area_m2 >= a.min_area_m2].reset_index(drop=True)
geoms = cand.geometry.buffer(a.buffer_m) if a.buffer_m > 0 else cand.geometry
mask = rasterize([(g, 1) for g in geoms], out_shape=shape, transform=transform,
                 fill=0, all_touched=not a.center_only, dtype="uint8").astype(bool)
orig50 = int((wc == BUILT).sum())
print(f"candidates burned: {len(cand)} | original class-50 cells: {orig50} | "
      f"cells burned: {int(mask.sum())} | newly built-up cells: {int((mask & (wc != BUILT)).sum())}")
u, c = np.unique(wc[mask], return_counts=True)
print("original WorldCover classes under burned cells:", {int(k): int(v) for k, v in zip(u, c)})
wc_new = wc.copy()
wc_new[mask] = BUILT
new_wc = out_dir / "damarakunta_worldcover_10m_buildings.tif"
with rasterio.open(new_wc, "w", **prof) as d:
    d.write(wc_new, 1)

spec = importlib.util.spec_from_file_location("v4mod", V4_SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
patch = dict(WORLDCOVER_PATH=new_wc, OUT_GPKG=out_dir / "routes_v4style.gpkg",
             OUT_CSV=out_dir / "routes_v4style_comparison.csv",
             OUT_CHECKS=out_dir / "routes_v4style_facility_checks.csv",
             OUT_README=out_dir / "routes_v4style_README.txt")
for k, v in patch.items():
    if not hasattr(mod, k):
        sys.exit(f"V4 script has no constant {k}; stopping")
    setattr(mod, k, v)
print("\n===== running existing V4 main() on building-burned WorldCover =====")
mod.main()
print("===== V4 main() finished =====\n")

after = {p: sha(p) for p in before}
for p in before:
    print("UNCHANGED" if before[p] == after[p] else "!!! CHANGED !!!", p)

layers = fiona.listlayers(mod.OUT_GPKG)
new = gpd.read_file(mod.OUT_GPKG, layer="route_alternatives" if "route_alternatives" in layers else layers[0]).to_crs(CRS)
old = gpd.read_file(V4_GPKG, layer="route_alternatives").to_crs(CRS)
for d in (old, new):
    d["facility_id"] = d["facility_id"].astype(str)

def table(df, label):
    rows = []
    for _, r in df.iterrows():
        rows.append(dict(facility_id=r.facility_id, alt=r.get("alternative"),
                         length_m=round(float(r.get("total_geometry_length_m", r.geometry.length)), 1),
                         cost=round(float(r.get("accumulated_cost", np.nan)), 1),
                         builtup_cells=r.get("builtup_cells"),
                         fallback_start=r.get("start_snap_used_fallback"),
                         crosses_cand_bldgs=int(cand.intersects(r.geometry).sum()),
                         intersects_road=r.get("route_intersects_road")))
    t = __import__("pandas").DataFrame(rows)
    print(f"\n{label}:")
    print(t.to_string(index=False))
    return t

table(old, "ORIGINAL V4 routes")
tn = table(new, "NEW routes (buildings burned in)")
print("\nCorridor overlap of each new route with the same-numbered original (share of new length within 10 m of old):")
for _, r in new.iterrows():
    m = old[(old.facility_id == r.facility_id) & (old["alternative"] == r["alternative"])]
    if len(m):
        f = r.geometry.intersection(m.iloc[0].geometry.buffer(10)).length / max(r.geometry.length, 1e-9)
        print(f"  {r.facility_id} alt {r['alternative']}: {f:.0%}")
    else:
        print(f"  {r.facility_id} alt {r['alternative']}: no original with this number")
print(f"\nroute counts: original {len(old)} | new {len(new)}")
tn.to_csv(out_dir / "new_routes_summary.csv", index=False)
print("Outputs in:", out_dir)