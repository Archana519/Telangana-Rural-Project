# Cleanup report, phase 1 (2026-10-30)

Nothing was deleted. 323 items were moved (renamed on the same drive) to `archive/2026-10-30_phase1/`, keeping their original relative paths. Every move is logged with SHA-256 in `archive/2026-10-30_phase1/MOVE_LOG.csv`; the plan is in `PLAN.csv`. To undo everything:

```bash
python src/tools/restore_from_archive.py 2026-10-30_phase1
```

## 1. Moved to archive

### scripts/ (legacy scripts and support files): 193 items
`CONNECTIVITY_AUDIT_FINDINGS_v2.md`, `Damarakunta_Final_Map_v3_1.py`, `Damarakunta_Final_Map_v3_2.py`, `Damarakunta_Final_Map_v4.py`, `__pycache__`, `align_slope_to_worldcover.py`, `assess_building_access.py`, `assess_building_access_v2.py`, `assess_damarakunta_route_feasibility.py`, `assess_damarakunta_route_feasibility_v3.py`, `attention.pdf`, `audit_loveda_masks.py`, `audit_phaseB_damarakunta.py`, `audit_plan_run.py`, `audit_provenance_alignment.py`, `audit_road_connectivity.py`, `audit_road_connectivity.py.bak_ca1`, `audit_road_connectivity.py.bak_ca2patch`, `audit_road_connectivity_new.py`, `build_damarakunta_road_graph.py`, `build_road_graph.py`, `calculate_school_overlap.py`, `check_class_mapping.py`, `check_damarakunta_facility_road_access.py`, `check_damarakunta_health_records.py`, `check_damarakunta_route_endpoints.py`, `check_damarakunta_routing_inputs.py`, `check_damarakunta_source_coverage.py`, `check_edge_alignment.py`, `check_esri_mosaic_coverage.py`, `check_plan_connectivity.py`, `check_school_class_distribution.py`, `check_tgrac_image.py`, `classify_candidate_routes.py`, `compare_candidate_routes_with_existing_roads.py`, `compare_damarakunta_health_records.py`, `compare_house_routes_v1_vs_slope25.py`, `connect_priority_facilities.py`, `create_candidate_routes_gpkg.py`, `create_cost_surface.py`, `create_d`, `create_damarakunta_channel_orders.py`, `create_damarakunta_esri_full_preview.py`, `create_damarakunta_esri_visual_diagnostic.py`, `create_damarakunta_final_review_package_v1.py`, `create_damarakunta_final_review_package_v3.py`, `create_damarakunta_residential_tile.py`, `create_damarakunta_sentinel2_visual_diagnostic.py`, `create_damarakunta_visual_diagnostic.py`, `create_esri_test_preview.py`, `create_phase13_diagnostic.py`, `create_residential_visual_diagnostic.py`, `create_slope.py`, `damarakunta_routes_v3_multi_criteria_ranking.xlsx`, `damarakunta_routes_v3_preferred_candidates.xlsx`, `diagnose_candidate_route_costs.py`, `diagnose_damarakunta_model.py`, `diagnose_route_flags.py`, `discover_mandal_villages.py`, `dk_stageA_prepare.py`, `dk_stageB_connectivity_audit_v1.py`, `dk_stageB_maps.py`, `dk_stageB_schema_probe_v1.py`, `download_damarakunta_sentinel.py`, `download_damarakunta_sentinel2.py`, `draw_damarakunta_named_routes.py`, `draw_damarakunta_named_routes_v3.py`, `evaluate_candidate_routes.py`, `evaluate_damarakunta_accessibility_v3.py`, `evaluate_damarakunta_accessibility_v3_backup.py`, `evaluate_damarakunta_accessibility_v3_corrected.py`, `evaluate_damarakunta_accessibility_v3_working_backup.py`, `evaluate_layer_vs_reference.py`, `evaluate_new_road_candidates.py`, `evaluate_vs_reference.py`, `evaluate_vs_reference.py.bak_before_digitizer_patch`, `export_esri_damarakunta_test.py`, `export_esri_damarakunta_tile12.py`, `extract_building_footprints.py`, `extract_buildings_roads.py`, `extract_buildings_v7.py`, `extract_candidate_buildings.py`, `extract_tgrac_plinth.py`, `extract_village_reference_data.py`, `generate_candidate_routes.py`, `generate_damarakunta_access_routes.py`, `generate_damarakunta_routes_v4_review_map.py`, `generate_damarakunta_v5_building_review.py`, `generate_new_road_candidates.py`, `generate_presentation_maps.py`, `generate_presentation_maps_backup.py`, `google_open_buildings_test.py`, `inspect_building_pipeline.py`, `inspect_cost_surface_alignment.py`, `inspect_damarakunta_bands.py`, `inspect_damarakunta_clipped_rasters.py`, `inspect_damarakunta_cost_surface.py`, `inspect_damarakunta_facilities.py`, `inspect_damarakunta_imagery.py`, `inspect_damarakunta_mpps_access.py`, `inspect_damarakunta_nearest_roads.py`, `inspect_damarakunta_reference.py`, `inspect_damarakunta_roads.py`, `inspect_geotiff.py`, `inspect_real_imagery.py`, `inspect_reference_layer_fields.py`, `inspect_reference_layers.py`, `inspect_school_building_components.py`, `inspect_slope_alignment.py`, `inspect_tgrac_angadi_kistapur.py`, `layers_pinned.json`, `make_digitizing_windows.py`, `make_first_village_report (1).py`, `make_first_village_report.py`, `map_damarakunta_health_locations.py`, `map_individual_house_network_v1.py`, `map_individual_house_routes_v1.py`, `phase0_audit.py`, `phase19_multi_criteria_evaluation.py`, `phase20_route_evaluation.py`, `phase21_before_after.py`, `phase22_fair_comparison.py`, `phase23_ablation_study.py`, `phase24_sensitivity_analysis.py`, `phase25_batch_readiness.py`, `phase25_create_village_manifest.py`, `phase25_discover_villages.py`, `phase25_master_status_report.py`, `phase25_multiple_villages.py`, `phase25_processing_summary.py`, `phase25_validate_village_inputs.py`, `phase25_village_expansion_checklist.py`, `phase25_village_template.py`, `plan_gap_routes.py`, `plan_network_v2_before_experiments_backup.py`, `plan_network_v2_before_slopefix_backup.py`, `plan_network_v2_run1_backup.py`, `plot_connectivity_audit.py`, `prepare_damarakunta_imagery.py`, `prepare_damarakunta_model_tiles.py`, `prepare_damarakunta_route_review.py`, `prepare_damarakunta_sentinel2_model_input.py`, `prepare_damarakunta_sentinel2_model_tiles.py`, `prepare_esri_lod18_tiles.py`, `prepare_esri_reference_tiles.py`, `prepare_model_tiles.py`, `prepare_real_imagery.py`, `prepare_siddipet_village.py`, `qa_candidate_buildings.py`, `query_village_reference_data.py`, `rank_damarakunta_routes_v3.py`, `reconstruct_damarakunta_routes.py`, `reconstruct_damarakunta_routes_v2.py`, `reconstruct_damarakunta_routes_v3.py`, `reproject_to_utm.py`, `rerun_v4_with_buildings.py`, `route_individual_houses_v1.py`, `run_damarakunta_sentinel2_inference.py`, `run_esri_lod18_segmentation.py`, `run_esri_reference_segmentation.py`, `run_first_village.py`, `run_planning_experiments.py`, `run_rural_planning_pipeline.py`, `run_village_segmentation.py`, `save_damarakunta_residential_mask.py`, `score_routes_with_buildings.py`, `summarise_access_gain.py`, `sweep_c1_building_perturbation.py`, `test_damarakunta_band_combinations.py`, `test_damarakunta_channel_orders_model.py`, `test_damarakunta_esri_inference.py`, `test_damarakunta_residential_inference.py`, `test_damarakunta_sentinel_export.py`, `test_esri_appearance_normalization.py`, `test_esri_damarakunta.py`, `test_esri_scale_normalization.py`, `test_esri_tile12_png.py`, `test_real_village_inference.py`, `tgrac_rest.py`, `validate_damarakunta_access_routes.py`, `validate_damarakunta_inputs.py`, `validate_damarakunta_road_graph.py`, `validate_damarakunta_route_connectivity_v3.py`, `validate_damarakunta_route_connectivity_v3_backup.py`, `validate_damarakunta_route_connectivity_v4.py`, `validate_damarakunta_route_connectivity_v4_layer.py`, `validate_school_predictions.py`, `verify_damarakunta_boundary.py`, `verify_damarakunta_model.py`, `verify_loveda_mask_ids.py`, `verify_siddipet_village.py`, `village_readiness.py`, `visualize_school_predictions.py`

