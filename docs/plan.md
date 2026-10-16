# PrayTime Python Port — High-Level Implementation Plan

> Inputs: `docs/research.md` (behavioral analysis of `zarrabi/praytime` v3.2.0) and
> `docs/specs.md` (implementation-ready specification). This plan is the roadmap for
> building the package. It does **not** re-derive algorithms: every formula, constant,
> default, and quirk lives in `specs.md` and is referenced here by section (e.g.
> `specs.md §8.2`).

---

## 1. Executive Summary

We are building a Python port of the zero-dependency JavaScript library
`zarrabi/praytime`, which computes the eight daily Islamic prayer times (Fajr,
Sunrise, Dhuhr, Asr, Sunset, Maghrib, Isha, Midnight) from a date and location using
standard astronomical formulas. The port reproduces the JS source's numerical behavior
exactly — including its deliberate quirks — while exposing an idiomatic, chainable,
fully type-hinted Python API (`PrayTime`). The outcome is a zero-runtime-dependency,
numerically-faithful, well-tested package importable as `praytime` (`from praytime
import PrayTime`), supporting Python 3.9+, verified by a pytest suite that mirrors the
upstream Jest tests plus golden snapshots generated directly from the JS library via
Node.

---

## 2. Goals & Success Criteria

- [ ] **Numerical parity** — for every input the JS library accepts, the port returns
      the same formatted strings / integer timestamps. Exact string/int equality on
      all reference and golden cases (`specs.md §11`, `§12`).
- [ ] **Ergonomic API** — chainable setters returning `self`; `times()` /
      `get_times()`; 8-key return dict in the specified order; snake_case public
      methods, camelCase settings keys (`specs.md §3`, `§3.6`).
- [ ] **Zero runtime dependencies** — standard library only (`math`, `datetime`,
      `zoneinfo`, `re`, `calendar`) (`specs.md §1.2`, `§13.4`).
- [ ] **Python 3.9+** — `zoneinfo` available; annotations written 3.9-compatible with
      `from __future__ import annotations` (`specs.md §1.4`).
- [ ] **Passing pytest suite** — `python -m pytest` green, mirroring upstream Jest
      assertions plus high-lat, formatting, date-input, and method tests
      (`specs.md §12.2`).
- [ ] **Golden-snapshot parity** — matrix snapshots generated from the JS library in
      Node compare equal against Python output (`specs.md §12.4`).
- [ ] **Clean static checks** — `mypy` (strict-mode goal) clean on the package
      (`specs.md §13.4`).

---

## 3. Architecture Overview

The port is a thin orchestration layer over a set of small, pure, independently
testable modules. The public class is the only stateful object; the astronomy,
formatting, and parsing logic are pure functions. This split is an internal
organization decision — the observable behavior is exactly that of the single JS
class (`specs.md §2.1` design note).

### 3.1 Layers

| Layer | Modules | Responsibility |
|---|---|---|
| **Presentation / public API** | `praytime/praytime.py` | `PrayTime` class: constructor, chainable setters, `times`/`get_times`, and the compute pipeline that wires the other layers together. Owns per-instance state (`methods`, `settings`, `labels`, `_utc_time`, `_adjusted`). |
| **Domain / computation** | `astro.py`, `highlat.py`, `methods.py` | Pure astronomical math (`sun_position`, `mid_day`, `angle_time`, `asr_angle`), high-latitude clamping, and the `defaults`-then-method resolution rule. |
| **Support / utility** | `trig.py`, `formatting.py`, `constants.py` | Degree-based trig with `nan`-on-range-error semantics, interval parsing / rounding / string rendering, and all numeric constants, seeds, and labels. |
| **Data / config** | (inside `constants.py`) | The `METHODS` table (`specs.md §4`), the `DEFAULTS` settings dict (`specs.md §7`), and `LABELS`. |

### 3.2 End-to-end flow

Input normalization → seeding → iterative `process_times` → high-latitude adjustment →
interval/midpoint overrides → tuning → conversion to timestamps → rounding → formatting.

