## Copyright (C)2020-2026 by John A Kline (john@johnkline.com)
## Distributed under the terms of the GNU Public License (GPLv3)
## See LICENSE for your rights.
##
## Shared scaffolding for the realtime updater(s).  Must be #included inside
## a <script> element.  The including updater must define
## updateReadings(result, age), which is called on every successful poll of
## the loop data file.

#errorCatcher Echo
  #if $Extras.has_key('page_update_pwd')
    var page_update_pwd = '$Extras.page_update_pwd';
  #else
    var page_update_pwd = 'foo';
  #end if
  #if $Extras.has_key('refresh_rate')
    var refresh_rate = $Extras.refresh_rate;
  #else
    var refresh_rate = 2;
  #end if
  #if $Extras.has_key('expiration_time')
    var expiration_time = $Extras.expiration_time;
  #else
    var expiration_time = 4;
  #end if

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
    if (age < 10 && result.hasOwnProperty("current.windSpeed.formatted")) {
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
    if (age < 10 && result.hasOwnProperty("current.UV.formatted")) {
      uv = padLeft(result["current.UV.formatted"], 4);
    } else {
      uv = "&nbsp;?.?";
    }
    setReading("current.UV.formatted", uv);
  }

  function updateBarometer(result, age) {
    var barometer_value;
    if (age < 10 && result.hasOwnProperty("current.barometer.formatted")) {
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
    if (age < 10 && result.hasOwnProperty("day.rain.sum.formatted")) {
      setReading("day.rain.sum.formatted", result["day.rain.sum.formatted"]);
    } else {
      setReading("day.rain.sum.formatted", '?.??');
    }

    if (age < 10 && result.hasOwnProperty("24h.rain.sum.formatted")) {
      setReading("24h.rain.sum.formatted", result["24h.rain.sum.formatted"]);
    } else {
      setReading("24h.rain.sum.formatted", '?.??');
    }
  }

  // The live label wears an age-tier color (classes in weatherboard.css),
  // liveseasons' tiers: green while the loop record is under a minute
  // old, neutral to five minutes, red beyond -- with white standing in
  // for liveseasons' neutral black on this board's black background.
  // 'failed' is the disconnected blue for the named fetch failures.
  function setLiveLabelClass(cls) {
    var classes = document.getElementById("live-label").classList;
    classes.remove("live", "behind", "stale", "failed");
    if (cls) {
      classes.add(cls);
    }
  }

  function getActivityClass(age) {
    if (age < 60) {
      return "live";
    }
    if (age < 300) {
      return "behind";
    }
    return "stale";
  }

  // Same progressive age formatting as liveseasons' getActivityStr.
  function getActivityStr(age) {
    if (isNaN(age)) {
      // The record carried no usable timestamp, so its age is unknown.
      // Every comparison below is false for NaN, which would fall through
      // to "LIVE" and claim the board is current while its readings show
      // question marks.  Say the same thing the readings say.
      return "??";
    }
    var actStr = "LIVE";
    if (age >= (3600 * 24)) {
      actStr = (age / (3600.0 * 24)).toFixed(1) + "d ago";
    } else if (age >= 3600) {
      actStr = (age / 3600.0).toFixed(1) + "h ago";
    } else if (age >= 60) {
      actStr = (age / 60.0).toFixed(1) + "m ago";
    } else if (age > 6) {
      actStr = age + "s ago";
    }
    return actStr;
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
        var lastUpdate = new Date(dateTime * 1000);
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
        document.getElementById("live-label").innerHTML =
            "&nbsp;" + getActivityStr(age) + "&nbsp;";
        setLiveLabelClass(getActivityClass(age));

        // Display the time of the last update.
        var activityElement = document.getElementById("activity-string");
        activityElement.innerHTML = lastUpdate.toLocaleTimeString([], {hour: '2-digit', minute: '2-digit', second: '2-digit'});
        activityElement.classList.remove("disconnected");

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
      console.log(e);
    }
  }

  // Set page expiration timer and start polling.
  setPageExpirationTimer();
  setInterval(updateCurrent, refresh_rate * 1000);
  addLoadEvent(updateCurrent);
