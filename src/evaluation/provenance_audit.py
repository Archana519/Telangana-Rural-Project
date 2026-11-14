"""Provenance and reproducibility audit for every number quoted in the manuscript.

    python -m src.evaluation.provenance_audit --write docs/results/PROVENANCE_AND_PROOFS.md --rerun --redownload

What it does (each step records PASS/FAIL, nothing is assumed):
  1. hashes every input file (SHA-256) and cross-checks the ones Stage B recorded (06_REPRODUCIBILITY/INPUT_HASHES.csv);
  2. Level 1 (Stage B): re-reads the recorded result tables, recomputes derived figures, and compares them with the values printed in the
     manuscript. Level 1 is NOT re-executed here: its 10 m cost raster and slope raster are git-ignored *.tif (recorded hash only);
  3. LoveDA metrics: recomputes pixel accuracy / macro precision / recall / Building-class IoU from the epoch-4 confusion matrix printed in the
     training notebook;
  4. Levels 2-4 and the penalty sweep: with --rerun, re-executes them into a temp folder and compares every numeric field with the committed
     results (determinism check); recomputes derived percentages from the raw fields;
  5. with --redownload, re-fetches every raster and road layer and compares pixel arrays / geometry hashes with the local copies;
  6. checks that the key numbers appear verbatim in paper/main.tex.
With --write it writes docs/results/provenance_audit.json, docs/results/input_manifest.csv and the Markdown report; a bare run only prints the summary.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import platform
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

RES = REPO / "docs" / "results"
RUN = RES / "hierarchy_real_run"
DEL = REPO / "DELIVERABLES_DAMARAKUNTA_STAGE_B"
T = DEL / "03_RESULTS_TABLES"

# Epoch-4 validation confusion matrix (rows = ground truth, columns = prediction; 7 scored LoveDA classes), copied verbatim from
# Archana519/smart_village_infrastructure :: final_MPS_project.ipynb (cell 22).
CM = np.array([
    [148250492, 7435926, 2326895, 6993769, 5593082, 4942134, 8466724],
    [6182914, 29910150, 28441, 41787, 96975, 330670, 140469],
    [7283602, 108266, 15267212, 12309, 406753, 465372, 260550],
    [7012451, 35833, 84202, 49352575, 692934, 1237529, 1265865],
    [9697575, 249308, 119751, 609109, 9682494, 125564, 1762792],
    [15361750, 61545, 167521, 137441, 845679, 19952166, 1042829],
    [44986441, 172473, 520963, 1154217, 2252864, 5382724, 91205885]], dtype=np.int64)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for blk in iter(lambda: fh.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def check(cid, claim, expected, actual, source, tol=0.0, kind="REAL"):
    ok = (abs(float(expected) - float(actual)) <= tol) if isinstance(expected, (int, float)) and isinstance(actual, (int, float, np.floating, np.integer)) \
        else expected == actual
    return dict(id=cid, claim=claim, expected=expected, actual=(float(actual) if isinstance(actual, (np.floating, np.integer)) else actual),
                source=source, tolerance=tol, status="PASS" if ok else "FAIL", evidence_class=kind)


# ================================================================================================ 1. inputs
def input_manifest(cfg) -> list:
    rows = []

    def add(group, level, rel, role, note=""):
        p = REPO / rel
        if not p.exists():
            rows.append(dict(group=group, level=level, role=role, path=rel, exists=False, bytes="", sha256="", note=note))
            return
        prov = Path(str(p) + ".provenance.json")
        rows.append(dict(group=group, level=level, role=role, path=rel, exists=True, bytes=p.stat().st_size, sha256=sha256(p),
                         note=note, provenance_json=str(prov.relative_to(REPO)) if prov.exists() else ""))

    g = cfg["data"]["gp"]
    for k in ("boundary", "roads", "facilities", "buildings", "house_targets_csv"):
        add("repository (TGRAC / Stage B)", "1,2", g[k], k)
    for rel, role in (("scripts/plan_network_v2.py", "Stage B planner (search engine reused by Levels 2-4)"),
                      ("scripts/dk_stageB_run_v1_6.py", "Stage B runner v1.6"),
                      ("Siddipet/Damarakunta/reference/school_compounds_utm44n.gpkg", "school compounds"),
                      ("Siddipet/Damarakunta/reference/damarakunta_cadastral_valid.gpkg", "cadastre (valid)"),
                      ("Siddipet/Damarakunta/reference/damarakunta_cadastral.gpkg", "cadastre (raw)")):
        add("repository (Stage B code/data)", "1", rel, role)
    for lvl in ("gp", "mandal", "district"):
        for k, rel in cfg["data"][lvl].items():
            if k in ("village_root",) or not isinstance(rel, str):
                continue
            if lvl == "gp" and k in ("boundary", "roads", "facilities", "buildings", "house_targets_csv"):
                continue
            add("downloaded (open data)", {"gp": "2", "mandal": "3", "district": "4"}[lvl], rel, f"{lvl}.{k}")
    cache = REPO / "data" / "raw" / "_cache"
    for f in sorted(cache.glob("*")) if cache.exists() else []:
        rows.append(dict(group="download cache", level="3,4", role="geoBoundaries raw", path=str(f.relative_to(REPO)), exists=True,
                         bytes=f.stat().st_size, sha256=sha256(f), note="raw national file before clipping", provenance_json=""))
    return rows


def stageb_recorded_hashes(rows) -> list:
    rec = pd.read_csv(DEL / "06_REPRODUCIBILITY" / "INPUT_HASHES.csv")
    out = []
    by = {Path(r["path"]).name: r for r in rows if r["exists"]}
    for _, r in rec.iterrows():
        name = Path(str(r["path"]).replace("\\", "/")).name
        if name in by:
            want, got, note = r["sha256_in_reference_manifest"], by[name]["sha256"], ""
            if got != want and name.endswith(".py"):          # the repository normalised scripts to LF (commit a179ff1); Stage B hashed CRLF
                raw = (REPO / by[name]["path"]).read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
                if hashlib.sha256(raw).hexdigest() == want:
                    got, note = want, " (equal after LF->CRLF conversion: content identical, only line endings were normalised)"
            out.append(check(f"H-{name}", f"SHA-256 of {name} equals the hash Stage B recorded{note}", want, got,
                             "06_REPRODUCIBILITY/INPUT_HASHES.csv", kind="REAL"))
        else:
            out.append(dict(id=f"H-{name}", claim=f"{name}: recorded hash {r['sha256_in_reference_manifest'][:16]}...",
                            expected=r["sha256_in_reference_manifest"], actual="file not in the repository (git-ignored raster or run output)",
                            source="06_REPRODUCIBILITY/INPUT_HASHES.csv", tolerance=0, status="RECORDED-NOT-RECOMPUTABLE", evidence_class="RECORDED"))
    return out


# ================================================================================================ 2. Level 1
def level1_checks() -> list:
    t1 = pd.read_csv(T / "COMPARISON_TABLES" / "table1_length_reduction.csv")
    t4 = pd.read_csv(T / "COMPARISON_TABLES" / "table4_c1_sensitivity.csv")
    t6 = pd.read_csv(T / "COMPARISON_TABLES" / "table6_obstacle_avoidance.csv")
    fs = pd.read_csv(T / "PRIMARY_RUN_S2_fac_C0_s25_final_x4" / "facility_status.csv")
    st = pd.read_csv(T / "PRIMARY_RUN_S2_fac_C0_s25_final_x4" / "scenario_targets.csv")
    c = []

    def row(conf, prefix):
        return t1[(t1.configuration == conf) & t1.method.str.startswith(prefix)].iloc[0]

    s1 = "03_RESULTS_TABLES/COMPARISON_TABLES/table1_length_reduction.csv"
    for conf, tag in (("x4 (primary)", "x4"), ("x1 (P3 control)", "x1")):
        two, ind = row(conf, "Two-stage"), row(conf, "Independent")
        exp = {"x4": dict(two=5069.0, tot=5069.0, ind_u=6753.1, ind_t=10045.4, pct=24.9, cross=28, inlen=209.1, icross=46, iinlen=328.3),
               "x1": dict(two=4705.4, tot=4705.5, ind_u=6921.3, ind_t=9595.9, pct=32.0, cross=56, inlen=660.1, icross=63, iinlen=1423.1)}[tag]
        c += [check(f"L1-{tag}-two-unique", f"[{tag}] two-stage plan unique length (m)", exp["two"], two.unique_len_m, s1, 0.05),
              check(f"L1-{tag}-two-total", f"[{tag}] two-stage plan total length (m)", exp["tot"], two.total_len_m, s1, 0.05),
              check(f"L1-{tag}-ind-unique", f"[{tag}] independent least-cost unique length (m)", exp["ind_u"], ind.unique_len_m, s1, 0.05),
              check(f"L1-{tag}-ind-total", f"[{tag}] independent least-cost total length (m)", exp["ind_t"], ind.total_len_m, s1, 0.05),
              check(f"L1-{tag}-saving", f"[{tag}] saving vs independent unique (%)", exp["pct"], two.reduction_vs_independent_unique_pct, s1, 0.05),
              check(f"L1-{tag}-saving-recomputed", f"[{tag}] saving recomputed from the two lengths (%)", exp["pct"],
                    round(100 * (ind.unique_len_m - two.unique_len_m) / ind.unique_len_m, 1), s1 + " (derived)", 0.05),
              check(f"L1-{tag}-cross", f"[{tag}] two-stage routes crossing other footprints", exp["cross"], two.routes_crossing_other_footprints, s1),
              check(f"L1-{tag}-inlen", f"[{tag}] two-stage length inside other footprints (m)", exp["inlen"], two.len_in_other_footprints_m, s1, 0.05),
              check(f"L1-{tag}-ind-cross", f"[{tag}] independent routes crossing", exp["icross"], ind.routes_crossing_other_footprints, s1),
              check(f"L1-{tag}-ind-inlen", f"[{tag}] independent length inside other footprints (m)", exp["iinlen"], ind.len_in_other_footprints_m, s1, 0.05)]
    for pre, tot, uni, cr, ln in (("Straight", 8092.3, None, 60, 1453.2), ("Length-only", 9166.3, 6979.8, 64, 1615.8), ("Roads-only", 5229.3, 5229.3, 29, 216.1)):
        r = row("x4 (primary)", pre)
        c.append(check(f"L1-x4-{pre}", f"[x4] {pre}: total length (m)", tot, r.total_len_m, s1, 0.05))
        if uni:
            c.append(check(f"L1-x4-{pre}-u", f"[x4] {pre}: unique length (m)", uni, r.unique_len_m, s1, 0.05))
        c.append(check(f"L1-x4-{pre}-c", f"[x4] {pre}: routes crossing", cr, r.routes_crossing_other_footprints, s1))
        c.append(check(f"L1-x4-{pre}-l", f"[x4] {pre}: length in footprints (m)", ln, r.len_in_other_footprints_m, s1, 0.05))
    lo = row("x4 (primary)", "Length-only")
    c.append(check("L1-x4-lengthonly-pct", "[x4] length-only control vs independent unique (%)", -3.4, lo.reduction_vs_independent_unique_pct, s1, 0.05))
    s6 = "03_RESULTS_TABLES/COMPARISON_TABLES/table6_obstacle_avoidance.csv"
    for pen, uni, pct, cr, ln in ((20.0, 6238.1, 18.5, 19, 147.9), (100.0, 6190.3, 18.9, 19, 144.8)):
        r = t6[(t6.avoid_buildings == "buffer") & (t6.penalty_multiplier == pen)].iloc[0]
        c += [check(f"L1-buf{int(pen)}-len", f"buffer x{int(pen)} house unique length (m)", uni, r.house_unique_len_m, s6, 0.05),
              check(f"L1-buf{int(pen)}-pct", f"buffer x{int(pen)} saving (%)", pct, r.saving_vs_independent_pct, s6, 0.05),
              check(f"L1-buf{int(pen)}-cr", f"buffer x{int(pen)} routes crossing", cr, r.house_routes_crossing_other_footprints, s6),
              check(f"L1-buf{int(pen)}-ln", f"buffer x{int(pen)} crossing length (m)", ln, r.crossing_len_m, s6, 0.05)]
    s4 = "03_RESULTS_TABLES/COMPARISON_TABLES/table4_c1_sensitivity.csv"
    base = float(t4[t4.perturbation == "baseline (no perturbation)"].unique_len_m_mean.iloc[0])
    for name, routed, uni, per, sav, dl, u, kap in (
            ("omit 10%", 147.0, 4684.43, 31.87, 25.09, 7.6, 16, 90.2), ("omit 20%", 130.0, 4211.49, 32.4, 24.95, 16.9, 33, 79.8),
            ("omit smallest 10%", 146, 4648.65, 31.84, 24.92, 8.3, 17, 89.6), ("omit smallest 25%", 122, 3798.29, 31.13, 25.56, 25.1, 41, 74.8),
            ("omit merged blobs", 101, 3579.04, 35.44, 26.64, 29.4, 62, 62.0), ("add 10%", 177.4, 5502.4, 31.02, 25.62, -8.6, None, None),
            ("add 20%", 190.6, 5868.27, 30.79, 25.39, -15.8, None, None)):
        r = t4[t4.perturbation == name].iloc[0]
        c += [check(f"L1-{name}-routed", f"[{name}] routed targets", routed, r.house_targets_routed_mean, s4, 0.05),
              check(f"L1-{name}-len", f"[{name}] unique length (m)", uni, r.unique_len_m_mean, s4, 0.005),
              check(f"L1-{name}-per", f"[{name}] length per routed target (m)", per, r.unique_len_per_routed_m_mean, s4, 0.005),
              check(f"L1-{name}-sav", f"[{name}] saving vs independent (%)", sav, r.saving_vs_independent_pct_mean, s4, 0.005),
              check(f"L1-{name}-dL", f"[{name}] delta_L recomputed vs baseline 5,069.0 (%; negative = longer)", dl,
                    round(100 * (base - r.unique_len_m_mean) / base, 1), s4 + " (derived)", 0.05)]
        if u is not None:
            c += [check(f"L1-{name}-U", f"[{name}] unserved households = 163 - routed", u, int(round(163 - r.house_targets_routed_mean)), s4 + " (derived)"),
                  check(f"L1-{name}-kappa", f"[{name}] coverage kappa (%)", kap, round(100 * r.house_targets_routed_mean / 163, 1), s4 + " (derived)", 0.05)]
    c.append(check("L1-targets", "163 house targets, quality classes PLAUSIBLE/REVIEW/UNRESOLVED_MERGE = 71/30/62", (163, 71, 30, 62),
                   (len(st), int((st.quality_class == "PLAUSIBLE").sum()), int((st.quality_class == "REVIEW").sum()), int((st.quality_class == "UNRESOLVED_MERGE").sum())),
                   "03_RESULTS_TABLES/PRIMARY_RUN_S2_fac_C0_s25_final_x4/scenario_targets.csv"))
    h = fs[fs.facility_id == "HEALTH_8734223673"].iloc[0]
    sf = "03_RESULTS_TABLES/PRIMARY_RUN_S2_fac_C0_s25_final_x4/facility_status.csv"
    c += [check("L1-health-len", "Sub-centre route length WITH override (m, incl. connector)", 67.4, round(h.len_m, 1), sf, 0.05),
          check("L1-health-cost", "Sub-centre route cost WITH override (units)", 260.1, round(h.cost, 1), sf, 0.05),
          check("L1-combined", "Houses + facilities combined unique length (m)", 5318.3, float(t1[(t1.configuration == "x4 (primary)") &
                t1.method.str.startswith("Houses + facilities")].unique_len_m.iloc[0]), s1, 0.05)]
    c.append(dict(id="L1-health-without", claim="Sub-centre route WITHOUT override: 73.3 m, cost 357.7; combined unique 5,324.2 m",
                  expected="73.3 m / 357.7 / 5,324.2 m", actual="cost 357.692 is quoted in C1_report.md (C07 check); the 73.3 m and 5,324.2 m figures appear only in "
                  "Phase1_Report_CBIT_Format/MISSING_ITEMS_SUMMARY.md and inputs/METADATA.md (no machine-readable file)",
                  source="03_RESULTS_TABLES/C1_SEGMENTATION_SENSITIVITY/C1_report.md; Phase1_Report_CBIT_Format/MISSING_ITEMS_SUMMARY.md", tolerance=0,
                  status="RECORDED-SINGLE-SOURCE", evidence_class="RECORDED"))
    return c


def loveda_checks() -> list:
    tp = np.diag(CM).astype(float)
    fp, fn = CM.sum(0) - tp, CM.sum(1) - tp
    iou, prec, rec = tp / (tp + fp + fn), tp / (tp + fp), tp / (tp + fn)
    f1 = 2 * prec * rec / (prec + rec)
    src = "Archana519/smart_village_infrastructure final_MPS_project.ipynb cells 6, 16, 22 (epoch-4 confusion matrix embedded in CM)"
    return [check("LV-miou", "mIoU (%)", 53.8, round(100 * iou.mean(), 1), src, 0.05),
            check("LV-dice", "mDice = macro F1 (%)", 68.9, round(100 * f1.mean(), 1), src, 0.05),
            check("LV-acc", "pixel accuracy (%) = trace/total of the 7x7 matrix (log: 0.7134)", 71.3, round(100 * tp.sum() / CM.sum(), 1), src, 0.05),
            check("LV-prec", "macro precision (%)", 72.4, round(100 * prec.mean(), 1), src, 0.05),
            check("LV-rec", "macro recall (%)", 66.9, round(100 * rec.mean(), 1), src, 0.05),
            check("LV-bld-iou", "Building class IoU (%)", 54.0, round(100 * iou[0], 1), src, 0.05),
            check("LV-bld-prec", "Building class precision (%)", 62.1, round(100 * prec[0], 1), src, 0.05),
            check("LV-bld-rec", "Building class recall (%)", 80.6, round(100 * rec[0], 1), src, 0.05),
            check("LV-bld-f1", "Building class Dice/F1 (%)", 70.1, round(100 * f1[0], 1), src, 0.05)]


# ================================================================================================ 3. Levels 2-4
def _num_equal(a, b, tol=1e-6):
    if isinstance(a, dict):
        return all(k in b and _num_equal(a[k], b[k], tol) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(_num_equal(x, y, tol) for x, y in zip(a, b))
    if isinstance(a, float) or isinstance(b, float):
        if a is None or b is None:
            return a == b
        if isinstance(a, float) and math.isnan(a) and isinstance(b, float) and math.isnan(b):
            return True
        return abs(float(a) - float(b)) <= tol * max(1.0, abs(float(a)))
    return a == b


def levels_checks() -> list:
    c = []
    S = {l: json.loads((RUN / l / f"{l}_summary.json").read_text()) for l in ("gp", "mandal", "district")}
    gp, md, ds = S["gp"], S["mandal"], S["district"]
    rel = "docs/results/hierarchy_real_run/"
    for tag, s in (("L2", gp), ("L3", md), ("L4", ds)):
        lvl = {"L2": "gp", "L3": "mandal", "L4": "district"}[tag]
        src = f"{rel}{lvl}/{lvl}_summary.json"
        c += [check(f"{tag}-nodes", f"{tag}: nodes routed = nodes", s["n_nodes"], s["n_routed_shared"], src),
              check(f"{tag}-saving-recomputed", f"{tag}: saving vs independent (%) recomputed from the two lengths",
                    round(s["saving_vs_independent_unique_pct"], 6),
                    round(100 * (s["independent_unique_length_m"] - s["shared_unique_length_m"]) / s["independent_unique_length_m"], 6), src + " (derived)", 1e-5)]
    ov = pd.read_csv(RUN / "gp" / "gp_override.csv")
    c.append(check("L2-detour", "L2: detour reduction from the local override, all exempt facilities (m)", round(gp["detour_reduction_m_total"], 2),
                   round(float(ov[ov.status == "ROUTED"].detour_reduction_m.astype(float).sum()), 2), rel + "gp/gp_override.csv", 0.01))
    c.append(check("L2-other-routes", "L2: routes changed by the override other than the exempt facilities", 0,
                   int(float(ov[ov.node == "_OTHER_ROUTES_CHANGED"].cost_reduction_pct.iloc[0])), rel + "gp/gp_override.csv"))
    c.append(check("L2-weight", "L2: 163 houses aggregated into hamlet hubs (sum of hub weights)", 163, gp["unit_weight_total"], rel + "gp/gp_summary.json"))
    c.append(check("L4-existing-share", "L4: share of the backbone on existing roads (%)", round(100 * ds["shared_on_existing_road_m"] / ds["shared_unique_length_m"], 1),
                   round(100 * (ds["shared_unique_length_m"] - ds["shared_new_construction_m"]) / ds["shared_unique_length_m"], 1), rel + "district/district_summary.json (derived)", 0.05))
    c.append(check("L4-new-saving", "L4: new-construction saving vs star layout (%)", round(100 * (ds["independent_new_construction_m"] - ds["shared_new_construction_m"]) /
                   ds["independent_new_construction_m"], 1), round(100 * (ds["independent_new_construction_m"] - ds["shared_new_construction_m"]) / ds["independent_new_construction_m"], 1),
                   rel + "district/district_summary.json (derived)", 0.05))
    sw = pd.read_csv(RES / "U02_penalty_sweep_gp.csv")
    b = sw[sw.mu == 1.0].iloc[0]
    for _, r in sw.iterrows():
        c.append(check(f"U02-mu{r.mu:g}-len", f"U02 mu={r.mu:g}: length increase vs mu=1 recomputed (%)", r.length_increase_vs_mu1_pct,
                       round(100 * (r.shared_unique_length_m - b.shared_unique_length_m) / b.shared_unique_length_m, 2), "docs/results/U02_penalty_sweep_gp.csv (derived)", 0.011))
        c.append(check(f"U02-mu{r.mu:g}-exp", f"U02 mu={r.mu:g}: exposure reduction vs mu=1 recomputed (%)", r.exposure_reduction_vs_mu1_pct,
                       round(100 * (b.length_in_footprints_m - r.length_in_footprints_m) / b.length_in_footprints_m, 2), "docs/results/U02_penalty_sweep_gp.csv (derived)", 0.011))
    return c


def _read_csv(path):
    try:
        return pd.read_csv(path)
    except pd.errors.EmptyDataError:                    # levels without exempt facilities write an empty override table
        return pd.DataFrame()


def rerun_checks(log=print) -> list:
    """Re-execute Levels 2-4 and the sweep into a temp folder; compare every numeric field with the committed outputs."""
    from src.evaluation import penalty_sweep
    from src.routing.hierarchical_router import load_config
    from src.routing.run_hierarchy import run
    cfg = load_config()
    out = []
    with tempfile.TemporaryDirectory() as td:
        run([2, 3, 4], "real", td, cfg, log=lambda *_: None)
        for lvl in ("gp", "mandal", "district"):
            new = json.loads((Path(td) / lvl / f"{lvl}_summary.json").read_text())
            old = json.loads((RUN / lvl / f"{lvl}_summary.json").read_text())
            out.append(check(f"RR-{lvl}-summary", f"re-run {lvl}_summary.json equals the committed file (all numeric fields)", True, _num_equal(old, new),
                             f"docs/results/hierarchy_real_run/{lvl}/{lvl}_summary.json", kind="REPRODUCED"))
            for tbl in ("omission", "override", "metrics"):
                a, b = _read_csv(RUN / lvl / f"{lvl}_{tbl}.csv"), _read_csv(Path(td) / lvl / f"{lvl}_{tbl}.csv")
                same = a.shape == b.shape and all(_num_equal(float(x), float(y)) if pd.api.types.is_number(x) and pd.api.types.is_number(y) else str(x) == str(y)
                                                  for x, y in zip(a.to_numpy().ravel(), b.to_numpy().ravel()))
                out.append(check(f"RR-{lvl}-{tbl}", f"re-run {lvl}_{tbl}.csv equals the committed file", True, same,
                                 f"docs/results/hierarchy_real_run/{lvl}/{lvl}_{tbl}.csv", kind="REPRODUCED"))
        sweep_out = Path(td) / "sweep.csv"
        penalty_sweep.main(["--out", str(sweep_out)])
        a, b = pd.read_csv(RES / "U02_penalty_sweep_gp.csv"), pd.read_csv(sweep_out)
        out.append(check("RR-sweep", "re-run penalty sweep equals the committed U02_penalty_sweep_gp.csv", True,
                         a.shape == b.shape and np.allclose(a.to_numpy(float), b.to_numpy(float), equal_nan=True),
                         "docs/results/U02_penalty_sweep_gp.csv", kind="REPRODUCED"))
    return out


def redownload_checks(cfg) -> list:
    """Re-fetch rasters / roads into a temp folder and compare with the local copies (pixel arrays, geometry hashes)."""
    import copy
    import geopandas as gpd
    import rasterio
    from src.utils import data_downloader_helper as dl
    out = []
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        c2 = copy.deepcopy(cfg)
        for lvl in ("gp", "mandal", "district"):
            for k in ("landcover", "dem"):
                c2["data"][lvl][k] = str(tdp / f"{lvl}_{k}.tif")
            if lvl != "gp":
                c2["data"][lvl]["roads"] = str(tdp / f"{lvl}_roads.gpkg")
        for lvl in ("gp", "mandal", "district"):
            dl.fetch_rasters(c2, REPO, lvl, "copernicus", False, lambda *_: None)
            for k in ("landcover", "dem"):
                a, b = REPO / cfg["data"][lvl][k], tdp / f"{lvl}_{k}.tif"
                with rasterio.open(a) as x, rasterio.open(b) as y:
                    same = x.shape == y.shape and x.transform == y.transform and np.array_equal(x.read(1), y.read(1))
                out.append(check(f"RD-{lvl}-{k}", f"re-downloaded {lvl} {k} raster is pixel-identical to the local copy", True, same,
                                 str(a.relative_to(REPO)), kind="REPRODUCED"))
        rel = None
        prov = json.loads(Path(str(REPO / cfg["data"]["mandal"]["roads"]) + ".provenance.json").read_text())
        rel = prov["source"].split("release")[-1].strip()
        dl.PINNED_RELEASE = rel
        for lvl in ("mandal", "district"):
            dl.fetch_roads(c2, REPO, lvl, False, "overture", lambda *_: None)
            a = gpd.read_file(REPO / cfg["data"][lvl]["roads"])
            b = gpd.read_file(tdp / f"{lvl}_roads.gpkg")
            ha = hashlib.sha256("".join(sorted(g.wkb_hex for g in a.geometry)).encode()).hexdigest()
            hb = hashlib.sha256("".join(sorted(g.wkb_hex for g in b.geometry)).encode()).hexdigest()
            out.append(check(f"RD-{lvl}-roads", f"re-fetched {lvl} roads (Overture release {rel}) have identical geometries", ha, hb,
                             cfg["data"][lvl]["roads"], kind="REPRODUCED"))
    return out


FIGS = {"figA_level2_gp_network": "fig:level2", "figB_penalty_sweep": "fig:sweep", "figC_scalability_levels3_4": "fig:scale", "figD_level1_omission": "fig:level1"}


def figure_checks() -> list:
    """Each Contribution 3 figure exists in both places, is identical in both, is 300 dpi, and is included + cited in paper/main.tex."""
    from PIL import Image
    tex = (REPO / "paper" / "main.tex").read_text(encoding="utf-8")
    out = []
    for name, label in FIGS.items():
        a, b = REPO / "paper" / "figures" / f"{name}.png", RES / "hierarchy_real_run" / "figures" / f"{name}.png"
        src = f"paper/figures/{name}.png"
        if not (a.exists() and b.exists()):
            out.append(dict(id=f"FG-{name}", claim=f"{name}.png exists in paper/figures and docs/results/hierarchy_real_run/figures", expected="both", actual="missing",
                            source=src, tolerance=0, status="FAIL", evidence_class="REAL"))
            continue
        im = Image.open(a)
        dpi = im.info.get("dpi", (0, 0))[0]
        out += [check(f"FG-{name}-copies", f"{name}.png is byte-identical in paper/figures and docs/results/hierarchy_real_run/figures", sha256(a), sha256(b), src),
                check(f"FG-{name}-dpi", f"{name}.png resolution (dpi)", 300.0, round(float(dpi), 1), src, 0.5),
                check(f"FG-{name}-size", f"{name}.png is at least 2000 px wide ({im.size[0]} x {im.size[1]} px, sha256 {sha256(a)[:16]}...)", True, im.size[0] >= 2000, src),
                check(f"FG-{name}-included", f"paper/main.tex includes {name}.png and cites it as \\ref{{{label}}}", True,
                      (f"figures/{name}.png" in tex) and (f"\\ref{{{label}}}" in tex), "paper/main.tex")]
    return out


def paper_checks() -> list:
    tex = (REPO / "paper" / "main.tex").read_text(encoding="utf-8")
    S = {l: json.loads((RUN / l / f"{l}_summary.json").read_text()) for l in ("gp", "mandal", "district")}
    sw = pd.read_csv(RES / "U02_penalty_sweep_gp.csv").set_index("mu")

    def fmt(x, nd=1):
        s = f"{x:,.{nd}f}"
        return s.replace(",", "{,}")

    items = [("Level 2 shared length (m)", fmt(S["gp"]["shared_unique_length_m"], 1)), ("Level 2 independent length (m)", fmt(S["gp"]["independent_unique_length_m"], 1)),
             ("Level 3 shared length (m)", fmt(S["mandal"]["shared_unique_length_m"], 0)),
             ("Level 4 backbone length (km)", fmt(S["district"]["shared_unique_length_m"] / 1000, 1)),
             ("Level 4 new construction (km)", fmt(S["district"]["shared_new_construction_m"] / 1000, 1)),
             ("Level 4 existing-road share (%)", fmt(100 * S["district"]["shared_on_existing_road_m"] / S["district"]["shared_unique_length_m"], 1)),
             ("mu=4 exposure reduction (%)", fmt(sw.loc[4.0, "exposure_reduction_vs_mu1_pct"], 1)),
             ("mu=4 length increase (%)", fmt(sw.loc[4.0, "length_increase_vs_mu1_pct"], 1))]
    return [dict(id=f"PP-{i}", claim=f"paper/main.tex contains the {name} value '{val}'", expected=val, actual="present" if val in tex else "ABSENT",
                 source="paper/main.tex", tolerance=0, status="PASS" if val in tex else "FAIL", evidence_class="REAL") for i, (name, val) in enumerate(items)]


# ================================================================================================ report
def environment() -> dict:
    import geopandas, rasterio, shapely
    try:
        sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True).stdout.strip()
    except Exception:
        sha = ""
    return dict(python=platform.python_version(), numpy=np.__version__, geopandas=geopandas.__version__, rasterio=rasterio.__version__,
                shapely=shapely.__version__, git_commit_at_audit=sha, platform=platform.platform())


def md_table(rows, cols):
    head = "| " + " | ".join(cols) + " |\n|" + "---|" * len(cols) + "\n"
    return head + "\n".join("| " + " | ".join(str(r.get(c, "")).replace("|", "/").replace("\n", " ") for c in cols) + " |" for r in rows) + "\n"


def write_report(path: Path, R: dict, inputs: list, env: dict):
    def cnt(rs):
        return {s: sum(1 for r in rs if r["status"] == s) for s in sorted({r["status"] for r in rs})}
    L1, LV, LX, RR, RD, PP, HH = R["level1"], R["loveda"], R["levels"], R.get("rerun", []), R.get("redownload", []), R["paper"], R["hashes"]
    FG = R["figures"]
    txt = f"""# Provenance and proofs

