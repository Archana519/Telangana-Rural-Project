"""Tests against YOUR REAL files. Run on the Windows laptop after copying the tool to
D:\\Telangana_Rural_Project\\digitizer :

    cd /d D:\\Telangana_Rural_Project\\digitizer
    python -m unittest discover -s tests -p "test_real_data.py" -v

Safety: the raster and the candidate layer are only read. Everything that writes (commit, backup, draft)
happens on a COPY of digitize_windows.gpkg in a temporary folder that is deleted afterwards. The real
GeoPackage's SHA-256 is compared before/after to prove it was not touched.
Override locations with env vars DIGITIZER_RASTER / DIGITIZER_GPKG / DIGITIZER_CANDIDATES.
"""
import math
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import numpy as np  # noqa: E402
import rasterio  # noqa: E402
from PIL import Image  # noqa: E402
import io  # noqa: E402
import geopandas as gpd  # noqa: E402

from core import (Config, DEFAULT_CANDIDATES, DEFAULT_GPKG, DEFAULT_RASTER, Project,  # noqa: E402
                  file_sha256, layer_digest, list_gpkg_layers, map_to_px, px_to_map)

RASTER = Path(os.environ.get("DIGITIZER_RASTER", DEFAULT_RASTER))
GPKG = Path(os.environ.get("DIGITIZER_GPKG", DEFAULT_GPKG))
CANDS = Path(os.environ.get("DIGITIZER_CANDIDATES", DEFAULT_CANDIDATES))


