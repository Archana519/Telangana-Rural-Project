# Results, validation and limitations: Damarakunta case study

*Draft chapter generated from the pipeline outputs of run `run_20261102_141136`. Every number comes from a file listed in Section 11. Planning results are model outputs on a 10 m grid: routes are unverified planning alternatives, costs are ordinal planning units (not rupees), and no field validation, legal access, road width or construction cost is claimed. The Damarakunta completion gate has not been approved and the five-village transfer study (C3) has not started.*

## 1. Purpose and scope
This chapter reports what was verified automatically after the Stage B planner passed its acceptance checks: (i) how far the detected building footprints and priority facilities agree with independent layers, (ii) how the road-connectivity exception for house C0002 arises and how it is evaluated, (iii) how the proposed two-stage planner compares with the baselines, and (iv) how the planned network responds to synthetic omissions and additions of building targets (C1). It also records, limitation by limitation, what is solved by automation, what is only reported, and what stays open.

## 2. Pipeline in five stages
| Stage | What it does | Status |
|---|---|---|
| 1 Detect | Building candidates (278; 165 inside the boundary) and four priority facilities from TGRAC layers. The detection output is verified by hash and reused; segmentation is not re-run because the model-weight location is not recorded. | Reused input |
| 2 Model terrain | Boundary, WorldCover, slope from a 30 m DEM and TGRAC roads on a 10 m grid (432 x 679) give an ordinal cost surface; water, no-data and cells steeper than 25 degrees are blocked. | Verified input |
| 3 Plan | Stage A generates up to three least-cost alternatives per target (319 for 163 houses); Stage B selects greedily by weight over marginal cost, so a route may end on another route (shared-edge accounting). | Run and reproduced |
| 4 Stress-test | C1: omit or add targets (synthetic); C2: ablation of alternatives per target and leaf-reroute passes. | Run |
| 5 Validate | Acceptance validator, connectivity audit, line-topology connectivity, detection agreement checks, per-route explanations. | Run |

The TGRAC layers hold four priority facilities: two schools, a health sub-centre and an anganwadi. The anganwadi was excluded from the planning layers, CSVs and maps at the project owner's request (`inputs/EXCLUSIONS.md`), Two Gram Panchayat headquarters points from TGRAC (`inputs/ADMIN_UTILITIES.md`) were added as administrative utilities, so the final layer holds five facilities. MeeSeva and Directorate of ESD (Aadhaar/service) centres have no located coordinate in any available source and are not included. No government-building layer exists, so no such class is detected or prioritised.

## 3. Detection and facility verification
There is no building ground truth: the project has no reference buildings and no manual labels. The checks below therefore measure **agreement with independent layers**, not accuracy. Thresholds were fixed beforehand: a footprint within 20 m of a facility point supports it, and an independent Google Open Buildings v3 polygon within 30 m corroborates it.

| facility_id                  | name                                                            |     lat |     lon |   dist_to_nearest_footprint_m |   nearest_open_buildings_m | inside_school_compound   | verdict      |
|:-----------------------------|:----------------------------------------------------------------|--------:|--------:|------------------------------:|---------------------------:|:-------------------------|:-------------|
| 36181600902                  | Mpps Damarakunta                                                | 17.7073 | 78.7505 |                           8.5 |                        0   | MPPS DAMARAKUNTA         | CORROBORATED |
| 36181600903                  | Zphs Damarakunta                                                | 17.7076 | 78.7505 |                           3.1 |                        1.4 | ZPHS DAMARAKUNTA         | CORROBORATED |
| HEALTH_8734223673            | Sub Centre, Damarakunta                                         | 17.7082 | 78.7538 |                           1.8 |                        8.7 |                          | CORROBORATED |
| GP_DAMARAKUNTA               | Damarakunta Gram Panchayat HQ                                   | 17.7064 | 78.753  |                           0.7 |                        3.4 |                          | CORROBORATED |
| GP_KASHIREDDYPALLY           | Kashireddypally Gram Panchayat HQ (Damarakunta revenue village) | 17.6991 | 78.7799 |                           0   |                        2.5 |                          | CORROBORATED |
| HEALTH_ALT_health_layer      | Sub Centre, Damarakunta                                         | 17.7082 | 78.7538 |                           1.8 |                        8.7 |                          | CORROBORATED |
| HEALTH_ALT_sub_centres_layer | SubCentre, Damarakunta                                          | 17.7072 | 78.7519 |                           0   |                        0.5 |                          | CORROBORATED |

**Finding.** 5 of the 5 facilities in the final layer are supported by a detected footprint and 5 are corroborated by an independent Open Buildings polygon; the two Gram Panchayat points lie on unresolved-merge footprints, so the Panchayat building itself is not identified. The anganwadi (Damarakunt-I) was excluded because its TGRAC coordinate lies 371 m from the nearest detected footprint and 126 m from the nearest Open Buildings polygon (record kept in `excluded_facilities.csv`); this does not show the anganwadi is absent from the village, only that its position is unsupported. Until a verified location exists the plan does not serve the anganwadi. The sub-centre has two TGRAC records 236 m apart; the position in the priority layer is the health-layer record, and both records are near a footprint, so proximity alone cannot say which is right.

