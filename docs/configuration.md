---
title: Configuration
layout: default
nav_order: 4
---

# Configuration

[weewx-weatherboard manual](https://chaunceygardiner.github.io/weewx-weatherboard/) · [weewx-weatherboard on GitHub](https://github.com/chaunceygardiner/weewx-weatherboard) · [Report an issue](https://github.com/chaunceygardiner/weewx-weatherboard/issues)

---

Everything about the board is configured in the `[[WeatherBoardReport]]`
stanza the installer put in `weewx.conf`.  The skin ships the same settings
in `skins/WeatherBoard/skin.conf`, but those are defaults only: a setting
present in `weewx.conf` wins, and `weewx.conf` is the file to edit — it
survives upgrades, and the shipped skin does not.

```
[StdReport]
    [[WeatherBoardReport]]
        HTML_ROOT = weatherboard
        enable = true
        skin = WeatherBoard
        [[[Extras]]]
            ...
```

`HTML_ROOT` is relative: WeeWX prepends the station's own `HTML_ROOT`, so
`weatherboard` becomes `public_html/weatherboard` on a standard install.
Writing `public_html/weatherboard` here would install the board to
`public_html/public_html/weatherboard`.

## The Extras

{: .note }
The four numeric settings — `refresh_rate`, `expiration_time`, `max_age` and
`clock_max_age` — are checked by the page itself, in the browser, as it
loads.  Anything that is not a number greater than zero, an empty value
included, falls back to that setting's default rather than stopping the
board.  `refresh_rate` is also never armed faster than once a second,
whatever fraction is set.  `refresh_rate` and `expiration_time` have an
upper limit as well,
because they are handed to browser timers and a timer keeps its delay in a
signed 32-bit integer: a value whose milliseconds exceed 2147483647 — about
596 hours for `expiration_time`, 24 days for `refresh_rate` — would wrap to
an arbitrary shorter delay, so it is clamped to that ceiling instead.
`max_age` and `clock_max_age` have no such limit; they are compared against
an age rather than handed to a timer, and a slow station may legitimately
want a large one.  Nothing is reported at report-generation time, so a
mistyped value leaves no trace in the WeeWX log — the board simply runs on
the default.

### `loop_data_file`

Default `loop-data.txt`.  Where the page fetches loop data from, as a URL
the *browser* resolves.  A bare filename therefore means "in this report's
`HTML_ROOT`", which is where LoopData writes if you leave its
`loop_data_dir` at the default.

Pointing this at another host works, with two conditions.  That server must
send `Access-Control-Allow-Origin`, or the browser refuses the fetch and
the board sits permanently disconnected.  And it should also send
`Access-Control-Expose-Headers: Date`, without which the age check falls
back to a weaker measure — see
[When data goes missing](missing-data.html#how-age-is-measured).

### `max_age`

Default `10`.  How old, in seconds, a loop record may be before the readings
it feeds show question marks instead — and the `LIVE` label starts reporting
the record's age rather than claiming the board is current.  The default suits a
station emitting loop packets every couple of seconds; raise it for a slower
one.  It governs a failing fetch as well: the board keeps counting from the
last age it knew, so an outage that outlasts this threshold blanks the
readings just as stale data would.  See
[When data goes missing](missing-data.html).

### `clock_max_age`

Default `120`.  How far behind, in seconds, the clock in the lower right may
fall before it reads `??:??:??` in the disconnected blue.

This is longer than [`max_age`](#max_age) on purpose, because the clock is
answering a different question than the readings are.  A temperature fifteen
seconds old has stopped being true and should show question marks; a clock
fifteen seconds slow is still a good clock, and quite possibly the best one
in the room.  The blue says the board is not a clock any more, so it is
worth saving for a time that would actually mislead you.  Lower it if you
read the corner to the second; raise it if you only want to be told when the
board has plainly died.

It is never allowed below [`max_age`](#max_age): a clock going blue while
the readings beside it are still live would be nonsense, so raising
`max_age` for a slow station carries the clock up with it, whatever this is
set to.

Two things still turn the clock blue immediately, whatever this is set to: a
fetch that fails, and a `fields` line with no time field in it, where there
is no time to show at all.

### `refresh_rate`

Default `2`.  Seconds between polls.  A good choice is the rate at which
your station's driver emits loop packets: polling faster than the data
arrives just re-reads the same record.  Values below 1 poll once a second.

### `title`, `subtitle`, `meta_title`

The branding across the top of the board and in the browser's title bar.
`Acme Weather` is a placeholder; put your own site's name here.  HTML
entities are allowed (the shipped default carries a `&trade;`), and
`subtitle` may contain links — a common use is a way back to a fuller site:

```
subtitle = '<a href="..">Full Site</a> | <a href="../about_us.html">About Us</a>'
```

With no `meta_title` the browser tab reads
`WeatherBoard&trade;—<your station location>`.

### `logo`

Default `weatherboard_logo.png`.  The mark at the left of the title bar.  A
generic weather icon ships with the skin; point this at your own image, or
set it to `""` for no mark at all.  The value is a URL as the browser sees
it, so a bare filename must name a file in this report's `HTML_ROOT`.

### `page_update_pwd`

Default `foobar` — change it.  When it appears on the URL as
`?page_update_pwd=...`, the page never expires.  This is what keeps a
wall-mounted tablet updating indefinitely.  The legacy spelling
`?pageUpdate=...` still works.  An empty setting means the default, not
"no password": with an empty one every visitor's absent password would
match it, and no page would ever expire.  Quote it in `weewx.conf` if it
contains a comma.

{: .note }
This password is visible to anyone who views the page source, by design.
It is a keep-alive gate, not a secret.

### `expiration_time`

Default `4`.  Hours before a page *without* the password stops polling.
The board then shows `Expired` and `CLICK-ME`; a click starts it again.
The point is to keep a forgotten browser tab from polling your server for
days.

Values above about 596 hours are clamped to 596 — see the note under
[The Extras](#the-extras) above.  Even so, a large value is not the way to make a board
that never expires: set `page_update_pwd` and put it on the URL, which is
what the wall-tablet case wants.

### `show_purple`

A boolean, `False` by default.  Set it to `True` to show the air quality
index, which requires
[weewx-purple](https://github.com/chaunceygardiner/weewx-purple) and two
more LoopData fields — see
[Installation](installation.html#3-what-the-installer-added).  With it off,
the AQI cell stays empty and the footer legend names one fewer reading.

### `googleAnalyticsId`, `analytics_host`

Both empty by default.  With an ID set, the board loads Google Analytics.
`analytics_host` restricts that to one hostname, which keeps a development
copy of the page out of your statistics.

## Labels

The wording in the footer legend, and the AQI heading, come from
`[[[Labels]]] [[[[Generic]]]]`:

| Label | Default |
|---|---|
| `air_quality_index` | Air Quality Index |
| `legend` | Legend |
| `rainToday` | Rain Today |
| `rain24h` | Rain 24h |
| `ten_min_max_gust` | 10m Gust |
| `time_of_day` | Time |
| `high_gust_today` | Today's High Gust |

Override any of them in `weewx.conf` to change the legend's wording.

## Units and number formats

The board's *numbers* are formatted by LoopData, using the report named by
LoopData's own `target_report`, not by this skin.  The
`[[[Units]]] [[[[StringFormats]]]]` entries in the WeatherBoard stanza —
`%.0f` for wind speeds, `%.1f` for temperatures — apply to the values this
skin renders itself at generation time.

To change how a live reading is formatted, change it in the report LoopData
formats against.  The same is true of units: the board shows whatever units
that report is configured for.

## The time format

The clock in the lower right is one of the LoopData fields, and its format
travels with the field name:

```
current.dateTime.format("%X")
```

`%X` is your station's own time-of-day format — `09:44:14 PM` where the
station runs a US locale, `21:44:14` under most others.

That locale is the one in weewxd's environment (`LANG`), not the `lang`
setting on a report: LoopData formats loop packets in its own thread,
outside the report cycle where WeeWX applies a report's `lang`.  Practically
this is the same locale the rest of your WeeWX pages use, with one case
worth knowing — a weewxd started with no `LANG` at all, which is common in
containers and hand-written unit files, falls back to the C locale and
renders 24-hour times everywhere, this board included.  Set `LANG` in the
service environment if that is not what you want.

One locale effect is worth knowing before you go looking for a css bug: a
`%X` that carries a timezone — the Indian subcontinent and several Arabic
locales, among others — is too many characters for the corner it sits in and
wraps onto a second line.  The clock is set in 95px monospace, in a footer
cell 65% of the board's width.  The lever there is `LANG` too — not the
`fields` line, for the reason below.

The format cannot be pinned from the `fields` line.  The board looks for the
`%X` spelling specifically, so putting a different strftime string there —
`current.dateTime.format("%H:%M:%S")`, say — does not reformat the clock: it
removes the field the board reads, and the corner falls back to `??:??:??`
until you put `%X` back.  `LANG` is the only lever on the format.

## Changing the styling

All styling lives in `skins/WeatherBoard/weatherboard.css`.  It is copied
to `HTML_ROOT` once, under `copy_once`, so a change reaches the browser on
the first report cycle after a WeeWX restart.  Remember that an upgrade
replaces the shipped file: keep a copy of anything you change.
