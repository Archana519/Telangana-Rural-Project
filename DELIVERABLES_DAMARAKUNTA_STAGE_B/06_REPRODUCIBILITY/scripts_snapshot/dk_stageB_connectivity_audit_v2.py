"""dk_stageB_connectivity_audit_v2.py (v2: house-phase ROAD-labelled routes are evaluated against roads UNION facility routes, label vs snap
mismatch reported separately (G09), line-level vs raster component evidence for off-main attachments (G10), zero-edge length check (L04);
all v1 checks and statuses kept) - READ-ONLY connectivity / GIS audit of existing Stage B run folders.

Never routes, never modifies an input. Writes only to <stageb-root>/_connectivity_audit_v1 (must not exist).
Statuses: PASS, FAIL, INFO, NOT_VERIFIABLE.

Network / attachment semantics this audit relies on (from plan_network_v2.py and dk_stageB_run_v1_3.py):
  * make_route(): the drawn LineString starts at the target point, follows 8-connected cell centres, and, if the
    last cell centre is not on the declared network, appends the nearest point of that network (end connector).
    So a correctly drawn route ENDS ON the declared network (distance ~0) by construction.
  * verify_network(): ok_local = distance(last cell centre, declared network) <= attach_tol_m AND
    distance(last drawn vertex, declared network) <= attach_tol_m; connected_to_roads additionally requires the
    attach chain to terminate at ROAD with every link ok_local, and no cycle.
  * Declared network: 'ROAD' = reference/tgrac_road_network.gpkg (union of lines); otherwise another route
    (attach_parent = that route's target_id, i.e. planner key).
  * road_cells_main_component = 10 m grid cells (all_touched rasterisation of the roads, passable cells only) of the
    largest road component, written as a MultiPolygon.
Independent rule used here (explicit): a link is TOUCH if the last vertex is within STRICT_TOL (0.01 m) of the declared
network geometry, WITHIN_TOL if within the planner's own attach_tol_m (read from config_stageB.json) but not touching,
GAP otherwise. A target is geometrically connected only if every link of its chain is TOUCH/WITHIN_TOL, there is no
cycle / dangling parent, and the chain ends on ROAD. Crossing lines are never treated as connected.
This is model connectivity on a planning grid; it says nothing about legal access, passability or field junctions.
"""
import argparse, hashlib, json, sys, datetime
from pathlib import Path
import numpy as np, pandas as pd, geopandas as gpd, fiona
from shapely.geometry import Point
from shapely.ops import unary_union
from shapely.strtree import STRtree

ST = ("PASS", "FAIL", "INFO", "NOT_VERIFIABLE")
REQ = ["routes.gpkg", "target_status.csv", "connectivity_checks.csv", "road_components.csv", "route_edges.csv",
       "facility_status.csv", "scenario_targets.csv", "config_stageB.json", "inputs_manifest_stageB.csv"]
PRIMARY = {"routes_network_houses": "house", "routes_network_facilities": "facility"}


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def mdt(df):
    df = df.fillna("")
    h = "| " + " | ".join(map(str, df.columns)) + " |\n|" + "---|" * len(df.columns) + "\n"
    return h + "\n".join("| " + " | ".join(str(v).replace("|", "/").replace("\n", " ") for v in r) + " |" for r in df.itertuples(index=False))


def boolcol(s):
    return s.astype(str).str.strip().str.lower().eq("true")


def classify_house_road_label(last_pt, roads_u, fac_geoms, strict, tol):
    """House-phase route labelled ROAD. The planner snaps the last vertex to the nearest point of roads UNION facility routes.
    Returns dict(status, snap_target, parent, dist, label_mismatch, reason). fac_geoms: {facility_id: geometry}.
    Geometric connectivity only; says nothing about real-world access, ownership or passability."""
    dr = float(last_pt.distance(roads_u)) if roads_u is not None else float("inf")
    fd = {k: float(last_pt.distance(g)) for k, g in fac_geoms.items()}
    fk, df = (min(fd.items(), key=lambda kv: kv[1]) if fd else (None, float("inf")))
    if dr <= strict:
        return dict(status="PASS", snap_target="ROAD_LINE", parent=None, dist=round(dr, 4), label_mismatch=False, reason="")
    if df <= strict:
        return dict(status="PASS", snap_target=f"FACILITY_ROUTE:{fk}", parent=fk, dist=round(df, 4), label_mismatch=True,
                    reason=f"labelled ROAD (end cell is a road cell) but the last vertex touches facility route {fk}; road line is {dr:.4f} m away")
    d = min(dr, df)
    tgt, par = ("ROAD_LINE", None) if dr <= df else (f"FACILITY_ROUTE:{fk}", fk)
    if d <= tol:
        return dict(status="INFO", snap_target=tgt, parent=par, dist=round(d, 4), label_mismatch=False, reason=f"last vertex {d:.4f} m from the declared combined network (roads + facility routes); within planner attach_tol_m but not touching")
    return dict(status="FAIL", snap_target=tgt, parent=par, dist=round(d, 4), label_mismatch=False, reason=f"last vertex {d:.4f} m from the declared combined network; exceeds attach_tol_m={tol}")


def line_components(segs, tol):
    tree = STRtree(segs); p = list(range(len(segs)))
    def f(x):
        while p[x] != x:
            p[x] = p[p[x]]; x = p[x]
        return x
    for i, sg in enumerate(segs):
        for j in tree.query(sg.buffer(tol)):
            if j != i and sg.distance(segs[j]) <= tol:
                p[f(i)] = f(j)
    return [f(i) for i in range(len(segs))]


