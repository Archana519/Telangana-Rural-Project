"""Hierarchical, multi-level cost-surface routing (Contribution 3): Gram Panchayat -> Mandal -> District.

Level 1 (village) is the completed Stage B pipeline (scripts/plan_network_v2.py + dk_stageB_run_v1_6.py). This module
re-uses its search engine (the padded `Grid` with 8-connected Dijkstra, hard/soft constraints) and adds:

  Level 2  GP      hamlet hubs + amenities -> existing roads, 10 m grid, footprint penalty with LOCAL OVERRIDES
  Level 3  Mandal  GP hubs + HQ/PHC/markets -> existing roads, 30 m grid, slope/forest/water resistance, road snapping
  Level 4  District  coarse-to-fine backbone: coarse Steiner-style plan -> graph contraction into chains ->
                   windowed fine refinement inside a corridor (memory bounded by `segment_m` and `corridor_m`)

Shared-network rule (all levels): lazy-greedy shortest-path attachment (Takahashi-Matsuyama style). A node's marginal
cost is the least-cost path to the CURRENT network (existing roads UNION already selected routes), so shared edges are
counted once. Costs only fall as the network grows, so stale heap keys are upper bounds and lazy evaluation is exact
for this greedy rule. No optimality guarantee is claimed (heuristic, like Stage B).

Cost-surface formulation (same as the manuscript):
  c(x) = [c_lc(class(x)) + g(slope(x))] * m(x),
  m(x) = 1 + (mu - 1) * 1[x in footprints] * (1 - 1[x within r_f of an exempt facility f])      (local override)
Units are ordinal planning units, not currency. Raw inputs are never modified.
"""
from __future__ import annotations

import heapq
import importlib.util
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

import numpy as np
from rasterio import features
from rasterio.transform import Affine
from shapely.geometry import LineString, Point
from shapely.ops import unary_union

from .layers import LayerProvider, cost_from_layers, grid_for

REPO = Path(__file__).resolve().parents[2]
_GM = None


def grid_module():
    """The Stage B planner module (scripts/plan_network_v2.py), loaded once. Provides `Grid`."""
    global _GM
    if _GM is None:
        spec = importlib.util.spec_from_file_location("plan_network_v2", REPO / "scripts" / "plan_network_v2.py")
        m = importlib.util.module_from_spec(spec)
        sys.modules["plan_network_v2"] = m
        spec.loader.exec_module(m)
        _GM = m
    return _GM


# ======================================================================================== data classes
@dataclass
class Node:
    id: str
    x: float
    y: float
    weight: float = 1.0
    kind: str = "house"          # hamlet | school | healthcare | panchayat_office | gp_hub | mandal_hq | phc | market | district_hq
    exempt: bool = False         # local penalty override applies around this node (GP level)


@dataclass
class Route:
    id: str
    kind: str
    geometry: LineString
    length_m: float
    cost: float
    attached_to: str             # "ROAD", a node id, "ROOT" or "" when failed
    snap_m: float = 0.0


@dataclass
class LevelResult:
    level: str
    mode: str                                   # shared | independent
    routes: dict = field(default_factory=dict)  # id -> Route
    failures: dict = field(default_factory=dict)
    unique_length_m: float = 0.0
    total_length_m: float = 0.0
    unique_cost: float = 0.0
    connected_any_road: set = field(default_factory=set)
    connected_main: set = field(default_factory=set)
    meta: dict = field(default_factory=dict)
    served: Optional[set] = None                # district level: terminals served (routes there are backbone chains)

    @property
    def routed_ids(self):
        return set(self.served) if self.served is not None else set(self.routes)


@dataclass
class GPInputs:
    name: str
    roads: object                 # GeoDataFrame (lines)
    nodes: list                   # list[Node] : hamlet hubs + facilities
    boundary: Optional[object] = None      # shapely polygon (optional)
    footprints: Optional[object] = None    # GeoDataFrame of building polygons (optional)
    provider: Optional[LayerProvider] = None
    notes: list = field(default_factory=list)


