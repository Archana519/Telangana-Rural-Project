"""v8: more conservative roof-instance extraction from the EXISTING model outputs (no re-inference).
Writes only to a NEW folder (results\\v8_instances). Does not touch v6/v7 outputs, rasters, checkpoint or references.

What changed vs v7, and why (evidence: the v7 overview and W1_CORE overlay):
  1. NO-DATA FIX. v7 reported ~10 detections on black (zero-pixel) mosaic area. v8 reads the mosaic, builds a
     no-data mask (all bands 0, or the raster's nodata value), and moves instances that are mostly on no-data to
     a separate 'rejected' layer. Instances merely near no-data get NEAR_NODATA.
  2. SPLITTING RULE. v7 split wherever the distance transform had a peak >= 1 m above its surroundings. On the
     smooth blobs the model produces, that cuts blobs arbitrarily. v8 splits only at a real NECK: two adjacent
     pieces are kept apart only if the saddle between them is narrower than --neck-ratio (default 0.65) times
     the inscribed radius of the SMALLER piece (scale-free), and every piece has >= --min-piece-m2.
     Otherwise they are re-merged. An L-shaped or wide irregular roof has no neck and stays one polygon.
  3. UNRESOLVED MERGES ARE FLAGGED, NOT CUT. A polygon much larger than a typical single roof, or large and
     non-compact, gets UNRESOLVED_MERGE and an estimated roof count (EST_ROOFS). Treat these as built-up
     extent, not as individual buildings. The reference roof size is the median of compact single polygons
     in this run (data-derived), not a number I chose.
  4. THRESHOLD DIAGNOSTICS. --diagnose prints how component count/size change with the probability threshold.
     --prob-thr uses prob >= thr as foreground instead of argmax class 2.
  5. Review flags: ISOLATED (no other detection within --isolated-m), LOW_CONF, SMALL, COMPLEX_SHAPE, EDGE_OF_MOSAIC.
  6. quality_class: PLAUSIBLE | REVIEW | UNRESOLVED_MERGE.

LIMITS (read this): the checkpoint is a semantic model. The mask boundary is coarse, so footprints are blob
outlines, not surveyed roof edges, and roofs that touch with no neck cannot be separated by any post-processing.
Nothing here is validated until it is scored against traced windows. No count is a house count.
"""
import argparse, heapq, json, os, sys, time
import numpy as np
import cv2
import rasterio
import geopandas as gpd
import pandas as pd
import shapely
from rasterio.features import shapes
from rasterio.transform import Affine
from rasterio.windows import Window
from shapely.geometry import shape as shp_shape
from shapely.ops import unary_union
from shapely.validation import make_valid

ROOT = r"D:\Telangana_Rural_Project\Siddipet\Damarakunta"
CRS = "EPSG:32644"


# ------------------------------------------------------------------ splitting (neck-ratio rule)
def hmax_markers(dt, h):
    k = np.ones((3, 3), np.uint8)
    dt = dt.astype(np.float32)
    rec = dt - h
    for _ in range(5000):
        nxt = np.minimum(cv2.dilate(rec, k), dt)
        if np.array_equal(nxt, rec):
            break
        rec = nxt
    top = ((dt - rec) >= (h - 1e-4)) & (dt > 0)
    n, lab = cv2.connectedComponents(top.astype(np.uint8), connectivity=8)
    return n - 1, lab


def flood(mask, dt, markers):
    lab = markers.astype(np.int32).copy()
    H, W = mask.shape
    heap, cnt = [], 0
    for y, x in zip(*np.nonzero(markers > 0)):
        heapq.heappush(heap, (-float(dt[y, x]), cnt, int(y), int(x))); cnt += 1
    while heap:
        _, _, y, x = heapq.heappop(heap)
        l = lab[y, x]
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                yy, xx = y + dy, x + dx
                if 0 <= yy < H and 0 <= xx < W and mask[yy, xx] and lab[yy, xx] == 0:
                    lab[yy, xx] = l
                    heapq.heappush(heap, (-float(dt[yy, xx]), cnt, yy, xx)); cnt += 1
    return lab


def necks(lab, dt):
    """{(a,b): saddle height} = highest 'pass' (min dt of two touching pixels) between adjacent pieces."""
    out = {}
    for A, B, da, db in ((lab[:, :-1], lab[:, 1:], dt[:, :-1], dt[:, 1:]),
                         (lab[:-1, :], lab[1:, :], dt[:-1, :], dt[1:, :])):
        m = (A > 0) & (B > 0) & (A != B)
        for a, b, v in zip(A[m], B[m], np.minimum(da, db)[m]):
            k = (int(min(a, b)), int(max(a, b)))
            if v > out.get(k, 0.0):
                out[k] = float(v)
    return out


