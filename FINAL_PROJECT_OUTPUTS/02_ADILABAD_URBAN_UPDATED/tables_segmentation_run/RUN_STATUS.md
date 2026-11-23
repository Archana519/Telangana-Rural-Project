# Adilabad Urban (Adilabad Town), updated boundary, StrongDINOv2Seg run: run status

Status: **complete on the owner's PC** (inference, extraction, segmentation routing, report, `final_maps_1_to_5/`, pushed in commit c178bf1). Synced into FINAL_PROJECT_OUTPUTS by `scripts/build_final_project_outputs.py`.

Results (from `metrics_summary.json`): 5,653 footprints (UNRESOLVED_MERGE 2773, PLAUSIBLE 2526, REVIEW 181, SMALL_EXCLUDED 173); 5,480 used for the footprint penalty; 613 road-gap targets, 607 routed;
86 verified facilities; independent unique length 36.3 km, two-stage shared plan 31.0 km (saving 14.4 %);
99 routes cross footprints, 677 m inside other footprints.
Open-footprint comparison: `comparison_open_vs_segmentation.csv` (two-stage saving 25.5 % with open footprints vs 14.4 % with segmentation; open footprints give about twice the unique length because Overture polygons are far more numerous).
Annotated satellite maps (facility labels F<id>, length and illustrative cost): regenerate on the PC with `python scripts\make_village_map_series.py --village <id>` and `python scripts\run_village_end_to_end.py --village <id> --stage report`.

Caveats (read before quoting numbers)
* The boundary is a derived built-up settlement extent (ESA WorldCover class 50 closed and buffered), not an administrative boundary; the shape is fragmented with thin road strips.
* Only the main strategy comparison was run (`--quick`); the penalty, omission and road-gap sweeps are not run for this variant, so those rows read n/a in the master table.
* The run log (`run_log_full.json`) was not committed from the owner's PC. Costs are ordinal. The Rs 75 lakh/km PMGSY rate (range 60-90) is an owner-supplied, unverified assumption used only for illustrative annotations on the maps.
* StrongDINOv2Seg pixel accuracy is the frozen 71.3 % reported for the model; no new training was done.
