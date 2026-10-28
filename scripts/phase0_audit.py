"""
phase0_audit.py - READ-ONLY project + environment audit (Phase 0).

It never modifies your project. It only reads files, imports libraries,
loads the checkpoint on CPU, and (optionally) builds the model once to test
checkpoint compatibility.

Writes:
  <project>/docs/PROJECT_AUDIT.md          human-readable evidence report
  <project>/docs/PROJECT_STATUS.json       machine-readable status + evidence
  <project>/docs/audit_bundle_<stamp>.zip  your .py/.md/.txt/.json/.yaml code files
                                           (no images, no checkpoint) for review
  <project>/logs/<stamp>/system_info.txt

Run (PowerShell / CMD, from Telangana_Rural_Project):
  python scripts\\phase0_audit.py
Options:
  --no-model-load   skip building StrongDINOv2Seg (skips the HuggingFace download)
"""
from __future__ import annotations

import argparse
import ast
import datetime as dt
import importlib
import importlib.metadata as md
import importlib.util
import inspect
import json
import os
import platform
import py_compile
import re
import shutil
import subprocess
import sys
import time
import traceback
import zipfile
from collections import Counter
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]

# ---- paths you gave; change here if they move --------------------------------
SEG_ROOT = Path(r"D:\new_MPS\remoteSensingWebApp")
SEG_FILES = [SEG_ROOT / "project" / n for n in
             ("app.py", "model.py", "start to end code_2.py", "utils.py")]
CHECKPOINT = SEG_ROOT / "checkpoints" / "best_model.pth"
LOVEDA_DIR = SEG_ROOT / "LoveDA Satellite Images Semantic Segmentation"
OLD_MODULES_DIR = SEG_ROOT / "next step of execution"
GIS_DIR = Path(r"C:\Users\DELL\Downloads\new_modules_layers3-6\major_project_new_modules")
CODE_DIRS = [SEG_ROOT / "project", OLD_MODULES_DIR, GIS_DIR]

KEY_PACKAGES = ["torch", "torchvision", "transformers", "timm", "numpy", "opencv-python",
                "Pillow", "scikit-image", "scipy", "rasterio", "geopandas", "shapely",
                "pyproj", "pyogrio", "fiona", "networkx", "osmnx", "matplotlib",
                "pandas", "requests", "flask", "streamlit", "albumentations",
                "segmentation-models-pytorch", "tensorboard", "psutil"]
HOSTS = {"TGRAC": "https://tgrac.telangana.gov.in/arcgis/rest/services",
         "HuggingFace": "https://huggingface.co/facebook/dinov2-base",
         "ESA WorldCover": "https://esa-worldcover.org/en/data-access",
         "Geofabrik": "https://download.geofabrik.de/asia/india.html",
         "USGS EarthExplorer": "https://earthexplorer.usgs.gov/",
         "PMGSY GeoSadak": "https://geosadak-pmgsy.nic.in/OpenData",
         "Copernicus": "https://dataspace.copernicus.eu/"}

# Patterns that need a human look (evidence, not verdicts)
SCAN_PATTERNS = {
    "fixed_0.55_m_per_px": r"\b0\.55\b",
    "gsd_or_pixel_scale": r"(?i)\bgsd\b|m_per_pixel|meters?_per_pixel|pixel_size|px_to_m",
    "size_based_facility_guess": r"(?i)(hospital|school|government|p1_candidate)",
    "largest_area_logic": r"(?i)(largest|argmax|sort.*area|max\(.*area)",
    "hardcoded_windows_path": r"[A-Za-z]:\\\\|[A-Za-z]:/",
    "class_ids_or_names": r"(?i)(num_classes|class_names|classes\s*=|building|road)\s*[:=]",
    "image_size": r"(?i)image_size|img_size|resize\(",
    "normalization": r"(?i)(mean|std)\s*=\s*[\[\(]",
    "random_split": r"(?i)random_split|train_test_split|shuffle\s*=\s*True",
    "crs_usage": r"(?i)\bcrs\b|epsg|to_crs|rasterio|transform",
    "euclidean_distance": r"(?i)euclid|np\.hypot|distance_transform|cdist",
    "graph_routing": r"(?i)networkx|astar|dijkstra|shortest_path",
}


def now_stamp():
    return dt.datetime.now().strftime("%Y%m%d_%H%M%S")


def run(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=30).stdout.strip()
    except Exception as exc:  # noqa: BLE001
        return f"unavailable ({exc.__class__.__name__})"


