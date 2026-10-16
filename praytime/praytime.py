"""Public :class:`PrayTime` API and compute pipeline (specs.md §3, §8.9).

The class is the only stateful unit in the package: it owns the constructor,
chainable setters, ``times`` / ``get_times``, and the pipeline that wires the
astronomy, high-latitude, methods, and formatting modules together.

Behaviour is a faithful port of ``zarrabi/praytime`` v3.2, including its
deliberate quirks (see specs.md §13.1): the ``defaults``-then-method merge, the
``utc_offset`` hours heuristic, the ``< 1000`` day-offset heuristic, the
stateful ``_adjusted`` flag, and ``'nan'``-safe conversion of polar results.
"""

from __future__ import annotations

import calendar
import copy
import datetime as _dt
import math
from collections.abc import Sequence
from typing import Any, Dict, List, Mapping, Optional, Tuple, Union

from . import constants as C
from .astro import angle_time, asr_angle, mid_day
from .formatting import format_time, parse_value, round_time
from .formatting import is_min as _is_min
from .highlat import adjust_high_lats

#: Accepted input type for :meth:`PrayTime.times` (specs.md §3.3).
DateInput = Union[
    int,
    float,
    _dt.date,
    _dt.datetime,
    Tuple[int, int, int],
    List[int],
    Sequence[int],
    None,
]


