"""Steps 3-5 of the shared pipeline: targets from footprints, Stage B planner (scripts/plan_network_v2.py, imported unchanged), baselines,
footprint-penalty sensitivity and omission scenarios. Every village runs through exactly this code."""
from __future__ import annotations

import importlib.util
import math
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import geopandas as gpd
from rasterio.features import rasterize
from shapely.geometry import Point
from shapely.ops import unary_union

REPO = Path(__file__).resolve().parents[2]
_PN = None


def pn():
    """The Stage B planner module, loaded once, unchanged."""
    global _PN
    if _PN is None:
        spec = importlib.util.spec_from_file_location("plan_network_v2", REPO / "scripts" / "plan_network_v2.py")
        m = importlib.util.module_from_spec(spec)
        sys.modules["plan_network_v2"] = m
        spec.loader.exec_module(m)
        _PN = m
    return _PN


def planner_params(cfg, **over) -> dict:
    c = cfg["planner"]
    p = dict(k=c["k"], corridor_m=c["corridor_m"], corridor_mults=tuple(c["corridor_mults"]), max_overlap=c["max_overlap"], max_search_m=c["max_search_m"],
             snap_m=c["snap_m"], attach_tol_m=c["attach_tol_m"], passes=c["passes"], budget=None, attach=True)
    p.update(over)
    return p


class World:
    """Grid + road network for one (cost surface, footprint penalty) combination."""

    def __init__(self, cost, transform, shape, roads_geoms, footprints, mu: float, corner_cut=False):
        P = pn()
        H, W = shape
        mult = np.ones((H, W))
        if mu != 1.0 and len(footprints):
            bm = rasterize([(g, 1) for g in footprints], out_shape=(H, W), transform=transform, fill=0, all_touched=False, dtype="uint8").astype(bool)
            mult[bm] *= mu
        self.mu, self.cost, self.T, self.shape = mu, cost, transform, shape
        self.grid = P.Grid(cost, transform, hard=None, mult=mult, corner_cut=corner_cut)
        lines = [g for g in roads_geoms if g is not None and not g.is_empty]
        self.road_union = unary_union(lines)
        rr = rasterize([(g, 1) for g in lines], out_shape=(H, W), transform=transform, fill=0, all_touched=True, dtype="uint8").astype(bool)
        pr = self.grid.pass_np[1:-1, 1:-1]
        rows, cols = np.nonzero(rr & pr)
        self.road_cells = set(((rows + 1) * self.grid.W2 + cols + 1).tolist())
        self.road_cells_total = int(rr.sum())
        self.road_cells_passable = int((rr & pr).sum())


def make_targets(houses: gpd.GeoDataFrame, facilities: gpd.DataFrame | None = None, weights: dict | None = None) -> list:
    t = []
    for r in houses.itertuples():
        pt = r.geometry.representative_point()
        t.append(dict(id=f"H{int(r.hid):04d}", kind="HOUSE", name="", ftype="", pt=pt, weight=1.0, n_buildings=1, n_unresolved=0, weight_rule="house"))
    if facilities is not None and len(facilities):
        w = weights or pn().DEFAULT_WEIGHTS
        for r in facilities.itertuples():
            wt, key = pn().priority_weight(dict(facility_type=r.facility_type, priority_group="", facility_name=r.name), w)
            t.append(dict(id="F:" + str(r.fid), kind="FACILITY", name=r.name, ftype=r.facility_type, pt=r.geometry, weight=wt, weight_rule=key,
                          n_buildings=0, n_unresolved=0))
    return t


def length_only_routes(world: World, targets: list, p: dict) -> tuple:
    """Control: shortest DISTANCE (cost 1 on every passable cell, no footprint penalty) under the same hard constraints, independent routes."""
    P = pn()
    cost1 = np.where(np.isfinite(world.cost), 1.0, np.nan)
    g = P.Grid(cost1, world.T, hard=None, mult=None, corner_cut=False)
    routes, fails = [], {}
    for t in targets:
        i0 = g.idx_of(t["pt"].x, t["pt"].y)
        if i0 is None or g.cost[i0] == P.INF:
            fails[t["id"]] = "TARGET_IN_HARD_CONSTRAINT_CELL_OR_OUTSIDE_GRID"
            continue
        s = g.snap(t["pt"].x, t["pt"].y, p["snap_m"])
        if s is None:
            fails[t["id"]] = "NO_START_CELL"
            continue
        a, why = P.gen_alternatives(g, s[0], set(world.road_cells), 1, p["corridor_m"], p["corridor_mults"], p["max_overlap"], p["max_search_m"])
        if not a:
            fails[t["id"]] = why
            continue
        routes.append(P.make_route(g, t["id"], t["pt"], s[1], a[0], "length_only", world.road_union, p["attach_tol_m"]))
    return routes, fails


def crossing_stats(routes: list, footprints_by_hid: gpd.GeoDataFrame) -> dict:
    """Per house route: length inside footprints other than the route's own building (Stage B definition, src/validation/building_crossing_diagnostic.py)."""
    fp = footprints_by_hid
    sidx = fp.sindex
    n_cross, total, first20 = 0, 0.0, 0
    for r in routes:
        hid = int(str(r["target"])[1:]) if str(r["target"]).startswith("H") else None
        g = r["geom"]
        cand = fp.iloc[list(sidx.query(g, predicate="intersects"))]
        cand = cand[cand.hid != hid]
        if cand.empty:
            continue
        L = g.intersection(unary_union(list(cand.geometry))).length
        if L > 1e-6:
            n_cross += 1
            total += L
    return dict(routes_crossing=n_cross, len_in_footprints_m=round(total, 1))


def metrics(name: str, routes: list, tmap: dict, nall: int, footprints, extra: dict | None = None) -> dict:
    P = pn()
    row = P.summarise(name, routes, tmap, nall)
    if routes and "edges" in routes[0]:
        row.update(crossing_stats(routes, footprints))
    else:                                                   # straight lines
        row.update(crossing_stats(routes, footprints))
    if extra:
        row.update(extra)
    return row


def run_all_strategies(world: World, targets: list, p: dict, footprints, log=print) -> dict:
    """Straight line, independent least-cost, length-only control, roads-only shared reference, two-stage shared plan."""
    P = pn()
    tmap = {t["id"]: t for t in targets}
    t0 = time.time()
    two = P.plan(world.grid, world.road_union, world.road_cells, targets, p, log=log)
    t_two = time.time() - t0
    t0 = time.time()
    ro = P.plan(world.grid, world.road_union, world.road_cells, targets, dict(p, attach=False, passes=0), log=log)
    t_ro = time.time() - t0
    lo_routes, lo_fail = length_only_routes(world, targets, p)
    n = len(targets)
    straight = [r for r in two["straight"].values()]
    rows = [
        metrics("Straight line", [dict(target=r["target"], geom=r["geom"], own_len_m=r["own_len_m"], feasible=r["feasible"]) for r in straight], tmap, n, footprints,
                dict(infeasible=sum(1 for r in straight if not r["feasible"]))),
        metrics("Independent least-cost routes", list(two["indep"].values()), tmap, n, footprints),
        metrics("Length-only control", lo_routes, tmap, n, footprints),
        metrics("Roads-only shared reference", list(ro["sel"].values()), tmap, n, footprints),
        metrics("Two-stage shared plan", list(two["sel"].values()), tmap, n, footprints),
    ]
    return dict(rows=rows, two=two, roads_only=ro, length_only=(lo_routes, lo_fail), seconds=dict(two_stage=round(t_two, 1), roads_only=round(t_ro, 1)))
