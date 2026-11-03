"""One-off patch: revision 2 of build_report.py (literature 45/35, stage architecture, dataset inventory,
connectivity reconciliation, evidence-status table, verified references). Run once on the revision-1 build_report.py."""
s = open("build_report.py", encoding="utf-8").read()


def rep(a, b):
    global s
    assert s.count(a) == 1, (s.count(a), a[:90])
    s = s.replace(a, b)


# ---- imports, table order, helpers
rep('REF = {"ch:lit": "2", "ch:data": "4", "ch:arch": "5"}',
    'import content_v2 as C\nREF = {"ch:lit": "2", "ch:data": "4", "ch:arch": "5"}')
rep('["contrib", "lit1", "lit2", "datasets", "datasets2", "modules", "progress", "s2", "runs", "pen", "unc"]',
    '["contrib", "lit1", "lit2", "gapmat", "datasets", "datasets2", "dsunits", "modules", "stages", "progress", "s2", "runs", "pen", "unc", "recon", "evid", "applit"]')
rep('def tp(n, **kw):',
    'def X(s):\n    """replace @T:key@ by the table number."""\n    return re.sub(r"@T:(\\w+)@", lambda m: REF["tab:" + m.group(1)], s)\n\n\ndef tp(n, **kw):')

# ---- literature chapter: nothing else to change (text comes from the edited .tex and tables)

# ---- chapter 3: gap matrix after the novelty paragraph
rep('tp(202)\n\n# ---------- 4 Datasets',
    '''tp(202)
table_caption("gapmat", "Research-gap matrix: what the reviewed literature does, what is missing and how the project responds.")
make_table(["Gap", "What the reviewed papers do", "What is missing", "Project response"],
           [[X(c) for c in r] for r in C.GAP_MATRIX], [1.1, 2.0, 1.7, 1.7], size=8)

# ---------- 4 Datasets''')

# ---- chapter 4: verified inventory
rep('make_table(["Dataset", "Reason for selection", "Use"], tex_rows(231, 239), [1.4, 3.7, 1.4], size=10)',
    '''make_table(["Dataset", "Reason for selection", "Use"], tex_rows(231, 239), [1.4, 3.7, 1.4], size=10)
H(2, "4.1", "Verified Counts and Units")
para(runs("Table @T:dsunits@ separates image counts, vector features, candidate buildings, routing targets, raster cells and route alternatives, and gives the source of each count. Counts marked as read from a file were measured on 29 October 2026; LoveDA figures come from its Zenodo record and arXiv abstract. Where the licence or acquisition date is not recorded, the table says so instead of assuming one.".replace("@T:dsunits@", REF["tab:dsunits"])))
table_caption("dsunits", "Dataset inventory with units, verified counts, source and status.")
make_table(["Dataset", "Unit", "Count and size", "Source and link", "Status"], [[X(c) for c in r] for r in C.DS_UNITS], [0.9, 0.7, 2.0, 1.7, 1.4], size=7.5)
H(2, "4.2", "Role of Each Source and What LoveDA Does Not Show")
para(runs("The sources play complementary roles. Imagery gives building candidates; the TGRAC boundary limits the study area; the TGRAC roads give the existing network that routes must reach; land cover and slope give the cost surface; facilities give the first planning group; cadastral parcels and school compounds are used only to flag possible exposure, not ownership. Each also has a weakness: the imagery has no recorded date, the roads are incomplete and extend beyond the boundary, the building candidates are unverified, the DEM is coarse, and the parcel layer does not show legal access."))
para(runs("LoveDA is a public land-cover benchmark with 5,987 images at 0.3 m from three Chinese cities, with urban and rural domains \\\\cite{F05}. It is useful for developing and comparing segmentation methods and for framing the domain-shift question behind C3. It is not a Telangana dataset, and no LoveDA score is evidence of how well buildings or roads are found in Damarakunta. Model results from LoveDA development are therefore not reported here as Damarakunta accuracy."))''')

# ---- chapter 5: figures and stage-by-stage section
rep('figure("arch", "Layered system architecture of the proposed pipeline (arrows show data flow).", "fig_arch.png", 5.6)',
    'figure("arch", "High-level architecture in nine stages. Green: implemented and run; amber: implemented but inputs or evidence unverified or synthetic; grey: planned.", "fig_arch_v2.png", 4.6)')
rep('figure("flow", "Workflow through the 20 modules. Green boxes are implemented in the scripts reviewed; yellow boxes are partial (see Table 6).", "fig_flow.png", 6.0)',
    'figure("flow", "Detailed workflow: inputs, scripts and outputs. Colours as in Figure 1; every box corresponds to a script or output in the project folder.", "fig_flow_v2.png", 4.8)')
