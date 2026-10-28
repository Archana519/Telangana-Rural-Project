"""Evaluate ANY candidate/instance layer against manually traced reference roofs (separate from inference).
New file: leaves evaluate_vs_reference.py alone. Scores ONLY windows marked complete in window_status.json
(an untouched window is never scored as 'zero roofs'). Writes a new CSV named after the layer; never overwrites.
Usage: python scripts\\evaluate_layer_vs_reference.py --cands <gpkg> [--layer buildings] [--name v7]"""
import argparse, json, sys
from pathlib import Path
import geopandas as gpd, pandas as pd
from shapely.ops import unary_union

ap = argparse.ArgumentParser()
ap.add_argument("--cands", required=True)
ap.add_argument("--layer", default=None)
ap.add_argument("--name", default="layer")
ap.add_argument("--ref", default=r"D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\reference\digitize_windows.gpkg")
a = ap.parse_args()
REF = Path(a.ref)
CAND = Path(a.cands)
OUT = REF.parent / f"reference_evaluation_{a.name}.csv"
STATUS = REF.parent / "window_status.json"
CRS, MIN_HIT_M2 = "EPSG:32644", 5.0
if OUT.exists():
    sys.exit(f"{OUT} exists; rename it first")
if not STATUS.exists():
    sys.exit("window_status.json not found: commit at least one completed window in the digitizer first")
DONE = set(json.load(open(STATUS, encoding="utf-8"))["complete_windows"])
if not DONE:
    sys.exit("no window is marked complete")
print("Scoring only windows marked complete:", sorted(DONE))

win = gpd.read_file(REF, layer="windows").to_crs(CRS)
ref = gpd.read_file(REF, layer="reference_buildings").to_crs(CRS)
cand = (gpd.read_file(CAND, layer=a.layer) if a.layer else gpd.read_file(CAND)).to_crs(CRS)
ref["note"] = ref["note"].fillna("").astype(str)
ref["geometry"] = ref.geometry.make_valid()

def div(a, b):
    return round(a / b, 3) if b else float("nan")

rows = []
for _, w in win.iterrows():
    if str(w.window_id) not in DONE:
        print("skipping (not marked complete):", w.window_id); continue
    wp = w.geometry
    inwin = ref[ref.geometry.representative_point().within(wp)]
    is_ext = inwin.note.str.upper().str.contains("TRACED_EXTENT")
    ext = inwin[is_ext]
    E = unary_union(ext.geometry.tolist()).intersection(wp) if len(ext) else wp
    R = inwin[~is_ext].copy()
    n_unsure = int(R.note.str.lower().str.contains("unsure").sum())
    R["geometry"] = R.geometry.intersection(E)
    R = R[~R.geometry.is_empty & (R.geometry.area > 0)]
    P = cand[cand.intersects(E)].copy()
    P["geometry"] = P.geometry.intersection(E)
    P = P[~P.geometry.is_empty & (P.geometry.area > 0)]
    ru = unary_union(R.geometry.tolist()) if len(R) else None
    pu = unary_union(P.geometry.tolist()) if len(P) else None
    ra = ru.area if ru else 0.0
    pa = pu.area if pu else 0.0
    inter = ru.intersection(pu).area if (ru and pu) else 0.0
    union = ra + pa - inter
    det30 = det50 = 0
    for g in R.geometry:
        cov = g.intersection(pu).area / g.area if pu else 0.0
        det30 += cov >= 0.3
        det50 += cov >= 0.5
    matched = merged = roofs_in_merged = 0
    for g in P.geometry:
        hits = sum(1 for r in R.geometry if g.intersection(r).area >= MIN_HIT_M2)
        matched += hits >= 1
        if hits >= 2:
            merged += 1
            roofs_in_merged += hits
    rows.append(dict(window=w.window_id, role=w.role, extent_m2=round(E.area), n_ref=len(R), n_unsure=n_unsure,
                     n_pred_blobs=len(P), ref_area_m2=round(ra), pred_area_m2=round(pa),
                     pixel_iou=div(inter, union), pixel_precision=div(inter, pa), pixel_recall=div(inter, ra),
                     roofs_found_30=int(det30), roofs_found_50=int(det50),
                     roof_recall_30=div(det30, len(R)), blobs_matched=matched,
                     blobs_unmatched=len(P) - matched, blobs_merged=merged, roofs_in_merged=roofs_in_merged))
df = pd.DataFrame(rows)
df.to_csv(OUT, index=False)
pd.set_option("display.width", 250)
print(df.drop(columns="role").to_string(index=False))
t = df[["n_ref", "n_pred_blobs", "roofs_found_30", "blobs_matched", "blobs_unmatched", "blobs_merged",
        "roofs_in_merged"]].sum()
print("\nPooled over scored windows (small manual sample, one annotator; NOT a village-wide estimate):")
print(t.to_string())
print("Wrote:", OUT)
