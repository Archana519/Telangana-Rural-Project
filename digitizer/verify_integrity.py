"""Check that the digitizer has not changed anything it must never change.

    python verify_integrity.py --init     # once, BEFORE you start tracing: record fingerprints
    python verify_integrity.py            # any time: compare against the recorded fingerprints

Fingerprinted (SHA-256): the satellite mosaic, the AI candidate GeoPackage, the V4 route GeoPackage,
the WorldCover/cost rasters used by routing (if present), and the `windows` layer (every attribute and
every geometry byte) of digitize_windows.gpkg. Add more files with --also PATH (repeatable).
Exit code 0 = everything identical; 1 = something differs or the baseline is missing.
Read-only except for writing its own baseline JSON on --init.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from core import (DEFAULT_CANDIDATES, DEFAULT_GPKG, DEFAULT_RASTER, DEFAULT_ROOT, file_sha256,  # noqa: E402
                  layer_digest)

EXTRA_DEFAULT = [
    DEFAULT_ROOT / "results" / "damarakunta_routes_v4.gpkg",
    DEFAULT_ROOT / "aligned" / "damarakunta_worldcover_10m.tif",
    DEFAULT_ROOT / "aligned" / "damarakunta_cost_surface_10m.tif",
]


def collect(raster, cands, gpkg, extra):
    fp = {}
    for p in [raster, cands, *extra]:
        p = Path(p)
        if p.exists():
            fp[str(p)] = {"sha256": file_sha256(p), "bytes": p.stat().st_size}
        else:
            fp[str(p)] = {"missing": True}
    fp[f"{gpkg}::windows"] = {"sha256": layer_digest(Path(gpkg), "windows")}
    return fp


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--init", action="store_true")
    ap.add_argument("--raster", default=str(DEFAULT_RASTER))
    ap.add_argument("--candidates", default=str(DEFAULT_CANDIDATES))
    ap.add_argument("--gpkg", default=str(DEFAULT_GPKG))
    ap.add_argument("--also", action="append", default=[])
    ap.add_argument("--baseline", default=None)
    a = ap.parse_args()
    base = Path(a.baseline) if a.baseline else Path(a.gpkg).parent / "digitizer_integrity_baseline.json"
    extra = [Path(x) for x in a.also] + EXTRA_DEFAULT
    now = collect(a.raster, a.candidates, a.gpkg, extra)
    if a.init:
        if base.exists():
            sys.exit(f"Baseline already exists: {base}\nDelete it only if you are sure the files are still pristine.")
        base.write_text(json.dumps(now, indent=2), encoding="utf-8")
        print(f"Baseline recorded for {len(now)} items -> {base}")
        return
    if not base.exists():
        sys.exit(f"No baseline at {base}. Run with --init first (ideally before tracing).")
    ref = json.loads(base.read_text(encoding="utf-8"))
    bad = 0
    for k, v in ref.items():
        cur = now.get(k)
        if v.get("missing") and (cur is None or cur.get("missing")):
            print(f"  (absent, as at baseline)  {k}")
            continue
        same = cur is not None and cur.get("sha256") == v.get("sha256")
        print(f"  {'UNCHANGED' if same else '!!! CHANGED !!!'}  {k}")
        bad += 0 if same else 1
    print("\nAll protected files/layers are identical to the baseline." if not bad else f"\n{bad} item(s) differ from the baseline.")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
