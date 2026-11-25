#!/usr/bin/env python
"""Write paper_erl/main.tex: the Environmental Research Letters submission (IOP `iopjournal` class) of the four-settlement study.

    python paper_erl/build_main.py        # rewrites main.tex, refreshes the figure / table copies, then:  cd paper_erl; pdflatex main; bibtex main; pdflatex main; pdflatex main

The prose is written here; every number that also appears in the pipeline result files is read from them (src/multivillage/pipeline_summary.py), and the detailed robustness tables of the
four-area strategy table is built from the committed routing-strategy CSVs (the old 17.75 km2 Adilabad mandal run is no longer used in this paper).
"""
import re
import shutil
import sys
from pathlib import Path

H = Path(__file__).resolve().parent
REPO = H.parent
sys.path.insert(0, str(REPO))
from src.multivillage import pipeline_summary as PS      # noqa: E402

M = {k: PS.collect(k) for k in PS.ORDER}
ERIS = (REPO / "paper_eris" / "main.tex").read_text(encoding="utf-8")
fac = lambda k: sum(M[k]["facilities"].values())
pc = lambda k: f"{M[k]['saving_pct']:.1f}"
km = lambda k, x: f"{M[k][x] / 1000:.2f}"
lk = lambda k: f"{M[k]['cost_lakh']:,.0f}".replace(",", "{,}")
n = lambda x: f"{x:,}".replace(",", "{,}")
DK, AD, AS, AL = "damarakunta", "adilabad", "aswaraopeta", "alampur"


def table(label, caption=None):
    """A table environment of paper_eris/main.tex, verbatim (optionally with a new caption), placed in the appendix."""
    m = re.search(r"\\begin\{table\}\[t\]\n\\caption\{(.*?)\}\n\\label\{" + label + r"\}\n(.*?)\\end\{table\}", ERIS, re.S)
    assert m, label
    cap = caption or m.group(1)
    return "\\begin{table}[t]\n\\caption{" + cap + "}\n\\label{" + label + "}\n" + m.group(2) + "\\end{table}\n"


abstract = (
    r"Rural access-road planning needs to know where dwellings and public facilities are, what terrain a corridor must cross and how houses can share road length, yet building and facility records are incomplete. "
    r"We present a reproducible pipeline that turns open geospatial data into shared access-road alternatives and apply it, without retraining or retuning, to four Telangana settlements of contrasting morphology: Damarakunta (rural), Adilabad (urban fringe), Aswaraopeta (semi-urban, tribal fringe) and Alampur (heritage town). "
    r"A DINOv2-based segmentation network trained on the LoveDA benchmark (mean intersection over union 53.8\%, mean Dice 68.9\%) feeds distance-transform building extraction; a four-pass multi-source audit snaps "
    + f"{fac(DK)}, {fac(AD)}, {fac(AS)} and {fac(AL)}"
    + r" verified schools, colleges, hospitals, government offices and anganwadis onto roofs; and a land-cover and slope cost surface on a 5~m grid with a 3.6~m building clearance supports two-stage Dijkstra routing, in which independent least-cost routes (Stage~A) are consolidated into a shared network (Stage~B). "
    r"No route crosses a building, whereas a 10~m soft footprint penalty leaves "
    + f"{M[DK]['soft_cross_routes']}, {M[AD]['soft_cross_routes']}, {M[AS]['soft_cross_routes']} and {M[AL]['soft_cross_routes']}"
    + r" routes across footprints. Shared routing shortened the unique network by "
    + f"{pc(DK)}, {pc(AD)}, {pc(AS)} and {pc(AL)}"
    + r"\%, equivalent to Rs "
    + f"{lk(DK)}, {lk(AD)}, {lk(AS)} and {lk(AL)}"
    + r" lakh at a benchmark of Rs 75 lakh per kilometre from India's Pradhan Mantri Gram Sadak Yojana (PMGSY). Savings depend on target density and road coverage, so the outputs are planning alternatives for field verification.")
words = len(re.sub(r"\\[A-Za-z]+|[{}$~\\%]", " ", abstract).split())

# ------------------------------------------------------------------------------------------------ front matter
head = r"""% Environmental Research Letters (IOP Publishing, ISSN 1748-9326): IOP `iopjournal` class, single-column preprint output.
% Written by paper_erl/build_main.py. Compile: pdflatex main && bibtex main && pdflatex main && pdflatex main. Add [anonymous] to \documentclass for double-anonymous review.
\documentclass{iopjournal}
\usepackage{amsmath,amssymb}
\usepackage{booktabs}
\usepackage{array}
\usepackage{algorithm}
\usepackage{algpseudocode}
\setlength{\emergencystretch}{3em}
\newcommand{\dinoseg}{StrongDINOv2Seg}
\newcommand{\Lcost}{L_{\mathrm{cost}}}
\newcommand{\pending}[1]{\textcolor{red}{\textit{#1}}}
\algrenewcommand\algorithmicrequire{\textbf{Input:}}
\algrenewcommand\algorithmicensure{\textbf{Output:}}

\begin{document}
\articletype{Letter}
\title{Smart village infrastructure planning and road network optimization for rural Telangana}
\author{Ramakrishna Kolikipogu$^{1,*}$ and Pendyala Archana$^{1}$}
\affil{$^1$Department of Information Technology, Chaitanya Bharathi Institute of Technology (A), Hyderabad, India}
\affil{$^*$Author to whom any correspondence should be addressed.}
\email{krkrishna.cse@gmail.com, pendyalaarchanareddy98@gmail.com}
\keywords{rural roads, building footprint extraction, satellite remote sensing, least-cost path, shared network, spatial transferability, open geospatial data, Telangana}
% abstract: """ + f"{words} words" + r"""
\begin{abstract}
""" + abstract + r"""
\end{abstract}

"""

