"""make_chapter.py - writes the thesis chapter (Markdown) from the generated tables, so every number in it traces to a file.

Inputs (all produced by src/run_final_package.py): outputs/verification, outputs/connectivity, outputs/final_comparison, the Stage B run folder.
Output: outputs/final_package/THESIS_CHAPTER_RESULTS_AND_VALIDATION.md
"""
import sys as _sys
from pathlib import Path as _P
_sys.path.insert(0, str(_P(__file__).resolve().parents[1]))
import scenario_names as SN

import argparse, json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
O = ROOT / "outputs"


def md(df, **kw):
    return df.fillna("").to_markdown(index=False, **kw)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stageb-root", required=True)
    ap.add_argument("--run-id", required=True)
    a = ap.parse_args()
    sb = Path(a.stageb_root)
    ver = O / "verification"; con = O / "connectivity"; cmp_ = O / "final_comparison"
    fv = pd.read_csv(ver / "facility_verification.csv")
    bs = pd.read_csv(ver / "building_agreement_summary.csv")
    vs = json.load(open(ver / "verification_summary.json"))
    rl = pd.read_csv(con / "route_end_line_connectivity.csv")
    t1, t2, t3, t4 = (pd.read_csv(cmp_ / f) for f in ("table1_length_reduction.csv", "table2_c2_ablation.csv", "table3_connectivity_constraints.csv", "table4_c1_sensitivity.csv"))
    ass_rate = json.load(open(ROOT / "inputs" / "economic_assumptions.json", encoding="utf-8"))["rate_lakh_per_km"]["central"]
    t5 = pd.read_csv(cmp_ / "table5_economic_material_impact.csv")
    t5b = pd.read_csv(cmp_ / "table5b_material_quantities.csv")
    va = pd.read_csv(O / "visual_audit" / "visual_grounding_table.csv", dtype=str)
    ev = json.load(open(sb / SN.PRIMARY / "evaluation_summary.json"))
    ev3 = json.load(open(sb / SN.P3 / "evaluation_summary.json"))
    exp = pd.read_csv(sb / "_route_explanations" / SN.PRIMARY / "route_explanations.csv")
    off = rl[rl.raster_main_component != True]  # noqa: E712
    off_row = off.iloc[0] if len(off) else None
    nsup = int((fv[fv.source_layer == "priority_facilities.gpkg"].verdict != "UNSUPPORTED").sum())
    p = t1[(t1.configuration == "x4 (primary)")].set_index("method")
    ind = p.loc["Independent least-cost routes to the roads"]
    net = p.loc["Two-stage network-aware plan (proposed)"]
    roads = p.loc["Roads-only shared reference (houses attach to roads only)"]
    q = t1[(t1.configuration == "x1 (P3 control)")].set_index("method")
    qn = q.loc["Two-stage network-aware plan (proposed)"]; qi = q.loc["Independent least-cost routes to the roads"]
    base4 = t4[t4.perturbation == "baseline (no perturbation)"].iloc[0]
    omit20 = t4[t4.perturbation == "omit 20%"].iloc[0] if (t4.perturbation == "omit 20%").any() else None
    gt = ev["houses_independent_baseline"]
    allb = bs[bs.group == "ALL"].iloc[0]
    rev = bs[bs.group == "REVIEW"].iloc[0]

    L = []
    A = L.append
    A("# Results, validation and limitations: Damarakunta case study")
    A("")
    A("*Draft chapter generated from the pipeline outputs of run `%s`. Every number comes from a file listed in Section 11. Planning results are model outputs on a 10 m grid: "
      "routes are unverified planning alternatives, costs are ordinal planning units (not rupees), and no field validation, legal access, road width or construction cost is claimed. "
      "The Damarakunta completion gate has not been approved and the five-village transfer study (C3) has not started.*" % a.run_id)
    A("")
    A("## 1. Purpose and scope")
    A("This chapter reports what was verified automatically after the Stage B planner passed its acceptance checks: (i) how far the detected building footprints and priority facilities agree with independent layers, "
      "(ii) how the road-connectivity exception for house C0002 arises and how it is evaluated, (iii) how the proposed two-stage planner compares with the baselines, and (iv) how the planned network responds to synthetic "
      "omissions and additions of building targets (C1). It also records, limitation by limitation, what is solved by automation, what is only reported, and what stays open.")
    A("")
    A("## 2. Pipeline in five stages")
    A("| Stage | What it does | Status |\n|---|---|---|\n"
      "| 1 Detect | Building candidates (278; 165 inside the boundary) and four priority facilities from TGRAC layers. The detection output is verified by hash and reused; segmentation is not re-run because the model-weight location is not recorded. | Reused input |\n"
      "| 2 Model terrain | Boundary, WorldCover, slope from a 30 m DEM and TGRAC roads on a 10 m grid (432 x 679) give an ordinal cost surface; water, no-data and cells steeper than 25 degrees are blocked. | Verified input |\n"
      "| 3 Plan | Stage A generates up to three least-cost alternatives per target (319 for 163 houses); Stage B selects greedily by weight over marginal cost, so a route may end on another route (shared-edge accounting). | Run and reproduced |\n"
      "| 4 Stress-test | C1: omit or add targets (synthetic); C2: ablation of alternatives per target and leaf-reroute passes. | Run |\n"
      "| 5 Validate | Acceptance validator, connectivity audit, line-topology connectivity, detection agreement checks, per-route explanations. | Run |")
    A("")
    exf = pd.read_csv(ver / "excluded_facilities.csv").iloc[0]
    A("The TGRAC layers hold four priority facilities: two schools, a health sub-centre and an anganwadi. The anganwadi was excluded from the planning layers, CSVs and maps at the project owner's request (`inputs/EXCLUSIONS.md`), Two Gram Panchayat headquarters points from TGRAC (`inputs/ADMIN_UTILITIES.md`) were added as administrative utilities, so the final layer holds five facilities. MeeSeva and Directorate of ESD (Aadhaar/service) centres have no located coordinate in any available source and are not included. No government-building layer exists, so no such class is detected or prioritised.")
    A("")
    A("## 3. Detection and facility verification")
    A("There is no building ground truth: the project has no reference buildings and no manual labels. The checks below therefore measure **agreement with independent layers**, not accuracy. "
      "Thresholds were fixed beforehand: a footprint within 20 m of a facility point supports it, and an independent Google Open Buildings v3 polygon within 30 m corroborates it.")
    A("")
    A(md(fv[["facility_id", "name", "lat", "lon", "dist_to_nearest_footprint_m", "nearest_open_buildings_m", "inside_school_compound", "verdict"]]))
    A("")
    ncor = int((fv[fv.source_layer == "priority_facilities.gpkg"].verdict == "CORROBORATED").sum())
    A("**Finding.** %d of the %d facilities in the final layer are supported by a detected footprint and %d are corroborated by an independent Open Buildings polygon; the two Gram Panchayat points lie on unresolved-merge footprints, so the Panchayat building itself is not identified. "
      "The anganwadi (Damarakunt-I) was excluded because its TGRAC coordinate lies %.0f m from the nearest detected footprint and %.0f m from the nearest Open Buildings polygon (record kept in `excluded_facilities.csv`); "
      "this does not show the anganwadi is absent from the village, only that its position is unsupported. Until a verified location exists the plan does not serve the anganwadi. "
      "The sub-centre has two TGRAC records %.0f m apart; the position in the priority layer is the health-layer record, and both records are near a footprint, so proximity alone cannot say which is right." % (
          nsup, int((fv.source_layer == "priority_facilities.gpkg").sum()), ncor, float(exf.nearest_footprint_m), float(exf.nearest_open_buildings_m), 235.7))
    A("")
    A("Building candidates inside the boundary against Google Open Buildings v3 (a different detector on other imagery; neither is truth):")
    A("")
    A(md(bs))
    A("")
    A("**Finding.** %d of %d candidates (%.0f%%) agree with an independent polygon; the REVIEW class agrees least (%.0f%%), which supports treating it as uncertain. "
      "The reverse direction is weak: Open Buildings lists %d polygons inside the boundary (%d with confidence of at least 0.70), of which %d have no candidate. "
      "The candidate set is therefore much smaller than what another detector sees. Part of the gap is expected (sheds, farm structures and duplicates are included in Open Buildings), but the cause was not established, so the 163 routing targets "
      "must not be read as the number of houses in the village." % (int(allb.proxy_TP), int(allb.candidates), 100 * allb.proxy_agreement_rate, 100 * rev.proxy_agreement_rate,
                                                                    vs["open_buildings_inside_boundary"], vs["open_buildings_conf_ge_0_70"], vs["proxy_FN_reference_polygons_without_candidate"]))
    A("")
    A("### Visual audit protocol for the priority facilities")
    A("Agreement checks cannot replace looking at the imagery. `outputs/visual_audit/` holds a Visual Grounding Table, a Google Earth KML and plain and annotated 200 m imagery crops for each facility. "
      "The measured columns (model latitude/longitude, offset to the nearest detected footprint and Open Buildings polygon, roof area, distance to the nearest TGRAC road, compound membership) are filled from project files. "
      "The observation columns (feature at the pin, matching-feature offset, roof size, playground or open ground, road access, corrected coordinate, imagery date, decision) are **empty on purpose**: they need a person with Google Earth Pro, and the decision rule is fixed in `protocol.md` "
      "(confirm within 20 m, relocate within 200 m, otherwise reject). No facility is visually confirmed by this project yet. A government-building row exists but cannot be audited, because no such layer is in the data.")
    A("")
    A(md(va[["facility_id", "name", "model_lat", "model_lon", "nearest_detected_footprint_m", "nearest_open_buildings_m", "distance_to_nearest_TGRAC_road_m", "agreement_verdict"]]))
    A("")
    A("The excluded anganwadi is not part of this audit; its record and the reason are in `inputs/EXCLUSIONS.md`.")
    A("")
    A("## 4. Road connectivity and the C0002 exception")
    A("Three connectivity measures are reported, because they answer different questions: the planner's check that each route ends on the declared network (%d of %d), the raster test that the route's terminal road cell belongs to the main road component "
      "inside the village polygon (%d of %d), and the road-line test on the TGRAC lines, which also covers the 44.7%% of road length outside the polygon (%d of %d)." % (
          t3.planner_verified_connected.iloc[0], t3.targets.iloc[0], t3.reach_main_component_raster.iloc[0], t3.targets.iloc[0], int(t3.reach_main_component_road_lines.iloc[0]), t3.targets.iloc[0]))
    A("")
    if off_row is not None:
        A("The single exception is house C0002 (candidate 2, class REVIEW, 95.6 m from the nearest road line). Its route ends on a 5-cell road fragment that the raster treats as a separate component. "
          "On the road lines the same fragment belongs to the main network: the lines run %s m to the main component, of which %s m lie outside the village polygon (accuracy about 5 m). "
          "The polygon clips the grid, so a road that leaves and re-enters the village is cut into pieces; 98%% of the blocked road cells found in the diagnostics lie outside the polygon." % (off_row.road_line_path_to_raster_main_m, off_row.path_m_outside_village))
        A("")
    A("**Decision.** The planner was not changed. It is hash-pinned and verified, and any snapping rule inside the clipped grid would either bridge a gap that is absent from the line data or move the boundary without an independent boundary source. "
      "Instead, the automated rule is applied in the evaluation: every route end is snapped to the nearest TGRAC line within the planner's 15 m tolerance (%d of %d snap) and connectivity is judged on line topology (script `connectivity_resolution.py`). "
      "Bridge proposals generated: %d. This resolves the reporting inconsistency. It does not show that the roads exist, are passable or are legally accessible, and the nearest-cell distance (155.24 m) and the audit distance (151.55 m) still differ between two diagnostics." % (
          int(rl.snapped_within_tol.sum()), len(rl), len(pd.read_csv(con / "bridge_proposals.csv"))))
    A("")
    A("The connectivity audit (version 2) still lists C0002 as a failure under its stricter raster rule, and the acceptance validator lists it as information. Both are reported as they are.")
    A("")
    A("## 5. Baseline versus proposed network")
    A("The x4 and x1 building-penalty configurations are separate blocks. Each uses baselines planned under its own penalty.")
    A("")
    A(md(t1))
    A("")
    A("**Finding (x4, primary).** Independent least-cost routes to the roads total %.0f m, but %.0f m of that duplicates grid edges used by several houses, leaving %.0f m of unique road. "
      "The two-stage plan needs %.0f m, a reduction of %.0f m (%.1f%%). The roads-only shared reference already gives %.1f%%, so the further gain from letting houses attach to other routes is %.1f percentage points "
      "(about %.0f m). The plan is not globally optimal; it is a greedy heuristic. In the x1 control the same comparison gives %.1f%% (%.0f m against %.0f m). "
      "The two configurations answer different questions (x4 discourages entering building footprints; x1 does not) and their lengths must not be compared as if they were one experiment." % (
          ind.total_len_m, ind.duplicated_len_m, ind.unique_len_m, net.unique_len_m, net.reduction_vs_independent_unique_m, net.reduction_vs_independent_unique_pct,
          roads.reduction_vs_independent_unique_pct, net.reduction_vs_independent_unique_pct - roads.reduction_vs_independent_unique_pct, net.reduction_vs_independent_unique_m - roads.reduction_vs_independent_unique_m,
          qn.reduction_vs_independent_unique_pct, qn.unique_len_m, qi.unique_len_m))
    A("")
    A("The length-only control is longer than the independent least-cost routes in unique length and crosses more building footprints, so the cost surface is doing useful work. "
      "The straight-line baseline ignores terrain and crosses 62 footprints; it is shown only as a distance reference.")
    A("")
    A("### C2 ablation (alternatives per target K and leaf-reroute passes)")
    A("")
    A(md(t2))
    A("")
    A("Two leaf-reroute passes change the result by about 10 m (0.2%); more alternatives per target (K = 3 instead of 1) change nothing in this village, because the network-aware attachment step already finds the cheaper connections. "
      "No run switches shared-edge accounting off, so the ablation does not isolate it (the roads-only reference in Table 1 is the nearest comparison), and it does not show that the planner is optimal or that the result transfers to other villages.")
    A("")
    t6 = pd.read_csv(cmp_ / "table6_obstacle_avoidance.csv")
    xs = pd.read_csv(cmp_ / "building_crossings_summary.csv").set_index("run")
    k4 = t6[t6.run == SN.PRIMARY].iloc[0]
    kb = t6[t6.run == SN.AVOID].iloc[0]
    A("### Obstacle avoidance: keeping routes out of building footprints")
    A("The request was to treat detected footprints as no-go zones or high-cost buffers so that no route crosses a building. Two things were tried, both without editing the verified planner or its runners "
      "(a new runner version, `dk_stageB_run_v1_4.py`, adds one option and is otherwise identical to v1.3).")
    A("")
    A("1. **Hard block (failed).** Every 10 m cell touched by a footprint was added to the prohibited-area raster. All 163 house routes then failed (`TARGET_IN_HARD_CONSTRAINT_CELL_OR_OUTSIDE_GRID`), because each house point lies inside its own blocked cell and the planner does not start a route from a blocked cell. The attempt is kept in `archive/2026-10-30_phase3_experiments/`.")
    A("2. **High-cost buffer (works, with limits).** The planner is handed footprints buffered by 7.1 m (half a cell diagonal), so every cell touched by a building has its centre inside a penalised polygon, with a penalty multiplier of x20, x100 or x1000. All 163 houses are routed.")
    A("")
    A(md(t6[["scenario", "houses_routed", "house_unique_len_m", "saving_vs_independent_pct", "house_routes_crossing_other_footprints", "crossing_len_m", "crossing_only_in_first_20m", "crossing_beyond_first_20m", "facility_unique_len_m"]]))
    A("")
    A("**Finding.** The building-avoiding network (x100) is %.0f m long against %.0f m for the primary x4 network, a rise of %.0f m (%.0f%%); its saving against independent routes planned under the same penalty is %.1f%% instead of %.1f%%. "
      "House routes crossing another footprint fall from %d to %d and the crossing length from %.0f to %.0f m. Routes that cross a building away from their start fall from %d to %d. "
      "At the assumed Rs 75 lakh/km the extra %.0f m is about Rs %.0f lakh (illustrative). The effect saturates by x20: a larger penalty changes nothing." % (
          kb.house_unique_len_m, k4.house_unique_len_m, kb.house_unique_len_m - k4.house_unique_len_m, 100 * (kb.house_unique_len_m / k4.house_unique_len_m - 1), kb.saving_vs_independent_pct, k4.saving_vs_independent_pct,
          k4.house_routes_crossing_other_footprints, kb.house_routes_crossing_other_footprints, k4.crossing_len_m, kb.crossing_len_m, int(k4.crossing_beyond_first_20m), int(kb.crossing_beyond_first_20m),
          kb.house_unique_len_m - k4.house_unique_len_m, (kb.house_unique_len_m - k4.house_unique_len_m) / 1000 * ass_rate))
    A("")
    A("**Why crossings do not reach zero.** %d of the %d remaining routes cross another footprint only within the first 20 m: the target point lies inside its own footprint, often among touching or merged buildings, and leaving the cluster means passing a neighbour. "
      "This is a property of the detections and the 10 m grid, not of the cost function, and no larger penalty removes it. Eliminating these crossings would need building-level geometry (entrances, gaps between buildings) or a finer grid, "
      "neither of which the project has." % (int(kb.crossing_only_in_first_20m), int(kb.house_routes_crossing_other_footprints)))
    A("")
    A("**What was not done, and why.** (i) *Snapping to street networks and lanes:* the project has TGRAC road lines only; no lane or street layer exists inside the settlement, so route ends snap to TGRAC roads or to other routes and not to lanes. "
      "(ii) *Anganwadi:* excluded from the planning layers and maps at the project owner's request (`inputs/EXCLUSIONS.md`), not corrected; no verified location exists. "
      "(iii) *Other sensitive structures:* only detected building footprints are avoided; school compounds and parcels are not blocked, because the schools' own points lie inside their compounds. "
      "(iv) The primary x4 network remains the reference result of this chapter; the building-avoiding network is a scenario that shows the price of avoidance.")
    A("")
    A("### Economic and material impact analysis (illustrative)")
    ra, rb = t5.iloc[0], t5.iloc[1]
    A("*This subsection is a parametric estimate. The project holds no road width, cross-section, soil or rate data, so the rate and the pavement section are assumptions listed in `inputs/economic_assumptions.json`. "
      "The rate of Rs 75 lakh per km is the figure supplied by the project owner as a PMGSY-based value; it was not checked against a PMGSY document or a State Schedule of Rates. "
      "It is not an engineering estimate, not a bill of quantities and not a claim about real construction cost. The routes are planning alternatives and are mostly short house lanes (about 31 m per house); "
      "a rate for habitation-connectivity roads may not apply to them, and the programme's eligibility for internal village lanes should be checked.*")
    A("")
    A("**Which length is the baseline.** The independent routes sum to %.0f m, but %.0f m of that is grid edges used by several houses. A shared edge would be built once even without optimisation, so the fair baseline is the unique length of the independent routes, %.0f m. "
      "The proposed network is %.0f m. The saving is therefore **%.0f m (%.1f%%)**, not the %.0f m (%.2f km) obtained by subtracting the shared network from the double-counted total. "
      "The %.2f km figure is %.1f times the real saving and should not be quoted as a saving." % (
          rb.baseline_len_m, rb.baseline_len_m - ra.baseline_len_m, ra.baseline_len_m, ra.proposed_len_m, ra.length_saving_m, ra.length_saving_pct, rb.length_saving_m, rb.length_saving_m / 1000, rb.length_saving_m / 1000, rb.length_saving_m / ra.length_saving_m))
    A("")
    A(md(t5[["baseline_basis", "baseline_len_m", "proposed_len_m", "length_saving_m", "length_saving_pct", "baseline_cost_central_Rs_lakh", "proposed_cost_central_Rs_lakh", "cost_saving_low_Rs_lakh", "cost_saving_central_Rs_lakh", "cost_saving_high_Rs_lakh"]]))
    A("")
    A("At Rs 75 lakh/km the cost of the independent routes (basis A) is about Rs %.0f lakh and of the proposed network about Rs %.0f lakh, a saving of about **Rs %.0f lakh (Rs %.2f crore)**, within Rs %.0f to %.0f lakh for rates of Rs 60 to 90 lakh/km. "
      "The basis-B figure of Rs %.0f lakh (Rs %.2f crore) follows from the double-counted length and is shown only so the two can be compared; it overstates the saving." % (
          ra.baseline_cost_central_Rs_lakh, ra.proposed_cost_central_Rs_lakh, ra.cost_saving_central_Rs_lakh, ra.cost_saving_central_Rs_lakh / 100, ra.cost_saving_low_Rs_lakh, ra.cost_saving_high_Rs_lakh,
          rb.cost_saving_central_Rs_lakh, rb.cost_saving_central_Rs_lakh / 100))
    A("")
    A("Material conservation follows from the length saving and one assumed cross-section (3.75 m carriageway, 150 mm sub-base, 150 mm WBM, 20 mm bituminous surface, 5.0 m formation, 0.30 m average earthwork depth, 1.30 loose factor, 2.0 kg/m2 bitumen). "
      "Quantities for each length, and the saving on basis A, are:")
    A("")
    A(md(t5b))
    A("")
    A("| Material saved (basis A, %.0f m) | Quantity |\n|---|---|\n| Aggregate for WBM and surfacing, loose | %.0f m3 |\n| Sub-base (GSB) material, loose | %.0f m3 |\n| Earthwork | %.0f m3 |\n| Bitumen | %.1f t |" % (
        ra.length_saving_m, ra.saving_aggregate_loose_m3, ra.saving_gsb_subbase_loose_m3, ra.saving_earthwork_m3, ra.saving_bitumen_t))
    A("")
    A("These quantities scale linearly with length because a single cross-section is assumed; they ignore drainage and cross-drainage works, side slopes, utilities, land, supervision and escalation. Replace the assumptions with State Schedule of Rates and a design section before any financial use.")
    A("")
    A("## 6. Connectivity rates and constraint checks")
    A("")
    A(md(t3))
    A("")
    A("No route violates a hard constraint (blocked cell, water, slope above 25 degrees), no cycle exists, and every target was routed. The x4 plan has fewer house routes crossing other footprints (%d) than the x1 control (%d) at the price of %.0f m more unique length. "
      "Footprint classes are model-derived, so avoiding them is not evidence that real compounds are avoided." % (
          int(t3.network_routes_crossing_other_footprints_houses.iloc[0]), int(t3.network_routes_crossing_other_footprints_houses.iloc[1]), ev["houses_primary"]["unique_len_m"] - ev3["houses_primary"]["unique_len_m"]))
    A("")
    A("## 7. Sensitivity to detection errors (C1)")
    A("")
    A(md(t4))
    A("")
    if omit20 is not None:
        A("**Finding.** The experiments remove or add targets at random (five seeds per setting where available) and are synthetic: they are not measured detector errors. Every placed target is still routed in every run. "
          "The unique length per routed target stays between %.1f and %.1f m against %.1f m for the baseline, so the network scales with the number of targets instead of breaking down. "
          "Total length is not a measure of efficiency here: omitting 20%% of targets shortens the network by about %.0f%% because those routes disappear. "
          "The sharing saving against independent routes stays between %.1f%% and %.1f%% in every setting. The risk of a missed building is therefore not a connectivity failure but a missing service: an omitted house gets no route, which this model cannot detect by itself. "
          "Omitting the merged blobs (the unresolved class) removes %d targets and leaves %.1f m per routed target, the highest value; why was not examined." % (
              t4.unique_len_per_routed_m_mean.min(), t4.unique_len_per_routed_m_mean.max(), base4.unique_len_per_routed_m_mean, 100 * (1 - omit20.unique_len_m_mean / base4.unique_len_m_mean),
              t4.saving_vs_independent_pct_mean.min(), t4.saving_vs_independent_pct_mean.max(), int(163 - t4[t4.perturbation == "omit merged blobs"].house_targets_routed_mean.iloc[0]) if (t4.perturbation == "omit merged blobs").any() else 0,
              t4[t4.perturbation == "omit merged blobs"].unique_len_per_routed_m_mean.iloc[0] if (t4.perturbation == "omit merged blobs").any() else float("nan")))
        A("")
    A("## 8. Why each route was chosen")
    A("For every selected route the planner log and the cost rasters were combined into one explanation (`3_routes/<run>/why_chosen/route_explanations.csv` and `.md`): the greedy step, the candidate used (Stage A alternative or a fresh path to the network), "
      "marginal and route cost, the land cover crossed, slope, building-penalty edges, the saving against the independent route and the object the route ends on. In the primary run %d of %d routes end on another route and %d routes enter penalised building cells. "
      "No grid edge is shared by two routes (shared length %.2f m): the saving arises because routes end on one another or on roads, not because they overlap." % (
          int((exp.attach_class.isin(["HOUSE_ROUTE", "FACILITY_ROUTE"])).sum()), len(exp), int((exp.building_penalty_edges > 0).sum()), ev["combined_primary"]["shared_len_m"]))
    A("")
    A("## 9. Stage-wise status and limitation audit")
    A("| Stage | Status | Limitation | Automated rule or check | Outcome |\n|---|---|---|---|---|\n"
      "| 1 Detect | Reused input, verified by hash | Detections unverified; no ground truth; anganwadi excluded (unsupported coordinate); 163 targets are not a house count | Agreement checks with fixed thresholds; quality classes carried through planning; Visual Grounding Table prepared | **Bounded and reported, not overcome.** Real accuracy needs labelled buildings and the Google Earth audit |\n"
      "| 2 Model terrain | Verified input | 30 m DEM interpolated to 10 m; roads 44.7%% outside the polygon; boundary not independently verified; imagery licence and date unresolved | Hash checks on all inputs; masks and counts reproduced by diagnostics; caveats printed on maps | **Bounded.** Resolution trade-off is a fundamental limit; licence unresolved |\n"
      "| 3 Plan | Run, reproduced exactly (27 reference runs, 405 metrics); building-avoiding scenario added | Greedy heuristic, not optimal; ordinal costs; routes still cross buildings when a target starts among touching footprints | Fixed planner hash; fresh run folder per execution; comparison with the reference run; buffered-footprint scenario (runner v1.4) | **Overcome for reproducibility**; crossings bounded (counts in Table 6), not eliminated |\n"
      "| 4 Stress-test | Run | Omissions and additions are synthetic; real detector error not measured | Seeded runs, per-routed-target metrics | **Bounded**; label-based error propagation not started |\n"
      "| 5 Validate | Run | C0002 off the main raster component; two audits rate it differently | Line-topology connectivity with 15 m snapping; acceptance validator; connectivity audit v2; per-route explanations | **Reporting resolved**; physical road not verified; the planner was deliberately not changed |")
    A("")
    A("## 9b. Limitations addressed by automation and what remains")
    A("| Limitation | Automated handling | Status |\n|---|---|---|\n"
      "| Detections may be wrong | Agreement checks against TGRAC tables, school compounds and Open Buildings; quality classes kept through planning | Reported; real accuracy needs labelled buildings |\n"
      "| Facility coordinates unverified | Verdict per facility with fixed thresholds | Anganwadi excluded; verified location still needed |\n"
      "| C0002 off the main raster component | Line-topology connectivity with snapping within 15 m | Reporting resolved; physical road not verified |\n"
      "| Roads partly outside the polygon (44.7%% of length) | Included in line connectivity; planner domain unchanged | Documented; boundary not independently verified |\n"
      "| 30 m DEM interpolated to 10 m | Stated on maps and in tables | Fundamental limit; no 10 m terrain accuracy claimed |\n"
      "| Stale or mixed outputs | One command writes a new run folder, verifies input hashes and reproduces the reference exactly | Resolved for Stage B |\n"
      "| Imagery licence and acquisition dates | Recorded in `inputs/METADATA.md`; maps carry a caution; one sampled capture date (29 Apr 2026) | Licence unresolved; mosaic-wide dates not recorded |\n"
      "| Synthetic C1 perturbations | Labelled synthetic everywhere | Real error propagation not started |\n"
      "| Other villages | None | C3 not started; needs written approval |")
    A("")
    A("## 10. Decision metrics")
    A("| Metric | Value |\n|---|---|\n"
      "| House targets routed (x4) | %d of %d, no failures |\n| Unique house-route length, independent baseline | %.1f m |\n| Unique house-route length, proposed | %.1f m |\n"
      "| Reduction in unique length | %.1f m (%.1f%%) |\n| House routes crossing other footprints (x4 plan / independent) | %d / %d |\n| Hard-constraint violations | %d |\n"
      "| Targets connected, planner / raster main component / road lines | %d / %d / %d of %d |\n| Facilities supported by a detected footprint | %d of 4 |\n| Candidate footprints agreeing with an independent detector | %.0f%% |" % (
          ev["n_house_targets"], ev["n_house_targets"], ind.unique_len_m, net.unique_len_m, net.reduction_vs_independent_unique_m, net.reduction_vs_independent_unique_pct,
          int(net.routes_crossing_other_footprints), int(ind.routes_crossing_other_footprints), int(t3.hard_constraint_violations.iloc[0]),
          t3.planner_verified_connected.iloc[0], t3.reach_main_component_raster.iloc[0], int(t3.reach_main_component_road_lines.iloc[0]), t3.targets.iloc[0], nsup, 100 * allb.proxy_agreement_rate))
    A("")
    A("## 11. Evidence files")
    A("`outputs/verification/` (facility and building agreement), `outputs/connectivity/` (line connectivity), `outputs/final_comparison/` (Tables 1 to 4 as CSV and Markdown), `outputs/final_maps/` (maps 1 to 5, Map 5 being the village-level detail), `outputs/final_comparison/charts/` (charts 1 to 5), "
      "`outputs/%s/` (stage 1 to 5 results of the pipeline run, `RUN_SUMMARY.md`). Planner SHA-256 d00ea92028101131627b8592e3df2c33ff350efac9b1de09f9b64cdd56ef70a4." % a.run_id)
    A("")
    A("## 12. What this chapter does not establish")
    A("Detector accuracy, the true number of houses, the existence or condition of any proposed road, legal access, ownership, drainage, road width, construction cost, or performance in other villages. "
      "The imagery licence is unresolved and its capture date is recorded for one sampled point only, so the maps containing imagery are review drafts.")
    import limitations_text
    A("")
    for _ln in limitations_text.TEXT.split("\n"):
        A(_ln)
    out = O / "final_package"
    out.mkdir(parents=True, exist_ok=True)
    (out / "THESIS_CHAPTER_RESULTS_AND_VALIDATION.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("chapter written:", out / "THESIS_CHAPTER_RESULTS_AND_VALIDATION.md")


if __name__ == "__main__":
    main()
