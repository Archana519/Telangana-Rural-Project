"""One-off patch (kept for provenance): run_pipeline.py and run_final_package.py use the 'noang' scenario family (anganwadi excluded)."""
ROOT = r"D:\Telangana_Rural_Project"


def patch(rel, pairs):
    path = ROOT + "\\" + rel.replace("/", "\\")
    s = open(path, encoding="utf-8").read()
    for a, b in pairs:
        assert s.count(a) == 1, (rel, s.count(a), a[:90])
        s = s.replace(a, b)
    open(path, "w", encoding="utf-8").write(s)


patch("src/run_pipeline.py", [
    ('PY = sys.executable\n', 'PY = sys.executable\nsys.path.insert(0, str(Path(__file__).resolve().parent))\nimport scenario_names as SN\nNOANG = ["--fac-file", str(SN.FAC_LAYER), "--expect-facilities", "3"]   # facility layer without the excluded anganwadi (inputs/EXCLUSIONS.md)\n'),
    ('''        P.append(("3", "S2_fac_C0_s25_avoid_buf100 (building-avoiding scenario: footprints buffered 7.1 m, penalty x100)",
                  lambda: self.stage_b("dk_stageB_run_v1_4.py", "avoid_buf100", mult=100.0, extra=["--avoid-buildings", "buffer"])))
''', '''        P.append(("3", "noang_x4 (final-family primary: 3 facilities, penalty x4)", lambda: self.stage_b("dk_stageB_run_v1_4.py", "noang_x4", mult=4.0, extra=NOANG)))
        P.append(("3", "noang_x1 (final-family control: no penalty)", lambda: self.stage_b("dk_stageB_run_v1_4.py", "noang_x1", mult=1.0, extra=NOANG)))
        P.append(("3", "noang_avoid_buf100 (building-avoiding scenario: footprints buffered 7.1 m, penalty x100)",
                  lambda: self.stage_b("dk_stageB_run_v1_4.py", "noang_avoid_buf100", mult=100.0, extra=NOANG + ["--avoid-buildings", "buffer"])))
'''),
    ('''                P.append(("3", "avoid_buf%g (penalty saturation check)" % m_, (lambda m_=m_: self.stage_b("dk_stageB_run_v1_4.py", "avoid_buf%g" % m_, mult=m_, extra=["--avoid-buildings", "buffer"]))))''',
     '''                P.append(("3", "noang_avoid_buf%g (penalty saturation check)" % m_, (lambda m_=m_: self.stage_b("dk_stageB_run_v1_4.py", "noang_avoid_buf%g" % m_, mult=m_, extra=NOANG + ["--avoid-buildings", "buffer"]))))'''),
    ('''        primary = "S2_fac_C0_s25_v11"
        self.run([PY, SCRIPTS / "dk_stageB_connectivity_audit_v2.py", "--stageb-root", self.stageB, "--runs", primary, "S2_fac_C0_s25_P3_none"])''',
     '''        primary = SN.REF_PRIMARY       # verified 4-facility baseline: used only for the reproduction check
        self.run([PY, SCRIPTS / "dk_stageB_connectivity_audit_v2.py", "--stageb-root", self.stageB, "--runs", SN.PRIMARY, SN.P3])'''),
    ('        for r in (primary, "S2_fac_C0_s25_P3_none", "S2_fac_C0_s25_avoid_buf100"):', '        for r in (SN.PRIMARY, SN.P3, SN.AVOID):'),
    ('        cp(VILLAGE / "reference" / "damarakunta_priority_facilities.gpkg", o / "stage1_detect" / "priority_facilities.gpkg")', '        cp(SN.FAC_LAYER, o / "stage1_detect" / "priority_facilities_excl_1702300.gpkg")'),
    ('        s3 = ["S2_fac_C0_s25_v11", "S2_fac_C0_s25_P3_none"] + [d.name for d in sorted(self.stageB.iterdir()) if d.is_dir() and "avoid_buf" in d.name]',
     '        s3 = [SN.PRIMARY, SN.P3] + [d.name for d in sorted(self.stageB.iterdir()) if d.is_dir() and d.name.startswith(SN.AVOID_PREFIX)]'),
    ('                for f in ("evaluation_summary.json", "config_stageB.json", "selection_summary.csv"):', '                for f in ("evaluation_summary.json", "config_stageB.json"):      # reference-family runs keep the 4-facility baseline; no per-facility rows are copied'),
    ('        mism = [f.name for g in ("routing", "validation", "preprocessing", "stress_test")', '        if not SN.FAC_LAYER.exists():\n            raise RuntimeError("derived facility layer missing: %s (see inputs/EXCLUSIONS.md)" % SN.FAC_LAYER)\n        mism = [f.name for g in ("routing", "validation", "preprocessing", "stress_test")'),
])

patch("src/run_final_package.py", [
    ('PY = sys.executable\n', 'PY = sys.executable\nsys.path.insert(0, str(Path(__file__).resolve().parent))\nimport scenario_names as SN\n'),
    ('    prim = sb / "S2_fac_C0_s25_v11"\n    avoid = sb / "S2_fac_C0_s25_avoid_buf100"\n', '    prim = sb / SN.PRIMARY\n    avoid = sb / SN.AVOID\n'),
    ('    runs_x = [sb / n for n in ("S2_fac_C0_s25_v11", "S2_fac_C0_s25_P3_none")] + sorted(sb.glob("S2_fac_C0_s25_avoid_buf*"))', '    runs_x = [sb / n for n in (SN.PRIMARY, SN.P3)] + sorted(sb.glob(SN.AVOID_PREFIX + "*"))'),
])
print("patched")