# ------------------------------------------------------------------------------------------------ 1 introduction
intro = r"""
\section{Introduction}
Road building is among the most consequential land-use changes of the coming decades. Global road length is projected to grow by roughly 3.0--4.7 million km by 2050 \cite{meijer2018global}, and new roads open land to clearing, fragmentation and conversion \cite{laurance2014global}. Much of this growth is local. In India the Pradhan Mantri Gram Sadak Yojana (PMGSY) connects habitations through all-weather rural roads \cite{pmgsy}, and planning for such schemes depends on knowing where dwellings and facilities are, what terrain and land cover a corridor must cross, and which connection rule is applied.

Computational support for this planning has matured along three separate lines. Remote sensing now maps buildings and roads at large scale, from continental building inventories \cite{sirko2021openbuildings} to foundation-model segmenters \cite{oquab2023dinov2}, with recent work addressing small and isolated rural buildings, uncertainty and domain shift \cite{r62,r63,r64,r65,r66,r67,r68,r69,r70}. Multi-criteria and least-cost analysis translates terrain and land cover into route costs \cite{r06,r53,r54,collischonn2000lcp}. Network-design formulations connect many demand points at low total cost, including Steiner-tree heuristics \cite{kou1981steiner,mehlhorn1988steiner,hwang1992steiner,r51}, rural road design models \cite{r41,r43,r44} and analogues for power and transport networks \cite{r45,r46,r47,r50}. These lines are rarely joined: detectors are judged by pixel overlap \cite{r01}, planners assume an error-free inventory, and each house is often connected independently, so neighbouring houses re-trace the same corridor.

We join them in one reproducible pipeline (figure~\ref{fig:arch}) and apply it, unchanged, to four settlements of different morphology in Telangana. The study is organised as a progression. A rural pilot, Damarakunta, fixes the method: the segmentation checkpoint, the cost surface, the building clearance and the two-stage planner. The same frozen checkpoint and routing rules are then transferred, without retraining, to Adilabad (urban fringe), Aswaraopeta (semi-urban, tribal fringe) and Alampur (heritage town), and what changes at each step---density of buildings and roads, number and kind of facilities, and the distribution of road-gap households---is documented. Our contributions are:
\begin{enumerate}
\item \textbf{End-to-end pipeline.} A chain from satellite imagery to a shared access network: \dinoseg{} segmentation, OpenCV/NumPy distance-transform instance extraction with an explicit merge flag, a four-pass multi-source facility audit with roof snapping, a multi-criteria cost surface with a 5~m zero-crossing building clearance, and a two-stage shared-network planner (Section~\ref{sec:methods}).
\item \textbf{Grid resolution and clearance.} A comparison of a $10$~m soft-penalty grid with the $5$~m hard-clearance grid, showing that only the latter removes building crossings in every settlement while keeping the saving from sharing (Section~\ref{sec:grid}).
\item \textbf{Four-settlement transferability.} A like-for-like comparison of a rural village, an urban fringe window, a semi-urban town and a heritage town under identical models and rules, set against three baseline routing strategies (Section~\ref{sec:results} and Appendix~\ref{app:robust}).
\end{enumerate}
Two scope limits apply. Four settlements in one state were evaluated, so we make no claim about a general rural--semi-urban--urban gradient beyond them. And the segmentation results are unvalidated in every area: no reference building mask exists, and in the dense fabric of Adilabad (49\% of instances), Aswaraopeta (35\%) and Alampur (38\%) many detected instances are merged roof blocks, so their targets are built-up units rather than counted houses.

\subsection{Related work}
\textbf{Building extraction.} Reviews of building extraction from remote sensing \cite{r01} document the shift from fully convolutional networks \cite{ji2019whu} to transformer and foundation-model encoders. Recent studies target isolated small buildings \cite{r63}, weak supervision \cite{r62}, uncertainty-guided refinement \cite{r64,r65}, and domain generalisation or adaptation across imagery sources \cite{r02,r66,r67,r68,r69,r70}. Road extraction has followed the same path, with width-adaptive, topology-preserving and foundation-model-based networks for rural and arid scenes \cite{r56,r57,r58,r59,r60}, and topological analysis has been used to detect informal settlements worldwide \cite{r48}. Evaluation is overwhelmingly through overlap scores on benchmark data \cite{foody2002status}; the effect of detection errors on downstream infrastructure decisions is rarely quantified, although error propagation in GIS models is long established \cite{heuvelink1998error}.

\textbf{Route and network planning.} Multi-criteria GIS analysis \cite{r06} and least-cost path methods \cite{collischonn2000lcp,r53,r54} underlie corridor selection for roads, with dedicated treatments of slope \cite{r54}, route alternatives \cite{r53} and travel-time uncertainty \cite{r61}, and GIS route reconstruction has been applied to historical transport routes \cite{r55}. Rural road design has been addressed with improved network-design models \cite{r41}, algorithmic planning under constrained capacities in India \cite{r43} and facility-based methodology \cite{r44}. Steiner-tree formulations \cite{hwang1992steiner} and their shortest-path-based heuristics \cite{kou1981steiner,mehlhorn1988steiner} connect many terminals at low total length and are applied to sub-network identification \cite{r51}, multi-terminal routing \cite{r52}, cable routing \cite{r45}, minimum spanning trees of road networks \cite{r46}, rural grids \cite{r47} and least-cost electrification \cite{r50}.

\textbf{Gap.} To our knowledge no cited work combines (i) satellite-derived building instances, (ii) a land-cover- and slope-based cost surface with building avoidance, (iii) a shared-network planner whose marginal cost credits built corridors, and (iv) a systematic test of how inventory omissions and the settlement setting change the result. This paper addresses that combination for rural Telangana and treats the comparison between four settlements as an explicit transferability test.
"""

# ------------------------------------------------------------------------------------------------ 2 study areas and data
study = r"""
\section{Study areas and data}\label{sec:data}
\subsection{Four settlements}
Four settlements are studied (table~\ref{tab:areas}; figure~\ref{fig:flow}), arranged from the rural pilot to progressively denser or more specialised fabrics. All use UTM zone 44N (EPSG:32644) and the same open data stack (table~\ref{tab:data}). The boundaries of Adilabad, Aswaraopeta and Alampur are built-up settlement extents derived from open data, not administrative polygons, because no official village or town polygon was available for them; each carries a provenance file with its derivation and an edge-continuity check against ESA WorldCover.

\textbf{Damarakunta (Siddipet district, rural).} A rural revenue village in Markook mandal ($17.707^{\circ}$N, $78.753^{\circ}$E). Its boundary, from the Telangana State Remote Sensing Application Centre (TGRAC), encloses 18.47~km$^2$ with 51.7~km of mapped road and a mean slope of 3.8\%; settlement is dispersed, with small house clusters separated by farmland. A 0.6~m mosaic (11{,}296 $\times$ 7{,}171 px) was assembled from Esri imagery and segmented in 459 tiles. The segmenter yields 278 building polygons, 165 inside the boundary (\textsc{Plausible} 71, \textsc{Review} 32, \textsc{Unresolved\_Merge} 62, the last denoting blobs that merge adjacent roofs), of which 163 lie more than 30~m from a road and become routing targets. The facility audit (section~\ref{sec:audit}) retains five verified facilities: two schools, one health sub-centre and two gram-panchayat offices; the TGRAC anganwadi layer gives all its records one shared village coordinate and was rejected as a placeholder.

\textbf{Adilabad (Adilabad district, urban fringe).} The study area is the built-up settlement extent of Adilabad town, derived from ESA WorldCover (class 50) around the OpenStreetMap place node ($19.676^{\circ}$N, $78.534^{\circ}$E): 18.59~km$^2$, spanning the Adilabad Urban mandal (50.5\%), Mavala (32.2\%) and Adilabad Rural (17.4\%), with 509.9~km of mapped road and a mean slope of 3.1\%. It has the same area as Damarakunta but a very different fabric: the segmenter yields 5{,}653 building instances (\textsc{Plausible} 2{,}526, \textsc{Review} 181, \textsc{Unresolved\_Merge} 2{,}773, and 173 smaller than 30~m$^2$), 34 times as many as the pilot, and the road layer is ten times longer. The road-gap rule selects 613 targets. The audit retains 132 verified facilities (39 schools, 15 colleges, 59 hospitals and health centres, 15 government offices and four anganwadis), the district-level institutions of the main town.

\textbf{Aswaraopeta (Bhadradri Kothagudem district, semi-urban, tribal fringe).} The headquarters town of Aswaraopeta mandal ($17.241^{\circ}$N, $81.128^{\circ}$E). No village or town polygon exists for it in OpenStreetMap or Overture, so the study area is the built-up extent derived from ESA WorldCover around the Overture locality point: 2.82~km$^2$, one-seventh of the Adilabad window, with 28.6~km of mapped road and a mean slope of 3.1\%. The segmenter yields 1{,}297 building instances (\textsc{Plausible} 772, \textsc{Review} 18, \textsc{Unresolved\_Merge} 452, and 55 smaller than 30~m$^2$); 52\% of the footprints lie more than 30~m from a mapped road, so the road-gap rule selects 678 targets, more than in the 6.6-times larger Adilabad window. The audit retains 32 verified facilities (5 schools, 3 colleges, 7 hospitals and health centres, 3 government offices and 14 anganwadis).

\textbf{Alampur (Jogulamba Gadwal district, heritage, semi-urban).} A small town on the Tungabhadra in Alampur mandal ($15.880^{\circ}$N, $78.135^{\circ}$E), known for its temple complex. OpenStreetMap maps it only as a point, so the study area is the settlement extent derived from Overture building footprints around that node: 1.65~km$^2$, the smallest and flattest window (mean slope 2.1\%), with 25.3~km of mapped road. The segmenter yields 430 building instances (\textsc{Plausible} 208, \textsc{Review} 26, \textsc{Unresolved\_Merge} 163, and 33 smaller than 30~m$^2$), and only 59 are road-gap targets because mapped roads already serve the dense core. The audit retains nine verified facilities (one school, one college, two hospitals and health centres and five anganwadis; no government office lies inside the polygon), several of them absent from Overture Places.

\begin{table}[t]
\caption{The four study areas and the data layers of each. Top: area profiles (road length is the mapped road layer inside the polygon; slope is the mean terrain slope over the polygon). Middle: the layer used in every area; the verified-facility and footprint rows give the number of facilities and of extracted buildings. Bottom: the datasets with resolution, version, licence and location (TGRAC: Telangana State Remote Sensing Application Centre; OSM: OpenStreetMap; WorldCover: ESA WorldCover land-cover map; DEM: digital elevation model; SRTM: Shuttle Radar Topography Mission; GLO-30: Copernicus global 30~m DEM; LoveDA: Land-cover Domain Adaptive semantic segmentation dataset; ODbL: Open Database Licence; CC BY: Creative Commons Attribution).}
\label{tab:areas}\label{tab:data}
\centering
\scriptsize
\renewcommand{\arraystretch}{1.1}
\begin{tabular}{@{}>{\raggedright\arraybackslash}p{2.5cm}>{\raggedright\arraybackslash}p{2.7cm}>{\raggedright\arraybackslash}p{2.7cm}>{\raggedright\arraybackslash}p{2.7cm}>{\raggedright\arraybackslash}p{2.7cm}@{}}
\toprule
 & Damarakunta & Adilabad & Aswaraopeta & Alampur\\
\midrule
District & Siddipet & Adilabad & Bhadradri Kothagudem & Jogulamba Gadwal\\
Typology & Rural & Urban fringe & Semi-urban, tribal fringe & Heritage, semi-urban\\
Window (km$^2$) & 18.47 & 18.59 & 2.82 & 1.65\\
Existing roads (km) & 51.7 & 509.9 & 28.6 & 25.3\\
Mean slope (\%) & 3.8 & 3.1 & 3.1 & 2.1\\
\midrule
Boundary & TGRAC village polygon & Built-up extent from WorldCover around the OSM place node & Built-up extent from WorldCover around the Overture locality point & Built-up extent from Overture footprints around the OSM place node\\
Existing roads & TGRAC road layer & Overture and OSM & Overture and OSM & Overture and OSM\\
Public facilities & 5 verified & 132 verified & 32 verified & 9 verified\\
Building footprints & 165 from \dinoseg{} on 0.6~m Esri imagery & 5{,}653 from \dinoseg{} on 0.6~m Esri imagery & 1{,}297 from \dinoseg{} on 0.6~m Esri imagery & 430 from \dinoseg{} on 0.6~m Esri imagery\\
Land cover & \multicolumn{4}{@{}p{11cm}}{ESA WorldCover, 10~m, v200 (all four areas)}\\
Terrain & SRTM 1 arc-second, 30~m & \multicolumn{3}{@{}p{8.4cm}}{Copernicus DEM GLO-30, 30~m (same Sobel slope method; the two DEMs agree to RMSE 2.3~m over Damarakunta)}\\
Training benchmark & \multicolumn{4}{@{}p{11cm}}{LoveDA, one checkpoint for all four areas}\\
\bottomrule
\end{tabular}

\medskip
\begin{tabular}{@{}>{\raggedright\arraybackslash}p{2.7cm}>{\raggedright\arraybackslash}p{1.9cm}>{\raggedright\arraybackslash}p{2.0cm}>{\raggedright\arraybackslash}p{2.7cm}>{\raggedright\arraybackslash}p{4.2cm}@{}}
\toprule
Dataset (use) & Resolution & Version & Licence & URL / DOI\\
\midrule
Esri World Imagery (imagery, 0.6~m tiles) & 0.6~m & live service & Esri terms; academic use, credit required & \url{services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer}\\
TGRAC / BharatMaps (Damarakunta boundary, roads, facilities) & vector & as supplied & provider terms & \url{tgrac.telangana.gov.in}, \url{bharatmaps.gov.in}\\
Overture Maps (buildings, roads, places) & vector & 2026-10-21.0 & ODbL 1.0; CDLA-Permissive-2.0 & \url{overturemaps.org}\\
OpenStreetMap (boundary candidates, facilities) & vector & live (Overpass, Photon) & ODbL 1.0 & \url{openstreetmap.org/copyright}\\
ESA WorldCover (land cover) & 10~m & v200 (2021) & CC BY 4.0 & \url{doi.org/10.5281/zenodo.7254221}\\
Copernicus DEM GLO-30 (slope) & 30~m, slope at 10~m & GLO-30 & Copernicus licence & \url{doi.org/10.5270/ESA-c5d3d65}\\
LoveDA (segmentation training, validation) & 0.3~m & 2021 & CC BY-NC-SA 4.0 & \url{doi.org/10.5281/zenodo.5706578}\\
Wikidata, Wikipedia (facility audit) & points & live & CC0; CC BY-SA 4.0 & \url{wikidata.org}\\
\bottomrule
\end{tabular}
\end{table}
"""

