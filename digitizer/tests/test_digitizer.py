"""Tests for the digitizer backend. Run:  python -m unittest discover -s tests -v
Uses a synthetic project in a temp folder; never touches real project data."""
import io
import json
import math
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

import fixture  # noqa: E402
from core import (Config, DigitizerError, Project, file_sha256, layer_digest,  # noqa: E402
                  list_gpkg_layers, map_to_px, px_to_map)
import geopandas as gpd  # noqa: E402


def _blob_centres(mask):
    """Centres (row, col means) of 4-connected blobs in a boolean mask. Pure numpy/python."""
    todo = {(int(r), int(c)) for r, c in zip(*np.nonzero(mask))}
    out = []
    while todo:
        stack = [todo.pop()]
        pts = []
        while stack:
            r, c = stack.pop()
            pts.append((r, c))
            for n in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
                if n in todo:
                    todo.remove(n)
                    stack.append(n)
        a = np.array(pts, float)
        out.append((a[:, 0].mean(), a[:, 1].mean()))
    return out


def make_project():
    tmp = Path(tempfile.mkdtemp(prefix="digitizer_test_"))
    fx = fixture.build(tmp)
    proj = Project(Config(fx["raster"], fx["gpkg"], fx["cands"], pad_m=15.0))
    return tmp, fx, proj


def rect_px(x0, y0, x1, y1):
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]


class CoordinateTests(unittest.TestCase):
    def setUp(self):
        self.tmp, self.fx, self.p = make_project()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_roundtrip_is_exact(self):
        tr, w, h = self.p.window_transform("W1_CORE")
        pts = [(0, 0), (12.5, 33.25), (w, h), (101.7, 5.1)]
        back = map_to_px(tr, px_to_map(tr, pts))
        for a, b in zip(pts, back):
            self.assertLess(math.hypot(a[0] - b[0], a[1] - b[1]), 1e-6)

    def test_marker_found_in_rendered_png_matches_known_map_coordinate(self):
        """Render the crop, find each red marker in the PNG, convert with the crop transform, and
        compare with the marker's true map coordinate (error must be < half a pixel = 0.3 m)."""
        for wid, markers in (("W1_CORE", fixture.MARKERS[:2]), ("W4_GAP", fixture.MARKERS[2:])):
            png = Image.open(io.BytesIO(self.p.render_png(wid))).convert("RGB")
            arr = np.asarray(png)
            tr, w, h = self.p.window_transform(wid)
            self.assertEqual((arr.shape[1], arr.shape[0]), (w, h))
            red = (arr[:, :, 0] == 255) & (arr[:, :, 1] == 0) & (arr[:, :, 2] == 0)
            found = [px_to_map(tr, [(cc + 0.5, rr + 0.5)])[0] for rr, cc in _blob_centres(red)]
            self.assertEqual(len(found), len(markers))
            for mx, my in markers:
                # (a) exact: the painted block's centre is the true point snapped to its pixel centre
                qx = fixture.X0 + (math.floor((mx - fixture.X0) / fixture.RES) + 0.5) * fixture.RES
                qy = fixture.Y0 - (math.floor((fixture.Y0 - my) / fixture.RES) + 0.5) * fixture.RES
                dq = min(math.hypot(qx - fx, qy - fy) for fx, fy in found)
                self.assertLess(dq, 1e-6, f"{wid} marker ({mx},{my}) conversion error {dq:.2e} m")
                # (b) and never more than half a pixel diagonal (0.424 m) from the true coordinate
                d = min(math.hypot(mx - fx, my - fy) for fx, fy in found)
                self.assertLess(d, 0.43)

    def test_drawn_pixel_polygon_lands_on_marker_in_map_coords(self):
        wid = "W1_CORE"
        tr, _, _ = self.p.window_transform(wid)
        mx, my = fixture.MARKERS[0]
        cx, cy = map_to_px(tr, [(mx, my)])[0]
        self.p.add_feature(wid, "roof", False, rect_px(cx - 6, cy - 6, cx + 6, cy + 6))
        feat = self.p.draft.data["features"][0]
        from shapely.geometry import Polygon, Point
        poly = Polygon(feat["coords"])
        self.assertTrue(poly.contains(Point(mx, my)))
        self.assertAlmostEqual(poly.area, (12 * 0.6) ** 2, places=3)
        self.assertEqual(self.p.draft.data["features"][0]["window_id"], wid)

    def test_invalid_and_tiny_polygons_rejected(self):
        with self.assertRaises(DigitizerError):
            self.p.add_feature("W1_CORE", "roof", False, [[0, 0], [10, 10], [10, 0], [0, 10]])  # bow-tie
        with self.assertRaises(DigitizerError):
            self.p.add_feature("W1_CORE", "roof", False, [[0, 0], [1, 0], [1, 1]])  # < 2 m2
        with self.assertRaises(DigitizerError):
            self.p.add_feature("W1_CORE", "roof", False, [[0, 0], [5, 5]])
        with self.assertRaises(DigitizerError):
            self.p.add_feature("NOPE", "roof", False, rect_px(0, 0, 9, 9))
        self.assertEqual(len(self.p.draft.data["features"]), 0)


