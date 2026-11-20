# IEEE-style Word manuscript (paper_ieee/)
`IEEE_Journal_Manuscript.docx` (US Letter, two-column, 10 pt Times New Roman, Roman-numeral sections, bracketed references).
Rebuild: `python paper_ieee/build_ieee_docx.py` (python-docx; references parsed from `paper_eris/references.bib`).
Verify: `python paper_ieee/verify_ieee_numbers.py` (runs the ERIS ledger, then checks every DOCX number/table row against it and the result CSVs).
Open items: corresponding e-mail, Zenodo DOI, imagery licence. No IEEE membership grades or funding were invented.
