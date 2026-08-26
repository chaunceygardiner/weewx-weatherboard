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

It also checks that skin.conf's [LoopData] [[fields]] declaration -- the
fields loopdata 7.0 and later writes under this report's name -- is
exactly the set of loopdata fields the updaters read.  A field the
updaters read but the skin does not declare arrives as question marks; a
field declared that nothing reads is rendered on every loop packet for
nobody.

And it loads install.py with a stubbed user.loopdata and exercises
loader(): an install must be refused on a station with no loopdata or one
older than 7.0, naming 7.0, and accepted with 7.0 and later by version
tuple rather than by string; a list or an uninstall must never be refused,
since WeeWX runs an installed extension's loader() for those too; and the
installer returned must carry the version changes.txt's newest heading
names, with no configure() left to edit the deprecated [LoopData]
[[Include]] fields line.

Run with a Python that has Cheetah installed, e.g. the WeeWX venv, with
esprima somewhere on PYTHONPATH (never installed into the venv itself):

  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/path/with/esprima \\
      /home/weewx/weewx-venv/bin/python3 tests/check_templates.py

This is a static check only: it proves the templates generate well-formed
pages, not that the updater behaves.  Behavior is verified by loading the
generated pages in a browser.
"""

import importlib.util
import io
import json
import os
import re
import sys
import types
from unittest import mock

try:
    from Cheetah.Template import Template
except ImportError:
    sys.exit("Cheetah is required (run with the WeeWX venv's python).")

try:
    import esprima
except ImportError:
    esprima = None

try:
    import configobj
except ImportError:
    sys.exit("configobj is required (run with the WeeWX venv's python).")

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIN = os.path.join(REPO, 'skins', 'WeatherBoard')
INSTALL = os.path.join(REPO, 'install.py')
SKIN_CONF = os.path.join(SKIN, 'skin.conf')
CHANGES = os.path.join(REPO, 'changes.txt')
# The report name the ordinary renders use.  The updater reads this key
# out of loop-data.txt, so it shows up in the rendered script.
REPORT_NAME = 'WeatherBoardReport'


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


def render(tmpl, show_purple, title_theme, analytics=True, overrides=None,
           report_name=REPORT_NAME):
    ns = {
        'Extras': make_extras(show_purple, title_theme, analytics, overrides),
        'current': Tag(),
        'day': Tag(),
        'station': Tag('Test Station'),
        'obs': Tag('SomeLabel'),
        # logo.inc embeds almanac values in JavaScript: bare number.
        'almanac': Tag('42.0'),
        # WeeWX's SkinInfo search list: the [StdReport] section name.
        'REPORT_NAME': report_name,
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


def declared_fields():
    """The fields skin.conf declares to loopdata: the union of the
    [LoopData] [[fields]] groups, read the way weewx reads a skin.conf
    (interpolation off, so the %X in the clock field survives) and the way
    loopdata takes the groups -- each a list, or a bare string for a
    one-field group."""
    conf = configobj.ConfigObj(SKIN_CONF, encoding='utf-8', interpolation=False,
                               file_error=True)
    groups = conf.get('LoopData', {}).get('fields')
    if not isinstance(groups, dict):
        return {}
    declared = {}
    for group, value in groups.items():
        if isinstance(value, dict):
            # A [[[section]]] under [[fields]]: loopdata warns and skips
            # it.  Reading its option names as fields here would report
            # the wrong thing, so it is carried through as a marker and
            # failed by name.
            declared.setdefault('<section %s under [[fields]]>' % group, []).append(group)
            continue
        if isinstance(value, str):
            value = [value]
        for entry in value:
            entry = entry.strip()
            if entry:
                declared.setdefault(entry, []).append(group)
    return declared


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


def check_declared_fields():
    """skin.conf's declaration must be exactly what the updaters read."""
    failures = []
    declared = declared_fields()
    if not declared:
        return ['skin.conf declares no [LoopData] [[fields]] groups']
    for field, groups in declared.items():
        if field.startswith('<section'):
            failures.append('%s: a group is a line of fields, not a section' % field)
        elif len(groups) > 1:
            failures.append('%s is declared in more than one group: %s' % (field, groups))
    read = fields_read_by_updaters()
    unresolved = sorted(f for f in read if f.startswith('<unresolved'))
    if unresolved:
        failures.append('cannot resolve field name(s): %s' % unresolved)
        read = set(read) - set(unresolved)
    missing = sorted(read - set(declared))
    if missing:
        failures.append('read by the updaters, not declared in skin.conf: %s' % missing)
    unread = sorted(set(declared) - read)
    if unread:
        failures.append('declared in skin.conf, read by nothing: %s' % unread)
    # The AQI fields are read only with show_purple set; they sit in a
    # group of their own so the comment saying so stays attached to them.
    for field, groups in declared.items():
        if ('aqi' in field) != (groups == ['air_quality']):
            failures.append('%s: only the AQI fields belong in the air_quality group' % field)
    return failures


