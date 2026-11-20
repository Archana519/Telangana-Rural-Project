"""Copy the Contribution 3 deliverables into a local folder (e.g. your Desktop project/results folder).

    python scripts/sync_results_to_folder.py "~/Desktop/<your results folder>" [--dry-run]

Creates <dest>/contribution3/ with:
  hierarchy_real_run/            real-data Levels 2-4 outputs (GeoPackages, summary JSON, override/omission CSVs, figures/ = 300 dpi PNGs)
  input_manifest.csv             SHA-256 of every input
  PROVENANCE_AND_PROOFS.md       provenance and proofs report (+ provenance_audit.json, U02/U08 evidence)
  DELIVERABLES_CONTRIBUTION_3_HIERARCHICAL_ROUTING/   the Stage-B-style deliverables package (maps, charts, tables, architecture, provenance copies)
  manuscript/                    main.tex, references.bib, main.pdf (compiled), manuscript.docx, figures/ (the PNGs main.tex includes)
  --docx-at-root                 also place a copy of manuscript.docx directly in <dest>/contribution3/
Existing files in <dest>/contribution3/ are overwritten; nothing outside that folder is touched.
"""
import argparse
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ITEMS = [("docs/results/hierarchy_real_run", "hierarchy_real_run"),
         ("docs/results/input_manifest.csv", "input_manifest.csv"),
         ("docs/results/PROVENANCE_AND_PROOFS.md", "PROVENANCE_AND_PROOFS.md"),
         ("docs/results/provenance_audit.json", "provenance_audit.json"),
         ("docs/results/U02_penalty_sweep_gp.csv", "U02_penalty_sweep_gp.csv"),
         ("docs/results/U08_dem_comparison.json", "U08_dem_comparison.json"),
         ("DELIVERABLES_CONTRIBUTION_3_HIERARCHICAL_ROUTING", "DELIVERABLES_CONTRIBUTION_3_HIERARCHICAL_ROUTING"),
         ("paper_eris/figures", "manuscript/figures"),
         ("paper_eris/manuscript.docx", "manuscript/manuscript.docx"),
         ("paper_eris/main.pdf", "manuscript/main.pdf"),
         ("paper_eris/main.tex", "manuscript/main.tex"),
         ("paper_eris/references.bib", "manuscript/references.bib")]


def sync(dest, dry_run=False, log=print, docx_at_root=False) -> list:
    out_root = Path(dest).expanduser() / "contribution3"
    done = []
    for rel, name in ITEMS:
        src, dst = REPO / rel, out_root / name
        if not src.exists():
            raise FileNotFoundError(f"{rel} is missing - run `git pull` first")
        log(f"{'would copy' if dry_run else 'copy'}  {rel}  ->  {dst}")
        if not dry_run:
            dst.parent.mkdir(parents=True, exist_ok=True)
            if src.is_dir():
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dst)
        done.append(dst)
    if docx_at_root:
        src, dst = REPO / "paper_eris" / "manuscript.docx", out_root / "manuscript.docx"
        log(f"{'would copy' if dry_run else 'copy'}  paper_eris/manuscript.docx  ->  {dst}")
        if not dry_run:
            shutil.copy2(src, dst)
        done.append(dst)
    return done


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dest")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--docx-at-root", action="store_true", help="also copy manuscript.docx to <dest>/contribution3/")
    a = ap.parse_args()
    sync(a.dest, a.dry_run, docx_at_root=a.docx_at_root)
