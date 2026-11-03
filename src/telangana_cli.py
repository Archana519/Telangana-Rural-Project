"""One simple command for the project, usable from any folder.

    telangana run [--profile quick|final|full] [--dry-run]   run the pipeline, then tidy old runs
    telangana package                                        build the final maps, tables and chapter
    telangana latest                                         print the folder of the newest outputs
    telangana show                                           put the newest results in a small Desktop folder and open them
    telangana all                                            run + package + show: the whole thing, one command
    telangana open                                           open the newest outputs folder
    telangana clean [--keep N] [--yes]                       delete old runs, keep the newest N (default 3)

Every run is saved in outputs/run_<date>_<time>/. After each run, `outputs/latest` points to the newest one and
older runs beyond --keep are removed, so the folder does not fill up. The reference run (run_20261029_01) is never touched.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
RES = ROOT / "Siddipet" / "Damarakunta" / "results"
RUN_NAME = re.compile(r"^run_\d{8}_\d{6}$")      # run_YYYYMMDD_HHMMSS; the reference run run_20261029_01 does not match
DEFAULT_KEEP = 3


def old_runs(keep):
    """Folders (in outputs/ and results/) of runs older than the newest `keep`."""
    names = sorted({d.name for base in (OUT, RES) if base.exists() for d in base.iterdir() if d.is_dir() and RUN_NAME.match(d.name)})
    old = names[:-keep] if keep > 0 else names
    return [base / n for n in old for base in (OUT, RES) if (base / n).exists()]


def newest():
    runs = sorted(d for d in OUT.glob("run_*") if d.is_dir() and RUN_NAME.match(d.name)) if OUT.exists() else []
    return runs[-1] if runs else None


def point_latest():
    """Make outputs/latest.txt (and, where the system allows, a `latest` shortcut) point to the newest run."""
    n = newest()
    if n is None:
        return None
    (OUT / "latest.txt").write_text(str(n) + "\n", encoding="utf-8")
    link = OUT / "latest"
    try:
        if link.is_symlink():
            link.unlink()
        if not link.exists():
            link.symlink_to(n.name, target_is_directory=True)
    except OSError:
        pass                       # e.g. Windows without symlink rights: latest.txt still works
    return n


def write_index():
    """outputs/INDEX.md: every saved run, newest first, with the date it ran and whether it passed."""
    runs = sorted((d for d in OUT.glob("run_*") if d.is_dir() and RUN_NAME.match(d.name)), reverse=True) if OUT.exists() else []
    L = ["# Saved runs", "", "Newest first. Open a folder and read its `RUN_SUMMARY.md` first.", "", "| Ran on | Result | Folder |", "|---|---|---|"]
    for d in runs:
        when = datetime.strptime(d.name[4:], "%Y%m%d_%H%M%S").strftime("%d %b %Y, %H:%M")
        summ = d / "RUN_SUMMARY.md"
        text = summ.read_text(encoding="utf-8") if summ.exists() else ""
        status = "PASS" if "Status: **PASS**" in text else ("FAILED" if "Status: **FAILED**" in text else "unknown")
        L.append("| %s | %s | [%s](%s/RUN_SUMMARY.md) |" % (when, status, d.name, d.name))
    if runs:
        OUT.mkdir(exist_ok=True)
        (OUT / "INDEX.md").write_text("\n".join(L) + "\n", encoding="utf-8")


def desktop():
    home = Path.home()
    for c in (home / "OneDrive" / "Desktop", home / "Desktop"):
        if c.exists():
            return c
    return home / "Desktop"


def open_in_vscode_or_folder(files, folder):
    """Show the files in VS Code if the `code` command exists, otherwise open the folder."""
    code = shutil.which("code")
    if code:
        subprocess.call([code, "-r", str(folder)] + [str(f) for f in files])
        return
    if sys.platform.startswith("win"):
        os.startfile(str(folder))
    else:
        subprocess.call(["open" if sys.platform == "darwin" else "xdg-open", str(folder)])


def small_image(src, dst):
    """Copy an image, shrunk to at most 1600 px wide as a JPEG so the folder stays small."""
    try:
        from PIL import Image
        im = Image.open(src).convert("RGB")
        im.thumbnail((1600, 1600))
        im.save(dst.with_suffix(".jpg"), quality=82)
    except Exception:
        shutil.copy2(src, dst)


def show(open_after=True):
    """Make Desktop/Telangana_Latest_Results: a small folder with only the newest results, replaced each time."""
    n = newest()
    if n is None:
        print("No runs yet. Try: telangana run")
        return 1
    dest = desktop() / "Telangana_Latest_Results"
    shutil.rmtree(dest, ignore_errors=True)
    dest.mkdir(parents=True)
    summ = n / "RUN_SUMMARY.md"
    if summ.exists():
        shutil.copy2(summ, dest / "RUN_SUMMARY.md")
    for sub, pattern, kind in (("final_maps", "*.png", "maps"), ("final_comparison/charts", "*.png", "charts")):
        for f in sorted((OUT / sub).glob(pattern)):
            (dest / kind).mkdir(exist_ok=True)
            small_image(f, dest / kind / f.name)
    for pattern in ("table1_*.csv", "table5_*.csv", "comparison_report.md", "economic_impact.md"):
        for f in sorted((OUT / "final_comparison").glob(pattern)):
            (dest / "tables").mkdir(exist_ok=True)
            shutil.copy2(f, dest / "tables" / f.name)
    when = datetime.strptime(n.name[4:], "%Y%m%d_%H%M%S").strftime("%d %b %Y, %H:%M")
    text = summ.read_text(encoding="utf-8") if summ.exists() else ""
    status = "PASS" if "Status: **PASS**" in text else ("FAILED" if "Status: **FAILED**" in text else "unknown")
    have_pkg = (dest / "maps").exists()
    L = ["# Latest results", "", "Run on: **%s**  |  Result: **%s**" % (when, status), "",
         "| Look here | What it shows |", "|---|---|",
         "| `maps/` | The final village maps (start with `map4_...`: alternatives vs. the shared network) |" if have_pkg else "| (maps) | Not built yet. Run `telangana package` |",
         "| `charts/` | Lengths, materials, cost, accessibility |" if have_pkg else "| (charts) | Not built yet. Run `telangana package` |",
         "| `tables/` | The key numbers as spreadsheets (CSV) and a short report |",
         "| `RUN_SUMMARY.md` | Pass/fail of every step in this run |", "",
         "This folder is replaced every time you run `telangana show`. The full results stay in the project's `outputs/` folder.", ""]
    (dest / "START_HERE.md").write_text("\n".join(L), encoding="utf-8")
    print("Latest results folder:", dest)
    if open_after:
        first = [dest / "START_HERE.md"]
        pics = sorted((dest / "maps").glob("map4*")) + sorted((dest / "charts").glob("chart1*")) if have_pkg else []
        open_in_vscode_or_folder(first + pics, dest)
    return 0


def clean(keep, yes):
    victims = old_runs(keep)
    if not victims:
        print("Nothing to clean. Keeping the newest %d run(s)." % keep)
        return
    print("Old runs to delete (keeping the newest %d):" % keep)
    for v in victims:
        print("  ", v)
    if not yes and input("Delete these folders? type yes: ").strip().lower() != "yes":
        print("Nothing deleted.")
        return
    for v in victims:
        shutil.rmtree(v, ignore_errors=True)
    print("Deleted %d folder(s)." % len(victims))


def run_script(name, args):
    return subprocess.call([sys.executable, str(ROOT / "src" / name)] + args, cwd=str(ROOT))


def main(argv=None):
    ap = argparse.ArgumentParser(prog="telangana", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="run the pipeline (extra options go to run_pipeline.py)")
    r.add_argument("--keep", type=int, default=DEFAULT_KEEP, help="how many recent runs to keep (default 3)")
    r.add_argument("--no-clean", action="store_true", help="do not delete old runs after this one")
    r.add_argument("--no-show", action="store_true", help="do not open the results afterwards")
    sub.add_parser("package", help="build final maps, tables and chapter, then show them")
    sub.add_parser("show", help="put the newest results in a small Desktop folder and open them")
    al = sub.add_parser("all", help="run + package + show (about 40 minutes with real data)")
    al.add_argument("--keep", type=int, default=DEFAULT_KEEP)
    sub.add_parser("latest", help="print the newest outputs folder")
    sub.add_parser("open", help="open the newest outputs folder")
    c = sub.add_parser("clean", help="delete old runs")
    c.add_argument("--keep", type=int, default=DEFAULT_KEEP)
    c.add_argument("--yes", action="store_true", help="do not ask first")
    a, rest = ap.parse_known_args(argv)

    if a.cmd == "run":
        if not (RES / "run_20261029_01").exists():
            print("The original project data is missing, so the pipeline cannot run here.\n"
                  "It needs the reference run (Siddipet/Damarakunta/results/run_20261029_01) and the input rasters.\n"
                  "Copy the data folder from the original computer into this project, then try again.")
            return 2
        code = run_script("run_pipeline.py", rest)
        if code == 0 and "--dry-run" not in rest:
            n = point_latest()
            print("\nNewest outputs:", n)
            if not a.no_clean:
                clean(a.keep, yes=True)
            write_index()
            if not a.no_show:
                show()
        return code
    if a.cmd == "package":
        code = run_script("run_final_package.py", rest)
        return show() if code == 0 else code
    if a.cmd == "show":
        return show()
    if a.cmd == "all":
        print("This takes about 35 to 45 minutes. You can leave it running.")
        code = main(["run", "--no-show", "--profile", "final", "--keep", str(a.keep)] + rest)
        if code:
            return code
        return main(["package"])
    if a.cmd == "latest":
        n = newest()
        print(n if n else "No runs yet. Try: telangana run")
        return 0 if n else 1
    if a.cmd == "open":
        n = newest()
        if n is None:
            print("No runs yet. Try: telangana run")
            return 1
        if sys.platform.startswith("win"):
            os.startfile(str(n))
        else:
            subprocess.call(["open" if sys.platform == "darwin" else "xdg-open", str(n)])
        return 0
    clean(a.keep, a.yes)
    write_index()
    return 0


if __name__ == "__main__":
    sys.exit(main())
