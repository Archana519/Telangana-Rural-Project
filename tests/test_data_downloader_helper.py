"""Offline tests for src/utils/data_downloader_helper.py (no network: network calls are exercised via local files / monkeypatching)."""
import copy
import json

import geopandas as gpd
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import Point, box

from src.routing.hierarchical_router import load_config
from src.utils import data_downloader_helper as dl

CFG = load_config()


def test_tile_names_for_siddipet_and_edges():
    assert dl.worldcover_tiles((78.6, 17.6, 78.9, 17.9)) == ["N15E078"]
    assert dl.worldcover_tiles((78.0, 17.5, 79.5, 18.5)) == ["N15E078", "N18E078"]       # crosses the 18 N tile edge
    assert dl.dem_tiles((78.6, 17.6, 78.9, 17.9)) == [(17, 78)]
    assert len(dl.dem_tiles((78.0, 16.5, 80.2, 18.5))) == 9
    assert dl.cop_name(17, 78) == "Copernicus_DSM_COG_10_N17_00_E078_00_DEM"
    assert dl.cop_name(-3, -70) == "Copernicus_DSM_COG_10_S03_00_W070_00_DEM"


def test_aligned_bounds_are_lattice_multiples_and_cover():
    b = (258810.3, 1955611.9, 265592.4, 1960912.1)
    a = dl.aligned_bounds(b, 10.0, buffer_m=0.0)
    assert all(v % 10 == 0 for v in a) and a[0] <= b[0] and a[1] <= b[1] and a[2] >= b[2] and a[3] >= b[3]


def _write_tile(path, west, north, val_fn, dtype="float32", nodata=-9999.0, n=60, deg=0.1):
    T = from_origin(west, north, deg / n, deg / n)
    arr = np.fromfunction(val_fn, (n, n)).astype(dtype)
    with rasterio.open(path, "w", driver="GTiff", height=n, width=n, count=1, dtype=dtype, crs="EPSG:4326", transform=T, nodata=nodata) as d:
        d.write(arr, 1)


def test_warp_to_grid_mosaics_two_wgs84_tiles_into_utm(tmp_path):
    # two side-by-side 0.1-degree tiles around 78.7E / 17.7N, constant values 100 and 200
    _write_tile(tmp_path / "a.tif", 78.60, 17.80, lambda r, c: 100 + 0 * r)
    _write_tile(tmp_path / "b.tif", 78.70, 17.80, lambda r, c: 200 + 0 * r)
    bounds = dl.aligned_bounds((248000.0, 1957000.0, 272000.0, 1961000.0), 30.0)
    out = dl.warp_to_grid([str(tmp_path / "a.tif"), str(tmp_path / "b.tif")], bounds, "EPSG:32644", 30.0, tmp_path / "o.tif",
                          "bilinear", "float32", -9999.0)
    with rasterio.open(out) as s:
        a = s.read(1)
        assert s.crs.to_epsg() == 32644 and abs(s.res[0] - 30.0) < 1e-9 and s.bounds.left == bounds[0]
    assert set(np.unique(a[a != -9999.0]).round().astype(int)) <= {100, 200}
    assert (a == 100).any() and (a == 200).any()                  # both tiles contribute, later tile only fills gaps


def test_warp_unreadable_source_is_skipped_not_fatal(tmp_path):
    _write_tile(tmp_path / "a.tif", 78.60, 17.80, lambda r, c: 100 + 0 * r)
    out = dl.warp_to_grid([str(tmp_path / "missing.tif"), str(tmp_path / "a.tif")], dl.aligned_bounds((248000.0, 1957000.0, 256000.0, 1960000.0), 30.0),
                          "EPSG:32644", 30.0, tmp_path / "o.tif", "nearest", "float32", -9999.0)
    with rasterio.open(out) as s:
        assert (s.read(1) == 100).any()


def test_classify_place_rules():
    assert dl.classify_place("Primary Health Centre Markook", "hospital") == "PHC"
    assert dl.classify_place("Gajwel PHC", None) == "PHC"
    assert dl.classify_place("Rythu Bazar", "shop") == "Market"
    assert dl.classify_place("Mandal Parishad Office", "government") == "Mandal HQ"
    assert dl.classify_place("Itikyala Government High School", "school") is None


