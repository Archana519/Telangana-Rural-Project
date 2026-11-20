"""Build paper_ieee/IEEE_Journal_Manuscript.docx (IEEE Transactions-style two-column Word layout).
Run: python paper_ieee/build_ieee_docx.py   then   python paper_ieee/verify_ieee_numbers.py
All numbers are copied from the verified ERIS manuscript / result files; verify_ieee_numbers.py re-checks them.
"""
import re, sys
from pathlib import Path
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.text import WD_ALIGN_PARAGRAPH as AL
from docx.shared import Inches, Pt
sys.path.insert(0, str(Path(__file__).resolve().parent))
from ieee_lib import *

H = Path(__file__).resolve().parent
FIG = H / "figures"
HAVE = lambda fn: (Path(__file__).resolve().parent / "figures" / fn).exists()
CR = "(Basemap imagery: Esri, Maxar, Earthstar Geographics, and the GIS User Community)."
doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Inches(8.5), Inches(11)
sec.left_margin = sec.right_margin = Inches(0.625); sec.top_margin = Inches(0.75); sec.bottom_margin = Inches(1.0)
st = doc.styles["Normal"]; st.font.name = FONT; st.font.size = Pt(10)

# ------------------------------------------------------------------ references (parsed from the verified bib)
BIB = (H.parent / "paper_eris" / "references.bib").read_text(encoding="utf-8")
ENT = {}
for m in re.finditer(r"@(\w+)\{([^,]+),(.*?)\n\}", BIB, re.S):
    f = {}
    for k, v in re.findall(r"(\w+)\s*=\s*(\{(?:[^{}]|\{[^{}]*\})*\}|\d+)", m.group(3)): f[k] = v.strip("{}") if v.startswith("{") else v
    f["_type"] = m.group(1); ENT[m.group(2)] = f
def tex(s):
    s = re.sub(r"\{\\'(\w)\}", lambda m: {"e": "é", "a": "á", "o": "ó"}.get(m.group(1), m.group(1)), s)
    s = s.replace("{\\'e}", "é").replace("\\&", "&").replace("--", "–").replace("~", " ").replace("\\url{", "").replace("{", "").replace("}", "").replace("\\", "")
    return s.strip()
def authors(a):
    a = a.replace("\n", " ")
    if not " and " in a and "," not in a: return tex(a)
    out = []
    for p in re.split(r"\s+and\s+", a):
        if p.strip() == "others": out.append("et al."); continue
        if "," in p:
            last, first = [x.strip() for x in p.split(",", 1)]
            ini = " ".join(w[0] + "." for w in re.split(r"[\s-]+", tex(first)) if w and w[0].isalpha()) if first else ""
            out.append((ini + " " + tex(last)).strip())
        else: out.append(tex(p))
    if len(out) > 6: out = out[:1] + ["et al."]; return " ".join(out[:1]) + " et al."
    return ", ".join(out[:-1]) + (", and " if len(out) > 2 else " and ") + out[-1] if len(out) > 1 else out[0]
def ref_text(e):
    t = e["_type"]; au = authors(e.get("author", "")); ti = tex(e.get("title", "")); yr = e.get("year", "")
    doi = f", doi: {e['doi']}" if "doi" in e else ""
    if t == "article":
        vol = f", vol. {e['volume']}" if "volume" in e else ""; no = f", no. {e['number']}" if "number" in e else ""
        pg = f", pp. {tex(e['pages'])}" if "pages" in e else (f", Art. no. {e['articleno']}" if "articleno" in e else "")
        return f'{au}, "{ti}," *{tex(e.get("journal",""))}*{vol}{no}{pg}, {yr}{doi}.'
    if t == "inproceedings":
        pg = f", pp. {tex(e['pages'])}" if "pages" in e else (f", Art. no. {e['articleno']}" if "articleno" in e else "")
        return f'{au}, "{ti}," in *{tex(e.get("booktitle",""))}*, {yr}{pg}{doi}.'
    if t == "book":
        s = f", ser. {tex(e['series'])}, vol. {e['volume']}" if "series" in e else ""
        return f'{au}, *{ti}*{s}. {tex(e.get("address",""))}: {tex(e.get("publisher",""))}, {yr}.'
    note = tex(e.get("note", "")); url = e.get("url", "")
    return f'{au}, "{ti}," {yr}. {note + ". " if note else ""}{("[Online]. Available: " + url) if url else ""}{doi}'.strip()

ORDER = []
def cite(keys):
    ks = [k.strip() for k in keys.split(",")]
    for k in ks:
        assert k in ENT, k
        if k not in ORDER: ORDER.append(k)
    nums = sorted(ORDER.index(k) + 1 for k in ks)
    # compress runs a-b
    out, i = [], 0
    while i < len(nums):
        j = i
        while j + 1 < len(nums) and nums[j + 1] == nums[j] + 1: j += 1
        out.append(f"{nums[i]}" if i == j else (f"{nums[i]}, {nums[j]}" if j == i + 1 else f"{nums[i]}]–[{nums[j]}")); i = j + 1
    return "[" + "], [".join(out) + "]"
def C(text): return re.sub(r"<<([^>]+)>>", lambda m: cite(m.group(1)), text)

# ------------------------------------------------------------------ block helpers
counters = {"fig": 0, "tab": 0}
ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII"]
sec_i = [0]; sub_i = [0]
def one_col(force=False):
    if not force: return
    s = doc.add_section(WD_SECTION.CONTINUOUS); set_cols(s, 1); return s
def two_col(force=False):
    if not force: return
    s = doc.add_section(WD_SECTION.CONTINUOUS); set_cols(s, 2, 0.25); return s
def H1(text):
    sec_i[0] += 1; sub_i[0] = 0
    p = doc.add_paragraph(); add_runs(p, f"{ROMAN[sec_i[0]-1]}. {text.upper()}", 10, smallcaps=False); fmt(p, AL.CENTER, 10, 4, keep=True)
def H1u(text):
    p = doc.add_paragraph(); add_runs(p, text.upper(), 10); fmt(p, AL.CENTER, 10, 4, keep=True)
def H2(text):
    sub_i[0] += 1; p = doc.add_paragraph(); add_runs(p, f"{chr(64+sub_i[0])}. {text}", 10, italic=True); fmt(p, AL.LEFT, 6, 2, keep=True)
def P(text, first=0.17, after=0):
    p = doc.add_paragraph(); add_runs(p, C(text), 10); fmt(p, AL.JUSTIFY, 0, after, first=first, line=1.0); return p
