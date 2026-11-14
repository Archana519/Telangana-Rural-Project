"""Data inventory, ingestion and tiling hooks for the hierarchical levels.

* inventory()          which inputs of configs/hierarchy_levels.yaml exist, what each level will fall back to
* load_gp_real()       Level 2 inputs for Damarakunta from files that ARE in the repository (vectors only; the
                       land-cover/DEM rasters are git-ignored *.tif and are used only if present locally)
* ingest_boundary()    GeoJSON / GPKG / SHP boundary -> one shapely polygon in the working CRS
* tile_bounds()        overlapping tile grid for large extents (feeds RasterLayerProvider windows / inference)
* fetch_osm_roads()    OSMnx road extract for a polygon (network + osmnx required; never called implicitly)
* road_graph()         lines -> networkx graph (for contract_degree2 / statistics)
Raw inputs are only read, never written.
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np

from .hierarchical_router import GPInputs, Node, hamlet_hubs, REPO
from .layers import FlatLayerProvider, RasterLayerProvider

QUALITY_USED = ("PLAUSIBLE", "REVIEW", "UNRESOLVED_MERGE")   # same classes as the Stage B footprint penalty


def _p(root: Path, rel: str) -> Path:
    q = Path(rel)
    return q if q.is_absolute() else root / q


def inventory(cfg: dict, root: Path | str = REPO) -> dict:
    """{level: {name: {path, exists}}} plus a per-level fallback statement."""
    root = Path(root)
    out = {}
    for lvl, items in cfg["data"].items():
        if not isinstance(items, dict):
            continue
        out[lvl] = {k: {"path": str(_p(root, v)), "exists": _p(root, v).exists()} for k, v in items.items()}
    fb = {}
    g = out.get("gp", {})
    fb["gp"] = ("REAL vectors (boundary, roads, facilities, footprints, house targets) + "
                + ("REAL land-cover raster" if g.get("landcover", {}).get("exists")
                   else "FLAT cost fallback (no WorldCover raster locally)")
                + (" + DEM slope" if g.get("dem", {}).get("exists") else ", no slope term")) \
        if all(g.get(k, {}).get("exists") for k in ("boundary", "roads", "facilities")) else "SYNTHETIC GP world"
    for lvl in ("mandal", "district"):
        d = out.get(lvl, {})
        need = ("boundary", "roads") if lvl == "mandal" else ("boundary", "roads", "terminals")
        fb[lvl] = "REAL inputs" if d and all(d.get(k, {}).get("exists") for k in need) else "SYNTHETIC world (inputs missing)"
    out["_fallback"] = fb
    return out


def missing_inputs(inv: dict) -> list:
    """Flat list of (level, name, path) for every missing input - the 'what you need to supply' list."""
    return [(lvl, k, v["path"]) for lvl, items in inv.items() if lvl != "_fallback"
            for k, v in items.items() if not v["exists"]]


def ingest_boundary(path: str | Path, crs: str = "EPSG:32644"):
    """Read GeoJSON/GPKG/SHP, reproject to the working CRS and dissolve to a single polygon."""
    import geopandas as gpd
    g = gpd.read_file(path)
    if g.crs is None:
        raise ValueError(f"{path}: boundary has no CRS")
    return g.to_crs(crs).geometry.union_all()


def load_gp_real(cfg: dict, root: Path | str = REPO):
    """Level 2 inputs for Damarakunta GP from repository files. Returns (GPInputs | None, report dict)."""
    import geopandas as gpd
    import pandas as pd
    root = Path(root)
    d = cfg["data"]["gp"]
    lv = cfg["levels"]["gp"]
    rep = {"used": [], "missing": [], "notes": []}
    need = {k: _p(root, d[k]) for k in ("boundary", "roads", "facilities", "house_targets_csv")}
    for k, p in need.items():
        (rep["used"] if p.exists() else rep["missing"]).append(str(p))
    if rep["missing"]:
        return None, rep
    boundary = ingest_boundary(need["boundary"], cfg["crs"])
    roads = gpd.read_file(need["roads"]).to_crs(cfg["crs"])
    fac = gpd.read_file(need["facilities"]).to_crs(cfg["crs"])
    tg = pd.read_csv(need["house_targets_csv"])
    exempt_types = {t.lower() for t in lv["exempt_facility_types"]}
    nodes = hamlet_hubs(tg[["x", "y"]].to_numpy(float), float(lv["hamlet_eps_m"]), int(lv["hamlet_min_houses"]))
    for _, r in fac.iterrows():
        t = str(r["facility_type"])
        kind = ("school" if t.lower().startswith("school") else "healthcare" if t.lower().startswith("health")
                else "panchayat_office" if "gram panchayat" in t.lower() else "facility")
        exempt = any(t.lower().startswith(e) or e in t.lower() for e in exempt_types) or kind == "panchayat_office"
        nodes.append(Node(str(r["facility_id"]), r.geometry.x, r.geometry.y, float(lv["facility_weight"]), kind, exempt))
    fp = None
    bp = _p(root, d["buildings"])
    if bp.exists():
        try:
            b = gpd.read_file(bp, layer="buildings").to_crs(cfg["crs"])
        except Exception:
            b = gpd.read_file(bp).to_crs(cfg["crs"])
        if "quality_class" in b:
            b = b[b.quality_class.isin(QUALITY_USED)]
        fp = b[["geometry"]]
        rep["used"].append(str(bp))
    else:
        rep["notes"].append("no building footprints: footprint penalty inactive")
    lc, dem = _p(root, d["landcover"]), _p(root, d["dem"])
    if lc.exists():
        provider = RasterLayerProvider(str(lc), str(dem) if dem.exists() else None)
        rep["used"].append(str(lc))
    else:
        provider = FlatLayerProvider()
        rep["notes"].append("land-cover raster not in repository (*.tif is git-ignored): flat cost fallback")
    gp = GPInputs("DAMARAKUNTA_GP", roads, nodes, boundary, fp, provider, rep["notes"])
    gp.houses_xy = tg[["x", "y"]].to_numpy(float)
    return gp, rep


def tile_bounds(bounds: tuple, tile_m: float, overlap_m: float = 0.0) -> list:
    """Row-major list of (minx, miny, maxx, maxy) tiles covering `bounds` with `overlap_m` overlap."""
    minx, miny, maxx, maxy = bounds
    step = tile_m - overlap_m
    if step <= 0:
        raise ValueError("overlap must be smaller than the tile size")
    nx, ny = max(1, math.ceil((maxx - minx - overlap_m) / step)), max(1, math.ceil((maxy - miny - overlap_m) / step))
    return [(minx + i * step, miny + j * step, min(minx + i * step + tile_m, maxx), min(miny + j * step + tile_m, maxy))
            for j in range(ny) for i in range(nx)]


def fetch_osm_roads(polygon_wgs84, network_type: str = "drive"):
    """OSMnx road extract (GeoDataFrame of edges, EPSG:4326). Requires `pip install osmnx` and network access."""
    try:
        import osmnx as ox
    except ImportError as e:  # pragma: no cover
        raise RuntimeError("osmnx is not installed (pip install osmnx)") from e
    G = ox.graph_from_polygon(polygon_wgs84, network_type=network_type, simplify=True)  # pragma: no cover
    return ox.graph_to_gdfs(G, nodes=False)                                              # pragma: no cover


def road_graph(roads_gdf, snap_m: float = 1.0):
    """Lines -> networkx graph with vertex coordinates (rounded to snap_m) as nodes and 'length' on edges."""
    import networkx as nx
    G = nx.Graph()
    for geom in roads_gdf.geometry:
        parts = getattr(geom, "geoms", [geom])
        for ln in parts:
            pts = [(round(x / snap_m) * snap_m, round(y / snap_m) * snap_m) for x, y in ln.coords]
            for a, b in zip(pts, pts[1:]):
                if a != b:
                    L = math.hypot(a[0] - b[0], a[1] - b[1])
                    if G.has_edge(a, b):
                        continue
                    G.add_edge(a, b, length=L)
    return G


# ---------------------------------------------------------------------------------------- Levels 3 and 4 loaders
def _provider(cfg_level_paths: dict, root: Path, notes: list):
    lc, dem = _p(root, cfg_level_paths["landcover"]), _p(root, cfg_level_paths["dem"])
    if lc.exists():
        return RasterLayerProvider(str(lc), str(dem) if dem.exists() else None)
    notes.append("land-cover raster missing: flat cost fallback")
    return FlatLayerProvider()


def load_mandal_real(cfg: dict, root: Path | str = REPO):
    """Level 3 inputs from the files named in configs/hierarchy_levels.yaml (data.mandal). Returns (MandalInputs|None, report).

    Column contract:  gp_boundaries.gpkg  -> polygons, optional numeric `houses` (weight), optional `gp_name`
                      facilities.gpkg     -> points with `facility_type` containing 'mandal hq' | 'phc'/'primary health' | 'market'
                      roads.gpkg          -> lines (NH/SH/MDR/PMGSY/OSM), any attributes
    """
    import geopandas as gpd
    from .hierarchical_router import MandalInputs
    root, d, lv = Path(root), cfg["data"]["mandal"], cfg["levels"]["mandal"]
    rep = {"used": [], "missing": [], "notes": []}
    for k in ("boundary", "gp_boundaries", "roads", "facilities"):
        (rep["used"] if _p(root, d[k]).exists() else rep["missing"]).append(str(_p(root, d[k])))
    if rep["missing"]:
        return None, rep
    boundary = ingest_boundary(_p(root, d["boundary"]), cfg["crs"])
    roads = gpd.read_file(_p(root, d["roads"])).to_crs(cfg["crs"])
    gps = gpd.read_file(_p(root, d["gp_boundaries"])).to_crs(cfg["crs"])
    fac = gpd.read_file(_p(root, d["facilities"])).to_crs(cfg["crs"])
    local = None
    classes = lv.get("collector_road_classes")
    if classes and "class" in roads.columns:
        is_coll = roads["class"].isin(classes)
        if is_coll.any():
            local, roads = roads[~is_coll], roads[is_coll]
            rep["notes"].append(f"roads split: {len(roads)} collector-grade segments are attachment goals; {len(local)} local segments only discounted")
        else:
            rep["notes"].append("no collector-class roads found: all roads used as goals")
    nodes = []
    for i, r in gps.reset_index(drop=True).iterrows():
        c = r.geometry.representative_point()
        nodes.append(Node(f"GP_{r.get('gp_name', i + 1)}", c.x, c.y,
                          (float(r["houses"]) if "houses" in gps and np.isfinite(r["houses"]) else 1.0)
                          * float(lv["hub_weight_per_house"]), "gp_hub"))
    for i, r in fac.reset_index(drop=True).iterrows():
        t = str(r.get("facility_type", "")).lower()
        kind, w = (("mandal_hq", lv["hq_weight"]) if "mandal" in t and "hq" in t else
                   ("phc", lv["phc_weight"]) if "phc" in t or "primary health" in t else
                   ("market", lv["market_weight"]) if "market" in t else (None, None))
        if kind:
            nodes.append(Node(str(r.get("facility_id", f"{kind}_{i}")), r.geometry.x, r.geometry.y, float(w), kind))
    b = tuple(boundary.buffer(float(lv["snap_m"])).bounds)
    return MandalInputs("MANDAL", roads, nodes, b, _provider(d, root, rep["notes"]), boundary, rep["notes"], local_roads=local), rep


def load_district_real(cfg: dict, root: Path | str = REPO):
    """Level 4 inputs (data.district). terminals.gpkg: points with `kind` ('district_hq'|'mandal_hq') and optional `weight`."""
    import geopandas as gpd
    from .hierarchical_router import DistrictInputs
    root, d = Path(root), cfg["data"]["district"]
    rep = {"used": [], "missing": [], "notes": []}
    for k in ("boundary", "roads", "terminals"):
        (rep["used"] if _p(root, d[k]).exists() else rep["missing"]).append(str(_p(root, d[k])))
    if rep["missing"]:
        return None, rep
    boundary = ingest_boundary(_p(root, d["boundary"]), cfg["crs"])
    roads = gpd.read_file(_p(root, d["roads"])).to_crs(cfg["crs"])
    term = gpd.read_file(_p(root, d["terminals"])).to_crs(cfg["crs"])
    nodes = [Node(str(r.get("id", f"T{i}")), r.geometry.x, r.geometry.y, float(r.get("weight", 1.0)),
                  str(r.get("kind", "mandal_hq"))) for i, r in term.reset_index(drop=True).iterrows()]
    return DistrictInputs("DISTRICT", roads, nodes, tuple(boundary.buffer(1000.0).bounds),
                          _provider(d, root, rep["notes"]), boundary, rep["notes"]), rep
