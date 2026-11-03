"""Render figures, equation images and logo crops used by build_report.py."""
import os, sys
import pymupdf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle
from PIL import Image

OLD = sys.argv[1]            # extracted LaTeX project folder
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
os.makedirs(OUT, exist_ok=True)
plt.rcParams["font.family"] = "Times New Roman"
plt.rcParams["mathtext.fontset"] = "stix"

# --- existing vector figures -> PNG
for name, dpi in (("satellite_overview", 170), ("shared_network_length", 200), ("building_quality", 200)):
    pg = pymupdf.open(os.path.join(OLD, "figures", name + ".pdf"))[0]
    pg.get_pixmap(dpi=dpi).save(os.path.join(OUT, name + ".png"))

# --- logos
logo = Image.open(os.path.join(OLD, "figures", "cbit_48_years_logo.jpg")).convert("RGB")
logo.save(os.path.join(OUT, "banner.png"))
w, h = logo.size
logo.crop((int(w * 0.012), 0, int(w * 0.15), h)).save(os.path.join(OUT, "emblem.png"))

# --- equations
EQ = {
 "eq_cost": r"$c(x)=c_{\mathrm{lc}}(x)+4\,\frac{\mathrm{clip}(s(x),\,0,\,10)}{10}$",
 "eq_pen": r"$c'(x)=m\,c(x)$ for $x\in\bigcup_{b\in\mathcal{B}_q}\mathrm{footprint}(b)$;   $c'(x)=c(x)$ otherwise",
 "eq_credit": r"$L_{\mathrm{unique}}=\sum_{e\in\bigcup_k E_k}\ell_e,\quad \mathrm{credit}_k=\sum_{e\in E_k}\frac{\ell_e}{n_e},\quad \sum_k \mathrm{credit}_k=L_{\mathrm{unique}}$",
}
for k, s in EQ.items():
    fig = plt.figure(figsize=(6, 1))
    fig.text(0, 0.5, s, fontsize=15, va="center")
    fig.savefig(os.path.join(OUT, k + ".png"), dpi=300, bbox_inches="tight", pad_inches=0.04, transparent=False, facecolor="white")
    plt.close(fig)

def box(ax, x, y, w, h, text, fc, fs=8.5):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08", fc=fc, ec="black", lw=0.8))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs)

def arrow(ax, p, q):
    ax.annotate("", xy=q, xytext=p, arrowprops=dict(arrowstyle="-|>", lw=1.0, color="black", shrinkA=0, shrinkB=0))

# --- Figure: layered architecture
fig, ax = plt.subplots(figsize=(7.2, 6.6)); ax.set_xlim(0, 10); ax.set_ylim(0, 10.6); ax.axis("off")
cols = [0.9, 3.95, 7.0]; bw, bh = 2.75, 1.0
rows = {0: 8.8, 1: 6.3, 2: 3.8, 3: 1.3}
layers = ["Inputs", "Preparation", "Targets and planning", "Evaluation and outputs"]
labels = [
 ["Imagery mosaic\n(0.6 m)", "GIS layers\n(roads, facilities, parcels)", "Land cover (10 m)\nand DEM slope"],
 ["Georeferencing, clipping,\nCRS EPSG:32644", "Building candidates\n+ quality classes", "Multi-criteria\ncost surface"],
 ["Facility targets\n(Stage 1)", "House targets\n(Stage 2)", "Two-stage planner\n+ shared-edge credit"],
 ["Graph and\nconnectivity checks", "Validation, sensitivity,\nuncertainty", "Maps, tables,\nreports"],
]
for r in range(4):
    y = rows[r]
    ax.add_patch(Rectangle((0.6, y - 0.25), 9.3, bh + 0.5, fill=False, ls="--", lw=0.8, ec="gray"))
    ax.text(0.33, y + bh / 2, layers[r], fontsize=8, style="italic", color="dimgray", rotation=90, ha="center", va="center")
    for c in range(3):
        box(ax, cols[c], y, bw, bh, labels[r][c], "#e6eefc")