def BUL(items):
    for i, t in enumerate(items, 1):
        p = doc.add_paragraph(); add_runs(p, f"{i}) " + C(t), 10); fmt(p, AL.JUSTIFY, 0, 2, hanging=0.25)
def EQ(text, n):
    p = doc.add_paragraph(); add_runs(p, text + f"\t({n})", 10); fmt(p, AL.LEFT, 4, 4)
    p.paragraph_format.tab_stops.add_tab_stop(Inches(3.45), alignment=2)
    p.paragraph_format.tab_stops.add_tab_stop(Inches(1.75), alignment=1)
    p.text = ""; p.add_run("\t"); add_runs(p, text, 10); p.add_run("\t"); add_runs(p, f"({n})", 10)
def FIGURE(fn, caption, width):
    counters["fig"] += 1
    p = doc.add_paragraph(); p.add_run().add_picture(str(FIG / fn), width=Inches(width)); fmt(p, AL.CENTER, 4, 2, keep=True)
    c = doc.add_paragraph(); add_runs(c, f"Fig. {counters['fig']}. " + C(caption), 8); fmt(c, AL.JUSTIFY, 0, 6, first=0)
def TABLE(title, header, rows, widths, bold_rows=(), sub_rows=(), size=8, align=None):
    counters["tab"] += 1
    p = doc.add_paragraph(); add_runs(p, f"TABLE {ROMAN[counters['tab']-1]}", 8); fmt(p, AL.CENTER, 6, 0, keep=True)
    p2 = doc.add_paragraph(); add_runs(p2, title.upper(), 8); fmt(p2, AL.CENTER, 0, 3, keep=True)
    avail = 3.45
    widths = [w * avail / sum(widths) for w in widths]
    t = doc.add_table(rows=1 + len(rows), cols=len(header)); t.autofit = False; cell_margins(t)
    lay = OxmlElement("w:tblLayout"); lay.set(qn("w:type"), "fixed"); t._tbl.tblPr.append(lay)
    for gc, w in zip(t._tbl.tblGrid.findall(qn("w:gridCol")), widths): gc.set(qn("w:w"), str(int(w * 1440)))
    allrows = [header] + rows
    for ri, row in enumerate(allrows):
        is_sub = (ri - 1) in sub_rows
        for ci, val in enumerate(row):
            c = t.cell(ri, ci); c.width = Inches(widths[ci]); par = c.paragraphs[0]
            add_runs(par, C(val), size, bold=(ri == 0 or (ri - 1) in bold_rows), italic=is_sub)
            fmt(par, AL.LEFT if ci == 0 or is_sub else AL.RIGHT, 0, 0, keep=False)
            if is_sub and ci == 0:
                c.merge(t.cell(ri, len(row) - 1)); break
            cell_borders(c, top=(ri == 0 or ri == 1 and False), bottom=(ri == 0 or ri == len(allrows) - 1))
    if len(allrows) > 1: pass
    sp = doc.add_paragraph(); fmt(sp, AL.LEFT, 0, 4); sp.paragraph_format.line_spacing = 0.5

# =====================================================================  TITLE BLOCK (single column)
set_cols(sec, 1)
p = doc.add_paragraph(); add_runs(p, "Smart Village Infrastructure Planning and Road Network Optimization for Rural Telangana: A Satellite-to-Network Pipeline and Its Transfer Across Settlement Types", 24); fmt(p, AL.CENTER, 0, 10)
AUTH = [("Ramakrishna Kolikipogu", "krkrishna.cse@gmail.com"), ("Pendyala Archana", "pendyalaarchanareddy98@gmail.com")]
tb = doc.add_table(rows=1, cols=2); tb.autofit = False
for ci, (nm, em) in enumerate(AUTH):
    c = tb.cell(0, ci); c.width = Inches(3.6)
    lines = [(nm, 11, True, False), ("Department of Information Technology", 9, False, True), ("Chaitanya Bharathi Institute of Technology (A)", 9, False, True), ("Hyderabad, India", 9, False, False), (em, 9, False, False)]
    for li, (tx, sz, b, it) in enumerate(lines):
        par = c.paragraphs[0] if li == 0 else c.add_paragraph(); add_runs(par, tx, sz, bold=b, italic=it); fmt(par, AL.CENTER, 0, 0)
sp = doc.add_paragraph(); fmt(sp, AL.CENTER, 0, 12)

ABS = ("*Abstract*—Rural road infrastructure planning faces several challenges, including incomplete spatial data, unplanned settlements, difficult terrain, and limited information about suitable road connections to essential public services such as hospitals, schools, and government institutions. Conventional road-planning approaches often rely on manual decision-making and shortest-path algorithms, which may not adequately consider the influence of spatial-data errors, terrain conditions, land-use constraints, and opportunities for sharing road segments. To address these challenges, this work proposes an AI- and GIS-based framework for rural village infrastructure planning and road-network optimization. The proposed framework integrates high-resolution satellite imagery, existing road-network data, village boundary information, land-cover maps, elevation data, and public-service locations. A StrongDINOv2Seg deep-learning model is employed for semantic segmentation, supported by GIS-based feature extraction to identify relevant spatial features. A multi-criteria cost surface is then generated by considering land-cover conditions, terrain slope, and restricted areas to identify suitable movement paths. For road-network planning, a two-stage approach is implemented: in the first stage, alternative least-cost routes are generated using grid-based Dijkstra pathfinding; in the second stage, a greedy shared-network selection strategy evaluates alternative routes based on their marginal cost and gives credit to road segments already included in the selected network, reducing unnecessary route duplication while prioritizing connections to public-service facilities and residential buildings. The framework is demonstrated on Damarakunta village in Siddipet District, Telangana, and evaluated for cross-morphology transferability in Adilabad Urban. On the LoveDA validation benchmark, the segmentation model achieved a mean Intersection over Union (mIoU) of 53.8% and a mean Dice score of 68.9%. In the Damarakunta building-access planning experiment, the two-stage network-aware approach produced 5,069.0 m of unique route length compared with 6,753.1 m for independent least-cost routing, representing a reduction of 24.9%. Re-applied end to end to Adilabad Urban on Esri imagery, the same cost surface and solver reduced unique route length from 21,440.8 m to 18,288.7 m (14.7%) for 345 road-gap targets, and with open Overture Maps footprints from 46,419.2 m to 34,358.8 m (26.0%), confirming consistent network-sharing behavior across contrasting settlement densities, although a roads-only shared reference recovered most of the saving in Damarakunta (22.6%) but little in Adilabad (2.3% and 2.9%). Because most StrongDINOv2Seg instances in Adilabad's dense fabric are merged roof blocks, its targets are built-up units rather than counted houses. The proposed framework provides a GIS-based decision-support approach for analyzing rural infrastructure requirements and generating cost-aware road-network alternatives as computational planning suggestions requiring field validation prior to implementation.")
p = doc.add_paragraph(); add_runs(p, ABS, 9, bold=False); fmt(p, AL.JUSTIFY, 0, 4, left=0.0)
p = doc.add_paragraph(); add_runs(p, "*Index Terms*—Building footprint extraction, DINOv2, least-cost path, open geospatial data, rural roads, shared network, spatial transferability, Telangana.", 9); fmt(p, AL.JUSTIFY, 0, 6)

