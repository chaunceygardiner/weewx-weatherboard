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
survives upgrades, and the shipped skin does not.  Both boards,
`index.html` and `splitflap.html`, come from this one report and share
every setting.

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

## Settings that are commented out

Some settings appear in `weewx.conf` with a `#` in front of them, and a
comment above saying what they do:

```
            # Seconds between polls.  A good choice is the rate at which
            # your station's driver emits loop packets.  Never armed faster
            # than once a second, whatever is set.
            #refresh_rate = 2
```

That is not a setting that has been turned off.  A commented line does
nothing, so the value the skin itself ships — in
`skins/WeatherBoard/skin.conf` — is the one that applies, and the line in
`weewx.conf` is there to tell you what that value is and give you something
to edit.  Leaving it commented is what lets a later release improve a
default: an upgrade replaces the skin, and never rewrites `weewx.conf`.

Go by what you see in your own file, not by which release you installed:

* Where it reads `#refresh_rate = 2`, remove the `#` and change the value.
* Where it reads `refresh_rate = 2`, with no `#`, just change the value.
* Where the setting is not there at all, add it inside `[[[Extras]]]`.

All three are correct configurations, and which one you have depends only on
when the stanza was written.  WeeWX never rewrites a setting that is already
in `weewx.conf`, so an upgrade leaves yours exactly as it is — including the
comments, which an upgrade will not add to a stanza that already exists.

{: .important }
Keep an uncommented setting inside `[[[Extras]]]`, at the same indentation as
the settings around it.  A setting that ends up one level out — directly
under `[[WeatherBoardReport]]` — is read by nothing, and nothing will warn
you.

## The Extras

{: .note }
The three numeric settings — `refresh_rate`, `expiration_time` and
`max_age` — are checked by the page itself, in the browser, as it loads.
Anything that is not a number greater than zero, an empty value included,
falls back to that setting's default rather than stopping the board.
`refresh_rate` is also never armed faster than once a second, whatever
fraction is set.  `refresh_rate` and `expiration_time` have an upper limit
as well, because they are handed to browser timers and a timer keeps its
delay in a signed 32-bit integer: a value whose milliseconds exceed
2147483647 — about 596 hours for `expiration_time`, 24 days for
`refresh_rate` — would wrap to an arbitrary shorter delay, so it is
clamped to that ceiling instead.  `max_age` has no such limit; it is
compared against an age rather than handed to a timer, and a slow station
may legitimately want a large one.  Nothing is reported at
report-generation time, so a mistyped value leaves no trace in the WeeWX
log — the board simply runs on the default.

### `loop_data_file`

Default `../loopdata/loop-data.txt`.  Where the pages fetch loop data
from, as a URL the *browser* resolves, relative to this report's
`HTML_ROOT`.  The default is where a stock LoopData writes: its
`loop_data_dir` default is its own sample report's `HTML_ROOT`,
`loopdata`, beside this one.  Either side can move — LoopData's
`loop_data_dir` or this setting — as long as the browser can fetch the
result.  An empty setting means the default, not "this page": an empty URL
resolves to the page itself, so the board would fetch its own HTML,
find no loop data in it and show `BAD DATA` for ever.