```
            user call: PrayTime(...).location(...).timezone(...).times(date)
                                          │
                                          ▼
        ┌─────────────────────────────────────────────────────────────┐
        │ praytime.py  (PrayTime orchestrator, the only stateful unit) │
        └─────────────────────────────────────────────────────────────┘
             │                │                 │                 │
   normalize date       seed hours        process_times       adjust_high_lats
   (specs §3.3)         (specs §8.9)      (specs §8.9)        (specs §6)
             │                │                 │                 │
             ▼                ▼                 ▼                 ▼
        _utc_time        SEED_{...}        astro.py           highlat.py
        (ms, UTC)        constants        sun_position/
                                          mid_day/
                                          angle_time/
                                          asr_angle
             │                                  ▲
             └──────────────────────────────────┘
                          trig.py + constants.py (leaf deps)

   update_times ──► tune_times ──► convert_times ──► round_time ──► format_time
   (specs §8.10)    (specs §8.11)  (specs §8.12)     (specs §8.13)  (specs §9.1)
        │               │               │               │              │
        └───────────────┴───────────────┴─ formatting.py + methods.py ─┘
                                                         │
                                                         ▼
                              dict: fajr, sunrise, dhuhr, asr, sunset,
                                    maghrib, isha, midnight
```

---

## 4. Code Organization

The package tree mirrors `specs.md §2`. Each module owns one concern; dependencies
point strictly downward (leaf utilities have no in-package imports beyond
`constants`), so there are **no circular imports**.

```
praytime/                         # repo root
├── pyproject.toml                # build metadata; no runtime deps; pytest dev dep
├── README.md
├── LICENSE                       # MIT (match upstream header)
├── docs/
│   ├── research.md               # (exists) research report
│   ├── specs.md                  # (exists) implementation spec
│   └── plan.md                   # (this file)
├── praytime/                     # the importable package
│   ├── __init__.py               # PrayTime, METHODS, __version__, __all__
│   ├── constants.py              # METHODS, DEFAULTS, LABELS, all numeric constants/seeds
│   ├── trig.py                   # dtr, rtd, sin, cos, tan, asin, acos, atan, acot, atan2, mod
│   ├── astro.py                  # sun_position, mid_day, angle_time, asr_angle, julian_offset
│   ├── highlat.py                # adjust_high_lats, adjust_time
│   ├── formatting.py             # round_time, js_round, format_time, time_to_string, parse_value, is_min
│   ├── methods.py                # resolve_method, get_methods
│   └── praytime.py               # PrayTime class (orchestration + public API)
└── tests/
    ├── __init__.py
    ├── test_reference.py         # mirrors tests/test.js assertions exactly
    ├── test_methods.py           # method table + inherited defaults
    ├── test_highlat.py           # polar / high-latitude rules
    ├── test_formatting.py        # 24h/12h/12H/x/X/callable/'-----', parse_value, js_round
    ├── test_date_inputs.py       # date/datetime/tuple/timestamp/day-offset
    ├── test_snapshot.py          # golden-file parity
    └── golden/
        ├── generate.js           # Node script: JS lib -> JSON goldens
        └── *.json                # checked-in golden matrices
```

### 4.1 Module ownership and public surface

| Module | Owns | Public / internal functions |
|---|---|---|
| `constants.py` | METHOD table, settings defaults, labels, every numeric constant seed (`HORIZON`, `J2000_OFFSET_DAYS`, MS constants, sun coefficients, shadow factors, high-lat factors, `JAFARI_SEED_HOUR`, `DEG_PER_HOUR`, `INVALID_TIME`, seed hours) | `METHODS`, `DEFAULTS`, `LABELS`, module constants (`specs.md §11`) |
| `trig.py` | Degree-based trig with JS coercion semantics; range errors → `nan` | `dtr`, `rtd`, `sin`, `cos`, `tan`, `asin`, `acos`, `atan`, `acot`, `atan2`, `mod` (`specs.md §8.1`) |
| `astro.py` | Pure astronomy | `sun_position(time, utc_ms, lng)`, `mid_day(...)`, `angle_time(...)`, `asr_angle(...)`, `julian_offset(...)` (`specs.md §8.2`–`§8.6`) |
| `highlat.py` | High-latitude clamping (adjusted flag returned, not stored) | `adjust_high_lats(times, settings, value_fn) -> bool`, `adjust_time(...)` (`specs.md §6`) |
| `formatting.py` | Rounding, interval parsing, string rendering | `round_time`, `js_round`, `format_time`, `time_to_string`, `parse_value`, `is_min` (`specs.md §8.13`, `§9`) |
| `methods.py` | Method resolution / inspection | `resolve_method(methods, name) -> dict`, `get_methods()` (`specs.md §4.2`) |
| `praytime.py` | `PrayTime`: constructor, chainable setters, `times`, `get_times`, pipeline (`compute_times`, `process_times`, `update_times`, `tune_times`, `convert_times`) | public class + methods (`specs.md §3`) |