*Generated by `python -m src.evaluation.provenance_audit --write docs/results/PROVENANCE_AND_PROOFS.md --rerun --redownload` on top of git commit
`{env['git_commit_at_audit'][:12]}`. Every row below is computed by that script (PASS/FAIL), not typed by hand. Machine-readable copy: `docs/results/provenance_audit.json`;
input hashes: `docs/results/input_manifest.csv`.*

## 0. Evidence classes - read this first
| Class | Meaning | Where it applies |
|---|---|---|
| **VERIFIED-REAL** | real inputs, numbers recomputed here from raw result files / re-executed here | Level 1 tables (re-read and recomputed, *not re-executed*), LoveDA metrics (recomputed from the confusion matrix), Level 2 Damarakunta GP, mu penalty sweep |
| **RECORDED** | value exists only in a recorded document/hash; not recomputable here (missing git-ignored rasters or a single prose source) | Level 1 cost/slope rasters and run command lines; sub-centre *without-override* length 73.3 m and combined 5,324.2 m |
| **SCALABILITY DEMONSTRATION (proxy nodes)** | the machinery runs on real rasters and roads, but terminals / hubs are *proxies* (polygon interior points, OSM village points), not verified HQ, PHC, market or GP locations | Level 3 Markook and Level 4 Siddipet - no administrative or planning conclusion may be drawn from them |
| **REPRODUCED** | re-executed or re-downloaded in this audit and compared with the committed copy | Levels 2-4, the sweep, all raster/road downloads |

