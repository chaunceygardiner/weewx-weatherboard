## Copyright (C)2020-2026 by John A Kline (john@johnkline.com)
## Distributed under the terms of the GNU Public License (GPLv3)
## See LICENSE for your rights.
##
## readout.inc -- how the readout board draws: its cells, its fit to the
## screen and the helpers a painter is built from.  It paints nothing
## itself.  The page's own painter follows it, index_painter.inc for
## index.html: the boardPaint(result, fresh, status) that board.inc calls
## after every poll and every failure, which sets each of the page's cells
## by id and ends with roStatus(status).
##
## THE LETTERING.  Every reading is set in League Gothic, a tall condensed
## face, so the figures stand tall in the width the panels have.  Its
## digits are not all the same width, so each digit sits in a box as wide
## as the widest (.ro-d): a figure does not shift as it changes, and a
## placeholder is exactly as wide as the reading it stands for.
##   - A missing digit, and a minus sign, is a minus sign in a digit's box.
##   - With no data the decimal point is dimmed.
#errorCatcher Echo
<script>
  // One cell's text as markup.  ok is false when the text is a
  // placeholder for missing data.  Digits, dashes and the spaces that pad
  // a figure out to its width take a digit's box; the rest (a wind
  // direction, the status words) are set as the font draws them.
  function roHtml(text, ok) {
    var html = '', lead = true;
    text = String(text).toUpperCase();
    for (var i = 0; i < text.length; i++) {
      var ch = text[i];
      if (ch !== ' ') {
        lead = false;
      }
      if (/[0-9]/.test(ch)) {
        html += '<span class="ro-d">' + ch + '</span>';
      } else if (ch === '-') {
        html += '<span class="ro-d">\u2212</span>';
      } else if (ch === ' ' && lead) {
        html += '<span class="ro-d"> </span>';
      } else if (ch === '.' && !ok) {
        html += '<span class="ro-dp-off">.</span>';
      } else if (ch === '&') {
        html += '&amp;';
      } else if (ch === '<') {
        html += '&lt;';
      } else {
        html += ch;
      }
    }
    return html;
  }

  // WIDTHS.  Each cell keeps two high-water marks, so it widens once and
  // never narrows, and nothing beside it shifts every poll:
  //   roWidth  the widest text it has shown, in characters.  Shorter text
  //            is padded on the left to it, so a figure stays right-aligned
  //            and a placeholder has the reading's shape.
  //   roEm     the widest it has been, in ems of its own size, in the fonts
  //            the page has now.  Held as the cell's min-width.  Letters
  //            are not all one width -- a wind direction of WSW is wider
  //            than NNE, in the same three characters -- so this, not the
  //            character count, is what says the cell grew.
  // Either one growing marks the fit dirty (roFitDirty).  roSet only
  // writes; roStatus, at the end of the paint, measures every cell in one
  // pass of reads (roMeasure) and then runs the fit, so a paint costs the
  // browser one layout however many cells changed.  When the figures' font
  // arrives every roEm is dropped, since a width measured in a fallback
  // means nothing in the real font, and that paint measures each cell
  // again.
  var roWidth = {};
  var roEm = {};
  var roPattern = {};
  var roShown = {};
  var roFitDirty = true;
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
  function roSet(id, text, color, tail) {
    var cell = document.getElementById(id);
    if (cell === null) {
      return;
    }
    var ok = text !== null && text !== undefined && text !== '';
    if (ok) {
      roPattern[id] = String(text).replace(/[^ .:]/g, '-');
    } else {
      text = roPattern[id] || cell.getAttribute('data-empty') || '--';
    }
    text = String(text);
    if (!roWidth[id] || text.length > roWidth[id]) {
      roWidth[id] = text.length;
      roFitDirty = true;
    }
    text = padTo(text, roWidth[id]);
    var html = '<span class="ro-v">' + roHtml(text, ok) + '</span>'
        + (tail ? '<span class="ro-t">' + tail + '</span>' : '');
    // Most polls change nothing; leave an unchanged cell alone rather
    // than rebuild it every couple of seconds.
    var n = cell.querySelector('.ro-n');
    if (roShown[id] !== html) {
      roShown[id] = html;
      n.innerHTML = html;
    }
    n.style.color = color || '';
  }
  // Every cell's width against its roEm: all the reads first, then the
  // writes, so the browser lays the page out once.
  function roMeasure() {
    var cells = document.querySelectorAll('.ro-c'), grown = [];
    for (var i = 0; i < cells.length; i++) {
      var n = cells[i].querySelector('.ro-n');
      var size = parseFloat(getComputedStyle(n).fontSize);
      var em = size > 0 ? n.getBoundingClientRect().width / size : 0;
      if (em > (roEm[cells[i].id] || 0) + 0.001) {
        grown.push([cells[i].id, n, em]);
      }
    }
    for (var k = 0; k < grown.length; k++) {
      roEm[grown[k][0]] = grown[k][2];
      grown[k][1].style.minWidth = grown[k][2] + 'em';
      roFitDirty = true;
    }
  }

  // THE FIT.  Every size on the board is set in rem for a 16:10 tablet;
  // each ROW then scales its figures and labels together by its own
  // --fit, the largest factor (never above 1, in steps of 0.01) at which
  // every panel in it still holds its cells, across and down.  Per row, so
  // a long label at the bottom of the board does not shrink the
  // temperatures at the top.  Run when a cell widens, when the window
  // changes and when a font arrives.
  //
  // What a panel needs does not scale in exact proportion -- its gaps and
  // padding stay put, and the row's panels share its width by what they
  // hold -- so the estimate can land a step either side of the answer,
  // and a row whose estimate overflows would simply alternate between the
  // two.  So: estimate a few times, step down until nothing overflows, then
  // step up while the next step still fits.  The answer is then the
  // largest step that fits, whatever the estimates did on the way -- so a
  // board fitted first in a fallback font ends where one that had its
  // fonts from the start does.
  function roRowNeed(row) {
    // How many times over the row's fullest panel is filled: 1 or less
    // fits.  The cells only; a panel's hidden heading is positioned out of
    // the flow and takes no gap.
    var need = 0;
    var panels = row.querySelectorAll('.ro-panel');
    for (var i = 0; i < panels.length; i++) {
      var p = panels[i];
      var cs = getComputedStyle(p);
      var innerW = p.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
      var innerH = p.clientHeight - parseFloat(cs.paddingTop) - parseFloat(cs.paddingBottom);
      var cells = p.querySelectorAll('.ro-c'), w = 0, h = 0;
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
  function roFit() {
    var rows = document.querySelectorAll('.ro-row');
    for (var ri = 0; ri < rows.length; ri++) {
      var row = rows[ri];
      var fit = Number(row.style.getPropertyValue('--fit')) || 1;
      for (var pass = 0; pass < 4; pass++) {
        var need = roRowNeed(row);
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
      while (fit > 0.3 && roRowNeed(row) > 1.001) {
        fit = Math.round(fit * 100 - 1) / 100;
        row.style.setProperty('--fit', String(fit));
      }
      while (fit < 1) {
        var up = Math.round(fit * 100 + 1) / 100;
        row.style.setProperty('--fit', String(up));
        if (roRowNeed(row) > 1.001) {
          row.style.setProperty('--fit', String(fit));
          break;
        }
        fit = up;
      }
    }
  }
  window.addEventListener('resize', function () { roFitDirty = true; repaint(); });

  // The fit measures the board in its fonts -- League Gothic for the
  // readings, Jost for the labels -- and a first paint made before they
  // arrive is measured in a fallback, which runs wider.  So the board
  // fits again as each one loads, and when it is the figures' font
  // (figures true) measures every cell afresh.  A browser without
  // document.fonts fits again at window load instead, which waits for the
  // web fonts the page is using.  Until then it fits again every two
  // seconds, for up to a minute: an analytics script that never finishes
  // loading holds window load back for good, and the fonts can arrive at
  // any point before that.  It cannot be told when the figures' font
  // arrives, so it sets a line of figures in their font stack each time
  // (roProbe) and takes a change in its width for the arrival.  Fitting
  // again changes nothing once the fonts are in.
  function roFontReady(figures) {
    if (figures) {
      for (var id in roEm) {
        if (roEm.hasOwnProperty(id) && document.getElementById(id) !== null) {
          document.getElementById(id).querySelector('.ro-n').style.minWidth = '';
        }
      }
      roEm = {};
    }
    roFitDirty = true;
    repaint();
  }
  if (document.fonts && document.fonts.load) {
    document.fonts.load('100px "League Gothic"').then(function () { roFontReady(true); });
    document.fonts.load('500 100px Jost').then(function () { roFontReady(false); });
  } else {
    var roProbe = function () {
      var probe = document.createElement('span');
      probe.className = 'ro-probe';
      probe.appendChild(document.createTextNode('0123456789 NESW'));
      document.body.appendChild(probe);
      var w = probe.offsetWidth;
      probe.parentNode.removeChild(probe);
      return w;
    };
    var roProbed = roProbe();
    var roRefit = function () {
      var w = roProbe();
      roFontReady(w !== roProbed);
      roProbed = w;
    };
    var roTries = 0;
    var roPoll = setInterval(function () {
      roRefit();
      if (++roTries >= 30) {
        clearInterval(roPoll);
      }
    }, 2000);
    window.addEventListener('load', function () {
      clearInterval(roPoll);
      roRefit();
    });
  }

  function has(r, key) {
    return r.hasOwnProperty(key) && r[key] !== null && r[key] !== '';
  }
  // The wind cell: the speed, and beside it the direction, "4 NNE".  Calm
  // by the speed as shown: a raw 0.00009 is not zero, but it shows as 0,
  // and a direction beside a 0 claims a wind there is not.
  function roWind(id, r, speed) {
    var dir = '   ';
    if (speed !== null && Number(speed) !== 0 && has(r, 'current.windDir.ordinal_compass')) {
      dir = (String(r['current.windDir.ordinal_compass']) + '   ').slice(0, 3);
    }
    roSet(id, speed === null ? null : padTo(speed, 2) + ' ' + dir);
  }
  // The barometer, with the trend arrow beside it while the data is fresh.
  function roBarometer(id, r, fresh, value) {
    roSet(id, value, null,
          fresh && trendCode(r) !== null ? trendSvg(trendCode(r), 'ro-trend') : '');
  }
  // The outdoor air quality index, in its level's color.
  function roAqi(id, r, value) {
    roSet(id, value, value !== null && has(r, 'current.pm2_5_aqi_color.raw')
          ? decodeRgb(r['current.pm2_5_aqi_color.raw']) : null);
  }
  // The clock panel, which is the status line, and then the fit: the last
  // thing every painter does, once its cells have their widths.
  function roStatus(status) {
    document.getElementById('ro-clock').className = 'ro-panel ro-status-' + status.kind;
    roSet('ro-clk', status.text);
    roMeasure();
    if (roFitDirty) {
      roFitDirty = false;
      roFit();
    }
  }
</script>