Pointing this at another host works, with two conditions.  That server must
send `Access-Control-Allow-Origin`, or the browser refuses every fetch and
the clock reads `NO CONNECT`.  And it should also send
`Access-Control-Expose-Headers: Date`, without which the age check falls
back to a weaker measure — see
[When data goes missing](missing-data.html#how-age-is-measured).

### `max_age`

Default `10`.  How old, in seconds, a loop record may be before every
reading it feeds is shown as missing and the clock gives way to the
record's age.  The default suits a station emitting loop packets every
couple of seconds; raise it for a slower one.  It governs a failing fetch
as well: the board keeps counting from the last age it knew, so an outage
that outlasts this threshold blanks the readings just as stale data would.
See [When data goes missing](missing-data.html).

### `refresh_rate`

Default `2`.  Seconds between polls.  A good choice is the rate at which
your station's driver emits loop packets: polling faster than the data
arrives just re-reads the same record.  Values below 1 poll once a second.

### `title`

The line across the top of both boards.  Without it the boards show the
station's `location`, from `[Station]` in `weewx.conf`.  HTML entities are
allowed (`&trade;`, `&amp;`).  A title too long for the screen is cut
short with an ellipsis.

The installer writes no `title`, because its default is your station, not
a value.  Earlier releases wrote an Acme Weather placeholder, live; a
station still carrying it gets its location, as if nothing were set.

### `meta_title`

The browser tab's title.  Without it the tab shows the board's
[`title`](#title).  HTML entities are allowed, and the Acme Weather
placeholder earlier installers wrote counts as unset.

### `page_update_pwd`

Default `foobar` — change it.  When it appears on the URL as
`?page_update_pwd=...`, the page never expires.  This is what keeps a
wall-mounted tablet updating indefinitely.  The legacy spelling
`?pageUpdate=...` still works.  An empty setting means the default, not
"no password": with an empty one every visitor's absent password would
match it, and no page would ever expire.  Quote it in `weewx.conf` if it
contains a comma.

Percent-encode it when you put it on the URL.  The value there is
URL-decoded before it is compared, so a `%` followed by two hexadecimal
digits decodes to something else and stops matching: a password of
`rain%20or%20shine` has to be written `rain%2520or%2520shine` on the URL.
Write every `%` as `%25` and it is right in every case.  `&` and `#` need
the same treatment -- `%26` and `%23` -- because both end the parameter
where they stand.

{: .note }
This password is visible to anyone who views the page source, by design.
It is a keep-alive gate, not a secret.

### `expiration_time`

Default `4`.  Hours before a page *without* the password stops polling.
The clock then reads `EXPIRED TAP`, in blue; a tap anywhere on the board
starts it again.  The point is to keep a forgotten browser tab from
polling your server for days.

Values above about 596 hours are clamped to 596 — see the note under
[The Extras](#the-extras) above.  Even so, a large value is not the way to
make a board that never expires: set `page_update_pwd` and put it on the
URL, which is what the wall-tablet case wants.

### `clock_format`

`12` or `24`.  Left unset, the report's language decides: English shows a
12 hour clock (`2:36:52 PM`), and every other language a 24 hour one
(`14:36:52`).  Either way it is the station's time — see
[the clock](reading-the-board.html#the-clock).

### `show_uv`, `show_radiation`, `show_aqi`

Each defaults to `auto`, which shows the reading when the station's
current record carries it at report time, so a station without the
sensor never shows an empty panel.  `true` forces the reading on and
`false` forces it off.  The pages are regenerated every archive interval,
so a sensor that is added or goes quiet is picked up within one.

For air quality, `auto` needs both the sensor's `pm2_5` and the index the
board shows, `pm2_5_aqi`, which an extension such as
[weewx-purple](https://github.com/chaunceygardiner/weewx-purple) computes
from it: a station with the sensor but not the index would otherwise show
a panel with nothing ever in it.

`show_purple`, the setting earlier releases used, is still honored: while
`show_aqi` is `auto`, a `show_purple` in `weewx.conf` decides instead.  A
station configured under 4.0 or 4.1 may have `show_purple = False`
written live; with an air quality sensor, delete it or set `show_aqi`.

The fields these readings need are declared whatever the settings — see
[The fields the board reads](installation.html#the-fields-the-board-reads).

### `googleAnalyticsId`, `analytics_host`

Both empty by default.  With an ID set, the board loads Google Analytics.
`analytics_host` restricts that to one hostname, which keeps a development
copy of the page out of your statistics.

### Settings from earlier releases

`subtitle`, `logo` and `clock_max_age` are no longer read.  The boards
have one line of title and no band around it, and the clock gives way to
the data's age at `max_age` like everything else.  They can be deleted
from `weewx.conf`, or left: nothing reads them.

## Languages

The board speaks Danish (`da`), Dutch (`nl`), English (`en`), French
(`fr`), German (`de`), Italian (`it`), Norwegian (`no`), Spanish (`es`)
and Swedish (`sv`).  Choose one with the report's standard WeeWX `lang`
setting:

```
[[WeatherBoardReport]]
    lang = de
```

That translates every label and status word, the wind direction's compass
points (`NNØ` in Danish, `ONO` in German), and sets the clock to 24 hour.
Restart WeeWX after changing it: LoopData renders the wind direction in
the report's language, and reads the report's settings only when weewxd
starts.

The translations live in `skins/WeatherBoard/lang/`, one file per
language, with English the reference.  To reword a single string, add a
`[[[Texts]]]` section to the report's stanza in `weewx.conf` with just
the strings you want to change, keyed by their English:

```
[[WeatherBoardReport]]
    [[[Texts]]]
        "FEELS LIKE" = "APPARENT"
```

The stanza outranks the language file, and unlike the skin it survives an
upgrade.

{: .note }
The readout board sets its status words in Bebas Neue, which has the
Latin letters and the accented capitals of the Western European
languages.  A status word reworded with a letter outside that set is
drawn in whatever typeface the tablet falls back to.  The labels under
the readings have no such limit.

## Units and number formats

The board's numbers are formatted by LoopData with *this report's* own
converter and formatter — since LoopData 7.0 every declaring report is its
own target — so the live readings and the unit labels the pages render at
generation time never disagree.  By default they follow the station's own
formats, from `[StdReport] [[Defaults]]`.

To change a format or a unit for the board alone, set it in the
WeatherBoard stanza the way you would for any WeeWX report: `[[[Units]]]
[[[[StringFormats]]]]` for a format, `unit_system = metric` on the stanza,
or `[[[Units]]] [[[[Groups]]]]` for one group.  A reading too wide for its
panel shrinks that row of the readout board, and the split-flap board gives up
a decimal before a figure runs off its row, so nothing needs adjusting.
Earlier releases' installers wrote the wind and temperature formats into
the stanza; that copy is harmless and can stay or go.

## Changing the styling

All styling lives in `skins/WeatherBoard/weatherboard.css`.  It is copied
to `HTML_ROOT` once, under `copy_once`, so a change reaches the browser on
the first report cycle after a WeeWX restart.  Remember that an upgrade
replaces the shipped file: keep a copy of anything you change.
