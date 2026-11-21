# MIKE 2026 — Paper ID 12 — Response to Reviewers

We thank the reviewers. All additions are in the revised 10-page manuscript; existing sections, equations and methodology are unchanged. New material: Sect. 6.5 (Table 4), Sect. 6.6 (Table 5), and one edited sentence in Sect. 7.

## Reviewer #3

**C1. "Experimental results are demonstrated using ten samples, which is smaller in size."**
We added further planning evidence (Sect. 6.5, Table 4; $r=5$ px):
- **4208.png** (moderately connected): 15 buildings, connectivity 46.67% → 100.00%, 8 links, 1,130.10 px total (141.26 px mean), path efficiency 0.8502.
- **4200.png** (isolated hamlet, sparse road fragment): 16 buildings, 0.00% → 100.00%, 16 links, 6,615.88 px total (413.49 px mean), efficiency 0.9300. Only 100 road pixels were detected in this tile, so all routes target that fragment.
- **Multi-tile batch:** the *active-road plannable subset* of the first 20 Rural validation tiles (the 5 tiles with at least one building and one proposed route; 13 had no building and 2 had no plannable route): mean 8.20 buildings/tile, 6.67% → 100.00%, 7.60 links/tile, 1,627.81 px total proposed length, efficiency 0.93. This subset is labelled as such in the paper; it is not an unbiased sample and still small, and we keep the Limitations statement that the evaluation is limited in size.
- **Radius sensitivity** (Table 3, left; tile 4208, now identified as such in Sect. 6.5): r = 3/5/8/10 px give before 40.00/46.67/53.33/60.00% → 100%, 9/8/7/6 links, 1,164.00/1,130.10/1,074.88/1,046.06 px, efficiency 0.8605/0.8502/0.8529/0.8307. This is a single-tile sweep.

**C2. "Results have not been compared with state-of-the-art methods."**
Sect. 6.6 and Table 5 add a comparison with SegFormer-B2 and DeepLabV3-R101, both fine-tuned on the 2,522-tile LoveDA training split at 560×560 (lr = 1.5e-4, 3 epochs) and scored on a 100-tile Rural validation subset against the official pixel-level ground truth on a Tesla T4:

| Model | mIoU | mDice | Building IoU | Road IoU | Latency (ms) |
|---|---|---|---|---|---|
| DeepLabV3-R101 (LoveDA) | 32.38 | 47.41 | 33.50 | 28.80 | 176.36 ± 2.98 |
| SegFormer-B2 (LoveDA) | 37.22 | 50.95 | 32.49 | 34.90 | 64.19 ± 3.23 |
| StrongDINOv2Seg (ours) | 43.11 | 56.62 | 62.40 | 34.79 | 145.34 ± 1.75 |

StrongDINOv2Seg is +5.89 mIoU above SegFormer-B2 and +10.73 above DeepLabV3-R101, with a +29.91 Building-IoU gain over SegFormer-B2. We state the limits of this comparison explicitly: it is *equal LoveDA training data under a short fixed 3-epoch schedule, not identical tuning budgets* (our model is the epoch-4 checkpoint selected on validation mIoU, which favours it; the baselines may be under-trained); Road IoU is on par with SegFormer-B2 (34.79% vs 34.90%); and SegFormer-B2 is about 2.3× faster (64.19 vs 145.34 ms). The 43.11% mIoU is on the 100-tile subset and is not comparable with the 53.80% mIoU (68.91% mDice) on the full validation split (Table 2), which we report separately. We therefore do not claim general superiority. Sect. 7 is updated accordingly (the earlier "No local baselines" sentence is replaced; the statement that this is a demonstration rather than proof of outperforming any baseline is retained).

## Reviewer #5
We thank the reviewer. The acknowledged limitations are retained unchanged in Sect. 7 (validation-split evaluation with model-selection bias and no held-out test set, pixel-space heuristic costs, no field validation, no engineering/terrain/legal feasibility), and we added the above caveats on the new results.

## Building IoU vs Road IoU
Building IoU (62.40%) is high because buildings are compact, high-contrast objects; Road IoU (34.79%, on par with SegFormer-B2) is lower on this 100-tile subset because rural tracks are thin and partly occluded by canopy. The planner is designed for imperfect road masks: roads are cleaned, skeletonized and graph-linked, and A* connects each isolated building to the nearest detected road pixel, so fragmented tracks still provide routing targets. Where no road is detected (e.g. tile 4200 has 100 road pixels) the planner has no target or only a sparse one, which we state in Sect. 6.5.