### project root (clutter, superseded notes, old tests and logs): 24 items
`--layers-json`, `1`, `DAMARAKUNTA_COMPLETION_CHECKPOINT_20261024.md`, `DAMARAKUNTA_COMPLETION_CHECKPOINT_20261024_v2.md`, `Damarakunta_Settlement_Detail_Maps.py`, `SLOPE_LIMIT_DEG`, `__pycache__`, `archive_cleanup`, `full1_after.txt`, `full1_before.txt`, `generate_damarakunta_access_routes_review.txt`, `layers_pinned.json`, `logs`, `newfunc.py`, `patch_detail.py`, `run5_after.txt`, `run5_before.txt`, `run6_after.txt`, `run6_before.txt`, `source_file_report.txt`, `strongdinov2seg_training_updated (2).py`, `temp_claude_review`, `tests`, `view_footprints.py`

### Siddipet/Damarakunta/results/ (legacy outputs): 106 items
`ALL_OUTPUT_IMAGES`, `_inspection_report.md`, `anganwadi_facility_crop.png`, `appearance_tests`, `audit_phaseB`, `band_tests`, `channel_order_comparison.png`, `channel_order_model_test`, `connectivity_audit_v1`, `damarakunta_accessibility_evaluation_v3.csv`, `damarakunta_accessibility_evaluation_v3.gpkg`, `damarakunta_accessibility_summary_v3.txt`, `damarakunta_esri_full_preview.jpg`, `damarakunta_esri_mosaic_coverage.gpkg`, `damarakunta_feasibility_map.png`, `damarakunta_feasibility_map_v3.png`, `damarakunta_feasibility_zoom.png`, `damarakunta_feasibility_zoom_v3.png`, `damarakunta_graph_validation.csv`, `damarakunta_health_location_comparison.png`, `damarakunta_health_record_comparison.csv`, `damarakunta_least_cost_access_routes.csv`, `damarakunta_least_cost_access_routes.gpkg`, `damarakunta_named_routes_map.png`, `damarakunta_named_routes_zoom.png`, `damarakunta_reconstructed_facility_checks.csv`, `damarakunta_reconstructed_route_alternatives.gpkg`, `damarakunta_reconstructed_route_comparison.csv`, `damarakunta_reconstructed_routes_README.txt`, `damarakunta_reconstructed_routes_map.png`, `damarakunta_route_connectivity_validation_v3.csv`, `damarakunta_route_connectivity_validation_v3.gpkg`, `damarakunta_route_connectivity_validation_v3_README.txt`, `damarakunta_route_connectivity_validation_v4.csv`, `damarakunta_route_connectivity_validation_v4.gpkg`, `damarakunta_route_connectivity_validation_v4_README.txt`, `damarakunta_route_connectivity_validation_v4_layer.csv`, `damarakunta_route_connectivity_validation_v4_layer.gpkg`, `damarakunta_route_connectivity_validation_v4_layer_README.txt`, `damarakunta_route_diagnostic_report.csv`, `damarakunta_route_feasibility_screening.csv`, `damarakunta_route_feasibility_screening_v2.csv`, `damarakunta_route_feasibility_screening_v3.csv`, `damarakunta_route_parcel_impacts.gpkg`, `damarakunta_route_parcel_impacts_v2.gpkg`, `damarakunta_route_parcel_impacts_v3.gpkg`, `damarakunta_route_review.gpkg`, `damarakunta_route_validation.csv`, `damarakunta_routes_v2.gpkg`, `damarakunta_routes_v2_README.txt`, `damarakunta_routes_v2_comparison.csv`, `damarakunta_routes_v2_facility_checks.csv`, `damarakunta_routes_v3.gpkg`, `damarakunta_routes_v3_README.txt`, `damarakunta_routes_v3_comparison.csv`, `damarakunta_routes_v3_facility_checks.csv`, `damarakunta_routes_v3_multi_criteria_ranking.csv`, `damarakunta_routes_v3_preferred_candidates.csv`, `damarakunta_routes_v4.gpkg`, `damarakunta_routes_v4_README.txt`, `damarakunta_routes_v4_comparison.csv`, `damarakunta_routes_v4_facility_checks.csv`, `damarakunta_routes_v4_review_details.pdf`, `damarakunta_routes_v4_review_details.png`, `damarakunta_routes_v4_review_map.pdf`, `damarakunta_routes_v4_review_map.png`, `damarakunta_routes_v4_review_table.csv`, `damarakunta_routes_v4_review_table_new.csv`, `damarakunta_sentinel2_diagnostic.png`, `damarakunta_tile000_diagnostic.png`, `damarakunta_v4_consolidated_review.csv`, `damarakunta_validated_route_diagnostics.gpkg`, `esri_damarakunta_test_preview.jpg`, `esri_world_imagery_identify.json`, `final_output_validation_v1`, `final_output_validation_v3`, `final_output_validation_v3_1`, `final_output_validation_v3_2`, `final_output_validation_v4`, `first_village_runs`, `footprints_v9_test`, `google_open_buildings`, `hash_cache.json`, `health_subcentre_facility_crop.png`, `health_subcentre_marked.png`, `health_two_coordinates_comparison.png`, `house_to_road_access_audit_v1.csv`, `img.qgz`, `individual_house_network_plausible_only_v1`, `individual_house_routing_slope25_v2`, `mapping_audit`, `pipeline_cache.json`, `pipeline_runs`, `planning_experiments`, `presentation_maps`, `residential_visual_diagnostic.jpg`, `residential_visual_diagnostic_corrected.jpg`, `scale_tests`, `school_prediction_comparison.png`, `schools_comparison.png`, `tile_0001_esri_visual_diagnostic.jpg`, `tile_0137_esri_visual_diagnostic.jpg`, `tile_0273_esri_visual_diagnostic.jpg`, `v5_building_review`, `v6_buildings`, `v7_instances`

