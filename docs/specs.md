# PrayTime Python Port — Implementation Specification

> Source of truth: `https://github.com/zarrabi/praytime`, file `src/praytime.js`
> (v3.2.0, 398 lines), test suite `tests/test.js`, and the research report at
> `docs/research.md`.
> This document is implementation-ready: every algorithm, constant, default, and
> public signature is specified. Where the JavaScript source is authoritative but
> quirky, the quirk is called out and the porting decision is made explicitly.
> All JavaScript snippets below are quoted verbatim from the source fetched on
> 2026-10-16.

---

## 1. Overview & Goals

### 1.1 Purpose

Port the zero-dependency JavaScript library `zarrabi/praytime` (Islamic prayer-time
calculator) to Python, producing a faithful, well-tested, idiomatic Python package
whose numerical output matches the JavaScript library for all supported inputs.

The JS library computes the eight daily prayer times — **Fajr, Sunrise, Dhuhr, Asr,
Sunset, Maghrib, Isha, Midnight** — from a date and `[latitude, longitude]`, using
standard astronomical formulas (USNO approximate solar coordinates + hour-angle
trigonometry). It supports 11 named calculation conventions, two Asr madhabs plus a
custom shadow factor, four high-latitude adjustment rules, timezone / numeric-offset
display, per-prayer tuning, minute rounding, and several output formats.

### 1.2 Goals

1. **Numerical parity**: for any input the JS library accepts, the Python port must
   return the same formatted strings / timestamps (see §11 tolerance rules).
2. **API parity (ergonomic)**: same chainable setter style and same returned keys,
   with idiomatic snake_case Python naming and type hints.
3. **Zero third-party runtime dependencies**: standard library only (`math`,
   `datetime`, `zoneinfo`, `re`, `calendar`).
4. **Testable**: a pytest suite that mirrors the JS Jest suite exactly, plus
   high-latitude and edge-case tests.
5. **Documented deviations**: any place Python intentionally differs from JS is
   listed in §12.

### 1.3 Non-Goals

