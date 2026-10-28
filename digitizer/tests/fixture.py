"""Synthetic stand-in for the Damarakunta data (same CRS, 0.6 m pixels, same layer names/schema).

Used ONLY by the tests. It never touches the real project files.
Known ground truth: red 5x5-pixel markers are painted at exact map coordinates (MARKERS), so a
test can find them in the rendered PNG and check pixel->map conversion against the truth.
"""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import box

CRS = "EPSG:32644"
X0, Y0, RES = 261000.0, 1959600.0, 0.6        # upper-left corner and pixel size of the fake mosaic
W_PX, H_PX = 1200, 900
# window boxes (minx, miny, maxx, maxy) in map coordinates, 200 m x 200 m like the real windows
WINDOWS = {
    "W1_CORE": box(261100, 1959100, 261300, 1959300),
    "W4_GAP": box(261400, 1959100, 261600, 1959300),
    "W6_FARMNEG": box(261100, 1959350, 261300, 1959550),
}
# exact marker centres (map coordinates) inside W1_CORE and W4_GAP
MARKERS = [(261150.3, 1959250.9), (261220.7, 1959180.1), (261450.0, 1959200.0)]


def build(root: Path) -> dict:
    root = Path(root)
    (root / "aligned").mkdir(parents=True, exist_ok=True)
    ref_dir = root / "results" / "v6_buildings" / "reference"
    ref_dir.mkdir(parents=True, exist_ok=True)

    transform = from_origin(X0, Y0, RES, RES)
    img = np.full((3, H_PX, W_PX), 90, np.uint8)
    img[1] = 120
    for mx, my in MARKERS:
        col = (mx - X0) / RES
        row = (Y0 - my) / RES
        c, r = int(np.floor(col)), int(np.floor(row))
        img[0, r - 2:r + 3, c - 2:c + 3] = 255
        img[1, r - 2:r + 3, c - 2:c + 3] = 0
        img[2, r - 2:r + 3, c - 2:c + 3] = 0
    raster = root / "aligned" / "damarakunta_esri_highres_mosaic_0p6m.tif"
    with rasterio.open(raster, "w", driver="GTiff", height=H_PX, width=W_PX, count=3, dtype="uint8",
                       crs=CRS, transform=transform) as dst:
        dst.write(img)

    gpkg = ref_dir / "digitize_windows.gpkg"
    wins = gpd.GeoDataFrame(
        {"window_id": list(WINDOWS), "role": ["dense settlement core", "gap cluster", "farmland, no predicted buildings"],
         "cx": [261200, 261500, 261200], "cy": [1959200, 1959200, 1959450], "n_pred": [3, 1, 0],
         "pred_area_m2": [1200.0, 55.0, 0.0]},
        geometry=list(WINDOWS.values()), crs=CRS)
    wins.to_file(gpkg, layer="windows", driver="GPKG")
    empty = gpd.GeoDataFrame({"window_id": [], "note": []}, geometry=[], crs=CRS)
    empty.to_file(gpkg, layer="reference_buildings", driver="GPKG", geometry_type="Polygon")

    cand_dir = root / "results" / "v6_buildings"
    cands = gpd.GeoDataFrame(
        {"cand_id": [1, 2, 3], "area_m2": [100.0, 80.0, 60.0], "mean_prob": [0.6, 0.55, 0.5],
         "max_prob": [0.7, 0.6, 0.55], "comp_id": [1, 2, 3], "status": ["UNVERIFIED_PREDICTION"] * 3},
        geometry=[box(261148, 1959249, 261153, 1959253), box(261218, 1959178, 261224, 1959183),
                  box(261448, 1959198, 261453, 1959202)], crs=CRS)
    cpath = cand_dir / "candidate_buildings_full.gpkg"
    cands.to_file(cpath, layer="candidate_buildings", driver="GPKG")
    return {"root": root, "raster": raster, "gpkg": gpkg, "cands": cpath, "ref_dir": ref_dir}
