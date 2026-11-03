"""Find printed page numbers of headings/captions in the exported PDF -> pages.json."""
import json, re, sys, os
import pymupdf
pdf, ent, out = sys.argv[1], sys.argv[2], sys.argv[3]
E = json.load(open(ent, encoding="utf-8"))
d = pymupdf.open(pdf)
norm = lambda s: re.sub(r"\s+", " ", s.replace("\u00a0", " ")).strip()
T = [norm(p.get_text()) for p in d]
main = next(i for i, t in enumerate(T) if "1. INTRODUCTION" in t)
roman = lambda n: ["", "i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x", "xi", "xii"][n]
res = {"toc": {}, "tables": {}, "figures": {}}
def find(s, start=main):
    s = norm(s)
    for i in range(start, len(T)):
        if s in T[i]: return i
    return None
miss = []
for key in E["toc"]:
    num, title = key.split("|", 1)
    lvl1 = "." not in num
    s = "REFERENCES" if not num else ("%s. %s" % (num, title.upper()) if lvl1 else "%s %s" % (num, title))
    i = find(s)
    if i is None: miss.append(s); continue
    res["toc"][key] = i - main + 1
for n, text in E["tables"]:
    i = find("Table %d. %s" % (n, re.sub(r"\.*", "", text)[:22]))
    if i is None: miss.append("Table %d" % n); continue
    res["tables"][str(n)] = i - main + 1
for n, text in E["figures"]:
    i = find("Figure %d. %s" % (n, text[:22]))
    if i is None: miss.append("Figure %d" % n); continue
    res["figures"][str(n)] = i - main + 1
lot = next(i for i, t in enumerate(T[:main]) if "List of Tables Table No." in t)
lof = next(i for i, t in enumerate(T[:main]) if "List of Figures Figure No." in t)
res["lot_roman"], res["lof_roman"] = roman(lot + 1), roman(lof + 1)
json.dump(res, open(out, "w", encoding="utf-8"))
print("main starts at pdf page", main + 1, "total", len(T), "missing:", miss)
