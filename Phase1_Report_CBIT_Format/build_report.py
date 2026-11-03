"""Build the Dissertation Phase-I Review-1 report as a Word file in the CBIT layout.

Usage: python build_report.py <latex_project_dir> <out.docx> [pages.json]

Content (prose, tables, references) is read from the LaTeX project so the two
versions cannot drift; layout follows 'Dissertation Phase - 1 review report'
(Times New Roman 12, 1.5 spacing, justified, centred chapter titles,
Certificate / Abstract / Contents table).
"""
import json, os, re, sys
from docx import Document
from docx.enum.section import WD_ORIENT, WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_COLOR_INDEX
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

OLD, OUT = sys.argv[1], sys.argv[2]
PAGES = json.load(open(sys.argv[3])) if len(sys.argv) > 3 else {}
HERE = os.path.dirname(os.path.abspath(__file__))
A = lambda n: os.path.join(HERE, "assets", n)

# ------------------------------------------------------------------ editable front-matter fields
STUDENT = "PENDYALA ARCHANA"
ROLL = "160125763008"
GUIDE1 = "Dr. Kolikipogu Ramakrishna, Professor"
GUIDE2 = "P. Swathi, Assistant Professor"
HOD = "Dr. M. Venu Gopalachari"
YEAR = "2026-2027"
TITLE = ("GIS and Remote Sensing-Based Smart Village Infrastructure Planning and "
         "Road Network Optimization for Rural Telangana")
SIMILARITY = "[__]%"

# ------------------------------------------------------------------ LaTeX source
tex_lines = open(os.path.join(OLD, "A_Dissertation_Phase_I_Review_1_Report_Final.tex"), encoding="utf-8").read().split("\n")
def TL(n): return tex_lines[n - 1]

full = "\n".join(tex_lines)
for f in ("lit_table1.tex", "lit_table2.tex"):
    full = full.replace("\\input{%s}" % f, open(os.path.join(OLD, f), encoding="utf-8").read())
cite_order = []
for m in re.finditer(r"\\cite\{([^}]*)\}", full):
    for k in m.group(1).split(","):
        k = k.strip()
        if k not in cite_order:
            cite_order.append(k)
CITE = {k: i + 1 for i, k in enumerate(cite_order)}

bib = {}
for m in re.finditer(r"@(\w+)\{(\w+),(.*?)\n\}?\s*(?=\n@|\Z)", open(os.path.join(OLD, "references.bib"), encoding="utf-8").read(), re.S):
    body = m.group(3)
    ent = {}
    for fm in re.finditer(r"(\w+)\s*=\s*\{(.*?)\}\s*(?:,|\}?\s*$)", body, re.S | re.M):
        ent[fm.group(1)] = re.sub(r"\s+", " ", fm.group(2)).replace("{", "").replace("}", "")
    bib[m.group(2)] = ent

import content_v2 as C
REF = {"ch:lit": "2", "ch:data": "4", "ch:arch": "5"}
TAB = {k: i + 1 for i, k in enumerate(["contrib", "lit1", "lit2", "align", "gapmat", "datasets", "datasets2", "dsunits", "admin", "modules", "stages", "progress", "s2", "runs", "pen", "unc", "recon", "avoid", "econ", "evid", "terms", "applit"])}
FIG = {k: i + 1 for i, k in enumerate(["arch", "flow", "bq", "len", "map"])}
EQN = {"cost": 1, "pen": 2, "credit": 3}
for k, v in TAB.items(): REF["tab:" + k] = str(v)
for k, v in FIG.items(): REF["fig:" + k] = str(v)
for k, v in EQN.items(): REF["eq:" + k] = str(v)
REF["alg:plan"] = "1"

# ------------------------------------------------------------------ LaTeX -> runs
MATH = {r"\circ": "°", r"\geq": "≥", r"\sim": "~", r"\cup": "∪", r"\sum": "Σ", r"\in": "∈", r"\ell": "ℓ", r"\times": "×",
        r"\,": " ", r"\sqrt": "√", r"\leq": "≤", r"\approx": "≈", r"\to": "→"}
SUP = str.maketrans("0123456789-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁻")

def brace(s, i):
    """return (content, next_index) for a {...} group starting at s[i]=='{'."""
    d, j = 0, i
    while j < len(s):
        if s[j] == "{": d += 1
        elif s[j] == "}":
            d -= 1
            if d == 0: return s[i + 1:j], j + 1
        j += 1
    return s[i + 1:], len(s)

def math_runs(m, st):
    out, i = [], 0
    m = m.replace("^{\\circ}", "°").replace("^\\circ", "°")
    m = re.sub(r"\\(operatorname|mathcal|text)\{([^}]*)\}", r"\2", m)
    m = re.sub(r"\\tfrac\{([^}]*)\}\{([^}]*)\}", r"(\1)/(\2)", m)
    while i < len(m):
        c = m[i]
        if c == "\\":
            for k, v in MATH.items():
                if m.startswith(k, i):
                    out.append((v, dict(st))); i += len(k); break
            else:
                mm = re.match(r"\\[A-Za-z]+", m[i:]); i += len(mm.group(0)) if mm else 1
        elif c in "^_":
            if i + 1 < len(m) and m[i + 1] == "{": arg, i = brace(m, i + 1)
            else: arg, i = m[i + 1:i + 2], i + 2
            arg = arg.replace("\\circ", "°")
            s2 = dict(st); s2["sup" if c == "^" else "sub"] = True
            out.append((arg, s2))
        elif c in "{}":
            i += 1
        else:
            out.append((c, dict(st, italic=True) if c.isalpha() else dict(st))); i += 1
    return out

def runs(s, st=None):
    st = st or {}
    out, i = [], 0
    buf = ""
    def flush():
        nonlocal buf
        if buf: out.append((buf, dict(st))); buf = ""
    while i < len(s):
        c = s[i]
        if c == "\\":
            mm = re.match(r"\\([A-Za-z]+)", s[i:])
            if mm:
                cmd = mm.group(1); j = i + len(mm.group(0))
                if cmd in ("textbf", "emph", "texttt", "url", "textit"):
                    arg, j = brace(s, j); flush()
                    ns = dict(st)
                    if cmd == "textbf": ns["bold"] = True
                    elif cmd in ("emph", "textit"): ns["italic"] = True
                    else: ns["mono"] = True
                    out += runs(arg, ns); i = j; continue
                if cmd == "cite":
                    arg, j = brace(s, j); flush()
                    out.append(("[" + ", ".join(str(CITE[k.strip()]) for k in arg.split(",")) + "]", dict(st))); i = j; continue
                if cmd in ("ref", "eqref"):
                    arg, j = brace(s, j); flush()
                    out.append((("(%s)" if cmd == "eqref" else "%s") % REF[arg], dict(st))); i = j; continue
                if cmd in ("planned", "partialS", "impl", "unver"):
                    flush(); out.append(({"planned": "Planned", "partialS": "Partial", "impl": "Implemented", "unver": "Unverified"}[cmd], dict(st, bold=True))); i = j
                    if s[i:i + 1] == " ": i += 1
                    continue
                if cmd in ("medskip", "noindent", "par"):
                    i = j; continue
                i = j; continue
            nxt = s[i + 1:i + 2]
            if nxt in "%&_#$": buf += nxt
            elif nxt == " ": buf += " "
            i += 2; continue
        if c == "$":
            j = s.index("$", i + 1); flush(); out += math_runs(s[i + 1:j], st); i = j + 1; continue
        if c == "~": buf += "\u00a0"; i += 1; continue
        if s.startswith("---", i): buf += "—"; i += 3; continue
        if s.startswith("--", i): buf += "–"; i += 2; continue
        if s.startswith("``", i): buf += "“"; i += 2; continue
        if s.startswith("''", i): buf += "”"; i += 2; continue
        if c in "{}": i += 1; continue
        buf += c; i += 1
    flush()
    return out

# ------------------------------------------------------------------ docx helpers
doc = Document()
sec0 = doc.sections[0]
sec0.page_width, sec0.page_height = Inches(8.27), Inches(11.69)
for a in ("left_margin", "right_margin", "top_margin", "bottom_margin"): setattr(sec0, a, Inches(1))
sec0.footer_distance = Inches(0.45)

