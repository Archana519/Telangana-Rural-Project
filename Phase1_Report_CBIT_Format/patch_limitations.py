"""One-off patch (kept for provenance): adds the 'Methodological Limitations and Future Scope' section and corrects the imagery capture-date wording
(the saved Esri identify result records 29 Apr 2026 for the sampled point)."""
import shutil
ROOT = r"D:\Telangana_Rural_Project"


def patch(rel, pairs):
    path = ROOT + "\\" + rel.replace("/", "\\")
    s = open(path, encoding="utf-8").read()
    for a, b in pairs:
        assert s.count(a) == 1, (rel, s.count(a), a[:90])
        s = s.replace(a, b)
    open(path, "w", encoding="utf-8").write(s)


SHORT = "capture date 29 Apr 2026 at the one point sampled (Esri identify result, Vantor 60 cm layer); dates elsewhere in the mosaic are not recorded"

patch("src/reporting/make_final_maps.py", [
    ('IMG_NOTE = " Imagery: Esri World Imagery export; capture date unknown, licence unresolved - review draft, do not redistribute."',
     'IMG_NOTE = " Imagery: Esri World Imagery export (Vantor 60 cm layer; capture date 29 Apr 2026 at one sampled point, mosaic-wide dates not recorded); licence unresolved - review draft, do not redistribute."'),
])
patch("src/validation/visual_audit_protocol.py", [
    ("Note that the project's Esri mosaic has an unknown capture date, so a mismatch in date can explain a difference.",
     "Note that the project's Esri mosaic has a recorded capture date of 29 Apr 2026 at one sampled point only (other parts may differ), so a mismatch in date can explain a difference."),
])
patch("inputs/METADATA.md", [
    ("**Capture date unknown** (not stored with the export)", "Capture date 29 Apr 2026 at the one point sampled with the Esri identify service (Vantor, 60 cm layer; `reference/external/esri_world_imagery_identify.json`); dates elsewhere in the mosaic are not recorded"),
])
patch("src/reporting/make_chapter.py", [
    ('"| Imagery capture date and licence | Recorded in `inputs/METADATA.md`; maps carry a caution | Unresolved |\\n"', '"| Imagery licence and acquisition dates | Recorded in `inputs/METADATA.md`; maps carry a caution; one sampled capture date (29 Apr 2026) | Licence unresolved; mosaic-wide dates not recorded |\\n"'),
    ('"The imagery licence and capture date are unresolved, so the maps containing imagery are review drafts.")\n', '"The imagery licence is unresolved and its capture date is recorded for one sampled point only, so the maps containing imagery are review drafts.")\n    import limitations_text\n    A("")\n    for _ln in limitations_text.TEXT.split("\\n"):\n        A(_ln)\n'),
])
patch("src/tools/rebuild_deliverables.py", [
    ("(built 4 Oct 2026 from 11 `MapServer/export` requests); capture date unknown |", "(built 4 Oct 2026 from 11 `MapServer/export` requests); capture date 29 Apr 2026 at one sampled point (Esri identify result), elsewhere not recorded |"),
    ('| 07_LIMITATIONS_AND_OPEN_ISSUES | limitations and unresolved issues |', '| 07_LIMITATIONS_AND_OPEN_ISSUES | limitations and unresolved issues, `METHODOLOGICAL_LIMITATIONS_AND_FUTURE_SCOPE.md` (data terms, field validation, C3) |'),
    ('    put("07_LIMITATIONS_AND_OPEN_ISSUES/LIMITATIONS.md",', '    sys_path = str(ROOT / "src" / "reporting")\n    import sys as _s\n    _s.path.insert(0, sys_path)\n    import limitations_text\n    put("07_LIMITATIONS_AND_OPEN_ISSUES/METHODOLOGICAL_LIMITATIONS_AND_FUTURE_SCOPE.md", "# Methodological Limitations and Future Scope\\n\\n" + limitations_text.TEXT.split("\\n", 1)[1])\n    put("07_LIMITATIONS_AND_OPEN_ISSUES/LIMITATIONS.md",'),
    ('| Field validation, legal access, physical passability | none | NOT IMPLEMENTED | Field work or authoritative records | outside current evidence |',
     '| Field validation, legal access, physical passability | none; routes are GIS/DEM simulations and ground truthing is designated for future phases | NOT IMPLEMENTED | Field work or authoritative records | `07_LIMITATIONS_AND_OPEN_ISSUES/METHODOLOGICAL_LIMITATIONS_AND_FUTURE_SCOPE.md` |'),
    ('| Additional-village transfer (C3) | none run | NOT IMPLEMENTED | Wait for written approval of this gate | five more villages |', '| Additional-village transfer (C3) | none run; multi-village testing is extended future work | NOT IMPLEMENTED | Wait for written approval of this gate | five more villages |'),
    ('| Imagery licence | unresolved (Esri World Imagery mosaic built from export requests; enquiry draft not sent) | NOT VERIFIED |', '| Imagery and TGRAC data licences | unresolved: Esri mosaic built from export requests (not Content Packages), enquiry draft not sent; TGRAC terms not found; attribution wording in Section 13.1 | NOT VERIFIED |'),
])
shutil.copy2(ROOT + r"\archive\restored_from_git_c397b49\Siddipet\Damarakunta\results\esri_world_imagery_identify.json", ROOT + r"\Siddipet\Damarakunta\reference\external\esri_world_imagery_identify.json")
print("patched")
