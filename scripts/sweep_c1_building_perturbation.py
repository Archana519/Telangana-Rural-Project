"""C1 prototype sweep: perturb the candidate-building layer, burn into a COPY of WorldCover,
re-run the EXISTING V4 generator for each setting, and measure how routes / selected plans change.
Original V4 outputs and WorldCover are hash-checked and never modified.
Perturbations are crude proxies for segmentation error: sensitivity evidence only, not accuracy."""
import argparse, contextlib, hashlib, importlib.util, io, sys, time
from pathlib import Path
import numpy as np, pandas as pd, geopandas as gpd, rasterio, fiona
from rasterio.features import rasterize

ROOT = Path(r"D:\Telangana_Rural_Project\Siddipet\Damarakunta")
V4_SCRIPT = Path(r"D:\Telangana_Rural_Project\scripts\reconstruct_damarakunta_routes_v4.py")
WC = ROOT / "aligned" / "damarakunta_worldcover_10m.tif"
CAND = ROOT / "results" / "v6_buildings" / "candidate_buildings_full.gpkg"
V4_GPKG = ROOT / "results" / "damarakunta_routes_v4.gpkg"
CRS, BUILT = "EPSG:32644", 50

ap = argparse.ArgumentParser()
ap.add_argument("--tag", default="c1sweep")
ap.add_argument("--seeds", type=int, default=5)
ap.add_argument("--overlap-tol-m", type=float, default=10.0)
ap.add_argument("--same-frac", type=float, default=0.5)
a = ap.parse_args()

root = ROOT / "results" / "v6_buildings" / f"sweep_{a.tag}"
if root.exists() and any(root.iterdir()):
    sys.exit(f"{root} already has files; choose a new --tag")
root.mkdir(parents=True, exist_ok=True)

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()
before = {p: sha(p) for p in (V4_GPKG, WC)}

with rasterio.open(WC) as s:
    wc, prof, transform, shape = s.read(1), s.profile.copy(), s.transform, s.shape
cand_all = gpd.read_file(CAND).to_crs(CRS)

def routes_from(path):
    layers = fiona.listlayers(path)
    g = gpd.read_file(path, layer="route_alternatives" if "route_alternatives" in layers else layers[0]).to_crs(CRS)
    g["facility_id"] = g["facility_id"].astype(str)
    return g.reset_index(drop=True)

settings = [
    dict(name="ref_center_min10", group="ref", min_area=10, center=True, buf=0, drop=0, seed=0),
    dict(name="anytouch_min10", group="burn_rule", min_area=10, center=False, buf=0, drop=0, seed=0),
    dict(name="min25", group="min_area", min_area=25, center=True, buf=0, drop=0, seed=0),
    dict(name="min50", group="min_area", min_area=50, center=True, buf=0, drop=0, seed=0),
    dict(name="min100", group="min_area", min_area=100, center=True, buf=0, drop=0, seed=0),
    dict(name="dilate2m", group="dilate", min_area=10, center=True, buf=2.0, drop=0, seed=0),
]
for fr in (0.1, 0.2, 0.3):
    for sd in range(1, a.seeds + 1):
        settings.append(dict(name=f"drop{int(fr*100)}_s{sd}", group=f"drop{int(fr*100)}",
                             min_area=10, center=True, buf=0, drop=fr, seed=sd))

def run(st):
    d = root / st["name"]; d.mkdir()
    c = cand_all[cand_all.area_m2 >= st["min_area"]]
    if st["drop"] > 0:
        rng = np.random.default_rng(st["seed"])
        c = c[rng.random(len(c)) >= st["drop"]]
    geoms = c.geometry.buffer(st["buf"]) if st["buf"] > 0 else c.geometry
    mask = rasterize([(g, 1) for g in geoms], out_shape=shape, transform=transform,
                     fill=0, all_touched=not st["center"], dtype="uint8").astype(bool)
    w = wc.copy(); w[mask] = BUILT
    p = d / "wc.tif"
    with rasterio.open(p, "w", **prof) as dst:
        dst.write(w, 1)
    spec = importlib.util.spec_from_file_location("v4mod_" + st["name"], V4_SCRIPT)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    for k, v in dict(WORLDCOVER_PATH=p, OUT_GPKG=d / "r.gpkg", OUT_CSV=d / "r.csv",
                     OUT_CHECKS=d / "c.csv", OUT_README=d / "r.txt").items():
        setattr(mod, k, v)
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            mod.main()
        return routes_from(mod.OUT_GPKG), int(mask.sum()), len(c), ""
    except Exception as e:
        return None, int(mask.sum()), len(c), repr(e)[:150]

