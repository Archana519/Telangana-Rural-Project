# Baseline versus proposed: comparison tables

Source: `D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\run_20261102_141136\stageB`. Lengths are metres on a 10 m planning grid; costs are ordinal planning units. The x4 and x1 configurations are kept apart, and each uses its own baselines. Omit/add runs are synthetic sensitivity probes, not measured detector error. Network results are planning alternatives, not verified roads.

## Table 1. Unique road length: independent routes versus shared network

| configuration   |   houses | method                                                    |   total_len_m |   unique_len_m |   duplicated_len_m |   reduction_vs_independent_unique_m |   reduction_vs_independent_unique_pct |   routes_crossing_other_footprints |   len_in_other_footprints_m |
|:----------------|---------:|:----------------------------------------------------------|--------------:|---------------:|-------------------:|------------------------------------:|--------------------------------------:|-----------------------------------:|----------------------------:|
| x4 (primary)    |      163 | Straight line (no terrain, 2 targets infeasible)          |        8092.3 |                |                    |                                     |                                       |                                 60 |                      1453.2 |
| x4 (primary)    |      163 | Independent least-cost routes to the roads                |       10045.4 |         6753.1 |             3292.3 |                                 0   |                                   0   |                                 46 |                       328.3 |
| x4 (primary)    |      163 | Length-only control (shortest distance, same constraints) |        9166.3 |         6979.8 |             2186.5 |                              -226.7 |                                  -3.4 |                                 64 |                      1615.8 |
| x4 (primary)    |      163 | Roads-only shared reference (houses attach to roads only) |        5229.3 |         5229.3 |                0   |                              1523.8 |                                  22.6 |                                 29 |                       216.1 |
| x4 (primary)    |      163 | Two-stage network-aware plan (proposed)                   |        5069   |         5069   |                0   |                              1684.1 |                                  24.9 |                                 28 |                       209.1 |
| x4 (primary)    |      163 | Facilities (5), network-aware                             |         249.3 |          249.3 |                    |                                     |                                       |                                    |                             |
| x4 (primary)    |      163 | Houses + facilities, network-aware (combined unique)      |        5318.4 |         5318.3 |                    |                              1626.3 |                                  23.4 |                                    |                             |
| x1 (P3 control) |      163 | Straight line (no terrain, 2 targets infeasible)          |        8092.3 |                |                    |                                     |                                       |                                 60 |                      1453.2 |
| x1 (P3 control) |      163 | Independent least-cost routes to the roads                |        9595.9 |         6921.3 |             2674.6 |                                 0   |                                   0   |                                 63 |                      1423.1 |
| x1 (P3 control) |      163 | Length-only control (shortest distance, same constraints) |        9166.3 |         6979.8 |             2186.5 |                               -58.4 |                                  -0.8 |                                 64 |                      1615.8 |
| x1 (P3 control) |      163 | Roads-only shared reference (houses attach to roads only) |        4816.7 |         4816.7 |                0   |                              2104.6 |                                  30.4 |                                 60 |                       711.4 |
| x1 (P3 control) |      163 | Two-stage network-aware plan (proposed)                   |        4705.5 |         4705.4 |                0   |                              2215.9 |                                  32   |                                 56 |                       660.1 |
| x1 (P3 control) |      163 | Facilities (5), network-aware                             |         235.2 |          235.2 |                    |                                     |                                       |                                    |                             |
| x1 (P3 control) |      163 | Houses + facilities, network-aware (combined unique)      |        4940.7 |         4940.6 |                    |                              2147.9 |                                  30.3 |                                    |                             |

Unique length counts a grid edge once. The independent routes duplicate edges that several houses share (duplicated length); the network-aware plan lets a route end on another route or road, so almost no grid edge is used twice.

## Table 2. C2 ablation (primary x4 configuration)

