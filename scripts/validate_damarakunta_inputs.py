#!/usr/bin/env python
"""validate_damarakunta_inputs.py - Stage A: READ-ONLY validation of the inputs listed in configs/damarakunta.json.

Opens every path in the config's "paths" block (the source of truth; nothing is guessed), and records for rasters: CRS, size,
resolution, bounds, dtype, bands, nodata, valid-pixel share (decimated read), overlap with the village polygon; for vectors:
every layer's CRS, feature count, geometry types, invalid/empty/duplicate geometries, features intersecting the village
polygon, share of features outside it.  It states measurements, not accuracy.  Nothing is modified; no network access.
Output: NEW folder <results>/stageA_input_validation/<tag>/ (refuses to reuse):  inputs_validation.json, inputs_validation.csv, provenance.json

Run from D:\\Telangana_Rural_Project:
  .venv\\Scripts\\python.exe scripts\\validate_damarakunta_inputs.py --config configs\\damarakunta.json
"""
import argparse, hashlib, json, os, sys, platform
from datetime import datetime, timezone
from pathlib import Path
import numpy as np, pandas as pd, geopandas as gpd, rasterio
from shapely.geometry import box

RASTER = {".tif", ".tiff"}
VECTOR = {".gpkg", ".geojson", ".json", ".shp"}