def set_font(style, size, bold=False, name="Times New Roman"):
    style.font.name = name; style.font.size = Pt(size); style.font.bold = bold
    style.font.color.rgb = RGBColor(0, 0, 0)
    rpr = style.element.get_or_add_rPr()
    rf = rpr.find(qn("w:rFonts"))
    if rf is None: rf = OxmlElement("w:rFonts"); rpr.append(rf)
    for a in list(rf.attrib):
        if "Theme" in a: del rf.attrib[a]
    for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"): rf.set(qn(a), name)

st = doc.styles
set_font(st["Normal"], 12)
st["Normal"].paragraph_format.space_after = Pt(6)
st["Normal"].paragraph_format.line_spacing = 1.5
for name, size, align, before, after in (("Heading 1", 16, WD_ALIGN_PARAGRAPH.CENTER, 0, 14), ("Heading 2", 14, WD_ALIGN_PARAGRAPH.LEFT, 10, 6), ("Heading 3", 12, WD_ALIGN_PARAGRAPH.LEFT, 8, 4)):
    s = st[name]; set_font(s, size, True)
    s.paragraph_format.alignment = align; s.paragraph_format.space_before = Pt(before); s.paragraph_format.space_after = Pt(after)
    s.paragraph_format.line_spacing = 1.15; s.paragraph_format.keep_with_next = True
st["Heading 1"].paragraph_format.page_break_before = True

def add_runs(p, rs, size=None, color=None):
    for text, f in rs:
        r = p.add_run(text)
        if f.get("bold"): r.bold = True
        if f.get("italic"): r.italic = True
        if f.get("sup"): r.font.superscript = True
        if f.get("sub"): r.font.subscript = True
        if f.get("mono"): r.font.name = "Courier New"; r._element.rPr.rFonts.set(qn("w:cs"), "Courier New"); r.font.size = Pt((size or 12) - 1.5)
        elif size: r.font.size = Pt(size)
        if color: r.font.color.rgb = color
    return p

def para(rs, align=WD_ALIGN_PARAGRAPH.JUSTIFY, size=None, spacing=None, after=None, before=None, keep=False, style=None, indent=None):
    p = doc.add_paragraph(style=style)
    if isinstance(rs, str): rs = [(rs, {})]
    add_runs(p, rs, size)
    p.alignment = align
    pf = p.paragraph_format
    if spacing: pf.line_spacing = spacing
    if after is not None: pf.space_after = Pt(after)
    if before is not None: pf.space_before = Pt(before)
    if keep: pf.keep_with_next = True
    if indent is not None: pf.left_indent = Inches(indent)
    return p

def X(s):
    """replace @T:key@ by the table number."""
    return re.sub(r"@T:(\w+)@", lambda m: REF["tab:" + m.group(1)], s)


def tp(n, **kw):
    """paragraph from tex line n."""
    return para(runs(TL(n).strip()), **kw)

def heading(level, text):
    p = doc.add_paragraph(style="Heading %d" % level)
    p.add_run(text.upper() if level == 1 else text)
    return p

def centered_title(text, size=16, before=0, after=14):
    return para([(text, {"bold": True})], align=WD_ALIGN_PARAGRAPH.CENTER, size=size, before=before, after=after, spacing=1.15)

def list_items(items, labels=None):
    for i, t in enumerate(items):
        lab = labels[i] if labels else "•"
        p = para([(lab + "\t", {})] + runs(t), spacing=1.5, after=2)
        p.paragraph_format.left_indent = Inches(0.45); p.paragraph_format.first_line_indent = Inches(-0.3)
        p.paragraph_format.tab_stops.add_tab_stop(Inches(0.45))

def page_break():
    p = doc.add_paragraph(); p.paragraph_format.space_after = Pt(0); p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.line_spacing = Pt(1)
    r = p.add_run(); r.font.size = Pt(1); r.add_break(WD_BREAK.PAGE)

def new_section(landscape=False, fmt=None, start=None):
    s = doc.add_section(WD_SECTION.NEW_PAGE)
    if landscape:
        s.orientation = WD_ORIENT.LANDSCAPE; s.page_width, s.page_height = Inches(11.69), Inches(8.27)
    else:
        s.orientation = WD_ORIENT.PORTRAIT; s.page_width, s.page_height = Inches(8.27), Inches(11.69)
    for a in ("left_margin", "right_margin", "top_margin", "bottom_margin"): setattr(s, a, Inches(0.8 if landscape else 1))
    if fmt: pg_num(s, fmt, start)
    else:
        for e in s._sectPr.findall(qn("w:pgNumType")):
            if e.get(qn("w:start")) is not None: del e.attrib[qn("w:start")]
    return s

def pg_num(section, fmt, start=None):
    sp = section._sectPr
    for e in sp.findall(qn("w:pgNumType")): sp.remove(e)
    e = OxmlElement("w:pgNumType"); e.set(qn("w:fmt"), fmt)
    if start is not None: e.set(qn("w:start"), str(start))
    sp.append(e)

def footer_pagenum(section):
    f = section.footer; f.is_linked_to_previous = False
    p = f.paragraphs[0]; p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for t, txt in (("begin", None), (None, "PAGE"), ("end", None)):
        r = p.add_run(); r.font.size = Pt(10); r.font.name = "Times New Roman"
        if t:
            fc = OxmlElement("w:fldChar"); fc.set(qn("w:fldCharType"), t); r._element.append(fc)
        else:
            it = OxmlElement("w:instrText"); it.set(qn("xml:space"), "preserve"); it.text = txt; r._element.append(it)

def shade(cell, color):
    tcPr = cell._tc.get_or_add_tcPr(); sh = OxmlElement("w:shd")
    sh.set(qn("w:val"), "clear"); sh.set(qn("w:color"), "auto"); sh.set(qn("w:fill"), color); tcPr.append(sh)

def set_borders(tbl, on=True):
    tblPr = tbl._tbl.tblPr; b = OxmlElement("w:tblBorders")
    for e in ("top", "left", "bottom", "right", "insideH", "insideV"):
        x = OxmlElement("w:" + e); x.set(qn("w:val"), "single" if on else "nil"); x.set(qn("w:sz"), "4"); x.set(qn("w:space"), "0"); x.set(qn("w:color"), "000000"); b.append(x)
    tblPr.append(b)

def repeat_header(row):
    trPr = row._tr.get_or_add_trPr(); e = OxmlElement("w:tblHeader"); e.set(qn("w:val"), "true"); trPr.append(e)

def no_split(row):
    trPr = row._tr.get_or_add_trPr(); e = OxmlElement("w:cantSplit"); e.set(qn("w:val"), "true"); trPr.append(e)

def make_table(headers, rows, widths, size=10, header_fill="D9D9D9", align_left=True):
    sc = doc.sections[-1]
    avail = (sc.page_width - sc.left_margin - sc.right_margin) / 914400
    widths = [w * avail / sum(widths) for w in widths]
    t = doc.add_table(rows=1, cols=len(headers)); t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False; set_borders(t)
    tblPr = t._tbl.tblPr; lay = OxmlElement("w:tblLayout"); lay.set(qn("w:type"), "fixed"); tblPr.append(lay)
    def fill(cells, data, bold=False):
        for c, d, w in zip(cells, data, widths):
            c.width = Inches(w)
            p = c.paragraphs[0]; p.paragraph_format.line_spacing = 1.0; p.paragraph_format.space_after = Pt(1); p.paragraph_format.space_before = Pt(1)
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            rs = runs(d) if isinstance(d, str) else d
            if bold: rs = [(a, dict(b, bold=True)) for a, b in rs]
            add_runs(p, rs, size)
    fill(t.rows[0].cells, headers, True)
    for c in t.rows[0].cells: shade(c, header_fill)
    repeat_header(t.rows[0])
    for r in rows:
        row = t.add_row(); no_split(row); fill(row.cells, r)
    for r_ in t.rows[:2]:
        for c_ in r_.cells:
            for p_ in c_.paragraphs: p_.paragraph_format.keep_with_next = True
    doc.add_paragraph().paragraph_format.space_after = Pt(4)
    return t