| run                       |   alternatives_per_target_K |   leaf_reroute_passes |   unique_len_m |   total_len_m |   saving_vs_independent_pct |
|:--------------------------|----------------------------:|----------------------:|---------------:|--------------:|----------------------------:|
| S2_fac_C0_s25_final_K1_P0 |                           1 |                     0 |        5079.27 |       5079.32 |                      24.786 |
| S2_fac_C0_s25_final_K1_P2 |                           1 |                     2 |        5069    |       5069.04 |                      24.938 |
| S2_fac_C0_s25_final_K3_P0 |                           3 |                     0 |        5079.27 |       5079.32 |                      24.786 |
| S2_fac_C0_s25_final_K3_P2 |                           3 |                     2 |        5069    |       5069.04 |                      24.938 |
| S2_fac_C0_s25_final_x4    |                           3 |                     2 |        5069    |       5069.04 |                      24.938 |

## Table 3. Connectivity and constraint checks

| configuration   |   targets |   failed |   planner_verified_connected |   cell_graph_connected |   reach_main_component_raster |   hard_constraint_violations |   routes_crossing_without_shared_cell |   cycles |   max_chain_depth |   network_len_slope_gt25_m |   network_len_slope_gt10_m |   network_len_in_penalised_cells_m |   network_routes_crossing_other_footprints_houses |   network_routes_crossing_other_footprints_all |   reach_main_component_road_lines |
|:----------------|----------:|---------:|-----------------------------:|-----------------------:|------------------------------:|-----------------------------:|--------------------------------------:|---------:|------------------:|---------------------------:|---------------------------:|-----------------------------------:|--------------------------------------------------:|-----------------------------------------------:|----------------------------------:|
| x4 (primary)    |       168 |        0 |                          168 |                    168 |                           167 |                            0 |                                     0 |        0 |                 9 |                          0 |                       44.1 |                              614.9 |                                                28 |                                             31 |                               168 |
| x1 (P3 control) |       168 |        0 |                          168 |                    168 |                           167 |                            0 |                                     0 |        0 |                10 |                          0 |                       44.1 |                                0   |                                                56 |                                             60 |                                   |

`reach_main_component_raster` is the planner's definition (the 6,149-cell main road component inside the village polygon); `reach_main_component_road_lines` uses the TGRAC road lines including the parts outside the polygon (see connectivity_resolution.md).

## Table 4. C1 sensitivity to synthetic target omissions and additions (x4 configuration)

| perturbation               |   runs |   house_targets_routed_mean |   failed_max |   unique_len_m_mean |   unique_len_m_min |   unique_len_m_max |   unique_len_per_routed_m_mean |   saving_vs_independent_pct_mean |   routes_crossing_other_footprints_mean |   share_common_targets_same_attach_class_mean |   mean_len_change_common_targets_m_mean |
|:---------------------------|-------:|----------------------------:|-------------:|--------------------:|-------------------:|-------------------:|-------------------------------:|---------------------------------:|----------------------------------------:|----------------------------------------------:|----------------------------------------:|
| baseline (no perturbation) |      1 |                       163   |            0 |             5069    |            5069    |            5069    |                          31.1  |                            24.94 |                                    28   |                                          1    |                                    0    |
| omit 10%                   |      5 |                       147   |            0 |             4684.43 |            4521.04 |            4821.89 |                          31.87 |                            25.09 |                                    24.2 |                                          0.97 |                                    0.49 |
| omit 20%                   |      5 |                       130   |            0 |             4211.49 |            3991.39 |            4410.93 |                          32.4  |                            24.95 |                                    20.4 |                                          0.96 |                                    1.39 |
| add 10%                    |      5 |                       177.4 |            0 |             5502.4  |            5393.23 |            5548.83 |                          31.02 |                            25.62 |                                    32   |                                          0.98 |                                   -0.55 |
| add 20%                    |      5 |                       190.6 |            0 |             5868.27 |            5822.32 |            5916.07 |                          30.79 |                            25.39 |                                    36.4 |                                          0.97 |                                   -1.2  |
| omit merged blobs          |      1 |                       101   |            0 |             3579.04 |            3579.04 |            3579.04 |                          35.44 |                            26.64 |                                    14   |                                          0.94 |                                    3.21 |
| omit smallest 10%          |      1 |                       146   |            0 |             4648.65 |            4648.65 |            4648.65 |                          31.84 |                            24.92 |                                    25   |                                          0.99 |                                    2.18 |
| omit smallest 25%          |      1 |                       122   |            0 |             3798.29 |            3798.29 |            3798.29 |                          31.13 |                            25.56 |                                    20   |                                          0.96 |                                    2    |

