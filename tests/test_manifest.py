"""Tests for manifest batch counting."""

from __future__ import annotations

import _bootstrap  # noqa: F401

from callqa.state import manifest


def test_max_batch_counts_partial_last_batch():
    calls = [{"stem": f"s{i}", "batch": i // 7 + 1} for i in range(100)]
    assert manifest.max_batch({"calls": calls}) == 15


def test_max_batch_empty_manifest():
    assert manifest.max_batch({"calls": []}) == 0
    assert manifest.max_batch({}) == 0
