"""Download, clip and reproject the open inputs needed by the hierarchical routing levels (2 GP, 3 Mandal, 4 District).

    python -m src.utils.data_downloader_helper --plan                          # what exists / what would be fetched
    python -m src.utils.data_downloader_helper --levels gp mandal district     # fetch whatever is missing
    python -m src.utils.data_downloader_helper --levels district --what rasters --dem-source srtm --force

Paths come from configs/hierarchy_levels.yaml (`data:` section; project convention is `Siddipet/...`, EPSG:32644).
Existing files are never overwritten unless --force. Every product gets `<file>.provenance.json` (source URL, release,
licence, bbox, date, caveats). Raw downloads are cached in data/raw/_cache/ (git-ignored).

Sources (all open; verified reachable from the project's cloud container on 2026-11-14)
  boundaries  geoBoundaries gbOpen IND ADM2/ADM3 (CC BY 4.0) - district + mandal polygons. NOTE: the release has 23 mandals
              inside Siddipet district whereas the district has since been re-organised; names/extents are 'as released'.
  rasters     ESA WorldCover 10 m v200 (2021) and Copernicus GLO-30 DEM (or SRTM 1 arc-second) from public AWS COGs,
              read as windows, reprojected to the working CRS. (Stage B docs list SRTM as the DEM; Copernicus is the default
              here because it is a surface model at the same 30 m - choose --dem-source srtm to match Stage B.)
  roads       Overture Maps transportation segments (OSM-derived, ODbL) on AWS; optional OSMnx path when Overpass is reachable.
  places      Overture Maps places + divisions (village localities). Facility coverage in rural Telangana is SPARSE: Mandal HQ,
              PHC and market positions are therefore written as clearly flagged PROXIES (`proxy=True`) or left missing.
Nothing downloaded here is ground truth (docs/DECISIONS.md row 6): all layers are REFERENCE data.
"""
from __future__ import annotations

import argparse
import datetime as dt
import gzip
import json
import math
import os
import re
import shutil
import ssl
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from shapely.geometry import box

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

CACHE = REPO / "data" / "raw" / "_cache"
GB_BASE = "https://media.githubusercontent.com/media/wmgeolab/geoBoundaries/main/releaseData/gbOpen/IND/{lvl}/geoBoundaries-IND-{lvl}.geojson"
WC_URL = "https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/ESA_WorldCover_10m_2021_v200_{tile}_Map.tif"
COP_URL = "https://copernicus-dem-30m.s3.amazonaws.com/{name}/{name}.tif"
SRTM_URL = "https://s3.amazonaws.com/elevation-tiles-prod/skadi/{ns}{lat:02d}/{ns}{lat:02d}{ew}{lon:03d}.hgt.gz"
OVERTURE_BUCKET = "overturemaps-us-west-2"
ANCHOR = (78.7538, 17.7082)            # a point inside Damarakunta; selects Siddipet district / Markook mandal
DISTRICT_NAME, MANDAL_NAME = "Siddipet", "Markook"
ROAD_CLASSES = {
    "gp": None,                                                         # all drivable classes
    "mandal": None,
    "district": {"motorway", "trunk", "primary", "secondary", "tertiary"},
}
DRIVABLE = {"motorway", "trunk", "primary", "secondary", "tertiary", "unclassified", "residential", "living_street",
            "service", "track", "unknown"}


# ============================================================================================ plumbing
def _cfg(path=None):
    from src.routing.hierarchical_router import load_config
    return load_config(path)


def _p(root: Path, rel: str) -> Path:
    q = Path(rel)
    return q if q.is_absolute() else root / q


def _ssl_context():
    for cand in (os.environ.get("SSL_CERT_FILE"), os.environ.get("CURL_CA_BUNDLE"), "/root/.ccr/ca-bundle.crt"):
        if cand and Path(cand).exists():
            return ssl.create_default_context(cafile=cand)
    return ssl.create_default_context()


