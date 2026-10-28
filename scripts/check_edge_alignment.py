"""READ-ONLY roads-on-mosaic alignment check for Damarakunta (proposed; not run by Claude).

Reads: the mosaic GeoTIFF, the TGRAC road layer, optionally the raw tile GeoTIFFs. Never modifies them.
Writes ONLY into a NEW folder (refuses to reuse an existing one):
  <out-root>/<tag>/edge_alignment_report.txt, block_offsets.csv, tile_inventory.csv, overview.png, corner_*.png
What it can show: CRS/transform/bounds facts, tile-vs-mosaic consistency, and a coarse offset estimate where roads
have image contrast. What it cannot show: absolute georeferencing (no independent ground control), legal/true road
position, or alignment where the road layer is itself displaced or roads are low-contrast.
"""
import argparse, csv, glob, os, sys, warnings
import numpy as np
warnings.filterwarnings("ignore")
import rasterio
from rasterio import features
from rasterio.windows import Window
import geopandas as gpd
from scipy import ndimage as ndi
from shapely import affinity

p = argparse.ArgumentParser()
p.add_argument("--mosaic", required=True)
p.add_argument("--roads", required=True)
p.add_argument("--roads-layer", default=None)
p.add_argument("--tiles-glob", default=None, help="e.g. Siddipet\\Damarakunta\\raw\\esri_tile_*.tif (optional)")
p.add_argument("--out-root", default=r"Siddipet\Damarakunta\results\stageD_edge_alignment")
p.add_argument("--tag", required=True)
p.add_argument("--grid", default="4x3", help="analysis blocks across x down (NOT necessarily source tiles)")
p.add_argument("--decim", type=int, default=4, help="read mosaic at 1/decim resolution")
p.add_argument("--max-shift-m", type=float, default=30.0)
p.add_argument("--no-png", action="store_true")
a = p.parse_args()

out = os.path.join(a.out_root, a.tag)
if os.path.exists(out):
    sys.exit(f"REFUSING: {out} already exists (choose a new --tag)")
L = []
def say(s=""): print(s); L.append(s)

with rasterio.open(a.mosaic) as ds:
    say(f"MOSAIC {a.mosaic}")
    say(f"  CRS {ds.crs}  size {ds.width}x{ds.height}  bands {ds.count}  dtype {ds.dtypes[0]}")
    say(f"  transform {tuple(ds.transform)[:6]}")
    say(f"  pixel size x={ds.transform.a:.6f} y={ds.transform.e:.6f}; rotation terms b={ds.transform.b} d={ds.transform.d}")
    say(f"  bounds {tuple(round(v,2) for v in ds.bounds)}")
    mosaic_crs, mosaic_tf, mb = ds.crs, ds.transform, ds.bounds
    f = a.decim
    h, w = ds.height // f, ds.width // f
    nb = min(3, ds.count)
    img = ds.read(list(range(1, nb + 1)), out_shape=(nb, h, w), resampling=rasterio.enums.Resampling.average).astype("float32")
    tf = mosaic_tf * mosaic_tf.scale(ds.width / w, ds.height / h)
gray = img.mean(axis=0)
valid = (img.sum(axis=0) > 0)
say(f"  read at 1/{f}: {w}x{h}, pixel {tf.a:.3f} m; all-zero share {100*(1-valid.mean()):.2f}%")

roads = gpd.read_file(a.roads, layer=a.roads_layer) if a.roads_layer else gpd.read_file(a.roads)
say(f"ROADS {a.roads}: {len(roads)} features, CRS {roads.crs}")
if roads.crs is None or mosaic_crs is None or roads.crs != mosaic_crs:
    say("  CRS DIFFERENCE or missing: roads will be reprojected in memory to the mosaic CRS (source unchanged).")
    roads = roads.to_crs(mosaic_crs)
roads = roads[roads.geometry.notna() & ~roads.geometry.is_empty]

# tile inventory
if a.tiles_glob:
    rows = []
    for t in sorted(glob.glob(a.tiles_glob)):
        with rasterio.open(t) as d:
            tb = d.bounds
            rows.append(dict(file=os.path.basename(t), crs=str(d.crs), width=d.width, height=d.height,
                px_x=round(d.transform.a, 6), px_y=round(d.transform.e, 6),
                ground_w_m=round(tb.right - tb.left, 2), ground_h_m=round(tb.top - tb.bottom, 2),
                px_aspect=round(abs(d.transform.a / d.transform.e), 6),
                inside_mosaic=(tb.left >= mb.left - 1e-6 and tb.right <= mb.right + 1e-6 and tb.bottom >= mb.bottom - 1e-6 and tb.top <= mb.top + 1e-6)))
    say(f"TILES matched by glob: {len(rows)}")
    for r in rows: say("  " + ", ".join(f"{k}={v}" for k, v in r.items()))
else:
    rows = []
    say("TILES: --tiles-glob not given; per-tile transforms not inspected.")

