"""Small helpers to build an IEEE-Journal-style two-column Word document with python-docx."""
import re
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.text import WD_ALIGN_PARAGRAPH as AL
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt

FONT = "Times New Roman"

def set_cols(section, n, space=0.25):
    sp = section._sectPr
    for c in sp.findall(qn("w:cols")): sp.remove(c)
    cols = OxmlElement("w:cols"); cols.set(qn("w:num"), str(n)); cols.set(qn("w:space"), str(int(space * 1440)))
    sp.append(cols)

def font(run, size=10, bold=False, italic=False, sub=False, sup=False, smallcaps=False):
    run.font.name = FONT; run._element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    run.font.size = Pt(size); run.bold = bold; run.italic = italic
    run.font.subscript = sub; run.font.superscript = sup; run.font.small_caps = smallcaps

TOK = re.compile(r"(\*\*.+?\*\*|\*.+?\*|_\{.+?\}|\^\{.+?\})")
def add_runs(p, text, size=10, bold=False, italic=False, smallcaps=False):
    for part in TOK.split(text):
        if not part: continue
        if part.startswith("**"): r = p.add_run(part[2:-2]); font(r, size, True, italic, smallcaps=smallcaps)
        elif part.startswith("*"): r = p.add_run(part[1:-1]); font(r, size, bold, True, smallcaps=smallcaps)
        elif part.startswith("_{"): r = p.add_run(part[2:-1]); font(r, size, bold, italic, sub=True)
        elif part.startswith("^{"): r = p.add_run(part[2:-1]); font(r, size, bold, italic, sup=True)
        else: r = p.add_run(part); font(r, size, bold, italic, smallcaps=smallcaps)

def fmt(p, align=AL.JUSTIFY, before=0, after=0, first=None, left=None, hanging=None, line=None, keep=False):
    pf = p.paragraph_format; p.alignment = align
    pf.space_before = Pt(before); pf.space_after = Pt(after)
    if first is not None: pf.first_line_indent = Inches(first)
    if left is not None: pf.left_indent = Inches(left)
    if hanging is not None: pf.left_indent = Inches(hanging); pf.first_line_indent = Inches(-hanging)
    if line: pf.line_spacing = line
    pf.keep_with_next = keep
    return p

def cell_borders(cell, **kw):
    tcPr = cell._tc.get_or_add_tcPr(); b = tcPr.find(qn("w:tcBorders"))
    if b is None: b = OxmlElement("w:tcBorders"); tcPr.append(b)
    for edge, val in kw.items():
        e = OxmlElement(f"w:{edge}"); e.set(qn("w:val"), "single" if val else "nil"); e.set(qn("w:sz"), "6"); e.set(qn("w:color"), "000000"); b.append(e)

def cell_margins(table, top=15, bottom=15, left=50, right=50):
    tblPr = table._tbl.tblPr; m = OxmlElement("w:tblCellMar")
    for k, v in (("top", top), ("left", left), ("bottom", bottom), ("right", right)):
        e = OxmlElement(f"w:{k}"); e.set(qn("w:w"), str(v)); e.set(qn("w:type"), "dxa"); m.append(e)
    tblPr.append(m)