def tex_rows(first, last):
    """rows between tex lines first..last, each line 'a & b & c \\\\' (a row can span the whole line)."""
    out = []
    for n in range(first, last + 1):
        line = TL(n).strip()
        line = re.sub(r"\\(bottomrule|midrule|toprule)", "", line).strip()
        line = re.sub(r"\\\\\s*$", "", line)
        out.append([c.strip() for c in re.split(r"(?<!\\)&", line)])
    return out

def file_rows(fname, first_marker="\\midrule\\endhead"):
    txt = open(os.path.join(OLD, fname), encoding="utf-8").read()
    body = txt.split("\\endfoot")[1].split("\\end{longtable}")[0]
    rows = []
    for line in body.strip().split("\n"):
        line = re.sub(r"\\\\\s*$", "", line.strip())
        if line: rows.append([c.strip() for c in re.split(r"(?<!\\)&", line)])
    return rows

captions = {"tables": [], "figures": []}
def table_caption(key, text):
    n = TAB[key]; captions["tables"].append((n, text))
    return para([("Table %d. " % n, {"bold": True})] + runs(text), align=WD_ALIGN_PARAGRAPH.CENTER, size=11, spacing=1.0, before=6, after=4, keep=True)

def figure(key, text, img, width):
    n = FIG[key]; captions["figures"].append((n, text))
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.keep_with_next = True; p.paragraph_format.line_spacing = 1.0
    p.add_run().add_picture(A(img), width=Inches(width))
    para([("Figure %d. " % n, {"bold": True})] + runs(text), align=WD_ALIGN_PARAGRAPH.CENTER, size=11, spacing=1.0, before=2, after=10)

def equation(key, img, width):
    n = EQN[key]
    t = doc.add_table(rows=1, cols=2); t.autofit = False
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for c, w in zip(t.rows[0].cells, (5.55, 0.7)): c.width = Inches(w)
    p = t.rows[0].cells[0].paragraphs[0]; p.alignment = WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.line_spacing = 1.0
    p.add_run().add_picture(A(img), width=Inches(width))
    q = t.rows[0].cells[1].paragraphs[0]; q.alignment = WD_ALIGN_PARAGRAPH.RIGHT; q.add_run("(%d)" % n)
    t.rows[0].cells[1].vertical_alignment = 1
    doc.add_paragraph().paragraph_format.space_after = Pt(2)

toc_entries = []   # (level, number, title)
def H(level, number, title):
    toc_entries.append((level, number, title))
    return heading(level, "%s %s" % (number, title) if level > 1 else "%s. %s" % (number, title))

def fix(line, *pairs):
    s = TL(line).strip()
    for a, b in pairs:
        assert a in s, (line, a)
        s = s.replace(a, b)
    return s

exec(open(os.path.join(HERE, 'report_fin_data.py'), encoding='utf-8').read(), globals())
import shutil as _shutil
for _nm, _src in (('chart1_network_lengths.png', r'D:\Telangana_Rural_Project\outputs\final_comparison\charts\chart1_network_lengths.png'), ('map4_alternatives_vs_network.png', r'D:\Telangana_Rural_Project\outputs\final_maps\map4_alternatives_vs_network.png')):
    _shutil.copy2(_src, A(_nm))

# ================================================================== TITLE PAGE
pg_num(sec0, "lowerRoman", 1); footer_pagenum(sec0)
sec0.footer.is_linked_to_previous = False
p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.space_after = Pt(18)
p.add_run().add_picture(A("banner.png"), width=Inches(6.2))
para([("A Dissertation Phase-I Review -1 Report", {"bold": True})], align=WD_ALIGN_PARAGRAPH.CENTER, size=12, before=14, after=0, spacing=1.15)
para([("On", {"bold": True})], align=WD_ALIGN_PARAGRAPH.CENTER, size=11, after=2, spacing=1.15)
para([(TITLE.upper(), {"bold": True})], align=WD_ALIGN_PARAGRAPH.CENTER, size=16, after=14, spacing=1.15)
para([("Submitted in partial fulfillment of the requirements for the degree", {"bold": True})], align=WD_ALIGN_PARAGRAPH.CENTER, size=11, after=4, spacing=1.15)
para([("in", {"bold": True})], align=WD_ALIGN_PARAGRAPH.CENTER, size=11, after=8, spacing=1.15)
para([("Master of Technology", {"bold": True})], align=WD_ALIGN_PARAGRAPH.CENTER, size=16, after=0, spacing=1.15).runs[0].font.color.rgb = RGBColor(0xFF, 0, 0)
para([("IT- (ARTIFICIAL INTELLIGENCE & ROBOTICS)", {"bold": True})], align=WD_ALIGN_PARAGRAPH.CENTER, size=16, after=8, spacing=1.15).runs[0].font.color.rgb = RGBColor(0xFF, 0, 0)
para([("by", {"bold": True})], align=WD_ALIGN_PARAGRAPH.CENTER, size=11, after=2, spacing=1.15)
p = para([("%s (%s)" % (STUDENT, ROLL), {"bold": True})], align=WD_ALIGN_PARAGRAPH.CENTER, size=12, after=14, spacing=1.15)
para([("Under the guidance of", {"bold": True})], align=WD_ALIGN_PARAGRAPH.CENTER, size=11, after=2, spacing=1.15)
for i, g in enumerate((GUIDE1, GUIDE2), 1):
    para([("%d.  %s" % (i, g), {"bold": True})], align=WD_ALIGN_PARAGRAPH.CENTER, size=11, after=0, spacing=1.15)
p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.space_before = Pt(60); p.paragraph_format.space_after = Pt(30)
para([("DEPARTMENT OF INFORMATION TECHNOLOGY", {"bold": True})], align=WD_ALIGN_PARAGRAPH.CENTER, size=13, after=0, spacing=1.15)
para([("Chaitanya Bharathi Institute of Technology (Autonomous)", {"bold": True})], align=WD_ALIGN_PARAGRAPH.CENTER, size=15, after=0, spacing=1.15)
para([("(Affiliated to Osmania University, Hyderabad)", {"bold": True})], align=WD_ALIGN_PARAGRAPH.CENTER, size=10, after=0, spacing=1.15)
para([("Hyderabad, TELANGANA (INDIA) –500 075", {"bold": True})], align=WD_ALIGN_PARAGRAPH.CENTER, size=10, after=0, spacing=1.15)
para([(YEAR, {"bold": True})], align=WD_ALIGN_PARAGRAPH.CENTER, size=11, after=0, spacing=1.15)

# ================================================================== CERTIFICATE
page_break()
p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER; p.add_run().add_picture(A("banner.png"), width=Inches(6.2))
centered_title("CERTIFICATE", before=26, after=22)
para([("This is to certify that the Dissertation Phase-I titled “", {}), (TITLE, {"bold": True}),
      ("” is the bonafide work carried out by ", {}), ("%s (%s)" % (STUDENT, ROLL), {"bold": True}),
      (", a student of M.Tech (AI & R) Semester-III at Chaitanya Bharathi Institute of Technology (A), Hyderabad, affiliated to Osmania University, Hyderabad, Telangana (India), during the academic year %s, submitted in partial fulfillment of the requirements for the degree in Master of Technology (AI & R) from " % YEAR, {}),
      ("Department of Information Technology", {"bold": True}),
      (" and that this work has not formed the basis for the award previously of any other degree, diploma, fellowship or any other similar title.", {})],
     spacing=1.5, after=36)
t = doc.add_table(rows=1, cols=2); t.autofit = False
for c, (lines) in zip(t.rows[0].cells, (("Supervisor", GUIDE1), ("Co-Supervisor", GUIDE2))):
    c.width = Inches(3.1)
    c.paragraphs[0].add_run(lines[0]).bold = True
    c.paragraphs[0].paragraph_format.line_spacing = 1.15
    q = c.add_paragraph(); q.add_run(lines[1]).bold = True; q.paragraph_format.line_spacing = 1.15
t.rows[0].cells[1].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT; t.rows[0].cells[1].paragraphs[1].alignment = WD_ALIGN_PARAGRAPH.RIGHT
para("", after=42)
for ln in ("Head, IT Dept.", HOD + ",", "Professor"):
    para([(ln, {"bold": True})], align=WD_ALIGN_PARAGRAPH.LEFT, spacing=1.15, after=0)
