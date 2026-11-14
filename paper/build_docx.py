#!/usr/bin/env python3
"""Build paper/manuscript.docx from paper/main.tex + paper/references.bib.

Pandoc cannot interpret IEEEtran/algorithm2e/BibTeX numbering, so this script
first rewrites main.tex into a plain article (numbered sections, resolved
\\ref/\\cite, numbered equations, a hand-expanded algorithm block, a numbered
reference list), then calls pandoc and finally styles the result with
python-docx.  Usage: python3 build_docx.py
"""
import os, re, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TEX = open(os.path.join(HERE, "main.tex"), encoding="utf-8").read()
BIB = open(os.path.join(HERE, "references.bib"), encoding="utf-8").read()
OUT = os.path.join(HERE, "manuscript.docx")

body = TEX[TEX.index("\\begin{document}") + len("\\begin{document}"):TEX.index("\\end{document}")]

# ---------------------------------------------------------------- front matter
abstract = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", body, re.S).group(1)
keywords = re.search(r"\\begin\{IEEEkeywords\}(.*?)\\end\{IEEEkeywords\}", body, re.S).group(1).strip()
title = re.search(r"\\title\{(.*?)\}\s*\n\\author", body, re.S).group(1).strip()
for tag in ("Methods", "Results", "Conclusion"):
    abstract = abstract.replace("\\textbf{%s:}" % tag, "\n\n\\textbf{%s:}" % tag)
main = body[body.index("\\section{Introduction}"):]
main = main.replace("\\bibliographystyle{IEEEtran}\n\\bibliography{references}\n", "")

# ---------------------------------------------------------------- numbering
labels = {}
sec = sub = 0
def number_sections(m):
    global sec, sub
    kind, star, name = m.group(1), m.group(2), m.group(3)
    if star:
        return m.group(0)
    if kind == "section":
        sec += 1; sub = 0; num = str(sec)
    else:
        sub += 1; num = "%d.%d" % (sec, sub)
    lab = re.match(r"\s*\\label\{([^}]*)\}", main_after[m.end():]) if False else None
    return "\\%s*{%s\\ %s}" % (kind, num, name) + "%%NUM:" + num + "%%"
main_after = main
# collect section labels (label follows heading on same line)
out, sec, sub = [], 0, 0
for line in main.split("\n"):
    m = re.match(r"\\(section|subsection)(\*?)\{(.*?)\}(\\label\{([^}]*)\})?\s*$", line)
    if m and not m.group(2):
        if m.group(1) == "section":
            sec += 1; sub = 0; num = str(sec)
        else:
            sub += 1; num = "%d.%d" % (sec, sub)
        if m.group(5):
            labels[m.group(5)] = num
        line = "\\%s*{%s %s}" % (m.group(1), (num + "." if m.group(1) == "section" else num), m.group(3))
    out.append(line)
main = "\n".join(out)

# equations: number every equation / align row in document order
eq_n = 0
def number_eq(m):
    global eq_n
    env, content = m.group(1), m.group(2)
    if env == "equation":
        eq_n += 1
        lab = re.search(r"\\label\{([^}]*)\}", content)
        if lab: labels[lab.group(1)] = str(eq_n)
        content = re.sub(r"\\label\{[^}]*\}", "", content)
        return "\\begin{equation}%s\\qquad (%d)\\end{equation}" % (content.rstrip(), eq_n)
    rows = re.split(r"\\\\", content)
    new = []
    for r in rows:
        if not r.strip():
            continue
        eq_n += 1
        lab = re.search(r"\\label\{([^}]*)\}", r)
        if lab: labels[lab.group(1)] = str(eq_n)
        r = re.sub(r"\\label\{[^}]*\}", "", r).rstrip()
        new.append("%s\\qquad (%d)" % (r, eq_n))
    return "\\begin{align}%s\\end{align}" % " \\\\\n".join(new)
main = re.sub(r"\\begin\{(equation|align)\}(.*?)\\end\{\1\}", number_eq, main, flags=re.S)

# tables: number in order, prefix caption
tab_n = 0
def number_tab(m):
    global tab_n
    tab_n += 1
    t = m.group(0)
    lab = re.search(r"\\label\{([^}]*)\}", t)
    if lab: labels[lab.group(1)] = str(tab_n)
    t = re.sub(r"\\label\{[^}]*\}", "", t)
    t = re.sub(r"\\caption\{", "\\\\caption{Table %d. " % tab_n, t, count=1)
    t = t.replace("\\begin{table*}", "\\begin{table}").replace("\\end{table*}", "\\end{table}")
    for junk in ("\\small", "\\footnotesize", "\\centering", "\\setlength{\\tabcolsep}{3pt}", "\\setlength{\\tabcolsep}{2.5pt}"):
        t = t.replace(junk, "")
    t = t.replace("\\begin{table}[t]", "\\begin{table}").replace("@{}", "")
    return t
