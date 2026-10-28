"""Run network-aware shared-route planning for individual Damarakunta building candidates.

Uses plan_network_v2.py helper functions without calling its main(). Compares:
  1) network-aware house-to-road routes, where already-selected route edges can be shared;
  2) independent least-cost routes, where each house routes to reference roads separately;
  3) Stage-A alternative route candidates.

All building candidates are model-derived, unverified targets. Output is a planning experiment,
not proof of real-house identity, land availability, road ownership, or construction readiness.
"""
import argparse
import importlib.util
import json
import math
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import Point
from shapely.ops import nearest_points

CRS = "EPSG:32644"
DEFAULT_ROOT = Path(r"D:\Telangana_Rural_Project\Siddipet\Damarakunta")


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("plan_network_v2_house_network", str(path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load planner helper module: {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    # Compatibility guard for a known typo in the current planner's diagnostics.
    mod.v4is = None
    return mod


def truth(v):
    return str(v).strip().lower() in {"true", "1", "yes", "y"}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=str(DEFAULT_ROOT))
    ap.add_argument("--planner", default=r"D:\Telangana_Rural_Project\scripts\plan_network_v2.py")
    ap.add_argument("--buildings", default=None)
    ap.add_argument("--buildings-layer", default="buildings")
    ap.add_argument("--roads", default=None)
    ap.add_argument("--cost", default=None)
    ap.add_argument("--worldcover", default=None)
    ap.add_argument("--blocked", default=None)
    ap.add_argument("--slope", default=None)
    ap.add_argument("--slope-limit-deg", type=float, default=25.0)
    ap.add_argument("--min-area-m2", type=float, default=10.0)
    ap.add_argument("--quality-keep", default="PLAUSIBLE,REVIEW,UNRESOLVED_MERGE")
    ap.add_argument("--snap-m", type=float, default=30.0)
    ap.add_argument("--max-search-m", type=float, default=1500.0)
    ap.add_argument("--attach-tol-m", type=float, default=15.0)
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--corridor-m", type=float, default=20.0)
    ap.add_argument("--corridor-mults", type=float, nargs="+", default=[3.0, 8.0])
    ap.add_argument("--max-overlap", type=float, default=0.8)
    ap.add_argument("--passes", type=int, default=2)
    ap.add_argument("--building-mult", type=float, default=4.0)
    ap.add_argument("--corner-cut", choices=["forbid", "allow"], default="forbid")
    ap.add_argument("--out-dir", default=None)
    a = ap.parse_args()

    root = Path(a.root)
    paths = {
        "planner": Path(a.planner),
        "buildings": Path(a.buildings) if a.buildings else root / "results" / "v8_instances" / "buildings_v8_full.gpkg",
        "roads": Path(a.roads) if a.roads else root / "reference" / "tgrac_road_network.gpkg",
        "cost": Path(a.cost) if a.cost else root / "aligned" / "damarakunta_cost_surface_10m.tif",
        "worldcover": Path(a.worldcover) if a.worldcover else root / "aligned" / "damarakunta_worldcover_10m.tif",
        "blocked": Path(a.blocked) if a.blocked else root / "aligned" / "damarakunta_prohibited_mask_10m.tif",
        "slope": Path(a.slope) if a.slope else root / "aligned" / "damarakunta_slope_10m.tif",
    }
    out = Path(a.out_dir) if a.out_dir else root / "results" / "individual_house_network_v1"
    if out.exists() and any(out.iterdir()):
        sys.exit(f"STOP: output folder already contains files: {out}\nChoose a new --out-dir; nothing was overwritten.")
    out.mkdir(parents=True, exist_ok=True)
    for k in ("planner", "buildings", "roads", "cost"):
        if not paths[k].exists():
            sys.exit(f"Required input missing ({k}): {paths[k]}")

    print("Importing plan_network_v2 helper functions (planner main() will not execute)...")
    pn = load_module(paths["planner"])
    world_args = argparse.Namespace(
        v4_script="",
        blocked=str(paths["blocked"]) if paths["blocked"].exists() else None,
        slope=str(paths["slope"]) if paths["slope"].exists() else None,
        slope_limit_deg=a.slope_limit_deg,
        water_class=None, builtup_class=None,
        cost=str(paths["cost"]),
        worldcover=str(paths["worldcover"]) if paths["worldcover"].exists() else None,
        builtup_mult=1.0,
        buildings=str(paths["buildings"]), buildings_layer=a.buildings_layer,
        building_quality=a.quality_keep, building_mult=a.building_mult,
        roads=str(paths["roads"]), corner_cut=a.corner_cut,
    )
    W = pn.load_world(world_args)
    grid, roads, road_union, road_cells = W["grid"], W["roads"], W["road_union"], W["road_cells"]
    print(f"Cost grid: {W['H']} x {W['W']} cells at {grid.res:g} m; passable road cells={len(road_cells)}")
    print(f"Hard slope limit: {a.slope_limit_deg:g} degrees")
    for note in W.get("notes", []):
        print("INPUT NOTE:", note)

    bld = gpd.read_file(paths["buildings"], layer=a.buildings_layer)
    if bld.crs is None:
        sys.exit("Building layer has no CRS; refusing to infer coordinates.")
    bld = bld.to_crs(CRS)
    n_in = len(bld)
    if "inside_village" in bld.columns:
        bld = bld[bld["inside_village"].map(truth)].copy()
    n_inside = len(bld)
    if "area_m2" in bld.columns:
        bld = bld[pd.to_numeric(bld["area_m2"], errors="coerce") >= a.min_area_m2].copy()
    n_area = len(bld)
    if "quality_class" in bld.columns:
        keep = [x.strip() for x in a.quality_keep.split(",") if x.strip()]
        bld = bld[bld["quality_class"].isin(keep)].copy()
    bld = bld[bld.geometry.notna() & ~bld.geometry.is_empty].copy().reset_index(drop=True)
    if bld.empty:
        sys.exit("No building targets remain after filters.")
    if "cand_id" not in bld.columns:
        bld["cand_id"] = np.arange(1, len(bld) + 1)
    if "bld_id" not in bld.columns:
        bld["bld_id"] = bld["cand_id"].astype(str)

    # Fixed target point is the polygon edge closest to the existing reference road network.
    # This keeps the starting point comparable across independent and network-aware runs.
    targets, points = [], []
    for num, (_, row) in enumerate(bld.iterrows(), start=1):
        edge_pt = nearest_points(row.geometry, road_union)[0]
        hid = f"H{num:04d}"
        quality = str(row.get("quality_class", "UNKNOWN"))
        detection_status = str(row.get("status", "UNVERIFIED_MODEL_PREDICTION"))
        targets.append({
            "id": hid, "kind": "HOUSE_CANDIDATE", "name": hid,
            "ftype": "MODEL_DERIVED_BUILDING_CANDIDATE", "pt": edge_pt,
            "weight": 1.0, "weight_rule": "equal_house_weight",
            "n_buildings": 1, "n_unresolved": int(quality == "UNRESOLVED_MERGE"),
            "coord_status": "UNVERIFIED_MODEL_PREDICTION",
            "cand_id": str(row.get("cand_id", num)),
            "bld_id": str(row.get("bld_id", row.get("cand_id", num))),
            "quality_class": quality, "detection_status": detection_status,
            "area_m2": float(row.get("area_m2", row.geometry.area)) if pd.notna(row.get("area_m2", row.geometry.area)) else None,
            "nearest_road_gap_m": float(row.geometry.distance(road_union)),
            "source_geometry": row.geometry,
        })
        points.append({"house_route_id": hid, "cand_id": str(row.get("cand_id", num)),
                       "bld_id": str(row.get("bld_id", row.get("cand_id", num))),
                       "quality_class": quality, "detection_status": detection_status,
                       "area_m2": targets[-1]["area_m2"], "nearest_road_gap_m": targets[-1]["nearest_road_gap_m"],
                       "geometry": edge_pt})

    tmap = {t["id"]: t for t in targets}
    P = dict(attach_tol_m=a.attach_tol_m, max_search_m=a.max_search_m, snap_m=a.snap_m,
             k=a.k, corridor_m=a.corridor_m, corridor_mults=a.corridor_mults,
             max_overlap=a.max_overlap, passes=a.passes, budget=None)
    print(f"Targets: {len(targets)} (source={n_in}, inside={n_inside}, area-filtered={n_area})")
    print("Running two-stage network-aware planner for individual building candidates...")
    result = pn.plan(grid, road_union, road_cells, targets, P)
    sel, indep, fails, straight = result["sel"], result["indep"], result["fails"], result["straight"]
    ver = pn.verify_network(sel, road_union, grid, a.attach_tol_m)
    for tid, route in sel.items():
        route.update(ver.get(tid, {}))

    # Target status table includes targets not selected/feasible.
    rows = []
    for t in targets:
        tid = t["id"]
        nr = sel.get(tid)
        ir = indep.get(tid)
        sr = straight.get(tid, {})
        connected = bool(nr and nr.get("connected_to_roads", False))
        rows.append({
            "house_route_id": tid, "cand_id": t["cand_id"], "bld_id": t["bld_id"],
            "quality_class": t["quality_class"], "detection_status": t["detection_status"],
            "area_m2": t["area_m2"], "nearest_road_gap_m": round(t["nearest_road_gap_m"], 2),
            "network_status": "CONNECTED_TO_CURRENT_PLANNED_NETWORK_UNVERIFIED" if connected else ("FAILED_OR_UNSERVED" if nr is None or tid in fails else "ATTACHMENT_NOT_VERIFIED"),
            "network_failure_reason": fails.get(tid, "" if nr else "NO_NETWORK_ROUTE_SELECTED"),
            "network_attach_to": nr.get("attach_to", "") if nr else "",
            "network_route_length_m": round(float(nr["own_len_m"]), 2) if nr else None,
            "network_route_cost": round(float(nr["cost"]), 4) if nr and nr.get("cost") is not None else None,
            "network_endpoint_dist_m": nr.get("endpoint_dist_m") if nr else None,
            "independent_status": "ROUTE_GENERATED_UNVERIFIED" if ir else "FAILED",
            "independent_route_length_m": round(float(ir["own_len_m"]), 2) if ir else None,
            "independent_route_cost": round(float(ir["cost"]), 4) if ir and ir.get("cost") is not None else None,
            "straight_line_feasible": sr.get("feasible", False),
            "straight_line_length_m": round(float(sr["own_len_m"]), 2) if sr.get("own_len_m") is not None else None,
            "interpretation": "Candidate polygon may not represent one confirmed house; routes are unverified planning alternatives.",
            "geometry": t["pt"],
        })
    status_gdf = gpd.GeoDataFrame(rows, geometry="geometry", crs=CRS)
    status_gdf.drop(columns="geometry").to_csv(out / "house_network_status.csv", index=False)
    status_gdf.to_file(out / "individual_house_network_v1.gpkg", layer="house_target_status", driver="GPKG")

    def write_routes(layer, route_list, extra_fn=None):
        recs = []
        for r in route_list:
            tid = r.get("target", "")
            t = tmap.get(tid, {})
            geom = r.get("geom")
            if geom is None or geom.is_empty:
                continue
            rec = {
                "house_route_id": tid, "cand_id": t.get("cand_id", ""),
                "quality_class": t.get("quality_class", "UNKNOWN"),
                "mode": r.get("mode", layer), "route_length_m": round(float(r.get("own_len_m", geom.length)), 2),
                "route_cost": round(float(r["cost"]), 4) if r.get("cost") is not None else None,
                "attach_to": r.get("attach_to", ""), "connected": bool(r.get("connected_to_roads", False)),
                "route_status": "UNVERIFIED_PLANNING_ALTERNATIVE_NOT_A_ROAD", "geometry": geom,
            }
            if extra_fn:
                rec.update(extra_fn(r))
            recs.append(rec)
        if recs:
            gpd.GeoDataFrame(recs, geometry="geometry", crs=CRS).to_file(out / "individual_house_network_v1.gpkg", layer=layer, driver="GPKG", mode="a")
        print(f"{layer}: {len(recs)} geometries")
        return recs

    selected = [r for r in sel.values() if r.get("geom") is not None]
    independent = list(indep.values())
    straight_routes = [dict(target=tid, **{k: v for k, v in r.items() if k != "target"}) for tid, r in straight.items()]
    # GPKG route outputs use separate layers; preserve independent baseline and Stage-A candidates.
    network_recs = write_routes("routes_network_aware", selected, lambda r: {
        "endpoint_dist_m": r.get("endpoint_dist_m"), "connected_to_roads": bool(r.get("connected_to_roads", False))})
    independent_recs = write_routes("routes_independent", independent)
    write_routes("routes_straight_line", straight_routes, lambda r: {"feasible": bool(r.get("feasible", False))})
    all_alts = [r for arr in result.get("alts", {}).values() for r in arr]
    write_routes("stageA_alternatives", all_alts)

    # Summaries use the planner's same unique-grid-edge accounting as its facility/cluster experiments.
    def sum_lengths(recs):
        return round(sum(float(r["route_length_m"]) for r in recs), 2)
    network_len = sum_lengths(network_recs)
    independent_len = sum_lengths(independent_recs)
    connected_count = int(status_gdf["network_status"].str.startswith("CONNECTED").sum())
    network_unique = None
    independent_unique = None
    try:
        network_unique = float(pn.unique_edge_metrics(selected).get("unique_len_m"))
        independent_unique = float(pn.unique_edge_metrics(independent).get("unique_len_m"))
    except Exception as e:
        print("NOTE: unique-edge metric helper could not summarize this run:", e)

    summary = {
        "project_area": "Damarakunta, Siddipet, Telangana",
        "targets_source_count": n_in, "inside_village_count": n_inside,
        "after_min_area_count": n_area, "targets_planned": len(targets),
        "network_connected_targets": connected_count,
        "independent_routes_generated": len(independent_recs),
        "network_route_geometries": len(network_recs),
        "route_length_sum_network_aware_m": network_len,
        "route_length_sum_independent_m": independent_len,
        "unique_grid_edge_length_network_aware_m": network_unique,
        "unique_grid_edge_length_independent_m": independent_unique,
        "shared_network_unique_length_reduction_m": (round(independent_unique - network_unique, 2) if network_unique is not None and independent_unique is not None else None),
        "slope_limit_deg": a.slope_limit_deg,
        "hard_constraints_resolved": W.get("constraints_resolved", {}),
        "planner_notes": W.get("notes", []),
        "parameters": {"k": a.k, "corridor_m": a.corridor_m, "corridor_mults": a.corridor_mults,
                       "max_overlap": a.max_overlap, "passes": a.passes, "snap_m": a.snap_m,
                       "max_search_m": a.max_search_m, "attach_tol_m": a.attach_tol_m,
                       "building_mult": a.building_mult, "corner_cut": a.corner_cut},
        "caveat": "These are planning alternatives based on model-derived building polygons and reference roads; not field-verified houses or roads.",
    }
    (out / "house_network_summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    # Also emit planner's common comparison metrics for the paper, where functions support this schema.
    try:
        metrics = pd.DataFrame([
            pn.summarise("network_aware", selected, tmap, len(targets)),
            pn.summarise("independent_least_cost", independent, tmap, len(targets)),
            pn.summarise("straight_line", straight_routes, tmap, len(targets), feasible_straight=True),
        ])
        metrics.to_csv(out / "house_network_plan_comparison.csv", index=False)
        print("Wrote house_network_plan_comparison.csv")
    except Exception as e:
        print("NOTE: comparison helper did not return table; main length metrics are in summary:", e)

    # Independent control checks.
    route_counts = status_gdf["network_status"].value_counts(dropna=False).to_dict()
    quality_counts = status_gdf.groupby(["quality_class", "network_status"], dropna=False).size().reset_index(name="count")
    quality_counts.to_csv(out / "house_network_quality_summary.csv", index=False)
    print("\n=== INDIVIDUAL HOUSE SHARED-NETWORK SUMMARY ===")
    print(json.dumps({**summary, "network_status_counts": route_counts,
                      "quality_status_counts": quality_counts.to_dict(orient="records")}, indent=2, default=str))
    print("\nOutputs:")
    for p in sorted(out.iterdir()):
        print(" ", p)
    print("Reminder: unverified planning alternatives; not construction approval or verified access.")


if __name__ == "__main__":
    main()
