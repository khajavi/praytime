#!/usr/bin/env node
/*
 * praytime golden generator (Phase 7, specs.md §12.4).
 *
 * Runs the vendored upstream JavaScript library over a deterministic matrix
 * and writes the resulting prayer-time dictionaries to `golden.json` beside
 * this script. The Python suite (`tests/test_snapshot.py`) reads that JSON and
 * asserts exact string/int equality, giving externally verifiable parity that
 * is independent of the port's own math.
 *
 * Regenerate with:
 *
 *     node tests/golden/generate.js
 *
 * The write is deterministic: no randomness, no clock, stable loop order, and
 * compact one-record-per-line JSON, so repeated runs are byte-identical. The
 * script is self-contained (no npm install) and exits after writing.
 */
"use strict";

const fs = require("fs");
const path = require("path");

const { PrayTime } = require(path.join(__dirname, "upstream", "praytime.js"));

// --- Matrix dimensions (specs.md §12.4) ---------------------------------

const METHODS = [
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
];

// Equinoxes/solstices across two years plus a non-solstice winter date.
const DATES = [
    [2025, 3, 20],
    [2025, 6, 21],
    [2025, 9, 23],
    [2025, 12, 21],
    [2024, 2, 21],
];

const LATS = [0, 21.4, 43.4643, 51.5, 64, 70];
const LNG = -80.5204;

const ASRS = ["Standard", "Hanafi"];
const HIGHLATS = ["None", "NightMiddle", "OneSeventh", "AngleBased"];
const FORMATS = ["24h", "12h", "x"];

// Two timezone configurations: (a) the deterministic numeric-offset path and
// (b) the IANA/`'auto'` offset path.
const TZ_CONFIGS = ["utc0", "America/Toronto"];

// --- Per-record computation ---------------------------------------------

function buildRecord(method, date, lat, tzConfig, asr, highLats, format) {
    const praytime = new PrayTime(method);
    praytime.location([lat, LNG]);
    if (tzConfig === "utc0") {
        praytime.timezone("UTC").utcOffset(0);
    } else {
        praytime.timezone(tzConfig);
    }
    praytime.adjust({ asr: asr, highLats: highLats });
    praytime.format(format);
    const times = praytime.getTimes(date);

    return {
        method: method,
        date: date,
        lat: lat,
        lng: LNG,
        timezoneConfig: tzConfig,
        asr: asr,
        highLats: highLats,
        format: format,
        times: times,
    };
}

// --- Build the matrix ----------------------------------------------------

// Full product of every dimension except `date`; the date is rotated across
// records so all five dates appear while the record count stays ~3k instead
// of ~16k (specs.md §12.4 allows sampling dates rather than exploding).
const records = [];
let index = 0;
for (const method of METHODS) {
    for (const lat of LATS) {
        for (const asr of ASRS) {
            for (const highLats of HIGHLATS) {
                for (const format of FORMATS) {
                    for (const tzConfig of TZ_CONFIGS) {
                        const date = DATES[index % DATES.length];
                        index += 1;
                        records.push(
                            buildRecord(method, date, lat, tzConfig, asr, highLats, format)
                        );
                    }
                }
            }
        }
    }
}

// One record per line: valid JSON, small, and diff-friendly.
const output = "[\n" + records.map((record) => JSON.stringify(record)).join(",\n") + "\n]\n";
fs.writeFileSync(path.join(__dirname, "golden.json"), output);
