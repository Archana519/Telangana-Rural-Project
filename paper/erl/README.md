# ERL manuscript (Phase 1 / Stage B only)

Letter for *Environmental Research Letters* (IOP Publishing) on the Damarakunta village case study: StrongDINOv2Seg + instance extraction,
cost surface, shared-network planner and omission sensitivity. No hierarchical (Contribution 3) content. `DELIVERABLES_DAMARAKUNTA_STAGE_B/` is read-only input.

| File | Purpose |
|---|---|
| `main.tex`, `references.bib` | manuscript (iopart-style structure; compiles with plain `article` when `iopart.cls` is absent) |
| `main.pdf`, `manuscript.docx` | built outputs |
| `figures/` , `make_erl_figures.py` | four 300 dpi figures, drawn from Stage B tables and tracked layers (no imagery basemap: licence unresolved) |
| `verify_erl_numbers.py` | checks every quoted number against Stage B files (`python paper/erl/verify_erl_numbers.py`) |
| `wordcount.py` | main-text and abstract word count (ERL Letters: 4000 words, abstract about 200) |
| `build_docx_erl.py` | builds `manuscript.docx` (pandoc + python-docx) |
| `supplementary/loveda_epoch4_confusion_matrix.csv` | epoch-4 confusion matrix copied from the training notebook (basis of the LoveDA metrics) |

Build: `pdflatex main && bibtex main && pdflatex main && pdflatex main`; Word: `python paper/erl/build_docx_erl.py`.
On Overleaf with the IOP template (`iopart.cls`, `iopart-num.bst`) the same file switches to the IOP class automatically; that branch has not been compiled here.

## Open items for the author (marked TODO in `main.tex`)
supervisor / co-authors, corresponding-author e-mail, funding statement, conflict-of-interest confirmation, Zenodo DOI for the data archive.
Before submission: clear the Esri imagery licence for derived products, and confirm the TGRAC data terms.