def test_derive_boundaries_selects_district_and_mandal():
    crs = 4326
    adm2 = gpd.GeoDataFrame({"shapeName": ["Siddipet", "Medak"], "shapeID": ["a", "b"]}, geometry=[box(78.0, 17.0, 79.0, 18.0), box(79.0, 17.0, 80.0, 18.0)], crs=crs)
    adm3 = gpd.GeoDataFrame({"shapeName": ["Markook", "Gajwel", "Other"], "shapeID": list("xyz")},
                            geometry=[box(78.6, 17.6, 78.9, 17.9), box(78.1, 17.1, 78.3, 17.3), box(79.2, 17.2, 79.4, 17.4)], crs=crs)
    dist, inside, mandal = dl.derive_boundaries(adm2, adm3)
    assert dist.shapeName.iloc[0] == "Siddipet" and sorted(inside.shapeName) == ["Gajwel", "Markook"] and mandal.shapeName.iloc[0] == "Markook"
    with pytest.raises(ValueError):
        dl.derive_boundaries(adm2, adm3, anchor=(70.0, 10.0))


def test_plan_reports_present_and_missing(tmp_path):
    cfg = copy.deepcopy(CFG)
    (tmp_path / "there.gpkg").write_bytes(b"x")
    cfg["data"]["district"]["boundary"] = str(tmp_path / "there.gpkg")
    cfg["data"]["district"]["roads"] = str(tmp_path / "nope.gpkg")
    arts = {(a.level, a.name): a for a in dl.plan(cfg, tmp_path, ["district"])}
    assert arts[("district", "boundary")].exists and not arts[("district", "roads")].exists


def test_existing_files_are_never_redownloaded(tmp_path, monkeypatch):
    cfg = copy.deepcopy(CFG)
    for lvl in ("gp", "mandal", "district"):
        for k in ("landcover", "dem"):
            p = tmp_path / f"{lvl}_{k}.tif"
            p.write_bytes(b"x")
            cfg["data"][lvl][k] = str(p)
    called = []
    monkeypatch.setattr(dl, "warp_to_grid", lambda *a, **k: called.append(1))
    for lvl in ("gp", "mandal", "district"):
        assert dl.fetch_rasters(cfg, tmp_path, lvl, log=lambda *_: None) == []
    assert not called


def test_http_download_uses_cache(tmp_path, monkeypatch):
    dest = tmp_path / "c" / "f.bin"
    dest.parent.mkdir()
    dest.write_bytes(b"cached")
    monkeypatch.setattr(dl.urllib.request, "urlopen", lambda *a, **k: (_ for _ in ()).throw(AssertionError("network used")))
    assert dl.http_download("https://example.invalid/f", dest, log=lambda *_: None) == dest


def test_provenance_sidecar_written(tmp_path):
    f = tmp_path / "x.gpkg"
    f.write_bytes(b"x")
    dl.write_provenance(f, source="unit-test", rows=3)
    j = json.loads((tmp_path / "x.gpkg.provenance.json").read_text())
    assert j["source"] == "unit-test" and j["reference_data_not_ground_truth"] is True


def test_terminals_flagged_as_proxy(tmp_path):
    cfg = copy.deepcopy(CFG)
    m = gpd.GeoDataFrame({"mandal": ["Markook", "Siddipet Urban"]}, geometry=[box(0, 0, 10, 10), box(20, 0, 30, 10)], crs=cfg["crs"])
    cfg["data"]["district"]["mandal_boundaries"] = str(tmp_path / "m.gpkg")
    cfg["data"]["district"]["terminals"] = str(tmp_path / "t.gpkg")
    m.to_file(tmp_path / "m.gpkg", driver="GPKG")
    dl.fetch_district_terminals(cfg, tmp_path, log=lambda *_: None)
    t = gpd.read_file(tmp_path / "t.gpkg")
    assert t.proxy.all() and set(t.kind) == {"mandal_hq", "district_hq"} and "DISTRICT_HQ" in set(t.id)
