# Environmental Research Letters (IOP Publishing, ISSN 1748-9326) submission folder

* `main.tex`, `references.bib` (`\bibliographystyle{iopart-num}`), `fig_architecture.png`, `fig_flow_study_areas.png`, `paper_comparison_table.tex`: the manuscript; flat folder as IOP asks, Overleaf-ready.
* `iopjournal.cls`, `orcid.pdf`, `iopjournal-guidelines.pdf`: IOP Publishing's own LaTeX package (https://publishingsupport.iopscience.iop.org/questions/latex-template/), unmodified.
  IOP now distributes `iopjournal.cls`; the older `iopart.cls` / `iopart10.clo` / `iopams.sty` / `setstack.sty` are no longer part of IOP's template package, so they are not included. `\submitto` and `\ead` belonged to `iopart`; the `iopjournal` equivalents are `\articletype` and `\email`.
* Compile: `pdflatex main && bibtex main && pdflatex main && pdflatex main`. Add `[anonymous]` to `\documentclass` for double-anonymous review.
* Regenerate from the working manuscript: `python paper_erl/make_from_eris.py` (body of `paper_eris/main.tex`, numbers of the abstract from the result files). After `python scripts/run_village_pipeline.py --compare-all` and `python scripts/build_paper_flow_figure.py --source segmentation`, run it again to refresh the table and figure copies.
* To confirm before submission: the author contributions (CRediT, marked DRAFT in `main.tex`), the corresponding author, the licences listed in the data availability statement, and the article length (this text is a full-length study; ERL Letters are shorter).
