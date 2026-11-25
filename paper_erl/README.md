# Environmental Research Letters manuscript (IOP `iopjournal` class)

`main.tex` is the ERL submission of the four-settlement study (Damarakunta, Adilabad, Aswaraopeta, Alampur). It is written by `build_main.py`
(prose in the script; numbers read from the committed result files through `src/multivillage/pipeline_summary.py`; the detailed 10 m robustness tables of the appendix are copied from `paper_eris/main.tex`).

```bash
python paper_erl/build_main.py                       # rewrites main.tex and refreshes the figure / table copies
cd paper_erl && pdflatex main && bibtex main && pdflatex main && pdflatex main
ERIS_TEX=paper_erl/main.tex python paper_eris/verify_eris_numbers.py     # ledger check of the numbers (164 checks, 0 failures)
```

Figures: `fig_architecture.png` (Figure 1; source `paper_eris/fig_architecture.tex`) and `fig_flow_study_areas.png` (Figure 2; regenerate on the PC that holds the segmentation results with
`python scripts/build_paper_flow_figure.py --source segmentation`). Table 3 is `paper_comparison_table.tex` (`python scripts/run_village_pipeline.py --compare-all`).
`iopjournal.cls`, `orcid.pdf` and `iopjournal-guidelines.pdf` are IOP's originals; add `[anonymous]` to `\documentclass` for double-anonymous review. The CRediT roles are a draft to be confirmed by the authors.
`make_from_eris.py` is the earlier generator and is superseded by `build_main.py`.