rep('H(2, "5.2", "Layer Explanation"); tp(331)',
    '''H(2, "5.2", "Stage-by-Stage Description")
para(runs("The nine stages below follow Figure 1. Each gives inputs, processing, outputs, validation, limitations and the execution status. Table @T:stages@ summarises them. Stages 1 to 8 were run on Damarakunta; Stage 9 has not started.".replace("@T:stages@", REF["tab:stages"])))
table_caption("stages", "Summary of the nine stages (inputs, processing, outputs, validation and status).")
make_table(["Stage", "Inputs", "Processing", "Outputs", "Validation", "Status"], C.STAGE_TABLE, [0.4, 1.4, 1.5, 1.0, 1.3, 1.0], size=7.5)
for num, title, status, inp, proc, outp, val, lim in C.STAGES:
    H(3, num, title)
    for lead, txt in (("Status. ", status), ("Inputs. ", inp), ("Processing. ", proc), ("Outputs. ", outp), ("Validation. ", val), ("Limitations. ", lim)):
        para([(lead, {"bold": True})] + runs(X(txt)))''')

# ---- 7 validation paragraph scope
rep("The Stage B audit covered 30 runs (primary scenarios, penalty variants, perturbation runs and paired reruns): 396 PASS, 28 INFO, 0 WARN and 0 FAIL; the INFO rows record the one house route that ends on a disconnected road fragment (Section 9.5).",
    "The Stage B acceptance validator covered 30 runs (primary scenarios, penalty variants, perturbation runs and paired reruns): 396 PASS, 28 INFO, 0 WARN and 0 FAIL; it rates the one house route that ends on a disconnected road fragment as INFO. A separate connectivity audit (version 2) applies a stricter rule to the same route and reports it as a failure (Section 9.5). The two audits have different scopes and are not interchangeable.")

# ---- 8 progress rows
rep('prog[3] = ["Penalty variants P1--P3", "Run on real data for S2 at $25^{\\\\circ}$ (Table 10)", "\\\\impl"]',
    'prog[1] = ["Stage B runs", "S1 and S2 at $25^{\\\\circ}$ and $10^{\\\\circ}$, plus C1 scenario; per-run acceptance checks have 0 FAIL; connectivity audit v2 reports one failed attachment (C0002)", "\\\\impl"]\nprog[3] = ["Penalty variants P1--P3", "Run on real data for S2 at $25^{\\\\circ}$ (Table %s)" % REF["tab:pen"], "\\\\impl"]')
rep('(Table 11); synthetic probes only", "\\\\impl"]', '(Table %s); synthetic probes only" % REF["tab:unc"], "\\\\impl"]')
rep('prog[5] = ["Automated validator and final tables", "30 runs audited: 396 PASS, 28 INFO, 0 WARN, 0 FAIL; final tables written", "\\\\impl"]',
    'prog[5] = ["Automated validator and final tables", "30 runs audited: 396 PASS, 28 INFO, 0 WARN, 0 FAIL (acceptance validator); final tables written", "\\\\impl"]\nprog.append(["Literature review", "45 IEEE works; 35 IEEE Transactions papers (2020 to 2026) with metadata checked against the DOI registry; full-text reading incomplete", "\\\\partialS"])\nprog.append(["Evidence-status items", "Twelve open items tracked in Table %s" % REF["tab:evid"], "\\\\partialS"])')

# ---- 9.3 / 9.4 hard-coded table numbers
rep('para("Table 10 compares the baseline penalty', 'para("Table %s compares the baseline penalty" % REF["tab:pen"] + "')
rep('para("Table 11 summarises 20 perturbation runs', 'para("Table %s summarises 20 perturbation runs" % REF["tab:unc"] + "')

# ---- 9.5 connectivity
a = s.index('H(2, "9.5", "Connectivity")')
b = s.index('figure("map"')
s = s[:a] + '''H(2, "9.5", "Connectivity")
para(runs(X("Two connectivity definitions are in use and they give different counts. The planner-level check (the route ends on the declared network and the cell graph is connected) holds for all 167 routed targets. The stricter check, that the route ends on the main road component of 6,149 cells, holds for 166 of 167 targets, or 162 of 163 houses. Both statements concern one target, C0002 (candidate 2, house H0001, class review): its route is 105.93 m long, starts 95.58 m from the road layer and ends on a 5-cell road component (component 10; component 11 in the 10 degree runs) that is cut off from the main component inside the planning grid. The target, route length and component are identical in the x4 and x1 runs, so the two penalty configurations do not differ in connectivity. Table @T:recon@ lists the evidence for each statement.")))
table_caption("recon", "Connectivity reconciliation: which run, target and definition each statement refers to.")
make_table(["No.", "Run", "Metric and definition", "Observed", "Evidence file", "Reading"], [[X(c) for c in r] for r in C.RECON], [0.35, 1.0, 1.3, 1.7, 1.0, 1.4], size=7)
para(runs(X("The disconnection is explained in the road-cell and boundary diagnostics as a boundary-truncation effect: the shortest chain of road cells that would join component 10 to the main component has 36 cells, 33 outside the village polygon and 3 inside within 8.4 m of it, and cells outside the polygon are masked as impassable. This is an interpretation of planning-grid evidence. The roads outside the polygon were not checked for existence or usability, the polygon itself was not independently validated, and no route was planned outside it. The audit and acceptance validator classify the same route differently (FAIL and INFO), and the distance from component 10 to the main component differs between two diagnostics (155.24 m and 151.55 m); neither difference is resolved here. The issue is therefore open, not closed.")))
''' + s[b:]

