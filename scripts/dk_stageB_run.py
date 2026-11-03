#!/usr/bin/env python
"""dk_stageB_run.py - Stage B executor for Damarakunta (ONE run = one scenario x slope x cost x facilities setting).

WHAT IT DOES (and does not do)
  * Reads Stage A outputs, the existing planner (plan_network_v2.py, UNMODIFIED, imported as a module) and read-only inputs.
  * Plans (a) the four priority facilities first, then (b) the Stage A house targets (S1 = 101 default IDs, or S2 = 163 =
    default + 62 UNRESOLVED_MERGE) onto roads UNION facility routes, using the planner's own two-stage generate-and-select
    algorithm with shared-edge credit. A second planner call on the same houses with REFERENCE ROADS ONLY gives the
    roads-only reference (this is the V1-equivalent configuration) and the independent / straight-line baselines.
  * Classifies every attachment (ROAD / FACILITY_ROUTE / HOUSE_ROUTE), builds a cell-level attachment graph, checks cycles,
    shared-cell connectivity and proper crossings that share no grid cell, and does shared-edge accounting.
  * Computes post-hoc geometric impact PROXIES (footprints, cadastral parcels, school compounds, land cover, slope).
    They are not ownership, legal access, passability or field-verified quantities.
  * Writes ONLY into a new run folder  <village>\\results\\<stageA run>\\stageB\\<run_key>\\  (exclusive creation, never
    overwrites). Existing project files are only read. Costs are ordinal model units (NOT INR).
  * Exit codes: 0 all acceptance tests pass (INFO/WARN allowed) | 1 run folder exists | 2 preflight failure (nothing written)
                | 4 run finished but >=1 post-run test FAILED | 5 read-back verification failed.
"""
import argparse, hashlib, importlib.util, json, math, os, platform, subprocess, sys, time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

CRS = "EPSG:32644"
VERSION = "dk_stageB_run v1.0"
EXPECTED_PLANNER_SHA = "d00ea92028101131627b8592e3df2c33ff350efac9b1de09f9b64cdd56ef70a4"
EXPECTED_COST_C0_SHA = "911ebeb1860aa49f7a701e28e54850a009dff365a11b564dfc42602043b4888e"
LAND_COST_C0 = {10: 8.0, 20: 5.0, 30: 3.0, 40: 6.0, 50: 2.0, 60: 4.0}
C1_PROVISIONAL = {10: 8.0, 20: 5.0, 30: 3.0, 40: 6.0, 50: 3.0, 60: 4.0}   # built-up = grass; PROVISIONAL, pending user approval
SLOPE_MAX_DEG, SLOPE_WEIGHT = 10.0, 4.0
FAC_IDENTITY = {
    "36181600902": "ATTRIBUTE_ONLY_SCHOOL_LAYER_NOT_INDEPENDENTLY_CONFIRMED",
    "36181600903": "ATTRIBUTE_ONLY_SCHOOL_LAYER_NOT_INDEPENDENTLY_CONFIRMED",
    "HEALTH_8734223673": "IDENTITY_UNRESOLVED_TWO_TGRAC_RECORDS_SAME_NIN_ID_235.7M_APART",
    "1702300": "UNVERIFIED_ANGANWADI_COORDINATES_4_DECIMALS",
}
LIMITATIONS = [
    "All building candidates are model-derived and unverified; routes are planning alternatives, not roads, not construction advice.",
    "Costs are ordinal model units from a land-cover table plus a slope term; they are NOT INR and not construction cost.",
    "Slope: 10 m raster is a bilinear resample of a slope computed (Sobel) from a ~30 m DEM that was itself bilinearly resampled; it is not genuine 10 m terrain detail.",
    "Reference roads (TGRAC layer) may be incomplete; only road cells inside the valid village grid are planner goals; attachment is model connectivity, not a verified physical junction.",
    "Cadastral polygons were assembled by a downloader that placed all rings of a feature in one Polygon; the repaired copy is a shapely make_valid result. Parcel counts are crossings of parcel units, not ownership or legal access.",
    "Facility identities and coordinates are taken from source layers and are not field-verified (see FAC_IDENTITY flags).",
    "Imagery source/date/licence, model-weight location and TGRAC data licence are unresolved.",
    "No field validation, legal access, real passability, construction savings or accessibility improvement is claimed.",
]


# ------------------------------------------------------------------------------------------------ helpers
def sha256_file(p, blk=1 << 20):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(blk), b""):
            h.update(b)
    return h.hexdigest()


def truth(v):
    return str(v).strip().lower() in {"true", "1", "1.0", "yes", "y"}


def stratum(d):
    return "<=10m" if d <= 10 else (">10-20m" if d <= 20 else ">20m")


def jsonable(o):
    if isinstance(o, dict):
        return {str(k): jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple, set)):
        return [jsonable(x) for x in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, float) and not math.isfinite(o):
        return None
    return o


class Checks:
    def __init__(self):
        self.rows = []

    def add(self, tid, status, name, detail=""):
        self.rows.append(dict(test_id=tid, status=status, name=name, detail=str(detail)))

    def ok(self, tid, cond, name, detail="", fail="FAIL"):
        self.add(tid, "PASS" if cond else fail, name, detail)
        return bool(cond)

    def n(self, status):
        return sum(1 for r in self.rows if r["status"] == status)

    def df(self):
        return pd.DataFrame(self.rows, columns=["test_id", "status", "name", "detail"])


def git_info(project_root):
    out = {}
    try:
        out["commit"] = subprocess.run(["git", "-C", project_root, "rev-parse", "HEAD"], capture_output=True, text=True, timeout=30).stdout.strip() or None
        st = subprocess.run(["git", "-C", project_root, "status", "--porcelain"], capture_output=True, text=True, timeout=60).stdout
        out["dirty_files_count"] = len([l for l in st.splitlines() if l.strip()])
        out["dirty_files_sample"] = st.splitlines()[:25]
    except Exception as e:  # git may be missing
        out["error"] = repr(e)
    return out


