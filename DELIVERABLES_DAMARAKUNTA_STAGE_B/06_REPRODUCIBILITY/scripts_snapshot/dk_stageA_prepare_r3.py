#!/usr/bin/env python
"""
dk_stageA_prepare_r3.py  (revision 3)  -  Telangana Rural Project, Damarakunta pilot, Stage A (data and candidate preparation)

WHAT IT DOES
  Reads existing project data (read-only), reconciles candidate IDs, runs internal consistency checks, and writes six NEW
  files into   <village>\\results\\run_20261029_01\\stageA\\
  It never runs a route planner, makes a map, or modifies / renames / moves / deletes any existing file.

SAFETY ORDER
  1. Preflight: required files, layers, columns, CRS, ID columns. Any problem -> stop, nothing created.
  2. Run folder already exists -> stop, nothing created.
  3. All checks and all output text are computed in memory. Any critical check FAIL -> stop, nothing created.
  4. Only then are the folders created (mkdir without exist_ok) and the files written (exclusive-create mode "x").
  Use --check-only to run steps 1-3 and print every result without creating anything.

WHAT IT DOES NOT CLAIM
  All checks are internal data-consistency checks. They do not verify that any building, road or facility exists or is
  correctly located, and they say nothing about legal access or imagery licensing.
"""
import argparse, hashlib, json, platform, sys
from datetime import datetime, timezone
from pathlib import Path
import re
import numpy as np
import pandas as pd
import geopandas as gpd
import pyogrio
from shapely.ops import unary_union

DEFAULT_PROJECT = r"D:\Telangana_Rural_Project"
DEFAULT_VILLAGE = r"D:\Telangana_Rural_Project\Siddipet\Damarakunta"
RUN_NAME = "run_20261029_01"
CRS_EPSG = 32644
MIN_AREA_M2 = 10.0                      # same value as the v1 house script's --min-area-m2 default
DEFAULT_CLASSES = ("PLAUSIBLE", "REVIEW")
SENSITIVITY_CLASSES = ("UNRESOLVED_MERGE",)
TIER = {"PLAUSIBLE": "A", "REVIEW": "B", "UNRESOLVED_MERGE": "C"}
THRESHOLDS_M = (10.0, 20.0)
# Expected values come from the Phase 3/4 audits and the 2026-10-29 read-only check. They are COMPARED, never assumed.
EXPECTED = dict(v8_buildings=278, footprints=165, routed=163, plausible=71, review_all=32, review_routed=30,
                merged=62, default_targets=101, outside_village_ids=13)
OUTSIDE13 = [48, 50, 51, 52, 53, 54, 55, 56, 58, 59, 60, 62, 64]
EXCLUDED2 = [189, 202]
THRESH_AUDIT = {"<=10": 48, "10-20": 24, ">20": 91}   # Phase 3 audit counts for the 163 routed targets (comparison only)
FP_LAYER, V8_LAYER, ROUTE_LAYER = "candidate_footprints", "buildings", "routes_network_aware"
REQ_SCRIPTS = ["plan_network_v2.py", "extract_buildings_v8.py", "plan_individual_house_network_v1.py"]
V8_COLS = ["cand_id", "bld_id", "comp_id", "piece", "quality_class", "area_m2", "est_roofs", "flags", "inside_village"]
FP_COLS = ["cand_id", "bld_id", "quality_class", "area_m2", "est_roofs", "flags", "inside_village", "house_route_id", "nearest_tgrac_road_distance_m"]
OUT_FILES = ["candidates_master.csv", "targets_default_ids.csv", "targets_merged_sensitivity_ids.csv",
             "inputs_manifest.csv", "config.json", "stageA_checks.txt"]     # stageA_checks.txt is written LAST (completion marker)
END_MARK = "END OF STAGE A CHECKS (file complete)"

CHECKS = []          # (status, name, detail); status in PASS / INFO / WARN / FAIL ; FAIL = critical, stops before any write
def chk(status, name, detail=""):
    CHECKS.append((status, name, detail))

def norm(x):
    s = str(x).strip()
    return str(int(float(s))) if re.fullmatch(r"-?\d+(\.0+)?", s) else s

def as_bool(s):
    return s.astype(str).str.strip().str.lower().isin(["true", "1", "1.0", "yes"])

def sha256(p, blk=1 << 20):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(blk), b""):
            h.update(b)
    return h.hexdigest()

def utc(ts):
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def ids_txt(s, n=30):
    s = sorted(s, key=lambda v: (not str(v).lstrip("-").isdigit(), int(v) if str(v).lstrip("-").isdigit() else 0, str(v)))
    return str(s[:n]) + (f" ... (+{len(s) - n} more)" if len(s) > n else "")

def set_check(name, a, b, la, lb, critical=True):
    """Compare two ID sets explicitly and report the actual differing IDs."""
    a, b = set(a), set(b)
    if a == b:
        chk("PASS", name, f"{la} == {lb} ({len(a)} IDs, identical IDs)")
    else:
        chk("FAIL" if critical else "WARN", name, f"{la} ({len(a)}) vs {lb} ({len(b)}): only in {la}: {ids_txt(a - b)}; only in {lb}: {ids_txt(b - a)}")

def id_quality(name, ser):
    """Null / duplicate cand_id check (critical)."""
    bad_null = int(ser.isna().sum()) + int(ser.astype(str).str.strip().str.lower().isin(["", "nan", "none"]).sum())
    n = ser.map(norm); dup = sorted(set(n[n.duplicated()]), key=str)
    chk("PASS" if bad_null == 0 else "FAIL", f"{name}: no null cand_id", f"{bad_null} null/blank")
    chk("PASS" if not dup else "FAIL", f"{name}: no duplicate cand_id", "none" if not dup else f"duplicates: {ids_txt(dup)}")

