"""v7: automatic roof-instance extraction from the EXISTING model outputs (no re-inference, no retraining).

Inputs (read-only):  pred_classes_<tag>.tif  (class IDs, 2 = Building)
                     building_prob_<tag>.tif (building probability scaled 0-255)
Output (new folder): buildings_v7_<tag>.gpkg  layers: buildings (instances), components (v6-style blobs)
                     buildings_v7_<tag>.csv, summary_v7_<tag>.json, overlays/*.png

What this is, honestly:
  * The checkpoint is a SEMANTIC segmentation model (one class per pixel). It has no per-roof (instance) output.
  * Step 1 keeps pixels the model calls Building (or prob >= --prob-thr) and labels connected regions
    ("components"; this is what v6 exported as candidates, so merged roofs stay merged there).
  * Step 2 tries to split each component into roofs with a distance-transform watershed. A component is split
    only where its distance transform has >= 2 peaks, each standing at least --h-m above the saddle between
    them (an h-maxima test: two bulges joined by a narrower neck). Roofs that touch with no neck at all, or
    whose merge the model produced inside a wide blob, are NOT separable this way. Those stay as one polygon
    and are flagged LARGE_UNSPLIT / COMPLEX_SHAPE for review. Splitting is a heuristic, not a measurement.
  * Tile-overlap duplicates: run_tiled_inference.py keeps only each tile's central region when it writes the
    full raster, so there is one prediction per pixel and no duplicate polygons by construction. This script
    verifies that (overlap check) instead of assuming it.
  * Small roofs are kept (default min area 6 m2) and flagged SMALL, not dropped.
Every polygon is an UNVERIFIED model prediction, not a surveyed building or a house count.
"""
import argparse, heapq, json, os, sys, time
import numpy as np
import cv2
import rasterio
import geopandas as gpd
import pandas as pd
from rasterio.features import shapes
from rasterio.transform import Affine
from shapely.geometry import shape as shp_shape, Polygon
from shapely.ops import unary_union
from shapely.validation import make_valid

ROOT = r"D:\Telangana_Rural_Project\Siddipet\Damarakunta"
CRS = "EPSG:32644"


# ----------------------------------------------------------------------------- instance splitting
def hmax_markers(dt, h):
    """Connected markers = regional maxima of dt whose prominence is >= h (grayscale reconstruction)."""
    k = np.ones((3, 3), np.uint8)
    rec = (dt - h).astype(np.float32)
    dt = dt.astype(np.float32)
    for _ in range(5000):
        nxt = np.minimum(cv2.dilate(rec, k), dt)
        if np.array_equal(nxt, rec):
            break
        rec = nxt
    top = ((dt - rec) >= (h - 1e-4)) & (dt > 0)
    n, lab = cv2.connectedComponents(top.astype(np.uint8), connectivity=8)
    return n - 1, lab


def flood(mask, dt, markers, n):
    """Marker-controlled watershed on -dt (priority flood, highest dt first). 8-connected."""
    lab = markers.astype(np.int32).copy()
    H, W = mask.shape
    heap, cnt = [], 0
    ys, xs = np.nonzero(markers > 0)
    for y, x in zip(ys, xs):
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


def split_component(mask, res, h_m, smooth_px, min_piece_m2, split_min_m2):
    """mask: bool crop of ONE component. Returns (labels int32 crop with 1..n, n)."""
    area = mask.sum() * res * res
    one = mask.astype(np.int32)
    if h_m is None or area < split_min_m2:
        return one, 1
    pad = np.pad(mask, 1)
    dt = cv2.distanceTransform(pad.astype(np.uint8), cv2.DIST_L2, 5).astype(np.float32) * res
    if smooth_px > 0:
        kk = int(2 * round(2 * smooth_px) + 1)
        dt = cv2.GaussianBlur(dt, (kk, kk), smooth_px)
    n, mk = hmax_markers(dt, h_m)
    if n < 2:
        return one, 1
    pm = np.pad(mask, 1)
    while n >= 2:
        lab = flood(pm, dt, mk, n)
        areas = np.bincount(lab[lab > 0].ravel(), minlength=n + 1)[1:] * res * res
        if areas.min() >= min_piece_m2:
            lab = lab[1:-1, 1:-1]
            lab[~mask] = 0
            return lab, n
        drop = int(np.argmin(areas)) + 1                   # drop the smallest piece's marker and retry
        mk[mk == drop] = 0
        keep = [i for i in np.unique(mk) if i > 0]
        remap = np.zeros(mk.max() + 1, np.int32)
        for new, old in enumerate(keep, 1):
            remap[old] = new
        mk = remap[mk]
        n = len(keep)
    return one, 1


