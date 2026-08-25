/*
 * Copyright 2026 by John A Kline
 * See LICENSE.txt for your rights
 *
 * The live logo: El Palo Alto under the real Palo Alto sky, shared with
 * weewx-liveseasons (introduced there in skin 7.9) -- keep the two
 * copies in sync.  Static markup lives in logo.inc (ids pl-*); this
 * file owns all dynamic rendering.  logo.inc calls pawLogoInit with
 * report-time values, so the sky is correct as soon as the page loads;
 * updater_common.inc keeps it live by calling pawLogoFromLoop(result)
 * on every successful poll of the loop data file.  Both merge partial
 * state -- a missing field leaves the previous value, so loop data
 * without a key never blanks the sky.  Ambient motion (drifting clouds,
 * sun rays, star twinkle, falling rain) is pure CSS in
 * weatherboard.css; this file only sets positions, colors, and
 * opacities.
 */

'use strict';

var pawLogo = (function() {
  var state = {
    sunAlt: 45, sunAz: 200, moonAlt: -40, moonAz: 100,
    moonFrac: 0.5, moonWaxing: true, wind: 4, rain: 0, humidity: 50
  };
  var cloudDur = 0;

  function clamp(v, lo, hi) { return v < lo ? lo : (v > hi ? hi : v); }
  function lerp(a, b, t) { return a + (b - a) * t; }
  function hex2rgb(h) {
    return [parseInt(h.slice(1, 3), 16), parseInt(h.slice(3, 5), 16),
            parseInt(h.slice(5, 7), 16)];
  }
  function mix(c1, c2, t) {
    var a = hex2rgb(c1), b = hex2rgb(c2);
    return 'rgb(' + Math.round(lerp(a[0], b[0], t)) + ',' +
           Math.round(lerp(a[1], b[1], t)) + ',' +
           Math.round(lerp(a[2], b[2], t)) + ')';
  }
  // piecewise color ramp: [[key, color], ...] sorted by key
  function ramp(stops, v) {
    if (v <= stops[0][0]) {
      return stops[0][1];
    }
    var i;
    for (i = 1; i < stops.length; i++) {
      if (v <= stops[i][0]) {
        return mix(stops[i - 1][1], stops[i][1],
                   (v - stops[i - 1][0]) / (stops[i][0] - stops[i - 1][0]));
      }
    }
    return stops[stops.length - 1][1];
  }

  // sky gradient keyed on sun altitude: night, dusk, sunset, golden, day
  var SKY_TOP = [[-18, '#0a1830'], [-8, '#101f38'], [-3, '#1c3352'],
                 [0, '#3c6ea5'], [8, '#4f93cc'], [25, '#2f80c3'], [90, '#2a79c0']];
  var SKY_BOT = [[-18, '#16304e'], [-8, '#3a3a63'], [-3, '#b3597a'],
                 [0, '#f08c42'], [8, '#ffcf87'], [25, '#a9d8f2'], [90, '#b7ddf5']];

  // map az/alt to a spot inside the disc (horizon is at about y=84)
  function skyXY(az, alt) {
    return [14 + clamp((az - 70) / 220, 0, 1) * 92,
            84 - clamp(alt, -8, 90) / 90 * 58];
  }

  // lit-side moon path around (0,0): f = illuminated fraction,
  // waxing = lit on the right (northern hemisphere)
  function moonPath(f, waxing) {
    f = clamp(f, 0.02, 0.98);
    var r = 7.5;
    var rx = (r * Math.abs(2 * f - 1)).toFixed(2);
    var s1 = waxing ? 1 : 0;
    var s2 = (f > 0.5) ? s1 : 1 - s1;
    return 'M 0 ' + (-r) + ' A ' + r + ' ' + r + ' 0 0 ' + s1 + ' 0 ' + r +
           ' A ' + rx + ' ' + r + ' 0 0 ' + s2 + ' 0 ' + (-r) + ' Z';
  }

  function setNum(key, v) {
    if (typeof v === 'number' && isFinite(v)) {
      state[key] = v;
    }
  }

  function render() {
    if (document.getElementById('paw-logo') === null) {
      return;
    }
    var s = state;
    var clouds = s.rain > 0.005 ? 1
               : (s.humidity > 85 ? 0.6 : (s.humidity > 70 ? 0.35 : 0.15));
    var daylight = clamp((s.sunAlt + 8) / 16, 0, 1);
    var el;

    document.getElementById('pl-sky-top').setAttribute('stop-color', ramp(SKY_TOP, s.sunAlt));
    document.getElementById('pl-sky-bot').setAttribute('stop-color', ramp(SKY_BOT, s.sunAlt));

    var sxy = skyXY(s.sunAz, s.sunAlt);
    el = document.getElementById('pl-sun');
    el.setAttribute('transform', 'translate(' + sxy[0].toFixed(1) + ',' + sxy[1].toFixed(1) + ')');
    el.setAttribute('opacity', s.sunAlt > -2
        ? (clamp((s.sunAlt + 2) / 4, 0, 1) * (1 - clouds * 0.55)).toFixed(2) : 0);
    document.getElementById('pl-sun-disc').setAttribute('fill',
        ramp([[0, '#ff9c3f'], [15, '#ffd54f']], s.sunAlt));

    var showMoon = s.moonAlt > 0 && s.sunAlt < 4;
    el = document.getElementById('pl-moon');
    el.setAttribute('opacity', showMoon ? clamp((4 - s.sunAlt) / 8, 0, 1).toFixed(2) : 0);
    if (showMoon) {
      var mxy = skyXY(s.moonAz, s.moonAlt);
      el.setAttribute('transform', 'translate(' + mxy[0].toFixed(1) + ',' + mxy[1].toFixed(1) + ')');
      document.getElementById('pl-moon-lit').setAttribute('d', moonPath(s.moonFrac, s.moonWaxing));
    }

    document.getElementById('pl-stars').setAttribute('opacity',
        clamp((-4 - s.sunAlt) / 8, 0, 1).toFixed(2));
    document.getElementById('pl-ovc').setAttribute('opacity', (clouds * 0.45).toFixed(2));

    // changing animation-duration restarts the drift, so only follow real
    // wind shifts, not 2-second jitter
    var dur = Math.max(7, 90 - s.wind * 2.8);
    if (Math.abs(dur - cloudDur) > cloudDur * 0.15) {
      cloudDur = dur;
      document.getElementById('pl-cloud1').style.animationDuration = dur + 's';
      document.getElementById('pl-cloud2').style.animationDuration = (dur * 1.5) + 's';
    }
    document.getElementById('pl-cloud1').setAttribute('opacity', (0.25 + clouds * 0.6).toFixed(2));
    document.getElementById('pl-cloud2').setAttribute('opacity', (0.15 + clouds * 0.5).toFixed(2));

    document.getElementById('pl-rain').setAttribute('opacity',
        s.rain > 0.005 ? clamp(0.4 + s.rain, 0, 1).toFixed(2) : 0);

    document.getElementById('pl-ground').setAttribute('fill', mix('#0a1a12', '#1d4534', daylight));
    document.getElementById('pl-tree').setAttribute('fill', mix('#05100a', '#0e281c', daylight));
  }

  return {
    init: function(vals) {
      setNum('sunAlt', vals.sunAlt);
      setNum('sunAz', vals.sunAz);
      setNum('moonAlt', vals.moonAlt);
      setNum('moonAz', vals.moonAz);
      setNum('moonFrac', vals.moonFrac);
      setNum('wind', vals.wind);
      setNum('rain', vals.rain);
      setNum('humidity', vals.humidity);
      if (vals.moonWaxing !== undefined) {
        state.moonWaxing = !!vals.moonWaxing;
      }
      render();
    },
    fromLoop: function(r) {
      setNum('sunAlt', r['almanac.sun.alt']);
      setNum('sunAz', r['almanac.sun.az']);
      setNum('moonAlt', r['almanac.moon.alt']);
      setNum('moonAz', r['almanac.moon.az']);
      if (typeof r['almanac.moon.phase'] === 'number') {
        state.moonFrac = clamp(r['almanac.moon.phase'] / 100, 0, 1);
      }
      // Waxing iff the next full moon precedes the next new moon (exact,
      // same rule as the Sun & Moon widget); phase-index fallback.
      var nf = r['almanac.next_full_moon.unix_epoch.raw'],
          nn = r['almanac.next_new_moon.unix_epoch.raw'];
      if (typeof nf === 'number' && typeof nn === 'number') {
        state.moonWaxing = nf < nn;
      } else if (typeof r['almanac.moon_index'] === 'number') {
        state.moonWaxing = r['almanac.moon_index'] <= 3;
      }
      setNum('wind', r['current.windSpeed.raw']);
      setNum('rain', r['current.rainRate.raw']);
      setNum('humidity', r['current.outHumidity.raw']);
      render();
    }
  };
})();

function pawLogoInit(vals) {
  try {
    pawLogo.init(vals);
  } catch (e) {
    console.log(e);
  }
}

function pawLogoFromLoop(result) {
  try {
    pawLogo.fromLoop(result);
  } catch (e) {
    console.log(e);
  }
}
