"""One-off patch (kept for provenance): scores read in the open-access preprint (arXiv) versions of six papers are added to literature table 2.
Text of the preprints was read from the PDFs; numbers are copied from them and are labelled as preprint figures (the published IEEE version may differ)."""
import csv
import re

R = r"D:\Telangana_Rural_Project\Phase1_Report_CBIT_Format"
PRE = {
    "L03": "mean IoU higher by 2.73% (Inria) and 3.26% (MAS) than the baseline, and by 1.51% over the second-best method on Inria",
    "L05": "F1 of 75.08% for DeepLabv3-CG on Berlin TerraSAR-X data, F1 and IoU 4.40% and 5.45% higher with complete footprints than with sensor-visible segments, and a mean building-height error of 2.39 m",
    "L19": "F1 higher by 3.21% (buildings) and 3.38% (roads) than the baseline (81.85% and 71.03%)",
    "L31": "mean IoU of 74.62% (ISPRS-Potsdam) and 50.97% (LoveDA) with 5% labels, against 72.01% and 44.20% without the proposed modules",
    "L44": "best segmentation accuracy of 48.06% and 52.03% in the two adaptation directions",
    "L39": "IoU higher than the best baseline by 1.25% (OSM) and 0.52% (SpaceNet), and APLS 0.8028 against 0.7843 on OSM",
}
t1 = open(R + r"\source_tex\lit_table1.tex", encoding="utf-8").read().split("\n")
t2p = R + r"\source_tex\lit_table2.tex"
t2 = open(t2p, encoding="utf-8").read().split("\n")
key_of = {int(m.group(1)): m.group(2) for l in t1 for m in [re.match(r"^(\d+) & .*\\cite\{(L\d+)\}", l)] if m}
OLD = " Quantitative score: not stated in the abstract."
n_done = 0
for i, l in enumerate(t2):
    m = re.match(r"^(\d+) & ", l)
    if not m:
        continue
    k = key_of[int(m.group(1))]
    if k not in PRE:
        continue
    txt = PRE[k].replace("%", "\\%")
    if OLD in l:
        t2[i] = l.replace(OLD, " Reported result (open-access preprint version): " + txt + ".")
    else:
        assert "Reported result:" in l, k
        t2[i] = re.sub(r"(Reported result: [^&]*?\.)( \\\\)?$", lambda mm: mm.group(1) + " Further, in the open-access preprint: " + txt + "." + (mm.group(2) or ""), l.rstrip())
    n_done += 1
assert n_done == 6, n_done
open(t2p, "w", encoding="utf-8").write("\n".join(t2))

rows = list(csv.reader(open(R + r"\literature_quantitative_results.csv", encoding="utf-8-sig")))
hdr, body = rows[0], rows[1:]
for r in body:
    if r[1] in PRE:
        r[2] = (r[2] + "; " if r[2] else "") + "preprint: " + PRE[r[1]]
        r[3] = "stated in abstract and preprint" if r[3] == "stated in abstract" else "from open-access preprint"
with open(R + r"\literature_quantitative_results.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(hdr)
    w.writerows(body)
print("ok", sum(1 for r in body if r[2]))

p = R + r"\source_tex\A_Dissertation_Phase_I_Review_1_Report_Final.tex"
s = open(p, encoding="utf-8").read()
a = "Numerical scores are quoted exactly as stated in the paper abstracts (nine of the 35 abstracts state scores); the other entries say that no score is stated in the abstract, or that the abstract could not be retrieved (three papers), and no figure is quoted from memory. "
assert s.count(a) == 1
b = ("Numerical scores are quoted exactly as stated in the paper abstracts (nine of the 35 abstracts state scores) and, for five more papers whose open-access preprints could be read, as stated in the preprint text; "
     "these preprint figures may differ from the published IEEE version. The other entries say that no score is stated in the abstract, or that the abstract could not be retrieved (three papers), and no figure is quoted from memory. ")
open(p, "w", encoding="utf-8").write(s.replace(a, b))
