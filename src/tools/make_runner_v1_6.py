"""Builds scripts/dk_stageB_run_v1_6.py from dk_stageB_run_v1_5.py by adding ONE option, --facility-exempt FACILITY_ID:RADIUS_M (repeatable).

For the named facility only, building footprints are cut by a circle of RADIUS_M around its point in the footprint file handed to the planner, so the
building penalty does not apply to the cells right next to that facility (a facility stands on the edge of its own footprint and the penalty made
its route detour round it). Elsewhere nothing changes. Crossing and penalty statistics are still computed from the original footprints.
Default none = identical to v1.5. The planner (plan_network_v2.py) is imported unmodified. Run once; refuses to overwrite.
usage: python src/tools/make_runner_v1_6.py
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
src = (ROOT / "scripts" / "dk_stageB_run_v1_5.py").read_text(encoding="utf-8")
dst = ROOT / "scripts" / "dk_stageB_run_v1_6.py"
assert not dst.exists(), "v1_6 already exists"


def rep(a, b):
    global src
    assert src.count(a) == 1, (src.count(a), a[:70])
    src = src.replace(a, b)


rep('VERSION = "dk_stageB_run v1.5"', 'VERSION = "dk_stageB_run v1.6"')
rep('    ap.add_argument("--roads-file"', '    ap.add_argument("--facility-exempt", action="append", default=[], metavar="ID:RADIUS_M", help="no building penalty within RADIUS_M of this facility point (repeatable)")\n    ap.add_argument("--roads-file"')
rep('''    _planner_buildings = P["buildings"]
    if a.avoid_buildings == "buffer":
        _bb = bld_all.copy()
        _bb["geometry"] = _bb.geometry.buffer(a.avoid_buffer_m)
''', '''    _planner_buildings = P["buildings"]
    _exempt = []
    for _x in a.facility_exempt:
        _fid, _rad = _x.rsplit(":", 1)
        _row = fac[fac.facility_id.astype(str) == _fid]
        assert len(_row) == 1, f"--facility-exempt: facility {_fid} not found"
        _exempt.append(_row.geometry.iloc[0].buffer(float(_rad)))
        log(f"FACILITY-EXEMPT {_fid}: no building penalty within {_rad} m of the facility point")
    def _cut(g):
        for _c in _exempt:
            g = g.difference(_c)
        return g
    if a.avoid_buildings == "buffer" or _exempt:
        _bb = bld_all.copy()
        if a.avoid_buildings == "buffer":
            _bb["geometry"] = _bb.geometry.buffer(a.avoid_buffer_m)
        _bb["geometry"] = _bb.geometry.map(_cut)
''')
rep('''        _planner_buildings = out / "buildings_buffered_for_planner.gpkg"''', '''        _planner_buildings = out / "buildings_for_planner.gpkg"''')
rep('written.append(("buildings_buffered_for_planner.gpkg", None))', 'written.append(("buildings_for_planner.gpkg", None))')
rep('''    if a.avoid_buildings == "buffer":
        bsub = bsub.assign(geometry=bsub.geometry.buffer(a.avoid_buffer_m))
''', '''    if a.avoid_buildings == "buffer":
        bsub = bsub.assign(geometry=bsub.geometry.buffer(a.avoid_buffer_m))
    if _exempt:
        bsub = bsub.assign(geometry=bsub.geometry.map(_cut))
''')
rep('        log(f"AVOID-BUILDINGS buffer: footprints buffered by {a.avoid_buffer_m} m for the planner; penalty x{a.building_mult}")',
    '        if a.avoid_buildings == "buffer":
            log(f"AVOID-BUILDINGS buffer: footprints buffered by {a.avoid_buffer_m} m for the planner; penalty x{a.building_mult}")')
dst.write_text(src, encoding="utf-8")
print("written", dst)
