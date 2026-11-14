"""DEM consistency check (U08 follow-up): Stage B used SRTM 1 arc-second; Levels 2-4 use Copernicus GLO-30.

Compares the two DEMs over the Damarakunta window (elevation, Sobel slope, hard-block mask) and re-runs Level 2 with each DEM to show how much the
headline numbers move. SRTM is fetched from the public AWS 'skadi' tiles (SRTM v3-derived), NOT from the USGS EarthExplorer file Stage B used
(`n17_e078_1arc_v3.tif`, not in the repository), so this is a proxy comparison of the two products, not a re-run of Stage B.

    python -m src.evaluation.dem_consistency --out docs/results/U08_dem_comparison.json
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
import tempfile
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import rasterio  # noqa: E402

from src.routing import data_hooks as dh  # noqa: E402
from src.routing.hierarchical_router import build_gp_problem, load_config  # noqa: E402
from src.routing.layers import RasterLayerProvider, slope_sobel  # noqa: E402
from src.utils import data_downloader_helper as dl  # noqa: E402


def _stats(a):
    a = a[np.isfinite(a)]
    return dict(n=int(a.size), mean=float(a.mean()), p95=float(np.percentile(a, 95)), max=float(a.max()),
                pct_gt10=float(100 * (a > 10).mean()), pct_gt25=float(100 * (a > 25).mean()))


def compare(cop_path: Path, srtm_path: Path) -> dict:
    with rasterio.open(cop_path) as c, rasterio.open(srtm_path) as s:
        assert c.transform == s.transform and c.shape == s.shape, "DEMs must share a grid"
        a, b = c.read(1).astype("float64"), s.read(1).astype("float64")
        res = abs(c.transform.a)
    a[a == -9999.0] = np.nan
    b[b == -9999.0] = np.nan
    ok = np.isfinite(a) & np.isfinite(b)
    d = a[ok] - b[ok]
    sa, sb = slope_sobel(a, res), slope_sobel(b, res)
    oks = np.isfinite(sa) & np.isfinite(sb)
    ds = sa[oks] - sb[oks]
    return dict(
        grid=dict(res_m=res, shape=list(a.shape), common_valid_cells=int(ok.sum())),
        elevation_m=dict(bias_cop_minus_srtm=float(d.mean()), mae=float(np.abs(d).mean()), rmse=float(np.sqrt((d ** 2).mean())),
                         p95_abs=float(np.percentile(np.abs(d), 95)), pearson_r=float(np.corrcoef(a[ok], b[ok])[0, 1]),
                         cop_range=[float(np.nanmin(a)), float(np.nanmax(a))], srtm_range=[float(np.nanmin(b)), float(np.nanmax(b))]),
        slope_deg=dict(copernicus=_stats(sa), srtm=_stats(sb), diff_mean=float(ds.mean()), diff_rmse=float(np.sqrt((ds ** 2).mean())),
                       pearson_r=float(np.corrcoef(sa[oks], sb[oks])[0, 1]),
                       hard_block_gt25_disagree_cells=int(((sa[oks] > 25) != (sb[oks] > 25)).sum())))


def level2_with_dem(cfg, dem_path: Path) -> dict:
    gp, _ = dh.load_gp_real(cfg)
    lc = str(REPO / cfg["data"]["gp"]["landcover"])
    gp.provider = RasterLayerProvider(lc, str(dem_path))
    prob = build_gp_problem(gp, cfg)
    sh, ind = prob.solve(mode="shared"), prob.solve(mode="independent")
    ov = prob.solve(use_override=False)
    return dict(shared_unique_length_m=sh.unique_length_m, independent_unique_length_m=ind.unique_length_m,
                shared_unique_cost=sh.unique_cost, routed=len(sh.routes), failed=len(sh.failures),
                detour_reduction_m=ov.unique_length_m - sh.unique_length_m)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(REPO / "docs" / "results" / "U08_dem_comparison.json"))
    a = ap.parse_args(argv)
    cfg = load_config()
    cop = REPO / cfg["data"]["gp"]["dem"]
    with rasterio.open(cop) as s:
        bounds, crs = tuple(s.bounds), str(s.crs)
    with tempfile.TemporaryDirectory() as td:
        srtm = Path(td) / "srtm.tif"
        tiles = dl.dem_tiles(tuple(__import__("geopandas").GeoSeries([__import__("shapely.geometry", fromlist=["box"]).box(*bounds)], crs=crs).to_crs(4326).total_bounds))
        urls = [dl.SRTM_URL.format(ns="N" if la >= 0 else "S", lat=abs(la), ew="E" if lo >= 0 else "W", lon=abs(lo)) for la, lo in tiles]
        dl.warp_to_grid(urls, bounds, crs, 30.0, srtm, "bilinear", "float32", -9999.0, gz=True)
        out = dict(note="SRTM via AWS skadi tiles (proxy for the USGS file used by Stage B); Copernicus GLO-30 via AWS COG", srtm_urls=urls,
                   comparison=compare(cop, srtm),
                   level2_copernicus=level2_with_dem(cfg, cop), level2_srtm=level2_with_dem(cfg, srtm))
    c, s = out["level2_copernicus"], out["level2_srtm"]
    out["level2_relative_difference_pct"] = {k: (100 * (c[k] - s[k]) / s[k] if s[k] else 0.0)
                                             for k in ("shared_unique_length_m", "independent_unique_length_m", "shared_unique_cost", "detour_reduction_m")}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("comparison", "level2_copernicus", "level2_srtm", "level2_relative_difference_pct")}, indent=2))


if __name__ == "__main__":
    main()
