#!/usr/bin/env python
"""Turn an existing building-probability raster into regularised, georeferenced footprint polygons.

READ-ONLY on inputs. Writes a NEW folder only. No model is run: it post-processes the probability
raster your segmentation pipeline already produced (e.g. predictions/tiled_v1/building_prob_full.tif,
uint8 probability scaled 0-255, EPSG:32644, 0.6 m).

Steps per block: smooth -> threshold -> clean -> split large blobs (distance-transform peaks)
-> polygonise (geotransform preserved) -> rectangle-regularise compact polygons / simplify others
-> area + validity filters -> de-duplicate across block borders.

LIMITS: footprints can only be as good as the probability map. Blobs larger than --large-area are flagged
LARGE_BLOB (a built-up block, not a single building). Output polygons are UNVERIFIED model predictions,
not surveyed buildings and not a house count.

Example (project root, .venv):
  .venv\\Scripts\\python.exe scripts\\extract_building_footprints.py ^
     --prob Siddipet\\Damarakunta\\predictions\\tiled_v1\\building_prob_full.tif ^
     --out-dir Siddipet\\Damarakunta\\results\\footprints_v9 --tag damarakunta
Add --window minx miny maxx maxy (map coordinates) to try a small area first.
"""
import argparse, hashlib, json, os, sys, datetime
import numpy as np
import rasterio
from rasterio.features import shapes
from rasterio.windows import Window, from_bounds
from scipy import ndimage as ndi
import geopandas as gpd
from shapely.geometry import shape, Polygon, MultiPolygon
from shapely.validation import make_valid

def sha256(p, n=1 << 22):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(n), b""): h.update(b)
    return h.hexdigest()

