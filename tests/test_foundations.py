"""Unit tests for Phase 1 foundations: constants and degree trigonometry."""

from __future__ import annotations

import math

import pytest

from praytime import METHODS, __version__
from praytime import constants as C
from praytime import trig


# ---------------------------------------------------------------------------
# Version / exports
# ---------------------------------------------------------------------------


def test_version_and_exports() -> None:
    assert __version__ == "0.1.0"
    assert METHODS["MWL"] == {"fajr": 18, "isha": 17}


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


def test_methods_keys() -> None:
    expected = {
        "MWL",
        "ISNA",
        "Egypt",
        "Makkah",
        "Karachi",
        "Tehran",
        "Jafari",
        "France",
        "Russia",
        "Malaysia",
        "Singapore",
        "defaults",
    }
    assert set(METHODS.keys()) == expected


def test_method_table_values() -> None:
    assert METHODS["MWL"] == {"fajr": 18, "isha": 17}
    assert METHODS["ISNA"] == {"fajr": 15, "isha": 15}
    assert METHODS["Egypt"] == {"fajr": 19.5, "isha": 17.5}
    assert METHODS["Makkah"]["isha"] == "90 min"
    assert METHODS["Makkah"]["fajr"] == 18.5
    assert METHODS["Karachi"] == {"fajr": 18, "isha": 18}
    assert METHODS["Tehran"] == {"fajr": 17.7, "maghrib": 4.5, "midnight": "Jafari"}
    assert METHODS["Jafari"] == {"fajr": 16, "maghrib": 4, "midnight": "Jafari"}
    assert METHODS["France"] == {"fajr": 12, "isha": 12}
    assert METHODS["Russia"] == {"fajr": 16, "isha": 15}
    assert METHODS["defaults"] == {
        "isha": 14,
        "maghrib": "1 min",
        "midnight": "Standard",
    }


@pytest.mark.parametrize("name", ["Malaysia", "Singapore"])
def test_malaysia_singapore(name: str) -> None:
    assert METHODS[name]["fajr"] == 20
    assert METHODS[name]["isha"] == 18


@pytest.mark.parametrize("name", ["Tehran", "Jafari"])
def test_jafari_midnight(name: str) -> None:
    assert METHODS[name]["midnight"] == "Jafari"


def test_labels() -> None:
    assert C.LABELS == [
        "Fajr",
        "Sunrise",
        "Dhuhr",
        "Asr",
        "Sunset",
        "Maghrib",
        "Isha",
        "Midnight",
    ]


def test_numeric_constants() -> None:
    assert C.HORIZON == 0.833
    assert C.J2000_OFFSET_DAYS == 2451545.0 - 2440587.5
    assert C.J2000_OFFSET_DAYS == 10957.5
    assert C.MS_PER_DAY == 86_400_000
    assert C.MS_PER_HOUR == 3_600_000
    assert C.MS_PER_MINUTE == 60_000
    assert C.MEAN_ANOMALY_BASE == 357.529
    assert C.MEAN_ANOMALY_RATE == 0.98560028
    assert C.MEAN_LONGITUDE_BASE == 280.459
    assert C.MEAN_LONGITUDE_RATE == 0.98564736
    assert C.EQ_CENTER_1 == 1.915
    assert C.EQ_CENTER_2 == 0.020
    assert C.OBLIQUITY_J2000 == 23.439
    assert C.OBLIQUITY_RATE == 0.00000036
    assert C.SHADOW_STANDARD == 1
    assert C.SHADOW_HANAFI == 2
    assert C.HL_NIGHT_MIDDLE == 1 / 2
    assert C.HL_ONE_SEVENTH == 1 / 7
    assert C.JAFARI_SEED_HOUR == 29
    assert C.NOON_OFFSET == 12
    assert C.HOURS_PER_DAY == 24
    assert C.DEG_PER_HOUR == 15
    assert C.INVALID_TIME == "-----"


def test_seed_times() -> None:
    assert C.SEED_TIMES == {
        "fajr": 5,
        "sunrise": 6,
        "dhuhr": 12,
        "asr": 13,
        "sunset": 18,
        "maghrib": 18,
        "isha": 18,
        "midnight": 24,
    }


def test_defaults_template() -> None:
    assert C.DEFAULTS["dhuhr"] == "0 min"
    assert C.DEFAULTS["asr"] == "Standard"
    assert C.DEFAULTS["highLats"] == "NightMiddle"
    assert C.DEFAULTS["tune"] == {}
    assert C.DEFAULTS["format"] == "24h"
    assert C.DEFAULTS["rounding"] == "nearest"
    assert C.DEFAULTS["utcOffset"] == "auto"
    assert C.DEFAULTS["iterations"] == 1


def test_default_settings_is_fresh_and_complete() -> None:
    a = C.default_settings()
    b = C.default_settings()
    assert a is not b
    assert a["tune"] is not b["tune"]
    assert "timezone" in a and isinstance(a["timezone"], str)
    assert "location" in a and len(a["location"]) == 2
    assert a["location"][0] == 0
    # Mutating one must not leak into the static template.
    a["tune"]["x"] = 1
    assert C.DEFAULTS["tune"] == {}


# ---------------------------------------------------------------------------
# Trigonometry
# ---------------------------------------------------------------------------


def test_mod() -> None:
    assert trig.mod(-1, 24) == 23
    assert trig.mod(25, 24) == 1
    assert trig.mod(24, 24) == 0
    assert trig.mod(0, 24) == 0


def test_sin_basic() -> None:
    assert trig.sin(30) == pytest.approx(0.5)
    assert trig.sin(18) == math.sin(math.radians(18))


def test_roundtrip() -> None:
    assert trig.rtd(trig.dtr(37)) == pytest.approx(37)


def test_acot() -> None:
    assert trig.acot(1) == pytest.approx(45)


def test_atan2() -> None:
    assert trig.atan2(1, 1) == pytest.approx(45)


def test_asin_out_of_domain_is_nan() -> None:
    assert math.isnan(trig.asin(2))


def test_acos_out_of_domain_is_nan() -> None:
    assert math.isnan(trig.acos(-2))


def test_asin_valid() -> None:
    assert trig.asin(1) == pytest.approx(90)


def test_non_numeric_input_is_nan() -> None:
    assert math.isnan(trig.sin("1 min"))
    assert math.isnan(trig.cos("1 min"))
    assert math.isnan(trig.tan("1 min"))
    assert math.isnan(trig.acot("1 min"))


def test_nan_propagates() -> None:
    nan = float("nan")
    assert math.isnan(trig.sin(nan))
    assert math.isnan(trig.cos(nan))
    assert math.isnan(trig.tan(nan))
    assert math.isnan(trig.asin(nan))
    assert math.isnan(trig.acos(nan))
    assert math.isnan(trig.atan(nan))
    assert math.isnan(trig.acot(nan))
    assert math.isnan(trig.atan2(nan, 1))
    assert math.isnan(trig.dtr(nan))
    assert math.isnan(trig.rtd(nan))


def test_acot_zero_matches_js_infinity() -> None:
    assert trig.acot(0) == pytest.approx(90)
