# Changelog

All notable changes to this project are documented in this file. The format is
based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-10-16

### Added

- Faithful Python port of `zarrabi/praytime` v3.2.0 with the full chainable
  `PrayTime` API (`method`, `adjust`, `location`, `timezone`, `tune`, `round`,
  `format`, `set`, `utc_offset`, `set_method`) and `times` / `get_times`.
- Eight returned prayer-time keys: `fajr`, `sunrise`, `dhuhr`, `asr`, `sunset`,
  `maghrib`, `isha`, `midnight`.
- All 11 calculation methods (`MWL`, `ISNA`, `Egypt`, `Makkah`, `Karachi`,
  `Tehran`, `Jafari`, `France`, `Russia`, `Malaysia`, `Singapore`) plus the
  shared `defaults`.
- Asr madhabs (`Standard`/`Hanafi`) and custom shadow factors; four
  high-latitude rules (`None`, `NightMiddle`, `OneSeventh`, `AngleBased`);
  per-prayer `tune`; minute `round`; `24h`/`12h`/`12H`/`x`/`X`/callable
  formats; numeric `utcOffset` and IANA `timezone` display.
- Command-line interface runnable as `python -m praytime` and as the `praytime`
  console script.
- Zero runtime dependencies; `py.typed` marker; pytest suite including
  upstream golden snapshots.

[Unreleased]: https://github.com/zarrabi/praytime/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/zarrabi/praytime/releases/tag/v0.1.0
