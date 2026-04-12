"""
data_bridge.py
──────────────
TTL cache + mock/live toggle.
Stores normalized match dicts from currentMatches so scorecard
lookup never needs a second API call on basic tier.
"""

import time
import logging
from config import MOCK_MODE, CACHE_TTL
import mock_data
import cricket_api

log = logging.getLogger(__name__)

# ── In-memory store ────────────────────────────────────────────────
_cache:       dict[str, tuple[float, object]] = {}
_match_store: dict[str, dict] = {}   # match_id → normalized match dict


def _cache_get(key: str):
    entry = _cache.get(key)
    if entry:
        ts, val = entry
        if time.time() - ts < CACHE_TTL:
            return val
    return None


def _cache_set(key: str, val):
    _cache[key] = (time.time(), val)


# ── Public API ─────────────────────────────────────────────────────

async def get_live_matches() -> list[dict]:
    cached = _cache_get("live_matches")
    if cached is not None:
        return cached

    if MOCK_MODE:
        result = mock_data.get_mock_matches()
    else:
        result = await cricket_api.fetch_live_matches()
        if not result:
            log.warning("Live API empty — using mock matches.")
            result = mock_data.get_mock_matches()

    # Index by match_id for fast scorecard lookup
    for m in result:
        mid = m.get("match_id")
        if mid:
            _match_store[mid] = m

    _cache_set("live_matches", result)
    return result


async def get_scorecard(match_id: str) -> dict | None:
    key = f"sc_{match_id}"
    cached = _cache_get(key)
    if cached is not None:
        return cached

    if MOCK_MODE or match_id.startswith("mock_"):
        result = mock_data.get_mock_scorecard(match_id)
    else:
        # 1st choice: match already stored from /live call
        result = _match_store.get(match_id)

        # 2nd choice: try dedicated scorecard endpoint (premium feature)
        if not result or not result.get("innings1"):
            detailed = await cricket_api.fetch_scorecard(match_id)
            if detailed and detailed.get("innings1"):
                result = detailed

        # 3rd choice: re-fetch live matches (refreshes store)
        if not result:
            await get_live_matches()
            result = _match_store.get(match_id)

        if not result:
            log.warning("No data for %s — mock fallback.", match_id)
            result = mock_data.get_mock_scorecard("mock_mi_rcb_20260412")

    _cache_set(key, result)
    return result


async def get_last_5_overs(match_id: str) -> list:
    key = f"last5_{match_id}"
    cached = _cache_get(key)
    if cached is not None:
        return cached

    sc = await get_scorecard(match_id)
    result = sc.get("last_5_overs", []) if sc else []
    _cache_set(key, result)
    return result


def get_primary_match_id() -> str | None:
    """Return match_id of the first match in store (most relevant live match)."""
    if _match_store:
        return next(iter(_match_store))
    return None


def clear_cache():
    _cache.clear()
    _match_store.clear()
