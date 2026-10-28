"""plan_network_v2.py - network-aware two-stage generate-and-select road-access planner (UNVERIFIED planning alternatives).

STAGE A (generate): for every eligible target (priority facilities + gap clusters) generate K least-cost
  alternatives to the REFERENCE ROADS on the planning grid (8-connected Dijkstra, corridor penalties for diversity).
STAGE B (select, network-aware): greedy benefit/marginal-cost selection. At every step the candidates of each
  unserved target are (a) its Stage-A alternatives and (b) a FRESH least-cost path to the CURRENT NETWORK =
  reference roads UNION already-selected proposed routes. A route that ends on a selected route is "attached";
  edges already in the selected network cost nothing again (shared-edge credit, each edge counted once).
  A final leaf-reroute pass lets a route be replaced when it becomes cheaper given the other routes.

OBJECTIVE (documented, heuristic - no optimality guarantee):
  maximise   sum_{t in S} w_t      subject to      UniqueCost(S) <= B   (B = infinity by default)
  UniqueCost(S) = sum over UNIQUE grid edges e in the union of selected routes of  0.5*(c_a+c_b)*len(e)
                + connector costs (target->first cell snap),   c = cost surface x soft multipliers.
  Greedy rule: pick the (target, route) maximising  w_t / marginal_unique_cost.  With B = infinity every feasible
  target is served and the result is a Steiner-forest-style heuristic that minimises unique network cost.
HARD constraints (route may never enter): invalid/non-positive cost cells, WorldCover water class, prohibited-area
  raster > 0, slope above the limit (when those layers are given).
SOFT constraints (cost multipliers, parameters not facts): WorldCover built-up multiplier, building-polygon multiplier
  (center-in-polygon rule). The cost surface itself already carries land-cover penalties; check data_check.json to
  avoid double counting.
BASELINES on the same targets and constraints: independent least-cost (each target to roads only) and straight line.
Connectivity is verified by geometry with a tolerance (never by exact coordinate equality).
Failures are reported with a reason; an impossible route is never reported as served.
"""
import argparse, hashlib, heapq, importlib.util, json, math, os, sys, time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from shapely.geometry import LineString, Point
from shapely.ops import nearest_points, unary_union

SQ2 = math.sqrt(2.0)
INF = float("inf")
ROOT = r"D:\Telangana_Rural_Project\Siddipet\Damarakunta"
CRS = "EPSG:32644"


# ====================================================================================== grid + search
class Grid:
    """Padded flat grid. cost[i] = INF means impassable. Cell (row,col) -> padded index (row+1)*W2 + col+1."""

    def __init__(self, cost, transform, hard=None, mult=None):
        if transform.b or transform.d:
            raise ValueError("rotated rasters are not supported")
        self.T, (self.H, self.W) = transform, cost.shape
        self.W2, self.res = self.W + 2, abs(transform.a)
        if abs(abs(transform.e) - self.res) > 1e-6 * self.res:
            raise ValueError("non-square cells are not supported")
        c = np.asarray(cost, float).copy()
        ok = np.isfinite(c) & (c > 0)
        c[~ok] = np.nan
        if mult is not None:
            c = c * mult
        if hard is not None:
            ok &= ~hard
        P = np.full((self.H + 2, self.W + 2), INF)
        P[1:-1, 1:-1] = np.where(ok, c, INF)
        self.pass_np = np.isfinite(P)
        self.cost = P.ravel().tolist()
        w2, r = self.W2, self.res
        self.pairs = tuple(zip((-1, 1, -w2, w2, -w2 - 1, -w2 + 1, w2 - 1, w2 + 1), (r, r, r, r) + (r * SQ2,) * 4))

    def rc(self, i):
        return divmod(i, self.W2)

    def xy(self, i):
        r, c = divmod(i, self.W2)
        return (self.T.c + (c - 0.5) * self.T.a, self.T.f + (r - 0.5) * self.T.e)

    def idx_of(self, x, y):
        col, row = int(math.floor((x - self.T.c) / self.T.a)), int(math.floor((y - self.T.f) / self.T.e))
        return (row + 1) * self.W2 + col + 1 if 0 <= row < self.H and 0 <= col < self.W else None

    def snap(self, x, y, max_m):
        """nearest PASSABLE cell to (x,y) within max_m -> (index, distance_m) or None."""
        i = self.idx_of(x, y)
        if i is None:
            return None
        if self.cost[i] < INF:
            cx, cy = self.xy(i)
            return i, math.hypot(cx - x, cy - y)
        r0, c0 = self.rc(i)
        k = int(max_m / self.res) + 1
        sub = self.pass_np[max(r0 - k, 0): r0 + k + 1, max(c0 - k, 0): c0 + k + 1]
        rr, cc = np.nonzero(sub)
        if len(rr) == 0:
            return None
        rr, cc = rr + max(r0 - k, 0), cc + max(c0 - k, 0)
        xs, ys = self.T.c + (cc - 0.5) * self.T.a, self.T.f + (rr - 0.5) * self.T.e
        d = np.hypot(xs - x, ys - y)
        j = int(np.argmin(d))
        return (int(rr[j]) * self.W2 + int(cc[j]), float(d[j])) if d[j] <= max_m else None

    def search(self, start, goals, pen=None, pen_mult=1.0, limit_m=None):
        """Least-cost path from start to the first goal cell popped. -> dict(cells) or str failure reason."""
        cost, pairs, W2 = self.cost, self.pairs, self.W2
        pen = pen or ()
        dist, prev, seen, heap, cut = {start: 0.0}, {start: -1}, set(), [(0.0, start)], False
        if limit_m:
            sr, sc = divmod(start, W2)
            lim2 = (limit_m / self.res) ** 2
        while heap:
            d, u = heapq.heappop(heap)
            if u in seen:
                continue
            seen.add(u)
            if u in goals:
                cells = [u]
                while prev[cells[-1]] != -1:
                    cells.append(prev[cells[-1]])
                return {"cells": cells[::-1]}
            if limit_m:
                r, c = divmod(u, W2)
                if (r - sr) ** 2 + (c - sc) ** 2 > lim2:
                    cut = True
                    continue
            cu = cost[u]
            for o, s in pairs:
                v = u + o
                cv = cost[v]
                if cv == INF or v in seen:
                    continue
                w = 0.5 * (cu + cv) * s
                if v in pen:
                    w *= pen_mult
                nd = d + w
                if nd < dist.get(v, INF):
                    dist[v], prev[v] = nd, u
                    heapq.heappush(heap, (nd, v))
        return "NO_PATH_WITHIN_SEARCH_LIMIT" if cut else "NO_PATH_BLOCKED_OR_DISCONNECTED"

    def edges(self, cells):
        out, W2, c = [], self.W2, self.cost
        for a, b in zip(cells, cells[1:]):
            L = self.res * (1.0 if abs(a - b) in (1, W2) else SQ2)
            out.append((min(a, b), max(a, b), L, 0.5 * (c[a] + c[b]) * L))
        return out

    def dilate(self, cells, radius_m):
        k, s = int(round(radius_m / self.res)), set()
        for i in cells:
            r, c = divmod(i, self.W2)
            for dr in range(-k, k + 1):
                for dc in range(-k, k + 1):
                    s.add((r + dr) * self.W2 + c + dc)
        return s


