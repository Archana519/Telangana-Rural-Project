#!/usr/bin/env python
"""dk_stageB_boundary_mask_diag_v1.py  -  READ-ONLY boundary vs. invalid-cost / prohibited-mask diagnostic.

Question: are road-line-covered cells with invalid cost AND prohibited-mask=1 outside the study-area polygon (H1),
or inside it but next to a masked edge (H2)?  Planning-grid evidence only: nothing here says anything about legal access,
ownership or physical passability.  No routing.  Existing inputs/outputs are never modified; a NEW folder is created and
an existing folder is never overwritten.

Method (all stated in findings):
 * road-line-covered cells = rasterize(TGRAC lines, cost grid, all_touched=True), as dk_stageB_run load_world;
 * passable = finite cost>0 & ~(WorldCover==water | prohibited>0 | slope>limit) with the stageB config values (same rule as the planner);
 * set B = road-line-covered cells with invalid cost AND prohibited>0 ; set A = rows of blocking_chain_cells.csv;
 * cell-centre in polygon: shapely covers(Point); signed distance = +distance to polygon boundary if inside, - if outside (m, EPSG:32644);
 * road length outside = sum over features of length(geom.difference(polygon)); near-edge inside lengths = length(geom ∩ polygon ∩ boundary.buffer(d)).
"""
import argparse, hashlib, json, sys, datetime
from pathlib import Path
import numpy as np, pandas as pd, geopandas as gpd, rasterio
from rasterio.features import rasterize, geometry_mask
from shapely.geometry import Point, box

CRS = "EPSG:32644"
BANDS = [10, 30, 60]          # m; 30 m = DEM cell size of align_damarakunta_terrain.py


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def same_grid(T1, crs1, s1, T2, crs2, s2, tol=1e-6):
    return s1 == s2 and crs1 is not None and crs2 is not None and crs1 == crs2 and all(abs(a - b) <= tol for a, b in zip(tuple(T1)[:6], tuple(T2)[:6]))


def read(path):
    with rasterio.open(path) as s:
        arr = s.read(1).astype(float)
        if s.nodata is not None:
            arr[arr == s.nodata] = np.nan
        return arr, s.transform, s.crs


