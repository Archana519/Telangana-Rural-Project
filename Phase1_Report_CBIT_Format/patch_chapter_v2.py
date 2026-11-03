"""One-off patch (kept for provenance): adds the economic subsection, visual-audit subsection and stage-wise status audit to make_chapter.py,
and the economic table to comparison_tables.py and run_final_package.py."""
import re

# ---------------------------------------------------------------- make_chapter.py
p = r"D:\Telangana_Rural_Project\src\reporting\make_chapter.py"
s = open(p, encoding="utf-8").read()


def rep(a, b):
    global s
    assert s.count(a) == 1, (s.count(a), a[:80])
    s = s.replace(a, b)


rep('    ev = json.load(open(sb / "S2_fac_C0_s25_v11" / "evaluation_summary.json"))',
    '    t5 = pd.read_csv(cmp_ / "table5_economic_material_impact.csv")\n    t5b = pd.read_csv(cmp_ / "table5b_material_quantities.csv")\n    va = pd.read_csv(O / "visual_audit" / "visual_grounding_table.csv", dtype=str)\n    ev = json.load(open(sb / "S2_fac_C0_s25_v11" / "evaluation_summary.json"))')

# visual audit subsection at the end of section 3 (before section 4)
rep('    A("## 4. Road connectivity and the C0002 exception")',
    '''    A("### Visual audit protocol for the priority facilities")
    A("Agreement checks cannot replace looking at the imagery. `outputs/visual_audit/` holds a Visual Grounding Table, a Google Earth KML and plain and annotated 200 m imagery crops for each facility. "
      "The measured columns (model latitude/longitude, offset to the nearest detected footprint and Open Buildings polygon, roof area, distance to the nearest TGRAC road, compound membership) are filled from project files. "
      "The observation columns (feature at the pin, matching-feature offset, roof size, playground or open ground, road access, corrected coordinate, imagery date, decision) are **empty on purpose**: they need a person with Google Earth Pro, and the decision rule is fixed in `protocol.md` "
      "(confirm within 20 m, relocate within 200 m, otherwise reject). No facility is visually confirmed by this project yet. A government-building row exists but cannot be audited, because no such layer is in the data.")
    A("")
    A(md(va[["facility_id", "name", "model_lat", "model_lon", "nearest_detected_footprint_m", "nearest_open_buildings_m", "distance_to_nearest_TGRAC_road_m", "agreement_verdict"]]))
    A("")
    A("A first look at the project's own Esri crop (undated imagery) at the anganwadi coordinate shows open scrub and fallow land with no roof inside the 100 m window; the nearest Open Buildings polygon is 126 m away and is small (30 m2). "
      "This is a preliminary reading by the analyst, not the Google Earth audit, and the facility should be relocated or rejected only after that audit.")
    A("")
    A("## 4. Road connectivity and the C0002 exception")''')

# economic subsection after the C2 ablation paragraph (before section 6)
rep('    A("## 6. Connectivity rates and constraint checks")',
    '''    A("### Economic and material impact analysis (illustrative)")
    ra, rb = t5.iloc[0], t5.iloc[1]
    A("*This subsection is a parametric estimate. The project holds no road width, cross-section, soil or rate data, so the rate and the pavement section are assumptions listed in `inputs/economic_assumptions.json`. "
      "The rate of Rs 75 lakh per km is the figure supplied by the project owner as a PMGSY-based value; it was not checked against a PMGSY document or a State Schedule of Rates. "
      "It is not an engineering estimate, not a bill of quantities and not a claim about real construction cost. The routes are planning alternatives and are mostly short house lanes (about 31 m per house); "
      "a rate for habitation-connectivity roads may not apply to them, and the programme's eligibility for internal village lanes should be checked.*")
    A("")
    A("**Which length is the baseline.** The independent routes sum to %.0f m, but %.0f m of that is grid edges used by several houses. A shared edge would be built once even without optimisation, so the fair baseline is the unique length of the independent routes, %.0f m. "
      "The proposed network is %.0f m. The saving is therefore **%.0f m (%.1f%%)**, not the %.0f m (4.91 km) obtained by subtracting the shared network from the double-counted total. "
      "The 4.91 km figure is %.1f times the real saving and should not be quoted as a saving." % (
          rb.baseline_len_m, rb.baseline_len_m - ra.baseline_len_m, ra.baseline_len_m, ra.proposed_len_m, ra.length_saving_m, ra.length_saving_pct, rb.length_saving_m, rb.length_saving_m / ra.length_saving_m))
    A("")
    A(md(t5[["baseline_basis", "baseline_len_m", "proposed_len_m", "length_saving_m", "length_saving_pct", "baseline_cost_central_Rs_lakh", "proposed_cost_central_Rs_lakh", "cost_saving_low_Rs_lakh", "cost_saving_central_Rs_lakh", "cost_saving_high_Rs_lakh"]]))
    A("")
    A("At Rs 75 lakh/km the cost of the independent routes (basis A) is about Rs %.0f lakh and of the proposed network about Rs %.0f lakh, a saving of about **Rs %.0f lakh (Rs %.2f crore)**, within Rs %.0f to %.0f lakh for rates of Rs 60 to 90 lakh/km. "
      "The basis-B figure of Rs %.0f lakh (Rs %.2f crore) follows from the double-counted length and is shown only so the two can be compared; it overstates the saving." % (
          ra.baseline_cost_central_Rs_lakh, ra.proposed_cost_central_Rs_lakh, ra.cost_saving_central_Rs_lakh, ra.cost_saving_central_Rs_lakh / 100, ra.cost_saving_low_Rs_lakh, ra.cost_saving_high_Rs_lakh,
          rb.cost_saving_central_Rs_lakh, rb.cost_saving_central_Rs_lakh / 100))
    A("")
    A("Material conservation follows from the length saving and one assumed cross-section (3.75 m carriageway, 150 mm sub-base, 150 mm WBM, 20 mm bituminous surface, 5.0 m formation, 0.30 m average earthwork depth, 1.30 loose factor, 2.0 kg/m2 bitumen). "
      "Quantities for each length, and the saving on basis A, are:")
    A("")
    A(md(t5b))
    A("")
    A("| Material saved (basis A, %.0f m) | Quantity |\\n|---|---|\\n| Aggregate for WBM and surfacing, loose | %.0f m3 |\\n| Sub-base (GSB) material, loose | %.0f m3 |\\n| Earthwork | %.0f m3 |\\n| Bitumen | %.1f t |" % (
        ra.length_saving_m, ra.saving_aggregate_loose_m3, ra.saving_gsb_subbase_loose_m3, ra.saving_earthwork_m3, ra.saving_bitumen_t))
    A("")
    A("These quantities scale linearly with length because a single cross-section is assumed; they ignore drainage and cross-drainage works, side slopes, utilities, land, supervision and escalation. Replace the assumptions with State Schedule of Rates and a design section before any financial use.")
    A("")
    A("## 6. Connectivity rates and constraint checks")''')

