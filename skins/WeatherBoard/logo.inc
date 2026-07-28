## Copyright 2026 by John A Kline (john@johnkline.com)
## Distributed under the terms of the GNU Public License (GPLv3)
## See LICENSE for your rights.
#errorCatcher Echo
#encoding UTF-8
##
## The PaloAltoWeather.com live logo: El Palo Alto under the real Palo
## Alto sky, shared with weewx-liveseasons (introduced there in skin 7.9;
## this is the mark only, without the wordmark lockup).  Static SVG
## markup here (ids pl-*); all dynamic rendering lives in paw_logo.js.
## The pawLogoInit call below paints the report-time sky, so the logo is
## right as soon as the page loads; updater_common.inc keeps it live by
## calling pawLogoFromLoop(result) on every successful poll of the loop
## data file.  Ambient motion (cloud drift, sun rays, star twinkle,
## falling rain) is CSS in weatherboard.css (paw-* keyframes; the
## per-drop rain delays live there too, this skin allows no inline
## styles).
##
## The tree path is generated art: the El Palo Alto silhouette extracted
## from the City of Palo Alto logo (public domain, via Wikimedia
## Commons).  Regenerate it from the Commons SVG rather than editing
## coordinates by hand.
<svg id="paw-logo" class="title-logo" width="100" height="100" viewBox="0 0 120 120" aria-hidden="true">
  <defs>
    <linearGradient id="pl-sky" x1="0" y1="0" x2="0" y2="1">
      <stop id="pl-sky-top" offset="0" stop-color="#2f80c3"/>
      <stop id="pl-sky-bot" offset="1" stop-color="#a9d8f2"/>
    </linearGradient>
    <clipPath id="pl-clip"><rect x="4" y="4" width="112" height="112" rx="20"/></clipPath>
  </defs>
  <g clip-path="url(#pl-clip)">
    <rect width="120" height="120" fill="url(#pl-sky)"/>
    <g id="pl-stars" opacity="0">
      <circle class="pl-star pl-t1" cx="22" cy="26" r="1.3" fill="#e8f0fa"/>
      <circle class="pl-star pl-t2" cx="35" cy="15" r="0.9" fill="#e8f0fa"/>
      <circle class="pl-star pl-t3" cx="48" cy="30" r="1.3" fill="#e8f0fa"/>
      <circle class="pl-star pl-t1" cx="60" cy="12" r="0.9" fill="#e8f0fa"/>
      <circle class="pl-star pl-t2" cx="74" cy="22" r="1.3" fill="#e8f0fa"/>
      <circle class="pl-star pl-t3" cx="88" cy="32" r="0.9" fill="#e8f0fa"/>
      <circle class="pl-star pl-t1" cx="97" cy="18" r="1.3" fill="#e8f0fa"/>
      <circle class="pl-star pl-t2" cx="30" cy="44" r="0.9" fill="#e8f0fa"/>
      <circle class="pl-star pl-t3" cx="80" cy="46" r="1.3" fill="#e8f0fa"/>
      <circle class="pl-star pl-t1" cx="52" cy="45" r="0.9" fill="#e8f0fa"/>
      <circle class="pl-star pl-t2" cx="16" cy="52" r="1.3" fill="#e8f0fa"/>
      <circle class="pl-star pl-t3" cx="102" cy="42" r="0.9" fill="#e8f0fa"/>
    </g>
    <g id="pl-moon" opacity="0">
      <circle id="pl-moon-disc" r="7.5" fill="#31435f"/>
      <path id="pl-moon-lit" d="M 0 -7.5 A 7.5 7.5 0 0 1 0 7.5 A 7.5 7.5 0 0 1 0 -7.5 Z" fill="#f4ecd8"/>
    </g>
    <g id="pl-sun" opacity="0">
      <g class="pl-rays">
        <line x1="0" y1="-11" x2="0" y2="-14.5" stroke="#ffd54f" stroke-width="1.6" stroke-linecap="round"/>
        <line x1="11" y1="0" x2="14.5" y2="0" stroke="#ffd54f" stroke-width="1.6" stroke-linecap="round"/>
        <line x1="0" y1="11" x2="0" y2="14.5" stroke="#ffd54f" stroke-width="1.6" stroke-linecap="round"/>
        <line x1="-11" y1="0" x2="-14.5" y2="0" stroke="#ffd54f" stroke-width="1.6" stroke-linecap="round"/>
        <line x1="7.8" y1="-7.8" x2="10.3" y2="-10.3" stroke="#ffd54f" stroke-width="1.6" stroke-linecap="round"/>
        <line x1="7.8" y1="7.8" x2="10.3" y2="10.3" stroke="#ffd54f" stroke-width="1.6" stroke-linecap="round"/>
        <line x1="-7.8" y1="7.8" x2="-10.3" y2="10.3" stroke="#ffd54f" stroke-width="1.6" stroke-linecap="round"/>
        <line x1="-7.8" y1="-7.8" x2="-10.3" y2="-10.3" stroke="#ffd54f" stroke-width="1.6" stroke-linecap="round"/>
      </g>
      <circle id="pl-sun-disc" r="7.5" fill="#ffd54f"/>
    </g>
    <rect id="pl-ovc" width="120" height="120" fill="#8fa3b3" opacity="0"/>
    <g id="pl-cloud1" class="pl-cloud-a" opacity="0.4">
      <ellipse cx="-20" cy="34" rx="14" ry="6" fill="#ffffff"/>
      <ellipse cx="-31" cy="37" rx="10" ry="5" fill="#ffffff"/>
      <ellipse cx="-10" cy="37" rx="9" ry="4.6" fill="#ffffff"/>
    </g>
    <g id="pl-cloud2" class="pl-cloud-b" opacity="0.3">
      <ellipse cx="20" cy="50" rx="11" ry="4.6" fill="#ffffff"/>
      <ellipse cx="29" cy="52.5" rx="8" ry="3.8" fill="#ffffff"/>
    </g>
    <g id="pl-rain" opacity="0">
      <line class="pl-drop" x1="14" y1="18" x2="11" y2="30" stroke="#dce9f4" stroke-width="1.6" stroke-linecap="round"/>
      <line class="pl-drop" x1="25" y1="32" x2="22" y2="44" stroke="#dce9f4" stroke-width="1.6" stroke-linecap="round"/>
      <line class="pl-drop" x1="36" y1="46" x2="33" y2="58" stroke="#dce9f4" stroke-width="1.6" stroke-linecap="round"/>
      <line class="pl-drop" x1="47" y1="18" x2="44" y2="30" stroke="#dce9f4" stroke-width="1.6" stroke-linecap="round"/>
      <line class="pl-drop" x1="58" y1="32" x2="55" y2="44" stroke="#dce9f4" stroke-width="1.6" stroke-linecap="round"/>
      <line class="pl-drop" x1="69" y1="46" x2="66" y2="58" stroke="#dce9f4" stroke-width="1.6" stroke-linecap="round"/>
      <line class="pl-drop" x1="80" y1="18" x2="77" y2="30" stroke="#dce9f4" stroke-width="1.6" stroke-linecap="round"/>
      <line class="pl-drop" x1="91" y1="32" x2="88" y2="44" stroke="#dce9f4" stroke-width="1.6" stroke-linecap="round"/>
      <line class="pl-drop" x1="102" y1="46" x2="99" y2="58" stroke="#dce9f4" stroke-width="1.6" stroke-linecap="round"/>
    </g>
    <path id="pl-ground" d="M0,90 Q60,80 120,90 L120,120 L0,120 Z" fill="#1d4534"/>
    <path id="pl-tree" fill-rule="evenodd" fill="#0e281c" d="M33.9,68.6L32.5,67.8L32.1,67.7L31.5,67.8L31.1,68.1L30.5,69.0L30.5,69.3L30.7,69.5L31.9,70.1L32.7,70.6L32.8,71.0L32.8,71.9L33.2,72.5L33.8,72.7L34.8,72.8L35.0,72.6L35.1,72.2L35.3,72.0L35.8,71.8L36.2,71.8L36.7,72.1L37.0,72.4L37.2,72.8L37.2,73.5L37.4,73.7L39.6,73.6L40.4,73.9L41.2,74.6L42.2,74.2L42.4,74.2L42.7,74.5L42.9,76.5L42.6,86.9L42.7,87.9L42.9,87.9L45.5,88.0L47.7,87.9L47.3,76.8L47.4,75.1L47.8,74.3L48.1,74.1L48.5,74.1L49.6,74.6L50.0,74.6L50.2,74.3L50.4,73.1L50.7,72.8L51.1,72.5L52.2,72.6L53.7,72.5L54.1,72.6L54.8,73.0L55.7,72.9L58.5,71.8L58.9,71.3L59.3,70.5L59.3,70.1L59.1,69.9L57.6,69.3L55.5,70.4L54.6,70.7L54.1,70.7L54.3,69.9L55.7,69.3L56.6,68.6L57.0,67.8L57.2,66.9L56.8,65.7L56.7,65.6L56.3,65.7L55.4,65.2L54.5,64.6L53.9,63.8L55.9,63.6L57.6,63.1L59.0,63.2L59.3,63.0L59.5,62.7L59.4,62.3L58.5,61.4L58.7,60.5L58.6,60.1L58.0,59.6L56.2,58.6L55.2,58.4L54.6,58.0L54.0,57.3L53.6,56.7L53.6,56.2L54.0,55.9L55.2,55.8L55.1,55.4L54.8,54.9L52.3,53.7L52.0,53.4L51.8,52.6L48.9,52.6L48.5,52.4L48.3,52.0L48.3,51.5L48.6,51.1L49.1,50.9L51.3,50.6L51.9,50.3L53.0,49.3L54.3,48.7L54.7,48.4L54.3,48.2L53.5,48.0L52.7,48.0L51.4,48.3L49.1,47.9L48.6,47.1L50.4,46.6L50.7,46.3L50.8,45.7L50.8,45.6L48.2,45.0L48.1,44.8L48.7,44.4L48.7,44.6L49.3,44.8L50.9,44.8L52.4,44.6L53.6,44.2L54.0,43.9L54.3,43.3L54.2,42.8L53.9,41.9L53.9,41.5L54.2,41.1L55.1,40.6L53.3,39.4L52.6,39.1L51.4,38.9L49.4,39.2L47.8,38.5L47.5,38.3L47.6,37.7L47.9,37.4L48.5,37.5L49.5,37.8L51.3,37.1L51.5,36.6L52.2,36.7L52.5,36.2L53.6,35.4L53.7,35.1L53.6,34.8L53.1,34.7L49.1,34.5L48.6,34.3L48.7,33.9L50.8,32.3L51.0,31.9L50.5,31.6L48.2,30.9L48.1,30.2L47.9,30.0L46.7,29.7L46.3,29.5L46.3,29.1L46.6,28.7L47.5,28.4L47.1,27.7L46.4,26.9L46.3,26.6L46.4,26.2L46.8,25.8L47.9,25.6L48.1,25.4L47.5,24.7L47.4,24.3L46.2,24.2L45.8,23.9L45.8,23.5L46.6,22.1L46.5,22.0L44.4,22.0L44.2,23.3L43.8,24.1L43.3,24.5L42.6,24.8L42.4,25.0L42.5,25.6L43.2,25.7L43.3,25.9L43.7,29.6L43.5,30.4L43.1,31.6L43.1,32.1L43.5,32.7L43.4,32.9L43.2,33.1L42.3,33.6L42.0,33.9L42.1,34.2L42.7,34.7L42.9,35.1L42.6,35.4L41.9,35.6L42.3,36.0L43.3,36.6L43.6,37.0L43.6,37.4L43.3,37.6L38.9,38.7L38.5,39.1L38.2,39.7L37.4,40.2L37.1,40.7L37.1,41.0L37.2,41.4L38.0,42.2L37.2,43.9L37.3,44.2L37.8,44.4L38.7,44.4L39.5,44.1L40.4,43.6L40.4,44.3L40.1,45.3L39.0,45.6L38.8,45.7L38.8,45.9L40.9,48.2L41.2,48.4L41.6,48.4L41.6,48.5L40.7,48.9L37.4,49.5L36.5,49.8L36.2,50.0L36.2,50.3L36.6,50.6L38.1,50.8L38.6,51.2L38.6,51.5L38.5,51.7L37.0,53.1L36.8,53.6L36.8,54.1L36.9,54.3L37.5,54.5L37.7,54.7L37.4,55.5L37.5,55.8L38.2,56.2L39.7,56.9L39.8,57.2L39.5,57.5L39.0,57.6L36.9,57.2L36.0,56.9L35.6,56.9L34.0,57.2L33.6,57.4L33.5,57.6L33.7,57.8L35.0,58.7L35.1,60.3L36.5,60.8L37.8,60.8L38.5,61.0L39.5,61.7L39.7,62.3L39.6,62.7L39.2,63.0L35.5,63.5L34.6,63.8L33.9,64.3L33.7,64.7L33.6,65.2L33.6,65.7L33.9,66.1L34.2,66.2L34.5,66.1L35.3,65.4L35.7,65.3L36.4,65.7L36.6,66.1L36.7,66.5L36.5,67.2L36.0,67.8L35.5,68.1L34.3,68.2L33.9,68.6ZM40.3,57.4L40.8,56.1L40.9,56.0L42.1,55.8L42.5,55.9L42.6,56.1L42.7,56.4L42.6,56.7L42.0,57.3L41.0,57.6L40.6,57.6L40.3,57.4ZM51.1,59.6L51.0,60.3L50.6,60.6L49.8,60.7L49.0,60.6L48.8,60.3L49.2,59.5L48.7,58.9L48.7,58.5L49.5,57.7L49.9,57.7L50.2,57.7L50.5,58.0L50.8,58.5L51.1,59.6ZM55.1,59.6L55.1,60.6L55.0,60.9L54.7,61.0L52.9,60.5L52.6,60.3L52.5,60.0L52.5,59.5L52.8,59.3L55.1,59.6ZM41.9,62.1L40.9,61.5L40.8,61.2L41.0,60.9L41.7,60.8L42.3,61.0L42.3,61.5L41.9,62.1ZM49.9,62.6L49.7,62.9L49.0,63.6L48.5,64.5L48.2,64.4L47.7,64.1L47.3,63.4L47.2,62.9L47.4,62.4L47.7,62.0L48.3,61.8L48.9,61.7L49.4,61.8L49.8,62.1L49.9,62.6ZM42.6,66.0L41.7,65.8L40.9,65.3L40.8,64.6L41.1,64.0L41.6,63.8L42.0,63.8L43.1,64.2L43.5,64.5L43.7,65.0L43.5,65.6L43.2,65.9L42.6,66.0ZM52.4,68.2L51.4,69.0L50.1,69.0L49.7,69.2L49.4,69.4L49.1,70.0L48.8,70.2L48.0,69.9L47.3,69.4L47.3,69.2L47.5,68.4L48.0,67.6L48.8,67.0L49.7,66.6L50.6,66.6L51.1,66.8L51.9,67.5L52.4,68.2ZM40.2,72.4L39.0,71.7L39.8,71.2L40.9,71.0L42.1,71.3L42.7,71.5L42.8,71.8L42.7,72.1L42.2,72.4L41.3,72.6L40.2,72.4ZM47.8,73.2L46.6,72.9L46.3,72.7L46.7,72.2L46.8,70.9L47.1,70.6L47.9,70.6L48.5,70.8L49.1,71.3L49.4,71.9L49.4,72.4L49.1,72.8L47.8,73.2Z"/>
  </g>
  <rect x="3.2" y="3.2" width="113.6" height="113.6" rx="20.8" fill="none" stroke="#ffffff" stroke-width="2.6"/>
</svg>
<script src="paw_logo.js"></script>
#set $pl_ws = $current.windSpeed.raw
#if $pl_ws is None
#set $pl_ws = 0
#end if
#set $pl_rr = $current.rainRate.raw
#if $pl_rr is None
#set $pl_rr = 0
#end if
#set $pl_hum = $current.outHumidity.raw
#if $pl_hum is None
#set $pl_hum = 50
#end if
#set $pl_wax = 1
#if $almanac.next_full_moon.raw >= $almanac.next_new_moon.raw
#set $pl_wax = 0
#end if
#set $pl_frac = $almanac.moon.phase / 100.0
<script>
  pawLogoInit({
    sunAlt: $almanac.sun.alt,
    sunAz: $almanac.sun.az,
    moonAlt: $almanac.moon.alt,
    moonAz: $almanac.moon.az,
    moonFrac: $pl_frac,
    moonWaxing: $pl_wax,
    wind: $pl_ws,
    rain: $pl_rr,
    humidity: $pl_hum
  });
</script>
