"""Create sampling windows + an empty reference layer for manual building digitizing (QGIS).
Writes one new GeoPackage; refuses to overwrite. Reads existing outputs only."""
import sys
from pathlib import Path
import numpy as np, geopandas as gpd, fiona, rasterio
from shapely.geometry import box
from rasterio.windows import from_bounds, Window

ROOT = Path(r"D:\Telangana_Rural_Project\Siddipet\Damarakunta")
ACC = ROOT / "results" / "v6_buildings" / "access" / "access_assessment.gpkg"
BND = ROOT / "study_area" / "damarakunta_boundary.gpkg"
RASTER = ROOT / "aligned" / "damarakunta_esri_highres_mosaic_0p6m.tif"
OUT_DIR = ROOT / "results" / "v6_buildings" / "reference"
OUT = OUT_DIR / "digitize_windows.gpkg"
CRS, HALF = "EPSG:32644", 100.0
if OUT.exists():
    sys.exit(f"{OUT} exists; will not overwrite (it may hold your traced buildings)")
OUT_DIR.mkdir(parents=True, exist_ok=True)

cl = gpd.read_file(ACC, layer="clusters").to_crs(CRS)
cand = gpd.read_file(ACC, layer="candidate_access").to_crs(CRS)
bnd = gpd.read_file(BND).to_crs(CRS).union_all()
chosen = []

def free(b):
    return all(not b.intersects(c[2]) for c in chosen)

def add(role, geom_center, tag):
    b = box(geom_center.x - HALF, geom_center.y - HALF, geom_center.x + HALF, geom_center.y + HALF)
    if free(b):
        chosen.append((f"W{len(chosen)+1}_{tag}", role, b)); return True
    return False

big = cl.sort_values("n_candidates", ascending=False)
for role, tag, row in (("dense settlement core", "CORE", big.iloc[0]),
                       ("second settlement", "EAST", big.iloc[1])):
    add(role, row.geometry.centroid, tag)
small = cl[(cl.kind == "ISOLATED_OR_SMALL_GROUP") & (~cl.gap_flag)].sort_values("n_candidates", ascending=False)
for _, r in small.iterrows():
    if add("fringe group near road", r.geometry.centroid, "FRINGE"):
        break
n = 0
for _, r in cl[cl.gap_flag].sort_values("n_candidates", ascending=False).iterrows():
    if add("gap cluster (far from reference road)", r.geometry.centroid, "GAP"):
        n += 1
    if n == 2:
        break

rng = np.random.default_rng(7)
minx, miny, maxx, maxy = gpd.GeoSeries([bnd], crs=CRS).total_bounds
with rasterio.open(RASTER) as src:
    for _ in range(5000):
        cx, cy = rng.uniform(minx + HALF, maxx - HALF), rng.uniform(miny + HALF, maxy - HALF)
        b = box(cx - HALF, cy - HALF, cx + HALF, cy + HALF)
        if not (bnd.contains(b) and free(b) and cand.intersects(b).sum() == 0):
            continue
        win = from_bounds(*b.bounds, transform=src.transform).round_offsets(op="floor").round_lengths(op="ceil")
        if win.col_off < 0 or win.row_off < 0 or win.col_off + win.width > src.width or win.row_off + win.height > src.height:
            continue
        if src.read_masks(1, window=win).min() == 0:
            continue
        chosen.append((f"W{len(chosen)+1}_FARMNEG", "farmland, no predicted buildings", b))
        break

rows = []
for wid, role, b in chosen:
    inside = cand[cand.intersects(b)]
    rows.append(dict(window_id=wid, role=role, cx=round(b.centroid.x), cy=round(b.centroid.y),
                     n_pred=int(len(inside)), pred_area_m2=round(float(inside.intersection(b).area.sum()), 0), geometry=b))
w = gpd.GeoDataFrame(rows, crs=CRS)
w.to_file(OUT, layer="windows", driver="GPKG")
schema = {"geometry": "Polygon", "properties": {"window_id": "str", "note": "str"}}
with fiona.open(OUT, "w", driver="GPKG", layer="reference_buildings", crs=CRS, schema=schema):
    pass
print(w.drop(columns="geometry").to_string(index=False))
print("\nWrote:", OUT, "| layers: windows, reference_buildings (empty)")