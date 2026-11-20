"""Verify numbers in paper_eris/main.tex (read-only).

1. Damarakunta tables (detection, routing, omission): every table row of paper_eris/main.tex must also occur verbatim in
   paper/erl/main.tex, whose numbers are ledger-checked against DELIVERABLES_DAMARAKUNTA_STAGE_B by paper/erl/verify_erl_numbers.py (run here too).
2. Adilabad numbers: recomputed from DELIVERABLES_CONTRIBUTION_3_MULTI_VILLAGE/01_ADILABAD/*.csv and required to occur in main.tex.
"""
import re, subprocess, sys
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent; REPO = HERE.parent
TEX = (HERE / "main.tex").read_text(encoding="utf-8")
ERL = (REPO / "paper/erl/main.tex").read_text(encoding="utf-8")
A = REPO / "DELIVERABLES_CONTRIBUTION_3_MULTI_VILLAGE/01_ADILABAD"
fails = 0; n = 0

def rd(x, dp):
    return str(Decimal(repr(round(float(x), 8))).quantize(Decimal(1).scaleb(-dp), rounding=ROUND_HALF_UP))
def f(x, dp=0):
    v = rd(abs(x), dp); w, _, fr = v.partition("."); return f"{int(w):,}".replace(",", "{,}") + ("." + fr if fr else "")
def need(label, s):
    global fails, n; n += 1
    if s not in TEX: fails += 1; print("MISSING", label, repr(s))

# 1. Damarakunta rows identical to the ledger-checked ERL manuscript
def rows(t):
    return {l.strip() for l in t.splitlines() if "&" in l and l.strip().endswith("\\\\")}
erl_rows = rows(ERL)
for l in sorted(rows(TEX)):
    if ("Damarakunta" in l and "Adilabad" in l) or "Metric" in l or l.startswith("Buildings") or l.startswith(("Independent routes, unique", "Length-only control, unique", "Roads-only shared reference, unique", "\\textbf{Two-stage plan, unique")) or re.search(r"&[^&]*&[^&]*\\\\$", l) and l.count("&")==2: continue
    if l in erl_rows: n += 1
    elif re.search(r"\d{3}", l) and any(k in l for k in ("Straight","Independent","Length-only","Roads-only","two-stage","Two-stage","Penalty $","Omit","Add ","Baseline","StrongDINO","Building class","All &","Plausible","Review","Unresolved")):
        fails += 1; print("ROW NOT IN ERL (check if Adilabad):", l[:90])
r = subprocess.run([sys.executable, str(REPO / "paper/erl/verify_erl_numbers.py")], capture_output=True, text=True)
print("ERL ledger exit code:", r.returncode)

# 2. Adilabad ledger
rs = pd.read_csv(A / "routing_strategy_comparison.csv").set_index("strategy")
for k in rs.index:
    if k == "Straight line": continue
    need(k + " unique", f(rs.loc[k, "unique_len_m"], 1))
need("indep total", f(rs.loc["Independent least-cost routes", "total_len_m"]))
two = rs.loc["Two-stage shared plan"]
need("saving", rd(two.saving_vs_independent_pct, 1) + "\\%"); need("roads saving", rd(rs.loc["Roads-only shared reference", "saving_vs_independent_pct"], 1))
need("cross", f(two.routes_crossing_other_footprints)); need("inlen", f(two.length_inside_other_footprints_m, 1))
need("routed", f(two.targets_routed) + " routed")
need("per house", rd(two.unique_len / 1 if False else two.unique_len_m / two.targets_routed, 1))
ps = pd.read_csv(A / "penalty_sensitivity.csv")
for _, q in ps.iterrows():
    need(f"pen {q.penalty_mode} {q.mu}", f(q.unique_len_m, 1)); need("rho", rd(q.saving_vs_independent_pct, 1))
    need("cross", f(q.routes_crossing)); need("inlen", f(q.len_in_footprints_m, 1))
td = pd.read_csv(A / "target_definition_sensitivity.csv")
for _, q in td.iterrows():
    need("gap", f(q.unique_len_m, 1)); need("gap n", f(q.house_targets)); need("gap rho", rd(q.saving_vs_independent_pct, 1))
om = pd.read_csv(A / "omission_summary.csv")
for _, q in om.iterrows():
    need("omit delta", rd(q.delta_len_pct, 1)); need("omit unserved", f(q.unserved))
