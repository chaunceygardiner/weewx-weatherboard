# Copyright (C)2026 by John A Kline <john@johnkline.com>
# Distributed under the terms of the GNU Public License (GPLv3)
# See LICENSE for your rights.
"""Offline check for the WeatherBoard templates.

Renders every *.html.tmpl in the skin with a stub searchList (both
show_purple settings) and validates the output:

  - templates render without Cheetah errors
  - every element id referenced by getElementById exists in the HTML
  - no unrendered $Extras/$current/... placeholders leak into the output
  - no inline style= attributes (all CSS belongs in weatherboard.css)
  - every <script> parses as valid JavaScript (needs the pure-Python
    'esprima' package; that check is skipped with a warning if absent)

Run with a Python that has Cheetah installed, e.g. the WeeWX venv:

  PYTHONDONTWRITEBYTECODE=1 /home/weewx/weewx-venv/bin/python3 tests/check_templates.py

This is a static check only: it proves the templates generate well-formed
pages, not that the updater behaves.  Behavior is verified by loading the
generated pages in a browser.
"""

import os
import re
import sys

try:
    from Cheetah.Template import Template
except ImportError:
    sys.exit("Cheetah is required (run with the WeeWX venv's python).")

try:
    import esprima
except ImportError:
    esprima = None

SKIN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    'skins', 'WeatherBoard')


class Tag:
    """Stub for WeeWX tags: $current.outTemp, $obs.label.foo, etc."""
    def __init__(self, s='54.9°F'):
        self._s = s

    def __getattr__(self, name):
        if name.startswith('__'):
            raise AttributeError(name)
        return self

    def __call__(self, *args, **kwargs):
        return self

    def __str__(self):
        return self._s


class Extras(dict):
    """WeeWX Extras sections still answer the py2-era has_key()."""
    def has_key(self, k):
        return k in self


def make_extras(show_purple):
    return Extras({
        'meta_title': 'Test WeatherBoard',
        'title': 'Test WeatherBoard&trade;',
        'subtitle': 'Updated continuously.',
        'logo': 'logo.png',
        'loop_data_file': 'loop-data.txt',
        'in_temp_file': 'inTemp.txt',
        'in_co2_file': 'inCO2.txt',
        'in_aqi_file': 'inAQI.txt',
        'in_file_max_age': 120,
        'in_file_slow_host': 'www.example.com',
        'in_file_slow_max_age': 360,
        'refresh_rate': 2,
        'expiration_time': 4,
        'page_update_pwd': 'testpwd',
        'show_purple': 'True' if show_purple else 'False',
    })


def render(tmpl, show_purple):
    ns = {
        'Extras': make_extras(show_purple),
        'current': Tag(),
        'day': Tag(),
        'station': Tag('Test Station'),
        'obs': Tag('SomeLabel'),
    }
    # #include paths resolve relative to the CWD.
    os.chdir(SKIN)
    return str(Template(file=os.path.join(SKIN, tmpl), searchList=[ns]))


def check(html):
    failures = []
    scripts = re.findall(r'<script>(.*?)</script>', html, re.S)
    if not scripts:
        failures.append('no <script> blocks found')
    js_all = ''.join(scripts)
    if esprima:
        for i, js in enumerate(scripts):
            try:
                esprima.parseScript(js)
            except Exception as e:
                failures.append('script %d: JS parse error: %s' % (i, e))
    used = set(re.findall(r'getElementById\("([^"]+)"\)', js_all))
    declared = set(re.findall(r'id=["\']([^"\']+)["\']', html))
    missing = used - declared
    if missing:
        failures.append('JS references missing ids: %s' % sorted(missing))
    # $24h... is included deliberately: it is NOT a valid Cheetah placeholder
    # (digit start) and renders as literal text if put in a template.
    leaks = re.findall(
        r'\$Extras[.\w]*|\$current[.\w]*|\$day[.\w]*|\$obs[.\w]*|\$24h[.\w]*|\$station[.\w]*',
        html)
    if leaks:
        failures.append('unrendered placeholders: %s' % sorted(set(leaks)))
    inline = re.findall(r'style="[^"]*"', html)
    if inline:
        failures.append('inline styles (move to weatherboard.css): %s' % inline[:5])
    return failures


def main():
    if esprima is None:
        print('WARNING: esprima not importable; skipping JS syntax checks.')
        print('         (pip install esprima to a dir on PYTHONPATH -- never into the venv.)')
    ok = True
    templates = sorted(f for f in os.listdir(SKIN) if f.endswith('.html.tmpl'))
    if not templates:
        sys.exit('no *.html.tmpl files found in %s' % SKIN)
    for tmpl in templates:
        for purple in (True, False):
            name = '%s show_purple=%s' % (tmpl, purple)
            try:
                html = render(tmpl, purple)
            except Exception as e:
                print('FAIL %s: render error: %s' % (name, e))
                ok = False
                continue
            failures = check(html)
            print('%s %s' % ('FAIL' if failures else 'ok  ', name))
            for f in failures:
                print('       - %s' % f)
            ok = ok and not failures
    sys.exit(0 if ok else 1)


main()
