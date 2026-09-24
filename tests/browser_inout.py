# Copyright (C)2026 by John A Kline <john@johnkline.com>
# Distributed under the terms of the GNU Public License (GPLv3)
# See LICENSE for your rights.
"""inout.html, the indoor readout board (paloaltoweather branch only), run in
a real browser the way tests/browser_check.py runs the other two boards,
and with its harness: the page, the skin's stylesheets and fonts, the loop
data AND the four sidecar files are all answered from here.

What it holds the page to:

  - every reading shows what the loop data and the sidecar files say: the
    indoor temperature, the solar array in kW, CO2 and indoor AQI in the
    colors their files give them
  - a failed fetch -- a missing file, one that is not json, or one
    lacking its fields -- leaves the last good reading up until it is
    older than its own max age, then dashes, CO2 and indoor AQI in white;
    a file whose reading is already too old is dashes at once; and the
    rest of the board carries on
  - a sidecar reading's age keeps counting between polls: it goes to
    dashes on its own, with no new fetch
  - an expired page fetches no sidecar file, and the tap that restarts it
    fetches them at once
  - the page fits every screen size with the widest readings

Run with the same Python as browser_check.py:

  PYTHONDONTWRITEBYTECODE=1 tools/pwenv/bin/python tests/browser_inout.py
"""
import email.utils
import json
import sys
import time
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import browser_check as bc                                # noqa: E402
import check_templates as ct                              # noqa: E402
from playwright.sync_api import sync_playwright           # noqa: E402

TMPL = 'inout.html.tmpl'
FILES = {'inTemp.txt': 'inTemp', 'inCO2.txt': 'inCO2', 'inAQI.txt': 'inAQI',
         'solar-array.json': 'solar'}


def sidecars(**over):
    """The four documents, as the site's plumbing writes them.  A value of
    None for one of them serves a 404."""
    now = time.time()
    docs = {'inTemp': {'ts': int(now), 'inTemp': 73.8},
            'inCO2': {'ts': int(now), 'inCO2': 450.0, 'inColor': 'rgb(0,200,0)'},
            'inAQI': {'ts': int(now), 'inAQI': 29, 'inColor': 'rgb(0,228,0)'},
            'solar': {'total_watts': 2583, 'total_timestamp': now}}
    docs.update(over)
    return docs


class Server(bc.Server):
    """browser_check's server, answering the sidecar files too.  Each
    document is served with a Date header of now, so its age is how far
    its own timestamp lags."""
    def __init__(self, html):
        super().__init__(html)
        self.docs = sidecars()
        self.fetches = {k: 0 for k in FILES.values()}

    def handle(self, route, request):
        path = request.url.split('://', 1)[1].split('/', 1)[1].split('?')[0]
        if path not in FILES:
            return super().handle(route, request)
        name = FILES[path]
        self.fetches[name] += 1
        doc = self.docs.get(name)
        if doc is None:
            return route.fulfill(status=404, body='')
        body = doc if isinstance(doc, str) else json.dumps(doc)
        return route.fulfill(body=body, headers={'Date': email.utils.formatdate(time.time(), usegmt=True),
                                                 'Content-Type': 'application/json'})


class Board(bc.Board):
    """browser_check's Board, on inout.html and this server."""
    def __init__(self, browser, size=(1280, 800), overrides=None, docs=None,
                 query='?page_update_pwd=testpwd', missing=ct.ALL_PRESENT):
        extras = {'refresh_rate': '1', 'in_temp_file': 'inTemp.txt', 'in_co2_file': 'inCO2.txt',
                  'in_aqi_file': 'inAQI.txt', 'solar_array_file': 'solar-array.json'}
        extras.update(overrides or {})
        self.server = Server(ct.render(TMPL, missing, analytics=False, overrides=extras))
        if docs is not None:
            self.server.docs = docs
        self.page = browser.new_page(viewport={'width': size[0], 'height': size[1]})
        self.errors = []
        self.page.on('pageerror', lambda e: self.errors.append(str(e)))
        self.page.route('**/*', self.server.handle)
        self.page.goto('http://board.test/board.html' + query)
        self.page.evaluate('document.fonts.ready')

    def text(self, cid):
        return self.page.evaluate(bc.RO_TEXT, cid)

    def wait_text(self, cid, want, timeout=6000):
        """Until the cell reads want, as RO_TEXT reads it."""
        self.page.wait_for_function('([id, want]) => (%s)(id) === want' % bc.RO_TEXT,
                                    arg=[cid, want], timeout=timeout)

    def color(self, cid):
        return self.page.evaluate("id => getComputedStyle(document.querySelector('#' + id + ' .ro-n')).color", cid)


