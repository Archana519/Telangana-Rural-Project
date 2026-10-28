# First-village case study: Damarakunta, Markook Mandal, Siddipet, Telangana

> **Status banner.** All routes are **unverified planning alternatives** computed from model-derived building polygons and a 10 m cost raster. They are not verified roads, not legally approved, not construction-ready, and not field-validated. Routing cost values are **routing cost units, not money**. Weights are ordinal design parameters.

Planner caveat (from `summary.json`): _All outputs are unverified planning alternatives from model-derived building polygons and a 10 m raster; not verified roads, not construction-ready._

## 1. Runs and reproducibility  `COMPUTED`

- Reference run: `run7_regress`  
- Reproduced run: `fv_repro1` (same parameters, rerun)  
- Planner: `plan_network_v2`, CRS EPSG:32644

**Reproducibility check result: PASS**  
_PASS means the reproduced run matches the reference run on the checks listed; it does not validate the planning result._

| check | passed | detail |
|---|---|---|
| summary.inputs hashes equal (reference vs reproduced) | True | 3 hashes equal |
| planner hash of 'access' equals sha256 of file now | True | equal |
| planner hash of 'roads' equals sha256 of file now | True | equal |
| planner hash of 'cost' equals sha256 of file now | True | equal |
| parameters equal (ignoring tag, out_root, no_map) | True | 33 parameters compared |
| plan_comparison.csv identical | True | 3 rows identical (floats rounded to 6 dp) |
| target_table.csv identical | True | 15 rows identical (floats rounded to 6 dp) |
| summary.json['c2_check'] identical (NaN = null) | True | equal |
| summary.json['failed_targets'] identical (NaN = null) | True | equal |
| summary.json['plan_comparison'] identical (NaN = null) | True | equal |
| summary.json['data_check'] identical (NaN = null) | True | equal |
| summary.json['constraints_resolved'] identical (NaN = null) | True | equal |
| network_v2.gpkg layers/geometry/attributes identical | True | constraints_hard: n=86 geometry identical (1 mm), attributes identical; routes_independent: n=13 geometry identical (1 mm), attributes identical; routes_network_aware: n=13 geometry identical (1 mm), attributes identical; routes_straight_line: n=15 geometry identical (1 mm), attributes identical; stageA_alternatives: n=37 geometry identical (1 mm), attributes identical; targets: n=15 geometry identical (1 mm), attributes identical |

## 2. Input inventory and provenance

`COMPUTED` (SHA-256 prefixes; full hashes in `run_log.json`)

| param | path | bytes | sha256 | exists |
|---|---|---|---|---|
| access_gpkg | D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v8_instances\access\access_assessment.gpkg | 765952 | 08e3bc4c6cc0f67d... | True |
| roads | D:\Telangana_Rural_Project\Siddipet\Damarakunta\reference\tgrac_road_network.gpkg | 163840 | 3574defb203f2453... | True |
| cost | D:\Telangana_Rural_Project\Siddipet\Damarakunta\aligned\damarakunta_cost_surface_10m.tif | 814171 | 911ebeb1860aa49f... | True |
| worldcover | D:\Telangana_Rural_Project\Siddipet\Damarakunta\aligned\damarakunta_worldcover_10m.tif | 26258 | 587eb4d652e3e66f... | True |
| blocked | D:\Telangana_Rural_Project\Siddipet\Damarakunta\aligned\damarakunta_prohibited_mask_10m.tif | 8617 | 7330837ba9b55588... | True |
| slope | D:\Telangana_Rural_Project\Siddipet\Damarakunta\aligned\damarakunta_slope_10m.tif | 859864 | 6f6b3c6d26837564... | True |
| buildings | D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v8_instances\buildings_v8_full.gpkg | 1146880 | 0eae82fea8ada939... | True |
| raster | D:\Telangana_Rural_Project\Siddipet\Damarakunta\aligned\damarakunta_esri_highres_mosaic_0p6m.tif | 241258858 | 9013449ce5bd3079... | True |
| v4_script | D:\Telangana_Rural_Project\scripts\reconstruct_damarakunta_routes_v4.py | 24342 | e1cc0c708766fa3f... | True |


