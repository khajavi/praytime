# PrayTime (zarrabi/praytime) — Research Report for a Python Port

> Source of truth: `https://github.com/zarrabi/praytime` (default branch `main`),
> file `src/praytime.js` (v3.2, 398 lines), plus the test suite, examples, and the
> official docs at `https://praytimes.org/docs/`.
> All values below are quoted from the actual source. The repository was fetched on
> 2026-10-16. Everything that could be fetched was fetched; no section was guessed.

---

## 1. Overview

**What it is.** PrayTime is a small, dependency-free JavaScript library that
calculates the eight daily Islamic prayer times (Fajr, Sunrise, Dhuhr, Asr,
Sunset, Maghrib, Isha, Midnight) for a given date and geographic location, using
standard astronomical formulas.

**Author / maintainer.** Hamid Zarrabi-Zadeh (source header: `Copyright (c)
2007-2025 Hamid Zarrabi-Zadeh`; `package.json` author `"Hamid Zarrabi-Zadeh"`).

**License.** MIT. The `LICENSE` file reads: `Copyright (c) 2007-2025 Hamid
Zarrabi-Zadeh`. `package.json` declares `"license": "MIT"`.

**Language / runtime.** Plain ES6 JavaScript (a single `class PrayTime`). Works in
the browser (loaded via `<script>`), in Node.js (`require('praytime')`), and on
npm. `package.json` `"main": "src/praytime.js"`.

**Version.** `3.2.0` (npm `praytime`). Recent tags: `v3.0.0`, `v3.0.1`, `v3.1.0`,
`v3.2.0`. Recent commits include "Add Malaysia method" (2026-02-19) and "Build
v3.2.0".

**Purpose.** Zero-dependency, embeddable prayer-time engine; supports multiple
conventions, time formats, timezones, rounding, tuning, and high-latitude
adjustments through a chainable API.

### Repository structure

```
praytime/
├── LICENSE                       # MIT, 1108 bytes
├── README.md                     # 652 bytes, links to praytimes.org
├── package.json                  # npm metadata, version 3.2.0
├── src/
│   └── praytime.js               # THE entire implementation (12210 bytes, 398 lines)
├── dist/
│   └── praytime.min.js           # 5190-byte minified build
├── tests/
│   └── test.js                   # Jest tests (74 lines)
└── examples/
    ├── daily.html                # single-day timetable
    ├── monthly.html              # month timetable with method/timezone pickers
    ├── yearly.html               # year printout
    └── style.css
```

There are only **two** meaningful source artifacts: `src/praytime.js` (the whole
library) and `tests/test.js`. `dist/praytime.min.js` is just the minified build.
All logic lives in one class — the port is a single-file translation problem.

### Dependencies

None at runtime. Tests use Jest via `npm test` → `npx jest --rootDir tests`
(`devDependencies` are not listed in `package.json`; Jest is expected from the
environment). The implementation relies on:

- `Intl.DateTimeFormat()`, `Date`, `Date.UTC`, `Date.prototype.toLocaleTimeString`
- `Intl.DateTimeFormat().resolvedOptions().timeZone` (host timezone detection)
- Standard `Math` functions only.

---

## 2. Public API

The library exports `{ PrayTime }` (`module.exports = { PrayTime }`) and also
defines a global `PrayTime` class for browser `<script>` usage.

Instantiate with `const praytime = new PrayTime(method)` where `method` defaults to
`'MWL'`.

### 2.1 Constructor

| Signature | `constructor(method)` |
|---|---|
| Parameter | `method` — string key into `this.methods` (default `'MWL'`). |
| Effect | Initializes `this.methods`, `this.settings`, `this.labels`, then calls `this.method(method \|\| 'MWL')`. |

### 2.2 Chainable setters (all return `this`)

Every setter returns `this` (through `set`), so calls can be chained:
`praytime.method('ISNA').location([43,-80]).utcOffset(-5).getTimes();`

| Method | Signature | Description |
|---|---|---|
| `method` | `method(method)` | Applies `defaults` first, then the named method's overrides: `return this.set(this.methods.defaults).set(this.methods[method]);`. Returns `this`. |
| `adjust` | `adjust(params)` | Alias for `set(params)`; merges arbitrary calculation parameters (fajr, isha, maghrib, midnight, dhuhr, asr, highLats, …). |
| `location` | `location(location)` | Sets `{ location }`, an array `[latitude, longitude]` in degrees. |
| `timezone` | `timezone(timezone)` | Sets `{ timezone }`, an IANA zone string, e.g. `'America/Toronto'`. |
| `tune` | `tune(tune)` | Sets `{ tune }`, an object of per-prayer offsets in **minutes** (fractions allowed, e.g. `{sunrise: -1, sunset: 3.5}`). |
| `round` | `round(rounding = 'nearest')` | Sets `{ rounding }`: `'nearest'`, `'up'`, `'down'`, or `'none'`. |
| `format` | `format(format)` | Sets `{ format }`: `'24h'`, `'12h'`, `'12H'`, `'x'`, `'X'`, or a **function** `timestamp => …`. |
| `set` | `set(settings)` | `Object.assign(this.settings, settings); return this;` — the generic merge used by all setters. |
| `utcOffset` | `utcOffset(utcOffset = 'auto')` | If `utcOffset` is a number with `Math.abs(utcOffset) < 16` it is treated as **hours** and multiplied by 60 (to minutes). Sets `timezone: 'UTC'`, then sets `utcOffset`. Returns `this`. |