def label_sizes(mask):
    H, W = mask.shape
    seen = np.zeros_like(mask, bool); sizes = []
    NB = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
    for r0, c0 in zip(*np.nonzero(mask)):
        if seen[r0, c0]:
            continue
        st = [(r0, c0)]; seen[r0, c0] = True; n = 0
        while st:
            r, c = st.pop(); n += 1
            for dr, dc in NB:
                r2, c2 = r + dr, c + dc
                if 0 <= r2 < H and 0 <= c2 < W and mask[r2, c2] and not seen[r2, c2]:
                    seen[r2, c2] = True; st.append((r2, c2))
        sizes.append(n)
    return sorted(sizes, reverse=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stageb-root", required=True)
    ap.add_argument("--run", default="S2_fac_C0_s25_K3_P2")
    ap.add_argument("--chain-csv", default=None, help="default: <stageb-root>/_c0002_roadcell_diag_v1/blocking_chain_cells.csv")
    ap.add_argument("--boundary", default=None)
    ap.add_argument("--boundary-layer", default="village_boundary")
    ap.add_argument("--out-name", default="_boundary_mask_diag_v1")
    ap.add_argument("--expect-total", type=int, default=8061)
    ap.add_argument("--expect-dropped", type=int, default=1567)
    ap.add_argument("--expect-both", type=int, default=1564)
    ap.add_argument("--expect-chain", type=int, default=36)
    a = ap.parse_args()
    root = Path(a.stageb_root); d = root / a.run; out = root / a.out_name
    if out.exists():
        sys.exit(f"stopping: {out} exists (never overwritten)")
    chain_p = Path(a.chain_csv) if a.chain_csv else root / "_c0002_roadcell_diag_v1" / "blocking_chain_cells.csv"
    for p in (d / "config_stageB.json", d / "inputs_manifest_stageB.csv", d / "road_components.csv", chain_p):
        if not p.exists():
            sys.exit(f"stopping: missing input {p}")
    watched = {p: sha(p) for p in (d / "config_stageB.json", d / "inputs_manifest_stageB.csv", d / "road_components.csv", chain_p)}
    cfg = json.loads((d / "config_stageB.json").read_text(encoding="utf-8")); rc = cfg.get("resolved_constraints", {})
    mf = pd.read_csv(d / "inputs_manifest_stageB.csv").set_index("role")
    for r in ("cost", "worldcover", "roads"):
        if r not in mf.index:
            sys.exit(f"stopping: manifest role '{r}' missing")
    paths = {r: Path(mf.loc[r, "path"]) for r in ("cost", "worldcover", "roads")}
    blocked_p, slope_p = rc.get("prohibited_raster"), rc.get("slope_raster")
    slope_lim, water_c = rc.get("slope_limit_deg"), rc.get("water_class", 80)
    if not blocked_p or not slope_p or slope_lim is None:
        sys.exit("stopping: config_stageB.json resolved_constraints lacks prohibited_raster / slope_raster / slope_limit_deg")
    # boundary: manifest role if present, else the location written by align_damarakunta_terrain.py (study_area/damarakunta_boundary.gpkg)
    if a.boundary:
        bpath = Path(a.boundary)
    elif "boundary" in mf.index:
        bpath = Path(mf.loc["boundary", "path"])
    else:
        bpath = paths["cost"].parent.parent / "study_area" / "damarakunta_boundary.gpkg"
    if not bpath.exists():
        sys.exit(f"stopping: boundary file not found: {bpath}")
    dem30 = paths["cost"].parent / "damarakunta_dem_30m.tif"
    extra = [Path(blocked_p), Path(slope_p), bpath] + ([dem30] if dem30.exists() else [])
    for p in list(paths.values()) + extra:
        if not p.exists():
            sys.exit(f"stopping: missing input {p}")
        watched[p] = sha(p)
    hash_ok = {r: watched[paths[r]] == mf.loc[r, "sha256"] for r in paths}

    # ---- rebuild passability exactly as the planner (cost grid)
    cost, T, crs = read(paths["cost"])
    if crs is None or crs.to_epsg() != 32644:
        sys.exit(f"stopping: cost raster CRS {crs}")
    H, W = cost.shape
    w, Tw, cw = read(paths["worldcover"]); pro, Tp, cp = read(Path(blocked_p)); slo, Ts, cs_ = read(Path(slope_p))
    for nm, (arr, Ta, ca) in dict(worldcover=(w, Tw, cw), prohibited=(pro, Tp, cp), slope=(slo, Ts, cs_)).items():
        if not same_grid(T, crs, cost.shape, Ta, ca, arr.shape):
            sys.exit(f"stopping: {nm} raster is not on the cost grid; planner rule not reproducible")
    ok = np.isfinite(cost) & (cost > 0)
    water = (w == water_c); prohib = np.nan_to_num(pro, nan=0) > 0; slopef = np.nan_to_num(slo, nan=0) > slope_lim
    passable = ok & ~(water | prohib | slopef)
    import pyogrio
    lays = [x[0] for x in pyogrio.list_layers(bpath)]
    if a.boundary_layer in lays:
        lay = a.boundary_layer
    elif len(lays) == 1:
        lay = lays[0]; print(f"note: layer '{a.boundary_layer}' absent; using the only layer '{lay}'")
    else:
        sys.exit(f"stopping: layer '{a.boundary_layer}' not in {lays}")
    boundary = gpd.read_file(bpath, layer=lay)
    if boundary.crs is None:
        sys.exit("stopping: boundary CRS undefined")
    boundary = boundary.to_crs(CRS)
    poly = boundary.geometry.union_all(); bline = poly.boundary
    roads = gpd.read_file(paths["roads"])
    if roads.crs is None:
        sys.exit("stopping: roads CRS undefined")
    roads = roads.to_crs(CRS); roads = roads[roads.geometry.notna() & ~roads.geometry.is_empty].reset_index(drop=True)
    rr = rasterize([(g, 1) for g in roads.geometry], out_shape=(H, W), transform=T, fill=0, all_touched=True, dtype="uint8").astype(bool)
    sizes = label_sizes(rr & passable)
    rec = list(pd.read_csv(d / "road_components.csv").sort_values("component_id").n_cells.astype(int))
    setB = rr & ~ok & prohib
    cnt = dict(total=int(rr.sum()), dropped=int((rr & ~passable).sum()), both=int(setB.sum()))
    chain = pd.read_csv(chain_p)
    if not {"row", "col"} <= set(chain.columns):
        sys.exit("stopping: chain csv lacks row/col columns")
    chain_blocked = chain[~chain.passable.astype(bool)] if "passable" in chain.columns else chain
    val = [("rebuilt component sizes equal road_components.csv", str(sizes), str(rec), sizes == rec),
           ("input hashes equal inputs_manifest_stageB.csv", str(hash_ok), "manifest", all(hash_ok.values())),
           ("road-line-covered cells", cnt["total"], a.expect_total, a.expect_total < 0 or cnt["total"] == a.expect_total),
           ("road cells dropped as impassable", cnt["dropped"], a.expect_dropped, a.expect_dropped < 0 or cnt["dropped"] == a.expect_dropped),
           ("road cells invalid-cost AND prohibited>0", cnt["both"], a.expect_both, a.expect_both < 0 or cnt["both"] == a.expect_both),
           ("blocked chain cells in chain csv", len(chain_blocked), a.expect_chain, a.expect_chain < 0 or len(chain_blocked) == a.expect_chain)]
    cs = set(zip(chain_blocked.row.astype(int), chain_blocked.col.astype(int)))
    val.append(("every chain cell is in set B", sum(setB[r, c] for r, c in cs), len(cs), all(setB[r, c] for r, c in cs)))
    V = pd.DataFrame(val, columns=["check", "rebuilt", "expected", "ok"])
    if not V.ok.all():
        print(V.to_string(index=False)); sys.exit("stopping: validation gate FAILED; nothing written (no guessing)")

    # ---- mask-generation rule check on the whole grid (align_damarakunta_terrain.py: inside = geometry_mask(centre), wc[~inside]=0, slope10[~inside]=nodata)
    inside_grid = geometry_mask([poly], out_shape=(H, W), transform=T, invert=True)
    bad_prohib_out = int((~inside_grid & (pro != 1)).sum())
    rule = dict(cells_outside=int((~inside_grid).sum()), outside_wc_nan=int((~inside_grid & ~np.isfinite(w)).sum()), outside_slope_nan=int((~inside_grid & ~np.isfinite(slo)).sum()),
                outside_cost_nan=int((~inside_grid & ~ok).sum()), outside_prohib1=int((~inside_grid & (pro == 1)).sum()), inside_cells=int(inside_grid.sum()),
                inside_wc_nan=int((inside_grid & ~np.isfinite(w)).sum()), inside_slope_nan=int((inside_grid & ~np.isfinite(slo)).sum()),
                inside_prohib1=int((inside_grid & (pro == 1)).sum()))

    # ---- per-cell relation to boundary
    dem_arr = dem_T = None
    if dem30.exists():
        dem_arr, dem_T, dem_crs = read(dem30)
        if dem_crs is None or dem_crs.to_epsg() != 32644:
            dem_arr = None

    def dem_valid(x, y):
        if dem_arr is None:
            return ""
        col, row = ~dem_T * (x, y); r, c = int(np.floor(row)), int(np.floor(col))
        return bool(0 <= r < dem_arr.shape[0] and 0 <= c < dem_arr.shape[1] and np.isfinite(dem_arr[r, c]))

    def rel(r, c, grp):
        x, y = T * (c + 0.5, r + 0.5); pt = Point(x, y); ins = bool(poly.covers(pt)); dist = float(pt.distance(bline))
        fp = box(x - abs(T.a) / 2, y - abs(T.e) / 2, x + abs(T.a) / 2, y + abs(T.e) / 2)
        return dict(group=grp, row=int(r), col=int(c), x=x, y=y, centre_in_polygon=ins, dist_to_boundary_m=round(dist, 3), signed_dist_m=round(dist if ins else -dist, 3),
                    footprint_frac_in_polygon=round(fp.intersection(poly).area / fp.area, 4), grid_inside_mask=bool(inside_grid[r, c]), worldcover=w[r, c], slope=slo[r, c], cost=cost[r, c],
                    prohibited=pro[r, c], passable=bool(passable[r, c]), dem30_cell_valid=dem_valid(x, y))
    rows = [rel(r, c, "B_invalid_and_prohibited") for r, c in zip(*np.nonzero(setB))]
    for rw in rows:
        rw["in_chain36"] = (rw["row"], rw["col"]) in cs
    other = rr & ~passable & ~setB
    rows += [dict(rel(r, c, "other_dropped"), in_chain36=False) for r, c in zip(*np.nonzero(other))]
    pas = np.argwhere(rr & passable)
    rows += [dict(rel(r, c, "passable_reference"), in_chain36=False) for r, c in pas]
    C = pd.DataFrame(rows)

    def cls(g):
        if not g.centre_in_polygon:
            return "OUTSIDE_polygon"
        for b in BANDS:
            if g.dist_to_boundary_m <= b:
                return f"INSIDE_within_{b}m"
        return f"INSIDE_beyond_{BANDS[-1]}m"
    C["position_class"] = C.apply(cls, axis=1)
    Bd = C[C.group == "B_invalid_and_prohibited"]; Ch = Bd[Bd.in_chain36]; Pr = C[C.group == "passable_reference"]

    def tab(df):
        s = df.position_class.value_counts().to_dict()
        return {k: int(s.get(k, 0)) for k in ["OUTSIDE_polygon"] + [f"INSIDE_within_{b}m" for b in BANDS] + [f"INSIDE_beyond_{BANDS[-1]}m"]}

    def dstat(df, ins):
        x = df[df.centre_in_polygon == ins].dist_to_boundary_m
        return "n=0" if not len(x) else f"n={len(x)} min={x.min():.1f} median={x.median():.1f} max={x.max():.1f} m"

    # ---- road geometry vs polygon
    lines = roads.geometry
    tot = float(lines.length.sum())
    outs = lines.apply(lambda g: g.difference(poly)); outlen = outs.length
    ins_g = lines.apply(lambda g: g.intersection(poly))
    u_all = lines.union_all(); u_out = u_all.difference(poly)
    RL = pd.DataFrame(dict(feature=roads.index, total_len_m=lines.length.round(3), outside_len_m=outlen.round(3), inside_len_m=ins_g.length.round(3)))
    near = {}
    for b in BANDS:
        zone = bline.buffer(b, resolution=32)
        near[b] = float(ins_g.apply(lambda g: g.intersection(zone)).length.sum())
        RL[f"inside_within_{b}m_of_boundary_m"] = ins_g.apply(lambda g: g.intersection(zone)).length.round(3)
    # distance of road-line cells' outside pieces: how far outside do the roads go
    maxout = 0.0
    for g in outs:
        if not g.is_empty:
            pts = [Point(c) for part in (g.geoms if hasattr(g, "geoms") else [g]) for c in part.coords]
            maxout = max(maxout, max(float(p.distance(poly)) for p in pts))

    # ---- findings
    F = []

    def add(i, c, o, v=""):
        assert c in ("VERIFIED_FACT", "HYPOTHESIS", "UNRESOLVED")
        F.append(dict(finding_id=i, classification=c, observation=o, value=v))
    add("E0", "VERIFIED_FACT", f"validation gate passed: rebuilt road-line cells {cnt['total']}, dropped {cnt['dropped']}, invalid-cost AND prohibited {cnt['both']}; chain cells {len(cs)} all in that set; component sizes equal road_components.csv; input hashes equal manifest", cnt["both"])
    add("E1", "VERIFIED_FACT", "generation rule read from scripts (not inferred): align_damarakunta_terrain.py sets WorldCover=0 and slope=-9999 for every 10 m cell whose CENTRE is outside the boundary (geometry_mask); slope is 30 m DEM slope resampled bilinearly (nodata propagates); create_damarakunta_cost_surface.py sets prohibited=1 unless WorldCover is a listed land class AND slope is valid, and sets cost NaN under the same condition. So prohibited=1 and cost NaN are the same condition by construction, and carry no legal meaning.", "")
    add("E2", "VERIFIED_FACT", f"rule reproduced on the whole grid ({H}x{W}): of {rule['cells_outside']} cells with centre outside the polygon, WorldCover NaN {rule['outside_wc_nan']}, slope NaN {rule['outside_slope_nan']}, cost NaN {rule['outside_cost_nan']}, prohibited=1 {rule['outside_prohib1']}; inside {rule['inside_cells']} cells: WorldCover NaN {rule['inside_wc_nan']}, slope NaN {rule['inside_slope_nan']}, prohibited=1 {rule['inside_prohib1']}", "")
    add("E3", "VERIFIED_FACT", f"set B ({len(Bd)} cells) by cell-centre position: {tab(Bd)}; inside-polygon distance to boundary: {dstat(Bd, True)}; outside-polygon distance: {dstat(Bd, False)}", int((~Bd.centre_in_polygon).sum()))
    add("E4", "VERIFIED_FACT", f"36 chain cells ({len(Ch)} matched) by position: {tab(Ch)}; inside: {dstat(Ch, True)}; outside: {dstat(Ch, False)}", int((~Ch.centre_in_polygon).sum()))
    if dem_arr is not None:
        ins_B = Bd[Bd.centre_in_polygon]
        add("E5", "VERIFIED_FACT", f"set B cells with centre INSIDE the polygon: {len(ins_B)}; of these the 30 m DEM cell at the centre is valid in {int((ins_B.dem30_cell_valid == True).sum())} and masked in {int((ins_B.dem30_cell_valid == False).sum())}; WorldCover finite in {int(np.isfinite(ins_B.worldcover).sum())}; slope finite in {int(np.isfinite(ins_B.slope).sum())}", len(ins_B))
    else:
        add("E5", "UNRESOLVED", "damarakunta_dem_30m.tif not found next to the cost raster: DEM-cell validity of inside cells not tested", "")
    add("E6", "VERIFIED_FACT", f"passable road-line cells ({len(Pr)}) by position: {tab(Pr)}", int((~Pr.centre_in_polygon).sum()))
    add("E7", "VERIFIED_FACT", f"TGRAC road length (sum of {len(roads)} features, EPSG:32644, shapely length): total {tot:.2f} m; outside polygon {float(outlen.sum()):.2f} m ({100*outlen.sum()/tot:.2f}%) by per-feature geometry.difference(polygon); outside by dissolved union {u_out.length:.2f} m; features with any outside part {int((outlen > 1e-6).sum())}; farthest outside vertex {maxout:.2f} m from the polygon", round(float(outlen.sum()), 2))
    add("E8", "VERIFIED_FACT", "road length INSIDE the polygon within d of the boundary (buffer resolution 32 segments/quadrant): " + "; ".join(f"{b} m: {near[b]:.2f} m" for b in BANDS), "")
    n_out, n_in = int((~Bd.centre_in_polygon).sum()), int(Bd.centre_in_polygon.sum())
    add("H1", "HYPOTHESIS", f"if E3 shows most set-B cells outside the polygon: the invalid/prohibited road cells are an artefact of road lines being drawn beyond the clipped study-area mask (observed outside {n_out}, inside {n_in}). Not a statement about the road's real status.", "")
    add("H2", "HYPOTHESIS", "cells inside the polygon but within ~30 m of the boundary can be invalid because the 30 m DEM slope is masked/interpolated at the edge (see E5); the reason a given inside cell is invalid is shown by its WorldCover/slope columns, not assumed.", "")
    add("U1", "UNRESOLVED", "whether the polygon itself is correct (TGRAC boundary not compared with an independent boundary) and whether the road lines outside it are real roads are not decided here; no legal access, ownership or passability is inferred; no routing was done.", "")
    Fd = pd.DataFrame(F)

    # ---- write (new folder only)
    out.mkdir(parents=True)
    C.to_csv(out / "cell_boundary_relation.csv", index=False)
    RL.to_csv(out / "road_length_by_feature.csv", index=False)
    V.to_csv(out / "validation_gate.csv", index=False)
    Fd.to_csv(out / "boundary_diag_findings.csv", index=False)
    pd.DataFrame([dict(metric=k, value=v) for k, v in {**rule, **{f"setB_{k}": v for k, v in tab(Bd).items()}, **{f"chain36_{k}": v for k, v in tab(Ch).items()},
                  **{f"passable_{k}": v for k, v in tab(Pr).items()}, "road_total_m": round(tot, 2), "road_outside_m": round(float(outlen.sum()), 2), "road_outside_union_m": round(u_out.length, 2),
                  **{f"road_inside_within_{b}m_m": round(near[b], 2) for b in BANDS}}.items()]).to_csv(out / "boundary_diag_summary.csv", index=False)
    changed = [str(p) for p, h in watched.items() if sha(p) != h]
    pd.DataFrame([dict(check="inputs unchanged (sha256 before/after)", status="FAIL" if changed else "PASS", detail=f"{len(watched)} files")]).to_csv(out / "readonly_proof.csv", index=False)
    print(V.to_string(index=False)); print()
    for _, r in Fd.iterrows():
        print(f"[{r.classification}] {r.finding_id}: {r.observation}")
    print("\ninputs unchanged:", not changed, f"({len(watched)} files hashed)"); print("output:", out)
    sys.exit(1 if changed else 0)


if __name__ == "__main__":
    main()
