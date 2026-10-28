#!/usr/bin/env python
"""run_first_village.py - reproducibility + reporting driver for the Damarakunta first-village case study.

It does NOT change the planner, its parameters, or any existing file. It:
  S0 preflight   : checks that the reference run (default run7_regress) and the reproduced run (default fv_repro1)
                   exist; records SHA-256 of every input file named in the reference run's summary.json.
  S1 repro_check : compares reference vs reproduced run (inputs hashes, parameters, plan_comparison.csv,
                   target_table.csv, summary fields, GeoPackage layers/geometry). Result is COMPUTED: PASS or FAIL.
  S2 access_gain : runs scripts\\summarise_access_gain.py (read-only) on BOTH runs into a NEW folder.
  S3 report      : runs scripts\\make_first_village_report.py (reads outputs; diagnoses failed targets from records).
Everything is written under  <village>\\results\\first_village_runs\\<tag>\\  (new folder; refuses to exist already).
Use --dry-run to print exactly what would run without creating anything.
Exit code: 0 = all stages ran and the reproducibility check PASSED; 1 = a stage failed or the check FAILED; 2 = preflight error.
"""
import argparse, datetime as dt, hashlib, json, os, platform, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent if HERE.name.lower() == "scripts" else HERE
IGNORE_PARAMS = {"tag", "out_root", "no_map"}
INPUT_PARAM_KEYS = ["access_gpkg", "roads", "cost", "worldcover", "blocked", "slope", "buildings", "raster", "v4_script"]


def die(msg, code=2):
    print("ERROR:", msg); sys.exit(code)


def sha256(p, chunk=1 << 22):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(chunk), b""):
            h.update(b)
    return h.hexdigest()


def resolve(p, root):
    q = Path(str(p).replace("\\", "/")) if os.sep == "/" else Path(p)  # tolerate Windows-style paths on other systems
    return q if q.is_absolute() else (root / q)


def norm_path(p, root):
    return os.path.normcase(os.path.normpath(str(resolve(p, root))))


def load_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def versions():
    v = {"python": platform.python_version(), "platform": platform.platform()}
    for n in ("numpy", "pandas", "geopandas", "shapely", "rasterio"):
        try:
            v[n] = __import__(n).__version__
        except Exception:
            v[n] = None
    return v


# ------------------------------------------------------------------------------- repro comparison
def _layers(gpkg):
    import geopandas as gpd
    try:
        return list(gpd.list_layers(gpkg)["name"])
    except AttributeError:
        import fiona
        return list(fiona.listlayers(str(gpkg)))


def _df_sig(df):
    import pandas as pd
    d = df.drop(columns=[c for c in df.columns if c == "geometry"]).copy()
    for c in d.columns:
        if pd.api.types.is_float_dtype(d[c]):
            d[c] = d[c].round(6)
    d = d.astype(str)
    d = d.sort_values(list(d.columns)).reset_index(drop=True) if len(d.columns) else d
    return d


def compare_csv(a, b):
    import pandas as pd
    A, B = pd.read_csv(a), pd.read_csv(b)
    if list(A.columns) != list(B.columns):
        return False, f"columns differ: {list(A.columns)} vs {list(B.columns)}"
    if len(A) != len(B):
        return False, f"row count {len(A)} vs {len(B)}"
    if _df_sig(A).equals(_df_sig(B)):
        return True, f"{len(A)} rows identical (floats rounded to 6 dp)"
    diff = (_df_sig(A) != _df_sig(B)).any()
    return False, "values differ in columns: " + ", ".join(diff[diff].index)


def compare_gpkg(a, b):
    import geopandas as gpd, shapely
    la, lb = _layers(a), _layers(b)
    if sorted(la) != sorted(lb):
        return False, f"layers differ: {la} vs {lb}"
    notes, ok = [], True
    for name in sorted(la):
        A, B = gpd.read_file(a, layer=name), gpd.read_file(b, layer=name)
        if len(A) != len(B):
            ok = False; notes.append(f"{name}: feature count {len(A)} vs {len(B)}"); continue
        if "geometry" in A.columns and A.geometry.notna().any():
            ga = sorted(shapely.to_wkb(shapely.set_precision(g, 0.001)) for g in A.geometry if g is not None)
            gb = sorted(shapely.to_wkb(shapely.set_precision(g, 0.001)) for g in B.geometry if g is not None)
            gok = ga == gb
        else:
            gok = True
        aok = _df_sig(A).equals(_df_sig(B))
        ok &= gok and aok
        notes.append(f"{name}: n={len(A)} geometry {'identical' if gok else 'DIFFERENT'} (1 mm), attributes {'identical' if aok else 'DIFFERENT'}")
    return ok, "; ".join(notes)


