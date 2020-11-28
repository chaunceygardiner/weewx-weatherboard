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
    refresh_rate = 2.5;
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
    if (pageTimedOut) {
        // We've already timed out,
        return false;
    }
    pageTimedOut = true;
    var liveLabel = document.getElementById("live-label");
    liveLabel.innerHTML = "CLICK";
    liveLabel.style.color = "red";
    var activityElement = document.getElementById("activity-string");
    activityElement.innerHTML = "";
    // set an onclick event on live-label to restart everything
    liveLabel.addEventListener("click", clickListener);
  }
  function clickListener() {
    // disable the onClick event again
    var liveLabel = document.getElementById("live-label");
    liveLabel.removeEventListener('click', clickListener);
    liveLabel.innerHTML = "";
    // restart everything
    pageTimedOut = false;
    // restart the page timeout
    timeOfNextPageExpiration = getTimeOfNextPageExpiration();
  }
  function getTimeToNextUpdateCurrent() {
    return refresh_rate * 1000;
  }
  // Get time that page expires.
  function getTimeOfNextPageExpiration() {
    if (getUrlParam('pageUpdate') !== page_update_pwd) {
      // expire in N hours
      return Date.now() + 1000 * 60 * 60 * expiration_time;
    } else {
      // expire in 10,000 days
      return Date.now() + 1000 * 60 * 60 * 24 * 10000;
    }
  }
  // global variables - times of next events
  var timeOfNextPageExpiration = getTimeOfNextPageExpiration();
  addLoadEvent(updateCurrent);

  var barometer_symbols = {
     '4': '&#9650;&plus;&plus;',
     '3': '&#9650;&plus;&nbsp;',
     '2': '&#9650;&nbsp;&nbsp;',
     '1': '&#9650;&minus;&nbsp;',
     '0': '&minus;&minus;&nbsp;',
    '-1': '&#9660;&minus;&nbsp;',
    '-2': '&#9660;&nbsp;&nbsp;',
    '-3': '&#9660;&plus;&nbsp;',
    '-4': '&#9660;&plus;&plus;',
  };

  function updateCurrent() {
    if (pageTimedOut) {
        return false;
    }
    var xhttp = new XMLHttpRequest();
    xhttp.onreadystatechange = function() {
      if (this.readyState == 4) {
        if (this.status == 200) {
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

          // temp
          if (result.hasOwnProperty("current.outTemp")) {
            var temp = result["current.outTemp"];
            if (temp.length == 5) {
              temp = "&nbsp;&nbsp;" + temp;
            } else if (temp.length == 6) {
              temp = "&nbsp;" + temp;
            }
            document.getElementById("current.outTemp").innerHTML = temp;
          } else {
            document.getElementById("current.outTemp").innerHTML = '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;';
          }

          if (result.hasOwnProperty("current.dewpoint")) {
            // dew point
            var dew = result["current.dewpoint"];
            if (dew.length == 5) {
              dew = "&nbsp;&nbsp;" + dew;
            } else if (dew.length == 6) {
              dew = "&nbsp;" + dew;
            }
            document.getElementById("current.dewpoint").innerHTML = dew;
          } else {
            document.getElementById("current.dewpoint").innerHTML = '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;';
          }

          if (result.hasOwnProperty("current.windSpeed.formatted")) {
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
            document.getElementById("windSpeedAndBearing").innerHTML = '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;';
          }

          if (result.hasOwnProperty("10m.windGust.max.formatted")) {
            // wind gust (10m gust)
            var windGust10m = result["10m.windGust.max.formatted"];
            if (windGust10m.length == 1) {
              windGust10m = "&nbsp;" + windGust10m;
            }
            document.getElementById("10m.windGust.max.formatted").innerHTML = windGust10m;
          } else {
            document.getElementById("10m.windGust.max.formatted").innerHTML = '&nbsp;&nbsp;';
          }

          if (result.hasOwnProperty("day.windGust.max")) {
            // wind gust (today)
            var windGustTM = result["day.windGust.max"];
            if (windGustTM.length == 5) {
              windGustTM = "&nbsp;" + windGustTM;
            }
            document.getElementById("day.windGust.max").innerHTML = windGustTM;
          } else {
            document.getElementById("day.windGust.max").innerHTML = '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;';
          }

          if (result.hasOwnProperty("current.UV.formatted")) {
            uv = result["current.UV.formatted"];
            if (uv.lengh == 3) {
              uv = "&nbsp;" + uv;
            }
          } else {
            uv = "&nbsp;N/A";
          }
          document.getElementById("current.UV.formatted").innerHTML = uv;

          if (result.hasOwnProperty("current.barometer.formatted")) {
            barometer_value = result["current.barometer.formatted"] + "&nbsp;";
            if (result.hasOwnProperty("trend.barometer.code")) {
              barometer_value += barometer_symbols[result["trend.barometer.code"]];
            } else {
              barometer_value += "&nbsp;&nbsp;&nbsp;"
            }
          } else {
            barometer_value += "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"
          }
          document.getElementById("barometer").innerHTML = barometer_value;

          if (result.hasOwnProperty("current.rainRate")) {
            // rain rate
            document.getElementById("current.rainRate").innerHTML = result["current.rainRate"];
          } else {
            document.getElementById("current.rainRate").innerHTML = '&nbsp;&nbsp;&nbsp;&nbsp;';
          }

          if (result.hasOwnProperty("day.rain.sum")) {
            // rain fall
            document.getElementById("day.rain.sum").innerHTML = result["day.rain.sum"];
          } else {
            document.getElementById("day.rain.sum").innerHTML = '';
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
        }
      }
    };
    try {
      xhttp.open("GET", "$Extras.loop_data_file", true);
      xhttp.send();
    } catch (e) {
    } finally {
      // set a timer to call updateCurrent (the 2 second timer) 2s from now.
      setTimeout(updateCurrent, getTimeToNextUpdateCurrent());
      // Check to see if it's time to call expirePage.
      if (Date.now() >= timeOfNextPageExpiration) {
        expirePage();
      }
    }
  }
  function decode_rgb(i) {
    var red   = i >> 16;
    var green = (i & 0xFF00) >> 8;
    var blue  = i & 0xFF;
    return `rgb(${red},${green},${blue})`
  }
</script>
