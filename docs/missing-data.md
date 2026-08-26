---
title: When data goes missing
layout: default
nav_order: 6
---

# When data goes missing

[weewx-weatherboard manual](https://chaunceygardiner.github.io/weewx-weatherboard/) · [weewx-weatherboard on GitHub](https://github.com/chaunceygardiner/weewx-weatherboard) · [Report an issue](https://github.com/chaunceygardiner/weewx-weatherboard/issues)

---

A board on the wall is read at a glance, and a glance cannot tell a live
number from one that froze an hour ago.  So the board would rather show
nothing than show something stale: every reading is checked for both age
and existence on every poll, and anything that fails shows question marks
of the same width as the number it replaces.

## The staleness rule

If the loop record is older than [`max_age`](configuration.html#max_age)
seconds — ten by default — readings drawn from it fall back to
placeholders:

| Reading | Placeholder |
|---|---|
| Temperature, dew point | `??.???` |
| Wind | `? ???` |
| Ten-minute gust, today's gust | `?`, `? ???` |
| UV | `?.?` |
| Barometer | `??.??? ?` |
| Rain today, rain 24h, rain rate | `?.??`, `?.?? ????` |
| Air quality index | `???` |

The clock in the lower right is the one exception.  It has its own, longer
threshold — [`clock_max_age`](configuration.html#clock_max_age), two minutes
by default — after which it reads `??:??:??` in the disconnected blue.  It
earns that blue: stale data a web server is still handing out looks exactly
like live data at a glance, and a plausible time in the ordinary red is the
most convincing thing on such a board.  But a reading and a clock go wrong
at different speeds.  A temperature fifteen seconds old has stopped being
true, while a clock fifteen seconds slow still tells you what time it is, so
blueing it there would spend the warning on something that does not need
warning about.  The clock reads `??:??:??` immediately, whatever the age,
when its field is missing from the report's entry altogether.

The board itself keeps working the whole time.  A reading whose field is
missing from `loop-data.txt` — an observation your station does not
report, which LoopData omits — blanks only itself; everything else goes on
updating.

## How age is measured

Age is the difference between two absolute times: the timestamp inside the
loop record, written by the WeeWX station, and the `Date` header on the
HTTP response that carried it, stamped by whatever web server answered.
The browser's own clock is deliberately not consulted.  A wall-mounted
tablet's clock can be badly wrong, and since this one number gates every
reading, a skewed clock used to blank the entire board.

When a cache sits in the middle it preserves the origin's `Date` and adds
an `Age` header; the board adds that back, so a cached response cannot
report itself as younger than it is.

Two further defenses:

* **A unique URL per poll.**  `loop-data.txt` ships without cache headers,
  so browsers fall back on heuristic freshness — and that window widens as
  the file gets older, which is exactly when a cached copy would claim to
  be live.
* **A revalidation request, same-origin only.**  `Cache-Control` is not a
  CORS-safelisted header, so sending it to another host would turn every
  poll into a preflighted request, and a plain file server answering
  `OPTIONS` with 405 would leave the board permanently disconnected.

If no usable `Date` comes back — the common case is a cross-origin
`loop_data_file` whose server does not send
`Access-Control-Expose-Headers: Date` — the board falls back on how long
the record's own timestamp has sat unchanged.  That elapsed time is always
a *lower* bound on the true age, so it can only understate it: a backstop,
not a substitute.

## Losing the file entirely

When the fetch fails outright, the clock in the lower right turns blue and
stays on its last value until a poll succeeds.  What the live label shows
depends on how it failed:

* An HTTP error status shows the status (`HTTP 404`) with
  `check loop_data_file` in place of the clock.  A persistent 404 nearly
  always means `loop_data_file` does not resolve to where LoopData writes
  — the classic being a file in `/dev/shm` with nothing serving it.
* A response that is not json shows `BAD DATA`, with the same hint:
  something is being served at that URL, but it is not LoopData's output.
* LoopData's json with no entry for this report shows `NO ENTRY`, with
  `restart WeeWX` in place of the clock.  LoopData reads each report's
  declaration when weewxd starts, so this is what a freshly installed or
  upgraded board shows until the restart — see
  [Troubleshooting](troubleshooting.html#the-live-label-reads-no-entry-and-the-clock-says-restart-weewx).
* A `loop_data_file` that is not a usable URL shows `BAD URL`, again with
  the same hint.  Nothing was ever sent: the browser rejected the address
  itself.
* A network-level failure — the server gone, the wifi dropped — blanks the
  label instead.  These are usually transient, and a board that shouts
  about every hiccup teaches you to ignore it.

The readings go on ageing throughout.  A failed poll brings no new data, so
the board keeps counting from the last age it knew: once that reaches
[`max_age`](configuration.html#max_age) the numbers fall back to question
marks, exactly as they would if the file were still being served but had
stopped advancing.  A dropped poll or two never blanks a board whose data
is fresh — at a two second refresh the arithmetic has not reached `max_age`
yet — but an outage that outlasts the threshold will, and that is the
point: a ten-minute-old temperature in the board's ordinary red is
indistinguishable from a live one, and the numbers, unlike the clock, have
no color of their own to warn you with.

Polling never stops for any of this.  When the data comes back, so does the
board.