Building candidates inside the boundary against Google Open Buildings v3 (a different detector on other imagery; neither is truth):

| group            |   candidates |   proxy_TP |   proxy_FP |   proxy_agreement_rate |
|:-----------------|-------------:|-----------:|-----------:|-----------------------:|
| ALL              |          165 |        118 |         47 |                  0.715 |
| PLAUSIBLE        |           71 |         51 |         20 |                  0.718 |
| REVIEW           |           32 |         14 |         18 |                  0.438 |
| UNRESOLVED_MERGE |           62 |         53 |          9 |                  0.855 |

**Finding.** 118 of 165 candidates (72%) agree with an independent polygon; the REVIEW class agrees least (44%), which supports treating it as uncertain. The reverse direction is weak: Open Buildings lists 1537 polygons inside the boundary (1298 with confidence of at least 0.70), of which 1186 have no candidate. The candidate set is therefore much smaller than what another detector sees. Part of the gap is expected (sheds, farm structures and duplicates are included in Open Buildings), but the cause was not established, so the 163 routing targets must not be read as the number of houses in the village.

### Visual audit protocol for the priority facilities
Agreement checks cannot replace looking at the imagery. `outputs/visual_audit/` holds a Visual Grounding Table, a Google Earth KML and plain and annotated 200 m imagery crops for each facility. The measured columns (model latitude/longitude, offset to the nearest detected footprint and Open Buildings polygon, roof area, distance to the nearest TGRAC road, compound membership) are filled from project files. The observation columns (feature at the pin, matching-feature offset, roof size, playground or open ground, road access, corrected coordinate, imagery date, decision) are **empty on purpose**: they need a person with Google Earth Pro, and the decision rule is fixed in `protocol.md` (confirm within 20 m, relocate within 200 m, otherwise reject). No facility is visually confirmed by this project yet. A government-building row exists but cannot be audited, because no such layer is in the data.

| facility_id        | name                                                            |   model_lat |   model_lon |   nearest_detected_footprint_m |   nearest_open_buildings_m |   distance_to_nearest_TGRAC_road_m | agreement_verdict   |
|:-------------------|:----------------------------------------------------------------|------------:|------------:|-------------------------------:|---------------------------:|-----------------------------------:|:--------------------|
| 36181600902        | Mpps Damarakunta                                                |     17.7073 |     78.7505 |                            8.5 |                        0   |                               11.1 | CORROBORATED        |
| 36181600903        | Zphs Damarakunta                                                |     17.7076 |     78.7505 |                            3.1 |                        1.4 |                               43.1 | CORROBORATED        |
| HEALTH_8734223673  | Sub Centre, Damarakunta                                         |     17.7082 |     78.7538 |                            1.8 |                        8.7 |                               62.2 | CORROBORATED        |
| GP_DAMARAKUNTA     | Damarakunta Gram Panchayat HQ                                   |     17.7064 |     78.753  |                            0.7 |                        3.4 |                               51.7 | CORROBORATED        |
| GP_KASHIREDDYPALLY | Kashireddypally Gram Panchayat HQ (Damarakunta revenue village) |     17.6991 |     78.7799 |                            0   |                        2.5 |                               43.7 | CORROBORATED        |
| (none)             | Government building                                             |             |             |                                |                            |                                    | NOT AUDITABLE       |

The excluded anganwadi is not part of this audit; its record and the reason are in `inputs/EXCLUSIONS.md`.

## 4. Road connectivity and the C0002 exception
Three connectivity measures are reported, because they answer different questions: the planner's check that each route ends on the declared network (168 of 168), the raster test that the route's terminal road cell belongs to the main road component inside the village polygon (167 of 168), and the road-line test on the TGRAC lines, which also covers the 44.7% of road length outside the polygon (168 of 168).

The single exception is house C0002 (candidate 2, class REVIEW, 95.6 m from the nearest road line). Its route ends on a 5-cell road fragment that the raster treats as a separate component. On the road lines the same fragment belongs to the main network: the lines run 630.4 m to the main component, of which 385.3 m lie outside the village polygon (accuracy about 5 m). The polygon clips the grid, so a road that leaves and re-enters the village is cut into pieces; 98% of the blocked road cells found in the diagnostics lie outside the polygon.

**Decision.** The planner was not changed. It is hash-pinned and verified, and any snapping rule inside the clipped grid would either bridge a gap that is absent from the line data or move the boundary without an independent boundary source. Instead, the automated rule is applied in the evaluation: every route end is snapped to the nearest TGRAC line within the planner's 15 m tolerance (168 of 168 snap) and connectivity is judged on line topology (script `connectivity_resolution.py`). Bridge proposals generated: 0. This resolves the reporting inconsistency. It does not show that the roads exist, are passable or are legally accessible, and the nearest-cell distance (155.24 m) and the audit distance (151.55 m) still differ between two diagnostics.

