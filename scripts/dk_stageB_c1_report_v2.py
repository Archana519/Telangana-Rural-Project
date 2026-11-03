"""dk_stageB_c1_report_v2.py - (v2: corrected parameter-status section, runner-version limitation, provenance, 2-decimal exposure, built-in validation and v1 comparison) builds the C1 Markdown report, figures and file manifest from EXISTING outputs only (read-only on all inputs).
Refuses to build if any validation row in any input is not PASS (INFO allowed only for C07 facility attribution). Writes only to a NEW folder _c1_<label>."""
import argparse, sys, json, hashlib, datetime
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""): h.update(ch)
    return h.hexdigest()

def short(run):
    if "omitsmall25" in run: return "omit_small P25"
    if "omitsmall10" in run: return "omit_small P10"
    if "omitmerge" in run: return "omit_merge"
    return "Baseline"

def key(run): return run.replace("_P3_none", "")

def mdt(df, fmt=None):
    fmt = fmt or {}; cols = list(df.columns); out = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for _, r in df.iterrows():
        cells = []
        for c in cols:
            v = r[c]
            if isinstance(v, (float, np.floating)):
                cells.append("n/a" if np.isnan(v) else (fmt.get(c, "{:.2f}")).format(v))
            else: cells.append(str(v))
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out)

def word(a, b, unit="", nd=2):
    d = b - a
    if abs(d) < 1e-9: return "was unchanged"
    return f"{'rose' if d > 0 else 'fell'} from {a:.{nd}f}{unit} to {b:.{nd}f}{unit}"

