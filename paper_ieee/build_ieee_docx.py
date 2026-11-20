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
def one_col():
    s = doc.add_section(WD_SECTION.CONTINUOUS); set_cols(s, 1); return s
def two_col():
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
    avail = 7.2 if sum(widths) > 3.7 else 3.45
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
p = doc.add_paragraph(); add_runs(p, "Pendyala Archana and Kolikipogu Ramakrishna", 11); fmt(p, AL.CENTER, 0, 2)
p = doc.add_paragraph(); add_runs(p, "Department of Information Technology, Chaitanya Bharathi Institute of Technology (CBIT), Hyderabad, Telangana, India", 9, italic=True); fmt(p, AL.CENTER, 0, 1)
p = doc.add_paragraph(); add_runs(p, "Corresponding author: [CORRESPONDING AUTHOR E-MAIL]", 9); fmt(p, AL.CENTER, 0, 10)

ABS = ("*Abstract*—Extending all-weather road access to dispersed rural hamlets depends on knowing where dwellings are, yet planning still relies on manually digitised building inventories and on connecting each house independently. "
       "This paper presents an end-to-end, open-source pipeline that converts satellite imagery and open geospatial layers into a shared access-road network. It combines a fine-tuned DINOv2 segmenter (StrongDINOv2Seg; 53.8% mIoU, 68.9% Dice and 71.3% pixel accuracy on the LoveDA validation split), marker-controlled distance-transform instance extraction, a 10 m multi-criteria cost surface with a soft building-footprint penalty, and a two-stage planner that selects least-cost route alternatives by marginal cost so that shared corridors are built once. "
       "In the rural village of Damarakunta the plan connects 163 houses and five facilities with 5,069.0 m of unique new corridor, 24.9% less than independent least-cost routes (6,753.1 m). "
       "Re-applied with open Overture Maps footprints, roads and facilities to the Adilabad Urban mandal (urban and peri-urban, 17.75 km^{2}), the same cost surface and solver connect 873 of 874 road-gap houses with 34,358.8 m, 26.0% less than independent routing, whereas a roads-only shared reference saves only 2.9% there against 22.6% in Damarakunta. "
       "Footprint penalties trade corridor length for fewer routes through other dwellings, and simulated building omissions shorten the plan while stranding households, so network length alone is a misleading quality indicator. Costs are ordinal planning units; results are planning alternatives, not engineered alignments.")
p = doc.add_paragraph(); add_runs(p, ABS, 9, bold=False); fmt(p, AL.JUSTIFY, 0, 4, left=0.0)
p = doc.add_paragraph(); add_runs(p, "*Index Terms*—Building footprint extraction, DINOv2, least-cost path, open geospatial data, rural roads, shared network, spatial transferability, Telangana.", 9); fmt(p, AL.JUSTIFY, 0, 6)

two_col()

# =====================================================================  I. INTRODUCTION
H1("Introduction")
P("Road building is among the most consequential land-use changes of the coming decades: global road length is projected to grow by roughly 3.0–4.7 million km by 2050 <<meijer2018global>>, and new roads open land to clearing and fragmentation <<laurance2014global>>. In India the Pradhan Mantri Gram Sadak Yojana (PMGSY) connects habitations through all-weather rural roads <<pmgsy>>. Planning access to individual hamlets needs three inputs: where the dwellings are, what land a corridor must cross, and a rule that turns these into alignments.")
P("Computational support has matured along three separate lines. Remote sensing maps buildings and roads at scale, from continental building inventories <<sirko2021openbuildings>> to foundation-model segmenters <<oquab2023dinov2>>, with recent work on small rural buildings, uncertainty and domain shift <<r62,r63,r64,r65,r66,r67,r68,r69,r70>>. Multi-criteria and least-cost analysis converts terrain and land cover into route cost <<r06,r53,r54,collischonn2000lcp>>. Network-design formulations connect many demand points at low total cost, including Steiner-tree heuristics <<kou1981steiner,mehlhorn1988steiner,hwang1992steiner,r51>>, rural road design models <<r41,r42,r43,r44>> and analogues for power and transport networks <<r45,r46,r47,r50>>. These lines are rarely joined: detectors are judged by pixel overlap <<r01>>, planners assume an error-free inventory, and each house is often connected independently, so neighbouring houses re-trace the same corridor.")
P("This paper joins them in one reproducible pipeline and tests it at two settlement densities. The contributions are:")
BUL(["**End-to-end pipeline.** StrongDINOv2Seg segmentation, OpenCV/NumPy instance extraction with an explicit merge flag and facility verification, a multi-criteria cost surface with a footprint penalty, and a two-stage shared-network planner (Section IV).",
     "**Error propagation.** Controlled omission and addition scenarios that propagate building-inventory errors through the planner and measure their effect on unique length, coverage and exposure of dwellings (Sections V-B to V-D).",
     "**Multi-settlement spatial transferability and open-data scalability.** The rural Damarakunta workflow is re-applied, with the same cost-surface definition and solver, to the Adilabad Urban mandal (urban and peri-urban) using open Overture Maps footprints, roads and facilities and a road-gap rule for targets, with robustness examined over penalty settings, road-gap thresholds and synthetic omissions (Section V-E)."])