def split_component(mask, res, smooth_px, seed_h_m, neck_ratio, min_piece_m2, split_min_m2):
    """-> (labels crop 1..n, n, {piece: best retained neck ratio or None})"""
    one = mask.astype(np.int32)
    if mask.sum() * res * res < split_min_m2 or neck_ratio is None:
        return one, 1, {1: None}
    pm = np.pad(mask, 1)
    dt = cv2.distanceTransform(pm.astype(np.uint8), cv2.DIST_L2, 5).astype(np.float32) * res
    if smooth_px > 0:
        kk = int(2 * round(2 * smooth_px) + 1)
        dt = cv2.GaussianBlur(dt, (kk, kk), smooth_px)
    n, mk = hmax_markers(dt, seed_h_m)
    if n < 2:
        return one, 1, {1: None}
    lab = flood(pm, dt, mk)
    while True:
        ids = [i for i in np.unique(lab) if i > 0]
        if len(ids) < 2:
            break
        peaks = {i: float(dt[lab == i].max()) for i in ids}
        areas = {i: float((lab == i).sum()) * res * res for i in ids}
        best = None
        for (a, b), s in necks(lab, dt).items():
            r = s / max(min(peaks[a], peaks[b]), 1e-6)
            small = min(areas[a], areas[b]) < min_piece_m2
            if (r > neck_ratio) or small:
                score = r + (10.0 if small else 0.0)
                if best is None or score > best[0]:
                    best = (score, a, b)
        if best is None:
            break
        lab[lab == best[2]] = best[1]
    ids = [i for i in np.unique(lab) if i > 0]
    remap = np.zeros(lab.max() + 1, np.int32)
    for new, old in enumerate(ids, 1):
        remap[old] = new
    lab = remap[lab][1:-1, 1:-1]
    lab[~mask] = 0
    if len(ids) == 1:
        return one, 1, {1: None}
    peaks = {i + 1: float(dt[1:-1, 1:-1][lab == i + 1].max()) for i in range(len(ids))}
    best_r = {i: None for i in range(1, len(ids) + 1)}
    full = np.pad(lab, 1)
    for (a, b), s in necks(full, dt).items():
        r = round(s / max(min(peaks[a], peaks[b]), 1e-6), 3)
        for p in (a, b):
            best_r[p] = r if best_r[p] is None else max(best_r[p], r)
    return lab, len(ids), best_r


# ------------------------------------------------------------------ helpers
def to_poly(lab_crop, lab_id, tr):
    m = lab_crop == lab_id
    geoms = [shp_shape(g) for g, v in shapes(m.astype(np.uint8), mask=m, transform=tr, connectivity=8) if v == 1]
    if not geoms:
        return None
    g = unary_union(geoms)
    return make_valid(g) if not g.is_valid else g


def nodata_mask(raster_path, block=1024):
    with rasterio.open(raster_path) as src:
        inv = np.zeros((src.height, src.width), bool)
        nd = src.nodata
        bands = list(range(1, min(src.count, 3) + 1))
        for r0 in range(0, src.height, block):
            h = min(block, src.height - r0)
            arr = src.read(bands, window=Window(0, r0, src.width, h))
            m = (arr == 0).all(axis=0)
            if nd is not None:
                m |= (arr == nd).all(axis=0)
            inv[r0:r0 + h] = m
    return inv


def threshold_table(cls, prob, valid, tr, boundary, res, ts):
    rows = []
    for t in ts:
        fg = ((prob >= int(round(t * 255))) if t is not None else (cls == 2)) & valid
        n, cc, st, cen = cv2.connectedComponentsWithStats(fg.astype(np.uint8), connectivity=8)
        a = st[1:, 4] * res * res
        keep = a >= 6.0
        a = a[keep]
        cx = tr.c + tr.a * cen[1:][keep, 0]
        cy = tr.f + tr.e * cen[1:][keep, 1]
        inside = int(shapely.contains_xy(boundary, cx, cy).sum()) if boundary is not None else None
        tot = a.sum() or 1.0
        rows.append(dict(threshold="argmax==2" if t is None else f"prob>={t:.2f}", fg_pixels=int(fg.sum()),
                         components_ge6m2=int(len(a)), inside_village=inside,
                         median_area_m2=round(float(np.median(a)), 1) if len(a) else None,
                         p90_area_m2=round(float(np.percentile(a, 90)), 1) if len(a) else None,
                         share_area_in_comps_gt400=round(float(a[a > 400].sum() / tot), 3)))
    return pd.DataFrame(rows)


