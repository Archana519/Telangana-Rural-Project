"""audit_road_connectivity.py - READ-ONLY, standalone geometric connectivity audit (auxiliary; NOT the planner).

PROPOSED FOR REVIEW. Does not import or run the planner, the V4 reconstruction script or any other project stage.

READS (read-only, hashed before and after):
  reference roads (.gpkg, layer tgrac_road_network)         geometry only
  access_assessment.gpkg                                     layers candidate_access, clusters, facility_access
  per run <runs-root>/<run>/network_v2.gpkg                  layers targets, routes_network_aware, routes_independent
  per run <runs-root>/<run>/summary.json                     params (attach_tol_m, paths)
  ESA WorldCover raster (aligned)                            NoData footprint only (coverage flag; never changes a distance)
WRITES (new folder <out-root>/<tag>; refused if it exists and is non-empty; nothing outside it is written):
  road_graph_tolerance_sweep.csv  road_components.csv  road_near_gaps.csv  road_junctions.csv
  candidate_connectivity.csv  route_connectivity.csv  facility_connectivity.csv  summary_by_group.csv
  checks.csv  data_dictionary.csv  connectivity_audit.gpkg  connectivity_audit_report.txt
  connectivity_audit_summary.json  input_integrity.json  manifest.csv
Exit codes: 0 = completed (read checks.csv for FLAG / DIFFERS_FROM_PRIOR rows); 1 = refused or failed (input problem, a FAIL check,
or an error); 2 = an input changed during the run (report INVALID, INPUT_CHANGED_REPORT_INVALID.txt written).

WHAT IT MEASURES: (a) the reference-road graph and its components at several tolerances; (b) PROXIMITY of candidate polygons and facility
points to roads; (c) GEOMETRIC attachment of proposed route terminals to roads and to other routes.
WHAT IT DOES NOT ESTABLISH: physical passability, legal access, land ownership, ground-truth road status, true junctions, bridges,
overpasses, road width, building truth, or any monetary cost. A geometric touch or an endpoint within a tolerance is not proof of a
valid or traversable connection.

DESIGN RULES (documented, deterministic):
 * Road segments = LineString parts of the road layer (multi-part features are exploded; parts are separate segments).
 * Intersection classes between two segments (tolerance 0 = exact geometric contact, numerical epsilon 1e-6 m):
     ENDPOINT_ENDPOINT, T_JUNCTION (an endpoint touches the other line), CROSSING_SHARED_VERTEX (both lines have a vertex there),
     OVERLAP_COLLINEAR, CROSSING_NO_SHARED_VERTEX (lines cross with no vertex in common).
 * Junction policy  assume_junction (headline, default): every class connects (a crossing without a shared vertex is an ASSUMED junction);
                    explicit_only (sensitivity): CROSSING_NO_SHARED_VERTEX does not connect (could be an overpass or tunnel).
 * Tolerance bridges (tolerance > 0) are INFERRED, never original connections, and follow one rule: a DANGLING endpoint P may be bridged
   to the nearest point Q of another segment if |PQ| <= tolerance AND the bridge direction lies within --bridge-max-angle-deg (45 deg)
   of the outward tangent of P's segment (last 5 m). Parallel lines that merely lie close do not satisfy the direction test.
 * Main component = largest connected component by TOTAL GEOMETRIC LENGTH (a proxy, not proof of the wider network).
 * Polygon distance = shapely distance from the filled polygon to the road geometry (0 if they intersect or a road lies inside it);
   the boundary-ring distance and the representative-point distance are computed INDEPENDENTLY. No ordering between them is assumed.
 * Distances are rounded to 0.01 m before a threshold comparison (the stored dist_to_ref_road_m is rounded the same way).
 * Route terminal = the end of the route that is NOT the target start point (orientation verified against the targets layer).
   Attachment options at tolerance t: ROAD if terminal<=t from any road, and every other route within t of the terminal.
   Deterministic hop: ROAD first, else nearest route (tie: smaller key). More than one option within t => flagged AMBIGUOUS.
   Chain outcomes: ROAD_MAIN, ROAD_MINOR, CYCLE, DEAD_END, UNEVALUABLE. The bottleneck (minimax) tolerance to the main component is
   computed over all options, so it does not depend on the deterministic hop.
"""
import argparse
import datetime as dt
import hashlib
import importlib.metadata as md
import json
import math
import os
import platform
import sys
import warnings
from collections import OrderedDict
from pathlib import Path

warnings.filterwarnings("ignore", message="DataFrame is highly fragmented")
_MISSING = []
for _mod, _pip in (("numpy", "numpy"), ("pandas", "pandas"), ("geopandas", "geopandas"), ("shapely", "shapely>=2"),
                   ("networkx", "networkx"), ("rasterio", "rasterio")):
    try:
        __import__(_mod)
    except Exception:
        _MISSING.append(_pip)
if _MISSING:
    sys.exit("ERROR: missing Python packages: " + ", ".join(_MISSING) + "\nInstall (only after you approve):  pip install " + " ".join(_MISSING))

import geopandas as gpd
import networkx as nx
import numpy as np
import pandas as pd
import rasterio
import shapely
from rasterio.features import rasterize
from shapely.geometry import LineString, MultiLineString, Point, box
from shapely.ops import nearest_points

if int(shapely.__version__.split(".")[0]) < 2:
    sys.exit("ERROR: Shapely >= 2.0 is required (found %s). Install (only after you approve):  pip install \"shapely>=2\"" % shapely.__version__)

SCRIPT_VERSION = "audit_road_connectivity v1 (proposed)"
EPS = 1e-6
EXPECTED_EPSG = 32644
TOLERANCES = [0.0, 1.0, 2.0, 5.0, 10.0, 15.0]
THRESHOLDS = [25.0, 50.0, 100.0]
HEADLINE_THRESHOLD = 50.0
POLICIES = ("assume_junction", "explicit_only")
HEADLINE_POLICY = "assume_junction"
SCENARIOS = ("network_aware", "independent")
SCEN_LAYER = {"network_aware": "routes_network_aware", "independent": "routes_independent"}
ROADS_LAYER_DEFAULT = "tgrac_road_network"
ACCESS_REQUIRED = {
    "candidate_access": ["cand_id", "cluster_id", "gap_flag", "quality_class", "dist_to_ref_road_m", "est_roofs", "flags"],
    "clusters": ["cluster_id", "gap_flag", "kind", "n_candidates"],
    "facility_access": ["facility_id", "facility_name", "facility_type", "dist_to_ref_road_m"],
}
RUN_REQUIRED = {"targets": ["id", "kind"], "routes_network_aware": ["target"], "routes_independent": ["target"]}
CAND_OPTIONAL = ["building_id", "instance_id", "area_m2", "inside_village", "nearest_m", "neck_ratio"]
FAC_OPTIONAL = ["priority_group", "source", "source_file"]

# Figures reported in EARLIER work. They are comparison targets only; nothing in the audit is tuned to them.
PRIOR_REPORTED = OrderedDict([
    ("road_components_t0", 7), ("route_terminals_on_main", 54), ("candidates_total", 163), ("facilities_total", 4),
    ("baseline_within50_polygon", 103), ("run5_within50_polygon", 118), ("run6_slope_soft_within50_polygon", 120),
    ("run5_gap_cluster_polygons", 16), ("run5_gap_cluster_within50_point", 11), ("run5_gap_cluster_within50_polygon", 12)])

NOT_ESTABLISHED = ("Physical passability, legal access, land ownership, road condition and ground-truth road status are NOT established by this audit. "
                   "Everything here is geometry of unverified layers: proximity is not connectivity, a tolerance-based connection is an inference, "
                   "and a route terminal near a road or another route is not proof of a valid or traversable connection.")
LIMITATIONS = [
    NOT_ESTABLISHED,
    "The main component is the largest road component by total geometric length. It is a proxy, not proof that it represents the official wider road network.",
    "Crossings without a shared vertex are counted as ASSUMED junctions under the headline policy; the data cannot distinguish overpasses, bridges or tunnels. The explicit_only policy is reported as a sensitivity.",
    "Tolerance bridges are inferred from dangling endpoints and a direction test; they are not original road connections and the tolerance values are not field-validated.",
    "The reference road layer may omit village lanes; a polygon far from a mapped road may still have unmapped access, and a polygon near a mapped road may not.",
    "est_roofs is a model-derived proxy (area / reference roof area), not a verified house count. UNRESOLVED_MERGE polygons are settlement extents; they are reported separately and are not removed.",
    "Routes start at their target point, so the targeted polygon/facility is close to its own route by construction. That is not independent evidence of improved access; use the spillover columns.",
    "Stored attach_to and connected fields are claims written by the planner. They are compared with independent geometry and never used as evidence.",
    "WorldCover NoData is a raster-coverage flag. It never changes a distance; a feature inside the NoData footprint has less evidence behind its land-cover context, nothing more.",
    "Routing cost units are not money and no cost is computed here. Slope units/source and WorldCover version are not established by this audit.",
    "Few runs and 163 polygons: counts are descriptive; nothing here is a significance test or an accuracy claim.",
]


class AuditError(Exception):
    pass


# --------------------------------------------------------------------------------------------------------------------- utils
def sha256_file(p, blk=1 << 20):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(blk), b""):
            h.update(b)
    return h.hexdigest()


def file_state(p):
    p = str(p)
    if not os.path.isfile(p):
        return dict(path=p, exists=False, size=None, mtime_ns=None, sha256=None)
    st = os.stat(p)
    return dict(path=p, exists=True, size=st.st_size, mtime_ns=st.st_mtime_ns, sha256=sha256_file(p))


def sidecars(p):
    d, n = os.path.dirname(os.path.abspath(p)), os.path.basename(p)
    return sorted(f for f in os.listdir(d) if f.startswith(n) and f != n)


def dir_listing(d):
    out = []
    for r, _, fs in os.walk(str(d)):
        for f in sorted(fs):
            fp = os.path.join(r, f)
            st = os.stat(fp)
            out.append([os.path.relpath(fp, str(d)), st.st_size, st.st_mtime_ns])
    return sorted(out)


def snapshot(paths, run_dirs):
    return dict(files=OrderedDict((p, file_state(p)) for p in paths),
                sidecars=OrderedDict((p, sidecars(p)) for p in paths if os.path.isfile(p)),
                run_dirs=OrderedDict((k, dir_listing(v)) for k, v in run_dirs.items()))


def compare_snapshots(a, b):
    """Return (content_changes, touch_only_notes)."""
    changes, notes = [], []
    for p, sa in a["files"].items():
        sb = b["files"].get(p)
        if sb is None or sa["sha256"] != sb["sha256"] or sa["size"] != sb["size"]:
            changes.append(f"content changed: {p}")
        elif sa["mtime_ns"] != sb["mtime_ns"]:
            notes.append(f"mtime changed but content identical: {p}")
        if a["sidecars"].get(p) != b["sidecars"].get(p):
            changes.append(f"sidecar files changed next to: {p}")
    for k, la in a["run_dirs"].items():
        lb = b["run_dirs"].get(k)
        if [x[:2] for x in la] != [x[:2] for x in (lb or [])]:
            changes.append(f"run folder listing (names/sizes) changed: {k}")
    return changes, notes


def resolve_path(p, project_root):
    if not p:
        return None
    p = str(p)
    for cand in (p, os.path.abspath(p), os.path.join(str(project_root), p)):
        if os.path.exists(cand):
            return cand
    return p


def to_bool(s):
    if s.dtype == bool:
        return s
    return s.astype(str).str.strip().str.lower().isin(["true", "1", "yes", "1.0"])


def lib_versions():
    v = OrderedDict(python=sys.version.split()[0], platform=platform.platform())
    for m in ("geopandas", "shapely", "networkx", "rasterio", "pandas", "numpy", "pyogrio", "fiona", "pyproj"):
        try:
            v[m] = md.version(m)
        except Exception:
            v[m] = "not installed"
    return v


def r2(x):
    return None if x is None or (isinstance(x, float) and not math.isfinite(x)) else round(float(x), 2)


class Checks:
    STATUSES = ("PASS", "FAIL", "INFO", "FLAG", "UNAVAILABLE", "MATCHES_PRIOR", "DIFFERS_FROM_PRIOR")

    def __init__(self):
        self.rows = []

    def add(self, cid, desc, status, observed="", expected="", detail=""):
        assert status in self.STATUSES, status
        self.rows.append(OrderedDict(check_id=cid, description=desc, status=status, observed=str(observed), expected=str(expected), detail=str(detail)))

    def count(self, status):
        return sum(1 for r in self.rows if r["status"] == status)


def read_layer(path, layer, required, label):
    try:
        df = gpd.read_file(path, layer=layer)
    except Exception as e:
        raise AuditError(f"cannot read layer '{layer}' from {path} ({label}): {e}")
    miss = [c for c in required if c not in df.columns]
    if miss:
        raise AuditError(f"{label}: layer '{layer}' lacks required columns {miss}; it has {list(df.columns)}")
    return df


def require_crs(df, name, epsg):
    ep = df.crs.to_epsg() if df.crs is not None else None
    if ep != epsg:
        raise AuditError(f"{name}: CRS is EPSG:{ep}, expected EPSG:{epsg}")


# --------------------------------------------------------------------------------------------------------------------- geometry QA
def prep_polygon(g):
    """-> (geometry or None, status). Never raises."""
    try:
        if g is None or g.is_empty:
            return None, "EMPTY_GEOMETRY"
        if g.geom_type not in ("Polygon", "MultiPolygon"):
            return None, "NOT_POLYGON:" + g.geom_type
        g = shapely.force_2d(g)
        if g.is_valid:
            return g, "OK"
        fixed = shapely.make_valid(g)
        parts = [p for p in shapely.get_parts(fixed) if p.geom_type in ("Polygon", "MultiPolygon") and not p.is_empty]
        if not parts:
            return None, "INVALID_UNREPAIRABLE"
        return shapely.union_all(parts), "INVALID_REPAIRED"
    except Exception as e:  # defensive: a bad geometry must not crash the audit
        return None, "GEOMETRY_ERROR:" + type(e).__name__


def prep_point(g):
    try:
        if g is None or g.is_empty:
            return None, "EMPTY_GEOMETRY"
        if g.geom_type != "Point":
            return None, "NOT_POINT:" + g.geom_type
        return shapely.force_2d(g), "OK"
    except Exception as e:
        return None, "GEOMETRY_ERROR:" + type(e).__name__


