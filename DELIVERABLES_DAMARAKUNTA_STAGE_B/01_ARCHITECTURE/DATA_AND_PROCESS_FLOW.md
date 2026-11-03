> **RECONSTRUCTION (2026-11-02).** The original deliverables folder was lost and was not under version control. This file was rebuilt from the live result files and from the original text as displayed earlier in the same working session, and updated where later evidence changed it. It is not the original file.

# Data and process flow (files)

| Stage | Script | Reads | Writes |
|---|---|---|---|
| Boundary | `save_damarakunta_boundary.py` | raw TGRAC JSON (EPSG:32644 declared) | `study_area/damarakunta_boundary.gpkg` (`village_boundary`) |
| Grid | `align_damarakunta_terrain.py` | boundary, WorldCover clip, DEM clip | `aligned/*_worldcover_10m.tif`, `*_dem_30m.tif`, `*_slope_30m.tif`, `*_slope_10m.tif` |
| Cost | `create_damarakunta_cost_surface.py` | WorldCover 10 m, slope 10 m | `*_cost_surface_10m.tif`, `*_prohibited_mask_10m.tif` |
| Stage A | `dk_stageA_prepare_r3.py` | v8 buildings, footprints, roads, v1 house network | `stageA/` tables, manifests |
| Stage B | `dk_stageB_run_v1_1/2/3/4.py`, `plan_network_v2.py` | Stage A, rasters, roads, facilities, cadastral | one run folder per scenario under `stageB/` |
| C1 | `dk_stageB_c1_*` scripts | run folders | `_c1_*` folders |
| C2 | `dk_stageB_c2_ablation_summary_v1.py` | run folders | `_c2_abl_v1` |
| Audits and diagnostics | `dk_stageB_connectivity_*`, `*_diag_v1`, `dk_boundary_crs_compare_v1.py` | run folders and inputs | `_connectivity_*`, `_c0002_*`, `_boundary_*`, `_road_component_*`, `_chain_cell_*` |
| Final package | `src/run_final_package.py` and its steps | pipeline run | `outputs/verification`, `connectivity`, `final_maps`, `final_comparison`, `final_package`, `visual_audit` |

Every Stage B run folder records `inputs_manifest_stageB.csv` (role, path, bytes, SHA-256, including the runner script), `config_stageB.json` and `outputs_manifest.csv`.
`01_ARCHITECTURE/ARCHITECTURE_DIAGRAM.png` and `WORKFLOW_DIAGRAM.png` are the nine-stage diagrams drawn for the Phase-I report, replacing the original draft overview.