def load_planner(path):
    spec = importlib.util.spec_from_file_location("plan_network_v2_stageB", str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def components(cells, w2):
    """8-connected components of a set of padded grid indices. Returns (label dict cell->id, sizes list), id 1 = largest."""
    cells = set(cells)
    nb = (-1, 1, -w2, w2, -w2 - 1, -w2 + 1, w2 - 1, w2 + 1)
    seen, comps = set(), []
    for s in sorted(cells):
        if s in seen:
            continue
        st, comp = [s], []
        seen.add(s)
        while st:
            u = st.pop()
            comp.append(u)
            for o in nb:
                v = u + o
                if v in cells and v not in seen:
                    seen.add(v)
                    st.append(v)
        comps.append(comp)
    comps.sort(key=lambda c: (-len(c), min(c)))
    lab = {}
    for i, c in enumerate(comps, 1):
        for u in c:
            lab[u] = i
    return lab, [len(c) for c in comps]


class DSU:
    def __init__(self):
        self.p = {}

    def find(self, x):
        self.p.setdefault(x, x)
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[rb] = ra


# ------------------------------------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project-root", default=r"D:\Telangana_Rural_Project")
    ap.add_argument("--village-root", default=None)
    ap.add_argument("--stagea-run", default="run_20261029_01")
    ap.add_argument("--planner", default=None, help="default <project>\\scripts\\plan_network_v2.py")
    ap.add_argument("--scenario", choices=["S1", "S2"], required=True)
    ap.add_argument("--facilities", choices=["on", "off"], default="on")
    ap.add_argument("--slope-limit-deg", type=float, default=25.0)
    ap.add_argument("--cost-scenario", choices=["C0", "C1"], default="C0")
    ap.add_argument("--c1-land-cost-json", default=None, help='JSON {"10":8,...}; default C1_PROVISIONAL (built-up=3.0) - pending approval')
    ap.add_argument("--building-quality", default="PLAUSIBLE,REVIEW,UNRESOLVED_MERGE")
    ap.add_argument("--building-mult", type=float, default=4.0)
    ap.add_argument("--roads-only-reference", choices=["on", "off"], default="on")
    ap.add_argument("--length-only-baseline", choices=["on", "off"], default="on")
    ap.add_argument("--cadastral", default=None, help="default reference\\damarakunta_cadastral_valid.gpkg (make_valid copy)")
    ap.add_argument("--cadastral-original", default=None)
    ap.add_argument("--v1-dir", default=None)
    ap.add_argument("--label", default="")
    ap.add_argument("--expect-s1", type=int, default=101)
    ap.add_argument("--expect-merged", type=int, default=62)
    ap.add_argument("--expect-facilities", type=int, default=4)
    ap.add_argument("--allow-planner-change", action="store_true")
    ap.add_argument("--snap-m", type=float, default=30.0)
    ap.add_argument("--max-search-m", type=float, default=1500.0)
    ap.add_argument("--attach-tol-m", type=float, default=15.0)
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--corridor-m", type=float, default=20.0)
    ap.add_argument("--corridor-mults", type=float, nargs="+", default=[3.0, 8.0])
    ap.add_argument("--max-overlap", type=float, default=0.8)
    ap.add_argument("--passes", type=int, default=2)
    ap.add_argument("--corner-cut", choices=["forbid", "allow"], default="forbid")
    ap.add_argument("--check-only", action="store_true", help="preflight + reconciliation only; writes nothing")
    a = ap.parse_args()

    t_start = time.time()
    proj = Path(a.project_root)
    root = Path(a.village_root) if a.village_root else proj / "Siddipet" / "Damarakunta"
    C = Checks()
    LOG = []

    def log(*x):
        s = " ".join(str(v) for v in x)
        LOG.append(s)
        print(s, flush=True)

    # ---------- paths
    P = dict(
        planner=Path(a.planner) if a.planner else proj / "scripts" / "plan_network_v2.py",
        buildings=root / "results" / "v8_instances" / "buildings_v8_full.gpkg",
        roads=root / "reference" / "tgrac_road_network.gpkg",
        cost=root / "aligned" / "damarakunta_cost_surface_10m.tif",
        worldcover=root / "aligned" / "damarakunta_worldcover_10m.tif",
        blocked=root / "aligned" / "damarakunta_prohibited_mask_10m.tif",
        slope=root / "aligned" / "damarakunta_slope_10m.tif",
        fac=root / "reference" / "damarakunta_priority_facilities.gpkg",
        compounds=root / "reference" / "school_compounds_utm44n.gpkg",
        cad=Path(a.cadastral) if a.cadastral else root / "reference" / "damarakunta_cadastral_valid.gpkg",
        cad0=Path(a.cadastral_original) if a.cadastral_original else root / "reference" / "damarakunta_cadastral.gpkg",
    )
    sa = root / "results" / a.stagea_run / "stageA"
    SA = {k: sa / f for k, f in dict(master="candidates_master.csv", s1="targets_default_ids.csv", merged="targets_merged_sensitivity_ids.csv",
                                     manifest="inputs_manifest.csv", config="config.json", checks="stageA_checks.txt").items()}
    v1dir = Path(a.v1_dir) if a.v1_dir else root / "results" / "individual_house_network_v1"
    cost_tag = a.cost_scenario
    run_key = f"{a.scenario}_{'fac' if a.facilities == 'on' else 'nofac'}_{cost_tag}_s{a.slope_limit_deg:g}" + (f"_{a.label}" if a.label else "")
    stageB_root = root / "results" / a.stagea_run / "stageB"
    out = stageB_root / run_key

    # ---------- PREFLIGHT (nothing is written in this block)
    log(f"== {VERSION} | run_key={run_key} | check_only={a.check_only}")
    missing = [f"{k}: {v}" for k, v in {**{k: v for k, v in P.items() if k not in ("cad0",)}, **SA}.items() if not Path(v).exists()]
    if C.ok("PRE-01", not missing, "required inputs exist", "; ".join(missing) or "all present"):
        pass
    else:
        for m in missing:
            log("MISSING:", m)
        return finish_preflight_fail(C, LOG)
    sha_planner = sha256_file(P["planner"])
    if sha_planner == EXPECTED_PLANNER_SHA:
        C.add("PRE-02", "PASS", "planner SHA-256 equals the reviewed copy", sha_planner)
    elif a.allow_planner_change:
        C.add("PRE-02", "WARN", "planner differs from the reviewed copy (allowed by flag)", sha_planner)
    else:
        C.add("PRE-02", "FAIL", "planner differs from the reviewed copy - my code review no longer applies", sha_planner)
        return finish_preflight_fail(C, LOG)

    import geopandas as gpd
    import rasterio
    from rasterio.features import rasterize
    from shapely.geometry import LineString, Point
    from shapely.ops import nearest_points, unary_union
    from shapely.strtree import STRtree

    master = pd.read_csv(SA["master"], dtype={"cand_id": str})
    need = {"cand_id", "quality_class", "tier", "dist_poly_to_tgrac_road_geom_m"}
    if not C.ok("PRE-03", need <= set(master.columns), "Stage A master has required columns", str(sorted(need - set(master.columns)))):
        return finish_preflight_fail(C, LOG)
    s1_ids = pd.read_csv(SA["s1"], dtype={"cand_id": str}).cand_id.tolist()
    mg_ids = pd.read_csv(SA["merged"], dtype={"cand_id": str}).cand_id.tolist()
    S1, MG = set(s1_ids), set(mg_ids)
    ok = C.ok("PRE-04", len(s1_ids) == len(S1) == a.expect_s1, "S1 default IDs: count, uniqueness", f"rows={len(s1_ids)} unique={len(S1)} expected={a.expect_s1}")
    ok &= C.ok("PRE-05", len(mg_ids) == len(MG) == a.expect_merged, "merged-sensitivity IDs: count, uniqueness", f"rows={len(mg_ids)} unique={len(MG)} expected={a.expect_merged}")
    ok &= C.ok("PRE-06", not (S1 & MG), "S1 and merged sets are disjoint", f"overlap={len(S1 & MG)}")
    S2 = S1 | MG
    ok &= C.ok("PRE-07", len(S2) == a.expect_s1 + a.expect_merged, "S2 = S1 + merged distinct IDs", f"S2={len(S2)}")
    mi = master.set_index("cand_id")
    ok &= C.ok("PRE-08", S2 <= set(mi.index) and mi.index.is_unique, "all S2 IDs exist once in the Stage A master", f"missing={len(S2 - set(mi.index))}")
    if S2 <= set(mi.index):
        qd = mi.loc[sorted(S1), "quality_class"]
        qm = mi.loc[sorted(MG), "quality_class"]
        ok &= C.ok("PRE-09", set(qd.unique()) <= {"PLAUSIBLE", "REVIEW"} and set(qm.unique()) == {"UNRESOLVED_MERGE"}, "S1 classes in {PLAUSIBLE,REVIEW}; merged all UNRESOLVED_MERGE",
                   f"S1={qd.value_counts().to_dict()} merged={qm.value_counts().to_dict()}")
    bld_all = gpd.read_file(P["buildings"], layer="buildings")
    ok &= C.ok("PRE-10", bld_all.crs is not None and bld_all.crs.to_epsg() == 32644, "v8 buildings CRS is EPSG:32644", str(bld_all.crs))
    bld_all = bld_all.to_crs(CRS)
    bld_all["cand_key"] = bld_all.cand_id.astype(int).astype(str)
    inside = bld_all.inside_village.map(truth)
    elig = bld_all[inside & (pd.to_numeric(bld_all.area_m2, errors="coerce") >= 10.0)]
    ok &= C.ok("PRE-11", set(elig.cand_key) == S2, "v8 eligible set (inside_village and area>=10) equals S2", f"eligible={len(elig)} S2={len(S2)} sym.diff={len(set(elig.cand_key) ^ S2)}")
    ok &= C.ok("PRE-12", bld_all.cand_key.is_unique and int(bld_all.cand_id.astype(int).max()) <= 9999, "v8 cand_id unique and <= 9999 (planner key C####)")
    fac = gpd.read_file(P["fac"], layer="priority_facilities")
    ok &= C.ok("PRE-13", len(fac) == a.expect_facilities and fac.facility_id.is_unique and fac.crs is not None and fac.crs.to_epsg() == 32644,
               "priority facilities: count, unique IDs, EPSG:32644", f"n={len(fac)}")
    if P["cost"].exists():
        sc = sha256_file(P["cost"])
        C.add("PRE-14", "PASS" if sc == EXPECTED_COST_C0_SHA else "INFO", "baseline cost raster SHA-256 vs the value seen in G0", sc)
    ok &= C.ok("PRE-15", not out.exists(), "run folder does not exist yet", str(out), fail="FAIL")
    if not ok:
        return finish_preflight_fail(C, LOG, exit_code=(1 if out.exists() else 2))
    if a.check_only:
        print(C.df().to_string(index=False))
        log("CHECK-ONLY: nothing written. Preflight PASS.")
        return 0

    # ---------- create run folder (exclusive) ----------
    stageB_root.mkdir(parents=True, exist_ok=True)       # parent only; the run folder itself must be new
    os.mkdir(out)
    written = []

    def wbytes(name, data):
        p = out / name
        with open(p, "xb") as f:
            f.write(data)
        written.append((name, data))
        return p

    def wcsv(name, df):
        return wbytes(name, df.to_csv(index=False, lineterminator="\n").encode("utf-8"))

    def wjson(name, obj):
        return wbytes(name, json.dumps(jsonable(obj), indent=2).encode("utf-8"))

    # ---------- cost raster for the scenario ----------
    cost_path = P["cost"]
    c1_table = None
    if a.cost_scenario == "C1":
        c1_table = dict(C1_PROVISIONAL)
        if a.c1_land_cost_json:
            c1_table = {int(k): float(v) for k, v in json.loads(Path(a.c1_land_cost_json).read_text(encoding="utf-8")).items()}
        with rasterio.open(P["worldcover"]) as w_src, rasterio.open(P["slope"]) as s_src:
            wc0 = w_src.read(1)
            sl0r = s_src.read(1).astype(float)
            prof = w_src.profile.copy()
            vs = np.isfinite(sl0r) & (sl0r != s_src.nodata) & (sl0r >= 0) & (sl0r <= 90)
            c = np.full(wc0.shape, np.nan, dtype=np.float64)
            for k, v in c1_table.items():
                c[wc0 == k] = v
            vl = np.isin(wc0, list(c1_table)) & vs
            c[vl] += np.clip(sl0r, 0, SLOPE_MAX_DEG)[vl] / SLOPE_MAX_DEG * SLOPE_WEIGHT
            c[~vs] = np.nan
            c[wc0 == 80] = np.nan
            c[wc0 == 0] = np.nan
            prof.update(dtype="float32", count=1, nodata=-9999.0, compress="lzw")
        cost_path = out / "cost_surface_C1.tif"
        with rasterio.open(cost_path, "w", **prof) as dst:
            dst.write(np.where(np.isfinite(c), c, -9999.0).astype(np.float32), 1)
        written.append(("cost_surface_C1.tif", cost_path.read_bytes()))
        log("C1 cost raster written (separate output; baseline raster untouched):", cost_path, "table:", c1_table)

    # ---------- world (planner's own load_world) ----------
    pn = load_planner(P["planner"])
    wa = argparse.Namespace(v4_script="", blocked=str(P["blocked"]), slope=str(P["slope"]), slope_limit_deg=a.slope_limit_deg,
                            water_class=None, builtup_class=None, cost=str(cost_path), worldcover=str(P["worldcover"]), builtup_mult=1.0,
                            buildings=str(P["buildings"]), buildings_layer="buildings", building_quality=a.building_quality,
                            building_mult=a.building_mult, roads=str(P["roads"]), corner_cut=a.corner_cut)
    W = pn.load_world(wa)
    grid, road_union, road_cells = W["grid"], W["road_union"], W["road_cells"]
    H, Wd, T = W["H"], W["W"], W["T"]
    w2 = grid.W2
    cr = W["constraints_resolved"]
    C.ok("RUN-01", cr.get("slope_limit_deg") == a.slope_limit_deg and cr.get("slope_limit_source") == "--slope-limit-deg",
         "slope limit resolved from the explicit argument (no V4 fallback)", f"{cr.get('slope_limit_deg')} via {cr.get('slope_limit_source')}")
    # penalty mask replicated independently (must equal the planner's count)
    bq = [x.strip() for x in a.building_quality.split(",") if x.strip()]
    bsub = bld_all[bld_all.quality_class.isin(bq)]
    bm = rasterize([(g, 1) for g in bsub.geometry], out_shape=(H, Wd), transform=T, fill=0, all_touched=False, dtype="uint8").astype(bool) if a.building_mult != 1.0 else np.zeros((H, Wd), bool)
    C.ok("RUN-02", int(bm.sum()) == int(W["check"].get("building_cells_penalised", 0)), "replicated penalty mask equals planner's building_cells_penalised",
         f"mine={int(bm.sum())} planner={W['check'].get('building_cells_penalised')}")

    def arr(path):
        with rasterio.open(path) as s:
            x = s.read(1).astype(float)
            if s.nodata is not None:
                x[x == s.nodata] = np.nan
            return x
    wc_arr, sl_arr = arr(P["worldcover"]), arr(P["slope"])
    sl0 = np.nan_to_num(sl_arr, nan=0.0)

    def rc(i):
        r, c = divmod(i, w2)
        return r - 1, c - 1

    # ---------- targets ----------
    sel_ids = S1 if a.scenario == "S1" else S2
    hs = elig[elig.cand_key.isin(sel_ids)].copy()
    hs["cid"] = hs.cand_id.astype(int)
    hs = hs.sort_values("cid")
    C.ok("RUN-03", len(hs) == len(sel_ids) and list(hs.cid) == sorted(hs.cid), "scenario target set built, ascending cand_id", f"{len(hs)} of {len(sel_ids)}")
    v1map = {}
    if (v1dir / "house_network_status.csv").exists():
        v1s = pd.read_csv(v1dir / "house_network_status.csv", dtype={"cand_id": str, "house_route_id": str})
        v1map = dict(zip(v1s.cand_id, v1s.house_route_id))
    targets_h, tinfo = [], {}
    for _, row in hs.iterrows():
        cid = int(row.cid)
        key = f"C{cid:04d}"
        pt = nearest_points(row.geometry, road_union)[0]
        d = float(mi.loc[str(cid), "dist_poly_to_tgrac_road_geom_m"])
        origin = "DEFAULT" if str(cid) in S1 else "MERGED_SENS"
        targets_h.append(dict(id=key, kind="HOUSE_CANDIDATE", pt=pt, weight=1.0, cand_id=cid))
        tinfo[key] = dict(planner_key=key, cand_id=cid, v1_house_id=v1map.get(str(cid), ""), origin=origin, quality_class=row.quality_class,
                          tier=mi.loc[str(cid), "tier"], area_m2=float(row.area_m2), dist_to_road_m=d, stratum=stratum(d), x=pt.x, y=pt.y)
    key_of_cand = {t["cand_id"]: t["id"] for t in targets_h}
    cand_of_key = {v: k for k, v in key_of_cand.items()}
    fac_t, finfo = [], {}
    for _, f in fac.sort_values("facility_id").iterrows():
        fid = str(f.facility_id)
        fac_t.append(dict(id=fid, kind="FACILITY", pt=f.geometry, weight=1.0))
        finfo[fid] = dict(facility_id=fid, facility_name=f.facility_name, facility_type=f.facility_type, source=f.source,
                          identity_status=FAC_IDENTITY.get(fid, "UNSPECIFIED"), x=f.geometry.x, y=f.geometry.y)
    PP = dict(attach_tol_m=a.attach_tol_m, max_search_m=a.max_search_m, snap_m=a.snap_m, k=a.k, corridor_m=a.corridor_m,
              corridor_mults=a.corridor_mults, max_overlap=a.max_overlap, passes=a.passes, budget=None)

    def phase(label, ru, rcells, targets):
        t0 = time.time()
        res = pn.plan(grid, ru, rcells, targets, PP)
        ver = pn.verify_network(res["sel"], ru, grid, a.attach_tol_m)
        for t, r in res["sel"].items():
            r.update(ver.get(t, {}))
        log(f"[{label}] targets={len(targets)} routed={len(res['sel'])} failed={len(res['fails'])} reroutes_changed={res['reroutes_changed']} time={time.time() - t0:.1f}s")
        ids = {t["id"] for t in targets}
        C.ok(f"RUN-04[{label}]", set(res["sel"]) | set(res["fails"]) == ids and not (set(res["sel"]) & set(res["fails"])),
             "every target is exactly one of routed / failed", f"routed={len(res['sel'])} failed={len(res['fails'])} total={len(ids)}")
        return res

    # ---------- phase F: facilities first ----------
    res_f, fac_cells, union2, goals2 = None, {}, road_union, set(road_cells)
    if a.facilities == "on":
        res_f = phase("facilities->roads", road_union, road_cells, fac_t)
        for fid, r in res_f["sel"].items():
            for c in r["cells"]:
                fac_cells.setdefault(c, fid)
        if res_f["sel"]:
            union2 = unary_union([road_union] + [pn.cell_line(grid, r["cells"]) for r in res_f["sel"].values()])
        goals2 = set(road_cells) | set(fac_cells)
    # ---------- phase H: houses onto roads (+ facility routes) ----------
    res_h = phase("houses->" + ("roads+facility routes" if a.facilities == "on" else "roads"), union2, goals2, targets_h)
    # ---------- roads-only reference + baselines ----------
    res_r = None
    if a.facilities == "on" and a.roads_only_reference == "on":
        res_r = phase("houses->roads only (reference)", road_union, road_cells, targets_h)
    base = res_r if res_r is not None else (res_h if a.facilities == "off" else None)
    res_ref = res_r if res_r is not None else (res_h if a.facilities == "off" else None)
    base_note = "roads-only reference" if base is not None else "NOT AVAILABLE (roads-only reference off): independent/straight baselines use the facility-inclusive goal set"
    if base is None:
        base = res_h
    # facility baselines come from the facility phase
    # ---------- length-only baseline (UNVERIFIED unless control tests pass) ----------
    lenonly, lenonly_ctl = {}, {}
    if a.length_only_baseline == "on":
        c1 = np.where(np.isfinite(W["cost"]) & (W["cost"] > 0), 1.0, np.nan)
        g1 = pn.Grid(c1, T, hard=W["hard"], mult=None, corner_cut=(a.corner_cut == "allow"))
        lenonly_ctl["pass_mask_identical"] = bool(np.array_equal(g1.pass_np, grid.pass_np))
        same_start, n_start = 0, 0
        for t in targets_h:
            s0, s1 = grid.snap(t["pt"].x, t["pt"].y, a.snap_m), g1.snap(t["pt"].x, t["pt"].y, a.snap_m)
            n_start += 1
            same_start += int(s0 is not None and s1 is not None and s0[0] == s1[0]) if s0 is not None else int(s1 is None)
            if s1 is None or grid.idx_of(t["pt"].x, t["pt"].y) is None or grid.cost[grid.idx_of(t["pt"].x, t["pt"].y)] == float("inf"):
                lenonly[t["id"]] = dict(status="FAILED", reason="NO_START_CELL")
                continue
            r = g1.search(s1[0], set(road_cells), limit_m=a.max_search_m)
            if isinstance(r, str):
                lenonly[t["id"]] = dict(status="FAILED", reason=r)
                continue
            rt = pn.make_route(g1, t["id"], t["pt"], s1[1], r, "length_only", road_union, a.attach_tol_m)
            e_real = grid.edges(rt["cells"])
            rt["cost_under_baseline_cost"] = sum(e[3] for e in e_real) + s1[1] * (grid.cost[rt["cells"][0]] if grid.cost[rt["cells"][0]] < float("inf") else 0.0)
            lenonly[t["id"]] = dict(status="ROUTED", route=rt)
        lenonly_ctl["same_start_cell"] = f"{same_start}/{n_start}"
        lenonly_ctl["verified"] = bool(lenonly_ctl["pass_mask_identical"] and same_start == n_start)
        C.add("RUN-05", "PASS" if lenonly_ctl["verified"] else "WARN", "length-only baseline control test (identical pass mask, identical start cells, same goals)",
              f"{lenonly_ctl}")

    # ---------- analysis of the primary (facility-inclusive) network ----------
    sel_f = res_f["sel"] if res_f else {}
    sel_h = res_h["sel"]
    all_sel = {**sel_f, **sel_h}
    lab, sizes = components(road_cells, w2)
    main_comp = 1 if sizes else None
    parent_of, endcell_of = {}, {}
    for tid, r in sel_f.items():
        at = r["attach_to"]
        e = r["end_cell"]
        endcell_of[tid] = e
        if at == "ROAD":
            parent_of[tid] = ("ROAD", "") if e in road_cells else ("UNCLASSIFIED", "")
        else:
            parent_of[tid] = ("FACILITY_ROUTE", at)
    for tid, r in sel_h.items():
        at = r["attach_to"]
        e = r["end_cell"]
        endcell_of[tid] = e
        if at == "ROAD":
            if e in road_cells:
                parent_of[tid] = ("ROAD", "")
            elif e in fac_cells:
                parent_of[tid] = ("FACILITY_ROUTE", fac_cells[e])
            else:
                parent_of[tid] = ("UNCLASSIFIED", "")
        else:
            parent_of[tid] = ("HOUSE_ROUTE", at)

    def chain(tid):
        seen, cur = [], tid
        while True:
            if cur in seen:
                return dict(depth=len(seen), terminal="CYCLE", comp=None)
            seen.append(cur)
            cls, par = parent_of.get(cur, ("MISSING", ""))
            if cls == "ROAD":
                return dict(depth=len(seen) - 1, terminal="ROAD", comp=lab.get(endcell_of[cur]))
            if cls in ("HOUSE_ROUTE", "FACILITY_ROUTE") and par in parent_of:
                cur = par
                continue
            return dict(depth=len(seen) - 1, terminal=cls, comp=None)

    dsu = DSU()
    cell_routes = defaultdict(list)
    for tid, r in all_sel.items():
        dsu.find(tid)
        for c in r["cells"]:
            cell_routes[c].append(tid)
            if c in road_cells:
                dsu.union(tid, "GROUND")
    for c, ts in cell_routes.items():
        for t2 in ts[1:]:
            dsu.union(ts[0], t2)
    lines = {tid: pn.cell_line(grid, r["cells"]) for tid, r in all_sel.items()}
    crossing = defaultdict(list)
    ids_l = list(lines)
    if ids_l:
        tree = STRtree([lines[i] for i in ids_l])
        for i, tid in enumerate(ids_l):
            for j in tree.query(lines[tid], predicate="crosses"):
                o = ids_l[int(j)]
                if o != tid and not (set(all_sel[tid]["cells"]) & set(all_sel[o]["cells"])):
                    crossing[tid].append(o)
    cyc = [t for t in all_sel if chain(t)["terminal"] == "CYCLE"]
    C.ok("RUN-06", not cyc, "no cycles in the attachment graph", f"cycles={len(cyc)}")
    unclass = [t for t in all_sel if parent_of[t][0] in ("UNCLASSIFIED", "MISSING")]
    C.ok("RUN-07", not unclass, "every attachment is classified ROAD / FACILITY_ROUTE / HOUSE_ROUTE", f"unclassified={len(unclass)}")
    invalid_geom = [t for t, r in all_sel.items() if r["geom"] is None or r["geom"].is_empty or not r["geom"].is_valid]
    C.ok("RUN-08", not invalid_geom, "all selected route geometries valid and non-empty", f"bad={len(invalid_geom)}")
    notok = [t for t, r in all_sel.items() if not r.get("endpoint_ok", False) or not r.get("hard_ok", False)]
    C.ok("RUN-09", not notok, "all selected routes: endpoint within tolerance and no hard-constraint samples", f"bad={len(notok)}")
    badlen = [t for t, r in all_sel.items() if abs(r["own_len_m"] - (sum(e[2] for e in r["edges"]) + r["start_snap_m"] + r["end_snap_m"])) > 0.011]
    C.ok("RUN-10", not badlen, "route length = grid edges + start/end connectors (planner rounds snaps to 0.01 m; tol 0.011)", f"bad={len(badlen)}")
    ver_disc = [t for t in all_sel if bool(chain(t)["terminal"] == "ROAD") != bool(dsu.find(t) == dsu.find("GROUND"))]
    C.ok("RUN-11", not ver_disc, "attachment-chain connectivity agrees with shared-cell connectivity", f"disagreements={len(ver_disc)}", fail="WARN")
    if crossing:
        C.add("RUN-12", "INFO", "routes with a proper crossing that shares no grid cell (diagonal X); not a junction", f"{len(crossing)} routes")
    else:
        C.add("RUN-12", "PASS", "no proper crossings without a shared grid cell")

    # ---------- shared-edge accounting ----------
    def edge_acc(sel, scope):
        E = {}
        for tid, r in sel.items():
            for (ea, eb, L, c) in r["edges"]:
                d = E.setdefault((ea, eb), dict(L=L, c=c, routes=[]))
                d["routes"].append(tid)
        per = {}
        for tid, r in sel.items():
            conn_cost = r["cost"] - sum(e[3] for e in r["edges"])
            share_c = conn_cost + sum(E[e[:2]]["c"] / len(E[e[:2]]["routes"]) for e in r["edges"])
            share_l = r["start_snap_m"] + r["end_snap_m"] + sum(E[e[:2]]["L"] / len(E[e[:2]]["routes"]) for e in r["edges"])
            first_cost = conn_cost + sum(e[3] for e in r["edges"] if E[e[:2]]["routes"][0] == tid)
            per[tid] = dict(equal_share_cost=share_c, equal_share_len_m=share_l, first_owner_cost=first_cost, start_connector_cost=conn_cost)
        c_net = sum(d["c"] for d in E.values()) + sum(p["start_connector_cost"] for p in per.values())
        return E, per, c_net

    EA = {}
    for scope, sel in (("facility_phase", sel_f), ("house_phase", sel_h)) + ((("house_roads_only_ref", res_r["sel"]),) if res_r else ()):
        if not sel:
            continue
        E, per, c_net = edge_acc(sel, scope)
        m = pn.unique_edge_metrics(list(sel.values()))
        EA[scope] = (E, per, c_net, m)
        C.ok(f"RUN-13[{scope}]", abs(sum(p["equal_share_cost"] for p in per.values()) - c_net) <= 1e-6 * max(1.0, c_net),
             "sum of equal-share allocations equals unique network proxy cost", f"sum={sum(p['equal_share_cost'] for p in per.values()):.4f} C_net={c_net:.4f}")
        C.ok(f"RUN-14[{scope}]", abs(c_net - m["unique_cost"]) <= 1e-6 * max(1.0, c_net), "C_net equals planner unique_edge_metrics unique_cost",
             f"mine={c_net:.4f} planner={m['unique_cost']:.4f}")
        C.ok(f"RUN-15[{scope}]", sum(1 for d in E.values() if len(d["routes"]) > 1) >= 0, "shared-edge table built", f"unique edges={len(E)} shared edges={sum(1 for d in E.values() if len(d['routes']) > 1)}", fail="INFO")

    # ---------- impact proxies ----------
    cad = gpd.read_file(P["cad"]).to_crs(CRS).reset_index(drop=True)
    cad["row"] = range(len(cad))
    repaired_rows = set()
    if P["cad0"].exists():
        cad0 = gpd.read_file(P["cad0"]).reset_index(drop=True)
        same_attr = cad0.drop(columns="geometry").equals(gpd.read_file(P["cad"]).reset_index(drop=True).drop(columns="geometry"))
        C.add("IMP-01", "PASS" if same_attr else "WARN", "original and repaired cadastral attribute tables identical (row correspondence)", f"identical={same_attr}")
        repaired_rows = set(int(i) for i in np.nonzero(~cad0.geometry.is_valid.values)[0]) if same_attr else set()
    comp_gdf = gpd.read_file(P["compounds"]).to_crs(CRS).reset_index(drop=True)
    bsi, csi, psi = bld_all.sindex, cad.sindex, comp_gdf.sindex
    own_comp_of = {}
    for fid, fi in finfo.items():
        pt = Point(fi["x"], fi["y"])
        h = [int(i) for i in range(len(comp_gdf)) if comp_gdf.geometry.iloc[i].contains(pt)]
        own_comp_of[fid] = h[0] if h else None
    unsurveyed = set(cad.index[cad.Descriptio.astype(str).str.contains("UnSurveyed", case=False)])

    def edge_stats(r):
        lc, sl_len, smax, wsum, w10, w25, pen_len, tot = Counter(), 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
        for (ea, eb, L, c) in r["edges"]:
            (ra, ca), (rb, cb) = rc(ea), rc(eb)
            for (rr_, cc_) in ((ra, ca), (rb, cb)):
                k = wc_arr[rr_, cc_]
                lc[int(k) if np.isfinite(k) else 0] += L / 2
            sa_, sb_ = sl0[ra, ca], sl0[rb, cb]
            wsum += L * (sa_ + sb_) / 2
            smax = max(smax, sa_, sb_)
            if max(sa_, sb_) > 10:
                w10 += L
            if max(sa_, sb_) > 25:
                w25 += L
            if bm[ra, ca] or bm[rb, cb]:
                pen_len += L
            tot += L
        return lc, (wsum / tot if tot > 0 else 0.0), smax, w10, w25, pen_len, tot

    def impacts(set_name, routes, kind):
        rows = []
        for tid, r in routes.items():
            g = r["geom"]
            if g is None or g.is_empty:
                continue
            own_cand = cand_of_key.get(tid) if kind == "house" else None
            own_comp = own_comp_of.get(tid) if kind == "facility" else None
            row = dict(set=set_name, target_id=tid, kind=kind, evidence_level="computed_geometric_proxy", route_len_m=float(g.length))
            own_len, oth, n_oth = 0.0, Counter(), 0
            for p in bsi.query(g, predicate="intersects"):
                bp = bld_all.iloc[int(p)]
                try:
                    L = g.intersection(bp.geometry).length
                except Exception:
                    L = 0.0
                if L <= 1e-6:
                    continue
                if own_cand is not None and int(bp.cand_id) == own_cand:
                    own_len += L
                else:
                    oth[bp.quality_class] += L
                    n_oth += 1
            row.update(len_in_own_polygon_m=own_len, n_other_polygons_crossed=n_oth,
                       len_other_PLAUSIBLE_m=oth["PLAUSIBLE"], len_other_REVIEW_m=oth["REVIEW"], len_other_UNRESOLVED_MERGE_m=oth["UNRESOLVED_MERGE"])
            pl, npar, uns, rep, plist = 0.0, 0, 0.0, 0.0, []
            for p in csi.query(g, predicate="intersects"):
                try:
                    L = g.intersection(cad.geometry.iloc[int(p)]).length
                except Exception:
                    L = 0.0
                if L > 0.01:
                    pl += L
                    npar += 1
                    plist.append(int(p))
                    if int(p) in unsurveyed:
                        uns += L
                    if int(p) in repaired_rows:
                        rep += L
            row.update(n_parcels_touched=npar, len_in_parcels_m=pl, len_outside_cadastre_m=max(0.0, g.length - pl), len_in_unsurveyed_parcels_m=uns,
                       len_in_repaired_parcels_m=rep, parcel_rows=";".join(f"{i}:{cad.Base_Syno.iloc[i]}" for i in sorted(plist)[:30]))
            cl = 0.0
            for p in psi.query(g, predicate="intersects"):
                if own_comp is not None and int(p) == own_comp:
                    continue
                try:
                    cl += g.intersection(comp_gdf.geometry.iloc[int(p)]).length
                except Exception:
                    pass
            row.update(len_in_school_compounds_excl_own_m=cl)
            if "edges" in r and r["edges"]:
                lc, smean, smax, w10, w25, pen_len, tot = edge_stats(r)
                tl = sum(lc.values()) or 1.0
                row.update(grid_edge_len_m=tot, connector_len_m=r["start_snap_m"] + r["end_snap_m"], slope_mean_deg=smean, slope_max_deg=smax,
                           len_slope_gt10_m=w10, len_slope_gt25_m=w25, len_in_penalised_cells_m=pen_len)
                for k_ in (10, 20, 30, 40, 50, 60):
                    row[f"landcover_{k_}_share"] = lc.get(k_, 0.0) / tl
            rows.append(row)
        return rows

    imp = []
    imp += impacts("network_primary", sel_h, "house")
    if sel_f:
        imp += impacts("network_primary", sel_f, "facility")
    if res_r is not None:
        imp += impacts("roads_only_reference", res_r["sel"], "house")
    imp += impacts("independent_baseline", base["indep"], "house")
    imp += impacts("straight_line_baseline", base["straight"], "house")
    imp += impacts("length_only_baseline", {t: v["route"] for t, v in lenonly.items() if v["status"] == "ROUTED"}, "house")
    if res_f:
        imp += impacts("independent_baseline", res_f["indep"], "facility")
        imp += impacts("straight_line_baseline", res_f["straight"], "facility")
    imp_df = pd.DataFrame(imp)

    # ---------- tables ----------
    step_of = {t: i + 1 for i, t in enumerate(all_sel)}          # insertion order of planner 'sel' dicts = greedy selection order
    step_h = {t: i + 1 for i, t in enumerate(sel_h)}
    step_f = {t: i + 1 for i, t in enumerate(sel_f)}
    trow = []
    for t in targets_h:
        k = t["id"]
        i = tinfo[k]
        r = sel_h.get(k)
        row = dict(**i)
        row["primary_status"] = "ROUTED" if r else "FAILED"
        row["primary_fail_reason"] = res_h["fails"].get(k, "")
        if r:
            cls, par = parent_of[k]
            ch = chain(k)
            row.update(primary_attach_class=cls, primary_attach_parent=(cand_of_key.get(par, par) if cls == "HOUSE_ROUTE" else par),
                       primary_attach_parent_key=par, primary_chain_depth=ch["depth"], primary_chain_terminal=ch["terminal"], primary_road_component=ch["comp"],
                       primary_reaches_main_road_component=bool(ch["terminal"] == "ROAD" and ch["comp"] == main_comp),
                       primary_connected_planner_verify=bool(r.get("connected_to_roads", False)),
                       primary_connected_cell_graph=bool(dsu.find(k) == dsu.find("GROUND")),
                       primary_crossings_no_shared_cell=len(crossing.get(k, [])),
                       primary_selection_step=step_h[k], primary_mode=r["mode"], primary_len_m=r["own_len_m"], primary_cost=r["cost"],
                       primary_marginal_cost_when_added=r.get("marginal_cost_when_added"), primary_start_snap_m=r["start_snap_m"], primary_end_snap_m=r["end_snap_m"],
                       primary_equal_share_cost=EA["house_phase"][1][k]["equal_share_cost"], primary_equal_share_len_m=EA["house_phase"][1][k]["equal_share_len_m"],
                       primary_first_owner_cost=EA["house_phase"][1][k]["first_owner_cost"])
        if res_r is not None:
            rr_ = res_r["sel"].get(k)
            row["refroads_status"] = "ROUTED" if rr_ else "FAILED"
            row["refroads_fail_reason"] = res_r["fails"].get(k, "")
            if rr_:
                row.update(refroads_attach_to=(cand_of_key.get(rr_["attach_to"], rr_["attach_to"]) if rr_["attach_to"] != "ROAD" else "ROAD"),
                           refroads_len_m=rr_["own_len_m"], refroads_cost=rr_["cost"], refroads_mode=rr_["mode"])
        ir = base["indep"].get(k)
        row["independent_status"] = "ROUTED" if ir else "FAILED"
        row["independent_fail_reason"] = base["fails"].get(k, "")
        if ir:
            row.update(independent_len_m=ir["own_len_m"], independent_cost=ir["cost"])
        sr = base["straight"].get(k)
        if sr:
            row.update(straight_len_m=sr["own_len_m"], straight_feasible=bool(sr["feasible"]), straight_bad_samples=int(sr["bad_samples"]))
        lo = lenonly.get(k)
        if lo:
            row["lengthonly_status"] = lo["status"]
            if lo["status"] == "ROUTED":
                row.update(lengthonly_len_m=lo["route"]["own_len_m"], lengthonly_cost_under_baseline_cost=lo["route"]["cost_under_baseline_cost"])
        trow.append(row)
    target_status = pd.DataFrame(trow)
    frow = []
    for t in fac_t:
        k = t["id"]
        row = dict(**finfo[k])
        r = sel_f.get(k)
        row["status"] = "ROUTED" if r else "FAILED"
        row["fail_reason"] = res_f["fails"].get(k, "") if res_f else ""
        if r:
            cls, par = parent_of[k]
            ch = chain(k)
            row.update(attach_class=cls, attach_parent=par, chain_depth=ch["depth"], chain_terminal=ch["terminal"], road_component=ch["comp"],
                       reaches_main_road_component=bool(ch["terminal"] == "ROAD" and ch["comp"] == main_comp), connected_planner_verify=bool(r.get("connected_to_roads", False)),
                       selection_step=step_f[k], mode=r["mode"], len_m=r["own_len_m"], cost=r["cost"], marginal_cost_when_added=r.get("marginal_cost_when_added"),
                       end_snap_m=r["end_snap_m"], equal_share_cost=EA["facility_phase"][1][k]["equal_share_cost"])
        ir = res_f["indep"].get(k) if res_f else None
        if ir:
            row.update(independent_len_m=ir["own_len_m"], independent_cost=ir["cost"])
        sr = res_f["straight"].get(k) if res_f else None
        if sr:
            row.update(straight_len_m=sr["own_len_m"], straight_feasible=bool(sr["feasible"]))
        frow.append(row)
    fac_status = pd.DataFrame(frow)
    if a.facilities == "on":
        C.ok("RUN-16", len(fac_status) == a.expect_facilities, "facility table has one row per prepared priority facility", f"{len(fac_status)}")

    # alternatives
    alt_rows = []
    for scope, res in (("facility_phase", res_f), ("house_phase", res_h)):
        if not res:
            continue
        for k, alts in res["alts"].items():
            first = set(alts[0]["cells"])
            chosen = (sel_f if scope == "facility_phase" else sel_h).get(k)
            for n_, r in enumerate(alts, 1):
                same = chosen is not None and chosen["cells"] == r["cells"]
                alt_rows.append(dict(scope=scope, target_id=k, cand_id=cand_of_key.get(k, ""), alt_rank=n_, len_m=r["own_len_m"], cost=r["cost"],
                                     overlap_with_alt1=len(set(r["cells"]) & first) / max(len(r["cells"]), 1), endpoint_ok=r["endpoint_ok"], hard_ok=r["hard_ok"],
                                     end_snap_m=r["end_snap_m"], identical_to_selected_route=bool(same)))
    alt_df = pd.DataFrame(alt_rows)
    # selection summary
    sel_rows = []
    for scope, sel, stp in (("facility_phase", sel_f, step_f), ("house_phase", sel_h, step_h)):
        for k, r in sel.items():
            m_ = r.get("marginal_cost_when_added")
            sel_rows.append(dict(scope=scope, step=stp[k], target_id=k, cand_id=cand_of_key.get(k, ""), weight=1.0, mode=r["mode"],
                                 alt_rank_used=(int(r["mode"][-1]) if r["mode"].startswith("stageA_alt") else 0), marginal_cost_when_added=m_,
                                 implied_score_weight_over_marginal=(1.0 / m_ if m_ else None), len_m=r["own_len_m"], cost=r["cost"],
                                 step_note="step = insertion order of the planner's selection dict (greedy order); leaf re-routes keep their original step"))
    sel_df = pd.DataFrame(sel_rows)
    # road components
    rc_rows = [dict(component_id=i, n_cells=n, share_of_goal_cells=n / max(len(road_cells), 1), is_main=(i == 1)) for i, n in enumerate(sizes, 1)]
    roadcomp_df = pd.DataFrame(rc_rows)
    # connectivity table
    cn_rows = []
    for tid, r in all_sel.items():
        ch = chain(tid)
        cls, par = parent_of[tid]
        cn_rows.append(dict(target_id=tid, kind=("facility" if tid in sel_f else "house"), cand_id=cand_of_key.get(tid, ""), attach_class=cls, attach_parent=par,
                            chain_depth=ch["depth"], chain_terminal=ch["terminal"], road_component=ch["comp"],
                            reaches_main_road_component=bool(ch["terminal"] == "ROAD" and ch["comp"] == main_comp),
                            planner_endpoint_dist_m=r.get("endpoint_dist_m"), planner_drawn_end_dist_m=r.get("drawn_end_dist_m"), planner_ok_local=r.get("ok_local"),
                            planner_connected_to_roads=r.get("connected_to_roads"), cell_graph_connected=bool(dsu.find(tid) == dsu.find("GROUND")),
                            end_snap_m=r["end_snap_m"], hard_violations=r["hard_violations"], endpoint_ok=r["endpoint_ok"],
                            crossings_no_shared_cell=len(crossing.get(tid, [])), crossing_with=";".join(crossing.get(tid, [])),
                            note="model connectivity on the planning grid; not a verified physical junction"))
    conn_df = pd.DataFrame(cn_rows)
    # shared edge tables
    se_rows, sp_rows, re_rows = [], [], []
    for scope, (E, per, c_net, m) in EA.items():
        for n_, (e, d) in enumerate(sorted(E.items()), 1):
            if len(d["routes"]) > 1:
                (ra, ca), (rb, cb) = rc(e[0]), rc(e[1])
                se_rows.append(dict(scope=scope, edge_id=n_, row_a=ra, col_a=ca, row_b=rb, col_b=cb, len_m=d["L"], cost=d["c"], n_routes=len(d["routes"]),
                                    owner_first=d["routes"][0], routes=";".join(d["routes"])))
        for tid, p in per.items():
            sp_rows.append(dict(scope=scope, target_id=tid, **p))
    shared_edges = pd.DataFrame(se_rows)
    shared_per_target = pd.DataFrame(sp_rows)
    for scope, sel in (("facility_phase", sel_f), ("house_phase", sel_h), ("house_roads_only_ref", res_r["sel"] if res_r else {})):
        for tid, r in sel.items():
            for (ea, eb, L, c) in r["edges"]:
                (ra, ca), (rb, cb) = rc(ea), rc(eb)
                re_rows.append((scope, tid, ra, ca, rb, cb, round(L, 6), round(c, 6)))
    route_edges = pd.DataFrame(re_rows, columns=["scope", "route_id", "row_a", "col_a", "row_b", "col_b", "len_m", "cost"])

    # ---------- evaluation summary ----------
    def metr(routes):
        routes = list(routes)
        if not routes:
            return dict(n=0, total_len_m=0.0, unique_len_m=0.0, shared_len_m=0.0, unique_cost=0.0, total_cost=0.0)
        m = pn.unique_edge_metrics(routes)
        return dict(n=len(routes), total_len_m=m["total_len_m"], unique_len_m=m["unique_len_m"], shared_len_m=m["total_len_m"] - m["unique_len_m"],
                    unique_cost=m["unique_cost"], total_cost=m["total_cost"])
    ev = dict(run_key=run_key, scenario=a.scenario, n_house_targets=len(targets_h), n_facility_targets=len(fac_t), slope_limit_deg=a.slope_limit_deg,
              cost_scenario=a.cost_scenario, building_quality=bq, building_mult=a.building_mult)
    ev["houses_primary"] = metr(sel_h.values())
    ev["facilities_primary"] = metr(sel_f.values())
    ev["combined_primary"] = metr(list(sel_f.values()) + list(sel_h.values()))
    ev["houses_independent_baseline"] = metr(base["indep"].values())
    if res_f:
        ev["facilities_independent_baseline"] = metr(res_f["indep"].values())
        ev["combined_independent_baseline"] = metr(list(res_f["indep"].values()) + list(base["indep"].values()))
        ev["credit_vs_independent_unique_cost_combined"] = ev["combined_independent_baseline"]["total_cost"] - ev["combined_primary"]["unique_cost"]
    ev["houses_straight_line"] = dict(n=len(base["straight"]), total_len_m=sum(s["own_len_m"] for s in base["straight"].values()),
                                      infeasible=sum(1 for s in base["straight"].values() if not s["feasible"]))
    ev["houses_length_only"] = metr([v["route"] for v in lenonly.values() if v["status"] == "ROUTED"]) if lenonly else None
    ev["length_only_control"] = lenonly_ctl
    if res_r is not None:
        ev["houses_roads_only_reference"] = metr(res_r["sel"].values())
        ev["facility_effect_on_house_unique_len_m"] = ev["houses_roads_only_reference"]["unique_len_m"] - ev["houses_primary"]["unique_len_m"]
        ev["facility_effect_note"] = "positive = fewer NEW house-route metres because houses can attach to facility routes; facility routes themselves are counted separately"
        ev["combined_primary_vs_separate_unique_len_m"] = dict(combined_primary=ev["combined_primary"]["unique_len_m"],
                                                               facilities_plus_roads_only_houses=ev["facilities_primary"]["unique_len_m"] + ev["houses_roads_only_reference"]["unique_len_m"])
    ev["failures_primary"] = dict(Counter(res_h["fails"].values()))
    ev["failures_facilities"] = dict(Counter(res_f["fails"].values())) if res_f else {}
    ev["attach_class_counts_primary_houses"] = dict(Counter(parent_of[t][0] for t in sel_h))
    ev["attach_class_counts_facilities"] = dict(Counter(parent_of[t][0] for t in sel_f))
    chains = [chain(t) for t in all_sel]
    ev["connectivity"] = dict(routed_total=len(all_sel), terminal_road=sum(1 for c in chains if c["terminal"] == "ROAD"),
                              reach_main_component=sum(1 for c in chains if c["terminal"] == "ROAD" and c["comp"] == main_comp),
                              max_chain_depth=max([c["depth"] for c in chains], default=0), cycles=len(cyc),
                              planner_verified_connected=sum(1 for r in all_sel.values() if r.get("connected_to_roads")),
                              cell_graph_connected=sum(1 for t in all_sel if dsu.find(t) == dsu.find("GROUND")),
                              routes_with_crossing_no_shared_cell=len(crossing), road_goal_cells=len(road_cells), road_components=len(sizes),
                              road_component_sizes=sizes[:15])
    ev["world"] = dict(grid=[H, Wd], resolution_m=grid.res, penalised_cells_all=int(bm.sum()), penalised_cells_valid=int((bm & np.isfinite(W["cost"]) & (W["cost"] > 0)).sum()),
                       road_cells_total=W["check"].get("road_cells"), slope_check=W["check"].get("slope"), notes=W.get("notes"))
    ev["baseline_note"] = base_note
    # by stratum
    strat_rows = []
    for sname in ["<=10m", ">10-20m", ">20m", "ALL"]:
        sub = target_status if sname == "ALL" else target_status[target_status.stratum == sname]
        for origin in ["ALL", "DEFAULT", "MERGED_SENS"]:
            s2 = sub if origin == "ALL" else sub[sub.origin == origin]
            if len(s2) == 0:
                continue
            row = dict(stratum=sname, origin=origin, n_targets=len(s2), primary_routed=int((s2.primary_status == "ROUTED").sum()),
                       primary_failed=int((s2.primary_status == "FAILED").sum()))
            for col, nm in (("primary_len_m", "primary"), ("independent_len_m", "independent"), ("straight_len_m", "straight"), ("lengthonly_len_m", "lengthonly"), ("refroads_len_m", "refroads")):
                if col in s2:
                    row[f"{nm}_sum_len_m"] = float(s2[col].sum(skipna=True))
                    row[f"{nm}_mean_len_m"] = float(s2[col].mean(skipna=True)) if s2[col].notna().any() else None
            if "primary_attach_class" in s2:
                for cl in ("ROAD", "FACILITY_ROUTE", "HOUSE_ROUTE"):
                    row[f"attach_{cl}"] = int((s2.primary_attach_class == cl).sum())
            if "primary_equal_share_cost" in s2:
                row["primary_equal_share_cost_sum"] = float(s2.primary_equal_share_cost.sum(skipna=True))
            strat_rows.append(row)
    strat_df = pd.DataFrame(strat_rows)

    # ---------- V1 regression (only when the configuration is V1-equivalent) ----------
    reg_rows, reg_done = [], False
    v1_equiv = (a.scenario == "S2" and a.slope_limit_deg == 25.0 and a.cost_scenario == "C0" and bq == ["PLAUSIBLE", "REVIEW", "UNRESOLVED_MERGE"] and a.building_mult == 4.0
                and a.k == 3 and a.corridor_m == 20.0 and a.corridor_mults == [3.0, 8.0] and a.max_overlap == 0.8 and a.passes == 2 and a.snap_m == 30.0
                and a.max_search_m == 1500.0 and a.attach_tol_m == 15.0 and a.corner_cut == "forbid")
    refsel = res_r if res_r is not None else (res_h if a.facilities == "off" else None)
    if v1_equiv and refsel is not None and (v1dir / "house_network_summary.json").exists() and (v1dir / "individual_house_network_v1.gpkg").exists():
        reg_done = True
        v1s = pd.read_csv(v1dir / "house_network_status.csv", dtype={"cand_id": str, "house_route_id": str})
        v1j = json.loads((v1dir / "house_network_summary.json").read_text(encoding="utf-8"))
        gna = gpd.read_file(v1dir / "individual_house_network_v1.gpkg", layer="routes_network_aware")
        gin = gpd.read_file(v1dir / "individual_house_network_v1.gpkg", layer="routes_independent")
        gna_m = {r.house_route_id: r.geometry for r in gna.itertuples()}
        gin_m = {r.house_route_id: r.geometry for r in gin.itertuples()}
        h2c = dict(zip(v1s.house_route_id, v1s.cand_id))
        C.ok("REG-01", set(v1s.cand_id) == S2 and len(v1s) == len(S2), "V1 target IDs equal S2", f"v1={len(v1s)} S2={len(S2)}")
        mism_att = mism_len = mism_cost = mism_geo = mism_ind = 0
        maxd = dict(len=0.0, cost=0.0, geo=0.0, ind_len=0.0)
        for r in v1s.itertuples():
            k = key_of_cand.get(int(r.cand_id))
            mine = refsel["sel"].get(k)
            if mine is None:
                mism_att += 1
                continue
            my_att = mine["attach_to"] if mine["attach_to"] == "ROAD" else str(cand_of_key.get(mine["attach_to"]))
            v_att = r.network_attach_to if r.network_attach_to == "ROAD" else h2c.get(r.network_attach_to)
            mism_att += int(my_att != v_att and str(my_att) != str(v_att))
            dl, dc = abs(round(mine["own_len_m"], 2) - float(r.network_route_length_m)), abs(round(mine["cost"], 4) - float(r.network_route_cost))
            maxd["len"], maxd["cost"] = max(maxd["len"], dl), max(maxd["cost"], dc)
            mism_len += int(dl > 0.0051)
            mism_cost += int(dc > 0.00006)
            gv = gna_m.get(r.house_route_id)
            dh = mine["geom"].hausdorff_distance(gv) if gv is not None else 1e9
            maxd["geo"] = max(maxd["geo"], dh)
            mism_geo += int(dh > 1e-3)
            ir = refsel["indep"].get(k)
            dli = abs(round(ir["own_len_m"], 2) - float(r.independent_route_length_m)) if ir else 1e9
            maxd["ind_len"] = max(maxd["ind_len"], dli)
            mism_ind += int(dli > 0.0051)
            reg_rows.append(dict(cand_id=r.cand_id, v1_house_id=r.house_route_id, planner_key=k, attach_equal=bool(my_att == v_att), len_diff_m=dl, cost_diff=dc, hausdorff_m=dh, indep_len_diff_m=dli))
        C.ok("REG-02", mism_att == 0, "attachment parent identical for every target (V1 vs this run, roads-only configuration)", f"mismatches={mism_att}")
        C.ok("REG-03", mism_len == 0 and mism_cost == 0, "network-aware route length and cost identical (V1 CSV rounding)", f"len mismatches={mism_len} (max {maxd['len']:.4f}) cost mismatches={mism_cost} (max {maxd['cost']:.6f})")
        C.ok("REG-04", mism_geo == 0, "network-aware route geometry identical (Hausdorff <= 1 mm)", f"mismatches={mism_geo} max={maxd['geo']:.6f} m")
        C.ok("REG-05", mism_ind == 0, "independent route lengths identical", f"mismatches={mism_ind} max={maxd['ind_len']:.4f}")
        mn, mi_ = pn.unique_edge_metrics(list(refsel["sel"].values())), pn.unique_edge_metrics(list(refsel["indep"].values()))
        C.ok("REG-06", abs(mn["unique_len_m"] - v1j["unique_grid_edge_length_network_aware_m"]) < 1e-6 and abs(mi_["unique_len_m"] - v1j["unique_grid_edge_length_independent_m"]) < 1e-6,
             "unique grid-edge totals equal V1 summary JSON", f"mine NA={mn['unique_len_m']:.6f} V1={v1j['unique_grid_edge_length_network_aware_m']:.6f}; mine IND={mi_['unique_len_m']:.6f} V1={v1j['unique_grid_edge_length_independent_m']:.6f}")
        s_my = round(sum(round(r["own_len_m"], 2) for r in refsel["sel"].values()), 2)
        C.ok("REG-07", abs(s_my - v1j["route_length_sum_network_aware_m"]) < 0.011, "route-length sum equals V1 summary JSON", f"mine={s_my} V1={v1j['route_length_sum_network_aware_m']}")
    else:
        C.add("REG-00", "INFO", "V1 regression not applicable to this run configuration", "needs S2, 25 deg, C0, all three penalty classes, V1 planner parameters, roads-only reference")
    reg_df = pd.DataFrame(reg_rows)

    # ---------- exclusion / review flags ----------
    fl = []
    for k, i in tinfo.items():
        if i["origin"] == "MERGED_SENS":
            fl.append(dict(id=k, cand_id=i["cand_id"], flag="UNRESOLVED_MERGE_TARGET", reason="merged-building polygon routed only in the sensitivity scenario; may be several buildings"))
        if k in res_h["fails"]:
            fl.append(dict(id=k, cand_id=i["cand_id"], flag="ROUTE_FAILED", reason=res_h["fails"][k]))
        if i["quality_class"] == "REVIEW":
            fl.append(dict(id=k, cand_id=i["cand_id"], flag="REVIEW_CLASS_TARGET", reason="Stage A tier B: flagged for review"))
        if k in crossing:
            fl.append(dict(id=k, cand_id=i["cand_id"], flag="CROSSING_WITHOUT_SHARED_CELL", reason=";".join(crossing[k])))
    for fid, fi in finfo.items():
        fl.append(dict(id=fid, cand_id="", flag="FACILITY_IDENTITY", reason=fi["identity_status"]))
        if res_f and fid in res_f["fails"]:
            fl.append(dict(id=fid, cand_id="", flag="FACILITY_ROUTE_FAILED", reason=res_f["fails"][fid]))
    if len(imp_df) and "len_in_repaired_parcels_m" in imp_df:
        for r in imp_df[(imp_df.set == "network_primary") & (imp_df.len_in_repaired_parcels_m > 0)].itertuples():
            fl.append(dict(id=r.target_id, cand_id=cand_of_key.get(r.target_id, ""), flag="TOUCHES_REPAIRED_CADASTRAL_PARCEL", reason=f"{r.len_in_repaired_parcels_m:.1f} m inside parcels that were invalid in the original layer"))
    flags_df = pd.DataFrame(fl, columns=["id", "cand_id", "flag", "reason"])

    # ---------- gpkg layers ----------
    import warnings
    warnings.simplefilter("ignore")
    gp = out / "routes.gpkg"
    layer_counts = {}
    first = [True]

    def wlayer(name, recs):
        recs = [r for r in recs if r.get("geometry") is not None and not r["geometry"].is_empty]
        if not recs:
            return
        gpd.GeoDataFrame(recs, geometry="geometry", crs=CRS).to_file(gp, layer=name, driver="GPKG", mode=("w" if first[0] else "a"))
        first[0] = False
        layer_counts[name] = len(recs)

    def route_recs(routes, scope, kind):
        recs = []
        for tid, r in routes.items():
            g = r.get("geom") if isinstance(r, dict) else None
            t = tinfo.get(tid, {})
            recs.append(dict(scope=scope, target_id=tid, cand_id=t.get("cand_id", -1), origin=t.get("origin", ""), quality_class=t.get("quality_class", ""),
                             stratum=t.get("stratum", ""), mode=r.get("mode", ""), len_m=float(r.get("own_len_m", g.length if g is not None else 0.0)),
                             cost=(float(r["cost"]) if r.get("cost") is not None else None), attach_class=parent_of.get(tid, ("", ""))[0] if scope.startswith("network_primary") else "",
                             attach_parent=parent_of.get(tid, ("", ""))[1] if scope.startswith("network_primary") else "", step=step_of.get(tid, 0) if scope.startswith("network_primary") else 0,
                             status="UNVERIFIED_PLANNING_ALTERNATIVE_NOT_A_ROAD", geometry=g))
        return recs
    wlayer("routes_network_houses", route_recs(sel_h, "network_primary_house", "house"))
    wlayer("routes_network_facilities", route_recs(sel_f, "network_primary_facility", "facility"))
    if res_r is not None:
        wlayer("routes_roads_only_houses", route_recs(res_r["sel"], "roads_only_reference", "house"))
    wlayer("routes_independent_houses", route_recs(base["indep"], "independent_baseline", "house"))
    if res_f:
        wlayer("routes_independent_facilities", route_recs(res_f["indep"], "independent_baseline", "facility"))
    wlayer("routes_straight_line_houses", route_recs(base["straight"], "straight_line_baseline", "house"))
    wlayer("routes_length_only_houses", route_recs({t: v["route"] for t, v in lenonly.items() if v["status"] == "ROUTED"}, "length_only_baseline", "house"))
    wlayer("targets_houses", [dict(target_id=k, cand_id=i["cand_id"], origin=i["origin"], quality_class=i["quality_class"], stratum=i["stratum"], dist_to_road_m=i["dist_to_road_m"],
                                    geometry=Point(i["x"], i["y"])) for k, i in tinfo.items()])
    wlayer("targets_facilities", [dict(target_id=k, facility_name=f["facility_name"], facility_type=f["facility_type"], identity_status=f["identity_status"], geometry=Point(f["x"], f["y"]))
                                  for k, f in finfo.items()])
    wlayer("stageA_alternatives_houses", [dict(target_id=k, alt_rank=n_, len_m=r["own_len_m"], cost=r["cost"], geometry=r["geom"]) for k, al in res_h["alts"].items() for n_, r in enumerate(al, 1)])
    wlayer("road_cells_main_component", [dict(component_id=1, n_cells=sizes[0] if sizes else 0, geometry=unary_union([Point(*grid.xy(c)).buffer(grid.res / 2, cap_style=3) for c in road_cells if lab.get(c) == 1]))] if road_cells else [])
    written.append(("routes.gpkg", None))

    # ---------- files ----------
    manifest_rows = []
    for k, p in {**P, **{f"stageA_{n}": v for n, v in SA.items()}, "v1_summary": v1dir / "house_network_summary.json", "v1_status": v1dir / "house_network_status.csv",
                  "v1_gpkg": v1dir / "individual_house_network_v1.gpkg"}.items():
        p = Path(p)
        if p.exists():
            manifest_rows.append(dict(role=k, path=str(p), bytes=p.stat().st_size, sha256=sha256_file(p)))
    for p in (Path(__file__),):
        manifest_rows.append(dict(role="this script", path=str(p), bytes=p.stat().st_size, sha256=sha256_file(p)))
    wcsv("inputs_manifest_stageB.csv", pd.DataFrame(manifest_rows))
    cfg = dict(version=VERSION, run_key=run_key, args=vars(a), planner_parameters=PP, python=platform.python_version(),
               packages={m: __import__(m).__version__ for m in ("numpy", "pandas", "geopandas", "shapely", "rasterio", "fiona") if m in sys.modules or True},
               gdal=rasterio.__gdal_version__, git=git_info(str(proj)), planner_sha256=sha_planner, resolved_constraints=cr,
               id_scheme="planner key C#### = cand_id zero-padded (sorts like ascending cand_id = V1 H#### order); cand_id is the primary identifier",
               cost_scenario=dict(name=a.cost_scenario, c0_land_cost=LAND_COST_C0, c1_land_cost=c1_table,
                                  c1_status="PROVISIONAL default (built-up = grass) - needs user approval" if a.cost_scenario == "C1" else None,
                                  slope_term=f"{SLOPE_WEIGHT} * clip(slope,0,{SLOPE_MAX_DEG}) / {SLOPE_MAX_DEG}"),
               target_counts=dict(houses=len(targets_h), facilities=len(fac_t)), limitations=LIMITATIONS, base_note=base_note,
               cadastral_used=str(P["cad"]), repaired_cadastral_rows=sorted(repaired_rows), started_utc=pd.Timestamp(t_start, unit="s").isoformat())
    wjson("config_stageB.json", cfg)
    wcsv("scenario_targets.csv", pd.DataFrame(list(tinfo.values())))
    wcsv("target_status.csv", target_status)
    wcsv("facility_status.csv", fac_status)
    wcsv("route_alternatives.csv", alt_df)
    wcsv("selection_summary.csv", sel_df)
    wcsv("connectivity_checks.csv", conn_df)
    wcsv("road_components.csv", roadcomp_df)
    wcsv("shared_edge_accounting.csv", shared_edges if len(shared_edges) else pd.DataFrame(columns=["scope", "edge_id", "row_a", "col_a", "row_b", "col_b", "len_m", "cost", "n_routes", "owner_first", "routes"]))
    wcsv("shared_edge_per_target.csv", shared_per_target)
    wcsv("route_edges.csv", route_edges)
    wcsv("impact_flags.csv", imp_df)
    wcsv("exclusion_review_flags.csv", flags_df)
    wcsv("evaluation_by_stratum.csv", strat_df)
    if len(reg_df):
        wcsv("regression_v1.csv", reg_df)
    wcsv("baselines.csv", pd.DataFrame(
        [dict(kind="house", baseline="independent_least_cost", verification="code-derived (planner indep = alt1 to goals)", **metr(base["indep"].values())),
         dict(kind="house", baseline="straight_line", verification="code-derived", n=ev["houses_straight_line"]["n"], total_len_m=ev["houses_straight_line"]["total_len_m"], infeasible=ev["houses_straight_line"]["infeasible"])]
        + ([dict(kind="house", baseline="length_only", verification=("VERIFIED by control test" if lenonly_ctl.get("verified") else "UNVERIFIED"), **ev["houses_length_only"])] if lenonly else [])))
    wjson("evaluation_summary.json", ev)

    # ---------- read-back verification ----------
    problems = []
    for name, data in written:
        p = out / name
        if not p.exists():
            problems.append(f"{name}: missing")
        elif data is not None and p.read_bytes() != data:
            problems.append(f"{name}: bytes differ from what was written")
    for name in ("target_status.csv", "scenario_targets.csv", "connectivity_checks.csv"):
        back = pd.read_csv(out / name)
        exp = {"target_status.csv": len(targets_h), "scenario_targets.csv": len(targets_h), "connectivity_checks.csv": len(all_sel)}[name]
        if len(back) != exp:
            problems.append(f"{name}: rows {len(back)} != {exp}")
    back_ids = pd.read_csv(out / "scenario_targets.csv").cand_id
    if back_ids.duplicated().any() or set(back_ids.astype(str)) != set(sel_ids):
        problems.append("scenario_targets.csv: cand_id set differs from the scenario")
    for layer, n_ in layer_counts.items():
        g_ = gpd.read_file(gp, layer=layer)
        if len(g_) != n_ or (g_.crs is None or g_.crs.to_epsg() != 32644) or (len(g_) and (g_.geometry.is_empty.any() or not g_.geometry.is_valid.all())):
            problems.append(f"routes.gpkg layer {layer}: count/CRS/validity problem")
    json.loads((out / "evaluation_summary.json").read_text(encoding="utf-8"))
    C.ok("VER-01", not problems, "read-back verification of all written files", "; ".join(problems) or f"{len(written)} files verified; layers={layer_counts}")
    # ---------- acceptance tests + manifest + checks (last) ----------
    wcsv("acceptance_tests.csv", C.df())
    outputs = []
    for p in sorted(out.iterdir()):
        outputs.append(dict(file=p.name, bytes=p.stat().st_size, sha256=sha256_file(p)))
    wcsv("outputs_manifest.csv", pd.DataFrame(outputs))
    txt = [f"{VERSION}  run_key={run_key}", f"started_utc={cfg['started_utc']}  elapsed_s={time.time() - t_start:.1f}", "",
           "ACCEPTANCE TESTS", C.df().to_string(index=False), "",
           f"counts: PASS={C.n('PASS')} INFO={C.n('INFO')} WARN={C.n('WARN')} FAIL={C.n('FAIL')}", "",
           "KEY NUMBERS", json.dumps(jsonable({k: ev[k] for k in ("houses_primary", "facilities_primary", "combined_primary", "houses_independent_baseline", "connectivity", "failures_primary")}), indent=2), "",
           "LIMITATIONS"] + [f"- {l}" for l in LIMITATIONS] + ["", "END OF STAGE B RUN CHECKS (file complete)"]
    wbytes("stageB_run_checks.txt", "\n".join(txt).encode("utf-8"))
    print("\n".join(txt))
    print(f"\nOutputs: {out}")
    for r_ in outputs:
        print(f"  {r_['bytes']:>10,} B  {r_['file']}")
    if problems:
        return 5
    return 0 if C.n("FAIL") == 0 else 4


def finish_preflight_fail(C, LOG, exit_code=2):
    print(C.df().to_string(index=False))
    print("PREFLIGHT FAILED: nothing was written.")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
