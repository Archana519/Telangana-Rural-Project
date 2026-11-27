"""Task 3 - accessibility and facility-connectivity metrics from the existing outputs (no new routing, no manual input).

    python scripts/accessibility_metrics.py [--windows damarakunta alampur ...]

Per window (needs data/villages/<id>/state_segmentation.pkl + clearance_network_v1.pkl, i.e. the paper's StrongDINOv2Seg run and its Stage A / Stage B routes):
  households   total, already within the road-gap distance of an existing road (baseline), road-gap households, routed by Stage A / Stage B, share served after;
  facilities   verified facilities (schools, colleges, health sub-centres/hospitals, anganwadis, government offices) within the road-gap distance of a road (baseline) and after A / B;
  distance     (a) straight-line distance from each road-gap household to the nearest existing road (baseline: mean / median / p90);
               (b) the same household's distance to the nearest road OR planned route after Stage A / Stage B (building-centroid based, so a few metres remain);
               (c) NETWORK path distance from the existing road to the household entrance along the planned lines: Stage A (own route) vs Stage B (shared network).
Outputs: validation/accessibility_summary.csv, accessibility_facilities.csv, accessibility_summary.tex
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd
from shapely.geometry import Point
from shapely.ops import unary_union

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.multivillage import clearance as CL, grid_graph as GG  # noqa: E402


def net_dist(world, routes) -> dict:
    """target id -> path length (m) from the existing road to the household/facility entrance along the union of `routes`' grid edges."""
    G = nx.Graph()
    for r in routes:
        for a, b, L, _ in r["edges"]:
            G.add_edge(a, b, length=L)
    roadn = [n for n in G.nodes if n in world.road_cells]
    for n in roadn:
        G.add_edge("root", n, length=0.0)
    if "root" not in G:
        return {}
    d = nx.single_source_dijkstra_path_length(G, "root", weight="length")
    out = {}
    for r in routes:
        s = world.grid.idx_of(*r["net_geom"].coords[0])
        if s in d:
            out[r["target"]] = d[s] + r["lane_m"] + r.get("end_snap_m", 0.0)
    return out


def stats(x) -> dict:
    x = np.asarray(list(x), float)
    return dict(mean=round(float(x.mean()), 1), median=round(float(np.median(x)), 1), p90=round(float(np.percentile(x, 90)), 1)) if len(x) else dict(mean=np.nan, median=np.nan, p90=np.nan)


