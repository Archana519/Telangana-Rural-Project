# Executed inside build_report.py: Chapter 9.1 to 9.6 rendered from the data prepared by report_fin_data.py
for _r in C.EVIDENCE:
    if _r[0].startswith("Primary x4 versus P3"):
        _r[1] = "Table @T:recon@ rows R1 to R3; unique house lengths %s m (x4) and %s m (x1) read from evaluation_summary.json of the final-family runs; the route-level P3 reproduction (U01) has not been run for this family." % (N1(e4["houses_primary"]["unique_len_m"]), N1(e1["houses_primary"]["unique_len_m"]))
H(1, "9", "Preliminary Results and Discussion")
tp(426)
para("All figures in this chapter come from the final scenario family: 163 house targets and five facilities (two schools, one sub-centre and two Gram Panchayat headquarters points). The anganwadi is excluded (inputs/EXCLUSIONS.md); the MeeSeva and Directorate of ESD centres have no located coordinate and are not included (inputs/ADMIN_UTILITIES.md). Run %s." % RUN_ID)
H(2, "9.1", "Shared-network results")
table_caption("s2", "Stage B results for S2 (25° slope limit, %d house targets, %d facilities)." % (nH, nF))
_ss = e4["houses_straight_line"]
make_table(["Quantity", "Value"], [
    ["Targets routed", "%d / %d houses; %d / %d facilities" % (hp["n"], nH, e4["facilities_primary"]["n"], nF)],
    ["Network-aware house routes, total length", N2(hp["total_len_m"]) + " m"],
    ["Network-aware house routes, unique length", N2(hp["unique_len_m"]) + " m"],
    ["Independent baseline, total length", N2(ih["total_len_m"]) + " m"],
    ["Independent baseline, unique length", N2(ih["unique_len_m"]) + " m"],
    ["Unique-length saving", "%s m (%.1f%%)" % (N2(sav), 100 * sav / ih["unique_len_m"])],
    ["Roads-only reference, unique length", N2(rr["unique_len_m"]) + " m"],
    ["Facility routes, unique length", N2(e4["facilities_primary"]["unique_len_m"]) + " m"],
    ["Combined (houses + facilities) unique length", N2(e4["combined_primary"]["unique_len_m"]) + " m"],
    ["Attachment counts (houses): road / facility route / house route", "%d / %d / %d" % (e4["attach_class_counts_primary_houses"].get("ROAD", 0), e4["attach_class_counts_primary_houses"].get("FACILITY_ROUTE", 0), e4["attach_class_counts_primary_houses"].get("HOUSE_ROUTE", 0))],
    ["Maximum chain depth; cycles", "%d; %d" % (cn["max_chain_depth"], cn["cycles"])],
    ["Straight-line baseline length (%d infeasible)" % _ss.get("infeasible", 0), N2(_ss["total_len_m"]) + " m"]], [4.3, 2.2], size=10.5)
_st = {r["stratum"]: r for r in CSV(X4, "evaluation_by_stratum.csv") if r["origin"] == "ALL"}
_l, _a, _b = _st[">20m"], _st["<=10m"], _st[">10-20m"]
para(runs("Table %s shows that sharing edges shortens the unique network, mainly for long routes: in the longest stratum (more than 20 m from a road, %s targets) the mean route length is %.1f m network-aware versus %.1f m independent, and %s of those %s routes attach to another house route. In the two shorter strata (up to 10 m, %s targets; 10 to 20 m, %s targets) the means are nearly equal (%.1f vs %.1f m and %.1f vs %.1f m)." % (
    REF["tab:s2"], _l["n_targets"], float(_l["primary_mean_len_m"]), float(_l["independent_mean_len_m"]), _l["attach_HOUSE_ROUTE"], _l["n_targets"], _a["n_targets"], _b["n_targets"],
    float(_a["primary_mean_len_m"]), float(_a["independent_mean_len_m"]), float(_b["primary_mean_len_m"]), float(_b["independent_mean_len_m"]))))
