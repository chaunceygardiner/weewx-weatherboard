---
title: Reading the board
layout: default
nav_order: 5
---

# Reading the board

[weewx-weatherboard manual](https://chaunceygardiner.github.io/weewx-weatherboard/) · [weewx-weatherboard on GitHub](https://github.com/chaunceygardiner/weewx-weatherboard) · [Report an issue](https://github.com/chaunceygardiner/weewx-weatherboard/issues)

---

The board is one screen, meant to be read from across the room rather than
studied.  Nothing on it is a link, and nothing needs a tap — except an
expired page, which a tap starts again.

There are two boards, and they show the same station.  Open whichever you
prefer on the tablet: `index.html` for the LED board, `splitflap.html` for
the split-flap board.

Across the top of both is one line of title: the station's `location`
from `weewx.conf`, or the board's own [`title`](configuration.html#title)
if one is set.  A title too long for the screen ends in an ellipsis.

## The LED board

![The LED board](images/LEDBoard.png)

Every reading is set in seven-segment digits over their own unlit
segments, the way a real LED display looks.  The panels, top to bottom,
with the LoopData field behind each reading:

| Panel | Reading | Field |
|---|---|---|
| Temperature | Outside | `current.outTemp.formatted` |
| | Dew point | `current.dewpoint.formatted` |
| Wind | Speed and direction | `current.windSpeed.formatted`, `current.windDir.ordinal_compass` |
| | Ten-minute high gust | `10m.windGust.max.formatted` |
| | Today's high gust | `day.windGust.max.formatted` |
| Barometer | Pressure, with its trend arrow | `current.barometer.formatted`, `trend.barometer.code` |
| Rain | Today | `day.rain.sum.formatted` |
| | Last 24 hours | `24h.rain.sum.formatted` |
| | Rate | `current.rainRate.formatted` |
| Sun | UV index | `current.UV.formatted` |
| | Solar radiation | `current.radiation.formatted` |
| Air quality | Index, in its level's color | `current.pm2_5_aqi.formatted`, `current.pm2_5_aqi_color.raw` |
| Comfort | Humidity | `current.outHumidity.formatted` |
| | Feels like | `current.appTemp.formatted` |
| Clock | The station's time, and the status line | `current.dateTime.format("%H:%M:%S")` |

The label under each reading names it and gives its unit, in the report's
own units and language.  On a station whose driver reports no gusts, the
two gust readings show the highest wind speed over the same ten minutes
and the same day instead — `10m.windSpeed.max.formatted` and
`day.windSpeed.max.formatted` — which is what a gust there would have
been; the split-flap board's `G` does the same.  The wind direction is
left blank when the speed shows 0: a compass point for a dead calm is
noise, not information.

UV, solar radiation and air quality show only on a station that has them
— see [`show_uv`, `show_radiation`, `show_aqi`](configuration.html#show_uv-show_radiation-show_aqi)
— and feels like only where WeeWX can compute it.  A panel with nothing to
show is left out, and its row closes up.

## The split-flap board

![The split-flap board](images/SplitFlapBoard.png)

Each row is twelve flaps.  When a character changes, its flap runs forward
through the letters to the new one, as a departure board's does.

| Row | Shows | Fields |
|---|---|---|
| Time | The station's time, and the status line | `current.dateTime.format("%H:%M:%S")` |
| Temp | Outside temperature, and today's high | `current.outTemp.formatted`, `day.outTemp.max.formatted` |
| Dew pt | Dew point, and the relative humidity | `current.dewpoint.formatted`, `current.outHumidity.formatted` |
| Wind | Direction and speed, or `CALM`, and the ten-minute gust | `current.windDir.ordinal_compass`, `current.windSpeed.formatted`, `10m.windGust.max.formatted` |
| Barometer | Pressure, and its trend arrow | `current.barometer.formatted`, `trend.barometer.code` |
| Rain | Today's rain, and the rate per hour | `day.rain.sum.formatted`, `current.rainRate.formatted` |
| Air | The index, and a word for its level | `current.pm2_5_aqi.formatted` |

A figure too wide for its place gives up decimals rather than running off
the row: a rate of `145.6` beside `123.4` today reads `123 145.6/HR`.

### The lamps

The lamp at the end of a row lights only when the row has something to
say, judged by the figure the row shows:

| Row | Lamp | When |
|---|---|---|
| Time | amber, red, blue | The status line — see [below](#the-status-line) |
| Wind | red | The ten-minute gust is 25 mph (40 km/h) or more |
| Barometer | orange | Below 29.70 inHg (1005.8 mbar) |
| | blue | Above 30.20 inHg (1022.7 mbar) |
| Rain | blue | Rain is falling |
| Air | the level's color | Above 50, worse than good, in the color of the index's level |

## The barometer trend

The arrow after the barometer is one arrow whose angle is the trend's
pace, on both boards:

| Arrow | Meaning |
|---|---|
| straight up | Rising very rapidly |
| steeply up | Rising quickly |
| up | Rising |
| gently up | Rising slowly |
| level | Steady |
| gently down | Falling slowly |
| down | Falling |
| steeply down | Falling quickly |
| straight down | Falling very rapidly |

Each step is 22.5 degrees.  LoopData computes the trend; the board only
draws it.

## The air quality reading

The index shows in the color the EPA assigns to its range — green
through maroon — which comes from the air quality extension as a field of
its own.  The split-flap board adds a word for the level: `GOOD`,
`MODERATE`, `USG` (unhealthy for sensitive groups), `UNHLTHY`,
`V UNHLTH`, `HAZARD`.

With [purple-proxy](https://github.com/chaunceygardiner/purple-proxy) as
the source the reading is a two-minute average, and weewx-purple averages
the sensor's two channels besides.

## The status line

Neither board has a separate LIVE label.  The clock is the status line:

| Shows | Color | Means |
|---|---|---|
| `2:36:52 PM` | red | The data is fresh: this is the station's time |
| `47 S AGO` | amber | The data is more than [`max_age`](configuration.html#max_age) seconds old, for its first minute |
| `7 M AGO`, `2 H AGO`, `1 D AGO` | red, blinking | The data is older than a minute |
| `HTTP 404` | red, blinking | The fetch came back with an error status — almost always `loop_data_file` pointing where nothing is served |
| `BAD DATA` | red, blinking | The fetch succeeded but the body is not LoopData's json |
| `NO ENTRY` | red, blinking | LoopData's json, but with no entry for this report — WeeWX has not been restarted since the board was installed |
| `BAD URL` | red, blinking | `loop_data_file` is not a usable URL, so the fetch never left the browser |
| `NO CONNECT` | red, blinking | The request failed or timed out: the server gone, the network down |
| `NO CLOCK` | red, blinking | The report's entry carries no usable `current.dateTime.raw`, so its age cannot be known |
| `EXPIRED TAP` | blue | The page stopped polling after [`expiration_time`](configuration.html#expiration_time) hours; tap anywhere to start it again |
| `WAITING` | amber | The page has loaded and no data has arrived yet |

On the split-flap board the words are on the time row's flaps, and its
lamp carries the color.  The status words are translated — see
[Languages](configuration.html#languages) — while the failure codes stay
as they are, so this page and the troubleshooting page find them in any
language.

The status line and the readings share one threshold.  At `max_age` the
clock gives way to the data's age and every reading is shown as missing,
together — see [When data goes missing](missing-data.html).

## The clock

The clock shows the time of the reading now on the board.  It is the
*station's* clock, not the tablet's: LoopData renders
`current.dateTime.format("%H:%M:%S")` through your report's own WeeWX
formatter, so it carries the station's timezone.  That matters on a wall
display: a tablet in another timezone, or with its clock simply set
wrong, would otherwise show a confident time that had nothing to do with
when the reading was taken.

The board lays the time out itself, 12 or 24 hour, by
[`clock_format`](configuration.html#clock_format) or the report's
language.

## Colors

Red is the board: every reading is red on black, which is what makes it
legible across a room and unobtrusive at night.  The exceptions carry
meaning — the air quality index in its level's color, and the status line
in amber, red or blue.  On the split-flap board the flaps are white, and
the lamps carry the color.
