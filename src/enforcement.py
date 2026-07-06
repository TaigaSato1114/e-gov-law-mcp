#!/usr/bin/env python3
"""
Enforcement timeline logic for the e-Gov Law MCP Server.

Pure, side-effect-free helpers for the "when was a law enforced" (施行) feature,
plus a per-entry-TTL cache. Kept HTTP-free so it can be unit-tested in isolation.

Design reference: .plan/[設計]施行タイムライン機能.md
"""

from __future__ import annotations

import threading
import time as _time
from collections import OrderedDict
from datetime import date, datetime, time
from typing import Any, Optional

try:
    from zoneinfo import ZoneInfo
    JST = ZoneInfo("Asia/Tokyo")
except Exception:  # pragma: no cover - zoneinfo always present on 3.9+
    JST = None

# Bump this when the derivation logic changes so cached entries are invalidated.
ALGO_VERSION = "1"

# current_revision_status enum (confirmed 4 values from API v2)
STATUS_CURRENT = "CurrentEnforced"
STATUS_UNENFORCED = "UnEnforced"
STATUS_PREVIOUS = "PreviousEnforced"
STATUS_REPEAL = "Repeal"

# enforcement_status enum (derived, client-facing)
ES_ENFORCED = "enforced"
ES_UNENFORCED = "unenforced"
ES_SCHEDULED_UNCERTAIN = "scheduled_uncertain"
ES_REPEALED = "repealed"

# Fields copied verbatim from an API revision object into a timeline entry.
REVISION_FIELDS = (
    "law_revision_id",
    "amendment_enforcement_date",
    "amendment_scheduled_enforcement_date",
    "amendment_enforcement_comment",
    "amendment_promulgate_date",
    "amendment_type",
    "mission",
    "current_revision_status",
    "amendment_law_id",
    "amendment_law_num",
    "amendment_law_title",
    "repeal_status",
    "repeal_date",
)


def today_jst() -> date:
    """Current date in JST (Asia/Tokyo), the fixed basis for enforcement checks."""
    if JST is not None:
        return datetime.now(JST).date()
    return datetime.now().date()


def parse_iso_date(value: Optional[str]) -> Optional[date]:
    """Parse a YYYY-MM-DD string, tolerating None/empty and bad input."""
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except (ValueError, TypeError):
        return None


def parse_revision_id(law_revision_id: str) -> dict[str, Any]:
    """Split a law_revision_id ``{law_id}_{YYYYMMDD}_{amendment_law_id}``.

    Returns the parts plus a ``valid`` flag; never raises so callers can attach
    a warning note on malformed ids instead of failing the whole request.
    """
    result: dict[str, Any] = {
        "law_id": None,
        "enforcement_date": None,
        "amendment_law_id": None,
        "valid": False,
    }
    if not law_revision_id or not isinstance(law_revision_id, str):
        return result
    parts = law_revision_id.split("_")
    if len(parts) != 3:
        return result
    law_id, date_str, amendment_law_id = parts
    result["law_id"] = law_id
    result["amendment_law_id"] = amendment_law_id
    if len(date_str) == 8 and date_str.isdigit():
        iso = f"{date_str[0:4]}-{date_str[4:6]}-{date_str[6:8]}"
        parsed = parse_iso_date(iso)
        if parsed is not None:
            result["enforcement_date"] = iso
            result["valid"] = True
    return result


def derive_enforcement_status(rev: dict, asof: date) -> dict[str, Any]:
    """Derive ``enforcement_status`` / ``days_to_enforcement`` / ``finalized``.

    Rules (design §4.1):
      - Repeal                              -> repealed (finalized)
      - no enforcement date (comment only)  -> scheduled_uncertain (NOT finalized)
      - enforcement_date <= asof            -> enforced (same-day counts as enforced)
      - else                                -> unenforced (finalized, days ahead)
    """
    status = rev.get("current_revision_status")
    if status == STATUS_REPEAL:
        return {
            "enforcement_status": ES_REPEALED,
            "days_to_enforcement": None,
            "finalized": True,
        }

    ed = parse_iso_date(rev.get("amendment_enforcement_date"))
    if ed is None:
        # Enforcement date not fixed (scheduled date and/or comment only).
        has_scheduled = bool(rev.get("amendment_scheduled_enforcement_date"))
        reason = "scheduled_only" if has_scheduled else "comment_only"
        return {
            "enforcement_status": ES_SCHEDULED_UNCERTAIN,
            "days_to_enforcement": None,
            "finalized": False,
            "reason": reason,
        }

    if ed <= asof:
        return {
            "enforcement_status": ES_ENFORCED,
            "days_to_enforcement": None,
            "finalized": True,
        }
    return {
        "enforcement_status": ES_UNENFORCED,
        "days_to_enforcement": (ed - asof).days,
        "finalized": True,
    }


def build_timeline_entry(rev: dict, asof: date) -> dict[str, Any]:
    """Project an API revision into the standard timeline entry schema."""
    entry = {field: rev.get(field) for field in REVISION_FIELDS}
    entry["derived"] = derive_enforcement_status(rev, asof)
    return entry


def _entry_sort_key(entry: dict) -> tuple:
    """Sort key: enforcement_date desc, then law_revision_id desc.

    Entries with no enforcement date (uncertain) sort to the very end.
    """
    ed = entry.get("amendment_enforcement_date") or ""
    rid = entry.get("law_revision_id") or ""
    # Empty date -> "" which is the smallest string; combined with the caller
    # placing uncertain entries last, we return a tuple that orders correctly.
    return (ed, rid)


