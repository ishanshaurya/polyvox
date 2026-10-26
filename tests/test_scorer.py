"""Tests for score_to_stars band edges and weighted_overall."""

import _bootstrap  # noqa: F401

from callqa.analysis.scorer import score_to_stars, weighted_overall

CFG = {
    "rating_bands": {5: 85, 4: 70, 3: 55, 2: 40, 1: 0},
    "kpis": [{"name": "a", "weight": 3}, {"name": "b", "weight": 1}],
}


def test_stars_at_band_edges():
    assert score_to_stars(85, CFG) == 5
    assert score_to_stars(84.9, CFG) == 4
    assert score_to_stars(70, CFG) == 4
    assert score_to_stars(55, CFG) == 3
    assert score_to_stars(40, CFG) == 2
    assert score_to_stars(39.9, CFG) == 1
    assert score_to_stars(0, CFG) == 1


def test_weighted_overall_uses_weights():
    assert weighted_overall({"a": 100, "b": 0}, CFG) == 75.0


def test_weighted_overall_skips_missing_kpi():
    assert weighted_overall({"a": 80, "b": None}, CFG) == 80.0


def test_weighted_overall_all_missing():
    assert weighted_overall({"a": None, "b": ""}, CFG) is None
