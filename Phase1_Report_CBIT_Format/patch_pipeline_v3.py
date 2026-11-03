"""One-off patch (kept for provenance): wires runner v1.4 (building-avoiding scenario), crossing diagnostic, charts and map 5 into the pipeline and final package."""
ROOT = r"D:\Telangana_Rural_Project"


def patch(path, pairs):
    s = open(path, encoding="utf-8").read()
    for a, b in pairs:
        assert s.count(a) == 1, (path, s.count(a), a[:80])
        s = s.replace(a, b)
    open(path, "w", encoding="utf-8").write(s)


patch(ROOT + r"\src\run_pipeline.py", [
    ('        if runner.endswith("v1_3.py"):', '        if runner.endswith(("v1_3.py", "v1_4.py")):'),
    ('        P.append(("4", "omit_merge (C1)",',
     '        P.append(("3", "S2_fac_C0_s25_avoid_buf100 (building-avoiding scenario: footprints buffered 7.1 m, penalty x100)",\n'
     '                  lambda: self.stage_b("dk_stageB_run_v1_4.py", "avoid_buf100", mult=100.0, extra=["--avoid-buildings", "buffer"])))\n'
     '        P.append(("4", "omit_merge (C1)",'),
    ('            for k, p_, lab in ((1, 0, "K1_P0"),',
     '            for m_ in (20.0, 1000.0):\n'
     '                P.append(("3", "avoid_buf%g (penalty saturation check)" % m_, (lambda m_=m_: self.stage_b("dk_stageB_run_v1_4.py", "avoid_buf%g" % m_, mult=m_, extra=["--avoid-buildings", "buffer"]))))\n'
     '            for k, p_, lab in ((1, 0, "K1_P0"),'),
    ('        for r in (primary, "S2_fac_C0_s25_P3_none"):\n            self.run([PY, SRC / "routing" / "explain_routes.py"',
     '        for r in (primary, "S2_fac_C0_s25_P3_none", "S2_fac_C0_s25_avoid_buf100"):\n            self.run([PY, SRC / "routing" / "explain_routes.py"'),
    ('        for r in ("S2_fac_C0_s25_v11", "S2_fac_C0_s25_P3_none"):\n            src = self.stageB / r',
     '        s3 = ["S2_fac_C0_s25_v11", "S2_fac_C0_s25_P3_none"] + [d.name for d in sorted(self.stageB.iterdir()) if d.is_dir() and "avoid_buf" in d.name]\n        for r in s3:\n            src = self.stageB / r'),
    ('            cp(self.stageB / "_route_explanations" / r, o / "stage3_plan" / r / "why_chosen")',
     '            if (self.stageB / "_route_explanations" / r).exists():\n                cp(self.stageB / "_route_explanations" / r, o / "stage3_plan" / r / "why_chosen")'),
    ('            if d.is_dir() and not d.name.startswith("_") and d.name not in ("S2_fac_C0_s25_v11", "S2_fac_C0_s25_P3_none"):',
     '            if d.is_dir() and not d.name.startswith("_") and d.name not in s3:'),
    ('        mism = [f.name for g in ("routing", "validation", "preprocessing", "stress_test")', '        mism = [f.name for g in ("routing", "validation", "preprocessing", "stress_test")'),
])

patch(ROOT + r"\src\run_final_package.py", [
    ('    prim = sb / "S2_fac_C0_s25_v11"\n', '    prim = sb / "S2_fac_C0_s25_v11"\n    avoid = sb / "S2_fac_C0_s25_avoid_buf100"\n'),
    ('    step("final maps 1-4", [PY, SRC / "reporting" / "make_final_maps.py", "--run-dir", prim, "--out", O / "final_maps"])',
     '    step("final maps 1-5", [PY, SRC / "reporting" / "make_final_maps.py", "--run-dir", prim, "--avoid-run-dir", avoid, "--out", O / "final_maps"])'),
    ('    step("comparison tables", [PY, SRC / "reporting" / "comparison_tables.py", "--stageb-root", sb, "--out", O / "final_comparison"])',
     '    runs_x = [sb / n for n in ("S2_fac_C0_s25_v11", "S2_fac_C0_s25_P3_none")] + sorted(sb.glob("S2_fac_C0_s25_avoid_buf*"))\n'
     '    step("building crossing diagnostic", [PY, SRC / "validation" / "building_crossing_diagnostic.py", "--runs"] + runs_x + ["--out", O / "final_comparison"])\n'
     '    step("comparison tables", [PY, SRC / "reporting" / "comparison_tables.py", "--stageb-root", sb, "--out", O / "final_comparison"])\n'
     '    step("charts", [PY, SRC / "reporting" / "make_charts.py", "--stageb-root", sb, "--comparison", O / "final_comparison", "--out", O / "final_comparison" / "charts"])'),
    ('           "| 3 | Map 1 imagery, boundary, roads | `outputs/final_maps/map1_imagery_boundary_roads.png` |",',
     '           "| 3 | Map 1 imagery, boundary, roads | `outputs/final_maps/map1_imagery_boundary_roads.png` |",\n           "| 6b | Map 5 village-level detail, primary versus building-avoiding network | `outputs/final_maps/map5_village_detail_shared_paths.png` |",\n           "| 7c | Charts 1-5 (lengths, materials, cost, accessibility, avoidance trade-off) | `outputs/final_comparison/charts/` |",'),
])
print("patched")