P("Two scope limits apply. Only these two settlements were evaluated; a semi-urban and a second rural window are planned but not yet run, so no rural–semi-urban–urban gradient is claimed. And in Adilabad the footprints are open map data rather than StrongDINOv2Seg output, so the transfer tested is that of the planning stages, not of the segmenter.")

# =====================================================================  II. RELATED WORK
H1("Related Work")
P("*Building and road extraction.* Reviews of building extraction <<r01>> document the shift from fully convolutional networks <<ji2019whu>> to transformer and foundation-model encoders. Recent studies address isolated small buildings <<r63>>, weak supervision <<r62>>, uncertainty-guided refinement <<r64,r65>> and domain generalisation across imagery sources <<r02,r66,r67,r68,r69,r70>>. Road extraction has followed the same path with width-adaptive, topology-preserving and foundation-model-based networks <<r56,r57,r58,r59,r60>>, and topological analysis has been used to detect informal settlements <<r48>>. Evaluation is overwhelmingly through overlap scores <<foody2002status>>; the effect of detection errors on downstream infrastructure decisions is rarely quantified, although error propagation in GIS models is long established <<heuvelink1998error>>.")
P("*Route and network planning.* Multi-criteria GIS analysis <<r06>> and least-cost paths <<collischonn2000lcp,r53,r54>> underlie corridor selection, with treatments of slope <<r54>>, alternative routes <<r53>> and travel-time uncertainty <<r61>>; GIS route reconstruction has also been applied to historical transport routes <<r55>>. Rural road design has been addressed with improved network-design models <<r41>>, ant-colony optimisation <<r42>>, algorithmic planning under constrained capacities in India <<r43>> and facility-based methodology <<r44>>. Steiner-tree formulations <<hwang1992steiner>> and their shortest-path heuristics <<kou1981steiner,mehlhorn1988steiner>> are applied to sub-network identification <<r51>>, multi-terminal routing <<r52>>, cable routing <<r45>>, minimum spanning trees of road networks <<r46>>, rural grids <<r47>> and least-cost electrification <<r50>>.")
P("*Gap.* To our knowledge no cited work combines (i) satellite-derived building instances, (ii) a land-cover- and slope-based cost surface with building avoidance, (iii) a shared-network planner whose marginal cost credits built corridors, and (iv) a systematic test of how inventory omissions and the settlement setting change the result.")

