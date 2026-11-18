#!/usr/bin/env python3
"""Build paper/erl/manuscript.docx from paper/erl/main.tex + paper/erl/references.bib (pandoc + python-docx).

Pandoc cannot interpret the iopart class or BibTeX numbering, so this script rewrites main.tex into a plain article first: numbered
figures, tables and equations, numeric citations in order of first appearance, and a hand-formatted reference list.
    python paper/erl/build_docx_erl.py
"""
from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

HERE = Path(__file__).resolve().parent
TEX = (HERE / "main.tex").read_text(encoding="utf-8")
BIB = (HERE / "references.bib").read_text(encoding="utf-8")
OUT = HERE / "manuscript.docx"

body = TEX[TEX.index("\\begin{document}") + len("\\begin{document}"):TEX.index("\\end{document}")]
title = re.search(r"\\title\[[^\]]*\]\{(.*?)\}\s*\n", body, re.S).group(1).strip()
author = re.search(r"(?m)^\\author\{(.*)\}\s*$", body).group(1).strip()
address = re.search(r"\\address\{(.*?)\}\s*\n\\ead", body, re.S).group(1).strip()
ead = re.search(r"\\ead\{(.*?)\}\s*\n", body).group(1).strip()
abstract = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", body, re.S).group(1).strip()
keywords = re.search(r"\\ERLkeywords\{(.*?)\}\s*\n", body).group(1).strip()
main = body[body.index("\\section{Introduction}"):body.index("\\bibliographystyle")]
main = re.sub(r"(?m)^\s*%.*$", "", main)                      # drop comment lines (TODO notes stay in the .tex only)
main = re.sub(r"(?<!\\)%\s*TODO.*", "", main)
main = main.replace("\\ack\n", "\\section*{Acknowledgments}\n")

# ------------------------------------------------------------------ numbering of floats, equations and citations
labels: dict[str, str] = {}
fig_n = tab_n = eq_n = 0
for m in re.finditer(r"\\begin\{(figure|table|equation)\}(.*?)\\end\{\1\}", main, re.S):
    kind, inner = m.group(1), m.group(2)
    lab = re.search(r"\\label\{([^}]*)\}", inner)
    if kind == "figure":
        fig_n += 1
        num = fig_n
    elif kind == "table":
        tab_n += 1
        num = tab_n
    else:
        eq_n += 1
        num = eq_n
    if lab:
        labels[lab.group(1)] = str(num)


def number_float(m):
    kind, inner = m.group(1), m.group(2)
    lab = re.search(r"\\label\{([^}]*)\}", inner)
    num = labels.get(lab.group(1), "?") if lab else "?"
    if kind == "equation":
        inner = re.sub(r"\\label\{[^}]*\}", "", inner)
        return "\\[" + inner.strip() + "\\qquad (" + num + ")\\]"
    prefix = "Figure" if kind == "figure" else "Table"
    inner = re.sub(r"\\label\{[^}]*\}", "", inner)
    inner = inner.replace("\\caption{", "\\caption{\\textbf{" + prefix + " " + num + ".} ", 1)
    return "\\begin{%s}%s\\end{%s}" % (kind, inner, kind)


main = re.sub(r"\\begin\{(figure|table|equation)\}(.*?)\\end\{\1\}", number_float, main, flags=re.S)
main = re.sub(r"\\ref\{([^}]*)\}", lambda m: labels.get(m.group(1), "?"), main)

order: list[str] = []


def cite(m):
    nums = []
    for k in m.group(1).split(","):
        k = k.strip()
        if k not in order:
            order.append(k)
        nums.append(order.index(k) + 1)
    nums = sorted(set(nums))
    out, i = [], 0
    while i < len(nums):                                      # compress runs 1,2,3 -> 1-3
        j = i
        while j + 1 < len(nums) and nums[j + 1] == nums[j] + 1:
            j += 1
        out.append(str(nums[i]) if i == j else (f"{nums[i]}, {nums[j]}" if j == i + 1 else f"{nums[i]}--{nums[j]}"))
        i = j + 1
    return "[" + ", ".join(out) + "]"


main = re.sub(r"\\cite\{([^}]*)\}", cite, main)

