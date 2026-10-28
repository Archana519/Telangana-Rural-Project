#!/usr/bin/env python
"""village_readiness.py - READ-ONLY readiness check of candidate villages for Phase C.

For every village in a discovery folder (made by discover_mandal_villages.py) it OPENS the data and records, per required
input, one of:
    PRESENT     the content was opened or queried and meets the stated test
    MISSING     it was looked for and nothing usable exists
    UNVERIFIED  it exists only partly, or could not be checked from here (the detail column says why)
File names are never used as evidence on their own: rasters are opened and measured, vector layers are read, TGRAC layers
are queried over the village polygon (HTTP GET only).

It does NOT download imagery, create village folders, run inference or plan anything. Output goes to a NEW folder:
    Siddipet/_village_readiness/<tag>/
        village_readiness.csv         one row per village (status + detail per input, blockers, score)
        village_readiness_detail.json the measurements behind every status
        tgrac_layers_found.json       TGRAC layer URLs found in your scripts, with the layer name/geometry read from the server
        recommendation.md             ranked shortlist (heuristic, stated in the file) with the exact blockers
        provenance.json

Run from the project root:
    .venv\\Scripts\\python.exe scripts\\village_readiness.py --discovery-dir Siddipet\\_village_discovery\\<tag>
Optionally pin which TGRAC layer is which (recommended once you have checked them):
    --layers-json my_layers.json     {"roads": "<url>", "schools": "<url>", "health": "<url>", "anganwadi": "<url>", "plinth": "<url>"}
"""
from __future__ import annotations

import argparse
import warnings
import json
import re
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.features import geometry_mask
from rasterio.warp import transform_bounds
from rasterio.windows import from_bounds
from shapely.geometry import box, shape

from tgrac_rest import RestError, get_json, query_layer, save_json, stamp, utc_now

warnings.filterwarnings("ignore", category=rasterio.errors.NotGeoreferencedWarning)
P, M, U = "PRESENT", "MISSING", "UNVERIFIED"
URL_RE = re.compile(r"https://tgrac\.telangana\.gov\.in/arcgis/rest/services/[A-Za-z0-9_/\-\.]+/(?:MapServer|FeatureServer)/\d+")
ROLE_WORDS = {"roads": ("road",), "schools": ("school",), "health": ("health", "hospital", "phc", "sub centre", "subcentre"),
              "anganwadi": ("anganwadi", "awc"), "plinth": ("plinth",)}
IMG_SKIP = ("slope", "dem", "worldcover", "cost", "prohibited", "tiles_560", "segmentation", "prob", "pred")


def norm(s):
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


# ---------------------------------------------------------------- raster checks
def res_m(src):
    r = abs(src.res[0])
    if src.crs and src.crs.is_geographic:
        lat = (src.bounds.top + src.bounds.bottom) / 2
        return r * 111320.0 * float(np.cos(np.radians(lat)))
    return r


def bbox4326(src):
    return box(*transform_bounds(src.crs, "EPSG:4326", *src.bounds)) if src.crs else None


def to_crs_geom(geom4326, crs):
    return gpd.GeoSeries([geom4326], crs="EPSG:4326").to_crs(crs).iloc[0]


