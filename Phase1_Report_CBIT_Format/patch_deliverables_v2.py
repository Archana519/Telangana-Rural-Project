"""One-off patch (kept for provenance): rebuild_deliverables.py follows the 'noang' scenario family and includes the final charts, tables and chapter."""
p = r"D:\Telangana_Rural_Project\src\tools\rebuild_deliverables.py"
s = open(p, encoding="utf-8").read()


def rep(a, b):
    global s
    assert s.count(a) == 1, (s.count(a), a[:90])
    s = s.replace(a, b)


rep('PRIM = REF / "S2_fac_C0_s25_v11"\n', 'PRIM = None   # set in main(): the noang_x4 run of the chosen pipeline run\n')
rep('    new = ROOT / "outputs" / a.run_id\n', '    global PRIM\n    new = ROOT / "outputs" / a.run_id\n    NEWSB = V / "results" / a.run_id / "stageB"\n    PRIM = NEWSB / "S2_fac_C0_s25_noang_x4"\n    P3R = NEWSB / "S2_fac_C0_s25_noang_x1"\n')
rep('    ev3 = json.load(open(REF / "S2_fac_C0_s25_P3_none" / "evaluation_summary.json", encoding="utf-8"))', '    ev3 = json.load(open(P3R / "evaluation_summary.json", encoding="utf-8"))')
rep('"03_RESULTS_TABLES/PRIMARY_RUN_S2_fac_C0_s25_v11/" + f)', '"03_RESULTS_TABLES/PRIMARY_RUN_S2_fac_C0_s25_noang_x4/" + f)')
rep('    cp(REF / "_connectivity_audit_v2", "03_RESULTS_TABLES/CONNECTIVITY/connectivity_audit_v2")\n    cp(REF / "_connectivity_diagnostic_v1", "03_RESULTS_TABLES/CONNECTIVITY/connectivity_diagnostic_v1")\n    cp(REF / "_validation_main", "04_VALIDATION/MAIN_RUN/validation_main")',
    '    cp(NEWSB / "_connectivity_audit_v2", "03_RESULTS_TABLES/CONNECTIVITY/connectivity_audit_v2")\n    cp(ROOT / "outputs" / "connectivity", "03_RESULTS_TABLES/CONNECTIVITY/line_topology_resolution")\n    cp(ROOT / "outputs" / "final_comparison", "03_RESULTS_TABLES/COMPARISON_TABLES")\n    cp(ROOT / "outputs" / "final_comparison" / "charts", "03_RESULTS_TABLES/CHARTS")\n    cp(ROOT / "outputs" / "verification", "04_VALIDATION/DETECTION_AND_FACILITY_VERIFICATION")\n    cp(ROOT / "outputs" / "visual_audit", "04_VALIDATION/VISUAL_AUDIT_KIT")\n    cp(ROOT / "outputs" / "final_package" / "THESIS_CHAPTER_RESULTS_AND_VALIDATION.md", "00_START_HERE/THESIS_CHAPTER_RESULTS_AND_VALIDATION.md")\n    cp(ROOT / "inputs" / "EXCLUSIONS.md", "00_START_HERE/EXCLUSIONS.md")\n    cp(NEWSB / "_validation_main", "04_VALIDATION/MAIN_RUN/validation_main")')
rep('    cp(REF / "S2_fac_C0_s25_P3_none" / "acceptance_tests.csv", "04_VALIDATION/MAIN_RUN/acceptance_tests_P3.csv")', '    cp(P3R / "acceptance_tests.csv", "04_VALIDATION/MAIN_RUN/acceptance_tests_P3.csv")')
rep('"reference run S2_fac_C0_s25_P3_none/evaluation_summary.json"),\n          ("P3 x1: facility unique length (m)"', '"S2_fac_C0_s25_noang_x1/evaluation_summary.json"),\n          ("P3 x1: facility unique length (m)"')
s = s.replace('"reference run S2_fac_C0_s25_P3_none/evaluation_summary.json"', '"S2_fac_C0_s25_noang_x1/evaluation_summary.json"')
s = s.replace('("primary x4: ', '("noang x4 (3 facilities): ').replace('("P3 x1: ', '("noang x1 (3 facilities): ')
rep('    cp(REF / "_boundary_mask_diag_v1", "05_DIAGNOSTICS/BOUNDARY_AND_ROADS/boundary_mask_diag_v1")', '    # diagnostics, C1, C2 and the reference-run copies below come from the verified 4-facility baseline run and are not scrubbed (inputs/EXCLUSIONS.md)\n    cp(REF / "_boundary_mask_diag_v1", "05_DIAGNOSTICS/BOUNDARY_AND_ROADS/boundary_mask_diag_v1")')
rep('    cp(REF / "_connectivity_audit_v2" / "connectivity_exceptions.csv", "05_DIAGNOSTICS/CONNECTIVITY_EXCEPTIONS/connectivity_exceptions.csv")', '    cp(NEWSB / "_connectivity_audit_v2" / "connectivity_exceptions.csv", "05_DIAGNOSTICS/CONNECTIVITY_EXCEPTIONS/connectivity_exceptions.csv")')
rep('    for sub in ("maps", "maps_v2"):\n        cp(PRIM / sub, "02_FINAL_MAPS/reference_run_%s" % sub)\n', '')
rep('| Facility connectivity | 4/4 routed, all reach the main component | PASS (model connectivity only) | Facility identities are not field-verified; the anganwadi coordinate is unsupported by any detected footprint | `facility_status.csv`, `outputs/verification/` |',
    '| Facility connectivity | 3/3 retained facilities routed and connected; the anganwadi (unsupported coordinate) was excluded at the project owner\'s request | PASS (model connectivity only) for 3 of 4 priority facilities | A verified location for the anganwadi; facility identities are not field-verified | `facility_status.csv`, `EXCLUSIONS.md` |')
