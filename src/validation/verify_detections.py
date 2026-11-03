"""verify_detections.py - spatial cross-check of detected building footprints and priority facilities (read-only).

There is NO building ground truth in this project (reference_buildings has 0 features; manual_building_labels is empty). So this script does
not report accuracy. It reports agreement with independent layers, and says which layer each number comes from:

  1. Priority facilities (4 targets plus the TGRAC alternative records): latitude/longitude from the geometry, the latitude/longitude stored in the
     TGRAC table where it exists (attribute-vs-geometry distance), inside the village boundary, inside a school-compound polygon, and distance to the
     nearest detected footprint and to the nearest Google Open Buildings v3 polygon. Verdict rule (fixed before looking at results):
       SUPPORTED     a detected footprint lies within FOOT_TOL_M of the point, or the point is inside a compound that contains a footprint
       CORROBORATED  SUPPORTED and an independent Google Open Buildings polygon lies within GOB_TOL_M
       UNSUPPORTED   otherwise (no footprint nearby: the coordinate, the detection or both may be wrong)
  2. Building candidates inside the boundary versus Google Open Buildings v3 (an independent ML product, itself imperfect, built from other imagery).
     A candidate "matches" if IoU >= IOU_MIN or one centroid lies inside the other polygon. Counts are PROXY agreement, not TP/FP against truth:
       proxy-TP = candidates with a match, proxy-FP = candidates with none, proxy-FN = reference polygons (confidence >= GOB_CONF) with no candidate.

usage: python src/validation/verify_detections.py --out outputs/verification
"""
import sys as _sys
from pathlib import Path as _P
_sys.path.insert(0, str(_P(__file__).resolve().parents[1]))
import scenario_names as SN

import argparse, json
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.strtree import STRtree

ROOT = Path(__file__).resolve().parents[2]
V = ROOT / "Siddipet" / "Damarakunta"
FOOT_TOL_M, GOB_TOL_M, IOU_MIN, GOB_CONF = 20.0, 30.0, 0.25, 0.70