### 4.2 Module dependency diagram

Arrows mean "imports / depends on". Direction is strictly one-way.

```
                      ┌─────────────────┐
                      │ praytime.py     │  (top: orchestration + state)
                      └─────────────────┘
                        │   │   │   │   │
        ┌───────────────┘   │   │   │   └───────────────┐
        ▼                   ▼   │   ▼                   ▼
  ┌───────────┐      ┌──────────┐│ ┌───────────┐  ┌───────────────┐
  │ methods.py│      │ astro.py ││ │highlat.py │  │ formatting.py │
  └───────────┘      └──────────┘│ └───────────┘  └───────────────┘
        │                 │      │       │               │
        │                 ▼      ▼       │               ▼
        │            ┌────────────────┐  │          (re, math,
        │            │   trig.py      │  │           datetime,
        │            └────────────────┘  │           zoneinfo)
        │                 │              │
        └────────┬────────┴──────────────┘
                 ▼
          ┌──────────────┐
          │ constants.py │  (leaf: no in-package imports)
          └──────────────┘
```

`trig.py` and `constants.py` are leaves. `astro.py`, `highlat.py`, `formatting.py`,
and `methods.py` depend only on leaves. `praytime.py` is the only module that composes
them all.

---

## 5. Key Design Decisions

- **Pure functions for all math.** `astro.py`, `trig.py`, and `highlat.py` are pure
  functions taking explicit arguments — no hidden instance state. This makes unit
  testing and golden comparison straightforward (`specs.md §2.1` design note).
- **Split modules for testability.** Astronomy, high-latitude logic, formatting, and
  parsing are isolated so each can be tested in isolation and compared to JS values
  with `pytest.approx` (`specs.md §12.3`).
- **Per-instance copies of methods and settings.** `self.methods` is a deep copy of
  `METHODS` and `self.settings` a copy of `DEFAULTS`, so mutating one instance
  (including `praytime.methods["Algeria"] = {...}`) never leaks to another
  (`specs.md §3.1`, `§13.2`).
- **snake_case public methods, camelCase settings keys.** Method names follow PEP 8
  (`utc_offset`, `get_times`, `set_method`); settings keys stay verbatim (`highLats`,
  `utcOffset`) because they are data read by the algorithm and passed through
  `adjust({...})` — renaming would break drop-in parity (`specs.md §3.6`, `§13.2`).
- **`js_round` half-up rounding.** Python's banker's rounding differs from JS
  `Math.round`; use `js_round(x) = floor(x + 0.5)` (`specs.md §8.13`). Never use
  builtin `round` for parity paths.
- **`nan` propagation instead of exceptions.** `math.acos`/`math.asin` raise
  `ValueError` outside `[-1, 1]`; the port's `acos`/`asin` catch and return
  `float("nan")` so polar-day/night flows into `adjust_high_lats` and `'-----'`
  rendering exactly as in JS. **Do not clamp** (`specs.md §8.1`, `§10.2`).
- **Type hints + `from __future__ import annotations`.** Full annotations written in a
  3.9-compatible form (`typing.Union`, `Optional`, `Tuple`, `Dict`, `Callable`,
  `Mapping`, `Sequence`) while keeping natural syntax (`specs.md §1.4`).
- **No exceptions from computation in parity mode.** Only deliberate `ValueError` for
  malformed date tuples / out-of-range dates (`specs.md §13.2` invalid-date row).
