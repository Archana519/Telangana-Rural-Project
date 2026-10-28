"""Read-only: tolerance-based attachment check of plan routes against TGRAC reference roads."""
import sys
from pathlib import Path
import geopandas as gpd, pandas as pd
from shapely.geometry import Point

ROOT = Path(r"D:\Telangana_Rural_Project\Siddipet\Damarakunta")
PLAN = ROOT / "results" / "v6_buildings" / "plan_gap1" / "plan.gpkg"
ROADS = ROOT / "reference" / "tgrac_road_network.gpkg"
OUT = PLAN.parent / "connectivity_check_v2.csv"
CRS = "EPSG:32644"
if OUT.exists():
    sys.exit(f"{OUT} exists; remove or rename it first")

road_u = gpd.read_file(ROADS).to_crs(CRS).geometry.union_all()
rows = []
for layer in ("stageB_credit_plan", "independent_plan"):
    g = gpd.read_file(PLAN, layer=layer).to_crs(CRS)
    for _, r in g.iterrows():
        geom = r.geometry
        rows.append(dict(
            layer=layer, target=r.target, kind=r.kind, alt=r.alt, length_m=r.length_m,
            valid=bool(geom.is_valid), simple=bool(geom.is_simple),
            strict_intersects=bool(geom.intersects(road_u)),
            road_end_to_road_m=float(Point(geom.coords[-1]).distance(road_u)),
            line_to_road_m=float(geom.distance(road_u))))
df = pd.DataFrame(rows)
df.to_csv(OUT, index=False)

for layer, d in df.groupby("layer"):
    print(f"\n=== {layer}: {len(d)} routes")
    print("valid:", int(d.valid.sum()), "| simple (no self-touch):", int(d.simple.sum()),
          "| strict intersects road:", int(d.strict_intersects.sum()))
    for tol in (0.001, 0.01, 0.1, 1.0):
        print(f"  road end within {tol:>5} m of road: {int((d.road_end_to_road_m <= tol).sum())}")
    print(f"  max road_end_to_road_m: {d.road_end_to_road_m.max():.4f}")
d = df[df.layer == "stageB_credit_plan"].copy()
d["road_end_to_road_m"] = d.road_end_to_road_m.map(lambda v: f"{v:.2e}")
d["line_to_road_m"] = d.line_to_road_m.map(lambda v: f"{v:.2e}")
print("\nCredit plan routes:")
print(d.drop(columns="layer").to_string(index=False))
print("\nWrote:", OUT)