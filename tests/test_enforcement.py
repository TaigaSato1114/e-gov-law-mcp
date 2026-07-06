#!/usr/bin/env python3
"""
Unit tests for src/enforcement.py — the pure施行タイムライン logic.

These are HTTP-free and do not import fastmcp, so they run standalone.
Design reference: .plan/[設計]施行タイムライン機能.md
"""

import sys
from datetime import date, datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import enforcement as enf  # noqa: E402


# --- parse_revision_id -----------------------------------------------------

def test_parse_revision_id_valid():
    r = enf.parse_revision_id("129AC0000000089_20290623_508AC0000000045")
    assert r["valid"] is True
    assert r["law_id"] == "129AC0000000089"
    assert r["enforcement_date"] == "2029-06-23"
    assert r["amendment_law_id"] == "508AC0000000045"


def test_parse_revision_id_malformed():
    assert enf.parse_revision_id("garbage")["valid"] is False
    assert enf.parse_revision_id("")["valid"] is False
    assert enf.parse_revision_id("a_b_c")["valid"] is False  # bad date
    # never raises
    assert enf.parse_revision_id(None)["valid"] is False


# --- derive_enforcement_status --------------------------------------------

ASOF = date(2026, 7, 6)


def test_derive_enforced_past():
    rev = {"current_revision_status": "CurrentEnforced",
           "amendment_enforcement_date": "2026-04-01"}
    d = enf.derive_enforcement_status(rev, ASOF)
    assert d["enforcement_status"] == "enforced"
    assert d["finalized"] is True


def test_derive_same_day_is_enforced():
    rev = {"current_revision_status": "CurrentEnforced",
           "amendment_enforcement_date": "2026-07-06"}
    d = enf.derive_enforcement_status(rev, ASOF)
    assert d["enforcement_status"] == "enforced"


def test_derive_unenforced_future():
    rev = {"current_revision_status": "UnEnforced",
           "amendment_enforcement_date": "2029-06-23"}
    d = enf.derive_enforcement_status(rev, ASOF)
    assert d["enforcement_status"] == "unenforced"
    assert d["days_to_enforcement"] == (date(2029, 6, 23) - ASOF).days
    assert d["finalized"] is True


def test_derive_scheduled_uncertain_comment_only():
    rev = {"current_revision_status": "UnEnforced",
           "amendment_enforcement_date": None,
           "amendment_enforcement_comment": "公布の日から起算して三年を超えない範囲内において政令で定める日"}
    d = enf.derive_enforcement_status(rev, ASOF)
    assert d["enforcement_status"] == "scheduled_uncertain"
    assert d["finalized"] is False
    assert d["reason"] == "comment_only"


def test_derive_scheduled_only():
    rev = {"current_revision_status": "UnEnforced",
           "amendment_enforcement_date": None,
           "amendment_scheduled_enforcement_date": "2026-12-01"}
    d = enf.derive_enforcement_status(rev, ASOF)
    assert d["reason"] == "scheduled_only"


def test_derive_repealed():
    rev = {"current_revision_status": "Repeal",
           "amendment_enforcement_date": "2000-01-01"}
    d = enf.derive_enforcement_status(rev, ASOF)
    assert d["enforcement_status"] == "repealed"
    assert d["finalized"] is True


# --- sort_timeline ---------------------------------------------------------

def test_sort_timeline_desc_uncertain_last():
    entries = [
        {"amendment_enforcement_date": "2020-04-01", "law_revision_id": "L_20200401_A"},
        {"amendment_enforcement_date": None, "law_revision_id": "L_00000000_B"},
        {"amendment_enforcement_date": "2029-06-23", "law_revision_id": "L_20290623_C"},
    ]
    out = enf.sort_timeline(entries, order="desc")
    assert out[0]["amendment_enforcement_date"] == "2029-06-23"
    assert out[1]["amendment_enforcement_date"] == "2020-04-01"
    assert out[2]["amendment_enforcement_date"] is None  # uncertain trails


def test_sort_timeline_asc_uncertain_still_last():
    entries = [
        {"amendment_enforcement_date": "2029-06-23", "law_revision_id": "L_20290623_C"},
        {"amendment_enforcement_date": None, "law_revision_id": "L_00000000_B"},
        {"amendment_enforcement_date": "2020-04-01", "law_revision_id": "L_20200401_A"},
    ]
    out = enf.sort_timeline(entries, order="asc")
    assert out[0]["amendment_enforcement_date"] == "2020-04-01"
    assert out[1]["amendment_enforcement_date"] == "2029-06-23"
    assert out[2]["amendment_enforcement_date"] is None


def test_sort_same_day_by_revision_id_desc():
    entries = [
        {"amendment_enforcement_date": "2026-04-01", "law_revision_id": "L_20260401_A"},
        {"amendment_enforcement_date": "2026-04-01", "law_revision_id": "L_20260401_B"},
    ]
    out = enf.sort_timeline(entries, order="desc")
    assert out[0]["law_revision_id"] == "L_20260401_B"


# --- resolve_revision_asof -------------------------------------------------

