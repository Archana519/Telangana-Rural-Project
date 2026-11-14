"""Tests for the Contribution 3 deliverables package (Stage-B-style layout) and for leaving Stage B untouched."""
import subprocess
from pathlib import Path

import openpyxl
import pandas as pd
import pytest
from PIL import Image

from src.evaluation import provenance_audit as pa

REPO = Path(__file__).resolve().parents[1]
D = REPO / "DELIVERABLES_CONTRIBUTION_3_HIERARCHICAL_ROUTING"


def test_required_files_exist_and_manifest_is_complete_and_correct():
    res = {c["id"]: c for c in pa.deliverables_checks()}
    for k in ("DV-required", "DV-manifest", "DV-manifest-complete", "DV-dpi", "DV-readme-numbers"):
        assert res[k]["status"] == "PASS", res[k]


def test_stage_b_is_untouched():
    if not (REPO / ".git").exists():
        pytest.skip("no git metadata")
    tree = subprocess.run(["git", "rev-parse", "HEAD:DELIVERABLES_DAMARAKUNTA_STAGE_B"], cwd=REPO, capture_output=True, text=True).stdout.strip()
    assert tree == pa.STAGE_B_TREE
    assert subprocess.run(["git", "status", "--porcelain", "--", "DELIVERABLES_DAMARAKUNTA_STAGE_B"], cwd=REPO, capture_output=True, text=True).stdout.strip() == ""


def test_maps_and_charts_are_high_resolution_300_dpi():
    for f in list((D / "02_FINAL_MAPS").glob("*.png")) + list((D / "03_RESULTS_TABLES" / "CHARTS").glob("*.png")):
        im = Image.open(f)
        assert abs(im.info["dpi"][0] - 300) < 1 and im.size[0] >= 2000, f


def test_tables_match_results_and_excel_has_all_sheets():
    t2 = pd.read_csv(D / "03_RESULTS_TABLES" / "T2_mu_penalty_sensitivity.csv")
    sweep = pd.read_csv(REPO / "docs" / "results" / "U02_penalty_sweep_gp.csv")
    assert list(t2.mu_penalty) == list(sweep.mu) == [1.0, 2.0, 4.0, 8.0, 20.0, 100.0]
    k = t2[t2.mu_penalty == 4.0].iloc[0]
    assert round(k.exposure_reduction_vs_mu1_pct, 1) == 89.0 and round(k.length_increase_vs_mu1_pct, 1) == 5.2
    t3 = pd.read_csv(D / "03_RESULTS_TABLES" / "T3_levels3_4_scalability.csv")
    assert set(t3.evidence) == {"PROXY nodes"} and round(t3.new_construction_km.iloc[1], 1) == 14.7
    wb = openpyxl.load_workbook(D / "03_RESULTS_TABLES" / "contribution3_summary_tables.xlsx")
    assert wb.sheetnames == ["README", "T1_L2_metrics", "T1b_L2_override", "T2_mu_sweep", "T3_L3_L4_scalability", "T4_omission"]


def test_proxy_status_is_stated_in_the_readme_and_limitations():
    for f in ("00_README_SUMMARY.md", "05_LIMITATIONS_AND_OPEN_ISSUES/LIMITATIONS.md"):
        txt = (D / f).read_text(encoding="utf-8")
        assert "PROXY" in txt and "not planning" in txt.lower() or "no planning conclusion" in txt.lower()
