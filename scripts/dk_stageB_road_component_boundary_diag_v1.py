#!/usr/bin/env python
"""dk_stageB_road_component_boundary_diag_v1.py - READ-ONLY road-component vs. boundary-crossing diagnostic (no routing).

Direct geometric evidence only; nothing here says a source line is a usable road, legal access or passable.
Method (see also findings):
 1 rebuild the road-cell components with the planner rule (gate: sizes == road_components.csv, input hashes == manifest, counts);
 2 each source road feature is split into LineString parts; each part is rasterised alone (all_touched=True, cost grid) -> cells -> components;
 3 along each part the polygon-boundary crossings define inside/outside segments; an OUTSIDE segment with inside segments at both ends is an EXCURSION;
 4 every crossing point is matched to the nearest PASSABLE road cell (any component) and its distance is kept (association threshold --assoc-m, default 20 m, only a label);
 5 for component pairs sharing a part: along-line gap between their nearest cells (by chainage), the outside-polygon length inside that gap, dropped cells in it;
 6 per component: 0-1 BFS minimum blocked chain to the main component over road-line-covered cells (as dk_stageB_c0002_roadcell_diag_v1), with how many chain cells have centres outside the polygon.
Limitations: chainage uses shapely project on each part (self-overlapping lines would be ambiguous); a cell's component comes from passable 8-adjacency, not from the feature that touches it.
"""
import argparse, hashlib, json, sys, datetime
from collections import deque
from pathlib import Path
import numpy as np, pandas as pd, geopandas as gpd, rasterio, shapely
from rasterio.features import rasterize
from scipy.spatial import cKDTree
from shapely.geometry import Point

CRS = "EPSG:32644"
NB = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def same_grid(T1, c1, s1, T2, c2, s2, tol=1e-6):
    return s1 == s2 and c1 is not None and c2 is not None and c1 == c2 and all(abs(a - b) <= tol for a, b in zip(tuple(T1)[:6], tuple(T2)[:6]))


def read(path):
    with rasterio.open(path) as s:
        arr = s.read(1).astype(float)
        if s.nodata is not None:
            arr[arr == s.nodata] = np.nan
        return arr, s.transform, s.crs


def label_components(mask):
    H, W = mask.shape; seen = np.zeros_like(mask, bool); comps = []
    for r0, c0 in zip(*np.nonzero(mask)):
        if seen[r0, c0]:
            continue
        st, comp = [(r0, c0)], []; seen[r0, c0] = True
        while st:
            r, c = st.pop(); comp.append((r, c))
            for dr, dc in NB:
                r2, c2 = r + dr, c + dc
                if 0 <= r2 < H and 0 <= c2 < W and mask[r2, c2] and not seen[r2, c2]:
                    seen[r2, c2] = True; st.append((r2, c2))
        comps.append(comp)
    comps.sort(key=lambda c: (-len(c), min(r * W + cc for r, cc in c)))
    lab = np.zeros(mask.shape, int)
    for i, c in enumerate(comps, 1):
        for r, cc in c:
            lab[r, cc] = i
    return lab, [len(c) for c in comps]


def min_block_chain(rr, passable, lab, cells):
    H, W = rr.shape; INF = 10 ** 9
    dist = np.full((H, W), INF, int); prev = {}; dq = deque()
    for c in cells:
        dist[c] = 0; dq.append(c)
    while dq:
        r, c = dq.popleft()
        if lab[r, c] == 1:
            cur = (r, c); path = [cur]
            while cur in prev:
                cur = prev[cur]; path.append(cur)
            return path[::-1]
        for dr, dc in NB:
            r2, c2 = r + dr, c + dc
            if 0 <= r2 < H and 0 <= c2 < W and rr[r2, c2]:
                w_ = 0 if passable[r2, c2] else 1
                if dist[r, c] + w_ < dist[r2, c2]:
                    dist[r2, c2] = dist[r, c] + w_; prev[(r2, c2)] = (r, c)
                    (dq.appendleft if w_ == 0 else dq.append)((r2, c2))
    return []