REVISIONS = [
    {"law_revision_id": "L_20200401_A", "amendment_enforcement_date": "2020-04-01",
     "current_revision_status": "PreviousEnforced"},
    {"law_revision_id": "L_20260401_B", "amendment_enforcement_date": "2026-04-01",
     "current_revision_status": "CurrentEnforced"},
    {"law_revision_id": "L_20290623_C", "amendment_enforcement_date": "2029-06-23",
     "current_revision_status": "UnEnforced"},
    {"law_revision_id": "L_00000000_D", "amendment_enforcement_date": None,
     "current_revision_status": "UnEnforced",
     "amendment_enforcement_comment": "政令で定める日"},
]


def test_asof_picks_latest_on_or_before():
    r = enf.resolve_revision_asof(REVISIONS, date(2026, 7, 6))
    assert r["law_revision_id"] == "L_20260401_B"


def test_asof_future_selects_unenforced_as_effective():
    # State-independent: an entry that is UnEnforced *today* is the in-force
    # version at a future asof past its enforcement date.
    r = enf.resolve_revision_asof(REVISIONS, date(2030, 1, 1))
    assert r["law_revision_id"] == "L_20290623_C"


def test_asof_before_enactment_returns_none():
    assert enf.resolve_revision_asof(REVISIONS, date(2019, 1, 1)) is None


def test_asof_ignores_uncertain_dates():
    # The comment-only revision (no date) never becomes the resolved version.
    r = enf.resolve_revision_asof(REVISIONS, date(2100, 1, 1))
    assert r["law_revision_id"] == "L_20290623_C"


def test_asof_repealed_returns_no_effective_text():
    revs = [
        {"law_revision_id": "L_20200401_A", "amendment_enforcement_date": "2020-04-01",
         "current_revision_status": "PreviousEnforced"},
        {"law_revision_id": "L_20250401_R", "amendment_enforcement_date": "2025-04-01",
         "current_revision_status": "Repeal", "repeal_date": "2025-04-01"},
    ]
    r = enf.resolve_revision_asof(revs, date(2026, 1, 1))
    assert r["no_effective_text"] is True
    assert r["repeal"]["law_revision_id"] == "L_20250401_R"


# --- dynamic_ttl -----------------------------------------------------------

def _now(y, m, d, hh=0):
    tz = enf.JST or timezone(timedelta(hours=9))
    return datetime(y, m, d, hh, 0, tzinfo=tz)


def test_ttl_immutable_statuses_30d():
    assert enf.dynamic_ttl("PreviousEnforced", date(2020, 1, 1), True) == 30 * 86400
    assert enf.dynamic_ttl("CurrentEnforced", date(2020, 1, 1), True) == 30 * 86400
    assert enf.dynamic_ttl("Repeal", date(2020, 1, 1), True) == 30 * 86400


def test_ttl_comment_only_12h():
    assert enf.dynamic_ttl("UnEnforced", None, False) == 12 * 3600


def test_ttl_unenforced_finalized_shrinks_toward_enforcement():
    now = _now(2026, 7, 6, 0)
    # enforcement tomorrow -> capped at 6h (min of remaining and 6h)
    ttl = enf.dynamic_ttl("UnEnforced", date(2026, 7, 7), True, now=now)
    assert ttl == 6 * 3600
    # enforcement long past target already -> floor 300s
    ttl2 = enf.dynamic_ttl("UnEnforced", date(2026, 7, 5), True, now=now)
    assert ttl2 == 300


def test_status_ttl_takes_minimum():
    revs = [
        {"current_revision_status": "PreviousEnforced",
         "amendment_enforcement_date": "2020-01-01"},
        {"current_revision_status": "UnEnforced",
         "amendment_enforcement_date": None},  # comment-only 12h
    ]
    assert enf.status_ttl_for_revisions(revs) == 12 * 3600


# --- cache & keys ----------------------------------------------------------

def test_ttl_cache_get_put_and_expiry():
    c = enf.TTLCache(max_size=2)
    c.put("k", {"v": 1}, ttl=100)
    got = c.get("k")
    assert got is not None
    value, age = got
    assert value == {"v": 1}
    assert age >= 0
    # expired
    c.put("k2", 5, ttl=0)
    assert c.get("k2") is None


def test_ttl_cache_lru_eviction():
    c = enf.TTLCache(max_size=2)
    c.put("a", 1, 100)
    c.put("b", 2, 100)
    c.get("a")            # touch a so b is LRU
    c.put("c", 3, 100)    # evicts b
    assert c.get("b") is None
    assert c.get("a") is not None
    assert c.get("c") is not None


def test_canonical_query_sorted_and_joined():
    q = enf.canonical_query({"b": "2", "a": ["x", "y"], "empty": "", "none": None})
    assert q == "a=x,y&b=2"


def test_revisions_cache_key_includes_version():
    key = enf.revisions_cache_key("129AC0000000089",
                                  {"current_revision_status": "UnEnforced"})
    assert key.startswith("law_revisions:129AC0000000089?")
    assert f"v={enf.ALGO_VERSION}" in key


def test_count_statuses():
    entries = [
        {"derived": {"enforcement_status": "enforced"}},
        {"derived": {"enforcement_status": "enforced"}},
        {"derived": {"enforcement_status": "unenforced"}},
        {"derived": {"enforcement_status": "scheduled_uncertain"}},
    ]
    counts = enf.count_statuses(entries)
    assert counts == {"enforced": 2, "unenforced": 1,
                      "scheduled_uncertain": 1, "repealed": 0}
