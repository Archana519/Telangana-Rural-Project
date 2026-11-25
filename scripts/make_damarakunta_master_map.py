#!/usr/bin/env python
"""Damarakunta master satellite planning map with building-clearance routes (same design as the other two study areas).

Reads only committed Damarakunta layers (read-only) and, on your PC, the Esri mosaic and the Stage B aligned cost surface; nothing in
DELIVERABLES_DAMARAKUNTA_STAGE_B/ is touched and the frozen Stage B maps and tables stay as they are. It re-plans the routes with
src/multivillage/clearance.py (footprints hard-blocked, routes start at the building edge, every drawn route verified against all footprints),
because the frozen Stage B plan uses a soft footprint penalty (mu = 4) and 28 of its 163 house routes still cross another footprint (209 m, table building_crossings_summary.csv).

    python scripts\\make_damarakunta_master_map.py

Inputs (Siddipet/Damarakunta/):
    results/v8_instances/buildings_v8_full.gpkg                  footprints (all 278, also those outside the village, so no route crosses them either)
    results/individual_house_network_v1/individual_house_network_v1.gpkg   the 163 road-gap target houses of Stage B
    reference/tgrac_road_network.gpkg, reference/derived/damarakunta_priority_facilities_final_5.gpkg, study_area/damarakunta_boundary.gpkg
    aligned/damarakunta_cost_surface_10m.tif (+ aligned/damarakunta_prohibited_mask_10m.tif)   Stage B cost surface (PC only). If absent, a cost surface is rebuilt from
                                                                  aligned_open/ (WorldCover + Copernicus DEM, the common recipe) and the output says so.
    aligned/damarakunta_esri_highres_mosaic_0p6m.tif             Esri imagery (PC only); without it the map has a grey background and is NOT a satellite map.
Output: DELIVERABLES_CONTRIBUTION_3_MULTI_VILLAGE/00_DAMARAKUNTA_MASTER_MAP/ (master_satellite_planning_map.png, clearance_verification.csv, map_facility_key.csv, RUN_STATUS.md);
        scripts/build_final_project_outputs.py copies it into FINAL_PROJECT_OUTPUTS/01_DAMARAKUNTA_RURAL/maps/.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from src.multivillage import acquire as A, clearance as CL, master_map as MM, pipeline as PL, prepare as P      # noqa: E402

CRS = "EPSG:32644"
ROOT = REPO / "Siddipet" / "Damarakunta"
OUT = REPO / "DELIVERABLES_CONTRIBUTION_3_MULTI_VILLAGE" / "00_DAMARAKUNTA_MASTER_MAP"


def cost_from_stage_b(aligned: Path):
    cp, mp = aligned / "damarakunta_cost_surface_10m.tif", aligned / "damarakunta_prohibited_mask_10m.tif"
    with rasterio.open(cp) as s:
        cost = s.read(1).astype("float64")
        if s.nodata is not None:
            cost[cost == s.nodata] = np.nan
        T, shape = s.transform, cost.shape
    cost[~np.isfinite(cost) | (cost <= 0)] = np.nan
    if mp.exists():
        with rasterio.open(mp) as s:
            cost[s.read(1) > 0] = np.nan
    return cost, T, shape


def cost_rebuilt(cfg, cell):
    """Fallback: the common cost recipe on WorldCover + DEM from aligned_open/ (temporary copy; nothing is written into Siddipet/)."""
    from src.utils import data_downloader_helper as dl
    tmp = Path(tempfile.mkdtemp(prefix="dk_cost_"))
    b10, _, _ = P.grid_for_cell(cell, 10.0)
    dl.warp_to_grid([str(ROOT / "aligned_open" / "worldcover_10m.tif")], b10, CRS, 10.0, tmp / "worldcover_10m.tif", "nearest", "uint8", 0)
    b30 = dl.aligned_bounds(b10, 30.0, buffer_m=60.0)
    dl.warp_to_grid([str(ROOT / "aligned_open" / "dem_30m.tif")], b30, CRS, 30.0, tmp / "dem_30m.tif", "bilinear", "float32", -9999.0)
    prep = P.prepare_rasters(cfg, cell, tmp, log=lambda *a: None)
    cost, _ = P.cost_surface(cfg, prep, cell)
    shutil.rmtree(tmp, ignore_errors=True)
    return cost, prep["transform"], prep["shape"]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mosaic", default=str(ROOT / "aligned" / "damarakunta_esri_highres_mosaic_0p6m.tif"))
    ap.add_argument("--out-dir", default=str(OUT))
    ap.add_argument("--dpi", type=int, default=200)
    ap.add_argument("--limit-targets", type=int, default=None, help="debug only")
    a = ap.parse_args()
    out = Path(a.out_dir); out.mkdir(parents=True, exist_ok=True)
    cfg = A.load_cfg("adilabad_urban")                                    # common.yaml planner / cost parameters, identical for every village (Stage B values)
    cell = gpd.read_file(ROOT / "study_area" / "damarakunta_boundary.gpkg").to_crs(CRS).geometry.union_all()
    b = gpd.read_file(ROOT / "results/v8_instances/buildings_v8_full.gpkg", layer="buildings").to_crs(CRS)
    tgt = gpd.read_file(ROOT / "results/individual_house_network_v1/individual_house_network_v1.gpkg", layer="house_target_status")
    b = b.reset_index(drop=True)
    b["hid"] = np.arange(1, len(b) + 1)
    b["quality_class_model"] = b["quality_class"]
    gap = b[b.bld_id.isin(set(tgt.bld_id))].copy()
    roads = gpd.read_file(ROOT / "reference/tgrac_road_network.gpkg").to_crs(CRS).geometry.intersection(cell)
    roads = roads[~roads.is_empty]
    vf = REPO / "configs/multivillage/villages/damarakunta_verified_facilities.csv"
    if vf.exists():                                                      # audited facilities (scripts/audit_facilities.py --village damarakunta): schools, colleges, hospitals, offices, anganwadis on real buildings
        t = pd.read_csv(vf)
        ft = {"School": "school", "College": "college", "Hospital": "health", "Government Office": "government", "Anganwadi": "anganwadi"}
        from pyproj import Transformer
        xy = Transformer.from_crs(4326, CRS, always_xy=True).transform(t.lon.values, t.lat.values)
        from shapely.geometry import Point
        fac = gpd.GeoDataFrame(dict(fid=np.arange(1, len(t) + 1), name=t["name"].values, facility_type=t.category.map(ft).values), geometry=[Point(x, y) for x, y in zip(*xy)], crs=CRS)
        fac = fac[fac.geometry.within(cell)].reset_index(drop=True)
        fac["fid"] = np.arange(1, len(fac) + 1)
    else:
        f = gpd.read_file(ROOT / "reference/derived/damarakunta_priority_facilities_final_5.gpkg").to_crs(CRS)

        def kind(t):
            t = str(t).lower()
            return "school" if "school" in t else ("health" if ("health" in t or "phc" in t or "hospital" in t or "sub" in t) else ("anganwadi" if "anganwadi" in t else "government"))
        fac = gpd.GeoDataFrame(dict(fid=np.arange(1, len(f) + 1), name=f.facility_name.values, facility_type=[kind(t) for t in f.facility_type]), geometry=f.geometry.values, crs=CRS)
    stage_b_cost = (ROOT / "aligned" / "damarakunta_cost_surface_10m.tif").exists()
    cost, T, shape = cost_from_stage_b(ROOT / "aligned") if stage_b_cost else cost_rebuilt(cfg, cell)
    print("cost surface:", "Stage B aligned cost surface" if stage_b_cost else "REBUILT from aligned_open (WorldCover + DEM, common recipe): approximates Stage B", "|", len(gap), "road-gap houses,", len(fac), "facilities")
    clear = CL.compute_from_arrays(cost, T, shape, list(roads), b, gap, fac, PL.planner_params(cfg), cache_path=out / "clearance_network_v1.pkl", limit_targets=a.limit_targets)
    mosaic = Path(a.mosaic)
    imagery = mosaic.exists()
    if not imagery:
        print("NOTE: no Esri mosaic at", mosaic, "-> grey background: this output is NOT a satellite map; run it on the PC that has the mosaic")
    sc = MM.scene_from_clearance("Damarakunta (village)", "TGRAC village polygon (administrative)", cell, roads, b, gap, fac, clear, mosaic=mosaic if imagery else None, footprint_source="StrongDINOv2Seg + OpenCV (v8)")
    MM.render_master(sc, out / "master_satellite_planning_map.png", dpi=a.dpi)
    MM.write_key_csv(sc, out / "map_facility_key.csv")
    st, v = sc.stats, sc.stats["verify"]
    pd.DataFrame([dict(grid_m=st["grid_m"], clearance_m=st["clearance_m"], house_targets=st["house_targets"], house_routed=st["house_routed"], facility_targets=st["fac_targets"], facility_routed=st["fac_routed"],
                       independent_m=round(st["indep_m"], 1), shared_m=round(st["shared_m"], 1), shared_incl_facilities_m=round(st["combined_m"], 1),
                       saving_vs_independent_pct=round(100 * (1 - st["shared_m"] / st["indep_m"]), 1), **{f"{k}_{m}": v[k][m] for k in v for m in v[k]})]).to_csv(out / "clearance_verification.csv", index=False, lineterminator="\n")
    (out / "RUN_STATUS.md").write_text(f"""# Damarakunta master satellite planning map: run status