# =====================================================================  III. STUDY AREAS AND DATA
H1("Study Areas and Data")
H2("Damarakunta (rural)")
P("Damarakunta is a rural revenue village in Markook mandal, Siddipet district, Telangana (≈17.707°N, 78.753°E). Its boundary, from the Telangana State Remote Sensing Application Centre (TGRAC), encloses 18.47 km^{2} (UTM zone 44N, EPSG:32644). Settlement is dispersed: houses form small clusters separated by farmland (Fig. 1). A 0.6 m three-band mosaic (11,296 × 7,171 px) was assembled from Esri World Imagery exports. Building candidates are model outputs: 278 polygons, 165 inside the boundary, of which 163 are routing targets. Each carries a quality class: Plausible (71), Review (32) and Unresolved_Merge (62), the last denoting blobs that merge adjacent roofs and could not be split. Five TGRAC facilities (schools, a health sub-centre and the gram-panchayat headquarters points) are planned in a separate phase. A TGRAC anganwadi record was excluded because its coordinate lies about 371 m from the nearest footprint and was judged unsupported; its true location remains to be verified. No ground-truth building mask exists for Damarakunta.")
FIGURE("fig2_study_area.png", "Damarakunta. (a) Boundary, TGRAC roads and detected footprints by quality class, with the five facilities. (b) Main settlement. Footprints are automatic detections, not a census; no imagery basemap is shown because the imagery licence for derived products is unresolved.", 3.4)
H2("Adilabad Urban (urban and peri-urban)")
P("The second window is the Adilabad Urban mandal, Adilabad district (geoBoundaries ADM3 polygon <<runfola2020geoboundaries>>; centroid 19.682°N, 78.528°E), 17.75 km^{2}, close to Damarakunta in area. Its 10 m grid has 424 × 564 cells, 177,533 of them inside the polygon and 0.62% blocked (water or slope above 25°). About 60% of cells are not WorldCover built-up, so the window holds an urban core and a peri-urban fringe. The boundary is the 2018 release and may differ from current municipal limits.")
P("All Adilabad layers are open (Table I). Overture release 2026-10-21.0 <<overture2026>> supplies 4,850 road segments, 24,924 building polygons (18,846 from OpenStreetMap and 6,078 from Google Open Buildings v3 <<sirko2021openbuildings>>) and 738 places. Footprints with area ≥ 30 m^{2} and confidence ≥ 0.7 (18,242 polygons) form the penalty layer. Of 107 school, health and government place candidates, 83 fall inside the window and 71 are verified (44 schools, 20 health, 7 government): records with mis-geocoded foreign place names were removed manually and a footprint within 20 m of the point was required. StrongDINOv2Seg was **not** run on Adilabad: the weights' location was not recorded, the Esri imagery licence for derived products is unresolved and no open sub-metre imagery was available. The Adilabad building layer is therefore open map data, not model output, and has not been field-verified.")

TABLE("Input data and licence status",
      ["Layer", "Damarakunta / Adilabad source", "Licence status"],
      [["Boundary", "TGRAC / geoBoundaries ADM3", "Not stated / ODbL 1.0"],
       ["Roads, facilities", "TGRAC (43 road features, 5 facilities) / Overture 2026-10-21.0", "Not stated / ODbL 1.0 (roads), CDLA-Permissive-2.0 (places); not re-verified"],
       ["Buildings", "StrongDINOv2Seg candidates (0.6 m Esri imagery) / Overture footprints (OSM, Google Open Buildings v3)", "Imagery licence for derived products unresolved / ODbL 1.0 and CC BY 4.0; not re-verified"],
       ["Land cover", "ESA WorldCover v200, 10 m <<zanaga2021worldcover>>", "CC BY 4.0"],
       ["Terrain", "~30 m DEM (source not recorded) / Copernicus GLO-30 <<esa2022copdem>>; Sobel slope, bilinear to 10 m", "Not stated / as stated by provider"],
       ["Training data", "LoveDA <<wang2021loveda>>", "Source domain only"]],
      [0.75, 1.55, 1.2], size=7.5)
# table cells contain <<>> markers: handled below by a post-pass

