#!/usr/bin/env python
"""audit_phaseB_damarakunta.py - READ-ONLY evidence audits for the Damarakunta first-village case study.

Nothing in the project is modified. All output goes to a NEW folder:
    <village>/results/audit_phaseB/<tag>/        (refuses to reuse an existing folder)

Audits (choose with --only, default all):
  b1  C12: slope at the target cell and along the C12 route of the no-slope-limit run, plus a slope check of every route
  b2  C13: decomposition of the 'prohibited' mask by cause, and the cell/boundary status of all 15 targets
  b3  165 inside_village polygons vs 163 access-analysis polygons
  b4  road cells the planner drops as impassable: causes, location, effect on target-to-road distance

What it does NOT do: it does not change any planner parameter, rerun the planner, or decide whether a
constraint is physically real. Where a cause cannot be established from the files, the output says UNKNOWN.

Run from the project root:
    .venv\\Scripts\\python.exe scripts\\audit_phaseB_damarakunta.py
"""
import argparse
import datetime as dt
import hashlib
import json
import math
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.features import geometry_mask, rasterize
from scipy import ndimage as ndi
from shapely.geometry import Point

CRS = "EPSG:32644"
LAND_CLASSES = (10, 20, 30, 40, 50, 60)  # classes that create_damarakunta_cost_surface.py leaves unblocked


# ------------------------------------------------------------------ small helpers
def sha256(p, chunk=1 << 22):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(chunk), b""):
            h.update(b)
    return h.hexdigest()


def layers_of(p):
    try:
        import pyogrio
        return [r[0] for r in pyogrio.list_layers(str(p))]
    except Exception:
        import fiona
        return list(fiona.listlayers(str(p)))


def read_layer(p, layer=None):
    names = layers_of(p)
    if layer is None or layer not in names:
        layer = names[0]
    return gpd.read_file(p, layer=layer).to_crs(CRS), layer


def load_raster(p):
    with rasterio.open(p) as src:
        raw = src.read(1)
        nd = src.nodata
        arr = raw.astype("float64")
        if nd is not None:
            arr[raw == nd] = np.nan
        return dict(raw=raw, arr=arr, T=src.transform, crs=src.crs, nodata=nd, shape=raw.shape, path=str(p))


def rc_of(T, x, y):
    return int(math.floor((y - T.f) / T.e)), int(math.floor((x - T.c) / T.a))


def val_at(r, row, col):
    if 0 <= row < r["shape"][0] and 0 <= col < r["shape"][1]:
        return float(r["arr"][row, col])
    return float("nan")


def find_rows(gdf, tid):
    for col in ("target", "id", "target_id"):
        if col in gdf.columns:
            m = gdf[col].astype(str) == str(tid)
            if m.any():
                return gdf[m], col
    return gdf.iloc[0:0], None


def line_parts(g):
    if g is None or g.is_empty:
        return []
    if g.geom_type == "LineString":
        return [g]
    if hasattr(g, "geoms"):
        return [p for p in g.geoms if p.geom_type == "LineString"]
    return []


def sample_line(g, step):
    pts = []
    for part in line_parts(g):
        n = max(int(math.ceil(part.length / step)), 1)
        for i in range(n + 1):
            p = part.interpolate(min(i * step, part.length))
            pts.append((p.x, p.y))
    return pts


def jdefault(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, Path):
        return str(o)
    return str(o)


def clean(o):
    """replace NaN/inf by None so the JSON files are valid JSON"""
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, (float, np.floating)):
        return None if not np.isfinite(o) else float(o)
    return o


class Out:
    def __init__(self, folder):
        self.f = folder
        self.lines = []

    def log(self, s=""):
        print(s, flush=True)
        self.lines.append(str(s))

    def json(self, name, obj):
        (self.f / name).write_text(json.dumps(clean(obj), indent=2, default=jdefault), encoding="utf-8")

    def csv(self, name, df):
        df.to_csv(self.f / name, index=False)


# ------------------------------------------------------------------ context
class Ctx:
    pass