- **Preserve JS quirks exactly:** `_adjusted` statefulness not reset when
  `highLats == 'None'`, the Jafari magic seed `29`, the `< 16` hours heuristic, the
  `'auto'` → UTC quirk in `get_times`, and interval-string `is_min` substring test
  (`specs.md §13.1`).

---

## 6. Implementation Phases

Phases are sequential; each lists its dependencies. "DoD" = definition of done.

### Phase 0 — Scaffolding

- **Goal:** Create an installable, importable skeleton with tooling wired up.
- **Deliverables:** `pyproject.toml`, `praytime/__init__.py` (placeholder exports),
  empty modules with docstring stubs, `tests/__init__.py`, `README.md`, `LICENSE`,
  `conftest.py` if needed.
- **Steps:**
  1. Write `pyproject.toml` (build backend, metadata, `requires-python = ">=3.9"`, no
     runtime deps, pytest dev extra).
  2. Create the package directory and all module files (§4) with docstrings only.
  3. Add `__init__.py` exporting `PrayTime`, `METHODS`, `__version__`.
  4. Add `tests/__init__.py`.
  5. Add `LICENSE` (MIT, matching upstream) and a minimal `README.md`.
- **DoD / verification:** `python -c "import praytime"` succeeds; `pip install -e .`
  works; `pytest` collects zero tests without errors.
- **Depends on:** none.

### Phase 1 — Constants + Trig

- **Goal:** Land the data tables and the degree-trig foundation.
- **Deliverables:** completed `constants.py`, `trig.py`.
- **Steps:**
  1. Transcribe `METHODS`, `DEFAULTS`, `LABELS` and every numeric constant/seed from
     `specs.md §4`, `§7`, `§11` into `constants.py`.
  2. Implement `trig.py` functions with degree semantics and JS coercion: full
     `float(x)` conversion, `nan` on failure; `asin`/`acos` catch `ValueError` →
     `nan`; `acot(x) = degrees(atan(1/x))`; `mod(a,b) = ((a%b)+b)%b`
     (`specs.md §8.1`).
- **DoD / verification:** `tests/test_formatting.py` units for `mod` and trig range
  behavior pass; a constants smoke test asserts the merged method dict shape.
- **Depends on:** Phase 0.

### Phase 2 — Astronomy

- **Goal:** Implement the pure astronomical core.
- **Deliverables:** `astro.py`.
- **Steps:**
  1. Implement `julian_offset` / the `D` term using `J2000_OFFSET_DAYS`
     (`specs.md §8.2`).
  2. Implement `sun_position` (returns declination + equation) with the exact
     operation order of `specs.md §8.2`.
  3. Implement `mid_day` (`specs.md §8.3`).
  4. Implement `angle_time` (`specs.md §8.4`).
  5. Implement `asr_angle` (`specs.md §8.6`, `specs.md §5`).
- **DoD / verification:** Unit tests comparing `sun_position`, `mid_day`,
  `angle_time`, `asr_angle` against JS-computed values with
  `pytest.approx(rel=1e-9, abs=1e-9)` (`specs.md §12.3`).
- **Depends on:** Phases 0–1.

### Phase 3 — Orchestration & Public API

- **Goal:** Deliver a working end-to-end `PrayTime` producing times (no high-lat
  polish yet is acceptable if seeds match).
- **Deliverables:** `methods.py`, `praytime.py`.
- **Steps:**
  1. Implement `resolve_method` / `get_methods` (defaults-then-method merge;
     unknown name applies only defaults) (`specs.md §4.2`, `§10.15`).
  2. Implement the `PrayTime` constructor and chainable setters: `method`, `adjust`,
     `location`, `timezone`, `tune`, `round`, `format`, `set`, `utc_offset`,
     `set_method` (`specs.md §3.1`–`§3.2`).
  3. Implement date normalization → `_utc_time` (`specs.md §3.3`).
  4. Implement the pipeline: `compute_times`, `process_times` (seeds + single
     iteration), then wire `update_times`, `tune_times`, `convert_times`
     (`specs.md §8.9`–`§8.12`).
  5. Implement `update_times` interval/midpoint overrides only after Phase 4 provides
     high-lat; for this phase, implement the willingness-to-iterate structure.
