#!/usr/bin/env python
"""dk_boundary_crs_compare_v1.py - READ-ONLY, CRS-aware comparison of the stored raw TGRAC boundary response with the saved study-area boundary.

Method
 1. CRS of the raw response is READ from the JSON (top-level spatialReference.wkid / latestWkid, and any spatialReference inside a geometry).
    If absent or contradictory the script stops (no guessing).
 2. Raw ESRI rings are converted to shapely polygons by ESRI ring orientation (clockwise = exterior, counter-clockwise = hole),
    and ALSO by the rule used in save_damarakunta_boundary.py (first ring = exterior, the rest = holes); both are reported.
 3. Saved GPKG is read with its declared CRS. Both geometries are transformed to EPSG:32644 (areas, distances) and EPSG:4326 (bounds sanity check)
    only if their own CRS differs.
 4. Reported: bounds, area (km2), symmetric-difference / intersection / union area, IoU, two-way Hausdorff distance, exact / tolerance equality and vertex-wise
    maximum coordinate difference when vertex counts match.
Nothing is edited; a NEW output folder is created and an existing one is never overwritten. This compares the saved file with the stored response only:
it does not show that TGRAC is authoritative or current.
"""
import argparse, hashlib, json, sys, datetime
from pathlib import Path
import numpy as np, pandas as pd, geopandas as gpd
from pyproj import CRS
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union
import shapely