two_col(True)

# =====================================================================  I. INTRODUCTION
H1("Introduction")
P("Road building is among the most consequential land-use changes of the coming decades: global road length is projected to grow by roughly 3.0–4.7 million km by 2050 <<meijer2018global>>, and new roads open land to clearing and fragmentation <<laurance2014global>>. In India the Pradhan Mantri Gram Sadak Yojana (PMGSY) connects habitations through all-weather rural roads <<pmgsy>>. Planning access to individual hamlets needs three inputs: where the dwellings are, what land a corridor must cross, and a rule that turns these into alignments.")
P("Computational support has matured along three separate lines. Remote sensing maps buildings and roads at scale, from continental building inventories <<sirko2021openbuildings>> to foundation-model segmenters <<oquab2023dinov2>>, with recent work on small rural buildings, uncertainty and domain shift <<r62,r63,r64,r65,r66,r67,r68,r69,r70>>. Multi-criteria and least-cost analysis converts terrain and land cover into route cost <<r06,r53,r54,collischonn2000lcp>>. Network-design formulations connect many demand points at low total cost, including Steiner-tree heuristics <<kou1981steiner,mehlhorn1988steiner,hwang1992steiner,r51>>, rural road design models <<r41,r43,r44>> and analogues for power and transport networks <<r45,r46,r47,r50>>. These lines are rarely joined: detectors are judged by pixel overlap <<r01>>, planners assume an error-free inventory, and each house is often connected independently, so neighbouring houses re-trace the same corridor.")
P("This paper joins them in one reproducible pipeline and tests it at two settlement densities. The contributions are:")
BUL(["**End-to-end pipeline.** StrongDINOv2Seg segmentation, OpenCV/NumPy instance extraction with an explicit merge flag and facility verification, a multi-criteria cost surface with a footprint penalty, and a two-stage shared-network planner (Section IV).",
     "**Error propagation.** Controlled omission and addition scenarios that propagate building-inventory errors through the planner and measure their effect on unique length, coverage and exposure of dwellings (Sections V-B to V-D).",
     "**Multi-settlement spatial transferability and open-data scalability.** The rural Damarakunta workflow is re-applied, with the same cost-surface definition and solver, to the Adilabad Urban mandal (urban and peri-urban): end to end on Esri imagery (StrongDINOv2Seg and instance extraction) and, as an independent check, on open Overture Maps footprints, with a road-gap rule for targets and robustness examined over penalty settings, road-gap thresholds and synthetic omissions (Section V-E)."])
P("Two scope limits apply. Only these two settlements were evaluated; a semi-urban and a second rural window are planned but not yet run, so no rural–semi-urban–urban gradient is claimed. And the Adilabad segmentation results are unvalidated: no reference building mask exists, and in the dense fabric most detected instances are merged roof blocks (Section V-E), so the Adilabad targets are built-up units rather than counted houses.")

# =====================================================================  II. RELATED WORK
H1("Related Work")
P("*Building and road extraction.* Reviews of building extraction <<r01>> document the shift from fully convolutional networks <<ji2019whu>> to transformer and foundation-model encoders. Recent studies address isolated small buildings <<r63>>, weak supervision <<r62>>, uncertainty-guided refinement <<r64,r65>> and domain generalisation across imagery sources <<r02,r66,r67,r68,r69,r70>>. Road extraction has followed the same path with width-adaptive, topology-preserving and foundation-model-based networks <<r56,r57,r58,r59,r60>>, and topological analysis has been used to detect informal settlements <<r48>>. Evaluation is overwhelmingly through overlap scores <<foody2002status>>; the effect of detection errors on downstream infrastructure decisions is rarely quantified, although error propagation in GIS models is long established <<heuvelink1998error>>.")
P("*Route and network planning.* Multi-criteria GIS analysis <<r06>> and least-cost paths <<collischonn2000lcp,r53,r54>> underlie corridor selection, with treatments of slope <<r54>>, alternative routes <<r53>> and travel-time uncertainty <<r61>>; GIS route reconstruction has also been applied to historical transport routes <<r55>>. Rural road design has been addressed with improved network-design models <<r41>>, algorithmic planning under constrained capacities in India <<r43>> and facility-based methodology <<r44>>. Steiner-tree formulations <<hwang1992steiner>> and their shortest-path heuristics <<kou1981steiner,mehlhorn1988steiner>> are applied to sub-network identification <<r51>>, multi-terminal routing <<r52>>, cable routing <<r45>>, minimum spanning trees of road networks <<r46>>, rural grids <<r47>> and least-cost electrification <<r50>>.")
P("*Gap.* To our knowledge no cited work combines (i) satellite-derived building instances, (ii) a land-cover- and slope-based cost surface with building avoidance, (iii) a shared-network planner whose marginal cost credits built corridors, and (iv) a systematic test of how inventory omissions and the settlement setting change the result.")