para("", after=18)
para([("Place:", {"bold": True})], align=WD_ALIGN_PARAGRAPH.LEFT, spacing=1.15, after=10)
para([("Date:", {"bold": True})], align=WD_ALIGN_PARAGRAPH.LEFT, spacing=1.15, after=0)

# ================================================================== ABSTRACT
page_break()
centered_title("ABSTRACT", before=20, after=14)
tp(105)
tp(107)
para(runs("Preliminary, model-derived results are reported for Damarakunta: 278 building candidates, 165 inside the village boundary and 163 eligible as house targets, plus five facilities (two schools, a health sub-centre and two Gram Panchayat headquarters points; the anganwadi is excluded). With a $25^{\\circ}$ slope limit, all 163 houses and all five facilities were routed; sharing edges reduced the unique house-route length from %.2f~km (independent routes) to %.2f~km in the two-stage network-aware plan (about %.1f%%, i.e. %.2f~km) and to %.2f~km in the roads-only shared-edge reference (about %.1f%%). These numbers are planning-level, have no field validation, and do not establish legal access, ownership, passability or construction feasibility. Limitations and the Phase-II plan are set out explicitly." % (ih["unique_len_m"] / 1000, hp["unique_len_m"] / 1000, 100 * sav / ih["unique_len_m"], sav / 1000, rr["unique_len_m"] / 1000, 100 * sav_ro / ih["unique_len_m"])),
     align=WD_ALIGN_PARAGRAPH.JUSTIFY)
_pr = [e_[0]["houses_primary"]["unique_len_m"] / e_[0]["houses_primary"]["n"] for v_ in _grp.values() for e_ in v_]
para("The planned experiments were then run on the real Damarakunta data. Removing the building penalty changes the unique house network from %s m to %s m (%.1f%%) and the routes that cross other building footprints from %d to %d. Across 20 synthetic omit/add perturbation runs (10%% and 20%% of targets, five seeds each) every placed target was still routed and the unique length per routed target stayed between %.1f m and %.1f m (baseline %.1f m). The perturbations are sensitivity probes, not measured segmentation error." % (
    N0(_pv[0][2]), N0(_pv[3][2]), 100 * (_pv[3][2] / _pv[0][2] - 1), _pv[0][4], _pv[3][4], min(_pr), max(_pr), hp["unique_len_m"] / hp["n"]))
para(runs(TL(111).replace("\\medskip\\noindent", "").strip()))

# ---- placeholder pages for TOC / LOT / LOF are inserted after the body is built (need entries); keep spot
page_break()
toc_anchor = doc.add_paragraph()   # replaced later

# ================================================================== MAIN MATTER
msec = new_section(fmt="decimal", start=1)

import sys as _sys
_sys.path.insert(0, r"D:\Telangana_Rural_Project\src\reporting")
import csv as _csv
import limitations_text as LT


def _clean(t):
    return t.replace("**", "").replace("`", "")


def md_to_doc(text, prefix, widths_by_cols, key):
    """small Markdown subset (### headings, one table, '- ' and '1. ' lists, paragraphs) -> report elements; headings numbered prefix.k"""
    lines = text.split("\n")[1:]
    i, k, para_buf = 0, 0, []
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("### "):
            k += 1
            title = ln[4:].split(" ", 1)[1]
            H(3, "%s.%d" % (prefix, k), title)
        elif ln.startswith("|"):
            blk = []
            while i < len(lines) and lines[i].startswith("|"):
                blk.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            rows = [[_clean(c) for c in r] for r in blk[2:]]
            if key:
                table_caption(key[0], key[1])
            make_table([_clean(c) for c in blk[0]], rows, widths_by_cols[len(blk[0])], size=7.5)
            continue
        elif ln.startswith("- ") or ln[:3] in ("1. ", "2. ", "3. ", "4. ", "5. ", "6. "):
            items, labs = [], []
            while i < len(lines) and (lines[i].startswith("- ") or lines[i][:3] in ("1. ", "2. ", "3. ", "4. ", "5. ", "6. ")):
                if lines[i].startswith("- "):
                    items.append(_clean(lines[i][2:])); labs.append("\u2022")
                else:
                    items.append(_clean(lines[i][3:])); labs.append(lines[i][:2])
                i += 1
            list_items(items, labels=labs)
            continue
        elif ln.strip():
            para(runs(_clean(ln)))
        i += 1


# ---------- 1 Introduction
H(1, "1", "Introduction")
H(2, "1.1", "Background and Motivation"); tp(125)
H(2, "1.2", "Problem Statement"); tp(128)
H(2, "1.3", "Research Gap"); tp(131)
H(2, "1.4", "Aim and Objectives"); tp(134)
para([("Objectives", {"bold": True})], keep=True, after=2)
list_items([re.sub(r"^\\item\s*", "", TL(n).strip()) for n in range(138, 145)], labels=["O%d." % i for i in range(1, 8)])
H(2, "1.5", "Scope of the Project"); tp(148)
H(2, "1.6", "Expected Contributions"); tp(151)
table_caption("contrib", "Established techniques, proposed contributions and status.")
make_table(["Item", "Description", "Status"], tex_rows(156, 159), [0.9, 4.2, 1.4], size=10)

# ---------- 2 Literature survey
H(1, "2", "Literature Survey and Critical Review")
tp(165)
H(2, "2.1", "Composition of the Review"); tp(168)
lit1 = file_rows("lit_table1.tex"); lit2 = file_rows("lit_table2.tex")
table_caption("lit1", "Reviewed literature (identification).")
make_table(["S.No", "Authors, year", "Title", "Venue", "Class", "Ref."], lit1, [0.4, 1.2, 2.5, 1.4, 0.55, 0.4], size=8)
table_caption("lit2", "Reviewed literature: objective, method/key findings (with project relevance) and limitations.")
make_table(["S.No", "Objective / outcome", "Method, key findings and relevance", "Limitations and gaps"], lit2, [0.4, 1.9, 2.0, 2.0], size=8)
H(2, "2.2", "Critical Discussion")
for num, ln, title in (("2.2.1", 175, "Road extraction and topology"), ("2.2.2", 178, "Building extraction and instance quality"),
                       ("2.2.3", 181, "Building–road interaction"), ("2.2.4", 184, "Domain adaptation, benchmarks and foundation models"),
                       ("2.2.5", 187, "Sparse labels and uncertainty"), ("2.2.6", 190, "Planning and optimisation")):
    H(3, num, title); tp(ln)
