# Proposed seeded random evaluation windows (PLAN ONLY; nothing created; awaiting your approval)

## Why
The six purposive windows were picked by role from model predictions, so recall measured there would be optimistic, and they cover about 1.3 % of the village. A separate random sample is the only part of the design that supports statements about the village as a whole. It is kept separate from the purposive windows in every analysis.

## Sampling frame (deterministic)
- 200 m x 200 m grid, anchored at the SW corner of the village polygon's bounding box (EPSG:32644), cells numbered row-major.
- **Eligible cell:** fully inside the village polygon; at least 90 % valid (non-zero) mosaic pixels; no overlap with any of the six purposive windows and no overlap within a 50 m buffer of them; no overlap with the blank missing-tile corner.
- The frame (list of eligible cell ids, count, SHA-256 of the sorted id list) is written to the manifest before any draw.

## Sample
- **Seed:** 20261024 (proposed), `numpy.random.default_rng(seed)`, draw without replacement from the id-sorted eligible list; numpy version recorded.
- **Size (proposal, your call):** 12 windows (about 0.48 km2, 2.6 % of the village).
- **Optional stratification (recommended):** because buildings cover about 0.3 % of pixels, a plain random sample may contain few buildings. Two strata by the model output: S1 = windows with at least one predicted building polygon (draw 8), S0 = windows with none (draw 4). S0 is essential: it is the only place misses by the model show up. Estimates are reweighted by stratum size (N1/N0 recorded in the manifest). If the eligible S1 cell count is below 8, take all and record it.
- Annotation effort: windows in S0 are mostly quick; estimated total comparable to the six purposive windows.

## Output (new paths; refuse to overwrite)
- `Siddipet\Damarakunta\reference\random_windows\random_windows_v1.gpkg`, layer `random_windows`, EPSG:32644: `rw_id, cell_id, stratum, draw_order, seed, frame_sha256, n_pred_buildings_at_draw`.
- `...\random_windows\sampling_manifest_v1.json` (seed, versions, frame count, hashes, script name and SHA-256).
- Reference buildings for these windows go in the same `reference_buildings_v1.gpkg`, field `sample = 'random'` (purposive ones `'purposive'`).
- New script `scripts\make_random_eval_windows.py` (to be shown to you before it runs; dry-run default that prints the frame and the draw without writing).

## Evaluation procedure
- Annotation is done blind to model predictions (see annotation plan), only after the windows are fixed.
- Metrics (instance precision/recall/F1 at IoU 0.5; pixel IoU for class 2) are computed per window and pooled with stratum weights; **random and purposive results are never pooled**.
- Uncertainty: cluster bootstrap over windows (2,000 resamples, seeded); with 12 windows the interval will be wide, and this is reported rather than hidden.
- Report as "estimate in a random sample of 12 windows", not "village accuracy".

## Limits
One annotator; imagery date unknown and possibly not matching the model's training conditions; windows are 200 m so large features are cut by window edges (flagged); no ground survey, so labels are image-interpretation labels, not field truth.
