"""Unit + integration tests for the hierarchical routing levels (Contribution 3). Run: pytest tests -q"""
import copy
import json
from pathlib import Path

import geopandas as gpd
import networkx as nx
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import LineString, Point, box

from src.evaluation.hierarchy_metrics import evaluate_level, omission_table, override_table
from src.routing import data_hooks as dh
from src.routing import synthetic_world as sw
from src.routing.hierarchical_router import (DistrictInputs, Node, RoutingProblem, build_district_problem,
                                              build_gp_problem, build_mandal_problem, cluster_hamlets, contract_chains,
                                              contract_degree2, disc_mask, grid_module, hamlet_hubs, load_config,
                                              penalty_multiplier, plan_on_grid)
from src.routing.layers import (RasterLayerProvider, SyntheticLayerProvider, cost_from_layers, grid_for)

CFG = load_config()
T10 = from_origin(0.0, 200.0, 10.0, 10.0)          # 20 x 20 grid of 10 m cells, north-west corner at (0, 200)


def toy_problem(nodes, mu=1.0, foot=None, radius=0.0):
    cost = np.full((20, 20), 1.0, dtype="float32")
    road = np.zeros((20, 20), bool)
    road[:, 0] = True                              # a road along the western edge
    return RoutingProblem("gp", cost, T10, nodes, road, foot, mu, radius, snap_m=30.0)


# ------------------------------------------------------------------------ cost surface / override
def test_penalty_multiplier_and_local_override():
    foot = np.zeros((20, 20), bool)
    foot[5:15, 5:15] = True
    m_all = penalty_multiplier((20, 20), T10, foot, 4.0)
    assert m_all[10, 10] == 4.0 and m_all[0, 19] == 1.0
    cx, cy = 100.0, 100.0                          # centre of the building
    m_ov = penalty_multiplier((20, 20), T10, foot, 4.0, [(cx, cy, 20.0)])
    d = disc_mask((20, 20), T10, cx, cy, 20.0)
    assert (m_ov[d & foot] == 1.0).all()           # override lifts the penalty inside the disc ...
    assert (m_ov[foot & ~d] == 4.0).all()          # ... and only inside it
    assert (m_ov[~foot] == 1.0).all()


def test_override_never_raises_isolated_route_cost():
    foot = np.zeros((20, 20), bool)
    foot[6:14, 6:14] = True
    fac = Node("F", 100.0, 100.0, 1.0, "healthcare", exempt=True)
    prob = toy_problem([fac], mu=4.0, foot=foot, radius=20.0)
    a = prob.solve(use_override=False).routes["F"].cost
    b = prob.solve(use_override=True).routes["F"].cost
    assert b < a


def test_cost_from_layers_recipe_blocks_water_and_steep_slope():
    from src.routing.layers import Layers
    lc = np.array([[40, 80], [10, 0]], dtype="uint8")
    slope = np.array([[0, 0], [30, 5]], dtype="float32")
    L = Layers(from_origin(0, 20, 10, 10), lc, slope, (2, 2), "t")
    c = cost_from_layers(L, CFG["cost_surface"], forest_multiplier=1.5)
    assert c[0, 0] == pytest.approx(6.0)            # cropland, flat
    assert np.isnan(c[0, 1])                        # water
    assert np.isnan(c[1, 0])                        # slope 30 deg > limit
    assert np.isnan(c[1, 1])                        # invalid class 0


# ------------------------------------------------------------------------ shared planner
def brute_greedy(grid, nodes, roads, snap):
    """Non-lazy reference: recompute every node each round and take the cheapest."""
    goals, left, total = set(roads), {n.id: grid.snap(n.x, n.y, snap)[0] for n in nodes}, 0.0
    edges = set()
    while left:
        best = None
        for nid, s in left.items():
            r = grid.search(s, goals)
            e = grid.edges(r["cells"])
            c = sum(x[3] for x in e)
            if best is None or c < best[0]:
                best = (c, nid, r["cells"], e)
        _, nid, cells, e = best
        edges.update((a, b, L) for a, b, L, _ in e)
        goals.update(cells)
        del left[nid]
    return sum(L for _, _, L in edges)


