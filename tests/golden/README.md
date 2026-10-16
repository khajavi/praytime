# Golden snapshots

These files lock the Python port to the exact numerical output of the upstream
JavaScript library `zarrabi/praytime` (v3.2), giving externally verifiable
parity that does not depend on the port's own math.

- `upstream/praytime.js` — vendored upstream library used to produce the goldens.
- `generate.js` — deterministic Node generator (no npm install required).
- `golden.json` — the committed matrix: a JSON array of records, each holding a
  full input configuration (`method`, `date`, `lat`, `lng`, `timezoneConfig`,
  `asr`, `highLats`, `format`) plus the resulting `times` dict.

`tests/test_snapshot.py` reads `golden.json` and asserts the Python output
equals every record exactly (`str` for string formats, `int` for `x`/`X`). The
default pytest suite never invokes Node.

## Regenerating

From the repository root (Node is only needed to regenerate, not to test):

```sh
node tests/golden/generate.js
```

The script writes `tests/golden/golden.json` next to itself. It is
deterministic and self-contained, so repeated runs produce byte-identical
output. The matrix covers all 11 methods × equinoxes/solstices of two years ×
latitudes `0, 21.4, 43.4643, 51.5, 64, 70` × both Asr madhabs × all four
high-latitude rules × formats `24h/12h/x` × both timezone paths (numeric
`UTC`/offset `0`, and IANA `America/Toronto` with the default `'auto'` offset);
dates are rotated so all five dates appear while the record count stays around
3k.

To regenerate and immediately re-check determinism inside pytest:

```sh
PRAYTIME_REGEN=1 python -m pytest tests/test_snapshot.py -k regenerate
```