def find_key(obj, key):
    if isinstance(obj, dict):
        if key in obj and not isinstance(obj[key], (dict, list)):
            return obj[key]
        for v in obj.values():
            r = find_key(v, key)
            if r is not None:
                return r
    return None


class Audit:
    def __init__(s):
        s.checks, s.det, s.inv, s.cov, s.lens = [], [], [], [], []

    def check(s, scen, cid, status, name, evidence, detail="", n=None, n_pass=None, n_info=None, n_fail=None, n_nv=None):
        assert status in ST
        s.checks.append(dict(scenario=scen, check_id=cid, status=status, check=name, evidence_source=evidence, detail=detail,
                             n_items=n, n_pass=n_pass, n_info=n_info, n_fail=n_fail, n_not_verifiable=n_nv))

    def item(s, scen, cid, kind, iid, status, value, evidence, reason):
        assert status in ST
        s.det.append(dict(scenario=scen, check_id=cid, item_kind=kind, item_id=iid, status=status, value=value, evidence_source=evidence, reason=reason))

    def roll(s, scen, cid, name, evidence, rows, fail_is="FAIL"):
        """Aggregate item rows (list of statuses) into one summary check."""
        c = pd.Series(rows).value_counts().to_dict() if rows else {}
        st = "FAIL" if c.get("FAIL") else ("NOT_VERIFIABLE" if c.get("NOT_VERIFIABLE") and not c.get("PASS") else ("INFO" if c.get("INFO") or c.get("NOT_VERIFIABLE") else "PASS"))
        if not rows:
            st = "NOT_VERIFIABLE"
        s.check(scen, cid, st, name, evidence, "; ".join(f"{k}={v}" for k, v in sorted(c.items())), len(rows), c.get("PASS", 0), c.get("INFO", 0), c.get("FAIL", 0), c.get("NOT_VERIFIABLE", 0))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stageb-root", required=True)
    ap.add_argument("--runs", nargs="+", default=["S2_fac_C0_s25_K3_P2", "S2_fac_C0_s25_omitmerge"])
    ap.add_argument("--roads", default=None, help="override the road file recorded in inputs_manifest_stageB.csv (role 'roads')")
    ap.add_argument("--strict-tol", type=float, default=0.01)
    ap.add_argument("--len-tol", type=float, default=0.01)
    ap.add_argument("--snap-sum-tol", type=float, default=0.02)
    ap.add_argument("--out-name", default="_connectivity_audit_v2")
    a = ap.parse_args()
    root = Path(a.stageb_root)
    out = root / a.out_name
    if out.exists():
        sys.exit(f"stopping: {out} already exists (never overwritten)")
    A = Audit()
    watched = {}                                   # path -> sha before
    CRS_EXPECT = "EPSG:32644"

    for run in a.runs:
        d = root / run
        S = run
        if not d.is_dir():
            A.check(S, "I01", "FAIL", "run directory exists", str(d), "directory missing; scenario skipped"); continue
        miss = [f for f in REQ if not (d / f).exists()]
        A.check(S, "I01", "FAIL" if miss else "PASS", "run directory and required files exist", str(d), ("missing: " + ", ".join(miss)) if miss else f"{len(REQ)} required files present")
        if miss:
            continue
        for f in REQ:
            watched[d / f] = sha(d / f)
        cfg = json.loads((d / "config_stageB.json").read_text(encoding="utf-8"))
        tol = find_key(cfg.get("args", cfg), "attach_tol_m"); snapm = find_key(cfg.get("args", cfg), "snap_m")
        if tol is None:
            tol, tsrc = 15.0, "NOT FOUND in config; planner default 15.0 assumed"
            A.check(S, "I02", "INFO", "attach tolerance", "config_stageB.json", tsrc)
        else:
            tol = float(tol); A.check(S, "I02", "INFO", "attach tolerance (planner attach_tol_m)", "config_stageB.json", f"attach_tol_m={tol}, snap_m={snapm}")
        # ---- roads
        mf = pd.read_csv(d / "inputs_manifest_stageB.csv")
        rpath = Path(a.roads) if a.roads else None
        if rpath is None:
            r_ = mf[mf.role == "roads"]
            rpath = Path(r_.path.iloc[0]) if len(r_) else None
        roads_u, roads_g = None, None
        if rpath is None or not rpath.exists():
            A.check(S, "I03", "NOT_VERIFIABLE", "source road network available", "inputs_manifest_stageB.csv role=roads", f"road file not found: {rpath}")
        else:
            watched[rpath] = sha(rpath)
            man_sha = mf[mf.role == "roads"].sha256.iloc[0] if (mf.role == "roads").any() else None
            A.check(S, "I03", "PASS" if man_sha == watched[rpath] else ("INFO" if man_sha is None else "FAIL"), "road file hash equals the hash recorded when the run was made", str(rpath),
                    f"recorded={man_sha}; now={watched[rpath]}")
        gp = d / "routes.gpkg"
        layers = fiona.listlayers(str(gp))
        L = {n: gpd.read_file(gp, layer=n) for n in layers}
        for n, g in L.items():
            geo = g.geometry
            nul = int(geo.isna().sum()); emp = int(geo[geo.notna()].is_empty.sum()); inv = int((~geo[geo.notna()].is_valid).sum())
            crs = g.crs.to_string() if g.crs else None
            A.inv.append(dict(scenario=S, file="routes.gpkg" if True else "", layer=n, n_features=len(g), crs=crs, geometry_types=";".join(sorted(set(geo.dropna().geom_type))),
                              null_geom=nul, empty_geom=emp, invalid_geom=inv, columns=";".join(c for c in g.columns if c != "geometry"), evidence_source=str(gp)))
            prim = n in PRIMARY or n in ("targets_houses", "targets_facilities", "road_cells_main_component")
            bad = (crs != CRS_EXPECT) or nul or emp or inv
            A.check(S, f"I04:{n}", ("FAIL" if bad else "PASS") if prim else ("INFO" if bad else "PASS"), f"layer {n}: CRS {CRS_EXPECT}, no null/empty/invalid geometry", str(gp),
                    f"n={len(g)} crs={crs} null={nul} empty={emp} invalid={inv}" + ("" if prim else " (baseline/alternative layer, not part of the network plan)"))
        if roads_u is None and rpath is not None and rpath.exists():
            rg = gpd.read_file(rpath)
            A.inv.append(dict(scenario=S, file=rpath.name, layer="(first layer)", n_features=len(rg), crs=rg.crs.to_string() if rg.crs else None,
                              geometry_types=";".join(sorted(set(rg.geometry.dropna().geom_type))), null_geom=int(rg.geometry.isna().sum()),
                              empty_geom=int(rg.geometry[rg.geometry.notna()].is_empty.sum()), invalid_geom=int((~rg.geometry[rg.geometry.notna()].is_valid).sum()),
                              columns=";".join(c for c in rg.columns if c != "geometry"), evidence_source=str(rpath)))
            rg = rg[rg.geometry.notna() & ~rg.geometry.is_empty].to_crs(CRS_EXPECT)
            roads_g = rg.geometry.explode(index_parts=False).reset_index(drop=True)
            roads_u = unary_union(list(roads_g))
        ts = pd.read_csv(d / "target_status.csv"); cc = pd.read_csv(d / "connectivity_checks.csv"); fs = pd.read_csv(d / "facility_status.csv")
        st_ = pd.read_csv(d / "scenario_targets.csv"); re_ = pd.read_csv(d / "route_edges.csv"); rc_ = pd.read_csv(d / "road_components.csv")
        for c_ in ("target_id",):
            cc[c_] = cc[c_].astype(str)
        rh, rf = L.get("routes_network_houses"), L.get("routes_network_facilities")
        th, tf = L.get("targets_houses"), L.get("targets_facilities")
        # ---- coverage
        def cover(kind, scen_ids, status_df, status_idcol, route_gdf, targets_gdf, conn_kind):
            sid = set(map(str, scen_ids))
            rid = list(map(str, route_gdf.target_id)) if route_gdf is not None else []
            tid = list(map(str, targets_gdf.target_id)) if targets_gdf is not None else []
            sdf = set(map(str, status_df[status_idcol]))
            cid = list(cc[cc.kind == conn_kind].target_id)
            dup_r = sorted({x for x in rid if rid.count(x) > 1}); dup_c = sorted({x for x in cid if cid.count(x) > 1})
            if kind == "house":
                routed_status = set(map(str, status_df[status_df.primary_status == "ROUTED"][status_idcol])); failed = sorted(sdf - routed_status)
            else:
                routed_status = set(map(str, status_df[status_df.status == "ROUTED"][status_idcol])); failed = sorted(sdf - routed_status)
            row = dict(scenario=S, kind=kind, n_scenario_targets=len(sid), n_status_records=len(sdf), n_target_points_layer=len(set(tid)), n_route_features=len(rid), n_unique_route_ids=len(set(rid)),
                       n_connectivity_rows=len(cid), n_status_routed=len(routed_status), n_failed_or_not_routed=len(failed), duplicate_route_ids=";".join(dup_r), duplicate_connectivity_ids=";".join(dup_c),
                       in_scenario_not_in_status=";".join(sorted(sid - sdf)), in_status_not_in_scenario=";".join(sorted(sdf - sid)),
                       in_scenario_not_routed_layer=";".join(sorted(sid - set(rid))), in_routed_layer_not_scenario=";".join(sorted(set(rid) - sid)),
                       in_routed_layer_not_connectivity=";".join(sorted(set(rid) - set(cid))), in_connectivity_not_routed_layer=";".join(sorted(set(cid) - set(rid))),
                       in_scenario_not_target_points=";".join(sorted(sid - set(tid))), failed_ids=";".join(failed),
                       evidence_source="scenario_targets.csv|target_status.csv|facility_status.csv|routes.gpkg|connectivity_checks.csv")
            A.cov.append(row)
            ok = (sid == sdf == set(rid) == set(cid) == set(tid)) and not dup_r and not dup_c and not failed
            A.check(S, f"C01:{kind}", "PASS" if ok else "FAIL", f"{kind} target coverage: scenario = status = route layer = connectivity = target points, no duplicates, none failed", row["evidence_source"],
                    f"scenario={len(sid)} status={len(sdf)} routes={len(rid)} connectivity={len(cid)} target_points={len(set(tid))} failed={len(failed)} duplicates={len(dup_r)+len(dup_c)}")
        if rh is not None and th is not None:
            cover("house", st_.planner_key, ts, "planner_key", rh, th, "house")
        else:
            A.check(S, "C01:house", "NOT_VERIFIABLE", "house coverage", "routes.gpkg", "routes_network_houses or targets_houses layer missing")
        if rf is not None and tf is not None:
            cover("facility", fs.facility_id, fs, "facility_id", rf, tf, "facility")
        else:
            A.check(S, "C01:facility", "NOT_VERIFIABLE", "facility coverage", "routes.gpkg", "routes_network_facilities or targets_facilities layer missing")
        # cand_id cross-match (houses)
        if rh is not None:
            m = rh.merge(st_[["planner_key", "cand_id"]].astype({"planner_key": str}), left_on=rh.target_id.astype(str), right_on="planner_key", how="left", suffixes=("", "_sc"))
            mism = int((m.cand_id.astype(str) != m.cand_id_sc.astype(str)).sum())
            A.check(S, "C02", "PASS" if mism == 0 else "FAIL", "route cand_id equals scenario_targets cand_id for the same target_id (houses)", "routes.gpkg vs scenario_targets.csv", f"mismatches={mism} of {len(rh)}")

        # ---- planner evidence
        def tcount(df, col):
            return boolcol(df[col]).sum() if col in df else None
        for kind in ("house", "facility"):
            sub = cc[cc.kind == kind]
            n = len(sub)
            fields = ["reaches_main_road_component", "planner_connected_to_roads", "cell_graph_connected", "planner_ok_local", "endpoint_ok"]
            vals = {f: int(boolcol(sub[f]).sum()) for f in fields if f in sub}
            hv = int((pd.to_numeric(sub.hard_violations, errors="coerce").fillna(0) > 0).sum())
            terminal = sub.chain_terminal.value_counts().to_dict()
            ac = sub.attach_class.value_counts().to_dict()
            allt = n > 0 and all(v == n for v in vals.values()) and hv == 0
            A.check(S, f"P01:{kind}", "PASS" if allt else "FAIL", f"planner evidence ({kind}): local endpoint fields AND wider-network fields all true, no hard violations", "connectivity_checks.csv",
                    f"n={n}; true-counts {vals}; hard_violations>0: {hv}; chain_terminal {terminal}; attach_class {ac}. Local (planner_ok_local, endpoint_ok) differ from wider-network "
                    "(reaches_main_road_component, planner_connected_to_roads, cell_graph_connected) evidence.")
        # consistency CSV <-> CSV
        mh = ts.assign(target_id=ts.planner_key.astype(str)).merge(cc[cc.kind == "house"], on="target_id", how="inner", suffixes=("_ts", "_cc"))
        pairs = [("primary_reaches_main_road_component", "reaches_main_road_component"), ("primary_attach_class", "attach_class"), ("primary_chain_depth", "chain_depth"), ("primary_end_snap_m", "end_snap_m")]
        bad = {}
        for x, y in pairs:
            if x in mh and y in mh:
                if "snap" in x:
                    bad[y] = int((pd.to_numeric(mh[x], errors="coerce").fillna(-1) - pd.to_numeric(mh[y], errors="coerce").fillna(-2)).abs().gt(0.011).sum())
                elif x.endswith("component"):
                    bad[y] = int((boolcol(mh[x]) != boolcol(mh[y])).sum())
                else:
                    bad[y] = int((mh[x].astype(str) != mh[y].astype(str)).sum())
        A.check(S, "P02", "PASS" if bad and not any(bad.values()) else ("NOT_VERIFIABLE" if not bad else "FAIL"), "target_status.csv and connectivity_checks.csv agree (houses)", "target_status.csv vs connectivity_checks.csv", f"mismatches per field: {bad}; rows compared={len(mh)}")

        # ---- independent geometric / network check
        if roads_u is None or rh is None or rf is None:
            A.check(S, "G00", "NOT_VERIFIABLE", "independent geometric connectivity", "routes.gpkg + source roads", "source road file or primary route layers unavailable; planner fields remain the only evidence")
        else:
            main_poly_g = L.get("road_cells_main_component")
            main_poly = unary_union(list(main_poly_g.geometry)) if main_poly_g is not None and len(main_poly_g) else None
            routes = {}
            for kind, g in (("house", rh), ("facility", rf)):
                for _, r in g.iterrows():
                    routes[str(r.target_id)] = dict(kind=kind, geom=r.geometry, ac=str(r.attach_class), ap=str(r.attach_parent), len_m=float(r.len_m))
            tpt = {}
            for g in (th, tf):
                for _, r in g.iterrows():
                    tpt[str(r.target_id)] = r.geometry
            ccx = cc.set_index("target_id")
            links, chainrows = {}, []
            g_rows = {k: [] for k in ("G01", "G02", "G03", "G04", "G09", "G10")}
            fac_geoms = {k: v["geom"] for k, v in routes.items() if v["kind"] == "facility"}
            lc = {}
            if main_poly is not None:
                for tl_ in (a.strict_tol, 10.0, 20.0):
                    lab_ = line_components(list(roads_g), tl_)
                    inpoly_ = pd.Series([sg.intersection(main_poly).length for sg in roads_g]).groupby(lab_).sum()
                    lc[tl_] = (lab_, inpoly_.idxmax() if inpoly_.max() > 0 else None)
            for tid, r in routes.items():
                co = list(r["geom"].coords)
                p0, p1 = Point(co[0]), Point(co[-1])
                tp = tpt.get(tid)
                orient = ""
                if tp is not None and p1.distance(tp) < p0.distance(tp):
                    p0, p1 = p1, p0; orient = " (line digitised end-to-start; nearer-to-target vertex used as start)"
                # G01 start at target
                if tp is None:
                    s0, v0, rs = "NOT_VERIFIABLE", None, "no target point"
                else:
                    v0 = round(p0.distance(tp), 4)
                    s0 = "PASS" if v0 <= a.strict_tol else ("INFO" if snapm is None or v0 <= float(snapm) else "FAIL")
                    rs = "" if s0 == "PASS" else (f"first vertex {v0} m from the target point" + (" (<= planner snap_m)" if s0 == "INFO" else " (> snap_m)")) + orient
                g_rows["G01"].append(s0); A.item(S, "G01", r["kind"], tid, s0, v0, "routes.gpkg (route first vertex vs targets_* point)", rs)
                # G02 link to declared network
                snap_target, mism = None, False
                if r["ac"] == "ROAD" and r["kind"] == "house":
                    c_ = classify_house_road_label(p1, roads_u, fac_geoms, a.strict_tol, tol)
                    ls = {"PASS": "TOUCH", "INFO": "WITHIN_TOL", "FAIL": "GAP"}[c_["status"]]
                    s2, v2, rs2, parent, snap_target, mism = c_["status"], c_["dist"], (c_["reason"] if c_["status"] != "PASS" else ""), c_["parent"], c_["snap_target"], c_["label_mismatch"]
                    ev2 = "routes.gpkg last vertex vs combined network (tgrac_road_network.gpkg UNION facility routes; house-phase goals)"
                else:
                    if r["ac"] == "ROAD":
                        net, parent = roads_u, None
                    elif r["ac"] in ("HOUSE_ROUTE", "FACILITY_ROUTE") and r["ap"] in routes and r["ap"] != tid:
                        net, parent = routes[r["ap"]]["geom"], r["ap"]
                    else:
                        net, parent = None, None
                    ev2 = f"routes.gpkg last vertex vs {'tgrac_road_network.gpkg' if r['ac']=='ROAD' else 'parent route'}"
                    if net is None:
                        s2, v2, rs2, ls = "FAIL", None, f"declared attachment '{r['ac']}' parent '{r['ap']}' cannot be resolved to a road or an existing route", "UNRESOLVED"
                    else:
                        v2 = round(p1.distance(net), 4)
                        ls = "TOUCH" if v2 <= a.strict_tol else ("WITHIN_TOL" if v2 <= tol else "GAP")
                        s2 = "PASS" if ls == "TOUCH" else ("INFO" if ls == "WITHIN_TOL" else "FAIL")
                        rs2 = "" if s2 == "PASS" else (f"last vertex {v2} m from the declared network; " + ("within planner attach_tol_m but not touching" if s2 == "INFO" else f"exceeds attach_tol_m={tol}"))
                links[tid] = dict(parent=parent, ls=ls, ac=r["ac"], end=p1)
                if r["ac"] == "ROAD" and r["kind"] == "house":
                    s9 = "INFO" if mism else "PASS"
                    g_rows["G09"].append(s9)
                    A.item(S, "G09", "house", tid, s9, snap_target, "routes.gpkg label (attach_class) vs snapped geometry", ("label/snap mismatch: " + c_["reason"]) if mism else "")
                g_rows["G02"].append(s2); A.item(S, "G02", r["kind"], tid, s2, v2, ev2, rs2)
            # chains
            comp_of = {}
            for tid, r in routes.items():
                seen, cur, st, why = [], tid, "PASS", ""
                while True:
                    if cur in seen:
                        st, why = "FAIL", "attachment cycle: " + "->".join(seen + [cur]); break
                    seen.append(cur)
                    lk = links[cur]
                    if lk["ls"] == "UNRESOLVED":
                        st, why = "FAIL", f"unresolved declared attachment at {cur} ({lk['ac']})"; break
                    if lk["ls"] == "GAP":
                        st, why = "FAIL", f"geometric gap at link {cur}"; break
                    if lk["ls"] == "WITHIN_TOL" and st == "PASS":
                        st, why = "INFO", f"link {cur} within planner tolerance but not touching"
                    if lk["parent"] is None:
                        break
                    cur = lk["parent"]
                terminal_ok = (st != "FAIL")
                comp_of[tid] = cur if terminal_ok else None
                A.item(S, "G03", r["kind"], tid, st, len(seen) - 1, "routes.gpkg chain walk over attach_parent links", why)
                g_rows["G03"].append(st)
                # G04 terminal on main component + agreement with planner flag
                if st == "FAIL":
                    s4, v4, rs4 = "FAIL", None, "chain does not reach ROAD geometrically"
                elif main_poly is None:
                    s4, v4, rs4 = "NOT_VERIFIABLE", None, "road_cells_main_component layer missing"
                else:
                    ep = links[cur]["end"]; v4 = round(ep.distance(main_poly), 4)
                    half_diag = 10 * 2 ** 0.5 / 2
                    s4 = "PASS" if v4 <= a.strict_tol else ("INFO" if v4 <= half_diag else "FAIL")
                    rs4 = "" if s4 == "PASS" else (f"road attachment point {v4} m from the planner's main-component cells" + (" (inside one half cell diagonal, 7.07 m: rasterisation offset)" if s4 == "INFO" else " (outside the main component)"))
                    pf = bool(boolcol(pd.Series([ccx.loc[tid, "reaches_main_road_component"]])).iloc[0]) if tid in ccx.index else None
                    if pf is not None and pf != (s4 in ("PASS", "INFO")):
                        s4, rs4 = "FAIL", rs4 + f"; DISAGREES with planner reaches_main_road_component={pf}"
                    elif s4 == "FAIL":
                        rs4 += f"; planner reaches_main_road_component={pf} (agrees): attached to a road component other than the main one"
                g_rows["G04"].append(s4); A.item(S, "G04", r["kind"], tid, s4, v4, "routes.gpkg terminal attachment point vs road_cells_main_component", rs4)
                if s4 == "FAIL" and st != "FAIL" and lc:
                    ep_ = links[cur]["end"]; idx_ = int(np.argmin([sg.distance(ep_) for sg in roads_g]))
                    parts = []
                    for tl_, (lab_, mlab_) in lc.items():
                        parts.append(f"{tl_:g} m: " + ("n/a" if mlab_ is None else ("same line component as the main network" if lab_[idx_] == mlab_ else "separate line component")))
                    A.item(S, "G10", r["kind"], tid, "INFO", v4, "tgrac_road_network.gpkg line components vs road_cells_main_component",
                           "planner (raster cells): not on the main component. Source road lines at joining tolerance " + "; ".join(parts) + ". Where the line data are joined but the cell component is not, the discrepancy lies between line topology and raster road-cell connectivity; the exact rasterisation cause is NOT established by this check.")
                    g_rows["G10"].append("INFO")
            A.roll(S, "G01", "route starts at its target point (<=0.01 m)", "routes.gpkg + targets_*", g_rows["G01"])
            A.roll(S, "G02", f"route end lies on declared network (touch <= {a.strict_tol} m; planner tolerance {tol} m)", "routes.gpkg + tgrac_road_network.gpkg", g_rows["G02"])
            A.roll(S, "G03", "every attach chain is geometrically unbroken and ends on ROAD (no cycle / dangling parent)", "routes.gpkg", g_rows["G03"])
            A.roll(S, "G09", "label vs snapped geometry for house routes labelled ROAD (INFO = label says road cell, drawn end snapped to a facility route)", "routes.gpkg", g_rows["G09"])
            A.roll(S, "G10", "off-main attachments: source road-line connectivity vs raster road-cell connectivity (INFO only, explanatory)", "tgrac_road_network.gpkg + road_cells_main_component", g_rows["G10"]) if g_rows["G10"] else None
            A.roll(S, "G04", "chain terminal lies on the planner's main road component and agrees with reaches_main_road_component", "routes.gpkg + road_cells_main_component + connectivity_checks.csv", g_rows["G04"])
            # route groups (union-find)
            par = {t: t for t in routes}; par["ROAD"] = "ROAD"
            def f_(x):
                while par[x] != x:
                    par[x] = par[par[x]]; x = par[x]
                return x
            for t, lk in links.items():
                if lk["ls"] in ("TOUCH", "WITHIN_TOL"):
                    other = "ROAD" if lk["ac"] == "ROAD" else lk["parent"]
                    if other in par:
                        par[f_(t)] = f_(other)
            groups = {}
            for t in routes:
                groups.setdefault(f_(t), []).append(t)
            off = [g for r_, g in groups.items() if f_("ROAD") != r_]
            A.check(S, "G05", "PASS" if not off else "FAIL", "route groups: all routes belong to one connected group containing the road network", "routes.gpkg link graph",
                    f"groups={len(groups)}; groups not containing ROAD={len(off)}; routes in them={sum(len(g) for g in off)}", len(groups))
            for g in off:
                for t in g:
                    A.item(S, "G05", routes[t]["kind"], t, "FAIL", len(g), "routes.gpkg link graph", "route group not connected to the road network")
            # roads vs connectors
            stat = set(rh.status.astype(str)) | set(rf.status.astype(str))
            A.check(S, "G06", "PASS" if stat == {"UNVERIFIED_PLANNING_ALTERNATIVE_NOT_A_ROAD"} else "INFO", "proposed routes are labelled as planning proxies and are held in layers separate from the existing roads", "routes.gpkg status field", f"distinct status values: {sorted(stat)}")
            near = unary_union([roads_u.buffer(1.0)])
            tot = sum(r["geom"].length for r in routes.values()); ov = sum(r["geom"].intersection(near).length for r in routes.values())
            A.check(S, "G07", "INFO", "share of proposed route length lying within 1 m of existing roads (should be small; routes attach to roads, not trace them)", "routes.gpkg vs tgrac_road_network.gpkg",
                    f"{ov:.2f} m of {tot:.2f} m ({100*ov/max(tot,1e-9):.2f}%)")
            # independent road components (INFO)
            segs = list(roads_g); tree = STRtree(segs)
            for tolr in (a.strict_tol, 10.0):
                p_ = list(range(len(segs)))
                def fr(x):
                    while p_[x] != x:
                        p_[x] = p_[p_[x]]; x = p_[x]
                    return x
                for i, s in enumerate(segs):
                    for j in tree.query(s.buffer(tolr)):
                        if j != i and s.distance(segs[j]) <= tolr:
                            p_[fr(i)] = fr(j)
                lens = pd.Series([s.length for s in segs]).groupby([fr(i) for i in range(len(segs))]).sum().sort_values(ascending=False)
                A.check(S, f"G08:{tolr:g}", "INFO", f"independent connected components of the source road lines at joining tolerance {tolr:g} m", "tgrac_road_network.gpkg",
                        f"components={len(lens)}; largest={lens.iloc[0]:.1f} m of {lens.sum():.1f} m; planner road_components.csv lists {len(rc_)} cell components (is_main={int(rc_.is_main.sum())}). Informational: planner components are raster cells, not line topology.")

        # ---- length consistency
        if rh is not None and rf is not None:
            snaps_h = ts.assign(target_id=ts.planner_key.astype(str)).set_index("target_id")
            edge_sum = re_.groupby(["scope", "route_id"]).len_m.sum()
            rows1, rows2, rows3, rows4 = [], [], [], []
            for kind, g, scope in (("house", rh, "house_phase"), ("facility", rf, "facility_phase")):
                for _, r in g.iterrows():
                    tid = str(r.target_id); gl = float(r.geometry.length); lm = float(r.len_m); df_ = gl - lm
                    s1 = "PASS" if abs(df_) <= a.len_tol else "FAIL"
                    A.lens.append(dict(scenario=S, kind=kind, target_id=tid, comparison="geometry_length_vs_len_m", value_a=gl, value_b=lm, diff_m=df_, tolerance_m=a.len_tol, status=s1,
                                       evidence_source="routes.gpkg geometry (CRS EPSG:32644, metres) vs routes.gpkg len_m", reason="" if s1 == "PASS" else "difference exceeds tolerance"))
                    rows1.append(s1)
                    # vs status csv
                    if kind == "house" and tid in snaps_h.index:
                        v = pd.to_numeric(snaps_h.loc[tid, "primary_len_m"], errors="coerce"); src = "target_status.csv primary_len_m"
                    elif kind == "facility":
                        q = fs[fs.facility_id.astype(str) == tid]; v = pd.to_numeric(q.len_m.iloc[0], errors="coerce") if len(q) else np.nan; src = "facility_status.csv len_m"
                    else:
                        v, src = np.nan, "status csv"
                    if pd.isna(v):
                        s2, d2 = "NOT_VERIFIABLE", np.nan
                    else:
                        d2 = lm - float(v); s2 = "PASS" if abs(d2) <= a.len_tol else "FAIL"
                    A.lens.append(dict(scenario=S, kind=kind, target_id=tid, comparison="len_m_vs_status_csv", value_a=lm, value_b=None if pd.isna(v) else float(v), diff_m=d2, tolerance_m=a.len_tol, status=s2,
                                       evidence_source=f"routes.gpkg len_m vs {src}", reason="" if s2 == "PASS" else ("no status value" if s2 == "NOT_VERIFIABLE" else "difference exceeds tolerance")))
                    rows2.append(s2)
                    # edges + connectors
                    if kind == "house" and (scope, tid) in edge_sum.index and tid in snaps_h.index and tid in ccx.index:
                        es = float(edge_sum[(scope, tid)]); ss = float(pd.to_numeric(snaps_h.loc[tid, "primary_start_snap_m"], errors="coerce")); ee = float(pd.to_numeric(ccx.loc[tid, "end_snap_m"], errors="coerce"))
                        tot_ = es + ss + ee; d3 = lm - tot_; s3 = "PASS" if abs(d3) <= a.snap_sum_tol else "FAIL"
                        A.lens.append(dict(scenario=S, kind=kind, target_id=tid, comparison="len_m_vs_grid_edges_plus_connectors", value_a=lm, value_b=tot_, diff_m=d3, tolerance_m=a.snap_sum_tol, status=s3,
                                           evidence_source="route_edges.csv (scope house_phase) + target_status.csv start snap + connectivity_checks.csv end snap",
                                           reason="" if s3 == "PASS" else "difference exceeds tolerance (start snap is exported rounded to 0.01 m)"))
                        rows3.append(s3)
                    elif kind == "facility":
                        A.lens.append(dict(scenario=S, kind=kind, target_id=tid, comparison="len_m_vs_grid_edges_plus_connectors", value_a=lm, value_b=None, diff_m=np.nan, tolerance_m=a.snap_sum_tol, status="NOT_VERIFIABLE",
                                           evidence_source="route_edges.csv", reason="facility start-connector length is not exported, so edges + connectors cannot be reconstructed"))
                        rows3.append("NOT_VERIFIABLE")
                    else:
                        A.lens.append(dict(scenario=S, kind=kind, target_id=tid, comparison="len_m_vs_grid_edges_plus_connectors", value_a=lm, value_b=None, diff_m=np.nan, tolerance_m=a.snap_sum_tol, status="NOT_VERIFIABLE",
                                           evidence_source="route_edges.csv", reason="no route_edges.csv rows or snap values for this route; a route with zero grid edges (start cell already a goal cell) writes no rows - see L04 for the alternative check"))
                        rows3.append("NOT_VERIFIABLE")
                        if kind == "house" and tid in snaps_h.index and tid in ccx.index and (scope, tid) not in edge_sum.index:
                            ss4 = float(pd.to_numeric(snaps_h.loc[tid, "primary_start_snap_m"], errors="coerce")); ee4 = float(pd.to_numeric(ccx.loc[tid, "end_snap_m"], errors="coerce"))
                            d4 = lm - (ss4 + ee4); s4_ = "PASS" if abs(d4) <= a.snap_sum_tol else "FAIL"
                            A.lens.append(dict(scenario=S, kind=kind, target_id=tid, comparison="len_m_vs_start_snap_plus_end_snap_zero_edge_route", value_a=lm, value_b=ss4 + ee4, diff_m=d4, tolerance_m=a.snap_sum_tol, status=s4_,
                                               evidence_source="target_status.csv start snap + connectivity_checks.csv end snap (route has no route_edges rows)", reason="" if s4_ == "PASS" else "difference exceeds tolerance"))
                            rows4.append(s4_)
            A.roll(S, "L01", f"geometry length equals stored len_m (|diff| <= {a.len_tol} m; EPSG:32644 metres)", "routes.gpkg", rows1)
            A.roll(S, "L02", f"stored len_m equals status CSV length (|diff| <= {a.len_tol} m)", "routes.gpkg vs target_status.csv / facility_status.csv", rows2)
            if rows4: A.roll(S, "L04", f"routes without route_edges rows: len_m equals start snap + end snap (zero grid edges; |diff| <= {a.snap_sum_tol} m)", "target_status.csv + connectivity_checks.csv", rows4)
            A.roll(S, "L03", f"stored len_m equals grid-edge sum + connectors (|diff| <= {a.snap_sum_tol} m; facilities NOT_VERIFIABLE because the facility start-connector length is not exported separately)", "route_edges.csv + CSV snaps", rows3)

    # ---- write
    out.mkdir(parents=True)
    inv = pd.DataFrame(A.inv); cov = pd.DataFrame(A.cov); lens = pd.DataFrame(A.lens)
    chk = pd.DataFrame(A.checks); det = pd.DataFrame(A.det)
    inv.to_csv(out / "layer_inventory.csv", index=False); cov.to_csv(out / "target_coverage.csv", index=False); lens.to_csv(out / "length_consistency.csv", index=False)
    chk.to_csv(out / "connectivity_summary.csv", index=False)
    exc = pd.concat([det[det.status != "PASS"] if len(det) else det, lens[lens.status != "PASS"].rename(columns={"comparison": "check_id", "kind": "item_kind", "target_id": "item_id", "diff_m": "value"})[["scenario", "check_id", "item_kind", "item_id", "status", "value", "evidence_source", "reason"]] if len(lens) else lens], ignore_index=True)
    exc.to_csv(out / "connectivity_exceptions.csv", index=False)
    # read-only proof
    changed = [str(p) for p, h in watched.items() if sha(p) != h]
    # internal consistency
    probs = []
    if not set(chk.status) <= set(ST): probs.append("invalid status in summary")
    for sc in chk.scenario.unique():
        for cid in ("G02", "G03", "L01"):
            r = chk[(chk.scenario == sc) & (chk.check_id == cid)]
            if len(r):
                n_exc = int(((det.scenario == sc) & (det.check_id == cid) & (det.status == "FAIL")).sum()) if cid.startswith("G") else int(((lens.scenario == sc) & (lens.comparison == "geometry_length_vs_len_m") & (lens.status == "FAIL")).sum())
                if int(r.n_fail.iloc[0]) != n_exc: probs.append(f"{sc} {cid}: summary fail count != item rows")
    if changed: probs.append("INPUT FILES CHANGED: " + ";".join(changed))
    pd.DataFrame([dict(check="inputs unchanged after audit (sha256 of every file read)", status="FAIL" if changed else "PASS", detail=f"{len(watched)} files hashed before and after")]).to_csv(out / "readonly_proof.csv", index=False)
    cnt = chk.groupby(["scenario", "status"]).size().unstack(fill_value=0)
    md = ["# Stage B connectivity / GIS audit v2 (read-only)", "", f"Generated {datetime.datetime.now():%Y-%m-%d %H:%M} by `dk_stageB_connectivity_audit_v2.py`. No route was regenerated and no input file was modified (sha256 of {len(watched)} inputs identical before and after: {'YES' if not changed else 'NO'}).", "",
          "Model connectivity on a planning grid only. Nothing here establishes legal access, ownership, passability or a field-verified junction.", "", "## Rule and tolerances", "",
          f"- Strict touch tolerance {a.strict_tol} m: the planner draws the last vertex ON the declared network (nearest point), so a correct link has distance ~0.",
          "- Planner tolerance `attach_tol_m` is read from each run's `config_stageB.json`; a link within it but not touching is reported INFO, beyond it FAIL.",
          f"- Length tolerance {a.len_tol} m for geometry vs `len_m` (both metres in EPSG:32644); {a.snap_sum_tol} m for edges + connectors (start snap exported to 0.01 m).",
          "- House-phase routes labelled ROAD are checked against the planner's declared combined network (road line UNION facility routes); G09 reports separately when the label (end cell is a road cell) and the snapped geometry (a facility route) differ.",
          "- Off-main attachments: G04 keeps the planner's raster definition of the main component (FAIL); G10 adds source road-line component evidence (INFO) and does not prove the rasterisation cause.",
          "- A target counts as geometrically connected only if every link of its attach chain is TOUCH/WITHIN_TOL, there is no cycle or dangling parent, and the chain ends on a road; crossings are never counted as connections.", "",
          "## Status counts per scenario", "", mdt(cnt.reset_index()), "", "## Checks", ""]
    for sc in chk.scenario.unique():
        md += [f"### {sc}", "", mdt(chk[chk.scenario == sc][["check_id", "status", "check", "detail"]]), ""]
    md += ["## Exceptions", "", f"{len(exc)} non-PASS item rows are listed in `connectivity_exceptions.csv` (INFO, FAIL and NOT_VERIFIABLE).", ""]
    if probs:
        md += ["## Internal consistency problems", ""] + [f"- {p}" for p in probs]
    else:
        md += ["Internal consistency checks (statuses valid, summary fail counts equal item rows, inputs unchanged): PASS."]
    (out / "audit_summary.md").write_text("\n".join(md), encoding="utf-8")
    print(cnt.to_string()); print(f"written: {out}"); print("internal consistency:", "PASS" if not probs else probs)


if __name__ == "__main__":
    main()
