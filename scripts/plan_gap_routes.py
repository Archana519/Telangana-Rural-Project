"""Two-stage generate-and-select prototype for gap-building clusters + priority facilities.
Stage A: existing V4 search (imported, unmodified) on WorldCover with candidate buildings burned in.
Stage B: greedy selection with shared-edge credit (shared length counted once).
Inputs are UNVERIFIED predictions; outputs are unverified planning alternatives, not roads."""
import argparse, hashlib, importlib.util, sys, time
from pathlib import Path
import numpy as np, pandas as pd, geopandas as gpd, rasterio
from rasterio.features import rasterize
from shapely.geometry import Point, LineString
from shapely.ops import nearest_points, unary_union

ROOT = Path(r"D:\Telangana_Rural_Project\Siddipet\Damarakunta")
V4_SCRIPT = Path(r"D:\Telangana_Rural_Project\scripts\reconstruct_damarakunta_routes_v4.py")
V4_GPKG = ROOT / "results" / "damarakunta_routes_v4.gpkg"
CAND = ROOT / "results" / "v6_buildings" / "candidate_buildings_full.gpkg"
CRS = "EPSG:32644"

ap = argparse.ArgumentParser()
ap.add_argument("--tag", default="gap1")
ap.add_argument("--gap-m", type=float, default=50.0)
ap.add_argument("--cluster-radius-m", type=float, default=20.0)
ap.add_argument("--share-tol-m", type=float, default=3.0)
ap.add_argument("--serve-buffer-m", type=float, default=30.0)
ap.add_argument("--same-tol-m", type=float, default=10.0)
ap.add_argument("--seeds", type=int, default=5)
ap.add_argument("--sweep", action="store_true")
a = ap.parse_args()
GAP, CLR, TOL, SERVE = a.gap_m, a.cluster_radius_m, a.share_tol_m, a.serve_buffer_m

out_dir = ROOT / "results" / "v6_buildings" / f"plan_{a.tag}"
if out_dir.exists() and any(out_dir.iterdir()):
    sys.exit(f"{out_dir} already has files; choose a new --tag")
out_dir.mkdir(parents=True, exist_ok=True)

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()

spec = importlib.util.spec_from_file_location("v4mod", V4_SCRIPT)
v4 = importlib.util.module_from_spec(spec); spec.loader.exec_module(v4)
protected = (V4_GPKG, v4.WORLDCOVER_PATH)
before = {p: sha(p) for p in protected}

cost, transform, crs, shape, _ = v4.read_raster(v4.COST_PATH)
world = v4.read_raster(v4.WORLDCOVER_PATH)[0]
slope = v4.read_raster(v4.SLOPE_PATH)[0]
blocked = v4.read_raster(v4.BLOCKED_PATH)[0].astype(bool)
if not (world.shape == slope.shape == blocked.shape == shape):
    sys.exit("raster grids differ")
facilities = gpd.read_file(v4.FACILITIES_PATH).to_crs(CRS)
roads = gpd.read_file(v4.ROADS_PATH).to_crs(CRS)
roads = roads[roads.geometry.notna() & ~roads.geometry.is_empty]
road_union = roads.geometry.union_all()
road_raster = rasterize([(g, 1) for g in roads.geometry], out_shape=shape, transform=transform,
                        fill=0, all_touched=True, dtype="uint8").astype(bool)
water = world == v4.WATER_CLASS
valid_cost = np.isfinite(cost) & (cost > 0)
valid_slope = np.isfinite(slope) & (slope >= 0) & (slope <= v4.SLOPE_LIMIT_DEG)
road_targets = road_raster & valid_cost & ~blocked & ~water
cand_all = gpd.read_file(CAND).to_crs(CRS)

def prep(cset):
    cset = cset.copy().reset_index(drop=True)
    cset["d_road"] = cset.geometry.distance(road_union)
    merged = unary_union(cset.geometry.buffer(CLR / 2.0).tolist())
    parts = list(merged.geoms) if hasattr(merged, "geoms") else [merged]
    cl = gpd.GeoDataFrame({"cluster_id": range(1, len(parts) + 1)}, geometry=parts, crs=CRS)
    pts = gpd.GeoDataFrame(geometry=cset.geometry.representative_point(), crs=CRS)
    j = gpd.sjoin(pts, cl, how="left", predicate="within")
    j = j[~j.index.duplicated(keep="first")]
    cset["cluster_id"] = j["cluster_id"].reindex(cset.index).fillna(-1).astype(int)
    g = cset.groupby("cluster_id")
    cl = cl.set_index("cluster_id")
    cl["n"] = g.size(); cl["min_d"] = g["d_road"].min(); cl["closest_idx"] = g["d_road"].idxmin()
    return cl.dropna(subset=["n"]).reset_index(), cset

