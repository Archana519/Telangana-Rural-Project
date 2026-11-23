"""Pure-logic tests for scripts/run_adilabad_end_to_end.py (no network, no torch, no checkpoint)."""
import argparse
import importlib.util
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("e2e", REPO / "scripts" / "run_village_end_to_end.py")
E = importlib.util.module_from_spec(spec)
spec.loader.exec_module(E)


def test_tile_grid_matches_damarakunta_recipe():
    nx, ny, tiles = E.tile_grid((238648.4, 2175274.5, 242997.5, 2181028.7))          # Adilabad polygon bbox + 60 m
    assert (nx, ny, len(tiles)) == (3, 4, 12)
    n, x0, y0, x1, y1 = tiles[0]
    assert round((x1 - x0) / E.RES_M) == 3000 and round((y1 - y0) / E.RES_M) == 3000     # 1800 m at 0.6 m/px
    assert abs(round((tiles[2][3] - tiles[2][1]) / E.RES_M) - 1248) <= 1                          # edge tile keeps 0.6 m/px (not stretched)


def test_starts_cover_the_raster():
    for n in (560, 561, 1400, 7248):
        s = E.starts(n, 560, 420)
        assert s[0] == 0 and s[-1] == n - 560 and all(b - a <= 420 for a, b in zip(s, s[1:]))


def test_dummy_inference_stitches_a_synthetic_mosaic(tmp_path):
    rasterio = pytest.importorskip("rasterio")
    from rasterio.transform import from_origin
    H = W = 1400
    rgb = np.full((3, H, W), 100, np.uint8)
    rgb[1, 300:420, 300:420] = 250
    rgb[0, 300:420, 300:420] = 60
    rgb[2, 300:420, 300:420] = 60
    mos = tmp_path / "aligned" / "m.tif"
    mos.parent.mkdir()
    with rasterio.open(mos, "w", driver="GTiff", height=H, width=W, count=3, dtype="uint8", crs="EPSG:32644", transform=from_origin(0, H * 0.6, 0.6, 0.6), nodata=0) as d:
        d.write(rgb)
    a = argparse.Namespace(work_dir=str(tmp_path), checkpoint="", model_py="", device="cpu", batch=2, stride=420, margin=70, smoke=False, force=True, dummy_model=True)
    P = E.Paths(a)
    P.mosaic = mos
    E.stage_infer(a, P)
    with rasterio.open(P.pred / "pred_classes_full.tif") as s:
        cls = s.read(1)
    assert cls.shape == (H, W) and (cls[300:420, 300:420] == 2).all() and (cls[0:200, 0:200] == 7).all()


def test_esri_response_check_accepts_octet_stream_tiff():
    class R:
        def __init__(self, ct, body):
            self.headers, self.content = {"content-type": ct}, body
    assert E.is_tiff_or_image(R("application/octet-stream", b"II*\x00rest"))
    assert E.is_tiff_or_image(R("application/octet-stream", b"MM\x00*rest"))
    assert E.is_tiff_or_image(R("image/tiff", b"whatever"))
    assert not E.is_tiff_or_image(R("application/json", b'{"error":{"code":400}}'))
    assert not E.is_tiff_or_image(R("application/octet-stream", b"<html>"))
