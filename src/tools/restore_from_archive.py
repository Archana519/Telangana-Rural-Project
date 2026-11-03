"""Reverse a cleanup batch: moves every archived item back to its original path using archive/<batch>/MOVE_LOG.csv.
usage: python src/tools/restore_from_archive.py 2026-10-30_phase1
Refuses to overwrite: if an original path already exists, that item is skipped and reported."""
import csv, shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
batch = sys.argv[1]
log = ROOT / "archive" / batch / "MOVE_LOG.csv"
n = skipped = 0
for row in csv.DictReader(open(log, encoding="utf-8")):
    src, dst = ROOT / row["archived"], ROOT / row["original"]
    if not src.exists():
        print("missing in archive:", src); skipped += 1; continue
    if dst.exists():
        print("original path exists, skipped:", dst); skipped += 1; continue
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst)); n += 1
print("restored", n, "skipped", skipped)