@dataclass
class MandalInputs:
    name: str
    roads: object
    nodes: list                   # GP hubs, mandal HQ, PHCs, markets
    bounds: tuple
    provider: LayerProvider
    boundary: Optional[object] = None
    notes: list = field(default_factory=list)
    local_roads: Optional[object] = None       # below-collector roads: cheaper to travel on, but NOT attachment goals


@dataclass
class DistrictInputs:
    name: str
    roads: object
    nodes: list                   # terminals: mandal HQs + one 'district_hq' (root)
    bounds: tuple
    provider: LayerProvider
    boundary: Optional[object] = None
    notes: list = field(default_factory=list)


# ======================================================================================== raster helpers
def rasterize(geoms, transform: Affine, shape, all_touched=True) -> np.ndarray:
    geoms = [g for g in geoms if g is not None and not g.is_empty]
    if not geoms:
        return np.zeros(shape, dtype=bool)
    return features.rasterize([(g, 1) for g in geoms], out_shape=shape, transform=transform, fill=0,
                              all_touched=all_touched, dtype="uint8").astype(bool)


def make_4connected(mask: np.ndarray) -> np.ndarray:
    """Add one orthogonal cell wherever two mask cells touch only diagonally.

    The planner forbids diagonal steps that squeeze between blocked cells (Stage B `corner_cut=forbid`), so a
    diagonally rasterised road would otherwise be impassable as a bridge over water.
    """
    m = mask.copy()
    d1 = mask[:-1, :-1] & mask[1:, 1:] & ~mask[:-1, 1:] & ~mask[1:, :-1]      # \ diagonal
    m[:-1, 1:] |= d1
    d2 = mask[:-1, 1:] & mask[1:, :-1] & ~mask[:-1, :-1] & ~mask[1:, 1:]      # / diagonal
    m[:-1, :-1] |= d2
    return m


def rasterize_roads(geoms, transform: Affine, shape) -> np.ndarray:
    return make_4connected(rasterize(geoms, transform, shape))


def disc_mask(shape, transform: Affine, x: float, y: float, r: float) -> np.ndarray:
    """Cells whose centre lies within r of (x, y); computed on a local block only."""
    res = abs(transform.a)
    H, W = shape
    c0 = int((x - transform.c) / res)
    r0 = int((transform.f - y) / res)
    k = int(math.ceil(r / res)) + 2
    rr, cc = np.mgrid[max(r0 - k, 0): min(r0 + k + 1, H), max(c0 - k, 0): min(c0 + k + 1, W)]
    cx = transform.c + (cc + 0.5) * res
    cy = transform.f - (rr + 0.5) * res
    out = np.zeros(shape, dtype=bool)
    out[rr, cc] = np.hypot(cx - x, cy - y) <= r
    return out


def penalty_multiplier(shape, transform: Affine, footprint_mask: Optional[np.ndarray], mu: float,
                       exempt_discs=()) -> np.ndarray:
    """m(x) = 1 + (mu-1) * 1[footprint] * (1 - 1[inside an exempt disc]).   (Eq. override of the manuscript)"""
    m = np.ones(shape, dtype="float32")
    if footprint_mask is None or mu == 1.0:
        return m
    pen = footprint_mask.copy()
    for (x, y, r) in exempt_discs:
        pen &= ~disc_mask(shape, transform, x, y, r)
    m[pen] = float(mu)
    return m


def apply_road_discount(cost: np.ndarray, road_mask: np.ndarray, factor: float) -> np.ndarray:
    """Existing-road snapping: road cells get cost*factor and stay passable even over water (bridges/culverts)."""
    out = cost.copy()
    fill = float(np.nanmean(cost)) if np.isfinite(cost).any() else 1.0
    base = np.where(np.isfinite(out), out, fill)
    out[road_mask] = (base * factor)[road_mask]
    return out


