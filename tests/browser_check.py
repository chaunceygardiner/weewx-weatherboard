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
  - missing data: on the LED board every digit is the 8's OWN middle
    segment, lit, and the decimal point is dark -- both measured in pixels
    against the digit's own full 8; on the split-flap board, question marks
    with a blank flap for the decimal point
  - a minus sign is that middle segment too, and an accented capital (Ø in
    a Danish wind direction) is its base letter plus a lit mark
  - the split-flap lamps light for gusts, low and high pressure, rain, and
    the air quality level, and stay dark otherwise
  - both boards fit the screen -- every LED panel holds its cells, the
    split-flap board and its footer sit inside the window -- at 1280x800,
    1024x768, 1180x820 and 1366x1024, with metric readings and the widest
    language

Run with a Python that has Playwright, Cheetah and configobj, and
Chromium in Playwright's browser cache -- tools/pwenv, which is not
published:

  python3 -m venv tools/pwenv
  tools/pwenv/bin/pip install playwright CT3 configobj pillow weewx   # playwright: match the browsers already cached
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
        self.page.on('console', lambda m: self.errors.append(m.text) if 'cannot set' in m.text else None)
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
# The LED board.

LED_TEXT = """id => {
  const v = document.querySelector('#' + id + ' .led-v');
  if (!v) return null;
  let s = '';
  for (const n of v.childNodes) {
    if (n.nodeType === 3) { s += n.data; continue; }
    if (n.classList.contains('led-mid')) s += '-';
    else if (n.classList.contains('led-dp-off')) s += '_';
    else if (n.classList.contains('led-ac')) s += n.className.replace(/.*led-ac-/, '<') + n.textContent;
    else s += n.textContent;
  }
  return s.trim();
}"""


def lit_pixels(img):
    """Pixels bright enough to be a lit segment (the unlit ones are near black)."""
    im = img.convert('RGB')
    px = im.load()
    w, h = im.size
    return {(x, y) for y in range(h) for x in range(w) if max(px[x, y]) > 150}


def shot(page, box):
    return Image.open(io.BytesIO(page.screenshot(clip=box)))