# =====================================================================  III. STUDY AREAS AND DATA
H1("Study Areas and Data")
H2("Damarakunta (rural)")
P("Damarakunta is a rural revenue village in Markook mandal, Siddipet district, Telangana (≈17.707°N, 78.753°E). Its boundary, from the Telangana State Remote Sensing Application Centre (TGRAC), encloses 18.47 km^{2} (UTM zone 44N, EPSG:32644). Settlement is dispersed: houses form small clusters separated by farmland (Figs. 1 and 2). A 0.6 m three-band mosaic (11,296 × 7,171 px) was assembled from Esri World Imagery exports. Building candidates are model outputs: 278 polygons, 165 inside the boundary, of which 163 are routing targets. Each carries a quality class: Plausible (71), Review (32) and Unresolved_Merge (62), the last denoting blobs that merge adjacent roofs and could not be split. Five TGRAC facilities (schools, a health sub-centre and the gram-panchayat headquarters points) are planned in a separate phase. A TGRAC anganwadi record was excluded because its coordinate lies about 371 m from the nearest footprint and was judged unsupported; its true location remains to be verified. No ground-truth building mask exists for Damarakunta.")
FIGURE("fig2_study_area.png", "Damarakunta. (a) Boundary, TGRAC roads and detected footprints by quality class, with the five facilities. (b) Main settlement. Footprints are automatic detections, not a census; no imagery basemap is shown.", 3.4)
FIGURE("dk_map1_satellite.jpg", "Damarakunta: village boundary (TGRAC, yellow) and existing TGRAC roads (cyan) over satellite imagery. (Basemap imagery: Esri, Maxar, Earthstar Geographics, and the GIS User Community).", 3.4)
H2("Adilabad Urban (urban and peri-urban)")
P("The second window is the Adilabad Urban mandal, Adilabad district (geoBoundaries ADM3 polygon <<runfola2020geoboundaries>>; centroid 19.682°N, 78.528°E), 17.75 km^{2}, close to Damarakunta in area. Its 10 m grid has 424 × 564 cells, 177,533 of them inside the polygon and 0.62% blocked (water or slope above 25°). About 60% of cells are not WorldCover built-up, so the window holds an urban core and a peri-urban fringe. The boundary is the 2018 release and may differ from current municipal limits.")
P("Two sets of building footprints are used. (i) *Segmentation footprints (primary, end to end).* A 0.6 m Esri World Imagery mosaic of the window (7,248 × 9,590 px, EPSG:32644) was exported with the Damarakunta recipe (1,800 m tiles). StrongDINOv2Seg was applied to 391 tiles of 560 × 560 px (stride 420 px, margin 70 px, the Damarakunta tiling; Damarakunta: 459 tiles) and the same instance extraction. This yields 2,769 instances, of which 2,690 have an area of at least 30 m^{2} and form the penalty layer; their quality classes are Plausible (1,033), Review (77) and Unresolved_Merge (1,580), the last with a median area of 1,125.5 m^{2} (Plausible: 207.4 m^{2}). Of 83 Overture place candidates inside the window, 68 are verified with the Damarakunta rule (a detected footprint within 20 m): 44 schools, 20 health and 4 government. (ii) *Open footprints (independent check).* Overture release 2026-10-21.0 <<overture2026>> supplies 4,850 road segments, 24,924 building polygons (18,846 from OpenStreetMap and 6,078 from Google Open Buildings v3 <<sirko2021openbuildings>>) and 738 places; footprints with area ≥ 30 m^{2} and confidence ≥ 0.7 (18,242 polygons) form the penalty layer, and 71 of the 83 facility candidates are verified (44 schools, 20 health, 7 government) after manual removal of mis-geocoded records. Roads are Overture/OSM segments in both variants. Neither footprint set has been field-verified.")

TABLE("Input data and licence status",
      ["Layer", "Damarakunta / Adilabad source", "Licence status"],
      [["Boundary", "TGRAC / geoBoundaries ADM3", "Not stated / ODbL 1.0"],
       ["Roads, facilities", "TGRAC (43 road features, 5 facilities) / Overture 2026-10-21.0", "Not stated / ODbL 1.0 (roads), CDLA-Permissive-2.0 (places); not re-verified"],
       ["Buildings", "StrongDINOv2Seg instances (0.6 m Esri imagery; both windows) / Overture footprints (Adilabad check)", "Esri academic-use terms, tiles not redistributed / ODbL 1.0 and CC BY 4.0; not re-verified"],
       ["Land cover", "ESA WorldCover v200, 10 m <<zanaga2021worldcover>>", "CC BY 4.0"],
       ["Terrain", "~30 m DEM (source not recorded) / Copernicus GLO-30 <<esa2022copdem>>; Sobel slope, bilinear to 10 m", "Not stated / Copernicus Open Access Licence"],
       ["Training data", "LoveDA <<wang2021loveda>>", "Source domain only"]],
      [0.75, 1.55, 1.2], size=7.5)
# table cells contain <<>> markers: handled below by a post-pass