# ------------------------------------------------------------------------------------------------ 3 methodology
method = r"""
\section{Methodology}\label{sec:methods}
\subsection{Pipeline overview}
The workflow (figure~\ref{fig:arch}) has five stages that are identical for all four settlements. (1)~Multi-source open geospatial data are ingested: 0.6~m Esri World Imagery, TGRAC/BharatMaps boundaries and roads (Damarakunta), Overture and OpenStreetMap roads, ESA WorldCover v200 land cover, the Copernicus GLO-30 elevation model and verified public-facility coordinates. (2)~\dinoseg{} segments the imagery. (3)~Building footprints are extracted from the segmentation, road-gap target buildings are identified (more than 30~m from an existing road) and facilities are snapped onto footprints. (4)~A terrain and land-cover cost surface $C(x,y)$ is built on a 5~m routing grid with a hard 3.6~m building clearance. (5)~Two-stage network optimisation connects the targets: Stage~A computes independent Dijkstra least-cost routes and Stage~B consolidates them into a shared, Steiner-like network; the result is benchmarked against a PMGSY corridor cost.

\begin{figure}[t]
\centering
\includegraphics[width=\textwidth]{fig_architecture.png}
\caption{End-to-end architecture, shown for the four study areas: (1)~multi-source open geospatial inputs (roads from TGRAC and OSM, ESA WorldCover land cover, Copernicus DEM elevation, $F_i$ the verified facilities), (2)~\dinoseg{} semantic segmentation of $560\times560\times3$ RGB tiles (DINOv2 ViT-B/14: self-supervised vision transformer, base size, 14~px patches; FPN: feature pyramid network; ASPP: atrous spatial pyramid pooling), (3)~morphological and watershed building-footprint extraction with road-gap targets ($>30$~m from roads) and facility snapping, (4)~$5$~m cost surface with a hard $3.6$~m building-clearance mask, (5)~Stage~A independent Dijkstra routes, Stage~B shared-trunk Steiner consolidation and the decision outputs.}
\label{fig:arch}
\end{figure}

\subsection{Semantic segmentation: StrongDINOv2Seg}
\dinoseg{} is a fully fine-tuned DINOv2 ViT-B/14 encoder \cite{oquab2023dinov2}. Tokens from blocks 3, 6, 9 and 12 are projected to 256 channels and fused FPN-style \cite{lin2017fpn}, passed through an ASPP neck (rates 6, 12, 18) \cite{chen2018deeplabv3plus} and a four-stage decoder of residual convolution blocks (256, 128, 64 and 32 channels) with auxiliary heads for deep supervision \cite{lee2015dsn}. \emph{Why LoveDA.} Telangana has no village-level pixel labels, and drawing them for every settlement would defeat the purpose of an open-data planning tool. LoveDA \cite{wang2021loveda} supplies standardised multi-class remote-sensing land-cover imagery, with urban and rural scenes and seven classes (background, building, road, water, barren, forest and agriculture), so it serves to pre-train and benchmark \dinoseg{} once; the frozen checkpoint is then applied to the open-data Telangana planning windows without any village-by-village labelling. Training used LoveDA at 560~px for a scheduled 10 epochs (AdamW, cosine schedule to $10^{-7}$, encoder learning rate $\times 0.1$); the epoch-4 checkpoint is used for all four settlements, frozen, with SHA-256 \texttt{2e7c4646dc77ceb2\allowbreak a357f44f11cb3f7f\allowbreak f84e636871d70ba4\allowbreak c31e194e5ec00cf3}. With logits $\mathbf z$, labels $y$, class probabilities $p_{ic}$ and one-hot targets $t_{ic}$ at pixel $i$ (class 0 is ignored), the loss is
\begin{equation}
\mathcal L(\mathbf z,y)=0.5\,\mathcal L_{\mathrm{CE}}+0.4\,\mathcal L_{\mathrm{Dice}}+0.1\,\mathcal L_{\mathrm{edge}},\qquad
\mathcal L_{\mathrm{total}}=\mathcal L(\mathbf z^{\mathrm{main}},y)+0.4\sum_{j=1}^{3}\mathcal L(\mathbf z^{(j)},y),
\label{eq:loss}
\end{equation}
\begin{equation}
\begin{aligned}
\mathcal L_{\mathrm{Dice}}&=\frac1{|\mathcal C|}\sum_{c\in\mathcal C}\Bigl(1-\frac{2\sum_i p_{ic}t_{ic}+\varepsilon}{\sum_i p_{ic}+\sum_i t_{ic}+\varepsilon}\Bigr),\\
\mathcal L_{\mathrm{edge}}&=\frac1{|\Omega|}\sum_{i\in\Omega}(1+4e_i)\,\mathrm{CE}_i,\qquad e_i=\min\{1,\,|(K_x{*}y)_i|+|(K_y{*}y)_i|\}.
\end{aligned}
\label{eq:diceedge}
\end{equation}
Here $\mathcal C$ is the set of scored classes, $\varepsilon$ a small smoothing constant, and $K_x,K_y$ the Sobel kernels, so that the edge term up-weights the cross-entropy of pixels on label boundaries by up to a factor of five \cite{milletari2016vnet}; the three auxiliary heads $\mathbf z^{(j)}$ provide deep supervision. From the confusion matrix, with $TP_c,FP_c,FN_c$ the true positives, false positives and false negatives of class $c$ and $N$ the number of labelled pixels,
\begin{equation}
\begin{aligned}
\mathrm{OA}&=\frac{\sum_c TP_c}{N},\qquad P_c=\frac{TP_c}{TP_c+FP_c},\qquad R_c=\frac{TP_c}{TP_c+FN_c},\\
F_{1,c}&=\frac{2P_cR_c}{P_c+R_c}=\frac{2TP_c}{2TP_c+FP_c+FN_c},\qquad \mathrm{IoU}_c=\frac{TP_c}{TP_c+FP_c+FN_c},
\end{aligned}
\label{eq:metrics}
\end{equation}
and $P$, $R$, $F_1$ (the Dice coefficient) and $\mathrm{mIoU}=|\mathcal C|^{-1}\sum_{c\in\mathcal C}\mathrm{IoU}_c$ are the macro averages over the scored classes; because $F_{1,c}$ equals the per-class Dice score, the reported F1-score is the mean Dice.

\subsection{Tiled inference, footprint extraction and road-gap targets}\label{sec:extract}
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

\subsection{Facility audit and roof snapping}\label{sec:audit}
Overture Places alone mislocated or missed colleges, hospitals, offices and anganwadis, so the facilities of each area come from a four-pass audit (\texttt{scripts/audit\_facilities.py}). Pass~1 harvests candidates inside and within 500~m of the polygon from OpenStreetMap (Overpass and the Photon geocoder), Overture Places, Wikidata and Wikipedia (and, for Damarakunta, the TGRAC layers). Pass~2 assigns one of five categories (School, College, Hospital, Government Office, Anganwadi), removes closed or commercial records (pharmacies, laboratories, coaching centres, banks, cooperative societies), religious sites, foreign place names and placeholder coordinates shared by several differently named records, and merges duplicates of one campus across sources; every removal is logged with its reason. Pass~3 moves each survivor onto the footprint that contains it or, failing that, the nearest footprint of at least 25~m$^2$ within 35~m (a compound building up to 25~m away for a school, college or hospital), and removes facilities with no building in range. Ten of the 68 verified facility points of the first Adilabad run shared an identical coordinate with another Overture record (generic geocodes), so a 20~m footprint check is weak evidence in dense fabric, which is why the audit rejects placeholder coordinates. Pass~4 writes the verified table with the sources, the snap distance and a confidence label; records with a single source and a snap of more than 12~m are kept with \texttt{use\_in\_analysis}${}=$\,False and are not routed.

\subsection{Cost surface and zero-crossing building clearance}\label{sec:cost}
Let $\mathcal B$ be blocked cells (water, invalid cells, slope $>25^{\circ}$) and $\mathcal P$ the cells whose centre lies inside a footprint. The 10~m comparison graph has the unblocked cells as nodes and 8-neighbour edges with no diagonal corner-cutting, and the cell cost is
\begin{equation}
c(x)=\bigl[c_{\mathrm{lc}}(\ell(x))+g(S(x))\bigr]\,m(x),\qquad m(x)=\begin{cases}\mu & x\in\mathcal P\\ 1 & \text{otherwise,}\end{cases}
\label{eq:cell}
\end{equation}
where $\ell$ is the WorldCover class with resistance $c_{\mathrm{lc}}=8,5,3,6,2,4$ for trees, shrubland, grassland, cropland, built-up and bare/sparse land (classes 10, 20, 30, 40, 50, 60), $g(S)=w_s\min(S,S_{\mathrm{ref}})/S_{\mathrm{ref}}$ with $w_s=4$ and $S_{\mathrm{ref}}=10^{\circ}$, and $\mu=4$ is the soft footprint penalty. Slope comes from the Copernicus GLO-30 elevation $z$ with the Sobel gradient at the DEM spacing $\Delta_z=30$~m, resampled bilinearly to the planning grid:
\begin{equation}
\partial_x z\approx\frac{(K_x{*}z)}{8\Delta_z},\quad \partial_y z\approx-\frac{(K_y{*}z)}{8\Delta_z},\quad S=\arctan\sqrt{(\partial_x z)^2+(\partial_y z)^2},\quad p_S=100\tan S,
\label{eq:slope}
\end{equation}
with $S$ in degrees and $p_S$ the percentage slope reported in the tables; no separate IRC slope-penalty factor is applied. The soft penalty lets a route cross a roof when the detour costs more, so the proposed plan uses a hard barrier on a finer grid. Each 10~m cost cell is refined to $2\times2$ cells of size $\Delta=5$~m with the same cost per metre, and with $D(x)$ the Euclidean distance from the centre of cell $x$ to the nearest footprint (zero inside a footprint),
\begin{equation}
\begin{aligned}
C(x)&=c_{\mathrm{lc}}(\ell(x))+g(S(x))+C_{\mathrm{bldg}}(x),\\
C_{\mathrm{bldg}}(x)&=\begin{cases}\infty & D(x)\le r_c\\ 0 & \text{otherwise,}\end{cases}\qquad r_c=3.6\ \mathrm{m},\ \Delta=5\ \mathrm{m}.
\end{aligned}
\label{eq:bldg}
\end{equation}
Because $r_c>\Delta\sqrt2/2=3.54$~m, no step between two free cell centres can touch a footprint: a point of the step lies within $\Delta\sqrt2/2$ of one of its end points, and that end point would then have been blocked. A target sits inside its own building, so each route starts at the edge of that building and reaches the nearest free cell connected to the road network by a straight lane of at most the snap distance that touches no other footprint; a target with no such lane (a house enclosed by other buildings) is reported as unrouted, never routed over a roof. Lengths are measured from the building edge, and every drawn route (lane, path and road attachment) is finally intersected with all footprints other than its own.

\subsection{Two-stage network optimisation}\label{sec:routing}
The graph has the free cells as nodes and 8-neighbour edges, a diagonal step being allowed only if both orthogonal neighbours are free. The weight of an edge $(u,v)$ is
\begin{equation}
w(u,v)=d(u,v)\,\frac{C(u)+C(v)}{2},\qquad d(u,v)=\begin{cases}\Delta&\text{cardinal step}\\ \sqrt2\,\Delta&\text{diagonal step.}\end{cases}
\label{eq:edge}
\end{equation}
Stage~A gives every target $t$ the independent least-cost path $\pi_t^{A}=\arg\min_{\pi:\,t\to R}\sum_{e\in\pi}w(e)$ to the existing road cells $R$ \cite{dijkstra1959note,hart1968astar,collischonn2000lcp}, and two further alternatives that multiply $w(e)$ by $\lambda\in\{3,8\}$ on cells within 20~m of the earlier paths and overlap them by at most 80\% ($K=3$ alternatives in total). Stage~B starts from $E_S=\emptyset$ and repeatedly serves the target and route with the highest weight per marginal cost,
\begin{equation}
(t^\star,\pi^\star)=\arg\max_{t\in U,\ \pi\in\Pi_t\cup\{\pi_t^{\mathrm{net}}\}}\frac{\omega_t}{\Delta\Lcost(\pi\mid S)},\qquad
\Delta\Lcost(\pi\mid S)=\sum_{e\in\pi\setminus E_S}w(e),
\label{eq:stageb}
\end{equation}
where $U$ is the set of unserved targets, $\Pi_t$ the Stage~A alternatives, $\pi_t^{\mathrm{net}}$ the least-cost path to the roads together with the routes already selected, and $\omega_t$ the priority weight (4 for hospitals and health centres, 3 for schools, colleges and anganwadis, 2 for government offices, 1 for houses). A built edge $e\in E_S$ costs nothing again---a discount factor $\alpha=0$ on $E_S$---so a route may end on another route; this is the shortest-path heuristic for Steiner trees \cite{kou1981steiner,mehlhorn1988steiner} on a penalised, land-cover-weighted graph with the road network as a free sub-tree, and it carries no optimality guarantee. Two passes of leaf re-routing follow. Snap distance is 30~m, search limit 1{,}500~m and attachment tolerance 15~m; facilities are planned in a separate phase.

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

\subsection{Evaluation metrics and PMGSY cost benchmark}\label{sec:eval}
With $L(\cdot)$ the total length of the unique edges of a route set (shared edges counted once), the saving of the shared network and the exposure of dwellings are
\begin{equation}
\begin{aligned}
\rho&=\frac{L_A-L_B}{L_A}\times100\%,\qquad L_A=L\bigl(\{\pi_t^A\}\bigr),\quad L_B=L(E_S),\\
X&=\sum_{r}\Bigl|r\cap\bigcup_{b\ne b_r}b\Bigr|=0.
\end{aligned}
\label{eq:saving}
\end{equation}
where $X$ is the length of routes inside footprints other than the route's own building $b_r$ (zero by construction under equation~\ref{eq:bldg}). The corridor cost is benchmarked against the PMGSY programme \cite{pmgsy}:
\begin{equation}
\mathrm{Cost}_{\mathrm{INR\ lakh}}=L_B[\mathrm{km}]\times c_{\mathrm{PMGSY}},\qquad c_{\mathrm{PMGSY}}=75\ \text{lakh/km}\ (\text{sensitivity range }60\text{--}90),
\label{eq:cost}
\end{equation}
with 1 lakh $=10^{5}$~INR. This unit rate is the single benchmark used throughout for the unique shared corridor; it excludes land, drainage structures and variation in cross-section, and its scope is stated in section~\ref{sec:limits}. Four strategies are compared on the 10~m soft-penalty grid in all four settlements: straight lines, independent least-cost routes, a length-only control (cost surface replaced by distance), a roads-only shared reference (routes may share edges only with the existing road network) and the two-stage shared plan. The exposure metrics are the number of routes crossing another house's footprint and the route length inside other footprints. As a pilot test of inventory error, on Damarakunta alone a random subset of targets is removed from the targets and from the penalty layer (a missed detection is absent from both) and the planner is re-run, with random draws using seeds 1--5; coverage and the change in unique length are recorded.
"""