# ======================================================================================== network planning
class RoutingProblem:
    """A grid-based routing problem (Levels 2 and 3): raster layers + nodes + existing roads -> shared network."""

    def __init__(self, level: str, cost: np.ndarray, transform: Affine, nodes: list, road_mask: np.ndarray,
                 footprint_mask: Optional[np.ndarray] = None, mu: float = 1.0, override_radius_m: float = 0.0,
                 snap_m: float = 30.0, domain_mask: Optional[np.ndarray] = None, meta: Optional[dict] = None):
        self.level, self.cost, self.T, self.nodes = level, cost, transform, nodes
        self.road_mask, self.footprint_mask = road_mask, footprint_mask
        self.mu, self.override_radius_m, self.snap_m = mu, override_radius_m, snap_m
        self.domain_mask = domain_mask
        self.meta = meta or {}
        self.shape = cost.shape

    def override_discs(self):
        return [(n.x, n.y, self.override_radius_m) for n in self.nodes if n.exempt and self.override_radius_m > 0]

    def build_grid(self, use_override: bool = True):
        discs = self.override_discs() if use_override else []
        mult = penalty_multiplier(self.shape, self.T, self.footprint_mask, self.mu, discs)
        hard = None if self.domain_mask is None else ~self.domain_mask
        # roads stay routable even if the domain polygon or the land cover would block them
        grid = grid_module().Grid(self.cost, self.T, hard=hard, mult=mult, corner_cut=False)
        return grid

    def road_cells(self, grid) -> set:
        rr, cc = np.nonzero(self.road_mask)
        ok = grid.pass_np[rr + 1, cc + 1]
        return set(((rr[ok] + 1) * grid.W2 + cc[ok] + 1).tolist())

    def solve(self, nodes: Optional[list] = None, use_override: bool = True, mode: str = "shared") -> LevelResult:
        grid = self.build_grid(use_override)
        return plan_on_grid(grid, nodes if nodes is not None else self.nodes, self.road_cells(grid), self.snap_m,
                            mode=mode, level=self.level)


def plan_on_grid(grid, nodes: list, road_cells: set, snap_m: float, mode: str = "shared", level: str = "") -> LevelResult:
    """Lazy-greedy shared-network attachment (mode='shared') or independent least-cost to roads (mode='independent')."""
    res = LevelResult(level=level, mode=mode)
    goals = set(road_cells)
    starts, snaps = {}, {}
    for n in nodes:
        s = grid.snap(n.x, n.y, snap_m)
        if s is None:
            res.failures[n.id] = "SNAP_FAILED_NO_PASSABLE_CELL_WITHIN_SNAP_DISTANCE"
            continue
        starts[n.id], snaps[n.id] = s[0], s[1]
    node_by_id = {n.id: n for n in nodes}
    owner = {}                                  # cell -> id of the route that created it
    unique_edges = {}                           # (a,b) -> (len, cost)
    total_len = 0.0
    version = 0
    heap = []
    counter = 0

    def attempt(nid, goal_set):
        r = grid.search(starts[nid], goal_set)
        if isinstance(r, str):
            return None, r
        cells = r["cells"]
        e = grid.edges(cells)
        return (cells, e), ""

    def make_route(nid, cells, e, attached):
        n = node_by_id[nid]
        coords = [(n.x, n.y)] + [grid.xy(c) for c in cells]
        L = sum(x[2] for x in e)
        C = sum(x[3] for x in e)
        return Route(nid, n.kind, LineString(coords), L, C, attached, snaps[nid])

    if mode == "independent":
        for nid in starts:
            out, why = attempt(nid, goals)
            if out is None:
                res.failures[nid] = why
                continue
            cells, e = out
            att = "ROAD"
            res.routes[nid] = make_route(nid, cells, e, att)
            total_len += res.routes[nid].length_m
            for a, b, L, c in e:
                unique_edges[(a, b)] = (L, c)
            for c in cells:
                owner.setdefault(c, nid)
    else:
        for nid in starts:
            out, why = attempt(nid, goals)
            if out is None:
                res.failures[nid] = why
                continue
            cost = sum(x[3] for x in out[1])
            heapq.heappush(heap, (cost / max(node_by_id[nid].weight, 1e-9), counter, nid, version, out))
            counter += 1
        while heap:
            key, _, nid, v, out = heapq.heappop(heap)
            if v != version:                     # stale upper bound -> recompute against the current network
                out, why = attempt(nid, goals)
                if out is None:
                    res.failures[nid] = why
                    continue
                cost = sum(x[3] for x in out[1])
                heapq.heappush(heap, (cost / max(node_by_id[nid].weight, 1e-9), counter, nid, version, out))
                counter += 1
                continue
            cells, e = out                       # fresh entry: its stored path is already against the current network
            end = cells[-1]
            att = "ROAD" if end in road_cells else owner.get(end, "ROAD")
            res.routes[nid] = make_route(nid, cells, e, att)
            total_len += res.routes[nid].length_m
            for a, b, L, c in e:
                unique_edges[(a, b)] = (L, c)
            for c in cells:
                owner.setdefault(c, nid)
            before = len(goals)
            goals.update(cells)
            if len(goals) != before:
                version += 1
    res.unique_length_m = sum(v[0] for v in unique_edges.values())
    res.unique_cost = sum(v[1] for v in unique_edges.values())
    res.total_length_m = total_len
    res.connected_any_road, res.connected_main = verify_connectivity(grid, res, starts, road_cells)
    res.meta.update(snap_m_max=max(snaps.values()) if snaps else 0.0, n_road_cells=len(road_cells))
    return res


