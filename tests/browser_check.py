# Copyright (C)2026 by John A Kline <john@johnkline.com>
# Distributed under the terms of the GNU Public License (GPLv3)
# See LICENSE for your rights.
"""The two boards, run in a real browser.

check_templates.py proves the pages render; this proves they WORK.  Each
board is rendered the way check_templates.py renders it, loaded into
Chromium, and fed a loop-data.txt the test controls -- its readings, its
age (by the Date header, as a real server sends it), or a failure.  Nothing
reaches the network: the page, the skin's stylesheet and fonts, and the
loop data are all answered from here.

What it holds the boards to:

  - every reading shows what the loop data says, and the clock is the
    station's time in the language's 12 or 24 hour form
  - the status line: the data's age once it is max_age old (amber for the
    first minute, then red), the failure when a fetch fails (HTTP 404, BAD
    DATA, NO ENTRY, NO CONNECT), and EXPIRED TAP once the page expires --
    after which it fetches nothing until a tap starts it again; a page with
    the keep-alive password never expires
  - missing data: on the readout board every digit is a minus sign in the
    digit's own box, so a placeholder is exactly as wide as the reading it
    replaced, and the decimal point is dimmed -- the bar and the dimming
    measured in pixels against the digits that stood there; on the
    split-flap board, question marks with a blank flap for the decimal
    point
  - the readings are set in Bebas Neue, loaded from the skin, and the
    font has every character the status line and the wind directions use
    in every language
  - the split-flap lamps light for gusts, low and high pressure, rain, and
    the air quality level, and stay dark otherwise
  - both boards fit the screen -- every readout panel holds its cells, the
    split-flap board and its footer sit inside the window -- at 1280x800,
    1024x768, 1180x820 and 1366x1024, with metric readings and the widest
    language

Run with a Python that has Playwright, Cheetah and configobj, and
Chromium in Playwright's browser cache -- tools/pwenv, which is not
published:

  python3 -m venv tools/pwenv
  tools/pwenv/bin/pip install playwright CT3 configobj pillow weewx fonttools brotli   # playwright: match the browsers already cached
  tools/pwenv/bin/playwright install chromium
  PYTHONDONTWRITEBYTECODE=1 tools/pwenv/bin/python tests/browser_check.py
"""
import email.utils
import io
import json
import os
import sys
import time
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_templates as ct                              # noqa: E402
from playwright.sync_api import sync_playwright           # noqa: E402

SKIN = ct.SKIN
NOW = int(time.time())
SIZES = [(1280, 800), (1024, 768), (1180, 820), (1366, 1024)]
TYPES = {'css': 'text/css', 'ttf': 'font/ttf', 'woff2': 'font/woff2', 'ico': 'image/x-icon',
         'png': 'image/png'}


def entry(**over):
    """One report's entry in loop-data.txt, US units."""
    e = {'current.dateTime.raw': NOW, 'current.dateTime.format("%H:%M:%S")': '16:07:17',
         'current.outTemp.formatted': '78.4', 'current.dewpoint.formatted': '61.2',
         'current.appTemp.formatted': '79.9', 'current.outHumidity.formatted': '56',
         'day.outTemp.max.formatted': '81.0',
         'current.windSpeed.formatted': '4', 'current.windSpeed.raw': 4.0,
         'current.windDir.ordinal_compass': 'NNE',
         '10m.windGust.max.formatted': '9', '10m.windGust.max.raw': 9.0,
         'day.windGust.max.formatted': '14',
         'current.barometer.formatted': '29.912', 'current.barometer.raw': 29.912,
         'trend.barometer.code': -1,
         'day.rain.sum.formatted': '0.00', '24h.rain.sum.formatted': '0.00',
         'current.rainRate.formatted': '0.00', 'current.rainRate.raw': 0.0,
         'current.UV.formatted': '5.4', 'current.radiation.formatted': '612',
         'current.pm2_5_aqi.formatted': '42', 'current.pm2_5_aqi_color.raw': 0x00e400}
    e.update(over)
    return e


# The widest a US or metric station's readings run.
WIDE = entry(**{'current.outTemp.formatted': '-12.3', 'current.dewpoint.formatted': '-15.8',
                'current.appTemp.formatted': '-20.5', 'current.outHumidity.formatted': '100',
                'current.windSpeed.formatted': '112', 'current.windDir.ordinal_compass': 'ØNØ',
                '10m.windGust.max.formatted': '140', 'day.windGust.max.formatted': '152',
                'current.barometer.formatted': '1013.2', 'day.rain.sum.formatted': '123.4',
                '24h.rain.sum.formatted': '130.2', 'current.rainRate.formatted': '145.6',
                'current.UV.formatted': '11.8', 'current.radiation.formatted': '1012',
                'current.pm2_5_aqi.formatted': '158'})


# Wider than any real station sends: every reading two characters past its
# widest.  The fit is insurance -- real readings fit without it -- and this
# is the case that proves the insurance pays: without the fit, panels
# overflow.
EXTREME = entry(**{'current.outTemp.formatted': '-112.34', 'current.dewpoint.formatted': '-115.87',
                   'current.barometer.formatted': '10132.55', 'day.rain.sum.formatted': '1234.56',
                   '24h.rain.sum.formatted': '1302.55', 'current.rainRate.formatted': '1456.66',
                   'current.windSpeed.formatted': '1122', '10m.windGust.max.formatted': '1400',
                   'day.windGust.max.formatted': '1520', 'current.appTemp.formatted': '-120.55',
                   'current.UV.formatted': '111.8', 'current.radiation.formatted': '10124'})


class Server:
    """What the page's fetches get.  Mutated between checks; the page picks
    the change up on its next poll."""
    def __init__(self, html):
        self.html = html
        self.set()
        self.polls = 0

    def set(self, mode='ok', age=1, e=None, status=200, frozen=False):
        self.mode, self.age, self.entry, self.status = mode, age, e or entry(), status
        self.frozen = frozen

    def handle(self, route, request):
        path = request.url.split('://', 1)[1].split('/', 1)[1].split('?')[0]
        if path in ('', 'board.html'):
            return route.fulfill(body=self.html.encode('utf-8'), content_type='text/html; charset=utf-8')
        if path == 'loop-data.txt':
            self.polls += 1
            if self.mode == 'abort':
                return route.abort()
            if self.mode == 'status':
                return route.fulfill(status=self.status, body='no')
            if self.mode == 'badjson':
                return route.fulfill(body='{not json', content_type='application/json')
            # Stamped now, as a live station's file is: a timestamp that
            # never moves is one the board rightly calls stale after
            # max_age, however young the Date header says it is.
            e = dict(self.entry)
            if isinstance(e.get('current.dateTime.raw'), (int, float)) and not self.frozen:
                e['current.dateTime.raw'] = int(time.time())
            body = {'OtherReport': {}} if self.mode == 'noentry' else {ct.REPORT_NAME: e}
            now = e['current.dateTime.raw'] if self.frozen else int(time.time())
            date = email.utils.formatdate(now + self.age, usegmt=True)
            return route.fulfill(body=json.dumps(body), headers={'Date': date,
                                                                 'Content-Type': 'application/json'})
        f = os.path.join(SKIN, path)
        if os.path.isfile(f):
            return route.fulfill(body=open(f, 'rb').read(),
                                 content_type=TYPES.get(f.rsplit('.', 1)[-1], 'application/octet-stream'))
        return route.fulfill(status=404, body='')


