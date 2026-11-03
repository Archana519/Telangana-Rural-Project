#!/usr/bin/env python
"""dk_stageB_chain_cell_reasons_v1.py - READ-ONLY chain-cell attribution for non-main road components (C2, C5, C6, C10, C11, C12).

Per chain cell: index/coordinates, chain membership, covering source feature ids (parts rasterised alone, all_touched=True), inside/outside polygon (centre),
cost validity, prohibited value, WorldCover, slope, DEM30 observations, and an invalid-cell reason that is DERIVED ONLY from observed values and the
generation rules read in create_damarakunta_cost_surface.py / align_damarakunta_terrain.py. Where the observed values do not identify a cause the cell is labelled UNRESOLVED.
Reuses helper functions of dk_stageB_road_component_boundary_diag_v1.py (same folder). No routing; nothing is modified; a NEW folder is written, never overwritten.
"""
import argparse, json, sys, datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np, pandas as pd, geopandas as gpd, rasterio, shapely
from rasterio.features import rasterize
from shapely.geometry import Point
import dk_stageB_road_component_boundary_diag_v1 as base

CRS = "EPSG:32644"
LAND = {10, 20, 30, 40, 50, 60}     # LAND_COST keys in create_damarakunta_cost_surface.py
COMPS = [2, 5, 6, 10, 11, 12]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stageb-root", required=True)
    ap.add_argument("--run", default="S2_fac_C0_s25_K3_P2")
    ap.add_argument("--prev-diag", default="_road_component_boundary_diag_v1")
    ap.add_argument("--boundary-layer", default="village_boundary")
    ap.add_argument("--out-name", default="_chain_cell_reasons_v1")
    a = ap.parse_args()
    root = Path(a.stageb_root); d = root / a.run; out = root / a.out_name; prev = root / a.prev_diag
    if out.exists():
        sys.exit(f"stopping: {out} exists (never overwritten)")
    req = [d / "config_stageB.json", d / "inputs_manifest_stageB.csv", d / "road_components.csv", prev / "component_summary.csv", Path(base.__file__)]
    for p in req:
        if not p.exists():
            sys.exit(f"stopping: missing {p}")
    watched = {p: base.sha(p) for p in req}
    cfg = json.loads(req[0].read_text(encoding="utf-8")); rc = cfg.get("resolved_constraints", {})
    mf = pd.read_csv(req[1]).set_index("role")
    paths = {r: Path(mf.loc[r, "path"]) for r in ("cost", "worldcover", "roads") if r in mf.index}
    if len(paths) < 3:
        sys.exit("stopping: manifest roles cost/worldcover/roads missing")
    blocked_p, slope_p, slope_lim, water_c = rc.get("prohibited_raster"), rc.get("slope_raster"), rc.get("slope_limit_deg"), rc.get("water_class", 80)
    if not blocked_p or not slope_p or slope_lim is None:
        sys.exit("stopping: config lacks prohibited_raster / slope_raster / slope_limit_deg")
    bpath = Path(mf.loc["boundary", "path"]) if "boundary" in mf.index else paths["cost"].parent.parent / "study_area" / "damarakunta_boundary.gpkg"
    for p in list(paths.values()) + [Path(blocked_p), Path(slope_p), bpath]:
        if not p.exists():
            sys.exit(f"stopping: missing input {p}")
        watched[p] = base.sha(p)
    al = paths["cost"].parent
    opt = {k: al / f for k, f in (("dem30", "damarakunta_dem_30m.tif"), ("slope30", "damarakunta_slope_30m.tif")) if (al / f).exists()}
    for p in opt.values():
        watched[p] = base.sha(p)
    hash_ok = {r: watched[paths[r]] == mf.loc[r, "sha256"] for r in paths}

    cost, T, crs = base.read(paths["cost"])
    if crs is None or crs.to_epsg() != 32644:
        sys.exit(f"stopping: cost CRS {crs}")
    H, W = cost.shape
    w, Tw, cw = base.read(paths["worldcover"]); pro, Tp, cp = base.read(Path(blocked_p)); slo, Ts, cs_ = base.read(Path(slope_p))
    for nm, (arr, Ta, ca) in dict(worldcover=(w, Tw, cw), prohibited=(pro, Tp, cp), slope=(slo, Ts, cs_)).items():
        if not base.same_grid(T, crs, cost.shape, Ta, ca, arr.shape):
            sys.exit(f"stopping: {nm} not on the cost grid")
    ok = np.isfinite(cost) & (cost > 0)
    passable = ok & ~((w == water_c) | (np.nan_to_num(pro, nan=0) > 0) | (np.nan_to_num(slo, nan=0) > slope_lim))
    import pyogrio
    lays = [x[0] for x in pyogrio.list_layers(bpath)]
    lay = a.boundary_layer if a.boundary_layer in lays else (lays[0] if len(lays) == 1 else None)
    if lay is None:
        sys.exit(f"stopping: boundary layer not in {lays}")
    poly = gpd.read_file(bpath, layer=lay).to_crs(CRS).geometry.union_all(); bline = poly.boundary
    roads = gpd.read_file(paths["roads"]).to_crs(CRS); roads = roads[roads.geometry.notna() & ~roads.geometry.is_empty].reset_index(drop=True)
    idcol = next((c for c in roads.columns if c.lower() in ("objectid", "fid", "id", "feature_id")), None)
    roads["fid"] = roads[idcol].astype(str) if idcol else roads.index.astype(str)
    rr = rasterize([(g, 1) for g in roads.geometry], out_shape=(H, W), transform=T, fill=0, all_touched=True, dtype="uint8").astype(bool)
    lab, sizes = base.label_components(rr & passable)
    rec = list(pd.read_csv(req[2]).sort_values("component_id").n_cells.astype(int))
    summ = pd.read_csv(prev / "component_summary.csv").set_index("component")
    chains = {k: base.min_block_chain(rr, passable, lab, [(r, c) for r, c in zip(*np.nonzero(lab == k))]) for k in COMPS}
    gate = [("component sizes equal road_components.csv", str(sizes), str(rec), sizes == rec), ("input hashes equal manifest", str(hash_ok), "manifest", all(hash_ok.values()))]
    for k in COMPS:
        ch = chains[k]; imp = sum(1 for p in ch if not passable[p])
        gate.append((f"component {k} chain cells / impassable equal previous component_summary.csv", f"{len(ch)}/{imp}", f"{int(summ.loc[k,'chain_cells'])}/{int(summ.loc[k,'chain_impassable'])}",
                     len(ch) == int(summ.loc[k, 'chain_cells']) and imp == int(summ.loc[k, 'chain_impassable'])))
    V = pd.DataFrame(gate, columns=["check", "rebuilt", "expected", "ok"])
    if not V.ok.all():
        print(V.to_string(index=False)); sys.exit("stopping: validation gate FAILED; nothing written")

    # per-part cover map (cell -> feature ids)
    cover = {}
    for _, row in roads.iterrows():
        for part in shapely.get_parts(row.geometry):
            if part.geom_type != "LineString" or part.length == 0:
                continue
            m = rasterize([(part, 1)], out_shape=(H, W), transform=T, fill=0, all_touched=True, dtype="uint8").astype(bool)
            for r, c in np.argwhere(m):
                cover.setdefault((int(r), int(c)), set()).add(row.fid)
    dem = sl30 = None
    for nm in ("dem30", "slope30"):
        if nm in opt:
            arr, Ta, ca = base.read(opt[nm])
            if ca is not None and ca.to_epsg() == 32644:
                if nm == "dem30": dem = (arr, Ta)
                else: sl30 = (arr, Ta)

    def obs30(pack, x, y):
        if pack is None:
            return "", ""
        arr, Ta = pack; col, row = ~Ta * (x, y); r, c = int(np.floor(row)), int(np.floor(col))
        if not (0 <= r < arr.shape[0] and 0 <= c < arr.shape[1]):
            return "off_extent", ""
        win = arr[max(r - 1, 0):r + 2, max(c - 1, 0):c + 2]
        return bool(np.isfinite(arr[r, c])), int((~np.isfinite(win)).sum())

    rows = []
    for k in COMPS:
        for i, (r, c) in enumerate(chains[k]):
            x, y = T * (c + 0.5, r + 0.5); pt = Point(x, y); ins = bool(poly.covers(pt)); dist = float(pt.distance(bline))
            lb = int(lab[r, c]); pas = bool(passable[r, c])
            wcv, slv, prv = w[r, c], slo[r, c], pro[r, c]
            if pas:
                role = "start_component_cell" if lb == k else ("main_component_cell" if lb == 1 else f"passable_cell_of_component_{lb}")
                reason, status = "", "passable"
            else:
                role = "impassable"
                flags = []
                if not np.isfinite(wcv): flags.append("worldcover_nodata")
                elif wcv == water_c: flags.append("worldcover_water")
                elif wcv not in LAND: flags.append("worldcover_class_not_costed")
                if not np.isfinite(slv): flags.append("slope_nodata")
                elif slv > slope_lim: flags.append("slope_above_limit")
                dv, dn = obs30(dem, x, y)
                if not ins:
                    rule_ok = (not np.isfinite(wcv)) and (not np.isfinite(slv)) and prv == 1 and not ok[r, c]
                    reason = "centre_outside_polygon (WorldCover=0 and slope=nodata by align_damarakunta_terrain.py rule)"
                    status = "OBSERVED_RULE_CONSISTENT" if rule_ok else "UNRESOLVED_outside_but_values_differ_from_rule"
                else:
                    reason = "inside_polygon: " + ("+".join(flags) if flags else "no_flag_observed")
                    if not flags:
                        status = "UNRESOLVED_no_flag_observed"
                    elif flags == ["worldcover_water"] or flags == ["worldcover_class_not_costed"] or flags == ["slope_above_limit"]:
                        status = "OBSERVED_direct_value"
                    elif "slope_nodata" in flags and dv is True:
                        status = "OBSERVED_flag_cause_of_nodata_UNRESOLVED(dem30 centre cell is valid)"
                    elif "slope_nodata" in flags:
                        status = "OBSERVED_flag_dem30_centre_cell_masked" if dv is False else "OBSERVED_flag_cause_of_nodata_UNRESOLVED(dem30 not read)"
                    else:
                        status = "OBSERVED_flag_cause_of_nodata_UNRESOLVED(source nodata/clip not examined)"
            dv, dn = obs30(dem, x, y); sv, sn = obs30(sl30, x, y)
            rows.append(dict(chain_component=k, chain_order=i, row=int(r), col=int(c), x=round(x, 2), y=round(y, 2), role=role, cell_component=lb, passable=pas,
                             covering_feature_ids=";".join(sorted(cover.get((int(r), int(c)), []))), centre_in_polygon=ins, signed_dist_to_boundary_m=round(dist if ins else -dist, 2),
                             cost_valid=bool(ok[r, c]), prohibited_value=prv, worldcover=wcv, slope=slv, dem30_centre_valid=dv, dem30_3x3_invalid_cells=dn, slope30_centre_valid=sv,
                             invalid_reason=reason, reason_status=status))
    C = pd.DataFrame(rows)
    I = C[~C.passable]
    S = (I.groupby(["chain_component", "centre_in_polygon", "invalid_reason", "reason_status"]).size().rename("n_cells").reset_index())
    Feat = (C[~C.passable].assign(f=lambda t: t.covering_feature_ids.replace("", "none")).groupby(["chain_component", "f"]).size().rename("n_impassable_cells").reset_index().rename(columns={"f": "covering_feature_ids"}))
    F = []

    def add(i, cl, o, v=""):
        assert cl in ("VERIFIED_FACT", "HYPOTHESIS", "UNRESOLVED")
        F.append(dict(finding_id=i, classification=cl, observation=o, value=v))
    add("K0", "VERIFIED_FACT", "gate passed: component sizes, input hashes, and chain length/impassable counts for C2, C5, C6, C10, C11, C12 equal the previous component_summary.csv", "")
    for k in COMPS:
        t = C[(C.chain_component == k) & ~C.passable]
        parts = []
        for (ins, rs, st), g in t.groupby(["centre_in_polygon", "invalid_reason", "reason_status"]):
            parts.append(f"{len(g)} cell(s) {'inside' if ins else 'outside'}: {rs} [{st}]")
        fe = sorted({f for s_ in t.covering_feature_ids for f in s_.split(";") if f})
        nocov = int((t.covering_feature_ids == "").sum())
        add(f"K{k}", "VERIFIED_FACT", f"C{k} chain: {len(t)} impassable cells; " + " | ".join(parts) + f"; features covering the impassable cells: {fe}; impassable cells covered by no feature: {nocov}", len(t))
    unres = I[I.reason_status.str.contains("UNRESOLVED")]
    add("K98", "UNRESOLVED" if len(unres) else "VERIFIED_FACT", f"{len(unres)} of {len(I)} impassable chain cell-rows have a flag whose underlying cause (why WorldCover/slope is nodata at an inside cell) is not determined by these files; this applies only to rows whose reason_status contains UNRESOLVED", len(unres))
    add("U1", "UNRESOLVED", "no claim is made that any cell should be passable, that any source line is a real or usable road, or that the boundary is authoritative/current; rows repeat across chains when a chain passes through another component (e.g. C6 cells in C10's chain), so do not sum rows across chain_component.", "")
    Fd = pd.DataFrame(F)
    out.mkdir(parents=True)
    V.to_csv(out / "validation_gate.csv", index=False); C.to_csv(out / "chain_cells.csv", index=False); S.to_csv(out / "chain_reason_summary.csv", index=False)
    Feat.to_csv(out / "chain_impassable_by_feature.csv", index=False); Fd.to_csv(out / "chain_cell_findings.csv", index=False)
    pd.DataFrame([("script", Path(__file__).name, base.sha(Path(__file__))), ("run", datetime.datetime.now().isoformat(timespec="seconds"), "")] + [(f"input:{p}", "", h) for p, h in watched.items()],
                 columns=["item", "value", "sha256"]).to_csv(out / "inputs_and_method.csv", index=False)
    changed = [str(p) for p, h in watched.items() if base.sha(p) != h]
    pd.DataFrame([dict(check="inputs unchanged (sha256 before/after)", status="FAIL" if changed else "PASS", detail=f"{len(watched)} files")]).to_csv(out / "readonly_proof.csv", index=False)
    print(V.to_string(index=False)); print()
    for _, r in Fd.iterrows():
        print(f"[{r.classification}] {r.finding_id}: {r.observation}")
    print("\nfeature table:"); print(Feat.to_string(index=False))
    print("\ninputs unchanged:", not changed, f"({len(watched)} files hashed)"); print("output:", out)
    sys.exit(1 if changed else 0)


if __name__ == "__main__":
    main()