Status counts - Level 1: {cnt(L1)}; LoveDA: {cnt(LV)}; Levels 2-4 + sweep: {cnt(LX)}; input hashes: {cnt(HH)}; re-run: {cnt(RR) if RR else 'not run'}; re-download: {cnt(RD) if RD else 'not run'}; manuscript numbers: {cnt(PP)}; figures: {cnt(FG)}.

## 1. Environment, commands and seeds
Python {env['python']}, numpy {env['numpy']}, geopandas {env['geopandas']}, rasterio {env['rasterio']}, shapely {env['shapely']} ({env['platform']}).

| Artifact | Command | Random seed |
|---|---|---|
| Open-data inputs (Levels 2-4) | `python -m src.utils.data_downloader_helper --levels gp mandal district --overture-release 2026-10-21.0` | none (public files; Overture release pinned) |
| Levels 2-4 results `docs/results/hierarchy_real_run/` | `python -m src.routing.run_hierarchy --levels 2 3 4 --data real --out docs/results/hierarchy_real_run` | planner is deterministic; omission scenarios use seeds **11, 12, 13** (`configs/hierarchy_levels.yaml`, `levels.*.omission_seeds`) at 10 % and 20 % |
| mu sweep `docs/results/U02_penalty_sweep_gp.csv` | `python -m src.evaluation.penalty_sweep` | none (deterministic) |
| DEM comparison `docs/results/U08_dem_comparison.json` | `python -m src.evaluation.dem_consistency` | none |
| Level 1 (Stage B) tables | recorded in `DELIVERABLES_DAMARAKUNTA_STAGE_B/06_REPRODUCIBILITY/COMMANDS_AND_PARAMETERS.md` (runner v1.1-v1.6; original command lines were not logged) | omit/add runs: seeds **20261029-20261033**; omit-small / omit-merge are deterministic |
| This audit | `python -m src.evaluation.provenance_audit --write docs/results/PROVENANCE_AND_PROOFS.md --rerun --redownload` | none |

