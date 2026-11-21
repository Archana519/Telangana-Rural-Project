# Changes vs. reconstructed original (10-page MIKE paper)

Content check (TeX-level sentence comparison, floats excluded): 128 original sentences -> 2 replaced, 0 other changes, ~11 added. All 6 original captions and all 4 original tables' numbers are unchanged.

## 1. Replaced (Sect. 7 only)
- OLD: "No local baselines or ablation. Figures for other methods (Sect. 2) come from their papers rather than identical retraining here, and isolating the FPN, ASPP, and decoder's individual contributions is left for future work; this is a demonstration, not proof of outperforming any baseline."
- NEW: "Limited baselines and no ablation. Besides figures for other methods taken from their papers (Sect. 2), two baselines were fine-tuned here on LoveDA under a short fixed 3-epoch schedule rather than matched tuning budgets (Sect. 6.6), and isolating the FPN, ASPP, and decoder's individual contributions is left for future work; this is a demonstration, not proof of outperforming any baseline."

## 2. Added (between `% ===== ADDED` markers in main.tex)
- Sect. 6.5 "Additional Planning Scenes" + Table 4 (tiles 4208, 4200, multi-tile active-road plannable subset, and the 100-tile run from final_100_distinct_samples_and_baselines.csv: 19 of 100 plannable, 13.26% -> 100.00%; 26 building tiles with no detected road).
- Sect. 6.6 "Domain-Adapted Baseline Comparison" + Table 5 (SegFormer-B2, DeepLabV3-R101, StrongDINOv2Seg).

## 3. Layout-only changes (no wording changes), needed to stay <= 10 pages
- `float` package, floats set to [H] at sentence-level positions chosen to avoid gaps; `\noindent` after a float that splits a paragraph.
- Fig. 1 width 0.75, Fig. 2 width 0.85 of text width, Fig. 3 two panels 0.43 each (white borders trimmed); Fig. 2 re-cropped from the original PDF at 450 dpi.
- `\linespread{0.94}`, slightly smaller heading spacing, display skips, float spacing, `\arraystretch 0.94`, Tables 1-2 and 3 at \footnotesize/resizebox, references 8 pt (`\footnotesize`).
- DOI format restored to the original `doi:...` style.
