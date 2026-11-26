#!/usr/bin/env python
"""Write paper_erl/main.tex: the Environmental Research Letters manuscript of the four-window study, in a two-column journal layout.

    python paper_erl/build_main.py        # rewrites main.tex, refreshes the figure / table copies, then:  cd paper_erl; pdflatex main; bibtex main; pdflatex main; pdflatex main

Outline: 1 Introduction; 2 Data and methods (2.1 study windows, 2.2 datasets, 2.3 methodology as a two-split framework); 3 Results (3.1 segmentation and footprints,
3.2 cost surfaces and connectivity, 3.3 Stage A versus Stage B); 4 Discussion and conclusions. The prose is written here; every number that also appears in the pipeline result
files is read from them (src/multivillage/pipeline_summary.py and the results folders of the four areas).
"""
import re
import shutil
import sys
from pathlib import Path

import pandas as pd

H = Path(__file__).resolve().parent
REPO = H.parent
sys.path.insert(0, str(REPO))
from src.multivillage import pipeline_summary as PS      # noqa: E402

M = {k: PS.collect(k) for k in PS.ORDER}
fac = lambda k: sum(M[k]["facilities"].values())
pc = lambda k: f"{M[k]['saving_pct']:.1f}"
km = lambda k, x: f"{M[k][x] / 1000:.2f}"
lk = lambda k: f"{M[k]['cost_lakh']:,.0f}".replace(",", "{,}")
n = lambda x: f"{x:,}".replace(",", "{,}")
DK, AD, AS, AL = "damarakunta", "adilabad", "aswaraopeta", "alampur"
AREA_ORDER = (DK, AD, AS, AL)


def qc(k):
    """Quality classes of the extracted footprints (building_extraction_summary.csv of the area): {class: (polygons, median area)}."""
    f = PS.AREAS[k]["results"] / "building_extraction_summary.csv"
    if not f.exists():
        return {}
    d = pd.read_csv(f)
    return {r.quality_class: (int(r.polygons), float(r.median_area_m2)) for r in d.itertuples()}


def Q(k, c):
    return qc(k).get(c, (0, 0))[0]


def fcat(k):
    """'2 schools, 1 hospital ...' list of the verified facility categories of an area."""
    names = {"School": ("school", "schools"), "College": ("college", "colleges"), "Hospital": ("hospital or health centre", "hospitals and health centres"),
             "Government Office": ("government office", "government offices"), "Anganwadi": ("anganwadi", "anganwadis")}
    parts = []
    for c, v in M[k]["facilities"].items():
        if v:
            parts.append(f"{v} {names[c][0] if v == 1 else names[c][1]}")
    return ", ".join(parts[:-1]) + (" and " if len(parts) > 1 else "") + parts[-1] if parts else "none"


def pct_merge(k):
    tot = sum(v[0] for c, v in qc(k).items() if c != "SMALL_EXCLUDED") or 1
    return 100.0 * Q(k, "UNRESOLVED_MERGE") / tot


abstract = (
    r"Rural access-road planning needs to know where dwellings and public facilities are, what terrain a corridor must cross and how houses can share road length, yet building and facility records are incomplete. "
    r"We present a reproducible two-split framework that turns open geospatial data into shared access-road alternatives and apply it, without retraining or retuning, to four Telangana settlement windows of contrasting morphology: Damarakunta (rural), Adilabad (urban fringe), Aswaraopeta (semi-urban, tribal fringe) and Alampur (heritage town). "
    r"The first split, vision and semantic perception, couples a segmentation network built on the self-supervised DINOv2 vision transformer and trained on the Land-cover Domain Adaptive (LoveDA) benchmark (mean intersection over union 53.8\%, mean Dice coefficient 68.9\%) with morphological and watershed footprint extraction and a four-pass audit that snaps "
    + f"{fac(DK)}, {fac(AD)}, {fac(AS)} and {fac(AL)}"
    + r" verified public facilities onto roofs. The second split builds a land-cover and Copernicus elevation cost surface on a 5~m grid with a 3.6~m hard building clearance and consolidates independent least-cost routes (Stage A) into a shared network (Stage B) by iterative Dijkstra search. "
    r"No route crosses a building in any window. Shared routing shortened the unique network by "
    + f"{pc(DK)}, {pc(AD)}, {pc(AS)} and {pc(AL)}"
    + r"\%, equivalent to Rs "
    + f"{lk(DK)}, {lk(AD)}, {lk(AS)} and {lk(AL)}"
    + r" lakh (1 lakh is $10^{5}$ Indian rupees) at a benchmark of Rs 75 lakh per kilometre from India's Pradhan Mantri Gram Sadak Yojana (PMGSY). Savings depend on target density and road coverage, so the outputs are planning alternatives for field verification.")
words = len(re.sub(r"\\[A-Za-z]+|[{}$~\\%]", " ", abstract).split())


# ================================================================================================ the two-column document
def kw(k, key, fmt="{:.1f}"):
    return fmt.format(M[k][key])


head = r"""% Environmental Research Letters manuscript: article class, A4, two columns.
% Written by paper_erl/build_main.py. Compile: pdflatex main && bibtex main && pdflatex main && pdflatex main
\documentclass[10pt,a4paper,twocolumn]{article}
\usepackage[top=0.75in,bottom=0.8in,left=0.68in,right=0.68in,columnsep=0.26in]{geometry}
\usepackage{mathptmx}
\usepackage[scaled=0.92]{helvet}
\usepackage{amsmath,amssymb}
\usepackage{booktabs}
\usepackage{array}
\usepackage{xcolor}
\usepackage{graphicx}
\usepackage[font=small,labelfont=bf,labelsep=period,skip=3pt]{caption}
\usepackage{algorithm}
\usepackage{algpseudocode}
\usepackage{titlesec}
\usepackage{stfloats}
\usepackage{placeins}
\usepackage[colorlinks=true,allcolors=blue!50!black]{hyperref}
\pagestyle{plain}
\setlength{\emergencystretch}{2em}
\setlength{\parindent}{10pt}
\setlength{\parskip}{0pt}
\setlength{\textfloatsep}{8pt plus 2pt minus 2pt}
\setlength{\floatsep}{8pt plus 2pt minus 2pt}
\setlength{\intextsep}{8pt plus 2pt minus 2pt}
\renewcommand{\topfraction}{0.9}\renewcommand{\dbltopfraction}{0.9}\renewcommand{\textfraction}{0.08}\renewcommand{\floatpagefraction}{0.7}\renewcommand{\dblfloatpagefraction}{0.7}
\titleformat{\section}{\sffamily\bfseries\large}{\thesection}{0.6em}{}
\titleformat{\subsection}{\sffamily\bfseries\normalsize}{\thesubsection}{0.6em}{}
\titleformat{\subsubsection}{\sffamily\bfseries\itshape\small}{\thesubsubsection}{0.6em}{}
\titlespacing*{\section}{0pt}{9pt plus 2pt minus 2pt}{3pt}
\titlespacing*{\subsection}{0pt}{7pt plus 2pt minus 2pt}{2pt}
\titlespacing*{\subsubsection}{0pt}{5pt plus 2pt minus 2pt}{1pt}
\newcommand{\dinoseg}{StrongDINOv2Seg}
\newcommand{\Lcost}{L_{\mathrm{cost}}}
\newcommand{\pending}[1]{\textcolor{red}{\textit{#1}}}
\algrenewcommand\algorithmicrequire{\textbf{Input:}}
\algrenewcommand\algorithmicensure{\textbf{Output:}}
\algrenewcommand\alglinenumber[1]{\scriptsize #1:}
\newcommand{\ack}[1]{\section*{Acknowledgments}#1}
\newcommand{\funding}[1]{\section*{Funding}#1}
\newcommand{\roles}[1]{\section*{Author contributions}#1}
\newcommand{\data}[1]{\section*{Data availability}#1}
\sloppy

\begin{document}
\twocolumn[{%
\begin{center}
{\sffamily\bfseries\LARGE Smart village infrastructure planning and road network optimization for rural Telangana\par}
\vspace{8pt}
{\large Ramakrishna Kolikipogu$^{1,*}$ and Pendyala Archana$^{1}$\par}
\vspace{3pt}
{\small $^1$Department of Information Technology, Chaitanya Bharathi Institute of Technology (A), Hyderabad, India\\
$^*$Author to whom any correspondence should be addressed. E-mail: krkrishna.cse@gmail.com, pendyalaarchanareddy98@gmail.com\par}
\end{center}
\vspace{2pt}
\noindent\begin{minipage}{\textwidth}
\small\noindent{\sffamily\bfseries Abstract}\hspace{0.6em}""" + abstract + r"""\par\smallskip
\noindent{\sffamily\bfseries Keywords:} rural roads, building footprint extraction, satellite remote sensing, least-cost path, shared network, spatial transferability, open geospatial data, Telangana
\end{minipage}
\vspace{10pt}
}]
% abstract: """ + f"{words} words" + r"""
"""

