"""Optional, opt-in patch for scripts\\evaluate_vs_reference.py so it only scores windows you marked
'complete' in the digitizer (otherwise untraced windows are scored as if they had zero roofs).

    python apply_eval_patch.py            # DRY RUN: shows the diff, changes nothing
    python apply_eval_patch.py --apply    # writes a backup copy first, then patches

It refuses to patch if the expected lines are not found exactly (e.g. you edited the script).
"""
import argparse
import difflib
import shutil
import sys
from pathlib import Path

DEFAULT = Path(r"D:\Telangana_Rural_Project\scripts\evaluate_vs_reference.py")

EDITS = [
    # 1) read the digitizer's status file (written at every commit)
    ('''if OUT.exists():
    sys.exit(f"{OUT} exists; rename it first")
''',
     '''if OUT.exists():
    sys.exit(f"{OUT} exists; rename it first")

# --- digitizer integration: only score windows marked 'complete' (window_status.json) ---
import json
STATUS = REF.parent / "window_status.json"
DONE = set(json.load(open(STATUS, encoding="utf-8"))["complete_windows"]) if STATUS.exists() else None
if DONE is not None:
    print("Scoring only windows marked complete:", sorted(DONE))
'''),
    # 2) an all-empty reference layer is legitimate if the only completed windows have zero roofs
    ('''if ref.empty:
    sys.exit("reference_buildings is empty: trace roofs in QGIS first")''',
     '''if ref.empty and not DONE:
    sys.exit("reference_buildings is empty and no window is marked complete: trace roofs first")'''),
    # 3) skip windows that are not complete
    ('''for _, w in win.iterrows():
    wp = w.geometry
''',
     '''for _, w in win.iterrows():
    if DONE is not None and str(w.window_id) not in DONE:
        print("skipping (not marked complete):", w.window_id)
        continue
    wp = w.geometry
'''),
]


def patched(text: str) -> str:
    for old, new in EDITS:
        if text.count(old) != 1:
            sys.exit("Expected lines not found exactly once - the script differs from what this patch expects.\n"
                     "Nothing was changed. Apply the three edits by hand (see README, section 'Evaluation script').")
        text = text.replace(old, new)
    return text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--script", default=str(DEFAULT))
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    p = Path(a.script)
    if not p.exists():
        sys.exit(f"Not found: {p}")
    old = p.read_text(encoding="utf-8")
    if "window_status.json" in old:
        sys.exit("Already patched.")
    new = patched(old)
    diff = "".join(difflib.unified_diff(old.splitlines(True), new.splitlines(True), "before", "after"))
    print(diff)
    if not a.apply:
        print("DRY RUN - nothing written. Re-run with --apply to patch (a backup copy is made first).")
        return
    bak = p.with_name(p.name + ".bak_before_digitizer_patch")
    if bak.exists():
        sys.exit(f"Backup {bak} already exists; move it aside first.")
    shutil.copy2(p, bak)
    p.write_text(new, encoding="utf-8")
    print(f"Patched. Backup of the original: {bak}")


if __name__ == "__main__":
    main()
