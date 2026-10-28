"""run_planning_experiments.py - C1 (building-input perturbation) and C2 (attachment / shared-credit) experiments.

Uses the VALIDATED planner (plan_network_v2.py: same hard constraints, same corner-cut rule, same endpoint/connector checks).
Nothing here measures segmentation accuracy. C1 perturbations are SYNTHETIC controlled changes to the model-predicted building
polygons; they show how SENSITIVE the road plan is to building-input errors, not how wrong the real segmentation is.
Evaluation set (fixed): the buildings of the baseline gap clusters + the baseline facilities. With few seeds results are
descriptive (mean/min/max); no significance is claimed.

C1 families : random omission | systematic omission (smallest / farthest-from-road / nearest-to-road) | inflation (buffer) |
              merge (morphological closing) | footprint-area threshold
C2          : network-aware vs independent least-cost on several target sets (gap threshold, random sub-sets) + ablations
              (independent | stage-A credit only | attachment without re-route | full | k=1)
All results go to a NEW folder; existing runs are never touched.
"""
import hashlib, json, math, os, sys, time
from pathlib import Path
import numpy as np, pandas as pd, geopandas as gpd
from rasterio.features import rasterize
from shapely.ops import unary_union

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plan_network_v2 as P

INF = P.INF
CRS = P.CRS


def sha(p):
    return P.sha(p) if p and os.path.exists(p) else None


def build_clusters(cand, road_u, radius, settlement_min_n, gap_m):
    """Same logic as assess_building_access_v2.build() (re-implemented so perturbed buildings can be re-clustered)."""
    cand = cand.copy().reset_index(drop=True)
    if cand.empty:
        return cand.assign(cluster_id=[], dist_to_ref_road_m=[]), gpd.GeoDataFrame(
            {"cluster_id": [], "gap_flag": [], "n_candidates": []}, geometry=[], crs=CRS)
    cand["dist_to_ref_road_m"] = cand.geometry.distance(road_u).round(2)
    merged = unary_union(cand.geometry.buffer(radius / 2.0).tolist())
    parts = list(merged.geoms) if hasattr(merged, "geoms") else [merged]
    cl = gpd.GeoDataFrame({"cluster_id": range(1, len(parts) + 1)}, geometry=parts, crs=CRS)
    pts = gpd.GeoDataFrame(geometry=cand.geometry.representative_point(), crs=CRS)
    j = gpd.sjoin(pts, cl, how="left", predicate="within")
    j = j[~j.index.duplicated(keep="first")]
    cand["cluster_id"] = j["cluster_id"].reindex(cand.index).fillna(-1).astype(int)
    g = cand.groupby("cluster_id")
    cl = cl.set_index("cluster_id")
    cl["n_candidates"] = g.size()
    cl["min_dist_to_ref_road_m"] = g["dist_to_ref_road_m"].min()
    if "quality_class" in cand.columns:
        cl["n_unresolved_merge"] = cand.groupby("cluster_id")["quality_class"].apply(lambda x: int((x == "UNRESOLVED_MERGE").sum()))
    cl = cl.reset_index()
    cl["gap_flag"] = cl["min_dist_to_ref_road_m"] > gap_m
    return cand, cl


