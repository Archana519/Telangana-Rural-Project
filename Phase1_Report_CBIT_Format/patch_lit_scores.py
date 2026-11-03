"""One-off patch (kept for provenance): quantitative results as stated in each paper's abstract are added to the literature table 2 (third column).
Numbers were copied from the abstracts retrieved from OpenAlex / Crossref / arXiv (lit_abstracts.json); nothing was taken from memory.
Papers whose abstract states no score are marked as such."""
import csv
import json
import re

R = r"D:\Telangana_Rural_Project\Phase1_Report_CBIT_Format"
SC = {
    "L09": "building-roof F1 77.05% and IoU 63.55%; whole-building F1 79.02% and IoU 66.05%, the best among the baseline models",
    "L18": "54.5% mIoU (LoveDA), 87.8% (Potsdam) and 84.1% (Vaihingen) at 132.7 FPS; 72.6% mIoU at 164.0 FPS (CityScapes) and 72.3% mIoU at 186.4 FPS (CamVid)",
    "L21": "F1 higher by 4.3 to 7.2 points and IoU higher by 4.9 to 8.0 points than the strong baseline on MSAW",
    "L22": "IoU +1.49%, +1.16%, +2.26% and F1 +0.82%, +0.70%, +1.22% over HD-Net on WHU, Inria and AIRS",
    "L23": "IoU of 0.8556, 0.8163 and 0.7797 on the three datasets",
    "L35": "mean IoU 67.60% (iSAID), 55.86% (LoveDA), 80.07% (Potsdam) and 96.46% (Vaihingen)",
    "L38": "F1 improved by 3.3% to 4.5% and IoU by 2.0% to 5.1% over state-of-the-art methods",
    "L39": "IoU of 70.71% (SpaceNet) and 75.52% (OSM)",
    "L42": "computation more than 1000 times faster than MILP, and an investment decrease of 30% or more with shortest-path distance instead of Euclidean or Manhattan distance",
}
A = json.load(open(R + r"\lit_abstracts.json", encoding="utf-8"))
t1 = open(R + r"\source_tex\lit_table1.tex", encoding="utf-8").read().split("\n")
t2p = R + r"\source_tex\lit_table2.tex"
t2 = open(t2p, encoding="utf-8").read().split("\n")
key_of = {}
for l in t1:
    m = re.match(r"^(\d+) & .*\\cite\{(L\d+)\}", l)
    if m:
        key_of[int(m.group(1))] = m.group(2)
assert len(key_of) == 35
rows = []
for i, l in enumerate(t2):
    m = re.match(r"^(\d+) & ", l)
    if not m:
        continue
    n = int(m.group(1))
    k = key_of[n]
    cells = l.rstrip().rstrip("\\").split(" & ")
    assert len(cells) == 4, (n, len(cells))
    if k in SC:
        add = " Reported result: " + SC[k].replace("%", "\\%") + "."
        status = "stated in abstract"
    elif A.get(k):
        add = " Quantitative score: not stated in the abstract."
        status = "no score in abstract"
    else:
        add = " Quantitative score: abstract not retrievable from the DOI registries."
        status = "abstract not retrievable"
    cells[2] = cells[2].rstrip() + add
    t2[i] = " & ".join(cells) + " \\\\"
    rows.append((n, k, SC.get(k, ""), status))
open(t2p, "w", encoding="utf-8").write("\n".join(t2))
with open(R + r"\literature_quantitative_results.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["table_no", "key", "reported_result_from_abstract", "status"])
    w.writerows(rows)
print(len(rows), sum(1 for r in rows if r[3] == "stated in abstract"))
