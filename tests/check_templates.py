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

It also checks that install.py's LOOP_DATA_FIELDS/PURPLE_FIELDS -- the
fields the installer adds to weewx.conf -- are exactly the loopdata fields
the updaters read.  A field the updaters read but the installer does not
add arrives as question marks on a fresh install; a field the installer
adds that nothing reads is dead weight on the user's fields line.

Run with a Python that has Cheetah installed, e.g. the WeeWX venv:

  PYTHONDONTWRITEBYTECODE=1 /home/weewx/weewx-venv/bin/python3 tests/check_templates.py

This is a static check only: it proves the templates generate well-formed
pages, not that the updater behaves.  Behavior is verified by loading the
generated pages in a browser.
"""

import ast
import io
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

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIN = os.path.join(REPO, 'skins', 'WeatherBoard')
INSTALL = os.path.join(REPO, 'install.py')


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
        'max_age': 10,
        'clock_max_age': 120,
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


def check(html, show_purple):
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
    # The show_purple gate itself.  The id check above cannot see this
    # crossing: <td id="aqi"> is unconditional in footer.inc, so if the gate
    # ever resolved the wrong way the whole AQI updater block would vanish
    # and every other check here would still pass.  The reading's own field
    # names appear only inside that block, so their presence is the gate.
    has_aqi_js = 'pm2_5' in html
    if show_purple and not has_aqi_js:
        failures.append('show_purple is on but no AQI updater code was rendered')
    if not show_purple and has_aqi_js:
        failures.append('show_purple is off but AQI updater code was rendered')
    return failures


def installer_field_lists():
    """install.py's LOOP_DATA_FIELDS and PURPLE_FIELDS, read without
    importing it: install.py imports weectl's 'setup' module, which only
    exists inside weectl."""
    lists = {}
    for node in ast.parse(io.open(INSTALL, encoding='utf-8').read()).body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id in (
                    'LOOP_DATA_FIELDS', 'PURPLE_FIELDS'):
                lists[target.id] = [ast.literal_eval(e) for e in node.value.elts]
    return lists


def fields_read_by_updaters():
    """Every loopdata field the javascript looks up in the poll result.

    Catches result["field"] directly, and result[someVar] by resolving
    someVar's literal in the same file -- which is how the clock field,
    current.dateTime.format("%X"), is read."""
    direct = re.compile(r"""result\[\s*(?:"([^"]+)"|'([^']+)')\s*\]""")
    indirect = re.compile(r"""result\[\s*([A-Za-z_$][\w$]*)\s*\]""")
    fields = set()
    for name in sorted(os.listdir(SKIN)):
        if not (name.endswith('.inc') or name.endswith('.tmpl')):
            continue
        src = io.open(os.path.join(SKIN, name), encoding='utf-8').read()
        for dq, sq in direct.findall(src):
            fields.add(dq or sq)
        for var in indirect.findall(src):
            assign = re.search(
                r"""\b(?:var|let|const)\s+%s\s*=\s*(?:"([^"]+)"|'([^']+)')"""
                % re.escape(var), src)
            if assign:
                fields.add(assign.group(1) or assign.group(2))
            else:
                fields.add('<unresolved variable %s in %s>' % (var, name))
    return fields


def check_installer_fields():
    """The installer's field lists must match what the updaters read."""
    lists = installer_field_lists()
    failures = []
    for name in ('LOOP_DATA_FIELDS', 'PURPLE_FIELDS'):
        if name not in lists:
            failures.append('install.py has no %s list' % name)
    if failures:
        return failures
    declared = lists['LOOP_DATA_FIELDS'] + lists['PURPLE_FIELDS']
    if len(set(declared)) != len(declared):
        failures.append('duplicate entries in install.py field lists')
    read = fields_read_by_updaters()
    unresolved = sorted(f for f in read if f.startswith('<unresolved'))
    if unresolved:
        failures.append('cannot resolve field name(s): %s' % unresolved)
        read = set(read) - set(unresolved)
    missing = sorted(read - set(declared))
    if missing:
        failures.append('read by the updaters, not added by install.py: %s' % missing)
    unread = sorted(set(declared) - read)
    if unread:
        failures.append('added by install.py, read by nothing: %s' % unread)
    # AQI fields belong in the purple list: they are added only for a
    # station with show_purple set.
    for field in lists['LOOP_DATA_FIELDS']:
        if 'aqi' in field:
            failures.append('%s belongs in PURPLE_FIELDS' % field)
    for field in lists['PURPLE_FIELDS']:
        if 'aqi' not in field:
            failures.append('%s does not look like an AQI field' % field)
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
            failures = check(html, purple)
            print('%s %s' % ('FAIL' if failures else 'ok  ', name))
            for f in failures:
                print('       - %s' % f)
            ok = ok and not failures
    failures = check_installer_fields()
    print('%s install.py loopdata fields match the updaters'
          % ('FAIL' if failures else 'ok  '))
    for f in failures:
        print('       - %s' % f)
    ok = ok and not failures
    sys.exit(0 if ok else 1)


main()
