"""Scene (footprints, targets, facilities, roads, Stage A / Stage B clearance routes) of each of the four study areas, for the paper's flow figure and any other renderer in master_map.py.

Preference: the StrongDINOv2Seg run (data/villages/<id>/state_segmentation.pkl + clearance_network_v1.pkl, on the owner's PC); if that is absent the open-footprint state
(data/villages/<id>/state.pkl, Overture footprints) is used and the Scene is flagged `preview=True`, so a figure built from it can be stamped as a preview.
Damarakunta: the frozen Stage B footprints (Siddipet/Damarakunta/results/v8_instances) and the committed clearance network of 00_DAMARAKUNTA_MASTER_MAP.
"""
from __future__ import annotations

import pickle
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

from . import acquire as A, clearance as CL, master_map as MM, pipeline_summary as PS, segmentation_variant as SV

REPO = Path(__file__).resolve().parents[2]
CRS = "EPSG:32644"


def mosaic_path(key: str) -> Path:
    a = PS.AREAS[key]
    if key == "damarakunta":
        return REPO / "Siddipet" / "Damarakunta" / "aligned" / "damarakunta_esri_highres_mosaic_0p6m.tif"
    return REPO / "data" / "villages" / f"{a['slug']}_esri" / "aligned" / f"{a['slug']}_esri_highres_mosaic_0p6m.tif"


def damarakunta_scene():
    from shapely.geometry import Point
    from pyproj import Transformer
    root = REPO / "Siddipet" / "Damarakunta"
    cell = gpd.read_file(root / "study_area/damarakunta_boundary.gpkg").to_crs(CRS).geometry.union_all()
    b = gpd.read_file(root / "results/v8_instances/buildings_v8_full.gpkg", layer="buildings").to_crs(CRS).reset_index(drop=True)
    b["hid"] = np.arange(1, len(b) + 1)
    b["quality_class_model"] = b["quality_class"]
    tgt = gpd.read_file(root / "results/individual_house_network_v1/individual_house_network_v1.gpkg", layer="house_target_status")
    gap = b[b.bld_id.isin(set(tgt.bld_id))].copy()
    roads = gpd.read_file(root / "reference/tgrac_road_network.gpkg").to_crs(CRS).geometry.intersection(cell)
    roads = roads[~roads.is_empty]
    t = pd.read_csv(REPO / "configs/multivillage/villages/damarakunta_verified_facilities.csv")
    t = t[t.use_in_analysis.astype(str).str.lower() == "true"]
    ft = {"School": "school", "College": "college", "Hospital": "health", "Government Office": "government", "Anganwadi": "anganwadi"}
    xy = Transformer.from_crs(4326, CRS, always_xy=True).transform(t.lon.values, t.lat.values)
    fac = gpd.GeoDataFrame(dict(fid=np.arange(1, len(t) + 1), name=t["name"].values, facility_type=t.category.map(ft).values), geometry=[Point(x, y) for x, y in zip(*xy)], crs=CRS)
    cp = PS.AREAS["damarakunta"]["maps"] / "clearance_network_v1.pkl"
    if not cp.exists():
        raise FileNotFoundError(f"{cp} not found: run scripts/make_damarakunta_master_map.py first")
    clear = pickle.load(open(cp, "rb"))
    sc = MM.scene_from_clearance("Damarakunta (village)", "TGRAC village polygon", cell, roads, b, gap, fac, clear, mosaic=mosaic_path("damarakunta") if mosaic_path("damarakunta").exists() else None,
                                 footprint_source="StrongDINOv2Seg + OpenCV (v8)")
    sc.preview = False
    return sc


def village_scene(key: str, source: str = "auto", log=print, limit_targets: int | None = None):
    a = PS.AREAS[key]
    cfg = A.load_cfg(a["config"])
    d = A.data_dir(cfg)
    seg = d / "state_segmentation.pkl"
    use_seg = seg.exists() and source in ("auto", "segmentation")
    if source == "segmentation" and not seg.exists():
        raise FileNotFoundError(f"{seg} not found (run the StrongDINOv2Seg stages on the PC first)")
    S = pickle.load(open(seg if use_seg else d / "state.pkl", "rb"))
    cache = d / ("clearance_network_v1.pkl" if (use_seg and not limit_targets) else f"clearance_network_preview_{limit_targets or 'all'}.pkl")
    clear = CL.compute_clearance(cfg, S, d, cache_path=cache, log=log, limit_targets=limit_targets)
    info = SV.study_area_info(cfg)
    cell = S["cell"]
    mos = mosaic_path(key)
    sc = MM.scene_from_clearance(info["study_area_name"], info.get("boundary_type") or info["study_area_type"], cell, S["layers"]["roads"].geometry.intersection(cell), S["classified"], S["gap"], S["fac"], clear,
                                 mosaic=mos if mos.exists() else None, footprint_source="StrongDINOv2Seg + OpenCV" if use_seg else "Overture open footprints (PREVIEW)")
    sc.preview = (not use_seg) or bool(limit_targets)
    return sc


def scene_for(key: str, source: str = "auto", log=print, limit_targets: int | None = None):
    return damarakunta_scene() if key == "damarakunta" else village_scene(key, source, log, limit_targets)