The connectivity audit (version 2) still lists C0002 as a failure under its stricter raster rule, and the acceptance validator lists it as information. Both are reported as they are.

## 5. Baseline versus proposed network
The x4 and x1 building-penalty configurations are separate blocks. Each uses baselines planned under its own penalty.

| configuration   |   houses | method                                                    |   total_len_m |   unique_len_m |   duplicated_len_m |   reduction_vs_independent_unique_m |   reduction_vs_independent_unique_pct |   routes_crossing_other_footprints |   len_in_other_footprints_m |
|:----------------|---------:|:----------------------------------------------------------|--------------:|---------------:|-------------------:|------------------------------------:|--------------------------------------:|-----------------------------------:|----------------------------:|
| x4 (primary)    |      163 | Straight line (no terrain, 2 targets infeasible)          |        8092.3 |                |                    |                                     |                                       |                                 60 |                      1453.2 |
| x4 (primary)    |      163 | Independent least-cost routes to the roads                |       10045.4 |         6753.1 |             3292.3 |                                 0   |                                   0   |                                 46 |                       328.3 |
| x4 (primary)    |      163 | Length-only control (shortest distance, same constraints) |        9166.3 |         6979.8 |             2186.5 |                              -226.7 |                                  -3.4 |                                 64 |                      1615.8 |
| x4 (primary)    |      163 | Roads-only shared reference (houses attach to roads only) |        5229.3 |         5229.3 |                0   |                              1523.8 |                                  22.6 |                                 29 |                       216.1 |
| x4 (primary)    |      163 | Two-stage network-aware plan (proposed)                   |        5069   |         5069   |                0   |                              1684.1 |                                  24.9 |                                 28 |                       209.1 |
| x4 (primary)    |      163 | Facilities (5), network-aware                             |         249.3 |          249.3 |                    |                                     |                                       |                                    |                             |
| x4 (primary)    |      163 | Houses + facilities, network-aware (combined unique)      |        5318.4 |         5318.3 |                    |                              1626.3 |                                  23.4 |                                    |                             |
| x1 (P3 control) |      163 | Straight line (no terrain, 2 targets infeasible)          |        8092.3 |                |                    |                                     |                                       |                                 60 |                      1453.2 |
| x1 (P3 control) |      163 | Independent least-cost routes to the roads                |        9595.9 |         6921.3 |             2674.6 |                                 0   |                                   0   |                                 63 |                      1423.1 |
| x1 (P3 control) |      163 | Length-only control (shortest distance, same constraints) |        9166.3 |         6979.8 |             2186.5 |                               -58.4 |                                  -0.8 |                                 64 |                      1615.8 |
| x1 (P3 control) |      163 | Roads-only shared reference (houses attach to roads only) |        4816.7 |         4816.7 |                0   |                              2104.6 |                                  30.4 |                                 60 |                       711.4 |
| x1 (P3 control) |      163 | Two-stage network-aware plan (proposed)                   |        4705.5 |         4705.4 |                0   |                              2215.9 |                                  32   |                                 56 |                       660.1 |
| x1 (P3 control) |      163 | Facilities (5), network-aware                             |         235.2 |          235.2 |                    |                                     |                                       |                                    |                             |
| x1 (P3 control) |      163 | Houses + facilities, network-aware (combined unique)      |        4940.7 |         4940.6 |                    |                              2147.9 |                                  30.3 |                                    |                             |

**Finding (x4, primary).** Independent least-cost routes to the roads total 10045 m, but 3292 m of that duplicates grid edges used by several houses, leaving 6753 m of unique road. The two-stage plan needs 5069 m, a reduction of 1684 m (24.9%). The roads-only shared reference already gives 22.6%, so the further gain from letting houses attach to other routes is 2.3 percentage points (about 160 m). The plan is not globally optimal; it is a greedy heuristic. In the x1 control the same comparison gives 32.0% (4705 m against 6921 m). The two configurations answer different questions (x4 discourages entering building footprints; x1 does not) and their lengths must not be compared as if they were one experiment.

The length-only control is longer than the independent least-cost routes in unique length and crosses more building footprints, so the cost surface is doing useful work. The straight-line baseline ignores terrain and crosses 62 footprints; it is shown only as a distance reference.

### C2 ablation (alternatives per target K and leaf-reroute passes)