main = re.sub(r"\\begin\{table\*?\}.*?\\end\{table\*?\}", number_tab, main, flags=re.S)

# algorithm: replace the algorithm2e block with an explicit step list
labels["alg:route"] = "1"
algo = r"""
\textbf{Algorithm 1.} Cost-surface routing with local penalty overrides.

\emph{Input:} grid cells $\Omega_g$, land cover $\ell$, slope $s$, footprint cells $\mathcal{P}$, targets $T$, facilities $F$, road cells $R$, penalty $\mu$, overrides $\{(p_f,r_f)\}_{f\in F_{\mathrm{ex}}}$, slope limit $s_{\max}$, alternatives $K$, passes $P$. \emph{Output:} network edge set $E_S$ and routes $\{\pi_t\}$.

\begin{enumerate}
\item Blocked set $\mathcal{B}\leftarrow\{x:\ \text{water}\vee\text{no-data}\vee s(x)>s_{\max}\}$.
\item For each cell $x\in\Omega_g\setminus\mathcal{B}$: set $m(x)\leftarrow 1+(\mu-1)\,\mathbb{1}[x\in\mathcal{P}]$; if there is $f\in F_{\mathrm{ex}}$ with $\|x-p_f\|\le r_f$, set $m(x)\leftarrow 1$ (local override); set $c(x)\leftarrow[c_{\mathrm{lc}}(\ell(x))+g(s(x))]\cdot m(x)$.
\item Build $G=(V,E)$ with edge weights $w(e)=\tfrac12(c(u)+c(v))\lambda(e)$.
\item For each $t\in T\cup F$: compute $\pi^{(1)}_t=\arg\min_{\pi:\,t\to R}L_{\mathrm{cost}}(\pi)$ (Dijkstra/A*) and set $A_t\leftarrow\{\pi^{(1)}_t\}$. For $k=2,\dots,K$: inflate $w$ by factors $\{3,8\}$ inside a 20~m corridor around $A_t$, compute the least-cost path $\pi$ on the inflated graph, and add it to $A_t$ if its overlap with every path already in $A_t$ is at most 0.8.
\item Initialise $E_S\leftarrow\emptyset$ and $U\leftarrow T\cup F$.
\item While $U\neq\emptyset$: choose $(t^\star,\pi^\star)=\arg\max_{t\in U,\,\pi\in A_t}\ w_t/\Delta L_{\mathrm{cost}}(\pi\mid E_S)$; set $E_S\leftarrow E_S\cup\pi^\star$ and $U\leftarrow U\setminus\{t^\star\}$.
\item Repeat $P$ times: for each leaf route $\pi_t$, re-route $t$ to the cheapest attachment on $(E_S\setminus\pi_t)\cup R$ and keep the new route if $L_{\mathrm{cost}}$ decreases.
\item Return $E_S$ and $\{\pi_t\}$.
\end{enumerate}
"""
main = re.sub(r"\\begin\{algorithm\}.*?\\end\{algorithm\}", lambda m: algo, main, flags=re.S)

# ---------------------------------------------------------------- citations
bib_entries = {}
for m in re.finditer(r"@(\w+)\{([^,]+),(.*?)\n\}\n", BIB, re.S):
    typ, key, rest = m.groups()
    fields = {}
    for fm in re.finditer(r"(\w+)\s*=\s*(\{(?:[^{}]|\{(?:[^{}]|\{[^{}]*\})*\})*\}|\d+)", rest):
        v = fm.group(2)
        fields[fm.group(1).lower()] = v[1:-1] if v.startswith("{") else v
    bib_entries[key] = (typ.lower(), fields)

order = []
for m in re.finditer(r"\\cite\{([^}]*)\}", main):
    for k in [x.strip() for x in m.group(1).split(",")]:
        if k not in bib_entries:
            sys.exit("missing bib key: " + k)
        if k not in order:
            order.append(k)
unused = set(bib_entries) - set(order)
if unused:
    sys.exit("unused bib keys: %s" % sorted(unused))
num = {k: i + 1 for i, k in enumerate(order)}

def cite(m):
    ns = sorted(num[k.strip()] for k in m.group(1).split(","))
    # collapse runs like 3,4 -> 3, 4 (IEEE keeps commas for two items)
    return "[" + ", ".join(map(str, ns)) + "]"
main = re.sub(r"~?\\cite\{([^}]*)\}", lambda m: " " + cite(m), main)

# cross references
def ref(m):
    key = m.group(1)
    if key not in labels:
        sys.exit("unresolved ref " + key)
    return labels[key]
