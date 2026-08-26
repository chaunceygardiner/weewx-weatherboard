## Copyright (C)2020-2026 by John A Kline (john@johnkline.com)
## Distributed under the terms of the GNU Public License (GPLv3)
## See LICENSE for your rights.
##
## Shared scaffolding for the realtime updater(s).  Must be #included inside
## a <script> element.  The including updater must define
## updateReadings(result, age), which is called on every successful poll of
## the loop data file.  jsstr(), from jsstr.inc, writes an Extras value as
## an escaped javascript string literal.

#errorCatcher Echo
#include "jsstr.inc"
## The keep-alive password is whatever the user typed, and both the README
## and the manual tell everyone to change it from the shipped placeholder.
## Interpolated bare into a quoted javascript string, an apostrophe -- a
## password like don't-sleep -- closed the literal early and threw at the
## top of this script, which aborted the WHOLE updater: nothing polled, no
## live label, no clock.  jsstr (see jsstr.inc) writes it as an
## escaped literal, so it reaches javascript exactly as typed and still
## matches what the user puts on the URL.
## An empty setting would match the empty string every visitor without a
## password on the URL presents, and the page would never expire for anyone,
## so empty means the shipped default -- the same foobar skin.conf carries.
  var page_update_pwd = $jsstr($Extras.get('page_update_pwd', 'foobar') or 'foobar');
  // Every numeric Extra below is whatever the user typed in weewx.conf.
  // Interpolated bare, a non-numeric value renders as a javascript
  // identifier rather than a number (the word ten, not 10) and throws a
  // ReferenceError at the top of this script.  That aborts the WHOLE
  // updater: updateCurrent is
  // never defined, nothing ever polls, and the board sits on its
  // report-cycle numbers with no live label and no clock, which is the
  // worst failure this file has.  A typo in a knob the manual invites you
  // to tune must not be able to do that, so each value is passed through
  // as a string and parsed here, falling back to the default it would have
  // had if the setting were absent.  (The two that feed a timer are also
  // bounded, at the timer: see clampDelay.)
  // A blank setting is treated as absent rather than as a number, because
  // Number("") is 0, not NaN -- so an empty max_age would mean every
  // reading is always stale, and an empty refresh_rate would poll as fast
  // as the browser could schedule it.  Zero and negatives are rejected for
  // the same reason: every one of these knobs is a count of seconds or
  // hours, and none of them has a meaningful value at or below zero.
  function numExtra(raw, dflt) {
    if (typeof raw !== "string" || raw.trim() === "") {
      return dflt;
    }
    var n = Number(raw);
    return (isFinite(n) && n > 0) ? n : dflt;
  }
  // A browser timer keeps its delay in a signed 32-bit int, so a delay
  // past 2147483647 ms wraps: expiration_time = 8760, a year, came out
  // near seventeen days, and values just over the edge fired at once -- a
  // station reaching for "never expire" got the opposite, silently.  The
  // delay is clamped to the ceiling where the timer is armed, so the
  // seconds-or-hours-to-milliseconds conversion is written exactly once.
  // Clamped, not dropped to the default: a station that typed 8760 asked
  // for a very long time, and 596 hours honours that where four would
  // not.  max_age and clock_max_age are never handed to a timer, so they
  // are not bounded; a station emitting slowly may legitimately want a
  // very large one.
  function clampDelay(ms) {
    return Math.min(ms, 2147483647);
  }