def check_readings(browser):
    """Every cell, from the loop data and the files; then each way a file
    can fail, with the board carrying on around it."""
    failures = []
    b = Board(browser)
    b.wait("document.querySelector('#ro-sol .ro-v') && document.querySelector('#ro-sol .ro-v').textContent.trim() === '2.6'")
    b.wait("document.querySelector('#ro-t .ro-v').textContent.trim() === '78.4'")
    for cid, want in (('ro-t', '78.4'), ('ro-td', '61.2'), ('ro-in', '73.8'), ('ro-w', '4 NNE'),
                      ('ro-g', '9'), ('ro-gd', '14'), ('ro-b', '29.912'), ('ro-uv', '5.4'),
                      ('ro-rad', '612'), ('ro-sol', '2.6'), ('ro-rd', '0.00'), ('ro-r24', '0.00'),
                      ('ro-rr', '0.00'), ('ro-co2', '450'), ('ro-iaq', '29'), ('ro-aqi', '42'),
                      ('ro-clk', '4:07:17 PM')):
        if b.text(cid) != want:
            failures.append('%s reads %r, expected %r' % (cid, b.text(cid), want))
    for cid, want in (('ro-co2', 'rgb(0, 200, 0)'), ('ro-iaq', 'rgb(0, 228, 0)'),
                      ('ro-aqi', 'rgb(0, 228, 0)'), ('ro-in', 'rgb(255, 45, 31)')):
        if b.color(cid) != want:
            failures.append('%s is %s, expected %s' % (cid, b.color(cid), want))
    # Each failure, one file at a time, the next poll forced through the
    # page's own pollSidecars rather than waited out.  A failed fetch
    # leaves the good reading up; the reading is then aged past its limit
    # -- its arrival moved back, and the page repainted -- and must go to
    # dashes, CO2 and indoor AQI in white.
    kept = {'inTemp': ('ro-in', '73.8', '--_-', False), 'inCO2': ('ro-co2', '450', '---', True),
            'inAQI': ('ro-iaq', '29', '--', True), 'solar': ('ro-sol', '2.6', '-_-', False)}
    for what, name, doc in (
            ('a missing file', 'inTemp', None),
            ('a file that is not json', 'inCO2', '{not json'),
            ('a file without its value', 'inAQI', {'ts': int(time.time()), 'inColor': 'rgb(0,228,0)'}),
            ('a file without its color', 'inCO2', {'ts': int(time.time()), 'inCO2': 450.0}),
            ('a file without a timestamp', 'inTemp', {'inTemp': 73.8}),
            ('a file that is not a number', 'solar', {'total_watts': 'n/a', 'total_timestamp': time.time()})):
        cid, good, dashes, white = kept[name]
        b.server.docs = sidecars(**{name: doc})
        before = b.server.fetches[name]
        b.page.evaluate('pollSidecars()')
        b.page.wait_for_timeout(300)
        if b.server.fetches[name] != before + 1:
            failures.append('%s: the forced poll fetched %s %d times' % (what, name, b.server.fetches[name] - before))
        if b.text(cid) != good:
            failures.append('%s: %s reads %r at once, expected the last good %r'
                            % (what, cid, b.text(cid), good))
        b.page.evaluate('k => { SIDECARS[k].at -= 1e7; repaint(); }', name)
        if b.text(cid) != dashes:
            failures.append('%s: %s reads %r once too old, expected %r' % (what, cid, b.text(cid), dashes))
        if white and b.color(cid) != 'rgb(255, 255, 255)':
            failures.append('%s: %s is %s with no data, expected white' % (what, cid, b.color(cid)))
        if b.text('ro-t') != '78.4':
            failures.append('%s stopped the rest of the board: ro-t reads %r' % (what, b.text('ro-t')))
        b.server.docs = sidecars()
        b.page.evaluate('pollSidecars()')
        b.wait_text(cid, good)
    # A file that answers, but with a reading already past its limit, is
    # dashes at once; one a few watts below zero is 0.0, never -0.0.
    old = int(time.time()) - 200
    for what, doc, want in (('a file older than its max age', {'total_watts': 2583, 'total_timestamp': old}, '-_-'),
                            ('inverter noise below zero', {'total_watts': -3, 'total_timestamp': time.time()}, '0.0')):
        b.server.docs = sidecars(solar=doc)
        b.page.evaluate('pollSidecars()')
        try:
            b.wait_text('ro-sol', want, timeout=3000)
        except Exception:
            failures.append('%s: ro-sol reads %r, expected %r' % (what, b.text('ro-sol'), want))
        b.server.docs = sidecars()
        b.page.evaluate('pollSidecars()')
        b.wait_text('ro-sol', '2.6')
    failures += ['page error: %s' % e for e in b.errors]
    b.close()
    return failures


