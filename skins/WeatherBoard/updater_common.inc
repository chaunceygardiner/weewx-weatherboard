## Copyright (C)2020-2026 by John A Kline (john@johnkline.com)
## Distributed under the terms of the GNU Public License (GPLv3)
## See LICENSE for your rights.
##
## Shared scaffolding for the realtime updater(s).  Must be #included inside
## a <script> element.  The including updater must define
## updateReadings(result, age), which is called on every successful poll of
## the loop data file.

#errorCatcher Echo
## The keep-alive password is whatever the user typed, and both the README
## and the manual tell everyone to change it from the shipped placeholder.
## Interpolated bare into a quoted javascript string, an apostrophe -- a
## password like don't-sleep -- closes the literal early and throws at the
## top of this script, which aborts the WHOLE updater: nothing polls, no
## live label, no clock.  json.dumps writes a correctly escaped literal, so
## the value reaches javascript exactly as typed and still matches what the
## user puts on the URL.  (Escaped, not stripped: changing the password
## silently would be its own bug.)
##
## json.dumps alone is not enough: it leaves < untouched, so a password
## containing </script> ends the script ELEMENT even though the javascript
## literal is well formed -- the HTML parser gets there first, and the
## board dies exactly as it would on an unescaped apostrophe.  Escaping <
## as \u003c keeps the value identical to javascript while leaving no
## closing tag for the parser to find.
#from json import dumps
#set $_pwd = $dumps($str($Extras.get('page_update_pwd', 'foo'))).replace('<', '\\u003c')
  var page_update_pwd = $_pwd;
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
  // had if the setting were absent.
  // A blank setting is treated as absent rather than as a number, because
  // Number("") is 0, not NaN -- so an empty max_age would mean every
  // reading is always stale, and an empty refresh_rate would poll as fast
  // as the browser could schedule it.  Zero and negatives are rejected for
  // the same reason: every one of these knobs is a count of seconds or
  // hours, and none of them has a meaningful value at or below zero.
  // The ceiling is the timer's, not ours.  setTimeout and setInterval keep
  // their delay in a signed 32-bit int, so a value whose milliseconds pass
  // 2147483647 wraps: expiration_time = 8760, a year, comes out around
  // twenty-five minutes, and values just over the edge fire at once.  A
  // station reaching for "never expire" would get the opposite of what it
  // asked for, silently.  Anything past the ceiling falls back to the
  // default, like any other value this cannot honour.  MAX_DELAY_MS is
  // divided by the caller's own multiplier, so each knob is bounded in its
  // own units -- hours for expiration_time, seconds for the rest.
  function numExtra(raw, dflt, multiplier) {
    if (typeof raw !== "string" || raw.trim() === "") {
      return dflt;
    }
    var n = Number(raw);
    if (!isFinite(n) || n <= 0) {
      return dflt;
    }
    if (multiplier && n * multiplier > 2147483647) {
      return dflt;
    }
    return n;
  }
## Strip any quote or backslash so the javascript string literal below stays
## well formed whatever the setting contains.
#set $_refresh_rate = str($Extras.get('refresh_rate', 2)).replace('\\', '').replace('"', '')
#set $_expiration_time = str($Extras.get('expiration_time', 4)).replace('\\', '').replace('"', '')
  var refresh_rate = numExtra("$_refresh_rate", 2, 1000);
  var expiration_time = numExtra("$_expiration_time", 4, 1000 * 60 * 60);
  // How old a loop record may be before the readings it feeds show
  // question marks instead.  The default suits a station emitting loop
  // packets every couple of seconds; raise it for a slower one.
#set $_max_age = str($Extras.get('max_age', 10)).replace('\\', '').replace('"', '')
  var max_age = numExtra("$_max_age", 10);
  // The clock gets its own, longer threshold, because it is answering a
  // different question than the readings are.  A temperature a minute old
  // is a stale reading; a clock a minute slow is still a clock.
