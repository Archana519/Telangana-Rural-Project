"""Copy the Contribution 3 deliverables into a local folder (e.g. your Desktop project/results folder).

    python scripts/sync_results_to_folder.py "~/Desktop/<your results folder>" [--dry-run]

Creates <dest>/contribution3/ with:
  hierarchy_real_run/            real-data Levels 2-4 outputs (GeoPackages, summary JSON, override/omission CSVs)
  input_manifest.csv             SHA-256 of every input
  PROVENANCE_AND_PROOFS.md       provenance and proofs report (+ provenance_audit.json, U02/U08 evidence)
  manuscript/                    main.tex, references.bib, manuscript.docx
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
         ("paper/manuscript.docx", "manuscript/manuscript.docx"),
         ("paper/main.tex", "manuscript/main.tex"),
         ("paper/references.bib", "manuscript/references.bib")]


def sync(dest, dry_run=False, log=print) -> list:
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
    return done


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dest")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    sync(a.dest, a.dry_run)
