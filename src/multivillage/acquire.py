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


def boundary(cfg) -> tuple:
    """Study-window polygon in EPSG:32644 and a selection record. method 'geoboundaries_adm3': an administrative polygon (geoBoundaries gbOpen ADM3);
    method 'voronoi_proxy': Thiessen cell of a village point (used only when no administrative polygon exists)."""
    v = cfg["village"]
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


def fetch_layers(cfg, cell) -> dict:
    """Roads, buildings and places inside the cell (all from the pinned Overture release)."""
    wgs = gpd.GeoSeries([cell.buffer(500)], crs=CRS_WORK).to_crs(4326).total_bounds
    out = {}
    r, rel = overture(cfg, "transportation", "segment", wgs, ["id", "class", "subtype", "names", "geometry"])
    r = _geom(r).to_crs(CRS_WORK)
    r = r[r.subtype.fillna("road") == "road"]
    r["name"] = r["names"].map(lambda n: n.get("primary") if isinstance(n, dict) else None)
    out["roads"] = r.drop(columns=["names"])[lambda d: d.intersects(cell)]
    b, _ = overture(cfg, "buildings", "building", wgs, ["id", "sources", "class", "subtype", "geometry"])
    b = _geom(b).to_crs(CRS_WORK)
    b = b[b.geometry.representative_point().within(cell)].copy()
    b["dataset"] = b.sources.map(lambda s: s[0].get("dataset") if s is not None and len(s) else None)
    # Google Open Buildings polygons carry a model confidence; OpenStreetMap polygons are human-mapped and carry none -> treated as 1.0 (flagged by `dataset`)
    b["confidence"] = b.sources.map(lambda s: (max([x.get("confidence") or 0.0 for x in s]) if s is not None and len(s) and s[0].get("dataset") != "OpenStreetMap" else 1.0))
    b["record_id"] = b.sources.map(lambda s: s[0].get("record_id") if s is not None and len(s) else None)
    b["area_m2"] = b.geometry.area
    out["buildings"] = b.drop(columns=["sources"])
    p, _ = overture(cfg, "places", "place", np.array(gpd.GeoSeries([cell.buffer(4000)], crs=CRS_WORK).to_crs(4326).total_bounds),
                    ["id", "confidence", "names", "basic_category", "taxonomy", "addresses", "sources", "operating_status", "geometry"])
    p = _geom(p).to_crs(CRS_WORK)
    p["name"] = p["names"].map(lambda n: n.get("primary") if isinstance(n, dict) else None)
    p["taxonomy_primary"] = p["taxonomy"].map(lambda t: t.get("primary") if isinstance(t, dict) else None)
    p["dataset"] = p["sources"].map(lambda s: s[0].get("dataset") if s is not None and len(s) else None)
    p["addr_region"] = p["addresses"].map(lambda a: a[0].get("region") if a is not None and len(a) else None)
    p["addr_locality"] = p["addresses"].map(lambda a: a[0].get("locality") if a is not None and len(a) else None)
    p["addr_postcode"] = p["addresses"].map(lambda a: a[0].get("postcode") if a is not None and len(a) else None)
    out["places_4km"] = p.drop(columns=["names", "taxonomy", "addresses", "sources"])
    out["release"] = rel
    return out
