"""Builds MTech_Major_Project_Review.pptx (numbers traced in PRESENTATION_RESULTS_AUDIT.md).
Run:  python -I build_deck.py   (needs python-pptx; Pillow)"""
import os, sys
sys.path.insert(0, os.environ.get("PPTX_LIB", ""))
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION
from pptx.oxml.ns import qn
from lxml import etree
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(HERE, "images")
OUT = os.path.join(HERE, "MTech_Major_Project_Review.pptx")

DARK, MID, ACC, LIGHT, TXT, MUTED, WARN, BLUE, WHITE, RULE = (
    "16382E", "2E7D5B", "D99A00", "F1F5F3", "1E2B26", "5B6B64", "B5483A", "3A6EA5", "FFFFFF", "D5DDD9")
AMBERBG, AMBERTX, GREENBG = "FBF1DC", "8A6100", "E6F2EC"
HF, BF = "Cambria", "Calibri"


def rgb(h):
    return RGBColor.from_string(h)


prs = Presentation()
prs.slide_width, prs.slide_height = Inches(10), Inches(5.625)
LAYOUT_TITLE_ONLY = prs.slide_layouts[5]
LAYOUT_BLANK = prs.slide_layouts[6]


def set_bg(slide, color):
    f = slide.background.fill
    f.solid()
    f.fore_color.rgb = rgb(color)


def _style_run(r, size, bold=False, color=TXT, font=BF, italic=False):
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.italic = italic
    r.font.name = font
    r.font.color.rgb = rgb(color)


def _bullet(p, on=True):
    pPr = p._p.get_or_add_pPr()
    for t in ("a:buNone", "a:buChar"):
        for e in pPr.findall(qn(t)):
            pPr.remove(e)
    if on:
        pPr.set("marL", str(Inches(0.2)))
        pPr.set("indent", str(-Inches(0.2)))
        bu = etree.SubElement(pPr, qn("a:buChar"))
        bu.set("char", "•")
    else:
        etree.SubElement(pPr, qn("a:buNone"))


def tb(slide, text, x, y, w, h, size=14, bold=False, color=TXT, font=BF, align="l",
       valign="t", bullets=False, space=6, italic=False, name=None):
    """text: str or list of str (paragraphs)."""
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    if name:
        box.name = name
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = {"t": MSO_ANCHOR.TOP, "m": MSO_ANCHOR.MIDDLE, "b": MSO_ANCHOR.BOTTOM}[valign]
    paras = text if isinstance(text, list) else [text]
    for i, t in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = {"l": PP_ALIGN.LEFT, "c": PP_ALIGN.CENTER, "r": PP_ALIGN.RIGHT}[align]
        p.space_after = Pt(space if len(paras) > 1 else 0)
        r = p.add_run()
        r.text = t
        _style_run(r, size, bold, color, font, italic)
        if bullets:
            _bullet(p)
    return box


def rect(slide, x, y, w, h, fill=LIGHT, line=RULE, shape=MSO_SHAPE.RECTANGLE):
    s = slide.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    s.fill.solid()
    s.fill.fore_color.rgb = rgb(fill)
    s.line.color.rgb = rgb(line)
    s.line.width = Pt(0.75)
    s.shadow.inherit = False
    return s


def card(slide, x, y, w, h, fill=LIGHT):
    return rect(slide, x, y, w, h, fill, RULE)


def chip(slide, text, x, y, w, color):
    s = rect(slide, x, y, w, 0.3, color, color, MSO_SHAPE.ROUNDED_RECTANGLE)
    tf = s.text_frame
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = text
    _style_run(r, 10, True, WHITE)


def circle(slide, text, x, y, d, fill, size=14):
    s = rect(slide, x, y, d, d, fill, fill, MSO_SHAPE.OVAL)
    tf = s.text_frame
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = text
    _style_run(r, size, True, WHITE)


def pic(slide, fname, x, y, w, h, alt):
    path = os.path.join(IMG, fname)
    iw, ih = Image.open(path).size
    ar = iw / ih
    pw, ph = w, w / ar
    if ph > h:
        ph, pw = h, h * ar
    p = slide.shapes.add_picture(path, Inches(x + (w - pw) / 2), Inches(y + (h - ph) / 2), Inches(pw), Inches(ph))
    p._element.nvPicPr.cNvPr.set("descr", alt)
    return p


slide_no = [0]


def content(title, notes):
    s = prs.slides.add_slide(LAYOUT_TITLE_ONLY)
    set_bg(s, WHITE)
    t = s.shapes.title
    t.left, t.top, t.width, t.height = Inches(0.5), Inches(0.25), Inches(9), Inches(0.75)
    tf = t.text_frame
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.LEFT
    r = p.add_run()
    r.text = title
    _style_run(r, 28, True, DARK, HF)
    s.notes_slide.notes_text_frame.text = "What I will say: " + notes
    slide_no[0] += 1
    tb(s, str(len(prs.slides)), 9.1, 5.3, 0.5, 0.25, size=10, color=MUTED, align="r")
    return s


def dark_slide(notes):
    s = prs.slides.add_slide(LAYOUT_BLANK)
    set_bg(s, DARK)
    s.notes_slide.notes_text_frame.text = "What I will say: " + notes
    return s


def hc(t):
    return (t, dict(bold=True, color=WHITE, fill=DARK))


def cc(t, **o):
    return (t, o)


def table(slide, rows, x, y, w, colw, size=10, row_h=0.3):
    nr, nc = len(rows), len(rows[0])
    gs = slide.shapes.add_table(nr, nc, Inches(x), Inches(y), Inches(w), Inches(row_h * nr))
    tbl = gs.table
    # remove built-in style banding look
    tblPr = tbl._tbl.tblPr
    tblPr.set("firstRow", "0")
    tblPr.set("bandRow", "0")
    tot = sum(colw)
    for i, cw in enumerate(colw):
        tbl.columns[i].width = Inches(w * cw / tot)
    for ri, row in enumerate(rows):
        tbl.rows[ri].height = Inches(row_h)
        for ci, (text, o) in enumerate(row):
            cell = tbl.cell(ri, ci)
            cell.margin_left = cell.margin_right = Inches(0.05)
            cell.margin_top = cell.margin_bottom = Inches(0.03)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE if ri == 0 else MSO_ANCHOR.TOP
            cell.fill.solid()
            cell.fill.fore_color.rgb = rgb(o.get("fill", "FFFFFF" if ri % 2 else "F7F9F8"))
            tf = cell.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            r = p.add_run()
            r.text = text
            _style_run(r, o.get("size", size), o.get("bold", False), o.get("color", TXT))
    return tbl


