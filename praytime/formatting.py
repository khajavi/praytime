"""Output formatting, rounding, and interval parsing (specs.md §8.13, §9).

This module holds the pure helpers used to turn computed timestamps into
strings (and interval strings into numbers):

* :func:`parse_value` — the JS ``value`` leading-number parse (specs.md §9.4);
* :func:`is_min` — the JS ``isMin`` ``'min'`` substring test (specs.md §9.4);
* :func:`js_round` — half-up rounding matching JS ``Math.round`` (specs.md §8.13);
* :func:`round_time` — minute rounding on the millisecond scale (specs.md §8.13);
* :func:`time_to_string` — ``24h``/``12h``/``12H`` rendering (specs.md §9.1, §9.3);
* :func:`format_time` — ``x``/``X``/callable/``'-----'`` dispatch (specs.md §9.1).

Standard library only (``math``, ``re``, ``datetime``, ``zoneinfo``).
"""

from __future__ import annotations

import datetime as _dt
import math
import re
from typing import Any, Mapping

from zoneinfo import ZoneInfo

from .constants import INVALID_TIME, MS_PER_MINUTE

#: Split pattern matching JS ``/[^0-9.+-]/``: everything that is not a digit,
#: dot, plus, or minus.
_NUM_RE = re.compile(r"[^0-9.+-]")

#: Pattern stripping the ``" AM"``/``" PM"`` suffix for the ``'12H'`` format,
#: matching JS ``/ ?[AP]M/`` (specs.md §8.13/§9.1).
_AMPM_RE = re.compile(r" ?[AP]M")


def parse_value(x: Any) -> float:
    """Parse the leading number of ``x`` like the JS ``value`` helper.

    Numbers pass straight through as ``float(x)``. For any other value the
    string form is split on the first non-numeric character and the head is
    converted; an empty or unparseable head yields ``0.0`` (mirroring
    ``+'' === 0`` / the JS fallback). See specs.md §9.4.
    """
    if isinstance(x, (int, float)):
        return float(x)
    head = _NUM_RE.split(str(x), maxsplit=1)[0]
    try:
        return float(head)
    except ValueError:
        return 0.0


def is_min(x: Any) -> bool:
    """Return whether the string form of ``x`` contains ``'min'`` (specs.md §9.4)."""
    return "min" in str(x)


def js_round(x: float) -> int:
    """Round half-up, matching JS ``Math.round`` (specs.md §8.13).

    JS ``Math.round`` rounds ``.5`` toward ``+`` infinity; Python's built-in
    :func:`round` uses banker's rounding and must not be used. For the positive
    timestamps handled here ``floor(x + 0.5)`` reproduces JS exactly.
    """
    return math.floor(x + 0.5)


def round_time(timestamp: float, rounding: str) -> float:
    """Round ``timestamp`` (ms) to the nearest minute per ``rounding`` (specs.md §8.13).

    ``'up'`` uses :func:`math.ceil`, ``'down'`` uses :func:`math.floor`,
    ``'nearest'`` uses :func:`js_round` (half-up). Any other value (including
    ``'none'``) leaves the timestamp unchanged, mirroring the JS lookup miss.
    """
    fn = {"up": math.ceil, "down": math.floor, "nearest": js_round}.get(rounding)
    if fn is None:
        return timestamp
    if isinstance(timestamp, float) and not math.isfinite(timestamp):
        return timestamp
    return fn(timestamp / MS_PER_MINUTE) * MS_PER_MINUTE


def _zone(name: str) -> _dt.tzinfo:
    """Return the IANA zone ``name``, falling back to UTC if data is missing.

    ``ZoneInfo`` raises when the tz database has no matching key (e.g. minimal
    images without ``tzdata``); the port degrades gracefully to UTC rather than
    failing (specs.md §7.1, §9.2).
    """
    try:
        return ZoneInfo(name)
    except Exception:
        return _dt.timezone.utc


def time_to_string(timestamp: float, fmt: str, settings: Mapping[str, Any]) -> str:
    """Render ``timestamp`` (ms) as a clock string in the configured zone.

    The instant is shifted by a numeric ``settings['utcOffset']`` (minutes)
    before rendering; ``'auto'`` leaves it untouched. JS **always** renders with
    ``settings['timezone']`` (specs.md §9.2, §9.3):

    * ``'24h'`` → ``HH:MM`` (zero-padded);
    * otherwise ``H:MM AM/PM`` (no leading zero), with the suffix stripped for
      ``'12H'`` and kept for ``'12h'``.
    """
    utc_offset = settings["utcOffset"]
    zone = _zone(settings["timezone"])
    if utc_offset == "auto":
        dt = _dt.datetime.fromtimestamp(timestamp / 1000, tz=zone)
    else:
        dt = _dt.datetime.fromtimestamp((timestamp + utc_offset * 60000) / 1000, tz=zone)

    if fmt == "24h":
        return f"{dt.hour:02d}:{dt.minute:02d}"

    hour = dt.hour % 12 or 12
    ampm = "AM" if dt.hour < 12 else "PM"
    rendered = f"{hour}:{dt.minute:02d} {ampm}"
    if fmt == "12H":
        return _AMPM_RE.sub("", rendered)
    return rendered


def format_time(timestamp: float, settings: Mapping[str, Any]) -> Any:
    """Dispatch ``timestamp`` (ms) through ``settings['format']`` (specs.md §9.1).

    A ``float('nan')`` timestamp renders as :data:`INVALID_TIME` (``'-----'``).
    A callable format receives the (already rounded) millisecond number. A
    ``'x'``/``'X'`` format returns ``floor`` of milliseconds/seconds (the
    seconds branch is case-sensitive on ``'X'``). Anything else is rendered via
    :func:`time_to_string`.
    """
    fmt = settings["format"]
    if isinstance(timestamp, float) and math.isnan(timestamp):
        return INVALID_TIME
    if callable(fmt):
        return fmt(timestamp)
    if isinstance(fmt, str) and fmt.lower() == "x":
        return math.floor(timestamp / (1000 if fmt == "X" else 1))
    return time_to_string(timestamp, fmt, settings)
