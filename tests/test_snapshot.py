"""Golden-snapshot parity against the upstream JavaScript library (specs.md §12.4).

The goldens in ``tests/golden/golden.json`` are produced once by
``tests/golden/generate.js`` (Node) running the vendored upstream
``tests/golden/upstream/praytime.js`` over a deterministic matrix. This module
re-reads that file and asserts the Python port reproduces every record exactly
(``str`` for string formats, ``int`` for ``'x'``/``'X'``).

The default suite is **Node-free**: the goldens are pre-generated and committed.
A separate opt-in test can regenerate them via Node when ``PRAYTIME_REGEN=1``
and ``node`` are available.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List

import pytest

from praytime import PrayTime

GOLDEN_DIR = Path(__file__).resolve().parent / "golden"
GOLDEN_PATH = GOLDEN_DIR / "golden.json"
GENERATOR = GOLDEN_DIR / "generate.js"
REPO_ROOT = GOLDEN_DIR.parent.parent

#: Minimum number of records that must have been compared (coverage guard).
MIN_RECORDS = 2000

#: Expected values for each covered dimension (coverage guard, specs.md §12.4).
EXPECTED_METHODS = {
    "MWL",
    "ISNA",
    "Egypt",
    "Makkah",
    "Karachi",
    "Tehran",
    "Jafari",
    "France",
    "Russia",
    "Malaysia",
    "Singapore",
}
EXPECTED_LATS = {0, 21.4, 43.4643, 51.5, 64, 70}
EXPECTED_ASRS = {"Standard", "Hanafi"}
EXPECTED_HIGHLATS = {"None", "NightMiddle", "OneSeventh", "AngleBased"}
EXPECTED_FORMATS = {"24h", "12h", "x"}
EXPECTED_TZ_CONFIGS = {"utc0", "America/Toronto"}


def _load_golden() -> List[Dict[str, Any]]:
    with GOLDEN_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def _build(record: Dict[str, Any]) -> PrayTime:
    """Rebuild a fresh :class:`PrayTime` from a golden record's configuration.

    Applies the same order as the generator (specs.md §12.4): constructor →
    ``location`` → timezone config → ``adjust`` (asr/highLats) → ``format``.
    """
    pt = PrayTime(record["method"]).location([record["lat"], record["lng"]])
    if record["timezoneConfig"] == "utc0":
        pt.timezone("UTC").utc_offset(0)
    else:
        pt.timezone(record["timezoneConfig"])
    pt.adjust({"asr": record["asr"], "highLats": record["highLats"]})
    pt.format(record["format"])
    return pt


def _describe(record: Dict[str, Any], got: Dict[str, Any]) -> str:
    expected = record["times"]
    lines = [
        "golden mismatch for config:",
        "  method={method!r} date={date!r} lat={lat!r} lng={lng!r}".format(**record),
        "  timezoneConfig={timezoneConfig!r} asr={asr!r} "
        "highLats={highLats!r} format={format!r}".format(**record),
    ]
    for key in expected:
        exp = expected[key]
        actual = got.get(key, "<missing>")
        if actual != exp or type(actual) is not type(exp):
            lines.append(
                f"  {key}: expected {exp!r} ({type(exp).__name__}), "
                f"got {actual!r} ({type(actual).__name__})"
            )
    return "\n".join(lines)


def test_golden_file_is_present_and_non_empty() -> None:
    assert GOLDEN_PATH.is_file(), f"missing golden file: {GOLDEN_PATH}"
    assert GOLDEN_PATH.stat().st_size > 0
    records = _load_golden()
    assert len(records) >= MIN_RECORDS, (
        f"expected at least {MIN_RECORDS} golden records, found {len(records)}"
    )


def test_golden_matrix_coverage() -> None:
    records = _load_golden()
    assert {r["method"] for r in records} == EXPECTED_METHODS
    assert {tuple(r["date"]) for r in records} >= {
        (2025, 3, 20),
        (2025, 6, 21),
        (2025, 9, 23),
        (2025, 12, 21),
        (2024, 2, 21),
    }
    assert {r["lat"] for r in records} == EXPECTED_LATS
    assert {r["asr"] for r in records} == EXPECTED_ASRS
    assert {r["highLats"] for r in records} == EXPECTED_HIGHLATS
    assert {r["format"] for r in records} == EXPECTED_FORMATS
    assert {r["timezoneConfig"] for r in records} == EXPECTED_TZ_CONFIGS


def test_snapshot_matches_golden_exactly() -> None:
    """Rebuild every record and assert exact string/int equality with the golden."""
    records = _load_golden()
    assert len(records) >= MIN_RECORDS

    failures: List[str] = []
    for record in records:
        got = _build(record).get_times(record["date"])
        expected = record["times"]
        if got != expected:
            failures.append(_describe(record, got))

    assert not failures, (
        f"{len(failures)}/{len(records)} golden records mismatched:\n\n"
        + "\n\n".join(failures[:25])
    )


@pytest.mark.skipif(
    os.environ.get("PRAYTIME_REGEN") != "1" or shutil.which("node") is None,
    reason="set PRAYTIME_REGEN=1 and install Node to regenerate goldens",
)
def test_regenerate_goldens_is_deterministic() -> None:
    """Opt-in: re-run the Node generator and confirm byte-identical output."""
    original = GOLDEN_PATH.read_bytes()
    subprocess.run(["node", str(GENERATOR)], check=True, cwd=str(REPO_ROOT))
    regenerated = GOLDEN_PATH.read_bytes()
    if regenerated != original:
        GOLDEN_PATH.write_bytes(original)
        pytest.fail("golden.json differs from a fresh generator run (drift detected)")