def sort_timeline(entries: list[dict], order: str = "desc") -> list[dict]:
    """Sort timeline entries by enforcement date, keeping uncertain ones last."""
    dated = [e for e in entries if e.get("amendment_enforcement_date")]
    undated = [e for e in entries if not e.get("amendment_enforcement_date")]
    dated.sort(key=_entry_sort_key, reverse=(order != "asc"))
    # Uncertain (undated) entries always trail, regardless of order direction.
    return dated + undated


def count_statuses(entries: list[dict]) -> dict[str, int]:
    """Tally derived enforcement_status values across timeline entries."""
    counts = {
        ES_ENFORCED: 0,
        ES_UNENFORCED: 0,
        ES_SCHEDULED_UNCERTAIN: 0,
        ES_REPEALED: 0,
    }
    for e in entries:
        status = e.get("derived", {}).get("enforcement_status")
        if status in counts:
            counts[status] += 1
    return counts


def resolve_revision_asof(revisions: list[dict], asof: date) -> Optional[dict]:
    """Resolve which revision is in force at ``asof`` (design §4.3).

    IMPORTANT: state-independent date filter (works for future asof too) and
    never uses ``current_revision_info`` (which is "today"-based). Returns:
      - {"no_effective_text": True, "last_enforced": .., "repeal": ..} if repealed
      - the chosen revision dict, or None if the law did not yet exist at asof.
    """
    candidates = []
    for r in revisions:
        ed = parse_iso_date(r.get("amendment_enforcement_date"))
        if ed is not None and ed <= asof:
            candidates.append(r)

    if not candidates:
        return None

    def latest(revs: list[dict]) -> dict:
        return max(
            revs,
            key=lambda r: (r.get("amendment_enforcement_date") or "",
                           r.get("law_revision_id") or ""),
        )

    # Repeal effective at asof -> no effective text.
    repealed = []
    for r in candidates:
        if r.get("current_revision_status") == STATUS_REPEAL:
            rd = parse_iso_date(r.get("repeal_date"))
            if rd is not None and rd <= asof:
                repealed.append(r)
    if repealed:
        return {
            "no_effective_text": True,
            "last_enforced": latest(candidates),
            "repeal": latest(repealed),
        }

    return latest(candidates)


def dynamic_ttl(rev_status: Optional[str],
                enforcement_date: Optional[date],
                finalized: bool,
                now: Optional[datetime] = None) -> int:
    """Compute a cache TTL (seconds) for a set of revisions (design §6.2).

    - Immutable-ish (Previous/Current/Repeal): 30 days
    - UnEnforced, comment-only (not finalized): 12 hours
    - UnEnforced, finalized: shrink toward the enforcement day's 03:00 JST
      so the un-enforced -> enforced flip is picked up promptly. No cron needed.
    """
    thirty_days = 30 * 86400
    if rev_status in (STATUS_PREVIOUS, STATUS_CURRENT, STATUS_REPEAL):
        return thirty_days
    if rev_status == STATUS_UNENFORCED:
        if not finalized:
            return 12 * 3600
        if enforcement_date is not None:
            now = now or (datetime.now(JST) if JST else datetime.now())
            target = datetime.combine(enforcement_date, time(3, 0), tzinfo=now.tzinfo)
            remaining = int((target - now).total_seconds())
            return max(300, min(6 * 3600, remaining))
        return 6 * 3600
    return 3600


def status_ttl_for_revisions(revisions: list[dict],
                             now: Optional[datetime] = None) -> int:
    """Pick the shortest applicable TTL for a collection of revisions.

    A collection is only as fresh as its most volatile member (an UnEnforced
    entry about to flip), so we take the minimum TTL across entries.
    """
    if not revisions:
        return 3600
    ttls = []
    for r in revisions:
        status = r.get("current_revision_status")
        ed = parse_iso_date(r.get("amendment_enforcement_date"))
        finalized = ed is not None
        ttls.append(dynamic_ttl(status, ed, finalized, now=now))
    return min(ttls)


class TTLCache:
    """Thread-safe LRU cache supporting a per-entry TTL.

    Unlike the fixed-TTL LRUCache in mcp_server, each ``put`` may specify its
    own TTL (seconds), which the enforcement caches need for the dynamic-TTL
    strategy. ``get`` returns ``(value, age_seconds)`` or ``None``.
    """

    def __init__(self, max_size: int = 500):
        self.max_size = max_size
        self._data: OrderedDict[str, tuple[Any, float, float]] = OrderedDict()
        self._lock = threading.RLock()

    def get(self, key: str) -> Optional[tuple[Any, int]]:
        with self._lock:
            item = self._data.get(key)
            if item is None:
                return None
            value, stored_at, ttl = item
            age = _time.time() - stored_at
            if age > ttl:
                del self._data[key]
                return None
            self._data.move_to_end(key)
            return value, int(age)

    def put(self, key: str, value: Any, ttl: int) -> None:
        with self._lock:
            if key in self._data:
                self._data[key] = (value, _time.time(), ttl)
                self._data.move_to_end(key)
                return
            if len(self._data) >= self.max_size:
                self._data.popitem(last=False)
            self._data[key] = (value, _time.time(), ttl)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()

    def size(self) -> int:
        with self._lock:
            return len(self._data)


def canonical_query(params: dict) -> str:
    """Deterministic query string for cache keys (sorted, comma-joined lists)."""
    parts = []
    for key in sorted(params):
        value = params[key]
        if value is None or value == "":
            continue
        if isinstance(value, (list, tuple)):
            value = ",".join(str(v) for v in value)
        parts.append(f"{key}={value}")
    return "&".join(parts)


def revisions_cache_key(law_id_or_num: str, params: dict) -> str:
    """Cache key for a /law_revisions request (design §6.3)."""
    return f"law_revisions:{law_id_or_num}?{canonical_query(params)}&v={ALGO_VERSION}"
