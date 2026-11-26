#!/usr/bin/env python
"""Figures 3-6 of the ERL manuscript: multi-panel composites cropped from the committed map series of the four study areas.

    python scripts/build_paper_result_figures.py            # writes paper_erl/fig_split1_footprints.png, fig_split2_cost_surface.png, fig_stage_AB.png, fig_shared_network_detail.png

Source images: DELIVERABLES_CONTRIBUTION_3_MULTI_VILLAGE/<area>/final_maps_1_to_5/map2 / map3 / map4 / map5 (made by scripts/make_village_map_series.py).
Only the map panels are cropped (titles, legends and the long footnote blocks of the source images are left out; the figure captions carry the explanations).
Every panel keeps the Esri imagery credit printed on the source map.
"""
from pathlib import Path

import matplotlib
from PIL import Image, ImageChops

matplotlib.use("Agg")
import matplotlib.pyplot as plt                                              # noqa: E402

REPO = Path(__file__).resolve().parents[1]
BASE = REPO / "DELIVERABLES_CONTRIBUTION_3_MULTI_VILLAGE"
OUT = REPO / "paper_erl"
AREAS = [("Damarakunta", "00_DAMARAKUNTA_MASTER_MAP"), ("Adilabad", "01_ADILABAD_UPDATED_SEGMENTATION"), ("Aswaraopeta", "02_ASWARAOPETA_SEGMENTATION"), ("Alampur", "03_ALAMPUR_SEGMENTATION")]
FILES = {"map2": "map2_footprints_facilities_latlon.png", "map3": "map3_terrain_cost_landcover_slope.png", "map4": "map4_alternatives_vs_network.png", "map5": "map5_village_detail_shared_paths.png"}
# map3 is a 2 x 2 grid of rasters on a white background: slope top right, cost surface bottom left (fractions of the image, then trimmed to the content)
QUAD = {"map3_slope": (0.50, 0.07, 1.00, 0.50), "map3_cost": (0.0, 0.50, 0.52, 0.84)}


def panel_boxes(im):
    """Bounding boxes (full-resolution pixels) of the solid non-white blocks of a map that survive a morphological opening
    (text, legends, leader lines and callout boxes are thin and vanish), with their pixel areas."""
    import numpy as np
    from scipy import ndimage as ndi
    sc = 600 / im.size[0]
    a = np.asarray(im.resize((600, int(im.size[1] * sc)))).min(axis=2) < 235
    a = ndi.binary_opening(a, structure=np.ones((15, 15)))
    lab, n = ndi.label(a)
    out = []
    for i, o in enumerate(ndi.find_objects(lab)):
        ar = int((lab[o] == i + 1).sum())
        if ar > 0.02 * a.size:
            out.append(((int(o[1].start / sc), int(o[0].start / sc), int(o[1].stop / sc), int(o[0].stop / sc)), ar))
    return out


def panel_box(im, pick):
    objs = panel_boxes(im)
    if not objs:
        return (0, 0) + im.size
    return (max(objs, key=lambda t: t[1]) if pick == "largest" else min(objs, key=lambda t: t[0][0]))[0]


def raster_box(im, key):
    """map3 is a 2 x 2 grid of rasters (land cover, slope / cost surface, blocked cells): in the right column the first block of rows is the slope raster,
    in the left column the second block is the cost surface. Blocks are separated by white bands; the box is widened to include the colour bar."""
    import numpy as np
    W, H = im.size
    x0, x1 = (int(0.5 * W), W) if key == "map3_slope" else (0, int(0.52 * W))
    a = np.asarray(im.crop((x0, int(0.05 * H), x1, int(0.86 * H)))).min(axis=2) < 235
    rows = np.where(a.sum(axis=1) > 3)[0]
    runs, start, prev = [], rows[0], rows[0]
    for r in rows[1:]:
        if r - prev > 0.035 * H:
            runs.append((start, prev)); start = r
        prev = r
    runs.append((start, prev))
    runs = [r for r in runs if r[1] - r[0] > 0.08 * H]                           # drop stray text lines
    r0, r1 = runs[0] if key == "map3_slope" else runs[1]
    y0, y1 = int(0.05 * H) + r0, int(0.05 * H) + r1
    return (x0, y0, x1, min(H, y1 + int(0.005 * H)))


def crop(folder, key, max_px=1100):
    src = key.split("_")[0]
    im = Image.open(BASE / folder / "final_maps_1_to_5" / FILES[src]).convert("RGB")
    W, H = im.size
    if key in QUAD:
        c = im.crop(raster_box(im, key))
        box = ImageChops.difference(c, Image.new("RGB", c.size, (255, 255, 255))).getbbox()
        c = c.crop(box) if box else c
    else:
        c = im.crop(panel_box(im, "leftmost" if src == "map5" else "largest"))
    s = max_px / max(c.size)
    return c.resize((int(c.size[0] * s), int(c.size[1] * s)), Image.LANCZOS) if s < 1 else c


def grid(key, out, ncols=2, w=7.0, labels=None):
    rows = (len(AREAS) + ncols - 1) // ncols
    ims = [crop(f, key) for _, f in AREAS]
    cell_w = w / ncols
    cell_h = max(im.size[1] / im.size[0] for im in ims) * cell_w
    fig, axs = plt.subplots(rows, ncols, figsize=(w, rows * (cell_h + 0.28)), squeeze=False)
    for ax, im, (nm, _), lab in zip(axs.ravel(), ims, AREAS, labels or [nm for nm, _ in AREAS]):
        ax.imshow(im)
        ax.set_title(lab, fontsize=7.5, loc="left", pad=3)
        ax.axis("off")
    fig.subplots_adjust(left=0.01, right=0.99, top=0.95, bottom=0.01, wspace=0.03, hspace=0.12)
    fig.savefig(out, dpi=170)
    plt.close(fig)
    print("wrote", out)


def cost_surface(out, w=7.2):
    """Two rows (slope, cost surface) by four columns (areas)."""
    fig, axs = plt.subplots(2, 4, figsize=(w, 4.1), squeeze=False)
    for ci, (nm, f) in enumerate(AREAS):
        for ri, key in enumerate(("map3_slope", "map3_cost")):
            im = crop(f, key, 700)
            axs[ri, ci].imshow(im)
            axs[ri, ci].axis("off")
            axs[ri, ci].set_title(f"({'abcd'[ci]}) {nm}" if ri == 0 else "", fontsize=7, loc="left", pad=2)
    fig.text(0.004, 0.73, "Slope (degrees)", rotation=90, fontsize=7, va="center")
    fig.text(0.004, 0.27, "Cost surface $C_0$", rotation=90, fontsize=7, va="center")
    fig.subplots_adjust(left=0.03, right=0.995, top=0.94, bottom=0.01, wspace=0.04, hspace=0.04)
    fig.savefig(out, dpi=170)
    plt.close(fig)
    print("wrote", out)


if __name__ == "__main__":
    lab = [f"({'abcd'[i]}) {nm}" for i, (nm, _) in enumerate(AREAS)]
    grid("map2", OUT / "fig_split1_footprints.png", labels=lab)
    cost_surface(OUT / "fig_split2_cost_surface.png")
    grid("map4", OUT / "fig_stage_AB.png", labels=lab)
    grid("map5", OUT / "fig_shared_network_detail.png", labels=lab)
