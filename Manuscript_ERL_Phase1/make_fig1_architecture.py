"""Figure 1 (Phase 1 only): strictly black-and-white technical architecture diagram, 300 dpi.
Run: python make_fig1_architecture.py   -> figures/ARCHITECTURE_DIAGRAM.png
Every specification printed here is taken from src/modeling/strongdinov2seg_training_updated.py,
scripts/create_damarakunta_cost_surface.py and the Stage B results (primary run S2_fac_C0_s25_final_x4)."""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

plt.rcParams.update({"font.family": "serif", "font.serif": ["DejaVu Serif"], "mathtext.fontset": "stix"})
fig, ax = plt.subplots(figsize=(7.4, 10.8))
ax.set_xlim(0, 101); ax.set_ylim(0, 146); ax.axis("off")
FS = 6.3

def panel(x0, y0, x1, y1, label, right=False):
    ax.add_patch(FancyBboxPatch((x0, y0), x1 - x0, y1 - y0, boxstyle="round,pad=0,rounding_size=1.2", fc="white", ec="black", lw=1.5))
    ax.text((x1 - 1.5) if right else (x0 + 1.5), y1 - 1.3, label, ha="right" if right else "left", va="top", fontsize=7.4, fontweight="bold")

def box(x0, y0, x1, y1, text, dashed=False, fs=FS, lw=0.9):
    ax.add_patch(FancyBboxPatch((x0, y0), x1 - x0, y1 - y0, boxstyle="round,pad=0,rounding_size=0.6", fc="white", ec="black", lw=lw, ls="--" if dashed else "-"))
    ax.text((x0 + x1) / 2, (y0 + y1) / 2, text, ha="center", va="center", fontsize=fs, linespacing=1.35)

def arrow(pts, dashed=False, lw=1.0):
    for a, b in zip(pts[:-2], pts[1:-1]):
        ax.plot([a[0], b[0]], [a[1], b[1]], color="black", lw=lw, ls="--" if dashed else "-", solid_capstyle="butt")
    ax.add_patch(FancyArrowPatch(pts[-2], pts[-1], arrowstyle="-|>", mutation_scale=7, color="black", lw=lw, ls="--" if dashed else "-", shrinkA=0, shrinkB=0))

# ---------------- Stage 1 ----------------
panel(1, 117, 95, 145, "Stage 1  Geospatial inputs and preprocessing")
xs = [2.5, 21.25, 40.0, 58.75, 77.5]; w = 17.0
box(xs[0], 124, xs[0] + w, 140, "Esri World Imagery\n0.6 m, RGB\n11,296 × 7,171 px\ntiles $X$: 560×560×3\n(stride 420 px)")
box(xs[1], 124, xs[1] + w, 140, "TGRAC layers\nboundary 18.47 km²\nroads, 43 lines\nfacilities, parcels\nEPSG:32644", fs=5.9)
box(xs[2], 124, xs[2] + w, 140, "ESA WorldCover\nv200, 10 m\nland-cover class\n$\\ell(x)$")
box(xs[3], 124, xs[3] + w, 140, "SRTM-type DEM\n30 m, Sobel slope\n$\\theta(x)$ in degrees\nbilinear to 10 m")
box(xs[4], 124, xs[4] + w, 140, "Google Open\nBuildings v3\n1,537 polygons\nvalidation only,\nnot a routing input", dashed=True)
box(15, 118.5, 82, 122.5, "Grid alignment: 10 m, 432×679 cells; blocked set $\\mathcal{B}$: water, no data, $\\theta>25^{\\circ}$", fs=6.1)
for x in (xs[1], xs[2], xs[3]):
    arrow([(x + w / 2, 124), (x + w / 2, 122.5)])