def http_download(url: str, dest: Path, log=print) -> Path:
    """Streaming download (honours HTTPS_PROXY) to a temp file, then atomic rename. Cached: skips when dest exists."""
    dest = Path(dest)
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    log(f"  downloading {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "telangana-rural-project-data-helper"})
    with urllib.request.urlopen(req, timeout=300, context=_ssl_context()) as r, open(tmp, "wb") as fh:
        shutil.copyfileobj(r, fh, 1 << 20)
    tmp.replace(dest)
    return dest


def gdal_env():
    import rasterio
    kw = dict(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif,.gz,.hgt",
              GDAL_HTTP_MAX_RETRY="4", GDAL_HTTP_RETRY_DELAY="2", VSI_CACHE="TRUE")
    ca = next((c for c in (os.environ.get("CURL_CA_BUNDLE"), os.environ.get("SSL_CERT_FILE"), "/root/.ccr/ca-bundle.crt")
               if c and Path(c).exists()), None)
    if ca:
        kw["CURL_CA_BUNDLE"] = ca
    return rasterio.Env(**kw)


def write_provenance(path: Path, **info):
    info.update(file=str(path), created=dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                reference_data_not_ground_truth=True)
    Path(str(path) + ".provenance.json").write_text(json.dumps(info, indent=2, default=str), encoding="utf-8")


@dataclass
class Artifact:
    level: str
    name: str
    path: Path
    exists: bool
    how: str

    def line(self):
        return f"  [{'present' if self.exists else 'MISSING'}] {self.level:8s} {self.name:16s} {self.path}   <- {self.how}"


HOW = dict(boundary="geoBoundaries ADM2/ADM3", mandal_boundaries="geoBoundaries ADM3", mandal_boundary="geoBoundaries ADM3",
           gp_boundaries="Overture village localities (points; NOT GP polygons)", roads="Overture transportation",
           facilities="Overture places + flagged proxies", terminals="mandal interior points (flagged PROXY, not verified HQs)",
           landcover="ESA WorldCover 10 m v200", dem="Copernicus GLO-30 / SRTM")


def plan(cfg: dict, root: Path | str = REPO, levels=("gp", "mandal", "district")) -> list:
    root, out = Path(root), []
    for lvl in levels:
        for name, rel in cfg["data"][lvl].items():
            if name in ("village_root",) or not isinstance(rel, str):
                continue
            path = _p(root, rel)
            how = HOW.get(name, "user-supplied")
            if lvl == "gp" and name in ("boundary", "roads", "facilities"):
                how = "TGRAC layers committed in the repository (not downloaded)"
            out.append(Artifact(lvl, name, path, path.exists(), how))
    return out


# ============================================================================================ tiles / grids
def worldcover_tiles(bounds_wgs84) -> list:
    """WorldCover v200 3-degree tiles (named by SW corner) intersecting (minx, miny, maxx, maxy) in lon/lat."""
    minx, miny, maxx, maxy = bounds_wgs84
    tiles = []
    for lat0 in range(int(math.floor(miny / 3) * 3), int(math.floor(maxy / 3) * 3) + 1, 3):
        for lon0 in range(int(math.floor(minx / 3) * 3), int(math.floor(maxx / 3) * 3) + 1, 3):
            tiles.append(f"{'N' if lat0 >= 0 else 'S'}{abs(lat0):02d}{'E' if lon0 >= 0 else 'W'}{abs(lon0):03d}")
    return tiles


def dem_tiles(bounds_wgs84) -> list:
    """(lat, lon) integer SW corners of 1-degree DEM tiles intersecting the bounds."""
    minx, miny, maxx, maxy = bounds_wgs84
    return [(la, lo) for la in range(int(math.floor(miny)), int(math.floor(maxy)) + 1)
            for lo in range(int(math.floor(minx)), int(math.floor(maxx)) + 1)]


def cop_name(lat: int, lon: int) -> str:
    return f"Copernicus_DSM_COG_10_{'N' if lat >= 0 else 'S'}{abs(lat):02d}_00_{'E' if lon >= 0 else 'W'}{abs(lon):03d}_00_DEM"


def aligned_bounds(bounds, res: float, buffer_m: float = 0.0):
    """Snap bounds outward to a multiple of `res` so rasters of one level share a lattice."""
    minx, miny, maxx, maxy = bounds
    f = lambda v, fn: fn(v / res) * res
    return (f(minx - buffer_m, math.floor), f(miny - buffer_m, math.floor), f(maxx + buffer_m, math.ceil), f(maxy + buffer_m, math.ceil))


def warp_to_grid(sources: list, bounds, crs: str, res: float, out_path: Path, resampling: str, dtype: str, nodata,
                 gz: bool = False) -> Path:
    """Read `sources` (local paths or URLs), reproject into ONE grid (bounds/crs/res) and write a tiled, LZW GeoTIFF.
    Sources may overlap partially; later sources only fill cells the earlier ones left at nodata."""
    import rasterio
    from rasterio.enums import Resampling
    from rasterio.transform import from_origin
    from rasterio.warp import reproject
    minx, miny, maxx, maxy = bounds
    W, H = int(round((maxx - minx) / res)), int(round((maxy - miny) / res))
    T = from_origin(minx, maxy, res, res)
    dst = np.full((H, W), nodata, dtype=dtype)
    rs = getattr(Resampling, resampling)
    with gdal_env():
        for s in sources:
            path = s if not str(s).startswith("http") else (("/vsigzip//vsicurl/" if gz else "/vsicurl/") + s)
            try:
                with rasterio.open(path) as src:
                    tmp = np.full((H, W), nodata, dtype=dtype)
                    reproject(rasterio.band(src, 1), tmp, src_transform=src.transform, src_crs=src.crs or "EPSG:4326",
                              dst_transform=T, dst_crs=crs, resampling=rs, src_nodata=src.nodata, dst_nodata=nodata)
                    fill = dst == nodata if not (isinstance(nodata, float) and math.isnan(nodata)) else np.isnan(dst)
                    dst[fill] = tmp[fill]
            except rasterio.errors.RasterioIOError as e:
                print(f"  WARNING: could not read {s}: {e}")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(out_path, "w", driver="GTiff", height=H, width=W, count=1, dtype=dtype, crs=crs, transform=T,
                       nodata=nodata, compress="lzw", tiled=True, blockxsize=256, blockysize=256) as d:
        d.write(dst, 1)
    return out_path


# ============================================================================================ boundaries
def derive_boundaries(adm2, adm3, anchor=ANCHOR, district_name=DISTRICT_NAME, mandal_name=MANDAL_NAME):
    """From national ADM2/ADM3 GeoDataFrames (EPSG:4326): (district polygon gdf, mandals-in-district gdf, mandal gdf)."""
    from shapely.geometry import Point
    pt = Point(*anchor)
    d = adm2[adm2.contains(pt)]
    d = d[d.shapeName.str.lower() == district_name.lower()] if len(d) > 1 else d
    if d.empty:
        raise ValueError(f"no ADM2 polygon contains the anchor point {anchor}")
    dist = d.iloc[[0]]
    inside = adm3[adm3.representative_point().within(dist.geometry.iloc[0])].copy()
    mandal = inside[inside.shapeName.str.lower() == mandal_name.lower()]
    if mandal.empty:
        raise ValueError(f"mandal {mandal_name!r} not found inside {district_name!r}")
    return dist, inside, mandal


def fetch_boundaries(cfg, root=REPO, force=False, log=print) -> list:
    import geopandas as gpd
    root, crs, made = Path(root), cfg["crs"], []
    dd, md = cfg["data"]["district"], cfg["data"]["mandal"]
    targets = {"district": _p(root, dd["boundary"]), "mandals": _p(root, dd["mandal_boundaries"]), "markook": _p(root, md["boundary"])}
    if not force and all(p.exists() for p in targets.values()):
        log("boundaries: all present")
        return made
    adm2 = gpd.read_file(http_download(GB_BASE.format(lvl="ADM2"), CACHE / "gb_IND_ADM2.geojson", log))
    adm3 = gpd.read_file(http_download(GB_BASE.format(lvl="ADM3"), CACHE / "gb_IND_ADM3.geojson", log))
    dist, mandals, mandal = derive_boundaries(adm2, adm3)
    prov = dict(source="geoBoundaries gbOpen IND (CC BY 4.0, wmgeolab/geoBoundaries)", urls=[GB_BASE.format(lvl="ADM2"), GB_BASE.format(lvl="ADM3")],
                caveat=f"{len(mandals)} mandals inside the district polygon as released; current administrative reorganisation may differ")
    for key, gdf, col in (("district", dist, "district"), ("mandals", mandals, "mandal"), ("markook", mandal, "mandal")):
        out = gdf[["shapeName", "shapeID", "geometry"]].rename(columns={"shapeName": col}).to_crs(crs)
        targets[key].parent.mkdir(parents=True, exist_ok=True)
        out.to_file(targets[key], driver="GPKG")
        write_provenance(targets[key], **prov, rows=len(out), area_km2=float(out.area.sum() / 1e6))
        made.append(targets[key])
        log(f"boundaries: wrote {targets[key]} ({len(out)} polygons, {out.area.sum() / 1e6:,.0f} km2)")
    return made


# ============================================================================================ rasters
def level_bounds(cfg, root, level, buffer_m=1000.0):
    """Working-CRS bounds + WGS84 bounds for a level, from its boundary file."""
    import geopandas as gpd
    root = Path(root)
    key = {"gp": "boundary", "mandal": "boundary", "district": "boundary"}[level]
    g = gpd.read_file(_p(root, cfg["data"][level][key])).to_crs(cfg["crs"])
    b = tuple(g.total_bounds)
    b = (b[0] - buffer_m, b[1] - buffer_m, b[2] + buffer_m, b[3] + buffer_m)
    wgs = tuple(gpd.GeoSeries([box(*b)], crs=cfg["crs"]).to_crs(4326).total_bounds)
    return b, wgs


def fetch_rasters(cfg, root=REPO, level="gp", dem_source="copernicus", force=False, log=print) -> list:
    root, made = Path(root), []
    d = cfg["data"][level]
    lc_path, dem_path = _p(root, d["landcover"]), _p(root, d["dem"])
    need_lc, need_dem = force or not lc_path.exists(), force or not dem_path.exists()
    if not (need_lc or need_dem):
        log(f"rasters[{level}]: present")
        return made
    b, wgs = level_bounds(cfg, root, level)
    if need_lc:
        b10 = aligned_bounds(b, 10.0)
        srcs = [WC_URL.format(tile=t) for t in worldcover_tiles(wgs)]
        log(f"rasters[{level}]: WorldCover {worldcover_tiles(wgs)} -> {lc_path.name}")
        warp_to_grid(srcs, b10, cfg["crs"], 10.0, lc_path, "nearest", "uint8", 0)
        write_provenance(lc_path, source="ESA WorldCover 10 m v200 (2021), CC BY 4.0", urls=srcs, bounds=b10, crs=cfg["crs"], res_m=10.0)
        made.append(lc_path)
    if need_dem:
        b30 = aligned_bounds(b, 30.0, buffer_m=60.0)
        if dem_source == "srtm":
            srcs = [SRTM_URL.format(ns="N" if la >= 0 else "S", lat=abs(la), ew="E" if lo >= 0 else "W", lon=abs(lo))
                    for la, lo in dem_tiles(wgs)]
        else:
            srcs = [COP_URL.format(name=cop_name(la, lo)) for la, lo in dem_tiles(wgs)]
        log(f"rasters[{level}]: DEM ({dem_source}) {len(srcs)} tile(s) -> {dem_path.name}")
        warp_to_grid(srcs, b30, cfg["crs"], 30.0, dem_path, "bilinear", "float32", -9999.0, gz=(dem_source == "srtm"))
        write_provenance(dem_path, source=("SRTM 1 arc-second (AWS skadi)" if dem_source == "srtm" else "Copernicus DEM GLO-30 (AWS COG)"),
                         urls=srcs, bounds=b30, crs=cfg["crs"], res_m=30.0, note="slope is computed downstream from this DEM")
        made.append(dem_path)
    return made


# ============================================================================================ Overture (roads, places, villages)
def overture_release(fs=None) -> str:
    import pyarrow.fs as pafs
    fs = fs or pafs.S3FileSystem(anonymous=True, region="us-west-2")
    infos = fs.get_file_info(pafs.FileSelector(f"{OVERTURE_BUCKET}/release/"))
    rel = sorted(Path(i.path).name for i in infos if i.type == pafs.FileType.Directory)
    if not rel:
        raise RuntimeError("no Overture release found")
    return rel[-1]


def overture_table(theme: str, typ: str, wgs_bounds, columns, release=None):
    import pyarrow.compute as pc
    import pyarrow.dataset as ds
    import pyarrow.fs as pafs
    fs = pafs.S3FileSystem(anonymous=True, region="us-west-2")
    release = release or overture_release(fs)
    dset = ds.dataset(f"{OVERTURE_BUCKET}/release/{release}/theme={theme}/type={typ}/", filesystem=fs, format="parquet")
    cols = [c for c in columns if c in dset.schema.names]
    xmin, ymin, xmax, ymax = wgs_bounds
    flt = (pc.field("bbox", "xmin") < xmax) & (pc.field("bbox", "xmax") > xmin) & (pc.field("bbox", "ymin") < ymax) & (pc.field("bbox", "ymax") > ymin)
    return dset.to_table(columns=cols, filter=flt).to_pandas(), release


def _primary(v):
    return v.get("primary") if isinstance(v, dict) else None


def fetch_roads(cfg, root=REPO, level="mandal", force=False, source="overture", log=print) -> list:
    import geopandas as gpd
    from shapely import from_wkb
    root = Path(root)
    out = _p(root, cfg["data"][level]["roads"])
    if out.exists() and not force:
        log(f"roads[{level}]: present")
        return []
    b, wgs = level_bounds(cfg, root, level, buffer_m=500.0)
    if source == "osmnx":
        from src.routing.data_hooks import fetch_osm_roads
        gdf = fetch_osm_roads(box(*wgs)).to_crs(cfg["crs"])
        rel = "osmnx"
    else:
        df, rel = overture_table("transportation", "segment", wgs, ["id", "class", "subtype", "names", "geometry"])
        df = df[df["subtype"].fillna("road") == "road"] if "subtype" in df else df
        keep = ROAD_CLASSES.get(level) or DRIVABLE
        df = df[df["class"].isin(keep)]
        gdf = gpd.GeoDataFrame({"class": df["class"].values, "name": df["names"].map(_primary).values,
                                "geometry": [from_wkb(g) for g in df["geometry"]]}, crs=4326).to_crs(cfg["crs"])
    gdf = gdf[gdf.intersects(box(*b))]
    out.parent.mkdir(parents=True, exist_ok=True)
    gdf[["class", "name", "geometry"]].to_file(out, driver="GPKG") if "class" in gdf else gdf[["geometry"]].to_file(out, driver="GPKG")
    write_provenance(out, source=f"Overture Maps transportation segments (OSM-derived, ODbL), release {rel}" if source != "osmnx" else "OpenStreetMap via OSMnx (ODbL)",
                     bounds=b, rows=len(gdf), classes=sorted(set(gdf["class"])) if "class" in gdf else None,
                     caveat="road completeness and class tags vary; not a PMGSY/TGRAC inventory")
    log(f"roads[{level}]: wrote {out} ({len(gdf)} segments, release {rel})")
    return [out]


PLACE_RULES = (("phc", r"\bphc\b|primary health|community health|\bchc\b"), ("market", r"market|mandi|rythu\s*bazar|bazaar"),
               ("mandal hq", r"mandal\s*(revenue|parishad|praja)|\bmro\b|\bmpdo\b|tah[sc]?[ie]l"))


def classify_place(name: str, cat: str):
    """Facility type for the Level-3 loaders from an Overture place, or None. Name rules first, then category."""
    n, c = (name or "").lower(), (cat or "").lower()
    for kind, rx in PLACE_RULES:
        if re.search(rx, n):
            return {"phc": "PHC", "market": "Market", "mandal hq": "Mandal HQ"}[kind]
    if "market" in c:
        return "Market"
    return None


def fetch_mandal_nodes(cfg, root=REPO, force=False, log=print) -> list:
    """Level-3 gram_panchayats.gpkg (village points) and facilities.gpkg (classified places + flagged Mandal-HQ proxy)."""
    import geopandas as gpd
    from shapely import from_wkb
    root = Path(root)
    md = cfg["data"]["mandal"]
    gp_out, fac_out = _p(root, md["gp_boundaries"]), _p(root, md["facilities"])
    if gp_out.exists() and fac_out.exists() and not force:
        log("mandal nodes: present")
        return []
    b, wgs = level_bounds(cfg, root, "mandal", buffer_m=0.0)
    mandal = gpd.read_file(_p(root, md["boundary"])).to_crs(cfg["crs"]).geometry.union_all()
    made = []
    if force or not gp_out.exists():
        df, rel = overture_table("divisions", "division", wgs, ["id", "names", "subtype", "geometry"])
        df = df[df["subtype"] == "locality"] if "subtype" in df else df
        pts = gpd.GeoDataFrame({"gp_name": df["names"].map(_primary).values, "houses": np.nan,
                                "geometry": [from_wkb(g) for g in df["geometry"]]}, crs=4326).to_crs(cfg["crs"])
        pts = pts[pts.within(mandal)]
        pts["proxy"] = True
        pts.to_file(gp_out, driver="GPKG")
        write_provenance(gp_out, source=f"Overture Maps divisions (village localities), release {rel}", rows=len(pts),
                         caveat="POINTS, not Gram Panchayat polygons: each village is treated as one GP hub with unknown house count "
                                "(weight 1). Supply TGRAC/Panchayat Raj GP polygons with a `houses` column for real weights.")
        made.append(gp_out)
        log(f"mandal nodes: {len(pts)} village points -> {gp_out}")
    if force or not fac_out.exists():
        rows = []
        try:
            df, rel = overture_table("places", "place", wgs, ["id", "names", "taxonomy", "categories", "confidence", "geometry"])
            for _, r in df.iterrows():
                cat = _primary(r.get("taxonomy")) or _primary(r.get("categories"))
                t = classify_place(_primary(r["names"]), cat)
                if t:
                    rows.append(dict(facility_id=r["id"], facility_name=_primary(r["names"]), facility_type=t, proxy=False,
                                     geometry=from_wkb(r["geometry"])))
        except Exception as e:                      # places coverage is optional
            log(f"  places unavailable ({e}); only the Mandal HQ proxy is written")
        c = mandal.representative_point()
        rows.append(dict(facility_id="MANDAL_HQ_PROXY", facility_name=f"{MANDAL_NAME} (interior point of mandal polygon)",
                         facility_type="Mandal HQ (proxy)", proxy=True,
                         geometry=gpd.GeoSeries([c], crs=cfg["crs"]).to_crs(4326).iloc[0]))
        fac = gpd.GeoDataFrame(rows, crs=4326).to_crs(cfg["crs"])
        fac.to_file(fac_out, driver="GPKG")
        write_provenance(fac_out, source="Overture Maps places (name/category rules) + Mandal HQ proxy", rows=len(fac),
                         caveat="PHCs and markets are only those Overture lists (often none in rural mandals). The Mandal HQ is an "
                                "interior point of the mandal polygon, NOT a verified office location: replace with the real HQ/PHC/market coordinates.")
        made.append(fac_out)
        log(f"mandal nodes: {len(fac)} facilities ({int((~fac.proxy).sum())} real, {int(fac.proxy.sum())} proxy) -> {fac_out}")
    return made


def fetch_district_terminals(cfg, root=REPO, force=False, log=print) -> list:
    import geopandas as gpd
    root = Path(root)
    out = _p(root, cfg["data"]["district"]["terminals"])
    if out.exists() and not force:
        log("terminals: present")
        return []
    mandals = gpd.read_file(_p(root, cfg["data"]["district"]["mandal_boundaries"])).to_crs(cfg["crs"])
    pts = mandals.copy()
    pts["geometry"] = mandals.geometry.representative_point()
    pts["id"] = ["MANDAL_" + re.sub(r"\W+", "_", m.upper()) for m in pts["mandal"]]
    pts["kind"] = "mandal_hq"
    pts["weight"] = 1.0
    root_row = pts["mandal"].str.lower().str.contains("siddipet urban")
    if root_row.any():
        pts.loc[root_row, "kind"] = "district_hq"
        pts.loc[root_row, "id"] = "DISTRICT_HQ"
        pts.loc[root_row, "weight"] = 100.0
    pts["proxy"] = True
    pts[["id", "kind", "weight", "proxy", "mandal", "geometry"]].to_file(out, driver="GPKG")
    write_provenance(out, source="interior points of geoBoundaries mandal polygons", rows=len(pts),
                     caveat="PROXY terminals, not verified mandal HQ coordinates. District HQ = 'Siddipet Urban' polygon if present, "
                            "otherwise the heaviest terminal is used as root.")
    log(f"terminals: wrote {out} ({len(pts)} proxy terminals)")
    return [out]


# ============================================================================================ CLI
def run(levels, what, cfg, root=REPO, dem_source="copernicus", force=False, roads_source="overture", log=print) -> list:
    made = []
    if "boundaries" in what and ({"mandal", "district"} & set(levels)):
        made += fetch_boundaries(cfg, root, force, log)
    for lvl in levels:
        if "rasters" in what:
            made += fetch_rasters(cfg, root, lvl, dem_source, force, log)
        if "roads" in what and lvl in ("mandal", "district"):       # GP roads come from TGRAC (already in the repository)
            made += fetch_roads(cfg, root, lvl, force, roads_source, log)
    if "places" in what:
        if "mandal" in levels:
            made += fetch_mandal_nodes(cfg, root, force, log)
        if "district" in levels:
            made += fetch_district_terminals(cfg, root, force, log)
    return made


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--levels", nargs="+", default=["gp", "mandal", "district"], choices=["gp", "mandal", "district"])
    ap.add_argument("--what", nargs="+", default=["boundaries", "rasters", "roads", "places"],
                    choices=["boundaries", "rasters", "roads", "places"])
    ap.add_argument("--dem-source", default="copernicus", choices=["copernicus", "srtm"])
    ap.add_argument("--roads-source", default="overture", choices=["overture", "osmnx"])
    ap.add_argument("--force", action="store_true", help="re-download even if the file exists")
    ap.add_argument("--plan", action="store_true", help="only list present/missing inputs")
    ap.add_argument("--config", default=None)
    a = ap.parse_args(argv)
    cfg = _cfg(a.config)
    print("input status (configs/hierarchy_levels.yaml):")
    for art in plan(cfg, REPO, a.levels):
        print(art.line())
    if a.plan:
        return
    made = run(a.levels, a.what, cfg, REPO, a.dem_source, a.force, a.roads_source)
    print("\nwritten:", *map(str, made), sep="\n  ") if made else print("\nnothing to do")


if __name__ == "__main__":
    main()