# stage-wise status
rep('    A("## 9. Limitations addressed by automation and what remains")',
    '''    A("## 9. Stage-wise status and limitation audit")
    A("| Stage | Status | Limitation | Automated rule or check | Outcome |\\n|---|---|---|---|---|\\n"
      "| 1 Detect | Reused input, verified by hash | Detections unverified; no ground truth; anganwadi coordinate off; 163 targets are not a house count | Agreement checks with fixed thresholds; quality classes carried through planning; Visual Grounding Table prepared | **Bounded and reported, not overcome.** Real accuracy needs labelled buildings and the Google Earth audit |\\n"
      "| 2 Model terrain | Verified input | 30 m DEM interpolated to 10 m; roads 44.7%% outside the polygon; boundary not independently verified; imagery licence and date unresolved | Hash checks on all inputs; masks and counts reproduced by diagnostics; caveats printed on maps | **Bounded.** Resolution trade-off is a fundamental limit; licence unresolved |\\n"
      "| 3 Plan | Run, reproduced exactly (27 runs, 405 metrics) | Greedy heuristic, not optimal; ordinal costs | Fixed planner hash; fresh run folder per execution; comparison with the reference run | **Overcome for reproducibility**; optimality not claimed |\\n"
      "| 4 Stress-test | Run | Omissions and additions are synthetic; real detector error not measured | Seeded runs, per-routed-target metrics | **Bounded**; label-based error propagation not started |\\n"
      "| 5 Validate | Run | C0002 off the main raster component; two audits rate it differently | Line-topology connectivity with 15 m snapping; acceptance validator; connectivity audit v2; per-route explanations | **Reporting resolved**; physical road not verified; the planner was deliberately not changed |")
    A("")
    A("## 9b. Limitations addressed by automation and what remains")''')
open(p, "w", encoding="utf-8").write(s)

# ---------------------------------------------------------------- comparison_tables.py: append economic section
p = r"D:\Telangana_Rural_Project\src\reporting\comparison_tables.py"
s = open(p, encoding="utf-8").read()
rep('    (out / "comparison_report.md").write_text("\\n".join(md), encoding="utf-8")',
    '    ee = out / "economic_impact.md"\n    if ee.exists():\n        md += ["## Table 5. Economic and material impact (illustrative; assumptions in inputs/economic_assumptions.json)", "", ee.read_text(encoding="utf-8").split("\\n", 2)[2], ""]\n    (out / "comparison_report.md").write_text("\\n".join(md), encoding="utf-8")')
open(p, "w", encoding="utf-8").write(s)

# ---------------------------------------------------------------- run_final_package.py
p = r"D:\Telangana_Rural_Project\src\run_final_package.py"
s = open(p, encoding="utf-8").read()
rep('    step("final maps 1-4"',
    '    step("visual audit protocol (table, KML, crops)", [PY, SRC / "validation" / "visual_audit_protocol.py", "--out", O / "visual_audit"])\n    step("economic and material impact (illustrative)", [PY, SRC / "reporting" / "economic_impact.py", "--stageb-root", sb, "--out", O / "final_comparison"])\n    step("final maps 1-4"')
rep('("verification", "connectivity", "final_maps", "final_comparison", "final_package")', '("verification", "connectivity", "visual_audit", "final_maps", "final_comparison", "final_package")')
rep('           "| 7 | Comparison tables (CSV and Markdown) | `outputs/final_comparison/` |",',
    '           "| 7 | Comparison tables incl. Table 5 economic and material impact (CSV and Markdown) | `outputs/final_comparison/` |",\n           "| 7b | Visual audit protocol, Visual Grounding Table, Google Earth KML, crops | `outputs/visual_audit/` |",')
open(p, "w", encoding="utf-8").write(s)
print("patched")