#set $_clock_max_age = str($Extras.get('clock_max_age', 120)).replace('\\', '').replace('"', '')
  var clock_max_age = numExtra("$_clock_max_age", 120);
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
      } else {
          return decodeURIComponent(results[1]);
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
      setTimeout(expirePage, 1000 * 60 * 60 * expiration_time);
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

  // Server-now in milliseconds, from a response's own Date header, or NaN
  // when the header cannot be read.  An intermediate cache preserves the
  // origin's Date and adds Age (RFC 9111), so server-now is Date + Age;
  // without that a cached hit reports itself as young as it was when it
  // was stored.  Date is not a CORS-safelisted response header, so this
  // returns NaN for a cross-origin fetch unless the server sends
  // Access-Control-Expose-Headers: Date -- callers fall back on their own
  // elapsed backstop.  getHeader is passed in because an XHR spells this
  // getResponseHeader(name) and a fetch Response spells it headers.get(name).
  function serverNowFromHeaders(getHeader) {
    var serverNow = Date.parse(getHeader("Date"));
    if (isNaN(serverNow)) {
      return NaN;
    }
    var cacheAge = Number(getHeader("Age"));
    if (isFinite(cacheAge) && cacheAge > 0) {
      serverNow += cacheAge * 1000;
    }
    return serverNow;
  }

  function decode_rgb(i) {
    var red   = i >> 16;
    var green = (i & 0xFF00) >> 8;
    var blue  = i & 0xFF;
    return 'rgb(' + red + ',' + green + ',' + blue + ')';
  }

  // Pad a reading on the left to `width` characters using no-break spaces
  // so the monospace columns don't shift as values change length.
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
    // rainRate is updated separately in realtime_updater.inc/realtime_updater2.inc
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
  }

  // The live label wears an age-tier color (classes in weatherboard.css),
  // liveseasons' tiers, but measured against max_age rather than the fixed
  // minute liveseasons uses: green for as long as the label says LIVE,
  // white to five minutes, red beyond -- with white standing in for
  // liveseasons' neutral black on this board's black background.  See
  // getActivityClass for the cuts themselves.
  // 'failed' is the disconnected blue for the named fetch failures.
  function setLiveLabelClass(cls) {
    var classes = document.getElementById("live-label").classList;
    classes.remove("live", "behind", "stale", "failed");
    if (cls) {
      classes.add(cls);
    }
  }

  // The colors follow the same cut the label's words do: green for as long
  // as it says LIVE, then white, then red.  The tiers were a hardcoded
  // minute and five minutes, which agreed with the label only while its
  // LIVE cut was a hardcoded six seconds.  With max_age configurable, a
  // board set to 120 would have read LIVE in the behind-white, and one set
  // past 300 would have read LIVE in the stale-red -- the label and its
  // color contradicting each other, which is the thing this coloring
  // exists to avoid.  The middle tier is floored at max_age for the same
  // reason: it must never begin before the first one has ended.
  function getActivityClass(age) {
    if (age < max_age) {
      return "live";
    }
    if (age < Math.max(300, max_age)) {
      return "behind";
    }
    return "stale";
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
    errorCount += 1;
    console.log('loop data fetch failed; consecutive failures: ' + errorCount);
    document.getElementById("live-label").innerHTML =
        code ? "&nbsp;" + code + "&nbsp;" : "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;";
    setLiveLabelClass(code ? "failed" : "");
    var activityElement = document.getElementById("activity-string");
    if (hint) {
      activityElement.innerHTML = hint;
    }
    activityElement.classList.add("disconnected");

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
    //
    // One coupling worth knowing: on the indoor board updateReadings is
    // also what advances the sidecar counter, so through the first max_age
    // seconds of an outage the sidecar files are not fetched, and then
    // resume.  That is harmless -- each has its own staleness limit and
    // ages out on its own -- but it does mean their cadence rides on the
    // loop-data fetch rather than being independent of it.
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
        setLiveLabelClass("");
        var activityElement = document.getElementById("activity-string");
        activityElement.innerHTML = "CLICK-ME";
        // set an onclick event to restart
        activityElement.addEventListener("click", clickListener);
      }
      return;
    }
    var xhttp = new XMLHttpRequest();
    xhttp.timeout = 1800;
    xhttp.onload = function() {
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
        result = JSON.parse(this.responseText);
      } catch (e) {
        // A 2xx whose body isn't json: loop_data_file points at
        // something, but not at loopdata's output.
        markDisconnected("BAD DATA", "check loop_data_file");
        console.log(e);
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
        // Note that the two operands can come from two different machines:
        // the Date header is stamped by whatever web server answers, while
        // dateTime was written by the weewx station.  Skew between them is
        // charged against the 10-second gate below, so both hosts are
        // assumed to keep NTP-grade time.  (Measured on this deployment:
        // the station within tens of microseconds, the web server within
        // tens of milliseconds -- three orders of magnitude inside the
        // budget.)
        var age = null;
        var xhr = this;
        var serverNow = serverNowFromHeaders(function(name) {
          return xhr.getResponseHeader(name);
        });
        if (!isNaN(serverNow)) {
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
        if (dateTime == null || dateTime === '' || isNaN(Number(dateTime))) {
          // No usable timestamp: leave the age unknown so the reading gates
          // below show question marks, as the browser-clock version did.
          // Number() rather than a typeof test, so a timestamp that arrives
          // as a numeric string still yields its real age -- but Number()
          // maps null and '' to 0, which would read as epoch 0 and put an
          // age of half a century on the label, so those are tested first.
          // == null is deliberate: it catches undefined too.
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
        setLiveLabelClass(getActivityClass(age));

        // The time of the last update, on the STATION's clock.  loopdata
        // renders this field through the target report's WeeWX formatter,
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
        // goes blue at once: the weewx.conf fields line does not list it,
        // so there is no time to show, and a time this page cannot vouch
        // for is worse than none.
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

        // The live logo (logo.inc) repaints from the same poll.  Guarded
        // by typeof so this shared file also works on a branch that has
        // no logo.inc/paw_logo.js.
        if (typeof pawLogoFromLoop === 'function') {
          pawLogoFromLoop(result);
        }
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
      var url = "$Extras.loop_data_file";
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
  setInterval(updateCurrent, refresh_rate * 1000);
  addLoadEvent(updateCurrent);
