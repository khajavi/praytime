"""Date-input normalization tests (specs.md §3.3, §10.1, §10.3)."""

from __future__ import annotations

import datetime as _dt
import json
import shutil
import subprocess

import pytest

from praytime import PrayTime

# 2025-02-21T20:32:00Z — UTC date 2025-02-21, host-local date on a UTC+ zone
# differs (e.g. Asia/Tehran → 2025-02-22).
MS_TIMESTAMP = 1740169920000


def _pt() -> PrayTime:
    return PrayTime().method("ISNA").location([43.4643, -80.5204]).utc_offset(0)


def _node_local_date(ms: int) -> tuple:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not available for the cross-check")
    script = (
        f"const d=new Date({ms});"
        "console.log(JSON.stringify([d.getFullYear(),d.getMonth()+1,d.getDate()]));"
    )
    out = subprocess.check_output([node, "-e", script], text=True)
    return tuple(json.loads(out))


# ---------------------------------------------------------------------------
# No-arg / zero → today; numeric < 1000 → day offset
# ---------------------------------------------------------------------------


def test_times_default_and_zero_are_today() -> None:
    today = _dt.date.today()
    expected = _pt().times([today.year, today.month, today.day])
    assert _pt().times() == expected
    assert _pt().times(0) == expected


def test_times_day_offset_is_local_now_plus_days() -> None:
    target = (_dt.datetime.now() + _dt.timedelta(days=7)).date()
    expected = _pt().times([target.year, target.month, target.day])
    assert _pt().times(7) == expected


def test_times_negative_day_offset_in_the_past() -> None:
    target = (_dt.datetime.now() + _dt.timedelta(days=-3)).date()
    expected = _pt().times([target.year, target.month, target.day])
    assert _pt().times(-3) == expected


# ---------------------------------------------------------------------------
# Numeric >= 1000 → Unix milliseconds, host-local calendar date
# ---------------------------------------------------------------------------


def test_ms_timestamp_uses_host_local_calendar_date() -> None:
    expected_date = _node_local_date(MS_TIMESTAMP)
    expected = _pt().times(list(expected_date))
    assert _pt().times(MS_TIMESTAMP) == expected
    # Sanity: this timestamp's UTC date differs on a UTC+ host, so a UTC-based
    # implementation would not match the Node-reported local date.
    assert _pt().times(MS_TIMESTAMP) == _pt().times(list(_node_local_date(MS_TIMESTAMP)))


# ---------------------------------------------------------------------------
# date / datetime inputs
# ---------------------------------------------------------------------------


def test_datetime_date_input() -> None:
    result = _pt().times(_dt.date(2025, 2, 21))
    assert result == _pt().times([2025, 2, 21])


def test_datetime_datetime_discards_time() -> None:
    result = _pt().times(_dt.datetime(2025, 2, 21, 23, 59, 59))
    assert result == _pt().times([2025, 2, 21])
    assert result == _pt().times(_dt.datetime(2025, 2, 21, 0, 0, 0))


# ---------------------------------------------------------------------------
# tuple / list inputs (1-based month)
# ---------------------------------------------------------------------------


def test_tuple_and_list_are_equivalent() -> None:
    assert _pt().times((2025, 2, 21)) == _pt().times([2025, 2, 21])


def test_month_is_one_based() -> None:
    # [2025, 2, 21] is 21 Feb 2025, not 21 Jan 2025.
    assert _pt().times([2025, 2, 21]) == _pt().times(_dt.date(2025, 2, 21))
    assert _pt().times([2025, 2, 21]) != _pt().times(_dt.date(2025, 1, 21))


# ---------------------------------------------------------------------------
# Invalid inputs
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad", [(2025, 2), (2025, 2, 21, 0), [2025], [2025, 2, 21, 1, 1]])
def test_wrong_tuple_length_raises_value_error(bad: object) -> None:
    with pytest.raises(ValueError):
        _pt().times(bad)  # type: ignore[arg-type]


@pytest.mark.parametrize("bad", [[2025, 13, 1], [2025, 0, 1], [2025, 2, 30], [2025, 2, 0]])
def test_out_of_range_month_or_day_raises_value_error(bad: list) -> None:
    with pytest.raises(ValueError):
        _pt().times(bad)


def test_wrong_type_raises_type_error() -> None:
    with pytest.raises(TypeError):
        _pt().times("2025-02-21")  # type: ignore[arg-type]
