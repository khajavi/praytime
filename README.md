# praytime

Zero-dependency Islamic prayer times calculator — a faithful Python port of
[`zarrabi/praytime`](https://github.com/zarrabi/praytime) (v3.2.0).

It computes the eight daily prayer times — **Fajr, Sunrise, Dhuhr, Asr, Sunset,
Maghrib, Isha, Midnight** — from a date and `[latitude, longitude]` using the
same standard astronomical formulas as the JavaScript library (USNO approximate
solar coordinates + hour-angle trigonometry). The port reproduces the JS
numerical behaviour exactly, including its deliberate quirks, while exposing an
idiomatic, chainable, fully type-hinted Python API.

## Status

Feature-complete and release-ready: the full API, the 11 calculation methods,
the four high-latitude rules, all output formats, date-input handling, and the
high-latitude/interval overrides are implemented and covered by a comprehensive
pytest suite that includes snapshots generated directly from the upstream
JavaScript library.

- Python **3.9+**
- **Zero runtime dependencies** (standard library only: `math`, `datetime`,
  `zoneinfo`, `re`, `calendar`)
- Ships `py.typed` for downstream type checkers

## Installation

```bash
pip install praytime
```

For development (installs pytest, ruff, and mypy):

```bash
pip install -e ".[dev]"
python -m pytest -q
```

## Quick start

```python
from praytime import PrayTime

praytime = PrayTime("ISNA").location([43.4643, -80.5204]).timezone("America/Toronto")
times = praytime.times([2025, 2, 21])  # 1-based month: 21 Feb 2025

times["fajr"]     # '05:52'
times["dhuhr"]    # '12:36'
times["asr"]      # '15:32'
times["maghrib"]  # '18:02'
```

All setters return `self`, so configuration chains:

```python
from praytime import PrayTime

times = (
    PrayTime("MWL")
    .location([51.5074, -0.1278])
    .timezone("Europe/London")
    .adjust({"asr": "Hanafi", "highLats": "AngleBased"})
    .tune({"fajr": -2, "isha": 3})   # minutes
    .round("nearest")
    .format("12h")
    .times([2025, 6, 21])
)
# {'fajr': '2:29 AM', 'sunrise': '4:43 AM', 'dhuhr': '1:02 PM', 'asr': '6:40 PM', ...}
```

`times()` accepts:
- nothing / `0` → today;
- an `int`/`float` `< 1000` → a day offset from today (may be fractional);
- an `int`/`float` `>= 1000` → a Unix **milliseconds** timestamp;
- a `datetime.date` / `datetime.datetime` (the time-of-day is discarded);
- a 1-based `(year, month, day)` tuple or list.

```python
praytime.times()                       # today
praytime.times(7)                      # one week from today
praytime.times([2025, 2, 21])          # 21 Feb 2025
```

> The CLI additionally accepts an ISO `YYYY-MM-DD` string for `--date`.

## Returned keys

`times()` (and `get_times()`) return a `dict` with exactly these eight keys, in
this order:

| Key | Prayer |
|---|---|
| `fajr` | Fajr |
| `sunrise` | Sunrise |
| `dhuhr` | Dhuhr |
| `asr` | Asr |
| `sunset` | Sunset |
| `maghrib` | Maghrib |
| `isha` | Isha |
| `midnight` | Midnight |

Values are formatted **strings** (`"05:52"`, `"3:32 PM"`, `"-----"`) for string
formats, and **ints** for the `"x"` (Unix ms) / `"X"` (Unix s) formats. A `nan`
result (e.g. Fajr at a polar latitude with `highLats="None"`) renders as
`"-----"`.

## Calculation methods

Select a method by name via the constructor or `.method("...")`. Every method is
applied on top of the shared `defaults` (`isha: 14°`, `maghrib: '1 min'`,
`midnight: 'Standard'`), so a method only overrides the keys it defines — e.g.
Tehran and Jafari inherit `isha: 14°`.

| Method | `fajr` | `isha` | `maghrib` | `midnight` | Convention |
|---|---|---|---|---|---|
| `MWL` (default) | 18° | 17° | `'1 min'` | `'Standard'` | Muslim World League |
| `ISNA` | 15° | 15° | `'1 min'` | `'Standard'` | Islamic Society of North America |
| `Egypt` | 19.5° | 17.5° | `'1 min'` | `'Standard'` | Egyptian General Authority of Survey |
| `Makkah` | 18.5° | `'90 min'` | `'1 min'` | `'Standard'` | Umm al-Qura |
| `Karachi` | 18° | 18° | `'1 min'` | `'Standard'` | Univ. of Islamic Sciences, Karachi |
| `Tehran` | 17.7° | 14° (inherited) | 4.5° | `'Jafari'` | Inst. of Geophysics, Univ. of Tehran |
| `Jafari` | 16° | 14° (inherited) | 4° | `'Jafari'` | Leva Research Institute, Qom |
| `France` | 12° | 12° | `'1 min'` | `'Standard'` | Union des Organisations Islamiques de France |
| `Russia` | 16° | 15° | `'1 min'` | `'Standard'` | Spiritual Administration of Muslims of Russia |
| `Malaysia` | 20° | 18° | `'1 min'` | `'Standard'` | JAKIM |
| `Singapore` | 20° | 18° | `'1 min'` | `'Standard'` | Islamic Religious Council of Singapore |

An angle is the sun's depression below the horizon; a `'<n> min'` value is a
fixed interval (Maghrib after Sunset, Isha after Maghrib). You can add your own
method to the per-instance table:

```python
praytime.methods["Algeria"] = {"fajr": 18, "isha": 17}
praytime.method("Algeria")
```

## Madhab / Asr

The Asr shadow length is set through the `asr` parameter (default `"Standard"`):

| `asr` | Meaning | Shadow factor |
|---|---|---|
| `"Standard"` | Shafi'i, Maliki, Jafari, Hanbali | 1 |
| `"Hanafi"` | Hanafi school | 2 |
| a number or numeric string (e.g. `1.7`) | custom shadow factor | parsed value |

```python
PrayTime().adjust({"asr": "Hanafi"})
```

## Options

| Setter | Values | Default | Notes |
|---|---|---|---|
| `.location([lat, lng])` | degrees | host-derived | latitude, longitude |
| `.timezone("...")` | IANA name | host zone | used when `utcOffset` is `"auto"` |
| `.adjust({...})` | any settings mapping | — | generic merge for `fajr`, `isha`, `dhuhr`, `maghrib`, `midnight`, `asr`, `highLats`, … |
| `.tune({...})` | prayer → minutes | `{}` | per-prayer offsets; fractions allowed |
| `.round(value)` | `"nearest"`, `"up"`, `"down"`, `"none"` | `"nearest"` | minute rounding (`nearest` is JS half-up) |
| `.format(value)` | `"24h"`, `"12h"`, `"12H"`, `"x"`, `"X"`, or a callable | `"24h"` | see formats below |
| `.utc_offset(value)` | number (minutes) or `"auto"` | `"auto"` | see the heuristic below |
| `.set({...})` | any settings mapping | — | low-level merge used by every setter |

### Output formats

| `format` | Result (Asr example) |
|---|---|
| `"24h"` | `'15:32'` (zero-padded hour) |
| `"12h"` | `'3:32 PM'` (no leading zero) |
| `"12H"` | `'3:32'` (AM/PM stripped) |
| `"x"` | `1740169920000` (Unix milliseconds, `int`) |
| `"X"` | `1740169920` (Unix seconds, `int`) |
| callable | the callable's return value; it receives the rounded ms `int` |

### `utc_offset` heuristic

`utc_offset(n)` treats a numeric `n` with `abs(n) < 16` as **hours** (`n * 60`),
and larger values as **minutes**. It also forces `timezone` to `"UTC"` and sets
`utcOffset` to the numeric value:

```python
PrayTime().utc_offset(-5)     # -300 minutes (UTC-5)
PrayTime().utc_offset(-4.5)   # -270 minutes
PrayTime().utc_offset(-300)   # -300 minutes (already minutes)
```

A numeric `utcOffset` shifts the timestamp before rendering; `"auto"` renders in
the configured `timezone` instead. (For parity, calling `utc_offset("auto")`
forces `timezone="UTC"`.)

### High-latitude rules

Controlled by `highLats` (default `"NightMiddle"`). They clamp Fajr/Isha/Maghrib
when the sun does not reach the required depression angle.

| `highLats` | Factor | Clamp |
|---|---|---|
| `"None"` | — | no adjustment (polar results may render as `'-----'`) |
| `"NightMiddle"` | 1/2 | Fajr = sunrise − night/2; Isha/Maghrib = sunset + night/2 |
| `"OneSeventh"` | 1/7 | Fajr = sunrise − night/7; Isha/Maghrib = sunset + night/7 |
| `"AngleBased"` | (1/60) × angle | proportional to the twilight angle |

where `night = 24 + sunrise − sunset`.

## Backward-compatible `get_times`

```python
praytime.get_times(date, location, timezone="auto", dst=0, format="24h")
```

When `location` is omitted/falsy it delegates to `times(date)`. Otherwise it sets
the location, a numeric UTC offset (`timezone + dst`), and the format, then
computes. Note the third parameter is a **numeric UTC offset** (or `"auto"`),
matching the JS library — not an IANA zone name.

## Command line

The package is runnable as `python -m praytime`, and installing it provides a
`praytime` console command:

```bash
python -m praytime \
  --method ISNA \
  --lat 43.4643 --lng -80.5204 \
  --timezone America/Toronto \
  --date 2025-02-21
```

```text
Fajr      05:52
Sunrise   07:11
Dhuhr     12:36
Asr       15:32
Sunset    18:01
Maghrib   18:02
Isha      19:20
Midnight  00:36
```

Options:

| Option | Default | Choices |
|---|---|---|
| `--method` | `MWL` | the 11 method names above |
| `--lat` | *(required)* | latitude in degrees |
| `--lng` | *(required)* | longitude in degrees |
| `--timezone` | `UTC` | IANA timezone name |
| `--date` | today | `YYYY-MM-DD` |
| `--format` | `24h` | `24h`, `12h`, `12H`, `x`, `X` |
| `--asr` | `Standard` | `Standard`, `Hanafi` |
| `--high-lats` | `NightMiddle` | `None`, `NightMiddle`, `OneSeventh`, `AngleBased` |

## Compatibility & intentional deviations from the JS library

The port is numerically faithful (see the spec's §13.1 parity list). The
following differ intentionally, and only in ergonomics or error handling
(spec §13.2):

- **snake_case public methods.** `getTimes` → `get_times`, `utcOffset` →
  `utc_offset`, `setMethod` → `set_method` (deprecated, returns `None`). The
  class name stays `PrayTime`.
- **camelCase settings keys are preserved verbatim.** Keys consumed by the
  algorithm and passed through `adjust({...})` — `highLats`, `utcOffset` — keep
  their JS spelling so drop-in translations keep working.
- **Stricter invalid-date handling.** Malformed `(y, m, d)` tuples (wrong length)
  and out-of-range dates raise `ValueError`; the JS `Date.UTC` silently
  normalizes them. A wrong-length sequence raises
  `ValueError("date must be (year, month, day)")`.
- **Type hints and private internals.** Full annotations are provided; the JS
  instance fields `utcTime` / `adjusted` become the private `_utc_time` /
  `_adjusted`. Observable behaviour is unchanged.
- **Per-instance method table.** `praytime.methods` is a deep copy, so mutating
  one instance (e.g. adding `"Algeria"`) never leaks to another. The user
  workflow `praytime.methods["X"] = {...}` is unchanged.
- **Unknown method names** apply only the shared `defaults` and do **not** raise,
  matching the JS no-op.
- **Timezone rendering** uses `zoneinfo` (stdlib) rather than the host `Intl`
  database; `12h` hours are rendered arithmetically (no leading zero) for
  deterministic, portable output.
- **Preserved JS quirks** (not deviations, but worth knowing): the
  `abs(n) < 16` hours heuristic in `utc_offset`, the `date < 1000` day-offset
  heuristic in `times`, the stateful high-latitude `_adjusted` flag, and
  `get_times`' numeric-offset third parameter.

The implementation specification lives in [`docs/specs.md`](docs/specs.md) and
the roadmap in [`docs/plan.md`](docs/plan.md).

## License

MIT — see [`LICENSE`](LICENSE). Preserves the upstream copyright notice:
`Copyright (c) 2007-2025 Hamid Zarrabi-Zadeh`.
