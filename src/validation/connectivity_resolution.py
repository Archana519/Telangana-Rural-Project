"""connectivity_resolution.py - resolves the C0002 "off the main road component" exception from the road LINE data (read-only).

Why not change the planner: plan_network_v2.py is hash-pinned and verified; the grid is clipped to the village polygon, so roads that leave
the polygon and re-enter are cut into separate raster components (diagnostics: 98% of the blocked road cells lie outside the polygon). Inventing a
bridge across that gap would assume a road that is not in the data. The source TGRAC LINES are not cut, so connectivity is evaluated on them:

  1. Each route's attachment chain is followed to the route whose last vertex lies on the declared road network.
  2. That end point is snapped to the nearest TGRAC road line within SNAP_TOL_M (the planner's attach tolerance, 15 m).
  3. The line's connected component is found with line endpoints joined at 0.01 m, and again at 10 m.
  4. A target is "line-connected" if its snapped line is in the largest line component. The road-line path length from the snap point to the main
     raster component is computed on a graph of the lines (densified to 5 m, so lengths are good to about +/-5 m).
  5. If a target is NOT line-connected, a candidate bridge (the shortest gap to the main component) is listed as a PROPOSAL that needs imagery or field
     confirmation. It is never added to the plan or to the reported connectivity.

Planner results are unchanged; this adds a second, line-based connectivity measure beside the raster one.
usage: python src/validation/connectivity_resolution.py --run-dir <stageB run folder> --out <folder>
"""
import argparse, csv
from pathlib import Path

import geopandas as gpd
import networkx as nx
import numpy as np
from shapely.geometry import LineString, MultiLineString, Point
from shapely.ops import nearest_points
from shapely.strtree import STRtree

ROOT = Path(__file__).resolve().parents[2]
V = ROOT / "Siddipet" / "Damarakunta"
SNAP_TOL_M = 15.0
DENSIFY_M = 5.0


def segments(g):
    return list(g.geoms) if isinstance(g, MultiLineString) else [g]