def nearest(point, geoms, tree):
    i = int(tree.nearest(point))
    return i, float(point.distance(geoms[i]))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(ROOT / "outputs" / "verification"))
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    boundary = gpd.read_file(V / "study_area" / "damarakunta_boundary.gpkg").geometry.iloc[0]
    bld = gpd.read_file(V / "results" / "v8_instances" / "buildings_v8_full.gpkg", layer="buildings")
    gob = gpd.read_file(V / "reference" / "external" / "google_open_buildings_v3.gpkg")
    comp = gpd.read_file(V / "reference" / "school_compounds_utm44n.gpkg")
    fac = gpd.read_file(SN.FAC_LAYER, layer="priority_facilities")
    fac_all = gpd.read_file(SN.FAC_LAYER_ORIGINAL, layer="priority_facilities")
    alt = {"tgrac_health.gpkg": "HEALTH_ALT_health_layer", "tgrac_sub_centres.gpkg": "HEALTH_ALT_sub_centres_layer"}
    cad = gpd.read_file(V / "reference" / "damarakunta_cadastral_valid.gpkg").to_crs(32644)

    bld_in = bld[bld.geometry.centroid.within(boundary)].reset_index(drop=True)
    gob_in = gob[gob.geometry.centroid.within(boundary)].reset_index(drop=True)
    bg, gg = list(bld.geometry), list(gob.geometry)
    bt, gt = STRtree(bg), STRtree(gg)

    # ---------------------------------------------------------------- 1. facilities
    pts = [(r.facility_id, r.facility_name, r.facility_type, r.geometry, "priority_facilities.gpkg") for r in fac.itertuples()]
    for fn, label in alt.items():
        g = gpd.read_file(V / "reference" / fn)
        for r in g.itertuples():
            pts.append((label, getattr(r, "Facility_Name", label), "Sub Centre (alternative TGRAC record)", r.geometry, fn))
    attr_ll = {}
    for r_ in fac.itertuples():
        if getattr(r_, 'tgrac_lat', None) is not None and getattr(r_, 'tgrac_lat') == getattr(r_, 'tgrac_lat'):
            attr_ll[str(r_.facility_id)] = (r_.tgrac_lat, r_.tgrac_lon)
    for fn, label in alt.items():
        g = gpd.read_file(V / "reference" / fn)
        attr_ll[label] = (g.Latitude.iloc[0], g.Longitude.iloc[0])
    to_ll = gpd.GeoSeries([p[3] for p in pts], crs=32644).to_crs(4326)
    rows = []
    for (fid, name, ftype, geom, src), ll in zip(pts, to_ll):
        bi, bd = nearest(geom, bg, bt)
        gi, gd = nearest(geom, gg, gt)
        in_comp = [c.School_Name for c in comp.itertuples() if c.geometry.contains(geom)]
        n_in_comp = sum(1 for c in comp.itertuples() if c.geometry.contains(geom) for g in bg if g.centroid.within(c.geometry))
        supported = bd <= FOOT_TOL_M or (bool(in_comp) and n_in_comp > 0)
        verdict = "CORROBORATED" if supported and gd <= GOB_TOL_M else "SUPPORTED" if supported else "UNSUPPORTED"
        al = attr_ll.get(str(fid), (np.nan, np.nan))
        attr_dist = float(gpd.GeoSeries(gpd.points_from_xy([al[1]], [al[0]]), crs=4326).to_crs(32644).iloc[0].distance(geom)) if np.isfinite(al[0]) else np.nan
        rows.append(dict(facility_id=fid, name=name, type=ftype, source_layer=src, lat=round(ll.y, 6), lon=round(ll.x, 6),
                         table_lat=al[0], table_lon=al[1], table_vs_geometry_m=None if np.isnan(attr_dist) else round(attr_dist, 1),
                         in_boundary=bool(geom.within(boundary)), inside_school_compound=";".join(in_comp), footprints_in_compound=n_in_comp,
                         nearest_footprint_cand_id=int(bld.cand_id.iloc[bi]), nearest_footprint_class=bld.quality_class.iloc[bi], dist_to_nearest_footprint_m=round(bd, 1),
                         nearest_open_buildings_m=round(gd, 1), in_parcel=bool(cad.geometry.contains(geom).any()), verdict=verdict))
    F = pd.DataFrame(rows)
    F.to_csv(out / "facility_verification.csv", index=False)
    # audit trail of the exclusion (inputs/EXCLUSIONS.md): the only place the excluded record is kept
    ex = fac_all[fac_all.facility_id.astype(str) == SN.EXCLUDED_FACILITY_ID].geometry.iloc[0]
    exll = gpd.GeoSeries([ex], crs=32644).to_crs(4326).iloc[0]
    pd.DataFrame([dict(facility_id=SN.EXCLUDED_FACILITY_ID, name="Damarakunt-I (anganwadi)", lat=round(exll.y, 6), lon=round(exll.x, 6),
                       nearest_footprint_m=round(float(ex.distance(bg[int(bt.nearest(ex))])), 1), nearest_open_buildings_m=round(float(ex.distance(gg[int(gt.nearest(ex))])), 1),
                       status="EXCLUDED from planning layers, CSVs and maps at the project owner's request; see inputs/EXCLUSIONS.md")]).to_csv(out / "excluded_facilities.csv", index=False)

    # ---------------------------------------------------------------- 2. buildings vs Open Buildings (proxy agreement)
    ig = list(gob_in.geometry)
    it = STRtree(ig)
    res = []
    matched_gob = set()
    for r in bld_in.itertuples():
        best, who = 0.0, -1
        for j in it.query(r.geometry.buffer(5)):
            g = ig[int(j)]
            inter = r.geometry.intersection(g).area
            iou = inter / max(r.geometry.union(g).area, 1e-9)
            hit = iou >= IOU_MIN or r.geometry.centroid.within(g) or g.centroid.within(r.geometry)
            if hit and (iou > best or who < 0):
                best, who = iou, int(j)
        if who >= 0:
            matched_gob.add(who)
        res.append(dict(cand_id=int(r.cand_id), quality_class=r.quality_class, area_m2=round(r.geometry.area, 1), matched=who >= 0, best_iou=round(best, 3),
                        gob_confidence=None if who < 0 else float(gob_in.confidence.iloc[who])))
    R = pd.DataFrame(res)
    R.to_csv(out / "building_candidates_vs_open_buildings.csv", index=False)
    hi = gob_in[gob_in.confidence >= GOB_CONF]
    fn_idx = [i for i in hi.index if i not in matched_gob]
    gob_in.loc[fn_idx, ["confidence", "area_in_meters", "latitude", "longitude"]].to_csv(out / "open_buildings_unmatched_high_conf.csv", index=False)
    summ = []
    for cls, g in [("ALL", R)] + list(R.groupby("quality_class")):
        tp = int(g.matched.sum())
        summ.append(dict(group=cls, candidates=len(g), proxy_TP=tp, proxy_FP=len(g) - tp, proxy_agreement_rate=round(tp / max(len(g), 1), 3)))
    S = pd.DataFrame(summ)
    S.to_csv(out / "building_agreement_summary.csv", index=False)
    tpall = int(R.matched.sum())
    ref_n = len(hi)
    notes = dict(candidates_inside_boundary=len(bld_in), open_buildings_inside_boundary=len(gob_in), open_buildings_conf_ge_0_70=ref_n,
                 proxy_FN_reference_polygons_without_candidate=len(fn_idx), proxy_recall_like=round((ref_n - len(fn_idx)) / max(ref_n, 1), 3),
                 thresholds=dict(FOOT_TOL_M=FOOT_TOL_M, GOB_TOL_M=GOB_TOL_M, IOU_MIN=IOU_MIN, GOB_CONF=GOB_CONF),
                 caveat="Open Buildings v3 is an independent ML product, not ground truth. These are agreement counts, not accuracy.")
    json.dump(notes, open(out / "verification_summary.json", "w"), indent=1)

    md = ["# Detection and facility verification", "",
          "No building ground truth exists in this project, so nothing here is an accuracy figure. Agreement is with independent layers (TGRAC tables, school compounds, "
          "Google Open Buildings v3). Thresholds were fixed before the run: footprint within %g m, Open Buildings within %g m, IoU >= %g." % (FOOT_TOL_M, GOB_TOL_M, IOU_MIN), "",
          "## Facilities (latitude/longitude from the geometry)", "", F[["facility_id", "name", "lat", "lon", "table_vs_geometry_m", "inside_school_compound", "dist_to_nearest_footprint_m", "nearest_footprint_class", "nearest_open_buildings_m", "verdict"]].to_markdown(index=False), "",
          "## Building candidates inside the boundary versus Open Buildings v3 (proxy agreement)", "", S.to_markdown(index=False), "",
          "Reference polygons with confidence >= %.2f and no candidate (proxy false negatives): %d of %d (proxy recall-like %.2f). These include sheds, farm buildings and structures the project's extraction did not keep, so a low value does not by itself mean missed houses." % (GOB_CONF, len(fn_idx), ref_n, notes["proxy_recall_like"]), "",
          "Read these as: the share of candidates that another detector also sees (proxy-TP) and the share that only this project sees (proxy-FP, which may be real buildings Open Buildings missed). Neither measures real accuracy; that needs labelled buildings (Phase-II).", ""]
    (out / "verification_report.md").write_text("\n".join(md), encoding="utf-8")
    print(F[["facility_id", "lat", "lon", "dist_to_nearest_footprint_m", "verdict"]].to_string(index=False))
    print(S.to_string(index=False)); print(notes)


if __name__ == "__main__":
    main()
