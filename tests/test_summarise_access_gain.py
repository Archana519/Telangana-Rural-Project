"""Tests for summarise_access_gain.py on SYNTHETIC fixtures only (no project data is read or written).
Run:  python tests\\test_summarise_access_gain.py     (from the project root; also works from the scripts folder)
"""
import hashlib, importlib.util, json, os, shutil, sys, tempfile, unittest
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString, Point, box

HERE = Path(__file__).resolve().parent
for cand_dir in (HERE, HERE.parent / "scripts", HERE / "scripts"):
    if (cand_dir / "summarise_access_gain.py").exists():
        SPEC = importlib.util.spec_from_file_location("sag", cand_dir / "summarise_access_gain.py")
        break
else:
    raise SystemExit("summarise_access_gain.py not found next to the test or in ..\\scripts")
sag = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sag)

CRS = "EPSG:32644"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def build_fixture(root, attach_label="ROAD", extra_unserved=True):
    root = Path(root)
    (root / "data").mkdir(parents=True)
    roads = gpd.GeoDataFrame({"RD_TYPE": ["x"]}, geometry=[LineString([(0, 0), (1000, 0)])], crs=CRS)
    roads.to_file(root / "data" / "roads.gpkg", driver="GPKG")
    (root / "data" / "cost.tif").write_bytes(b"synthetic-cost-raster")
    polys = [  # cand_id, cluster, box, quality
        (1, 1, box(300, 100, 310, 110), "PLAUSIBLE"), (2, 1, box(300, 112, 310, 122), "UNRESOLVED_MERGE"),
        (3, 2, box(600, 20, 610, 30), "PLAUSIBLE"), (4, 2, box(600, 40, 610, 50), "REVIEW"),
        (5, 2, box(600, 70, 610, 80), "PLAUSIBLE"), (6, 2, box(600, 85, 610, 95), "UNRESOLVED_MERGE"),
        (7, 3, box(800, 10, 810, 20), "PLAUSIBLE")]
    cand = gpd.GeoDataFrame({"cand_id": [p[0] for p in polys], "cluster_id": [p[1] for p in polys], "quality_class": [p[3] for p in polys]},
                            geometry=[p[2] for p in polys], crs=CRS)
    cand["dist_to_ref_road_m"] = cand.geometry.distance(roads.geometry.iloc[0]).round(2)
    cand["gap_flag"] = cand["dist_to_ref_road_m"] > 50
    mind = cand.groupby("cluster_id")["dist_to_ref_road_m"].min()
    kinds = {1: "ISOLATED_OR_SMALL_GROUP", 2: "SETTLEMENT_CLUSTER", 3: "ISOLATED_OR_SMALL_GROUP"}
    cl = gpd.GeoDataFrame({"cluster_id": [1, 2, 3], "n_candidates": [2, 4, 1], "min_dist_to_ref_road_m": [mind[1], mind[2], mind[3]],
                           "kind": [kinds[1], kinds[2], kinds[3]], "gap_flag": [mind[1] > 50, mind[2] > 50, mind[3] > 50]},
                          geometry=[box(290, 95, 320, 125), box(590, 15, 620, 100), box(790, 5, 820, 25)], crs=CRS)
    fac = gpd.GeoDataFrame({"facility_id": ["1", "H2"], "facility_name": ["School A", "Sub Centre B"], "facility_type": ["School", "Healthcare"],
                            "dist_to_ref_road_m": [30.0, 120.0]}, geometry=[Point(200, 30), Point(500, 120)], crs=CRS)
    access = root / "data" / "access_assessment.gpkg"
    cand.to_file(access, layer="candidate_access", driver="GPKG")
    cl.to_file(access, layer="clusters", driver="GPKG")
    fac.to_file(access, layer="facility_access", driver="GPKG")

    runs_root = root / "network_v2"
    for rn, extra in (("run_a", False), ("run_b", True)):
        rd = runs_root / rn
        rd.mkdir(parents=True)
        tg = [("F:1", "FACILITY", 3.0, Point(200, 30)), ("F:H2", "FACILITY", 4.0, Point(500, 120)), ("C1", "CLUSTER", 1.25, Point(305, 105))]
        routes = {"F:1": LineString([(200, 30), (200, 0)]), "F:H2": LineString([(500, 120), (500, 0)]), "C1": LineString([(305, 105), (305, 0)])}
        if extra:
            tg.append(("C9", "CLUSTER", 1.0, Point(805, 15)))
            routes["C9"] = LineString([(805, 15), (805, 0)])
        if extra_unserved:
            tg.append(("C13", "CLUSTER", 1.0, Point(900, 500)))
        tgt = gpd.GeoDataFrame({"id": [t[0] for t in tg], "kind": [t[1] for t in tg], "weight": [t[2] for t in tg]}, geometry=[t[3] for t in tg], crs=CRS)
        rows = [dict(target=k, mode="stageA_alt1", length_m=round(g.length, 1), cost=round(g.length * 6.0, 1), attach_to=attach_label if k == "F:1" else "",
                     route_status="UNVERIFIED_PLANNING_ALTERNATIVE_NOT_A_ROAD", geometry=g) for k, g in routes.items()]
        ra = gpd.GeoDataFrame([dict(r, endpoint_dist_m=0.0, connected=True) for r in rows], crs=CRS)
        ri = gpd.GeoDataFrame([dict(r) for r in rows], crs=CRS)
        gp = rd / "network_v2.gpkg"
        tgt.to_file(gp, layer="targets", driver="GPKG")
        ra.to_file(gp, layer="routes_network_aware", driver="GPKG")
        ri.to_file(gp, layer="routes_independent", driver="GPKG")
        tot = round(sum(r["length_m"] for r in rows), 1)
        cst = round(sum(r["cost"] for r in rows), 1)
        served_w = sum(t[2] for t in tg if t[0] in routes)
        trows = []
        for t in tg:
            ok = t[0] in routes
            trows.append(dict(target=t[0], kind=t[1], name="n", weight=t[2], status="SERVED" if ok else "FAILED",
                              failure_reason="" if ok else "TARGET_IN_HARD_CONSTRAINT_CELL_OR_OUTSIDE_GRID", euclid_to_road_m=1.0,
                              route_len_m=[r["length_m"] for r in rows if r["target"] == t[0]][0] if ok else None,
                              route_cost=[r["cost"] for r in rows if r["target"] == t[0]][0] if ok else None))
        pd.DataFrame(trows).to_csv(rd / "target_table.csv", index=False)
        pc = [dict(plan=p, targets_routed=len(rows), targets_total=len(tg), total_len_m=tot, unique_len_m=tot, shared_len_m=0.0, unique_cost=cst,
                   weighted_benefit=served_w, facilities_served=2, cluster_buildings_served=1, infeasible_routes=0) for p in ("network_aware", "independent_least_cost")]
        pd.DataFrame(pc).to_csv(rd / "plan_comparison.csv", index=False)
        summ = dict(params=dict(access_gpkg=str(access), roads=str(root / "data" / "roads.gpkg"), cost=str(root / "data" / "cost.tif"), attach_tol_m=15.0,
                                worldcover=None, tag=rn),
                    constraints_resolved=dict(prohibited_raster=None, slope_raster=None, slope_limit_deg=None),
                    inputs=dict(access=sha(access), roads=sha(root / "data" / "roads.gpkg"), cost=sha(root / "data" / "cost.tif")))
        (rd / "summary.json").write_text(json.dumps(summ), encoding="utf-8")
    return root, runs_root


