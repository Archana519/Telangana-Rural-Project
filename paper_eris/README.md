# ERIS manuscript (paper_eris/)
Build: `pdflatex main && bibtex main && pdflatex main && pdflatex main`; double-anonymous: `pdflatex "\def\ANON{1}\input{main}"` (after a normal build).
Checks: `python paper_eris/verify_eris_numbers.py` (numbers vs result files), `python paper_eris/check_citations.py` (cite keys / bib / DOI-or-URL).
DOCX: `python paper_eris/build_docx.py` (pandoc). `fig_architecture.tex` -> TikZ source of the architecture figure.
Open items: corresponding e-mail, Zenodo DOI, imagery licence. The IOP class is not installed here; paste into the IOP template at submission.