def build_ctx(a):
    c = Ctx()
    c.a = a
    root = Path(a.root).resolve()
    vil = (root / a.village) if not Path(a.village).is_absolute() else Path(a.village)
    c.root, c.vil = root, vil
    al = vil / "aligned"
    c.p = dict(
        cost=al / "damarakunta_cost_surface_10m.tif",
        proh=al / "damarakunta_prohibited_mask_10m.tif",
        wc=al / "damarakunta_worldcover_10m.tif",
        slope=al / "damarakunta_slope_10m.tif",
        boundary=vil / "study_area" / "damarakunta_boundary.gpkg",
        roads=vil / "reference" / "tgrac_road_network.gpkg",
        v8=vil / "results" / "v8_instances" / "buildings_v8_full.gpkg",
        access=vil / "results" / "v8_instances" / "access" / "access_assessment.gpkg",
    )
    c.runs_root = Path(a.runs_root) if a.runs_root else vil / "results" / "planning_experiments" / "network_v2"
    c.ref_gpkg = c.runs_root / a.ref_run / "network_v2.gpkg"
    c.soft_gpkg = c.runs_root / a.soft_run / "network_v2.gpkg"
    return c


def need(paths):
    miss = [str(p) for p in paths if not Path(p).exists()]
    return miss


# ------------------------------------------------------------------ B1
def b1(c, o):
    a = c.a
    o.log("\n=== B1: C12 slope audit ===")
    miss = need([c.p["slope"], c.p["cost"], c.p["wc"], c.ref_gpkg])
    if miss:
        o.log("SKIPPED, missing: " + "; ".join(miss))
        return dict(status="SKIPPED", missing=miss)
    slope, cost, wc = load_raster(c.p["slope"]), load_raster(c.p["cost"]), load_raster(c.p["wc"])
    lim = a.slope_limit
    valid_cost = np.isfinite(cost["arr"]) & (cost["arr"] > 0)
    sl = slope["arr"]
    over = np.isfinite(sl) & (sl > lim)
    res = dict(status="DONE", slope_limit_deg=lim, grid_shape=list(slope["shape"]),
               cells_slope_over_limit=int(over.sum()), cells_over_limit_with_valid_cost=int((over & valid_cost).sum()),
               valid_cost_cells=int(valid_cost.sum()),
               note_dem="Slope is derived from a 30 m DEM (Sobel on 30 m cells, bilinear to 10 m) in align_damarakunta_terrain.py; "
                       "the DEM vertical error was not quantified here, so an exceedance of a few tenths of a degree is not resolvable.")
    tg, _ = read_layer(c.ref_gpkg, "targets")
    rows, col = find_rows(tg, a.c12)
    if rows.empty:
        res["target_cell"] = "target not found in targets layer"
    else:
        g = rows.iloc[0].geometry
        pt = g if g.geom_type == "Point" else g.representative_point()
        r0, c0 = rc_of(slope["T"], pt.x, pt.y)
        win = []
        for dr in range(-2, 3):
            win.append([None if not np.isfinite(val_at(slope, r0 + dr, c0 + dc)) else round(val_at(slope, r0 + dr, c0 + dc), 2)
                        for dc in range(-2, 3)])
        flat = [v for rr in win for v in rr if v is not None]
        res["target_cell"] = dict(x=pt.x, y=pt.y, row=r0, col=c0, slope_deg=val_at(slope, r0, c0), cost=val_at(cost, r0, c0),
                                  worldcover=val_at(wc, r0, c0), window_5x5_slope_deg=win,
                                  window_cells_over_limit=int(sum(v > lim for v in flat)), window_cells=len(flat))
        o.log(f"{a.c12} cell: slope {res['target_cell']['slope_deg']:.3f} deg (limit {lim}); 5x5 window cells over limit: "
              f"{res['target_cell']['window_cells_over_limit']} of {len(flat)}")

    all_rows, c12_rows = [], []
    for tag, gp in (("reference", c.ref_gpkg), ("soft_or_no_slope_run", c.soft_gpkg)):
        if not Path(gp).exists():
            res[tag] = "gpkg missing: " + str(gp)
            o.log(f"[{tag}] gpkg missing")
            continue
        names = layers_of(gp)
        lay = next((n for n in ("routes_network_aware", "routes_independent") if n in names), None)
        if lay is None:
            res[tag] = "no route layer"
            continue
        rt = gpd.read_file(gp, layer=lay).to_crs(CRS)
        tcol = next((x for x in ("target", "id", "target_id") if x in rt.columns), None)
        for _, rw in rt.iterrows():
            tid = str(rw[tcol]) if tcol else str(_)
            pts = sample_line(rw.geometry, a.sample_m)
            if not pts:
                continue
            sv = np.array([val_at(slope, *rc_of(slope["T"], x, y)) for x, y in pts])
            wv = np.array([val_at(wc, *rc_of(wc["T"], x, y)) for x, y in pts])
            ok = np.isfinite(sv)
            d = dict(run=tag, layer=lay, target=tid, length_m=round(float(rw.geometry.length), 1), samples=len(pts),
                     samples_slope_nodata=int((~ok).sum()), slope_max=float(np.nanmax(sv)) if ok.any() else np.nan,
                     slope_p95=float(np.nanpercentile(sv[ok], 95)) if ok.any() else np.nan,
                     share_samples_over_limit=float((sv[ok] > lim).mean()) if ok.any() else np.nan,
                     approx_len_over_limit_m=round(float((sv[ok] > lim).mean() * rw.geometry.length), 1) if ok.any() else np.nan,
                     worldcover_classes=json.dumps({int(k): int(v) for k, v in Counter(wv[np.isfinite(wv)].astype(int)).items()}))
            all_rows.append(d)
            if tid == a.c12:
                c12_rows.append(d)
    df = pd.DataFrame(all_rows)
    o.csv("b1_route_slope_all_routes.csv", df)
    res["c12_routes"] = c12_rows
    if len(df):
        for tag, sub in df.groupby("run"):
            res.setdefault("per_run_summary", {})[tag] = dict(
                routes=int(len(sub)), routes_with_any_sample_over_limit=int((sub.share_samples_over_limit > 0).sum()),
                max_slope_over_all_routes=float(sub.slope_max.max()), approx_len_over_limit_m=float(sub.approx_len_over_limit_m.sum()))
            o.log(f"[{tag}] routes {len(sub)}; with samples over {lim} deg: {(sub.share_samples_over_limit > 0).sum()}; "
                  f"max slope along any route {sub.slope_max.max():.2f}; approx length over limit {sub.approx_len_over_limit_m.sum():.1f} m")
    if c12_rows:
        for d in c12_rows:
            o.log(f"C12 route in [{d['run']}]: {d['length_m']} m, max slope {d['slope_max']:.2f}, "
                  f"approx {d['approx_len_over_limit_m']} m above {lim} deg")
    else:
        o.log("No C12 route found in either run's route layer.")
    return res


