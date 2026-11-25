# Environmental Research Letters manuscript (IOP `iopjournal` class)

`main.tex` is the ERL submission of the four-settlement study (Damarakunta, Adilabad, Aswaraopeta, Alampur). It is written by `build_main.py`
(prose in the script; numbers read from the committed result files through `src/multivillage/pipeline_summary.py`; the appendix strategy table is built from the committed routing_strategy_comparison.csv files).

```bash
python paper_erl/build_main.py                       # rewrites main.tex and refreshes the figure / table copies
cd paper_erl && pdflatex main && bibtex main && pdflatex main && pdflatex main
ERIS_TEX=paper_erl/main.tex python paper_eris/verify_eris_numbers.py     # ledger check of the numbers (ERL mode checks the four-area numbers; the ERIS manuscript keeps the 2018-mandal ledger)
```

Figures: `fig_architecture.png` (Figure 1; source `paper_erl/fig_architecture.tex`, synced to `paper_eris/`) and `fig_flow_study_areas.png` (Figure 2; regenerate on the PC that holds the segmentation results with
`python scripts/build_paper_flow_figure.py --source segmentation`). Table 3 is `paper_comparison_table.tex` (`python scripts/run_village_pipeline.py --compare-all`).
`iopjournal.cls`, `orcid.pdf` and `iopjournal-guidelines.pdf` are IOP's originals; add `[anonymous]` to `\documentclass` for double-anonymous review. The CRediT roles are a draft to be confirmed by the authors.
`make_from_eris.py` is the earlier generator and is superseded by `build_main.py`.