# ----------------------------------------------------------------------------- helpers
def to_poly(lab_crop, lab_id, tr):
    geoms = [shp_shape(g) for g, v in shapes((lab_crop == lab_id).astype(np.uint8), mask=(lab_crop == lab_id),
                                              transform=tr, connectivity=8) if v == 1]
    if not geoms:
        return None
    g = unary_union(geoms)
    return make_valid(g) if not g.is_valid else g


def render_overlays(raster, inst, comps, wins, boundary, out_dir, pad_m=15, scale=2):
    os.makedirs(out_dir, exist_ok=True)
    made = []
    with rasterio.open(raster) as src:
        # full-extent overview
        f = max(1, int(np.ceil(src.width / 2400)))
        ov = src.read([1, 2, 3], out_shape=(3, src.height // f, src.width // f)).transpose(1, 2, 0)
        ov = np.ascontiguousarray(ov[:, :, ::-1])
        t = src.transform
        for g in inst.geometry:
            c = g.representative_point()
            x, y = int((c.x - t.c) / t.a / f), int((c.y - t.f) / t.e / f)
            cv2.circle(ov, (x, y), 3, (0, 0, 255), -1)
        if boundary is not None:
            for poly in getattr(boundary, "geoms", [boundary]):
                pts = np.array([[(x - t.c) / t.a / f, (y - t.f) / t.e / f] for x, y in poly.exterior.coords], np.int32)
                cv2.polylines(ov, [pts], True, (0, 255, 255), 2)
        p = os.path.join(out_dir, "overview_instances.png"); cv2.imwrite(p, ov); made.append(p)
        if wins is None:
            return made
        for _, w in wins.iterrows():
            minx, miny, maxx, maxy = w.geometry.buffer(pad_m).bounds
            win = rasterio.windows.from_bounds(minx, miny, maxx, maxy, src.transform).round_offsets().round_lengths()
            win = win.intersection(rasterio.windows.Window(0, 0, src.width, src.height))
            img = src.read([1, 2, 3], window=win).transpose(1, 2, 0)
            tr = src.window_transform(win)
            big = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)[:, :, ::-1].copy()
            left, right = big.copy(), big.copy()

            def draw(canvas, gdf, colour_by_id):
                for _, r in gdf.iterrows():
                    for poly in getattr(r.geometry, "geoms", [r.geometry]):
                        if poly.is_empty:
                            continue
                        pts = np.array([[(x - tr.c) / tr.a * scale, (y - tr.f) / tr.e * scale]
                                        for x, y in poly.exterior.coords], np.int32)
                        col = (0, 0, 255)
                        if colour_by_id:
                            rng = np.random.default_rng(int(r["comp_id"]) * 7919 + int(r["piece"]))
                            col = tuple(int(v) for v in rng.integers(60, 255, 3))
                            if r["n_in_comp"] > 1:
                                col = (0, 255, 255)
                        cv2.polylines(canvas, [pts], True, col, 2)
            draw(left, comps, False)
            draw(right, inst, True)
            cv2.putText(left, "components (v6-style blobs)", (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            cv2.putText(right, "v7 instances (yellow = split)", (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            p = os.path.join(out_dir, f"{w.window_id}_components_vs_instances.png")
            cv2.imwrite(p, np.hstack([left, right])); made.append(p)
    return made


# ----------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="full")
    ap.add_argument("--pred-dir", default=os.path.join(ROOT, "predictions", "tiled_v1"))
    ap.add_argument("--raster", default=os.path.join(ROOT, "aligned", "damarakunta_esri_highres_mosaic_0p6m.tif"))
    ap.add_argument("--boundary", default=os.path.join(ROOT, "study_area", "damarakunta_boundary.gpkg"))
    ap.add_argument("--windows-gpkg", default=os.path.join(ROOT, "results", "v6_buildings", "reference",
                                                           "digitize_windows.gpkg"))
    ap.add_argument("--out-dir", default=os.path.join(ROOT, "results", "v7_instances"))
    ap.add_argument("--prob-thr", type=float, default=None,
                    help="foreground = building prob >= thr (0-1) INSTEAD of argmax class 2 (use e.g. 0.35 to recover small roofs)")
    ap.add_argument("--min-area-m2", type=float, default=6.0, help="drop below this (default keeps small rural roofs)")
    ap.add_argument("--small-flag-m2", type=float, default=15.0)
    ap.add_argument("--large-flag-m2", type=float, default=400.0)
    ap.add_argument("--h-m", type=float, default=1.0, help="DT peak prominence needed to split (m); <=0 disables splitting")
    ap.add_argument("--smooth-px", type=float, default=1.0)
    ap.add_argument("--split-min-m2", type=float, default=40.0, help="only try to split components at least this big")
    ap.add_argument("--min-piece-m2", type=float, default=12.0, help="reject splits that create a piece below this")
    ap.add_argument("--simplify-m", type=float, default=0.0)
    ap.add_argument("--low-conf", type=float, default=0.5)
    ap.add_argument("--overwrite", action="store_true")
    ap.add_argument("--no-overlays", action="store_true")
    a = ap.parse_args()

    os.makedirs(a.out_dir, exist_ok=True)
    out_gpkg = os.path.join(a.out_dir, f"buildings_v7_{a.tag}.gpkg")
    out_csv = os.path.join(a.out_dir, f"buildings_v7_{a.tag}.csv")
    out_json = os.path.join(a.out_dir, f"summary_v7_{a.tag}.json")
    for p in (out_gpkg, out_csv, out_json):
        if os.path.exists(p) and not a.overwrite:
            sys.exit(f"{p} exists; use --overwrite (replaces only this script's own v7 output)")
    if a.overwrite and os.path.exists(out_gpkg):
        os.remove(out_gpkg)

    t0 = time.time()
    with rasterio.open(os.path.join(a.pred_dir, f"pred_classes_{a.tag}.tif")) as s:
        cls, tr, crs = s.read(1), s.transform, s.crs
    with rasterio.open(os.path.join(a.pred_dir, f"building_prob_{a.tag}.tif")) as s:
        prob = s.read(1)
    if cls.shape != prob.shape:
        sys.exit("class and probability rasters differ in shape")
    res = abs(tr.a)
    pix_m2 = res * res
    print(f"CRS: {crs} | res: {res} m | shape: {cls.shape}")
    fg = (prob >= int(round(a.prob_thr * 255))) if a.prob_thr is not None else (cls == 2)
    print(f"foreground rule: {'prob >= %.2f' % a.prob_thr if a.prob_thr is not None else 'argmax class == 2'} | "
          f"pixels: {int(fg.sum())} ({100 * fg.mean():.3f}%)")
    n, cc, stats, _ = cv2.connectedComponentsWithStats(fg.astype(np.uint8), connectivity=8)
    print(f"connected components: {n - 1}")

    boundary = None
    if os.path.exists(a.boundary):
        boundary = gpd.read_file(a.boundary).to_crs(CRS).geometry.union_all()
    else:
        print("WARNING: boundary file not found; inside_village will be empty")

    H, W = cls.shape
    rows, geoms, crow, cgeoms = [], [], [], []
    sens_h = [0.4, 0.7, 1.0, 1.5, 2.0, 3.0, None]
    sens = {("none" if h is None else h): [0, 0] for h in sens_h}       # [instances, components_split]
    for cid in range(1, n):
        x, y, w, hh, ar = [int(v) for v in stats[cid]]
        if ar * pix_m2 < a.min_area_m2:
            continue
        x0, y0, x1, y1 = max(x - 1, 0), max(y - 1, 0), min(x + w + 1, W), min(y + hh + 1, H)
        mask = cc[y0:y1, x0:x1] == cid
        ctr = Affine(tr.a, tr.b, tr.c + tr.a * x0 + tr.b * y0, tr.d, tr.e, tr.f + tr.d * x0 + tr.e * y0)
        pc = prob[y0:y1, x0:x1].astype(np.float32) / 255.0

        for h in sens_h:                                                  # sensitivity (cheap; ~240 components)
            lab_s, ns = split_component(mask, res, h if h is None else h, a.smooth_px, a.min_piece_m2, a.split_min_m2)
            k = "none" if h is None else h
            sens[k][0] += ns; sens[k][1] += int(ns > 1)

        lab, npc = split_component(mask, res, a.h_m if a.h_m > 0 else None, a.smooth_px, a.min_piece_m2, a.split_min_m2)
        cg = to_poly(mask.astype(np.int32), 1, ctr)
        crow.append(dict(comp_id=cid, n_pixels=ar, area_m2=round(ar * pix_m2, 2), n_pieces=npc,
                         mean_prob=round(float(pc[mask].mean()), 4)))
        cgeoms.append(cg)
        for pid in range(1, npc + 1):
            pm = lab == pid
            npx = int(pm.sum())
            if npx * pix_m2 < a.min_area_m2:
                continue
            g = to_poly(lab, pid, ctr)
            if g is None or g.is_empty:
                continue
            if a.simplify_m > 0:
                g = g.simplify(a.simplify_m, preserve_topology=True)
            area = g.area
            hull = g.convex_hull.area or 1.0
            solidity = area / hull
            per = g.length or 1.0
            compact = 4 * np.pi * area / (per * per)
            flags = []
            if npc > 1:
                flags.append("SPLIT_BY_WATERSHED")
            if area < a.small_flag_m2:
                flags.append("SMALL")
            if npc == 1 and area > a.large_flag_m2:
                flags.append("LARGE_UNSPLIT")
            if solidity < 0.7:
                flags.append("COMPLEX_SHAPE")
            pmean = float(pc[pm].mean())
            if pmean < a.low_conf:
                flags.append("LOW_CONF")
            touches = (x0 == 0 and pm[:, 0].any()) or (y0 == 0 and pm[0, :].any()) or \
                      (x1 == W and pm[:, -1].any()) or (y1 == H and pm[-1, :].any())
            if touches:
                flags.append("EDGE_OF_MOSAIC")
            rows.append(dict(comp_id=cid, piece=pid, n_in_comp=npc, area_m2=round(area, 2),
                             perimeter_m=round(per, 2), solidity=round(solidity, 3), compactness=round(compact, 3),
                             mean_prob=round(pmean, 4), max_prob=round(float(pc[pm].max()), 4),
                             flags=";".join(flags),
                             inside_village=(None if boundary is None else bool(boundary.contains(g.representative_point())))))
            geoms.append(g)

    inst = gpd.GeoDataFrame(rows, geometry=geoms, crs=CRS)
    inst.insert(0, "cand_id", np.arange(1, len(inst) + 1))              # v6-compatible id column
    inst.insert(1, "bld_id", [f"B{i:05d}" for i in inst.cand_id])
    inst["status"] = "AUTO_DETECTED_UNVERIFIED"
    comps = gpd.GeoDataFrame(crow, geometry=cgeoms, crs=CRS)

    # duplicate / overlap check (should be zero: one prediction per pixel)
    ov = 0
    if len(inst):
        left, right = inst.sindex.query(inst.geometry, predicate="intersects")
        for i, j in zip(left, right):
            if i < j and inst.geometry.iloc[i].intersection(inst.geometry.iloc[j]).area > 0.05:
                ov += 1

    inst.to_file(out_gpkg, layer="buildings", driver="GPKG")
    comps.to_file(out_gpkg, layer="components", driver="GPKG")
    inst.drop(columns="geometry").to_csv(out_csv, index=False)

    flag_counts = {}
    for f in inst["flags"]:
        for x in [s for s in f.split(";") if s]:
            flag_counts[x] = flag_counts.get(x, 0) + 1
    inside = inst if boundary is None else inst[inst.inside_village == True]
    summary = dict(
        tag=a.tag, params={k: v for k, v in vars(a).items() if k not in ("overwrite", "no_overlays")},
        components=int(len(comps)), instances=int(len(inst)),
        components_split=int((comps.n_pieces > 1).sum()), instances_inside_village=int(len(inside)),
        components_inside_village=(None if boundary is None else
                                   int(sum(boundary.contains(g.representative_point()) for g in comps.geometry))),
        area_m2_percentiles_10_50_90_99=[round(float(x), 1) for x in np.percentile(inst.area_m2, [10, 50, 90, 99])] if len(inst) else None,
        flag_counts=flag_counts, overlapping_pairs=int(ov),
        split_sensitivity_h_m={str(k): dict(instances=v[0], components_split=v[1]) for k, v in sens.items()},
        seconds=round(time.time() - t0, 1),
        note="instances are UNVERIFIED model predictions; splitting is a heuristic; not a house count")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"\ninstances: {len(inst)} from {len(comps)} components ({summary['components_split']} split) | "
          f"inside village: {summary['instances_inside_village']} (components: {summary['components_inside_village']})")
    print("area m2 p10/p50/p90/p99:", summary["area_m2_percentiles_10_50_90_99"])
    print("flags:", flag_counts)
    print("overlapping instance pairs (expect 0):", ov)
    print("\nsplit sensitivity (h = required DT-peak prominence in metres):")
    print("   h_m | instances | components_split")
    for k, v in sens.items():
        print(f"{str(k):>6} | {v[0]:>9} | {v[1]:>16}")
    print("\nWrote:", out_gpkg, out_csv, out_json, sep="\n  ")

    if not a.no_overlays:
        wins = gpd.read_file(a.windows_gpkg, layer="windows").to_crs(CRS) if os.path.exists(a.windows_gpkg) else None
        made = render_overlays(a.raster, inst, comps, wins, boundary, os.path.join(a.out_dir, "overlays"))
        print("Overlays:", *made, sep="\n  ")


if __name__ == "__main__":
    main()