def prep_line(g):
    try:
        if g is None or g.is_empty:
            return None, "EMPTY_GEOMETRY"
        g = shapely.force_2d(g)
        if g.geom_type == "MultiLineString":
            m = shapely.line_merge(g)
            if m.geom_type == "LineString":
                g = m
            else:
                return None, "MULTIPART_NOT_SINGLE_LINE"
        if g.geom_type != "LineString":
            return None, "NOT_LINE:" + g.geom_type
        if len(g.coords) < 2 or g.length <= EPS:
            return None, "ZERO_LENGTH"
        return g, "OK"
    except Exception as e:
        return None, "GEOMETRY_ERROR:" + type(e).__name__


# --------------------------------------------------------------------------------------------------------------------- road graph
def build_segments(gdf):
    segs, issues = [], []
    for row_i, g in enumerate(gdf.geometry):
        if g is None or g.is_empty:
            issues.append(dict(src_row=row_i, issue="EMPTY_GEOMETRY"))
            continue
        g = shapely.force_2d(g)
        if g.geom_type == "LineString":
            parts = [g]
        elif g.geom_type == "MultiLineString":
            parts = list(g.geoms)
        else:
            issues.append(dict(src_row=row_i, issue="NOT_LINE:" + g.geom_type))
            continue
        for k, p in enumerate(parts):
            if p.is_empty or len(p.coords) < 2 or p.length <= EPS:
                issues.append(dict(src_row=row_i, issue="ZERO_LENGTH_PART"))
                continue
            segs.append(dict(seg_id=len(segs), src_row=row_i, part=k, geom=p, length_m=float(p.length)))
    return segs, issues


def _is_end(line, x, y):
    c = line.coords
    return math.hypot(c[0][0] - x, c[0][1] - y) <= EPS or math.hypot(c[-1][0] - x, c[-1][1] - y) <= EPS


def _is_vertex(line, x, y):
    return any(math.hypot(cx - x, cy - y) <= EPS for cx, cy in line.coords)


KIND_EVIDENCE = {
    "ENDPOINT_ENDPOINT": "OBSERVED_SHARED_ENDPOINT", "T_JUNCTION": "OBSERVED_ENDPOINT_ON_LINE",
    "CROSSING_SHARED_VERTEX": "OBSERVED_SHARED_INTERIOR_VERTEX", "OVERLAP_COLLINEAR": "OBSERVED_COLLINEAR_OVERLAP",
    "CROSSING_NO_SHARED_VERTEX": "ASSUMED_JUNCTION_GEOMETRIC_CROSSING"}
CONNECTS = {"assume_junction": lambda k: True, "explicit_only": lambda k: k != "CROSSING_NO_SHARED_VERTEX"}


def analyse_junctions(segs):
    geoms = [s["geom"] for s in segs]
    tree = shapely.STRtree(geoms)
    rows = []
    for i, a in enumerate(geoms):
        minx, miny, maxx, maxy = a.bounds
        for j in sorted(int(x) for x in tree.query(box(minx - EPS, miny - EPS, maxx + EPS, maxy + EPS))):
            if j <= i:
                continue
            b = geoms[j]
            if a.distance(b) > EPS:
                continue
            pts, overlap = [], 0.0

            def collect(g):
                nonlocal overlap
                if g.is_empty:
                    return
                t = g.geom_type
                if t == "Point":
                    pts.append((g.x, g.y, False))
                elif t == "LineString":
                    overlap += g.length
                    pts.append((g.coords[0][0], g.coords[0][1], True))
                    pts.append((g.coords[-1][0], g.coords[-1][1], True))
                else:
                    for h in g.geoms:
                        collect(h)
            inter = a.intersection(b)
            collect(inter)
            if not pts:  # within epsilon but not exactly touching
                pa, _ = nearest_points(a, b)
                pts.append((pa.x, pa.y, False))
            seen = set()
            for x, y, lin in pts:
                key = (round(x, 5), round(y, 5))
                if key in seen:
                    continue
                seen.add(key)
                ea, eb = _is_end(a, x, y), _is_end(b, x, y)
                if lin:
                    kind = "OVERLAP_COLLINEAR"
                elif ea and eb:
                    kind = "ENDPOINT_ENDPOINT"
                elif ea or eb:
                    kind = "T_JUNCTION"
                elif _is_vertex(a, x, y) and _is_vertex(b, x, y):
                    kind = "CROSSING_SHARED_VERTEX"
                else:
                    kind = "CROSSING_NO_SHARED_VERTEX"
                rows.append(dict(seg_a=i, seg_b=j, kind=kind, evidence_class=KIND_EVIDENCE[kind], x=x, y=y,
                                 overlap_len_m=overlap if lin else 0.0,
                                 connects_assume_junction=CONNECTS["assume_junction"](kind), connects_explicit_only=CONNECTS["explicit_only"](kind)))
    return rows


def find_dangling(segs, junction_rows):
    """Dangling = an endpoint (of a non-closed segment) that no other segment touches (exact contact, epsilon 1e-6 m)."""
    geoms = [s["geom"] for s in segs]
    touched = set()
    for r in junction_rows:
        for sid in (r["seg_a"], r["seg_b"]):
            line = geoms[sid]
            c = line.coords
            for which, (cx, cy) in (("S", c[0]), ("E", c[-1])):
                if math.hypot(cx - r["x"], cy - r["y"]) <= EPS:
                    touched.add((sid, which))
    ends = []
    for s in segs:
        c = s["geom"].coords
        closed = math.hypot(c[0][0] - c[-1][0], c[0][1] - c[-1][1]) <= EPS
        for which, (cx, cy) in (("S", c[0]), ("E", c[-1])):
            ends.append(dict(end_id=f"{s['seg_id']}:{which}", seg_id=s["seg_id"], which=which, x=cx, y=cy,
                             dangling=(not closed) and ((s["seg_id"], which) not in touched)))
    return ends


def outward_tangent(line, which, back_m=5.0):
    L = line.length
    b = min(back_m, L)
    if which == "S":
        p, q = line.coords[0], line.interpolate(b).coords[0]
    else:
        p, q = line.coords[-1], line.interpolate(L - b).coords[0]
    v = np.array([p[0] - q[0], p[1] - q[1]], float)
    n = np.linalg.norm(v)
    return v / n if n > 0 else None


def bridge_candidates(segs, ends, tmax, max_angle_deg):
    geoms = [s["geom"] for s in segs]
    arr = np.array(geoms, dtype=object)
    dang = [e for e in ends if e["dangling"]]
    dang_at = {}
    for e in dang:
        dang_at.setdefault(e["seg_id"], []).append(e)
    out = []
    for e in dang:
        P = Point(e["x"], e["y"])
        d = shapely.distance(P, arr)
        tan = outward_tangent(geoms[e["seg_id"]], e["which"])
        for j in np.argsort(d, kind="stable"):
            j = int(j)
            if d[j] > tmax + 1e-9:
                break
            if j == e["seg_id"]:
                continue
            Q = nearest_points(P, geoms[j])[1]
            v = np.array([Q.x - P.x, Q.y - P.y], float)
            nv = np.linalg.norm(v)
            if tan is None or nv <= EPS:
                ang = float("nan")
                ok = False
            else:
                ang = float(math.degrees(math.acos(max(-1.0, min(1.0, float(np.dot(tan, v / nv)))))))
                ok = ang <= max_angle_deg + 1e-9
            q_end = None
            for e2 in dang_at.get(j, []):
                if math.hypot(e2["x"] - Q.x, e2["y"] - Q.y) <= EPS:
                    q_end = e2["end_id"]
            out.append(dict(end_id=e["end_id"], from_seg=e["seg_id"], to_seg=j, dist_m=float(d[j]), angle_deg=ang, direction_ok=bool(ok),
                            px=P.x, py=P.y, qx=Q.x, qy=Q.y, q_end_id=q_end))
    return out


class RoadModel:
    def __init__(self, gdf, tolerances, bridge_max_angle_deg, policy_headline=HEADLINE_POLICY):
        self.tolerances = list(tolerances)
        self.tmax = max(self.tolerances)
        self.headline = policy_headline
        self.segs, self.geom_issues = build_segments(gdf)
        if not self.segs:
            raise AuditError("the road layer contains no usable LineString segment")
        self.geoms = np.array([s["geom"] for s in self.segs], dtype=object)
        self.lengths = np.array([s["length_m"] for s in self.segs])
        self.junctions = analyse_junctions(self.segs)
        self.ends = find_dangling(self.segs, self.junctions)
        self.bridges = bridge_candidates(self.segs, self.ends, self.tmax, bridge_max_angle_deg)
        self.state = {}
        for pol in POLICIES:
            for t in self.tolerances:
                self.state[(pol, t)] = self._components(pol, t)

    def _graph(self, pol, t):
        G = nx.Graph()
        G.add_nodes_from(range(len(self.segs)))
        key = "connects_" + pol
        for r in self.junctions:
            if r[key]:
                G.add_edge(r["seg_a"], r["seg_b"], kind=r["kind"], inferred=False)
        if t > 0:
            for b in self.bridges:
                if b["direction_ok"] and b["dist_m"] <= t + 1e-9:
                    if not G.has_edge(b["from_seg"], b["to_seg"]):
                        G.add_edge(b["from_seg"], b["to_seg"], kind="INFERRED_TOLERANCE_BRIDGE", inferred=True)
        return G

    def _components(self, pol, t):
        G = self._graph(pol, t)
        comps = [sorted(c) for c in nx.connected_components(G)]
        comps.sort(key=lambda c: (-float(self.lengths[c].sum()), c[0]))
        seg2comp = np.zeros(len(self.segs), int)
        for k, c in enumerate(comps):
            seg2comp[c] = k
        lens = [float(self.lengths[c].sum()) for c in comps]
        tie = len(lens) > 1 and abs(lens[0] - lens[1]) <= 1e-9 * max(1.0, lens[0])
        resolved = set()
        for b in self.bridges:
            if b["direction_ok"] and t > 0 and b["dist_m"] <= t + 1e-9:
                resolved.add(b["end_id"])
                if b["q_end_id"]:
                    resolved.add(b["q_end_id"])
        n_dang = sum(1 for e in self.ends if e["dangling"] and e["end_id"] not in resolved)
        n_bridge_edges = sum(1 for _, _, d in G.edges(data=True) if d.get("inferred"))
        return dict(comps=comps, seg2comp=seg2comp, lengths=lens, main_tie=tie, n_dangling=n_dang, n_bridge_edges=n_bridge_edges)

    def main_mask(self, pol=None, t=0.0):
        st = self.state[(pol or self.headline, t)]
        return st["seg2comp"] == 0

    def comp_ids(self, pol=None, t=0.0):
        return self.state[(pol or self.headline, t)]["seg2comp"]

    def nearest(self, geom, mask=None):
        d = shapely.distance(geom, self.geoms)
        if mask is not None:
            d = np.where(mask, d, np.inf)
        i = int(np.argmin(d))
        return float(d[i]), i

    def nearest_class(self, geom, t=0.0):
        """('main'|'minor'|'none', distance, nearest seg id, tie flag) using the headline policy at tolerance t."""
        if geom is None:
            return "none", float("nan"), None, False
        d = shapely.distance(geom, self.geoms)
        i = int(np.argmin(d))
        mask = self.main_mask(t=t)
        near = np.where(d <= d[i] + EPS)[0]
        cls_set = {bool(mask[k]) for k in near}
        cls = "main" if True in cls_set else "minor"
        return cls, float(d[i]), i, len(cls_set) > 1


# --------------------------------------------------------------------------------------------------------------------- WorldCover
class WorldCover:
    def __init__(self, path, epsg):
        self.path = path
        with rasterio.open(path) as ds:
            self.epsg = ds.crs.to_epsg() if ds.crs else None
            self.transform = ds.transform
            self.bounds = ds.bounds
            self.nodata = ds.nodata
            arr = ds.read(1)
        if self.epsg != epsg:
            raise AuditError(f"WorldCover raster CRS is EPSG:{self.epsg}, expected EPSG:{epsg}")
        self.shape = arr.shape
        self.nd = (arr == self.nodata) if self.nodata is not None else (arr == 0)
        self.rule = f"cells == nodata({self.nodata})" if self.nodata is not None else "no nodata tag: class 0 treated as NoData"
        self.extent = box(*self.bounds)

    def polygon_status(self, g):
        if g is None:
            return "UNEVALUABLE", False, 0, 0
        try:
            touched = rasterize([(g, 1)], out_shape=self.shape, transform=self.transform, all_touched=True, fill=0, dtype="uint8").astype(bool)
        except Exception:
            return "UNEVALUABLE", False, 0, 0
        n = int(touched.sum())
        if n == 0:
            return "OUTSIDE_EXTENT", False, 0, 0
        nn = int((touched & self.nd).sum())
        inside = self.extent.contains(g)
        if nn == 0:
            return ("FULL_VALID" if inside else "PARTIAL_OUTSIDE_EXTENT"), False, n, 0
        return ("ALL_NODATA" if nn == n else "PARTIAL_NODATA"), True, n, nn

    def point_status(self, g):
        if g is None:
            return "UNEVALUABLE", False
        col, row = (~self.transform) @ (g.x, g.y)
        r, c = int(math.floor(row)), int(math.floor(col))
        if r < 0 or c < 0 or r >= self.shape[0] or c >= self.shape[1]:
            return "OUTSIDE_EXTENT", False
        if self.nd[r, c]:
            return "NODATA", True
        return "VALID", False

    def line_share(self, g):
        if g is None:
            return float("nan"), "UNEVALUABLE"
        pts = shapely.get_coordinates(shapely.segmentize(g, 5.0))
        n = bad = 0
        for x, y in pts:
            n += 1
            st, nd = self.point_status(Point(x, y))
            bad += 1 if (nd or st == "OUTSIDE_EXTENT") else 0
        share = bad / n if n else float("nan")
        return share, ("FULL_VALID" if bad == 0 else ("ALL_NODATA_OR_OUTSIDE" if bad == n else "PARTIAL_NODATA_OR_OUTSIDE"))