def gen_alts(pt, traversable, fallback_mask):
    r = v4.nearest_cell(traversable, transform, pt.x, pt.y, v4.MAX_SNAP_M)
    fb = False
    if r is None:
        r = v4.nearest_cell(fallback_mask, transform, pt.x, pt.y, v4.MAX_SNAP_M)
        fb = r is not None
    if r is None:
        return [], "NO_START_CELL"
    sr, sc, snap = r
    start = (sr, sc); sp = Point(*v4.cell_xy(transform, sr, sc))
    prior = np.zeros(shape, bool); prev = []; out = []
    for alt in range(1, v4.N_ALTERNATIVES + 1):
        pens = (0.0,) if alt == 1 else v4.ALT_CORRIDOR_PENALTIES
        acc = None
        for pen in pens:
            cells, tc, _ = v4.dijkstra(start, traversable, cost, road_targets,
                                       penalty_corridor=None if alt == 1 else prior, corridor_penalty=pen)
            if cells is None:
                continue
            ov = max((v4.route_overlap_ratio(cells, o) for o in prev), default=0.0)
            if alt > 1 and ov > v4.MAX_ROUTE_OVERLAP_RATIO:
                continue
            acc = (cells, tc); break
        if acc is None:
            continue
        cells, tc = acc
        rl = v4.path_to_line(cells, transform)
        ep = Point(*v4.cell_xy(transform, *cells[-1]))
        rp = nearest_points(ep, road_union)[1]
        line = v4.combine_route_geometry(pt, sp, rl, rp)
        out.append(dict(alt=alt, geom=line, length=float(line.length), cost=float(tc),
                        hits_road=bool(line.intersects(road_union)), fallback=fb))
        prev.append(cells)
        prior |= v4.make_corridor(cells, shape, v4.CORRIDOR_RADIUS)
    return out, ("OK_FALLBACK_START" if fb else "OK")

def marginal(r, net):
    return r["geom"].length if net is None else r["geom"].difference(net.buffer(TOL)).length

def pick(al, net):
    return min(al, key=lambda r: (round(marginal(r, net), 3), r["cost"]))

def select_independent(alts, order):
    return {t: (min(alts[t], key=lambda r: r["length"]) if alts[t] else None) for t in order}

def select_credit(alts, order, passes=2):
    chosen, net = {}, None
    for t in order:
        if not alts[t]:
            chosen[t] = None; continue
        b = pick(alts[t], net); chosen[t] = b
        net = b["geom"] if net is None else unary_union([net, b["geom"]])
    for _ in range(passes):
        for t in order:
            if not alts[t]:
                continue
            others = [chosen[o]["geom"] for o in order if o != t and chosen.get(o)]
            chosen[t] = pick(alts[t], unary_union(others) if others else None)
    return chosen

def unique_len(geoms):
    u, tot = None, 0.0
    for g in sorted(geoms, key=lambda g: g.length):
        tot += g.length if u is None else g.difference(u.buffer(TOL)).length
        u = g if u is None else unary_union([u, g])
    return tot

def metrics(chosen, tmap):
    ch = [(t, r) for t, r in chosen.items() if r]
    geoms = [r["geom"] for _, r in ch]
    sl = sum(g.length for g in geoms)
    ul = unique_len(geoms) if geoms else 0.0
    return dict(routed=len(ch), of=len(chosen), sum_len=round(sl, 1), unique_len=round(ul, 1),
                saving=round(sl - ul, 1),
                fac_routed=sum(1 for t, _ in ch if tmap[t]["kind"] == "FACILITY"),
                cluster_bldgs_served=sum(tmap[t]["n"] for t, _ in ch if tmap[t]["kind"] == "CLUSTER"),
                hits_road=sum(1 for _, r in ch if r["hits_road"]))