# ------------------------------------------------------------------ inline math -> Unicode (renders in every Word processor)
GREEK = {"\\mu": "μ", "\\rho": "ρ", "\\kappa": "κ", "\\delta": "δ", "\\times": "×", "\\approx": "≈", "\\sim": "~", "\\le": "≤", "\\ge": "≥",
         "\\pm": "±", "\\setminus": "∖", "\\subset": "⊂", "\\ell": "ℓ", "\\,": " ", "\\;": " ", "\\!": ""}


def uni(m):
    t = m.group(1)
    t = re.sub(r"\\(?:mathcal|mathrm|text)\{([^{}]*)\}", r"\1", t)
    t = t.replace("\\bar\\ell", "ℓ̄").replace("\\bar{\\ell}", "ℓ̄")
    t = t.replace("^{\\circ}", "°").replace("^2", "²").replace("^{2}", "²")
    t = re.sub(r"_\{?([A-Za-z0-9]+)\}?", r"_\1", t)
    for k, v in sorted(GREEK.items(), key=lambda kv: -len(kv[0])):
        t = t.replace(k, v)
    if "\\" in t or "{" in t or "}" in t:                           # something we cannot express: keep as real math
        return m.group(0)
    t = re.sub(r"(?<=\d)\s*-", "-", t)
    t = t.replace("-", "−").replace("=", " = ").replace("<", " < ").replace(">", " > ")
    t = re.sub(r"\s{2,}", " ", t).strip()
    t = re.sub(r"^\+", "+", t)
    return t


main = re.sub(r"\$([^$\n]+?)\$", uni, main) if False else main

_parts = re.split(r"(\\\[.*?\\\])", main, flags=re.S)
main = "".join(p if p.startswith("\\[") else re.sub(r"\$([^$\n]+?)\$", uni, p) for p in _parts)
main = re.sub(r"\\path\{([^}]*)\}", r"\\texttt{\1}", main)
main = re.sub(r"\\url\{([^}]*)\}", r"\\texttt{\1}", main)
main = re.sub(r"\\begin\{tabular\}\{@\{\}p\{[^}]*\}p\{[^}]*\}p\{[^}]*\}@\{\}\}", r"\\begin{tabular}{lll}", main)
main = re.sub(r"\\begin\{tabular\}\{@\{\}p\{[^}]*\}rrrrr@\{\}\}", r"\\begin{tabular}{lrrrrr}", main)
main = re.sub(r"\\multicolumn\{(\d+)\}\{@\{\}l\}", r"\\multicolumn{\1}{l}", main)
main = main.replace("\\footnotesize", "").replace("\\small", "").replace("\\centering", "")
main = main.replace("figures/", str(HERE / "figures") + "/")


# ------------------------------------------------------------------ reference list
def parse_bib(text):
    entries = {}
    for m in re.finditer(r"@(\w+)\{([^,]+),(.*?)\n\}", text, re.S):
        fields = {}
        for fm in re.finditer(r"(\w+)\s*=\s*\{((?:[^{}]|\{[^{}]*\})*)\}", m.group(3)):
            fields[fm.group(1).lower()] = fm.group(2)
        entries[m.group(2)] = (m.group(1).lower(), fields)
    return entries


def clean(s):
    s = re.sub(r"\{\\'([a-zA-Z])\}", lambda m: {"e": "é", "a": "á"}.get(m.group(1), m.group(1)), s)
    s = s.replace("{\\'e}", "é").replace("{\\'a}", "á").replace("\\&", "&").replace("~", " ").replace("--", "–")
    s = re.sub(r"\\url\{([^}]*)\}", r"\1", s)
    return s.replace("{", "").replace("}", "")


def fmt_authors(a):
    names = [x.strip() for x in a.split(" and ")]
    out = []
    for n in names:
        if "," in n:
            sur, given = [p.strip() for p in n.split(",", 1)]
            ini = "".join(w[0] for w in re.split(r"[\s\-]+", clean(given)) if w)
            out.append(f"{clean(sur)} {ini}")
        else:
            out.append(clean(n))
    return ", ".join(out[:6]) + (", et al" if len(out) > 6 else "")


