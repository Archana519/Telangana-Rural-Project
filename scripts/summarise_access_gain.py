"""summarise_access_gain.py - READ-ONLY auxiliary report: proximity-based access before/after proposed routes.

PROPOSED FOR REVIEW. This is an evaluation utility, NOT the planner and NOT a replacement for any project stage.

READS (never modifies):
  access_assessment.gpkg      layers candidate_access, clusters, facility_access
  reference roads (.gpkg)     geometry only
  per run (<runs-root>/<run>) network_v2.gpkg (targets, routes_network_aware, routes_independent),
                              target_table.csv, plan_comparison.csv, summary.json
  constraint rasters named in each summary.json (cost, slope, prohibited, worldcover): HASHED ONLY, never opened as data
WRITES (new folder <out-root>/<tag>, refused if it exists and is non-empty):
  access_gain_summary.csv, facility_access_gain.csv, route_length_cost.csv, unserved_targets.csv,
  gap_flag_composition.csv, checks.csv, buildings_access.gpkg, access_gain_report.txt, access_gain_summary.json

WHAT IT MEASURES: PROXIMITY (distance polygon/point -> reference roads, and -> roads + proposed routes).
WHAT IT DOES NOT ESTABLISH: network-level accessibility, graph connectivity gain, monetary cost, road width, building accuracy,
multi-criteria selection quality, physical/legal/engineering feasibility. Weighted routing cost units are NOT money.

Every count, distance, length and cost is read or recomputed from the existing files and cross-checked against the run outputs.
Nothing is hard-coded as an expected result; a quantity that cannot be verified is reported as UNAVAILABLE.
"""
import argparse
import datetime as dt
import hashlib
import importlib.metadata as md
import json
import math
import os
import platform
import sys
from collections import OrderedDict
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import Point
from shapely.ops import unary_union

SCRIPT_VERSION = "summarise_access_gain v1 (proposed)"
PROJECT_ROOT = r"D:\Telangana_Rural_Project"
ROOT = os.path.join(PROJECT_ROOT, "Siddipet", "Damarakunta")
EXPECTED_EPSG = 32644
PLAN_NAMES = {"na": "network_aware", "ic": "independent_least_cost"}
SCENARIO_LABEL = {"na": "roads_plus_network_aware_routes", "ic": "roads_plus_independent_least_cost_routes"}
LAYERS_ACCESS = {"candidate_access": ["cand_id", "cluster_id", "gap_flag", "quality_class", "dist_to_ref_road_m"],
                 "clusters": ["cluster_id", "gap_flag", "kind", "n_candidates", "min_dist_to_ref_road_m"],
                 "facility_access": ["facility_id", "facility_name", "facility_type", "dist_to_ref_road_m"]}

LIMITATIONS = [
    "Proximity only: distance from a polygon/point to the reference roads or to roads plus proposed routes. It is not routed, walking or network accessibility.",
    "A polygon-level gap flag is defined as distance > gap_m, so at threshold == gap_m the baseline coverage of every gap-flagged set is 0 by definition.",
    "Routes start at their target point, so a targeted polygon or facility is close to its own route by construction; that is not independent validation. The informative quantity is spillover onto non-target polygons.",
    "Candidate polygons are unverified model predictions. UNRESOLVED_MERGE polygons are settlement extents, so counts are polygons, not verified buildings.",
    "The reference road layer is unverified and may omit internal lanes. The settlement-interior screening result is NOT proof that roads are required.",
    "Routes are UNVERIFIED planning alternatives on a 10 m raster. 'connected' (planner) is geometric connection within a tolerance; it is not a physical, legal or engineered connection.",
    "attach_to labels are not used as evidence. The independent route layer is known to carry a mislabelled attach_to in the reviewed copy of the planner.",
    "Weighted routing cost units are unitless planner scores (cost surface x multipliers x length), not rupees. No road width or construction rate is used. monetary_cost_estimated is false.",
    "Unserved targets are reported with the planner's failure_reason only; a target inside a hard-constrained or nodata cell is a raster-coverage/constraint result, not evidence of a real access gap.",
    "Constraint rasters are hashed at report time; this proves their current content, not that the run used identical content.",
    "Few runs/seeds elsewhere in the project: nothing here is a significance test.",
]


# ----------------------------------------------------------------------------------------------------------------- utils
def sha256_file(p, blk=1 << 20):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(blk), b""):
            h.update(b)
    return h.hexdigest()


def file_state(p):
    p = str(p)
    if not os.path.isfile(p):
        return dict(path=p, exists=False, size=None, mtime_ns=None, sha256=None)
    st = os.stat(p)
    return dict(path=p, exists=True, size=st.st_size, mtime_ns=st.st_mtime_ns, sha256=sha256_file(p))


def dir_listing(d):
    out = []
    for r, _, fs in os.walk(str(d)):
        for f in sorted(fs):
            fp = os.path.join(r, f)
            st = os.stat(fp)
            out.append((os.path.relpath(fp, str(d)), st.st_size, st.st_mtime_ns))
    return sorted(out)