TOL_EXACT, TOL_FINE = 1e-6, 0.01     # m (in EPSG:32644)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def esri_to_shapely(rings):
    """ESRI orientation rule: clockwise ring = exterior, counter-clockwise = hole."""
    ext, holes = [], []
    for r in rings:
        lr = shapely.LinearRing(r)
        (holes if lr.is_ccw else ext).append(Polygon(r) if not lr.is_ccw else Polygon(r))
    if not ext:
        sys.exit("stopping: no clockwise (exterior) ring in the raw geometry; orientation rule not applicable")
    polys = []
    for e in ext:
        hs = [h.exterior.coords[:] for h in holes if e.contains(h.representative_point())]
        polys.append(Polygon(e.exterior.coords[:], hs))
    return polys[0] if len(polys) == 1 else MultiPolygon(polys)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=r"D:\Telangana_Rural_Project\docs\village_template\damarakunta_boundary_tgrac_query.json")
    ap.add_argument("--gpkg", default=r"D:\Telangana_Rural_Project\Siddipet\Damarakunta\study_area\damarakunta_boundary.gpkg")
    ap.add_argument("--layer", default="village_boundary")
    ap.add_argument("--out", default=r"D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\run_20261029_01\stageB\_boundary_crs_compare_v1")
    ap.add_argument("--village", default="DAMARAKUNTA")
    a = ap.parse_args()
    out, jp, gp = Path(a.out), Path(a.json), Path(a.gpkg)
    if out.exists():
        sys.exit(f"stopping: {out} exists (never overwritten)")
    for p in (jp, gp):
        if not p.exists():
            sys.exit(f"stopping: missing {p}")
    watched = {jp: sha(jp), gp: sha(gp)}

    data = json.loads(jp.read_text(encoding="utf-8"))
    F = []

    def add(i, c, o, v=""):
        assert c in ("VERIFIED_FACT", "HYPOTHESIS", "UNRESOLVED")
        F.append(dict(finding_id=i, classification=c, observation=o, value=v))

    # ---- 1. declared CRS of the raw response
    top = data.get("spatialReference") or {}
    feats = data.get("features", [])
    if len(feats) != 1:
        sys.exit(f"stopping: expected exactly 1 feature in the stored response, found {len(feats)}")
    feat = feats[0]; geo = feat.get("geometry") or {}
    gsr = geo.get("spatialReference") or {}
    wk = [top.get("latestWkid"), top.get("wkid")] + [gsr.get("latestWkid"), gsr.get("wkid")]
    declared = {int(x) for x in wk if x is not None}
    if not declared:
        sys.exit("stopping: raw response declares no spatialReference (top-level or geometry-level); not guessing")
    if len(declared) > 1:
        sys.exit(f"stopping: raw response declares conflicting WKIDs {sorted(declared)}")
    raw_epsg = declared.pop(); raw_crs = CRS.from_epsg(raw_epsg)
    add("B1", "VERIFIED_FACT", f"raw response declares spatialReference wkid={top.get('wkid')} latestWkid={top.get('latestWkid')} (geometry-level spatialReference: {gsr or 'absent'}); geometryType={data.get('geometryType')}; adopted CRS EPSG:{raw_epsg} ({raw_crs.name}), units {raw_crs.axis_info[0].unit_name}", raw_epsg)
    attrs = feat.get("attributes", {})
    if str(attrs.get("Village", "")).strip().upper() != a.village:
        sys.exit(f"stopping: feature Village={attrs.get('Village')!r} is not {a.village}")
    rings = geo.get("rings", [])
    raw_esri = esri_to_shapely(rings)
    raw_savescript = Polygon(rings[0], rings[1:])      # rule used by save_damarakunta_boundary.py
    add("B2", "VERIFIED_FACT", f"raw rings: {len(rings)}; ESRI-orientation interpretation -> {raw_esri.geom_type} with {len(raw_esri.interiors) if raw_esri.geom_type == 'Polygon' else 'n/a'} hole(s); save-script rule (first ring exterior, rest holes) -> {raw_savescript.geom_type}; the two interpretations are {'identical' if raw_esri.equals_exact(raw_savescript, TOL_EXACT) else 'DIFFERENT'} (max abs diff test, tol {TOL_EXACT})", len(rings))

    # ---- 2. saved boundary
    sv = gpd.read_file(gp, layer=a.layer)
    if sv.crs is None:
        sys.exit("stopping: saved boundary has no CRS")
    if len(sv) != 1:
        sys.exit(f"stopping: saved boundary has {len(sv)} records, expected 1")
    sv_crs = sv.crs; sv_geom = sv.geometry.iloc[0]
    add("B3", "VERIFIED_FACT", f"saved boundary {gp.name} layer '{a.layer}': CRS {sv_crs.to_string()} ({sv_crs.name}), records {len(sv)}, geometry {sv_geom.geom_type}, valid={sv_geom.is_valid}; save script constructs GeoDataFrame with crs='EPSG:32644' and passes the raw coordinates through unchanged (no reprojection)", sv_crs.to_epsg())

    # ---- 3. common CRS
    def to(g, src, dst):
        if CRS.from_user_input(src) == CRS.from_user_input(dst):
            return g
        return gpd.GeoSeries([g], crs=src).to_crs(dst).iloc[0]
    raw32 = to(raw_esri, raw_crs, "EPSG:32644"); sv32 = to(sv_geom, sv_crs, "EPSG:32644")
    raw4 = to(raw_esri, raw_crs, "EPSG:4326"); sv4 = to(sv_geom, sv_crs, "EPSG:4326")
    same_crs = CRS.from_user_input(raw_crs) == CRS.from_user_input(sv_crs)
    M = {}
    M["raw_crs"] = f"EPSG:{raw_epsg}"; M["saved_crs"] = sv_crs.to_string(); M["declared_crs_equal"] = same_crs
    M["raw_bounds_native"] = [round(x, 4) for x in raw_esri.bounds]; M["saved_bounds_native"] = [round(x, 4) for x in sv_geom.bounds]
    M["raw_bounds_32644"] = [round(x, 4) for x in raw32.bounds]; M["saved_bounds_32644"] = [round(x, 4) for x in sv32.bounds]
    M["raw_bounds_4326"] = [round(x, 7) for x in raw4.bounds]; M["saved_bounds_4326"] = [round(x, 7) for x in sv4.bounds]
    M["raw_area_km2"] = raw32.area / 1e6; M["saved_area_km2"] = sv32.area / 1e6
    M["raw_area_m2"] = raw32.area; M["saved_area_m2"] = sv32.area
    M["area_diff_m2"] = sv32.area - raw32.area
    sd = raw32.symmetric_difference(sv32); it = raw32.intersection(sv32); un = raw32.union(sv32)
    M["sym_diff_area_m2"] = sd.area; M["sym_diff_area_km2"] = sd.area / 1e6; M["intersection_area_km2"] = it.area / 1e6; M["union_area_km2"] = un.area / 1e6
    M["iou"] = it.area / un.area if un.area else float("nan")
    M["hausdorff_m"] = float(max(shapely.hausdorff_distance(raw32, sv32), shapely.hausdorff_distance(sv32, raw32)))
    M["equals_exact_tol0"] = bool(raw32.equals_exact(sv32, 0)); M[f"equals_exact_tol{TOL_EXACT}"] = bool(raw32.equals_exact(sv32, TOL_EXACT))
    M[f"equals_exact_tol{TOL_FINE}"] = bool(raw32.equals_exact(sv32, TOL_FINE)); M["topological_equals"] = bool(raw32.equals(sv32))
    nr, ns = shapely.get_num_coordinates(raw32), shapely.get_num_coordinates(sv32)
    M["vertices_raw"], M["vertices_saved"] = int(nr), int(ns)
    if nr == ns:
        M["max_abs_vertex_diff_m"] = float(np.abs(shapely.get_coordinates(raw32) - shapely.get_coordinates(sv32)).max())
    else:
        M["max_abs_vertex_diff_m"] = "vertex counts differ"
    M["raw_SHAPE_Area_attr_m2"] = attrs.get("SHAPE_Area"); M["raw_SHAPE_Length_attr_m"] = attrs.get("SHAPE_Length")
    M["raw_computed_perimeter_m"] = raw32.length
    sa = attrs.get("SHAPE_Area")
    M["SHAPE_Area_minus_computed_m2"] = (sa - raw32.area) if sa is not None else None
    # attribute carry-over
    for k_raw, k_sv in (("Village_Code", "tgrac_village_code"), ("DMV_Code", "tgrac_dmv_code")):
        M[f"attr_{k_raw}_raw"] = attrs.get(k_raw)
        M[f"attr_{k_raw}_saved"] = sv[k_sv].iloc[0] if k_sv in sv.columns else "column absent"
    M["raw_geometry_valid"] = bool(raw_esri.is_valid); M["saved_geometry_valid"] = bool(sv_geom.is_valid)

    # ---- 4. findings
    add("B4", "VERIFIED_FACT", f"declared CRS equal (raw EPSG:{raw_epsg} vs saved {sv_crs.to_epsg()}): {same_crs}. Bounds in EPSG:32644 - raw {M['raw_bounds_32644']}, saved {M['saved_bounds_32644']}; in EPSG:4326 - raw {M['raw_bounds_4326']}, saved {M['saved_bounds_4326']}", "")
    add("B5", "VERIFIED_FACT", f"area (EPSG:32644): raw {M['raw_area_km2']:.6f} km2, saved {M['saved_area_km2']:.6f} km2, diff {M['area_diff_m2']:.6f} m2; symmetric difference {M['sym_diff_area_m2']:.6f} m2; intersection {M['intersection_area_km2']:.6f} km2; IoU {M['iou']:.9f}; two-way Hausdorff {M['hausdorff_m']:.6f} m", M["sym_diff_area_m2"])
    add("B6", "VERIFIED_FACT", f"equality: exact(tol 0) {M['equals_exact_tol0']}; exact(tol {TOL_EXACT} m) {M[f'equals_exact_tol{TOL_EXACT}']}; exact(tol {TOL_FINE} m) {M[f'equals_exact_tol{TOL_FINE}']}; topological {M['topological_equals']}; vertices raw {nr} / saved {ns}; max vertex coordinate difference {M['max_abs_vertex_diff_m']}", "")
    add("B7", "VERIFIED_FACT", f"raw feature attribute SHAPE_Area {sa} vs computed planar area in the declared CRS {raw32.area:.6f} m2 (difference {M['SHAPE_Area_minus_computed_m2']}); a match supports that the declared CRS is the one the attribute area was computed in", "")
    match = M[f"equals_exact_tol{TOL_FINE}"] and M["sym_diff_area_m2"] < 1.0 and same_crs
    add("B8", "VERIFIED_FACT" if match else "UNRESOLVED",
        ("the saved geometry MATCHES the stored raw TGRAC response within 0.01 m (same declared CRS, symmetric difference < 1 m2)" if match else
         "the saved geometry does NOT demonstrably match the stored raw response within the stated tolerance: inspect B4-B6"), "")
    add("B9", "HYPOTHESIS", "the earlier comparison reported degrees because it set/transformed one side to EPSG:4326 and compared against the raw metre coordinates (CRS mismatch in the comparison, not in the data files); its symmetric-difference and equality outputs are superseded by B5/B6. (Reading of the earlier output; the earlier comparison script was not inspected here.)", "")
    add("U1", "UNRESOLVED", "B8 compares a saved file with a stored response only. It does not show that TGRAC's village polygon is authoritative, current or legally definitive; the cadastral overlap (97.81% boundary coverage, 0.79% cadastral area outside) is a cross-check, not proof. The query was not re-run, so whether the live service still returns the same geometry is not tested.", "")
    Fd = pd.DataFrame(F)

    # ---- write
    out.mkdir(parents=True)
    pd.DataFrame([dict(metric=k, value=str(v)) for k, v in M.items()]).to_csv(out / "boundary_crs_compare_metrics.csv", index=False)
    Fd.to_csv(out / "boundary_crs_compare_findings.csv", index=False)
    src = [("raw_json", str(jp), watched[jp]), ("saved_gpkg", str(gp), watched[gp]),
           ("method", "see script docstring", ""), ("script", Path(__file__).name, sha(Path(__file__))),
           ("run", datetime.datetime.now().isoformat(timespec="seconds"), ""),
           ("source_query_url_from_verify_script", "https://tgrac.telangana.gov.in/arcgis/rest/services/AdministrativeInfoSystem_Folder/Administrative_Information_System/MapServer/27/query (where UPPER(Village)='DAMARAKUNTA', returnGeometry=true, f=json; no inSR/outSR in the script, so the service's native SR applies)", "")]
    pd.DataFrame(src, columns=["item", "value", "sha256"]).to_csv(out / "inputs_and_method.csv", index=False)
    changed = [str(p) for p, h in watched.items() if sha(p) != h]
    pd.DataFrame([dict(check="inputs unchanged (sha256 before/after)", status="FAIL" if changed else "PASS", detail=f"{len(watched)} files")]).to_csv(out / "readonly_proof.csv", index=False)
    for _, r in Fd.iterrows():
        print(f"[{r.classification}] {r.finding_id}: {r.observation}")
    print("\ninputs unchanged:", not changed); print("output:", out)
    sys.exit(1 if changed else 0)


if __name__ == "__main__":
    main()