# ------------------------------------------------------------------------------------------------ 1 introduction
intro = r"""
\section{Introduction}
Road building is among the most consequential land-use changes of the coming decades. Global road length is projected to grow by roughly 3.0--4.7 million km by 2050 \cite{meijer2018global}, and new roads open land to clearing, fragmentation and conversion \cite{laurance2014global}. Much of this growth is local. In India the Pradhan Mantri Gram Sadak Yojana (PMGSY) connects habitations through all-weather rural roads \cite{pmgsy}, and planning for such schemes depends on knowing where dwellings and facilities are, what terrain and land cover a corridor must cross, and which connection rule is applied.

Computational support for this planning has matured along three separate lines. Remote sensing now maps buildings and roads at large scale, from continental building inventories \cite{sirko2021openbuildings} to foundation-model segmenters \cite{oquab2023dinov2}, with recent work on small and isolated rural buildings, uncertainty and domain shift \cite{r62,r63,r64,r65,r66,r67,r68,r69,r70}, on road extraction for rural and arid scenes \cite{r56,r57,r58,r59,r60} and on informal settlements \cite{r48}. Multi-criteria and least-cost analysis translates terrain and land cover into route costs \cite{r06,r53,r54,collischonn2000lcp}. Network-design formulations connect many demand points at low total cost, including Steiner-tree heuristics \cite{kou1981steiner,mehlhorn1988steiner,hwang1992steiner,r51}, rural road design models \cite{r41,r43,r44} and analogues for power and transport networks \cite{r45,r46,r47,r50}. These lines are rarely joined: detectors are judged by pixel overlap \cite{r01,foody2002status}, planners assume an error-free inventory \cite{heuvelink1998error}, and each house is often connected independently, so neighbouring houses re-trace the same corridor. To our knowledge no cited work combines satellite-derived building instances, a land-cover and slope cost surface with building avoidance, and a shared-network planner whose marginal cost credits built corridors.

We join them in one two-split framework (figure~\ref{fig:arch}) and apply it, unchanged, to four settlement windows of different morphology in Telangana, built from one set of open data layers and one frozen segmentation checkpoint. Our objectives are (1)~to develop a reproducible framework whose first split, vision and semantic perception, extracts building footprints, road-gap targets and verified facilities from open imagery, and whose second split builds a terrain and land-cover cost surface with a hard building clearance and consolidates independent routes into a shared network; (2)~to test whether the same checkpoint and rules transfer without retraining across a rural village, an urban fringe, a semi-urban town and a heritage town; and (3)~to quantify the length, cost and building-crossing outcomes of independent (Stage~A) and shared (Stage~B) routing, against baseline strategies, as planning alternatives for PMGSY-type schemes.
"""

# ------------------------------------------------------------------------------------------------ 2 data and methods
def area_par(k, lead, extra=""):
    m = M[k]
    return (lead + f" The window covers {m['window_km2']:.2f}~km$^2$ with {m['roads_km']:.1f}~km of mapped road and a mean slope of {m['slope_mean_pct']:.1f}\\%. "
            f"The segmenter yields {n(m['buildings'])} building instances (\\textsc{{Plausible}} {n(Q(k, 'PLAUSIBLE'))}, \\textsc{{Review}} {n(Q(k, 'REVIEW'))}, \\textsc{{Unresolved\\_Merge}} {n(Q(k, 'UNRESOLVED_MERGE'))}, "
            f"and {n(Q(k, 'SMALL_EXCLUDED'))} smaller than 30~m$^2$), of which {n(m['gap_targets'])} lie more than 30~m from a road and become targets. "
            f"The audit retains {fac(k)} verified facilities ({fcat(k)}). " + extra)


study = r"""
\section{Data and methods}\label{sec:data}
\subsection{Selection and characteristics of the four Telangana study windows}
The four windows span the settlement gradient of Telangana from a dispersed village to a district town (figure~\ref{fig:flow}), so that the same method meets different building densities, road coverage and facility mixes. All use UTM zone 44N (EPSG:32644) and the same open data stack (table~\ref{tab:data}). Because no official village or town polygon was available for them, each study window is the built-up settlement extent derived from open data around the settlement centre, with an edge-continuity check against ESA WorldCover; the windows are therefore settlement extents, not administrative polygons.

\textbf{Damarakunta} (Siddipet district, Markook mandal; $17.707^{\circ}$N, $78.753^{\circ}$E) is a dispersed rural village whose houses cluster around one core. """ + area_par(DK, "Its window is the extent derived from Overture building footprints around the village centre (the footprints themselves come from the segmentation).") + r"""

\textbf{Adilabad} (Adilabad district; $19.676^{\circ}$N, $78.534^{\circ}$E) is the urban fringe of the district town. Its window is the built-up extent derived from ESA WorldCover around the OpenStreetMap place node, spanning the Adilabad Urban mandal (50.5\%), Mavala (32.2\%) and Adilabad Rural (17.4\%). """ + area_par(AD, "It is the largest window and has the densest fabric.").replace("The window covers", "It covers") + r"""

\textbf{Aswaraopeta} (Bhadradri Kothagudem district; $17.241^{\circ}$N, $81.128^{\circ}$E) is the headquarters town of Aswaraopeta mandal, a semi-urban tribal-fringe town. Its window is the WorldCover built-up extent around the Overture locality point. """ + area_par(AS, "").replace("The window covers", "It covers", 1) + r"""

\textbf{Alampur} (Jogulamba Gadwal district; $15.880^{\circ}$N, $78.135^{\circ}$E) is a small heritage town on the Tungabhadra, known for its temple complex. Its window is the extent derived from Overture building footprints around the OpenStreetMap place node. """ + area_par(AL, "").replace("The window covers", "It covers", 1) + r"""

\subsection{Datasets}
All four windows are processed from the same open layers (table~\ref{tab:areas}): 0.6~m Esri World Imagery, \dinoseg{} building footprints, ESA WorldCover v200 land cover ($10$~m), the Copernicus GLO-30 elevation model ($30$~m), Overture Maps and OpenStreetMap road networks, and verified public facilities from OpenStreetMap, Overture Places, Wikidata and Wikipedia. The training benchmark is LoveDA, from which one checkpoint serves all windows. No layer is specific to one window.

\begin{table*}[t]
\caption{The four study windows and the data layers of each; the layers are the same open sources in every window. Top: window profiles (road length is the mapped road layer inside the window; slope is the mean terrain slope). Middle: the layer used in each window (OSM: OpenStreetMap; WorldCover: ESA WorldCover land-cover map; DEM: digital elevation model; GLO-30: Copernicus global 30~m DEM; LoveDA: Land-cover Domain Adaptive semantic segmentation dataset; ODbL: Open Database Licence; CC BY: Creative Commons Attribution). Bottom: the datasets with resolution, version, licence and location.}
\label{tab:areas}\label{tab:data}
\centering
\scriptsize
\renewcommand{\arraystretch}{1.1}
\begin{tabular}{@{}>{\raggedright\arraybackslash}p{2.3cm}>{\raggedright\arraybackslash}p{3.2cm}>{\raggedright\arraybackslash}p{3.2cm}>{\raggedright\arraybackslash}p{3.2cm}>{\raggedright\arraybackslash}p{3.2cm}@{}}
\toprule
 & Damarakunta & Adilabad & Aswaraopeta & Alampur\\
\midrule
District & Siddipet & Adilabad & Bhadradri Kothagudem & Jogulamba Gadwal\\
Typology & Rural & Urban fringe & Semi-urban, tribal fringe & Heritage, semi-urban\\
Window (km$^2$) & """ + " & ".join(f"{M[k]['window_km2']:.2f}" for k in AREA_ORDER) + r"""\\
Existing roads (km) & """ + " & ".join(f"{M[k]['roads_km']:.1f}" for k in AREA_ORDER) + r"""\\
Mean slope (\%) & """ + " & ".join(f"{M[k]['slope_mean_pct']:.1f}" for k in AREA_ORDER) + r"""\\
\midrule
Boundary & Built-up extent from Overture footprints around the village centre & Built-up extent from WorldCover around the OSM place node & Built-up extent from WorldCover around the Overture locality point & Built-up extent from Overture footprints around the OSM place node\\
Existing roads & \multicolumn{4}{@{}l}{Overture Maps and OSM road networks (all four windows)}\\
Public facilities & """ + " & ".join(f"{fac(k)} verified" for k in AREA_ORDER) + r"""\\
Building footprints & \multicolumn{4}{@{}l}{\dinoseg{} on 0.6~m Esri imagery: """ + ", ".join(n(M[k]['buildings']) for k in AREA_ORDER) + r""" instances}\\
Land cover & \multicolumn{4}{@{}l}{ESA WorldCover, 10~m, v200}\\
Terrain & \multicolumn{4}{@{}l}{Copernicus DEM GLO-30, 30~m, slope by the Sobel method}\\
Training benchmark & \multicolumn{4}{@{}l}{LoveDA, one checkpoint for all four windows}\\
\bottomrule
\end{tabular}

\medskip
\begin{tabular}{@{}>{\raggedright\arraybackslash}p{3.4cm}>{\raggedright\arraybackslash}p{1.6cm}>{\raggedright\arraybackslash}p{1.8cm}>{\raggedright\arraybackslash}p{3.0cm}>{\raggedright\arraybackslash}p{5.0cm}@{}}
\toprule
Dataset (use) & Resolution & Version & Licence & URL / DOI\\
\midrule
Esri World Imagery \cite{esri2026worldimagery} (imagery) & 0.6~m & live service & Esri terms; academic use, credit required & \url{services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer}\\
Overture Maps \cite{overture2026} (roads, places, footprints for window extents) & vector & 2026-10-21.0 & ODbL 1.0; CDLA-Permissive-2.0 & \url{overturemaps.org}\\
OpenStreetMap \cite{haklay2008osm} (roads, facilities) & vector & live (Overpass, Photon) & ODbL 1.0 & \url{openstreetmap.org/copyright}\\
ESA WorldCover \cite{zanaga2021worldcover} (land cover) & 10~m & v200 (2021) & CC BY 4.0 & \url{doi.org/10.5281/zenodo.7254221}\\
Copernicus DEM GLO-30 \cite{esa2022copdem} (slope) & 30~m, slope at 10~m & GLO-30 & Copernicus licence & \url{doi.org/10.5270/ESA-c5d3d65}\\
LoveDA \cite{wang2021loveda} (training, validation) & 0.3~m & 2021 & CC BY-NC-SA 4.0 & \url{doi.org/10.5281/zenodo.5706578}\\
Wikidata \cite{vrandecic2014wikidata}, Wikipedia (facility audit) & points & live & CC0; CC BY-SA 4.0 & \url{wikidata.org}\\
\bottomrule
\end{tabular}
\end{table*}


\subsection{Methodology}\label{sec:methods}
"""

