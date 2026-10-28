"""Single-command runner for the rural planning pipeline (Workflow A: no manual digitization required).

  python scripts\\run_rural_planning_pipeline.py --config configs\\damarakunta.json            run what is out of date
  python scripts\\run_rural_planning_pipeline.py --config configs\\damarakunta.json --list     show stages and cache status
  python scripts\\run_rural_planning_pipeline.py --config ... --dry-run                         validate + show what would run
  python scripts\\run_rural_planning_pipeline.py --config ... --force extract_buildings_v8      rerun one stage (and later ones)
  python scripts\\run_rural_planning_pipeline.py --config ... --only access

What it does:  1) pre-flight validation (CRS, size, resolution, nodata share, geometry validity, class-ID range,
shape match)  2) runs each enabled stage as a subprocess with the SAME python  3) skips a stage when its inputs,
script and arguments are unchanged AND its outputs exist (SHA-256 signature cache)  4) writes a run manifest
(inputs hashes, versions, parameters, per-stage status, warnings) and a short report into a NEW folder per run.

Safety: never deletes or overwrites inputs. The expensive inference stage is never started automatically: if its
outputs are missing the run stops with an instruction; if they exist but have no recorded provenance they are
'ADOPTED' (hashed and recorded, not rerun). Stages write to their own versioned output folders.
"""
import argparse, hashlib, json, os, platform, subprocess, sys, time
from datetime import datetime
from pathlib import Path


def sha256(p, block=1 << 20):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(block), b""):
            h.update(b)
    return h.hexdigest()


class HashCache:
    """sha256 keyed by (path,size,mtime) so the 250 MB mosaic is only hashed when it changes."""
    def __init__(self, path):
        self.path = Path(path); self.d = json.loads(self.path.read_text()) if self.path.exists() else {}
    def get(self, p):
        p = str(p); st = os.stat(p); key = f"{st.st_size}:{st.st_mtime_ns}"
        e = self.d.get(p)
        if not e or e["key"] != key:
            e = {"key": key, "sha256": sha256(p)}; self.d[p] = e
        return e["sha256"]
    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True); self.path.write_text(json.dumps(self.d, indent=1))


# ------------------------------------------------------------------------------ config
def load_config(path):
    cfg = json.loads(Path(path).read_text(encoding="utf-8"))
    root = Path(cfg["root"])
    paths = {}
    for k, v in cfg["paths"].items():
        if isinstance(v, str) and (k.endswith("_layer") or k.endswith("_name")):
            paths[k] = v
        else:
            paths[k] = str((Path(v) if os.path.isabs(v) or ":" in v[:3] else root / v))
    cfg["paths"] = {k: os.path.normpath(v) if not (k.endswith("_layer") or k.endswith("_name")) else v for k, v in paths.items()}
    return cfg


def interp(s, paths):
    if not isinstance(s, str):
        return s
    for k, v in paths.items():
        s = s.replace("{" + k + "}", v)
    return s