class Board:
    def __init__(self, browser, tmpl, size=(1280, 800), lang='en', missing=ct.ALL_PRESENT,
                 overrides=None, query='?page_update_pwd=testpwd', unit=None):
        extras = {'refresh_rate': '1'}
        extras.update(overrides or {})
        self.server = Server(ct.render(tmpl, missing, analytics=False, overrides=extras, lang=lang,
                                       unit=unit))
        self.page = browser.new_page(viewport={'width': size[0], 'height': size[1]})
        self.errors = []
        self.page.on('pageerror', lambda e: self.errors.append(str(e)))
        self.page.route('**/*', self.server.handle)
        self.page.goto('http://board.test/board.html' + query)
        self.page.evaluate('document.fonts.ready')

    def wait(self, js, timeout=6000):
        self.page.wait_for_function(js, timeout=timeout)

    def close(self):
        # A request held open on purpose (hang_analytics) is let go here
        # rather than left pending when the page goes.
        while HELD:
            try:
                HELD.pop().abort()
            except Exception:
                pass
        self.page.close()


# ---------------------------------------------------------------------------
# The readout board.

# A cell's text as the board shows it: a dimmed decimal point reads _, and
# the minus sign every dash is drawn as reads -.
RO_TEXT = """id => {
  const v = document.querySelector('#' + id + ' .ro-v');
  if (!v) return null;
  let s = '';
  for (const n of v.childNodes) {
    if (n.nodeType === 3) s += n.data;
    else if (n.classList.contains('ro-dp-off')) s += '_';
    else s += n.textContent.replace(/−/g, '-');
  }
  return s.trim();
}"""

# Each row's --fit, top to bottom.
FITS = "[...document.querySelectorAll('.ro-row')].map(r => r.style.getPropertyValue('--fit') || '1')"


def lit_pixels(img):
    """Pixels bright enough to be lettering (the panels are near black)."""
    im = img.convert('RGB')
    px = im.load()
    w, h = im.size
    return {(x, y) for y in range(h) for x in range(w) if max(px[x, y]) > 150}


def shot(page, box):
    return Image.open(io.BytesIO(page.screenshot(clip=box)))


def check_readout(browser):
    failures = []
    b = Board(browser, 'index.html.tmpl')
    t = lambda cid: b.page.evaluate(RO_TEXT, cid)
    b.wait("document.querySelector('#ro-t .ro-v') && document.querySelector('#ro-t .ro-v').textContent.trim() === '78.4'")
    for cid, want in (('ro-t', '78.4'), ('ro-td', '61.2'), ('ro-w', '4 NNE'), ('ro-g', '9'),
                      ('ro-gd', '14'), ('ro-b', '29.912'), ('ro-rd', '0.00'), ('ro-rr', '0.00'),
                      ('ro-uv', '5.4'), ('ro-rad', '612'), ('ro-aqi', '42'), ('ro-rh', '56'),
                      ('ro-fl', '79.9'), ('ro-clk', '4:07:17 PM')):
        if t(cid) != want:
            failures.append('readout %s reads %r, expected %r' % (cid, t(cid), want))
    if b.page.evaluate("document.querySelector('#ro-aqi .ro-n').style.color") != 'rgb(0, 228, 0)':
        failures.append('the air quality reading is not in its level color')
    if b.page.evaluate("!!document.querySelector('#ro-b .ro-trend')") is not True:
        failures.append('the barometer has no trend arrow')
    # The arrow takes no height: were the barometer's cell taller for it,
    # the row would fit differently with the arrow than without.
    heights = b.page.evaluate("['#ro-b', '#ro-w'].map(c => document.querySelector(c + ' .ro-n').getBoundingClientRect().height)")
    if abs(heights[0] - heights[1]) > .5:
        failures.append('the barometer with its trend arrow is %.1f px tall, the wind beside it %.1f' % tuple(heights))
    # The readings are in Bebas Neue, fetched from the skin: a font the
    # stylesheet names at a path that is not there leaves the board in
    # whatever fallback the tablet has.
    b.page.evaluate('document.fonts.ready')
    faces = b.page.evaluate("[...document.fonts].filter(f => f.family.replace(/\"/g, '') === 'Bebas Neue')"
                            ".map(f => f.status)")
    if faces != ['loaded']:
        failures.append('Bebas Neue is %s, not loaded' % (faces or 'not declared'))
    if 'Bebas Neue' not in b.page.evaluate("getComputedStyle(document.querySelector('#ro-t .ro-n')).fontFamily"):
        failures.append('the readings are not set in Bebas Neue')
    fresh = ro_digits(b)

    # Aging, then old: the age on the status line, every reading dashes
    # with its decimal point dimmed.
    b.server.set(age=47)
    b.wait("document.getElementById('ro-clock').className.indexOf('ro-status-aging') >= 0")
    if t('ro-clk') != '47 S AGO':
        failures.append('47 s old reads %r' % t('ro-clk'))
    for cid, want in (('ro-t', '--_-'), ('ro-b', '--_---'), ('ro-w', '- ---'), ('ro-aqi', '--')):
        if t(cid) != want:
            failures.append('missing %s reads %r, expected %r' % (cid, t(cid), want))
    if b.page.evaluate("!!document.querySelector('#ro-b .ro-trend')"):
        failures.append('the trend arrow outlived the data')
    failures += ro_missing_pixels(b, fresh)
    b.server.set(age=420)
    b.wait("document.getElementById('ro-clock').className.indexOf('ro-status-old') >= 0")
    if t('ro-clk') != '7 M AGO':
        failures.append('7 minutes old reads %r' % t('ro-clk'))

    # Failures, each on the status line.
    for mode, status, want in (('status', 404, 'HTTP 404'), ('badjson', 200, 'BAD DATA'),
                               ('noentry', 200, 'NO ENTRY'), ('abort', 200, 'NO CONNECT')):
        b.server.set(mode=mode, status=status)
        b.wait("document.getElementById('ro-clock').className.indexOf('ro-status-error') >= 0"
               " && document.querySelector('#ro-clk .ro-v').textContent.replace(/\\s/g, '') === %s"
               % json.dumps(want.replace(' ', '')))
    # Back, and a minus sign is a minus in a digit's box too; a Danish
    # wind direction is the font's own letters.
    b.server.set(e=WIDE)
    b.wait("document.getElementById('ro-clock').className === 'ro-panel ro-status-live'")
    if t('ro-t') != '-12.3':
        failures.append('-12.3 reads %r' % t('ro-t'))
    if t('ro-w') != '112 ØNØ':
        failures.append('a Danish wind direction reads %r' % t('ro-w'))
    # A station that reports no gusts shows the highest wind speed instead.
    gustless = entry(**{'10m.windSpeed.max.formatted': '11', 'day.windSpeed.max.formatted': '17'})
    del gustless['10m.windGust.max.formatted']
    del gustless['day.windGust.max.formatted']
    b.server.set(e=gustless)
    b.wait("document.querySelector('#ro-g .ro-v').textContent.trim() === '11'")
    if t('ro-gd') != '17':
        failures.append('with no gusts reported, today reads %r, not the top speed 17' % t('ro-gd'))
    # Not-a-number is missing: WeeWX writes N/A for a value it lacks, and a
    # trend code that is not a number draws no arrow.
    b.server.set(e=entry(**{'current.outTemp.formatted': 'N/A', 'current.barometer.formatted': '29.912',
                            'trend.barometer.code': 'x'}))
    b.wait("(%s)('ro-t') === '--_-'" % RO_TEXT)
    if b.page.evaluate("!!document.querySelector('#ro-b .ro-trend')"):
        failures.append('a trend code that is not a number drew an arrow')
    # Calm by the speed as SHOWN: a raw 0.00009 shows as 0, and a direction
    # beside it would claim a wind that is not there.
    b.server.set(e=entry(**{'current.windSpeed.formatted': '0', 'current.windSpeed.raw': 9.1e-05}))
    b.wait("document.querySelector('#ro-w .ro-v').textContent.trim().charAt(0) === '0'")
    if t('ro-w') != '0':
        failures.append('a wind that shows 0 reads %r: a direction beside a calm' % t('ro-w'))
    failures += ['readout page: %s' % e for e in b.errors]
    b.close()
    return failures


