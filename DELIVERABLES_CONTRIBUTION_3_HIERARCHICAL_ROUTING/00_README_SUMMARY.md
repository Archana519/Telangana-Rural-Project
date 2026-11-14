# Contribution 3 - hierarchical multi-scale routing: deliverables package

Case study: scaling cost-surface-driven shared road planning from the village (Damarakunta, Level 1, Stage B) to the Gram Panchayat (Level 2), Markook mandal (Level 3) and Siddipet district (Level 4), Telangana.
Planning results on 10 m (Level 2), 30 m (Level 3) and 250 m / 30 m coarse-to-fine (Level 4) grids, EPSG:32644. Routes are unverified planning alternatives, not roads. Costs are ordinal planning units, not rupees.
No field validation, legal access, ownership, drainage, road width or construction cost is established. **Level 2 and the mu sweep use real inputs. Levels 3 and 4 are a computational scalability demonstration on PROXY nodes** (polygon interior points and OSM village points, not verified HQ, PHC, market or Gram Panchayat locations): no planning conclusion may be drawn from them.
`DELIVERABLES_DAMARAKUNTA_STAGE_B/` (Level 1) is untouched by this package.

| Folder | Content |
|---|---|
| 00_README_SUMMARY.md, MANIFEST.csv | this file; SHA-256 of every file in folders 00-03 and 05 |
| 01_ARCHITECTURE | architecture and workflow diagrams, data and process flow |
| 02_FINAL_MAPS | four 300 dpi maps with land-cover context, legend, scale bar and north arrow |
| 03_RESULTS_TABLES | CSV, Markdown and Excel tables; `CHARTS/` (two 300 dpi charts) |
| 04_PROVENANCE_AND_AUDIT | snapshot copies of the provenance report, audit JSON, input manifest, DEM comparison, sweep and decisions |
| 05_LIMITATIONS_AND_OPEN_ISSUES | real vs proxy, what needs the owner's data |

## Headline metrics (all read from `docs/results/`)

| Level | Evidence | Nodes | Shared unique length | New construction | Independent (new) | Saving on new construction |
|---|---|---|---|---|---|---|
| 1 Village (Stage B, recorded) | real | 163 houses (+5 facilities) | 5,069.0 m | 5,069.0 m | 6,753.1 m | 24.9 % |
| 2 Gram Panchayat (Damarakunta) | real | 18 hamlet hubs + 5 facilities | 1,743.7 m | 1,743.7 m | 1,782.3 m | 2.2 % |
| 3 Mandal (Markook) | PROXY | 14 village points + proxy HQ | 5.91 km | 5.91 km | 5.91 km | 0.0 % |
| 4 District (Siddipet) | PROXY | 22 proxy terminals -> proxy district HQ | 358.7 km | 14.7 km | 19.8 km | 25.9 % |

* **Level 2 override:** lifting the footprint penalty within 20 m of an amenity shortens facility routes by 42.4 m in total, lowers facility route cost by 33-67 %, and changes 0 other routes.
* **mu sweep (owner sign-off on mu = 4):** mu = 4 removes 89.0 % of route length inside footprints (109.1 m -> 12.0 m) for +5.2 % network length; the swept set is {1, 2, 4, 8, 20, 100} (16 was not run).
* **Level 4:** 95.9 % of the 358.7 km backbone is existing road; only 14.7 km is new construction.
* **Omission scenarios** (random removal of 10 / 20 % of units, seeds 11-13) are synthetic, not measured detection errors; see `03_RESULTS_TABLES/T4_omission_sensitivity_levels2_4.csv`.

## Data sources
ESA WorldCover 10 m v200 2021 (CC BY 4.0); Copernicus GLO-30 DEM (Stage B used SRTM 1 arc-second: difference quantified in `04_PROVENANCE_AND_AUDIT/U08_dem_comparison.json`, RMSE 2.3 m, effect on Level 2 length 1.0 %);
geoBoundaries gbOpen IND ADM2/ADM3 (CC BY 4.0; 23 mandals as released); Overture Maps release 2026-10-21.0 (OSM-derived, ODbL); TGRAC roads, facilities and boundary, v8 building footprints and the 163 Stage B house targets (Level 2). Hashes: `04_PROVENANCE_AND_AUDIT/input_manifest.csv`.

## Deliverable files
* `01_ARCHITECTURE/ARCHITECTURE_DIAGRAM.png`, `WORKFLOW_DIAGRAM.png`, `DATA_AND_PROCESS_FLOW.md`
* `02_FINAL_MAPS/map1_level2_damarakunta_gp_network.png`, `map2_level2_facility_override_zooms.png`, `map3_level3_markook_mandal_network.png`, `map4_level4_siddipet_district_backbone.png`
* `03_RESULTS_TABLES/T1_level2_gp_metrics.csv`, `T1b_level2_facility_override.csv`, `T2_mu_penalty_sensitivity.csv`, `T3_levels3_4_scalability.csv`, `T4_omission_sensitivity_levels2_4.csv`, `contribution3_summary_tables.md`, `contribution3_summary_tables.xlsx`
* `03_RESULTS_TABLES/CHARTS/chart1_mu_penalty_tradeoff.png`, `chart2_multiscale_network_comparison.png`
* `04_PROVENANCE_AND_AUDIT/` PROVENANCE_AND_PROOFS.md, provenance_audit.json, input_manifest.csv, U08_dem_comparison.json, U02_penalty_sweep_gp.csv, DECISIONS.md, REPRODUCE.md, STAGE_B_UNTOUCHED.txt
* GeoPackages and per-level CSV/JSON: `docs/results/hierarchy_real_run/` (kept in place; not duplicated here)

## Audit status (snapshot at build time)
189 provenance checks in the `provenance_audit.json` copy: 175 PASS, 0 FAIL, the rest are values recorded only in documents (Stage B git-ignored rasters and run outputs). The audit also checks this package (required files, `MANIFEST.csv` hashes, README numbers, and that Stage B is unchanged); re-run it for current counts: see `04_PROVENANCE_AND_AUDIT/REPRODUCE.md`.
Run everything again with `python -m src.evaluation.build_contribution3_deliverables` after the pipeline (see REPRODUCE.md).