H(2, "2.3", "Alignment of the Reviewed Literature with the Pipeline")
para(runs("This section connects the 35 reviewed IEEE Transactions papers to the architectural choices of the pipeline. The word used is motivate, not prove: the papers report results on other datasets and tasks, and none of them evaluates a rural road-planning pipeline. Table @T:align@ pairs each implemented component with the papers that motivate it, states what those papers support, and states what the project does not claim.".replace("@T:align@", REF["tab:align"])))
table_caption("align", "Pipeline components, the reviewed papers that motivate them, and what is and is not claimed.")
make_table(["Pipeline component (as implemented)", "Motivating papers", "What the papers support", "What is not claimed"], [
    ["Segmentation of building footprints: DINOv2-Base encoder (768 channels) with FPN fusion (256), an ASPP module and a residual decoder (class StrongDINOv2Seg); the detection stage is reused as a verified input",
     "\\cite{L33,L34,L35}; multi-scale context \\cite{L06,L07,L16,L18}",
     "Pretrained vision foundation encoders and multi-scale context modules are an active and reported-effective direction; for example HyperR3SNet reports mean IoU of 67.60%, 55.86%, 80.07% and 96.46% on iSAID, LoveDA, Potsdam and Vaihingen \\cite{L35}, and a searched real-time network reports 54.5% mIoU on LoveDA \\cite{L18}.",
     "The model is not retrained or re-scored in this report; no reference labels exist for Damarakunta, so its accuracy there is not measured, and its weights provenance is undocumented."],
    ["Footprint quality classes (plausible, review, unresolved merge) instead of one confirmed building class",
     "Boundary and shape: \\cite{L03,L06,L08,L22}; review \\cite{L17}",
     "Boundary precision, shape regularisation and occlusion are recognised weaknesses of segmentation outputs, so ambiguous or merged blobs should not automatically become houses.",
     "No shape regulariser is implemented; the classes are rule-based and were checked only against independent layers."],
    ["Local layers and benchmark: LoveDA for the model background; TGRAC boundary, roads, parcels and facilities and Google Open Buildings v3 for local checks (Chapter 4)",
     "Domain shift: \\cite{L11,L43,L44,L45}; LoveDA \\cite{F05}",
     "Segmentation accuracy drops across sensors, regions and seasons, so benchmark scores do not transfer to a new village and local verification is needed.",
     "Agreement with Open Buildings or TGRAC is consistency, not accuracy."],
    ["Road layer: TGRAC road lines clipped to the village boundary; connectivity checked on the planning grid and on the lines",
     "\\cite{L36,L37,L38,L39}; \\cite{L12,L20}",
     "Road connectivity and topology matter for downstream use, and incomplete existing road maps are a recognised input problem; the TGRAC layer is incomplete near the boundary.",
     "No road extraction is performed; the papers improve raster road maps and do not join houses to a network."],
    ["Cost surface and least-cost routing: ordinal cost on a 10 m grid, 8-connected Dijkstra search with a binary heap (A* is not used; NetworkX is used only in one connectivity diagnostic; STRtree spatial indexes serve footprint tests)",
     "Foundations \\cite{F01,F02,F04,F03}; \\cite{L40,L41,L42}",
     "Cost-weighted path planning is established; planning with a realistic path distance instead of Euclidean or Manhattan distance reduced investment by 30% or more in a distribution-network study \\cite{L42}; multi-objective route planning is studied in \\cite{L40,L41}.",
     "Dijkstra and A* with an admissible heuristic return the same least-cost path; the choice affects speed only, which is not a constraint on a grid of 293,328 cells."],
    ["Two-stage generate-and-select planning: K = 3 candidate routes per target (Stage A), then selection by marginal cost with shared-edge credit and leaf re-routing (Stage B)",
     "\\cite{L40,L41,L42}",
     "Generating candidates and then choosing among them under an objective trade-off is consistent with improvement-heuristic and multi-objective planners; sharing infrastructure lowers network cost.",
     "Novelty is not claimed for shortest-path search or for sharing edges; the claim is the fair, unique-length accounting on one target set."],
    ["Target-set perturbation (C1) and building-penalty variants",
     "\\cite{L23,L24,L31}",
     "Sparse-label and semi-supervised work shows that predictions are uncertain and may be partial, which motivates testing how target changes propagate.",
     "The omit and add runs are synthetic probes, not measured segmentation error."],
], [1.8, 1.0, 2.2, 1.5], size=8)
para(runs("The chain from literature to results is as follows. The reviewed segmentation papers motivate the detection stage and its quality classes (Section 2.2.2); Chapter 4 documents the datasets that stand in for ground truth (LoveDA for the model background, and the TGRAC and Open Buildings layers for local checks); and the planner then turns the 163 eligible targets and five facilities into a shared network. On these inputs the two-stage plan has a unique house-route length of %s m against %s m for independent routes (a saving of %.1f%%), and Chapter 9 reports the sensitivity of that result. The papers themselves are not evidence for these numbers." % (N0(hp["unique_len_m"]), N0(ih["unique_len_m"]), 100 * sav / ih["unique_len_m"])))

# ---------- 3 Research gap
H(1, "3", "Research Gap and Proposed Contributions")
tp(193)
list_items([re.sub(r"^\\item\s*", "", TL(n).strip()) for n in range(195, 201)], labels=["%d." % i for i in range(1, 7)])
tp(202)
table_caption("gapmat", "Research-gap matrix: what the reviewed literature does, what is missing and how the project responds.")
make_table(["Gap", "What the reviewed papers do", "What is missing", "Project response"],
           [[X(c) for c in r] for r in C.GAP_MATRIX], [1.1, 2.0, 1.7, 1.7], size=8)

# ---------- 4 Datasets
H(1, "4", "Dataset Sources, Description and Justification")
tp(206)
table_caption("datasets", "Datasets: source, coverage and records.")
make_table(["Dataset", "Source / link", "Coverage, resolution, CRS", "Records and attributes", "Limitations"],
           [[r[0], r[1], r[2], r[3] + ". " + r[4], r[5]] for r in tex_rows(214, 223)],
           [1.2, 1.5, 1.2, 1.5, 1.6], size=8)
table_caption("datasets2", "Why each dataset was selected and how it is used.")
make_table(["Dataset", "Reason for selection", "Use"], tex_rows(231, 239), [1.4, 3.7, 1.4], size=10)
H(2, "4.1", "Verified Counts and Units")
para(runs("Table @T:dsunits@ separates image counts, vector features, candidate buildings, routing targets, raster cells and route alternatives, and gives the source of each count. Counts marked as read from a file were measured on 29 October 2026; LoveDA figures come from its Zenodo record and arXiv abstract. Where the licence or acquisition date is not recorded, the table says so instead of assuming one.".replace("@T:dsunits@", REF["tab:dsunits"])))
table_caption("dsunits", "Dataset inventory with units, verified counts, source and status.")
para(runs("Update of 31 October 2026: at the project owner's request the anganwadi (facility 1702300, Damarakunt-I) is excluded from the final planning layers, tables and maps because its TGRAC coordinate lies 371 m from the nearest detected footprint (inputs/EXCLUSIONS.md). Two Gram Panchayat headquarters points are added as administrative utilities (Section 4.3). All facility counts and results in this report refer to the final five-facility layer; the verified four-facility baseline run is used only for the reproduction check."))
make_table(["Dataset", "Unit", "Count and size", "Source and link", "Status"], [[X(c) for c in r] for r in C.DS_UNITS], [0.9, 0.7, 2.0, 1.7, 1.4], size=7.5)
H(2, "4.2", "Role of Each Source and What LoveDA Does Not Show")
para(runs("The sources play complementary roles. Imagery gives building candidates; the TGRAC boundary limits the study area; the TGRAC roads give the existing network that routes must reach; land cover and slope give the cost surface; facilities give the first planning group; cadastral parcels and school compounds are used only to flag possible exposure, not ownership. Each also has a weakness: the imagery has no recorded date, the roads are incomplete and extend beyond the boundary, the building candidates are unverified, the DEM is coarse, and the parcel layer does not show legal access."))
para(runs("LoveDA is a public land-cover benchmark with 5,987 images at 0.3 m from three Chinese cities, with urban and rural domains \\cite{F05}. It is useful for developing and comparing segmentation methods and for framing the domain-shift question behind C3. It is not a Telangana dataset, and no LoveDA score is evidence of how well buildings or roads are found in Damarakunta. Model results from LoveDA development are therefore not reported here as Damarakunta accuracy."))

H(2, "4.3", "Administrative and Governance Utilities")
_vf = {r["facility_id"]: r for r in _csv.DictReader(open(r"D:\Telangana_Rural_Project\outputs\verification\facility_verification.csv", encoding="utf-8-sig"))}
_g1, _g2 = _vf["GP_DAMARAKUNTA"], _vf["GP_KASHIREDDYPALLY"]
para(runs("Besides schools and the health sub-centre, a village baseline needs the administrative and governance points that residents use: the Gram Panchayat office, the MeeSeva citizen-service centre and the Directorate of Electronic Service Delivery (ESD) service and Aadhaar centre. They are treated as primary administrative utility points of the village baseline, and the same layer structure is meant to be reused for other villages. Table @T:admin@ gives the source, count, position, checks and status of each. Only the Gram Panchayat headquarters points could be sourced.".replace("@T:admin@", REF["tab:admin"])))
table_caption("admin", "Administrative and governance utilities: source, count, position and verification status.")
make_table(["Utility", "Source and count", "Position (lat, lon)", "Checks against other layers", "Status"], [
    ["Damarakunta Gram Panchayat headquarters", "TGRAC Administrative Information System, MapServer layer 10 (Gram Panchayat Head Quarter, point layer); 1 point", "%s N, %s E" % (_g1["lat"], _g1["lon"]),
     "Inside the village boundary; table latitude/longitude equals the geometry; %s m from a detected footprint (an unresolved-merge blob, building not identified); %s m from an Open Buildings polygon" % (_g1["dist_to_nearest_footprint_m"], _g1["nearest_open_buildings_m"]), "Included in the facility layer"],
    ["Kashireddypally Gram Panchayat headquarters (second GP whose revenue village is Damarakunta)", "Same layer; 1 point", "%s N, %s E" % (_g2["lat"], _g2["lon"]),
     "Inside the boundary, in the eastern settlement; %s m from a detected footprint; %s m from an Open Buildings polygon" % (_g2["dist_to_nearest_footprint_m"], _g2["nearest_open_buildings_m"]), "Included in the facility layer"],
    ["MeeSeva centre", "No source found: none of the 162 TGRAC map services (2,019 layers) has a MeeSeva, ESD, Aadhaar or citizen-service layer, and OpenStreetMap has no such feature in the village area; 0 points", "not located", "none possible", "Not included; coordinate and source needed"],
    ["Directorate of ESD (Aadhaar/service) centre", "Same search; 0 points", "not located", "none possible", "Not included; coordinate and source needed"]],
    [1.3, 1.9, 1.0, 1.9, 0.9], size=8)
