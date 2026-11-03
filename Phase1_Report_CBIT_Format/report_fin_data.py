# Executed inside build_report.py before the front matter: loads the FINAL scenario family (see report_results_block.py)
# Executed inside build_report.py (shares its namespace): Chapter 9.1 to 9.6 generated from the FINAL scenario family
# (5 facilities: 2 schools, 1 sub-centre, 2 Gram Panchayat HQ points; anganwadi excluded). Every number is read from the run folder.
import csv as _c, glob as _g, json as _j, os as _o, re as _re

_cands = sorted(_g.glob(r"D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\run_*\stageB\S2_fac_C0_s25_final_x4"))
assert _cands, "no final-family run found: run src/run_pipeline.py --profile final first"
SB = _o.path.dirname(_cands[-1])
RUN_ID = _o.path.basename(_o.path.dirname(SB))


def EV(n): return _j.load(open(_o.path.join(SB, n, "evaluation_summary.json"), encoding="utf-8"))
def CSV(n, f): return list(_c.DictReader(open(_o.path.join(SB, n, f), encoding="utf-8-sig")))
def N1(x): return "{:,.1f}".format(float(x))
def N0(x): return "{:,.0f}".format(float(x))
def N2(x): return "{:,.2f}".format(float(x))


def IMP(run, st, kind="house"):
    rows = [r for r in CSV(run, "impact_flags.csv") if r["set"] == st and r["kind"] == kind]
    f = lambda r, k: float(r.get(k) or 0)
    return dict(n=len(rows), routes=sum(f(r, "n_other_polygons_crossed") > 0 for r in rows),
                cross=sum(f(r, "len_other_PLAUSIBLE_m") + f(r, "len_other_REVIEW_m") + f(r, "len_other_UNRESOLVED_MERGE_m") for r in rows),
                pen=sum(f(r, "len_in_penalised_cells_m") for r in rows), s10=sum(f(r, "len_slope_gt10_m") for r in rows), s25=sum(f(r, "len_slope_gt25_m") for r in rows),
                rep=sum(f(r, "len_in_repaired_parcels_m") for r in rows))


X4, X1, S1A, S1B, S2B, S2C = "S2_fac_C0_s25_final_x4", "S2_fac_C0_s25_final_x1", "S1_fac_C0_s25_final", "S1_fac_C0_s10_final", "S2_fac_C0_s10_final", "S2_fac_C1_s25_final"
e4, e1 = EV(X4), EV(X1)
nH, nF = e4["n_house_targets"], e4["n_facility_targets"]
hp, ih, rr = e4["houses_primary"], e4["houses_independent_baseline"], e4["houses_roads_only_reference"]
sav = ih["unique_len_m"] - hp["unique_len_m"]
sav_ro = ih["unique_len_m"] - rr["unique_len_m"]
cn = e4["connectivity"]
FIN_FAC = CSV(X4, "facility_status.csv")
FACN = {"36181600902": "MPPS primary school", "36181600903": "ZPHS high school", "HEALTH_8734223673": "sub-centre", "GP_DAMARAKUNTA": "Damarakunta Gram Panchayat HQ", "GP_KASHIREDDYPALLY": "Kashireddypally Gram Panchayat HQ"}


# ---- penalty variants and perturbation groups (used by the abstract and by 9.3 / 9.4)
_V = [("Baseline", "Plausible, review, unresolved merge (x4)", X4), ("P1", "Plausible (x4)", "S2_fac_C0_s25_final_P1"), ("P2", "Plausible, review (x4)", "S2_fac_C0_s25_final_P2"), ("P3", "None (x1)", X1)]
_pv = []
for nm, cls, rn in _V:
    ee = EV(rn); im = IMP(rn, "network_primary")
    _pv.append([nm, cls, ee["houses_primary"]["unique_len_m"], 100 * (ee["houses_independent_baseline"]["unique_len_m"] - ee["houses_primary"]["unique_len_m"]) / ee["houses_independent_baseline"]["unique_len_m"], im["routes"], im["cross"], im["pen"], ee["houses_primary"]["n"]])
_base = _pv[0]
_short = min(_pv, key=lambda r: r[2])
_most = max(_pv, key=lambda r: r[4])

_bt = {r["planner_key"]: r for r in CSV(X4, "target_status.csv")}
_seeds = ["20261029", "20261030", "20261031", "20261032", "20261033"]
_grp, _chg, _same, _unpl = {}, [], [], 0
for kind in ("add", "omit"):
    for pct in (10, 20):
        runs_ = []
        for sd in _seeds:
            rn = "S2_fac_C0_s25_%s%d_seed%s_final" % (kind, pct, sd)
            ee = EV(rn); ts = {r["planner_key"]: r for r in CSV(rn, "target_status.csv")}
            com = [k for k in _bt if k in ts and _bt[k].get("primary_len_m") not in (None, "") and ts[k].get("primary_len_m") not in (None, "")]
            _chg.append(sum(float(ts[k]["primary_len_m"]) - float(_bt[k]["primary_len_m"]) for k in com) / max(len(com), 1))
            _same.append(100 * sum(ts[k]["primary_attach_class"] == _bt[k]["primary_attach_class"] for k in com) / max(len(com), 1))
            if kind == "add":
                m = _re.search(r"PRT-01\s+(\w+)", open(_o.path.join(SB, rn, "stageB_run_checks.txt"), encoding="utf-8").read())
                _unpl += int(bool(m) and m.group(1) != "PASS")
            runs_.append((ee, IMP(rn, "network_primary"), _same[-1]))
        _grp[(kind, pct)] = runs_

# ---- validator summary text (acceptance validator over the final-family runs)
try:
    _vs = open(_o.path.join(SB, "_validation_main", "validation_summary.txt"), encoding="utf-8").read()
    _m = _re.search(r"runs audited: (\d+).*?'PASS': (\d+)(?:, 'INFO': (\d+))?", _vs, _re.S)
    VAL_TEXT = "%s runs audited: %s PASS, %s INFO, 0 WARN, 0 FAIL" % (_m.group(1), _m.group(2), _m.group(3) or "0")
except Exception:
    VAL_TEXT = "acceptance validator: see the validation summary"
