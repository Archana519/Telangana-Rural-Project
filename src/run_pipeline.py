"""Master pipeline for the Damarakunta case study: ONE command, fresh outputs, no stale files.

    python src/run_pipeline.py                  # quick profile (5 Stage B runs)
    python src/run_pipeline.py --profile final  # the two verified baseline runs + every final-family scenario (what the report and tables use)
    python src/run_pipeline.py --profile full   # final profile plus the verified 4-facility reference runs (27 runs, 405 metrics checked)
    python src/run_pipeline.py --dry-run        # checks inputs and planner hash, prints the plan, runs nothing

What it does (the five stages of the project):
  Stage 1 Detect     verifies the building candidates (buildings_v8_full.gpkg) and the imagery by SHA-256. It does NOT re-run the
                     segmentation: the StrongDINOv2Seg weights' location is not recorded in the project, so detection is reused as input.
  Stage 2 Terrain    verifies the 10 m aligned rasters, roads and facilities by SHA-256 against the reference run. It does not rebuild them
                     (rebuilding would overwrite verified inputs); the builders are in src/preprocessing.
  Stage 3 Plan       Stage A (candidate routes) into a NEW run folder, then Stage B (network selection) for the primary x4 run and the P3 x1 control.
  Stage 4 Stress     C1 omission/addition/merge runs (synthetic probes, not measured segmentation error) and, with --profile full, the C2 ablation.
  Stage 5 Validate   acceptance validator, connectivity audit v2, route-level explanations, comparison with the reference run.
Fresh results are written under results/<run_id>/ by the Stage A/B scripts and then collected into outputs/<run_id>/stage<N>_<name>/.
Nothing in archive/ or in earlier runs is read, except the reference run's manifest and results used for the comparison.
Costs are ordinal planning units; routes are planning alternatives, not roads; no field validation is implied.
"""
import argparse, csv, hashlib, json, shutil, subprocess, sys, time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VILLAGE = ROOT / "Siddipet" / "Damarakunta"
SCRIPTS = ROOT / "scripts"            # the verified runners look for the planner here by default (see CLEANUP_PHASE1_REPORT.md)
SRC = ROOT / "src"
REF_RUN = "run_20261029_01"
PLANNER_SHA = "d00ea92028101131627b8592e3df2c33ff350efac9b1de09f9b64cdd56ef70a4"
SEEDS = [20261029, 20261030, 20261031, 20261032, 20261033]
PY = sys.executable
sys.path.insert(0, str(Path(__file__).resolve().parent))
import scenario_names as SN
FIN = ["--fac-file", str(SN.FAC_LAYER), "--expect-facilities", str(SN.N_FACILITIES), "--roads-file", str(ROOT / "Siddipet" / "Damarakunta" / "reference" / "derived" / "tgrac_road_network_clipped.gpkg"), "--facility-exempt", "HEALTH_8734223673:20"]   # final facility layer: 3 retained + 2 Gram Panchayat HQ (inputs/EXCLUSIONS.md, inputs/ADMIN_UTILITIES.md)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


