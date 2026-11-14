"""Tests for the provenance audit tool (fast parts only; --rerun / --redownload are exercised by running the audit itself)."""
import numpy as np

from src.evaluation import provenance_audit as pa


def test_check_pass_fail_and_tolerance():
    assert pa.check("x", "c", 5.0, 5.04, "s", 0.05)["status"] == "PASS"
    assert pa.check("x", "c", 5.0, 5.2, "s", 0.05)["status"] == "FAIL"
    assert pa.check("x", "c", (1, 2), (1, 2), "s")["status"] == "PASS"


def test_loveda_metrics_recompute_from_embedded_confusion_matrix():
    r = {c["id"]: c for c in pa.loveda_checks()}
    assert all(c["status"] == "PASS" for c in r.values())
    assert abs(r["LV-acc"]["actual"] - 71.3) < 0.05                # the epoch-4 log says 0.7134


def test_level1_claims_match_recorded_tables():
    bad = [c for c in pa.level1_checks() if c["status"] == "FAIL"]
    assert not bad, bad


def test_levels_checks_recompute_derived_numbers():
    bad = [c for c in pa.levels_checks() if c["status"] == "FAIL"]
    assert not bad, bad


def test_sha256_is_stable(tmp_path):
    f = tmp_path / "a.bin"
    f.write_bytes(b"abc")
    assert pa.sha256(f) == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


def test_num_equal_handles_nested_and_nan():
    assert pa._num_equal({"a": [1.0, float("nan")]}, {"a": [1.0 + 1e-12, float("nan")]})
    assert not pa._num_equal({"a": 1.0}, {"a": 1.1})
