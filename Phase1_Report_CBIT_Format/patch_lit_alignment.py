"""One-off patch (kept for provenance): new Section 2.3 'Alignment of the Reviewed Literature with the Pipeline' (table + text) in the literature chapter.
Pipeline facts are taken from the code: StrongDINOv2Seg (src/modeling), plan_network_v2.py (8-connected Dijkstra, heapq), STRtree in the runners."""
p = r"D:\Telangana_Rural_Project\Phase1_Report_CBIT_Format\build_report.py"
s = open(p, encoding="utf-8").read()


def rep(a, b):
    global s
    assert s.count(a) == 1, (s.count(a), a[:70])
    s = s.replace(a, b)


rep('["contrib", "lit1", "lit2", "gapmat"', '["contrib", "lit1", "lit2", "align", "gapmat"')
rep('''    H(3, num, title); tp(ln)

# ---------- 3 Research gap''', '''    H(3, num, title); tp(ln)
H(2, "2.3", "Alignment of the Reviewed Literature with the Pipeline")
para(runs("This section connects the 35 reviewed IEEE Transactions papers to the architectural choices of the pipeline. The word used is motivate, not prove: the papers report results on other datasets and tasks, and none of them evaluates a rural road-planning pipeline. Table @T:align@ pairs each implemented component with the papers that motivate it, states what those papers support, and states what the project does not claim.".replace("@T:align@", REF["tab:align"])))
table_caption("align", "Pipeline components, the reviewed papers that motivate them, and what is and is not claimed.")
make_table(["Pipeline component (as implemented)", "Motivating papers", "What the papers support", "What is not claimed"], [
    ["Segmentation of building footprints: DINOv2-Base encoder (768 channels) with FPN fusion (256), an ASPP module and a residual decoder (class StrongDINOv2Seg); the detection stage is reused as a verified input",
     "\\\\cite{L33,L34,L35}; multi-scale context \\\\cite{L06,L07,L16,L18}",
     "Pretrained vision foundation encoders and multi-scale context modules are an active and reported-effective direction; for example HyperR3SNet reports mean IoU of 67.60%, 55.86%, 80.07% and 96.46% on iSAID, LoveDA, Potsdam and Vaihingen \\\\cite{L35}, and a searched real-time network reports 54.5% mIoU on LoveDA \\\\cite{L18}.",
     "The model is not retrained or re-scored in this report; no reference labels exist for Damarakunta, so its accuracy there is not measured, and its weights provenance is undocumented."],
    ["Footprint quality classes (plausible, review, unresolved merge) instead of one confirmed building class",
     "Boundary and shape: \\\\cite{L03,L06,L08,L22}; review \\\\cite{L17}",
     "Boundary precision, shape regularisation and occlusion are recognised weaknesses of segmentation outputs, so ambiguous or merged blobs should not automatically become houses.",
     "No shape regulariser is implemented; the classes are rule-based and were checked only against independent layers."],
    ["Local layers and benchmark: LoveDA for the model background; TGRAC boundary, roads, parcels and facilities and Google Open Buildings v3 for local checks (Chapter 4)",
     "Domain shift: \\\\cite{L11,L43,L44,L45}; LoveDA \\\\cite{F05}",
     "Segmentation accuracy drops across sensors, regions and seasons, so benchmark scores do not transfer to a new village and local verification is needed.",
     "Agreement with Open Buildings or TGRAC is consistency, not accuracy."],
    ["Road layer: TGRAC road lines clipped to the village boundary; connectivity checked on the planning grid and on the lines",
     "\\\\cite{L36,L37,L38,L39}; \\\\cite{L12,L20}",
     "Road connectivity and topology matter for downstream use, and incomplete existing road maps are a recognised input problem; the TGRAC layer is incomplete near the boundary.",
     "No road extraction is performed; the papers improve raster road maps and do not join houses to a network."],
    ["Cost surface and least-cost routing: ordinal cost on a 10 m grid, 8-connected Dijkstra search with a binary heap (A* is not used; NetworkX is used only in one connectivity diagnostic; STRtree spatial indexes serve footprint tests)",
     "Foundations \\\\cite{F01,F02,F04,F03}; \\\\cite{L40,L41,L42}",
     "Cost-weighted path planning is established; planning with a realistic path distance instead of Euclidean or Manhattan distance reduced investment by 30% or more in a distribution-network study \\\\cite{L42}; multi-objective route planning is studied in \\\\cite{L40,L41}.",
     "Dijkstra and A* with an admissible heuristic return the same least-cost path; the choice affects speed only, which is not a constraint on a grid of 293,328 cells."],
    ["Two-stage generate-and-select planning: K = 3 candidate routes per target (Stage A), then selection by marginal cost with shared-edge credit and leaf re-routing (Stage B)",
     "\\\\cite{L40,L41,L42}",
     "Generating candidates and then choosing among them under an objective trade-off is consistent with improvement-heuristic and multi-objective planners; sharing infrastructure lowers network cost.",
     "Novelty is not claimed for shortest-path search or for sharing edges; the claim is the fair, unique-length accounting on one target set."],
    ["Target-set perturbation (C1) and building-penalty variants",
     "\\\\cite{L23,L24,L31}",
     "Sparse-label and semi-supervised work shows that predictions are uncertain and may be partial, which motivates testing how target changes propagate.",
     "The omit and add runs are synthetic probes, not measured segmentation error."],
], [1.8, 1.0, 2.2, 1.5], size=8)
para(runs("The chain from literature to results is as follows. The reviewed segmentation papers motivate the detection stage and its quality classes (Section 2.2.2); Chapter 4 documents the datasets that stand in for ground truth (LoveDA for the model background, and the TGRAC and Open Buildings layers for local checks); and the planner then turns the 163 eligible targets and five facilities into a shared network. On these inputs the two-stage plan has a unique house-route length of %s m against %s m for independent routes (a saving of %.1f%%), and Chapter 9 reports the sensitivity of that result. The papers themselves are not evidence for these numbers." % (N0(hp["unique_len_m"]), N0(ih["unique_len_m"]), 100 * sav / ih["unique_len_m"])))

# ---------- 3 Research gap''')
open(p, "w", encoding="utf-8").write(s)
print("patched")
