# Pipeline run run_20261102_141136

Status: **PASS**. Profile `final`. Planner SHA-256 `d00ea92028101131627b8592e3df2c33ff350efac9b1de09f9b64cdd56ef70a4`.

| Stage | Step | Status | Seconds | Note |
|---|---|---|---|---|
| 1-2 | verify inputs (hashes) and planner | PASS | 1 | 11 input hashes equal the reference manifest; planner d00ea9202810...; src copies equal scripts/ |
| 3 | Stage A candidate routes | PASS | 3 |  |
| 3 | S2_fac_C0_s25_v11 (verified baseline, building penalty x4) | PASS | 53 |  |
| 3 | S2_fac_C0_s25_P3_none (verified baseline control, no penalty x1) | PASS | 58 |  |
| 3 | final_x4 (final family primary: 5 facilities, penalty x4) | PASS | 51 |  |
| 3 | final_x1 (final family control: no penalty) | PASS | 50 |  |
| 3 | final_avoid_buf100 (building-avoiding scenario: footprints buffered 7.1 m, penalty x100) | PASS | 49 |  |
| 3 | final_avoid_buf20 (penalty saturation check) | PASS | 57 |  |
| 3 | final_avoid_buf1000 (penalty saturation check) | PASS | 51 |  |
| 3 | final_P1 (penalise plausible only) | PASS | 53 |  |
| 3 | final_P2 (penalise plausible and review) | PASS | 53 |  |
| 3 | S1 25 degrees (final family) | PASS | 27 |  |
| 3 | S1 10 degrees (final family) | PASS | 23 |  |
| 3 | S2 10 degrees (final family) | PASS | 47 |  |
| 3 | S2 cost scenario C1 (final family) | PASS | 56 |  |
| 4 | final_K1_P0 (C2 ablation, final family) | PASS | 50 |  |
| 4 | final_K1_P2 (C2 ablation, final family) | PASS | 49 |  |
| 4 | final_K3_P0 (C2 ablation, final family) | PASS | 52 |  |
| 4 | final_K3_P2 (C2 ablation, final family) | PASS | 55 |  |
| 4 | omit_merge (C1, final family) | PASS | 34 |  |
| 4 | omit smallest 10% (C1, final family) | PASS | 39 |  |
| 4 | omit smallest 25% (C1, final family) | PASS | 27 |  |
| 4 | omit 10% seed 20261029 (C1, final family, synthetic) | PASS | 40 |  |
| 4 | omit 10% seed 20261030 (C1, final family, synthetic) | PASS | 41 |  |
| 4 | omit 10% seed 20261031 (C1, final family, synthetic) | PASS | 44 |  |
| 4 | omit 10% seed 20261032 (C1, final family, synthetic) | PASS | 42 |  |
| 4 | omit 10% seed 20261033 (C1, final family, synthetic) | PASS | 43 |  |
| 4 | omit 20% seed 20261029 (C1, final family, synthetic) | PASS | 34 |  |
| 4 | omit 20% seed 20261030 (C1, final family, synthetic) | PASS | 36 |  |
| 4 | omit 20% seed 20261031 (C1, final family, synthetic) | PASS | 33 |  |
| 4 | omit 20% seed 20261032 (C1, final family, synthetic) | PASS | 36 |  |
| 4 | omit 20% seed 20261033 (C1, final family, synthetic) | PASS | 34 |  |
| 4 | add 10% seed 20261029 (C1, final family, synthetic) | PASS | 58 |  |
| 4 | add 10% seed 20261030 (C1, final family, synthetic) | PASS | 78 |  |
| 4 | add 10% seed 20261031 (C1, final family, synthetic) | PASS | 91 |  |
| 4 | add 10% seed 20261032 (C1, final family, synthetic) | PASS | 77 |  |
| 4 | add 10% seed 20261033 (C1, final family, synthetic) | PASS | 99 |  |
| 4 | add 20% seed 20261029 (C1, final family, synthetic) | PASS | 71 |  |
| 4 | add 20% seed 20261030 (C1, final family, synthetic) | PASS | 56 |  |
| 4 | add 20% seed 20261031 (C1, final family, synthetic) | PASS | 56 |  |
| 4 | add 20% seed 20261032 (C1, final family, synthetic) | PASS | 53 |  |
| 4 | add 20% seed 20261033 (C1, final family, synthetic) | PASS | 84 |  |
| 5 | validator, connectivity audit, reference comparison, explanations | PASS | 17 |  |
| 5 | metrics equal the reference run | PASS | 0 | 2 runs, 30 metrics identical to run_20261029_01 (/diff/ <= 1e-6) |
| 5 | collect outputs | PASS | 0 |  |

Costs are ordinal planning units; routes are planning alternatives, not roads; the stress-test runs are synthetic. Detection (Stage 1) and terrain (Stage 2) are verified inputs, not re-run. Where each output is: `stage1_detect` (footprints, facilities), `stage2_terrain` (cost surface rasters, existing roads), `stage3_plan` (new routes, alternatives, why-chosen), `stage4_stress`, `stage5_validate`.

## Input hashes

| Role | SHA-256 now | Equals reference |
|---|---|---|
| buildings | 0eae82fea8ada939 | PASS |
| roads | 3574defb203f2453 | PASS |
| cost | 911ebeb1860aa49f | PASS |
| worldcover | 587eb4d652e3e66f | PASS |
| blocked | 7330837ba9b55588 | PASS |
| slope | 6f6b3c6d26837564 | PASS |
| fac | fc8c5368f5d8b527 | PASS |
| compounds | bc54d6e8c85bf602 | PASS |
| cad | 22d87307efef919a | PASS |
| cad0 | 998d5841637cc8f5 | PASS |
| planner | d00ea92028101131 | PASS |
