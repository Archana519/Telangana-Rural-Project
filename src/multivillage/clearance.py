"""Building-clearance routing: proposed and alternative routes that never run over a building rooftop.

Why this exists. The Stage B planner (scripts/plan_network_v2.py, frozen) treats footprints as a SOFT penalty (mu = 4): the least-cost path may still run across a
building when the detour costs more than the penalty. Stage B measured this for Damarakunta (28 of 163 house routes cross another footprint, 209 m). This module keeps the
planner untouched and changes only the grid it is given:

1. Hard clearance. Every cell whose CENTRE lies within `clearance_m` (default 7.2 m) of ANY footprint is impassable. The cost grid is 10 m, so a path segment joins two
   passable cell centres and is at most 14.14 m long; its nearer end is then at most 7.07 m from any point on the segment, so with 7.2 m of clearance no segment can touch a footprint.
   (Proof sketch: a point P of a footprint on the segment lies within 7.07 m of one end; that end would then be within 7.2 m of the footprint and impassable.)
2. Entrances. A target (house or facility) sits inside its own building, which is blocked. Each target is therefore connected from the EDGE of its own building (the entrance) to
   the nearest passable cell by a short straight lane; candidates are tried nearest first and a lane that would touch any OTHER footprint is rejected. A target with no such lane inside
   `snap_m` (a house enclosed by other buildings) is reported as unreachable, never silently routed across a roof.
3. Verification. After planning, the drawn geometry of every route (lane + path + attachment to the road) is intersected with all footprints other than the route's own; the length
   inside them is reported (expected 0.0 m) together with the number of routes checked.

Route lengths are measured from the building entrance (the part inside the target's own building is not counted). Costs are ordinal; routes are planning alternatives, not engineered roads.
"""
from __future__ import annotations

import math

import numpy as np
from affine import Affine
from rasterio.features import rasterize
from shapely.geometry import LineString, Point
from shapely.ops import nearest_points, unary_union
from shapely.strtree import STRtree

from . import pipeline as PL

GRID_M = 5.0                # clearance grid: the 10 m planning cost surface is refined to 5 m cells (same cost per metre) so that streets wider than 2 x clearance stay passable
CLEARANCE_M = 3.6           # > half the diagonal of a 5 m cell (3.54 m); with 10 m cells the same argument needs 7.2 m and blocks every street narrower than 14.4 m
CROSS_TOL_M = 0.05          # numerical tolerance when reporting length inside other footprints


class ClearWorld:
    """Like pipeline.World, but footprints (buffered by the clearance) are impassable instead of penalised."""

    def __init__(self, cost, transform, shape, roads_geoms, footprints, clearance_m=CLEARANCE_M, corner_cut=False, grid_m=GRID_M):
        P = PL.pn()
        k = max(1, int(round(abs(transform.a) / grid_m)))
        if k > 1:                                                    # refine: every 10 m cell becomes k x k cells of the same cost per metre
            cost = np.repeat(np.repeat(np.asarray(cost, float), k, axis=0), k, axis=1)
            transform = Affine(transform.a / k, 0, transform.c, 0, transform.e / k, transform.f)
            shape = cost.shape
        if clearance_m < abs(transform.a) * math.sqrt(2) / 2:
            raise ValueError(f"clearance {clearance_m} m is below half the cell diagonal ({abs(transform.a) * math.sqrt(2) / 2:.2f} m): routes could clip footprints")
        H, W = shape
        blocked = np.zeros((H, W), bool)
        if len(footprints):
            blocked = rasterize([(g.buffer(clearance_m), 1) for g in footprints], out_shape=(H, W), transform=transform, fill=0, all_touched=False, dtype="uint8").astype(bool)
        self.blocked, self.cost, self.T, self.shape, self.clearance_m = blocked, cost, transform, shape, clearance_m
        self.grid = P.Grid(cost, transform, hard=blocked, mult=None, corner_cut=corner_cut)
        lines = [g for g in roads_geoms if g is not None and not g.is_empty]
        self.road_union = unary_union(lines)
        rr = rasterize([(g, 1) for g in lines], out_shape=(H, W), transform=transform, fill=0, all_touched=True, dtype="uint8").astype(bool)
        pr = self.grid.pass_np[1:-1, 1:-1]
        rows, cols = np.nonzero(rr & pr)
        self.road_cells = set(((rows + 1) * self.grid.W2 + cols + 1).tolist())
        self.road_cells_total, self.road_cells_passable = int(rr.sum()), int((rr & pr).sum())
        from scipy import ndimage                                   # 4-connected components of the passable grid (a diagonal step needs both orthogonal cells passable, so 4-connectivity is exact)
        self.comp, _ = ndimage.label(pr)
        self.road_comps = set(np.unique(self.comp[rr & pr]).tolist()) - {0}