# ---------------------------------------------------------------------------------------------- perturbations
def perturb(cand, kind, level, seed, road_u):
    c = cand.copy().reset_index(drop=True)
    n = len(c)
    if kind == "baseline":
        return c
    if kind == "random_omission":
        rng = np.random.default_rng(seed)
        keep = np.ones(n, bool); keep[rng.choice(n, int(round(level * n)), replace=False)] = False
        return c[keep].reset_index(drop=True)
    if kind.startswith("systematic_omission"):
        how = kind.split(":")[1]
        k = int(round(level * n))
        d = c.geometry.distance(road_u)
        order = {"smallest": c.area_m2.values.argsort(kind="stable"),
                 "farthest_from_road": (-d.values).argsort(kind="stable"),
                 "nearest_to_road": d.values.argsort(kind="stable")}[how]
        keep = np.ones(n, bool); keep[order[:k]] = False
        return c[keep].reset_index(drop=True)
    if kind == "inflation":
        c["geometry"] = c.geometry.buffer(level); c["area_m2"] = c.geometry.area; return c
    if kind == "merge_closing":
        u = unary_union(c.geometry.buffer(level).tolist()).buffer(-level)
        parts = list(u.geoms) if hasattr(u, "geoms") else [u]
        parts = [p for p in parts if not p.is_empty]
        out = gpd.GeoDataFrame({"area_m2": [p.area for p in parts]}, geometry=parts, crs=CRS)
        if "quality_class" in c.columns:
            out["quality_class"] = "UNRESOLVED_MERGE"
        return out
    if kind == "area_threshold":
        return c[c.area_m2 >= level].reset_index(drop=True)
    raise ValueError(kind)


# ---------------------------------------------------------------------------------------------- planning wrapper
class Ctx:
    pass


def building_mult(ctx, polys):
    if ctx.a.building_mult == 1.0 or polys is None or len(polys) == 0:
        return ctx.W["mult_base"]
    bm = rasterize([(g, 1) for g in polys.geometry if g is not None and not g.is_empty], out_shape=(ctx.W["H"], ctx.W["W"]),
                   transform=ctx.W["T"], fill=0, all_touched=False, dtype="uint8").astype(bool)
    m = ctx.W["mult_base"].copy(); m[bm] *= ctx.a.building_mult
    return m


def run_plan(ctx, cand_s, cl_s, polys_for_cost, attach=True, passes=None, k=None, extra_targets=None, keep_clusters=None):
    a, W = ctx.a, ctx.W
    grid = P.Grid(W["cost"], W["T"], hard=W["hard"], mult=building_mult(ctx, polys_for_cost), corner_cut=(a.corner_cut == "allow"))
    cl_use = cl_s if keep_clusters is None else cl_s[cl_s.cluster_id.isin(keep_clusters)]
    targets = P.build_targets(a, grid, ctx.fac, cl_use, cand_s) if len(cl_s) else P.build_targets(a, grid, ctx.fac, cl_s, cand_s)
    Pp = dict(attach_tol_m=a.attach_tol_m, max_search_m=a.max_search_m, snap_m=a.snap_m, k=(k or a.k), corridor_m=a.corridor_m,
              corridor_mults=a.corridor_mults, max_overlap=a.max_overlap, passes=(a.passes if passes is None else passes),
              budget=None, attach=attach)
    t0 = time.time()
    res = P.plan(grid, W["road_union"], W["road_cells"], targets, Pp)
    ver = P.verify_network(res["sel"], W["road_union"], grid, a.attach_tol_m)
    for t, r in res["sel"].items():
        r.update(ver[t])
    sel = [r for r in res["sel"].values() if r["connected_to_roads"]]
    ind = list(res["indep"].values())
    tmap = {t["id"]: t for t in targets}
    out = dict(n_targets=len(targets), n_cluster_targets=sum(t["kind"] == "CLUSTER" for t in targets), targets=targets, tmap=tmap, res=res,
               sel=sel, ind=ind, seconds=round(time.time() - t0, 1))
    for nm, rs in (("na", sel), ("ic", ind)):
        m = P.unique_edge_metrics(rs) if rs else dict(unique_len_m=0.0, unique_cost=0.0, total_len_m=0.0, total_cost=0.0)
        out[nm] = m
        out[nm + "_served_clusters"] = sum(tmap[r["target"]]["kind"] == "CLUSTER" for r in rs)
        out[nm + "_served_facilities"] = sum(tmap[r["target"]]["kind"] == "FACILITY" for r in rs)
        out[nm + "_benefit"] = round(sum(tmap[r["target"]]["weight"] for r in rs), 2)
    out["failed"] = dict(res["fails"])
    out["attached"] = [r["target"] for r in sel if r.get("attach_to", "ROAD") != "ROAD"]
    out["hard_violating_selected_routes"] = sum(1 for r in sel if not r.get("hard_ok", True))
    return out