# ------------------------------------------------------------------------------------------------ 3 results
def strat_rows():
    """Routing-strategy comparison on the 10 m soft-penalty grid, four windows, from the committed routing_strategy_comparison.csv of each window."""
    names = {"Independent least-cost routes": "Independent routes", "Length-only control": "Length-only control", "Roads-only shared reference": "Roads-only shared reference", "Two-stage shared plan": "Two-stage shared plan"}
    out = []
    for i, k in enumerate(AREA_ORDER):
        df = pd.read_csv(PS.AREAS[k]["results"] / "routing_strategy_comparison.csv").set_index("strategy")
        rows = []
        for key, nm in names.items():
            q = df.loc[key]
            sv = q.saving_vs_independent_pct
            svs = f"{abs(sv):.1f}" if sv >= 0 else f"$-{abs(sv):.1f}$"
            rows.append((nm, f"{int(q.targets_routed)}", f"{q.unique_len_m:,.1f}".replace(",", "{,}"), svs, f"{int(q.routes_crossing_other_footprints)}", f"{q.length_inside_other_footprints_m:,.1f}".replace(",", "{,}")))
        if i:
            out.append(r"\midrule")
        for j, r in enumerate(rows):
            out.append((f"{M[k]['label']} " if j == 0 else "") + "& " + " & ".join(r) + r"\\")
    return "\n".join(out), {k: pd.read_csv(PS.AREAS[k]["results"] / "routing_strategy_comparison.csv").set_index("strategy") for k in AREA_ORDER}


strat_tex, SR = strat_rows()
sv = lambda k, key: SR[k].loc[key, "saving_vs_independent_pct"]
STG = {"two": "Two-stage shared plan", "road": "Roads-only shared reference", "len": "Length-only control"}
plaus = lambda k: 100.0 * Q(k, "PLAUSIBLE") / (sum(v[0] for c, v in qc(k).items() if c != "SMALL_EXCLUDED") or 1)


def fig_wide(lab, fn, cap, h="0.44"):
    return ("\\begin{figure*}[!t]\n\\centering\n\\includegraphics[width=0.74\\textwidth,height=" + h + "\\textheight,keepaspectratio]{" + fn + "}\n\\caption{" + cap + "}\n\\label{" + lab + "}\n\\end{figure*}\n\n")


