## Copyright (C)2020-2026 by John A Kline (john@johnkline.com)
## Distributed under the terms of the GNU Public License (GPLv3)
## See LICENSE for your rights.
##
## Updater for the indoor board (index2.html.tmpl).  Uses .formatted loop
## data fields (no unit labels) and adds indoor temp/CO2/AQI read from
## separate single-value files.  Scaffolding and the reading updaters shared
## with the outdoor board live in updater_common.inc.

#errorCatcher Echo
<script>
#include "updater_common.inc"

    var default_in_temp_file = $jsstr($Extras.get('in_temp_file', 'inTemp.txt'));
    var default_in_co2_file = $jsstr($Extras.get('in_co2_file', 'inCO2.txt'));
    var default_in_aqi_file = $jsstr($Extras.get('in_aqi_file', 'inAQI.txt'));
    var default_solar_array_file = $jsstr($Extras.get('solar_array_file', 'solar-array.json'));
  ## Maximum age (seconds) of each sidecar file before its reading falls
  ## back to placeholders.  One limit per file, because they are written on
  ## different schedules: the AirGradient trio on a ~30s cron, the solar
  ## array every 15s but carrying data the Enphase pipeline has already
  ## delayed by the better part of a minute.  Measured against the real
  ## site, worst observed ages were inTemp 28s, inCO2 34s, inAQI 58s and
  ## solar 73s, so each limit leaves room for a missed write or two.
  var in_temp_max_age = numExtra($jsstr($Extras.get('in_temp_max_age', 120)), 120);
  var in_co2_max_age = numExtra($jsstr($Extras.get('in_co2_max_age', 120)), 120);
  var in_aqi_max_age = numExtra($jsstr($Extras.get('in_aqi_max_age', 120)), 120);
  var solar_array_max_age = numExtra($jsstr($Extras.get('solar_array_max_age', 150)), 150);

  // Per-file staleness backstop, keyed by element id: how long each file's
  // own timestamp has sat unchanged.  Same role as lastChangeAt in
  // updater_common.inc -- it is used only when the response carries no
  // readable Date header, and it can only ever understate the age.
  var sidecarLastTs = {};
  var sidecarLastChangeAt = {};

  function getInTempFile() {
    var f = getUrlParam('inTempFile');
    return f !== '' ? f : default_in_temp_file;
  }
  function getInCo2File() {
    var f = getUrlParam('inCO2File');
    return f !== '' ? f : default_in_co2_file;
  }
  function getInAqiFile() {
    var f = getUrlParam('inAQIFile');
    return f !== '' ? f : default_in_aqi_file;
  }
  function getSolarArrayFile() {
    var f = getUrlParam('solarArrayFile');
    return f !== '' ? f : default_solar_array_file;
  }

  // Read one sidecar file -- a small JSON document written beside the loop
  // data, e.g. {"total_watts": 2583, "total_timestamp": 1784578112.383} --
  // and update its reading, or show the placeholder if the file is
  // missing, unreadable, or stale.  Options, rather than the nine
  // positional arguments this used to take:
  //
  //   url          where to fetch it from
  //   tsKey        name of the timestamp field inside the document
  //   elementId    the reading to write
  //   key          name of the value field inside the document
  //   digits       decimal places to show
  //   divisor      scale the raw value by this (e.g. 1000 for W -> kW)
  //   width        pad the result to this many characters
  //   placeholder  what to show when the value is unavailable
  //   maxAge       seconds before the value counts as stale
  //   hasColor     the document also carries an "inColor" for the reading
  function updateSidecarFile(opts) {
    var element = document.getElementById(opts.elementId);
    function showUnavailable() {
      element.innerHTML = opts.placeholder;
      if (opts.hasColor) {
        element.style.color = "rgb(255,255,255)";
      }
    }
    // Both anti-cache measures the loop-data poll takes, because these
    // files ship without cache headers too: a unique URL per fetch, and a
    // demand for revalidation.  The loop poll asks for that with a
    // Cache-Control request header and so must gate it to same-origin --
    // the header is not CORS-safelisted and would draw a preflight that a
    // plain file server refuses.  fetch's cache option is not a header, so
    // it needs no such gate; measured cross-origin against a server that
    // 405s OPTIONS, it revalidates with zero preflights.
    var url = opts.url;
    url += (url.indexOf('?') === -1 ? '?' : '&') + '_=' + (cacheBuster++);
    fetch(url, {cache: 'no-cache'})
      .then(response => {
        // fetch only rejects on network failure, not on HTTP error status
        // (e.g. 403/404/500), so check explicitly and route a bad status
        // into the .catch below.
        if (!response.ok) throw new Error('HTTP ' + response.status);
        // Carry the server's own clock forward with the body, by the same
        // rules the loop-data poll uses.
        var serverNow = serverNowFromHeaders(function(name) {
          return response.headers.get(name);
        });
        return response.text().then(text => ({text: text, serverNow: serverNow}));
      })
      .then(r => {
        var j = JSON.parse(r.text);
        if (!j.hasOwnProperty(opts.tsKey) || !j.hasOwnProperty(opts.key)
            || (opts.hasColor && !j.hasOwnProperty("inColor"))) {
          // A writer that stops emitting one of these leaves nothing to
          // judge the reading by, so blank it rather than leaving the last
          // good value on screen for ever -- the same answer an unusable
          // timestamp gets below.
          showUnavailable();
          return;
        }
        var ts = j[opts.tsKey];
        if (sidecarLastTs[opts.elementId] !== ts) {
          sidecarLastTs[opts.elementId] = ts;
          sidecarLastChangeAt[opts.elementId] = performance.now();
        }
        // Age against the server's clock, as the loop-data poll does, so a
        // tablet with a wrong clock does not blank these readings either.
        var age = null;
        if (!isNaN(r.serverNow)) {
          age = Math.round(r.serverNow / 1000 - ts);
        }
        var elapsed = Math.round(
            (performance.now() - sidecarLastChangeAt[opts.elementId]) / 1000);
        age = (age === null) ? elapsed : Math.max(age, elapsed);
        if (age < 0) {
          age = 0;
        }
        if (ts == null || ts === '' || isNaN(Number(ts))) {
          // No usable timestamp: NaN fails the comparison below, so the
          // reading shows its placeholder rather than an invented age.
          age = NaN;
        }
        if (age < opts.maxAge) {
          var value = j[opts.key] / opts.divisor;
          element.innerHTML = padLeft(value.toFixed(opts.digits), opts.width);
          if (opts.hasColor) {
            element.style.color = j['inColor'];
          }
        } else {
          showUnavailable();
        }
      })
      .catch(e => {
        // Bad status, unparseable body, or network error: show the value
        // as unreadable rather than leaving a stale reading on the page.
        showUnavailable();
      });
  }

  // The sidecar files are written far more slowly than the loop data: the
  // AirGradient trio on a ~30s cron, the solar array every 15s.  Reading
  // them every 2s would buy nothing, so throttle to every 8th loop (~16s).
  // Decoupled from the write schedules on purpose, so worst-case staleness
  // stays bounded (~write + read 16s) and this keeps working regardless of
  // how the writers are rescheduled.  %8===1 so a freshly loaded page
  // fetches them on the first tick rather than waiting 16s.
  var sidecarCounter = 0;

  function updateReadings(result, age) {
    // temp
    if (age < max_age && result.hasOwnProperty("current.outTemp.formatted")) {
      setReading("current.outTemp.formatted", padLeft(result["current.outTemp.formatted"], 5));
    } else {
      setReading("current.outTemp.formatted", '&nbsp;??.?');
    }

    // dew point
    if (age < max_age && result.hasOwnProperty("current.dewpoint.formatted")) {
      setReading("current.dewpoint.formatted", padLeft(result["current.dewpoint.formatted"], 5));
    } else {
      setReading("current.dewpoint.formatted", '&nbsp;??.?');
    }

    // wind speed and bearing
    updateWind(result, age);

    // wind gust (10m gust)
    if (age < max_age && result.hasOwnProperty("10m.windGust.max.formatted")) {
      setReading("10m.windGust.max.formatted", padLeft(result["10m.windGust.max.formatted"], 2));
    } else {
      setReading("10m.windGust.max.formatted", '&nbsp;?');
    }

    // wind gust (today)
    if (age < max_age && result.hasOwnProperty("day.windGust.max.formatted")) {
      setReading("day.windGust.max.formatted", padLeft(result["day.windGust.max.formatted"], 2));
    } else {
      setReading("day.windGust.max.formatted", '&nbsp;?');
    }

    // radiation
    if (age < max_age && result.hasOwnProperty("current.radiation.formatted")) {
      setReading("current.radiation.formatted", padLeft(result["current.radiation.formatted"], 4));
    } else {
      setReading("current.radiation.formatted", '????');
    }

    // rain rate
    if (age < max_age && result.hasOwnProperty("current.rainRate.formatted")) {
      setReading("current.rainRate.formatted", result["current.rainRate.formatted"]);
    } else {
      setReading("current.rainRate.formatted", '?.??');
    }

    // current watts generated by solar power 

    updateUV(result, age);
    updateBarometer(result, age);
    updateRain(result, age);

    // aqi
#from weeutil.weeutil import to_bool
## show_purple is a boolean -- read as one rather than compared against two
## particular spellings of true, exactly as the outdoor board reads it.  A
## value that is not a boolean at all turns the reading off rather than
## failing the report.
#try
#set $show_aqi = $to_bool($Extras.get('show_purple', False))
#except
#set $show_aqi = False
#end try
    #if $show_aqi
      // Age-gated like every other reading, as on the outdoor board.
      // Clearing the inline color returns the cell to the footer's red.
      if (age < max_age && result.hasOwnProperty("current.pm2_5_aqi.formatted")) {
        setReading("aqi", padLeft(result["current.pm2_5_aqi.formatted"], 3));
      } else {
        // Three wide: the AQI never runs to four digits -- we would be dead.
        setReading("aqi", '???');
      }
      if (age < max_age && result.hasOwnProperty("current.pm2_5_aqi_color.raw")) {
        document.getElementById("aqi").style.color = decode_rgb(result["current.pm2_5_aqi_color.raw"]);
      } else {
        document.getElementById("aqi").style.color = '';
      }
    #end if

    // indoor temp, CO2 and AQI, and solar production
    sidecarCounter += 1;
    if (sidecarCounter % 8 === 1) {
      updateSidecarFile({url: getInTempFile(), tsKey: "ts",
                         elementId: "current.inTemp.formatted", key: "inTemp",
                         digits: 1, divisor: 1, width: 5,
                         placeholder: '&nbsp;??.?', maxAge: in_temp_max_age,
                         hasColor: false});
      updateSidecarFile({url: getInCo2File(), tsKey: "ts",
                         elementId: "indoor_co2", key: "inCO2",
                         digits: 0, divisor: 1, width: 4,
                         placeholder: '????', maxAge: in_co2_max_age,
                         hasColor: true});
      updateSidecarFile({url: getInAqiFile(), tsKey: "ts",
                         elementId: "indoor_aqi", key: "inAQI",
                         digits: 0, divisor: 1, width: 3,
                         placeholder: '???', maxAge: in_aqi_max_age,
                         hasColor: true});
      updateSidecarFile({url: getSolarArrayFile(), tsKey: "total_timestamp",
                         elementId: "total_watts", key: "total_watts",
                         digits: 1, divisor: 1000, width: 4,
                         placeholder: "??.?", maxAge: solar_array_max_age,
                         hasColor: false});
    }
  }
</script>
