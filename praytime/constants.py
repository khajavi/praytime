"""Static data tables and numeric constants for :mod:`praytime`.

This module is a leaf: it imports nothing from the rest of the package. It holds

* :data:`METHODS` — the calculation-method table (specs.md §4);
* :data:`LABELS` — the prayer labels (specs.md §11);
* :data:`DEFAULTS` — the static settings template (specs.md §7);
* :func:`default_settings` — a fresh settings mapping with host timezone/location
  resolved (specs.md §7.1);
* every numeric constant and seed hour used by the astronomy pipeline
  (specs.md §11).
"""

from __future__ import annotations

import datetime as _dt
from typing import Any, Dict, List, Tuple, Union

Number = Union[int, float]

# ---------------------------------------------------------------------------
# Calculation methods (specs.md §4)
# ---------------------------------------------------------------------------

#: Calculation-method table, transcribed verbatim from the JS source.
#:
#: ``defaults`` is applied first by ``PrayTime.method`` and then overridden by
#: the named method, so methods such as ``Tehran``/``Jafari`` inherit
#: ``isha: 14`` and ``maghrib: '1 min'``.
METHODS: Dict[str, Dict[str, Any]] = {
    "MWL": {"fajr": 18, "isha": 17},
    "ISNA": {"fajr": 15, "isha": 15},
    "Egypt": {"fajr": 19.5, "isha": 17.5},
    "Makkah": {"fajr": 18.5, "isha": "90 min"},
    "Karachi": {"fajr": 18, "isha": 18},
    "Tehran": {"fajr": 17.7, "maghrib": 4.5, "midnight": "Jafari"},
    "Jafari": {"fajr": 16, "maghrib": 4, "midnight": "Jafari"},
    "France": {"fajr": 12, "isha": 12},
    "Russia": {"fajr": 16, "isha": 15},
    "Malaysia": {"fajr": 20, "isha": 18},  # JAKIM
    "Singapore": {"fajr": 20, "isha": 18},
    "defaults": {"isha": 14, "maghrib": "1 min", "midnight": "Standard"},
}

#: Human-readable prayer labels, in returned-dict order (specs.md §11).
LABELS: List[str] = [
    "Fajr",
    "Sunrise",
    "Dhuhr",
    "Asr",
    "Sunset",
    "Maghrib",
    "Isha",
    "Midnight",
]

# ---------------------------------------------------------------------------
# Numeric constants (specs.md §11)
# ---------------------------------------------------------------------------

#: Sunrise/Sunset horizon angle in degrees (refraction + solar radius).
HORIZON = 0.833

#: Days from the Unix epoch to J2000.0 (JD 2451545.0). Computed, not hardcoded,
#: per the research recommendation: ``2451545.0 - 2440587.5 == 10957.5``.
J2000_OFFSET_DAYS = 2451545.0 - 2440587.5

MS_PER_DAY = 86_400_000
MS_PER_HOUR = 3_600_000
MS_PER_MINUTE = 60_000

# Sun-position coefficients (USNO approximate solar coordinates).
MEAN_ANOMALY_BASE = 357.529
MEAN_ANOMALY_RATE = 0.98560028
MEAN_LONGITUDE_BASE = 280.459
MEAN_LONGITUDE_RATE = 0.98564736
EQ_CENTER_1 = 1.915
EQ_CENTER_2 = 0.020
OBLIQUITY_J2000 = 23.439
OBLIQUITY_RATE = 0.00000036

# Asr shadow factors.
SHADOW_STANDARD = 1
SHADOW_HANAFI = 2

# High-latitude portion factors.
HL_NIGHT_MIDDLE = 1 / 2
HL_ONE_SEVENTH = 1 / 7
#: Divisor for the AngleBased factor ``(1 / HL_ANGLE_DIVISOR) * parse_value(angle)``.
HL_ANGLE_DIVISOR = 60

#: Fixed local-solar-time seed (hours) used to estimate next-day Jafari Fajr.
JAFARI_SEED_HOUR = 29

NOON_OFFSET = 12
HOURS_PER_DAY = 24
DEG_PER_HOUR = 15

#: Placeholder returned for an invalid (NaN) timestamp.
INVALID_TIME = "-----"

#: Initial local-solar-time seed hours for ``compute_times`` (specs.md §8.9).
SEED_TIMES: Dict[str, Number] = {
    "fajr": 5,
    "sunrise": 6,
    "dhuhr": 12,
    "asr": 13,
    "sunset": 18,
    "maghrib": 18,
    "isha": 18,
    "midnight": 24,
}

# ---------------------------------------------------------------------------
# Settings defaults (specs.md §7)
# ---------------------------------------------------------------------------

#: Static settings template. ``timezone`` and ``location`` are host-dependent
#: and filled in by :func:`default_settings` at runtime.
DEFAULTS: Dict[str, Any] = {
    "dhuhr": "0 min",
    "asr": "Standard",
    "highLats": "NightMiddle",
    "tune": {},
    "format": "24h",
    "rounding": "nearest",
    "utcOffset": "auto",
    "iterations": 1,
}


def _host_timezone_and_longitude() -> Tuple[str, float]:
    """Return the host IANA zone (or ``"UTC"``) and its default longitude.

    Mirrors ``Intl.DateTimeFormat().resolvedOptions().timeZone`` and
    ``-(new Date()).getTimezoneOffset() / 4`` (specs.md §7.1). Fixed-offset
    tzinfos that lack a ``.key`` fall back to ``"UTC"``.
    """
    now = _dt.datetime.now().astimezone()
    tzinfo = now.tzinfo
    default_tz = getattr(tzinfo, "key", "UTC")
    offset = now.utcoffset()
    offset_min = 0.0 if offset is None else offset.total_seconds() / 60
    default_lng = -offset_min / 4
    return default_tz, default_lng


def default_settings() -> Dict[str, Any]:
    """Build a fresh settings mapping with host timezone/location resolved.

    Returns a new ``dict`` each call (including a new ``tune`` mapping) so
    callers can freely mutate it without affecting :data:`DEFAULTS` or other
    instances.
    """
    settings: Dict[str, Any] = {
        "dhuhr": DEFAULTS["dhuhr"],
        "asr": DEFAULTS["asr"],
        "highLats": DEFAULTS["highLats"],
        "tune": dict(DEFAULTS["tune"]),
        "format": DEFAULTS["format"],
        "rounding": DEFAULTS["rounding"],
        "utcOffset": DEFAULTS["utcOffset"],
        "iterations": DEFAULTS["iterations"],
    }
    timezone, longitude = _host_timezone_and_longitude()
    settings["timezone"] = timezone
    settings["location"] = [0, longitude]
    return settings
