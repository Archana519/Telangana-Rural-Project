#!/usr/bin/env python
"""view_footprints.py - overlay extracted building-footprint polygons on satellite imagery.

Read-only on all inputs. Writes only new PNG/PDF files into --out-dir (a new subfolder).
Outputs (prefix = --name, default 'footprints_overlay'):
  <name>.png            full test-window overview
  <name>_closeup.png    densest cluster close-up
  <name>_sidebyside.png close-up: imagery alone | imagery + outlines
Polygons are model-derived candidates, NOT verified buildings. No metrics are computed.
"""
import argparse, math, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent
VILLAGE = ROOT / "Siddipet" / "Damarakunta"
DEF_IMG = VILLAGE / "aligned" / "damarakunta_esri_highres_mosaic_0p6m.tif"
DEF_BLD = VILLAGE / "results" / "footprints_v9_test" / "footprints_test.gpkg"
DEF_OUT = VILLAGE / "results" / "footprints_v9_test" / "overlay_views"


def warn(m):
    print(f"WARNING: {m}")


def die(m):
    print(f"ERROR: {m}")
    sys.exit(2)


def load_image_window(src, bounds, margin):
    """Read only the needed window. Returns (rgb float/uint8 array HxWx3, valid mask, extent[l,r,b,t], window bounds)."""
    import rasterio
    from rasterio.windows import from_bounds, Window
    from rasterio.vrt import WarpedVRT
    from rasterio.transform import array_bounds
    ds = src
    t = src.transform
    vrt = None
    if abs(t.b) > 1e-9 or abs(t.d) > 1e-9 or t.e > 0:
        warn("raster transform is rotated/south-up; reading through a north-up WarpedVRT")
        from rasterio.warp import calculate_default_transform
        tr, w, h = calculate_default_transform(src.crs, src.crs, src.width, src.height, *src.bounds)
        vrt = WarpedVRT(src, crs=src.crs, transform=tr, width=w, height=h)
        ds = vrt
    minx, miny, maxx, maxy = bounds
    minx -= margin; miny -= margin; maxx += margin; maxy += margin
    l, b, r, tp = ds.bounds
    cx0, cy0, cx1, cy1 = max(minx, l), max(miny, b), min(maxx, r), min(maxy, tp)
    if not (cx0 < cx1 and cy0 < cy1):
        die("requested window does not intersect the raster")
    if (cx0, cy0, cx1, cy1) != (minx, miny, maxx, maxy):
        warn("window clipped to raster extent (part of the margin has no imagery)")
    win = from_bounds(cx0, cy0, cx1, cy1, ds.transform).round_offsets().round_lengths()
    win = win.intersection(Window(0, 0, ds.width, ds.height))
    if win.width < 2 or win.height < 2:
        die("window is empty after rounding")
    nb = min(ds.count, 3)
    arr = ds.read(list(range(1, nb + 1)), window=win, masked=True)
    wt = ds.window_transform(win)
    ext_b = array_bounds(int(win.height), int(win.width), wt)  # (minx? ) -> (west,south,east,north)
    extent = [ext_b[0], ext_b[2], ext_b[1], ext_b[3]]
    valid = ~np.ma.getmaskarray(arr).any(axis=0)
    data = np.ma.getdata(arr)
    if ds.nodata is not None:
        valid &= ~(data == ds.nodata).all(axis=0)
    if nb == 1:
        data = np.repeat(data, 3, axis=0)
    elif nb == 2:
        data = np.concatenate([data, data[:1]], axis=0)
    img = np.transpose(data, (1, 2, 0)).astype("float32")
    if data.dtype != np.uint8:
        pool = img[valid] if valid.any() else img.reshape(-1, 3)
        lo, hi = np.percentile(pool, [2, 98])
        img = np.clip((img - lo) / max(hi - lo, 1e-6), 0, 1)
    else:
        img = img / 255.0
    img[~valid] = 0
    if vrt is not None:
        vrt.close()
    return img, valid, extent, (cx0, cy0, cx1, cy1)


def densest_window(gdf, size):
    """Return bounds of a size x size window with most polygon centroids (step size/4)."""
    c = gdf.geometry.centroid
    xs, ys = c.x.values, c.y.values
    step = size / 4.0
    best, bb = -1, None
    for x0 in np.arange(xs.min() - size / 2, xs.max() + step, step):
        for y0 in np.arange(ys.min() - size / 2, ys.max() + step, step):
            n = int(((xs >= x0) & (xs < x0 + size) & (ys >= y0) & (ys < y0 + size)).sum())
            if n > best:
                best, bb = n, (x0, y0, x0 + size, y0 + size)
    return bb, best