def check_led(browser):
    failures = []
    b = Board(browser, 'index.html.tmpl')
    t = lambda cid: b.page.evaluate(LED_TEXT, cid)
    b.wait("document.querySelector('#led-t .led-v') && document.querySelector('#led-t .led-v').textContent.trim() === '78.4'")
    for cid, want in (('led-t', '78.4'), ('led-td', '61.2'), ('led-w', '4 NNE'), ('led-g', '9'),
                      ('led-gd', '14'), ('led-b', '29.912'), ('led-rd', '0.00'), ('led-rr', '0.00'),
                      ('led-uv', '5.4'), ('led-rad', '612'), ('led-aqi', '42'), ('led-rh', '56'),
                      ('led-fl', '79.9'), ('led-clk', '4:07:17 PM')):
        if t(cid) != want:
            failures.append('LED %s reads %r, expected %r' % (cid, t(cid), want))
    if b.page.evaluate("document.querySelector('#led-aqi .led-n').style.color") != 'rgb(0, 228, 0)':
        failures.append('the air quality reading is not in its level color')
    if b.page.evaluate("!!document.querySelector('#led-b .led-trend')") is not True:
        failures.append('the barometer has no trend arrow')

    # Aging, then old: the age on the status line, every reading dashes
    # with its decimal point dark.
    b.server.set(age=47)
    b.wait("document.getElementById('led-clock').className.indexOf('led-status-aging') >= 0")
    if t('led-clk') != '47 S AGO':
        failures.append('47 s old reads %r' % t('led-clk'))
    for cid, want in (('led-t', '--_-'), ('led-b', '--_---'), ('led-w', '- ---'), ('led-aqi', '--')):
        if t(cid) != want:
            failures.append('missing %s reads %r, expected %r' % (cid, t(cid), want))
    if b.page.evaluate("!!document.querySelector('#led-b .led-trend')"):
        failures.append('the trend arrow outlived the data')
    failures += led_pixels(b)
    b.server.set(age=420)
    b.wait("document.getElementById('led-clock').className.indexOf('led-status-old') >= 0")
    if t('led-clk') != '7 M AGO':
        failures.append('7 minutes old reads %r' % t('led-clk'))

    # Failures, each on the status line.
    for mode, status, want in (('status', 404, 'HTTP 404'), ('badjson', 200, 'BAD DATA'),
                               ('noentry', 200, 'NO ENTRY'), ('abort', 200, 'NO CONNECT')):
        b.server.set(mode=mode, status=status)
        b.wait("document.getElementById('led-clock').className.indexOf('led-status-error') >= 0"
               " && document.querySelector('#led-clk .led-v').textContent.replace(/\\s/g, '') === %s"
               % json.dumps(want.replace(' ', '')))
    # Back, and a minus sign is the middle segment too.
    b.server.set(e=WIDE)
    b.wait("document.getElementById('led-clock').className === 'led-panel led-status-live'")
    if t('led-t') != '-12.3':
        failures.append('-12.3 reads %r' % t('led-t'))
    if t('led-w') != '112 <slashONN<slashO'.replace('NN', 'N'):
        failures.append('a Danish wind direction reads %r' % t('led-w'))
    failures += accent_pixels(b)
    # A station that reports no gusts shows the highest wind speed instead.
    gustless = entry(**{'10m.windSpeed.max.formatted': '11', 'day.windSpeed.max.formatted': '17'})
    del gustless['10m.windGust.max.formatted']
    del gustless['day.windGust.max.formatted']
    b.server.set(e=gustless)
    b.wait("document.querySelector('#led-g .led-v').textContent.trim() === '11'")
    if t('led-gd') != '17':
        failures.append('with no gusts reported, today reads %r, not the top speed 17' % t('led-gd'))
    # Not-a-number is missing: WeeWX writes N/A for a value it lacks, and a
    # trend code that is not a number draws no arrow.
    b.server.set(e=entry(**{'current.outTemp.formatted': 'N/A', 'current.barometer.formatted': '29.912',
                            'trend.barometer.code': 'x'}))
    b.wait("document.querySelector('#led-t .led-mid') !== null")
    if t('led-t') != '--_-':
        failures.append('an N/A temperature reads %r, not missing' % t('led-t'))
    if b.page.evaluate("!!document.querySelector('#led-b .led-trend')"):
        failures.append('a trend code that is not a number drew an arrow')
    # Calm by the speed as SHOWN: a raw 0.00009 shows as 0, and a direction
    # beside it would claim a wind that is not there.
    b.server.set(e=entry(**{'current.windSpeed.formatted': '0', 'current.windSpeed.raw': 9.1e-05}))
    b.wait("document.querySelector('#led-w .led-v').textContent.trim().charAt(0) === '0'")
    if t('led-w') not in ('0', '0    '.strip()):
        failures.append('a wind that shows 0 reads %r: a direction beside a calm' % t('led-w'))
    failures += ['LED page: %s' % e for e in b.errors]
    b.close()
    return failures


def led_pixels(b):
    """The missing digits and decimal points, measured: each dash lights only
    pixels of its own 8, about one segment in seven; each dark decimal point
    lights nothing."""
    failures = []
    # One dash at a time, the others hidden, in a crop wide enough for the
    # italic 8's lean: each dash against its own full 8, nothing else.
    b.page.add_style_tag(content='.led-v .led-mid { visibility: hidden; }'
                                 ' .led-v .led-mid.probe { visibility: visible; }'
                                 ' .led-title { visibility: hidden; }')   # its red is not a segment
    mids = b.page.query_selector_all('#led-t .led-mid, #led-b .led-mid')
    for m in mids:
        m.evaluate("e => e.classList.add('probe')")
        box = m.bounding_box()
        box = {'x': box['x'] - box['width'] * .5, 'y': box['y'] - box['height'],
               'width': box['width'] * 2, 'height': box['height'] * 3}
        dash = lit_pixels(shot(b.page, box))
        m.evaluate("e => e.style.clipPath = 'none'")
        full = lit_pixels(shot(b.page, box))
        m.evaluate("e => { e.style.clipPath = ''; e.classList.remove('probe'); }")
        share = len(dash) / max(1, len(full))
        if dash - full or not 0.10 < share < 0.20:
            failures.append('a missing digit lights %d pixels outside its 8 and %.2f of it:'
                            ' not its middle segment' % (len(dash - full), share))
        # And it is the MIDDLE one: every lit pixel within the 8's middle
        # band (the segment spans 702 to 936 of the font's 1638 units).
        if dash and full:
            top = min(y for x, y in full)
            height = max(y for x, y in full) - top
            stray = [p for p in dash if not .36 <= (p[1] - top) / height <= .64]
            if stray:
                failures.append('a missing digit lights %d pixels outside the middle band'
                                % len(stray))
    for d in b.page.query_selector_all('#led-t .led-dp-off, #led-b .led-dp-off'):
        if lit_pixels(shot(b.page, d.bounding_box())):
            failures.append('a decimal point is lit with no data')
    if not mids:
        failures.append('no missing digits were drawn')
    return failures


