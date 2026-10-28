"""Class-2 raster -> candidate building polygons (EPSG:32644). Unvalidated."""
import argparse, os, sys
import numpy as np, cv2, rasterio, geopandas as gpd
from rasterio.features import shapes
from shapely.geometry import shape
from shapely.validation import make_valid

ROOT = r"D:\Telangana_Rural_Project\Siddipet\Damarakunta"
PRED = os.path.join(ROOT, "predictions", "tiled_v1")
BOUNDARY = os.path.join(ROOT, "study_area", "damarakunta_boundary.gpkg")
OUT_DIR = os.path.join(ROOT, "results", "v6_buildings")

ap = argparse.ArgumentParser()
ap.add_argument("--tag", default="full")
ap.add_argument("--min-area-m2", type=float, default=10.0)
ap.add_argument("--min-prob", type=float, default=0.0, help="min mean building prob (0-1)")
ap.add_argument("--open-px", type=int, default=0, help="opening kernel size (0=off)")
ap.add_argument("--close-px", type=int, default=0, help="closing kernel size (0=off)")
ap.add_argument("--simplify-m", type=float, default=0.0)
ap.add_argument("--overwrite", action="store_true")
a = ap.parse_args()

out_gpkg = os.path.join(OUT_DIR, f"candidate_buildings_{a.tag}.gpkg")
if os.path.exists(out_gpkg) and not a.overwrite:
    sys.exit(f"{out_gpkg} exists; use --overwrite")
os.makedirs(OUT_DIR, exist_ok=True)

with rasterio.open(os.path.join(PRED, f"pred_classes_{a.tag}.tif")) as s:
    cls, tr, crs = s.read(1), s.transform, s.crs
with rasterio.open(os.path.join(PRED, f"building_prob_{a.tag}.tif")) as s:
    prob = s.read(1)
px_area = abs(tr.a * tr.e)
print("CRS:", crs, "| pixel area m2:", round(px_area, 4), "| shape:", cls.shape)

mask = (cls == 2).astype(np.uint8)
print("raw class-2 pixels:", int(mask.sum()), f"({100*mask.mean():.3f}%)")
if a.open_px > 0:
    k = np.ones((a.open_px, a.open_px), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k)
if a.close_px > 0:
    k = np.ones((a.close_px, a.close_px), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k)

n, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
area_m2 = stats[:, cv2.CC_STAT_AREA] * px_area
mean_p = np.bincount(labels.ravel(), weights=prob.ravel(), minlength=n) / np.maximum(
    np.bincount(labels.ravel(), minlength=n), 1) / 255.0
max_p = np.zeros(n)
np.maximum.at(max_p, labels.ravel(), prob.ravel() / 255.0)
print("components before filtering:", n - 1)
print("sensitivity (count surviving min area):")
for t in (5, 10, 15, 25, 50, 100):
    print(f"  >= {t:>3} m2: {int((area_m2[1:] >= t).sum())}")

keep = (area_m2 >= a.min_area_m2) & (mean_p >= a.min_prob)
keep[0] = False
print(f"kept (min_area={a.min_area_m2} m2, min_prob={a.min_prob}):", int(keep.sum()))

lab = np.where(keep[labels], labels, 0).astype(np.int32)
del labels
rows = []
for geom, val in shapes(lab, mask=lab > 0, transform=tr, connectivity=8):
    g = make_valid(shape(geom))
    if a.simplify_m > 0:
        g = g.simplify(a.simplify_m)
    v = int(val)
    rows.append(dict(comp_id=v, area_m2=round(float(area_m2[v]), 2),
                     mean_prob=round(float(mean_p[v]), 3), max_prob=round(float(max_p[v]), 3),
                     status="UNVERIFIED_PREDICTION", geometry=g))
gdf = gpd.GeoDataFrame(rows, crs=crs)

b = gpd.read_file(BOUNDARY).to_crs(crs)
bu = b.union_all()
gdf = gdf[gdf.geometry.centroid.within(bu)].reset_index(drop=True)
gdf.insert(0, "cand_id", range(1, len(gdf) + 1))
print("candidates inside village boundary:", len(gdf))
if len(gdf):
    print("area m2 percentiles (10/50/90/99):",
          [round(float(x), 1) for x in np.percentile(gdf.area_m2, [10, 50, 90, 99])])
    print("mean_prob percentiles (10/50/90):",
          [round(float(x), 2) for x in np.percentile(gdf.mean_prob, [10, 50, 90])])
gdf.to_file(out_gpkg, layer="candidate_buildings", driver="GPKG")
print("Wrote:", out_gpkg, "| layer: candidate_buildings | CRS:", gdf.crs)