"""
inspect_geotiff.py - print the georeferencing and raster properties of a GeoTIFF.

Usage:
  python inspect_geotiff.py path\\to\\image.tif
  python inspect_geotiff.py path\\to\\image.tif --json out.json

Reports CRS, size, bands, dtype, affine transform, pixel size (and an
approximate size in metres when the CRS is geographic), bounds, nodata,
compression/tiling and overviews. Exit code 2 if the file has no CRS or no
transform, because such a file cannot be used for Siddipet analysis.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import rasterio
from rasterio.warp import transform_bounds


def describe(path: Path) -> dict:
    with rasterio.open(path) as ds:
        t, crs = ds.transform, ds.crs
        info = {
            "file": str(path.resolve()),
            "driver": ds.driver,
            "crs": crs.to_string() if crs else None,
            "epsg": crs.to_epsg() if crs else None,
            "crs_is_geographic": bool(crs and crs.is_geographic),
            "width": ds.width,
            "height": ds.height,
            "band_count": ds.count,
            "dtypes": list(ds.dtypes),
            "nodata": ds.nodata,
            "color_interp": [c.name for c in ds.colorinterp],
            "transform": [t.a, t.b, t.c, t.d, t.e, t.f],
            "pixel_size_x": t.a,
            "pixel_size_y": -t.e,
            "rotation_terms": [t.b, t.d],
            "bounds": list(ds.bounds),
            "compression": ds.compression.name if ds.compression else None,
            "tiled": ds.profile.get("tiled", False),
            "overviews_band1": ds.overviews(1),
            "has_georeference": bool(crs) and not t.is_identity,
        }
        if crs:
            info["bounds_wgs84"] = list(transform_bounds(crs, "EPSG:4326", *ds.bounds))
        if crs and crs.is_geographic:
            lat = (ds.bounds.bottom + ds.bounds.top) / 2
            info["approx_pixel_size_m"] = [
                abs(t.a) * 111_320 * math.cos(math.radians(lat)),
                abs(t.e) * 110_574,
            ]
        elif crs:
            info["approx_pixel_size_m"] = [abs(t.a), abs(t.e)]
        return info


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tif", type=Path)
    ap.add_argument("--json", type=Path, help="also save the report as JSON")
    args = ap.parse_args()
    if not args.tif.exists():
        sys.exit(f"File not found: {args.tif}")

    info = describe(args.tif)
    width = max(len(k) for k in info)
    for k, v in info.items():
        print(f"{k:<{width}} : {v}")
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(info, indent=2), encoding="utf-8")
        print(f"saved: {args.json}")
    if not info["has_georeference"]:
        print("\nWARNING: no CRS or identity transform - this image is NOT georeferenced.")
        sys.exit(2)
    if info["rotation_terms"] != [0.0, 0.0]:
        print("\nNOTE: rotated transform - reproject before tiling for the model.")


if __name__ == "__main__":
    main()