def verify_connectivity(grid, res: LevelResult, starts: dict, road_cells: set):
    """Graph check (not by construction): union-find over route cells + road cells.
    Returns (ids connected to ANY road component, ids connected to the LARGEST road component)."""
    parent = {}

    def find(a):
        parent.setdefault(a, a)
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    W2 = grid.W2
    for c in road_cells:
        find(c)
        for d in (1, W2, W2 + 1, W2 - 1):
            if c + d in road_cells:
                union(c, c + d)
    for nid, rt in res.routes.items():
        # recover the cell path from the geometry: route cells are grid cell centres after the node point
        pts = list(rt.geometry.coords)[1:]
        prev = None
        for (x, y) in pts:
            i = grid.idx_of(x, y)
            if i is None:
                continue
            find(i)
            if prev is not None:
                union(prev, i)
            prev = i
        if nid in starts and pts:
            union(starts[nid], grid.idx_of(*pts[0]) if grid.idx_of(*pts[0]) is not None else starts[nid])
    road_roots = {}
    for c in road_cells:
        road_roots.setdefault(find(c), 0)
        road_roots[find(c)] += 1
    main_root = max(road_roots, key=road_roots.get) if road_roots else None
    any_ids, main_ids = set(), set()
    for nid in res.routes:
        pts = list(res.routes[nid].geometry.coords)[1:]
        if not pts:
            continue
        i = grid.idx_of(*pts[0])
        if i is None:
            continue
        r = find(i)
        if r in road_roots:
            any_ids.add(nid)
        if r == main_root:
            main_ids.add(nid)
    return any_ids, main_ids


# ======================================================================================== Level 2 (GP)
def cluster_hamlets(points_xy: np.ndarray, eps_m: float, min_houses: int = 1):
    """Connected components of the eps-neighbour graph -> list of index arrays (hamlet clusters)."""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    from scipy.spatial import cKDTree
    n = len(points_xy)
    if n == 0:
        return []
    tree = cKDTree(points_xy)
    pairs = tree.query_pairs(eps_m, output_type="ndarray")
    if len(pairs):
        g = coo_matrix((np.ones(len(pairs)), (pairs[:, 0], pairs[:, 1])), shape=(n, n))
    else:
        g = coo_matrix((n, n))
    _, lab = connected_components(g, directed=False)
    groups = [np.nonzero(lab == k)[0] for k in range(lab.max() + 1)]
    return [g_ for g_ in groups if len(g_) >= min_houses]