def load_installer():
    """install.py as a module.  It imports weectl's 'setup' module: in
    WeeWX 5 weecfg.extension registers itself under that name when
    imported (the alias that keeps pre-5.0 installers loading); in WeeWX 4
    wee_extension makes the alias itself, so it is made here too."""
    module = importlib.import_module('weecfg.extension')
    sys.modules.setdefault('setup', module)
    spec = importlib.util.spec_from_file_location('weatherboard_install', INSTALL)
    installer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(installer)
    return installer


INSTALL_ARGV = ['weectl', 'extension', 'install', 'weewx-weatherboard.zip']


def loader_result(module, loop_data_version, argv=INSTALL_ARGV):
    """What loader() does, run as the given command line, on a station
    whose weewx-loopdata is the given version, or absent (None): the
    installer, or the SystemExit message.  A None in sys.modules makes the
    import raise ModuleNotFoundError, which is what an uninstalled loopdata
    looks like from inside weectl.  The string 'broken' stands for a
    loopdata that IS installed but whose import fails -- a module with no
    LOOP_DATA_VERSION, as every loopdata before 2020 was, which raises a
    plain ImportError rather than a ModuleNotFoundError."""
    if loop_data_version is None:
        modules = {'user': None, 'user.loopdata': None}
    elif loop_data_version == 'broken':
        user = types.ModuleType('user')
        loopdata = types.ModuleType('user.loopdata')
        user.loopdata = loopdata
        modules = {'user': user, 'user.loopdata': loopdata}
    else:
        user = types.ModuleType('user')
        loopdata = types.ModuleType('user.loopdata')
        loopdata.LOOP_DATA_VERSION = loop_data_version
        user.loopdata = loopdata
        modules = {'user': user, 'user.loopdata': loopdata}
    with mock.patch.dict(sys.modules, modules), mock.patch.object(sys, 'argv', list(argv)):
        try:
            return module.loader()
        except SystemExit as e:
            return str(e)