# =====================================================================  IV. METHODOLOGY
H1("Methodology")
P("Fig. 3 summarises the architecture. The two settlements differ in the perception and target stages and share the cost surface, planner and evaluation stages.")
FIGURE("fig_architecture.png", "System architecture. Inputs feed a perception stage (Damarakunta: segmentation and instance extraction; Adilabad: the same chain on Esri imagery, with open footprints entering the target stage directly as an independent check), a shared cost surface, a two-stage shared-network planner and an evaluation stage that includes the cross-settlement transfer.", 3.4)
H2("Semantic segmentation: StrongDINOv2Seg")
P("StrongDINOv2Seg uses the pre-trained facebook/dinov2-base encoder (DINOv2 ViT-B/14 <<oquab2023dinov2>>), fully fine-tuned. Tokens from transformer blocks 3, 6, 9 and 12 are projected to 256 channels and fused in a feature-pyramid manner <<lin2017fpn>>, passed through an atrous spatial pyramid pooling neck with rates 6, 12 and 18 <<chen2018deeplabv3plus>> and a four-stage residual decoder with auxiliary heads for deep supervision <<lee2015dsn>>. Training on LoveDA <<wang2021loveda>> used 560 px inputs for a scheduled 10 epochs with AdamW, a cosine learning-rate schedule to 10^{-7}, an encoder learning rate of 0.1 times the base rate, and the loss 0.5·CE + 0.4·Dice + 0.1·edge <<milletari2016vnet>> with auxiliary weight 0.4. The epoch-4 checkpoint was evaluated and used; the file used for the Adilabad run has SHA-256 2e7c4646dc77ceb2a357f44f11cb3f7ff84e636871d70ba4c31e194e5ec00cf3.")
H2("Instance extraction and facility verification")
P("Building instances are extracted from the predicted mask with OpenCV and NumPy. For each connected component, a Euclidean distance transform is computed; h-maxima, obtained by iterative morphological reconstruction with a 3 × 3 dilation, give one marker per candidate roof; a priority-driven marker-controlled flooding of the distance transform (a watershed-type transform) assigns pixels to markers; and adjacent pieces are merged back unless the saddle height between them is below 0.65 of the lower peak (neck test) and each piece exceeds a minimum area. Components that cannot be split reliably are flagged Unresolved_Merge, and the remaining polygons are labelled Plausible or Review by size and shape rules. Facilities are accepted as targets only if they lie inside the boundary and have a detected footprint within 20 m of the recorded point; the same rule is applied to Overture places in Adilabad, together with manual removal of mis-geocoded records.")
H2("Road-gap targets and Adilabad footprint sources")
P("For Adilabad the same imagery-to-footprint chain is run on Esri imagery (Section III-B), and Overture footprints serve as an independent check. Because connecting every footprint is meaningless in a built-up fabric already served by roads, only houses more than 30 m (the planner snap distance) from an existing road are routed. Planner cost grows roughly quadratically with the number of targets, which further motivates the filter; the threshold is varied (20, 30, 50 m) in Section V-E.")
H2("Multi-criteria cost surface")
P("Let *B* be the set of blocked cells (water, invalid cells, slope above 25°) and *P* the set of cells whose centre lies inside a footprint. The graph has the unblocked 10 m cells as nodes and 8-neighbour edges without diagonal corner-cutting. The cell cost is")
EQ("*c*(*x*) = [ *c*_{lc}(ℓ(*x*)) + *g*(*s*(*x*)) ] · *m*(*x*)", 1)
P("where *m*(*x*) = μ if *x* ∈ P and 1 otherwise, ℓ is the ESA WorldCover class <<zanaga2021worldcover>> with resistances 8, 5, 3, 6, 2 and 4 for classes 10 (tree cover), 20 (shrubland), 30 (grassland), 40 (cropland), 50 (built-up) and 60 (bare/sparse), g(s) = 4·clip(s, 0, 10)/10 with s the slope in degrees derived from the DEM <<esa2022copdem>>, and μ = 4 is the footprint penalty. Edge weights are the mean end-cell cost times step length. The 25° slope limit is a project rule, not a transcription of Indian Roads Congress standards, and costs are ordinal planning units, not currency. In Damarakunta the penalty is lifted within a 20 m disc around the health sub-centre, whose point lies on the edge of its own footprint. The base cost surface of Damarakunta is shown in Fig. 4.", first=0)
FIGURE("dk_cost_surface.png", "Damarakunta base cost surface (land cover plus slope, before the footprint penalty; ordinal planning units per 10 m cell, not rupees). White cells are blocked (water or invalid cells); blue lines are existing TGRAC roads.", 3.4)
H2("Two-stage shared-network planner")
P("For each target, Stage A computes a least-cost path to the existing road cells with Dijkstra's algorithm <<dijkstra1959note,hart1968astar,collischonn2000lcp>> and obtains alternatives by inflating costs along earlier paths (K = 3 alternatives in total). Stage B greedily selects the (target, alternative) pair with the highest weight per marginal cost")
EQ("Δ*L*_{cost}(π | *S*) = Σ *w*(*e*),  *e* ∈ π∖*E*_{S}", 2)
P("where *E*_{S} is the set of already selected edges, so built edges are free and a route may end on another route. This is the shortest-path heuristic for Steiner trees <<kou1981steiner,mehlhorn1988steiner>> on a penalised, land-cover-weighted graph with the road network as a free sub-tree; it carries no optimality guarantee. Two leaf re-routing passes follow. Snap distance is 30 m, search limit 1,500 m and attachment tolerance 15 m. Facilities are planned in a separate phase (script plan_network_v2.py).", first=0)
H2("Baselines, scenarios and metrics")
P("Four baselines are compared: straight lines, independent least-cost routes, a length-only control (distance instead of cost surface) and a roads-only shared reference (routes may share edges only with the existing road network). The saving against independent routing is ρ = (*L*_{ind} − *L*)/*L*_{ind}, with *L* the unique network length (shared edges counted once). Exposure is measured by the number of routes crossing another house's footprint and the route length inside other footprints. The footprint penalty is varied (μ ∈ {1, 4, 20, 100}, with a variant in which footprints are buffered by 7.1 m). For omissions, a target set *M* is removed from the targets and from the penalty layer (a missed detection is absent from both) and the planner re-run; random draws use seeds 1–5. Reported are coverage, unserved households, change in unique length and length per routed target. No monetary cost is computed: the repository holds no rupee-denominated estimates, and the PMGSY scheme <<pmgsy>> is used only as planning context.")

# wide figure: architecture

# =====================================================================  V. RESULTS
H1("Experiments and Results")
H2("Detection")
P("On the 1,669-image LoveDA validation split (560 px, seven scored classes) the epoch-4 checkpoint reached 53.8% mIoU, 68.9% Dice and 71.3% pixel accuracy (recomputed from the saved confusion matrix), with 72.4% macro precision and 66.9% macro recall; for the Building class IoU is 54.0%, precision 62.1% and recall 80.6% (Table II). These are source-domain figures, not accuracy on Damarakunta. Against Google Open Buildings v3 as a proxy (not ground truth), 118 of the 165 in-boundary candidates agree (71.5%).")
TABLE("Detection evaluation (LoveDA validation, %; and proxy agreement)",
      ["", "mIoU", "Dice", "Pix. acc.", "Prec.", "Rec."],
      [["StrongDINOv2Seg", "53.8", "68.9", "71.3", "72.4", "66.9"],
       ["  Building class", "54.0", "70.1", "—", "62.1", "80.6"],
       ["Damarakunta candidates vs. Open Buildings v3", "", "", "", "", ""],
       ["Class", "n", "Agree", "Disagree", "Agr. %", ""],
       ["All", "165", "118", "47", "71.5", ""],
       ["Plausible", "71", "51", "20", "71.8", ""],
       ["Review", "32", "14", "18", "43.8", ""],
       ["Unresolved_Merge", "62", "53", "9", "85.5", ""]],
      [1.2, 0.4, 0.42, 0.52, 0.45, 0.45], sub_rows=(2,), bold_rows=(3,), size=7.5)
