---
title: Installation
layout: default
nav_order: 2
---

# Installation

[weewx-weatherboard manual](https://chaunceygardiner.github.io/weewx-weatherboard/) · [weewx-weatherboard on GitHub](https://github.com/chaunceygardiner/weewx-weatherboard) · [Report an issue](https://github.com/chaunceygardiner/weewx-weatherboard/issues)

---

**Requirements:** WeeWX 4.6 or later, Python 3.7 or later, and
[weewx-loopdata](https://github.com/chaunceygardiner/weewx-loopdata) 7.0 or
later.  There is no Python in this skin beyond its installer: the board is
Cheetah templates and vanilla javascript.

{: .important }
LoopData is not optional.  Every number on the board comes from the
`loop-data.txt` file LoopData writes; without it the page renders once and
then shows question marks forever.  Install it first.

## 1. Install weewx-loopdata

Follow the
[LoopData installation instructions](https://chaunceygardiner.github.io/weewx-loopdata/installation.html).
Version 7.0 or later is required, and the board's installer refuses to run
without it.  Since 7.0 a report declares the fields it needs in its own
skin, and LoopData writes them into `loop-data.txt` under the report's
name; the board reads that entry and nothing else.

Note where LoopData writes `loop-data.txt` — its `loop_data_dir` — because
the board has to be able to fetch that file over HTTP.  LoopData's default
is its own sample report's directory, `loopdata`, which sits beside this
board's `weatherboard` under `public_html`, and the board's shipped
`loop_data_file` points exactly there; if you move LoopData's file, move
that setting with it (step 3).

## 2. Install the skin

Download the latest release,
[weewx-weatherboard.zip](https://github.com/chaunceygardiner/weewx-weatherboard/releases/latest/download/weewx-weatherboard.zip).

WeeWX 5, pip install (`weectl` lives in the virtual environment, so
activate it first; yours may sit elsewhere, `~/weewx-venv` is the usual
place):

```
source ~/weewx-venv/bin/activate
weectl extension install weewx-weatherboard.zip
```

WeeWX 5, Debian or Red Hat package install (`weectl` is already on the
path).  No `sudo`: that install put your account in the `weewx` group,
which owns the files -- if you installed WeeWX in this same login
session, log out and back in first so the group membership takes
effect.

```
weectl extension install weewx-weatherboard.zip
```

WeeWX 4:

```
sudo /home/weewx/bin/wee_extension --install weewx-weatherboard.zip
```

(Adjust the path if WeeWX is installed elsewhere.)

The installer checks that LoopData 7.0 or later is installed — if not it
stops, saying whether LoopData is missing or which older version it found
— and adds a `[[WeatherBoardReport]]` stanza to `[StdReport]` in
`weewx.conf`.  That is all it does.

## 3. What the installer added

The report stanza:

```
[[WeatherBoardReport]]
    HTML_ROOT = weatherboard
    enable = true
    skin = WeatherBoard
    [[[Extras]]]
        meta_title = Acme Weather at a Glance WeatherBoard&trade;
        title = Acme Weather WeatherBoard&trade;
        subtitle = Updated continuously.
        logo = weatherboard_logo.png
        loop_data_file = ../loopdata/loop-data.txt
        max_age = 10
        clock_max_age = 120
        expiration_time = 4
        page_update_pwd = foobar
        googleAnalyticsId = ""
        analytics_host = ""
        show_purple = False
        refresh_rate = 2
```

Every one of those is described on the
[Configuration](configuration.html) page.  At minimum, replace the Acme
Weather placeholders with your own site's name and choose your own
`page_update_pwd`.  `loop_data_file` as shipped points at where a stock
LoopData writes — its own sample report's `HTML_ROOT`, `loopdata`, beside
the board's — so with both extensions at their defaults it needs nothing;
if LoopData writes somewhere else, point it there (a URL relative to the
board's page).  A board pointed where nothing is written reads `HTTP 404`
with `check loop_data_file` in the corner.

{: .note }
WeeWX merges settings that are missing but never overwrites ones already
there, so on an upgrade your edits survive and only genuinely new settings
appear.

### The fields the board reads

Nothing in `weewx.conf` lists them.  The skin declares them itself, in
`skins/WeatherBoard/skin.conf`, as a `[LoopData] [[fields]]` section of
named groups — LoopData's
[declaration](https://chaunceygardiner.github.io/weewx-loopdata/declaring-fields.html)
— and LoopData writes them into `loop-data.txt` under the report's name,
`WeatherBoardReport`, converted and formatted the way this report would
render them:

```
current.dateTime.raw, current.dateTime.format("%X"), current.outTemp,
current.dewpoint, current.windSpeed.formatted, current.windSpeed.raw,
current.windDir.ordinal_compass, 10m.windGust.max.formatted,
day.windGust.max, current.UV.formatted, current.barometer.formatted,
trend.barometer.code, day.rain.sum.formatted, 24h.rain.sum.formatted,
current.rainRate, current.pm2_5_aqi.formatted, current.pm2_5_aqi_color.raw
```

The last two are the air quality reading, shown with `show_purple` set.
They are declared whether or not it is: LoopData omits a field whose
observation the station does not report, so on a station without
weewx-purple they simply never appear, and turning `show_purple` on later
needs nothing but the setting.

The installer does not touch the older `[LoopData] [[Include]] fields`
line in `weewx.conf`.  If you upgraded from 4.0, that line still carries
the board's fields, and LoopData warns at startup that the line is
deprecated; leave it alone — a later LoopData release removes it.  See
[Upgrading](upgrading.html#upgrading-to-41).

{: .note }
Running [purple-proxy](https://github.com/chaunceygardiner/purple-proxy)
needs nothing extra here: the board reads the AQI of the `pm2_5`
observation the WeeWX database carries, and with the proxy that reading is
already a two-minute average; weewx-purple averages the sensor's two
channels besides.

## 4. Restart WeeWX

```
sudo systemctl restart weewx
```

The board appears at `<your weewx url>/weatherboard/` after the next report
cycle — typically within five minutes.

The restart is not optional.  LoopData reads each report's declaration
when weewxd starts, so until then there is no `WeatherBoardReport` entry
in `loop-data.txt`, and a board page that is somehow already there reads
`NO ENTRY` with `restart WeeWX` in the corner.

## 5. Point the tablet at it, and keep it awake

Open the page full screen on the tablet.  As shipped, the board stops
polling after four hours; a click on the clock in the lower right starts it
again.  That guard exists so a browser tab forgotten on a laptop does not
poll your server forever.

A tablet on the wall is exactly the case where you do not want it.  Choose
your own `page_update_pwd` in `weewx.conf` and open the board with it on
the URL:

```
http://<your weewx url>/weatherboard/index.html?page_update_pwd=yourpassword
```

With the password present the page never expires.

{: .note }
The password is visible in the page source, by design.  It is a keep-alive
gate, not a secret — it exists so that a random visitor's browser tab
expires and yours does not.