def bar_chart(slide, x, y, w, h, cats, vals, title, colors, fmt, axis_title):
    cd = CategoryChartData()
    cd.categories = cats
    cd.add_series("Unique network length (m)", vals)
    gf = slide.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(x), Inches(y), Inches(w), Inches(h), cd)
    ch = gf.chart
    ch.has_legend = False
    ch.has_title = True
    ch.chart_title.text_frame.text = title
    for r in ch.chart_title.text_frame.paragraphs[0].runs:
        _style_run(r, 11, False, TXT)
    plot = ch.plots[0]
    plot.gap_width = 60
    plot.vary_by_categories = False
    plot.has_data_labels = True
    dl = plot.data_labels
    dl.number_format = fmt
    dl.number_format_is_linked = False
    dl.position = XL_LABEL_POSITION.OUTSIDE_END
    dl.font.size = Pt(10)
    dl.font.name = BF
    dl.font.color.rgb = rgb(TXT)
    ser = plot.series[0]
    for i, col in enumerate(colors):
        pt = ser.points[i]
        pt.format.fill.solid()
        pt.format.fill.fore_color.rgb = rgb(col)
    ca, va = ch.category_axis, ch.value_axis
    for ax in (ca, va):
        ax.tick_labels.font.size = Pt(9)
        ax.tick_labels.font.name = BF
        ax.tick_labels.font.color.rgb = rgb(MUTED)
    va.minimum_scale = 0
    va.has_major_gridlines = True
    va.major_gridlines.format.line.color.rgb = rgb(RULE)
    va.major_gridlines.format.line.width = Pt(0.5)
    va.format.line.fill.background()
    va.has_title = True
    va.axis_title.text_frame.text = axis_title
    for r in va.axis_title.text_frame.paragraphs[0].runs:
        _style_run(r, 9, False, MUTED)
    va.tick_labels.number_format = "#,##0"
    va.tick_labels.number_format_is_linked = False
    return ch


# =============== 1 Title ===============
s = dark_slide("Good morning. My major project is about planning rural road connections for a village using satellite images and GIS data. I studied one village, Damarakunta in Siddipet district. This is a review of work in progress, so I will clearly separate what is finished and verified from what is still pending.")
tb(s, "M.Tech Major Project Review", 0.5, 0.45, 5, 0.3, 14, True, ACC)
tb(s, "GIS-Based Smart Village Infrastructure Planning and Multi-Criteria Rural Road Network Optimization Using Remote Sensing and AI",
   0.5, 0.95, 5.0, 2.4, 24, True, WHITE, HF)
tb(s, ["Pendyala Archana", "M.Tech Information Technology: AI and Robotics", "Chaitanya Bharathi Institute of Technology, Hyderabad",
       "Study area: Damarakunta, Markook Mandal, Siddipet, Telangana"], 0.5, 3.6, 5.0, 1.5, 14, False, "DCE8E2", space=4)
s.shapes[-1].text_frame.paragraphs[0].runs[0].font.bold = True
pic(s, "map_study_area.jpg", 5.75, 0.8, 3.8, 3.9, "Damarakunta study area on satellite imagery")
tb(s, "Imagery source and licence: to be confirmed", 5.75, 4.75, 3.8, 0.25, 10, False, "B8C9C1")

# =============== 2 Abstract ===============
s = content("Abstract", "Rural villages often lack a clear plan for connecting houses and public facilities to the road network. I took Damarakunta village as the study area. I combined a satellite mosaic, a village boundary, existing roads, building candidates, land cover and terrain into one planning grid. A planner then generates alternative low-cost routes and selects them into one shared network. I also test what happens when some buildings are missing from the input. The planning runs are executed and the numbers are verified for the primary run. Connectivity checks, field validation and a second village are still pending. The outputs are planning support, not construction designs.")
tb(s, "Rural road planning needs many spatial datasets together. This project builds a GIS and least-cost-path planner for Damarakunta village (18.466 km²), using satellite imagery, roads, building candidates, land cover and slope. It generates alternative routes, selects a shared network, and tests how missing building data changes the result.", 0.5, 1.1, 9, 1.2, 14)
card(s, 0.5, 2.5, 4.4, 2.1, GREENBG)
tb(s, "Completed so far", 0.7, 2.6, 4, 0.3, 16, True, MID, HF)
tb(s, ["Data integrated on a 10 m grid", "163 house and 4 facility routes generated", "C1 omission and C2 ablation runs executed"], 0.7, 3.0, 4.0, 2.0, 14, bullets=True)
card(s, 5.1, 2.5, 4.4, 2.1, AMBERBG)
tb(s, "Ongoing or pending", 5.3, 2.6, 4, 0.3, 16, True, AMBERTX, HF)
tb(s, ["Connectivity exception (one house)", "Imagery licence and data-source checks", "Field or expert validation; second village (C3)"], 5.3, 3.0, 4.0, 2.0, 14, bullets=True)

# =============== 3 Introduction ===============
s = content("Introduction", "Roads decide whether a family can reach a school or a health centre. Satellite images and GIS let us look at a whole village at once. But a good route depends on terrain, land cover, existing roads, facilities and where buildings are. An automated planner can compare many alternatives quickly. The results still need engineers and local field checks before anything is built.")
rows = [("1", "Why roads matter", "Access to schools, health care and markets"),
        ("2", "Why satellite and GIS", "One view of a whole village; layers can be combined"),
        ("3", "Why many layers", "Terrain, land cover, roads, facilities and buildings all change a route"),
        ("4", "Why automate", "Compare many alternatives quickly and consistently"),
        ("5", "Why verify", "Outputs are model results; experts and field checks are still needed")]
