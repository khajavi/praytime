"""Public API tests: chainability, key order, custom methods, isolation (specs.md §3)."""

from __future__ import annotations

from praytime import PrayTime

KEY_ORDER = ["fajr", "sunrise", "dhuhr", "asr", "sunset", "maghrib", "isha", "midnight"]


def test_setters_are_chainable() -> None:
    pt = PrayTime()
    assert pt.method("ISNA") is pt
    assert pt.adjust({"fajr": 18}) is pt
    assert pt.location([43.4643, -80.5204]) is pt
    assert pt.timezone("America/Toronto") is pt
    assert pt.tune({"asr": 1}) is pt
    assert pt.round("nearest") is pt
    assert pt.format("24h") is pt
    assert pt.set({"iterations": 1}) is pt
    assert pt.utc_offset(-5) is pt


def test_setters_chain_in_one_expression() -> None:
    pt = PrayTime()
    result = (
        pt.method("MWL")
        .location([43.4643, -80.5204])
        .timezone("America/Toronto")
        .format("24h")
        .round("nearest")
        .utc_offset(0)
    )
    assert result is pt


def test_returned_dict_key_order() -> None:
    times = PrayTime().method("ISNA").location([43.4643, -80.5204]).times([2025, 2, 21])
    assert list(times.keys()) == KEY_ORDER


def test_custom_method() -> None:
    pt = PrayTime()
    pt.methods["Algeria"] = {"fajr": 18, "isha": 17}
    assert pt.method("Algeria") is pt
    assert pt.settings["fajr"] == 18
    assert pt.settings["isha"] == 17
    # Inherited from ``defaults`` (applied first).
    assert pt.settings["maghrib"] == "1 min"
    assert pt.settings["midnight"] == "Standard"


def test_unknown_method_applies_only_defaults_no_raise() -> None:
    # Constructing directly with an unknown method applies only ``defaults``
    # (parity with ``new PrayTime('Nope')`` → ``settings.fajr === undefined``).
    pt = PrayTime("DoesNotExist")
    assert pt.settings["isha"] == 14
    assert pt.settings["maghrib"] == "1 min"
    assert pt.settings["midnight"] == "Standard"
    assert "fajr" not in pt.settings
    assert pt.method("StillMissing") is pt


def test_unknown_method_times_do_not_raise() -> None:
    pt = PrayTime("Nope").location([43.4643, -80.5204]).utc_offset(0)
    times = pt.times([2025, 2, 21])
    assert list(times.keys()) == KEY_ORDER


def test_set_method_returns_none() -> None:
    pt = PrayTime()
    assert pt.set_method("ISNA") is None
    assert pt.settings["fajr"] == 15


def test_instances_have_isolated_methods() -> None:
    a = PrayTime()
    b = PrayTime()
    a.methods["MWL"]["fajr"] = 0
    a.methods["Algeria"] = {"fajr": 18, "isha": 17}
    assert b.methods["MWL"]["fajr"] == 18
    assert "Algeria" not in b.methods


def test_instances_have_isolated_settings() -> None:
    a = PrayTime().method("ISNA")
    b = PrayTime().method("ISNA")
    a.set({"format": "12h"})
    a.settings["location"][0] = 99
    assert b.settings["format"] == "24h"
    assert b.settings["location"][0] == 0


def test_labels_are_exposed() -> None:
    pt = PrayTime()
    assert pt.labels == [
        "Fajr",
        "Sunrise",
        "Dhuhr",
        "Asr",
        "Sunset",
        "Maghrib",
        "Isha",
        "Midnight",
    ]
