#!/usr/bin/env python
"""List every downloaded input file of a village (size, SHA-256, source URL pattern, release / version, licence) as acquired_data_manifest.csv in the village's open-data result folder.

    python scripts/write_acquired_manifest.py --village alampur

Reads data/villages/<id>/ and data/villages/<slug>_esri/ (git-ignored); run it on the machine that holds the downloads. The file is committed so the provenance survives without the data.
"""
import argparse
import hashlib
import sys
from datetime import date
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from src.multivillage import acquire as A      # noqa: E402

LIC = dict(overture="ODbL 1.0 (buildings, transportation); CDLA-Permissive-2.0 (places, divisions); see the release notes", wc="CC BY 4.0", cop="Copernicus DEM licence (free, attribution)", esri="Esri World Imagery terms; non-commercial academic use, credit required",
           derived="derived from the files above; licence of the inputs applies")


def sha(p: Path):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--village", required=True)
    a = ap.parse_args()
    cfg = A.load_cfg(a.village)
    v = cfg["village"]
    d, w = A.data_dir(cfg), REPO / "data" / "villages" / f"{v['work_slug']}_esri"
    rel = cfg["overture_release"]
    ov = "https://overturemaps-us-west-2.s3.amazonaws.com/release/{rel}/theme={theme}/type={typ}/"
    from src.utils import data_downloader_helper as dl
    import geopandas as gpd
    b = gpd.read_file(d / "boundary.gpkg").to_crs(4326).total_bounds
    wc_tiles, dem_tiles = dl.worldcover_tiles(tuple(b)), [dl.cop_name(la, lo) for la, lo in dl.dem_tiles(tuple(b))]
    rows = [("boundary.gpkg", "study polygon: configs/multivillage/villages/%s_boundary.geojson (see its provenance file)" % a.village, "see provenance file", "see provenance file", LIC["derived"]),
            ("roads.gpkg", ov.format(rel=rel, theme="transportation", typ="segment"), rel, "Overture transportation segments (road classes)", LIC["overture"]),
            ("buildings.gpkg", ov.format(rel=rel, theme="buildings", typ="building"), rel, "Overture buildings (open footprints)", LIC["overture"]),
            ("places_4km.gpkg", ov.format(rel=rel, theme="places", typ="place"), rel, "Overture places within 4 km (facility candidates)", LIC["overture"]),
            ("worldcover_10m.tif", " ; ".join(dl.WC_URL.format(tile=t) for t in wc_tiles), "ESA WorldCover v200 (2021)", "tiles " + ", ".join(wc_tiles), LIC["wc"]),
            ("dem_30m.tif", " ; ".join(dl.COP_URL.format(name=n) for n in dem_tiles), "Copernicus DEM GLO-30 (DGED COG)", "tiles " + ", ".join(dem_tiles), LIC["cop"]),
            ("slope_30m.tif", "computed from dem_30m.tif (Sobel)", "-", "-", LIC["derived"]), ("slope_10m.tif", "computed from slope_30m.tif (bilinear to 10 m)", "-", "-", LIC["derived"])]
    out = []
    for fn, url, relv, note, lic in rows:
        p = d / fn
        if p.exists():
            out.append(dict(file=f"data/villages/{a.village}/{fn}", bytes=p.stat().st_size, sha256=sha(p), source_url=url, release_or_version=relv, note=note, licence=lic, listed=str(date.today())))
    for p in sorted((w / "esri_tiles").glob("*.tif")) + sorted((w / "aligned").glob("*.tif")):
        out.append(dict(file=str(p.relative_to(REPO)).replace("\\", "/"), bytes=p.stat().st_size, sha256=sha(p), source_url="https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/export",
                        release_or_version="live service; exported on the file date", note="0.6 m/px, EPSG:32644" + (" (mosaic of the tiles)" if p.parent.name == "aligned" else ""), licence=LIC["esri"], listed=str(date.today())))
    dest = REPO / "DELIVERABLES_CONTRIBUTION_3_MULTI_VILLAGE" / v["folder"] / "acquired_data_manifest.csv"
    pd.DataFrame(out).to_csv(dest, index=False, lineterminator="\n")
    print("wrote", dest, len(out), "files")


if __name__ == "__main__":
    main()
