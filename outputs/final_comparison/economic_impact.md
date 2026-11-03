# Economic and material impact (illustrative)

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