# ------------------------------------------------------------------------------------------------ 4 results
def eris_block(start, end):
    i = ERIS.index(start)
    j = ERIS.index(end, i + 1) if end else len(ERIS)
    return ERIS[i:j]

results = r"""
\section{Results}\label{sec:results}
The results follow the progression of the study. The pilot (Damarakunta) shows what the pipeline produces and fixes the checkpoint, thresholds and cost rules; each later settlement then changes one thing---building density (Adilabad), target density and a sparse road layer (Aswaraopeta), or scale and heritage fabric (Alampur)---while the weights, the checkpoint and the planner stay fixed, so that differences in the output can be attributed to the settlement and not to retuning.

\subsection{Segmentation: StrongDINOv2Seg on LoveDA}
On the 1{,}669-image LoveDA validation split (560~px tiles, seven scored classes) the epoch-4 checkpoint reached 53.8\% mIoU, 68.9\% Dice (equal to the macro F1-score), 71.3\% pixel accuracy, 72.4\% macro precision and 66.9\% macro recall; for the Building class IoU is 54.0\%, Dice 70.1\%, precision 62.1\% and recall 80.6\% (table~\ref{tab:seg}). The high building recall is what the routing task needs: a missed roof removes a household from the plan, whereas a spurious blob is absorbed by the merge flag and the 25~m$^2$ minimum. For orientation, table~\ref{tab:seg} lists the published test-set mIoU of other LoveDA baselines; they were scored on the benchmark's test split with different protocols, so the comparison is indicative, not a like-for-like ranking. The scores are source-domain figures: they describe the LoveDA validation images, not the four Telangana settlements, for which no surveyed reference mask exists. The Telangana footprints are therefore assessed through their consequences for planning (section~\ref{sec:disc}) and, for Damarakunta, against Google Open Buildings v3 (appendix~\ref{app:robust}: 118 of the 165 candidates, 71.5\%, agree).

\begin{table}[t]
\caption{Semantic segmentation on LoveDA. mIoU is the mean intersection over union over classes, F1 is the harmonic mean of precision and recall (equal to the Dice coefficient), and precision and recall are the share of predicted pixels that are correct and of true pixels that are found. (a)~Published mIoU of the benchmark baselines (test split, from the cited papers) next to \dinoseg{} (our 1{,}669-image validation split, so the comparison is indicative). (b)~Validation metrics of \dinoseg{} at 560~px: macro averages over the seven scored classes and the Building class alone; F1 equals Dice. Overall pixel accuracy, a whole-image quantity with no per-class counterpart, is 71.3\%.}
\label{tab:seg}
\centering
\small
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

\medskip
\begin{tabular}{@{}lrrrr@{}}
\toprule
\multicolumn{5}{@{}l}{\textit{(b) \dinoseg{} validation metrics (560~px, 1{,}669 images)}}\\
Scope & mIoU (\%) & F1 / Dice (\%) & Precision (\%) & Recall (\%)\\
\midrule
All 7 classes (macro) & 53.8 & 68.9 & 72.4 & 66.9\\
Building class & 54.0 & 70.1 & 62.1 & 80.6\\
\bottomrule
\end{tabular}
\end{table}

\subsection{Pipeline output across the four settlements}
Figure~\ref{fig:flow} follows the chain of figure~\ref{fig:arch} for the four areas: for each, the input (0.6~m imagery, boundary and existing roads) is paired with the final output (extracted footprints, verified facilities and the Stage~B shared network). Table~\ref{tab:four} at the end of this section collects every metric of the four areas.

\begin{figure*}[p]
\centering
\IfFileExists{fig_flow_study_areas.png}{\includegraphics[width=0.93\textwidth]{fig_flow_study_areas.png}}{\fbox{\parbox{0.8\textwidth}{\centering\pending{Figure not generated yet: run \texttt{python scripts/build\_paper\_flow\_figure.py --source segmentation} on the PC that holds the segmentation results.}}}}
\caption{Study areas and end-to-end flow. Left: Telangana with district outlines (geoBoundaries \cite{runfola2020geoboundaries}) and the four study locations (1~Damarakunta, rural; 2~Adilabad, urban fringe; 3~Aswaraopeta, semi-urban, tribal fringe; 4~Alampur, heritage, semi-urban). Right, one strip per area: input (0.6~m Esri World Imagery, study-area boundary and existing road network) $\rightarrow$ final output (extracted building footprints, road-gap target houses in orange, verified facilities and the Stage~B shared network of the 5~m zero-crossing plan: blue for houses, red for facilities), with scale bar and north arrow. Stage~A is the set of independent least-cost routes and Stage~B the shared network that consolidates them. Below each output: Stage~A and Stage~B unique length, building crossings and facility count. Basemap imagery: Esri, Maxar, Earthstar Geographics, and the GIS User Community. Footprints are automatic detections and routes are planning alternatives.}
\label{fig:flow}
\end{figure*}

\subsection{Damarakunta: the baseline pilot}\label{sec:damar}
Damarakunta (18.47~km$^2$, 51.7~km of mapped roads, mean slope 3.8\%) is the baseline against which the other settlements are read. The segmenter yields 165 footprints, of which 163 lie more than 30~m from a road and become targets; five verified facilities (two schools, one hospital and two government offices) are added. On the 5~m grid with the 3.6~m clearance, 162 targets are routed (one house is enclosed by buildings and reported unrouted), Stage~A needs 7.56~km and Stage~B 5.98~km, a saving of 21.0\% that corresponds to Rs 448 lakh at the PMGSY benchmark, and no route crosses a roof. On the coarser 10~m soft-penalty grid the same targets leave 28 routes (209~m) inside other footprints. Against the other strategies on that grid (table~\ref{tab:strategies}) the two-stage plan saves 24.9\% of the unique length of independent routes, the roads-only shared reference 22.6\% and the length-only control is 3.4\% \emph{longer}, so in this dispersed village most of the saving comes from sharing. A pilot error test shows how inventory errors act: omitting a random 10\% of houses understates the planned length by 7.6\% and omitting all merged blobs by 29.4\%, while leaving 62 households (38.0\%) unserved, so a planner reading total length alone would underfund the scheme.

\subsection{Adilabad: dense urban fringe}\label{sec:adilabad_res}
Adilabad (18.59~km$^2$, 509.9~km of roads, mean slope 3.1\%) keeps the window size of the pilot but changes the density: the segmenter yields 5{,}653 footprints, 34 times as many, over a road layer ten times longer. Of these, 613 are road-gap targets and 607 are routed (six are enclosed). The audit verifies 132 facilities (39 schools, 15 colleges, 59 hospitals, 15 government offices and four anganwadis), far more than in the pilot. Stage~A needs 30.87~km and Stage~B 27.12~km, a saving of 12.2\% (Rs 2{,}034 lakh); the soft-penalty plan would have left 99 routes (677~m) inside footprints. On the 10~m grid the two-stage plan saves 14.4\%, the roads-only reference only 3.2\% and the length-only control 6.8\%. The smaller saving follows from the layout: the dense road layer already serves most houses, so the remaining targets are scattered and offer few shared trunks. The same checkpoint and planner produce a well-formed network in a fabric 34 times denser than the pilot, which is the main evidence of transfer without retraining.

\subsection{Aswaraopeta: sparse roads, dense targets}
Aswaraopeta (2.82~km$^2$, 28.6~km of roads, mean slope 3.1\%) is one-seventh of the area of Adilabad but has more road-gap targets: 678 against 613, from 1{,}297 footprints. Of the 678 targets 632 are routed; 46 are enclosed by neighbouring buildings and reported unrouted rather than routed over a roof. Thirty-two facilities are verified (14 anganwadis, 7 hospitals, 5 schools, 3 colleges and 3 government offices). Stage~A needs 36.89~km and Stage~B 27.57~km, a saving of 25.3\% (Rs 2{,}067 lakh), because many houses lie far from the sparse mapped road layer and can feed the same trunks; the soft-penalty plan leaves 157 routes (1{,}090~m) inside footprints, the most of any area. On the 10~m grid the two-stage plan saves 31.2\%, the roads-only reference 1.7\%, and the length-only control is 16.5\% longer than independent routing. High target density in a small window is the regime in which the shared network pays most and in which a hard clearance matters most.

\subsection{Alampur: a small heritage town}
Alampur is the smallest and flattest window (1.65~km$^2$, 25.3~km of roads, mean slope 2.1\%). The segmenter yields 430 footprints; 59 are targets (58 routed) and nine facilities are verified (five anganwadis, two hospitals, one school and one college). Stage~A needs 3.28~km and Stage~B 2.74~km, a saving of 16.2\% (Rs 206 lakh), and the soft-penalty plan leaves only five routes (33~m) inside footprints. On the 10~m grid the two-stage plan saves 17.8\%, the roads-only reference 4.9\% and the length-only control 8.2\%. Few targets, short routes and an existing road net close to most houses yield a modest saving; because the extent is small, its figures are noisier than those of the larger windows.

\subsection{Cross-settlement comparison}
The comparison (table~\ref{tab:four}) shows how the same pipeline responds to four fabrics. Building crossings are zero everywhere, against 28, 99, 157 and 5 routes under the 10~m soft penalty, so the clearance guarantee is independent of settlement type. The saving of the shared network ranges from 12.2\% in Adilabad to 25.3\% in Aswaraopeta; it is largest where targets are numerous, clustered and far from the mapped roads (Aswaraopeta, Damarakunta) and smallest where roads are dense and targets scattered (Adilabad), with Alampur between. Unique network length scales with the number of targets and the road coverage, not with the window size: Aswaraopeta needs almost as much new road as Adilabad (27.57~km against 27.12~km) from one-seventh of the area. Costs follow length, Rs 448, 2{,}034, 2{,}067 and 206 lakh, so Aswaraopeta is as expensive as Adilabad at the benchmark rate. The segmentation rows are model-level: they are the LoveDA scores of the one checkpoint used for all four areas.

\begin{table*}[t]
\caption{Four study areas side by side. Segmentation rows: LoveDA validation of the single \dinoseg{} checkpoint (overall accuracy is the share of correctly classified pixels; precision and recall are macro averages over classes; F1-score equals the mean Dice coefficient; mIoU is the mean intersection over union). Stage~A is independent least-cost routing and Stage~B the shared-trunk network; PMGSY is the Pradhan Mantri Gram Sadak Yojana rural road programme; 1 lakh $=10^{5}$ INR (Indian rupees); slope is the mean terrain slope in percent. Routing rows: unique lengths on the 5~m zero-crossing grid (Stage~A independent, Stage~B shared network, shared edges once); building crossings are routes inside another building's footprint; cost is the Stage~B length times Rs 75 lakh per km (range 60--90).}
\label{tab:four}
\centering
\scriptsize
\resizebox{\textwidth}{!}{\input{paper_comparison_table.tex}}
\end{table*}
"""