def flag_mask(gdf, large_area):
    f = np.zeros(len(gdf), bool)
    if "flag" in gdf.columns:
        f |= gdf["flag"].astype(str).str.contains("BLOB|MERGE|UNRESOLVED", case=False, na=False).values
    f |= (gdf.geometry.area.values > large_area)
    return f


def draw(ax, img, extent, gdf, flagged, lw, show_poly=True):
    ax.imshow(img, extent=extent, origin="upper", interpolation="nearest")
    if show_poly and len(gdf):
        for sub, col in ((gdf[~flagged], "#FFEB3B"), (gdf[flagged], "#FF7043")):
            if len(sub):
                sub.boundary.plot(ax=ax, color="black", linewidth=lw * 2.2)  # halo
                sub.boundary.plot(ax=ax, color=col, linewidth=lw)
    ax.set_xlim(extent[0], extent[1]); ax.set_ylim(extent[2], extent[3])
    ax.set_aspect("equal"); ax.tick_params(labelsize=7)
    ax.ticklabel_format(useOffset=False, style="plain")


def scalebar(ax, extent):
    import matplotlib.patches as mp
    w = extent[1] - extent[0]
    L = 10 ** math.floor(math.log10(w / 4)) * (5 if w / 4 / 10 ** math.floor(math.log10(w / 4)) >= 5 else 2 if w / 4 / 10 ** math.floor(math.log10(w / 4)) >= 2 else 1)
    x0 = extent[0] + 0.04 * w; y0 = extent[2] + 0.05 * (extent[3] - extent[2])
    ax.add_patch(mp.Rectangle((x0, y0), L, (extent[3] - extent[2]) * 0.008, fc="white", ec="black", zorder=5))
    ax.text(x0 + L / 2, y0 + (extent[3] - extent[2]) * 0.015, f"{L:g} m", ha="center", color="white",
            fontsize=8, path_effects=_fx(), zorder=6)


def _fx():
    import matplotlib.patheffects as pe
    return [pe.withStroke(linewidth=2, foreground="black")]