Per-run rows are in `table4_c1_sensitivity_per_run.csv`. Compare `unique_len_per_routed_m`, not total length: removing targets removes routes, so a shorter network is not by itself more efficient.

## Table 6. Obstacle avoidance: price and effect of keeping routes out of building footprints

| scenario                                 | run                               |   penalty_multiplier | avoid_buildings   |   houses_routed |   failed |   house_unique_len_m |   independent_unique_len_m_same_config |   saving_vs_independent_pct |   house_routes_crossing_other_footprints |   crossing_len_m |   crossing_only_in_first_20m |   crossing_beyond_first_20m |   facility_unique_len_m |   reach_main_component |   targets |
|:-----------------------------------------|:----------------------------------|---------------------:|:------------------|----------------:|---------:|---------------------:|---------------------------------------:|----------------------------:|-----------------------------------------:|-----------------:|-----------------------------:|----------------------------:|------------------------:|-----------------------:|----------:|
| x1, no penalty (P3 control)              | S2_fac_C0_s25_final_x1            |                    1 | off               |             163 |        0 |               4705.4 |                                 6921.3 |                        32   |                                       56 |            660.1 |                           21 |                          35 |                   235.2 |                    167 |       168 |
| x4, penalty on footprint cells (primary) | S2_fac_C0_s25_final_x4            |                    4 | off               |             163 |        0 |               5069   |                                 6753.1 |                        24.9 |                                       28 |            209.1 |                           12 |                          16 |                   249.3 |                    167 |       168 |
| buffer 7.1 m, penalty x20                | S2_fac_C0_s25_final_avoid_buf20   |                   20 | buffer            |             163 |        0 |               6238.1 |                                 7650   |                        18.5 |                                       19 |            147.9 |                           16 |                           3 |                   302.4 |                    167 |       168 |
| buffer 7.1 m, penalty x100               | S2_fac_C0_s25_final_avoid_buf100  |                  100 | buffer            |             163 |        0 |               6190.3 |                                 7633   |                        18.9 |                                       19 |            144.8 |                           16 |                           3 |                   322.9 |                    167 |       168 |
| buffer 7.1 m, penalty x1000              | S2_fac_C0_s25_final_avoid_buf1000 |                 1000 | buffer            |             163 |        0 |               6190.3 |                                 7661.4 |                        19.2 |                                       19 |            144.8 |                           16 |                           3 |                   322.9 |                    167 |       168 |

Hard blocking of footprint cells failed: all 163 house points lie inside their own blocked cell and the planner does not start from a blocked cell. The buffer scenarios hand the planner footprints buffered by 7.1 m (half a cell diagonal) with a large penalty. The effect saturates by x20; the remaining crossings are mostly at the start of a route, where the target sits among touching buildings.

## Table 5. Economic and material impact (illustrative; assumptions in inputs/economic_assumptions.json)

**This is a parametric estimate from assumptions in `inputs/economic_assumptions.json`; it is not an engineering estimate and it is not field-validated.** Rate: Rs 75 lakh/km (central, supplied by the project owner as a PMGSY-based figure and not verified; Rs 60 and 90 lakh/km shown for sensitivity). Section: 3.75 m carriageway, 150 mm sub-base, 150 mm WBM, 20 mm bituminous surface, formation 5.0 m wide, 0.30 m average earthwork depth, loose-to-compact factor 1.30, bitumen 2.0 kg/m2. All of these are assumptions.