para(runs("Two saving percentages are quoted because they use different comparators against the same independent baseline (%s m unique): %.1f%% is the roads-only shared-edge reference (%s m) and %.1f%% is the two-stage network-aware plan (%s m). Table 12 covers five facilities: the primary school, the high school, the sub-centre and the Damarakunta and Kashireddypally Gram Panchayat headquarters points; both administrative panchayat jurisdiction points are held in the spatial database and routed, and the anganwadi is excluded. Roads were clipped to the village boundary with gpd.clip() before routing. Adding the two Gram Panchayat headquarters points as facility targets shortens the house network by %s m, because some houses attach to the facility routes; against the four-facility verified baseline (5,137.7 m of house routes) the change is %s m." % (
    N2(ih["unique_len_m"]), 100 * sav_ro / ih["unique_len_m"], N2(rr["unique_len_m"]), 100 * sav / ih["unique_len_m"], N2(hp["unique_len_m"]), N1(e4["facility_effect_on_house_unique_len_m"]), N1(5137.706 - hp["unique_len_m"]))))
figure("len", "Unique grid-edge length: independent routes versus the shared network (chart 1 of the final package; model-derived, no field validation).", "chart1_network_lengths.png", 6.0)
table_caption("runs", "Other runs (final scenario family).")
_rows = []
for lab, rn in (("S1, 25°", S1A), ("S2, 10°", S2B), ("S1, 10°", S1B), ("S2, C1 (built-up 3.0), 25°", S2C)):
    ee = EV(rn)
    _rows.append([lab, "%d / %d" % (ee["houses_primary"]["n"], ee["n_house_targets"]), N2(ee["houses_primary"]["unique_len_m"]), N2(ee["houses_independent_baseline"]["unique_len_m"])])
make_table(["Run", "Routed (houses)", "Network unique (m)", "Independent unique (m)"], _rows, [2.3, 1.2, 1.5, 1.5], size=10.5)
_f10 = list(EV(S2B)["failures_primary"].keys())
para(runs("At 10 degrees %d house target%s could not be routed (%s) because their start cells exceed the limit; this is a model constraint, not a statement about the buildings." % (len(_f10), "" if len(_f10) == 1 else "s", ", ".join(_f10) if _f10 else "none")))

# ---------------------------------------------------------------- 9.2
H(2, "9.2", "Facility routes and impact proxies")
_fl = []
for r in FIN_FAC:
    _fl.append("%.1f m (%s%s)" % (float(r["len_m"]), FACN.get(r["facility_id"], r["facility_name"]), "; attached to " + r["attach_parent"] if r["attach_class"] == "FACILITY_ROUTE" else ""))
_i = {k: IMP(X4, k) for k in ("network_primary", "independent_baseline", "straight_line_baseline", "length_only_baseline")}
para(runs("Facility routes are " + ", ".join(_fl[:-1]) + " and " + _fl[-1] + ". Planning facilities first reduces the house unique length by %s m (S2) and %s m (S1). Network-aware house routes: %d routes cross another footprint (%.0f m) against %d for independent routes, %d for straight lines and %d for length-only routes. Penalised-cell length is %.0f m (network) versus %.0f m (independent); route length on slopes above 10 degrees is %.0f m and %s exceeds 25 degrees; about %.0f m lies inside parcels that were invalid in the original cadastral layer and needs visual checking. These are proxies, not ownership or access findings." % (
    N0(e4["facility_effect_on_house_unique_len_m"]), N0(EV(S1A)["facility_effect_on_house_unique_len_m"]), _i["network_primary"]["routes"], _i["network_primary"]["cross"], _i["independent_baseline"]["routes"], _i["straight_line_baseline"]["routes"], _i["length_only_baseline"]["routes"],
    _i["network_primary"]["pen"], _i["independent_baseline"]["pen"], _i["network_primary"]["s10"], "none" if _i["network_primary"]["s25"] == 0 else "%.0f m" % _i["network_primary"]["s25"], _i["network_primary"]["rep"])))

