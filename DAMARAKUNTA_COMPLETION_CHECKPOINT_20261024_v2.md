# DAMARAKUNTA_COMPLETION_CHECKPOINT_20261024_v2 (proposed document; supersedes the first checkpoint file, which is unchanged)

Save as a NEW file in `D:\Telangana_Rural_Project\`. Scope: Damarakunta only. No other village has been processed or prepared since the one-village rule; earlier read-only discovery/readiness runs and review-pack drafts for other villages are on hold and unused.
Labels: **Met** (evidence in hand), **Partial**, **Open** (needs your decision or work), **Unverified**.

## Gate criteria (from your prompt)
| # | Criterion | Status | Evidence / what is missing |
|---|---|---|---|
| 1 | Inputs inspected, limitations documented | **Met, pending your review** | `DAMARAKUNTA_STAGE_A_INPUT_VALIDATION.md`; `stageA_1`; `stageA2_provenance_alignment\pa1` (exact transform equality inside the 0.6 m, 10 m and 30 m families; 10 m to 30 m nests exactly; 0.6 m to 10 m does not nest, tied by coordinates only). Not checked: absolute georeferencing of the Esri tiles against TGRAC vectors (edge-tile risk, below) |
| 2 | Imagery permissions addressed | **Open** | Questions drafted in `DAMARAKUNTA_STAGE_B_C_PROPOSALS.md` Part B. Needs your choice B1/B2/B3 |
| 3 | Facility selection understood, reproducible, documented | **Partial** | 4 targets reproduced from the script and files (2 school compounds, 1 sub-centre, 1 anganwadi; hand-curated). Verified: the school polygons equal TGRAC `Schools/MapServer/4` ("School Building Compound Wall") geometries exactly (same School_Code, symmetric difference 0.0 m2); the "verified" wording in the script is unexplained. Sub-centre location **Unverified** (NIN 8734223673, two TGRAC positions 235.7 m apart; you judged the image inconclusive). Anganwadi location Unverified (about 500 m from the colocated school). School targets are interior points of compounds |
| 4 | Segmentation ran or blocker recorded | **Partial** | Ran on 23 Oct 2026: `predictions\tiled_v1\run_log_full.json` (CPU, 459 tiles of 560 px, stride 420, margin 70, 3,640.5 s = 60.7 min measured; checkpoint `D:\new_MPS\remoteSensingWebApp\checkpoints\best_model.pth`, outside the project, no hash logged; memory not recorded). Predicted class shares: 1 38.5 %, 5 38.8 %, 7 19.2 %, 6 2.35 %, 4 0.77 %, building (2) 0.33 %, road (3) 0.05 %. The log states "raw argmax over classes 1-7; unvalidated". IDs 1-7 follow LoveDA's order (my inference; training data not seen). No accuracy claim possible without reference labels |
| 5 | Road extraction and network evaluated | **Partial** | The pipeline plans on the TGRAC road layer; the model's road class covers 0.05 % of pixels, so no extracted road network exists to compare. Graph audit of the reference run (`connectivity_audit_v1\ca_ref`): 7 road components, main component 86,101.5 m = 92.09 % of 93,496.8 m; 29-30 dangling ends; 13/13 routes reach the main component (2 ambiguous). Road layer completeness not established (it may omit village lanes) |
| 6 | Building/cluster connectivity | **Met at the resolution supported** | `ca_ref`: baseline 103/163 within 50 m by polygon distance (92/163 by representative point); only 10/163 touch the main component within 1 m (153 PROXIMITY_ONLY). After planning 118/163: **9 by construction (route starts in the polygon) + 6 spillover**. Proximity, not legal or physical access; polygons are model-derived and unverified |
| 7 | Route generation and selection checked | **Met for the reference run** | `run7_regress`/`fv_repro1`: 13 of 15 routed; C12 and C13 failed with traced causes (Phase B); `run6_slope_soft` is a no-slope-limit sensitivity run |
| 8 | Evaluation and baseline comparison | **Partial** | C1/C2 experiments exist (most conditions single runs); independent baseline comparison exists. No segmentation-quality metric (no ground truth). Runtime: 60.7 min inference measured; planner runtime not collected here; memory not recorded |
| 9 | Paths, parameters, failures, reproducibility recorded | **Partial** | Planner chain reproduced 13/13 (`fv_20261024_193950`); `ca_ref` shows `run7_regress` and `fv_repro1` give identical gain splits (103 / 45 / 9 / 6) and route counts. Missing: checkpoint hash and training provenance, memory use, environment capture for the inference |
| 10 | Results and limitations reviewed | **Partial** | First-village report plus `PHASE_B_FINDINGS.md` corrections (six wording changes not yet applied to the report) |
| 11 | Pipeline tested without damaging prior outputs | **Met for the planner chain** | new output folders only; inference not re-run |
| 12 | Final completion report | **Not started** | to be written after items 2-10 |

## Findings added today (all Verified unless stated)
- Priority weights: `priority_group` has no effect in `plan_network_v2.py`; weights come from keywords in type/name (health/sub-centre 4.0, school 3.0, anganwadi 3.0, cluster 1.0 + 0.25 per extra building). They are described in the code as ordinal design parameters.
- Six evaluation windows are 200 x 200 m each (1.3 % of the village), chosen by role from model predictions; 67 model buildings inside them. Purposive, not a random sample.
- The mosaic has a blank corner (3.32 % of its bbox, 0.967 km2, outside the polygon): the missing 12th tile.
- Esri edge tiles were requested at 3000 x 3000 px with non-square ground extent; whether the server adjusted the extent is **Unverified**. Check: overlay the TGRAC roads on the edge tiles.
- School layers in the TGRAC service: polygons `Schools/MapServer/4` (has School_Code); points 0, 1, 3. Resolves "school layer not identified" for Damarakunta's source.

## Corrections and additions since the first checkpoint file
- Earlier I inferred "at most 1 spillover polygon"; the audit shows 6 spillover and 9 by construction (cluster members other than the start polygon count as spillover). The earlier statement was wrong and is withdrawn.
- The 11 versus 12 difference (gap-cluster polygons within 50 m after planning) is a definition difference: representative point gives 11, polygon distance gives 12.
- The audit tool flags one documentation item for `ca_ref` (4 undocumented columns for `fv_repro1`); no data check failed (FAIL = 0).
- Earlier connectivity audits (`ca1`-`ca3`, `ca_angle60`) ran on `run5` and `run6_slope_soft`; `ca_ref` is the audit of the reference run and its reproduction.

## Pending decisions (yours)
1. Licence route B1 / B2 / B3.
2. Labelling workflow (Part C): approve or change; optional seeded random windows (new layer).
3. Whether to build the edge-tile overlay check.
4. Whether a roads-on-mosaic overlay for the Esri edge tiles is wanted before the final report.

## Proposed DECISIONS rows (not applied; rows 21-24 in the earlier file concern other villages and are on hold)
| # | Decision | Reason | Evidence |
|---|---|---|---|
| 25 | Sub-centre target kept at the `tgrac_health.gpkg` position, recorded Unverified; the sub-centre-layer position (235.7 m away) is not substituted | Both positions share NIN 8734223673; image review inconclusive | `damarakunta_health_record_comparison.csv`; `health_two_coordinates_comparison.png` |
| 26 | School compounds documented as TGRAC `Schools/MapServer/4` geometries, accessed about 5 Oct 2026 | Geometry equal to the layer (0.0 m2 difference) | provenance query of 2026-10-24 |
| 27 | `priority_group` documented as inert; hierarchy comes from keyword weights, which are design parameters | Code read | `plan_network_v2.py` `priority_weight` |
| 28 | Segmentation accuracy reported as "not computed" until reference labels exist | `reference_buildings` has 0 features; label folder empty | Stage A report |

| 29 | Access results are reported with their definition: 103/163 within 50 m by polygon distance (92/163 by representative point) at baseline, 118/163 after planning, of which 9 by construction and 6 spillover; none is graph connectivity or legal access | Audit `ca_ref` | `connectivity_audit_v1\ca_ref` |
| 30 | The model's road class is not used; the road network is the TGRAC layer (road class covers 0.05 % of pixels) | run log class shares | `predictions\tiled_v1\run_log_full.json` |