# block offset analysis
gx, gy = (int(v) for v in a.grid.lower().split("x"))
gm = ndi.gaussian_gradient_magnitude(gray, sigma=1.0)
step = tf.a                                    # metres per analysed pixel
shifts = np.arange(-a.max_shift_m, a.max_shift_m + 1e-6, step * 1.0)
res = []
for bj in range(gy):
    for bi in range(gx):
        r0, r1 = bj * h // gy, (bj + 1) * h // gy
        c0, c1 = bi * w // gx, (bi + 1) * w // gx
        sub_tf = tf * tf.translation(c0, r0)
        sub_valid = valid[r0:r1, c0:c1]
        row = dict(block=f"r{bj}c{bi}", valid_share_pct=round(100 * sub_valid.mean(), 1))
        if sub_valid.mean() < 0.5:
            row.update(status="SKIPPED_MOSTLY_NO_IMAGE"); res.append(row); continue
        x0, y0 = sub_tf * (0, 0); x1, y1 = sub_tf * (c1 - c0, r1 - r0)
        from shapely.geometry import box
        pad = a.max_shift_m + 5
        clip = box(min(x0, x1) - pad, min(y0, y1) - pad, max(x0, x1) + pad, max(y0, y1) + pad)
        geoms = [g for g in roads.geometry.intersection(clip) if not g.is_empty]
        length = sum(g.length for g in geoms)
        row["road_length_m"] = round(length, 0)
        if length < 300:
            row.update(status="SKIPPED_LITTLE_ROAD"); res.append(row); continue
        g_sub = gm[r0:r1, c0:c1]
        # 2-D search on a coarse shift grid
        best = None; grid_vals = {}
        for dx in shifts:
            for dy in shifts:
                sh = [affinity.translate(g, xoff=dx, yoff=dy) for g in geoms]
                m = features.rasterize([(g, 1) for g in sh], out_shape=g_sub.shape, transform=sub_tf, fill=0, all_touched=False, dtype="uint8")
                m = (m > 0) & sub_valid
                if m.sum() < 50: continue
                v = float(g_sub[m].mean()); grid_vals[(round(dx, 2), round(dy, 2))] = v
                if best is None or v > best[0]: best = (v, dx, dy)
        if best is None:
            row.update(status="SKIPPED_NO_ROAD_PIXELS"); res.append(row); continue
        v0 = grid_vals.get((0.0, 0.0), float("nan"))
        allv = np.array(list(grid_vals.values()))
        z = (best[0] - allv.mean()) / (allv.std() + 1e-9)
        row.update(grad_at_zero_shift=round(v0, 3), best_dx_m=round(best[1], 1), best_dy_m=round(best[2], 1),
                   best_grad=round(best[0], 3), peak_over_mean=round(best[0] / (allv.mean() + 1e-9), 3), peak_z=round(z, 2),
                   status="INFORMATIVE" if best[0] / (allv.mean() + 1e-9) >= 1.10 else "LOW_CONTRAST_UNINFORMATIVE")
        res.append(row)
say("BLOCK OFFSET ESTIMATES (image-gradient maximum along road lines vs shifted copies)")
say("  Interpretation limits: a block is INFORMATIVE only if shifted-road contrast has a clear peak; best_dx/dy is the shift of the ROAD LAYER that best matches image edges. It may reflect road-layer error, not mosaic error.")
for r in res: say("  " + ", ".join(f"{k}={v}" for k, v in r.items()))

os.makedirs(out)
keys = sorted({k for r in res for k in r}, key=lambda k: (k != "block", k))
with open(os.path.join(out, "block_offsets.csv"), "w", newline="") as fh:
    wr = csv.DictWriter(fh, fieldnames=keys); wr.writeheader(); wr.writerows(res)
if rows:
    with open(os.path.join(out, "tile_inventory.csv"), "w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(rows[0])); wr.writeheader(); wr.writerows(rows)

if not a.no_png:
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    rgb = np.clip(np.moveaxis(img, 0, -1) / 255.0, 0, 1) if img.max() > 1.5 else np.moveaxis(img, 0, -1)
    ext = (mb.left, mb.right, mb.bottom, mb.top)
    fig, ax = plt.subplots(figsize=(12, 8)); ax.imshow(rgb, extent=ext)
    roads.plot(ax=ax, color="yellow", linewidth=0.5); ax.set_title("Mosaic (decimated) with TGRAC roads"); fig.savefig(os.path.join(out, "overview.png"), dpi=120); plt.close(fig)
    with rasterio.open(a.mosaic) as ds:
        wpx = 1000
        for name, (c, r) in dict(NW=(0, 0), NE=(ds.width - wpx, 0), SW=(0, ds.height - wpx), SE=(ds.width - wpx, ds.height - wpx)).items():
            win = Window(c, r, wpx, wpx)
            crop = ds.read(list(range(1, nb + 1)), window=win).astype("float32")
            rgbc = np.clip(np.moveaxis(crop, 0, -1) / 255.0, 0, 1)
            wtf = ds.window_transform(win); x0, y0 = wtf * (0, 0); x1, y1 = wtf * (wpx, wpx)
            fig, ax = plt.subplots(figsize=(8, 8)); ax.imshow(rgbc, extent=(x0, x1, y1, y0))
            roads.plot(ax=ax, color="yellow", linewidth=0.8)
            ax.set_xlim(min(x0, x1), max(x0, x1)); ax.set_ylim(min(y0, y1), max(y0, y1))
            ax.set_title(f"corner {name} (600 m)"); fig.savefig(os.path.join(out, f"corner_{name}.png"), dpi=110); plt.close(fig)
with open(os.path.join(out, "edge_alignment_report.txt"), "w") as fh: fh.write("\n".join(L))
say(f"WRITTEN (new folder only): {out}")