def ro_crops(b, cid, cls):
    """Each .cls box in a cell, as tall as the cell's own block (.ro-n), so
    a crop takes in the whole glyph and nothing of the label beneath or the
    row below: an inline box runs to the font's full ascent and descent,
    far past the figures."""
    n = b.page.query_selector('#%s .ro-n' % cid).bounding_box()
    crops = []
    for d in b.page.query_selector_all('#%s .%s' % (cid, cls)):
        r = d.bounding_box()
        crops.append({'x': r['x'], 'y': n['y'], 'width': r['width'], 'height': n['height']})
    return crops


def ro_ink(b, box):
    """The lit pixels in a crop, in page coordinates."""
    return {(x + box['x'], y + box['y']) for x, y in lit_pixels(shot(b.page, box))}


def ro_digits(b):
    """The temperature and the barometer as they stand: each figure's
    width, and each digit's lit pixels."""
    out = {}
    for cid in ('ro-t', 'ro-b'):
        width = b.page.evaluate("document.querySelector('#%s .ro-v').getBoundingClientRect().width" % cid)
        out[cid] = (width, [ro_ink(b, box) for box in ro_crops(b, cid, 'ro-d')])
    return out


def ro_missing_pixels(b, fresh):
    """The placeholders, measured against the readings they replaced: each
    exactly as wide, each missing digit a bar across the middle of where
    the digit stood, and each decimal point dimmed -- there to see, but
    never lit.  In page coordinates, and each crop taken afresh, so a
    figure that had moved would be measured where it now is."""
    failures = []
    for cid, (width, digits) in sorted(fresh.items()):
        now = b.page.evaluate("document.querySelector('#%s .ro-v').getBoundingClientRect().width" % cid)
        if abs(now - width) > .5:
            failures.append('missing %s is %.1f px wide, the reading was %.1f' % (cid, now, width))
        crops = ro_crops(b, cid, 'ro-d')
        if len(crops) != len(digits):
            failures.append('missing %s has %d digits, the reading had %d' % (cid, len(crops), len(digits)))
        for box, full in zip(crops, digits):
            bar = ro_ink(b, box)
            if not full or not bar:
                failures.append('%s: a digit or its dash lit nothing' % cid)
                continue
            top = min(y for x, y in full)
            height = max(y for x, y in full) - top
            ys = [y for x, y in bar]
            xs = [x for x, y in bar]
            if max(ys) - min(ys) > height * .2:
                failures.append('%s: a missing digit is %d px tall where the digit was %d: not a bar'
                                % (cid, max(ys) - min(ys), height))
            elif not .35 <= ((max(ys) + min(ys)) / 2 - top) / height <= .65:
                failures.append('%s: a missing digit is not across the middle of the digit' % cid)
            if max(xs) - min(xs) < box['width'] * .5:
                failures.append('%s: a missing digit spans %d px of its %d px box'
                                % (cid, max(xs) - min(xs), box['width']))
    dps = ro_crops(b, 'ro-t', 'ro-dp-off') + ro_crops(b, 'ro-b', 'ro-dp-off')
    if len(dps) != 2:
        failures.append('%d dimmed decimal points, expected 2' % len(dps))
    for box in dps:
        im = shot(b.page, box).convert('RGB')
        brightest = max(max(im.getpixel((x, y))) for x in range(im.width) for y in range(im.height))
        if brightest > 150:
            failures.append('a decimal point is lit with no data')
        elif brightest < 30:
            failures.append('a decimal point is dark with no data, not dimmed')
    return failures


def check_readout_widths(browser):
    """Letters are not all one width.  A wind direction as long as the last
    one but wider (WWW after NNN) makes the board fit again rather than run
    past its panel, and a narrower one (III) leaves the cell as wide as it
    was, so the gusts beside it stay where they are.  Dutch at 1024x768
    with readings too wide for the design: the wind row is already full.
    And the same holds through the refits a browser without document.fonts
    makes on its timer."""
    failures = []
    w = "document.querySelector('#ro-w .ro-n').getBoundingClientRect().width"
    b = Board(browser, 'index.html.tmpl', size=(1024, 768), lang='nl')
    widths = []
    for d in ('NNN', 'WWW', 'III'):
        b.server.set(e=entry(**dict(EXTREME, **{'current.windDir.ordinal_compass': d})))
        b.wait("document.querySelector('#ro-w .ro-v') && document.querySelector('#ro-w .ro-v').textContent.indexOf('%s') >= 0" % d)
        b.page.evaluate('new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))')
        for p in b.page.evaluate(RO_FIT):
            failures.append('the wind direction %s: %s overflows' % (d, p))
        widths.append(b.page.evaluate(w))
    if widths[1] <= widths[0]:
        failures.append('WWW is no wider than NNN (%.1f, %.1f px): this checks nothing' % tuple(widths[:2]))
    if widths[2] < widths[1] - .5:
        failures.append('the wind cell narrowed from %.1f to %.1f px for III' % (widths[1], widths[2]))
    b.close()
    # Without document.fonts, and with a hung analytics script holding
    # window load back, the board fits again every two seconds for a
    # minute, not knowing when its fonts arrive.  It notices the figures'
    # font at the first tick after it lands, and measures every cell again
    # then, once; the ticks after that must not narrow a cell.  So: wait
    # until the arrival has been noticed, then WWW, then III, and two ticks
    # later the cell is still as wide as WWW made it.
    b = Board.__new__(Board)
    b.server = Server(ct.render('index.html.tmpl', analytics=True, overrides={'refresh_rate': '1'}))
    b.errors = []
    b.page = browser.new_page(viewport={'width': 1280, 'height': 800})
    b.page.add_init_script(NO_FONT_API)
    b.page.route('**/*', hang_analytics(b.server.handle))
    # The page's clock is the test's: each two-second tick is run on demand.
    b.page.clock.install()
    b.page.goto('http://board.test/board.html?page_update_pwd=testpwd', wait_until='domcontentloaded')

    def tick():
        n = b.page.evaluate('roTries')
        b.page.clock.run_for(2000)
        b.wait('roTries > %d' % n)
    tick()
    b.wait("roProbed === roProbe()")
    for d in ('WWW', 'III'):
        b.server.set(e=entry(**{'current.windDir.ordinal_compass': d}))
        b.page.clock.run_for(1000)                 # the next poll
        b.wait("document.querySelector('#ro-w .ro-v') && document.querySelector('#ro-w .ro-v').textContent.indexOf('%s') >= 0" % d)
    wide = b.page.evaluate(w)
    tick()
    tick()
    if b.page.evaluate(w) < wide - .5:
        failures.append('without document.fonts, a refit on its timer narrowed the wind cell from'
                        ' %.1f to %.1f px' % (wide, b.page.evaluate(w)))
    b.close()
    return failures


