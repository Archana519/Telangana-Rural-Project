#!/bin/bash
# usage: run_all.sh <latex_project_dir>
set -e
cd "$(dirname "$0")"
D="$PWD"; W=$(cygpath -w "$D")
python build_report.py "$1" "$D/Phase1_Report_CBIT_Format.docx" > /dev/null
for pass in 1 2; do
  powershell -NoProfile -ExecutionPolicy Bypass -File export_pdf.ps1 -Docx "$W\Phase1_Report_CBIT_Format.docx" -Pdf "$W\Phase1_Report_CBIT_Format.pdf"
  python -I compute_pages.py Phase1_Report_CBIT_Format.pdf _entries.json pages.json
  python build_report.py "$1" "$D/Phase1_Report_CBIT_Format.docx" pages.json > /dev/null
done
powershell -NoProfile -ExecutionPolicy Bypass -File export_pdf.ps1 -Docx "$W\Phase1_Report_CBIT_Format.docx" -Pdf "$W\Phase1_Report_CBIT_Format.pdf"
python -I compute_pages.py Phase1_Report_CBIT_Format.pdf _entries.json pages_check.json
cmp pages.json pages_check.json && echo "page numbers stable"
