## Copyright (C)2020 by John A Kline (john@johnkline.com)
## Distributed under the terms of the GNU Public License (GPLv3)
## See LICENSE for your rights.

#errorCatcher Echo
<script>
  #include "common_updater.inc"

  function updateCurrent() {
    if (pageTimedOut) {
        setTimeout(updateCurrent, getTimeToNextUpdateCurrent());
        return false;
    }
    var xhttp = new XMLHttpRequest();
    xhttp.onreadystatechange = function() {
      if (this.readyState == 4) {
        if (this.status == 200) {
          var result = JSON.parse(this.responseText);

          // Check the date
          // "dateTime": 1578965850,
          var lastUpdate = new Date(result["dateTime"] * 1000);
          var age = Math.round(Math.abs(new Date() - lastUpdate) / 1000);
          var element = document.getElementById("live-label");
          element.style.fontWeight = "bolder";
          if (age < 15) {
            element.style.color = "green";
          } else {
            element.style.color = "red";
          }
          if (age <= 6) {
            element.innerHTML = "&nbsp;LIVE&nbsp;";
          } else {
            element.innerHTML = "&nbsp;" + age + "s ago&nbsp;";
          }

          // Display the time of the last update.
          var activityElement = document.getElementById("activity-string");
          activityElement.innerHTML = lastUpdate.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit', second:'2-digit'});

          // temp
          var temp = result["FMT_outTemp"];
          if (temp.length == 5) {
            temp = "&nbsp;&nbsp;" + temp;
          } else if (temp.length == 6) {
            temp = "&nbsp;" + temp;
          }
          document.getElementById("FMT_outTemp").innerHTML = temp;

          // dew point
          var dew = result["FMT_dewpoint"];
          if (dew.length == 5) {
            dew = "&nbsp;&nbsp;" + dew;
          } else if (dew.length == 6) {
            dew = "&nbsp;" + dew;
          }
          document.getElementById("FMT_dewpoint").innerHTML = dew;

          // wind speed and bearing
          var windSpeed = result["FMT_windSpeed"];
          if (windSpeed.length == 7) {
            windSpeed = "&nbsp;&nbsp;" + windSpeed;
          } else if (windSpeed.length == 8) {
            windSpeed = "&nbsp;" + windSpeed;
          }
          var windBearing = result["COMPASS_windDir"];
          if (result["windSpeed"] == 0.0) {
            windBearing = "";
          }
          if (windBearing.length == 0) {
            windBearing = "&nbsp;&nbsp;&nbsp;";
          } else if (windBearing.length == 1) {
            windBearing = windBearing + "&nbsp;&nbsp;";
          } else if (windBearing.length == 2) {
            windBearing = windBearing + "&nbsp;";
          }
          document.getElementById("windSpeedAndBearing").innerHTML = windSpeed + " " + windBearing;

          // wind gust (10m gust)
          var windGust10m = result["FMT_10mMaxGust"];
          // This yeilds 9.9 mph.   We need to lose the " mph".
          windGust10m = windGust10m.split(" ")[0]
          if (windGust10m.length == 1) {
            windGust10m = "&nbsp;&nbsp;&nbsp;" + windGust10m;
          } else if (windGust10m.length == 2) {
            windGust10m = "&nbsp;&nbsp;" + windGust10m;
          } else if (windGust10m.length == 3) {
            windGust10m = "&nbsp;" + windGust10m;
          }
          document.getElementById("FMT_10mMaxGust").innerHTML = windGust10m;

          // wind gust (today)
          var windGustTM = result["FMT_HI_windGust"];
          if (windGustTM.length == 5) {
            windGustTM = "&nbsp;&nbsp;&nbsp;" + windGustTM;
          } else if (windGustTM.length == 6) {
            windGustTM = "&nbsp;&nbsp;" + windGustTM;
          } else if (windGustTM.length == 7) {
            windGustTM = "&nbsp;" + windGustTM;
          }
          document.getElementById("FMT_HI_windGust").innerHTML = windGustTM;

          // rain rate
          document.getElementById("FMT_rainRate").innerHTML = result["FMT_rainRate"];

          // rain fall
          document.getElementById("FMT_day_rain_total").innerHTML = result["FMT_day_rain_total"];
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
      if (Date.now() >= timeOfNextArchiveInterval) {
        updateAtArchiveInterval();
      }
    }
  }
  function updateAtArchiveInterval() {
    if (pageTimedOut) {
        return false;
    }
    var updateHttp = new XMLHttpRequest();

    updateHttp.onreadystatechange = function() {
      if (this.readyState == 4) {
        if (this.status == 200) {
          var result = JSON.parse(this.responseText.replace(/\n/g, " "));

          #if $Extras.has_key('show_purple') and ($Extras.show_purple == 'Outdoor' or $Extras.show_purple == 'Indoor')
            // aqi
            document.getElementById("aqi").innerHTML = result["aqi"];
            document.getElementById("aqi").style.color = result["aqic"];
          #end if
        }
      }
    };
    try {
      updateHttp.open("GET", "updater.txt", true);
      updateHttp.send();
    } catch (e) {
    } finally {
      timeOfNextArchiveInterval = getTimeOfNextArchiveInterval();
    }
  }
</script>