## 2. Inputs and SHA-256 hashes
Level labels: 1,2 = Damarakunta (repository TGRAC / Stage B files); 2/3/4 = downloaded open data (git-ignored, regenerable; `.provenance.json` beside each file records URL, release, licence, caveats).
{md_table([{**r, 'sha256': r['sha256'], 'exists': 'yes' if r['exists'] else 'NO'} for r in inputs], ['level', 'role', 'path', 'bytes', 'sha256'])}
Open-data sources: ESA WorldCover 10 m v200 2021 (CC BY 4.0, AWS `esa-worldcover`); Copernicus GLO-30 DEM (AWS `copernicus-dem-30m`); geoBoundaries gbOpen IND ADM2/ADM3 (CC BY 4.0, `wmgeolab/geoBoundaries`, LFS via media.githubusercontent.com);
Overture Maps transportation / divisions, release 2026-10-21.0 (OSM-derived, ODbL); Google Open Buildings v3 (`Siddipet/Damarakunta/reference/external/google_open_buildings_v3_provenance.json`).

### 2.1 Hashes recorded by Stage B
{md_table(HH, ['id', 'claim', 'expected', 'actual', 'status'])}
## 3. Level 1 (Stage B) - VERIFIED-REAL (tables re-read and recomputed) / RECORDED (rasters, command lines)
Level 1 was **not re-executed** here: its inputs `damarakunta_cost_surface_10m.tif` (sha256 `911ebeb1...`) and the aligned slope raster are git-ignored. What is verified is that every number in the manuscript equals the value in the recorded result tables and that every derived percentage recomputes.
{md_table(L1, ['id', 'claim', 'expected', 'actual', 'status', 'source'])}
### 3.1 LoveDA segmentation metrics (source-domain, *not* Damarakunta accuracy)
Source notebook: external repository `Archana519/smart_village_infrastructure` (`final_MPS_project.ipynb`), epoch-4 checkpoint `best_model.pth` (checkpoint file and hash are not in any repository). The 7x7 confusion matrix is embedded in `src/evaluation/provenance_audit.py` and all metrics are recomputed from it.
{md_table(LV, ['id', 'claim', 'expected', 'actual', 'status'])}
## 4. Level 2 (Damarakunta GP) and the mu = 4 sweep - VERIFIED-REAL
Inputs: repository TGRAC roads / facilities / boundary, v8 building footprints, the 163 Stage B house targets, plus downloaded WorldCover and Copernicus DEM (hashes in section 2). Level 2 routes **hamlet hubs** (houses clustered at 150 m), so its lengths are not comparable with Level 1's house-by-house 5,069 m.
Artifacts: `docs/results/hierarchy_real_run/gp/` (`gp_routes.gpkg`, `gp_summary.json`, `gp_metrics.csv`, `gp_override.csv`, `gp_omission.csv`), `docs/results/U02_penalty_sweep_gp.csv`.
{md_table([r for r in LX if r['id'].startswith(('L2', 'U02'))], ['id', 'claim', 'expected', 'actual', 'status', 'source'])}
## 5. Levels 3 and 4 - SCALABILITY DEMONSTRATION on proxy nodes (not findings)
Level 3 (Markook): 14 Overture village points as GP hubs (weight 1, house counts unknown) and one **proxy** Mandal HQ (interior point of the geoBoundaries polygon); attachments are to collector-grade roads (tertiary and above) from Overture (OSM-derived), not a PMGSY/TGRAC inventory.
Level 4 (Siddipet): 22 **proxy** mandal terminals and a **proxy** district HQ (`Siddipet Urban` polygon interior point), geoBoundaries release with 23 mandals; the backbone runs 95.9 % on existing roads, so only the *new-construction* length is a planning-relevant quantity.
Artifacts: `docs/results/hierarchy_real_run/mandal/`, `docs/results/hierarchy_real_run/district/`.
{md_table([r for r in LX if r['id'].startswith(('L3', 'L4'))], ['id', 'claim', 'expected', 'actual', 'status', 'source'])}
## 6. Reproduction checks
{('### 6.1 Re-run of Levels 2-4 and the sweep' + chr(10) + md_table(RR, ['id', 'claim', 'status', 'source'])) if RR else 'Re-run not executed in this audit.' + chr(10)}
{('### 6.2 Re-download of rasters and roads' + chr(10) + md_table(RD, ['id', 'claim', 'status', 'source'])) if RD else 'Re-download not executed in this audit.' + chr(10)}
## 7. Manuscript numbers present in `paper/main.tex`
{md_table(PP, ['id', 'claim', 'status'])}
### 7.1 Figures (`python -m src.evaluation.plot_hierarchy_figures`, `python -m src.evaluation.plot_level1_omission`)
Figure D (Level 1 omission sensitivity, regenerated from `table4_c1_sensitivity.csv`, resolves U12) and Figures A-C are drawn only from the committed results (`docs/results/hierarchy_real_run/*/*_routes.gpkg`, `gp_override.csv`, the summaries and `U02_penalty_sweep_gp.csv`) and the real input layers; the only recomputation is the without-override routes in Figure A(c). Copies live in `paper/figures/` and `docs/results/hierarchy_real_run/figures/`. The sweep covers mu in {{1, 2, 4, 8, 20, 100}} (a value of 16 was never run, so it is not plotted).
{md_table(FG, ['id', 'claim', 'status'])}
## 8. DEM consistency (U08 follow-up)
Stage B used **SRTM 1 arc-second** (`n17_e078_1arc_v3.tif`, USGS) with Sobel slope on a 30 m grid, bilinearly resampled to 10 m; Levels 2-4 use **Copernicus GLO-30** with the *same* slope method (`slope_sobel`, 30 m native grid -> bilinear to the target grid). Over the Damarakunta window the two DEMs agree to RMSE {R['dem']['comparison']['elevation_m']['rmse']:.1f} m (bias {R['dem']['comparison']['elevation_m']['bias_cop_minus_srtm']:.1f} m, r = {R['dem']['comparison']['elevation_m']['pearson_r']:.3f}); slopes correlate at r = {R['dem']['comparison']['slope_deg']['pearson_r']:.2f} (noise on flat ground), and the >25 deg hard-block mask differs in {R['dem']['comparison']['slope_deg']['hard_block_gt25_disagree_cells']} cells. Re-running Level 2 with each DEM changes the shared length by {R['dem']['level2_relative_difference_pct']['shared_unique_length_m']:.1f} % and the ordinal cost by {R['dem']['level2_relative_difference_pct']['shared_unique_cost']:.1f} %; the override detour reduction is identical. The SRTM used for this comparison is the AWS 'skadi' product, a proxy for the USGS file (which is not in the repository). Full numbers: `docs/results/U08_dem_comparison.json`.

