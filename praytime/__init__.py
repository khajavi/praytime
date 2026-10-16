"""praytime — zero-dependency Islamic prayer times calculator.

Python port of ``zarrabi/praytime``. Public surface: :class:`PrayTime`,
:data:`METHODS`, and :data:`__version__`.

.. warning::
   This package was ported from the original ``zarrabi/praytime`` library using
   AI-agent code-generation tooling. Despite extensive testing against the
   upstream implementation, it may contain bugs in prayer-time calculations.
   Verify the times before relying on them, and use it at your own
   responsibility (provided "as is", without warranty of any kind).
"""

from __future__ import annotations

from .constants import METHODS
from .praytime import PrayTime

__version__ = "0.1.0"

__all__ = ["PrayTime", "METHODS", "__version__"]