# --------------------------------------------------------------------------------------------------------------------- candidates / facilities
def pt_cols(prefix, d_any, d_main, d_main_inf, thr):
    out = {}
    for t in thr:
        tl = f"{int(t)}" if float(t).is_integer() else f"{t:g}"
        out[f"{prefix}_any_le{tl}"] = bool(d_any is not None and not math.isnan(d_any) and round(d_any, 2) <= t)
        out[f"{prefix}_main_le{tl}"] = bool(d_main is not None and not math.isnan(d_main) and round(d_main, 2) <= t)
        out[f"{prefix}_maininf_le{tl}"] = bool(d_main_inf is not None and not math.isnan(d_main_inf) and round(d_main_inf, 2) <= t)
    return out


def tl(t):
    return f"{int(t)}" if float(t).is_integer() else f"{t:g}"


def proximity_class(d, thr):
    if d is None or math.isnan(d):
        return "UNEVALUABLE"
    d = round(d, 2)
    prev = None
    for t in thr:
        if d <= t:
            return f"<={tl(t)}" if prev is None else f">{tl(prev)}..<={tl(t)}"
        prev = t
    return f">{tl(thr[-1])}"


def evaluate_features(gdf, kind, road, wc, thr, contact_tol, tmax):
    """Per-feature road metrics for candidate polygons ('poly') or facility points ('point')."""
    rows, geoms = [], []
    main0 = road.main_mask(t=0.0)
    maininf = road.main_mask(t=tmax)
    for g0 in gdf.geometry:
        if kind == "poly":
            g, status = prep_polygon(g0)
        else:
            g, status = prep_point(g0)
        geoms.append(g)
        r = OrderedDict(geometry_status=status, unevaluable_reason="" if g is not None else status)
        if g is None:
            r.update(d_poly_any_m=np.nan, d_poly_main_m=np.nan, d_poly_minor_m=np.nan, d_poly_maininf_m=np.nan, d_boundary_any_m=np.nan,
                     d_point_any_m=np.nan, d_point_main_m=np.nan, d_point_maininf_m=np.nan, nearest_component_class="none", nearest_component_tie=False,
                     nearest_seg_id=None, wc_status="UNEVALUABLE", intersects_wc_nodata=False, wc_cells_total=0, wc_cells_nodata=0)
            rows.append(r)
            continue
        rep = g.representative_point() if kind == "poly" else g
        d_any, i_any = road.nearest(g)
        d_main = road.nearest(g, main0)[0]
        d_maininf = road.nearest(g, maininf)[0]
        d_minor = road.nearest(g, ~main0)[0] if (~main0).any() else float("inf")
        cls, _, _, tie = road.nearest_class(g, 0.0)
        p_any = road.nearest(rep)[0]
        p_main = road.nearest(rep, main0)[0]
        p_maininf = road.nearest(rep, maininf)[0]
        d_bound = road.nearest(g.boundary)[0] if kind == "poly" else d_any
        r.update(d_poly_any_m=d_any, d_poly_main_m=d_main, d_poly_minor_m=(d_minor if math.isfinite(d_minor) else np.nan), d_poly_maininf_m=d_maininf,
                 d_boundary_any_m=d_bound, d_point_any_m=p_any, d_point_main_m=p_main, d_point_maininf_m=p_maininf,
                 nearest_component_class=cls, nearest_component_tie=tie, nearest_seg_id=i_any)
        if kind == "poly":
            r["rep_point_x"], r["rep_point_y"] = rep.x, rep.y
        if wc is not None:
            if kind == "poly":
                st, nd, n, nn = wc.polygon_status(g)
                r.update(wc_status=st, intersects_wc_nodata=nd, wc_cells_total=n, wc_cells_nodata=nn)
            else:
                st, nd = wc.point_status(g)
                r.update(wc_status=st, intersects_wc_nodata=nd, wc_cells_total=1, wc_cells_nodata=int(nd))
        else:
            r.update(wc_status="UNAVAILABLE", intersects_wc_nodata=False, wc_cells_total=0, wc_cells_nodata=0)
        rows.append(r)
    df = pd.DataFrame(rows)
    df["contact_any_le_tol"] = df["d_poly_any_m"].round(2) <= contact_tol
    df["contact_main_le_tol"] = df["d_poly_main_m"].round(2) <= contact_tol
    df["contact_minor_le_tol"] = df["d_poly_minor_m"].round(2) <= contact_tol
    df["proximity_class_poly"] = [proximity_class(x, thr) for x in df["d_poly_any_m"]]
    for t in thr:
        k = tl(t)
        df[f"poly_any_le{k}"] = df["d_poly_any_m"].round(2) <= t
        df[f"poly_main_le{k}"] = df["d_poly_main_m"].round(2) <= t
        df[f"poly_maininf_le{k}"] = df["d_poly_maininf_m"].round(2) <= t
        df[f"point_any_le{k}"] = df["d_point_any_m"].round(2) <= t
        df[f"point_main_le{k}"] = df["d_point_main_m"].round(2) <= t
    def status(x):
        if x["unevaluable_reason"]:
            return "UNEVALUABLE"
        if x["contact_main_le_tol"]:
            return "CONTACT_MAIN_COMPONENT"
        if x["contact_minor_le_tol"]:
            return "CONTACT_MINOR_COMPONENT"
        return "NOT_ESTABLISHED_PROXIMITY_ONLY"
    df["connectivity_status"] = df.apply(status, axis=1)
    return df, geoms


# --------------------------------------------------------------------------------------------------------------------- routes
def eval_routes(run, scen, rgdf, tgdf, road, wc, tols, attach_tol, thr_near):
    """Return (long_df, static_df, objects). One entry per route row; geometry QA never raises."""
    main0 = road.main_mask(t=0.0)
    maininf = road.main_mask(t=road.tmax)
    tgt_info = {}
    tgt_pt = {}
    if tgdf is not None:
        for _, r in tgdf.iterrows():
            tgt_info[str(r["id"])] = str(r.get("kind", ""))
            if r.geometry is not None and not r.geometry.is_empty and r.geometry.geom_type == "Point":
                tgt_pt[str(r["id"])] = r.geometry
    recs = []
    seen = {}
    for idx, row in rgdf.reset_index(drop=True).iterrows():
        tid = str(row["target"])
        seen[tid] = seen.get(tid, 0) + 1
        key = tid if seen[tid] == 1 else f"{tid}#{seen[tid]}"
        g, st = prep_line(row.geometry)
        rec = dict(route_key=key, target=tid, target_kind=tgt_info.get(tid, ""), row_index=int(idx), geometry_status=st, geom=g,
                   stored_length_m=(float(row["length_m"]) if "length_m" in rgdf.columns and pd.notna(row.get("length_m")) else np.nan),
                   claimed_attach_to=("" if "attach_to" not in rgdf.columns or pd.isna(row.get("attach_to")) else str(row["attach_to"]).strip()),
                   claimed_connected=(None if "connected" not in rgdf.columns or pd.isna(row.get("connected")) else str(row["connected"]).strip().lower() in ("true", "1", "yes")),
                   route_status=("" if "route_status" not in rgdf.columns or pd.isna(row.get("route_status")) else str(row["route_status"])))
        recs.append(rec)
    keys = [r["route_key"] for r in recs]
    ok = [r for r in recs if r["geom"] is not None]
    for r in recs:
        r["orientation"] = "UNEVALUABLE"
        r["start_pt"] = r["term_pt"] = None
        if r["geom"] is None:
            continue
        c = r["geom"].coords
        a, b = Point(c[0]), Point(c[-1])
        tp = tgt_pt.get(r["target"])
        if tp is not None:
            da, db = a.distance(tp), b.distance(tp)
            if da <= 1.0 and db > 1.0:
                r.update(orientation="VERIFIED", start_pt=a, term_pt=b)
            elif db <= 1.0 and da > 1.0:
                r.update(orientation="VERIFIED_REVERSED", start_pt=b, term_pt=a)
            else:
                far = b if da <= db else a
                near = a if far is b else b
                r.update(orientation="UNVERIFIED_FARTHER_END_USED", start_pt=near, term_pt=far)
        else:
            r.update(orientation="UNVERIFIED_NO_TARGET_POINT_LAST_VERTEX_USED", start_pt=a, term_pt=b)
    for r in ok:
        T = r["term_pt"]
        r["d_road"], r["seg_road"] = road.nearest(T)
        r["d_main"] = road.nearest(T, main0)[0]
        r["d_maininf"] = road.nearest(T, maininf)[0]
        cls, _, _, tie = road.nearest_class(T, 0.0)
        r["road_cls"], r["road_tie"] = cls, tie
        r["d_start_road"] = road.nearest(r["start_pt"])[0]
        r["geom_min_dist_road"] = road.nearest(r["geom"])[0]
        r["geom_len"] = float(r["geom"].length)
        r["wc_share"], r["wc_status"] = (wc.line_share(r["geom"]) if wc is not None else (float("nan"), "UNAVAILABLE"))
        r["comps_within"] = {}
    D = {r["route_key"]: {} for r in ok}
    for r in ok:
        for q in ok:
            if q["route_key"] != r["route_key"]:
                D[r["route_key"]][q["route_key"]] = float(r["term_pt"].distance(q["geom"]))
    byk = {r["route_key"]: r for r in ok}

    def bottleneck(dkey):
        best = {k: byk[k][dkey] for k in byk}
        nxt = {k: "MAIN" for k in byk}
        for _ in range(len(byk) + 1):
            changed = False
            for k in sorted(byk):
                for j in sorted(byk):
                    if j == k:
                        continue
                    cand = max(D[k][j], best[j])
                    if cand < best[k] - 1e-12:
                        best[k], nxt[k], changed = cand, j, True
            if not changed:
                break
        chains = {}
        for k in byk:
            ch, cur, guard = [k], k, 0
            while nxt[cur] != "MAIN" and guard <= len(byk):
                cur = nxt[cur]
                ch.append(cur)
                guard += 1
            chains[k] = ">".join(ch) + ">MAIN"
        return best, chains
    bt, bchain = bottleneck("d_main")
    bti, bchain_i = bottleneck("d_maininf")
    rows = []
    out_objs = {}
    for t in tols:
        hop, outcome, chain_str, hops, gap_own, chain_max, ambig, chain_amb, n_opts = {}, {}, {}, {}, {}, {}, {}, {}, {}
        for k, r in byk.items():
            within = sorted([(D[k][j], j) for j in byk if j != k and D[k][j] <= t + 1e-9])
            road_ok = r["d_road"] <= t + 1e-9
            opts = (1 if road_ok else 0) + len(within)
            n_opts[k] = opts
            comps_near = set(int(c) for c in road.comp_ids(t=0.0)[shapely.distance(r["term_pt"], road.geoms) <= t + 1e-9]) if road_ok else set()
            ambig[k] = bool(opts >= 2 or len(comps_near) >= 2)
            if road_ok:
                hop[k] = "ROAD"
                gap_own[k] = r["d_road"]
            elif within:
                hop[k] = within[0][1]
                gap_own[k] = within[0][0]
            else:
                hop[k] = None
                gap_own[k] = float("nan")
        for k, r in byk.items():
            path, cur, seen_k, res = [k], k, {k}, None
            gaps = []
            chain_ambiguous = ambig[k]
            while True:
                h = hop[cur]
                if h is None:
                    res = "DEAD_END"
                    break
                gaps.append(gap_own[cur])
                if h == "ROAD":
                    res = "ROAD_" + byk[cur]["road_cls"].upper()
                    path.append("ROAD[" + byk[cur]["road_cls"] + "]")
                    break
                if h in seen_k:
                    res = "CYCLE"
                    path.append(h)
                    break
                path.append(h)
                seen_k.add(h)
                cur = h
                chain_ambiguous = chain_ambiguous or ambig[cur]
            outcome[k] = res
            chain_str[k] = ">".join(path)
            hops[k] = len(path) - 1
            chain_max[k] = max(gaps) if gaps else float("nan")
            chain_amb[k] = chain_ambiguous
        for rec in recs:
            k = rec["route_key"]
            row = OrderedDict(run=run, scenario=scen, route_key=k, target=rec["target"], target_kind=rec["target_kind"], tolerance_m=t,
                              geometry_status=rec["geometry_status"], orientation=rec["orientation"])
            if rec["geom"] is None:
                row.update(chain_outcome="UNEVALUABLE", unevaluable_reason=rec["geometry_status"])
                rows.append(row)
                continue
            r = byk[k]
            nearest_route = min(D[k], key=lambda j: (D[k][j], j)) if D[k] else ""
            row.update(
                unevaluable_reason="", route_length_m=r["geom_len"], stored_length_m=rec["stored_length_m"],
                terminal_x=r["term_pt"].x, terminal_y=r["term_pt"].y, start_x=r["start_pt"].x, start_y=r["start_pt"].y,
                start_to_road_m=r["d_start_road"], terminal_to_road_m=r["d_road"], terminal_to_main_m=r["d_main"], terminal_to_main_inferred_m=r["d_maininf"],
                terminal_nearest_road_class=r["road_cls"], terminal_nearest_class_tie=r["road_tie"],
                terminal_to_nearest_other_route_m=(D[k][nearest_route] if nearest_route else np.nan), nearest_other_route=nearest_route,
                route_geometry_min_dist_to_road_m=r["geom_min_dist_road"], route_intersects_road=bool(r["geom_min_dist_road"] <= EPS),
                n_attachment_options=n_opts[k], ambiguous_options=ambig[k], next_hop=("" if hop[k] is None else hop[k]),
                terminal_gap_m=gap_own[k], chain=chain_str[k], chain_hops=hops[k], chain_max_gap_m=chain_max[k], chain_ambiguous=chain_amb[k],
                chain_outcome=outcome[k], reaches_main_deterministic=(outcome[k] == "ROAD_MAIN"),
                reaches_main_any_resolution=bool(bt[k] <= t + 1e-9), reaches_any_road_deterministic=outcome[k].startswith("ROAD_"),
                min_tolerance_to_main_m=bt[k], bottleneck_chain=bchain[k], min_tolerance_to_main_inferred_m=bti[k],
                near_road_but_not_attached=(not outcome[k].startswith("ROAD_")) and r["geom_min_dist_road"] <= thr_near,
                wc_nodata_or_outside_share=r["wc_share"], wc_status=r["wc_status"],
                claimed_attach_to=rec["claimed_attach_to"], claimed_connected=rec["claimed_connected"], planner_route_status=rec["route_status"])
            # claim comparison is only meaningful at the planner's own attach tolerance
            if abs(t - attach_tol) < 1e-9:
                opts_ids = {j for _, j in sorted((D[k][j], j) for j in byk if j != k and D[k][j] <= t + 1e-9)}
                if r["d_road"] <= t + 1e-9:
                    opts_ids.add("ROAD")
                ca, cc = rec["claimed_attach_to"], rec["claimed_connected"]
                if not ca:
                    cmp_a = "NO_CLAIM"
                elif ca == row["next_hop"]:
                    cmp_a = "AGREE"
                elif ca in opts_ids:
                    cmp_a = "AGREE_WITHIN_AMBIGUOUS_OPTIONS"
                else:
                    cmp_a = "DISAGREE"
                if cc is None:
                    cmp_c = "NO_CLAIM"
                else:
                    cmp_c = "AGREE" if cc == row["reaches_any_road_deterministic"] else "DISAGREE"
                row.update(claim_attach_to_vs_independent=cmp_a, claim_connected_vs_independent=cmp_c)
            rows.append(row)
        out_objs[t] = dict(outcome=dict(outcome), hop=dict(hop))
    long_df = pd.DataFrame(rows)
    return long_df, recs, byk, out_objs


