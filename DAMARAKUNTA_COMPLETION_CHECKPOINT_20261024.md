# DAMARAKUNTA_COMPLETION_CHECKPOINT_20261024 (proposed document)

Save as a NEW file in `D:\Telangana_Rural_Project\`. Scope: Damarakunta only. No other village has been processed or prepared since the one-village rule; earlier read-only discovery/readiness runs and review-pack drafts for other villages are on hold and unused.
Labels: **Met** (evidence in hand), **Partial**, **Open** (needs your decision or work), **Unverified**.

## Gate criteria (from your prompt)
| # | Criterion | Status | Evidence / what is missing |
|---|---|---|---|
| 1 | Inputs inspected, limitations documented | **Met, pending your review** | `DAMARAKUNTA_STAGE_A_INPUT_VALIDATION.md`; `stageA_1`; `stageA2_provenance_alignment\pa1` (exact transform equality inside the 0.6 m, 10 m and 30 m families; 10 m to 30 m nests exactly; 0.6 m to 10 m does not nest, tied by coordinates only). Not checked: absolute georeferencing of the Esri tiles against TGRAC vectors (edge-tile risk, below) |
| 2 | Imagery permissions addressed | **Open** | Questions drafted in `DAMARAKUNTA_STAGE_B_C_PROPOSALS.md` Part B. Needs your choice B1/B2/B3 |
| 3 | Facility selection understood, reproducible, documented | **Partial** | 4 targets reproduced from the script and files (2 school compounds, 1 sub-centre, 1 anganwadi; hand-curated). Verified: the school polygons equal TGRAC `Schools/MapServer/4` ("School Building Compound Wall") geometries exactly (same School_Code, symmetric difference 0.0 m2); the "verified" wording in the script is unexplained. Sub-centre location **Unverified** (NIN 8734223673, two TGRAC positions 235.7 m apart; you judged the image inconclusive). Anganwadi location Unverified (about 500 m from the colocated school). School targets are interior points of compounds |
| 4 | Segmentation ran or blocker recorded | **Partial** | Prediction rasters exist on the mosaic grid (classes 1-7, 0 = nodata, Building = 2 per extraction scripts). Inference was not re-run; `check_class_mapping.py` output and the inference run log were not seen. No accuracy claim |
| 5 | Road extraction and network evaluated | **Unverified** | Planner uses TGRAC road cells. `connectivity_audit_v1` (ca1-ca3) and `audit_road_connectivity.py` exist; not read. No comparison of segmentation-derived roads with the reference was seen |
| 6 | Building/cluster connectivity | **Partial** | 163 access polygons; 103 (63.19 %) within 50 m of a road at baseline, 118 (72.39 %) after planning. This is proximity, not graph connectivity or legal access |
| 7 | Route generation and selection checked | **Met for the reference run** | `run7_regress`/`fv_repro1`: 13 of 15 routed; C12 and C13 failed with traced causes (Phase B); `run6_slope_soft` is a no-slope-limit sensitivity run |
| 8 | Evaluation and baseline comparison | **Partial** | C1/C2 experiments exist (most conditions single runs). No segmentation-quality metric (no ground truth). Runtime/memory: only the "about 61 min" inference note |
| 9 | Paths, parameters, failures, reproducibility recorded | **Partial** | Planner chain reproduced 13/13 (`fv_20261024_193950`) with parameters in `summary.json`. Inference environment/log not verified |
| 10 | Results and limitations reviewed | **Partial** | First-village report plus `PHASE_B_FINDINGS.md` corrections (six wording changes not yet applied to the report) |
| 11 | Pipeline tested without damaging prior outputs | **Met for the planner chain** | new output folders only; inference not re-run |
| 12 | Final completion report | **Not started** | to be written after items 2-10 |

## Findings added today (all Verified unless stated)
- Priority weights: `priority_group` has no effect in `plan_network_v2.py`; weights come from keywords in type/name (health/sub-centre 4.0, school 3.0, anganwadi 3.0, cluster 1.0 + 0.25 per extra building). They are described in the code as ordinal design parameters.
- Six evaluation windows are 200 x 200 m each (1.3 % of the village), chosen by role from model predictions; 67 model buildings inside them. Purposive, not a random sample.
- The mosaic has a blank corner (3.32 % of its bbox, 0.967 km2, outside the polygon): the missing 12th tile.
- Esri edge tiles were requested at 3000 x 3000 px with non-square ground extent; whether the server adjusted the extent is **Unverified**. Check: overlay the TGRAC roads on the edge tiles.
- School layers in the TGRAC service: polygons `Schools/MapServer/4` (has School_Code); points 0, 1, 3. Resolves "school layer not identified" for Damarakunta's source.

## Pending decisions (yours)
1. Licence route B1 / B2 / B3.
2. Labelling workflow (Part C): approve or change; optional seeded random windows (new layer).
3. Whether to build the edge-tile overlay check.
4. Whether to run read-only checks of the connectivity audits and class-mapping output (they need your paste).

## Proposed DECISIONS rows (not applied; rows 21-24 in the earlier file concern other villages and are on hold)
| # | Decision | Reason | Evidence |
|---|---|---|---|
| 25 | Sub-centre target kept at the `tgrac_health.gpkg` position, recorded Unverified; the sub-centre-layer position (235.7 m away) is not substituted | Both positions share NIN 8734223673; image review inconclusive | `damarakunta_health_record_comparison.csv`; `health_two_coordinates_comparison.png` |
| 26 | School compounds documented as TGRAC `Schools/MapServer/4` geometries, accessed about 5 Oct 2026 | Geometry equal to the layer (0.0 m2 difference) | provenance query of 2026-10-24 |
| 27 | `priority_group` documented as inert; hierarchy comes from keyword weights, which are design parameters | Code read | `plan_network_v2.py` `priority_weight` |
| 28 | Segmentation accuracy reported as "not computed" until reference labels exist | `reference_buildings` has 0 features; label folder empty | Stage A report |
