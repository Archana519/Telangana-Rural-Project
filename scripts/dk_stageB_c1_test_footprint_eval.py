import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import geopandas as gpd
from shapely.geometry import box, LineString
from dk_stageB_c1_footprint_eval_v1 import eval_routes, summarise
bld = gpd.GeoDataFrame({"cand_id": [1, 2, 3]}, geometry=[box(0, 0, 10, 10), box(20, 0, 30, 10), box(40, 0, 50, 10)])
# route of cand 1 runs along y=5 from x=5 to 55: leaves own (1), crosses 2 and 3
rt = gpd.GeoDataFrame({"cand_id": [1]}, geometry=[LineString([(5, 5), (55, 5)])])
T = []
def t(n, ok): T.append(ok); print("PASS" if ok else "FAIL", n)
s0 = summarise(eval_routes(rt, bld, []))
t("U1 no omissions: all crossings are retained, own footprint excluded (10+10 m, 2 polygons)", s0["routes_crossing_retained"] == 1 and abs(s0["len_in_retained_m"] - 20) < 1e-9 and s0["routes_crossing_omitted"] == 0)
s1 = summarise(eval_routes(rt, bld, [3]))
t("U2 omit footprint 3: still counted, now as OMITTED (10 m), retained 10 m", abs(s1["len_in_omitted_m"] - 10) < 1e-9 and abs(s1["len_in_retained_m"] - 10) < 1e-9)
t("U3 full-set total independent of which footprints are omitted", abs(s0["len_in_any_full_m"] - s1["len_in_any_full_m"]) < 1e-9 and s0["routes_crossing_any_full"] == s1["routes_crossing_any_full"] == 1)
rt2 = gpd.GeoDataFrame({"cand_id": [1]}, geometry=[LineString([(5, 5), (8, 5)])])
s2 = summarise(eval_routes(rt2, bld, [2, 3]))
t("U4 route only inside its own footprint: zero crossings, no division error", s2["routes_crossing_any_full"] == 0 and s2["len_in_any_full_m"] == 0)
s3 = summarise(eval_routes(rt.iloc[0:0], bld, []))
t("U5 empty route set: zero routed, NaN ratio not an exception", s3["routed"] == 0 and s3["crossing_any_full_per_routed"] != s3["crossing_any_full_per_routed"])
print("tests:", len(T), "failed:", T.count(False)); sys.exit(0 if all(T) else 1)