def mark_pixels(b, el):
    """The pixels an accent adds to its base letter, and the letter's box:
    the same crop with the mark and without it."""
    box = el.bounding_box()
    wide = {'x': box['x'] - box['width'], 'y': box['y'] - box['height'],
            'width': box['width'] * 3, 'height': box['height'] * 3}
    with_mark = lit_pixels(shot(b.page, wide))
    el.evaluate("e => e.classList.add('led-ac-none')")
    b.page.add_style_tag(content='.led-ac-none::after { display: none; }')
    bare = lit_pixels(shot(b.page, wide))
    el.evaluate("e => e.classList.remove('led-ac-none')")
    return with_mark - bare, bare, box


def accent_pixels(b):
    """O-slash is the font's O plus a lit slash: a thin stroke, not a block,
    inside the character's own box."""
    failures = []
    acs = b.page.query_selector_all('#led-w .led-ac-slash')
    if len(acs) != 2:
        return ['the Danish direction drew %d slashed Os, expected 2' % len(acs)]
    added, bare, box = mark_pixels(b, acs[0])
    area = box['width'] * box['height']
    if len(added) < 50:
        failures.append('the slash through the O lights only %d pixels' % len(added))
    if len(added) > area * .25:
        failures.append('the slash lights %d pixels, a block rather than a stroke' % len(added))
    inside = [(x, y) for x, y in added if box['width'] * .8 <= x <= box['width'] * 2.2]
    if len(inside) < len(added) * .95:
        failures.append('the slash strays outside its own character')
    return failures


def check_marks_above(browser):
    """A ring and two dots sit ABOVE their letter: Swedish, whose status
    line reads FR<A-ring>NKOPPLAD with no connection and TRYCK H<A-umlaut>R
    once the page has expired -- both steady, so nothing is redrawn while
    they are measured."""
    failures = []
    b = Board(browser, 'index.html.tmpl', lang='sv')
    b.server.set(mode='abort')
    for cls, reach in (('led-ac-ring', None), ('led-ac-uml', 'expirePage()')):
        if reach:
            b.page.evaluate(reach)
        b.wait("document.querySelector('#led-clk .%s')" % cls)
        el = b.page.query_selector('#led-clk .' + cls)
        added, bare, box = mark_pixels(b, el)
        cap = min(y for x, y in bare if box['width'] <= x <= box['width'] * 2) if bare else 0
        if len(added) < 20:
            failures.append('%s adds only %d lit pixels' % (cls, len(added)))
        elif any(y >= cap for x, y in added):
            failures.append('%s lights %d pixels at or below the top of its letter'
                            % (cls, sum(1 for x, y in added if y >= cap)))
        if len(added) > box['width'] * box['height'] * .25:
            failures.append('%s is a block, not a mark' % cls)
    b.close()
    return failures


def check_frozen_file(browser):
    """A file whose timestamp has stopped moving goes stale even though
    every response calls it young: the board counts how long the timestamp
    has sat unchanged, and that alone passes max_age (3 s here)."""
    failures = []
    b = Board(browser, 'index.html.tmpl', overrides={'max_age': '3'})
    b.server.set(e=entry(**{'current.dateTime.raw': int(time.time())}), frozen=True)
    b.wait("document.getElementById('led-clock').className === 'led-panel led-status-live'")
    b.wait("document.getElementById('led-clock').className.indexOf('led-status-aging') >= 0", timeout=8000)
    if b.page.evaluate(LED_TEXT, 'led-t') != '--_-':
        failures.append('a frozen file left the temperature up: %r' % b.page.evaluate(LED_TEXT, 'led-t'))
    b.close()
    return failures


