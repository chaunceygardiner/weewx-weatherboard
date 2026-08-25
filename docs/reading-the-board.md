---
title: Reading the board
layout: default
nav_order: 5
---

# Reading the board

[weewx-weatherboard manual](https://chaunceygardiner.github.io/weewx-weatherboard/) · [weewx-weatherboard on GitHub](https://github.com/chaunceygardiner/weewx-weatherboard) · [Report an issue](https://github.com/chaunceygardiner/weewx-weatherboard/issues)

---

The board is one screen, meant to be read from across the room rather than
studied.  Nothing on it is a link, and nothing needs a click.

![WeatherBoard, with the air quality reading](images/WeatherBoard.png)

## The readings

Top to bottom, with the LoopData field behind each one:

| Reading | Field |
|---|---|
| Outside temperature | `current.outTemp` |
| Dew point | `current.dewpoint` |
| Wind speed and direction | `current.windSpeed.formatted`, `current.windSpeed.raw`, `current.windDir.ordinal_compass` |
| Ten-minute high gust | `10m.windGust.max.formatted` |
| Today's high gust | `day.windGust.max` |
| UV index | `current.UV.formatted` |
| Barometer, with trend arrow | `current.barometer.formatted`, `trend.barometer.code` |
| Rain today | `day.rain.sum.formatted` |
| Rain in the last 24 hours | `24h.rain.sum.formatted` |
| Rain rate | `current.rainRate` |
| Air quality index | `current.pm2_5_1m_aqi.formatted` or `current.pm2_5_aqi.formatted`, with the matching `_color.raw` |

The wind direction is left blank when the wind speed is zero: a compass
point for a dead calm is noise, not information.

The footer's left column is the legend — it names the readings in the order
they appear, so a visitor who has never seen the board can work out what
the big numbers are.  The wording comes from
[Labels](configuration.html#labels).

## The barometer trend

The arrow after the barometer is the direction, and the suffix is the rate:

| Symbol | Meaning |
|---|---|
| ↑ ++ | Rising very rapidly |
| ↑ + | Rising quickly |
| ↑ | Rising |
| ↑ − | Rising slowly |
| − − | Steady |
| ↓ − | Falling slowly |
| ↓ | Falling |
| ↓ + | Falling quickly |
| ↓ ++ | Falling very rapidly |

LoopData computes the trend; the board only draws it.

## The air quality reading

With `show_purple` set, the AQI appears in the footer in the color the EPA
assigns to its range — green through maroon — which comes from
weewx-purple as a field of its own.  The board prefers
purple-proxy's one-minute average when it is present, and falls back to the
plain reading otherwise.

Like every other reading it is age-checked: once the data is older than
[`max_age`](configuration.html#max_age) seconds it shows `???` in the
board's red rather than a number that has stopped being true.

## The live label

At the right of the title bar, in red:

| Shows | Means |
|---|---|
| `LIVE` | The loop record is younger than [`max_age`](configuration.html#max_age) |
| `12s ago` | How old the record actually is — seconds for the first minute, then `1.5m ago`, `2.3h ago`, `1.2d ago` |
| `HTTP 404` | The fetch came back with an error status — almost always `loop_data_file` pointing where nothing is served |
| `BAD DATA` | The fetch succeeded but the body is not LoopData's json |
| `BAD URL` | `loop_data_file` is not a usable URL, so the fetch never left the browser |
| `Expired` | Polling stopped after `expiration_time` hours; click the clock to restart |
| `??` | The loop record carried no usable timestamp, so its age cannot be known — the `fields` line is missing `current.dateTime.raw` |
| (blank) | A network-level failure, presumed transient — the clock turns blue |

The label and the readings share one threshold.  At `max_age`, `LIVE`
gives way to the record's age and every reading falls back to question
marks, together.  The clock keeps its own, longer one —
[`clock_max_age`](configuration.html#clock_max_age) — so a board can read
`45s ago` over a full set of question marks with the time still in red.

## The clock

The lower right corner shows the time of the reading now on the board —
`10:25:34 PM`.

It is the *station's* clock, not the tablet's.  The string comes from
LoopData, rendered through your report's own WeeWX formatter, so it carries
the station's timezone and time format.  That matters on a wall display: a
tablet in another timezone, or with its clock simply set wrong, used to show
a confident time that had nothing to do with when the reading was taken.

The format lives in the field name, in `weewx.conf`:

```
current.dateTime.format("%X")
```

`%X` is the station's own time-of-day format: `09:44:14 PM` where the
station runs a US locale, `21:44:14` under most others.  It cannot be pinned
from the `fields` line — the board looks for the `%X` spelling specifically,
so anything else blanks the corner rather than reformatting it.  The lever is
`LANG` in weewxd's environment; see
[the time format](configuration.html#the-time-format).

The clock ages out too, but later than the readings beside it: once the
loop record is older than
[`clock_max_age`](configuration.html#clock_max_age) seconds — two minutes by
default — the corner reads `??:??:??` in the disconnected blue.  Stale data
that a web server is still handing out looks exactly like live data at a
glance, and a plausible time is the most convincing thing on such a board.

The threshold is longer than the readings' because the clock is answering a
different question.  A temperature fifteen seconds old has stopped being
true; a clock fifteen seconds slow is still a good clock.  The blue means
this is not a clock any more, and it is worth keeping that warning for a
time that would genuinely mislead you.  A field missing from your `fields`
line is the exception and goes blue at once — there is no time to show.

Clicking the clock restarts an expired page.

## Colors

Red is the board: every reading is red on black, which is what makes it
legible across a room and unobtrusive at night.  The exceptions carry
meaning — the AQI in its EPA color, and the clock turning blue, which it
does when the fetch is failing, when the data has fallen further behind
than [`clock_max_age`](configuration.html#clock_max_age), or when the time
field is missing from your `fields` line.
