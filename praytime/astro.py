"""Pure astronomical core (specs.md §8.2–§8.6).

Implements the approximate solar-coordinate algorithm and the hour-angle
trigonometry used by the prayer-time pipeline:

* :func:`julian_offset` — the Julian-day offset term ``D`` (specs.md §8.2);
* :func:`sun_position` — solar declination and equation of time (specs.md §8.2);
* :func:`mid_day` — local solar noon / Dhuhr (specs.md §8.3);
* :func:`angle_time` — time the sun reaches a given altitude (specs.md §8.4);
* :func:`asr_angle` — Asr shadow-angle (specs.md §8.6, §5).

Every function is **pure**: it takes the inputs it needs explicitly (the UTC
midnight timestamp ``utc_ms`` and the longitude ``lng`` are threaded through
rather than read from instance state) and holds no global state. All angles are
in degrees and all times are local solar hours. Operation order mirrors the JS
source exactly so the double-precision results agree to the last ULP.
"""

from __future__ import annotations

from typing import Any, Dict, NamedTuple, Union

from . import constants as C
from .formatting import parse_value
from .trig import acos, acot, asin, atan2, cos, mod, sin, tan

#: Type accepted for the ``time`` seed: a number or a JS-style string such as
#: ``'90 min'``. Non-numeric strings coerce to ``nan`` (specs.md §8.1).
TimeValue = Union[int, float, str]


class SunPosition(NamedTuple):
    """Solar declination (degrees) and equation of time (hours)."""

    declination: float
    equation: float


#: Asr shadow-length factors for the named madhabs (specs.md §5).
_SHADOW_FACTORS: Dict[str, int] = {
    "Standard": C.SHADOW_STANDARD,
    "Hanafi": C.SHADOW_HANAFI,
}


def julian_offset(utc_ms: float, time: TimeValue, lng: float) -> float:
    """Return the Julian-day offset ``D`` from the J2000.0 epoch (specs.md §8.2).

    Mirrors ``utcTime / 864e5 - 10957.5 + value(time) / 24 - lng / 360``.
    """
    return (
        utc_ms / C.MS_PER_DAY
        - C.J2000_OFFSET_DAYS
        + parse_value(time) / C.HOURS_PER_DAY
        - lng / 360
    )


def sun_position(time: TimeValue, utc_ms: float, lng: float) -> SunPosition:
    """Return the sun's declination and equation of time (specs.md §8.2).

    Uses the USNO approximate solar-coordinate algorithm; the Earth-Sun
    distance term is not used. ``time`` seeds the fractional solar day.
    """
    d = julian_offset(utc_ms, time, lng)

    g = mod(C.MEAN_ANOMALY_BASE + C.MEAN_ANOMALY_RATE * d, 360)
    q = mod(C.MEAN_LONGITUDE_BASE + C.MEAN_LONGITUDE_RATE * d, 360)
    L = mod(q + C.EQ_CENTER_1 * sin(g) + C.EQ_CENTER_2 * sin(2 * g), 360)
    e = C.OBLIQUITY_J2000 - C.OBLIQUITY_RATE * d
    ra = mod(atan2(cos(e) * sin(L), cos(L)) / C.DEG_PER_HOUR, 24)

    declination = asin(sin(e) * sin(L))
    equation = q / 15 - ra
    return SunPosition(declination, equation)


def mid_day(time: TimeValue, utc_ms: float, lng: float) -> float:
    """Return local solar noon as ``mod(12 - EqT, 24)`` hours (specs.md §8.3)."""
    eqt = sun_position(time, utc_ms, lng).equation
    return mod(C.NOON_OFFSET - eqt, C.HOURS_PER_DAY)


def angle_time(
    angle: Any,
    time: TimeValue,
    lat: float,
    utc_ms: float,
    lng: float,
    direction: int = 1,
) -> float:
    """Return the hour the sun reaches ``angle`` below the horizon (specs.md §8.4).

    ``direction`` is ``-1`` for morning prayers and ``+1`` (default) for
    afternoon. When ``cos(H)`` leaves ``[-1, 1]`` the ``acos`` helper returns
    ``nan`` (never clamped), and a non-numeric ``angle`` string coerces to
    ``nan`` via the trig helpers.
    """
    decl = sun_position(time, utc_ms, lng).declination
    numerator = -sin(angle) - sin(lat) * sin(decl)
    diff = acos(numerator / (cos(lat) * cos(decl))) / C.DEG_PER_HOUR
    return mid_day(time, utc_ms, lng) + diff * direction


def asr_angle(asr_param: Any, time: TimeValue, lat: float, utc_ms: float, lng: float) -> float:
    """Return the Asr shadow angle ``-acot(t + tan|lat - decl|)`` (specs.md §8.6).

    The shadow factor ``t`` is ``1`` for ``'Standard'``, ``2`` for ``'Hanafi'``,
    otherwise ``parse_value(asr_param)`` (a custom factor). The ``or`` mirrors
    the JS ``||`` short-circuit (specs.md §5).
    """
    shadow_factor = _SHADOW_FACTORS.get(asr_param) or parse_value(asr_param)
    decl = sun_position(time, utc_ms, lng).declination
    return -acot(shadow_factor + tan(abs(lat - decl)))