class Footprints:
    """All footprints with a spatial index; `own` footprints are excluded when testing a route's crossings."""

    def __init__(self, gdf):
        self.geoms = list(gdf.geometry)
        self.hids = [int(h) if h == h else -1 for h in (gdf["hid"] if "hid" in gdf else range(len(gdf)))]
        self.tree = STRtree(self.geoms)

    def near(self, geom, d):
        return [int(i) for i in self.tree.query(geom.buffer(d))]

    def nearest_own(self, pt, max_m=25.0):
        """Index of the footprint containing pt, else the nearest within max_m, else None."""
        best, bd = None, max_m
        for i in self.near(pt, max_m):
            d = self.geoms[i].distance(pt)
            if d < bd or (d == 0 and bd > 0):
                best, bd = i, d
        return best

    def crossing_len(self, line, own_idx):
        """Length of `line` inside any footprint except own_idx."""
        tot = 0.0
        for i in (int(j) for j in self.tree.query(line)):
            if i == own_idx:
                continue
            tot += line.intersection(self.geoms[i]).length
        return tot


def entrance(world: ClearWorld, fp: Footprints, own_idx, pt: Point, snap_m: float, tries: int = 14):
    """(entrance point on the own building edge, passable cell-centre Point, lane length m) or None.
    The lane is the straight segment from the entrance to the cell centre; a lane that touches any other footprint is skipped."""
    g = world.grid
    own = fp.geoms[own_idx] if own_idx is not None else None
    ref = own if own is not None else pt
    b = ref.buffer(snap_m + world.grid.res).bounds
    c0, r1 = int(math.floor((b[0] - world.T.c) / world.T.a)), int(math.floor((b[1] - world.T.f) / world.T.e))
    c1, r0 = int(math.ceil((b[2] - world.T.c) / world.T.a)), int(math.ceil((b[3] - world.T.f) / world.T.e))
    r_lo, r_hi = sorted((max(min(r0, r1), 0), min(max(r0, r1), world.shape[0] - 1)))
    c_lo, c_hi = max(c0, 0), min(c1, world.shape[1] - 1)
    sub = g.pass_np[1:-1, 1:-1][r_lo:r_hi + 1, c_lo:c_hi + 1]
    rr, cc = np.nonzero(sub)
    if len(rr) == 0:
        return None
    rr, cc = rr + r_lo, cc + c_lo
    keep = np.isin(world.comp[rr, cc], list(world.road_comps))     # only free cells that are connected to the road network (not pockets enclosed by buildings)
    rr, cc = rr[keep], cc[keep]
    if len(rr) == 0:
        return None
    xs, ys = world.T.c + (cc + 0.5) * world.T.a, world.T.f + (rr + 0.5) * world.T.e
    d = np.array([ref.distance(Point(x, y)) for x, y in zip(xs, ys)])
    for j in np.argsort(d)[:tries]:
        if d[j] > snap_m:
            break
        cen = Point(xs[j], ys[j])
        ent = nearest_points(own, cen)[0] if own is not None else pt
        lane = LineString([(ent.x, ent.y), (cen.x, cen.y)]) if ent.distance(cen) > 1e-6 else None
        if lane is not None and fp.crossing_len(lane, own_idx) > CROSS_TOL_M:
            continue
        return ent, cen, float(ent.distance(cen))
    return None