## Each value is written by jsstr, like page_update_pwd above: however a
## setting is malformed -- a quote, a backslash, a newline from a
## triple-quoted weewx.conf value, a < that would end the script element --
## it reaches numExtra as a well formed string literal, fails Number(), and
## falls back to the default.
  var refresh_rate = numExtra($jsstr($Extras.get('refresh_rate', 2)), 2);
  var expiration_time = numExtra($jsstr($Extras.get('expiration_time', 4)), 4);
  // How old a loop record may be before the readings it feeds show
  // question marks instead.  The default suits a station emitting loop
  // packets every couple of seconds; raise it for a slower one.
  var max_age = numExtra($jsstr($Extras.get('max_age', 10)), 10);
  // The clock gets its own, longer threshold, because it is answering a
  // different question than the readings are.  A temperature a minute old
  // is a stale reading; a clock a minute slow is still a clock.
  var clock_max_age = numExtra($jsstr($Extras.get('clock_max_age', 120)), 120);
  // The clock's threshold never sits below the readings'.  The two are
  // configured independently, and a station that raised max_age alone --
  // which the docs invite, for a slow emitter -- would otherwise show a
  // blue ??:??:?? beside a LIVE label and a full set of live readings,
  // exactly the incoherence two thresholds exist to avoid.  Raising
  // max_age therefore carries the clock up with it.
  if (clock_max_age < max_age) {
    clock_max_age = max_age;
  }

  var pageTimedOut = false;
  var expiredShown = false;
  var errorCount = 0;

  // Staleness tracking.  lastDateTime/lastChangeAt record how long the loop
  // data has sat unchanged; cacheBuster puts every poll on a URL of its own.
  // Date.now() only seeds a unique starting value here and is never read
  // back as a clock.  lastDateTime starts undefined rather than null
  // because JSON can deliver null for a missing timestamp, and that has to
  // read as a change rather than as "same as last time"; lastChangeAt is
  // seeded here so the elapsed backstop is never measured from null.
  var lastDateTime;
  var lastChangeAt = performance.now();
  var cacheBuster = Date.now();

  // The last poll that rendered, kept so a FAILED poll can go on ageing
  // its readings.  A failure never reaches updateReadings, so without
  // these the numbers would hold their last values for as long as the
  // outage lasted.  See markDisconnected.
  //
  // The seed matters as much as the update.  Before the first successful
  // poll the board is showing the numbers CheetahGenerator rendered into
  // the page, which are as old as the last report cycle -- an archive
  // interval, typically minutes.  A board that loads while the fetch is
  // already failing would otherwise present those indefinitely, in the
  // ordinary red, having never confirmed a single reading.  So the clock
  // on them starts at page load.
  var lastResult = null;
  var lastGoodAge = 0;
  var lastSuccessAt = performance.now();

  function addLoadEvent(func) {
    var oldonload = window.onload;
    if (typeof window.onload != 'function') {
      window.onload = func;
    } else {
      window.onload = function() {
        if (oldonload) {
          oldonload();
        }
        func();
      }
    }
  }

  function getUrlParam(paramName) {
      var name, regexS, regex, results;
      name = paramName.replace(/(\[|\])/g, '\\$1');
      regexS = '[\\?&]' + name + '=([^&#]*)';
      regex = new RegExp(regexS);
      results = regex.exec(window.location.href);
      if (results === null) {
          return '';
      }
      // decodeURIComponent throws on a lone % -- a password like 100% put
      // on the URL as typed -- and this runs at the top of the script, so
      // the throw would abort the whole updater.  The raw value is the
      // best reading of a string that does not decode.
      try {
          return decodeURIComponent(results[1]);
      } catch (e) {
          return results[1];
      }
  }

  // True when url resolves to this page's own origin; a relative path
  // always does.  URL() throws on a malformed value, which counts as
  // cross-origin here so a bad config cannot add a preflight on top of
  // whatever else is wrong with it.
  function sameOrigin(url) {
    try {
      return new URL(url, window.location.href).origin === window.location.origin;
    } catch (e) {
      return false;
    }
  }

  function expirePage() {
    pageTimedOut = true;
  }

  function clickListener() {
    // The CLICK-ME listener was added to activity-string; remove it there.
    var activityElement = document.getElementById("activity-string");
    activityElement.removeEventListener('click', clickListener);
    activityElement.innerHTML = "";
    // Belt and braces: the expiry paint in updateCurrent already cleared
    // the disconnected color before attaching this listener, and nothing
    // repaints the corner after expiry, so this is a no-op unless that
    // changes.
    activityElement.classList.remove("disconnected");
    document.getElementById("live-label").innerHTML = "";
    // restart everything
    pageTimedOut = false;
    expiredShown = false;
    setPageExpirationTimer();
  }

  function setPageExpirationTimer() {
    // 'pageUpdate' is the legacy name for the keep-alive URL parameter.
    var pwd = getUrlParam('page_update_pwd');
    if (pwd === '') {
      pwd = getUrlParam('pageUpdate');
    }
    if (pwd !== page_update_pwd) {
      // expire in N hours
      setTimeout(expirePage, clampDelay(1000 * 60 * 60 * expiration_time));
    }
  }

  // Arrow shows the direction of the barometer trend; the +/- suffix shows
  // how fast it is changing (++ very fast, + fast, blank medium, - slow).
  const barometer_symbols = {
     '4': '<i class="arrow up_dir"></i>&plus;&plus;',
     '3': '<i class="arrow up_dir"></i>&plus;&nbsp;',
     '2': '<i class="arrow up_dir"></i>&nbsp;&nbsp;',
     '1': '<i class="arrow up_dir"></i>&minus;&nbsp;',
     '0': '&minus;&minus;&nbsp;',
    '-1': '<i class="arrow down_dir"></i>&minus;&nbsp;',
    '-2': '<i class="arrow down_dir"></i>&nbsp;&nbsp;',
    '-3': '<i class="arrow down_dir"></i>&plus;&nbsp;',
    '-4': '<i class="arrow down_dir"></i>&plus;&plus;',
  };

  function decode_rgb(i) {
    var red   = i >> 16;
    var green = (i & 0xFF00) >> 8;
    var blue  = i & 0xFF;
    return 'rgb(' + red + ',' + green + ',' + blue + ')';
  }

  // Pad a reading on the left to `width` characters using no-break spaces
  // so the monospace columns don't shift as values change length.
  // True for a json object proper: not null, not an array, not a
  // primitive.  loopdata's file is one, and so is each report's entry in
  // it; anything else that parses is some other server's json.
  function isJsonObject(value) {
    return value !== null && typeof value === 'object'
        && !Array.isArray(value);
  }

  function padLeft(value, width) {
    return value.padStart(width).replaceAll(' ', '&nbsp;');
  }

  function setReading(id, html) {
    document.getElementById(id).innerHTML = html;
  }

  // Reading updaters shared by both boards.

  function updateWind(result, age) {
    if (age < max_age && result.hasOwnProperty("current.windSpeed.formatted")) {
      var windSpeed = padLeft(result["current.windSpeed.formatted"], 2);
      var windBearing = "";
      if (result["current.windSpeed.raw"] != 0.0
          && result.hasOwnProperty("current.windDir.ordinal_compass")) {
        windBearing = result["current.windDir.ordinal_compass"];
      }
      windBearing = windBearing.padEnd(3).replaceAll(' ', '&nbsp;');
      setReading("windSpeedAndBearing", windSpeed + " " + windBearing);
    } else {
      setReading("windSpeedAndBearing", '&nbsp;?&nbsp;???');
    }
  }

  function updateUV(result, age) {
    var uv;
    if (age < max_age && result.hasOwnProperty("current.UV.formatted")) {
      uv = padLeft(result["current.UV.formatted"], 4);
    } else {
      uv = "&nbsp;?.?";
    }
    setReading("current.UV.formatted", uv);
  }

  function updateBarometer(result, age) {
    var barometer_value;
    if (age < max_age && result.hasOwnProperty("current.barometer.formatted")) {
      barometer_value = result["current.barometer.formatted"] + "&nbsp;";
      if (result.hasOwnProperty("trend.barometer.code")) {
        barometer_value += barometer_symbols[result["trend.barometer.code"]];
      } else {
        barometer_value += "???"
      }
    } else {
      barometer_value = "??.???&nbsp;?&nbsp;&nbsp;"
    }
    setReading("barometer", barometer_value);
  }

  function updateRain(result, age) {
    if (age < max_age && result.hasOwnProperty("day.rain.sum.formatted")) {
      setReading("day.rain.sum.formatted", result["day.rain.sum.formatted"]);
    } else {
      setReading("day.rain.sum.formatted", '?.??');
    }

    if (age < max_age && result.hasOwnProperty("24h.rain.sum.formatted")) {
      setReading("24h.rain.sum.formatted", result["24h.rain.sum.formatted"]);
    } else {
      setReading("24h.rain.sum.formatted", '?.??');
    }

    if (age < max_age && result.hasOwnProperty("current.rainRate")) {
      setReading("current.rainRate", result["current.rainRate"]);
    } else {
      setReading("current.rainRate", '?.??&nbsp;????');
    }
  }

  // What the live label says about the age of the loop record.  Same
  // progressive formatting as liveseasons' getActivityStr: a board that
  // has been behind since yesterday should say so in days, not in eighty
  // thousand seconds.
  function getActivityStr(age) {
    if (isNaN(age)) {
      // The record carried no usable timestamp, so its age is unknown.
      // Every comparison against NaN is false, so an unguarded label falls
      // through to the seconds line and concatenates it into "NaNs ago".
      // Say what the readings beside it say.
      return "??";
    }
    // The LIVE cut comes before the ladder, not after it as liveseasons
    // has it.  That order was harmless while the cut was a hardcoded six
    // seconds, always below the one-minute rung; with max_age
    // configurable, a board set to 120 would read "1.5m ago" at ninety
    // seconds -- while every reading beside it was still live.
    if (age < max_age) {
      return "LIVE";
    }
    if (age >= (3600 * 24)) {
      return (age / (3600.0 * 24)).toFixed(1) + "d ago";
    }
    if (age >= 3600) {
      return (age / 3600.0).toFixed(1) + "h ago";
    }
    if (age >= 60) {
      return (age / 60.0).toFixed(1) + "m ago";
    }
    return age + "s ago";
  }

  function markDisconnected(code, hint) {
    // With a code and hint (the config-shaped failures: an HTTP error
    // status, a body that isn't json) the label and clock name the
    // problem; without them (a network-level failure, presumed
    // transient) the label blanks and the clock keeps its last time.
    // Either way the clock wears the disconnected color, and a later
    // successful poll restores everything.
    //
    //
    // Except once the page has expired.  A request issued just before
    // expiry can fail just after it -- the 1800 ms XHR timeout outlives a
    // short poll interval -- and painting the disconnected look over
    // Expired / CLICK-ME would hide the one affordance the expired state
    // exists to show.  The corner is left alone; the failure is still
    // counted and logged, and the ageing block below still runs -- though
    // for the request or two that can still be in flight it adds only a
    // couple of seconds to the last known age, so it changes nothing unless
    // the board was already within a couple of seconds of max_age when it
    // expired.
    errorCount += 1;
    console.log('loop data fetch failed; consecutive failures: ' + errorCount);
    if (!pageTimedOut) {
      document.getElementById("live-label").innerHTML =
          code ? "&nbsp;" + code + "&nbsp;" : "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;";
      var activityElement = document.getElementById("activity-string");
      if (hint) {
        activityElement.innerHTML = hint;
      }
      activityElement.classList.add("disconnected");
    }

    // The readings age out through an outage too.  A failed poll never
    // reaches updateReadings, so without this every number would sit at
    // its last value in the ordinary red for as long as the fetch kept
    // failing -- a ten-minute-old temperature presented exactly like a
    // live one.  The clock has a signal for this already, the
    // disconnected color it takes from the first failure; the numbers
    // have none, so they fall back to the same question marks they show
    // when the data itself goes stale, on the same max_age.
    //
    // The age carried forward is the last known age plus the time since
    // that poll.  Both parts are lower bounds -- the outage cannot have
    // made the data younger -- so the readings can only blank later than
    // the truth, never earlier, and a single dropped poll at a two second
    // cadence cannot blank a board whose data is fresh.  performance.now()
    // is monotonic, so an NTP correction on the tablet cannot skew it.
    // A last-known age of NaN needs no arithmetic: that poll had no usable
    // timestamp and already blanked these readings.
    var outageAge = lastGoodAge + (performance.now() - lastSuccessAt) / 1000;
    if (outageAge >= max_age) {
      try {
        // An empty object when no poll has ever succeeded: every reading's
        // hasOwnProperty check fails and they all fall back to question
        // marks, which is the whole point -- there is nothing to vouch for.
        updateReadings(lastResult === null ? {} : lastResult, outageAge);
      } catch (e) {
        // As on the success path, a rendering error must not stop polling.
        console.log(e);
      }
    }
  }

  function updateCurrent() {
    if (pageTimedOut) {
      if (!expiredShown) {
        expiredShown = true;
        document.getElementById("live-label").innerHTML = "Expired";
        var activityElement = document.getElementById("activity-string");
        activityElement.innerHTML = "CLICK-ME";
        // As in clickListener: a board can reach its expiry while already
        // disconnected, and CLICK-ME in the fault blue reads as a failure
        // rather than as a board waiting to be started again.
        activityElement.classList.remove("disconnected");
        // set an onclick event to restart
        activityElement.addEventListener("click", clickListener);
      }
      return;
    }
    var xhttp = new XMLHttpRequest();
    xhttp.timeout = 1800;
    xhttp.onload = function() {
      // A response issued before the page expired can land after it.
      // Painting LIVE and a clock over Expired / CLICK-ME would leave a
      // board that looks alive, has stopped polling, and shows no way to
      // start again.  The mirror of markDisconnected's guard.
      if (pageTimedOut) {
        return;
      }
      // onload also fires for HTTP error statuses (404/500/...); only a
      // 2xx response carries loop data.  A persistent HTTP error is
      // almost always loop_data_file not resolving to where loopdata
      // writes -- the classic being a 404 because the file lives outside
      // HTML_ROOT (say /dev/shm) with nothing on the web server serving
      // it -- so name it instead of looking like a network blip.
      if (this.status < 200 || this.status >= 300) {
        markDisconnected("HTTP " + this.status, "check loop_data_file");
        return;
      }
      var result;
      try {
        // Since loopdata 7.0 the file carries each declaring report's
        // fields under the report's name -- the [StdReport] section name,
        // not the skin's: one skin can be listed under two reports -- so
        // this page takes its own entry and reads nothing else.  The name
        // goes through jsstr like every other string Cheetah hands this
        // script: a report name is any [StdReport] section name, quotes
        // and non-ASCII included.
        var file = JSON.parse(this.responseText);
        // Anything that parses but is not a json object -- an array, a
        // string, a number, null -- is some other server's json, and
        // belongs with the non-json case below rather than with a file of
        // loopdata's that lacks this report.
        if (!isJsonObject(file)) {
          throw new Error('loop_data_file is json, but not a json object');
        }
        result = file[$jsstr($REPORT_NAME)];
      } catch (e) {
        // A 2xx whose body isn't json, or isn't a json object:
        // loop_data_file points at something, but not at loopdata's
        // output.
        markDisconnected("BAD DATA", "check loop_data_file");
        console.log(e);
        return;
      }
      if (!isJsonObject(result)) {
        // json, but with no entry for this report -- or, from some file
        // that is not loopdata's, an entry that is not an object.  Almost
        // always weewxd not restarted since the board was installed: the
        // report engine reads the skin's declaration afresh every cycle,
        // so it built this page, but the loopdata service inside weewxd
        // is still running on the declarations it read at startup, and
        // does not know this report yet.  Or loop_data_file points at a
        // file some other station's loopdata writes.  Either way the file
        // is there and this page's data is not; a label of its own, so
        // the manual can name the cure.
        markDisconnected("NO ENTRY", "restart WeeWX");
        return;
      }
      errorCount = 0;
      try {
        // Check the date
        // "dateTime": 1578965850,
        var dateTime = result["current.dateTime.raw"];
        if (dateTime !== lastDateTime) {
          lastDateTime = dateTime;
          lastChangeAt = performance.now();
        }
        // Age comes from the server's own clock, stamped on this very
        // response, rather than from the browser's.  A wall-mounted
        // tablet's clock can be badly wrong, and this age gates every
        // reading below, so a skewed clock used to blank the whole board.
        // Both operands are absolute times: Date.parse only decodes the
        // header's string form, it does not consult the local clock.
        var age = null;
        var serverNow = Date.parse(this.getResponseHeader("Date"));
        if (!isNaN(serverNow)) {
          // An intermediate cache preserves the origin's Date and adds Age
          // (RFC 9111), so server-now is Date + Age.  Without this a cached
          // hit reports itself as young as it was when it was stored.
          var cacheAge = Number(this.getResponseHeader("Age"));
          if (isFinite(cacheAge) && cacheAge > 0) {
            serverNow += cacheAge * 1000;
          }
          age = Math.round(serverNow / 1000 - dateTime);
        }
        // Backstop.  Elapsed since the data last advanced is always a LOWER
        // bound on the true age (a new record is seen some delay after it
        // was written), so it can only win when the header reads too young
        // -- a response served from cache, whose Date is frozen along with
        // its body.  performance.now() is monotonic, so an NTP correction
        // on the tablet cannot make this jump.
        var elapsed = Math.round((performance.now() - lastChangeAt) / 1000);
        age = (age === null) ? elapsed : Math.max(age, elapsed);
        if (age < 0) {
          age = 0;
        }
        if (isNaN(Number(dateTime))) {
          // No usable timestamp: leave the age unknown so the reading gates
          // below show question marks, as the browser-clock version did.
          // Number() rather than a typeof test, so a timestamp that arrives
          // as a numeric string still yields its real age.
          age = NaN;
        }
        // The label and the readings share max_age: the label stops saying
        // LIVE at the same instant the readings fall back to question
        // marks.  The label's tier was a separate six seconds, which meant
        // a board could read "8s ago" beside a full set of live readings,
        // and -- once max_age became configurable -- a station that raised
        // it would never see LIVE again.
        var liveLabel = document.getElementById("live-label");
        liveLabel.innerHTML = "&nbsp;" + getActivityStr(age) + "&nbsp;";

        // The time of the last update, on the STATION's clock.  loopdata
        // renders this field through this report's own WeeWX formatter,
        // so it carries the station's timezone, locale and time format.
        // The browser's own formatting showed the TABLET's instead, and a
        // wall display can sit in another timezone -- or simply have its
        // clock set wrong, which is what sent the staleness math onto the
        // server's clock in 3.2.
        // The clock ages out too, but on clock_max_age, not max_age.
        // Stale data a web server is still handing out looks exactly like
        // live data at a glance, and a plausible time in the ordinary red
        // is the most convincing thing on such a board; question marks in
        // the disconnected blue -- the same color a failing fetch wears
        // -- say plainly that this is no longer a clock.  But that is a
        // later moment than a stale reading: a temperature fifteen
        // seconds old has stopped being true, while a clock fifteen
        // seconds slow is still the best clock in the room, and blueing
        // it there would spend the warning on something that does not
        // need warning about.  A missing field is different again and
        // goes blue at once: the skin's declaration does not list it, so
        // there is no time to show, and a time this page cannot vouch for
        // is worse than none.
        var activityElement = document.getElementById("activity-string");
        var clockKey = 'current.dateTime.format("%X")';
        if (age < clock_max_age && result.hasOwnProperty(clockKey)) {
          activityElement.textContent = result[clockKey];
          activityElement.classList.remove("disconnected");
        } else {
          activityElement.textContent = "??:??:??";
          activityElement.classList.add("disconnected");
        }

        lastResult = result;
        lastGoodAge = age;
        lastSuccessAt = performance.now();
        updateReadings(result, age);
      } catch (e) {
        // A rendering error must not stop the polling.
        console.log(e);
      }
    }
    // Wrapped so the handlers' event argument cannot reach
    // markDisconnected's code parameter.
    xhttp.onerror = function() { markDisconnected(); };
    xhttp.ontimeout = function() { markDisconnected(); };
    try {
      // A unique URL per poll.  loop-data.txt ships without cache headers,
      // so browsers fall back on heuristic freshness -- and that window
      // widens as the file goes stale, which is exactly when a cached copy
      // would report itself as live.
## Escaped like page_update_pwd above, and for the same reason: this value
## is a URL the user types, and a quote, a backslash or a </script> in it
## would end the literal -- or the script element -- and abort the whole
## updater rather than producing a bad fetch.
      var url = $jsstr($Extras.get('loop_data_file', 'loop-data.txt'));
      url += (url.indexOf('?') === -1 ? '?' : '&') + '_=' + (cacheBuster++);
      xhttp.open("GET", url, true);
      // The unique URL misses a cache that keys on path alone, so ask for
      // revalidation too -- but only same-origin.  Cache-Control is not a
      // CORS-safelisted request header, so sending it cross-origin makes
      // every poll a preflighted request, and a plain file server that
      // answers OPTIONS with 405 would leave the board permanently
      // disconnected on a configuration that worked before.
      if (sameOrigin(url)) {
        xhttp.setRequestHeader("Cache-Control", "no-cache");
      }
      xhttp.send();
    } catch (e) {
      // open() throws synchronously on a malformed loop_data_file -- a bare
      // "http://", say -- so this is a configuration error that repeats on
      // every poll, not a transient.  It has to reach markDisconnected like
      // any other failure: it is the one path that never gets an onerror,
      // and without this the label would never blank, the clock would never
      // go blue and the readings would never age out, leaving the board
      // showing its report-cycle numbers in the ordinary red forever.
      console.log(e);
      markDisconnected("BAD URL", "check loop_data_file");
    }
  }

  // Set page expiration timer and start polling.
  setPageExpirationTimer();
  // Floored at one second: numExtra accepts any positive number, and a
  // refresh_rate of 0.01 would arm a 10 ms interval with no in-flight
  // guard, piling up overlapping requests against the server.  The floor
  // caps the overlap rather than removing it: the XHR timeout is 1800 ms,
  // so at a one second rate a slow server can still have two in flight.
  setInterval(updateCurrent, clampDelay(Math.max(refresh_rate, 1) * 1000));
  addLoadEvent(updateCurrent);
