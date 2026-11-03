"""One-off patch (kept for provenance): run_pipeline.py gets a 'final' profile and the full final-family scenario set (5 facilities: 3 retained + 2 GP HQ),
and comparison_tables.py uses the final family for the C2 and C1 tables."""
ROOT = r"D:\Telangana_Rural_Project"


def patch(rel, pairs):
    path = ROOT + "\\" + rel.replace("/", "\\")
    s = open(path, encoding="utf-8").read()
    for a, b in pairs:
        assert s.count(a) == 1, (rel, s.count(a), a[:90])
        s = s.replace(a, b)
    open(path, "w", encoding="utf-8").write(s)


s = open(ROOT + r"\src\run_pipeline.py", encoding="utf-8").read()
# 1. constants
a = s.index('NOANG = ["--fac-file"')
b = s.index("\n", a)
s = s[:a] + 'FIN = ["--fac-file", str(SN.FAC_LAYER), "--expect-facilities", str(SN.N_FACILITIES)]   # final facility layer: 3 retained + 2 Gram Panchayat HQ (inputs/EXCLUSIONS.md, inputs/ADMIN_UTILITIES.md)' + s[b:]
s = s.replace("NOANG", "FIN")
# 2. stage_b with scenario / slope / cost
a = s.index("    def stage_b(self, runner")
b = s.index("    def plan_runs(self):")
s = s[:a] + '''    def stage_b(self, runner, label="", mult=4.0, k=3, passes=2, perturb=None, frac=None, seed=None, extra=(), scenario="S2", slope=25, cost="C0", small=None):
        cmd = [PY, SCRIPTS / runner, "--stagea-run", self.run_id, "--scenario", scenario, "--facilities", "on", "--slope-limit-deg", str(slope),
               "--cost-scenario", cost, "--building-mult", str(mult)]
        if label:
            cmd += ["--label", label]
        if runner.endswith(("v1_3.py", "v1_4.py")):
            cmd += ["--k", str(k), "--passes", str(passes)]
            if perturb:
                cmd += ["--perturb", perturb]
            if frac is not None:
                cmd += ["--perturb-frac", str(frac)]
            if seed is not None:
                cmd += ["--perturb-seed", str(seed)]
            if small is not None:
                cmd += ["--small-pct", str(small)]
        self.run(cmd + list(extra))

''' + s[b:]
# 3. plan_runs
a = s.index("    def plan_runs(self):")
b = s.index("    # ------------------------------------------------------------------ stage 5")
s = s[:a] + '''    def plan_runs(self):
        """(stage, name, callable) for Stage B runs.
        Reference family (4 facilities, verified): v11 and P3_none always (reproduction check); the other 25 only with --profile full.
        Final family (5 facilities, key suffix 'final'): quick = x4, x1, avoid100; full and final = every scenario the report and tables use."""
        P = []
        P.append(("3", "S2_fac_C0_s25_v11 (verified baseline, building penalty x4)", lambda: self.stage_b("dk_stageB_run_v1_1.py", "v11")))
        P.append(("3", "S2_fac_C0_s25_P3_none (verified baseline control, no penalty x1)", lambda: self.stage_b("dk_stageB_run_v1_2.py", "P3_none", mult=1.0)))
        fin = lambda lab, **kw: (lambda: self.stage_b("dk_stageB_run_v1_4.py", lab, extra=kw.pop("extra", []) + FIN, **kw))
        P.append(("3", "final_x4 (final family primary: 5 facilities, penalty x4)", fin("final_x4", mult=4.0)))
        P.append(("3", "final_x1 (final family control: no penalty)", fin("final_x1", mult=1.0)))
        P.append(("3", "final_avoid_buf100 (building-avoiding scenario: footprints buffered 7.1 m, penalty x100)", fin("final_avoid_buf100", mult=100.0, extra=["--avoid-buildings", "buffer"])))
        if self.a.profile in ("full", "final"):
            for m_ in (20.0, 1000.0):
                P.append(("3", "final_avoid_buf%g (penalty saturation check)" % m_, fin("final_avoid_buf%g" % m_, mult=m_, extra=["--avoid-buildings", "buffer"])))
            P.append(("3", "final_P1 (penalise plausible only)", fin("final_P1", extra=["--building-quality", "PLAUSIBLE"])))
            P.append(("3", "final_P2 (penalise plausible and review)", fin("final_P2", extra=["--building-quality", "PLAUSIBLE,REVIEW"])))
            P.append(("3", "S1 25 degrees (final family)", fin("final", scenario="S1")))
            P.append(("3", "S1 10 degrees (final family)", fin("final", scenario="S1", slope=10)))
            P.append(("3", "S2 10 degrees (final family)", fin("final", slope=10)))
            P.append(("3", "S2 cost scenario C1 (final family)", fin("final", cost="C1")))
            for k, p_, lab in ((1, 0, "K1_P0"), (1, 2, "K1_P2"), (3, 0, "K3_P0"), (3, 2, "K3_P2")):
                P.append(("4", "final_" + lab + " (C2 ablation, final family)", fin("final_" + lab, k=k, passes=p_)))
            P.append(("4", "omit_merge (C1, final family)", fin("final", perturb="omit_merge")))
            for sp in (10, 25):
                P.append(("4", "omit smallest %d%% (C1, final family)" % sp, fin("final", perturb="omit_small", small=sp)))
            for kind in ("omit", "add"):
                for frac in (0.1, 0.2):
                    for sd in SEEDS:
                        P.append(("4", "%s %d%% seed %d (C1, final family, synthetic)" % (kind, round(frac * 100), sd), fin("final", perturb=kind, frac=frac, seed=sd)))
        if self.a.profile == "full":
            P.append(("4", "omit_merge (C1)", lambda: self.stage_b("dk_stageB_run_v1_3.py", "", perturb="omit_merge")))
            for k, p_, lab in ((1, 0, "K1_P0"), (1, 2, "K1_P2"), (3, 0, "K3_P0"), (3, 2, "K3_P2")):
                P.append(("4", lab + " (C2 ablation)", (lambda k=k, p_=p_, lab=lab: self.stage_b("dk_stageB_run_v1_3.py", lab, k=k, passes=p_))))
            for kind in ("omit", "add"):
                for frac in (0.1, 0.2):
                    for sd in SEEDS:
                        P.append(("4", "%s %d%% seed %d (C1, synthetic)" % (kind, round(frac * 100), sd),
                                  (lambda kind=kind, frac=frac, sd=sd: self.stage_b("dk_stageB_run_v1_3.py", "", perturb=kind, frac=frac, seed=sd))))
        return P

''' + s[b:]
s = s.replace('        vruns = [d.name for d in sorted(self.stageB.iterdir()) if d.is_dir() and not d.name.startswith("_") and "omitmerge" not in d.name\n                 and not any(t in d.name for t in ("_K1_", "_K3_"))]',
              '        vruns = [d.name for d in sorted(self.stageB.iterdir()) if d.is_dir() and not d.name.startswith("_") and "omitmerge" not in d.name and "omitsmall" not in d.name\n                 and not any(t in d.name for t in ("_K1_", "_K3_"))]')
