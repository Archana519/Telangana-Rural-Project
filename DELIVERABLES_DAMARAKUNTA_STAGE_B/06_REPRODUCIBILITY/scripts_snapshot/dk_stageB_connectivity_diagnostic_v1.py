"""dk_stageB_connectivity_diagnostic_v1.py - READ-ONLY diagnosis of three findings from _connectivity_audit_v1.
 F1  a target whose attach chain ends on a road component other than the planner's main component (default C0002)
 F2  a target whose last vertex does not touch its declared road network (default C0076), within attach_tol_m
 F3  routes for which the audit could not reconstruct 'grid edges + connectors' (missing route_edges rows; facilities)
Reads existing outputs only. Writes only to <stageb-root>/_connectivity_diagnostic_v1 (must not exist). No routing, no planner import.
Each finding row is classified VERIFIED_FACT (computed from the files / quoted code), PLAUSIBLE (consistent with the evidence, not proven)
or UNRESOLVED. Nothing here is a statement about legal access, passability or field connectivity.
"""
import argparse, hashlib, json, sys, datetime
from pathlib import Path
import numpy as np, pandas as pd, geopandas as gpd
from shapely.geometry import Point
from shapely.ops import unary_union
from shapely.strtree import STRtree

CRS = "EPSG:32644"


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def boolcol(s):
    return s.astype(str).str.strip().str.lower().eq("true")


def mdt(df):
    df = df.fillna("")
    return "| " + " | ".join(map(str, df.columns)) + " |\n|" + "---|" * len(df.columns) + "\n" + "\n".join(
        "| " + " | ".join(str(v).replace("|", "/").replace("\n", " ") for v in r) + " |" for r in df.itertuples(index=False))


