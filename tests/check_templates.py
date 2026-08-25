# Copyright (C)2026 by John A Kline <john@johnkline.com>
# Distributed under the terms of the GNU Public License (GPLv3)
# See LICENSE for your rights.
"""Offline check for the WeatherBoard templates.

Renders every *.html.tmpl in the skin with a stub searchList (both
show_purple settings crossed with both title_theme settings) and
validates the output:

  - templates render without Cheetah errors
  - every element id referenced by getElementById exists in the HTML
  - no unrendered $Extras/$current/... placeholders leak into the output
  - no inline style= attributes (all CSS belongs in weatherboard.css)
  - every <script> parses as valid JavaScript (needs the pure-Python
    'esprima' package; the ordinary renders skip this with a warning if it
    is absent, but the hostile-Extras render FAILS without it -- parsing is
    the whole point of that check, so esprima is required for a pass)

It also checks that install.py's LOOP_DATA_FIELDS/PURPLE_FIELDS -- the
fields the installer adds to weewx.conf -- are exactly the loopdata fields
the updaters read.  A field the updaters read but the installer does not
add arrives as question marks on a fresh install; a field the installer
adds that nothing reads is dead weight on the user's fields line.

Run with a Python that has Cheetah installed, e.g. the WeeWX venv, with
esprima somewhere on PYTHONPATH (never installed into the venv itself):

  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/path/with/esprima \\
      /home/weewx/weewx-venv/bin/python3 tests/check_templates.py

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
    """Stub for WeeWX tags: $current.outTemp, $obs.label.foo, etc.

    .raw renders as a bare number and the numeric operators are defined
    because logo.inc embeds tag values in JavaScript ('54.9°F' there
    would be an esprima parse error) and compares/divides them in
    Cheetah (#if a.raw >= b.raw, $almanac.moon.phase / 100.0).
    """
    def __init__(self, s='54.9°F'):
        self._s = s

    def __getattr__(self, name):
        if name.startswith('__'):
            raise AttributeError(name)
        if name == 'raw':
            return Tag('4.2')
        return self

    def __call__(self, *args, **kwargs):
        return self

    def __str__(self):
        return self._s

    def __ge__(self, other):
        return False

    def __truediv__(self, other):
        return 0.42


class Extras(dict):
    """WeeWX Extras sections still answer the py2-era has_key()."""
    def has_key(self, k):
        return k in self


def make_extras(show_purple, title_theme, analytics=True, overrides=None):
    extras = {
        'title_theme': title_theme,
        'meta_title': 'Test WeatherBoard',
        'title': 'Test WeatherBoard&trade;',
        'subtitle': 'Updated continuously.',
        'loop_data_file': 'loop-data.txt',
        'max_age': 10,
        'clock_max_age': 120,
        'in_temp_file': 'inTemp.txt',
        'in_co2_file': 'inCO2.txt',
        'in_aqi_file': 'inAQI.txt',
        'in_temp_max_age': 120,
        'in_co2_max_age': 120,
        'in_aqi_max_age': 120,
        'solar_array_max_age': 150,
        'refresh_rate': 2,
        'expiration_time': 4,
        'page_update_pwd': 'testpwd',
        'show_purple': 'True' if show_purple else 'False',
    }
    # analytics.inc renders its body only when both keys are present, and
    # the escaping there is exercised only then; the render without them is
    # the one every station without Google Analytics gets.  Both paths are
    # checked (see main).
    if analytics:
        extras['googleAnalyticsId'] = 'G-TESTID0001'
        extras['analytics_host'] = 'example.com'
    if overrides:
        extras.update(overrides)
    return Extras(extras)


def render(tmpl, show_purple, title_theme, analytics=True, overrides=None):
    ns = {
        'Extras': make_extras(show_purple, title_theme, analytics, overrides),
        'current': Tag(),
        'day': Tag(),
        'station': Tag('Test Station'),
        'obs': Tag('SomeLabel'),
        # logo.inc embeds almanac values in JavaScript: bare number.
        'almanac': Tag('42.0'),
    }
    # #include paths resolve relative to the CWD.
    os.chdir(SKIN)
    return str(Template(file=os.path.join(SKIN, tmpl), searchList=[ns]))


def check(html, mono, show_purple):
    failures = []
    # The mono theme is body class + repaint script; color is neither.
    for token in ('class="title-mono"', 'paw_logo_mono.js'):
        if (token in html) != mono:
            failures.append('%s %s for title_theme=%s' % (
                token, 'missing' if mono else 'present', 'mono' if mono else 'color'))
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
        r'\$Extras[.\w]*|\$current[.\w]*|\$day[.\w]*|\$obs[.\w]*|\$24h[.\w]*'
        r'|\$station[.\w]*|\$almanac[.\w]*|\$pl_\w+|\$jsstr\(',
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
    # The standalone .js files (the live logo) receive the loop-data object
    # as a parameter of their own naming, so result[...] never matches them.
    # Match any object indexed by a quoted name in one of loopdata's
    # namespaces instead.  That pattern is too loose for the templates --
    # they carry element ids and prose that would match it -- so it is used
    # only on .js, where every such string is a field read.
    js_direct = re.compile(
        r"""\[\s*(?:"((?:current|day|week|month|year|rainyear|alltime|trend|almanac|unit|station|10m|2h|24h)\.[^"]+)"|'((?:current|day|week|month|year|rainyear|alltime|trend|almanac|unit|station|10m|2h|24h)\.[^']+)')\s*\]""")
    fields = set()
    for name in sorted(os.listdir(SKIN)):
        if name.endswith('.js'):
            src = io.open(os.path.join(SKIN, name), encoding='utf-8').read()
            for dq, sq in js_direct.findall(src):
                fields.add(dq or sq)
            continue
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
          for theme in ('color', 'mono'):
            name = '%s show_purple=%s title_theme=%s' % (tmpl, purple, theme)
            try:
                html = render(tmpl, purple, theme)
            except Exception as e:
                print('FAIL %s: render error: %s' % (name, e))
                ok = False
                continue
            failures = check(html, theme == 'mono', purple)
            print('%s %s' % ('FAIL' if failures else 'ok  ', name))
            for f in failures:
                print('       - %s' % f)
            ok = ok and not failures
    # The no-analytics render, once: the #if in analytics.inc is the only
    # thing it changes, so one template at one show_purple setting covers it.
    name = '%s analytics absent' % templates[0]
    try:
        html = render(templates[0], False, 'color', analytics=False)
        failures = check(html, False, False)
        if 'googletagmanager' in html:
            failures.append('analytics block rendered with no googleAnalyticsId set')
        # The installer's stanza ships both analytics settings as EMPTY
        # strings; that must gate the block off exactly as absence does.
        html = render(templates[0], False, 'color', analytics=False,
                      overrides={'googleAnalyticsId': '', 'analytics_host': '',
                                 'page_update_pwd': ''})
        failures += check(html, False, False)
        if 'googletagmanager' in html:
            failures.append('analytics block rendered with an empty googleAnalyticsId')
        # An empty password would match every visitor's absent one and the
        # page would never expire; it must fall back to the default.
        if 'var page_update_pwd = "foobar";' not in html:
            failures.append('an empty page_update_pwd did not fall back to the default')
        # An id with an empty host must configure gtag with no host check:
        # 4.0 wrapped it in a check against "", which no page ever matches.
        html = render(templates[0], False, 'color', analytics=False,
                      overrides={'googleAnalyticsId': 'G-HOSTLESS', 'analytics_host': ''})
        failures += check(html, False, False)
        if ('googletagmanager' not in html or 'host == ""' in html
                or 'gtag(\'config\', "G-HOSTLESS")' not in html):
            failures.append('an id with an empty analytics_host did not configure gtag unconditionally')
    except Exception as e:
        failures = ['render error: %s' % e]
    print('%s %s' % ('FAIL' if failures else 'ok  ', name))
    for f in failures:
        print('       - %s' % f)
    ok = ok and not failures
    # Every Extras value that reaches a <script> goes through jsstr().  This
    # render feeds each one the characters that used to kill the updater --
    # a quote of each kind, a backslash, a newline, a </script> -- and
    # demands that every script still parses and that no script element
    # ends early.  With benign stub values the escaping is exercised by
    # nothing: remove it and the ordinary renders still pass.
    HOSTILE = {
        'page_update_pwd': "don't</script><x>\\ \"sleep\"",
        'loop_data_file': 'a"b\\c</script>.txt',
        # A list here too: the src URL and the gtag literal must agree.
        'googleAnalyticsId': ["G-1'&2\"3<x", 'y'],
        # A list: what ConfigObj hands over for an unquoted comma.  jsstr
        # joins it back, so the value reaches the page as typed.
        'analytics_host': ["h'", '</script>'],
        'refresh_rate': '2"',
        'expiration_time': "4'",
        'max_age': 'ten\nseconds',
        'clock_max_age': '</script>',
        # The indoor board's sidecar files, so its render is hostile too.
        'in_temp_file': "in'</script>.txt",
        'in_co2_file': 'a"b.txt',
        'in_aqi_file': 'x\\y.txt',
        'solar_array_file': 'p</script>.json',
    }
    for tmpl in templates:
        name = '%s hostile Extras' % tmpl
        try:
            html = render(tmpl, True, 'color', overrides=HOSTILE)
            failures = check(html, False, True)
            if not esprima:
                failures.append('esprima not importable: the hostile render cannot be parse-checked')
            if 'if (host == "h\',\\u003c/script>")' not in html:
                failures.append('a list-valued setting was not joined back with commas')
            if 'gtag/js?id=G-1%27%262%223%3Cx%2Cy"' not in html or 'gtag(\'config\', "G-1\'&2\\"3\\u003cx,y")' not in html:
                failures.append('the analytics src and literal disagree on a list-valued id')
            if html.count('</script') != html.count('<script'):
                failures.append('a script element ended early: %d <script vs %d </script'
                                % (html.count('<script'), html.count('</script')))
        except Exception as e:
            failures = ['render error: %s' % e]
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