def prepare_targets(world: ClearWorld, fp: Footprints, targets: list, snap_m: float):
    """Replace each target's point by the passable cell centre reached from its building entrance. Returns (usable targets, meta by id, unreachable ids)."""
    out, meta, bad = [], {}, {}
    for t in targets:
        own = fp.nearest_own(t["pt"], 25.0 if t["kind"] == "FACILITY" else 1.0)
        if t["kind"] == "HOUSE":
            own = fp.nearest_own(t["pt"], 1.0)
        e = entrance(world, fp, own, t["pt"], snap_m)
        if e is None:
            bad[t["id"]] = "NO_CLEAR_LANE_FROM_BUILDING_EDGE_TO_A_FREE_CELL"
            continue
        ent, cen, lane = e
        out.append(dict(t, pt=cen))
        meta[t["id"]] = dict(entrance=ent, own=own, lane_m=lane)
    return out, meta, bad


def _wrap(r, meta, fp_hids):
    """Planner route -> drawn geometry that starts at the building entrance."""
    m = meta[r["target"]]
    ent = m["entrance"]
    coords = list(r["geom"].coords)
    if (ent.x, ent.y) != tuple(coords[0]):
        coords = [(ent.x, ent.y)] + coords
    return dict(target=r["target"], geom=LineString(coords), net_geom=r["geom"], own=m["own"], lane_m=m["lane_m"], raw=r, own_hid=(fp_hids[m["own"]] if m["own"] is not None else None), own_len_m=r["own_len_m"] + m["lane_m"])


def plan_clear(world: ClearWorld, fp: Footprints, targets: list, p: dict, log=lambda *a: None):
    """Two-stage plan on the clearance grid. Returns dict(indep, shared, unreachable, fails, sel_raw)."""
    P = PL.pn()
    use, meta, bad = prepare_targets(world, fp, targets, p["snap_m"])
    res = P.plan(world.grid, world.road_union, world.road_cells, use, p, log=log)
    indep = [_wrap(r, meta, fp.hids) for r in res["indep"].values()]
    shared = [_wrap(r, meta, fp.hids) for r in res["sel"].values()]
    return dict(indep=indep, shared=shared, unreachable=bad, fails=dict(res.get("fails", {})), raw=res, meta=meta)


def verify(routes: list, fp: Footprints) -> dict:
    """Length of each DRAWN route (lane + path + road attachment) inside footprints other than its own."""
    n_cross, tot, worst = 0, 0.0, 0.0
    for r in routes:
        L = fp.crossing_len(r["geom"], r["own"])
        if L > CROSS_TOL_M:
            n_cross += 1; tot += L; worst = max(worst, L)
    return dict(routes_checked=len(routes), routes_crossing=n_cross, length_inside_other_footprints_m=round(tot, 2), worst_route_m=round(worst, 2))


def unique_len(routes: list) -> float:
    return float(PL.pn().unique_edge_metrics([r.get("raw", r) for r in routes])["unique_len_m"]) if routes else 0.0


# ---------------------------------------------------------------------------------------------- one call per village (cached)
def compute_clearance(cfg: dict, S: dict, ddir, cache_path=None, log=print, limit_targets: int | None = None) -> dict:
    """Plan the building-clearance network for one village from its state dict S (footprints, road-gap houses, verified facilities, roads).
    House routes and facility routes are planned separately, exactly as the main comparison does, on the SAME clearance grid. Cached as a pickle.
    Returns dict with lists of routes (geometry, target id, own footprint, lane) and summary numbers; geometries are EPSG:32644."""
    import pickle
    from pathlib import Path

    from . import prepare as P
    if cache_path and Path(cache_path).exists():
        c = pickle.load(open(cache_path, "rb"))
        if c.get("fingerprint") == fingerprint(S["gap"], S["fac"], limit_targets):
            return c
        log("clearance cache is stale (targets or facilities changed): re-planning")
    cell = S["cell"]
    prep = P.prepare_rasters(cfg, cell, ddir, log=lambda *a: None)
    cost, _ = P.cost_surface(cfg, prep, cell)
    return compute_from_arrays(cost, prep["transform"], prep["shape"], list(S["layers"]["roads"].geometry.intersection(cell)), S["houses_all"], S["gap"], S["fac"], PL.planner_params(cfg),
                               cache_path=cache_path, log=log, limit_targets=limit_targets)


