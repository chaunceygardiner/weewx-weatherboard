## Copyright (C)2020-2026 by John A Kline (john@johnkline.com)
## Distributed under the terms of the GNU Public License (GPLv3)
## See LICENSE for your rights.
##
## board.inc -- everything the two boards share: the settings the page
## runs on, the loop-data poll, the age of the data, the failures, the
## page's expiry and the status line.  A page includes it at the top of its
## body: the #set global names below (wb_uv, wb_rad, wb_aqi, wb_feels) are
## what its markup tests to leave out a panel, and the page then defines
## the painter this calls, boardPaint(result, fresh, status) -- the one
## thing the two boards do differently.  Nothing runs before
## DOMContentLoaded, by which time the painter exists.
##
## THE STATUS LINE.  Neither board has a LIVE label; the clock is the
## status line, and the painter is handed what it should say:
##   live     the station's time, while the data is max_age seconds old or
##            younger
##   aging    the data's age ("47 S AGO") for its first minute past max_age
##   old      the age after that
##   error    what went wrong fetching: HTTP 404, BAD DATA, NO ENTRY,
##            BAD URL, NO CONNECT (a timeout or a network error, which
##            carry no code of their own)
##   expired  the page stopped polling after expiration_time hours; a tap
##            anywhere starts it again
##   waiting  no data has arrived yet
## Once the data is max_age seconds old, by ANY of those routes, every
## reading is painted as missing: fresh is false.
#errorCatcher Echo
#include "jsstr.inc"
#from weeutil.weeutil import to_bool
##
## An optional reading: auto shows it when the station's current record
## carries it at report time; anything to_bool reads forces it.  A value
## to_bool cannot read counts as auto rather than stopping the report.
#def wb_show($raw, $present)
#try
#if str($raw).strip().lower() == 'auto'
#return bool($present)
#end if
#return bool($to_bool($raw))
#except
#return bool($present)
#end try
#end def
#set global $wb_uv = $wb_show($Extras.get('show_uv', 'auto'), $current.UV.has_data)
#set global $wb_rad = $wb_show($Extras.get('show_radiation', 'auto'), $current.radiation.has_data)
## show_purple, from earlier releases, answers for show_aqi while show_aqi
## is auto.  Auto needs both the sensor's pm2_5 and the index the board
## actually shows, which an extension computes from it: pm2_5 alone would
## put up a panel that never had a number to show.
#set global $wb_aqi_raw = $Extras.get('show_aqi', 'auto')
#if str($wb_aqi_raw).strip().lower() == 'auto' and 'show_purple' in $Extras
#set global $wb_aqi_raw = $Extras.show_purple
#end if
#set global $wb_aqi = $wb_show($wb_aqi_raw, $current.pm2_5.has_data and $current.pm2_5_aqi.has_data)
#set global $wb_feels = bool($current.appTemp.has_data)
## The clock: 12 or 24 hour from clock_format, else from the language.
#set global $wb_clock = $gettext("%-I:%M:%S %p")
#set global $wb_cf = str($Extras.get('clock_format', '')).strip()
#if $wb_cf == '12'
#set global $wb_clock = "%-I:%M:%S %p"
#elif $wb_cf == '24'
#set global $wb_clock = "%H:%M:%S"
#end if
#set $wb_js = {True: 'true', False: 'false'}
<script>
  // Settings, as the report was generated.
  var WB = {
    report: $jsstr($REPORT_NAME),
    url: $jsstr($Extras.get('loop_data_file', '') or '../loopdata/loop-data.txt'),
    pwd: $jsstr($Extras.get('page_update_pwd', '') or 'foobar'),
    refreshRate: $jsstr($Extras.get('refresh_rate', '')),
    expirationTime: $jsstr($Extras.get('expiration_time', '')),
    maxAge: $jsstr($Extras.get('max_age', '')),
    clockFormat: $jsstr($wb_clock),
    show: { uv: $wb_js[$wb_uv], radiation: $wb_js[$wb_rad], aqi: $wb_js[$wb_aqi], feels: $wb_js[$wb_feels] },
    // The status words, in the report's language.  {n} is the number.
    text: {
      agoS: $jsstr($gettext("{n} S AGO")),
      agoM: $jsstr($gettext("{n} M AGO")),
      agoH: $jsstr($gettext("{n} H AGO")),
      agoD: $jsstr($gettext("{n} D AGO")),
      noConnect: $jsstr($gettext("NO CONNECT")),
      expired: $jsstr($gettext("EXPIRED TAP")),
      waiting: $jsstr($gettext("WAITING"))
    }
  };

  // A numeric setting, or its default when the setting is empty, not a
  // number, or not above zero -- a typo in weewx.conf must not stop the
  // board.
  function numExtra(raw, dflt) {
    if (typeof raw !== "string" || raw.trim() === "") {
      return dflt;
    }
    var n = Number(raw);
    return (isFinite(n) && n > 0) ? n : dflt;
  }
  // setTimeout and setInterval treat a delay past 2^31-1 ms as zero, which
  // turns a huge expiration_time into an immediate expiry.
  function clampDelay(ms) {
    return Math.min(ms, 2147483647);
  }
  var refresh_rate = numExtra(WB.refreshRate, 2);
  var expiration_time = numExtra(WB.expirationTime, 4);
  var max_age = numExtra(WB.maxAge, 10);

  var pageTimedOut = false;
  var errorCode = null;       // the failure the last poll ended in, if it failed
  var lastResult = null;      // the last good entry from loop-data.txt
  var lastGoodAge = 0;        // its age when it arrived, by the server's clock
  var lastSuccessAt = performance.now();
  var lastDateTime;           // its current.dateTime.raw, to notice a file that stopped changing
  var lastChangeAt = performance.now();
  var cacheBuster = Date.now();
  var expiryTimer = null;
  var started = false;        // startUpdating has run: the page and its painter exist

  function getUrlParam(paramName) {
    var name = paramName.replace(/(\[|\])/g, '\\$1');
    var results = new RegExp('[\\?&]' + name + '=([^&#]*)').exec(window.location.href);
    if (results === null) {
      return '';
    }
    try {
      return decodeURIComponent(results[1]);
    } catch (e) {
      return results[1];
    }
  }
  // Cache-Control is not a CORS-safelisted request header: sent across
  // origins it draws a preflight a plain file server refuses.
  function sameOrigin(url) {
    try {
      return new URL(url, window.location.href).origin === window.location.origin;
    } catch (e) {
      return false;
    }
  }
  function isJsonObject(value) {
    return value !== null && typeof value === 'object' && !Array.isArray(value);
  }
  // Whether the entry carries a field with something in it.
  function hasValue(r, key) {
    return r.hasOwnProperty(key) && r[key] !== null && r[key] !== '';
  }
  // s, padded with spaces on the left to w characters.
  function padLeft(s, w) {
    s = String(s);
    while (s.length < w) {
      s = ' ' + s;
    }
    return s;
  }
  // The ten-minute and today's gusts, or on a station whose driver
  // reports no gusts, the highest wind speed over the same period -- which
  // is what a gust there would have been.
  function gustField(r, span) {
    var gust = span + '.windGust.max.formatted', speed = span + '.windSpeed.max.formatted';
    return hasValue(r, gust) ? gust : speed;
  }
  // A reading, as the painters take it: the field's text when the data is
  // fresh and the field holds a NUMBER, else null, which each board paints
  // as missing.  WeeWX writes N/A for a value it does not have; that is
  // missing, and must never reach a board as though it were a reading.
  function numericReading(r, key, fresh) {
    if (!fresh || !r.hasOwnProperty(key) || r[key] === null) {
      return null;
    }
    var text = String(r[key]).trim();
    return (text !== '' && isFinite(Number(text))) ? text : null;
  }
  // The barometer's trend code as a whole number from -4 to 4, or null
  // when there is none that is a number.
  function trendCode(r) {
    var code = r['trend.barometer.code'];
    if (code === null || code === undefined || code === '' || !isFinite(Number(code))) {
      return null;
    }
    return Math.max(-4, Math.min(4, Math.round(Number(code))));
  }
  // The trend drawn: one arrow whose angle is its pace -- flat for steady,
  // 22.5 degrees more per step, straight up or down at +/-4.  Both boards
  // draw it, the readout board beside its figure and the split-flap board
  // on a flap of its own; cls is the class each styles it by.
  function trendSvg(code, cls) {
    return '<svg class="' + cls + '" viewBox="-11 -11 22 22" aria-hidden="true">'
        + '<g transform="rotate(' + (-code * 22.5) + ')" fill="none" stroke="currentColor"'
        + ' stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round">'
        + '<path d="M-8 0H7M1.5-5.5L7 0L1.5 5.5"/></g></svg>';
  }
  function decodeRgb(i) {
    return 'rgb(' + (i >> 16) + ',' + ((i & 0xFF00) >> 8) + ',' + (i & 0xFF) + ')';
  }

  // How old the data on the board is, in seconds: its age when it arrived
  // plus the time since.  NaN when the entry carries no usable timestamp.
  function dataAge() {
    if (lastResult === null) {
      return Infinity;
    }
    return lastGoodAge + (performance.now() - lastSuccessAt) / 1000;
  }
  // "47 S AGO": one unit, floored, in the report's language.
  function ageWords(age) {
    var n, t;
    if (age >= 86400) { n = Math.floor(age / 86400); t = WB.text.agoD; }
    else if (age >= 3600) { n = Math.floor(age / 3600); t = WB.text.agoH; }
    else if (age >= 60) { n = Math.floor(age / 60); t = WB.text.agoM; }
    else { n = Math.floor(age); t = WB.text.agoS; }
    return t.replace('{n}', n);
  }
  // The station's time, "16:07:17" from loopdata, laid out as the clock
  // format asks.  The format's own letters are the only ones that reach
  // the board: %-I %I %H %M %S and %p (AM or PM, always in those letters).
  function clockText(hms) {
    var m = /^(\d{1,2}):(\d{2}):(\d{2})$/.exec(hms || '');
    if (!m) {
      return null;
    }
    var h = Number(m[1]), h12 = (h % 12) || 12;
    return WB.clockFormat.replace(/%(-?)([IHMSp])/g, function (all, dash, k) {
      if (k === 'I') { return dash ? String(h12) : ('0' + h12).slice(-2); }
      if (k === 'H') { return ('0' + h).slice(-2); }
      if (k === 'M') { return m[2]; }
      if (k === 'S') { return m[3]; }
      return h < 12 ? 'AM' : 'PM';
    });
  }
  function boardStatus() {
    var age = dataAge();
    if (pageTimedOut) {
      return { kind: 'expired', text: WB.text.expired };
    }
    if (errorCode !== null) {
      return { kind: 'error', text: errorCode };
    }
    if (lastResult === null) {
      return { kind: 'waiting', text: WB.text.waiting };
    }
    if (isNaN(age)) {
      return { kind: 'error', text: 'NO CLOCK' };
    }
    if (age >= max_age) {
      return { kind: age < 60 ? 'aging' : 'old', text: ageWords(age) };
    }
    return { kind: 'live', text: clockText(lastResult['current.dateTime.format("%H:%M:%S")']) };
  }
  // Nothing is painted before startUpdating: a font that is already
  // cached can call for a paint while the page is still being read, before
  // its cells or its painter exist.  A painter that throws must not stop
  // the polling, so the error is caught -- and thrown again on its own,
  // so it still reaches the browser as an error rather than a line in the
  // console nobody reads.
  function repaint() {
    if (!started) {
      return;
    }
    var age = dataAge();
    var fresh = lastResult !== null && age < max_age;
    try {
      boardPaint(lastResult === null ? {} : lastResult, fresh, boardStatus());
    } catch (e) {
      setTimeout(function () { throw e; }, 0);
    }
  }

  // THE WINDOW CHANGING SIZE.  Dragging a window's edge fires a resize
  // every frame, and a refit lays the page out many times over.  So a
  // board refits at the first resize, and again once the window has held
  // its size for a tenth of a second -- not at every step between.  A page
  // hands its refit to onResized.  resizeFits counts the refits, for the
  // tests.
  var resizeFns = [];
  var resizeTimer = null;
  var resizeAgain = false;
  var resizeFits = 0;
  function onResized(fn) {
    resizeFns.push(fn);
  }
  function runResized() {
    resizeFits++;
    for (var i = 0; i < resizeFns.length; i++) {
      resizeFns[i]();
    }
  }
  window.addEventListener('resize', function () {
    if (resizeTimer === null) {
      runResized();
    } else {
      clearTimeout(resizeTimer);
      resizeAgain = true;
    }
    resizeTimer = setTimeout(function () {
      resizeTimer = null;
      if (resizeAgain) {
        resizeAgain = false;
        runResized();
      }
    }, 100);
  });

  // THE PAGE'S EXPIRY.  Without the keep-alive password on its URL the
  // page stops fetching after expiration_time hours and says so; a tap
  // anywhere starts it again.  It keeps repainting, so the readings still
  // turn to dashes as the data it last had grows old.
  function expirePage() {
    pageTimedOut = true;
    repaint();
  }
  function setPageExpirationTimer() {
    var pwd = getUrlParam('page_update_pwd');
    if (pwd === '') {
      pwd = getUrlParam('pageUpdate');
    }
    clearTimeout(expiryTimer);
    if (pwd !== WB.pwd) {
      expiryTimer = setTimeout(expirePage, clampDelay(1000 * 60 * 60 * expiration_time));
    }
  }
  document.addEventListener('click', function () {
    if (!pageTimedOut) {
      return;
    }
    pageTimedOut = false;
    errorCode = null;
    setPageExpirationTimer();
    updateCurrent();
  });

  function markFailed(code) {
    errorCode = code || WB.text.noConnect;
    console.log('loop data fetch failed: ' + errorCode);
    repaint();
  }

  function updateCurrent() {
    if (pageTimedOut) {
      repaint();
      return;
    }
    var xhttp = new XMLHttpRequest();
    // Under the default two-second poll, so a hung request fails before
    // the next one starts rather than piling up behind it.  At a faster
    // refresh_rate two may overlap; either answer is current enough.
    xhttp.timeout = 1800;
    xhttp.onload = function() {
      if (pageTimedOut) {
        return;
      }
      if (this.status < 200 || this.status >= 300) {
        markFailed("HTTP " + this.status);
        return;
      }
      var result;
      try {
        var file = JSON.parse(this.responseText);
        if (!isJsonObject(file)) {
          throw new Error('loop_data_file is json, but not a json object');
        }
        result = file[WB.report];
      } catch (e) {
        console.log(e);
        markFailed("BAD DATA");
        return;
      }
      // A file with no entry for this report: loopdata has not read this
      // report's field list, which it does only when weewxd starts.
      if (!isJsonObject(result)) {
        markFailed("NO ENTRY");
        return;
      }
      errorCode = null;
      var dateTime = result["current.dateTime.raw"];
      if (dateTime !== lastDateTime) {
        lastDateTime = dateTime;
        lastChangeAt = performance.now();
      }
      // The age by the SERVER's clock (its Date header, plus the Age an
      // intermediate cache adds), so a tablet whose own clock is wrong
      // still judges the data right.  How long the file's timestamp has
      // sat unchanged backs that up: it can only understate the age, and
      // it is all there is when no Date header can be read.
      var age = null;
      var serverNow = Date.parse(this.getResponseHeader("Date"));
      if (!isNaN(serverNow)) {
        var cacheAge = Number(this.getResponseHeader("Age"));
        if (isFinite(cacheAge) && cacheAge > 0) {
          serverNow += cacheAge * 1000;
        }
        age = serverNow / 1000 - dateTime;
      }
      var elapsed = (performance.now() - lastChangeAt) / 1000;
      age = (age === null || isNaN(age)) ? elapsed : Math.max(age, elapsed);
      if (age < 0) {
        age = 0;
      }
      if (dateTime === null || dateTime === '' || isNaN(Number(dateTime))) {
        age = NaN;
      }
      lastResult = result;
      lastGoodAge = age;
      lastSuccessAt = performance.now();
      repaint();
    };
    xhttp.onerror = function() { if (!pageTimedOut) { markFailed(); } };
    xhttp.ontimeout = function() { if (!pageTimedOut) { markFailed(); } };
    try {
      var url = WB.url;
      url += (url.indexOf('?') === -1 ? '?' : '&') + '_=' + (cacheBuster++);
      xhttp.open("GET", url, true);
      if (sameOrigin(url)) {
        xhttp.setRequestHeader("Cache-Control", "no-cache");
      }
      xhttp.send();
    } catch (e) {
      console.log(e);
      markFailed("BAD URL");
    }
  }

  // Armed at DOMContentLoaded, not window load: the load event waits for
  // every subresource, and an analytics script that never finishes
  // loading on a tablet with no route out would hold the board blank.
  function startUpdating() {
    started = true;
    setPageExpirationTimer();
    repaint();
    setInterval(updateCurrent, clampDelay(Math.max(refresh_rate, 1) * 1000));
    updateCurrent();
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', startUpdating);
  } else {
    startUpdating();
  }
</script>
