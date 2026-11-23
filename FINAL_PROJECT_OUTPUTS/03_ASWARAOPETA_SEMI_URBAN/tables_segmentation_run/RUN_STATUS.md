# Aswaraopeta (Ashwaraopet town), StrongDINOv2Seg run: run status

Status: **complete on the owner's PC** (inference, extraction, segmentation routing, report, `final_maps_1_to_5/`, pushed in commit c178bf1). Synced into FINAL_PROJECT_OUTPUTS by `scripts/build_final_project_outputs.py`.

Results (from `metrics_summary.json`): 1,297 footprints (PLAUSIBLE 772, UNRESOLVED_MERGE 452, SMALL_EXCLUDED 55, REVIEW 18); 1,242 used for the footprint penalty; 678 road-gap targets, 636 routed;
11 verified facilities; independent unique length 43.1 km, two-stage shared plan 29.7 km (saving 31.2 %);
157 routes cross footprints, 1090 m inside other footprints.
Open-footprint comparison: `comparison_open_vs_segmentation.csv` (two-stage saving 37.2 % open vs 31.2 % segmentation). The mapped road layer is sparse (10.1 km/km2; 51 % of footprints are >30 m from a road), so results mostly reflect missing roads; 42 targets are unrouted (636 of 678).
Annotated satellite maps (facility labels F<id>, length and illustrative cost): regenerate on the PC with `python scripts\make_village_map_series.py --village <id>` and `python scripts\run_village_end_to_end.py --village <id> --stage report`.

Caveats (read before quoting numbers)
* The boundary is a derived built-up settlement extent (ESA WorldCover class 50 closed and buffered), not an administrative boundary; the shape is fragmented with thin road strips.
* Only the main strategy comparison was run (`--quick`); the penalty, omission and road-gap sweeps are not run for this variant, so those rows read n/a in the master table.
* The run log (`run_log_full.json`) was not committed from the owner's PC. Costs are ordinal. The Rs 75 lakh/km PMGSY rate (range 60-90) is an owner-supplied, unverified assumption used only for illustrative annotations on the maps.
* StrongDINOv2Seg pixel accuracy is the frozen 71.3 % reported for the model; no new training was done.
