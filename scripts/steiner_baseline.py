"""Task 4 - automated graph-routing baselines on the planner's own clearance graph (no manual input).

    python scripts/steiner_baseline.py                     # every paper window whose state_segmentation.pkl is on this machine
    python scripts/steiner_baseline.py --windows damarakunta alampur

Baselines, on exactly the same 5 m clearance grid, cost surface, hard 3.6 m building clearance and road-cell goals as Stage A / Stage B (src/multivillage/grid_graph.py):
  * Kou Steiner tree (Kou-Markowsky-Berman 1981): metric closure of {road root, targets} -> MST -> expand shortest paths -> MST of the union -> prune non-terminal leaves.
    Cost-metric shortest paths: it optimises the same objective as the planner and is a 2-approximation of the optimal Steiner tree.
  * Euclidean MST: straight-line minimum spanning tree over {road, targets}; ignores terrain and buildings (the naive planning baseline).
Targets = the targets Stage B routed (house phase = the paper's Stage A / B numbers; also house + facility). Outputs: validation/steiner_baseline.csv / .tex
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd
from scipy.sparse.csgraph import dijkstra, minimum_spanning_tree
from shapely.geometry import LineString, Point
from shapely.ops import nearest_points

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.multivillage import clearance as CL, grid_graph as GG  # noqa: E402


def _start_cell(world, r):
    return world.grid.idx_of(*r["net_geom"].coords[0])


def kou_steiner(Gc, Gl, root, terminals, batch=32):
    """-> (set of undirected edges (u, v), unconnected terminal list)."""
    K = [root] + list(dict.fromkeys(terminals))
    n = len(K)
    closure = np.full((n, n), np.inf)
    for i0 in range(0, n, batch):
        d = dijkstra(Gc, directed=True, indices=K[i0:i0 + batch])
        closure[i0:i0 + batch] = d[:, K]
    fin = np.where(np.isfinite(closure), closure, 0.0)
    fin = np.maximum(fin, fin.T)
    mst = minimum_spanning_tree(fin).tocoo()
    edges, preds = set(), {}
    for i, j in zip(mst.row, mst.col):
        if i not in preds:
            preds[i] = dijkstra(Gc, directed=True, indices=K[i], return_predecessors=True)[1]
        pr, v = preds[i], K[j]
        while v != K[i] and v >= 0:
            u = pr[v]
            if u < 0:
                break
            edges.add((min(u, v), max(u, v)))
            v = u
    H = nx.Graph()
    for u, v in edges:
        H.add_edge(int(u), int(v), weight=float(Gc[u, v]))
    T = nx.minimum_spanning_tree(H, weight="weight")
    keep = set(K)
    while True:                                                        # prune non-terminal leaves
        leaves = [x for x in T.nodes if T.degree(x) == 1 and x not in keep]
        if not leaves:
            break
        T.remove_nodes_from(leaves)
    comp = nx.node_connected_component(T, root) if root in T else {root}
    return {(min(u, v), max(u, v)) for u, v in T.edges}, [t for t in K[1:] if t not in comp]


def tree_metrics(Gc, Gl, root, isroad, edges) -> dict:
    ln = cost = 0.0
    for u, v in edges:
        if u == root or v == root or (isroad[u] and isroad[v]):
            continue
        ln += Gl[u, v]
        cost += Gc[u, v]
    return dict(len_m=ln, cost=cost)


def euclid_mst(pts, roads_u, fp, own_idx):
    """Straight-line MST over {road, targets}: road-target distance = distance to the nearest existing road line."""
    n = len(pts)
    D = np.zeros((n + 1, n + 1))
    for i in range(n):
        D[0, i + 1] = D[i + 1, 0] = max(pts[i].distance(roads_u), 1e-6)
        for j in range(i + 1, n):
            D[i + 1, j + 1] = D[j + 1, i + 1] = max(pts[i].distance(pts[j]), 1e-6)
    t = minimum_spanning_tree(D).tocoo()
    ln, cross, ncross = 0.0, 0.0, 0
    for i, j in zip(t.row, t.col):
        if i == 0 or j == 0:
            k = j if i == 0 else i
            a, b = pts[k - 1], nearest_points(roads_u, pts[k - 1])[0]
            owns = {own_idx[k - 1]}
        else:
            a, b = pts[i - 1], pts[j - 1]
            owns = {own_idx[i - 1], own_idx[j - 1]}
        seg = LineString([(a.x, a.y), (b.x, b.y)])
        ln += seg.length
        x = sum(seg.intersection(fp.geoms[q]).length for q in (int(q) for q in fp.tree.query(seg)) if q not in owns)
        if x > CL.CROSS_TOL_M:
            cross += x; ncross += 1
    return dict(len_m=ln, crossing_edges=ncross, len_in_footprints_m=cross)


def one_window(key: str, log=print) -> list:
    L = GG.load_window(key)
    if L is None:
        log(f"[{key}] SKIPPED: data/villages/{GG.WINDOWS[key]}/state_segmentation.pkl is not on this machine (the StrongDINOv2Seg state of this window lives on the owner's PC)")
        return []
    cfg, S, ddir, vid = L
    C = CL.compute_clearance(cfg, S, ddir, cache_path=ddir / "clearance_network_v1.pkl", log=lambda *a: None)
    world, fp = GG.build_world(cfg, S, ddir)
    Gc, Gl, root = GG.graph(world)
    isroad = np.zeros(Gc.shape[0], bool)
    isroad[list(world.road_cells)] = True
    roads_u = world.road_union
    rows = []
    for label, groups in (("houses", ("houses",)), ("houses + facilities", ("houses", "facilities"))):
        shared = [r for g in groups for r in C[g]["shared"]]
        ids = {r["target"] for r in shared}
        indep = [r for g in groups for r in C[g]["indep"] if r["target"] in ids]
        terms = [_start_cell(world, r) for r in shared]
        ok = [i for i, t in enumerate(terms) if t is not None]
        terms = [terms[i] for i in ok]
        shared = [shared[i] for i in ok]
        edges, unconn = kou_steiner(Gc, Gl, root, terms)
        km = tree_metrics(Gc, Gl, root, isroad, edges)
        sA = GG.edge_set_metrics([e for r in indep for e in r["edges"]])
        sB = GG.edge_set_metrics([e for r in shared for e in r["edges"]])
        conA = sum(r["start_snap_m"] + r["end_snap_m"] for r in indep)
        conB = sum(r["start_snap_m"] + r["end_snap_m"] for r in shared)
        pts = [Point(r["net_geom"].coords[0]) for r in shared]
        em = euclid_mst(pts, roads_u, fp, [r["own"] for r in shared])
        base = sB["unique_len_m"]
        vA = CL.verify(indep, fp)
        vB = CL.verify(shared, fp)
        def row(method, ln, cost, cross, extra=""):
            rows.append(dict(window=key, targets=label, n_targets=len(shared), method=method, unique_len_km=round(ln / 1000, 3), cost_rs_lakh=round(ln / 1000 * GG.RATE_LAKH_PER_KM, 1),
                             cost_surface_objective=(round(cost, 0) if cost is not None else ""), vs_stage_B_pct=round(100 * (ln - base) / base, 1), routes_or_edges_crossing_buildings=cross, note=extra))
        row("Stage A (independent least-cost)", sA["unique_len_m"], sA["unique_cost"], vA["routes_crossing"])
        row("Stage B (two-stage shared)", sB["unique_len_m"], sB["unique_cost"], vB["routes_crossing"])
        row("Kou Steiner tree (same grid)", km["len_m"], km["cost"], 0, f"{len(unconn)} unconnected" if unconn else "")
        row("Euclidean MST (straight lines)", em["len_m"], None, em["crossing_edges"], f"{em['len_in_footprints_m']:.0f} m inside other footprints")
        log(f"[{key}] {label}: Stage A {sA['unique_len_m']:.0f} m (+{conA:.0f} m connectors), Stage B {sB['unique_len_m']:.0f} m (+{conB:.0f}), Kou {km['len_m']:.0f} m, Euclid MST {em['len_m']:.0f} m")
    return rows


def latex(df: pd.DataFrame) -> str:
    d = df[df.targets == "houses"]
    out = ["\\begin{tabular}{llrrrr}", "\\hline", "Window & Method & Length (km) & Cost (Rs lakh) & vs Stage B (\\%) & Bldg.\\ crossings \\\\", "\\hline"]
    for w, g in d.groupby("window", sort=False):
        for i, r in enumerate(g.itertuples()):
            out.append(f"{w.capitalize() if i == 0 else ''} & {r.method} & {r.unique_len_km:.2f} & {r.cost_rs_lakh:.0f} & {r.vs_stage_B_pct:+.1f} & {r.routes_or_edges_crossing_buildings} \\\\")
        out.append("\\hline")
    out.append("\\end{tabular}")
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--windows", nargs="+", default=list(GG.WINDOWS), choices=list(GG.WINDOWS))
    a = ap.parse_args()
    rows = [r for k in a.windows for r in one_window(k)]
    if rows:
        GG.OUT.mkdir(parents=True, exist_ok=True)
        df = pd.DataFrame(rows)
        df.to_csv(GG.OUT / "steiner_baseline.csv", index=False, lineterminator="\n")
        (GG.OUT / "steiner_baseline.tex").write_text(latex(df))
        print(df.to_string(index=False))
        print("written", GG.OUT / "steiner_baseline.csv")


if __name__ == "__main__":
    main()