para(runs("Selection reason. The Gram Panchayat is the village's governance body and a destination for residents; its headquarters location is published by TGRAC in the same service as the village boundary, which makes the source official, queryable by village and reusable for every other village in the template. Verification means agreement with independent layers: both points lie inside the boundary and on or within 1 m of a detected building footprint and within 4 m of an Open Buildings polygon. This shows consistency, not that the building is the Panchayat office; TGRAC calls the point a headquarters location, and a visual or field check is still needed. The MeeSeva and ESD centres are not placed on a guess: in many villages the MeeSeva centre sits in the Panchayat office, but that is an assumption and is not applied. Coordinates for them can be added through inputs/admin_utilities_intake.csv once a source (the MeeSeva or UIDAI locator, a register or a field GPS reading) is available."))
para(runs("Facility counts used throughout this report: five facilities in the final layer (primary school, high school, sub-centre and two Gram Panchayat headquarters points). The TGRAC anganwadi (Damarakunt-I) is excluded because its coordinate lies 371 m from the nearest detected footprint (inputs/EXCLUSIONS.md); it is kept only as an excluded record. Note on the two Gram Panchayat points: the headquarters points of two Gram Panchayat jurisdictions, Damarakunta and Kashireddypally, both lie inside the Damarakunta village boundary (the second in the eastern settlement), so both administrative panchayat jurisdiction points are held in the spatial database and both are planning targets."))

# ---------- 5 Architecture
H(1, "5", "Proposed System Architecture")
H(2, "5.1", "Overview"); tp(246)
figure("arch", "High-level architecture in nine stages. Dark gray: implemented and run; light gray: implemented but inputs or evidence unverified or synthetic; white with dashed border: planned.", "fig_arch_v2.png", 4.6)
figure("flow", "Detailed workflow: inputs, scripts and outputs. Shading as in Figure 1; every box corresponds to a script or output in the project folder.", "fig_flow_v2.png", 4.8)
table_caption("modules", "Module description (status as of this report).")
make_table(["#", "Module", "Purpose (input)", "Algorithm", "Output; evaluation", "Status"],
           [[r[0], r[1], r[2] + " (input: " + r[3] + ")", r[4], r[5] + "; evaluation: " + r[6], r[7]] for r in tex_rows(307, 326)],
           [0.5, 1.0, 1.5, 1.25, 1.8, 0.95], size=7.5)
H(2, "5.2", "Stage-by-Stage Description")
para(runs("The nine stages below follow Figure 1. Each gives inputs, processing, outputs, validation, limitations and the execution status. Table @T:stages@ summarises them. Stages 1 to 8 were run on Damarakunta; Stage 9 has not started.".replace("@T:stages@", REF["tab:stages"])))
table_caption("stages", "Summary of the nine stages (inputs, processing, outputs, validation and status).")
make_table(["Stage", "Inputs", "Processing", "Outputs", "Validation", "Status"], C.STAGE_TABLE, [0.55, 1.35, 1.45, 1.0, 1.25, 1.0], size=7.5)
for num, title, status, inp, proc, outp, val, lim in C.STAGES:
    H(3, num, title)
    for lead, txt in (("Status. ", status), ("Inputs. ", inp), ("Processing. ", proc), ("Outputs. ", outp), ("Validation. ", val), ("Limitations. ", lim)):
        para([(lead, {"bold": True})] + runs(X(txt)))

# ---------- 6 Methodology
H(1, "6", "Detailed Methodology and Workflow")
H(2, "6.1", "GIS Data Preparation and Georeferencing"); tp(336)
H(2, "6.2", "Remote Sensing-Based Building and Land-Cover Processing"); tp(339)
figure("bq", "Building-candidate quality classes inside the village (n = 165). The classes are model-derived and do not confirm house identity.", "building_quality.png", 4.6)
H(2, "6.3", "Road Network Extraction and Existing Road Integration"); tp(347)
H(2, "6.4", "Public-Service Facility and House Connectivity Planning")
para(runs(fix(350, ("Four facilities (a primary school, a high school, one sub-centre, one anganwadi)", "Five facilities (a primary school, a high school, one sub-centre and two Gram Panchayat headquarters points from TGRAC; the anganwadi is excluded)"))))
H(2, "6.5", "Multi-Criteria Route Generation and Route Selection")
H(3, "6.5.1", "Cost surface"); tp(354); equation("cost", "eq_cost.png", 3.4); tp(358)
H(3, "6.5.2", "Building penalty")
para(runs(fix(361, ("are multiplied by $m=4$:", "raise the edge weight by a factor $m=4$ when the planner enters them:"))))
equation("pen", "eq_pen.png", 5.4)
para(runs(fix(365, ("It is a cost, not a block.", "It is a cost, not a block: in the planner (plan\\_network\\_v2.py) the weight of a step into a penalised cell is multiplied by $m$."),
    ("are planned runs.", "are reported in Section 9.3."))))
H(3, "6.5.3", "Path cost and shared-edge credit")
para(runs(fix(368, ("This formulation should be checked against the planner source before final submission.",
                    "This formulation was checked against the planner source (plan\\_network\\_v2.py), where the step weight is $0.5\\,(c_u+c_v)$ times the step length."))))
equation("credit", "eq_credit.png", 5.3)
tp(372)
# algorithm
para([("Algorithm 1. ", {"bold": True}), ("Two-stage generate-and-select planning (schematic)", {})], align=WD_ALIGN_PARAGRAPH.CENTER, size=11, spacing=1.0, before=6, after=4, keep=True)
alg = [
    "Input: cost surface c, goal cells G (roads), facilities F, house targets H",
    "1.  Route each facility f ∈ F to G by Dijkstra; add its cells to G_F",
    "2.  for each house h ∈ H in fixed order:",
    "3.       route h to G ∪ G_F ∪ G_H; record attachment class",
    "4.       add the route’s cells to G_H",
    "5.  Compute L_unique, credits (Eq. 3), components and attachment chains",
    "6.  Re-run with roads only as goals for the reference baseline",
]
t = doc.add_table(rows=1, cols=1); t.alignment = WD_TABLE_ALIGNMENT.CENTER; set_borders(t)
c = t.rows[0].cells[0]; c.width = Inches(6.0)
for i, a in enumerate(alg):
    q = c.paragraphs[0] if i == 0 else c.add_paragraph()
    q.paragraph_format.line_spacing = 1.0; q.paragraph_format.space_after = Pt(1)
    r = q.add_run(a); r.font.size = Pt(10.5); r.bold = (i == 0)
doc.add_paragraph().paragraph_format.space_after = Pt(4)
H(3, "6.5.4", "Planning-level versus real-world feasibility"); tp(389)
H(2, "6.6", "Sensitivity and Uncertainty Design (C1)")
para("Two perturbations are defined. Omit removes a random fraction (0.10 or 0.20) of scenario targets and their footprints, representing missed detections. Add inserts synthetic translated copies (15–50 m) of random buildings on valid cells at least 1 m from roads, representing spurious detections; synthetic additions are probes only. Seeds are fixed (20261029–20261033) so runs are reproducible. Both perturbations, with five seeds per setting, and the three penalty variants have been run on the real Damarakunta data; the results are in Sections 9.3 and 9.4. They measure sensitivity to synthetic target changes and not real segmentation error.")