def check_led_expiry(browser):
    """Without the password the page expires, says so, fetches nothing
    more, and a tap starts it again.  (expiration_time is in hours: 0.0006
    is about two seconds.)"""
    failures = []
    b = Board(browser, 'index.html.tmpl', overrides={'expiration_time': '0.0006'}, query='')
    b.wait("document.getElementById('led-clock').className.indexOf('led-status-expired') >= 0")
    if b.page.evaluate(LED_TEXT, 'led-clk') != 'EXPIRED TAP':
        failures.append('an expired page reads %r' % b.page.evaluate(LED_TEXT, 'led-clk'))
    polls = b.server.polls
    b.page.wait_for_timeout(2500)          # proving the ABSENCE of polls
    if b.server.polls != polls:
        failures.append('an expired page went on fetching: %d polls' % (b.server.polls - polls))
    b.page.mouse.click(300, 300)
    b.wait("document.getElementById('led-clock').className === 'led-panel led-status-live'")
    b.close()
    # With the password it does not expire.
    b = Board(browser, 'index.html.tmpl', overrides={'expiration_time': '0.0006'})
    b.wait("document.querySelector('#led-t .led-v') && document.querySelector('#led-t .led-v').textContent.trim() === '78.4'")
    b.page.wait_for_timeout(2600)          # proving the ABSENCE of expiry
    if 'expired' in b.page.evaluate("document.getElementById('led-clock').className"):
        failures.append('a page with the keep-alive password expired')
    b.close()
    return failures


LED_FIT = """() => {
  const bad = [];
  for (const p of document.querySelectorAll('.led-panel')) {
    const P = p.getBoundingClientRect();
    for (const c of p.querySelectorAll('.led-stk, .led-l')) {
      const r = c.getBoundingClientRect();
      if (r.left < P.left - 1 || r.right > P.right + 1 || r.top < P.top - 1 || r.bottom > P.bottom + 1)
        bad.push(p.id);
    }
  }
  // A panel that cannot hold its cells may simply grow past the window's
  // edge, where nothing scrolls to show it: hold every panel, and the
  // footer, inside the window too.
  for (const e of document.querySelectorAll('.led-panel, .led-foot, .led-title')) {
    const r = e.getBoundingClientRect();
    if (r.left < -1 || r.right > innerWidth + 1 || r.top < -1 || r.bottom > innerHeight + 1)
      bad.push((e.id || 'the footer') + ' leaves the window');
  }
  const title = document.querySelector('.led-title');
  if (title && title.scrollHeight > title.clientHeight * 1.08)
    bad.push('the title is squeezed to ' + title.clientHeight + 'px of its ' + title.scrollHeight);
  if (document.documentElement.scrollWidth > innerWidth || document.documentElement.scrollHeight > innerHeight)
    bad.push('the page scrolls');
  return [...new Set(bad)];
}"""

