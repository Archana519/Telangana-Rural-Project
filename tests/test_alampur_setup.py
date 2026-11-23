"""Offline tests for the Alampur (4th study area) set-up: config, folders, generic scripts, boundary provenance (once locked)."""
import json
from pathlib import Path

import pytest

from src.multivillage import acquire as A, run as R

REPO = Path(__file__).resolve().parents[1]


def test_config_and_folders():
    c = A.load_cfg("alampur")["village"]
    assert c["id"] == "alampur" and c["district"] == "Jogulamba" and c["adm3_name"] == "Alampur" and c["boundary_method"] == "polygon_file"
    assert R.FOLDERS["alampur"] == c["folder"] == "03_ALAMPUR" and c["bundle_folder"] == "04_ALAMPUR" and c["work_slug"] == "alampur"
    ref = A.load_cfg("aswaraopeta")["village"]
    for k in ("min_house_area_m2", "min_conf", "min_dist_to_road_m"):                # same target rule as the other settlements
        assert c[k] == ref[k]
    assert A.load_cfg("alampur")["res_m"] == 10.0 and A.load_cfg("alampur")["planner"]["building_mult"] == 4.0


def test_generic_scripts_accept_alampur():
    for s in ("run_village_end_to_end.py", "make_village_map_series.py"):
        txt = (REPO / "scripts" / s).read_text(encoding="utf-8")
        assert 'glob("*.yaml")' in txt                                              # --village choices come from the config folder, so alampur is accepted without code changes


def test_locked_boundary_has_provenance():
    pf = REPO / "configs/multivillage/villages/alampur_boundary.provenance.json"
    if not pf.exists():
        pytest.skip("boundary not locked yet")
    p = json.loads(pf.read_text(encoding="utf-8"))
    assert p["study_area_name"] and p["boundary_type"] and p["area_km2"] > 0 and "edge_continuity" in p
    assert (REPO / "configs/multivillage/villages/alampur_boundary.geojson").exists()