| run                       |   alternatives_per_target_K |   leaf_reroute_passes |   unique_len_m |   total_len_m |   saving_vs_independent_pct |
|:--------------------------|----------------------------:|----------------------:|---------------:|--------------:|----------------------------:|
| S2_fac_C0_s25_final_K1_P0 |                           1 |                     0 |        5079.27 |       5079.32 |                      24.786 |
| S2_fac_C0_s25_final_K1_P2 |                           1 |                     2 |        5069    |       5069.04 |                      24.938 |
| S2_fac_C0_s25_final_K3_P0 |                           3 |                     0 |        5079.27 |       5079.32 |                      24.786 |
| S2_fac_C0_s25_final_K3_P2 |                           3 |                     2 |        5069    |       5069.04 |                      24.938 |
| S2_fac_C0_s25_final_x4    |                           3 |                     2 |        5069    |       5069.04 |                      24.938 |

Two leaf-reroute passes change the result by about 10 m (0.2%); more alternatives per target (K = 3 instead of 1) change nothing in this village, because the network-aware attachment step already finds the cheaper connections. No run switches shared-edge accounting off, so the ablation does not isolate it (the roads-only reference in Table 1 is the nearest comparison), and it does not show that the planner is optimal or that the result transfers to other villages.

### Obstacle avoidance: keeping routes out of building footprints
The request was to treat detected footprints as no-go zones or high-cost buffers so that no route crosses a building. Two things were tried, both without editing the verified planner or its runners (a new runner version, `dk_stageB_run_v1_4.py`, adds one option and is otherwise identical to v1.3).

1. **Hard block (failed).** Every 10 m cell touched by a footprint was added to the prohibited-area raster. All 163 house routes then failed (`TARGET_IN_HARD_CONSTRAINT_CELL_OR_OUTSIDE_GRID`), because each house point lies inside its own blocked cell and the planner does not start a route from a blocked cell. The attempt is kept in `archive/2026-10-30_phase3_experiments/`.
2. **High-cost buffer (works, with limits).** The planner is handed footprints buffered by 7.1 m (half a cell diagonal), so every cell touched by a building has its centre inside a penalised polygon, with a penalty multiplier of x20, x100 or x1000. All 163 houses are routed.

| scenario                                 |   houses_routed |   house_unique_len_m |   saving_vs_independent_pct |   house_routes_crossing_other_footprints |   crossing_len_m |   crossing_only_in_first_20m |   crossing_beyond_first_20m |   facility_unique_len_m |
|:-----------------------------------------|----------------:|---------------------:|----------------------------:|-----------------------------------------:|-----------------:|-----------------------------:|----------------------------:|------------------------:|
| x1, no penalty (P3 control)              |             163 |               4705.4 |                        32   |                                       56 |            660.1 |                           21 |                          35 |                   235.2 |
| x4, penalty on footprint cells (primary) |             163 |               5069   |                        24.9 |                                       28 |            209.1 |                           12 |                          16 |                   249.3 |
| buffer 7.1 m, penalty x20                |             163 |               6238.1 |                        18.5 |                                       19 |            147.9 |                           16 |                           3 |                   302.4 |
| buffer 7.1 m, penalty x100               |             163 |               6190.3 |                        18.9 |                                       19 |            144.8 |                           16 |                           3 |                   322.9 |
| buffer 7.1 m, penalty x1000              |             163 |               6190.3 |                        19.2 |                                       19 |            144.8 |                           16 |                           3 |                   322.9 |

**Finding.** The building-avoiding network (x100) is 6190 m long against 5069 m for the primary x4 network, a rise of 1121 m (22%); its saving against independent routes planned under the same penalty is 18.9% instead of 24.9%. House routes crossing another footprint fall from 28 to 19 and the crossing length from 209 to 145 m. Routes that cross a building away from their start fall from 16 to 3. At the assumed Rs 75 lakh/km the extra 1121 m is about Rs 84 lakh (illustrative). The effect saturates by x20: a larger penalty changes nothing.

**Why crossings do not reach zero.** 16 of the 19 remaining routes cross another footprint only within the first 20 m: the target point lies inside its own footprint, often among touching or merged buildings, and leaving the cluster means passing a neighbour. This is a property of the detections and the 10 m grid, not of the cost function, and no larger penalty removes it. Eliminating these crossings would need building-level geometry (entrances, gaps between buildings) or a finer grid, neither of which the project has.

**What was not done, and why.** (i) *Snapping to street networks and lanes:* the project has TGRAC road lines only; no lane or street layer exists inside the settlement, so route ends snap to TGRAC roads or to other routes and not to lanes. (ii) *Anganwadi:* excluded from the planning layers and maps at the project owner's request (`inputs/EXCLUSIONS.md`), not corrected; no verified location exists. (iii) *Other sensitive structures:* only detected building footprints are avoided; school compounds and parcels are not blocked, because the schools' own points lie inside their compounds. (iv) The primary x4 network remains the reference result of this chapter; the building-avoiding network is a scenario that shows the price of avoidance.

