"""Edit the literature text in the LaTeX source (counts, new citations, novelty wording). Keeps the line count unchanged,
because build_report.py addresses the file by line number. Run on a pristine copy of the original .tex."""
import sys

SRC = sys.argv[1]
L = open(SRC, encoding="utf-8").read().split("\n")
n0 = len(L)


def rep(n, a, b):
    assert a in L[n - 1], (n, a)
    L[n - 1] = L[n - 1].replace(a, b)


rep(105, "a literature review of 35 IEEE-published works (2020--2026) plus five foundational references",
    "a literature review of 45 IEEE-published works (2020--2026), 35 of which are IEEE Transactions papers whose metadata were checked against the DOI registry, plus five foundational references")
assert L[164].startswith("This chapter reviews 35")
L[164] = (r"This chapter reviews 45 IEEE-published works from 2020 to 2026 and five foundational references. Of the 45, 35 are IEEE Transactions papers; they form the qualifying set for the guide's requirement of at least 30 Transactions papers. The other ten (seven in the IEEE Journal of Selected Topics in Applied Earth Observations and Remote Sensing, one Geoscience and Remote Sensing Letter, one Geoscience and Remote Sensing Magazine article and one WACV conference paper) are kept as background and are not counted. For every entry the title, all authors, journal, year, volume, pages or article number and DOI were checked against the DOI-registry record (Crossref) on 29 October 2026, and each DOI link leads to the IEEE Xplore page; Appendix A lists the verified details of the 35 qualifying papers. Tables~\ref{tab:lit1} and~\ref{tab:lit2} give the full comparison. Findings and limitations in Table~\ref{tab:lit2} are a project-oriented critical assessment based on abstracts and metadata, not necessarily statements by the authors; full-text reading of every paper is not yet complete. The datasets used by each paper were not recorded in the survey file, so a dataset column is omitted rather than guessed. The searches did not return an IEEE Transactions paper on rural village road planning from remote-sensing building targets, which is the gap this project addresses, but this is a statement about the searches made and not a proof that none exists.")
assert L[167].startswith("Of the 35 works")
L[167] = (r"Of the 45 works, 35 are IEEE Transactions papers (30 in IEEE Transactions on Geoscience and Remote Sensing, 2 in IEEE Transactions on Image Processing, 2 in IEEE Transactions on Intelligent Transportation Systems and 1 in IEEE Transactions on Power Systems), 7 are in the IEEE Journal of Selected Topics in Applied Earth Observations and Remote Sensing, 1 is an IEEE Geoscience and Remote Sensing Letter, 1 is an IEEE Geoscience and Remote Sensing Magazine article and 1 is an IEEE/CVF WACV conference paper. Only the 35 Transactions papers published between 2020 and 2026 count towards the requirement. By theme, the Transactions papers cover road extraction and topology, building extraction, segmentation with sparse labels and uncertainty, foundation-model and domain-adaptation methods, multi-objective route planning and GIS-based network planning. The planning themes are thinly covered in IEEE Transactions, which is why established least-cost-path references are kept as foundational references.")
rep(175, r"\cite{L01,L02,L12,L16,L20,L29,L30,L32}", r"\cite{L01,L02,L12,L16,L20,L29,L30,L32,L36,L37,L38}")
L[174] = L[174].rstrip() + r" Topology-oriented methods represent the road layer as a graph or correct its connections \cite{L37,L38}, and one method uses incomplete existing road maps as an extra input \cite{L39}; this is close to the incomplete TGRAC layer, but the output is again a road map and not a set of house connections."
L[183] = L[183].rstrip() + r" Cross-domain adaptation and domain-generalisation methods for remote-sensing segmentation \cite{L43,L44,L45} aim at unseen regions, sensors and seasons, which is the situation C3 would meet in a new village; they report segmentation accuracy and not the effect of transfer on a downstream network plan."
L[189] = L[189].rstrip() + r" Learning-based multi-objective route planning \cite{L40}, terrain-aware multi-objective off-road path planning \cite{L41} and GIS-based network planning with shortest-path distances \cite{L42} show that route cost, terrain and network design are studied in IEEE Transactions, but they address vehicle routes or urban power networks. Among the papers reviewed, none evaluates a village road network with shared-edge credit under uncertain building targets."
a = "These gaps are not proof of novelty. Novelty must be argued by comparing the implemented method and experiments with prior art, which remains open for Phase-II."
assert a in L[201]
L[201] = (r"These gaps are not proof of novelty. The project does not claim novelty for shortest-path search, least-cost paths, A* or multi-criteria analysis, which are established \cite{F01,F02,F04,F03}. The contribution claimed is narrower: C1 measures how changes in the building-target set propagate into route selection, network length and exposure, and C2 generates alternatives first and selects among them with unique-length and shared-edge accounting. C3 (five-village transfer) is planned and has not started. Whether this combination is new must still be argued against prior art beyond the 45 papers reviewed, which remains open for Phase-II.")
rep(507, "reviewed 35 IEEE-published works with five foundational references",
    "reviewed 45 IEEE-published works (35 of them IEEE Transactions papers) with five foundational references")
assert len(L) == n0
open(SRC, "w", encoding="utf-8").write("\n".join(L))
print("ok", len(L))