def resolve_path(p):
    if not p:
        return None
    p = str(p)
    for cand in (p, os.path.abspath(p), os.path.join(PROJECT_ROOT, p)):
        if os.path.exists(cand):
            return cand
    return p


def to_bool(s):
    if s.dtype == bool:
        return s
    return s.astype(str).str.strip().str.lower().isin(["true", "1", "yes"])


def lib_versions():
    v = OrderedDict(python=sys.version.split()[0], platform=platform.platform())
    for m in ("geopandas", "shapely", "pandas", "numpy", "pyogrio", "fiona", "pyproj"):
        try:
            v[m] = md.version(m)
        except Exception:
            v[m] = "not installed"
    return v


class Checks:
    def __init__(self):
        self.rows = []

    def add(self, cid, desc, status, observed="", expected="", detail=""):
        assert status in ("PASS", "FAIL", "INFO", "FLAG", "UNAVAILABLE")
        self.rows.append(OrderedDict(check_id=cid, description=desc, status=status, observed=str(observed), expected=str(expected), detail=str(detail)))

    def any_fail(self):
        return any(r["status"] == "FAIL" for r in self.rows)


def fatal(msg):
    sys.exit("ERROR: " + msg + "\nNothing was written.")


def read_layer(path, layer, required, label, optional=False):
    try:
        df = gpd.read_file(path, layer=layer)
    except Exception as e:
        if optional:
            return None
        fatal(f"cannot read layer '{layer}' from {path}: {e}")
    miss = [c for c in required if c not in df.columns]
    if miss:
        fatal(f"{label}: layer '{layer}' lacks required columns {miss}; it has {list(df.columns)}")
    return df


def verify_unchanged(before, after):
    """before/after: {path: state}. Returns list of (path, what_changed)."""
    bad = []
    for p, b in before.items():
        a = after.get(p)
        if a is None or a["exists"] != b["exists"]:
            bad.append((p, "existence"))
        elif b["exists"] and (a["sha256"] != b["sha256"] or a["size"] != b["size"]):
            bad.append((p, "content"))
    return bad


# ----------------------------------------------------------------------------------------------------------------- geometry
def geometric_reach(routes, tpoints, road_u, tol):
    """Independent of attach_to: does each route's network end lie within tol of the roads or of another route that reaches the roads?
    Orientation (coords[0] = target point) is verified against the targets layer; otherwise both endpoints are used and flagged."""
    geoms = list(routes.geometry)
    ids = [str(x) for x in routes["target"]]
    n = len(geoms)
    if n == 0:
        return [], True
    if not all(g is not None and g.geom_type == "LineString" for g in geoms):
        return None, False
    orient = all(i in tpoints and Point(g.coords[0]).distance(tpoints[i]) <= 0.5 for i, g in zip(ids, geoms))
    ends = [[Point(g.coords[-1])] if orient else [Point(g.coords[0]), Point(g.coords[-1])] for g in geoms]
    reach = [min(e.distance(road_u) for e in ends[i]) <= tol for i in range(n)]
    changed = True
    while changed:
        changed = False
        for i in range(n):
            if reach[i]:
                continue
            for j in range(n):
                if j != i and reach[j] and min(e.distance(geoms[j]) for e in ends[i]) <= tol:
                    reach[i] = True
                    changed = True
                    break
    return reach, orient


def pct(a, n):
    return float("nan") if n == 0 else 100.0 * a / n


