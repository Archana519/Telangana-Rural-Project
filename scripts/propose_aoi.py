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


def rank_candidates(cands: gpd.GeoDataFrame, mandal_wgs, aliases, min_km2=0.2, max_km2=120.0) -> pd.DataFrame:
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
        if r.name_score == 0 and r.source != "file" and r.source != "worldcover_builtup":
            v.append("name does not match")
        if r.share_in_mandal < 0.9:
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


# ------------------------------------------------------------------------------------------------ network fetchers (PC with internet)
def _get(url, **kw):
    import requests
    r = requests.get(url, headers=UA, timeout=120, **kw)
    r.raise_for_status()
    return r


def fetch_nominatim(aliases, mandal, district):
    rows = []
    for a in aliases[:3]:
        try:
            r = _get(NOMINATIM, params=dict(q=f"{a}, {mandal}, {district}, Telangana, India", format="jsonv2", polygon_geojson=1, addressdetails=1, limit=10))
        except Exception as e:
            print("  nominatim:", e)
            continue
        for it in r.json():
            gj = it.get("geojson") or {}
            if gj.get("type") in ("Polygon", "MultiPolygon"):
                rows.append(dict(source="nominatim", name=it.get("name") or it.get("display_name", "").split(",")[0], kind=f"{it.get('category')}/{it.get('type')}", source_id=f"{it.get('osm_type')}/{it.get('osm_id')}",
                                 url=f"https://www.openstreetmap.org/{it.get('osm_type')}/{it.get('osm_id')}", geometry=make_valid(shape(gj))))
        time.sleep(1.1)
    return rows


def fetch_overpass(aliases, bbox_wgs):
    w, s_, e, n = bbox_wgs
    pat = "^(" + "|".join(re.escape(a) for a in aliases) + ")$"
    q = (f'[out:json][timeout:120];(relation["name"~"{pat}",i]({s_},{w},{n},{e});way["name"~"{pat}",i]({s_},{w},{n},{e});'
         f'relation["name:en"~"{pat}",i]({s_},{w},{n},{e}););out geom tags;')
    rows = []
    try:
        r = _get(OVERPASS, params={"data": q})
    except Exception as e_:
        print("  overpass:", e_)
        return rows
    for el in r.json().get("elements", []):
        g = osm_to_polygon(el)
        if g is None or g.is_empty:
            continue
        t = el.get("tags", {})
        kind = "/".join(x for x in (t.get("boundary"), f"admin_level={t['admin_level']}" if "admin_level" in t else None, t.get("place")) if x) or "polygon"
        rows.append(dict(source="osm", name=t.get("name") or t.get("name:en", ""), kind=kind, source_id=f"{el['type']}/{el['id']}", url=f"https://www.openstreetmap.org/{el['type']}/{el['id']}", geometry=g))
    return rows


def fetch_overture(cfg, bbox_wgs, aliases):
    from shapely import from_wkb
    from src.utils import data_downloader_helper as dl
    dl.PINNED_RELEASE = cfg["overture_release"]
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
        rows.append(dict(source="overture", name=nm, kind=f"{r.get('subtype')}/{r.get('class')}", source_id=str(r["id"]), url=f"overture release {rel}, theme=divisions, type=division_area", geometry=make_valid(from_wkb(r["geometry"]))))
    return rows


def settlement_point(cfg, aliases, bbox_wgs):
    """Town centre (lon, lat) from Overture divisions points named like the settlement, else None."""
    from shapely import from_wkb
    from src.utils import data_downloader_helper as dl
    dl.PINNED_RELEASE = cfg["overture_release"]
    try:
        df, _ = dl.overture_table("divisions", "division", bbox_wgs, ["id", "names", "subtype", "geometry"])
    except Exception as e:
        print("  overture division points:", e)
        return None
    for _, r in df.iterrows():
        nm = r["names"].get("primary") if isinstance(r["names"], dict) else None
        if name_score(nm, aliases) >= 1.0:
            p = from_wkb(r["geometry"])
            return p.x, p.y
    return None


def worldcover_extent(cfg, centre_lonlat, mandal_wgs, ddir: Path):
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
    g = g.intersection(gpd.GeoSeries([mandal_wgs], crs=4326).to_crs(CRS).iloc[0])
    return gpd.GeoSeries([g], crs=CRS).to_crs(4326).iloc[0]


# ------------------------------------------------------------------------------------------------ main
def mandal_polygon(cfg):
    from src.utils import data_downloader_helper as dl
    v = cfg["village"]
    adm2 = gpd.read_file(dl.http_download(dl.GB_BASE.format(lvl="ADM2"), dl.CACHE / "gb_IND_ADM2.geojson"))
    adm3 = gpd.read_file(dl.http_download(dl.GB_BASE.format(lvl="ADM3"), dl.CACHE / "gb_IND_ADM3.geojson"))
    dist = adm2[adm2.shapeName == v["district"]].geometry.iloc[0]
    return adm3[(adm3.shapeName == v["adm3_name"]) & adm3.representative_point().within(dist)].geometry.iloc[0]