def ram_gb():
    try:
        import psutil
        vm = psutil.virtual_memory()
        return round(vm.total / 1e9, 1), round(vm.available / 1e9, 1)
    except ImportError:
        pass
    if os.name == "nt":
        import ctypes

        class MEM(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
        m = MEM()
        m.dwLength = ctypes.sizeof(MEM)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
        return round(m.ullTotalPhys / 1e9, 1), round(m.ullAvailPhys / 1e9, 1)
    return None, None


def system_info():
    total, avail = ram_gb()
    info = {"python": sys.version.split()[0], "python_exe": sys.executable,
            "os": platform.platform(), "cpu": platform.processor() or run(["wmic", "cpu", "get", "name"]),
            "cpu_logical_cores": os.cpu_count(), "ram_total_gb": total, "ram_available_gb": avail,
            "disks": {}}
    for drive in ("C:\\", "D:\\") if os.name == "nt" else ("/",):
        if os.path.exists(drive):
            du = shutil.disk_usage(drive)
            info["disks"][drive] = {"total_gb": round(du.total / 1e9, 1),
                                    "free_gb": round(du.free / 1e9, 1)}
    try:
        import torch
        info["torch"] = torch.__version__
        info["torch_cuda_build"] = torch.version.cuda
        info["cuda_available"] = torch.cuda.is_available()
        if torch.cuda.is_available():
            p = torch.cuda.get_device_properties(0)
            info["gpu_name"] = p.name
            info["gpu_memory_gb"] = round(p.total_memory / 1e9, 1)
            info["gpu_count"] = torch.cuda.device_count()
            info["bf16_supported"] = torch.cuda.is_bf16_supported()
    except ImportError:
        info["torch"] = "NOT INSTALLED"
    info["nvidia_smi"] = run(["nvidia-smi", "--query-gpu=name,memory.total,driver_version",
                              "--format=csv,noheader"])
    pk = {}
    for name in KEY_PACKAGES:
        try:
            pk[name] = md.version(name)
        except md.PackageNotFoundError:
            pk[name] = None
    info["packages"] = pk
    info["all_packages_count"] = len(list(md.distributions()))
    return info


def internet():
    out = {}
    try:
        import requests
    except ImportError:
        return {"error": "requests not installed"}
    for name, url in HOSTS.items():
        t0 = time.time()
        try:
            r = requests.get(url, timeout=15, headers={"User-Agent": "phase0-audit"}, stream=True)
            out[name] = {"status": r.status_code, "seconds": round(time.time() - t0, 1)}
            r.close()
        except Exception as exc:  # noqa: BLE001
            out[name] = {"status": f"FAILED {exc.__class__.__name__}"}
    return out


def tree(root: Path, depth=3, max_entries=400):
    lines, count = [], 0
    if not root.exists():
        return [f"MISSING: {root}"]
    skip = {".git", "__pycache__", ".venv", "venv", "node_modules"}
    for dirpath, dirnames, filenames in os.walk(root):
        rel = Path(dirpath).relative_to(root)
        if len(rel.parts) > depth:
            dirnames[:] = []
            continue
        dirnames[:] = [d for d in dirnames if d not in skip]
        ext = Counter(Path(f).suffix.lower() for f in filenames)
        size = sum((Path(dirpath) / f).stat().st_size for f in filenames) / 1e6
        lines.append(f"{'  ' * len(rel.parts)}{rel if rel.parts else root}/  "
                     f"[{len(filenames)} files, {size:.1f} MB] {dict(ext.most_common(6))}")
        count += 1
        if count >= max_entries:
            lines.append("... truncated")
            break
    return lines


def dataset_summary(root: Path):
    if not root.exists():
        return {"exists": False}
    splits = {}
    for dirpath, _, filenames in os.walk(root):
        imgs = [f for f in filenames if f.lower().endswith((".png", ".tif", ".tiff", ".jpg"))]
        if imgs:
            rel = str(Path(dirpath).relative_to(root))
            splits[rel] = len(imgs)
    sample = None
    try:
        from PIL import Image
        for dirpath, _, filenames in os.walk(root):
            for f in filenames:
                if f.lower().endswith((".png", ".tif", ".tiff", ".jpg")):
                    with Image.open(Path(dirpath) / f) as im:
                        sample = {"file": str(Path(dirpath) / f), "size": im.size, "mode": im.mode}
                    break
            if sample:
                break
    except Exception as exc:  # noqa: BLE001
        sample = {"error": str(exc)}
    return {"exists": True, "image_counts_by_folder": splits, "sample": sample}


def checkpoint_summary(path: Path):
    if not path.exists():
        return {"exists": False}
    info = {"exists": True, "size_mb": round(path.stat().st_size / 1e6, 1)}
    try:
        import torch
        ck = torch.load(path, map_location="cpu", weights_only=False)  # your own file
        info["top_level_keys"] = list(ck.keys()) if isinstance(ck, dict) else str(type(ck))
        for k in ("epoch", "mIoU", "mDice", "miou", "mdice", "best_miou"):
            if isinstance(ck, dict) and k in ck:
                v = ck[k]
                info[k] = float(v) if hasattr(v, "__float__") else str(v)
        sd = ck.get("state_dict", ck.get("model_state_dict", ck)) if isinstance(ck, dict) else {}
        tensors = {k: tuple(v.shape) for k, v in sd.items() if hasattr(v, "shape")}
        info["state_dict_tensors"] = len(tensors)
        info["parameters_millions"] = round(sum(
            int(__import__("math").prod(s)) for s in tensors.values()) / 1e6, 2)
        info["key_prefixes"] = dict(Counter(k.split(".")[0] for k in tensors).most_common(12))
        info["has_module_prefix"] = any(k.startswith("module.") for k in tensors)
        info["candidate_head_layers"] = {k: s for k, s in tensors.items()
                                         if len(s) >= 1 and s[0] == 8 and k.endswith("weight")}
        info["first_keys"] = list(tensors)[:8]
        info["last_keys"] = list(tensors)[-8:]
        info["_state_dict"] = sd
    except Exception as exc:  # noqa: BLE001
        info["load_error"] = f"{exc.__class__.__name__}: {exc}"
    return info


def try_build_model(model_py: Path, state_dict):
    """Import model.py, build StrongDINOv2Seg, and test strict state_dict loading."""
    res = {}
    try:
        sys.path.insert(0, str(model_py.parent))
        spec = importlib.util.spec_from_file_location("audit_model", model_py)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        cls = getattr(mod, "StrongDINOv2Seg", None)
        if cls is None:
            return {"error": "class StrongDINOv2Seg not found in model.py",
                    "classes_found": [n for n, o in vars(mod).items() if inspect.isclass(o)]}
        sig = inspect.signature(cls.__init__)
        res["constructor_signature"] = str(sig)
        kwargs = {"num_classes": 8} if "num_classes" in sig.parameters else {}
        model = cls(**kwargs)
        cleaned = {k.replace("module.", "", 1): v for k, v in state_dict.items()}
        missing, unexpected = model.load_state_dict(cleaned, strict=False)
        res["missing_keys"] = list(missing)[:20]
        res["unexpected_keys"] = list(unexpected)[:20]
        res["n_missing"], res["n_unexpected"] = len(missing), len(unexpected)
        res["strict_compatible"] = not missing and not unexpected
        import torch
        model.eval()
        size = getattr(mod, "IMAGE_SIZE", 560)
        with torch.no_grad():
            out = model(torch.zeros(1, 3, size, size))
        out = out[0] if isinstance(out, (tuple, list)) else out
        out = out.get("out", out) if isinstance(out, dict) else out
        res["dummy_input"] = [1, 3, size, size]
        res["dummy_output_shape"] = list(out.shape)
        res["output_finite"] = bool(torch.isfinite(out).all())
    except Exception as exc:  # noqa: BLE001
        res["error"] = f"{exc.__class__.__name__}: {exc}"
        res["traceback_tail"] = traceback.format_exc().splitlines()[-6:]
    return res


def scan_code(files):
    report = []
    for f in files:
        entry = {"file": str(f), "exists": f.exists()}
        if not f.exists():
            report.append(entry)
            continue
        text = f.read_text(encoding="utf-8", errors="replace")
        entry["lines"] = text.count("\n") + 1
        try:
            py_compile.compile(str(f), doraise=True)
            entry["compiles"] = True
        except py_compile.PyCompileError as exc:
            entry["compiles"] = False
            entry["compile_error"] = str(exc)[:300]
        try:
            tree_ = ast.parse(text)
            entry["functions"] = [n.name for n in ast.walk(tree_) if isinstance(n, ast.FunctionDef)]
            entry["classes"] = [n.name for n in ast.walk(tree_) if isinstance(n, ast.ClassDef)]
            entry["imports"] = sorted({(n.module if isinstance(n, ast.ImportFrom) else a.name).split(".")[0]
                                       for n in ast.walk(tree_) if isinstance(n, (ast.Import, ast.ImportFrom))
                                       for a in (n.names if isinstance(n, ast.Import) else [n])
                                       if (n.module if isinstance(n, ast.ImportFrom) else a.name)})
        except SyntaxError as exc:
            entry["parse_error"] = str(exc)
        hits = {}
        for i, line in enumerate(text.splitlines(), 1):
            for tag, pat in SCAN_PATTERNS.items():
                if re.search(pat, line):
                    hits.setdefault(tag, []).append(f"L{i}: {line.strip()[:140]}")
        entry["flags"] = {k: v[:15] for k, v in hits.items()}
        report.append(entry)
    return report


def collect_code_files():
    files = list(SEG_FILES)
    for d in (OLD_MODULES_DIR, GIS_DIR):
        if d.exists():
            files += sorted(p for p in d.rglob("*.py") if "__pycache__" not in p.parts)
    seen, out = set(), []
    for f in files:
        if f not in seen:
            seen.add(f)
            out.append(f)
    return out


def bundle(dest: Path):
    allowed = {".py", ".md", ".txt", ".json", ".yaml", ".yml", ".cfg", ".ini", ".csv"}
    added = 0
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
        for root in CODE_DIRS:
            if not root.exists():
                continue
            for p in root.rglob("*"):
                if (p.is_file() and p.suffix.lower() in allowed and p.stat().st_size < 2_000_000
                        and "LoveDA" not in str(p) and "__pycache__" not in p.parts):
                    z.write(p, arcname=f"{root.name}/{p.relative_to(root)}")
                    added += 1
    return added


def status_block(checkpoint, build, scan, data):
    """Only facts that the evidence can decide; everything else NEEDS VALIDATION."""
    def flagged(name, tag):
        return any(name.lower() in e["file"].lower() and tag in e.get("flags", {}) for e in scan)
    ck_ok = checkpoint.get("exists") and "load_error" not in checkpoint
    return {
        "environment": "IMPLEMENTED",
        "checkpoint_file": "IMPLEMENTED" if ck_ok else ("MISSING" if not checkpoint.get("exists") else "INCORRECT"),
        "checkpoint_model_compatibility": ("IMPLEMENTED" if build.get("strict_compatible")
                                           else "NEEDS VALIDATION"),
        "loveda_dataset": "IMPLEMENTED" if data.get("exists") else "MISSING",
        "segmentation_performance_on_siddipet": "MISSING (not evaluated)",
        "georeferencing_03": ("INCORRECT for Siddipet (fixed scale found)" if flagged("georeference", "fixed_0.55_m_per_px")
                              else "NEEDS VALIDATION"),
        "facility_tagging_04": ("INCORRECT for Siddipet (name/size heuristic found)"
                                if flagged("facility_tagging", "size_based_facility_guess") else "NEEDS VALIDATION"),
        "accessibility_05": "NEEDS VALIDATION",
        "routing_06": "NEEDS VALIDATION",
        "evaluation_07": "NEEDS VALIDATION",
        "module1_extraction": "NEEDS VALIDATION",
        "module2_connectivity": "NEEDS VALIDATION",
        "module3_final_output": "NEEDS VALIDATION",
        "siddipet_imagery": "MISSING",
        "siddipet_boundary": "MISSING (run scripts/verify_siddipet_village.py)",
        "siddipet_labels": "MISSING",
        "cost_surface": "MISSING",
        "baselines_equal_budget": "MISSING",
        "ablation_sensitivity": "MISSING",
        "multi_village": "MISSING",
    }


def write_md(path, sysinfo, net, trees, data, ck, build, scan, status, stamp):
    L = [f"# PROJECT_AUDIT — Phase 0 (generated {stamp})",
         "", "Generated by `scripts/phase0_audit.py`. Evidence only; classifications marked "
         "NEEDS VALIDATION are completed after code review.", "",
         "## A–J Environment", "```", json.dumps({k: v for k, v in sysinfo.items() if k != "packages"},
                                                  indent=2), "```",
         "### Key packages", "| package | version |", "|---|---|"]
    L += [f"| {k} | {v or 'NOT INSTALLED'} |" for k, v in sysinfo["packages"].items()]
    L += ["", "### Internet reachability", "| host | result |", "|---|---|"]
    L += [f"| {k} | {v} |" for k, v in net.items()]
    L += ["", "## Project structure"]
    for root, lines in trees.items():
        L += [f"### {root}", "```", *lines, "```"]
    L += ["", "## K–L Model and checkpoint", "```",
          json.dumps({k: v for k, v in ck.items() if k != "_state_dict"}, indent=2, default=str), "```",
          "### Model build + strict load test", "```", json.dumps(build, indent=2, default=str), "```",
          "", "## M Dataset (LoveDA — source domain only)", "```",
          json.dumps(data, indent=2, default=str), "```", "", "## N–Q Code scan (flags need human review)"]
    for e in scan:
        L += [f"### {e['file']}", f"- exists: {e['exists']}, compiles: {e.get('compiles')}, "
              f"lines: {e.get('lines')}", f"- functions: {', '.join(e.get('functions', [])[:40])}"]
        for tag, hits in e.get("flags", {}).items():
            L.append(f"- **{tag}**")
            L += [f"  - `{h}`" for h in hits]
    L += ["", "## Component status (evidence-based draft)", "| component | status |", "|---|---|"]
    L += [f"| {k} | {v} |" for k, v in status.items()]
    L += ["", "## T Recommended execution sequence",
          "1. Upload PROJECT_STATUS.json + audit_bundle zip for code review.",
          "2. Run scripts/verify_siddipet_village.py and scripts/inspect_tgrac_angadi_kistapur.py.",
          "3. Obtain legally usable imagery; then scripts/inspect_geotiff.py and the model smoke test."]
    path.write_text("\n".join(L), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-model-load", action="store_true")
    args = ap.parse_args()
    stamp = now_stamp()
    docs, logs = PROJECT / "docs", PROJECT / "logs" / stamp
    docs.mkdir(parents=True, exist_ok=True)
    logs.mkdir(parents=True, exist_ok=True)

    print("[1/7] system + packages");   sysinfo = system_info()
    print("[2/7] internet");            net = internet()
    print("[3/7] folder trees")
    trees = {str(p): tree(p) for p in (SEG_ROOT, GIS_DIR, PROJECT)}
    print("[4/7] LoveDA summary");      data = dataset_summary(LOVEDA_DIR)
    print("[5/7] checkpoint");          ck = checkpoint_summary(CHECKPOINT)
    build = {"skipped": True}
    if not args.no_model_load and "_state_dict" in ck:
        print("[6/7] building model + strict load test (may download facebook/dinov2-base once)")
        build = try_build_model(SEG_ROOT / "project" / "model.py", ck["_state_dict"])
    print("[7/7] code scan + bundle")
    scan = scan_code(collect_code_files())
    n_bundled = bundle(docs / f"audit_bundle_{stamp}.zip")
    status = status_block(ck, build, scan, data)

    ck_public = {k: v for k, v in ck.items() if k != "_state_dict"}
    result = {"generated": stamp, "system": sysinfo, "internet": net, "loveda": data,
              "checkpoint": ck_public, "model_build": build, "code_scan": scan,
              "component_status": status, "bundled_files": n_bundled}
    (docs / "PROJECT_STATUS.json").write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    write_md(docs / "PROJECT_AUDIT.md", sysinfo, net, trees, data, ck, build, scan, status, stamp)
    (logs / "system_info.txt").write_text(json.dumps(sysinfo, indent=2), encoding="utf-8")

    print("\nSummary")
    print(f"  Python {sysinfo['python']} | torch {sysinfo.get('torch')} | "
          f"CUDA available: {sysinfo.get('cuda_available')} | GPU: {sysinfo.get('gpu_name', '-')}")
    print(f"  checkpoint: {'OK' if 'load_error' not in ck else ck['load_error']} | "
          f"epoch={ck.get('epoch')} mIoU={ck.get('mIoU')}")
    if not build.get("skipped"):
        print(f"  model strict-compatible: {build.get('strict_compatible')} "
              f"| output {build.get('dummy_output_shape')} | error: {build.get('error', '-')}")
    print(f"  code files scanned: {len(scan)} | bundled: {n_bundled}")
    print(f"  wrote: {docs / 'PROJECT_AUDIT.md'}")
    print(f"         {docs / 'PROJECT_STATUS.json'}")
    print(f"         {docs / f'audit_bundle_{stamp}.zip'}")


if __name__ == "__main__":
    main()