def line_components(segs, tol):
    tree = STRtree(segs); p = list(range(len(segs)))
    def f(x):
        while p[x] != x:
            p[x] = p[p[x]]; x = p[x]
        return x
    for i, s in enumerate(segs):
        for j in tree.query(s.buffer(tol)):
            if j != i and s.distance(segs[j]) <= tol:
                p[f(i)] = f(j)
    return [f(i) for i in range(len(segs))]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stageb-root", required=True)
    ap.add_argument("--runs", nargs="+", default=["S2_fac_C0_s25_K3_P2", "S2_fac_C0_s25_omitmerge"])
    ap.add_argument("--off-main-target", default="C0002")
    ap.add_argument("--gap-target", default="C0076")
    ap.add_argument("--strict-tol", type=float, default=0.01)
    ap.add_argument("--len-tol", type=float, default=0.02)
    ap.add_argument("--snap-m", type=float, default=None)
    ap.add_argument("--out-name", default="_connectivity_diagnostic_v1")
    a = ap.parse_args()
    root = Path(a.stageb_root); out = root / a.out_name
    if out.exists():
        sys.exit(f"stopping: {out} exists (never overwritten)")
    F, EDGE, FAC = [], [], []
    watched = {}

    def add(fid, scen, topic, item, cls, obs, val="", ev=""):
        assert cls in ("VERIFIED_FACT", "PLAUSIBLE", "UNRESOLVED")
        F.append(dict(finding_id=fid, scenario=scen, topic=topic, item=item, classification=cls, observation=obs, value=val, evidence_source=ev))

    roads_cache = {}
    for run in a.runs:
        d = root / run; S = run
        files = ["routes.gpkg", "connectivity_checks.csv", "target_status.csv", "road_components.csv", "route_edges.csv", "facility_status.csv", "scenario_targets.csv", "config_stageB.json", "inputs_manifest_stageB.csv"]
        if not all((d / f).exists() for f in files):
            add("X0", S, "inputs", str(d), "UNRESOLVED", "run folder or required file missing; scenario skipped"); continue
        for f in files:
            watched[d / f] = sha(d / f)
        cfg = json.loads((d / "config_stageB.json").read_text(encoding="utf-8"))
        def fk(o, k):
            if isinstance(o, dict):
                if k in o and not isinstance(o[k], (dict, list)): return o[k]
                for v in o.values():
                    r = fk(v, k)
                    if r is not None: return r
        tol = float(fk(cfg.get("args", cfg), "attach_tol_m") or 15.0)
        mf = pd.read_csv(d / "inputs_manifest_stageB.csv")
        rp = Path(mf[mf.role == "roads"].path.iloc[0]); watched[rp] = sha(rp)
        if rp not in roads_cache:
            rg = gpd.read_file(rp).to_crs(CRS); rg = rg[rg.geometry.notna() & ~rg.geometry.is_empty]
            segs = list(rg.geometry.explode(index_parts=False).reset_index(drop=True))
            roads_cache[rp] = (segs, unary_union(segs))
        segs, roads_u = roads_cache[rp]
        L = {n: gpd.read_file(d / "routes.gpkg", layer=n) for n in ("routes_network_houses", "routes_network_facilities", "targets_houses", "targets_facilities", "road_cells_main_component")}
        cc = pd.read_csv(d / "connectivity_checks.csv"); cc["target_id"] = cc.target_id.astype(str)
        ts = pd.read_csv(d / "target_status.csv"); ts["planner_key"] = ts.planner_key.astype(str)
        fs = pd.read_csv(d / "facility_status.csv"); rcm = pd.read_csv(d / "road_components.csv"); re_ = pd.read_csv(d / "route_edges.csv")
        sc = pd.read_csv(d / "scenario_targets.csv"); sc["planner_key"] = sc.planner_key.astype(str)
        routes = {}
        for kind, g in (("house", L["routes_network_houses"]), ("facility", L["routes_network_facilities"])):
            for _, r in g.iterrows():
                routes[str(r.target_id)] = dict(kind=kind, geom=r.geometry, ac=str(r.attach_class), ap=str(r.attach_parent), len_m=float(r.len_m))
        tpt = {str(r.target_id): r.geometry for g in (L["targets_houses"], L["targets_facilities"]) for _, r in g.iterrows()}
        main_poly = unary_union(list(L["road_cells_main_component"].geometry))
        ccx = cc.set_index("target_id")

        # ================= F1
        t = a.off_main_target
        if t not in routes:
            add("F1.0", S, "off-main target", t, "UNRESOLVED", "target not routed in this scenario")
        else:
            chain, cur, seen = [], t, set()
            while True:
                chain.append(cur); seen.add(cur)
                nxt = routes[cur]["ap"] if routes[cur]["ac"] in ("HOUSE_ROUTE", "FACILITY_ROUTE") else None
                if nxt is None or nxt not in routes or nxt in seen: break
                cur = nxt
            term = chain[-1]; tg = routes[term]["geom"]; endpt = Point(list(tg.coords)[-1])
            row = ccx.loc[t]
            add("F1.1", S, "attach chain", t, "VERIFIED_FACT", f"chain {' -> '.join(chain)}; terminal attach_class={routes[term]['ac']}; planner chain_depth={row.chain_depth}, chain_terminal={row.chain_terminal}, road_component={row.road_component}, reaches_main={row.reaches_main_road_component}", row.road_component, "routes.gpkg attach_parent walk; connectivity_checks.csv")
            tsr = ts[ts.planner_key == t]
            if len(tsr):
                same = str(tsr.primary_road_component.iloc[0]) == str(row.road_component)
                add("F1.2", S, "component id consistency", t, "VERIFIED_FACT" if same else "UNRESOLVED", f"target_status primary_road_component={tsr.primary_road_component.iloc[0]} vs connectivity_checks road_component={row.road_component}: {'equal' if same else 'DIFFERENT'}", "", "target_status.csv; connectivity_checks.csv")
            comp = int(float(row.road_component)) if pd.notna(row.road_component) else None
            main_rows = rcm[boolcol(rcm.is_main)]
            ids = set(cc.road_component.dropna().astype(float).astype(int)); known = set(rcm.component_id.astype(int))
            add("F1.3", S, "component table", "road_components.csv", "VERIFIED_FACT" if (len(main_rows) == 1 and int(main_rows.component_id.iloc[0]) == 1 and ids <= known) else "UNRESOLVED",
                f"{len(rcm)} components; is_main rows={len(main_rows)} (component_id {list(main_rows.component_id)}); all component ids used by routes {sorted(ids)} exist in the table: {ids <= known}; component sizes (cells) {dict(zip(rcm.component_id, rcm.n_cells))}", "", "road_components.csv; connectivity_checks.csv")
            if comp is not None and comp in known:
                r_ = rcm[rcm.component_id == comp].iloc[0]
                add("F1.4", S, "attached component", t, "VERIFIED_FACT", f"component {comp} has {int(r_.n_cells)} road cells ({100*float(r_.share_of_goal_cells):.2f}% of all road goal cells); main component has {int(main_rows.n_cells.iloc[0])} cells ({100*float(main_rows.share_of_goal_cells.iloc[0]):.2f}%)", int(r_.n_cells), "road_components.csv")
            n_same = int((cc.road_component.astype(str) == str(row.road_component)).sum())
            add("F1.5", S, "targets on the same component", t, "VERIFIED_FACT", f"{n_same} routed target(s) terminate on road component {row.road_component}: {list(cc[cc.road_component.astype(str) == str(row.road_component)].target_id)}", n_same, "connectivity_checks.csv")
            tp = tpt[t]
            add("F1.6", S, "geometry distances", t, "VERIFIED_FACT", f"target point to main-component cells {tp.distance(main_poly):.2f} m; attachment point to main-component cells {endpt.distance(main_poly):.4f} m; attachment point to road line {endpt.distance(roads_u):.4f} m; route length {routes[t]['len_m']:.2f} m",
                round(endpt.distance(main_poly), 4), "routes.gpkg; road_cells_main_component")
            dtr = sc[sc.planner_key == t].dist_to_road_m
            if len(dtr): add("F1.7", S, "scenario distance to road", t, "VERIFIED_FACT", f"scenario_targets dist_to_road_m={float(dtr.iloc[0]):.2f} (distance to the nearest road of ANY component, from the Stage A table)", float(dtr.iloc[0]), "scenario_targets.csv")
            # line-level components of the source roads
            for tl in (a.strict_tol, 10.0, 20.0):
                lab = line_components(segs, tl)
                ln = pd.Series([s.length for s in segs]).groupby(lab).sum()
                inpoly = pd.Series([s.intersection(main_poly).length for s in segs]).groupby(lab).sum()
                main_lab = inpoly.idxmax() if inpoly.max() > 0 else None
                idx = int(np.argmin([s.distance(endpt) for s in segs])); my_lab = lab[idx]
                if main_lab is None:
                    add(f"F1.8@{tl:g}", S, "source road line components", t, "UNRESOLVED", f"no source road line intersects the main-component cells at join tolerance {tl:g} m", "", str(rp)); continue
                if my_lab == main_lab:
                    add(f"F1.8@{tl:g}", S, "source road line components", t, "VERIFIED_FACT", f"at line-joining tolerance {tl:g} m the attachment point's road line belongs to the SAME line component as the main component ({ln[main_lab]:.1f} m): the off-main label comes from raster-cell connectivity, not from a disjoint road in the source", "same", str(rp))
                else:
                    gap = min(segs[i].distance(segs[j]) for i in [k for k, l_ in enumerate(lab) if l_ == my_lab] for j in [k for k, l_ in enumerate(lab) if l_ == main_lab])
                    add(f"F1.8@{tl:g}", S, "source road line components", t, "VERIFIED_FACT", f"at line-joining tolerance {tl:g} m the attachment point's road line is a separate line component of {ln[my_lab]:.1f} m (main line component {ln[main_lab]:.1f} m; total {ln.sum():.1f} m in {len(ln)} components); minimum gap between the two components = {gap:.2f} m", round(gap, 2), str(rp))
            add("F1.9", S, "planner goal set (code)", "plan_network_v2.py", "VERIFIED_FACT", "plan(): goals_road = set(road_cells) = every passable road cell of EVERY component; the runner labels components (id 1 = largest) only for reporting. Nothing restricts targets to the main component. (quoted from plan_network_v2.py plan() and dk_stageB_run_v1_3.py components())", "", "source code")
            add("F1.10", S, "likely cause", t, "PLAUSIBLE", "the route attaches to the cheapest reachable road cell of any component, and component %s is cheaper to reach than the main component; the data show this component is not joined to the main one under the stated tolerances. Whether the separation is a real road-network break or a digitisation/raster gap in the source is not decided by these files." % row.road_component, "", "inference")
            add("F1.11", S, "cost comparison with main component", t, "UNRESOLVED", "whether a route to the main component exists and how much longer/costlier it would be cannot be established without routing (not done by instruction)", "", "n/a")

        # ================= F2
        t = a.gap_target
        if t in routes:
            r = routes[t]; co = list(r["geom"].coords); last = Point(co[-1])
            dist_road = last.distance(roads_u)
            fac_ids = [k for k, v in routes.items() if v["kind"] == "facility"]
            near = sorted(((k, last.distance(v["geom"])) for k, v in routes.items() if k != t), key=lambda x: x[1])[:3]
            add("F2.1", S, "last vertex", t, "VERIFIED_FACT", f"declared attach_class={r['ac']}, attach_parent='{r['ap']}'; last vertex to road line = {dist_road:.4f} m; nearest other routes: " + "; ".join(f"{k} ({routes[k]['kind']}) {dd:.4f} m" for k, dd in near), round(dist_road, 4), "routes.gpkg; source roads")
            fd = {k: last.distance(routes[k]["geom"]) for k in fac_ids}
            onfac = [k for k, v in fd.items() if v <= a.strict_tol]
            if dist_road > a.strict_tol:
                if onfac:
                    add("F2.2", S, "where the end really snaps", t, "VERIFIED_FACT", f"last vertex touches facility route(s) {onfac} (distance <= {a.strict_tol} m) although the route is labelled ROAD and the road line is {dist_road:.2f} m away", dist_road, "routes.gpkg")
                else:
                    add("F2.2", S, "where the end really snaps", t, "UNRESOLVED", f"last vertex touches neither the road line nor any facility route (nearest facility distance {min(fd.values()):.4f} m)", dist_road, "routes.gpkg")
            else:
                add("F2.2", S, "where the end really snaps", t, "VERIFIED_FACT", f"in this scenario the last vertex touches the road line ({dist_road:.4f} m): no gap", dist_road, "routes.gpkg")
            add("F2.3", S, "tolerance relation", t, "VERIFIED_FACT", f"gap {dist_road:.4f} m vs planner attach_tol_m {tol}: {'within' if dist_road <= tol else 'EXCEEDS'} tolerance", dist_road, "config_stageB.json")
            add("F2.4", S, "code mechanism", "dk_stageB_run_v1_3.py / plan_network_v2.py", "VERIFIED_FACT", "In the house phase the runner calls plan() with road_union = roads UNION facility routes and goals = road cells UNION facility-route cells. A route that ends in a goal cell snaps its last vertex to the nearest point of that union (make_route). The runner then labels it ROAD whenever the end cell is a road cell (parent_of), even if the nearest point of the union lay on a facility route. So the label (cell membership) and the drawn snap (nearest point of the union) can disagree.", "", "source code")
            if dist_road > a.strict_tol and onfac:
                add("F2.5", S, "likely cause", t, "PLAUSIBLE", "gap is a labelling/representation effect (label ROAD by end cell vs snap to facility route), not a routing error: the route does touch a facility route, which the audit's G02 check on facilities showed touches the road. The effective chain C->facility->road is geometrically connected.", "", "inference from F2.1-F2.4")
        else:
            add("F2.0", S, "gap target", t, "UNRESOLVED", "target not routed in this scenario")

        # ================= F3 (edge rows, facilities)
        eh = re_[re_.scope == "house_phase"].groupby("route_id").len_m.sum(); ef = re_[re_.scope == "facility_phase"].groupby("route_id").len_m.sum()
        ts_ix = ts.set_index("planner_key"); fsx = fs.set_index(fs.facility_id.astype(str))
        snapm = float(a.snap_m if a.snap_m is not None else (fk(cfg.get("args", cfg), "snap_m") or 30.0))
        for tid, r in routes.items():
            co = list(r["geom"].coords); nv = len(co)
            d01 = Point(co[0]).distance(Point(co[1])) if nv > 1 else np.nan
            if r["kind"] == "house":
                es = eh.get(tid, np.nan); has = tid in eh.index
                endsn = float(ccx.loc[tid, "end_snap_m"]) if tid in ccx.index else np.nan
                ss = float(pd.to_numeric(ts_ix.loc[tid, "primary_start_snap_m"], errors="coerce")) if tid in ts_ix.index else np.nan
                dist_r = float(sc[sc.planner_key == tid].dist_to_road_m.iloc[0]) if (sc.planner_key == tid).any() else np.nan
            else:
                es = ef.get(tid, np.nan); has = tid in ef.index
                endsn = float(pd.to_numeric(fsx.loc[tid, "end_snap_m"], errors="coerce")) if tid in fsx.index else np.nan
                ss, dist_r = np.nan, np.nan
            e_ = es if has else 0.0
            implied = r["len_m"] - e_ - (endsn if pd.notna(endsn) else np.nan)      # start connector implied by len_m = edges + start + end
            if r["kind"] == "house" and pd.notna(ss):
                ok = bool(abs(implied - ss) <= a.len_tol); how = "implied start connector equals exported primary_start_snap_m"
            elif pd.notna(implied):
                ok = bool(-a.len_tol <= implied <= snapm + a.len_tol and (abs(implied) <= a.len_tol or abs(implied - d01) <= a.len_tol)); how = "implied start connector is 0 or equals the first geometry segment, and <= snap_m (facility start snap is not exported)"
            else:
                ok, how = None, "end snap missing"
            diff = (implied - ss) if (r["kind"] == "house" and pd.notna(ss)) else np.nan
            EDGE.append(dict(scenario=S, kind=r["kind"], target_id=tid, has_edge_rows=has, n_vertices=nv, edge_len_sum_m=es, first_geometry_segment_m=round(d01, 4), start_snap_exported_m=ss,
                             end_snap_exported_m=endsn, len_m=r["len_m"], implied_start_connector_m=implied, diff_vs_exported_start_m=diff, within_tol=ok, basis=how, dist_to_road_m=dist_r))
        E = pd.DataFrame([e for e in EDGE if e["scenario"] == S])
        miss = E[~E.has_edge_rows]
        okm = miss[miss.within_tol == True]
        add("F3.1", S, "routes without edge rows", "route_edges.csv", "VERIFIED_FACT", f"{len(miss)} of {len(E)} routes have no rows in route_edges.csv (houses {int((miss.kind=='house').sum())}, facilities {int((miss.kind=='facility').sum())}); vertices per route without rows: {sorted(set(miss.n_vertices))}; with rows: min {int(E[E.has_edge_rows].n_vertices.min())}", len(miss), "route_edges.csv; routes.gpkg")
        add("F3.2", S, "zero-edge hypothesis", "routes without edge rows", "VERIFIED_FACT" if len(miss) and len(okm) == len(miss) else "UNRESOLVED",
            f"for {len(okm)} of {len(miss)} routes without edge rows, len_m = exported start snap + exported end snap within {a.len_tol} m, i.e. the stored length is fully explained by a path with zero grid edges (the start cell is already a goal cell)" if len(miss) else "no routes without edge rows",
            len(okm), "routes.gpkg geometry + connectivity_checks.csv end_snap_m")
        if len(miss):
            add("F3.3", S, "zero-edge routes vs distance to road", "routes without edge rows", "VERIFIED_FACT", f"dist_to_road_m of house routes without edge rows: median {miss[miss.kind=='house'].dist_to_road_m.median():.1f} m, max {miss[miss.kind=='house'].dist_to_road_m.max():.1f} m; with edge rows: median {E[(E.kind=='house') & E.has_edge_rows].dist_to_road_m.median():.1f} m", "", "scenario_targets.csv")
        withrows = E[E.has_edge_rows]
        okw = withrows[withrows.within_tol == True]
        add("F3.4", S, "reconstruction of all routes", "all routes", "VERIFIED_FACT" if len(okw) == len(withrows) and len(okm) == len(miss) else "UNRESOLVED",
            f"len_m = grid-edge sum + start connector + exported end snap is consistent for {len(okw)+len(okm)} of {len(E)} routes (houses: start connector must equal the exported start snap within {a.len_tol} m; facilities: the implied start connector must be 0 or the first geometry segment and <= snap_m, because the facility start snap is not exported, so facilities are consistency-checked, not exactly reconstructed)", len(okw) + len(okm), "route_edges.csv; routes.gpkg; facility_status.csv")
        bad = E[E.within_tol == False]
        if len(bad):
            add("F3.5", S, "reconstruction failures", ", ".join(bad.target_id.head(10)), "UNRESOLVED", f"{len(bad)} route(s) do not reconcile; see edge_row_reconstruction.csv", len(bad), "edge_row_reconstruction.csv")
        add("F3.6", S, "code mechanism", "dk_stageB_run_v1_3.py", "VERIFIED_FACT", "route_edges rows are written by looping over r['edges'] for the three scopes; a route with an empty edge list contributes no rows. facility_status.csv/routes.gpkg do not export the facility start-connector length (start_snap), so the audit could not rebuild it from exported fields; the geometry's first segment gives it.", "", "source code")

    # ---- write
    out.mkdir(parents=True)
    Fd = pd.DataFrame(F); Fd.to_csv(out / "diagnostic_findings.csv", index=False)
    pd.DataFrame(EDGE).to_csv(out / "edge_row_reconstruction.csv", index=False)
    changed = [str(p) for p, h in watched.items() if sha(p) != h]
    pd.DataFrame([dict(check="inputs unchanged (sha256 before/after)", status="FAIL" if changed else "PASS", detail=f"{len(watched)} files")]).to_csv(out / "readonly_proof.csv", index=False)
    md = ["# Connectivity diagnostic v1 (read-only)", "", f"Generated {datetime.datetime.now():%Y-%m-%d %H:%M} by `dk_stageB_connectivity_diagnostic_v1.py`. Inputs unchanged after run: {'YES' if not changed else 'NO'} ({len(watched)} files hashed).", "",
          "Model connectivity on a planning grid only; no statement about legal access, passability or field connectivity. Classification: VERIFIED_FACT (computed from files/code), PLAUSIBLE (consistent, not proven), UNRESOLVED.", ""]
    for cls in ("VERIFIED_FACT", "PLAUSIBLE", "UNRESOLVED"):
        sub = Fd[Fd.classification == cls]
        md += [f"## {cls.replace('_', ' ').title()} ({len(sub)})", "", mdt(sub[["finding_id", "scenario", "item", "observation"]]) if len(sub) else "None.", ""]
    (out / "diagnostic_report.md").write_text("\n".join(md), encoding="utf-8")
    print(Fd.groupby(["scenario", "classification"]).size().to_string()); print("written:", out); print("inputs unchanged:", not changed)


if __name__ == "__main__":
    main()
