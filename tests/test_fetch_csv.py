"""Tests for CDR fetch helpers — xlsx talk time and date filter."""

from __future__ import annotations

import datetime as dt
from datetime import date

import pytest

import _bootstrap  # noqa: F401

import importlib

fetch = importlib.import_module("callqa.ingestion.fetch")


def test_talk_time_seconds_from_time():
    assert fetch.talk_time_seconds(dt.time(0, 2, 53)) == 173
    assert fetch.talk_time_seconds(dt.time(0, 0, 32)) == 32
    assert fetch.talk_time_seconds("00:02:53") == 173


def test_talk_time_seconds_empty():
    assert fetch.talk_time_seconds(None) == 0
    assert fetch.talk_time_seconds("") == 0


def test_format_talk_time():
    assert fetch.format_talk_time(dt.time(0, 2, 53)) == "00:02:53"


def test_parse_call_date_formats():
    assert fetch.parse_call_date("15-06-2026") == date(2026, 6, 15)
    assert fetch.parse_call_date("2026-06-01") == date(2026, 6, 1)


def test_row_in_cohort_dates():
    cfg = {"cohort_date_from": "2026-06-01", "cohort_date_to": "2026-06-15"}
    assert fetch.row_in_cohort_dates({"Call Date": "2026-06-10"}, cfg)
    assert not fetch.row_in_cohort_dates({"Call Date": "2026-05-31"}, cfg)
    assert not fetch.row_in_cohort_dates({"Call Date": "2026-06-16"}, cfg)


def test_normalize_xlsx_row():
    row = {
        "Call ID": 22081548171783100,
        "Call Date": dt.datetime(2026, 6, 15),
        "Talk Time": dt.time(0, 2, 53),
        "Agent": "Test Agent",
        "Location": "Hyderabad",
        "Recording URL": "https://example.com/a.mp3",
    }
    out = fetch.normalize_xlsx_row(row)
    assert out["Call Date"] == "2026-06-15"
    assert out["Talk Time"] == "00:02:53"
    assert out["Location"] == "Hyderabad"
    assert fetch.talk_time_seconds(out["Talk Time"]) == 173


def test_last_arrow_agent():
    flow = "Queue -> Agent Dials (Afshan Sultana) -> Agent Dials (Obaidullah)"
    assert fetch.last_arrow_agent(flow) == "Obaidullah"


def test_resolve_final_agent_prefers_cleaned_column():
    row = {
        "Agent (cleaned)": "Akula Varsha",
        "Call Flow": "Queue -> Agent Dials (Someone Else)",
        "Agent": "Someone Else",
    }
    assert fetch.resolve_final_agent(row, "Agent (cleaned)") == "Akula Varsha"


def test_resolve_final_agent_falls_back_to_last_arrow():
    row = {
        "Call Flow": "Queue -> Agent Dials (Afshan Sultana) -> Agent Dials (Parigi Janardhan)",
        "Agent": "Afshan Sultana",
    }
    assert fetch.resolve_final_agent(row, None) == "Parigi Janardhan"