results = r"""
\section{Results}\label{sec:results}
\subsection{Land-cover segmentation and building footprint accuracy}\label{sec:res1}
On the 1{,}669-image LoveDA validation split (560~px tiles, seven scored classes) the epoch-4 checkpoint reached 53.8\% mIoU, 68.9\% Dice (equal to the macro F1-score), 71.3\% pixel accuracy, 72.4\% macro precision and 66.9\% macro recall; for the Building class IoU is 54.0\%, Dice 70.1\%, precision 62.1\% and recall 80.6\% (table~\ref{tab:seg}). The high building recall is what the routing task needs, because a missed roof removes a household from the plan whereas a spurious blob is absorbed by the merge flag and the 25~m$^2$ minimum. The published test-set mIoU of other LoveDA baselines are listed for orientation; they were scored on the benchmark's test split with other protocols, so the comparison is indicative. The scores are source-domain figures: no surveyed building mask exists for any Telangana window, so the footprints are described by their quality classes (figure~\ref{fig:split1}). Plausible single roofs make up """ + f"{plaus(DK):.0f}\\%, {plaus(AD):.0f}\\%, {plaus(AS):.0f}\\% and {plaus(AL):.0f}\\%" + r""" of the instances in Damarakunta, Adilabad, Aswaraopeta and Alampur, and merged roof blocks """ + f"{pct_merge(DK):.0f}\\%, {pct_merge(AD):.0f}\\%, {pct_merge(AS):.0f}\\% and {pct_merge(AL):.0f}\\%" + r""", rising with the density of the fabric; the targets of the dense windows are therefore built-up units rather than individual houses.

\begin{table*}[t]
\caption{Semantic segmentation on LoveDA. mIoU is the mean intersection over union over classes, F1 is the harmonic mean of precision and recall (equal to the Dice coefficient), and precision and recall are the share of predicted pixels that are correct and of true pixels that are found. (a)~Published mIoU of the benchmark baselines (test split, from the cited papers) next to \dinoseg{} (our 1{,}669-image validation split, so the comparison is indicative). (b)~Validation metrics of \dinoseg{} at 560~px: macro averages over the seven scored classes and the Building class alone. Overall pixel accuracy, a whole-image quantity with no per-class counterpart, is 71.3\%.}
\label{tab:seg}
\centering
\scriptsize
\setlength{\tabcolsep}{3pt}
\begin{minipage}[t]{0.47\textwidth}\centering
\begin{tabular}{@{}llr@{}}
\toprule
\multicolumn{3}{@{}l}{\textit{(a) Literature comparison on LoveDA}}\\
Model & Backbone & Published mIoU (\%)\\
\midrule
U-Net \cite{ronneberger2015unet,wang2021loveda} & ResNet-50 & 47.84\\
DeepLabv3+ \cite{chen2018deeplabv3plus,wang2021loveda} & ResNet-50 & 47.62\\
UNetFormer \cite{wang2022unetformer} & ResNet-18 & 52.4\\
\dinoseg{} (ours) & DINOv2 ViT-B/14 & 53.8\\
\bottomrule
\end{tabular}
\end{minipage}\hfill
\begin{minipage}[t]{0.5\textwidth}\centering
\begin{tabular}{@{}lrrrr@{}}
\toprule
\multicolumn{5}{@{}l}{\textit{(b) \dinoseg{} validation metrics (560 px, 1,669 images)}}\\
Scope & mIoU (\%) & F1 / Dice (\%) & Precision (\%) & Recall (\%)\\
\midrule
All 7 classes (macro) & 53.8 & 68.9 & 72.4 & 66.9\\
Building class & 54.0 & 70.1 & 62.1 & 80.6\\
\bottomrule
\end{tabular}
\end{minipage}
\end{table*}

""" + fig_wide("fig:split1", "fig_split1_footprints.png", r"Split~1 output in the densest cluster of each study window: building footprints extracted by \dinoseg{} and OpenCV (orange: road-gap target houses; outlined: other footprints), verified public facilities (School, College, Hospital, Government Office, Anganwadi, with their facility numbers) and existing roads (cyan). Scale bars are 200~m. Basemap imagery: Esri, Maxar, Earthstar Geographics, and the GIS User Community.") + r"""
\subsection{Multi-criteria cost surfaces and proposed road connectivity across the four study windows}\label{sec:res2}
The cost surface adds a land-cover resistance and a slope penalty to a hard building clearance (equations~\ref{eq:cell}--\ref{eq:bldg}); the terrain is nearly flat in all four windows, with mean slopes of """ + f"{M[DK]['slope_mean_pct']:.1f}, {M[AD]['slope_mean_pct']:.1f}, {M[AS]['slope_mean_pct']:.1f} and {M[AL]['slope_mean_pct']:.1f}" + r"""\% (figure~\ref{fig:cost}), so cost differences come mainly from land cover and from the blocked cells around buildings. On the $5$~m grid with the $3.6$~m clearance every window yields a connected plan with no route across a roof (table~\ref{tab:four}). """ + (
    f"In Damarakunta, {n(M[DK]['routed'])} of {n(M[DK]['gap_targets'])} road-gap targets are routed and {fac(DK)} verified facilities are connected; in Adilabad {n(M[AD]['routed'])} of {n(M[AD]['gap_targets'])} targets and {fac(AD)} facilities; in Aswaraopeta {n(M[AS]['routed'])} of {n(M[AS]['gap_targets'])} targets and {fac(AS)} facilities; and in Alampur {n(M[AL]['routed'])} of {n(M[AL]['gap_targets'])} targets and {fac(AL)} facilities. ") + r"""The few unrouted targets are houses enclosed by neighbouring buildings and are reported as unrouted rather than routed over a roof. A $10$~m cell is wider than the lanes between neighbouring buildings, so a coarse grid with only a soft footprint penalty cannot keep routes off roofs, whereas a $5$~m grid that blocks every cell within $3.6$~m of a footprint (above the $3.54$~m half-diagonal of a $5$~m cell) leaves no step that can touch a roof; every drawn route was checked against all other footprints.

""" + fig_wide("fig:cost", "fig_split2_cost_surface.png", r"Split~2 inputs for the four study windows. Top: terrain slope in degrees from the 30~m Copernicus GLO-30 DEM (digital elevation model), resampled to the 10~m planning grid. Bottom: the base cost surface $C_0$ in ordinal planning units per 10~m, the sum of the land-cover resistance and the slope penalty (equation~\ref{eq:cell}); cells that are water, invalid or steeper than 25$^{\circ}$ are blocked.", "0.3") + r"""
\begin{table*}[t]
\caption{Four study windows side by side. Segmentation rows: LoveDA validation of the single \dinoseg{} checkpoint (overall accuracy is the share of correctly classified pixels; precision and recall are macro averages over classes; F1-score equals the mean Dice coefficient; mIoU is the mean intersection over union). Stage~A is independent least-cost routing and Stage~B the shared-trunk network; PMGSY is the Pradhan Mantri Gram Sadak Yojana rural road programme; 1 lakh $=10^{5}$ INR (Indian rupees); slope is the mean terrain slope in percent. Routing rows: unique lengths on the 5~m zero-crossing grid (shared edges once); building crossings are routes inside another building's footprint; cost is the Stage~B length times Rs 75 lakh per km (range 60--90).}
\label{tab:four}
\centering
\scriptsize
\resizebox{0.92\textwidth}{!}{\input{paper_comparison_table.tex}}
\end{table*}

\subsection{Stage A versus Stage B and shared-network routing trade-offs}\label{sec:res3}
Consolidating the independent routes into a shared trunk shortens the unique network in every window (figure~\ref{fig:ab}): Stage~A needs """ + f"{km(DK,'stageA_m')}, {km(AD,'stageA_m')}, {km(AS,'stageA_m')} and {km(AL,'stageA_m')}" + r"""~km and Stage~B """ + f"{km(DK,'stageB_m')}, {km(AD,'stageB_m')}, {km(AS,'stageB_m')} and {km(AL,'stageB_m')}" + r"""~km in Damarakunta, Adilabad, Aswaraopeta and Alampur, savings of """ + f"{pc(DK)}\\%, {pc(AD)}\\%, {pc(AS)}\\% and {pc(AL)}\\%" + r""", or Rs """ + f"{lk(DK)}, {lk(AD)}, {lk(AS)} and {lk(AL)}" + r""" lakh at the PMGSY benchmark. The saving is largest where targets are numerous, clustered and far from the mapped roads (Aswaraopeta) and smallest where the dense road layer already serves most houses and the remaining targets are scattered (Adilabad). Unique length scales with the number of targets and the road coverage, not with the window size: Aswaraopeta needs almost as much new road as Adilabad (""" + f"{km(AS,'stageB_m')}~km against {km(AD,'stageB_m')}~km" + r""") from one-seventh of the area. Figure~\ref{fig:detail} shows the shared trunks at settlement scale.

Table~\ref{tab:strategies} sets the two-stage plan against three baselines on the $10$~m soft-penalty grid, with the same targets and cost surface in each window. The two-stage plan is the shortest in all four windows (""" + ", ".join(f"{sv(k, STG['two']):.1f}\\%" for k in AREA_ORDER) + r""" below independent routes); the roads-only shared reference recovers """ + ", ".join(f"{sv(k, STG['road']):.1f}\\%" for k in AREA_ORDER) + r""" and the length-only control """ + ", ".join((f"{sv(k, STG['len']):.1f}\\% shorter" if sv(k, STG['len']) >= 0 else f"{abs(sv(k, STG['len'])):.1f}\\% longer") for k in AREA_ORDER) + r""", so sharing among the new routes, not sharing with existing roads or merely minimising length, drives the gain.

""" + fig_wide("fig:ab", "fig_stage_AB.png", r"Stage~A against Stage~B in the densest cluster of each window: the white dashed lines are the independent least-cost routes (Stage~A first choice), the blue lines the shared network for houses and the red lines the shared network for facilities (Stage~B), on the $5$~m grid with the $3.6$~m building clearance. Orange footprints are road-gap target houses. Basemap imagery: Esri, Maxar, Earthstar Geographics, and the GIS User Community.") + fig_wide("fig:detail", "fig_shared_network_detail.png", r"Settlement-scale detail of the zero-crossing shared network in each window (same window as the master planning map): house routes in blue, facility routes in red, verified facilities with their numbers, existing roads in cyan. No route crosses a building footprint. Basemap imagery: Esri, Maxar, Earthstar Geographics, and the GIS User Community.") + r"""
\begin{table*}[t]
\caption{Routing strategies on the $10$~m soft-penalty grid in the four study windows. Unique length counts shared edges once; saving is against independent routes (negative: longer); routes crossing is the number of routes that cross another building's footprint, and the last column is their length inside footprints. The length-only control replaces the cost surface by distance; the roads-only shared reference lets routes share edges only with the existing roads; the two-stage plan is the shared network of section~\ref{sec:routing}.}
\label{tab:strategies}
\centering
\scriptsize
\begin{tabular}{@{}llrrrrr@{}}
\toprule
Window & Strategy & Routed & Unique length (m) & Saving (\%) & Routes crossing & In footprints (m)\\
\midrule
""" + strat_tex + r"""
\bottomrule
\end{tabular}
\end{table*}
"""