def test_lazy_greedy_matches_bruteforce_and_beats_independent():
    nodes = [Node(f"N{i}", 150.0 + 6 * i, 20.0 + 17 * i, 1.0) for i in range(8)]
    prob = toy_problem(nodes)
    grid = prob.build_grid()
    roads = prob.road_cells(grid)
    shared = plan_on_grid(grid, nodes, roads, 30.0, "shared")
    indep = plan_on_grid(grid, nodes, roads, 30.0, "independent")
    assert shared.unique_length_m == pytest.approx(brute_greedy(grid, nodes, roads, 30.0))
    assert shared.unique_length_m <= indep.unique_length_m + 1e-9
    assert len(shared.routes) == 8 and shared.connected_any_road == set(shared.routes)


def test_unreachable_node_is_reported_not_served():
    cost = np.full((20, 20), 1.0, dtype="float32")
    cost[:, 8:11] = np.nan                           # a river no road crosses
    road = np.zeros((20, 20), bool)
    road[:, 0] = True
    prob = RoutingProblem("gp", cost, T10, [Node("A", 150.0, 100.0), Node("B", 40.0, 100.0)], road, snap_m=30.0)
    r = prob.solve()
    assert "A" in r.failures and "B" in r.routes and "A" not in r.connected_any_road


def test_hamlet_aggregation_and_weights():
    pts = np.vstack([np.random.default_rng(1).normal([0, 0], 20, (10, 2)), np.random.default_rng(2).normal([2000, 0], 20, (5, 2))])
    groups = cluster_hamlets(pts, 150.0)
    assert sorted(len(g) for g in groups) == [5, 10]
    hubs = hamlet_hubs(pts, 150.0)
    assert [h.weight for h in hubs] == [10.0, 5.0] and hubs[0].id == "HAM001"


# ------------------------------------------------------------------------ graph contraction
def test_contract_chains_y_tree():
    # cells 1-2-3-4-5 with a branch 3-6-7  -> junction at 3, leaves 1,5,7 => 3 chains
    edges = {(1, 2), (2, 3), (3, 4), (4, 5), (3, 6), (6, 7)}
    chains = contract_chains(edges, keep_cells={1, 5, 7})
    assert len(chains) == 3
    assert sorted(len(c) for c in chains) == [3, 3, 3]


def test_contract_degree2_preserves_length():
    G = nx.Graph()
    for a, b in [(0, 1), (1, 2), (2, 3), (3, 4), (3, 5)]:
        G.add_edge(a, b, length=10.0)
    H = contract_degree2(G, keep={0})
    assert set(H.nodes) == {0, 3, 4, 5}
    assert H[0][3]["length"] == 30.0 and sum(d["length"] for *_, d in H.edges(data=True)) == 50.0


# ------------------------------------------------------------------------ providers / loaders
def test_synthetic_provider_is_resolution_consistent_and_deterministic():
    b = (258000.0, 1950000.0, 268000.0, 1960000.0)
    p = SyntheticLayerProvider(b, seed=3)
    a = p.layers(b, 100.0)
    c = p.layers(b, 100.0)
    assert np.array_equal(a.landcover, c.landcover)
    sub = p.layers((258000.0, 1955000.0, 263000.0, 1960000.0), 100.0)      # an aligned sub-window
    assert np.array_equal(sub.landcover, a.landcover[:50, :50])


