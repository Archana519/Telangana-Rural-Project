"""Read-only scoring of V4 route alternatives vs candidate buildings, with shared-edge accounting.
No weights applied. Candidate buildings are UNVERIFIED predictions; routes are unverified alternatives."""
import argparse, itertools, os, sys
import pandas as pd, geopandas as gpd
from shapely.geometry import Point
from shapely.ops import unary_union

ROOT = r"D:\Telangana_Rural_Project\Siddipet\Damarakunta"
V4 = os.path.join(ROOT, "results", "damarakunta_routes_v4.gpkg")
ROADS = os.path.join(ROOT, "reference", "tgrac_road_network.gpkg")
ACC = os.path.join(ROOT, "results", "v6_buildings", "access", "access_assessment.gpkg")
OUT_DIR = os.path.join(ROOT, "results", "v6_buildings", "routes_scored")
CRS = "EPSG:32644"

ap = argparse.ArgumentParser()
ap.add_argument("--serve-buffer-m", type=float, default=30.0)
ap.add_argument("--share-tol-m", type=float, default=3.0)
ap.add_argument("--attach-tol-m", type=float, default=5.0)
ap.add_argument("--gap-m", type=float, default=50.0)
ap.add_argument("--max-combos", type=int, default=5000)
ap.add_argument("--overwrite", action="store_true")
a = ap.parse_args()

gpkg = os.path.join(OUT_DIR, "routes_scored.gpkg")
if os.path.exists(gpkg):
    if not a.overwrite:
        sys.exit(f"{gpkg} exists; use --overwrite")
    os.remove(gpkg)
os.makedirs(OUT_DIR, exist_ok=True)

routes = gpd.read_file(V4, layer="route_alternatives").to_crs(CRS).reset_index(drop=True)
road_u = gpd.read_file(ROADS).to_crs(CRS).geometry.union_all()
cand = gpd.read_file(ACC, layer="candidate_access").to_crs(CRS)
gapc = cand[cand.dist_to_ref_road_m > a.gap_m]
routes["facility_id"] = routes["facility_id"].astype(str)

show = ["facility_id", "facility_name", "alternative", "status", "total_geometry_length_m",
        "facility_to_nearest_road_m", "route_intersects_road", "builtup_cells", "water_cells",
        "max_sampled_slope_deg", "accumulated_cost", "facility_location_verification",
        "topology_verified", "construction_feasibility"]
print("\nV4 routes (as stored):")
print(routes[[c for c in show if c in routes.columns]].to_string())

served_all, served_gap, recs = {}, {}, []
for i, r in routes.iterrows():
    g = r.geometry
    ends = [Point(g.coords[0]), Point(g.coords[-1])]
    de = [round(float(e.distance(road_u)), 2) for e in ends]
    buf = g.buffer(a.serve_buffer_m)
    sa = set(cand.loc[cand.intersects(buf), "cand_id"])
    sg = set(gapc.loc[gapc.intersects(buf), "cand_id"])
    served_all[i], served_gap[i] = sa, sg
    recs.append(dict(route_idx=i, facility_id=r.facility_id, alternative=r.get("alternative"),
                     length_m=round(g.length, 1), end0_to_road_m=de[0], end1_to_road_m=de[1],
                     attaches_to_road=bool(min(de) <= a.attach_tol_m),
                     cands_within_buffer=len(sa), gap_cands_within_buffer=len(sg),
                     cost=r.get("accumulated_cost"),
                     loc_verif=r.get("facility_location_verification")))
met = pd.DataFrame(recs)
print(f"\nPer-route metrics (service buffer {a.serve_buffer_m} m, attach tol {a.attach_tol_m} m, gap {a.gap_m} m):")
print(met.to_string(index=False))

print("\nShared corridor between routes of DIFFERENT facilities (m within tolerance, conservative = min of both directions):")
pairs = []
for i, j in itertools.combinations(range(len(routes)), 2):
    if routes.facility_id[i] == routes.facility_id[j]:
        continue
    gi, gj = routes.geometry[i], routes.geometry[j]
    s = min(gj.intersection(gi.buffer(a.share_tol_m)).length,
            gi.intersection(gj.buffer(a.share_tol_m)).length)
    if s > 0:
        pairs.append(dict(i=i, j=j, fac_i=routes.facility_id[i], alt_i=routes.get("alternative")[i],
                          fac_j=routes.facility_id[j], alt_j=routes.get("alternative")[j], shared_m=round(s, 1)))
sp = pd.DataFrame(pairs)
print(sp.to_string(index=False) if len(sp) else "  none above tolerance")

groups = {f: list(idx) for f, idx in routes.groupby("facility_id").groups.items()}
n_combo = 1
for v in groups.values():
    n_combo *= len(v)
print(f"\nFacilities with routes: {len(groups)} | alternatives per facility: "
      f"{ {k: len(v) for k, v in groups.items()} } | combinations: {n_combo}")
if n_combo > a.max_combos:
    sys.exit("Too many combinations; raise --max-combos deliberately.")

out = []
for combo in itertools.product(*groups.values()):
    ordered = sorted(combo, key=lambda k: routes.geometry[k].length)
    uniq, prev = 0.0, None
    for k in ordered:
        g = routes.geometry[k]
        uniq += g.length if prev is None else g.difference(prev.buffer(a.share_tol_m)).length
        prev = g if prev is None else unary_union([prev, g])
    tot = sum(routes.geometry[k].length for k in combo)
    sg = set().union(*[served_gap[k] for k in combo])
    sa = set().union(*[served_all[k] for k in combo])
    cost = sum(float(routes.accumulated_cost[k]) for k in combo if pd.notna(routes.accumulated_cost[k]))
    out.append(dict(combo=" | ".join(f"{routes.facility_id[k]}:{routes.get('alternative')[k]}" for k in combo),
                    sum_length_m=round(tot, 1), unique_length_m=round(uniq, 1),
                    shared_saving_m=round(tot - uniq, 1), gap_cands_served=len(sg),
                    all_cands_served=len(sa), sum_raw_cost=round(cost, 1)))
co = pd.DataFrame(out).sort_values("unique_length_m").reset_index(drop=True)
print("\nCombinations, shortest unique length first (top 15; NO weights applied):")
print(co.head(15).to_string(index=False))

routes.merge(met.drop(columns=["facility_id", "alternative", "cost", "loc_verif"]),
             left_index=True, right_on="route_idx").to_file(gpkg, layer="routes_scored", driver="GPKG")
met.to_csv(os.path.join(OUT_DIR, "route_metrics.csv"), index=False)
co.to_csv(os.path.join(OUT_DIR, "combinations.csv"), index=False)
if len(sp):
    sp.to_csv(os.path.join(OUT_DIR, "shared_pairs.csv"), index=False)
print("\nWrote:", gpkg, "(+CSVs in routes_scored)")