def check_imagery(folder, poly):
    """best local RGB-like raster for this village; returns (status, detail, measurements)"""
    if folder is None:
        return M, "no local village folder", {}
    cands = []
    for pat in ("aligned/*.tif", "raw/imagery/**/*.tif"):
        for p in folder.glob(pat):
            if any(k in p.name.lower() for k in IMG_SKIP):
                continue
            cands.append(p)
    meas = []
    for p in cands:
        try:
            with rasterio.open(p) as src:
                if not src.crs or src.transform.is_identity:
                    meas.append(dict(file=str(p), skipped="not georeferenced (no CRS / identity transform)"))
                    continue
                if src.count < 3:
                    continue
                bb = bbox4326(src)
                cov = float(bb.intersection(poly.envelope).area / poly.envelope.area)
                pg = to_crs_geom(poly, src.crs)
                scale = max(src.width, src.height) / 1024.0
                scale = max(scale, 1.0)
                oh, ow = max(int(src.height / scale), 1), max(int(src.width / scale), 1)
                data = src.read([1, 2, 3], out_shape=(3, oh, ow))
                tr = src.transform * src.transform.scale(src.width / ow, src.height / oh)
                inside = geometry_mask([pg], out_shape=(oh, ow), transform=tr, invert=True)
                valid = (data.max(axis=0) > 0)
                vfrac = float(valid[inside].mean()) if inside.any() else float("nan")
                meas.append(dict(file=str(p), resolution_m=round(res_m(src), 3), crs=str(src.crs), bbox_coverage=round(cov, 3),
                                 valid_share_inside_village=round(vfrac, 3) if np.isfinite(vfrac) else None, width=src.width, height=src.height))
        except Exception as e:
            meas.append(dict(file=str(p), error=repr(e)))
    good = [m for m in meas if "error" not in m and "skipped" not in m]
    if not good:
        return M, "no RGB-like georeferenced raster found by opening files in aligned/ or raw/imagery/", dict(files=meas)
    best = max(good, key=lambda m: (m["bbox_coverage"], m["valid_share_inside_village"] or 0, -m["resolution_m"]))
    ok = best["resolution_m"] <= 1.0 and best["bbox_coverage"] >= 0.98 and (best["valid_share_inside_village"] or 0) >= 0.95
    det = (f"{Path(best['file']).name}: {best['resolution_m']} m/pixel, covers {best['bbox_coverage']:.0%} of the village bbox, "
           f"{(best['valid_share_inside_village'] or 0):.0%} non-empty pixels inside the village polygon")
    return (P if ok else U), det + ("" if ok else "; test: <=1.0 m, >=98% coverage, >=95% non-empty"), dict(files=meas)


def window_stats(tifs, bb, kind):
    """first tile that contains the bbox; valid share in the bbox window (+ class counts for land cover)"""
    for p in tifs:
        try:
            with rasterio.open(p) as src:
                if not src.crs:
                    continue
                if not bbox4326(src).contains(bb):
                    continue
                b = transform_bounds("EPSG:4326", src.crs, *bb.bounds)
                w = from_bounds(*b, transform=src.transform)
                arr = src.read(1, window=w, boundless=False)
                if arr.size == 0:
                    continue
                nd = src.nodata
                if kind == "dem":
                    valid = np.isfinite(arr) & (arr > -500) & (arr != nd if nd is not None else True)
                    extra = dict(min=float(arr[valid].min()), max=float(arr[valid].max())) if valid.any() else {}
                else:
                    valid = arr != (nd if nd is not None else 0)
                    vals, cnt = np.unique(arr[valid], return_counts=True)
                    extra = dict(classes={int(a): int(b_) for a, b_ in zip(vals, cnt)})
                return dict(file=str(p), valid_share=round(float(valid.mean()), 4), window_shape=list(arr.shape), res_m=round(res_m(src), 1), **extra)
        except Exception as e:
            return dict(file=str(p), error=repr(e))
    return None


# ---------------------------------------------------------------- TGRAC layers
def scan_layer_urls(dirs):
    urls = {}
    for d in dirs:
        d = Path(d)
        if not d.exists():
            continue
        for p in list(d.rglob("*.py")) + list(d.rglob("*.json")) + list(d.rglob("*.md")) + list(d.rglob("*.txt")):
            try:
                if p.stat().st_size > 5_000_000:
                    continue
                t = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            t = re.sub(r"[\"']\s*\n\s*[\"']", "", t)       # join implicitly concatenated string literals
            t = re.sub(r"[\"']\s+[\"']", "", t)
            for u in URL_RE.findall(t):
                urls.setdefault(u, set()).add(p.name)
    return {u: sorted(v) for u, v in urls.items()}


def infer_roles(found, pinned):
    """role -> list of dict(url, source). Roles come from the layer NAME only, never from the URL path
    (the path names the whole service, so every layer of 'SchoolGIS_Folder/Schools' would look like a school layer)."""
    roles = {}
    for r, u in pinned.items():
        for uu in (u if isinstance(u, list) else [u]):
            roles.setdefault(r, []).append(dict(url=uu, source="pinned by --layers-json"))
    for u, meta in found.items():
        nm = (meta.get("name") or "").lower()
        if not nm or not meta.get("geometryType"):
            continue
        for r, words in ROLE_WORDS.items():
            if r not in pinned and any(w in nm for w in words):
                roles.setdefault(r, []).append(dict(url=u, source=f"INFERRED from layer name '{meta.get('name')}' (UNVERIFIED)"))
    return roles


