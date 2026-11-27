"""LaTeX tables and prose numbers for the manuscripts, read ONLY from DELIVERABLES_CONTRIBUTION_3_MULTI_VILLAGE/validation/*.csv.

Nothing is typed in by hand: every figure the validation sections quote is formatted from these files, so a re-run of the scripts (footprint_crossval, steiner_baseline,
accessibility_metrics, aggregate_sweeps) regenerates the tables and text consistently. Used by paper_erl/build_main.py and paper_srs/build_main.py.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

V = Path(__file__).resolve().parents[2] / "DELIVERABLES_CONTRIBUTION_3_MULTI_VILLAGE" / "validation"
ORDER = ["damarakunta", "adilabad", "aswaraopeta", "alampur"]
NAME = {"damarakunta": "Damarakunta", "adilabad": "Adilabad", "aswaraopeta": "Aswaraopeta", "alampur": "Alampur"}
RATE = 75.0


def _csv(name):
    return pd.read_csv(V / name)


def n(x) -> str:
    return f"{int(round(x)):,}".replace(",", "{,}")


def f(x, d=2) -> str:
    return f"{x:.{d}f}"


def sg(x, d=1) -> str:
    s = f"{x:+.{d}f}"
    return s.replace("-", "$-$")


# ---------------------------------------------------------------------------------------------- footprint agreement
REFS = {"Overture (all sources)": "Overture, all sources", "Overture - OSM only": "Overture, OSM subset", "Overture - Google only": "Overture, Google subset", "Google Open Buildings v3 (raw)": "Google Open Buildings v3 (raw)"}
MIN_REF = 100            # sub-source rows with fewer reference features are not tabulated (Aswaraopeta's OSM subset has 7)


def fp_df() -> pd.DataFrame:
    d = _csv("footprint_crossval.csv")
    d = d[d.region == "model coverage"]
    return d[(d.b == "Overture (all sources)") | (d.n_b >= MIN_REF)]


def fp_all() -> pd.DataFrame:
    return _csv("footprint_crossval.csv")


def tab_footprint(width_note=False) -> str:
    d = fp_df()
    out = ["\\begin{tabular}{@{}llrrrrrrr@{}}", "\\toprule",
           "Window & Reference & Ref.\\ $n$ & Area IoU & Area P & Area R & Detect.\\ P & Detect.\\ R & Merged (\\%)\\\\", "\\midrule"]
    for w in ORDER:
        g = d[d.window == w]
        for i, r in enumerate(g.itertuples()):
            out.append(f"{NAME[w] if i == 0 else ''} & {REFS[r.b]} & {n(r.n_b)} & {f(r.area_iou, 3)} & {f(r.area_precision, 3)} & {f(r.area_recall, 3)} & {f(r.det_precision, 3)} & {f(r.det_recall, 3)} & {r.ours_merging_2plus_ref_pct:.1f}\\\\")
        if w != ORDER[-1]:
            out.append("\\addlinespace")
    out += ["\\bottomrule", "\\end{tabular}"]
    return "\n".join(out)


def fp_facts() -> dict:
    d = _csv("footprint_crossval.csv")
    o = d[(d.region == "model coverage") & (d.b == "Overture (all sources)")].set_index("window").loc[ORDER]
    w = d[(d.region == "window") & (d.b == "Overture (all sources)")].set_index("window").loc[ORDER]
    rng = lambda s, k=3: f"{s.min():.{k}f}--{s.max():.{k}f}"
    return dict(n_ours={k: int(o.loc[k, "n_a"]) for k in ORDER}, iou=rng(o.area_iou), area_p=rng(o.area_precision), area_r=rng(o.area_recall), det_p=rng(o.det_precision), det_r=rng(o.det_recall),
                merged=f"{o.ours_merging_2plus_ref_pct.min():.0f}--{o.ours_merging_2plus_ref_pct.max():.0f}", inst_f1_max=f"{o.inst_f1.max():.3f}", inst_f1_min=f"{o.inst_f1.min():.3f}",
                dk_cov_km2=f"{o.loc['damarakunta', 'region_km2']:.3f}", dk_win_km2=f"{w.loc['damarakunta', 'region_km2']:.3f}", dk_nref_cov=int(o.loc["damarakunta", "n_b"]), dk_nref_win=int(w.loc["damarakunta", "n_b"]),
                dk_det_r_win=f"{w.loc['damarakunta', 'det_recall']:.3f}", dk_det_r_cov=f"{o.loc['damarakunta', 'det_recall']:.3f}", o=o, w=w, all=d)


# ---------------------------------------------------------------------------------------------- Steiner / MST baselines
METH = {"Stage A (independent least-cost)": "Stage A (independent)", "Stage B (two-stage shared)": "Stage B (two-stage shared)", "Kou Steiner tree (same grid)": "Kou Steiner tree", "Euclidean MST (straight lines)": "Euclidean MST"}


def st_df(targets="houses") -> pd.DataFrame:
    d = _csv("steiner_baseline.csv")
    return d[d.targets == targets]


def tab_steiner() -> str:
    d = st_df()
    out = ["\\begin{tabular}{@{}l" + "r" * len(ORDER) + "@{}}", "\\toprule", "Method & " + " & ".join(NAME[w] for w in ORDER) + "\\\\", "\\midrule",
           "Targets (houses) & " + " & ".join(n(d[d.window == w].n_targets.iloc[0]) for w in ORDER) + "\\\\", "\\midrule"]
    for m, lab in METH.items():
        cells = []
        for w in ORDER:
            r = d[(d.window == w) & (d.method == m)].iloc[0]
            c = f"{f(r.unique_len_km)}"
            if lab.startswith("Stage B"):
                c += " (ref.)"
            else:
                c += f" ({sg(r.vs_stage_B_pct)}\\%)"
            cells.append(c)
        out.append(f"{lab}: length, km & " + " & ".join(cells) + "\\\\")
    out.append("\\midrule")
    for m, lab in METH.items():
        cells = []
        for w in ORDER:
            r = d[(d.window == w) & (d.method == m)].iloc[0]
            cells.append(n(r.cost_rs_lakh))
        out.append(f"{lab}: cost, Rs lakh & " + " & ".join(cells) + "\\\\")
    out.append("\\midrule")
    cells = []
    for w in ORDER:
        r = d[(d.window == w) & (d.method.str.startswith("Euclidean"))].iloc[0]
        cells.append(f"{int(r.routes_or_edges_crossing_buildings)} ({r.note.split(' m')[0]} m)")
    out.append("Euclidean MST: edges crossing a building (length inside) & " + " & ".join(cells) + "\\\\")
    cells = []
    for w in ORDER:
        s = d[d.window == w]
        cells.append(str(int(s[s.method.str.startswith(("Stage", "Kou"))].routes_or_edges_crossing_buildings.sum())))
    out.append("Stages A, B and Kou tree: crossing routes (total) & " + " & ".join(cells) + "\\\\")
    out += ["\\bottomrule", "\\end{tabular}"]
    return "\n".join(out)


def st_facts() -> dict:
    d, d2 = st_df(), st_df("houses + facilities")
    g = lambda dd, w, m, c: dd[(dd.window == w) & (dd.method == m)].iloc[0][c]
    kou = {w: g(d, w, "Kou Steiner tree (same grid)", "vs_stage_B_pct") for w in ORDER}
    stA = {w: g(d, w, "Stage A (independent least-cost)", "vs_stage_B_pct") for w in ORDER}
    mst = {w: g(d, w, "Euclidean MST (straight lines)", "vs_stage_B_pct") for w in ORDER}
    mstx = {w: int(g(d, w, "Euclidean MST (straight lines)", "routes_or_edges_crossing_buildings")) for w in ORDER}
    obj_better = sum(g(d, w, "Stage B (two-stage shared)", "cost_surface_objective") < g(d, w, "Kou Steiner tree (same grid)", "cost_surface_objective") for w in ORDER)
    kou2 = {w: g(d2, w, "Kou Steiner tree (same grid)", "vs_stage_B_pct") for w in ORDER}
    return dict(kou=kou, stA=stA, mst=mst, mstx=mstx, obj_better=int(obj_better), kou_fac=kou2, d=d, d2=d2,
                kou_rng=f"{min(kou.values()):.1f}--{max(kou.values()):.1f}", stA_rng=f"{min(stA.values()):.1f}--{max(stA.values()):.1f}",
                mst_rng=f"{min(abs(v) for v in mst.values()):.1f}--{max(abs(v) for v in mst.values()):.1f}")


# ---------------------------------------------------------------------------------------------- accessibility
def ac_df() -> pd.DataFrame:
    return _csv("accessibility_summary.csv").set_index("window").loc[ORDER]


def tab_access() -> str:
    a = ac_df()
    out = ["\\begin{tabular}{@{}l" + "r" * len(ORDER) + "@{}}", "\\toprule", "Metric & " + " & ".join(NAME[w] for w in ORDER) + "\\\\", "\\midrule"]
    row = lambda lab, fn: out.append(lab + " & " + " & ".join(fn(a.loc[w]) for w in ORDER) + "\\\\")
    row("Households (footprints used)", lambda r: n(r.households))
    row("Within road-gap distance of a road", lambda r: f"{n(r.served_baseline)} ({r.served_pct_baseline:.1f}\\%)")
    row("Road-gap households", lambda r: n(r.road_gap_households))
    row("Routed, Stage A / Stage B", lambda r: f"{n(r.routed_stage_A)} / {n(r.routed_stage_B)}")
    row("Unreachable (no clear lane or route)", lambda r: n(r.unreachable))
    row("Served after Stage B", lambda r: f"{r.served_pct_stage_B:.1f}\\%")
    row("Verified facilities", lambda r: n(r.facilities))
    row("Facilities reached: baseline $\\rightarrow$ Stage B", lambda r: f"{int(r.fac_reached_baseline)}$\\rightarrow${int(r.fac_reached_stage_B)}")
    row("Median distance to nearest road, m: baseline $\\rightarrow$ Stage B", lambda r: f"{r.road_dist_baseline_median_m:.1f}$\\rightarrow${r.line_dist_stage_B_median_m:.1f}")
    row("Mean network path to road, m: Stage A / Stage B", lambda r: f"{r.path_dist_stage_A_mean_m:.1f} / {r.path_dist_stage_B_mean_m:.1f}")
    row("Median network path to road, m: Stage A / Stage B", lambda r: f"{r.path_dist_stage_A_median_m:.1f} / {r.path_dist_stage_B_median_m:.1f}")
    out += ["\\bottomrule", "\\end{tabular}"]
    return "\n".join(out)


# ---------------------------------------------------------------------------------------------- sweeps
SC = ["none (all footprints)", "omit 10% (random)", "omit 20% (random)", "omit smallest 10%", "omit smallest 25%"]
SCL = ["None", "10\\% random", "20\\% random", "Smallest 10\\%", "Smallest 25\\%"]


def om_df() -> pd.DataFrame:
    return _csv("sweeps_omission.csv")


def pen_df() -> pd.DataFrame:
    return _csv("sweeps_penalty.csv")


def tab_omission() -> str:
    d = om_df()
    out = ["\\begin{tabular}{@{}ll" + "r" * len(SC) + "@{}}", "\\toprule", "Window & Quantity & " + " & ".join(SCL) + "\\\\", "\\midrule"]
    for w in ORDER:
        g = d[d.window == w].set_index("scenario").loc[SC]
        out.append(f"{NAME[w]} ({n(g.gap_households.iloc[0])} road-gap hh) & Stage B length, km & " + " & ".join(f(x, 2) for x in g.stage_B_len_km) + "\\\\")
        out.append(" & Unserved households & " + " & ".join(f(x, 1) if x != int(x) else str(int(x)) for x in g.unserved_households) + "\\\\")
        out.append(" & Length per served household, m & " + " & ".join(f(x, 1) for x in g.m_per_served_hh) + "\\\\")
        if w != ORDER[-1]:
            out.append("\\addlinespace")
    out += ["\\bottomrule", "\\end{tabular}"]
    return "\n".join(out)


MU = [1.0, 4.0, 20.0, 100.0]


def pen_cip() -> pd.DataFrame:
    d = pen_df()
    d = d[d.penalty_mode.str.startswith("centre")].copy()
    return d


def tab_penalty() -> str:
    d = pen_cip()
    out = ["\\begin{tabular}{@{}ll" + "r" * len(MU) + "@{}}", "\\toprule", "Window & Quantity & " + " & ".join(f"$\\mu={m:g}$" + (" (main)" if m == 4 else "") for m in MU) + "\\\\", "\\midrule"]
    for w in ORDER:
        g = d[d.window == w].set_index("mu").loc[MU]
        out.append(f"{NAME[w]} & Stage B length, km & " + " & ".join(f(x, 2) for x in g.stage_B_len_km) + "\\\\")
        out.append(" & Routes crossing a footprint & " + " & ".join(str(int(x)) for x in g.routes_crossing) + "\\\\")
        out.append(" & Length inside footprints, m & " + " & ".join(f(x, 1) for x in g.len_in_footprints_m) + "\\\\")
        if w != ORDER[-1]:
            out.append("\\addlinespace")
    out += ["\\bottomrule", "\\end{tabular}"]
    return "\n".join(out)


def sw_facts() -> dict:
    d = om_df()
    g = lambda w, s, c: d[(d.window == w) & (d.scenario == s)].iloc[0][c]
    p = pen_cip()
    pm = lambda w, mu, c: p[(p.window == w) & (p.mu == mu)].iloc[0][c]
    return dict(d=d, g=g, pm=pm,
                d20=" , ".join(f"{g(w, 'omit 20% (random)', 'delta_len_pct'):+.1f}" for w in ORDER),
                dlen20={w: g(w, "omit 20% (random)", "delta_len_pct") for w in ORDER}, unserved20={w: g(w, "omit 20% (random)", "unserved_households") for w in ORDER},
                gap={w: int(g(w, "none (all footprints)", "gap_households")) for w in ORDER}, mph0={w: g(w, "none (all footprints)", "m_per_served_hh") for w in ORDER},
                mph20={w: g(w, "omit 20% (random)", "m_per_served_hh") for w in ORDER}, mph25={w: g(w, "omit smallest 25%", "m_per_served_hh") for w in ORDER},
                dlen25={w: g(w, "omit smallest 25%", "delta_len_pct") for w in ORDER}, unserved25={w: g(w, "omit smallest 25%", "unserved_households") for w in ORDER})


# ---------------------------------------------------------------------------------------------- prose (identical wording in both manuscripts; every number comes from the CSVs)
def paras() -> dict:
    fp, st, sw, a = fp_facts(), st_facts(), sw_facts(), ac_df()
    allfp = fp_all()
    mc = allfp[allfp.region == "model coverage"].set_index(["window", "b"])
    cov = lambda w, b, c: mc.loc[(w, b), c]
    pen = pen_cip()
    p = lambda w, mu, c: pen[(pen.window == w) & (pen.mu == mu)].iloc[0][c]
    pa, pb = a.path_dist_stage_A_mean_m, a.path_dist_stage_B_mean_m
    ids = lambda dct, fmt: ", ".join(fmt(dct[w]) for w in ORDER)
    P = {}
    P["intro"] = ("Four automated checks extend the main comparison. They use only the open layers of the Data section, no manual labelling and no field survey, and they are run by "
                  "\\texttt{footprint\\_crossval.py}, \\texttt{steiner\\_baseline.py}, \\texttt{accessibility\\_metrics.py} and \\texttt{aggregate\\_sweeps.py}; their outputs are in "
                  "\\path{DELIVERABLES_CONTRIBUTION_3_MULTI_VILLAGE/validation}. They therefore measure agreement between open datasets and planning behaviour, not accuracy against ground truth.")
    P["footprint"] = (
        "\\textbf{Cross-source footprint agreement.} Table~\\ref{tab:xval} compares the segmentation footprints with Overture Maps buildings (OpenStreetMap and Google Open Buildings sources, "
        "release 2026-10-21.0) and, in Damarakunta, with the raw Google Open Buildings v3 polygons, inside each window's model-coverage region (the window intersected with the 30~m-buffered convex hull "
        f"of the footprints; for Damarakunta this is {fp['dk_cov_km2']} of {fp['dk_win_km2']}~km$^2$ because the stored footprints cover part of the window only, and over the whole window the detection recall is "
        f"{fp['dk_det_r_win']} instead of {fp['dk_det_r_cov']}). Against all Overture sources, area IoU is {fp['iou']}, area precision (share of our area covered by the reference) {fp['area_p']} and area recall "
        f"(share of the reference area covered by our footprints) {fp['area_r']} across the four windows. At the object level, detection precision (share of our footprints that touch a reference building) is {fp['det_p']} and "
        f"detection recall (share of reference buildings whose representative point lies in one of our footprints) is {fp['det_r']}. Between {fp['merged'].replace('--', ' and ')}\\% of our footprints contain two or more "
        f"Overture buildings: the model groups dense contiguous roofs, so one-to-one instance matching at IoU~0.5 reaches an F1 of only {fp['inst_f1_min']}--{fp['inst_f1_max']} and is not a meaningful score for these footprints. "
        f"The agreement differs by source: the human-mapped OpenStreetMap subset is covered far more completely than the machine-derived Google subset in Adilabad (detection recall "
        f"{cov('adilabad', 'Overture - OSM only', 'det_recall'):.3f} against {cov('adilabad', 'Overture - Google only', 'det_recall'):.3f}) and in Alampur "
        f"({cov('alampur', 'Overture - OSM only', 'det_recall'):.3f} against {cov('alampur', 'Overture - Google only', 'det_recall'):.3f}), whereas its subset has only "
        f"{int(cov('aswaraopeta', 'Overture - OSM only', 'n_b'))} features in Aswaraopeta and too few to score (fewer than five) in Damarakunta, and is not tabulated for either. "
        "No reference is treated as truth, since each has its own omissions and merging. Most of our footprints touch an open-inventory building, but our footprints reach only about half to three quarters of the reference buildings and "
        "group dense roofs, which is the footprint-granularity limitation that the error-propagation test below quantifies.")
    P["graph"] = (
        "\\textbf{Graph-routing baselines.} Table~\\ref{tab:graphbase} sets Stage~A and Stage~B against two classical baselines on the planner's own graph: the $5$~m clearance grid, the same cost surface and edge weights, "
        "the hard $3.6$~m building clearance and the existing-road cells as goals. The Kou--Markowsky--Berman Steiner tree \\cite{kou1981steiner} (metric closure of the road network and the targets, minimum spanning tree, "
        "shortest-path expansion, second spanning tree and leaf pruning) is the standard 2-approximation for the same problem; the Euclidean minimum spanning tree joins the targets and the nearest road by straight lines. "
        "The comparison uses the house targets that Stage~B routed and counts unique grid-edge length without the short per-route connectors, so its lengths are slightly below the Stage~A and Stage~B lengths of the main "
        "results, which include the connectors and the facility routes. "
        f"Stage~A is {st['stA_rng'].replace('--', ' to ')}\\% longer than Stage~B, and the Kou Steiner tree is {st['kou_rng'].replace('--', ' to ')}\\% longer than Stage~B "
        f"(house targets; with the facilities added it is {sg(st['kou_fac']['damarakunta'])}\\%, {sg(st['kou_fac']['adilabad'])}\\%, {sg(st['kou_fac']['aswaraopeta'])}\\% and {sg(st['kou_fac']['alampur'])}\\% in Damarakunta, Adilabad, Aswaraopeta and Alampur). "
        f"Stage~B also has the lower cost-surface objective in {'all four' if st['obj_better'] == 4 else str(st['obj_better']) + ' of the four'} windows. On total length the two-stage plan therefore matches a classical Steiner approximation closely but does not beat it by a margin that would support a claim of optimality; "
        f"the claims of this paper rest on the zero-crossing corridors and the end-to-end open-data workflow, not on optimality. The Euclidean tree is {st['mst_rng'].replace('--', ' to ')}\\% shorter than Stage~B but is not a buildable plan: "
        f"it ignores slope, land cover and buildings and crosses a building with {ids(st['mstx'], str)} edges in Damarakunta, Adilabad, Aswaraopeta and Alampur, whereas Stage~A, Stage~B and the Kou tree have no crossing.")
    P["access"] = (
        f"\\textbf{{Accessibility.}} Table~\\ref{{tab:access}} counts the households and verified facilities that the plans connect. Before planning, {a.served_pct_baseline.min():.1f}\\% to {a.served_pct_baseline.max():.1f}\\% of the households in a window are "
        f"within the road-gap distance of a mapped road (lowest in Aswaraopeta, {a.loc['aswaraopeta', 'served_pct_baseline']:.1f}\\%); after Stage~B the served share is {a.served_pct_stage_B.min():.1f}\\% to {a.served_pct_stage_B.max():.1f}\\%, "
        f"the remainder being households without a clear lane or route ({ids({w: a.loc[w, 'unreachable'] for w in ORDER}, lambda x: str(int(x)))} in Damarakunta, Adilabad, Aswaraopeta and Alampur). "
        f"Verified facilities within the road-gap distance of a road rise from {int(a.fac_reached_baseline.loc['damarakunta'])}, {int(a.fac_reached_baseline.loc['adilabad'])}, {int(a.fac_reached_baseline.loc['aswaraopeta'])} and "
        f"{int(a.fac_reached_baseline.loc['alampur'])} to {int(a.fac_reached_stage_B.loc['damarakunta'])}, {int(a.fac_reached_stage_B.loc['adilabad'])}, {int(a.fac_reached_stage_B.loc['aswaraopeta'])} and {int(a.fac_reached_stage_B.loc['alampur'])} "
        f"of {int(a.facilities.loc['damarakunta'])}, {int(a.facilities.loc['adilabad'])}, {int(a.facilities.loc['aswaraopeta'])} and {int(a.facilities.loc['alampur'])}. "
        f"The median straight-line distance from a road-gap household to the nearest road falls from {a.road_dist_baseline_median_m.min():.1f}--{a.road_dist_baseline_median_m.max():.1f}~m to "
        f"{a.line_dist_stage_B_median_m.min():.1f}--{a.line_dist_stage_B_median_m.max():.1f}~m to the nearest road or planned route (measured from the building centroid, so some metres remain). "
        f"Sharing has a price in travel distance: the mean network path from the existing road to a household is longer on the Stage~B network than on the Stage~A routes in all four windows "
        f"({', '.join(f'{pa[w]:.1f} against {pb[w]:.1f}~m' for w in ORDER)} in Damarakunta, Adilabad, Aswaraopeta and Alampur), "
        "the detour that a shared trunk imposes on individual households.")
    P["error"] = (
        "\\textbf{Error propagation from the footprint inventory.} The omission and penalty sweeps of the planner (10~m soft-penalty grid, so lengths are comparable within the table but not with the $5$~m results) test how "
        "an incomplete or merged inventory changes the plan. In each scenario a share of the road-gap households is missing from the footprints: they are neither routed nor penalised, and the remaining targets are re-planned "
        f"(five random draws for the random scenarios). Table~\\ref{{tab:omit}} shows that with 20\\% of the road-gap households missing the Stage~B length falls by {ids(sw['dlen20'], lambda x: f'{abs(x):.1f}')}\\% "
        f"in Damarakunta, Adilabad, Aswaraopeta and Alampur, while on average {ids(sw['unserved20'], lambda x: f'{x:.1f}')} households are left unserved (including {ids({w: sw['g'](w, 'none (all footprints)', 'unserved_households') for w in ORDER}, lambda x: f'{x:.0f}')} that the planner cannot route even with the full inventory); the length per served household changes little "
        f"(from {ids(sw['mph0'], lambda x: f'{x:.1f}')}~m with the full inventory to {ids(sw['mph20'], lambda x: f'{x:.1f}')}~m). Network length is therefore close to proportional to the number of households served, and the "
        "risk of an incomplete inventory is not an over-sized network but unserved households that a plan sized from the footprints does not know about. Removing the smallest 25\\% of the road-gap footprints, which mimics "
        f"the loss of small buildings, leaves {ids(sw['unserved25'], lambda x: f'{x:.0f}')} households unserved and shortens the network by {ids(sw['dlen25'], lambda x: f'{abs(x):.1f}')}\\% in the same four windows. "
        f"The footprint penalty behaves as designed: without a penalty ($\\mu=1$) {ids({w: int(p(w, 1.0, 'routes_crossing')) for w in ORDER}, str)} routes cross a footprint on the $10$~m grid, with the main penalty ($\\mu=4$) "
        f"{ids({w: int(p(w, 4.0, 'routes_crossing')) for w in ORDER}, str)}, and with $\\mu=100$ {ids({w: int(p(w, 100.0, 'routes_crossing')) for w in ORDER}, str)}, at the cost of longer networks "
        f"({ids({w: f(p(w, 1.0, 'stage_B_len_km')) for w in ORDER}, str)}~km at $\\mu=1$ against {ids({w: f(p(w, 100.0, 'stage_B_len_km')) for w in ORDER}, str)}~km at $\\mu=100$); "
        "only the hard $3.6$~m clearance of the $5$~m grid removes the crossings completely.")
    return P
