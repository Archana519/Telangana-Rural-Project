#!/usr/bin/env python
"""google_open_buildings_test.py - first Google Open Buildings v3 test for one village.

Source : Google Research Open Buildings v3 (https://sites.research.google/open-buildings/)
Modes  : --source tiles (default) official public S2-level-4 CSV tiles, NO authentication, but each
                         tile is one large file that is streamed and filtered locally (never the global set).
         --source ee     Google Earth Engine 'GOOGLE/Research/open-buildings/v3/polygons'; downloads only the
                         study area but needs Earth Engine sign-up + `earthengine authenticate` + --ee-project.
Nothing existing is modified. Refuses to overwrite files in --out-dir.
Google polygons are model-derived candidates, NOT ground truth. So are the project's own candidates.
"""
import argparse, gzip, io, json, math, sys, hashlib, datetime as dt
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent
if (ROOT / "view_footprints.py").exists():
    sys.path.insert(0, str(ROOT))
elif (ROOT.parent / "view_footprints.py").exists():
    sys.path.insert(0, str(ROOT.parent))
VILLAGE = None
S2_URL = "https://storage.googleapis.com/open-buildings-data/v3/polygons_s2_level_4_gzip/{tok}_buildings.csv.gz"
LICENCE = ("Google Open Buildings v3: CC BY 4.0 and ODbL v1.0 (dual licence per the dataset page; confirm on "
           "https://sites.research.google/open-buildings/ before publication). Attribute: 'Google Open Buildings v3'.")


def die(m):
    print("ERROR:", m); sys.exit(2)


def warn(m):
    print("WARNING:", m)


def find_boundary(vdir):
    ex = {"results", "predictions", "raw", "aligned", ".venv", "__pycache__"}
    out = []
    for p in vdir.rglob("*"):
        if p.suffix.lower() in (".gpkg", ".shp", ".geojson") and not (set(p.relative_to(vdir).parts[:-1]) & ex):
            n = p.stem.lower()
            if any(k in n for k in ("boundary", "village", "study", "aoi", "extent")):
                out.append(p)
    return out


def s2_tokens(lonlat_bbox):
    try:
        import s2sphere as s2
    except ImportError:
        die("pip install s2sphere   (run in the project .venv)")
    w, s, e, n = lonlat_bbox
    rect = s2.LatLngRect(s2.LatLng.from_degrees(s, w), s2.LatLng.from_degrees(n, e))
    rc = s2.RegionCoverer(); rc.min_level = rc.max_level = 4; rc.max_cells = 20
    return sorted({c.to_token() for c in rc.get_covering(rect)})


def download_resumable(url, dest, tries=30):
    """Download url -> dest with HTTP Range resume and progress. Cached files are reused."""
    import requests, time
    dest.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    try:
        h = requests.head(url, allow_redirects=True, timeout=60)
        if h.status_code != 200:
            die(f"HEAD {url} -> HTTP {h.status_code} (tile may not exist, or access blocked)")
        total = int(h.headers.get("Content-Length", 0))
    except requests.RequestException as ex:
        warn(f"could not read file size ({ex}); continuing without it")
    for attempt in range(1, tries + 1):
        have = dest.stat().st_size if dest.exists() else 0
        if total and have == total:
            print(f"  tile already cached: {dest} ({have/1e6:,.0f} MB)"); return
        if total and have > total:
            dest.unlink(); have = 0
        try:
            hdr = {"Range": f"bytes={have}-"} if have else {}
            with requests.get(url, stream=True, headers=hdr, timeout=(30, 90)) as r:
                if r.status_code not in (200, 206):
                    die(f"GET {url} -> HTTP {r.status_code}")
                if have and r.status_code == 200:
                    have = 0
                mode = "ab" if r.status_code == 206 else "wb"
                print(f"  download attempt {attempt}: {have/1e6:,.0f} MB of {total/1e6:,.0f} MB already on disk")
                done, nxt = have, have + 50_000_000
                with open(dest, mode) as f:
                    for chunk in r.iter_content(1 << 20):
                        f.write(chunk); done += len(chunk)
                        if done >= nxt:
                            print(f"  ... {done/1e6:,.0f} MB" + (f" ({100*done/total:.0f}%)" if total else ""), flush=True)
                            nxt += 50_000_000
            if not total or dest.stat().st_size == total:
                print("  download complete"); return
        except Exception as ex:
            print(f"  interrupted ({type(ex).__name__}); retrying and resuming in 5 s", flush=True)
            time.sleep(5)
    die("download did not complete; run again and it will resume from the cached file")


