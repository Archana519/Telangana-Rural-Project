"""One-off patch: bring build_report.py up to date with the real-data Stage B runs (run_20261029_01)."""
s = open('build_report.py', encoding='utf-8').read()

def rep(a, b):
    global s
    assert s.count(a) == 1, a
    s = s.replace(a, b)

rep('"progress", "s2", "runs"]', '"progress", "s2", "runs", "pen", "unc"]')

# abstract
rep('para(runs(TL(111).replace("\\\\medskip\\\\noindent", "").strip()))',
'''para("The planned experiments were then run on the real Damarakunta data. Removing the building penalty shortens the unique network from 5,138 m to 4,762 m (7.3%) but doubles the routes that cross other building footprints (29 to 57). Across 20 synthetic omit/add perturbation runs (10% and 20% of targets, five seeds each) every placed target was still routed and the unique length per routed target stayed between 30.5 m and 34.2 m (baseline 31.5 m). The perturbations are sensitivity probes, not measured segmentation error.")
para(runs(TL(111).replace("\\\\medskip\\\\noindent", "").strip()))''')

# penalty sentence
rep('multiplied by $m$."))))',
    'multiplied by $m$."),\n    ("are planned runs.", "are reported in Section 9.3."))))')

# 6.6 and chapter 7 validation
rep('H(2, "6.6", "Sensitivity and Uncertainty Design (C1)"); tp(392)',
'''H(2, "6.6", "Sensitivity and Uncertainty Design (C1)")
para("Two perturbations are defined. Omit removes a random fraction (0.10 or 0.20) of scenario targets and their footprints, representing missed detections. Add inserts synthetic translated copies (15–50 m) of random buildings on valid cells at least 1 m from roads, representing spurious detections; synthetic additions are probes only. Seeds are fixed (20261029–20261033) so runs are reproducible. Both perturbations, with five seeds per setting, and the three penalty variants have been run on the real Damarakunta data; the results are in Sections 9.3 and 9.4. They measure sensitivity to synthetic target changes and not real segmentation error.")''')
rep('''for n, title in ((396, "Scenarios"), (398, "Metrics"), (400, "Baselines"), (402, "Automated validation"), (404, "Environment")):
    tp(n)''',
'''for n, title in ((396, "Scenarios"), (398, "Metrics"), (400, "Baselines")):
    tp(n)
para([("Automated validation. ", {"bold": True}), ("A read-only validator checks required files, manifest hashes, target counts and identifiers, duplicates and missing targets, geometry validity, connectivity, failure reasons, regression against the reference and reproducibility of paired runs. Stage A passed 51 checks with 9 informational notes and 0 warnings or failures. The Stage B audit covered 30 runs (primary scenarios, penalty variants, perturbation runs and paired reruns): 396 PASS, 28 INFO, 0 WARN and 0 FAIL; the INFO rows record the one house route that ends on a disconnected road fragment (Section 9.5).", {})])
tp(404)''')

# progress table
rep('make_table(["Component", "Evidence", "Status"], tex_rows(414, 420), [1.7, 3.8, 1.0], size=10)',
'''prog = tex_rows(414, 420)
prog[3] = ["Penalty variants P1--P3", "Run on real data for S2 at $25^{\\\\circ}$ (Table 10)", "\\\\impl"]
prog[4] = ["Perturbation runs (omit/add)", "20 runs on real data: omit and add, 10\\\\% and 20\\\\%, five seeds each (Table 11); synthetic probes only", "\\\\impl"]
prog[5] = ["Automated validator and final tables", "30 runs audited: 396 PASS, 28 INFO, 0 WARN, 0 FAIL; final tables written", "\\\\impl"]
make_table(["Component", "Evidence", "Status"], prog, [1.7, 3.8, 1.0], size=10)''')

