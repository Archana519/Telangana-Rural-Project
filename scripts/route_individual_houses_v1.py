"""Generate individual building-edge to existing TGRAC-road least-cost routes for Damarakunta.

This is a separate, non-overwriting workflow. Routes are planning candidates based on
unverified building predictions and reference road geometries; they are not field-verified roads.
"""
import argparse
import importlib.util
import json
import math
import os
import sys
import traceback
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from shapely.geometry import Point
from shapely.ops import nearest_points

ROOT = Path(r"D:\Telangana_Rural_Project\Siddipet\Damarakunta")
CRS = "EPSG:32644"


def load_planner_module(path: Path):
    spec = importlib.util.spec_from_file_location("plan_network_v2_house_route", str(path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load planner module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def bool_value(v):
    return str(v).strip().lower() in {"true", "1", "yes", "y"}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=str(ROOT), help="Damarakunta project directory")
    ap.add_argument("--planner", default=r"D:\Telangana_Rural_Project\scripts\plan_network_v2.py")
    ap.add_argument("--buildings", default=None)
    ap.add_argument("--buildings-layer", default="buildings")
    ap.add_argument("--roads", default=None)
    ap.add_argument("--cost", default=None)
    ap.add_argument("--worldcover", default=None)
    ap.add_argument("--blocked", default=None)
    ap.add_argument("--slope", default=None)
    ap.add_argument("--slope-limit-deg", type=float, default=None,
                    help="Optional hard slope threshold; omitted means slope raster is not a hard constraint")
    ap.add_argument("--min-area-m2", type=float, default=10.0)
    ap.add_argument("--quality-keep", default="PLAUSIBLE,REVIEW,UNRESOLVED_MERGE")
    ap.add_argument("--snap-m", type=float, default=30.0,
                    help="maximum building-edge to passable-grid-cell snap distance")
    ap.add_argument("--max-search-m", type=float, default=1500.0,
                    help="maximum path-search radius/distance according to planner Grid.search")
    ap.add_argument("--attach-tol-m", type=float, default=15.0,
                    help="maximum final grid endpoint distance to reference road geometry")
    ap.add_argument("--building-mult", type=float, default=4.0,
                    help="soft cost multiplier over predicted building polygons; 1 disables it")
    ap.add_argument("--corner-cut", choices=["forbid", "allow"], default="forbid")
    ap.add_argument("--out-dir", default=None)
    a = ap.parse_args()

    root = Path(a.root)
    buildings_path = Path(a.buildings) if a.buildings else root / "results" / "v8_instances" / "buildings_v8_full.gpkg"
    roads_path = Path(a.roads) if a.roads else root / "reference" / "tgrac_road_network.gpkg"
    cost_path = Path(a.cost) if a.cost else root / "aligned" / "damarakunta_cost_surface_10m.tif"
    worldcover_path = Path(a.worldcover) if a.worldcover else root / "aligned" / "damarakunta_worldcover_10m.tif"
    blocked_path = Path(a.blocked) if a.blocked else root / "aligned" / "damarakunta_prohibited_mask_10m.tif"
    slope_path = Path(a.slope) if a.slope else root / "aligned" / "damarakunta_slope_10m.tif"
    out_dir = Path(a.out_dir) if a.out_dir else root / "results" / "individual_house_routing_v1"
    planner_path = Path(a.planner)

    # Refuse to overwrite outputs, including prior partial runs.
    if out_dir.exists() and any(out_dir.iterdir()):
        sys.exit(f"STOP: output folder already contains files: {out_dir}\nChoose a new --out-dir. Nothing was overwritten.")
    out_dir.mkdir(parents=True, exist_ok=True)

    for p in [planner_path, buildings_path, roads_path, cost_path]:
        if not p.exists():
            sys.exit(f"Required input does not exist: {p}")
    if not worldcover_path.exists():
        print(f"WARNING: WorldCover missing, continuing without it: {worldcover_path}")
        worldcover_arg = None
    else:
        worldcover_arg = str(worldcover_path)
    if not blocked_path.exists():
        print(f"WARNING: prohibited-area raster missing, continuing without it: {blocked_path}")
        blocked_arg = None
    else:
        blocked_arg = str(blocked_path)
    if not slope_path.exists():
        print(f"WARNING: slope raster missing: {slope_path}")
        slope_arg = None
    else:
        slope_arg = str(slope_path)

    print("Loading existing planner helpers (module import only; planner main() will not run)...")
    pn = load_planner_module(planner_path)
    # Compatibility guard: the supplied planner excerpt references v4is instead of v4
    # in one diagnostic dictionary field. Define it as None so load_world can continue.
    pn.v4is = None

    # Explicit argument bundle for load_world(). Use v4_script='' so load_world does not
    # import/rely on optional V4 constants; prohibited raster is supplied explicitly above.
    world_args = argparse.Namespace(
        v4_script="", blocked=blocked_arg, slope=slope_arg,
        slope_limit_deg=a.slope_limit_deg,
        water_class=None, builtup_class=None,
        cost=str(cost_path), worldcover=worldcover_arg,
        builtup_mult=1.0,
        buildings=str(buildings_path), buildings_layer=a.buildings_layer,
        building_quality=a.quality_keep,
        building_mult=a.building_mult,
        roads=str(roads_path), corner_cut=a.corner_cut,
    )
    W = pn.load_world(world_args)
    grid, roads, road_union, road_cells = W["grid"], W["roads"], W["road_union"], W["road_cells"]
    attach_tol = a.attach_tol_m

    print(f"Loading buildings: {buildings_path}")
    bld = gpd.read_file(buildings_path, layer=a.buildings_layer)
    if bld.crs is None:
        sys.exit("Building layer has no CRS; refusing to guess its coordinates.")
    bld = bld.to_crs(CRS)
    if "inside_village" in bld.columns:
        before = len(bld)
        bld = bld[bld["inside_village"].map(bool_value)].copy()
        print(f"inside_village filter: {before} -> {len(bld)}")
    if "area_m2" in bld.columns:
        bld = bld[pd.to_numeric(bld["area_m2"], errors="coerce") >= a.min_area_m2].copy()
    if "quality_class" in bld.columns:
        keep = [x.strip() for x in a.quality_keep.split(",") if x.strip()]
        bld = bld[bld["quality_class"].isin(keep)].copy()
    bld = bld[bld.geometry.notna() & ~bld.geometry.is_empty].copy().reset_index(drop=True)
    if bld.empty:
        sys.exit("No building candidates remain after inside-village/area/quality filters.")
    if "cand_id" not in bld.columns:
        bld["cand_id"] = np.arange(1, len(bld) + 1)
    if "bld_id" not in bld.columns:
        bld["bld_id"] = bld["cand_id"].astype(str)

    print(f"Targets to process: {len(bld)}")
    print(f"Passable road grid cells: {len(road_cells)}")
    print(f"Cost grid: {W['H']} rows x {W['W']} cols, {W['grid'].res:g} m cells")
    for n in W.get("notes", []):
        print("INPUT NOTE:", n)

    status_rows, route_rows = [], []
    total = len(bld)
    for num, (_, row) in enumerate(bld.iterrows(), start=1):
        geom = row.geometry
        rec = {
            "house_route_id": f"H{num:04d}",
            "bld_id": str(row.get("bld_id", row.get("cand_id", num))),
            "cand_id": str(row.get("cand_id", num)),
            "quality_class": str(row.get("quality_class", "UNKNOWN")),
            "detection_status": str(row.get("status", "UNVERIFIED_MODEL_PREDICTION")),
            "area_m2": float(row.get("area_m2", geom.area)) if pd.notna(row.get("area_m2", geom.area)) else None,
            "inside_village": True,
            "edge_to_nearest_road_m": None,
            "start_snap_m": None,
            "path_grid_length_m": None,
            "route_geometry_length_m": None,
            "end_snap_to_road_m": None,
            "route_cost": None,
            "hard_violations": None,
            "route_status": "NOT_PROCESSED",
            "failure_reason": "",
            "endpoint_within_tolerance": False,
            "route_quality_warning": "MODEL_DERIVED_BUILDING;REFERENCE_ROADS_NOT_FIELD_VERIFIED",
            "geometry": geom.representative_point(),
        }
        try:
            # Begin at the predicted building footprint edge nearest to any existing road.
            house_edge, near_road = nearest_points(geom, road_union)
            edge_gap = float(house_edge.distance(near_road))
            rec["edge_to_nearest_road_m"] = round(edge_gap, 2)
            snapped = grid.snap(house_edge.x, house_edge.y, a.snap_m)
            if snapped is None:
                rec["route_status"] = "FAILED_NO_PASSABLE_START_WITHIN_SNAP"
                rec["failure_reason"] = f"No passable cell within {a.snap_m:g} m of predicted footprint edge"
            else:
                start_idx, start_snap = snapped
                rec["start_snap_m"] = round(float(start_snap), 2)
                found = grid.search(start_idx, road_cells, limit_m=a.max_search_m)
                if isinstance(found, str):
                    rec["route_status"] = "FAILED_NO_PATH_WITHIN_SEARCH_LIMIT"
                    rec["failure_reason"] = str(found)
                else:
                    made = pn.make_route(
                        grid, rec["house_route_id"], house_edge,
                        float(start_snap), found, "INDIVIDUAL_HOUSE_TO_EXISTING_ROAD",
                        snap_target=road_union, tol_m=attach_tol,
                    )
                    rec["path_grid_length_m"] = round(float(made["path_len_m"]), 2)
                    rec["route_geometry_length_m"] = round(float(made["geom"].length), 2)
                    rec["end_snap_to_road_m"] = round(float(made["end_snap_m"]), 2)
                    rec["route_cost"] = round(float(made["cost"]), 4)
                    rec["hard_violations"] = int(made["hard_violations"])
                    rec["endpoint_within_tolerance"] = bool(made["end_snap_m"] <= attach_tol)
                    if made["endpoint_ok"]:
                        rec["route_status"] = "ROUTE_GENERATED_GRID_CHECKS_PASS_UNVERIFIED"
                    else:
                        rec["route_status"] = "ROUTE_GENERATED_REQUIRES_REVIEW"
                        reasons = []
                        if made["end_snap_m"] > attach_tol:
                            reasons.append(f"road endpoint gap {made['end_snap_m']:.2f} m exceeds {attach_tol:g} m")
                        if made["hard_violations"]:
                            reasons.append(f"{made['hard_violations']} sampled geometry positions fall in impassable cells")
                        rec["failure_reason"] = "; ".join(reasons)
                    route_rows.append({
                        "house_route_id": rec["house_route_id"],
                        "bld_id": rec["bld_id"], "cand_id": rec["cand_id"],
                        "quality_class": rec["quality_class"],
                        "detection_status": rec["detection_status"],
                        "edge_to_nearest_road_m": rec["edge_to_nearest_road_m"],
                        "start_snap_m": rec["start_snap_m"],
                        "path_grid_length_m": rec["path_grid_length_m"],
                        "route_geometry_length_m": rec["route_geometry_length_m"],
                        "end_snap_to_road_m": rec["end_snap_to_road_m"],
                        "route_cost": rec["route_cost"],
                        "hard_violations": rec["hard_violations"],
                        "route_status": rec["route_status"],
                        "failure_reason": rec["failure_reason"],
                        "geometry": made["geom"],
                    })
        except Exception as e:
            rec["route_status"] = "FAILED_EXCEPTION"
            rec["failure_reason"] = f"{type(e).__name__}: {e}"
            print(f"WARNING {rec['house_route_id']} / cand_id={rec['cand_id']}: {type(e).__name__}: {e}")
        status_rows.append(rec)
        if num % 10 == 0 or num == total:
            print(f"Processed {num}/{total}")

    status = pd.DataFrame(status_rows)
    routes = pd.DataFrame(route_rows)
    # Human-readable, complete all-target table, retaining both route outcomes and failed targets.
    status.drop(columns=["geometry"]).to_csv(out_dir / "house_route_status.csv", index=False)
    counts = status["route_status"].value_counts(dropna=False).to_dict()
    quality_counts = status.groupby(["quality_class", "route_status"], dropna=False).size().rename("count").reset_index()
    quality_counts.to_csv(out_dir / "house_route_quality_summary.csv", index=False)

    # Write all building target points and only generated route lines as separate layers.
    status_gdf = gpd.GeoDataFrame(status_rows, geometry="geometry", crs=CRS)
    gpkg_path = out_dir / "individual_house_routes_v1.gpkg"
    status_gdf.to_file(gpkg_path, layer="house_route_status_points", driver="GPKG")
    if not routes.empty:
        routes_gdf = gpd.GeoDataFrame(routes, geometry="geometry", crs=CRS)
        routes_gdf.to_file(gpkg_path, layer="house_routes", driver="GPKG")
    else:
        print("WARNING: no route geometry was generated; GPKG contains status points only.")

    # Machine-readable run notes and a concise console summary.
    summary = {
        "project_area": "Damarakunta, Siddipet, Telangana",
        "input_buildings": str(buildings_path),
        "input_roads": str(roads_path),
        "cost_raster": str(cost_path),
        "prohibited_raster": str(blocked_path) if blocked_arg else None,
        "slope_raster": str(slope_path) if slope_arg else None,
        "slope_limit_deg": a.slope_limit_deg,
        "targets_attempted": int(len(status)),
        "routes_with_geometry": int(len(routes)),
        "route_status_counts": {str(k): int(v) for k, v in counts.items()},
        "quality_status_counts": quality_counts.to_dict(orient="records"),
        "interpretation": "All routes are unverified planning alternatives from model-derived building polygons to reference-road geometry. Route generation does not establish that a real house or road exists, that land is available, or that a route is construction-ready.",
        "parameters": {"min_area_m2": a.min_area_m2, "quality_keep": a.quality_keep, "snap_m": a.snap_m,
                       "max_search_m": a.max_search_m, "attach_tol_m": attach_tol,
                       "building_mult": a.building_mult, "corner_cut": a.corner_cut},
        "planner_notes": W.get("notes", []),
        "hard_constraints_resolved": W.get("constraints_resolved", {}),
    }
    (out_dir / "run_summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    print("\n=== INDIVIDUAL HOUSE ROUTING SUMMARY ===")
    print(f"Targets attempted: {len(status)}")
    print(f"Routes with geometry: {len(routes)}")
    for k, v in counts.items():
        print(f"  {k}: {v}")
    print("\nOutputs:")
    print(" ", gpkg_path)
    print(" ", out_dir / "house_route_status.csv")
    print(" ", out_dir / "house_route_quality_summary.csv")
    print(" ", out_dir / "run_summary.json")
    print("\nReminder: these are unverified planning routes, not construction approvals or proof of real-house access.")


if __name__ == "__main__":
    main()