def run_script(root, runs_root, tag, extra=None):
    argv = ["--runs-root", str(runs_root), "--runs", "run_a", "run_b", "--out-root", str(root / "out"), "--tag", tag]
    return sag.main(argv + (extra or []))


class T(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.root, self.runs_root = build_fixture(self.tmp / "fx")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def snapshot(self):
        return {str(p): sha(p) for p in (self.root / "data").rglob("*") if p.is_file()} | {str(p): sha(p) for p in self.runs_root.rglob("*") if p.is_file()}

    def test_runs_clean_and_reads_only(self):
        before = self.snapshot()
        rc = run_script(self.root, self.runs_root, "t1")
        self.assertEqual(rc, 0)
        self.assertEqual(before, self.snapshot(), "inputs or run folders changed")
        out = self.root / "out" / "t1"
        for f in ("access_gain_summary.csv", "facility_access_gain.csv", "route_length_cost.csv", "unserved_targets.csv", "gap_flag_composition.csv",
                  "checks.csv", "buildings_access.gpkg", "access_gain_report.txt", "access_gain_summary.json"):
            self.assertTrue((out / f).exists(), f)
        js = json.loads((out / "access_gain_summary.json").read_text())
        self.assertIs(js["monetary_cost_estimated"], False)
        self.assertFalse(js["any_check_failed"])
        ch = pd.read_csv(out / "checks.csv")
        self.assertFalse((ch.status == "FAIL").any(), ch[ch.status == "FAIL"].to_string())

    def test_set_sizes_and_coverage_match_independent_geometry(self):
        run_script(self.root, self.runs_root, "t2")
        s = pd.read_csv(self.root / "out" / "t2" / "access_gain_summary.csv")
        n = lambda name: int(s[(s.building_set == name)].n_polygons.iloc[0])
        self.assertEqual((n("all_candidate_polygons"), n("polygon_gap_flag_true"), n("gap_cluster_polygons"), n("settlement_cluster_polygons"),
                          n("settlement_interior_screening"), n("non_target_polygons"), n("nongap_isolated_cluster_polygons")), (7, 4, 2, 4, 2, 5, 1))
        row = lambda sn, T: s[(s.run == "run_a") & (s.scenario == "roads_plus_network_aware_routes") & (s.building_set == sn) & (s.threshold_m == T)].iloc[0]
        for T in (25.0, 50.0):
            self.assertEqual(int(row("gap_cluster_polygons", T).baseline_n_within), 0)       # 0 by definition at/below gap_m
        self.assertEqual(int(row("gap_cluster_polygons", 50.0).proposed_n_within), 2)         # both polygons within 50 m of the C1 route
        self.assertEqual(int(row("polygon_gap_flag_true", 50.0).baseline_n_within), 0)
        self.assertEqual(int(row("polygon_gap_flag_true", 50.0).proposed_n_within), 2)        # only the 2 polygons beside the route
        self.assertAlmostEqual(float(row("gap_cluster_polygons", 50.0).pp_change), 100.0)
        self.assertEqual(int(row("polygon_gap_flag_true", 50.0).n_polygons), 4)

    def test_facilities_separate_and_route_cost_rows(self):
        run_script(self.root, self.runs_root, "t3")
        f = pd.read_csv(self.root / "out" / "t3" / "facility_access_gain.csv", dtype={"facility_id": str})
        self.assertEqual(sorted(f.facility_id.unique()), ["1", "H2"])
        h = f[(f.run == "run_a") & (f.facility_id == "H2")].iloc[0]
        self.assertAlmostEqual(float(h.dist_base_m), 120.0, places=2)
        self.assertAlmostEqual(float(h.dist_na_m), 0.0, places=2)
        self.assertEqual(h.planner_status, "SERVED")
        r = pd.read_csv(self.root / "out" / "t3" / "route_length_cost.csv")
        self.assertTrue((r.monetary_cost_estimated == False).all())
        self.assertIn("NOT money", r.cost_unit_label.iloc[0])
        u = pd.read_csv(self.root / "out" / "t3" / "unserved_targets.csv")
        self.assertEqual(set(u.target), {"C13"})
        self.assertEqual(int(r[(r.run == "run_b")].routes_used.iloc[0]), 4)
        self.assertEqual(int(r[(r.run == "run_a")].routes_used.iloc[0]), 3)

    def test_refuses_nonempty_output(self):
        (self.root / "out" / "t4").mkdir(parents=True)
        (self.root / "out" / "t4" / "x.txt").write_text("keep")
        with self.assertRaises(SystemExit):
            run_script(self.root, self.runs_root, "t4")
        self.assertEqual((self.root / "out" / "t4" / "x.txt").read_text(), "keep")

    def test_deterministic_outputs(self):
        run_script(self.root, self.runs_root, "d1")
        run_script(self.root, self.runs_root, "d2")
        for f in ("access_gain_summary.csv", "facility_access_gain.csv", "route_length_cost.csv", "unserved_targets.csv", "gap_flag_composition.csv", "checks.csv", "access_gain_report.txt"):
            self.assertEqual((self.root / "out" / "d1" / f).read_bytes(), (self.root / "out" / "d2" / f).read_bytes(), f)

    def test_attach_to_label_is_not_used(self):
        run_script(self.root, self.runs_root, "l1")
        root2, rr2 = build_fixture(self.tmp / "fx2", attach_label="C1")
        sag.main(["--runs-root", str(rr2), "--runs", "run_a", "run_b", "--out-root", str(root2 / "out"), "--tag", "l2"])
        a = pd.read_csv(self.root / "out" / "l1" / "access_gain_summary.csv")
        b = pd.read_csv(root2 / "out" / "l2" / "access_gain_summary.csv")
        pd.testing.assert_frame_equal(a, b)

    def test_hash_mismatch_is_reported(self):
        p = self.runs_root / "run_a" / "summary.json"
        d = json.loads(p.read_text()); d["inputs"]["roads"] = "0" * 64; p.write_text(json.dumps(d))
        rc = run_script(self.root, self.runs_root, "h1")
        self.assertEqual(rc, 1)
        ch = pd.read_csv(self.root / "out" / "h1" / "checks.csv")
        self.assertTrue(((ch.check_id == "HASH_run_a_roads") & (ch.status == "FAIL")).any())

    def test_input_change_during_run_fails(self):
        real = sag.file_state
        out_gpkg = self.root / "out" / "c1" / "buildings_access.gpkg"

        def tamper(p):
            st = real(p)
            if out_gpkg.exists() and str(p).endswith("roads.gpkg"):
                st = dict(st, sha256="deadbeef")
            return st
        sag.file_state = tamper
        try:
            rc = run_script(self.root, self.runs_root, "c1")
        finally:
            sag.file_state = real
        self.assertEqual(rc, 2)
        self.assertTrue((self.root / "out" / "c1" / "INPUT_CHANGED_REPORT_INVALID.txt").exists())

    def test_missing_required_column_aborts_before_writing(self):
        access = self.root / "data" / "access_assessment.gpkg"
        c = gpd.read_file(access, layer="candidate_access").drop(columns=["gap_flag"])
        c.to_file(access, layer="candidate_access", driver="GPKG")
        with self.assertRaises(SystemExit):
            run_script(self.root, self.runs_root, "m1")
        self.assertFalse((self.root / "out" / "m1").exists())

    def test_verify_unchanged(self):
        a = {"p": dict(exists=True, size=1, sha256="a", mtime_ns=1)}
        self.assertEqual(sag.verify_unchanged(a, {"p": dict(exists=True, size=1, sha256="b", mtime_ns=1)}), [("p", "content")])
        self.assertEqual(sag.verify_unchanged(a, dict(a)), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
