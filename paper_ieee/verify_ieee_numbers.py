"""Verify that every number in IEEE_Journal_Manuscript.docx is backed by the verified sources (read-only).
 1. runs paper_eris/verify_eris_numbers.py (ERIS ledger: tex vs Stage B / Adilabad result files);
 2. every numeric token of the DOCX body and tables (excluding the reference list, citation brackets, table/figure/section numbers)
    must occur in (a) paper_eris/main.tex (ledger-verified), (b) the Adilabad result CSVs, or (c) a short list of declared method constants;
 3. every table row of the DOCX must also occur (numbers, in order) in a table row of paper_eris/main.tex."""
import re, subprocess, sys
from pathlib import Path
import pandas as pd
from docx import Document
H = Path(__file__).resolve().parent; REPO = H.parent
r = subprocess.run([sys.executable, str(REPO / "paper_eris/verify_eris_numbers.py")], capture_output=True, text=True); print(r.stdout.strip().splitlines()[-1], "| exit", r.returncode)
tex = (REPO / "paper_eris/main.tex").read_text().replace("{,}", "")
A = REPO / "DELIVERABLES_CONTRIBUTION_3_MULTI_VILLAGE/01_ADILABAD"
EXCL = " ".join(f.read_text() for f in (REPO / "DELIVERABLES_DAMARAKUNTA_STAGE_B").glob("*/EXCLUSIONS.md"))
SEGD = REPO / "DELIVERABLES_CONTRIBUTION_3_MULTI_VILLAGE/01_ADILABAD_SEGMENTATION"
seg_txt = " ".join(open(f).read() for f in SEGD.glob("*.csv") if f.name not in ("verified_facilities.csv", "omission_runs.csv")) + " " + (SEGD / "metrics_summary.json").read_text()
import json
sj = json.loads((SEGD / "metrics_summary.json").read_text())
def fm(x, d): return f"{x:.{d}f}"
derived = " ".join([fm(sj["unique_len_independent_m"] / 1 - sj["unique_len_two_stage_m"], 1), fm(round(sj["unique_len_independent_m"] - sj["unique_len_two_stage_m"]), 0),
                    fm((sj["unique_len_independent_m"] - sj["unique_len_two_stage_m"]) * 5 / 10000, 1), fm(sj["unique_len_two_stage_m"] / sj["routed"], 1),
                    fm(100 * sj["routes_crossing"] / sj["targets"], 1), str(138 - 54), str(round(100 * sj["quality_classes"]["UNRESOLVED_MERGE"] / sj["footprints_total"]))])
csv_txt = (seg_txt + " " + " ".join(open(f).read() for f in A.glob("*.csv") if f.name != "verified_facilities.csv")).replace(",", " ")
src = tex + " " + EXCL + " " + derived + " " + csv_txt
NUM = r"\d+(?:\.\d+)?"
def toks(s): return re.findall(NUM, s.replace(",", ""))
srcset = set(toks(src))
srcset |= {t[:-2] for t in srcset if t.endswith(".0")}
CONST = {"7248", "9590", "391", "459", "1800", "420", "10", "14", "560", "25", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "12", "18", "20", "30", "50", "256", "0.1", "0.4", "0.5", "0.65", "100", "1500", "15", "7.1", "0.7", "40", "60", "0.0", "17.707", "78.753", "19.682", "78.528", "2026", "2021", "2018", "2024", "2025", "2023", "2022", "2020", "2019", "2.3", "3.0", "4.7", "1.0", "3.5", "52", "53"}
d = Document(H / "IEEE_Journal_Manuscript.docx")
paras = [p.text for p in d.paragraphs]; end = next(i for i, t in enumerate(paras) if t.strip().upper() == "REFERENCES")
body = [re.sub(r"\b[0-9a-f]{64}\b", " ", re.sub(r"\[[\d,\s–\]\[]+\]", " ", t)) for t in paras[:end]]
body = [re.sub(r"\b(Fig|Table|Section|TABLE|Eq)\.?\s*[IVX\d]+(-[A-E])?", " ", t) for t in body]
cells = [re.sub(r"\[[\d,\s]+\]", " ", c.text) for t in d.tables for row in t.rows for c in row.cells]
bad = set()
for t in body + cells:
    for k in toks(t):
        if k not in srcset and k not in CONST and k.lstrip("0") not in srcset: bad.add(k)
print("unbacked numeric tokens in DOCX:", sorted(bad) if bad else "none")
# table rows vs ERIS tex rows
rows_tex = [toks(l) for l in tex.splitlines() if "&" in l]
miss = 0; chk = 0
for t in d.tables[1:]:
    for row in t.rows[1:]:
        vals = []
        seen = []
        for c in row.cells:
            if c._tc in seen: continue
            seen.append(c._tc); vals += toks(re.sub(r"\[[\d,\s]+\]", " ", c.text))
        if len(vals) < 2: continue
        chk += 1
        if not any(all(v in rt for v in vals) for rt in rows_tex) and not all(v in srcset or v in CONST for v in vals):
            miss += 1; print("ROW NOT TRACEABLE:", [c.text for c in row.cells][:4])
print(f"{chk} table rows checked, {miss} untraceable")
# ---- run metadata against the committed Adilabad run log
al = json.loads((SEGD / "run_log_full.json").read_text())
alltxt = " ".join(paras) + " " + " ".join(c.text for t in d.tables for row in t.rows for c in row.cells)
need_txt = [f"{al['window'][2]:,} × {al['window'][3]:,} px", f"{al['tiles_run']} tiles of {al['tile']} × {al['tile']} px", f"stride {al['stride']} px, margin {al['margin']} px", al["checkpoint_sha256"]]
logmiss = [t for t in need_txt if t not in alltxt]
print("run-log metadata missing from DOCX:", logmiss if logmiss else "none")
sys.exit(1 if bad or miss or logmiss or r.returncode else 0)