| Layer | Label | Note |
|---|---|---|
| Imagery (ESRI 0.6 m mosaic) | UNVERIFIED | No licence/terms file found; use rights not established (cf. DECISIONS #4 for TGRAC). |
| Building polygons (v8 semantic-mask candidates) | MODEL-DERIVED | Output of a semantic model (StrongDINOv2Seg); blobs, some merged; class mapping unverified. |
| Road network (TGRAC) | UNVERIFIED | External reference layer; accuracy not independently checked. |
| Facilities (school compounds, TGRAC health, TGRAC anganwadi) | UNVERIFIED | From named source files; planner flags the sub-centre and anganwadi as UNVERIFIED_FLAGGED. |
| Cost surface / WorldCover / slope / prohibited mask (10 m) | MODEL-DERIVED | Derived rasters; weights are design parameters. |
| Google Open Buildings v3 | REFERENCE ONLY | Model output, not ground truth; not used by the planner in this run. |

## 3. Planner results (reproduced run)  `COMPUTED` on `MODEL-DERIVED` inputs

| plan | targets_routed | targets_total | total_len_m | unique_len_m | shared_len_m | unique_cost | weighted_benefit | facilities_served | cluster_buildings_served | infeasible_routes |
|---|---|---|---|---|---|---|---|---|---|---|
| network_aware | 13 | 15 | 1506.1 | 1506.1 | -0 | 9438.7 | 23.25 | 4 | 14 | 0 |
| independent_least_cost | 13 | 15 | 1516.6 | 1516.6 | -0 | 9456.5 | 23.25 | 4 | 14 | 0 |
| straight_line | 15 | 15 | 1625.7 | 1625.7 | 0 |  | 25.25 | 4 | 16 | 2 |

_Straight-line plan: routes marked infeasible cross hard constraints and must not be counted as served._

### Target table

| target | kind | name | weight | buildings | unresolved_in_cluster | coord_status | euclid_to_road_m | status | failure_reason | mode | attach_to | route_len_m | route_cost | marginal_cost | endpoint_dist_m | connected_to_roads | indep_len_m | straight_len_m | straight_feasible | detour_ratio | connectivity_gain |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| F:36181600902 | FACILITY | Mpps Damarakunta | 3 | 0 | 0 | SOURCE_LAYER_NOT_INDEPENDENTLY_VERIFIED | 11.1 | SERVED |  | stageA_alt1 | ROAD | 16.9 | 40 | 40 | 2.44 | True | 16.9 | 11.1 | True | 1.53 | 1 priority facility |
| F:36181600903 | FACILITY | Zphs Damarakunta | 3 | 0 | 0 | SOURCE_LAYER_NOT_INDEPENDENTLY_VERIFIED | 43.1 | SERVED |  | attach_network | F:36181600902 | 52.3 | 153.4 | 153.4 | 0 | True | 62.7 | 43.1 | True | 1.21 | 1 priority facility |
| F:HEALTH_8734223673 | FACILITY | Sub Centre, Damarakunta | 4 | 0 | 0 | UNVERIFIED_FLAGGED | 62.2 | SERVED |  | attach_network | ROAD | 73.3 | 357.7 | 357.7 | 3.41 | True | 73.3 | 62.2 | True | 1.18 | 1 priority facility |
| F:1702300 | FACILITY | Damarakunt-I | 3 | 0 | 0 | UNVERIFIED_FLAGGED | 121.1 | SERVED |  | attach_network | ROAD | 168.9 | 700 | 700 | 4.71 | True | 168.9 | 121.1 | True | 1.39 | 1 priority facility |
| C3 | CLUSTER | gap cluster (model-derived, unverified) | 1 | 1 | 0 | MODEL_DERIVED | 133.2 | SERVED |  | attach_network | ROAD | 149.2 | 938.2 | 938.2 | 4.72 | True | 149.2 | 133.2 | True | 1.12 | 1 model-derived building polygons |
| C7 | CLUSTER | gap cluster (model-derived, unverified) | 1 | 1 | 0 | MODEL_DERIVED | 107 | SERVED |  | attach_network | ROAD | 118.3 | 473.9 | 474 | 1.47 | True | 118.3 | 107 | True | 1.11 | 1 model-derived building polygons |
| C11 | CLUSTER | gap cluster (model-derived, unverified) | 1 | 1 | 1 | MODEL_DERIVED | 200 | SERVED |  | attach_network | ROAD | 212.8 | 1531.3 | 1531.3 | 5.13 | True | 212.8 | 200 | True | 1.06 | 1 model-derived building polygons |
| C12 | CLUSTER | gap cluster (model-derived, unverified) | 1 | 1 | 0 | MODEL_DERIVED | 147.8 | FAILED | TARGET_IN_HARD_CONSTRAINT_CELL_OR_OUTSIDE_GRID |  |  |  |  |  |  | False |  | 147.8 | False |  | 1 model-derived building polygons |
| C13 | CLUSTER | gap cluster (model-derived, unverified) | 1 | 1 | 0 | MODEL_DERIVED | 161.3 | FAILED | TARGET_IN_HARD_CONSTRAINT_CELL_OR_OUTSIDE_GRID |  |  |  |  |  |  | False |  | 161.3 | False |  | 1 model-derived building polygons |
| C14 | CLUSTER | gap cluster (model-derived, unverified) | 1 | 1 | 0 | MODEL_DERIVED | 100 | SERVED |  | attach_network | ROAD | 109.4 | 933 | 933.1 | 2.39 | True | 109.4 | 100 | True | 1.09 | 1 model-derived building polygons |
| C21 | CLUSTER | gap cluster (model-derived, unverified) | 1 | 1 | 0 | MODEL_DERIVED | 183.4 | SERVED |  | attach_network | ROAD | 190.2 | 1145.2 | 1145 | 4.35 | True | 190.2 | 183.4 | True | 1.04 | 1 model-derived building polygons |
| C22 | CLUSTER | gap cluster (model-derived, unverified) | 1 | 1 | 0 | MODEL_DERIVED | 125.7 | SERVED |  | attach_network | ROAD | 130.9 | 1076.6 | 1076.5 | 5.83 | True | 130.9 | 125.7 | True | 1.04 | 1 model-derived building polygons |
| C23 | CLUSTER | gap cluster (model-derived, unverified) | 2.25 | 6 | 4 | MODEL_DERIVED | 96.9 | SERVED |  | attach_network | ROAD | 136.4 | 679.4 | 679.4 | 4.58 | True | 136.4 | 96.9 | True | 1.41 | 6 model-derived building polygons |
| C29 | CLUSTER | gap cluster (model-derived, unverified) | 1 | 1 | 0 | MODEL_DERIVED | 67 | SERVED |  | attach_network | ROAD | 70.9 | 585.4 | 585.5 | 1.73 | True | 70.9 | 67 | True | 1.06 | 1 model-derived building polygons |
| C33 | CLUSTER | gap cluster (model-derived, unverified) | 1 | 1 | 0 | MODEL_DERIVED | 65.9 | SERVED |  | attach_network | ROAD | 76.7 | 824.6 | 824.7 | 2.79 | True | 76.7 | 65.9 | True | 1.16 | 1 model-derived building polygons |

### Network-attachment (C2) check

- Targets attached to another selected route: ['F:36181600903']  
- Targets whose route differs from the independent plan: ['F:36181600903']  
- Unique length reduction: 10.5 m (0.69 %)  
- Re-routes changed: 0

_This is the effect on THIS target set only; the number of changed routes is stated above, not extrapolated._

### Data check recorded by the planner

- Cost raster invalid share: 0.3748636338842524  
- Cells over slope limit with valid cost: 2317  
- Road cells: {'total': 8061, 'passable': 6430, 'dropped_impassable': 1631}  
- Targets: {'facilities': 4, 'clusters': 11}

## 4. Failed targets  `COMPUTED` from records and masks

### C12
- Planner reason: `TARGET_IN_HARD_CONSTRAINT_CELL_OR_OUTSIDE_GRID`  
- Records found: [{'gpkg': 'D:\\Telangana_Rural_Project\\Siddipet\\Damarakunta\\results\\planning_experiments\\network_v2\\fv_repro1\\network_v2.gpkg', 'layer': 'targets', 'column': 'id', 'n_rows': 1}, {'gpkg': 'D:\\Telangana_Rural_Project\\Siddipet\\Damarakunta\\results\\planning_experiments\\network_v2\\fv_repro1\\network_v2.gpkg', 'layer': 'routes_straight_line', 'column': 'target', 'n_rows': 1}]  
- **Finding:** CONSISTENT WITH the planner failure reason: [('slope > 10.0 deg',)] at the tested point(s). Geometry source: targets.id in network_v2.gpkg. This layer looks like the planner's own target layer.

| point | x | y | flags | slope_deg | worldcover | prohibited | dist_to_valid_cell_m |
|---|---|---|---|---|---|---|---|
| point | 259389.69 | 1960017.79 | slope > 10.0 deg | 10.3486948 | 40 | 0 | 6 |

### C13
- Planner reason: `TARGET_IN_HARD_CONSTRAINT_CELL_OR_OUTSIDE_GRID`  
- Records found: [{'gpkg': 'D:\\Telangana_Rural_Project\\Siddipet\\Damarakunta\\results\\planning_experiments\\network_v2\\fv_repro1\\network_v2.gpkg', 'layer': 'targets', 'column': 'id', 'n_rows': 1}, {'gpkg': 'D:\\Telangana_Rural_Project\\Siddipet\\Damarakunta\\results\\planning_experiments\\network_v2\\fv_repro1\\network_v2.gpkg', 'layer': 'routes_straight_line', 'column': 'target', 'n_rows': 1}]  
- **Finding:** CONSISTENT WITH the planner failure reason: [('cost invalid (nodata or <= 0)', 'prohibited mask > 0')] at the tested point(s). Geometry source: targets.id in network_v2.gpkg. This layer looks like the planner's own target layer.

| point | x | y | flags | slope_deg | worldcover | prohibited | dist_to_valid_cell_m |
|---|---|---|---|---|---|---|---|
| point | 259398.69 | 1960050.79 | cost invalid (nodata or <= 0); prohibited mask > 0 | -9999 | 0 | 1 | 17.3 |

## 5. Access gain recomputed for the same runs  `COMPUTED` (proximity, auxiliary)

_Source: `D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\first_village_runs\fv_20261024_193950\access_gain\ag`. Runs included: ['fv_repro1', 'run7_regress']. The statistic is a distance to a road or proposed route; it is NOT proof of physical or legal access._

| run | scenario | building_set | set_role | threshold_m | n_polygons | baseline_n_within | proposed_n_within | baseline_pct | proposed_pct | abs_change_n | pp_change |
|---|---|---|---|---|---|---|---|---|---|---|---|
| run7_regress | roads_plus_network_aware_routes | all_candidate_polygons | population | 25 | 163 | 80 | 95 | 49.08 | 58.282 | 15 | 9.202 |
| run7_regress | roads_plus_network_aware_routes | all_candidate_polygons | population | 50 | 163 | 103 | 118 | 63.19 | 72.393 | 15 | 9.202 |
| run7_regress | roads_plus_network_aware_routes | all_candidate_polygons | population | 100 | 163 | 136 | 146 | 83.436 | 89.571 | 10 | 6.135 |
| run7_regress | roads_plus_network_aware_routes | polygon_gap_flag_true | polygon_level_gap | 25 | 60 | 0 | 11 | 0 | 18.333 | 11 | 18.333 |
| run7_regress | roads_plus_network_aware_routes | polygon_gap_flag_true | polygon_level_gap | 50 | 60 | 0 | 15 | 0 | 25 | 15 | 25 |
| run7_regress | roads_plus_network_aware_routes | polygon_gap_flag_true | polygon_level_gap | 100 | 60 | 33 | 43 | 55 | 71.667 | 10 | 16.667 |
| run7_regress | roads_plus_network_aware_routes | gap_cluster_polygons | cluster_level_gap | 25 | 16 | 0 | 10 | 0 | 62.5 | 10 | 62.5 |
| run7_regress | roads_plus_network_aware_routes | gap_cluster_polygons | cluster_level_gap | 50 | 16 | 0 | 12 | 0 | 75 | 12 | 75 |
| run7_regress | roads_plus_network_aware_routes | gap_cluster_polygons | cluster_level_gap | 100 | 16 | 5 | 14 | 31.25 | 87.5 | 9 | 56.25 |
| run7_regress | roads_plus_network_aware_routes | settlement_interior_screening | screening | 25 | 43 | 0 | 1 | 0 | 2.326 | 1 | 2.326 |
| run7_regress | roads_plus_network_aware_routes | settlement_interior_screening | screening | 50 | 43 | 0 | 3 | 0 | 6.977 | 3 | 6.977 |
| run7_regress | roads_plus_network_aware_routes | settlement_interior_screening | screening | 100 | 43 | 27 | 28 | 62.791 | 65.116 | 1 | 2.326 |
| fv_repro1 | roads_plus_network_aware_routes | all_candidate_polygons | population | 25 | 163 | 80 | 95 | 49.08 | 58.282 | 15 | 9.202 |
| fv_repro1 | roads_plus_network_aware_routes | all_candidate_polygons | population | 50 | 163 | 103 | 118 | 63.19 | 72.393 | 15 | 9.202 |
| fv_repro1 | roads_plus_network_aware_routes | all_candidate_polygons | population | 100 | 163 | 136 | 146 | 83.436 | 89.571 | 10 | 6.135 |
| fv_repro1 | roads_plus_network_aware_routes | polygon_gap_flag_true | polygon_level_gap | 25 | 60 | 0 | 11 | 0 | 18.333 | 11 | 18.333 |
| fv_repro1 | roads_plus_network_aware_routes | polygon_gap_flag_true | polygon_level_gap | 50 | 60 | 0 | 15 | 0 | 25 | 15 | 25 |
| fv_repro1 | roads_plus_network_aware_routes | polygon_gap_flag_true | polygon_level_gap | 100 | 60 | 33 | 43 | 55 | 71.667 | 10 | 16.667 |
| fv_repro1 | roads_plus_network_aware_routes | gap_cluster_polygons | cluster_level_gap | 25 | 16 | 0 | 10 | 0 | 62.5 | 10 | 62.5 |
| fv_repro1 | roads_plus_network_aware_routes | gap_cluster_polygons | cluster_level_gap | 50 | 16 | 0 | 12 | 0 | 75 | 12 | 75 |
| fv_repro1 | roads_plus_network_aware_routes | gap_cluster_polygons | cluster_level_gap | 100 | 16 | 5 | 14 | 31.25 | 87.5 | 9 | 56.25 |
| fv_repro1 | roads_plus_network_aware_routes | settlement_interior_screening | screening | 25 | 43 | 0 | 1 | 0 | 2.326 | 1 | 2.326 |
| fv_repro1 | roads_plus_network_aware_routes | settlement_interior_screening | screening | 50 | 43 | 0 | 3 | 0 | 6.977 | 3 | 6.977 |
| fv_repro1 | roads_plus_network_aware_routes | settlement_interior_screening | screening | 100 | 43 | 27 | 28 | 62.791 | 65.116 | 1 | 2.326 |

**Access-gain agreement between reference and reproduced run:** identical (60 vs 60 rows).

### Facilities

| run | facility_id | facility_name | facility_type | target_id | dist_base_m | dist_stored_m | dist_na_m | dist_ic_m | within_25_base | within_25_na | within_25_ic | within_50_base | within_50_na | within_50_ic | within_100_base | within_100_na | within_100_ic | planner_status | failure_reason | route_len_m |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| run7_regress | 36181600902 | Mpps Damarakunta | School | F:36181600902 | 11.05 | 11.1 | 0 | 0 | True | True | True | True | True | True | True | True | True | SERVED |  | 16.9 |
| run7_regress | 36181600903 | Zphs Damarakunta | School | F:36181600903 | 43.139 | 43.1 | 0 | 0 | False | True | True | True | True | True | True | True | True | SERVED |  | 52.3 |
| run7_regress | HEALTH_8734223673 | Sub Centre, Damarakunta | Healthcare | F:HEALTH_8734223673 | 62.202 | 62.2 | 0 | 0 | False | True | True | False | True | True | True | True | True | SERVED |  | 73.3 |
| run7_regress | 1702300 | Damarakunt-I | Anganwadi | F:1702300 | 121.11 | 121.1 | 0 | 0 | False | True | True | False | True | True | False | True | True | SERVED |  | 168.9 |
| fv_repro1 | 36181600902 | Mpps Damarakunta | School | F:36181600902 | 11.05 | 11.1 | 0 | 0 | True | True | True | True | True | True | True | True | True | SERVED |  | 16.9 |
| fv_repro1 | 36181600903 | Zphs Damarakunta | School | F:36181600903 | 43.139 | 43.1 | 0 | 0 | False | True | True | True | True | True | True | True | True | SERVED |  | 52.3 |
| fv_repro1 | HEALTH_8734223673 | Sub Centre, Damarakunta | Healthcare | F:HEALTH_8734223673 | 62.202 | 62.2 | 0 | 0 | False | True | True | False | True | True | True | True | True | SERVED |  | 73.3 |
| fv_repro1 | 1702300 | Damarakunt-I | Anganwadi | F:1702300 | 121.11 | 121.1 | 0 | 0 | False | True | True | False | True | True | False | True | True | SERVED |  | 168.9 |

## 6. Earlier C1/C2 experiments (read only, NOT recomputed here)

_Source folder `D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\planning_experiments\experiments_v1\full1` (files as produced earlier). C1 perturbations are synthetic and labelled so._

### c1_summary.csv

| family | level | runs | clusters_mean | served_mean | served_min | served_max | unique_len_mean | unique_len_min | unique_len_max | coverage_mean | coverage_min | coverage_max | overlap_mean | overlap_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| area_threshold | 5 | 1 | 11 | 9 | 9 | 9 | 1506.1 | 1506.1 | 1506.1 | 0.688 | 0.688 | 0.688 | 1 | 1 |
| area_threshold | 15 | 1 | 11 | 9 | 9 | 9 | 1506.1 | 1506.1 | 1506.1 | 0.688 | 0.688 | 0.688 | 1 | 1 |
| area_threshold | 20 | 1 | 10 | 8 | 8 | 8 | 1356.9 | 1356.9 | 1356.9 | 0.625 | 0.625 | 0.625 | 1 | 1 |
| area_threshold | 30 | 1 | 10 | 8 | 8 | 8 | 1356.9 | 1356.9 | 1356.9 | 0.625 | 0.625 | 0.625 | 1 | 1 |
| area_threshold | 50 | 1 | 9 | 8 | 8 | 8 | 1356.9 | 1356.9 | 1356.9 | 0.625 | 0.625 | 0.625 | 1 | 1 |
| baseline | 0 | 1 | 11 | 9 | 9 | 9 | 1506.1 | 1506.1 | 1506.1 | 0.688 | 0.688 | 0.688 | 1 | 1 |
| inflation | 1 | 1 | 11 | 9 | 9 | 9 | 1506 | 1506 | 1506 | 0.688 | 0.688 | 0.688 | 1 | 1 |
| inflation | 2 | 1 | 9 | 8 | 8 | 8 | 1388.3 | 1388.3 | 1388.3 | 0.625 | 0.625 | 0.625 | 1 | 1 |
| inflation | 4 | 1 | 9 | 8 | 8 | 8 | 1419.8 | 1419.8 | 1419.8 | 0.625 | 0.625 | 0.625 | 0.967 | 0.967 |
| merge_closing | 2 | 1 | 11 | 9 | 9 | 9 | 1513 | 1513 | 1513 | 0.75 | 0.75 | 0.75 | 0.905 | 0.905 |
| merge_closing | 4 | 1 | 11 | 9 | 9 | 9 | 1531.9 | 1531.9 | 1531.9 | 0.875 | 0.875 | 0.875 | 0.894 | 0.894 |
| random_omission | 0.1 | 5 | 12 | 10.2 | 10 | 11 | 1574.86 | 1473.2 | 1694 | 0.662 | 0.625 | 0.688 | 0.921 | 0.888 |
| random_omission | 0.2 | 5 | 11.8 | 10 | 9 | 11 | 1627 | 1497.6 | 1820.5 | 0.662 | 0.625 | 0.75 | 0.851 | 0.728 |
| random_omission | 0.3 | 5 | 11.4 | 9.8 | 8 | 12 | 1507.98 | 1212.8 | 1731.6 | 0.625 | 0.562 | 0.812 | 0.779 | 0.643 |
| systematic_omission:farthest_from_road | 0.1 | 1 | 8 | 8 | 8 | 8 | 1212.9 | 1212.9 | 1212.9 | 0.562 | 0.562 | 0.562 | 0.91 | 0.91 |
| systematic_omission:farthest_from_road | 0.2 | 1 | 4 | 4 | 4 | 4 | 705.1 | 705.1 | 705.1 | 0.312 | 0.312 | 0.312 | 0.844 | 0.844 |
| systematic_omission:farthest_from_road | 0.3 | 1 | 3 | 3 | 3 | 3 | 534.6 | 534.6 | 534.6 | 0.125 | 0.125 | 0.125 | 0.883 | 0.883 |
| systematic_omission:nearest_to_road | 0.1 | 1 | 11 | 9 | 9 | 9 | 1506.1 | 1506.1 | 1506.1 | 0.688 | 0.688 | 0.688 | 1 | 1 |
| systematic_omission:nearest_to_road | 0.2 | 1 | 11 | 9 | 9 | 9 | 1506.1 | 1506.1 | 1506.1 | 0.688 | 0.688 | 0.688 | 1 | 1 |
| systematic_omission:nearest_to_road | 0.3 | 1 | 11 | 9 | 9 | 9 | 1492 | 1492 | 1492 | 0.688 | 0.688 | 0.688 | 1 | 1 |
| systematic_omission:smallest | 0.1 | 1 | 9 | 8 | 8 | 8 | 1356.9 | 1356.9 | 1356.9 | 0.625 | 0.625 | 0.625 | 1 | 1 |
| systematic_omission:smallest | 0.2 | 1 | 10 | 9 | 9 | 9 | 1466.7 | 1466.7 | 1466.7 | 0.625 | 0.625 | 0.625 | 0.925 | 0.925 |
| systematic_omission:smallest | 0.3 | 1 | 7 | 7 | 7 | 7 | 1311 | 1311 | 1311 | 0.5 | 0.5 | 0.5 | 0.893 | 0.893 |

### c2_scenarios.csv

| target_set | clusters | targets | served_na | served_independent | failed | ic_total_len_m | ic_unique_len_m | ic_overlap_m | na_total_len_m | na_unique_len_m | unique_len_reduction_m | unique_len_reduction_pct | unique_cost_na | unique_cost_ic | attached_targets | attached_ids | hard_violating_selected | seconds |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gap>0 m | 31 | 35 | 33 | 33 | 2 | 2238.5 | 2238.5 | -0 | 2214 | 2214 | 24.6 | 1.1 | 14279.4 | 14357.7 | 2 | F:36181600903;C22 | 0 | 0.7 |
| gap>25 m | 16 | 20 | 18 | 18 | 2 | 1832 | 1832 | -0 | 1821.5 | 1821.5 | 10.4 | 0.57 | 11541.3 | 11559.1 | 1 | F:36181600903 | 0 | 0.4 |
| gap>50 m | 11 | 15 | 13 | 13 | 2 | 1516.6 | 1516.6 | -0 | 1506.1 | 1506.1 | 10.4 | 0.69 | 9438.7 | 9456.5 | 1 | F:36181600903 | 0 | 0.3 |
| gap>100 m | 6 | 10 | 8 | 8 | 2 | 1004.9 | 1004.9 | 0 | 994.5 | 994.5 | 10.4 | 1.04 | 5942.3 | 5960.1 | 1 | F:36181600903 | 0 | 0.1 |
| random 50% of gap>50 m clusters, seed 0 | 6 | 10 | 9 | 9 | 1 | 952.7 | 952.7 | -0 | 942.3 | 942.3 | 10.4 | 1.1 | 5307.2 | 5325 | 1 | F:36181600903 | 0 | 0.1 |
| random 50% of gap>50 m clusters, seed 1 | 6 | 10 | 9 | 9 | 1 | 1054.4 | 1054.4 | -0 | 1043.9 | 1043.9 | 10.4 | 0.99 | 6384.1 | 6401.9 | 1 | F:36181600903 | 0 | 0.1 |
| random 50% of gap>50 m clusters, seed 2 | 6 | 10 | 9 | 9 | 1 | 1008.8 | 1008.8 | 0 | 998.3 | 998.3 | 10.4 | 1.04 | 6017 | 6034.8 | 1 | F:36181600903 | 0 | 0.1 |
| random 50% of gap>50 m clusters, seed 3 | 6 | 10 | 9 | 9 | 1 | 1023.4 | 1023.5 | -0 | 1013 | 1013 | 10.4 | 1.02 | 5919.8 | 5937.6 | 1 | F:36181600903 | 0 | 0.1 |
| random 50% of gap>50 m clusters, seed 4 | 6 | 10 | 9 | 9 | 1 | 867.8 | 867.8 | -0 | 857.3 | 857.3 | 10.4 | 1.2 | 5149.8 | 5167.6 | 1 | F:36181600903 | 0 | 0.1 |
| random 75% of gap>50 m clusters, seed 0 | 8 | 12 | 11 | 11 | 1 | 1267.4 | 1267.4 | -0 | 1257 | 1257 | 10.4 | 0.82 | 7888.2 | 7906 | 1 | F:36181600903 | 0 | 0.2 |
| random 75% of gap>50 m clusters, seed 1 | 8 | 12 | 10 | 10 | 2 | 977.2 | 977.2 | -0 | 966.7 | 966.7 | 10.4 | 1.07 | 6082.8 | 6100.6 | 1 | F:36181600903 | 0 | 0.1 |
| random 75% of gap>50 m clusters, seed 2 | 8 | 12 | 11 | 11 | 1 | 1258 | 1258 | 0 | 1247.5 | 1247.5 | 10.4 | 0.83 | 7567.5 | 7585.3 | 1 | F:36181600903 | 0 | 0.2 |
| random 75% of gap>50 m clusters, seed 3 | 8 | 12 | 10 | 10 | 2 | 1259.6 | 1259.6 | 0 | 1249.1 | 1249.1 | 10.4 | 0.83 | 7095.7 | 7113.4 | 1 | F:36181600903 | 0 | 0.2 |
| random 75% of gap>50 m clusters, seed 4 | 8 | 12 | 11 | 11 | 1 | 1369 | 1369 | -0 | 1358.5 | 1358.5 | 10.4 | 0.76 | 8028.6 | 8046.4 | 1 | F:36181600903 | 0 | 0.2 |

### c2_ablation.csv

| target_set | variant | targets | served | independent_unique_len_m | variant_unique_len_m | reduction_vs_independent_m | reduction_pct | attached_targets | seconds |
|---|---|---|---|---|---|---|---|---|---|
| gap>0 m | stageA_credit_only (no fresh attachment, no re-route) | 35 | 33 | 2238.5 | 2238.5 | 0 | 0 | 0 | 0.1 |
| gap>0 m | attachment, no re-route pass | 35 | 33 | 2238.5 | 2214 | 24.6 | 1.1 | 2 | 0.7 |
| gap>0 m | full (attachment + re-route) | 35 | 33 | 2238.5 | 2214 | 24.6 | 1.1 | 2 | 0.8 |
| gap>0 m | full with k=1 alternative | 35 | 33 | 2238.5 | 2214 | 24.6 | 1.1 | 2 | 0.7 |
| gap>50 m | stageA_credit_only (no fresh attachment, no re-route) | 15 | 13 | 1516.6 | 1516.6 | 0 | 0 | 0 | 0.1 |
| gap>50 m | attachment, no re-route pass | 15 | 13 | 1516.6 | 1506.1 | 10.4 | 0.69 | 1 | 0.3 |
| gap>50 m | full (attachment + re-route) | 15 | 13 | 1516.6 | 1506.1 | 10.4 | 0.69 | 1 | 0.3 |
| gap>50 m | full with k=1 alternative | 15 | 13 | 1516.6 | 1506.1 | 10.4 | 0.69 | 1 | 0.2 |

## 7. Building-count context  `COMPUTED`

| Quantity | Value |
|---|---|
| v8 candidate polygons in the layer | 278 |
| of which inside_village is true | 165 |
| v8 quality_class = PLAUSIBLE | 135 |
| v8 quality_class = UNRESOLVED_MERGE | 84 |
| v8 quality_class = REVIEW | 59 |
| polygons in the access analysis (all_candidate_polygons) | 163 |
| Google Open Buildings v3 polygons in the study area (reference only) | 1537 |


## 8. Limitations and unverified items

- `LIMITATION` The planner's access analysis uses the polygons listed above. That count is **not** the confirmed number of buildings in the village; model polygons can merge or miss roofs, and `est_roofs` is a proxy, not a house count.
- `LIMITATION` Google Open Buildings footprints are **reference data, not ground truth**, and were not used by the planner in this run.
- `LIMITATION` Routing costs are **routing cost units**, not monetary construction costs. No monetary estimate is made.
- `LIMITATION` A building or facility being within 50 m of a road or proposed route is a **proximity statistic**, not proof of access, passability or legal access.
- `LIMITATION` Facility source files (school compounds, TGRAC health, TGRAC anganwadi) are **not independently verified**; the sub-centre and anganwadi are flagged unverified by the planner.
- `LIMITATION` The **imagery licence is unverified**.
- `LIMITATION` No field validation, construction readiness, land ownership, road width or passability is claimed.
- `LIMITATION` The segmentation checkpoint was validated on LoveDA only; its class mapping for this village is unverified.
- `LIMITATION` Whether Google footprints are displaced relative to the imagery is **unresolved** (study parked).
- `LIMITATION` The straight-line baseline ignores hard constraints; its infeasible routes are not served targets.
- `LIMITATION` Results describe this target set in this village only; no generalisation to other villages is made.

## 9. How to reproduce

```
.venv\Scripts\python.exe scripts\run_first_village.py --dry-run
.venv\Scripts\python.exe scripts\run_first_village.py
```
Run log, commands, exit codes and SHA-256 hashes: `D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\first_village_runs\fv_20261024_193950\run_log.json`
