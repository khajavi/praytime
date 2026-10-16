"""Unit tests for Phase 2: the pure astronomical core and interval parsing.

Every expected value below was captured by running the **exact upstream JS
library** (``tests/golden/upstream/praytime.js``) under Node v24 on
2026-10-16, for Waterloo, ON ``lat=43.4643, lng=-80.5204``, date
``[2025, 2, 21]`` (``utcTime = Date.UTC(2025, 1, 21)``). The JS-captured
numbers are asserted with ``pytest.approx(rel=1e-9, abs=1e-9)`` (specs.md
§12.3). Do not re-derive these from Python — they are the parity oracle.
"""

from __future__ import annotations

import math

import pytest

from praytime import astro
from praytime.formatting import is_min, parse_value

LAT = 43.4643
LNG = -80.5204
UTC_MS = 1740096000000  # Date.UTC(2025, 1, 21)

APPROX = dict(rel=1e-9, abs=1e-9)


# ---------------------------------------------------------------------------
# julian_offset
# ---------------------------------------------------------------------------

JULIAN_OFFSET_CASES = [
    (5, 9182.932001111112),
    (6, 9182.973667777778),
    (12, 9183.223667777778),
    (13, 9183.265334444444),
    (18, 9183.473667777778),
]


@pytest.mark.parametrize("time,expected", JULIAN_OFFSET_CASES)
def test_julian_offset(time: int, expected: float) -> None:
    assert astro.julian_offset(UTC_MS, time, LNG) == pytest.approx(expected, **APPROX)


# ---------------------------------------------------------------------------
# sun_position
# ---------------------------------------------------------------------------

SUN_POSITION_CASES = [
    (5, -10.38809149559445, -0.22601938877880912),
    (6, -10.372959528991231, -0.2259354007465575),
    (12, -10.282071023253552, -0.22542506546799856),
    (13, -10.266906897934076, -0.22533894463957438),
    (18, -10.191018016636866, -0.22490379514067982),
]


@pytest.mark.parametrize("time,declination,equation", SUN_POSITION_CASES)
def test_sun_position(time: int, declination: float, equation: float) -> None:
    result = astro.sun_position(time, UTC_MS, LNG)
    assert isinstance(result, tuple)
    assert result.declination == pytest.approx(declination, **APPROX)
    assert result.equation == pytest.approx(equation, **APPROX)


# ---------------------------------------------------------------------------
# mid_day
# ---------------------------------------------------------------------------

MID_DAY_CASES = [
    (5, 12.22601938877881),
    (6, 12.225935400746557),
    (12, 12.225425065468002),
    (13, 12.225338944639574),
    (18, 12.224903795140676),
]


@pytest.mark.parametrize("time,expected", MID_DAY_CASES)
def test_mid_day(time: int, expected: float) -> None:
    assert astro.mid_day(time, UTC_MS, LNG) == pytest.approx(expected, **APPROX)


# ---------------------------------------------------------------------------
# angle_time
# ---------------------------------------------------------------------------

ANGLE_TIME_CASES = [
    (5, 18, -1, 5.224881227781956),
    (5, 18, 1, 19.22715754977566),
    (5, 15, -1, 5.500531537825899),
    (5, 15, 1, 18.95150723973172),
    (5, 0.833, -1, 6.814219823937226),
    (5, 0.833, 1, 17.637818953620393),
    (6, 18, -1, 5.2238568792579025),
    (6, 18, 1, 19.228013922235213),
    (6, 15, -1, 5.499509448845647),
    (6, 15, 1, 18.95236135264747),
    (6, 0.833, -1, 6.813139627639777),
    (6, 0.833, 1, 17.638731173853337),
    (12, 18, -1, 5.217696456782784),
    (12, 18, 1, 19.233153674153222),
    (12, 15, -1, 5.493363411469752),
    (12, 15, 1, 18.957486719466253),
    (12, 0.833, -1, 6.806648425951942),
    (12, 0.833, 1, 17.644201704984063),
    (13, 18, -1, 5.216667336142197),
    (13, 18, 1, 19.23401055313695),
    (13, 15, -1, 5.4923368267143085),
    (13, 15, 1, 18.95834106256484),
    (13, 0.833, -1, 6.805564895202547),
    (13, 0.833, 1, 17.6451129940766),
    (18, 18, -1, 5.211511549785411),
    (18, 18, 1, 19.238296040495943),
    (18, 15, -1, 5.4871943153328235),
    (18, 15, 1, 18.96261327494853),
    (18, 0.833, -1, 6.800140154863628),
    (18, 0.833, 1, 17.649667435417726),
]


