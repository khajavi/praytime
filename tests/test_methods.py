"""Unit tests for method resolution (specs.md §4.2, §10.15).

Effective merged parameters were captured from the upstream JS library
(``new PrayTime(name).settings``) under Node v24 on 2026-10-16.
"""

from __future__ import annotations

import pytest

from praytime import constants as C
from praytime.methods import get_methods, resolve_method

# Effective {fajr, isha, maghrib, midnight} for each method after the
# defaults-then-method merge, captured from Node.
MERGED_CASES = {
    "MWL": {"fajr": 18, "isha": 17, "maghrib": "1 min", "midnight": "Standard"},
    "ISNA": {"fajr": 15, "isha": 15, "maghrib": "1 min", "midnight": "Standard"},
    "Tehran": {"fajr": 17.7, "isha": 14, "maghrib": 4.5, "midnight": "Jafari"},
    "Jafari": {"fajr": 16, "isha": 14, "maghrib": 4, "midnight": "Jafari"},
    "Makkah": {"fajr": 18.5, "isha": "90 min", "maghrib": "1 min", "midnight": "Standard"},
    "Egypt": {"fajr": 19.5, "isha": 17.5, "maghrib": "1 min", "midnight": "Standard"},
    "Karachi": {"fajr": 18, "isha": 18, "maghrib": "1 min", "midnight": "Standard"},
    "France": {"fajr": 12, "isha": 12, "maghrib": "1 min", "midnight": "Standard"},
    "Russia": {"fajr": 16, "isha": 15, "maghrib": "1 min", "midnight": "Standard"},
    "Malaysia": {"fajr": 20, "isha": 18, "maghrib": "1 min", "midnight": "Standard"},
    "Singapore": {"fajr": 20, "isha": 18, "maghrib": "1 min", "midnight": "Standard"},
}


@pytest.mark.parametrize("name,expected", MERGED_CASES.items())
def test_resolve_method(name: str, expected: dict) -> None:
    assert resolve_method(C.METHODS, name) == expected


def test_resolve_method_unknown_is_defaults_only() -> None:
    assert resolve_method(C.METHODS, "Nope") == {
        "isha": 14,
        "maghrib": "1 min",
        "midnight": "Standard",
    }


def test_resolve_method_returns_new_dict() -> None:
    resolved = resolve_method(C.METHODS, "MWL")
    assert resolved is not C.METHODS["defaults"] is not C.METHODS["MWL"]
    resolved["fajr"] = 999
    assert C.METHODS["MWL"]["fajr"] == 18
    assert C.METHODS["defaults"] == {"isha": 14, "maghrib": "1 min", "midnight": "Standard"}


def test_resolve_method_custom_method_inherits_defaults() -> None:
    methods = dict(C.METHODS)
    methods["Algeria"] = {"fajr": 18, "isha": 17}
    assert resolve_method(methods, "Algeria") == {
        "isha": 17,
        "maghrib": "1 min",
        "midnight": "Standard",
        "fajr": 18,
    }


def test_get_methods_is_a_deep_copy() -> None:
    methods = get_methods()
    assert methods == C.METHODS
    assert methods is not C.METHODS

    methods["MWL"]["fajr"] = 0
    methods["Algeria"] = {"fajr": 1, "isha": 2}
    assert C.METHODS["MWL"]["fajr"] == 18
    assert "Algeria" not in C.METHODS


def test_get_methods_nested_dicts_independent() -> None:
    a = get_methods()
    b = get_methods()
    a["Makkah"]["isha"] = "changed"
    assert b["Makkah"]["isha"] == "90 min"
    assert C.METHODS["Makkah"]["isha"] == "90 min"
