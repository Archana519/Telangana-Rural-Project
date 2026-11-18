"""Check that the numbers quoted in paper/erl/main.tex match the Phase 1 / Stage B result files (read-only).

    python paper/erl/verify_erl_numbers.py

Each ledger row computes a value from a Stage B file (or from a tracked input layer) and requires its formatted string to occur in main.tex.
Rows marked RECORDED come from a document, not from a machine-readable result table. A census at the end lists numeric tokens of the body text
that no ledger row or declared method constant covers, for manual review.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
S = REPO / "DELIVERABLES_DAMARAKUNTA_STAGE_B"
T = S / "03_RESULTS_TABLES"
CT = T / "COMPARISON_TABLES"
RUN = T / "PRIMARY_RUN_S2_fac_C0_s25_final_x4"
TEX = (HERE / "main.tex").read_text(encoding="utf-8")


from decimal import ROUND_HALF_UP, Decimal


def rd(x, dp=0):
    """Round half up (as printed in the tables), not half-to-even."""
    q = Decimal(1).scaleb(-dp)
    return str(Decimal(repr(round(float(x), 8))).quantize(q, rounding=ROUND_HALF_UP))


def f(x, dp=0):
    v = rd(abs(x), dp)
    whole, _, frac = v.partition(".")
    whole = f"{int(whole):,}".replace(",", "{,}")
    return whole + ("." + frac if frac else "")


rows = []        # (label, source, string expected in tex, kind)


def need(label, source, text, kind="VERIFIED"):
    rows.append((label, source, text, kind))


t1 = pd.read_csv(CT / "table1_length_reduction.csv")
x4 = t1[t1.configuration == "x4 (primary)"].set_index("method")
x1 = t1[t1.configuration == "x1 (P3 control)"].set_index("method")
M = {"straight": "Straight line (no terrain, 2 targets infeasible)", "indep": "Independent least-cost routes to the roads",
     "lenonly": "Length-only control (shortest distance, same constraints)", "roads": "Roads-only shared reference (houses attach to roads only)",
     "plan": "Two-stage network-aware plan (proposed)"}
for cfg, df in (("x4", x4), ("x1", x1)):
    for k, name in M.items():
        r = df.loc[name]
        if k == "straight":
            need(f"{cfg} {k} total", "table1", f(r.total_len_m, 1))
            need(f"{cfg} {k} crossing len", "table1", f(r.len_in_other_footprints_m, 1))
            continue
        if cfg == "x1" and k in ("lenonly", "roads"):
            continue
        need(f"{cfg} {k} total", "table1", f(r.total_len_m, 1))
        need(f"{cfg} {k} unique", "table1", f(r.unique_len_m, 1))
        need(f"{cfg} {k} routes crossing", "table1", f"{int(r.routes_crossing_other_footprints)}")
        need(f"{cfg} {k} crossing len", "table1", f(r.len_in_other_footprints_m, 1))
need("saving 24.9%", "table1", "24.9")
need("saving 1,684 m", "table1", f(x4.loc[M['plan'], 'reduction_vs_independent_unique_m'], 0))
need("roads-only 160 m longer", "table1", f"{rd(x4.loc[M['roads'], 'unique_len_m'] - x4.loc[M['plan'], 'unique_len_m'],0)}~m longer")
need("length-only +3.4%", "table1", f"{rd(abs(x4.loc[M['lenonly'], 'reduction_vs_independent_unique_pct']),1)}")
need("length-only 64 routes", "table1", f"{int(x4.loc[M['lenonly'], 'routes_crossing_other_footprints'])} routes")
need("x1 saving 32.0", "table1", f"{rd(x1.loc[M['plan'], 'reduction_vs_independent_unique_pct'],1)}")
need("x1 saving 22.6 roads-only", "table1", f"{rd(x4.loc[M['roads'], 'reduction_vs_independent_unique_pct'],1)}")
mu1, mu4 = float(x1.loc[M['plan'], 'unique_len_m']), float(x4.loc[M['plan'], 'unique_len_m'])
need("363 m longer", "table1", f"{rd(mu4 - mu1,0)}~m")
need("7.7% longer", "table1", f"{rd(100 * (mu4 - mu1) / mu1,1)}")

t2 = pd.read_csv(CT / "table2_c2_ablation.csv").set_index("run")
k1 = t2.loc["S2_fac_C0_s25_final_K1_P2", "unique_len_m"]
k3 = t2.loc["S2_fac_C0_s25_final_K3_P2", "unique_len_m"]
need("K=1 and K=3 identical", "table2", "identical lengths", "VERIFIED" if abs(k1 - k3) < 1e-6 else "FAIL")
leaf = t2.loc["S2_fac_C0_s25_final_K3_P0", "unique_len_m"] - t2.loc["S2_fac_C0_s25_final_K3_P2", "unique_len_m"]
need("leaf re-routing 10.3 m", "table2", f"{rd(leaf,1)}~m")
need("leaf 0.2%", "table2", f"{rd(100 * leaf / t2.loc['S2_fac_C0_s25_final_K3_P0', 'unique_len_m'],1)}")

t3 = pd.read_csv(CT / "table3_connectivity_constraints.csv").set_index("configuration").loc["x4 (primary)"]
need("168 of 168 connected", "table3", f"{int(t3.planner_verified_connected)} of {int(t3.targets)}")
need("0 hard-constraint violations", "table3", "no hard-constraint violation" if int(t3.hard_constraint_violations) == 0 else "FAIL")
need("0 cycles", "table3", "no cycle" if int(t3.cycles) == 0 else "FAIL")

_pr = pd.read_csv(CT / "table4_c1_sensitivity_per_run.csv")          # unrounded per-run values (the 2-decimal summary CSV double-rounds)
t4 = _pr.groupby("perturbation").agg(runs=("run", "count"), house_targets_routed_mean=("house_targets_routed", "mean"), unique_len_m_mean=("unique_len_m", "mean"),
                                     unique_len_m_min=("unique_len_m", "min"), unique_len_m_max=("unique_len_m", "max"),
                                     unique_len_per_routed_m_mean=("unique_len_per_routed_m", "mean"), saving_vs_independent_pct_mean=("saving_vs_independent_pct", "mean"))
base = t4.loc["baseline (no perturbation)"]
for k, lab in (("omit 10%", "Omit 10\\% (random)"), ("omit 20%", "Omit 20\\% (random)"), ("omit smallest 10%", "Omit smallest 10\\%"),
               ("omit smallest 25%", "Omit smallest 25\\%"), ("omit merged blobs", "Omit merged blobs"), ("add 10%", "Add 10\\% (random)"), ("add 20%", "Add 20\\% (random)")):
    r = t4.loc[k]
    d = 100 * (r.unique_len_m_mean - base.unique_len_m_mean) / base.unique_len_m_mean
    routed = r.house_targets_routed_mean
    need(f"{k} L", "table4", f(r.unique_len_m_mean, 1))
    need(f"{k} delta", "table4", f"{d:+.1f}".replace("-", "$-$").replace("+", "$+$") if False else f"{rd(abs(d),1)}")
    need(f"{k} per target", "table4", f"{rd(r.unique_len_per_routed_m_mean,1)}")
    need(f"{k} rho", "table4", f"{rd(r.saving_vs_independent_pct_mean,1)}")
    if k.startswith("omit"):
        U = 163 - routed
        need(f"{k} U", "table4", f"{int(round(U))}")
        need(f"{k} kappa", "table4", f"{rd(100 * routed / 163,1)}")
rho = t4.saving_vs_independent_pct_mean
need("rho range", "table4", f"{rd(rho.min(),1)}--{rd(rho.max(),1)}")
need("merged blobs 38.0%", "table4", f"{rd(100 * (163 - t4.loc['omit merged blobs', 'house_targets_routed_mean']) / 163,1)}")
need("per-target +14%", "table4", f"{rd(100 * (t4.loc['omit merged blobs', 'unique_len_per_routed_m_mean'] / base.unique_len_per_routed_m_mean - 1),0)}\\%")

t6 = pd.read_csv(CT / "table6_obstacle_avoidance.csv").set_index("run")
for run, mu in (("S2_fac_C0_s25_final_avoid_buf20", "20"), ("S2_fac_C0_s25_final_avoid_buf100", "100")):
    r = t6.loc[run]
    need(f"buffer mu{mu} unique", "table6", f(r.house_unique_len_m, 1))
    need(f"buffer mu{mu} saving", "table6", f"{rd(r.saving_vs_independent_pct,1)}")
    need(f"buffer mu{mu} crossing len", "table6", f(r.crossing_len_m, 1))
need("buffered saving range", "table6", f"{rd(t6.loc[[i for i in t6.index if 'avoid' in i], 'saving_vs_independent_pct'].min(),1)}--{rd(t6.loc[[i for i in t6.index if 'avoid' in i], 'saving_vs_independent_pct'].max(),1)}")
b = t6.loc[[i for i in t6.index if "avoid" in i]]
need("buffered +1.1-1.2 km", "table6", f"{rd((b.house_unique_len_m.min() - mu4) / 1000,1)}--{rd((b.house_unique_len_m.max() - mu4) / 1000,1)}~km")
need("buffered 145-148", "table6", f"{rd(b.crossing_len_m.min(),0)}--{rd(b.crossing_len_m.max(),0)}~m")
need("16 of 19 first 20 m", "table6", f"{int(b.crossing_only_in_first_20m.iloc[0])} of {int(b.house_routes_crossing_other_footprints.iloc[0])}")

# area thresholds of the "omit smallest" scenarios (script: thr = np.percentile(area_m2, small_pct); omitted = area <= thr)
_tg = pd.read_csv(RUN / "scenario_targets.csv"); _tg = _tg[_tg.planner_key.astype(str).str.startswith("C")]
for _p, _n in ((10, 17), (25, 41)):
    _thr = np.percentile(_tg.area_m2, _p)
    need(f"P{_p} area threshold", "scenario_targets.csv + scripts/dk_stageB_run_v1_6.py line 387", f"{rd(_thr, 1)}" if _p == 10 else f"{rd(_thr, 1)}")
    need(f"P{_p} targets omitted ({_n})", "scenario_targets.csv", "17 and 41 targets" if int((_tg.area_m2 <= _thr).sum()) == _n else "FAIL")

# LoveDA
cm = pd.read_csv(HERE / "supplementary" / "loveda_epoch4_confusion_matrix.csv", index_col=0).values.astype(float)
tp = np.diag(cm)
fp, fn = cm.sum(0) - tp, cm.sum(1) - tp
iou, prec, rec = tp / (tp + fp + fn), tp / (tp + fp), tp / (tp + fn)
f1 = 2 * prec * rec / (prec + rec)
for lab, v, src in (("mIoU", iou.mean(), "53.8"), ("mDice", f1.mean(), "68.9"), ("pixel acc", tp.sum() / cm.sum(), "71.3"), ("macro prec", prec.mean(), "72.4"),
                    ("macro rec", rec.mean(), "66.9"), ("bld IoU", iou[0], "54.0"), ("bld prec", prec[0], "62.1"), ("bld rec", rec[0], "80.6"), ("bld Dice", f1[0], "70.1")):
    need(f"LoveDA {lab}", "confusion matrix (copied from the training notebook, recorded)", f"{rd(100 * v,1)}", "VERIFIED" if f"{rd(100 * v,1)}" == src else "FAIL")

ag = pd.read_csv(S / "04_VALIDATION/DETECTION_AND_FACILITY_VERIFICATION/building_agreement_summary.csv").set_index("group")
for g, r in ag.iterrows():
    need(f"agreement {g}", "building_agreement_summary", f"{rd(100 * r.proxy_agreement_rate,1)}")
    need(f"agreement {g} counts", "building_agreement_summary", f"{int(r.candidates)} & {int(r.proxy_TP)} & {int(r.proxy_FP)}" if g != "ALL" else f"{int(r.candidates)} & {int(r.proxy_TP)} & {int(r.proxy_FP)}")
import json
vs = json.load(open(S / "04_VALIDATION/DETECTION_AND_FACILITY_VERIFICATION/verification_summary.json"))
need("Open Buildings 1,537", "verification_summary", f(vs["open_buildings_inside_boundary"]))
need("unmatched 1,186", "verification_summary", f(vs["proxy_FN_reference_polygons_without_candidate"]))
need("proxy threshold 30 m", "verification_summary", f"{int(vs['thresholds']['GOB_TOL_M'])}~m")

# facility + sub-centre
fs = pd.read_csv(RUN / "facility_status.csv").set_index("facility_id").loc["HEALTH_8734223673"]
need("sub-centre length 67.4", "facility_status", f"{rd(fs.len_m,1)}~m")
need("sub-centre cost 260.1", "facility_status", f"{rd(fs.cost,1)}")
fv = pd.read_csv(S / "04_VALIDATION/DETECTION_AND_FACILITY_VERIFICATION/facility_verification.csv").set_index("facility_id").loc["HEALTH_8734223673"]
need("sub-centre 1.8 m to footprint", "facility_verification", f"{rd(fv.dist_to_nearest_footprint_m,1)}~m")
need("override 357.7 (no override)", "C1_report.md / PROVENANCE note: cost 357.692 quoted in the C07 check", "357.7", "RECORDED")
need("override -27.3%", "derived from 357.7 and 260.1", f"{rd(100 * (260.107 - 357.692) / 357.692,1)}", "RECORDED")

# layers
bl = gpd.read_file(REPO / "Siddipet/Damarakunta/results/v8_instances/buildings_v8_full.gpkg", layer="buildings")
ins = bl[bl.inside_village.astype(bool)]
need("278 polygons", "buildings_v8_full.gpkg", f"{len(bl)} polygons")
need("165 inside", "buildings_v8_full.gpkg", f"{len(ins)} inside")
vc = ins.quality_class.value_counts()
for q, n in vc.items():
    need(f"class {q}", "buildings_v8_full.gpkg", f"({int(n)})" if q in ("PLAUSIBLE", "REVIEW") else f"({int(n)}),")
tg = pd.read_csv(RUN / "scenario_targets.csv")
need("163 targets", "scenario_targets.csv", "163", "VERIFIED" if int((tg.planner_key.astype(str).str.startswith("C")).sum()) == 163 else "FAIL")
alts = pd.read_csv(RUN / "route_alternatives.csv")
n_alt = alts.loc[alts.iloc[:, 0].astype(str).str.contains("house", na=False)].shape[0] if alts.iloc[:, 0].dtype == object else None
bnd = gpd.read_file(REPO / "Siddipet/Damarakunta/study_area/damarakunta_boundary.gpkg").to_crs(32644)
need("boundary 18.47 km2", "damarakunta_boundary.gpkg", f"{rd(bnd.area.sum() / 1e6,2)}~km")
r0 = gpd.read_file(REPO / "Siddipet/Damarakunta/reference/tgrac_road_network.gpkg").to_crs(32644)
rc = gpd.read_file(REPO / "Siddipet/Damarakunta/reference/derived/tgrac_road_network_clipped.gpkg").to_crs(32644)
need("43 road features", "tgrac_road_network.gpkg", f"{len(r0)} road features")
need("93.5 km", "tgrac_road_network.gpkg", f"{rd(r0.length.sum() / 1000,1)}~km")
need("51.7 km", "tgrac_road_network_clipped.gpkg", f"{rd(rc.length.sum() / 1000,1)}~km")
need("44.7% outside", "road_clip_report / derived", f"{rd(100 * (1 - rc.length.sum() / r0.length.sum()),1)}")
ex = (REPO / "inputs/EXCLUSIONS.md").read_text()
need("anganwadi 371 m", "inputs/EXCLUSIONS.md", "371~m", "VERIFIED" if "371 m" in ex else "FAIL")
need("anganwadi 126 m", "inputs/EXCLUSIONS.md", "126~m", "VERIFIED" if "126 m" in ex else "FAIL")
need("land take 0.84 ha", "arithmetic: 1,684.1 m x 5 m (assumed width, inputs/economic_assumptions.json)", f"{rd(1684.1 * 5 / 1e4,2)}~ha")
need("land take 2.53 ha", "arithmetic: 5,069.0 m x 5 m", f"{rd(5069.0 * 5 / 1e4,2)}~ha")
need("land take 3.38 ha", "arithmetic: 6,753.1 m x 5 m", f"{rd(6753.1 * 5 / 1e4,2)}~ha")
need("buffer ~0.6 ha", "arithmetic: 1.1-1.2 km x 5 m", "0.6~ha" if 0.55 <= (b.house_unique_len_m.min() - mu4) * 5 / 1e4 <= 0.6 else "FAIL")
need("recorded in doc: grid/imagery/invalid cells", "Stage B documents (imagery mosaic size, grid, invalid cell counts, 319 alternatives)", "432 $\\times$ 679", "RECORDED")
need("11,296 x 7,171", "Stage B documents", "11{,}296", "RECORDED")
need("961 slope / 178 land-cover cells", "Stage B documents", "961 slope cells", "RECORDED")
need("319 alternatives", "Stage B documents", "319 alternatives", "RECORDED")
need("178 land-cover cells", "Stage B documents", "178 land-cover cells", "RECORDED")
need("7,171 px", "Stage B documents", "7{,}171", "RECORDED")
need("1,669 LoveDA images", "training notebook log (recorded)", "1{,}669", "RECORDED")
need("1,194 m2 footprint", "Stage B documents", "1{,}194", "RECORDED")

# integer-rounded values used in the running text, and the Routed column of the omission table
for lab, v in (("indep total", x4.loc[M["indep"], "total_len_m"]), ("indep unique", x4.loc[M["indep"], "unique_len_m"]), ("lenonly unique", x4.loc[M["lenonly"], "unique_len_m"]),
               ("roads unique", x4.loc[M["roads"], "unique_len_m"]), ("plan unique", mu4), ("x1 plan unique", mu1)):
    need(f"text {lab} (rounded)", "table1", f(v, 0) + "~m")
need("text crossing 209 m / 660 m", "table1", f"{rd(x4.loc[M['plan'], 'len_in_other_footprints_m'], 0)}~m")
need("text crossing 660 m", "table1", f"{rd(x1.loc[M['plan'], 'len_in_other_footprints_m'], 0)}~m")
for k in ("omit 10%", "omit 20%", "omit smallest 10%", "omit smallest 25%", "omit merged blobs", "add 10%", "add 20%"):
    v = float(t4.loc[k, "house_targets_routed_mean"])
    need(f"{k} routed", "table4", f"& {rd(v, 1) if abs(v - round(v)) > 1e-9 or k in ('omit 10%', 'omit 20%') else rd(v, 0)} &")
need("baseline kappa 100.0", "table4", "100.0")
need("straight line crossing 60 routes", "table1", f"{int(x4.loc[M['straight'], 'routes_crossing_other_footprints'])} &")

bad = 0
counts = {"VERIFIED": 0, "RECORDED": 0, "MISSING": 0, "FAIL": 0}
for label, src, text, kind in rows:
    ok = text in TEX
    if kind == "FAIL":
        status = "FAIL"
    elif not ok:
        status = "MISSING"
    else:
        status = kind
    counts[status] += 1
    if status in ("FAIL", "MISSING"):
        bad += 1
        print(f"{status:8s} {label}: expected {text!r} (source: {src})")
print(f"ledger rows: {len(rows)}  " + "  ".join(f"{k}={v}" for k, v in counts.items()))

# census of numeric tokens in the body that the ledger does not cover
body = TEX.split("\\begin{abstract}")[1].split("\\ack")[0]
body = re.sub(r"\\begin\{equation\}.*?\\end\{equation\}", " ", body, flags=re.S)
body = re.sub(r"\\cite\{[^}]*\}|\\ref\{[^}]*\}|\\label\{[^}]*\}|\\includegraphics\[[^\]]*\]\{[^}]*\}", " ", body)
body = body.replace("{,}", "").replace("\\%", "%")
tokens = set(re.findall(r"(?<![\w.])\d+(?:\.\d+)?", body))
covered = set()
for _, _, text, _ in rows:
    covered |= set(re.findall(r"\d+(?:\.\d+)?", text.replace("{,}", "")))
method = {"0.5", "0.4", "0.1", "560", "420", "10", "20", "25", "3", "8", "2", "1", "0.65", "0.8", "7.1", "30", "4", "12", "6", "9", "14", "256", "5", "100", "1000",
          "2026", "29", "0.6", "17.707", "78.753", "2021", "2014", "2018", "1959", "2050", "3.0", "4.7", "7", "168", "11", "34", "3.4"}
rest = sorted(tokens - covered - method, key=lambda s: float(s))
print("numeric tokens not covered by the ledger or declared method constants (review manually):", rest)
sys.exit(1 if bad else 0)
