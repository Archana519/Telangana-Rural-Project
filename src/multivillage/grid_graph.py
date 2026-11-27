"""The planner's clearance grid as an explicit sparse graph, for graph-theoretic baselines (Kou Steiner tree, MST) and network-distance metrics.

The graph is IDENTICAL to the one the Stage A / Stage B planner searches (scripts/plan_network_v2.py, Grid.search):
  * nodes  = passable cells of the 5 m clearance grid (footprints buffered by 3.6 m are hard-blocked), padded flat index (row+1)*W2 + col+1;
  * edges  = 8-neighbourhood, a diagonal step needs BOTH orthogonal neighbours passable (corner_cut=False);
  * weight = 0.5 * (cost[u] + cost[v]) * step_length (cost-surface units per metre x metre); length = step_length.
Existing road cells are the planner's goals: here they are joined to one virtual root node by an epsilon edge, so "connect to the existing network" = "connect to root".
"""
from __future__ import annotations

import numpy as np
from scipy import sparse

import pickle
from pathlib import Path

from . import acquire as A, clearance as CL, prepare as P

EPS = 1e-9
RATE_LAKH_PER_KM = 75.0     # owner-supplied, unverified PMGSY-based rate (sensitivity 60-90); same constant as the paper's cost column
WINDOWS = {"damarakunta": "damarakunta_open", "adilabad": "adilabad_urban_updated", "aswaraopeta": "aswaraopeta", "alampur": "alampur"}   # paper window -> village config id
OUT = Path(__file__).resolve().parents[2] / "DELIVERABLES_CONTRIBUTION_3_MULTI_VILLAGE" / "validation"


def load_window(key: str):
    """(cfg, state, data_dir, village_id) of the StrongDINOv2Seg run of one paper window, or None when its state_segmentation.pkl is not on this machine."""
    vid = WINDOWS[key]
    cfg = A.load_cfg(vid)
    ddir = A.data_dir(cfg)
    f = ddir / "state_segmentation.pkl"
    if not f.exists():
        return None
    return cfg, pickle.load(open(f, "rb")), ddir, vid


def build_world(cfg, S, ddir):
    """(ClearWorld, Footprints) for a window state S: same inputs as clearance.compute_clearance."""
    cell = S["cell"]
    prep = P.prepare_rasters(cfg, cell, ddir, log=lambda *a: None)
    cost, _ = P.cost_surface(cfg, prep, cell)
    fp = CL.Footprints(S["houses_all"])
    roads = list(S["layers"]["roads"].geometry.intersection(cell))
    return CL.ClearWorld(cost, prep["transform"], prep["shape"], roads, fp.geoms), fp


def graph(world):
    """-> (G_cost, G_len, root): symmetric csr matrices (cost and metre length) over padded cell indices plus a virtual root node = index n_cells."""
    g = world.grid
    n = len(g.cost)
    c = np.asarray(g.cost, float)
    ok = np.isfinite(c)
    idx = np.nonzero(ok)[0]
    us, vs, ls = [], [], []
    for o, s, oa, ob in g.pairs:
        v = idx + o
        keep = (v >= 0) & (v < n)
        u, v = idx[keep], v[keep]
        m = ok[v]
        if oa:
            m &= ok[u + oa] & ok[u + ob]
        u, v = u[m], v[m]
        us.append(u); vs.append(v); ls.append(np.full(len(u), s))
    u, v, L = np.concatenate(us), np.concatenate(vs), np.concatenate(ls)
    w = 0.5 * (c[u] + c[v]) * L
    root = n
    rc = np.array(sorted(world.road_cells), dtype=np.int64)
    isroad = np.zeros(n, bool)
    isroad[rc] = True
    both = isroad[u] & isroad[v]                      # existing road: travelling along it is free and is never counted as new construction (the planner stops at the first road cell)
    w, L = np.where(both, EPS, w), np.where(both, EPS, L)
    # the 8 offsets are symmetric, so every undirected edge is already present once in EACH direction; only the root edges are added both ways
    u2, v2 = np.concatenate([u, rc, np.full(len(rc), root)]), np.concatenate([v, np.full(len(rc), root), rc])
    w2, L2 = np.concatenate([w, np.full(2 * len(rc), EPS)]), np.concatenate([L, np.full(2 * len(rc), EPS)])
    N = n + 1
    mk = lambda x: sparse.csr_matrix((x, (u2, v2)), shape=(N, N))
    return mk(w2), mk(L2), root


def cell_of(world, xy) -> int | None:
    return world.grid.idx_of(xy[0], xy[1])


def edge_set_metrics(edges) -> dict:
    """Unique grid edges -> length (m) and cost; same counting as plan_network_v2.unique_edge_metrics without the per-route connectors."""
    ec = {}
    for e in edges:
        ec[(e[0], e[1])] = (e[2], e[3])
    return dict(unique_len_m=float(sum(v[0] for v in ec.values())), unique_cost=float(sum(v[1] for v in ec.values())), edges=len(ec))