def test_raster_provider_roundtrip(tmp_path):
    T = from_origin(1000.0, 2000.0, 10.0, 10.0)
    lc = np.full((100, 100), 40, dtype="uint8")
    lc[:, 50:55] = 80
    dem = np.fromfunction(lambda r, c: 5.0 * c, (100, 100), dtype="float32")     # 5 m per 10 m cell ~ 26.6 deg
    prof = dict(driver="GTiff", height=100, width=100, count=1, crs="EPSG:32644", transform=T)
    with rasterio.open(tmp_path / "lc.tif", "w", dtype="uint8", **prof) as d:
        d.write(lc, 1)
    with rasterio.open(tmp_path / "dem.tif", "w", dtype="float32", **prof) as d:
        d.write(dem, 1)
    L = RasterLayerProvider(str(tmp_path / "lc.tif"), str(tmp_path / "dem.tif")).layers((1000.0, 1000.0, 2000.0, 2000.0), 10.0)
    assert (L.landcover[:, 50:55] == 80).all()
    c = cost_from_layers(L, CFG["cost_surface"])
    assert np.isnan(c[:, 52]).all() and np.isnan(c[10, 10])                    # water; slope 26.6 > 25 limit


def test_tile_bounds_cover_and_overlap():
    tiles = dh.tile_bounds((0, 0, 10000, 6000), 4000, 500)
    assert min(t[0] for t in tiles) == 0 and max(t[2] for t in tiles) == 10000
    assert max(t[3] for t in tiles) == 6000 and all(t[2] - t[0] <= 4000 for t in tiles)
    with pytest.raises(ValueError):
        dh.tile_bounds((0, 0, 10, 10), 100, 100)


def test_inventory_reports_missing_and_fallback(tmp_path):
    inv = dh.inventory(CFG, tmp_path)                    # an empty root: nothing exists, whatever has been downloaded locally
    assert "SYNTHETIC" in inv["_fallback"]["district"]
    miss = dh.missing_inputs(inv)
    assert any(l == "district" and k == "boundary" for l, k, _ in miss)


def test_mandal_loader_from_geopackages(tmp_path):
    crs = CFG["crs"]
    cfg = copy.deepcopy(CFG)
    d = cfg["data"]["mandal"]
    gpd.GeoDataFrame(geometry=[box(258000, 1950000, 268000, 1960000)], crs=crs).to_file(tmp_path / "b.gpkg", driver="GPKG")
    gpd.GeoDataFrame({"houses": [100, 250]}, geometry=[box(258000, 1950000, 263000, 1960000), box(263000, 1950000, 268000, 1960000)],
                     crs=crs).to_file(tmp_path / "gp.gpkg", driver="GPKG")
    gpd.GeoDataFrame(geometry=[LineString([(258000, 1955000), (268000, 1955000)])], crs=crs).to_file(tmp_path / "r.gpkg", driver="GPKG")
    gpd.GeoDataFrame({"facility_type": ["Mandal HQ", "PHC", "Weekly market", "School"]},
                     geometry=[Point(262000, 1955500), Point(259000, 1952000), Point(266000, 1958000), Point(1, 1)],
                     crs=crs).to_file(tmp_path / "f.gpkg", driver="GPKG")
    d.update(landcover=str(tmp_path / "no_lc.tif"), dem=str(tmp_path / "no_dem.tif"), boundary=str(tmp_path / "b.gpkg"), gp_boundaries=str(tmp_path / "gp.gpkg"), roads=str(tmp_path / "r.gpkg"),
             facilities=str(tmp_path / "f.gpkg"))
    m, rep = dh.load_mandal_real(cfg)
    assert m is not None and not rep["missing"]
    kinds = sorted(n.kind for n in m.nodes)
    assert kinds == ["gp_hub", "gp_hub", "mandal_hq", "market", "phc"]       # the school is not a Level-3 node
    prob = build_mandal_problem(m, cfg)                                       # flat fallback cost (no rasters)
    assert any("FALLBACK" in n for n in prob.meta["notes"]) or any("missing" in n for n in prob.meta["notes"])
    r = prob.solve()
    assert len(r.routes) == 5 and not r.failures


