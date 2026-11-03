"""Tests for dk_stageB_connectivity_audit_v2.py (revised connectivity interpretation). Read-only; nothing is routed.
Usage:
  python dk_stageB_connectivity_audit_v2_tests.py                       # unit tests on synthetic geometry (C0076-like baseline / omission cases)
  ... --v1-dir <_connectivity_audit_v1> --v2-dir <_connectivity_audit_v2>  # regression: v1 vs v2 outputs on the same runs (no check weakened)
  ... --real-root <stageB> --v2-dir <...>                               # real-data expectations (C0076, C0002, zero-edge routes)
Geometric connectivity on a planning grid only: not real-world access, ownership or physical passability."""
import argparse, importlib.util, sys
from pathlib import Path
import pandas as pd
from shapely.geometry import Point, LineString

here = Path(__file__).parent
spec = importlib.util.spec_from_file_location("aud2", here / "dk_stageB_connectivity_audit_v2.py")
M = importlib.util.module_from_spec(spec); spec.loader.exec_module(M)
res = []


def t(name, cond, detail=""):
    res.append((name, bool(cond), detail)); print(("PASS " if cond else "FAIL ") + name + (f"  [{detail}]" if detail and not cond else ""))


S, TOL = 0.01, 15.0
road = LineString([(0, 0), (100, 0)])
fac = {"HEALTH": LineString([(30, 3.4062), (70, 3.4062)])}

# T1 baseline-like: cell centre on a facility route, road line 3.4062 m away, labelled ROAD
c = M.classify_house_road_label(Point(50, 3.4062), road, fac, S, TOL)
t("T1 baseline-like: touches facility route -> PASS, snap=FACILITY, label mismatch flagged", c["status"] == "PASS" and c["snap_target"] == "FACILITY_ROUTE:HEALTH" and c["label_mismatch"] and c["parent"] == "HEALTH", c)
t("T1b distance to the road line is still reported in the reason", "3.4062" in c["reason"], c["reason"])
# T2 omission-like: last vertex on the road line
c = M.classify_house_road_label(Point(50, 0), road, {"HEALTH": LineString([(30, 40), (70, 40)])}, S, TOL)
t("T2 omission-like: touches road -> PASS, snap=ROAD_LINE, no mismatch", c["status"] == "PASS" and c["snap_target"] == "ROAD_LINE" and not c["label_mismatch"], c)
# T3 not weakened: near but touching nothing
c = M.classify_house_road_label(Point(50, 3.4062), road, {"HEALTH": LineString([(30, 40), (70, 40)])}, S, TOL)
t("T3 within tolerance but touching nothing -> still INFO (not PASS)", c["status"] == "INFO" and not c["label_mismatch"], c)
# T4 beyond tolerance
c = M.classify_house_road_label(Point(50, 20), road, fac, S, TOL)
t("T4 beyond attach_tol_m of road and facilities -> FAIL", c["status"] == "FAIL", c)
# T5 junction: touches both
c = M.classify_house_road_label(Point(50, 0), road, {"H": LineString([(40, 0), (60, 0)])}, S, TOL)
t("T5 touches road and facility -> ROAD_LINE, no mismatch", c["status"] == "PASS" and c["snap_target"] == "ROAD_LINE" and not c["label_mismatch"], c)
# T6 no facility routes: roads-only behaviour unchanged
c = M.classify_house_road_label(Point(50, 3.4062), road, {}, S, TOL)
t("T6 no facility routes: same as roads-only rule (INFO)", c["status"] == "INFO", c)
# T7 strict boundary
c = M.classify_house_road_label(Point(50, 0.02), road, {}, S, TOL)
t("T7 0.02 m off the road is not 'touching' at the 0.01 m strict tolerance", c["status"] == "INFO", c)
# T8 line components helper: joined at tolerance, separate below it
segs = [LineString([(0, 0), (10, 0)]), LineString([(10.5, 0), (20, 0)]), LineString([(100, 0), (110, 0)])]
l0 = M.line_components(segs, 0.01); l1 = M.line_components(segs, 1.0)
t("T8 line components: 0.5 m gap separates at 0.01 m, joins at 1 m, far segment stays separate", l0[0] != l0[1] and l1[0] == l1[1] and l1[0] != l1[2])

ap = argparse.ArgumentParser()
ap.add_argument("--v1-dir"); ap.add_argument("--v2-dir"); ap.add_argument("--real-root")
ap.add_argument("--baseline", default="S2_fac_C0_s25_K3_P2"); ap.add_argument("--omit", default="S2_fac_C0_s25_omitmerge")
a = ap.parse_args()