- **DoD / verification:** `tests/test_reference.py::test_prayer_times` exact strings
  pass; `tests/test_methods.py` passes; chainability smoke test passes.
- **Depends on:** Phases 0–2.

### Phase 4 — High-Latitude & Interval Overrides

- **Goal:** Complete the high-latitude rules and the interval/midpoint overrides in the
  exact JS order.
- **Deliverables:** `highlat.py`; `update_times` completed in `praytime.py`.
- **Steps:**
  1. Implement `adjust_high_lats` / `adjust_time` returning `_adjusted`
     (`specs.md §6`), preserving the not-reset-when-`'None'` quirk
     (`specs.md §10.5`).
  2. Implement `update_times`: Maghrib/Isha `'<n> min'` overrides, Jafari midnight
     with seed `29` and the `_adjusted` branch, Dhuhr offset (`specs.md §8.10`).
  3. Ensure `adjust_high_lats` runs **before** `update_times` (`specs.md §6.2`).
- **DoD / verification:** `tests/test_highlat.py` passes, including
  `test_adjusted_statefulness`, `test_angle_based_makkah`, and `'None'` → `'-----'`.
- **Depends on:** Phase 3.

### Phase 5 — Formatting, Rounding & Parsing

- **Goal:** Finalize output rendering and interval parsing.
- **Deliverables:** `formatting.py` completed; `times`/`get_times` return shapes final.
- **Steps:**
  1. Implement `parse_value` (leading-number split, `0.0` fallback) and `is_min`
     (`specs.md §9.4`).
  2. Implement `js_round` and `round_time` (`specs.md §8.13`).
  3. Implement `format_time` and `time_to_string` for `24h`/`12h`/`12H`/`x`/`X`/
     callable/`'-----'`, using arithmetic hour rendering (`specs.md §9.1`, `§9.3`).
  4. Implement timezone/offset display via `zoneinfo.ZoneInfo` and
     `datetime.timezone(timedelta(minutes=...))` (`specs.md §9.2`).
- **DoD / verification:** `tests/test_formatting.py` and `test_date_inputs.py` pass;
  all format rows of `tests/test_reference.py` pass.
- **Depends on:** Phases 3–4.

### Phase 6 — CLI / Examples (optional)

- **Goal:** Provide a small runnable entry point mirroring the JS examples.
- **Deliverables:** `praytime/__main__.py` (thin CLI: `python -m praytime --method
  --lat --lng --timezone [--date]`), optionally an `examples/` script.
- **Steps:**
  1. Add an `argparse`-based `__main__.py` that builds a `PrayTime` and prints the 8
     times.
  2. Document usage in `README.md`.
- **DoD / verification:** `python -m praytime --method ISNA --lat 43.4643 --lng
  -80.5204 --timezone America/Toronto` prints the reference values.
- **Depends on:** Phase 5. **Note:** optional; must not add runtime dependencies.

### Phase 7 — Tests & Golden Parity

- **Goal:** Complete the test suite and lock parity against the JS library.
- **Deliverables:** all `tests/test_*.py` files; `tests/golden/generate.js` and
  checked-in golden JSON.
- **Steps:**
  1. Finish `test_reference.py` (fresh instance per test, re-applying base setup)
     (`specs.md §12.1`).
  2. Finish `test_methods.py`, `test_highlat.py`, `test_formatting.py`,
     `test_date_inputs.py` (`specs.md §12.2`).
  3. Write `tests/golden/generate.js` importing upstream `src/praytime.js`, looping the
     matrix (methods × solstices/equinoxes × latitudes `0, 21.4, 43.46, 51.5, 64, 70`;
     both madhabs; four high-lat rules) and writing JSON (`specs.md §12.4`).
  4. Run the generator once and check in golden JSON; implement `test_snapshot.py` to
     compare Python output exactly.
- **DoD / verification:** `python -m pytest` fully green; snapshot tests pass for the
  whole matrix.
- **Depends on:** Phases 5–6.

### Phase 8 — Docs, Packaging & Release