# --------------------------------------------------------------------------------------------------------------------- data dictionary
DICT_RULES = [
    ("cand_id", "Candidate polygon identifier from candidate_access.", "id", "n/a"),
    ("quality_class", "Extraction quality class stored with the polygon (PLAUSIBLE / REVIEW / UNRESOLVED_MERGE).", "label", "n/a"),
    ("est_roofs", "MODEL-DERIVED PROXY roof count (area / reference roof area). Not a verified house count.", "count (proxy)", "n/a"),
    ("d_poly_", "Distance from the filled polygon (or point) to the stated road set; 0 if they intersect or a road lies inside.", "metres", "per polygon"),
    ("d_boundary_any_m", "Distance from the polygon boundary ring only to any road (differs from the filled-polygon distance when a road lies inside).", "metres", "per polygon"),
    ("d_point_", "Distance from the representative point (a point guaranteed inside the polygon) to the stated road set. Computed independently of the polygon distance; no ordering is assumed.", "metres", "per polygon"),
    ("poly_any_le", "Polygon distance to ANY road <= threshold (rounded to 0.01 m). Proximity only.", "boolean", "denominator = evaluable polygons"),
    ("poly_main_le", "Polygon distance to the MAIN component (tolerance 0, headline policy) <= threshold. Proximity only.", "boolean", "evaluable polygons"),
    ("poly_maininf_le", "Polygon distance to the main component after inferred tolerance bridges at the largest tolerance <= threshold.", "boolean", "evaluable polygons"),
    ("point_any_le", "Representative-point distance to ANY road <= threshold.", "boolean", "evaluable polygons"),
    ("point_main_le", "Representative-point distance to the MAIN component <= threshold.", "boolean", "evaluable polygons"),
    ("contact_", "Polygon distance to the stated road set <= polygon-contact tolerance (default 1 m). A contact tolerance, not proof of access.", "boolean", "tolerance = contact_tol_m"),
    ("proximity_class_poly", "Class of the polygon distance to any road against the thresholds.", "label", "thresholds 25/50/100 m"),
    ("nearest_component_class", "Component class (main / minor / none) of the nearest road segment at tolerance 0, headline policy.", "label", "n/a"),
    ("nearest_component_tie", "True when equally-near segments belong to both main and minor components.", "boolean", "n/a"),
    ("connectivity_status", "CONTACT_MAIN_COMPONENT / CONTACT_MINOR_COMPONENT / NOT_ESTABLISHED_PROXIMITY_ONLY. Graph connectivity of the polygon is only 'established' as geometric contact within the contact tolerance.", "label", "contact tolerance"),
    ("wc_", "WorldCover coverage: status / count of raster cells touched by the footprint that are NoData. Coverage flag only; no distance depends on it.", "label / count", "raster cells"),
    ("intersects_wc_nodata", "Footprint touches at least one WorldCover NoData cell.", "boolean", "n/a"),
    ("geometry_status", "OK / INVALID_REPAIRED / EMPTY_GEOMETRY / INVALID_UNREPAIRABLE / NOT_POLYGON ...", "label", "n/a"),
    ("unevaluable_reason", "Empty when the feature was evaluated; otherwise why it could not be.", "label", "n/a"),
    ("cluster_", "Cluster attribute stored in the access assessment (kind, gap flag, size).", "label", "n/a"),
    ("gap_flag", "Stored flag: distance to road > gap threshold (50 m).", "boolean", "n/a"),
    ("flags", "Stored extraction flags.", "text", "n/a"),
    ("rep_point_", "Representative point coordinate (EPSG:32644).", "metres", "n/a"),
    ("tolerance_m", "Snapping / attachment tolerance in force on this row.", "metres", "n/a"),
    ("policy", "Junction policy: assume_junction (headline) or explicit_only (crossings without a shared vertex do not connect).", "label", "n/a"),
    ("n_components", "Number of connected road components.", "count", "road segments"),
    ("main_", "Main component (largest by total geometric length) properties.", "metres / %", "total road length"),
    ("total_length_m", "Sum of road segment lengths (geometric).", "metres", "n/a"),
    ("n_dangling_ends", "Dangling endpoints not resolved by a valid inferred bridge at this tolerance.", "count", "segment endpoints"),
    ("n_valid_bridges", "Candidate tolerance bridges that pass the distance and direction tests.", "count", "n/a"),
    ("n_assumed_junction_crossings", "Intersections of class CROSSING_NO_SHARED_VERTEX (assumed junctions).", "count", "segment pairs"),
    ("component_id", "Rank by length at tolerance 0 (1 = main).", "id", "n/a"),
    ("merged_into_main_at_", "Whole component belongs to the main component at that tolerance via exact + inferred connections.", "boolean", "tolerance in name"),
    ("length_m", "Geometric length.", "metres", "n/a"),
    ("share_of_total_pct", "Component length as percent of total road length.", "percent", "total road length"),
    ("dist_to_main_m", "Minimum distance from this component to the main component.", "metres", "n/a"),
    ("kind", "Junction class or feature kind.", "label", "n/a"),
    ("evidence_class", "OBSERVED_* (geometry shares a vertex/endpoint), ASSUMED_JUNCTION_* (crossing without a shared vertex), INFERRED_TOLERANCE_BRIDGE.", "label", "n/a"),
    ("connects_", "Whether this intersection connects the two segments under the named policy.", "boolean", "n/a"),
    ("end_id", "Segment endpoint id '<seg_id>:S|E'.", "id", "n/a"),
    ("dist_m", "Distance from the dangling endpoint to the nearest point of the other segment.", "metres", "n/a"),
    ("angle_deg", "Angle between the outward tangent of the dangling end and the bridge direction.", "degrees", "n/a"),
    ("direction_ok", "Angle test passed (<= bridge-max-angle).", "boolean", "n/a"),
    ("valid_bridge_at_max_tol", "Distance <= largest tolerance and direction test passed (an INFERRED connection, never original).", "boolean", "largest tolerance"),
    ("same_component_t0", "Both segments are already in the same component at tolerance 0.", "boolean", "n/a"),
    ("run", "Planner run folder name.", "label", "n/a"),
    ("scenario", "Route scenario: network_aware or independent.", "label", "n/a"),
    ("route_key", "Route identifier (target id; '#n' suffix if the target repeats in the layer).", "id", "n/a"),
    ("target", "Planner target id (F:<facility> or C<cluster>).", "id", "n/a"),
    ("orientation", "How the start (target) end of the route was identified from the targets layer.", "label", "n/a"),
    ("terminal_", "Route network-end (non-target end) position or distance, as named.", "metres", "n/a"),
    ("start_", "Route target-start position or distance (close to its own target BY CONSTRUCTION).", "metres", "n/a"),
    ("route_", "Route geometry property as named.", "metres / flag", "n/a"),
    ("stored_length_m", "length_m stored by the planner (claim; compared, not used).", "metres", "n/a"),
    ("n_attachment_options", "Number of attachment options within the tolerance (ROAD counts once, plus each route).", "count", "n/a"),
    ("ambiguous_options", "More than one attachment option or more than one road component within the tolerance.", "boolean", "tolerance_m"),
    ("next_hop", "Deterministic first hop: ROAD, a route key, or blank.", "label", "tolerance_m"),
    ("terminal_gap_m", "Distance of the first hop.", "metres", "tolerance_m"),
    ("chain", "Deterministic attachment chain from this route.", "text", "tolerance_m"),
    ("chain_", "Chain property as named (hops, largest gap, outcome, ambiguity).", "see name", "tolerance_m"),
    ("reaches_main_deterministic", "Deterministic chain ends at a road of the MAIN component (tolerance 0 components).", "boolean", "tolerance_m"),
    ("reaches_main_any_resolution", "Some resolution of the ambiguous options reaches the main component (bottleneck <= tolerance).", "boolean", "tolerance_m"),
    ("reaches_any_road_deterministic", "Deterministic chain ends at any road (the planner's own 'connected' notion).", "boolean", "tolerance_m"),
    ("min_tolerance_to_main", "Smallest tolerance at which some chain reaches the main component (minimax over all options).", "metres", "n/a"),
    ("bottleneck_chain", "Chain realising the minimax tolerance.", "text", "n/a"),
    ("near_road_but_not_attached", "Route geometry within the smallest proximity threshold of a road but its chain does not reach a road at this tolerance.", "boolean", "tolerance_m"),
    ("claimed_", "Value stored by the planner (a CLAIM, not evidence).", "as stored", "n/a"),
    ("claim_", "Stored claim vs independent geometry at the planner's attach tolerance (AGREE / DISAGREE / NO_CLAIM).", "label", "attach_tol_m"),
    ("planner_route_status", "route_status stored by the planner.", "label", "n/a"),
    ("facility_", "Facility attribute from facility_access.", "as stored", "n/a"),
    ("priority_group", "Facility priority group where stored.", "as stored", "n/a"),
    ("coord_status", "Target coordinate status written by the planner.", "label", "n/a"),
    ("route_present", "A route for this facility exists in the layer.", "boolean", "n/a"),
    ("start_in_polygon", "The route start point lies inside / within the contact tolerance of this polygon (proximity gain BY CONSTRUCTION).", "boolean", "contact_tol_m"),
    ("gain_class_", "BASELINE_WITHIN / BY_CONSTRUCTION / SPILLOVER / NOT_WITHIN at the headline threshold.", "label", "50 m"),
    ("roads_routes", "Distance or flag using roads UNION routes of that run/scenario. Proximity only.", "metres / boolean", "threshold in name"),
    ("roads_connroutes", "Distance or flag using roads UNION routes whose deterministic chain reaches the main component at the attach tolerance. Proximity only.", "metres / boolean", "threshold in name"),
    ("summary_id", "Section of the summary.", "label", "n/a"),
    ("group_type", "Grouping variable.", "label", "n/a"),
    ("group_value", "Group value.", "label", "n/a"),
    ("metric", "Metric name.", "label", "n/a"),
    ("threshold_or_tolerance_m", "Threshold / tolerance of the metric.", "metres", "n/a"),
    ("unit", "Unit of the numerator and denominator.", "label", "n/a"),
    ("numerator", "Count satisfying the metric.", "count", "see denominator"),
    ("denominator", "Count of evaluable members of the group.", "count", "n/a"),
    ("percent", "100 * numerator / denominator.", "percent", "n/a"),
    ("roofs_", "Sum of est_roofs (MODEL-DERIVED PROXY) over the numerator / denominator members. Not verified houses.", "roofs (proxy)", "n/a"),
    ("definition", "Plain-language metric definition.", "text", "n/a"),
    ("check_id", "Check identifier.", "id", "n/a"), ("description", "What is checked.", "text", "n/a"), ("status", "PASS / FAIL / INFO / FLAG / UNAVAILABLE / MATCHES_PRIOR / DIFFERS_FROM_PRIOR.", "label", "n/a"),
    ("observed", "Observed value.", "as stated", "n/a"), ("expected", "Expected / previously reported value (comparison only).", "as stated", "n/a"), ("detail", "Explanation.", "text", "n/a"),
    ("seg_", "Road segment id / source row / part.", "id", "n/a"), ("src_row", "Row in the source road layer.", "id", "n/a"), ("part", "Part index inside a multi-part feature.", "id", "n/a"),
    ("x", "X coordinate (EPSG:32644).", "metres", "n/a"), ("y", "Y coordinate (EPSG:32644).", "metres", "n/a"),
    ("overlap_len_m", "Length of collinear overlap.", "metres", "n/a"),
    ("dangling", "Endpoint touched by no other segment.", "boolean", "n/a"), ("which", "S = start, E = end of the segment.", "label", "n/a"),
    ("px", "Dangling end X.", "metres", "n/a"), ("py", "Dangling end Y.", "metres", "n/a"), ("qx", "Nearest point on other segment X.", "metres", "n/a"), ("qy", "Nearest point Y.", "metres", "n/a"),
    ("q_end_id", "Endpoint id of the other segment when Q coincides with one of its dangling ends.", "id", "n/a"), ("from_seg", "Segment owning the dangling end.", "id", "n/a"), ("to_seg", "Segment receiving the bridge.", "id", "n/a"),
    ("to_comp", "Component rank of the target segment at tolerance 0.", "id", "n/a"), ("from_comp", "Component rank of the dangling end's segment at tolerance 0.", "id", "n/a"),
    ("n_segments", "Number of road segments.", "count", "n/a"), ("n_merges", "Components merged relative to tolerance 0 at this tolerance.", "count", "n/a"),
    ("second_", "Second-largest component property.", "metres", "n/a"), ("n_inferred", "Inferred bridge edges in the graph.", "count", "n/a"), ("n_observed", "Observed intersections by class.", "count", "n/a"),
    ("main_tie", "Largest and second-largest components tie on length.", "boolean", "n/a"),
    ("file", "File name.", "text", "n/a"), ("bytes", "File size.", "bytes", "n/a"), ("sha256", "SHA-256.", "hex", "n/a"), ("column", "Column name.", "text", "n/a"),
    ("units", "Units.", "text", "n/a"), ("basis", "Denominator / basis.", "text", "n/a"), ("tolerance", "Tolerance in force.", "text", "n/a"),
    ("min_x", "Component bounding box minimum X (EPSG:32644).", "metres", "n/a"), ("min_y", "Component bounding box minimum Y.", "metres", "n/a"),
    ("max_x", "Component bounding box maximum X.", "metres", "n/a"), ("max_y", "Component bounding box maximum Y.", "metres", "n/a"),
    ("stored_dist_to_ref_road_m", "dist_to_ref_road_m stored by the access assessment (claim; recomputed independently, see checks).", "metres", "n/a"),
    ("nearest_other_route", "Route (same run/scenario) whose geometry is nearest to this route's terminal.", "id", "n/a"),
    ("within_", "Dangling-end bridge distance <= the tolerance in the column name (candidate INFERRED bridge; also requires direction_ok to count).", "boolean", "tolerance in name"),
    ("area_m2", "Polygon area stored by the extraction step (extract_buildings_v8), rounded to 0.01. Pass-through, not recomputed.", "m2", "per polygon"),
    ("inside_village", "Stored flag: the polygon's representative point lies inside the village boundary used at extraction. Pass-through.", "boolean", "per polygon"),
    ("nearest_m", "Stored distance to the nearest OTHER detected polygon at extraction (not to a road), rounded to 0.1 m. Pass-through.", "metres", "per polygon"),
    ("neck_ratio", "Value recorded by the distance-transform splitting step for the polygon; blank when none was recorded. Pass-through.", "ratio (dimensionless)", "per polygon"),
    ("source", "Source file name of the facility record as stored in facility_access. Pass-through.", "text", "per facility"),
    ("n_", "Count as named.", "count", "n/a"), ("is_main", "Component is the main component.", "boolean", "n/a"),
    ("terminals_", "Route terminals counted as named.", "count", "n/a"), ("routes_", "Routes counted as named.", "count", "n/a"),
]