# ---------------------------------------------------------------- 9.3
H(2, "9.3", "Building-penalty variants")
para("Table %s compares the baseline penalty (all three quality classes, multiplier 4) with P1 (plausible only), P2 (plausible and review) and P3 (no penalty), all for S2 at the 25° limit; every run routes %d of %d houses. The shortest unique network is %s (%s m, %.1f%% %s than the baseline %s m); %s has the most routes crossing other footprints (%d, against %d for the baseline), and P1 and P2 cross %d and %d. The saving column compares each run with independent routes planned under the same penalty, so it is not comparable across rows as a length measure. Footprint classes are model-derived and a route that avoids them is not evidence that real compounds are avoided." % (
    REF["tab:pen"], _pv[0][7], nH, _short[0], N1(_short[2]), abs(100 * (_short[2] / _base[2] - 1)), "shorter" if _short[2] < _base[2] else "longer", N1(_base[2]), _most[0], _most[4], _base[4], _pv[1][4], _pv[2][4]))
table_caption("pen", "Building-penalty variants (S2, 25° slope limit, %d house targets)." % nH)
make_table(["Variant", "Penalised classes", "Unique length (m)", "Saving (%)", "Routes crossing other footprints", "Length in other footprints (m)", "Penalised-cell length (m)"],
           [[r[0], r[1], N1(r[2]), "%.1f" % r[3], "%d" % r[4], N1(r[5]), N1(r[6])] for r in _pv], [0.7, 1.5, 0.8, 0.8, 0.9, 0.9, 0.9], size=9)

# ---------------------------------------------------------------- 9.4
H(2, "9.4", "Sensitivity to target-set perturbations")
para(runs("Table %s summarises 20 perturbation runs on the S2 scenario. Every target that could be placed was routed, with %d failures. The unique length per routed target stayed between %.1f m and %.1f m over the 20 runs, against %.1f m for the unperturbed baseline (%s m over %d targets). On targets common to the base and perturbed runs, the mean change in route length per run ranged from %.1f m to %+.1f m and %.0f%% to %.0f%% of targets kept the same attachment class (road, facility or house route). The widest spread in total unique length is for %s (%s m to %s m), because removing a target can remove branches that other houses were sharing. In %d of the ten add runs not all requested synthetic buildings could be placed, which the run checks log as a warning. These perturbations are synthetic sensitivity probes; they do not measure how real segmentation errors would change the plan." % (
    REF["tab:unc"], sum(len(e_[0]["failures_primary"]) for v in _grp.values() for e_ in v),
    min(e_[0]["houses_primary"]["unique_len_m"] / e_[0]["houses_primary"]["n"] for v in _grp.values() for e_ in v), max(e_[0]["houses_primary"]["unique_len_m"] / e_[0]["houses_primary"]["n"] for v in _grp.values() for e_ in v),
    hp["unique_len_m"] / hp["n"], N1(hp["unique_len_m"]), hp["n"], min(_chg), max(_chg), min(_same), max(_same),
    (lambda k: "%d%% %s" % (k[1], "omission" if k[0] == "omit" else "addition"))(max(_grp, key=lambda k: max(e_[0]["houses_primary"]["unique_len_m"] for e_ in _grp[k]) - min(e_[0]["houses_primary"]["unique_len_m"] for e_ in _grp[k]))),
    N0(min(e_[0]["houses_primary"]["unique_len_m"] for e_ in _grp[max(_grp, key=lambda k: max(e_[0]["houses_primary"]["unique_len_m"] for e_ in _grp[k]) - min(e_[0]["houses_primary"]["unique_len_m"] for e_ in _grp[k]))])),
    N0(max(e_[0]["houses_primary"]["unique_len_m"] for e_ in _grp[max(_grp, key=lambda k: max(e_[0]["houses_primary"]["unique_len_m"] for e_ in _grp[k]) - min(e_[0]["houses_primary"]["unique_len_m"] for e_ in _grp[k]))])), _unpl)))
