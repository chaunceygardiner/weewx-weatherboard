## Copyright (C)2020-2026 by John A Kline (john@johnkline.com)
## Distributed under the terms of the GNU Public License (GPLv3)
## See LICENSE for your rights.
##
## index_painter.inc -- index.html's painter: the boardPaint(result, fresh,
## status) that board.inc calls after every poll and every failure.  It
## sets each of index.html's cells by id, with readout.inc's helpers.
#errorCatcher Echo
<script>
  function boardPaint(r, fresh, status) {
    function val(key) {
      return numericReading(r, key, fresh);
    }
    roSet('ro-t', val('current.outTemp.formatted'));
    roSet('ro-td', val('current.dewpoint.formatted'));
    roWind('ro-w', r, val('current.windSpeed.formatted'));
    roSet('ro-g', val(gustField(r, '10m')));
    roSet('ro-gd', val(gustField(r, 'day')));
    roBarometer('ro-b', r, fresh, val('current.barometer.formatted'));
    roSet('ro-rd', val('day.rain.sum.formatted'));
    roSet('ro-r24', val('24h.rain.sum.formatted'));
    roSet('ro-rr', val('current.rainRate.formatted'));
    if (WB.show.uv) { roSet('ro-uv', val('current.UV.formatted')); }
    if (WB.show.radiation) { roSet('ro-rad', val('current.radiation.formatted')); }
    if (WB.show.aqi) { roAqi('ro-aqi', r, val('current.pm2_5_aqi.formatted')); }
    roSet('ro-rh', val('current.outHumidity.formatted'));
    roSet('ro-hi', val('day.outTemp.max.formatted'));
    if (WB.show.feels) { roSet('ro-fl', val('current.appTemp.formatted')); }
    roDate('ro-date', r, fresh);
    roStatus(status);
  }
</script>