def select(g, rule):
    col = "accumulated_cost" if rule == "min_cost" else "total_geometry_length_m"
    out = {}
    for fid, grp in g.groupby("facility_id"):
        grp = grp[grp[col].notna() & grp.geometry.notna()]
        if len(grp):
            out[fid] = grp.loc[grp[col].idxmin()]
    return out

def overlap(r1, r2):
    t = a.overlap_tol_m
    f1 = r1.geometry.intersection(r2.geometry.buffer(t)).length / max(r1.geometry.length, 1e-9)
    f2 = r2.geometry.intersection(r1.geometry.buffer(t)).length / max(r2.geometry.length, 1e-9)
    return min(f1, f2)

recs, ref_sel = [], {}
def record(name, group, g, cells, ncand, note, first=False):
    for rule in ("min_cost", "min_length"):
        sel = select(g, rule) if g is not None else {}
        if first:
            ref_sel[rule] = sel
        for fid, rr in ref_sel[rule].items():
            if fid in sel:
                ov = overlap(sel[fid], rr)
                recs.append(dict(setting=name, group=group, rule=rule, facility=fid,
                                 chosen_alt=sel[fid]["alternative"],
                                 length_m=float(sel[fid]["total_geometry_length_m"]),
                                 cost=float(sel[fid]["accumulated_cost"]),
                                 overlap_vs_ref=round(ov, 2), changed=bool(ov < a.same_frac),
                                 n_routes=0 if g is None else len(g), cells_burned=cells, n_cands=ncand))
            else:
                recs.append(dict(setting=name, group=group, rule=rule, facility=fid, chosen_alt=None,
                                 length_m=np.nan, cost=np.nan, overlap_vs_ref=np.nan, changed=True,
                                 n_routes=0 if g is None else len(g), cells_burned=cells, n_cands=ncand))

t0 = time.time()
for i, st in enumerate(settings):
    ts = time.time()
    g, cells, ncand, err = run(st)
    if st["name"] == "ref_center_min10":
        if g is None:
            sys.exit("Reference run failed: " + err)
        record(st["name"], st["group"], g, cells, ncand, err, first=True)
        old = routes_from(V4_GPKG)
        record("orig_V4_no_buildings", "orig_V4", old, 0, 0, "")
    else:
        record(st["name"], st["group"], g, cells, ncand, err)
    print(f"[{i+1}/{len(settings)}] {st['name']:<18} cands={ncand:>3} cells_burned={cells:>5} "
          f"routes_found={0 if g is None else len(g):>2} {time.time()-ts:4.1f}s {err}", flush=True)

df = pd.DataFrame(recs)
df.to_csv(root / "sweep_records.csv", index=False)
for rule in ("min_cost", "min_length"):
    d = df[df.rule == rule].copy()
    d["changed"] = d["changed"].astype(float)
    print(f"\n=== selection rule: {rule} (changed = selected route overlaps reference selection < {a.same_frac:.0%})")
    print("share of runs where the selected route differs from the reference run, per facility:")
    print(d.pivot_table(index="facility", columns="group", values="changed", aggfunc="mean").round(2).to_string())
    plan = d.groupby(["group", "setting"]).agg(plan_len=("length_m", "sum"), n_fac=("facility", "nunique"),
                                              n_changed=("changed", "sum"), routes=("n_routes", "first")).reset_index()
    print("plan-level summary per group (4 facilities):")
    print(plan.groupby("group").agg(runs=("setting", "nunique"), mean_fac_changed=("n_changed", "mean"),
                                    plan_len_min=("plan_len", "min"), plan_len_max=("plan_len", "max"),
                                    routes_min=("routes", "min"), routes_max=("routes", "max")).round(1).to_string())
after = {p: sha(p) for p in before}
for p in before:
    print("UNCHANGED" if before[p] == after[p] else "!!! CHANGED !!!", p)
print(f"\nTotal time {time.time()-t0:.0f}s | records: {root / 'sweep_records.csv'}")