# ------------------------------------------------------------------ B2
def mask_causes(c):
    cost, proh, wc, slope = (load_raster(c.p[k]) for k in ("cost", "proh", "wc", "slope"))
    bnd, _ = read_layer(c.p["boundary"])
    geom = bnd.geometry.union_all()
    inside = geometry_mask([geom], out_shape=cost["shape"], transform=cost["T"], invert=True)
    blocked = np.nan_to_num(proh["arr"], nan=0) > 0
    wcr = wc["raw"].astype(int)
    slope_bad = ~np.isfinite(slope["arr"]) | (slope["arr"] < 0) | (slope["arr"] > 90)
    code = np.zeros(cost["shape"], np.uint8)
    # priority order mirrors how the rasters were built: boundary clip first, then land class, then slope validity
    code[blocked & ~inside] = 1
    code[blocked & inside & (wcr == c.a.water) & (code == 0)] = 2
    code[blocked & inside & (wcr == 0) & (code == 0)] = 3
    code[blocked & inside & ~np.isin(wcr, LAND_CLASSES) & (code == 0)] = 4
    code[blocked & inside & slope_bad & (code == 0)] = 5
    code[blocked & (code == 0)] = 6
    return dict(cost=cost, proh=proh, wc=wc, slope=slope, geom=geom, inside=inside, blocked=blocked, code=code)


