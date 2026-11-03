"""Builds scripts/dk_stageB_run_v1_5.py from dk_stageB_run_v1_4.py by adding ONE option, --roads-file (alternative road layer, default none = unchanged).
Used with the road layer clipped to the village boundary by src/preprocessing/clip_roads.py (gpd.clip). The planner is imported unmodified.
Versioned like v1_1 to v1_4; run once; refuses to overwrite.
usage: python src/tools/make_runner_v1_5.py
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
src = (ROOT / "scripts" / "dk_stageB_run_v1_4.py").read_text(encoding="utf-8")
dst = ROOT / "scripts" / "dk_stageB_run_v1_5.py"
assert not dst.exists(), "v1_5 already exists"


def rep(a, b):
    global src
    assert src.count(a) == 1, (src.count(a), a[:70])
    src = src.replace(a, b)


rep('VERSION = "dk_stageB_run v1.4"', 'VERSION = "dk_stageB_run v1.5"')
rep('    ap.add_argument("--avoid-buffer-m"', '    ap.add_argument("--roads-file", default=None, help="alternative road layer (for example the layer clipped to the boundary); the verified input is not edited")\n    ap.add_argument("--avoid-buffer-m"')
rep('    if a.fac_file:\n        P["fac"] = Path(a.fac_file)\n', '    if a.fac_file:\n        P["fac"] = Path(a.fac_file)\n    if a.roads_file:\n        P["roads"] = Path(a.roads_file)\n')
rep('and a.max_search_m == 1500.0 and a.attach_tol_m == 15.0 and a.corner_cut == "forbid")', 'and a.max_search_m == 1500.0 and a.attach_tol_m == 15.0 and a.corner_cut == "forbid" and not a.roads_file)   # V1 used the unclipped road layer: with --roads-file the V1 comparison does not apply')
dst.write_text(src, encoding="utf-8")
print("written", dst)
