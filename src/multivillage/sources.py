"""Input provenance: one row per input layer (URL / API endpoint, release, licence, resolution, SHA-256) -> input_manifest.csv."""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
from dataclasses import dataclass, asdict, field
from pathlib import Path


def sha256_file(p: Path, blk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(blk), b""):
            h.update(b)
    return h.hexdigest()


@dataclass
class Source:
    layer: str                  # e.g. "roads"
    role: str                   # what it is used for in the pipeline
    provider: str
    url: str                    # download URL or API endpoint (the exact one that was read)
    release: str = ""
    licence: str = ""
    resolution: str = ""
    local_path: str = ""
    sha256: str = ""
    bytes: int | str = ""
    rows: int | str = ""
    accessed_utc: str = field(default_factory=lambda: dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    note: str = ""

    def fingerprint(self, path: Path, rows=""):
        self.local_path = str(path)
        if path.exists():
            self.sha256, self.bytes, self.rows = sha256_file(path), path.stat().st_size, rows
        return self


def write_manifest(sources: list, out: Path):
    out.parent.mkdir(parents=True, exist_ok=True)
    cols = list(asdict(sources[0]).keys()) if sources else []
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        for s in sources:
            w.writerow(asdict(s))