# =====================================================================  IV. METHODOLOGY
H1("Methodology")
P("Fig. 2 summarises the architecture. The two settlements differ in the perception and target stages and share the cost surface, planner and evaluation stages.")
H2("Semantic segmentation: StrongDINOv2Seg")
P("StrongDINOv2Seg uses the pre-trained facebook/dinov2-base encoder (DINOv2 ViT-B/14 <<oquab2023dinov2>>), fully fine-tuned. Tokens from transformer blocks 3, 6, 9 and 12 are projected to 256 channels and fused in a feature-pyramid manner <<lin2017fpn>>, passed through an atrous spatial pyramid pooling neck with rates 6, 12 and 18 <<chen2018deeplabv3plus>> and a four-stage residual decoder with auxiliary heads for deep supervision <<lee2015dsn>>. Training on LoveDA <<wang2021loveda>> used 560 px inputs for a scheduled 10 epochs with AdamW, a cosine learning-rate schedule to 10^{-7}, an encoder learning rate of 0.1 times the base rate, and the loss 0.5·CE + 0.4·Dice + 0.1·edge <<milletari2016vnet>> with auxiliary weight 0.4. The epoch-4 checkpoint was evaluated and used.")
H2("Instance extraction and facility verification")
P("Building instances are extracted from the predicted mask with OpenCV and NumPy. For each connected component, a Euclidean distance transform is computed; h-maxima, obtained by iterative morphological reconstruction with a 3 × 3 dilation, give one marker per candidate roof; a priority-driven marker-controlled flooding of the distance transform (a watershed-type transform) assigns pixels to markers; and adjacent pieces are merged back unless the saddle height between them is below 0.65 of the lower peak (neck test) and each piece exceeds a minimum area. Components that cannot be split reliably are flagged Unresolved_Merge, and the remaining polygons are labelled Plausible or Review by size and shape rules. Facilities are accepted as targets only if they lie inside the boundary and have a detected footprint within 20 m of the recorded point; the same rule is applied to Overture places in Adilabad, together with manual removal of mis-geocoded records.")
H2("Open-data mode and road-gap targets")
P("For Adilabad, Overture footprints replace the segmenter output. Because connecting every footprint is meaningless in a built-up fabric already served by roads, only houses more than 30 m (the planner snap distance) from an existing road are routed. Planner cost grows roughly quadratically with the number of targets, which further motivates the filter; the threshold is varied (20, 30, 50 m) in Section V-E.")
H2("Multi-criteria cost surface")
P("Let *B* be the set of blocked cells (water, invalid cells, slope above 25°) and *P* the set of cells whose centre lies inside a footprint. The graph has the unblocked 10 m cells as nodes and 8-neighbour edges without diagonal corner-cutting. The cell cost is")
EQ("*c*(*x*) = [ *c*_{lc}(ℓ(*x*)) + *g*(*s*(*x*)) ] · *m*(*x*)", 1)
P("where *m*(*x*) = μ if *x* ∈ P and 1 otherwise, ℓ is the ESA WorldCover class <<zanaga2021worldcover>> with resistances 8, 5, 3, 6, 2 and 4 for classes 10 (tree cover), 20 (shrubland), 30 (grassland), 40 (cropland), 50 (built-up) and 60 (bare/sparse), g(s) = 4·clip(s, 0, 10)/10 with s the slope in degrees derived from the DEM <<esa2022copdem>>, and μ = 4 is the footprint penalty. Edge weights are the mean end-cell cost times step length. The 25° slope limit is a project rule, not a transcription of Indian Roads Congress standards, and costs are ordinal planning units, not currency. In Damarakunta the penalty is lifted within a 20 m disc around the health sub-centre, whose point lies on the edge of its own footprint.", first=0)
H2("Two-stage shared-network planner")
P("For each target, Stage A computes a least-cost path to the existing road cells with Dijkstra's algorithm <<dijkstra1959note,hart1968astar,collischonn2000lcp>> and obtains alternatives by inflating costs along earlier paths (K = 3 alternatives in total). Stage B greedily selects the (target, alternative) pair with the highest weight per marginal cost")
EQ("Δ*L*_{cost}(π | *S*) = Σ *w*(*e*),  *e* ∈ π∖*E*_{S}", 2)
P("where *E*_{S} is the set of already selected edges, so built edges are free and a route may end on another route. This is the shortest-path heuristic for Steiner trees <<kou1981steiner,mehlhorn1988steiner>> on a penalised, land-cover-weighted graph with the road network as a free sub-tree; it carries no optimality guarantee. Two leaf re-routing passes follow. Snap distance is 30 m, search limit 1,500 m and attachment tolerance 15 m. Facilities are planned in a separate phase (script plan_network_v2.py).", first=0)
H2("Baselines, scenarios and metrics")
P("Four baselines are compared: straight lines, independent least-cost routes, a length-only control (distance instead of cost surface) and a roads-only shared reference (routes may share edges only with the existing road network). The saving against independent routing is ρ = (*L*_{ind} − *L*)/*L*_{ind}, with *L* the unique network length (shared edges counted once). Exposure is measured by the number of routes crossing another house's footprint and the route length inside other footprints. The footprint penalty is varied (μ ∈ {1, 4, 20, 100}, with a variant in which footprints are buffered by 7.1 m). For omissions, a target set *M* is removed from the targets and from the penalty layer (a missed detection is absent from both) and the planner re-run; random draws use seeds 1–5. Reported are coverage, unserved households, change in unique length and length per routed target. No monetary cost is computed: the repository holds no rupee-denominated estimates, and the PMGSY scheme <<pmgsy>> is used only as planning context.")

