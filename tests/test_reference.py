"""Reference parity tests mirroring ``tests/golden/upstream/test.js`` (specs.md §12.1).

The upstream Jest suite mutates one shared instance; the port uses a **fresh
``PrayTime`` per test** (re-applying the base setup) to avoid order dependence
(specs.md §12.1 note). Expected values are the exact upstream assertions.
"""

from __future__ import annotations

from praytime import PrayTime

LATITUDE = 43.4643
LONGITUDE = -80.5204
DATE = [2025, 2, 21]
TIMEZONE = "America/Toronto"


def _base() -> PrayTime:
    """Fresh instance with the reference Water, ON base setup (specs.md §12.1)."""
    return (
        PrayTime()
        .method("ISNA")
        .location([LATITUDE, LONGITUDE])
        .timezone(TIMEZONE)
    )


def test_prayer_times() -> None:
    times = _base().get_times(DATE)
    assert times["fajr"] == "05:52"
    assert times["dhuhr"] == "12:36"
    assert times["asr"] == "15:32"
    assert times["maghrib"] == "18:02"


def test_time_formats() -> None:
    assert _base().format("x").get_times(DATE)["asr"] == 1740169920000
    assert _base().format("X").get_times(DATE)["asr"] == 1740169920
    assert _base().format("12h").get_times(DATE)["asr"] == "3:32 PM"
    assert _base().format("12H").get_times(DATE)["asr"] == "3:32"
    assert _base().format("24h").get_times(DATE)["asr"] == "15:32"


def test_timezones() -> None:
    assert _base().utc_offset(-4.5).get_times(DATE)["fajr"] == "06:22"
    assert _base().utc_offset(-300).get_times(DATE)["fajr"] == "05:52"


def test_rounding_method() -> None:
    assert _base().round("down").get_times(DATE)["asr"] == "15:32"
    assert _base().round("up").get_times(DATE)["asr"] == "15:33"
    assert _base().round("nearest").get_times(DATE)["asr"] == "15:32"


def test_adjust_method() -> None:
    times = _base().adjust({"fajr": 19.7, "dhuhr": "11 min"}).get_times(DATE)
    assert times["fajr"] == "05:26"
    assert times["dhuhr"] == "12:47"


def test_tuning_method() -> None:
    times = _base().tune({"asr": 11, "maghrib": 4.5}).get_times(DATE)
    assert times["asr"] == "15:43"
    assert times["maghrib"] == "18:07"
