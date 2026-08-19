## Copyright (C)2020-2026 by John A Kline (john@johnkline.com)
## Distributed under the terms of the GNU Public License (GPLv3)
## See LICENSE for your rights.
##
## Updater for the board (index.html.tmpl).  Uses loop data fields that
## include the unit label (e.g. current.outTemp).  Scaffolding and the
## shared reading updaters live in updater_common.inc.

#errorCatcher Echo
<script>
#include "updater_common.inc"

  function updateReadings(result, age) {
    // temp (includes unit label, e.g. 54.9°F)
    if (age < 10 && result.hasOwnProperty("current.outTemp")) {
      setReading("current.outTemp", padLeft(result["current.outTemp"], 7));
    } else {
      setReading("current.outTemp", '&nbsp;??.???');
    }

    // dew point
    if (age < 10 && result.hasOwnProperty("current.dewpoint")) {
      setReading("current.dewpoint", padLeft(result["current.dewpoint"], 7));
    } else {
      setReading("current.dewpoint", '&nbsp;??.???');
    }

    // wind speed and bearing
    updateWind(result, age);

    // wind gust (10m gust)
    if (age < 10 && result.hasOwnProperty("10m.windGust.max.formatted")) {
      setReading("10m.windGust.max.formatted", padLeft(result["10m.windGust.max.formatted"], 2));
    } else {
      setReading("10m.windGust.max.formatted", '&nbsp;?');
    }

    // wind gust (today; includes unit label, e.g. 12 mph)
    if (age < 10 && result.hasOwnProperty("day.windGust.max")) {
      setReading("day.windGust.max", padLeft(result["day.windGust.max"], 6));
    } else {
      setReading("day.windGust.max", '&nbsp;?&nbsp;???');
    }

    // rain rate
    if (age < 10 && result.hasOwnProperty("current.rainRate")) {
      setReading("current.rainRate", result["current.rainRate"]);
    } else {
      setReading("current.rainRate", '?.??&nbsp;????');
    }

    updateUV(result, age);
    updateBarometer(result, age);
    updateRain(result, age);

    // aqi
    #if $Extras.has_key('show_purple') and ($Extras.show_purple == 'true' or $Extras.show_purple == 'True')
      // Age-gated like every other reading.  Without the gate a stale board
      // kept showing the last AQI, in the last color, while everything
      // around it had fallen back to question marks.  Clearing the inline
      // color returns the cell to the footer's red, which is what the rest
      // of the placeholders wear.
      if (age < 10 && result.hasOwnProperty("current.pm2_5_1m_aqi.formatted")) {
        setReading("aqi", result["current.pm2_5_1m_aqi.formatted"]);
      } else if (age < 10 && result.hasOwnProperty("current.pm2_5_aqi.formatted")) {
        setReading("aqi", result["current.pm2_5_aqi.formatted"]);
      } else {
        // Three wide: the AQI never runs to four digits -- we would be dead.
        setReading("aqi", '???');
      }
      if (age < 10 && result.hasOwnProperty("current.pm2_5_1m_aqi_color.raw")) {
        document.getElementById("aqi").style.color = decode_rgb(result["current.pm2_5_1m_aqi_color.raw"]);
      } else if (age < 10 && result.hasOwnProperty("current.pm2_5_aqi_color.raw")) {
        document.getElementById("aqi").style.color = decode_rgb(result["current.pm2_5_aqi_color.raw"]);
      } else {
        document.getElementById("aqi").style.color = '';
      }
    #end if
  }
</script>
