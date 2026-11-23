"""Building-clearance routing: no proposed or alternative route runs over a footprint (synthetic 1 km x 1 km world, 10 m cost cells)."""
import math

import geopandas as gpd
import numpy as np
import pytest
from affine import Affine
from shapely.geometry import LineString, box

from src.multivillage import clearance as CL
from src.multivillage import master_map as MM

CRS = "EPSG:32644"
PARAMS = dict(k=3, corridor_m=20.0, corridor_mults=(3.0, 8.0), max_overlap=0.8, max_search_m=1500.0, snap_m=30.0, attach_tol_m=15.0, passes=2, budget=None, attach=True)
X0, Y0, N = 500000.0, 1900000.0, 100                           # 100 x 100 cells of 10 m
T = Affine(10, 0, X0, 0, -10, Y0 + N * 10)


def world_data(blocks, houses, fac=()):
    """Road along the west edge; `blocks` = extra non-target buildings, `houses` = target buildings (road-gap houses)."""
    def b(x, y, w, h):
        return box(X0 + x, Y0 + y, X0 + x + w, Y0 + y + h)
    allg = [b(*r) for r in houses] + [b(*r) for r in blocks]
    ha = gpd.GeoDataFrame(dict(hid=range(1, len(allg) + 1), quality_class_model="PLAUSIBLE"), geometry=allg, crs=CRS)
    gap = ha.iloc[: len(houses)].copy()
    f = gpd.GeoDataFrame(dict(fid=range(1, len(fac) + 1), name=[f"Facility {i}" for i in range(len(fac))], facility_type=["school"] * len(fac)), geometry=[b(*r).centroid for r in fac], crs=CRS)
    road = LineString([(X0 + 5, Y0), (X0 + 5, Y0 + 1000)])
    return ha, gap, f, [road]


def run(blocks, houses, fac=()):
    ha, gap, f, roads = world_data(blocks, houses, fac)
    cost = np.ones((N, N))
    return ha, CL.compute_from_arrays(cost, T, (N, N), roads, ha, gap, f, PARAMS, log=lambda *a: None)


def test_routes_go_around_buildings_and_verify_zero():
    # a wall of buildings between the target house (x = 700-720) and the road, with a 40 m gap at y = 440-480
    wall = [(300, 100, 30, 340), (300, 480, 30, 400)]
    ha, out = run(wall, [(700, 450, 20, 20)])
    assert len(out["houses"]["shared"]) == 1 and not out["houses"]["fails"] and not out["houses"]["unreachable"]
    r = out["houses"]["shared"][0]["geom"]
    others = [g for g, h in zip(ha.geometry, ha.hid) if h != 1]
    assert all(r.intersection(g).length == 0 for g in others)                       # independent re-check with shapely
    assert out["verify"]["house_shared"]["routes_crossing"] == 0
    assert out["verify"]["house_shared"]["length_inside_other_footprints_m"] == 0.0
    assert r.length > 700 - 5                                                        # it reached the road
    assert math.isfinite(out["unique"]["house_shared_m"]) and out["unique"]["house_shared_m"] > 0


def test_every_route_clear_of_all_footprints_in_a_dense_block():
    rng = np.random.default_rng(3)
    houses = [(600 + 25 * i, 100 + 40 * j, 12, 14) for i in range(6) for j in range(10) if rng.random() < 0.5]
    blocks = [(400 + 30 * i, 100 + 40 * j, 14, 14) for i in range(5) for j in range(10)]
    ha, out = run(blocks, houses)
    routes = out["houses"]["shared"] + out["houses"]["indep"]
    assert len(routes) > 10
    tree_geoms = list(ha.geometry)
    for r in routes:
        own = r["own_hid"]
        for g, h in zip(tree_geoms, ha.hid):
            if h != own:
                assert r["geom"].intersection(g).length < 1e-6
    v = out["verify"]
    assert v["house_shared"]["routes_crossing"] == 0 and v["house_indep"]["routes_crossing"] == 0


def test_enclosed_house_is_unreachable_not_routed_over_a_roof():
    ring = [(450, 450, 30, 6), (450, 494, 30, 6), (450, 456, 6, 38), (474, 456, 6, 38)]             # house at 458-472 enclosed by four buildings
    ha, out = run(ring, [(460, 465, 10, 10)])
    h = out["houses"]
    assert len(h["shared"]) == 0 and len(h["unreachable"]) + len(h["fails"]) == 1


def test_verify_detects_a_route_over_a_footprint():
    ha, gap, f, roads = world_data([(300, 100, 40, 100)], [(700, 450, 20, 20)])
    fp = CL.Footprints(ha)
    bad = dict(geom=LineString([(X0 + 250, Y0 + 150), (X0 + 400, Y0 + 150)]), own=None)
    res = CL.verify([bad], fp)
    assert res["routes_crossing"] == 1 and res["length_inside_other_footprints_m"] == pytest.approx(40.0, abs=0.01)


def test_clearance_below_half_cell_diagonal_is_rejected():
    ha, gap, f, roads = world_data([], [(700, 450, 20, 20)])
    with pytest.raises(ValueError):
        CL.ClearWorld(np.ones((N, N)), T, (N, N), roads, list(ha.geometry), clearance_m=2.0, grid_m=5.0)
    CL.ClearWorld(np.ones((N, N)), T, (N, N), roads, list(ha.geometry), clearance_m=7.2, grid_m=10.0)   # 10 m grid needs 7.07 m


def test_facility_route_and_master_map_render(tmp_path):
    ha, out = run([(300, 100, 30, 340)], [(700, 450, 20, 20), (650, 300, 20, 20)], fac=[(800, 700, 20, 20)])
    assert len(out["facilities"]["shared"]) == 1
    _, gap, f, roads = world_data([(300, 100, 30, 340)], [(700, 450, 20, 20), (650, 300, 20, 20)], fac=[(800, 700, 20, 20)])
    cell = box(X0, Y0, X0 + 1000, Y0 + 1000)
    sc = MM.scene_from_clearance("Test area", "synthetic polygon", cell, gpd.GeoSeries(roads, crs=CRS), ha, gap, f, out, mosaic=None)
    lines = " ".join(MM.summary_lines(sc, routes=True, fac_key=True))
    assert "0 cross another building" in lines and "Facility key: F1 school" in lines and "illustrative" in lines and "NOT verified" in lines
    png = MM.render_master(sc, tmp_path / "m.png", dpi=40)
    p2 = MM.render_panel(sc, (X0, Y0, X0 + 1000, Y0 + 1000), tmp_path / "p.png", "two_stage", False, dpi=40)
    assert png.stat().st_size > 5000 and p2.stat().st_size > 3000