- **Goal:** Make the package publishable and documented.
- **Deliverables:** final `README.md`, `pyproject.toml` metadata polish, CI workflow,
  changelog/release notes.
- **Steps:**
  1. Document API, deviations (`specs.md §13.2`), and CLI in `README.md`.
  2. Verify packaging metadata (name `praytime`, version, license, classifiers,
     `py.typed` marker for type consumers).
  3. Add a CI workflow (lint + `mypy` + `pytest` on 3.9–3.13).
  4. Tag a first release; confirm `from praytime import PrayTime` after a clean
     install from a built wheel.
- **DoD / verification:** Build sdist/wheel, install into a clean venv, import works,
  `pytest` passes there; `mypy` clean.
- **Depends on:** Phases 7.

---

## 7. Testing & Verification Plan

| Suite | Covers | "Done" means |
|---|---|---|
| `test_reference.py` | Exact upstream Jest assertions (`specs.md §11`, `§12.1`) | Fresh instance per test; fajr/dhuhr/asr/maghrib strings and all format/utc/redundant/rounding/adjust/tune rows match exactly. |
| `test_methods.py` | Method table + `defaults`-then-method merge (`specs.md §4`) | Tehran/Jafari inherit `isha == 14` and `midnight == 'Jafari'`; others inherit `'1 min'`/`'Standard'`; Makkah `'90 min'`; Malaysia/Singapore `20/18`; custom method works; unknown method applies only defaults (no raise). |
| `test_highlat.py` | All four high-lat rules (`specs.md §6`) | `'None'` yields `'-----'` at polar latitudes; other rules clamp; `night` formula correct; `AngleBased`+Makkah factor `1.5`; `_adjusted` statefulness regression-guarded. |
| `test_formatting.py` | Rendering, parsing, rounding (`specs.md §9`, `§8.13`) | 24h pad, 12h no-pad, 12H strip, `x`/`X` ints, callable receives rounded ms, `nan` → `'-----'`; `parse_value` table; `is_min`; `js_round` half-up. |
| `test_date_inputs.py` | Date normalization (`specs.md §3.3`, `§10.1`) | No-arg/`0` = today; `<1000` offset; `>=1000` ms timestamp; `date`/`datetime` time discarded; tuple/list 1-based month; invalid length raises `ValueError`. |
| `test_snapshot.py` + `tests/golden/` | Cross-implementation parity (`specs.md §12.4`) | Python output equals JS-generated golden JSON exactly across the full matrix. |

- **Float tolerance rule:** final outputs are strings/ints → exact equality; unit-level
  astronomy comparisons use `pytest.approx(rel=1e-9, abs=1e-9)` (`specs.md §12.3`).
- **Golden generation:** `tests/golden/generate.js` runs the upstream JS library under
  Node and writes JSON; goldens are committed and compared by `test_snapshot.py`
  (`specs.md §12.4`).
- **Run everything:** `python -m pytest` (optionally `mypy --strict praytime/`).

---

## 8. Packaging & Tooling

- **`pyproject.toml`:** PEP 621 metadata; build backend `hatchling` or
  `setuptools` (choose one at Phase 0); `name = "praytime"`, `version`, MIT license,
  `requires-python = ">=3.9"`, **no `dependencies`**.
- **Optional dev dependencies:** `pytest` (required); `ruff` (lint/format) and `mypy`
  (type-check) optional but recommended; a `golden` extra or documented Node
  requirement for `generate.js` only.
- **`README.md`:** install, quick-start, API summary, supported methods, deviations.
- **`LICENSE`:** MIT, preserving upstream copyright notice.
- **Versioning:** semantic versioning; start at `0.1.0` or `1.0.0`; keep a
  `__version__` in `__init__.py`.
- **`py.typed`:** include for downstream type checkers (Phase 8).
- **CI outline:** matrix over Python 3.9–3.13; steps = install → `ruff` →
  `mypy` → `pytest`; a separate optional job running `tests/golden/generate.js` under
  Node to detect drift.

---