def make_route(grid, tid, start_pt, snap_m, res, mode, snap_target=None, tol_m=15.0):
    """Attach connectors + geometry. snap_target: shapely geometry of the network the path should end on."""
    cells = res["cells"]
    edges = grid.edges(cells)
    xy = [grid.xy(i) for i in cells]
    end_xy = Point(*xy[-1])
    end_snap, snap_pt = 0.0, None
    if snap_target is not None:
        snap_pt = nearest_points(end_xy, snap_target)[1]
        end_snap = float(end_xy.distance(snap_pt))
    coords = [(start_pt.x, start_pt.y)] + xy + ([(snap_pt.x, snap_pt.y)] if snap_pt is not None and end_snap > 1e-9 else [])
    dedup = [coords[0]] + [p for q, p in zip(coords, coords[1:]) if p != q]
    degenerate = len(dedup) < 2
    if degenerate:
        dedup = [dedup[0], (dedup[0][0] + 1e-3, dedup[0][1])]
    line = LineString(dedup)
    cost_path = sum(e[3] for e in edges)
    c0 = grid.cost[cells[0]]
    return dict(target=tid, mode=mode, cells=cells, edges=edges, geom=line, start_snap_m=round(snap_m, 2),
                end_snap_m=round(end_snap, 2), path_len_m=sum(e[2] for e in edges),
                own_len_m=sum(e[2] for e in edges) + snap_m + end_snap,
                cost=cost_path + (snap_m * c0 if c0 < INF else 0.0), end_cell=cells[-1],
                degenerate=degenerate, endpoint_ok=end_snap <= tol_m)


def cell_line(grid, cells):
    xy = [grid.xy(i) for i in cells]
    return LineString(xy * 2 if len(xy) == 1 else xy) if len(xy) > 1 else Point(*xy[0]).buffer(1e-3)


def gen_alternatives(grid, start, goals, k, corridor_m, corr_mults, max_overlap, limit_m):
    alts, pen, prev = [], set(), []
    for alt in range(1, k + 1):
        found = None
        for m in ((1.0,) if alt == 1 else corr_mults):
            r = grid.search(start, goals, pen=(pen if alt > 1 else None), pen_mult=m, limit_m=limit_m)
            if isinstance(r, str):
                if alt == 1:
                    return [], r
                break
            ov = max((len(set(r["cells"]) & s) / max(len(r["cells"]), 1) for s in prev), default=0.0)
            if alt > 1 and ov > max_overlap:
                continue
            found = r
            break
        if not found:
            break
        alts.append(found); prev.append(set(found["cells"])); pen |= grid.dilate(found["cells"], corridor_m)
    return alts, "OK"


# ====================================================================================== planner
def priority_weight(row, weights):
    text = (str(row.get("facility_type", "")) + " " + str(row.get("priority_group", "")) + " " + str(row.get("facility_name", ""))).lower()
    for key, w in weights.items():
        if key in text:
            return float(w), key
    return float(weights.get("_default", 1.0)), "_default"


DEFAULT_WEIGHTS = {"health": 4.0, "hospital": 4.0, "sub-centre": 4.0, "sub centre": 4.0, "phc": 4.0,
                   "school": 3.0, "zphs": 3.0, "mpps": 3.0, "anganwadi": 3.0, "aganwadi": 3.0, "anganwadi": 3.0,
                   "government": 2.0, "gov": 2.0, "panchayat": 2.0, "office": 2.0, "_default": 1.0}


