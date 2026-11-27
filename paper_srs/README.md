# Science of Remote Sensing manuscript (Elsevier `elsarticle`)

Build: `python paper_erl/build_main.py && python paper_srs/build_main.py`, then in this folder `pdflatex main && bibtex main && pdflatex main && pdflatex main`.

## Grounding rule
No number is typed into `build_main.py`. Data, Methods and Results text is copied verbatim from `paper_erl/main.tex` (itself generated from the result files). All validation figures come from
`DELIVERABLES_CONTRIBUTION_3_MULTI_VILLAGE/validation/*.csv` via `src/multivillage/validation_tables.py`; the abstract, highlights and conclusions use `src/multivillage/pipeline_summary.py`
(same module as the ERL paper). `ERIS_TEX=paper_srs/main.tex python paper_eris/verify_eris_numbers.py` reports 40 checks, 0 failures.

## Journal requirements: what was and was not verified
Verified (search result quoting the ScienceDirect guide for authors, 2026-11-27): Highlights are encouraged, 3-5 bullets, each at most 85 characters including spaces, as a separate editable file
(`highlights.txt`; the lengths are asserted in `build_main.py`).
NOT verified (the guide page returned HTTP 403 to automated access): article-type length or word limit, abstract word limit, keyword limit, graphical-abstract size, figure resolution rules,
reference style, APC. Check these at https://www.sciencedirect.com/journal/science-of-remote-sensing/publish/guide-for-authors before submitting.
Generic Elsevier items used: `elsarticle` template, CRediT statement, declaration of competing interest, data availability, generative-AI declaration, graphical abstract.

## Before submission (authors)
* The generative-AI declaration is marked in red as a placeholder: the authors must confirm or edit it.
* Elsevier's uploaded graphical abstract is `graphical_abstract.png` (a copy of the framework figure); replace it if a dedicated one is wanted.
* Page count is for the single-column `preprint` (review) format with line numbers; it is not a journal limit.
