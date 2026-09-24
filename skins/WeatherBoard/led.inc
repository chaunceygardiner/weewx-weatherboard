## Copyright (C)2020-2026 by John A Kline (john@johnkline.com)
## Distributed under the terms of the GNU Public License (GPLv3)
## See LICENSE for your rights.
##
## led.inc -- how an LED page draws: its cells, its fit to the screen and
## the helpers a painter is built from.  It paints nothing itself.  The
## page's own painter follows it, index_painter.inc for index.html: the
## boardPaint(result, fresh, status) that board.inc calls after every poll
## and every failure, which sets each of the page's cells by id and ends
## with ledStatus(status).
##
## THE LEDS.  Every reading is set in the LCD font over a dim copy of
## itself with each lit character replaced by "8", so the unlit segments
## show the way they do on a real display.  The font has digits, capital
## letters, the decimal point, colon, slash and question mark, and nothing
## else -- no hyphen, no accented letters -- and the board never lets a
## character fall back to another font:
##   - A missing digit, and a minus sign, is the 8's own middle segment
##     lit: a real "8" clipped to that segment's outline (.led-mid in
##     weatherboard.css).
##   - With no data the decimal point stays dark.
##   - An accented capital is its base letter from the font with the
##     accent drawn over it (.led-ac-*): two dots, a ring, an acute stroke,
##     or the slash through an O.  ß is set as SS.
##   - Any other character is left out, and says so in the console; the
##     language files are tested to carry only characters this can set.
#errorCatcher Echo
<script>
  // Characters the LCD font draws itself, and the accented capitals the
  // board draws from a base letter and a mark.
  var LED_NATIVE = /^[A-Z0-9 .:\/?]$/;
  var LED_MARKS = {
    '\u00c4': ['A', 'uml'], '\u00d6': ['O', 'uml'], '\u00dc': ['U', 'uml'],
    '\u00c5': ['A', 'ring'], '\u00d8': ['O', 'slash'],
    '\u00c1': ['A', 'acute'], '\u00c9': ['E', 'acute'], '\u00cd': ['I', 'acute'],
    '\u00d3': ['O', 'acute'], '\u00da': ['U', 'acute']
  };

  // One cell's two layers: the unlit segments, and what is lit.  ok is
  // false when the text is a placeholder for missing data.
  function ledLayers(text, ok) {
    var ghost = '', lit = '';
    text = String(text).toUpperCase().replace(/\u00df/g, 'SS');
    for (var i = 0; i < text.length; i++) {
      var ch = text[i];
      if (ch === '-') {
        ghost += '8';
        lit += '<span class="led-mid">8</span>';
      } else if (ch === '.') {
        ghost += '.';
        lit += ok ? '.' : '<span class="led-dp-off">.</span>';
      } else if (ch === ' ' || ch === ':' || ch === '/') {
        ghost += ch;
        lit += ch;
      } else if (LED_NATIVE.test(ch)) {
        ghost += '8';
        lit += ch;
      } else if (LED_MARKS.hasOwnProperty(ch)) {
        ghost += '8';
        lit += '<span class="led-ac led-ac-' + LED_MARKS[ch][1] + '">' + LED_MARKS[ch][0] + '</span>';
      } else {
        console.log('the LED board cannot set ' + JSON.stringify(ch));
        ghost += ' ';
        lit += ' ';
      }
    }
    return { ghost: ghost, lit: lit };
  }

  // Each cell keeps the widest text it has shown, so a figure growing a
  // digit widens its cell once instead of the board jumping every poll,
  // and a placeholder is as wide as the reading it stands for.
  var ledWidth = {};
  var ledPattern = {};
  var ledShown = {};
  var ledFitDirty = true;
  function padTo(s, w) {
    while (s.length < w) {
      s = ' ' + s;
    }
    return s;
  }
  // text: what to show, or null for a missing reading.  The placeholder
  // is the last reading's shape with every character a dash -- "--.-" for
  // a temperature, "--.---" for the barometer, "- ---" for the wind --
  // so nothing of the old reading, a wind direction least of all, stays
  // up looking current.
  function ledSet(id, text, color, tail) {
    var cell = document.getElementById(id);
    if (cell === null) {
      return;
    }
    var ok = text !== null && text !== undefined && text !== '';
    if (ok) {
      ledPattern[id] = String(text).replace(/[^ .:]/g, '-');
    } else {
      text = ledPattern[id] || cell.getAttribute('data-empty') || '--';
    }
    text = String(text);
    if (!ledWidth[id] || text.length > ledWidth[id]) {
      ledWidth[id] = text.length;
      ledFitDirty = true;
    }
    text = padTo(text, ledWidth[id]);
    var layers = ledLayers(text, ok);
    var html = '<span class="led-stk"><span class="led-g">' + layers.ghost
        + '</span><span class="led-v">' + layers.lit + '</span></span>'
        + (tail ? '<span class="led-t">' + tail + '</span>' : '');
    // Most polls change nothing; leave an unchanged cell alone rather
    // than rebuild it every couple of seconds.
    var n = cell.querySelector('.led-n');
    if (ledShown[id] !== html) {
      ledShown[id] = html;
      n.innerHTML = html;
    }
    n.style.color = color || '';
  }

  // THE FIT.  Every size on the board is set in rem for a 16:10 tablet;
  // each ROW then scales its digits and labels together by its own --fit,
  // the largest factor (never above 1, in steps of 0.01) at which every
  // panel in it still holds its cells, across and down.  Per row, so a
  // long label at the bottom of the board does not shrink the
  // temperatures at the top.  Run when a cell widens and when the window
  // changes.
  //
  // What a panel needs does not scale in exact proportion -- its gaps and
  // padding stay put, and the row's panels share its width by what they
  // hold -- so the estimate can land a step either side of the answer,
  // and a row whose estimate overflows would simply alternate between the
  // two.  So: estimate a few times, then step down until nothing
  // overflows.
  function ledRowNeed(row) {
    // How many times over the row's fullest panel is filled: 1 or less
    // fits.  The cells only; a panel's hidden heading is positioned out of
    // the flow and takes no gap.
    var need = 0;
    var panels = row.querySelectorAll('.led-panel');
    for (var i = 0; i < panels.length; i++) {
      var p = panels[i];
      var cs = getComputedStyle(p);
      var innerW = p.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
      var innerH = p.clientHeight - parseFloat(cs.paddingTop) - parseFloat(cs.paddingBottom);
      var cells = p.querySelectorAll('.led-c'), w = 0, h = 0;
      for (var k = 0; k < cells.length; k++) {
        var r = cells[k].getBoundingClientRect();
        w += r.width;
        h = Math.max(h, r.height);
      }
      // A browser that reports the gap as "normal" (no flex gap) has none:
      // NaN here would stop the fit for good.
      w += Math.max(0, cells.length - 1) * (parseFloat(cs.columnGap) || 0);
      if (innerW > 0) { need = Math.max(need, w / innerW); }
      if (innerH > 0) { need = Math.max(need, h / innerH); }
    }
    return need;
  }
  function ledFit() {
    var rows = document.querySelectorAll('.led-row');
    for (var ri = 0; ri < rows.length; ri++) {
      var row = rows[ri];
      var fit = Number(row.style.getPropertyValue('--fit')) || 1;
      for (var pass = 0; pass < 4; pass++) {
        var need = ledRowNeed(row);
        if (!(need > 0)) {
          break;
        }
        var next = Math.min(1, Math.floor(fit / need * 100) / 100);
        if (next === fit) {
          break;
        }
        fit = next;
        row.style.setProperty('--fit', String(fit));
      }
      while (fit > 0.3 && ledRowNeed(row) > 1.001) {
        fit = Math.round(fit * 100 - 1) / 100;
        row.style.setProperty('--fit', String(fit));
      }
    }
  }
  window.addEventListener('resize', function () { ledFitDirty = true; repaint(); });

  // Where the LCD font's baseline falls in a box of the board's line
  // height, as a fraction of the font size: the middle-segment clip and
  // the accents are placed from it (--led-bl).  Measured once the font has
  // loaded, since it depends on the font's own metrics.  A browser
  // without document.fonts measures at window load instead, which waits
  // for the web fonts the page is using.  Until then it measures every two
  // seconds, for up to a minute: an analytics script that never finishes
  // loading holds window load back for good, and the font can arrive at
  // any point before that.  Left unmeasured, every dash and accent would
  // sit where a guess put it.  Measuring again changes nothing once it is
  // right.
  function ledBaseline() {
    var probe = document.createElement('span');
    probe.className = 'led-probe';
    probe.appendChild(document.createTextNode('8'));
    var mark = document.createElement('span');
    mark.className = 'led-probe-mark';
    probe.appendChild(mark);
    document.body.appendChild(probe);
    var bl = mark.offsetTop / 100;
    probe.parentNode.removeChild(probe);
    if (bl > 0) {
      document.documentElement.style.setProperty('--led-bl', bl + 'em');
    }
    ledFitDirty = true;
    repaint();
  }
  if (document.fonts && document.fonts.load) {
    document.fonts.load('100px LCD').then(ledBaseline);
  } else {
    var ledTries = 0;
    var ledPoll = setInterval(function () {
      ledBaseline();
      if (++ledTries >= 30) {
        clearInterval(ledPoll);
      }
    }, 2000);
    window.addEventListener('load', function () {
      clearInterval(ledPoll);
      ledBaseline();
    });
  }

  function has(r, key) {
    return r.hasOwnProperty(key) && r[key] !== null && r[key] !== '';
  }
  // The wind cell: the speed, and beside it the direction, "4 NNE".  Calm
  // by the speed as shown: a raw 0.00009 is not zero, but it shows as 0,
  // and a direction beside a 0 claims a wind there is not.
  function ledWind(id, r, speed) {
    var dir = '   ';
    if (speed !== null && Number(speed) !== 0 && has(r, 'current.windDir.ordinal_compass')) {
      dir = (String(r['current.windDir.ordinal_compass']) + '   ').slice(0, 3);
    }
    ledSet(id, speed === null ? null : padTo(speed, 2) + ' ' + dir);
  }
  // The barometer, with the trend arrow beside it while the data is fresh.
  function ledBarometer(id, r, fresh, value) {
    ledSet(id, value, null,
           fresh && trendCode(r) !== null ? trendSvg(trendCode(r), 'led-trend') : '');
  }
  // The outdoor air quality index, in its level's color.
  function ledAqi(id, r, value) {
    ledSet(id, value, value !== null && has(r, 'current.pm2_5_aqi_color.raw')
           ? decodeRgb(r['current.pm2_5_aqi_color.raw']) : null);
  }
  // The clock panel, which is the status line, and then the fit: the last
  // thing every painter does, once its cells have their widths.
  function ledStatus(status) {
    document.getElementById('led-clock').className = 'led-panel led-status-' + status.kind;
    ledSet('led-clk', status.text);
    if (ledFitDirty) {
      ledFitDirty = false;
      ledFit();
    }
  }
</script>
