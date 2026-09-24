## Copyright (C)2020-2026 by John A Kline (john@johnkline.com)
## Distributed under the terms of the GNU Public License (GPLv3)
## See LICENSE for your rights.
##
## splitflap.inc -- the split-flap board's painter (splitflap.html).
## board.inc calls boardPaint(result, fresh, status) after every poll and
## every failure.  Included at the END of the page's body: it builds the
## flaps into the rows above it as it runs.
##
## Each row is twelve flaps.  When a character changes its flap runs
## forward through the drum to the new one, as the real boards do.  A
## missing reading is question marks of its own width, with a blank flap
## where its decimal point was.  The lamp at the end of a row lights only
## when the row has something to say, and it judges by the figure the row
## SHOWS, never a raw value behind it: a gust showing 25 lights the gust
## lamp even if it was 24.6, and a rate showing 0.00 never lights the rain
## lamp, whatever fraction of a hundredth lies behind it.
#errorCatcher Echo
#import weewx.units
## The lamps' thresholds, in this report's own units: gusts from 25 mph,
## low pressure under 29.70 inHg, high over 30.20.  The report's unit for
## each is passed in: a #def cannot see the page's #set variables.  A
## report with no unit information keeps them in US units.
#def wb_conv($value, $unit, $group, $target)
#try
#return weewx.units.convert(weewx.units.ValueTuple($value, $unit, $group), $target)[0]
#except
#return $value
#end try
#end def
#try
#set $wb_gust_unit = $unit.unit_type.windGust
#set $wb_baro_unit = $unit.unit_type.barometer
#except
#set $wb_gust_unit = 'mile_per_hour'
#set $wb_baro_unit = 'inHg'
#end try
<script>
  var FLAP_WIDTH = 12;
  var FLAP = {
    gustWarn: $wb_conv(25.0, 'mile_per_hour', 'group_speed', $wb_gust_unit),
    baroLow: $wb_conv(29.70, 'inHg', 'group_pressure', $wb_baro_unit),
    baroHigh: $wb_conv(30.20, 'inHg', 'group_pressure', $wb_baro_unit),
    text: {
      hi: $jsstr($gettext("HI")),
      rh: $jsstr($gettext("RH")),
      calm: $jsstr($gettext("CALM")),
      gust: $jsstr($gettext("G")),
      perHour: $jsstr($gettext("/HR")),
      aqi: [$jsstr($gettext("GOOD")), $jsstr($gettext("MODERATE")), $jsstr($gettext("USG")),
            $jsstr($gettext("UNHLTHY")), $jsstr($gettext("V UNHLTH")), $jsstr($gettext("HAZARD"))]
    }
  };
  var FLAP_COLORS = { aging: '#f2a01f', waiting: '#f2a01f', old: '#ff3b30', error: '#ff3b30',
                      expired: '#3a8fd6', rain: '#3aa0ff', wind: '#ff3b30', low: '#ff6600', high: '#3399ff' };

  // The drum: the order a flap runs through its characters.  Anything not
  // on it (an accented capital from another language, the trend arrow)
  // is shown directly.
  var FLAP_DRUM = " ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.:\u00b0/-?";
  var flapCells = {};

  function flapBuild() {
    var rows = document.querySelectorAll('.flap-row');
    for (var r = 0; r < rows.length; r++) {
      var row = rows[r], cells = [];
      for (var i = 0; i < FLAP_WIDTH; i++) {
        var f = document.createElement('span');
        f.className = 'flap';
        var b = document.createElement('b');
        b.appendChild(document.createTextNode('\u00a0'));
        f.appendChild(b);
        row.appendChild(f);
        cells.push(f);
      }
      flapCells[row.id] = cells;
    }
  }

  function flapHtml(ch) {
    if (ch === ' ') {
      return '\u00a0';
    }
    // The barometer's trend: ">" and its code, drawn (Jost has no
    // arrows).  Only board.inc's trendCode() builds that item.
    if (ch.length > 1 && ch.charAt(0) === '>') {
      return trendSvg(Number(ch.slice(1)), 'flap-trend');
    }
    return ch.replace(/&/g, '&amp;').replace(/</g, '&lt;');
  }
  function flapSet(f, ch) {
    if (f.getAttribute('data-ch') === ch) {
      return;
    }
    var from = f.getAttribute('data-ch') || ' ';
    f.setAttribute('data-ch', ch);
    var b = f.firstChild;
    var i = FLAP_DRUM.indexOf(from), j = FLAP_DRUM.indexOf(ch), steps = [];
    if (i < 0 || j < 0) {
      steps = [ch];
    } else {
      for (var k = i; k !== j; k = (k + 1) % FLAP_DRUM.length) {
        steps.push(FLAP_DRUM.charAt((k + 1) % FLAP_DRUM.length));
      }
    }
    if (steps.length > 9) {
      steps = steps.slice(-9);
    }
    if (steps.length === 0) {
      steps = [ch];
    }
    var n = 0;
    (function next() {
      if (f.getAttribute('data-ch') !== ch) {
        return;
      }
      b.innerHTML = flapHtml(steps[n]);
      f.classList.remove('flap-tick');
      void f.offsetWidth;
      f.classList.add('flap-tick');
      if (++n < steps.length) {
        setTimeout(next, 70);
      }
    })();
  }
  // A row's text as flaps.  An item of more than one character (the trend
  // arrow) takes one flap.
  function flapShow(rowId, items) {
    var cells = flapCells[rowId];
    if (!cells) {
      return;
    }
    if (typeof items === 'string') {
      items = items.toUpperCase().replace(/\u00df/g, 'SS').split('');
    }
    for (var i = 0; i < FLAP_WIDTH; i++) {
      flapSet(cells[i], i < items.length ? items[i] : ' ');
    }
  }
  function flapLamp(rowId, color) {
    var lamp = document.getElementById(rowId + '-lamp');
    if (lamp === null) {
      return;
    }
    lamp.classList.toggle('flap-lit', !!color);
    if (color) {
      lamp.style.setProperty('--flap-lamp', color);
    }
  }

  function padL(s, w) { s = String(s); while (s.length < w) { s = ' ' + s; } return s; }
  function padR(s, w) { s = String(s); while (s.length < w) { s += ' '; } return s; }
  // A figure squeezed to a width: fewer decimals until it fits.
  function squeeze(s, w) {
    s = String(s);
    var v = Number(s), d = (s.split('.')[1] || '').length;
    while (s.length > w && d > 0 && isFinite(v)) {
      d--;
      s = v.toFixed(d);
    }
    return s;
  }
  // Two halves of a row: the left one padded, the right one pushed to the
  // row's end; the gap closes up if the two together run long.
  function flapPair(left, lw, right) {
    var s = padR(left, lw) + padL(right, FLAP_WIDTH - lw);
    return s.length > FLAP_WIDTH ? (left + ' ' + right).slice(0, FLAP_WIDTH) : s;
  }
  // A placeholder: the reading's shape with its digits as question marks
  // and its decimal point a blank flap.
  var flapShape = {};
  function q(key, text, dflt) {
    if (text !== null) {
      flapShape[key] = String(text).replace(/[0-9]/g, '?').replace(/\./g, ' ');
      return String(text);
    }
    return flapShape[key] || dflt;
  }
  function aqiWord(v) {
    var t = FLAP.text.aqi;
    return v <= 50 ? t[0] : v <= 100 ? t[1] : v <= 150 ? t[2] : v <= 200 ? t[3] : v <= 300 ? t[4] : t[5];
  }

  function has(r, key) {
    return r.hasOwnProperty(key) && r[key] !== null && r[key] !== '';
  }
  function boardPaint(r, fresh, status) {
    function val(key) {
      return numericReading(r, key, fresh);
    }
    var st = status.text === null ? '??:??:??' : status.text;
    flapShow('flap-time', padL(st, Math.min(FLAP_WIDTH, Math.max(st.length, 11))));
    flapLamp('flap-time', FLAP_COLORS[status.kind] || null);

    flapShow('flap-temp', flapPair(q('t', val('current.outTemp.formatted'), '?? ?') + '\u00b0', 6,
                                   FLAP.text.hi + ' ' + q('hi', val('day.outTemp.max.formatted') === null ? null
                                       : String(Math.round(Number(val('day.outTemp.max.formatted')))), '??')));
    flapShow('flap-dew', flapPair(q('td', val('current.dewpoint.formatted'), '?? ?') + '\u00b0', 6,
                                  FLAP.text.rh + ' ' + q('rh', val('current.outHumidity.formatted'), '??')));

    var speed = val('current.windSpeed.formatted'), left;
    if (speed === null) {
      left = '??? ' + (flapShape.ws || '??');
    } else if (Number(speed) === 0) {
      // Calm by the speed as shown: a raw 0.00009 is not zero, but it
      // shows as 0.
      left = FLAP.text.calm;
    } else {
      flapShape.ws = speed.replace(/[0-9]/g, '?');
      left = padR(has(r, 'current.windDir.ordinal_compass') ? String(r['current.windDir.ordinal_compass']) : '', 3)
          + ' ' + padL(speed, 3);
    }
    var gust = val(gustField(r, '10m'));
    flapShow('flap-wind', flapPair(left, 7, FLAP.text.gust + ' ' + q('g', gust, '??')));
    flapLamp('flap-wind', gust !== null && Number(gust) >= FLAP.gustWarn ? FLAP_COLORS.wind : null);

    var baro = val('current.barometer.formatted');
    var items = (q('b', baro, '?? ???') + ' ').split('');
    if (baro !== null && trendCode(r) !== null) {
      items.push('>' + trendCode(r));
    }
    flapShow('flap-baro', items);
    flapLamp('flap-baro', baro === null ? null
             : Number(baro) < FLAP.baroLow ? FLAP_COLORS.low : Number(baro) > FLAP.baroHigh ? FLAP_COLORS.high : null);

    // Today's rain and the rate on one line: "1.23 0.42/HR".
    var room = FLAP_WIDTH - FLAP.text.perHour.length - 1;
    var today = q('rd', val('day.rain.sum.formatted'), '? ??');
    var rate = q('rr', val('current.rainRate.formatted'), '? ??');
    var tw = Math.min(today.length, Math.max(1, room - Math.min(rate.length, 4)));
    today = squeeze(today, tw);
    rate = squeeze(rate, room - today.length);
    flapShow('flap-rain', today + ' ' + rate + FLAP.text.perHour);
    // Lit by the rate as shown, for the same reason as calm: a raw rate
    // of 0.0000001 shows as 0.00, and a lamp over 0.00 says rain is falling.
    flapLamp('flap-rain', Number(val('current.rainRate.formatted')) > 0 ? FLAP_COLORS.rain : null);

    if (WB.show.aqi) {
      var aqi = val('current.pm2_5_aqi.formatted');
      flapShow('flap-air', padL(q('aqi', aqi, '??'), 3) + (aqi === null ? '' : ' ' + aqiWord(Number(aqi))));
      flapLamp('flap-air', aqi !== null && has(r, 'current.pm2_5_aqi_color.raw')
               ? decodeRgb(r['current.pm2_5_aqi_color.raw']) : null);
    }
    flapFit();
  }

  // THE FIT.  The board is laid out in rem for a 16:10 tablet and then
  // scaled by --flap-fit, the largest factor (never above 1) at which it,
  // its title and its footer fit the screen -- a language with long row
  // names, or a long title, runs wider.  Rechecked when the window changes.
  var flapFitDone = false;
  function flapFit(force) {
    if (flapFitDone && !force) {
      return;
    }
    flapFitDone = true;
    var root = document.documentElement;
    for (var pass = 0; pass < 2; pass++) {
      var scale = Number(getComputedStyle(root).getPropertyValue('--flap-fit')) || 1;
      var board = document.getElementById('flap-board').getBoundingClientRect();
      var foot = document.getElementById('flap-foot').getBoundingClientRect();
      var title = document.getElementById('flap-title');
      var tr = title.getBoundingClientRect(), ts = getComputedStyle(title);
      var titleH = tr.height + parseFloat(ts.marginTop) + parseFloat(ts.marginBottom);
      var worst = Math.min(window.innerWidth / (Math.max(board.width, tr.width) * 1.02),
                           window.innerHeight / ((board.height + foot.height + titleH) * 1.04));
      root.style.setProperty('--flap-fit', String(Math.min(1, Math.floor(scale * worst * 100) / 100)));
    }
  }
  window.addEventListener('resize', function () { flapFit(true); });
  // The row names are set in Jost, and the first paint can come before it
  // has loaded; fit again once it has, since the names then measure true.
  if (document.fonts && document.fonts.ready) {
    document.fonts.ready.then(function () { flapFit(true); });
  }
  // Included at the end of the page's body, after its rows, so the flaps
  // exist before board.inc paints the first time.
  flapBuild();
</script>