Note on `utcOffset`: the `< 16` heuristic means `-5` → `-300` minutes, `-4.5` →
`-270`, and `3.5` → `210`; but `20` would be treated as 20 **minutes**. Also, this
setter **forces** `timezone` to `'UTC'` so the numeric offset is applied manually
at formatting time.

### 2.3 Deprecated

| Method | Signature | Description |
|---|---|---|
| `setMethod` | `setMethod(method)` | Deprecated: calls `this.method(method)` but returns `undefined` (does **not** chain). |

### 2.4 Getters

| Method | Signature | Return | Description |
|---|---|---|---|
| `times` | `times(date = 0)` | `Object` of 8 string/timestamp values | Primary computation entry point. |
| `getTimes` | `getTimes(date, location, timezone = 'auto', dst = 0, format = '24h')` | `Object` | Backward-compatible wrapper. If `location` is falsy, delegates to `this.times(date)`. Otherwise sets location, `utcOffset`, and format, then calls `times`. |

**`times(date)` input normalization:**

```js
times(date = 0) {
    if (typeof date === 'number')
        date = new Date((date < 1000) ? Date.now() + date * 864e5 : date);
    if (date.constructor === Date)
        date = [date.getFullYear(), date.getMonth() + 1, date.getDate()];
    this.utcTime = Date.UTC(date[0], date[1] - 1, date[2]);

    let times = this.computeTimes();
    this.formatTimes(times);
    return times;
}
```

Accepted forms (from the manual):

| Type | Meaning | Example |
|---|---|---|
| `Date` | JS Date object | `new Date()` |
| `Array` | `[year, month, day]`, **month is 1-based** (converted with `getMonth()+1`, then `-1` again for `Date.UTC`) | `[2025, 3, 21]` |
| number ≥ 1000 | Unix timestamp in **milliseconds** | `1742686502920` |
| number < 1000 | Day offset from **now** (`Date.now() + n*864e5`) | `7` |
| omitted | defaults to `0` → today | — |

Important: only the **date** (Y/M/D) is used; times are always built from
`Date.UTC(y, m-1, d)`, i.e. midnight UTC of that calendar date. The clock time
comes from the longitude/timezone math, not from the input's time-of-day.

**`getTimes` backward-compatible behavior:** the third argument named `timezone`
is actually a **numeric UTC offset** (or `'auto'`), and `dst` is added to it:

```js
getTimes(date, location, timezone = 'auto', dst = 0, format = '24h') {
    if (!location) return this.times(date);
    const utcOffset = (timezone == 'auto') ? timezone : timezone + dst;
    this.location(location).utcOffset(utcOffset).format(format);
    return this.times(date);
}
```

So `getTimes(date, [lat,lng], -5, 1)` means UTC-5 plus 1 hour DST = UTC-4.

### 2.5 Returned object

`times()` returns an object with exactly these 8 keys (lowercase):

```
fajr, sunrise, dhuhr, asr, sunset, maghrib, isha, midnight
```

Each value is either a formatted string (`'05:52'`, `'3:32 PM'`, `'-----'`) or a
number for format `'x'`/`'X'`, or whatever the user's format function returns.

Example output from the docs:

```js
{
  fajr: '04:51', sunrise: '06:03', dhuhr: '12:06', asr: '15:29',
  sunset: '18:10', maghrib: '18:11', isha: '19:18', midnight: '23:30'
}
```

### 2.6 Exposed public properties

| Property | Value |
|---|---|
| `methods` | The method table (mutable — users may add new methods, e.g. `praytime.methods['Algeria'] = { fajr: 18, isha: 17 };`). |
| `settings` | The full settings object (see §7). |
| `labels` | `['Fajr', 'Sunrise', 'Dhuhr', 'Asr', 'Sunset', 'Maghrib', 'Isha', 'Midnight']` (declared but not used internally). |

---

## 3. Calculation Methods (juristic/algebraic conventions)

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

| Key | Fajr angle | Isha | Maghrib | Midnight | Notes |
|---|---|---|---|---|---|
| `MWL` | 18° | 17° | defaults (`'1 min'`) | defaults (`'Standard'`) | Muslim World League |
| `ISNA` | 15° | 15° | defaults | defaults | Islamic Society of North America |
| `Egypt` | 19.5° | 17.5° | defaults | defaults | Egyptian General Authority of Survey |
| `Makkah` | 18.5° | `'90 min'` (90 min after Maghrib) | defaults | defaults | Umm al-Qura; docs say 120 min during Ramadan (not implemented as a special case) |
| `Karachi` | 18° | 18° | defaults | defaults | University of Islamic Sciences |
| `Tehran` | 17.7° | **inherits defaults `isha: 14`** | 4.5° | `'Jafari'` | Institute of Geophysics, Univ. of Tehran |
| `Jafari` | 16° | **inherits defaults `isha: 14`** | 4° | `'Jafari'` | Leva Research Institute, Qom |
| `France` | 12° | 12° | defaults | defaults | Muslims of France |
| `Russia` | 16° | 15° | defaults | defaults | Spiritual Administration of Muslims of Russia |
| `Malaysia` | 20° | 18° | defaults | defaults | JAKIM (added 2026) |
| `Singapore` | 20° | 18° | defaults | defaults | Islamic Religious Council of Singapore |
| `defaults` | — | 14° | `'1 min'` | `'Standard'` | Applied to **all** methods first |

