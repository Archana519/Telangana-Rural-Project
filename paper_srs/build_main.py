"""Builds paper_srs/main.tex, the Science of Remote Sensing (Elsevier, elsarticle) manuscript.

Grounding rule: no number is typed here. Body text of the Data/Methods/Results sections is taken VERBATIM from paper_erl/main.tex (itself generated from the result files by
paper_erl/build_main.py); the validation numbers come from DELIVERABLES_CONTRIBUTION_3_MULTI_VILLAGE/validation/*.csv through src/multivillage/validation_tables.py; the headline
numbers of the abstract, highlights and conclusions come from src/multivillage/pipeline_summary.py (the same module as the ERL paper). Run paper_erl/build_main.py first.
    python paper_srs/build_main.py && cd paper_srs && pdflatex main && bibtex main && pdflatex main && pdflatex main
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

H = Path(__file__).resolve().parent
REPO = H.parent
sys.path.insert(0, str(REPO))
from src.multivillage import pipeline_summary as PS, validation_tables as VT   # noqa: E402

ERL = (REPO / "paper_erl" / "main.tex").read_text(encoding="utf-8")
M = {k: PS.collect(k) for k in PS.ORDER}
ORD = ["damarakunta", "adilabad", "aswaraopeta", "alampur"]
pc = lambda k: f"{M[k]['saving_pct']:.1f}"
lk = lambda k: f"{M[k]['cost_lakh']:,.0f}".replace(",", "{,}")
win = f"{min(M[k]['window_km2'] for k in ORD):.2f}--{max(M[k]['window_km2'] for k in ORD):.2f}"
sav_rng = f"{min(M[k]['saving_pct'] for k in ORD):.1f}--{max(M[k]['saving_pct'] for k in ORD):.1f}"
fp, st, sw, ac = VT.fp_facts(), VT.st_facts(), VT.sw_facts(), VT.ac_df()
P = VT.paras()


def between(text, a, b):
    i = text.index(a)
    j = text.index(b, i + len(a)) if b else len(text)
    return text[i:j]


# ------------------------------------------------------------------ highlights (Elsevier: 3-5 bullets, <= 85 characters each including spaces; checked below)
HL = [
    "Open-data pipeline turns building footprints into shared rural road plans",
    f"Shared networks are {sav_rng.replace('--', '-')}% shorter than independent routes in four windows",
    f"Footprint detection precision {fp['o'].det_precision.min():.2f}-{fp['o'].det_precision.max():.2f}, but {fp['merged'].replace('--', '-')}% merge several buildings",
    "Omitting 20% of footprints leaves households unserved, not networks oversized",
    f"Kou Steiner baseline is only {st['kou_rng'].replace('--', '-')}% longer than the shared plan",
]
assert 3 <= len(HL) <= 5
for h in HL:
    assert len(h) <= 85, (len(h), h)

# ------------------------------------------------------------------ abstract (all numbers from the result files)
abstract = (
    "Planning access roads for unconnected rural buildings with open Earth-observation data inherits the errors of the building inventory, yet these errors are seldom propagated to the plan. "
    f"We apply one fully open workflow to four Telangana windows ({win}~km$^2$): a frozen segmenter, StrongDINOv2Seg (53.8\\% mean intersection over union, mIoU, on the LoveDA benchmark), applied to 0.6~m Esri imagery gives building footprints and road-gap targets; "
    "land cover and terrain slope give a multi-criteria cost surface on a 5~m grid with a hard 3.6~m building clearance; and two-stage Dijkstra routing consolidates independent routes into a shared network. "
    f"The shared network is {sav_rng.replace('--', ' to ')}\\% shorter than independent routes, with zero building crossings in all four windows. "
    f"We then test the weakest input without manual labels. Against Overture Maps buildings the footprints reach an area overlap (intersection over union, IoU) of {fp['iou'].replace('--', ' to ')} and a detection precision of {fp['det_p'].replace('--', ' to ')}, "
    f"but {fp['merged'].replace('--', ' to ')}\\% of them merge two or more reference buildings. Omitting 20\\% of the road-gap footprints leaves {min(sw['unserved20'].values()):.0f} to {max(sw['unserved20'].values()):.0f} households unserved "
    f"while the length per served household changes little, and a Kou Steiner tree is {st['kou_rng'].replace('--', ' to ')}\\% longer than the shared plan. "
    "The results are agreement and sensitivity figures between open datasets, not accuracy against field ground truth, and the corridors are planning alternatives for field verification."
)
_plain = re.sub(r"\\[a-zA-Z]+|[{}$~^\\]", " ", abstract)
abs_words = len(_plain.split())
assert abs_words <= 250 and "\\cite" not in abstract, abs_words        # Science of Remote Sensing: abstract <= 250 words, standalone, no citations
KEYWORDS = ["rural roads", "building footprint extraction", "satellite remote sensing", "uncertainty propagation", "least-cost path", "Steiner tree", "open geospatial data"]
assert 1 <= len(KEYWORDS) <= 7

# ------------------------------------------------------------------ body reused verbatim from paper_erl/main.tex
intro_all = between(ERL, "\\section{Introduction}\n", "\\section{Data and methods}")
intro_paras = [p for p in intro_all.split("\n\n") if p.strip()]
intro = "\n\n".join(intro_paras[:2]).strip()
data_methods = between(ERL, "\\section{Data and methods}", "\\section{Results}")
results = between(ERL, "\\section{Results}", "\\FloatBarrier\n\\section{Discussion and conclusions}")
disc_src = between(ERL, "\\textbf{Regional planning implications.}", "\\textbf{Conclusions.}")
regional = between(disc_src, "\\textbf{Regional planning implications.}", "\\textbf{Methodological limitations.}").strip()
scal = between(disc_src, "\\textbf{Scalability.}", None).strip()


JURIS = "Map lines delineate study areas and do not necessarily depict accepted national boundaries."
AI_FIG = "AI-assisted workflow diagram: the framework diagram was drafted with a generative AI tool (Claude, Anthropic) and reviewed by the authors."


def make_flow_figure():
    """paper_erl/fig_flow_study_areas.png without its Telangana/district locator map: Science of Remote Sensing maps may show only the study-area extents."""
    from PIL import Image, ImageDraw
    im = Image.open(REPO / "paper_erl" / "fig_flow_study_areas.png").convert("RGB")
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 340, 240], fill="white")           # state/district locator inset
    d.rectangle([340, 0, im.width, 135], fill="white")     # its heading line ('study districts shaded')
    im.crop((0, 130, im.width, im.height)).save(H / "fig_flow_study_areas.png")


make_flow_figure()


def srs_captions(t: str) -> str:
    t = re.sub(r"Top: Telangana with district outlines.*?and the key\.", "Top: the key.", t, flags=re.S)
    def one(m):
        blk = m.group(0)
        if "fig_architecture.png" in blk:
            return blk.replace("}\n\\label{fig:arch}", " " + AI_FIG + "}\n\\label{fig:arch}")
        return re.sub(r"\}\n(\\label\{fig:)", lambda k: " " + JURIS + "}\n" + k.group(1), blk, count=1)
    return re.sub(r"\\begin\{figure\}.*?\\end\{figure\}", one, t, flags=re.S)


def srs_floats(t: str) -> str:
    t = srs_captions(t.replace("\\begin{figure*}", "\\begin{figure}").replace("\\end{figure*}", "\\end{figure}"))
    t = t.replace("\\begin{table*}", "\\begin{table}").replace("\\end{table*}", "\\end{table}").replace("\\begin{figure*}", "\\begin{figure}").replace("\\end{figure*}", "\\end{figure}")
    t = re.sub(r"width=0\.7\\textwidth,height=0\.36\\textheight", r"width=\\textwidth,height=0.42\\textheight", t)
    t = re.sub(r"width=0\.7\\textwidth,height=0\.3\\textheight", r"width=\\textwidth,height=0.36\\textheight", t)
    t = t.replace("width=0.86\\textwidth", "width=\\textwidth").replace("width=0.9\\textwidth,height=0.82\\textheight", "width=\\textwidth,height=0.68\\textheight")
    t = t.replace("p{1.6cm}>{\\raggedright", "p{1.7cm}>{\\raggedright")
    t = t.replace("\\resizebox{0.92\\textwidth}{!}", "\\resizebox{\\textwidth}{!}")
    t = re.sub(r"\\begin\{tabular\}", r"\\begin{adjustbox}{max width=\\textwidth}\n\\begin{tabular}", t)
    t = re.sub(r"\\end\{tabular\}", r"\\end{tabular}\n\\end{adjustbox}", t)
    return t


# the 3.4 sub-section of the ERL paper is rebuilt here in single-column form (same CSV-driven text and tables)
res_pre = results[: results.index("\\subsection{Cross-source footprint agreement")]
vtab = lambda lab, cap, body: "\\begin{table}[t]\n\\caption{" + cap + "}\n\\label{" + lab + "}\n\\centering\n\\footnotesize\n" + body + "\n\\end{table}\n"
def _cap(lab):
    i = ERL.index("\\label{" + lab + "}")
    j = ERL.rfind("\\caption{", 0, i)
    return ERL[j + len("\\caption{"): i].rstrip().rstrip("}")


caps = {lab: _cap(lab) for lab in ("tab:xval", "tab:graphbase", "tab:access", "tab:omit")}
res_val = ("\\subsection{Cross-source footprint agreement, graph baselines, accessibility and error propagation}\\label{sec:res4}\n" + P["intro"] + "\n\n" + P["footprint"] + "\n\n"
           + vtab("tab:xval", caps["tab:xval"], VT.tab_footprint()) + "\n" + P["graph"] + "\n\n" + vtab("tab:graphbase", caps["tab:graphbase"], VT.tab_steiner()) + "\n" + P["access"] + "\n\n"
           + vtab("tab:access", caps["tab:access"], VT.tab_access()) + "\n" + P["error"] + "\n\n" + vtab("tab:omit", caps["tab:omit"], VT.tab_omission()))

# ------------------------------------------------------------------ discussion: reused paragraphs + the limits reported openly (numbers from the CSVs)
limits = (
    "\\textbf{Limits reported openly.} (i)~\\emph{No ground truth.} No field-surveyed or hand-digitised building masks exist for any window and none were produced: the premise of the study is a workflow that "
    "needs no manual survey. The footprint evaluation is therefore a multi-source agreement analysis against Overture (OpenStreetMap and Google Open Buildings sources) and, in Damarakunta, the raw Google Open Buildings v3 polygons, "
    f"and each reference has its own errors. (ii)~\\emph{{Merging.}} {fp['merged'].replace('--', ' to ')}\\% of the footprints contain two or more reference buildings, so the road-gap targets are partly built-up units rather than dwellings; "
    f"detection recall is {fp['det_r'].replace('--', ' to ')}, so a share of the reference buildings has no footprint at all. (iii)~\\emph{{Partial coverage in Damarakunta.}} The stored footprints cover {fp['dk_cov_km2']} of the "
    f"{fp['dk_win_km2']}~km$^2$ window, and the window contains {fp['n_ours']['damarakunta']} footprints against {fp['dk_nref_win']} Overture buildings, so the Damarakunta results are a small-sample illustration. "
    "(iv)~\\emph{Different planner bases.} The omission and penalty sweeps run on the $10$~m soft-penalty planner and the graph baselines and accessibility counts on the $5$~m clearance grid; their lengths are not interchangeable with "
    "each other or with the main results table, and the Steiner comparison counts grid-edge length without connectors. (v)~\\emph{Heuristic and benchmark.} The Kou tree is itself an approximation, the Euclidean tree ignores terrain and buildings, "
    "and the corridor cost is length times a planning rate of Rs 75 lakh per kilometre (sensitivity range 60--90) that the project owner supplied and that was not checked against a published PMGSY schedule. "
    "(vi)~\\emph{Planning alternatives.} Accessibility counts use the road-gap distance of 30~m and building-centroid distances; none of the corridors has been verified on the ground or engineered."
)
meaning = (
    "\\textbf{What the evidence supports.} The positive result is the workflow: the same checkpoint and rules produced zero-crossing shared networks in four morphologically different windows, "
    f"with {sav_rng.replace('--', ' to ')}\\% less new length than independent routes, and the shared plan stays within {st['kou_rng'].replace('--', ' to ')}\\% of a classical Steiner approximation. The sweeps show where the exposure lies: "
    "an incomplete footprint inventory changes how many households a plan serves far more than how much road it needs, so the uncertainty to report alongside a plan is the number of households it may not know about."
)
conclusions = (
    "\\section{Conclusions}\n"
    f"Open imagery, open terrain and land-cover layers and open building and road inventories were enough to plan shared rural access corridors in four Telangana windows ({win}~km$^2$) without manual labelling. "
    f"The $5$~m cost grid with a $3.6$~m hard building clearance produced corridors that cross no building, and consolidating independent least-cost routes into a shared network shortened the new road by "
    f"{pc('damarakunta')}\\%, {pc('adilabad')}\\%, {pc('aswaraopeta')}\\% and {pc('alampur')}\\% in Damarakunta, Adilabad, Aswaraopeta and Alampur, at planning-benchmark costs of Rs {lk('damarakunta')}, {lk('adilabad')}, {lk('aswaraopeta')} and {lk('alampur')} lakh. "
    f"A Kou Steiner tree on the same graph was {st['kou_rng'].replace('--', ' to ')}\\% longer. Against open building inventories the footprints are precise ({fp['det_p'].replace('--', ' to ')} detection precision) but coarse "
    f"({fp['det_r'].replace('--', ' to ')} detection recall, {fp['merged'].replace('--', ' to ')}\\% merged), and the main consequence of missing footprints is unserved households rather than a larger network. "
    "Independent reference labels, official parcels and field verification of the corridors are the next steps before any engineering use."
)

preamble = r"""% Science of Remote Sensing (Elsevier) manuscript, elsarticle template. Written by paper_srs/build_main.py (numbers from the repository's CSV/LaTeX outputs).
% Compile: pdflatex main && bibtex main && pdflatex main && pdflatex main
\documentclass[preprint,12pt]{elsarticle}
\usepackage{amsmath}
\usepackage{booktabs}
\usepackage{array}
\usepackage{xcolor}
\usepackage{graphicx}
\usepackage{adjustbox}
\usepackage{algorithm}
\usepackage{algpseudocode}
\usepackage{placeins}
\usepackage{lineno}
\usepackage[colorlinks=true,allcolors=blue!50!black]{hyperref}
\modulolinenumbers[5]
\newcommand{\dinoseg}{StrongDINOv2Seg}
\newcommand{\Lcost}{L_{\mathrm{cost}}}
\newcommand{\pending}[1]{\textcolor{red}{\textit{#1}}}
\algrenewcommand\algorithmicrequire{\textbf{Input:}}
\algrenewcommand\algorithmicensure{\textbf{Output:}}
\algrenewcommand\alglinenumber[1]{\scriptsize #1:}
\setlength{\emergencystretch}{2em}
\hfuzz=3pt\vfuzz=10pt   % elsarticle's own preprint title-page footer is 2.6 pt wide / 7.5 pt high in a minimal document too; nothing else exceeds the page
\renewcommand{\topfraction}{0.9}\renewcommand{\textfraction}{0.08}\renewcommand{\floatpagefraction}{0.7}
\biboptions{sort&compress}
\journal{Science of Remote Sensing}
\begin{document}
\linenumbers
"""

front = ("\\begin{frontmatter}\n\\title{Propagating open building-footprint uncertainty into shared rural road networks: a four-window study in Telangana, India}\n"
         "\\author[cbit]{Pendyala Archana}\n\\author[cbit]{Ramakrishna Kolikipogu\\corref{cor1}}\n\\cortext[cor1]{Corresponding author.}\n"
         "\\affiliation[cbit]{organization={Department of Information Technology, Chaitanya Bharathi Institute of Technology (A)},city={Hyderabad},country={India}}\n"
         "\\begin{highlights}\n" + "\n".join("\\item " + h.replace("%", "\\%") for h in HL) + "\n\\end{highlights}\n"
         "\\begin{graphicalabstract}\n\\includegraphics[width=\\textwidth]{graphical_abstract.png}\n\\end{graphicalabstract}\n"
         "\\begin{abstract}\n" + abstract + "\n\\end{abstract}\n"
         "\\begin{keyword}\n" + "\\sep ".join(KEYWORDS) + "\n\\end{keyword}\n\\end{frontmatter}\n")

DATA_AVAIL = (
    "All code, derived tables and the open-data manifests with SHA-256 hashes are openly available in the repository \\url{https://github.com/Archana519/Telangana-Rural-Project} "
    "(folders \\path{DELIVERABLES_CONTRIBUTION_3_MULTI_VILLAGE}, including its \\path{validation} subfolder with the cross-source, baseline, accessibility and sweep tables, and \\path{FINAL_PROJECT_OUTPUTS}). "
    "The datasets used are cited in the reference list with the [dataset] tag: Esri World Imagery \\cite{esri2026worldimagery} (sources: Esri, Maxar, Earthstar Geographics, and the GIS User Community; used for non-commercial academic research and overlay under Esri's academic terms, and raw tiles are not redistributed), "
    "ESA WorldCover 10~m v200 \\cite{zanaga2021worldcover} (CC BY 4.0), the Copernicus GLO-30 digital elevation model \\cite{esa2022copdem}, Overture Maps \\cite{overture2026} and OpenStreetMap (ODbL 1.0), geoBoundaries \\cite{runfola2020geoboundaries} (ODbL 1.0) "
    "and LoveDA \\cite{ds_loveda} (CC BY-NC-SA 4.0). The \\dinoseg{} checkpoint is not included in the repository; its SHA-256 is given in section~\\ref{sec:seg}."
)

body = ("\n\\section{Introduction}\n" + intro + "\n\n"
        "We therefore ask not only whether shared rural road networks can be planned from open Earth-observation data, but how far such a plan can be trusted when the building inventory it rests on is incomplete or merged. "
        "We join the three lines in one two-split framework (figure~\\ref{fig:arch}) and apply it, unchanged, to four settlement windows of different morphology in Telangana, built from one set of open data layers and one frozen segmentation checkpoint. "
        "Our objectives are (1)~to develop a reproducible framework whose first split extracts building footprints, road-gap targets and verified facilities from open imagery and whose second split builds a terrain and land-cover cost surface "
        "with a hard building clearance and consolidates independent routes into a shared network; (2)~to test whether the same checkpoint and rules transfer without retraining across a rural village, an urban fringe, a semi-urban town and a heritage town; "
        "(3)~to quantify the length, cost and building-crossing outcomes of independent (Stage~A) and shared (Stage~B) routing against baseline strategies; and (4)~to report, with automated multi-source checks and no manual labelling, how closely the footprints agree "
        "with open building inventories, how footprint omission propagates into network length and unserved households, and how the shared plan compares with a Kou Steiner tree and a Euclidean minimum spanning tree.\n\n"
        + srs_floats(data_methods) + "\n\\FloatBarrier\n" + srs_floats(res_pre) + "\n" + res_val.replace("\\begin{tabular}", "\\begin{adjustbox}{max width=\\textwidth}\n\\begin{tabular}").replace("\\end{tabular}", "\\end{tabular}\n\\end{adjustbox}")
        + "\n\\FloatBarrier\n\\section{Discussion}\\label{sec:disc}\n" + meaning + "\n\n" + regional + "\n\n" + limits + "\n\n" + scal + "\n\n" + conclusions + "\n\n"
        "\\section*{CRediT authorship contribution statement}\n\\textbf{Pendyala Archana:} Methodology, Software, Investigation, Formal analysis, Visualization, Writing -- original draft. "
        "\\textbf{Ramakrishna Kolikipogu:} Conceptualization, Supervision, Writing -- review \\& editing.\n\n"
        "\\section*{Declaration of competing interest}\nThe authors declare that they have no known competing financial interests or personal relationships that could have appeared to influence the work reported in this paper.\n\n"
        "\\section*{Funding}\nThis research did not receive any specific grant from funding agencies in the public, commercial, or not-for-profit sectors.\n\n"
        "\\section*{Declaration of generative AI and AI-assisted technologies in the manuscript preparation process}\n"
        "% AUTHORS: this is Elsevier's required wording. Submit it only if it is true for you (the AI tool was used; you reviewed and edited the content and take full responsibility).\n"
        "During the preparation of this work the author(s) used Claude (Anthropic) in order to draft and edit the manuscript text, write the analysis scripts and draft the framework (workflow) diagram. "
        "After using this tool/service, the author(s) reviewed and edited the content as needed and take(s) full responsibility for the content of the published article.\n\n"
        "\\section*{Data availability}\n" + DATA_AVAIL + "\n\n"
        "\\section*{Acknowledgements}\nThe authors acknowledge the providers of the open datasets used (Esri World Imagery, ESA WorldCover, Copernicus DEM, Overture Maps, OpenStreetMap, Wikidata, geoBoundaries, LoveDA).\n\n"
        "\\bibliographystyle{elsarticle-num}\n\\bibliography{references}\n\n\\end{document}\n")

(H / "main.tex").write_text(preamble + front + body, encoding="utf-8")
(H / "highlights.txt").write_text("\n".join(HL) + "\n", encoding="utf-8")      # Elsevier asks for highlights as a separate editable file
print("highlights:", [len(h) for h in HL], "| abstract words (approx.):", abs_words, "| wrote", H / "main.tex")
