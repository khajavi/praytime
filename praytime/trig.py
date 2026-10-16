"""Degree-based trigonometry helpers with JavaScript coercion semantics.

Every angle-taking/returning helper here works in **degrees** and reproduces the
behaviour of the upstream JS class (specs.md §8.1):

* inputs are coerced with a *full* ``float(x)`` conversion; on failure the input
  becomes ``nan`` and the result is ``nan`` (matching JS where ``'1 min' * 1``
  is ``NaN``);
* :func:`asin`/:func:`acos` catch :class:`ValueError` (out-of-domain) and return
  ``nan`` instead of raising, matching ``Math.asin``/``Math.acos``; results are
  **never clamped**;
* :func:`mod` is the positive (floored) modulo.
"""

from __future__ import annotations

import math
from typing import Any

_NAN = float("nan")


def _to_float(x: Any) -> float:
    """Full numeric coercion: ``float(x)`` or ``nan`` on failure.

    This mirrors JS's implicit ``Number`` coercion for multiplication operands;
    a non-numeric value such as ``'1 min'`` yields ``nan``.
    """
    try:
        return float(x)
    except (TypeError, ValueError):
        return _NAN


def dtr(d: Any) -> float:
    """Degrees to radians."""
    return _to_float(d) * math.pi / 180


def rtd(r: Any) -> float:
    """Radians to degrees."""
    return _to_float(r) * 180 / math.pi


def sin(d: Any) -> float:
    """Sine of an angle in degrees."""
    return math.sin(dtr(d))


def cos(d: Any) -> float:
    """Cosine of an angle in degrees."""
    return math.cos(dtr(d))


def tan(d: Any) -> float:
    """Tangent of an angle in degrees."""
    return math.tan(dtr(d))


def asin(x: Any) -> float:
    """Arc-sine in degrees; ``nan`` outside ``[-1, 1]`` (no clamping)."""
    try:
        return rtd(math.asin(_to_float(x)))
    except ValueError:
        return _NAN


def acos(x: Any) -> float:
    """Arc-cosine in degrees; ``nan`` outside ``[-1, 1]`` (no clamping)."""
    try:
        return rtd(math.acos(_to_float(x)))
    except ValueError:
        return _NAN


def atan(x: Any) -> float:
    """Arc-tangent in degrees."""
    return rtd(math.atan(_to_float(x)))


def acot(x: Any) -> float:
    """Arc-cotangent in degrees: ``rtd(atan(1 / x))``.

    A zero input yields ``90`` (JS ``1 / 0`` is ``Infinity``); ``nan``
    propagates to ``nan``.
    """
    n = _to_float(x)
    try:
        inverse = 1.0 / n
    except ZeroDivisionError:
        inverse = math.inf
    return rtd(math.atan(inverse))


def atan2(y: Any, x: Any) -> float:
    """Two-argument arc-tangent in degrees."""
    return rtd(math.atan2(_to_float(y), _to_float(x)))


def mod(a: Any, b: Any) -> float:
    """Positive modulo: ``((a % b) + b) % b``."""
    return ((a % b) + b) % b
