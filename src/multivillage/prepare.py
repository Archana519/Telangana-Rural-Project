"""Step 2 of the shared pipeline: land cover, DEM and slope on the 10 m planning grid (Stage B method), plus the 10 m cost surface (step 4).

Land cover: ESA WorldCover v200 (2021) windows. Terrain: Copernicus GLO-30 DEM windows; slope = Sobel on the 30 m DEM (Stage B method),
bilinearly resampled to 10 m. Cells outside the village polygon are blocked (the polygon clips the planning domain, as for Damarakunta).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio
from rasterio.features import rasterize
from rasterio.transform import from_origin
from shapely.geometry import box

from src.routing.layers import Layers, cost_from_layers, slope_sobel
from src.utils import data_downloader_helper as dl
from src.multivillage.sources import Source

CRS = "EPSG:32644"


def grid_for_cell(cell, res: float):
    minx, miny, maxx, maxy = dl.aligned_bounds(cell.bounds, res, 0.0)
    W, H = int(round((maxx - minx) / res)), int(round((maxy - miny) / res))
    return (minx, miny, maxx, maxy), from_origin(minx, maxy, res, res), (H, W)


def prepare_rasters(cfg, cell, ddir: Path, log=print) -> dict:
    import geopandas as gpd
    res = cfg["res_m"]
    b10, T, shape = grid_for_cell(cell, res)
    wgs = tuple(gpd.GeoSeries([box(*b10)], crs=CRS).to_crs(4326).total_bounds)
    wc_path, dem_path, slope30_path = ddir / "worldcover_10m.tif", ddir / "dem_30m.tif", ddir / "slope_30m.tif"
    sources = []
    if not wc_path.exists():
        urls = [dl.WC_URL.format(tile=t) for t in dl.worldcover_tiles(wgs)]
        log(f"  WorldCover tiles {dl.worldcover_tiles(wgs)}")
        dl.warp_to_grid(urls, b10, CRS, res, wc_path, "nearest", "uint8", 0)
        sources.append(Source("landcover", "10 m land-cover resistance and hard blocks (water)", "ESA WorldCover consortium", "; ".join(urls),
                              "v200 (2021)", "CC BY 4.0 (doi:10.5281/zenodo.7254221)", "10 m").fingerprint(wc_path))
    if not dem_path.exists():
        b30 = dl.aligned_bounds(b10, 30.0, buffer_m=60.0)
        wgs30 = tuple(gpd.GeoSeries([box(*b30)], crs=CRS).to_crs(4326).total_bounds)
        urls = [dl.COP_URL.format(name=dl.cop_name(la, lo)) for la, lo in dl.dem_tiles(wgs30)]
        log(f"  Copernicus GLO-30 tiles {len(urls)}")
        dl.warp_to_grid(urls, b30, CRS, 30.0, dem_path, "bilinear", "float32", -9999.0)
        sources.append(Source("dem", "slope (Sobel on 30 m, bilinear to 10 m); slope > 25 deg blocked", "Copernicus / ESA (AWS Open Data)", "; ".join(urls),
                              "GLO-30 (DGED COG)", "Copernicus DEM licence (free, attribution; doi:10.5270/ESA-c5d3d65)", "30 m").fingerprint(dem_path))
    with rasterio.open(dem_path) as s:
        dem = s.read(1).astype("float32")
        dem[dem == -9999.0] = np.nan
        T30 = s.transform
    slope30 = slope_sobel(dem, 30.0)
    with rasterio.open(slope30_path, "w", driver="GTiff", height=slope30.shape[0], width=slope30.shape[1], count=1, dtype="float32", crs=CRS,
                       transform=T30, nodata=-9999.0, compress="lzw") as d:
        d.write(np.where(np.isfinite(slope30), slope30, -9999.0).astype("float32"), 1)
    slope10_path = ddir / "slope_10m.tif"
    dl.warp_to_grid([str(slope30_path)], b10, CRS, res, slope10_path, "bilinear", "float32", -9999.0)
    with rasterio.open(wc_path) as s:
        lc = s.read(1)
    with rasterio.open(slope10_path) as s:
        sl = s.read(1).astype("float32")
        sl[sl == -9999.0] = np.nan
    return dict(landcover=lc, slope=sl, transform=T, shape=shape, bounds=b10, sources=sources,
                paths=dict(landcover=wc_path, dem=dem_path, slope10=slope10_path))


def cost_surface(cfg, prep: dict, cell) -> tuple:
    """Stage B cost recipe; cells outside the village polygon are blocked. Returns (cost float32 with NaN = blocked, inside mask)."""
    H, W = prep["shape"]
    inside = rasterize([(cell, 1)], out_shape=(H, W), transform=prep["transform"], fill=0, all_touched=False, dtype="uint8").astype(bool)
    layers = Layers(shape=(H, W), transform=prep["transform"], landcover=prep["landcover"], slope_deg=prep["slope"], source="multivillage")
    cost = cost_from_layers(layers, cfg["cost_surface"])
    cost[~inside] = np.nan
    return cost, inside
