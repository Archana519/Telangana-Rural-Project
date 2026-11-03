"""One-off patch (kept for provenance): brings the Phase-I report in line with the final deliverables - anganwadi exclusion note, building-avoiding network and
illustrative economics (9.7), and the 'Methodological Limitations and Future Scope' section (10.3, from src/reporting/limitations_text.py)."""
p = r"D:\Telangana_Rural_Project\Phase1_Report_CBIT_Format\build_report.py"
s = open(p, encoding="utf-8").read()


def rep(a, b):
    global s
    assert s.count(a) == 1, (s.count(a), a[:90])
    s = s.replace(a, b)


rep('"pen", "unc", "recon", "evid", "applit"]', '"pen", "unc", "recon", "avoid", "econ", "evid", "terms", "applit"]')

rep('# ---------- 1 Introduction\n', '''import sys as _sys
_sys.path.insert(0, r"D:\\Telangana_Rural_Project\\src\\reporting")
import csv as _csv
import limitations_text as LT


def _clean(t):
    return t.replace("**", "").replace("`", "")


def md_to_doc(text, prefix, widths_by_cols, key):
    """small Markdown subset (### headings, one table, '- ' and '1. ' lists, paragraphs) -> report elements; headings numbered prefix.k"""
    lines = text.split("\\n")[1:]
    i, k, para_buf = 0, 0, []
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("### "):
            k += 1
            title = ln[4:].split(" ", 1)[1]
            H(3, "%s.%d" % (prefix, k), title)
        elif ln.startswith("|"):
            blk = []
            while i < len(lines) and lines[i].startswith("|"):
                blk.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            rows = [[_clean(c) for c in r] for r in blk[2:]]
            if key:
                table_caption(key[0], key[1])
            make_table([_clean(c) for c in blk[0]], rows, widths_by_cols[len(blk[0])], size=7.5)
            continue
        elif ln.startswith("- ") or ln[:3] in ("1. ", "2. ", "3. ", "4. ", "5. ", "6. "):
            items, labs = [], []
            while i < len(lines) and (lines[i].startswith("- ") or lines[i][:3] in ("1. ", "2. ", "3. ", "4. ", "5. ", "6. ")):
                if lines[i].startswith("- "):
                    items.append(_clean(lines[i][2:])); labs.append("\\u2022")
                else:
                    items.append(_clean(lines[i][3:])); labs.append(lines[i][:2])
                i += 1
            list_items(items, labels=labs)
            continue
        elif ln.strip():
            para(runs(_clean(ln)))
        i += 1


# ---------- 1 Introduction
''')

rep('table_caption("dsunits", "Dataset inventory with units, verified counts, source and status.")',
    'table_caption("dsunits", "Dataset inventory with units, verified counts, source and status.")\n'
    'para(runs("Update of 31 October 2026: at the project owner\'s request the anganwadi (facility 1702300, Damarakunt-I) is excluded from the final planning layers, tables and maps because its TGRAC coordinate lies 371 m from the nearest detected footprint (inputs/EXCLUSIONS.md). Rows and results in this report that list four facilities describe the verified four-facility baseline run; the final deliverables use three facilities."))')

rep('para(runs(sv))\n', 'para(runs(sv))\npara(runs("The facility rows of Table @T:s2@ and the combined lengths belong to the verified four-facility baseline run. Without the anganwadi the facility routes total 142.5 m and the combined unique length is 5,280.2 m; the 163 house routes (5,137.7 m) are unchanged.".replace("@T:s2@", REF["tab:s2"])))\n')

rep('H(1, "10", "Limitations and Threats to Validity")', '''H(2, "9.7", "Building-Avoiding Network and Illustrative Economics")
def _rd(path):
    try:
        return list(_csv.DictReader(open(path, encoding="utf-8-sig")))
    except Exception:
        return []
_t6 = _rd(r"D:\\Telangana_Rural_Project\\outputs\\final_comparison\\table6_obstacle_avoidance.csv")
_t5 = _rd(r"D:\\Telangana_Rural_Project\\outputs\\final_comparison\\table5_economic_material_impact.csv")
if _t6:
    para(runs("Strict no-go zones around building footprints were tried first and failed: every house point lies inside its own blocked cell, so all 163 house routes failed. Footprints buffered by 7.1 m with a large penalty were then used. All 163 houses are routed, but the routes do not completely skirt buildings: the remaining crossings occur mostly where a target starts among touching buildings. Table @T:avoid@ gives the effect (three retained facilities). The effect saturates by a penalty of x20.".replace("@T:avoid@", REF["tab:avoid"])))
    table_caption("avoid", "Building avoidance: length and footprint crossings (house routes; anganwadi excluded).")
    make_table(["Scenario", "Houses routed", "House unique length (m)", "Saving vs independent (%)", "Routes crossing other footprints", "Crossing length (m)", "Facility routes (m)"],
               [[r["scenario"], r["houses_routed"], r["house_unique_len_m"], r["saving_vs_independent_pct"], r["house_routes_crossing_other_footprints"], r["crossing_len_m"], r["facility_unique_len_m"]] for r in _t6],
               [1.5, 0.6, 0.8, 0.8, 0.9, 0.7, 0.7], size=8)
if _t5:
    a_, b_ = _t5[0], _t5[1]
    para(runs("Illustrative economics (assumptions, not project data: Rs 75 lakh/km supplied by the project owner and not checked against PMGSY or a State Schedule of Rates; one assumed pavement section). The fair baseline is the unique length of the independent routes (%s m), not their sum (%s m), because a shared edge is built once. The saving is %s m (%s%%), about Rs %s lakh at the assumed rate. Subtracting the shared network from the double-counted sum gives %s m (4.91 km), which overstates the saving about three times and is not a saving. These figures are not an engineering estimate." % (
        a_["baseline_len_m"], b_["baseline_len_m"], a_["length_saving_m"], a_["length_saving_pct"], a_["cost_saving_central_Rs_lakh"], b_["length_saving_m"])))
    table_caption("econ", "Illustrative length and cost saving of the shared network (Rs 75 lakh/km assumed).")
    make_table(["Baseline", "Baseline length (m)", "Shared network (m)", "Length saving (m)", "Saving (%)", "Cost saving (Rs lakh)"],
               [[r["baseline_basis"], r["baseline_len_m"], r["proposed_len_m"], r["length_saving_m"], r["length_saving_pct"], r["cost_saving_central_Rs_lakh"]] for r in _t5],
               [2.2, 0.8, 0.8, 0.8, 0.6, 0.8], size=8)
H(1, "10", "Limitations and Threats to Validity")''')

rep('H(1, "11", "Future Work and Phase-II Plan")', '''H(2, "10.3", "Methodological Limitations and Future Scope")
md_to_doc(LT.TEXT, "10.3", {4: [1.2, 1.7, 2.2, 1.5]}, ("terms", "Data sources, attribution and recorded usage terms (none confirmed in writing)."))
H(1, "11", "Future Work and Phase-II Plan")''')
open(p, "w", encoding="utf-8").write(s)
print("patched")
