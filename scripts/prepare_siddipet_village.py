"""
prepare_siddipet_village.py

Builds the study area for one village and collects ONLY the data inside the
village + buffer. Raw downloads are saved as received and never overwritten.

Steps
  1. create the village folder structure
  2. read the village boundary, pick a UTM CRS from its centroid, buffer (m)
  3. query TGRAC feature layers by the buffer's bounding box (optional)
       raw/tgrac/<name>_<stamp>.json      server response, as received
       reference/<name>.gpkg              clipped to buffer, EPSG:4326
       aligned/<name>_utm.gpkg            same, in village UTM
  4. clip local vector files you already downloaded (optional, e.g. OSM, PMGSY)
  5. mosaic + clip + reproject SRTM tiles to UTM, derive slope % (optional)
  6. write study_area/study_area_config.json and append study_area/sources.json

Examples (from Telangana_Rural_Project\\scripts):
  python prepare_siddipet_village.py ^
     --boundary ..\\Siddipet\\Angadi_Kistapur\\raw\\tgrac_master_admin\\village_boundary_<stamp>.geojson

  python prepare_siddipet_village.py --boundary <file> ^
     --tgrac-layer schools=https://tgrac.telangana.gov.in/arcgis/rest/services/SchoolGIS_Folder/Schools/MapServer/<id> ^
     --dem ..\\Siddipet\\Angadi_Kistapur\\raw\\srtm\\n17_e078_1arc_v3.tif

Layer IDs (<id>) come from opening each MapServer URL in a browser; do not guess them.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.merge import merge
from rasterio.warp import calculate_default_transform, reproject, transform_bounds

from tgrac_rest import RestError, get_json, query_layer, save_json, stamp, utc_now

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VILLAGE_DIR = ROOT / "Siddipet" / "Angadi_Kistapur"
SUBDIRS = ["study_area", "raw", "reference", "aligned", "predictions", "derived", "results"]


def utm_epsg(lon: float, lat: float) -> int:
    zone = int((lon + 180) // 6) + 1
    return (32600 if lat >= 0 else 32700) + zone


def parse_pairs(pairs):
    out = {}
    for p in pairs or []:
        if "=" not in p:
            sys.exit(f"Expected NAME=VALUE, got: {p}")
        k, v = p.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def append_sources(path: Path, entries: list[dict]):
    existing = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    existing.extend(entries)
    save_json(path, existing)


def clip_and_save(gdf, buffer_wgs84, utm, name, vdir):
    gdf = gdf.to_crs(4326) if gdf.crs else gdf.set_crs(4326)
    clipped = gpd.clip(gdf, buffer_wgs84)
    ref_path = vdir / "reference" / f"{name}.gpkg"
    utm_path = vdir / "aligned" / f"{name}_utm.gpkg"
    if len(clipped):
        clipped.to_file(ref_path, driver="GPKG")
        clipped.to_crs(utm).to_file(utm_path, driver="GPKG")
    return len(gdf), len(clipped), ref_path, utm_path


def prepare_dem(dem_paths, buffer_utm_gdf, utm, res, vdir):
    srcs = [rasterio.open(p) for p in dem_paths]
    try:
        dem_crs = srcs[0].crs
        bounds = transform_bounds(f"EPSG:{utm}", dem_crs, *buffer_utm_gdf.total_bounds)
        pad = 0.005 if dem_crs.is_geographic else 500
        bounds = (bounds[0] - pad, bounds[1] - pad, bounds[2] + pad, bounds[3] + pad)
        mosaic, m_transform = merge(srcs, bounds=bounds)
        nodata = srcs[0].nodata
    finally:
        for s in srcs:
            s.close()

    left, bottom, right, top = buffer_utm_gdf.total_bounds
    width, height = int(np.ceil((right - left) / res)), int(np.ceil((top - bottom) / res))
    dst_transform = rasterio.transform.from_origin(left, top, res, res)
    dem_utm = np.full((height, width), -9999.0, dtype="float32")
    reproject(mosaic[0].astype("float32"), dem_utm, src_transform=m_transform,
              src_crs=dem_crs, src_nodata=nodata, dst_transform=dst_transform,
              dst_crs=f"EPSG:{utm}", dst_nodata=-9999.0, resampling=Resampling.bilinear)

    profile = {"driver": "GTiff", "height": height, "width": width, "count": 1,
               "dtype": "float32", "crs": f"EPSG:{utm}", "transform": dst_transform,
               "nodata": -9999.0, "compress": "deflate"}
    dem_path = vdir / "aligned" / "dem_utm.tif"
    with rasterio.open(dem_path, "w", **profile) as dst:
        dst.write(dem_utm, 1)

    z = np.where(dem_utm == -9999.0, np.nan, dem_utm)
    dz_dy, dz_dx = np.gradient(z, res, res)
    slope_pct = (np.hypot(dz_dx, dz_dy) * 100).astype("float32")
    slope_pct = np.where(np.isnan(slope_pct), -9999.0, slope_pct)
    slope_path = vdir / "aligned" / "slope_percent_utm.tif"
    with rasterio.open(slope_path, "w", **profile) as dst:
        dst.write(slope_pct, 1)
    return dem_path, slope_path


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--boundary", type=Path, required=True,
                    help="village boundary file (GeoJSON/GPKG/SHP) with a CRS")
    ap.add_argument("--feature-index", type=int,
                    help="use only this feature if the file holds several")
    ap.add_argument("--village-dir", type=Path, default=DEFAULT_VILLAGE_DIR)
    ap.add_argument("--buffer-m", type=float, default=500.0)
    ap.add_argument("--tgrac-layer", action="append",
                    help="NAME=URL of a TGRAC feature layer (…/MapServer/<id>); repeatable")
    ap.add_argument("--local-vector", action="append",
                    help="NAME=PATH of a vector file you downloaded; repeatable")
    ap.add_argument("--dem", action="append", type=Path,
                    help="SRTM GeoTIFF tile(s) covering the village; repeatable")
    ap.add_argument("--dem-res", type=float, default=30.0, help="output DEM pixel size (m)")
    ap.add_argument("--insecure", action="store_true")
    args = ap.parse_args()
    vdir, ts, verify = args.village_dir, stamp(), not args.insecure

    for d in SUBDIRS:
        (vdir / d).mkdir(parents=True, exist_ok=True)
    print(f"[1] folders ready under {vdir}")

    b = gpd.read_file(args.boundary)
    if b.crs is None:
        sys.exit("Boundary has no CRS - refusing to guess. Fix the source file.")
    if args.feature_index is not None:
        b = b.iloc[[args.feature_index]]
    elif len(b) > 1:
        sys.exit(f"Boundary has {len(b)} features; pass --feature-index.")
    b_wgs = b.to_crs(4326)
    c = b_wgs.geometry.union_all().centroid
    utm = utm_epsg(c.x, c.y)
    b_utm = b.to_crs(utm)
    buf_utm = gpd.GeoDataFrame(geometry=[b_utm.geometry.union_all().buffer(args.buffer_m)],
                               crs=utm)
    buf_wgs = buf_utm.to_crs(4326)
    sa = vdir / "study_area" / "study_area.gpkg"
    b_wgs.to_file(sa, layer="boundary_wgs84", driver="GPKG")
    b_utm.to_file(sa, layer="boundary_utm", driver="GPKG")
    buf_wgs.to_file(sa, layer="buffer_wgs84", driver="GPKG")
    buf_utm.to_file(sa, layer="buffer_utm", driver="GPKG")
    area_ha = float(b_utm.area.sum() / 10_000)
    print(f"[2] UTM EPSG:{utm}; village area {area_ha:.1f} ha; buffer {args.buffer_m:.0f} m")

    sources, layer_log = [], []
    bbox = tuple(buf_wgs.total_bounds)
    for name, url in parse_pairs(args.tgrac_layer).items():
        try:
            info = get_json(url, verify=verify)
            if info.get("type") != "Feature Layer":
                print(f"[3] {name}: skipped, layer type is {info.get('type')!r}")
                continue
            feats, pages, exceeded = query_layer(url, info, bbox_wgs84=bbox, verify=verify)
        except RestError as exc:
            print(f"[3] {name}: FAILED {exc}")
            layer_log.append({"name": name, "url": url, "error": str(exc)})
            continue
        save_json(vdir / "raw" / "tgrac" / f"{name}_{ts}.json", pages)
        gdf = (gpd.GeoDataFrame.from_features(feats, crs=4326) if feats
               else gpd.GeoDataFrame(geometry=[], crs=4326))
        n_all, n_clip, ref, _ = clip_and_save(gdf, buf_wgs, utm, name, vdir)
        warn = " (TRANSFER LIMIT HIT - results incomplete)" if exceeded else ""
        print(f"[3] {name}: {n_all} in bbox, {n_clip} inside buffer{warn}")
        sources.append({"name": name, "type": "TGRAC REST query", "url": url,
                        "retrieved_at_utc": utc_now(), "features_in_bbox": n_all,
                        "features_in_buffer": n_clip, "exceeded_limit": exceeded,
                        "copyrightText": info.get("copyrightText") or "not stated by service",
                        "licence": "not stated; permission requested/pending",
                        "raw_file": f"raw/tgrac/{name}_{ts}.json", "clipped_file": str(ref)})

    for name, p in parse_pairs(args.local_vector).items():
        gdf = gpd.read_file(p, bbox=buf_wgs)  # reads only features near the village
        n_all, n_clip, ref, _ = clip_and_save(gdf, buf_wgs, utm, name, vdir)
        print(f"[4] {name}: {n_clip} features inside buffer")
        sources.append({"name": name, "type": "local file", "path": str(Path(p).resolve()),
                        "prepared_at_utc": utc_now(), "features_in_buffer": n_clip,
                        "licence": "record from the provider's page"})

    if args.dem:
        dem_path, slope_path = prepare_dem(args.dem, buf_utm, utm, args.dem_res, vdir)
        print(f"[5] DEM -> {dem_path.name}, slope -> {slope_path.name} ({args.dem_res} m)")
        sources.append({"name": "srtm", "type": "local file",
                        "paths": [str(p.resolve()) for p in args.dem],
                        "prepared_at_utc": utc_now(),
                        "licence": "SRTM: public domain (USGS), credit requested"})

    config = {"village_dir": str(vdir.resolve()), "boundary_source": str(args.boundary.resolve()),
              "utm_epsg": utm, "buffer_m": args.buffer_m, "village_area_ha": area_ha,
              "buffer_bbox_wgs84": list(bbox), "prepared_at_utc": utc_now(),
              "note": "Image grid alignment happens later, once imagery is available. "
                      "The LoveDA 0.55 m/pixel factor is never used here."}
    save_json(vdir / "study_area" / "study_area_config.json", config)
    append_sources(vdir / "study_area" / "sources.json", sources)
    if layer_log:
        save_json(vdir / "study_area" / f"prepare_errors_{ts}.json", layer_log)
    print(f"[6] config + sources written in {vdir / 'study_area'}")


if __name__ == "__main__":
    main()