### Economic and material impact analysis (illustrative)
*This subsection is a parametric estimate. The project holds no road width, cross-section, soil or rate data, so the rate and the pavement section are assumptions listed in `inputs/economic_assumptions.json`. The rate of Rs 75 lakh per km is the figure supplied by the project owner as a PMGSY-based value; it was not checked against a PMGSY document or a State Schedule of Rates. It is not an engineering estimate, not a bill of quantities and not a claim about real construction cost. The routes are planning alternatives and are mostly short house lanes (about 31 m per house); a rate for habitation-connectivity roads may not apply to them, and the programme's eligibility for internal village lanes should be checked.*

**Which length is the baseline.** The independent routes sum to 10045 m, but 3292 m of that is grid edges used by several houses. A shared edge would be built once even without optimisation, so the fair baseline is the unique length of the independent routes, 6753 m. The proposed network is 5069 m. The saving is therefore **1684 m (24.9%)**, not the 4976 m (4.98 km) obtained by subtracting the shared network from the double-counted total. The 4.98 km figure is 3.0 times the real saving and should not be quoted as a saving.

| baseline_basis                                       |   baseline_len_m |   proposed_len_m |   length_saving_m |   length_saving_pct |   baseline_cost_central_Rs_lakh |   proposed_cost_central_Rs_lakh |   cost_saving_low_Rs_lakh |   cost_saving_central_Rs_lakh |   cost_saving_high_Rs_lakh |
|:-----------------------------------------------------|-----------------:|-----------------:|------------------:|--------------------:|--------------------------------:|--------------------------------:|--------------------------:|------------------------------:|---------------------------:|
| A (fair): independent routes, unique length          |           6753.1 |             5069 |            1684.1 |                24.9 |                           506.5 |                           380.2 |                     101   |                         126.3 |                      151.6 |
| B (double-counted): independent routes, total length |          10045.4 |             5069 |            4976.4 |                49.5 |                           753.4 |                           380.2 |                     298.6 |                         373.2 |                      447.9 |

At Rs 75 lakh/km the cost of the independent routes (basis A) is about Rs 506 lakh and of the proposed network about Rs 380 lakh, a saving of about **Rs 126 lakh (Rs 1.26 crore)**, within Rs 101 to 152 lakh for rates of Rs 60 to 90 lakh/km. The basis-B figure of Rs 373 lakh (Rs 3.73 crore) follows from the double-counted length and is shown only so the two can be compared; it overstates the saving.

Material conservation follows from the length saving and one assumed cross-section (3.75 m carriageway, 150 mm sub-base, 150 mm WBM, 20 mm bituminous surface, 5.0 m formation, 0.30 m average earthwork depth, 1.30 loose factor, 2.0 kg/m2 bitumen). Quantities for each length, and the saving on basis A, are:

| length                                |   length_m |   aggregate_loose_m3 |   gsb_subbase_loose_m3 |   earthwork_m3 |   bitumen_t |   cost_central_Rs_lakh |
|:--------------------------------------|-----------:|---------------------:|-----------------------:|---------------:|------------:|-----------------------:|
| Proposed shared network               |     5069   |               4200.9 |                 3706.7 |         7603.5 |        38   |                  380.2 |
| Independent routes, unique length (A) |     6753.1 |               5596.6 |                 4938.2 |        10129.7 |        50.6 |                  506.5 |
| Independent routes, total length (B)  |    10045.4 |               8325.1 |                 7345.7 |        15068.1 |        75.3 |                  753.4 |

| Material saved (basis A, 1684 m) | Quantity |
|---|---|
| Aggregate for WBM and surfacing, loose | 1396 m3 |
| Sub-base (GSB) material, loose | 1232 m3 |
| Earthwork | 2526 m3 |
| Bitumen | 12.6 t |

These quantities scale linearly with length because a single cross-section is assumed; they ignore drainage and cross-drainage works, side slopes, utilities, land, supervision and escalation. Replace the assumptions with State Schedule of Rates and a design section before any financial use.

## 6. Connectivity rates and constraint checks

| configuration   |   targets |   failed |   planner_verified_connected |   cell_graph_connected |   reach_main_component_raster |   hard_constraint_violations |   routes_crossing_without_shared_cell |   cycles |   max_chain_depth |   network_len_slope_gt25_m |   network_len_slope_gt10_m |   network_len_in_penalised_cells_m |   network_routes_crossing_other_footprints_houses |   network_routes_crossing_other_footprints_all |   reach_main_component_road_lines |
|:----------------|----------:|---------:|-----------------------------:|-----------------------:|------------------------------:|-----------------------------:|--------------------------------------:|---------:|------------------:|---------------------------:|---------------------------:|-----------------------------------:|--------------------------------------------------:|-----------------------------------------------:|----------------------------------:|
| x4 (primary)    |       168 |        0 |                          168 |                    168 |                           167 |                            0 |                                     0 |        0 |                 9 |                          0 |                       44.1 |                              614.9 |                                                28 |                                             31 |                               168 |
| x1 (P3 control) |       168 |        0 |                          168 |                    168 |                           167 |                            0 |                                     0 |        0 |                10 |                          0 |                       44.1 |                                0   |                                                56 |                                             60 |                                   |