def check_readout_no_font(browser):
    """Bebas Neue never arrives -- not yet synced to the web server, or
    blocked: the figures fall back to a wider face, and each digit's box
    widens to hold its digit rather than letting it run into the next."""
    failures = []
    b = Board.__new__(Board)
    b.server = Server(ct.render('index.html.tmpl', analytics=False, overrides={'refresh_rate': '1'}))
    b.errors = []
    b.page = browser.new_page(viewport={'width': 1280, 'height': 800})

    def route(r, request):
        if request.url.endswith('bebasneue.woff2'):
            return r.fulfill(status=404, body='')
        return b.server.handle(r, request)
    b.page.route('**/*', route)
    b.page.goto('http://board.test/board.html?page_update_pwd=testpwd')
    b.wait("document.querySelector('#ro-b .ro-v') && document.querySelector('#ro-b .ro-v').textContent.trim() === '29.912'")
    spill = b.page.evaluate("[...document.querySelectorAll('.ro-d')].filter(d => d.scrollWidth > d.clientWidth)"
                            ".map(d => d.closest('.ro-c').id)")
    if spill:
        failures.append('with no Bebas Neue, digits spill out of their boxes in %s' % sorted(set(spill)))
    for p in b.page.evaluate(RO_FIT):
        failures.append('with no Bebas Neue, %s overflows' % p)
    b.close()
    return failures


def check_font_covers(browser):
    """Every character the readout board sets in Bebas Neue, in every
    language, is in the font: the status words, the wind directions, the
    clock's AM and PM, the digits, the decimal point, the colon and the
    minus sign.  A character it lacks would be drawn in whatever face the
    tablet falls back to.  (Read from the font itself: a browser shows no
    sign of a fallback it made.)"""
    from fontTools.ttLib import TTFont
    cmap = TTFont(os.path.join(SKIN, 'fonts', 'bebasneue', 'bebasneue.woff2')).getBestCmap()
    need = set('0123456789.:/− AMP')
    for lang in ct.LANGS:
        conf = ct.lang_texts(lang)
        for key in ct.STATUS:
            need |= set(conf['Texts'].get(key, '').replace('{n}', '').upper())
        need |= set(''.join(conf['Units']['Ordinates']['directions'][:16]).upper())
    missing = sorted(ch for ch in need if ord(ch) not in cmap)
    if missing:
        return ['Bebas Neue has no %s' % ', '.join('%r (U+%04X)' % (ch, ord(ch)) for ch in missing)]
    return []


def check_frozen_file(browser):
    """A file whose timestamp has stopped moving goes stale even though
    every response calls it young: the board counts how long the timestamp
    has sat unchanged, and that alone passes max_age (3 s here)."""
    failures = []
    b = Board(browser, 'index.html.tmpl', overrides={'max_age': '3'})
    b.server.set(e=entry(**{'current.dateTime.raw': int(time.time())}), frozen=True)
    b.wait("document.getElementById('ro-clock').className === 'ro-panel ro-status-live'")
    b.wait("document.getElementById('ro-clock').className.indexOf('ro-status-aging') >= 0", timeout=8000)
    if b.page.evaluate(RO_TEXT, 'ro-t') != '--_-':
        failures.append('a frozen file left the temperature up: %r' % b.page.evaluate(RO_TEXT, 'ro-t'))
    b.close()
    return failures


def check_readout_expiry(browser):
    """Without the password the page expires, says so, fetches nothing
    more, and a tap starts it again.  (expiration_time is in hours: 0.0006
    is about two seconds.)"""
    failures = []
    b = Board(browser, 'index.html.tmpl', overrides={'expiration_time': '0.0006'}, query='')
    b.wait("document.getElementById('ro-clock').className.indexOf('ro-status-expired') >= 0")
    if b.page.evaluate(RO_TEXT, 'ro-clk') != 'EXPIRED TAP':
        failures.append('an expired page reads %r' % b.page.evaluate(RO_TEXT, 'ro-clk'))
    polls = b.server.polls
    b.page.wait_for_timeout(2500)          # proving the ABSENCE of polls
    if b.server.polls != polls:
        failures.append('an expired page went on fetching: %d polls' % (b.server.polls - polls))
    b.page.mouse.click(300, 300)
    b.wait("document.getElementById('ro-clock').className === 'ro-panel ro-status-live'")
    b.close()
    # With the password it does not expire.
    b = Board(browser, 'index.html.tmpl', overrides={'expiration_time': '0.0006'})
    b.wait("document.querySelector('#ro-t .ro-v') && document.querySelector('#ro-t .ro-v').textContent.trim() === '78.4'")
    b.page.wait_for_timeout(2600)          # proving the ABSENCE of expiry
    if 'expired' in b.page.evaluate("document.getElementById('ro-clock').className"):
        failures.append('a page with the keep-alive password expired')
    b.close()
    return failures


RO_FIT = """() => {
  const bad = [];
  for (const p of document.querySelectorAll('.ro-panel')) {
    const P = p.getBoundingClientRect();
    for (const c of p.querySelectorAll('.ro-n, .ro-l')) {
      const r = c.getBoundingClientRect();
      if (r.left < P.left - 1 || r.right > P.right + 1 || r.top < P.top - 1 || r.bottom > P.bottom + 1)
        bad.push(p.id);
    }
  }
  // A panel that cannot hold its cells may simply grow past the window's
  // edge, where nothing scrolls to show it: hold every panel, and the
  // footer, inside the window too.
  for (const e of document.querySelectorAll('.ro-panel, .ro-foot, .ro-title')) {
    const r = e.getBoundingClientRect();
    if (r.left < -1 || r.right > innerWidth + 1 || r.top < -1 || r.bottom > innerHeight + 1)
      bad.push((e.id || 'the footer') + ' leaves the window');
  }
  const title = document.querySelector('.ro-title');
  if (title && title.scrollHeight > title.clientHeight * 1.08)
    bad.push('the title is squeezed to ' + title.clientHeight + 'px of its ' + title.scrollHeight);
  if (document.documentElement.scrollWidth > innerWidth || document.documentElement.scrollHeight > innerHeight)
    bad.push('the page scrolls');
  return [...new Set(bad)];
}"""