# ------------------------------------------------------------------------------------------------ 5 discussion, 6 conclusions
disc = r"""
\section{Discussion}\label{sec:disc}
\subsection{What transfers and what differs}
The planning stages transferred without modification to all four settlements: the same cost surface, clearance rule, solver parameters and metrics produced connected plans in a dispersed village, an urban fringe, a semi-urban town and a small heritage town, with zero building crossings throughout. Stage~B shortened the unique network in every area (21.0\% in Damarakunta, 12.2\% in Adilabad, 25.3\% in Aswaraopeta, 16.2\% in Alampur). The strategy comparison on the 10~m grid (table~\ref{tab:strategies}) gives the same ordering in all four areas: the two-stage plan is shortest (24.9\%, 14.4\%, 31.2\% and 17.8\% below independent routes), the length-only control is no reliable substitute (3.4\% and 16.5\% longer in Damarakunta and Aswaraopeta, 6.8\% and 8.2\% shorter in Adilabad and Alampur) and roads-only sharing recovers most of the gain only in the dispersed village (22.6\%, against 3.2\%, 1.7\% and 4.9\%). The value of a marginal-cost planner therefore grows where new routes can share with one another rather than with existing roads.

What differs between settlements is the mechanism, not the outcome. In Damarakunta the dispersed clusters leave long unserved stretches and the saving comes from shared village trunks. In Adilabad the dense road layer absorbs most targets and the remaining ones are scattered, so the saving is the smallest. In Aswaraopeta a sparse mapped road layer and 678 targets in 2.82~km$^2$ create the longest shared trunks and the largest saving. In Alampur few targets and a nearby road network limit both the length and the saving, and the small extent makes the figures noisy. The savings should therefore not be read as a ranking of settlement types: they reflect target density and road coverage as much as morphology.

\subsection{Why pixel metrics are not enough for infrastructure use}
Segmentation metrics are area-weighted over classes, while the planner counts instances. In the pilot error test on Damarakunta, a detector that misses the smallest quarter of buildings removes a quarter of households from the plan (122 of 163 routed, 41 unserved) and a detector that merges adjacent roofs can score a high pixel IoU yet strands 38\% of the houses in the merged-blob scenario. Network length falls in both cases, so total length is a poor quality indicator. This matters most in the denser settlements, where merged roof blocks make up 49\% (Adilabad), 35\% (Aswaraopeta) and 38\% (Alampur) of the instances and the targets are built-up units rather than individual houses.

\subsection{Land take and planning use}
Shared corridors reduce the length of new road for the same households. As an illustration only, assuming a 5~m formation width (an assumption of this study; no road-width data were available), the length saved by Stage~B over Stage~A corresponds to about 0.79~ha less land take in Damarakunta (1.58~km), 1.88~ha in Adilabad (3.75~km), 4.66~ha in Aswaraopeta (9.32~km) and 0.27~ha in Alampur (0.53~km). For PMGSY-style schemes \cite{pmgsy,irc2002sp20} three points follow. Building inventories are uncertain inputs and a network sized from them should carry a sensitivity band. Shared corridors save between about one eighth and one quarter of unique length. Local overrides should be used sparingly and documented. The outputs are screening-level planning alternatives for field verification.

\subsection{Limitations and scope}\label{sec:limits}
Five limitations bound the claims of this study.
\begin{enumerate}
\item \emph{Scope.} Four settlements in one state were studied, so no general settlement gradient is claimed. The boundaries of Adilabad, Aswaraopeta and Alampur are derived built-up extents, not administrative polygons, and the Alampur extent is small (1.65~km$^2$), so its figures are noisy.
\item \emph{No field-surveyed masks.} No surveyed building mask exists for any Telangana area. The LoveDA scores are source-domain scores, and the footprints are assessed indirectly, through agreement with Open Buildings for Damarakunta (118 of 165 candidates, 71.5\%) and through a pilot omission test. Merged roof blocks make up 49\%, 35\% and 38\% of the instances in Adilabad, Aswaraopeta and Alampur, so their targets are built-up units, not individual houses. The verified facility lists come from open sources and are lower bounds, not a census.
\item \emph{Heuristic routing.} The shared network is a greedy Steiner-like heuristic with no optimality guarantee, the clearance plan reports targets enclosed by buildings as unrouted, and the saving depends on the road-gap threshold and on how complete the mapped road layer is. The omission test was run on Damarakunta only, so the sensitivity of the other three settlements to detection errors is untested.
\item \emph{Terrain source.} The frozen Damarakunta pilot uses an SRTM 1 arc-second elevation model and the other three use Copernicus GLO-30; the two agree to an RMSE of 2.3~m over Damarakunta, and the same slope method is applied to both.
\item \emph{Cost benchmark.} Costs are PMGSY-benchmarked at Rs 75 lakh per kilometre (sensitivity 60--90). The central rate is an assumption supplied by the project owner that we could not verify against a published PMGSY schedule, and it excludes land, drainage structures and cross-section variation, so the lakh figures indicate order of magnitude and relative scale, not budgets, and the plans are not designs to the IRC rural roads manual \cite{irc2002sp20}.
\end{enumerate}

\section{Conclusions}
A pipeline from satellite imagery and open layers to shared access roads connects the houses and facilities of four Telangana settlements without changing the cost surface or solver: a rural village (Stage~B 21.0\% shorter than independent routing), an urban fringe (12.2\%), a semi-urban town on a tribal fringe (25.3\%) and a small heritage town (16.2\%), with a 5~m building clearance that removes every route across a roof (the 10~m soft penalty left 28, 99, 157 and 5 routes across other footprints). A four-pass multi-source audit replaced raw Overture facility points with 5, 132, 32 and 9 verified facilities of five categories snapped onto roofs. Across all four settlements the shared plan is the shortest of the strategies compared, and sharing among new routes, not with existing roads, accounts for most of the gain wherever roads are dense. The effect of detection quality beyond the Damarakunta pilot, the completeness of the audited facility lists and the cost rate are the main open questions, and all results need field validation.
"""