def hamlet_hubs(points_xy: np.ndarray, eps_m: float, min_houses: int = 1, prefix: str = "HAM") -> list:
    """Aggregate village-level house targets into hamlet hub nodes (member nearest the cluster centroid)."""
    hubs = []
    for k, idx in enumerate(sorted(cluster_hamlets(points_xy, eps_m, min_houses), key=lambda g: -len(g))):
        pts = points_xy[idx]
        cen = pts.mean(axis=0)
        j = int(np.argmin(np.hypot(*(pts - cen).T)))
        hubs.append(Node(f"{prefix}{k + 1:03d}", float(pts[j, 0]), float(pts[j, 1]), float(len(idx)), "hamlet"))
    return hubs


def build_gp_problem(gp: GPInputs, cfg: dict) -> RoutingProblem:
    """Level 2: high-resolution cost raster + footprint penalty + local overrides for GP-level amenities."""
    lv, cs = cfg["levels"]["gp"], cfg["cost_surface"]
    res = float(lv["resolution_m"])
    pts = [(n.x, n.y) for n in gp.nodes]
    if gp.boundary is not None:
        bounds = gp.boundary.buffer(lv.get("domain_buffer_m", 0.0)).bounds
    else:                                  # no polygon: nodes + roads + margin
        rb = gp.roads.total_bounds
        xs = [p[0] for p in pts] + [rb[0], rb[2]]
        ys = [p[1] for p in pts] + [rb[1], rb[3]]
        bounds = (min(xs) - 500.0, min(ys) - 500.0, max(xs) + 500.0, max(ys) + 500.0)
    provider = gp.provider
    if provider is None:
        from .layers import FlatLayerProvider
        provider = FlatLayerProvider()
    layers = provider.layers(bounds, res)
    cost = cost_from_layers(layers, cs)
    T, shape = layers.transform, layers.shape
    notes = list(gp.notes)
    if layers.landcover is None:
        notes.append("FALLBACK: no land-cover raster; constant cost surface (flat_fallback_cost) + footprint penalty only")
    if layers.slope_deg is None:
        notes.append("FALLBACK: no DEM; slope term omitted")
    road_mask = rasterize_roads(list(gp.roads.geometry), T, shape)
    foot_mask = rasterize(list(gp.footprints.geometry), T, shape) if gp.footprints is not None and len(gp.footprints) else None
    domain = None
    if gp.boundary is not None:
        domain = rasterize([gp.boundary.buffer(lv.get("domain_buffer_m", 0.0))], T, shape) | road_mask
    # nodes that carry the exempt flag get the override; the flag is set by the caller from facility types
    return RoutingProblem("gp", cost, T, gp.nodes, road_mask, foot_mask, float(lv["footprint_penalty"]),
                          float(lv["override_radius_m"]), float(lv["snap_m"]), domain,
                          meta=dict(layer_source=layers.source, notes=notes, resolution_m=res, bounds=bounds))


# ======================================================================================== Level 3 (Mandal)
def build_mandal_problem(m: MandalInputs, cfg: dict) -> RoutingProblem:
    """Level 3: collector roads from GP hubs/HQ/PHC/markets over slope, water and forest resistance, snapped to roads."""
    lv, cs = cfg["levels"]["mandal"], cfg["cost_surface"]
    res = float(lv["resolution_m"])
    layers = m.provider.layers(m.bounds, res)
    cost = cost_from_layers(layers, cs, forest_multiplier=float(lv["forest_cost_multiplier"]))
    T, shape = layers.transform, layers.shape
    road_mask = rasterize_roads(list(m.roads.geometry), T, shape)
    discount_mask = road_mask
    if m.local_roads is not None and len(m.local_roads):
        discount_mask = road_mask | rasterize_roads(list(m.local_roads.geometry), T, shape)
    cost = apply_road_discount(cost, discount_mask, float(lv["road_discount"]))
    domain = rasterize([m.boundary], T, shape) | discount_mask if m.boundary is not None else None
    notes = list(m.notes)
    if layers.landcover is None:
        notes.append("FALLBACK: no land-cover raster; constant cost surface")
    return RoutingProblem("mandal", cost, T, m.nodes, road_mask, None, 1.0, 0.0, float(lv["snap_m"]), domain,
                          meta=dict(layer_source=layers.source, notes=notes, resolution_m=res, bounds=m.bounds))