class SafetyAndCommitTests(unittest.TestCase):
    def setUp(self):
        self.tmp, self.fx, self.p = make_project()
        self.raster_sha = file_sha256(self.fx["raster"])
        self.cand_sha = file_sha256(self.fx["cands"])
        self.win_digest = layer_digest(self.fx["gpkg"], "windows")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _trace(self, wid, n, kind="roof", unsure=False):
        for i in range(n):
            self.p.add_feature(wid, kind, unsure, rect_px(30 + 25 * i, 40, 45 + 25 * i, 55))

    def test_autosave_survives_restart(self):
        self._trace("W4_GAP", 2)
        p2 = Project(Config(self.fx["raster"], self.fx["gpkg"], self.fx["cands"]))  # "restart"
        self.assertEqual(len(p2.draft.data["features"]), 2)
        self.assertEqual(len(gpd.read_file(self.fx["gpkg"], layer="reference_buildings")), 0)  # gpkg untouched

    def test_commit_end_to_end(self):
        self._trace("W4_GAP", 2)
        self._trace("W4_GAP", 1, unsure=True)
        self._trace("W1_CORE", 2)
        with self.assertRaises(DigitizerError):          # CORE needs an extent first
            self.p.set_complete("W1_CORE", True)
        self.p.add_feature("W1_CORE", "extent", False, rect_px(10, 10, 120, 120))
        self.p.set_complete("W1_CORE", True)
        self.p.set_complete("W4_GAP", True)
        self.p.set_complete("W6_FARMNEG", True)          # legitimately zero roofs
        pv = self.p.commit_preview()
        self.assertEqual(pv["errors"], [])
        self.assertEqual(pv["new_total"], 6)
        with self.assertRaises(DigitizerError):
            self.p.commit("yes")
        r = self.p.commit("COMMIT")
        self.assertTrue(r["windows_layer_unchanged"])
        self.assertTrue(Path(r["backup"]).exists())
        self.assertTrue((self.fx["ref_dir"] / "digitizer_backups" / "digitize_windows.ORIGINAL_before_digitizer.gpkg").exists())
        self.assertEqual(set(list_gpkg_layers(self.fx["gpkg"])), {"windows", "reference_buildings"})
        ref = gpd.read_file(self.fx["gpkg"], layer="reference_buildings")
        self.assertEqual(len(ref), 6)
        self.assertEqual(ref.crs.to_epsg(), 32644)
        self.assertTrue({"window_id", "note", "geometry"} <= set(ref.columns))
        self.assertEqual(sorted(ref["note"].fillna("").unique().tolist()), ["", "TRACED_EXTENT", "unsure"])
        self.assertEqual((ref["note"] == "TRACED_EXTENT").sum(), 1)
        self.assertEqual(layer_digest(self.fx["gpkg"], "windows"), self.win_digest)
        st = json.load(open(self.fx["ref_dir"] / "window_status.json"))
        self.assertEqual(st["complete_windows"], ["W1_CORE", "W4_GAP", "W6_FARMNEG"])
        # draft is now empty and a second commit is a no-op (no duplicates)
        self.assertEqual(len(self.p.draft.data["features"]), 0)
        r2 = self.p.commit("COMMIT")
        self.assertEqual(r2["committed_new"], 0)
        self.assertEqual(len(gpd.read_file(self.fx["gpkg"], layer="reference_buildings")), 6)
        # untouched inputs
        self.assertEqual(file_sha256(self.fx["raster"]), self.raster_sha)
        self.assertEqual(file_sha256(self.fx["cands"]), self.cand_sha)

    def test_existing_polygons_preserved_and_deletion_needs_confirmation(self):
        self._trace("W4_GAP", 2)
        self.p.commit("COMMIT")
        before = gpd.read_file(self.fx["gpkg"], layer="reference_buildings")
        old_geoms = {r["uid"]: r.geometry.wkb for _, r in before.iterrows()}
        self._trace("W1_CORE", 1)
        self.p.commit("COMMIT")
        after = gpd.read_file(self.fx["gpkg"], layer="reference_buildings")
        self.assertEqual(len(after), 3)
        for _, r in after.iterrows():
            if r["uid"] in old_geoms:
                self.assertEqual(r.geometry.wkb, old_geoms[r["uid"]])   # byte-identical geometry
        victim = list(old_geoms)[0]
        with self.assertRaises(DigitizerError):
            self.p.delete_feature(victim)                                # refused without confirmation
        self.assertEqual(len(gpd.read_file(self.fx["gpkg"], layer="reference_buildings")), 3)
        self.p.delete_feature(victim, confirm_committed=True)
        self.assertEqual(len(gpd.read_file(self.fx["gpkg"], layer="reference_buildings")), 3)  # still there until commit
        self.p.commit("COMMIT")
        self.assertEqual(len(gpd.read_file(self.fx["gpkg"], layer="reference_buildings")), 2)

    def test_commit_removing_everything_keeps_layer_valid(self):
        self._trace("W4_GAP", 1)
        self.p.commit("COMMIT")
        uid = gpd.read_file(self.fx["gpkg"], layer="reference_buildings").iloc[0]
        self.p.delete_feature(self.p.read_reference().iloc[0]["uid"], confirm_committed=True)
        self.p.commit("COMMIT")
        self.assertEqual(set(list_gpkg_layers(self.fx["gpkg"])), {"windows", "reference_buildings"})
        self.assertEqual(len(gpd.read_file(self.fx["gpkg"], layer="reference_buildings")), 0)

    def test_legacy_polygons_traced_elsewhere_are_kept(self):
        from shapely.geometry import box
        legacy = gpd.GeoDataFrame({"window_id": ["W4_GAP"], "note": [""]}, geometry=[box(261410, 1959110, 261420, 1959120)], crs="EPSG:32644")
        legacy.to_file(self.fx["gpkg"], layer="reference_buildings", driver="GPKG")  # as if traced in QGIS
        self.assertEqual(set(list_gpkg_layers(self.fx["gpkg"])), {"windows", "reference_buildings"})
        p = Project(Config(self.fx["raster"], self.fx["gpkg"], self.fx["cands"]))
        p.add_feature("W4_GAP", "roof", False, rect_px(30, 40, 45, 55))
        p.commit("COMMIT")
        ref = gpd.read_file(self.fx["gpkg"], layer="reference_buildings")
        self.assertEqual(len(ref), 2)
        self.assertTrue(any(ref.geometry.apply(lambda g: g.equals_exact(box(261410, 1959110, 261420, 1959120), 1e-9))))

    def test_blocked_commit_leaves_everything_intact(self):
        self._trace("W1_CORE", 1)
        self.p.draft.data["complete"]["W1_CORE"] = True      # bypass UI guard on purpose
        gp_sha = file_sha256(self.fx["gpkg"])
        with self.assertRaises(DigitizerError):
            self.p.commit("COMMIT")
        self.assertEqual(file_sha256(self.fx["gpkg"]), gp_sha)
        self.assertEqual(len(self.p.draft.data["features"]), 1)

    def test_whole_window_extent(self):
        self._trace("W1_CORE", 1)
        self.p.add_extent_whole_window("W1_CORE")
        self.p.set_complete("W1_CORE", True)
        self.p.commit("COMMIT")
        ref = gpd.read_file(self.fx["gpkg"], layer="reference_buildings")
        ext = ref[ref["note"] == "TRACED_EXTENT"].iloc[0].geometry
        self.assertAlmostEqual(ext.area, 200 * 200, places=3)

    def test_payload_overlays_use_same_transform(self):
        pl = self.p.window_payload("W1_CORE")
        self.assertEqual(len(pl["candidates"]), 2)         # two candidates fall in W1_CORE
        tr = pl["transform"]
        ring = pl["candidates"][0]["rings"][0]
        x, y = ring[0]
        mx, my = tr[0] * x + tr[1] * y + tr[2], tr[3] * x + tr[4] * y + tr[5]
        cand = gpd.read_file(self.fx["cands"])
        d = min(math.hypot(mx - px, my - py) for g in cand.geometry for px, py in g.exterior.coords)
        self.assertLess(d, 1e-6)


if __name__ == "__main__":
    unittest.main(verbosity=2)
