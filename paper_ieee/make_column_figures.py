"""Derive single-column figures (no new data): crops of existing maps and a column-width re-plot of the Adilabad sensitivity CSVs.
Run: python paper_ieee/make_column_figures.py   (writes paper_ieee/figures/*.png; copy to paper_eris/figures by the build step)"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import pandas as pd, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
H = Path(__file__).resolve().parent; REPO = H.parent; F = H / "figures"
A = REPO / "DELIVERABLES_CONTRIBUTION_3_MULTI_VILLAGE/01_ADILABAD"
S = REPO / "DELIVERABLES_DAMARAKUNTA_STAGE_B/02_FINAL_MAPS/final_maps_1_to_5"
FONT = ImageFont.truetype(str(Path(matplotlib.get_data_path()) / "fonts/ttf/DejaVuSans-Bold.ttf"), 95)
def label(im, txt, xy=(30, 20)):
    d = ImageDraw.Draw(im); d.rectangle([xy[0] - 10, xy[1] - 5, xy[0] + 130, xy[1] + 120], fill="white"); d.text(xy, txt, fill="black", font=FONT); return im
# Adilabad map2: panels (a)(b) full window, (c)(d) zoom; titles/legend removed (described in the captions)
m2 = Image.open(A / "figures/map2_network_comparison.png").convert("RGB")
a = m2.crop((116, 500, 1500, 2325)); b = m2.crop((1675, 500, 3081, 2325))
w = a.width + b.width + 30; ab = Image.new("RGB", (w, 1825), "white"); ab.paste(label(a, "(a)"), (0, 0)); ab.paste(label(b, "(b)"), (a.width + 30, 0)); ab.save(F / "adilabad_map2_ab.png")
c = m2.crop((3305, 500, 4456, 1330)); d = m2.crop((3305, 1500, 4456, 2325))
cd = Image.new("RGB", (c.width + d.width + 30, max(c.height, d.height)), "white"); cd.paste(label(c, "(c)"), (0, 0)); cd.paste(label(d, "(d)"), (c.width + 30, 0)); cd.save(F / "adilabad_map2_cd.png")
# Damarakunta: imagery overview (footer with the old draft note removed) and cost-surface panel
m1 = Image.open(S / "map1_imagery_boundary_roads.png").convert("RGB"); m1.crop((330, 70, 3000, 1740)).resize((1800, int(1670 * 1800 / 2670)), Image.LANCZOS).save(F / "dk_map1_satellite.jpg", quality=88)
m3 = Image.open(S / "map3_terrain_cost_landcover_slope.png").convert("RGB"); m3.crop((0, 1500, 1640, 2650)).save(F / "dk_cost_surface.png")
def sens_fig(src_dir, out_name):
    ps = pd.read_csv(src_dir / "penalty_sensitivity.csv"); om = pd.read_csv(src_dir / "omission_summary.csv")
    plt.rcParams.update({"font.size": 6.5, "font.family": "DejaVu Sans"})
    fig, ax = plt.subplots(2, 1, figsize=(3.4, 4.6)); a1, a2 = ax
    for mode, col in (("centre-in-footprint", "tab:blue"), ("buffered 7.1 m", "tab:green")):
        q = ps[ps.penalty_mode == mode]; a1.scatter(q.unique_len_m / 1000, q.len_in_footprints_m, c=col, s=22, edgecolor="k", label=mode, zorder=3)
        OFF = {("centre-in-footprint", 1): (5, 3), ("centre-in-footprint", 4): (5, 4), ("centre-in-footprint", 20): (-34, -9), ("centre-in-footprint", 100): (5, 7), ("buffered 7.1 m", 20): (-44, 8), ("buffered 7.1 m", 100): (-58, -14)}
        for _, r in q.iterrows(): a1.annotate(f"μ={int(r.mu)}, {int(r.routes_crossing)} routes", (r.unique_len_m / 1000, r.len_in_footprints_m), xytext=OFF[(mode, int(r.mu))], textcoords="offset points", fontsize=5.5)
    a1.set_xlabel("Unique network length (km)"); a1.set_ylabel("Route length inside\nother footprints (m)"); a1.set_title("(a) Footprint-penalty trade-off", fontsize=7, loc="left"); a1.set_ylim(850, 5200); a1.legend(fontsize=5.5); a1.grid(alpha=.25)
    for _, r in om.iterrows():
        rnd = "random" in r.group; col = "tab:blue" if rnd else "tab:orange"
        if rnd: a2.errorbar(r.unserved, r.delta_len_pct, yerr=[[r.delta_len_pct - r.delta_min], [r.delta_max - r.delta_len_pct]], fmt="none", ecolor=col, capsize=2)
        a2.scatter(r.unserved, r.delta_len_pct, c=col, s=22, edgecolor="k", zorder=3)
        off = {"omit 10% (random)": (6, 6), "omit smallest 10%": (7, -15), "omit 20% (random)": (6, 3), "omit smallest 25%": (6, 3)}[r.group]
        a2.annotate(f"{r.group}\n{r.delta_len_pct:.1f}%, {round(r.unserved)} unserved", (r.unserved, r.delta_len_pct), xytext=off, textcoords="offset points", fontsize=5.3)
    a2.axhline(0, c="gray", lw=.6); a2.set_xlim(60, 290); a2.set_ylim(-26, 2); a2.set_xlabel("Road-gap houses left without a route (incl. baseline failure)"); a2.set_ylabel("Unique-length change (%)")
    a2.set_title("(b) Omission sensitivity", fontsize=7, loc="left"); a2.grid(alpha=.25)
    fig.tight_layout(); fig.savefig(F / out_name, dpi=300); plt.close(fig)



SEG = REPO / "DELIVERABLES_CONTRIBUTION_3_MULTI_VILLAGE/01_ADILABAD_SEGMENTATION"
sens_fig(A, "adilabad_sens_col.png")
if (SEG / "penalty_sensitivity.csv").exists():
    sens_fig(SEG, "adilabad_seg_sens_col.png")
    # satellite composites from the segmentation run (every panel already carries the Esri credit line)
    Image.MAX_IMAGE_PIXELS = None
    g = lambda n: Image.open(SEG / "figures" / n).convert("RGB")
    def fit(im, w): return im.resize((w, int(im.height * w / im.width)), Image.LANCZOS)
    def pair(l, r, ll, rl, out, w=1800):
        H = max(l.height, r.height); c = Image.new("RGB", (l.width + r.width + 30, H), "white")
        c.paste(label(l.copy(), ll), (0, 0)); c.paste(label(r.copy(), rl), (l.width + 30, 0)); fit(c, w).save(F / out, quality=88)
    a1, b1, lg = g("sat_map1_a.png"), g("sat_map1_b.png"), g("sat_legend.png")
    right = Image.new("RGB", (b1.width, a1.height), "white"); right.paste(b1, (0, 0)); lgf = fit(lg, b1.width); right.paste(lgf, (0, b1.height + 40))
    pair(a1, right, "(a)", "(b)", "adilabad_sat_overview.jpg")
    pair(g("sat_map2_independent_window.png"), g("sat_map2_two_stage_window.png"), "(a)", "(b)", "adilabad_sat_routes_window.jpg")
    pair(g("sat_map2_independent_zoom.png"), g("sat_map2_two_stage_zoom.png"), "(c)", "(d)", "adilabad_sat_routes_zoom.jpg")
print("ok")
