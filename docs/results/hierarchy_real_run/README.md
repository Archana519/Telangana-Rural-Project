# Real-data multi-level run (2026-11-14)

Command: `python -m src.routing.run_hierarchy --levels 2 3 4 --data real --out docs/results/hierarchy_real_run` (log: `run_log.txt`; omission seeds 11, 12, 13).
Inputs: open data fetched by `src/utils/data_downloader_helper.py` (Copernicus GLO-30 DEM, ESA WorldCover 2021, geoBoundaries, Overture release 2026-10-21.0) plus, for Level 2, the repository's TGRAC roads, 5 facilities, v8 building footprints and 163 Stage B house targets.
Every input is hashed in `../input_manifest.csv`; every number is mapped to its source in `../PROVENANCE_AND_PROOFS.md` (generated and re-checked by `python -m src.evaluation.provenance_audit`).

| Level | Evidence class | Shared unique length | New construction | Independent (new) |
|---|---|---|---|---|
| 2 GP (Damarakunta) | real inputs | 1,743.7 m | 1,743.7 m | 1,782.3 m |
| 3 Mandal (Markook) | **proxy nodes - scalability demonstration** | 5,912.9 m | 5,912.9 m | 5,912.9 m |
| 4 District (Siddipet) | **proxy nodes - scalability demonstration** | 358.7 km | 14.7 km (95.9% of the backbone is existing road) | 19.8 km |

## Read before quoting any number
* Levels 3-4: terminals are interior points of geoBoundaries polygons (`proxy=True`), GP hubs are OSM village points (weight 1); none is a verified HQ/PHC/market/GP location. Do not draw planning conclusions.
* Level 2 routes hamlet hubs, not houses: not comparable with Level 1's house-by-house 5,069 m.
* Costs are ordinal planning units, not rupees. Omission columns are synthetic random omissions of units, not measured detection errors. Nothing is field validated.
* Roads are Overture (OSM-derived) segments, not a PMGSY/TGRAC inventory; the district run uses motorway-tertiary only.

## Figures (`figures/`, 300 dpi PNG; `python -m src.evaluation.plot_hierarchy_figures`)
* `figA_level2_gp_network.png` - Level 2 shared network vs existing roads, hamlet hubs, facilities, local-override comparison (real inputs).
* `figB_penalty_sweep.png` - footprint-penalty trade-off curve, mu in {1, 2, 4, 8, 20, 100} (16 was never run).
* `figC_scalability_levels3_4.png` - Level 3 and Level 4 on **proxy nodes**; Level 4 splits existing-road reuse from new construction.
* `figD_level1_omission.png` - Level 1 (Stage B) omission sensitivity redrawn from `table4_c1_sensitivity.csv` (`python -m src.evaluation.plot_level1_omission`; replaces the original chart with the overlapping legend, U12).
Identical copies are in `paper/figures/`, the files `paper/main.tex` includes.
Level 1 (Stage B) maps and charts are in `DELIVERABLES_DAMARAKUNTA_STAGE_B/02_FINAL_MAPS/` and `03_RESULTS_TABLES/CHARTS/`.