s = s.replace('        if self.a.profile == "full":\n            self.run([PY, SCRIPTS / "dk_stageB_c2_ablation_summary_v1.py", "--stageb-root", self.stageB, "--label", "main", "--reference", "S2_fac_C0_s25_v11",',
              '        if self.a.profile in ("full", "final"):\n            self.run([PY, SCRIPTS / "dk_stageB_c2_ablation_summary_v1.py", "--stageb-root", self.stageB, "--label", "final", "--reference", SN.PRIMARY,\n                      "--same-config-control", "S2_fac_C0_s25_final_K3_P2", "--runs", "S2_fac_C0_s25_final_K1_P0", "S2_fac_C0_s25_final_K1_P2", "S2_fac_C0_s25_final_K3_P0", "S2_fac_C0_s25_final_K3_P2"])\n        if self.a.profile == "full":\n            self.run([PY, SCRIPTS / "dk_stageB_c2_ablation_summary_v1.py", "--stageb-root", self.stageB, "--label", "main", "--reference", "S2_fac_C0_s25_v11",')
s = s.replace('ap.add_argument("--profile", choices=["quick", "full"], default="quick")', 'ap.add_argument("--profile", choices=["quick", "full", "final"], default="quick")')
s = s.replace('    python src/run_pipeline.py --profile full   # adds C2 ablation (K, passes) and all 20 omit/add seed runs', '    python src/run_pipeline.py --profile final  # the two verified baseline runs + every final-family scenario (what the report and tables use)\n    python src/run_pipeline.py --profile full   # final profile plus the verified 4-facility reference runs (27 runs, 405 metrics checked)')
open(ROOT + r"\src\run_pipeline.py", "w", encoding="utf-8").write(s)

patch("src/reporting/comparison_tables.py", [
    ('        if "final" not in name and cfg.get("perturb", "none") == "none" and cfg["building_mult"] == 4.0 and cfg["slope_limit_deg"] == 25.0 and cfg["scenario"] == "S2" and cfg["cost_scenario"] == "C0":',
     '        if "_final" in name and cfg.get("perturb", "none") == "none" and cfg["building_mult"] == 4.0 and cfg["slope_limit_deg"] == 25.0 and cfg["scenario"] == "S2" and cfg["cost_scenario"] == "C0" and cfg.get("avoid_buildings", "off") == "off" and cfg["building_quality"] == "PLAUSIBLE,REVIEW,UNRESOLVED_MERGE":'),
    ('        if cfg["building_mult"] != 4.0 or cfg["slope_limit_deg"] != 25.0 or cfg["scenario"] != "S2" or cfg["k"] != 3 or cfg["passes"] != 2:', '        if "_final" not in name or cfg["building_mult"] != 4.0 or cfg["slope_limit_deg"] != 25.0 or cfg["scenario"] != "S2" or cfg["k"] != 3 or cfg["passes"] != 2 or cfg.get("avoid_buildings", "off") != "off" or cfg["cost_scenario"] != "C0":'),
    ('        if "_K1_" in name or "_K3_" in name or "final" not in name:      # C2 ablation and 4-facility reference runs are not scenarios of this table', '        if "_K1_" in name or "_K3_" in name or "_final" not in name or cfg["scenario"] != "S2" or cfg["cost_scenario"] != "C0" or cfg["slope_limit_deg"] != 25.0 or cfg.get("perturb", "none") != "none":      # only the final-family S2 scenarios'),
])
print("patched")