rep('| Building-footprint avoidance | buffer scenario: 29 to 20 house routes crossing another footprint, +22% unique length; hard block failed (163/163 targets) | PARTIAL |',
    '| Building-footprint avoidance | active in the final network: buffer 7.1 m, penalty x100; 29 to 20 house routes crossing another footprint, +22% unique length; hard block failed (163/163 targets). Routes do NOT completely skirt buildings | PARTIAL |')
rep('| Visual audit of facilities | protocol and Visual Grounding Table prepared | NOT VERIFIED |', '| Anganwadi exclusion | excluded from planning layers, CSVs and maps (derived layer; original input untouched); the plan serves 3 of 4 priority facilities | OPEN (needs a verified location) | Verified coordinate, then re-include | `inputs/EXCLUSIONS.md` |\n| Visual audit of facilities | protocol and Visual Grounding Table prepared (3 facilities) | NOT VERIFIED |')
rep("- Facility identities and coordinates are not field-verified; the anganwadi coordinate lies 371 m from the nearest detected footprint.", "- Facility identities and coordinates are not field-verified. The anganwadi was excluded from the deliverables because its coordinate lies 371 m from the nearest detected footprint (inputs/EXCLUSIONS.md).")
rep('("U15", "Anganwadi coordinate unsupported: nearest detected footprint 371 m, nearest Open Buildings polygon 126 m", "UNRESOLVED", "Visual audit in Google Earth; verify against registry", "outputs/verification, outputs/visual_audit"),',
    '("U15", "Anganwadi excluded at the owner\'s request (coordinate 371 m from the nearest footprint, 126 m from the nearest Open Buildings polygon); the plan serves 3 of 4 priority facilities", "OPEN", "Verify the location (registry or Google Earth), then re-include", "inputs/EXCLUSIONS.md"),')
rep('("U17", "House routes still crossing another footprint in the building-avoiding scenario (20 of 163)", "BOUNDED",', '("U17", "House routes still crossing another footprint in the building-avoiding final network (20 of 163)", "BOUNDED",')
rep('| Facilities / schools / health | TGRAC layers (school, health, anganwadi) | Not stated |', '| Facilities / schools / health | TGRAC layers (school, health; the anganwadi record is excluded, see EXCLUSIONS.md) | Not stated |')
rep('| 02_FINAL_MAPS | reference-run maps, the five final maps, `MAP_FILE_CHECK.csv` |', '| 02_FINAL_MAPS | the five final maps, `MAP_FILE_CHECK.csv` |')
rep('| 03_RESULTS_TABLES | primary run tables, C1, C2, connectivity, uncertainty |', '| 03_RESULTS_TABLES | primary (noang x4) tables, comparison tables, charts 1-5, connectivity, and the verified-baseline C1, C2 and uncertainty tables |')
rep('| 04_VALIDATION | acceptance tests, validator results, manifests |', '| 04_VALIDATION | acceptance tests, validator results, manifests, detection and facility verification, visual audit kit |')
rep('Run everything again with', 'The final scenarios exclude the anganwadi (`00_START_HERE/EXCLUSIONS.md`); the verified 4-facility baseline run is kept only as reproduction evidence (C1, C2, uncertainty and diagnostics below come from it and are not scrubbed).\n\nRun everything again with')
open(p, "w", encoding="utf-8").write(s)
print("patched")