# For each readout row the fit has shrunk: whether it is the LARGEST step that
# fits.  The row is set one step (0.01) larger and measured: a row that
# still fits there was shrunk further than it needed to be.  Measured here,
# independently of the page's own arithmetic.
RO_TIGHT = """() => {
  const need = row => {
    let most = 0;
    for (const p of row.querySelectorAll('.ro-panel')) {
      const cs = getComputedStyle(p);
      const iw = p.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
      const ih = p.clientHeight - parseFloat(cs.paddingTop) - parseFloat(cs.paddingBottom);
      const cells = [...p.querySelectorAll('.ro-c')];
      let w = 0, h = 0;
      for (const c of cells) { const r = c.getBoundingClientRect(); w += r.width; h = Math.max(h, r.height); }
      w += Math.max(0, cells.length - 1) * parseFloat(cs.columnGap);
      most = Math.max(most, w / iw, h / ih);
    }
    return most;
  };
  const out = [];
  for (const row of document.querySelectorAll('.ro-row')) {
    const fit = row.style.getPropertyValue('--fit');
    if (!fit || fit === '1') continue;
    const at = need(row);
    row.style.setProperty('--fit', String(Math.round(Number(fit) * 100 + 1) / 100));
    const above = need(row);
    row.style.setProperty('--fit', fit);
    out.push([Number(fit), at, above]);
  }
  return out;
}"""

FLAP_FIT = """() => {
  const b = document.getElementById('flap-board').getBoundingClientRect();
  const f = document.getElementById('flap-foot').getBoundingClientRect();
  const t = document.getElementById('flap-title').getBoundingClientRect();
  const bad = [];
  if (b.left < 0 || b.right > innerWidth || t.top < 0 || f.bottom > innerHeight) bad.push('the board leaves the window');
  if (t.bottom > b.top + 1) bad.push('the title runs into the board');
  const te = document.getElementById('flap-title');
  // A squeezed title loses a good part of its height; a pixel or two of
  // difference is rounding.
  if (te.scrollHeight > te.clientHeight * 1.08) bad.push('the title is squeezed to ' + te.clientHeight + 'px of its ' + te.scrollHeight);
  if (document.documentElement.scrollWidth > innerWidth || document.documentElement.scrollHeight > innerHeight)
    bad.push('the page scrolls');
  return bad;
}"""


def check_long_title(browser):
    """A title far too long for one line is cut with an ellipsis; neither
    board is pushed off the screen by it."""
    failures = []
    long_title = 'The Weather Station at the End of the Very Long Road, Somewhere Rather Far Away'
    for tmpl, check, sel in (('index.html.tmpl', RO_FIT, '.ro-title'), ('splitflap.html.tmpl', FLAP_FIT, '#flap-title')):
        for size in ((1280, 800), (1024, 768)):
            b = Board(browser, tmpl, size=size, overrides={'title': long_title})
            b.page.evaluate('document.fonts.ready')
            b.page.wait_for_timeout(1500)
            for p in b.page.evaluate(check):
                failures.append('%s %dx%d, a long title: %s' % (tmpl, size[0], size[1], p))
            clipped = b.page.evaluate("(s => { const e = document.querySelector(s); return e.scrollWidth > e.clientWidth; })", sel)
            if not clipped:
                failures.append('%s %dx%d: the long title fit whole, so this checked nothing' % (tmpl, size[0], size[1]))
            b.close()
    return failures


# Run before a page's own scripts: a browser without the font loading API.
NO_FONT_API = "Object.defineProperty(document, 'fonts', {value: undefined, configurable: true});"


# Run before a page's own scripts: a browser without flex gap, which draws
# none between the readout panels' cells and reports it as "normal", which is
# not a number.
GAP_NORMAL = """(() => {
  document.addEventListener('DOMContentLoaded', () => {
    const st = document.createElement('style');
    st.textContent = '.ro-panel { gap: 0 !important; }';
    document.head.appendChild(st);
  });
  const real = window.getComputedStyle;
  window.getComputedStyle = function (el, pseudo) {
    const cs = real.call(window, el, pseudo);
    if (!el.classList || !el.classList.contains('ro-panel')) return cs;
    return new Proxy(cs, {get: (t, k) => k === 'columnGap' ? 'normal'
                                   : (typeof t[k] === 'function' ? t[k].bind(t) : t[k])});
  };
})();"""


HELD = []


def hang_analytics(handle):
    """A route handler that never answers the analytics script, as a
    tablet with no route out sees it: window load then never fires.  The
    request waits in HELD until Board.close lets it go."""
    def route(r, request):
        if 'googletagmanager' in request.url:
            HELD.append(r)
            return None
        return handle(r, request)
    return route


def check_flap_late_font(browser, font_api=True, hang=False):
    """A split-flap board whose row names are too long for the screen
    shrinks to fit -- and fits again once its font has loaded, which the
    first paint may come before.  The font is held back a second here, and
    one row name made absurdly long so the board has to shrink at all.
    Without document.fonts (font_api False) it fits again at window load,
    and with the analytics script hung (hang), so that window load never
    comes, on its timers."""
    failures = []
    texts = ct.lang_texts('en')
    texts['Texts']['BAROMETER'] = 'ATMOSPHERIC PRESSURE AT SEA LEVEL'
    real = ct.lang_texts
    ct.lang_texts = lambda lang: texts
    try:
        b = Board.__new__(Board)
        b.server = Server(ct.render('splitflap.html.tmpl', analytics=hang, overrides={'refresh_rate': '1'}))
    finally:
        ct.lang_texts = real
    plain = hang_analytics(b.server.handle) if hang else b.server.handle

    def late(route, request):
        if request.url.endswith('jost.woff2'):
            time.sleep(1.0)
        return plain(route, request)
    b.errors = []
    b.page = browser.new_page(viewport={'width': 1024, 'height': 768})
    if not font_api:
        b.page.add_init_script(NO_FONT_API)
    b.page.route('**/*', late)
    b.page.goto('http://board.test/board.html?page_update_pwd=testpwd',
                wait_until='domcontentloaded' if hang else 'load')
    if font_api:
        b.page.evaluate('document.fonts.ready')
    if hang:
        # The two-second timer, after the font's one-second hold.
        b.page.wait_for_timeout(2500)
    b.page.evaluate('new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))')
    for p in b.page.evaluate(FLAP_FIT):
        failures.append('a long row name, font late: %s' % p)
    full = b.page.evaluate("""(() => { const b = document.getElementById('flap-board').getBoundingClientRect(),
        f = document.getElementById('flap-foot').getBoundingClientRect();
        return Math.max(b.width * 1.02 / innerWidth, (b.height + f.height) * 1.04 / innerHeight); })()""")
    if full < 0.98:
        failures.append('with its font loaded late the board fills only %.3f of the screen:'
                        ' it was fitted to the fallback font and never again' % full)
    b.close()
    return failures


