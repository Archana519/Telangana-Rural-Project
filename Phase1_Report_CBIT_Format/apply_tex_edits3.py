import json, re, sys
p = sys.argv[1]
L = open(p, encoding="utf-8").read().split("\n")
n0 = len(L)
a = r"Figure~\ref{fig:arch} shows the layered architecture and Figure~\ref{fig:flow} the workflow through the 20 modules. Table~\ref{tab:modules} lists each module's"
assert a in L[245], L[245][:120]
L[245] = L[245].replace(a, r"Figure~\ref{fig:arch} shows the architecture in nine stages and Figure~\ref{fig:flow} the flow from inputs through scripts to outputs. Section 5.2 describes each stage. Table~\ref{tab:modules} lists the 20 implementation modules, with each module's")
assert len(L) == n0
open(p, "w", encoding="utf-8").write("\n".join(L))

# DOI case: IEEE DOIs are written with upper-case suffixes
def up(doi):
    return re.sub(r"^(10\.1109/)(.*)$", lambda m: m.group(1) + m.group(2).upper(), doi)
b = open("source_tex/references.bib", encoding="utf-8").read()
b = re.sub(r"doi=\{(10\.1109/[^}]*)\}", lambda m: "doi={%s}" % up(m.group(1)), b)
open("source_tex/references.bib", "w", encoding="utf-8").write(b)
m = json.load(open("lit_verified.json", encoding="utf-8"))
for x in m:
    x["doi"] = up(x["doi"]); x["url"] = "https://doi.org/" + x["doi"]
json.dump(m, open("lit_verified.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
import csv
rows = list(csv.reader(open("literature_verification.csv", encoding="utf-8-sig")))
for r in rows[1:]:
    r[8] = up(r[8]); r[9] = "https://doi.org/" + r[8]
csv.writer(open("literature_verification.csv", "w", newline="", encoding="utf-8-sig")).writerows(rows)
print("ok")