# ---------------- Stage 2 ----------------
panel(1, 74, 95, 113, "Stage 2  StrongDINOv2Seg semantic segmentation (LoveDA, 8 labels, ID 0 ignored)")
box(2.5, 96, 19, 108, "Input tile\n$X\\in\\mathbb{R}^{560\\times560\\times3}$\nnormalised")
box(22, 96, 57, 108, "ViT-B/14 encoder (DINOv2-base)\nall weights fine-tuned\npatch $14\\times14$ → $40\\times40$ tokens, $D=768$\ntaps $L\\in\\{3,6,9,12\\}$: $4\\times(40\\times40\\times768)$", fs=5.8)
box(60, 96, 94.5, 108, "FPN fusion\n1×1 lateral $768\\to256$ per layer (×4)\nconcat $40\\times40\\times1024$\n→ 1×1 → $40\\times40\\times512$", fs=5.8)
box(60, 83, 94.5, 93.5, "ASPP: 1×1, 3×3 dilated $r\\in\\{6,12,18\\}$,\nglobal pool; 5 branches × 256\n→ 1×1 → $40\\times40\\times256$", fs=5.8)
box(22, 83, 57, 93.5, "Residual decoder: 4 × (bilinear ×2\n+ residual block), $256\\to128\\to64\\to32$ ch;\nresize to $560\\times560\\times32$; aux heads\non 3 scales (training only)", fs=5.8)
box(2.5, 83, 19, 93.5, "1×1 conv + softmax\n$560\\times560\\times8$\nargmax → class map")
box(22, 75, 94.5, 81.5, "Loss $\\mathcal{L}=0.5\\,\\mathcal{L}_{CE}+0.4\\,\\mathcal{L}_{Dice}+0.1\\,\\mathcal{L}_{edge}+0.4\\,\\Sigma_{k=1..3}\\mathcal{L}_{aux,k}$; AdamW, 10 epochs\nLoveDA validation (7 scored classes): 53.80% mIoU, 68.91% mDice, 71.3% pixel accuracy\n(source-domain scores, not village accuracy)", fs=5.8)
arrow([(19, 102), (22, 102)]); arrow([(57, 102), (60, 102)]); arrow([(77.25, 96), (77.25, 93.5)])
arrow([(60, 88.2), (57, 88.2)]); arrow([(22, 88.2), (19, 88.2)])
arrow([(10.75, 124), (10.75, 108)])
# ---------------- Stage 3 ----------------
panel(1, 43, 95, 71, "Stage 3  Post-processing and multi-criteria cost surface")
box(2.5, 45, 40, 66, "Instance extraction (OpenCV, NumPy)\n1. morphological open / close of building mask\n2. distance-transform split where saddle\n   width < 0.65 × inscribed radius\n3. oversize blobs flagged unresolved merge\n→ 278 polygons, 165 in boundary,\n163 house targets (71 plausible, 32 review,\n62 merge) + 5 facility targets", fs=5.9)
box(44, 45, 94.5, 66, "Cost surface $c(x)$, $432\\times679$ raster, 10 m\n$c(x)=[\\,c_{lc}(\\ell(x))+w_s\\,\\min(\\theta,\\theta_{max})/\\theta_{max}\\,]\\cdot m(x)$\n$m(x)=\\mu$ if $x\\in\\mathcal{P}$ (footprint cells, $M_{bldg}$), else 1; $\\mu=4$\n$c_{lc}$: tree 8, crop 6, shrub 5, bare 4, grass 3, built-up 2\n$w_s=4$, $\\theta_{max}=10^{\\circ}$; $c(x)=\\infty$ on $\\mathcal{B}$", fs=5.8)
arrow([(40, 55.5), (44, 55.5)])
arrow([(10.75, 83), (10.75, 66)])
# data bus (raster stack from Stage 1 -> Stages 3 and 4)
arrow([(82, 120.5), (98, 120.5), (98, 33), (94.5, 33)], lw=1.0)
arrow([(98, 58), (94.5, 58)], lw=1.0)
ax.text(99.7, 90, "$\\ell(x),\\ \\theta(x),\\ \\mathcal{B}$, roads", rotation=90, ha="center", va="center", fontsize=5.6)
# ---------------- Stage 4 ----------------
panel(1, 1, 95, 40, "Stage 4  Shared-network Dijkstra routing and validation", right=True)
box(2.5, 25, 35, 36, "Grid graph $G=(V,E)$, 8-connected\n$V$: unblocked cells\n$w(u,v)=d(u,v)\\,[c(u)+c(v)]\\,/\\,2$", fs=5.9)
box(37.5, 25, 66, 36, "Stage A: per-target least-cost paths\nDijkstra, $K=3$ alternatives each\n(cost ×3, ×8 in 20 m corridor)\n319 alternatives, 163 houses", fs=6.0)
box(68.5, 25, 94.5, 36, "Stage B: greedy selection\nmax weight / $\\Delta L$, where\n$\\Delta L=\\Sigma\\,w_e$ over $e\\in\\pi\\setminus E_S$;\nbuilt edges $\\gamma=0$; 2 leaf passes", fs=5.8)
arrow([(35, 30.5), (37.5, 30.5)]); arrow([(66, 30.5), (68.5, 30.5)])
arrow([(70, 45), (70, 42), (18.75, 42), (18.75, 36)])
ax.text(44, 42.8, "$c(x)$", fontsize=5.8, ha="center", va="bottom")
arrow([(81.5, 25), (81.5, 19)])
box(54, 3, 94.5, 19, "Outputs (primary run, $\\mu=4$)\nshared network 5,069.0 m vs. independent\nunique 6,753.1 m: −24.9% (−1,684.1 m)\n168 / 168 targets connected, 0 constraint violations\nfootprint-crossing routes: 28 ($\\mu=4$) vs. 56 ($\\mu=1$)", fs=6.0)
box(2.5, 3, 47, 19, "Validation\n23 perturbed runs (omit / add 10–20%, smallest\n10% / 25%, merged blobs): saving 24.9–26.6%\nOpen Buildings v3 agreement: 118 / 165 (71.5%),\nproxy only, no ground truth", dashed=True, fs=6.0)
arrow([(54, 11), (47, 11)])
out = Path(__file__).parent / "figures" / "ARCHITECTURE_DIAGRAM.png"
fig.savefig(out, dpi=300, facecolor="white", bbox_inches="tight", pad_inches=0.05)
print(out)
