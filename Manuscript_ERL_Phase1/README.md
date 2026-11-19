# ERL Letter, Phase 1 (Damarakunta, Stage A + B)

| File | Purpose |
|---|---|
| `erl_manuscript.tex` | IOP `iopjournal` version (not compiled here: class not installed) |
| `erl_manuscript_article.tex`, `erl_manuscript_article.pdf` | `article` fallback, compiled with pdflatex (13 pages, no undefined references) |
| `body.tex`, `abstract.tex`, `backmatter.tex` | shared text (main text about 1,900 words) |
| `references.bib`, `references.tex` | bibliography; `references.tex` is the ERL Harvard (Author Year) list typeset from the `.bib` by `make_references.py` |
| `figures/` | `ARCHITECTURE_DIAGRAM.png`, `chart1_network_lengths.png`, `chart5_obstacle_avoidance_tradeoff.png` copied from Stage B; `fig1_architecture_phase1.png` is the architecture diagram cropped to drop the planned-work box; `fig4_omission.png` from `paper/erl` |

Numbers come from `DELIVERABLES_DAMARAKUNTA_STAGE_B` and the checked ledger in `paper/erl/verify_erl_numbers.py`.