def early_gate():
    """Stop immediately (before any further processing or any write) if a critical check has already failed."""
    fails = [c for c in CHECKS if c[0] == "FAIL"]
    if fails:
        print("\n==== CRITICAL CHECK(S) FAILED ====")
        for s_, n_, d_ in CHECKS:
            if s_ in ("FAIL", "WARN"): print(f"[{s_}] {n_}" + (f" :: {d_}" if d_ else ""))
        print(f"\nSTOPPED: {len(fails)} critical check(s) failed. Nothing was created, changed or overwritten.")
        sys.exit(3)

def read_utm(path, layer=None):
    g = gpd.read_file(path, layer=layer)
    if g.crs is None:
        raise SystemExit(f"STOP: no CRS in {path} (layer {layer}); nothing was created.")
    native = g.crs.to_epsg()
    if native != CRS_EPSG:
        chk("WARN", f"CRS of {Path(path).name}:{layer}", f"native EPSG {native}; reprojected to {CRS_EPSG} in memory only")
        g = g.to_crs(CRS_EPSG)
    return g

def compare_tables(a, b, cols, atol=1e-9):
    out = {}
    for c in cols:
        x, y = a[c], b[c]
        if pd.api.types.is_numeric_dtype(x) and pd.api.types.is_numeric_dtype(y):
            same = np.isclose(x.astype(float).values, y.astype(float).values, rtol=0, atol=atol, equal_nan=True)
        else:
            same = (x.astype(str).values == y.astype(str).values)
        bad = list(a.index[~same])
        if bad:
            out[c] = bad
    return out

def preflight(items, csvs, roads_path):
    """Return a list of problems; reads only metadata/headers."""
    prob = []
    for label, path, layer, cols in items:
        if not Path(path).exists():
            prob.append(f"{label}: file missing: {path}"); continue
        try:
            layers = [l[0] for l in pyogrio.list_layers(path)]
            if layer not in layers:
                prob.append(f"{label}: layer '{layer}' not found in {path}; layers present: {layers}"); continue
            info = pyogrio.read_info(path, layer=layer)
        except Exception as e:
            prob.append(f"{label}: cannot open {path} ({e})"); continue
        miss = [c for c in cols if c not in list(info["fields"])]
        if miss: prob.append(f"{label}: required column(s) missing {miss}; columns present: {list(info['fields'])}")
        if not info.get("crs"): prob.append(f"{label}: layer has no CRS ({path})")
        if int(info.get("features", 0)) == 0: prob.append(f"{label}: layer has 0 features")
    if not Path(roads_path).exists():
        prob.append(f"TGRAC roads: file missing: {roads_path}")
    else:
        try:
            lay = pyogrio.list_layers(roads_path)[0][0]; info = pyogrio.read_info(roads_path, layer=lay)
            if not info.get("crs"): prob.append(f"TGRAC roads: no CRS ({roads_path})")
            if int(info.get("features", 0)) == 0: prob.append("TGRAC roads: 0 features")
        except Exception as e:
            prob.append(f"TGRAC roads: cannot open ({e})")
    for label, path, cols in csvs:
        if not Path(path).exists():
            prob.append(f"{label}: file missing: {path}"); continue
        try:
            have = list(pd.read_csv(path, nrows=0).columns)
        except Exception as e:
            prob.append(f"{label}: cannot read {path} ({e})"); continue
        miss = [c for c in cols if c not in have]
        if miss: prob.append(f"{label}: required column(s) missing {miss}; columns present: {have}")
    return prob