# wide figure: architecture
one_col()
FIGURE("fig_architecture.png", "System architecture. Inputs feed a perception stage (Damarakunta: segmentation and instance extraction; Adilabad: open footprints enter the target stage directly with the road-gap filter), a shared cost surface, a two-stage shared-network planner and an evaluation stage that includes the cross-settlement transfer.", 7.1)
two_col()

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
P("The penalty trades length for exposure (Fig. 3). With μ = 1 the plan is shortest (4,705.4 m) but 56 routes pass through other houses (660.1 m inside footprints). With μ = 4 it is 7.7% longer while crossings halve to 28 routes and 209.1 m. Buffering footprints by 7.1 m with μ = 20 or 100 lowers crossings to 19 routes at 6,238.1 m and 6,190.3 m.")
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
P("Table IV and Fig. 4 give the omission analysis against the 5,069.0 m baseline. Missing buildings make the plan *shorter*: 10% random omission (16 houses) understates length by 7.6%, 20% by 16.9%, omission of the smallest quarter by 25.1% and omission of all merged blobs by 29.4%. At the same time U households lose access: 16 and 33 for random 10% and 20% omission, 41 for the smallest quarter and 62 (38.0%) for merged blobs. A planner reading only total length would therefore underfund the scheme. Random additions lengthen the plan by 8.6% and 15.8%. The saving ρ stays within 24.9–26.6% across omissions, so the benefit of sharing is robust to inventory error.")
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
P("Of 18,242 penalty-layer footprints, 874 (4.8%) lie more than 30 m from a road and form the targets; their median footprint is 139.6 m^{2} and median distance to the nearest road 42.3 m (Damarakunta: 235.8 m^{2} and 27.7 m). The planner routes 873 of 874. Independent least-cost routes total 56,308.0 m (unique 46,419.2 m); the two-stage plan needs 34,358.8 m, a saving of 26.0% (Table V, Fig. 5). The facility phase connects 71 verified facilities with 1,090.1 m of unique corridor.")
P("The baselines behave differently from the rural case. The roads-only shared reference saves just 2.9% (22.6% in Damarakunta) and the length-only control 5.7% (−3.4% in Damarakunta). In the dense fabric, targets are scattered among many existing roads, so sharing among *new* routes accounts for almost all the gain, whereas in the dispersed village a trunk-and-branch structure off existing roads already captures most of it. Exposure is much higher: 332 of 873 routes (38%) cross another footprint (2,041.1 m) against 28 of 163 (17%) in Damarakunta.")
one_col()
TABLE("Cross-settlement comparison under the same cost surface and solver",
      ["Metric", "Damarakunta (rural)", "Adilabad (urban/peri-urban)"],
      [["Study area (km^{2})", "18.47", "17.75"],
       ["House targets / routed", "163 / 163", "874 / 873"],
       ["Independent routes, unique length (m)", "6,753.1", "46,419.2"],
       ["Length-only control, unique (m)", "6,979.8", "43,787.2"],
       ["Roads-only shared reference, unique (m)", "5,229.3", "45,058.9"],
       ["**Two-stage plan, unique (m)**", "**5,069.0**", "**34,358.8**"],
       ["Saving vs. independent (%)", "24.9", "26.0"],
       ["Roads-only shared saving (%)", "22.6", "2.9"],
       ["Unique length per routed house (m)", "31.1", "39.4"],
       ["Routes crossing other footprints", "28 of 163 (17%)", "332 of 873 (38%)"],
       ["Length inside other footprints (m)", "209.1", "2,041.1"],
       ["μ = 1 → 4: unique length change (%)", "+7.7", "+13.3"],
       ["μ = 1 → 4: routes crossing", "56 → 28", "618 → 332"],
       ["Facility phase: facilities / unique length (m)", "5 / 249.3", "71 / 1,090.1"],
       ["10% random omission: length change (%) / unserved", "−7.6 / 16 of 163", "−7.6 / 88 of 874"],
       ["20% random omission: length change (%) / unserved", "−16.9 / 33 of 163", "−15.0 / 176 of 874"],
       ["Smallest-25% omission: length change (%) / unserved", "−25.1 / 41 of 163", "−21.2 / 220 of 874"]],
      [3.6, 1.7, 1.8], size=8)
