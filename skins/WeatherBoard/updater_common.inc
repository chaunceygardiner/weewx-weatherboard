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

    if (age < 10 && result.hasOwnProperty("current.rainRate")) {
      setReading("current.rainRate", result["current.rainRate"]);
    } else {
      setReading("current.rainRate", '?.??&nbsp;????');
    }
  }

  function markDisconnected() {
    errorCount += 1;
    console.log('loop data fetch failed; consecutive failures: ' + errorCount);
    document.getElementById("live-label").innerHTML = "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;";
    document.getElementById("activity-string").classList.add("disconnected");
  }

  function updateCurrent() {
    if (pageTimedOut) {
      if (!expiredShown) {
        expiredShown = true;
        document.getElementById("live-label").innerHTML = "Expired";
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
      try {
        // onload also fires for HTTP error statuses (404/500/...);
        // only a 2xx response carries loop data.
        if (this.status < 200 || this.status >= 300) {
          markDisconnected();
          return;
        }
        errorCount = 0;
        var result = JSON.parse(this.responseText);

        // Check the date
        // "dateTime": 1578965850,
        var lastUpdate = new Date(result["current.dateTime.raw"] * 1000);
        var age = Math.round(Math.abs(new Date() - lastUpdate) / 1000);
        var liveLabel = document.getElementById("live-label");
        if (age <= 6) {
          liveLabel.innerHTML = "&nbsp;LIVE&nbsp;";
        } else {
          liveLabel.innerHTML = "&nbsp;" + age + "s ago&nbsp;";
        }

        // Display the time of the last update.
        var activityElement = document.getElementById("activity-string");
        activityElement.innerHTML = lastUpdate.toLocaleTimeString([], {hour: '2-digit', minute: '2-digit', second: '2-digit'});
        activityElement.classList.remove("disconnected");

        updateReadings(result, age);
      } catch (e) {
        console.log(e);
      }
    }
    xhttp.onerror = markDisconnected;
    xhttp.ontimeout = markDisconnected;
    try {
      xhttp.open("GET", "$Extras.loop_data_file", true);
      xhttp.send();
    } catch (e) {
      console.log(e);
    }
  }

  // Set page expiration timer and start polling.
  setPageExpirationTimer();
  setInterval(updateCurrent, refresh_rate * 1000);
  addLoadEvent(updateCurrent);
