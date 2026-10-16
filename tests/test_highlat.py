"""Unit tests for high-latitude adjustment (specs.md §6, §10.5).

Expected results were captured from the upstream JS library's
``adjustHighLats`` / ``adjustTime`` under Node v24 on 2026-10-16 using the
synthetic times dict the spec requests. They are the parity oracle.
"""

from __future__ import annotations

import math

import pytest

from praytime.formatting import parse_value
from praytime.highlat import adjust_high_lats, adjust_time

NAN = float("nan")


def synthetic_times() -> dict:
    """Fresh synthetic times dict (mutated in place by adjust_high_lats)."""
    return {
        "fajr": NAN,
        "sunrise": 6.0,
        "dhuhr": 12.0,
        "asr": 13.0,
        "sunset": 18.0,
        "maghrib": 18.0,
        "isha": NAN,
        "midnight": 24.0,
    }


def settings(rule: str, fajr: object = 18, isha: object = 17, maghrib: object = "1 min") -> dict:
    return {"highLats": rule, "fajr": fajr, "isha": isha, "maghrib": maghrib}


def approx(value: float) -> float:
    return pytest.approx(value, rel=1e-9, abs=1e-9)


# ---------------------------------------------------------------------------
# 'None' branch: untouched times, prior_adjusted returned (specs.md §10.5)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("prior", [False, True, None])
def test_none_returns_prior_adjusted_and_touches_nothing(prior: object) -> None:
    times = synthetic_times()
    original = dict(times)
    ret = adjust_high_lats(times, settings("None"), parse_value, prior)
    assert ret is prior
    assert times == original


def test_none_default_prior_is_none() -> None:
    assert adjust_high_lats(synthetic_times(), settings("None"), parse_value) is None


# ---------------------------------------------------------------------------
# Full NightMiddle case — captured from JS adjustHighLats
# ---------------------------------------------------------------------------

def test_night_middle_full_case() -> None:
    times = synthetic_times()
    ret = adjust_high_lats(times, settings("NightMiddle"), parse_value, False)
    assert ret is True
    assert times["fajr"] == approx(0.0)
    assert times["isha"] == approx(24.0)
    assert times["maghrib"] == approx(18.0)
    # Untouched keys keep their values.
    assert times["sunrise"] == 6.0
    assert times["sunset"] == 18.0
    assert times["midnight"] == 24.0


def test_one_seventh_full_case() -> None:
    times = synthetic_times()
    ret = adjust_high_lats(times, settings("OneSeventh"), parse_value, False)
    assert ret is True
    assert times["fajr"] == approx(6.0 - 12.0 / 7.0)  # 4.285714285714286
    assert times["isha"] == approx(18.0 + 12.0 / 7.0)  # 19.714285714285715
    assert times["maghrib"] == approx(18.0)


def test_angle_based_full_case() -> None:
    times = synthetic_times()
    ret = adjust_high_lats(times, settings("AngleBased"), parse_value, False)
    assert ret is True
    assert times["fajr"] == approx(2.4)   # 6 - (18/60)*12
    assert times["isha"] == approx(21.4)  # 18 + (17/60)*12
    assert times["maghrib"] == approx(18.0)  # (1/60)*12 = 0.2 not exceeded


def test_angle_based_makkah_isha_90min() -> None:
    times = synthetic_times()
    ret = adjust_high_lats(
        times, settings("AngleBased", fajr=18.5, isha="90 min"), parse_value, False
    )
    assert ret is True
    assert times["fajr"] == approx(2.3)   # 6 - (18.5/60)*12
    assert times["isha"] == approx(36.0)  # 18 + 1.5*12
    assert times["maghrib"] == approx(18.0)


# ---------------------------------------------------------------------------
# Non-clamping and boundary behavior (strict '>')
# ---------------------------------------------------------------------------

def test_night_middle_non_clamping_keeps_values_and_adjusted_false() -> None:
    times = {
        "fajr": 5.5,
        "sunrise": 6.0,
        "dhuhr": 12.0,
        "asr": 13.0,
        "sunset": 18.0,
        "maghrib": 18.0,
        "isha": 19.0,
        "midnight": 24.0,
    }
    ret = adjust_high_lats(times, settings("NightMiddle"), parse_value, False)
    assert ret is False
    assert times["fajr"] == 5.5
    assert times["isha"] == 19.0
    assert times["maghrib"] == 18.0


