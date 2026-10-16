"""Unit tests for Phase 5: rounding, rendering, and format dispatch.

Expected values were captured by running the **exact upstream JS library**
(``tests/golden/upstream/praytime.js``) under Node v24 on 2026-10-16. The
reference timestamp is the Waterloo, ON Asr value ``1740169920000``
(``Date.UTC(2025, 1, 21)`` + Asr), rendered in ``America/Toronto``.

Do not re-derive these from Python — they are the parity oracle (specs.md §9,
§8.13).
"""

from __future__ import annotations

import math

import pytest

from praytime.formatting import (
    format_time,
    is_min,
    js_round,
    parse_value,
    round_time,
    time_to_string,
)

# Asr reference timestamp (ms), from tests/test.js / specs.md §12.1.
ASR_MS = 1740169920000


# ---------------------------------------------------------------------------
# js_round (specs.md §8.13) — JS Math.round is half-up
# ---------------------------------------------------------------------------

JS_ROUND_CASES = [
    (0.5, 1),
    (1.5, 2),
    (2.5, 3),
    (-0.5, 0),
    (-1.5, -1),
    (0.4999, 0),
    (2.49, 2),
    (29999999.5, 30000000),
]


@pytest.mark.parametrize("x,expected", JS_ROUND_CASES)
def test_js_round_half_up(x: float, expected: int) -> None:
    assert js_round(x) == expected


def test_js_round_not_bankers() -> None:
    # Python's builtin round(2.5) == 2; js_round must be 3.
    assert js_round(2.5) == 3
    assert round(2.5) == 2


# ---------------------------------------------------------------------------
# round_time (specs.md §8.13) — captured from JS pt.roundTime(ts)
# ---------------------------------------------------------------------------

ROUND_TIME_CASES = [
    (90000, "up", 120000),
    (90000, "down", 60000),
    (90000, "nearest", 120000),
    (90000, "none", 90000),
    (90000, "bogus", 90000),
    (150000, "up", 180000),
    (150000, "down", 120000),
    (150000, "nearest", 180000),
    (150000, "none", 150000),
    (89999, "up", 120000),
    (89999, "down", 60000),
    (89999, "nearest", 60000),
    (120001, "up", 180000),
    (120001, "down", 120000),
    (120001, "nearest", 120000),
    (60000, "up", 60000),
    (60000, "down", 60000),
    (60000, "nearest", 60000),
    (60000, "none", 60000),
]


@pytest.mark.parametrize("timestamp,rounding,expected", ROUND_TIME_CASES)
def test_round_time(timestamp: float, rounding: str, expected: float) -> None:
    assert round_time(timestamp, rounding) == expected


def test_round_time_unknown_returns_unchanged() -> None:
    assert round_time(123456.0, "whatever") == 123456.0


# ---------------------------------------------------------------------------
# round_time non-finite parity (JS Math.round(NaN) === NaN)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("rounding", ["up", "down", "nearest", "none", "bogus"])
def test_round_time_nan_returns_nan(rounding: str) -> None:
    result = round_time(float("nan"), rounding)
    assert isinstance(result, float) and math.isnan(result)


@pytest.mark.parametrize("rounding", ["up", "down", "nearest", "none", "bogus"])
@pytest.mark.parametrize("value", [float("inf"), float("-inf")])
def test_round_time_inf_returns_inf(value: float, rounding: str) -> None:
    assert round_time(value, rounding) == value


# ---------------------------------------------------------------------------
# format_time dispatch (specs.md §9.1) — captured from JS pt.formatTime(ASR_MS)
# ---------------------------------------------------------------------------

def _settings(fmt: object, utc_offset: object = "auto", timezone: str = "America/Toronto") -> dict:
    return {"format": fmt, "utcOffset": utc_offset, "timezone": timezone}


FORMAT_TIME_CASES = [
    ("24h", "15:32"),
    ("12h", "3:32 PM"),
    ("12H", "3:32"),
    ("x", 1740169920000),
    ("X", 1740169920),
]


@pytest.mark.parametrize("fmt,expected", FORMAT_TIME_CASES)
def test_format_time(fmt: str, expected: object) -> None:
    assert format_time(ASR_MS, _settings(fmt)) == expected


def test_format_time_nan_is_invalid() -> None:
    assert format_time(float("nan"), _settings("24h")) == "-----"


def test_format_time_callable_receives_ms() -> None:
    captured = {}

    def fmt(timestamp: object) -> str:
        captured["value"] = timestamp
        return f"<{timestamp}>"

    result = format_time(ASR_MS, _settings(fmt))
    assert result == "<1740169920000>"
    assert captured["value"] == 1740169920000


def test_format_time_callable_return_type_passthrough() -> None:
    assert format_time(ASR_MS, _settings(lambda t: [t])) == [1740169920000]


# ---------------------------------------------------------------------------
# time_to_string (specs.md §9.1–§9.3) — captured from JS pt.timeToString(...)
# ---------------------------------------------------------------------------

def tts(timestamp: float, fmt: str, utc_offset: object, timezone: str) -> str:
    return time_to_string(timestamp, fmt, {"utcOffset": utc_offset, "timezone": timezone})


TIME_TO_STRING_CASES = [
    # Numeric utcOffset (-300 min) rendered in UTC: JS "15:32".
    (ASR_MS, "24h", -300, "UTC", "15:32"),
    (ASR_MS, "12h", -300, "UTC", "3:32 PM"),
    (ASR_MS, "12H", -300, "UTC", "3:32"),
    # 'auto' offset rendered in UTC: JS "20:32" (ASR is 20:32 UTC).
    (ASR_MS, "24h", "auto", "UTC", "20:32"),
    (ASR_MS, "12h", "auto", "UTC", "8:32 PM"),
    (ASR_MS, "12H", "auto", "UTC", "8:32"),
    # 'auto' offset rendered in America/Toronto: JS "15:32".
    (ASR_MS, "24h", "auto", "America/Toronto", "15:32"),
    (ASR_MS, "12h", "auto", "America/Toronto", "3:32 PM"),
    (ASR_MS, "12H", "auto", "America/Toronto", "3:32"),
    # Midnight / noon hour edge cases (UTC 2025-02-21T00:00 and T12:00).
    (1740096000000, "24h", "auto", "UTC", "00:00"),
    (1740096000000, "12h", "auto", "UTC", "12:00 AM"),
    (1740096000000, "12H", "auto", "UTC", "12:00"),
    (1740139200000, "24h", "auto", "UTC", "12:00"),
    (1740139200000, "12h", "auto", "UTC", "12:00 PM"),
    (1740139200000, "12H", "auto", "UTC", "12:00"),
]


@pytest.mark.parametrize("timestamp,fmt,utc_offset,timezone,expected", TIME_TO_STRING_CASES)
def test_time_to_string(
    timestamp: float, fmt: str, utc_offset: object, timezone: str, expected: str
) -> None:
    assert tts(timestamp, fmt, utc_offset, timezone) == expected


def test_time_to_string_zoneinfo_fallback_to_utc() -> None:
    # A missing tz database entry must degrade to UTC rather than raise.
    assert tts(ASR_MS, "24h", "auto", "No/Such_Zone") == "20:32"


# ---------------------------------------------------------------------------
# parse_value / is_min sanity (kept from Phase 1; specs.md §9.4)
# ---------------------------------------------------------------------------

def test_parse_value_and_is_min_still_present() -> None:
    assert parse_value("90 min") == 90.0
    assert parse_value("Standard") == 0.0
    assert is_min("90 min") is True
    assert is_min("Standard") is False
    assert not math.isnan(parse_value(18))