H2("Damarakunta: shared network and footprint penalty")
P("Independent least-cost routes for the 163 houses total 10,045.4 m, but because neighbouring houses re-trace the same corridors the unique built length is 6,753.1 m (Table III). The two-stage plan reduces this to 5,069.0 m, a saving of 24.9%; all 163 houses and five facilities are connected. The length-only control has 3.4% more unique length than independent cost-surface routing, and the roads-only shared reference saves 22.6%, so most of the saving comes from sharing and a further 2.3 percentage points from sharing among new routes.")
P("The penalty trades length for exposure (Fig. 5). With μ = 1 the plan is shortest (4,705.4 m) but 56 routes pass through other houses (660.1 m inside footprints). With μ = 4 it is 7.7% longer while crossings halve to 28 routes and 209.1 m. Buffering footprints by 7.1 m with μ = 20 or 100 lowers crossings to 19 routes at 6,238.1 m and 6,190.3 m.")
TABLE("Damarakunta routing, 163 houses (μ = 4 unless stated)",
      ["Strategy", "Total (m)", "Unique (m)", "ρ (%)", "Cross.", "In fp. (m)"],
      [["Straight line (2 infeasible)", "8,092.3", "—", "—", "60", "1,453.2"],
       ["Independent least-cost", "10,045.4", "6,753.1", "0.0", "46", "328.3"],
       ["Length-only control", "9,166.3", "6,979.8", "−3.4", "64", "1,615.8"],
       ["Roads-only shared ref.", "5,229.3", "5,229.3", "22.6", "29", "216.1"],
       ["**Two-stage plan (proposed)**", "**5,069.0**", "**5,069.0**", "**24.9**", "**28**", "**209.1**"],
       ["No footprint penalty (μ = 1)", "", "", "", "", ""],
       ["Independent least-cost", "9,595.9", "6,921.3", "0.0", "63", "1,423.1"],
       ["Two-stage plan", "4,705.5", "4,705.4", "32.0", "56", "660.1"],
       ["Buffered footprints (7.1 m), two-stage", "", "", "", "", ""],
       ["Penalty μ = 20", "—", "6,238.1", "18.5", "19", "147.9"],
       ["Penalty μ = 100", "—", "6,190.3", "18.9", "19", "144.8"]],
      [1.2, 0.5, 0.5, 0.4, 0.35, 0.55], sub_rows=(5, 8), size=7.5)
FIGURE("fig3_routing.png", "Damarakunta routing results for 163 houses. (a) Total and unique corridor length by strategy. (b) Unique network length against route length inside other houses' footprints for μ = 1, μ = 4 and buffered footprints with large penalties.", 3.4)
H2("Damarakunta: impact of building omissions")
P("Table IV and Fig. 6 give the omission analysis against the 5,069.0 m baseline. Missing buildings make the plan *shorter*: 10% random omission (16 houses) understates length by 7.6%, 20% by 16.9%, omission of the smallest quarter by 25.1% and omission of all merged blobs by 29.4%. At the same time U households lose access: 16 and 33 for random 10% and 20% omission, 41 for the smallest quarter and 62 (38.0%) for merged blobs. A planner reading only total length would therefore underfund the scheme. Random additions lengthen the plan by 8.6% and 15.8%. The saving ρ stays within 24.9–26.6% across omissions, so the benefit of sharing is robust to inventory error.")
TABLE("Simulated omissions and additions, Damarakunta (baseline 5,069.0 m, 163 routed)",
      ["Scenario", "Routed", "U", "κ (%)", "L (m)", "δ_{L} (%)", "ρ (%)"],
      [["Baseline", "163", "0", "100.0", "5,069.0", "0.0", "24.9"],
       ["Omit 10% (random)", "147.0", "16", "90.2", "4,684.4", "−7.6", "25.1"],
       ["Omit 20% (random)", "130.0", "33", "79.8", "4,211.5", "−16.9", "24.9"],
       ["Omit smallest 10%", "146", "17", "89.6", "4,648.6", "−8.3", "24.9"],
       ["Omit smallest 25%", "122", "41", "74.8", "3,798.3", "−25.1", "25.6"],
       ["Omit merged blobs", "101", "62", "62.0", "3,579.0", "−29.4", "26.6"],
       ["Add 10% (random)", "177.4", "—", "—", "5,502.4", "+8.6", "25.6"],
       ["Add 20% (random)", "190.6", "—", "—", "5,868.3", "+15.8", "25.4"]],
      [1.15, 0.45, 0.3, 0.4, 0.5, 0.45, 0.35], size=7.5)
FIGURE("fig4_omission.png", "Damarakunta omission sensitivity (163 baseline targets; random scenarios are five draws with min–max bars). (a) Change in unique length against households left without a route. (b) Unique length per routed target.", 3.4)
H2("Transfer to Adilabad Urban")
P("*End-to-end run (StrongDINOv2Seg footprints).* Of the 2,690 footprints of at least 30 m^{2}, 345 lie more than 30 m from a road and form the targets (Damarakunta: 163). The planner routes all 345. Independent least-cost routes total 23,312.5 m (unique 21,440.8 m); the two-stage plan needs 18,288.7 m, a saving of 14.7% (Table V, Figs. 7–9). The roads-only shared reference saves 2.3% and the length-only control 6.9%, so almost all of the saving comes from sharing among new routes. Exposure: 54 of 345 routes (15.7%) cross another footprint (398.0 m), against 28 of 163 (17%) in Damarakunta.")
P("These numbers must be read with the extraction quality in mind. More than half of the instances (1,580 of 2,769) are Unresolved_Merge blobs with a median area of 1,125.5 m^{2}: in the dense fabric the segmenter merges neighbouring roofs, so the 345 targets are built-up units rather than houses, and the footprint penalty acts on merged blocks. No reference mask exists for Adilabad, so detection accuracy there is not known.")
P("*Open-footprint check.* With 874 road-gap targets among 18,242 Overture footprints (median footprint 139.6 m^{2}, median distance to the nearest road 42.3 m), independent routes total 56,308.0 m (unique 46,419.2 m) and the two-stage plan 34,358.8 m, a saving of 26.0%; the roads-only reference saves 2.9% and the length-only control 5.7%; 332 of 873 routes (38%) cross another footprint (2,041.1 m). The facility phase connects 71 verified facilities with 1,090.1 m of unique corridor.")
P("Both Adilabad variants agree that sharing helps (14.7% and 26.0%) and that a roads-only reference does not (2.3% and 2.9%, against 22.6% in Damarakunta), but they differ in the size of the saving. This is consistent with fewer, more widely spaced targets (345 against 874) offering less opportunity to share, an explanation that was not tested. The comparison is between two footprint sources, not a validation of either.")
TABLE("Cross-settlement comparison under the same cost surface and solver (seg. = StrongDINOv2Seg footprints on Esri imagery; open = Overture footprints)",
      ["Metric", "Damar-akunta", "Adilabad seg.", "Adilabad open"],
      [["Study area (km^{2})", "18.47", "17.75", "17.75"],
       ["Targets / routed", "163 / 163", "345 / 345", "874 / 873"],
       ["Independent, unique (m)", "6,753.1", "21,440.8", "46,419.2"],
       ["Length-only, unique (m)", "6,979.8", "19,961.2", "43,787.2"],
       ["Roads-only shared, unique (m)", "5,229.3", "20,947.0", "45,058.9"],
       ["**Two-stage, unique (m)**", "**5,069.0**", "**18,288.7**", "**34,358.8**"],
       ["Saving vs. independent (%)", "24.9", "14.7", "26.0"],
       ["Roads-only saving (%)", "22.6", "2.3", "2.9"],
       ["Unique length per routed house (m)", "31.1", "53.0", "39.4"],
       ["Routes crossing footprints", "28 of 163", "54 of 345", "332 of 873"],
       ["Length inside footprints (m)", "209.1", "398.0", "2,041.1"],
       ["μ = 1 → 4: length change (%)", "+7.7", "+9.2", "+13.3"],
       ["μ = 1 → 4: crossing routes", "56 → 28", "138 → 54", "618 → 332"],
       ["10% omission: change (%) / unserved", "−7.6 / 16", "−8.8 / 34", "−7.6 / 88"],
       ["20% omission: change (%) / unserved", "−16.9 / 33", "−18.3 / 69", "−15.0 / 176"],
       ["Smallest 25%: change (%) / unserved", "−25.1 / 41", "−21.2 / 87", "−21.2 / 220"]],
      [1.55, 0.6, 0.65, 0.65], size=7.5)