def evaluate(cset, center=True, buf=0.0):
    geoms = cset.geometry.buffer(buf) if buf > 0 else cset.geometry
    bm = rasterize([(g, 1) for g in geoms], out_shape=shape, transform=transform, fill=0,
                   all_touched=not center, dtype="uint8").astype(bool)
    built = (world == v4.BUILTUP_CLASS) | bm
    trav = valid_cost & valid_slope & ~blocked & ~built & ~water
    fbm = valid_cost & valid_slope & ~blocked & ~water
    cl, cs = prep(cset)
    tmap = {}
    for _, f in facilities.iterrows():
        tid = "F:" + str(f.get("facility_id"))
        tmap[tid] = dict(kind="FACILITY", pt=f.geometry, n=0, name=str(f.get("facility_name")), d_road=float(f.geometry.distance(road_union)), cid=None)
    gapc = cl[cl.min_d > GAP].sort_values("n", ascending=False)
    for _, c in gapc.iterrows():
        b = cs.loc[int(c.closest_idx)]
        tmap["C%d" % c.cluster_id] = dict(kind="CLUSTER", pt=b.geometry.representative_point(), n=int(c.n),
                                          name="gap cluster", d_road=float(c.min_d), cid=int(c.cluster_id))
    order = [t for t in tmap if tmap[t]["kind"] == "FACILITY"] + [t for t in tmap if tmap[t]["kind"] == "CLUSTER"]
    alts, notes = {}, {}
    for t in order:
        alts[t], notes[t] = gen_alts(tmap[t]["pt"], trav, fbm)
        for r in alts[t]:
            oth = cs if tmap[t]["cid"] is None else cs[cs.cluster_id != tmap[t]["cid"]]
            r["crossed"] = int(oth.intersects(r["geom"]).sum())
    sel_i, sel_c = select_independent(alts, order), select_credit(alts, order)
    base = {}
    for t in order:
        p = tmap[t]["pt"]; rp = nearest_points(p, road_union)[1]
        base[t] = dict(geom=LineString([(p.x, p.y), (rp.x, rp.y)]), alt=0, cost=np.nan, hits_road=True,
                       length=float(p.distance(rp)))
    return dict(tmap=tmap, order=order, alts=alts, notes=notes, sel_i=sel_i, sel_c=sel_c,
                base=base, cs=cs, bmask=int(bm.sum()), gap_cands=cs[cs.d_road > GAP])

t0 = time.time()
ref = evaluate(cand_all[cand_all.area_m2 >= 10], center=True, buf=0.0)
tmap, order = ref["tmap"], ref["order"]
print(f"Reference setting: {len(ref['cs'])} candidates, burn cells {ref['bmask']} (center rule), "
      f"gap threshold {GAP} m, cluster radius {CLR} m")
print(f"Targets: {sum(tmap[t]['kind']=='FACILITY' for t in order)} facilities + "
      f"{sum(tmap[t]['kind']=='CLUSTER' for t in order)} gap clusters")
rows = []
for t in order:
    for r in ref["alts"][t]:
        rows.append(dict(target=t, kind=tmap[t]["kind"], name=tmap[t]["name"], bldgs=tmap[t]["n"],
                         d_to_road_m=round(tmap[t]["d_road"], 1), alt=r["alt"], length_m=round(r["length"], 1),
                         cost=round(r["cost"], 1), hits_road=r["hits_road"], crossed=r["crossed"],
                         start=ref["notes"][t],
                         sel_indep=ref["sel_i"][t] is r, sel_credit=ref["sel_c"][t] is r))
    if not ref["alts"][t]:
        rows.append(dict(target=t, kind=tmap[t]["kind"], name=tmap[t]["name"], bldgs=tmap[t]["n"],
                         d_to_road_m=round(tmap[t]["d_road"], 1), alt=None, start=ref["notes"][t]))
adf = pd.DataFrame(rows)
print("\nStage A alternatives and Stage B selections (reference):")
print(adf.to_string(index=False))
print("\nPlan metrics (reference setting):")
mt = pd.DataFrame({"independent_shortest": metrics(ref["sel_i"], tmap),
                   "credit_greedy": metrics(ref["sel_c"], tmap),
                   "straight_to_road_baseline": metrics(ref["base"], tmap)}).T
print(mt.to_string())
bl_cross = sum(int((ref["cs"][ref["cs"].cluster_id != (tmap[t]["cid"] if tmap[t]["cid"] else -9)].intersects(ref["base"][t]["geom"])).sum()) for t in order)
print(f"candidate buildings touched by straight-line baseline connectors (excluding own cluster): {bl_cross}")
print("selected routes crossing other candidate buildings (credit plan):",
      sum(r["crossed"] for r in ref["sel_c"].values() if r))

def to_gdf(d, extra):
    recs = []
    for t, r in d.items():
        if r:
            recs.append(dict(target=t, kind=tmap[t]["kind"], alt=r["alt"], length_m=round(r["length"], 1),
                             cost=r["cost"], status="UNVERIFIED_PLANNING_ALTERNATIVE", **extra, geometry=r["geom"]))
    return gpd.GeoDataFrame(recs, crs=CRS)
gp = out_dir / "plan.gpkg"
allrec = [dict(target=t, kind=tmap[t]["kind"], alt=r["alt"], length_m=round(r["length"], 1), cost=r["cost"],
               status="UNVERIFIED_PLANNING_ALTERNATIVE", geometry=r["geom"]) for t in order for r in ref["alts"][t]]