def fetch_tiles(tokens, bbox, cache):
    import pandas as pd
    w, s, e, n = bbox
    parts = []
    for tok in tokens:
        url = S2_URL.format(tok=tok)
        dest = Path(cache) / f"{tok}_buildings.csv.gz"
        print(f"tile {tok}: {url}\n  cache: {dest}")
        download_resumable(url, dest)
        rows = 0
        try:
            for ch in pd.read_csv(dest, compression="gzip", chunksize=500_000,
                                  usecols=["latitude", "longitude", "area_in_meters", "confidence", "geometry", "full_plus_code"]):
                rows += len(ch)
                m = ch[(ch.longitude >= w) & (ch.longitude <= e) & (ch.latitude >= s) & (ch.latitude <= n)]
                if len(m):
                    parts.append(m)
                print(f"  scanned {rows:,} rows; kept {sum(len(x) for x in parts):,}", flush=True)
        except Exception as ex:
            die(f"could not read cached tile {dest} ({ex}); delete that file and rerun to download it again")
    return pd.concat(parts, ignore_index=True) if parts else None


def fetch_ee(bbox, project):
    try:
        import ee
    except ImportError:
        die("pip install earthengine-api")
    try:
        ee.Initialize(project=project)
    except Exception as ex:
        die("Earth Engine not authenticated/initialised: run  .venv\\Scripts\\earthengine.exe authenticate  "
            f"then pass --ee-project <your-cloud-project>.  ({ex})")
    import pandas as pd
    w, s, e, n = bbox
    fc = ee.FeatureCollection("GOOGLE/Research/open-buildings/v3/polygons").filterBounds(ee.Geometry.Rectangle([w, s, e, n]))
    cnt = fc.size().getInfo()
    print(f"EE reports {cnt} features in bbox")
    if cnt > 4500:
        die("more than 4500 features: shrink the extent or export via ee.batch.Export (getInfo limit is 5000)")
    feats = fc.getInfo()["features"]
    from shapely.geometry import shape
    return pd.DataFrame([{**f["properties"], "geometry": shape(f["geometry"]).wkt} for f in feats])


