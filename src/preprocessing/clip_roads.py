"""Clips the TGRAC road lines to the village boundary with gpd.clip() so that only road length inside the boundary is routed.
Writes Siddipet/Damarakunta/reference/derived/tgrac_road_network_clipped.gpkg and inputs/road_clip_report.csv. The original road layer is not edited.
usage: python src/preprocessing/clip_roads.py
"""
import csv
from pathlib import Path
import geopandas as gpd

ROOT = Path(__file__).resolve().parents[2]
V = ROOT / "Siddipet" / "Damarakunta"
roads = gpd.read_file(V / "reference" / "tgrac_road_network.gpkg")
bnd = gpd.read_file(V / "study_area" / "damarakunta_boundary.gpkg").to_crs(roads.crs)
clipped = gpd.clip(roads, bnd)
clipped = clipped.explode(index_parts=False)
clipped = clipped[(clipped.geometry.length > 0) & clipped.geom_type.eq("LineString")].reset_index(drop=True)
out = V / "reference" / "derived" / "tgrac_road_network_clipped.gpkg"
clipped.to_file(out, layer=gpd.list_layers(V / "reference" / "tgrac_road_network.gpkg").name.iloc[0], driver="GPKG")
L0, L1 = roads.geometry.length.sum(), clipped.geometry.length.sum()
rows = [("features_original", len(roads)), ("length_original_m", round(L0, 2)), ("features_reaching_outside", int((~roads.within(bnd.unary_union)).sum())),
        ("line_parts_after_clip", len(clipped)), ("length_inside_m", round(L1, 2)), ("length_outside_removed_m", round(L0 - L1, 2)),
        ("outside_percent", round(100 * (L0 - L1) / L0, 2))]
with open(ROOT / "inputs" / "road_clip_report.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["quantity", "value"]); w.writerows(rows)
print(rows, out)