# ---------- 7 Experimental setup
H(1, "7", "Experimental Setup and Evaluation Metrics")
for n, title in ((396, "Scenarios"), (398, "Metrics"), (400, "Baselines")):
    tp(n)
para([("Automated validation. ", {"bold": True}), ("A read-only validator checks required files, manifest hashes, target counts and identifiers, duplicates and missing targets, geometry validity, connectivity, failure reasons, regression against the reference and reproducibility of paired runs. Stage A passed 51 checks with 9 informational notes and 0 warnings or failures. The Stage B acceptance validator covered 30 runs (primary scenarios, penalty variants, perturbation runs and paired reruns): 396 PASS, 28 INFO, 0 WARN and 0 FAIL; it rates the one house route that ends on a disconnected road fragment as INFO. A separate connectivity audit (version 2) applies a stricter rule to the same route and reports it as a failure (Section 9.5). The two audits have different scopes and are not interchangeable.", {})])
tp(404)

# ---------- 8 Implementation
H(1, "8", "Implementation and Current Project Progress")
tp(408)
table_caption("progress", "Progress summary.")
prog = tex_rows(414, 420)
prog[1] = ["Stage B runs", "S1 and S2 at $25^{\\circ}$ and $10^{\\circ}$, plus C1 scenario; per-run acceptance checks have 0 FAIL; connectivity audit v2 reports one failed attachment (C0002)", "\\impl"]
prog[3] = ["Penalty variants P1--P3", "Run on real data for S2 at $25^{\\circ}$ (Table %s)" % REF["tab:pen"], "\\impl"]
prog[4] = ["Perturbation runs (omit/add)", "20 runs on real data (final family): omit and add, 10\\% and 20\\%, five seeds each (Table " + REF["tab:unc"] + "); synthetic probes only", "\\impl"]
prog[5] = ["Automated validator and final tables", "%s (acceptance validator, final family); final tables written" % VAL_TEXT, "\\impl"]
prog.append(["Literature review", "35 IEEE Transactions papers (2020 to 2026): metadata verified against the DOI registry; methodology, findings and limitations extracted for every paper", "Complete"])
prog.append(["Evidence-status items", "Twelve open items tracked in Table %s" % REF["tab:evid"], "\\partialS"])
make_table(["Component", "Evidence", "Status"], prog, [1.7, 3.8, 1.0], size=10)

# ---------- 9 Results
exec(open(os.path.join(HERE, 'report_results_block.py'), encoding='utf-8').read(), globals())

# ---------- 10-12
H(2, "9.7", "Building-Avoiding Network and Illustrative Economics")
def _rd(path):
    try:
        return list(_csv.DictReader(open(path, encoding="utf-8-sig")))
    except Exception:
        return []
_t6 = _rd(r"D:\Telangana_Rural_Project\outputs\final_comparison\table6_obstacle_avoidance.csv")
_t5 = _rd(r"D:\Telangana_Rural_Project\outputs\final_comparison\table5_economic_material_impact.csv")
if _t6:
    para(runs("Strict no-go zones around building footprints were tried first and failed: every house point lies inside its own blocked cell, so all 163 house routes failed. Footprints buffered by 7.1 m with a large penalty were then used. All 163 houses are routed, but the routes do not completely skirt buildings: the remaining crossings occur mostly where a target starts among touching buildings. Table @T:avoid@ gives the effect (three retained facilities). The effect saturates by a penalty of x20.".replace("@T:avoid@", REF["tab:avoid"])))
    table_caption("avoid", "Building avoidance: length and footprint crossings (house routes; anganwadi excluded).")
    make_table(["Scenario", "Houses routed", "House unique length (m)", "Saving vs independent (%)", "Routes crossing other footprints", "Crossing length (m)", "Facility routes (m)"],
               [[r["scenario"], r["houses_routed"], r["house_unique_len_m"], r["saving_vs_independent_pct"], r["house_routes_crossing_other_footprints"], r["crossing_len_m"], r["facility_unique_len_m"]] for r in _t6],
               [1.5, 0.6, 0.8, 0.8, 0.9, 0.7, 0.7], size=8)
if _t5:
    a_, b_ = _t5[0], _t5[1]
    para(runs("Illustrative economics (assumptions, not project data: Rs 75 lakh/km supplied by the project owner and not checked against PMGSY or a State Schedule of Rates; one assumed pavement section). The fair baseline is the unique length of the independent routes (%s m), not their sum (%s m), because a shared edge is built once. The saving is %s m (%s%%), about Rs %s lakh at the assumed rate. Subtracting the shared network from the double-counted sum gives %s m (%.2f km), which overstates the saving about three times and is not a saving. These figures are not an engineering estimate." % (
        a_["baseline_len_m"], b_["baseline_len_m"], a_["length_saving_m"], a_["length_saving_pct"], a_["cost_saving_central_Rs_lakh"], b_["length_saving_m"], float(b_["length_saving_m"]) / 1000)))
    table_caption("econ", "Illustrative length and cost saving of the shared network (Rs 75 lakh/km assumed).")
    make_table(["Baseline", "Baseline length (m)", "Shared network (m)", "Length saving (m)", "Saving (%)", "Cost saving (Rs lakh)"],
               [[r["baseline_basis"], r["baseline_len_m"], r["proposed_len_m"], r["length_saving_m"], r["length_saving_pct"], r["cost_saving_central_Rs_lakh"]] for r in _t5],
               [2.2, 0.8, 0.8, 0.8, 0.6, 0.8], size=8)
H(1, "10", "Limitations and Threats to Validity")
H(2, "10.1", "Evidence-Status Table")
para(runs(X("Table @T:evid@ lists each open issue, what is known, what is not, the corrective action and a closure criterion. An issue stays unresolved until the closure criterion is met; describing it in this report does not close it. The Damarakunta completion gate is not approved, and this report is not final.")))
table_caption("evid", "Evidence status of open issues.")
make_table(["Issue (type)", "Known and evidence", "Remaining unknown", "Corrective action and closure criterion", "Status"], [[X(c) for c in r] for r in C.EVIDENCE], [1.25, 1.85, 1.05, 1.75, 0.9], size=7.5)
H(2, "10.2", "Limitations")
list_items([re.sub(r"^\\item\s*", "", TL(n).strip()) for n in range(483, 493)] +
           ["In nine of the ten add-perturbation runs some requested synthetic buildings could not be placed, so the perturbation size is slightly below the nominal fraction."])
H(2, "10.3", "Methodological Limitations and Future Scope")
md_to_doc(LT.TEXT, "10.3", {4: [1.2, 1.7, 2.2, 1.5]}, ("terms", "Data sources, attribution and recorded usage terms (none confirmed in writing)."))
para(runs("The sources, attribution and usage terms of every dataset are summarised in the Data Availability Statement before the References; no usage terms have been confirmed in writing."))
H(1, "11", "Future Work and Phase-II Plan")
list_items([
    "Replace the synthetic perturbations by label-based error propagation: build reference labels for a village subset and measure how real segmentation errors change the plan (C1).",
    "Check the road fragment on which target C0002 ends against imagery and the road layer beyond the boundary, and review the maps and inset boxes visually.",
    "Verify facility identities against official registries and obtain imagery metadata.",
    "Document the DEM and land-cover sources and test a finer DEM where available.",
    "Decide whether a second village allows an honest test of C3.",
    "Extend the novelty comparison with prior art beyond the 35 IEEE Transactions papers reviewed.",
    "Run the P3 baseline reproduction and send the imagery licence enquiry."], labels=["%d." % i for i in range(1, 8)])
H(1, "12", "Conclusion")
para(runs(fix(507, ("the C1 experiments and C3 transfer remain to be done, and the Phase-II plan targets them together with verification of data sources.",
    "the C1 experiments are synthetic sensitivity probes without real labels, C3 transfer remains to be done, and the Phase-II plan targets both together with verification of data sources."))))