def describe(col):
    for pat, d, u, den in DICT_RULES:
        if col == pat:
            return d, u, den
    best = None
    for pat, d, u, den in DICT_RULES:
        if col.startswith(pat) and (best is None or len(pat) > len(best[0])):
            best = (pat, d, u, den)
    if best:
        return best[1], best[2], best[3]
    for pat, d, u, den in DICT_RULES:
        if pat in col and len(pat) >= 4:
            return d, u, den
    return None


def data_dictionary(files):
    rows = []
    for fname, df in files.items():
        for c in df.columns:
            d = describe(c)
            if d is None:
                d = ("UNDOCUMENTED COLUMN", "", "")
            rows.append(OrderedDict(file=fname, column=c, definition=d[0], units=d[1], basis=d[2]))
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------------------------------------------------- summaries
def group_masks(c):
    yield "ALL", "ALL", pd.Series(True, index=c.index)
    for q in sorted(c["quality_class"].dropna().astype(str).unique()):
        yield "quality_class", q, c["quality_class"].astype(str) == q
    for k in sorted(c["cluster_kind"].dropna().astype(str).unique()):
        yield "cluster_kind", k, c["cluster_kind"].astype(str) == k
    for gflag in (True, False):
        yield "candidate_gap_flag", str(gflag), c["gap_flag"] == gflag
    for gflag in (True, False):
        yield "cluster_gap_flag", str(gflag), c["cluster_gap_flag"] == gflag
    for q in sorted(c["quality_class"].dropna().astype(str).unique()):
        for gflag in (True, False):
            yield "quality_class|candidate_gap_flag", f"{q}|{gflag}", (c["quality_class"].astype(str) == q) & (c["gap_flag"] == gflag)


def candidate_summary(c, metrics):
    rows = []
    ev = c["unevaluable_reason"] == ""
    for gtype, gval, m in group_masks(c):
        base = m & ev
        n_un = int((m & ~ev).sum())
        for (metric, run, scen, thr, col, definition) in metrics:
            num = base & c[col].fillna(False).astype(bool)
            roofs_n = float(c.loc[num, "est_roofs"].sum())
            roofs_d = float(c.loc[base, "est_roofs"].sum())
            rows.append(OrderedDict(summary_id="candidates", group_type=gtype, group_value=gval, run=run, scenario=scen, metric=metric,
                                    threshold_or_tolerance_m=thr, unit="polygons (denominator = evaluable polygons in group)", numerator=int(num.sum()), denominator=int(base.sum()),
                                    percent=(100.0 * num.sum() / base.sum()) if base.sum() else np.nan, roofs_numerator=roofs_n, roofs_denominator=roofs_d,
                                    roofs_percent=(100.0 * roofs_n / roofs_d) if roofs_d else np.nan, definition=definition))
        rows.append(OrderedDict(summary_id="candidates", group_type=gtype, group_value=gval, run="", scenario="", metric="unevaluable_polygons",
                                threshold_or_tolerance_m=np.nan, unit="polygons", numerator=n_un, denominator=int(m.sum()),
                                percent=(100.0 * n_un / m.sum()) if m.sum() else np.nan, roofs_numerator=float(c.loc[m & ~ev, "est_roofs"].sum()),
                                roofs_denominator=float(c.loc[m, "est_roofs"].sum()), roofs_percent=np.nan, definition="geometry could not be evaluated"))
    return rows


# --------------------------------------------------------------------------------------------------------------------- main
def parse_args(argv):
    here = Path(__file__).resolve().parent
    default_root = here.parent if here.name.lower() == "scripts" else here
    ap = argparse.ArgumentParser(description="READ-ONLY road / candidate / route geometric connectivity audit (auxiliary; not the planner).")
    ap.add_argument("--project-root", default=str(default_root))
    ap.add_argument("--runs-root", default=None, help="default: <root>/Siddipet/Damarakunta/results/planning_experiments/network_v2")
    ap.add_argument("--runs", nargs="+", default=["run5", "run6_slope_soft"])
    ap.add_argument("--out-root", default=None, help="default: <root>/Siddipet/Damarakunta/results/connectivity_audit_v1")
    ap.add_argument("--tag", default="ca1")
    ap.add_argument("--access-gpkg", default=None, help="default: path recorded in the first run's summary.json (params.access_gpkg)")
    ap.add_argument("--roads", default=None, help="default: path recorded in the first run's summary.json (params.roads)")
    ap.add_argument("--roads-layer", default=ROADS_LAYER_DEFAULT)
    ap.add_argument("--worldcover", default=None, help="default: path recorded in the first run's summary.json (params.worldcover)")
    ap.add_argument("--no-worldcover", action="store_true", help="skip the WorldCover coverage flag (wc_status = UNAVAILABLE)")
    ap.add_argument("--tolerances", type=float, nargs="+", default=TOLERANCES)
    ap.add_argument("--thresholds", type=float, nargs="+", default=THRESHOLDS)
    ap.add_argument("--headline-threshold", type=float, default=HEADLINE_THRESHOLD)
    ap.add_argument("--contact-tol-m", type=float, default=1.0, help="polygon-contact tolerance (default 1 m)")
    ap.add_argument("--attach-tol-m", type=float, default=None, help="default: params.attach_tol_m recorded in the run summaries")
    ap.add_argument("--bridge-max-angle-deg", type=float, default=45.0)
    ap.add_argument("--expected-epsg", type=int, default=EXPECTED_EPSG)
    ap.add_argument("--skip-prior-comparison", action="store_true")
    ap.add_argument("--polygon-dist-tol-m", type=float, default=0.011)
    return ap.parse_args(argv)


_HOOKS = {"after_processing": None, "before_processing": None}   # test hooks (mutation simulation); never used in a real run


def main(argv=None):
    try:
        return _run(argv)
    except AuditError as e:
        print("ERROR: " + str(e) + "\nNo normal audit outputs were written.", file=sys.stderr)
        return 1


