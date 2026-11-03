"""dk_stageB_c0002_roadcell_diag_v1.py - READ-ONLY diagnostic of why a target's road attachment lies on a small road-CELL component
although the source road LINES join the main network.

It re-creates, from the same input files the run used, the planner's passable road-cell set exactly as plan_network_v2.load_world does:
  rr   = rasterize(road lines, shape/transform of the cost raster, all_touched=True)
  ok   = isfinite(cost) & (cost > 0)                                   (Grid.__init__)
  hard = (WorldCover == water_class)  |  (prohibited > 0)  |  (slope > slope_limit_deg)      [each only if its raster is on the cost grid]
  pass = ok & ~hard ;  road_cells = rr & pass ;  components = 8-connected, id 1 = largest, ties by lowest row-major cell index
(buildings / builtup multipliers only scale cost and never change passability.)
VALIDATION GATE: the rebuilt component sizes must equal the run's road_components.csv and the attachment cell's component must equal the
recorded road_component; otherwise nothing is concluded (status UNRESOLVED) and the script exits with code 2.
Diagnosis: a 0-1 BFS over ALL road-line-covered cells (rr, passable or not) from the target's component to the main component. Impassable
cells on the cheapest such path are the cells that break cell connectivity while the line itself is continuous. If no such path exists the
break is in the rasterised line coverage itself.
Nothing is routed; no input is modified; output goes only to <stageb-root>/<out-name> (must not exist).
Geometric/raster evidence on the planning grid only: not legal access, ownership or physical passability."""
import argparse, hashlib, json, sys, datetime
from collections import deque
from pathlib import Path
import numpy as np, pandas as pd, geopandas as gpd, rasterio
from rasterio.features import rasterize
from shapely.geometry import Point, box

CRS = "EPSG:32644"


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def same_grid(T1, crs1, shape1, T2, crs2, shape2, tol=1e-6):
    return (shape1 == shape2 and crs1 is not None and crs2 is not None and crs1 == crs2 and all(abs(a - b) <= tol for a, b in zip(tuple(T1)[:6], tuple(T2)[:6])))


def read(path):
    with rasterio.open(path) as s:
        arr = s.read(1).astype(float)
        if s.nodata is not None:
            arr[arr == s.nodata] = np.nan
        return arr, s.transform, s.crs


NB = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


def label_components(mask):
    """8-connected components of a boolean array; ids by (-size, min row-major index), as dk_stageB_run components()."""
    H, W = mask.shape
    seen = np.zeros_like(mask, bool); comps = []
    for r0, c0 in zip(*np.nonzero(mask)):
        if seen[r0, c0]:
            continue
        st, comp = [(r0, c0)], []
        seen[r0, c0] = True
        while st:
            r, c = st.pop(); comp.append((r, c))
            for dr, dc in NB:
                rr_, cc_ = r + dr, c + dc
                if 0 <= rr_ < H and 0 <= cc_ < W and mask[rr_, cc_] and not seen[rr_, cc_]:
                    seen[rr_, cc_] = True; st.append((rr_, cc_))
        comps.append(comp)
    comps.sort(key=lambda c: (-len(c), min(r * W + cc for r, cc in c)))
    lab = np.zeros(mask.shape, int)
    for i, c in enumerate(comps, 1):
        for r, cc in c:
            lab[r, cc] = i
    return lab, [len(c) for c in comps]


