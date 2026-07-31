/*
 * Copyright 2026 by John A Kline
 * See LICENSE for your rights.
 *
 * The mono title theme's logo repaint (Extras title_theme = mono).
 * logo.inc loads this file right after paw_logo.js for that theme only;
 * loading it is the opt-in.  It wraps pawLogoInit/pawLogoFromLoop and
 * repaints the logo pure red after every render: the scene logic
 * (sun/moon position, moon phase, cloud cover, rain, star fade) stays
 * paw_logo.js's own -- that file remains a verbatim copy of the
 * liveseasons renderer -- this wrapper only swaps the palette.
 * Polarity follows daylight: a light red panel with a dark drawing by
 * day, a dark panel with a bright drawing by night.  (A straight
 * luminance mapping can't keep daytime light: the sun and clouds are
 * lighter than the sky, so they could never come out darker than it.)
 */

'use strict';

(function() {
  var origInit = pawLogoInit;
  var origLoop = pawLogoFromLoop;
  var monoAlt = 45;

  function clamp(v, lo, hi) { return v < lo ? lo : (v > hi ? hi : v); }
  function lerp(a, b, t) { return a + (b - a) * t; }
  // piecewise ramp over sun altitude: [[key, value], ...] sorted by key
  function ramp(stops, v) {
    if (v <= stops[0][0]) {
      return stops[0][1];
    }
    for (var i = 1; i < stops.length; i++) {
      if (v <= stops[i][0]) {
        return lerp(stops[i - 1][1], stops[i][1],
                    (v - stops[i - 1][0]) / (stops[i][0] - stops[i - 1][0]));
      }
    }
    return stops[stops.length - 1][1];
  }
  function red(v) { return 'rgb(' + Math.round(clamp(v, 0, 255)) + ',0,0)'; }
  function setAll(sel, attr, val) {
    var els = document.querySelectorAll(sel);
    for (var i = 0; i < els.length; i++) {
      els[i].setAttribute(attr, val);
    }
  }

  function monoPaint() {
    if (document.getElementById('paw-logo') === null) {
      return;
    }
    // Panel brightness follows the sun; the drawing takes the opposite
    // polarity, smoothstepped so the flip is quick around dawn/dusk
    // (the two inevitably meet for a moment right at dusk).
    var panel = ramp([[-18, 34], [-6, 44], [-2, 80], [0, 140], [4, 205],
                      [10, 242], [25, 255]], monoAlt);
    var u = clamp((panel - 120) / 70, 0, 1);
    u = u * u * (3 - 2 * u);
    var mark = lerp(228, 55, u);
    var ground = lerp(panel, mark, 0.45);

    document.getElementById('pl-sky-top').setAttribute('stop-color', red(panel * 0.78));
    document.getElementById('pl-sky-bot').setAttribute('stop-color', red(panel));
    document.getElementById('pl-sun-disc').setAttribute('fill', red(mark));
    setAll('#pl-sun line', 'stroke', red(mark));
    document.getElementById('pl-moon-disc').setAttribute('fill', red(lerp(panel, mark, 0.25)));
    document.getElementById('pl-moon-lit').setAttribute('fill', red(mark));
    setAll('#pl-stars circle', 'fill', red(mark));
    setAll('#pl-cloud1 ellipse, #pl-cloud2 ellipse', 'fill', red(mark));
    setAll('#pl-rain line', 'stroke', red(mark));
    document.getElementById('pl-ovc').setAttribute('fill', red(Math.min(90, panel)));
    document.getElementById('pl-ground').setAttribute('fill', red(ground));
    document.getElementById('pl-tree').setAttribute('fill', red(mark));
    // the white border ring goes full red, matching the readings
    setAll('#paw-logo > rect', 'stroke', red(255));
  }

  pawLogoInit = function(vals) {
    origInit(vals);
    if (typeof vals.sunAlt === 'number' && isFinite(vals.sunAlt)) {
      monoAlt = vals.sunAlt;
    }
    try { monoPaint(); } catch (e) { console.log(e); }
  };

  pawLogoFromLoop = function(result) {
    origLoop(result);
    var alt = result['almanac.sun.alt'];
    if (typeof alt === 'number' && isFinite(alt)) {
      monoAlt = alt;
    }
    try { monoPaint(); } catch (e) { console.log(e); }
  };
})();
