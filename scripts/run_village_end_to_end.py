#!/usr/bin/env python
"""Any configured village (Adilabad Urban, Aswaraopeta, ...): the full Damarakunta pipeline, end to end, on one machine (Windows PC with internet + the StrongDINOv2Seg checkpoint).

    Esri World Imagery RGB tiles (0.6 m)  ->  mosaic  ->  StrongDINOv2Seg tiled inference  ->  OpenCV instance extraction (extract_buildings_v8)
    ->  Stage A / Stage B routing (the same planner, cost surface and sweeps as the open-data run)  ->  tables + satellite-overlay figures

Run from the repository root (see docs/guides/ADILABAD_END_TO_END_WINDOWS.md for the full walk-through):

    python scripts\\run_village_end_to_end.py --stage check                                 # default village: adilabad_urban; add --village aswaraopeta for the other
    python scripts\\run_village_end_to_end.py --stage all --workers 4          # everything, resumable (finished stages are skipped)
    python scripts\\run_village_end_to_end.py --stage infer --smoke            # 3 x 3 tile smoke test before the long run

Stages (each can be run alone; `all` = open -> esri -> mosaic -> infer -> extract -> route -> report):
    check    versions, GPU, checkpoint (+SHA-256), model code, Esri reachability, study-area files.  Writes nothing.
    open     only if data/villages/<village>/state.pkl is missing: the open-data acquire/prepare/extract steps (boundary, Overture roads/places, WorldCover, DEM).
    esri     download the Esri World Imagery export tiles for the study polygon (same service, 1800 m tiles, 0.6 m/px, EPSG:32644 as export_esri_damarakunta_full.py).
    mosaic   merge the tiles into <work>/aligned/<slug>_esri_highres_mosaic_0p6m.tif
    infer    tiled StrongDINOv2Seg inference (tile 560, stride 420, margin 70 = the Damarakunta run) -> pred_classes_full.tif, building_prob_full.tif, run_log_full.json
    extract  scripts/extract_buildings_v8.py on the predictions -> buildings_v8_<slug>.gpkg (+csv/json)
    route    Stage A / Stage B planner on the segmentation footprints (src.multivillage.run --variant segmentation)
    report   tables (CSV/JSON) and satellite overlay figures in DELIVERABLES_CONTRIBUTION_3_MULTI_VILLAGE/<folder>_SEGMENTATION/

Nothing in DELIVERABLES_DAMARAKUNTA_STAGE_B/ or in the open-data folder 01_ADILABAD/ is modified.
Esri imagery is used for non-commercial academic research under the Esri terms; tiles stay in <work>/ (git-ignored) and are not redistributed.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

DEFAULT_VILLAGE = "adilabad_urban"
CRS_EPSG = 32644
ESRI_EXPORT = "https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/export"
ESRI_TILE_M = 1800.0            # Damarakunta: 1800 m tiles
RES_M = 0.6                     # Damarakunta: 1800 m / 3000 px
TILE = 560                      # model input size (LoveDA training size)
DEFAULT_CKPT = r"D:\new_MPS\remoteSensingWebApp\checkpoints\best_model.pth"
DEFAULT_MODEL_PY = r"D:\new_MPS\remoteSensingWebApp\project\model.py"
CREDIT = "Basemap imagery: Esri, Maxar, Earthstar Geographics, and the GIS User Community."


def say(*a, **k):
    print(*a, flush=True, **k)


def sha256(path: Path, chunk=1 << 22) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(chunk), b""):
            h.update(b)
    return h.hexdigest()


class Paths:
    """All locations of one village's run. `a.village` (default adilabad_urban); the slug, output folder and boundary come from configs/multivillage/villages/<id>.yaml."""

    def __init__(self, a):
        from src.multivillage import acquire as A
        self.village = getattr(a, "village", None) or DEFAULT_VILLAGE
        self.cfg = A.load_cfg(self.village)
        v = self.cfg["village"]
        self.slug = v["work_slug"]
        self.data = REPO / "data" / "villages" / self.village
        wd = getattr(a, "work_dir", None)
        self.work = Path(wd) if wd else REPO / "data" / "villages" / f"{self.slug}_esri"      # git-ignored (data/ is not tracked)
        self.tiles = self.work / "esri_tiles"
        self.mosaic = self.work / "aligned" / f"{self.slug}_esri_highres_mosaic_0p6m.tif"
        self.pred = self.work / "predictions"
        self.v8 = self.work / "results" / "v8_instances"
        self.v8_gpkg = self.v8 / f"buildings_v8_{self.slug}.gpkg"
        self.boundary = self.data / "boundary.gpkg"
        self.out = REPO / "DELIVERABLES_CONTRIBUTION_3_MULTI_VILLAGE" / (v["folder"] + "_SEGMENTATION")