class PrayTime:
    """Islamic prayer-times calculator.

    A faithful port of ``zarrabi/praytime``'s ``PrayTime``. All setters return
    ``self`` so calls chain (``set_method`` is the deprecated exception).
    """

    def __init__(self, method: str = "MWL") -> None:
        self.methods: Dict[str, Dict[str, Any]] = copy.deepcopy(C.METHODS)
        self.settings: Dict[str, Any] = C.default_settings()
        self.labels: List[str] = list(C.LABELS)
        self._utc_time: int = 0
        self._adjusted: Optional[bool] = None
        self.method(method)

    # ------------------------------------------------------------------
    # Setters (specs.md §3.2)
    # ------------------------------------------------------------------

    def method(self, method: str) -> "PrayTime":
        """Select a calculation method, applying ``defaults`` first (specs.md §4.2)."""
        self.set(self.methods["defaults"])
        self.set(self.methods.get(method, {}))
        return self

    def adjust(self, params: Mapping[str, Any]) -> "PrayTime":
        """Merge arbitrary calculation parameters (specs.md §3.2)."""
        return self.set(params)

    def location(self, location: Sequence[float]) -> "PrayTime":
        """Set ``[latitude, longitude]`` (degrees); stored as a list (specs.md §3.2)."""
        return self.set({"location": list(location)})

    def timezone(self, timezone: str) -> "PrayTime":
        """Set the IANA timezone used for ``'auto'`` offset rendering (specs.md §3.2)."""
        return self.set({"timezone": timezone})

    def tune(self, tune: Mapping[str, float]) -> "PrayTime":
        """Set per-prayer minute offsets (specs.md §3.2)."""
        return self.set({"tune": tune})

    def round(self, rounding: str = "nearest") -> "PrayTime":
        """Set the minute-rounding rule (``nearest``/``up``/``down``/``none``)."""
        return self.set({"rounding": rounding})

    def format(self, format: Union[str, Any]) -> "PrayTime":
        """Set the output format (``24h``/``12h``/``12H``/``x``/``X``/callable)."""
        return self.set({"format": format})

    def set(self, settings: Mapping[str, Any]) -> "PrayTime":
        """Merge ``settings`` into the settings object and return ``self`` (specs.md §3.2)."""
        self.settings.update(settings)
        return self

    def utc_offset(self, utc_offset: Union[float, str] = "auto") -> "PrayTime":
        """Set the UTC offset; a numeric ``|value| < 16`` is hours (specs.md §3.2, §10.4).

        Follows the JS ``utcOffset`` exactly: a numeric argument with
        ``abs(value) < 16`` is multiplied by 60, then ``timezone`` is forced to
        ``'UTC'`` before ``utcOffset`` is stored. Passing ``'auto'`` forces
        ``timezone='UTC'`` and ``utcOffset='auto'`` (a preserved quirk).
        """
        if (
            isinstance(utc_offset, (int, float))
            and not isinstance(utc_offset, bool)
            and abs(utc_offset) < 16
        ):
            utc_offset = utc_offset * 60
        self.set({"timezone": "UTC"})
        return self.set({"utcOffset": utc_offset})

    def set_method(self, method: str) -> None:
        """Deprecated: select a calculation method; returns ``None`` (specs.md §3.2)."""
        self.method(method)
        return None

    # ------------------------------------------------------------------
    # Getters (specs.md §3.3)
    # ------------------------------------------------------------------

    def times(self, date: DateInput = 0) -> Dict[str, Union[str, int]]:
        """Compute the eight prayer times for ``date`` (specs.md §3.3, §8.9).

        ``date`` may be omitted/``0`` (today), a day offset (``< 1000``), a
        Unix-milliseconds timestamp (``>= 1000``), a :class:`datetime.date` /
        :class:`datetime.datetime` (time discarded), or a 1-based
        ``(year, month, day)`` tuple/list.
        """
        year, month, day = _normalize_date(date)
        _dt.date(year, month, day)
        self._utc_time = calendar.timegm((year, month, day, 0, 0, 0)) * 1000

        times = self.compute_times()
        self.format_times(times)
        return times

    def get_times(
        self,
        date: DateInput = None,
        location: Optional[Sequence[float]] = None,
        timezone: Union[str, float] = "auto",
        dst: float = 0,
        format: Union[str, Any] = "24h",
    ) -> Dict[str, Union[str, int]]:
        """Backward-compatible wrapper around :meth:`times` (specs.md §3.3).

        When ``location`` is falsy this delegates to :meth:`times`. Otherwise it
        sets the location, a numeric UTC offset (``timezone`` plus ``dst``;
        ``'auto'`` is preserved), and the format, then computes.
        """
        if not location:
            return self.times(date)
        utc_offset_arg: Union[str, float] = timezone if timezone == "auto" else timezone + dst
        self.location(location).utc_offset(utc_offset_arg).format(format)
        return self.times(date)

    # ------------------------------------------------------------------
    # Misc (specs.md §9.4)
    # ------------------------------------------------------------------

    def value(self, x: Any) -> float:
        """JS ``value``: leading-number parse (specs.md §9.4)."""
        return parse_value(x)

    def is_min(self, x: Any) -> bool:
        """JS ``isMin``: ``'min'`` substring test (specs.md §9.4)."""
        return _is_min(x)

    # ------------------------------------------------------------------
    # Compute pipeline (specs.md §8.9)
    # ------------------------------------------------------------------

    def compute_times(self) -> Dict[str, float]:
        """Run the full compute pipeline and return raw timestamps (ms)."""
        times: Dict[str, float] = dict(C.SEED_TIMES)

        for _ in range(int(self.settings["iterations"])):
            times = self.process_times(times)

        # An unknown method leaves ``fajr`` absent (parity with JS ``undefined``).
        # ``highlat`` reads the key directly, so supply a sentinel for that call
        # only (``parse_value(None) == 0.0``, mirroring ``value(undefined)``).
        highlat_settings: Mapping[str, Any] = self.settings
        if "fajr" not in highlat_settings:
            highlat_settings = dict(highlat_settings)
            highlat_settings["fajr"] = None
        adjusted = adjust_high_lats(times, highlat_settings, parse_value, self._adjusted)
        if adjusted is not None:
            self._adjusted = adjusted
        self.update_times(times)
        self.tune_times(times)
        self.convert_times(times)
        return times

    def process_times(self, times: Mapping[str, float]) -> Dict[str, float]:
        """Refine the seed times with one pass of the astronomical formulas."""
        lat, lng = self._lat_lng()
        utc = self._utc_time
        params = self.settings
        return {
            "fajr": angle_time(params.get("fajr"), times["fajr"], lat, utc, lng, -1),
            "sunrise": angle_time(C.HORIZON, times["sunrise"], lat, utc, lng, -1),
            "dhuhr": mid_day(times["dhuhr"], utc, lng),
            "asr": angle_time(
                asr_angle(params["asr"], times["asr"], lat, utc, lng),
                times["asr"],
                lat,
                utc,
                lng,
            ),
            "sunset": angle_time(C.HORIZON, times["sunset"], lat, utc, lng),
            "maghrib": angle_time(params.get("maghrib"), times["maghrib"], lat, utc, lng),
            "isha": angle_time(params.get("isha"), times["isha"], lat, utc, lng),
            "midnight": mid_day(times["midnight"], utc, lng) + C.NOON_OFFSET,
        }

    def update_times(self, times: Dict[str, float]) -> None:
        """Apply interval overrides, Jafari midnight, and the Dhuhr offset (specs.md §8.10)."""
        lat, lng = self._lat_lng()
        utc = self._utc_time
        params = self.settings

        if _is_min(params["maghrib"]):
            times["maghrib"] = times["sunset"] + parse_value(params["maghrib"]) / 60
        if _is_min(params["isha"]):
            times["isha"] = times["maghrib"] + parse_value(params["isha"]) / 60
        if params["midnight"] == "Jafari":
            next_fajr = (
                angle_time(params.get("fajr"), C.JAFARI_SEED_HOUR, lat, utc, lng, -1) + 24
            )
            times["midnight"] = (
                times["sunset"] + ((times["fajr"] + 24) if self._adjusted else next_fajr)
            ) / 2
        times["dhuhr"] += parse_value(params["dhuhr"]) / 60

    def tune_times(self, times: Dict[str, float]) -> None:
        """Apply per-prayer minute tuning (specs.md §8.11)."""
        mins = self.settings["tune"]
        for key in times:
            if key in mins:
                times[key] += mins[key] / 60

    def convert_times(self, times: Dict[str, float]) -> None:
        """Convert local solar hours to rounded Unix-ms timestamps (specs.md §8.12)."""
        lng = self.settings["location"][1]
        for key in times:
            local_ms = (times[key] - lng / 15) * C.MS_PER_HOUR
            timestamp = self._utc_time + (
                math.floor(local_ms) if math.isfinite(local_ms) else local_ms
            )
            times[key] = round_time(timestamp, self.settings["rounding"])

    def format_times(self, times: Dict[str, Any]) -> None:
        """Format each timestamp in place per the configured format (specs.md §9.1)."""
        for key in times:
            times[key] = format_time(times[key], self.settings)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _lat_lng(self) -> Tuple[float, float]:
        location = self.settings["location"]
        return location[0], location[1]


def _normalize_date(date: DateInput) -> Tuple[int, int, int]:
    """Normalize a date input to a 1-based ``(year, month, day)`` tuple (specs.md §3.3).

    Mirrors the JS ``times`` normalization: numeric values ``< 1000`` are day
    offsets from *now* (host-local), larger ones are Unix-millisecond
    timestamps rendered to the host-local calendar date.
    """
    if date is None:
        date = 0
    if isinstance(date, bool):
        raise TypeError("date must be a number, date, or (year, month, day)")
    if isinstance(date, (int, float)):
        if date < 1000:
            resolved = (_dt.datetime.now() + _dt.timedelta(days=date)).date()
        else:
            resolved = _dt.datetime.fromtimestamp(date / 1000).date()
        return resolved.year, resolved.month, resolved.day
    if isinstance(date, _dt.datetime):
        return date.year, date.month, date.day
    if isinstance(date, _dt.date):
        return date.year, date.month, date.day
    if isinstance(date, Sequence) and not isinstance(date, (str, bytes)):
        if len(date) != 3:
            raise ValueError("date must be (year, month, day)")
        return date[0], date[1], date[2]
    raise TypeError("date must be a number, date, or (year, month, day)")