entries = parse_bib(BIB)
refs = []
for i, k in enumerate(order, 1):
    typ, f = entries[k]
    au = fmt_authors(f.get("author", ""))
    t = clean(f.get("title", ""))
    venue = clean(f.get("journal") or f.get("booktitle") or f.get("howpublished") or f.get("publisher") or "")
    bits = [f"{au}. {t}."]
    if venue:
        bits.append(f"{venue}")
    yr = f.get("year", "")
    vol, num, pg = f.get("volume"), f.get("number"), f.get("pages")
    tail = yr
    if vol:
        tail += f";{vol}" + (f"({num})" if num else "")
    if pg:
        tail += f":{clean(pg)}"
    bits.append(tail + ".")
    if f.get("note"):
        bits.append(clean(f["note"]) + ".")
    if f.get("doi"):
        bits.append(f"doi:{f['doi']}")
    refs.append(f"{i}. " + " ".join(bits))

reflist = "\\section*{References}\n\\begin{itemize}\n" + "\n".join("\\item[] " + r.replace("&", "\\&").replace("_", "\\_").replace("%", "\\%") for r in refs) + "\n\\end{itemize}\n"

doc = ("\\documentclass{article}\n\\usepackage{graphicx,booktabs,amsmath}\n\\newcommand{\\Lcost}{L_{\\mathrm{cost}}}\n\\begin{document}\n"
       "\\title{" + title + "}\n\\author{" + author + "\\\\ " + address + "}\n\\date{}\n\\maketitle\n"
       "\\begin{abstract}\n" + abstract + "\n\\end{abstract}\n\n\\noindent\\textit{Keywords}: " + keywords + "\n\n" + main + "\n" + reflist + "\\end{document}\n")

with tempfile.TemporaryDirectory() as td:
    tex = Path(td) / "erl_docx.tex"
    raw = Path(td) / "raw.docx"
    tex.write_text(doc, encoding="utf-8")
    r = subprocess.run(["pandoc", str(tex), "-f", "latex", "-t", "docx", "-o", str(raw), f"--resource-path={HERE}"], capture_output=True, text=True)
    if r.returncode != 0 or r.stderr.strip():
        print("pandoc:", r.stderr.strip()[:1500])
    if r.returncode != 0:
        raise SystemExit(1)
    d = Document(str(raw))

# ------------------------------------------------------------------ styling
for s in d.sections:
    s.left_margin = s.right_margin = s.top_margin = s.bottom_margin = Cm(2.5)
usable = Cm(16.0)
for st in d.styles:
    if st.type == 1 and st.font is not None and st.name not in ("Heading 1", "Heading 2", "Heading 3", "Title"):
        st.font.name = "Times New Roman"
        st.font.size = Pt(11)
for name, size in (("Title", 16), ("Heading 1", 13), ("Heading 2", 12), ("Heading 3", 11)):
    try:
        st = d.styles[name]
    except KeyError:
        continue
    st.font.name = "Times New Roman"
    st.font.size = Pt(size)
    st.font.bold = True
    st.font.color.rgb = RGBColor(0, 0, 0)
for p in d.paragraphs:
    p.paragraph_format.line_spacing = 1.3
    if p.style.name.startswith("Heading"):
        for run in p.runs:
            run.font.color.rgb = RGBColor(0, 0, 0)
for sh in d.inline_shapes:
    if sh.width > usable:
        ratio = usable / sh.width
        sh.width, sh.height = int(sh.width * ratio), int(sh.height * ratio)
for tb in d.tables:
    tb.alignment = WD_TABLE_ALIGNMENT.CENTER
    tblPr = tb._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "bottom", "insideH"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), "4")
        el.set(qn("w:color"), "808080")
        borders.append(el)
    tblPr.append(borders)
    for row in tb.rows:
        for cell in row.cells:
            for p in cell.paragraphs:
                p.paragraph_format.line_spacing = 1.0
                for run in p.runs:
                    run.font.size = Pt(9)
d.save(str(OUT))
print("wrote", OUT, "refs:", len(refs), "figures:", fig_n, "tables:", tab_n, "equations:", eq_n)
