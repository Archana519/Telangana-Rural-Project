"""Proximity-based access screening: candidate buildings / clusters / facilities vs TGRAC reference roads.
Inputs are UNVERIFIED model predictions; outputs are screening estimates, not access verification."""
import argparse, os, sys
import numpy as np, geopandas as gpd, rasterio
from rasterio.windows import from_bounds, Window, bounds as wbounds
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from shapely.ops import unary_union

ROOT = r"D:\Telangana_Rural_Project\Siddipet\Damarakunta"
RASTER = os.path.join(ROOT, "aligned", "damarakunta_esri_highres_mosaic_0p6m.tif")
CAND = os.path.join(ROOT, "results", "v6_buildings", "candidate_buildings_full.gpkg")
ROADS = os.path.join(ROOT, "reference", "tgrac_road_network.gpkg")
FAC = os.path.join(ROOT, "reference", "damarakunta_priority_facilities.gpkg")
OUT_DIR = os.path.join(ROOT, "results", "v6_buildings", "access")
CRS = "EPSG:32644"

ap = argparse.ArgumentParser()
ap.add_argument("--min-area-m2", type=float, default=10.0)
ap.add_argument("--cluster-radius-m", type=float, default=20.0)
ap.add_argument("--settlement-min-n", type=int, default=8)
ap.add_argument("--gap-m", type=float, default=50.0)
ap.add_argument("--fac-near-m", type=float, default=30.0)
ap.add_argument("--overwrite", action="store_true", help="replace this script's own earlier output")
a = ap.parse_args()

gpkg = os.path.join(OUT_DIR, "access_assessment.gpkg")
if os.path.exists(gpkg):
    if not a.overwrite:
        sys.exit(f"{gpkg} exists; use --overwrite")
    os.remove(gpkg)
os.makedirs(OUT_DIR, exist_ok=True)

cand_all = gpd.read_file(CAND).to_crs(CRS)
roads = gpd.read_file(ROADS).to_crs(CRS)
fac = gpd.read_file(FAC, layer="priority_facilities").to_crs(CRS)
road_u = roads.geometry.union_all()

def build(cand, r):
    cand = cand.copy().reset_index(drop=True)
    cand["dist_to_ref_road_m"] = cand.geometry.distance(road_u).round(2)
    merged = unary_union(cand.geometry.buffer(r / 2.0).tolist())
    parts = list(merged.geoms) if hasattr(merged, "geoms") else [merged]
    cl = gpd.GeoDataFrame({"cluster_id": range(1, len(parts) + 1)}, geometry=parts, crs=CRS)
    pts = gpd.GeoDataFrame(geometry=cand.geometry.representative_point(), crs=CRS)
    j = gpd.sjoin(pts, cl, how="left", predicate="within")
    j = j[~j.index.duplicated(keep="first")]
    cand["cluster_id"] = j["cluster_id"].reindex(cand.index).fillna(-1).astype(int)
    g = cand.groupby("cluster_id")
    cl = cl.set_index("cluster_id")
    cl["n_candidates"] = g.size()
    cl["footprint_area_m2"] = g["area_m2"].sum().round(1)
    cl["min_dist_to_ref_road_m"] = g["dist_to_ref_road_m"].min()
    cl["extent_area_m2"] = cl.geometry.area.round(1)
    cl["kind"] = np.where(cl["n_candidates"] >= a.settlement_min_n,
                          "SETTLEMENT_CLUSTER", "ISOLATED_OR_SMALL_GROUP")
    cl = cl.reset_index()
    cand["gap_flag"] = cand["dist_to_ref_road_m"] > a.gap_m
    cl["gap_flag"] = cl["min_dist_to_ref_road_m"] > a.gap_m
    cand["status"] = "UNVERIFIED_PROXIMITY_ESTIMATE"
    return cand, cl

print("\nParameter sensitivity (screening counts only):")
print(" min_area_m2 | gap_m | candidates | cand_gap | clusters | cluster_gap")
for ma in (10, 25, 50, 100):
    c, k = build(cand_all[cand_all.area_m2 >= ma], a.cluster_radius_m)
    for gap in (25, 50, 100):
        print(f"{ma:>12} | {gap:>5} | {len(c):>10} | {int((c.dist_to_ref_road_m > gap).sum()):>8} |"
              f" {len(k):>8} | {int((k.min_dist_to_ref_road_m > gap).sum()):>11}")