## Savings, house routes only (primary x4 plan, 163 houses)

| baseline_basis                                       |   baseline_len_m |   proposed_len_m |   length_saving_m |   length_saving_pct |   cost_saving_low_Rs_lakh |   cost_saving_central_Rs_lakh |   cost_saving_high_Rs_lakh |   baseline_cost_central_Rs_lakh |   proposed_cost_central_Rs_lakh |   saving_aggregate_loose_m3 |   saving_gsb_subbase_loose_m3 |   saving_earthwork_m3 |   saving_bitumen_t |
|:-----------------------------------------------------|-----------------:|-----------------:|------------------:|--------------------:|--------------------------:|------------------------------:|---------------------------:|--------------------------------:|--------------------------------:|----------------------------:|------------------------------:|----------------------:|-------------------:|
| A (fair): independent routes, unique length          |           6753.1 |             5069 |            1684.1 |                24.9 |                     101   |                         126.3 |                      151.6 |                           506.5 |                           380.2 |                      1395.7 |                        1231.5 |                2526.2 |               12.6 |
| B (double-counted): independent routes, total length |          10045.4 |             5069 |            4976.4 |                49.5 |                     298.6 |                         373.2 |                      447.9 |                           753.4 |                           380.2 |                      4124.2 |                        3639   |                7464.6 |               37.3 |

## Quantities for each length

| length                                |   length_m |   aggregate_loose_m3 |   gsb_subbase_loose_m3 |   earthwork_m3 |   bitumen_t |   cost_central_Rs_lakh |
|:--------------------------------------|-----------:|---------------------:|-----------------------:|---------------:|------------:|-----------------------:|
| Proposed shared network               |     5069   |               4200.9 |                 3706.7 |         7603.5 |        38   |                  380.2 |
| Independent routes, unique length (A) |     6753.1 |               5596.6 |                 4938.2 |        10129.7 |        50.6 |                  506.5 |
| Independent routes, total length (B)  |    10045.4 |               8325.1 |                 7345.7 |        15068.1 |        75.3 |                  753.4 |

Combined with the 5 facility routes the unique saving is 1626 m (23.4%): 6945 m independent against 5318 m shared.

Reading: the quotable saving is basis A. Basis B (4976 m, 4.98 km) subtracts the shared network from routes that count shared edges several times; a shared edge would be built once even without optimisation, so basis B overstates the saving by about 3.0 times. Quantities scale linearly with length because a single cross-section is assumed. Earthwork, drainage, cross-drainage works, land and utilities are not modelled.

## Building-avoiding network (illustrative)

| item                                     | value                                                  |
|:-----------------------------------------|:-------------------------------------------------------|
| scenario                                 | Building-avoiding network (buffer 7.1 m, penalty x100) |
| independent_unique_len_same_config_m     | 7633.0                                                 |
| network_len_m                            | 6190.3                                                 |
| length_saving_vs_independent_m           | 1442.7                                                 |
| length_saving_vs_independent_pct         | 18.9                                                   |
| cost_saving_central_Rs_lakh              | 108.2                                                  |
| extra_length_vs_x4_network_m             | 1121.3                                                 |
| extra_cost_vs_x4_network_central_Rs_lakh | 84.1                                                   |
| extra_aggregate_loose_m3_vs_x4           | 929.3                                                  |
| extra_gsb_subbase_loose_m3_vs_x4         | 819.9                                                  |
| extra_earthwork_m3_vs_x4                 | 1681.9                                                 |
| extra_bitumen_t_vs_x4                    | 8.4                                                    |

The saving is against independent routes planned under the same buffer and penalty. The extra length is the price of keeping routes out of footprints compared with the x4 network.