def check_age_between_polls(browser):
    """A reading one second old with a three-second limit goes to dashes
    about two seconds later, with no fetch in between."""
    failures = []
    b = Board(browser, overrides={'in_temp_max_age': '3'},
              docs=sidecars(inTemp={'ts': int(time.time()) - 1, 'inTemp': 73.8}))
    b.wait("document.querySelector('#ro-in .ro-v') && document.querySelector('#ro-in .ro-v').textContent.trim() === '73.8'")
    fetched = b.server.fetches['inTemp']
    b.wait("(%s)('ro-in') === '--_-'" % bc.RO_TEXT, timeout=5000)
    if b.server.fetches['inTemp'] != fetched:
        failures.append('the reading went stale only after another fetch')
    if b.text('ro-t') != '78.4':
        failures.append('the outdoor temperature went with it: %r' % b.text('ro-t'))
    b.close()
    return failures


def check_expiry(browser):
    """An expired page polls no sidecar file, and the tap that restarts it
    polls all four at once.  (expiration_time is in hours: 0.0006 is about
    two seconds.)"""
    failures = []
    b = Board(browser, overrides={'expiration_time': '0.0006'}, query='')
    b.wait("document.getElementById('ro-clock').className.indexOf('ro-status-expired') >= 0", timeout=8000)
    before = dict(b.server.fetches)
    b.page.evaluate('pollSidecars()')
    b.page.wait_for_timeout(300)
    if b.server.fetches != before:
        failures.append('an expired page fetched the sidecar files: %s -> %s' % (before, b.server.fetches))
    b.page.mouse.click(10, 10)
    b.wait("document.getElementById('ro-clock').className.indexOf('ro-status-expired') < 0")
    b.page.wait_for_timeout(300)
    for name, n in sorted(b.server.fetches.items()):
        if n != before[name] + 1:
            failures.append('the tap fetched %s %d times, expected once' % (name, n - before[name]))
    b.close()
    return failures


def check_fit(browser):
    """Every size, the widest readings, sidecars at their widest too."""
    failures = []
    wide = sidecars(inTemp={'ts': int(time.time()), 'inTemp': -12.3},
                    inCO2={'ts': int(time.time()), 'inCO2': 4800, 'inColor': 'rgb(143,63,151)'},
                    inAQI={'ts': int(time.time()), 'inAQI': 458, 'inColor': 'rgb(126,0,35)'},
                    solar={'total_watts': 12345, 'total_timestamp': time.time()})
    b = Board(browser, size=bc.SIZES[0], docs=wide)
    b.server.set(e=bc.WIDE)
    b.wait("document.querySelector('#ro-co2 .ro-v') && document.querySelector('#ro-co2 .ro-v').textContent.trim() === '4800'")
    b.wait("document.querySelector('#ro-t .ro-v').textContent.indexOf('12.3') >= 0")
    for size in bc.SIZES:
        b.page.set_viewport_size({'width': size[0], 'height': size[1]})
        b.page.evaluate('new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))')
        for p in b.page.evaluate(bc.RO_FIT):
            failures.append('%dx%d: %s overflows' % (size[0], size[1], p))
    b.close()
    return failures


def main():
    start = time.time()
    ok = True
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for name, fn in (('inout.html: readings, colors, and each way a file fails', check_readings),
                         ('inout.html: a sidecar reading ages between polls', check_age_between_polls),
                         ('inout.html: no sidecar polls while expired; the tap polls at once', check_expiry),
                         ('inout.html fits every screen size', check_fit)):
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