def count_bbox(url, bbox, verify):
    """features whose envelope meets the bbox, using returnCountOnly (cheap); None if the server cannot say"""
    d = get_json(url.rstrip("/") + "/query", {"where": "1=1", "returnCountOnly": "true", "f": "json",
                                              "geometry": ",".join(f"{v:.8f}" for v in bbox), "geometryType": "esriGeometryEnvelope",
                                              "inSR": 4326, "spatialRel": "esriSpatialRelIntersects"}, verify=verify)
    return d.get("count")


def count_in_polygon(url, info, poly, verify, max_fetch=2000):
    """(n_intersecting or None, n_in_bbox, exceeded). When the bbox holds more than max_fetch features the features are NOT
    downloaded and n_intersecting is None (the caller reports UNVERIFIED with the bbox count)."""
    nbox = count_bbox(url, poly.bounds, verify)
    if nbox is not None and nbox == 0:
        return 0, 0, False
    if nbox is not None and nbox > max_fetch:
        return None, nbox, False
    feats, _, exceeded = query_layer(url, info, where="1=1", bbox_wgs84=poly.bounds, return_geometry=True, verify=verify)
    n = 0
    for f in feats:
        g = f.get("geometry")
        if not g:
            continue
        try:
            if shape(g).intersects(poly):
                n += 1
        except Exception:
            pass
    return n, len(feats), exceeded


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=".")
    ap.add_argument("--district-dir", default="Siddipet")
    ap.add_argument("--discovery-dir", required=True)
    ap.add_argument("--layers-json", default=None)
    ap.add_argument("--scan-dirs", nargs="*", default=["scripts", "Siddipet/Angadi_Kistapur/raw", "Siddipet/Damarakunta/raw", "docs"])
    ap.add_argument("--exclude", nargs="*", default=["Damarakunta"], help="villages (name text) left out of the shortlist; they are still checked")
    ap.add_argument("--include-nearby", action="store_true", help="also check villages of other mandals listed in the discovery folder")
    ap.add_argument("--max-fetch", type=int, default=2000, help="layers with more features than this in a village bbox are not downloaded (UNVERIFIED, bbox count reported)")
    ap.add_argument("--count-all-layers", action="store_true", help="also query layers that have no role (slow: includes cadastral and building layers)")
    ap.add_argument("--tag", default=None)
    ap.add_argument("--no-network", action="store_true", help="skip TGRAC queries (service-based inputs then become UNVERIFIED)")
    ap.add_argument("--insecure", action="store_true")
    a = ap.parse_args()
    verify = not a.insecure
    root = Path(a.root).resolve()
    dist = root / a.district_dir
    disc = Path(a.discovery_dir)
    disc = disc if disc.is_absolute() else root / disc
    gj = disc / "mandal_villages.geojson"
    if not gj.exists():
        sys.exit(f"{gj} not found: run discover_mandal_villages.py first")
    vill = gpd.read_file(gj).to_crs("EPSG:4326")
    if "in_target_mandal" in vill.columns and not a.include_nearby:
        vill = vill[vill.in_target_mandal.astype(str).str.lower().isin(["true", "1"])]
    out = dist / "_village_readiness" / (a.tag or "ready_" + stamp())
    if out.exists() and any(out.iterdir()):
        sys.exit(f"{out} already exists; choose another --tag (nothing is overwritten)")
    out.mkdir(parents=True, exist_ok=True)
    print(f"output folder: {out}\nread-only; HTTP GET only")

    folders = {norm(p.name): p for p in dist.iterdir() if p.is_dir() and not p.name.startswith("_")}
    dem_tifs = sorted(dist.glob("*/raw/dem/*.tif"))
    wc_tifs = sorted(dist.glob("*/raw/landcover/*.tif"))
    ref_area = None
    cand_csv = disc / "candidates.csv"
    cand = pd.read_csv(cand_csv).set_index("village_name") if cand_csv.exists() else None

    # TGRAC layers
    found = {}
    pinned = json.loads(Path(a.layers_json).read_text()) if a.layers_json else {}
    if not a.no_network:
        urls = scan_layer_urls([root / d for d in a.scan_dirs])
        pinned_urls = [x for v in pinned.values() for x in (v if isinstance(v, list) else [v])]
        for u in sorted(set(urls) | set(pinned_urls)):
            try:
                info = get_json(u, verify=verify)
                found[u] = dict(name=info.get("name"), geometryType=info.get("geometryType"), found_in=urls.get(u, ["--layers-json"]),
                                fields=[f.get("name") for f in (info.get("fields") or [])][:40], _info=info)
            except Exception as e:   # one odd layer must not stop the run; it is recorded and its role stays UNVERIFIED
                found[u] = dict(name=None, geometryType=None, error=repr(e), found_in=urls.get(u, []))
        save_json(out / "tgrac_layers_found.json", {u: {k: v for k, v in m.items() if k != "_info"} for u, m in found.items()})
        print(f"TGRAC layer URLs found in your files: {len(found)}")
    roles = infer_roles(found, pinned)
    for r, ms in roles.items():
        for m in ms:
            print(f"  role {r:<10} -> {m['url'].split('/services/')[-1]}   [{m['source'][:44]}]")
    for u, m in found.items():
        print(f"  layer {u.split('/services/')[-1]:<70} name={m.get('name')!r} geom={m.get('geometryType')} {('ERROR ' + str(m.get('error'))[:60]) if m.get('error') else ''}")

    rows, detail, layer_rows = [], {}, []
    role_urls = {m["url"] for ms in roles.values() for m in ms}
    for _, v in vill.iterrows():
        name = str(v.get("village_name"))
        poly = v.geometry
        bb = poly.envelope
        folder = folders.get(norm(name))
        d = {}
        r = dict(village=name, area_km2=(cand.loc[name, "area_km2"] if cand is not None and name in cand.index else None),
                 local_folder=str(folder) if folder else "")
        # boundary
        ok = poly is not None and not poly.is_empty and poly.is_valid and poly.area > 0
        r["boundary"], r["boundary_detail"] = (P, "polygon returned by the TGRAC service; valid; NOT compared with an independent boundary") if ok else (M, "no valid polygon")
        # imagery
        r["imagery_local"], r["imagery_local_detail"], d["imagery"] = check_imagery(folder, poly)
        r["imagery_obtainable"] = P if r["imagery_local"] == P else U
        r["imagery_obtainable_detail"] = ("local imagery already meets the test" if r["imagery_local"] == P else
                                          "not probed: Damarakunta's mosaic came from an ESRI World Imagery export (export_esri_damarakunta_full.py); "
                                          "use rights UNVERIFIED (DECISIONS row 15); needs your approval before any download")
        # DEM / land cover
        for key, tifs in (("dem", dem_tifs), ("worldcover", wc_tifs)):
            s = window_stats(tifs, bb, key)
            d[key] = s
            if s is None:
                r[key], r[key + "_detail"] = M, f"no {key} tile on disk contains the village bbox"
            elif "error" in s:
                r[key], r[key + "_detail"] = U, "could not read: " + s["error"]
            else:
                good = s["valid_share"] >= 0.99
                r[key] = P if good else U
                r[key + "_detail"] = f"{Path(s['file']).name}: {s['valid_share']:.1%} valid in the village bbox window, {s['res_m']} m cells" + ("" if good else "; test: >=99% valid")
        # TGRAC layers: count the features that intersect the polygon for EVERY layer found, so a wrong role guess is visible;
        # the role columns are then views over these counts.
        counts = {}
        print(f"[{len(rows) + 1}/{len(vill)}] {name}", flush=True)
        for u, meta in found.items():
            info = meta.get("_info")
            if a.no_network or info is None or not meta.get("geometryType") or (not a.count_all_layers and u not in role_urls):
                counts[u] = None
                continue
            try:
                n, nb, exc = count_in_polygon(u, info, poly, verify, a.max_fetch)
                counts[u] = dict(n=n, in_bbox=nb, exceeded=exc)
            except Exception as e:
                counts[u] = dict(error=repr(e))
            layer_rows.append(dict(village=name, layer_url=u, layer_name=meta.get("name"), geometryType=meta.get("geometryType"),
                                   intersecting=(counts[u] or {}).get("n"), in_bbox=(counts[u] or {}).get("in_bbox"),
                                   exceeded_transfer_limit=(counts[u] or {}).get("exceeded"), error=(counts[u] or {}).get("error")))
        for role in ("roads", "schools", "health", "anganwadi", "plinth"):
            col = "road_layer" if role == "roads" else role
            vals, parts = [], []
            for m in roles.get(role, []):
                c = counts.get(m["url"])
                lab = m["url"].split("/services/")[-1]
                if c is None:
                    vals.append(U); parts.append(f"{lab}: not queried")
                elif "error" in c:
                    vals.append(U); parts.append(f"{lab}: query failed {c['error'][:60]}")
                elif c["n"] is None:
                    vals.append(U); parts.append(f"{lab}: {c['in_bbox']} features in the bbox, more than --max-fetch, not clipped to the polygon")
                else:
                    vals.append(P if c["n"] > 0 else M)
                    parts.append(f"{lab}: {c['n']} intersect ({m['source'][:18]}{'; server limit hit' if c['exceeded'] else ''})")
            if role == "roads" and folder:       # a road file already on disk counts as a second, independent source
                for p in sorted((folder / "reference").glob("*road*.gpkg")):
                    try:
                        g = gpd.read_file(p).to_crs("EPSG:4326")
                        n = int(g.intersects(poly).sum())
                        vals.append(P if n else M); parts.append(f"local file {p.name}: {n} features intersect")
                    except Exception as e:
                        vals.append(U); parts.append(f"local file {p.name} unreadable: {e!r}"[:90])
            if not vals:
                r[col], r[col + "_detail"] = U, "no layer for this role and no local file"
            else:
                r[col] = P if P in vals else (U if U in vals else M)
                r[col + "_detail"] = " | ".join(parts)
            d[role] = parts
        fac = [r.get(k) for k in ("schools", "health", "anganwadi")]
        r["any_facility"] = P if P in fac else (U if U in fac else M)
        # blockers: what stops the existing pipeline (not evidence quality)
        bl = []
        if r["boundary"] != P:
            bl.append("boundary")
        if r["imagery_local"] != P:
            bl.append("0.6 m imagery: " + ("missing" if r["imagery_local"] == M else "present but fails the test"))
        for k in ("dem", "worldcover", "road_layer"):
            if r[k] != P:
                bl.append(f"{k} {r[k].lower()}")
        if r["any_facility"] != P:
            bl.append("no facility targets confirmed (not blocking: clusters can still be planned)")
        r["blockers"] = "; ".join(bl)
        sc = 2 * sum(r[k] == P for k in ("boundary", "dem", "worldcover", "road_layer")) + (1 if r["any_facility"] == P else 0) + (3 if r["imagery_local"] == P else 0)
        ar = r["area_km2"]
        if ar is not None and cand is not None and "area_vs_reference" in cand.columns:
            ratio = cand.loc[name, "area_vs_reference"]
            sc += 1 if (pd.notna(ratio) and 0.5 <= ratio <= 2.0) else 0
        r["score"] = sc
        rows.append(r)
        detail[name] = d
    df = pd.DataFrame(rows).sort_values(["score", "village"], ascending=[False, True])
    df.to_csv(out / "village_readiness.csv", index=False)
    save_json(out / "village_readiness_detail.json", detail)
    pd.DataFrame(layer_rows).to_csv(out / "tgrac_layer_counts.csv", index=False)

    short = df[~df.village.apply(lambda s: any(e.lower() in s.lower() for e in a.exclude))].head(5)
    lines = ["# Village shortlist (heuristic, generated by village_readiness.py)", "",
             "Ranking rule: 2 points for each of boundary / DEM / WorldCover / road layer that is PRESENT, 1 for any facility layer PRESENT, "
             "3 for local imagery PRESENT, 1 if the village area is 0.5-2 times Damarakunta's. This is a data-availability ranking only. "
             "It says nothing about suitability for the research question, and 'PRESENT' means the test in the CSV was met, not that the data are correct.", ""]
    for _, r in short.iterrows():
        lines += [f"## {r.village} (score {r.score}, area {r.area_km2} km2)", f"Blockers: {r.blockers or 'none found'}", ""]
    lines += ["Not checked by this script: imagery licence, facility accuracy, road accuracy, whether the segmentation model works on the village.",
              "No imagery was downloaded and no inference was started."]
    (out / "recommendation.md").write_text("\n".join(lines), encoding="utf-8")
    save_json(out / "provenance.json", dict(created=utc_now(), discovery_dir=str(disc), layers_pinned=pinned,
                                            roles={k: v for k, v in roles.items()}, dem_tiles=[str(p) for p in dem_tifs],
                                            worldcover_tiles=[str(p) for p in wc_tifs], network=not a.no_network))
    show = ["village", "score", "boundary", "imagery_local", "dem", "worldcover", "road_layer", "schools", "health", "anganwadi", "plinth"]
    short_df = df[show].copy()
    for c_ in show[2:]:
        short_df[c_] = short_df[c_].map({P: "P", M: "M", U: "U"})
    print("\nP = PRESENT, M = MISSING, U = UNVERIFIED (details in the CSV)\n" + short_df.to_string(index=False))
    print(f"\ntable: {out / 'village_readiness.csv'}\nshortlist: {out / 'recommendation.md'}")


if __name__ == "__main__":
    main()
