"""One-off patch (kept for provenance): Chapter 4 and architecture texts synced to the five-facility final layer; new subsection 4.3
'Administrative and Governance Utilities'."""
ROOT = r"D:\Telangana_Rural_Project\Phase1_Report_CBIT_Format"


def patch(rel, pairs):
    path = ROOT + "\\" + rel.replace("/", "\\")
    s = open(path, encoding="utf-8").read()
    for a, b in pairs:
        assert s.count(a) == 1, (rel, s.count(a), a[:90])
        s = s.replace(a, b)
    open(path, "w", encoding="utf-8").write(s)


patch("source_tex/A_Dissertation_Phase_I_Review_1_Report_Final.tex", [
    ("Built from TGRAC school, health and anganwadi layers by \\texttt{prepare\\_damarakunta\\_priority\\_facilities.py}",
     "Built from TGRAC school and health layers by \\texttt{prepare\\_damarakunta\\_priority\\_facilities.py}, plus two Gram Panchayat headquarters points from TGRAC layer 10 (see Section 4.3); the anganwadi record is excluded"),
    ("4 facilities (a primary school, a high school, a sub-centre, an anganwadi), all priority group~1",
     "5 facilities in the final layer (a primary school, a high school, a sub-centre, two Gram Panchayat headquarters points), all priority group~1"),
    ("Priority facilities & Define the first-stage targets for the shared network (C2). & Actual village planning",
     "Priority facilities and administrative utilities & Define the first-stage targets for the shared network (C2); the Gram Panchayat headquarters points add administrative service destinations. & Actual village planning"),
])
patch("content_v2.py", [
    ("the village boundary and four facility points.", "the village boundary and five facility points (three school and health points, two Gram Panchayat headquarters points; the anganwadi is excluded)."),
    ('"scenario_targets.csv (163 houses) and facility targets (4).",', '"scenario_targets.csv (163 houses) and facility targets (5).",'),
    ("Facility identity is unresolved: the school layers are attribute-only, the anganwadi coordinates are given to four decimals, and the sub-centre has two TGRAC records 235.7 m apart.",
     "Facility identity is unresolved: the school layers are attribute-only, the Gram Panchayat points are headquarters locations (the building is not identified), the sub-centre has two TGRAC records 235.7 m apart, and the anganwadi was excluded because no footprint lies within 371 m of its coordinate."),
    ('["3", "278 candidates, 4 facilities",', '["3", "278 candidates, 5 facilities",'),
    ('["Facility targets", "Point features", "4 (2 schools, 1 sub-centre, 1 anganwadi)", "TGRAC school, health and anganwadi layers",',
     '["Facility targets", "Point features", "5 in the final layer (2 schools, 1 sub-centre, 2 Gram Panchayat HQ points); the TGRAC anganwadi is excluded", "TGRAC school and health layers; TGRAC layer 10 (Gram Panchayat headquarters)",'),
    ("167 selected routes (163 houses, 4 facilities)", "168 selected routes (163 houses, 5 facilities)"),
    ('"4 targets; school layers attribute-only; anganwadi 4-decimal coordinates; sub-centre has two TGRAC records 235.7 m apart (facility_status.csv)."',
     '"5 targets (3 school and health points, 2 Gram Panchayat HQ points); school layers attribute-only; Gram Panchayat building not identified; sub-centre has two TGRAC records 235.7 m apart; the anganwadi was excluded (facility_status.csv, inputs/EXCLUSIONS.md)."'),
])
patch("make_arch_figs.py", [("targets (quality classes); 4 facility targets", "targets (quality classes); 5 facility targets")])