# ------------------------------------------------------------------------------------------------ appendix + back matter

def strat_rows():
    """Routing-strategy comparison on the 10 m soft-penalty grid, four areas: three from the committed result CSVs, Damarakunta from the ledger-checked table of paper_eris/main.tex."""
    import pandas as pd
    names = {"Independent least-cost routes": "Independent routes", "Length-only control": "Length-only control", "Roads-only shared reference": "Roads-only shared reference", "Two-stage shared plan": "Two-stage shared plan"}
    dk = [("Independent routes", "163", "6{,}753.1", "0.0", "46", "328.3"), ("Length-only control", "163", "6{,}979.8", "$-3.4$", "64", "1{,}615.8"),
          ("Roads-only shared reference", "163", "5{,}229.3", "22.6", "29", "216.1"), ("Two-stage shared plan", "163", "5{,}069.0", "24.9", "28", "209.1")]
    out = []
    def block(label, rows, first=False):
        if not first:
            out.append(r"\midrule")
        for i, r in enumerate(rows):
            out.append((f"{label} " if i == 0 else "") + "& " + " & ".join(r) + r"\\")
    block("Damarakunta", dk, True)
    for k, folder in ((AD, "01_ADILABAD_UPDATED_SEGMENTATION"), (AS, "02_ASWARAOPETA_SEGMENTATION"), (AL, "03_ALAMPUR_SEGMENTATION")):
        df = pd.read_csv(REPO / "DELIVERABLES_CONTRIBUTION_3_MULTI_VILLAGE" / folder / "routing_strategy_comparison.csv").set_index("strategy")
        rows = []
        for key, nm in names.items():
            q = df.loc[key]
            sv = q.saving_vs_independent_pct
            svs = f"{abs(sv):.1f}" if sv >= 0 else f"$-{abs(sv):.1f}$"
            rows.append((nm, f"{int(q.targets_routed)}", f"{q.unique_len_m:,.1f}".replace(",", "{,}"), svs, f"{int(q.routes_crossing_other_footprints)}", f"{q.length_inside_other_footprints_m:,.1f}".replace(",", "{,}")))
        block(M[k]["label"], rows)
    return "\n".join(out)