# ---- 10 evidence table and limitations
rep('H(1, "10", "Limitations and Threats to Validity")\nlist_items(',
    '''H(1, "10", "Limitations and Threats to Validity")
H(2, "10.1", "Evidence-Status Table")
para(runs(X("Table @T:evid@ lists each open issue, what is known, what is not, the corrective action and a closure criterion. An issue stays unresolved until the closure criterion is met; describing it in this report does not close it. The Damarakunta completion gate is not approved, and this report is not final.")))
table_caption("evid", "Evidence status of open issues.")
make_table(["Issue (type)", "Known and evidence", "Remaining unknown", "Corrective action and closure criterion", "Status"], [[X(c) for c in r] for r in C.EVIDENCE], [1.3, 1.9, 1.1, 1.8, 0.7], size=7.5)
H(2, "10.2", "Limitations")
list_items(''')

# ---- 11 future work
rep('"Check the disconnected road fragment near candidate 2 against imagery and the road layer, and review the maps and inset boxes visually.",',
    '"Check the road fragment on which target C0002 ends against imagery and the road layer beyond the boundary, and review the maps and inset boxes visually.",')
rep('"Complete the full-text reading of the reviewed papers and the novelty comparison with prior art.",\n    "Add more IEEE Transactions papers to the literature review where the guide requires them."], labels=["%d." % i for i in range(1, 8)])',
    '"Read the full text of the 35 IEEE Transactions papers and extend the novelty comparison with prior art beyond the papers reviewed.",\n    "Run the P3 baseline reproduction and send the imagery licence enquiry."], labels=["%d." % i for i in range(1, 8)])')

# ---- references with volume, number, pages
rep('''    txt = "%s%s“%s,” %s, %s." % (au, ", " if au else "", e.get("title", ""), venue, e.get("year", ""))''',
    '''    pg = e.get("pages", "").replace("--", "–")
    pg = "" if not pg else (", pp. %s" % pg if re.search(r"[-–]", pg) else ", Art. no. %s" % pg)
    vn = (", vol. %s" % e["volume"] if e.get("volume") else "") + (", no. %s" % e["number"] if e.get("number") else "")
    txt = "%s%s“%s,” %s%s%s, %s." % (au, ", " if au else "", e.get("title", ""), venue, vn, pg, e.get("year", ""))''')

# ---- appendix A after the reference list
rep('# ================================================================== TOC / LOT / LOF (front matter, before body)',
    '''import json as _json
lit_ver = [m for m in _json.load(open("lit_verified.json", encoding="utf-8")) if m["qualifies"] and m["key"] in CITE]
lit_ver.sort(key=lambda m: CITE[m["key"]])
H(1, "A", "Verified Bibliographic Details of the 35 IEEE Transactions Papers")
para(runs("Each entry below was checked against its DOI-registry record (Crossref) on 29 October 2026: all authors, journal, volume, issue where given, pages or article number, year and DOI. Every journal is an IEEE Transactions title and every paper was published between 2020 and 2026. Links of the form https://doi.org/DOI lead to the IEEE Xplore page. This verifies the bibliographic record; it does not mean the papers were read in full."))
table_caption("applit", "Verified details of the 35 qualifying IEEE Transactions papers.")
make_table(["Ref.", "Authors", "Journal, volume, pages, year", "DOI"],
           [["[%d]" % CITE[m["key"]], m["authors"].replace("; ", ", "),
             "%s, vol. %s%s, %s, %s" % (m["journal"].replace("IEEE Transactions on", "IEEE Trans."), m["volume"], (", no. " + m["issue"]) if m["issue"] else "", ("pp. " + m["pages"]) if "-" in m["pages"] else ("art. no. " + m["pages"]), m["year"]),
             m["doi"]] for m in lit_ver],
           [0.4, 2.3, 2.3, 1.5], size=7)

# ================================================================== TOC / LOT / LOF (front matter, before body)''')

open("build_report.py", "w", encoding="utf-8").write(s)
print("patched")