# ------------------------------------------------------------------------------------------------ 4 discussion and conclusions
disc = r"""
\FloatBarrier
\section{Discussion and conclusions}\label{sec:disc}
\textbf{Regional planning implications.} The planning stages transferred without modification to all four windows: the same cost surface, clearance rule, solver parameters and metrics produced connected plans in a dispersed village, an urban fringe, a semi-urban town and a heritage town, with zero building crossings throughout. The size of the saving reflects target density and road coverage as much as morphology (""" + f"{pc(DK)}\\%, {pc(AD)}\\%, {pc(AS)}\\% and {pc(AL)}\\%" + r"""), so the figures describe the planning problem and do not rank settlement types. For PMGSY-style schemes \cite{pmgsy,irc2002sp20} three points follow. Building inventories are uncertain inputs, so a network sized from them should carry a sensitivity band; merged roof blocks make up """ + f"{pct_merge(AD):.0f}\\%, {pct_merge(AS):.0f}\\% and {pct_merge(AL):.0f}\\%" + r""" of the instances in the three larger windows, and their targets are built-up units rather than houses. Shared corridors save between about one eighth and one quarter of the unique length, which also reduces land take (about """ + f"{(M[DK]['stageA_m']-M[DK]['stageB_m'])*5/10000:.2f}, {(M[AD]['stageA_m']-M[AD]['stageB_m'])*5/10000:.2f}, {(M[AS]['stageA_m']-M[AS]['stageB_m'])*5/10000:.2f} and {(M[AL]['stageA_m']-M[AL]['stageB_m'])*5/10000:.2f}" + r"""~ha for an assumed 5~m formation width). Local overrides should be used sparingly and documented.

\textbf{Methodological limitations.} Four constraints bound the claims. (i)~\emph{Geographic and boundary scope:} four contrasting settlements in Telangana (""" + f"{min(M[k]['window_km2'] for k in AREA_ORDER):.2f}--{max(M[k]['window_km2'] for k in AREA_ORDER):.2f}" + r"""~km$^2$) were studied, with derived built-up extents; further agro-climatic regions and official cadastral or administrative polygons are future work. (ii)~\emph{Ground truth and footprint granularity:} field-surveyed building masks are unavailable, so \dinoseg{} was trained on LoveDA (53.8\% mIoU) and its footprints are described by quality classes; dense contiguous roofs are grouped as built-up blocks, and sub-metre stereo imagery or cadastral parcels could separate individual dwellings. (iii)~\emph{Heuristic optimisation:} the two-stage Steiner-like router consolidates trunks quickly and at scale but has no global optimality guarantee; exact mixed-integer solvers for sub-problems are a promising extension. (iv)~\emph{Planning-level cost benchmark:} corridor costs use a standardised PMGSY-aligned benchmark of Rs 75 lakh per kilometre (sensitivity range 60--90) for comparing corridors before detailed engineering design, which would add drainage structures, culverts and right-of-way acquisition \cite{irc2002sp20}; the central rate is a planning assumption supplied by the project owner and was not checked against a published PMGSY schedule.

\textbf{Scalability.} Every input is an open global layer and the segmentation checkpoint is applied frozen, so extending the framework to a further window needs only a settlement centre, the open-data download and the facility audit; the cost of a window is dominated by the $5$~m routing, which grows with the number of targets.

\textbf{Conclusions.} Open geospatial data, a single segmentation checkpoint and one rule set were enough to plan shared access roads in four Telangana windows of different morphology. In every window the $5$~m cost grid with a $3.6$~m hard building clearance produced corridor plans with no route across a building, and consolidating independent least-cost routes into a shared trunk shortened the new network by """ + f"{pc(DK)}\\%, {pc(AD)}\\%, {pc(AS)}\\% and {pc(AL)}\\%" + r""", at planning-benchmark costs of Rs """ + f"{lk(DK)}, {lk(AD)}, {lk(AS)} and {lk(AL)}" + r""" lakh. The shared plan was the shortest of the strategies compared in all four windows. The corridors remain planning alternatives for field verification.

\ack{The authors acknowledge the providers of the open datasets used (Esri World Imagery, ESA WorldCover, Copernicus DEM, Overture Maps, OpenStreetMap, Wikidata, geoBoundaries, LoveDA).}

\funding{This research received no specific grant from any funding agency in the public, commercial, or not-for-profit sectors.}

\roles{Ramakrishna Kolikipogu: conceptualization, supervision, writing -- review and editing. Pendyala Archana: methodology, software, investigation, formal analysis, visualization, writing -- original draft.}

\data{Code, derived summary tables and the open-data manifests with SHA-256 hashes are available at \url{https://github.com/Archana519/Telangana-Rural-Project} (folders \path{DELIVERABLES_CONTRIBUTION_3_MULTI_VILLAGE} and \path{FINAL_PROJECT_OUTPUTS}). Imagery: Esri World Imagery (sources: Esri, Maxar, Earthstar Geographics, and the GIS User Community), used for non-commercial academic research and overlay under Esri's academic terms; raw tiles are not redistributed. Open datasets: ESA WorldCover 10~m v200 (CC BY 4.0, \url{https://doi.org/10.5281/zenodo.7254221}), Copernicus GLO-30 DEM (\url{https://doi.org/10.5270/ESA-c5d3d65}), Overture Maps and OpenStreetMap (ODbL 1.0), geoBoundaries (ODbL 1.0), LoveDA (CC BY-NC-SA 4.0, \url{https://doi.org/10.5281/zenodo.5706578}). The \dinoseg{} checkpoint is not included in the repository; its SHA-256 is given in section~\ref{sec:seg}.}

\section*{Conflict of interest}
The authors declare no competing interests.

{\footnotesize\setlength{\itemsep}{0pt}
\bibliographystyle{iopart-num}
\bibliography{references}}

\end{document}
"""
method = r"""
\section{Methodology: a two-split framework}\label{sec:methods}
\subsection{Framework overview}
The method is organised as two splits that are identical for all four settlements and communicate through a small set of objects (figure~\ref{fig:arch}). \emph{Split~1, vision and semantic perception}, turns open imagery into the objects that planning needs: 0.6~m Esri World Imagery \cite{esri2026worldimagery} is segmented by \dinoseg{}, and OpenCV morphological and watershed operations \cite{bradski2000opencv} extract building footprints $B$, the road-gap target houses $\mathcal T$ (more than 30~m from an existing road) and the verified facilities $F_i$ snapped onto roofs (sections~\ref{sec:seg}--\ref{sec:audit}). \emph{Split~2, geospatial cost surface and shared-network routing}, takes these objects together with the road network $R$ (TGRAC and OpenStreetMap), ESA WorldCover v200 land cover \cite{zanaga2021worldcover} and the Copernicus GLO-30 elevation model \cite{esa2022copdem}, builds a $5$~m cost raster with a hard $3.6$~m building clearance, computes independent least-cost routes (Stage~A) and consolidates them by iterative Dijkstra search \cite{dijkstra1959note} into a shared network (Stage~B), and prices the result against the PMGSY programme benchmark \cite{pmgsy} (sections~\ref{sec:cost}--\ref{sec:eval}). The interface between the splits is the footprint raster and the target and facility lists, so the segmentation model can be replaced without touching the planner and vice versa.

\begin{figure}[t]
\centering
\includegraphics[width=\textwidth]{fig_architecture.png}
\caption{Two-split framework, applied unchanged to the four study areas. Split~1 (vision and semantic perception): (1)~multi-source open inputs (Esri World Imagery, roads from TGRAC and OSM, ESA WorldCover, Copernicus DEM, verified facilities $F_i$); (2)~\dinoseg{} semantic segmentation of $560\times560\times3$ RGB tiles (DINOv2 ViT-B/14: self-supervised vision transformer, base size, 14~px patches; FPN: feature pyramid network; ASPP: atrous spatial pyramid pooling; CE: cross-entropy; mIoU: mean intersection over union; F1: harmonic mean of precision and recall); (3)~OpenCV morphological and watershed footprint extraction with road-gap targets and facility snapping. Split~2 (geospatial cost surface and shared-network routing): (4)~$5$~m cost surface from DEM slope and land cover with a hard $3.6$~m building clearance; (5)~Stage~A independent and Stage~B shared-trunk Dijkstra routing; (6)~PMGSY-benchmarked cost, zero-crossing corridors and GIS planning maps (PMGSY: Pradhan Mantri Gram Sadak Yojana; IRC: Indian Roads Congress).}
\label{fig:arch}
\end{figure}

@@FLOWFIG@@

\subsection{Split 1: semantic segmentation with StrongDINOv2Seg}\label{sec:seg}
\dinoseg{} is a fully fine-tuned DINOv2 ViT-B/14 encoder \cite{oquab2023dinov2}. Tokens from blocks 3, 6, 9 and 12 are projected to 256 channels and fused FPN-style \cite{lin2017fpn}, passed through an ASPP neck (rates 6, 12, 18) \cite{chen2018deeplabv3plus} and a four-stage decoder of residual convolution blocks (256, 128, 64 and 32 channels) with auxiliary heads for deep supervision \cite{lee2015dsn}. \emph{Why LoveDA.} Telangana has no village-level pixel labels, and drawing them for every settlement would defeat the purpose of an open-data planning tool. LoveDA \cite{wang2021loveda} supplies standardised multi-class remote-sensing land-cover imagery, with urban and rural scenes and seven classes (background, building, road, water, barren, forest and agriculture), so it serves to pre-train and benchmark \dinoseg{} once; the frozen checkpoint is then applied to the open-data Telangana planning windows without any village-by-village labelling. Training used LoveDA at 560~px for a scheduled 10 epochs (AdamW, cosine schedule to $10^{-7}$, encoder learning rate $\times 0.1$); the epoch-4 checkpoint is used for all four settlements, frozen, with SHA-256 \texttt{2e7c4646dc77ceb2\allowbreak a357f44f11cb3f7f\allowbreak f84e636871d70ba4\allowbreak c31e194e5ec00cf3}. With logits $\mathbf z$, labels $y$, class probabilities $p_{ic}$ and one-hot targets $t_{ic}$ at pixel $i$ (class 0 is ignored), the loss is
\begin{equation}
\begin{aligned}
\mathcal L(\mathbf z,y)&=0.5\,\mathcal L_{\mathrm{CE}}+0.4\,\mathcal L_{\mathrm{Dice}}+0.1\,\mathcal L_{\mathrm{edge}},\\
\mathcal L_{\mathrm{total}}&=\mathcal L(\mathbf z^{\mathrm{main}},y)+0.4\sum_{j=1}^{3}\mathcal L(\mathbf z^{(j)},y),
\end{aligned}
\label{eq:loss}
\end{equation}
\begin{equation}
\begin{aligned}
\mathcal L_{\mathrm{Dice}}&=\frac1{|\mathcal C|}\sum_{c\in\mathcal C}\Bigl(1-\frac{2\sum_i p_{ic}t_{ic}+\varepsilon}{\sum_i (p_{ic}+t_{ic})+\varepsilon}\Bigr),\\
\mathcal L_{\mathrm{edge}}&=\frac1{|\Omega|}\sum_{i\in\Omega}(1+4e_i)\,\mathrm{CE}_i,\\
e_i&=\min\{1,\,|(K_x{*}y)_i|+|(K_y{*}y)_i|\}.
\end{aligned}
\label{eq:diceedge}
\end{equation}
Here $\mathcal C$ is the set of scored classes, $\varepsilon$ a small smoothing constant, and $K_x,K_y$ the Sobel kernels, so that the edge term up-weights the cross-entropy of pixels on label boundaries by up to a factor of five \cite{milletari2016vnet}; the three auxiliary heads $\mathbf z^{(j)}$ provide deep supervision. From the confusion matrix, with $TP_c,FP_c,FN_c$ the true positives, false positives and false negatives of class $c$ and $N$ the number of labelled pixels,
\begin{equation}
\begin{aligned}
\mathrm{OA}&=\frac{\sum_c TP_c}{N},\qquad P_c=\frac{TP_c}{TP_c+FP_c},\\
R_c&=\frac{TP_c}{TP_c+FN_c},\qquad F_{1,c}=\frac{2P_cR_c}{P_c+R_c},\\
\mathrm{IoU}_c&=\frac{TP_c}{TP_c+FP_c+FN_c},
\end{aligned}
\label{eq:metrics}
\end{equation}
and $P$, $R$, $F_1$ (the Dice coefficient) and $\mathrm{mIoU}=|\mathcal C|^{-1}\sum_{c\in\mathcal C}\mathrm{IoU}_c$ are the macro averages over the scored classes; because $F_{1,c}$ equals the per-class Dice score, the reported F1-score is the mean Dice.

\subsection{Split 1: tiled inference, footprint extraction and road-gap targets}\label{sec:extract}
Each mosaic is segmented in $560\times560$~px tiles at a stride of 420~px with a 70~px margin discarded at inner tile edges (stride $\le$ tile $-\,2\times$ margin, so no gaps appear). Building instances are extracted from the predicted mask with OpenCV and NumPy (algorithm~\ref{alg:extract}): a distance transform of each connected component gives $h$-maxima markers, a marker-controlled flooding of the inverted transform (a watershed-type split) proposes pieces, and a neck test keeps two pieces apart only if the saddle between them is narrower than 0.65 times the inscribed radius of the smaller piece; otherwise they are re-merged. Blobs much larger than the median compact roof are flagged \textsc{Unresolved\_Merge} and treated as built-up extent rather than single houses. Because connecting every footprint is meaningless in a fabric already served by roads, only buildings more than 30~m (the planner snap distance) from an existing road are routed; planner cost grows roughly quadratically with the number of targets, which further motivates the filter. The threshold is varied (20, 30, 50~m) in section~\ref{app:robust}.

\begin{algorithm}[t]
\caption{Tiled \dinoseg{} inference and distance-transform building extraction (EDT: Euclidean distance transform; $h$-maxima: regional maxima of height $h$ used as seeds) (\texttt{run\_tiled\_inference.py}, \texttt{extract\_buildings\_v8.py})}
\label{alg:extract}
\begin{algorithmic}[1]
\Require mosaic $I$ (0.6~m), checkpoint $\theta$, tile $T=560$, stride $s=420$, margin $m=70$, neck ratio $\eta=0.65$, seed height $h=0.3$~m
\Ensure footprints $\mathcal B$ with quality classes
\State \textbf{assert} $s\le T-2m$ \Comment{no gaps between tile centres}
\For{each tile of size $T\times T$ at stride $s$}
  \State $p\gets\mathrm{softmax}(f_\theta(\text{tile}))$; write class $\arg\max p$ and $p_{\mathrm{bldg}}$ for the tile centre (drop $m$ px at inner edges)
\EndFor
\State $M\gets(\text{class}=\text{building})\wedge\lnot\text{no-data}$; drop components smaller than 6~m$^2$
\For{each connected component $K$ of $M$}
  \State $D\gets\mathrm{EDT}(K)$ (smoothed, $\sigma=1$ px); markers $\gets$ $h$-maxima of $D$ with height $h$
  \State pieces $\gets$ marker-controlled flooding of $-D$ (only if area $\ge 40$~m$^2$)
  \For{each adjacent piece pair $(a,b)$}
    \State $r_{ab}\gets D_{\mathrm{saddle}}/\min(D_a^{\max},D_b^{\max})$
    \If{$r_{ab}>\eta$ \textbf{or} a piece is smaller than 12~m$^2$} merge $a,b$ \Comment{no real neck}
    \EndIf
  \EndFor
\EndFor
\State polygonise; flag \textsc{Unresolved\_Merge} if area $>4\times$ the median compact roof; assign \textsc{Plausible} / \textsc{Review} / \textsc{Small} by confidence and shape
\State \Return $\mathcal B$
\end{algorithmic}
\end{algorithm}

\subsection{Split 1: facility audit and roof snapping}\label{sec:audit}
Overture Places alone mislocated or missed colleges, hospitals, offices and anganwadis, so the facilities of each area come from a four-pass audit (\texttt{scripts/audit\_facilities.py}). Pass~1 harvests candidates inside and within 500~m of the polygon from OpenStreetMap (Overpass and the Photon geocoder), Overture Places, Wikidata and Wikipedia (and, for Damarakunta, the TGRAC layers). Pass~2 assigns one of five categories (School, College, Hospital, Government Office, Anganwadi), removes closed or commercial records (pharmacies, laboratories, coaching centres, banks, cooperative societies), religious sites, foreign place names and placeholder coordinates shared by several differently named records, and merges duplicates of one campus across sources; every removal is logged with its reason. Pass~3 moves each survivor onto the footprint that contains it or, failing that, the nearest footprint of at least 25~m$^2$ within 35~m (a compound building up to 25~m away for a school, college or hospital), and removes facilities with no building in range. Ten of the 68 verified facility points of the first Adilabad run shared an identical coordinate with another Overture record (generic geocodes), so a 20~m footprint check is weak evidence in dense fabric, which is why the audit rejects placeholder coordinates. Pass~4 writes the verified table with the sources, the snap distance and a confidence label; records with a single source and a snap of more than 12~m are kept with \texttt{use\_in\_analysis}${}=$\,False and are not routed.

\subsection{Split 2: DEM slope, multi-criteria cost surface and building clearance}\label{sec:cost}
Let $\mathcal B$ be blocked cells (water, invalid cells, slope $>25^{\circ}$) and $\mathcal P$ the cells whose centre lies inside a footprint. The 10~m comparison graph has the unblocked cells as nodes and 8-neighbour edges with no diagonal corner-cutting, and the cell cost is
\begin{equation}
\begin{aligned}
c(x)&=\bigl[c_{\mathrm{lc}}(\ell(x))+g(S(x))\bigr]\,m(x),\\
m(x)&=\begin{cases}\mu & x\in\mathcal P\\ 1 & \text{otherwise,}\end{cases}
\end{aligned}
\label{eq:cell}
\end{equation}
where $\ell$ is the WorldCover class with resistance $c_{\mathrm{lc}}=8,5,3,6,2,4$ for trees, shrubland, grassland, cropland, built-up and bare/sparse land (classes 10, 20, 30, 40, 50, 60), $g(S)=w_s\min(S,S_{\mathrm{ref}})/S_{\mathrm{ref}}$ with $w_s=4$ and $S_{\mathrm{ref}}=10^{\circ}$, and $\mu=4$ is the soft footprint penalty. Slope comes from the Copernicus GLO-30 elevation $z$ with the Sobel gradient at the DEM spacing $\Delta_z=30$~m, resampled bilinearly to the planning grid:
\begin{equation}
\begin{aligned}
\partial_x z&\approx\frac{(K_x{*}z)}{8\Delta_z},\qquad \partial_y z\approx-\frac{(K_y{*}z)}{8\Delta_z},\\
S&=\arctan\sqrt{(\partial_x z)^2+(\partial_y z)^2},\qquad p_S=100\tan S,
\end{aligned}
\label{eq:slope}
\end{equation}
where $z$ is the elevation (m), $K_x$ and $K_y$ are the $3\times3$ Sobel kernels, $*$ is two-dimensional convolution, $\Delta_z=30$~m is the DEM grid spacing, $\partial_x z$ and $\partial_y z$ are the elevation gradients, $S$ is the slope in degrees (used in the cost surface) and $p_S$ the percentage slope reported in the tables; no separate IRC slope-penalty factor is applied. The soft penalty lets a route cross a roof when the detour costs more, so the proposed plan uses a hard barrier on a finer grid. Each 10~m cost cell is refined to $2\times2$ cells of size $\Delta=5$~m with the same cost per metre, and with $D(x)$ the Euclidean distance from the centre of cell $x$ to the nearest footprint (zero inside a footprint),
\begin{equation}
\begin{aligned}
C(x)&=c_{\mathrm{lc}}(\ell(x))+g(S(x))+C_{\mathrm{bldg}}(x),\\
C_{\mathrm{bldg}}(x)&=\begin{cases}\infty & D(x)\le r_c\\ 0 & \text{otherwise,}\end{cases}\\
r_c&=3.6\ \mathrm{m},\qquad \Delta=5\ \mathrm{m}.
\end{aligned}
\label{eq:bldg}
\end{equation}
Because $r_c>\Delta\sqrt2/2=3.54$~m, no step between two free cell centres can touch a footprint: a point of the step lies within $\Delta\sqrt2/2$ of one of its end points, and that end point would then have been blocked. A target sits inside its own building, so each route starts at the edge of that building and reaches the nearest free cell connected to the road network by a straight lane of at most the snap distance that touches no other footprint; a target with no such lane (a house enclosed by other buildings) is reported as unrouted, never routed over a roof. Lengths are measured from the building edge, and every drawn route (lane, path and road attachment) is finally intersected with all footprints other than its own.

\subsection{Split 2: shared-network routing by iterative Dijkstra search}\label{sec:routing}
The graph has the free cells as nodes and 8-neighbour edges, a diagonal step being allowed only if both orthogonal neighbours are free. The weight of an edge $(u,v)$ between neighbouring free cells $u$ and $v$, with $C(u)$ the cost of cell $u$ and $d(u,v)$ the step length, is
\begin{equation}
\begin{aligned}
w(u,v)&=d(u,v)\,\frac{C(u)+C(v)}{2},\\
d(u,v)&=\begin{cases}\Delta&\text{cardinal step}\\ \sqrt2\,\Delta&\text{diagonal step.}\end{cases}
\end{aligned}
\label{eq:edge}
\end{equation}
Stage~A gives every target $t$ the independent least-cost path $\pi_t^{A}=\arg\min_{\pi:\,t\to R}\sum_{e\in\pi}w(e)$ to the existing road cells $R$ \cite{dijkstra1959note,hart1968astar,collischonn2000lcp}, and two further alternatives that multiply $w(e)$ by $\lambda\in\{3,8\}$ on cells within 20~m of the earlier paths and overlap them by at most 80\% ($K=3$ alternatives in total). Stage~B starts from $E_S=\emptyset$ and repeatedly serves the target and route with the highest weight per marginal cost,
\begin{equation}
\begin{aligned}
(t^\star,\pi^\star)&=\arg\max_{t\in U,\ \pi\in\Pi_t\cup\{\pi_t^{\mathrm{net}}\}}\frac{\omega_t}{\Delta\Lcost(\pi\mid S)},\\
\Delta\Lcost(\pi\mid S)&=\sum_{e\in\pi\setminus E_S}w(e),
\end{aligned}
\label{eq:stageb}
\end{equation}
where $\omega_t$ weights the target (below), $E_S$ is the set of edges already built, $\Delta\Lcost(\pi\mid S)$ is the extra cost of route $\pi$ given the built network $S=E_S$, and $U$ is the set of unserved targets, $\Pi_t$ the Stage~A alternatives, $\pi_t^{\mathrm{net}}$ the least-cost path to the roads together with the routes already selected, and $\omega_t$ the priority weight (4 for hospitals and health centres, 3 for schools, colleges and anganwadis, 2 for government offices, 1 for houses). A built edge $e\in E_S$ costs nothing again---a discount factor $\alpha=0$ on $E_S$---so a route may end on another route; this is the shortest-path heuristic for Steiner trees \cite{kou1981steiner,mehlhorn1988steiner} on a penalised, land-cover-weighted graph with the road network as a free sub-tree, and it carries no optimality guarantee. Two passes of leaf re-routing follow. Snap distance is 30~m, search limit 1{,}500~m and attachment tolerance 15~m; facilities are planned in a separate phase.

\begin{algorithm}[t]
\caption{Cost surface with zero-crossing clearance and two-stage routing (\texttt{clearance.py}, \texttt{plan\_network\_v2.py})}
\label{alg:route}
\begin{algorithmic}[1]
\Require land cover $\ell$, DEM $z$, roads $R$, footprints $\mathcal B$, targets $\mathcal T$ (road-gap houses and verified facilities with weights $\omega_t$), $\Delta=5$~m, $r_c=3.6$~m, $K=3$
\Ensure route sets $\{\pi_t^A\}$, $E_S$ and lengths $L_A$, $L_B$, saving $\rho$, cost
\State $S\gets$ slope of $z$ (equation~\ref{eq:slope}); $C_0(x)\gets c_{\mathrm{lc}}(\ell(x))+g(S(x))$; block water, invalid cells and $S>25^{\circ}$
\State refine $C_0$ from 10~m to $\Delta=5$~m (same cost per metre); $D\gets\mathrm{EDT}(\mathcal B)$; $C(x)\gets\infty$ where $D(x)\le r_c$
\State keep the free cells connected to a road cell; edge weights $w$ by equation~\ref{eq:edge}
\For{each target $t\in\mathcal T$}
  \State entrance $e_t\gets$ point of the target's building edge nearest to a free cell $s_t$; require a lane $e_t\to s_t$ of at most 30~m that touches no other footprint, else mark $t$ unrouted
  \State $\Pi_t\gets K$ Dijkstra alternatives from $s_t$ to $R$ (corridor inflation $\lambda\in\{3,8\}$, 20~m, overlap $\le 80\%$); $\pi_t^A\gets$ first alternative
\EndFor
\State $L_A\gets L(\{\pi_t^A\})$; $U\gets$ routed targets; $E_S\gets\emptyset$
\While{$U\ne\emptyset$}
  \For{each $t\in U$} add the least-cost path $\pi_t^{\mathrm{net}}$ to $R\cup E_S$ to the candidates $\Pi_t$ \EndFor
  \State $(t^\star,\pi^\star)\gets\arg\max\ \omega_t/\Delta\Lcost(\pi\mid S)$ (equation~\ref{eq:stageb}); $E_S\gets E_S\cup\pi^\star$; $U\gets U\setminus\{t^\star\}$
\EndWhile
\State two leaf re-route passes: replace a route that no other route uses if it has become cheaper given the others
\State verify $X=0$ (equation~\ref{eq:saving}); $L_B\gets L(E_S)$; $\rho\gets 100(L_A-L_B)/L_A$; cost by equation~\ref{eq:cost}
\end{algorithmic}
\end{algorithm}

\subsection{Split 2: network metrics and PMGSY cost estimation}\label{sec:eval}
With $L(\cdot)$ the total length of the unique edges of a route set (shared edges counted once), the saving of the shared network and the exposure of dwellings are
\begin{equation}
\begin{aligned}
\rho&=\frac{L_A-L_B}{L_A}\times100\%,\\
L_A&=L\bigl(\{\pi_t^A\}\bigr),\qquad L_B=L(E_S),\\
X&=\sum_{r}\Bigl|r\cap\bigcup_{b\ne b_r}b\Bigr|=0.
\end{aligned}
\label{eq:saving}
\end{equation}
where $X$ is the length of routes inside footprints other than the route's own building $b_r$ (zero by construction under equation~\ref{eq:bldg}). The corridor cost is benchmarked against the PMGSY programme \cite{pmgsy}:
\begin{equation}
\begin{aligned}
\mathrm{Cost}_{\mathrm{INR\ lakh}}&=L_B[\mathrm{km}]\times c_{\mathrm{PMGSY}},\\
c_{\mathrm{PMGSY}}&=75\ \text{lakh/km}\ (\text{sensitivity range }60\text{--}90),
\end{aligned}
\label{eq:cost}
\end{equation}
where $L_B$ is the unique Stage~B length in kilometres, $c_{\mathrm{PMGSY}}$ the benchmark cost per kilometre and 1 lakh $=10^{5}$~INR (Indian rupees). This unit rate is the single benchmark used throughout for the unique shared corridor; it excludes land, drainage structures and variation in cross-section, and its scope is stated in section~\ref{sec:disc}. Four strategies are compared on the 10~m soft-penalty grid in all four settlements: straight lines, independent least-cost routes, a length-only control (cost surface replaced by distance), a roads-only shared reference (routes may share edges only with the existing road network) and the two-stage shared plan. The exposure metrics are the number of routes crossing another house's footprint and the route length inside other footprints. As a pilot test of inventory error, on Damarakunta alone a random subset of targets is removed from the targets and from the penalty layer (a missed detection is absent from both) and the planner is re-run, with random draws using seeds 1--5; coverage and the change in unique length are recorded.
"""
FLOW = r"""\begin{figure*}[p]
\centering
\IfFileExists{fig_flow_study_areas.png}{\includegraphics[width=0.9\textwidth,height=0.82\textheight,keepaspectratio]{fig_flow_study_areas.png}}{\fbox{\parbox{0.8\textwidth}{\centering\pending{Figure not generated yet: run \texttt{python scripts/build\_paper\_flow\_figure.py --source segmentation}.}}}}
\caption{Study windows and end-to-end flow. Top: Telangana with district outlines (geoBoundaries \cite{runfola2020geoboundaries}) and the four numbered study locations (1~Damarakunta, rural; 2~Adilabad, urban fringe; 3~Aswaraopeta, semi-urban, tribal fringe; 4~Alampur, heritage, semi-urban), and the key. One row per window, three columns: (a)~input (0.6~m Esri World Imagery, window boundary and existing roads); (b)~\dinoseg{} building footprints (road-gap target houses in orange) with the verified facilities; (c)~output, the Stage~B shared network of the 5~m zero-crossing plan (blue for houses, red for facilities) with scale bar and north arrow. Stage~A is the set of independent least-cost routes and Stage~B the shared network that consolidates them; below each output are their unique lengths, the building crossings and the facility count. Basemap imagery: Esri, Maxar, Earthstar Geographics, and the GIS User Community.}
\label{fig:flow}
\end{figure*}
"""