**Critical ordering rule:** `method(m)` does
`this.set(this.methods.defaults).set(this.methods[m])`. `defaults` is applied
first, then the named method overrides only the keys it defines. Hence:
- Tehran/Jafari have **no explicit `isha`**, so they inherit `isha: 14` from
  `defaults`. (The docs' methods table lists 14° for both.)
- All methods inherit `maghrib: '1 min'` unless they override it (Tehran 4.5°,
  Jafari 4°).
- All methods inherit `midnight: 'Standard'` unless overridden (Tehran/Jafari →
  `'Jafari'`).
- `MWL`/`ISNA`/etc. have **no `maghrib`** key, so Maghrib = Sunset + 1 minute
  (because default `maghrib: '1 min'`).

> Note discrepancy: the online manual's "Get List of Calculation Methods" output
> omits `midnight: 'Jafari'` for Tehran/Jafari, but the **actual source adds it**.
> The source is authoritative for the port. Also the manual/method tables do not
> list `Malaysia`, but the source and commit history do.

Adding a method: `praytime.methods['Algeria'] = { fajr: 18, isha: 17 };` then
`praytime.method('Algeria')`.

---

## 4. Madhab / Asr calculation options

Controlled by the `asr` setting (default `'Standard'`). `asrAngle` resolves the
shadow-length factor:

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
| `'Standard'` | Shafi'i, Maliki, Jafari, Hanbali | 1 |
| `'Hanafi'` | Hanafi school | 2 |
| numeric (e.g. `1.7`, or string `'1.7'`) | Custom shadow factor | `this.value(asrParam)` |

The Asr **angle** is `-arccot(t + tan|lat − decl|)`. That negative angle is fed
into `angleTime`, whose `-sin(angle)` term cancels the sign. Asr always uses the
`+1` (afternoon) direction (`processTimes` omits the direction arg → default `1`).

---

## 5. High-latitude adjustment rules

Controlled by `highLats` (default `'NightMiddle'`). Supported: `'None'`,
`'NightMiddle'`, `'OneSeventh'`, `'AngleBased'`.

```js
adjustHighLats(times) {
    const params = this.settings;
    if (params.highLats == 'None')
        return;

    this.adjusted = false;
    const night = 24 + times.sunrise - times.sunset;

    Object.assign(times, {
        fajr: this.adjustTime(times.fajr, times.sunrise, params.fajr, night, -1),
        isha: this.adjustTime(times.isha, times.sunset, params.isha, night),
        maghrib: this.adjustTime(times.maghrib, times.sunset, params.maghrib, night)
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

**Night length:** `night = 24 + sunrise − sunset` hours (sunrise is next morning,
so `24` shifts it forward; e.g. sunrise 6, sunset 18 → 12 hours).

**Factors (`portion` = factor × night):**

| `highLats` | Factor | Meaning |
|---|---|---|
| `'NightMiddle'` | `1/2` | Half the night. Fajr = sunrise − night/2; Isha/Maghrib = sunset + night/2. |
| `'OneSeventh'` | `1/7` | One seventh of the night. |
| `'AngleBased'` | `(1/60) × angle` | Angle-based: angle/60 of the night (e.g. 18° → 0.30 × night). |
| `'None'` | — | Early `return`; no adjustment. |

**Direction:** Fajr uses `direction = -1` (measured back from sunrise); Isha and
Maghrib use `direction = 1` (measured forward from sunset).

**When it clamps:** if the computed time is `NaN` (sun never reaches the angle) or
if it lies farther than `portion` from the base, the time is set to
`base + portion × direction` and `this.adjusted` is set to `true`. `this.adjusted`
is later consumed by the Jafari midnight calculation (§6).

**Quirks to replicate:**
- `adjustHighLats` runs **before** `updateTimes`, so the angle values used here are
  the raw `fajr`/`isha`/`maghrib` settings (which may be strings like `'90 min'`).
  `AngleBased` calls `this.value(angle)` on them.
- When `highLats == 'None'`, `this.adjusted` is **not reset** — it keeps whatever
  value the previous computation left (initially `undefined`). A stateful side
  effect worth mirroring or deliberately fixing.
- `maghrib` is adjusted too, "to make sure Maghrib always falls between Sunset and
  Isha" during abnormal periods (per the docs).

---

## 6. Time adjustment logic

`computeTimes` orchestrates the pipeline:

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

The initial values above are **hour guesses** (local solar time), used as the
"seed" time fed into the sun-position iteration. `settings.iterations` defaults to
`1`.

### 6.1 `processTimes` — the core per-prayer formulas

```js
processTimes(times) {
    const params = this.settings;
    const horizon = 0.833;
    return {
        fajr: this.angleTime(params.fajr, times.fajr, -1),
        sunrise: this.angleTime(horizon, times.sunrise, -1),
        dhuhr: this.midDay(times.dhuhr),
        asr: this.angleTime(this.asrAngle(params.asr, times.asr), times.asr),
        sunset: this.angleTime(horizon, times.sunset),
        maghrib: this.angleTime(params.maghrib, times.maghrib),
        isha: this.angleTime(params.isha, times.isha),
        midnight: this.midDay(times.midnight) + 12
    }
}
```

- `horizon = 0.833°` — the standard refraction/solar-radius constant for
  sunrise/sunset. Elevation is **not** modeled (constant regardless of altitude).
- Fajr and Sunrise use direction `-1` (before noon); Asr, Sunset, Maghrib, Isha
  use the default `+1` (after noon).
- Midnight is `midDay + 12` (i.e. solar noon plus 12 h ≈ next-day noon), refined
  later.

### 6.2 `updateTimes` — intervals and midpoint overrides

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

Order of operations and exact semantics:

1. **Maghrib interval:** if `maghrib` setting contains `'min'`, then
   `maghrib = sunset + minutes/60`. (Default method value is `'1 min'` → Sunset + 1
   minute; Makkah-style is `'90 min'` style for Isha.)
2. **Isha interval:** if `isha` contains `'min'`, then `isha = maghrib + minutes/60`
   — note it is relative to **Maghrib**, not Sunset. (Makkah `'90 min'` → 90 min
   after Maghrib.)
3. **Jafari midnight:** when `midnight == 'Jafari'`, the next day's Fajr is
   approximated by calling `angleTime(params.fajr, 29, -1) + 24` (the magic number
   `29` is a fixed time-of-day guess for seeding the solar-position iteration). If
   high-latitude adjustment fired (`this.adjusted`), it instead uses the already
   adjusted `times.fajr + 24`. Midnight = midpoint of Sunset and that Fajr.
4. **Dhuhr offset:** `dhuhr += value(dhuhr)/60`. Default `dhuhr: '0 min'` → +0.

### 6.3 `tuneTimes` — manual per-prayer minutes

```js
tuneTimes(times) {
    const mins = this.settings.tune
    for (let i in times)
        if (i in mins)
            times[i] += mins[i] / 60;
}
```

Tune values are in minutes (fractions allowed). Applied to any matching key.

### 6.4 `convertTimes` — hours → timestamp

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

- All computed values are **local solar time (hours)**. Converting to UTC subtracts
  `longitude/15` hours (`15° = 1 h`).
- `utcTime` = `Date.UTC(y, m-1, d)` = midnight UTC of the date in ms.
- `Math.floor(time * 36e5)` → integer milliseconds added to `utcTime`.
- `36e5` = `3,600,000` ms/hour.

### 6.5 `roundTime` — rounding mode

```js
roundTime(timestamp) {
    const rounding = {
        up: 'ceil', down: 'floor', nearest: 'round'
    }[this.settings.rounding];
    if (!rounding)
        return timestamp;
    const OneMinute = 6e4;
    return Math[rounding](timestamp / OneMinute) * OneMinute;
}
```

| `rounding` | `Math` fn | Result |
|---|---|---|
| `'up'` | `Math.ceil` | next minute |
| `'down'` | `Math.floor` | this minute |
| `'nearest'` (default) | `Math.round` | nearest minute |
| `'none'` / anything else | — | raw ms timestamp (no rounding) |

Rounding is done on the **minute-since-epoch** scale, then multiplied back.

### 6.6 Formatting

```js
formatTimes(times) {
    for (let i in times)
        times[i] = this.formatTime(times[i]);
}

formatTime(timestamp) {
    const format = this.settings.format;
    const InvalidTime = '-----';
    if (isNaN(timestamp))
        return InvalidTime;
    if (typeof format === 'function')
        return format(timestamp);
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
| `'12h'` | 12-hour with suffix, `hour12:true`, `hour:'numeric'` | `'3:32 PM'` |
| `'12H'` | 12-hour, AM/PM stripped via `replace(/ ?[AP]M/, '')` | `'3:32'` |
| `'x'` | Unix **milliseconds** (`Math.floor(ts/1)`) | `1740169920000` |
| `'X'` | Unix **seconds** (`Math.floor(ts/1000)`) | `1740169920` |
| function | whatever the function returns | — |
| invalid (`isNaN`) | `'-----'` | — |

**Timezone / offset handling:**
- Default `utcOffset: 'auto'` → `Date` uses `settings.timezone` (an IANA string) for
  the display. No manual offset added.
- Numeric `utcOffset` (set via `utcOffset()`) → `settings.timezone` is forced to
  `'UTC'` and the numeric offset (in minutes) is added to the timestamp before the
  UTC-rendered display. This is how DST/odd offsets are applied manually.
- Minute rounding happens **before** formatting, on the absolute timestamp.

---

## 7. Complete settings object (defaults)

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
| `fajr`, `isha`, `maghrib`, `midnight` | set by `method()` | angle (number) or `'<n> min'` interval string; midnight is `'Standard'` / `'Jafari'` |
| `dhuhr` | `'0 min'` | minutes added after solar noon |
| `asr` | `'Standard'` | `'Standard'`, `'Hanafi'`, or numeric shadow factor |
| `highLats` | `'NightMiddle'` | `'None'`/`'NightMiddle'`/`'OneSeventh'`/`'AngleBased'` |
| `tune` | `{}` | per-prayer minute offsets |
| `format` | `'24h'` | output format |
| `rounding` | `'nearest'` | `'nearest'`/`'up'`/`'down'`/`'none'` |
| `utcOffset` | `'auto'` | minutes when numeric, else `'auto'` |
| `timezone` | host IANA zone | used when `utcOffset == 'auto'` |
| `location` | `[0, -getTimezoneOffset()/4]` | latitude, longitude; default longitude approximates the host offset (offset minutes/4 = degrees, since 60 min = 15°). E.g. UTC+3 → `getTimezoneOffset() = -180` → lng `45`. |
| `iterations` | `1` | number of `processTimes` refinement passes |

Note the parameter set applied by methods does **not** include `dhuhr`, `asr`,
`highLats`, etc.; those come from `settings` defaults and `adjust()`.

---

## 8. Core astronomical algorithms

### 8.1 Degree-based trigonometry helpers (class fields)

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

All public trig takes/returns **degrees**. `arccot(x) = atan(1/x)` in degrees.

### 8.2 Julian date offset and sun position

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

- **Julian day offset `D`**: `utcTime/864e5` is days since the Unix epoch
  (1970-01-01). `10957.5` is the gap between the Unix epoch and the J2000.0 epoch
  (JD 2451545.0; 2451545.0 − 2440587.5 = 10957.5). `time/24` adds the fractional
  local solar day, and `−lng/360` converts longitude to a day fraction
  (15°/hour → 360°/day).
- **Mean anomaly** `g = 357.529 + 0.98560028·D` (deg, mod 360).
- **Mean longitude** `q = 280.459 + 0.98564736·D` (deg, mod 360).
- **Ecliptic longitude** `L = q + 1.915·sin(g) + 0.020·sin(2g)` (deg, mod 360).
- **Obliquity** `e = 23.439 − 0.00000036·D` (deg).
- **Right ascension** `RA = mod(arctan2(cos e·sin L, cos L)/15, 24)` (hours).
- **Declination** `δ = arcsin(sin e · sin L)` (deg).
- **Equation of time** `EqT = q/15 − RA` (hours).

This matches the U.S. Naval Observatory approximate solar-coordinate algorithm
quoted in `https://praytimes.org/docs/calculation`, minus the `R` (Earth–Sun
distance) term which PrayTime does not use.

Note: `this.value(time)` allows `time` to be a number or a string; `time` is the
solar-time seed (hours).

### 8.3 Dhuhr / solar noon (midDay)

```js
midDay(time) {
    const eqt = this.sunPosition(time).equation;
    const noon = this.mod(12 - eqt, 24);
    return noon;
}
```

`Dhuhr = 12 − EqT` (local solar noon in hours, mod 24). The `TimeZone − Lng/15`
part of the classical formula is applied later in `convertTimes` (through the
`−lng/15` shift and timestamp construction), not here.

### 8.4 Sun altitude / twilight time (angleTime)

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
T(α)   = H / 15            (hours)
time   = Dhuhr ± T(α)
```

- `α` = `angle` (positive degrees below horizon; e.g. 18 for Fajr, 0.833 for
  sunrise/sunset). The `−sin(α)` sign accounts for the angle being **below** the
  horizon.
- `direction = -1` for morning prayers (subtract), `+1` (default) for afternoon.
- If the argument to `arccos` is outside `[−1, 1]` (polar day/night),
  `Math.acos` returns `NaN`; the NaN then propagates and is handled by
  `adjustHighLats` / rendered as `'-----'`.

### 8.5 Sunrise / Sunset

Same `angleTime` with `angle = 0.833` (the `horizon` constant): Sunrise uses
`direction = -1`, Sunset uses `+1`. Elevation is ignored.

### 8.6 Asr (shadow factor)

See §4. Formula implemented:

```
Asr angle  = −arccot(t + tan|φ − δ|)
Asr time   = Dhuhr + arccos-based T(Asr angle)
```

with `t = 1` (Standard) or `t = 2` (Hanafi) or a custom numeric factor via
`adjust({asr: 1.7})`.

### 8.7 Maghrib / Isha

Default: computed as twilight angles (`angleTime(maghrib)`, `angleTime(isha)`),
then **overridden** in `updateTimes` when the setting is a `'<n> min'` interval
string (Maghrib relative to Sunset; Isha relative to Maghrib). Makkah uses
`isha: '90 min'`. Defaults give `maghrib: '1 min'` for all standard methods.

### 8.8 Midnight (Standard vs Jafari)

- **Standard** (default, and all methods except Tehran/Jafari): midnight =
  `midDay + 12` ≈ mean between Sunset and Sunrise (astronomical midnight).
- **Jafari**: midpoint between Sunset and **next Fajr** (legal midnight), computed
  in `updateTimes` (§6.2).

---

## 9. Constants, tables, and magic numbers

| Constant / number | Where | Meaning |
|---|---|---|
| `0.833` | `processTimes` | Sunrise/Sunset horizon angle (refraction + solar radius), degrees |
| `10957.5` | `sunPosition` | Days from Unix epoch (1970-01-01) to J2000.0 (JD 2451545.0) |
| `864e5` | `times`, `sunPosition` | ms per day (`86,400,000`) |
| `36e5` | `convertTimes` | ms per hour (`3,600,000`) |
| `6e4` | `roundTime`, `timeToString` | ms per minute (`60,000`) |
| `357.529` | `sunPosition` | Mean anomaly constant `g` |
| `0.98560028` | `sunPosition` | Mean anomaly rate per day |
| `280.459` | `sunPosition` | Mean longitude constant `q` |
| `0.98564736` | `sunPosition` | Mean longitude rate per day |
| `1.915` | `sunPosition` | Equation-of-center amplitude (sin g) |
| `0.020` | `sunPosition` | Equation-of-center amplitude (sin 2g) |
| `23.439` | `sunPosition` | Obliquity of ecliptic at J2000 (deg) |
| `0.00000036` | `sunPosition` | Obliquity change per day |
| `1`, `2` | `asrAngle` | Shadow factors for Standard / Hanafi |
| `1/2`, `1/7`, `1/60` | `adjustTime` | High-latitude portion factors |
| `29` | `updateTimes` (Jafari) | Hard-coded hour seed for computing next-day Fajr |
| `12` | `midDay`, midnight | Half-day offset (noon) / hours-per-half-day |
| `24` | various | Hours per day |
| `15` | `convertTimes`, `angleTime`, `sunPosition` | Degrees to hours (15°/h) |
| `360`, `90`, `180` | validation docs | Valid coordinate ranges |
| hours `5,6,12,13,18,18,18,24` | `computeTimes` | Initial solar-time guesses per prayer |
| `InvalidTime = '-----'` | `formatTime` | Placeholder for NaN times |

Method table numbers: Fajr/Isha angles 18/17, 15/15, 19.5/17.5, 18.5 + 90 min,
18/18, 17.7 + (14 default) + 4.5 maghrib, 16 + (14 default) + 4 maghrib, 12/12,
16/15, 20/18, 20/18; defaults isha 14, maghrib `'1 min'`, midnight `'Standard'`.

---

## 10. Edge cases and special handling

1. **Polar day/night / extreme latitudes.** `angleTime` feeds a value outside
   `[−1,1]` into `arccos` → `NaN`. `adjustHighLats` catches `isNaN(time)` and
   clamps to `base + portion·direction` (unless `highLats == 'None'`, in which case
   the NaN survives and `formatTime` emits `'-----'`).
2. **`highLats: 'None'` does not reset `this.adjusted`.** The flag is only set to
   `false` inside `adjustHighLats` when the mode is not `'None'`. With `'None'`,
   `this.adjusted` retains its last value (initially `undefined`), which can affect
   a subsequent `'Jafari'` midnight calculation. Reproduce or intentionally fix.
3. **`this.adjusted` and Jafari midnight.** If high-lat correction fired, Jafari
   midnight uses `times.fajr + 24`; otherwise it re-derives next-day Fajr via
   `angleTime(fajr, 29, -1) + 24`.
4. **`'min'` strings.** `isMin` checks `String(str).indexOf('min') != -1`;
   `value` parses the leading number with `+String(str).split(/[^0-9.+-]/)[0]`. A
   bare `'min'` parses to `+''` = `0`; be careful when porting (Python should
   define explicit behavior).
5. **Elevation is not supported.** The `0.833` constant is fixed; the docs state
   "in practice, the constant is considered the same regardless of the elevation."
6. **Only Y/M/D of the input date is used.** Any time-of-day on the `Date` object
   is discarded (`utcTime = Date.UTC(y, m-1, d)`).
7. **Month indexing is 1-based in arrays.** `times([2025, 3, 21])` is March 21,
   but `Date` construction subtracts 1 internally. The test uses `[2025, 2, 21]`
   for **February** 21, 2025 (comment in test says "Fab 21, 2025").
8. **Number input ambiguity.** A numeric `date` `< 1000` is a **day offset from
   now**, not a timestamp. So `times(7)` = one week from today; `times(1000)` is
   interpreted as a ms timestamp (which is 1970-01-01).
9. **`utcOffset` heuristic.** Values with `|n| < 16` are **hours** (×60); larger
   values are **minutes**. `utcOffset()` also forces `timezone: 'UTC'`.
10. **IANA vs numeric timezone.** `timezone('America/Toronto')` uses the host
    `Intl` database; `utcOffset(n)` bypasses IANA and forces UTC. Mixing them
    (setting both) means the last call wins for the relevant setting — note
    `utcOffset()` overwrites `timezone` to `'UTC'`, while `timezone()` does not
    reset `utcOffset`.
11. **`getTimes` third parameter is an offset, not an IANA zone.** `dst` is added
    to it. Passing an IANA string there would break the arithmetic (string + number).
12. **Default location longitude** is derived from the host's current UTC offset
    (`−getTimezoneOffset()/4`). At the poles/default latitude 0, times are still
    computed; use with care.
13. **Iteration count.** `iterations: 1` by default; increasing it re-seeds the
    sun-position `time` with the previous pass's result, refining accuracy.
14. **Makkah Ramadan rule (120 min) is NOT implemented.** The code always uses the
    method's `isha: '90 min'`; there is no Ramadan special case.
15. **Jest test mutates a shared instance across tests** (`.location`, `.method`,
    `.format`, `.round`, `.tune`, `.utcOffset`), relying on execution order. Ported
    tests should use fresh instances.
16. **`getTimes`/`times` aliasing.** Both names exist; `getTimes` is the legacy
    signature, `times` the modern one. The examples mostly call `getTimes()` with
    no args (which delegates to `times(0)` → today).

---

## 11. Full reference behavior from the test suite

`tests/test.js` (Waterloo, ON: lat `43.4643`, lng `-80.5204`; date `[2025, 2, 21]`;
timezone `'America/Toronto'`; method `'ISNA'`). These are exact expected strings —
ideal as port regression tests:

```js
// default 24h
times.fajr    === '05:52'
times.dhuhr   === '12:36'
times.asr     === '15:32'
times.maghrib === '18:02'

// formats (asr)
format('x').getTimes(date).asr === 1740169920000
format('X').getTimes(date).asr === 1740169920
format('12h').getTimes(date).asr === '3:32 PM'
format('12H').getTimes(date).asr === '3:32'
format('24h').getTimes(date).asr === '15:32'

// utc offsets (fajr)
utcOffset(-4.5).getTimes(date).fajr === '06:22'
utcOffset(-300).getTimes(date).fajr === '05:52'

// rounding (asr)
round('down').getTimes(date).asr === '15:32'
round('up').getTimes(date).asr === '15:33'
round('nearest').getTimes(date).asr === '15:32'

// adjust
adjust({ fajr: 19.7, dhuhr: '11 min' }).getTimes(date)
  → fajr === '05:26', dhuhr === '12:47'

// tune
tune({ asr: 11, maghrib: 4.5 }).getTimes(date)
  → asr === '15:43', maghrib === '18:07'
```

Note `test.js` calls `praytime.method('ISNA').location(...).timezone(...)` and then
chains mutations across tests without resetting; the numeric expectations above
reflect that accumulated state for `fajr`/`dhuhr` etc. only where the test itself
didn't mutate those keys.

### Example HTML usage

- `daily.html`: `new PrayTime('ISNA')`, `.location([43.65, -79.4]).timezone('America/Toronto').getTimes()`, then reads `times[label.toLowerCase()]` for labels `Fajr, Sunrise, Dhuhr, Asr, Maghrib, Isha`.
- `monthly.html`: full UI; iterates a month with `getTimes(date)`, supports `format('12H'|'24h')`, timezone from `Intl.supportedValuesOf("timeZone")`, and a method dropdown listing MWL, ISNA, Egypt, Makkah, Karachi, Tehran, Jafari, France, Russia, Singapore (Malaysia not shown in the dropdowns).
- `yearly.html`: prints Jan 1–Dec 31 in a `<pre>` table.

---

## 12. Porting notes for Python

These are recommendations for a faithful, idiomatic Python port.

### 12.1 Structure

- One module, e.g. `praytime.py`, with a `PrayTime` dataclass-like class. Keep the
  method table as a module-level dict and copy-on-write per instance
  (`self.methods` is mutable/public in JS; users may add methods).
- Use `datetime.date` / tuple `(y, m, d)` for the date; accept `date`, `datetime`,
  `(y, m, d)`, `int` timestamp, or `int` day offset (careful with the `< 1000`
  ambiguity). Normalize to `(y, m, d)` immediately.
- Keep the chainable API by returning `self` from setters. In Python this is
  idiomatic and matches the JS ergonomics.

### 12.2 Dates, time and timezones

- JS `Date.UTC(y, m-1, d)` → Python `datetime(y, m, d, tzinfo=timezone.utc)` or a
  ms-epoch computed as `calendar.timegm((y, m, d, 0, 0, 0)) * 1000`. Avoid
  `time.mktime` (local-time dependent).
- The JS `10957.5` constant should be computed, not hard-coded: the J2000 Julian
  date is `2451545.0` and the Unix epoch is `2440587.5`, so
  `D = utc_days - 10957.5 + time/24 - lng/360`.
- Timezone display: JS uses the host `Intl` database. Python should use
  `zoneinfo.ZoneInfo` (standard library, 3.9+) for IANA zones, and
  `datetime.astimezone(ZoneInfo(tz))`. For numeric UTC offsets, use
  `datetime.timezone(timedelta(minutes=offset))` and format directly — do **not**
  call `strftime('%H:%M')` on a naive value.
- Emulate the final formatting: apply rounding in ms first, then convert to the
  target tz, then format `HH:MM` (24h, zero-padded), `h:MM AM/PM` (12h,
  `%-I`/strip leading zero — JS uses `hour:'numeric'`), or strip the AM/PM for
  `12H`. Python's `%I` gives a leading zero; strip it or use `strftime('%-I')`
  on glibc (not portable) — safer: `f"{dt.hour % 12 or 12}:{dt.minute:02d}"`.
- Implement `'x'`/`'X'` as `int(timestamp_ms)` and `int(timestamp_ms // 1000)`.

### 12.3 Floating point and degrees/radians

- Port the degree-based trig helpers (`dtr`, `rtd`, `sin`, `cos`, `tan`, `asin`,
  `acos`, `atan`, `acot = atan(1/x)`, `atan2`) — all taking/returning degrees.
  Either module functions or a small mixin.
- Python `math` raises `ValueError` on `math.acos`/`math.asin` out of range
  (unlike JS `Math.acos` which returns `NaN`). To match the high-latitude logic,
  catch `ValueError` and return `float('nan')`, or clamp — but clamping would
  change behavior. Best: return `nan` so `math.isnan` drives the same
  `adjustHighLats` branch.
- `math.fmod` differs from JS `%` for negatives; implement `mod(a, b) = ((a % b) + b) % b` to match JS positive modulo (Python's `%` already returns a
  non-negative result for positive `b`, so `a % b` alone is usually equivalent —
  but keep the helper for parity and clarity).

### 12.4 Faithfully preserve these behaviors

- **`defaults` then method** merge order.
- **`isha`/`maghrib` interval strings**: `'90 min'`, `'1 min'`, `'<n> min'`.
  Parse with a regex like `^\s*([+-]?\d+(?:\.\d+)?)\s*min` → float; keep the
  `is_min` check as `'min' in str(x)`.
- **High-latitude `this.adjusted` statefulness**: decide explicitly. For a clean
  port, make `adjusted` a local variable returned from `adjust_high_lats`, but if
  you want bit-identical output, mirror the JS quirk (including not resetting it
  when mode is `'None'`).
- **Jafari next-day Fajr seed `29`** and `adjusted` branch.
- **Rounding on the ms scale**, then format.
- **Default location longitude** `-gettzoffset/4` uses the *host current* offset;
  in Python, derive from `datetime.now().astimezone().utcoffset()` →
  `-offset_minutes/4`, or require the caller to set location.
- **`utcOffset` `< 16` → hours** heuristic. Consider making it explicit in the
  Python API (separate `utc_offset_hours`/`utc_offset_minutes`) but keep the
  heuristic if you want drop-in parity.
- **NaN → `'-----'`** in formatting.
- **`hour:'numeric'` for 12h** (no leading zero) and `'2-digit'` for 24h.

### 12.5 API shape suggestions

- Provide both `times(date=0)` and `get_times(date, location=None, timezone='auto', dst=0, format='24h')`
  for API parity (snake_case names, but consider aliases). Keep the deprecated
  `set_method`.
- Return a `dict[str, str|int]` with keys exactly
  `fajr, sunrise, dhuhr, asr, sunset, maghrib, isha, midnight`.
- Type hints: `location: tuple[float, float]`, `format: str | Callable`, etc.
- No third-party dependencies needed — standard library only (`math`, `datetime`,
  `zoneinfo`).
- Add pytest tests mirroring §11, plus polar-latitude cases
  (e.g. lat 70 in June/December) to exercise `adjust_high_lats`.

### 12.6 Known gaps to decide on

- Elevation not supported (match JS, or add as an extension).
- Makkah 120-min Ramadan rule absent (match JS, or add).
- `iterations` default 1; expose for refinement.
- `Intl`-based timezone formatting differences (e.g. hour cycle, `numeric` hour on
  some platforms) — Python formatting gives full control, so results should be
  *more* deterministic than the JS version.

---

## 13. Accuracy / provenance

- The solar-position algorithm is the USNO "approximate solar coordinates"
  algorithm (accuracy ~1 arcminute within two centuries of 2000), exactly as
  documented at `https://praytimes.org/docs/calculation`.
- The twilight hour-angle formula and the Asr shadow-factor formula match the
  documentation's `T(α)` and `A(t)` formulas.
- Method parameters and high-latitude methods are cross-checked against
  `https://praytimes.org/docs/methods` and `.../calculation`. The source adds
  `midnight: 'Jafari'` for Tehran/Jafari and a `Malaysia` method not shown in the
  older docs tables.
- Everything in this report is derived from the fetched source; no algorithm or
  constant was invented. Where docs and source disagree, the discrepancy is called
  out explicitly and the **source** is treated as authoritative.