if a.v1_dir and a.v2_dir:
    v1 = pd.read_csv(Path(a.v1_dir) / "connectivity_summary.csv"); v2 = pd.read_csv(Path(a.v2_dir) / "connectivity_summary.csv")
    rank = {"FAIL": 0, "NOT_VERIFIABLE": 1, "INFO": 2, "PASS": 3}
    m = v1.merge(v2, on=["scenario", "check_id"], how="left", suffixes=("_v1", "_v2"))
    t("R1 every v1 check id still exists in v2", m.status_v2.notna().all(), str(m[m.status_v2.isna()][["scenario", "check_id"]].values.tolist()))
    worse = m[m.status_v2.notna() & (m.status_v2.map(rank) < m.status_v1.map(rank))]
    t("R2 no v1 check became worse in v2", worse.empty, str(worse[["scenario", "check_id", "status_v1", "status_v2"]].values.tolist()))
    relaxed = m[m.status_v2.notna() & (m.status_v2.map(rank) > m.status_v1.map(rank))]
    t("R3 any check that improved is only G02/G03 (the combined-network interpretation)", set(relaxed.check_id) <= {"G02", "G03"}, str(relaxed[["scenario", "check_id", "status_v1", "status_v2"]].values.tolist()))
    for cid in ("G04", "L01", "L02", "L03", "P01:house", "P01:facility", "C01:house", "C01:facility"):
        a1 = v1[v1.check_id == cid].set_index("scenario").status; a2 = v2[v2.check_id == cid].set_index("scenario").status
        t(f"R4 {cid} status unchanged", a1.equals(a2.reindex(a1.index)), f"{dict(a1)} vs {dict(a2)}")

if a.real_root and a.v2_dir:
    d = Path(a.v2_dir); ex = pd.read_csv(d / "connectivity_exceptions.csv"); sm = pd.read_csv(d / "connectivity_summary.csv"); ln = pd.read_csv(d / "length_consistency.csv")
    b, o = a.baseline, a.omit
    g09 = ex[(ex.check_id == "G09") & (ex.item_id == "C0076")]
    t("D1 baseline C0076: G09 INFO label/snap mismatch on a facility route", ((g09.scenario == b) & (g09.status == "INFO")).any() and g09[g09.scenario == b].value.astype(str).str.contains("HEALTH_8734223673").any(), str(g09.values.tolist()))
    t("D2 omission C0076: no mismatch row (road touch)", not ((g09.scenario == o)).any())
    t("D3 baseline C0076 no longer a G02 INFO gap", not ((ex.check_id == "G02") & (ex.item_id == "C0076") & (ex.scenario == b)).any())
    g04 = ex[(ex.check_id == "G04") & (ex.item_id == "C0002")]
    t("D4 C0002 still FAIL on the planner's main-component rule in both scenarios", set(g04.scenario) == {b, o} and (g04.status == "FAIL").all(), str(g04.values.tolist()))
    g10 = ex[(ex.check_id == "G10") & (ex.item_id == "C0002")]
    t("D5 C0002 G10 INFO in both scenarios, line data joined to main at 0.01/10/20 m", set(g10.scenario) == {b, o} and g10.reason.str.count("same line component as the main network").eq(3).all(), str(g10.reason.tolist()))
    t("D6 G10 text does not claim a proven cause", g10.reason.str.contains("NOT established").all())
    for sc, n in ((b, 37), (o, 16)):
        x = ln[(ln.scenario == sc) & (ln.comparison == "len_m_vs_start_snap_plus_end_snap_zero_edge_route")]
        t(f"D7 {sc}: {n} zero-edge routes, all L04 PASS", len(x) == n and (x.status == "PASS").all(), f"n={len(x)}")
    for sc, n in ((b, 41), (o, 20)):
        x = ln[(ln.scenario == sc) & (ln.comparison == "len_m_vs_grid_edges_plus_connectors") & (ln.status == "NOT_VERIFIABLE")]
        t(f"D8 {sc}: L03 NOT_VERIFIABLE count preserved ({n})", len(x) == n, f"n={len(x)}")
    fx = ln[(ln.kind == "facility") & (ln.comparison == "len_m_vs_grid_edges_plus_connectors")]
    t("D9 facility edge+connector rows remain NOT_VERIFIABLE with the start-connector disclosure", (fx.status == "NOT_VERIFIABLE").all() and fx.reason.str.contains("start-connector").all())

bad = [r for r in res if not r[1]]
print(f"\ntests: {len(res)}  failed: {len(bad)}")
sys.exit(1 if bad else 0)