def _run(argv):
    a = parse_args(argv)
    root = Path(a.project_root)
    area = root / "Siddipet" / "Damarakunta"
    runs_root = Path(a.runs_root) if a.runs_root else area / "results" / "planning_experiments" / "network_v2"
    out_root = Path(a.out_root) if a.out_root else area / "results" / "connectivity_audit_v1"
    out = out_root / a.tag
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        raise AuditError(f"{out} already exists and is not empty (or is not a folder); choose a new --tag. Nothing is overwritten.")
    tols = sorted(set(float(t) for t in a.tolerances) | {0.0})
    thr = sorted(set(float(t) for t in a.thresholds))
    chk = Checks()

    # ---- 1. runs, summaries, registry BEFORE any data use
    reg_paths, run_dirs, runs = [], OrderedDict(), OrderedDict()
    for rn in a.runs:
        rd = runs_root / rn
        if not rd.is_dir():
            raise AuditError(f"run folder not found: {rd}")
        gp, sj = rd / "network_v2.gpkg", rd / "summary.json"
        for p in (gp, sj):
            if not p.is_file():
                raise AuditError(f"missing run file: {p}")
        try:
            sm = json.loads(sj.read_text(encoding="utf-8"))
        except Exception as e:
            raise AuditError(f"cannot parse {sj}: {e}")
        runs[rn] = dict(dir=rd, gpkg=str(gp), summary=sm)
        reg_paths += [str(gp), str(sj)]
        run_dirs[rn] = rd
    first = next(iter(runs.values()))["summary"]
    params = first.get("params", {}) or {}
    access_p = resolve_path(a.access_gpkg or params.get("access_gpkg"), root)
    roads_p = resolve_path(a.roads or params.get("roads"), root)
    wc_p = None if a.no_worldcover else resolve_path(a.worldcover or params.get("worldcover"), root)
    for nm, p in (("access GeoPackage", access_p), ("roads file", roads_p)):
        if not p or not os.path.isfile(p):
            raise AuditError(f"{nm} not found: {p}")
    if not a.no_worldcover and (not wc_p or not os.path.isfile(wc_p)):
        raise AuditError(f"WorldCover raster not found: {wc_p} (give --worldcover or --no-worldcover)")
    reg_paths += [access_p, roads_p] + ([wc_p] if wc_p else [])
    tols_attach = []
    for rn, r in runs.items():
        v = (r["summary"].get("params", {}) or {}).get("attach_tol_m")
        tols_attach.append(None if v is None else float(v))
    if a.attach_tol_m is not None:
        attach_tol = float(a.attach_tol_m)
        chk.add("CFG_attach_tol", "attach_tol_m taken from --attach-tol-m", "INFO", attach_tol, tols_attach)
    else:
        vals = {v for v in tols_attach if v is not None}
        if len(vals) != 1:
            raise AuditError(f"attach_tol_m is missing or differs between the run summaries ({tols_attach}); give --attach-tol-m")
        attach_tol = vals.pop()
        chk.add("CFG_attach_tol", "attach_tol_m read from the run summaries (identical in all runs)", "PASS", attach_tol, tols_attach)
    snap_before = snapshot(reg_paths, run_dirs)
    if _HOOKS["before_processing"]:
        _HOOKS["before_processing"](dict(paths=reg_paths))

    # ---- 2. load + validate
    try:
        roads_gdf = gpd.read_file(roads_p, layer=a.roads_layer)
    except Exception as e:
        raise AuditError(f"cannot read road layer '{a.roads_layer}' from {roads_p}: {e}")
    require_crs(roads_gdf, "roads", a.expected_epsg)
    cand = read_layer(access_p, "candidate_access", ACCESS_REQUIRED["candidate_access"], "access")
    clus = read_layer(access_p, "clusters", ACCESS_REQUIRED["clusters"], "access")
    fac = read_layer(access_p, "facility_access", ACCESS_REQUIRED["facility_access"], "access")
    for nm, df in (("candidate_access", cand), ("clusters", clus), ("facility_access", fac)):
        require_crs(df, nm, a.expected_epsg)
    run_layers = OrderedDict()
    for rn, r in runs.items():
        lay = OrderedDict()
        for ln, req in RUN_REQUIRED.items():
            df = read_layer(r["gpkg"], ln, req, rn)
            require_crs(df, f"{rn}/{ln}", a.expected_epsg)
            lay[ln] = df
        run_layers[rn] = lay
    chk.add("CRS_all", f"all inputs are EPSG:{a.expected_epsg}", "PASS", a.expected_epsg, a.expected_epsg)
    wc = WorldCover(wc_p, a.expected_epsg) if wc_p else None
    if cand["cand_id"].duplicated().any():
        chk.add("CAND_unique_ids", "candidate cand_id unique", "FAIL", int(cand["cand_id"].duplicated().sum()), 0)
    else:
        chk.add("CAND_unique_ids", "candidate cand_id unique", "PASS", len(cand), len(cand))
    if clus["cluster_id"].duplicated().any():
        chk.add("CLUS_unique_ids", "cluster_id unique in clusters", "FAIL", int(clus["cluster_id"].duplicated().sum()), 0)
    else:
        chk.add("CLUS_unique_ids", "cluster_id unique in clusters", "PASS", len(clus), len(clus))
    miss_cl = sorted(set(cand["cluster_id"]) - set(clus["cluster_id"]))
    chk.add("JOIN_cluster", "every candidate cluster_id exists in clusters", "PASS" if not miss_cl else "FAIL", miss_cl[:10], "none missing")

    # ---- 3. road graph
    road = RoadModel(roads_gdf, tols, a.bridge_max_angle_deg)
    tmax = road.tmax
    chk.add("ROAD_geometry_issues", "road layer features with empty / non-line / zero-length geometry (skipped)", "PASS" if not road.geom_issues else "FLAG",
            len(road.geom_issues), 0, "; ".join(f"row {i['src_row']}: {i['issue']}" for i in road.geom_issues[:8]))
    st0 = road.state[(HEADLINE_POLICY, 0.0)]
    total_len = float(road.lengths.sum())
    chk.add("ROAD_total_length", "total geometric road length (m)", "INFO", r2(total_len), "")
    chk.add("ROAD_main_tie", "largest and second-largest components do not tie on length", "PASS" if not st0["main_tie"] else "FLAG", st0["main_tie"], False)

    sweep_rows = []
    kinds_all = [r["kind"] for r in road.junctions]
    for pol in POLICIES:
        s0 = road.state[(pol, 0.0)]
        for t in tols:
            s = road.state[(pol, t)]
            L = s["lengths"]
            sweep_rows.append(OrderedDict(
                policy=pol, tolerance_m=t, n_segments=len(road.segs), total_length_m=total_len, n_components=len(L), main_length_m=L[0],
                main_share_of_total_pct=100 * L[0] / total_len, second_length_m=(L[1] if len(L) > 1 else 0.0), main_tie=s["main_tie"],
                n_dangling_ends=s["n_dangling"], n_valid_bridges=sum(1 for b in road.bridges if b["direction_ok"] and b["dist_m"] <= t + 1e-9 and t > 0),
                n_inferred_bridge_edges=s["n_bridge_edges"], n_merges=len(s0["lengths"]) - len(L),
                n_observed_shared_endpoint=kinds_all.count("ENDPOINT_ENDPOINT"), n_observed_t_junction=kinds_all.count("T_JUNCTION"),
                n_observed_shared_vertex_crossing=kinds_all.count("CROSSING_SHARED_VERTEX"), n_observed_collinear_overlap=kinds_all.count("OVERLAP_COLLINEAR"),
                n_assumed_junction_crossings=kinds_all.count("CROSSING_NO_SHARED_VERTEX")))
    sweep = pd.DataFrame(sweep_rows)

    comp_rows = []
    c0 = st0["comps"]
    main_set_by_t = {t: set(road.state[(HEADLINE_POLICY, t)]["comps"][0]) for t in tols}
    main0_mask = road.main_mask(t=0.0)
    dang_by_seg = {}
    for e in road.ends:
        if e["dangling"]:
            dang_by_seg[e["seg_id"]] = dang_by_seg.get(e["seg_id"], 0) + 1
    for k, c in enumerate(c0):
        segsel = np.array(c)
        gu = shapely.union_all(road.geoms[segsel])
        d_main = 0.0 if k == 0 else float(shapely.distance(gu, shapely.union_all(road.geoms[main0_mask])))
        minx, miny, maxx, maxy = gu.bounds
        row = OrderedDict(component_id=k + 1, is_main=(k == 0), n_segments=len(c), length_m=st0["lengths"][k], share_of_total_pct=100 * st0["lengths"][k] / total_len,
                          dist_to_main_m=d_main, n_dangling_ends=sum(dang_by_seg.get(s, 0) for s in c), min_x=minx, min_y=miny, max_x=maxx, max_y=maxy,
                          src_rows=";".join(str(x) for x in sorted({road.segs[s]["src_row"] for s in c})))
        for t in tols:
            row[f"merged_into_main_at_{tl(t)}m"] = set(c) <= main_set_by_t[t]
        comp_rows.append(row)
    comps_df = pd.DataFrame(comp_rows)

    seg2comp0 = road.comp_ids(t=0.0)
    gap_rows = []
    best = {}
    for b in road.bridges:
        key = (b["end_id"], int(seg2comp0[b["to_seg"]]))
        if key not in best or (b["dist_m"], b["to_seg"]) < (best[key]["dist_m"], best[key]["to_seg"]):
            best[key] = b
    emitted = set()
    for key in sorted(best, key=lambda k: (best[k]["dist_m"], k)):
        b = best[key]
        if b["q_end_id"] and frozenset((b["end_id"], b["q_end_id"])) in emitted:
            continue
        if b["q_end_id"]:
            emitted.add(frozenset((b["end_id"], b["q_end_id"])))
        same = seg2comp0[b["from_seg"]] == seg2comp0[b["to_seg"]]
        gap_rows.append(OrderedDict(end_id=b["end_id"], from_seg=b["from_seg"], to_seg=b["to_seg"], from_comp=int(seg2comp0[b["from_seg"]]) + 1,
                                    to_comp=int(seg2comp0[b["to_seg"]]) + 1, same_component_t0=bool(same), dist_m=b["dist_m"], angle_deg=b["angle_deg"],
                                    direction_ok=b["direction_ok"], valid_bridge_at_max_tol=bool(b["direction_ok"]), q_end_id=b["q_end_id"] or "",
                                    px=b["px"], py=b["py"], qx=b["qx"], qy=b["qy"],
                                    **{f"within_{tl(t)}m": bool(b["dist_m"] <= t + 1e-9) for t in tols if t > 0}))
    gap_cols = (["end_id", "from_seg", "to_seg", "from_comp", "to_comp", "same_component_t0", "dist_m", "angle_deg", "direction_ok", "valid_bridge_at_max_tol", "q_end_id",
                 "px", "py", "qx", "qy"] + [f"within_{tl(t)}m" for t in tols if t > 0])
    gaps_df = pd.DataFrame(gap_rows, columns=gap_cols)
    junc_df = pd.DataFrame([OrderedDict(seg_a=r["seg_a"], seg_b=r["seg_b"], kind=r["kind"], evidence_class=r["evidence_class"], x=r["x"], y=r["y"], overlap_len_m=r["overlap_len_m"],
                                        connects_assume_junction=r["connects_assume_junction"], connects_explicit_only=r["connects_explicit_only"]) for r in road.junctions])
    if junc_df.empty:
        junc_df = pd.DataFrame(columns=["seg_a", "seg_b", "kind", "evidence_class", "x", "y", "overlap_len_m", "connects_assume_junction", "connects_explicit_only"])
    chk.add("ROAD_components_t0", "road components at tolerance 0 (headline policy assume_junction)", "INFO", len(c0), "", f"explicit_only: {len(road.state[('explicit_only', 0.0)]['lengths'])}")

    # ---- 4. candidates
    cand = cand.reset_index(drop=True)
    cdf, cgeoms = evaluate_features(cand, "poly", road, wc, thr, a.contact_tol_m, tmax)
    cmap = clus.set_index("cluster_id")
    out_c = pd.DataFrame(OrderedDict([("cand_id", cand["cand_id"])]))
    for col in CAND_OPTIONAL:
        if col in cand.columns:
            out_c[col] = cand[col]
    out_c["quality_class"] = cand["quality_class"].astype(str)
    out_c["flags"] = cand["flags"].fillna("").astype(str)
    out_c["est_roofs"] = pd.to_numeric(cand["est_roofs"], errors="coerce")
    out_c["cluster_id"] = cand["cluster_id"]
    out_c["cluster_kind"] = cand["cluster_id"].map(cmap["kind"]).astype(str)
    out_c["cluster_n_candidates"] = cand["cluster_id"].map(cmap["n_candidates"])
    out_c["cluster_gap_flag"] = cand["cluster_id"].map(to_bool(cmap["gap_flag"])).fillna(False).astype(bool)
    out_c["gap_flag"] = to_bool(cand["gap_flag"])
    out_c["stored_dist_to_ref_road_m"] = cand["dist_to_ref_road_m"]
    out_c = pd.concat([out_c, cdf], axis=1)
    if out_c["est_roofs"].isna().any():
        chk.add("CAND_est_roofs", "est_roofs numeric for all candidates", "FLAG", int(out_c["est_roofs"].isna().sum()), 0, "treated as 0 in roof totals")
        out_c["est_roofs"] = out_c["est_roofs"].fillna(0)
    ev = out_c["unevaluable_reason"] == ""
    dd = (out_c.loc[ev, "d_poly_any_m"] - out_c.loc[ev, "stored_dist_to_ref_road_m"]).abs()
    chk.add("DIST_polygon_stored", "recomputed polygon->road distance equals stored dist_to_ref_road_m", "PASS" if (len(dd) == 0 or dd.max() <= a.polygon_dist_tol_m) else "FLAG",
            f"max abs diff {dd.max() if len(dd) else float('nan'):.4f} m", f"<= {a.polygon_dist_tol_m} m",
            "FLAG means the road file or distance definition differs from the one used by the access assessment")
    mism = int(((out_c["stored_dist_to_ref_road_m"] > a.headline_threshold) != out_c["gap_flag"]).sum())
    chk.add("GAP_polygon_def", f"candidate gap_flag == (stored distance > {a.headline_threshold:g} m)", "PASS" if mism == 0 else "FLAG", f"{mism} mismatches", 0)
    n_rep_closer = int((out_c.loc[ev, "d_point_any_m"].round(2) < out_c.loc[ev, "d_poly_any_m"].round(2)).sum())
    n_bound_gt_poly = int((out_c.loc[ev, "d_boundary_any_m"].round(2) > out_c.loc[ev, "d_poly_any_m"].round(2)).sum())
    chk.add("DIST_point_vs_polygon", "OBSERVATION: polygons whose representative-point distance is smaller than the filled-polygon distance (no ordering is assumed or enforced)",
            "INFO" if n_rep_closer == 0 else "FLAG", n_rep_closer, "", "a non-zero count would indicate an invalid or repaired geometry; reported, not asserted")
    chk.add("DIST_boundary_vs_polygon", "OBSERVATION: polygons with a road inside the footprint (boundary-ring distance > filled-polygon distance)", "INFO", n_bound_gt_poly, "")
    chk.add("CAND_unevaluable", "polygons that could not be evaluated", "PASS" if (~ev).sum() == 0 else "FLAG", int((~ev).sum()), 0,
            "; ".join(sorted(set(out_c.loc[~ev, "unevaluable_reason"]))))

    # ---- 5. facilities
    fac = fac.reset_index(drop=True)
    fdf, fgeoms = evaluate_features(fac, "point", road, wc, thr, a.contact_tol_m, tmax)
    fout = pd.DataFrame(OrderedDict([("facility_id", fac["facility_id"].astype(str)), ("facility_name", fac["facility_name"]), ("facility_type", fac["facility_type"])]))
    for col in FAC_OPTIONAL:
        if col in fac.columns:
            fout[col] = fac[col]
    fout["stored_dist_to_ref_road_m"] = fac["dist_to_ref_road_m"]
    fout = pd.concat([fout, fdf], axis=1)
    fev = fout["unevaluable_reason"] == ""
    fd = (fout.loc[fev, "d_poly_any_m"] - fout.loc[fev, "stored_dist_to_ref_road_m"]).abs()
    chk.add("DIST_facility_stored", "recomputed facility->road distance equals stored value", "PASS" if (len(fd) == 0 or fd.max() <= 0.06) else "FLAG",
            f"max abs diff {fd.max() if len(fd) else float('nan'):.4f} m", "<= 0.06 m (stored value rounded)")

    # ---- 6. routes
    near_thr = thr[0]
    route_tols = sorted(set(tols) | {attach_tol})
    route_frames, route_static = [], []
    run_scen = OrderedDict()
    for rn, lay in run_layers.items():
        tg = lay["targets"]
        for scen in SCENARIOS:
            ldf = lay[SCEN_LAYER[scen]]
            long_df, recs, byk, objs = eval_routes(rn, scen, ldf, tg, road, wc, route_tols, attach_tol, near_thr)
            run_scen[(rn, scen)] = dict(df=long_df, recs=recs, byk=byk)
            route_frames.append(long_df)
            n_un = sum(1 for r in recs if r["geom"] is None)
            chk.add(f"ROUTES_{rn}_{scen}", f"{rn}/{SCEN_LAYER[scen]}: routes evaluated / total rows", "PASS" if n_un == 0 else "FLAG", f"{len(recs) - n_un}/{len(recs)}", f"{len(recs)}/{len(recs)}",
                    "; ".join(sorted({r['geometry_status'] for r in recs if r['geom'] is None})))
            orient = sorted({r["orientation"] for r in recs if r["geom"] is not None})
            chk.add(f"ORIENT_{rn}_{scen}", f"{rn}/{scen}: route orientation identified from the targets layer", "PASS" if orient in (["VERIFIED"], ["VERIFIED", "VERIFIED_REVERSED"], ["VERIFIED_REVERSED"], []) else "FLAG",
                    ",".join(orient), "VERIFIED")
            dup = int(ldf["target"].astype(str).duplicated().sum())
            if dup:
                chk.add(f"DUP_{rn}_{scen}", f"{rn}/{scen}: target appears more than once in the route layer", "FLAG", dup, 0)
    routes_df = pd.concat(route_frames, ignore_index=True) if route_frames else pd.DataFrame()

    # ---- 7. candidate x route proximity (roads + routes); by-construction start points
    combo_cols = {}
    for (rn, scen), rs in run_scen.items():
        pref = f"{rn}__{scen}__"
        geoms = [r["geom"] for r in rs["recs"] if r["geom"] is not None]
        sub = routes_df[(routes_df["run"] == rn) & (routes_df["scenario"] == scen) & (np.isclose(routes_df["tolerance_m"], attach_tol))]
        conn_keys = set(sub.loc[sub["reaches_main_deterministic"] == True, "route_key"]) if len(sub) else set()   # noqa: E712
        cgeo = [rs["byk"][k]["geom"] for k in conn_keys if k in rs["byk"]]
        starts = {r["route_key"]: r["start_pt"] for r in rs["recs"] if r["geom"] is not None}
        d_r, d_rr, d_rr_pt, d_rc, d_rc_pt, in_start, start_ids = [], [], [], [], [], [], []
        for g, d_any, rep_d in zip(cgeoms, out_c["d_poly_any_m"], out_c["d_point_any_m"]):
            if g is None:
                for L_ in (d_r, d_rr, d_rr_pt, d_rc, d_rc_pt):
                    L_.append(np.nan)
                in_start.append(False)
                start_ids.append("")
                continue
            rep = g.representative_point()
            dr = min([g.distance(x) for x in geoms]) if geoms else np.inf
            drp = min([rep.distance(x) for x in geoms]) if geoms else np.inf
            dc = min([g.distance(x) for x in cgeo]) if cgeo else np.inf
            dcp = min([rep.distance(x) for x in cgeo]) if cgeo else np.inf
            d_r.append(dr if np.isfinite(dr) else np.nan)
            d_rr.append(min(d_any, dr))
            d_rr_pt.append(min(rep_d, drp))
            d_rc.append(min(d_any, dc))
            d_rc_pt.append(min(rep_d, dcp))
            hit = sorted(k for k, sp in starts.items() if sp is not None and g.distance(sp) <= a.contact_tol_m)
            in_start.append(bool(hit))
            start_ids.append(";".join(hit))
        cc = OrderedDict()
        cc[pref + "d_routes_poly_m"] = d_r
        cc[pref + "d_roads_routes_poly_m"] = d_rr
        cc[pref + "d_roads_routes_pt_m"] = d_rr_pt
        cc[pref + "d_roads_connroutes_poly_m"] = d_rc
        cc[pref + "d_roads_connroutes_pt_m"] = d_rc_pt
        cdfx = pd.DataFrame(cc)
        for t in thr:
            k = tl(t)
            cdfx[pref + f"roads_routes_poly_le{k}"] = cdfx[pref + "d_roads_routes_poly_m"].round(2) <= t
            cdfx[pref + f"roads_routes_pt_le{k}"] = cdfx[pref + "d_roads_routes_pt_m"].round(2) <= t
            cdfx[pref + f"roads_connroutes_poly_le{k}"] = cdfx[pref + "d_roads_connroutes_poly_m"].round(2) <= t
            cdfx[pref + f"roads_connroutes_pt_le{k}"] = cdfx[pref + "d_roads_connroutes_pt_m"].round(2) <= t
        cdfx[pref + "start_in_polygon"] = in_start
        cdfx[pref + "start_in_polygon_route_keys"] = start_ids
        hk = tl(a.headline_threshold)
        base_in = out_c[f"poly_any_le{hk}"] if f"poly_any_le{hk}" in out_c else out_c["d_poly_any_m"].round(2) <= a.headline_threshold
        wr = cdfx[pref + "d_roads_routes_poly_m"].round(2) <= a.headline_threshold
        cdfx[pref + "gain_class_headline"] = np.where(base_in, "BASELINE_WITHIN", np.where(wr & cdfx[pref + "start_in_polygon"], "BY_CONSTRUCTION",
                                                      np.where(wr, "SPILLOVER", "NOT_WITHIN")))
        combo_cols[(rn, scen)] = cdfx
    out_c = pd.concat([out_c] + [d.set_axis(out_c.index) for d in combo_cols.values()], axis=1)

    # ---- 8. facility x route
    for (rn, scen), rs in run_scen.items():
        pref = f"{rn}__{scen}__"
        sub = routes_df[(routes_df["run"] == rn) & (routes_df["scenario"] == scen) & (np.isclose(routes_df["tolerance_m"], attach_tol))].set_index("target")
        pres, outc, rm, rany, mt, ch, kinds = [], [], [], [], [], [], []
        for fid in fout["facility_id"]:
            tid = "F:" + str(fid)
            if tid in sub.index:
                r = sub.loc[tid]
                if isinstance(r, pd.DataFrame):
                    r = r.iloc[0]
                pres.append(True)
                outc.append(r["chain_outcome"])
                rm.append(bool(r.get("reaches_main_deterministic", False)))
                rany.append(bool(r.get("reaches_main_any_resolution", False)))
                mt.append(r.get("min_tolerance_to_main_m", np.nan))
                ch.append(r.get("chain", ""))
            else:
                pres.append(False)
                outc.append("NO_ROUTE_IN_LAYER")
                rm.append(False)
                rany.append(False)
                mt.append(np.nan)
                ch.append("")
        fout[pref + "route_present"] = pres
        fout[pref + "chain_outcome_at_attach_tol"] = outc
        fout[pref + "reaches_main_deterministic"] = rm
        fout[pref + "reaches_main_any_resolution"] = rany
        fout[pref + "min_tolerance_to_main_m"] = mt
        fout[pref + "chain"] = ch
        fout[pref + "route_start_at_facility_by_construction"] = pres
    tgt_status = {}
    for rn, lay in run_layers.items():
        tg = lay["targets"]
        if "coord_status" in tg.columns:
            for _, r in tg.iterrows():
                tgt_status.setdefault(str(r["id"]), set()).add(f"{rn}:{r['coord_status']}")
    fout["coord_status_by_run"] = ["|".join(sorted(tgt_status.get("F:" + str(f), []))) for f in fout["facility_id"]]

    # ---- 9. summaries
    metrics = []
    for t in thr:
        k = tl(t)
        metrics += [
            (f"within_{k}m_polygon_any_road", "", "", t, f"poly_any_le{k}", "polygon distance to ANY road <= threshold (proximity only)"),
            (f"within_{k}m_polygon_main_component", "", "", t, f"poly_main_le{k}", "polygon distance to the main component (tolerance 0) <= threshold"),
            (f"within_{k}m_polygon_main_component_inferred_bridges", "", "", t, f"poly_maininf_le{k}", "as above, after inferred tolerance bridges at the largest tolerance"),
            (f"within_{k}m_rep_point_any_road", "", "", t, f"point_any_le{k}", "representative-point distance to ANY road <= threshold (sensitivity)"),
            (f"within_{k}m_rep_point_main_component", "", "", t, f"point_main_le{k}", "representative-point distance to the main component <= threshold"),
        ]
    metrics += [("contact_any_road", "", "", a.contact_tol_m, "contact_any_le_tol", "polygon within the contact tolerance of any road"),
                ("contact_main_component", "", "", a.contact_tol_m, "contact_main_le_tol", "polygon within the contact tolerance of the main component"),
                ("intersects_wc_nodata", "", "", np.nan, "intersects_wc_nodata", "footprint touches a WorldCover NoData cell (coverage flag)")]
    for (rn, scen) in run_scen:
        pref = f"{rn}__{scen}__"
        for t in thr:
            k = tl(t)
            metrics += [(f"within_{k}m_roads_plus_routes_polygon", rn, scen, t, pref + f"roads_routes_poly_le{k}", "polygon distance to roads UNION this scenario's routes <= threshold (proximity only)"),
                        (f"within_{k}m_roads_plus_routes_rep_point", rn, scen, t, pref + f"roads_routes_pt_le{k}", "representative-point distance to roads UNION routes <= threshold"),
                        (f"within_{k}m_roads_plus_main_connected_routes_polygon", rn, scen, t, pref + f"roads_connroutes_poly_le{k}",
                         "polygon distance to roads UNION routes whose deterministic chain reaches the main component at the attach tolerance")]
        out_c = pd.concat([out_c, pd.DataFrame({pref + "gain_spillover_headline": out_c[pref + "gain_class_headline"] == "SPILLOVER",
                                                pref + "gain_by_construction_headline": out_c[pref + "gain_class_headline"] == "BY_CONSTRUCTION"})], axis=1)
        metrics += [("newly_within_headline_by_construction", rn, scen, a.headline_threshold, pref + "gain_by_construction_headline", "within headline threshold only with this scenario, polygon holds a route start point"),
                    ("newly_within_headline_spillover", rn, scen, a.headline_threshold, pref + "gain_spillover_headline", "within headline threshold only with this scenario, polygon holds NO route start point")]
    srows = candidate_summary(out_c, metrics)

    fac_metrics = []
    for t in thr:
        k = tl(t)
        fac_metrics += [(f"within_{k}m_polygon_any_road", t, f"poly_any_le{k}"), (f"within_{k}m_main_component", t, f"poly_main_le{k}")]
    for gtype, gval, m in (("ALL", "ALL", pd.Series(True, index=fout.index)),):
        base = m & fev
        for metric, t, col in fac_metrics:
            num = base & fout[col]
            srows.append(OrderedDict(summary_id="facilities", group_type=gtype, group_value=gval, run="", scenario="", metric=metric, threshold_or_tolerance_m=t,
                                     unit="facility points", numerator=int(num.sum()), denominator=int(base.sum()), percent=(100.0 * num.sum() / base.sum()) if base.sum() else np.nan,
                                     roofs_numerator=np.nan, roofs_denominator=np.nan, roofs_percent=np.nan, definition="facility point distance to the stated road set"))
    for (rn, scen), rs in run_scen.items():
        sub_all = routes_df[(routes_df["run"] == rn) & (routes_df["scenario"] == scen)]
        for t in route_tols:
            s = sub_all[np.isclose(sub_all["tolerance_m"], t)]
            ev_r = s[s["chain_outcome"] != "UNEVALUABLE"]
            for metric, cond, definition in (
                    ("routes_reaching_main_deterministic", ev_r["reaches_main_deterministic"] == True, "deterministic chain ends at a road of the main component"),   # noqa: E712
                    ("routes_reaching_main_any_resolution", ev_r["reaches_main_any_resolution"] == True, "some resolution of ambiguous options reaches the main component"),  # noqa: E712
                    ("routes_reaching_any_road_deterministic", ev_r["reaches_any_road_deterministic"] == True, "deterministic chain ends at any road"),  # noqa: E712
                    ("routes_with_ambiguous_options", ev_r["ambiguous_options"] == True, "more than one attachment option within the tolerance"),  # noqa: E712
                    ("routes_chain_cycle", ev_r["chain_outcome"] == "CYCLE", "chain revisits a route"),
                    ("routes_chain_dead_end", ev_r["chain_outcome"] == "DEAD_END", "chain ends without reaching a road"),
                    ("routes_near_road_but_not_attached", ev_r["near_road_but_not_attached"] == True, "route within the smallest threshold of a road along its geometry but chain does not reach a road")):  # noqa: E712
                srows.append(OrderedDict(summary_id="routes", group_type="run_scenario", group_value=f"{rn}|{scen}", run=rn, scenario=scen, metric=metric,
                                         threshold_or_tolerance_m=t, unit="routes", numerator=int(cond.sum()), denominator=len(ev_r),
                                         percent=(100.0 * cond.sum() / len(ev_r)) if len(ev_r) else np.nan, roofs_numerator=np.nan, roofs_denominator=np.nan, roofs_percent=np.nan,
                                         definition=definition))
    summ = pd.DataFrame(srows)

    # ---- 10. validation against previously reported figures + claim agreement
    nroutes_total = 0
    on_main_t0 = 0
    on_main_15 = 0
    for (rn, scen), rs in run_scen.items():
        for r in rs["byk"].values():
            nroutes_total += 1
            on_main_t0 += int(r["road_cls"] == "main")
            on_main_15 += int(r["d_main"] <= attach_tol)
    claims = routes_df[routes_df["claim_attach_to_vs_independent"].notna()] if "claim_attach_to_vs_independent" in routes_df.columns else pd.DataFrame()
    if len(claims):
        for (rn, scen), g in claims.groupby(["run", "scenario"]):
            n_dis_a = int((g["claim_attach_to_vs_independent"] == "DISAGREE").sum())
            n_dis_c = int((g["claim_connected_vs_independent"] == "DISAGREE").sum())
            chk.add(f"CLAIM_attach_{rn}_{scen}", f"{rn}/{scen}: stored attach_to disagrees with independent geometry at {attach_tol:g} m", "PASS" if n_dis_a == 0 else "FLAG", n_dis_a, 0,
                    "labels: " + ",".join(f"{k}={v}" for k, v in g["claim_attach_to_vs_independent"].value_counts().items()))
            chk.add(f"CLAIM_connected_{rn}_{scen}", f"{rn}/{scen}: stored connected disagrees with independent geometry at {attach_tol:g} m", "PASS" if n_dis_c == 0 else "FLAG", n_dis_c, 0,
                    "labels: " + ",".join(f"{k}={v}" for k, v in g["claim_connected_vs_independent"].value_counts().items()))

    def prior(cid, desc, observed, key, detail=""):
        exp = PRIOR_REPORTED[key]
        if a.skip_prior_comparison:
            chk.add(cid, desc, "INFO", observed, exp, "prior comparison skipped")
        else:
            chk.add(cid, desc + " [previously reported figure; comparison only]", "MATCHES_PRIOR" if observed == exp else "DIFFERS_FROM_PRIOR", observed, exp, detail)
    hk = tl(a.headline_threshold)
    prior("PRIOR_components_t0", "road components at tolerance 0 (assume_junction)", len(c0), "road_components_t0",
          f"explicit_only gives {len(road.state[('explicit_only', 0.0)]['lengths'])}")
    prior("PRIOR_terminals_on_main", "route terminals whose nearest road is in the main component (all runs x scenarios, tolerance 0)", on_main_t0, "route_terminals_on_main",
          f"routes evaluated in total: {nroutes_total}; terminals within {attach_tol:g} m of the main component: {on_main_15}")
    prior("PRIOR_candidates_total", "candidate polygons in candidate_access", len(out_c), "candidates_total")
    prior("PRIOR_facilities_total", "facility points in facility_access", len(fout), "facilities_total")
    n_base = int(out_c[f"poly_any_le{hk}"].sum())
    prior("PRIOR_baseline_within50", f"baseline polygons within {hk} m of any road (polygon distance)", n_base, "baseline_within50_polygon", f"denominator {int(ev.sum())}")
    for rn in runs:
        key = f"{rn}_within50_polygon"
        s = f"{rn}__network_aware__roads_routes_poly_le{hk}"
        s_ic = f"{rn}__independent__roads_routes_poly_le{hk}"
        if s in out_c.columns:
            obs = int(out_c[s].sum())
            detail = f"network_aware={obs}; independent={int(out_c[s_ic].sum())}; denominator {int(ev.sum())}; roads+main-connected routes (network_aware)=" + str(int(out_c[f'{rn}__network_aware__roads_connroutes_poly_le{hk}'].sum()))
            if key in PRIOR_REPORTED:
                prior(f"PRIOR_{rn}_within50", f"{rn}: polygons within {hk} m of roads+network-aware routes", obs, key, detail)
            else:
                chk.add(f"INFO_{rn}_within50", f"{rn}: polygons within {hk} m of roads+network-aware routes", "INFO", obs, "", detail)
    gap_sub = out_c["cluster_gap_flag"] & ev
    prior("PRIOR_gap_cluster_polygons", "polygons in planner-targeted gap clusters", int(gap_sub.sum()), "run5_gap_cluster_polygons")
    if "run5" in runs:
        pt_col = f"run5__network_aware__roads_routes_pt_le{hk}"
        pg_col = f"run5__network_aware__roads_routes_poly_le{hk}"
        prior("PRIOR_gap_cluster_point_run5", f"gap-cluster polygons with representative point within {hk} m of roads+run5 routes", int(out_c.loc[gap_sub, pt_col].sum()), "run5_gap_cluster_within50_point",
              "definition: representative-point distance (experiments-script style); by-construction start polygons are included")
        prior("PRIOR_gap_cluster_poly_run5", f"gap-cluster polygons within {hk} m (polygon distance) of roads+run5 routes", int(out_c.loc[gap_sub, pg_col].sum()), "run5_gap_cluster_within50_polygon",
              "definition: polygon distance (ag1 style); by-construction start polygons are included")
    return _finish(a, out, root, locals_=dict(
        chk=chk, snap_before=snap_before, reg_paths=reg_paths, run_dirs=run_dirs, sweep=sweep, comps_df=comps_df, gaps_df=gaps_df, junc_df=junc_df, out_c=out_c, fout=fout,
        routes_df=routes_df, summ=summ, road=road, cgeoms=cgeoms, fgeoms=fgeoms, roads_p=roads_p, access_p=access_p, wc_p=wc_p, wc=wc, attach_tol=attach_tol, tols=tols, thr=thr,
        runs=runs, run_scen=run_scen, ev=ev, total_len=total_len, access_ok=True, params_first=params))