No route violates a hard constraint (blocked cell, water, slope above 25 degrees), no cycle exists, and every target was routed. The x4 plan has fewer house routes crossing other footprints (28) than the x1 control (56) at the price of 364 m more unique length. Footprint classes are model-derived, so avoiding them is not evidence that real compounds are avoided.

## 7. Sensitivity to detection errors (C1)

| perturbation               |   runs |   house_targets_routed_mean |   failed_max |   unique_len_m_mean |   unique_len_m_min |   unique_len_m_max |   unique_len_per_routed_m_mean |   saving_vs_independent_pct_mean |   routes_crossing_other_footprints_mean |   share_common_targets_same_attach_class_mean |   mean_len_change_common_targets_m_mean |
|:---------------------------|-------:|----------------------------:|-------------:|--------------------:|-------------------:|-------------------:|-------------------------------:|---------------------------------:|----------------------------------------:|----------------------------------------------:|----------------------------------------:|
| baseline (no perturbation) |      1 |                       163   |            0 |             5069    |            5069    |            5069    |                          31.1  |                            24.94 |                                    28   |                                          1    |                                    0    |
| omit 10%                   |      5 |                       147   |            0 |             4684.43 |            4521.04 |            4821.89 |                          31.87 |                            25.09 |                                    24.2 |                                          0.97 |                                    0.49 |
| omit 20%                   |      5 |                       130   |            0 |             4211.49 |            3991.39 |            4410.93 |                          32.4  |                            24.95 |                                    20.4 |                                          0.96 |                                    1.39 |
| add 10%                    |      5 |                       177.4 |            0 |             5502.4  |            5393.23 |            5548.83 |                          31.02 |                            25.62 |                                    32   |                                          0.98 |                                   -0.55 |
| add 20%                    |      5 |                       190.6 |            0 |             5868.27 |            5822.32 |            5916.07 |                          30.79 |                            25.39 |                                    36.4 |                                          0.97 |                                   -1.2  |
| omit merged blobs          |      1 |                       101   |            0 |             3579.04 |            3579.04 |            3579.04 |                          35.44 |                            26.64 |                                    14   |                                          0.94 |                                    3.21 |
| omit smallest 10%          |      1 |                       146   |            0 |             4648.65 |            4648.65 |            4648.65 |                          31.84 |                            24.92 |                                    25   |                                          0.99 |                                    2.18 |
| omit smallest 25%          |      1 |                       122   |            0 |             3798.29 |            3798.29 |            3798.29 |                          31.13 |                            25.56 |                                    20   |                                          0.96 |                                    2    |

**Finding.** The experiments remove or add targets at random (five seeds per setting where available) and are synthetic: they are not measured detector errors. Every placed target is still routed in every run. The unique length per routed target stays between 30.8 and 35.4 m against 31.1 m for the baseline, so the network scales with the number of targets instead of breaking down. Total length is not a measure of efficiency here: omitting 20% of targets shortens the network by about 17% because those routes disappear. The sharing saving against independent routes stays between 24.9% and 26.6% in every setting. The risk of a missed building is therefore not a connectivity failure but a missing service: an omitted house gets no route, which this model cannot detect by itself. Omitting the merged blobs (the unresolved class) removes 62 targets and leaves 35.4 m per routed target, the highest value; why was not examined.

## 8. Why each route was chosen
For every selected route the planner log and the cost rasters were combined into one explanation (`stage3_plan/<run>/why_chosen/route_explanations.csv` and `.md`): the greedy step, the candidate used (Stage A alternative or a fresh path to the network), marginal and route cost, the land cover crossed, slope, building-penalty edges, the saving against the independent route and the object the route ends on. In the primary run 69 of 168 routes end on another route and 57 routes enter penalised building cells. No grid edge is shared by two routes (shared length 0.05 m): the saving arises because routes end on one another or on roads, not because they overlap.

## 9. Stage-wise status and limitation audit
| Stage | Status | Limitation | Automated rule or check | Outcome |
|---|---|---|---|---|
| 1 Detect | Reused input, verified by hash | Detections unverified; no ground truth; anganwadi excluded (unsupported coordinate); 163 targets are not a house count | Agreement checks with fixed thresholds; quality classes carried through planning; Visual Grounding Table prepared | **Bounded and reported, not overcome.** Real accuracy needs labelled buildings and the Google Earth audit |
| 2 Model terrain | Verified input | 30 m DEM interpolated to 10 m; roads 44.7%% outside the polygon; boundary not independently verified; imagery licence and date unresolved | Hash checks on all inputs; masks and counts reproduced by diagnostics; caveats printed on maps | **Bounded.** Resolution trade-off is a fundamental limit; licence unresolved |
| 3 Plan | Run, reproduced exactly (27 reference runs, 405 metrics); building-avoiding scenario added | Greedy heuristic, not optimal; ordinal costs; routes still cross buildings when a target starts among touching footprints | Fixed planner hash; fresh run folder per execution; comparison with the reference run; buffered-footprint scenario (runner v1.4) | **Overcome for reproducibility**; crossings bounded (counts in Table 6), not eliminated |
| 4 Stress-test | Run | Omissions and additions are synthetic; real detector error not measured | Seeded runs, per-routed-target metrics | **Bounded**; label-based error propagation not started |
| 5 Validate | Run | C0002 off the main raster component; two audits rate it differently | Line-topology connectivity with 15 m snapping; acceptance validator; connectivity audit v2; per-route explanations | **Reporting resolved**; physical road not verified; the planner was deliberately not changed |