def gp_hubs_from_level2(gp_name: str, result: LevelResult, nodes: list, hub_weight_per_house: float = 1.0) -> Node:
    """One Level-3 hub per GP: the panchayat office if present, else the heaviest hamlet; weight = houses served."""
    houses = sum(n.weight for n in nodes if n.kind == "hamlet" and n.id in result.routes)
    anchor = next((n for n in nodes if n.kind == "panchayat_office"), None) or \
        max((n for n in nodes if n.kind == "hamlet"), key=lambda n: n.weight)
    return Node(f"GP_{gp_name}", anchor.x, anchor.y, max(houses, 1.0) * hub_weight_per_house, "gp_hub")


# ======================================================================================== Level 4 (District)
def contract_chains(edges: set, keep_cells: set) -> list:
    """Graph contraction: collapse a cell-edge set (a tree/forest) into chains between 'key' cells.

    Key cells are the terminals/hubs and every cell of degree != 2 (junctions, leaves). Each returned chain is the
    ordered cell list from one key cell to the next; degree-2 interior cells are contracted away.
    """
    adj = {}
    for a, b in edges:
        adj.setdefault(a, []).append(b)
        adj.setdefault(b, []).append(a)
    key = {c for c, nb in adj.items() if len(nb) != 2} | (set(adj) & set(keep_cells))
    seen, chains = set(), []
    for k in key:
        for nb in adj.get(k, []):
            if (k, nb) in seen:
                continue
            chain, prev, cur = [k, nb], k, nb
            seen.add((k, nb))
            while cur not in key:
                nxt = [x for x in adj[cur] if x != prev]
                if not nxt:
                    break
                prev, cur = cur, nxt[0]
                chain.append(cur)
                seen.add((chain[-2], chain[-1]))
            seen.add((chain[-1], chain[-2]))
            chains.append(chain)
    return chains


def contract_degree2(G, keep=()):
    """Contract degree-2 vertices of a weighted networkx graph (attribute 'length'), keeping `keep` nodes.
    Returns a new graph whose edges store the summed length and the contracted vertex path in 'via'."""
    import networkx as nx
    H = nx.Graph()
    keep = set(keep)
    key = {n for n in G if G.degree(n) != 2 or n in keep}
    done = set()
    for k in key:
        H.add_node(k, **G.nodes[k])
        for nb in G[k]:
            if (k, nb) in done:
                continue
            path, prev, cur = [k, nb], k, nb
            length = G[k][nb].get("length", 1.0)
            while cur not in key:
                nxt = [x for x in G[cur] if x != prev]
                if not nxt:
                    break
                length += G[cur][nxt[0]].get("length", 1.0)
                prev, cur = cur, nxt[0]
                path.append(cur)
            done.add((k, nb))
            done.add((path[-1], path[-2]))
            if path[-1] != k and (not H.has_edge(k, path[-1]) or H[k][path[-1]]["length"] > length):
                H.add_edge(k, path[-1], length=length, via=path)
    return H