# ---------- Data Availability Statement
toc_entries.append((1, "", "Data Availability Statement"))
p = doc.add_paragraph(style="Heading 1"); p.add_run("DATA AVAILABILITY STATEMENT")
for _t in [
    "The study uses publicly accessible geospatial data for Damarakunta village, Siddipet district, Telangana, for non-commercial academic research only.",
    "Satellite imagery. Imagery was obtained through the Esri World Imagery service, accessed via its public ArcGIS REST export endpoint (services.arcgisonline.com). The imagery is © Esri and its data providers and is used here under Esri's published terms for the service. The imagery itself is not redistributed with this report.",
    "Administrative and infrastructure data. The village boundary, road network, cadastral parcels, school and health facility locations and Gram Panchayat headquarters points were obtained from the Telangana Remote Sensing Applications Centre (TGRAC), Government of Telangana, through its public ArcGIS REST services (tgrac.telangana.gov.in). Ownership of these data remains with the originating agency.",
    "Other data. Elevation and land-cover rasters were taken from publicly available global products, as documented in the data-sources table (Section 10.3).",
    "Derived data and code. Building footprints, cost surfaces, routes and result tables were generated by the author from these inputs and are model-derived, planning-level outputs. The processing scripts, run manifests with file hashes and result tables are available from the author on reasonable request. Redistribution of the source layers is subject to the terms of the providers named above.",
    "Written confirmation of usage terms will be requested from the data providers; until it is received, no redistribution rights are claimed.",
]:
    para(_t, align=WD_ALIGN_PARAGRAPH.JUSTIFY)

# ---------- References
toc_entries.append((1, "", "References"))
p = doc.add_paragraph(style="Heading 1"); p.add_run("REFERENCES")
for k in cite_order:
    e = bib[k]
    au = e.get("author", "").replace(" and others", " et al.")
    au = "" if au.lower().startswith("authors to be confirmed") else au
    venue = e.get("journal") or e.get("booktitle") or e.get("howpublished") or ""
    pg = e.get("pages", "").replace("--", "–")
    pg = "" if not pg else (", pp. %s" % pg if re.search(r"[-–]", pg) else ", Art. no. %s" % pg)
    vn = (", vol. %s" % e["volume"] if e.get("volume") else "") + (", no. %s" % e["number"] if e.get("number") else "")
    txt = "%s%s“%s,” %s%s%s, %s." % (au, ", " if au else "", e.get("title", ""), venue, vn, pg, e.get("year", ""))
    if e.get("doi"): txt += " doi: %s." % e["doi"]
    q = para([("[%d]\t" % CITE[k], {}), (txt, {})], spacing=1.15, after=5)
    q.paragraph_format.left_indent = Inches(0.45); q.paragraph_format.first_line_indent = Inches(-0.45)
    q.paragraph_format.tab_stops.add_tab_stop(Inches(0.45))

import json as _json
lit_ver = [m for m in _json.load(open("lit_verified.json", encoding="utf-8")) if m["qualifies"] and m["key"] in CITE]
lit_ver.sort(key=lambda m: CITE[m["key"]])
H(1, "A", "Verified Bibliographic Details of the 35 IEEE Transactions Papers")
para(runs("Each entry below was checked against its DOI-registry record (Crossref) on 29 October 2026: all authors, journal, volume, issue where given, pages or article number, year and DOI. Every journal is an IEEE Transactions title and every paper was published between 2020 and 2026. Links of the form https://doi.org/DOI lead to the IEEE Xplore page. Together with the objective, method, findings and limitations extracted for each paper (Tables 2 to 4), this completes the literature review for the 35-paper scope."))
table_caption("applit", "Verified details of the 35 qualifying IEEE Transactions papers.")
make_table(["Ref.", "Authors", "Journal, volume, pages, year", "DOI"],
           [["[%d]" % CITE[m["key"]], m["authors"].replace("; ", ", "),
             "%s, vol. %s%s, %s, %s" % (m["journal"].replace("IEEE Transactions on", "IEEE Trans."), m["volume"], (", no. " + m["issue"]) if m["issue"] else "", ("pp. " + m["pages"]) if "-" in m["pages"] else ("art. no. " + m["pages"]), m["year"]),
             m["doi"]] for m in lit_ver],
           [0.4, 2.3, 2.3, 1.5], size=7)

# ================================================================== TOC / LOT / LOF (front matter, before body)
body = doc.element.body
def new_front_blocks():
    """build TOC, LOT, LOF in a scratch container and move them before the first main-matter section."""
    start = len(body) - 1
    centered_title("Table of Contents", size=14, before=0, after=10).paragraph_format.page_break_before = True
    t = doc.add_table(rows=1, cols=3); t.autofit = False; set_borders(t)
    widths = (0.75, 4.8, 0.7)
    def put(cells, texts, bold=False, indent=0.0):
        for i, (c, tx) in enumerate(zip(cells, texts)):
            c.width = Inches(widths[i]); q = c.paragraphs[0]; q.paragraph_format.line_spacing = 1.0; q.paragraph_format.space_after = Pt(1)
            if i == 1: q.paragraph_format.left_indent = Inches(indent)
            r_ = q.add_run(tx); r_.bold = bold; r_.font.size = Pt(11)
    hdr = t.rows[0].cells
    put(hdr, ("Section No.", "Content", "Page No."), True)
    for c in hdr: shade(c, "D9D9D9")
    front = [("Title Page", "i"), ("Certificate", "ii"), ("Abstract", "iii"),
             ("Table of Contents", "iv"), ("List of Tables", PAGES.get("lot_roman", "vii")), ("List of Figures", PAGES.get("lof_roman", "viii"))]
    for name, pg in front:
        put(t.add_row().cells, ("", name, pg), indent=0.1)
    for lvl, num, title in toc_entries:
        label = title.upper() if lvl == 1 else title
        pg = str(PAGES.get("toc", {}).get("%s|%s" % (num, title), ""))
        put(t.add_row().cells, (num if lvl == 1 else "", ("%s %s" % (num, title) if lvl > 1 else label), pg), bold=(lvl == 1), indent=0.0 if lvl == 1 else (0.15 if lvl == 2 else 0.45))
    for r in t.rows: no_split(r)
    repeat_header(t.rows[0])
    centered_title("List of Tables", size=14, before=0, after=10).paragraph_format.page_break_before = True
    tt = doc.add_table(rows=1, cols=3); tt.autofit = False; set_borders(tt)
    put(tt.rows[0].cells, ("Table No.", "Table Title", "Page No."), True)
    for c in tt.rows[0].cells: shade(c, "D9D9D9")
    for n, text in sorted(captions["tables"]):
        put(tt.add_row().cells, ("Table %d" % n, "".join(a for a, _ in runs(text)), str(PAGES.get("tables", {}).get(str(n), ""))))
    centered_title("List of Figures", size=14, before=0, after=10).paragraph_format.page_break_before = True
    tf = doc.add_table(rows=1, cols=3); tf.autofit = False; set_borders(tf)
    put(tf.rows[0].cells, ("Figure No.", "Figure Title", "Page No."), True)
    for c in tf.rows[0].cells: shade(c, "D9D9D9")
    for n, text in sorted(captions["figures"]):
        put(tf.add_row().cells, ("Figure %d" % n, "".join(a for a, _ in runs(text)), str(PAGES.get("figures", {}).get(str(n), ""))))
    return list(body)[start:]

blocks = new_front_blocks()
# the sectPr of the document must stay last in body; move the blocks before toc_anchor's successor (the main-matter section break)
anchor = toc_anchor._p
for b in blocks:
    if b.tag == qn("w:sectPr"): continue
    anchor.addprevious(b)
anchor.getparent().remove(anchor)

# main-matter section break paragraph precedes body; make sure TOC/LOT/LOF pages sit in front-matter section
doc.core_properties.title = "A Dissertation Phase-I Review -1 Report"
doc.core_properties.author = STUDENT.title()
doc.save(OUT)
json.dump({"toc": ["%s|%s" % (n, t) for _, n, t in toc_entries], "tables": captions["tables"], "figures": captions["figures"]},
          open(os.path.join(HERE, "_entries.json"), "w", encoding="utf-8"))
print("saved", OUT, "refs", len(cite_order))