table_caption("unc", "Perturbation runs, mean over five seeds (range in brackets).")
_ur = []
for (kind, pct), v in sorted(_grp.items(), key=lambda kv: (kv[0][0] != "add", kv[0][1])):
    ul = [e_[0]["houses_primary"]["unique_len_m"] for e_ in v]; nr = [e_[0]["houses_primary"]["n"] for e_ in v]
    _ur.append(["%s %d%%" % (kind.capitalize(), pct), "%.1f" % (sum(nr) / len(nr)), "%s (%s–%s)" % (N1(sum(ul) / len(ul)), N1(min(ul)), N1(max(ul))), "%.1f" % (sum(u / n for u, n in zip(ul, nr)) / len(ul)),
                "%.1f" % (sum(e_[1]["routes"] for e_ in v) / len(v)), "%.0f" % (sum(e_[2] for e_ in v) / len(v))])
make_table(["Perturbation", "Targets routed", "Unique length (m)", "Length per routed target (m)", "Routes crossing other footprints", "Same attachment class (%)"], _ur, [1.0, 0.8, 1.7, 1.0, 1.0, 0.8], size=9)

# ---------------------------------------------------------------- 9.5 (the reconciliation table is built from the final run)
H(2, "9.5", "Connectivity")
_cc = CSV(X4, "connectivity_checks.csv")
_off = [r for r in _cc if r["reaches_main_road_component"] != "True"]
_offh = [r for r in _off if r["kind"] == "house"]
_c1 = CSV(X1, "connectivity_checks.csv")
_main = sum(r["reaches_main_road_component"] == "True" for r in _cc); _tot = len(_cc)
_hmain = sum(r["reaches_main_road_component"] == "True" for r in _cc if r["kind"] == "house")
_t0 = _offh[0] if _offh else None
_tsrow = next((r for r in CSV(X4, "target_status.csv") if _t0 and r["planner_key"] == _t0["target_id"]), None)
para(runs(X("Two connectivity definitions are in use and they give different counts. The planner-level check (the route ends on the declared network and the cell graph is connected) holds for all %d routed targets. The stricter check, that the route ends on the main road component of %s cells, holds for %d of %d targets, or %d of %d houses. Both statements concern one target, C0002 (candidate 2, house H0001, class review): its route is %.2f m long, starts %.2f m from the road layer and ends on a 5-cell road component (component 10; component 11 in the 10 degree runs) that is cut off from the main component inside the planning grid. The target, route length and component are identical in the x4 and x1 runs, so the two penalty configurations do not differ in connectivity. Table @T:recon@ lists the evidence for each statement." % (
    _tot, "{:,}".format(cn["road_component_sizes"][0]), _main, _tot, _hmain, nH, float(_tsrow["primary_len_m"]) if _tsrow else 0, float(_tsrow["dist_to_road_m"]) if _tsrow else 0))))