def deep_diff(a, b, path="$", out=None, limit=8, root=None):
    """Structural comparison of two JSON values. NaN equals NaN and None; floats compared to 9 significant digits."""
    import math
    out = [] if out is None else out
    if len(out) >= limit:
        return out
    nanlike = lambda v: v is None or (isinstance(v, float) and math.isnan(v))
    if nanlike(a) and nanlike(b):
        return out
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b), key=str):
            if k not in a or k not in b:
                out.append(f"{path}.{k}: present in only one run ({'reference' if k in a else 'reproduced'})")
            else:
                deep_diff(a[k], b[k], f"{path}.{k}", out, limit, root)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append(f"{path}: list length {len(a)} vs {len(b)}")
        else:
            for i, (x, y) in enumerate(zip(a, b)):
                deep_diff(x, y, f"{path}[{i}]", out, limit, root)
    elif isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool) and not isinstance(b, bool):
        if not math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-12):
            out.append(f"{path}: {a!r} vs {b!r}")
    elif isinstance(a, str) and isinstance(b, str) and root is not None and (("\\" in a or "/" in a) and ("\\" in b or "/" in b)):
        if norm_path(a, root) != norm_path(b, root):   # same file written absolute vs relative counts as equal
            out.append(f"{path}: {a!r} vs {b!r} (different paths)")
    elif a != b:
        out.append(f"{path}: {a!r} vs {b!r}")
    return out


def compare_runs(ref_dir, rep_dir, root, input_hashes):
    checks = []

    def add(name, passed, detail):
        checks.append({"check": name, "passed": bool(passed), "detail": detail})

    sr, sp = load_json(ref_dir / "summary.json"), load_json(rep_dir / "summary.json")
    # recorded input hashes (planner's own) must match between runs
    ir, ip = sr.get("inputs", {}), sp.get("inputs", {})
    add("summary.inputs hashes equal (reference vs reproduced)", ir == ip and bool(ir), f"{ir} vs {ip}" if ir != ip else f"{len(ir)} hashes equal")
    # and match the file bytes we hash now (planner may hash differently -> informational)
    for k in ir:
        mine = input_hashes.get(k)
        if mine:
            add(f"planner hash of '{k}' equals sha256 of file now", mine == ir[k],
                "equal" if mine == ir[k] else "different: file changed since the run, or the planner hashes differently")
    pr, pp = sr.get("params", {}), sp.get("params", {})
    diffs = []
    for k in sorted(set(pr) | set(pp)):
        if k in IGNORE_PARAMS:
            continue
        a, b = pr.get(k), pp.get(k)
        if isinstance(a, str) and isinstance(b, str) and ("\\" in a or "/" in a or "\\" in b or "/" in b):
            a, b = norm_path(a, root), norm_path(b, root)
        if a != b:
            diffs.append(f"{k}: {pr.get(k)!r} vs {pp.get(k)!r}")
    add("parameters equal (ignoring tag, out_root, no_map)", not diffs, "; ".join(diffs) or f"{len(pr)} parameters compared")
    for fname in ("plan_comparison.csv", "target_table.csv"):
        ok, d = compare_csv(ref_dir / fname, rep_dir / fname)
        add(fname + " identical", ok, d)
    for key in ("c2_check", "failed_targets", "plan_comparison", "data_check", "constraints_resolved"):
        d = deep_diff(sr.get(key), sp.get(key), f"$.{key}", root=root)
        add(f"summary.json['{key}'] identical (NaN = null)", not d, "equal" if not d else "DIFFERENT: " + " | ".join(d))
    ok, d = compare_gpkg(ref_dir / "network_v2.gpkg", rep_dir / "network_v2.gpkg")
    add("network_v2.gpkg layers/geometry/attributes identical", ok, d)
    return {"overall": "PASS" if all(c["passed"] for c in checks) else "FAIL", "checks": checks,
            "note": "PASS means the reproduced run matches the reference run on the checks listed; it does not validate the planning result."}


