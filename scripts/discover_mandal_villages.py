#!/usr/bin/env python
"""discover_mandal_villages.py - READ-ONLY village discovery for Phase C.

Lists the villages of one mandal from the TGRAC Master Administrative Boundary service (HTTP GET only), computes
simple size figures, and checks what is already on disk for each village. It does NOT download imagery, create village
folders, run inference or plan anything.

Output goes to a NEW folder (never reused):
    Siddipet/_village_discovery/<tag>/
        layers_overview.json        every feature layer of the service with its geometry type and fields
        raw_query_pages.json        the server responses exactly as parsed
        mandal_villages.geojson     village polygons found (EPSG:4326)
        candidates.csv              one row per village: area, size vs the reference village, local data status
        provenance.json             service URL, query, time, counts, files checked

What 'candidate' means here: a village polygon returned by the service. Whether imagery, facilities or roads exist for a
village is NOT known from this script; the columns say only what is on this computer. Boundary provenance stays UNVERIFIED
until compared with an independent source (for example an LGD export).

Run from the project root:
    .venv\\Scripts\\python.exe scripts\\discover_mandal_villages.py --mandal MARKOOK
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd
import rasterio
from shapely.geometry import box

from tgrac_rest import RestError, get_json, query_layer, save_json, stamp, utc_now

CRS_UTM = "EPSG:32644"
DEFAULT_SERVICE = ("https://tgrac.telangana.gov.in/arcgis/rest/services/"
                   "Master_Administrative_Folder/Master_Administrative_Boundary/MapServer")
STRING = "esriFieldTypeString"


def norm(s):
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def pick_field(fields, *needles):
    for f in fields:
        if f.get("type") != STRING:
            continue
        n = f["name"].upper()
        if any(k in n for k in needles):
            return f["name"]
    return None


def tile_boxes(village_root, subdir, patterns):
    """bounds (lon/lat) of raster tiles already on disk, as {path: shapely box}"""
    out = {}
    for pat in patterns:
        for p in village_root.glob(f"*/raw/{subdir}/{pat}"):
            try:
                with rasterio.open(p) as src:
                    if src.crs and src.crs.to_epsg() == 4326:
                        out[str(p)] = box(*src.bounds)
            except Exception:
                pass
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=".")
    ap.add_argument("--district-dir", default="Siddipet")
    ap.add_argument("--service", default=DEFAULT_SERVICE)
    ap.add_argument("--mandal", default="MARKOOK", help="text matched (LIKE, case-insensitive) in the mandal field")
    ap.add_argument("--ref-boundary", default="Siddipet/Damarakunta/study_area/damarakunta_boundary.gpkg")
    ap.add_argument("--layer-id", type=int, default=None, help="only use this layer id of the service (for example 27 in Administrative_Information_System)")
    ap.add_argument("--nearby-km", type=float, default=0.0,
                    help="also list villages of OTHER mandals whose polygons intersect the target mandal's envelope enlarged by this many km")
    ap.add_argument("--tag", default=None)
    ap.add_argument("--insecure", action="store_true", help="skip TLS verification (as in the earlier TGRAC scripts); use only if the normal call fails")
    a = ap.parse_args()
    verify = not a.insecure

    root = Path(a.root).resolve()
    dist = root / a.district_dir
    tag = a.tag or "disc_" + stamp()
    out = dist / "_village_discovery" / tag
    if out.exists() and any(out.iterdir()):
        sys.exit(f"{out} already exists; choose another --tag (nothing is overwritten)")
    out.mkdir(parents=True, exist_ok=True)
    print(f"output folder: {out}\nread-only: HTTP GET requests only")

    try:
        svc = get_json(a.service, verify=verify)
    except RestError as e:
        sys.exit(f"cannot read the service: {e}")
    overview, raw_pages, found = [], [], []
    for lyr in svc.get("layers", []):
        if lyr.get("subLayerIds"):
            continue
        if a.layer_id is not None and lyr["id"] != a.layer_id:
            continue
        url = f"{a.service}/{lyr['id']}"
        try:
            info = get_json(url, verify=verify)
        except RestError as e:
            overview.append(dict(id=lyr["id"], name=lyr["name"], error=str(e)))
            continue
        if info.get("type") != "Feature Layer":
            continue
        fields = info.get("fields") or []
        mf, vf = pick_field(fields, "MANDAL"), pick_field(fields, "VILLAGE", "VIL_NAME")
        overview.append(dict(id=lyr["id"], name=lyr["name"], geometryType=info.get("geometryType"),
                             mandal_field=mf, village_field=vf, fields=[f["name"] for f in fields]))
        if info.get("geometryType") != "esriGeometryPolygon" or not mf or not vf:
            continue
        where = f"UPPER({mf}) LIKE '%{a.mandal.upper()}%'"
        try:
            feats, pages, exceeded = query_layer(url, info, where=where, return_geometry=True, verify=verify)
        except Exception as e:
            overview[-1]["query_error"] = repr(e)
            continue
        raw_pages.append(dict(layer_id=lyr["id"], where=where, exceeded_transfer_limit=exceeded, pages=pages))
        print(f"layer {lyr['id']} {lyr['name']!r}: {len(feats)} polygons for mandal ~ {a.mandal} (exceeded limit: {exceeded})")
        if feats:
            g = gpd.GeoDataFrame.from_features(feats, crs="EPSG:4326")
            g["layer_id"], g["layer_name"], g["village_field"], g["mandal_field"] = lyr["id"], lyr["name"], vf, mf
            g["in_target_mandal"] = True
            found.append(g)
            if a.nearby_km > 0:
                env = gpd.GeoSeries([box(*g.to_crs(CRS_UTM).total_bounds)], crs=CRS_UTM).buffer(a.nearby_km * 1000)
                nb = tuple(env.to_crs("EPSG:4326").total_bounds)
                f2, p2, ex2 = query_layer(url, info, where="1=1", bbox_wgs84=nb, return_geometry=True, verify=verify)
                raw_pages.append(dict(layer_id=lyr["id"], where="1=1", bbox_wgs84=nb, exceeded_transfer_limit=ex2, pages=p2))
                if f2:
                    g2 = gpd.GeoDataFrame.from_features(f2, crs="EPSG:4326")
                    g2 = g2[~g2[mf].astype(str).str.upper().str.contains(a.mandal.upper(), regex=False)].copy()
                    g2["layer_id"], g2["layer_name"], g2["village_field"], g2["mandal_field"] = lyr["id"], lyr["name"], vf, mf
                    g2["in_target_mandal"] = False
                    found.append(g2)
                    print(f"  nearby (other mandals, within {a.nearby_km:g} km): {len(g2)} polygons (exceeded limit: {ex2})")
    save_json(out / "layers_overview.json", overview)
    save_json(out / "raw_query_pages.json", raw_pages)
    if not found:
        print("No polygon layer with both a mandal and a village field returned features. See layers_overview.json.")
        (out / "provenance.json").write_text(json.dumps(dict(created=utc_now(), service=a.service, mandal=a.mandal, result="NO_MATCH"), indent=2))
        sys.exit(2)

    g = pd.concat(found, ignore_index=True)
    g = g[g.geometry.notna() & ~g.geometry.is_empty].copy()
    g["village_name"] = [r[r["village_field"]] for _, r in g.iterrows()]
    g["mandal_value"] = [r[r["mandal_field"]] for _, r in g.iterrows()]
    u = g.to_crs(CRS_UTM)
    g["area_km2"] = (u.area / 1e6).round(3)
    c = gpd.GeoSeries(u.geometry.centroid, crs=CRS_UTM).to_crs("EPSG:4326")
    g["centroid_lon"], g["centroid_lat"] = c.x.round(5), c.y.round(5)
    bb = u.geometry.bounds
    g["bbox_w_km"], g["bbox_h_km"] = ((bb.maxx - bb.minx) / 1e3).round(2), ((bb.maxy - bb.miny) / 1e3).round(2)

    ref_area = None
    rp = root / a.ref_boundary
    if rp.exists():
        ref_area = float(gpd.read_file(rp).to_crs(CRS_UTM).geometry.union_all().area / 1e6)
        g["area_vs_reference"] = (g.area_km2 / ref_area).round(2)
    local = {norm(p.name): p for p in dist.iterdir() if p.is_dir() and not p.name.startswith("_")} if dist.exists() else {}
    dem_tiles = tile_boxes(dist, "dem", ["*.tif"])
    wc_tiles = tile_boxes(dist, "landcover", ["*.tif"])
    rows = []
    for _, r in g.iterrows():
        nm = norm(r.village_name)
        folder = local.get(nm)
        has_mosaic = bool(folder and list((folder / "aligned").glob("*mosaic*0p6m*.tif"))) if folder else False
        vb = r.geometry.envelope
        rows.append(dict(
            village_name=r.village_name, mandal=r.mandal_value, in_target_mandal=bool(r.in_target_mandal), layer_id=r.layer_id, area_km2=r.area_km2, area_vs_reference=r.get("area_vs_reference"),
            population_TOT_P=r.get("TOT_P"), households_No_HH=r.get("No_HH"),
            bbox_w_km=r.bbox_w_km, bbox_h_km=r.bbox_h_km, centroid_lon=r.centroid_lon, centroid_lat=r.centroid_lat,
            local_folder=str(folder) if folder else "", has_0p6m_mosaic=has_mosaic,
            dem_tile_on_disk_covers=next((Path(k).name for k, b in dem_tiles.items() if b.contains(vb)), ""),
            worldcover_tile_on_disk_covers=next((Path(k).name for k, b in wc_tiles.items() if b.contains(vb)), ""),
            other_attributes=json.dumps({k: (None if pd.isna(v) else v) for k, v in r.items()
                                         if k not in ("geometry", "village_name", "mandal_value", "in_target_mandal", "layer_id", "layer_name", "village_field", "mandal_field",
                                                      "area_km2", "area_vs_reference", "bbox_w_km", "TOT_P", "No_HH", "bbox_h_km", "centroid_lon", "centroid_lat")},
                                        default=str)))
    df = pd.DataFrame(rows).sort_values("village_name")
    df.to_csv(out / "candidates.csv", index=False)
    g.drop(columns=[x for x in g.columns if x.startswith("area_vs")], errors="ignore").to_file(out / "mandal_villages.geojson", driver="GeoJSON")
    save_json(out / "provenance.json", dict(
        created=utc_now(), service=a.service, mandal_query=a.mandal, layers_used=sorted(set(map(int, g.layer_id))),
        villages_returned=int(len(df)), reference_village_area_km2=ref_area, dem_tiles_checked=list(dem_tiles), worldcover_tiles_checked=list(wc_tiles),
        boundary_status="UNVERIFIED: returned by the TGRAC service; not compared with an independent boundary source",
        not_known_from_this_script="imagery availability, imagery licence, road/facility layers, building counts"))
    print(f"\n{len(df)} villages; table: {out / 'candidates.csv'}")
    show = ["village_name", "area_km2", "population_TOT_P", "households_No_HH", "area_vs_reference", "local_folder", "has_0p6m_mosaic", "dem_tile_on_disk_covers", "worldcover_tile_on_disk_covers"]
    print(df[show].to_string(index=False))


if __name__ == "__main__":
    main()
