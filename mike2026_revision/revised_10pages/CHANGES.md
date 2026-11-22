# Changes vs. the reconstructed original (10-page MIKE 2026 paper, Paper ID 12)

The original `.tex` was not available; the baseline is a reconstruction from the submitted PDF (96.8% character-level match, differences only in table/figure text extraction). TeX-level sentence comparison (floats excluded): 128 original sentences; 6 changed (listed below), 122 identical; 18 new sentences. All 6 original captions and the numbers of all 4 original tables are unchanged.

## A. Edited original text (6 items)
1. **Sect. 6.1** – dangling cross-reference corrected: "pixel-area fractions in Sect. 7.3" -> "Sect. 6.3" (there is no Sect. 7.3; the fractions are in Sect. 6.3).
2. **Abstract** – two sentences added before "All figures are validation-split results…": the 100-tile planning result (19 of 100 plannable, 13.26% -> 100.00%) and the baseline result (43.11% mIoU vs 37.22% SegFormer-B2 and 32.38% DeepLabV3-R101 on 100 validation tiles, Road IoU on par with SegFormer-B2). Abstract is 238 words.
3. **Sect. 7, Evaluation split** – "No local baselines or ablation. Figures for other methods (Sect. 2) come from their papers rather than identical retraining here, and isolating…" -> "Limited baselines and no ablation. Besides figures for other methods taken from their papers (Sect. 2), two baselines were fine-tuned here on LoveDA under a short fixed 3-epoch schedule rather than matched tuning budgets (Sect. 6.6), and isolating…". The clause "this is a demonstration, not proof of outperforming any baseline" is kept.
4. **Sect. 7, Planning scope** – "Results cover only the ten selected LoveDA tiles (Table 3)" -> "…the ten selected LoveDA tiles (Table 3), two further scenes, and 100 validation-split tiles (Table 4)"; failure list extended with "26 of the 45 building tiles in the 100-tile run".
5. **Sect. 7, Generalisation** – "Ten tiles is a small sample…" -> "Ten tiles, and even 100 tiles from one dataset split, are a small sample…; our checkpoint was selected on the validation split while the baselines had only 3 epochs, so the baseline margin may not hold under matched tuning".
6. **Sect. 8 Conclusion** – one sentence added (100-tile planning result and baseline mIoU comparison); "baseline reproduction" -> "matched-budget baseline comparison" in the future-work list.

## B. New material (between `% ===== ADDED` markers)
- **Sect. 6.5 "Additional Planning Scenes" + Table 4:** tiles 4208 and 4200; multi-tile active-road plannable subset (5 of the first 20 LoveDA validation tiles); the 100-tile run on validation-split tiles 2522-2621 from `final_100_distinct_samples_and_baselines.csv` (19 of 100 plannable, 13.26% -> 100.00%, mean 9.95 buildings, 8.63 links, 2,055.13 px, 206.46 px mean route, efficiency 0.9206; 26 building tiles with no detected road; 55 tiles without buildings).
- **Sect. 6.6 "Domain-Adapted Baseline Comparison" + Table 5:** SegFormer-B2 and DeepLabV3-R101 fine-tuned on the 2,522-tile LoveDA training split (AdamW, lr 1.5e-4, 3 epochs), scored with StrongDINOv2Seg on 100 LoveDA validation tiles. Rural-only status of these tiles is not claimed.

## C. Layout-only changes (no wording), needed to stay <= 10 pages
- `float` package with [H] floats at positions that avoid page gaps; `\noindent` after a float that splits a paragraph.
- Fig. 1 width 0.65, Fig. 2 width 0.70 of the text width; Fig. 3 two panels of 0.40 each (white borders trimmed); Fig. 2 re-cropped from the original PDF at 450 dpi.
- `\linespread{0.93}`, compact section/subsection spacing, display and float spacing, `\arraystretch` 0.94, Tables 1-2 at `\footnotesize`, Tables 3-5 via `\resizebox`, references at 8 pt.
- Table 3: minipages 0.49 / 0.44 with a 0.05 text-width gap.
- DOI format restored to the original `doi:...` style.
- Note: line spacing, section spacing and float spacing deviate from the stock `llncs` settings; if the publisher's check flags them, remove these overrides and shorten text instead.
