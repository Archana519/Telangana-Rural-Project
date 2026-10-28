"""Tests for audit_road_connectivity.py on SYNTHETIC fixtures only (temporary folders; no project data is read or written).
Run:  python tests\\test_audit_road_connectivity.py      (from the project root; also works from the scripts folder)

Every test records EXPECTED and ACTUAL outcomes; the table is printed at the end of the run.
"""
import hashlib
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
import shapely
from rasterio.transform import from_origin
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

HERE = Path(__file__).resolve().parent
for cand_dir in (HERE, HERE.parent / "scripts", HERE / "scripts"):
    if (cand_dir / "audit_road_connectivity.py").exists():
        SPEC = importlib.util.spec_from_file_location("arc", cand_dir / "audit_road_connectivity.py")
        break
else:
    raise SystemExit("audit_road_connectivity.py not found next to the test or in ..\\scripts")
arc = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(arc)

CRS = "EPSG:32644"
RECORD = []


def rec(test, expected, actual):
    RECORD.append((test, str(expected), str(actual)))


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def gdf_lines(geoms):
    return gpd.GeoDataFrame({"id": list(range(len(geoms)))}, geometry=geoms, crs=CRS)


def model(geoms, tols=(0, 1, 2, 5, 10, 15), angle=45.0):
    return arc.RoadModel(gdf_lines(geoms), [float(t) for t in tols], angle)


def ncomp(m, t, pol="assume_junction"):
    return len(m.state[(pol, float(t))]["lengths"])


