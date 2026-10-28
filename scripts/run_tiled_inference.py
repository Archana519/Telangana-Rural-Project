"""Tiled, georeferenced StrongDINOv2Seg inference on the Damarakunta mosaic.
Read-only on inputs. Writes new GeoTIFFs + a JSON log. Raw predictions only."""
import argparse, json, os, sys, time
import numpy as np
import rasterio
from rasterio.windows import Window
import torch

PROJECT_DIR = r"D:\new_MPS\remoteSensingWebApp\project"
CHECKPOINT = r"D:\new_MPS\remoteSensingWebApp\checkpoints\best_model.pth"
RASTER = (r"D:\Telangana_Rural_Project\Siddipet\Damarakunta\aligned"
          r"\damarakunta_esri_highres_mosaic_0p6m.tif")
OUT_DIR = r"D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\tiled_v1"
TILE = 560

def starts(n, tile, stride):
    s = list(range(0, n - tile + 1, stride))
    if s[-1] != n - tile:
        s.append(n - tile)
    return s

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true",
                    help="small 1400x1400 test window (9 tiles)")
    ap.add_argument("--window", nargs=4, type=int, metavar=("COL", "ROW", "W", "H"))
    ap.add_argument("--stride", type=int, default=420)
    ap.add_argument("--margin", type=int, default=70)
    ap.add_argument("--batch", type=int, default=2)
    ap.add_argument("--overwrite", action="store_true")
    a = ap.parse_args()
    if a.stride > TILE - 2 * a.margin:
        sys.exit("stride must be <= tile - 2*margin or gaps appear")
    sys.path.insert(0, PROJECT_DIR)
    from model import StrongDINOv2Seg

    tag = "full"
    with rasterio.open(RASTER) as src:
        print("CRS:", src.crs, "| res:", src.res, "| size (W,H):", src.width, src.height,
              "| bands:", src.count, "| dtype:", src.dtypes[0])
        if src.count < 3 or src.dtypes[0] != "uint8":
            sys.exit("Expected >=3 bands of uint8; stopping rather than guessing scaling.")
        if a.smoke:
            win = Window(5000, 3000, 1400, 1400); tag = "smoke"
        elif a.window:
            win = Window(*a.window); tag = "window"
        else:
            win = Window(0, 0, src.width, src.height)
        h, w = int(win.height), int(win.width)
        if h < TILE or w < TILE:
            sys.exit("Window smaller than one tile")
        os.makedirs(OUT_DIR, exist_ok=True)
        p_cls = os.path.join(OUT_DIR, f"pred_classes_{tag}.tif")
        p_bp = os.path.join(OUT_DIR, f"building_prob_{tag}.tif")
        p_log = os.path.join(OUT_DIR, f"run_log_{tag}.json")
        if not a.overwrite and any(os.path.exists(p) for p in (p_cls, p_bp, p_log)):
            sys.exit(f"Outputs for tag '{tag}' exist; use --overwrite")

        device = "cuda" if torch.cuda.is_available() else "cpu"
        print("Device:", device)
        model = StrongDINOv2Seg().to(device)
        ck = torch.load(CHECKPOINT, map_location="cpu", weights_only=False)
        res = model.load_state_dict(ck["state_dict"], strict=False)
        print("Missing keys:", res.missing_keys)
        print("Unexpected keys:", res.unexpected_keys)
        if res.missing_keys:
            sys.exit("Missing model keys: checkpoint mismatch")
        model.eval()

        valid = src.read_masks(1, window=win)
        out_cls = np.zeros((h, w), np.uint8)
        out_bp = np.zeros((h, w), np.uint8)
        rows, cols = starts(h, TILE, a.stride), starts(w, TILE, a.stride)
        jobs = [(ri, ci) for ri in range(len(rows)) for ci in range(len(cols))]
        print(f"Tiles: {len(rows)} x {len(cols)} = {len(jobs)}")
        t0, done = time.time(), 0

        def flush(batch):
            x = torch.from_numpy(np.stack([b[2] for b in batch])).float().div(255.0).to(device)
            with torch.no_grad():
                logits = model(x)
                assert logits.shape[1] == 8 and logits.shape[-2:] == (TILE, TILE), logits.shape
                pr = torch.softmax(logits, 1)
                cls = (pr[:, 1:].argmax(1) + 1).cpu().numpy().astype(np.uint8)
                bp = (pr[:, 2] * 255).round().cpu().numpy().astype(np.uint8)
            for k, (ri, ci, _) in enumerate(batch):
                r0, c0 = rows[ri], cols[ci]
                t = a.margin if ri > 0 else 0
                b = TILE - (a.margin if ri < len(rows) - 1 else 0)
                l = a.margin if ci > 0 else 0
                r = TILE - (a.margin if ci < len(cols) - 1 else 0)
                out_cls[r0 + t:r0 + b, c0 + l:c0 + r] = cls[k, t:b, l:r]
                out_bp[r0 + t:r0 + b, c0 + l:c0 + r] = bp[k, t:b, l:r]

        batch = []
        for ri, ci in jobs:
            r0, c0 = rows[ri], cols[ci]
            if not valid[r0:r0 + TILE, c0:c0 + TILE].any():
                continue
            arr = src.read([1, 2, 3], window=Window(win.col_off + c0, win.row_off + r0, TILE, TILE))
            batch.append((ri, ci, arr))
            if len(batch) == a.batch:
                flush(batch); done += len(batch); batch = []
                el = time.time() - t0
                print(f"{done}/{len(jobs)} tiles | {el:.0f}s | ETA {el / done * (len(jobs) - done):.0f}s", flush=True)
        if batch:
            flush(batch); done += len(batch)

        out_cls[valid == 0] = 0
        out_bp[valid == 0] = 0
        prof = dict(driver="GTiff", height=h, width=w, count=1, dtype="uint8",
                    crs=src.crs, transform=src.window_transform(win),
                    compress="lzw", tiled=True)
        with rasterio.open(p_cls, "w", nodata=0, **prof) as d:
            d.write(out_cls, 1)
        with rasterio.open(p_bp, "w", **prof) as d:
            d.write(out_bp, 1)

        u, c = np.unique(out_cls, return_counts=True)
        hist = {int(i): round(100 * int(n) / out_cls.size, 3) for i, n in zip(u, c)}
        log = dict(raster=RASTER, checkpoint=CHECKPOINT, window=[int(win.col_off), int(win.row_off), w, h],
                   tile=TILE, stride=a.stride, margin=a.margin, device=device,
                   tiles_run=done, seconds=round(time.time() - t0, 1),
                   class_percent=hist, note="raw argmax over classes 1-7; unvalidated")
        with open(p_log, "w") as f:
            json.dump(log, f, indent=2)
        print("Class % :", hist)
        print("Wrote:", p_cls, p_bp, p_log, sep="\n  ")

if __name__ == "__main__":
    main()