def test_missing_real_inputs_return_none_not_exception(tmp_path):
    m, rep = dh.load_mandal_real(CFG, tmp_path)
    d, rep2 = dh.load_district_real(CFG, tmp_path)
    assert m is None and d is None and rep["missing"] and rep2["missing"]


@pytest.mark.skipif(not (Path("Siddipet/Damarakunta/study_area/damarakunta_boundary.gpkg").exists()), reason="repo data absent")
def test_real_damarakunta_gp_inputs_load_and_run():
    gp, rep = dh.load_gp_real(CFG)
    assert gp is not None
    assert sum(n.weight for n in gp.nodes if n.kind == "hamlet") == 163            # all Stage B house targets aggregated
    assert sorted(n.kind for n in gp.nodes if n.kind != "hamlet") == ["healthcare", "panchayat_office", "panchayat_office", "school", "school"]
    prob = build_gp_problem(gp, CFG)
    r = prob.solve()
    assert not r.failures and len(r.routes) == len(gp.nodes)
    assert r.unique_length_m <= prob.solve(mode="independent").unique_length_m + 1e-9


# ------------------------------------------------------------------------ levels end to end (synthetic)
def test_gp_level_outputs_override_and_omission(tmp_path):
    gp = sw.make_synthetic_gp(seed=5, n_hamlets=4)
    prob = build_gp_problem(gp, CFG)
    from src.routing.run_hierarchy import gp_omit_fn
    s = evaluate_level("gp", prob, gp.nodes, tmp_path, CFG["crs"], (0.1, 0.2), (1, 2),
                       {"data_source": "synthetic"}, omit_fn=gp_omit_fn(gp, CFG))
    for f in ("gp_routes.gpkg", "gp_summary.json", "gp_metrics.csv", "gp_override.csv", "gp_omission.csv"):
        assert (tmp_path / "gp" / f).exists(), f
    assert s["coverage_pct"] == 100.0 and s["saving_vs_independent_unique_pct"] >= 0
    assert s["detour_reduction_m_total"] >= -1e-6
    layers = set(gpd.list_layers(tmp_path / "gp" / "gp_routes.gpkg")["name"])
    assert {"routes_shared", "routes_independent", "nodes"} <= layers
    om = omission_table(prob, gp.nodes, "gp", (0.2,), (1,), gp_omit_fn(gp, CFG))
    base, row = om[0], om[1]
    assert row["unserved_weight"] >= row["units_omitted"] - 1e-9                # omitted houses are never served
    assert row["unique_length_m"] <= base["unique_length_m"] * 1.05              # missing houses do not grow the plan much
    ov = override_table(prob, gp.nodes)
    assert any(r["node"] == "_OTHER_ROUTES_CHANGED" for r in ov)


def test_mandal_level_connects_everything_on_synthetic_world():
    m = sw.make_synthetic_mandal(seed=11, n_gps=6)
    prob = build_mandal_problem(m, CFG)
    shared, indep = prob.solve(), prob.solve(mode="independent")
    assert not shared.failures and len(shared.connected_main) == len(m.nodes)
    assert shared.unique_length_m <= indep.unique_length_m + 1e-9
    assert prob.cost[np.isfinite(prob.cost)].min() < 1.0                            # road discount active (road snapping)


def test_district_coarse_to_fine_is_bounded_and_connected():
    d = sw.make_synthetic_district(seed=4, n_mandals=6, size_m=30000.0)
    cfg = copy.deepcopy(CFG)
    cfg["levels"]["district"].update(segment_m=3000.0, corridor_m=800.0)
    prob = build_district_problem(d, cfg)
    shared = prob.solve()
    star = prob.solve(mode="independent")
    assert shared.served == {n.id for n in d.nodes if n.kind != "district_hq"}
    assert set(shared.meta["fine_status"]) <= {"fine"}                              # no coarse fallbacks
    assert shared.unique_length_m < star.unique_length_m
    # refinement never exceeds the coarse chain length by more than a small tolerance
    grid, _ = prob.coarse()
    assert shared.meta["n_chains"] >= len(d.nodes) - 1
    assert shared.meta["coarse_cells"] == grid.H * grid.W