# ================================================================================ check
def stage_check(a, P: Paths):
    say("=" * 78, "\nSTAGE check (writes nothing)\n", "=" * 78)
    say("python", sys.version.split()[0], "|", platform.platform())
    for mod in ("numpy", "rasterio", "geopandas", "shapely", "cv2", "pandas", "matplotlib", "requests", "yaml", "torch", "transformers"):
        try:
            m = __import__(mod)
            say(f"  {mod:13s} OK  {getattr(m, '__version__', '')}")
        except Exception as e:
            say(f"  {mod:13s} MISSING ({e.__class__.__name__}) -> pip install -r requirements.txt  (torch/transformers: see the guide)")
    try:
        import torch
        say("  CUDA available:", torch.cuda.is_available(), "|", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU only (Damarakunta ran on CPU: 459 tiles, ~61 min)")
    except Exception:
        pass
    ck = Path(a.checkpoint)
    say("\ncheckpoint:", ck, "| exists:", ck.is_file(), "|", f"{ck.stat().st_size / 1e6:,.0f} MB" if ck.is_file() else "")
    if ck.is_file() and a.hash:
        say("  sha256:", sha256(ck))
    mp_ = Path(a.model_py)
    say("model code:", mp_, "| exists:", mp_.is_file(), "| fallback (repo copy):", REPO / "src/modeling/strongdinov2seg_model.py")
    say("study polygon:", P.boundary, "| exists:", P.boundary.is_file(), "(created by --stage open)")
    v = P.cfg["village"]
    if v.get("boundary_method") == "polygon_file":
        bf = REPO / v["boundary_file"]
        say("  boundary file (true village / town polygon):", bf, "| exists:", bf.is_file(), "" if bf.is_file() else f"-> python scripts/propose_aoi.py --village {P.village}, review, then --pick N")
    say("open-data state:", P.data / "state.pkl", "| exists:", (P.data / "state.pkl").is_file())
    say("work dir:", P.work, "| tiles:", len(list(P.tiles.glob("*.tif"))) if P.tiles.exists() else 0, "| mosaic:", P.mosaic.is_file(),
        "| predictions:", (P.pred / "pred_classes_full.tif").is_file(), "| v8 footprints:", P.v8_gpkg.is_file())
    try:
        import requests
        r = requests.get(ESRI_EXPORT, params=dict(bbox="238708,2175334,238808,2175434", bboxSR=CRS_EPSG, imageSR=CRS_EPSG, size="64,64", format="png", f="image"), timeout=30,
                         headers={"User-Agent": "Mozilla/5.0"})
        say("Esri export reachable: HTTP", r.status_code, "| bytes", len(r.content), "| content-type", r.headers.get("content-type"))
    except Exception as e:
        say("Esri export NOT reachable:", e)
    say("\nIf anything above says MISSING / NOT reachable / exists: False for the checkpoint, fix it before --stage all.")


# ================================================================================ open-data prerequisites
def stage_open(a, P: Paths):
    if (P.data / "state.pkl").is_file() and not a.force:
        say("open-data state exists -> skipping (use --force to rebuild)"); return
    say("STAGE open: boundary, Overture roads/places, WorldCover, DEM (internet; ~minutes)")
    cmd = [sys.executable, "-m", "src.multivillage.run", "--village", P.village, "--steps", "acquire", "prepare"]
    if a.skip_overture_buildings:
        cmd += ["--skip-buildings"]                       # segmentation run: footprints come from the model, so the slow Overture buildings query is not needed
    elif a.from_cache:
        cmd += ["--from-cache"]
    else:
        cmd += ["extract"]                                # full open-data pipeline (also writes the open-footprint targets)
    subprocess.run(cmd, cwd=REPO, check=True)


# ================================================================================ esri tiles
def study_bounds(P: Paths, pad_m: float):
    import geopandas as gpd
    if not P.boundary.exists():
        sys.exit(f"{P.boundary} not found: run --stage open first (it builds the study polygon from the village config; for polygon_file villages fetch the boundary with scripts/propose_aoi.py first)")
    g = gpd.read_file(P.boundary).to_crs(CRS_EPSG)
    x0, y0, x1, y1 = g.total_bounds
    return x0 - pad_m, y0 - pad_m, x1 + pad_m, y1 + pad_m


def tile_grid(b, tile_m=ESRI_TILE_M):
    import math
    x0, y0, x1, y1 = b
    nx, ny = math.ceil((x1 - x0) / tile_m), math.ceil((y1 - y0) / tile_m)
    out = []
    for r in range(ny):
        for c in range(nx):
            out.append((r * nx + c + 1, x0 + c * tile_m, y0 + r * tile_m, min(x0 + (c + 1) * tile_m, x1), min(y0 + (r + 1) * tile_m, y1)))
    return nx, ny, out


def is_tiff_or_image(r) -> bool:
    """Esri may answer HTTP 200 with content-type application/octet-stream for a TIFF; accept an image/* type or TIFF / PNG / JPEG magic bytes (the export has been seen to return PNG bytes for format=tiff, with no content-type)."""
    ct = r.headers.get("content-type", "").lower()
    head = bytes(r.content[:4])
    return ct.startswith("image") or head in (b"II*\x00", b"MM\x00*", b"II+\x00", b"MM\x00+") or head[:3] == b"\x89PN" or head[:2] == b"\xff\xd8"      # the service may return PNG / JPEG bytes whatever `format` says


def stage_esri(a, P: Paths):
    import numpy as np
    import rasterio
    import requests
    from rasterio.crs import CRS
    from rasterio.transform import from_bounds
    b = study_bounds(P, a.pad_m)
    nx, ny, tiles = tile_grid(b)
    import geopandas as gpd
    from shapely.geometry import box as _box
    poly = gpd.read_file(P.boundary).to_crs(CRS_EPSG).geometry.union_all().buffer(a.pad_m)
    allt = len(tiles)
    tiles = [t for t in tiles if _box(t[1], t[2], t[3], t[4]).intersects(poly)]            # irregular boundaries: skip tiles that do not touch the study area (+ padding)
    say(f"  {len(tiles)} of {allt} grid tiles touch the study polygon (+{a.pad_m:g} m)")
    say(f"STAGE esri: bbox (EPSG:{CRS_EPSG}) {[round(float(v), 1) for v in b]} -> {nx} x {ny} = {len(tiles)} tiles of {ESRI_TILE_M:.0f} m at {RES_M} m/px")
    if a.dry_run:
        for n, x0, y0, x1, y1 in tiles:
            say(f"  tile {n:02d}: {round(x0)} {round(y0)} {round(x1)} {round(y1)} -> {round((x1 - x0) / RES_M)} x {round((y1 - y0) / RES_M)} px")
        return
    P.tiles.mkdir(parents=True, exist_ok=True)
    sess = requests.Session()
    sess.headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/154.0 Safari/537.36"
    for n, x0, y0, x1, y1 in tiles:
        # pixel size is proportional to the tile extent, so edge tiles keep 0.6 m/px (the Damarakunta export forced 3000 x 3000 px on every tile)
        w, h = int(round((x1 - x0) / RES_M)), int(round((y1 - y0) / RES_M))
        dst = P.tiles / f"{P.slug}_esri_tile_{n:02d}.tif"
        if dst.exists():
            try:
                with rasterio.open(dst) as s:
                    if s.count >= 3 and s.crs is not None and s.width == w and s.height == h:
                        say(f"  tile {n:02d} exists and is valid -> skip"); continue
            except Exception:
                pass
        params = dict(bbox=f"{x0},{y0},{x1},{y1}", bboxSR=CRS_EPSG, imageSR=CRS_EPSG, size=f"{w},{h}", format="tiff", transparent="false", f="image")
        for attempt in range(1, 6):
            try:
                r = sess.get(ESRI_EXPORT, params=params, timeout=180)
                say(f"  tile {n:02d}/{len(tiles)} attempt {attempt}: HTTP {r.status_code}, {len(r.content):,} bytes")
                if r.status_code == 200 and is_tiff_or_image(r):
                    break
            except requests.RequestException as e:
                say("  network error:", e)
            time.sleep(10)
        else:
            sys.exit(f"Esri export failed for tile {n}; re-run the stage (finished tiles are kept)")
        raw = P.tiles / f"raw_{dst.name}"
        raw.write_bytes(r.content)
        with rasterio.open(raw) as s:
            data = s.read()
        if data.shape[0] < 3 or data.ndim != 3:
            sys.exit(f"tile {n}: unexpected image {data.shape}")
        data = data[:3]
        if float((data == 0).all(axis=0).mean()) > 0.5 or float((data == 255).all(axis=0).mean()) > 0.5:
            sys.exit(f"tile {n}: more than half of the pixels are blank - the service returned an empty image")
        with rasterio.open(dst, "w", driver="GTiff", height=data.shape[1], width=data.shape[2], count=3, dtype=data.dtype, crs=CRS.from_epsg(CRS_EPSG),
                           transform=from_bounds(x0, y0, x1, y1, data.shape[2], data.shape[1]), compress="lzw") as d:
            d.write(data)
        raw.unlink()
        time.sleep(a.esri_delay)
    say("tiles done:", len(list(P.tiles.glob(f"{P.slug}_esri_tile_*.tif"))), "/", len(tiles))


# ================================================================================ mosaic
def stage_mosaic(a, P: Paths):
    import glob
    import rasterio
    from rasterio.merge import merge
    files = sorted(glob.glob(str(P.tiles / f"{P.slug}_esri_tile_*.tif")))
    if not files:
        sys.exit("no tiles: run --stage esri first")
    if P.mosaic.exists() and not a.force:
        say("mosaic exists -> skip (use --force)"); return
    say(f"STAGE mosaic: {len(files)} tiles -> {P.mosaic}")
    srcs = [rasterio.open(f) for f in files]
    try:
        arr, tr = merge(srcs, res=(RES_M, RES_M), nodata=0)
        prof = dict(driver="GTiff", height=arr.shape[1], width=arr.shape[2], count=arr.shape[0], dtype=arr.dtype, crs=f"EPSG:{CRS_EPSG}", transform=tr, compress="lzw",
                    tiled=True, BIGTIFF="IF_SAFER", nodata=0)
        P.mosaic.parent.mkdir(parents=True, exist_ok=True)
        with rasterio.open(P.mosaic, "w", **prof) as d:
            d.write(arr)
    finally:
        for s in srcs:
            s.close()
    with rasterio.open(P.mosaic) as s:
        say(f"mosaic: {s.width} x {s.height} px, {s.count} bands, {s.dtypes[0]}, res {s.res}, CRS {s.crs}")


# ================================================================================ inference
def starts(n, tile, stride):
    s = list(range(0, n - tile + 1, stride))
    if s[-1] != n - tile:
        s.append(n - tile)
    return s


def load_model(a):
    """StrongDINOv2Seg from the original project file when present (what Damarakunta used), else the verbatim repo copy; strict key check either way."""
    import torch
    cls = None
    mp_ = Path(a.model_py)
    if mp_.is_file():
        sys.path.insert(0, str(mp_.parent))
        spec = importlib.util.spec_from_file_location("sdv2_model_original", mp_)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        cls, origin = m.StrongDINOv2Seg, f"original project file {mp_}"
    else:
        from src.modeling.strongdinov2seg_model import StrongDINOv2Seg as cls            # noqa: N813
        origin = "repo copy src/modeling/strongdinov2seg_model.py"
    say("model class from:", origin)
    model = cls()
    ck = torch.load(a.checkpoint, map_location="cpu", weights_only=False)
    sd = ck["state_dict"] if isinstance(ck, dict) and "state_dict" in ck else ck
    res = model.load_state_dict(sd, strict=False)
    say("missing keys:", res.missing_keys, "| unexpected keys:", res.unexpected_keys)
    if res.missing_keys:
        sys.exit("checkpoint does not match the model architecture (missing keys)")
    info = {k: (float(ck[k]) if k in ("mIoU", "mDice") else ck[k]) for k in ("epoch", "mIoU", "mDice") if isinstance(ck, dict) and k in ck}
    return model, origin, info


def make_predictor(a):
    """-> (predict(batch uint8 N,3,H,W) -> (class uint8 N,H,W, building prob*255 uint8 N,H,W), meta). torch is imported only for the real model."""
    import numpy as np
    if a.dummy_model:
        def dummy(x):
            g = x[:, 1].astype("float32") - 0.5 * (x[:, 0].astype("float32") + x[:, 2].astype("float32"))
            bp = np.clip(128 + g, 0, 255).astype("uint8")
            return np.where(bp > 140, 2, 7).astype("uint8"), bp
        return dummy, dict(model="DUMMY numpy predictor (self-test only, NOT StrongDINOv2Seg)", device="cpu")
    import torch
    device = a.device if a.device != "auto" else ("cuda" if torch.cuda.is_available() else "cpu")
    model, origin, info = load_model(a)
    model.to(device).eval()

    def predict(x):
        with torch.no_grad():
            logits = model(torch.from_numpy(x).float().div(255.0).to(device))
            assert logits.shape[1] == 8 and logits.shape[-2:] == (TILE, TILE), logits.shape
            pr = torch.softmax(logits, 1)
            cls = (pr[:, 1:].argmax(1) + 1).cpu().numpy().astype("uint8")           # classes 1..7 (0 = ignore is never predicted), as in the Damarakunta run
            bp = (pr[:, 2] * 255).round().cpu().numpy().astype("uint8")             # 255 x softmax(Building)
        return cls, bp
    return predict, dict(model=origin, device=device, checkpoint=str(a.checkpoint), checkpoint_info=info,
                         checkpoint_sha256=sha256(Path(a.checkpoint)))


def stage_infer(a, P: Paths):
    import numpy as np
    import rasterio
    from rasterio.windows import Window
    stride, margin = a.stride, a.margin
    if stride > TILE - 2 * margin:
        sys.exit("stride must be <= tile - 2*margin")
    tag = "smoke" if a.smoke else "full"
    p_cls, p_bp, p_log = (P.pred / f"{n}_{tag}.{e}" for n, e in (("pred_classes", "tif"), ("building_prob", "tif"), ("run_log", "json")))
    if p_cls.exists() and not a.force:
        say(f"predictions '{tag}' exist -> skip (use --force)"); return
    P.pred.mkdir(parents=True, exist_ok=True)
    predict, meta = make_predictor(a)
    with rasterio.open(P.mosaic) as src:
        if src.count < 3 or src.dtypes[0] != "uint8":
            sys.exit("mosaic must be >= 3 bands of uint8")
        win = Window(src.width // 2 - 700, src.height // 2 - 700, 1400, 1400) if a.smoke else Window(0, 0, src.width, src.height)
        h, w = int(win.height), int(win.width)
        valid = src.read_masks(1, window=win)
        rows, cols = starts(h, TILE, stride), starts(w, TILE, stride)
        jobs = [(ri, ci) for ri in range(len(rows)) for ci in range(len(cols)) if valid[rows[ri]:rows[ri] + TILE, cols[ci]:cols[ci] + TILE].any()]
        say(f"STAGE infer ({tag}): window {w} x {h} px | tiles {len(rows)} x {len(cols)} = {len(rows) * len(cols)}, with data {len(jobs)} | stride {stride}, margin {margin} | {meta}")
        out_cls, out_bp = np.zeros((h, w), np.uint8), np.zeros((h, w), np.uint8)
        t0, done, batch = time.time(), 0, []

        def flush(batch):
            cls, bp = predict(np.stack([b[2] for b in batch]))
            for k, (ri, ci, _) in enumerate(batch):
                r0, c0 = rows[ri], cols[ci]
                t = margin if ri > 0 else 0
                bt = TILE - (margin if ri < len(rows) - 1 else 0)
                l = margin if ci > 0 else 0
                r = TILE - (margin if ci < len(cols) - 1 else 0)
                out_cls[r0 + t:r0 + bt, c0 + l:c0 + r] = cls[k, t:bt, l:r]
                out_bp[r0 + t:r0 + bt, c0 + l:c0 + r] = bp[k, t:bt, l:r]

        for ri, ci in jobs:
            batch.append((ri, ci, src.read([1, 2, 3], window=Window(win.col_off + cols[ci], win.row_off + rows[ri], TILE, TILE))))
            if len(batch) == a.batch:
                flush(batch); done += len(batch); batch = []
                if done % (a.batch * 10) == 0 or done == len(jobs):
                    el = time.time() - t0
                    say(f"  {done}/{len(jobs)} tiles | {el:.0f}s | ETA {el / done * (len(jobs) - done):.0f}s")
        if batch:
            flush(batch); done += len(batch)
        out_cls[valid == 0] = 0
        out_bp[valid == 0] = 0
        prof = dict(driver="GTiff", height=h, width=w, count=1, dtype="uint8", crs=src.crs, transform=src.window_transform(win), compress="lzw", tiled=True)
        with rasterio.open(p_cls, "w", nodata=0, **prof) as d:
            d.write(out_cls, 1)
        with rasterio.open(p_bp, "w", **prof) as d:
            d.write(out_bp, 1)
        u, c = np.unique(out_cls, return_counts=True)
        log = dict(raster=str(P.mosaic), window=[int(win.col_off), int(win.row_off), w, h], tile=TILE, stride=stride, margin=margin, tiles_run=done,
                   seconds=round(time.time() - t0, 1), class_percent={int(i): round(100 * int(n) / out_cls.size, 3) for i, n in zip(u, c)}, **meta,
                   note="raw argmax over classes 1-7; unvalidated")
        p_log.write_text(json.dumps(log, indent=2, default=str), encoding="utf-8")
        say("class %:", log["class_percent"], "\nwrote", p_cls, p_bp, p_log, sep="\n  ")


# ================================================================================ extraction
def stage_extract(a, P: Paths):
    tag = "full"
    if a.smoke:
        say("--smoke covers a sub-window of the mosaic; extraction needs the full-window predictions -> nothing to do"); return
    if P.v8_gpkg.exists() and not a.force:
        say("v8 footprints exist -> skip (use --force)"); return
    say("STAGE extract: scripts/extract_buildings_v8.py (distance-transform h-maxima + marker-controlled flooding + neck test 0.65)")
    cmd = [sys.executable, str(REPO / "scripts" / "extract_buildings_v8.py"), "--tag", tag, "--pred-dir", str(P.pred), "--raster", str(P.mosaic), "--boundary", str(P.boundary),
           "--out-dir", str(P.v8), "--out-name", P.v8_gpkg.stem, "--no-overlays"] + (["--overwrite"] if a.force else [])
    subprocess.run(cmd, cwd=REPO, check=True)


# ================================================================================ routing + report
def stage_route(a, P: Paths, steps):
    if not P.v8_gpkg.exists():
        sys.exit("no segmentation footprints: run --stage extract first")
    cmd = [sys.executable, "-m", "src.multivillage.run", "--village", P.village, "--variant", "segmentation", "--footprints", str(P.v8_gpkg), "--steps", *steps,
           "--workers", str(a.workers), "--mosaic", str(P.mosaic)] + (["--quick"] if a.quick else []) \
        + (["--limit-targets", str(a.debug_limit_targets)] if a.debug_limit_targets else [])
    say("STAGE", "+".join(steps), ":", " ".join(cmd))
    subprocess.run(cmd, cwd=REPO, check=True)


def main(default_village=DEFAULT_VILLAGE):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--village", default=default_village, choices=sorted(p.stem for p in (REPO / "configs/multivillage/villages").glob("*.yaml")), help="village config id")
    ap.add_argument("--stage", default="check", choices=["check", "open", "esri", "mosaic", "infer", "extract", "route", "report", "all"])
    ap.add_argument("--work-dir", default=None, help="imagery / predictions / v8 outputs (default data/villages/<slug>_esri, git-ignored)")
    ap.add_argument("--checkpoint", default=DEFAULT_CKPT)
    ap.add_argument("--model-py", default=DEFAULT_MODEL_PY, help="original project model.py; if missing the repo copy of the architecture is used")
    ap.add_argument("--device", default="auto", choices=["auto", "cpu", "cuda"])
    ap.add_argument("--batch", type=int, default=2)
    ap.add_argument("--stride", type=int, default=420)
    ap.add_argument("--margin", type=int, default=70)
    ap.add_argument("--workers", type=int, default=4, help="parallel planner jobs (route stage)")
    ap.add_argument("--pad-m", type=float, default=60.0, help="metres of imagery around the study polygon")
    ap.add_argument("--esri-delay", type=float, default=1.0)
    ap.add_argument("--smoke", action="store_true", help="infer/extract on a 1400 x 1400 px window in the middle of the mosaic (tag 'smoke'); a quick check, not a result")
    ap.add_argument("--quick", action="store_true", help="route: main strategy comparison only (no sweeps)")
    ap.add_argument("--debug-limit-targets", type=int, default=None, help="DEBUG ONLY (code-path tests): keep the first N road-gap targets; never use for results")
    ap.add_argument("--dummy-model", action="store_true", help="SELF-TEST ONLY: numpy stand-in for the network (no checkpoint, no torch)")
    ap.add_argument("--dry-run", action="store_true", help="esri: print the tile plan only")
    ap.add_argument("--hash", action="store_true", help="check: also compute the checkpoint SHA-256")
    ap.add_argument("--skip-overture-buildings", action="store_true", help="open: reuse boundary.gpkg and any cached roads/places gpkg, never download the Overture buildings (not needed for the segmentation run)")
    ap.add_argument("--from-cache", action="store_true", help="open: reuse every cached data/villages/<village>/*.gpkg, query only missing layers")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    P = Paths(a)
    order = ["open", "esri", "mosaic", "infer", "extract", "route", "report"]
    todo = order if a.stage == "all" else [a.stage]
    t0 = time.time()
    for st in todo:
        say(f"\n######## {st} ########")
        if st == "check":
            stage_check(a, P)
        elif st == "open":
            stage_open(a, P)
        elif st == "esri":
            stage_esri(a, P)
        elif st == "mosaic":
            stage_mosaic(a, P)
        elif st == "infer":
            stage_infer(a, P)
        elif st == "extract":
            stage_extract(a, P)
        elif st == "route":
            stage_route(a, P, ["prepare", "extract", "route"])
        elif st == "report":
            stage_route(a, P, ["prepare", "report"])
    say(f"\nfinished {todo} in {time.time() - t0:.0f} s")
    if a.stage in ("all", "report"):
        say("Results:", P.out, "\n  metrics_summary.json, routing_strategy_comparison.csv, penalty_sensitivity.csv, omission_summary.csv, target_definition_sensitivity.csv,",
            "\n  comparison_open_vs_segmentation.csv, figures/sat_map1_*.png, figures/sat_map2_*.png (credit:", CREDIT, ")")


if __name__ == "__main__":
    main()