# --------------------------------------------------------------------------------------------------------------------- outputs
def _finish(a, out, root, locals_):
    L = locals_
    chk = L["chk"]
    road = L["road"]
    if _HOOKS["after_processing"]:
        _HOOKS["after_processing"](dict(paths=L["reg_paths"]))
    snap_after = snapshot(L["reg_paths"], L["run_dirs"])
    changes, notes = compare_snapshots(L["snap_before"], snap_after)
    out.mkdir(parents=True, exist_ok=True)
    integrity = OrderedDict(script=SCRIPT_VERSION, created_utc=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), libraries=lib_versions(),
                            inputs_before=L["snap_before"]["files"], inputs_after=snap_after["files"], sidecars_before=L["snap_before"]["sidecars"],
                            run_folder_listing_before=L["snap_before"]["run_dirs"], run_folder_listing_after=snap_after["run_dirs"],
                            content_changes=changes, mtime_only_notes=notes, inputs_unchanged=(not changes))
    if changes:
        (out / "INPUT_CHANGED_REPORT_INVALID.txt").write_text(
            "INPUT CHANGED DURING THE RUN - THIS REPORT IS INVALID.\n" + "\n".join(changes) + "\nNo audit result from this run may be used. Re-run after the inputs are stable.\n", encoding="utf-8")
        (out / "input_integrity.json").write_text(json.dumps(integrity, indent=2, default=str), encoding="utf-8")
        print("INPUT CHANGED DURING THE RUN - report invalid:\n  " + "\n  ".join(changes), file=sys.stderr)
        return 2
    chk.add("INPUT_unchanged_before_write", "SHA-256, size and sidecar/run-folder listings unchanged after processing", "PASS", "unchanged", "unchanged")
    if notes:
        chk.add("INPUT_mtime", "files touched (mtime) without a content change", "FLAG", len(notes), 0, "; ".join(notes))
    try:
        files = _write_outputs(a, out, L, integrity)
    except Exception as e:
        (out / "AUDIT_INCOMPLETE_ERROR.txt").write_text(f"Writing the outputs failed: {type(e).__name__}: {e}\nTreat any file in this folder as incomplete.\n", encoding="utf-8")
        raise AuditError(f"writing outputs failed: {type(e).__name__}: {e}")
    snap_final = snapshot(L["reg_paths"], L["run_dirs"])
    changes2, _ = compare_snapshots(L["snap_before"], snap_final)
    if changes2:
        (out / "INPUT_CHANGED_REPORT_INVALID.txt").write_text("INPUT CHANGED WHILE WRITING OUTPUTS - THIS REPORT IS INVALID.\n" + "\n".join(changes2) + "\n", encoding="utf-8")
        print("INPUT CHANGED while writing outputs - report invalid", file=sys.stderr)
        return 2
    nfail = chk.count("FAIL")
    ndiff = chk.count("DIFFERS_FROM_PRIOR")
    nflag = chk.count("FLAG")
    print(f"Audit written to {out}\n  checks: FAIL={nfail}  FLAG={nflag}  DIFFERS_FROM_PRIOR={ndiff}  MATCHES_PRIOR={chk.count('MATCHES_PRIOR')}")
    if ndiff:
        print("  Some figures differ from earlier reports. Read checks.csv; nothing was forced to match.")
    return 1 if nfail else 0


