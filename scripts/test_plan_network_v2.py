"""Synthetic tests for plan_network_v2: shared credit, attachment, blocked routes, endpoint connectivity."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import numpy as np
from affine import Affine
from shapely.geometry import Point, LineString
import plan_network_v2 as P

T = Affine(10, 0, 0, 0, -10, 600)          # 60x60 cells, 10 m
H = W = 60
def xy(r, c): return Point(c * 10 + 5, 600 - (r * 10 + 5))
P_ = dict(attach_tol_m=15.0, max_search_m=2000.0, snap_m=30.0, k=3, corridor_m=20.0, corridor_mults=[3.0, 8.0],
          max_overlap=0.8, passes=2, budget=None)

def setup(cost, hard=None):
    g = P.Grid(cost, T, hard=hard)
    road = LineString([(0, 600 - 555), (600, 600 - 555)])
    cells = {(r + 1) * g.W2 + c + 1 for r in (55,) for c in range(W)}
    return g, road, cells

def tg(i, r, c, w=1.0): return dict(id=i, pt=xy(r, c), weight=w, kind="CLUSTER", n_buildings=1)

def test_attachment_and_shared_credit():
    g, road, rc = setup(np.ones((H, W)))
    # B is far from road (row 20) but next to A; A is heavier-weight and closer -> picked first
    ts = [tg("A", 40, 30, 5.0), tg("B", 36, 31, 1.0), tg("C", 33, 29, 1.0)]
    res = P.plan(g, road, rc, ts, P_)
    sel = res["sel"]
    assert not res["fails"], res["fails"]
    ver = P.verify_network(sel, road, g, 15.0)
    assert all(v["connected_to_roads"] for v in ver.values()), ver
    attached = [t for t, r in sel.items() if r["attach_to"] != "ROAD"]
    assert attached, "expected at least one route attached to a selected route"
    na = P.unique_edge_metrics(list(sel.values()))
    ind = P.unique_edge_metrics(list(res["indep"].values()))
    assert na["unique_len_m"] < ind["unique_len_m"] - 1.0, (na, ind)
    assert na["total_len_m"] - na["unique_len_m"] >= 0
    print("attach OK: attached", attached, "unique", round(na["unique_len_m"]), "vs indep", round(ind["unique_len_m"]))

def test_shared_edges_counted_once():
    g, road, rc = setup(np.ones((H, W)))
    r1 = P.make_route(g, "x", xy(50, 10), 0, {"cells": [(r + 1) * g.W2 + 11 for r in range(50, 55)]}, "t", road)
    r2 = P.make_route(g, "y", xy(50, 10), 0, {"cells": [(r + 1) * g.W2 + 11 for r in range(50, 55)]}, "t", road)
    m = P.unique_edge_metrics([r1, r2])
    assert abs(m["total_len_m"] - 2 * m["unique_len_m"]) < 1e-6 + 2 * (r1["start_snap_m"] + r1["end_snap_m"]), m
    print("shared edges once OK", m)

def test_blocked_and_disconnected():
    cost = np.ones((H, W)); hard = np.zeros((H, W), bool)
    hard[10:15, 10:15] = True; hard[11:14, 11:14] = False       # ring around a pocket
    hard[0:20, 40:41] = False
    g, road, rc = setup(cost, hard)
    ts = [tg("POCKET", 12, 12), tg("OK", 30, 40), tg("WATER", 12, 10)]  # WATER target sits on a hard cell (>snap?)
    res = P.plan(g, road, rc, ts, P_)
    assert "POCKET" in res["fails"] and res["fails"]["POCKET"].startswith("NO_PATH"), res["fails"]
    assert "POCKET" not in res["sel"]
    assert "OK" in res["sel"]
    print("blocked OK:", res["fails"])

def test_no_start_cell():
    hard = np.zeros((H, W), bool); hard[0:30, 0:30] = True
    g, road, rc = setup(np.ones((H, W)), hard)
    res = P.plan(g, road, rc, [tg("DEEP", 5, 5)], P_)
    assert res["fails"]["DEEP"] .startswith("TARGET_IN_HARD_CONSTRAINT"), res["fails"]
    print("no-start OK")

def test_nodata_cells_impassable():
    cost = np.ones((H, W)); cost[30, :] = np.nan; cost[31, :] = -1
    g, road, rc = setup(cost)
    res = P.plan(g, road, rc, [tg("T", 10, 30)], P_)
    assert "T" in res["fails"] and res["sel"] == {}, res
    print("nodata wall OK:", res["fails"])

def test_endpoint_tolerance():
    g, road, rc = setup(np.ones((H, W)))
    res = P.plan(g, road, rc, [tg("A", 40, 30)], P_)
    r = res["sel"]["A"]
    assert r["endpoint_ok"] and r["end_snap_m"] <= 15.0
    assert Point(r["geom"].coords[-1]).distance(road) <= 15.0
    # tolerance 0.01 m must not pass for off-centre cell ends unless exactly on the line
    print("endpoint OK end_snap", r["end_snap_m"])

def test_straight_line_flags_infeasible():
    hard = np.zeros((H, W), bool); hard[45:50, :] = True
    g, road, rc = setup(np.ones((H, W)), hard)
    res = P.plan(g, road, rc, [tg("A", 40, 30)], P_)
    assert res["straight"]["A"]["feasible"] is False
    assert "A" in res["fails"]          # wall spans full width -> truly blocked
    print("straight infeasible + blocked OK")

def test_corner_squeeze_forbidden():
    cost = np.ones((H, W)); hard = np.zeros((H, W), bool)
    for k in range(60):
        hard[k, 59 - k] = True                       # diagonal wall: sealed for 4-connectivity, leaky for naive 8-connectivity
    g = P.Grid(cost, T, hard=hard)                   # default: corner cutting forbidden
    g2 = P.Grid(cost, T, hard=hard, corner_cut=True)
    road_cells = {(55 + 1) * g.W2 + c + 1 for c in range(30, 60)}   # road only on the far side of the wall
    st = (10 + 1) * g.W2 + 10 + 1
    assert isinstance(g.search(st, road_cells), str), "forbid mode must not squeeze through the diagonal wall"
    assert isinstance(g2.search(st, road_cells), dict), "allow mode reproduces the squeeze"
    print("corner squeeze: forbid -> no path, allow -> path through zero-width gap")

def test_connector_crossing_hard_is_rejected():
    # start point sits in a blocked strip; nearest passable cell is across it only via a connector through blocked cells
    hard = np.zeros((H, W), bool); hard[40:43, 28:33] = True
    g, road, rc = setup(np.ones((H, W)), hard)
    r = P.make_route(g, "x", xy(41, 30), 20.0, {"cells": [(44 + 1) * g.W2 + 30 + 1, (45 + 1) * g.W2 + 30 + 1]}, "t", road)
    assert r["hard_violations"] > 0 and not r["hard_ok"] and not r["endpoint_ok"], r["hard_violations"]
    print("connector across hard cells rejected OK:", r["hard_violations"], "bad samples")

def test_overlap_zero_for_attached_positive_for_independent():
    cost = np.ones((H, W)); cost[:55, 30] = 0.05     # cheap corridor -> independent routes funnel into it and re-lay it
    g, road, rc = setup(cost)
    res = P.plan(g, road, rc, [tg("A", 40, 24, 5.0), tg("B", 36, 36), tg("C", 30, 22)], P_)
    na = P.unique_edge_metrics(list(res["sel"].values())); ic = P.unique_edge_metrics(list(res["indep"].values()))
    assert abs(na["total_len_m"] - na["unique_len_m"]) < 1e-6, na
    assert ic["total_len_m"] - ic["unique_len_m"] > 1.0, ic
    assert na["unique_len_m"] <= ic["unique_len_m"] + 1e-6
    print("overlap: network-aware", round(na["total_len_m"] - na["unique_len_m"], 1), "| independent", round(ic["total_len_m"] - ic["unique_len_m"], 1))

def test_coordinate_index_roundtrip():
    g, road, rc = setup(np.ones((H, W)))
    for r, c in [(0, 0), (0, 59), (59, 0), (30, 17), (59, 59)]:
        i = (r + 1) * g.W2 + c + 1
        x, y = g.xy(i)
        assert g.idx_of(x, y) == i, (r, c)
        assert abs(x - (c * 10 + 5)) < 1e-9 and abs(y - (600 - (r * 10 + 5))) < 1e-9     # negative pixel height handled
    assert g.idx_of(-1, 300) is None and g.idx_of(300, 601) is None
    print("coordinate/index roundtrip OK (negative pixel height)")

def test_slope_and_water_hard_cells():
    slope = np.zeros((H, W)); slope[30, :] = 14.2; slope[31, :] = 10.35       # values seen in Damarakunta C12/C13
    water = np.zeros((H, W), bool); water[40:45, :] = True
    hard = (slope > 10.0) | water
    g, road, rc = setup(np.ones((H, W)), hard)
    res = P.plan(g, road, rc, [tg("A", 10, 30)], P_)
    assert "A" in res["fails"] and "A" not in res["sel"], res["fails"]
    hard2 = (slope > 20.0) | water                       # limit raised above the data: slope wall disappears, water wall still blocks
    g2, road2, rc2 = setup(np.ones((H, W)), hard2)
    assert "A" in P.plan(g2, road2, rc2, [tg("A", 10, 30)], P_)["fails"]
    hard3 = slope > 10.0                                  # slope wall only, full width -> blocked; with a gap -> routed AROUND, never across
    hard3[30:32, 20] = False
    g3, road3, rc3 = setup(np.ones((H, W)), hard3)
    r3 = P.plan(g3, road3, rc3, [tg("A", 10, 30)], P_)
    assert "A" in r3["sel"] and r3["sel"]["A"]["hard_violations"] == 0
    assert any(abs(g3.xy(c)[0] - 205) < 1e-6 for c in r3["sel"]["A"]["cells"] if g3.rc(c)[0] - 1 in (30, 31)), "must pass through the gap"
    print("slope/water hard cells OK (blocked, or routed through the gap only)")

def test_target_in_blocked_cell_fails_explicitly():
    hard = np.zeros((H, W), bool); hard[20:26, 20:26] = True
    g, road, rc = setup(np.ones((H, W)), hard)
    res = P.plan(g, road, rc, [tg("IN", 22, 22)], P_)
    assert res["fails"]["IN"].startswith("TARGET_IN_HARD_CONSTRAINT"), res["fails"]
    print("target in blocked cell ->", res["fails"]["IN"])

def test_end_connector_crossing_forbidden_cell_rejected():
    hard = np.zeros((H, W), bool); hard[50:53, :] = True          # blocked band between path end and the road line (row 55)
    g, road, rc = setup(np.ones((H, W)), hard)
    cells = [(48 + 1) * g.W2 + 30 + 1, (49 + 1) * g.W2 + 30 + 1]
    r = P.make_route(g, "x", xy(47, 30), 0.0, {"cells": cells}, "t", road)   # end snaps to the road across the band
    assert r["end_snap_m"] > 0 and r["hard_violations"] > 0 and not r["endpoint_ok"], r
    print("end connector across forbidden band rejected OK")

if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"):
            f()
    print("ALL TESTS PASSED")