def one_window(key: str, log=print):
    L = GG.load_window(key)
    if L is None:
        log(f"[{key}] SKIPPED: data/villages/{GG.WINDOWS[key]}/state_segmentation.pkl is not on this machine")
        return None
    cfg, S, ddir, vid = L
    C = CL.compute_clearance(cfg, S, ddir, cache_path=ddir / "clearance_network_v1.pkl", log=lambda *a: None)
    world, fp = GG.build_world(cfg, S, ddir)
    cell = S["cell"]
    roads_u = world.road_union
    thr = cfg["village"]["min_dist_to_road_m"]
    ha, gap, fac = S["houses_all"], S["gap"], S["fac"]
    Hs, Hi = C["houses"]["shared"], C["houses"]["indep"]
    Fs, Fi = C["facilities"]["shared"], C["facilities"]["indep"]
    n_all, n_gap = len(ha), len(gap)
    served0 = n_all - n_gap
    # (b) distance to the nearest road or planned line after A / B
    pts = {int(h): g.representative_point() for h, g in zip(gap.hid, gap.geometry)}
    def after(routes):
        u = unary_union([roads_u] + [r["geom"] for r in routes])
        return {h: p.distance(u) for h, p in pts.items()}
    dA, dB = after(Hi), after(Hs)
    nA, nB = net_dist(world, Hi), net_dist(world, Hs)
    # facilities
    fac = fac.copy()
    fac["dist_road_m"] = [g.distance(roads_u) for g in fac.geometry]
    fac["base"] = fac.dist_road_m <= thr
    fa, fb = {str(r["target"]) for r in Fi}, {str(r["target"]) for r in Fs}
    fac["fid_s"] = ["F:" + str(int(i)) for i in fac.fid]
    fac["A"] = fac.base | fac.fid_s.isin(fa)
    fac["B"] = fac.base | fac.fid_s.isin(fb)
    ftab = fac.groupby("facility_type").agg(facilities=("fid", "count"), reached_baseline=("base", "sum"), reached_stage_A=("A", "sum"), reached_stage_B=("B", "sum")).reset_index()
    ftab.insert(0, "window", key)
    base_d = stats(gap.dist_to_road_m)
    row = dict(window=key, households=n_all, served_baseline=served0, road_gap_households=n_gap, routed_stage_A=len(Hi), routed_stage_B=len(Hs),
               unreachable=len(C["houses"]["unreachable"]) + len(C["houses"]["fails"]),
               served_pct_baseline=round(100 * served0 / n_all, 1), served_pct_stage_B=round(100 * (served0 + len(Hs)) / n_all, 1),
               facilities=len(fac), fac_reached_baseline=int(fac.base.sum()), fac_reached_stage_A=int(fac.A.sum()), fac_reached_stage_B=int(fac.B.sum()),
               road_dist_baseline_mean_m=base_d["mean"], road_dist_baseline_median_m=base_d["median"], road_dist_baseline_p90_m=base_d["p90"],
               line_dist_stage_A_mean_m=stats(dA.values())["mean"], line_dist_stage_A_median_m=stats(dA.values())["median"],
               line_dist_stage_B_mean_m=stats(dB.values())["mean"], line_dist_stage_B_median_m=stats(dB.values())["median"],
               path_dist_stage_A_mean_m=stats(nA.values())["mean"], path_dist_stage_A_median_m=stats(nA.values())["median"],
               path_dist_stage_B_mean_m=stats(nB.values())["mean"], path_dist_stage_B_median_m=stats(nB.values())["median"])
    log(f"[{key}] households {n_all}: baseline served {served0}, gap {n_gap}, routed A {len(Hi)} / B {len(Hs)}; facilities {len(fac)}: baseline {int(fac.base.sum())}, A {int(fac.A.sum())}, B {int(fac.B.sum())}")
    return row, ftab


def latex(df: pd.DataFrame) -> str:
    out = ["\\begin{tabular}{lrrrrrr}", "\\hline",
           "Window & Households & Served (baseline) & Gap & Routed (B) & Facilities reached (base $\\rightarrow$ B) & Median road distance (m): baseline / A / B \\\\", "\\hline"]
    for r in df.itertuples():
        out.append(f"{r.window.capitalize()} & {r.households:,} & {r.served_baseline:,} & {r.road_gap_households:,} & {r.routed_stage_B:,} & {r.fac_reached_baseline}$\\rightarrow${r.fac_reached_stage_B} of {r.facilities} & "
                   f"{r.road_dist_baseline_median_m:.0f} / {r.line_dist_stage_A_median_m:.0f} / {r.line_dist_stage_B_median_m:.0f} \\\\")
    out += ["\\hline", "\\end{tabular}"]
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--windows", nargs="+", default=list(GG.WINDOWS), choices=list(GG.WINDOWS))
    a = ap.parse_args()
    res = [r for r in (one_window(k) for k in a.windows) if r]
    if not res:
        raise SystemExit("no window had its state_segmentation.pkl on this machine")
    GG.OUT.mkdir(parents=True, exist_ok=True)
    s = pd.DataFrame([r[0] for r in res])
    s.to_csv(GG.OUT / "accessibility_summary.csv", index=False, lineterminator="\n")
    pd.concat([r[1] for r in res]).to_csv(GG.OUT / "accessibility_facilities.csv", index=False, lineterminator="\n")
    (GG.OUT / "accessibility_summary.tex").write_text(latex(s))
    print(s.T.to_string(header=False))
    print(pd.concat([r[1] for r in res]).to_string(index=False))


if __name__ == "__main__":
    main()