C.RECON = [
 ["R1", "S2_fac_C0_s25_final_x4 (primary, x4)", "planner_connected_to_roads and cell_graph_connected, all %d targets (%d houses, %d facilities)" % (_tot, nH, nF), "%d of %d true" % (sum(r["planner_connected_to_roads"] == "True" for r in _cc), _tot), "connectivity_checks.csv", "Planner-level connection holds for every routed target."],
 ["R2", "S2_fac_C0_s25_final_x4 (primary, x4)", "reaches_main_road_component: chain terminal lies on the %s-cell main road component" % "{:,}".format(cn["road_component_sizes"][0]),
  "%d of %d (houses %d of %d, facilities %d of %d). The exception is target C0002 (candidate 2, house H0001, class review, %.2f m from the nearest road); its route is %.2f m and ends on road component 10 (5 cells)" % (_main, _tot, _hmain, nH, _main - _hmain, nF, float(_tsrow["dist_to_road_m"]) if _tsrow else 0, float(_tsrow["primary_len_m"]) if _tsrow else 0),
  "connectivity_checks.csv; road_components.csv", "Different definition from R1. One target ends on a fragment cut off from the main component inside the grid."],
 ["R3", "S2_fac_C0_s25_final_x1 (x1)", "Same two fields", "%d of %d and %d of %d. Same target C0002, same component 10" % (sum(r["planner_connected_to_roads"] == "True" for r in _c1), len(_c1), sum(r["reaches_main_road_component"] == "True" for r in _c1), len(_c1)), "connectivity_checks.csv; target_status.csv", "The x1 and x4 runs agree on connectivity: %d of %d (all targets) and %d of %d (houses only) describe the same single target." % (_main, _tot, _hmain, nH)],
 ["R4", "S2_fac_C0_s10_final (10 degree limit)", "Same fields", "%d of %d reach the main component; C0002 on component 11" % (sum(r["reaches_main_road_component"] == "True" for r in CSV(S2B, "connectivity_checks.csv")), len(CSV(S2B, "connectivity_checks.csv"))), "connectivity_checks.csv", "Different run and component numbering; same target."],
 ["R5", "S2_fac_C0_s25_final_x4 and _x1 (audit v2)", "Check G04: chain terminal on the planner's main component; P01: planner evidence for houses", "Per scenario the audit lists the C0002 attachment as FAIL under G04 and P01:house (see the audit summary)", "_connectivity_audit_v2/connectivity_summary.csv; audit_summary.md", "The audit counts the C0002 attachment as FAIL. The earlier note '31 passed, 0 failed' does not match the file; the file is followed."],
 ["R6", "S2_fac_C0_s25_final_x4 and _x1 (acceptance tests)", "Per-run acceptance checks", "0 FAIL; the off-main attachment is INFO", "acceptance_tests.csv", "The acceptance checks rate the off-main attachment as INFO, the audit as FAIL: two severity rules applied to the same data, not two different data."],
 ["R7", "Cause of component 10", "Chain of road-line cells between component 10 and the main component", "36 road cells in the minimum blocked chain: 33 outside the polygon and 3 inside within 8.4 m of it. Nearest main-component cell is 155.24 m away in the road-cell diagnostic and 151.55 m in the audit gate note", "_boundary_mask_diag_v1; _chain_cell_reasons_v1 (verified baseline run)", "Consistent with boundary truncation of the planning domain. The difference between the two distances is not reconciled. Whether the roads connect in reality is unknown."]]
table_caption("recon", "Connectivity reconciliation: which run, target and definition each statement refers to.")
make_table(["No.", "Run", "Metric and definition", "Observed", "Evidence file", "Reading"], [[X(c) for c in r] for r in C.RECON], [0.42, 0.93, 1.18, 1.5, 1.27, 1.4], size=7)
para(runs(X("The disconnection is explained in the road-cell and boundary diagnostics (run on the verified baseline) as a boundary-truncation effect: the shortest chain of road cells that would join component 10 to the main component has 36 cells, 33 outside the village polygon and 3 inside within 8.4 m of it, and cells outside the polygon are masked as impassable. This is an interpretation of planning-grid evidence. The roads outside the polygon were not checked for existence or usability, the polygon itself was not independently validated, and no route was planned outside it. The audit and acceptance validator classify the same route differently (FAIL and INFO), and the distance from component 10 to the main component differs between two diagnostics (155.24 m and 151.55 m); neither difference is resolved here. The issue is therefore open, not closed. On the TGRAC road lines, which also cover the part outside the polygon, the same road is connected to the main network.")))
figure("map", "Damarakunta: alternative candidate routes versus the final shared network (map 4 of the final package; draft, model-derived; imagery licence unresolved).", "map4_alternatives_vs_network.png", 6.3)
H(2, "9.6", "Discussion")
para("The results support C2 as a working, reproducible planner at planning level: shared-edge accounting lowers unique length and the building penalty trades some length for fewer footprint crossings. The C1 experiments are run on the real village and show the plan is fairly stable under synthetic omissions and additions, but they do not measure real segmentation error. Adding administrative utilities (Gram Panchayat headquarters points) changes the house network slightly because houses can attach to the new facility routes, which shows that the facility set matters for the baseline numbers. The results do not support claims about cost in rupees, constructability or real-world connectivity, and C3 is untested.")