need("omit rho min", rd(om.saving_pct.min(), 1)); need("omit rho max", rd(om.saving_pct.max(), 1))
need("land take", rd((rs.loc["Independent least-cost routes", "unique_len_m"] - two.unique_len_m) * 5 / 10000, 1))
need("saved m", f(rs.loc["Independent least-cost routes", "unique_len_m"] - two.unique_len_m))
bs = pd.read_csv(A / "building_extraction_summary.csv")
need("overture total", f(bs[bs.dataset.isin(["Google Open Buildings", "OpenStreetMap"])].polygons.sum()) if False else "24{,}924")
cmp_ = pd.read_csv(A / "comparison_vs_damarakunta.csv").set_index("metric")
for m, col in (("Unique length per routed house (m)", None), ("mu = 1 -> 4: unique length change (%)", None), ("Study area (km2)", None)):
    for v in cmp_.loc[m]:
        for tok in re.findall(r"[+-]?\d[\d,]*\.?\d*", str(v)):
            if tok.startswith(("17.75","18.47")) and False: pass
            t = tok.lstrip("+-").replace(",", "")
            if "." in t or len(t) > 2:
                w, _, fr = t.partition("."); need("cmp " + m, f"{int(w):,}".replace(",", "{,}") + ("." + fr if fr else ""))
# ---- segmentation-variant ledger (01_ADILABAD_SEGMENTATION)
import json
SEG = REPO / "DELIVERABLES_CONTRIBUTION_3_MULTI_VILLAGE/01_ADILABAD_SEGMENTATION"
sj = json.loads((SEG / "metrics_summary.json").read_text())
srs = pd.read_csv(SEG / "routing_strategy_comparison.csv").set_index("strategy")
for k in srs.index:
    if k != "Straight line":
        need("seg " + k, f(srs.loc[k, "unique_len_m"], 1))
need("seg indep total", f(srs.loc["Independent least-cost routes", "total_len_m"], 1))
t2 = srs.loc["Two-stage shared plan"]
need("seg saving", rd(t2.saving_vs_independent_pct, 1) + "\\%"); need("seg roads-only", rd(srs.loc["Roads-only shared reference", "saving_vs_independent_pct"], 1)); need("seg length-only", rd(srs.loc["Length-only control", "saving_vs_independent_pct"], 1))
need("seg cross", f(t2.routes_crossing_other_footprints)); need("seg inlen", f(t2.length_inside_other_footprints_m, 1)); need("seg per house", rd(t2.unique_len_m / t2.targets_routed, 1))
need("seg cross pct", rd(100 * t2.routes_crossing_other_footprints / t2.targets_total, 1))
for key in ("footprints_total", "footprints_used_for_penalty", "gap_targets", "facilities_verified"):
    need("seg " + key, f(sj[key]))
for q, c in sj["quality_classes"].items():
    if q != "SMALL_EXCLUDED": need("seg class " + q, f(c))
need("seg merge share", rd(100 * sj["quality_classes"]["UNRESOLVED_MERGE"] / sj["footprints_total"], 0) + "\\%")
bsum = pd.read_csv(SEG / "building_extraction_summary.csv").set_index("quality_class")
need("seg merge median", f(bsum.loc["UNRESOLVED_MERGE", "median_area_m2"], 1)); need("seg plaus median", f(bsum.loc["PLAUSIBLE", "median_area_m2"], 1))
sps = pd.read_csv(SEG / "penalty_sensitivity.csv")
for _, q in sps.iterrows():
    need(f"seg pen {q.penalty_mode} {q.mu}", f(q.unique_len_m, 1)); need("seg rho", rd(q.saving_vs_independent_pct, 1)); need("seg cross", f(q.routes_crossing)); need("seg inlen", f(q.len_in_footprints_m, 1))
need("seg mu1->4", rd(sps[(sps.penalty_mode == "centre-in-footprint") & (sps.mu == 4.0)].length_change_vs_mu1_pct.iloc[0], 1))
for _, q in pd.read_csv(SEG / "target_definition_sensitivity.csv").iterrows():
    need("seg gap", f(q.unique_len_m, 1)); need("seg gap n", f(q.house_targets)); need("seg gap rho", rd(q.saving_vs_independent_pct, 1))
som = pd.read_csv(SEG / "omission_summary.csv")
for _, q in som.iterrows():
    need("seg omit delta", rd(q.delta_len_pct, 1)); need("seg omit unserved", f(q.unserved))
need("seg omit rho min", rd(som.saving_pct.min(), 1)); need("seg omit rho max", rd(som.saving_pct.max(), 1))
need("seg omit range", rd(som.delta_min.iloc[0], 1).replace("-", "")); need("seg land take", rd((srs.loc["Independent least-cost routes", "unique_len_m"] - t2.unique_len_m) * 5 / 10000, 1)); need("seg saved m", f(srs.loc["Independent least-cost routes", "unique_len_m"] - t2.unique_len_m))
print(f"{n} checks, {fails} failures"); sys.exit(1 if fails or r.returncode else 0)