def fingerprint(gap, fac, limit=None) -> str:
    """Identifies the target set (road-gap houses and facilities); a cached clearance network is reused only if it matches."""
    import hashlib
    h = hashlib.md5()
    h.update(repr((len(gap), limit, sorted(int(x) for x in gap["hid"]) if "hid" in gap else [])).encode())
    h.update(repr(sorted((int(r.fid), str(r.name), round(r.geometry.x, 1), round(r.geometry.y, 1), str(r.facility_type)) for r in fac.itertuples())).encode())
    return h.hexdigest()


def compute_from_arrays(cost, transform, shape, roads, houses_all, gap, fac, params, cache_path=None, log=print, limit_targets=None, clearance_m=CLEARANCE_M, grid_m=GRID_M) -> dict:
    import pickle
    from pathlib import Path
    import time
    t0 = time.time()
    fprint = fingerprint(gap, fac, limit_targets)
    if cache_path and Path(cache_path).exists():
        c = pickle.load(open(cache_path, "rb"))
        if c.get("fingerprint") == fprint:
            return c
    fp = Footprints(houses_all)
    w = ClearWorld(cost, transform, shape, roads, fp.geoms, clearance_m=clearance_m, grid_m=grid_m)
    g = gap if not limit_targets else gap.iloc[:limit_targets]
    htg = PL.make_targets(g, None)
    ftg = PL.make_targets(houses_all.iloc[0:0], fac.rename(columns={"name": "name"})[["fid", "name", "facility_type", "geometry"]]) if len(fac) else []
    log(f"clearance grid {w.grid.res:g} m, clearance {clearance_m:g} m, blocked {100 * w.blocked.mean():.1f}% of cells; planning {len(htg)} house and {len(ftg)} facility targets")
    H = plan_clear(w, fp, htg, params)
    F = plan_clear(w, fp, ftg, params) if ftg else dict(indep=[], shared=[], unreachable={}, fails={}, meta={})
    all_shared, all_indep = H["shared"] + F["shared"], H["indep"] + F["indep"]
    out = dict(
        params=dict(grid_m=w.grid.res, clearance_m=clearance_m, snap_m=params["snap_m"], planner="plan_network_v2 (unchanged), footprints hard-blocked; lane from building edge"),
        houses=dict(targets=len(htg), indep=H["indep"], shared=H["shared"], unreachable=H["unreachable"], fails=H["fails"]),
        facilities=dict(targets=len(ftg), indep=F["indep"], shared=F["shared"], unreachable=F["unreachable"], fails=F["fails"]),
        unique=dict(house_indep_m=unique_len(H["indep"]), house_shared_m=unique_len(H["shared"]), fac_shared_m=unique_len(F["shared"]), fac_indep_m=unique_len(F["indep"]),
                    combined_shared_m=unique_len(all_shared), combined_indep_m=unique_len(all_indep)),
        verify=dict(house_indep=verify(H["indep"], fp), house_shared=verify(H["shared"], fp), fac_indep=verify(F["indep"], fp), fac_shared=verify(F["shared"], fp)),
        road_cells=(w.road_cells_total, w.road_cells_passable), seconds=round(time.time() - t0, 1), fingerprint=fprint)
    if cache_path:
        out = _slim(out)
        pickle.dump(out, open(cache_path, "wb"))
    return out


def _slim(out: dict) -> dict:
    """Routes without the planner's raw objects (smaller pickle); keeps what the lengths, the maps and the checks need."""
    def one(r):
        raw = r.get("raw") or {}
        return {**{k: v for k, v in r.items() if k != "raw"}, "edges": raw.get("edges", r.get("edges")), "start_snap_m": raw.get("start_snap_m", r.get("start_snap_m", 0.0)),
                "end_snap_m": raw.get("end_snap_m", r.get("end_snap_m", 0.0)), "cost": raw.get("cost", r.get("cost", 0.0))}
    o = dict(out)
    for grp in ("houses", "facilities"):
        o[grp] = dict(out[grp], indep=[one(r) for r in out[grp]["indep"]], shared=[one(r) for r in out[grp]["shared"]])
    return o
