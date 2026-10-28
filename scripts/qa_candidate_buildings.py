"""Read-only QA: candidate-building overlay, chip contact sheet, GIS layer info."""
import os, numpy as np, geopandas as gpd, rasterio, fiona
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from rasterio.windows import Window, from_bounds, bounds as wbounds

ROOT = r"D:\Telangana_Rural_Project\Siddipet\Damarakunta"
RASTER = os.path.join(ROOT, "aligned", "damarakunta_esri_highres_mosaic_0p6m.tif")
CAND = os.path.join(ROOT, "results", "v6_buildings", "candidate_buildings_full.gpkg")
BND = os.path.join(ROOT, "study_area", "damarakunta_boundary.gpkg")
ROADS = os.path.join(ROOT, "reference", "tgrac_road_network.gpkg")
FAC = os.path.join(ROOT, "reference", "damarakunta_priority_facilities.gpkg")
V4 = os.path.join(ROOT, "results", "damarakunta_routes_v4.gpkg")
OUT = os.path.join(ROOT, "results", "v6_buildings", "qa")
os.makedirs(OUT, exist_ok=True)
CRS = "EPSG:32644"

def info(path):
    print(f"\n== {path}")
    if not os.path.exists(path):
        print("   NOT FOUND"); return {}
    d = {}
    for lyr in fiona.listlayers(path):
        g = gpd.read_file(path, layer=lyr)
        print(f"   layer '{lyr}': {len(g)} features | CRS: {g.crs.to_string() if g.crs else None} "
              f"| geom: {sorted(g.geom_type.unique().tolist())}")
        print(f"   columns: {[c for c in g.columns if c != 'geometry']}")
        d[lyr] = g
    return d

cand = gpd.read_file(CAND).to_crs(CRS)
bnd = gpd.read_file(BND).to_crs(CRS)
roads = info(ROADS); fac = info(FAC); v4 = info(V4)

print("\nCandidate area bins (m2):")
for lo, hi in [(0, 30), (30, 150), (150, 500), (500, 1e9)]:
    print(f"  {lo:>4}-{hi if hi < 1e9 else 'inf'}: {int(((cand.area_m2 >= lo) & (cand.area_m2 < hi)).sum())}")

with rasterio.open(RASTER) as src:
    def read_rgb(bounds, maxdim=None, boundless=False):
        win = from_bounds(*bounds, transform=src.transform)
        win = win.round_offsets(op="floor").round_lengths(op="ceil")
        if not boundless:
            win = win.intersection(Window(0, 0, src.width, src.height))
        h, w = int(win.height), int(win.width)
        shp = (3, h, w)
        if maxdim and max(h, w) > maxdim:
            s = maxdim / max(h, w); shp = (3, int(h * s), int(w * s))
        arr = src.read([1, 2, 3], window=win, out_shape=shp, boundless=boundless, fill_value=0)
        l, b, r, t = wbounds(win, src.transform)
        return arr.transpose(1, 2, 0), (l, r, b, t)

    # 1) village overview
    bb = bnd.buffer(100).total_bounds
    img, ext = read_rgb(bb, maxdim=2600)
    fig, ax = plt.subplots(figsize=(14, 14 * (ext[3] - ext[2]) / (ext[1] - ext[0])))
    ax.imshow(img, extent=ext)
    bnd.boundary.plot(ax=ax, color="yellow", linewidth=1.2)
    for g in roads.values():
        g.to_crs(CRS).clip(bb).plot(ax=ax, color="cyan", linewidth=1.0)
    cand.boundary.plot(ax=ax, color="red", linewidth=0.8)
    for g in fac.values():
        g.to_crs(CRS).plot(ax=ax, color="lime", markersize=40, edgecolor="black")
    ax.set_xlim(ext[0], ext[1]); ax.set_ylim(ext[2], ext[3]); ax.set_axis_off()
    p1 = os.path.join(OUT, "overview_candidates_roads.png")
    fig.savefig(p1, dpi=110, bbox_inches="tight"); plt.close(fig)

    # 2) contact sheet: 6 largest, 6 median, 6 smallest
    s = cand.sort_values("area_m2").reset_index(drop=True)
    mid = len(s) // 2
    picks = [("LARGEST", s.iloc[-6:]), ("MEDIAN", s.iloc[mid - 3:mid + 3]), ("SMALLEST", s.iloc[:6])]
    fig, axes = plt.subplots(3, 6, figsize=(18, 9.4))
    for r, (name, rows) in enumerate(picks):
        for c, (_, row) in enumerate(rows.iterrows()):
            cx, cy = row.geometry.centroid.x, row.geometry.centroid.y
            half = 45
            img, ext = read_rgb((cx - half, cy - half, cx + half, cy + half), boundless=True)
            ax = axes[r, c]; ax.imshow(img, extent=ext)
            gpd.GeoSeries([row.geometry], crs=CRS).boundary.plot(ax=ax, color="red", linewidth=1.2)
            ax.set_xlim(ext[0], ext[1]); ax.set_ylim(ext[2], ext[3]); ax.set_axis_off()
            ax.set_title(f"{name} id{int(row.cand_id)}\n{row.area_m2:.0f} m2  p={row.mean_prob:.2f}", fontsize=8)
    p2 = os.path.join(OUT, "contact_sheet.png")
    fig.savefig(p2, dpi=100, bbox_inches="tight"); plt.close(fig)

cand.drop(columns="geometry").to_csv(os.path.join(OUT, "candidates_table.csv"), index=False)
print("\nWrote:", p1, p2, os.path.join(OUT, "candidates_table.csv"), sep="\n  ")