Notes: `results/google_open_buildings` (17 GB test run) is in the archive. Scripts that kept scripts name in code (`plan_individual_house_network_v1`, `reconstruct_damarakunta_routes_v4`, older `dk_stageB_c1_*` versions, `dk_stageB_run`) stay in `scripts/` and are also copied to `src/legacy_dependencies/`.

## 2. Final directory tree

```
.gitignore
CLEANUP_PHASE1_REPORT.md
Complete M.docx
DAMARAKUNTA_BUILDING_ANNOTATION_PLAN_PROPOSED.md
DAMARAKUNTA_COMPLETION_CHECKPOINT_20261024_v2_1.md
DAMARAKUNTA_FINAL_COMPLETION_REPORT_PROPOSED.md
DAMARAKUNTA_IMAGERY_LICENCE_ENQUIRY_DRAFT.md
DAMARAKUNTA_RANDOM_WINDOW_SAMPLING_PLAN_PROPOSED.md
DAMARAKUNTA_READONLY_COMMANDS_20261024.md
DAMARAKUNTA_STAGE_A_INPUT_VALIDATION.md
DAMARAKUNTA_STAGE_B_C_PROPOSALS.md
DATA_SOURCES.md
DECISIONS.md
DECISIONS_proposed_additions.md
DELIVERABLES_DAMARAKUNTA_STAGE_B/  (9 entries)
Generative_AI_Assignment/  (0 entries)
PHASE_B_FINDINGS.md
PHASE_C_READINESS_PLAN.md
PROJECT_COMPLETION_STATUS.md
Phase1_Report_CBIT_Format/  (24 entries)
Presentation_Review/  (6 entries)
README.md
README_google_open_buildings_test.md
README_presentation_maps.md
Siddipet/  (4 entries)
  Angadi_Kistapur/  (10 entries)
  Damarakunta/  (8 entries)
  _village_discovery/  (2 entries)
  _village_readiness/  (7 entries)
archive/  (2 entries)
configs/  (1 entries)
digitizer/  (9 entries)
docs/  (4 entries)
download_manifest.csv
inputs/  (1 entries)
outputs/  (7 entries)
  connectivity/  (3 entries)
  final_comparison/  (6 entries)
  final_maps/  (4 entries)
  final_package/  (2 entries)
  run_20261030_192515/  (7 entries)
  run_20261030_202603/  (7 entries)
  verification/  (6 entries)
phase1_classified_inventory_PROPOSED.csv
requirements.txt
scripts/  (60 entries)
src/  (10 entries)
  legacy_dependencies/  (8 entries)
  modeling/  (7 entries)
  preprocessing/  (15 entries)
  reporting/  (6 entries)
  routing/  (5 entries)
  stress_test/  (11 entries)
  tools/  (3 entries)
  validation/  (13 entries)
```

