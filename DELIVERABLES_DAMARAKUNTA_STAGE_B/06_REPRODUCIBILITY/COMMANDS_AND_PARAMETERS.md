> **RECONSTRUCTION (2026-11-02).** The original deliverables folder was lost and was not under version control. This file was rebuilt from the live result files and from the original text as displayed earlier in the same working session, and updated where later evidence changed it. It is not the original file.

# Commands and parameters

Python 3.10.0; numpy 2.2.6, pandas 2.3.3, geopandas 1.1.4, shapely 2.1.2, rasterio 1.4.4, fiona 1.10.1 (from `config_stageB.json`).

## Runs (parameters taken from each run's `config_stageB.json`)
Common: scenario S2, facilities on, cost scenario C0, slope limit 25, building quality `PLAUSIBLE,REVIEW,UNRESOLVED_MERGE`, snap 30 m, max search 1500 m, attach tolerance 15 m, K=3, corridor 20 m with multipliers 3.0 and 8.0, max overlap 0.8, passes 2, corner cut forbid.

| Run | Runner | Differing arguments |
|---|---|---|
| `S2_fac_C0_s25_v11` (primary baseline) | v1.1 | `--building-mult 4.0 --label v11` |
| `S2_fac_C0_s25_P3_none` | v1.2 | `--building-mult 1.0 --label P3_none` |
| `S2_fac_C0_s25_K3_P2`, `K1_P0`, `K1_P2`, `K3_P0` (C2) | v1.3 | `--k`, `--passes` |
| `..._omitsmall25`, `omitsmall10`, `omitmerge` and `_P3_none` variants | v1.3 | `--perturb omit_small --small-pct 25` etc. |
| `..._omit10/20`, `..._add10/20` seeds 20261029-33 | v1.3 | `--perturb omit|add --perturb-frac --perturb-seed` |
| `..._avoid_buf20/100/1000` (building-avoiding scenario) | v1.4 | `--building-mult 20|100|1000 --avoid-buildings buffer --label avoid_buf<m>` |

The original run command lines were not logged; the pipeline (`src/run_pipeline.py`) now writes them to `outputs/run_<timestamp>/pipeline.log`.

## Whole pipeline
```bash
python src/run_pipeline.py --profile full
python src/run_final_package.py
```
## Diagnostics (as run)
```powershell
$B = "D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\run_20261029_01\stageB"
python scripts\dk_stageB_boundary_mask_diag_v1.py --stageb-root $B
python scripts\dk_boundary_crs_compare_v1.py
python scripts\dk_stageB_road_component_boundary_diag_v1.py --stageb-root $B
python scripts\dk_stageB_chain_cell_reasons_v1.py --stageb-root $B
```
Each refuses to overwrite its output folder and hashes inputs before and after. Hashes: `SCRIPT_HASHES.csv`, `INPUT_HASHES.csv` (recomputed in this reconstruction).
