
// PrayTime Test
// By Hamid Zarrabi-Zadeh


"use strict";

const { PrayTime } = require('../src/praytime');


// ----------------------- Initialize Test Data ---------------------

// Test Location: Waterloo, ON, Canada
const latitude = 43.4643;
const longitude = -80.5204;

// Test Date: Fab 21, 2025
const date = [2025, 2, 21];
const timezone = 'America/Toronto';


// ----------------------- Run Test and Validate --------------------

const praytime = new PrayTime();

praytime.method('ISNA')
    .location([latitude, longitude])
    .timezone(timezone);

test('Test prayer times', () => {
    const times = praytime.getTimes(date);
    expect(times.fajr).toBe('05:52');
    expect(times.dhuhr).toBe('12:36');
    expect(times.asr).toBe('15:32');
    expect(times.maghrib).toBe('18:02');
});

test('Test time formats', () => {
    expect(praytime.format('x').getTimes(date).asr).toBe(1740169920000);
    expect(praytime.format('X').getTimes(date).asr).toBe(1740169920);
    expect(praytime.format('12h').getTimes(date).asr).toBe('3:32 PM');
    expect(praytime.format('12H').getTimes(date).asr).toBe('3:32');
    expect(praytime.format('24h').getTimes(date).asr).toBe('15:32');
});

test('Test timezones', () => {
    expect(praytime.utcOffset(-4.5).getTimes(date).fajr).toBe('06:22');
    expect(praytime.utcOffset(-300).getTimes(date).fajr).toBe('05:52');
});

test('Test rounding method', () => {
    expect(praytime.round('down').getTimes(date).asr).toBe('15:32');
    expect(praytime.round('up').getTimes(date).asr).toBe('15:33');
    expect(praytime.round('nearest').getTimes(date).asr).toBe('15:32');
});

test('Test adjust method', () => {
    const times = praytime.adjust({
        fajr: 19.7,
        dhuhr: "11 min",
    }).getTimes(date);
    expect(times.fajr).toBe('05:26');
    expect(times.dhuhr).toBe('12:47');
});

test('Test tuning method', () => {
    const times = praytime.tune({
        asr: 11,
        maghrib: 4.5,
    }).getTimes(date);
    expect(times.asr).toBe('15:43');
    expect(times.maghrib).toBe('18:07');
});