`scripts/` still holds the verified Stage B scripts, because the runner looks for `scripts/plan_network_v2.py` by default and the run manifests record that path. `src/` holds identical copies grouped by stage (preprocessing, modeling, routing, stress_test, validation, reporting). Checked: the planner copy has the same SHA-256 (d00ea92028101131627b8592e3df2c33ff350efac9b1de09f9b64cdd56ef70a4) and the runner still starts.

## 3. Master command (phase 2)

```bash
python src/run_pipeline.py                 # quick profile
python src/run_pipeline.py --profile full    # adds C2 ablation and all 20 omit/add seed runs
python src/run_pipeline.py --dry-run             # checks hashes, prints the plan, runs nothing
python src/run_final_package.py            # after a full run: verification, connectivity, 4 maps, comparison tables, thesis chapter
```

It verifies the 11 input files and the planner by SHA-256 against the reference run, runs Stage A and Stage B into a **new** `results/run_<timestamp>/` folder, runs the validator, the connectivity audit and `src/routing/explain_routes.py`, checks that every metric equals the reference run `run_20261029_01`, and collects the results in `outputs/run_<timestamp>/stage1_detect ... stage5_validate` with a `RUN_SUMMARY.md`. Stage 1 (detection) and Stage 2 (terrain) are verified inputs and are not re-run: the segmentation weights' location is not recorded, and rebuilding the terrain would overwrite verified inputs. Input sources, dates and licence status: `inputs/METADATA.md`.