- **Elevation is not modeled.** The `0.833°` horizon constant is fixed regardless of
  altitude, matching the JS source and the docs ("the constant is considered the same
  regardless of the elevation").
- **Makkah Ramadan rule (120 min) is NOT implemented.** The JS source always uses the
  method value `isha: '90 min'`; there is no Ramadan special case. The port matches.
- No GUI, no network access, no astronomical ephemeris beyond the built-in
  approximate algorithm (accuracy ~1 arcminute within two centuries of J2000).
- Not a re-derivation of the astronomy: the port reproduces the JS algorithms
  exactly, including the iteration seeding guess `29` and the single-pass default.

### 1.4 Target Python version

**Python 3.9+**. Rationale: `zoneinfo` (PEP 615) is standard-library from 3.9; modern
typing syntax is written in a 3.9-compatible form (`typing.Union`, `typing.Optional`,
`typing.Tuple`, `typing.Dict`, `typing.Callable`, `typing.Mapping`, `typing.Sequence`)
rather than `X | Y` (which requires 3.10). Use `from __future__ import annotations`
so annotations can be written naturally while still running on 3.9.

### 1.5 Package name

PyPI / import name: **`praytime`**. The public class remains **`PrayTime`** to match
the JS export.

---

## 2. Package Layout

```
praytime/
├── pyproject.toml              # build metadata; no runtime deps; pytest dev dep
├── README.md
├── docs/
│   ├── research.md             # (exists) research report
│   └── specs.md                # (this file)
├── praytime/
│   ├── __init__.py             # public exports: PrayTime, METHODS, VERSION
│   ├── constants.py            # all numeric constants, method table, defaults, labels
│   ├── trig.py                 # degree-based trig helpers (dtr, rtd, sin, ... acot)
│   ├── astro.py                # sunPosition, midDay, angleTime, asrAngle, julian offset
│   ├── highlat.py              # adjustHighLats / adjustTime logic
│   ├── formatting.py           # roundTime, formatTime, timeToString, value(), isMin()
│   ├── methods.py              # thin helpers to resolve/inspect the method table
│   └── praytime.py             # the PrayTime class (orchestration + public API)
└── tests/
    ├── __init__.py
    ├── test_reference.py       # mirrors tests/test.js assertions exactly
    ├── test_methods.py         # method table + inherited defaults
    ├── test_highlat.py         # polar / high-latitude rules
    ├── test_formatting.py      # 24h/12h/12H/x/X/function/'-----'
    ├── test_date_inputs.py     # date / datetime / tuple / timestamp / day offset
    └── test_snapshot.py        # golden files across months/latitudes
```

### 2.1 File contents

| File | Contents |
|---|---|
| `praytime/__init__.py` | `from .praytime import PrayTime`, `from .constants import METHODS`, `__version__`, `__all__`. |
| `praytime/constants.py` | `METHODS` (the full method table, §4), `DEFAULTS` (settings defaults, §7), `LABELS`, `HORIZON = 0.833`, `J2000_OFFSET_DAYS = 10957.5`, MS per day/hour/minute, sun-position coefficients, high-lat factors, `INVALID_TIME = "-----"`. |
| `praytime/trig.py` | Degree trig: `dtr`, `rtd`, `sin`, `cos`, `tan`, `asin`, `acos`, `atan`, `acot`, `atan2`, `mod`. All take/return **degrees**; range errors return `nan` (§8.1, §9). |
| `praytime/astro.py` | Pure functions `sun_position(time, utc_ms, lng)`, `mid_day(...)`, `angle_time(...)`, `asr_angle(...)`, `julian_offset(...)` (§8). |
| `praytime/highlat.py` | `adjust_high_lats(times, settings, value_fn) -> bool` and `adjust_time(...)` returning the clamped time and an `adjusted` flag (§6, §8.9). |
| `praytime/formatting.py` | `round_time(ms, rounding)`, `format_time(ms, settings)`, `time_to_string(ms, fmt, settings)`, `parse_value(x)`, `is_min(x)` (§6.5, §6.6). |
| `praytime/methods.py` | `resolve_method(methods, name) -> dict` implementing `defaults`-then-method merge; `get_methods()` accessor. |
| `praytime/praytime.py` | The `PrayTime` class: constructor, chainable setters, `times`, `get_times`, `compute_times`, and the pipeline that wires the modules together. |
| `tests/` | pytest suite (§11). |

> Design note: the astronomical and formatting logic is split into small pure
> functions to make unit testing and parity checking straightforward. The public
> surface and observable behavior are exactly those of the single JS class; the split
> is an internal organization decision only.

---

## 3. Public Python API

The port keeps the JavaScript **constructor + chainable setters** ergonomics because
it is idiomatic enough in Python (returning `self`) and makes drop-in translation of
examples trivial. All setter methods return `self` so calls chain:

```python
praytime = PrayTime("ISNA").location([43.4643, -80.5204]).timezone("America/Toronto")
times = praytime.times([2025, 2, 21])
```

### 3.1 Class and constructor

```python
class PrayTime:
    def __init__(self, method: str = "MWL") -> None:
        ...
```

| Item | Behavior |
|---|---|
| Parameter | `method: str`, key into the method table. Default `"MWL"`. |
| Effect | Initializes `self.methods` (deep copy of the module `METHODS` table so instances can add/override methods without affecting others), `self.settings` (copy of `DEFAULTS`, §7), `self.labels` (copy of `LABELS`), `self._adjusted = None` (the stateful high-lat flag, §9.4), then calls `self.method(method)`. |
| Unknown method | JS: `this.methods[method]` is `undefined` and `Object.assign(this.settings, undefined)` is a no-op, so only `defaults` are applied. Python: mirror this — applying an unknown method applies only `defaults` (do not raise). Document as a deliberate parity choice; see §12. |

### 3.2 Chainable setters (all return `self`)

| Python method | Signature | Behavior |
|---|---|---|
| `method` | `method(self, method: str) -> "PrayTime"` | `self.set(self.methods["defaults"]); self.set(self.methods.get(method, {})); return self`. Applies `defaults` first, then the named method's overrides. |
| `adjust` | `adjust(self, params: Mapping[str, Any]) -> "PrayTime"` | Alias for `set(params)`. Merges arbitrary calculation parameters (`fajr`, `isha`, `maghrib`, `midnight`, `dhuhr`, `asr`, `highLats`, …). |
| `location` | `location(self, location: Sequence[float]) -> "PrayTime"` | Sets `{"location": [lat, lng]}` (degrees). Store as a **list** to preserve JS mutation semantics. |
| `timezone` | `timezone(self, timezone: str) -> "PrayTime"` | Sets `{"timezone": <IANA string>}`. Does **not** touch `utcOffset`. |
| `tune` | `tune(self, tune: Mapping[str, float]) -> "PrayTime"` | Sets `{"tune": ...}`; per-prayer offsets in **minutes** (fractions allowed). |
| `round` | `round(self, rounding: str = "nearest") -> "PrayTime"` | Sets `{"rounding": ...}`: `"nearest"`, `"up"`, `"down"`, `"none"`. |
| `format` | `format(self, format: Union[str, Callable[[int], Any]]) -> "PrayTime"` | Sets `{"format": ...}`: `"24h"`, `"12h"`, `"12H"`, `"x"`, `"X"`, or a callable `timestamp_ms -> Any`. |
| `set` | `set(self, settings: Mapping[str, Any]) -> "PrayTime"` | `self.settings.update(settings); return self`. The generic merge used by every setter. |
| `utc_offset` | `utc_offset(self, utc_offset: Union[float, str] = "auto") -> "PrayTime"` | If it is a number with `abs(value) < 16`, multiply by 60 (hours → minutes). Then set `timezone = "UTC"`, then `utcOffset = value`. Returns `self`. |
| `set_method` | `set_method(self, method: str) -> None` | **Deprecated.** Calls `self.method(method)`; returns `None` (does not chain). |

> `round` and `format` shadow Python builtins as *method names*. This is acceptable
> because they are attributes of the instance, not module-level. Tests and examples
> must not accidentally call the builtins through the instance.

### 3.3 Getters

| Python method | Signature | Returns |
|---|---|---|
| `times` | `times(self, date: DateInput = 0) -> Dict[str, Union[str, int]]` | Primary computation entry point. |
| `get_times` | `get_times(self, date=None, location=None, timezone="auto", dst=0, format="24h") -> Dict[str, Union[str, int]]` | Backward-compatible wrapper. If `location` is falsy, delegates to `self.times(date)`. Otherwise sets location, `utc_offset`, and format, then calls `times`. |

`DateInput` is:

```python
DateInput = Union[int, float, datetime.date, datetime.datetime,
                  Tuple[int, int, int], List[int]]
```

#### `times(date)` input normalization

JS source:

```js
times(date = 0) {
    if (typeof date === 'number')
        date = new Date((date < 1000) ? Date.now() + date * 864e5 : date);
    if (date.constructor === Date)
        date = [date.getFullYear(), date.getMonth() + 1, date.getDate()];
    this.utcTime = Date.UTC(date[0], date[1] - 1, date[2]);
    ...
}
```

Python normalization rules:

| Input | Interpretation |
|---|---|
| omitted / `0` | `0 < 1000` → day offset 0 → **today** (host local date). |
| `int`/`float` `< 1000` | Day offset from **now**: `date.today() + timedelta(days=n)`; `n` may be fractional. |
| `int`/`float` `>= 1000` | Unix timestamp in **milliseconds**: `datetime.fromtimestamp(n/1000, tz=UTC).date()`. |
| `datetime.date` / `datetime.datetime` | Use `(year, month, day)`; any time-of-day is discarded. |
| `tuple`/`list` `(y, m, d)` | **Month is 1-based** (e.g. `[2025, 2, 21]` = 21 Feb 2025). Length must be exactly 3. |

After normalization, compute:

```python
utc_ms = calendar.timegm((y, m, d, 0, 0, 0)) * 1000   # midnight UTC in ms
```

Store as `self._utc_time` (JS `this.utcTime`). Note: **only the calendar date is
used**; the input's clock time never affects the result.

#### `get_times` (backward-compatible)

JS source:

```js
getTimes(date, location, timezone = 'auto', dst = 0, format = '24h') {
    if (!location) return this.times(date);
    const utcOffset = (timezone == 'auto') ? timezone : timezone + dst;
    this.location(location).utcOffset(utcOffset).format(format);
    return this.times(date);
}
```

Semantics:

- Third parameter `timezone` is a **numeric UTC offset** (or the string `"auto"`),
  **not** an IANA zone. `dst` (hours) is added to it: `-5, dst=1` → `-4`.
- If `timezone == "auto"`, `utc_offset("auto")` is called, which forces
  `timezone="UTC"` and `utcOffset="auto"` → the result is rendered in **UTC**.
  This is a JS quirk; the port preserves it (§12).

### 3.4 Returned dictionary

`times()` returns a `dict` with exactly these 8 keys, in this order:

```
"fajr", "sunrise", "dhuhr", "asr", "sunset", "maghrib", "isha", "midnight"
```

Values are:

- a formatted **string** (`"05:52"`, `"3:32 PM"`, `"-----"`) for string formats;
- an **int** for `"x"` (Unix ms) / `"X"` (Unix s);
- whatever the user's **format callable** returns.

Example (docs):

```python
{
    "fajr": "04:51", "sunrise": "06:03", "dhuhr": "12:06", "asr": "15:29",
    "sunset": "18:10", "maghrib": "18:11", "isha": "19:18", "midnight": "23:30",
}
```

### 3.5 Exposed public attributes

| Attribute | Type | Value |
|---|---|---|
| `methods` | `dict[str, dict]` | Per-instance copy of `METHODS`. Mutable: users may add methods, e.g. `praytime.methods["Algeria"] = {"fajr": 18, "isha": 17}` then `praytime.method("Algeria")`. |
| `settings` | `dict[str, Any]` | Full settings object (§7). |
| `labels` | `list[str]` | `["Fajr", "Sunrise", "Dhuhr", "Asr", "Sunset", "Maghrib", "Isha", "Midnight"]` (public, not used internally). |
| `_adjusted` | `bool \| None` | Internal stateful high-latitude flag (§9.4). Not part of the documented public API but observable via Jafari midnight. |

### 3.6 JS → Python name mapping

| JS | Python | Notes |
|---|---|---|
| `new PrayTime(method)` | `PrayTime(method="MWL")` | same class name |
| `method(m)` | `method(m)` | same |
| `adjust(p)` | `adjust(p)` | same |
| `location(l)` | `location(l)` | same |
| `timezone(tz)` | `timezone(tz)` | same |
| `tune(t)` | `tune(t)` | same |
| `round(r)` | `round(r="nearest")` | same |
| `format(f)` | `format(f)` | same |
| `set(s)` | `set(s)` | same |
| `utcOffset(o)` | `utc_offset(o="auto")` | snake_case |
| `getTimes(...)` | `get_times(...)` | snake_case |
| `times(d)` | `times(d=0)` | same |
| `setMethod(m)` | `set_method(m)` | deprecated; snake_case |
| `.methods` | `.methods` | same |
| `.settings` | `.settings` | same |
| `.labels` | `.labels` | same |
| `.utcTime` | `._utc_time` | internal, private in Python |
| `.adjusted` | `._adjusted` | internal, private in Python |
| `this.value(x)` | `parse_value(x)` | module function in `formatting.py` |
| `this.isMin(x)` | `is_min(x)` | module function |
| `this.mod(a,b)` | `mod(a,b)` | module function in `trig.py` |
| setting `highLats` | setting `highLats` | kept verbatim as a **string key** for parity |
| setting `utcOffset` | setting `utcOffset` | kept verbatim as a string key |

> **Settings keys keep their JS camelCase names** (`highLats`, `utcOffset`) because
> they are data values read by the algorithm and because users pass them through
> `adjust({...})`. Only the **public method names** are snake_cased. This keeps
> `praytime.adjust({"utcOffset": -300})` behaving identically to JS.

---

## 4. Calculation Methods

Defined verbatim in the constructor:

```js
this.methods = {
    MWL: { fajr: 18, isha: 17 },
    ISNA: { fajr: 15, isha: 15 },
    Egypt: { fajr: 19.5, isha: 17.5 },
    Makkah: { fajr: 18.5, isha: '90 min' },
    Karachi: { fajr: 18, isha: 18 },
    Tehran: { fajr: 17.7, maghrib: 4.5, midnight: 'Jafari' },
    Jafari: { fajr: 16, maghrib: 4, midnight: 'Jafari' },
    France: { fajr: 12, isha: 12 },
    Russia: { fajr: 16, isha: 15 },
    Malaysia: { fajr: 20, isha: 18 }, // JAKIM
    Singapore: { fajr: 20, isha: 18 },
    defaults: { isha: 14, maghrib: '1 min', midnight: 'Standard' }
};
```

### 4.1 Effective values after `defaults`-then-method merge

| Name | `fajr` (angle°) | `isha` | `maghrib` | `midnight` | Convention |
|---|---|---|---|---|---|
| `MWL` | 18 | 17° | `'1 min'` | `'Standard'` | Muslim World League |
| `ISNA` | 15 | 15° | `'1 min'` | `'Standard'` | Islamic Society of North America |
| `Egypt` | 19.5 | 17.5° | `'1 min'` | `'Standard'` | Egyptian General Authority of Survey |
| `Makkah` | 18.5 | `'90 min'` | `'1 min'` | `'Standard'` | Umm al-Qura (90 min after Maghrib) |
| `Karachi` | 18 | 18° | `'1 min'` | `'Standard'` | University of Islamic Sciences, Karachi |
| `Tehran` | 17.7 | 14° (inherited) | 4.5° | `'Jafari'` | Institute of Geophysics, Univ. of Tehran |
| `Jafari` | 16 | 14° (inherited) | 4° | `'Jafari'` | Leva Research Institute, Qom |
| `France` | 12 | 12° | `'1 min'` | `'Standard'` | Union des Organisations Islamiques de France |
| `Russia` | 16 | 15° | `'1 min'` | `'Standard'` | Spiritual Administration of Muslims of Russia |
| `Malaysia` | 20 | 18° | `'1 min'` | `'Standard'` | JAKIM (added 2026) |
| `Singapore` | 20 | 18° | `'1 min'` | `'Standard'` | Islamic Religious Council of Singapore |
| `defaults` | — | 14° | `'1 min'` | `'Standard'` | applied to **every** method first |

### 4.2 Ordering rule (critical)

`method(m)` is exactly:

```js
method(method) {
    return this.set(this.methods.defaults).set(this.methods[method]);
}
```

Therefore:

1. `defaults` (`isha: 14`, `maghrib: '1 min'`, `midnight: 'Standard'`) is applied first.
2. The named method overrides only the keys it defines.
3. **Tehran and Jafari define no `isha`**, so they inherit `isha: 14` (angle).
4. All methods without an explicit `midnight` inherit `'Standard'`; all without an
   explicit `maghrib` inherit `'1 min'`.
5. `MWL`/`ISNA`/`Egypt`/`Karachi`/`France`/`Russia`/`Malaysia`/`Singapore`/`Makkah`
   have no `maghrib` key, so Maghrib = Sunset + 1 minute.

> **Discrepancy note:** the online manual's method listing omits `midnight:'Jafari'`
> for Tehran/Jafari and does not list `Malaysia`. The **source is authoritative**;
> the port uses the source values.

### 4.3 Adding a method

```python
praytime.methods["Algeria"] = {"fajr": 18, "isha": 17}
praytime.method("Algeria")
```

Because `method()` applies `defaults` first then the (possibly partial) method dict,
a user-added method may also inherit defaults.

---

## 5. Madhab / Asr Options

Controlled by the `asr` setting (default `'Standard'`). The shadow-length factor is
resolved by `asrAngle`:

```js
asrAngle(asrParam, time) {
    const shadowFactor = { Standard: 1, Hanafi: 2 }[asrParam] || this.value(asrParam);
    const lat = this.settings.location[0];
    const decl = this.sunPosition(time).declination;
    return -this.arccot(shadowFactor + this.tan(Math.abs(lat - decl)));
}
```

| `asr` value | Meaning | Shadow factor `t` |
|---|---|---|
| `'Standard'` | Shafi'i, Maliki, Jafari, Hanbali | `1` |
| `'Hanafi'` | Hanafi school | `2` |
| numeric (`1.7`) or numeric string (`'1.7'`) | custom shadow factor | `parse_value(value)` |

Asr **angle** = `-acot(t + tan|lat − decl|)` (degrees). Asr time is computed by
`angle_time(asr_angle, seed)` using the default `direction = +1` (afternoon). The
negative sign cancels via the `-sin(angle)` term in the hour-angle formula (§8.4).

> Note: the JS `||` falls through when `{Standard:1,Hanafi:2}[asrParam]` is `undefined`
> **or** `0`. Since the mapped values are `1` and `2` this only matters for a custom
> factor of exactly `0`; the port mirrors the `or` short-circuit for parity.

---

## 6. High-Latitude Rules

Controlled by `highLats` (default `'NightMiddle'`). Supported values: `'None'`,
`'NightMiddle'`, `'OneSeventh'`, `'AngleBased'`.

```js
adjustHighLats(times) {
    const params = this.settings;
    if (params.highLats == 'None')
        return;

    this.adjusted = false;
    const night = 24 + times.sunrise - times.sunset;

    Object.assign(times, {
        fajr:    this.adjustTime(times.fajr,    times.sunrise, params.fajr,    night, -1),
        isha:    this.adjustTime(times.isha,    times.sunset,  params.isha,    night),
        maghrib: this.adjustTime(times.maghrib, times.sunset,  params.maghrib, night)
    });
}

adjustTime(time, base, angle, night, direction = 1) {
    const factors = {
        NightMiddle: 1 / 2,
        OneSeventh: 1 / 7,
        AngleBased: 1 / 60 * this.value(angle)
    };
    const portion = factors[this.settings.highLats] * night;
    const timeDiff = (time - base) * direction;
    if (isNaN(time) || timeDiff > portion) {
        time = base + portion * direction;
        this.adjusted = true;
    }
    return time;
}
```

### 6.1 Definitions and formulas

- **Night length**: `night = 24 + sunrise − sunset` (solar hours). Sunrise is the next
  morning, so `+24` shifts it forward. Example: sunrise 6, sunset 18 → `night = 12`.
- **Portion**: `portion = factor × night`, where the factor depends on `highLats`:

| `highLats` | Factor | Clamp rule (from `base`) |
|---|---|---|
| `'None'` | — | No adjustment (early return; `_adjusted` is **not** reset). |
| `'NightMiddle'` | `1/2` | Fajr = sunrise − night/2; Isha = sunset + night/2; Maghrib = sunset + night/2. |
| `'OneSeventh'` | `1/7` | Fajr = sunrise − night/7; Isha/Maghrib = sunset + night/7. |
| `'AngleBased'` | `(1/60) × parse_value(angle)` | e.g. fajr 18° → `0.30 × night`; Makkah isha `'90 min'` → `1.5 × night` (raw setting value). |

- **Direction**: Fajr uses `direction = -1` (measured back from sunrise); Isha and
  Maghrib use `direction = +1` (forward from sunset).
- **Clamping trigger**: `time` is `NaN`, or `(time - base) * direction > portion`.
  When triggered, `time = base + portion * direction` and `_adjusted = True`.

### 6.2 Pipeline order

`adjust_high_lats` runs **before** `update_times`. Consequently the `fajr`/`isha`/
`maghrib` **raw settings** (which may be strings such as `'1 min'`, `'90 min'`,
`'Standard'`) are the `angle` argument. `AngleBased` therefore calls `parse_value`
on them; `parse_value('90 min') == 90.0`, `parse_value('Standard') == 0.0`.

`maghrib` is adjusted as well (even though it is usually overridden later by the
`'1 min'` interval) so that Maghrib always falls between Sunset and Isha during
abnormal periods, per the docs.

---

## 7. Complete Settings Object (Defaults)

```js
this.settings = {
    dhuhr: '0 min',
    asr: 'Standard',
    highLats: 'NightMiddle',
    tune: {},
    format: '24h',
    rounding: 'nearest',
    utcOffset: 'auto',
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    location: [0, -(new Date()).getTimezoneOffset() / 4],
    iterations: 1
};
```

| Setting | Default | Meaning |
|---|---|---|
| `fajr`, `isha`, `maghrib`, `midnight` | set by `method()` | angle (number) or `'<n> min'` interval string; `midnight` ∈ `{'Standard','Jafari'}` |
| `dhuhr` | `'0 min'` | minutes added after solar noon |
| `asr` | `'Standard'` | `'Standard'`, `'Hanafi'`, or numeric shadow factor |
| `highLats` | `'NightMiddle'` | `'None'` / `'NightMiddle'` / `'OneSeventh'` / `'AngleBased'` |
| `tune` | `{}` | per-prayer minute offsets |
| `format` | `'24h'` | output format |
| `rounding` | `'nearest'` | `'nearest'` / `'up'` / `'down'` / `'none'` |
| `utcOffset` | `'auto'` | minutes when numeric, else the string `'auto'` |
| `timezone` | host IANA zone | used when `utcOffset == 'auto'` |
| `location` | `[0, -host_utc_offset_minutes/4]` | `[latitude, longitude]`; default longitude approximates the host offset (60 min ↔ 15° → offset_min/4 = degrees). E.g. UTC+3 → host offset `-180` min → lng `45`. |
| `iterations` | `1` | number of `process_times` refinement passes |

### 7.1 Python default for `timezone` and `location`

JS reads the host via `Intl.DateTimeFormat().resolvedOptions().timeZone` and
`new Date().getTimezoneOffset()`. Python equivalent:

```python
import datetime as _dt
now = _dt.datetime.now().astimezone()
default_tz = now.tzinfo.key if hasattr(now.tzinfo, "key") else "UTC"
offset_min = now.utcoffset().total_seconds() / 60      # minutes east of UTC
default_lng = -offset_min / 4
```

If the host zone cannot be determined (e.g. fixed-offset tzinfo without `.key`),
fall back to `"UTC"` and `default_lng = -offset_min / 4`. This only affects the
defaults; the docs' examples always set an explicit location/timezone.

---

## 8. Astronomical Algorithm Specification

Everything below is local **solar time in hours** unless stated otherwise. Degrees
are used for all trig (helpers convert to radians internally).

### 8.1 Degree-based trigonometry helpers

```js
dtr = (d) => d * Math.PI / 180;
rtd = (r) => r * 180 / Math.PI;
sin = (d) => Math.sin(this.dtr(d));
cos = (d) => Math.cos(this.dtr(d));
tan = (d) => Math.tan(this.dtr(d));
arcsin = (d) => this.rtd(Math.asin(d));
arccos = (d) => this.rtd(Math.acos(d));
arctan = (d) => this.rtd(Math.atan(d));
arccot = (x) => this.rtd(Math.atan(1 / x));
arctan2 = (y, x) => this.rtd(Math.atan2(y, x));
```

Port requirements:

- All functions take/return **degrees**.
- `acot(x) = degrees(atan(1/x))`.
- **Input coercion**: JS multiplication coerces its operand; a non-numeric string
  (e.g. `'1 min'`) yields `NaN`. Python must reproduce this: the trig helpers first
  attempt a **full** numeric conversion (`float(x)`); on failure they use `nan` and
  return `nan`. This is distinct from `parse_value` (§6.6), which parses only the
  **leading** number.
- **Range errors**: `math.asin`/`math.acos` raise `ValueError` outside `[-1, 1]`.
  JS `Math.asin`/`Math.acos` return `NaN`. The port's `asin`/`acos` **catch
  `ValueError` and return `nan`** (§9.2).
- `mod(a, b)` returns the JS positive modulo: `((a % b) + b) % b`. (For positive `b`
  Python's `%` already matches, but keep the helper for clarity/parity.)
- `atan2(y, x)` = `degrees(math.atan2(y, x))`.

### 8.2 Julian day offset and sun position

```js
sunPosition(time) {
    const lng = this.settings.location[1];
    const D = this.utcTime / 864e5 - 10957.5 + this.value(time) / 24 - lng / 360;

    const g = this.mod(357.529 + 0.98560028 * D, 360);
    const q = this.mod(280.459 + 0.98564736 * D, 360);
    const L = this.mod(q + 1.915 * this.sin(g) + 0.020 * this.sin(2 * g), 360);
    const e = 23.439 - 0.00000036 * D;
    const RA = this.mod(this.arctan2(this.cos(e) * this.sin(L), this.cos(L)) / 15, 24);

    return {
        declination: this.arcsin(this.sin(e) * this.sin(L)),
        equation: q / 15 - RA,
    }
}
```

Step by step:

1. `lng` = `settings["location"][1]`.
2. **Julian day offset** `D`:
   - `self._utc_time / 86_400_000` = whole days since Unix epoch (1970-01-01).
   - `- 10957.5` converts from the Unix epoch to **J2000.0** (JD 2451545.0; because
     `2451545.0 − 2440587.5 = 10957.5`). Compute this constant as
     `2451545.0 - 2440587.5` in code, not a literal, per the research recommendation.
   - `+ parse_value(time) / 24` adds the fractional local solar day (seed hours).
   - `- lng / 360` converts longitude to a day fraction (360° = 24 h).
3. **Mean anomaly** `g = mod(357.529 + 0.98560028 * D, 360)`.
4. **Mean longitude** `q = mod(280.459 + 0.98564736 * D, 360)`.
5. **Ecliptic longitude** `L = mod(q + 1.915 * sin(g) + 0.020 * sin(2*g), 360)`.
6. **Obliquity** `e = 23.439 - 0.00000036 * D`.
7. **Right ascension** `RA = mod(atan2(cos(e)*sin(L), cos(L)) / 15, 24)` (hours).
8. **Declination** `δ = asin(sin(e) * sin(L))` (degrees).
9. **Equation of time** `EqT = q/15 - RA` (hours).

This is the USNO approximate solar-coordinate algorithm (accuracy ≈ 1 arcminute
within two centuries of 2000); the `R` (Earth–Sun distance) term is not used.

### 8.3 Dhuhr / solar noon (`midDay`)

```js
midDay(time) {
    const eqt = this.sunPosition(time).equation;
    const noon = this.mod(12 - eqt, 24);
    return noon;
}
```

`Dhuhr = mod(12 − EqT, 24)` hours of local solar time. The timezone/longitude
correction is applied later in `convert_times` (via the `−lng/15` shift and the
`utcTime` timestamp), not here.

### 8.4 Sun altitude / twilight time (`angleTime`)

```js
angleTime(angle, time, direction = 1) {
    const lat = this.settings.location[0];
    const decl = this.sunPosition(time).declination;
    const numerator = -this.sin(angle) - this.sin(lat) * this.sin(decl);
    const diff = this.arccos(numerator / (this.cos(lat) * this.cos(decl))) / 15;
    return this.midDay(time) + diff * direction;
}
```

Implements the standard hour-angle formula:

```
cos(H) = (−sin(α) − sin(φ)·sin(δ)) / (cos(φ)·cos(δ))
T(α)   = H / 15                        (hours)
time   = Dhuhr ± T(α)
```

- `α` = `angle` (positive degrees below the horizon: 18 for Fajr, 0.833 for
  sunrise/sunset). The leading `−sin(α)` accounts for the angle being below the
  horizon.
- `direction = -1` for morning prayers; `+1` (default) for afternoon.
- If `cos(H)` leaves `[−1, 1]` (polar day/night), `acos` returns `nan`, which
  propagates and is resolved by `adjust_high_lats` or rendered `'-----'`.
- `angle` may be a non-numeric interval string; the trig coercion (§8.1) then yields
  `nan`, matching JS.

### 8.5 Sunrise / Sunset

Same `angle_time` with `angle = HORIZON = 0.833` (refraction + solar radius),
Sunrise with `direction = -1`, Sunset with `+1`. Elevation is ignored.

### 8.6 Asr

See §5. Angle = `-acot(t + tan|φ − δ|)`, then `angle_time(angle, seed)` with
`direction = +1`.

### 8.7 Maghrib / Isha

Default: computed as twilight angles `angle_time(maghrib)` / `angle_time(isha)`,
then **overridden** in `update_times` when the setting is a `'<n> min'` interval
string (Maghrib relative to **Sunset**, Isha relative to **Maghrib**). Default
`maghrib: '1 min'` applies to all standard methods; Makkah uses `isha: '90 min'`.

### 8.8 Midnight (Standard vs Jafari)

- **Standard** (default and all methods except Tehran/Jafari): `midnight = midDay + 12`
  (astronomical midnight).
- **Jafari**: midpoint between Sunset and **next Fajr** (legal midnight), computed in
  `update_times` (§8.10) using the seed `29` and the `_adjusted` flag.

### 8.9 Compute pipeline (`computeTimes`)

```js
computeTimes() {
    let times = {
        fajr: 5, sunrise: 6, dhuhr: 12, asr: 13,
        sunset: 18, maghrib: 18, isha: 18, midnight: 24
    };
    for (let i = 0; i < this.settings.iterations; i++)
        times = this.processTimes(times);
    this.adjustHighLats(times);
    this.updateTimes(times);
    this.tuneTimes(times);
    this.convertTimes(times);
    return times;
}
```

- Seed times (hours, local solar time): `fajr 5, sunrise 6, dhuhr 12, asr 13,
  sunset 18, maghrib 18, isha 18, midnight 24`.
- `iterations` (default `1`) re-seeds the sun-position `time` with the previous pass
  result, refining accuracy.

#### `processTimes`

```js
processTimes(times) {
    const params = this.settings;
    const horizon = 0.833;
    return {
        fajr:    this.angleTime(params.fajr, times.fajr, -1),
        sunrise: this.angleTime(horizon, times.sunrise, -1),
        dhuhr:   this.midDay(times.dhuhr),
        asr:     this.angleTime(this.asrAngle(params.asr, times.asr), times.asr),
        sunset:  this.angleTime(horizon, times.sunset),
        maghrib: this.angleTime(params.maghrib, times.maghrib),
        isha:    this.angleTime(params.isha, times.isha),
        midnight: this.midDay(times.midnight) + 12
    }
}
```

### 8.10 `updateTimes` — intervals and midpoint overrides

```js
updateTimes(times) {
    const params = this.settings;
    if (this.isMin(params.maghrib))
        times.maghrib = times.sunset + this.value(params.maghrib) / 60;
    if (this.isMin(params.isha))
        times.isha = times.maghrib + this.value(params.isha) / 60;
    if (params.midnight == 'Jafari') {
        const nextFajr = this.angleTime(params.fajr, 29, -1) + 24;
        times.midnight = (times.sunset + (this.adjusted ? times.fajr + 24 : nextFajr)) / 2;
    }
    times.dhuhr += this.value(params.dhuhr) / 60;
}
```

Order and exact semantics:

1. **Maghrib interval**: if `'min' in str(maghrib)`, `maghrib = sunset + minutes/60`.
2. **Isha interval**: if `'min' in str(isha)`, `isha = maghrib + minutes/60`
   (relative to **Maghrib**, not Sunset).
3. **Jafari midnight**: next-day Fajr approximated as
   `angle_time(fajr, 29, -1) + 24` (magic seed `29`). If `_adjusted` is truthy, use
   `times.fajr + 24` instead. Midnight = mean of Sunset and that Fajr.
4. **Dhuhr offset**: `dhuhr += parse_value(dhuhr)/60` (default `'0 min'` → +0).

### 8.11 `tuneTimes`

```js
tuneTimes(times) {
    const mins = this.settings.tune
    for (let i in times)
        if (i in mins)
            times[i] += mins[i] / 60;
}
```

Per-prayer minute offsets; fractions allowed. Applied to any matching key.

### 8.12 `convertTimes` — hours → timestamp

```js
convertTimes(times) {
    const lng = this.settings.location[1];
    for (let i in times) {
        const time = times[i] - lng / 15;
        const timestamp = this.utcTime + Math.floor(time * 36e5);
        times[i] = this.roundTime(timestamp);
    }
}
```

- Convert local solar hours to UTC by subtracting `lng/15` hours (15° = 1 h).
- `self._utc_time` = midnight UTC of the date in ms.
- Add `floor(time * 3_600_000)` integer ms; then round (§8.13).

### 8.13 `roundTime`

```js
roundTime(timestamp) {
    const rounding = { up: 'ceil', down: 'floor', nearest: 'round' }[this.settings.rounding];
    if (!rounding)
        return timestamp;
    const OneMinute = 6e4;
    return Math[rounding](timestamp / OneMinute) * OneMinute;
}
```

| `rounding` | JS fn | Python | Result |
|---|---|---|---|
| `'up'` | `Math.ceil` | `math.ceil` | next minute |
| `'down'` | `Math.floor` | `math.floor` | this minute |
| `'nearest'` (default) | `Math.round` | `js_round` (see below) | nearest minute |
| other / `'none'` | — | — | raw ms (no rounding) |

`js_round(x) = math.floor(x + 0.5)` reproduces JS `Math.round` (half rounds toward
+∞; Python's built-in `round` uses banker's rounding and **must not** be used).
Timestamps here are positive, so `floor(x+0.5)` is exact for JS parity.

---

## 9. Time Handling

### 9.1 Formatting

```js
formatTime(timestamp) {
    const format = this.settings.format;
    const InvalidTime = '-----';
    if (isNaN(timestamp)) return InvalidTime;
    if (typeof format === 'function') return format(timestamp);
    if (format.toLowerCase() == 'x')
        return Math.floor(timestamp / ((format == 'X') ? 1000 : 1));
    return this.timeToString(timestamp, format);
}

timeToString(timestamp, format) {
    const utcOffset = this.settings.utcOffset;
    const date = new Date(timestamp + (utcOffset == 'auto' ? 0 : utcOffset) * 6e4);
    const str = date.toLocaleTimeString('en-US', {
        timeZone: this.settings.timezone,
        hour12: format == '24h' ? false : true,
        hour: format == '24h' ? '2-digit' : 'numeric',
        minute: '2-digit'
    });
    return format == '12H' ? str.replace(/ ?[AP]M/, '') : str;
}
```

| `format` | Output | Example (test: asr) |
|---|---|---|
| `'24h'` (default) | `HH:MM`, `hour12:false`, `hour:'2-digit'` | `'15:32'` |
| `'12h'` | 12-hour with suffix, `hour12:true`, `hour:'numeric'` (no leading zero) | `'3:32 PM'` |
| `'12H'` | 12-hour, AM/PM stripped | `'3:32'` |
| `'x'` | Unix **milliseconds**: `floor(ts)` | `1740169920000` |
| `'X'` | Unix **seconds**: `floor(ts/1000)` | `1740169920` |
| callable | whatever it returns (receives the ms `int`) | — |
| `nan` timestamp | `'-----'` | — |

### 9.2 UTC offset / timezone rules

- Default `utcOffset: 'auto'` → display uses `settings.timezone` (an IANA name):
  `datetime.fromtimestamp(ts/1000, tz=ZoneInfo(settings["timezone"]))`.
- Numeric `utcOffset` (set via `utc_offset()`) → `settings["timezone"]` is forced to
  `"UTC"` and the numeric offset (minutes) is added to the timestamp before a
  UTC-rendered display:
  `dt = datetime.fromtimestamp((ts + offset_min * 60000)/1000, tz=timezone.utc)`.
- Minute rounding happens **before** formatting (§8.13).
- `utc_offset(n)`: if `isinstance(n, (int,float))` and `abs(n) < 16`, `n *= 60`; then
  `timezone = "UTC"`; then `utcOffset = n`. Calling `utc_offset("auto")` sets
  `timezone="UTC"` and `utcOffset="auto"` (a quirk preserved for parity).

### 9.3 String rendering

For a `datetime` `dt` in the resolved zone:

- `'24h'`: `f"{dt.hour:02d}:{dt.minute:02d}"`.
- `'12h'`: `h = dt.hour % 12 or 12`; `ampm = "AM" if dt.hour < 12 else "PM"`;
  `f"{h}:{dt.minute:02d} {ampm}"`.
- `'12H'`: same as `'12h'` without the `" AM"/" PM"` suffix.

Do **not** use `strftime('%-I')` (glibc-only) or `%I` (adds a leading zero).
Compute the hour arithmetically as above.

### 9.4 Interval parsing (`value` / `isMin`)

```js
value(str) { return +String(str).split(/[^0-9.+-]/)[0]; }
isMin(str) { return String(str).indexOf('min') != -1; }
```

Python equivalents:

```python
import re
_NUM_RE = re.compile(r"[^0-9.+-]")

def parse_value(x):
    if isinstance(x, (int, float)):
        return float(x)
    head = _NUM_RE.split(str(x), maxsplit=1)[0]
    try:
        return float(head)
    except ValueError:
        return 0.0

def is_min(x):
    return "min" in str(x)
```

| Input | JS `value` | Python `parse_value` |
|---|---|---|
| `'90 min'` | `90` | `90.0` |
| `'1 min'` | `1` | `1.0` |
| `'0 min'` | `0` | `0.0` |
| `18` | `18` | `18.0` |
| `4.5` | `4.5` | `4.5` |
| `'-5'` | `-5` | `-5.0` |
| `'min'` (bare) | `+'' = 0` | `0.0` |
| `'Standard'` | `+'' = 0` | `0.0` |
| `'Jafari'` | `0` | `0.0` |
| `'1.5e3'` | `1.5` (JS splits at `e`) | `1.5` (same split) |

> JS applies unary `+` to the head; `+'' === 0` and `+'abc'` (unstripped) would be
> `NaN`, but the split always yields either a numeric prefix or `''`, so `0` is the
> only fallback. Python's `float('')` raises, hence the explicit `0.0` fallback.

### 9.5 Sentinel values

- Invalid/NaN time string: `INVALID_TIME = "-----"`.
- Interval strings: `'<n> min'`; `is_min` is a substring test.

---

## 10. Error Handling & Edge Cases

### 10.1 Invalid dates

- Wrong tuple/list length → raise `ValueError("date must be (year, month, day)")`.
- Month/day out of range → Python `datetime` construction raises; surface as
  `ValueError`. (JS `Date.UTC` silently normalizes overflow; the port chooses stricter
  validation — see §12.)
- `date=None` passed explicitly to `get_times` → `times(None)` → treat as `0`
  (today), matching JS `getTimes()` calling `times(undefined)` → default `0`.

### 10.2 Extreme latitudes — `acos`/`asin` domain errors

- JS `Math.acos`/`Math.asin` return `NaN` outside `[-1, 1]`.
- Python `math.acos`/`math.asin` raise `ValueError`. The port's `acos`/`asin`
  **catch `ValueError` and return `float("nan")`** so that downstream `isnan` logic
  (high-latitude clamping, `'-----'` rendering) behaves identically.
- **Do not clamp.** Clamping to `[-1, 1]` would change Fajr/Isha at high latitudes
  where JS intentionally produces `NaN` and relies on `adjust_high_lats`.

### 10.3 `< 1000` day-offset heuristic

A numeric `date < 1000` is a **day offset from now**, not a timestamp. So `times(7)`
= one week from today, while `times(1000)` is a ms timestamp (1970-01-01). Negative
values are always offsets. This is preserved exactly.

### 10.4 `utcOffset < 16` heuristic

`utc_offset(n)` treats `|n| < 16` as **hours** (×60) and larger values as
**minutes**. Thus `-5 → -300`, `-4.5 → -270`, `3.5 → 210`, but `20 → 20 minutes`.
`utc_offset()` also forces `timezone = "UTC"`. Preserved exactly.

### 10.5 Stateful `_adjusted` flag

- `adjust_high_lats` sets `_adjusted = False` **only when `highLats != 'None'`**
  (after the early return). With `'None'`, the flag retains its previous value
  (initially `None`).
- `_adjusted` is consumed by the Jafari midnight branch.
- The port **mirrors this statefulness** for numerical parity (see §12.2). It is
  initialized to `None` in `__init__`.

### 10.6 Elevation

Not supported; `HORIZON = 0.833` is constant.

### 10.7 Only Y/M/D of the input date is used

Any time-of-day on a `datetime` is discarded; `_utc_time` is midnight UTC.

### 10.8 1-based array months

`times([2025, 2, 21])` = 21 Feb 2025 (the test comment says "Fab 21, 2025").

### 10.9 IANA vs numeric timezone

`timezone('America/Toronto')` uses `zoneinfo`; `utc_offset(n)` forces `"UTC"`.
`utc_offset()` **overwrites** `timezone`; `timezone()` does **not** reset
`utcOffset`. Last call wins for the setting it touches.

### 10.10 `get_times` third parameter is an offset

`get_times(date, loc, -5, 1)` = UTC−5 + 1 h DST = UTC−4. Passing an IANA string there
would break the arithmetic (mirroring JS). Document; the port does not "fix" it.

### 10.11 Default location longitude

Derived from the host's current UTC offset: `-offset_minutes/4`. At latitude 0
(default) times are still produced but are geographically meaningless; callers should
set a location.

### 10.12 Iteration count

`iterations = 1` default; increasing re-seeds and refines.

### 10.13 Makkah Ramadan rule

Not implemented (matches source).

### 10.14 Shared-instance mutation

The JS Jest suite mutates one instance across tests. The port's tests use fresh
instances to avoid order dependence; the library itself keeps no cross-call
computation state other than `_adjusted` and `_utc_time`.

### 10.15 Unknown method name

Applies only `defaults` (no exception), matching `Object.assign(settings, undefined)`.

---

## 11. Constants & Data Tables

| Constant | Where used | Value | Meaning |
|---|---|---|---|
| `HORIZON` | `process_times` | `0.833` | Sunrise/Sunset horizon angle (refraction + solar radius), degrees |
| `J2000_OFFSET_DAYS` | `sun_position` | `2451545.0 - 2440587.5 = 10957.5` | Days from Unix epoch to J2000.0 |
| `MS_PER_DAY` | `times`, `sun_position` | `86_400_000` (`864e5`) | ms per day |
| `MS_PER_HOUR` | `convert_times` | `3_600_000` (`36e5`) | ms per hour |
| `MS_PER_MINUTE` | `round_time`, `time_to_string` | `60_000` (`6e4`) | ms per minute |
| `MEAN_ANOMALY_BASE` | `sun_position` | `357.529` | `g` constant |
| `MEAN_ANOMALY_RATE` | `sun_position` | `0.98560028` | `g` per day |
| `MEAN_LONGITUDE_BASE` | `sun_position` | `280.459` | `q` constant |
| `MEAN_LONGITUDE_RATE` | `sun_position` | `0.98564736` | `q` per day |
| `EQ_CENTER_1` | `sun_position` | `1.915` | Equation-of-center amplitude (`sin g`) |
| `EQ_CENTER_2` | `sun_position` | `0.020` | Equation-of-center amplitude (`sin 2g`) |
| `OBLIQUITY_J2000` | `sun_position` | `23.439` | Obliquity of ecliptic at J2000, degrees |
| `OBLIQUITY_RATE` | `sun_position` | `0.00000036` | Obliquity change per day |
| `SHADOW_STANDARD` | `asr_angle` | `1` | Standard shadow factor |
| `SHADOW_HANAFI` | `asr_angle` | `2` | Hanafi shadow factor |
| `HL_NIGHT_MIDDLE` | `adjust_time` | `1/2` | NightMiddle portion factor |
| `HL_ONE_SEVENTH` | `adjust_time` | `1/7` | OneSeventh portion factor |
| `HL_ANGLE_BASED` | `adjust_time` | `1/60 * parse_value(angle)` | AngleBased portion factor |
| `JAFARI_SEED_HOUR` | `update_times` | `29` | Fixed time-of-day seed for next-day Fajr |
| `NOON_OFFSET` | `mid_day`, midnight | `12` | Half-day / noon offset |
| `HOURS_PER_DAY` | many | `24` | Hours per day |
| `DEG_PER_HOUR` | `convert_times`, `angle_time`, `sun_position` | `15` | 15°/h |
| `INVALID_TIME` | `format_time` | `"-----"` | NaN placeholder |
| `SEED_FAJR..SEED_MIDNIGHT` | `compute_times` | `5,6,12,13,18,18,18,24` | Initial solar-time seeds |
| `LABELS` | `.labels` | `['Fajr','Sunrise','Dhuhr','Asr','Sunset','Maghrib','Isha','Midnight']` | Prayer labels |

Method table numbers: `18/17`, `15/15`, `19.5/17.5`, `18.5` + `'90 min'`, `18/18`,
`17.7` (+ inherited isha 14) + `4.5` maghrib + `'Jafari'` midnight, `16` (+ inherited
isha 14) + `4` maghrib + `'Jafari'` midnight, `12/12`, `16/15`, `20/18`, `20/18`;
`defaults` = isha `14`, maghrib `'1 min'`, midnight `'Standard'`.

---

## 12. Testing Strategy

### 12.1 Reference test data (from `tests/test.js`, quoted)

Location: **Waterloo, ON** `lat = 43.4643`, `lng = -80.5204`; date `[2025, 2, 21]`
(21 Feb 2025); timezone `'America/Toronto'`; method `'ISNA'`.

```js
// default 24h
times.fajr    === '05:52'
times.dhuhr   === '12:36'
times.asr     === '15:32'
times.maghrib === '18:02'

// formats (asr)
format('x').getTimes(date).asr  === 1740169920000
format('X').getTimes(date).asr  === 1740169920
format('12h').getTimes(date).asr === '3:32 PM'
format('12H').getTimes(date).asr === '3:32'
format('24h').getTimes(date).asr === '15:32'

// utc offsets (fajr)
utcOffset(-4.5).getTimes(date).fajr === '06:22'
utcOffset(-300).getTimes(date).fajr === '05:52'

// rounding (asr)
round('down').getTimes(date).asr    === '15:32'
round('up').getTimes(date).asr      === '15:33'
round('nearest').getTimes(date).asr === '15:32'

// adjust
adjust({ fajr: 19.7, dhuhr: '11 min' }).getTimes(date)
  → fajr === '05:26', dhuhr === '12:47'

// tune
tune({ asr: 11, maghrib: 4.5 }).getTimes(date)
  → asr === '15:43', maghrib === '18:07'
```

> **Test-suite order dependence.** The JS test mutates a single shared instance
> (`.method`, `.location`, `.timezone`, `.format`, `.round`, `.utcOffset`, `.tune`,
> `.adjust`). The Python tests MUST use a **fresh instance per test** and re-apply the
> base setup (`method('ISNA').location([lat,lng]).timezone('America/Toronto')`), then
> the specific mutation. This reproduces the intended values without relying on Jest
> execution order.

### 12.2 Proposed pytest cases

`tests/test_reference.py`

- `test_prayer_times`: fajr/dhuhr/asr/maghrib exact strings.
- `test_time_formats`: asr for `x`, `X`, `12h`, `12H`, `24h`.
- `test_timezones`: `utc_offset(-4.5)` → fajr `'06:22'`; `utc_offset(-300)` → `'05:52'`.
- `test_rounding`: `down`/`up`/`nearest` on asr.
- `test_adjust`: `adjust({"fajr": 19.7, "dhuhr": "11 min"})` → fajr `'05:26'`, dhuhr `'12:47'`.
- `test_tune`: `tune({"asr": 11, "maghrib": 4.5})` → asr `'15:43'`, maghrib `'18:07'`.

`tests/test_methods.py`

- For each of the 11 methods assert the effective merged parameter dict (fajr/isha/
  maghrib/midnight), especially:
  - Tehran/Jafari inherit `isha == 14` and set `midnight == 'Jafari'`.
  - All others inherit `maghrib == '1 min'` and `midnight == 'Standard'`.
  - Makkah `isha == '90 min'`.
  - `Malaysia` and `Singapore` both `fajr == 20, isha == 18`.
- `test_add_custom_method`: add `{"fajr": 18, "isha": 17}` and select it.
- `test_unknown_method`: selecting a missing name applies only defaults (no raise).

`tests/test_highlat.py`

- `highLats='None'`: polar latitude (e.g. `lat=70`) in June/December yields `'-----'`
  for the affected prayers (Fajr/Isha), because `nan` survives.
- `highLats='NightMiddle'` / `'OneSeventh'` / `'AngleBased'`: no `'-----'`; values are
  clamped to `base ± portion`.
- `test_night_length`: verify `night = 24 + sunrise − sunset`.
- `test_angle_based_makkah`: `isha '90 min'` → factor `1.5`.
- `test_adjusted_statefulness`: exercise a Jafari midnight after a high-lat
  computation to lock the `_adjusted` behavior (regression guard for the quirk).

`tests/test_formatting.py`

- 24h zero-padding, 12h `"3:32 PM"` (no leading zero), 12H strip, `x`/`X` ints,
  callable format receives the rounded ms int, `nan` → `'-----'`.
- `parse_value` table from §9.4; `is_min` cases.
- `js_round` half-up behavior (`0.5→1`, `1.5→2`, `2.5→3`).

`tests/test_date_inputs.py`

- `times()` with no args = today.
- `times(0)` = today; `times(7)` = today + 7 days.
- `times(1740169920000)` (ms ≥ 1000) = correct calendar date.
- `datetime.date`, `datetime.datetime` (time discarded), tuple/list `(y, m, d)`
  (1-based month).
- Invalid tuple length raises `ValueError`.

`tests/test_snapshot.py`

- Golden JSON snapshots (checked into `tests/golden/`) for a matrix of:
  - methods × dates (solstices/equinoxes) × latitudes (`0, 21.4, 43.46, 51.5, 64, 70`)
  - both madhabs, all four high-lat rules.
- Generate goldens from the **JS library** (Node) once for maximum fidelity, then
  assert the Python output equals the golden strings exactly.

### 12.3 Tolerance for float comparisons

- **Final outputs are strings or ints.** String equality is exact; `x`/`X` are exact
  integers (`floor`).
- **Intermediate astronomical values**: when unit-testing `sun_position`, `mid_day`,
  `angle_time`, `asr_angle` directly, compare against JS-computed values with
  `pytest.approx(rel=1e-9, abs=1e-9)`. The same double-precision operations in the
  same order should agree to ~1e-12, but `math` vs `Math` libm implementations can
  differ in the final ULP, so `1e-9` is a safe tolerance.
- **Minute-rounded strings** are robust to sub-millisecond differences except at
  exact `.5`-minute boundaries; the reference values are chosen away from those
  boundaries. If a golden ever lands exactly on a boundary, `js_round` already
  encodes the JS half-up rule, so exact equality is expected.

### 12.4 Golden/snapshot generation

Provide `tests/golden/generate.js` (Node, run manually) that imports the upstream
`src/praytime.js`, loops the matrix, and writes JSON. The Python snapshot test reads
the JSON and compares. This makes parity externally verifiable and independent of the
port's own math.

---

## 13. Porting Decisions & Rationale

### 13.1 Where Python **must match JS exactly** (numerical parity)

1. **Algorithm and operation order** in `sun_position`, `angle_time`, `mid_day`,
   `asr_angle`, `compute_times`, `update_times`, `convert_times`.
2. **`defaults`-then-method** merge order.
3. **`js_round` (half-up)** instead of Python's banker's rounding.
4. **`nan` propagation** from `acos`/`asin` domain errors instead of exceptions.
5. **`parse_value` leading-number semantics** and the `0.0` fallback for bare `'min'`
   / non-numeric strings (distinct from the trig helpers' full-parse → `nan`).
6. **`utc_offset` `< 16` heuristic** and the forced `timezone = "UTC"`.
7. **`get_times` third parameter as a numeric offset**, `dst` added, and the
   `'auto'` → UTC quirk.
8. **`_adjusted` statefulness** (not reset when `highLats == 'None'`; persists across
   calls) and the Jafari midnight branch.
9. **Magic seed `29`** for next-day Jafari Fajr.
10. **`0.833` horizon**, no elevation.
11. **Interval strings** (`'1 min'`, `'90 min'`) with `is_min` substring test.
12. **`'x'`/`'X'` choose ms vs seconds via case-sensitive `format == 'X'`** while the
    `'x'` test is case-insensitive.
13. **12h hour has no leading zero; 24h hour is zero-padded.**
14. **Rounding on the ms scale**, before formatting.
15. **Keys and key order** of the returned dict.
16. **Default location longitude** `-host_offset_minutes/4`.

### 13.2 Where Python intentionally **differs** from JS

| Area | JS behavior | Python decision | Rationale |
|---|---|---|---|
| Naming | camelCase methods (`getTimes`, `utcOffset`, `setMethod`) | snake_case primary (`get_times`, `utc_offset`, `set_method`) | PEP 8; the mapping table (§3.6) documents the correspondence. |
| Settings keys | camelCase (`highLats`, `utcOffset`) | **keep camelCase** strings | they are data consumed by `adjust({...})`; renaming would break drop-in parity. |
| Types | dynamic | full type hints; `dict[str, ...]`, tuples, `Callable` | static clarity, IDE support. |
| Invalid date | silently normalizes via `Date.UTC` | raise `ValueError` on malformed tuple / out-of-range date | fail fast; the research report recommends explicit behavior. |
| Exceptions | `NaN` everywhere, no throws | only `nan` where JS uses it; otherwise no exceptions from computation | capped to the places parity demands. |
| `utcOffset` heuristic | implicit | keep implicit but document; optionally add explicit `utc_offset_minutes` helper | drop-in parity by default. |
| Internals | instance fields mutated in place | private attributes (`_utc_time`, `_adjusted`); pure helper modules | testability; observable behavior unchanged. |
| Instance method table | shared by reference in JS (mutating one method leaks) | per-instance deep copy | avoids surprising cross-instance leakage; users can still mutate `praytime.methods` for that instance. |
| `methods` mutation | must be callable via `praytime.methods['X']=...` | kept as a plain mutable `dict` | exact same user workflow. |
| Immutability | none | `settings` stays mutable (required by `set`/`adjust`); returned `times` dict is fresh per call | matches JS; no shared returned dict. |
| Timezone display | host `Intl` database | `zoneinfo.ZoneInfo` (stdlib, 3.9+) | deterministic; no `Intl` quirks. |
| `12h` hours | host `toLocaleTimeString` (`numeric`) | arithmetic `hour % 12 or 12` | portable, deterministic (avoids `%I` leading zero / `%-I` glibc-only). |

### 13.3 Optional clean-ups (kept behind a flag or documented, not default)

- A `strict=True` *constructor* flag could reset `_adjusted = False` unconditionally
  and normalize invalid dates instead of raising. **Default is parity mode
  (`strict=False`)** so the reference outputs match. This is a suggestion, not
  required by the spec; if implemented, document it as non-default.
- Elevation and Makkah-120 should be considered *future extensions* only; the default
  port must not include them if parity is the priority.

### 13.4 Deliverable definition of done

1. `praytime` importable; `from praytime import PrayTime` works.
2. All `tests/test_reference.py` assertions pass with exact strings/ints.
3. Snapshot tests against JS-generated goldens pass for the full matrix.
4. `python -m pytest` green; `mypy --strict` (or equivalent) clean on the package.
5. No third-party runtime imports (`math`, `datetime`, `zoneinfo`, `re`, `calendar`
   only).
