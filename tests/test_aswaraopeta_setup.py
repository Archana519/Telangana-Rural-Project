"""Offline tests for the Aswaraopeta set-up: true village / town boundary from a polygon file, the candidate finder (scripts/propose_aoi.py), generic scripts."""
import importlib.util
import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import pytest
from rasterio.transform import from_origin
from shapely.geometry import Point, Polygon, box

from src.multivillage import acquire as A, run as R

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("propose_aoi", REPO / "scripts" / "propose_aoi.py")
PA = importlib.util.module_from_spec(spec)
spec.loader.exec_module(PA)


def test_config_and_folders():
    c = A.load_cfg("aswaraopeta")["village"]
    assert c["boundary_method"] == "polygon_file" and c["district"] == "Bhadradri" and c["adm3_name"] == "Aswaraopeta"
    assert R.FOLDERS["aswaraopeta"] == c["folder"] == "02_ASWARAOPETA" and c["bundle_folder"] == "03_ASWARAOPETA_SEMI_URBAN"
    assert "min_dist_to_road_m" in c and c["min_dist_to_road_m"] == A.load_cfg("adilabad_urban")["village"]["min_dist_to_road_m"]      # same target rule as Adilabad
    assert R.FOLDERS["adilabad_urban"] == A.load_cfg("adilabad_urban")["village"]["folder"]


def test_missing_boundary_file_explains_what_to_do(tmp_path):
    cfg = A.load_cfg("aswaraopeta")
    cfg["village"]["boundary_file"] = str(tmp_path / "nope.geojson")
    with pytest.raises(FileNotFoundError, match="propose_aoi.py"):
        A.boundary(cfg)


def test_name_matching_handles_spellings():
    al = ["Aswaraopeta", "Ashwaraopet"]
    assert PA.name_score("Ashwaraopeta", al) == 1.0 and PA.name_score("Aswaraopet", al) == 1.0
    assert PA.name_score("Aswaraopeta Mandal", al) == 0.6 and PA.name_score("Aswapuram", al) == 0.0


def test_osm_relation_assembly_with_hole():
    outer1 = [{"lon": 0, "lat": 0}, {"lon": 2, "lat": 0}, {"lon": 2, "lat": 2}]
    outer2 = [{"lon": 2, "lat": 2}, {"lon": 0, "lat": 2}, {"lon": 0, "lat": 0}]               # two ways that only close together
    hole = [{"lon": 0.5, "lat": 0.5}, {"lon": 1, "lat": 0.5}, {"lon": 1, "lat": 1}, {"lon": 0.5, "lat": 1}, {"lon": 0.5, "lat": 0.5}]
    el = {"type": "relation", "id": 1, "members": [{"role": "outer", "geometry": outer1}, {"role": "outer", "geometry": outer2}, {"role": "inner", "geometry": hole}]}
    g = PA.osm_to_polygon(el)
    assert abs(g.area - (4 - 0.25)) < 1e-9
    way = {"type": "way", "geometry": [{"lon": 0, "lat": 0}, {"lon": 1, "lat": 0}, {"lon": 1, "lat": 1}, {"lon": 0, "lat": 0}]}
    assert PA.osm_to_polygon(way).area == pytest.approx(0.5)
    assert PA.osm_to_polygon({"type": "way", "geometry": [{"lon": 0, "lat": 0}, {"lon": 1, "lat": 0}]}) is None


def test_ranking_prefers_the_plausible_named_polygon():
    mandal = box(81.0, 17.2, 81.3, 17.5)
    rows = [dict(source="osm", name="Aswaraopeta", kind="boundary/admin_level=10", source_id="relation/1", geometry=box(81.12, 17.24, 81.15, 17.27)),
            dict(source="osm", name="Aswaraopeta", kind="boundary/admin_level=6", source_id="relation/2", geometry=mandal),                         # the mandal itself
            dict(source="overture", name="Other Village", kind="locality", source_id="x", geometry=box(81.2, 17.3, 81.22, 17.32)),
            dict(source="osm", name="Aswaraopeta", kind="place/village", source_id="relation/3", geometry=box(80.5, 17.0, 80.52, 17.02))]          # outside the mandal
    r = PA.rank_candidates(gpd.GeoDataFrame(rows, geometry="geometry", crs=4326), mandal, ["Aswaraopeta"])
    assert r.iloc[0].source_id == "relation/1" and r.iloc[0].verdict == "plausible"
    v = dict(zip(r.source_id, r.verdict))
    assert "too large" in v["relation/2"] and "name" in v["x"] and "inside the mandal" in v["relation/3"]