cand, cl = build(cand_all[cand_all.area_m2 >= a.min_area_m2], a.cluster_radius_m)
print(f"\nSettings: min_area={a.min_area_m2} m2, cluster_radius={a.cluster_radius_m} m, "
      f"settlement_min_n={a.settlement_min_n}, gap={a.gap_m} m")
print(f"candidates: {len(cand)} | clusters: {len(cl)} "
      f"({int((cl.kind == 'SETTLEMENT_CLUSTER').sum())} settlement-type)")
print("candidate dist to ref road (m) p10/p50/p90/max:",
      [round(float(x), 1) for x in np.percentile(cand.dist_to_ref_road_m, [10, 50, 90, 100])])
print("candidates at dist 0 (touch/cross road geometry):", int((cand.dist_to_ref_road_m == 0).sum()))
print(f"candidates beyond {a.gap_m} m:", int(cand.gap_flag.sum()),
      "| clusters beyond:", int(cl.gap_flag.sum()))
show = ["cluster_id", "kind", "n_candidates", "footprint_area_m2", "min_dist_to_ref_road_m", "gap_flag"]
print("\nClusters (top 12 by candidate count):")
print(cl.sort_values("n_candidates", ascending=False)[show].head(12).to_string(index=False))

rows = []
for _, f in fac.iterrows():
    dc = cand.geometry.distance(f.geometry); i = dc.idxmin()
    dk = cl.geometry.distance(f.geometry); k = dk.idxmin()
    rows.append(dict(
        facility_id=f.facility_id, facility_name=f.facility_name, facility_type=f.facility_type,
        priority_group=f.priority_group, source=f.source,
        dist_to_ref_road_m=round(float(f.geometry.distance(road_u)), 1),
        nearest_cand_id=int(cand.loc[i, "cand_id"]), dist_to_nearest_cand_m=round(float(dc[i]), 1),
        nearest_cluster_id=int(cl.loc[k, "cluster_id"]), dist_to_nearest_cluster_m=round(float(dk[k]), 1),
        near_candidate_building=bool(dc[i] <= a.fac_near_m),
        note="facility location/type taken from source layer; not verified here",
        geometry=f.geometry))
fa = gpd.GeoDataFrame(rows, crs=CRS)
print("\nFacilities:")
print(fa.drop(columns=["geometry", "note", "source"]).to_string(index=False))

cand.to_file(gpkg, layer="candidate_access", driver="GPKG")
cl.to_file(gpkg, layer="clusters", driver="GPKG")
fa.to_file(gpkg, layer="facility_access", driver="GPKG")
cand.drop(columns="geometry").to_csv(os.path.join(OUT_DIR, "candidate_access.csv"), index=False)
cl.drop(columns="geometry").to_csv(os.path.join(OUT_DIR, "clusters.csv"), index=False)
fa.drop(columns="geometry").to_csv(os.path.join(OUT_DIR, "facility_access.csv"), index=False)

big = cl.sort_values("n_candidates", ascending=False).iloc[0]
bb = big.geometry.buffer(150).bounds
with rasterio.open(RASTER) as src:
    win = from_bounds(*bb, transform=src.transform).round_offsets(op="floor").round_lengths(op="ceil")
    win = win.intersection(Window(0, 0, src.width, src.height))
    img = src.read([1, 2, 3], window=win).transpose(1, 2, 0)
    l, b_, r, t = wbounds(win, src.transform)
fig, ax = plt.subplots(figsize=(12, 12 * (t - b_) / (r - l)))
ax.imshow(img, extent=(l, r, b_, t))
rz = roads.cx[l:r, b_:t]
if len(rz): rz.plot(ax=ax, color="cyan", linewidth=1.6)
cand.cx[l:r, b_:t].boundary.plot(ax=ax, color="red", linewidth=0.8)
fz = fa.cx[l:r, b_:t]
for _, f in fz.iterrows():
    ax.plot(f.geometry.x, f.geometry.y, "o", color="lime", markeredgecolor="black", markersize=11)
    ax.annotate(str(f.facility_id), (f.geometry.x, f.geometry.y), color="white", fontsize=10,
                xytext=(6, 6), textcoords="offset points")
ax.set_xlim(l, r); ax.set_ylim(b_, t); ax.set_axis_off()
p = os.path.join(OUT_DIR, "zoom_main_settlement.png")
fig.savefig(p, dpi=110, bbox_inches="tight"); plt.close(fig)
print("\nWrote:", gpkg, p, "(+3 CSVs in the same folder)", sep="\n  ")