# ------------------------------------------------------------------------------------------------ methodology block: placed under 2.3 as sub-subsections
method = method.replace("@@FLOWFIG@@", FLOW)

def tx(old, new, cnt=1):
    global method
    assert old in method, old[:70]
    method = method.replace(old, new, cnt)


method = method.replace("\\section{Methodology: a two-split framework}\\label{sec:methods}\n", "")
method = method.replace("\\subsection{", "\\subsubsection{")
tx("\\begin{figure}[t]\n\\centering\n\\includegraphics[width=\\textwidth]{fig_architecture.png}", "\\begin{figure*}[t]\n\\centering\n\\includegraphics[width=0.86\\textwidth]{fig_architecture.png}")
tx("\\label{fig:arch}\n\\end{figure}", "\\label{fig:arch}\n\\end{figure*}")
method = method.replace("\\begin{algorithm}[t]", "\\begin{algorithm}[t]\n\\footnotesize")
tx("roads from TGRAC and OSM,", "roads from Overture and OSM,")
tx("(TGRAC and OpenStreetMap)", "(Overture Maps and OpenStreetMap)")
tx(" (and, for Damarakunta, the TGRAC layers)", "")
tx(" The threshold is varied (20, 30, 50~m) in section~\\ref{app:robust}.", "")
a = method.index(" As a pilot test of inventory error"); b = method.index("\n", a)
method = method[:a] + method[b:]
a = method.find("Ten of the 68")
if a >= 0:
    b = method.index("rejects placeholder coordinates.", a) + len("rejects placeholder coordinates.")
    method = method[:a].rstrip() + method[b:]
