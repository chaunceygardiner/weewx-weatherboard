---
title: Home
layout: default
nav_order: 1
permalink: /
---

# WeeWX WeatherBoard — the weather at a glance

[View on GitHub](https://github.com/chaunceygardiner/weewx-weatherboard){: .btn .btn-primary }
[Download weewx-weatherboard.zip](https://github.com/chaunceygardiner/weewx-weatherboard/releases/latest/download/weewx-weatherboard.zip){: .btn }
[Report an issue](https://github.com/chaunceygardiner/weewx-weatherboard/issues){: .btn }

WeatherBoard&trade; is a WeeWX skin inspired by the RainWise LED Weather
Oracle: one page, a dozen readings, and type large enough to read from
across the room.  It is meant to run full screen on a low-cost tablet
mounted on the wall, and it never needs a reload — the numbers change every
couple of seconds.

Does the wind sound ferocious?  Look up and see how fast it is gusting.  Is
the rain coming down hard?  The rate and today's total are already on the
wall.

![WeatherBoard, with the air quality reading](images/WeatherBoard.png)

**Requirements:** WeeWX 4.6 or later, Python 3.7 or later, and
[weewx-loopdata](https://github.com/chaunceygardiner/weewx-loopdata) 7.0 or
later.  The air quality reading additionally needs
[weewx-purple](https://github.com/chaunceygardiner/weewx-purple).

## What is on the board

* Current outside temperature
* Current dew point
* Current wind speed and direction
* Ten-minute high wind gust
* Today's high wind gust
* Current UV index
* Current barometer, with a trend arrow
* Today's total rainfall
* 24-hour total rainfall
* Current rain rate
* Air quality index, when a PurpleAir sensor is configured
* A live label and a clock, showing how current the board is

Without the air quality reading the board keeps the same layout, minus the
AQI cell:

![WeatherBoard without the air quality reading](images/WeatherBoard_no_aqi.png)

## How it stays live

The page itself is ordinary WeeWX output: CheetahGenerator writes it once
per archive interval.  The *readings* do not wait for that.  A few dozen
lines of vanilla javascript in the page poll the `loop-data.txt` file
written by [weewx-loopdata](https://github.com/chaunceygardiner/weewx-loopdata)
— by default every two seconds, which is about as often as a typical
station emits a loop packet — and rewrite the numbers in place.

That makes LoopData a hard requirement rather than a nicety: the board
displays what LoopData puts in that file.  The skin declares the fields it
reads, and LoopData writes them under the report's name in the report's
own units and formats, so an ordinary install has nothing to edit.  See
[Installation](installation.html).

Everything on the board is age-checked.  If the loop data stops advancing —
or stops arriving at all — readings fall back to question marks of the same
width rather than showing you a number that stopped being true ten minutes
ago — see
[When data goes missing](missing-data.html).

## Where to go next

* [Installation](installation.html) — install LoopData, install the skin,
  restart, and keep the tablet awake.
* [Upgrading](upgrading.html) — what each release needs from you, newest
  first.
* [Configuration](configuration.html) — every `[Extras]` setting, what it
  does, and what it defaults to.
* [Reading the board](reading-the-board.html) — what each reading is, the
  legend in the footer, the live label and the clock.
* [When data goes missing](missing-data.html) — the question marks, the
  colors, and how staleness is measured.
* [Troubleshooting](troubleshooting.html) — symptoms, in the order they
  turn up.