def plan(grid, road_union, road_cells, targets, p, log=print):
    """targets: list of dict(id, pt(Point), weight, ...). Returns dict with plans, failures, baselines."""
    tol, limit = p["attach_tol_m"], p["max_search_m"]
    goals_road = set(road_cells)
    start, snapd, fails, alts = {}, {}, {}, {}
    for t in targets:
        s = grid.snap(t["pt"].x, t["pt"].y, p["snap_m"])
        if s is None:
            fails[t["id"]] = "NO_START_CELL_WITHIN_SNAP_DISTANCE"
            continue
        start[t["id"]], snapd[t["id"]] = s
        a, why = gen_alternatives(grid, s[0], goals_road, p["k"], p["corridor_m"], p["corridor_mults"], p["max_overlap"], limit)
        if not a:
            fails[t["id"]] = why
            continue
        alts[t["id"]] = [make_route(grid, t["id"], t["pt"], snapd[t["id"]], r, f"stageA_alt{n}", road_union, tol) for n, r in enumerate(a, 1)]
    tmap = {t["id"]: t for t in targets}

    # ---- independent baseline: alternative 1 of every target, roads only
    indep = {tid: a[0] for tid, a in alts.items()}

    # ---- Stage B: network-aware greedy with fresh attachment candidates
    sel, ecount, owner, deps = {}, Counter(), {}, defaultdict(set)

    def goals_now(excl=None):
        g = set(goals_road)
        g |= {c for c, o in owner.items() if o != excl}
        return g

    def sel_geom(excl=None):
        ls = [cell_line(grid, r["cells"]) for tid, r in sel.items() if tid != excl]
        return unary_union(ls) if ls else None

    def marginal(r, ec):
        m = sum(e[3] for e in r["edges"] if ec.get(e[:2], 0) == 0)
        return m + r["start_snap_m"] * (grid.cost[r["cells"][0]] if grid.cost[r["cells"][0]] < INF else 0.0)

    def attach_candidate(tid, excl=None):
        r = grid.search(start[tid], goals_now(excl), limit_m=limit)
        if isinstance(r, str):
            return None
        end = r["cells"][-1]
        net = None
        if end in goals_road:
            net = road_union
        else:
            o = owner.get(end)
            net = cell_line(grid, sel[o]["cells"]) if o in sel else None
        rt = make_route(grid, tid, tmap[tid]["pt"], snapd[tid], r, "attach_network", net, tol)
        return rt

    def attach_to(r, excl=None):
        e = r["end_cell"]
        if e in goals_road:
            return "ROAD"
        o = owner.get(e)
        return o if (o is not None and o != r["target"]) else "ROAD"

    def register(r):
        sel[r["target"]] = r
        for e in r["edges"]:
            ecount[e[:2]] += 1
        for c in r["cells"]:
            if c not in goals_road and c not in owner:
                owner[c] = r["target"]
        r["attach_to"] = attach_to(r)
        if r["attach_to"] != "ROAD":
            deps[r["attach_to"]].add(r["target"])

    unserved = sorted(alts)
    while unserved:
        best = None
        for tid in unserved:
            cands = list(alts[tid])
            if sel:                                           # fresh attachment to roads UNION selected routes
                c = attach_candidate(tid)
                if c is not None:
                    cands.append(c)
            for r in cands:
                if not r["endpoint_ok"]:
                    continue
                m = marginal(r, ecount)
                score = tmap[tid]["weight"] / max(m, 1e-9)
                key = (-score, m, tid, r["mode"])
                if best is None or key < best[0]:
                    best = (key, tid, r, m)
        if best is None:
            for tid in unserved:
                fails[tid] = "ENDPOINT_SNAP_EXCEEDS_TOLERANCE"
            break
        _, tid, r, m = best
        if p["budget"] is not None and sum(x["cost"] for x in []) + m > 1e300:
            break
        register(r)
        r["marginal_cost_when_added"] = round(m, 1)
        unserved.remove(tid)

    # ---- leaf re-route passes (a route that nothing attaches to may be replaced if cheaper given the others)
    changed = 0
    for _ in range(p["passes"]):
        improved = False
        for tid in sorted(sel):
            if deps.get(tid):
                continue
            old = sel[tid]
            for e in old["edges"]:
                ecount[e[:2]] -= 1
            old_owner = {c for c, o in owner.items() if o == tid}
            for c in old_owner:
                del owner[c]
            cur = marginal(old, ecount)
            cand = [attach_candidate(tid, excl=tid)] + list(alts[tid])
            cand = [c for c in cand if c is not None and c["endpoint_ok"]]
            nb = min(cand, key=lambda r: (marginal(r, ecount), tid, r["mode"])) if cand else None
            if nb is not None and marginal(nb, ecount) < cur - 1e-6:
                if old["attach_to"] != "ROAD":
                    deps[old["attach_to"]].discard(tid)
                register(nb); nb["marginal_cost_when_added"] = round(marginal(nb, ecount), 1)
                improved = True; changed += 1
            else:
                for e in old["edges"]:
                    ecount[e[:2]] += 1
                for c in old_owner:
                    owner[c] = tid
        if not improved:
            break
    for tid, r in sel.items():
        r["attach_to"] = attach_to(r)

    # ---- straight-line baseline (same targets, same hard constraints)
    straight = {}
    for t in targets:
        q = nearest_points(t["pt"], road_union)[1]
        ln = LineString([(t["pt"].x, t["pt"].y), (q.x, q.y)])
        n = max(2, int(ln.length / (grid.res / 2)) + 1)
        bad = 0
        for f in np.linspace(0, 1, n):
            pt = ln.interpolate(f, normalized=True)
            i = grid.idx_of(pt.x, pt.y)
            if i is None or grid.cost[i] == INF:
                bad += 1
        straight[t["id"]] = dict(target=t["id"], geom=ln, own_len_m=float(ln.length), bad_samples=bad, feasible=bad == 0)
    return dict(alts=alts, indep=indep, sel=sel, fails=fails, straight=straight, start=start, snap=snapd,
                reroutes_changed=changed)