def segments_of(part, poly, bline):
    """crossings + inside/outside segments along one LineString part (chainage s in m)."""
    L = part.length; pts, flags = [], []
    for g in shapely.get_parts(part.intersection(bline)):
        if g.is_empty:
            continue
        if g.geom_type == "Point":
            pts.append(part.project(g))
        else:
            pts += [part.project(Point(g.coords[0])), part.project(Point(g.coords[-1]))]; flags.append("collinear_with_boundary")
    bp = sorted({round(float(s), 6) for s in pts if 1e-6 < s < L - 1e-6})
    cuts = [0.0] + bp + [L]
    raw = []
    for a, b in zip(cuts[:-1], cuts[1:]):
        if b - a < 1e-9:
            continue
        mid = part.interpolate((a + b) / 2)
        raw.append([a, b, "inside" if poly.covers(mid) else "outside"])
    seg = []
    for s in raw:
        if seg and seg[-1][2] == s[2]:
            seg[-1][1] = s[1]
        else:
            seg.append(list(s))
    return seg, bp, flags


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stageb-root", required=True)
    ap.add_argument("--run", default="S2_fac_C0_s25_K3_P2")
    ap.add_argument("--boundary", default=None)
    ap.add_argument("--boundary-layer", default="village_boundary")
    ap.add_argument("--out-name", default="_road_component_boundary_diag_v1")
    ap.add_argument("--assoc-m", type=float, default=20.0)
    ap.add_argument("--expect-total", type=int, default=8061)
    ap.add_argument("--expect-dropped", type=int, default=1567)
    ap.add_argument("--expect-comp10-impassable", type=int, default=36)
    a = ap.parse_args()
    root = Path(a.stageb_root); d = root / a.run; out = root / a.out_name
    if out.exists():
        sys.exit(f"stopping: {out} exists (never overwritten)")
    base = [d / "config_stageB.json", d / "inputs_manifest_stageB.csv", d / "road_components.csv"]
    for p in base:
        if not p.exists():
            sys.exit(f"stopping: missing {p}")
    watched = {p: sha(p) for p in base}
    cfg = json.loads(base[0].read_text(encoding="utf-8")); rc = cfg.get("resolved_constraints", {})
    mf = pd.read_csv(base[1]).set_index("role")
    for r in ("cost", "worldcover", "roads"):
        if r not in mf.index:
            sys.exit(f"stopping: manifest role '{r}' missing")
    paths = {r: Path(mf.loc[r, "path"]) for r in ("cost", "worldcover", "roads")}
    blocked_p, slope_p, slope_lim, water_c = rc.get("prohibited_raster"), rc.get("slope_raster"), rc.get("slope_limit_deg"), rc.get("water_class", 80)
    if not blocked_p or not slope_p or slope_lim is None:
        sys.exit("stopping: config lacks prohibited_raster / slope_raster / slope_limit_deg")
    bpath = Path(a.boundary) if a.boundary else (Path(mf.loc["boundary", "path"]) if "boundary" in mf.index else paths["cost"].parent.parent / "study_area" / "damarakunta_boundary.gpkg")
    for p in list(paths.values()) + [Path(blocked_p), Path(slope_p), bpath]:
        if not p.exists():
            sys.exit(f"stopping: missing input {p}")
        watched[p] = sha(p)
    hash_ok = {r: watched[paths[r]] == mf.loc[r, "sha256"] for r in paths}

    cost, T, crs = read(paths["cost"])
    if crs is None or crs.to_epsg() != 32644:
        sys.exit(f"stopping: cost CRS {crs}")
    H, W = cost.shape
    w, Tw, cw = read(paths["worldcover"]); pro, Tp, cp = read(Path(blocked_p)); slo, Ts, cs_ = read(Path(slope_p))
    for nm, (arr, Ta, ca) in dict(worldcover=(w, Tw, cw), prohibited=(pro, Tp, cp), slope=(slo, Ts, cs_)).items():
        if not same_grid(T, crs, cost.shape, Ta, ca, arr.shape):
            sys.exit(f"stopping: {nm} not on the cost grid; planner rule not reproducible")
    ok = np.isfinite(cost) & (cost > 0)
    passable = ok & ~((w == water_c) | (np.nan_to_num(pro, nan=0) > 0) | (np.nan_to_num(slo, nan=0) > slope_lim))
    import pyogrio
    lays = [x[0] for x in pyogrio.list_layers(bpath)]
    lay = a.boundary_layer if a.boundary_layer in lays else (lays[0] if len(lays) == 1 else None)
    if lay is None:
        sys.exit(f"stopping: boundary layer '{a.boundary_layer}' not in {lays}")
    bnd = gpd.read_file(bpath, layer=lay)
    if bnd.crs is None:
        sys.exit("stopping: boundary CRS undefined")
    poly = bnd.to_crs(CRS).geometry.union_all(); bline = poly.boundary
    roads = gpd.read_file(paths["roads"])
    if roads.crs is None:
        sys.exit("stopping: roads CRS undefined")
    roads = roads.to_crs(CRS); roads = roads[roads.geometry.notna() & ~roads.geometry.is_empty].reset_index(drop=True)
    idcol = next((c for c in roads.columns if c.lower() in ("objectid", "fid", "id", "feature_id")), None)
    roads["fid"] = roads[idcol].astype(str) if idcol else roads.index.astype(str)
    if roads.fid.duplicated().any():
        roads["fid"] = roads.index.astype(str); idcol = None
    rr = rasterize([(g, 1) for g in roads.geometry], out_shape=(H, W), transform=T, fill=0, all_touched=True, dtype="uint8").astype(bool)
    lab, sizes = label_components(rr & passable)
    rec = list(pd.read_csv(base[2]).sort_values("component_id").n_cells.astype(int))
    nd = int((rr & ~passable).sum())
    gate = [("component sizes equal road_components.csv", str(sizes), str(rec), sizes == rec),
            ("input hashes equal manifest", str(hash_ok), "manifest", all(hash_ok.values())),
            ("road-line-covered cells", int(rr.sum()), a.expect_total, a.expect_total < 0 or int(rr.sum()) == a.expect_total),
            ("dropped cells", nd, a.expect_dropped, a.expect_dropped < 0 or nd == a.expect_dropped)]
    ncomp = len(sizes)
    # component 10 regression (earlier diagnostic: 36 impassable cells on the minimum chain)
    chains = {}
    for k in range(2, ncomp + 1):
        cells = [(r, c) for r, c in zip(*np.nonzero(lab == k))]
        chains[k] = min_block_chain(rr, passable, lab, cells)
    if ncomp >= 10 and a.expect_comp10_impassable >= 0:
        n10 = sum(1 for p in chains[10] if not passable[p])
        gate.append(("component 10 minimum chain impassable cells", n10, a.expect_comp10_impassable, n10 == a.expect_comp10_impassable))
    V = pd.DataFrame(gate, columns=["check", "rebuilt", "expected", "ok"])
    if not V.ok.all():
        print(V.to_string(index=False)); sys.exit("stopping: validation gate FAILED; nothing written")

    cx = lambda r, c: T * (c + 0.5, r + 0.5)
    pr, pc = np.nonzero(rr & passable)
    cen = np.array([cx(r, c) for r, c in zip(pr, pc)]); plab = lab[pr, pc]
    tree = cKDTree(cen)

    def nearest_pass(pt):
        dd, i = tree.query([pt.x, pt.y]); return float(dd), int(plab[i])
    dr_, dc_ = np.nonzero(rr & ~passable); dcen = np.array([cx(r, c) for r, c in zip(dr_, dc_)]) if len(dr_) else np.zeros((0, 2))

    # ---- parts: cells, components, crossings, segments
    P, CROSS, EXC, CF = [], [], [], []
    partinfo = {}
    for i, row in roads.iterrows():
        for k, part in enumerate(shapely.get_parts(row.geometry)):
            if part.geom_type != "LineString" or part.length == 0:
                continue
            key = f"{row.fid}:{k}"
            m = rasterize([(part, 1)], out_shape=(H, W), transform=T, fill=0, all_touched=True, dtype="uint8").astype(bool)
            seg, bp, flags = segments_of(part, poly, bline)
            cells_pass = np.argwhere(m & passable); cells_drop = np.argwhere(m & ~passable)
            s_pass = np.array([part.project(Point(*cx(r, c))) for r, c in cells_pass]) if len(cells_pass) else np.array([])
            l_pass = np.array([lab[r, c] for r, c in cells_pass], int) if len(cells_pass) else np.array([], int)
            s_drop = np.array([part.project(Point(*cx(r, c))) for r, c in cells_drop]) if len(cells_drop) else np.array([])
            drop_out = np.array([not poly.covers(Point(*cx(r, c))) for r, c in cells_drop], bool) if len(cells_drop) else np.array([], bool)
            out_len = sum(s[1] - s[0] for s in seg if s[2] == "outside")
            partinfo[key] = dict(part=part, seg=seg, s_pass=s_pass, l_pass=l_pass, s_drop=s_drop, drop_out=drop_out)
            P.append(dict(feature_id=row.fid, part=k, part_key=key, length_m=round(part.length, 3), outside_len_m=round(out_len, 3), n_crossings=len(bp), n_segments=len(seg),
                          n_excursions=sum(1 for j, s in enumerate(seg) if s[2] == "outside" and 0 < j < len(seg) - 1), flags=";".join(sorted(set(flags))),
                          n_passable_cells=len(cells_pass), n_dropped_cells=len(cells_drop), components=";".join(str(x) for x in sorted(set(l_pass.tolist())))))
            for u in sorted(set(l_pass.tolist())):
                CF.append(dict(component=u, feature_id=row.fid, part_key=key, n_passable_cells=int((l_pass == u).sum())))
            for s in bp:
                pt = part.interpolate(s); eps = 0.5
                before = poly.covers(part.interpolate(max(s - eps, 0))); after = poly.covers(part.interpolate(min(s + eps, part.length)))
                typ = "enter" if (not before and after) else "exit" if (before and not after) else "touch_or_graze"
                dist, comp = nearest_pass(pt)
                CROSS.append(dict(feature_id=row.fid, part_key=key, chainage_m=round(s, 3), x=pt.x, y=pt.y, type=typ, nearest_passable_cell_m=round(dist, 2), nearest_passable_component=comp, associated=dist <= a.assoc_m))
            for j, s in enumerate(seg):
                if s[2] == "outside" and 0 < j < len(seg) - 1:
                    p0, p1 = part.interpolate(s[0]), part.interpolate(s[1])
                    d0, c0 = nearest_pass(p0); d1, c1 = nearest_pass(p1)
                    EXC.append(dict(feature_id=row.fid, part_key=key, exit_chainage_m=round(s[0], 3), reenter_chainage_m=round(s[1], 3), outside_len_m=round(s[1] - s[0], 3), straight_gap_m=round(p0.distance(p1), 3),
                                    exit_x=p0.x, exit_y=p0.y, enter_x=p1.x, enter_y=p1.y, exit_nearest_comp=c0, exit_dist_m=round(d0, 2), enter_nearest_comp=c1, enter_dist_m=round(d1, 2),
                                    both_ends_associated=(d0 <= a.assoc_m and d1 <= a.assoc_m), ends_in_different_components=(c0 != c1)))
    Pd = pd.DataFrame(P)
    Cd = pd.DataFrame(CROSS, columns=['feature_id', 'part_key', 'chainage_m', 'x', 'y', 'type', 'nearest_passable_cell_m', 'nearest_passable_component', 'associated'])
    Ed = pd.DataFrame(EXC, columns=['feature_id', 'part_key', 'exit_chainage_m', 'reenter_chainage_m', 'outside_len_m', 'straight_gap_m', 'exit_x', 'exit_y', 'enter_x', 'enter_y', 'exit_nearest_comp', 'exit_dist_m', 'enter_nearest_comp', 'enter_dist_m', 'both_ends_associated', 'ends_in_different_components'])
    CFd = pd.DataFrame(CF, columns=['component', 'feature_id', 'part_key', 'n_passable_cells'])

    # ---- along-line gaps between components sharing a part
    G = []
    for key, pi in partinfo.items():
        comps = sorted(set(pi["l_pass"].tolist()))
        for k in comps:
            for o in comps:
                if o == k:
                    continue
                sk, so = np.sort(pi["s_pass"][pi["l_pass"] == k]), np.sort(pi["s_pass"][pi["l_pass"] == o])
                diff = np.abs(sk[:, None] - so[None, :]); i, j = np.unravel_index(np.argmin(diff), diff.shape)
                lo, hi = sorted((sk[i], so[j]))
                out_in = sum(max(0.0, min(s[1], hi) - max(s[0], lo)) for s in pi["seg"] if s[2] == "outside")
                nd_ = int(((pi["s_drop"] > lo) & (pi["s_drop"] < hi)).sum()) if len(pi["s_drop"]) else 0
                ndo = int((((pi["s_drop"] > lo) & (pi["s_drop"] < hi)) & pi["drop_out"]).sum()) if len(pi["s_drop"]) else 0
                G.append(dict(component=k, other_component=o, part_key=key, feature_id=key.split(":")[0], along_line_gap_m=round(hi - lo, 3), outside_len_in_gap_m=round(out_in, 3),
                              inside_len_in_gap_m=round(hi - lo - out_in, 3), dropped_cells_in_gap=nd_, dropped_cells_in_gap_centre_outside=ndo))
    Gd = pd.DataFrame(G, columns=['component', 'other_component', 'part_key', 'feature_id', 'along_line_gap_m', 'outside_len_in_gap_m', 'inside_len_in_gap_m', 'dropped_cells_in_gap', 'dropped_cells_in_gap_centre_outside'])

    # ---- component summary
    CS = []
    for k in range(1, ncomp + 1):
        cells = np.argwhere(lab == k); cc = np.array([cx(r, c) for r, c in cells])
        fl = CFd[CFd.component == k]; feats = sorted(fl.feature_id.unique()); ch = chains.get(k, [])
        row = dict(component=k, n_cells=sizes[k - 1], n_unique_features=len(feats), feature_ids=";".join(feats), n_parts=int(fl.part_key.nunique()))
        if k > 1:
            dd = np.sqrt(((cc[:, None, :] - cen[plab == 1][None, :, :]) ** 2).sum(-1)); row["centre_gap_to_main_m"] = round(float(dd.min()), 2)
            gm = Gd[(Gd.component == k) & (Gd.other_component == 1)]
            row["shares_part_with_main"] = bool(len(gm))
            row["min_along_gap_to_main_m"] = float(gm.along_line_gap_m.min()) if len(gm) else np.nan
            if len(gm):
                g0 = gm.sort_values("along_line_gap_m").iloc[0]
                row.update(gap_part=g0.part_key, gap_outside_len_m=g0.outside_len_in_gap_m, gap_dropped_cells=g0.dropped_cells_in_gap, gap_dropped_cells_centre_outside=g0.dropped_cells_in_gap_centre_outside)
            row["chain_found"] = bool(ch); row["chain_cells"] = len(ch) if ch else np.nan
            if ch:
                imp = [p for p in ch if not passable[p]]
                row["chain_impassable"] = len(imp)
                row["chain_impassable_centre_outside"] = sum(1 for p in imp if not poly.covers(Point(*cx(*p))))
        near = Cd[(Cd.nearest_passable_component == k) & Cd.associated] if len(Cd) else Cd
        row["crossings_within_assoc_m"] = int(len(near)); row["excursion_ends_within_assoc_m"] = int(((Ed.exit_nearest_comp == k) & (Ed.exit_dist_m <= a.assoc_m)).sum() + ((Ed.enter_nearest_comp == k) & (Ed.enter_dist_m <= a.assoc_m)).sum()) if len(Ed) else 0
        row["min_cell_dist_to_polygon_boundary_m"] = round(float(min(Point(*p).distance(bline) for p in cc)), 2)
        CS.append(row)
    CSd = pd.DataFrame(CS)

    # ---- findings
    F = []

    def add(i, c, o, v=""):
        assert c in ("VERIFIED_FACT", "HYPOTHESIS", "UNRESOLVED")
        F.append(dict(finding_id=i, classification=c, observation=o, value=v))
    uf = roads.fid.nunique()
    add("R0", "VERIFIED_FACT", f"gate passed: components {sizes}; road-line cells {int(rr.sum())}; dropped {nd}; component-10 chain impassable count reproduced; input hashes equal manifest. Source features {uf} unique ids (feature id column: {idcol or 'row index'}), {len(Pd)} line parts", uf)
    exf = Ed.feature_id.nunique() if len(Ed) else 0
    add("R1", "VERIFIED_FACT", f"boundary excursions (exit then re-entry on the same part): {len(Ed)} in {exf} unique features; total outside length on excursions {Ed.outside_len_m.sum() if len(Ed) else 0:.1f} m; parts with an outside segment that touches a part end (no re-entry on that part): {int(sum(1 for pi in partinfo.values() if pi['seg'] and ((pi['seg'][0][2]=='outside') or (pi['seg'][-1][2]=='outside'))))}; crossings {len(Cd)}", len(Ed))
    nonmain = CSd[CSd.component > 1]
    add("R2", "VERIFIED_FACT", f"non-main components {len(nonmain)}: sharing a source part with the main component {int(nonmain.shares_part_with_main.sum())}; with a minimum blocked chain to the main component {int(nonmain.chain_found.sum())}; with at least one polygon-crossing within {a.assoc_m:g} m of a passable cell of the component {int((nonmain.crossings_within_assoc_m > 0).sum())}", "")
    if len(Ed):
        add("R3", "VERIFIED_FACT", f"excursions whose two ends are both within {a.assoc_m:g} m of passable cells: {int(Ed.both_ends_associated.sum())}; of these, ends in different components: {int((Ed.both_ends_associated & Ed.ends_in_different_components).sum())}; ends in the same component: {int((Ed.both_ends_associated & ~Ed.ends_in_different_components).sum())}", "")
    r10 = CSd[CSd.component == 10]
    if len(r10):
        r = r10.iloc[0]
        add("R4", "VERIFIED_FACT", f"component 10 (C0002 attachment): {int(r.n_cells)} cells, features {r.feature_ids}; centre gap to main {r.centre_gap_to_main_m} m; shares a part with main: {r.shares_part_with_main}; min along-line gap {r.min_along_gap_to_main_m}; outside length in that gap {r.get('gap_outside_len_m')}; chain cells {r.chain_cells}, impassable {r.get('chain_impassable')}, of which centre outside polygon {r.get('chain_impassable_centre_outside')}", "")
    add("H1", "HYPOTHESIS", "where a non-main component has a boundary crossing within the association distance and its minimum blocked chain has impassable cells with centres outside the polygon, the split is geometrically associated with the road leaving the polygon. This is an association in the source geometry, not proof of cause for every component and not evidence of a usable road.", "")
    add("U1", "UNRESOLVED", "real-world existence, completeness, currentness and usability of any source line (inside or outside the polygon) are not tested; no legal access, ownership or passability is inferred; no routing was done; boundary authority/currentness not verified.", "")
    Fd = pd.DataFrame(F)

    out.mkdir(parents=True)
    V.to_csv(out / "validation_gate.csv", index=False); CSd.to_csv(out / "component_summary.csv", index=False); CFd.to_csv(out / "component_feature_cells.csv", index=False)
    Pd.to_csv(out / "road_parts.csv", index=False); Cd.to_csv(out / "boundary_crossings.csv", index=False); Ed.to_csv(out / "boundary_excursions.csv", index=False)
    Gd.to_csv(out / "component_part_gaps.csv", index=False); Fd.to_csv(out / "road_component_boundary_findings.csv", index=False)
    pd.DataFrame([("script", Path(__file__).name, sha(Path(__file__))), ("assoc_m", a.assoc_m, ""), ("run", datetime.datetime.now().isoformat(timespec="seconds"), "")] + [(f"input:{p}", "", h) for p, h in watched.items()],
                 columns=["item", "value", "sha256"]).to_csv(out / "inputs_and_method.csv", index=False)
    changed = [str(p) for p, h in watched.items() if sha(p) != h]
    pd.DataFrame([dict(check="inputs unchanged (sha256 before/after)", status="FAIL" if changed else "PASS", detail=f"{len(watched)} files")]).to_csv(out / "readonly_proof.csv", index=False)
    print(V.to_string(index=False)); print()
    with pd.option_context("display.width", 250, "display.max_columns", 30):
        print(CSd.drop(columns=["feature_ids"], errors="ignore").to_string(index=False))
    print()
    for _, r in Fd.iterrows():
        print(f"[{r.classification}] {r.finding_id}: {r.observation}")
    print("\ninputs unchanged:", not changed, f"({len(watched)} files hashed)"); print("output:", out)
    sys.exit(1 if changed else 0)


if __name__ == "__main__":
    main()
