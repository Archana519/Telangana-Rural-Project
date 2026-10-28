from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.features import geometry_mask
from rasterio.transform import from_origin
from rasterio.warp import reproject
from scipy.ndimage import sobel

ROOT = Path(r"D:\Telangana_Rural_Project")
VILLAGE = ROOT / "Siddipet" / "Damarakunta"
CRS = "EPSG:32644"

BOUNDARY_PATH = VILLAGE / "study_area" / "damarakunta_boundary.gpkg"
WC_PATH = VILLAGE / "raw" / "landcover" / "damarakunta_worldcover_clip.tif"
DEM_PATH = VILLAGE / "raw" / "dem" / "damarakunta_dem_clip.tif"
OUT = VILLAGE / "aligned"

OUT.mkdir(parents=True, exist_ok=True)

boundary = gpd.read_file(BOUNDARY_PATH).to_crs(CRS)
geom = boundary.geometry.union_all()
minx, miny, maxx, maxy = geom.bounds

# Common 10 m planning grid
x0 = np.floor(minx / 10) * 10
y0 = np.ceil(maxy / 10) * 10
width = int(np.ceil((maxx - x0) / 10))
height = int(np.ceil((y0 - miny) / 10))
transform10 = from_origin(x0, y0, 10, 10)

inside = geometry_mask(
    [geom],
    out_shape=(height, width),
    transform=transform10,
    invert=True
)

# 1. Reproject WorldCover using nearest-neighbour resampling
with rasterio.open(WC_PATH) as src:
    wc = np.zeros((height, width), dtype=np.uint8)

    reproject(
        source=rasterio.band(src, 1),
        destination=wc,
        src_transform=src.transform,
        src_crs=src.crs,
        src_nodata=src.nodata,
        dst_transform=transform10,
        dst_crs=CRS,
        dst_nodata=0,
        resampling=Resampling.nearest
    )

wc[~inside] = 0

wc_profile = {
    "driver": "GTiff",
    "height": height,
    "width": width,
    "count": 1,
    "dtype": "uint8",
    "crs": CRS,
    "transform": transform10,
    "nodata": 0,
    "compress": "lzw"
}

with rasterio.open(OUT / "damarakunta_worldcover_10m.tif", "w", **wc_profile) as dst:
    dst.write(wc, 1)

# 2. Reproject DEM at approximately 30 m resolution
dem_transform = from_origin(
    np.floor(minx / 30) * 30,
    np.ceil(maxy / 30) * 30,
    30, 30
)
dem_width = int(np.ceil((maxx - dem_transform.c) / 30))
dem_height = int(np.ceil((dem_transform.f - miny) / 30))

dem = np.full((dem_height, dem_width), -9999.0, dtype=np.float32)

with rasterio.open(DEM_PATH) as src:
    reproject(
        source=rasterio.band(src, 1),
        destination=dem,
        src_transform=src.transform,
        src_crs=src.crs,
        src_nodata=src.nodata,
        dst_transform=dem_transform,
        dst_crs=CRS,
        dst_nodata=-9999.0,
        resampling=Resampling.bilinear
    )

dem_profile = {
    "driver": "GTiff",
    "height": dem_height,
    "width": dem_width,
    "count": 1,
    "dtype": "float32",
    "crs": CRS,
    "transform": dem_transform,
    "nodata": -9999.0,
    "compress": "lzw"
}

with rasterio.open(OUT / "damarakunta_dem_30m.tif", "w", **dem_profile) as dst:
    dst.write(dem, 1)

# 3. Calculate slope in degrees on the projected DEM grid
valid = np.isfinite(dem) & (dem != -9999.0)
safe = np.where(valid, dem, np.nan)

# Fill missing cells temporarily for numerical differentiation;
# final slope remains NoData where neighbourhood support is insufficient.
filled = np.where(valid, dem, np.nanmedian(dem[valid]))

dzdx = sobel(filled, axis=1, mode="nearest") / 8.0 / 30.0
dzdy = -sobel(filled, axis=0, mode="nearest") / 8.0 / 30.0

slope = np.degrees(np.arctan(np.hypot(dzdx, dzdy))).astype(np.float32)

# Avoid reporting slope where the DEM itself is missing.
slope[~valid] = -9999.0

with rasterio.open(OUT / "damarakunta_slope_30m.tif", "w", **dem_profile) as dst:
    dst.write(slope, 1)

# 4. Resample slope to the 10 m WorldCover grid for cost-surface use
slope10 = np.full((height, width), -9999.0, dtype=np.float32)

reproject(
    source=slope,
    destination=slope10,
    src_transform=dem_transform,
    src_crs=CRS,
    src_nodata=-9999.0,
    dst_transform=transform10,
    dst_crs=CRS,
    dst_nodata=-9999.0,
    resampling=Resampling.bilinear
)

slope10[~inside] = -9999.0

slope_profile = wc_profile.copy()
slope_profile.update(dtype="float32", nodata=-9999.0)

with rasterio.open(OUT / "damarakunta_slope_10m.tif", "w", **slope_profile) as dst:
    dst.write(slope10, 1)

print("Terrain alignment complete.")
print("CRS:", CRS)
print("WorldCover:", OUT / "damarakunta_worldcover_10m.tif")
print("DEM:", OUT / "damarakunta_dem_30m.tif")
print("Slope:", OUT / "damarakunta_slope_30m.tif")
print("Slope aligned to 10 m:", OUT / "damarakunta_slope_10m.tif")
print("10 m grid dimensions:", width, "x", height)
print("WorldCover classes:", np.unique(wc))
print("Valid DEM cells:", int(valid.sum()))
print("Valid slope cells on 10 m grid:", int(np.sum(slope10 != -9999.0)))