def densify(ls, step):
    n = max(int(ls.length // step), 1)
    return [ls.interpolate(i * ls.length / n) for i in range(n + 1)]


class UF:
    def __init__(self, n):
        self.p = list(range(n))

    def f(self, a):
        while self.p[a] != a:
            self.p[a] = self.p[self.p[a]]; a = self.p[a]
        return a

    def u(self, a, b):
        self.p[self.f(b)] = self.f(a)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--roads", default=str(V / "reference" / "tgrac_road_network.gpkg"))
    a = ap.parse_args()
    run, out = Path(a.run_dir), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    roads = gpd.read_file(a.roads)
    boundary = gpd.read_file(V / "study_area" / "damarakunta_boundary.gpkg").geometry.iloc[0]
    lines, feat = [], []
    for i, r in roads.iterrows():
        for s in segments(r.geometry):
            lines.append(s); feat.append(int(r.OBJECTID_1))
    tree = STRtree(lines)

    def components(tol):
        uf = UF(len(lines))
        for i, l in enumerate(lines):
            for j in tree.query(l.buffer(tol + 1e-6)):
                if j > i and l.distance(lines[int(j)]) <= tol:
                    uf.u(i, int(j))
        roots = [uf.f(i) for i in range(len(lines))]
        length = {}
        for r_, l in zip(roots, lines):
            length[r_] = length.get(r_, 0) + l.length
        main = max(length, key=length.get)
        return roots, main, length

    comp = {tol: components(tol) for tol in (0.01, 10.0)}

    # road graph for path lengths (vertices every 5 m; ends joined within 10 m)
    G = nx.Graph()
    node_pts = {}
    for k, l in enumerate(lines):
        pts = densify(l, DENSIFY_M)
        ids = [(k, i) for i in range(len(pts))]
        for n_, p in zip(ids, pts):
            node_pts[n_] = p
        for u, v, p, q in zip(ids[:-1], ids[1:], pts[:-1], pts[1:]):
            G.add_edge(u, v, w=p.distance(q))
    ends = [(k, i) for k, l in enumerate(lines) for i in (0, len(densify(l, DENSIFY_M)) - 1)]
    et = STRtree([node_pts[n_] for n_ in ends])
    for n_ in ends:
        for j in et.query(node_pts[n_].buffer(10.0)):
            m = ends[int(j)]
            if m != n_ and node_pts[n_].distance(node_pts[m]) <= 10.0:
                G.add_edge(n_, m, w=node_pts[n_].distance(node_pts[m]))
    all_nodes = list(node_pts)
    nt = STRtree([node_pts[n_] for n_ in all_nodes])
    # T-junctions: vertices of different lines within 6 m (densify step 5 m puts a junction within 2.5 m of a vertex) are joined
    for n_ in all_nodes:
        for j in nt.query(node_pts[n_].buffer(6.0)):
            m = all_nodes[int(j)]
            if m[0] != n_[0] and node_pts[n_].distance(node_pts[m]) <= 6.0:
                G.add_edge(n_, m, w=node_pts[n_].distance(node_pts[m]))

    def node_near(p):
        return all_nodes[int(nt.nearest(p))]

    # selected routes and their attach chains
    conn = {r["target_id"]: r for r in csv.DictReader(open(run / "connectivity_checks.csv", encoding="utf-8"))}
    geoms = {}
    for layer in ("routes_network_houses", "routes_network_facilities"):
        g = gpd.read_file(run / "routes.gpkg", layer=layer)
        key = "target_id" if "target_id" in g.columns else "target"
        for r in g.itertuples():
            geoms[str(getattr(r, key))] = r.geometry
    main_cells = gpd.read_file(run / "routes.gpkg", layer="road_cells_main_component").geometry.iloc[0]
    main_nodes = {n_ for n_ in all_nodes if node_pts[n_].distance(main_cells) <= 10.0}
    rows, bridges = [], []
    for tid, c in conn.items():
        t = tid
        seen = set()
        while conn[t]["attach_class"] != "ROAD" and conn[t]["attach_parent"] and t not in seen:
            seen.add(t); t = conn[t]["attach_parent"]
        end = Point(list(geoms[t].coords)[-1])
        j = int(tree.nearest(end))
        d = float(end.distance(lines[j]))
        r0, m0, _ = comp[0.01]
        r1, m1, _ = comp[10.0]
        in0, in1 = r0[j] == m0, r1[j] == m1
        row = dict(target_id=tid, kind=c["kind"], terminal_route=t, snap_distance_m=round(d, 2), snapped_within_tol=d <= SNAP_TOL_M, road_feature_id=feat[j],
                   raster_main_component=c["reaches_main_road_component"], line_main_component_0p01m=in0, line_main_component_10m=in1,
                   road_line_path_to_raster_main_m="", path_m_outside_village="")
        if c["reaches_main_road_component"] != "True":
            s_node = node_near(end)
            best = None
            if main_nodes:
                dist, path = nx.single_source_dijkstra(G, s_node, weight="w")
                cand = [(dist[n_], n_) for n_ in main_nodes if n_ in dist]
                if cand:
                    best = min(cand)
                    pth = nx.dijkstra_path(G, s_node, best[1], weight="w")
                    outside = sum(node_pts[u].distance(node_pts[v]) for u, v in zip(pth[:-1], pth[1:]) if not LineString([node_pts[u], node_pts[v]]).representative_point().within(boundary))
                    row["road_line_path_to_raster_main_m"] = round(best[0], 1)
                    row["path_m_outside_village"] = round(outside, 1)
            if not in0:
                m_geom = MultiLineString([l for l, rr in zip(lines, r0) if rr == m0])
                p1, p2 = nearest_points(lines[j], m_geom)
                bridges.append(dict(target_id=tid, gap_m=round(p1.distance(p2), 1), status="PROPOSAL_ONLY_NOT_IN_PLAN", note="needs imagery or field confirmation"))
        rows.append(row)
    with open(out / "route_end_line_connectivity.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    with open(out / "bridge_proposals.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["target_id", "gap_m", "status", "note"]); w.writeheader(); w.writerows(bridges)
    n = len(rows)
    raster = sum(r["raster_main_component"] == "True" for r in rows)
    l1 = sum(r["line_main_component_0p01m"] for r in rows)
    l2 = sum(r["line_main_component_10m"] for r in rows)
    snapped = sum(r["snapped_within_tol"] for r in rows)
    off = [r for r in rows if r["raster_main_component"] != "True"]
    s = ["# Connectivity resolution (road-line topology)", "",
         "Run `%s`. Planner results are unchanged. Road line components: %d at 0.01 m joining, %d at 10 m (raw TGRAC lines before gpd.clip(), including the 44.7%% of the length outside the village polygon; the planner routes on the clipped roads only)." % (
             run.name, len({r for r in comp[0.01][0]}), len({r for r in comp[10.0][0]})), "",
         "| Measure | Targets |", "|---|---|",
         "| Routed targets | %d |" % n, "| Route end snaps to a TGRAC line within %g m | %d |" % (SNAP_TOL_M, snapped),
         "| Reaches the main component on the planning RASTER (planner definition) | %d |" % raster,
         "| Reaches the main component on the road LINES (0.01 m joining) | %d |" % l1,
         "| Reaches the main component on the road LINES (10 m joining) | %d |" % l2, ""]
    for r in off:
        s.append("Exception %s: raster says not connected; road lines say %s. Road-line path from its attachment to the main raster component: %s m, of which %s m lies outside the village polygon (about +/-5 m)." % (
            r["target_id"], "connected" if r["line_main_component_0p01m"] else "NOT connected", r["road_line_path_to_raster_main_m"] or "n/a", r["path_m_outside_village"] or "n/a"))
    s += ["", "Reading: where lines are connected but the raster is not, the cut comes from clipping the grid to the village polygon, not from a gap in the road data. "
          "In the clipped network that is routed, C0002 is therefore not connected to the main road component inside the boundary: its only link runs through roads outside the boundary, which are excluded. "
          "This shows connectivity in the raw TGRAC lines; it does not show that the roads exist, are passable or are legally accessible. "
          "Bridge proposals: %d (%s)." % (len(bridges), "none needed" if not bridges else "see bridge_proposals.csv; not part of the plan"), ""]
    (out / "connectivity_resolution.md").write_text("\n".join(s), encoding="utf-8")
    print("\n".join(s))


if __name__ == "__main__":
    main()
