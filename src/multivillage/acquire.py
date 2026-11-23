"""Step 1 of the shared pipeline: administrative boundary, existing roads, facilities and building footprints for one village.

Everything is read from open sources that are reachable without credentials. Each layer is clipped to the village polygon, written to
data/villages/<id>/ (git-ignored, regenerable) and recorded in the input manifest with URL, release, licence and SHA-256.
"""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import yaml
from shapely import from_wkb
from shapely.geometry import box

from src.utils import data_downloader_helper as dl
from src.multivillage.sources import Source

REPO = Path(__file__).resolve().parents[2]
CRS_WORK = "EPSG:32644"
OV_HTTPS = "https://overturemaps-us-west-2.s3.amazonaws.com/release/{rel}/theme={theme}/type={typ}/"


def load_cfg(village_id: str) -> dict:
    common = yaml.safe_load((REPO / "configs/multivillage/common.yaml").read_text())
    v = yaml.safe_load((REPO / f"configs/multivillage/villages/{village_id}.yaml").read_text())
    return {**common, "village": v}


def data_dir(cfg) -> Path:
    d = REPO / "data" / "villages" / cfg["village"]["id"]
    d.mkdir(parents=True, exist_ok=True)
    return d


def overture(cfg, theme, typ, bounds_wgs84, cols):
    dl.PINNED_RELEASE = cfg["overture_release"]
    df, rel = dl.overture_table(theme, typ, tuple(bounds_wgs84), cols)
    return df, rel


def _geom(df, crs=4326):
    return gpd.GeoDataFrame(df.drop(columns=["geometry"]), geometry=[from_wkb(x) for x in df.geometry], crs=crs)


def polygon_file_boundary(cfg) -> tuple:
    """Study area = a village / town polygon supplied as a file (GeoJSON / GPKG, any CRS) plus an optional `<name>.provenance.json` sidecar.
    The polygon is used exactly as given (no clipping, no buffering); it is only checked against the mandal polygon so a wrong pick is noticed."""
    import json
    from shapely.validation import make_valid
    v = cfg["village"]
    bf = REPO / v["boundary_file"]
    if not bf.exists():
        raise FileNotFoundError(f"{bf} not found. Fetch the true village / town polygon on a PC with internet first: python scripts/propose_aoi.py --village {v['id']}  (review the candidates), "
                                f"then python scripts/propose_aoi.py --village {v['id']} --pick N")
    g = gpd.read_file(bf)
    g = g.set_crs(4326) if g.crs is None else g
    cell = make_valid(g.to_crs(CRS_WORK).geometry.union_all())
    prov_f = bf.with_name(bf.stem + ".provenance.json")
    prov = json.loads(prov_f.read_text(encoding="utf-8")) if prov_f.exists() else {}
    inside = None
    try:                                                    # consistency check against the mandal polygon (cached geoBoundaries ADM3; skipped offline)
        adm2 = gpd.read_file(dl.http_download(dl.GB_BASE.format(lvl="ADM2"), dl.CACHE / "gb_IND_ADM2.geojson"))
        adm3 = gpd.read_file(dl.http_download(dl.GB_BASE.format(lvl="ADM3"), dl.CACHE / "gb_IND_ADM3.geojson"))
        dist = adm2[adm2.shapeName == v["district"]].geometry.iloc[0]
        m = adm3[(adm3.shapeName == v["adm3_name"]) & adm3.representative_point().within(dist)].to_crs(CRS_WORK).geometry.iloc[0]
        inside = float(cell.intersection(m).area / cell.area)
        mode = v.get("mandal_check", "strict")
        if inside < 0.9 and mode == "strict":
            raise ValueError(f"only {inside:.0%} of the polygon lies inside the {v['adm3_name']} mandal: wrong feature picked?")
        if inside < 0.9 and mode == "warn":
            print(f"note: only {inside:.0%} of the polygon lies inside the 2018 {v['adm3_name']} mandal (expected: the current town boundary extends beyond it)")
    except (OSError, IndexError):
        pass
    rec = dict(method=f"polygon file {bf.name}" + (f" ({prov.get('source')})" if prov.get("source") else ""), shape_name=prov.get("name", v["short_name"]), shape_id=str(prov.get("source_id", "")),
               area_km2=cell.area / 1e6, bounds_epsg32644=[float(x) for x in cell.bounds], bounds_wgs84=[float(x) for x in g.to_crs(4326).total_bounds],
               share_inside_mandal=inside, provenance=prov)
    return cell, rec


def boundary(cfg) -> tuple:
    """Study-window polygon in EPSG:32644 and a selection record. method 'geoboundaries_adm3': an administrative polygon (geoBoundaries gbOpen ADM3);
    method 'voronoi_proxy': Thiessen cell of a village point (used only when no administrative polygon exists)."""
    v = cfg["village"]
    if v["boundary_method"] == "polygon_file":
        return polygon_file_boundary(cfg)
    adm2 = gpd.read_file(dl.http_download(dl.GB_BASE.format(lvl="ADM2"), dl.CACHE / "gb_IND_ADM2.geojson"))
    adm3 = gpd.read_file(dl.http_download(dl.GB_BASE.format(lvl="ADM3"), dl.CACHE / "gb_IND_ADM3.geojson"))
    dist = adm2[adm2.shapeName == v["district"]].geometry.iloc[0]
    if v["boundary_method"] == "geoboundaries_adm3":
        g = adm3[(adm3.shapeName == v["adm3_name"]) & adm3.representative_point().within(dist)]
        if len(g) != 1:
            raise ValueError(f"expected exactly one ADM3 polygon named {v['adm3_name']!r} in {v['district']}, found {len(g)}")
        cell = g.to_crs(CRS_WORK).geometry.iloc[0]
        rec = dict(method="geoBoundaries gbOpen IND ADM3 polygon", shape_name=g.shapeName.iloc[0], shape_id=g.shapeID.iloc[0], area_km2=cell.area / 1e6,
                   bounds_epsg32644=[float(x) for x in cell.bounds], bounds_wgs84=[float(x) for x in g.total_bounds])
        return cell, rec
    raise NotImplementedError("voronoi_proxy was only used for a discarded village; re-enable from git history if needed")


