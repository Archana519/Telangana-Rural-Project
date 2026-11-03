# PROJECT_COMPLETION_STATUS (proposed document, 2026-10-24)

Save as a NEW file in `D:\Telangana_Rural_Project\` (it does not exist yet; nothing is overwritten).

Evidence labels: **Verified** = seen in output you pasted. **Unverified** = inferred, or not yet read. **Blocked** = cannot proceed without something listed.

## 1. Basis
- Your pasted inventory (`mtech_inventory.txt`), earlier pasted outputs (planner summaries, DECISIONS rows 1-8, results listings) and the first-village report `fv_20261024_193950`.
- I have **not** read the contents of the scripts named below. What they do is Unverified until I do.

## 2. Completed
| Item | Evidence |
|---|---|
| Damarakunta reference run `run7_regress` and reproduction `fv_repro1`; 13 of 13 reproduction checks pass | Verified (console + `repro_check.json` line) |
| Access gain recomputed for both runs (60 rows each, identical) | Verified (report section 5) |
| First-village report with limitations section | Verified (report read) |
| Planner and experiment scripts: `plan_network_v2.py`, `run_planning_experiments.py`, `summarise_access_gain.py`; earlier C1/C2 results in `experiments_v1\full1` | Verified (files listed; tables shown in report section 6) |
| Config-driven runner `run_rural_planning_pipeline.py` + `damarakunta.json` (inference, extract_buildings_v8, access stages) | Verified (config pasted). Its `network_planner` stage is disabled and says "NOT WRITTEN YET", which is out of date |
| Google Open Buildings v3 retrieved, reference only; offset study parked | Verified (earlier outputs) |
| Model checkpoint present; torch 2.14.0+cpu, **no CUDA**; 182.3 GB free on D: | Verified |

**Partial:** `Angadi_Kistapur` has a folder with rasters, derived layers, one segmentation raster, TGRAC reference layers and one result file; it is not pipeline-ready (section 4). Eight `phase25_*` village-expansion scripts exist (Oct 1); contents not seen.

**Not started:** Phase B audits, any additional village run, C3, final documents.

## 3. Findings from the inventory that change the plan
1. **Only two village folders exist** under `Siddipet`: Damarakunta and Angadi_Kistapur. Searching the project and `D:\new_MPS` for `*mosaic*.tif` and `*boundary*.gpkg|geojson` found nothing for any other village. Other file names could exist.
2. **Angadi_Kistapur is not equivalent to Damarakunta.**
   - No 0.6 m mosaic. Its imagery files are 1.3-1.6 MB, and 20 of 25 tiles in `tiles_560` are 0.0-0.1 MB (mostly empty or heavily compressed; not diagnosed).
   - It was processed in the Sep 30 workflow, before the v8 pipeline.
   - Its boundary exists only as a raw TGRAC GeoJSON (`raw\tgrac_master_admin`); the `study_area` folder holds no vector or raster file.
   - No prohibited-mask file was found in its folder.
3. **Imagery source and licence.** Damarakunta's 0.6 m mosaic came from an ESRI export and mosaic step (`export_esri_damarakunta_full.py`, `mosaic_esri_damarakunta.py`). The licence is unverified (proposed DECISIONS row 15). Repeating this for more villages repeats that status.
4. **Compute.** Inference is CPU-only; `damarakunta.json` notes 61 min for Damarakunta. Five more villages is hours of unattended compute, not days (Unverified: depends on village area).
5. **Terrain and land cover may already be on disk.** Angadi's raw folder has a DEM tile `n17_e078` and WorldCover tile `N15E078`. By tile naming these cover a block larger than one village, so villages inside that block (probably the rest of Markook mandal) may need no new download. Unverified until the tile extents are checked.
6. **Village-name hard-coding in the core pipeline scripts is small** (matches: `plan_network_v2.py` 5, `run_tiled_inference.py` 4, `extract_buildings_v8.py` 3, `assess_building_access_v2.py` 3, `run_rural_planning_pipeline.py` 2). Whether these are defaults or logic is Unverified. Most Damarakunta-named scripts are one-off data preparation (cost surface, terrain, boundary, facilities) and would need a generic equivalent.
7. **Housekeeping:** `make_first_village_report (1).py` is a same-size copy (22,113 bytes) of `make_first_village_report.py`. Several `*_backup.py` and `.bak` files exist. Nothing should be deleted without your decision.

## 4. Remaining tasks
Effort figures are my rough estimates of working time, not measurements.

| ID | Task | Scripts / inputs needed | Missing | Depends on | Rough effort |
|---|---|---|---|---|---|
| B1 | C12: does the soft-slope run route it? | `run6*` `summary.json`, `target_table.csv`; `plan_network_v2.py` | nothing | none | 0.5 h |
| B2 | C13: why is the prohibited mask 1 there? | prohibited mask tif; `create_damarakunta_cost_surface.py`, `align_damarakunta_terrain.py`, `audit_damarakunta_masks.py`; source layers | maybe the source layers | none | 1 h; may end as "unknown" |
| B3 | 165 `inside_village` vs 163 access polygons | `buildings_v8_full.gpkg`, `access_assessment.gpkg`, `assess_building_access_v2.py` | nothing | none | 0.5 h |
| B4 | 1,631 dropped road cells: where, and effect on attachment | TGRAC roads gpkg, cost raster, `data_check.json` | nothing | none | 1 h |
| B5 | C1 coverage/overlap definitions, effect of missing and split clusters | `run_planning_experiments.py`, `sweep_c1_building_perturbation.py` | nothing | none | 1 h |
| B6 | Verify report numbers, units, wording | report CSVs, `summary.json` | nothing | B1-B5 | 0.5 h |
| C0 | Decide imagery source and village list (D1, D2) | TGRAC master admin query; `tgrac_rest.py` | **your decision** | none | 0.5 h |
| C1 | Generic per-village data prep (boundary, DEM/WorldCover clip, slope, cost, prohibited mask, roads, facilities) | `prepare_siddipet_village.py`, `create_cost_surface.py`, `clip_*`, `create_slope.py` etc. | to be read | C0 | 2-3 h to build, then per village |
| C2 | Pilot: Angadi_Kistapur end to end | all of the above + 0.6 m imagery | **0.6 m imagery** | C1 | 3-4 h |
| C3 | At least four more villages (Angadi counts as one) | per-village config, CPU inference | **villages + imagery** | C2 | per village ~1 h compute + prep |
| D1 | C1 experiments per village; C2 vs independent baseline per village | `run_planning_experiments.py` | per-village inputs | C3 | 2-3 h compute |
| D2 | C3 table across villages, limitations stated | outputs of D1 | possibly building reference (D3) | D1 | 1 h |
| E | Provenance inventory, tables, maps, architecture diagram, methodology, limitations, final report (separate proposed files) | everything above | nothing | D2 | 1-2 days |

## 5. Shortest safe route
1. Run B1-B6 now. They need no new data and keep Damarakunta defensible.
2. In parallel, settle D1 and D2, and build new per-village config files (new files only; `damarakunta.json` is not edited).
3. Pilot Angadi_Kistapur end to end. Fix only the smallest blockers found.
4. Repeat for at least four more villages, running CPU inference unattended.
5. Run D1, D2 and E.

## 6. Open decisions (defaults stated; tell me if you want a different one)
- **D1 Imagery source.** Default: reuse the ESRI export used for Damarakunta, for comparability, labelled licence-unverified in every village. Alternatives: the TGRAC image, or Sentinel-2 at 10 m. Sentinel-2 was tried for Damarakunta (scripts exist), and I have not seen why it was not adopted.
- **D2 Village list.** Default: Angadi_Kistapur plus villages in Markook mandal, chosen by data availability.
- **D3 What C3 measures per village.** Default: planning outcomes (served targets, access gain, failures) only. Measuring building-extraction accuracy would need manual reference windows per village, as Damarakunta's `digitize_windows.gpkg` did.

## 7. Not claimed
No field validation, legal access, construction readiness, ground truth, or transferability. Routing costs are cost units, not money. The 163 access polygons are not a confirmed building count.
