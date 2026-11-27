"""Prefix the dataset records of the reference list with Elsevier's [dataset] tag (run between bibtex and the last two pdflatex passes)."""
import re
from pathlib import Path

DATASETS = ["zanaga2021worldcover", "esa2022copdem", "overture2026", "esri2026worldimagery", "ds_loveda"]
p = Path(__file__).with_name("main.bbl")
t = p.read_text(encoding="utf-8")
n = 0
for k in DATASETS:
    pat = re.compile(r"(\\bibitem(?:\[[^\]]*\])?\{" + re.escape(k) + r"\}\s*\n)(?!\[dataset\])")
    t, c = pat.subn(r"\1[dataset] ", t)
    n += c
p.write_text(t, encoding="utf-8")
print("tagged [dataset]:", n, "of", len(DATASETS))