class Block:
    def __init__(s, root, title, cmp_d, fp_d, ex_d):
        s.title = title; s.root = root; s.cmp_d, s.fp_d, s.ex_d = [root / x for x in (cmp_d, fp_d, ex_d)]
        s.cmp = pd.read_csv(s.cmp_d / "c1_scenario_comparison.csv"); s.val = pd.read_csv(s.cmp_d / "c1_validation.csv")
        s.om = pd.read_csv(s.cmp_d / "omitted_candidates.csv"); s.nmc = pd.read_csv(s.cmp_d / "non_main_component_targets.csv")
        s.fp = pd.read_csv(s.fp_d / "c1_footprint_crossings_full_set.csv"); s.fpv = pd.read_csv(s.fp_d / "c1_footprint_validation.csv")
        s.ex = pd.read_csv(s.ex_d / "c1_omitted_footprint_exposure.csv"); s.exv = pd.read_csv(s.ex_d / "c1_exposure_validation.csv")
        s.base = s.cmp[s.cmp.role == "BASELINE"].run.iloc[0]
    def gate(s):
        bad = []
        for df, name, ok in ((s.val, "compare", ("PASS", "INFO")), (s.fpv, "footprint", ("PASS",)), (s.exv, "exposure", ("PASS",))):
            b = df[~df.status.isin(ok)]
            if len(b): bad.append((name, b))
        info_non_c07 = s.val[(s.val.status == "INFO") & (~s.val.id.str.startswith("C07"))]
        if len(info_non_c07): bad.append(("compare INFO outside C07", info_non_c07))
        return bad

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--stageb-root", required=True); ap.add_argument("--label", default="report_v2"); ap.add_argument("--cost-raster", required=True); ap.add_argument("--v1-report", default=None); ap.add_argument("--scripts-dir", required=True); ap.add_argument("--buildings", required=True)
    ap.add_argument("--primary", nargs=3, default=["_c1_c07fix_primary", "_c1_fp_primary", "_c1_ex_primary"], metavar=("CMP", "FP", "EX"))
    ap.add_argument("--p3", nargs=3, default=["_c1_c07fix_p3", "_c1_fp_p3", "_c1_ex_p3"], metavar=("CMP", "FP", "EX"))
    ap.add_argument("--no-p3", action="store_true", help="sandbox testing only")
    a = ap.parse_args(); root = Path(a.stageb_root); out = root / f"_c1_{a.label}"
    if out.exists(): sys.exit(f"refusing: {out} already exists")
    blocks = [Block(root, "Primary baseline (building penalty x4)", *a.primary)]
    if not a.no_p3: blocks.append(Block(root, "P3 baseline (no building penalty)", *a.p3))
    stop = False
    for b in blocks:
        for name, df in b.gate(): print(f"GATE FAIL [{b.title}] {name}:\n{df}"); stop = True
    if stop: sys.exit("stopping: an input validation is not clean; no report written")
    out.mkdir(); figs = out / "figures"; figs.mkdir()
    # ---------- figures (from real CSVs) ----------
    C = {"Primary baseline (building penalty x4)": "#0072B2", "P3 baseline (no building penalty)": "#D55E00"}
    order = ["Baseline", "omit_small P25", "omit_small P10", "omit_merge"]
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
    for k, (col, ttl, yl) in enumerate((("net_unique_len_m", "Unique network length (all routed targets)", "metres"), ("net_unique_len_per_routed_m", "Unique length per routed target", "metres per routed target"))):
        for j, b in enumerate(blocks):
            d = b.cmp.assign(s=b.cmp.run.map(short)).set_index("s").reindex(order)[col]
            x = np.arange(len(order)) + (j - (len(blocks) - 1) / 2) * 0.38
            bars = ax[k].bar(x, d.values, 0.36, color=C[b.title], label=b.title)
            for xi, v in zip(x, d.values):
                if not np.isnan(v): ax[k].text(xi, v, f"{v:.0f}" if k == 0 else f"{v:.1f}", ha="center", va="bottom", fontsize=7)
        ax[k].set_xticks(range(len(order))); ax[k].set_xticklabels(order, rotation=15, fontsize=8); ax[k].set_ylabel(yl); ax[k].set_title(ttl, fontsize=10); ax[k].spines[["top", "right"]].set_visible(False)
    ax[0].legend(fontsize=7, frameon=False); fig.suptitle("Fewer targets shorten the network; per-target length is the comparable quantity", fontsize=10); fig.tight_layout(); fig.savefig(figs / "fig1_length_and_per_routed.png", dpi=170); plt.close(fig)
    fig, ax = plt.subplots(1, len(blocks), figsize=(5.6 * len(blocks), 4.2), squeeze=False)
    for j, b in enumerate(blocks):
        e = b.ex.assign(s=b.ex.run.map(short)); x = np.arange(len(e))
        ax[0][j].bar(x - 0.19, e.baseline_retained_len_in_omitted_m, 0.36, color="#999999", label="baseline routes (footprints known)")
        ax[0][j].bar(x + 0.19, e.omission_len_in_omitted_m, 0.36, color=C[b.title], label="omission-run routes (footprints unknown)")
        for xi, v in zip(x - 0.19, e.baseline_retained_len_in_omitted_m): ax[0][j].text(xi, v, f"{v:.0f}", ha="center", va="bottom", fontsize=7)
        for xi, v in zip(x + 0.19, e.omission_len_in_omitted_m): ax[0][j].text(xi, v, f"{v:.0f}", ha="center", va="bottom", fontsize=7)
        ax[0][j].set_xticks(x); ax[0][j].set_xticklabels(e.s, fontsize=8); ax[0][j].set_ylabel("route length inside the omitted footprints (m)"); ax[0][j].set_title(b.title, fontsize=9); ax[0][j].spines[["top", "right"]].set_visible(False)
        ax[0][j].legend(fontsize=7, frameon=False)
    fig.suptitle("Same footprints, same remaining targets: route length inside them", fontsize=10); fig.tight_layout(); fig.savefig(figs / "fig2_length_inside_omitted_footprints.png", dpi=170); plt.close(fig)
    # ---------- tables ----------
    def t_scale(b):
        d = b.cmp.copy(); d["Run"] = d.run.map(short)
        return d[["Run", "original_targets", "omitted", "remaining", "routed", "genuine_failures", "not_main_component", "net_unique_len_m", "net_unique_len_m_diff_pct", "net_unique_len_per_routed_m", "net_unique_len_per_routed_diff_pct", "credit_pct", "facility_unique_len_m"]].rename(columns={
            "original_targets": "Original", "omitted": "Omitted", "remaining": "Remaining", "routed": "Routed", "genuine_failures": "Genuine failures", "not_main_component": "Not in main comp.", "net_unique_len_m": "Unique length (m)",
            "net_unique_len_m_diff_pct": "Change (%)", "net_unique_len_per_routed_m": "Per routed (m)", "net_unique_len_per_routed_diff_pct": "Change per routed (%)", "credit_pct": "Shared-edge credit (%)", "facility_unique_len_m": "Facility unique (m)"})
    def t_fp(b):
        d = b.fp.copy(); d["Run"] = d.run.map(short); d["len_per_routed"] = d.len_in_any_full_m / d.routed
        return d[["Run", "routed", "routes_crossing_any_full", "crossing_any_full_per_routed", "len_in_any_full_m", "len_per_routed", "routes_crossing_omitted", "len_in_omitted_m", "routes_crossing_retained", "len_in_retained_m"]].rename(columns={
            "routed": "Routed", "routes_crossing_any_full": "Routes crossing any footprint", "crossing_any_full_per_routed": "Rate per routed", "len_in_any_full_m": "Length in footprints (m)", "len_per_routed": "Length per routed (m)",
            "routes_crossing_omitted": "Routes crossing omitted", "len_in_omitted_m": "Length in omitted (m)", "routes_crossing_retained": "Routes crossing retained (runner metric)", "len_in_retained_m": "Length in retained (m, runner metric)"})
    def t_ex(b):
        d = b.ex.copy(); d["Run"] = d.run.map(short)
        return d[["Run", "omitted_footprints", "retained_targets", "baseline_retained_cross_omitted", "baseline_retained_len_in_omitted_m", "omission_cross_omitted", "omission_len_in_omitted_m", "delta_len_vs_baseline_retained_m"]].rename(columns={
            "omitted_footprints": "Omitted footprints", "retained_targets": "Retained targets", "baseline_retained_cross_omitted": "Baseline routes crossing", "baseline_retained_len_in_omitted_m": "Baseline length (m)",
            "omission_cross_omitted": "Omission routes crossing", "omission_len_in_omitted_m": "Omission length (m)", "delta_len_vs_baseline_retained_m": "Delta (m)"})
    I = "{:.0f}"; F3 = "{:.3f}"
    fmt_int = {c: I for c in ["Original", "Omitted", "Remaining", "Routed", "Genuine failures", "Not in main comp.", "Omitted footprints", "Retained targets", "Baseline routes crossing", "Omission routes crossing", "Routes crossing any footprint", "Routes crossing omitted", "Routes crossing retained (runner metric)"]}
    fmt_int.update({"Rate per routed": F3})
    # ---------- narrative ----------
    P = blocks[0]; P3 = blocks[1] if len(blocks) > 1 else None
    scripts = ["dk_stageB_run_v1_1.py", "dk_stageB_run_v1_2.py", "dk_stageB_run_v1_3.py", "plan_network_v2.py", "dk_stageB_c1_compare.py", "dk_stageB_c1_compare_v2.py", "dk_stageB_c1_c07.py", "dk_stageB_c1_test_c07.py", "dk_stageB_c1_diag_facility.py", "dk_stageB_c1_diag_facility_costs_v2.py",
               "dk_stageB_c1_footprint_eval_v1.py", "dk_stageB_c1_test_footprint_eval.py", "dk_stageB_c1_omitted_exposure_v1.py", "dk_stageB_c1_report_v1.py", "dk_stageB_c1_report_v2.py"]
    sd = Path(a.scripts_dir); srows = [dict(Script=s, **{"SHA-256": sha(sd / s) if (sd / s).exists() else "NOT FOUND"}) for s in scripts]
    L = []
    L += [f"# C1 report: propagation of building-candidate omission into rural road-network planning", "", f"Village: Damarakunta, Siddipet, Telangana (EPSG:32644). Generated {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')} by `dk_stageB_c1_report_v1.py` from existing outputs only.", "",
          "> All results below come from **deterministic candidate-omission scenarios** applied to a building-candidate layer. They are not measured segmentation false-negative rates, and nothing here is field-validated.", ""]
    L += ["## 1. Research question and hypotheses", "",
          "**Question (C1).** How does a missing set of building candidates change the road-network plan produced by the Stage B planner, compared with planning on the full candidate set?", "",
          "Hypotheses as evaluated here (the exposure measure in H2 was adopted after an output audit, see section 10):", "",
          "- **H1 (scale).** Omitting targets shortens the absolute network because fewer targets are connected; length per routed target is the comparable quantity.",
          "- **H2 (exposure).** When a building penalty is used, omitting footprints from the planner input increases route length inside those footprints, because the penalty can no longer steer routes around them.",
          "- **H3 (structure control).** With no penalty (P3) the planner ignores footprints, so any change in exposure then reflects network restructuring rather than lost penalty information.", ""]
    L += ["## 2. Relation to the research gap", "",
          "C1 is one of three planned contributions (C1 error propagation, C2 two-stage generate-and-select planner with shared-edge credit, C3 transfer only if supported). Generic A*, least-cost paths, AHP and facility prioritisation are not claimed as novel. This report supports C1 only, on one village.", ""]
    L += ["## 3. Baselines and fixed parameters", ""]
    for b in blocks:
        cfg = json.load(open(root / b.base / "config_stageB.json")); args = cfg.get("args", {})
        L += [f"**{b.title}** - baseline run `{b.base}`", "", mdt(pd.DataFrame([dict(Argument=k, Value=str(v)) for k, v in sorted(args.items())])), ""]
    L += ["Costs are ordinal model units, not money. Edge weight is the mean of the two cell costs times step length (10 m or 10*sqrt(2) m); the building penalty is a cell multiplier inside the cost grid. The two baselines are never mixed in one comparison.", ""]
    cfgP = json.load(open(root / P.base / "config_stageB.json")); csn = cfgP.get("cost_scenario", {}); cargs = cfgP.get("args", {})
    L += ["### 3.1 Settings used in these runs and their status", "",
          mdt(pd.DataFrame([
              dict(Setting="Cost scenario", Value=str(cargs.get("cost_scenario")), Status="Fixed: land-cover table `c0_land_cost` plus slope term, recorded in each config. The separate `C1` cost scenario (built-up cost 3.0, a provisional table in the runner) was NOT used (`c1_land_cost_json` = " + str(cargs.get("c1_land_cost_json")) + "); note that this `C1` is a cost scenario, unrelated to the contribution C1."),
              dict(Setting="Slope limit (hard)", Value=str(cargs.get("slope_limit_deg")) + " deg", Status="Fixed setting for all runs."),
              dict(Setting="Building penalty", Value="x" + str(cargs.get("building_mult")) + " on " + str(cargs.get("building_quality")), Status="Design parameter (soft multiplier, not a fact). P3 repeats the experiment with multiplier 1.0."),
              dict(Setting="Target and facility weights", Value="1.0 for every house and facility", Status="Design choice set in the Stage B runner (source inspection: `dk_stageB_run_v1_3.py` lines 498 and 506); the planner's own default weights (health 4, school 3, government 2) are not used in Stage B."),
              dict(Setting="Cadastral file", Value=str(cfgP.get("cadastral_used")), Status="Used only for parcel-overlap metrics; routes do not depend on it. Repaired by make_valid; parcel counts are crossings of parcel units, not ownership."),
              dict(Setting="Slope data", Value="Sobel slope from a ~30 m DEM, resampled to 10 m", Status="Not genuine 10 m terrain detail (noted in the run configs)."),
              dict(Setting="Costs", Value="ordinal model units", Status="Not money; no construction-cost claim is made.")])), ""]
    L += ["## 4. Perturbation definitions", ""]
    pr = []
    for b in blocks:
        for run, g in b.om.groupby("run"):
            pr.append(dict(Baseline="Primary" if b is P else "P3", Run=short(run), Rule=g.reason.iloc[0], Omitted=len(g), **{"Threshold (m2)": (float(g.threshold_m2.iloc[0]) if pd.notna(g.threshold_m2.iloc[0]) else np.nan)}))
    L += [mdt(pd.DataFrame(pr), {"Threshold (m2)": "{:.2f}", "Omitted": "{:.0f}"}), "",
          "- `omit_small`: targets with `area_m2` at or below the stated percentile of the scenario-target areas (163 targets) are removed.",
          "- `omit_merge`: all targets whose `quality_class` is `UNRESOLVED_MERGE` are removed.",
          "- The omitted footprints are also removed from the planner's building-penalty layer. Facilities are never omitted.",
          "- These are **not** spatially clustered omissions and carry no random seed. The omitted groups are defined by footprint area or quality class, which may be spatially concentrated; that concentration was not designed or measured.", ""]
    qc = []
    for b in blocks:
        ct = b.om.groupby(["run", "quality_class"]).size().reset_index(name="n"); ct["Baseline"] = "Primary" if b is P else "P3"; ct["Run"] = ct.run.map(short); qc.append(ct[["Baseline", "Run", "quality_class", "n"]])
    L += ["Omitted targets by quality class:", "", mdt(pd.concat(qc).rename(columns={"quality_class": "Quality class", "n": "Omitted"}), {"Omitted": "{:.0f}"}), ""]
    L += ["## 5. Reproducibility", "", "The omission modes are deterministic; the `perturb_seed` value shown in the configs is not used by them. The runs record their arguments and version in each `config_stageB.json`; the command lines below are **reconstructed from the working session**, not machine-recorded:", "", "```powershell",
          "scripts\\dk_stageB_run_v1_3.py --scenario S2 --perturb omit_small --small-pct 25      (also --small-pct 10)",
          "scripts\\dk_stageB_run_v1_3.py --scenario S2 --building-mult 1.0 --perturb omit_small --small-pct 25 --label P3_none",
          "scripts\\dk_stageB_run_v1_3.py --scenario S2 --building-mult 1.0 --perturb omit_merge --label P3_none",
          "scripts\\dk_stageB_run_v1_3.py --scenario S2 --perturb omit_merge", "scripts\\dk_stageB_c1_compare_v2.py --stageb-root $B --label c07fix_primary|c07fix_p3 --buildings <v8 buildings> --cost-raster <aligned cost surface> --baseline <baseline run> --runs <omission runs>",
          "scripts\\dk_stageB_c1_footprint_eval_v1.py --label fp_primary|fp_p3 ... --ref-comparison <c07fix folder>\\c1_scenario_comparison.csv",
          "scripts\\dk_stageB_c1_omitted_exposure_v1.py --label ex_primary|ex_p3 ... --fp-summary <fp folder>\\c1_footprint_crossings_full_set.csv", "scripts\\dk_stageB_c1_report_v2.py --stageb-root $B --scripts-dir <scripts> --buildings <v8 buildings> --cost-raster <aligned cost surface>", "```", "",
          "### 5.1 Runner versions and comparability", "",
          mdt(pd.DataFrame([dict(Run=b_.base, **{"Recorded runner version": json.load(open(root / b_.base / "config_stageB.json")).get("version")}) for b_ in blocks] + [dict(Run=short(r_) + " (" + ("Primary" if b_ is P else "P3") + ")", **{"Recorded runner version": json.load(open(root / r_ / "config_stageB.json")).get("version")}) for b_ in blocks for r_ in b_.cmp.run if r_ != b_.base])), "",
          "Source comparison of the three runner scripts (hashes below): v1.1 to v1.2 adds the `--perturb`, `--perturb-frac`, `--perturb-seed`, `--add-min-m` and `--add-max-m` options and code gated by `--perturb != none`, plus lookups guarded by an index test that is always true for real candidates. v1.2 to v1.3 adds the `omit_small` and `omit_merge` modes, `--small-pct`, and branches gated by those modes. No change to routing, cost, penalty or evaluation code was found for `--perturb none`. The check C06 compared every baseline configuration key except the perturbation, label and path keys, and found no difference. **Not verified:** an empirical `--perturb none` reproduction of the primary baseline with v1.3; the conclusion above rests on static source comparison.", "",
          "Script versions (SHA-256 at report build time):", "", mdt(pd.DataFrame(srows)), "",
          f"Buildings input: `{a.buildings}` SHA-256 `{sha(a.buildings)}`", "", f"Cost raster input: `{a.cost_raster}` SHA-256 `{sha(a.cost_raster)}`", "",
          "### 5.2 Input provenance and licence status", "",
          "- Building candidates (`buildings_v8_full.gpkg`) are model-derived polygons extracted from a high-resolution imagery mosaic; they are unverified candidates, not surveyed buildings.",
          "- The mosaic was assembled on 4 Oct 2026 from Esri World Imagery map-export requests. The project document `DAMARAKUNTA_STAGE_B_C_PROPOSALS.md` records that the licence for this use is **not verified** (storage, inference, derived maps, publication and sharing are undetermined). Nothing in this report is licence-cleared.",
          "- Reference roads, facilities and cadastral data are used as provided in the project folders; their provenance is documented in the project data-source notes, not re-verified here.", ""]
    L += ["## 6. Results", ""]
    for b in blocks: L += [f"### 6.{blocks.index(b)+1} {b.title}", "", mdt(t_scale(b), fmt_int), ""]
    L += ["## 7. Absolute versus per-routed-target change", "",
          "Absolute network length falls whenever targets are omitted, because fewer targets are connected. A shorter network is therefore **not** evidence of efficiency. Compare length per routed target (the `Per routed` column) and the shared-edge credit. Route-count metrics (routes crossing footprints) and route-length metrics (metres inside footprints) are reported separately and must not be mixed.", ""]
    for b in blocks:
        r = b.cmp.assign(s=b.cmp.run.map(short)).set_index("s")
        for s_ in order[1:]:
            if s_ in r.index: L += [f"- {b.title}, {s_}: unique length {word(r.loc['Baseline','net_unique_len_m'], r.loc[s_,'net_unique_len_m'], ' m')}; per routed target {word(r.loc['Baseline','net_unique_len_per_routed_m'], r.loc[s_,'net_unique_len_per_routed_m'], ' m')}."]
    L += [""]
    L += ["## 8. Connectivity and non-main-component targets", "", "Genuine routing failures are 0 in every run. Omitted targets are not counted as failures. The non-main-component count refers to targets whose route attaches to a road component other than the main one:", ""]
    for b in blocks: L += [f"**{b.title}**", "", mdt(b.nmc.assign(run=b.nmc.run.map(short)), {"route_len_m": "{:.1f}"}), ""]
    L += ["A change in this count between runs can occur only because the affected target was itself omitted; it is not evidence of improved connectivity.", ""]
    L += ["## 9. Facility-route invariance test and its resolution", "",
          "The original check C07 assumed facility routes cannot change because facilities are planned first. In the primary omit_merge run it warned (facility unique length 303.72 m vs 311.34 m). Diagnosis (read-only): omitted footprints are also removed from the penalty layer, which changes the cost surface the facility routes are planned on; the two changed routes pass through cells whose penalty was removed, and the baseline routes pass through none. Corrected check (`dk_stageB_c1_c07.py`): PASS if geometry is identical; INFO only if geometry changed AND the new route uses removed-penalty cells AND the cost reconstruction calibrates AND the new route is not costlier than the old on the new surface; otherwise FAIL.", ""]
    for b in blocks:
        c7 = b.val[b.val.id.str.startswith("C07")]; L += [f"{b.title}: C07 PASS {int((c7.status=='PASS').sum())}, INFO {int((c7.status=='INFO').sum())}, other {int((~c7.status.isin(['PASS','INFO'])).sum())}.", ""]
        for r in c7[c7.status == "INFO"].itertuples(): L += [f"- `{r.id}` {r.name} - {r.detail}"]
        L += [""]
    L += ["Costs on the two surfaces are not comparable for changed routes; report the facility change as geometry and length only. It is not evidence that omission improves facility planning.", ""]
    L += ["## 10. Route-footprint interaction", "",
          "**Audit finding.** The runner scores routes against its own (reduced) footprint set, so in omission runs the omitted footprints are invisible to its crossing metrics. Those columns (`retained`) are reported only for reproducibility and are **not comparable** with the baseline. All comparisons below score every run's saved routes against the full footprint set (`dk_stageB_c1_footprint_eval_v1.py`); that script reproduces the runner's own numbers exactly for the retained footprints (checks F01-F03 PASS). The runner's `net_len_penalised_cells_m` is measured against each run's own penalty mask and is likewise excluded from the conclusions.", ""]
    for b in blocks: L += [f"### 10.{blocks.index(b)+1} Crossings against the full footprint set - {b.title}", "", mdt(t_fp(b), fmt_int), ""]
    L += ["### 10.3 Controlled contrast on identical footprints", "", "For each scenario: route length inside the footprints that scenario omits, for the baseline routes of the same remaining targets (footprints known to the planner) versus the omission run (footprints unknown). Per-target segments depend on shared-edge attribution, so compare totals, not individual routes.", ""]
    for b in blocks: L += [f"**{b.title}**", "", mdt(t_ex(b), {**fmt_int, "Baseline length (m)": "{:.2f}", "Omission length (m)": "{:.2f}", "Delta (m)": "{:+.2f}"}), ""]
    ce = P.ex.assign(s=P.ex.run.map(short)).set_index("s")
    for s_ in ["omit_merge", "omit_small P25", "omit_small P10"]:
        if s_ in ce.index: L += [f"- Primary, {s_}: length inside omitted footprints {word(ce.loc[s_,'baseline_retained_len_in_omitted_m'], ce.loc[s_,'omission_len_in_omitted_m'], ' m')} (routes crossing: {int(ce.loc[s_,'baseline_retained_cross_omitted'])} in the baseline routes, {int(ce.loc[s_,'omission_cross_omitted'])} in the omission run)."]
    if P3 is not None:
        c3 = P3.ex.assign(s=P3.ex.run.map(short)).set_index("s")
        for s_ in c3.index: L += [f"- P3 (no penalty), {s_}: {word(c3.loc[s_,'baseline_retained_len_in_omitted_m'], c3.loc[s_,'omission_len_in_omitted_m'], ' m')} - this is the structural component only, since the planner ignores footprints in P3."]
        both = [s_ for s_ in ce.index if s_ in c3.index]
        if both:
            L += ["", "Indicative decomposition (not a causal estimate; one deterministic scenario per mode): primary delta minus P3 delta.", "",
                  mdt(pd.DataFrame([dict(Scenario=s_, **{"Primary delta (m)": ce.loc[s_, "delta_len_vs_baseline_retained_m"], "P3 delta (m)": c3.loc[s_, "delta_len_vs_baseline_retained_m"], "Difference (m)": ce.loc[s_, "delta_len_vs_baseline_retained_m"] - c3.loc[s_, "delta_len_vs_baseline_retained_m"]}) for s_ in both]), {c: "{:+.2f}" for c in ["Primary delta (m)", "P3 delta (m)", "Difference (m)"]})]
    L += [""]
    L += ["## 11. Figures", "", "![Length and per-routed length](figures/fig1_length_and_per_routed.png)", "", "*Figure 1. Unique network length (left) and unique length per routed target (right) for each baseline and omission scenario. Absolute length falls mainly because fewer targets are connected; per-routed length is the comparable quantity. Source: `c1_scenario_comparison.csv` in the two compare folders.*", "", "![Length inside omitted footprints](figures/fig2_length_inside_omitted_footprints.png)", "", "*Figure 2. Route length inside the footprints each scenario omits, for the baseline routes of the same remaining targets (footprints known) and for the omission-run routes (footprints unknown). One deterministic scenario per mode; not an effect size. Source: `c1_omitted_footprint_exposure.csv`.*", "", "Both figures are generated from the CSV outputs listed in the manifest.", ""]
    L += ["## 12. Limitations and threats to validity", "",
          "- One village, one deterministic scenario per mode, no repeats: differences are descriptive, not statistical.",
          "- Omission is simulated on candidate footprints; it is not a measured detector false-negative rate and does not reflect real error structure.",
          "- 'Crossing' means a route geometry intersects a candidate footprint polygon. Candidates are unverified; this says nothing about legal access, passability or real damage.",
          "- Routes are planning proxies. Costs are ordinal model units, not construction cost. Slope comes from a ~30 m DEM resampled to 10 m.",
          "- Omitted groups differ in size and location (merged candidates are the largest and probably spatially concentrated; this was not measured), and the omitted targets were themselves part of the baseline network, so rate comparisons mix target composition with footprint knowledge.",
          "- Shared-edge attribution differs between runs; per-target segments are not individually comparable.",
          "- The slope >10 degrees and repaired-parcel lengths rest on a handful of cells and are not interpreted.",
          "- The building-penalty multiplier (x4) and the penalised class set are design parameters, not facts; equal target weights (1.0) are likewise a design choice. None has been confirmed against reference data (section 3.1).",
          "- The three baselines/runs were produced by different recorded runner versions (section 5.1); a v1.3 `--perturb none` reproduction of the primary baseline has not been run.",
          "- Input imagery licence: the Esri World Imagery mosaic used to derive the building candidates has an unverified licence status (project document `DAMARAKUNTA_STAGE_B_C_PROPOSALS.md`, Part B). Derived maps and footprints must not be described as licence-cleared.", ""]
    L += ["## 13. Conclusions", "", "**Supported by these experiments**", ""]
    mm = ce.loc["omit_merge"] if "omit_merge" in ce.index else None
    if mm is not None: L += [f"- In the primary baseline (one village, one deterministic scenario), the route length inside the omitted UNRESOLVED_MERGE footprints {word(mm.baseline_retained_len_in_omitted_m, mm.omission_len_in_omitted_m, ' m')} when the planner no longer knew those footprints; the number of routes crossing them went from {int(mm.baseline_retained_cross_omitted)} to {int(mm.omission_cross_omitted)}. The same measure fell under P3, where the planner ignores footprints (section 10.3)."]
    L += ["- Absolute network length falls with omission mainly because fewer targets are connected; per-routed-target length is the comparable quantity (section 7).",
          "- The runner's own crossing metrics are not comparable across omission runs and were replaced by full-set scoring (section 10).",
          "- Facility-route differences in the primary omit_merge run are attributable to removed-penalty cells (section 9).", "",
          "**Not supported**", "",
          "- Any measured segmentation false-negative rate, detector accuracy, or field validation.",
          "- Claims of legal access, passability, real construction cost or savings.",
          "- That a shorter network after omission is more efficient.",
          "- A general effect size for omission: the scenarios are single, deterministic and from one village.",
          "- C3 (transfer): no second village has been run.", ""]
    L += ["## 14. Manifest of files", "", "SHA-256 of every input file used (comparison, footprint and exposure folders). Files in this report folder are listed in `manifest_report_files.csv`.", ""]
    mrows = []
    for b in blocks:
        for d in (b.cmp_d, b.fp_d, b.ex_d):
            for f in sorted(d.rglob("*")):
                if f.is_file(): mrows.append(dict(File=str(f.relative_to(root)), Bytes=f.stat().st_size, **{"SHA-256": sha(f)}))
    L += [mdt(pd.DataFrame(mrows), {"Bytes": "{:.0f}"}), ""]
    (out / "C1_report.md").write_text("\n".join(L), encoding="utf-8")
    # ---------- built-in validation of the written report ----------
    import re, difflib
    md = (out / "C1_report.md").read_text(encoding="utf-8"); VR = []
    def vr(i, ok, name, det=""): VR.append(dict(id=i, status="PASS" if ok else "FAIL", name=name, detail=det))
    for f_ in ("C1_report.md", "figures/fig1_length_and_per_routed.png", "figures/fig2_length_inside_omitted_footprints.png"):
        vr("V01 " + f_, (out / f_).exists() and (out / f_).stat().st_size > 1000, "file exists and is non-empty", str((out / f_).stat().st_size if (out / f_).exists() else "missing"))
    vr("V02", all(f.stat().st_size > 0 for f in out.rglob("*") if f.is_file()), "no empty files in the report folder")
    vr("V03", not re.search(r"\bnan\b|\binf\b|NOT FOUND|TODO|<PASTE|\{[a-z_]+\}", md, flags=re.I), "no NaN/inf/NOT FOUND/TODO/placeholder tokens in the report")
    vr("V04", len(re.findall(r"^## \d+\. ", md, flags=re.M)) == 14, "14 numbered sections present", str(re.findall(r"^## (\d+)\. ", md, flags=re.M)))
    for b_ in blocks:
        for r_ in b_.cmp.itertuples():
            for val, nd in ((r_.net_unique_len_m, 2), (r_.net_unique_len_per_routed_m, 2), (r_.credit_pct, 2), (r_.facility_unique_len_m, 2)):
                vr(f"V10 {short(r_.run)} {nd}", f"{val:.{nd}f}" in md, "scenario value from CSV appears in the report", f"{val:.{nd}f}")
        for r_ in b_.ex.itertuples():
            for val in (r_.baseline_retained_len_in_omitted_m, r_.omission_len_in_omitted_m):
                vr(f"V11 {short(r_.run)}", f"{val:.2f}" in md, "exposure value from CSV appears with 2 decimals", f"{val:.2f}")
        c7 = b_.val[b_.val.id.str.startswith("C07")]
        vr(f"V12 {b_.title}", f"C07 PASS {int((c7.status=='PASS').sum())}, INFO {int((c7.status=='INFO').sum())}" in md, "C07 summary equals validation CSV", f"{(c7.status=='PASS').sum()} PASS / {(c7.status=='INFO').sum()} INFO")
        vr(f"V13 {b_.title}", int(b_.cmp.omitted.sum()) == len(b_.om) and (b_.cmp.routed + b_.cmp.omitted == b_.cmp.original_targets).all(), "omitted counts reconcile to 163 in every run")
    vr("V14", "C1_PROVISIONAL" not in md and "built-up cost 3.0 " not in md.replace("built-up cost 3.0, a provisional", ""), "built-up cost 3.0 no longer listed as a provisional setting of these runs")
    Vr = pd.DataFrame(VR); Vr.to_csv(out / "report_validation.csv", index=False)
    # ---------- comparison with v1 ----------
    if a.v1_report and Path(a.v1_report).exists():
        d = list(difflib.unified_diff(Path(a.v1_report).read_text(encoding="utf-8").splitlines(), md.splitlines(), "C1_report_v1.md", "C1_report_v2.md", lineterm="", n=0))
        (out / "v1_vs_v2_diff.txt").write_text("\n".join(d), encoding="utf-8")
        print(f"v1 vs v2: {sum(1 for x in d if x.startswith('+') and not x.startswith('+++'))} lines added, {sum(1 for x in d if x.startswith('-') and not x.startswith('---'))} removed (see v1_vs_v2_diff.txt)")
    pd.DataFrame([dict(file=str(f.relative_to(out)), bytes=f.stat().st_size, sha256=sha(f)) for f in sorted(out.rglob("*")) if f.is_file() and f.name != "manifest_report_files.csv"]).to_csv(out / "manifest_report_files.csv", index=False)
    print("written:", out); print("validation: PASS", int((Vr.status == "PASS").sum()), "FAIL", int((Vr.status == "FAIL").sum()))
    if (Vr.status == "FAIL").any(): print(Vr[Vr.status == "FAIL"].to_string(index=False)); sys.exit(3)
