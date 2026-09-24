---
title: Troubleshooting
layout: default
nav_order: 7
---

# Troubleshooting

[weewx-weatherboard manual](https://chaunceygardiner.github.io/weewx-weatherboard/) · [weewx-weatherboard on GitHub](https://github.com/chaunceygardiner/weewx-weatherboard) · [Report an issue](https://github.com/chaunceygardiner/weewx-weatherboard/issues)

---

Symptoms below, roughly in the order they turn up.  Most of them start
with the clock: when something is wrong, the clock says what — see
[the status line](reading-the-board.html#the-status-line).  The failure
codes are the same in every language.

## No page at `<weewx-url>/weatherboard/`

The board's HTML is written by the normal WeeWX report cycle, typically
every five minutes.  Wait for a cycle after installing and restarting.  If
it still is not there, check the WeeWX log for report errors, and confirm
`enable = true` in the `[[WeatherBoardReport]]` stanza.

## Every reading is missing, and the clock reads `WAITING`

The page has loaded but no poll has come back yet, successful or not.
That lasts a second or two; if it lasts longer, the browser is not
fetching at all — look in its developer console.

## Every reading is missing, and the clock shows an age

`47 S AGO`, `7 M AGO`: the fetch is fine, and the data behind it is not
advancing.  In order of likelihood:

1. **LoopData is not running.**  Check the WeeWX log at startup for its
   banner, and look at `loop-data.txt` itself — is its timestamp moving?
2. **weewxd has stopped.**  Its web server may still be handing out the
   last file it wrote.
3. **The station has stopped sending loop packets.**  LoopData writes what
   it is given.

A station that emits loop packets less often than every
[`max_age`](configuration.html#max_age) seconds — ten by default —
flickers between its time and an age as each packet arrives and ages.
Raise `max_age` for it.

## The clock reads `HTTP 404`

`loop_data_file` is a URL as the *browser* resolves it, not a path on the
server, relative to this report's `HTML_ROOT`.  As shipped,
`../loopdata/loop-data.txt`, it points where a stock LoopData writes — its
own sample report's directory, `loopdata`, beside this one.  If LoopData
writes somewhere else — `/dev/shm` is a popular choice — that directory has
to be reachable over HTTP and this setting has to name it, or LoopData has
to write somewhere under `public_html` instead.

## The clock reads `NO ENTRY`

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

## The clock reads `BAD DATA`

Something is being served at that URL, but it is not LoopData's json.  Fetch
the URL yourself and look at what comes back; a directory listing or an
error page is the usual answer.

## The clock reads `BAD URL`

`loop_data_file` is not an address the browser can use at all — a bare
`http://`, or a bracket that does not close, like `http://[bad` — so the
request is rejected before anything is sent.  Check the value in
`weewx.conf`.  It is a URL as the *browser* resolves it, so a bare filename
or a plain path is fine; only a malformed absolute URL reaches this state.
A value that is merely *wrong* — a path with a space in it, or one that
points somewhere nothing is served — is a valid URL, so it is sent and
comes back `HTTP 404` instead.

## The clock reads `NO CONNECT`

The request failed outright or timed out: the web server is down, the
tablet's network is, or the file is on another host that does not allow
the fetch — see [Cross-origin trouble](#cross-origin-trouble).  A
passing `NO CONNECT` that clears on the next poll is a network hiccup,
and the readings ride it out: they are shown as missing only once the
data they hold passes `max_age`.

## The clock reads `NO CLOCK`

The report's entry has no usable `current.dateTime.raw`, so the board
cannot tell how old the data is, and will not vouch for data it cannot
age.  The clock's fields ship in the skin's declaration, so one is missing
only if the declaration was overridden — a `[[[LoopData]]] [[[[fields]]]]`
group named `clock` under the report's stanza in `weewx.conf` replaces the
skin's — or the shipped `skin.conf` was edited.  Put the field back and
restart WeeWX.

## The date under the clock is blank

The readout board takes its date from `current.dateTime.format("%Y-%m-%d")`,
and LoopData reads a report's fields only when weewxd starts.  Right after
an upgrade to 5.2, restart WeeWX; running a report by hand is not enough.
If the date is still blank, the declaration was overridden: a
`[[[LoopData]]] [[[[fields]]]]` group named `clock` under the report's
stanza in `weewx.conf` replaces the skin's, and needs the field added.

## The clock reads `EXPIRED TAP`

The page polled for `expiration_time` hours without the keep-alive
password, and stopped.  Tap it to restart.  For a permanently mounted
tablet, set your own `page_update_pwd` and open the board as
`...?page_update_pwd=yourpassword` — see
[Installation](installation.html#5-point-the-tablet-at-it-and-keep-it-awake).

## The title is not the one I set

Without a `title` the boards show the station's `location`, from
`[Station]` in `weewx.conf`, and a title still reading the Acme Weather
placeholder earlier installers wrote counts as no title.  A `title` has to
be inside `[[[Extras]]]` in the `[[WeatherBoardReport]]` stanza to be
read, and it takes effect at the next report cycle — the title is set when
the page is generated, not by the page's polling.

## The time is not the one I expected

It is the station's time, not the tablet's, so a time off by hours means
the station's clock or timezone is — what you are seeing is what the
station believes.  12 or 24 hour comes from the report's language, or
from [`clock_format`](configuration.html#clock_format) if it is set.

## A reading I expected is not on the board

UV, solar radiation and air quality show only when the station's current
record carries them — see
[`show_uv`, `show_radiation`, `show_aqi`](configuration.html#show_uv-show_radiation-show_aqi).
Check that the sensor is reporting, or set the matching setting to `true`
to show the panel regardless.  For air quality, both `pm2_5` and the
index computed from it, `pm2_5_aqi`, have to be there: without an
extension such as
[weewx-purple](https://github.com/chaunceygardiner/weewx-purple) there is
no index to show.  A `show_purple = False` left in `weewx.conf` by an
earlier release also turns air quality off.

Feels like needs WeeWX's apparent temperature, which it computes from the
temperature, humidity and wind.

## One reading is missing and the rest are fine

Your station does not report that observation: LoopData omits a field
whose observation is not in the loop packet.  Look in the
`WeatherBoardReport` entry of `loop-data.txt` for the field named on the
[Reading the board](reading-the-board.html) page.

## A status word has a letter in the wrong typeface on the readout board

The readout board sets the status line in Bebas Neue, which has the
Latin letters and the accented capitals of the Western European
languages.  A `[[[Texts]]]` override in `weewx.conf` that uses any other
letter draws it in whatever typeface the tablet falls back to.  See
[Languages](configuration.html#languages).

## A CSS change has not taken effect

`weatherboard.css` is copied under `copy_once`, so it reaches `HTML_ROOT`
on the first report cycle after a WeeWX restart.  Restart WeeWX, or copy
the file into place yourself.

## Cross-origin trouble

If `loop_data_file` points at another host, that server must send
`Access-Control-Allow-Origin` or the browser blocks every poll and the
clock reads `NO CONNECT`.  Adding `Access-Control-Expose-Headers: Date`
restores the full staleness check; without it the board falls back on a
weaker measure, described in
[How age is measured](missing-data.html#how-age-is-measured).