FIGURE("adilabad_sat_overview.jpg", "Adilabad Urban on Esri satellite imagery: (a) study window with the polygon boundary (yellow), existing roads (cyan), StrongDINOv2Seg instances outlined by quality class (green Plausible, amber Review, red Unresolved_Merge), road-gap targets (orange) and verified facilities (stars); (b) zoom on the densest road-gap cluster. "+CR, 3.4)
FIGURE("adilabad_sat_routes_window.jpg", "Adilabad Urban route comparison for the 345 road-gap targets (μ = 4), full window: (a) independent least-cost routes (blue), (b) two-stage shared plan (red). Planning alternatives, not engineered roads. "+CR, 3.4)
FIGURE("adilabad_sat_routes_zoom.jpg", "Adilabad Urban, zoom on the densest road-gap cluster (200 m scale bar): (c) independent least-cost routes, (d) two-stage shared plan. "+CR, 3.4)
H2("Adilabad robustness")
P("*Footprint penalty.* Raising μ from 1 to 4 lengthens the unique network by 9.2% and removes 84 crossing routes (138 to 54); μ = 20 and 100 give 19,777.0 m and 19,924.5 m with 49 and 48 routes crossing, and buffered footprints give 22,757.0 m and 23,475.5 m with 7 crossing each (Table VI, Fig. 10a). The saving against independent routing stays between 10.1% and 17.7% across all settings (open footprints: 17.8% to 30.8%).")
P("*Road-gap threshold.* Targets defined as houses more than 20, 30 or 50 m from a road number 750, 345 and 129 and give savings of 10.6%, 14.7% and 18.5% (open footprints: 2,190, 874 and 296 targets; 21.9%, 26.0% and 29.5%). The saving therefore depends on the target definition, which should be reported with any such result.")
P("*Omissions.* Random omission of 10% and 20% (five seeds) changes unique length by −8.8% (range −11.7 to −6.5) and −18.3% (−21.9 to −15.8), leaving 34 and 69 targets unserved; single-run smallest-10% and smallest-25% omissions give −8.0% and −21.2% (35 and 87 unserved). As in Damarakunta and in the open-footprint check, missing buildings shorten the plan while stranding households, and the saving stays at 12.6–14.1%. Merged-blob and addition scenarios were not defined for Adilabad.")
TABLE("Adilabad sensitivity, StrongDINOv2Seg footprints (345 targets unless stated)",
      ["Setting", "Unique (m)", "ρ (%)", "Cross.", "In fp. (m)"],
      [["Centre-in-footprint, μ = 1", "16,740.5", "17.7", "138", "1,479.8"],
       ["Centre-in-footprint, μ = 4", "18,288.7", "14.7", "54", "398.0"],
       ["Centre-in-footprint, μ = 20", "19,777.0", "12.5", "49", "356.4"],
       ["Centre-in-footprint, μ = 100", "19,924.5", "12.2", "48", "343.2"],
       ["Buffered 7.1 m, μ = 20", "22,757.0", "10.1", "7", "57.9"],
       ["Buffered 7.1 m, μ = 100", "23,475.5", "10.6", "7", "55.7"],
       ["Road-gap > 20 m (750 targets)", "30,621.7", "10.6", "69", "442.8"],
       ["Road-gap > 30 m (345, primary)", "18,288.7", "14.7", "54", "398.0"],
       ["Road-gap > 50 m (129 targets)", "9,155.2", "18.5", "28", "251.9"]],
      [1.5, 0.6, 0.4, 0.4, 0.55], size=7.5)
FIGURE("adilabad_seg_sens_col.png", "Adilabad sensitivity (StrongDINOv2Seg footprints). (a) Footprint-penalty trade-off between unique network length and route length inside other footprints. (b) Omission sensitivity (random: mean and min–max over five seeds; smallest-q: single run).", 3.4)

if HAVE("adilabad_fac_route_2panel.png"):
    FIGURE("adilabad_fac_route_2panel.png", "Adilabad Urban, central zone on Esri imagery: (a) verified facilities (stars: schools; crosses: health; squares: government) and detected footprints outlined by quality class; (b) final shared network (red), facility routes (white) and road-gap targets (orange). "+CR, 3.0)
