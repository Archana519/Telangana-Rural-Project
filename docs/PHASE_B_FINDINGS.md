# PHASE_B_FINDINGS (proposed document, 2026-10-24)

Save as a NEW file in `D:\Telangana_Rural_Project\`. It does not change the first-village report or `DECISIONS.md`.

Evidence labels: **Verified** = from audit output or code I read. **Unverified** = inferred. **Open** = not resolved.
Basis: audit run `audit_phaseB\pb_20261024_201335` (console output seen; the CSV and JSON files in that folder not yet seen), the run summaries in the review pack, and the scripts named below.

## 1. Results

| Item | Finding | Label |
|---|---|---|
| B1 C12, slope | The target cell has slope 10.349 deg against the 10 deg hard limit. 10 of the 20 valid cells in its 5x5 window are also over the limit, so it sits on a steeper patch, not an isolated marginal cell. All 13 routes of the reference run stay at or below 6.49 deg along the sampled points. | Verified |
| B1 C12, no-limit run | `run6_slope_soft` had no slope raster and no slope limit, so it is an unconstrained-slope run, not a soft-slope run. Its C12 route is 227.9 m; the maximum slope sampled along it is 10.35 deg and about 14.5 m of it is above 10 deg (5 m sampling, so approximate). | Verified |
| B1 knock-on | In that run C11 attaches to C12's route (212.8 m becomes 137.7 m) and the network-aware total rises 1506.1 m to 1658.9 m (+227.9 -75.1 = +152.8 m). The other 12 targets are identical to the reference run. That run used an earlier planner version, so it is a sensitivity run only. | Verified |
| B1 DEM caveat | Slope is computed from a 30 m elevation model and resampled to 10 m. Its error was not measured here, so the exact 10.35 value should not be treated as precise. | Verified (code); error Open |
| B2 mask meaning | The "prohibited" mask is 1 everywhere except WorldCover classes 10-60 with a valid slope. It is not a legal or protected-land layer. | Verified (`create_damarakunta_cost_surface.py`) |
| B2 mask causes | 109,958 of 293,328 cells (37.5 %) are blocked: 108,682 outside the village boundary, 224 water, 178 WorldCover nodata inside the boundary, 874 land cells with invalid slope, 0 unexplained. | Verified |
| B2 C13 | The target point lies 0.6 m inside the boundary polygon, but its 10 m cell has its centre outside, so the cell was masked as outside the boundary. The member polygon (cand_id 29, 86.8 m2) is only 55.3 % inside the boundary. The failure is a boundary-edge effect of the 10 m clip, not an obstacle found on the ground. | Verified |
| B2 C12 | Excluded by the slope limit only; the prohibited mask is 0 there. Nearest passable cell centre: 6.0 m. C13: 17.3 m. | Verified |
| B3 165 vs 163 | Reproduced: 165 inside_village polygons, all in kept quality classes, minus 2 with area under 10 m2 (cand_id 189 at 7.2 m2 and cand_id 202 at 8.28 m2, both REVIEW, est_roofs 1) = 163. | Verified |
| B4 dropped road cells | The count reproduces the planner: 8,061 road cells, 6,430 passable, 1,631 dropped. By first matching cause: 1,532 (93.9 %) outside the village boundary, 67 slope above limit, 32 mask inside the boundary. So only 99 (6.1 %) are dropped for terrain reasons inside the village. | Verified |
| B4 network shape | The passable road cells form 13 connected pieces; the largest holds 6,078 of 6,430 cells (94.5 %). The dropped cells form 22 pieces, the largest 689 cells. | Verified |
| B4 targets | The 2 of 15 targets whose nearest road cell is dropped are exactly the two failed ones. C12: nearest road cell 144.7 m, nearest passable one 191.0 m (+46.3 m). C13: 157.8 m and 223.2 m (+65.4 m). The other 13 targets are unaffected. All 15 targets lie inside the grid and the boundary polygon; C13 is 0.6 m and C12 15.4 m from the boundary. | Verified |
| B5 C1 metrics | See section 2. | Verified (code read) |
| B6 report arithmetic | Checked against `target_table.csv` and `summary.json` of `run7_regress`: 13 served targets; weighted benefit 23.25 (13 for the four facilities + 10.25 for the clusters; 25.25 with C12 and C13); 14 of 16 cluster polygons served; route lengths sum to 1506.2 m (1506.1 m unique, rounding); route cost 9438.7. | Verified |

## 2. How the C1 numbers are defined (from `run_planning_experiments.py`)
- **Coverage** is the share of a fixed set of 16 points within 50 m of the roads plus the planned routes. The points are representative points of the unperturbed baseline gap-cluster polygons, so values move in steps of 1/16 (0.688 = 11/16).
- **Overlap** is the share of the perturbed plan's route length that lies within 15 m of the baseline routes. It does not penalise routes the perturbed plan lost. The reverse overlap is computed per run but left out of the summary table.
- **Served clusters** is not comparable between conditions: omitting buildings can split a cluster, so the number of clusters changes (11 in the baseline, 12 on average with 10 % random omission).
- The evaluation set is the model's own baseline polygons. C1 therefore measures how the plan responds to synthetic perturbations of model-derived polygons. It does not measure agreement with real buildings.
- Most conditions are single runs (random omission has 5 seeds), so no spread is available for them.
- The access-gain table shows 12 of 16 gap-cluster polygons within 50 m after planning, while the C1 baseline coverage is 11 of 16. I have not read `summarise_access_gain.py`. If it measures from the polygon and C1 from a point, that would explain the difference. Open.

## 3. Wording corrections for the first-village report (the report itself is not edited)
1. Section 4, C13: replace "prohibited mask > 0, reason unknown" with "the target cell is masked as outside the village boundary; the polygon straddles the boundary (55 % inside); the mask is a non-land / outside-boundary exclusion, not a legal layer".
2. Wherever `run6_slope_soft` appears, call it "no-slope-limit run".
3. Section 7: state that 163 = 165 inside_village minus 2 polygons under 10 m2.
4. Planner data check: state that 94 % of the dropped road cells lie outside the village boundary.
5. Section 3: the C2 reduction is 10.5 m in `summary.json` and 10.4 m in the experiment CSV; use one source consistently.
6. `shared_len_m` prints as `-0`; it is zero.

## 4. Proposed DECISIONS rows (not applied)

| # | Date | Decision | Reason | Evidence | Alternative considered | Why rejected |
|---|---|---|---|---|---|---|
| 17 | 2026-10-24 | C13 stays in the evaluation as a failed target and is described as a boundary-edge exclusion | Its cell is masked as outside the village boundary at 10 m; the polygon is 55 % inside | `audit_phaseB\pb_20261024_201335` (B2); `create_damarakunta_cost_surface.py`; `align_damarakunta_terrain.py` | Drop it from the target list | Removing failures would flatter the result |
| 18 | 2026-10-24 | C12 stays failed under the 10 deg hard limit; `run6_slope_soft` is reported only as a no-slope-limit sensitivity run | C12's cell is 10.349 deg and half its neighbourhood exceeds the limit; the slope comes from a 30 m model | audit B1; `run6_slope_soft\summary.json` (no slope raster, no limit) | Relax the limit for the reference run | Changes a planner parameter |
| 19 | 2026-10-24 | The access polygon set is inside_village, kept quality classes, area at least 10 m2 (163 polygons) | Reproduces the access count exactly | audit B3; `assess_building_access_v2.py` defaults | Use all 165 | Two polygons under 10 m2 are excluded by the access script |
| 20 | 2026-10-24 | Road cells outside the village boundary are not usable attachment points; 94 % of dropped road cells are of this kind | The terrain rasters are clipped to the boundary | audit B4 | Treat dropped road cells as impassable roads | They are outside the planning domain, not impassable roads |

## 5. Still open
- The 11 versus 12 within-50 m difference (needs `summarise_access_gain.py`).
- The `cells_covered` fields for small polygons in `audit_phaseB_damarakunta.py` use a cell-centre rule and show 0 for small polygons; ignore them.
- Possible sensitivity runs that need your approval because they change planner behaviour: allowing a target to snap to a passable cell within the 30 m snap distance, and a slope limit other than 10 deg. Neither would replace the reference run.
