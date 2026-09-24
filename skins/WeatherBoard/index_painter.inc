## Copyright (C)2020-2026 by John A Kline (john@johnkline.com)
## Distributed under the terms of the GNU Public License (GPLv3)
## See LICENSE for your rights.
##
## index_painter.inc -- index.html's painter: the boardPaint(result, fresh,
## status) that board.inc calls after every poll and every failure.  It
## sets each of index.html's cells by id, with led.inc's helpers.
#errorCatcher Echo
<script>
  function boardPaint(r, fresh, status) {
    function val(key) {
      return numericReading(r, key, fresh);
    }
    ledSet('led-t', val('current.outTemp.formatted'));
    ledSet('led-td', val('current.dewpoint.formatted'));
    ledWind('led-w', r, val('current.windSpeed.formatted'));
    ledSet('led-g', val(gustField(r, '10m')));
    ledSet('led-gd', val(gustField(r, 'day')));
    ledBarometer('led-b', r, fresh, val('current.barometer.formatted'));
    ledSet('led-rd', val('day.rain.sum.formatted'));
    ledSet('led-r24', val('24h.rain.sum.formatted'));
    ledSet('led-rr', val('current.rainRate.formatted'));
    if (WB.show.uv) { ledSet('led-uv', val('current.UV.formatted')); }
    if (WB.show.radiation) { ledSet('led-rad', val('current.radiation.formatted')); }
    if (WB.show.aqi) { ledAqi('led-aqi', r, val('current.pm2_5_aqi.formatted')); }
    ledSet('led-rh', val('current.outHumidity.formatted'));
    if (WB.show.feels) { ledSet('led-fl', val('current.appTemp.formatted')); }
    ledStatus(status);
  }
</script>
