"""High-latitude adjustment rules (specs.md §6, §10.5).

Implements the JS ``adjustHighLats`` / ``adjustTime`` logic for the ``None`` /
``NightMiddle`` / ``OneSeventh`` / ``AngleBased`` rules:

* :func:`adjust_high_lats` — clamp Fajr/Isha/Maghrib for abnormal night lengths,
  returning the ``adjusted`` flag;
* :func:`adjust_time` — clamp one time against ``base ± portion × night``.

The stateful quirk is preserved: the ``'None'`` rule returns ``prior_adjusted``
untouched and mutates nothing (specs.md §10.5). ``NaN`` is **never** clamped
away silently — it is replaced by the clamp value and flips ``adjusted``.
"""

from __future__ import annotations

import math
from typing import Any, Callable, Dict, Mapping, MutableMapping, Optional, Tuple

from . import constants as C


def adjust_high_lats(
    times: MutableMapping[str, float],
    settings: Mapping[str, Any],
    value_fn: Callable[[Any], float],
    prior_adjusted: Optional[bool] = None,
) -> Optional[bool]:
    """Adjust Fajr/Isha/Maghrib for high latitudes (specs.md §6).

    Returns the ``adjusted`` flag: ``prior_adjusted`` unchanged when
    ``settings['highLats'] == 'None'`` (and touches nothing — specs.md §10.5),
    otherwise ``True`` if any of the three prayers was clamped. ``times`` is
    mutated in place.
    """
    if settings["highLats"] == "None":
        return prior_adjusted

    adjusted = False
    night = 24 + times["sunrise"] - times["sunset"]

    times["fajr"], adjusted = adjust_time(
        times["fajr"], times["sunrise"], settings["fajr"], night, -1,
        settings, value_fn, adjusted,
    )
    times["isha"], adjusted = adjust_time(
        times["isha"], times["sunset"], settings["isha"], night, 1,
        settings, value_fn, adjusted,
    )
    times["maghrib"], adjusted = adjust_time(
        times["maghrib"], times["sunset"], settings["maghrib"], night, 1,
        settings, value_fn, adjusted,
    )
    return adjusted


def adjust_time(
    time: float,
    base: float,
    angle: Any,
    night: float,
    direction: int,
    settings: Mapping[str, Any],
    value_fn: Callable[[Any], float],
    adjusted: bool,
) -> Tuple[float, bool]:
    """Clamp a single ``time`` against ``base ± portion × night`` (specs.md §6.1).

    ``portion`` depends on the rule in ``settings['highLats']``:
    ``NightMiddle`` → ``1/2``, ``OneSeventh`` → ``1/7``, ``AngleBased`` →
    ``(1/60) × value_fn(angle)`` (the **raw** setting value, e.g. ``'90 min'``
    → ``1.5``). A ``NaN`` time or one whose ``(time − base) × direction``
    exceeds ``portion`` is clamped to ``base + portion × direction`` and sets
    ``adjusted`` to ``True`` (strict ``>`` — an exact boundary is not clamped).
    """
    factors: Dict[str, float] = {
        "NightMiddle": C.HL_NIGHT_MIDDLE,
        "OneSeventh": C.HL_ONE_SEVENTH,
        "AngleBased": (1 / C.HL_ANGLE_DIVISOR) * value_fn(angle),
    }
    portion = factors[settings["highLats"]] * night
    time_diff = (time - base) * direction
    if math.isnan(time) or time_diff > portion:
        time = base + portion * direction
        adjusted = True
    return time, adjusted
