# MIKE 2026 — Paper ID 12 — Response to Reviewers

We thank the reviewers for their careful reading. Changes are marked by section/table in the revised manuscript.

## Reviewer #3

**Comment 1 — "experimental results are demonstrated using ten samples, which is smaller in size."**

We expanded the planning evaluation from 10 to **100 distinct LoveDA Rural validation-split tiles (2522.png–2621.png)**, run with identical settings (r = 5 px, 20 px minimum building area). New Sect. 6.3 and Tables 4–5 report:
- Tile composition: 55 tiles have no detected building; 45 have at least one (512 buildings). Of these 45, 19 have a non-empty road skeleton (the *active-road subset*); on the other 26 no road is detected and connectivity stays at 0%.
- Pooled over all 512 buildings, connectivity rises from 4.88% to 36.91% (164 routes, 39,047 px).
- On the 19 active tiles, connectivity rises from 13.26% to 100% (all 19 reach 100%), mean route length 206.5 ± 122.3 px, path efficiency 0.921 ± 0.021. We state that this 100% is algorithmic (every isolated building with a KD-tree target receives a route).
- We report all-tile mean ± std (as computed in our notebook) alongside active-subset mean ± std and median [IQR], since all-tile means include tiles where nothing can be planned.
- The connectivity-radius sensitivity table is retained (tile 4208, 15 buildings) and labelled as a single-tile analysis.

**Comment 2 — "not compared with state-of-the-art methods, limiting any conclusion on its superiority."**

We have added two comparisons and have deliberately limited what we claim from each.

*(a) Route planning (Sect. 4.3, 6.4, Table 6).* Terrain-aware A\* is compared with unweighted A\* and a straight-line (Bresenham) route on the same 100 tiles. On the 19 active tiles it has lower traversal cost on every tile (19/19; exact Wilcoxon signed-rank, two-sided p = 3.8×10⁻⁶; median per-tile reduction 7.6% [IQR 3.2–11.3%] vs. unweighted A\*, 10.5% [7.5–15.1%] vs. the straight line). The straight line crosses predicted water/no-data on 4 tiles versus 1 for terrain-aware A\*; with so few affected tiles this is not statistically significant (p = 0.25) and is reported descriptively. Because cost and obstacles are measured on the same predicted cost surface that A\* minimises, we describe this as a check of **cost-surface adherence and obstacle avoidance**, not evidence of real-world route quality.

*(b) Segmentation backbones (Sect. 6.5, Table 7).* We benchmarked SegFormer-B2 (77.90 ± 25.09 ms) and DeepLabV3-R101 (204.25 ± 57.61 ms) against StrongDINOv2Seg (148.16 ± 33.12 ms) on a Tesla T4. These baselines were used as publicly released and were **not fine-tuned on LoveDA**, so the comparison is **inference latency only**; we make no claim that StrongDINOv2Seg is more accurate than them. We removed an earlier road-fragmentation comparison for the same reason. A like-for-like accuracy comparison (fine-tuning the baselines on LoveDA under the same protocol and reporting mIoU / Road IoU) is stated as future work in Sect. 7, and the paper no longer claims superiority over any baseline.

## Reviewer #5

**Comment — acknowledgement of limitations, including absence of held-out test-set evaluation and field validation.**

We thank the reviewer and have retained and expanded Sect. 7.
- *Evaluation split (Sect. 5, 7):* The 100 planning tiles are validation-split tiles not used for training. Because the validation split also guided epoch selection, they are **not** a held-out test set, and this is stated explicitly. The LoveDA validation metrics (53.80% mIoU, 68.91% mDice, Building IoU 66.77%, Road IoU 56.44%, Table 2) are computed over the full validation split, not over these 100 tiles.
- *Spatial scale (Sect. 4.2, 5):* LoveDA native resolution ≈ 0.3 m/px at 1024×1024, resized to 560×560 ≈ 0.55 m/px; pixel-to-metre conversions are approximate and not used in any metric.
- *Field validation and terrain (Sect. 7):* We state that no physical GPS/cadastral/on-ground survey was performed and that no DEM was used, so slope, drainage and earthworks do not enter the cost surface. The framework is positioned as an automated remote-sensing **pre-feasibility screening tool**, not an engineering design tool.
- We additionally state the 26-tile failure mode (no detected road ⇒ no planning) and the Bresenham-fallback caveat.