# new subsection 4.3 in build_report.py
p = ROOT + r"\build_report.py"
s = open(p, encoding="utf-8").read()
a = "# ---------- 5 Architecture"
assert s.count(a) == 1
new = '''H(2, "4.3", "Administrative and Governance Utilities")
_vf = {r["facility_id"]: r for r in _csv.DictReader(open(r"D:\\Telangana_Rural_Project\\outputs\\verification\\facility_verification.csv", encoding="utf-8-sig"))}
_g1, _g2 = _vf["GP_DAMARAKUNTA"], _vf["GP_KASHIREDDYPALLY"]
para(runs("Besides schools and the health sub-centre, a village baseline needs the administrative and governance points that residents use: the Gram Panchayat office, the MeeSeva citizen-service centre and the Directorate of Electronic Service Delivery (ESD) service and Aadhaar centre. They are treated as primary administrative utility points of the village baseline, and the same layer structure is meant to be reused for other villages. Table @T:admin@ gives the source, count, position, checks and status of each. Only the Gram Panchayat headquarters points could be sourced.".replace("@T:admin@", REF["tab:admin"])))
table_caption("admin", "Administrative and governance utilities: source, count, position and verification status.")
make_table(["Utility", "Source and count", "Position (lat, lon)", "Checks against other layers", "Status"], [
    ["Damarakunta Gram Panchayat headquarters", "TGRAC Administrative Information System, MapServer layer 10 (Gram Panchayat Head Quarter, point layer); 1 point", "%s N, %s E" % (_g1["lat"], _g1["lon"]),
     "Inside the village boundary; table latitude/longitude equals the geometry; %s m from a detected footprint (an unresolved-merge blob, building not identified); %s m from an Open Buildings polygon" % (_g1["dist_to_nearest_footprint_m"], _g1["nearest_open_buildings_m"]), "Included in the facility layer"],
    ["Kashireddypally Gram Panchayat headquarters (second GP whose revenue village is Damarakunta)", "Same layer; 1 point", "%s N, %s E" % (_g2["lat"], _g2["lon"]),
     "Inside the boundary, in the eastern settlement; %s m from a detected footprint; %s m from an Open Buildings polygon" % (_g2["dist_to_nearest_footprint_m"], _g2["nearest_open_buildings_m"]), "Included in the facility layer"],
    ["MeeSeva centre", "No source found: none of the 162 TGRAC map services (2,019 layers) has a MeeSeva, ESD, Aadhaar or citizen-service layer, and OpenStreetMap has no such feature in the village area; 0 points", "not located", "none possible", "Not included; coordinate and source needed"],
    ["Directorate of ESD (Aadhaar/service) centre", "Same search; 0 points", "not located", "none possible", "Not included; coordinate and source needed"]],
    [1.3, 1.9, 1.0, 1.9, 0.9], size=8)
para(runs("Selection reason. The Gram Panchayat is the village's governance body and a destination for residents; its headquarters location is published by TGRAC in the same service as the village boundary, which makes the source official, queryable by village and reusable for every other village in the template. Verification means agreement with independent layers: both points lie inside the boundary and on or within 1 m of a detected building footprint and within 4 m of an Open Buildings polygon. This shows consistency, not that the building is the Panchayat office; TGRAC calls the point a headquarters location, and a visual or field check is still needed. The MeeSeva and ESD centres are not placed on a guess: in many villages the MeeSeva centre sits in the Panchayat office, but that is an assumption and is not applied. Coordinates for them can be added through inputs/admin_utilities_intake.csv once a source (the MeeSeva or UIDAI locator, a register or a field GPS reading) is available."))
para(runs("Facility counts used throughout this report: five facilities in the final layer (primary school, high school, sub-centre and two Gram Panchayat headquarters points). The TGRAC anganwadi (Damarakunt-I) is excluded because its coordinate lies 371 m from the nearest detected footprint (inputs/EXCLUSIONS.md); it is kept only as an excluded record."))

'''
s = s.replace(a, new + a)
s = s.replace('"dsunits", "modules"', '"dsunits", "admin", "modules"')
open(p, "w", encoding="utf-8").write(s)
print("patched")