def render_overlays(raster, layers, wins, out_dir, invalid, pad_m=15, scale=2):
    os.makedirs(out_dir, exist_ok=True)
    made = []
    col = {"PLAUSIBLE": (60, 200, 60), "REVIEW": (0, 165, 255), "UNRESOLVED_MERGE": (255, 0, 255)}
    with rasterio.open(raster) as src:
        for _, w in wins.iterrows():
            minx, miny, maxx, maxy = w.geometry.buffer(pad_m).bounds
            win = rasterio.windows.from_bounds(minx, miny, maxx, maxy, src.transform).round_offsets().round_lengths()
            win = win.intersection(Window(0, 0, src.width, src.height))
            img = src.read([1, 2, 3], window=win).transpose(1, 2, 0)
            tr = src.window_transform(win)
            base = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)[:, :, ::-1].copy()
            panels = []
            for name, gdf in layers:
                c = base.copy()
                sub = gdf[gdf.intersects(w.geometry.buffer(pad_m))]
                for _, r in sub.iterrows():
                    for poly in getattr(r.geometry, "geoms", [r.geometry]):
                        if poly.is_empty:
                            continue
                        pts = np.array([[(x - tr.c) / tr.a * scale, (y - tr.f) / tr.e * scale]
                                        for x, y in poly.exterior.coords], np.int32)
                        colour = col.get(r.get("quality_class", ""), (0, 0, 255))
                        cv2.polylines(c, [pts], True, colour, 2)
                cv2.rectangle(c, (0, 0), (c.shape[1], 30), (0, 0, 0), -1)
                cv2.putText(c, f"{name}: {len(sub)} polygons", (8, 21), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                panels.append(c)
            p = os.path.join(out_dir, f"{w.window_id}_v6_v7_v8.png")
            cv2.imwrite(p, np.hstack(panels)); made.append(p)
    return made


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tag", default="full")
    ap.add_argument("--pred-dir", default=os.path.join(ROOT, "predictions", "tiled_v1"))
    ap.add_argument("--raster", default=os.path.join(ROOT, "aligned", "damarakunta_esri_highres_mosaic_0p6m.tif"))
    ap.add_argument("--boundary", default=os.path.join(ROOT, "study_area", "damarakunta_boundary.gpkg"))
    ap.add_argument("--windows-gpkg", default=os.path.join(ROOT, "results", "v6_buildings", "reference", "digitize_windows.gpkg"))
    ap.add_argument("--v6", default=os.path.join(ROOT, "results", "v6_buildings", "candidate_buildings_full.gpkg"))
    ap.add_argument("--v7", default=os.path.join(ROOT, "results", "v7_instances", "buildings_v7_full.gpkg"))
    ap.add_argument("--out-dir", default=os.path.join(ROOT, "results", "v8_instances"))
    ap.add_argument("--out-name", default=None, help="file stem; default buildings_v8_<tag>")
    ap.add_argument("--diagnose", action="store_true", help="print threshold diagnostics and exit (writes nothing)")
    ap.add_argument("--prob-thr", type=float, default=None, help="foreground = prob >= thr instead of argmax class 2")
    ap.add_argument("--min-area-m2", type=float, default=6.0)
    ap.add_argument("--small-flag-m2", type=float, default=15.0)
    ap.add_argument("--low-conf", type=float, default=0.5)
    ap.add_argument("--neck-ratio", type=float, default=0.65, help="split only if saddle/smaller-peak <= this; <=0 disables splitting")
    ap.add_argument("--seed-h-m", type=float, default=0.3, help="candidate-marker prominence before neck test")
    ap.add_argument("--smooth-px", type=float, default=1.0)
    ap.add_argument("--split-min-m2", type=float, default=40.0)
    ap.add_argument("--min-piece-m2", type=float, default=12.0)
    ap.add_argument("--unresolved-factor", type=float, default=4.0, help="UNRESOLVED_MERGE if area > factor x reference roof area")
    ap.add_argument("--nodata-dilate-px", type=int, default=7)
    ap.add_argument("--nodata-reject-frac", type=float, default=0.5)
    ap.add_argument("--isolated-m", type=float, default=50.0)
    ap.add_argument("--overwrite", action="store_true")
    ap.add_argument("--no-overlays", action="store_true")
    a = ap.parse_args()

    stem = a.out_name or f"buildings_v8_{a.tag}"
    out_gpkg, out_csv, out_json = [os.path.join(a.out_dir, stem + e) for e in (".gpkg", ".csv", ".json")]
    if not a.diagnose:
        os.makedirs(a.out_dir, exist_ok=True)
        for p in (out_gpkg, out_csv, out_json):
            if os.path.exists(p) and not a.overwrite:
                sys.exit(f"{p} exists; use --overwrite (replaces only this script's own v8 output) or --out-name")
        if a.overwrite and os.path.exists(out_gpkg):
            os.remove(out_gpkg)

    t0 = time.time()
    with rasterio.open(os.path.join(a.pred_dir, f"pred_classes_{a.tag}.tif")) as s:
        cls, tr = s.read(1), s.transform
    with rasterio.open(os.path.join(a.pred_dir, f"building_prob_{a.tag}.tif")) as s:
        prob = s.read(1)
    res = abs(tr.a)
    pix = res * res
    boundary = gpd.read_file(a.boundary).to_crs(CRS).geometry.union_all() if os.path.exists(a.boundary) else None
    print("reading mosaic to build the no-data mask ...")
    inv0 = nodata_mask(a.raster)
    if inv0.shape != cls.shape:
        sys.exit("mosaic and prediction rasters differ in shape")
    k = 2 * a.nodata_dilate_px + 1
    inv = cv2.dilate(inv0.astype(np.uint8), np.ones((k, k), np.uint8)).astype(bool) if a.nodata_dilate_px > 0 else inv0
    print(f"no-data pixels: {int(inv0.sum())} ({100 * inv0.mean():.3f}%) | building-class pixels on no-data: {int(((cls == 2) & inv0).sum())}")
    pb = prob[cls == 2].astype(np.float32) / 255.0
    print("building probability inside class-2 pixels p10/p50/p90:", [round(float(x), 3) for x in np.percentile(pb, [10, 50, 90])])

    tt = threshold_table(cls, prob, ~inv0, tr, boundary, res, [None, 0.40, 0.50, 0.60, 0.70, 0.80])
    print("\nTHRESHOLD DIAGNOSTICS (no-data excluded; components >= 6 m2):")
    print(tt.to_string(index=False))
    print("Reading: if components_ge6m2 rises and p90/share_area_in_comps_gt400 falls as the threshold rises, high "
          "thresholds are separating blobs; whether that helps is decided only by scoring against traced windows.")
    if a.diagnose:
        return

    fg = (prob >= int(round(a.prob_thr * 255))) if a.prob_thr is not None else (cls == 2)   # no-data kept here on purpose: such blobs are audited in the 'rejected' layer
    n, cc, stats, _ = cv2.connectedComponentsWithStats(fg.astype(np.uint8), connectivity=8)
    print(f"\nforeground: {'prob>=%.2f' % a.prob_thr if a.prob_thr is not None else 'argmax class 2'} | components: {n - 1}")
    H, W = cls.shape
    ratio = a.neck_ratio if a.neck_ratio > 0 else None
    sens = {r: [0, 0] for r in (0.4, 0.5, 0.65, 0.8, 1.0, "none")}
    rows, geoms, crow, cgeoms = [], [], [], []
    for cid in range(1, n):
        x, y, w, hh, ar = [int(v) for v in stats[cid]]
        if ar * pix < a.min_area_m2:
            continue
        x0, y0, x1, y1 = max(x - 1, 0), max(y - 1, 0), min(x + w + 1, W), min(y + hh + 1, H)
        mask = cc[y0:y1, x0:x1] == cid
        ctr = Affine(tr.a, tr.b, tr.c + tr.a * x0 + tr.b * y0, tr.d, tr.e, tr.f + tr.d * x0 + tr.e * y0)
        pc = prob[y0:y1, x0:x1].astype(np.float32) / 255.0
        ic = inv[y0:y1, x0:x1]
        for r in sens:
            _, ns, _ = split_component(mask, res, a.smooth_px, a.seed_h_m, None if r == "none" else r, a.min_piece_m2, a.split_min_m2)
            sens[r][0] += ns; sens[r][1] += int(ns > 1)
        lab, npc, nr = split_component(mask, res, a.smooth_px, a.seed_h_m, ratio, a.min_piece_m2, a.split_min_m2)
        cgeoms.append(to_poly(mask.astype(np.int32), 1, ctr))
        crow.append(dict(comp_id=cid, area_m2=round(ar * pix, 2), n_pieces=npc, mean_prob=round(float(pc[mask].mean()), 4)))
        for pid in range(1, npc + 1):
            pm = lab == pid
            if pm.sum() * pix < a.min_area_m2:
                continue
            g = to_poly(lab, pid, ctr)
            if g is None or g.is_empty:
                continue
            area = g.area
            per = g.length or 1.0
            edge = (x0 == 0 and pm[:, 0].any()) or (y0 == 0 and pm[0, :].any()) or \
                   (x1 == W and pm[:, -1].any()) or (y1 == H and pm[-1, :].any())
            rows.append(dict(comp_id=cid, piece=pid, n_in_comp=npc,
                             split_method="dt_neck_ratio" if npc > 1 else "none",
                             neck_ratio=nr.get(pid), area_m2=round(area, 2), perimeter_m=round(per, 2),
                             solidity=round(area / (g.convex_hull.area or 1.0), 3),
                             compactness=round(4 * np.pi * area / (per * per), 3),
                             mean_prob=round(float(pc[pm].mean()), 4), max_prob=round(float(pc[pm].max()), 4),
                             nodata_frac=round(float(ic[pm].mean()), 3), edge_mosaic=bool(edge)))
            geoms.append(g)

    df = gpd.GeoDataFrame(rows, geometry=geoms, crs=CRS)
    comps = gpd.GeoDataFrame(crow, geometry=cgeoms, crs=CRS)
    rej = df[df.nodata_frac >= a.nodata_reject_frac].copy()
    rej["reject_reason"] = "MOSTLY_ON_NODATA"
    df = df[df.nodata_frac < a.nodata_reject_frac].reset_index(drop=True)

    single = df[(df.n_in_comp == 1) & (df.solidity >= 0.85) & df.area_m2.between(10, 200)]
    ref_roof = float(single.area_m2.median()) if len(single) >= 10 else 60.0
    df["est_roofs"] = np.maximum(1, np.round(df.area_m2 / ref_roof)).astype(int)
    if len(df) > 1:
        gl = list(df.geometry)
        idx, dist = shapely.STRtree(gl).query_nearest(gl, return_distance=True, exclusive=True, all_matches=False)
        nn = np.full(len(df), np.inf); nn[idx[0]] = dist
    else:
        nn = np.full(len(df), np.inf)
    df["nearest_m"] = np.round(nn, 1)
    flags, qual = [], []
    for _, r in df.iterrows():
        f = []
        if r.n_in_comp > 1: f.append("SPLIT_AT_NECK")
        if r.area_m2 < a.small_flag_m2: f.append("SMALL")
        if r.area_m2 > a.unresolved_factor * ref_roof or (r.solidity < 0.75 and r.area_m2 > 2 * ref_roof):
            f.append("UNRESOLVED_MERGE")
        elif r.solidity < 0.75: f.append("COMPLEX_SHAPE")
        if r.mean_prob < a.low_conf: f.append("LOW_CONF")
        if r.nearest_m > a.isolated_m: f.append("ISOLATED")
        if r.nodata_frac > 0: f.append("NEAR_NODATA")
        if r.edge_mosaic: f.append("EDGE_OF_MOSAIC")
        flags.append(";".join(f))
        qual.append("UNRESOLVED_MERGE" if "UNRESOLVED_MERGE" in f else
                    "REVIEW" if set(f) & {"SMALL", "COMPLEX_SHAPE", "LOW_CONF", "ISOLATED", "NEAR_NODATA", "EDGE_OF_MOSAIC"} else "PLAUSIBLE")
    df["flags"], df["quality_class"] = flags, qual
    df["inside_village"] = None if boundary is None else shapely.contains_xy(boundary, df.geometry.representative_point().x.values,
                                                                              df.geometry.representative_point().y.values)
    df.insert(0, "cand_id", np.arange(1, len(df) + 1))
    df.insert(1, "bld_id", [f"B8_{i:05d}" for i in df.cand_id])
    df["status"] = "AUTO_DETECTED_UNVERIFIED"

    df.to_file(out_gpkg, layer="buildings", driver="GPKG")
    comps.to_file(out_gpkg, layer="components", driver="GPKG")
    if len(rej):
        rej.to_file(out_gpkg, layer="rejected", driver="GPKG")
    df.drop(columns="geometry").to_csv(out_csv, index=False)

    def stats_of(g, inside_col=None):
        d = {"n": int(len(g)), "area_p10_50_90_99": [round(float(x), 1) for x in np.percentile(g.area_m2, [10, 50, 90, 99])] if len(g) else None}
        return d
    comp_inside = None if boundary is None else int(shapely.contains_xy(boundary, comps.geometry.representative_point().x.values,
                                                                        comps.geometry.representative_point().y.values).sum())
    summary = dict(params=vars(a), reference_roof_area_m2=round(ref_roof, 1), components=int(len(comps)),
                   components_inside_village=comp_inside, components_split=int((comps.n_pieces > 1).sum()),
                   instances=int(len(df)), instances_inside_village=(None if boundary is None else int(df.inside_village.sum())),
                   rejected_nodata=int(len(rej)), quality_class=df.quality_class.value_counts().to_dict(),
                   flag_counts={f: int(df["flags"].str.contains(f).sum()) for f in
                                ["SPLIT_AT_NECK", "SMALL", "UNRESOLVED_MERGE", "COMPLEX_SHAPE", "LOW_CONF", "ISOLATED", "NEAR_NODATA", "EDGE_OF_MOSAIC"]},
                   area_m2_percentiles_10_50_90_99=stats_of(df)["area_p10_50_90_99"],
                   neck_ratio_sensitivity={str(k): dict(instances=v[0], components_split=v[1]) for k, v in sens.items()},
                   threshold_diagnostics=tt.to_dict("records"), seconds=round(time.time() - t0, 1),
                   note="UNVERIFIED model predictions; not a house count; accuracy unmeasured until scored against traced windows")
    json.dump(summary, open(out_json, "w", encoding="utf-8"), indent=2, default=str)

    print(f"\nreference single-roof area: {ref_roof:.1f} m2 ({'median of ' + str(len(single)) + ' compact single polygons' if len(single) >= 10 else 'FALLBACK 60 m2: fewer than 10 compact singles found'})")
    print(f"instances: {len(df)} from {len(comps)} components ({summary['components_split']} split) | inside village: {summary['instances_inside_village']}")
    print("rejected (mostly on no-data):", len(rej))
    print("quality_class:", summary["quality_class"])
    print("flags:", summary["flag_counts"])
    print("area m2 p10/p50/p90/p99:", summary["area_m2_percentiles_10_50_90_99"])
    print("\nneck-ratio sensitivity (higher ratio = more splitting; 'none' = no splitting):")
    for k, v in sens.items():
        print(f"{str(k):>6} | instances {v[0]:>4} | components split {v[1]:>3}")

    # v6 / v7 / v8 comparison, overall and per window
    wins = gpd.read_file(a.windows_gpkg, layer="windows").to_crs(CRS) if os.path.exists(a.windows_gpkg) else None
    lay = [("v6 components", gpd.read_file(a.v6).to_crs(CRS) if os.path.exists(a.v6) else None),
           ("v7 instances", gpd.read_file(a.v7, layer="buildings").to_crs(CRS) if os.path.exists(a.v7) else None),
           ("v8 instances", df)]
    comp_rows = []
    for name, g in lay:
        if g is None:
            continue
        rp = g.geometry.representative_point()
        ins = shapely.contains_xy(boundary, rp.x.values, rp.y.values) if boundary is not None else np.ones(len(g), bool)
        ar = g.geometry.area
        row = dict(layer=name, polygons=len(g), inside_village=int(ins.sum()), area_p50=round(float(ar.median()), 1),
                   area_p90=round(float(ar.quantile(0.9)), 1), n_gt400m2=int((ar > 400).sum()))
        if wins is not None:
            for _, w in wins.iterrows():
                row[f"{w.window_id}"] = int(g.geometry.representative_point().within(w.geometry).sum())
        comp_rows.append(row)
    cmp_df = pd.DataFrame(comp_rows)
    cmp_df.to_csv(os.path.join(a.out_dir, f"comparison_v6_v7_v8_{a.tag}.csv"), index=False)
    print("\nCOMPARISON (polygons; counts per sampling window = representative point inside window):")
    print(cmp_df.to_string(index=False))
    print("\nWrote:", out_gpkg, out_csv, out_json, sep="\n  ")
    if not a.no_overlays and wins is not None:
        made = render_overlays(a.raster, [(n_, g) for n_, g in lay if g is not None], wins, os.path.join(a.out_dir, "overlays"), inv0)
        print("Overlays (panels: v6 | v7 | v8; v8 colours: green PLAUSIBLE, orange REVIEW, magenta UNRESOLVED_MERGE):", *made, sep="\n  ")


if __name__ == "__main__":
    main()
