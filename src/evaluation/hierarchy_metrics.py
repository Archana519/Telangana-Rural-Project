"""Multi-level metrics and sensitivity logger for the hierarchical routing levels.

For every level it writes (never overwriting raw inputs):
  <out>/<level>/<level>_routes.gpkg      layers: routes_shared, routes_independent, nodes
  <out>/<level>/<level>_summary.json     all headline numbers + provenance flags (data source, fallbacks, synthetic?)
  <out>/<level>/<level>_metrics.csv      long table  metric,value
  <out>/<level>/<level>_override.csv     per exempt facility: route with vs without the local penalty override
  <out>/<level>/<level>_omission.csv     one row per (omitted fraction, seed): length change, unserved weight, ...
and <out>/hierarchy_summary.{csv,json} across levels.

Definitions (match the manuscript, Eqs. kappa/delta/exposure):
  saving_pct        = (L_independent_unique - L_shared_unique) / L_independent_unique * 100
  coverage          = routed nodes / nodes
  delta_L_pct       = (L(T) - L(T \\ M)) / L(T) * 100            (positive = plan SHORTER after omission)
  unserved_weight   = full unit weight - weight of routed units in the omission run (units = houses / GP hubs / mandals)
  length_per_weight = unique length / served weight           (comparable across omission scenarios)
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Callable, Optional

import numpy as np

UNIT_KINDS = {"gp": {"hamlet"}, "mandal": {"gp_hub"}, "district": {"mandal_hq"}}


def _f(x):
    if isinstance(x, (np.floating, np.integer)):
        return x.item()
    return x


def _clean(o):
    if isinstance(o, dict):
        return {str(k): _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple, set)):
        return [_clean(v) for v in o]
    return _f(o)


def _unit_weight(nodes, kinds):
    return float(sum(n.weight for n in nodes if n.kind in kinds))


def _served_weight(result, nodes, kinds):
    by = {n.id: n for n in nodes}
    return float(sum(by[i].weight for i in result.routed_ids if i in by and by[i].kind in kinds))


def override_table(problem, nodes) -> list:
    """Per exempt node: shared-plan route with vs without the local penalty override (detour reduction)."""
    exempt = [n for n in nodes if n.exempt]
    if not exempt or not hasattr(problem, "override_discs"):
        return []
    with_o = problem.solve(nodes, use_override=True, mode="shared")
    without = problem.solve(nodes, use_override=False, mode="shared")
    rows = []
    for n in exempt:
        a, b = without.routes.get(n.id), with_o.routes.get(n.id)
        if a is None or b is None:
            rows.append(dict(node=n.id, kind=n.kind, status="NOT_ROUTED"))
            continue
        rows.append(dict(node=n.id, kind=n.kind, status="ROUTED", length_without_m=a.length_m, length_with_m=b.length_m,
                         detour_reduction_m=a.length_m - b.length_m, cost_without=a.cost, cost_with=b.cost,
                         cost_reduction_pct=(100.0 * (a.cost - b.cost) / a.cost) if a.cost > 0 else 0.0))
    exempt_ids = {n.id for n in exempt}
    changed = 0
    for nid, r in with_o.routes.items():
        if nid in exempt_ids or nid not in without.routes:
            continue
        if not r.geometry.equals_exact(without.routes[nid].geometry, 1e-6):
            changed += 1
    rows.append(dict(node="_OTHER_ROUTES_CHANGED", kind="", status="count", length_without_m="", length_with_m="",
                     detour_reduction_m="", cost_without="", cost_with="", cost_reduction_pct=changed))
    rows.append(dict(node="_NETWORK_UNIQUE_LENGTH", kind="", status="m", length_without_m=without.unique_length_m,
                     length_with_m=with_o.unique_length_m, detour_reduction_m=without.unique_length_m - with_o.unique_length_m,
                     cost_without="", cost_with="", cost_reduction_pct=""))
    return rows


def omission_table(problem, nodes, level, fractions, seeds, omit_fn: Optional[Callable] = None, protected_kinds=()) -> list:
    """Re-plan after removing a fraction of the units (simulated detection false negatives).

    omit_fn(fraction, seed) -> (nodes_after_omission, n_units_omitted); default removes random unit nodes.
    """
    kinds = UNIT_KINDS[level]
    base = problem.solve(nodes, mode="shared")
    full_w = _unit_weight(nodes, kinds)
    base_served = _served_weight(base, nodes, kinds)
    rows = [dict(scenario="baseline", fraction=0.0, seed=-1, units_omitted=0, routed=len(base.routed_ids),
                 unique_length_m=base.unique_length_m, delta_L_pct=0.0, unserved_weight=full_w - base_served,
                 coverage_weight_pct=100.0 * base_served / full_w if full_w else 100.0,
                 length_per_served_weight_m=base.unique_length_m / base_served if base_served else float("nan"))]
    units = [n for n in nodes if n.kind in kinds]
    for frac in fractions:
        for seed in seeds:
            if omit_fn is not None:
                sub, k = omit_fn(frac, seed)
            else:
                rng = np.random.default_rng(seed)
                k = int(round(frac * len(units)))
                drop = {units[i].id for i in rng.choice(len(units), size=k, replace=False)} if k else set()
                sub = [n for n in nodes if n.id not in drop]
            r = problem.solve(sub, mode="shared")
            served = _served_weight(r, sub, kinds)
            rows.append(dict(scenario=f"omit_{int(round(frac * 100))}pct", fraction=frac, seed=seed, units_omitted=k,
                             routed=len(r.routed_ids), unique_length_m=r.unique_length_m,
                             delta_L_pct=100.0 * (base.unique_length_m - r.unique_length_m) / base.unique_length_m
                             if base.unique_length_m else 0.0,
                             unserved_weight=full_w - served,
                             coverage_weight_pct=100.0 * served / full_w if full_w else 100.0,
                             length_per_served_weight_m=r.unique_length_m / served if served else float("nan")))
    return rows


def _write_csv(path: Path, rows: list):
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow({k: _f(r.get(k, "")) for k in keys})


def _routes_gdf(result, crs):
    import geopandas as gpd
    recs = [dict(route_id=i, kind=r.kind, length_m=r.length_m, cost=r.cost, attached_to=r.attached_to,
                 snap_m=r.snap_m, geometry=r.geometry) for i, r in result.routes.items()]
    return gpd.GeoDataFrame(recs, geometry="geometry", crs=crs) if recs else \
        gpd.GeoDataFrame({"route_id": [], "geometry": []}, geometry="geometry", crs=crs)


def evaluate_level(level: str, problem, nodes: list, out_dir, crs: str, fractions=(0.1, 0.2), seeds=(11, 12, 13),
                   provenance: Optional[dict] = None, omit_fn: Optional[Callable] = None) -> dict:
    """Run shared + independent plans, the override comparison and the omission sensitivity; write all outputs."""
    import geopandas as gpd
    from shapely.geometry import Point
    out = Path(out_dir) / level
    out.mkdir(parents=True, exist_ok=True)
    shared = problem.solve(nodes, use_override=True, mode="shared")
    indep = problem.solve(nodes, use_override=True, mode="independent")
    kinds = UNIT_KINDS[level]
    full_w = _unit_weight(nodes, kinds)
    served = _served_weight(shared, nodes, kinds)
    ov = override_table(problem, nodes)
    om = omission_table(problem, nodes, level, fractions, seeds, omit_fn)
    n = len([x for x in nodes if x.kind != "district_hq"])
    summary = dict(
        level=level, n_nodes=n, n_routed_shared=len(shared.routed_ids), n_failed_shared=len(shared.failures),
        coverage_pct=100.0 * len(shared.routed_ids) / n if n else 100.0,
        connected_any_road=len(shared.connected_any_road), connected_main_component=len(shared.connected_main),
        shared_unique_length_m=shared.unique_length_m, shared_total_length_m=shared.total_length_m,
        independent_unique_length_m=indep.unique_length_m, independent_total_length_m=indep.total_length_m,
        saving_vs_independent_unique_pct=(100.0 * (indep.unique_length_m - shared.unique_length_m) / indep.unique_length_m)
        if indep.unique_length_m else 0.0,
        saving_vs_independent_total_pct=(100.0 * (indep.total_length_m - shared.total_length_m) / indep.total_length_m)
        if indep.total_length_m else 0.0,
        shared_new_construction_m=shared.meta.get("new_construction_m", shared.unique_length_m),
        shared_on_existing_road_m=shared.meta.get("on_existing_road_m", 0.0),
        independent_new_construction_m=indep.meta.get("new_construction_m", indep.unique_length_m),
        shared_unique_cost=shared.unique_cost, unit_weight_total=full_w, unit_weight_served=served,
        length_per_served_weight_m=shared.unique_length_m / served if served else float("nan"),
        detour_reduction_m_total=float(sum(r["detour_reduction_m"] for r in ov
                                           if r.get("status") == "ROUTED" and r["detour_reduction_m"] != "")),
        other_routes_changed_by_override=int(next((r["cost_reduction_pct"] for r in ov
                                                   if r["node"] == "_OTHER_ROUTES_CHANGED"), 0) or 0),
        omission_max_delta_L_pct=max((r["delta_L_pct"] for r in om), default=0.0),
        omission_max_unserved_weight=max((r["unserved_weight"] for r in om), default=0.0),
        failures=shared.failures, shared_meta=shared.meta, provenance=provenance or {})
    # ---- files
    gpkg = out / f"{level}_routes.gpkg"
    if gpkg.exists():
        gpkg.unlink()
    _routes_gdf(shared, crs).to_file(gpkg, layer="routes_shared", driver="GPKG")
    _routes_gdf(indep, crs).to_file(gpkg, layer="routes_independent", driver="GPKG")
    gpd.GeoDataFrame([dict(node_id=x.id, kind=x.kind, weight=x.weight, exempt=x.exempt, routed=x.id in shared.routed_ids,
                           geometry=Point(x.x, x.y)) for x in nodes], geometry="geometry", crs=crs
                     ).to_file(gpkg, layer="nodes", driver="GPKG")
    (out / f"{level}_summary.json").write_text(json.dumps(_clean(summary), indent=2), encoding="utf-8")
    flat = [dict(metric=k, value=_f(v)) for k, v in summary.items() if not isinstance(v, (dict, list))]
    _write_csv(out / f"{level}_metrics.csv", flat)
    _write_csv(out / f"{level}_override.csv", ov)
    _write_csv(out / f"{level}_omission.csv", om)
    summary["_paths"] = dict(gpkg=str(gpkg), summary=str(out / f"{level}_summary.json"))
    return summary


def write_hierarchy_summary(out_dir, summaries: list):
    out = Path(out_dir)
    cols = ["level", "n_nodes", "n_routed_shared", "coverage_pct", "shared_unique_length_m", "shared_new_construction_m",
            "independent_unique_length_m", "independent_new_construction_m",
            "saving_vs_independent_unique_pct", "detour_reduction_m_total", "omission_max_delta_L_pct",
            "omission_max_unserved_weight"]
    rows = [{c: _f(s.get(c, "")) for c in cols} | {"data_source": s.get("provenance", {}).get("data_source", "")}
            for s in summaries]
    _write_csv(out / "hierarchy_summary.csv", rows)
    (out / "hierarchy_summary.json").write_text(json.dumps(_clean([{k: v for k, v in s.items() if k != "_paths"}
                                                                  for s in summaries]), indent=2), encoding="utf-8")
    return rows
