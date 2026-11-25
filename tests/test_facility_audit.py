"""Facility audit: classification into the five categories, duplicate merging, rooftop snapping, and the curated table read by the pipeline (all offline)."""
import importlib.util
from pathlib import Path

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Point, box

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("audit_facilities", REPO / "scripts" / "audit_facilities.py")
AF = importlib.util.module_from_spec(spec)
spec.loader.exec_module(AF)
CRS = "EPSG:32644"


@pytest.mark.parametrize("name,tags,tax,expect", [
    ("Zphs Alampur", {}, "", "School"), ("Govt Junior College", {"amenity": "college"}, "", "College"), ("Agriculture college aswaraopet", {}, "school", "College"),
    ("Area Hospital", {"amenity": "hospital"}, "", "Hospital"), ("PHC Damarakunta", {}, "", "Hospital"), ("Sub Centre, Damarakunta", {}, "", "Hospital"),
    ("Anganwadi Centre 3", {}, "", "Anganwadi"), ("Mandal Parishad Office", {}, "", "Government Office"), ("Alampur Police Station", {"amenity": "police"}, "", "Government Office"),
    ("Post office", {}, "post_office", "Government Office"), ("Montessori School", {}, "preschool", "School"),
    ("SC Welfare Hostel", {}, "", "Anganwadi")])
def test_categories(name, tags, tax, expect):
    assert AF.classify(name, tags, tax, "OSM")[0] == expect


@pytest.mark.parametrize("name,tags,tax", [
    ("Apollo Pharmacy", {"amenity": "pharmacy"}, ""), ("Sri Medical Hall", {}, ""), ("Vijaya Diagnostic Centre", {}, "laboratory_testing"), ("Ramana Coaching Centre", {}, "education"),
    ("State Bank of India", {}, "bank_or_credit_union"), ("Primary Agricultural Cooperative Credit Society", {}, ""), ("Jogulamba Temple", {}, "hindu_place_of_worship"),
    ("University Of Mirpurkhas", {}, "school"), ("Hotel Sai", {}, "hotel")])
def test_false_positives_are_removed_with_a_reason(name, tags, tax):
    cat, why, _ = AF.classify(name, tags, tax, "Overture")
    assert cat is None and why


def test_name_similarity_handles_spelling():
    assert AF.sim("Govt. Hospital Alampur", "Government Hospital, Alampur") >= 0.6
    assert AF.sim("Zphs Alampur", "ZP High School Alampur") >= 0.5
    assert AF.sim("Anganwadi 1", "") == 0.0


def area(fp_boxes, cell=box(0, 0, 1000, 1000)):
    fp = gpd.GeoDataFrame(geometry=[box(*b) for b in fp_boxes], crs=CRS)
    return dict(v="t", cell=cell, fp=fp, places=None, mosaic=Path("none"), cfg={"overture_release": "x"})


def recs(rows):
    return pd.DataFrame([dict(source=s, source_id=i, name=n, tags={}, taxonomy=t, lon=0, lat=0, confidence=0.8, status="open", is_area=False, _x=x, _y=y) for s, i, n, t, x, y in rows])


def test_duplicates_merge_and_outside_is_logged(monkeypatch):
    A = area([(100, 100, 130, 120)])
    monkeypatch.setattr(AF, "FROM_WGS", type("T", (), {"transform": staticmethod(lambda lon, lat: (lon, lat))})())
    df = pd.DataFrame([dict(source="OSM", source_id="n1", name="Zphs Alampur", tags={}, taxonomy="school", lon=110, lat=110, confidence=float("nan"), status="open", is_area=False),
                       dict(source="Overture", source_id="o1", name="ZP High School Alampur", tags={}, taxonomy="school", lon=125, lat=115, confidence=0.9, status="open", is_area=False),
                       dict(source="Overture", source_id="o2", name="Govt School Far", tags={}, taxonomy="school", lon=1500, lat=500, confidence=0.9, status="open", is_area=False),
                       dict(source="Overture", source_id="o3", name="Apollo Pharmacy", tags={}, taxonomy="pharmacy", lon=300, lat=300, confidence=0.9, status="open", is_area=False)])
    C, EX = AF.pass2(A, df, None, lambda *a: None)
    assert len(C) == 1 and C.category.iat[0] == "School" and set(C.sources.iat[0].split(";")) == {"OSM", "Overture"}
    reasons = " | ".join(EX.reason)
    assert "duplicate of" in reasons and "outside the study polygon" in reasons and "pharmacy" in reasons


def test_snapping_moves_the_pin_onto_the_building_and_drops_pins_in_fields(monkeypatch):
    A = area([(100, 100, 140, 130), (200, 100, 210, 106)])
    monkeypatch.setattr(AF, "TO_WGS", type("T", (), {"transform": staticmethod(lambda x, y: (x / 1e5, y / 1e5))})())
    C = pd.DataFrame([dict(cluster=1, name="Zphs", all_names="Zphs", category="School", subtype="school", lat=0, lon=0, x=150, y=115, sources="OSM", source_ids="OSM:1", n_records=1, overture_conf=float("nan")),
                      dict(cluster=2, name="Field pin", all_names="", category="School", subtype="school", lat=0, lon=0, x=600, y=600, sources="Overture", source_ids="Overture:2", n_records=1, overture_conf=0.9)])
    K, D = AF.pass3(A, C, lambda *a: None)
    assert len(K) == 1 and K.snapped_to_building.iat[0] and K.snap_distance_m.iat[0] == pytest.approx(10.0, abs=0.1)
    assert len(D) == 1 and "no building" in D.reason.iat[0]


def test_curated_table_feeds_the_pipeline(tmp_path, monkeypatch):
    from src.multivillage import facilities as FAC
    f = tmp_path / "zz_verified_facilities.csv"
    pd.DataFrame(dict(facility_id=["Z-SCH-001", "Z-COL-002"], name=["A School", "B College"], category=["School", "College"], lat=[15.88, 15.881], lon=[78.135, 78.136],
                      verification_sources=["OSM;Overture", "OSM"], confidence=["high", "medium"], snapped_to_building=[True, True])).to_csv(f, index=False)
    monkeypatch.setattr(FAC, "curated_path", lambda v: f)
    fp = gpd.GeoSeries([Point(0, 0).buffer(5)], crs=CRS)
    from pyproj import Transformer
    x, y = Transformer.from_crs(4326, CRS, always_xy=True).transform(78.135, 15.88)
    cell = Point(x, y).buffer(500)
    p = FAC.curated("zz", cell, gpd.GeoDataFrame(geometry=fp))
    assert list(p.facility_type) == ["school", "college"] and p.status.tolist() == ["VERIFIED_USED", "VERIFIED_USED"] and p.dataset.iat[0]
