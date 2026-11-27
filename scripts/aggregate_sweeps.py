"""Task 2 - aggregate the omission (error-propagation) and footprint-penalty sweeps of all four windows into LaTeX tables.

Step 1 (per window; ON THE MACHINE THAT HOLDS data/villages/<id>/state_segmentation.pkl; ~2 s Damarakunta, minutes-hours for Adilabad):
    python -m src.multivillage.run --village damarakunta_open        --variant segmentation --steps route --workers 4
    python -m src.multivillage.run --village adilabad_urban_updated  --variant segmentation --steps route --workers 4
    python -m src.multivillage.run --village aswaraopeta             --variant segmentation --steps route --workers 4
    python -m src.multivillage.run --village alampur                 --variant segmentation --steps route --workers 4
  (no --quick = the full job list: penalty sweep, omission scenarios, 20 / 50 m road-gap definitions; results are appended to state_segmentation.pkl, which is git-ignored;
   the 'main' job is deterministic and reproduces the paper's two-stage numbers.)
Step 2:  python scripts/aggregate_sweeps.py        -> validation/sweeps_omission.{csv,tex}, sweeps_penalty.{csv,tex}

Scope: these sweeps run on the planner's 10 m SOFT-penalty grid (footprints penalised, mu = 4), so their absolute lengths are the 10 m numbers (e.g. Damarakunta two-stage 1.47 km),
not the 5 m hard-clearance numbers of the main results table (1.31 km); read the sweeps as relative changes. Cost = length x Rs 75 lakh/km (owner-supplied, unverified; 60-90 sensitivity).
Omission = a share of road-gap households is missing from the extracted footprints: they are neither routed nor penalised ('unserved'); the rest are re-planned.
Total length falls when households are omitted simply because fewer households are served, so read it together with the 'm per served household' column.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.multivillage import grid_graph as GG, report as R  # noqa: E402


def one_window(key: str, log=print):
    L = GG.load_window(key)
    if L is None:
        log(f"[{key}] SKIPPED: data/villages/{GG.WINDOWS[key]}/state_segmentation.pkl is not on this machine")
        return None
    cfg, S, _, _ = L
    res = S.get("results", [])
    if not any(r["spec"]["kind"] == "omit" for r in res):
        log(f"[{key}] SKIPPED: state has no omission results; run the Step 1 command above (without --quick)")
        return None
    main = next(r for r in res if r["spec"]["kind"] == "main")["out"]
    two = next(x for x in main["rows"] if x["plan"] == "Two-stage shared plan")
    base, n_gap = float(two["unique_len_m"]), len(S["gap"])
    _, g = R.omission_table(res, base, n_gap)
    om = [dict(window=key, scenario="none (all footprints)", runs=1, gap_households=n_gap, unserved_households=n_gap - two["targets_routed"], stage_B_len_km=round(base / 1000, 3),
               delta_len_pct=0.0, delta_min=0.0, delta_max=0.0, m_per_served_hh=round(base / two["targets_routed"], 1))]
    for r in g.itertuples():
        om.append(dict(window=key, scenario=r.group, runs=r.runs, gap_households=n_gap, unserved_households=r.unserved, stage_B_len_km=round(r.unique_len_m / 1000, 3),
                       delta_len_pct=r.delta_len_pct, delta_min=r.delta_min, delta_max=r.delta_max, m_per_served_hh=r.len_per_routed_house_m))
    pen = []
    for r in res:
        if r["spec"]["kind"] == "penalty":
            x = r["row"]
            pen.append(dict(window=key, penalty_mode=x["penalty_mode"], mu=x["mu"], gap_households=x["targets"], unserved_households=x["targets"] - x["routed"], stage_B_len_km=round(x["unique_len_m"] / 1000, 3),
                            saving_vs_independent_pct=x["saving_vs_independent_pct"], routes_crossing=x["routes_crossing"], len_in_footprints_m=x["len_in_footprints_m"]))
    pen.append(dict(window=key, penalty_mode="centre-in-footprint (main)", mu=cfg["planner"]["building_mult"], gap_households=n_gap, unserved_households=n_gap - two["targets_routed"],
                    stage_B_len_km=round(base / 1000, 3), saving_vs_independent_pct=round(100 * (1 - base / next(x for x in main["rows"] if x["plan"].startswith("Independent"))["unique_len_m"]), 1),
                    routes_crossing=two["routes_crossing"], len_in_footprints_m=two["len_in_footprints_m"]))
    log(f"[{key}] {len(om)} omission rows, {len(pen)} penalty rows (base two-stage {base:.0f} m)")
    return pd.DataFrame(om), pd.DataFrame(pen)


def tex_omission(df: pd.DataFrame) -> str:
    out = ["\\begin{tabular}{llrrrrrr}", "\\hline", "Window & Footprints missing & Unserved hh & Stage B (km) & Cost (Rs lakh) & $\\Delta$ length (\\%) & range (\\%) & m / served hh \\\\", "\\hline"]
    for w, g in df.groupby("window", sort=False):
        for i, r in enumerate(g.itertuples()):
            out.append(f"{w.capitalize() if i == 0 else ''} & {r.scenario} & {r.unserved_households:.0f} & {r.stage_B_len_km:.2f} & {r.stage_B_len_km * GG.RATE_LAKH_PER_KM:.0f} & {r.delta_len_pct:+.1f} & {r.delta_min:+.1f} to {r.delta_max:+.1f} & {r.m_per_served_hh:.0f} \\\\")
        out.append("\\hline")
    return "\n".join(out + ["\\end{tabular}"]) + "\n"


def tex_penalty(df: pd.DataFrame) -> str:
    d = df[df.penalty_mode.str.startswith("centre")].sort_values(["window", "mu"], kind="stable")
    out = ["\\begin{tabular}{lrrrrr}", "\\hline", "Window & $\\mu$ & Unserved hh & Stage B (km) & Cost (Rs lakh) & Routes crossing \\\\", "\\hline"]
    for w, g in d.groupby("window", sort=False):
        for i, r in enumerate(g.itertuples()):
            out.append(f"{w.capitalize() if i == 0 else ''} & {r.mu:g} & {r.unserved_households:.0f} & {r.stage_B_len_km:.2f} & {r.stage_B_len_km * GG.RATE_LAKH_PER_KM:.0f} & {r.routes_crossing} \\\\")
        out.append("\\hline")
    return "\n".join(out + ["\\end{tabular}"]) + "\n"


def main():
    parts = [p for p in (one_window(k) for k in GG.WINDOWS) if p]
    if not parts:
        raise SystemExit("no window has full-sweep results yet: run the Step 1 commands in the docstring")
    om, pen = pd.concat([p[0] for p in parts]), pd.concat([p[1] for p in parts])
    om["cost_rs_lakh"] = (om.stage_B_len_km * GG.RATE_LAKH_PER_KM).round(1)
    pen["cost_rs_lakh"] = (pen.stage_B_len_km * GG.RATE_LAKH_PER_KM).round(1)
    GG.OUT.mkdir(parents=True, exist_ok=True)
    om.to_csv(GG.OUT / "sweeps_omission.csv", index=False, lineterminator="\n")
    pen.to_csv(GG.OUT / "sweeps_penalty.csv", index=False, lineterminator="\n")
    (GG.OUT / "sweeps_omission.tex").write_text(tex_omission(om))
    (GG.OUT / "sweeps_penalty.tex").write_text(tex_penalty(pen))
    print(om.to_string(index=False)); print(pen.sort_values(["window", "penalty_mode", "mu"]).to_string(index=False))


if __name__ == "__main__":
    main()