def check_installer():
    """loader() refuses to install on a station without weewx-loopdata 7.0,
    refuses nothing when WeeWX is only listing or uninstalling, and the
    installer it returns is the release changes.txt names, with no
    configure() left to edit the fields line."""
    failures = []
    try:
        module = load_installer()
    except Exception as e:
        return ['install.py failed to load: %s' % e]
    for version in (None, '6.0', '6.11.3', '6.99'):
        result = loader_result(module, version)
        if not isinstance(result, str):
            failures.append('loader() accepted weewx-loopdata %s' % (version or 'absent'))
            continue
        if '7.0' not in result or (version is not None and version not in result):
            failures.append('the refusal for weewx-loopdata %s does not name 7.0%s: %r'
                            % (version or 'absent',
                               '' if version is None else ' and the version found', result))
        if version is None and 'not installed' not in result:
            failures.append('the refusal with no loopdata does not say so: %r' % result)
        # wee_extension (WeeWX 4) is optparse: --install FILE, --install=FILE,
        # and any unambiguous prefix of the option all install.
        for argv in (['wee_extension', '--install', 'weewx-weatherboard.zip'],
                     ['wee_extension', '--install=weewx-weatherboard.zip'],
                     ['wee_extension', '--inst', 'weewx-weatherboard.zip']):
            result = loader_result(module, version, argv)
            if not isinstance(result, str):
                failures.append('loader() accepted weewx-loopdata %s under `%s`'
                                % (version or 'absent', ' '.join(argv)))
    # An installed loopdata whose import fails is not an absent one: saying
    # "not installed" would tell the user to install what they have.
    result = loader_result(module, 'broken')
    if not isinstance(result, str):
        failures.append('loader() accepted a loopdata with no LOOP_DATA_VERSION')
    elif 'not installed' in result or 'is installed' not in result:
        failures.append('a broken loopdata was reported as not installed: %r' % result)
    # 10.0 pins a tuple compare over a string one; a bare 7 pins that the
    # tuple is padded, since (7,) sorts before (7, 0).
    installer = None
    for version in ('7.0', '7.0.1', '7.1b1', '10.0', '7'):
        result = loader_result(module, version)
        if isinstance(result, str):
            failures.append('loader() refused weewx-loopdata %s: %r' % (version, result))
        elif installer is None:
            installer = result
    # WeeWX runs an installed extension's loader() for extension list and
    # extension uninstall too, from its cached copy of install.py, and
    # catches only its own ExtensionError: a refusal there would leave the
    # board unlistable and unremovable once loopdata was gone.
    for argv in (['weectl', 'extension', 'list'],
                 ['weectl', 'extension', 'uninstall', 'weatherboard'],
                 ['wee_extension', '--list'],
                 ['wee_extension', '--uninstall', 'weatherboard']):
        result = loader_result(module, None, argv)
        if isinstance(result, str):
            failures.append('loader() refused `%s` with no loopdata: %r' % (' '.join(argv), result))
    if installer is None:
        return failures
    if 'configure' in type(installer).__dict__:
        failures.append('the installer still defines configure()')
    if 'LoopData' in installer['config']:
        failures.append("the installer's stanza writes a [LoopData] section")
    # The version is the release: it must be the one changes.txt's newest
    # heading names.
    heading = re.search(r'^(\d+(?:\.\d+)+)\s+\d{1,2}/\d{1,2}/\d{4}\s*$',
                        io.open(CHANGES, encoding='utf-8').read(), re.M)
    if not heading:
        failures.append('no release heading found in changes.txt')
    elif heading.group(1) != installer['version']:
        failures.append('install.py says %s, changes.txt says %s'
                        % (installer['version'], heading.group(1)))
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
    # The report name is not an Extra, but it reaches the script the same
    # way and a [StdReport] section can be named anything.
    HOSTILE_REPORT = "Weather'Board\"</script>\\ R\u00e9port"
    for tmpl in templates:
        name = '%s hostile Extras' % tmpl
        try:
            html = render(tmpl, True, 'color', overrides=HOSTILE,
                          report_name=HOSTILE_REPORT)
            failures = check(html, False, True)
            expected = '[' + json.dumps(HOSTILE_REPORT).replace('<', '\\u003c') + ']'
            if expected not in html:
                failures.append('the report name did not reach the updater as an escaped literal')
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
    failures = check_declared_fields()
    print('%s skin.conf declares the loopdata fields the updaters read'
          % ('FAIL' if failures else 'ok  '))
    for f in failures:
        print('       - %s' % f)
    ok = ok and not failures
    failures = check_installer()
    print('%s install.py requires weewx-loopdata 7.0 and is the release changes.txt names'
          % ('FAIL' if failures else 'ok  '))
    for f in failures:
        print('       - %s' % f)
    ok = ok and not failures
    sys.exit(0 if ok else 1)


main()
