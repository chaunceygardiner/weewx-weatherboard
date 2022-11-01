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
      setTimeout(updateCurrent, getTimeToNextUpdateCurrent());
      return false;
    }
    var xhttp = new XMLHttpRequest();
    xhttp.timeout = 2000;
    xhttp.onreadystatechange = function() {
      if (this.readyState == 4) {
        try {
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
            if (age < 10 && result.hasOwnProperty("current.outTemp.formatted")) {
              var temp = result["current.outTemp.formatted"];
              if (temp.length == 3) {
                temp = "&nbsp;&nbsp;" + temp;
              } else if (temp.length == 4) {
                temp = "&nbsp;" + temp;
              }
              document.getElementById("current.outTemp.formatted").innerHTML = temp;
            } else {
              document.getElementById("current.outTemp.formatted").innerHTML = '&nbsp;??.?';
            }
  
            if (age < 10 && result.hasOwnProperty("current.dewpoint.formatted")) {
              // dew point
              var dew = result["current.dewpoint.formatted"];
              if (dew.length == 3) {
                dew = "&nbsp;&nbsp;" + dew;
              } else if (dew.length == 4) {
                dew = "&nbsp;" + dew;
              }
              document.getElementById("current.dewpoint.formatted").innerHTML = dew;
            } else {
              document.getElementById("current.dewpoint.formatted").innerHTML = '&nbsp;??.?';
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
              var windGustDay = result["day.windGust.max"];
              if (windGustDay.length == 1) {
                windGustDay = "&nbsp;" + windGustDay;
              }
              document.getElementById("day.windGust.max").innerHTML = windGustDay;
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
  
            if (age < 10 && result.hasOwnProperty("current.rainRate")) {
              // rain rate
              document.getElementById("current.rainRate").innerHTML = result["current.rainRate"];
            } else {
              document.getElementById("current.rainRate").innerHTML = '?.??&nbsp;????';
            }
  
            if (age < 10 && result.hasOwnProperty("24h.rain.sum")) {
              // rain fall
              document.getElementById("24h.rain.sum").innerHTML = result["24h.rain.sum"];
            } else {
              document.getElementById("24h.rain.sum").innerHTML = '?.??&nbsp;??';
            }
  
            // indoor aqi
            fetch('inAQI.txt')
              .then(indoorAqiResponse => indoorAqiResponse.text())
              .then(indoorAqiData => {
                var indoor = JSON.parse(indoorAqiData);
                if (indoor.hasOwnProperty("ts") && indoor.hasOwnProperty("inAQI") && indoor.hasOwnProperty("inColor")) {
                  now = Date.now() / 1000.0;
                  var ts = indoor['ts'];
                  var age = now - ts;
                  var hostname = location.hostname;
                  if (age < 60 || (age < 360 && hostname == 'www.paloaltoweather.com')) {
                    inAQI = indoor['inAQI'].toFixed(0);
                    inColor = indoor['inColor'];
                  } else {
                    inAQI = '??';
                    inColor = "rgb(128,128,128)";
                  }
                  document.getElementById("indoor_aqi").innerHTML = inAQI;
                  document.getElementById("indoor_aqi").style.color = inColor;
                }
              });
  
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
  
            // indoor temp
            fetch('inTemp.txt')
              .then(response => response.text())
              .then(responseData => {
                try {
                  var j = JSON.parse(responseData);
                  if (j.hasOwnProperty("ts") && j.hasOwnProperty("inTemp")) {
                    now = Date.now() / 1000.0;
                    var ts = j['ts'];
                    var age = now - ts;
                    var hostname = location.hostname;
                    if (age < 60 || (age < 360 && hostname == 'www.paloaltoweather.com')) {
                      inTemp = j['inTemp'].toFixed(1);
                    } else {
                      inTemp = '??.?';
                    }
                    // It will be a tight squeeze (and a shift in characters) if inTemp >= 100.
                    if (inTemp.length == 5) {
                      inTemp = "&nbsp;&nbsp;" + inTemp;
                      } else if (inTemp.length == 6) {
                      inTemp = "&nbsp;" + inTemp;
                    }
                    document.getElementById("current.inTemp.formatted").innerHTML = inTemp;
                  }
                } catch (e) {
                  // Sometimes, we get a partial file to parse.
                }
              });
          } else {
            // Status not OK (!= 200).
            var element = document.getElementById("live-label");
            element.style.fontWeight = "bolder";
            element.style.color = "#e51b23";
            element.innerHTML = "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;";
            var activityElement = document.getElementById("activity-string");
            activityElement.innerHTML = "OFFLINE";
          }
        } catch (e) {
          console.log(e);
        } finally {
          // Check to see if it's time to call expirePage.
          if (Date.now() >= timeOfNextPageExpiration) {
            expirePage();
          }
          // set a timer to call updateCurrent (the 2 second timer) 2s from now.
          setTimeout(updateCurrent, getTimeToNextUpdateCurrent());
        }
      }
    };
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