def write_pick(cfg, row, out_geojson: Path, note: str | None):
    g = gpd.GeoDataFrame([{"name": row["name"]}], geometry=[row["geometry"]], crs=4326)
    out_geojson.parent.mkdir(parents=True, exist_ok=True)
    g.to_file(out_geojson, driver="GeoJSON")
    prov = dict(village=cfg["village"]["id"], name=row["name"], source=row["source"], source_id=row.get("source_id", ""), source_url=row.get("url", ""), kind=row.get("kind", ""), licence=LICENCE.get(row["source"], ""),
                retrieved=str(date.today()), area_km2=float(row["area_km2"]), share_inside_mandal=float(row["share_in_mandal"]), verdict=row["verdict"],
                derived=row["source"] == "worldcover_builtup", note=note or "", sha256=hashlib.sha256(out_geojson.read_bytes()).hexdigest())
    out_geojson.with_name(out_geojson.stem + ".provenance.json").write_text(json.dumps(prov, indent=2, ensure_ascii=False), encoding="utf-8")
    return prov


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--village", required=True)
    ap.add_argument("--sources", nargs="*", default=["overpass", "nominatim", "overture"], choices=["overpass", "nominatim", "overture"], help="empty (--sources with no value) = query nothing, use only --use-file / --settlement-extent")
    ap.add_argument("--pick", type=int, default=None, help="index (first column of the table) of the candidate to fix as the study area")
    ap.add_argument("--use-file", default=None, help="your own village polygon (shp / gpkg / geojson) as the candidate to pick")
    ap.add_argument("--note", default=None, help="provenance note for --use-file / --pick")
    ap.add_argument("--settlement-extent", action="store_true", help="add the derived built-up settlement extent as a candidate (needs --centre or an Overture division point)")
    ap.add_argument("--centre", nargs=2, type=float, metavar=("LAT", "LON"))
    ap.add_argument("--candidates-file", default=None, help="re-use a saved candidates.geojson instead of querying the sources (offline review / --pick)")
    a = ap.parse_args(argv)
    from src.multivillage import acquire as A
    cfg = A.load_cfg(a.village)
    v = cfg["village"]
    ddir = A.data_dir(cfg)
    cdir = ddir / "aoi_candidates"
    cdir.mkdir(exist_ok=True)
    aliases = v.get("place_aliases", [v["short_name"]])
    mandal = mandal_polygon(cfg)
    bbox = tuple(gpd.GeoSeries([mandal], crs=4326).total_bounds)
    print(f"{v['short_name']}: mandal {v['adm3_name']} (district {v['district']}) bbox {[round(x, 4) for x in bbox]}")
    if a.candidates_file:
        raw = gpd.read_file(a.candidates_file).to_crs(4326)
        ranked = raw
    else:
        rows = []
        if "overpass" in a.sources:
            rows += fetch_overpass(aliases, bbox)
        if "nominatim" in a.sources:
            rows += fetch_nominatim(aliases, v["mandal"], v["district"])
        if "overture" in a.sources:
            rows += fetch_overture(cfg, bbox, aliases)
        if a.use_file:
            g = gpd.read_file(a.use_file)
            g = g.set_crs(4326) if g.crs is None else g
            rows.append(dict(source="file", name=v["short_name"], kind="user file", source_id=Path(a.use_file).name, url=str(a.use_file), geometry=make_valid(g.to_crs(4326).geometry.union_all())))
        if a.settlement_extent:
            centre = (a.centre[1], a.centre[0]) if a.centre else settlement_point(cfg, aliases, bbox)
            if centre is None:
                sys.exit("no town centre: pass --centre LAT LON")
            rows.append(dict(source="worldcover_builtup", name=v["short_name"] + " (derived built-up extent)", kind="derived built-up extent", source_id="ESA WorldCover v200 class 50",
                             url="https://esa-worldcover.org", geometry=worldcover_extent(cfg, centre, mandal, ddir)))
        if not rows:
            sys.exit("no candidate polygon found in any source. Options: --use-file with a village polygon you hold (LGD / Census / Survey of India), or --settlement-extent --centre LAT LON")
        ranked = rank_candidates(gpd.GeoDataFrame(rows, geometry="geometry", crs=4326), mandal, aliases)
        ranked.to_file(cdir / "candidates.geojson", driver="GeoJSON")
    ranked = ranked.reset_index(drop=True)
    show = ranked[["source", "name", "kind", "source_id", "area_km2", "share_in_mandal", "name_score", "verdict"]]
    print("\nCandidates (best first):\n" + show.to_string())
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(9, 9))
        gpd.GeoSeries([mandal], crs=4326).boundary.plot(ax=ax, color="k", lw=0.6)
        for i, r in ranked.iterrows():
            gpd.GeoSeries([r.geometry], crs=4326).boundary.plot(ax=ax, lw=1.6)
            c = r.geometry.representative_point()
            ax.annotate(f"{i}: {r.source}\n{r.area_km2} km²", (c.x, c.y), fontsize=7)
        ax.set_title(f"{v['short_name']}: candidate village / town polygons inside the {v['adm3_name']} mandal")
        fig.savefig(cdir / "preview.png", dpi=150)
        print("\npreview:", cdir / "preview.png")
    except Exception as e:
        print("preview skipped:", e)
    if a.pick is not None:
        row = ranked.iloc[a.pick]
        if row.verdict != "plausible":
            print(f"WARNING: candidate {a.pick} is flagged: {row.verdict}")
        out = REPO / v["boundary_file"]
        prov = write_pick(cfg, row.to_dict(), out, a.note)
        print(f"\nwrote {out} and its provenance ({prov['source']} {prov['source_id']}, {prov['area_km2']} km²). Commit both files, then run scripts/run_village_end_to_end.py --village {v['id']} --stage check")
    else:
        print("\nNothing fixed yet. Review preview.png (and the polygons on the Esri imagery), then re-run with --pick N.")


if __name__ == "__main__":
    main()