app = r"""
\appendix
\setcounter{table}{0}
\renewcommand{\thetable}{A\arabic{table}}
\section{Routing strategies on the $10$~m grid}\label{app:robust}
Table~\ref{tab:strategies} compares four routing strategies in all four settlements on the $10$~m soft-penalty grid, with the same targets, cost surface and footprint penalty ($\mu=4$) in each area. Independent routes connect every target on its own least-cost path; the length-only control replaces the cost surface by distance; the roads-only shared reference lets routes share edges only with the existing roads; the two-stage plan is the shared network of section~\ref{sec:routing}. The routed count is the number of targets with a route, the saving $\rho$ is measured against the independent routes (negative when longer), and exposure is the number of routes that cross another house's footprint and their length inside footprints.

\begin{table}[t]
\caption{Routing strategies on the $10$~m soft-penalty grid in the four study areas. Unique length counts shared edges once; saving is against independent routes (negative: longer); routes crossing is the number of routes that cross another building's footprint, and the last column is their length inside footprints.}
\label{tab:strategies}
\centering
\scriptsize
\resizebox{\textwidth}{!}{\begin{tabular}{@{}llrrrrr@{}}
\toprule
Area & Strategy & Routed & Unique length (m) & Saving (\%) & Routes crossing & In footprints (m)\\
\midrule
""" + strat_rows().replace("\n& ", "\n& ") + r"""
\bottomrule
\end{tabular}}
\end{table}
"""

back = r"""
\ack{The authors acknowledge the Telangana State Remote Sensing Application Centre (TGRAC) for the boundary, road and facility layers of Damarakunta, and the providers of the open datasets used (ESA WorldCover, Copernicus DEM, Overture Maps, geoBoundaries, Google Open Buildings, LoveDA).}

\funding{This research received no specific grant from any funding agency in the public, commercial, or not-for-profit sectors.}

\roles{Ramakrishna Kolikipogu: conceptualization, supervision, writing -- review and editing. Pendyala Archana: methodology, software, investigation, formal analysis, visualization, writing -- original draft.}

\data{Code, derived summary tables and the open-data manifests with SHA-256 hashes are available at \url{https://github.com/Archana519/Telangana-Rural-Project} (folders \path{DELIVERABLES_DAMARAKUNTA_STAGE_B}, \path{DELIVERABLES_CONTRIBUTION_3_MULTI_VILLAGE} and \path{FINAL_PROJECT_OUTPUTS}). Imagery: Esri World Imagery (sources: Esri, Maxar, Earthstar Geographics, and the GIS User Community), used for non-commercial academic research and overlay under Esri's academic terms; raw tiles are not redistributed. Open datasets: ESA WorldCover 10~m v200 (CC BY 4.0, \url{https://doi.org/10.5281/zenodo.7254221}), Copernicus GLO-30 DEM (\url{https://doi.org/10.5270/ESA-c5d3d65}), Overture Maps (ODbL 1.0 / CDLA-Permissive-2.0), OpenStreetMap (ODbL 1.0), geoBoundaries (ODbL 1.0), LoveDA (CC BY-NC-SA 4.0, \url{https://doi.org/10.5281/zenodo.5706578}). TGRAC layers for Damarakunta are subject to the provider's terms. The \dinoseg{} checkpoint is not included in the repository; its SHA-256 is given in section~\ref{sec:methods}.}

\section*{Conflict of interest}
The authors declare no competing interests.

\bibliographystyle{iopart-num}
\bibliography{references}

\end{document}
"""

