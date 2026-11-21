# MIKE 2026 — Paper ID 12 — Point-by-point response (DRAFT, additional experiments)

All numbers below are taken from the Colab outputs in `Untitled0.ipynb` (commit 31b5f28) and `final_MPS_project.ipynb`. Items marked **[verify]** depend on files not yet visible to the author of this draft (`fair_100tile_loveda_sota_comparison.csv`, `multi_tile_planner_summary.csv`).

## 1. Comparison with other segmentation methods (Reviewer #3)
We fine-tuned SegFormer-B2 and DeepLabV3-R101 on the same 2,522-tile LoveDA training split at 560×560 (AdamW, lr 1.5e-4, 3 epochs, cross-entropy ignoring index 0) and scored all three models on 100 validation tiles against the official pixel-level ground truth (classes 1–7), on a Tesla T4.

| Model | mIoU | mDice | Building IoU | Road IoU | Latency (ms) |
|---|---|---|---|---|---|
| DeepLabV3-R101 (LoveDA) | 32.38 | 47.41 | 33.50 | 28.80 | 176.36 ± 2.98 |
| SegFormer-B2 (LoveDA) | 37.22 | 50.95 | 32.49 | 34.90 | 64.19 ± 3.23 |
| StrongDINOv2Seg (ours) | 43.11 | 56.62 | 62.40 | 34.79 | 145.34 ± 1.75 |

StrongDINOv2Seg is +5.89 mIoU over SegFormer-B2 and +10.73 over DeepLabV3-R101, with a large Building-IoU gain (+29.91 over SegFormer-B2). On Road IoU it is on par with SegFormer-B2 (34.79 vs 34.90), and SegFormer-B2 is about 2.3× faster. We state the protocol limits in the paper: the baselines use an identical, short 3-epoch schedule with one learning rate, whereas our model is a 10-epoch checkpoint selected on validation mIoU (the same split the 100 tiles come from), so the comparison is equal-data but not equal-tuning and is biased toward our model. This replaces our earlier latency-only benchmark of non-fine-tuned weights.

## 2. Generalisation across scenes
- 4208.png (15 buildings): connectivity 46.67% → 100%, 8 links, 1,130.10 px (141.26 px mean), efficiency 0.8502.
- 4200.png (16 buildings, none road-connected): 0% → 100%, 16 links, 6,615.88 px (413.49 px mean), efficiency 0.93. Only 100 road pixels were detected in this tile, so every route targets one small fragment; the result shows planner behaviour on an isolated hamlet, not network quality.
- Multi-tile batch: the first 20 LoveDA validation tiles, **restricted to tiles with at least one building and one proposed route**: mean 8.20 buildings, 6.67% → 100%, 7.60 links, 1,627.81 px, efficiency 0.93. Because empty and road-less tiles are excluded, this describes the active-road subset only **[verify: number of tiles retained]**. The unrestricted 100-tile run (`final_100_distinct_samples_and_baselines.csv`) shows that only 19 of 100 tiles are plannable (45 contain buildings; 26 of those have no detected road), and we report both.

## 3. Radius sensitivity (4208.png)
| r (px) | Before → After (%) | Links | Length (px) | Efficiency |
|---|---|---|---|---|
| 3 | 40.00 → 100 | 9 | 1,164.00 | 0.8605 |
| 5 (default) | 46.67 → 100 | 8 | 1,130.10 | 0.8502 |
| 8 | 53.33 → 100 | 7 | 1,074.88 | 0.8529 |
| 10 | 60.00 → 100 | 6 | 1,046.06 | 0.8307 |

Larger radii mark more buildings as already connected, so fewer links are proposed; length falls 10% and efficiency stays within 0.83–0.86. This is a single-tile sweep.

## 4. Building IoU vs Road IoU
Building IoU (62.40%) is high because buildings are compact, high-contrast objects; Road IoU (34.79%) is lower because rural tracks are thin, partly occluded and fragmented. The planner is designed around this: roads are closed/opened, skeletonized and treated as a graph, and A* connects each isolated building to the nearest skeleton pixel over the terrain cost surface, so isolated building–road gaps are bridged by proposed links rather than relying on a complete road mask. We do not claim this repairs missing roads: where no road is detected the planner has no target (26 of 45 building tiles in the 100-tile run).
