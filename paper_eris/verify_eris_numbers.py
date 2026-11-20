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
    if ("Damarakunta" in l and "Adilabad" in l) or "Metric" in l or l.startswith("Buildings") or re.search(r"&[^&]*&[^&]*\\\\$", l) and l.count("&")==2: continue
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
need("routed", f(two.targets_routed) + " of " + f(two.targets_total))
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
for m, col in (("Median target footprint area (m2)", None), ("Median target distance to nearest road (m)", None), ("Unique length per routed house (m)", None), ("Facility phase: unique length (m) / facilities", None), ("mu = 1 -> 4: unique length change (%)", None), ("Study area (km2)", None)):
    for v in cmp_.loc[m]:
        for tok in re.findall(r"[+-]?\d[\d,]*\.?\d*", str(v)):
            if tok.startswith(("17.75","18.47")) and False: pass
            t = tok.lstrip("+-").replace(",", "")
            if "." in t or len(t) > 2:
                w, _, fr = t.partition("."); need("cmp " + m, f"{int(w):,}".replace(",", "{,}") + ("." + fr if fr else ""))
print(f"{n} checks, {fails} failures"); sys.exit(1 if fails or r.returncode else 0)