class DistrictProblem:
    """Coarse-to-fine district backbone. Memory is bounded by the coarse grid + one fine window at a time."""

    def __init__(self, d: DistrictInputs, cfg: dict):
        self.d, self.cfg = d, cfg
        self.lv, self.cs = cfg["levels"]["district"], cfg["cost_surface"]
        self.nodes = d.nodes
        self.level = "district"
        self.notes = list(d.notes)
        self.fine_res = float(self.lv["fine_resolution_m"])
        self.coarse_res = float(self.lv["coarse_resolution_m"])
        self.root = next((n for n in d.nodes if n.kind == "district_hq"), max(d.nodes, key=lambda n: n.weight))
        self.origin = (d.bounds[0], d.bounds[3])
        self._coarse = None
        self._road_buf = None

    def _existing_road_length(self, lines) -> float:
        """Length of the refined network lying on existing roads (within 1.5 fine cells); the rest is new construction."""
        if not lines:
            return 0.0
        if self._road_buf is None:
            self._road_buf = self.d.roads.geometry.union_all().buffer(1.5 * self.fine_res)
        return float(unary_union(lines).intersection(self._road_buf).length)

    # ---- coarse stage
    def coarse(self):
        if self._coarse is None:
            L = self.d.provider.layers(self.d.bounds, self.coarse_res)
            cost = cost_from_layers(L, self.cs, forest_multiplier=1.0)
            road = rasterize_roads(list(self.d.roads.geometry), L.transform, L.shape)
            cost = apply_road_discount(cost, road, float(self.lv["road_discount"]))
            self._coarse = (grid_module().Grid(cost, L.transform, corner_cut=False), L)
        return self._coarse

    def _coarse_plan(self, nodes, mode):
        grid, L = self.coarse()
        root_cell = grid.snap(self.root.x, self.root.y, 4 * self.coarse_res)
        if root_cell is None:
            raise RuntimeError("district root has no passable coarse cell")
        others = [n for n in nodes if n.id != self.root.id]
        # a copy of the root as the only seed goal: terminals attach to each other or to the root
        res = plan_on_grid(grid, others, {root_cell[0]}, 4 * self.coarse_res, mode=mode, level="district-coarse")
        return grid, res, root_cell[0]

    # ---- fine refinement of one coarse polyline
    def _window(self, poly_xy):
        r = self.fine_res
        ox, oy = self.origin
        line = LineString(poly_xy)
        minx, miny, maxx, maxy = line.buffer(float(self.lv["corridor_m"])).bounds
        minx = ox + math.floor((minx - ox) / r) * r
        maxy = oy - math.floor((oy - maxy) / r) * r
        maxx = ox + math.ceil((maxx - ox) / r) * r
        miny = oy - math.ceil((oy - miny) / r) * r
        return line, (minx, miny, maxx, maxy)

    def _refine_segment(self, poly_xy):
        """Fine least-cost path between the ends of a coarse sub-polyline, confined to its corridor.
        Returns (coords, length, cost, status)."""
        line, bounds = self._window(poly_xy)
        r = self.fine_res
        cells = ((bounds[2] - bounds[0]) / r) * ((bounds[3] - bounds[1]) / r)
        status = "fine"
        if cells > self.lv["max_fine_cells"]:        # memory guard: degrade to a coarser window grid
            r = r * math.ceil(math.sqrt(cells / self.lv["max_fine_cells"]))
            status = "fine_degraded"
        L = self.d.provider.layers(bounds, r)
        cost = cost_from_layers(L, self.cs)
        road = rasterize_roads(list(self.d.roads.clip_by_rect(*bounds).geometry), L.transform, L.shape)
        cost = apply_road_discount(cost, road, float(self.lv["road_discount"]))
        corridor = rasterize([line.buffer(float(self.lv["corridor_m"]))], L.transform, L.shape)
        g = grid_module().Grid(cost, L.transform, hard=~corridor, corner_cut=False)
        (x0, y0), (x1, y1) = poly_xy[0], poly_xy[-1]
        snap = max(3 * r, 1.5 * self.coarse_res)      # coarse waypoint -> nearest fine-passable cell (road/bridge cells)
        a, b = g.snap(x0, y0, snap), g.snap(x1, y1, snap)
        if a is None or b is None:
            return poly_xy, line.length, line.length * 3.0, "coarse_fallback"
        out = g.search(a[0], {b[0]})
        if isinstance(out, str):
            return poly_xy, line.length, line.length * 3.0, "coarse_fallback"
        e = g.edges(out["cells"])
        return [g.xy(c) for c in out["cells"]], sum(x[2] for x in e), sum(x[3] for x in e), status

    def _refine_polyline(self, poly_xy):
        seg_m = float(self.lv["segment_m"])
        # split at vertices once a segment exceeds seg_m
        parts, cur, acc = [], [poly_xy[0]], 0.0
        for p, q in zip(poly_xy, poly_xy[1:]):
            acc += math.hypot(q[0] - p[0], q[1] - p[1])
            cur.append(q)
            if acc >= seg_m:
                parts.append(cur)
                cur, acc = [q], 0.0
        if len(cur) > 1:
            parts.append(cur)
        coords, length, cost, statuses = [], 0.0, 0.0, []
        for part in parts:
            c, L, C, s = self._refine_segment(part)
            coords.extend(c if not coords else c[1:])
            length += L
            cost += C
            statuses.append(s)
        return coords, length, cost, statuses

    # ---- public solve
    def solve(self, nodes: Optional[list] = None, use_override: bool = True, mode: str = "shared") -> LevelResult:
        nodes = nodes if nodes is not None else self.nodes
        if not any(n.id == self.root.id for n in nodes):
            nodes = [self.root] + list(nodes)
        grid, cres, root_cell = self._coarse_plan(nodes, mode)
        res = LevelResult(level="district", mode=mode, failures=dict(cres.failures))
        status_count = {}
        lines = []
        if mode == "shared":
            edges = set()
            for rt in cres.routes.values():
                pts = [grid.idx_of(x, y) for (x, y) in list(rt.geometry.coords)[1:]]
                edges.update((min(a, b), max(a, b)) for a, b in zip(pts, pts[1:]) if a != b)
            keep = {root_cell} | {grid.snap(n.x, n.y, 4 * self.coarse_res)[0] for n in nodes
                                  if grid.snap(n.x, n.y, 4 * self.coarse_res)}
            chains = contract_chains(edges, keep)
            res.meta["n_coarse_edges"], res.meta["n_chains"] = len(edges), len(chains)
            for k, ch in enumerate(chains):
                coords, L, C, st = self._refine_polyline([grid.xy(c) for c in ch])
                for s in st:
                    status_count[s] = status_count.get(s, 0) + 1
                geom = LineString(coords)
                lines.append(geom)
                res.routes[f"CHAIN{k:03d}"] = Route(f"CHAIN{k:03d}", "backbone", geom, L, C, "ROOT")
                res.total_length_m += L
                res.unique_cost += C
            res.unique_length_m = unary_union(lines).length if lines else 0.0
            # a terminal is served if it lies within 2 coarse cells of the refined backbone
            net = unary_union(lines) if lines else None
            served = set()
            for n in nodes:
                if n.id == self.root.id:
                    continue
                if n.id in cres.failures:
                    continue
                tol = cres.routes[n.id].snap_m + 2 * self.coarse_res      # terminal -> coarse-cell snap + 2 cells
                if net is not None and Point(n.x, n.y).distance(net) <= tol:
                    served.add(n.id)
            res.served = served
            res.connected_any_road = served
            res.connected_main = served
            res.meta["served_terminals"] = len(served)
        else:                                          # independent star: every terminal to the root on its own
            for n in nodes:
                if n.id == self.root.id or n.id in cres.failures:
                    continue
                rt = cres.routes[n.id]
                poly = [grid.xy(grid.idx_of(x, y)) for (x, y) in list(rt.geometry.coords)[1:]]
                coords, L, C, st = self._refine_polyline(poly)
                for s in st:
                    status_count[s] = status_count.get(s, 0) + 1
                geom = LineString(coords)
                lines.append(geom)
                res.routes[n.id] = Route(n.id, n.kind, geom, L, C, "ROOT")
                res.total_length_m += L
            res.unique_length_m = unary_union(lines).length if lines else 0.0
            res.unique_cost = sum(r.cost for r in res.routes.values())
            res.served = set(res.routes)
            res.connected_any_road = set(res.routes)
            res.connected_main = set(res.routes)
        res.meta["on_existing_road_m"] = self._existing_road_length(lines)
        res.meta["new_construction_m"] = max(res.unique_length_m - res.meta["on_existing_road_m"], 0.0)
        res.meta["fine_status"] = status_count
        res.meta["coarse_cells"] = int(grid.H * grid.W)
        return res


def build_district_problem(d: DistrictInputs, cfg: dict) -> DistrictProblem:
    return DistrictProblem(d, cfg)


def load_config(path=None) -> dict:
    import yaml
    path = Path(path) if path else REPO / "configs" / "hierarchy_levels.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))
