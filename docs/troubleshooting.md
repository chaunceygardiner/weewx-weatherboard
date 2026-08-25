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
3. **The fields are missing.**  A field the board reads that is not in
   `[LoopData] [[Include]] fields` never arrives.  Installing the extension
   again adds any that are missing.

The clock in the lower right may still be showing a time in red while this
is going on; that is deliberate, not a leftover.  It has a longer threshold
of its own — see [`clock_max_age`](configuration.html#clock_max_age).

## The live label reads `HTTP 404`, and the clock says `check loop_data_file`

`loop_data_file` is a URL as the *browser* resolves it, not a path on the
server.  A bare filename means "in this report's `HTML_ROOT`".  If LoopData
writes somewhere else — `/dev/shm` is a popular choice — that directory has
to be reachable over HTTP, or LoopData has to write into `HTML_ROOT`
instead.

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
`current.dateTime.format("%X")` is present and perfectly fresh — so check
`current.dateTime.raw` on the `fields` line, not the `%X` field.

Otherwise the `fields` line does not carry
`current.dateTime.format("%X")` at all.  For either missing field, install
the extension again (the installer adds it, along with any other field the
board reads that is missing), or add it by hand and restart WeeWX.

Note that the readings blank well before the clock does, at
[`max_age`](configuration.html#max_age).  A board showing question marks
everywhere with the time still in red is not a bug: a reading seconds old
has stopped being true, while a clock seconds slow is still a clock.

If you put a different strftime string in the `fields` line, that is the
cause: the board looks for the `%X` spelling specifically, so anything else
leaves it with no field to read.  Put `%X` back; see
[the time format](configuration.html#the-time-format).

## The time format is not the one I expected

The clock is formatted by the station: `%X` gives `09:44:14 PM` under a US
locale and `21:44:14` under most others.  That locale comes from weewxd's
environment (`LANG`), not from a report's `lang` — a weewxd started with no
`LANG`, which is usual in a container, renders 24-hour times.  Set `LANG` in
the service environment.  Pinning a different strftime string in the
`fields` line is not an alternative: the board looks for the `%X` spelling,
so anything else leaves the corner reading `??:??:??` — see
[the time format](configuration.html#the-time-format).

If the time is off by hours rather than formatted differently, check the
station's clock and timezone: as of 4.0 the board shows the station's time,
so what you are seeing is what the station believes.

## The clock wraps onto two lines

The clock is set in 95px monospace, in a footer cell 65% of the board's
width, and some locales' `%X` includes a timezone — more characters than
that cell can hold.  This is a locale effect rather than a styling one: the
lever is weewxd's `LANG`, not the `fields` line and not the stylesheet.  See
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

It needs `show_purple = True`, a working
[weewx-purple](https://github.com/chaunceygardiner/weewx-purple), and four
LoopData fields.  If the cell shows `???`, the fields are not arriving; if
it is simply empty and the footer legend does not mention air quality,
`show_purple` is off.

## One reading shows question marks and the rest are fine

Either your station does not report that observation, or that one field is
missing from the `fields` line.  Look in `loop-data.txt` for the field named
on the [Reading the board](reading-the-board.html#the-readings) page.

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