for r in range(3):
    for c in range(3):
        arrow(ax, (cols[c] + bw / 2, rows[r] - 0.25), (cols[c] + bw / 2, rows[r + 1] + bh + 0.25))
arrow(ax, (cols[0] + bw, rows[1] + bh / 2), (cols[1], rows[1] + bh / 2))   # georef -> buildings
arrow(ax, (cols[0] + bw, rows[2] + bh / 2), (cols[1], rows[2] + bh / 2))   # facilities -> houses
arrow(ax, (cols[1] + bw, rows[2] + bh / 2), (cols[2], rows[2] + bh / 2))   # houses -> planner
arrow(ax, (cols[0] + bw, rows[3] + bh / 2), (cols[1], rows[3] + bh / 2))   # connectivity -> validation
arrow(ax, (cols[1] + bw, rows[3] + bh / 2), (cols[2], rows[3] + bh / 2))   # validation -> outputs
fig.savefig(os.path.join(OUT, "fig_arch.png"), dpi=220, bbox_inches="tight", facecolor="white"); plt.close(fig)

# --- Figure: 20-module workflow
mods = [
 ("M1", "Inputs", 1), ("M2", "Source\nverification", 0), ("M3", "Georef.", 0), ("M4", "Preprocess", 1), ("M5", "Building\ndetection", 1),
 ("M6", "Land cover\ncost surface", 1), ("M7", "Existing\nroads", 1), ("M8", "House\ntargets", 1), ("M9", "Facility\npriority", 0), ("M10", "Raster/\nvector", 1),
 ("M11", "Slope,\nterrain", 1), ("M12", "Multi-\ncriteria cost", 1), ("M13", "Candidate\nroutes", 1), ("M14", "Feasibility,\nranking", 0), ("M15", "Shared-edge\ncredit", 1),
 ("M16", "Graph,\nconnectivity", 1), ("M17", "House/facility\nconnectivity", 1), ("M18", "Metrics", 1), ("M19", "QC, sensitivity,\nuncertainty", 0), ("M20", "Maps,\nreports", 0),
]
fig, ax = plt.subplots(figsize=(7.4, 4.6)); ax.set_xlim(0, 10.4); ax.set_ylim(-0.6, 6.2); ax.axis("off")
cw, ch, gx, gy = 1.7, 0.95, 0.4, 0.7
pos = []
for i, (m, t, done) in enumerate(mods):
    r, c = divmod(i, 5); x = 0.1 + c * (cw + gx); y = 5.2 - r * (ch + gy)
    box(ax, x, y, cw, ch, f"{m}\n{t}", "#dff3dc" if done else "#fff3b8", fs=7.3); pos.append((x, y))
for i in range(19):
    (x1, y1), (x2, y2) = pos[i], pos[i + 1]
    if i % 5 != 4:
        arrow(ax, (x1 + cw, y1 + ch / 2), (x2, y2 + ch / 2))
    else:
        ax.plot([x1 + cw / 2, x1 + cw / 2], [y1, y1 - gy / 2], color="black", lw=1)
        ax.plot([x1 + cw / 2, x2 + cw / 2], [y1 - gy / 2, y1 - gy / 2], color="black", lw=1)
        arrow(ax, (x2 + cw / 2, y1 - gy / 2), (x2 + cw / 2, y2 + ch))
ax.add_patch(Rectangle((0.1, -0.45), 0.25, 0.2, fc="#dff3dc", ec="black")); ax.text(0.45, -0.35, "Implemented", fontsize=7.5, va="center")
ax.add_patch(Rectangle((2.1, -0.45), 0.25, 0.2, fc="#fff3b8", ec="black")); ax.text(2.45, -0.35, "Partial", fontsize=7.5, va="center")
fig.savefig(os.path.join(OUT, "fig_flow.png"), dpi=220, bbox_inches="tight", facecolor="white"); plt.close(fig)
print("assets ok")
