#!/usr/bin/env python
"""READ-ONLY inspection of model weights, building outputs and imagery for a village.
Writes only one new file: <village>/results/_inspection_report.md  (use --no-write to skip).
Run from the project root:
    .venv\\Scripts\\python.exe scripts\\inspect_building_pipeline.py --village Siddipet\\Damarakunta
"""
import argparse, os, re, sys, json, hashlib, datetime, warnings
warnings.filterwarnings("ignore")
SKIP = {".venv", "__pycache__", ".git", "node_modules", "presentation_maps"}
OUT = []
def p(m=""):
    print(m); OUT.append(str(m))
def walk(root):
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in SKIP]
        for f in fn: yield os.path.join(dp, f)
def mb(x): return f"{x/1e6:.1f} MB"
def sha(path, n=1 << 22):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(n), b""): h.update(b)
    return h.hexdigest()

def weights(files, dohash):
    p("\n## 1. Model weights / checkpoints")
    ws = [f for f in files if f.lower().endswith((".pt", ".pth", ".ckpt", ".safetensors", ".bin")) and os.path.getsize(f) > 1e6]
    if not ws: p("NONE FOUND (.pt/.pth/.ckpt/.safetensors > 1 MB)"); return
    try:
        import torch
    except Exception:
        torch = None; p("(torch not importable here: key inspection skipped)")
    for f in sorted(ws):
        p(f"- {f} | {mb(os.path.getsize(f))} | modified {datetime.datetime.fromtimestamp(os.path.getmtime(f)):%Y-%m-%d %H:%M}" + (f" | sha256 {sha(f)}" if dohash else ""))
        if torch and f.lower().endswith((".pt", ".pth", ".ckpt")):
            try:
                ck = torch.load(f, map_location="cpu", weights_only=False)
                if isinstance(ck, dict):
                    meta = {k: (v if isinstance(v, (int, float, str)) else type(v).__name__) for k, v in ck.items() if not hasattr(v, "keys") or k not in ("model", "state_dict", "model_state_dict")}
                    p(f"    top-level keys: {list(ck.keys())[:15]}")
                    p(f"    scalar/meta: {json.dumps({k: v for k, v in meta.items() if isinstance(v, (int, float, str))}, default=str)[:600]}")
                    sd = next((ck[k] for k in ("model_state_dict", "state_dict", "model") if k in ck and hasattr(ck[k], "items")), ck)
                    heads = [(k, tuple(v.shape)) for k, v in sd.items() if hasattr(v, "shape") and v.ndim in (1, 4) and any(t in k.lower() for t in ("classifier", "cls", "head", "final", "out"))]
                    p(f"    candidate output-head tensors (name, shape): {heads[-4:]}")
                    for k in ("classes", "class_names", "num_classes", "class_map", "label_map"):
                        if k in ck: p(f"    {k}: {ck[k]}")
            except Exception as e:
                p(f"    could not load: {type(e).__name__}: {str(e)[:120]}")

def vectors(files):
    p("\n## 2. Building / candidate vector outputs")
    import geopandas as gpd, fiona
    pat = re.compile(r"build|roof|candidate|extract|polygon|footprint|v[5-9]_", re.I)
    for f in sorted(x for x in files if x.lower().endswith((".gpkg", ".shp", ".geojson")) and pat.search(os.path.basename(x) + os.path.dirname(x))):
        try:
            layers = fiona.listlayers(f) if f.lower().endswith(".gpkg") else [None]
        except Exception as e:
            p(f"- {f}: unreadable ({e})"); continue
        for l in layers:
            try:
                g = gpd.read_file(f, layer=l) if l else gpd.read_file(f)
            except Exception as e:
                p(f"- {f} [{l}]: unreadable"); continue
            if len(g) == 0: continue
            gt = sorted(g.geom_type.dropna().unique().tolist())
            line = f"- {f} [{l}] | n={len(g)} | geom={gt} | crs={g.crs.to_string() if g.crs else None}"
            if any("Polygon" in t for t in gt):
                a = g.to_crs(32644).area if g.crs else g.area
                line += f" | area m2 min/median/max={a.min():.1f}/{a.median():.1f}/{a.max():.1f} | invalid={int((~g.is_valid).sum())}"
            elif "Point" in gt: line += " | POINTS ONLY (not footprints)"
            p(line); p(f"    columns: {list(g.columns)[:14]}")