def clean(o):
    if isinstance(o, dict): return {k: clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)): return [clean(v) for v in o]
    if isinstance(o, (np.integer,)): return int(o)
    if isinstance(o, (np.floating, float)): return None if not np.isfinite(o) else float(o)
    if isinstance(o, (np.bool_,)): return bool(o)
    return o


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def raster_info(p, poly_utm, crs_exp):
    with rasterio.open(p) as s:
        d = dict(kind="raster", crs=str(s.crs), epsg=s.crs.to_epsg() if s.crs else None, width=s.width, height=s.height, bands=s.count,
                 res=list(s.res), bounds=list(s.bounds), dtype=s.dtypes[0], nodata=s.nodata, transform=list(s.transform)[:6])
        f = max(1, int(max(s.width, s.height) / 2000))
        a = s.read(out_shape=(s.count, max(1, s.height // f), max(1, s.width // f)), masked=True)
        d["decimation"] = f
        d["valid_share_all_pixels"] = float(1 - np.ma.getmaskarray(a).all(axis=0).mean())
        if s.count >= 3 and s.nodata is None:
            raw = np.asarray(a.data[:3])
            d["all_zero_share_rgb"] = float((raw == 0).all(axis=0).mean())
        if s.crs is not None and poly_utm is not None:
            pb = gpd.GeoSeries([poly_utm], crs=crs_exp).to_crs(s.crs).iloc[0]
            rb = box(*s.bounds)
            d["village_bbox_inside_raster_bounds"] = bool(rb.contains(box(*pb.bounds)))
            d["village_polygon_share_inside_raster_bounds"] = float(pb.intersection(rb).area / pb.area)
            if f >= 1 and a.shape[0] >= 1:
                from rasterio.features import geometry_mask
                tr = s.transform * rasterio.Affine.scale(s.width / a.shape[2], s.height / a.shape[1])
                inside = ~geometry_mask([pb], out_shape=a.shape[1:], transform=tr)
                valid = ~np.ma.getmaskarray(a).all(axis=0)
                if s.count >= 3 and s.nodata is None:
                    valid = valid & ~(np.asarray(a.data[:3]) == 0).all(axis=0)
                d["valid_share_inside_polygon"] = float((valid & inside).sum() / max(1, inside.sum()))
        d["class_values_if_small_int"] = None
        if s.count == 1 and s.dtypes[0] in ("uint8", "int16", "uint16"):
            u = np.unique(a.compressed())
            if len(u) <= 40:
                d["class_values_if_small_int"] = [int(x) for x in u]
    return d


def vector_info(p, poly_utm, crs_exp, layer):
    import fiona
    layers = fiona.listlayers(p) if p.suffix == ".gpkg" else [None]
    out = dict(kind="vector", layers_in_file=layers, layer_reports=[])
    for ly in layers:
        g = gpd.read_file(p, layer=ly) if ly else gpd.read_file(p)
        r = dict(layer=ly, requested=(ly == layer), n=len(g), crs=str(g.crs), epsg=g.crs.to_epsg() if g.crs else None,
                 geometry_types=g.geom_type.value_counts().to_dict(), columns=[c for c in g.columns if c != "geometry"][:30])
        if len(g) and g.crs is not None:
            u = g.to_crs(crs_exp)
            r["invalid"] = int((~u.is_valid).sum()); r["empty"] = int(u.is_empty.sum())
            r["duplicate_geometries"] = int(u.geometry.apply(lambda x: x.wkb if x is not None else b"").duplicated().sum())
            if poly_utm is not None:
                r["intersect_village"] = int(u.intersects(poly_utm).sum()); r["outside_village"] = int((~u.intersects(poly_utm)).sum())
                if u.geom_type.isin(["LineString", "MultiLineString"]).all():
                    r["length_m_total"] = float(u.length.sum()); r["length_m_inside_village"] = float(u.intersection(poly_utm).length.sum())
                r["bounds_utm"] = list(u.total_bounds)
        out["layer_reports"].append(r)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", required=True); ap.add_argument("--tag", default=None)
    ap.add_argument("--hash", action="store_true", help="also SHA-256 each input (slow for the mosaic)")
    a = ap.parse_args()
    cfg = json.loads(Path(a.config).read_text(encoding="utf-8")); root = Path(cfg["root"]); crs = cfg.get("crs", "EPSG:32644")
    def res(v): return Path(v) if os.path.isabs(v) or ":" in v[:3] else root / v
    paths = {k: v for k, v in cfg["paths"].items() if isinstance(v, str) and not k.endswith(("_layer", "_name"))}
    out = Path(cfg["paths"].get("results_dir", root / "Siddipet" / "Damarakunta" / "results")); out = (res(str(out)) if not out.is_absolute() else out) / "stageA_input_validation" / (a.tag or "stageA_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    if out.exists() and any(out.iterdir()):
        sys.exit(f"{out} exists; choose another --tag")
    out.mkdir(parents=True)
    poly = None
    bp = paths.get("boundary")
    if bp and res(bp).exists():
        bl = cfg["paths"].get("boundary_layer")
        bg = gpd.read_file(res(bp), layer=bl) if bl else gpd.read_file(res(bp))
        poly = bg.to_crs(crs).geometry.union_all()
    rep, rows = {}, []
    for k, v in paths.items():
        p = res(v); e = dict(config_key=k, path=str(p), exists=p.exists())
        if p.is_dir():
            e.update(kind="directory", entries=len(list(p.iterdir())))
        elif p.exists():
            e["bytes"] = p.stat().st_size
            if a.hash: e["sha256"] = sha(p)
            try:
                if p.suffix.lower() in RASTER: e.update(raster_info(p, poly, crs))
                elif p.suffix.lower() in VECTOR: e.update(vector_info(p, poly, crs, cfg["paths"].get(k + "_layer")))
                else: e["kind"] = "other (not opened)"
            except Exception as ex:
                e["open_error"] = repr(ex)
        rep[k] = e
        rows.append(dict(key=k, exists=e["exists"], kind=e.get("kind"), crs=e.get("crs"), res=e.get("res"), size=(e.get("width"), e.get("height")),
                         valid_in_polygon=e.get("valid_share_inside_polygon"), village_in_bounds=e.get("village_polygon_share_inside_raster_bounds"),
                         open_error=e.get("open_error"), path=str(p)))
    (out / "inputs_validation.json").write_text(json.dumps(clean(rep), indent=1))
    pd.DataFrame(rows).to_csv(out / "inputs_validation.csv", index=False)
    (out / "provenance.json").write_text(json.dumps(dict(created=datetime.now(timezone.utc).isoformat(), config=str(Path(a.config).resolve()), python=sys.version,
        platform=platform.platform(), rasterio=rasterio.__version__, geopandas=gpd.__version__, crs_expected=crs, boundary_status="UNVERIFIED (TGRAC polygon)",
        imagery_licence="UNVERIFIED", scope="measurements only; no accuracy claim"), indent=1))
    pd.set_option("display.width", 250, "display.max_colwidth", 60)
    print(pd.DataFrame(rows).drop(columns=["path"]).to_string(index=False)); print("\nfull detail:", out)
    for k, e in rep.items():
        for r in e.get("layer_reports", []):
            if r.get("requested") or len(e["layer_reports"]) == 1:
                print(f"  {k}[{r['layer']}]: n={r['n']} epsg={r['epsg']} types={r['geometry_types']} invalid={r.get('invalid')} dup={r.get('duplicate_geometries')} intersect_village={r.get('intersect_village')} outside={r.get('outside_village')}")


if __name__ == "__main__":
    main()
