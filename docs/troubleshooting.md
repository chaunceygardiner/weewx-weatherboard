---
title: Troubleshooting
layout: default
nav_order: 7
---

# Troubleshooting

[weewx-weatherboard manual](https://chaunceygardiner.github.io/weewx-weatherboard/) · [weewx-weatherboard on GitHub](https://github.com/chaunceygardiner/weewx-weatherboard) · [Report an issue](https://github.com/chaunceygardiner/weewx-weatherboard/issues)

---

Symptoms below, roughly in the order they turn up.

## No page at `<weewx-url>/weatherboard/`

The board's HTML is written by the normal WeeWX report cycle, typically
every five minutes.  Wait for a cycle after installing and restarting.  If
it still is not there, check the WeeWX log for report errors, and confirm
`enable = true` in the `[[WeatherBoardReport]]` stanza.

## Every reading shows question marks

The page is rendering but the loop data is not reaching it.  In order of
likelihood:

1. **LoopData is not running.**  Check the WeeWX log at startup for its
   banner, and look at `loop-data.txt` itself — is its timestamp moving?
2. **The board cannot fetch the file.**  Open the browser's developer
   console on the board page.  A 404 there means `loop_data_file` does not
   point at a URL your web server actually serves; see below.
3. **LoopData does not know the report yet.**  The live label reads
   `NO ENTRY` — see below.

The clock in the lower right may still be showing a time in red while this
is going on; that is deliberate, not a leftover.  It has a longer threshold
of its own — see [`clock_max_age`](configuration.html#clock_max_age).

## The live label reads `HTTP 404`, and the clock says `check loop_data_file`

`loop_data_file` is a URL as the *browser* resolves it, not a path on the
server, relative to this report's `HTML_ROOT`.  As shipped,
`../loopdata/loop-data.txt`, it points where a stock LoopData writes — its
own sample report's directory, `loopdata`, beside this one.  If LoopData
writes somewhere else — `/dev/shm` is a popular choice — that directory has
to be reachable over HTTP and this setting has to name it, or LoopData has
to write somewhere under `public_html` instead.

## The live label reads `NO ENTRY`, and the clock says `restart WeeWX`

`loop-data.txt` is being served and is LoopData's json, but it has no
`WeatherBoardReport` entry.  LoopData reads each report's declaration when
weewxd starts, while the report engine reads the skin afresh every cycle
— so between installing (or upgrading) the board and restarting WeeWX,
the new page exists and its entry does not.  Restart WeeWX.

If a restart does not clear it, LoopData is not writing this report's
entry at all.  Check the WeeWX log at startup: LoopData logs one line per
declaring report, and the board's should be among them.  (Renaming the
`[[WeatherBoardReport]]` stanza is not the cause: the entry is keyed by
the report name, and the page reads the name of the stanza that built it,
so the two move together.)  Two things do get here: a `loop_data_file`
pointing at a file some *other* station's LoopData writes, which carries
that station's reports and not this one; and a LoopData older than 7.0,
which writes no report entries at all, only the flat keys of the old
`fields` line — the installer refuses that, but a downgrade afterwards
lands here.

## The live label reads `BAD DATA`

Something is being served at that URL, but it is not LoopData's json.  Fetch
the URL yourself and look at what comes back; a directory listing or an
error page is the usual answer.

## The live label reads `BAD URL`

`loop_data_file` is not an address the browser can use at all — a bare
`http://`, or a bracket that does not close, like `http://[bad` — so the
request is rejected before anything is sent.  Check the value in
`weewx.conf`.  It is a URL as the *browser* resolves it, so a bare filename
or a plain path is fine; only a malformed absolute URL reaches this state.
A value that is merely *wrong* — a path with a space in it, or one that
points somewhere nothing is served — is a valid URL, so it is sent and
comes back `HTTP 404` instead.

## The clock reads `??:??:??`

There are three causes, and the live label beside the clock tells them apart.

If the label reads an age — `3.0m ago` — the loop data has fallen further
behind than [`clock_max_age`](configuration.html#clock_max_age), two minutes
by default.  The fetch is fine; the data behind it is not.

If the label reads `??`, the loop record carries no usable
`current.dateTime.raw`, so the board cannot work out how old it is and will
not vouch for a time it cannot age.  The clock blanks even though
`current.dateTime.format("%X")` is present and perfectly fresh — so look for
`current.dateTime.raw` in the report's entry, not the `%X` field.

Otherwise the entry does not carry `current.dateTime.format("%X")` at all.
Both fields ship in the skin's declaration, so either is missing only if
the declaration was overridden — a `[[[LoopData]]] [[[[fields]]]]` group
named `clock` under the report's stanza in `weewx.conf` replaces the
skin's — or the shipped `skin.conf` was edited.  Put the field back and
restart WeeWX.

Note that the readings blank well before the clock does, at
[`max_age`](configuration.html#max_age).  A board showing question marks
everywhere with the time still in red is not a bug: a reading seconds old
has stopped being true, while a clock seconds slow is still a clock.

If you put a different strftime string in the declaration, that is the
cause: the board looks for the `%X` spelling specifically, so anything else
leaves it with no field to read.  Put `%X` back; see
[the time format](configuration.html#the-time-format).

## The time format is not the one I expected

The clock is formatted by the station: `%X` gives `09:44:14 PM` under a US
locale and `21:44:14` under most others.  That locale comes from weewxd's
environment (`LANG`), not from a report's `lang` — a weewxd started with no
`LANG`, which is usual in a container, renders 24-hour times.  Set `LANG` in
the service environment.  Pinning a different strftime string in the
declaration is not an alternative: the board looks for the `%X` spelling,
so anything else leaves the corner reading `??:??:??` — see
[the time format](configuration.html#the-time-format).

If the time is off by hours rather than formatted differently, check the
station's clock and timezone: as of 4.0 the board shows the station's time,
so what you are seeing is what the station believes.

## The clock wraps onto two lines

The clock is set in 95px monospace, in a footer cell 65% of the board's
width, and some locales' `%X` includes a timezone — more characters than
that cell can hold.  This is a locale effect rather than a styling one: the
lever is weewxd's `LANG`, not the declaration and not the stylesheet.  See
[the time format](configuration.html#the-time-format).

## The board says `Expired`, with `CLICK-ME` in the corner

The page polled for `expiration_time` hours without the keep-alive
password, and stopped.  Click it to restart.  For a permanently mounted
tablet, set your own `page_update_pwd` and open the board as
`...?page_update_pwd=yourpassword` — see
[Installation](installation.html#5-point-the-tablet-at-it-and-keep-it-awake).

## The clock is blue

Either the last fetch failed or the loop data has fallen more than
[`clock_max_age`](configuration.html#clock_max_age) seconds behind.  Read the
live label beside it: blank means a network-level failure, usually transient;
`HTTP nnn`, `BAD DATA` and `BAD URL` are covered above; and an age past `clock_max_age` —
`3.0m ago`, say — means the fetch is fine and the data behind it is not.  Look
at whether weewxd is running and `loop-data.txt` is still being written.

A smaller age there, `12s ago` or `45s ago`, leaves the clock red on purpose:
it is behind, but not so far behind that it has stopped being a clock.

## The air quality reading is missing

It needs `show_purple = True` and a working
[weewx-purple](https://github.com/chaunceygardiner/weewx-purple).  If the
cell shows `???`, the two AQI fields are not arriving — the skin declares
them, so LoopData is omitting them because the station reports no
`pm2_5`; if it is simply empty and the footer legend does not mention air
quality, `show_purple` is off.

## One reading shows question marks and the rest are fine

Your station does not report that observation: LoopData omits a field
whose observation is not in the loop packet.  Look in the
`WeatherBoardReport` entry of `loop-data.txt` for the field named on the
[Reading the board](reading-the-board.html#the-readings) page.

## A CSS change has not taken effect

`weatherboard.css` is copied under `copy_once`, so it reaches `HTML_ROOT`
on the first report cycle after a WeeWX restart.  Restart WeeWX, or copy
the file into place yourself.

## Cross-origin trouble

If `loop_data_file` points at another host, that server must send
`Access-Control-Allow-Origin` or the browser blocks every poll and the
board never updates.  Adding `Access-Control-Expose-Headers: Date` restores
the full staleness check; without it the board falls back on a weaker
measure, described in
[How age is measured](missing-data.html#how-age-is-measured).