# ----------------------------------------------------------------------------------------------------------------- main
def main(argv=None):
    ap = argparse.ArgumentParser(description="READ-ONLY proximity access-gain report (auxiliary; not the planner).")
    ap.add_argument("--runs-root", default=os.path.join(ROOT, "results", "planning_experiments", "network_v2"))
    ap.add_argument("--runs", nargs="+", default=["run5", "run6_slope_soft"])
    ap.add_argument("--out-root", default=os.path.join(ROOT, "results", "planning_experiments", "access_gain_v1"))
    ap.add_argument("--tag", default="ag1")
    ap.add_argument("--access-gpkg", default=None, help="default: path recorded in the first run's summary.json")
    ap.add_argument("--roads", default=None, help="default: path recorded in the first run's summary.json")
    ap.add_argument("--roads-layer", default=None)
    ap.add_argument("--thresholds", type=float, nargs="+", default=[25.0, 50.0, 100.0])
    ap.add_argument("--gap-m", type=float, default=50.0, help="gap threshold used by assess_building_access_v2 (cross-checked against the data)")
    ap.add_argument("--polygon-dist-tol-m", type=float, default=0.011)
    ap.add_argument("--facility-dist-tol-m", type=float, default=0.06)
    a = ap.parse_args(argv)

    out = Path(a.out_root) / a.tag
    if out.exists() and any(out.iterdir()):
        fatal(f"{out} already exists and is not empty; choose a new --tag (nothing is overwritten)")
    thresholds = sorted(set(float(t) for t in a.thresholds))
    chk = Checks()

    # ---- 1. run folders, summaries, input registry (hashes BEFORE any data use)
    runs = OrderedDict()
    reg_before = OrderedDict()
    listing_before = OrderedDict()
    for rn in a.runs:
        rd = Path(a.runs_root) / rn
        if not rd.is_dir():
            fatal(f"run folder not found: {rd}")
        r = dict(name=rn, dir=rd, files=OrderedDict((k, rd / v) for k, v in dict(
            gpkg="network_v2.gpkg", target_table="target_table.csv", plan_comparison="plan_comparison.csv", summary="summary.json").items()))
        for k, p in r["files"].items():
            if not p.is_file():
                fatal(f"missing run file: {p}")
            reg_before[str(p)] = file_state(p)
        r["summary"] = json.loads(Path(r["files"]["summary"]).read_text(encoding="utf-8"))
        listing_before[rn] = dir_listing(rd)
        runs[rn] = r
    first = next(iter(runs.values()))["summary"]
    access_p = resolve_path(a.access_gpkg or first.get("params", {}).get("access_gpkg"))
    roads_p = resolve_path(a.roads or first.get("params", {}).get("roads"))
    if not access_p or not os.path.isfile(access_p):
        fatal(f"access GeoPackage not found: {access_p}")
    if not roads_p or not os.path.isfile(roads_p):
        fatal(f"roads file not found: {roads_p}")
    reg_before[access_p] = file_state(access_p)
    reg_before[roads_p] = file_state(roads_p)
    provenance_rasters = OrderedDict()
    for rn, r in runs.items():
        sm = r["summary"]
        cands = OrderedDict(cost=sm.get("params", {}).get("cost"), worldcover=sm.get("params", {}).get("worldcover"),
                            slope=(sm.get("constraints_resolved") or {}).get("slope_raster"),
                            prohibited=(sm.get("constraints_resolved") or {}).get("prohibited_raster"))
        for k, p in cands.items():
            rp = resolve_path(p)
            provenance_rasters[(rn, k)] = rp
            if rp and os.path.isfile(rp) and rp not in reg_before:
                reg_before[rp] = file_state(rp)

    # ---- 2. load and validate the shared data
    cand = read_layer(access_p, "candidate_access", LAYERS_ACCESS["candidate_access"], "access")
    clus = read_layer(access_p, "clusters", LAYERS_ACCESS["clusters"], "access")
    fac = read_layer(access_p, "facility_access", LAYERS_ACCESS["facility_access"], "access")
    try:
        roads = gpd.read_file(roads_p, layer=a.roads_layer) if a.roads_layer else gpd.read_file(roads_p)
    except Exception as e:
        fatal(f"cannot read roads: {e}")
    for nm, df in (("candidate_access", cand), ("clusters", clus), ("facility_access", fac), ("roads", roads)):
        ep = df.crs.to_epsg() if df.crs is not None else None
        chk.add("CRS_" + nm, f"{nm} CRS is EPSG:{EXPECTED_EPSG}", "PASS" if ep == EXPECTED_EPSG else "FAIL", ep, EXPECTED_EPSG)
    if roads.crs is None or cand.crs is None or roads.crs != cand.crs:
        chk.add("CRS_match", "roads and candidates share one CRS", "FAIL", f"{roads.crs} vs {cand.crs}", "equal")
    road_u = unary_union(list(roads.geometry))

    cand = cand.reset_index(drop=True)
    cand["poly_gap"] = to_bool(cand["gap_flag"])
    clus["cl_gap"] = to_bool(clus["gap_flag"])
    chk.add("CAND_unique_ids", "candidate cand_id unique", "PASS" if cand["cand_id"].is_unique else "FAIL", int(cand["cand_id"].nunique()), len(cand))
    chk.add("CLUS_unique_ids", "cluster_id unique in clusters", "PASS" if clus["cluster_id"].is_unique else "FAIL", int(clus["cluster_id"].nunique()), len(clus))
    cmap = clus.set_index("cluster_id")
    missing_cl = sorted(set(cand["cluster_id"]) - set(cmap.index))
    chk.add("JOIN_cluster", "every candidate cluster_id exists in clusters", "PASS" if not missing_cl else "FAIL", missing_cl[:10], "none missing")
    cand["cluster_gap"] = cand["cluster_id"].map(cmap["cl_gap"]).fillna(False).astype(bool)
    cand["cluster_kind"] = cand["cluster_id"].map(cmap["kind"]).astype(str)
    cand["d_base_m"] = cand.geometry.distance(road_u)
    dd = (cand["d_base_m"] - cand["dist_to_ref_road_m"]).abs()
    chk.add("DIST_polygon_base", "recomputed polygon->road distance equals stored dist_to_ref_road_m", "PASS" if dd.max() <= a.polygon_dist_tol_m else "FAIL",
            f"max abs diff {dd.max():.4f} m", f"<= {a.polygon_dist_tol_m} m")
    derived_flag = cand["dist_to_ref_road_m"] > a.gap_m      # stored (rounded) distance, as the access run compared it
    mism = int((derived_flag != cand["poly_gap"]).sum())
    chk.add("GAP_polygon_def", f"candidate gap_flag == (distance > gap_m={a.gap_m:g})", "PASS" if mism == 0 else "FAIL", f"{mism} mismatches", 0,
            "FAIL here means gap_m differs from the access run's value")
    g = cand.groupby("cluster_id")
    cnt = g.size()
    mn = g["dist_to_ref_road_m"].min()
    bad_n = int((clus.set_index("cluster_id")["n_candidates"].reindex(cnt.index) != cnt).sum())
    chk.add("CLUS_n_candidates", "clusters.n_candidates equals members counted in candidate_access", "PASS" if bad_n == 0 else "FAIL", f"{bad_n} mismatches", 0)
    cl_flag_derived = (mn > a.gap_m).reindex(clus["cluster_id"]).values
    mism_c = int((cl_flag_derived != clus["cl_gap"].values).sum())
    chk.add("GAP_cluster_def", "cluster gap_flag == (min member distance > gap_m)", "PASS" if mism_c == 0 else "FAIL", f"{mism_c} mismatches", 0)

    fac = fac.reset_index(drop=True)
    fac["facility_id_s"] = fac["facility_id"].astype(str)
    fac["target_id"] = "F:" + fac["facility_id_s"]
    fac["d_base_m"] = fac.geometry.distance(road_u)
    fd = (fac["d_base_m"] - fac["dist_to_ref_road_m"]).abs()
    chk.add("DIST_facility_base", "recomputed facility->road distance equals stored value", "PASS" if (len(fac) == 0 or fd.max() <= a.facility_dist_tol_m) else "FAIL",
            f"max abs diff {fd.max() if len(fac) else float('nan'):.4f} m", f"<= {a.facility_dist_tol_m} m (stored value is rounded)")
    if not all(g.geom_type == "Point" for g in fac.geometry):
        chk.add("FAC_geom", "facility geometries are Points", "FAIL", fac.geom_type.value_counts().to_dict(), "Point")

    # ---- 3. building sets (derived from the data; definitions are explicit)
    sets = OrderedDict()
    allm = pd.Series(True, index=cand.index)
    sets["all_candidate_polygons"] = (allm, "population", "every row of candidate_access")
    for q in sorted(cand["quality_class"].astype(str).unique()):
        sets["quality_" + q] = (cand["quality_class"].astype(str) == q, "population", f"candidate_access quality_class == {q}")
    sets["polygon_gap_flag_true"] = (cand["poly_gap"], "polygon_level_gap", f"candidate gap_flag True (own distance > {a.gap_m:g} m)")
    sets["gap_cluster_polygons"] = (cand["cluster_gap"], "cluster_level_gap", "polygons whose cluster has clusters.gap_flag True (these are the planner's cluster targets)")
    settle = cand["cluster_kind"] == "SETTLEMENT_CLUSTER"
    if (cand["cluster_kind"] == "nan").all():
        chk.add("SET_settlement", "clusters.kind available for settlement sets", "UNAVAILABLE", "kind missing", "kind present")
    sets["settlement_cluster_polygons"] = (settle, "population", "polygons in clusters with kind == SETTLEMENT_CLUSTER")
    sets["settlement_interior_screening"] = (settle & (cand["dist_to_ref_road_m"] > a.gap_m), "screening",
                                              f"SETTLEMENT_CLUSTER polygons > {a.gap_m:g} m from a reference road; SCREENING result, not proof that roads are required")
    sets["nongap_isolated_cluster_polygons"] = ((cand["cluster_kind"] == "ISOLATED_OR_SMALL_GROUP") & (~cand["cluster_gap"]), "population", "ISOLATED_OR_SMALL_GROUP clusters that are not gap clusters")
    sets["non_target_polygons"] = (~cand["cluster_gap"], "spillover", "all polygons not in a gap cluster (spillover population)")
    comp = (cand.groupby(["poly_gap", "cluster_gap", "cluster_kind", "quality_class"]).size().reset_index(name="n_polygons")
            .rename(columns={"poly_gap": "polygon_gap_flag", "cluster_gap": "in_gap_cluster"}))

    # ---- 4. per run
    sum_rows, fac_rows, rl_rows, unserved_rows = [], [], [], []
    run_info = OrderedDict()
    per_poly = cand[["cand_id", "cluster_id", "quality_class", "cluster_kind", "cluster_gap", "poly_gap", "d_base_m", "geometry"]].copy()
    per_poly = per_poly.rename(columns={"cluster_gap": "in_gap_cluster", "poly_gap": "polygon_gap_flag"})
    for rn, r in runs.items():
        gp = str(r["files"]["gpkg"])
        sm = r["summary"]
        tt = pd.read_csv(r["files"]["target_table"])
        pc = pd.read_csv(r["files"]["plan_comparison"])
        for col in ("target", "kind", "status", "failure_reason", "route_len_m", "route_cost", "euclid_to_road_m", "weight"):
            if col not in tt.columns and col != "weight":
                fatal(f"{rn}: target_table.csv lacks column {col}; has {list(tt.columns)}")
        tgt = read_layer(gp, "targets", ["id", "kind", "weight"], rn)
        tpoints = {str(i): g for i, g in zip(tgt["id"], tgt.geometry)}
        routes = OrderedDict()
        routes["na"] = read_layer(gp, "routes_network_aware", ["target", "length_m", "cost"], rn, optional=True)
        routes["ic"] = read_layer(gp, "routes_independent", ["target", "length_m", "cost"], rn, optional=True)
        tol = float(sm.get("params", {}).get("attach_tol_m", 15.0))
        if "attach_tol_m" not in sm.get("params", {}):
            chk.add(f"TOL_{rn}", "attach tolerance recorded in summary.json", "FLAG", "not recorded; using 15 m", "recorded")

        # recorded input hashes vs recomputed
        for key, pth in (("access", access_p), ("roads", roads_p), ("cost", provenance_rasters.get((rn, "cost")))):
            rec = (sm.get("inputs") or {}).get(key)
            cur = reg_before.get(pth, {}).get("sha256") if pth else None
            if rec is None or cur is None:
                chk.add(f"HASH_{rn}_{key}", f"{rn}: recorded {key} hash vs current file", "UNAVAILABLE", f"recorded={rec} current={cur}", "both available")
            else:
                chk.add(f"HASH_{rn}_{key}", f"{rn}: recorded {key} hash equals current file", "PASS" if rec == cur else "FAIL", cur[:12], rec[:12])
        for k in ("slope", "prohibited", "worldcover"):
            pth = provenance_rasters.get((rn, k))
            if pth and os.path.isfile(pth):
                chk.add(f"PROV_{rn}_{k}", f"{rn}: {k} raster hashed now (the run did not record this hash)", "INFO", reg_before[pth]["sha256"][:12], "n/a")
            else:
                chk.add(f"PROV_{rn}_{k}", f"{rn}: {k} raster named in summary.json", "UNAVAILABLE", pth, "existing file" if (sm.get("constraints_resolved") or {}).get(k + "_raster", pth) else "not applied in this run")

        # counts and consistency
        served = tt[tt["status"].astype(str) == "SERVED"]
        pcm = {str(p): row for p, row in zip(pc["plan"], pc.to_dict("records"))}
        for scen in ("na", "ic"):
            pname = PLAN_NAMES[scen]
            if pname not in pcm:
                chk.add(f"PLAN_{rn}_{scen}", f"{rn}: plan_comparison has row {pname}", "UNAVAILABLE", list(pcm), pname)
        chk.add(f"CNT_{rn}_targets", f"{rn}: target_table rows == plan_comparison targets_total", "PASS" if len(tt) == int(pcm["network_aware"]["targets_total"]) else "FAIL",
                len(tt), int(pcm["network_aware"]["targets_total"]))
        chk.add(f"CNT_{rn}_targets_layer", f"{rn}: targets layer rows == target_table rows", "PASS" if len(tgt) == len(tt) else "FAIL", len(tgt), len(tt))
        n_na = 0 if routes["na"] is None else len(routes["na"])
        n_ic = 0 if routes["ic"] is None else len(routes["ic"])
        chk.add(f"CNT_{rn}_served_na", f"{rn}: SERVED rows == plan_comparison.targets_routed == network-aware route rows", "PASS" if (len(served) == int(pcm["network_aware"]["targets_routed"]) == n_na) else "FAIL",
                f"served={len(served)} routed={int(pcm['network_aware']['targets_routed'])} layer={n_na}", "all equal")
        chk.add(f"CNT_{rn}_routed_ic", f"{rn}: independent route rows == plan_comparison independent targets_routed", "PASS" if n_ic == int(pcm["independent_least_cost"]["targets_routed"]) else "FAIL",
                n_ic, int(pcm["independent_least_cost"]["targets_routed"]))
        wb = float(tgt[tgt["id"].astype(str).isin(set(served["target"].astype(str)))]["weight"].sum())
        chk.add(f"BEN_{rn}", f"{rn}: sum of weights of SERVED targets == plan_comparison.weighted_benefit", "PASS" if abs(wb - float(pcm["network_aware"]["weighted_benefit"])) < 0.011 else "FAIL",
                round(wb, 3), pcm["network_aware"]["weighted_benefit"])

        info = OrderedDict(targets=len(tt), served=len(served), unserved=len(tt) - len(served))
        # unserved targets
        for rec in tt[tt["status"].astype(str) != "SERVED"].to_dict("records"):
            unserved_rows.append(OrderedDict(run=rn, target=rec["target"], kind=rec["kind"], status=rec["status"],
                                             failure_reason="" if pd.isna(rec["failure_reason"]) else rec["failure_reason"], euclid_to_road_m=rec["euclid_to_road_m"]))

        dists = {}
        for scen in ("na", "ic"):
            rt = routes[scen]
            pname = PLAN_NAMES[scen]
            if rt is None:
                chk.add(f"LAYER_{rn}_{scen}", f"{rn}: route layer for {pname} readable", "UNAVAILABLE", "layer missing", "layer present")
                dists[scen] = None
                continue
            if rt.crs is None or rt.crs.to_epsg() != EXPECTED_EPSG:
                chk.add(f"CRS_{rn}_{scen}", f"{rn}: {pname} routes CRS", "FAIL", rt.crs, EXPECTED_EPSG)
            use = rt
            if scen == "na":
                if "connected" in rt.columns:
                    use = rt[to_bool(rt["connected"])]
                    chk.add(f"CONN_{rn}", f"{rn}: planner 'connected' flag on network-aware rows (geometric within tolerance)", "INFO",
                            f"{len(use)} of {len(rt)} True", "informational")
                else:
                    chk.add(f"CONN_{rn}", f"{rn}: 'connected' column on network-aware layer", "UNAVAILABLE", "column missing", "present")
            else:
                chk.add(f"CONN_{rn}_ic", f"{rn}: independent layer has no connectivity field; rows used as exported", "INFO", len(rt), "n/a")
            reach, orient = geometric_reach(use, tpoints, road_u, tol)
            if reach is None:
                chk.add(f"REACH_{rn}_{scen}", f"{rn}: geometric reach of {pname} routes", "UNAVAILABLE", "non-LineString geometry", "LineString")
            else:
                nr = int(sum(reach))
                chk.add(f"REACH_{rn}_{scen}", f"{rn}: {pname} routes whose network end lies within {tol:g} m of roads or of a route that does (geometry only, attach_to not used)",
                        "PASS" if nr == len(reach) else "FLAG", f"{nr} of {len(reach)}", "all",
                        "orientation verified from targets layer" if orient else "orientation NOT verified: both endpoints used")
            # lengths and costs
            row_pc = pcm.get(pname)
            tot_len = float(use["length_m"].sum())
            tot_cost = float(use["cost"].sum())
            ru = unary_union(list(use.geometry)) if len(use) else None
            geo_union = float(ru.length) if ru is not None else 0.0
            geo_sum = float(sum(g.length for g in use.geometry))
            if row_pc is not None and scen == "na":
                tl = float(row_pc["total_len_m"]); tol_len = 0.05 * len(use) + 0.1
                chk.add(f"LEN_{rn}_{scen}", f"{rn}: sum of layer length_m == plan_comparison total_len_m ({pname})", "PASS" if abs(tot_len - tl) <= tol_len else "FAIL",
                        round(tot_len, 2), tl, f"tolerance {tol_len:.2f} m for 0.1 m rounding")
                tsum = float(served["route_len_m"].sum()); csum = float(served["route_cost"].sum())
                chk.add(f"LEN_{rn}_table", f"{rn}: sum of SERVED route_len_m (target_table) == layer length sum", "PASS" if abs(tsum - tot_len) <= tol_len else "FAIL", round(tsum, 2), round(tot_len, 2))
                chk.add(f"COST_{rn}_table", f"{rn}: sum of SERVED route_cost (target_table) == layer cost sum", "PASS" if abs(csum - tot_cost) <= 0.05 * len(use) + 0.1 else "FAIL", round(csum, 2), round(tot_cost, 2))
            elif row_pc is not None:
                tl = float(row_pc["total_len_m"]); tol_len = 0.05 * len(use) + 0.1
                chk.add(f"LEN_{rn}_{scen}", f"{rn}: sum of layer length_m == plan_comparison total_len_m ({pname})", "PASS" if abs(tot_len - tl) <= tol_len else "FAIL",
                        round(tot_len, 2), tl, f"tolerance {tol_len:.2f} m for 0.1 m rounding")
            if row_pc is not None:
                uc = row_pc.get("unique_cost")
                if uc is not None and not pd.isna(uc):
                    chk.add(f"COST_{rn}_{scen}", f"{rn}: layer total cost >= planner unique cost ({pname})", "PASS" if tot_cost + 0.05 * len(use) + 0.1 >= float(uc) else "FAIL", round(tot_cost, 1), uc)
            rl_rows.append(OrderedDict(
                run=rn, scenario=SCENARIO_LABEL[scen], routes_in_layer=len(rt), routes_used=len(use), targets_total=len(tt),
                targets_served_table=len(served), unserved=len(tt) - len(served),
                total_len_m_layer=tot_len, total_len_m_planner=(float(row_pc["total_len_m"]) if row_pc else float("nan")),
                unique_len_m_planner=(float(row_pc["unique_len_m"]) if row_pc else float("nan")),
                shared_len_m_planner=(float(row_pc["shared_len_m"]) if row_pc else float("nan")),
                geometric_union_len_m=geo_union, geometric_sum_len_m=geo_sum,
                total_cost_units_layer=tot_cost, unique_cost_units_planner=(float(row_pc["unique_cost"]) if row_pc and not pd.isna(row_pc.get("unique_cost")) else float("nan")),
                weighted_benefit_planner=(float(row_pc["weighted_benefit"]) if row_pc else float("nan")),
                cost_unit_label="weighted routing cost units (NOT money)", monetary_cost_estimated=False))
            net = unary_union([road_u, ru]) if ru is not None else road_u
            dists[scen] = (cand.geometry.distance(net), fac.geometry.distance(net))
            per_poly[f"d_{rn}_{scen}_m"] = dists[scen][0].values

        # coverage rows
        for scen in ("na", "ic"):
            if dists[scen] is None:
                continue
            dprop = dists[scen][0]
            for sname, (mask, role, definition) in sets.items():
                n = int(mask.sum())
                for T in thresholds:
                    b_in = int(((cand["d_base_m"] <= T) & mask).sum())
                    p_in = int(((dprop <= T) & mask).sum())
                    sum_rows.append(OrderedDict(run=rn, scenario=SCENARIO_LABEL[scen], building_set=sname, set_role=role, threshold_m=T, n_polygons=n,
                                                baseline_n_within=b_in, proposed_n_within=p_in, baseline_pct=pct(b_in, n), proposed_pct=pct(p_in, n),
                                                abs_change_n=p_in - b_in, pp_change=(pct(p_in, n) - pct(b_in, n)) if n else float("nan")))
            # facilities
        for i, f in fac.iterrows():
            row = OrderedDict(run=rn, facility_id=f["facility_id_s"], facility_name=f["facility_name"], facility_type=f["facility_type"], target_id=f["target_id"],
                              dist_base_m=f["d_base_m"], dist_stored_m=f["dist_to_ref_road_m"])
            for scen in ("na", "ic"):
                row[f"dist_{scen}_m"] = float(dists[scen][1].iloc[i]) if dists[scen] is not None else float("nan")
            for T in thresholds:
                row[f"within_{T:g}_base"] = bool(f["d_base_m"] <= T)
                for scen in ("na", "ic"):
                    row[f"within_{T:g}_{scen}"] = bool(dists[scen][1].iloc[i] <= T) if dists[scen] is not None else None
            m = tt[tt["target"].astype(str) == f["target_id"]]
            if m.empty:
                chk.add(f"FAC_{rn}_{f['facility_id_s']}", f"{rn}: facility target {f['target_id']} present in target_table", "UNAVAILABLE", "not found", "found")
                row.update(planner_status="UNAVAILABLE", failure_reason="", route_len_m=float("nan"))
            else:
                m = m.iloc[0]
                row.update(planner_status=m["status"], failure_reason="" if pd.isna(m["failure_reason"]) else m["failure_reason"],
                           route_len_m=m["route_len_m"] if not pd.isna(m["route_len_m"]) else float("nan"))
            fac_rows.append(row)
        run_info[rn] = info

    summ_df = pd.DataFrame(sum_rows)
    # ---- definitional and monotonicity checks (derived from the data)
    if a.gap_m in thresholds:
        for sname in ("polygon_gap_flag_true", "gap_cluster_polygons"):
            sub = summ_df[(summ_df.building_set == sname) & (summ_df.threshold_m == a.gap_m)]
            if len(sub):
                chk.add(f"DEF_{sname}", f"baseline coverage of {sname} at T == gap_m is 0 by definition", "PASS" if (sub.baseline_n_within == 0).all() else "FAIL",
                        sub.baseline_n_within.unique().tolist(), 0)
    bad_mono = bad_prop = 0
    for _, grp in summ_df.groupby(["run", "scenario", "building_set"], sort=False):
        grp = grp.sort_values("threshold_m")
        if (grp.baseline_n_within.diff().dropna() < 0).any() or (grp.proposed_n_within.diff().dropna() < 0).any():
            bad_mono += 1
        if (grp.proposed_n_within < grp.baseline_n_within).any():
            bad_prop += 1
    chk.add("MONO_threshold", "coverage never decreases as the threshold grows", "PASS" if bad_mono == 0 else "FAIL", f"{bad_mono} violating groups", 0)
    chk.add("MONO_routes", "adding routes never reduces coverage", "PASS" if bad_prop == 0 else "FAIL", f"{bad_prop} violating groups", 0)
    chk.add("SAME_inputs", "all runs read the same access and roads files", "PASS", f"{os.path.basename(access_p)}; {os.path.basename(roads_p)}", "same")

    # ---- 5. write outputs (inputs untouched), then re-hash
    out.mkdir(parents=True, exist_ok=True)

    def wcsv(df, name):
        df.to_csv(out / name, index=False, float_format="%.3f")

    wcsv(summ_df, "access_gain_summary.csv")
    wcsv(pd.DataFrame(fac_rows), "facility_access_gain.csv")
    wcsv(pd.DataFrame(rl_rows), "route_length_cost.csv")
    wcsv(pd.DataFrame(unserved_rows, columns=["run", "target", "kind", "status", "failure_reason", "euclid_to_road_m"]), "unserved_targets.csv")
    wcsv(comp, "gap_flag_composition.csv")
    wcsv(pd.DataFrame(chk.rows), "checks.csv")
    pp = gpd.GeoDataFrame(per_poly, geometry="geometry", crs=cand.crs)
    for c in [c for c in pp.columns if c.startswith("d_")]:
        pp[c] = pp[c].round(3)
    pp["d_base_m"] = pp["d_base_m"].round(3)
    pp.to_file(out / "buildings_access.gpkg", layer="buildings_access", driver="GPKG")

    reg_after = OrderedDict((p, file_state(p)) for p in reg_before)
    changed = verify_unchanged(reg_before, reg_after)
    listing_after = OrderedDict((rn, dir_listing(r["dir"])) for rn, r in runs.items())
    dir_changed = [rn for rn in runs if listing_before[rn] != listing_after[rn]]
    chk.add("INPUT_unchanged", "SHA-256/size of every input identical before and after the run", "PASS" if not changed else "FAIL", f"{len(changed)} changed", 0, str(changed))
    chk.add("RUNDIR_unchanged", "file listing (name, size, mtime) of every run folder identical before and after", "PASS" if not dir_changed else "FAIL", dir_changed, "none")
    wcsv(pd.DataFrame(chk.rows), "checks.csv")

    # ---- 6. report text (no timestamps -> deterministic)
    L = []
    L.append(SCRIPT_VERSION + " - proximity-based access report (auxiliary; not the planner)")
    L.append("monetary_cost_estimated: false | cost units are weighted routing cost units, not money | routes are UNVERIFIED planning alternatives")
    L.append("")
    L.append("BUILDING SETS (observed counts; polygons, not verified buildings)")
    L.append(pd.DataFrame([OrderedDict(building_set=k, role=v[1], n_polygons=int(v[0].sum()), definition=v[2]) for k, v in sets.items()]).to_string(index=False))
    L.append("")
    L.append("POLYGON-LEVEL GAP FLAG versus CLUSTER MEMBERSHIP (kept separate)")
    L.append(comp.to_string(index=False))
    prim = 50.0 if 50.0 in thresholds else thresholds[len(thresholds) // 2]
    L.append("")
    L.append(f"COVERAGE AT {prim:g} m (baseline = reference roads only)")
    L.append(summ_df[summ_df.threshold_m == prim][["run", "scenario", "building_set", "n_polygons", "baseline_n_within", "proposed_n_within", "baseline_pct", "proposed_pct", "abs_change_n", "pp_change"]].round(2).to_string(index=False))
    L.append("")
    L.append("FACILITIES (separate from polygon statistics)")
    L.append(pd.DataFrame(fac_rows)[["run", "facility_id", "facility_type", "dist_base_m", "dist_na_m", "dist_ic_m", "planner_status", "failure_reason"]].round(2).to_string(index=False))
    L.append("")
    L.append("ROUTE LENGTH AND WEIGHTED ROUTING COST UNITS")
    L.append(pd.DataFrame(rl_rows)[["run", "scenario", "routes_used", "targets_total", "unserved", "total_len_m_layer", "unique_len_m_planner", "geometric_union_len_m", "total_cost_units_layer", "unique_cost_units_planner"]].round(1).to_string(index=False))
    L.append("")
    L.append("UNSERVED TARGETS (planner failure_reason; not evidence of a real access gap)")
    L.append(pd.DataFrame(unserved_rows).to_string(index=False) if unserved_rows else "none")
    L.append("")
    L.append("CHECKS NOT PASSING")
    nb = [r for r in chk.rows if r["status"] not in ("PASS", "INFO")]
    L.append(pd.DataFrame(nb)[["check_id", "status", "observed", "expected", "detail"]].to_string(index=False) if nb else "none")
    L.append("")
    L.append("LIMITATIONS")
    L.extend("- " + s for s in LIMITATIONS)
    (out / "access_gain_report.txt").write_text("\n".join(L) + "\n", encoding="utf-8")

    summary = OrderedDict(
        script=SCRIPT_VERSION, script_sha256=sha256_file(os.path.abspath(__file__)) if "__file__" in globals() else None,
        generated_utc=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        monetary_cost_estimated=False, cost_unit="weighted routing cost units (not money)", road_width_used=False,
        parameters=dict(runs=a.runs, thresholds_m=thresholds, gap_m=a.gap_m, polygon_dist_tol_m=a.polygon_dist_tol_m, facility_dist_tol_m=a.facility_dist_tol_m, tag=a.tag),
        software=lib_versions(),
        inputs=OrderedDict((p, dict(before=reg_before[p], after=reg_after[p])) for p in reg_before),
        provenance_rasters=OrderedDict((f"{k[0]}:{k[1]}", v) for k, v in provenance_rasters.items()),
        sets=OrderedDict((k, dict(role=v[1], definition=v[2], n_polygons=int(v[0].sum()))) for k, v in sets.items()),
        facilities=len(fac), runs_summary=run_info,
        checks=chk.rows, any_check_failed=chk.any_fail(), inputs_changed=[list(c) for c in changed], run_dirs_changed=dir_changed,
        limitations=LIMITATIONS,
        assumptions=["Layer and column names are those written by assess_building_access_v2.py and plan_network_v2.py; any missing field aborts the run before writing.",
                     "Route LineString orientation (first vertex = target point) is verified per run against the targets layer; otherwise both endpoints are used and flagged.",
                     "The planner's recorded attach tolerance is used for geometric reach; 15 m only if it is not recorded (flagged)."])
    (out / "access_gain_summary.json").write_text(json.dumps(summary, indent=2, default=str, sort_keys=False), encoding="utf-8")

    print("\n".join(L))
    print(f"\nWrote report to {out}")
    if changed or dir_changed:
        (out / "INPUT_CHANGED_REPORT_INVALID.txt").write_text("An input or run folder changed during execution: " + str(changed) + str(dir_changed) + "\n", encoding="utf-8")
        print("ERROR: inputs changed during execution; this report is INVALID")
        return 2
    if chk.any_fail():
        print("WARNING: one or more checks FAILED; see checks.csv. Do not use the numbers until resolved.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