def coverage(ctx, routes, eval_pts, radius):
    net = unary_union([ctx.W["road_union"]] + [r["geom"] for r in routes]) if routes else ctx.W["road_union"]
    if not len(eval_pts):
        return float("nan")
    return float(np.mean([p.distance(net) <= radius for p in eval_pts]))


def overlap(routes_a, routes_b, tol):
    if not routes_a or not routes_b:
        return float("nan")
    ua, ub = unary_union([r["geom"] for r in routes_a]), unary_union([r["geom"] for r in routes_b])
    return float(ua.intersection(ub.buffer(tol)).length / max(ua.length, 1e-9))


# ---------------------------------------------------------------------------------------------- main
def main():
    ap = P.make_parser()
    ap.set_defaults(out_root=os.path.join(P.ROOT, "results", "planning_experiments", "experiments_v1"), tag="exp1", buildings="")
    ap.add_argument("--only", choices=["c1", "c2", "all"], default="all")
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--levels", type=float, nargs="+", default=[0.1, 0.2, 0.3], help="omission fractions")
    ap.add_argument("--inflate-m", type=float, nargs="+", default=[1.0, 2.0, 4.0])
    ap.add_argument("--closing-m", type=float, nargs="+", default=[2.0, 4.0])
    ap.add_argument("--area-thresholds", type=float, nargs="+", default=[5.0, 15.0, 20.0, 30.0, 50.0])
    ap.add_argument("--gap-values", type=float, nargs="+", default=[0.0, 25.0, 50.0, 100.0])
    ap.add_argument("--subset-fracs", type=float, nargs="+", default=[0.5, 0.75])
    ap.add_argument("--cluster-radius-m", type=float, default=20.0)
    ap.add_argument("--settlement-min-n", type=int, default=8)
    ap.add_argument("--gap-m", type=float, default=50.0)
    ap.add_argument("--coverage-radius-m", type=float, default=50.0, help="a reference building counts as covered if within this distance of roads+planned routes")
    ap.add_argument("--overlap-tol-m", type=float, default=15.0)
    ap.add_argument("--quick", action="store_true", help="3 seeds, levels 0.1/0.3, fewer thresholds; for a first timing")
    a = ap.parse_args()
    if a.quick:
        a.seeds, a.levels, a.inflate_m, a.closing_m, a.area_thresholds, a.gap_values, a.subset_fracs = 3, [0.1, 0.3], [2.0], [3.0], [20.0], [0.0, 50.0], [0.5]

    out = Path(a.out_root) / a.tag
    if out.exists() and any(out.iterdir()):
        sys.exit(f"{out} already has files; choose a new --tag (nothing is overwritten)")
    out.mkdir(parents=True, exist_ok=True)
    t_start = time.time()
    ctx = Ctx(); ctx.a = a
    ctx.W = P.load_world(a)
    for n in ctx.W["notes"]:
        print("NOTE:", n)
    print("RESOLVED HARD CONSTRAINTS:", ctx.W["constraints_resolved"])
    cand0 = gpd.read_file(a.access_gpkg, layer="candidate_access").to_crs(CRS)
    ctx.fac = gpd.read_file(a.access_gpkg, layer="facility_access").to_crs(CRS)
    cl_file = gpd.read_file(a.access_gpkg, layer="clusters").to_crs(CRS)
    for c in ("area_m2",):
        if c not in cand0.columns:
            sys.exit(f"candidate_access lacks {c}; has {list(cand0.columns)}")
    road_u = ctx.W["road_union"]
    cand_b, cl_b = build_clusters(cand0.drop(columns=[c for c in ("cluster_id", "dist_to_ref_road_m", "gap_flag") if c in cand0.columns]),
                                  road_u, a.cluster_radius_m, a.settlement_min_n, a.gap_m)
    chk = dict(clusters_rebuilt=len(cl_b), clusters_in_file=len(cl_file), gap_clusters_rebuilt=int(cl_b.gap_flag.sum()),
               gap_clusters_in_file=int(cl_file.gap_flag.astype(str).str.lower().isin(["true", "1"]).sum()))
    print("RE-CLUSTERING CHECK (must match the access assessment):", chk)
    if chk["clusters_rebuilt"] != chk["clusters_in_file"] or chk["gap_clusters_rebuilt"] != chk["gap_clusters_in_file"]:
        print("WARNING: re-clustering does not reproduce the access assessment; check --cluster-radius-m/--gap-m against the access run")
    ref_gap = cl_b[cl_b.gap_flag]
    eval_b = cand_b[cand_b.cluster_id.isin(ref_gap.cluster_id)]
    eval_pts = list(eval_b.geometry.representative_point())
    print(f"FIXED EVALUATION SET: {len(eval_pts)} reference buildings in {len(ref_gap)} baseline gap clusters + {len(ctx.fac)} facilities")

    rows = []

    def record(family, level, seed, label, r, base):
        d = dict(family=family, level=level, seed=seed, label=label, input_buildings=r["_n_in"], clusters=r["_n_cl"], cluster_targets=r["n_cluster_targets"],
                 targets=r["n_targets"], served_clusters_na=r["na_served_clusters"], served_facilities_na=r["na_served_facilities"],
                 failed_targets=len(r["failed"]), failed_reasons=";".join(sorted(set(r["failed"].values()))),
                 weighted_benefit_na=r["na_benefit"], na_total_len_m=round(r["na"]["total_len_m"], 1), na_unique_len_m=round(r["na"]["unique_len_m"], 1),
                 na_unique_cost=round(r["na"]["unique_cost"], 1), ic_unique_len_m=round(r["ic"]["unique_len_m"], 1), ic_total_len_m=round(r["ic"]["total_len_m"], 1),
                 c2_reduction_m=round(r["ic"]["unique_len_m"] - r["na"]["unique_len_m"], 1),
                 c2_reduction_pct=round(100 * (r["ic"]["unique_len_m"] - r["na"]["unique_len_m"]) / max(r["ic"]["unique_len_m"], 1e-9), 2),
                 attached_targets=len(r["attached"]), hard_violating_selected_routes=r["hard_violating_selected_routes"],
                 ref_building_coverage=round(coverage(ctx, r["sel"], eval_pts, a.coverage_radius_m), 4),
                 net_overlap_with_baseline=round(overlap(r["sel"], base["sel"], a.overlap_tol_m), 4) if base is not None else 1.0,
                 baseline_overlap_with_net=round(overlap(base["sel"], r["sel"], a.overlap_tol_m), 4) if base is not None else 1.0,
                 seconds=r["seconds"])
        rows.append(d)
        print(f"  [{len(rows):>3}] {label:<42} clusters={d['cluster_targets']:<3} served={d['served_clusters_na']:<3} uniqueNA={d['na_unique_len_m']:<8} "
              f"cov={d['ref_building_coverage']:<6} ovl={d['net_overlap_with_baseline']:<6} ({d['seconds']} s)", flush=True)

    def scenario(family, level, seed, label, cand_s, base, gap=None):
        c2, cl2 = build_clusters(cand_s, road_u, a.cluster_radius_m, a.settlement_min_n, a.gap_m if gap is None else gap)
        r = run_plan(ctx, c2, cl2[cl2.gap_flag] if len(cl2) else cl2, cand_s)
        r["_n_in"], r["_n_cl"] = len(cand_s), len(cl2)
        record(family, level, seed, label, r, base)
        return r

    base = None
    if a.only in ("c1", "all"):
        print("\n=== BASELINE + C1 perturbations (synthetic building-input perturbations; NOT measured segmentation error) ===")
        base_cand = cand_b[["area_m2", "geometry"] + [c for c in ("quality_class", "cand_id") if c in cand_b.columns]]
        base = scenario("baseline", 0, 0, "baseline (unperturbed v8 buildings)", base_cand, None)
        for lv in a.levels:
            for sd in range(a.seeds):
                scenario("random_omission", lv, sd, f"random omission {int(lv*100)}% seed {sd}", perturb(base_cand, "random_omission", lv, sd, road_u), base)
        for how in ("smallest", "farthest_from_road", "nearest_to_road"):
            for lv in a.levels:
                scenario(f"systematic_omission:{how}", lv, 0, f"omit {int(lv*100)}% {how}", perturb(base_cand, f"systematic_omission:{how}", lv, 0, road_u), base)
        for d in a.inflate_m:
            scenario("inflation", d, 0, f"inflate footprints +{d} m", perturb(base_cand, "inflation", d, 0, road_u), base)
        for d in a.closing_m:
            scenario("merge_closing", d, 0, f"merge (closing {d} m)", perturb(base_cand, "merge_closing", d, 0, road_u), base)
        for t in a.area_thresholds:
            scenario("area_threshold", t, 0, f"min footprint {t} m2", perturb(base_cand, "area_threshold", t, 0, road_u), base)

    c2rows, abl = [], []
    if a.only in ("c2", "all"):
        print("\n=== C2: network-aware vs independent over several target sets ===")
        base_cand = cand_b[["area_m2", "geometry"] + [c for c in ("quality_class", "cand_id") if c in cand_b.columns]]
        sets = []
        for g in a.gap_values:
            c2_, cl2_ = build_clusters(base_cand, road_u, a.cluster_radius_m, a.settlement_min_n, g)
            sets.append((f"gap>{g:g} m", c2_, cl2_[cl2_.gap_flag]))
        full = sets[[g for g in a.gap_values].index(a.gap_m)] if a.gap_m in a.gap_values else sets[0]
        for fr in a.subset_fracs:
            for sd in range(a.seeds):
                cl_f = full[2]
                rng = np.random.default_rng(1000 + sd)
                ids = list(cl_f.cluster_id)
                pick = rng.choice(len(ids), max(1, int(round(fr * len(ids)))), replace=False) if ids else []
                sets.append((f"random {int(fr*100)}% of {full[0]} clusters, seed {sd}", full[1], cl_f[cl_f.cluster_id.isin([ids[i] for i in pick])]))
        for name, c2_, clg in sets:
            r = run_plan(ctx, c2_, clg, base_cand)
            red = r["ic"]["unique_len_m"] - r["na"]["unique_len_m"]
            c2rows.append(dict(target_set=name, clusters=r["n_cluster_targets"], targets=r["n_targets"], served_na=r["na_served_clusters"] + r["na_served_facilities"],
                               served_independent=r["ic_served_clusters"] + r["ic_served_facilities"], failed=len(r["failed"]),
                               ic_total_len_m=round(r["ic"]["total_len_m"], 1), ic_unique_len_m=round(r["ic"]["unique_len_m"], 1),
                               ic_overlap_m=round(r["ic"]["total_len_m"] - r["ic"]["unique_len_m"], 1),
                               na_total_len_m=round(r["na"]["total_len_m"], 1), na_unique_len_m=round(r["na"]["unique_len_m"], 1),
                               unique_len_reduction_m=round(red, 1), unique_len_reduction_pct=round(100 * red / max(r["ic"]["unique_len_m"], 1e-9), 2),
                               unique_cost_na=round(r["na"]["unique_cost"], 1), unique_cost_ic=round(r["ic"]["unique_cost"], 1),
                               attached_targets=len(r["attached"]), attached_ids=";".join(r["attached"]), hard_violating_selected=r["hard_violating_selected_routes"],
                               seconds=r["seconds"]))
            print(f"  {name:<44} targets={r['n_targets']:<3} IC unique={r['ic']['unique_len_m']:<8.1f} NA unique={r['na']['unique_len_m']:<8.1f} "
                  f"reduction={red:>7.1f} m ({c2rows[-1]['unique_len_reduction_pct']}%) attached={len(r['attached'])}", flush=True)
        print("\n=== C2 ablations (same targets and constraints) ===")
        for name, c2_, clg in [sets[0], full] if sets[0][0] != full[0] else [full]:
            for vname, kw in (("stageA_credit_only (no fresh attachment, no re-route)", dict(attach=False, passes=0)),
                              ("attachment, no re-route pass", dict(attach=True, passes=0)),
                              ("full (attachment + re-route)", dict(attach=True)),
                              ("full with k=1 alternative", dict(attach=True, k=1))):
                r = run_plan(ctx, c2_, clg, base_cand, **kw)
                abl.append(dict(target_set=name, variant=vname, targets=r["n_targets"], served=r["na_served_clusters"] + r["na_served_facilities"],
                                independent_unique_len_m=round(r["ic"]["unique_len_m"], 1), variant_unique_len_m=round(r["na"]["unique_len_m"], 1),
                                reduction_vs_independent_m=round(r["ic"]["unique_len_m"] - r["na"]["unique_len_m"], 1),
                                reduction_pct=round(100 * (r["ic"]["unique_len_m"] - r["na"]["unique_len_m"]) / max(r["ic"]["unique_len_m"], 1e-9), 2),
                                attached_targets=len(r["attached"]), seconds=r["seconds"]))
                print(f"  {name:<12} {vname:<56} unique={abl[-1]['variant_unique_len_m']:<8} vs independent {abl[-1]['independent_unique_len_m']:<8} "
                      f"({abl[-1]['reduction_pct']}%) attached={abl[-1]['attached_targets']}", flush=True)

    # ---- write
    summ = {}
    if rows:
        df = pd.DataFrame(rows); df.to_csv(out / "c1_runs.csv", index=False)
        g = df.groupby(["family", "level"]).agg(runs=("seed", "size"), clusters_mean=("cluster_targets", "mean"),
                                                served_mean=("served_clusters_na", "mean"), served_min=("served_clusters_na", "min"), served_max=("served_clusters_na", "max"),
                                                unique_len_mean=("na_unique_len_m", "mean"), unique_len_min=("na_unique_len_m", "min"), unique_len_max=("na_unique_len_m", "max"),
                                                coverage_mean=("ref_building_coverage", "mean"), coverage_min=("ref_building_coverage", "min"), coverage_max=("ref_building_coverage", "max"),
                                                overlap_mean=("net_overlap_with_baseline", "mean"), overlap_min=("net_overlap_with_baseline", "min")).round(3).reset_index()
        g.to_csv(out / "c1_summary.csv", index=False)
        print("\nC1 SUMMARY (descriptive; seeds =", a.seeds, "-> no significance claimed)"); print(g.to_string(index=False))
        summ["c1_baseline"] = rows[0]
    if c2rows:
        pd.DataFrame(c2rows).to_csv(out / "c2_scenarios.csv", index=False)
        pd.DataFrame(abl).to_csv(out / "c2_ablation.csv", index=False)
        d2 = pd.DataFrame(c2rows)
        print("\nC2 SCENARIOS"); print(d2[["target_set", "targets", "ic_unique_len_m", "na_unique_len_m", "unique_len_reduction_pct", "attached_targets", "failed"]].to_string(index=False))
        summ["c2_reduction_pct_min_max_mean"] = [float(d2.unique_len_reduction_pct.min()), float(d2.unique_len_reduction_pct.max()), float(d2.unique_len_reduction_pct.mean())]
        summ["c2_scenarios_where_attachment_changed_selection"] = int((d2.attached_targets > 0).sum())
        summ["c2_scenarios_total"] = int(len(d2))
    try:
        import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
        if rows:
            fam = pd.DataFrame(rows); fig, ax = plt.subplots(1, 2, figsize=(12, 4.2))
            for f_, sub in fam.groupby("family"):
                s_ = sub.groupby("level")[["na_unique_len_m", "ref_building_coverage"]].agg(["mean", "min", "max"])
                x = s_.index.values
                ax[0].errorbar(x, s_[("na_unique_len_m", "mean")], yerr=[s_[("na_unique_len_m", "mean")] - s_[("na_unique_len_m", "min")], s_[("na_unique_len_m", "max")] - s_[("na_unique_len_m", "mean")]], marker="o", label=f_, capsize=2)
                ax[1].errorbar(x, s_[("ref_building_coverage", "mean")], yerr=[s_[("ref_building_coverage", "mean")] - s_[("ref_building_coverage", "min")], s_[("ref_building_coverage", "max")] - s_[("ref_building_coverage", "mean")]], marker="o", label=f_, capsize=2)
            ax[0].set_ylabel("network-aware unique length (m)"); ax[1].set_ylabel(f"reference gap buildings within {a.coverage_radius_m:g} m of roads+plan")
            for x_ in ax: x_.set_xlabel("perturbation level (fraction / metres / m2 - per family)")
            ax[1].legend(fontsize=6); fig.suptitle("C1: sensitivity of the road plan to SYNTHETIC building-input perturbations (bars = min-max over seeds; descriptive)", fontsize=9)
            fig.tight_layout(); fig.savefig(out / "c1_sensitivity.png", dpi=120); plt.close(fig)
        if c2rows:
            fig, ax = plt.subplots(figsize=(10, 4.2)); d2 = pd.DataFrame(c2rows)
            ax.barh(range(len(d2)), d2.unique_len_reduction_pct); ax.set_yticks(range(len(d2))); ax.set_yticklabels(d2.target_set, fontsize=6)
            ax.set_xlabel("unique-length reduction of network-aware vs independent (%)"); ax.set_title("C2: effect of attachment + shared-edge credit by target set (descriptive)", fontsize=9)
            fig.tight_layout(); fig.savefig(out / "c2_reduction.png", dpi=120); plt.close(fig)
    except Exception as e:
        print("figures skipped:", e)
    meta = dict(version="run_planning_experiments v1", params=P.jsonable({k: v for k, v in vars(a).items()}), constraints_resolved=P.jsonable(ctx.W["constraints_resolved"]),
                recluster_check=chk, evaluation_set=dict(reference_buildings=len(eval_pts), reference_gap_clusters=int(len(ref_gap)), facilities=int(len(ctx.fac))),
                hashes=dict(planner=sha(os.path.join(os.path.dirname(os.path.abspath(__file__)), "plan_network_v2.py")), this_script=sha(os.path.abspath(__file__)),
                            access_gpkg=sha(a.access_gpkg), cost=sha(a.cost), roads=sha(a.roads)),
                results=P.jsonable(summ), total_seconds=round(time.time() - t_start, 1),
                caveats=["C1 perturbations are synthetic; they are NOT measured segmentation error and say nothing about real accuracy.",
                         "Few seeds: results are descriptive; no statistical significance is claimed.",
                         "Weights, cost units and the hard slope rule are project parameters; cost units are not money.",
                         "All building polygons are unverified model predictions; routes are planning alternatives, not roads."])
    (out / "experiments_summary.json").write_text(json.dumps(meta, indent=2, default=str), encoding="utf-8")
    print(f"\nWrote results to {out}  (total {meta['total_seconds']} s)")


if __name__ == "__main__":
    main()