# ------------------------------------------------------------------------------------------------ write

# ------------------------------------------------------------------------------------------------ 4.8 grid resolution and clearance sensitivity (numbers from the committed result files only)
def grid_row(k):
    m = M[k]
    soft_sav = 100 * (m["soft_indep_m"] - m["soft_shared_m"]) / m["soft_indep_m"]
    return (f"{m['label']} & {n(round(m['soft_indep_m']))} & {n(round(m['soft_shared_m']))} & {soft_sav:.1f} & {m['soft_cross_routes']} & {m['soft_cross_m']:.0f} & "
            f"{n(round(m['stageA_m']))} & {n(round(m['stageB_m']))} & {m['saving_pct']:.1f} & {m['crossings']} & {m['crossing_m']:.0f}\\\\")

grid = r"""
\subsection{Grid resolution and clearance sensitivity}\label{sec:grid}
The routing raster was refined during the study, and the effect is recorded for every area (table~\ref{tab:grid}). The first planner worked on the $10$~m cost grid of the WorldCover and slope layers and discouraged, but did not forbid, routes over roofs: cells whose centre lies in a footprint cost $\mu=4$ times as much (equation~\ref{eq:cell}). A $10$~m cell is wider than the lanes between neighbouring buildings in compact fabric, so such a grid cannot represent a lane at all: the cell that covers a lane also covers part of a roof, and when its centre falls inside a footprint it carries the penalty, so the planner either crosses the roof when the detour costs more or leaves a usable gap unused. On this grid 28, 99, 157 and 5 routes ended up inside other footprints in Damarakunta, Adilabad, Aswaraopeta and Alampur, with 209, 677, 1{,}090 and 33~m of route length inside them. The final planner refines the raster to $5$~m with the same cost per metre and blocks every cell whose centre lies within $r_c=3.6$~m of a footprint, a distance above the half-diagonal of a $5$~m cell ($3.54$~m), so that no step between free cells can touch a roof (section~\ref{sec:cost}). Every one of the four settlements then has zero building crossings, verified by intersecting each drawn route with all other footprints. The corridor-consolidation saving remains positive and of similar size (Stage~B 12.2--25.3\% shorter than Stage~A, against 14.4--31.2\% on the coarse grid in the same areas), so the clearance removes the encroachments without removing the benefit of sharing.

The two sets of lengths are not strictly comparable and the table should be read column-wise. The $10$~m figures come from the soft-penalty planner (routes may cross a roof, every target is routed), the $5$~m figures from the clearance planner, whose routes start at the building edge, may not cross a roof and leave unrouted any target enclosed by buildings (Damarakunta 162 of 163, Adilabad 607 of 613, Aswaraopeta 632 of 678, Alampur 58 of 59). The soft-penalty comparison is also a unique-length measure over all targets of a cheaper graph, so the absolute lengths differ for reasons that include both the grid and the target set; the quantities that bear on the grid choice are the crossing counts and the saving.

\begin{table*}[t]
\caption{Routing grid resolution: $10$~m soft-penalty grid versus $5$~m zero-crossing grid ($3.6$~m clearance). Lengths are unique network lengths in metres (shared edges counted once); Independent is the sum over independent least-cost routes with shared edges counted once, Shared (10~m) and Stage~B (5~m) are the consolidated networks; saving is the consolidated network against the independent routes; crossings are routes inside another building's footprint, with the route length inside footprints in metres.}
\label{tab:grid}
\centering
\scriptsize
\renewcommand{\arraystretch}{1.1}
\resizebox{\textwidth}{!}{%
\begin{tabular}{@{}lrrrrrrrrrr@{}}
\toprule
 & \multicolumn{5}{c}{$10$~m grid, footprint penalty $\mu=4$} & \multicolumn{5}{c}{$5$~m grid, $3.6$~m hard clearance}\\
\cmidrule(lr){2-6}\cmidrule(lr){7-11}
Area & Independent & Shared & Saving (\%) & Routes crossing & In footprints (m) & Stage A & Stage B & Saving (\%) & Routes crossing & In footprints (m)\\
\midrule
""" + "\n".join(grid_row(k) for k in (DK, AD, AS, AL)) + r"""
\bottomrule
\end{tabular}}
\end{table*}
"""
for _k in (DK, AD, AS, AL):
    _m = M[_k]
    _sv = 100 * (_m["soft_indep_m"] - _m["soft_shared_m"]) / _m["soft_indep_m"]
    print("grid", _k, f"soft saving {_sv:.1f}")
doc = head + intro + study + method + results + grid + disc + app + back

# ------------------------------------------------------------------------------------------------ citation pass (every dataset, method and benchmark source cited at first use)
CITES = [
 (r"Esri World Imagery (imagery, 0.6~m tiles) &", r"Esri World Imagery \cite{esri2026worldimagery} (imagery, 0.6~m tiles) &"),
 (r"Overture Maps (buildings, roads, places) &", r"Overture Maps \cite{overture2026} (buildings, roads, places) &"),
 (r"OpenStreetMap (boundary candidates, facilities) &", r"OpenStreetMap \cite{haklay2008osm} (boundary candidates, facilities) &"),
 (r"ESA WorldCover (land cover) &", r"ESA WorldCover \cite{zanaga2021worldcover} (land cover) &"),
 (r"Copernicus DEM GLO-30 (slope) &", r"Copernicus DEM GLO-30 \cite{esa2022copdem} (slope) &"),
 (r"LoveDA (segmentation training, validation) &", r"LoveDA \cite{wang2021loveda} (segmentation training, validation) &"),
 (r"Wikidata, Wikipedia (facility audit) &", r"Wikidata \cite{vrandecic2014wikidata}, Wikipedia (facility audit) &"),
 (r"0.6~m Esri World Imagery, TGRAC", r"0.6~m Esri World Imagery \cite{esri2026worldimagery}, TGRAC"),
 (r"ESA WorldCover v200 land cover, the Copernicus GLO-30 elevation model", r"ESA WorldCover v200 land cover \cite{zanaga2021worldcover}, the Copernicus GLO-30 elevation model \cite{esa2022copdem} (SRTM 1 arc-second for the frozen Damarakunta pilot, which agrees with GLO-30 to an RMSE of 2.3~m)"),
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
 (r"carries no optimality guarantee. Two passes", r"carries no optimality guarantee. Two passes"),
 (r"against Google Open Buildings v3 (appendix", r"against Google Open Buildings v3 \cite{sirko2021openbuildings} (appendix"),
 (r"Wikidata and Wikipedia (and, for Damarakunta", r"Wikidata \cite{vrandecic2014wikidata} and Wikipedia (and, for Damarakunta"),
 (r"equivalent to Rs ", r"equivalent to Rs "),
]
for old, new in CITES:
    if old == new:
        continue
    if old not in doc:
        print("CITE ANCHOR NOT FOUND:", old[:70])
    else:
        doc = doc.replace(old, new, 1)

(H / "main.tex").write_text(doc, encoding="utf-8")
for src, dst in [(REPO / "paper_eris" / "figures" / "fig_architecture.png", H / "fig_architecture.png"),
                 (REPO / "paper_eris" / "figures" / "fig_flow_study_areas.png", H / "fig_flow_study_areas.png"),
                 (REPO / "paper_eris" / "paper_comparison_table.tex", H / "paper_comparison_table.tex")]:
    if src.exists() and src.resolve() != dst.resolve():
        shutil.copyfile(src, dst)
print("abstract words:", words, "| wrote", H / "main.tex")
