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
    if (age < max_age && result.hasOwnProperty("current.outTemp")) {
      setReading("current.outTemp", padLeft(result["current.outTemp"], 7));
    } else {
      setReading("current.outTemp", '&nbsp;??.???');
    }

    // dew point
    if (age < max_age && result.hasOwnProperty("current.dewpoint")) {
      setReading("current.dewpoint", padLeft(result["current.dewpoint"], 7));
    } else {
      setReading("current.dewpoint", '&nbsp;??.???');
    }

    // wind speed and bearing
    updateWind(result, age);

    // wind gust (10m gust)
    if (age < max_age && result.hasOwnProperty("10m.windGust.max.formatted")) {
      setReading("10m.windGust.max.formatted", padLeft(result["10m.windGust.max.formatted"], 2));
    } else {
      setReading("10m.windGust.max.formatted", '&nbsp;?');
    }

    // wind gust (today; includes unit label, e.g. 12 mph)
    if (age < max_age && result.hasOwnProperty("day.windGust.max")) {
      setReading("day.windGust.max", padLeft(result["day.windGust.max"], 6));
    } else {
      setReading("day.windGust.max", '&nbsp;?&nbsp;???');
    }

    updateUV(result, age);
    updateBarometer(result, age);
    updateRain(result, age);

    // aqi
#from weeutil.weeutil import to_bool
## show_purple is a boolean -- read as one rather than compared against two
## particular spellings of true.  A value that is not a boolean at all turns
## the reading off rather than failing the report.
#try
#set $show_aqi = $to_bool($Extras.get('show_purple', False))
#except
#set $show_aqi = False
#end try
    #if $show_aqi
      // Age-gated like every other reading.  Without the gate a stale board
      // kept showing the last AQI, in the last color, while everything
      // around it had fallen back to question marks.  Clearing the inline
      // color returns the cell to the footer's red, which is what the rest
      // of the placeholders wear.
      if (age < max_age && result.hasOwnProperty("current.pm2_5_aqi.formatted")) {
        setReading("aqi", result["current.pm2_5_aqi.formatted"]);
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
  }
</script>
