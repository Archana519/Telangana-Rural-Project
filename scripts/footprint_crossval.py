"""Task 1 - multi-source open building-footprint cross-validation (100 % automated; NOT manual ground truth).

    python scripts/footprint_crossval.py [--windows damarakunta alampur ...] [--no-fetch]

Our StrongDINOv2Seg footprints (state_segmentation.pkl 'classified', clipped to the study window) are compared with independent open footprint sources, and the open sources
are compared with each other. References (all clipped to the same window):
  Overture all            Overture Maps buildings, pinned release (configs/multivillage/common.yaml); conflates OpenStreetMap + Google Open Buildings (+ Microsoft where it adds a polygon)
  Overture - OSM only     the subset of Overture features whose source dataset is OpenStreetMap (human-mapped)
  Overture - Google only  the subset whose source dataset is Google Open Buildings (ML-derived)
  Google Open Buildings v3  the raw v3 polygons, used where already cached (Damarakunta only)
Microsoft ML Buildings: no Overture feature in any of the four windows carries Microsoft as its source dataset, and no raw Microsoft tile is cached, so it is not scored.
Overture conflates its sources (a footprint appears once, under one source dataset), so the OSM and Google subsets do not overlap by construction and are never compared with each other.
Regions: "window" = the whole study window; "model coverage" = window intersected with the 30 m-buffered convex hull of our footprints (where StrongDINOv2Seg actually produced output: for
Damarakunta the stored v8 footprints cover only part of the window, so references outside that hull would count as misses that are not the model's).
Metrics: area level (IoU, precision = share of OUR area covered by the reference, recall = share of the REFERENCE area covered by ours, F1); detection level, robust to merged blobs
(recall = share of reference buildings whose representative point lies inside one of our footprints; precision = share of our footprints that contain or touch at least one reference building; F1);
instance level (one-to-one greedy matching at IoU >= 0.5), which punishes merged footprints (reported with the share of our footprints that contain >= 2 reference buildings).
These measure AGREEMENT between open datasets, not accuracy: every reference has its own errors.
Overture buildings missing from data/villages/<id>/buildings.gpkg are fetched from the pinned release (network) and cached next to it as overture_buildings_cache.gpkg.
Outputs: validation/footprint_crossval.csv, footprint_crossval.tex
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.ops import unary_union
from shapely.strtree import STRtree

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.multivillage import acquire as A, grid_graph as GG  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
GOOGLE_V3 = REPO / "Siddipet/Damarakunta/reference/external/google_open_buildings_v3.gpkg"


def f1(p, r):
    return 2 * p * r / (p + r) if p + r else 0.0


def area_metrics(a: gpd.GeoSeries, b: gpd.GeoSeries) -> dict:
    ua, ub = unary_union(list(a.geometry)), unary_union(list(b.geometry))
    inter = ua.intersection(ub).area
    union = ua.area + ub.area - inter
    p, r = inter / ua.area if ua.area else 0.0, inter / ub.area if ub.area else 0.0
    return dict(area_iou=inter / union if union else 0.0, area_precision=p, area_recall=r, area_f1=f1(p, r), area_a_m2=ua.area, area_b_m2=ub.area)


def instance_metrics(a: gpd.GeoSeries, b: gpd.GeoSeries, thr: float = 0.5) -> dict:
    ga, gb = list(a.geometry), list(b.geometry)
    tree = STRtree(gb)
    cand = []
    for i, g in enumerate(ga):
        for j in tree.query(g):
            inter = g.intersection(gb[int(j)]).area
            if inter > 0:
                iou = inter / (g.area + gb[int(j)].area - inter)
                if iou >= thr:
                    cand.append((iou, i, int(j)))
    cand.sort(reverse=True)
    ua, ub, tp = set(), set(), 0
    for iou, i, j in cand:
        if i not in ua and j not in ub:
            ua.add(i); ub.add(j); tp += 1
    p, r = tp / len(ga) if ga else 0.0, tp / len(gb) if gb else 0.0
    return dict(n_a=len(ga), n_b=len(gb), matched=tp, inst_precision=p, inst_recall=r, inst_f1=f1(p, r))


def detection_metrics(a: gpd.GeoSeries, b: gpd.GeoSeries) -> dict:
    ga, gb = list(a.geometry), list(b.geometry)
    ta, tb = STRtree(ga), STRtree(gb)
    rec = sum(1 for g in gb if any(ga[int(i)].contains(g.representative_point()) for i in ta.query(g.representative_point())))
    prec, merged = 0, 0
    for g in ga:
        hits = [int(j) for j in tb.query(g) if g.intersects(gb[int(j)])]
        inside = [j for j in hits if g.contains(gb[j].representative_point())]
        prec += bool(hits)
        merged += len(inside) >= 2
    p, r = prec / len(ga) if ga else 0.0, rec / len(gb) if gb else 0.0
    return dict(det_precision=p, det_recall=r, det_f1=f1(p, r), ours_merging_2plus_ref_pct=100 * merged / len(ga) if ga else 0.0)


def overture(vid: str, cfg, cell, fetch: bool):
    ddir = A.data_dir(cfg)
    for name in ("buildings.gpkg", "overture_buildings_cache.gpkg"):
        f = ddir / name
        if f.exists():
            b = gpd.read_file(f).to_crs(A.CRS_WORK)
            if len(b):
                return b
    if not fetch:
        return None
    import geopandas
    wgs = geopandas.GeoSeries([cell.buffer(500)], crs=A.CRS_WORK).to_crs(4326).total_bounds
    b = A._fetch_buildings(cfg, cell, wgs)
    b.to_file(ddir / "overture_buildings_cache.gpkg", driver="GPKG")
    return b


def clip(g: gpd.GeoDataFrame, cell) -> gpd.GeoDataFrame:
    g = g[g.geometry.notna() & ~g.geometry.is_empty].copy()
    g["geometry"] = g.geometry.buffer(0).intersection(cell)
    return g[~g.geometry.is_empty & (g.geometry.area > 0.5)]


def one_window(key: str, fetch: bool, log=print) -> list:
    vid = GG.WINDOWS[key]
    cfg = A.load_cfg(vid)
    L = GG.load_window(key)
    if L is not None:
        cell, ours = L[1]["cell"], L[1]["classified"]
    else:
        import pickle
        cell = pickle.load(open(A.data_dir(cfg) / "state.pkl", "rb"))["cell"]
        ours = None
        log(f"[{key}] SKIPPED: our StrongDINOv2Seg footprints (data/villages/{vid}/state_segmentation.pkl) are not on this machine")
        return []
    ov = overture(vid, cfg, cell, fetch)
    if ov is None:
        log(f"[{key}] no Overture buildings cached and --no-fetch given: skipped")
        return []
    ov = clip(ov, cell)
    refs = {"Overture (all sources)": ov, "Overture - OSM only": ov[ov.dataset == "OpenStreetMap"], "Overture - Google only": ov[ov.dataset == "Google Open Buildings"]}
    if key == "damarakunta" and GOOGLE_V3.exists():
        refs["Google Open Buildings v3 (raw)"] = clip(gpd.read_file(GOOGLE_V3).to_crs(A.CRS_WORK), cell)
    rows = []
    if ours is None:
        return rows
    ours = clip(ours, cell)
    hull = ours.geometry.union_all().convex_hull.buffer(30).intersection(cell)
    for region, area in (("window", cell), ("model coverage", hull)):
        o = clip(ours, area)
        for n, r in refs.items():
            r = clip(r, area)
            if len(o) < 5 or len(r) < 5:
                log(f"[{key}] {region}: ours vs {n}: skipped (fewer than 5 features: {len(o)} / {len(r)})")
                continue
            m = {**area_metrics(o, r), **instance_metrics(o, r), **detection_metrics(o, r), "region_km2": area.area / 1e6}
            rows.append(dict(window=key, region=region, a="StrongDINOv2Seg (ours)", b=n, **{k: (round(v, 4) if isinstance(v, float) else v) for k, v in m.items()}))
            r_ = rows[-1]
            log(f"[{key}] {region}: vs {n}: area IoU {r_['area_iou']:.3f} P {r_['area_precision']:.3f} R {r_['area_recall']:.3f} | detection P {r_['det_precision']:.3f} R {r_['det_recall']:.3f} | n {r_['n_a']} vs {r_['n_b']}")
    return rows


def latex(df: pd.DataFrame) -> str:
    out = ["\\begin{tabular}{llrrrrrr}", "\\hline", "Window & Reference & Area IoU & Area P & Area R & Detect.\\ P & Detect.\\ R & $n$ (ours / ref.) \\\\", "\\hline"]
    for w, g in df[df.region == "model coverage"].groupby("window", sort=False):
        for i, r in enumerate(g.itertuples()):
            out.append(f"{w.capitalize() if i == 0 else ''} & {r.b} & {r.area_iou:.3f} & {r.area_precision:.3f} & {r.area_recall:.3f} & {r.det_precision:.3f} & {r.det_recall:.3f} & {r.n_a:,} / {r.n_b:,} \\\\")
        out.append("\\hline")
    out.append("\\end{tabular}")
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--windows", nargs="+", default=list(GG.WINDOWS), choices=list(GG.WINDOWS))
    ap.add_argument("--no-fetch", action="store_true", help="never query Overture (S3); use only cached buildings")
    a = ap.parse_args()
    rows = [r for k in a.windows for r in one_window(k, not a.no_fetch)]
    GG.OUT.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_csv(GG.OUT / "footprint_crossval.csv", index=False, lineterminator="\n")
    if len(df):
        (GG.OUT / "footprint_crossval.tex").write_text(latex(df))
        print(df.drop(columns=["area_a_m2", "area_b_m2"]).to_string(index=False))


if __name__ == "__main__":
    main()