# ------------------------------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--village-dir", default=str(Path("Siddipet") / "Damarakunta"))
    ap.add_argument("--ref-run", default="run7_regress")
    ap.add_argument("--repro-run", default="fv_repro1")
    ap.add_argument("--runs-root", default=None, help="default <village>\\results\\planning_experiments\\network_v2")
    ap.add_argument("--experiments-dir", default=None, help="default <village>\\results\\planning_experiments\\experiments_v1\\full1 (read only)")
    ap.add_argument("--out-root", default=None, help="default <village>\\results\\first_village_runs")
    ap.add_argument("--tag", default=None, help="default fv_<YYYYmmdd_HHMMSS>")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    village = resolve(a.village_dir, ROOT)
    runs_root = resolve(a.runs_root, ROOT) if a.runs_root else village / "results" / "planning_experiments" / "network_v2"
    exp_dir = resolve(a.experiments_dir, ROOT) if a.experiments_dir else village / "results" / "planning_experiments" / "experiments_v1" / "full1"
    out_root = resolve(a.out_root, ROOT) if a.out_root else village / "results" / "first_village_runs"
    tag = a.tag or "fv_" + dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = out_root / tag
    ref_dir, rep_dir = runs_root / a.ref_run, runs_root / a.repro_run
    py = sys.executable
    ag_root, ag_tag = run_dir / "access_gain", "ag"
    ag_dir = ag_root / ag_tag
    scripts = HERE
    stages = [
        {"name": "S2_access_gain", "cmd": [py, str(scripts / "summarise_access_gain.py"), "--runs-root", str(runs_root),
                                             "--runs", a.ref_run, a.repro_run, "--out-root", str(ag_root), "--tag", ag_tag],
         "outputs": [str(ag_dir)]},
        {"name": "S3_report", "cmd": [py, str(scripts / "make_first_village_report.py"), "--run-dir", str(run_dir), "--ref-run", a.ref_run,
                                       "--repro-run", a.repro_run, "--runs-root", str(runs_root), "--experiments-dir", str(exp_dir),
                                       "--ag-dir", str(ag_dir), "--village-dir", str(village)],
         "outputs": [str(run_dir / "report")]},
    ]
    print(f"project root     : {ROOT}\nreference run    : {ref_dir}\nreproduced run   : {rep_dir}\nnew run folder   : {run_dir}")
    print("stages:\n  S0_preflight   (in process) existence checks + SHA-256 of planner input files (read only)\n"
          "  S1_repro_check (in process) compare reference vs reproduced run -> repro_check.json")
    for s in stages:
        print(f"  {s['name']}:\n    " + " ".join(f'"{c}"' if " " in c else c for c in s["cmd"]))
    print("writes only under:", run_dir, "(and nothing else). No existing file is modified.")
    if a.dry_run:
        print("--dry-run: nothing created."); return 0

    # ---- S0 preflight -----------------------------------------------------------------------------
    for d, nm in ((ref_dir, "reference"), (rep_dir, "reproduced")):
        for f in ("summary.json", "plan_comparison.csv", "target_table.csv", "network_v2.gpkg"):
            if not (d / f).exists():
                die(f"{nm} run is missing {d / f}")
    for s in stages:
        if not Path(s["cmd"][1]).exists():
            die(f"script not found: {s['cmd'][1]}")
    if run_dir.exists():
        die(f"{run_dir} already exists; refusing to overwrite. Use --tag.")
    run_dir.mkdir(parents=True, exist_ok=False)
    (run_dir / "logs").mkdir()
    sref = load_json(ref_dir / "summary.json")
    inputs, input_hashes, missing = [], {}, []
    for k in INPUT_PARAM_KEYS:
        v = sref.get("params", {}).get(k)
        if not v:
            continue
        p = resolve(v, ROOT)
        if not p.exists():
            missing.append(str(p)); inputs.append({"param": k, "path": str(p), "exists": False}); continue
        t0 = time.time(); h = sha256(p)
        inputs.append({"param": k, "path": str(p), "exists": True, "bytes": p.stat().st_size, "sha256": h, "hash_seconds": round(time.time() - t0, 1)})
        input_hashes[k] = h
    # the planner records hashes under 'access','roads','cost' -> map param names
    for src, dst in (("access_gpkg", "access"), ("roads", "roads"), ("cost", "cost")):
        if src in input_hashes:
            input_hashes[dst] = input_hashes[src]
    log = {"tag": tag, "started_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "argv": sys.argv, "cwd": str(Path.cwd()), "project_root": str(ROOT),
           "versions": versions(), "reference_run": str(ref_dir), "reproduced_run": str(rep_dir),
           "inputs": inputs, "missing_inputs": missing, "stages": [], "final_status": "RUNNING"}

    def save():
        (run_dir / "run_log.json").write_text(json.dumps(log, indent=2), encoding="utf-8")
    save()
    log["stages"].append({"name": "S0_preflight", "exit_code": 0 if not missing else 1, "status": "OK" if not missing else "MISSING_INPUTS", "detail": f"{len(inputs)} inputs hashed"})
    save()
    if missing:
        print("WARNING: planner input files missing:", missing)
    input_missing = bool(missing)

    # ---- S1 repro check --------------------------------------------------------------------------------
    t0 = time.time()
    try:
        rc = compare_runs(ref_dir, rep_dir, ROOT, input_hashes)
        status, code = rc["overall"], 0
    except Exception as ex:  # report honestly
        rc = {"overall": "ERROR", "error": f"{type(ex).__name__}: {ex}", "checks": []}
        status, code = "ERROR", 1
    (run_dir / "repro_check.json").write_text(json.dumps(rc, indent=2), encoding="utf-8")
    log["stages"].append({"name": "S1_repro_check", "exit_code": code, "status": status, "seconds": round(time.time() - t0, 1),
                          "output": str(run_dir / "repro_check.json")})
    save()
    print("S1 reproducibility check:", status)
    for c in rc.get("checks", []):
        print(("  PASS  " if c["passed"] else "  FAIL  ") + c["check"] + " - " + (c["detail"][:160] if c["passed"] else c["detail"]))

    # ---- S2/S3 subprocess stages -------------------------------------------------------------------------
    failed = status != "PASS" or input_missing
    for s in stages:
        t0 = time.time()
        so, se = run_dir / "logs" / (s["name"] + ".stdout.txt"), run_dir / "logs" / (s["name"] + ".stderr.txt")
        print(f"running {s['name']} ...", flush=True)
        try:
            with open(so, "w", encoding="utf-8", errors="replace") as fo, open(se, "w", encoding="utf-8", errors="replace") as fe:
                r = subprocess.run(s["cmd"], stdout=fo, stderr=fe, cwd=str(ROOT))
            ec = r.returncode
        except Exception as ex:
            ec = -1; se.write_text(f"{type(ex).__name__}: {ex}", encoding="utf-8")
        outs_ok = all(Path(o).exists() for o in s["outputs"])
        st = "OK" if ec == 0 and outs_ok else ("FAILED" if ec != 0 else "NO_OUTPUT")
        failed |= st != "OK"
        log["stages"].append({"name": s["name"], "command": s["cmd"], "exit_code": ec, "status": st, "seconds": round(time.time() - t0, 1),
                              "stdout_log": str(so), "stderr_log": str(se), "expected_outputs": s["outputs"], "outputs_exist": outs_ok})
        save()
        print(f"  {s['name']}: {st} (exit {ec}); logs: {so.name}, {se.name}")
        if st != "OK" and s["name"] == "S2_access_gain":
            print("  access-gain failed; the report will state that access-gain figures are unavailable.")
    log["finished_utc"] = dt.datetime.now(dt.timezone.utc).isoformat()
    log["final_status"] = "ALL_STAGES_OK_AND_REPRO_PASS" if not failed else "COMPLETED_WITH_FAILURES_SEE_STAGES"
    save()
    print("final status:", log["final_status"], "\nrun log:", run_dir / "run_log.json")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