main = re.sub(r"\\eqref\{([^}]*)\}", lambda m: "(" + ref(m) + ")", main)
main = re.sub(r"\\ref\{([^}]*)\}", ref, main)
main = re.sub(r"\\label\{[^}]*\}", "", main)

# ---------------------------------------------------------------- bibliography text
ACC = {"\\'e": "é", "\\'a": "á", "\\'E": "É", "\\c{c}": "ç", "\\&": "&", "\\url": "\\url"}
def clean(s):
    for k, v in ACC.items():
        s = s.replace("{" + k + "}", v).replace(k, v)
    s = re.sub(r"\\['`^\"~]\{?(\w)\}?", r"\1", s)
    s = s.replace("--", "–").replace("~", " ")
    s = re.sub(r"[{}]", "", s)
    return s.strip()

def fmt_author(a):
    if "," not in a:
        return clean(a)
    last, first = [x.strip() for x in a.split(",", 1)]
    first = clean(first)
    ini = " ".join(p[0] + "." for p in re.split(r"[\s]+", first.replace("-", " -")) if p and p[0].isalpha()) if first else ""
    return (ini + " " + clean(last)).strip()

def fmt_authors(raw):
    if raw.startswith("{") and raw.endswith("}"):
        return clean(raw)
    parts = [p.strip() for p in re.split(r"\s+and\s+", raw)]
    names = [fmt_author(p) for p in parts]
    if len(names) > 6:
        return names[0] + " et al."
    if len(names) > 2:
        return ", ".join(names[:-1]) + ", and " + names[-1]
    return " and ".join(names)

refs = []
for k in order:
    typ, f = bib_entries[k]
    au = fmt_authors(f.get("author", ""))
    t = clean(f.get("title", ""))
    y = f.get("year", "")
    if typ == "article":
        s = '%s, "%s," \\emph{%s}' % (au, t, clean(f["journal"]))
        if "volume" in f: s += ", vol. " + f["volume"]
        if "number" in f: s += ", no. " + f["number"]
        if "pages" in f: s += ", pp. " + clean(f["pages"])
        s += ", " + y
        if "note" in f and "arXiv" in f["note"]: s += " (" + clean(f["note"]) + ")"
    elif typ == "inproceedings":
        s = '%s, "%s," in \\emph{%s}' % (au, t, clean(f["booktitle"]))
        if "volume" in f: s += ", vol. " + f["volume"]
        if "pages" in f: s += ", pp. " + clean(f["pages"])
        s += ", " + y
        if "note" in f: s += " (" + clean(f["note"]) + ")"
    elif typ == "book":
        s = '%s, \\emph{%s}' % (au, t)
        if "series" in f: s += ", " + clean(f["series"])
        if "volume" in f: s += ", vol. " + f["volume"]
        s += ". " + clean(f.get("address", "")) + (": " if "address" in f else "") + clean(f["publisher"]) + ", " + y
    else:
        s = '%s, "%s," %s' % (au, t, y)
        if "howpublished" in f: s += ". " + f["howpublished"].replace("\\url{", "\\url{")
        if "doi" in f: s += ". doi: " + f["doi"]
        if "note" in f: s += ". " + clean(f["note"])
    if "doi" in f and typ in ("article", "inproceedings"):
        s += ", doi: " + f["doi"]
    refs.append("\\noindent[%d]\\quad %s.\\par\n" % (num[k], s.rstrip(". ")))

main = main.replace("\\IEEEPARstart{R}{ural}", "Rural")
main = re.sub(r"\\ang\{([\d.]+)\}", r"\1°", main)
main = re.sub(r"\\textsc\{([^}]*)\}", r"\1", main)
for macro, rep in (("\\Lcost", " L_{\\mathrm{cost}} "), ("\\argmin", "\\operatorname{arg\\,min}"), ("\\argmax", "\\operatorname{arg\\,max}")):
    main = main.replace(macro, rep)
for big in ("\\Bigl","\\Bigr","\\bigl","\\bigr"):
    main = main.replace(big, "")
main = main.replace("\\tcp*", "").replace("\\paragraph{", "\\textbf{").replace("\\subsection{", "\\subsection{")
# \paragraph{X}\n text -> bold run-in
main = re.sub(r"\\textbf\{([^}]*)\}\s*\n", lambda m: "\\textbf{%s} " % m.group(1) if False else m.group(0), main)

doc = r"""\documentclass{article}
\usepackage{amsmath,amssymb,booktabs,multirow,hyperref}
\title{%s}
\author{Pendyala Archana\\Chaitanya Bharathi Institute of Technology (CBIT), Hyderabad, Telangana, India}
\date{}
\begin{document}
\maketitle
\begin{abstract}
%s
\end{abstract}

\noindent\textbf{Keywords---}%s

%s

\section*{References}
%s
\end{document}
""" % (title, abstract.strip(), keywords, main, "\n".join(refs))

