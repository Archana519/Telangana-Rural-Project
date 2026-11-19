"""Figure 1 (Phase 1 only): ERL-style three-panel workflow figure at exact print size (170 x 115 mm, no rescaling).

    python make_fig1_architecture.py   ->  figures/ARCHITECTURE_DIAGRAM.pdf (vector) and .png (600 dpi)

All labels are 8.5-9.5 pt. Numbers come from src/modeling/strongdinov2seg_training_updated.py,
scripts/create_damarakunta_cost_surface.py and the Stage B primary run (S2_fac_C0_s25_final_x4).
Longer specifications (tensor sizes, equations) are in the caption in body.tex.
"""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

plt.rcParams.update({"font.family": "Liberation Sans", "pdf.fonttype": 42, "ps.fonttype": 42})

W_IN, H_IN = 6.7, 4.5                 # 170 mm x 115 mm
W, H = W_IN * 72, H_IN * 72           # drawing units are points (1 unit = 1 pt)
INK, PANEL = "#1F2937", "#F7F9FA"
BLUE, TEAL, AMBER, GRAY = "#2B5C8F", "#2E7D6B", "#B4651E", "#6B7280"
FS, FS_T, FS_H = 8.5, 9.0, 9.5

fig = plt.figure(figsize=(W_IN, H_IN))
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis("off")

PW, GAP, X0 = 118.0, 60.2, 3.0
PX = [X0, X0 + PW + GAP, X0 + 2 * (PW + GAP)]          # panel left edges
BX, BW = 5.0, PW - 10.0                                  # block inset and width


def panel(i, title):
    ax.add_patch(FancyBboxPatch((PX[i], 6), PW, H - 12, boxstyle="round,pad=0,rounding_size=4",
                                fc=PANEL, ec=INK, lw=1.2))
    ax.text(PX[i] + 7, H - 12, title, ha="left", va="top", fontsize=FS_H, fontweight="bold", color=INK, linespacing=1.15)


def block(i, top, h, lines, accent, dashed=False, fill="white"):
    x = PX[i] + BX
    ax.add_patch(FancyBboxPatch((x, top - h), BW, h, boxstyle="round,pad=0,rounding_size=3",
                                fc=fill, ec=accent, lw=1.2, ls=(0, (3, 2)) if dashed else "-"))
    n = len(lines)
    lh = 10.6
    y = top - h / 2 + (n - 1) * lh / 2
    for k, t in enumerate(lines):
        ax.text(x + BW / 2, y - k * lh, t, ha="center", va="center", fontsize=FS_T if k == 0 else FS,
                fontweight="bold" if k == 0 else "normal", color=accent if k == 0 else INK)
    return x, x + BW, top, top - h


def arrow(pts, color=INK, dashed=False):
    for a, b in zip(pts[:-2], pts[1:-1]):
        ax.plot([a[0], b[0]], [a[1], b[1]], color=color, lw=1.2, solid_capstyle="butt", ls=(0, (3, 2)) if dashed else "-")
    ax.add_patch(FancyArrowPatch(pts[-2], pts[-1], arrowstyle="-|>", mutation_scale=9, color=color, lw=1.2,
                                 shrinkA=0, shrinkB=0, ls="-"))


def label(x, y, text, ha="center", va="center"):
    ax.text(x, y, text, ha=ha, va=va, fontsize=FS, color=INK, linespacing=1.1)


TOP = 286.0
panel(0, "(a) Geospatial inputs")
panel(1, "(b) Segmentation and\ncost surface")
panel(2, "(c) Shared-corridor\nrouting, validation")

# ---- (a) inputs, four blocks of 46 pt with 24 pt gaps
a1 = block(0, TOP, 46, ["Esri World Imagery", "0.6 m RGB tiles", "560×560×3"], BLUE)
a2 = block(0, TOP - 70, 46, ["ESA WorldCover", "10 m land cover"], TEAL)
a3 = block(0, TOP - 140, 46, ["SRTM-type DEM", "slope θ · TGRAC", "boundary, roads"], TEAL)
a4 = block(0, TOP - 210, 46, ["Open Buildings", "validation only:", "72% agreement check"], GRAY, dashed=True)

# ---- (b) segmentation and cost surface
b1 = block(1, TOP, 74, ["StrongDINOv2Seg", "ViT-B/14 → FPN → ASPP", "→ residual decoder", "LoveDA 53.80% mIoU", "68.91% mDice · 71.3% OA"], BLUE)
b2 = block(1, TOP - 108, 56, ["Instance split", "distance transform", "building mask m(x),", "μ = 4 penalty"], BLUE)
b3 = block(1, TOP - 198, 56, ["Cost raster c(x)", "(land cover + slope)", "× m(x), 10 m grid"], TEAL)

# ---- (c) routing and validation
c1 = block(2, TOP, 52, ["8-connected graph", "G = (V, E)", "168 routing targets"], TEAL)
c2 = block(2, TOP - 67, 52, ["Baseline", "independent routes", "6,753.1 m unique", "46 crossings (μ = 4)"], AMBER)
c3 = block(2, TOP - 134, 52, ["Proposed", "shared corridors, γ = 0", "5,069.0 m (−24.9%)", "28 crossings (μ = 4)"], AMBER, fill="#FBEFE0")
c4 = block(2, TOP - 201, 52, ["Validation", "23 perturbation runs", "saving 24.9–26.6%", "Open Buildings 71.5%"], GRAY, dashed=True)

# ---- arrows with tensor / resolution callouts
y_img = TOP - 24
arrow([(a1[1], y_img), (b1[0], y_img)])
label((a1[1] + b1[0]) / 2, y_img + 14, "560×560×3\nRGB", va="center")

bus = 172.0
ya2, ya3, yb3 = (a2[2] + a2[3]) / 2, (a3[2] + a3[3]) / 2, (b3[2] + b3[3]) / 2
arrow([(a2[1], ya2), (bus, ya2), (bus, yb3), (b3[0], yb3)])
arrow([(a3[1], ya3), (bus, ya3)]); ax.plot([bus], [ya3], marker="o", ms=2.5, color=INK)
label(146.5, yb3 + 21, "land cover\n+ slope")

xb = (b1[0] + b1[1]) / 2
arrow([(xb, b1[3]), (xb, b2[2])]); label(xb + 5, (b1[3] + b2[2]) / 2, "560×560×8\nlogits", ha="left")
arrow([(xb, b2[3]), (xb, b3[2])]); label(xb + 5, (b2[3] + b3[2]) / 2, "m(x) raster", ha="left")

bus2 = 345.0
y_c1 = (c1[2] + c1[3]) / 2
arrow([(b3[1], yb3), (bus2, yb3), (bus2, y_c1), (c1[0], y_c1)])
label(bus2 - 4, 150, "c(x)\nraster", ha="right")

xc = (c1[0] + c1[1]) / 2
arrow([(xc, c1[3]), (xc, c2[2])])
arrow([(xc, c2[3]), (xc, c3[2])]); label(xc + 5, (c2[3] + c3[2]) / 2, "same graph", ha="left")
arrow([(xc, c3[3]), (xc, c4[2])], color=GRAY, dashed=True); label(xc + 5, (c3[3] + c4[2]) / 2, "perturbation", ha="left")

out = Path(__file__).parent / "figures"
fig.savefig(out / "ARCHITECTURE_DIAGRAM.pdf", facecolor="white")
fig.savefig(out / "ARCHITECTURE_DIAGRAM.png", dpi=600, facecolor="white")
print("ok")