def check_readout_without_font_api(browser):
    """Without document.fonts the readout board still fits again once its
    fonts are in, at window load -- or on its timers, when a hung analytics
    script means window load never comes -- and ends at the fit a browser
    with the font API reaches.  The readings are too wide for the design,
    so the fit has rows to shrink."""
    failures = []
    want = None
    for font_api, hang in ((True, False), (False, False), (False, True)):
        b = Board.__new__(Board)
        b.server = Server(ct.render('index.html.tmpl', analytics=hang, overrides={'refresh_rate': '1'}))
        b.server.set(e=EXTREME)
        b.errors = []
        b.page = browser.new_page(viewport={'width': 1024, 'height': 768})
        if not font_api:
            b.page.add_init_script(NO_FONT_API)
        b.page.route('**/*', hang_analytics(b.server.handle) if hang else b.server.handle)
        b.page.goto('http://board.test/board.html?page_update_pwd=testpwd',
                    wait_until='domcontentloaded' if hang else 'load')
        b.wait("document.querySelector('#ro-t .ro-v') && document.querySelector('#ro-t .ro-v').textContent.indexOf('112.34') >= 0")
        if want is None:
            b.page.evaluate('document.fonts.ready')
            b.page.evaluate('new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))')
            want = b.page.evaluate(FITS)
            if all(f == '1' for f in want):
                failures.append('readings too wide for the design shrank no row: the test proves nothing')
        else:
            try:
                b.wait('JSON.stringify(%s) === %s' % (FITS, json.dumps(json.dumps(want, separators=(',', ':')))),
                       timeout=5000)
            except Exception:
                failures.append('without document.fonts%s the fit ends at %s, not %s'
                                % (' or window load' if hang else '', b.page.evaluate(FITS), want))
        b.close()
    return failures


def check_readout_late_font(browser):
    """Each of the readout board's fonts held back until the board has
    painted in a fallback: once it arrives the board fits again, and ends
    where a board that had its fonts from the start does.  Bebas Neue
    sets the readings and Jost the labels; the fit measures both, so each
    is held alone.  Dutch, whose labels run longest, and readings too wide
    for the design, so the fit has rows to shrink."""
    failures = []
    ref = Board(browser, 'index.html.tmpl', size=(1024, 768), lang='nl')
    ref.server.set(e=EXTREME)
    ref.wait("document.querySelector('#ro-t .ro-v') && document.querySelector('#ro-t .ro-v').textContent.indexOf('112.34') >= 0")
    ref.page.evaluate('new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))')
    want = ref.page.evaluate(FITS)
    ref.close()
    for font in ('bebasneue.woff2', 'jost.woff2'):
        held = []
        b = Board.__new__(Board)
        b.server = Server(ct.render('index.html.tmpl', analytics=False, lang='nl', overrides={'refresh_rate': '1'}))
        b.server.set(e=EXTREME)
        b.errors = []
        b.page = browser.new_page(viewport={'width': 1024, 'height': 768})

        def route(r, request, handle=b.server.handle, font=font):
            if request.url.endswith(font):
                held.append(r)
                return None
            return handle(r, request)
        b.page.route('**/*', route)
        b.page.goto('http://board.test/board.html?page_update_pwd=testpwd', wait_until='domcontentloaded')
        b.wait("document.querySelector('#ro-t .ro-v') && document.querySelector('#ro-t .ro-v').textContent.indexOf('112.34') >= 0")
        b.page.evaluate('new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))')
        early = b.page.evaluate(FITS)
        if early == want:
            failures.append('with %s held the fallback fit the board just as the font does: the test'
                            ' proves nothing' % font)
        while held:
            b.server.handle(held[0], held.pop(0).request)
        try:
            b.wait('JSON.stringify(%s) === %s' % (FITS, json.dumps(json.dumps(want, separators=(',', ':')))),
                   timeout=3000)
        except Exception:
            failures.append('%s arriving late left the fit at %s, not %s' % (font, b.page.evaluate(FITS), want))
        b.close()
    return failures


def check_font_late_without_load(browser):
    """Without document.fonts, with the analytics script hung so window
    load never comes, and each board's font held back eight seconds: the
    readout board still ends fitted to Bebas Neue, and the split-flap
    board refits to Jost once it arrives.  Both pages load together and the
    fonts are released from here, so the wait is paid once."""
    failures = []
    ref = Board(browser, 'index.html.tmpl', size=(1024, 768))
    ref.server.set(e=EXTREME)
    ref.wait("document.querySelector('#ro-t .ro-v') && document.querySelector('#ro-t .ro-v').textContent.indexOf('112.34') >= 0")
    ref.page.evaluate('new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))')
    want = ref.page.evaluate(FITS)
    ref.close()
    held = []

    def holding(handle, font):
        def route(r, request):
            if request.url.endswith(font):
                held.append((r, handle))
                return None
            return handle(r, request)
        return hang_analytics(route)

    ro = Board.__new__(Board)
    ro.server = Server(ct.render('index.html.tmpl', analytics=True, overrides={'refresh_rate': '1'}))
    ro.server.set(e=EXTREME)
    ro.errors = []
    ro.page = browser.new_page(viewport={'width': 1024, 'height': 768})
    ro.page.add_init_script(NO_FONT_API)
    ro.page.route('**/*', holding(ro.server.handle, 'bebasneue.woff2'))
    texts = ct.lang_texts('en')
    texts['Texts']['BAROMETER'] = 'ATMOSPHERIC PRESSURE AT SEA LEVEL'
    real = ct.lang_texts
    ct.lang_texts = lambda lang: texts
    try:
        flap = Board.__new__(Board)
        flap.server = Server(ct.render('splitflap.html.tmpl', analytics=True, overrides={'refresh_rate': '1'}))
    finally:
        ct.lang_texts = real
    flap.errors = []
    flap.page = browser.new_page(viewport={'width': 1024, 'height': 768})
    flap.page.add_init_script(NO_FONT_API)
    flap.page.route('**/*', holding(flap.server.handle, 'jost.woff2'))
    start = time.time()
    for b in (ro, flap):
        b.page.goto('http://board.test/board.html?page_update_pwd=testpwd', wait_until='domcontentloaded')
    # Past the old six-second timer, with the fonts still held: the readout
    # board has only the fallback font to fit, which runs wider, so its fit
    # must differ, or this test is not testing anything.
    ro.page.wait_for_timeout(max(0, 7000 - (time.time() - start) * 1000))
    early = ro.page.evaluate(FITS)
    if early == want:
        failures.append('the fallback font fit the board just as Bebas Neue does: the test proves nothing')
    ro.page.wait_for_timeout(max(0, 8000 - (time.time() - start) * 1000))
    for r, handle in held:
        handle(r, r.request)
    try:
        ro.wait('JSON.stringify(%s) === %s' % (FITS, json.dumps(json.dumps(want, separators=(',', ':')))),
                timeout=4000)
    except Exception:
        failures.append('a font arriving after eight seconds left the fit at %s, not %s'
                        % (ro.page.evaluate(FITS), want))
    try:
        flap.wait("""(() => { const b = document.getElementById('flap-board').getBoundingClientRect(),
            f = document.getElementById('flap-foot').getBoundingClientRect();
            return Math.max(b.width * 1.02 / innerWidth, (b.height + f.height) * 1.04 / innerHeight) >= 0.98; })()""",
                  timeout=4000)
    except Exception:
        failures.append('a font arriving after eight seconds: the split-flap board was never refitted to it')
    for p in flap.page.evaluate(FLAP_FIT):
        failures.append('a font arriving after eight seconds: %s' % p)
    ro.close()
    flap.close()
    return failures