gpd.GeoDataFrame(allrec, crs=CRS).to_file(gp, layer="stageA_alternatives", driver="GPKG")
to_gdf(ref["sel_c"], {}).to_file(gp, layer="stageB_credit_plan", driver="GPKG")
to_gdf(ref["sel_i"], {}).to_file(gp, layer="independent_plan", driver="GPKG")
to_gdf(ref["base"], {}).to_file(gp, layer="straight_baseline", driver="GPKG")
adf.to_csv(out_dir / "alternatives_and_selection.csv", index=False)
mt.to_csv(out_dir / "plan_metrics_reference.csv")
print("Wrote:", gp)

if a.sweep:
    ref_union = unary_union([r["geom"] for r in ref["sel_c"].values() if r])
    ref_gap = ref["gap_cands"]
    ref_served = int(ref_gap.intersects(ref_union.buffer(SERVE)).sum())
    print(f"\nReference plan: unique length {metrics(ref['sel_c'], tmap)['unique_len']} m, "
          f"reference gap buildings {len(ref_gap)}, within {SERVE:.0f} m of plan: {ref_served}")
    settings = [("anytouch", "burn_rule", 10, False, 0.0, 0.0, 0), ("dilate2m", "dilate", 10, True, 2.0, 0.0, 0),
                ("min25", "min_area", 25, True, 0.0, 0.0, 0), ("min50", "min_area", 50, True, 0.0, 0.0, 0),
                ("min100", "min_area", 100, True, 0.0, 0.0, 0)]
    for fr in (0.1, 0.2, 0.3):
        for sd in range(1, a.seeds + 1):
            settings.append((f"drop{int(fr*100)}_s{sd}", f"drop{int(fr*100)}", 10, True, 0.0, fr, sd))
    recs = []
    for name, grp, ma, center, buf, drop, sd in settings:
        c = cand_all[cand_all.area_m2 >= ma]
        if drop > 0:
            c = c[np.random.default_rng(sd).random(len(c)) >= drop]
        res = evaluate(c, center=center, buf=buf)
        m = metrics(res["sel_c"], res["tmap"])
        gs = [r["geom"] for r in res["sel_c"].values() if r]
        pu = unary_union(gs)
        ov_ref = ref_union.intersection(pu.buffer(a.same_tol_m)).length / ref_union.length
        ov_new = pu.intersection(ref_union.buffer(a.same_tol_m)).length / max(pu.length, 1e-9)
        fchg = 0
        for t in order:
            if tmap[t]["kind"] != "FACILITY":
                continue
            r0, r1 = ref["sel_c"][t], res["sel_c"].get(t)
            if r0 is None or r1 is None:
                fchg += 1; continue
            o = min(r0["geom"].intersection(r1["geom"].buffer(a.same_tol_m)).length / max(r0["geom"].length, 1e-9),
                    r1["geom"].intersection(r0["geom"].buffer(a.same_tol_m)).length / max(r1["geom"].length, 1e-9))
            fchg += int(o < 0.5)
        recs.append(dict(setting=name, group=grp, cands=len(res["cs"]), targets=len(res["order"]),
                         gap_clusters=sum(res["tmap"][t]["kind"] == "CLUSTER" for t in res["order"]),
                         unique_len=m["unique_len"], saving=m["saving"],
                         ref_plan_kept=round(ov_ref, 2), new_plan_in_ref=round(ov_new, 2),
                         ref_gap_served=int(ref_gap.intersects(pu.buffer(SERVE)).sum()),
                         fac_changed=fchg))
        print(f"{name:<14} done", flush=True)
    sw = pd.DataFrame(recs)
    sw.to_csv(out_dir / "sweep_records.csv", index=False)
    print("\nPer-setting results vs reference plan:")
    print(sw.to_string(index=False))
    print(f"\n(reference gap buildings served by reference plan: {ref_served} of {len(ref_gap)})")
    print("Group summary (mean | min..max):")
    print(sw.groupby("group").agg(runs=("setting", "count"), clusters=("gap_clusters", "mean"),
                                  unique_len=("unique_len", "mean"), plan_kept=("ref_plan_kept", "mean"),
                                  plan_kept_min=("ref_plan_kept", "min"), gap_served=("ref_gap_served", "mean"),
                                  gap_served_min=("ref_gap_served", "min"),
                                  fac_changed=("fac_changed", "mean")).round(2).to_string())

after = {p: sha(p) for p in before}
for p in before:
    print("UNCHANGED" if before[p] == after[p] else "!!! CHANGED !!!", p)
print(f"Total time {time.time()-t0:.0f}s | outputs: {out_dir}")