H1("Discussion and Limitations")
H2("What transfers and what does not")
P("The planning stages transferred without modification: the same cost surface, solver parameters and metrics produced connected plans in a dense window, both from StrongDINOv2Seg footprints on Esri imagery (345 targets) and from open footprints (874 targets). The qualitative findings were reproduced in all three settings: sharing saves unique length (24.9%, 14.7% and 26.0%), the footprint penalty trades length for exposure, and omissions shorten the plan while stranding households. What did not transfer is the benefit of the simpler baselines: roads-only sharing recovered most of the gain in the dispersed village (22.6%) but almost none in the dense window (2.3% and 2.9%), which suggests that the value of a marginal-cost planner grows with settlement density, a hypothesis supported by one dense window. The two Adilabad footprint sources differ in the size of the saving (14.7% against 26.0%); with 57% of the segmented instances being merged blocks, the segmentation result may reflect coarse, widely spaced targets, and no reference mask exists to say which footprint set is closer to the truth.")
H2("Why pixel metrics are not enough")
P("Segmentation metrics are area-weighted over classes, while the planner counts instances. A detector that misses the smallest quarter of buildings can lose few building pixels yet removes a quarter of the households from the plan (Table IV), and a detector that merges adjacent roofs can score a high pixel IoU yet strand 38% of Damarakunta's houses in the merged-blob scenario. Network length falls in both cases, so total length is a poor quality indicator.")
H2("Land take and planning use")
P("Shared corridors reduce new road length for the same households. As an illustration only, assuming a 5 m formation width (an assumption of this study; no road-width data were available), the 1,684 m saved in Damarakunta corresponds to about 0.84 ha less land take, the 3,152 m saved in Adilabad (segmentation targets) to about 1.6 ha and the 12,060 m saved against the open-footprint targets to about 6.0 ha. For PMGSY-style schemes <<pmgsy>>, building inventories should be treated as uncertain inputs, with a sensitivity band on any network sized from them. The outputs are screening-level alternatives; no compliance with Indian Roads Congress design standards and no cost in rupees is claimed.")
H2("Limitations")
P("(i) Two settlements only; the semi-urban and second rural windows are planned but not run. (ii) Omission scenarios are synthetic, not measured detection errors. (iii) Neither Damarakunta nor Adilabad has a surveyed reference mask; the LoveDA metrics come from the epoch-4 checkpoint with metadata recovered from the training notebook, and the checkpoint hash (SHA-256 2e7c4646dc77ceb2a357f44f11cb3f7ff84e636871d70ba4c31e194e5ec00cf3) was logged only for the Adilabad run, not with the Damarakunta candidates, although both runs loaded the same file path. (iv) In Adilabad 57% of the StrongDINOv2Seg instances are Unresolved_Merge blocks, so its 345 targets are built-up units, not houses; the open footprints are map data of unverified completeness, and Overture licences were not re-verified. Ten of the 68 verified facility points share an identical coordinate with another Overture record (generic geocodes), so the 20 m footprint check is weak evidence in the dense fabric. (v) Costs are ordinal, the planner is a heuristic without an optimality guarantee, and road-gap targeting changes the problem, as the threshold sweep shows. (vi) Pixel accuracy is reported as 71.3%, the value recomputed from the confusion matrix. (vii) Merged-blob and addition scenarios were run only for Damarakunta.")

# =====================================================================  VII. CONCLUSION
H1("Conclusion")
P("A pipeline from satellite imagery and open layers to shared access roads connects the houses and facilities of a rural village with 24.9% less unique corridor than independent routing and, without changes to the cost surface or solver, those of an urban and peri-urban mandal, end to end on Esri imagery (14.7% less) and on open footprints (26.0% less). Footprint penalties and simulated inventory errors behave consistently in both settings: penalties trade length for fewer routes through dwellings, and omissions shorten the plan while stranding households. The dependence of the roads-only baseline on settlement density and the effect of detection quality across settings are the main open questions; a semi-urban and a second rural window are planned to address the first.")
H1u("Data Sources and Imagery Attribution")
P("High-resolution RGB satellite basemap imagery for Damarakunta Village and the Adilabad Urban window was obtained via Esri World Imagery (sources: Esri, Maxar, Earthstar Geographics, and the GIS User Community) and used strictly for non-commercial academic research and visual overlay in accordance with Esri’s academic use terms, while raw imagery tiles are not redistributed. All derived modeling and multi-settlement planning layers rely on open-licensed datasets: ESA WorldCover 10 m v200 (CC BY 4.0), Copernicus GLO-30 DEM (Copernicus Open Access Licence), geoBoundaries ADM3 (ODbL 1.0), and Overture Maps (ODbL 1.0 / CDLA-Permissive-2.0). Damarakunta's boundary, road and facility layers are TGRAC data and its ~30 m DEM source was not recorded; the Copernicus GLO-30 and geoBoundaries layers apply to the Adilabad window.")
H1u("Acknowledgment")
P("The authors acknowledge the Telangana State Remote Sensing Application Centre (TGRAC) for the Damarakunta boundary, road and facility layers, and the providers of the open datasets used (ESA WorldCover, Copernicus DEM, Overture Maps, geoBoundaries, Google Open Buildings, LoveDA). This research received no specific grant from any funding agency in the public, commercial, or not-for-profit sectors. The authors declare no competing interests.")
H1u("Data Availability")
P("Code, derived summary tables and open-data manifests with SHA-256 hashes are available at https://github.com/Archana519/Telangana-Rural-Project (folders DELIVERABLES_DAMARAKUNTA_STAGE_B and DELIVERABLES_CONTRIBUTION_3_MULTI_VILLAGE, including the Adilabad segmentation results in 01_ADILABAD_SEGMENTATION). TGRAC layers are subject to the provider's terms. The StrongDINOv2Seg checkpoint is not included in the repository; its SHA-256 is given in Section IV-A. A Zenodo DOI will be added when the archive is minted.")
H1u("References")
for i, k in enumerate(ORDER, 1):
    p = doc.add_paragraph(); add_runs(p, f"[{i}]\t" + ref_text(ENT[k]), 8); fmt(p, AL.JUSTIFY, 0, 2, hanging=0.3)
    p.paragraph_format.tab_stops.add_tab_stop(Inches(0.3))

# ---------------- post-pass: resolve <<key>> markers inside table cells (citation numbers must follow body order,
# so table cells are processed last only for keys already cited; new keys are appended to the reference list above is NOT possible here)
for t in doc.tables:
    for row in t.rows:
        for c in row.cells:
            for par in c.paragraphs:
                for r in par.runs:
                    if "<<" in r.text:
                        def rep(m):
                            ks = [k.strip() for k in m.group(1).split(",")]
                            return "[" + ", ".join(str(ORDER.index(k) + 1) for k in ks) + "]"
                        r.text = re.sub(r"<<([^>]+)>>", rep, r.text)
out = H / "IEEE_Journal_Manuscript.docx"; doc.save(out)
print("saved", out, "refs:", len(ORDER), "figures:", counters["fig"], "tables:", counters["tab"])
unused = set(ENT) - set(ORDER); print("bib entries not cited:", sorted(unused))