# ------------------------------------------------------------------------------------------------ project fixture
def write_wc(path, nodata_box=None):
    arr = np.full((70, 140), 30, dtype="uint8")        # x -200..1200, y -200..500, 10 m cells
    if nodata_box:
        x0, y0, x1, y1 = nodata_box
        c0, c1 = int((x0 + 200) // 10), int((x1 + 200) // 10)
        r0, r1 = int((500 - y1) // 10), int((500 - y0) // 10)
        arr[r0:r1, c0:c1] = 0
    with rasterio.open(path, "w", driver="GTiff", height=70, width=140, count=1, dtype="uint8", crs=CRS,
                       transform=from_origin(-200, 500, 10, 10), nodata=0) as ds:
        ds.write(arr, 1)


STD_ROADS = [LineString([(0, 0), (1000, 0)]), LineString([(500, -100), (500, 100)]), LineString([(0, 300), (100, 300)]), LineString([(1100, 0), (1200, 0)])]
STD_CANDS = [  # cand_id, cluster, geometry, quality, est_roofs
    (1, 1, box(100, 10, 110, 20), "PLAUSIBLE", 1), (2, 2, box(100, 200, 110, 210), "REVIEW", 1), (3, 2, box(300, 60, 310, 70), "UNRESOLVED_MERGE", 6),
    (4, 3, box(40, 310, 50, 320), "PLAUSIBLE", 1), (5, 4, box(700, 0, 710, 10), "PLAUSIBLE", 1)]
STD_FACS = [("1", "School A", "School", Point(200, 30)), ("H2", "Sub Centre B", "Healthcare", Point(800, 150))]


def std_runs():
    def tg():
        return [("F:1", "facility", Point(200, 30)), ("C2", "cluster", Point(105, 205))]
    na_a = [("F:1", LineString([(200, 30), (200, 2)]), dict(attach_to="ROAD", connected=True)),
            ("C2", LineString([(105, 205), (180, 40), (195, 31)]), dict(attach_to="F:1", connected=True))]
    ic_a = [("F:1", LineString([(200, 30), (200, 2)]), dict(attach_to="ROAD")),
            ("C2", LineString([(105, 205), (105, 2)]), dict(attach_to="F:1"))]          # mislabelled on purpose
    na_b = [("F:1", LineString([(200, 30), (200, 12)]), dict(attach_to="ROAD", connected=True))]
    return {"run_a": dict(targets=tg(), na=na_a, ic=ic_a), "run_b": dict(targets=tg()[:1], na=na_b, ic=na_b)}


def make_project(root, roads=None, cands=None, facs=None, runs=None, nodata_box=None, roads_crs=CRS, drop_cand_cols=(), roads_layer="tgrac_road_network",
                 cand_geoms_override=None):
    root = Path(root)
    area = root / "Siddipet" / "Damarakunta"
    (area / "reference").mkdir(parents=True)
    (area / "aligned").mkdir(parents=True)
    (area / "access").mkdir(parents=True)
    roads = STD_ROADS if roads is None else roads
    rg = gpd.GeoDataFrame({"RD_TYPE": ["x"] * len(roads)}, geometry=roads, crs=CRS)
    if roads_crs != CRS:
        rg = rg.to_crs(roads_crs)
    roads_p = area / "reference" / "roads.gpkg"
    rg.to_file(roads_p, layer=roads_layer, driver="GPKG")
    union = unary_union(roads)
    cands = STD_CANDS if cands is None else cands
    geoms = [c[2] for c in cands] if cand_geoms_override is None else cand_geoms_override
    cdf = gpd.GeoDataFrame({"cand_id": [c[0] for c in cands], "cluster_id": [c[1] for c in cands], "quality_class": [c[3] for c in cands],
                            "est_roofs": [c[4] for c in cands], "flags": [""] * len(cands)}, geometry=geoms, crs=CRS)
    dist = []
    for g in geoms:
        dist.append(round(g.distance(union), 2) if g is not None and not g.is_empty and g.is_valid else 0.0)
    cdf["dist_to_ref_road_m"] = dist
    cdf["gap_flag"] = cdf["dist_to_ref_road_m"] > 50
    cl_ids = sorted(set(cdf["cluster_id"]))
    mind = cdf.groupby("cluster_id")["dist_to_ref_road_m"].min()
    cl = gpd.GeoDataFrame({"cluster_id": cl_ids, "n_candidates": [int((cdf.cluster_id == c).sum()) for c in cl_ids],
                           "kind": ["SETTLEMENT_CLUSTER" if c == 2 else "ISOLATED_OR_SMALL_GROUP" for c in cl_ids],
                           "gap_flag": [bool(mind[c] > 50) for c in cl_ids]}, geometry=[box(0, 0, 1, 1)] * len(cl_ids), crs=CRS)
    facs = STD_FACS if facs is None else facs
    fdf = gpd.GeoDataFrame({"facility_id": [f[0] for f in facs], "facility_name": [f[1] for f in facs], "facility_type": [f[2] for f in facs],
                            "dist_to_ref_road_m": [round(f[3].distance(union), 2) for f in facs]}, geometry=[f[3] for f in facs], crs=CRS)
    cdf = cdf.drop(columns=list(drop_cand_cols))
    access = area / "access" / "access_assessment.gpkg"
    cdf.to_file(access, layer="candidate_access", driver="GPKG")
    cl.to_file(access, layer="clusters", driver="GPKG")
    fdf.to_file(access, layer="facility_access", driver="GPKG")
    wc = area / "aligned" / "wc.tif"
    write_wc(wc, nodata_box)
    runs_root = area / "results" / "planning_experiments" / "network_v2"
    for rn, r in (std_runs() if runs is None else runs).items():
        rd = runs_root / rn
        rd.mkdir(parents=True)
        gp = rd / "network_v2.gpkg"
        tg = gpd.GeoDataFrame({"id": [t[0] for t in r["targets"]], "kind": [t[1] for t in r["targets"]]}, geometry=[t[2] for t in r["targets"]], crs=CRS)
        tg.to_file(gp, layer="targets", driver="GPKG")
        for key, layer in (("na", "routes_network_aware"), ("ic", "routes_independent")):
            rows = r[key]
            df = gpd.GeoDataFrame({"target": [x[0] for x in rows], "length_m": [round(x[1].length, 2) for x in rows],
                                   "attach_to": [x[2].get("attach_to", "") for x in rows]}, geometry=[x[1] for x in rows], crs=CRS)
            if key == "na":
                df["connected"] = [x[2].get("connected", False) for x in rows]
            df.to_file(gp, layer=layer, driver="GPKG")
        (rd / "summary.json").write_text(json.dumps({"params": {"attach_tol_m": 15.0}}), encoding="utf-8")
    return dict(root=root, area=area, roads=roads_p, access=access, wc=wc, runs_root=runs_root, out_root=area / "results" / "connectivity_audit_v1")


def cli(p, tag="t1", extra=()):
    return ["--project-root", str(p["root"]), "--runs-root", str(p["runs_root"]), "--runs", "run_a", "run_b", "--out-root", str(p["out_root"]), "--tag", tag,
            "--access-gpkg", str(p["access"]), "--roads", str(p["roads"]), "--worldcover", str(p["wc"]), "--skip-prior-comparison", *extra]


def read_csv(p, tag, name):
    return pd.read_csv(Path(p["out_root"]) / tag / name)


def routes_for(m, specs, tols=(0, 1, 2, 5, 10, 15, 20), attach=15.0, near=25.0):
    """specs: list of (target, LineString). Targets layer = first vertex of each route (the start)."""
    r = gpd.GeoDataFrame({"target": [s[0] for s in specs]}, geometry=[s[1] for s in specs], crs=CRS)
    t = gpd.GeoDataFrame({"id": [s[0] for s in specs], "kind": ["facility"] * len(specs)}, geometry=[Point(s[1].coords[0]) for s in specs], crs=CRS)
    df, recs, byk, _ = arc.eval_routes("rx", "network_aware", r, t, m, None, [float(x) for x in tols], attach, near)
    return df


def row(df, key, t):
    x = df[(df["route_key"] == key) & np.isclose(df["tolerance_m"], t)]
    assert len(x) == 1, (key, t, len(x))
    return x.iloc[0]


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="arc_test_")
        arc._HOOKS["after_processing"] = None
        arc._HOOKS["before_processing"] = None

    def tearDown(self):
        arc._HOOKS["after_processing"] = None
        shutil.rmtree(self.tmp, ignore_errors=True)


# ================================================================================================ road graph
class TestRoadGraph(Base):
    def test_01_endpoint_gap_3m(self):
        """T1: 3 m endpoint gap -> not bridged at 2 m; inferred bridge at 5 m."""
        m = model([LineString([(0, 0), (100, 0)]), LineString([(103, 0), (200, 0)])])
        a2, a5 = ncomp(m, 2), ncomp(m, 5)
        b2, b5 = m.state[("assume_junction", 2.0)]["n_bridge_edges"], m.state[("assume_junction", 5.0)]["n_bridge_edges"]
        rec("T1 3 m gap", "2 comps & 0 bridges at 2 m; 1 comp & 1 inferred bridge at 5 m", f"{a2} comps/{b2} bridges at 2 m; {a5} comps/{b5} bridge at 5 m")
        self.assertEqual((a2, b2, a5, b5), (2, 0, 1, 1))
        self.assertEqual(ncomp(m, 0), 2)
        self.assertEqual(ncomp(m, 1), 2)

    def test_02_parallel_lines_do_not_merge(self):
        """T2: parallel lines 3 m apart (aligned and staggered) never merge at any tolerance."""
        for b in ([(0, 3), (100, 3)], [(50, 3), (150, 3)]):
            m = model([LineString([(0, 0), (100, 0)]), LineString(b)])
            counts = [ncomp(m, t) for t in (0, 1, 2, 5, 10, 15)]
            valid = sum(1 for x in m.bridges if x["direction_ok"])
            rec("T2 parallel 3 m", "2 components at every tolerance; 0 direction-valid bridges", f"{counts}; valid bridges={valid}; candidates={len(m.bridges)}")
            self.assertEqual(counts, [2] * 6)
            self.assertEqual(valid, 0)
            self.assertGreater(len(m.bridges), 0)            # the pair WAS considered and rejected by the direction rule

    def test_03_crossing_policy(self):
        """T3: crossing without a shared vertex is detected and marked ASSUMED; connects only under assume_junction."""
        m = model([LineString([(0, 0), (100, 0)]), LineString([(50, -50), (50, 50)])])
        kinds = [r["kind"] for r in m.junctions]
        n_a, n_e = ncomp(m, 0, "assume_junction"), ncomp(m, 0, "explicit_only")
        ev = [r["evidence_class"] for r in m.junctions]
        rec("T3 crossing no shared vertex", "kind CROSSING_NO_SHARED_VERTEX / ASSUMED_JUNCTION...; 1 comp (assume_junction), 2 comps (explicit_only)", f"{kinds}/{ev}; {n_a}, {n_e}")
        self.assertEqual(kinds, ["CROSSING_NO_SHARED_VERTEX"])
        self.assertEqual(ev, ["ASSUMED_JUNCTION_GEOMETRIC_CROSSING"])
        self.assertEqual((n_a, n_e), (1, 2))
        m2 = model([LineString([(0, 0), (50, 0), (100, 0)]), LineString([(50, -50), (50, 0), (50, 50)])])
        k2 = [r["kind"] for r in m2.junctions]
        rec("T3 crossing shared vertex", "CROSSING_SHARED_VERTEX connects under both policies", f"{k2}; {ncomp(m2, 0)}, {ncomp(m2, 0, 'explicit_only')}")
        self.assertEqual(k2, ["CROSSING_SHARED_VERTEX"])
        self.assertEqual((ncomp(m2, 0), ncomp(m2, 0, "explicit_only")), (1, 1))
        m3 = model([LineString([(0, 0), (100, 0)]), LineString([(100, 0), (150, 40)]), LineString([(50, 0), (50, 30)])])
        k3 = sorted(r["kind"] for r in m3.junctions)
        rec("T3 endpoint and T classes", "ENDPOINT_ENDPOINT + T_JUNCTION", str(k3))
        self.assertEqual(k3, ["ENDPOINT_ENDPOINT", "T_JUNCTION"])

    def test_08_main_component_by_length(self):
        """T8: main component = largest total length even when another component has more segments."""
        many = [LineString([(i * 10, 500), (i * 10 + 10, 500)]) for i in range(6)]       # 6 segments, 60 m
        one = [LineString([(0, 0), (200, 0)])]                                              # 1 segment, 200 m
        m = model(many + one)
        st = m.state[("assume_junction", 0.0)]
        main_segs = st["comps"][0]
        rec("T8 main by length", "main = the single 200 m segment (not the 6-segment 60 m chain)", f"main segments={main_segs}, lengths={[round(x, 1) for x in st['lengths']]}")
        self.assertEqual(main_segs, [6])
        self.assertAlmostEqual(st["lengths"][0], 200.0)
        self.assertEqual(len(st["comps"][1]), 6)

    def test_dangling_and_near_gap_rows(self):
        m = model([LineString([(0, 0), (100, 0)]), LineString([(103, 0), (200, 0)])])
        dang = [e for e in m.ends if e["dangling"]]
        rec("dangling ends", "4 dangling ends at t0, 2 at 5 m (the bridged pair is resolved)", f"{len(dang)} at t0, {m.state[('assume_junction', 5.0)]['n_dangling']} at 5 m")
        self.assertEqual(len(dang), 4)
        self.assertEqual(m.state[("assume_junction", 5.0)]["n_dangling"], 2)

    def test_invalid_road_geometries_reported(self):
        gdf = gpd.GeoDataFrame({"id": [0, 1, 2, 3]}, geometry=[LineString([(0, 0), (10, 0)]), LineString(), Point(5, 5), LineString([(0, 0), (0, 0)])], crs=CRS)
        m = arc.RoadModel(gdf, [0.0, 1.0], 45.0)
        issues = sorted(i["issue"].split(":")[0] for i in m.geom_issues)
        rec("T11 bad road geometries", "3 issues reported (EMPTY, NOT_LINE, ZERO_LENGTH_PART); 1 usable segment", f"{issues}; segments={len(m.segs)}")
        self.assertEqual(len(m.segs), 1)
        self.assertEqual(len(m.geom_issues), 3)


# ================================================================================================ routes
class TestRoutes(Base):
    def setUp(self):
        super().setUp()
        self.road = model([LineString([(0, 0), (1000, 0)])])

    def test_04_three_route_chain(self):
        """T4: R1 -> R2 -> R3 -> ROAD(main); breaks at 2 m because the last link (5 m) is not met."""
        specs = [("R1", LineString([(350, 300), (350, 152)])), ("R2", LineString([(300, 150), (398, 150)])), ("R3", LineString([(400, 200), (400, 5)]))]
        df = routes_for(self.road, specs)
        r5, r2 = row(df, "R1", 5), row(df, "R1", 2)
        rec("T4 chain @5 m", "R1>R2>R3>ROAD[main], outcome ROAD_MAIN, hops 3, min tolerance 5", f"{r5['chain']} {r5['chain_outcome']} hops={r5['chain_hops']} min_tol={r5['min_tolerance_to_main_m']:.2f}")
        rec("T4 chain @2 m", "R1>R2>R3 DEAD_END (R3 not within 2 m of the road)", f"{r2['chain']} {r2['chain_outcome']}")
        self.assertEqual(r5["chain"], "R1>R2>R3>ROAD[main]")
        self.assertEqual(r5["chain_outcome"], "ROAD_MAIN")
        self.assertEqual(int(r5["chain_hops"]), 3)
        self.assertAlmostEqual(r5["min_tolerance_to_main_m"], 5.0, places=6)
        self.assertEqual(r5["bottleneck_chain"], "R1>R2>R3>MAIN")
        self.assertTrue(bool(r5["reaches_main_deterministic"]))
        self.assertEqual(r2["chain"], "R1>R2>R3")
        self.assertEqual(r2["chain_outcome"], "DEAD_END")
        self.assertFalse(bool(r2["reaches_main_any_resolution"]))

    def test_05_two_route_cycle(self):
        """T5: two routes whose terminals lie on each other, none near a road -> CYCLE (and DEAD_END below the link distance)."""
        specs = [("Ra", LineString([(0, 100), (100, 100)])), ("Rb", LineString([(100, 103), (0, 103)]))]
        df = routes_for(self.road, specs)
        a5, a2 = row(df, "Ra", 5), row(df, "Ra", 2)
        rec("T5 cycle", "CYCLE at 5 m for both; DEAD_END at 2 m; never reaches main", f"Ra@5={a5['chain_outcome']} ({a5['chain']}), Rb@5={row(df, 'Rb', 5)['chain_outcome']}, Ra@2={a2['chain_outcome']}")
        self.assertEqual(a5["chain_outcome"], "CYCLE")
        self.assertEqual(row(df, "Rb", 5)["chain_outcome"], "CYCLE")
        self.assertEqual(a2["chain_outcome"], "DEAD_END")
        self.assertFalse(bool(a5["reaches_main_deterministic"]))
        self.assertFalse(bool(a5["reaches_any_road_deterministic"]))

    def test_06_route_20m_from_road(self):
        """T6: terminal 20 m from a road does not attach at 15 m (attaches only at 20 m)."""
        df = routes_for(self.road, [("R", LineString([(100, 80), (100, 20)]))])
        r15, r20 = row(df, "R", 15), row(df, "R", 20)
        rec("T6 20 m", "DEAD_END at 15 m (terminal_to_road 20.0); ROAD_MAIN at 20 m", f"{r15['chain_outcome']} d={r15['terminal_to_road_m']:.2f}; {r20['chain_outcome']}")
        self.assertEqual(r15["chain_outcome"], "DEAD_END")
        self.assertAlmostEqual(r15["terminal_to_road_m"], 20.0)
        self.assertEqual(r20["chain_outcome"], "ROAD_MAIN")

    def test_07_ambiguous_road_and_route(self):
        """T7: terminal within tolerance of a road AND another route -> deterministic ROAD-first hop, flagged ambiguous, repeatable."""
        specs = [("R1", LineString([(100, 40), (100, 6)])), ("R2", LineString([(60, 10), (140, 10)]))]
        df1, df2 = routes_for(self.road, specs), routes_for(self.road, specs)
        r = row(df1, "R1", 10)
        rec("T7 ambiguous", "next_hop ROAD, ambiguous_options True, 2 options, ROAD_MAIN; identical on repeat", f"{r['next_hop']}, {r['ambiguous_options']}, {r['n_attachment_options']}, {r['chain_outcome']}; repeat equal={df1.equals(df2)}")
        self.assertEqual(r["next_hop"], "ROAD")
        self.assertTrue(bool(r["ambiguous_options"]))
        self.assertEqual(int(r["n_attachment_options"]), 2)
        self.assertEqual(r["chain_outcome"], "ROAD_MAIN")
        self.assertTrue(df1.equals(df2))
        # at 5 m only R2 (4 m) is an option: the road (6 m) is out of reach, so the hop is R2 and nothing is ambiguous
        self.assertFalse(bool(row(df1, "R1", 5)["ambiguous_options"]))
        self.assertEqual(row(df1, "R1", 5)["next_hop"], "R2")

    def test_17_close_but_not_connected_stays_proximity_only(self):
        """T17: a route running 8 m beside a road with a far terminal is NOT attached; it is flagged proximity-only."""
        df = routes_for(self.road, [("R", LineString([(100, 30), (100, 8), (300, 8), (300, 40)]))])
        r = row(df, "R", 15)
        rec("T17 proximity only", "DEAD_END, near_road_but_not_attached True, geometry min distance 8.0, not touching", f"{r['chain_outcome']}, {r['near_road_but_not_attached']}, {r['route_geometry_min_dist_to_road_m']:.1f}, intersects={r['route_intersects_road']}")
        self.assertEqual(r["chain_outcome"], "DEAD_END")
        self.assertTrue(bool(r["near_road_but_not_attached"]))
        self.assertAlmostEqual(r["route_geometry_min_dist_to_road_m"], 8.0)
        self.assertFalse(bool(r["route_intersects_road"]))
        self.assertFalse(bool(r["reaches_any_road_deterministic"]))

    def test_minor_component_outcome(self):
        road = model([LineString([(0, 0), (1000, 0)]), LineString([(0, 300), (100, 300)])])
        df = routes_for(road, [("R", LineString([(50, 380), (50, 305)]))])
        r = row(df, "R", 5)
        rec("route to minor component", "ROAD_MINOR; does not reach main at 5 m", f"{r['chain_outcome']}; main={r['reaches_main_deterministic']}")
        self.assertEqual(r["chain_outcome"], "ROAD_MINOR")
        self.assertFalse(bool(r["reaches_main_deterministic"]))

    def test_empty_route_geometry_reported(self):
        r = gpd.GeoDataFrame({"target": ["A", "B"]}, geometry=[LineString([(100, 40), (100, 4)]), LineString()], crs=CRS)
        t = gpd.GeoDataFrame({"id": ["A", "B"], "kind": ["f", "f"]}, geometry=[Point(100, 40), Point(0, 0)], crs=CRS)
        df, _, _, _ = arc.eval_routes("rx", "network_aware", r, t, self.road, None, [5.0], 15.0, 25.0)
        b = df[df["route_key"] == "B"].iloc[0]
        rec("T11 empty route", "B UNEVALUABLE (EMPTY_GEOMETRY); A evaluated", f"{b['chain_outcome']} {b['unevaluable_reason']}; A={df[df.route_key == 'A'].iloc[0]['chain_outcome']}")
        self.assertEqual(b["chain_outcome"], "UNEVALUABLE")
        self.assertEqual(b["unevaluable_reason"], "EMPTY_GEOMETRY")
        self.assertEqual(df[df.route_key == "A"].iloc[0]["chain_outcome"], "ROAD_MAIN")


# ================================================================================================ candidates
class TestCandidates(Base):
    def feats(self, road, polys, thr=(25.0, 50.0, 100.0), wc=None):
        g = gpd.GeoDataFrame({"i": range(len(polys))}, geometry=polys, crs=CRS)
        return arc.evaluate_features(g, "poly", road, wc, list(thr), 1.0, 15.0)

    def test_09_main_vs_minor_polygons(self):
        """T9: polygon touching the main component vs polygon near only a minor component."""
        road = model([LineString([(0, 0), (500, 0)]), LineString([(0, 300), (100, 300)])])
        df, _ = self.feats(road, [box(200, 0, 210, 10), box(40, 310, 50, 320), box(40, 300, 50, 310)])
        a, b, c = df.iloc[0], df.iloc[1], df.iloc[2]
        rec("T9 main/minor", "A: CONTACT_MAIN_COMPONENT; B: minor, any<=25 True, main<=25 False, NOT_ESTABLISHED_PROXIMITY_ONLY; C: CONTACT_MINOR_COMPONENT",
            f"A {a['connectivity_status']}/{a['nearest_component_class']}; B {b['connectivity_status']}/{b['nearest_component_class']} any25={b['poly_any_le25']} main25={b['poly_main_le25']}; C {c['connectivity_status']}")
        self.assertEqual((a["connectivity_status"], a["nearest_component_class"]), ("CONTACT_MAIN_COMPONENT", "main"))
        self.assertEqual((b["connectivity_status"], b["nearest_component_class"]), ("NOT_ESTABLISHED_PROXIMITY_ONLY", "minor"))
        self.assertTrue(b["poly_any_le25"] and not b["poly_main_le25"] and not b["poly_main_le100"])
        self.assertEqual(c["connectivity_status"], "CONTACT_MINOR_COMPONENT")
        self.assertAlmostEqual(a["d_poly_any_m"], 0.0)
        self.assertAlmostEqual(b["d_poly_any_m"], 10.0)

    def test_10_outline_and_point_distances_independent(self):
        """T10: boundary-ring, filled-polygon and representative-point distances are computed independently; no ordering is imposed."""
        road = model([LineString([(0, 0), (1000, 0)]), LineString([(140, 60), (160, 60)])])
        court = box(100, 20, 200, 120)           # a road piece lies INSIDE the footprint
        plain = box(300, 10, 310, 20)
        df, _ = self.feats(road, [court, plain])
        gu = unary_union([LineString([(0, 0), (1000, 0)]), LineString([(140, 60), (160, 60)])])
        for i, g in enumerate([court, plain]):
            self.assertAlmostEqual(df.iloc[i]["d_poly_any_m"], g.distance(gu), places=6)
            self.assertAlmostEqual(df.iloc[i]["d_boundary_any_m"], g.boundary.distance(gu), places=6)
            self.assertAlmostEqual(df.iloc[i]["d_point_any_m"], g.representative_point().distance(gu), places=6)
        c, p = df.iloc[0], df.iloc[1]
        rec("T10 courtyard polygon", "filled 0.0; boundary ring 20.0; representative point 10.0 (boundary > point)", f"{c['d_poly_any_m']:.2f}; {c['d_boundary_any_m']:.2f}; {c['d_point_any_m']:.2f}")
        rec("T10 plain polygon", "filled 10.0; boundary 10.0; representative point 15.0 (boundary < point)", f"{p['d_poly_any_m']:.2f}; {p['d_boundary_any_m']:.2f}; {p['d_point_any_m']:.2f}")
        self.assertGreater(c["d_boundary_any_m"], c["d_point_any_m"])        # ordering one way ...
        self.assertLess(p["d_boundary_any_m"], p["d_point_any_m"])           # ... and the other way: no universal inequality
        self.assertAlmostEqual(c["d_poly_any_m"], 0.0)
        # concave polygon whose CENTROID is outside the footprint and closer to the road than any polygon point (a further counterexample to a universal ordering)
        cshape = Polygon([(0, 20), (60, 20), (60, 30), (10, 30), (10, 70), (60, 70), (60, 80), (0, 80)])
        self.assertFalse(cshape.contains(cshape.centroid))
        self.assertLess(cshape.centroid.distance(LineString([(40, 0), (40, 0.001)])), 100)   # sanity: geometry is usable
        rec("T10 concave polygon", "centroid lies outside the polygon", f"contains={cshape.contains(cshape.centroid)}")

    def test_11_empty_and_invalid_polygons(self):
        """T11: empty / invalid / non-polygon geometries are reported, never crash."""
        road = model([LineString([(0, 0), (500, 0)])])
        bow = Polygon([(100, 10), (110, 20), (110, 10), (100, 20)])            # self-intersecting bowtie
        df, geoms = self.feats(road, [box(0, 5, 10, 15), Polygon(), bow, None, Point(1, 1)])
        reasons = list(df["unevaluable_reason"])
        st = list(df["geometry_status"])
        rec("T11 polygons", "OK; EMPTY_GEOMETRY; INVALID_REPAIRED (evaluated); EMPTY_GEOMETRY(None); NOT_POLYGON:Point", f"{st}")
        self.assertEqual(st[0], "OK")
        self.assertEqual(st[1], "EMPTY_GEOMETRY")
        self.assertEqual(st[2], "INVALID_REPAIRED")
        self.assertEqual(reasons[2], "")
        self.assertTrue(np.isfinite(df.iloc[2]["d_poly_any_m"]))
        self.assertEqual(st[3], "EMPTY_GEOMETRY")
        self.assertTrue(st[4].startswith("NOT_POLYGON"))
        self.assertTrue(np.isnan(df.iloc[1]["d_poly_any_m"]))
        self.assertEqual(df.iloc[1]["connectivity_status"], "UNEVALUABLE")

    def test_18_worldcover_flag_only(self):
        """T18: NoData footprint sets the coverage flag but changes no distance (direct and via the CLI)."""
        p = make_project(Path(self.tmp) / "w", nodata_box=(90, 190, 120, 220))
        wc = arc.WorldCover(str(p["wc"]), 32644)
        road = model(STD_ROADS)
        df_wc, _ = self.feats(road, [c[2] for c in STD_CANDS], wc=wc)
        df_no, _ = self.feats(road, [c[2] for c in STD_CANDS], wc=None)
        dist_cols = [c for c in df_wc.columns if c.startswith(("d_", "poly_", "point_", "contact_"))]
        same = all(np.allclose(df_wc[c].astype(float), df_no[c].astype(float), equal_nan=True) for c in dist_cols)
        rec("T18 direct", "cand 2 (box 100,200..110,210) ALL_NODATA & flagged; every distance/proximity column identical with and without the raster",
            f"{list(df_wc['wc_status'])}; flags={list(df_wc['intersects_wc_nodata'])}; distances identical={same}")
        self.assertEqual(df_wc.iloc[1]["wc_status"], "ALL_NODATA")
        self.assertTrue(bool(df_wc.iloc[1]["intersects_wc_nodata"]))
        self.assertFalse(df_wc["intersects_wc_nodata"].drop(1).any())
        self.assertTrue(same)
        self.assertEqual(list(df_no["wc_status"].unique()), ["UNAVAILABLE"])
        a1 = arc.main(cli(p, "wc"))
        a2 = arc.main(cli(p, "nowc", ["--no-worldcover"]))
        c1, c2 = read_csv(p, "wc", "candidate_connectivity.csv"), read_csv(p, "nowc", "candidate_connectivity.csv")
        dcols = [c for c in c1.columns if c.startswith(("d_", "poly_", "point_", "contact_")) or "__" in c and "wc" not in c]
        eq = all(c1[c].equals(c2[c]) for c in dcols)
        rec("T18 CLI", "exit 0 both; every distance column identical; flag differs", f"exit {a1},{a2}; identical={eq}; flag with raster={c1['intersects_wc_nodata'].sum()} without={c2['intersects_wc_nodata'].sum()}")
        self.assertEqual((a1, a2), (0, 0))
        self.assertTrue(eq)
        self.assertEqual(int(c1["intersects_wc_nodata"].sum()), 1)
        self.assertEqual(int(c2["intersects_wc_nodata"].sum()), 0)


# ================================================================================================ CLI behaviour
class TestCli(Base):
    def project(self, name="p", **kw):
        return make_project(Path(self.tmp) / name, **kw)

    def test_12a_missing_required_column_fails_before_outputs(self):
        p = self.project(drop_cand_cols=["est_roofs"])
        code = arc.main(cli(p))
        rec("T12 missing column", "exit 1 and no output folder", f"exit {code}; out exists={(p['out_root'] / 't1').exists()}")
        self.assertEqual(code, 1)
        self.assertFalse((p["out_root"] / "t1").exists())

    def test_12b_wrong_crs_fails_before_outputs(self):
        p = self.project(roads_crs="EPSG:4326")
        code = arc.main(cli(p))
        rec("T12 wrong CRS", "exit 1 and no output folder", f"exit {code}; out exists={(p['out_root'] / 't1').exists()}")
        self.assertEqual(code, 1)
        self.assertFalse((p["out_root"] / "t1").exists())

    def test_12c_missing_roads_layer_and_missing_file(self):
        p = self.project(roads_layer="other_layer")
        self.assertEqual(arc.main(cli(p)), 1)
        self.assertFalse((p["out_root"] / "t1").exists())
        p2 = self.project("p2")
        os.remove(p2["wc"])
        self.assertEqual(arc.main(cli(p2)), 1)
        rec("T12 missing layer / file", "exit 1, nothing written", "exit 1, 1")

    def test_13_non_empty_output_dir_refused(self):
        p = self.project()
        out = p["out_root"] / "t1"
        out.mkdir(parents=True)
        (out / "keep.txt").write_text("precious", encoding="utf-8")
        before = sorted(os.listdir(out))
        code = arc.main(cli(p))
        after = sorted(os.listdir(out))
        rec("T13 non-empty output", "exit 1; folder content unchanged", f"exit {code}; before={before} after={after}; keep.txt={(out / 'keep.txt').read_text()}")
        self.assertEqual(code, 1)
        self.assertEqual(before, after)
        self.assertEqual((out / "keep.txt").read_text(), "precious")

    def test_14_input_mutation_invalidates_report(self):
        p = self.project()

        def mutate(ctx):
            with open(p["roads"], "ab") as f:
                f.write(b"tamper")
        arc._HOOKS["after_processing"] = mutate
        code = arc.main(cli(p))
        out = p["out_root"] / "t1"
        names = sorted(os.listdir(out))
        rec("T14 mutation", "exit 2; INPUT_CHANGED_REPORT_INVALID.txt present; no candidate_connectivity.csv", f"exit {code}; files={names}")
        self.assertEqual(code, 2)
        self.assertIn("INPUT_CHANGED_REPORT_INVALID.txt", names)
        self.assertNotIn("candidate_connectivity.csv", names)
        self.assertIn("roads.gpkg", (out / "INPUT_CHANGED_REPORT_INVALID.txt").read_text())

    def test_14b_run_folder_listing_change_invalidates(self):
        p = self.project()
        arc._HOOKS["after_processing"] = lambda ctx: (p["runs_root"] / "run_a" / "new_file.txt").write_text("x")
        code = arc.main(cli(p))
        rec("T14 run-folder change", "exit 2", f"exit {code}")
        self.assertEqual(code, 2)

    def test_15_hashes_identical_after_clean_run(self):
        p = self.project()
        files = [p["roads"], p["access"], p["wc"]] + [p["runs_root"] / r / n for r in ("run_a", "run_b") for n in ("network_v2.gpkg", "summary.json")]
        before = {str(f): sha(f) for f in files}
        listing = {str(f): sorted(os.listdir(Path(f).parent)) for f in files}
        code = arc.main(cli(p))
        after = {str(f): sha(f) for f in files}
        integ = json.loads((p["out_root"] / "t1" / "input_integrity.json").read_text())
        rec("T15 hashes", "exit 0; all input hashes identical; integrity json inputs_unchanged True; no new files beside inputs", f"exit {code}; identical={before == after}; json={integ['inputs_unchanged']}")
        self.assertEqual(code, 0)
        self.assertEqual(before, after)
        self.assertTrue(integ["inputs_unchanged"])
        self.assertEqual(listing, {str(f): sorted(os.listdir(Path(f).parent)) for f in files})
        for f in files:
            self.assertEqual(integ["inputs_before"][str(f)]["sha256"], before[str(f)])
            self.assertEqual(integ["inputs_after"][str(f)]["sha256"], before[str(f)])

    def test_16_determinism(self):
        p = self.project()
        c1, c2 = arc.main(cli(p, "d1")), arc.main(cli(p, "d2"))
        names = [n for n in os.listdir(p["out_root"] / "d1") if n.endswith((".csv", ".txt")) and n != "manifest.csv"] + ["connectivity_audit_summary.json"]
        same = {n: (p["out_root"] / "d1" / n).read_bytes() == (p["out_root"] / "d2" / n).read_bytes() for n in names}
        # report mentions only input paths (identical); tags differ only in the folder name, which is not written into the files
        rec("T16 determinism", "both exit 0; every csv/txt/json byte-identical (manifest and integrity json excluded: they hold timestamps)", f"exit {c1},{c2}; identical={all(same.values())}; checked={len(same)} files")
        self.assertEqual((c1, c2), (0, 0))
        self.assertTrue(all(same.values()), [n for n, v in same.items() if not v])

    def test_outputs_complete_and_documented(self):
        p = self.project()
        self.assertEqual(arc.main(cli(p)), 0)
        out = p["out_root"] / "t1"
        need = ["road_graph_tolerance_sweep.csv", "road_components.csv", "road_near_gaps.csv", "road_junctions.csv", "candidate_connectivity.csv", "route_connectivity.csv",
                "facility_connectivity.csv", "summary_by_group.csv", "checks.csv", "data_dictionary.csv", "connectivity_audit.gpkg", "connectivity_audit_report.txt",
                "connectivity_audit_summary.json", "input_integrity.json", "manifest.csv"]
        present = sorted(os.listdir(out))
        missing = [n for n in need if n not in present]
        dd = pd.read_csv(out / "data_dictionary.csv")
        chk = pd.read_csv(out / "checks.csv")
        try:
            layers = gpd.list_layers(out / "connectivity_audit.gpkg")["name"].tolist()
        except AttributeError:                       # geopandas < 1.0
            import fiona
            layers = fiona.listlayers(str(out / "connectivity_audit.gpkg"))
        rec("outputs", "all 15 files; data dictionary has no UNDOCUMENTED COLUMN; DICT_complete PASS; no FAIL checks; gpkg has candidates/facilities/road_segments/dangling_ends/routes_at_attach_tol",
            f"missing={missing}; undocumented={(dd['definition'] == 'UNDOCUMENTED COLUMN').sum()}; FAIL={(chk['status'] == 'FAIL').sum()}; layers={layers}")
        self.assertEqual(missing, [])
        self.assertEqual(int((dd["definition"] == "UNDOCUMENTED COLUMN").sum()), 0, dd[dd["definition"] == "UNDOCUMENTED COLUMN"].to_string())
        self.assertEqual(chk[chk.check_id == "DICT_complete"].iloc[0]["status"], "PASS")
        self.assertEqual(int((chk["status"] == "FAIL").sum()), 0, chk[chk.status == "FAIL"].to_string())
        for l in ("candidates", "facilities", "road_segments", "dangling_ends", "routes_at_attach_tol"):
            self.assertIn(l, layers)
        man = pd.read_csv(out / "manifest.csv")
        for r in man.itertuples():
            self.assertEqual(sha(out / r.file), r.sha256)
        self.assertIn("NOT established", (out / "connectivity_audit_report.txt").read_text())

    def test_candidate_table_values(self):
        p = self.project()
        self.assertEqual(arc.main(cli(p)), 0)
        c = read_csv(p, "t1", "candidate_connectivity.csv").set_index("cand_id")
        rec("candidate table", "5 rows; cand 5 touches the main road (CONTACT_MAIN_COMPONENT); cand 4 near minor only (50>d>25 not required, nearest minor); cand 2 is 90 m from the minor road (not within 50 m, within 100 m)",
            f"n={len(c)}; c5={c.loc[5, 'connectivity_status']}; c4={c.loc[4, 'nearest_component_class']}/{c.loc[4, 'connectivity_status']}; c2 d={c.loc[2, 'd_poly_any_m']}")
        self.assertEqual(len(c), 5)
        self.assertEqual(c.loc[5, "connectivity_status"], "CONTACT_MAIN_COMPONENT")
        self.assertEqual(c.loc[4, "nearest_component_class"], "minor")
        self.assertEqual(c.loc[4, "connectivity_status"], "NOT_ESTABLISHED_PROXIMITY_ONLY")
        self.assertAlmostEqual(c.loc[2, "d_poly_any_m"], 90.0, places=2)
        self.assertFalse(c.loc[2, "poly_any_le50"])
        self.assertTrue(c.loc[2, "poly_any_le100"])
        self.assertTrue(c.loc[3, "poly_any_le100"] and not c.loc[3, "poly_any_le50"])
        # by-construction: run_a/network_aware route C2 starts inside polygon 2
        self.assertTrue(c.loc[2, "run_a__network_aware__start_in_polygon"])
        self.assertEqual(c.loc[2, "run_a__network_aware__gain_class_headline"], "NOT_WITHIN" if c.loc[2, "run_a__network_aware__d_roads_routes_poly_m"] > 50 else "BY_CONSTRUCTION")

    def test_route_claims_compared_not_trusted(self):
        p = self.project()
        self.assertEqual(arc.main(cli(p)), 0)
        r = read_csv(p, "t1", "route_connectivity.csv")
        x = r[(r.run == "run_a") & (r.scenario == "independent") & (r.route_key == "C2") & np.isclose(r.tolerance_m, 15)].iloc[0]
        y = r[(r.run == "run_a") & (r.scenario == "network_aware") & (r.route_key == "C2") & np.isclose(r.tolerance_m, 15)].iloc[0]
        rec("claims", "independent C2 claimed attach_to F:1 but terminal is on the road -> DISAGREE; network-aware C2 chain C2>F:1>ROAD[main] AGREE",
            f"ind: {x['claim_attach_to_vs_independent']} ({x['chain']}); na: {y['claim_attach_to_vs_independent']} ({y['chain']})")
        self.assertEqual(x["claim_attach_to_vs_independent"], "DISAGREE")
        self.assertEqual(y["chain"], "C2>F:1>ROAD[main]")
        self.assertEqual(y["claim_attach_to_vs_independent"], "AGREE")
        chk = read_csv(p, "t1", "checks.csv")
        self.assertEqual(chk[chk.check_id == "CLAIM_attach_run_a_independent"].iloc[0]["status"], "FLAG")

    def test_facility_rows(self):
        p = self.project()
        self.assertEqual(arc.main(cli(p)), 0)
        f = read_csv(p, "t1", "facility_connectivity.csv").set_index("facility_id")
        rec("facilities", "F 1 is 30 m from the road; H2 is 150 m; run_a route for 1 reaches main; no route for H2",
            f"d1={f.loc['1', 'd_poly_any_m']}, dH2={f.loc['H2', 'd_poly_any_m']}, reach={f.loc['1', 'run_a__network_aware__reaches_main_deterministic']}, H2 route={f.loc['H2', 'run_a__network_aware__route_present']}")
        self.assertAlmostEqual(f.loc["1", "d_poly_any_m"], 30.0)
        self.assertTrue(f.loc["1", "run_a__network_aware__reaches_main_deterministic"])
        self.assertFalse(f.loc["H2", "run_a__network_aware__route_present"])
        self.assertEqual(f.loc["H2", "run_a__network_aware__chain_outcome_at_attach_tol"], "NO_ROUTE_IN_LAYER")

    def test_summary_denominators_and_roofs_separate(self):
        p = self.project()
        self.assertEqual(arc.main(cli(p)), 0)
        s = read_csv(p, "t1", "summary_by_group.csv")
        x = s[(s.summary_id == "candidates") & (s.group_type == "ALL") & (s.metric == "within_50m_polygon_any_road")].iloc[0]
        um = s[(s.summary_id == "candidates") & (s.group_type == "quality_class") & (s.group_value == "UNRESOLVED_MERGE") & (s.metric == "within_50m_polygon_any_road")].iloc[0]
        rec("summary", "ALL: 5 polygons, roofs 10; within 50 m = {1,4,5} -> 3/5 polygons, roofs 3/10; UNRESOLVED_MERGE reported separately 0/1 polygons, roofs 0/6",
            f"ALL {x['numerator']}/{x['denominator']} roofs {x['roofs_numerator']}/{x['roofs_denominator']}; UM {um['numerator']}/{um['denominator']} roofs {um['roofs_numerator']}/{um['roofs_denominator']}")
        self.assertEqual((x["numerator"], x["denominator"], x["roofs_numerator"], x["roofs_denominator"]), (3, 5, 3, 10))
        self.assertEqual((um["numerator"], um["denominator"], um["roofs_numerator"], um["roofs_denominator"]), (0, 1, 0, 6))

    def test_near_gaps_csv_rows_and_empty_header(self):
        p = self.project("g1", roads=[LineString([(0, 0), (100, 0)]), LineString([(103, 0), (200, 0)]), LineString([(0, 50), (100, 50)]), LineString([(0, 53), (100, 53)])])
        self.assertEqual(arc.main(cli(p)), 0)
        g = read_csv(p, "t1", "road_near_gaps.csv")
        sw = read_csv(p, "t1", "road_graph_tolerance_sweep.csv")
        h = sw[sw.policy == "assume_junction"].set_index("tolerance_m")
        valid = g[g.valid_bridge_at_max_tol]
        rec("near gaps csv", "collinear 3 m gap listed once (valid, within_5m True, within_2m False); the parallel pair is listed with direction_ok False; components 4 -> 3 at 5 m",
            f"valid rows={len(valid)} dist={valid['dist_m'].round(2).tolist()}; invalid rows={int((~g.direction_ok).sum())}; comps={h['n_components'].tolist()}")
        self.assertEqual(len(valid), 1)
        self.assertAlmostEqual(valid.iloc[0]["dist_m"], 3.0)
        self.assertTrue(valid.iloc[0]["within_5m"] and not valid.iloc[0]["within_2m"])
        self.assertGreaterEqual(int((~g.direction_ok).sum()), 2)
        self.assertEqual(h["n_components"].tolist(), [4, 4, 4, 3, 3, 3])
        self.assertEqual(read_csv(p, "t1", "checks.csv").set_index("check_id").loc["DICT_complete", "status"], "PASS")
        p2 = self.project("g2")
        self.assertEqual(arc.main(cli(p2)), 0)
        g2 = read_csv(p2, "t1", "road_near_gaps.csv")           # standard roads have no gap within 15 m: header only, never an unreadable empty file
        rec("near gaps empty", "header-only CSV, 0 rows", f"{len(g2)} rows, {len(g2.columns)} columns")
        self.assertEqual(len(g2), 0)
        self.assertIn("dist_m", g2.columns)

    def test_road_sweep_and_components_table(self):
        p = self.project()
        self.assertEqual(arc.main(cli(p)), 0)
        sw = read_csv(p, "t1", "road_graph_tolerance_sweep.csv")
        h = sw[sw.policy == "assume_junction"].set_index("tolerance_m")
        e = sw[sw.policy == "explicit_only"].set_index("tolerance_m")
        comps = read_csv(p, "t1", "road_components.csv")
        rec("sweep", "assume_junction: 3 components (main 1200 m = line + crossing, minor 100 m, far 100 m) at every tolerance <=15 (gap 100 m, separation 200 m+); explicit_only: 4",
            f"{h['n_components'].tolist()}; explicit {e['n_components'].tolist()}; main={h.loc[0.0, 'main_length_m']}")
        self.assertEqual(h["n_components"].tolist(), [3] * 6)
        self.assertEqual(e["n_components"].tolist(), [4] * 6)
        self.assertAlmostEqual(h.loc[0.0, "main_length_m"], 1200.0, places=1)
        self.assertEqual(int(comps["is_main"].sum()), 1)
        self.assertEqual(int(h.loc[0.0, "n_assumed_junction_crossings"]), 1)


def tearDownModule():
    print("\n" + "=" * 110 + "\nEXPECTED vs ACTUAL (recorded by each test)\n" + "=" * 110)
    for t, e, a in RECORD:
        print(f"- {t}\n    expected: {e}\n    actual:   {a}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
