# Damarakunta: final completion report (PROPOSED OUTLINE with current evidence; NOT a completion claim)
Target path: `Siddipet\Damarakunta\DAMARAKUNTA_FINAL_COMPLETION_REPORT_PROPOSED.md` (check that it does not exist; otherwise version it).
Evidence labels: **[M]** measured by project code/logs, **[S]** source-reported, **[I]** inference, **[U]** unverified, **[L]** limitation. Date of evidence: 24 Oct 2026. Damarakunta only.

## 1. Objective and scope
Road-network and facility planning for Damarakunta (Markook Mandal, Siddipet; EPSG:32644) from imagery, a segmentation model and GIS layers. Contributions: C1 segmentation-error propagation into planning results; C2 two-stage route generation/selection with shared-edge credit; C3 empirical transfer findings (no novelty claimed for facility prioritisation, A*, least-cost paths or AHP). No other village is part of this report. [L] No field validation, legal road access or construction readiness is claimed.

## 2. Data sources and provenance
- Roads, anganwadi, health, sub-centres, plinth, village boundary: TGRAC layers (map in `layers_pinned.json`) [S]. School compounds: geometry equals TGRAC `Schools/MapServer/4` (0.0 m2 symmetric difference for codes 36181600902 and 36181600903) [M]; the project script wording "verified" is unexplained and the local file was written by a GDAL/OGR tool on 5 Oct 2026 [M]; the layer's own accuracy is [U].
- Imagery: Esri World Imagery, 11 of 12 tiles, mosaic 0.6 m [M]; **licence UNRESOLVED** (enquiry drafted, unsent) [U]. WorldCover 10 m, 30 m DEM, derived 10 m slope and cost surface [S/M].

## 3. Input validation and alignment
Mosaic 11,296 x 7,171 at 0.6 m; 3.32 % of the bounding box is all-zero and equals the missing 12th tile, outside the village polygon [M]. Exact transform equality inside the 0.6 m family, the 10 m family and the 30 m family; 10 m nests exactly in 30 m; 0.6 m does not nest in 10 m (tied by coordinates only) [M]. Cost raster valid share inside the polygon 99.31 %, WorldCover 99.90 % [M]. [U] Absolute georeferencing of the Esri tiles (edge tiles requested with non-square extent); the roads-on-mosaic check is prepared, results pending. Shared CRS or resolution is not evidence of correct georeferencing.

## 4. Model checkpoint, inference, runtime
`D:\new_MPS\remoteSensingWebApp\checkpoints\best_model.pth` (outside the project) [M]; CPU, tile 560, stride 420, margin 70, 459 tiles, 3,640.5 s (60.7 min) [M]. SHA-256, size and date: PENDING (command prepared). Training data and model version provenance: **unknown** [U]. Memory use: **not recorded** [U]. Environment versions: PENDING.

## 5. Segmentation output
Class shares: 1 38.479 %, 2 (building) 0.332 %, 3 (road) 0.05 %, 4 0.765 %, 5 38.795 %, 6 2.35 %, 7 19.228 % [M]; log note "raw argmax over classes 1-7; unvalidated". Class order matches LoveDA (my inference) [I]. **Accuracy not computed: no reference labels exist** (`reference_buildings` has 0 features) [L]. Six purposive windows (1.3 % of the village, chosen from predictions) hold 67 model buildings [M]; a labelling plan and a random-window plan await your approval.

## 6. Road source and connectivity audit
Planning uses the TGRAC roads; the model road class is not used (0.05 %) [M]. Completeness of the TGRAC layer is [U]. Audit `ca_ref` (read-only, FAIL=0, FLAG=1) [M]: 7 components, main component 86,101.5 m = 92.09 % of 93,496.8 m, 29-30 dangling ends. 163 candidate polygons: 103 within 50 m by polygon distance (92 by representative point), 10 touch the main component within 1 m. All of this is proximity; the statuses are `NOT_ESTABLISHED_PROXIMITY_ONLY`.