def test_exact_boundary_is_not_clamped() -> None:
    times = {
        "fajr": 0.0,  # timeDiff == portion == 6, strictly not >
        "sunrise": 6.0,
        "dhuhr": 12.0,
        "asr": 13.0,
        "sunset": 18.0,
        "maghrib": 18.0,
        "isha": 24.0,
        "midnight": 24.0,
    }
    ret = adjust_high_lats(times, settings("NightMiddle"), parse_value, False)
    assert ret is False
    assert times["fajr"] == 0.0
    assert times["isha"] == 24.0


def test_overshoot_boundary_is_clamped() -> None:
    times = {
        "fajr": -1.0,  # timeDiff == 7 > 6
        "sunrise": 6.0,
        "dhuhr": 12.0,
        "asr": 13.0,
        "sunset": 18.0,
        "maghrib": 18.0,
        "isha": 24.0,
        "midnight": 24.0,
    }
    ret = adjust_high_lats(times, settings("NightMiddle"), parse_value, False)
    assert ret is True
    assert times["fajr"] == 0.0


def test_night_length_and_portion_from_other_sunrise_sunset() -> None:
    # night = 24 + 7 - 17 = 14, NightMiddle portion = 7.
    times = {
        "fajr": NAN,
        "sunrise": 7.0,
        "dhuhr": 12.0,
        "asr": 13.0,
        "sunset": 17.0,
        "maghrib": 18.0,
        "isha": NAN,
        "midnight": 24.0,
    }
    ret = adjust_high_lats(times, settings("NightMiddle"), parse_value, False)
    assert ret is True
    assert times["fajr"] == approx(0.0)   # 7 - 7
    assert times["isha"] == approx(24.0)  # 17 + 7


def test_angle_based_night14_maghrib_and_isha() -> None:
    times = {
        "fajr": NAN,
        "sunrise": 7.0,
        "dhuhr": 12.0,
        "asr": 13.0,
        "sunset": 17.0,
        "maghrib": NAN,
        "isha": NAN,
        "midnight": 24.0,
    }
    ret = adjust_high_lats(
        times, settings("AngleBased", fajr=18.5, isha="90 min"), parse_value, False
    )
    assert ret is True
    assert times["fajr"] == approx(2.6833333333333336)   # 7 - (18.5/60)*14
    assert times["maghrib"] == approx(17.233333333333334)  # 17 + (1/60)*14
    assert times["isha"] == approx(38.0)                  # 17 + 1.5*14


# ---------------------------------------------------------------------------
# adjust_time direct (captured from JS adjustTime)
# ---------------------------------------------------------------------------

def test_adjust_time_nan_is_clamped_and_flags() -> None:
    assert adjust_time(NAN, 6, 18, 12, -1, settings("NightMiddle"), parse_value, False) == (
        approx(0.0),
        True,
    )


def test_adjust_time_no_change() -> None:
    assert adjust_time(6, 6, 18, 12, -1, settings("NightMiddle"), parse_value, False) == (
        6,
        False,
    )


def test_adjust_time_overshoot_clamped() -> None:
    time, adjusted = adjust_time(-1, 6, 18, 12, -1, settings("NightMiddle"), parse_value, False)
    assert time == approx(0.0)
    assert adjusted is True


def test_adjust_time_angle_based_90min() -> None:
    time, adjusted = adjust_time(
        NAN, 18, "90 min", 12, 1, settings("AngleBased"), parse_value, False
    )
    assert time == approx(36.0)
    assert adjusted is True


def test_adjust_time_angle_based_uses_raw_angle_string() -> None:
    seen = []

    def value_fn(angle: object) -> float:
        seen.append(angle)
        return parse_value(angle)

    time, adjusted = adjust_time(
        NAN, 18, "90 min", 12, 1, settings("AngleBased"), value_fn, False
    )
    assert seen == ["90 min"]
    assert time == approx(36.0)  # (1/60) * 90 * 12 = 18; 18 + 18
    assert adjusted is True


def test_adjust_time_preserves_adjusted_when_no_clamp() -> None:
    time, adjusted = adjust_time(6, 6, 18, 12, -1, settings("NightMiddle"), parse_value, True)
    assert time == 6
    assert adjusted is True


def test_adjust_high_lats_nan_never_left_unclamped() -> None:
    for rule in ("NightMiddle", "OneSeventh", "AngleBased"):
        times = synthetic_times()
        adjust_high_lats(times, settings(rule), parse_value, False)
        assert not math.isnan(times["fajr"])
        assert not math.isnan(times["isha"])
