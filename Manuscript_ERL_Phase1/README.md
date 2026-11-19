# ERL Letter, Phase 1 (Damarakunta, Stage A + B)

| File | Purpose |
|---|---|
| `erl_manuscript.tex` | IOP `iopjournal` version (not compiled here: class not installed) |
| `erl_manuscript_article.tex`, `erl_manuscript_article.pdf` | `article` fallback, compiled with pdflatex (14 pages, 0 errors, 0 warnings) |
| `body.tex`, `abstract.tex`, `backmatter.tex` | shared text (main text about 1,900 words) |
| `references.bib`, `references.tex` | bibliography; `references.tex` is the ERL Harvard (Author Year) list typeset from the `.bib` by `make_references.py` |
| `figures/`, `make_fig1_architecture.py` | `ARCHITECTURE_DIAGRAM.png` is the black-and-white technical Figure 1 drawn by the script (300 dpi, Phase 1 only); `chart1_network_lengths.png` and `chart5_obstacle_avoidance_tradeoff.png` are copied from Stage B; `fig4_omission.png` from `paper/erl` |

Numbers come from `DELIVERABLES_DAMARAKUNTA_STAGE_B` and the checked ledger in `paper/erl/verify_erl_numbers.py`.