## 7. Facility targets and unresolved locations
Four targets: MPPS, ZPHS (school polygons' interior points), sub-centre `HEALTH_8734223673`, Damarakunt-I anganwadi 1702300 [M]. The raw count of 7 was inflated by stacked anganwadi points of other villages and a duplicated sub-centre [M]. **Sub-centre position unverified**: two layers carry the same NIN ID 8734223673, 235.7 m apart; the planner target is the health-layer position; the other is not substituted [U]. **Anganwadi position unverified**; it lies about 500 m from the MPPS record that flags it as colocated; the discrepancy is not resolved and neither record is declared wrong [U]. `priority_group` = 1 for all targets is inert in the planner; the hierarchy comes from keyword weights (health 4, school 3, government 2, default 1), which are ordinal design parameters, not calibrated values [M from code].

## 8. Candidate route generation and selection
Planner v2: 10 m grid, slope limit 10 degrees, snap 30 m, building multiplier 4.0, k = 3, attach tolerance 15 m [M]. Reference run `run7_regress`; reproduction `fv_repro1` (driver run passed 13/13 checks) [M]. 13 of 15 targets routed; C12 failed (slope 10.349 deg against the 10 deg limit) and C13 failed (cell centre outside the boundary polygon; mask is not a legal layer) [M]. Network-aware unique length 1,506.1 m vs independent 1,516.6 m [M]. All 13 routes reach the main component (deterministic geometry), 2 ambiguous [M]. Access change 103 to 118 = 9 by construction + 6 spillover; identical in both runs [M]. This is a proximity change for 15 polygons, not an area-wide accessibility improvement [L].

## 9. C1/C2 experiments and baseline comparison
Summarise from the experiment CSVs: most conditions are single runs (random omission has 5 seeds), so no spread for them [L]. C1 perturbs model-derived polygons, so it measures plan response, not agreement with real buildings [L]. `run6_slope_soft` is a no-slope-limit sensitivity run from an earlier planner version [M]. Corrected-health-target sensitivity run: not started, needs your approval.

## 10. Reproducibility and environment
Done: reproduction run, input integrity SHA-256 recorded by the audit. Missing: checkpoint hash, inference script hash/config, library versions, memory use, data-dictionary entries for four `fv_repro1` columns (documentation only).

## 11. Failure cases, uncertainties, limitations
C12 and C13 as above; boundary accuracy [U]; TGRAC layer currency [U]; DEM 30 m precision against a 10 degree limit [L]; polygon merges (62 polygons classed UNRESOLVED_MERGE) [M]; single annotator and single imagery source [L].

## 12. Licence restrictions and pending approvals
Esri licence unresolved; no new imagery export/download; enquiry draft awaiting your review/sending; derived-figure and redistribution permissions unknown. Wording corrections from `PHASE_B_FINDINGS.md` (six) are a proposal only; proposed DECISIONS rows 25-30 are not applied; `DECISIONS.md` untouched.

## 13. Gate criteria (honest status as of this draft)
| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | Inputs validated | Complete (alignment of absolute georeferencing unverified) | Stage A report; `pa1` |
| 2 | Imagery licence | **Unresolved** | enquiry draft |
| 3 | Facility selection | Partial (2 locations unverified) | health comparison; Stage C |
| 4 | Segmentation | Partial (ran; accuracy not computed) | `run_log_full.json` |
| 5 | Road/network | Partial (TGRAC only, completeness unknown) | `ca_ref` |
| 6 | Building connectivity | Complete as proximity only | `ca_ref` |
| 7 | Route generation | Complete with 2 documented failures | `run7_regress`, `fv_repro1` |
| 8 | Evaluation | Partial (single runs, no ground truth) | experiment CSVs |
| 9 | Reproducibility records | Partial (hash, memory, versions missing) | see section 10 |
| 10 | Limitations documented | Partial (wording corrections unapplied) | `PHASE_B_FINDINGS.md` |
| 11 | Non-destructive testing | Complete so far (all new outputs in new paths) | this session's file list |
| 12 | Final report | **Not complete**; this is an outline | this file |
**Overall: Damarakunta is NOT complete.** The gate stays open until items 2, 4 (reference labels), the edge-tile result and the reproducibility gaps are addressed or explicitly accepted by you.

## 14. Decisions needed from you
1. Review/send the licence enquiry; who is the contact. 2. Approve (or edit) the annotation plan, then the random-window plan. 3. Run the read-only commands (hash, environment, Anganwadi evidence, overlay) and paste results. 4. Whether to apply the six wording corrections as a new report version. 5. Whether to apply DECISIONS rows 25-30 (you edit `DECISIONS.md`; I will not). 6. Whether any corrected-health-target sensitivity run is wanted (not started).
