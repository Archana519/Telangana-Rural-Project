#!/usr/bin/env python
"""audit_provenance_alignment.py - READ-ONLY. (A) provenance evidence for the two school-compound GeoPackages,
(D) exact raster-grid alignment of the Damarakunta rasters. Writes only a NEW folder; refuses to reuse one; no network.

A: GeoPackage internals (tables, SRS, application id, hashes, times); is the UTM file a pure reprojection of the other
   (geometry difference, vertex counts, attribute equality); text search of the project for scripts/logs/notes that mention
   the files (extensions .py .ps1 .txt .md .json .csv .log .ipynb .bat .cmd .cfg, < 5 MB, .venv excluded).
D: for each raster: transform, origin, size; exact transform equality inside grid families (0.6 m, 10 m); origin offsets of
   each grid relative to the others, in cells; extents.  It reports numbers; it does not call anything 'aligned' unless
   transforms match to 1e-6 of a cell.

Run from D:\\Telangana_Rural_Project:
  .venv\\Scripts\\python.exe scripts\\audit_provenance_alignment.py --tag pa1
"""
import argparse, hashlib, json, os, re, sqlite3, sys
from datetime import datetime, timezone
from pathlib import Path
import numpy as np, geopandas as gpd, rasterio

NEEDLES = ["school_compounds", "School_Code", "School_Name", "SchoolGIS", "school compound", "school_compound"]
EXT = {".py", ".ps1", ".txt", ".md", ".json", ".csv", ".log", ".ipynb", ".bat", ".cmd", ".cfg"}


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def gpkg_internals(p):
    c = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
    q = lambda s: c.execute(s).fetchall()
    d = dict(application_id=q("PRAGMA application_id")[0][0], user_version=q("PRAGMA user_version")[0][0])
    for t in ("gpkg_contents", "gpkg_geometry_columns", "gpkg_spatial_ref_sys", "gpkg_metadata", "gpkg_extensions", "gpkg_ogr_contents"):
        try:
            rows = q(f"SELECT * FROM {t}")
            d[t] = [list(map(str, r))[:12] for r in rows][:12]
        except Exception as e:
            d[t] = f"absent ({e.__class__.__name__})"
    d["tables"] = [r[0] for r in q("SELECT name FROM sqlite_master WHERE type='table'")]
    c.close()
    return d


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default="."); ap.add_argument("--village-dir", default="Siddipet/Damarakunta")
    ap.add_argument("--tag", default=None)
    a = ap.parse_args()
    root = Path(a.root).resolve(); V = root / a.village_dir; ref = V / "reference"
    out = V / "results" / "stageA2_provenance_alignment" / (a.tag or "pa_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    if out.exists() and any(out.iterdir()):
        sys.exit(f"{out} exists; choose another --tag")
    out.mkdir(parents=True)
    R = {}

    # ---------------- A
    A = {}
    f1, f2 = ref / "school_compounds.gpkg", ref / "school_compounds_utm44n.gpkg"
    for f in (f1, f2):
        A[f.name] = dict(exists=f.exists())
        if f.exists():
            st = f.stat(); A[f.name].update(bytes=st.st_size, modified=datetime.fromtimestamp(st.st_mtime).isoformat(), sha256=sha(f), internals=gpkg_internals(f))
    if f1.exists() and f2.exists():
        g1, g2 = gpd.read_file(f1), gpd.read_file(f2)
        cmp = dict(crs_file1=str(g1.crs), crs_file2=str(g2.crs), n1=len(g1), n2=len(g2), columns_equal=list(g1.columns) == list(g2.columns))
        if g1.crs and g2.crs and len(g1) == len(g2):
            r1 = g1.to_crs(g2.crs)
            sd, hd, vt = [], [], []
            for x, y in zip(r1.geometry, g2.geometry):
                sd.append(float(x.symmetric_difference(y).area)); hd.append(float(x.hausdorff_distance(y)))
                vt.append((len(x.exterior.coords) if x.geom_type == "Polygon" else None, len(y.exterior.coords) if y.geom_type == "Polygon" else None))
            cmp.update(symmetric_difference_area_m2=sd, hausdorff_m=hd, vertex_counts=vt, area_file2_m2=[float(v) for v in g2.area])
            other = [c for c in g1.columns if c != "geometry" and c in g2.columns]
            cmp["attribute_columns_identical"] = bool(g1[other].astype(str).equals(g2[other].astype(str)))
            cmp["only_in_file1"] = [c for c in g1.columns if c not in g2.columns]; cmp["only_in_file2"] = [c for c in g2.columns if c not in g1.columns]
            for c in ("School_Code", "School_Name", "Village_Name", "Latitude", "Longitude", "Shape_Area"):
                if c in g2.columns: cmp[c] = g2[c].astype(str).tolist()
        A["comparison"] = cmp
    hits = []
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in (".venv", ".git", "__pycache__", "node_modules")]
        for n in fn:
            p = Path(dp) / n
            if p.suffix.lower() in EXT:
                try:
                    if p.stat().st_size > 5_000_000: continue
                    lines = p.read_text(encoding="utf-8", errors="ignore").splitlines()
                except Exception:
                    continue
                m = [(i + 1, l.strip()[:160]) for i, l in enumerate(lines) if any(k.lower() in l.lower() for k in NEEDLES)]
                if m:
                    hits.append(dict(file=str(p.relative_to(root)), n=len(m), first=m[:3], modified=datetime.fromtimestamp(p.stat().st_mtime).isoformat()))
    A["text_mentions"] = sorted(hits, key=lambda h: h["modified"])
    for nm in ("sources.json", "study_area_config.json"):
        p = V / "study_area" / nm
        A[nm] = dict(exists=p.exists(), mentions_school=(p.exists() and "school" in p.read_text(encoding="utf-8", errors="ignore").lower()))
    R["A_school_provenance"] = A

    # ---------------- D
    rs = {}
    cand = sorted(list((V / "aligned").glob("*.tif")) + list((V / "predictions").rglob("pred_classes*.tif")) + list((V / "predictions").rglob("building_prob*.tif")))
    for p in cand:
        try:
            with rasterio.open(p) as s:
                t = s.transform
                rs[str(p.relative_to(root))] = dict(epsg=s.crs.to_epsg() if s.crs else None, w=s.width, h=s.height, res=[abs(t.a), abs(t.e)], origin=[t.c, t.f],
                                                     transform=list(t)[:6], bounds=list(s.bounds), rotation=[t.b, t.d])
        except Exception as e:
            rs[str(p)] = dict(error=repr(e))
    ok = {k: v for k, v in rs.items() if "transform" in v}
    fam = {}
    for k, v in ok.items():
        fam.setdefault(f"{v['res'][0]:g} m", []).append(k)
    D = dict(rasters=rs, families={})
    for f, ks in fam.items():
        base = ok[ks[0]]; rows = []
        for k in ks:
            v = ok[k]
            rows.append(dict(raster=k, same_transform_as_first=bool(np.allclose(v["transform"], base["transform"], atol=1e-9)), same_shape_as_first=(v["w"], v["h"]) == (base["w"], base["h"]),
                             origin_offset_vs_first_in_cells=[(v["origin"][0] - base["origin"][0]) / base["res"][0], (v["origin"][1] - base["origin"][1]) / base["res"][1]]))
        D["families"][f] = rows
    # cross-family: offsets of each grid origin relative to the finest grid, in cells of the COARSER grid
    names = sorted(ok, key=lambda k: ok[k]["res"][0]); cross = []
    for i, ka in enumerate(names):
        for kb in names[i + 1:]:
            va, vb = ok[ka], ok[kb]
            if va["res"][0] == vb["res"][0]: continue
            ox = ((va["origin"][0] - vb["origin"][0]) / vb["res"][0]) % 1; oy = ((va["origin"][1] - vb["origin"][1]) / vb["res"][1]) % 1
            ratio = vb["res"][0] / va["res"][0]
            cross.append(dict(fine=ka, coarse=kb, ratio=ratio, ratio_is_integer=abs(ratio - round(ratio)) < 1e-9, fractional_offset_x_in_coarse_cells=ox, fractional_offset_y_in_coarse_cells=oy,
                              fine_origin_on_coarse_cell_edge=bool(min(ox, 1 - ox) < 1e-6 and min(oy, 1 - oy) < 1e-6)))
    D["cross_family_origin_offsets"] = cross
    R["D_raster_alignment"] = D
    (out / "provenance_alignment.json").write_text(json.dumps(R, indent=1, default=str))
    print("A: files", {k: v.get("exists") for k, v in A.items() if k.endswith(".gpkg")})
    c = A.get("comparison", {})
    print("A: crs", c.get("crs_file1"), "->", c.get("crs_file2"), "| symdiff m2", c.get("symmetric_difference_area_m2"), "| hausdorff m", c.get("hausdorff_m"), "| attrs identical", c.get("attribute_columns_identical"))
    print("A: only in file1:", c.get("only_in_file1"), "| only in file2:", c.get("only_in_file2"))
    print("A: text mentions (oldest first):")
    for h in A["text_mentions"]:
        print(f"   {h['modified'][:16]}  {h['file']}  ({h['n']} lines)")
    print("D: families")
    for f, rows in D["families"].items():
        print(f"  {f}:", [(Path(r['raster']).name, r['same_transform_as_first'], r['same_shape_as_first']) for r in rows])
    print("D: cross-family:")
    for x in cross:
        print(f"   {Path(x['fine']).name} -> {Path(x['coarse']).name}: ratio {x['ratio']:.4g}, integer {x['ratio_is_integer']}, frac offset ({x['fractional_offset_x_in_coarse_cells']:.4f}, {x['fractional_offset_y_in_coarse_cells']:.4f}), on cell edge {x['fine_origin_on_coarse_cell_edge']}")
    print("\nfull detail:", out)


if __name__ == "__main__":
    main()