def _write_outputs(a, out, L, integrity):
    chk, road = L["chk"], L["road"]
    out_c, fout, routes_df, summ = L["out_c"], L["fout"], L["routes_df"], L["summ"]
    written = OrderedDict()

    def fmt(df):
        df = df.copy()
        for c in df.columns:
            if df[c].dtype.kind == "f":
                df[c] = df[c].round(2)
        return df
    csvs = OrderedDict([
        ("road_graph_tolerance_sweep.csv", L["sweep"]), ("road_components.csv", L["comps_df"]), ("road_near_gaps.csv", L["gaps_df"]), ("road_junctions.csv", L["junc_df"]),
        ("candidate_connectivity.csv", out_c.drop(columns=["geometry"], errors="ignore")), ("route_connectivity.csv", routes_df),
        ("facility_connectivity.csv", fout), ("summary_by_group.csv", summ)])
    # GPKG layers
    gp = out / "connectivity_audit.gpkg"
    crs = f"EPSG:{a.expected_epsg}"
    layers = OrderedDict()
    cg = out_c.copy()
    cg["geometry"] = [g if g is not None else None for g in L["cgeoms"]]
    layers["candidates"] = gpd.GeoDataFrame(cg, geometry="geometry", crs=crs)
    fg = fout.copy()
    fg["geometry"] = L["fgeoms"]
    layers["facilities"] = gpd.GeoDataFrame(fg, geometry="geometry", crs=crs)
    seg = pd.DataFrame(dict(seg_id=[s["seg_id"] for s in road.segs], src_row=[s["src_row"] for s in road.segs], part=[s["part"] for s in road.segs],
                            length_m=road.lengths, component_id=road.comp_ids(t=0.0) + 1, is_main=road.main_mask(t=0.0),
                            component_id_inferred_bridges=road.comp_ids(t=road.tmax) + 1))
    layers["road_segments"] = gpd.GeoDataFrame(seg, geometry=list(road.geoms), crs=crs)
    dang = [e for e in road.ends if e["dangling"]]
    if dang:
        layers["dangling_ends"] = gpd.GeoDataFrame(pd.DataFrame(dang).drop(columns=["x", "y"]), geometry=[Point(e["x"], e["y"]) for e in dang], crs=crs)
    vb = [b for b in road.bridges if b["direction_ok"]]
    if vb:
        layers["inferred_bridges"] = gpd.GeoDataFrame(pd.DataFrame([dict(end_id=b["end_id"], from_seg=b["from_seg"], to_seg=b["to_seg"], dist_m=b["dist_m"], angle_deg=b["angle_deg"]) for b in vb]),
                                                      geometry=[LineString([(b["px"], b["py"]), (b["qx"], b["qy"])]) for b in vb], crs=crs)
    rg = []
    attach = routes_df[np.isclose(routes_df["tolerance_m"], L["attach_tol"])] if len(routes_df) else routes_df
    for _, r in attach.iterrows():
        rs = L["run_scen"][(r["run"], r["scenario"])]
        rec = rs["byk"].get(r["route_key"])
        rg.append(rec["geom"] if rec else None)
    if len(attach):
        keep = [i for i, g in enumerate(rg) if g is not None]
        layers["routes_at_attach_tol"] = gpd.GeoDataFrame(attach.reset_index(drop=True).iloc[keep], geometry=[rg[i] for i in keep], crs=crs)
    for name, g in layers.items():
        for c in g.columns:
            if g[c].dtype == object and c != "geometry":
                g[c] = g[c].astype(str)
        g.to_file(gp, layer=name, driver="GPKG")
    written["connectivity_audit.gpkg"] = None
    # data dictionary
    dict_src = OrderedDict(csvs)
    dict_src["checks.csv"] = pd.DataFrame(chk.rows)
    dd = data_dictionary(dict_src)
    undoc = dd[dd["definition"] == "UNDOCUMENTED COLUMN"]
    if len(undoc):
        chk.add("DICT_complete", "every output column has a definition", "FLAG", len(undoc), 0, "; ".join(f"{r.file}:{r.column}" for r in undoc.itertuples())[:400])
    else:
        chk.add("DICT_complete", "every output column has a definition", "PASS", 0, 0)
    chk_df = pd.DataFrame(chk.rows)
    csvs["checks.csv"] = chk_df
    csvs["data_dictionary.csv"] = dd
    for name, df in csvs.items():
        fmt(df).to_csv(out / name, index=False, encoding="utf-8")
        written[name] = None
    # JSON summary
    st0 = L["sweep"]
    hk = tl(a.headline_threshold)
    ev = L["ev"]
    summary = OrderedDict(
        script=SCRIPT_VERSION, not_established=NOT_ESTABLISHED, limitations=LIMITATIONS,
        parameters=OrderedDict(tolerances_m=L["tols"], thresholds_m=L["thr"], headline_threshold_m=a.headline_threshold, contact_tol_m=a.contact_tol_m, attach_tol_m=L["attach_tol"],
                               headline_policy=HEADLINE_POLICY, bridge_max_angle_deg=a.bridge_max_angle_deg, crs=f"EPSG:{a.expected_epsg}"),
        road_graph=OrderedDict(sweep=json.loads(st0.to_json(orient="records")), n_segments=len(road.segs), total_length_m=r2(L["total_len"])),
        candidates=OrderedDict(n=int(len(out_c)), n_evaluable=int(ev.sum()), est_roofs_total_proxy=float(out_c["est_roofs"].sum()),
                               within_headline_polygon_any_road=int(out_c[f"poly_any_le{hk}"].sum()), within_headline_polygon_main=int(out_c[f"poly_main_le{hk}"].sum())),
        facilities=OrderedDict(n=int(len(fout))),
        checks=OrderedDict((s, chk.count(s)) for s in Checks.STATUSES), inputs_unchanged=True)
    (out / "connectivity_audit_summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    written["connectivity_audit_summary.json"] = None
    (out / "input_integrity.json").write_text(json.dumps(integrity, indent=2, default=str), encoding="utf-8")
    written["input_integrity.json"] = None
    (out / "connectivity_audit_report.txt").write_text(_report(a, L, chk_df), encoding="utf-8")
    written["connectivity_audit_report.txt"] = None
    man = []
    for name in sorted(written):
        p = out / name
        man.append(OrderedDict(file=name, bytes=p.stat().st_size, sha256=sha256_file(p)))
    pd.DataFrame(man).to_csv(out / "manifest.csv", index=False)
    return man


def _report(a, L, chk_df):
    road, out_c, fout, routes_df, summ = L["road"], L["out_c"], L["fout"], L["routes_df"], L["summ"]
    s = []
    s.append(f"CONNECTIVITY AUDIT - {SCRIPT_VERSION}")
    s.append("=" * 100)
    s.append(NOT_ESTABLISHED)
    s.append("")
    s.append("INPUTS (SHA-256 recorded in input_integrity.json; unchanged after processing)")
    for p in L["reg_paths"]:
        s.append(f"  {p}")
    s.append("")
    s.append("1. ROAD GRAPH (headline policy: assume_junction; main component = largest by total length)")
    sw = L["sweep"]
    cols = ["policy", "tolerance_m", "n_components", "main_length_m", "main_share_of_total_pct", "n_dangling_ends", "n_valid_bridges", "n_assumed_junction_crossings"]
    s.append(sw[cols].round(2).to_string(index=False))
    s.append("")
    s.append("2. CANDIDATE POLYGONS (proximity is NOT graph connectivity)")
    hk = tl(a.headline_threshold)
    ev = L["ev"]
    n = int(ev.sum())
    for lab, col in (("polygon distance, any road", f"poly_any_le{hk}"), ("polygon distance, main component", f"poly_main_le{hk}"),
                     ("representative point, any road", f"point_any_le{hk}"), ("representative point, main component", f"point_main_le{hk}")):
        s.append(f"  within {hk} m, {lab}: {int(out_c[col].sum())}/{n}  (est_roofs proxy {out_c.loc[out_c[col], 'est_roofs'].sum():.0f}/{out_c.loc[ev, 'est_roofs'].sum():.0f})")
    s.append(f"  polygon contact (<= {a.contact_tol_m:g} m) with the main component: {int(out_c['contact_main_le_tol'].sum())}/{n}")
    s.append("  by quality class (polygon distance, any road, headline threshold):")
    for q, g in out_c.groupby("quality_class"):
        s.append(f"    {q}: {int(g[f'poly_any_le{hk}'].sum())}/{len(g)} polygons; est_roofs proxy {g.loc[g[f'poly_any_le{hk}'], 'est_roofs'].sum():.0f}/{g['est_roofs'].sum():.0f}")
    s.append("")
    s.append("3. PROPOSED ROUTES (geometric attachment at the planner's attach tolerance; stored attach_to/connected are claims)")
    for (rn, scen) in L["run_scen"]:
        sub = routes_df[(routes_df["run"] == rn) & (routes_df["scenario"] == scen) & np.isclose(routes_df["tolerance_m"], L["attach_tol"])]
        s.append(f"  {rn} / {scen}: routes={len(sub)}  reach main (deterministic)={int((sub['reaches_main_deterministic'] == True).sum())}  "   # noqa: E712
                 f"cycle={int((sub['chain_outcome'] == 'CYCLE').sum())}  dead end={int((sub['chain_outcome'] == 'DEAD_END').sum())}  ambiguous={int((sub['ambiguous_options'] == True).sum())}")  # noqa: E712
    s.append("")
    s.append("4. FACILITIES")
    s.append(fout[["facility_id", "facility_name", "d_poly_any_m", "nearest_component_class", "connectivity_status"]].round(2).to_string(index=False))
    s.append("")
    s.append("5. CHECKS (FAIL / FLAG / DIFFERS_FROM_PRIOR first)")
    order = {"FAIL": 0, "FLAG": 1, "DIFFERS_FROM_PRIOR": 2}
    cd = chk_df.assign(_o=chk_df["status"].map(order).fillna(9)).sort_values(["_o", "check_id"])
    for r in cd.itertuples():
        s.append(f"  [{r.status}] {r.check_id}: {r.description} | observed={r.observed} expected={r.expected} {r.detail}")
    s.append("")
    s.append("6. LIMITATIONS")
    for x in LIMITATIONS:
        s.append("  - " + x)
    return "\n".join(s) + "\n"


if __name__ == "__main__":
    sys.exit(main())