## 9b. Limitations addressed by automation and what remains
| Limitation | Automated handling | Status |
|---|---|---|
| Detections may be wrong | Agreement checks against TGRAC tables, school compounds and Open Buildings; quality classes kept through planning | Reported; real accuracy needs labelled buildings |
| Facility coordinates unverified | Verdict per facility with fixed thresholds | Anganwadi excluded; verified location still needed |
| C0002 off the main raster component | Line-topology connectivity with snapping within 15 m | Reporting resolved; physical road not verified |
| Roads partly outside the polygon (44.7%% of length) | Included in line connectivity; planner domain unchanged | Documented; boundary not independently verified |
| 30 m DEM interpolated to 10 m | Stated on maps and in tables | Fundamental limit; no 10 m terrain accuracy claimed |
| Stale or mixed outputs | One command writes a new run folder, verifies input hashes and reproduces the reference exactly | Resolved for Stage B |
| Imagery licence and acquisition dates | Recorded in `inputs/METADATA.md`; maps carry a caution; one sampled capture date (29 Apr 2026) | Licence unresolved; mosaic-wide dates not recorded |
| Synthetic C1 perturbations | Labelled synthetic everywhere | Real error propagation not started |
| Other villages | None | C3 not started; needs written approval |

## 10. Decision metrics
| Metric | Value |
|---|---|
| House targets routed (x4) | 163 of 163, no failures |
| Unique house-route length, independent baseline | 6753.1 m |
| Unique house-route length, proposed | 5069.0 m |
| Reduction in unique length | 1684.1 m (24.9%) |
| House routes crossing other footprints (x4 plan / independent) | 28 / 46 |
| Hard-constraint violations | 0 |
| Targets connected, planner / raster main component / road lines | 168 / 167 / 168 of 168 |
| Facilities supported by a detected footprint | 5 of 4 |
| Candidate footprints agreeing with an independent detector | 72% |

## 11. Evidence files
`outputs/verification/` (facility and building agreement), `outputs/connectivity/` (line connectivity), `outputs/final_comparison/` (Tables 1 to 4 as CSV and Markdown), `outputs/final_maps/` (maps 1 to 5, Map 5 being the village-level detail), `outputs/final_comparison/charts/` (charts 1 to 5), `outputs/run_20261102_141136/` (stage 1 to 5 results of the pipeline run, `RUN_SUMMARY.md`). Planner SHA-256 d00ea92028101131627b8592e3df2c33ff350efac9b1de09f9b64cdd56ef70a4.

## 12. What this chapter does not establish
Detector accuracy, the true number of houses, the existence or condition of any proposed road, legal access, ownership, drainage, road width, construction cost, or performance in other villages. The imagery licence is unresolved and its capture date is recorded for one sampled point only, so the maps containing imagery are review drafts.

## 13. Methodological Limitations and Future Scope

### 13.1 Data sources, attribution and usage terms (status as of 2026-10-31)
The terms below are what the project has recorded. **None has been confirmed in writing**, and nothing here is legal advice or a statement that academic use, redistribution or publication of the data or of figures made from it is permitted.