FIGURE("adilabad_map2_network_comparison.png", "Adilabad Urban route comparison for 874 road-gap houses (μ = 4): (a) independent least-cost routes, (b) two-stage shared plan, (c), (d) zoom on the densest road-gap cluster. Planning alternatives, not engineered roads; the basemap shows land cover and footprints only.", 7.1)
two_col()
H2("Adilabad robustness")
P("*Footprint penalty.* As in Damarakunta, raising μ from 1 to 4 lengthens the unique network by 13.3% and removes 286 crossing routes (618 to 332). Settings μ = 20 and 100 give 37,024.1 m and 37,513.9 m with 271 and 275 routes crossing; buffered footprints give 42,071.9 m and 44,094.6 m with 231 and 221 crossing (Table VI, Fig. 6a). The saving against independent routing stays between 17.8% and 30.8% across all settings.")
P("*Road-gap threshold.* Defining targets as houses more than 20, 30 or 50 m from a road gives 2,190, 874 and 296 targets and savings of 21.9%, 26.0% and 29.5%. The saving therefore depends on the target definition, which should be reported with any such result.")
P("*Omissions.* Random omission of 10% and 20% (five seeds) changes unique length by −7.6% (range −8.9 to −6.7) and −15.0% (−16.1 to −13.9), with 88 and 176 households unserved including one baseline failure; single-run smallest-10% and smallest-25% omissions give −7.9% and −21.2% (89 and 220 unserved). As in Damarakunta, missing buildings shorten the plan while stranding households, and the saving stays at 23.8–25.2%. Merged-blob and addition scenarios were not defined for the open footprints.")
TABLE("Adilabad sensitivity (874 targets unless stated)",
      ["Setting", "Unique (m)", "ρ (%)", "Cross.", "In fp. (m)"],
      [["Centre-in-footprint, μ = 1", "30,335.7", "30.8", "618", "4,893.0"],
       ["Centre-in-footprint, μ = 4", "34,358.8", "26.0", "332", "2,041.1"],
       ["Centre-in-footprint, μ = 20", "37,024.1", "22.8", "271", "1,687.4"],
       ["Centre-in-footprint, μ = 100", "37,513.9", "21.7", "275", "1,744.8"],
       ["Buffered 7.1 m, μ = 20", "42,071.9", "20.1", "231", "1,397.2"],
       ["Buffered 7.1 m, μ = 100", "44,094.6", "17.8", "221", "1,310.5"],
       ["Road-gap > 20 m (2,190 targets)", "65,204.4", "21.9", "815", "4,543.9"],
       ["Road-gap > 30 m (874, primary)", "34,358.8", "26.0", "332", "2,041.1"],
       ["Road-gap > 50 m (296 targets)", "15,880.9", "29.5", "126", "809.9"]],
      [1.5, 0.6, 0.4, 0.4, 0.55], size=7.5)
