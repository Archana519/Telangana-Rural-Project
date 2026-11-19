"""Offline tests for src/multivillage (contribution 3: multi-village generalisation). No network; a tiny synthetic village exercises the Stage B planner."""
import numpy as np
import pandas as pd
import geopandas as gpd
import pytest
from rasterio.transform import from_origin
from shapely.geometry import LineString, Point, box

from src.multivillage import facilities as FAC, pipeline as PL, run as R
from src.multivillage.sources import Source, sha256_file, write_manifest


def _b(rows):
    return gpd.GeoDataFrame(rows, geometry=[r.pop("geometry") for r in rows], crs=32644)


def test_classify_and_split_targets():
    v = dict(min_house_area_m2=30, min_conf=0.70)
    rows = [dict(id="a", area_m2=20.0, confidence=1.0, dataset="OpenStreetMap", geometry=box(0, 0, 4, 5)),          # too small
            dict(id="b", area_m2=60.0, confidence=0.6, dataset="Google Open Buildings", geometry=box(100, 0, 108, 7.5)),   # low confidence
            dict(id="c", area_m2=60.0, confidence=0.9, dataset="Google Open Buildings", geometry=box(200, 0, 208, 7.5)),   # plausible, 200 m from the road
            dict(id="d", area_m2=60.0, confidence=1.0, dataset="OpenStreetMap", geometry=box(10, 20, 18, 27.5)),           # plausible, 20 m from the road
            dict(id="e", area_m2=400.0, confidence=1.0, dataset="OpenStreetMap", geometry=box(300, 0, 320, 20))]          # large
    b = R.classify(_b(rows), v)
    assert dict(zip(b.id, b.quality_class)) == {"a": "SMALL_EXCLUDED", "b": "LOWCONF_EXCLUDED", "c": "PLAUSIBLE", "d": "PLAUSIBLE", "e": "LARGE_POSSIBLE_MERGE"}
    road = LineString([(-50, 0), (400, 0)])
    houses, gap = R.split_targets(b, road, 30.0)
    assert list(houses.id) == ["c", "d", "e"] and list(houses.hid) == [1, 2, 3]
    assert list(gap.id) == []                         # all three representative points are within 30 m of the road ... except none farther
    houses, gap = R.split_targets(b, LineString([(-50, -200), (400, -200)]), 30.0)
    assert set(gap.id) == {"c", "d", "e"}


def test_facility_status_rules():
    foot = _b([dict(id="f1", geometry=box(0, 0, 10, 10)), dict(id="f2", geometry=box(500, 500, 510, 510))])
    pts = gpd.GeoDataFrame({"id": ["p1", "p2", "p3", "p4", "p5"], "name": ["Govt High School", "Faisalabad College", "Far Clinic", "Outside Hospital", "Govt High School"],
                            "taxonomy_primary": ["high_school", "college_university", "hospital", "hospital", "high_school"], "confidence": [0.9, 0.8, 0.7, 0.7, 0.5]},
                           geometry=[Point(5, 12), Point(505, 505), Point(100, 100), Point(9000, 9000), Point(8, 12)], crs=32644)
    cell = box(-50, -50, 600, 600)
    ex = pd.DataFrame({"id": ["p2"], "reason": ["misgeocoded"]})
    out = FAC.candidates(pts, cell, foot, ex).set_index("id")
    assert out.loc["p1", "status"] == "VERIFIED_USED" and out.loc["p1", "facility_type"] == "school"
    assert out.loc["p2", "status"] == "EXCLUDED_MISGEOCODED_OR_NOT_A_FACILITY"
    assert out.loc["p3", "status"] == "NO_FOOTPRINT_WITHIN_20M_NOT_USED"
    assert out.loc["p4", "status"] == "OUTSIDE_WINDOW_NOT_USED"
    assert "duplicate" in str(out.loc["p5", "manual_exclusion"])          # same normalised name within 150 m, lower confidence


def test_manifest_hashes(tmp_path):
    f = tmp_path / "x.bin"
    f.write_bytes(b"abc")
    s = Source("roads", "role", "provider", "https://example.invalid/x", "rel", "ODbL 1.0", "vector").fingerprint(f, rows=3)
    assert s.sha256 == sha256_file(f) and s.bytes == 3
    write_manifest([s], tmp_path / "m.csv")
    assert "ODbL 1.0" in (tmp_path / "m.csv").read_text()


def test_stage_b_planner_on_a_tiny_village():
    """Four houses in a cul-de-sac 40 m from a road: shared planning must beat independent routes, and the length-only control must be a valid baseline."""
    H, W = 60, 60
    T = from_origin(0, 600, 10, 10)
    cost = np.full((H, W), 3.0, dtype="float32")
    road = LineString([(0, 30), (600, 30)])
    houses = gpd.GeoDataFrame({"hid": [1, 2, 3, 4]}, geometry=[box(290 + 12 * i, 440, 298 + 12 * i, 448) for i in range(4)], crs=32644)
    houses["area_m2"] = houses.area
    world = PL.World(cost, T, (H, W), [road], list(houses.geometry), 4.0)
    cfg = dict(planner=dict(k=3, corridor_m=20.0, corridor_mults=[3.0, 8.0], max_overlap=0.8, max_search_m=1500.0, snap_m=30.0, attach_tol_m=15.0, passes=2))
    p = PL.planner_params(cfg)
    tg = PL.make_targets(houses)
    out = PL.run_all_strategies(world, tg, p, houses)
    rows = {r["plan"]: r for r in out["rows"]}
    two, ind = rows["Two-stage shared plan"], rows["Independent least-cost routes"]
    assert two["targets_routed"] == 4 and ind["targets_routed"] == 4
    assert two["unique_len_m"] < ind["unique_len_m"]
    assert two["unique_len_m"] <= rows["Roads-only shared reference"]["unique_len_m"] + 1e-6
    assert rows["Length-only control"]["targets_routed"] == 4
    assert rows["Straight line"]["unique_len_m"] > 0