CAUSE = {0: "not blocked", 1: "outside village boundary (WorldCover and slope were set to nodata there)",
         2: "inside boundary, WorldCover water (80)", 3: "inside boundary, WorldCover nodata (0)",
         4: "inside boundary, WorldCover class other than 10-60 and 80", 5: "inside boundary, land class but slope invalid",
         6: "blocked but NOT explained by the rules above (UNKNOWN)"}


def b2(c, o):
    a = c.a
    o.log("\n=== B2: C13 / prohibited-mask audit ===")
    miss = need([c.p[k] for k in ("cost", "proh", "wc", "slope", "boundary")] + [c.ref_gpkg])
    if miss:
        o.log("SKIPPED, missing: " + "; ".join(miss))
        return dict(status="SKIPPED", missing=miss)
    m = mask_causes(c)
    n = m["code"].size
    res = dict(status="DONE", grid_cells=int(n), blocked_cells=int(m["blocked"].sum()),
               rule="create_damarakunta_cost_surface.py sets blocked=1 everywhere except cells whose WorldCover class is 10,20,30,40,50 or 60 "
                    "AND whose slope is valid. So 'prohibited' means 'not usable land with a valid slope'; it is not a legal or protected-area layer.")
    res["blocked_by_cause"] = {CAUSE[k]: int((m["code"] == k).sum()) for k in range(1, 7)}
    res["unblocked_but_outside_boundary"] = int((~m["blocked"] & ~m["inside"]).sum())
    o.log(f"blocked cells: {res['blocked_cells']} of {n} ({res['blocked_cells'] / n:.1%})")
    for k, v in res["blocked_by_cause"].items():
        o.log(f"  {v:>8}  {k}")

    cost, wc, slope = m["cost"], m["wc"], m["slope"]
    valid_cost = np.isfinite(cost["arr"]) & (cost["arr"] > 0)
    passable = valid_cost & ~(wc["raw"].astype(int) == a.water) & ~m["blocked"] & ~(np.isfinite(slope["arr"]) & (slope["arr"] > a.slope_limit))
    tg, _ = read_layer(c.ref_gpkg, "targets")
    tcol = next((x for x in ("id", "target", "target_id") if x in tg.columns), None)
    T = cost["T"]

    def flags_at(r, cc):
        f = []
        if not valid_cost[r, cc]:
            f.append("cost invalid (nodata or <= 0)")
        if wc["raw"][r, cc] == a.water:
            f.append(f"WorldCover water ({a.water})")
        if m["blocked"][r, cc]:
            f.append("prohibited mask > 0")
        if np.isfinite(slope["arr"][r, cc]) and slope["arr"][r, cc] > a.slope_limit:
            f.append(f"slope > {a.slope_limit:g} deg ({slope['arr'][r, cc]:.2f})")
        return f

    rows = []
    for _, rw in tg.iterrows():
        g = rw.geometry
        pt = g if g.geom_type == "Point" else g.representative_point()
        r0, c0 = rc_of(T, pt.x, pt.y)
        inside_grid = 0 <= r0 < cost["shape"][0] and 0 <= c0 < cost["shape"][1]
        cd = int(m["code"][r0, c0]) if inside_grid else -1
        k = 6
        rr, cc = np.nonzero(passable[max(r0 - k, 0): r0 + k + 1, max(c0 - k, 0): c0 + k + 1])
        dmin = float("nan")
        if len(rr):
            xs = T.c + (cc + max(c0 - k, 0) + 0.5) * T.a
            ys = T.f + (rr + max(r0 - k, 0) + 0.5) * T.e
            dmin = float(np.min(np.hypot(xs - pt.x, ys - pt.y)))
        rows.append(dict(target=str(rw[tcol]) if tcol else "?", x=round(pt.x, 2), y=round(pt.y, 2), inside_grid=inside_grid,
                         inside_boundary_polygon=bool(m["geom"].contains(pt)), dist_to_boundary_m=round(float(m["geom"].boundary.distance(pt)), 1),
                         cost=val_at(cost, r0, c0), prohibited=val_at(m["proh"], r0, c0), worldcover=val_at(wc, r0, c0),
                         slope_deg=val_at(slope, r0, c0), cell_passable_in_planner=bool(inside_grid and passable[r0, c0]),
                         planner_exclusion=("; ".join(flags_at(r0, c0)) if inside_grid else "outside grid"),
                         mask_cause=CAUSE.get(cd, "outside grid"), nearest_passable_cell_centre_m=round(dmin, 1) if np.isfinite(dmin) else None))
    tdf = pd.DataFrame(rows)
    o.csv("b2_target_cells.csv", tdf)
    res["targets_not_passable"] = tdf[~tdf.cell_passable_in_planner].to_dict("records")
    o.log("targets whose own cell is not passable: " + (", ".join(tdf[~tdf.cell_passable_in_planner].target) or "none"))
    for _, r in tdf[~tdf.cell_passable_in_planner].iterrows():
        o.log(f"  {r.target}: planner exclusion: {r.planner_exclusion}; prohibited-mask cause: {r.mask_cause}; inside boundary polygon: {r.inside_boundary_polygon}; "
              f"distance to boundary {r.dist_to_boundary_m} m; nearest passable cell centre {r.nearest_passable_cell_centre_m} m")

    # member polygons of the failed clusters
    res["failed_cluster_polygons"] = {}
    if Path(c.p["access"]).exists():
        names = layers_of(c.p["access"])
        if "candidate_access" in names:
            cand = gpd.read_file(c.p["access"], layer="candidate_access").to_crs(CRS)
            for tid in (a.c12, a.c13):
                if "cluster_id" not in cand.columns or not tid.startswith("C"):
                    continue
                mem = cand[cand.cluster_id.astype(str).str.replace(r"\.0$", "", regex=True) == tid[1:]]
                info = []
                for _, p in mem.iterrows():
                    pg = p.geometry
                    cells = rasterize([(pg, 1)], out_shape=cost["shape"], transform=T, fill=0, all_touched=False, dtype="uint8").astype(bool)
                    info.append(dict(cand_id=p.get("cand_id", None), area_m2=round(float(pg.area), 1),
                                     share_area_inside_boundary=round(float(pg.intersection(m["geom"]).area / pg.area), 3) if pg.area > 0 else None,
                                     cells_covered=int(cells.sum()), cells_passable=int((cells & passable).sum()),
                                     representative_point_inside_boundary=bool(m["geom"].contains(pg.representative_point()))))
                res["failed_cluster_polygons"][tid] = info
                o.log(f"{tid} member polygons: {info}")
    res["verdict"] = ("The planner failure is explained by the files: a failed target sits in a cell excluded by the mask. "
                      "Whether that exclusion reflects a real obstacle is UNKNOWN from these files; 'outside boundary' cells carry no land-cover or slope "
                      "data by construction.")
    return res