def process_block(p, tr, a, res):
    """p: float prob 0-1 (2D). Returns list of (geom, attrs) in map coords."""
    if a.sigma > 0: p = ndi.gaussian_filter(p, a.sigma)
    m = p >= a.thr
    if a.open_px > 0: m = ndi.binary_opening(m, iterations=a.open_px)
    if a.close_px > 0: m = ndi.binary_closing(m, iterations=a.close_px)
    m = ndi.binary_fill_holes(m)
    lab, n = ndi.label(m)
    if n == 0: return []
    # split large blobs using distance-transform peaks
    area_px = np.bincount(lab.ravel())
    big = np.where(area_px * res * res > a.split_area)[0]; big = big[big > 0]
    out_lab = lab.copy(); nxt = n + 1
    if len(big):
        dist = ndi.distance_transform_edt(m)
        dist_s = ndi.gaussian_filter(dist, 1.5)
        pk = (dist_s == ndi.maximum_filter(dist_s, size=a.peak_px)) & (dist_s >= a.min_peak_m / res) & m
        mk, nk = ndi.label(pk)
        for b in big:
            reg = lab == b
            ids = np.unique(mk[reg & (mk > 0)])
            if len(ids) < 2: continue
            markers = np.where(reg & np.isin(mk, ids), mk, 0)
            _, (iy, ix) = ndi.distance_transform_edt(markers == 0, return_indices=True)
            assigned = markers[iy, ix]
            for k, i_ in enumerate(ids):
                out_lab[reg & (assigned == i_)] = nxt; nxt += 1
            out_lab[reg & ~np.isin(assigned, ids)] = 0
    res_list = []
    lab_i = out_lab.astype(np.int32)
    means = ndi.mean(p, lab_i, index=np.arange(1, lab_i.max() + 1)) if lab_i.max() else []
    for geom, v in shapes(lab_i, mask=lab_i > 0, transform=tr):
        g = shape(geom)
        if not g.is_valid: g = make_valid(g)
        if g.geom_type == "MultiPolygon": g = max(g.geoms, key=lambda x: x.area)
        if g.geom_type != "Polygon" or g.area < a.min_area: continue
        g = Polygon(g.exterior)  # drop interior holes
        rect = g.minimum_rotated_rectangle
        rectness = g.area / rect.area if rect.area else 0
        if a.regularize and rectness >= a.rect_thr and rect.area >= a.min_area:
            g2 = rect; method = "RECT_REGULARISED"
        else:
            g2 = g.simplify(a.simplify, preserve_topology=True); method = "SIMPLIFIED"
        if not g2.is_valid: g2 = make_valid(g2)
        if g2.geom_type != "Polygon" or g2.area < a.min_area: continue
        flag = "LARGE_BLOB" if g2.area > a.large_area else "OK"
        res_list.append((g2, dict(area_m2=round(g2.area, 2), rectangularity=round(rectness, 3), method=method,
                                  mean_prob=round(float(means[int(v) - 1]), 3), flag=flag)))
    return res_list

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--prob", required=True, help="building probability raster, uint8 0-255 (or float 0-1)")
    ap.add_argument("--out-dir", required=True); ap.add_argument("--tag", default="village")
    ap.add_argument("--thr", type=float, default=0.5, help="probability threshold (0-1)")
    ap.add_argument("--sigma", type=float, default=1.0, help="gaussian smoothing, pixels")
    ap.add_argument("--open-px", type=int, default=1); ap.add_argument("--close-px", type=int, default=1)
    ap.add_argument("--min-area", type=float, default=12.0, help="m2")
    ap.add_argument("--split-area", type=float, default=150.0, help="blobs bigger than this (m2) are split at distance peaks")
    ap.add_argument("--peak-px", type=int, default=15); ap.add_argument("--min-peak-m", type=float, default=1.2)
    ap.add_argument("--large-area", type=float, default=400.0, help="polygons above this are flagged LARGE_BLOB")
    ap.add_argument("--rect-thr", type=float, default=0.78, help="area/min-rotated-rectangle ratio to snap to a rectangle")
    ap.add_argument("--no-regularize", dest="regularize", action="store_false")
    ap.add_argument("--simplify", type=float, default=0.35, help="m")
    ap.add_argument("--block", type=int, default=2048); ap.add_argument("--overlap", type=int, default=96)
    ap.add_argument("--window", nargs=4, type=float, metavar=("MINX", "MINY", "MAXX", "MAXY"))
    a = ap.parse_args()
    if os.path.exists(a.out_dir) and os.listdir(a.out_dir): sys.exit(f"Refusing to write into non-empty {a.out_dir}; choose a new folder.")
    os.makedirs(a.out_dir, exist_ok=True)
    feats = []
    with rasterio.open(a.prob) as src:
        res = abs(src.transform.a); crs = src.crs
        scale = 255.0 if src.dtypes[0] == "uint8" else 1.0
        full = Window(0, 0, src.width, src.height)
        win = from_bounds(*a.window, src.transform).round_offsets().round_lengths().intersection(full) if a.window else full
        x0, y0, W, H = int(win.col_off), int(win.row_off), int(win.width), int(win.height)
        print(f"raster {src.width}x{src.height} res={res} crs={crs}; processing {W}x{H} px; threshold={a.thr}")
        for by in range(0, H, a.block):
            for bx in range(0, W, a.block):
                cx0, cy0 = x0 + bx, y0 + by
                cw, ch = min(a.block, W - bx), min(a.block, H - by)
                rx0, ry0 = max(x0, cx0 - a.overlap), max(y0, cy0 - a.overlap)
                rx1, ry1 = min(x0 + W, cx0 + cw + a.overlap), min(y0 + H, cy0 + ch + a.overlap)
                w = Window(rx0, ry0, rx1 - rx0, ry1 - ry0)
                p = src.read(1, window=w).astype(np.float32) / scale
                if p.max() < a.thr * 0.5: continue
                tr = src.window_transform(w)
                core = Polygon([src.xy(cy0, cx0, offset="ul"), src.xy(cy0, cx0 + cw, offset="ul"), src.xy(cy0 + ch, cx0 + cw, offset="ul"), src.xy(cy0 + ch, cx0, offset="ul")])
                for g, at in process_block(p, tr, a, res):
                    if core.contains(g.representative_point()): feats.append(dict(geometry=g, **at))
                print(f"  block ({bx},{by}) -> total {len(feats)}", end="\r")
    print()
    if not feats: sys.exit("No polygons produced; lower --thr or check the raster.")
    gdf = gpd.GeoDataFrame(feats, crs=crs)
    gdf.insert(0, "building_id", range(1, len(gdf) + 1))
    gdf["source_raster"] = os.path.basename(a.prob)
    gdf["status"] = "UNVERIFIED_MODEL_PREDICTION"
    assert gdf.is_valid.all(), "invalid geometry produced"
    gpkg = os.path.join(a.out_dir, f"footprints_{a.tag}.gpkg")
    gdf.to_file(gpkg, layer="buildings", driver="GPKG")
    prov = dict(created=datetime.datetime.now().isoformat(timespec="seconds"), input=os.path.abspath(a.prob), input_sha256=sha256(a.prob),
                crs=str(crs), pixel_size_m=res, params={k: v for k, v in vars(a).items()}, n_polygons=len(gdf),
                n_large_blob=int((gdf.flag == "LARGE_BLOB").sum()), n_rect=int((gdf.method == "RECT_REGULARISED").sum()),
                area_m2_percentiles={q: float(np.percentile(gdf.area_m2, q)) for q in (5, 25, 50, 75, 95)},
                caveat="Unverified model-derived polygons; not surveyed buildings or house counts.")
    json.dump(prov, open(os.path.join(a.out_dir, f"provenance_{a.tag}.json"), "w"), indent=2)
    print(f"Wrote {gpkg}: {len(gdf)} polygons ({prov['n_large_blob']} LARGE_BLOB, {prov['n_rect']} rectangles)")

if __name__ == "__main__":
    main()
