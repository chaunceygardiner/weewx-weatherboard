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

  #if $Extras.has_key('in_temp_file')
    var default_in_temp_file = '$Extras.in_temp_file';
  #else
    var default_in_temp_file = 'inTemp.txt';
  #end if
  #if $Extras.has_key('in_co2_file')
    var default_in_co2_file = '$Extras.in_co2_file';
  #else
    var default_in_co2_file = 'inCO2.txt';
  #end if
  #if $Extras.has_key('in_aqi_file')
    var default_in_aqi_file = '$Extras.in_aqi_file';
  #else
    var default_in_aqi_file = 'inAQI.txt';
  #end if
  #if $Extras.has_key('solar_array_file')
    var default_solar_array_file = '$Extras.solar_array_file';
  #else
    var default_solar_array_file = 'solar-array.json';
  #end if
  ## Maximum age of the indoor observation files before ?? placeholders are
  ## shown; on in_file_slow_host (a host where the files sync less often)
  ## in_file_slow_max_age applies instead.
  #if $Extras.has_key('in_file_max_age')
    var in_file_max_age = $Extras.in_file_max_age;
  #else
    var in_file_max_age = 120;
  #end if
  #if $Extras.has_key('in_file_slow_host')
    var in_file_slow_host = '$Extras.in_file_slow_host';
  #else
    var in_file_slow_host = '';
  #end if
  #if $Extras.has_key('in_file_slow_max_age')
    var in_file_slow_max_age = $Extras.in_file_slow_max_age;
  #else
    var in_file_slow_max_age = 360;
  #end if

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

  // {"total_watts": 2583, "total_timestamp": 1784578112.383, ...}
  // and update elementId, or show the placeholder if the file is missing,
  // unreadable, or stale.
    function updateIndoorFile(url, ts_key, elementId, key, digits, divisor, width, placeholder, hasColor) {
    var element = document.getElementById(elementId);
    function showUnavailable() {
      element.innerHTML = placeholder;
      if (hasColor) {
        element.style.color = "rgb(255,255,255)";
      }
    }
    fetch(url)
      .then(response => {
        // fetch only rejects on network failure, not on HTTP error status
        // (e.g. 403/404/500), so check explicitly and route a bad status
        // into the .catch below.
        if (!response.ok) throw new Error('HTTP ' + response.status);
        return response.text();
      })
      .then(data => {
        var j = JSON.parse(data);
        if (!j.hasOwnProperty(ts_key) || !j.hasOwnProperty(key)
            || (hasColor && !j.hasOwnProperty("inColor"))) {
          return;
        }
        var age = Date.now() / 1000.0 - j[ts_key];
        if (age < in_file_max_age
            || (location.hostname == in_file_slow_host && age < in_file_slow_max_age)) {
          var value = j[key] / divisor;
          element.innerHTML = padLeft(value.toFixed(digits), width);
          if (hasColor) {
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

  // Indoor files are written by cron only every 30s, so reading them every
  // 2s just produces 304s.  Throttle to every 8th loop (~16s).  Decoupled
  // from the cron write schedule on purpose, so worst-case staleness stays
  // bounded (~write 30s + read 16s) and this keeps working regardless of how
  // the writers are rescheduled.  %8===1 so a freshly loaded page fetches
  // indoor data on the first tick rather than waiting 16s.
  var indoorCounter = 0;

  function updateReadings(result, age) {
    // temp
    if (age < 10 && result.hasOwnProperty("current.outTemp.formatted")) {
      setReading("current.outTemp.formatted", padLeft(result["current.outTemp.formatted"], 5));
    } else {
      setReading("current.outTemp.formatted", '&nbsp;??.?');
    }

    // dew point
    if (age < 10 && result.hasOwnProperty("current.dewpoint.formatted")) {
      setReading("current.dewpoint.formatted", padLeft(result["current.dewpoint.formatted"], 5));
    } else {
      setReading("current.dewpoint.formatted", '&nbsp;??.?');
    }

    // wind speed and bearing
    updateWind(result, age);

    // wind gust (10m gust)
    if (age < 10 && result.hasOwnProperty("10m.windGust.max.formatted")) {
      setReading("10m.windGust.max.formatted", padLeft(result["10m.windGust.max.formatted"], 2));
    } else {
      setReading("10m.windGust.max.formatted", '&nbsp;?');
    }

    // wind gust (today)
    if (age < 10 && result.hasOwnProperty("day.windGust.max.formatted")) {
      setReading("day.windGust.max.formatted", padLeft(result["day.windGust.max.formatted"], 2));
    } else {
      setReading("day.windGust.max.formatted", '&nbsp;?');
    }

    // radiation
    if (age < 10 && result.hasOwnProperty("current.radiation.formatted")) {
      setReading("current.radiation.formatted", padLeft(result["current.radiation.formatted"], 4));
    } else {
      setReading("current.radiation.formatted", '????');
    }

    // rain rate
    if (age < 10 && result.hasOwnProperty("current.rainRate.formatted")) {
      setReading("current.rainRate.formatted", result["current.rainRate.formatted"]);
    } else {
      setReading("current.rainRate.formatted", '?.??');
    }

    // current watts generated by solar power 

    updateUV(result, age);
    updateBarometer(result, age);
    updateRain(result, age);

    // aqi
    #if $Extras.has_key('show_purple') and ($Extras.show_purple == 'true' or $Extras.show_purple == 'True')
      if (result.hasOwnProperty("current.pm2_5_1m_aqi.formatted")) {
        setReading("aqi", padLeft(result["current.pm2_5_1m_aqi.formatted"], 3));
      } else if (result.hasOwnProperty("current.pm2_5_aqi.formatted")) {
        setReading("aqi", padLeft(result["current.pm2_5_aqi.formatted"], 3));
      }
      if (result.hasOwnProperty("current.pm2_5_1m_aqi_color.raw")) {
        document.getElementById("aqi").style.color = decode_rgb(result["current.pm2_5_1m_aqi_color.raw"]);
      } else if (result.hasOwnProperty("current.pm2_5_aqi_color.raw")) {
        document.getElementById("aqi").style.color = decode_rgb(result["current.pm2_5_aqi_color.raw"]);
      }
    #end if

    // indoor temp, CO2 and AQI
    indoorCounter += 1;
    if (indoorCounter % 8 === 1) {
      updateIndoorFile(getInTempFile(),     "ts",              "current.inTemp.formatted", "inTemp",       1,    1, 5, '&nbsp;??.?', false);
      updateIndoorFile(getInCo2File(),      "ts",              "indoor_co2",               "inCO2",        0,    1, 4, '????',       true);
      updateIndoorFile(getInAqiFile(),      "ts",              "indoor_aqi",               "inAQI",        0,    1, 3, '???',        true);
      updateIndoorFile(getSolarArrayFile(), "total_timestamp", "total_watts",               "total_watts", 1, 1000, 4, "??.?",       false);
    }
  }
</script>
