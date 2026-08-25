---
title: Installation
layout: default
nav_order: 2
---

# Installation

[weewx-weatherboard manual](https://chaunceygardiner.github.io/weewx-weatherboard/) · [weewx-weatherboard on GitHub](https://github.com/chaunceygardiner/weewx-weatherboard) · [Report an issue](https://github.com/chaunceygardiner/weewx-weatherboard/issues)

---

**Requirements:** WeeWX 4.6 or later, Python 3.7 or later, and
[weewx-loopdata](https://github.com/chaunceygardiner/weewx-loopdata) 6.0 or
later.  There is no Python in this skin beyond its installer: the board is
Cheetah templates and vanilla javascript.

{: .important }
LoopData is not optional.  Every number on the board comes from the
`loop-data.txt` file LoopData writes; without it the page renders once and
then shows question marks forever.  Install it first.

## 1. Install weewx-loopdata

Follow the
[LoopData installation instructions](https://chaunceygardiner.github.io/weewx-loopdata/installation.html).
Version 6.0 or later is required: the board asks LoopData for a
report-formatted timestamp, which is a 6.0 feature.

Note where LoopData writes `loop-data.txt` — its `loop_data_dir` — because
the board has to be able to fetch that file over HTTP.  The simplest
arrangement, and the default, is to let LoopData write into this report's
own `HTML_ROOT`.

## 2. Install the skin

Download the latest release,
[weewx-weatherboard.zip](https://github.com/chaunceygardiner/weewx-weatherboard/releases/latest/download/weewx-weatherboard.zip).

WeeWX 5:

```
weectl extension install weewx-weatherboard.zip
```

WeeWX 4:

```
sudo /home/weewx/bin/wee_extension --install weewx-weatherboard.zip
```

(Adjust the path if WeeWX is installed elsewhere.)

The installer does two things: it adds a `[[WeatherBoardReport]]` stanza to
`[StdReport]` in `weewx.conf`, and it adds the LoopData fields the board
reads to your `[LoopData] [[Include]] fields` line.

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
        loop_data_file = loop-data.txt
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
`page_update_pwd`.

{: .note }
WeeWX merges settings that are missing but never overwrites ones already
there, so on an upgrade your edits survive and only genuinely new settings
appear.

The fields the installer adds to `[LoopData] [[Include]]`:

```
current.dateTime.raw, current.dateTime.format("%X"), current.outTemp,
current.dewpoint, current.windSpeed.formatted, current.windSpeed.raw,
current.windDir.ordinal_compass, 10m.windGust.max.formatted,
day.windGust.max, current.UV.formatted, current.barometer.formatted,
trend.barometer.code, day.rain.sum.formatted, 24h.rain.sum.formatted,
current.rainRate
```

Fields already in your list are left alone, and nothing is removed or
reordered: that line is yours, and it usually feeds other pages too.

If `[LoopData]` is not in `weewx.conf` yet — you installed the board before
LoopData — the installer cannot add anything.  It prints the list and tells
you what to do about it.

The simplest cure is to install LoopData and then **install the board
again**; the second run finds `[LoopData]` and adds the fields for you.  Do
not skip that second run on the grounds that both extensions are now
installed.  LoopData's own installer writes a `fields` line for its sample
page, and WeeWX adds settings that are missing but never overwrites ones
already there — so a `fields` line LoopData just created is left exactly as
it is, without any of the fields the board reads, and the board comes up
showing question marks everywhere.  Installing the board again fixes it.

With `show_purple` set, two more fields are needed for the air quality
reading:

```
current.pm2_5_aqi.formatted, current.pm2_5_aqi_color.raw
```

The installer adds those too when it finds `show_purple = True` already in
your configuration.  If you turn `show_purple` on later, either add the two
fields by hand or simply install the extension again — it will notice they
are missing.

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