def stats(a):
    a = np.asarray(a, float)
    q = np.percentile(a, [0, 10, 25, 50, 75, 90, 100]).round(3).tolist()
    bins = [0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1.0001]
    h, _ = np.histogram(a, bins=bins)
    return {"n": int(a.size), "mean": round(float(a.mean()), 3), "percentiles_0_10_25_50_75_90_100": q,
            "histogram": {f"{bins[i]:.2f}-{min(bins[i+1],1):.2f}": int(h[i]) for i in range(len(h))},
            "below_0.65": int((a < 0.65).sum())}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--village-dir", default=r"Siddipet\Damarakunta")
    ap.add_argument("--imagery", default=None)
    ap.add_argument("--candidates", default=None, help="existing candidate footprints gpkg (for comparison)")
    ap.add_argument("--boundary", default=None, help="village/study boundary (gpkg/shp/geojson); auto-searched if omitted")
    ap.add_argument("--boundary-layer", default=None)
    ap.add_argument("--test-extent", nargs=4, type=float, metavar=("MINX", "MINY", "MAXX", "MAXY"),
                    help="user-approved test extent in the raster CRS (only if no boundary)")
    ap.add_argument("--use-candidate-extent", action="store_true",
                    help="use candidate-footprint bounds + --margin as the test extent (documented as a test extent only)")
    ap.add_argument("--margin", type=float, default=60.0)
    ap.add_argument("--source", choices=["tiles", "ee"], default="tiles")
    ap.add_argument("--ee-project", default=None)
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--min-confidence", type=float, default=0.0, help="optional filter; default keeps all (v3 min is 0.65)")
    ap.add_argument("--cache-dir", default=None, help="where the downloaded tile is kept (default <out-dir>\\_cache)")
    ap.add_argument("--dpi", type=int, default=300)
    a = ap.parse_args()

    import rasterio, geopandas as gpd, matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from shapely.geometry import box
    from shapely import wkt as shwkt

    vdir = Path(a.village_dir).resolve()
    img_p = Path(a.imagery) if a.imagery else vdir / "aligned" / "damarakunta_esri_highres_mosaic_0p6m.tif"
    cand_p = Path(a.candidates) if a.candidates else vdir / "results" / "footprints_v9_test" / "footprints_test.gpkg"
    out = Path(a.out_dir) if a.out_dir else vdir / "results" / "google_open_buildings"
    for p in (img_p,):
        if not p.exists():
            die(f"not found: {p}")
    out.mkdir(parents=True, exist_ok=True)
    gpkg_p, prov_p = out / "google_open_buildings_v3.gpkg", out / "provenance.json"
    pngs = [out / "gob_overlay.png", out / "gob_closeup.png", out / "gob_comparison_closeup.png"]
    for p in [gpkg_p, prov_p] + pngs:
        if p.exists():
            die(f"{p} exists; refusing to overwrite. Use --out-dir for a new folder.")

    with rasterio.open(img_p) as src:
        crs, rb = src.crs, box(*src.bounds)
        print(f"imagery {img_p.name}: CRS {crs}, res {src.res}, bounds {src.bounds}")
    cand = None
    if cand_p.exists():
        cand = gpd.read_file(cand_p).to_crs(crs)
        print(f"candidates: {len(cand)} polygons from {cand_p}")
    else:
        warn(f"candidate file not found ({cand_p}); comparison skipped")

    # ---- study area -----------------------------------------------------------------------------
    area_src = None
    if a.boundary:
        bp = Path(a.boundary)
    else:
        found = find_boundary(vdir)
        print("boundary candidates found by name search:", [str(f) for f in found])
        bp = found[0] if len(found) == 1 else None
        if len(found) > 1:
            die("several possible boundary files; choose one with --boundary (I will not guess)")
    if bp is not None:
        if not bp.exists():
            die(f"boundary not found: {bp}")
        bg = gpd.read_file(bp, layer=a.boundary_layer) if a.boundary_layer else gpd.read_file(bp)
        if bg.crs is None:
            die("boundary has no CRS")
        bg = bg.to_crs(crs)
        study = bg.geometry.union_all()
        area_src = {"type": "boundary", "file": str(bp), "features": len(bg)}
    elif a.test_extent:
        study = box(*a.test_extent); area_src = {"type": "user_test_extent", "extent": a.test_extent}
    elif a.use_candidate_extent and cand is not None:
        tb = cand.total_bounds
        study = box(tb[0] - a.margin, tb[1] - a.margin, tb[2] + a.margin, tb[3] + a.margin)
        area_src = {"type": "candidate_extent_plus_margin_TEST_ONLY", "margin_m": a.margin}
        warn("NO village boundary used: this is a small test extent around the 58 candidates, not the village")
    else:
        die("no village boundary found. Give --boundary FILE, or an approved --test-extent, or --use-candidate-extent")
    print("study area:", area_src, "bounds", tuple(round(v, 1) for v in study.bounds))
    cover = study.intersection(rb).area / study.area
    print(f"study area covered by imagery: {100*cover:.1f}%")
    sg = gpd.GeoSeries([study], crs=crs).to_crs(4326)
    bbox = tuple(sg.total_bounds)  # w,s,e,n

    # ---- retrieve -------------------------------------------------------------------------------
    t0 = dt.datetime.utcnow().isoformat() + "Z"
    tokens = None
    if a.source == "tiles":
        tokens = s2_tokens(bbox)
        print("S2 level-4 tiles needed:", tokens)
        df = fetch_tiles(tokens, bbox, Path(a.cache_dir) if a.cache_dir else out / "_cache")
    else:
        df = fetch_ee(bbox, a.ee_project)
    if df is None or df.empty:
        die("no Google buildings returned for this extent (could be genuinely none, or a failed query)")
    g = gpd.GeoDataFrame(df.drop(columns=["geometry"]), geometry=[shwkt.loads(w) for w in df["geometry"]], crs=4326)
    n_raw = len(g)
    g = g.to_crs(crs)
    g = g[g.geometry.intersects(study)].copy()
    if a.min_confidence > 0:
        g = g[g["confidence"] >= a.min_confidence]
    g["clipped_to_study_area"] = False
    if area_src["type"] == "boundary":
        clipped = g.geometry.intersection(study)
        part = ~g.geometry.within(study)
        g.loc[part, "geometry"] = clipped[part]
        g.loc[part, "clipped_to_study_area"] = True
    g["area_m2_utm"] = g.geometry.area.round(2)
    g = g[~g.geometry.is_empty].reset_index(drop=True)
    print(f"retrieved in bbox: {n_raw}; kept in study area: {len(g)}")
    if g.empty:
        die("no polygons intersect the study area")
    g.to_file(gpkg_p, layer="google_buildings", driver="GPKG")
    print("saved", gpkg_p)

    # ---- comparison (descriptive only) -------------------------------------------------------------
    comp = None
    if cand is not None and len(cand):
        sidx = g.sindex
        ov, frac = 0, []
        for geom in cand.geometry:
            hit = g.iloc[list(sidx.query(geom, predicate="intersects"))]
            if len(hit):
                ov += 1
                frac.append(float(hit.geometry.intersection(geom).area.sum() / geom.area))
        gin = g[g.geometry.intersects(box(*cand.total_bounds))]
        comp = {"candidates": len(cand), "candidates_touching_any_google_polygon": ov,
                "median_fraction_of_candidate_area_covered_by_google": round(float(np.median(frac)), 3) if frac else None,
                "google_polygons_inside_candidate_bounds_box": len(gin),
                "note": "descriptive overlap only; neither layer is ground truth"}
        print("comparison:", comp)

    # ---- figures ---------------------------------------------------------------------------------
    from view_footprints import load_image_window, densest_window, scalebar
    from matplotlib.lines import Line2D
    ref = cand if cand is not None else g
    tb = ref.total_bounds
    with rasterio.open(img_p) as src:
        img, valid, ext, _ = load_image_window(src, tuple(tb), a.margin)
        cb, _n = densest_window(ref, 120.0)
        cimg, _v, cext, _w = load_image_window(src, cb, 0.0)

    def plot(ax, im, ex, show_g=True, show_c=True, lw=0.9):
        ax.imshow(im, extent=ex, origin="upper", interpolation="nearest")
        if show_g:
            gs = g.cx[ex[0]:ex[1], ex[2]:ex[3]]
            if len(gs):
                gs.boundary.plot(ax=ax, color="black", linewidth=lw * 2.2); gs.boundary.plot(ax=ax, color="#00E5FF", linewidth=lw)
        if show_c and cand is not None:
            cs = cand.cx[ex[0]:ex[1], ex[2]:ex[3]]
            if len(cs):
                cs.boundary.plot(ax=ax, color="#FFEB3B", linewidth=lw * 0.8, linestyle="--")
        ax.set_xlim(ex[0], ex[1]); ax.set_ylim(ex[2], ex[3]); ax.set_aspect("equal")
        ax.tick_params(labelsize=7); ax.ticklabel_format(useOffset=False, style="plain")

    def leg(ax, show_g=True, show_c=True):
        h = []
        if show_g: h.append(Line2D([], [], color="#00E5FF", lw=2, label="Google Open Buildings v3 (candidate)"))
        if show_c and cand is not None: h.append(Line2D([], [], color="#FFEB3B", lw=1.5, ls="--", label="project candidates (58, unverified)"))
        ax.legend(handles=h, loc="upper right", fontsize=7, framealpha=0.85)

    ttl = "Google Open Buildings v3 vs project candidates - neither is ground truth\nimagery: " + img_p.name
    for stem, im, ex in ((pngs[0], img, ext), (pngs[1], cimg, cext)):
        fig, ax = plt.subplots(figsize=(10, 10)); plot(ax, im, ex, lw=0.9 if im is img else 1.4)
        scalebar(ax, ex); leg(ax); ax.set_title(ttl, fontsize=9)
        fig.savefig(stem, dpi=a.dpi, bbox_inches="tight"); plt.close(fig); print("saved", stem, f"({stem.stat().st_size:,} bytes)")
    fig, axs = plt.subplots(1, 2, figsize=(16, 8))
    plot(axs[0], cimg, cext, show_g=False, lw=1.4); axs[0].set_title("project candidates only", fontsize=9)
    plot(axs[1], cimg, cext, show_c=False, lw=1.4); axs[1].set_title("Google Open Buildings v3 only", fontsize=9)
    fig.savefig(pngs[2], dpi=a.dpi, bbox_inches="tight"); plt.close(fig); print("saved", pngs[2], f"({pngs[2].stat().st_size:,} bytes)")

    prov = {"run_utc": t0, "source": a.source, "dataset": "Google Open Buildings v3", "s2_level4_tiles": tokens,
            "url_pattern": S2_URL if a.source == "tiles" else "ee:GOOGLE/Research/open-buildings/v3/polygons",
            "study_area": area_src, "study_area_covered_by_imagery_pct": round(100 * cover, 1),
            "imagery": str(img_p), "output_crs": str(crs), "feature_count": len(g),
            "bounds_output_crs": [round(v, 2) for v in g.total_bounds], "attributes": [c for c in g.columns if c != "geometry"],
            "confidence": stats(g["confidence"]), "min_confidence_filter": a.min_confidence,
            "comparison": comp, "licence": LICENCE,
            "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "caveats": ["Google polygons are model-derived, not verified buildings",
                        "image-date mismatch between Google's source imagery and the ESRI mosaic is unknown"]}
    prov_p.write_text(json.dumps(prov, indent=2))
    print("saved", prov_p)
    print("confidence:", json.dumps(prov["confidence"]))
    print("done. Open the PNGs and judge alignment/roof shape by eye.")


if __name__ == "__main__":
    main()