# ====================================================================================== verification + metrics
def verify_network(sel, road_union, grid, tol):
    """Geometry-based: each route's end must be within tol of the network it declares; chain must reach the roads."""
    out, geoms = {}, {t: cell_line(grid, r["cells"]) for t, r in sel.items()}
    for t, r in sel.items():
        end = Point(*grid.xy(r["end_cell"]))
        net = road_union if r["attach_to"] == "ROAD" else geoms.get(r["attach_to"])
        d = float(end.distance(net)) if net is not None else INF
        # final point of the drawn geometry must also touch the declared network
        gend = Point(r["geom"].coords[-1])
        dg = float(gend.distance(net)) if net is not None else INF
        out[t] = dict(endpoint_dist_m=round(d, 2), drawn_end_dist_m=round(dg, 2), ok_local=bool(d <= tol and dg <= tol))
    for t in sel:
        seen, cur, ok = set(), t, True
        while True:
            if cur in seen:
                ok = False; break
            seen.add(cur)
            a = sel[cur]["attach_to"]
            if a == "ROAD":
                break
            if a not in sel:
                ok = False; break
            cur = a
        out[t]["connected_to_roads"] = bool(ok and out[t]["ok_local"] and all(out[x]["ok_local"] for x in seen))
        out[t]["chain_len"] = len(seen)
    return out


def unique_edge_metrics(routes):
    ec = {}
    conn = 0.0
    for r in routes:
        conn += r["start_snap_m"] + r["end_snap_m"]
        for e in r["edges"]:
            ec[e[:2]] = (e[2], e[3])
    return dict(unique_len_m=sum(v[0] for v in ec.values()) + conn, unique_cost=sum(v[1] for v in ec.values()),
                total_len_m=sum(r["own_len_m"] for r in routes), total_cost=sum(r["cost"] for r in routes))


def summarise(name, routes, tmap, nall, feasible_straight=None):
    ts = [tmap[r["target"]] for r in routes]
    m = unique_edge_metrics(routes) if routes and "edges" in routes[0] else None
    if m is None:                                         # straight lines: geometric union
        u = unary_union([r["geom"] for r in routes]).length if routes else 0.0
        m = dict(unique_len_m=u, unique_cost=float("nan"), total_len_m=sum(r["own_len_m"] for r in routes), total_cost=float("nan"))
    return dict(plan=name, targets_routed=len(routes), targets_total=nall, total_len_m=round(m["total_len_m"], 1),
                unique_len_m=round(m["unique_len_m"], 1), shared_len_m=round(m["total_len_m"] - m["unique_len_m"], 1),
                unique_cost=None if math.isnan(m["unique_cost"]) else round(m["unique_cost"], 1),
                weighted_benefit=round(sum(t["weight"] for t in ts), 2),
                facilities_served=sum(1 for t in ts if t["kind"] == "FACILITY"),
                cluster_buildings_served=sum(t.get("n_buildings", 0) for t in ts if t["kind"] == "CLUSTER"),
                infeasible_routes=(sum(1 for r in routes if not r["feasible"]) if feasible_straight else 0))


# ====================================================================================== I/O
def sha(p, blk=1 << 20):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(blk), b""):
            h.update(b)
    return h.hexdigest()


