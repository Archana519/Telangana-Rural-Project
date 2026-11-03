# Presentation results audit

Deck: `MTech_Major_Project_Review.pptx` (25 slides, speaker notes on every slide, built by `build_deck.py`).
Paths below are relative to `D:\Telangana_Rural_Project`. `DELIVERABLES_DAMARAKUNTA_STAGE_B` is abbreviated `DEL_B`.
Status key: **Verified** = read from the named output file today. **Provisional** = file exists, but a pending check (noted) is open. **Not shown** = left off the slides.

## 1. Numbers shown on slides

| Slide | Result | Value | Configuration | Source file | Status |
|---|---|---|---|---|---|
| 18, 20 | C1 baseline | 163 routed, 5,137.71 m unique, 31.52 m per target | S2, K3, 2 passes, slope 25°, cost C0, building penalty x4 | `DEL_B/03_RESULTS_TABLES/C1_SEGMENTATION_SENSITIVITY/PRIMARY_x4/c1_scenario_comparison.csv` | Verified |
| 18, 20 | C1 omit 25% smallest | 122 routed, 3,890.60 m (-24.27%), 31.89 m per target | same | same file | Verified |
| 18 | C1 omit 10% smallest | 146 routed, 4,717.53 m (-8.18%), 32.31 m per target | same | same file | Verified |
| 18, 20 | C1 omit merged candidates | 101 routed, 3,627.87 m (-29.39%), 35.92 m per target | same | same file | Verified |
| 20 | C1 P3 (no building penalty) baseline / omit-merge | 4,761.73 m / 3,425.66 m (-28.06%), 101 routed | P3: building penalty off | `DEL_B/00_START_HERE/README_PROJECT_OVERVIEW.md` section 11 and `.../P3_no_building_penalty/c1_scenario_comparison.csv` | Provisional: P3 baseline reproduction run not yet executed (`COMPLETION_GATE.md`) |
| 19, 20 | C2 independent vs shared plan | 6,755.36 m vs 5,137.71 m, -1,617.65 m (-23.95%), 163 houses, 0 failed | S2, K3 P2, slope 25°, C0 | `DEL_B/03_RESULTS_TABLES/PRIMARY_RUN_S2_fac_C0_s25_v11/evaluation_summary.json`; `.../C2_ROUTE_SELECTION_ABLATION/c2_ablation_summary.csv` | Verified |
| 20 | C2 vs roads-only reference | 6,755.36 m vs 5,231.54 m, -1,523.82 m (-22.56%) | same run; `houses_roads_only_reference` | `evaluation_summary.json` | Verified (a reference baseline, not the main planner) |
| 19, 20 | C2 ablation | K1/P0 5,147.98 m vs K3/P2 5,137.71 m (-10.27 m, 0.20%); credit 23.79% vs 23.95% | 5 runs, same inputs | `c2_ablation_summary.csv` | Verified |
| 19, 21 | Connectivity | 163/163 houses and 4/4 facilities routed; 162 of 163 houses reach the main road component; 12 road components | primary run | `evaluation_summary.json` (`connectivity`), `DEL_B/00_START_HERE/COMPLETION_GATE.md` | Verified |
| 10-12 | Boundary area | 18.466 km² (computed 18.4661 km², EPSG:32644) | `study_area/damarakunta_boundary.gpkg` | re-measured with geopandas | Verified |
| 11 | Mosaic size | 11,296 x 7,171 px, 3 bands, 0.6 m, EPSG:32644 | `aligned/damarakunta_esri_highres_mosaic_0p6m.tif` | re-measured with rasterio | Verified |
| 11 | Roads | 43 features, 93,496.76 m | `reference/tgrac_road_network.gpkg` | re-measured; 44.70% outside boundary from `README_PROJECT_OVERVIEW.md` | Verified |
| 11-12 | Buildings, parcels, facilities | 278 candidates; 165 footprints; 163 routed; 794 parcels; 4 facilities | `buildings_v8_full.gpkg`, `damarakunta_cadastral_valid.gpkg`, `damarakunta_priority_facilities.gpkg` | re-counted with geopandas; 165/163 from `run_20261029_01/stageA/stageA_checks.txt` | Verified |
| 13, 16 | Grid, planner hash | 432 x 679 cells at 10 m; planner SHA-256 d00ea920...ef70a4 | | rasters re-read; hash from `evaluation`/manifest records | Verified |
| 16 | Library versions | rasterio 1.4.4, geopandas 1.1.4, shapely 2.1.2, numpy 2.2.6, scipy 1.15.3, networkx 3.4.2, etc. | `.venv\Lib\site-packages` | dist-info folder names | Verified (installed versions; scipy and networkx use in the planner not confirmed) |
| 6 | Mini-project: mIoU 53.80%, mDice 68.91% (epoch 4), config list | as supplied by you | LoveDA validation only | `DECISIONS.md` row 2 records 53.80 / 68.91; the config list comes from your message | Provisional: checkpoint metadata "to be confirmed by audit" in `DECISIONS.md` |

