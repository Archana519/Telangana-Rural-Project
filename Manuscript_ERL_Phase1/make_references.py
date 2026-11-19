"""Typeset references.bib as an ERL Harvard (author year) list: references.tex (natbib \\bibitem labels). Run: python make_references.py"""
import re, sys
from pathlib import Path
here = Path(__file__).parent
bib = (here / "references.bib").read_text(encoding="utf-8")
body = (here / "body.tex").read_text(encoding="utf-8")
cited = set(re.findall(r"\\citealt\{([^}]*)\}", body)) | set(re.findall(r"\\citep?\{([^}]*)\}", body))
cited = {k.strip() for c in cited for k in c.split(",")}

def parse(text):
    out = {}
    for m in re.finditer(r"@(\w+)\{([^,]+),", text):
        typ, key = m.group(1).lower(), m.group(2)
        i, depth = m.end(), 1
        j = i
        while depth:
            c = text[j]
            depth += (c == "{") - (c == "}")
            j += 1
        fields = {}
        for f in re.finditer(r"(\w+)\s*=\s*", text[i:j - 1]):
            s = i + f.end()
            if text[s] == "{":
                d, e = 1, s + 1
                while d:
                    d += (text[e] == "{") - (text[e] == "}")
                    e += 1
                fields[f.group(1).lower()] = text[s + 1:e - 1]
        out[key] = (typ, fields)
    return out

def initials(first):
    parts = [p for p in re.split(r"[\s]+", first.replace("-", " ")) if p]
    return " ".join(re.sub(r"^\{?\\.\{?(\w)\}?.*", r"\1", p)[0] if p[0] != "\\" and p[0] != "{" else p[3] if len(p) > 3 else p for p in parts)

def names(a):
    if a.startswith("{"):
        return a.strip("{}"), a.strip("{}")
    auth = [x.strip() for x in a.split(" and ")]
    fmt = []
    for x in auth:
        last, _, first = x.partition(",")
        fmt.append(f"{last.strip()} {initials(first.strip())}")
    if len(fmt) == 1: s = fmt[0]
    else: s = ", ".join(fmt[:-1]) + " and " + fmt[-1]
    l = [x.partition(",")[0].strip() for x in auth]
    lab = l[0] if len(l) == 1 else (f"{l[0]} and {l[1]}" if len(l) == 2 else l[0] + " {\\it et al}")
    return s, lab

entries = parse(bib)
lines = ["\\begin{thebibliography}{99}", "\\providecommand{\\url}[1]{\\texttt{#1}}"]
for key in sorted(cited, key=lambda k: (names(entries[k][1]["author"])[1].lower(), entries[k][1]["year"])):
    typ, f = entries[key]
    s, lab = names(f["author"])
    y = f["year"]
    t = f["title"]
    tail = ""
    if typ == "article":
        tail = f"{{\\it {f['journal']}}}"
        if "volume" in f: tail += f" {{\\bf {f['volume']}}}"
        if "pages" in f: tail += f" {f['pages'].replace('--','--')}"
    elif typ == "inproceedings":
        tail = f"{f['booktitle']}"
        if "volume" in f: tail += f" vol {f['volume']}"
        if "pages" in f: tail += f" pp {f['pages']}"
    elif typ == "book":
        tail = f"{f['publisher']}, {f['address']}" if "address" in f else f["publisher"]
    else:
        tail = f.get("howpublished", "")
    if "note" in f and typ != "misc": tail += f" ({f['note']})"
    elif "note" in f: tail += f" {f['note']}"
    if "doi" in f: tail += f" doi:{f['doi']}"
    lines.append(f"\\bibitem[{{{lab}({y})}}]{{{key}}} {s} {y} {t} {tail}".rstrip() + "\n")
lines.append("\\end{thebibliography}")
(here / "references.tex").write_text("\n".join(lines), encoding="utf-8")
print(len(cited), "references written")