for i, r in enumerate(rows):
    y = 1.2 + i * 0.78
    circle(s, r[0], 0.6, y, 0.55, MID, 16)
    tb(s, r[1], 1.4, y, 2.8, 0.55, 16, True, DARK, valign="m")
    tb(s, r[2], 4.2, y, 5.3, 0.55, 14, valign="m")

# =============== 4 Problem ===============
s = content("Problem statement", "The main problem is how to plan rural road connections when the data come from many sources and are not perfect. Building information may be incomplete. Routes must respect terrain, land cover and existing roads. And if we plan each route alone we can count the same road several times, so we should plan the routes together.")
card(s, 0.5, 1.15, 9, 1.0, DARK)
tb(s, "How can alternative rural road connections be generated and combined into a shared network from multi-source GIS data, when building information may be incomplete?", 0.7, 1.2, 8.6, 0.9, 16, True, WHITE, valign="m")
pts = [("Many datasets", "Imagery, roads, facilities, land cover and terrain must be combined"),
       ("Uncertain buildings", "Candidate buildings are model output, not a verified census"),
       ("Many alternatives", "Routes must be compared using terrain, land cover and constraints"),
       ("Shared segments", "Routes that share road should not be costed separately")]
for i, p in enumerate(pts):
    x, y = 0.5 + (i % 2) * 4.6, 2.45 + (i // 2) * 1.35
    card(s, x, y, 4.4, 1.2)
    tb(s, p[0], x + 0.2, y + 0.12, 4.0, 0.35, 16, True, MID, HF)
    tb(s, p[1], x + 0.2, y + 0.52, 4.0, 0.6, 14)

# =============== 5 Objectives ===============
s = content("Objectives and current status", "I have four objectives. The first two, data preparation and route generation, are done for Damarakunta. The third, shared network selection, has been executed and the numbers for the primary run are verified. The fourth, the effect of building omissions and method choices, is executed, but final consolidation and some checks are pending.")
objs = [("Prepare and integrate GIS and remote-sensing data for Damarakunta", "Achieved", MID),
        ("Generate connections from target buildings and priority facilities to the road network", "Achieved (163 houses, 4 facilities)", MID),
        ("Select and compare a shared network using route costs and marginal network cost", "Executed; primary run verified", MID),
        ("Evaluate effect of building omissions and planner choices", "Executed; final checks pending", ACC)]
for i, r in enumerate(objs):
    y = 1.2 + i * 1.0
    card(s, 0.5, y, 9, 0.85)
    tb(s, "O%d" % (i + 1), 0.65, y, 0.6, 0.85, 20, True, MID, HF, valign="m")
    tb(s, r[0], 1.3, y, 5.3, 0.85, 14, valign="m")
    chip(s, r[1], 6.75, y + 0.28, 2.65, r[2])

# =============== 6 Mini vs major ===============
s = content("Mini-project versus major project", "My mini-project explored image segmentation on the public LoveDA benchmark with a DINOv2 model. Those results belong only to the mini-project. LoveDA is not Damarakunta data. The major project takes the next step: it uses GIS data for one real village, plans roads, and studies how uncertain building data affect the plan.")
R = [[hc("Aspect"), hc("Mini-project"), hc("Major project")],
     [cc("Purpose", bold=True), cc("Explore remote-sensing image segmentation"), cc("Rural infrastructure and road-network planning")],
     [cc("Study data", bold=True), cc("LoveDA benchmark (5,987 images)"), cc("Damarakunta village GIS layers and imagery")],
     [cc("Methods", bold=True), cc("StrongDINOv2Seg: DINOv2-base, FPN + ASPP decoder, CE + Dice + Boundary loss"), cc("GIS cost grid, least-cost routes, shared-network selection")],
     [cc("Output", bold=True), cc("Segmentation maps; best validation mIoU 53.80%, mDice 68.91% (epoch 4)"), cc("Candidate routes, selected network, C1 and C2 results")],
     [cc("Research focus", bold=True), cc("Segmentation performance"), cc("Effect of building-data uncertainty; shared-network planning")]]
table(s, R, 0.5, 1.1, 9, [1.4, 3.8, 3.8], size=12, row_h=0.45)
card(s, 0.5, 4.3, 9, 0.8, AMBERBG)
tb(s, "Mini-project numbers are LoveDA validation results only (10 epochs, no test set recorded). They are not Damarakunta results.", 0.7, 4.35, 8.6, 0.7, 14, True, "6B4A00", valign="m")

# =============== 7-8 Literature ===============
lit_hdr = [hc(t) for t in ["No.", "Author, year", "Topic", "Method", "Main finding", "Limitation or gap", "Relevance"]]
lit_w = [0.35, 1.0, 1.9, 1.35, 1.6, 1.5, 1.3]
s = content("Literature survey (1 of 2): perception", "These papers cover building and road extraction from satellite images. They show good progress on footprints and on road continuity. But they mostly score the map, not what happens to a road plan when a building is missed. That is the gap I look at. Findings here are from abstracts and summaries, not a full reading.")
table(s, [lit_hdr,
          [cc("1"), cc("Ding et al., 2022"), cc("Adversarial Shape Learning for Building Extraction in VHR Remote Sensing Images"), cc("Adversarial shape learning with a shape regularizer"), cc("Improves building footprint geometry"), cc("Does not test road-planning effects"), cc("Quality of building targets")],
          [cc("2"), cc("Li et al., 2024"), cc("A Review of Building Extraction From Remote Sensing Imagery"), cc("Review (optical and SAR)"), cc("Maps geometric and semantic challenges"), cc("Does not name a best model for rural India"), cc("Frames the building stage")],
          [cc("3"), cc("Hu et al., 2023"), cc("LGNet: Location-Guided Network for Road Extraction From Satellite Images"), cc("Road-location task plus guided decoder"), cc("Improves road continuity"), cc("Needs vector graph checks"), cc("Road connectivity matters")],
          [cc("4"), cc("Xu et al., 2023"), cc("Road Extraction With Satellite Images and Partial Road Maps"), cc("Partial-to-Complete network"), cc("Completes incomplete road maps"), cc("No house connection; no rural India test"), cc("Like our incomplete road layer")]],
      0.5, 1.1, 9, lit_w, size=11, row_h=0.5)
tb(s, "Full citations on the References slide.", 0.5, 4.95, 6, 0.25, 10, color=MUTED)

s = content("Literature survey (2 of 2): planning", "These papers are about route planning, multi-criteria analysis and uncertainty. Path planning and multi-criteria GIS are mature tools, so I use them as they are and do not claim them as new. The papers do not connect uncertain building input to the final shared road network, which is the focus of my C1 and C2 experiments.")
table(s, [lit_hdr,
          [cc("5"), cc("Zhu et al., 2025"), cc("A Multi-Objective Path Planning Framework in Off-Road Environments Based on Deep Reinforcement Learning"), cc("Actor-critic deep RL on a traversability map"), cc("Terrain-aware multi-objective path cost"), cc("Single vehicle path, not a network"), cc("Terrain-aware cost idea")],
          [cc("6"), cc("Wang et al., 2024"), cc("A Practical Urban Distribution Network Planning Method With Geographic Information System"), cc("GIS street graph, shortest paths, optimisation"), cc("Path distances beat straight-line distances"), cc("Urban power network, not rural roads"), cc("Supports path-based network planning")],
          [cc("7"), cc("Malczewski, 2006"), cc("GIS-based multicriteria decision analysis: a survey of the literature"), cc("Literature survey"), cc("Reviews multi-criteria methods in GIS"), cc("General survey; no rural roads"), cc("Basis for multi-criteria cost")],
          [cc("8"), cc("Yang et al., 2025"), cc("UGD-DLinkNet: Enhanced Network for Occluded Road Extraction Using Attention and Uncertainty Estimation"), cc("Attention, Monte Carlo dropout, distillation"), cc("Uses uncertainty for occluded roads"), cc("Not propagated into planning"), cc("Motivates uncertainty study")]],
      0.5, 1.1, 9, lit_w, size=11, row_h=0.5)

# =============== 9 Research gap ===============
s = content("Research gap and project questions", "I am not claiming that A star, least-cost path, multi-criteria analysis or facility prioritisation are new. They are established tools. My questions are narrower. C1: how do missing buildings change the plan. C2: does selecting routes together with shared-edge credit reduce duplicated network length compared with independent routing. C3: transfer to other villages, which I have not tested yet.")
items = [("C1", "Building-data uncertainty", "How can missing building targets affect road-planning decisions?", "Executed", MID),
         ("C2", "Shared-network planning", "Does generate-and-select with shared-edge credit reduce duplicated network cost compared with independent routing?", "Executed", MID),
         ("C3", "Transfer to other villages", "Future evaluation only. Not an established contribution.", "Pending", WARN)]
for i, it in enumerate(items):
    y = 1.2 + i * 1.15
    card(s, 0.5, y, 9, 1.0)
    tb(s, it[0], 0.65, y, 0.8, 1.0, 26, True, it[4], HF, valign="m")
    tb(s, it[1], 1.5, y + 0.1, 5.6, 0.35, 16, True, DARK)
    tb(s, it[2], 1.5, y + 0.47, 6.3, 0.5, 13)
    chip(s, it[3], 8.1, y + 0.35, 1.2, it[4])
tb(s, "Not claimed as new: A*, least-cost path, AHP / multi-criteria analysis, DINOv2, FPN, ASPP, facility prioritisation.", 0.5, 4.75, 9, 0.4, 12, color=MUTED)

# =============== 10 Study area ===============
s = content("Study area: Damarakunta village", "The study area is Damarakunta, in Markook Mandal, Siddipet District, Telangana. The boundary layer in my project covers about 18.466 square kilometres. The map shows the boundary, the satellite imagery, existing roads and model-detected building areas. A state-level location map is not yet in my project files, so I have not drawn one.")
pic(s, "map_study_area.jpg", 0.5, 1.05, 5.6, 4.1, "Study area overview map")
card(s, 6.3, 1.1, 3.2, 3.95)
tb(s, "Location", 6.5, 1.2, 2.8, 0.3, 16, True, MID, HF)
tb(s, ["Telangana, India", "Siddipet District", "Markook Mandal", "Damarakunta village"], 6.5, 1.55, 2.8, 1.5, 14, bullets=True)
tb(s, "18.466 km²", 6.5, 3.1, 2.8, 0.5, 28, True, DARK, HF)
tb(s, "current project boundary layer (EPSG:32644)", 6.5, 3.65, 2.8, 0.45, 12, color=MUTED)
tb(s, "State and district context map: not in project files yet. Imagery source and licence: to be confirmed.", 6.5, 4.2, 2.8, 0.8, 11, color=WARN)

# =============== 11-12 Dataset inventory ===============
ds_hdr = [hc(t) for t in ["Dataset", "Source", "Local file", "Resolution / count", "Purpose", "Limitation / status"]]
ds_w = [1.2, 1.3, 2.05, 1.4, 1.4, 1.65]
s = content("Dataset inventory (1 of 2)", "These are the main input layers. For each one I list the file, the size, and what is still unverified. The satellite mosaic is the most important open point: its provider details and licence still need confirming. The boundary matches the stored TGRAC response, but that does not prove legal authority. The building candidates are model detections, not a census.")
table(s, [ds_hdr,
          [cc("A. Satellite mosaic", bold=True), cc("Esri imagery export (provenance to confirm)"), cc("aligned/damarakunta_esri_highres_mosaic_0p6m.tif"), cc("11,296 × 7,171 px, RGB, 0.6 m"), cc("Visual review, building and road context"), cc("Capture date and licence: to be confirmed")],
          [cc("B. Village boundary", bold=True), cc("TGRAC boundary service"), cc("study_area/damarakunta_boundary.gpkg"), cc("EPSG:32644, 18.466 km²"), cc("Study area, clipping"), cc("Equals stored TGRAC response; legal status not established")],
          [cc("C. Road network", bold=True), cc("TGRAC"), cc("reference/tgrac_road_network.gpkg"), cc("43 features, 93.5 km"), cc("Existing-road goals"), cc("44.7% of length outside boundary; completeness unverified")],
          [cc("D. Building candidates", bold=True), cc("Project model output"), cc("results/v8_instances/buildings_v8_full.gpkg"), cc("278 candidates; 165 footprints; 163 routed"), cc("Target buildings"), cc("Not a verified census of houses")],
          [cc("E. Land cover", bold=True), cc("ESA WorldCover"), cc("aligned/damarakunta_worldcover_10m.tif"), cc("10 m, 679 × 432 cells"), cc("Land-cover route cost"), cc("2021 per project notes; version to confirm")]],
      0.5, 1.1, 9, ds_w, size=10, row_h=0.55)
tb(s, "WorldCover: esa-worldcover.org/en/data-access", 0.5, 4.95, 6, 0.25, 10, color=MUTED)

s = content("Dataset inventory (2 of 2)", "The rest are the elevation data, derived layers, parcels, facilities and the LoveDA benchmark. The slope comes from a roughly 30 metre DEM resampled to 10 metres, so it does not carry true 10 metre detail. Cost values are model units, not rupees. LoveDA is used only in the mini-project and is not Damarakunta data. Parcel counts do not show ownership or legal access.")
table(s, [ds_hdr,
          [cc("F. DEM", bold=True), cc("Copernicus DEM per project plan; project notes also list SRTM"), cc("raw/dem/damarakunta_dem_clip.tif"), cc("~30 m"), cc("Slope for route cost"), cc("Exact product: to be confirmed; not true 10 m detail")],
          [cc("G. Slope, cost, prohibited mask", bold=True), cc("Derived by project scripts"), cc("aligned/…_slope_10m, …_cost_surface_10m, …_prohibited_mask_10m.tif"), cc("10 m, 679 × 432"), cc("Terrain difficulty, cost, excluded cells"), cc("Model units, not rupees")],
          [cc("H. Cadastral parcels", bold=True), cc("Project parcel layer"), cc("reference/damarakunta_cadastral_valid.gpkg"), cc("794 parcels"), cc("Parcel-crossing counts"), cc("No ownership or legal-access claim")],
          [cc("I. Facilities", bold=True), cc("TGRAC facility and school records"), cc("reference/damarakunta_priority_facilities.gpkg; school_compounds*.gpkg"), cc("4 priority facilities"), cc("Service destinations"), cc("Completeness and identity unverified")],
          [cc("J. LoveDA (mini-project only)", bold=True), cc("Wang et al.; doi:10.5281/zenodo.5706578"), cc("Not in the Damarakunta folders"), cc("5,987 images (as reported)"), cc("Mini-project segmentation"), cc("Not Damarakunta data")]],
      0.5, 1.1, 9, ds_w, size=10, row_h=0.55)
tb(s, "DEM: dataspace.copernicus.eu (COP-DEM collection)", 0.5, 4.95, 6, 0.25, 10, color=MUTED)

# =============== 13 Data prep ===============
s = content("Data preparation and GIS integration", "Before any routing, the data must be made consistent. I check the data and metadata, put every layer in the same coordinate system, clip to the village boundary, prepare targets, roads, facilities, land cover and slope, and then build a 10 metre cost grid with excluded cells. The result is only as good as the input data.")
steps = ["Collect input data", "Check quality and metadata", "Align coordinate systems", "Clip to boundary", "Prepare targets, roads, facilities, land cover, slope", "Build cost grid and prohibited mask", "Analysis-ready GIS inputs"]
w, gap = 1.18, 0.13
for i, t in enumerate(steps):
    x = 0.5 + i * (w + gap)
    last = i == 6
    rect(s, x, 1.2, w, 1.45, MID if last else LIGHT, RULE)
    tb(s, str(i + 1), x, 1.25, w, 0.3, 14, True, WHITE if last else MID, align="c")
    tb(s, t, x + 0.05, 1.55, w - 0.1, 1.05, 11, False, WHITE if last else TXT, align="c", valign="m")
    if i < 6:
        tb(s, "›", x + w - 0.02, 1.7, gap + 0.04, 0.4, 16, True, MID, align="c")
pic(s, "fig_slope_cost.png", 0.5, 2.85, 5.6, 2.3, "Slope and cost surface rendered from project rasters")
card(s, 6.3, 2.9, 3.2, 2.2)
tb(s, ["Grid: 432 × 679 cells, 10 m, EPSG:32644", "Cost = land cover + slope term", "Blocked: water, prohibited, slope above 25°", "Output quality depends on input quality"], 6.45, 3.0, 2.95, 2.0, 12, bullets=True)

# =============== 14 Architecture ===============
s = content("Proposed system architecture", "The system is a GIS and graph-routing pipeline, not a deep-learning model. Inputs are cleaned and aligned, targets are prepared, a cost surface is built, and a routing graph is made from the grid. Stage A generates candidate routes. Stage B selects them into one shared network. At the end we evaluate connectivity, length and cost, and run the C1 and C2 experiments.")
mods = [("1 Input data", "Imagery, boundary, roads, buildings, facilities, land cover, DEM, parcels"),
        ("2 Preprocessing", "CRS alignment, clipping, raster and vector preparation, quality checks"),
        ("3 Target preparation", "Filter buildings; define facilities and road connection points"),
        ("4 Cost surface", "Land-cover and slope cost, prohibited mask, movement-cost grid"),
        ("5 Road graph", "Passable grid cells, movement rules, no routing through blocked cells"),
        ("6 Stage A", "Generate alternative candidate routes per target"),
        ("7 Stage B", "Select routes by marginal cost with shared-edge credit"),
        ("8 Evaluation", "Connectivity, length, cost; C1 omission, C2 ablation; maps")]
mw, mh = 2.1, 1.45
for i, m in enumerate(mods):
    row, col = divmod(i, 4)
    x, y = 0.5 + col * (mw + 0.2), 1.15 + row * (mh + 0.55)
    hl = i in (5, 6)
    rect(s, x, y, mw, mh, MID if hl else LIGHT, MID if hl else RULE)
    tb(s, m[0], x + 0.1, y + 0.08, mw - 0.2, 0.3, 14, True, WHITE if hl else DARK, HF)
    tb(s, m[1], x + 0.1, y + 0.42, mw - 0.2, mh - 0.5, 11, False, WHITE if hl else TXT)
    if col < 3:
        a = rect(s, x + mw + 0.02, y + mh / 2 - 0.1, 0.16, 0.2, MUTED, MUTED, MSO_SHAPE.RIGHT_ARROW)
tb(s, "Planner: graph and least-cost-path heuristic on an 8-connected 10 m grid. Not claimed to be globally optimal.", 0.5, 4.85, 9, 0.3, 12, color=MUTED)

# =============== 15 Execution flow ===============
s = content("Step-by-step execution flow", "This is the order in which the work runs, from loading the data to the final report. Each step has an input and an output. Steps one to ten have been run for Damarakunta. Steps eleven and twelve are partly done, because final consolidation and the connectivity checks are still pending.")
st = [("Load project data", "files to layers"), ("Check CRS and quality", "validated inputs"), ("Prepare targets", "163 houses, 4 facilities"),
      ("Prepare land cover, slope, mask", "10 m rasters"), ("Generate cost surface", "cost grid"), ("Build routing graph", "grid graph"),
      ("Generate candidate routes", "K = 3 per target"), ("Select shared network", "selected routes"), ("Evaluate feasibility and cost", "length, connectivity"),
      ("Run C1 and C2", "result tables"), ("Export maps and tables", "GIS layers, figures"), ("Final checks and report", "pending")]
for i, t in enumerate(st):
    col, row = i % 4, i // 4
    x, y = 0.5 + col * 2.28, 1.15 + row * 1.35
    pend = i == 11
    rect(s, x, y, 2.1, 1.15, AMBERBG if pend else LIGHT, RULE)
    circle(s, str(i + 1), x + 0.08, y + 0.08, 0.36, ACC if pend else MID, 12)
    tb(s, t[0], x + 0.5, y + 0.05, 1.55, 0.55, 12, True, DARK, valign="m")
    tb(s, "Output: " + t[1], x + 0.12, y + 0.68, 1.9, 0.4, 11, color=MUTED)

# =============== 16 Tools ===============
s = content("Implementation and tools", "Everything runs in Python in a project virtual environment. The versions shown come from the installed packages in that environment. Data are stored as GeoPackage and GeoTIFF. The planner is one Python script, and I recorded its file hash in every run so that I know the planner was not changed between runs.")
L = [("Language", "Python 3.10"),
     ("Raster and vector", "rasterio 1.4.4, geopandas 1.1.4, shapely 2.1.2, pyogrio 0.13.0, pyproj 3.7.1, fiona 1.10.1"),
     ("Numerics and graphs", "numpy 2.2.6, scipy 1.15.3, networkx 3.4.2, pandas 2.3.3"),
     ("Imaging and plots", "scikit-image 0.25.2, OpenCV-python 5.0.0.93, matplotlib 3.10.9"),
     ("Data formats", "GeoPackage (.gpkg), GeoTIFF (.tif), CSV, JSON"),
     ("Planner", "plan_network_v2.py (heap-based search; SHA-256 d00ea920…ef70a4)")]
for i, r in enumerate(L):
    y = 1.15 + i * 0.66
    card(s, 0.5, y, 9, 0.56)
    tb(s, r[0], 0.7, y, 2.3, 0.56, 14, True, MID, valign="m")
    tb(s, r[1], 3.0, y, 6.3, 0.56, 13, valign="m")

# =============== 17 Outputs ===============
s = content("Actual project outputs", "These are real exports from my project folders. Top left: building areas and existing roads in the main settlement. Top right: proposed network on the village map. Bottom left: connectivity audit, where cyan marks route geometry and white dots are road endpoints. Bottom right: slope and cost surface. Context imagery in some maps is coarse, and the imagery licence is still being confirmed.")
cells = [("map_buildings_roads.jpg", "Building candidates and existing roads"),
         ("map_proposed_network.jpg", "Planner output (model result, not verified roads)"),
         ("map_connectivity_audit.jpg", "Connectivity audit: endpoints and bridge candidates"),
         ("fig_slope_cost.png", "Slope and cost surface (rendered from project rasters)")]
for i, (f, cap) in enumerate(cells):
    x, y = 0.5 + (i % 2) * 4.6, 1.1 + (i // 2) * 2.05
    pic(s, f, x, y, 4.4, 1.7, cap)
    tb(s, cap, x, y + 1.73, 4.4, 0.25, 10, color=MUTED)

# =============== 18 C1 ===============
s = content("C1: Building-data uncertainty", "The question is: what happens to the road plan if some buildings are missing from the input? I removed buildings in controlled steps and re-ran the planner. The baseline routes 163 houses with 5,138 metres of unique network. Removing the smallest 25 percent leaves 122 houses and 3,891 metres. The network shrinks because fewer houses are served. So the comparable number is length per served house, which stays near 32 metres and rises to about 36 metres when merged buildings are removed. These omissions are synthetic tests. They do not measure real building-detection error.")
bar_chart(s, 0.5, 1.1, 5.2, 3.5, ["Baseline (163)", "Omit 10% smallest (146)", "Omit 25% smallest (122)", "Omit merged (101)"],
          [5137.7, 4717.5, 3890.6, 3627.9], "Unique network length (m); targets routed in brackets", [MUTED, MID, MID, MID], "#,##0", "metres")
tb(s, "Config: S2, K=3, 2 passes, slope limit 25°, building penalty ×4. Source: c1_scenario_comparison.csv", 0.5, 4.65, 5.2, 0.45, 10, color=MUTED)
tb(s, ["Question: how does omitting targets change the plan?", "Fewer targets give a shorter network and no failed routes", "Length per served house: 31.5 m baseline; 31.9, 32.3, 35.9 m for the omissions", "Synthetic omissions, not measured detection error"], 5.9, 1.2, 3.6, 3.8, 13, bullets=True)

# =============== 19 C2 ===============
s = content("C2: Shared-network planning", "Independent routing plans each house separately and counts each road each time. Shared-network planning gives credit when a new route can use road that is already selected. The measure is marginal unique network cost, the extra network a new route needs. On the same 163 houses, the independent routes need 6,755 metres of unique network and the shared plan needs 5,138 metres, a reduction of about 24 percent. This is a heuristic and is not claimed to be globally optimal. These lengths are model grid lengths, not construction costs.")
bar_chart(s, 0.5, 1.1, 4.0, 3.4, ["Independent least-cost routes", "Shared-network plan (K=3, 2 passes)"], [6755.4, 5137.7],
          "Unique network length, 163 houses (m)", [BLUE, MID], "#,##0.0", "metres")
tb(s, "Config: S2, slope 25°, cost C0. Source: evaluation_summary.json", 0.5, 4.55, 4.0, 0.4, 10, color=MUTED)
pic(s, "map_independent_vs_network_inset.jpg", 4.7, 1.1, 4.8, 2.6, "Independent versus shared-network routes, inset A")
tb(s, ["Reduction 1,617.7 m (23.9%); heuristic; 0 failed routes", "Ablation: K1/P0 5,148.0 m vs K3/P2 5,137.7 m (0.2% gap)", "Connectivity: 162 of 163 houses reach the main road component"], 4.7, 3.8, 4.8, 1.4, 12, bullets=True)

# =============== 20 Results ===============
s = content("Actual numerical results", "Every number here was read from the saved output files. The status column is honest. Primary-run C1 and C2 numbers are verified from the CSV and JSON files. The no-building-penalty P3 row is provisional because the P3 baseline reproduction run is still pending. The 5,231.5 metre figure is the roads-only reference baseline, not the main planner, and it gives 22.6 percent. The main planner gives 23.9 percent.")
V = ("Verified", dict(bold=True, color=MID)); P = ("Provisional", dict(bold=True, color=AMBERTX))
table(s, [[hc(t) for t in ["Experiment", "Configuration", "Baseline", "Method", "Change", "N", "Source file", "Status"]],
          [cc("C2 shared vs independent"), cc("S2, K3 P2, slope 25°, C0"), cc("6,755.4 m"), cc("5,137.7 m"), cc("−1,617.7 m (−23.9%)"), cc("163"), cc("evaluation_summary.json"), V],
          [cc("C2 vs roads-only reference"), cc("same run; reference baseline"), cc("6,755.4 m"), cc("5,231.5 m"), cc("−1,523.8 m (−22.6%)"), cc("163"), cc("evaluation_summary.json"), V],
          [cc("C2 ablation K1 P0 vs K3 P2"), cc("5 runs, same inputs"), cc("5,148.0 m"), cc("5,137.7 m"), cc("−10.3 m (−0.2%)"), cc("163"), cc("c2_ablation_summary.csv"), V],
          [cc("C1 omit 25% smallest"), cc("primary, building penalty ×4"), cc("5,137.7 m"), cc("3,890.6 m"), cc("−24.3%; 122 routed"), cc("163 → 122"), cc("c1_scenario_comparison.csv"), V],
          [cc("C1 omit merged candidates"), cc("primary, building penalty ×4"), cc("5,137.7 m"), cc("3,627.9 m"), cc("−29.4%; 101 routed"), cc("163 → 101"), cc("c1_scenario_comparison.csv"), V],
          [cc("C1 omit merged candidates"), cc("P3, no building penalty"), cc("4,761.7 m"), cc("3,425.7 m"), cc("−28.1%; 101 routed"), cc("163 → 101"), cc("P3 c1_scenario_comparison.csv"), P]],
      0.5, 1.1, 9, [1.4, 1.3, 0.8, 0.8, 1.3, 0.75, 1.95, 0.85], size=10, row_h=0.42)
tb(s, "Lengths are unique network length in metres on the 10 m grid. Costs are model units, not rupees. Earlier prototype runs (for example 1,506.1 m, 9 clusters) are superseded and not shown as results.", 0.5, 4.5, 9, 0.6, 11, color=MUTED)

# =============== 21 Status ===============
s = content("Current project status", "This table is the honest status. The core planner experiments are executed. The boundary check passed for the stored boundary. The connectivity investigation is ongoing: one house, C0002, attaches to a small road component that is separate from the main road cells, and I need to check whether the road leaves and re-enters the boundary. Transfer to other villages is not established.")
OK = lambda t: cc(t, bold=True, color=MID); WIP = lambda t: cc(t, bold=True, color=AMBERTX); NO = lambda t: cc(t, bold=True, color=WARN)
table(s, [[hc(t) for t in ["Component", "Status", "Evidence", "Next action"]],
          [cc("Core GIS and route planning"), OK("Executed"), cc("163/163 houses and 4/4 facilities routed, 0 failed"), cc("Final result consolidation")],
          [cc("C1 omission experiments"), OK("Executed; primary verified"), cc("c1_scenario_comparison.csv; 49 report checks pass"), cc("P3 baseline reproduction")],
          [cc("C2 shared-network ablation"), OK("Executed; verified"), cc("c2_ablation_summary.csv; control identical"), cc("Optional geometry comparison")],
          [cc("Boundary comparison"), OK("Passed"), cc("Saved copy equals stored TGRAC response"), cc("Record query date")],
          [cc("Connectivity investigation"), WIP("Ongoing"), cc("12 road components; house C0002 on a 5-cell component"), cc("Check boundary exit and re-entry")],
          [cc("Connector visual review"), WIP("Pending"), cc("Route connectors need visual review"), cc("Complete review")],
          [cc("C3 transfer to other villages"), NO("Not established"), cc("No second village run"), cc("Needs approval and data")],
          [cc("Report, maps, citation audit"), WIP("Pending"), cc("Maps partly final"), cc("Finish audit")]],
      0.5, 1.1, 9, [2.1, 1.7, 3.2, 2.0], size=11, row_h=0.42)

# =============== 22 Limitations ===============
s = content("Limitations and future work", "These are the things I know are not finished or are not supported by evidence. The imagery licence, the completeness of roads and facilities, and the disconnected road component need checking. Final numbers need confirmation. Nothing here has been checked in the field, so I do not claim the roads are ready to build.")
L = ["Confirm satellite mosaic source, date and licence", "Check road and facility completeness and currency", "Investigate disconnected road components", "Finish visual review of route connectors",
     "Confirm final C1 and C2 numbers and settings", "Finish report, literature and citation audit", "Second-village transfer (C3) only if data and time allow", "Field or expert validation before any real-world claim"]
for i, t in enumerate(L):
    x, y = 0.5 + (i % 2) * 4.6, 1.15 + (i // 2) * 0.98
    card(s, x, y, 4.4, 0.85)
    tb(s, str(i + 1), x + 0.12, y, 0.4, 0.85, 18, True, ACC, HF, valign="m")
    tb(s, t, x + 0.55, y, 3.75, 0.85, 13, valign="m")

# =============== 23 Conclusion ===============
s = content("Conclusion", "To conclude. I integrated imagery, boundary, roads, building candidates, land cover and terrain for Damarakunta. I implemented a graph-based planner that generates and selects shared routes. My C1 and C2 experiments investigate building uncertainty and shared networks. The primary-run numbers are verified. Connectivity, licence checks, validation and transfer are still to do. I do not claim the routes are ready to build or optimal.")
L = [("Data integrated", "Imagery, boundary, roads, buildings, land cover, slope on a 10 m grid"),
     ("System built", "GIS cost grid with a generate-and-select route planner"),
     ("Experiments run", "C1 building omissions, C2 shared-network ablation"),
     ("Confirmed", "Primary run: 163 houses, 5,137.7 m shared vs 6,755.4 m independent"),
     ("Still to do", "Connectivity checks, licence checks, validation, transfer (C3)")]
for i, r in enumerate(L):
    y = 1.15 + i * 0.78
    card(s, 0.5, y, 9, 0.68, AMBERBG if i == 4 else LIGHT)
    tb(s, r[0], 0.7, y, 2.2, 0.68, 15, True, AMBERTX if i == 4 else MID, HF, valign="m")
    tb(s, r[1], 2.9, y, 6.4, 0.68, 13, valign="m")

# =============== 24 References ===============
s = content("References", "These are the references used on the slides. The IEEE items were checked against their DOI records in my literature verification file. Full-text reading is still pending for some. The dataset links are the official pages.")
refs = ['[1] L. Ding et al., "Adversarial Shape Learning for Building Extraction in VHR Remote Sensing Images," IEEE Trans. Image Process., 2022, doi:10.1109/TIP.2021.3134455.',
        '[2] Q. Li et al., "A Review of Building Extraction From Remote Sensing Imagery," IEEE Trans. Geosci. Remote Sens., 2024, doi:10.1109/TGRS.2024.3369723.',
        '[3] J. Hu et al., "LGNet: Location-Guided Network for Road Extraction From Satellite Images," IEEE TGRS, 2023, doi:10.1109/TGRS.2023.3305031.',
        '[4] Q. Xu et al., "Road Extraction With Satellite Images and Partial Road Maps," IEEE TGRS, 2023, doi:10.1109/TGRS.2023.3261332.',
        '[5] L. Zhu et al., "A Multi-Objective Path Planning Framework in Off-Road Environments Based on Deep Reinforcement Learning," IEEE Trans. Intell. Transp. Syst., 2025, doi:10.1109/TITS.2025.3589586.',
        '[6] Z. Wang et al., "A Practical Urban Distribution Network Planning Method With Geographic Information System," IEEE Trans. Power Syst., 2024, doi:10.1109/TPWRS.2024.3384534.',
        '[7] J. Malczewski, "GIS-based multicriteria decision analysis: a survey of the literature," Int. J. Geogr. Inf. Sci., 2006, doi:10.1080/13658810600661508.',
        '[8] P. Yang et al., "UGD-DLinkNet: An Enhanced Network for Occluded Road Extraction Using Attention Mechanisms and Uncertainty Estimation," IEEE JSTARS, 2025, doi:10.1109/JSTARS.2025.3608007.',
        '[9] J. Wang et al., "LoveDA: A Remote Sensing Land-Cover Dataset for Domain Adaptive Semantic Segmentation," NeurIPS Datasets and Benchmarks, 2021, arXiv:2110.08733; data doi:10.5281/zenodo.5706578.',
        '[10] ESA WorldCover: esa-worldcover.org/en/data-access.   [11] Copernicus DEM (COP-DEM): dataspace.copernicus.eu.']
tb(s, refs, 0.5, 1.1, 9, 4.1, 10, space=4)

# =============== 25 Thank you ===============
s = dark_slide("Thank you. I am happy to take questions. If asked, remember: results are planning support only, the primary-run numbers are verified, and field validation and transfer to other villages are future work.")
tb(s, "Thank you", 0.5, 1.6, 9, 1.0, 44, True, WHITE, HF, align="c")
tb(s, "Questions and suggestions are welcome", 0.5, 2.7, 9, 0.5, 20, False, "DCE8E2", align="c")
tb(s, "Pendyala Archana  |  M.Tech IT (AI and Robotics)  |  CBIT Hyderabad", 0.5, 4.4, 9, 0.4, 14, False, ACC, align="c")

prs.core_properties.author = "Pendyala Archana"
prs.core_properties.title = "M.Tech Major Project Review - Smart Village Road Network Planning"
prs.save(OUT)
print("saved", OUT, len(prs.slides), "slides")
