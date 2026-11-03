"""One-off patch (kept for provenance): texts, verification and runner identity flags for the 5-facility final layer (3 retained + 2 Gram Panchayat HQ)."""
ROOT = r"D:\Telangana_Rural_Project"


def patch(rel, pairs):
    path = ROOT + "\\" + rel.replace("/", "\\")
    s = open(path, encoding="utf-8").read()
    for a, b in pairs:
        assert s.count(a) == 1, (rel, s.count(a), a[:90])
        s = s.replace(a, b)
    open(path, "w", encoding="utf-8").write(s)


patch("src/validation/verify_detections.py", [
    ("    attr_ll = {}\n    for fn, label in alt.items():",
     "    attr_ll = {}\n    for r_ in fac.itertuples():\n        if getattr(r_, 'tgrac_lat', None) is not None and getattr(r_, 'tgrac_lat') == getattr(r_, 'tgrac_lat'):\n            attr_ll[str(r_.facility_id)] = (r_.tgrac_lat, r_.tgrac_lon)\n    for fn, label in alt.items():"),
])
patch("src/validation/visual_audit_protocol.py", [
    ('        "Government building": "NOT IN DATA:', '        "Administrative (Gram Panchayat headquarters)": "a single building with a Gram Panchayat signboard (about 100-400 m2), usually near the settlement centre, with a yard or meeting space and road or lane access; the TGRAC point is a headquarters location, so check the building",\n        "Government building": "NOT IN DATA:'),
])
patch("src/reporting/make_charts.py", [
    ("Facility counts are straight-line distances from the three retained facilities (the anganwadi was excluded, inputs/EXCLUSIONS.md). Planning results, not field-verified.",
     "Facility counts are straight-line distances from the five facilities in the final layer (anganwadi excluded, two Gram Panchayat HQ points added; inputs/EXCLUSIONS.md, inputs/ADMIN_UTILITIES.md). Planning results, not field-verified."),
    ('names.append(r.facility_name.replace(", ", "\\n")', 'names.append(r.facility_name.replace(" (Damarakunta revenue village)", "").replace(", ", "\\n").replace(" Gram Panchayat HQ", "\\nGram Panchayat HQ")'),
])
patch("src/reporting/make_chapter.py", [
    ("so the deliverables cover three. No government-building layer exists, so no such class is detected or prioritised.\")",
     "Two Gram Panchayat headquarters points from TGRAC (`inputs/ADMIN_UTILITIES.md`) were added as administrative utilities, so the final layer holds five facilities. MeeSeva and Directorate of ESD (Aadhaar/service) centres have no located coordinate in any available source and are not included. No government-building layer exists, so no such class is detected or prioritised.\")"),
    ('    A("**Finding.** All %d retained facilities are supported by a detected footprint and corroborated by an independent Open Buildings polygon. "',
     '    ncor = int((fv[fv.source_layer == "priority_facilities.gpkg"].verdict == "CORROBORATED").sum())\n    A("**Finding.** %d of the %d facilities in the final layer are supported by a detected footprint and %d are corroborated by an independent Open Buildings polygon; the two Gram Panchayat points lie on unresolved-merge footprints, so the Panchayat building itself is not identified. "'),
    ("Until a verified location exists the plan serves 3 of the 4 priority facilities. \"", "Until a verified location exists the plan does not serve the anganwadi. \""),
    ("          nsup, float(exf.nearest_footprint_m)", "          nsup, int((fv.source_layer == \"priority_facilities.gpkg\").sum()), ncor, float(exf.nearest_footprint_m)"),
])
patch("src/reporting/limitations_text.py", [
    ("1. Verify facility positions against a registry, Google Earth and then the field; re-include the excluded anganwadi once its location is verified.",
     "1. Verify facility positions against a registry, Google Earth and then the field; re-include the excluded anganwadi once its location is verified; locate the MeeSeva and Directorate of ESD (Aadhaar/service) centres and add them through `inputs/admin_utilities_intake.csv`; confirm which building is the Gram Panchayat office."),
    ("- Costs are ordinal planning units, not rupees;", "- Two Gram Panchayat headquarters points are included as administrative utilities; the MeeSeva and ESD centres are not, because no coordinate source exists.\n- Costs are ordinal planning units, not rupees;"),
])
patch("src/tools/rebuild_deliverables.py", [
    ("| Facility connectivity | 3/3 retained facilities routed and connected; the anganwadi (unsupported coordinate) was excluded at the project owner's request | PASS (model connectivity only) for 3 of 4 priority facilities | A verified location for the anganwadi; facility identities are not field-verified |",
     "| Facility connectivity | 5/5 facilities in the final layer routed and connected (2 schools, 1 sub-centre, 2 Gram Panchayat HQ points); the anganwadi (unsupported coordinate) was excluded at the project owner's request | PASS (model connectivity only) for the 5 facilities | A verified anganwadi location; facility identities are not field-verified |"),
    ("| Anganwadi exclusion | excluded from planning layers, CSVs and maps (derived layer; original input untouched); the plan serves 3 of 4 priority facilities | OPEN (needs a verified location) | Verified coordinate, then re-include | `inputs/EXCLUSIONS.md` |",
     "| Anganwadi exclusion | excluded from planning layers, CSVs and maps (derived layer; original input untouched) | OPEN (needs a verified location) | Verified coordinate, then re-include | `inputs/EXCLUSIONS.md` |\n| Administrative utilities | 2 Gram Panchayat HQ points (TGRAC layer 10) included, each on or within 1 m of a detected footprint; MeeSeva and Directorate of ESD centres NOT located (no source in 162 TGRAC services or OpenStreetMap) | PARTIAL | Coordinates and source for MeeSeva and ESD; confirm the Panchayat building | `inputs/ADMIN_UTILITIES.md`, `inputs/admin_utilities_intake.csv` |"),
    ('("U15", "Anganwadi excluded at the owner\'s request (coordinate 371 m from the nearest footprint, 126 m from the nearest Open Buildings polygon); the plan serves 3 of 4 priority facilities", "OPEN",',
     '("U15", "Anganwadi excluded at the owner\'s request (coordinate 371 m from the nearest footprint, 126 m from the nearest Open Buildings polygon)", "OPEN",'),
    ('    cp(ROOT / "inputs" / "EXCLUSIONS.md", "00_START_HERE/EXCLUSIONS.md")', '    cp(ROOT / "inputs" / "EXCLUSIONS.md", "00_START_HERE/EXCLUSIONS.md")\n    cp(ROOT / "inputs" / "ADMIN_UTILITIES.md", "00_START_HERE/ADMIN_UTILITIES.md")\n    cp(ROOT / "inputs" / "admin_utilities_intake.csv", "00_START_HERE/admin_utilities_intake.csv")'),
    ('("noang x4', '("noang x4') if False else ('("final x4 (5 facilities): house unique length (m)"', '("final x4 (5 facilities): house unique length (m)"'),
])
# the runner generator: identity flags for the two GP points
patch("src/tools/make_runner_v1_4.py", [
    ("rep('VERSION = \"dk_stageB_run v1.3\"', 'VERSION = \"dk_stageB_run v1.4\"')",
     "rep('VERSION = \"dk_stageB_run v1.3\"', 'VERSION = \"dk_stageB_run v1.4\"')\nrep('FAC_IDENTITY = {\\n', 'FAC_IDENTITY = {\\n    \"GP_DAMARAKUNTA\": \"TGRAC_GP_HEADQUARTERS_POINT_BUILDING_NOT_IDENTIFIED\",\\n    \"GP_KASHIREDDYPALLY\": \"TGRAC_GP_HEADQUARTERS_POINT_BUILDING_NOT_IDENTIFIED\",\\n')"),
])
print("patched")
