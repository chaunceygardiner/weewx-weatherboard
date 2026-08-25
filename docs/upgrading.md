---
title: Upgrading
layout: default
nav_order: 3
---

# Upgrading

[weewx-weatherboard manual](https://chaunceygardiner.github.io/weewx-weatherboard/) · [weewx-weatherboard on GitHub](https://github.com/chaunceygardiner/weewx-weatherboard) · [Report an issue](https://github.com/chaunceygardiner/weewx-weatherboard/issues)

---

Upgrading is the same command as installing — the installer replaces the
skin and leaves your settings alone:

```
weectl extension install weewx-weatherboard.zip
```

(WeeWX 4: `sudo /home/weewx/bin/wee_extension --install weewx-weatherboard.zip`.)
Restart WeeWX afterwards.  Full steps are on the
[Installation](installation.html) page.

Because your existing configuration is preserved, an upgrade can leave new
code reading an old `weewx.conf`.  Everything below is a case where that
matters.  Read the entries newer than the version you are coming from.

{: .note }
`weectl extension install` overwrites `skins/WeatherBoard/` on every
upgrade.  Customizations belong in the report's stanza in `weewx.conf`
(`[[[Extras]]]`, `[[[Labels]]]` and `[[[Units]]]` entries survive
upgrades); edits made directly to the shipped skin files do not.

## Upgrading to 4.0

**WeeWX 4.6 or later is now required.**  WeeWX 4.5 and earlier are no longer
supported, and the installer refuses to run on them.

**LoopData 6.0 or later is now required.**  The clock in the lower right
corner is no longer formatted by the browser; it is a string LoopData
renders with your report's own WeeWX formatter, which is a 6.0 feature.

**One new field is needed in `weewx.conf`:**

```
current.dateTime.format("%X")
```

The installer adds it to `[LoopData] [[Include]] fields` for you, along
with any other field the board reads that your fields line happens to be
missing, so the ordinary upgrade needs no hand-editing.  If your fields
line does not have it — you edited the line afterwards, or LoopData was not
installed when the board was — the corner reads `??:??:??` until it does.

Also new in 4.0, needing nothing from you:

* The clock ages out — `??:??:??` in blue, where it used to show that
  record's timestamp indefinitely — on its own `clock_max_age` Extra, two
  minutes by default.
* The readings' staleness threshold is the `max_age` Extra rather than a
  hardcoded ten seconds, and the live label changes at that same threshold,
  where its `LIVE` tier used to be a separate six seconds.
* The label reports the age in scale — seconds for the first minute, then
  minutes, hours and days — instead of counting seconds forever, and says
  `??` rather than `NaNs ago` when a record carries no usable timestamp.
* `show_purple` is read as a boolean rather than compared against two
  particular spellings of it.
* The readings age out while the fetch is failing, too, instead of holding
  their last values in the ordinary red for as long as the outage lasts.
* A malformed `loop_data_file` reads `BAD URL` rather than failing silently.
* A value that is not a number in `refresh_rate`, `expiration_time`,
  `max_age` or `clock_max_age` falls back to that setting's default instead
  of stopping the updater outright.

The clock change is worth having on a wall display: that clock used to be
rendered from the tablet's own clock, timezone and locale.  A tablet in
another timezone, or with its clock simply set wrong, showed a confident
time that had nothing to do with when the reading was taken.  It now shows
the station's time, in the station's format.  See
[the clock](reading-the-board.html#the-clock) for how to change that
format.

## Upgrading to 3.3

The defaults for `title` and `logo` changed, and a generic logo image now
ships with the skin.  An existing `weewx.conf` keeps whatever it already
has — WeeWX adds missing settings but never overwrites present ones — so
nothing changes for you unless you want it to.  To pick up the new look,
edit `[[[Extras]]]` by hand:

```
title = Acme Weather WeatherBoard&trade;
logo = weatherboard_logo.png
```

## Upgrading to 3.2

No configuration change.  Staleness moved off the browser's clock and onto
the server's, which is what makes a tablet with a wrong clock show a
correct board.  If your `loop_data_file` points at a *different* host, that
host must send `Access-Control-Expose-Headers: Date` for the stronger check
to work; without it the board falls back on how long the record has sat
unchanged.  See [When data goes missing](missing-data.html).

## Upgrading to 3.0

1. WeatherBoard 3.0 reads more fields from `loop-data.txt` than 2.x did.
   Since 4.0 the installer adds them, so installing 4.0 or later fixes this
   for you.
2. The default `loop_data_file` became `loop-data.txt`, relative to the
   report's `HTML_ROOT`.  If your `loop-data.txt` lives elsewhere, set
   `loop_data_file` in `[[[Extras]]]`.
3. `contact_email` and `contact.inc` were removed.
