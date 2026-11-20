# Adilabad end to end on your Windows PC (Esri imagery → StrongDINOv2Seg → building extraction → Stage A/B routing → satellite overlays)

One script runs the same chain that produced Damarakunta: `scripts\run_adilabad_end_to_end.py`.

## What the repository contains, and what it does not

| item | in the repo? | where / how it was used for Damarakunta |
|---|---|---|
| Esri tile download | yes, as a recipe | `scripts/export_esri_damarakunta_full.py`: `services.arcgisonline.com/.../World_Imagery/MapServer/export`, 1800 m tiles, 3000 × 3000 px (0.6 m), EPSG:32644, 5 retries. Merged by `scripts/mosaic_esri_damarakunta.py` to `damarakunta_esri_highres_mosaic_0p6m.tif`. |
| StrongDINOv2Seg architecture | yes, two copies | training export `src/modeling/strongdinov2seg_training_updated.py` (runs training at import) and the importable verbatim copy `src/modeling/strongdinov2seg_model.py` (added for this script). Encoder `facebook/dinov2-base` (downloaded from Hugging Face on first use), FPN on blocks 3/6/9/12, ASPP 6/12/18, 4-stage decoder, 8 classes. |
| **Checkpoint** (`best_model.pth`, epoch 4) | **no** | stays outside the repo: `D:\new_MPS\remoteSensingWebApp\checkpoints\best_model.pth` (the Stage B documents say the same; its hash was never logged). |
| Original `model.py` | **no** | `D:\new_MPS\remoteSensingWebApp\project\model.py`. The script prefers it and falls back to the repo copy; either way `load_state_dict` must report **no missing keys** or the run stops. |
| Tiled inference | yes | `scripts/run_tiled_inference.py` (tile 560, stride 420, margin 70; Damarakunta: CPU, 459 tiles, 3,640.5 s). The new script re-implements it with configurable paths and also logs the checkpoint SHA-256. |
| Instance extraction | yes | `scripts/extract_buildings_v8.py` (distance transform, h-maxima, marker-controlled flooding, neck ratio 0.65, UNRESOLVED_MERGE flag). |
| Stage A / Stage B | yes | `scripts/plan_network_v2.py`, driven by `src/multivillage` with the Stage B parameters in `configs/multivillage/common.yaml`. |
| Satellite overlay figures | new | `src/multivillage/segmentation_variant.py` (credit line "Basemap imagery: Esri, Maxar, Earthstar Geographics, and the GIS User Community." is drawn in every panel). |

Not verified here: the cloud sandbox has no internet route to Esri, no PyTorch and no checkpoint, so the **network and model stages could not be executed**. The stitching, extraction, routing, tables and overlay figures were run on a synthetic stand-in mosaic (a dummy numpy predictor, 40 targets) to prove the code path; those stand-in outputs were deleted and are not results.

## One-time setup (PowerShell, repository root)

```powershell
git pull origin main
python -m venv .venv ; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt opencv-python-headless
pip install torch torchvision transformers          # CPU build is enough; use the CUDA build from pytorch.org if you have an NVIDIA GPU
python scripts\run_adilabad_end_to_end.py --stage check --hash
```

`--stage check` prints versions, GPU, the checkpoint path/size/SHA-256, whether `model.py` is found, whether Esri answers, and which stages already have outputs. Fix anything marked MISSING / NOT reachable. If your checkpoint or `model.py` is elsewhere add `--checkpoint "E:\...\best_model.pth" --model-py "E:\...\model.py"` to every command.

## Run

```powershell
python scripts\run_adilabad_end_to_end.py --stage esri --dry-run        # prints the 12-tile plan (3 x 4, 0.6 m/px) without downloading
python scripts\run_adilabad_end_to_end.py --stage all --workers 4       # open data -> Esri tiles -> mosaic -> inference -> extraction -> routing -> report
```

Every stage skips work that already exists (`--force` redoes it), so you can stop and resume. Run stages separately if you prefer:
`--stage open | esri | mosaic | infer | extract | route | report`.
Before the long inference run, `python scripts\run_adilabad_end_to_end.py --stage infer --smoke` processes a 1400 × 1400 px window to confirm the model loads (writes `*_smoke` files only).

Expected size/time: the study polygon (17.75 km², bbox 4.35 × 5.75 km with 60 m padding) gives 12 Esri tiles and a mosaic of about 7,250 × 9,590 px, about 390 inference tiles (Damarakunta needed about 7.9 s per tile on CPU, so roughly 50 min on CPU; far less on a GPU). The routing stage with the full sweeps took about an hour with 4 workers for the open-data run; `--quick` runs only the main strategy comparison (minutes) and is not enough for the sensitivity tables.
On Windows the planner jobs use the `spawn` start method (no `fork`), which is supported.

## Outputs

Work files (git-ignored): `data\villages\adilabad_esri\` (tiles, `aligned\adilabad_esri_highres_mosaic_0p6m.tif`, `predictions\pred_classes_full.tif`, `building_prob_full.tif`, `run_log_full.json` with the checkpoint hash, `results\v8_instances\buildings_v8_adilabad.gpkg`).

Deliverables (commit these): `DELIVERABLES_CONTRIBUTION_3_MULTI_VILLAGE\01_ADILABAD_SEGMENTATION\`
`metrics_summary.json`, `building_extraction_summary.csv`, `verified_facilities.csv`, `routing_strategy_comparison.csv`, `penalty_sensitivity.csv`, `omission_runs.csv`, `omission_summary.csv`, `target_definition_sensitivity.csv`, `comparison_open_vs_segmentation.csv`, and `figures\sat_map1_a/b.png` (window and zoom with detected footprints coloured by quality class), `sat_map2_independent_*`/`sat_map2_two_stage_*` (routes over the imagery), `sat_legend.png`.
Only the footprint source differs from the open-data run in `01_ADILABAD`; boundary, Overture roads, Overture places, WorldCover, DEM, cost surface, planner settings, the 30 m road-gap rule, penalty sweep and omission seeds are identical.

## Plugging the results into the papers

Commit and push `01_ADILABAD_SEGMENTATION`, then ask for the paper update. The numbers that change, once the segmentation run replaces open footprints as the Adilabad evidence, are: Section III-B (footprint source, counts, the "StrongDINOv2Seg was not run" sentences), Table V, Section V-E and its robustness subsection, the abstract's Adilabad figures, the limitations, and the figure captions (satellite panels carry the Esri credit). Keep the open-data result as a second row/column if you want both.

## Cautions

* Esri World Imagery is used under the terms you stated (non-commercial academic use, tiles not redistributed); check that bulk export of a 17.75 km² window is within them. Never commit the tiles or the mosaic.
* The model was trained on LoveDA and was only checked on Damarakunta by proxy agreement; in Adilabad's dense urban fabric expect many touching roofs, hence a high UNRESOLVED_MERGE share and fewer, larger instances than the Overture footprints. Report the extraction counts and quality classes next to the routing numbers; nothing is validated against a manual reference.
* The Damarakunta mosaic was exported with 3000 × 3000 px on every tile; the new script keeps 0.6 m/px on edge tiles instead.
* Do not use `--dummy-model` or `--debug-limit-targets` for results; they exist for code-path tests.