def jsonable(o):
    if isinstance(o, dict):
        return {str(k): jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple, set)):
        return [jsonable(x) for x in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return None if np.isnan(o) else float(o)
    if isinstance(o, float) and (math.isnan(o) or math.isinf(o)):
        return None
    return o


def main():
    import rasterio, geopandas as gpd, pandas as pd
    from rasterio.features import rasterize, shapes
    from shapely.geometry import shape as shp
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    d = lambda *x: os.path.join(ROOT, *x)
    ap.add_argument("--access-gpkg", default=d("results", "v8_instances", "access", "access_assessment.gpkg"))
    ap.add_argument("--roads", default=d("reference", "tgrac_road_network.gpkg"))
    ap.add_argument("--cost", default=d("aligned", "damarakunta_cost_surface_10m.tif"))
    ap.add_argument("--worldcover", default=d("aligned", "damarakunta_worldcover_10m.tif"))
    ap.add_argument("--blocked", default=None, help="prohibited-area raster (>0 = forbidden), same grid as cost")
    ap.add_argument("--slope", default=None)
    ap.add_argument("--slope-limit-deg", type=float, default=None)
    ap.add_argument("--v4-script", default=r"D:\Telangana_Rural_Project\scripts\reconstruct_damarakunta_routes_v4.py",
                    help="imported (not run) only to read its BLOCKED/SLOPE paths and class constants; '' to skip")
    ap.add_argument("--water-class", type=int, default=None)
    ap.add_argument("--builtup-class", type=int, default=None)
    ap.add_argument("--buildings", default=d("results", "v8_instances", "buildings_v8_full.gpkg"))
    ap.add_argument("--buildings-layer", default="buildings")
    ap.add_argument("--raster", default=d("aligned", "damarakunta_esri_highres_mosaic_0p6m.tif"), help="only for the map background")
    ap.add_argument("--out-root", default=d("results", "planning_experiments", "network_v2"))
    ap.add_argument("--tag", default="run1")
    ap.add_argument("--k", type=int, default=3, help="Stage-A alternatives per target")
    ap.add_argument("--corridor-m", type=float, default=20.0)
    ap.add_argument("--corridor-mults", type=float, nargs="+", default=[3.0, 8.0])
    ap.add_argument("--max-overlap", type=float, default=0.8)
    ap.add_argument("--max-search-m", type=float, default=1500.0)
    ap.add_argument("--snap-m", type=float, default=30.0)
    ap.add_argument("--attach-tol-m", type=float, default=15.0, help="endpoint must be within this of the network it attaches to")
    ap.add_argument("--builtup-mult", type=float, default=1.0, help="soft multiplier on WorldCover built-up cells (1 = off; see data_check)")
    ap.add_argument("--building-mult", type=float, default=4.0, help="soft multiplier on cells whose CENTRE lies in a building polygon (1 = off)")
    ap.add_argument("--building-quality", default="PLAUSIBLE,REVIEW,UNRESOLVED_MERGE")
    ap.add_argument("--passes", type=int, default=2)
    ap.add_argument("--budget", type=float, default=None, help="reserved: unique-cost budget (not enforced in this version)")
    ap.add_argument("--weights-json", default=None, help="JSON {keyword: weight} replacing the default priority weights")
    ap.add_argument("--cluster-weight-per-building", type=float, default=0.25)
    ap.add_argument("--unverified-keywords", default="anganwadi,aganwadi,sub-centre,sub centre,subcentre")
    ap.add_argument("--include-nongap-clusters", action="store_true")
    ap.add_argument("--no-map", action="store_true")
    a = ap.parse_args()

    out = Path(a.out_root) / a.tag
    if out.exists() and any(out.iterdir()):
        sys.exit(f"{out} already has files; choose a new --tag (nothing is overwritten)")
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    notes = []

    # ---- optional import of V4 constants (never run)
    v4 = None
    if a.v4_script and os.path.exists(a.v4_script):
        try:
            spec = importlib.util.spec_from_file_location("v4mod", a.v4_script)
            v4 = importlib.util.module_from_spec(spec); spec.loader.exec_module(v4)
        except Exception as e:
            notes.append(f"V4 script could not be imported ({e}); blocked/slope layers only from CLI")
    g = lambda n, default=None: getattr(v4, n, default) if v4 else default
    blocked_p = a.blocked or (str(g("BLOCKED_PATH")) if g("BLOCKED_PATH") else None)
    slope_p = a.slope or (str(g("SLOPE_PATH")) if g("SLOPE_PATH") else None)
    slope_lim = a.slope_limit_deg if a.slope_limit_deg is not None else g("SLOPE_LIMIT_DEG")
    water_c = a.water_class if a.water_class is not None else g("WATER_CLASS", 80)
    built_c = a.builtup_class if a.builtup_class is not None else g("BUILTUP_CLASS", 50)

    # ---- rasters
    def read(path):
        with rasterio.open(path) as s:
            arr = s.read(1).astype(float)
            if s.nodata is not None:
                arr[arr == s.nodata] = np.nan
            return arr, s.transform, s.crs
    cost, T, crs = read(a.cost)
    if crs is None or crs.to_epsg() != 32644:
        sys.exit(f"cost raster CRS is {crs}, expected EPSG:32644")
    H, W = cost.shape
    hard = np.zeros((H, W), bool)
    kinds = np.zeros((H, W), np.uint8)               # 1 water, 2 prohibited, 3 slope, 4 invalid cost
    check = {"cost_raster": dict(path=a.cost, shape=[H, W], res=abs(T.a), invalid_share=float((~(np.isfinite(cost) & (cost > 0))).mean()),
                                 percentiles_5_50_95=[float(x) for x in np.nanpercentile(cost[np.isfinite(cost) & (cost > 0)], [5, 50, 95])])}
    world = None
    if a.worldcover and os.path.exists(a.worldcover):
        w, Tw, _ = read(a.worldcover)
        if w.shape == cost.shape and Tw.almost_equals(T):
            world = w
            hard_w = world == water_c
            kinds[hard_w] = 1; hard |= hard_w
            cls, cnt = np.unique(world[np.isfinite(world)].astype(int), return_counts=True)
            check["worldcover"] = {int(c): dict(cells=int(n), mean_cost=float(np.nanmean(np.where(world == c, np.where(cost > 0, cost, np.nan), np.nan))))
                                   for c, n in zip(cls, cnt)}
        else:
            notes.append("WorldCover grid differs from the cost grid: water hard-constraint NOT applied")
    else:
        notes.append("WorldCover not available: water hard-constraint NOT applied")
    for nm, pth, thr in (("prohibited", blocked_p, None), ("slope", slope_p, slope_lim)):
        if pth and os.path.exists(pth) and not (nm == "slope" and thr is None):
            arr, Ta, _ = read(pth)
            if arr.shape != cost.shape:
                notes.append(f"{nm} raster grid differs: NOT applied"); continue
            m = (np.nan_to_num(arr, nan=0) > 0) if nm == "prohibited" else (np.nan_to_num(arr, nan=0) > thr)
            kinds[m & (kinds == 0)] = 2 if nm == "prohibited" else 3; hard |= m
            check[nm] = dict(path=pth, forbidden_share=float(m.mean()))
        else:
            notes.append(f"{nm} layer not applied (path/limit unavailable): PROHIBITED/STEEP AREAS MAY NOT BE RESPECTED" if nm == "prohibited" else f"{nm} layer not applied")
    inval = ~(np.isfinite(cost) & (cost > 0))
    kinds[inval & (kinds == 0)] = 4

    mult = np.ones((H, W))
    if world is not None and a.builtup_mult != 1.0:
        mult[world == built_c] *= a.builtup_mult
    bld = None
    if a.buildings and os.path.exists(a.buildings) and a.building_mult != 1.0:
        bld = gpd.read_file(a.buildings, layer=a.buildings_layer).to_crs(CRS)
        keep = [x.strip() for x in a.building_quality.split(",")]
        if "quality_class" in bld.columns:
            bld = bld[bld.quality_class.isin(keep)]
        bm = rasterize([(x, 1) for x in bld.geometry], out_shape=(H, W), transform=T, fill=0, all_touched=False, dtype="uint8").astype(bool)
        mult[bm] *= a.building_mult
        check["building_cells_penalised"] = int(bm.sum())
    grid = Grid(cost, T, hard=hard, mult=mult)

    # ---- roads
    roads = gpd.read_file(a.roads).to_crs(CRS)
    roads = roads[roads.geometry.notna() & ~roads.geometry.is_empty]
    road_union = roads.geometry.union_all()
    rr = rasterize([(x, 1) for x in roads.geometry], out_shape=(H, W), transform=T, fill=0, all_touched=True, dtype="uint8").astype(bool)
    pr = grid.pass_np[1:-1, 1:-1]
    check["road_cells"] = dict(total=int(rr.sum()), passable=int((rr & pr).sum()), dropped_impassable=int((rr & ~pr).sum()))
    rows, cols = np.nonzero(rr & pr)
    road_cells = set(((rows + 1) * grid.W2 + cols + 1).tolist())
    if not road_cells:
        sys.exit("no passable road cells: cannot plan")

    # ---- targets from the access assessment
    weights = json.loads(a.weights_json) if a.weights_json else DEFAULT_WEIGHTS
    unv = [x.strip().lower() for x in a.unverified_keywords.split(",") if x.strip()]
    fac = gpd.read_file(a.access_gpkg, layer="facility_access").to_crs(CRS)
    cl = gpd.read_file(a.access_gpkg, layer="clusters").to_crs(CRS)
    cand = gpd.read_file(a.access_gpkg, layer="candidate_access").to_crs(CRS)
    for nm, df, req in (("facility_access", fac, ["facility_id", "facility_name", "facility_type"]),
                        ("clusters", cl, ["cluster_id", "gap_flag", "n_candidates"]),
                        ("candidate_access", cand, ["cluster_id", "dist_to_ref_road_m"])):
        miss = [c for c in req if c not in df.columns]
        if miss:
            sys.exit(f"layer {nm} lacks columns {miss}; has {list(df.columns)}")
    targets = []
    for _, f in fac.iterrows():
        w, key = priority_weight(f, weights)
        txt = (str(f.facility_name) + " " + str(f.facility_type)).lower()
        targets.append(dict(id="F:" + str(f.facility_id), kind="FACILITY", name=str(f.facility_name), ftype=str(f.facility_type),
                            pt=f.geometry, weight=w, weight_rule=key, n_buildings=0, n_unresolved=0,
                            coord_status="UNVERIFIED_FLAGGED" if any(k in txt for k in unv) else "SOURCE_LAYER_NOT_INDEPENDENTLY_VERIFIED"))
    gl = cl[cl.gap_flag.astype(str).str.lower().isin(["true", "1"])] if not a.include_nongap_clusters else cl
    for _, c in gl.iterrows():
        mem = cand[cand.cluster_id == c.cluster_id]
        if mem.empty:
            continue
        b = mem.loc[mem.dist_to_ref_road_m.idxmin()]
        nb = int(c.n_candidates)
        targets.append(dict(id=f"C{int(c.cluster_id)}", kind="CLUSTER", name="gap cluster (model-derived, unverified)", ftype="",
                            pt=b.geometry.representative_point(), weight=1.0 + a.cluster_weight_per_building * (nb - 1), weight_rule="cluster",
                            n_buildings=nb, n_unresolved=int(c.get("n_unresolved_merge", 0) or 0), coord_status="MODEL_DERIVED"))
    tmap = {t["id"]: t for t in targets}
    check["targets"] = dict(facilities=sum(t["kind"] == "FACILITY" for t in targets), clusters=sum(t["kind"] == "CLUSTER" for t in targets))
    print("DATA CHECK"); print(json.dumps(jsonable(check), indent=1)[:3500])
    for n in notes:
        print("NOTE:", n)
    print("\nTargets (weights are ordinal DESIGN parameters, see --weights-json):")
    for t in targets:
        print(f"  {t['id']:<8} {t['kind']:<9} w={t['weight']:<5} rule={t['weight_rule']:<10} bldgs={t['n_buildings']:<3} {t['coord_status']:<42} {t['name']}")

    P = dict(attach_tol_m=a.attach_tol_m, max_search_m=a.max_search_m, snap_m=a.snap_m, k=a.k, corridor_m=a.corridor_m,
             corridor_mults=a.corridor_mults, max_overlap=a.max_overlap, passes=a.passes, budget=a.budget)
    res = plan(grid, road_union, road_cells, targets, P)
    sel, indep, fails, straight = res["sel"], res["indep"], res["fails"], res["straight"]
    ver = verify_network(sel, road_union, grid, a.attach_tol_m)
    for t, r in sel.items():
        r.update(ver[t])

    # ---- tables
    rows = []
    for t in targets:
        tid = t["id"]
        r, i, s = sel.get(tid), indep.get(tid), straight[tid]
        euclid = float(t["pt"].distance(road_union))
        rows.append(dict(target=tid, kind=t["kind"], name=t["name"], weight=t["weight"], buildings=t["n_buildings"], unresolved_in_cluster=t["n_unresolved"],
                         coord_status=t["coord_status"], euclid_to_road_m=round(euclid, 1),
                         status="SERVED" if (r and r["connected_to_roads"]) else ("FAILED" if tid in fails or r is None else "ATTACHMENT_NOT_VERIFIED"),
                         failure_reason=fails.get(tid, "" if r else "NOT_SELECTED"),
                         mode=r["mode"] if r else "", attach_to=r["attach_to"] if r else "", route_len_m=round(r["own_len_m"], 1) if r else None,
                         route_cost=round(r["cost"], 1) if r else None, marginal_cost=r.get("marginal_cost_when_added") if r else None,
                         endpoint_dist_m=r["endpoint_dist_m"] if r else None, connected_to_roads=r["connected_to_roads"] if r else False,
                         indep_len_m=round(i["own_len_m"], 1) if i else None, straight_len_m=round(s["own_len_m"], 1),
                         straight_feasible=s["feasible"], detour_ratio=round(r["own_len_m"] / max(euclid, 1e-9), 2) if r else None,
                         connectivity_gain=("1 priority facility" if t["kind"] == "FACILITY" else f"{t['n_buildings']} model-derived building polygons")))
    rt = pd.DataFrame(rows)
    sel_list = [r for r in sel.values() if r["connected_to_roads"]]
    ind_list = list(indep.values())
    str_list = [dict(target=k, **{kk: vv for kk, vv in v.items() if kk != "target"}) for k, v in straight.items()]
    metrics = pd.DataFrame([summarise("network_aware", sel_list, tmap, len(targets)),
                            summarise("independent_least_cost", ind_list, tmap, len(targets)),
                            summarise("straight_line", str_list, tmap, len(targets), feasible_straight=True)])
    na, ic = metrics.iloc[0], metrics.iloc[1]
    attached = [t for t, r in sel.items() if r["attach_to"] != "ROAD"]
    differs = [t for t, r in sel.items() if t in indep and r["cells"] != indep[t]["cells"]]
    claim = dict(targets_attached_to_other_selected_routes=attached, targets_with_route_different_from_independent=differs,
                 unique_len_network_aware_m=float(na.unique_len_m), unique_len_independent_m=float(ic.unique_len_m),
                 unique_len_reduction_m=round(float(ic.unique_len_m - na.unique_len_m), 1),
                 unique_len_reduction_pct=round(100 * float(ic.unique_len_m - na.unique_len_m) / max(float(ic.unique_len_m), 1e-9), 2),
                 reroutes_changed=res["reroutes_changed"],
                 interpretation=("Network attachment changed the selection and reduced unique network length on THIS target set."
                                 if attached and na.unique_len_m < ic.unique_len_m - 1e-6 else
                                 "No evidence of benefit on this target set: network-aware selection did not reduce unique length versus independent least-cost routing."))
    print("\nTARGET TABLE"); print(rt[["target", "kind", "weight", "status", "failure_reason", "mode", "attach_to", "route_len_m", "indep_len_m", "straight_len_m", "straight_feasible", "endpoint_dist_m"]].to_string(index=False))
    print("\nPLAN COMPARISON (same targets, same hard constraints)"); print(metrics.to_string(index=False))
    print("\nC2 CHECK:", json.dumps(jsonable(claim), indent=1))

    # ---- GIS outputs
    gp = out / "network_v2.gpkg"
    tg = gpd.GeoDataFrame([{k: v for k, v in t.items() if k != "pt"} | {"geometry": t["pt"], "building_status": "UNVERIFIED_MODEL_PREDICTION"} for t in targets], crs=CRS)
    tg.to_file(gp, layer="targets", driver="GPKG")
    def rl(routes, extra=lambda r: {}):
        return gpd.GeoDataFrame([dict(target=r["target"], mode=r.get("mode", "straight"), length_m=round(r["own_len_m"], 1), cost=r.get("cost"),
                                      attach_to=r.get("attach_to", ""), route_status="UNVERIFIED_PLANNING_ALTERNATIVE_NOT_A_ROAD", geometry=r["geom"], **extra(r)) for r in routes], crs=CRS)
    if sel_list: rl(sel_list, lambda r: dict(endpoint_dist_m=r["endpoint_dist_m"], connected=r["connected_to_roads"])).to_file(gp, layer="routes_network_aware", driver="GPKG")
    if ind_list: rl(ind_list).to_file(gp, layer="routes_independent", driver="GPKG")
    rl(str_list, lambda r: dict(feasible=r["feasible"])).to_file(gp, layer="routes_straight_line", driver="GPKG")
    allalt = [r for tid in res["alts"] for r in res["alts"][tid]]
    if allalt: rl(allalt).to_file(gp, layer="stageA_alternatives", driver="GPKG")
    recs = []
    for code, nm in ((1, "water"), (2, "prohibited"), (3, "steep"), (4, "invalid_cost")):
        m = (kinds == code).astype(np.uint8)
        if m.any():
            for geom, v in shapes(m, mask=m.astype(bool), transform=T):
                recs.append(dict(constraint=nm, kind="HARD", geometry=shp(geom).simplify(T.a * 0.25)))
    if recs: gpd.GeoDataFrame(recs, crs=CRS).to_file(gp, layer="constraints_hard", driver="GPKG")
    rt.to_csv(out / "target_table.csv", index=False); metrics.to_csv(out / "plan_comparison.csv", index=False)
    summary = dict(version="plan_network_v2", village_crs=CRS, run=dict(tag=a.tag, seconds=round(time.time() - t0, 1)), params=vars(a),
                   hard_constraints=["cost nodata/<=0", f"WorldCover class {water_c} (water)", "prohibited raster >0 (if provided)", "slope > limit (if provided)"],
                   soft_constraints=dict(builtup_multiplier=a.builtup_mult, building_multiplier=a.building_mult, cost_surface="already contains land-cover penalties"),
                   data_check=check, notes=notes, c2_check=claim, plan_comparison=metrics.to_dict("records"),
                   failed_targets={k: v for k, v in fails.items()},
                   inputs={k: sha(v) for k, v in dict(access=a.access_gpkg, roads=a.roads, cost=a.cost).items() if os.path.exists(v)},
                   caveat="All outputs are unverified planning alternatives from model-derived building polygons and a 10 m raster; not verified roads, not construction-ready.")
    (out / "summary.json").write_text(json.dumps(jsonable(summary), indent=2), encoding="utf-8")
    (out / "data_check.json").write_text(json.dumps(jsonable(check), indent=2), encoding="utf-8")
    print(f"\nWrote: {gp}\n       {out / 'target_table.csv'}\n       {out / 'plan_comparison.csv'}\n       {out / 'summary.json'}")

    # ---- map
    if not a.no_map:
        try:
            import matplotlib; matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            geoms = [t["pt"] for t in targets] + [r["geom"] for r in sel_list]
            bb = unary_union(geoms).bounds
            pad = 250
            x0, y0, x1, y1 = bb[0] - pad, bb[1] - pad, bb[2] + pad, bb[3] + pad
            fig, ax = plt.subplots(figsize=(11, 11 * (y1 - y0) / (x1 - x0)))
            if a.raster and os.path.exists(a.raster):
                with rasterio.open(a.raster) as s:
                    from rasterio.windows import from_bounds
                    win = from_bounds(x0, y0, x1, y1, s.transform).round_offsets().round_lengths()
                    ff = max(1, int(max(win.width, win.height) / 1600))
                    img = s.read([1, 2, 3], window=win, out_shape=(3, max(1, int(win.height // ff)), max(1, int(win.width // ff)))).transpose(1, 2, 0)
                    from rasterio.windows import bounds as wb
                    l, b, r_, t_ = wb(win, s.transform)
                ax.imshow(img, extent=(l, r_, b, t_), alpha=0.8)
            if recs:
                cg = gpd.GeoDataFrame(recs, crs=CRS).cx[x0:x1, y0:y1]
                if len(cg): cg.plot(ax=ax, color="deepskyblue", alpha=0.45, linewidth=0)
            roads.cx[x0:x1, y0:y1].plot(ax=ax, color="white", linewidth=1.6)
            if ind_list:
                for r in ind_list: ax.plot(*r["geom"].xy, color="orange", linewidth=1.2, linestyle="--")
            for r in sel_list: ax.plot(*r["geom"].xy, color="red", linewidth=2.4)
            for t in targets:
                ax.plot(t["pt"].x, t["pt"].y, "o" if t["kind"] == "FACILITY" else "s", color="lime" if t["kind"] == "FACILITY" else "yellow",
                        markeredgecolor="black", markersize=9)
                ax.annotate(t["id"], (t["pt"].x, t["pt"].y), color="white", fontsize=8, xytext=(5, 5), textcoords="offset points")
            ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_axis_off()
            ax.set_title("white = TGRAC reference roads | red = network-aware plan | orange dashed = independent least-cost | blue = hard constraints\n"
                         "UNVERIFIED planning alternatives, not roads", fontsize=9)
            fig.savefig(out / "network_plan_map.png", dpi=110, bbox_inches="tight"); plt.close(fig)
            print("       ", out / "network_plan_map.png")
        except Exception as e:
            print("map skipped:", e)


if __name__ == "__main__":
    main()
