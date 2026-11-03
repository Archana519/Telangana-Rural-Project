"""Write CLEANUP_PHASE1_REPORT.md from archive/2026-10-30_phase1/PLAN.csv and the current tree."""
import collections, csv, os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
os.chdir(ROOT)
rows = [r for r in csv.DictReader(open("archive/2026-10-30_phase1/PLAN.csv", encoding="utf-8")) if r["action"] == "move"]
cat = collections.defaultdict(list)
for r in rows:
    s = r["source"].replace(chr(92), "/")
    top = s.split("/")[0]
    key = ("scripts/ (legacy scripts and support files)" if top == "scripts" else
           "Siddipet/Damarakunta/results/ (legacy outputs)" if top == "Siddipet" else
           "project root (clutter, superseded notes, old tests and logs)")
    cat[key].append(s.split("/")[-1])

out = ["# Cleanup report, phase 1 (2026-10-30)", "",
       "Nothing was deleted. %d items were moved (renamed on the same drive) to `archive/2026-10-30_phase1/`, keeping their original relative paths. "
       "Every move is logged with SHA-256 in `archive/2026-10-30_phase1/MOVE_LOG.csv`; the plan is in `PLAN.csv`. To undo everything:" % len(rows),
       "", "```bash", "python src/tools/restore_from_archive.py 2026-10-30_phase1", "```", "", "## 1. Moved to archive", ""]
for k, v in cat.items():
    out.append("### %s: %d items" % (k, len(v)))
    out.append(", ".join("`%s`" % n for n in sorted(v)))
    out.append("")
out += ["Notes: `results/google_open_buildings` (17 GB test run) is in the archive. Scripts that kept scripts name in code "
        "(`plan_individual_house_network_v1`, `reconstruct_damarakunta_routes_v4`, older `dk_stageB_c1_*` versions, `dk_stageB_run`) "
        "stay in `scripts/` and are also copied to `src/legacy_dependencies/`.", "",
        "## 2. Final directory tree", "", "```"]
SKIP = {".git", ".venv", "__pycache__"}
OPAQUE = {"archive", "raw", "predictions", "aligned", "digitizer", "Generative_AI_Assignment", "Presentation_Review",
          "DELIVERABLES_DAMARAKUNTA_STAGE_B", "Phase1_Report_CBIT_Format", "run_20261029_01", "scripts", "docs", "Angadi_Kistapur"}


def tree(p, depth, pre=""):
    for n in sorted(os.listdir(p)):
        fp = os.path.join(p, n)
        if n in SKIP:
            continue
        if os.path.isdir(fp):
            out.append("%s%s/  (%d entries)" % (pre, n, len(os.listdir(fp))))
            if depth > 1 and n not in OPAQUE:
                tree(fp, depth - 1, pre + "  ")
        elif pre == "":
            out.append("%s%s" % (pre, n))


tree(".", 2)
out += ["```", "",
        "`scripts/` still holds the verified Stage B scripts, because the runner looks for `scripts/plan_network_v2.py` by default and the run manifests "
        "record that path. `src/` holds identical copies grouped by stage (preprocessing, modeling, routing, stress_test, validation, reporting). "
        "Checked: the planner copy has the same SHA-256 (d00ea92028101131627b8592e3df2c33ff350efac9b1de09f9b64cdd56ef70a4) and the runner still starts.", "",
        "## 3. Master command (phase 2)", "",
        "```bash", "python src/run_pipeline.py                 # quick profile", "python src/run_pipeline.py --profile full    # adds C2 ablation and all 20 omit/add seed runs",
        "python src/run_pipeline.py --dry-run             # checks hashes, prints the plan, runs nothing", "python src/run_final_package.py            # after a full run: verification, connectivity, 4 maps, comparison tables, thesis chapter", "```", "",
        "It verifies the 11 input files and the planner by SHA-256 against the reference run, runs Stage A and Stage B into a **new** `results/run_<timestamp>/` folder, "
        "runs the validator, the connectivity audit and `src/routing/explain_routes.py`, checks that every metric equals the reference run `run_20261029_01`, "
        "and collects the results in `outputs/run_<timestamp>/stage1_detect ... stage5_validate` with a `RUN_SUMMARY.md`. "
        "Stage 1 (detection) and Stage 2 (terrain) are verified inputs and are not re-run: the segmentation weights' location is not recorded, and rebuilding the terrain would overwrite verified inputs. "
        "Input sources, dates and licence status: `inputs/METADATA.md`.", ""]
Path("CLEANUP_PHASE1_REPORT.md").write_text("\n".join(out), encoding="utf-8")
print(len(out), "lines")