# ------------------------------------------------------------------------------ preflight
def preflight(cfg):
    import numpy as np
    out = []                                   # (level, check, message)
    def add(l, c, m): out.append((l, c, m))
    P = cfg["paths"]; crs_ok = cfg.get("crs", "EPSG:32644")
    try:
        import rasterio, geopandas as gpd
    except Exception as e:
        add("ERROR", "imports", f"rasterio/geopandas not importable: {e}"); return out
    # raster
    r = P.get("raster")
    if not r or not os.path.exists(r):
        add("ERROR", "raster", f"missing: {r}")
    else:
        with rasterio.open(r) as s:
            epsg = s.crs.to_epsg() if s.crs else None
            add("OK" if f"EPSG:{epsg}" == crs_ok else "ERROR", "raster.crs", f"{s.crs} (expected {crs_ok})")
            add("OK" if s.count >= 3 else "ERROR", "raster.bands", f"{s.count} bands")
            add("OK" if abs(s.res[0] - cfg.get("resolution_m", 0.6)) < 0.02 else "WARN", "raster.res", f"{s.res} m")
            add("INFO", "raster.size", f"{s.width} x {s.height}, nodata={s.nodata}, dtype={s.dtypes[0]}")
            f = max(1, int(max(s.width, s.height) / 1500))
            a = s.read([1, 2, 3], out_shape=(3, s.height // f, s.width // f))
            blank = float((a == 0).all(axis=0).mean())
            add("WARN" if blank > 0.001 else "OK", "raster.blank", f"{100 * blank:.2f}% of pixels are all-zero (no imagery). "
                "They are NOT land cover; extraction rejects building blobs on them." if blank > 0.001 else "no blank area")
            rshape = (s.height, s.width)
    # vectors
    for key, layer_key in (("roads", "roads_layer"), ("facilities", "facilities_layer"), ("boundary", "boundary_layer"), ("windows_gpkg", None)):
        p = P.get(key)
        opt = key in cfg.get("optional_inputs", [])
        if not p or not os.path.exists(p):
            add("WARN" if opt else "ERROR", key, f"missing: {p}"); continue
        try:
            layer = P.get(layer_key) if layer_key else ("windows" if key == "windows_gpkg" else None)
            g = gpd.read_file(p, layer=layer) if layer else gpd.read_file(p)
            bad = int((~g.geometry.is_valid).sum()); empty = int(g.geometry.is_empty.sum())
            add("OK" if str(g.crs.to_epsg()) == crs_ok.split(":")[1] else "WARN", f"{key}.crs", f"{g.crs.to_epsg()} (will be reprojected to {crs_ok} if needed)")
            add("OK" if bad == 0 and empty == 0 else "WARN", f"{key}.geometry", f"{len(g)} features, {bad} invalid, {empty} empty")
        except Exception as e:
            add("ERROR", key, f"cannot read: {e}")
    # predictions
    pc, pb = P.get("pred_classes"), P.get("building_prob")
    if pc and os.path.exists(pc):
        with rasterio.open(pc) as s:
            f = max(1, int(max(s.width, s.height) / 2000))
            a = s.read(1, out_shape=(s.height // f, s.width // f))
            ids = sorted(int(x) for x in np.unique(a))
            add("OK" if max(ids) <= 7 else "ERROR", "pred.class_ids", f"IDs present (subsampled): {ids}; expected within 0-7")
            add("OK" if r and (s.height, s.width) == rshape else "ERROR", "pred.shape", f"{(s.height, s.width)} vs raster {rshape if r else '?'}")
            add("OK" if s.crs and f"EPSG:{s.crs.to_epsg()}" == crs_ok else "ERROR", "pred.crs", str(s.crs))
        if pb and os.path.exists(pb):
            with rasterio.open(pb) as s:
                add("OK" if s.dtypes[0] == "uint8" else "WARN", "pred.prob", f"building_prob dtype {s.dtypes[0]} (expected uint8 0-255 = softmax channel {cfg.get('building_class_id', 2)})")
    else:
        add("INFO", "pred", "prediction rasters not present yet (inference stage will be required)")
    for k in ("worldcover", "cost"):
        p = P.get(k)
        if p and not os.path.exists(p):
            add("WARN" if k in cfg.get("optional_inputs", []) else "ERROR", k, f"missing: {p}")
    return out


# ------------------------------------------------------------------------------ stages
def stage_paths(st, P):
    return [os.path.normpath(interp(x, P)) for x in st.get("inputs", [])], [os.path.normpath(interp(x, P)) for x in st.get("outputs", [])]


def signature(st, P, hc):
    ins, _ = stage_paths(st, P)
    script = os.path.normpath(interp(st["script"], P))
    d = {"script": hc.get(script) if os.path.exists(script) else None,
         "args": [interp(a, P) for a in st.get("args", [])],
         "inputs": {i: (hc.get(i) if os.path.exists(i) else None) for i in ins}}
    return hashlib.sha256(json.dumps(d, sort_keys=True).encode()).hexdigest(), d


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", required=True)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--force", nargs="*", default=[], help="stage names to rerun (later stages that depend on them rerun too)")
    ap.add_argument("--skip-preflight", action="store_true")
    ap.add_argument("--run-name", default=None)
    a = ap.parse_args()

    cfg = load_config(a.config); P = cfg["paths"]
    results = Path(P["results_dir"]); cache_file = results / "pipeline_cache.json"
    hc = HashCache(results / "hash_cache.json")
    cache = json.loads(cache_file.read_text()) if cache_file.exists() else {}
    stages = [s for s in cfg["stages"]]
    names = [s["name"] for s in stages]
    for n in a.force + (a.only or []):
        if n not in names:
            sys.exit(f"unknown stage '{n}'. stages: {names}")

    print(f"Village: {cfg['village']} | config: {a.config}")
    pre = []
    if not a.skip_preflight:
        pre = preflight(cfg)
        print("\nPRE-FLIGHT")
        for l, c, m in pre:
            print(f"  [{l:<5}] {c:<16} {m}")
        errs = [x for x in pre if x[0] == "ERROR"]
        if errs and not a.list:
            sys.exit(f"\n{len(errs)} pre-flight ERROR(s); fix them (or --skip-preflight to override at your own risk).")

    # plan
    forced_from = None
    plan = []
    for st in stages:
        sig, detail = signature(st, P, hc)
        _, outs = stage_paths(st, P)
        have = all(os.path.exists(o) for o in outs) if outs else False
        rec = cache.get(st["name"])
        if not st.get("enabled", True):
            status = "DISABLED"
        elif st["name"] in a.force or forced_from is not None:
            status = "RUN"; forced_from = forced_from or st["name"]
        elif have and rec and rec.get("signature") == sig:
            status = "UP_TO_DATE"
        elif have and not rec:
            status = "ADOPT"                    # outputs exist, no provenance recorded
        elif have and rec:
            status = "RUN"; forced_from = forced_from or st["name"]
        else:
            status = "RUN"; forced_from = forced_from or st["name"]
        if a.only and st["name"] not in a.only and status in ("RUN", "UP_TO_DATE", "ADOPT"):
            status = status + "(not selected)"
        plan.append((st, sig, detail, outs, status))
    print("\nSTAGES")
    for st, sig, d, outs, status in plan:
        print(f"  {st['name']:<26} {status:<20} {st.get('note', '')}")
    if a.list or a.dry_run:
        hc.save(); return

    run_id = a.run_name or datetime.now().strftime("%Y%m%d_%H%M%S")
    rdir = results / "pipeline_runs" / run_id
    rdir.mkdir(parents=True, exist_ok=False)
    manifest = {"run_id": run_id, "village": cfg["village"], "config": str(Path(a.config).resolve()),
                "config_sha256": sha256(a.config), "started": datetime.now().isoformat(timespec="seconds"),
                "python": sys.version.split()[0], "platform": platform.platform(), "preflight": pre, "stages": [],
                "inputs": {k: (hc.get(v) if os.path.isfile(v) else None) for k, v in P.items()
                           if isinstance(v, str) and not k.endswith(("_layer", "_name")) and os.path.isfile(v)}}
    for mod in ("numpy", "rasterio", "geopandas", "shapely", "pandas", "cv2", "networkx"):
        try:
            manifest.setdefault("versions", {})[mod] = __import__(mod).__version__
        except Exception:
            manifest.setdefault("versions", {})[mod] = None
    failed = False
    import shutil
    for st, sig, detail, outs, status in plan:
        sig, detail = signature(st, P, hc)          # recomputed NOW: upstream stages may have just rewritten this stage's inputs
        rec = {"name": st["name"], "planned": status, "signature": sig}
        if status in ("DISABLED",) or "(not selected)" in status:
            rec["status"] = status
        elif failed:
            rec["status"] = "NOT_RUN_EARLIER_FAILURE"
        elif status == "UP_TO_DATE":
            rec["status"] = "SKIPPED_UP_TO_DATE"
        elif status == "ADOPT":
            rec.update(status="ADOPTED_EXISTING_OUTPUTS", warning="outputs existed with no recorded provenance; hashed and recorded, NOT rerun",
                       output_hashes={o: hc.get(o) for o in outs if os.path.isfile(o)})
            cache[st["name"]] = {"signature": sig, "adopted": True, "when": datetime.now().isoformat(timespec="seconds")}
            print(f"[{st['name']}] ADOPTED existing outputs (provenance unknown, recorded)")
        else:
            if st.get("expensive") and not all(os.path.exists(o) for o in outs):
                print(f"[{st['name']}] outputs missing and this stage is EXPENSIVE; not started automatically.\n"
                      f"   run it yourself:  {sys.executable} {interp(st['script'], P)} {' '.join(interp(x, P) for x in st.get('args', []))}")
                rec["status"] = "BLOCKED_EXPENSIVE_STAGE_NOT_RUN"; failed = True
                manifest["stages"].append(rec); continue
            bk = [o for o in outs if os.path.isfile(o) and os.path.getsize(o) < 2 << 30]
            if bk:                                   # back up previous outputs before a stage may replace them
                bdir = rdir / f"backup_before_{st['name']}"; bdir.mkdir(exist_ok=True)
                for o in bk:
                    shutil.copy2(o, bdir / os.path.basename(o))
                rec["backed_up"] = [str(bdir / os.path.basename(o)) for o in bk]
                print(f"[{st['name']}] previous outputs backed up to {bdir}")
            cmd = [sys.executable, os.path.normpath(interp(st["script"], P))] + [interp(x, P) for x in st.get("args", [])]
            log = rdir / f"{st['name']}.log"
            print(f"\n[{st['name']}] running: {' '.join(cmd)}")
            t0 = time.time()
            with open(log, "w", encoding="utf-8") as lf:
                pr = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
                for line in pr.stdout:
                    lf.write(line); print("   " + line.rstrip())
                pr.wait()
            rec.update(seconds=round(time.time() - t0, 1), returncode=pr.returncode, log=str(log), command=cmd)
            missing = [o for o in outs if not os.path.exists(o)]
            if pr.returncode != 0 or missing:
                rec["status"] = "FAILED"; rec["missing_outputs"] = missing
                if st.get("optional"):
                    rec["status"] = "FAILED_OPTIONAL"; print(f"[{st['name']}] optional stage failed; continuing")
                else:
                    failed = True; print(f"[{st['name']}] FAILED (returncode {pr.returncode}, missing outputs {missing})")
            else:
                rec["status"] = "RAN_OK"
                rec["output_hashes"] = {o: hc.get(o) for o in outs if os.path.isfile(o)}
                cache[st["name"]] = {"signature": sig, "when": datetime.now().isoformat(timespec="seconds")}
                for jf in st.get("summary_json", []):
                    jp = os.path.normpath(interp(jf, P))
                    if os.path.exists(jp):
                        rec.setdefault("summaries", {})[jp] = json.loads(Path(jp).read_text())
        manifest["stages"].append(rec)
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps(cache, indent=1))
    manifest["finished"] = datetime.now().isoformat(timespec="seconds")
    manifest["overall"] = "FAILED_OR_BLOCKED" if failed else "OK"
    (rdir / "run_manifest.json").write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")
    lines = [f"# Pipeline run {run_id} - {cfg['village']}", f"Overall: **{manifest['overall']}**", "",
             "Outputs are UNVERIFIED model-derived candidates (not surveyed buildings, not construction-ready roads).", "",
             "| stage | status | seconds |", "|---|---|---|"]
    lines += [f"| {s['name']} | {s['status']} | {s.get('seconds', '')} |" for s in manifest["stages"]]
    warns = [f"- {c}: {m}" for l, c, m in pre if l in ("WARN", "ERROR")] + [f"- {s['name']}: {s['warning']}" for s in manifest["stages"] if s.get("warning")]
    if warns:
        lines += ["", "## Warnings", *warns]
    (rdir / "run_report.md").write_text("\n".join(lines), encoding="utf-8")
    hc.save()
    print(f"\nOverall: {manifest['overall']}\nManifest: {rdir / 'run_manifest.json'}\nReport:   {rdir / 'run_report.md'}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
