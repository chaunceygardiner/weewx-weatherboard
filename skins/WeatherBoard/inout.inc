## Copyright (C)2020-2026 by John A Kline (john@johnkline.com)
## Distributed under the terms of the GNU Public License (GPLv3)
## See LICENSE for your rights.
##
## inout.inc -- inout.html's indoor readings and its painter
## (paloaltoweather branch only).
##
## THE SIDECAR FILES.  Four readings come from small JSON files written
## beside loop-data.txt by the site's own plumbing, not from loopdata:
##   in_temp_file      {"ts": 1790221564, "inTemp": 73.8}
##   in_co2_file       {"ts": ..., "inCO2": 450.0, "inColor": "rgb(0,200,0)"}
##   in_aqi_file       {"ts": ..., "inAQI": 29, "inColor": "rgb(0,228,0)"}
##   solar_array_file  {"total_watts": 2583, "total_timestamp": 1790221501.865, ...}
## The indoor temperature is in the station's own temperature unit.  Each
## file is polled every eighth refresh (about 16 seconds): they are written
## far more slowly than the loop data -- the AirGradient trio on a ~30 s
## cron, the solar file every 15 s carrying Enphase data already the
## better part of a minute old -- so each has its own max age.  URL
## parameters inTempFile, inCO2File, inAQIFile and solarArrayFile override
## the paths.
##
## A reading's age keeps counting between polls, so it goes to dashes on
## its own once it passes its max age, whether the file went stale, the
## fetch failed, or the page expired and stopped polling.  A failed fetch
## -- no answer, an HTTP error, a file that is not usable -- changes
## nothing by itself: the last good reading stays until it is too old, as
## the loop data's readings do when a poll fails, so one lost request does
## not blank the indoor readings for a whole polling cycle.  The CO2 and
## indoor AQI readings wear the color their file gives them, and white
## with no data.
#errorCatcher Echo
<script>
  // Settings, as the report was generated.
  function sidecar(param, file, maxAge, dfltMaxAge, key, tsKey, colored) {
    var f = getUrlParam(param);
    return { url: f !== '' ? f : file, maxAge: numExtra(maxAge, dfltMaxAge), key: key,
             tsKey: tsKey, colored: colored, value: null, color: '', age: 0, at: 0,
             lastTs: undefined, lastChangeAt: 0 };
  }
  var SIDECARS = {
    inTemp: sidecar('inTempFile', $jsstr($Extras.get('in_temp_file', '') or 'inTemp.txt'),
                    $jsstr($Extras.get('in_temp_max_age', '')), 120, 'inTemp', 'ts', false),
    inCO2: sidecar('inCO2File', $jsstr($Extras.get('in_co2_file', '') or 'inCO2.txt'),
                   $jsstr($Extras.get('in_co2_max_age', '')), 120, 'inCO2', 'ts', true),
    inAQI: sidecar('inAQIFile', $jsstr($Extras.get('in_aqi_file', '') or 'inAQI.txt'),
                   $jsstr($Extras.get('in_aqi_max_age', '')), 120, 'inAQI', 'ts', true),
    solar: sidecar('solarArrayFile', $jsstr($Extras.get('solar_array_file', '') or 'solar-array.json'),
                   $jsstr($Extras.get('solar_array_max_age', '')), 150,
                   'total_watts', 'total_timestamp', false)
  };

  // Leaves the last good reading to age out; see the header.
  function sidecarFailed() {
    repaint();
  }
  // One file, fetched the way board.inc fetches loop-data.txt: a unique
  // URL and a same-origin no-cache header against the files' missing
  // cache headers, and a timeout, so a request that hangs gives up rather
  // than holding one of the few connections the browser allows the host.
  function fetchSidecar(s) {
    var xhttp = new XMLHttpRequest();
    xhttp.timeout = 5000;
    xhttp.onload = function() {
      if (this.status < 200 || this.status >= 300) {
        sidecarFailed();
        return;
      }
      var doc;
      try {
        doc = JSON.parse(this.responseText);
      } catch (e) {
        sidecarFailed();
        return;
      }
      // A writer that stops emitting a field leaves nothing new to show:
      // the last good value ages out, never stays up for ever.
      if (!isJsonObject(doc) || doc[s.key] === null || doc[s.key] === undefined
          || !isFinite(Number(doc[s.key])) || (s.colored && typeof doc.inColor !== 'string')) {
        sidecarFailed();
        return;
      }
      var ts = doc[s.tsKey];
      if (ts === null || ts === undefined || ts === '' || !isFinite(Number(ts))) {
        sidecarFailed();
        return;
      }
      if (ts !== s.lastTs) {
        s.lastTs = ts;
        s.lastChangeAt = performance.now();
      }
      // The age by the server's clock, as board.inc judges the loop data,
      // backed up by how long the file's timestamp has sat unchanged.
      var age = null;
      var serverNow = Date.parse(this.getResponseHeader("Date"));
      if (!isNaN(serverNow)) {
        var cacheAge = Number(this.getResponseHeader("Age"));
        if (isFinite(cacheAge) && cacheAge > 0) {
          serverNow += cacheAge * 1000;
        }
        age = serverNow / 1000 - Number(ts);
      }
      var elapsed = (performance.now() - s.lastChangeAt) / 1000;
      age = (age === null || isNaN(age)) ? elapsed : Math.max(age, elapsed);
      s.value = Number(doc[s.key]);
      s.color = s.colored ? doc.inColor : '';
      s.age = Math.max(age, 0);
      s.at = performance.now();
      repaint();
    };
    xhttp.onerror = function() { sidecarFailed(); };
    xhttp.ontimeout = function() { sidecarFailed(); };
    try {
      var url = s.url;
      url += (url.indexOf('?') === -1 ? '?' : '&') + '_=' + (cacheBuster++);
      xhttp.open("GET", url, true);
      if (sameOrigin(url)) {
        xhttp.setRequestHeader("Cache-Control", "no-cache");
      }
      xhttp.send();
    } catch (e) {
      console.log(e);
      sidecarFailed();
    }
  }
  function pollSidecars() {
    if (pageTimedOut) {
      return;
    }
    for (var k in SIDECARS) {
      if (SIDECARS.hasOwnProperty(k)) {
        fetchSidecar(SIDECARS[k]);
      }
    }
  }
  // A reading's value while it is younger than its max age, else null.
  function sidecarValue(s) {
    if (s.value === null) {
      return null;
    }
    return s.age + (performance.now() - s.at) / 1000 < s.maxAge ? s.value : null;
  }

  // The tap that restarts an expired page (board.inc's listener, which
  // runs first) fetches the sidecars at once too, rather than leaving them
  // dashes until the next eighth refresh.
  var inoutLastKind = null;
  document.addEventListener('click', function () {
    if (inoutLastKind === 'expired') {
      pollSidecars();
    }
  });
  function startSidecars() {
    pollSidecars();
    setInterval(pollSidecars, clampDelay(Math.max(refresh_rate, 1) * 8 * 1000));
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', startSidecars);
  } else {
    startSidecars();
  }

  // A sidecar value as the board shows it, or null for none.  Never
  // "-0.0": a few watts of inverter noise at night round to zero, and a
  // minus sign would show for it.
  function sidecarText(v, digits) {
    if (v === null) {
      return null;
    }
    var t = v.toFixed(digits);
    return Number(t) === 0 ? (0).toFixed(digits) : t;
  }
  // A sidecar reading in its file's color.  With no data the color is
  // cleared, and the cell's inout-white class (inout.css) shows through.
  function inoutColored(id, s, digits) {
    var v = sidecarValue(s);
    roSet(id, sidecarText(v, digits), v === null ? null : s.color);
  }

  function boardPaint(r, fresh, status) {
    function val(key) {
      return numericReading(r, key, fresh);
    }
    var v;
    roSet('ro-t', val('current.outTemp.formatted'));
    roSet('ro-td', val('current.dewpoint.formatted'));
    roSet('ro-in', sidecarText(sidecarValue(SIDECARS.inTemp), 1));
    roWind('ro-w', r, val('current.windSpeed.formatted'));
    roSet('ro-g', val(gustField(r, '10m')));
    roSet('ro-gd', val(gustField(r, 'day')));
    roBarometer('ro-b', r, fresh, val('current.barometer.formatted'));
    if (WB.show.uv) { roSet('ro-uv', val('current.UV.formatted')); }
    if (WB.show.radiation) { roSet('ro-rad', val('current.radiation.formatted')); }
    v = sidecarValue(SIDECARS.solar);
    roSet('ro-sol', sidecarText(v === null ? null : v / 1000, 1));
    roSet('ro-rd', val('day.rain.sum.formatted'));
    roSet('ro-r24', val('24h.rain.sum.formatted'));
    roSet('ro-rr', val('current.rainRate.formatted'));
    inoutColored('ro-co2', SIDECARS.inCO2, 0);
    inoutColored('ro-iaq', SIDECARS.inAQI, 0);
    if (WB.show.aqi) { roAqi('ro-aqi', r, val('current.pm2_5_aqi.formatted')); }
    inoutLastKind = status.kind;
    roDate('ro-date', r, fresh);
    roStatus(status);
  }
</script>
