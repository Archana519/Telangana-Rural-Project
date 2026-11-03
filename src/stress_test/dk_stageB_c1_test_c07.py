"""Regression tests for the C07 facility-invariance rule (no project data needed). Run: python dk_stageB_c1_test_c07.py"""
import sys, math
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from dk_stageB_c1_c07 import classify_facility_change as f
T = []
def t(name, got, want): T.append((name, got[0] == want, got)); 
# 1 unchanged P3 (no penalty), identical geometry
t("T1 P3 unchanged geometry", f(0.0, 1.0, 0.0, 0.0, 0.0, 100.0, 100.0), "PASS")
# 2 unchanged geometry with penalty on
t("T2 penalty unchanged geometry", f(0.0, 4.0, 0.0, 0.0, 0.0, 100.0, 100.0), "PASS")
# 3 changed + removed-penalty evidence + calibrated + cheaper on new surface (observed Zphs/Sub Centre pattern)
t("T3 changed, explained (Sub Centre-like: longer, cheaper)", f(28.284, 4.0, 44.142, 0.0, 0.0, 256.511, 357.692), "INFO")
# 4 changed, penalty on, but no removed-penalty cell used
t("T4 changed without evidence", f(20.0, 4.0, 0.0, 0.0, 0.0, 100.0, 120.0), "FAIL")
# 5 changed in P3 (mult 1.0): no cost-surface cause can exist
t("T5 changed under P3", f(20.0, 1.0, 10.0, 0.0, 0.0, 100.0, 120.0), "FAIL")
# 6 changed, evidence, but new route is worse on its own surface -> inconsistent
t("T6 new route worse on own surface", f(20.0, 4.0, 10.0, 0.0, 0.0, 150.0, 120.0), "FAIL")
# 7 uncalibrated cost -> explained by geometry, optimality skipped
t("T7 calibration failed", f(20.0, 4.0, 10.0, 0.0, 7.0, 150.0, 120.0), "INFO")
# 8 missing route
t("T8 missing facility route", f(None, 4.0, None, None, None, None, None), "FAIL")
bad = 0
for n, ok, g in T:
    print(("PASS" if ok else "FAIL"), n, "->", g[0], "|", g[1][:90]); bad += (not ok)
print("tests:", len(T), "failed:", bad); sys.exit(1 if bad else 0)