# For each LED row the fit has shrunk: whether it is the LARGEST step that
# fits.  The row is set one step (0.01) larger and measured: a row that
# still fits there was shrunk further than it needed to be.  Measured here,
# independently of the page's own arithmetic.
LED_TIGHT = """() => {
  const need = row => {
    let most = 0;
    for (const p of row.querySelectorAll('.led-panel')) {
      const cs = getComputedStyle(p);
      const iw = p.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
      const ih = p.clientHeight - parseFloat(cs.paddingTop) - parseFloat(cs.paddingBottom);
      const cells = [...p.querySelectorAll('.led-c')];
      let w = 0, h = 0;
      for (const c of cells) { const r = c.getBoundingClientRect(); w += r.width; h = Math.max(h, r.height); }
      w += Math.max(0, cells.length - 1) * parseFloat(cs.columnGap);
      most = Math.max(most, w / iw, h / ih);
    }
    return most;
  };
  const out = [];
  for (const row of document.querySelectorAll('.led-row')) {
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
    for tmpl, check, sel in (('index.html.tmpl', LED_FIT, '.led-title'), ('splitflap.html.tmpl', FLAP_FIT, '#flap-title')):
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
# none between the LED panels' cells and reports it as "normal", which is
# not a number.
GAP_NORMAL = """(() => {
  document.addEventListener('DOMContentLoaded', () => {
    const st = document.createElement('style');
    st.textContent = '.led-panel { gap: 0 !important; }';
    document.head.appendChild(st);
  });
  const real = window.getComputedStyle;
  window.getComputedStyle = function (el, pseudo) {
    const cs = real.call(window, el, pseudo);
    if (!el.classList || !el.classList.contains('led-panel')) return cs;
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


def check_led_without_font_api(browser):
    """Without document.fonts the LED board still measures its font's
    baseline, at window load -- or on its timers, when a hung analytics
    script means window load never comes -- and gets the same answer: the
    dashes and accents are placed from it."""
    failures = []
    want = None
    for font_api, hang in ((True, False), (False, False), (False, True)):
        b = Board.__new__(Board)
        b.server = Server(ct.render('index.html.tmpl', analytics=hang, overrides={'refresh_rate': '1'}))
        b.errors = []
        b.page = browser.new_page(viewport={'width': 1280, 'height': 800})
        if not font_api:
            b.page.add_init_script(NO_FONT_API)
        b.page.route('**/*', hang_analytics(b.server.handle) if hang else b.server.handle)
        b.page.goto('http://board.test/board.html?page_update_pwd=testpwd',
                    wait_until='domcontentloaded' if hang else 'load')
        b.wait("document.documentElement.style.getPropertyValue('--led-bl') !== ''")
        bl = b.page.evaluate("document.documentElement.style.getPropertyValue('--led-bl')")
        if want is None:
            want = bl
        elif bl != want:
            failures.append('without document.fonts the baseline is %s, with it %s' % (bl, want))
        b.close()
    return failures


def check_font_late_without_load(browser):
    """Without document.fonts, with the analytics script hung so window
    load never comes, and each board's font held back eight seconds: the
    LED board still ends on the font's own baseline, and the split-flap
    board refits to the font once it arrives.  Both pages load together
    and the fonts are released from here, so the wait is paid once."""
    failures = []
    ref = Board(browser, 'index.html.tmpl')
    ref.wait("document.documentElement.style.getPropertyValue('--led-bl') !== ''")
    want = ref.page.evaluate("document.documentElement.style.getPropertyValue('--led-bl')")
    ref.close()
    held = []

    def holding(handle, font):
        def route(r, request):
            if request.url.endswith(font):
                held.append((r, handle))
                return None
            return handle(r, request)
        return hang_analytics(route)

    led = Board.__new__(Board)
    led.server = Server(ct.render('index.html.tmpl', analytics=True, overrides={'refresh_rate': '1'}))
    led.errors = []
    led.page = browser.new_page(viewport={'width': 1280, 'height': 800})
    led.page.add_init_script(NO_FONT_API)
    led.page.route('**/*', holding(led.server.handle, 'lcdmono2ultra-webfont.ttf'))
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
    for b in (led, flap):
        b.page.goto('http://board.test/board.html?page_update_pwd=testpwd', wait_until='domcontentloaded')
    # Past the old six-second timer, with the fonts still held: the LED
    # board has only the fallback font to measure, so its baseline must
    # differ, or this test is not testing anything.
    led.page.wait_for_timeout(max(0, 7000 - (time.time() - start) * 1000))
    early = led.page.evaluate("document.documentElement.style.getPropertyValue('--led-bl')")
    if early == want:
        failures.append('the fallback font measured the same baseline as the real one: the test proves nothing')
    led.page.wait_for_timeout(max(0, 8000 - (time.time() - start) * 1000))
    for r, handle in held:
        handle(r, r.request)
    try:
        led.wait("document.documentElement.style.getPropertyValue('--led-bl') === %s" % json.dumps(want), timeout=4000)
    except Exception:
        failures.append('a font arriving after eight seconds left the baseline at %s, not %s'
                        % (led.page.evaluate("document.documentElement.style.getPropertyValue('--led-bl')"), want))
    try:
        flap.wait("""(() => { const b = document.getElementById('flap-board').getBoundingClientRect(),
            f = document.getElementById('flap-foot').getBoundingClientRect();
            return Math.max(b.width * 1.02 / innerWidth, (b.height + f.height) * 1.04 / innerHeight) >= 0.98; })()""",
                  timeout=4000)
    except Exception:
        failures.append('a font arriving after eight seconds: the split-flap board was never refitted to it')
    for p in flap.page.evaluate(FLAP_FIT):
        failures.append('a font arriving after eight seconds: %s' % p)
    led.close()
    flap.close()
    return failures


def check_led_fit_gap_normal(browser):
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
    b.wait("document.querySelector('#led-t .led-v') && document.querySelector('#led-t .led-v').textContent.indexOf('112.34') >= 0")
    b.page.evaluate('new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))')
    fits = b.page.evaluate("[...document.querySelectorAll('.led-row')].map(r => r.style.getPropertyValue('--fit') || '1')")
    if all(f == '1' for f in fits):
        failures.append('with the gap reported as "normal" no row shrank: %s' % fits)
    for p in b.page.evaluate(LED_FIT):
        failures.append('with the gap reported as "normal": %s overflows' % p)
    b.close()
    return failures


def check_fit(browser):
    """Both boards, at every size, with the widest readings, in English and
    in the language with the longest words.  One page per board and
    language, resized: the fit reruns on every resize."""
    failures = []
    for lang in ('en', 'nl'):
        led = Board(browser, 'index.html.tmpl', size=SIZES[0], lang=lang)
        led.server.set(e=WIDE)
        led.wait("document.querySelector('#led-t .led-v') && document.querySelector('#led-t .led-v').textContent.indexOf('12.3') >= 0")
        flap = Board(browser, 'splitflap.html.tmpl', size=SIZES[0], lang=lang)
        flap.wait("document.querySelector('#flap-temp .flap')")
        for size in SIZES:
            for b in (led, flap):
                b.page.set_viewport_size({'width': size[0], 'height': size[1]})
                b.page.evaluate('new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))')
            for p in led.page.evaluate(LED_FIT):
                failures.append('LED %s %dx%d: %s overflows' % (lang, size[0], size[1], p))
            for p in flap.page.evaluate(FLAP_FIT):
                failures.append('split-flap %s %dx%d: %s' % (lang, size[0], size[1], p))
        # The fit counts the cells and nothing else: a panel with room to
        # spare is not shrunk by its hidden heading.  At 1024x768, where the
        # title's line leaves height to spare, everyday readings keep every
        # row at its full size.  (At 16:10 the title's line comes out of
        # the temperature row: that is its cost.)
        led.server.set()
        led.page.set_viewport_size({'width': 1024, 'height': 768})
        led.wait("document.querySelector('#led-t .led-v').textContent.indexOf('78.4') >= 0")
        led.page.evaluate('new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))')
        if lang == 'en':
            fits = led.page.evaluate("[...document.querySelectorAll('.led-row')].map(r => r.style.getPropertyValue('--fit') || '1')")
            if any(f != '1' for f in fits):
                failures.append('everyday English readings shrank a row at 1024x768: %s' % fits)
        # The case that needs the fit: at 1024x768 every panel still holds.
        led.server.set(e=EXTREME)
        led.wait("document.querySelector('#led-t .led-v').textContent.indexOf('112.34') >= 0")
        led.page.set_viewport_size({'width': 1024, 'height': 768})
        led.page.evaluate('new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))')
        for p in led.page.evaluate(LED_FIT):
            failures.append('LED %s, readings too wide for the design: %s overflows' % (lang, p))
        tight = led.page.evaluate(LED_TIGHT)
        if not tight:
            failures.append('LED %s: readings too wide for the design shrank no row' % lang)
        for fit, at, above in tight:
            if at > 1.001:
                failures.append('LED %s: a row at %.2f is %.3f full, overflowing' % (lang, fit, at))
            if above <= 1.001:
                failures.append('LED %s: a row at %.2f would still fit a step larger (%.3f full'
                                ' there): the fit shrank it further than it needed' % (lang, fit, above))
        led.close()
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
    b.wait("document.querySelector('#led-clk .led-v') && document.querySelector('#led-clk .led-v').textContent.trim() === '16:07:17'")
    b.server.set(age=47)
    b.wait("document.getElementById('led-clock').className.indexOf('aging') >= 0")
    if b.page.evaluate(LED_TEXT, 'led-clk') != '47 S SIDEN':
        failures.append('Danish 47 s old reads %r' % b.page.evaluate(LED_TEXT, 'led-clk'))
    failures += ['Danish LED page: %s' % e for e in b.errors]
    b.close()
    b = Board(browser, 'index.html.tmpl', overrides={'clock_format': '24'})
    b.wait("document.querySelector('#led-clk .led-v') && document.querySelector('#led-clk .led-v').textContent.trim() === '16:07:17'")
    b.close()
    return failures


def main():
    start = time.time()
    ok = True
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for name, fn in (('the LED board: readings, status line, missing data in pixels', check_led),
                         ('the LED board: expiry, the tap, and the keep-alive password', check_led_expiry),
                         ('a file that stops changing goes stale', check_frozen_file),
                         ('the split-flap board: rows, lamps, missing data, failures', check_flap),
                         ('the clock and status line in other languages', check_languages),
                         ('accents drawn above their letters', check_marks_above),
                         ('both boards fit every screen size, metric and in Dutch', check_fit),
                         ('the split-flap board refits once its font has loaded', check_flap_late_font),
                         ('without document.fonts, window load or not: the LED baseline, the split-flap refit',
                          lambda br: check_led_without_font_api(br) + check_flap_late_font(br, font_api=False)
                          + check_flap_late_font(br, font_api=False, hang=True)),
                         ('the LED fit, in a browser that reports its gap as "normal"', check_led_fit_gap_normal),
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