def legend(ax, n, nflag):
    from matplotlib.lines import Line2D
    h = [Line2D([], [], color="#FFEB3B", lw=2, label=f"candidate outline ({n - nflag})")]
    if nflag:
        h.append(Line2D([], [], color="#FF7043", lw=2, label=f"large/merged-flagged ({nflag})"))
    ax.legend(handles=h, loc="upper right", fontsize=7, framealpha=0.85)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--imagery", default=str(DEF_IMG))
    ap.add_argument("--buildings", default=str(DEF_BLD))
    ap.add_argument("--layer", default=None, help="GeoPackage layer (default: first layer)")
    ap.add_argument("--out-dir", default=str(DEF_OUT))
    ap.add_argument("--name", default="footprints_overlay")
    ap.add_argument("--margin", type=float, default=30.0, help="metres around footprints (overview)")
    ap.add_argument("--closeup-size", type=float, default=120.0, help="metres, densest-cluster window")
    ap.add_argument("--large-area", type=float, default=400.0, help="m2 above which a polygon is coloured as suspicious")
    ap.add_argument("--linewidth", type=float, default=0.8)
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--pdf", action="store_true", help="also save PDFs")
    a = ap.parse_args()

    import rasterio, geopandas as gpd, matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    img_p, bld_p, out = Path(a.imagery), Path(a.buildings), Path(a.out_dir)
    print(f"cwd:      {Path.cwd()}\nimagery:  {img_p}\nbuildings:{bld_p}\nout-dir:  {out}")
    for p in (img_p, bld_p):
        if not p.exists():
            die(f"input not found: {p}")
    if out.exists() and any(out.iterdir()):
        warn("out-dir already has files; same-named outputs will be replaced. Use --out-dir for a fresh folder.")
    out.mkdir(parents=True, exist_ok=True)

    import fiona  # noqa  (geopandas backend lists layers)
    layers = gpd.list_layers(bld_p)["name"].tolist() if hasattr(gpd, "list_layers") else fiona.listlayers(str(bld_p))
    layer = a.layer or layers[0]
    print(f"layers:   {layers} -> using '{layer}'")
    gdf = gpd.read_file(bld_p, layer=layer)
    print(f"features: {len(gdf)}  CRS: {gdf.crs}  geom types: {sorted(gdf.geom_type.unique().tolist())}")
    print(f"columns:  {[c for c in gdf.columns if c != 'geometry']}")
    bad = gdf.geometry.isna() | gdf.geometry.is_empty
    if bad.any():
        warn(f"dropping {int(bad.sum())} empty/null geometries")
        gdf = gdf[~bad]
    inv = ~gdf.geometry.is_valid
    if inv.any():
        warn(f"repairing {int(inv.sum())} invalid geometries with buffer(0) (in memory only)")
        gdf.loc[inv, "geometry"] = gdf.loc[inv, "geometry"].buffer(0)
    gdf = gdf[gdf.geom_type.isin(["Polygon", "MultiPolygon"])]
    if gdf.empty:
        die("no polygon features to draw (points are not footprints)")

    with rasterio.open(img_p) as src:
        print(f"raster:   {src.width}x{src.height}, bands={src.count}, dtype={src.dtypes[0]}, "
              f"res={src.res}, CRS={src.crs}, nodata={src.nodata}\n          bounds={tuple(round(v, 2) for v in src.bounds)}")
        if src.crs is None:
            die("raster has no CRS")
        if gdf.crs is None:
            die("footprints have no CRS; refusing to guess")
        if gdf.crs != src.crs:
            warn(f"reprojecting footprints {gdf.crs} -> {src.crs}")
            gdf = gdf.to_crs(src.crs)
        from shapely.geometry import box
        tb = gdf.total_bounds
        if not np.all(np.isfinite(tb)):
            die("non-finite footprint bounds")
        inter = box(*tb).intersection(box(*src.bounds)).area
        print(f"footprint bounds: {tuple(round(v, 2) for v in tb)}  overlap with raster: "
              f"{100 * inter / max(box(*tb).area, 1e-9):.1f}% of footprint box")
        if inter <= 0:
            die("footprints do not overlap the imagery: CRS/alignment error")
        flagged = flag_mask(gdf, a.large_area)
        gdf = gdf.reset_index(drop=True)

        views = []
        img, valid, ext, wb = load_image_window(src, tuple(tb), a.margin)
        views.append(("overview", img, valid, ext, wb))
        cb, cn = densest_window(gdf, a.closeup_size)
        print(f"densest cluster: {cn} polygon centroids inside {a.closeup_size:g} m window {tuple(round(v, 1) for v in cb)}")
        cimg, cvalid, cext, cwb = load_image_window(src, cb, 0.0)
        views.append(("closeup", cimg, cvalid, cext, cwb))

    if any((~v[2]).mean() > 0.01 for v in views):
        warn("some pixels are NoData (shown black); do not read black as ground")

    def save(fig, stem):
        p = out / f"{stem}.png"
        fig.savefig(p, dpi=a.dpi, bbox_inches="tight")
        print(f"saved: {p} ({p.stat().st_size:,} bytes)")
        if a.pdf:
            fig.savefig(out / f"{stem}.pdf", bbox_inches="tight")
        plt.close(fig)

    for tag, img, valid, ext, wb in views:
        sub = gdf.cx[ext[0]:ext[1], ext[2]:ext[3]]
        fl = flagged[sub.index.values] if len(sub) else np.array([], bool)
        fig, ax = plt.subplots(figsize=(10, 10))
        draw(ax, img, ext, sub, fl, a.linewidth * (1.6 if tag == "closeup" else 1))
        scalebar(ax, ext); legend(ax, len(sub), int(fl.sum()))
        ax.set_title(f"{tag}: model-derived building-footprint candidates (not verified buildings)\n"
                     f"{len(sub)} polygons in view | imagery: {img_p.name}", fontsize=9)
        ax.set_xlabel("Easting (m)", fontsize=8); ax.set_ylabel("Northing (m)", fontsize=8)
        save(fig, a.name if tag == "overview" else f"{a.name}_closeup")
        if tag == "closeup":
            fig, axs = plt.subplots(1, 2, figsize=(16, 8))
            draw(axs[0], img, ext, sub, fl, a.linewidth, show_poly=False); axs[0].set_title("imagery only", fontsize=9)
            draw(axs[1], img, ext, sub, fl, a.linewidth * 1.6); axs[1].set_title("imagery + candidate outlines", fontsize=9)
            save(fig, f"{a.name}_sidebyside")
    print("done. Open the PNGs in Windows Explorer and check each outline against its roof by eye.")


if __name__ == "__main__":
    main()
