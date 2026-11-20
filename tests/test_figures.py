"""Tests for the Contribution 3 figure script: the committed figures exist, are 300 dpi, and Figure B can be regenerated from the sweep CSV."""
from pathlib import Path

import pytest
from PIL import Image

from src.evaluation import plot_hierarchy_figures as pf

REPO = Path(__file__).resolve().parents[1]
NAMES = list(pf.FIGURES)


@pytest.mark.parametrize("name", NAMES)
def test_committed_figures_exist_in_both_places_at_300_dpi(name):
    for d in (REPO / "docs" / "results" / "hierarchy_real_run" / "figures",):
        im = Image.open(d / f"{name}.png")
        assert abs(im.info["dpi"][0] - 300) < 1 and im.size[0] >= 2000


def test_figure_b_regenerates_from_the_sweep_csv(tmp_path):
    fig = pf.figure_b(tmp_path)
    out = tmp_path / "b.png"
    fig.savefig(out, dpi=100)
    assert out.stat().st_size > 10_000
    texts = " ".join(t.get_text() for ax in fig.axes for t in ax.texts)
    assert "89.0%" in texts and "5.2%" in texts                          # the knee annotation is computed from the CSV, not typed


def test_level1_omission_figure_is_300_dpi_in_both_places_and_values_come_from_the_csv():
    from src.evaluation import plot_level1_omission as p1
    for d in (REPO / "docs" / "results" / "hierarchy_real_run" / "figures",):
        im = Image.open(d / f"{p1.NAME}.png")
        assert abs(im.info["dpi"][0] - 300) < 1 and im.size[0] >= 2000
    d, base, base_per = p1.load()
    r = d.set_index("key")
    assert base == 5069.0 and abs(base_per - 31.1) < 1e-9
    assert round(r.loc["omit merged blobs", "dL"], 1) == -29.4 and int(r.loc["omit merged blobs", "unserved"]) == 62
    assert round(r.loc["omit 10%", "dL"], 1) == -7.6 and round(r.loc["add 20%", "dL"], 1) == 15.8
    fig = p1.figure()
    assert fig.axes[0].get_legend() is None and fig.axes[1].get_legend() is None        # direct labels only: no legend to overlap anything
