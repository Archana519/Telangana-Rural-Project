"""Raster layer providers and the shared cost-surface recipe for the hierarchical routing levels.

Separation of concerns (raw -> derived -> parameters -> metrics):
  * a LayerProvider serves RAW layers (land cover, slope) for any bounding box at any resolution;
  * cost_from_layers() DERIVES a cost raster from those layers using parameters from configs/hierarchy_levels.yaml;
  * nothing here writes to disk or touches the raw inputs.

Providers
  RasterLayerProvider      windowed, resampled reads from GeoTIFFs (WorldCover + DEM) - the production path
  SyntheticLayerProvider   deterministic landscape (hills, forest, rivers with fords); a pure function of
                           coordinates, so windows at different resolutions agree and nothing large is allocated
  FlatLayerProvider        documented fallback when no land-cover raster exists (constant cost; flagged in outputs)
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

import numpy as np
from rasterio.transform import Affine, from_origin

Bounds = tuple  # (minx, miny, maxx, maxy) in the working CRS


@dataclass
class Layers:
    """Raw layers on one grid. landcover: WorldCover class codes (0 = invalid); slope_deg: degrees or NaN."""
    transform: Affine
    landcover: Optional[np.ndarray]
    slope_deg: Optional[np.ndarray]
    shape: tuple
    source: str

    @property
    def res(self) -> float:
        return abs(self.transform.a)


def grid_for(bounds: Bounds, res: float):
    """Affine + shape covering `bounds` with square cells of `res` m, anchored on the north-west corner."""
    minx, miny, maxx, maxy = bounds
    W = max(1, int(math.ceil((maxx - minx) / res)))
    H = max(1, int(math.ceil((maxy - miny) / res)))
    return from_origin(minx, maxy, res, res), (H, W)


def slope_sobel(dem: np.ndarray, res: float) -> np.ndarray:
    """Slope in degrees by the Stage B method (scripts/align_damarakunta_terrain.py): Sobel/8/res on a DEM whose missing
    cells are temporarily filled with the median; NaN where the DEM itself is NaN."""
    from scipy.ndimage import sobel
    valid = np.isfinite(dem)
    if not valid.any():
        return np.full(dem.shape, np.nan, dtype="float32")
    filled = np.where(valid, dem, np.nanmedian(dem[valid])).astype("float64")
    dzdx = sobel(filled, axis=1, mode="nearest") / 8.0 / res
    dzdy = -sobel(filled, axis=0, mode="nearest") / 8.0 / res
    s = np.degrees(np.arctan(np.hypot(dzdx, dzdy))).astype("float32")
    s[~valid] = np.nan
    return s


def slope_from_dem(dem: np.ndarray, res: float) -> np.ndarray:
    """Slope in degrees by central differences (np.gradient). NaN where the DEM is NaN."""
    gy, gx = np.gradient(dem.astype("float64"), res)
    return np.degrees(np.arctan(np.hypot(gx, gy))).astype("float32")


class LayerProvider:
    name = "base"

    def layers(self, bounds: Bounds, res: float) -> Layers:  # pragma: no cover - interface
        raise NotImplementedError


# ------------------------------------------------------------------------------------------ synthetic
class SyntheticLayerProvider(LayerProvider):
    """Deterministic synthetic landscape for tests and the no-data fallback of Levels 3-4.

    land cover: grassland / cropland dominate, tree-cover patches where a smooth field is high, built-up near
    `settlements`, water along `n_rivers` sinuous rivers that are passable only at `ford_every_m` spacing (fords),
    so the landscape is always connectable. slope: gradient of a smooth elevation field (ridges up to ~max_slope_deg).
    """
    name = "synthetic"

    def __init__(self, bounds: Bounds, seed: int = 7, n_rivers: int = 2, ford_every_m: float = 6000.0,
                 forest_threshold: float = 0.62, max_slope_deg: float = 22.0, settlements=()):
        self.bounds, self.seed = bounds, int(seed)
        rng = np.random.default_rng(self.seed)
        self.ph = rng.uniform(0, 2 * math.pi, size=(6,))
        self.span = max(bounds[2] - bounds[0], bounds[3] - bounds[1])
        self.lam = self.span / np.array([3.1, 5.3, 8.7])
        self.n_rivers, self.ford_every_m = n_rivers, ford_every_m
        self.forest_threshold, self.max_slope_deg = forest_threshold, max_slope_deg
        self.rivers = []
        for k in range(n_rivers):
            y0 = bounds[1] + (k + 1) * (bounds[3] - bounds[1]) / (n_rivers + 1)
            self.rivers.append((y0, 0.045 * self.span * (1 + 0.3 * k), self.span / (2.5 + k), rng.uniform(0, 6.28)))
        self.settlements = list(settlements)

    def _smooth(self, X, Y, which):
        a = self.ph
        l0, l1, l2 = self.lam
        if which == 0:   # forest propensity in [0,1]
            f = np.sin(X / l0 + a[0]) * np.cos(Y / l1 + a[1]) + 0.5 * np.sin((X + Y) / l2 + a[2])
        else:            # elevation basis
            f = np.cos(X / l1 + a[3]) * np.sin(Y / l0 + a[4]) + 0.5 * np.cos((X - Y) / l2 + a[5])
        return 0.5 + f / 3.0

    def layers(self, bounds: Bounds, res: float) -> Layers:
        T, (H, W) = grid_for(bounds, res)
        xs = T.c + (np.arange(W) + 0.5) * res
        ys = T.f - (np.arange(H) + 0.5) * res
        X, Y = np.meshgrid(xs, ys)
        forest = self._smooth(X, Y, 0)
        lc = np.where(forest > self.forest_threshold, 10,
                      np.where(forest > 0.45, 40, np.where(forest > 0.30, 30, 20))).astype("uint8")
        for (sx, sy, sr) in self.settlements:
            lc[np.hypot(X - sx, Y - sy) <= sr] = 50
        for (y0, amp, lam, ph) in self.rivers:
            yr = y0 + amp * np.sin(X / lam + ph)
            water = np.abs(Y - yr) <= 0.012 * self.span          # widths do NOT depend on the sampling resolution
            ford = np.mod(X - self.bounds[0], self.ford_every_m) < 0.015 * self.span
            lc[water & ~ford] = 80
        # elevation on a margin-padded grid so the gradient is correct at the window edge
        elev = self.max_slope_deg_scale() * self._smooth(X, Y, 1)
        slope = slope_from_dem(elev, res)
        return Layers(T, lc, slope, (H, W), self.name)

    def max_slope_deg_scale(self) -> float:
        # elevation (m) chosen so slopes reach ~max_slope_deg over a wavelength of ~span/5
        return math.tan(math.radians(self.max_slope_deg)) * self.span / 5.0 / 3.0


# ------------------------------------------------------------------------------------------ rasters
class RasterLayerProvider(LayerProvider):
    """Windowed, resampled reads from a WorldCover GeoTIFF and (optionally) a DEM GeoTIFF.

    Land cover uses nearest-neighbour resampling (class codes); the DEM uses bilinear resampling and slope is computed
    on the target grid. Cells outside a raster's extent come back as invalid (0 / NaN).
    """
    name = "raster"

    DEM_RES = 30.0                      # native DEM grid (SRTM 1" and Copernicus GLO-30 are both ~30 m)

    def __init__(self, landcover_path: Optional[str], dem_path: Optional[str] = None, slope_method: str = "sobel_native"):
        """slope_method 'sobel_native' (default, = Stage B): slope by Sobel on a 30 m DEM grid, then bilinear to the target grid.
        'gradient_target': np.gradient on the DEM resampled to the target grid (legacy, differs from Stage B)."""
        self.landcover_path, self.dem_path, self.slope_method = landcover_path, dem_path, slope_method

    @staticmethod
    def _read(path, bounds, res, T, shape, resampling, dtype, fill):
        import rasterio
        from rasterio.warp import reproject
        out = np.full(shape, fill, dtype=dtype)
        with rasterio.open(path) as src:
            reproject(source=rasterio.band(src, 1), destination=out, src_transform=src.transform, src_crs=src.crs,
                      dst_transform=T, dst_crs=src.crs, resampling=resampling, src_nodata=src.nodata,
                      dst_nodata=fill)
        return out

    def layers(self, bounds: Bounds, res: float) -> Layers:
        from rasterio.enums import Resampling
        T, shape = grid_for(bounds, res)
        lc = slope = None
        if self.landcover_path:
            lc = self._read(self.landcover_path, bounds, res, T, shape, Resampling.nearest, "uint8", 0)
        if self.dem_path and self.slope_method == "gradient_target":
            dem = self._read(self.dem_path, bounds, res, T, shape, Resampling.bilinear, "float32", np.nan)
            slope = slope_from_dem(dem, res)
        elif self.dem_path:
            r = self.DEM_RES                                           # DEM lattice aligned to the window, 2 cells of margin
            nb = (bounds[0] - 2 * r, bounds[1] - 2 * r, bounds[2] + 2 * r, bounds[3] + 2 * r)
            T30, shape30 = grid_for(nb, r)
            dem30 = self._read(self.dem_path, nb, r, T30, shape30, Resampling.bilinear, "float32", np.nan)
            s30 = slope_sobel(dem30, r)
            slope = np.full(shape, np.nan, dtype="float32")
            from rasterio.warp import reproject
            import rasterio
            with rasterio.open(self.dem_path) as src:
                crs = src.crs
            reproject(s30, slope, src_transform=T30, src_crs=crs, dst_transform=T, dst_crs=crs,
                      src_nodata=np.nan, dst_nodata=np.nan, resampling=Resampling.bilinear)
        return Layers(T, lc, slope, shape, self.name)


class FlatLayerProvider(LayerProvider):
    """No land cover, no DEM: cost_from_layers() will return the constant fallback cost (flagged downstream)."""
    name = "flat_fallback"

    def layers(self, bounds: Bounds, res: float) -> Layers:
        T, shape = grid_for(bounds, res)
        return Layers(T, None, None, shape, self.name)


# ------------------------------------------------------------------------------------------ cost recipe
def cost_from_layers(layers: Layers, cs: dict, forest_multiplier: float = 1.0) -> np.ndarray:
    """Cost raster (float32; NaN = hard-blocked) following the Level-1 recipe.

    cost = land_cost[class] (+ forest multiplier on class 10) + clip(slope, 0, slope_ref)/slope_ref * slope_weight
    hard-blocked: water, invalid class, slope > slope_limit_deg, invalid slope where a DEM was used.
    With no land cover the constant `flat_fallback_cost` is used (and slope still applies when a DEM exists).
    """
    H, W = layers.shape
    if layers.landcover is None:
        cost = np.full((H, W), float(cs["flat_fallback_cost"]), dtype="float32")
    else:
        lc = layers.landcover
        table = {int(k): float(v) for k, v in cs["worldcover_cost"].items()}
        cost = np.full((H, W), np.nan, dtype="float32")
        for code, base in table.items():
            cost[lc == code] = base * (forest_multiplier if code == 10 else 1.0)
        cost[lc == int(cs["water_class"])] = np.nan
        cost[lc == int(cs["invalid_class"])] = np.nan
    if layers.slope_deg is not None:
        s = layers.slope_deg
        pen = np.clip(s, 0, cs["slope_ref_deg"]) / cs["slope_ref_deg"] * cs["slope_weight"]
        cost = cost + pen.astype("float32")
        cost[~np.isfinite(s)] = np.nan
        cost[s > cs["slope_limit_deg"]] = np.nan
    return cost