def test_settlement_extent_follows_the_built_up_area_not_a_box():
    res = 10.0
    lc = np.full((600, 600), 40, np.uint8)                                  # cropland, 6 km x 6 km
    lc[200:330, 250:380] = 50                                               # town core, 1.3 km
    lc[200:330, 400:430] = 50                                               # outlying colony 200 m east of the core (must be linked)
    lc[300:306, 380:400] = 50
    lc[500:540, 20:60] = 50                                                 # far village (must stay out)
    lc[250:255, 300:305] = 40                                               # small gap inside the core (must be filled)
    T = from_origin(0, 6000, res, res)
    g = PA.settlement_extent_from_raster(lc, T, centre_xy=(3150.0, 3700.0))
    assert g.contains(Point(3150, 3700)) and g.contains(Point(4150, 3900))   # core and the colony
    assert not g.intersects(Point(400, 700))                                 # far village excluded
    assert g.geom_type == "Polygon" and len(g.interiors) == 0
    built = 100.0 * float((lc[150:400, 200:500] == 50).sum())                # the settlement's own built-up area (the far village excluded)
    assert built <= g.area < 1.25 * built                                    # hugs the built-up area: no box, no large filled cavities
    with pytest.raises(ValueError):
        PA.settlement_extent_from_raster(lc, T, centre_xy=(5500.0, 500.0), seed_radius_m=100.0)


def test_polygon_file_boundary_and_provenance(tmp_path):
    cache = REPO / "data/raw/_cache/gb_IND_ADM3.geojson"
    if not cache.exists():
        pytest.skip("geoBoundaries cache not available")
    adm3 = gpd.read_file(cache)
    m = adm3[adm3.shapeName == "Aswaraopeta"].geometry.iloc[0]
    c = m.representative_point()
    poly = gpd.GeoSeries([Point(c.x, c.y).buffer(0.01)], crs=4326)                      # a village-sized polygon well inside the mandal
    f = tmp_path / "b.geojson"
    poly.to_file(f, driver="GeoJSON")
    cfg = A.load_cfg("aswaraopeta")
    cfg["village"]["boundary_file"] = str(f)
    row = dict(name="Aswaraopeta", source="osm", source_id="relation/1", url="u", kind="k", geometry=poly.iloc[0], area_km2=1.2, share_in_mandal=1.0, verdict="plausible")
    prov = PA.write_pick(cfg, row, f, "test")
    assert json.loads(f.with_name("b.provenance.json").read_text())["sha256"] == prov["sha256"]
    cell, rec = A.boundary(cfg)
    assert 0.5 < cell.area / 1e6 < 6 and rec["share_inside_mandal"] > 0.99 and rec["provenance"]["source"] == "osm"
    adil = gpd.GeoSeries([box(78.5, 19.65, 78.55, 19.7)], crs=4326)                      # Adilabad, not in the Aswaraopeta mandal
    adil.to_file(f, driver="GeoJSON")
    f.with_name("b.provenance.json").unlink()
    with pytest.raises(ValueError, match="inside the Aswaraopeta mandal"):
        A.boundary(cfg)


def test_generic_scripts_take_a_village():
    e = importlib.util.spec_from_file_location("e2e", REPO / "scripts" / "run_village_end_to_end.py")
    E = importlib.util.module_from_spec(e)
    e.loader.exec_module(E)
    import argparse
    P = E.Paths(argparse.Namespace(village="aswaraopeta", work_dir=None))
    assert P.slug == "aswaraopeta" and P.mosaic.name == "aswaraopeta_esri_highres_mosaic_0p6m.tif" and P.out.name == "02_ASWARAOPETA_SEGMENTATION"
    P0 = E.Paths(argparse.Namespace(work_dir=None))
    assert P0.village == "adilabad_urban" and P0.mosaic.name == "adilabad_esri_highres_mosaic_0p6m.tif" and P0.out.name == "01_ADILABAD_SEGMENTATION"