Generated by `scripts/make_damarakunta_master_map.py`. The frozen Stage B deliverables are not modified.

* Cost surface: {"Stage B aligned cost surface (Siddipet/Damarakunta/aligned)" if stage_b_cost else "REBUILT from aligned_open (WorldCover + Copernicus DEM, common recipe): an approximation of the Stage B surface. Re-run on the PC that has Siddipet/Damarakunta/aligned/ for the exact surface."}
* Imagery: {"Esri 0.6 m mosaic" if imagery else "NONE (grey background): this file is not a satellite map; re-run where the mosaic exists"}.
* Routing: footprints hard-blocked ({st['clearance_m']:g} m clearance, {st['grid_m']:g} m grid), routes start at the building edge; {st['house_routed']} of {st['house_targets']} house targets and {st['fac_routed']} of {st['fac_targets']} facilities routed;
  drawn routes crossing another footprint: {sum(v[k]['routes_crossing'] for k in v)} ({sum(v[k]['length_inside_other_footprints_m'] for k in v):.1f} m).
* Frozen Stage B (soft penalty mu = 4) for comparison: 28 of 163 house routes cross another footprint, 209.1 m (`DELIVERABLES_DAMARAKUNTA_STAGE_B/.../building_crossings_summary.csv`). The Stage B tables and maps are unchanged.
* Lengths are measured from the building edge; the PMGSY rate (Rs 75 lakh/km, range 60-90) is owner-supplied and unverified; costs are illustrative.
""", encoding="utf-8")
    print("wrote", out / "master_satellite_planning_map.png", "|", {k: (round(x, 1) if isinstance(x, float) else x) for k, x in st.items() if k in ("house_routed", "indep_m", "shared_m", "combined_m")})
    print("verification:", v)


if __name__ == "__main__":
    main()