one_col()
FIGURE("adilabad_fig3_sensitivity.png", "Adilabad sensitivity. (a) Footprint-penalty trade-off between unique network length and route length inside other footprints. (b) Omission sensitivity (random: mean and min–max over five seeds; smallest-q: single run).", 6.2)
two_col()

# =====================================================================  VI. DISCUSSION
H1("Discussion and Limitations")
H2("What transfers and what does not")
P("The planning stages transferred without modification: the same cost surface, solver parameters and metrics produced a connected plan in a window with more than five times as many targets (874 against 163), and the qualitative findings were reproduced: sharing saves about a quarter of the unique length (24.9% and 26.0%), the footprint penalty trades length for exposure, and omissions shorten the plan while stranding households. What did not transfer is the benefit of the simpler baselines: roads-only sharing recovered most of the gain in the dispersed village but almost none in the dense one. This suggests that the value of a marginal-cost planner grows with settlement density, a hypothesis supported by two settlements only. The effect of detection quality across settings could not be tested because Adilabad uses open map footprints.")
H2("Why pixel metrics are not enough")
P("Segmentation metrics are area-weighted over classes, while the planner counts instances. A detector that misses the smallest quarter of buildings can lose few building pixels yet removes a quarter of the households from the plan (Table IV), and a detector that merges adjacent roofs can score a high pixel IoU yet strand 38% of Damarakunta's houses in the merged-blob scenario. Network length falls in both cases, so total length is a poor quality indicator.")
H2("Land take and planning use")
P("Shared corridors reduce new road length for the same households. As an illustration only, assuming a 5 m formation width (an assumption of this study; no road-width data were available), the 1,684 m saved in Damarakunta corresponds to about 0.84 ha less land take and the 12,060 m saved in Adilabad to about 6.0 ha. For PMGSY-style schemes <<pmgsy>>, building inventories should be treated as uncertain inputs, with a sensitivity band on any network sized from them. The outputs are screening-level alternatives; no compliance with Indian Roads Congress design standards and no cost in rupees is claimed.")
H2("Limitations")
P("(i) Two settlements only; the semi-urban and second rural windows are planned but not run. (ii) Omission scenarios are synthetic, not measured detection errors. (iii) Damarakunta has no surveyed reference; the LoveDA metrics come from the epoch-4 checkpoint with metadata recovered from the training notebook, and the checkpoint hash was not logged with the village candidates. (iv) Adilabad footprints are open map data of unverified completeness and the Overture licences were not re-verified. (v) Costs are ordinal, the planner is a heuristic without an optimality guarantee, and road-gap targeting changes the problem, as the threshold sweep shows. (vi) Pixel accuracy is reported as 71.3%, the value recomputed from the confusion matrix.")

# =====================================================================  VII. CONCLUSION
H1("Conclusion")
P("A pipeline from satellite imagery and open layers to shared access roads connects the houses and facilities of a rural village with 24.9% less unique corridor than independent routing and, without changes to the cost surface or solver, those of an urban and peri-urban mandal with 26.0% less. Footprint penalties and simulated inventory errors behave consistently in both settings: penalties trade length for fewer routes through dwellings, and omissions shorten the plan while stranding households. The dependence of the roads-only baseline on settlement density and the effect of detection quality across settings are the main open questions; a semi-urban and a second rural window are planned to address the first.")
H1u("Acknowledgment")
P("The authors acknowledge the Telangana State Remote Sensing Application Centre (TGRAC) for the Damarakunta boundary, road and facility layers, and the providers of the open datasets used (ESA WorldCover, Copernicus DEM, Overture Maps, geoBoundaries, Google Open Buildings, LoveDA). This research received no specific grant from any funding agency in the public, commercial, or not-for-profit sectors. The authors declare no competing interests.")
H1u("Data Availability")
P("Code, derived summary tables and open-data manifests with SHA-256 hashes are available at https://github.com/Archana519/Telangana-Rural-Project (folders DELIVERABLES_DAMARAKUNTA_STAGE_B and DELIVERABLES_CONTRIBUTION_3_MULTI_VILLAGE). TGRAC layers are subject to the provider's terms; Esri imagery is not redistributed. A Zenodo DOI will be added when the archive is minted.")
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