method = method.replace("in all four settlements: straight lines", "in all four windows: straight lines")

doc = head + intro + study + method + results + disc

# ------------------------------------------------------------------------------------------------ citation pass (every dataset, method and benchmark source cited at first use)
CITES = [
 (r"Stage~A computes independent Dijkstra least-cost routes", r"Stage~A computes independent Dijkstra least-cost routes \cite{dijkstra1959note}"),
 (r"benchmarked against a PMGSY corridor cost", r"benchmarked against a PMGSY corridor cost \cite{pmgsy}"),
 (r"OpenStreetMap (Overpass and the Photon geocoder)", r"OpenStreetMap \cite{haklay2008osm} (Overpass and the Photon geocoder \cite{photon2026})"),
 (r"with the Sobel gradient at the DEM spacing", r"with the Sobel gradient \cite{sobel1968gradient,horn1981hill} at the DEM spacing"),
 (r"OpenCV and NumPy (algorithm", r"OpenCV and NumPy \cite{bradski2000opencv,harris2020numpy} (algorithm"),
 (r"a distance transform of each connected component gives", r"a distance transform of each connected component \cite{felzenszwalb2012edt} gives"),
 (r"$h$-maxima markers, a marker-controlled flooding of the inverted transform (a watershed-type split)", r"$h$-maxima markers \cite{vincent1993morph}, a marker-controlled flooding of the inverted transform (a watershed-type split \cite{vincent1991watershed})"),
 (r"fully fine-tuned DINOv2 ViT-B/14 encoder \cite{oquab2023dinov2}", r"fully fine-tuned DINOv2 ViT-B/14 encoder \cite{oquab2023dinov2}, a vision transformer \cite{dosovitskiy2021vit}"),
 (r"a four-stage decoder of residual convolution blocks", r"a four-stage decoder of residual convolution blocks \cite{he2016resnet}"),
 (r"(AdamW, cosine schedule to $10^{-7}$,", r"(AdamW \cite{loshchilov2019adamw}, cosine schedule \cite{loshchilov2017sgdr} to $10^{-7}$,"),
 (r"are the macro averages over the scored classes; because", r"are the macro averages over the scored classes (IoU as in \cite{everingham2010voc}); because"),
 (r"it excludes land, drainage structures and variation in cross-section, and its scope", r"it excludes land, drainage structures and variation in cross-section (design practice for the programme is set out in the Indian Roads Congress (IRC) rural roads manual \cite{irc2002sp20}), and its scope"),
 (r"Wikidata and Wikipedia", r"Wikidata \cite{vrandecic2014wikidata} and Wikipedia"),
]
for old, new in CITES:
    if old not in doc:
        print("CITE ANCHOR NOT FOUND:", old[:70])
    else:
        doc = doc.replace(old, new, 1)

(H / "main.tex").write_text(doc, encoding="utf-8")
(H / "paper_comparison_table.tex").write_text(PS.latex_table([M[k] for k in PS.ORDER]), encoding="utf-8")      # Table 3, generated from the result files (never copied from paper_eris)
src = REPO / "paper_eris" / "figures" / "fig_architecture.png"
if src.exists() and src.resolve() != (H / "fig_architecture.png").resolve():
    shutil.copyfile(src, H / "fig_architecture.png")
print("abstract words:", words, "| wrote", H / "main.tex")
