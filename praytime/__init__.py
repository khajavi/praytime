"""praytime — zero-dependency Islamic prayer times calculator.

Python port of ``zarrabi/praytime``. Public surface: :class:`PrayTime`,
:data:`METHODS`, and :data:`__version__`.
"""

from __future__ import annotations

from .constants import METHODS
from .praytime import PrayTime

__version__ = "0.1.0"

__all__ = ["PrayTime", "METHODS", "__version__"]