@pytest.mark.parametrize("time,angle,direction,expected", ANGLE_TIME_CASES)
def test_angle_time(time: int, angle: float, direction: int, expected: float) -> None:
    result = astro.angle_time(angle, time, LAT, UTC_MS, LNG, direction)
    assert result == pytest.approx(expected, **APPROX)


def test_angle_time_default_direction_is_afternoon() -> None:
    default = astro.angle_time(18, 5, LAT, UTC_MS, LNG)
    explicit = astro.angle_time(18, 5, LAT, UTC_MS, LNG, 1)
    assert default == pytest.approx(explicit, **APPROX)


@pytest.mark.parametrize("angle", ["90 min", "1 min", "Standard"])
def test_angle_time_non_numeric_angle_is_nan(angle: str) -> None:
    # JS: this.sin('90 min') === NaN, so the whole result is NaN.
    assert math.isnan(astro.angle_time(angle, 5, LAT, UTC_MS, LNG, -1))


# ---------------------------------------------------------------------------
# asr_angle
# ---------------------------------------------------------------------------

ASR_ANGLE_CASES = [
    (5, "Standard", -22.88595443551159),
    (5, "Hanafi", -16.532376680289254),
    (5, 1.7, -18.04789831536376),
    (6, "Standard", -22.89253130421162),
    (6, "Hanafi", -16.53589761678103),
    (6, 1.7, -18.052072030745407),
    (12, "Standard", -22.932009808618073),
    (12, "Hanafi", -16.557022898217227),
    (12, 1.7, -18.07711681937331),
    (13, "Standard", -22.93859240800883),
    (13, "Hanafi", -16.56054370420017),
    (13, 1.7, -18.081291345447237),
    (18, "Standard", -22.97151739970854),
    (18, "Hanafi", -16.578147300758125),
    (18, 1.7, -18.102165530093053),
]


@pytest.mark.parametrize("time,asr_param,expected", ASR_ANGLE_CASES)
def test_asr_angle(time: int, asr_param: object, expected: float) -> None:
    result = astro.asr_angle(asr_param, time, LAT, UTC_MS, LNG)
    assert result == pytest.approx(expected, **APPROX)


def test_asr_angle_numeric_string_custom_factor() -> None:
    # '1.7' resolves via parse_value, matching the numeric 1.7 case.
    assert astro.asr_angle("1.7", 5, LAT, UTC_MS, LNG) == pytest.approx(
        astro.asr_angle(1.7, 5, LAT, UTC_MS, LNG), **APPROX
    )


# ---------------------------------------------------------------------------
# parse_value (specs.md §9.4)
# ---------------------------------------------------------------------------

PARSE_VALUE_CASES = [
    ("90 min", 90.0),
    ("1 min", 1.0),
    ("0 min", 0.0),
    (18, 18.0),
    (4.5, 4.5),
    ("-5", -5.0),
    ("min", 0.0),
    ("Standard", 0.0),
    ("Jafari", 0.0),
    ("1.5e3", 1.5),
]


@pytest.mark.parametrize("value,expected", PARSE_VALUE_CASES)
def test_parse_value(value: object, expected: float) -> None:
    assert parse_value(value) == expected


def test_parse_value_returns_float() -> None:
    assert isinstance(parse_value(18), float)
    assert isinstance(parse_value("90 min"), float)


# ---------------------------------------------------------------------------
# is_min (specs.md §9.4)
# ---------------------------------------------------------------------------

IS_MIN_CASES = [
    ("1 min", True),
    ("90 min", True),
    ("min", True),
    ("Standard", False),
    ("Jafari", False),
    (18, False),
    ("Min", False),  # case-sensitive, matching JS String.indexOf
]


@pytest.mark.parametrize("value,expected", IS_MIN_CASES)
def test_is_min(value: object, expected: bool) -> None:
    assert is_min(value) is expected
