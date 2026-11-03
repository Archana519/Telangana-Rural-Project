# scripts/

The verified working scripts. **Do not move or edit these casually.** The pipeline checks their SHA-256 hashes and the runners look for `plan_network_v2.py` in this folder, so a change here would break the reproduction check.

| Group | Scripts |
|---|---|
| Prepare the village | `save_damarakunta_boundary`, `clip_*`, `reproject_worldcover`, `fill_slope_nodata`, `align_damarakunta_terrain`, `create_damarakunta_cost_surface`, `prepare_damarakunta_*`, `*_cadastral`, `dk_stageA_prepare_r3` |
| Find buildings | `extract_buildings_v8`, `run_damarakunta_inference`, `run_tiled_inference`, `mosaic_esri_damarakunta`, `export_esri_damarakunta_full` |
| Plan routes | `plan_network_v2` (the planner), `plan_individual_house_network_v1`, `reconstruct_damarakunta_routes_v4`, `dk_stageB_run*` (runners; `v1_6` is the newest) |
| Stress tests | `dk_stageB_c1_*` (omit/add buildings), `dk_stageB_c2_ablation_summary_v1` |
| Checks | `dk_stageB_validate`, `dk_stageB_connectivity_*`, `dk_stageB_run_repro_compare_v1`, `*_diag_v1`, `test_plan_network_v2` |
| Maps | `Damarakunta_Final_Map_v4_1`, `Damarakunta_Settlement_Detail_Maps`, `dk_stageB_maps_v2` |

Newer helper code that is safe to change lives in `../src/`.