def test_district_memory_guard_degrades_instead_of_failing():
    d = sw.make_synthetic_district(seed=4, n_mandals=3, size_m=20000.0)
    cfg = copy.deepcopy(CFG)
    cfg["levels"]["district"].update(max_fine_cells=500, segment_m=5000.0)
    r = build_district_problem(d, cfg).solve()
    assert "fine_degraded" in r.meta["fine_status"] and r.unique_length_m > 0


def test_cli_runs_all_levels_on_synthetic_data(tmp_path):
    from src.routing.run_hierarchy import run
    s = run([2, 3, 4], "synthetic", tmp_path, CFG, log=lambda *_: None)
    assert [x["level"] for x in s] == ["gp", "mandal", "district"]
    rows = (tmp_path / "hierarchy_summary.csv").read_text().strip().splitlines()
    assert len(rows) == 4 and "synthetic" in rows[1]
    assert "mandal" in json.loads((tmp_path / "data_inventory.json").read_text())["_fallback"]


def test_make_4connected_links_diagonal_road_cells():
    from src.routing.hierarchical_router import make_4connected
    m = np.zeros((4, 4), bool)
    m[0, 0] = m[1, 1] = m[2, 2] = True
    out = make_4connected(m)
    assert out.sum() > m.sum() and (out & ~m).sum() == 2
    anti = np.zeros((4, 4), bool)
    anti[0, 3] = anti[1, 2] = True
    assert make_4connected(anti).sum() == 3


def test_mandal_loader_splits_collector_and_local_roads(tmp_path):
    crs = CFG["crs"]
    cfg = copy.deepcopy(CFG)
    d = cfg["data"]["mandal"]
    gpd.GeoDataFrame(geometry=[box(258000, 1950000, 268000, 1960000)], crs=crs).to_file(tmp_path / "b.gpkg", driver="GPKG")
    gpd.GeoDataFrame(geometry=[box(259000, 1951000, 260000, 1952000)], crs=crs).to_file(tmp_path / "gp.gpkg", driver="GPKG")
    gpd.GeoDataFrame({"class": ["primary", "residential"]}, geometry=[LineString([(258000, 1955000), (268000, 1955000)]),
                     LineString([(259500, 1952000), (259500, 1955000)])], crs=crs).to_file(tmp_path / "r.gpkg", driver="GPKG")
    gpd.GeoDataFrame({"facility_type": ["Mandal HQ"]}, geometry=[Point(262000, 1955500)], crs=crs).to_file(tmp_path / "f.gpkg", driver="GPKG")
    d.update(landcover=str(tmp_path / "x.tif"), dem=str(tmp_path / "y.tif"), boundary=str(tmp_path / "b.gpkg"),
             gp_boundaries=str(tmp_path / "gp.gpkg"), roads=str(tmp_path / "r.gpkg"), facilities=str(tmp_path / "f.gpkg"))
    m, _ = dh.load_mandal_real(cfg)
    assert len(m.roads) == 1 and len(m.local_roads) == 1                          # only the primary road is an attachment goal
    prob = build_mandal_problem(m, cfg)
    assert prob.road_mask.sum() < (prob.cost < 1.0).sum() + prob.road_mask.sum()   # local road cells are discounted but not goals
    r = prob.solve()
    assert not r.failures and r.unique_length_m > 1000.0                           # the village must reach the primary road, not the track


def test_district_reports_new_construction_vs_existing_road():
    d = sw.make_synthetic_district(seed=4, n_mandals=5, size_m=30000.0)
    r = build_district_problem(d, CFG).solve()
    m = r.meta
    assert 0.0 <= m["on_existing_road_m"] <= r.unique_length_m + 1e-6
    assert m["new_construction_m"] == pytest.approx(r.unique_length_m - m["on_existing_road_m"])