class Pipeline:
    def __init__(self, a):
        self.a = a
        self.ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_id = a.resume or "run_%s" % self.ts
        self.res = VILLAGE / "results" / self.run_id
        self.out = ROOT / "outputs" / self.run_id
        self.stageB = self.res / "stageB"
        self.steps = []          # (stage, name, status, seconds, note)
        self.log_lines = []

    def log(self, *x):
        s = " ".join(str(v) for v in x)
        print(s, flush=True)
        self.log_lines.append(s)

    def step(self, stage, name, fn):
        t = time.time()
        try:
            note = fn() or ""
            self.steps.append((stage, name, "PASS", time.time() - t, note))
            self.log("[PASS] stage %s | %s %s" % (stage, name, note))
        except Exception as e:                       # stop at the first failure: later stages would rest on it
            self.steps.append((stage, name, "FAIL", time.time() - t, str(e)))
            self.log("[FAIL] stage %s | %s | %s" % (stage, name, e))
            self.finish(False)
            sys.exit(1)

    def run(self, args, cwd=ROOT, ok_codes=(0,)):
        self.log("   $", " ".join(str(x) for x in args))
        if self.a.dry_run:
            return
        p = subprocess.run([str(x) for x in args], cwd=str(cwd), capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.log_lines.append(p.stdout[-4000:])
        if p.returncode not in ok_codes:
            raise RuntimeError("exit %d: %s" % (p.returncode, (p.stderr or p.stdout)[-600:]))

    # ------------------------------------------------------------------ stage 1 and 2
    def verify_inputs(self):
        man = list(csv.DictReader(open(VILLAGE / "results" / REF_RUN / "stageB" / "S2_fac_C0_s25_v11" / "inputs_manifest_stageB.csv", encoding="utf-8")))
        want = {r["role"]: r for r in man}
        roles = ["buildings", "roads", "cost", "worldcover", "blocked", "slope", "fac", "compounds", "cad", "cad0", "planner"]
        bad = []
        rows = []
        for r in roles:
            p = Path(want[r]["path"])
            now = sha(p) if p.exists() else "MISSING"
            ok = now == want[r]["sha256"]
            rows.append((r, str(p), now, want[r]["sha256"], "PASS" if ok else "FAIL"))
            if not ok:
                bad.append(r)
        self.input_rows = rows
        if bad:
            raise RuntimeError("input files differ from the reference manifest: %s (stop; do not run on changed inputs)" % bad)
        if want["planner"]["sha256"] != PLANNER_SHA:
            raise RuntimeError("reference planner hash is not the reviewed one")
        if not SN.FAC_LAYER.exists():
            raise RuntimeError("derived facility layer missing: %s (see inputs/EXCLUSIONS.md)" % SN.FAC_LAYER)
        mism = [f.name for g in ("routing", "validation", "preprocessing", "stress_test") for f in (SRC / g).glob("*.py")
                if (SCRIPTS / f.name).exists() and sha(f) != sha(SCRIPTS / f.name)]
        if mism:
            raise RuntimeError("src copy differs from scripts/: %s" % mism)
        return "%d input hashes equal the reference manifest; planner %s...; src copies equal scripts/" % (len(rows), PLANNER_SHA[:12])

    # ------------------------------------------------------------------ stage 3
    def stage_a(self):
        self.run([PY, SCRIPTS / "dk_stageA_prepare_r3.py", "--run-name", self.run_id])

    def stage_b(self, runner, label="", mult=4.0, k=3, passes=2, perturb=None, frac=None, seed=None, extra=(), scenario="S2", slope=25, cost="C0", small=None):
        cmd = [PY, SCRIPTS / runner, "--stagea-run", self.run_id, "--scenario", scenario, "--facilities", "on", "--slope-limit-deg", str(slope),
               "--cost-scenario", cost, "--building-mult", str(mult)]
        if label:
            cmd += ["--label", label]
        if runner.endswith(("v1_3.py", "v1_4.py", "v1_5.py", "v1_6.py")):
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

    def plan_runs(self):
        """(stage, name, callable) for Stage B runs.
        Reference family (4 facilities, verified): v11 and P3_none always (reproduction check); the other 25 only with --profile full.
        Final family (5 facilities, key suffix 'final'): quick = x4, x1, avoid100; full and final = every scenario the report and tables use."""
        P = []
        P.append(("3", "S2_fac_C0_s25_v11 (verified baseline, building penalty x4)", lambda: self.stage_b("dk_stageB_run_v1_1.py", "v11")))
        P.append(("3", "S2_fac_C0_s25_P3_none (verified baseline control, no penalty x1)", lambda: self.stage_b("dk_stageB_run_v1_2.py", "P3_none", mult=1.0)))
        fin = lambda lab, **kw: (lambda: self.stage_b("dk_stageB_run_v1_6.py", lab, extra=kw.pop("extra", []) + FIN, **kw))
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

    # ------------------------------------------------------------------ stage 5
    def validate(self):
        # The acceptance validator was built for the primary/penalty/omit/add runs (as in the reference audit of 30 runs). It does not support
        # omit_merge (it applies the add-run rule) nor the C2 ablation runs (it compares them with the V1 regression, which they differ from by design).
        vruns = [d.name for d in sorted(self.stageB.iterdir()) if d.is_dir() and not d.name.startswith("_") and "omitmerge" not in d.name and "omitsmall" not in d.name
                 and not any(t in d.name for t in ("_K1_", "_K3_"))]
        self.run([PY, SCRIPTS / "dk_stageB_validate.py", "--stageb-root", self.stageB, "--stagea-dir", self.res / "stageA", "--label", "main", "--runs"] + vruns, ok_codes=(0, 3))
        self.check_validator_fails()
        if self.a.profile in ("full", "final"):
            self.run([PY, SCRIPTS / "dk_stageB_c2_ablation_summary_v1.py", "--stageb-root", self.stageB, "--label", "final", "--reference", SN.PRIMARY,
                      "--same-config-control", "S2_fac_C0_s25_final_K3_P2", "--runs", "S2_fac_C0_s25_final_K1_P0", "S2_fac_C0_s25_final_K1_P2", "S2_fac_C0_s25_final_K3_P0", "S2_fac_C0_s25_final_K3_P2"])
        if self.a.profile == "full":
            self.run([PY, SCRIPTS / "dk_stageB_c2_ablation_summary_v1.py", "--stageb-root", self.stageB, "--label", "main", "--reference", "S2_fac_C0_s25_v11",
                      "--same-config-control", "S2_fac_C0_s25_K3_P2", "--runs", "S2_fac_C0_s25_K1_P0", "S2_fac_C0_s25_K1_P2", "S2_fac_C0_s25_K3_P0", "S2_fac_C0_s25_K3_P2"])
        primary = SN.REF_PRIMARY       # verified 4-facility baseline: used only for the reproduction check
        self.run([PY, SCRIPTS / "dk_stageB_connectivity_audit_v2.py", "--stageb-root", self.stageB, "--runs", SN.PRIMARY, SN.P3])
        self.run([PY, SCRIPTS / "dk_stageB_run_repro_compare_v1.py", "--original", VILLAGE / "results" / REF_RUN / "stageB" / primary,
                  "--repro", self.stageB / primary, "--out", self.stageB / "_compare_to_reference"], ok_codes=(0, 1))
        self.check_repro_compare()
        for r in (SN.PRIMARY, SN.P3, SN.AVOID):
            self.run([PY, SRC / "routing" / "explain_routes.py", "--run-dir", self.stageB / r, "--out", self.stageB / "_route_explanations" / r])

    def check_validator_fails(self):
        """The final family routes on the road layer clipped to the boundary, so the comparison with the earlier single-stage (V1) result, made on the
        unclipped layer, does not apply to the primary run (REG-00 INFO). The validator's V15 then reports FAIL for that one run; any other FAIL stops the pipeline."""
        import pandas as pd
        if self.a.dry_run:
            return
        D = pd.read_csv(self.stageB / "_validation_main" / "validation_results.csv")
        bad = D[D.status == "FAIL"]
        unexpected = [(r.run, r.test_id) for _, r in bad.iterrows() if not (r.run == SN.PRIMARY and r.test_id == "V15")]
        if unexpected:
            raise RuntimeError("validator FAIL: %s" % unexpected)
        self.log("   validator: %d FAIL, all expected (V15 on the primary run: V1 regression not applicable to the clipped road layer)" % len(bad))

    def check_repro_compare(self):
        """The comparer exits 1 for any DIFFERENT row. Two differences are expected for a fresh run: the Stage A run name (config arg
        'stagea_run') and the hashes of the Stage A config/checks files, which contain that name. Anything else is a real failure."""
        import pandas as pd
        D = pd.read_csv(self.stageB / "_compare_to_reference" / "repro_comparison.csv")
        bad = D[D.result != "MATCH"]
        unexpected = []
        for _, r in bad.iterrows():
            ok = (r.check.startswith("config args equal") and "differing args: ['stagea_run']" in r.detail) or                  (r.check.startswith("input sha256 per role") and "roles differing: ['stageA_config', 'stageA_checks']" in r.detail and "only in one: []" in r.detail)
            if not ok:
                unexpected.append(r.check)
        if unexpected:
            raise RuntimeError("fresh run differs from the reference run in: %s" % unexpected)
        self.log("   reproduction check: %d checks, %d MATCH, %d expected differences (new run name only)" % (len(D), (D.result == "MATCH").sum(), len(bad)))

    def compare_reference(self):
        """new run vs reference run, per run folder present in both; exact equality expected (deterministic planner)."""
        rows, bad = [], []
        for d in sorted(self.stageB.iterdir()):
            ref = VILLAGE / "results" / REF_RUN / "stageB" / d.name
            if d.name.startswith("_") or not (d / "evaluation_summary.json").exists() or not (ref / "evaluation_summary.json").exists():
                continue
            n, r = json.load(open(d / "evaluation_summary.json")), json.load(open(ref / "evaluation_summary.json"))
            for blk in ("houses_primary", "facilities_primary", "combined_primary"):
                for key in ("n", "unique_len_m", "total_len_m", "unique_cost", "total_cost"):
                    x, y = n[blk][key], r[blk][key]
                    diff = abs(x - y)
                    rows.append((d.name, blk, key, x, y, diff))
                    if diff > 1e-6:
                        bad.append((d.name, blk, key, x, y))
        with open(self.stageB / "_compare_to_reference" / "summary_vs_reference.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f); w.writerow(["run", "block", "metric", "new", "reference", "abs_diff"]); w.writerows(rows)
        if bad:
            raise RuntimeError("%d metrics differ from the reference run, first: %s" % (len(bad), bad[0]))
        return "%d runs, %d metrics identical to %s (|diff| <= 1e-6)" % (len({r[0] for r in rows}), len(rows), REF_RUN)

    # ------------------------------------------------------------------ collect outputs
    def collect(self):
        o = self.out
        def cp(src, dst):
            dst.parent.mkdir(parents=True, exist_ok=True)
            if Path(src).is_dir():
                shutil.copytree(src, dst, dirs_exist_ok=True)
            elif Path(src).exists():
                shutil.copy2(src, dst)
        cp(VILLAGE / "results" / "v8_instances" / "buildings_v8_full.gpkg", o / "stage1_detect" / "building_footprints" / "buildings_v8_full.gpkg")
        cp(SN.FAC_LAYER, o / "stage1_detect" / "priority_facilities_excl_1702300.gpkg")
        for f in ("damarakunta_cost_surface_10m.tif", "damarakunta_prohibited_mask_10m.tif", "damarakunta_slope_10m.tif", "damarakunta_worldcover_10m.tif"):
            cp(VILLAGE / "aligned" / f, o / "stage2_terrain" / "cost_surface_rasters" / f)
        cp(VILLAGE / "reference" / "tgrac_road_network.gpkg", o / "stage2_terrain" / "existing_roads" / "tgrac_road_network.gpkg")
        cp(VILLAGE / "reference" / "derived" / "tgrac_road_network_clipped.gpkg", o / "stage2_terrain" / "existing_roads" / "tgrac_road_network_clipped.gpkg")
        s3 = [SN.PRIMARY, SN.P3] + [d.name for d in sorted(self.stageB.iterdir()) if d.is_dir() and d.name.startswith(SN.AVOID_PREFIX)]
        for r in s3:
            src = self.stageB / r
            for f in ("routes.gpkg", "selection_summary.csv", "route_edges.csv", "route_alternatives.csv", "evaluation_summary.json", "config_stageB.json",
                      "connectivity_checks.csv", "road_components.csv", "inputs_manifest_stageB.csv", "outputs_manifest.csv"):
                cp(src / f, o / "stage3_plan" / r / f)
            if (self.stageB / "_route_explanations" / r).exists():
                cp(self.stageB / "_route_explanations" / r, o / "stage3_plan" / r / "why_chosen")
        for d in sorted(self.stageB.iterdir()):
            if d.is_dir() and not d.name.startswith("_") and d.name not in s3:
                for f in ("evaluation_summary.json", "config_stageB.json"):      # reference-family runs keep the 4-facility baseline; no per-facility rows are copied
                    cp(d / f, o / "stage4_stress" / d.name / f)
        for d in sorted(self.stageB.iterdir()):
            if d.is_dir() and d.name.startswith("_"):
                cp(d, o / "stage5_validate" / d.name.lstrip("_"))
        cp(self.res / "stageA", o / "stage5_validate" / "stageA_checks")

    def finish(self, ok):
        if self.a.dry_run:
            return
        self.out.mkdir(parents=True, exist_ok=True)
        L = ["# Pipeline run %s" % self.run_id, "", "Status: **%s**. Profile `%s`. Planner SHA-256 `%s`." % ("PASS" if ok else "FAILED", self.a.profile, PLANNER_SHA), "",
             "| Stage | Step | Status | Seconds | Note |", "|---|---|---|---|---|"]
        for s, n, st, sec, note in self.steps:
            L.append("| %s | %s | %s | %.0f | %s |" % (s, n, st, sec, str(note).replace("|", "/")[:300]))
        L += ["", "Costs are ordinal planning units; routes are planning alternatives, not roads; the stress-test runs are synthetic. "
              "Detection (Stage 1) and terrain (Stage 2) are verified inputs, not re-run. Where each output is: `stage1_detect` (footprints, facilities), "
              "`stage2_terrain` (cost surface rasters, existing roads), `stage3_plan` (new routes, alternatives, why-chosen), `stage4_stress`, `stage5_validate`.", ""]
        if getattr(self, "input_rows", None):
            L += ["## Input hashes", "", "| Role | SHA-256 now | Equals reference |", "|---|---|---|"] + ["| %s | %s | %s |" % (r[0], r[2][:16], r[4]) for r in self.input_rows]
        (self.out / "RUN_SUMMARY.md").write_text("\n".join(L) + "\n", encoding="utf-8")
        (self.out / "pipeline.log").write_text("\n".join(self.log_lines), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--profile", choices=["quick", "full", "final"], default="quick")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--resume", default=None, metavar="RUN_ID", help="reuse the Stage A and Stage B runs already in results/RUN_ID and run only stage 5 and the output collection")
    a = ap.parse_args()
    pl = Pipeline(a)
    pl.log("run id:", pl.run_id, "| profile:", a.profile, "| dry-run:", a.dry_run)
    pl.step("1-2", "verify inputs (hashes) and planner", pl.verify_inputs)
    if not a.resume:
        pl.step("3", "Stage A candidate routes", pl.stage_a)
        for stage, name, fn in pl.plan_runs():
            pl.step(stage, name, fn)
    if not a.dry_run:
        pl.step("5", "validator, connectivity audit, reference comparison, explanations", pl.validate)
        pl.step("5", "metrics equal the reference run", pl.compare_reference)
        pl.step("5", "collect outputs", pl.collect)
    pl.finish(True)
    pl.log("outputs:", pl.out)


if __name__ == "__main__":
    main()