# results
rep('H(2, "9.3", "Connectivity"); tp(470)',
'''H(2, "9.3", "Building-penalty variants")
para("Table 10 compares the baseline penalty (all three quality classes, multiplier 4) with P1 (plausible only), P2 (plausible and review) and P3 (no penalty), all for S2 at the 25° limit with 163 targets routed in every run. Removing the penalty gives the shortest unique network, 4,761.7 m, which is 7.3% shorter than the baseline 5,137.7 m, but 57 routes then cross other footprints against 29 for the baseline; P1 and P2 cross 47 and 45. Penalising every candidate class costs between 4.6% and 7.3% more unique length than P1 or P3 in exchange for the fewest footprint crossings. The saving column compares each run with independent routes planned under the same penalty, so it is not comparable across rows as a length measure. Footprint classes are model-derived and a route that avoids them is not evidence that real compounds are avoided.")
table_caption("pen", "Building-penalty variants (S2, 25° slope limit, 163 targets).")
make_table(["Variant", "Penalised classes", "Unique length (m)", "Saving (%)", "Routes crossing other footprints", "Length in other footprints (m)", "Penalised-cell length (m)"],
           [["Baseline", "Plausible, review, unresolved merge (x4)", "5,137.7", "23.9", "29", "216.1", "586.6"],
            ["P1", "Plausible (x4)", "4,900.8", "26.2", "47", "571.6", "244.1"],
            ["P2", "Plausible, review (x4)", "4,952.4", "26.4", "45", "567.8", "374.1"],
            ["P3", "None (x1)", "4,761.7", "31.2", "57", "666.0", "0.0"]],
           [0.7, 1.5, 0.8, 0.8, 0.9, 0.9, 0.9], size=9)
H(2, "9.4", "Sensitivity to target-set perturbations")
para("Table 11 summarises 20 perturbation runs on the S2 scenario. All routed every target that could be placed, with no failures. The unique length per routed target stayed between 30.5 m and 34.2 m over the 20 runs, against 31.5 m for the unperturbed baseline (5,137.7 m over 163 targets). On targets common to the base and perturbed runs, the mean change in route length per seed ranged from −2.3 m to +2.0 m and 96% to 99% of targets kept the same attachment class (road, facility or house route). The widest spread in total unique length is for 20% omission (3,961 m to 4,450 m), because removing a target can remove branches that other houses were sharing. In nine of the ten add runs not all requested synthetic buildings could be placed (for example 14 of 16), which the run checks log as a warning. A paired rerun of one omit and one add run reproduced the original results. These perturbations are synthetic sensitivity probes; they do not measure how real segmentation errors would change the plan.")
table_caption("unc", "Perturbation runs, mean over five seeds (range in brackets).")
make_table(["Perturbation", "Targets routed", "Unique length (m)", "Length per routed target (m)", "Routes crossing other footprints", "Same attachment class (%)"],
           [["Add 10%", "177.4", "5,564.5 (5,462.6–5,609.7)", "31.4", "33.0", "99"],
            ["Add 20%", "190.6", "5,934.9 (5,847.8–5,978.0)", "31.1", "37.2", "97"],
            ["Omit 10%", "147.0", "4,745.0 (4,589.8–4,851.6)", "32.3", "24.0", "98"],
            ["Omit 20%", "130.0", "4,256.4 (3,961.1–4,450.3)", "32.7", "20.2", "97"]],
           [1.0, 0.8, 1.7, 1.0, 1.0, 0.8], size=9)
H(2, "9.5", "Connectivity")
para("One house route does not end on the main road component. It is candidate 2 (house H0001, quality class review, more than 20 m from the nearest road): its route is 105.9 m long and starts 95.6 m from the road layer, but it ends on a small TGRAC road fragment (component 10, 5 grid cells, component 11 in the 10° runs) that is disconnected from the main component inside the planning grid. The validator records it as an information item in all eight affected runs. Whether this fragment connects to the main road outside the grid, or whether the road layer is missing a link, is not known and needs checking against imagery.")''')
rep('H(2, "9.4", "Discussion"); tp(478)',
'''H(2, "9.6", "Discussion")
para("The results support C2 as a working, reproducible planner at planning level: shared-edge accounting lowers unique length and the building penalty trades some length for fewer footprint crossings. The C1 experiments are now run on the real village, and they show the plan is fairly stable under synthetic omissions and additions, but they do not measure real segmentation error. The results do not support claims about cost in rupees, constructability or real-world connectivity, and C3 is untested.")''')

# limitations / future / conclusion
rep('range(483, 493)])',
    '''range(483, 493)] +
           ["In nine of the ten add-perturbation runs some requested synthetic buildings could not be placed, so the perturbation size is slightly below the nominal fraction."])''')
rep('list_items([re.sub(r"^\\\\item\\s*", "", TL(n).strip()) for n in range(483, 493)]',
    'list_items([re.sub(r"^\\\\item\\s*", "", TL(n).strip()) for n in range(483, 493)]')
rep('''list_items([re.sub(r"^\\\\item\\s*", "", TL(n).strip()) for n in range(497, 504)], labels=["%d." % i for i in range(1, 8)])''',
'''list_items([
    "Replace the synthetic perturbations by label-based error propagation: build reference labels for a village subset and measure how real segmentation errors change the plan (C1).",
    "Check the disconnected road fragment near candidate 2 against imagery and the road layer, and review the maps and inset boxes visually.",
    "Verify facility identities against official registries and obtain imagery metadata.",
    "Document the DEM and land-cover sources and test a finer DEM where available.",
    "Decide whether a second village allows an honest test of C3.",
    "Complete the full-text reading of the reviewed papers and the novelty comparison with prior art.",
    "Add more IEEE Transactions papers to the literature review where the guide requires them."], labels=["%d." % i for i in range(1, 8)])''')
rep('tp(507)', '''para(runs(fix(507, ("the C1 experiments and C3 transfer remain to be done, and the Phase-II plan targets them together with verification of data sources.",
    "the C1 experiments are synthetic sensitivity probes without real labels, C3 transfer remains to be done, and the Phase-II plan targets both together with verification of data sources."))))''')
open('build_report.py', 'w', encoding='utf-8').write(s)
print('ok')