# ------------------------------------------------------------------ B3
def b3(c, o):
    a = c.a
    o.log("\n=== B3: 165 inside_village vs 163 access polygons ===")
    miss = need([c.p["v8"], c.p["access"]])
    if miss:
        o.log("SKIPPED, missing: " + "; ".join(miss))
        return dict(status="SKIPPED", missing=miss)
    v8, lay = read_layer(c.p["v8"], a.buildings_layer)
    area = v8["area_m2"] if "area_m2" in v8.columns else v8.geometry.area
    ins = v8["inside_village"].astype(str).str.lower().isin(["true", "1"]) if "inside_village" in v8.columns else pd.Series(True, index=v8.index)
    keep = [k.strip() for k in a.quality_keep.split(",")]
    qk = v8["quality_class"].isin(keep) if "quality_class" in v8.columns else pd.Series(True, index=v8.index)
    big = area >= a.min_area
    acc = gpd.read_file(c.p["access"], layer="candidate_access")
    res = dict(status="DONE", v8_layer=lay, v8_total=int(len(v8)), inside_village=int(ins.sum()),
               inside_and_quality_kept=int((ins & qk).sum()), inside_quality_and_area_ge_min=int((ins & qk & big).sum()),
               min_area_m2=a.min_area, quality_keep=keep, access_candidate_access_rows=int(len(acc)))
    o.log(json.dumps({k: v for k, v in res.items() if k != "status"}, default=jdefault))
    res["rule_reproduces_access_count"] = bool(res["inside_quality_and_area_ge_min"] == res["access_candidate_access_rows"])
    idcol = "cand_id" if "cand_id" in v8.columns and "cand_id" in acc.columns else None
    if idcol:
        acc_ids = set(acc[idcol].astype(str))
        dropped = v8[ins & ~v8[idcol].astype(str).isin(acc_ids)].copy()
        dropped["area_m2_used"] = area[dropped.index]
        dropped["quality_kept"] = qk[dropped.index]
        dropped["area_ge_min"] = big[dropped.index]
        keepcols = [x for x in (idcol, "area_m2_used", "quality_class", "quality_kept", "area_ge_min", "status", "est_roofs") if x in dropped.columns]
        o.csv("b3_inside_village_not_in_access.csv", dropped[keepcols])
        extra = acc[~acc[idcol].astype(str).isin(set(v8.loc[ins, idcol].astype(str)))]
        res["inside_village_not_in_access"] = int(len(dropped))
        res["access_not_inside_village"] = int(len(extra))
        res["dropped_detail"] = dropped[keepcols].to_dict("records")
        o.log(f"inside_village but not in access: {len(dropped)}")
        for rec in res["dropped_detail"]:
            o.log("   " + json.dumps(rec, default=jdefault))
        o.log(f"in access but not inside_village: {len(extra)}")
    else:
        res["note"] = "no common cand_id column; only counts could be compared"
    if res["rule_reproduces_access_count"]:
        res["verdict"] = (f"The access count {res['access_candidate_access_rows']} is reproduced by inside_village AND quality in {keep} AND area >= {a.min_area} m2.")
    else:
        res["verdict"] = "The stated filter rule does NOT reproduce the access count: UNRESOLVED; see the CSV of unmatched polygons."
    o.log(res["verdict"])
    return res