def main():
    ap = argparse.ArgumentParser(description="Stage A preparation (writes only new files in a new run folder)")
    ap.add_argument("--project-root", default=DEFAULT_PROJECT)
    ap.add_argument("--village-root", default=DEFAULT_VILLAGE)
    ap.add_argument("--run-name", default=RUN_NAME)
    ap.add_argument("--check-only", action="store_true", help="run every check and print results; create nothing")
    a = ap.parse_args()
    PR = Path(a.project_root); V = Path(a.village_root); RES = V / "results"; RUN = RES / a.run_name; OUT = RUN / "stageA"
    SCRIPTS = PR / "scripts"
    P_SELF = Path(sys.argv[0]).resolve() if sys.argv and sys.argv[0] not in ("", "-") else None

    # ---------------------------------------------------------------- 0. paths printed and verified (nothing created)
    print("Project root        :", PR)
    print("Village root        :", V)
    print("Scripts folder      :", SCRIPTS)
    print("This script         :", P_SELF)
    print("Run folder (target) :", RUN)
    try:
        V.relative_to(PR); under = True
    except ValueError:
        under = False
    stop = []
    if not under: stop.append(f"village root is not inside the project root: {V} vs {PR}")
    if not SCRIPTS.is_dir(): stop.append(f"scripts folder not found: {SCRIPTS}")
    for nm in REQ_SCRIPTS:
        ok = (SCRIPTS / nm).is_file(); print(f"  required script {nm:42s} {'FOUND' if ok else 'MISSING'}")
        if not ok: stop.append(f"required script missing: {SCRIPTS / nm}")
    if P_SELF and P_SELF.parent != SCRIPTS.resolve() and str(P_SELF.parent).lower() != str(SCRIPTS).lower():
        print(f"  note: this script is not located in {SCRIPTS} (it is in {P_SELF.parent}); allowed, recorded in the manifest")
    if RUN.exists():
        sys.exit(f"STOP: run folder already exists: {RUN}\nNothing was created, changed or overwritten. Choose --run-name <new name> or review the existing folder.")

    P_V8 = RES / "v8_instances" / "buildings_v8_full.gpkg"
    P_FP_CANON = RES / "final_output_validation_v4_1" / "candidate_footprints_for_review_v4_1.gpkg"
    P_FP_ALL = sorted(RES.glob("final_output_validation_v4_1*/candidate_footprints_for_review_v4_1.gpkg"))
    P_ROUTES = RES / "individual_house_network_v1" / "individual_house_network_v1.gpkg"
    P_STATUS = RES / "individual_house_network_v1" / "house_network_status.csv"
    P_MINAREA = RES / "individual_house_routing_v1" / "candidates_excluded_by_min_area_v1.csv"
    P_ROADS = V / "reference" / "tgrac_road_network.gpkg"

    # ---------------------------------------------------------------- 1. preflight: files, layers, columns, CRS
    stop += preflight([("v8 buildings", P_V8, V8_LAYER, V8_COLS), ("canonical footprints", P_FP_CANON, FP_LAYER, FP_COLS),
                       ("V1 network-aware routes", P_ROUTES, ROUTE_LAYER, ["cand_id"])],
                      [("V1 status table", P_STATUS, ["cand_id"]), ("min-area exclusion table", P_MINAREA, ["cand_id"])], P_ROADS)
    if stop:
        sys.exit("STOP: preflight failed; nothing was created.\n  - " + "\n  - ".join(stop))
    print("Preflight passed: all required files, layers, columns and CRS definitions are present.")

    # ---------------------------------------------------------------- read inputs (read-only)
    v8 = read_utm(P_V8, V8_LAYER); fp = read_utm(P_FP_CANON, FP_LAYER); rt = read_utm(P_ROUTES, ROUTE_LAYER)
    st = pd.read_csv(P_STATUS); ma = pd.read_csv(P_MINAREA)
    roads = read_utm(P_ROADS); ru = unary_union(list(roads.geometry))
    for nm, g in (("v8", v8), ("footprints", fp)):
        g["area_m2"] = pd.to_numeric(g["area_m2"], errors="coerce")
        chk("PASS" if g["area_m2"].notna().all() else "FAIL", f"{nm}: area_m2 numeric and non-null", f"{int(g['area_m2'].isna().sum())} bad values")
        chk("PASS" if g["quality_class"].notna().all() else "FAIL", f"{nm}: quality_class non-null", f"{int(g['quality_class'].isna().sum())} null")
    for nm, g in (("v8", v8), ("footprints", fp), ("V1 routes", rt), ("V1 status", st), ("min-area table", ma)):
        id_quality(nm, g["cand_id"]); g["cid"] = g["cand_id"].map(norm)
    chk("PASS" if v8["bld_id"].is_unique else "FAIL", "v8: bld_id unique", "")
    v8["inside_village_b"] = as_bool(v8["inside_village"])
    early_gate()      # duplicate/null IDs or bad numeric columns make the later ID reconciliation meaningless: stop now
    chk("PASS", "CRS", f"all spatial layers in EPSG:{CRS_EPSG} (native CRS differences, if any, are listed as WARN)")
    chk("PASS" if bool(fp.geometry.is_valid.all()) else "WARN", "footprint geometries valid", f"{int((~fp.geometry.is_valid).sum())} invalid")

    # ---------------------------------------------------------------- 2. compare the footprint copies
    chk("INFO", "canonical footprint file (provisional)", f"{P_FP_CANON} (the copy used by the Phase 3 audit)")
    fpi = fp.set_index("cid").sort_index(); copy_rows = []
    for p in P_FP_ALL:
        name = p.parent.name
        try:
            layers = [l[0] for l in pyogrio.list_layers(p)]
            g = read_utm(p, FP_LAYER); g["cid"] = g["cand_id"].map(norm); gi = g.set_index("cid").sort_index()
        except BaseException as e:
            if p == P_FP_CANON: raise
            chk("WARN", f"copy {name}", f"not readable, not used: {e}"); continue
        r = dict(copy=name, layers=",".join(layers), n=len(gi), crs=gi.crs.to_epsg(), sha16=sha256(p)[:16], is_canonical=(p == P_FP_CANON))
        if p == P_FP_CANON:
            copy_rows.append(r); continue
        if gi.index.has_duplicates:
            chk("FAIL", f"copy {name}: duplicate cand_id", ids_txt(set(gi.index[gi.index.duplicated()]))); copy_rows.append(r); continue
        same_ids = set(gi.index) == set(fpi.index); r["same_id_set"] = same_ids
        if not same_ids:
            set_check(f"copy {name}: ID set equals canonical", set(fpi.index), set(gi.index), "canonical", "copy", critical=True)
            copy_rows.append(r); continue
        gi = gi.loc[fpi.index]
        cols = [c for c in fpi.columns if c in gi.columns and c != "geometry"]
        r["columns_only_in_canonical"] = ",".join(c for c in fpi.columns if c not in gi.columns and c != "geometry")
        r["columns_only_in_copy"] = ",".join(c for c in gi.columns if c not in fpi.columns and c != "geometry")
        diffs = compare_tables(fpi, gi, cols)
        r["attribute_columns_differing"] = ";".join(f"{c}({len(v)} ids)" for c, v in diffs.items()) or "none"
        neq = []; maxsd = 0.0
        for cid_ in fpi.index:
            ga, gb = fpi.at[cid_, "geometry"], gi.at[cid_, "geometry"]
            if not ga.equals_exact(gb, 1e-6):
                neq.append(cid_); maxsd = max(maxsd, ga.symmetric_difference(gb).area)
        r["geometries_not_equal"] = len(neq); r["max_symdiff_area_m2"] = round(maxsd, 6)
        identical = (not diffs) and not neq and not r["columns_only_in_canonical"] and not r["columns_only_in_copy"]
        r["content_identical_to_canonical"] = identical
        if identical:
            chk("PASS", f"copy {name} vs canonical", "identical IDs, attributes and geometry; the SHA-256 differs only at container level (file metadata)")
        else:
            tier_aff = [c for c in ("quality_class", "inside_village", "area_m2") if c in diffs]
            why = []
            if diffs: why.append("attribute differences: " + "; ".join(f"{c} in IDs {ids_txt(v, 8)}" for c, v in diffs.items()))
            if neq: why.append(f"{len(neq)} geometries differ (IDs {ids_txt(neq, 8)}, largest symmetric difference {maxsd:.4f} m2)")
            if r["columns_only_in_canonical"] or r["columns_only_in_copy"]: why.append(f"column sets differ (canonical-only: {r['columns_only_in_canonical'] or '-'}; copy-only: {r['columns_only_in_copy'] or '-'})")
            note = ("TIER-AFFECTING columns differ (" + ",".join(tier_aff) + "): if you prefer this copy the default and sensitivity sets could change" if tier_aff
                    else "no tier-affecting column differs; the canonical copy is still used for all outputs")
            chk("WARN", f"copy {name} vs canonical", " | ".join(why) + " | " + note)
        copy_rows.append(r)
    copies_df = pd.DataFrame(copy_rows)

    # ---------------------------------------------------------------- 3. ID reconciliation (actual IDs, not only counts)
    v8i = v8.set_index("cid"); fp_ids = set(fp["cid"]); v8_ids = set(v8["cid"])
    chk("PASS" if len(v8) == EXPECTED["v8_buildings"] else "FAIL", "v8 buildings count", f"{len(v8)} (expected {EXPECTED['v8_buildings']})")
    chk("PASS" if len(fp) == EXPECTED["footprints"] else "FAIL", "footprint count", f"{len(fp)} (expected {EXPECTED['footprints']})")
    set_check("footprint IDs are a subset of v8 IDs", fp_ids & v8_ids, fp_ids, "footprints found in v8", "footprints")
    shared = [c for c in ("bld_id", "comp_id", "piece", "quality_class", "area_m2", "est_roofs", "flags", "inside_village") if c in fp.columns and c in v8.columns]
    fpx = fpi.loc[sorted(fp_ids & v8_ids)]
    attr_diff = compare_tables(fpx, v8i.loc[fpx.index], shared, atol=0.011)
    crit = {c: v for c, v in attr_diff.items() if c in ("bld_id", "quality_class", "inside_village")}
    minor = {c: v for c, v in attr_diff.items() if c not in crit}
    chk("PASS" if not crit else "FAIL", "footprint vs v8: bld_id, quality_class, inside_village agree", "agree for all footprints" if not crit else "; ".join(f"{c}: IDs {ids_txt(v, 10)}" for c, v in crit.items()))
    chk("PASS" if not minor else "WARN", "footprint vs v8: other attributes agree", "agree" if not minor else "; ".join(f"{c}: IDs {ids_txt(v, 10)}" for c, v in minor.items()))
    mismatch_ids = set(i for v in attr_diff.values() for i in v)

    n_in = int(v8["inside_village_b"].sum()); set_in = set(v8.loc[v8["inside_village_b"], "cid"])
    chk("INFO", "v8 inside_village counts", f"True={n_in}, False={len(v8) - n_in}")
    set_check("inside_village=True in v8 equals footprint IDs", set_in, fp_ids, "v8 inside-village", "footprints")
    bad13 = [i for i in OUTSIDE13 if not ((str(i) in v8_ids) and (not bool(v8i.at[str(i), "inside_village_b"])) and (str(i) not in fp_ids))]
    chk("PASS" if not bad13 else "FAIL", "13 listed IDs: in v8, inside_village=False, not in footprints",
        f"all {len(OUTSIDE13)} confirmed: {OUTSIDE13}" if not bad13 else f"failing IDs: {bad13}")
    chk("INFO", "basis for outside-village exclusion", "recorded v8 attribute inside_village=False. The code that built the footprint layer was NOT read, so the exact filter used is not confirmed.")

    routed = set(rt.loc[rt.geometry.notna() & ~rt.geometry.is_empty, "cid"])
    chk("PASS" if len(rt) == len(routed) else "FAIL", "V1 route layer: no null/empty route geometry", f"{len(rt)} rows, {len(routed)} usable")
    chk("PASS" if len(routed) == EXPECTED["routed"] else "FAIL", "routed count", f"{len(routed)} (expected {EXPECTED['routed']})")
    set_check("routed IDs are footprint IDs", routed & fp_ids, routed, "routed found in footprints", "routed")
    set_check("V1 status-table IDs equal routed IDs", set(st["cid"]), routed, "status table", "routed")
    unrouted = fp_ids - routed
    set_check("unrouted footprints are exactly IDs 189 and 202", unrouted, {str(i) for i in EXCLUDED2}, "unrouted footprints", "{189,202}")

    # ---------------------------------------------------------------- 4. min-area table: actual ID column and IDs 189/202
    chk("INFO", "min-area table", f"ID column used: 'cand_id' (verified present); columns: {list(ma.columns)[:20]}; rows: {len(ma)}")
    ma_ids = set(ma["cid"])
    set_check("min-area table IDs equal unrouted footprints", ma_ids, unrouted, "min-area table", "unrouted footprints")
    set_check("min-area table IDs are exactly {189,202}", ma_ids, {str(i) for i in EXCLUDED2}, "min-area table", "{189,202}")
    ma_i = ma.set_index("cid"); ma_rows = []
    for i in EXCLUDED2:
        c = str(i); in_tab, in_fp, in_v8_, rout = c in ma_ids, c in fp_ids, c in v8_ids, c in routed
        farea = float(fpi.at[c, "area_m2"]) if in_fp else np.nan
        tarea = float(pd.to_numeric(ma_i.at[c, "area_m2"], errors="coerce")) if (in_tab and "area_m2" in ma.columns) else np.nan
        qc = fpi.at[c, "quality_class"] if in_fp else ""
        ok = in_tab and in_fp and in_v8_ and (not rout) and farea < MIN_AREA_M2
        ma_rows.append(dict(cand_id=i, in_min_area_table=in_tab, in_footprint_layer=in_fp, in_v8=in_v8_, routed_in_v1=rout,
                            table_area_m2=tarea, footprint_area_m2=farea, quality_class=qc))
        chk("PASS" if ok else "FAIL", f"ID {i}: in min-area table, footprint layer and v8; not routed; area < {MIN_AREA_M2:g} m2",
            f"table={in_tab}, footprint={in_fp}, v8={in_v8_}, routed={rout}, table area={tarea}, footprint area={farea}, class={qc}")
        if in_tab and in_fp and not np.isnan(tarea) and abs(tarea - farea) > 0.011:
            chk("WARN", f"ID {i}: table area vs footprint area", f"{tarea} vs {farea}")
    ma_df = pd.DataFrame(ma_rows)

    # ---------------------------------------------------------------- 5. tiers and scenario sets
    cnt = fp["quality_class"].value_counts().to_dict()
    chk("INFO", "footprint quality classes", str(cnt))
    unknown = sorted(set(fp["quality_class"]) - set(TIER))
    chk("PASS" if not unknown else "FAIL", "no unrecognised quality classes", str(unknown))
    for k, ek in (("PLAUSIBLE", "plausible"), ("REVIEW", "review_all"), ("UNRESOLVED_MERGE", "merged")):
        chk("PASS" if cnt.get(k) == EXPECTED[ek] else "FAIL", f"{k} footprints", f"{cnt.get(k)} (expected {EXPECTED[ek]})")
    base = fp["cid"].isin(set_in) & (fp["area_m2"] >= MIN_AREA_M2)
    default_ids = set(fp.loc[base & fp["quality_class"].isin(DEFAULT_CLASSES), "cid"])
    sens_ids = set(fp.loc[base & fp["quality_class"].isin(SENSITIVITY_CLASSES), "cid"])
    n_pl = sum(fpi.at[c, "quality_class"] == "PLAUSIBLE" for c in default_ids); n_rv = sum(fpi.at[c, "quality_class"] == "REVIEW" for c in default_ids)
    chk("PASS" if len(default_ids) == EXPECTED["default_targets"] and n_pl == EXPECTED["plausible"] and n_rv == EXPECTED["review_routed"] else "FAIL",
        "default target counts (rule-based)", f"{len(default_ids)} = {n_pl} PLAUSIBLE + {n_rv} REVIEW (expected {EXPECTED['default_targets']} = {EXPECTED['plausible']} + {EXPECTED['review_routed']})")
    chk("PASS" if len(sens_ids) == EXPECTED["merged"] else "FAIL", "merged-sensitivity count", f"{len(sens_ids)} (expected {EXPECTED['merged']})")
    set_check("default targets equal routed minus merged (actual IDs)", default_ids, routed - sens_ids, "default", "routed minus merged")
    set_check("default + merged equal routed (actual IDs)", default_ids | sens_ids, routed, "default union merged", "routed")
    set_check("merged targets equal all UNRESOLVED_MERGE footprints", sens_ids, set(fp.loc[fp["quality_class"] == "UNRESOLVED_MERGE", "cid"]), "merged targets", "UNRESOLVED_MERGE footprints")
    chk("PASS" if not (default_ids & sens_ids) else "FAIL", "default and sensitivity sets disjoint", ids_txt(default_ids & sens_ids) if default_ids & sens_ids else "disjoint")
    chk("INFO", "tier policy", "Tier A PLAUSIBLE and Tier B REVIEW (flagged) = default scenario; Tier C UNRESOLVED_MERGE = separately labelled sensitivity scenario, never counted as verified individual houses. est_roofs is a model estimate, not a house count.")
    if "170" in v8_ids:
        chk("INFO", "ID 170", f"v8 class {v8i.at['170', 'quality_class']}, flags '{v8i.at['170', 'flags']}', in default set: {'170' in default_ids}")

    # ---------------------------------------------------------------- 6. distances to road GEOMETRY (not network)
    v8["dist_poly_to_tgrac_road_geom_m"] = v8.geometry.distance(ru).round(2)
    d_by = v8.set_index("cid")["dist_poly_to_tgrac_road_geom_m"]
    dd = (fpi["nearest_tgrac_road_distance_m"].astype(float) - d_by.loc[fpi.index]).abs()
    chk("PASS" if dd.max() < 0.5 else "WARN", "stored footprint road distance vs recomputed", f"max abs difference {dd.max():.2f} m")
    rd = d_by.loc[sorted(routed & v8_ids, key=int)]
    n10, n20, nfar = int((rd <= 10).sum()), int(((rd > 10) & (rd <= 20)).sum()), int((rd > 20).sum())
    chk("INFO", "routed targets by distance to TGRAC road GEOMETRY (not network)",
        f"<=10 m: {n10}; 10-20 m: {n20}; >20 m: {nfar} (Phase 3 audit: {THRESH_AUDIT}). 10 m and 20 m are kept as separate scenarios; none is chosen here.")

    # ---------------------------------------------------------------- 7. master table with explicit reasons
    rows = []
    for _, r in v8.sort_values("cand_id").iterrows():
        c = r["cid"]; inf = c in fp_ids; q = r["quality_class"]; fr = fpi.loc[c] if inf else None
        tier = TIER.get(q, "UNKNOWN"); status, reason, basis, flag, note = "", "", "", False, ""
        if not inf:
            if not r["inside_village_b"]:
                status, reason, basis = "EXCLUDED", "OUTSIDE_VILLAGE_FLAG_IN_V8", "RECORDED_ATTRIBUTE (v8 inside_village=False; footprint-builder filter code not read)"
            else:
                status, reason, basis, flag = "EXCLUDED", "INSIDE_VILLAGE_BUT_NOT_IN_FOOTPRINT_LAYER", "UNEXPLAINED", True
        elif float(r["area_m2"]) < MIN_AREA_M2:
            intab = c in ma_ids
            status, reason = "EXCLUDED", f"BELOW_MIN_AREA_{MIN_AREA_M2:g}M2"
            basis = "RECORDED_TABLE (candidates_excluded_by_min_area_v1.csv)" if intab else "RULE_ONLY (not listed in the min-area table)"
            flag = not intab
        elif tier == "C":
            status, reason, basis = "SENSITIVITY_ONLY", "UNRESOLVED_MERGE_NOT_COUNTED_AS_INDIVIDUAL_HOUSE", "RULE (v8 quality_class; project decision)"
        elif tier in ("A", "B"):
            status, reason, basis = "INCLUDED_DEFAULT", "", "RULE (quality_class PLAUSIBLE/REVIEW, in footprint layer, area >= min)"
            if tier == "B": note = "REVIEW tier: low-confidence or small candidate; included but flagged"
        else:
            status, reason, basis, flag = "EXCLUDED", "UNRECOGNISED_QUALITY_CLASS", "UNEXPLAINED", True
        if c in mismatch_ids:
            flag = True; note = (note + "; " if note else "") + "footprint layer and v8 attributes differ"
        if "ISOLATED" in str(r.get("flags", "")):
            note = (note + "; " if note else "") + "ISOLATED flag (far from other candidates)"
        rows.append(dict(cand_id=int(c) if c.lstrip("-").isdigit() else c, bld_id=r["bld_id"], comp_id=r.get("comp_id"), piece=r.get("piece"), quality_class=q, tier=tier,
                         flags=r.get("flags"), area_m2=round(float(r["area_m2"]), 2), est_roofs_model_estimate=r.get("est_roofs"),
                         inside_village=bool(r["inside_village_b"]), in_footprint_layer=inf,
                         house_route_id_positional_info_only=(fr["house_route_id"] if inf else ""), routed_in_v1=c in routed,
                         dist_poly_to_tgrac_road_geom_m=r["dist_poly_to_tgrac_road_geom_m"],
                         road_proximity_le10m=bool(r["dist_poly_to_tgrac_road_geom_m"] <= 10), road_proximity_le20m=bool(r["dist_poly_to_tgrac_road_geom_m"] <= 20),
                         scenario_default=status == "INCLUDED_DEFAULT", scenario_merged_sensitivity=status == "SENSITIVITY_ONLY",
                         inclusion_status=status, exclusion_or_flag_reason=reason, reason_basis=basis, flag_unexplained=flag, notes=note))
    master = pd.DataFrame(rows)
    chk("INFO", "master table status counts", str(master["inclusion_status"].value_counts().to_dict()))
    nflag = int(master["flag_unexplained"].sum())
    chk("PASS" if nflag == 0 else "FAIL", "no candidate is unexplained or inconsistent", f"{nflag}: {ids_txt(set(master.loc[master.flag_unexplained, 'cand_id'].astype(str)))}")
    chk("PASS" if len(master) == len(v8) else "FAIL", "master has one row per v8 candidate", f"{len(master)} rows vs {len(v8)}")
    set_check("master default flag equals default set", set(master.loc[master.scenario_default, "cand_id"].astype(str)), default_ids, "master", "default set")
    set_check("master merged flag equals sensitivity set", set(master.loc[master.scenario_merged_sensitivity, "cand_id"].astype(str)), sens_ids, "master", "sensitivity set")
    tcols = ["cand_id", "bld_id", "quality_class", "tier", "flags", "area_m2", "est_roofs_model_estimate", "dist_poly_to_tgrac_road_geom_m",
             "road_proximity_le10m", "road_proximity_le20m", "routed_in_v1"]
    tdef = master[master.scenario_default][tcols].reset_index(drop=True); tdef.insert(0, "scenario", "default_individual_candidates")
    tsen = master[master.scenario_merged_sensitivity][tcols].reset_index(drop=True); tsen.insert(0, "scenario", "merged_groups_sensitivity_only")

    # ---------------------------------------------------------------- 8. manifest and config (read-only hashing)
    man = []
    def add(role, p):
        p = Path(p)
        if p.exists():
            man.append(dict(role=role, path=str(p), bytes=p.stat().st_size, modified_utc=utc(p.stat().st_mtime), sha256=sha256(p)))
    add("v8 building candidates", P_V8)
    for p in P_FP_ALL: add("footprint copy" + (" (canonical, provisional)" if p == P_FP_CANON else ""), p)
    add("V1 house routes", P_ROUTES); add("V1 status table", P_STATUS); add("min-area exclusion table", P_MINAREA); add("TGRAC road layer", P_ROADS)
    for nm in REQ_SCRIPTS: add("script (read only)", SCRIPTS / nm)
    if P_SELF and P_SELF.exists(): add("this script", P_SELF)
    man_df = pd.DataFrame(man)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    others = [r for r in copy_rows if not r.get("is_canonical")]
    if others and all(r.get("content_identical_to_canonical") is True for r in others):
        canon_note = (f"CHOSEN because it is the copy used by the Phase 3 audit. In this run the {len(others)} other copy/copies were compared and "
                      "found identical in IDs, attributes and geometry (as compared by this script); container-level file hashes differ.")
    else:
        canon_note = "PROVISIONAL: copy used by the Phase 3 audit; the other copies are NOT all identical - see stageA_checks.txt for the comparison"
    cfg = dict(run_id=a.run_name, stage="A", script_revision=3, created_utc=now, project_root=str(PR), village_root=str(V), scripts_folder=str(SCRIPTS),
               output_dir=str(OUT), crs_epsg=CRS_EPSG,
               parameters=dict(min_area_m2=MIN_AREA_M2, default_classes=list(DEFAULT_CLASSES), sensitivity_classes=list(SENSITIVITY_CLASSES),
                               tier_map=TIER, road_proximity_thresholds_m=list(THRESHOLDS_M),
                               threshold_note="10 m and 20 m are separate experimental scenarios; no final choice is made. Distances are to TGRAC road GEOMETRY, not to a verified road network."),
               canonical_footprint_file=str(P_FP_CANON), canonical_selection=canon_note,
               expected_counts=EXPECTED,
               provenance_status=dict(imagery_source="UNRESOLVED", imagery_capture_date="UNRESOLVED", imagery_licence_for_publication="UNRESOLVED",
                                      imagery_permission_status="UNRESOLVED", model_weights_location="UNRESOLVED",
                                      tgrac_layer_licence="UNRESOLVED (DATA_SOURCES.md covers Angadi Kistapur only and records TGRAC licences as 'Not stated')",
                                      note="No claim is made that the imagery or TGRAC layers are licensed for publication."),
               software=dict(python=platform.python_version(), geopandas=gpd.__version__, pandas=pd.__version__, numpy=np.__version__, pyogrio=pyogrio.__version__),
               evidence_level="Internal data-consistency checks only. No field, official or independent verification of buildings, roads or facilities.",
               outputs=OUT_FILES)

    # ---------------------------------------------------------------- 9. gate: any critical FAIL stops BEFORE anything is written
    cnts = pd.Series([c[0] for c in CHECKS]).value_counts().to_dict()
    fails = [c for c in CHECKS if c[0] == "FAIL"]
    if fails or a.check_only:
        print("\n==== CHECK RESULTS ====")
        for s, n, d in CHECKS:
            if s != "PASS" or a.check_only: print(f"[{s}] {n}" + (f" :: {d}" if d else ""))
        print("Summary:", cnts)
        if fails:
            print(f"\nSTOPPED: {len(fails)} critical check(s) failed. Nothing was created, changed or overwritten.")
            sys.exit(3)
        print("\nCHECK-ONLY: no critical failure. Nothing was created.")
        sys.exit(0)

    # ---------------------------------------------------------------- 10. checks text (complete text built in memory)
    L = [f"STAGE A CHECKS - {a.run_name} (script revision 3)", f"created_utc: {now}", f"project_root: {PR}", f"village_root: {V}", f"scripts_folder: {SCRIPTS}", "",
         "SCOPE: internal data-consistency checks on existing files. They do not verify real-world buildings, roads, facilities, legal access or imagery licensing.",
         "Imagery source, capture date, licence and permission, model-weight location, and TGRAC licence are UNRESOLVED.", "",
         f"SUMMARY: {cnts}", "FAIL = critical (stops before writing; none occurred in this run). WARN = needs your decision.", "", "== CHECKS =="]
    for s, n, d in CHECKS: L.append(f"[{s}] {n}" + (f" :: {d}" if d else ""))
    L += ["", "== FOOTPRINT COPY COMPARISON =="]; L.append(copies_df.to_string(index=False) if len(copies_df) else "(none)")
    L += ["", "== MIN-AREA TABLE vs IDS 189 and 202 =="]; L.append(ma_df.to_string(index=False))
    L += ["", "== CANDIDATES FLAGGED (unexplained or inconsistent) =="]
    fl = master[master.flag_unexplained]
    L.append(fl[["cand_id", "quality_class", "inclusion_status", "exclusion_or_flag_reason", "reason_basis", "notes"]].to_string(index=False) if len(fl) else "(none)")
    L += ["", "== THE 14 REVIEWED IDS (13 outside-village + 170) =="]
    L.append(master[master.cand_id.isin(OUTSIDE13 + [170])][["cand_id", "quality_class", "inside_village", "in_footprint_layer", "routed_in_v1", "inclusion_status", "exclusion_or_flag_reason", "reason_basis"]].to_string(index=False))
    L += ["", "== ID RECONCILIATION SUMMARY =="]
    L += [f"footprints {len(fp_ids)} | routed {len(routed)} | unrouted {ids_txt(unrouted)} | default {len(default_ids)} | merged-sensitivity {len(sens_ids)} | default+merged==routed: {(default_ids | sens_ids) == routed}"]
    L += ["", END_MARK]
    texts = {"candidates_master.csv": master.to_csv(index=False), "targets_default_ids.csv": tdef.to_csv(index=False),
             "targets_merged_sensitivity_ids.csv": tsen.to_csv(index=False), "inputs_manifest.csv": man_df.to_csv(index=False),
             "config.json": json.dumps(cfg, indent=2, default=str), "stageA_checks.txt": "\n".join(L) + "\n"}

    # ---------------------------------------------------------------- 11. write: new folders, exclusive-create files, checks file LAST
    written = []
    try:
        RUN.mkdir(parents=False, exist_ok=False); OUT.mkdir(parents=False, exist_ok=False)
        for n in OUT_FILES:
            with open(OUT / n, "x", newline="", encoding="utf-8") as f: f.write(texts[n])
            written.append(n)
    except BaseException as e:
        print(f"\nWRITE FAILED: {type(e).__name__}: {e}")
        print("Nothing existing was overwritten and nothing was deleted. Partial output (if any) was LEFT IN PLACE for you to review:")
        for n in written: print(f"  complete file: {OUT / n} ({(OUT / n).stat().st_size} bytes)")
        if OUT.exists():
            for p in sorted(OUT.iterdir()):
                if p.name not in written: print(f"  possibly incomplete file: {p} ({p.stat().st_size} bytes)")
        print(f"The stageA folder is incomplete unless all six files exist and stageA_checks.txt ends with '{END_MARK}'.")
        print("A re-run will refuse (folder exists). Choose --run-name <new name>, or review/remove the partial folder yourself.")
        sys.exit(4)

    # ---------------------------------------------------------------- 12. post-write verification (read-only, all six files)
    problems = []
    names_on_disk = {p.name for p in OUT.iterdir()}
    if names_on_disk != set(OUT_FILES): problems.append(f"files in stageA differ from the six expected: {sorted(names_on_disk ^ set(OUT_FILES))}")
    for n in OUT_FILES:
        p = OUT / n
        if not p.is_file() or p.stat().st_size == 0: problems.append(f"{n}: missing or empty"); continue
        if p.read_bytes() != texts[n].encode("utf-8"): problems.append(f"{n}: bytes on disk differ from the content prepared in memory")
    try:
        m2 = pd.read_csv(OUT / "candidates_master.csv"); d2 = pd.read_csv(OUT / "targets_default_ids.csv")
        s2 = pd.read_csv(OUT / "targets_merged_sensitivity_ids.csv"); mf2 = pd.read_csv(OUT / "inputs_manifest.csv")
        cj = json.loads((OUT / "config.json").read_text(encoding="utf-8"))
        if len(m2) != len(v8) or m2["cand_id"].nunique() != len(v8): problems.append(f"candidates_master.csv: {len(m2)} rows / {m2['cand_id'].nunique()} unique IDs, expected {len(v8)}")
        if {str(i) for i in d2["cand_id"]} != default_ids: problems.append("targets_default_ids.csv: IDs differ from the default set")
        if {str(i) for i in s2["cand_id"]} != sens_ids: problems.append("targets_merged_sensitivity_ids.csv: IDs differ from the sensitivity set")
        if set(d2["cand_id"]) & set(s2["cand_id"]): problems.append("default and sensitivity files share IDs")
        if set(d2["quality_class"]) - set(DEFAULT_CLASSES) or set(s2["quality_class"]) - set(SENSITIVITY_CLASSES): problems.append("unexpected quality_class in a target file")
        vc = m2["inclusion_status"].value_counts().to_dict()
        if vc.get("INCLUDED_DEFAULT") != len(default_ids) or vc.get("SENSITIVITY_ONLY") != len(sens_ids): problems.append(f"master inclusion_status counts differ: {vc}")
        if len(mf2) != len(man_df): problems.append("inputs_manifest.csv row count differs")
        if cj.get("run_id") != a.run_name or cj.get("script_revision") != 3: problems.append("config.json run_id/script_revision differ")
        if not (OUT / "stageA_checks.txt").read_text(encoding="utf-8").rstrip().endswith(END_MARK): problems.append("stageA_checks.txt end marker missing")
    except Exception as e:
        problems.append(f"read-back error: {type(e).__name__}: {e}")
    print("Stage A complete. New files:")
    for n in OUT_FILES: print(f"  {OUT / n}  ({(OUT / n).stat().st_size} bytes)")
    print("Check summary:", cnts)
    for s, n, d in CHECKS:
        if s == "WARN": print(f"  [WARN] {n} :: {d}")
    print("Read-back verification:", "OK (all six files byte-identical to the prepared content; IDs and counts re-checked)" if not problems else "PROBLEMS: " + "; ".join(problems))
    print("No existing file was modified. No planner was run.")
    if problems:
        print("Nothing was deleted or altered. Review the files above before using them.")
        sys.exit(5)

if __name__ == "__main__":
    main()
