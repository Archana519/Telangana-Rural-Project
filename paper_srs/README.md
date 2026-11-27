# Science of Remote Sensing manuscript (Elsevier `elsarticle`)

Build: `python paper_erl/build_main.py && python paper_srs/build_main.py`, then in this folder `pdflatex main && bibtex main && pdflatex main && pdflatex main`.

## Grounding rule
No number is typed into `build_main.py`. Data, Methods and Results text is copied verbatim from `paper_erl/main.tex` (itself generated from the result files). All validation figures come from
`DELIVERABLES_CONTRIBUTION_3_MULTI_VILLAGE/validation/*.csv` via `src/multivillage/validation_tables.py`; the abstract, highlights and conclusions use `src/multivillage/pipeline_summary.py`
(same module as the ERL paper). `ERIS_TEX=paper_srs/main.tex python paper_eris/verify_eris_numbers.py` reports 40 checks, 0 failures.

## Rules enforced (as supplied by the authors from the Science of Remote Sensing Guide for Authors)
1. Abstract <= 250 words, standalone, no citations, abbreviations defined (mIoU, IoU); 1-7 keywords (7). Asserted in `build_main.py`.
2. `highlights.txt`: 3-5 bullets, each <= 85 characters including spaces (asserted; currently 65-78).
3. Maps show study-area extents only: the Telangana/district locator inset was removed from the flow figure (`make_flow_figure()` in `build_main.py`) and every map caption ends with
   "Map lines delineate study areas and do not necessarily depict accepted national boundaries."
4. End matter before the references: CRediT, Declaration of competing interest, Funding (Elsevier no-grant wording), Declaration of generative AI (Elsevier wording, plus the AI-assisted
   workflow-diagram disclosure in the Fig. 1 caption), Data availability (GitHub repository link; datasets cited with the [dataset] tag).
5. References numbered in order of first citation (`elsarticle-num`), LTWA journal abbreviations (27 journal fields rewritten in `references.bib`), DOIs where one exists; the [dataset] tag is added to
   the five dataset records by `postbib.py`.
Build: `python paper_erl/build_main.py && python paper_srs/build_main.py && cd paper_srs && pdflatex main && bibtex main && python postbib.py && pdflatex main && pdflatex main`.

## Journal requirements: what was and was not verified
Verified (search result quoting the ScienceDirect guide for authors, 2026-11-27): Highlights are encouraged, 3-5 bullets, each at most 85 characters including spaces, as a separate editable file
(`highlights.txt`; the lengths are asserted in `build_main.py`).
NOT verified (the guide page returned HTTP 403 to automated access): article-type length or word limit, abstract word limit, keyword limit, graphical-abstract size, figure resolution rules,
reference style, APC. Check these at https://www.sciencedirect.com/journal/science-of-remote-sensing/publish/guide-for-authors before submitting.
Generic Elsevier items used: `elsarticle` template, CRediT statement, declaration of competing interest, data availability, generative-AI declaration, graphical abstract.

## Before submission (authors)
* The generative-AI declaration uses Elsevier's exact wording and the Fig. 1 caption discloses the AI-assisted diagram; the authors must confirm both are true before submitting.
* 12 reference entries have no DOI (policy documents, books, software, a 1968 report and similar); none is invented.
* Elsevier's uploaded graphical abstract is `graphical_abstract.png` (a copy of the framework figure); replace it if a dedicated one is wanted.
* Page count is for the single-column `preprint` (review) format with line numbers; it is not a journal limit.
