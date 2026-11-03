"""Builds scripts/dk_stageB_run_v1_4.py from the verified dk_stageB_run_v1_3.py by adding ONE option, --avoid-buildings {off,buffer}.

  off     (default) behaves exactly like v1.3.
  buffer  the planner is handed footprints buffered by --avoid-buffer-m (7.1 m), so every 10 m cell touched by a building has its centre inside a
          penalised polygon; with a large --building-mult (for example 100) routes enter such cells only when no other way exists.
          A hard block (prohibited raster) was tried first and failed: every house point lies inside its own blocked cell and the planner does not
          start a route from a blocked cell (163 of 163 targets failed with TARGET_IN_HARD_CONSTRAINT_CELL_OR_OUTSIDE_GRID).
          The planner (plan_network_v2.py, hash-pinned) is imported unmodified; only the footprint file handed to it changes.

Also adds --fac-file (alternative facility layer, default none = unchanged).
Versioned like v1_1 to v1_3: the verified runners and the planner are not edited. Run once; refuses to overwrite.
usage: python src/tools/make_runner_v1_4.py
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
src = (ROOT / "scripts" / "dk_stageB_run_v1_3.py").read_text(encoding="utf-8")
dst = ROOT / "scripts" / "dk_stageB_run_v1_4.py"
assert not dst.exists(), "v1_4 already exists"


def rep(a, b):
    global src
    assert src.count(a) == 1, (src.count(a), a[:70])
    src = src.replace(a, b)


rep('VERSION = "dk_stageB_run v1.3"', 'VERSION = "dk_stageB_run v1.4"')
rep('FAC_IDENTITY = {\n', 'FAC_IDENTITY = {\n    "GP_DAMARAKUNTA": "TGRAC_GP_HEADQUARTERS_POINT_BUILDING_NOT_IDENTIFIED",\n    "GP_KASHIREDDYPALLY": "TGRAC_GP_HEADQUARTERS_POINT_BUILDING_NOT_IDENTIFIED",\n')
rep('    ap.add_argument("--corner-cut", choices=["forbid", "allow"], default="forbid")',
    '    ap.add_argument("--corner-cut", choices=["forbid", "allow"], default="forbid")\n'
    '    ap.add_argument("--avoid-buildings", choices=["off", "buffer"], default="off",\n'
    '                    help="buffer: hand the planner footprints buffered by --avoid-buffer-m, so every cell touched by a building is penalised (use with a large --building-mult)")\n'
    '    ap.add_argument("--avoid-buffer-m", type=float, default=7.1, help="7.1 m = half the diagonal of a 10 m cell: any cell touching a footprint has its centre inside the buffered polygon")')
rep('    pn = load_planner(P["planner"])\n',
    '''    _planner_buildings = P["buildings"]
    if a.avoid_buildings == "buffer":
        _bb = bld_all.copy()
        _bb["geometry"] = _bb.geometry.buffer(a.avoid_buffer_m)
        _planner_buildings = out / "buildings_buffered_for_planner.gpkg"
        _planner_buildings.parent.mkdir(parents=True, exist_ok=True)
        _bb.drop(columns=[c for c in ("cand_key",) if c in _bb.columns]).to_file(_planner_buildings, layer="buildings", driver="GPKG")
        written.append(("buildings_buffered_for_planner.gpkg", None))
        log(f"AVOID-BUILDINGS buffer: footprints buffered by {a.avoid_buffer_m} m for the planner; penalty x{a.building_mult}")
    pn = load_planner(P["planner"])
''')
rep('buildings=str(P["buildings"]), buildings_layer="buildings", building_quality=a.building_quality,',
    'buildings=str(_planner_buildings), buildings_layer="buildings", building_quality=a.building_quality,')
rep('    bsub = bld_all[bld_all.quality_class.isin(bq)]\n',
    '    bsub = bld_all[bld_all.quality_class.isin(bq)]\n    if a.avoid_buildings == "buffer":\n        bsub = bsub.assign(geometry=bsub.geometry.buffer(a.avoid_buffer_m))\n')
rep('    ap.add_argument("--avoid-buffer-m"', '    ap.add_argument("--fac-file", default=None, help="alternative priority-facility layer (layer priority_facilities); use with --expect-facilities; the verified input is not edited")\n    ap.add_argument("--avoid-buffer-m"')
rep('    sa = root / "results" / a.stagea_run / "stageA"\n', '    if a.fac_file:\n        P["fac"] = Path(a.fac_file)\n    sa = root / "results" / a.stagea_run / "stageA"\n')
dst.write_text(src, encoding="utf-8")
print("written", dst)