def check_readout_fit_gap_normal(browser):
    """A browser that reports the panels' gap as "normal" still fits: with
    readings too wide for the design, every panel holds and some row
    shrinks."""
    failures = []
    b = Board.__new__(Board)
    b.server = Server(ct.render('index.html.tmpl', analytics=False, overrides={'refresh_rate': '1'}))
    b.server.set(e=EXTREME)
    b.errors = []
    b.page = browser.new_page(viewport={'width': 1024, 'height': 768})
    b.page.add_init_script(GAP_NORMAL)
    b.page.route('**/*', b.server.handle)
    b.page.goto('http://board.test/board.html?page_update_pwd=testpwd')
    b.wait("document.querySelector('#ro-t .ro-v') && document.querySelector('#ro-t .ro-v').textContent.indexOf('112.34') >= 0")
    b.page.evaluate('new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))')
    fits = b.page.evaluate("[...document.querySelectorAll('.ro-row')].map(r => r.style.getPropertyValue('--fit') || '1')")
    if all(f == '1' for f in fits):
        failures.append('with the gap reported as "normal" no row shrank: %s' % fits)
    for p in b.page.evaluate(RO_FIT):
        failures.append('with the gap reported as "normal": %s overflows' % p)
    b.close()
    return failures


def check_fit(browser):
    """Both boards, at every size, with the widest readings, in English and
    in the language with the longest words.  One page per board and
    language, resized: the fit reruns on every resize."""
    failures = []
    for lang in ('en', 'nl'):
        ro = Board(browser, 'index.html.tmpl', size=SIZES[0], lang=lang)
        ro.server.set(e=WIDE)
        ro.wait("document.querySelector('#ro-t .ro-v') && document.querySelector('#ro-t .ro-v').textContent.indexOf('12.3') >= 0")
        flap = Board(browser, 'splitflap.html.tmpl', size=SIZES[0], lang=lang)
        flap.wait("document.querySelector('#flap-temp .flap')")
        for size in SIZES:
            for b in (ro, flap):
                b.page.set_viewport_size({'width': size[0], 'height': size[1]})
                b.page.evaluate('new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))')
            for p in ro.page.evaluate(RO_FIT):
                failures.append('readout %s %dx%d: %s overflows' % (lang, size[0], size[1], p))
            for p in flap.page.evaluate(FLAP_FIT):
                failures.append('split-flap %s %dx%d: %s' % (lang, size[0], size[1], p))
        # The fit counts the cells and nothing else: a panel with room to
        # spare is not shrunk by its hidden heading.  At 1024x768, where the
        # title's line leaves height to spare, everyday readings keep every
        # row at its full size.  (At 16:10 the title's line comes out of
        # the temperature row: that is its cost.)
        ro.server.set()
        ro.page.set_viewport_size({'width': 1024, 'height': 768})
        ro.wait("document.querySelector('#ro-t .ro-v').textContent.indexOf('78.4') >= 0")
        ro.page.evaluate('new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))')
        if lang == 'en':
            fits = ro.page.evaluate("[...document.querySelectorAll('.ro-row')].map(r => r.style.getPropertyValue('--fit') || '1')")
            if any(f != '1' for f in fits):
                failures.append('everyday English readings shrank a row at 1024x768: %s' % fits)
        # The case that needs the fit: at 1024x768 every panel still holds.
        ro.server.set(e=EXTREME)
        ro.wait("document.querySelector('#ro-t .ro-v').textContent.indexOf('112.34') >= 0")
        ro.page.set_viewport_size({'width': 1024, 'height': 768})
        ro.page.evaluate('new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))')
        for p in ro.page.evaluate(RO_FIT):
            failures.append('readout %s, readings too wide for the design: %s overflows' % (lang, p))
        tight = ro.page.evaluate(RO_TIGHT)
        if not tight:
            failures.append('readout %s: readings too wide for the design shrank no row' % lang)
        for fit, at, above in tight:
            if at > 1.001:
                failures.append('readout %s: a row at %.2f is %.3f full, overflowing' % (lang, fit, at))
            if above <= 1.001:
                failures.append('readout %s: a row at %.2f would still fit a step larger (%.3f full'
                                ' there): the fit shrank it further than it needed' % (lang, fit, above))
        ro.close()
        flap.close()
    return failures


# ---------------------------------------------------------------------------
# The split-flap board.

FLAP_ROW = "id => [...document.querySelectorAll('#' + id + ' .flap')].map(f => (f.getAttribute('data-ch') || ' ').charAt(0) === '>' ? '^' : (f.getAttribute('data-ch') || ' ')).join('')"
FLAP_LAMP = "id => { const l = document.getElementById(id + '-lamp'); return l.classList.contains('flap-lit') ? l.style.getPropertyValue('--flap-lamp') : '' }"