def cached_boundary(ddir: Path) -> tuple:
    """Study polygon from the existing data/villages/<id>/boundary.gpkg (written by the first acquire run) -> (polygon in EPSG:32644, record). No network."""
    g = gpd.read_file(ddir / "boundary.gpkg").to_crs(CRS_WORK)
    cell = g.geometry.union_all()
    rec = dict(method="cached boundary.gpkg (geoBoundaries gbOpen IND ADM3 polygon from the first acquire run)", shape_name=str(g.iloc[0].get("name", "")),
               shape_id="", area_km2=cell.area / 1e6, bounds_epsg32644=[float(x) for x in cell.bounds], bounds_wgs84=[float(x) for x in g.to_crs(4326).total_bounds])
    return cell, rec


def _fetch_roads(cfg, cell, wgs):
    r, rel = overture(cfg, "transportation", "segment", wgs, ["id", "class", "subtype", "names", "geometry"])
    r = _geom(r).to_crs(CRS_WORK)
    r = r[r.subtype.fillna("road") == "road"]
    r["name"] = r["names"].map(lambda n: n.get("primary") if isinstance(n, dict) else None)
    return r.drop(columns=["names"])[lambda d: d.intersects(cell)], rel


def _fetch_buildings(cfg, cell, wgs):
    b, _ = overture(cfg, "buildings", "building", wgs, ["id", "sources", "class", "subtype", "geometry"])
    b = _geom(b).to_crs(CRS_WORK)
    b = b[b.geometry.representative_point().within(cell)].copy()
    b["dataset"] = b.sources.map(lambda s: s[0].get("dataset") if s is not None and len(s) else None)
    # Google Open Buildings polygons carry a model confidence; OpenStreetMap polygons are human-mapped and carry none -> treated as 1.0 (flagged by `dataset`)
    b["confidence"] = b.sources.map(lambda s: (max([x.get("confidence") or 0.0 for x in s]) if s is not None and len(s) and s[0].get("dataset") != "OpenStreetMap" else 1.0))
    b["record_id"] = b.sources.map(lambda s: s[0].get("record_id") if s is not None and len(s) else None)
    b["area_m2"] = b.geometry.area
    return b.drop(columns=["sources"])


def _fetch_places(cfg, cell):
    p, _ = overture(cfg, "places", "place", np.array(gpd.GeoSeries([cell.buffer(4000)], crs=CRS_WORK).to_crs(4326).total_bounds),
                    ["id", "confidence", "names", "basic_category", "taxonomy", "addresses", "sources", "operating_status", "geometry"])
    p = _geom(p).to_crs(CRS_WORK)
    p["name"] = p["names"].map(lambda n: n.get("primary") if isinstance(n, dict) else None)
    p["taxonomy_primary"] = p["taxonomy"].map(lambda t: t.get("primary") if isinstance(t, dict) else None)
    p["dataset"] = p["sources"].map(lambda s: s[0].get("dataset") if s is not None and len(s) else None)
    p["addr_region"] = p["addresses"].map(lambda a: a[0].get("region") if a is not None and len(a) else None)
    p["addr_locality"] = p["addresses"].map(lambda a: a[0].get("locality") if a is not None and len(a) else None)
    p["addr_postcode"] = p["addresses"].map(lambda a: a[0].get("postcode") if a is not None and len(a) else None)
    return p.drop(columns=["names", "taxonomy", "addresses", "sources"])


def fetch_layers(cfg, cell) -> dict:
    """Roads, buildings and places inside the cell (all from the pinned Overture release)."""
    wgs = gpd.GeoSeries([cell.buffer(500)], crs=CRS_WORK).to_crs(4326).total_bounds
    roads, rel = _fetch_roads(cfg, cell, wgs)
    return {"roads": roads, "buildings": _fetch_buildings(cfg, cell, wgs), "places_4km": _fetch_places(cfg, cell), "release": rel}


def cached_layers(cfg, cell, ddir: Path, skip_buildings: bool = False, log=print) -> dict:
    """Same layers as fetch_layers, read from data/villages/<id>/*.gpkg when present; only the missing ones are queried from Overture (S3).
    With skip_buildings the (slow) Overture buildings query is never made: the open buildings are replaced by an empty frame, which is only valid for the
    segmentation variant (its footprints come from StrongDINOv2Seg)."""
    wgs = gpd.GeoSeries([cell.buffer(500)], crs=CRS_WORK).to_crs(4326).total_bounds
    out = {"release": cfg["overture_release"]}
    for name in ("roads", "buildings", "places_4km"):
        f = ddir / f"{name}.gpkg"
        if f.exists():
            out[name] = gpd.read_file(f).to_crs(CRS_WORK)
            log(f"  {name}: {len(out[name]):,} rows from cache {f.name}")
        elif name == "buildings" and skip_buildings:
            out[name] = gpd.GeoDataFrame({"id": [], "dataset": [], "confidence": [], "area_m2": []}, geometry=[], crs=CRS_WORK)
            log("  buildings: skipped (no Overture buildings download)")
        else:
            log(f"  {name}: not cached -> Overture S3 query")
            out[name] = {"roads": lambda: _fetch_roads(cfg, cell, wgs)[0], "buildings": lambda: _fetch_buildings(cfg, cell, wgs), "places_4km": lambda: _fetch_places(cfg, cell)}[name]()
    return out
