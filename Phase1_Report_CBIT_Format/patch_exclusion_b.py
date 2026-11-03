"""One-off patch (kept for provenance): switches the reporting tools to the 'noang' scenario family (anganwadi excluded; inputs/EXCLUSIONS.md)
and makes the building-avoiding network the final network on Maps 4 and 5."""
ROOT = r"D:\Telangana_Rural_Project"


def patch(rel, pairs, header=None):
    path = ROOT + "\\" + rel.replace("/", "\\")
    s = open(path, encoding="utf-8").read()
    for a, b in pairs:
        assert s.count(a) == 1, (rel, s.count(a), a[:90])
        s = s.replace(a, b)
    if header:
        k = s.index("\nimport ") if "\nimport " in s else 0
        s = s[:k] + header + s[k:]
    open(path, "w", encoding="utf-8").write(s)


IMP = "\nimport sys as _sys\nfrom pathlib import Path as _P\n_sys.path.insert(0, str(_P(__file__).resolve().parents[1]))\nimport scenario_names as SN\n"

# ---------------------------------------------------------------- visual_audit_protocol
patch("src/validation/visual_audit_protocol.py", [
    ('    fac = gpd.read_file(V / "reference" / "damarakunta_priority_facilities.gpkg")', '    fac = gpd.read_file(SN.FAC_LAYER, layer="priority_facilities")'),
    ('    print(T.loc[T.facility_id == "1702300", "leads_to_inspect_open_buildings_within_200m"].iloc[0])\n', ''),
], IMP)

# ---------------------------------------------------------------- make_chapter (names and anganwadi text)
s = open(ROOT + r"\src\reporting\make_chapter.py", encoding="utf-8").read()


def rep(a, b):
    global s
    assert s.count(a) == 1, (s.count(a), a[:90])
    s = s.replace(a, b)


rep('    ev = json.load(open(sb / "S2_fac_C0_s25_v11" / "evaluation_summary.json"))', '    ev = json.load(open(sb / SN.PRIMARY / "evaluation_summary.json"))')
rep('    ev3 = json.load(open(sb / "S2_fac_C0_s25_P3_none" / "evaluation_summary.json"))', '    ev3 = json.load(open(sb / SN.P3 / "evaluation_summary.json"))')
rep('"_route_explanations" / "S2_fac_C0_s25_v11" / "route_explanations.csv"', '"_route_explanations" / SN.PRIMARY / "route_explanations.csv"')
rep('    k4 = t6[t6.run == "S2_fac_C0_s25_v11"].iloc[0]', '    k4 = t6[t6.run == SN.PRIMARY].iloc[0]')
rep('    kb = t6[t6.run == "S2_fac_C0_s25_avoid_buf100"].iloc[0]', '    kb = t6[t6.run == SN.AVOID].iloc[0]')
rep('    A("Only schools, a health sub-centre and an anganwadi exist as priority facilities in the data (TGRAC layers). No government-building layer exists, so no such class is detected or prioritised.")',
    '    exf = pd.read_csv(ver / "excluded_facilities.csv").iloc[0]\n    A("The TGRAC layers hold four priority facilities: two schools, a health sub-centre and an anganwadi. The anganwadi was excluded from the planning layers, CSVs and maps at the project owner\'s request (`inputs/EXCLUSIONS.md`), so the deliverables cover three. No government-building layer exists, so no such class is detected or prioritised.")')
a = s.index('    A("**Finding.** %d of the 4 priority facilities')
b = s.index('    A("Building candidates inside the boundary against Google Open Buildings v3')
s = s[:a] + '''    A("**Finding.** All %d retained facilities are supported by a detected footprint and corroborated by an independent Open Buildings polygon. "
      "The anganwadi (Damarakunt-I) was excluded because its TGRAC coordinate lies %.0f m from the nearest detected footprint and %.0f m from the nearest Open Buildings polygon (record kept in `excluded_facilities.csv`); "
      "this does not show the anganwadi is absent from the village, only that its position is unsupported. Until a verified location exists the plan serves 3 of the 4 priority facilities. "
      "The sub-centre has two TGRAC records %.0f m apart; the position in the priority layer is the health-layer record, and both records are near a footprint, so proximity alone cannot say which is right." % (
          nsup, float(exf.nearest_footprint_m), float(exf.nearest_open_buildings_m), 235.7))
    A("")
''' + s[b:]
a = s.index('    A("A first look at the project\'s own Esri crop')
b = s.index('    A("## 4. Road connectivity and the C0002 exception")')
s = s[:a] + '    A("The excluded anganwadi is not part of this audit; its record and the reason are in `inputs/EXCLUSIONS.md`.")\n    A("")\n' + s[b:]
rep('"(ii) *Anganwadi correction:* no verified corrected location exists. The coordinate is flagged unsupported and was left unchanged; Map 5 marks the nearest Open Buildings polygon only as a lead for the visual audit. "',
    '"(ii) *Anganwadi:* excluded from the planning layers and maps at the project owner\'s request (`inputs/EXCLUSIONS.md`), not corrected; no verified location exists. "')
rep('anganwadi coordinate off; 163 targets', 'anganwadi excluded (unsupported coordinate); 163 targets')
rep('| Anganwadi flagged unsupported; open |', '| Anganwadi excluded; verified location still needed |')
k = s.index("\nimport ") if "\nimport " in s else 0
s = s[:k] + IMP + s[k:]
open(ROOT + r"\src\reporting\make_chapter.py", "w", encoding="utf-8").write(s)
print("patched")