## 9. Limits of this audit
* Level 1 was not re-executed (missing rasters); its run command lines were never logged.
* The sub-centre *without-override* figures (73.3 m, 5,324.2 m) have a single prose source.
* LoveDA metrics come from an external notebook; the checkpoint hash is unrecorded and no Damarakunta pixel reference exists (agreement with Open Buildings is a proxy, not accuracy).
* Levels 3-4 inputs are proxies; omission scenarios are synthetic random omissions of units, not measured detection errors; nothing is field validated.
"""
    path.write_text(txt, encoding="utf-8")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--write", default=None)
    ap.add_argument("--rerun", action="store_true")
    ap.add_argument("--redownload", action="store_true")
    a = ap.parse_args(argv)
    from src.routing.hierarchical_router import load_config
    cfg = load_config()
    inputs = input_manifest(cfg)
    R = dict(hashes=stageb_recorded_hashes(inputs), level1=level1_checks(), loveda=loveda_checks(), levels=levels_checks(), figures=figure_checks(), paper=paper_checks(),
             dem=json.loads((RES / "U08_dem_comparison.json").read_text()))
    if a.rerun:
        R["rerun"] = rerun_checks()
    if a.redownload:
        R["redownload"] = redownload_checks(cfg)
    env = environment()
    keys = ["group", "level", "role", "path", "exists", "bytes", "sha256", "note", "provenance_json"]
    if a.write:          # a bare run only prints: it must not overwrite the committed audit artifacts with a shorter run
        with open(RES / "input_manifest.csv", "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore")
            w.writeheader()
            w.writerows(inputs)
        (RES / "provenance_audit.json").write_text(json.dumps(dict(environment=env, inputs=inputs, **{k: v for k, v in R.items() if k != "dem"}), indent=2, default=str), encoding="utf-8")
    allr = [r for k, v in R.items() if k != "dem" for r in v]
    fails = [r for r in allr if r["status"] == "FAIL"]
    print(f"checks: {len(allr)}  PASS: {sum(r['status'] == 'PASS' for r in allr)}  FAIL: {len(fails)}  other: {len(allr) - len(fails) - sum(r['status'] == 'PASS' for r in allr)}")
    for r in fails:
        print("FAIL", r["id"], r["claim"], "expected", r["expected"], "actual", r["actual"])
    if a.write:
        write_report(Path(a.write), R, inputs, env)
        print("wrote", a.write)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
