"""Compare Damarakunta individual-house routes with and without a 25-degree hard slope constraint.

Reads existing outputs only. Writes two QA CSVs into the slope25 run folder.
Line sampling is an approximate raster QA, not a substitute for grid-path validation.
"""
from pathlib import Path
import math
import sys

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio

BASE = Path(r"D:\Telangana_Rural_Project\Siddipet\Damarakunta\results")
V1 = BASE / "individual_house_routing_v1" / "individual_house_routes_v1.gpkg"
V2 = BASE / "individual_house_routing_slope25_v2" / "individual_house_routes_v1.gpkg"
OUT = BASE / "individual_house_routing_slope25_v2"
SLOPE = Path(r"D:\Telangana_Rural_Project\Siddipet\Damarakunta\aligned\damarakunta_slope_10m.tif")
LAYER = "house_routes"
ID = "house_route_id"


def need_fields(gdf, required, path):
    missing = [c for c in required if c not in gdf.columns]
    if missing:
        raise ValueError(f"{path} missing fields {missing}; available={list(gdf.columns)}")


def sample_line_slope(line, src, interval_m=2.0):
    if line is None or line.is_empty or line.length <= 0:
        return {"samples": 0, "valid_samples": 0, "samples_over_25deg": 0,
                "max_sampled_slope_deg": np.nan, "nodata_or_outside_samples": 0}
    n = max(2, int(math.ceil(line.length / interval_m)) + 1)
    vals = []
    nodata = 0
    for i in range(n):
        p = line.interpolate(line.length * i / (n - 1))
        try:
            row, col = src.index(p.x, p.y)
            if row < 0 or col < 0 or row >= src.height or col >= src.width:
                nodata += 1
                continue
            v = float(src.read(1, window=((row, row + 1), (col, col + 1)))[0, 0])
            if src.nodata is not None and np.isclose(v, src.nodata):
                nodata += 1
                continue
            if not np.isfinite(v):
                nodata += 1
                continue
            vals.append(v)
        except Exception:
            nodata += 1
    return {
        "samples": n,
        "valid_samples": len(vals),
        "samples_over_25deg": int(sum(v > 25.0 for v in vals)),
        "max_sampled_slope_deg": round(max(vals), 3) if vals else np.nan,
        "nodata_or_outside_samples": nodata,
    }


def main():
    for p in (V1, V2, SLOPE):
        if not p.exists():
            sys.exit(f"Missing required input: {p}")
    print("Reading route geometries (read-only)...")
    a = gpd.read_file(V1, layer=LAYER)
    b = gpd.read_file(V2, layer=LAYER)
    need_fields(a, [ID], V1)
    need_fields(b, [ID], V2)
    a = a[a.geometry.notna() & ~a.geometry.is_empty].copy()
    b = b[b.geometry.notna() & ~b.geometry.is_empty].copy()
    da = {str(r[ID]): r for _, r in a.iterrows()}
    db = {str(r[ID]): r for _, r in b.iterrows()}
    ids = sorted(set(da) & set(db))
    rows = []
    for rid in ids:
        g1, g2 = da[rid].geometry, db[rid].geometry
        h = float(g1.hausdorff_distance(g2))
        l1, l2 = float(g1.length), float(g2.length)
        rows.append({
            ID: rid,
            "cand_id_v1": str(da[rid].get("cand_id", "")),
            "cand_id_v2": str(db[rid].get("cand_id", "")),
            "quality_class_v2": str(db[rid].get("quality_class", "")),
            "v1_length_m": round(l1, 3),
            "v2_length_m": round(l2, 3),
            "length_change_m_v2_minus_v1": round(l2 - l1, 3),
            "topologically_equal_geometry": bool(g1.equals(g2)),
            "hausdorff_distance_m": round(h, 3),
            "geometry_changed_over_0p1m": bool(h > 0.1),
        })
    comp = pd.DataFrame(rows)
    comp_path = OUT / "v1_vs_slope25_route_geometry_comparison.csv"
    comp.to_csv(comp_path, index=False)

    print("Sampling the slope raster along both sets of route lines (2 m intervals)...")
    slope_rows = []
    with rasterio.open(SLOPE) as src:
        if src.crs is None or src.crs.to_epsg() != 32644:
            sys.exit(f"Unexpected slope raster CRS: {src.crs}")
        for rid in ids:
            for version, rec in (("v1_no_hard_slope_limit", da[rid]), ("v2_slope_limit_25deg", db[rid])):
                met = sample_line_slope(rec.geometry, src)
                slope_rows.append({ID: rid, "version": version, **met})
    slope_df = pd.DataFrame(slope_rows)
    slope_path = OUT / "route_line_slope_sample_audit.csv"
    slope_df.to_csv(slope_path, index=False)

    print("\n=== ROUTE GEOMETRY COMPARISON ===")
    print(f"V1 route lines: {len(a)} | V2 route lines: {len(b)} | matched IDs: {len(ids)}")
    if not comp.empty:
        print(f"Length changed > 0.01 m: {int((comp['length_change_m_v2_minus_v1'].abs() > 0.01).sum())}")
        print(f"Geometry changed (Hausdorff > 0.1 m): {int(comp['geometry_changed_over_0p1m'].sum())}")
        print(f"Topologically equal geometries: {int(comp['topologically_equal_geometry'].sum())}/{len(comp)}")
        print(f"V1 total line length: {comp['v1_length_m'].sum():.2f} m")
        print(f"V2 total line length: {comp['v2_length_m'].sum():.2f} m")
        print("Largest geometry changes:")
        print(comp.sort_values("hausdorff_distance_m", ascending=False).head(12).to_string(index=False))

    print("\n=== ROUTE-LINE SLOPE SAMPLE AUDIT ===")
    summary = slope_df.groupby("version").agg(
        route_lines=(ID, "nunique"),
        routes_with_any_sample_over_25deg=("samples_over_25deg", lambda s: int((s > 0).sum())),
        total_samples_over_25deg=("samples_over_25deg", "sum"),
        maximum_sampled_slope_deg=("max_sampled_slope_deg", "max"),
        routes_with_nodata_or_outside_samples=("nodata_or_outside_samples", lambda s: int((s > 0).sum())),
    ).reset_index()
    print(summary.to_string(index=False))
    print("\nNOTE: line sampling includes the house-edge connector and can sample adjacent cells near grid-cell boundaries.")
    print("A sample >25 degrees needs inspection; it does not alone prove the internal grid path violated the constraint.")
    print("Wrote:", comp_path)
    print("Wrote:", slope_path)
    print("No route GPKG or source raster was modified.")


if __name__ == "__main__":
    main()
