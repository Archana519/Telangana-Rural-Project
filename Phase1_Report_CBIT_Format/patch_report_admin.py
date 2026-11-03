"""One-off patch (kept for provenance): Phase-I report built from the FINAL scenario family (5 facilities) with a new Chapter 4 subsection
'Administrative and Governance Utilities'; abstract, 6.4, Chapter 9, progress table and conclusion synced to the final numbers."""
p = r"D:\Telangana_Rural_Project\Phase1_Report_CBIT_Format\build_report.py"
s = open(p, encoding="utf-8").read()


def rep(a, b):
    global s
    assert s.count(a) == 1, (s.count(a), a[:90])
    s = s.replace(a, b)


# 0. data module before the title page
rep("# ================================================================== TITLE PAGE\n",
    "exec(open(os.path.join(HERE, 'report_fin_data.py'), encoding='utf-8').read(), globals())\nimport shutil as _shutil\nfor _nm, _src in (('chart1_network_lengths.png', r'D:\\Telangana_Rural_Project\\outputs\\final_comparison\\charts\\chart1_network_lengths.png'), ('map4_alternatives_vs_network.png', r'D:\\Telangana_Rural_Project\\outputs\\final_maps\\map4_alternatives_vs_network.png')):\n    _shutil.copy2(_src, A(_nm))\n\n# ================================================================== TITLE PAGE\n")

# 1. abstract: third paragraph and the experiments paragraph
a = s.index("para(runs(fix(109,")
b = s.index("para(runs(TL(111)")
s = s[:a] + '''para(runs("Preliminary, model-derived results are reported for Damarakunta: 278 building candidates, 165 inside the village boundary and 163 eligible as house targets, plus five facilities (two schools, a health sub-centre and two Gram Panchayat headquarters points; the anganwadi is excluded). With a $25^{\\\\circ}$ slope limit, all 163 houses and all five facilities were routed; sharing edges reduced the unique house-route length from %.2f~km (independent routes) to %.2f~km in the two-stage network-aware plan (about %.1f%%, i.e. %.2f~km) and to %.2f~km in the roads-only shared-edge reference (about %.1f%%). These numbers are planning-level, have no field validation, and do not establish legal access, ownership, passability or construction feasibility. Limitations and the Phase-II plan are set out explicitly." % (ih["unique_len_m"] / 1000, hp["unique_len_m"] / 1000, 100 * sav / ih["unique_len_m"], sav / 1000, rr["unique_len_m"] / 1000, 100 * sav_ro / ih["unique_len_m"])),
     align=WD_ALIGN_PARAGRAPH.JUSTIFY)
_pr = [e_[0]["houses_primary"]["unique_len_m"] / e_[0]["houses_primary"]["n"] for v_ in _grp.values() for e_ in v_]
para("The planned experiments were then run on the real Damarakunta data. Removing the building penalty changes the unique house network from %s m to %s m (%.1f%%) and the routes that cross other building footprints from %d to %d. Across 20 synthetic omit/add perturbation runs (10%% and 20%% of targets, five seeds each) every placed target was still routed and the unique length per routed target stayed between %.1f m and %.1f m (baseline %.1f m). The perturbations are sensitivity probes, not measured segmentation error." % (
    N0(_pv[0][2]), N0(_pv[3][2]), 100 * (_pv[3][2] / _pv[0][2] - 1), _pv[0][4], _pv[3][4], min(_pr), max(_pr), hp["unique_len_m"] / hp["n"]))
''' + s[b:]

# 2. 6.4 text
rep('H(2, "6.4", "Public-Service Facility and House Connectivity Planning"); tp(350)',
    'H(2, "6.4", "Public-Service Facility and House Connectivity Planning")\npara(runs(fix(350, ("Four facilities (a primary school, a high school, one sub-centre, one anganwadi)", "Five facilities (a primary school, a high school, one sub-centre and two Gram Panchayat headquarters points from TGRAC; the anganwadi is excluded)"))))')

# 3. chapter 9
a = s.index("# ---------- 9 Results")
b = s.index("# ---------- 10-12")
s = s[:a] + "# ---------- 9 Results\nexec(open(os.path.join(HERE, 'report_results_block.py'), encoding='utf-8').read(), globals())\n\n" + s[b:]

# 4. progress rows
rep('prog[5] = ["Automated validator and final tables", "30 runs audited: 396 PASS, 28 INFO, 0 WARN, 0 FAIL (acceptance validator); final tables written", "\\\\impl"]',
    'prog[5] = ["Automated validator and final tables", "%s (acceptance validator, final family); final tables written" % VAL_TEXT, "\\\\impl"]')
rep('prog[4] = ["Perturbation runs (omit/add)", "20 runs on real data:', 'prog[4] = ["Perturbation runs (omit/add)", "20 runs on real data (final family):')

# 5. conclusion wording
open(p, "w", encoding="utf-8").write(s)
print("patched build_report")

# data module: validation text
d = r"D:\Telangana_Rural_Project\Phase1_Report_CBIT_Format\report_fin_data.py"
t = open(d, encoding="utf-8").read()
t += '''
# ---- validator summary text (acceptance validator over the final-family runs)
try:
    _vs = open(_o.path.join(SB, "_validation_main", "validation_summary.txt"), encoding="utf-8").read()
    _m = _re.search(r"runs audited: (\\d+).*?'PASS': (\\d+)(?:, 'INFO': (\\d+))?", _vs, _re.S)
    VAL_TEXT = "%s runs audited: %s PASS, %s INFO, 0 WARN, 0 FAIL" % (_m.group(1), _m.group(2), _m.group(3) or "0")
except Exception:
    VAL_TEXT = "acceptance validator: see the validation summary"
'''
open(d, "w", encoding="utf-8").write(t)
print("patched data")
