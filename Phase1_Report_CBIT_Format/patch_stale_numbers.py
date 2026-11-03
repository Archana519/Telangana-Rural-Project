"""One-off patch (kept for provenance): static numbers in generator texts replaced by data-driven or generic wording (final family, 5 facilities)."""
ROOT = r"D:\Telangana_Rural_Project\\"


def patch(rel, pairs):
    path = ROOT + rel.replace("/", "\\")
    s = open(path, encoding="utf-8").read()
    for a, b in pairs:
        assert s.count(a) == 1, (rel, s.count(a), a[:80])
        s = s.replace(a, b)
    open(path, "w", encoding="utf-8").write(s)


patch("src/reporting/economic_impact.py", [
    ("Basis B (%.0f m, 4.91 km) subtracts", "Basis B (%.0f m, %.2f km) subtracts"),
    ("overstates the saving by about %.1f times. \"", "overstates the saving by about %.1f times. \""),
])
s = open(ROOT + r"src\reporting\economic_impact.py", encoding="utf-8").read()
i = s.index("Reading: the quotable saving is basis A.")
j = s.index("% (", i)
# add the km value as the second argument of that formatted string
k = s.index("L[\"B_independent_total\"] - L[\"proposed\"]", j)
s = s[:k] + "L[\"B_independent_total\"] - L[\"proposed\"], (L[\"B_independent_total\"] - L[\"proposed\"]) / 1000, " + s[k + len("L[\"B_independent_total\"] - L[\"proposed\"], "):]
open(ROOT + r"src\reporting\economic_impact.py", "w", encoding="utf-8").write(s)

patch("src/reporting/make_chapter.py", [
    ("not the %.0f m (4.91 km) obtained by subtracting", "not the %.0f m (%.2f km) obtained by subtracting"),
    ("The 4.91 km figure is %.1f times the real saving", "The %.2f km figure is %.1f times the real saving"),
    ("ra.length_saving_pct, rb.length_saving_m, rb.length_saving_m / ra.length_saving_m))", "ra.length_saving_pct, rb.length_saving_m, rb.length_saving_m / 1000, rb.length_saving_m / 1000, rb.length_saving_m / ra.length_saving_m))"),
    ("crossings bounded (29 to 20 routes), not eliminated", "crossings bounded (counts in Table 6), not eliminated"),
])
patch("src/reporting/make_charts.py", [
    ("the double-counted 4.91 km would overstate it about 3 times.", "the double-counted total minus the shared network (%.2f km) would overstate it about %.1f times."),
])
s = open(ROOT + r"src\reporting\make_charts.py", encoding="utf-8").read()
i = s.index("the double-counted total minus the shared network")
j = s.index("rate[\"central\"], ra.length_saving_m, ra.length_saving_pct", i)
s = s[:j] + "rate[\"central\"], ra.length_saving_m, ra.length_saving_pct, t5.iloc[1].length_saving_m / 1000, t5.iloc[1].length_saving_m / ra.length_saving_m" + s[j + len("rate[\"central\"], ra.length_saving_m, ra.length_saving_pct"):]
open(ROOT + r"src\reporting\make_charts.py", "w", encoding="utf-8").write(s)

patch("src/reporting/limitations_text.py", [
    ("for example the 23.9% unique-length saving, must not be quoted as general", "for example the unique-length saving of the shared network, must not be quoted as general"),
    ("- Building avoidance is bounded, not complete: 20 of 163 house routes still cross a neighbouring footprint, mostly where a target starts among touching buildings.",
     "- Building avoidance is bounded, not complete: some house routes still cross a neighbouring footprint (counts in Table 6), mostly where a target starts among touching buildings."),
])
patch("src/tools/rebuild_deliverables.py", [
    ("Run; crossings reduced (29 to 20 house routes), not eliminated", "Run; crossings reduced, not eliminated (counts in table6_obstacle_avoidance.csv)"),
    ("buffer 7.1 m, penalty x100; 29 to 20 house routes crossing another footprint, +22% unique length; hard block failed", "buffer 7.1 m, penalty x100; fewer house routes cross another footprint at the price of a longer network (table6_obstacle_avoidance.csv); hard block failed"),
    ("The buffer scenario keeps 20 of 163 house routes crossing another footprint, 16 of them only within the first 20 m of the route.", "The buffer scenario keeps some house routes crossing another footprint, most of them only within the first 20 m of the route (table6_obstacle_avoidance.csv)."),
    ("final network (20 of 163)", "final network (see table6_obstacle_avoidance.csv)"),
])
print("patched")
