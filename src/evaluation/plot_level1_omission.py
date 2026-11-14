"""Level 1 (Stage B) omission-sensitivity figure, regenerated from the recorded table (resolves U12, the overlapping-legend defect of the original chart).

    python -m src.evaluation.plot_level1_omission        # writes figD_level1_omission.png (300 dpi) to paper/figures/ and docs/results/hierarchy_real_run/figures/

Source: DELIVERABLES_DAMARAKUNTA_STAGE_B/03_RESULTS_TABLES/COMPARISON_TABLES/table4_c1_sensitivity.csv (5 seeds for the random scenarios, 1 deterministic run otherwise).
Panel (a): change of the unique network length against the number of households left without a route (U = 163 - routed); error bars are the
min-max over the five seeds. Panel (b): unique length per routed target. No legend: every point is labelled directly.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from src.evaluation.plot_hierarchy_figures import DPI, RUN  # noqa: E402  (shared style: rcParams, dpi)

CSV = REPO / "DELIVERABLES_DAMARAKUNTA_STAGE_B" / "03_RESULTS_TABLES" / "COMPARISON_TABLES" / "table4_c1_sensitivity.csv"
NAME = "figD_level1_omission"
N_TARGETS = 163
# scenario -> (display label, family colour, marker)
FAMILY = {"omit 10%": ("Random 10 %", "#1f78b4", "o"), "omit 20%": ("Random 20 %", "#1f78b4", "o"),
          "omit smallest 10%": ("Smallest 10 %", "#d95f02", "s"), "omit smallest 25%": ("Smallest 25 %", "#d95f02", "s"),
          "omit merged blobs": ("Merged blobs", "#7570b3", "D"),
          "add 10%": ("Add 10 %", "#1b9e77", "^"), "add 20%": ("Add 20 %", "#1b9e77", "^")}
ORDER = list(FAMILY)


def load():
    t = pd.read_csv(CSV).set_index("perturbation")
    base = float(t.loc["baseline (no perturbation)", "unique_len_m_mean"])
    base_per = float(t.loc["baseline (no perturbation)", "unique_len_per_routed_m_mean"])
    rows = []
    for k in ORDER:
        r = t.loc[k]
        rows.append(dict(key=k, label=FAMILY[k][0], short=FAMILY[k][0].replace(" by area", "").replace(" (random)", ""), color=FAMILY[k][1], marker=FAMILY[k][2], routed=float(r.house_targets_routed_mean),
                         unserved=max(0.0, N_TARGETS - float(r.house_targets_routed_mean)),
                         dL=100 * (float(r.unique_len_m_mean) - base) / base, dL_lo=100 * (float(r.unique_len_m_min) - base) / base,
                         dL_hi=100 * (float(r.unique_len_m_max) - base) / base, per=float(r.unique_len_per_routed_m_mean), seeds=int(r.runs)))
    return pd.DataFrame(rows), base, base_per


def figure():
    d, base, base_per = load()
    fig, (a, b) = plt.subplots(1, 2, figsize=(7.16, 3.15), gridspec_kw=dict(width_ratios=[1.12, 1.0], wspace=0.62, left=0.075, right=0.985, top=0.9, bottom=0.17))
    # ---------------- (a) length change vs unserved households
    a.axhline(0, color="#888888", lw=0.7, zorder=1)
    for _, r in d.iterrows():
        if r.seeds > 1:
            a.errorbar(r.unserved, r.dL, yerr=[[r.dL - r.dL_lo], [r.dL_hi - r.dL]], fmt="none", ecolor=r.color, elinewidth=1.0, capsize=2.5, zorder=2, alpha=0.8)
        a.scatter(r.unserved, r.dL, marker=r.marker, s=34, c=r.color, edgecolor="k", lw=0.5, zorder=3)
    # labels form a column in the empty right-hand region; leader lines attach to each label's left edge, so nothing overlaps a marker or another label
    col = {"omit 10%": 8, "omit smallest 10%": 2, "omit 20%": -4, "omit smallest 25%": -10, "omit merged blobs": -16}
    for _, r in d.iterrows():
        if r.key.startswith("add"):
            a.annotate(f"{r.short}: {r.dL:+.1f}%, U = 0", (r.unserved, r.dL), xytext=(r.unserved + 5, r.dL), textcoords="data", ha="left", va="center", fontsize=5.8)
        else:
            a.annotate(f"{r.short}: {r.dL:+.1f}%, U = {int(round(r.unserved))}", (r.unserved, r.dL), xytext=(50, col[r.key]), textcoords="data", ha="left", va="center", fontsize=5.8,
                       arrowprops=dict(arrowstyle="-", lw=0.5, color="#777777", shrinkA=1, shrinkB=3, relpos=(0, 0.5)))
    a.set_xlim(-4, 84)
    a.set_ylim(-38, 22)
    a.set_xlabel(f"Households left without a route, $U$ (of {N_TARGETS})")
    a.set_ylabel("Network length change vs baseline (%)")
    a.grid(True, lw=0.3, color="#e6e6e6")
    a.set_title(f"(a)  Shorter plan, more households lost (baseline {base:,.0f} m)", loc="left")
    # ---------------- (b) length per routed target
    ys = np.arange(len(d))[::-1]
    b.axvline(base_per, color="#666666", ls=(0, (4, 3)), lw=0.9, zorder=1)
    for y, (_, r) in zip(ys, d.iterrows()):
        b.hlines(y, base_per, r.per, color=r.color, lw=1.2, alpha=0.6, zorder=2)
        b.scatter(r.per, y, marker=r.marker, s=34, c=r.color, edgecolor="k", lw=0.5, zorder=3)
        right = r.per >= base_per
        b.text(r.per + (0.3 if right else -0.3), y, f"{r.per:.1f}", ha="left" if right else "right", va="center", fontsize=6)
    b.set_yticks(ys)
    b.set_yticklabels(d.label, fontsize=6)
    b.set_xlim(29.8, 37.4)
    b.set_ylim(-0.7, len(d) + 0.15)
    b.set_xlabel("Unique length per routed target (m)")
    b.text(base_per + 0.12, len(d) - 0.3, f"baseline {base_per:.1f} m", fontsize=6, color="#555555", va="center")
    b.grid(True, axis="x", lw=0.3, color="#e6e6e6")
    b.set_title("(b)  Length per routed target (m)", loc="left")
    return fig


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", nargs="+", default=[str(REPO / "paper" / "figures"), str(RUN / "figures")])
    a = ap.parse_args(argv)
    outs = [Path(o) for o in a.out]
    for o in outs:
        o.mkdir(parents=True, exist_ok=True)
    fig = figure()
    first = outs[0] / f"{NAME}.png"
    fig.savefig(first, dpi=DPI, facecolor="white")
    plt.close(fig)
    for o in outs[1:]:
        shutil.copy2(first, o / first.name)
    print("wrote", first)
    return first


if __name__ == "__main__":
    main()