tmp = os.path.join(tempfile.gettempdir(), "manuscript_pandoc.tex")
open(tmp, "w", encoding="utf-8").write(doc)
raw = os.path.join(tempfile.gettempdir(), "manuscript_raw.docx")
r = subprocess.run(["pandoc", tmp, "-f", "latex", "-t", "docx", "-o", raw], capture_output=True, text=True)
sys.stderr.write(r.stderr)
if r.returncode:
    sys.exit(r.returncode)

# ---------------------------------------------------------------- styling
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

d = Document(raw)
for s in d.sections:
    s.page_width, s.page_height = Cm(21.0), Cm(29.7)
    s.left_margin = s.right_margin = Cm(2.2)
    s.top_margin = s.bottom_margin = Cm(2.2)
def setfont(style, size, bold=None, name="Times New Roman"):
    style.font.name = name
    style.element.rPr.rFonts.set(qn("w:eastAsia"), name)
    style.font.size = Pt(size)
    if bold is not None: style.font.bold = bold
    style.font.color.rgb = None
for st in d.styles:
    try:
        if st.type == 1:
            setfont(st, 10.5)
    except Exception:
        pass
for name, size in (("Title", 17), ("Author", 11), ("Abstract", 9.5), ("Heading 1", 13), ("Heading 2", 11.5), ("Heading 3", 10.5)):
    try:
        st = d.styles[name]; setfont(st, size, bold=(name.startswith("Heading") or name == "Title"))
        if name == "Abstract": st.font.italic = False
    except KeyError:
        pass
for p in d.paragraphs:
    if p.style.name in ("Title", "Author"):
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    elif p.style.name in ("Body Text", "First Paragraph", "Compact", "Abstract"):
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    if p.style.name.startswith("Table Caption") or p.text.startswith("Table "):
        pass
def border(cell, **kw):
    tcPr = cell._tc.get_or_add_tcPr()
    b = tcPr.find(qn("w:tcBorders"))
    if b is None:
        b = OxmlElement("w:tcBorders")
        later = [qn("w:" + n) for n in ("shd", "noWrap", "tcMar", "textDirection", "tcFitText", "vAlign", "hideMark")]
        pos = next((i for i, ch in enumerate(tcPr) if ch.tag in later), None)
        if pos is None: tcPr.append(b)
        else: tcPr.insert(pos, b)
    for edge in ("top", "left", "bottom", "right"):
        if edge in kw:
            e = OxmlElement("w:" + edge)
            e.set(qn("w:val"), "single"); e.set(qn("w:sz"), str(kw[edge])); e.set(qn("w:space"), "0"); e.set(qn("w:color"), "000000")
            b.append(e)
def table_borders(t):
    tblPr = t._tbl.tblPr
    old = tblPr.find(qn("w:tblBorders"))
    if old is not None: tblPr.remove(old)
    tb = OxmlElement("w:tblBorders")
    for edge, sz in (("top", 12), ("bottom", 12)):
        e = OxmlElement("w:" + edge)
        e.set(qn("w:val"), "single"); e.set(qn("w:sz"), str(sz)); e.set(qn("w:space"), "0"); e.set(qn("w:color"), "000000")
        tb.append(e)
    later = [qn("w:" + n) for n in ("shd", "tblLayout", "tblCellMar", "tblLook")]
    pos = next((i for i, ch in enumerate(tblPr) if ch.tag in later), None)
    if pos is None: tblPr.append(tb)
    else: tblPr.insert(pos, tb)

TOTAL = 16.6
for t in d.tables:
    t.alignment = 1
    table_borders(t)
    ncol = len(t.columns)
    first = TOTAL * (0.38 if ncol >= 6 else 0.40)
    widths = [first] + [(TOTAL - first) / (ncol - 1)] * (ncol - 1)
    t.autofit = False
    grid = t._tbl.tblGrid
    for gc, w in zip(grid.findall(qn("w:gridCol")), widths):
        gc.set(qn("w:w"), str(int(Cm(w).twips)))
    for row in t.rows:
        for ci, c in enumerate(row.cells):
            c.width = Cm(widths[ci]) if ci < len(widths) else c.width
            for p in c.paragraphs:
                p.paragraph_format.space_after = Pt(1); p.paragraph_format.space_before = Pt(1)
                for run in p.runs:
                    run.font.size = Pt(8.5); run.font.name = "Times New Roman"
    for ri, row in enumerate(t.rows):
        for c in row.cells:
            kw = {}
            if ri == 0: kw["top"] = 12
            if ri == 1: kw["top"] = 6
            if ri == len(t.rows) - 1: kw["bottom"] = 12
            if kw: border(c, **kw)
d.save(OUT)
print("wrote", OUT, "refs:", len(order), "tables:", len(d.tables))
