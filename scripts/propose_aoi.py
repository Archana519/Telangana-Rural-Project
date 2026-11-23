#!/usr/bin/env python
"""Find, review and fix the TRUE village / town boundary of a study area (run on a PC with internet).

The multi-settlement pipeline never uses a clipped box or a whole mandal: the study area is the real settlement polygon, so houses and roads at the
edge of the village are not cut off from the network. geoBoundaries (the layer cached in the repository) only has the mandal (ADM3), so the village or
town polygon has to come from a village-level source. This script collects candidates from every open source that has one, ranks them, shows them for
review and, after you choose, writes the polygon plus a provenance file that the pipeline reads (configs/multivillage/villages/<id>_boundary.geojson).

    python scripts/propose_aoi.py --village aswaraopeta                    # 1. collect candidates, print the table, save previews (writes nothing into configs/)
    python scripts/propose_aoi.py --village aswaraopeta --pick 2           # 2. fix candidate 2 as the study area (boundary file + provenance)
    python scripts/propose_aoi.py --village aswaraopeta --use-file my.shp --note "LGD village boundary, downloaded 2026-11-24"      # your own polygon instead
    python scripts/propose_aoi.py --village aswaraopeta --settlement-extent --centre 17.25 81.13      # last resort, see below

Sources (all optional, all open):
  * OpenStreetMap through Overpass: boundary / place polygons named like the settlement (ODbL 1.0).
  * Nominatim (OpenStreetMap geocoder) with polygon output (ODbL 1.0).
  * Overture Maps `divisions` theme, type division_area: locality / local-admin polygons (licence per the Overture release documentation).
  * LGD (Local Government Directory) and the Census village layers publish no open API: if you hold a village shapefile (for example from the LGD or the
    Survey of India), pass it with --use-file; it is treated like any other candidate and its provenance is whatever you state with --note.
Last resort (--settlement-extent): the connected built-up area (ESA WorldCover class 50) around the town centre, closed over small gaps and linked over
roads and fields up to 250 m, then smoothed. That is a DERIVED settlement extent, not an administrative boundary, and the provenance file says so. It is
still a natural outline of the settlement, never a box.

Latest, uncut boundaries: the candidates come from live sources (OpenStreetMap, the newest Overture release), so they are current, and the 2018 geoBoundaries mandal polygon is shown only as a
REFERENCE row (never pickable). Every candidate gets an EDGE-CONTINUITY check on ESA WorldCover: the share of its boundary with built-up land on both sides (30 m in / 30 m out) and the share of the
local built-up settlement extent that lies OUTSIDE the polygon. A polygon that cuts through continuous built-up area is flagged CUTS_BUILTUP and refused by --pick unless you add --accept-cut. The ranking
prefers the cleanest boundary. Both `--village adilabad_urban` (writes the new boundary for the config `adilabad_urban_updated`; the 2018-based run and its papers stay untouched) and
`--village aswaraopeta` are supported.

Whichever candidate you pick, check the preview (data/villages/<id>/aoi_candidates/preview.png) against the Esri imagery: the polygon should contain
the whole built-up area of the village / town, including its outskirts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from datetime import date
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import MultiPolygon, Polygon, shape
from shapely.ops import linemerge, polygonize, unary_union
from shapely.validation import make_valid

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
CRS = "EPSG:32644"
UA = {"User-Agent": "Mozilla/5.0 (research script; boundary lookup)"}
OVERPASS = "https://overpass-api.de/api/interpreter"
NOMINATIM = "https://nominatim.openstreetmap.org/search"
LICENCE = {"osm": "ODbL 1.0 (c) OpenStreetMap contributors", "nominatim": "ODbL 1.0 (c) OpenStreetMap contributors", "overture": "per the Overture Maps release documentation (docs.overturemaps.org/attribution)",
           "file": "as stated by the supplier of the file", "worldcover_builtup": "derived from ESA WorldCover v200 (CC BY 4.0)"}


# ------------------------------------------------------------------------------------------------ pure helpers (unit-tested offline)
def norm(s) -> str:
    return re.sub(r"[^a-z]", "", str(s or "").lower().replace("ashwa", "aswa"))


def name_score(name, aliases) -> float:
    """1.0 exact (after normalising spelling), 0.6 one contains the other, 0 otherwise."""
    n = norm(name)
    if not n:
        return 0.0
    best = 0.0
    for a in aliases:
        k = norm(a)
        if n == k:
            return 1.0
        if k and (k in n or n in k):
            best = max(best, 0.6)
    return best


def osm_to_polygon(el: dict):
    """Overpass element (`out geom`) -> shapely (Multi)Polygon or None. Closed ways become polygons; relations are assembled from their outer (and inner) member ways."""
    def line(g):
        return [(p["lon"], p["lat"]) for p in g]
    if el["type"] == "way":
        pts = line(el.get("geometry", []))
        return Polygon(pts) if len(pts) >= 4 and pts[0] == pts[-1] else None
    if el["type"] != "relation":
        return None
    from shapely.geometry import LineString
    outer = [LineString(line(m["geometry"])) for m in el.get("members", []) if m.get("role") == "outer" and m.get("geometry") and len(m["geometry"]) > 1]
    inner = [LineString(line(m["geometry"])) for m in el.get("members", []) if m.get("role") == "inner" and m.get("geometry") and len(m["geometry"]) > 1]
    if not outer:
        return None
    polys = list(polygonize(linemerge(outer)))
    if not polys:
        return None
    g = unary_union(polys)
    if inner:
        holes = list(polygonize(linemerge(inner)))
        if holes:
            g = g.difference(unary_union(holes))
    return make_valid(g)


def rank_candidates(cands: gpd.GeoDataFrame, mandal_wgs, aliases, min_km2=0.2, max_km2=120.0, strict_mandal=True) -> pd.DataFrame:
    """Add area, share inside the mandal, name score and a plausibility verdict; best first. Input: EPSG:4326 frame with columns source, name, geometry (+ optional kind)."""
    if cands.empty:
        return cands.assign(area_km2=[], share_in_mandal=[], name_score=[], verdict=[], score=[])
    c = cands.copy().reset_index(drop=True)
    u = c.to_crs(CRS)
    c["area_km2"] = (u.area / 1e6).round(2)
    mu = gpd.GeoSeries([mandal_wgs], crs=4326).to_crs(CRS).iloc[0]
    c["share_in_mandal"] = [round(float(g.intersection(mu).area / g.area), 2) if g.area else 0.0 for g in u.geometry]
    c["name_score"] = [name_score(n, aliases) for n in c["name"]]
    verdict = []
    for _, r in c.iterrows():
        v = []
        if r.source == "geoboundaries_2018_reference":
            v.append("REFERENCE ONLY (outdated 2018 layer)")
        elif r.name_score == 0 and r.source != "file" and r.source != "worldcover_builtup":
            v.append("name does not match")
        if r.share_in_mandal < 0.9 and strict_mandal:
            v.append(f"only {r.share_in_mandal:.0%} inside the mandal")
        if r.area_km2 > max_km2:
            v.append("too large (mandal / district level)")
        if r.area_km2 < min_km2:
            v.append("too small")
        verdict.append("; ".join(v) or "plausible")
    c["verdict"] = verdict
    kind = c["kind"].fillna("") if "kind" in c else pd.Series([""] * len(c))
    adm = kind.str.contains(r"administrative|locality|localadmin|census|village|town|city|suburb|neighbourhood", case=False, regex=True).astype(float)
    c["score"] = 3 * c.name_score + 1.0 * adm + (c.verdict == "plausible") * 2.0 + np.where(c.area_km2.between(1, 60), 0.5, 0.0)
    return c.sort_values("score", ascending=False).reset_index(drop=True)


def settlement_extent_from_raster(lc, transform, centre_xy, built_class=50, close_m=60.0, link_m=250.0, seed_radius_m=1500.0, buffer_m=40.0, res=10.0, hole_km2=0.5):
    """Natural settlement outline from a land-cover grid: built-up cells (class 50), closed over gaps <= close_m, linked into one settlement over gaps <= link_m, keeping the
    clusters that reach within seed_radius_m of the town centre; outline smoothed by a buffer round trip; interior holes smaller than hole_km2 filled. Returns a polygon in the raster CRS."""
    from scipy import ndimage as ndi
    from rasterio.features import shapes
    built = lc == built_class
    r_close = max(1, int(round(close_m / 2 / res)))
    r_link = max(1, int(round(link_m / 2 / res)))
    disk = lambda r: (np.add.outer(np.arange(-r, r + 1) ** 2, np.arange(-r, r + 1) ** 2) <= r * r)
    closed = ndi.binary_closing(built, structure=disk(r_close))
    linked = ndi.binary_dilation(closed, structure=disk(r_link))
    lab, n = ndi.label(linked)
    cx, cy = centre_xy
    col, row = (~transform) @ (cx, cy)
    yy, xx = np.ogrid[: lc.shape[0], : lc.shape[1]]
    seed = ((yy - row) ** 2 + (xx - col) ** 2) <= (seed_radius_m / res) ** 2
    keep = np.unique(lab[seed & closed])
    keep = keep[keep > 0]
    if len(keep) == 0:
        raise ValueError("no built-up area within the seed radius of the centre: check the centre coordinates")
    mask = closed & np.isin(lab, keep)
    polys = [shape(g) for g, v in shapes(mask.astype(np.uint8), mask=mask, transform=transform) if v == 1]
    g = unary_union(polys).buffer(buffer_m).buffer(-buffer_m / 2).simplify(res / 2)
    parts = [g] if g.geom_type == "Polygon" else list(g.geoms)
    parts = [Polygon(p.exterior, [h for h in p.interiors if Polygon(h).area / 1e6 >= hole_km2]) for p in parts]
    return unary_union(parts)


def edge_report(poly_utm, lc, transform, step=50.0, d=30.0, built_class=50, res=10.0):
    """Does the polygon cut through continuous built-up area? (poly_utm in the raster CRS, lc a land-cover grid)
    edge_both_pct   share of the boundary (sampled every `step` m) with built-up land both d m inside and d m outside;
    outside_pct     share of the local built-up settlement extent (derived like settlement_extent_from_raster, seeded inside the polygon) that lies outside the polygon;
    outside_km2     that area. None values when the raster does not cover the polygon or has no built-up land near its centre."""
    built = lc == built_class
    if poly_utm.buffer(-d).is_empty:
        raise ValueError("polygon too small for the edge check")
    inner, outer = poly_utm.buffer(-d).boundary, poly_utm.buffer(d).boundary
    bd = poly_utm.boundary
    n = max(int(bd.length // step), 1)
    inv = ~transform

    def val(p):
        c, r = inv @ (p.x, p.y)
        r, c = int(r), int(c)
        return bool(built[r, c]) if 0 <= r < built.shape[0] and 0 <= c < built.shape[1] else None
    tot = both = 0
    for i in range(n):
        p = bd.interpolate(i * step)
        a, b = val(inner.interpolate(inner.project(p))), val(outer.interpolate(outer.project(p)))
        if a is None or b is None:
            continue
        tot += 1
        both += int(a and b)
    out = dict(edge_both_pct=round(100 * both / tot, 1) if tot else None, edge_both_km=round(both * step / 1000, 2) if tot else None, outside_pct=None, outside_km2=None)
    try:
        c0 = poly_utm.representative_point()
        ext = settlement_extent_from_raster(lc, transform, (c0.x, c0.y), seed_radius_m=min(1500.0, 0.5 * np.sqrt(poly_utm.area)))
        outside = ext.difference(poly_utm.buffer(d))                 # tolerance d m: the derived extent is smoothed, so thin slivers along a correct boundary are not 'outside'
        out["outside_pct"] = round(100 * outside.area / ext.area, 1)
        out["outside_km2"] = round(outside.area / 1e6, 2)
    except Exception:
        pass
    return out


EDGE_FLAG_BOTH_PCT, EDGE_FLAG_OUTSIDE_PCT = 5.0, 10.0


def add_edge_metrics(ranked: pd.DataFrame, lc, transform) -> pd.DataFrame:
    """Add edge columns + an `edge_verdict` (CUTS_BUILTUP / clean) and re-rank: cleaner boundaries first among otherwise equal candidates."""
    r = ranked.copy()
    cols = {k: [] for k in ("edge_both_pct", "edge_both_km", "outside_pct", "outside_km2")}
    for g in gpd.GeoSeries(r.geometry, crs=4326).to_crs(CRS):
        try:
            e = edge_report(g, lc, transform)
        except Exception:
            e = dict(edge_both_pct=None, edge_both_km=None, outside_pct=None, outside_km2=None)
        for k in cols:
            cols[k].append(e[k])
    for k, v in cols.items():
        r[k] = v
    nn = lambda x: x is not None and not (isinstance(x, float) and np.isnan(x))
    flag = [bool((nn(a) and a > EDGE_FLAG_BOTH_PCT) or (nn(b) and b > EDGE_FLAG_OUTSIDE_PCT)) for a, b in zip(r.edge_both_pct, r.outside_pct)]
    r["edge_verdict"] = ["CUTS_BUILTUP" if f else ("clean" if (nn(a) or nn(b)) else "not_checked") for f, a, b in zip(flag, r.edge_both_pct, r.outside_pct)]
    big = r.area_km2 > 120.0                                       # mandal / district polygons: the settlement edge check does not apply
    r.loc[big, "edge_verdict"] = "not_applicable"
    for k in ("edge_both_pct", "edge_both_km", "outside_pct", "outside_km2"):
        r.loc[big, k] = np.nan
    pen = 0.1 * r.edge_both_pct.fillna(0) + 0.05 * r.outside_pct.fillna(0)
    r["score"] = r["score"] - pen
    return r.sort_values("score", ascending=False).reset_index(drop=True)


def edge_raster(bounds_wgs_list, ddir: Path, pad_m=400.0):
    """WorldCover window covering all candidates (+pad) for the edge check. Returns (lc, transform)."""
    import rasterio
    from shapely.geometry import box
    from src.utils import data_downloader_helper as dl
    u = gpd.GeoSeries([box(*b) for b in bounds_wgs_list], crs=4326).to_crs(CRS).union_all()
    x0, y0, x1, y1 = u.bounds
    b = (np.floor((x0 - pad_m) / 10) * 10, np.floor((y0 - pad_m) / 10) * 10, np.ceil((x1 + pad_m) / 10) * 10, np.ceil((y1 + pad_m) / 10) * 10)
    wgs = tuple(gpd.GeoSeries([box(*b)], crs=CRS).to_crs(4326).total_bounds)
    out = ddir / "aoi_candidates" / "worldcover_edge.tif"
    out.parent.mkdir(parents=True, exist_ok=True)
    dl.warp_to_grid([dl.WC_URL.format(tile=t) for t in dl.worldcover_tiles(wgs)], b, CRS, 10.0, out, "nearest", "uint8", 0)
    with rasterio.open(out) as s:
        return s.read(1), s.transform


# ------------------------------------------------------------------------------------------------ network fetchers (PC with internet)
def _get(url, **kw):
    import requests
    r = requests.get(url, headers=UA, timeout=120, **kw)
    r.raise_for_status()
    return r


def fetch_nominatim(aliases, mandal, district):
    """Nominatim search with polygon output (format=geojson: the plain json format is rate-limited more aggressively from shared IPs)."""
    rows, seen = [], set()
    queries = []
    for a in aliases[:4]:
        queries += [f"{a}, {district}, Telangana, India", f"{a}, {mandal}, {district}, Telangana, India"]
    for q in dict.fromkeys(queries):
        try:
            r = _get(NOMINATIM, params=dict(q=q, format="geojson", polygon_geojson=1, addressdetails=1, limit=10))
            feats = r.json().get("features", [])
        except Exception as e:
            print(f"  nominatim '{q}': {type(e).__name__}: {str(e)[:90]}")
            time.sleep(2)
            continue
        for f in feats:
            p_, gj = f.get("properties", {}), f.get("geometry") or {}
            key = (p_.get("osm_type"), p_.get("osm_id"))
            if gj.get("type") in ("Polygon", "MultiPolygon") and key not in seen:
                seen.add(key)
                rows.append(dict(source="nominatim", name=p_.get("name") or p_.get("display_name", "").split(",")[0], kind=f"{p_.get('category')}/{p_.get('type')}", source_id=f"{p_.get('osm_type')}/{p_.get('osm_id')}",
                                 url=f"https://www.openstreetmap.org/{p_.get('osm_type')}/{p_.get('osm_id')}", geometry=make_valid(shape(gj))))
        time.sleep(1.2)
    return rows


def fetch_photon_relations(aliases):
    """Photon (komoot) finds OSM objects by name; for every relation among the hits the polygon comes from polygons.openstreetmap.fr (OSM data, ODbL). Also returns OSM place nodes (name, lon, lat)
    for reporting: a town / village that OSM maps only as a point has no polygon to fetch."""
    rows, points, seen = [], [], set()
    for a in aliases[:4]:
        try:
            feats = _get("https://photon.komoot.io/api/", params=dict(q=a, limit=20)).json().get("features", [])
        except Exception as e:
            print(f"  photon '{a}': {type(e).__name__}: {str(e)[:80]}")
            continue
        for f in feats:
            p_ = f["properties"]
            if name_score(p_.get("name"), aliases) == 0:
                continue
            if p_.get("osm_type") == "N" and p_.get("osm_key") == "place":
                points.append(dict(name=p_.get("name"), value=p_.get("osm_value"), osm_id=p_.get("osm_id"), lon=f["geometry"]["coordinates"][0], lat=f["geometry"]["coordinates"][1]))
            if p_.get("osm_type") == "R" and p_["osm_id"] not in seen and p_.get("osm_key") in ("boundary", "place"):
                seen.add(p_["osm_id"])
                try:
                    g = shape(_get("https://polygons.openstreetmap.fr/get_geojson.py", params=dict(id=p_["osm_id"], params=0)).json())
                except Exception as e:
                    print(f"  polygons.osm.fr R{p_['osm_id']}: {type(e).__name__}: {str(e)[:80]}")
                    continue
                rows.append(dict(source="osm", name=p_.get("name"), kind=f"{p_.get('osm_key')}/{p_.get('osm_value')}", source_id=f"relation/{p_['osm_id']}", url=f"https://www.openstreetmap.org/relation/{p_['osm_id']}", geometry=make_valid(g)))
        time.sleep(0.5)
    return rows, points


OVERPASS_MIRRORS = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter", "https://overpass.private.coffee/api/interpreter", "https://maps.mail.ru/osm/tools/overpass/api/interpreter"]


def fetch_overpass(aliases, bbox_wgs):
    w, s_, e, n = bbox_wgs
    pat = "^(" + "|".join(re.escape(a) for a in aliases) + ")$"
    q = (f'[out:json][timeout:90];(relation["name"~"{pat}",i]({s_},{w},{n},{e});way["name"~"{pat}",i]({s_},{w},{n},{e});'
         f'relation["name:en"~"{pat}",i]({s_},{w},{n},{e}););out geom tags;')
    data = None
    for url in OVERPASS_MIRRORS:
        try:
            import requests
            r = requests.post(url, data={"data": q}, headers=UA, timeout=100)
            r.raise_for_status()
            data = r.json()
            print("  overpass:", url.split("/")[2], "ok")
            break
        except Exception as e_:
            print(f"  overpass {url.split('/')[2]}: {type(e_).__name__}: {str(e_)[:80]}")
    rows = []
    for el in (data or {}).get("elements", []):
        g = osm_to_polygon(el)
        if g is None or g.is_empty:
            continue
        t = el.get("tags", {})
        kind = "/".join(x for x in (t.get("boundary"), f"admin_level={t['admin_level']}" if "admin_level" in t else None, t.get("place")) if x) or "polygon"
        rows.append(dict(source="osm", name=t.get("name") or t.get("name:en", ""), kind=kind, source_id=f"{el['type']}/{el['id']}", url=f"https://www.openstreetmap.org/{el['type']}/{el['id']}", geometry=g))
    return rows


def fetch_overture(cfg, bbox_wgs, aliases, release=None):
    """release=None -> the newest Overture release (boundaries should be current); a string pins it."""
    from shapely import from_wkb
    from src.utils import data_downloader_helper as dl
    dl.PINNED_RELEASE = release
    rows = []
    try:
        df, rel = dl.overture_table("divisions", "division_area", bbox_wgs, ["id", "names", "subtype", "class", "country", "region", "geometry"])
    except Exception as e:
        print("  overture divisions:", e)
        return rows
    for _, r in df.iterrows():
        nm = r["names"].get("primary") if isinstance(r["names"], dict) else None
        if name_score(nm, aliases) == 0:
            continue
        rows.append(dict(source="overture", name=nm, kind=f"{r.get('subtype')}/{r.get('class')}", source_id=str(r["id"]), url=f"overture release {rel}, theme=divisions, type=division_area", release=rel, geometry=make_valid(from_wkb(r["geometry"]))))
    return rows


def settlement_point(cfg, aliases, bbox_wgs, release=None):
    """Town centre (lon, lat) from Overture divisions points named like the settlement, else None."""
    from shapely import from_wkb
    from src.utils import data_downloader_helper as dl
    dl.PINNED_RELEASE = release
    try:
        df, _ = dl.overture_table("divisions", "division", bbox_wgs, ["id", "names", "subtype", "geometry"])
    except Exception as e:
        print("  overture division points:", e)
        return None
    for _, r in df.iterrows():
        nm = r["names"].get("primary") if isinstance(r["names"], dict) else None
        if name_score(nm, aliases) >= 1.0:
            p = from_wkb(r["geometry"])
            return p.x, p.y, f"Overture division point '{nm}' ({r.get('subtype')})"
    return None


def worldcover_extent(cfg, centre_lonlat, clip_wgs, ddir: Path):
    """clip_wgs = the search area (mandal, or mandal + buffer when a town extends beyond its 2018 mandal); the built-up extent is only clipped to that."""
    import rasterio
    from pyproj import Transformer
    from shapely.geometry import box
    from src.utils import data_downloader_helper as dl
    cx, cy = Transformer.from_crs(4326, CRS, always_xy=True).transform(*centre_lonlat)
    half = 5000.0                                            # computation window only (the outline itself is derived from the built-up area, never from this box)
    b = (cx - half, cy - half, cx + half, cy + half)
    wgs = tuple(gpd.GeoSeries([box(*b)], crs=CRS).to_crs(4326).total_bounds)
    out = ddir / "aoi_candidates" / "worldcover_window.tif"
    out.parent.mkdir(parents=True, exist_ok=True)
    urls = [dl.WC_URL.format(tile=t) for t in dl.worldcover_tiles(wgs)]
    dl.warp_to_grid(urls, b, CRS, 10.0, out, "nearest", "uint8", 0)
    with rasterio.open(out) as s:
        lc, T = s.read(1), s.transform
    g = settlement_extent_from_raster(lc, T, (cx, cy))
    g = g.intersection(gpd.GeoSeries([clip_wgs], crs=4326).to_crs(CRS).iloc[0])
    return gpd.GeoSeries([g], crs=CRS).to_crs(4326).iloc[0]


DERIVATION = dict(raster="ESA WorldCover v200 (2021), 10 m, built-up class 50", close_m=60.0, link_m=250.0, seed_radius_m=1500.0, buffer_round_trip_m="+40 / -20", simplify_m=5.0, fill_holes_below_km2=0.5,
                  window_m="10 km x 10 km computation window around the centre (not the study area)", method="built-up cells closed over gaps <= 60 m, linked over gaps <= 250 m, clusters reaching within 1.5 km of the centre kept, outline smoothed; clipped only to the search area")


# ------------------------------------------------------------------------------------------------ main
def mandal_polygon(cfg):
    from src.utils import data_downloader_helper as dl
    v = cfg["village"]
    adm2 = gpd.read_file(dl.http_download(dl.GB_BASE.format(lvl="ADM2"), dl.CACHE / "gb_IND_ADM2.geojson"))
    adm3 = gpd.read_file(dl.http_download(dl.GB_BASE.format(lvl="ADM3"), dl.CACHE / "gb_IND_ADM3.geojson"))
    dist = adm2[adm2.shapeName == v["district"]].geometry.iloc[0]
    return adm3[(adm3.shapeName == v["adm3_name"]) & adm3.representative_point().within(dist)].geometry.iloc[0]


def coverage_report(poly_wgs, release=None) -> dict:
    """What the polygon covers: the 2018 geoBoundaries mandals it intersects (area, share of the polygon) and the Overture localities / neighbourhoods whose point lies inside it."""
    from shapely import from_wkb
    out = dict(mandals_2018=[], localities=[], localities_source="")
    u = gpd.GeoSeries([poly_wgs], crs=4326).to_crs(CRS).iloc[0]
    try:
        from src.utils import data_downloader_helper as dl
        a3 = gpd.read_file(dl.http_download(dl.GB_BASE.format(lvl="ADM3"), dl.CACHE / "gb_IND_ADM3.geojson"))
        a3 = a3[a3.geometry.intersects(poly_wgs)]
        for _, r in a3.iterrows():
            x = gpd.GeoSeries([r.geometry], crs=4326).to_crs(CRS).iloc[0].intersection(u)
            if x.area > 1e4:
                out["mandals_2018"].append(dict(mandal=r.shapeName, area_km2=round(x.area / 1e6, 2), share_of_polygon_pct=round(100 * x.area / u.area, 1)))
        out["mandals_2018"].sort(key=lambda d: -d["area_km2"])
    except Exception as e:
        out["mandals_error"] = str(e)[:100]
    try:
        from src.utils import data_downloader_helper as dl
        dl.PINNED_RELEASE = release
        df, rel = dl.overture_table("divisions", "division", tuple(poly_wgs.bounds), ["id", "names", "subtype", "geometry"])
        names = sorted({(r["names"].get("primary") if isinstance(r["names"], dict) else None) for _, r in df.iterrows()
                        if r.get("subtype") in ("locality", "neighborhood", "macrohood", "microhood") and poly_wgs.contains(from_wkb(r["geometry"]))} - {None})
        out["localities"], out["localities_source"] = names, f"Overture divisions points inside the polygon, release {rel}"
    except Exception as e:
        out["localities_error"] = str(e)[:100]
    return out


def write_pick(cfg, row, out_geojson: Path, note: str | None):
    g = gpd.GeoDataFrame([{"name": row["name"]}], geometry=[row["geometry"]], crs=4326)
    out_geojson.parent.mkdir(parents=True, exist_ok=True)
    g.to_file(out_geojson, driver="GeoJSON")
    prov = dict(village=cfg["village"]["id"], name=row["name"], source=row["source"], source_id=row.get("source_id", ""), source_url=row.get("url", ""), kind=row.get("kind", ""), licence=LICENCE.get(row["source"], ""),
                retrieved=str(date.today()), area_km2=float(row["area_km2"]), share_inside_mandal=float(row["share_in_mandal"]), verdict=row["verdict"],
                edge_continuity={k: (None if row.get(k) is None or (isinstance(row.get(k), float) and np.isnan(row.get(k))) else row.get(k)) for k in ("edge_both_pct", "edge_both_km", "outside_pct", "outside_km2", "edge_verdict")},
                overture_release=(row.get("release") if isinstance(row.get("release"), str) else ""),
                study_area_name=cfg["village"].get("study_area_name", cfg["village"]["short_name"]), study_area_type=cfg["village"].get("study_area_type", ""),
                boundary_type=("DERIVED built-up settlement extent (NOT an administrative boundary)" if row["source"] == "worldcover_builtup" else f"polygon from {row['source']}"),
                derivation=(dict(DERIVATION, centre_lon=row.get("centre_lon"), centre_lat=row.get("centre_lat"), centre_source=row.get("centre_source")) if row["source"] == "worldcover_builtup" else None),
                covers=coverage_report(row["geometry"], None),
                derived=row["source"] == "worldcover_builtup", note=note or "", sha256=hashlib.sha256(out_geojson.read_bytes()).hexdigest())
    out_geojson.with_name(out_geojson.stem + ".provenance.json").write_text(json.dumps(prov, indent=2, ensure_ascii=False), encoding="utf-8")
    return prov


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--village", required=True)
    ap.add_argument("--sources", nargs="*", default=["overpass", "nominatim", "overture"], choices=["overpass", "nominatim", "overture"], help="empty (--sources with no value) = query nothing, use only --use-file / --settlement-extent")
    ap.add_argument("--overture-release", default=None, help="Overture release to read (default: the newest, so the boundary is current; the release used is recorded)")
    ap.add_argument("--pick", type=int, default=None, help="index (first column of the table) of the candidate to fix as the study area")
    ap.add_argument("--accept-cut", action="store_true", help="allow --pick of a candidate flagged CUTS_BUILTUP (not recommended: the study area would cut through built-up land)")
    ap.add_argument("--use-file", default=None, help="your own village / town polygon (shp / gpkg / geojson, e.g. an LGD or municipal boundary) as a candidate")
    ap.add_argument("--note", default=None, help="provenance note for --use-file / --pick")
    ap.add_argument("--settlement-extent", action="store_true", help="add the derived built-up settlement extent as a candidate (needs --centre or an Overture division point)")
    ap.add_argument("--centre", nargs=2, type=float, metavar=("LAT", "LON"))
    ap.add_argument("--no-edge-check", action="store_true", help="skip the WorldCover edge-continuity check (not recommended)")
    ap.add_argument("--candidates-file", default=None, help="re-use a saved candidates.geojson instead of querying the sources (offline review / --pick)")
    a = ap.parse_args(argv)
    from src.multivillage import acquire as A
    cfg = A.load_cfg(a.village)
    v = cfg["village"]
    tgt = A.load_cfg(v["updated_boundary_village"]) if v.get("updated_boundary_village") else cfg          # adilabad_urban -> adilabad_urban_updated
    tv = tgt["village"]
    if tgt is not cfg:
        print(f"note: the 2018-based village '{v['id']}' stays frozen; the new boundary is written for '{tv['id']}' ({tv['boundary_file']}).")
    ddir = A.data_dir(tgt)
    cdir = ddir / "aoi_candidates"
    cdir.mkdir(exist_ok=True)
    aliases = tv.get("place_aliases") or v.get("place_aliases") or [v["short_name"]]
    strict = tv.get("mandal_check", "strict") == "strict"
    mandal = mandal_polygon(cfg)
    buf_km = float(tv.get("search_buffer_km", 0.0))
    area_poly = gpd.GeoSeries([mandal], crs=4326).to_crs(CRS).buffer(buf_km * 1000).to_crs(4326).iloc[0] if buf_km else mandal
    bbox = tuple(gpd.GeoSeries([area_poly], crs=4326).total_bounds)
    print(f"{v['short_name']}: reference mandal {v['adm3_name']} (district {v['district']}); search bbox {[round(float(x), 4) for x in bbox]}" + (f" (mandal + {buf_km:g} km: a town boundary may extend beyond the 2018 mandal)" if buf_km else ""))
    if a.candidates_file:
        ranked = gpd.read_file(a.candidates_file).to_crs(4326)
    else:
        rows = []
        points = []
        if "overpass" in a.sources:
            rows += fetch_overpass(aliases, bbox)
            pr, points = fetch_photon_relations(aliases)
            rows += pr
            points = list({(p_["osm_id"]): p_ for p_ in points}.values())
            if points:
                print("OSM maps this place as a point only (no polygon in OSM):", [(p_["name"], p_["value"], round(p_["lat"], 5), round(p_["lon"], 5)) for p_ in points])
        if "nominatim" in a.sources:
            rows += fetch_nominatim(aliases, v["mandal"], v["district"])
        if "overture" in a.sources:
            rows += fetch_overture(cfg, bbox, aliases, a.overture_release)
        if a.use_file:
            g = gpd.read_file(a.use_file)
            g = g.set_crs(4326) if g.crs is None else g
            rows.append(dict(source="file", name=v["short_name"], kind="user file", source_id=Path(a.use_file).name, url=str(a.use_file), geometry=make_valid(g.to_crs(4326).geometry.union_all())))
        if a.settlement_extent:
            if a.centre:
                centre, csrc = (a.centre[1], a.centre[0]), f"--centre {a.centre[0]} {a.centre[1]} (given; e.g. the OpenStreetMap place node)"
            else:
                sp = settlement_point(cfg, aliases, bbox, a.overture_release)
                if sp is None:
                    sys.exit("no town centre: pass --centre LAT LON")
                centre, csrc = sp[:2], sp[2]
            rows.append(dict(source="worldcover_builtup", name=v["short_name"] + " (derived built-up extent)", kind="derived built-up extent", source_id="ESA WorldCover v200 class 50",
                             url="https://esa-worldcover.org", centre_lon=float(centre[0]), centre_lat=float(centre[1]), centre_source=csrc, geometry=worldcover_extent(cfg, centre, area_poly, ddir)))
        if not rows:
            sys.exit("no candidate polygon found in any source. Options: --use-file with a village / municipal polygon you hold (LGD / Census / municipality), or --settlement-extent --centre LAT LON")
        if tv.get("legacy_reference_adm3") or v.get("legacy_reference_adm3"):
            rows.append(dict(source="geoboundaries_2018_reference", name=v["adm3_name"], kind="administrative/mandal 2018 (geoBoundaries ADM3)", source_id="geoBoundaries gbOpen IND ADM3 2018", url="https://www.geoboundaries.org", geometry=mandal))
        cg = gpd.GeoDataFrame(rows, geometry="geometry", crs=4326)
        cg = cg.drop_duplicates(subset=["source_id"], keep="first") if "source_id" in cg else cg           # the same OSM relation can come from Overpass, Photon and Nominatim
        ranked = rank_candidates(cg, mandal, aliases, strict_mandal=strict)
        if not a.no_edge_check:
            try:
                small = ranked[ranked.area_km2 < 400]
                lc, T = edge_raster([g.bounds for g in small.geometry], ddir)
                ranked = add_edge_metrics(ranked, lc, T)
            except Exception as e:
                print("edge-continuity check skipped:", e)
        ranked.to_file(cdir / "candidates.geojson", driver="GeoJSON")
    ranked = ranked.reset_index(drop=True)
    for k in ("edge_both_pct", "outside_pct", "edge_verdict", "release"):
        if k not in ranked:
            ranked[k] = None
    show = ranked[["source", "name", "kind", "source_id", "area_km2", "share_in_mandal", "name_score", "edge_both_pct", "outside_pct", "edge_verdict", "verdict"]]
    print("\nCandidates (best first). edge_both_pct = % of the boundary with built-up land on both sides; outside_pct = % of the local built-up extent outside the polygon:\n" + show.to_string())
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(9, 9))
        gpd.GeoSeries([mandal], crs=4326).boundary.plot(ax=ax, color="k", lw=0.6, ls="--")
        for i, r in ranked.iterrows():
            gpd.GeoSeries([r.geometry], crs=4326).boundary.plot(ax=ax, lw=1.6)
            c = r.geometry.representative_point()
            ax.annotate(f"{i}: {r.source}\n{r.area_km2} km², edge {r.edge_both_pct}%", (c.x, c.y), fontsize=7)
        ax.set_title(f"{v['short_name']}: candidate boundaries (dashed: 2018 mandal polygon)")
        fig.savefig(cdir / "preview.png", dpi=150)
        print("\npreview:", cdir / "preview.png")
    except Exception as e:
        print("preview skipped:", e)
    if a.pick is not None:
        row = ranked.iloc[a.pick].to_dict()
        if row["source"] == "geoboundaries_2018_reference":
            sys.exit("candidate is the outdated 2018 reference row: pick a current candidate")
        if row["verdict"] != "plausible":
            print(f"WARNING: candidate {a.pick} is flagged: {row['verdict']}")
        if row.get("edge_verdict") == "CUTS_BUILTUP" and not a.accept_cut:
            sys.exit(f"candidate {a.pick} cuts through built-up land (edge_both {row['edge_both_pct']}%, {row['outside_pct']}% of the built-up extent outside). Pick another, supply a better polygon with --use-file, or add --accept-cut.")
        out = REPO / tv["boundary_file"]
        prov = write_pick(tgt, row, out, a.note)
        print(f"\nwrote {out} and its provenance ({prov['source']} {prov['source_id']}, {prov['area_km2']} km², edge {prov['edge_continuity']}). Commit both files, then: "
              f"python scripts/run_village_end_to_end.py --village {tv['id']} --stage check")
    else:
        print("\nNothing fixed yet. Review preview.png (and the polygons on the Esri imagery), then re-run with --pick N.")


if __name__ == "__main__":
    main()