| Dataset | Source and attribution to cite | Recorded terms and status | Action before publication |
|---|---|---|---|
| TGRAC village boundary, 43 road lines, facilities (school and health layers; Gram Panchayat headquarters points from layer 10; the anganwadi record is excluded), cadastral parcels, school compounds | TGRAC, Government of Telangana (name as used in the project); ArcGIS REST services at tgrac.telangana.gov.in (boundary: Administrative Information System MapServer layer 27; roads: Schools MapServer layer 20); downloaded 4 to 5 Oct 2026 | No licence or terms of use were found for these services as recorded. Currentness, completeness and authority are not verified. The saved boundary equals the stored query response (IoU 1.0), which shows consistency, not authority | Ask TGRAC in writing for terms for research use and for publishing derived maps; record the query date; cite as TGRAC, Government of Telangana |
| Esri World Imagery 0.6 m mosaic (11,296 x 7,171 px) | Esri World Imagery. The identify result saved with the project names Vantor (60 cm layer, dated 29 Apr 2026 at the one point sampled) and Earthstar Geographics as sources; attribution to Esri and its data providers is required by the terms summary the project recorded | The recorded Esri terms summary (21 Apr 2025) says basemap data may only be taken offline using Esri Content Packages, prohibits systematic harvesting of tiles by other methods, and requires attribution. The mosaic was built from 11 map-image export requests (4 Oct 2026), not Content Packages. Whether this use, model inference on the pixels, and publishing derived maps or figures is allowed is **not determined**. The enquiry draft has not been sent. Acquisition dates elsewhere in the mosaic are not recorded | Send the enquiry (or ask CBIT's GIS office whether an ArcGIS licence covers it). Until answered, do not redistribute the imagery or figures containing it; maps with imagery are review drafts |
| Building footprints (278 candidates) | Project extraction from the imagery above | Derived from imagery of unresolved terms, so the same question applies | Settle the imagery terms first |
| ESA WorldCover | ESA WorldCover (esa-worldcover.org); project notes record 2021 v200, not stored in the raster | CC BY 4.0 per project notes (not re-checked) | Confirm the product version and cite as the product requires |
| DEM (30 m, interpolated to 10 m) | Source not recorded; the file name n17_e078_1arc_v3 suggests an SRTM-type 1 arc-second product | Unknown | Identify the product and its terms |
| Google Open Buildings v3 (agreement checks only) | Sirko et al., 2021 | CC BY 4.0 / ODbL per Google's notes (not re-checked) | Cite |
| LoveDA (segmentation benchmark only) | Wang et al., NeurIPS 2021 Datasets and Benchmarks; doi 10.5281/zenodo.5706578 | CC BY 4.0 per its Zenodo record (checked 29 Oct 2026) | Cite |

### 13.2 Field validation status
Every route in this work is the output of a **GIS simulation**: an ordinal cost surface on a 10 m raster, built from ESA WorldCover land cover and slope computed from a DEM of about 30 m resolution that was interpolated to 10 m, with the TGRAC road lines as the existing network and automatically detected building footprints as targets. The routes are unverified planning alternatives (status `UNVERIFIED_PLANNING_ALTERNATIVE_NOT_A_ROAD`).
**No ground truthing has been done.** There has been no field visit, no surveyed road centreline, width, drainage or soil data, no check of ownership or right of way, and no confirmation of facility positions or of building use. Interpolating a 30 m DEM does not give 10 m terrain accuracy. **Ground-level physical validation is designated for future phases.**

Proposed validation steps (not scheduled):
1. Verify facility positions against a registry, Google Earth and then the field; re-include the excluded anganwadi once its location is verified; locate the MeeSeva and Directorate of ESD (Aadhaar/service) centres and add them through `inputs/admin_utilities_intake.csv`; confirm which building is the Gram Panchayat office.
2. Label a subset of buildings in the village to measure detector precision and recall, and to replace the synthetic C1 omissions with measured errors.
3. Walk a sample of the proposed routes and record obstructions, width, gradient, drainage and crossings.
4. Check parcel and right-of-way status with revenue records.
5. Compare the DEM slope with a surveyed or higher-resolution profile.
6. Replace the illustrative cost and material assumptions with State Schedule of Rates values and a design section.

### 13.3 Network generalisation (C3)
C3 asks whether the method carries over to other villages. **It has not started.** Only Damarakunta has been processed, and no transfer result exists or is claimed. Testing across multiple villages remains part of the extended future work and begins only after the project owner approves the Damarakunta completion gate in writing. Planned, not scheduled: five additional villages, the same pipeline and metrics, a per-village input check (imagery, boundary, roads, facilities, DEM) and the licence questions of Section 13.1 settled first. Results from Damarakunta, for example the unique-length saving of the shared network, must not be quoted as general.

### 13.4 Other methodological limits
- Two Gram Panchayat headquarters points are included as administrative utilities; the MeeSeva and ESD centres are not, because no coordinate source exists.
- Costs are ordinal planning units, not rupees; the economic and material figures are assumption-driven and illustrative.
- The planner is a greedy heuristic with no optimality guarantee; shared-edge credit counts identical grid edges only.
- Building detections are unverified and the 163 routing targets are not a house count; agreement with Open Buildings is not accuracy.
- The omit/add runs (C1) are synthetic probes, not measured segmentation error.
- Building avoidance is bounded, not complete: some house routes still cross a neighbouring footprint (counts in Table 6), mostly where a target starts among touching buildings.
- 44.7% of the raw TGRAC road length lies outside the village polygon. The road layer was clipped to the boundary with gpd.clip() (51,707 m of 93,497 m remain, in 50 parts) and only the clipped roads are routed; the boundary itself has not been independently validated.
- The route of the health sub-centre uses a manual local override: the building penalty is lifted within 20 m of the facility point because the facility sits at the edge of its own footprint. The override changes no other route and is not a verified finding about access.
- 961 slope cells and 178 land-cover cells inside the boundary have no value because of the coarse 30 m DEM and land-cover source. This is a spatial limitation: the gaps are not filled by interpolation, and the planner treats them as invalid cells.