def min_block_chain(rr, passable, lab, cells10):
    """0-1 BFS over road-line-covered cells rr (8-connected) from cells10 to any cell with label 1. Cost 1 per impassable cell.
    Returns (goal, path) or (None, [])."""
    H, W = rr.shape
    INFc = 10 ** 9
    dist = np.full((H, W), INFc, int); prev = {}
    dq = deque()
    for c in cells10:
        dist[c] = 0; dq.append(c)
    while dq:
        r, c = dq.popleft()
        if lab[r, c] == 1:
            goal = (r, c); cur = goal; path = [cur]
            while cur in prev:
                cur = prev[cur]; path.append(cur)
            return goal, path[::-1]
        for dr, dc in NB:
            r2, c2 = r + dr, c + dc
            if 0 <= r2 < H and 0 <= c2 < W and rr[r2, c2]:
                w_ = 0 if passable[r2, c2] else 1
                if dist[r, c] + w_ < dist[r2, c2]:
                    dist[r2, c2] = dist[r, c] + w_; prev[(r2, c2)] = (r, c)
                    (dq.appendleft if w_ == 0 else dq.append)((r2, c2))
    return None, []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stageb-root", required=True)
    ap.add_argument("--run", default="S2_fac_C0_s25_K3_P2")
    ap.add_argument("--target", default="C0002")
    ap.add_argument("--margin-cells", type=int, default=5)
    ap.add_argument("--out-name", default="_c0002_roadcell_diag_v1")
    a = ap.parse_args()
    root = Path(a.stageb_root); d = root / a.run; out = root / a.out_name
    if out.exists():
        sys.exit(f"stopping: {out} exists (never overwritten)")
    F, watched = [], {}

    def add(fid, cls, obs, val=""):
        assert cls in ("VERIFIED_FACT", "PLAUSIBLE", "UNRESOLVED")
        F.append(dict(finding_id=fid, classification=cls, observation=obs, value=val))

    for f in ("config_stageB.json", "inputs_manifest_stageB.csv", "road_components.csv", "connectivity_checks.csv", "routes.gpkg"):
        if not (d / f).exists():
            sys.exit(f"missing {d / f}")
        watched[d / f] = sha(d / f)
    cfg = json.loads((d / "config_stageB.json").read_text(encoding="utf-8"))
    rc = cfg.get("resolved_constraints", {})
    mf = pd.read_csv(d / "inputs_manifest_stageB.csv").set_index("role")
    need = ["cost", "worldcover", "roads"]
    for r in need:
        if r not in mf.index:
            sys.exit(f"manifest role '{r}' missing: cannot rebuild the road-cell set (no guessing)")
    paths = {r: Path(mf.loc[r, "path"]) for r in need}
    blocked_p, slope_p = rc.get("prohibited_raster"), rc.get("slope_raster")
    slope_lim, water_c = rc.get("slope_limit_deg"), rc.get("water_class", 80)
    for k, p in list(paths.items()) + [("blocked", Path(blocked_p) if blocked_p else None), ("slope", Path(slope_p) if slope_p else None)]:
        if p is not None and p.exists():
            watched[p] = sha(p)
    hash_ok = {r: (watched.get(paths[r]) == mf.loc[r, "sha256"]) for r in need}

    cost, T, crs = read(paths["cost"])
    if crs is None or crs.to_epsg() != 32644:
        sys.exit(f"cost raster CRS {crs}")
    H, W = cost.shape
    hard = np.zeros((H, W), bool)
    reason = {k: np.zeros((H, W), bool) for k in ("water", "prohibited", "slope")}
    used = {}
    if paths["worldcover"].exists():
        w, Tw, crsw = read(paths["worldcover"])
        if same_grid(T, crs, cost.shape, Tw, crsw, w.shape):
            reason["water"] = (w == water_c); hard |= reason["water"]; used["water"] = True
        else:
            used["water"] = False
    else:
        w = np.full((H, W), np.nan); used["water"] = False
    pro = np.full((H, W), np.nan); slo = np.full((H, W), np.nan)
    for nm, pth, thr in (("prohibited", blocked_p, None), ("slope", slope_p, slope_lim)):
        if pth and Path(pth).exists() and not (nm == "slope" and thr is None):
            arr, Ta, crsa = read(pth)
            if same_grid(T, crs, cost.shape, Ta, crsa, arr.shape):
                m = (np.nan_to_num(arr, nan=0) > 0) if nm == "prohibited" else (np.nan_to_num(arr, nan=0) > thr)
                reason[nm] = m; hard |= m; used[nm] = True
                if nm == "prohibited": pro = arr
                else: slo = arr
            else:
                used[nm] = False
        else:
            used[nm] = False
    ok = np.isfinite(cost) & (cost > 0)
    passable = ok & ~hard
    roads = gpd.read_file(paths["roads"]).to_crs(CRS)
    roads = roads[roads.geometry.notna() & ~roads.geometry.is_empty]
    rr = rasterize([(x, 1) for x in roads.geometry], out_shape=(H, W), transform=T, fill=0, all_touched=True, dtype="uint8").astype(bool)
    road_cells = rr & passable
    lab, sizes = label_components(road_cells)
    ts = {k: bool(v) for k, v in used.items()}

    # ---- validation gate
    rec = pd.read_csv(d / "road_components.csv").sort_values("component_id")
    rec_sizes = list(rec.n_cells.astype(int)); match = rec_sizes == sizes
    cc = pd.read_csv(d / "connectivity_checks.csv"); cc["target_id"] = cc.target_id.astype(str)
    rrow = cc[cc.target_id == a.target]
    rec_comp = int(float(rrow.road_component.iloc[0])) if len(rrow) and pd.notna(rrow.road_component.iloc[0]) else None
    routes = gpd.read_file(d / "routes.gpkg", layer="routes_network_houses")
    rt = routes[routes.target_id.astype(str) == a.target]
    if rt.empty:
        sys.exit(f"{a.target} not in routes_network_houses")
    endpt = Point(list(rt.geometry.iloc[0].coords)[-1])

    def cell_of(pt):
        col, row = ~T * (pt.x, pt.y)
        return int(np.floor(row)), int(np.floor(col))
    er, ec = cell_of(endpt)
    my_lab = int(lab[er, ec]) if 0 <= er < H and 0 <= ec < W else 0
    gate = match and my_lab == rec_comp
    val = pd.DataFrame([
        dict(check="rebuilt road-cell total", rebuilt=sum(sizes), recorded=sum(rec_sizes), ok=sum(sizes) == sum(rec_sizes)),
        dict(check="rebuilt component sizes equal road_components.csv", rebuilt=str(sizes), recorded=str(rec_sizes), ok=match),
        dict(check=f"{a.target} attachment-cell component equals connectivity_checks road_component", rebuilt=my_lab, recorded=rec_comp, ok=my_lab == rec_comp),
        dict(check="input hashes equal inputs_manifest_stageB.csv (cost, worldcover, roads)", rebuilt=str(hash_ok), recorded="manifest", ok=all(hash_ok.values())),
        dict(check="constraint rasters applied (on the cost grid)", rebuilt=str(ts), recorded=str({k: rc.get(k) for k in ('prohibited_raster', 'slope_raster', 'slope_limit_deg', 'water_class')}), ok=True)])
    add("D0", "VERIFIED_FACT" if gate else "UNRESOLVED", f"rebuild gate {'PASSED' if gate else 'FAILED'}: sizes_match={match}, attachment component rebuilt={my_lab} vs recorded={rec_comp}", my_lab)
    totals = dict(rr_total=int(rr.sum()), rr_passable=int((rr & passable).sum()), rr_dropped=int((rr & ~passable).sum()))
    add("D1", "VERIFIED_FACT" if gate else "UNRESOLVED",
        f"road-line-covered cells (rasterize all_touched=True on the cost grid {H}x{W}, {abs(T.a):g} m): {totals['rr_total']}; passable {totals['rr_passable']}; dropped as impassable {totals['rr_dropped']} "
        f"(by reason, overlapping: invalid/non-positive cost {int((rr & ~ok).sum())}, water class {water_c} {int((rr & reason['water']).sum())}, prohibited>0 {int((rr & reason['prohibited']).sum())}, slope>{slope_lim} {int((rr & reason['slope']).sum())})", totals["rr_dropped"])

    cells10 = [(r, c) for r, c in zip(*np.nonzero(lab == my_lab))] if my_lab else []
    cells1 = np.argwhere(lab == 1)
    gapdist = np.nan; pair = None
    if len(cells10) and len(cells1):
        a10 = np.array(cells10)
        dd = np.sqrt(((a10[:, None, :] - cells1[None, :, :]) ** 2).sum(-1)) * abs(T.a)
        i, j = np.unravel_index(np.argmin(dd), dd.shape); gapdist = float(dd[i, j]); pair = (tuple(a10[i]), tuple(cells1[j]))
    if gate:
        add("D2", "VERIFIED_FACT", f"component {my_lab} has {len(cells10)} cells; nearest main-component (id 1, {sizes[0]} cells) cell is {gapdist:.2f} m away centre-to-centre (cells {pair})", round(gapdist, 2))

    # ---- 0-1 BFS through ALL road-line-covered cells
    path = []
    if gate and len(cells10):
        goal, path = min_block_chain(rr, passable, lab, cells10)
        if goal is None:
            add("D3", "VERIFIED_FACT", "no 8-connected chain of road-line-covered cells links the component to the main component: the break is in the rasterised line coverage itself, not in the constraint masks", "")
        else:
            blocked_cells = [p for p in path if not passable[p]]
            add("D3", "VERIFIED_FACT", f"an 8-connected chain of {len(path)} road-line-covered cells links component {my_lab} to the main component; it contains {len(blocked_cells)} impassable cell(s) (minimum over all such chains). With those cells passable the components would be one cell component", len(blocked_cells))
    rows = []
    for k, (r, c) in enumerate(path):
        x, y = T * (c + 0.5, r + 0.5)
        rows.append(dict(order=k, row=r, col=c, x=x, y=y, road_line_covered=True, passable=bool(passable[r, c]), component=int(lab[r, c]), cost=cost[r, c],
                         invalid_cost=bool(not ok[r, c]), water=bool(reason['water'][r, c]), worldcover=w[r, c], prohibited_flag=bool(reason['prohibited'][r, c]), prohibited_value=pro[r, c],
                         slope_flag=bool(reason['slope'][r, c]), slope_value=slo[r, c]))
    P = pd.DataFrame(rows)
    # window listing
    if gate and pair is not None:
        rs = [pair[0][0], pair[1][0]] + [p[0] for p in path]; cs = [pair[0][1], pair[1][1]] + [p[1] for p in path]
        r0, r1 = max(0, min(rs) - a.margin_cells), min(H - 1, max(rs) + a.margin_cells); c0, c1 = max(0, min(cs) - a.margin_cells), min(W - 1, max(cs) + a.margin_cells)
        wrows = []
        for r in range(r0, r1 + 1):
            for c in range(c0, c1 + 1):
                if rr[r, c]:
                    x, y = T * (c + 0.5, r + 0.5)
                    wrows.append(dict(row=r, col=c, x=x, y=y, passable=bool(passable[r, c]), component=int(lab[r, c]), cost=cost[r, c], invalid_cost=bool(not ok[r, c]), water=bool(reason['water'][r, c]),
                                      worldcover=w[r, c], prohibited_flag=bool(reason['prohibited'][r, c]), prohibited_value=pro[r, c], slope_flag=bool(reason['slope'][r, c]), slope_value=slo[r, c]))
        Wd = pd.DataFrame(wrows)
        win = dict(r0=r0, r1=r1, c0=c0, c1=c1)
        if len(P):
            bl = P[~P.passable]
            if len(bl):
                rs_ = []
                for _, b in bl.iterrows():
                    rs_.append("cell(%d,%d) at (%.1f, %.1f): " % (b.row, b.col, b.x, b.y) + ", ".join(n for n, f in (("invalid/non-positive cost", b.invalid_cost), ("water", b.water), ("prohibited", b.prohibited_flag), ("slope", b.slope_flag)) if f))
                add("D4", "VERIFIED_FACT", "impassable cells on the minimum chain: " + " | ".join(rs_), len(bl))
                kinds = set()
                for _, b in bl.iterrows():
                    for n, f in (("invalid_cost", b.invalid_cost), ("water", b.water), ("prohibited", b.prohibited_flag), ("slope", b.slope_flag)):
                        if f: kinds.add(n)
                add("D5", "PLAUSIBLE", f"the component split is produced by the planner's passability rule (constraint masks: {sorted(kinds)}) applied to cells the source road line crosses; whether those mask values are physically meaningful for the road (e.g. a culvert/bridge, a coarse DEM slope, a WorldCover water pixel) is not decided by these files", "")
            elif goal is not None:
                add("D4", "UNRESOLVED", "the chain contains no impassable cell, yet the cells are not 8-connected in the passable set: unexpected; inspect window_road_cells.csv", 0)
    else:
        Wd = pd.DataFrame(); win = None
    add("D6", "UNRESOLVED", "whether the lost connectivity matters for planning (a route to the main component through this stretch, its length/cost) is not assessed: no routing was done", "")

    # ---- write
    out.mkdir(parents=True)
    val.to_csv(out / "component_validation.csv", index=False)
    P.to_csv(out / "blocking_chain_cells.csv", index=False)
    Wd.to_csv(out / "window_road_cells.csv", index=False)
    Fd = pd.DataFrame(F); Fd.to_csv(out / "diagnostic_findings.csv", index=False)
    try:
        import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
        if win is not None:
            fig, ax = plt.subplots(figsize=(9, 7))
            sub = (slice(win["r0"], win["r1"] + 1), slice(win["c0"], win["c1"] + 1))
            img = np.zeros(lab[sub].shape + (3,)); img[:] = 1
            img[rr[sub] & ~passable[sub]] = (0.85, 0.1, 0.1)
            img[lab[sub] == 1] = (0.2, 0.4, 0.8); img[(lab[sub] > 1)] = (0.3, 0.7, 0.3); img[lab[sub] == my_lab] = (0.95, 0.6, 0.1)
            ax.imshow(img, extent=(T.c + win["c0"] * T.a, T.c + (win["c1"] + 1) * T.a, T.f + (win["r1"] + 1) * T.e, T.f + win["r0"] * T.e), origin="upper")
            for g in roads.geometry:
                for ln in (g.geoms if hasattr(g, "geoms") else [g]):
                    ax.plot(*ln.xy, color="k", lw=0.8)
            ax.plot(endpt.x, endpt.y, "m*", ms=12)
            ax.set_xlim(T.c + win["c0"] * T.a, T.c + (win["c1"] + 1) * T.a); ax.set_ylim(T.f + (win["r1"] + 1) * T.e, T.f + win["r0"] * T.e)
            ax.set_title(f"{a.target}: road cells (orange = attached component {my_lab}, blue = main, green = other, red = line-covered but impassable); lines black")
            ax.set_aspect("equal"); fig.savefig(out / "window_map.png", dpi=130, bbox_inches="tight"); plt.close(fig)
    except Exception as e:
        print("map skipped:", e)
    changed = [str(p) for p, h in watched.items() if sha(p) != h]
    pd.DataFrame([dict(check="inputs unchanged (sha256 before/after)", status="FAIL" if changed else "PASS", detail=f"{len(watched)} files")]).to_csv(out / "readonly_proof.csv", index=False)
    md = ["# C0002 road-cell connectivity diagnostic v1 (read-only)", "", f"Generated {datetime.datetime.now():%Y-%m-%d %H:%M} by `dk_stageB_c0002_roadcell_diag_v1.py` for run `{a.run}`. Inputs unchanged: {'YES' if not changed else 'NO'} ({len(watched)} files hashed).", "",
          "Raster/planning-grid evidence only; not legal access, ownership or physical passability. Nothing was routed.", "", "## Validation gate", "",
          val.to_markdown(index=False) if hasattr(val, "to_markdown") and _has_tab() else val.to_string(index=False), "", "## Findings", ""]
    for _, r in Fd.iterrows():
        md.append(f"- **{r.finding_id} [{r.classification}]** {r.observation}")
    md += ["", "Files: component_validation.csv, diagnostic_findings.csv, blocking_chain_cells.csv, window_road_cells.csv, window_map.png (if matplotlib available), readonly_proof.csv."]
    (out / "diagnostic_report.md").write_text("\n".join(md), encoding="utf-8")
    print(Fd[["finding_id", "classification", "observation"]].to_string(index=False, max_colwidth=200)); print("written:", out, "| inputs unchanged:", not changed)
    sys.exit(0 if gate else 2)


def _has_tab():
    try:
        import tabulate  # noqa
        return True
    except Exception:
        return False


if __name__ == "__main__":
    main()