# ------------------------------------------------------------------ B4
def b4(c, o):
    a = c.a
    o.log("\n=== B4: dropped road cells ===")
    miss = need([c.p[k] for k in ("cost", "proh", "wc", "slope", "boundary", "roads")] + [c.ref_gpkg])
    if miss:
        o.log("SKIPPED, missing: " + "; ".join(miss))
        return dict(status="SKIPPED", missing=miss)
    m = mask_causes(c)
    cost, wc, slope = m["cost"], m["wc"], m["slope"]
    T, shape = cost["T"], cost["shape"]
    valid_cost = np.isfinite(cost["arr"]) & (cost["arr"] > 0)
    water = wc["raw"].astype(int) == a.water
    steep = np.isfinite(slope["arr"]) & (slope["arr"] > a.slope_limit)
    hard = water | m["blocked"] | steep | ~valid_cost
    passable = ~hard
    roads, _ = read_layer(c.p["roads"])
    roads = roads[roads.geometry.notna() & ~roads.geometry.is_empty].reset_index(drop=True)
    rr = rasterize([(g, 1) for g in roads.geometry], out_shape=shape, transform=T, fill=0, all_touched=True, dtype="uint8").astype(bool)
    drop = rr & ~passable
    res = dict(status="DONE", road_features=int(len(roads)), road_cells=int(rr.sum()), passable=int((rr & passable).sum()),
               dropped_impassable=int(drop.sum()))
    dc = ref_dc = None
    dcp = c.runs_root / a.ref_run / "data_check.json"
    if dcp.exists():
        try:
            ref_dc = json.loads(dcp.read_text(encoding="utf-8")).get("road_cells")
        except Exception:
            ref_dc = None
    res["planner_recorded_road_cells"] = ref_dc
    res["reproduces_planner_counts"] = bool(ref_dc and ref_dc.get("total") == res["road_cells"] and ref_dc.get("dropped_impassable") == res["dropped_impassable"])
    o.log(f"road cells {res['road_cells']}, passable {res['passable']}, dropped {res['dropped_impassable']}; "
          f"planner recorded {ref_dc}; reproduces: {res['reproduces_planner_counts']}")

    # causes (first match): outside boundary, water, prohibited-other, steep, invalid cost
    cause = np.full(shape, "", dtype=object)
    cause[drop & ~m["inside"]] = "outside village boundary"
    cause[drop & (cause == "") & water] = "water (WorldCover 80)"
    cause[drop & (cause == "") & m["blocked"]] = "prohibited mask (non-land class or invalid slope, inside boundary)"
    cause[drop & (cause == "") & steep] = "slope above limit"
    cause[drop & (cause == "") & ~valid_cost] = "invalid cost"
    cause[drop & (cause == "")] = "other (UNKNOWN)"
    res["dropped_by_first_matching_cause"] = dict(Counter(cause[drop].tolist()))
    o.log("dropped by first matching cause: " + json.dumps(res["dropped_by_first_matching_cause"]))

    # per road feature (cells burned in feature order; overlaps are attributed to the later feature, so this is approximate)
    lab = rasterize([(g, i + 1) for i, g in enumerate(roads.geometry)], out_shape=shape, transform=T, fill=0, all_touched=True, dtype="int32")
    namecol = next((x for x in ("name", "road_name", "NAME", "roadname", "Name") if x in roads.columns), None)
    recs = []
    for i in range(len(roads)):
        sel = lab == (i + 1)
        n = int(sel.sum())
        if n == 0:
            continue
        recs.append(dict(feature_index=i, name=str(roads.loc[i, namecol]) if namecol else "", cells_burned=n,
                         dropped=int((sel & drop).sum()), dropped_share=round(float((sel & drop).sum() / n), 3)))
    pf = pd.DataFrame(recs).sort_values("dropped", ascending=False) if recs else pd.DataFrame()
    o.csv("b4_dropped_by_road_feature.csv", pf)
    if len(pf):
        o.log("top road features by dropped cells:\n" + pf.head(8).to_string(index=False))

    # spatial structure of dropped cells and of the passable road network
    st8 = np.ones((3, 3), int)
    dl, nd = ndi.label(drop, structure=st8)
    sizes = np.bincount(dl.ravel())[1:] if nd else np.array([])
    pl, npass = ndi.label(rr & passable, structure=st8)
    psizes = np.bincount(pl.ravel())[1:] if npass else np.array([])
    res["dropped_components"] = dict(n=int(nd), largest=int(sizes.max()) if nd else 0, n_ge_10_cells=int((sizes >= 10).sum()) if nd else 0)
    res["passable_road_components_8conn"] = dict(n=int(npass), largest=int(psizes.max()) if npass else 0,
                                                 sizes_desc=sorted([int(s) for s in psizes], reverse=True)[:10])
    o.log(f"dropped-cell components {res['dropped_components']}; passable-road components {res['passable_road_components_8conn']}")

    # effect on target-to-road distance
    tg, _ = read_layer(c.ref_gpkg, "targets")
    tcol = next((x for x in ("id", "target", "target_id") if x in tg.columns), None)
    rows_, cols_ = np.nonzero(rr)
    xs_all = T.c + (cols_ + 0.5) * T.a
    ys_all = T.f + (rows_ + 0.5) * T.e
    pm = passable[rows_, cols_]
    trows = []
    for _, rw in tg.iterrows():
        g = rw.geometry
        pt = g if g.geom_type == "Point" else g.representative_point()
        d_all = np.hypot(xs_all - pt.x, ys_all - pt.y)
        d_pass = np.where(pm, d_all, np.inf)
        trows.append(dict(target=str(rw[tcol]) if tcol else "?", dist_to_nearest_road_cell_m=round(float(d_all.min()), 1),
                          dist_to_nearest_PASSABLE_road_cell_m=round(float(d_pass.min()), 1),
                          extra_m_because_of_dropped_cells=round(float(d_pass.min() - d_all.min()), 1)))
    td = pd.DataFrame(trows)
    o.csv("b4_target_road_distance.csv", td)
    res["targets_where_nearest_road_cell_is_dropped"] = td[td.extra_m_because_of_dropped_cells > 0.05].to_dict("records")
    o.log(f"targets whose nearest road cell is dropped: {len(res['targets_where_nearest_road_cell_is_dropped'])} of {len(td)}")

    # figure
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(8, 8))
        base = np.where(passable, 0.85, 0.55)
        ax.imshow(base, cmap="gray", vmin=0, vmax=1, extent=(T.c, T.c + shape[1] * T.a, T.f + shape[0] * T.e, T.f))
        rr_i, cc_i = np.nonzero(rr & passable)
        ax.scatter(T.c + (cc_i + .5) * T.a, T.f + (rr_i + .5) * T.e, s=2, c="tab:blue", label="road cells, passable")
        rr_d, cc_d = np.nonzero(drop)
        ax.scatter(T.c + (cc_d + .5) * T.a, T.f + (rr_d + .5) * T.e, s=2, c="tab:red", label="road cells, dropped")
        for _, rw in tg.iterrows():
            g = rw.geometry
            pt = g if g.geom_type == "Point" else g.representative_point()
            ax.plot(pt.x, pt.y, "k^", ms=4)
        bx, by = m["geom"].exterior.xy if m["geom"].geom_type == "Polygon" else (None, None)
        if bx is not None:
            ax.plot(bx, by, "k-", lw=0.8)
        ax.legend(loc="lower left", fontsize=7)
        ax.set_title("Road cells kept and dropped by the planner (grey: darker = excluded cells; triangles: targets)", fontsize=8)
        ax.set_aspect("equal")
        fig.savefig(o.f / "b4_road_cells_map.png", dpi=150, bbox_inches="tight")
        plt.close(fig)
    except Exception as e:
        o.log(f"figure not written: {e}")
    return res


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=".")
    ap.add_argument("--village", default="Siddipet/Damarakunta")
    ap.add_argument("--runs-root", default=None)
    ap.add_argument("--ref-run", default="run7_regress")
    ap.add_argument("--soft-run", default="run6_slope_soft")
    ap.add_argument("--out-root", default=None)
    ap.add_argument("--tag", default=None)
    ap.add_argument("--only", default="b1,b2,b3,b4")
    ap.add_argument("--slope-limit", type=float, default=10.0)
    ap.add_argument("--water", type=int, default=80)
    ap.add_argument("--sample-m", type=float, default=5.0)
    ap.add_argument("--min-area", type=float, default=10.0)
    ap.add_argument("--quality-keep", default="PLAUSIBLE,REVIEW,UNRESOLVED_MERGE")
    ap.add_argument("--buildings-layer", default="buildings")
    ap.add_argument("--c12", default="C12")
    ap.add_argument("--c13", default="C13")
    a = ap.parse_args()
    c = build_ctx(a)
    tag = a.tag or "pb_" + dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_root = Path(a.out_root) if a.out_root else c.vil / "results" / "audit_phaseB"
    folder = out_root / tag
    if folder.exists() and any(folder.iterdir()):
        sys.exit(f"{folder} already exists; choose another --tag (nothing is overwritten)")
    folder.mkdir(parents=True, exist_ok=True)
    o = Out(folder)
    o.log(f"output folder: {folder}\nread-only audit; no existing project file is modified")
    inputs = {}
    for k, p in list(c.p.items()) + [("ref_gpkg", c.ref_gpkg), ("soft_gpkg", c.soft_gpkg)]:
        p = Path(p)
        inputs[k] = dict(path=str(p), exists=p.exists(), sha256=sha256(p) if p.exists() and p.stat().st_size < 600e6 else None)
    summary = dict(created=dt.datetime.now(dt.timezone.utc).isoformat(), args=vars(a), inputs=inputs, audits={})
    fns = dict(b1=b1, b2=b2, b3=b3, b4=b4)
    exit_code = 0
    for k in [x.strip().lower() for x in a.only.split(",") if x.strip()]:
        try:
            summary["audits"][k] = fns[k](c, o)
        except Exception as e:  # keep going; report the failure honestly
            import traceback
            summary["audits"][k] = dict(status="FAILED", error=repr(e), traceback=traceback.format_exc())
            o.log(f"{k.upper()} FAILED: {e!r}")
            exit_code = 1
    o.json("audit_summary.json", summary)
    (folder / "audit_log.txt").write_text("\n".join(o.lines), encoding="utf-8")
    o.log(f"\nwritten: {folder}")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