def check_flap(browser):
    failures = []
    # A US-units station, like entry()'s readings: its lamps judge mph and
    # inHg.  (check_templates.py holds the metric conversion.)
    b = Board(browser, 'splitflap.html.tmpl', unit=ct.UnitUS())
    row = lambda rid: b.page.evaluate(FLAP_ROW, rid)
    lamp = lambda rid: b.page.evaluate(FLAP_LAMP, rid)
    b.wait("document.querySelector('#flap-temp .flap') && document.querySelector('#flap-temp .flap').getAttribute('data-ch') === '7'")
    for rid, want in (('flap-time', ' 4:07:17 PM '), ('flap-temp', '78.4°  HI 81'),
                      ('flap-dew', '61.2°  RH 56'), ('flap-wind', 'NNE   4  G 9'),
                      ('flap-baro', '29.912 ^    '), ('flap-rain', '0.00 0.00/HR'),
                      ('flap-air', ' 42 GOOD    ')):
        if row(rid) != want:
            failures.append('split-flap %s reads %r, expected %r' % (rid, row(rid), want))
    for rid in ('flap-time', 'flap-wind', 'flap-baro', 'flap-rain', 'flap-air'):
        if lamp(rid):
            failures.append('the %s lamp is lit on a quiet day' % rid)
    # A storm: every lamp that should light does.
    b.server.set(e=entry(**{'10m.windGust.max.formatted': '38', '10m.windGust.max.raw': 38.0,
                            'current.barometer.formatted': '29.612', 'current.barometer.raw': 29.612,
                            'current.rainRate.formatted': '0.42', 'current.rainRate.raw': 0.42,
                            'current.pm2_5_aqi.formatted': '51', 'current.pm2_5_aqi_color.raw': 0xffff00}))
    b.wait("document.getElementById('flap-rain-lamp').classList.contains('flap-lit')")
    for rid in ('flap-wind', 'flap-baro', 'flap-rain', 'flap-air'):
        if not lamp(rid):
            failures.append('the %s lamp stayed dark in a storm' % rid)
    # The air lamp lights at 51, the first figure past good, in the level's
    # color; 50 is still good and stayed dark on the quiet day above at 42.
    if lamp('flap-air') not in ('#ffff00', 'rgb(255,255,0)'):
        failures.append('an AQI of 51 lights the air lamp %r, not the level color' % lamp('flap-air'))
    b.server.set(e=entry(**{'current.barometer.formatted': '30.312', 'current.barometer.raw': 30.312}))
    b.wait("!document.getElementById('flap-rain-lamp').classList.contains('flap-lit')")
    if lamp('flap-baro') != '#3399ff':
        failures.append('high pressure lights %r, not blue' % lamp('flap-baro'))
    # 50 is still good: the air lamp goes dark again.
    b.server.set(e=entry(**{'current.pm2_5_aqi.formatted': '50'}))
    b.wait("(%s)('flap-air').indexOf(' 50 ') === 0" % FLAP_ROW)
    if lamp('flap-air'):
        failures.append('an AQI of 50, still good, lights the air lamp %r' % lamp('flap-air'))
    # Not-a-number is missing: an N/A high reads ??, and a trend code that
    # is not a number puts no arrow on the row.
    b.server.set(e=entry(**{'day.outTemp.max.formatted': 'N/A', 'trend.barometer.code': 'x'}))
    b.wait("[...document.querySelectorAll('#flap-temp .flap')].slice(-2).every(f => f.getAttribute('data-ch') === '?')")
    b.page.wait_for_timeout(700)           # the flaps finish turning
    if not row('flap-temp').endswith('HI ??'):
        failures.append('an N/A high reads %r' % row('flap-temp'))
    if '^' in row('flap-baro'):
        failures.append('a trend code that is not a number put an arrow on %r' % row('flap-baro'))
    # Old data: question marks, a blank flap where each decimal point was.
    b.server.set(age=47)
    b.wait("document.getElementById('flap-time-lamp').classList.contains('flap-lit')")
    b.page.wait_for_timeout(800)           # the flaps finish turning
    for rid, want in (('flap-time', '   47 S AGO '), ('flap-temp', '?? ?°  HI ??'),
                      ('flap-baro', '?? ???      '), ('flap-rain', '? ?? ? ??/HR')):
        if row(rid) != want:
            failures.append('old %s reads %r, expected %r' % (rid, row(rid), want))
    if lamp('flap-time') != '#f2a01f':
        failures.append('47 s old lights the time lamp %r, not amber' % lamp('flap-time'))
    # Calm and dry by what is SHOWN: a raw wind of 0.00009 shows as 0, a raw
    # rate of 0.0000001 as 0.00, and neither may claim wind or rain (a real
    # simulator's calm reads exactly so).
    b.server.set(e=entry(**{'current.windSpeed.formatted': '0', 'current.windSpeed.raw': 9.1e-05,
                            'current.rainRate.formatted': '0.00', 'current.rainRate.raw': 1e-07}))
    b.wait("document.getElementById('flap-wind').textContent.indexOf('C') >= 0"
           " || [...document.querySelectorAll('#flap-wind .flap')].some(f => f.getAttribute('data-ch') === 'C')")
    b.page.wait_for_timeout(700)           # the flaps finish turning
    if not row('flap-wind').startswith('CALM'):
        failures.append('a 0 wind reads %r, not CALM' % row('flap-wind'))
    if lamp('flap-rain'):
        failures.append('the rain lamp lit over a rate that shows 0.00')
    # No gusts reported: the gust flap shows the top wind speed, and it
    # lights the gust lamp like a gust would.
    gustless = entry(**{'10m.windSpeed.max.formatted': '45'})   # over 25 mph
    del gustless['10m.windGust.max.formatted']
    b.server.set(e=gustless)
    b.wait("document.getElementById('flap-wind-lamp').classList.contains('flap-lit')")
    b.page.wait_for_timeout(700)           # the flaps finish turning
    if not row('flap-wind').endswith('G 45'):
        failures.append('with no gusts reported the wind row reads %r' % row('flap-wind'))
    # A day's total too long to leave the rate room shows alone, never
    # running off the row with the rate's unit.
    b.server.set(e=entry(**{'day.rain.sum.formatted': '10234.56', 'current.rainRate.formatted': '1234.56'}))
    b.wait("[...document.querySelectorAll('#flap-rain .flap')].map(f => f.getAttribute('data-ch')).join('').indexOf('10234.56') === 0")
    b.page.wait_for_timeout(700)           # the flaps finish turning
    if row('flap-rain') != '10234.56    ':
        failures.append('a rain total with no room for the rate reads %r' % row('flap-rain'))
    b.server.set(mode='status', status=404)
    b.wait("document.getElementById('flap-time-lamp').style.getPropertyValue('--flap-lamp') === '#ff3b30'")
    failures += ['split-flap page: %s' % e for e in b.errors]
    b.close()
    return failures


def check_languages(browser):
    """A 24 hour language shows the station's time as it came, and a Danish
    status line draws its letters."""
    failures = []
    b = Board(browser, 'index.html.tmpl', lang='da')
    b.wait("document.querySelector('#ro-clk .ro-v') && document.querySelector('#ro-clk .ro-v').textContent.trim() === '16:07:17'")
    b.server.set(age=47)
    b.wait("document.getElementById('ro-clock').className.indexOf('aging') >= 0")
    if b.page.evaluate(RO_TEXT, 'ro-clk') != '47 S SIDEN':
        failures.append('Danish 47 s old reads %r' % b.page.evaluate(RO_TEXT, 'ro-clk'))
    failures += ['Danish readout page: %s' % e for e in b.errors]
    b.close()
    b = Board(browser, 'index.html.tmpl', overrides={'clock_format': '24'})
    b.wait("document.querySelector('#ro-clk .ro-v') && document.querySelector('#ro-clk .ro-v').textContent.trim() === '16:07:17'")
    b.close()
    return failures


def main():
    start = time.time()
    ok = True
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for name, fn in (('the readout board: readings, status line, missing data in pixels', check_readout),
                         ('the readout board: expiry, the tap, and the keep-alive password', check_readout_expiry),
                         ('a file that stops changing goes stale', check_frozen_file),
                         ('the split-flap board: rows, lamps, missing data, failures', check_flap),
                         ('the clock and status line in other languages', check_languages),
                         ('Bebas Neue has every character the status line and wind use', check_font_covers),
                         ('the readout board fits again as each of its fonts arrives', check_readout_late_font),
                         ('a wider wind direction refits the board; a narrower one moves nothing', check_readout_widths),
                         ('with no Bebas Neue, each digit keeps to its own box', check_readout_no_font),
                         ('both boards fit every screen size, metric and in Dutch', check_fit),
                         ('the split-flap board refits once its font has loaded', check_flap_late_font),
                         ('without document.fonts, window load or not: the readout and split-flap refits',
                          lambda br: check_readout_without_font_api(br) + check_flap_late_font(br, font_api=False)
                          + check_flap_late_font(br, font_api=False, hang=True)),
                         ('the readout fit, in a browser that reports its gap as "normal"', check_readout_fit_gap_normal),
                         ('without document.fonts or window load, a font that arrives after eight seconds',
                          check_font_late_without_load),
                         ('a long title is cut short, and moves nothing off the screen', check_long_title)):
            t0 = time.time()
            try:
                failures = fn(browser)
            except Exception as e:
                failures = ['%s: %s' % (type(e).__name__, str(e).split('\n')[0])]
            ok = ct.report('%s (%.1f s)' % (name, time.time() - t0), failures) and ok
        browser.close()
    print('%.1f s' % (time.time() - start))
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