## 2. Figures that were left off the slides, and why

| Figure you supplied | Finding | Slide treatment |
|---|---|---|
| 9 served clusters, 1,506.1 m, 68.8% coverage; 8 clusters, 1,356.9 m, 62.5%; independent 1,516.6 m vs 1,506.1 m (10.4 m, 0.69%) | Exist in `Siddipet/Damarakunta/results/planning_experiments/experiments_v1/full1/c1_summary.csv` and `c2_scenarios.csv` (row "gap>50 m"). They come from an **earlier prototype**: 11 gap clusters, slope limit 10°, older planner. Not comparable with the 163-house run. | Not shown as results. Mentioned only as "superseded" in the slide 20 footnote. |
| Independent 6,755.36 m vs "network-aware" 5,231.54 m, -22.56% | **Mislabelled.** 5,231.54 m is the roads-only reference baseline (`houses_roads_only_reference.unique_len_m`). The shared-network planner itself gives **5,137.71 m (-23.95%)**. The old chart `journal_shared_network_length_comparison_v4_1.png` also plots 5.23 km. | Slide 20 shows both rows, labelled correctly. Slides 19 and 23 use 5,137.7 m. The old chart is not used. |
| Stage A: 278 / 165 / 163; S1 101 (71 PLAUSIBLE, 30 REVIEW); S2 62 UNRESOLVED_MERGE; 51 PASS, 9 INFO | Counts 165 / 163 / 101 / 62 and "51 PASS, 9 INFO" confirmed in `stageA_checks.txt`. The 71/30 split was not re-checked. | Only 278/165/163 are shown. |
| 10° run: two start-cell slope failures | Confirmed: `S1_fac_C0_s10` has 2 failures (`TARGET_IN_HARD_CONSTRAINT_CELL_OR_OUTSIDE_GRID`). | Not on slides. |
| "All ten V4 review rows valid, `CONNECTORS_REQUIRE_VISUAL_REVIEW`" | Not re-checked. | Slide 21 only says connectors need visual review. |

## 3. Corrections to your brief

- **DEM source:** your brief says Copernicus DEM. `DATA_SOURCES.md` lists SRTM 1 arc-second, and no script in `scripts/` names either product. The slide says "to be confirmed".
- **WorldCover year:** "2021" comes from `DATA_SOURCES.md` and `README_PROJECT_OVERVIEW.md`. The raster does not store a version.
- **Connectivity:** the 12 road components and the C0002 exception are confirmed. The 151.55 m and 155.24 m distances differ between two diagnostics (`MISSING_ITEMS_SUMMARY.md`), so no distance is on the slides.

## 4. Missing inputs and evidence

1. Supervisor and co-guide names, roll number, academic year: only placeholders exist in the LaTeX report. The title slide shows your name only.
2. State, district and mandal location map: none in the project files. Slide 10 says so rather than drawing one.
3. Imagery provider, capture date and licence (`DAMARAKUNTA_IMAGERY_LICENCE_ENQUIRY_DRAFT.md` not sent).
4. DEM product and licence; WorldCover version.
5. P3 baseline reproduction run (`DEL_B/06_REPRODUCIBILITY/P3_BASELINE_REPRODUCTION/README_RUN_THIS.md`).
6. Mini-project evidence: no training log or checkpoint metadata for the StrongDINOv2Seg run is in this repository, so the config and metrics come only from your message.
7. Literature: the project's own `literature_verification.csv` checked titles, authors and DOIs against Crossref, but findings come from abstracts. Full-text reading is pending. No paper on shared-network optimisation or uncertainty propagation specific to rural road planning was found in the project's literature; slide 8 uses UGD-DLinkNet only as the nearest "uncertainty" item.
8. Stage B C1 report v4 and the 14 planner tests were not re-run today (counts quoted from `EXECUTION_STATUS.md`).
9. No slope/cost map was exported earlier; slide 13 and 17 show a figure rendered from the real rasters (`images/fig_slope_cost.png`).
10. The imagery in the study-area and output maps carries "source/licence to be confirmed" captions; check redistribution rules before the deck leaves the university.