def rasters(files):
    p("\n## 3. Rasters: imagery and prediction masks")
    import rasterio, numpy as np
    for f in sorted(x for x in files if x.lower().endswith((".tif", ".tiff", ".vrt"))):
        try:
            with rasterio.open(f) as r:
                if r.crs is None: continue
                tags = {k: v for k, v in r.tags().items() if re.search(r"date|time|acq|source|sensor|copyright|licen|attrib", k, re.I)}
                kind = "IMAGERY" if r.count >= 3 else "single-band"
                line = f"- {kind} {f} | {r.width}x{r.height} | bands={r.count} {r.dtypes[0]} | res={abs(r.transform.a):.3f} | crs={r.crs.to_string()} | bounds={tuple(round(b,1) for b in r.bounds)} | {mb(os.path.getsize(f))}"
                if tags: line += f" | tags={tags}"
                if r.count == 1 and re.search(r"pred|mask|build|seg|class", os.path.basename(f), re.I):
                    s = r.read(1, out_shape=(min(r.height, 1500), min(r.width, 1500)))
                    u, c = np.unique(s, return_counts=True); line += f" | values={dict(zip(u.tolist()[:12], c.tolist()[:12]))}"
                p(line)
        except Exception:
            continue

def docs(files):
    p("\n## 4. Licence / provenance / metadata documents near imagery")
    for f in sorted(files):
        b = os.path.basename(f).lower()
        if re.search(r"licen|readme|attrib|metadata|provenance|terms|source", b) and b.endswith((".txt", ".md", ".json", ".xml", ".pdf", ".csv")) and "imagery" in f.lower() + os.path.dirname(f).lower():
            p(f"- {f} ({mb(os.path.getsize(f))})")
    p("(If nothing is listed above, no licence/terms file for the imagery exists in the project.)")

def scripts(root):
    p("\n## 5. Scripts that look related to inference / building extraction")
    d = os.path.join(root, "scripts")
    if not os.path.isdir(d): p("scripts folder not found"); return
    for f in sorted(os.listdir(d)):
        if not f.endswith(".py"): continue
        txt = open(os.path.join(d, f), encoding="utf-8", errors="ignore").read()
        if re.search(r"building", txt, re.I) and re.search(r"infer|predict|polygon|extract|checkpoint|load_state", txt, re.I):
            hits = [l.strip()[:150] for l in txt.splitlines() if re.search(r"building.*(class|idx|index|==|=\s*\d)|class.*building|BUILDING|\.pth|\.pt\b|checkpoint", l, re.I)][:8]
            p(f"- scripts\\{f} ({os.path.getsize(os.path.join(d,f))} bytes)")
            for h in hits: p(f"    {h}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--village", default=os.path.join("Siddipet", "Damarakunta"))
    ap.add_argument("--root", default=os.getcwd())
    ap.add_argument("--hash", action="store_true", help="also SHA-256 each weights file (slow for large files)")
    ap.add_argument("--no-write", action="store_true")
    a = ap.parse_args()
    root = os.path.abspath(a.root)
    files = list(walk(root))
    p(f"# Inspection report | root={root} | village={a.village} | {datetime.datetime.now():%Y-%m-%d %H:%M}")
    p(f"Files scanned: {len(files)}")
    weights(files, a.hash); vectors(files); rasters(files); docs(files); scripts(root)
    if not a.no_write:
        out = os.path.join(root, a.village, "results", "_inspection_report.md")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        open(out, "w", encoding="utf-8").write("\n".join(OUT)); print("\nWrote", out)
if __name__ == "__main__":
    main()