@unittest.skipUnless(RASTER.exists() and GPKG.exists(), f"real files not found: {RASTER} / {GPKG}")
class RealDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gpkg_sha = file_sha256(GPKG)
        cls.raster_stat = (RASTER.stat().st_size, RASTER.stat().st_mtime_ns)
        cls.cand_sha = file_sha256(CANDS) if CANDS.exists() else None
        cls.tmp = Path(tempfile.mkdtemp(prefix="digitizer_real_"))
        (cls.tmp / "reference").mkdir()
        cls.gpkg_copy = cls.tmp / "reference" / GPKG.name
        shutil.copy2(GPKG, cls.gpkg_copy)                      # all writes go to this copy
        cls.p = Project(Config(RASTER, cls.gpkg_copy, CANDS if CANDS.exists() else None))
        cls.window_ids = [w["window_id"] for w in cls.p.state()["windows"]]

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    # ---- the real files look as the project says they do
    def test_raster_matches_project_facts(self):
        with rasterio.open(RASTER) as src:
            self.assertEqual(src.crs.to_epsg(), 32644)
            self.assertAlmostEqual(src.res[0], 0.6, delta=0.01)
            self.assertAlmostEqual(src.res[1], 0.6, delta=0.01)
            self.assertEqual((src.width, src.height), (11296, 7171))
            self.assertGreaterEqual(src.count, 3)
            self.assertEqual((src.transform.b, src.transform.d), (0, 0))

    def test_geopackage_schema(self):
        self.assertEqual(set(list_gpkg_layers(GPKG)) >= {"windows", "reference_buildings"}, True)
        w = gpd.read_file(GPKG, layer="windows")
        self.assertEqual(w.crs.to_epsg(), 32644)
        self.assertIn("window_id", w.columns)
        self.assertGreaterEqual(len(w), 1)
        r = gpd.read_file(GPKG, layer="reference_buildings")
        self.assertEqual(r.crs.to_epsg(), 32644)
        self.assertTrue({"window_id", "note"} <= set(r.columns))
        print(f"\n  windows: {list(w['window_id'])} | reference rows already present: {len(r)}")

    # ---- coordinate conversion on the real raster, independent of the tool's own transform
    def test_png_pixels_equal_raster_pixels_at_same_map_coordinate(self):
        """For sample map points in every real window: read the raster directly at that coordinate
        (rasterio's own index lookup) and compare with the PNG pixel the tool maps that coordinate to."""
        for wid in self.window_ids:
            png = np.asarray(Image.open(io.BytesIO(self.p.render_png(wid))).convert("RGB"))
            tr, w, h = self.p.window_transform(wid)
            self.assertEqual(png.shape[:2], (h, w))
            row = self.p._window(wid)
            minx, miny, maxx, maxy = row.geometry.bounds
            rng = np.random.default_rng(1)
            checked = 0
            with rasterio.open(RASTER) as src:
                for _ in range(60):
                    x, y = rng.uniform(minx, maxx), rng.uniform(miny, maxy)
                    r_, c_ = src.index(x, y)
                    if not (0 <= r_ < src.height and 0 <= c_ < src.width):
                        continue
                    direct = src.read([1, 2, 3], window=((r_, r_ + 1), (c_, c_ + 1)))[:, 0, 0]
                    px, py = map_to_px(tr, [(x, y)])[0]
                    shown = png[int(math.floor(py)), int(math.floor(px))]
                    self.assertEqual(list(direct), list(shown), f"{wid}: pixel mismatch at ({x:.2f},{y:.2f})")
                    checked += 1
            self.assertGreater(checked, 20, f"{wid}: too few valid sample points")

    def test_roundtrip_and_candidate_overlay_on_real_windows(self):
        for wid in self.window_ids:
            tr, w, h = self.p.window_transform(wid)
            pts = [(0, 0), (w / 3, h / 7), (w, h)]
            back = map_to_px(tr, px_to_map(tr, pts))
            for a, b in zip(pts, back):
                self.assertLess(math.hypot(a[0] - b[0], a[1] - b[1]), 1e-6)
            if CANDS.exists():
                pl = self.p.window_payload(wid)
                t = pl["transform"]
                for c in pl["candidates"][:25]:
                    for x, y in c["rings"][0]:
                        mx, my = t[0] * x + t[1] * y + t[2], t[3] * x + t[4] * y + t[5]
                        self.assertTrue(math.isfinite(mx) and math.isfinite(my))
                print(f"  {wid}: crop {w}x{h}px, {len(pl['candidates'])} candidate polygons in view")

    def test_window_boundary_maps_inside_crop(self):
        for wid in self.window_ids:
            pl = self.p.window_payload(wid)
            xs = [p[0] for ring in pl["window_px"] for p in ring]
            ys = [p[1] for ring in pl["window_px"] for p in ring]
            self.assertGreaterEqual(min(xs), 0)
            self.assertGreaterEqual(min(ys), 0)
            self.assertLessEqual(max(xs), pl["width"])
            self.assertLessEqual(max(ys), pl["height"])
            # a 200 m window at ~0.6 m/px is ~333 px wide
            self.assertAlmostEqual((max(xs) - min(xs)) * abs(pl["transform"][0]), 200, delta=2.0)

    # ---- write path, exercised on a COPY of the real GeoPackage
    def test_commit_on_copy_preserves_real_windows_layer(self):
        wid = self.window_ids[0]
        tr, w, h = self.p.window_transform(wid)
        before_layers = set(list_gpkg_layers(self.gpkg_copy))
        win_digest = layer_digest(self.gpkg_copy, "windows")
        n_before = len(gpd.read_file(self.gpkg_copy, layer="reference_buildings"))
        cx, cy = w / 2, h / 2
        self.p.add_feature(wid, "roof", True, [[cx - 8, cy - 8], [cx + 8, cy - 8], [cx + 8, cy + 8], [cx - 8, cy + 8]])
        res = self.p.commit("COMMIT")
        self.assertTrue(res["windows_layer_unchanged"])
        self.assertEqual(set(list_gpkg_layers(self.gpkg_copy)), before_layers)
        self.assertEqual(layer_digest(self.gpkg_copy, "windows"), win_digest)
        after = gpd.read_file(self.gpkg_copy, layer="reference_buildings")
        self.assertEqual(len(after), n_before + 1)
        self.assertEqual(after.crs.to_epsg(), 32644)
        self.assertTrue(Path(res["backup"]).exists())

    # ---- nothing real was modified (runs last: name sorts after the others)
    def test_zz_real_files_untouched(self):
        self.assertEqual(file_sha256(GPKG), self.gpkg_sha, "REAL GeoPackage changed!")
        self.assertEqual((RASTER.stat().st_size, RASTER.stat().st_mtime_ns), self.raster_stat, "REAL raster changed!")
        if self.cand_sha:
            self.assertEqual(file_sha256(CANDS), self.cand_sha, "REAL candidate layer changed!")


if __name__ == "__main__":
    unittest.main(verbosity=2)
