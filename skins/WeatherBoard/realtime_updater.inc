## Copyright (C)2020 by John A Kline (john@johnkline.com)
## Distributed under the terms of the GNU Public License (GPLv3)
## See LICENSE for your rights.

#errorCatcher Echo
<script>
  #if $Extras.has_key('page_update_pwd')
    page_update_pwd = '$Extras.page_update_pwd';
  #else
    page_update_pwd = 'foo';
  #end if
  #if $Extras.has_key('refresh_rate')
    refresh_rate = $Extras.refresh_rate;
  #else
    refresh_rate = 2;
  #end if
  #if $Extras.has_key('expiration_time')
    expiration_time = $Extras.expiration_time;
  #else
    expiration_time = 4;
  #end if
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
          return results[1];
      }
  }
  var pageTimedOut = false;
  function expirePage() {
    pageTimedOut = true;
  }
  function clickListener() {
    // disable the onClick event again
    var liveLabel = document.getElementById("live-label");
    liveLabel.removeEventListener('click', clickListener);
    liveLabel.innerHTML = "";
    // restart everything
    pageTimedOut = false;
    // restart the page timeout
    setPageExpirationTimer();
  }
  function setPageExpirationTimer() {
    if (getUrlParam('pageUpdate') !== page_update_pwd) {
      // expire in N hours
      setTimeout(expirePage, 1000 * 60 * 60 * expiration_time);
    }
  }
  // Set interval and page expiration timer.
  setPageExpirationTimer();
  setInterval(updateCurrent, refresh_rate * 1000);
  addLoadEvent(updateCurrent);

  const barometer_symbols = {
     '4': '<i class="arrow up_dir" style="margin-right:15px;"></i>&plus;&plus;',
     '3': '<i class="arrow up_dir" style="margin-right:15px;"></i>&plus;&nbsp;',
     '2': '<i class="arrow up_dir" style="margin-right:15px;"></i>&nbsp;&nbsp;',
     '1': '<i class="arrow up_dir" style="margin-right:15px;"></i>&minus;&nbsp;',
     '0': '&minus;&minus;&nbsp;',
    '-1': '<i class="arrow down_dir" style="margin-right:15px;"></i>&minus;&nbsp;',
    '-2': '<i class="arrow down_dir" style="margin-right:15px;"></i>&nbsp;&nbsp;',
    '-2': '<i class="arrow down_dir" style="margin-right:15px;"></i>&nbsp;&nbsp;',
    '-3': '<i class="arrow down_dir" style="margin-right:15px;"></i>&plus;&nbsp;',
    '-4': '<i class="arrow down_dir" style="margin-right:15px;"></i>&plus;&plus;',
  };

  var counter = 0;
  function updateCurrent() {
    if (pageTimedOut) {
      // If click listener not already set up...
      var liveLabel = document.getElementById("live-label");
      if (liveLabel.innterHTML != "Expired") {
        liveLabel.innerHTML = "Expired";
        var activityElement = document.getElementById("activity-string");
        activityElement.innerHTML = "CLICK-ME";
        // set an onclick event to restart
        activityElement.addEventListener("click", clickListener);
      }
      return false;
    }
    var xhttp = new XMLHttpRequest();
    xhttp.timeout = 1800;
    xhttp.onload = function() {
      try {
        counter = 0;
        var result = JSON.parse(this.responseText);

        // Check the date
        // "dateTime": 1578965850,
        var lastUpdate = new Date(result["current.dateTime.raw"] * 1000);
        var age = Math.round(Math.abs(new Date() - lastUpdate) / 1000);
        var element = document.getElementById("live-label");
        element.style.fontWeight = "bolder";
        element.style.color = "#e51b23";
        if (age <= 6) {
          element.innerHTML = "&nbsp;LIVE&nbsp;";
        } else {
          element.innerHTML = "&nbsp;" + age + "s ago&nbsp;";
        }

        // Display the time of the last update.
        var activityElement = document.getElementById("activity-string");
        activityElement.innerHTML = lastUpdate.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit', second:'2-digit'});
        activityElement.style.color = "red";

        // temp
        if (age < 10 && result.hasOwnProperty("current.outTemp")) {
          var temp = result["current.outTemp"];
          if (temp.length == 5) {
            temp = "&nbsp;&nbsp;" + temp;
          } else if (temp.length == 6) {
            temp = "&nbsp;" + temp;
          }
          document.getElementById("current.outTemp").innerHTML = temp;
        } else {
          document.getElementById("current.outTemp").innerHTML = '&nbsp;??.???';
        }

        if (age < 10 && result.hasOwnProperty("current.dewpoint")) {
          // dew point
          var dew = result["current.dewpoint"];
          if (dew.length == 5) {
            dew = "&nbsp;&nbsp;" + dew;
          } else if (dew.length == 6) {
            dew = "&nbsp;" + dew;
          }
          document.getElementById("current.dewpoint").innerHTML = dew;
        } else {
          document.getElementById("current.dewpoint").innerHTML = '&nbsp;??.???';
        }

        if (age < 10 && result.hasOwnProperty("current.windSpeed.formatted")) {
          // wind speed and bearing
          var windSpeed = result["current.windSpeed.formatted"];
          if (windSpeed.length == 1) {
            windSpeed = '&nbsp;' + windSpeed;
          }
          var windBearing = "";
          if (result["current.windSpeed.raw"] != 0.0) {
            if (result.hasOwnProperty("current.windDir.ordinal_compass")) {
              windBearing = result["current.windDir.ordinal_compass"];
            }
          }
          if (windBearing.length == 0) {
            windBearing = windBearing + '&nbsp;&nbsp;&nbsp;';
          } else if (windBearing.length == 1) {
            windBearing = windBearing + '&nbsp;&nbsp;';
          } else if (windBearing.length == 2) {
            windBearing = windBearing + '&nbsp;';
          }
          document.getElementById("windSpeedAndBearing").innerHTML = windSpeed + " " + windBearing;
        } else {
          document.getElementById("windSpeedAndBearing").innerHTML = '&nbsp;?&nbsp;???';
        }

        if (age < 10 && result.hasOwnProperty("10m.windGust.max.formatted")) {
          // wind gust (10m gust)
          var windGust10m = result["10m.windGust.max.formatted"];
          if (windGust10m.length == 1) {
            windGust10m = "&nbsp;" + windGust10m;
          }
          document.getElementById("10m.windGust.max.formatted").innerHTML = windGust10m;
        } else {
          document.getElementById("10m.windGust.max.formatted").innerHTML = '&nbsp;?';
        }

        if (age < 10 && result.hasOwnProperty("day.windGust.max")) {
          // wind gust (today)
          var windGustTM = result["day.windGust.max"];
          if (windGustTM.length == 5) {
            windGustTM = "&nbsp;" + windGustTM;
          }
          document.getElementById("day.windGust.max").innerHTML = windGustTM;
        } else {
          document.getElementById("day.windGust.max").innerHTML = '&nbsp;?&nbsp;???';
        }

        if (age < 10 && result.hasOwnProperty("current.UV.formatted")) {
          uv = result["current.UV.formatted"];
          if (uv.length == 3) {
            uv = "&nbsp;" + uv;
          }
        } else {
          uv = "&nbsp;?.?";
        }
        document.getElementById("current.UV.formatted").innerHTML = uv;

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
        document.getElementById("barometer").innerHTML = barometer_value;

        if (age < 10 && result.hasOwnProperty("day.rain.sum.formatted")) {
          // rain fall
          document.getElementById("day.rain.sum.formatted").innerHTML = result["day.rain.sum.formatted"];
        } else {
          document.getElementById("day.rain.sum.formatted").innerHTML = '?.??';
        }

        if (age < 10 && result.hasOwnProperty("24h.rain.sum.formatted")) {
          // rain fall
          document.getElementById("24h.rain.sum.formatted").innerHTML = result["24h.rain.sum.formatted"];
        } else {
          document.getElementById("24h.rain.sum.formatted").innerHTML = '?.??';
        }

        if (age < 10 && result.hasOwnProperty("current.rainRate")) {
          // rain rate
          document.getElementById("current.rainRate").innerHTML = result["current.rainRate"];
        } else {
          document.getElementById("current.rainRate").innerHTML = '?.??&nbsp;????';
        }

        // aqi
        #if $Extras.has_key('show_purple') and ($Extras.show_purple == 'true' or $Extras.show_purple == 'True')
          if (result.hasOwnProperty("current.pm2_5_1m_aqi.formatted")) {
            document.getElementById("aqi").innerHTML = result["current.pm2_5_1m_aqi.formatted"];
          } else if (result.hasOwnProperty("current.pm2_5_aqi.formatted")) {
            document.getElementById("aqi").innerHTML = result["current.pm2_5_aqi.formatted"];
          }
          if (result.hasOwnProperty("current.pm2_5_1m_aqi_color.raw")) {
            document.getElementById("aqi").style.color = decode_rgb(result["current.pm2_5_1m_aqi_color.raw"]);
          } else if (result.hasOwnProperty("current.pm2_5_aqi_color.raw")) {
            document.getElementById("aqi").style.color = decode_rgb(result["current.pm2_5_aqi_color.raw"]);
          }
        #end if
      } catch (e) {
        console.log(e);
      }
    }
    xhttp.onerror = function() {
      counter += 1;
      console.log('status: ' + this.status + ', counter: ' + counter);
      var element = document.getElementById("live-label");
      element.style.fontWeight = "bolder";
      element.style.color = "#e51b23";
      element.innerHTML = "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;";
      var activityElement = document.getElementById("activity-string");
      activityElement.style.color = "blue";
    }
    try {
      xhttp.open("GET", "$Extras.loop_data_file", true);
      xhttp.send();
    } catch (e) {
      console.log(e);
    }
  }
  function decode_rgb(i) {
    var red   = i >> 16;
    var green = (i & 0xFF00) >> 8;
    var blue  = i & 0xFF;
    return `rgb(${red},${green},${blue})`
  }
</script>
