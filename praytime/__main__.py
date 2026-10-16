"""Command-line interface for :mod:`praytime` (plan.md Phase 6).

Runnable as ``python -m praytime`` (or as the ``praytime`` console script once
installed). Computes the eight daily prayer times for a location, date, and
calculation method and prints them with aligned labels.

Standard library only; no third-party runtime dependencies.
"""

from __future__ import annotations

import argparse
import datetime as _dt
from typing import List, Optional, Sequence, Tuple

from .constants import METHODS
from .praytime import PrayTime

#: Selectable method names, excluding the internal ``defaults`` entry
#: (specs.md §4).
METHOD_NAMES: List[str] = [name for name in METHODS if name != "defaults"]

#: Allowed ``--format`` values (specs.md §9.1).
FORMATS: List[str] = ["24h", "12h", "12H", "x", "X"]

#: Allowed ``--asr`` values (specs.md §5).
ASR_CHOICES: List[str] = ["Standard", "Hanafi"]

#: Allowed ``--high-lats`` values (specs.md §6).
HIGH_LATS_CHOICES: List[str] = ["None", "NightMiddle", "OneSeventh", "AngleBased"]


def _parse_date(value: str) -> Tuple[int, int, int]:
    """Parse an ISO ``YYYY-MM-DD`` date into a 1-based ``(year, month, day)`` tuple."""
    try:
        parsed = _dt.date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"invalid date {value!r}; expected YYYY-MM-DD"
        ) from exc
    return parsed.year, parsed.month, parsed.day


def build_parser() -> argparse.ArgumentParser:
    """Create the :mod:`argparse` argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        prog="praytime",
        description=(
            "Compute the eight daily Islamic prayer times for a location and "
            "date (Python port of zarrabi/praytime)."
        ),
    )
    parser.add_argument(
        "--method",
        default="MWL",
        choices=METHOD_NAMES,
        help="calculation method (default: MWL)",
    )
    parser.add_argument("--lat", type=float, required=True, help="latitude in degrees")
    parser.add_argument("--lng", type=float, required=True, help="longitude in degrees")
    parser.add_argument(
        "--timezone",
        default="UTC",
        help="IANA timezone name used for display (default: UTC)",
    )
    parser.add_argument(
        "--date",
        type=_parse_date,
        default=None,
        help="date as YYYY-MM-DD (default: today)",
    )
    parser.add_argument(
        "--format",
        default="24h",
        choices=FORMATS,
        help="output format (default: 24h)",
    )
    parser.add_argument(
        "--asr",
        default="Standard",
        choices=ASR_CHOICES,
        help="Asr madhab (default: Standard)",
    )
    parser.add_argument(
        "--high-lats",
        dest="high_lats",
        default="NightMiddle",
        choices=HIGH_LATS_CHOICES,
        help="high-latitude adjustment rule (default: NightMiddle)",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run the ``praytime`` command line and print the eight prayer times."""
    args = build_parser().parse_args(argv)

    date = args.date if args.date is not None else _today()

    praytime = (
        PrayTime(args.method)
        .location([args.lat, args.lng])
        .timezone(args.timezone)
        .adjust({"asr": args.asr, "highLats": args.high_lats})
        .format(args.format)
    )
    times = praytime.times(date)

    width = max(len(label) for label in praytime.labels)
    for label, key in zip(praytime.labels, times):
        print(f"{label:<{width}}  {times[key]}")
    return 0


def _today() -> Tuple[int, int, int]:
    """Return today's host-local date as a ``(year, month, day)`` tuple."""
    today = _dt.date.today()
    return today.year, today.month, today.day


if __name__ == "__main__":
    raise SystemExit(main())