## 9. Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| **Float ULP differences** between Python `math`/libm and JS `Math` | Rare last-bit divergence could flip a minute at a `.5` boundary | Same operation order (`specs.md §8.2`); `js_round` half-up; unit comparisons via `approx(1e-9)`; goldens chosen away from exact boundaries (`specs.md §12.3`). |
| **Timezone / `zoneinfo` availability** (missing tzdata on some systems) | IANA lookups fail on minimal images | Detect host zone; fall back to `"UTC"` and `-offset_min/4` longitude (`specs.md §7.1`); document numeric-offset usage as the deterministic path. |
| **JS quirks / statefulness** (`_adjusted` not reset for `'None'`, magic seed `29`) | Subtle divergence in Jafari midnight or repeated calls | Mirror the quirks exactly (`specs.md §10.5`, `§13.1`); regression test `test_adjusted_statefulness`. |
| **`< 16` / `< 1000` heuristics** (hours-vs-minutes, day-offset-vs-timestamp) | Misinterpreting user input | Preserve heuristics exactly (`specs.md §10.3`, `§10.4`); cover both sides of each threshold in `test_date_inputs.py`/`test_reference.py`. |
| **High-latitude NaN behavior** (`acos`/`asin` out-of-range) | Divergent clamping or raised exception in polar cases | Return `nan` instead of clamping/raising (`specs.md §8.1`, `§10.2`); let `adjust_high_lats`/`'-----'` handle it; polar tests. |
| **`get_times` third arg is an offset, not IANA**, plus `'auto'`→UTC quirk | Surprising but parity-critical behavior | Preserve and document (`specs.md §10.10`, `§13.1`); reference test covers it. |
| **Banker's rounding from builtin `round`** | Off-by-one-minute outputs | Use `js_round` exclusively on parity paths (`specs.md §8.13`); unit-test half-up cases. |
| **Unknown method silently applies defaults** | Users expect an error | Match JS (no raise), document as deliberate parity choice (`specs.md §10.15`). |
| **`round`/`format` shadow builtins as method names** | Accidental builtin calls through instances | Keep as instance attributes only; note in tests/examples (`specs.md §3.2`). |

---

## 10. Milestones & Timeline

Ordered milestones (no calendar dates) mapping phases to outcomes.

| Milestone | Outcome | Phases |
|---|---|---|
| **M0 — Scaffold** | Importable, installable empty package; tooling wired | Phase 0 |
| **M1 — Foundations** | Constants, method table, degree-trig with JS semantics | Phase 1 |
| **M2 — Astronomy core** | Pure `sun_position`/`mid_day`/`angle_time`/`asr_angle` verified vs JS | Phase 2 |
| **M3 — First end-to-end times** | `PrayTime.times()` returns correct reference values; chainable API works | Phase 3 |
| **M4 — High-lat & intervals** | All four high-lat rules and interval/midpoint overrides correct | Phase 4 |
| **M5 — Formats complete** | All output formats, rounding, timezones, date inputs correct | Phase 5 |
| **M6 — CLI/examples (optional)** | `python -m praytime` works | Phase 6 |
| **M7 — Full parity** | Full pytest suite green; golden snapshots match JS | Phase 7 |
| **M8 — Release-ready** | Docs, packaging, `py.typed`, CI; clean-install verified | Phase 8 |

---

## 11. Future / Out of Scope

Matching `specs.md §1.3` and `§13.3`, the default port intentionally **excludes** these;
they may be considered as documented extensions later:

- **Elevation support** — `HORIZON` stays a fixed `0.833°`, matching JS (`specs.md §10.6`).
- **Makkah 120-minute Ramadan rule** — always use the method's `isha: '90 min'`
  (`specs.md §10.13`).
- **Additional calculation methods** beyond the 11 in the table — users can add their
  own via `praytime.methods["X"] = {...}` (`specs.md §4.3`).
- **A `strict=True` mode** to reset `_adjusted` unconditionally and validate/normalize
  dates instead of raising — optional, non-default (`specs.md §13.3`).
- **Explicit `utc_offset_minutes`/`utc_offset_hours` helpers** alongside the implicit
  `< 16` heuristic (`specs.md §13.2`).
- **GUI, network access, or a full ephemeris** — the port is a faithful reproduction of
  the JS approximate algorithm (`specs.md §1.3`).
