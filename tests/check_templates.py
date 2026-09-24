# Copyright (C)2026 by John A Kline <john@johnkline.com>
# Distributed under the terms of the GNU Public License (GPLv3)
# See LICENSE for your rights.
"""Offline check for the WeatherBoard templates.

Renders both boards -- index.html (the readout board) and splitflap.html
(the split-flap board) -- with a stub searchList, once with every
optional reading present and once with none, and validates the output:

  - templates render without Cheetah errors
  - every element id the javascript paints exists in the HTML
  - no unrendered $Extras/$current/... placeholders leak into the output
  - every <script> is plain ASCII: WeeWX writes these pages with
    encoding = html_entities, which turns any other character into an
    entity -- inside a script, a broken string
  - no inline style= attributes (all CSS belongs in weatherboard.css)
  - every <script> parses as valid JavaScript (needs the pure-Python
    'esprima' package; the ordinary renders skip this with a warning if it
    is absent, but the hostile-Extras render FAILS without it -- parsing is
    the whole point of that check, so esprima is required for a pass)

It also checks that skin.conf's [LoopData] [[fields]] declaration -- the
fields loopdata 7.0 and later writes under this report's name -- is
exactly the set of loopdata fields the boards read.  A field the boards
read but the skin does not declare arrives missing; a field declared that
nothing reads is rendered on every loop packet for nobody.

And it holds the language files to the pages: en.conf carries exactly the
strings the pages render, every other language carries all of them and
nothing else, and the strings the boards draw in their own lettering fit
the split-flap board's twelve flaps.  (That Bebas Neue, the readout
board's lettering, has every letter they use is read from the font by
tests/browser_check.py, which has fontTools.)

And it loads install.py with a stubbed user.loopdata and exercises
loader(): an install must be refused on a station with no loopdata or one
older than 7.0, naming 7.0, and accepted with 7.0 and later by version
tuple rather than by string; a list or an uninstall must never be refused,
since WeeWX runs an installed extension's loader() for those too; and the
installer returned must carry the version changes.md's newest heading
names, with no configure() left to edit the deprecated [LoopData]
[[Include]] fields line.

Run with a Python that has Cheetah installed, e.g. the WeeWX venv, with
esprima somewhere on PYTHONPATH (never installed into the venv itself):

  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/path/with/esprima \\
      /home/weewx/weewx-venv/bin/python3 tests/check_templates.py

This is a static check only: it proves the templates generate well-formed
pages, not that the boards behave.  tests/browser_check.py runs them.
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
CHANGES = os.path.join(REPO, 'changes.md')
# The release, as install.py names it: the pages' stylesheet links carry it.
RELEASE = re.search(r'^\s*version\s*=\s*"([^"]+)"', io.open(INSTALL, encoding='utf-8').read(),
                    re.M).group(1)
# The report name the ordinary renders use.  The updater reads this key
# out of loop-data.txt, so it shows up in the rendered script.
REPORT_NAME = 'WeatherBoardReport'


class Tag:
    """Stub for WeeWX tags: $current.outTemp, $obs.label.foo, etc.  Truthy
    unless made otherwise, which is what .has_data answers."""
    def __init__(self, s='54.9°F', present=True):
        self._s = s
        self._present = present

    def __getattr__(self, name):
        if name.startswith('__'):
            raise AttributeError(name)
        return self

    def __call__(self, *args, **kwargs):
        return self

    def __str__(self):
        return self._s

    def __bool__(self):
        return self._present


class Current:
    """$current.<obs>: its has_data is False for the observations named
    missing, so the auto settings can be driven both ways."""
    def __init__(self, missing=()):
        self._missing = set(missing)

    def __getattr__(self, name):
        if name.startswith('__'):
            raise AttributeError(name)
        return Tag(present=name not in self._missing)


class Unit:
    """$unit: labels, and unit_type for the split-flap lamps' thresholds."""
    class _Labels:
        def __getattr__(self, name):
            if name.startswith('__'):
                raise AttributeError(name)
            return {'outTemp': '°F', 'dewpoint': '°F', 'appTemp': '°F', 'outHumidity': '%',
                    'windSpeed': 'mph', 'barometer': 'inHg', 'rain': 'in', 'rainRate': 'in/h',
                    'radiation': 'W/m²'}.get(name, '?')

    class _Types:
        def __getattr__(self, name):
            if name.startswith('__'):
                raise AttributeError(name)
            return {'windGust': 'km_per_hour', 'barometer': 'mbar'}.get(name, 'unknown')

    label = _Labels()
    unit_type = _Types()


class UnitUS(Unit):
    """$unit for a station in US units: mph and inHg."""
    class _Types:
        def __getattr__(self, name):
            if name.startswith('__'):
                raise AttributeError(name)
            return {'windGust': 'mile_per_hour', 'barometer': 'inHg'}.get(name, 'unknown')

    unit_type = _Types()


# Every optional reading present, and every one absent.
ALL_PRESENT = ()
NONE_PRESENT = ('UV', 'radiation', 'pm2_5', 'pm2_5_aqi', 'appTemp')


class Extras(dict):
    """WeeWX Extras sections still answer the py2-era has_key()."""
    def has_key(self, k):
        return k in self


def make_extras(analytics=True, overrides=None):
    extras = {
        'loop_data_file': 'loop-data.txt',
        'max_age': 10,
        'refresh_rate': 2,
        'expiration_time': 4,
        'page_update_pwd': 'testpwd',
        'show_uv': 'auto',
        'show_radiation': 'auto',
        'show_aqi': 'auto',
    }
    # googleAnalyticsId ALONE gates analytics.inc's body; analytics_host
    # only decides whether the gtag calls are wrapped in a host test, and an
    # id with no host is a working configuration.  The escaping there is
    # exercised only when the body renders; the render without an id is the
    # one every station without Google Analytics gets.  All three paths are
    # checked (see main).
    if analytics:
        extras['googleAnalyticsId'] = 'G-TESTID0001'
        extras['analytics_host'] = 'example.com'
    if overrides:
        extras.update(overrides)
    return Extras(extras)


def lang_texts(lang):
    """A language file's [Texts], the way WeeWX reads a skin's files."""
    conf = configobj.ConfigObj(os.path.join(SKIN, 'lang', lang + '.conf'), encoding='utf-8',
                               interpolation=False, file_error=True)
    return conf


def render(tmpl, missing=ALL_PRESENT, analytics=True, overrides=None,
           report_name=REPORT_NAME, lang='en', unit=None):
    texts = lang_texts(lang)['Texts']
    ns = {
        'Extras': make_extras(analytics, overrides),
        'current': Current(missing),
        'day': Tag(),
        'station': Tag('Test Station'),
        'unit': unit or Unit(),
        'gettext': lambda key: texts.get(key, key),
        # WeeWX's SkinInfo search list: the [StdReport] section name.
        'REPORT_NAME': report_name,
    }
    # #include paths resolve relative to the CWD.
    os.chdir(SKIN)
    return str(Template(file=os.path.join(SKIN, tmpl), searchList=[ns]))


# The ids each board's painter reaches the page through: every helper that
# takes a cell's id first.  A helper missing here takes its ids out of the
# check without failing anything.
PAINTED = re.compile(r"""(?:getElementById|roSet|roWind|roBarometer|roAqi|flapShow|flapLamp)"""
                     r"""\(\s*(?:"([^"]+)"|'([^']+)')""")


def check(html, tmpl, missing=ALL_PRESENT):
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
    for i, js in enumerate(scripts):
        odd = sorted(set(ch for ch in js if ord(ch) > 127))
        if odd:
            failures.append('script %d carries non-ASCII %s: html_entities encoding turns it into'
                            ' an entity; write it as a \\u escape' % (i, odd))
    declared = set(re.findall(r'id=["\']([^"\']+)["\']', html))
    used = set()
    for dq, sq in PAINTED.findall(js_all):
        used.add(dq or sq)
    # flapLamp names the row; its lamp is the row's id plus -lamp.
    used |= set((dq or sq) + '-lamp' for dq, sq in
                re.findall(r"""flapLamp\(\s*(?:"([^"]+)"|'([^']+)')""", js_all))
    optional = {'ro-uv': 'UV', 'ro-rad': 'radiation', 'ro-aqi': 'pm2_5_aqi',
                'ro-fl': 'appTemp', 'flap-air': 'pm2_5_aqi', 'flap-air-lamp': 'pm2_5_aqi'}
    missing_ids = sorted(i for i in used - declared
                         if not (i in optional and optional[i] in missing))
    if missing_ids:
        failures.append('the javascript paints ids the page does not have: %s' % missing_ids)
    # $24h... is included deliberately: it is NOT a valid Cheetah placeholder
    # (digit start) and renders as literal text if put in a template.
    leaks = re.findall(
        r'\$Extras[.\w]*|\$current[.\w]*|\$day[.\w]*|\$obs[.\w]*|\$24h[.\w]*|\$station[.\w]*'
        r'|\$jsstr\(|\$gettext|\$unit[.\w]*|\$wb_\w*',
        html)
    if leaks:
        failures.append('unrendered placeholders: %s' % sorted(set(leaks)))
    # Every stylesheet link carries the release, so an upgrade's pages never
    # draw with a stylesheet a browser cached from the last one.
    for href in re.findall(r'<link rel="stylesheet"[^>]*href="([^"]*)"', html):
        if not href.endswith('?v=' + RELEASE):
            failures.append('the stylesheet link %s does not carry ?v=%s, the release install.py'
                            ' names: a browser may draw the page with a cached old stylesheet'
                            % (href, RELEASE))
    inline = re.findall(r'style="[^"]*"', html)
    if inline:
        failures.append('inline styles (move to weatherboard.css): %s' % inline[:5])
    # The optional readings.  With everything present each panel is there
    # and its flag is on; with nothing present each is gone and its flag is
    # off.  The ids alone cannot see a gate that resolved the wrong way:
    # the painter skips a missing cell, so both renders would pass.
    want = {'uv': 'UV' not in missing, 'radiation': 'radiation' not in missing,
            'aqi': 'pm2_5_aqi' not in missing, 'feels': 'appTemp' not in missing}
    m = re.search(r'show: \{ uv: (\w+), radiation: (\w+), aqi: (\w+), feels: (\w+) \}', html)
    if not m:
        failures.append('the show flags were not rendered')
    else:
        got = dict(zip(('uv', 'radiation', 'aqi', 'feels'), (v == 'true' for v in m.groups())))
        if got != want:
            failures.append('show flags are %s, expected %s' % (got, want))
    if tmpl == 'index.html.tmpl':
        for cell, key in (('ro-uv', 'uv'), ('ro-rad', 'radiation'), ('ro-aqi', 'aqi'), ('ro-fl', 'feels')):
            if (('id="%s"' % cell) in html) != want[key]:
                failures.append('the %s panel is %s but %s is %s'
                                % (cell, 'there' if not want[key] else 'missing', key, want[key]))
        if ('id="ro-sun"' in html) != (want['uv'] or want['radiation']):
            failures.append('the sun panel does not follow UV and radiation')
    elif tmpl == 'splitflap.html.tmpl':
        if ('id="flap-air"' in html) != want['aqi']:
            failures.append('the air row does not follow show_aqi')
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
    """Every loopdata field the javascript looks up in a poll result:
    result["f"], r['f'] and lastResult['f'] directly, and val('f') and
    has(r, 'f') -- the painters' two helpers."""
    patterns = [
        re.compile(r"""\b(?:result|lastResult|r)\[\s*(?:"([^"]+)"|'([^']+)')\s*\]"""),
        re.compile(r"""\bval\(\s*(?:"([^"]+)"|'([^']+)')\s*\)"""),
        re.compile(r"""\bhas\(\s*r\s*,\s*(?:"([^"]+)"|'([^']+)')\s*\)"""),
    ]
    fields = set()
    for name in sorted(os.listdir(SKIN)):
        if not (name.endswith('.inc') or name.endswith('.tmpl')):
            continue
        src = io.open(os.path.join(SKIN, name), encoding='utf-8').read()
        for pat in patterns:
            for dq, sq in pat.findall(src):
                fields.add(dq or sq)
        # gustField(r, span) reads span + '.windGust.max.formatted' and
        # span + '.windSpeed.max.formatted'.
        for span in re.findall(r"gustField\(r,\s*'(\w+)'\)", src):
            fields.add(span + '.windGust.max.formatted')
            fields.add(span + '.windSpeed.max.formatted')
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
    # The AQI fields are read only when the air quality reading shows;
    # they sit in a group of their own so the comment saying so stays
    # attached to them.
    for field, groups in declared.items():
        if ('aqi' in field) != (groups == ['air_quality']):
            failures.append('%s: only the AQI fields belong in the air_quality group' % field)
    return failures


def load_installer():
    """install.py as a module.  It imports weectl's 'setup' module: in
    WeeWX 5 weecfg.extension registers itself under that name when
    imported (the alias that keeps pre-5.0 installers loading); in WeeWX 4
    wee_extension made the alias itself; making it here as well costs
    nothing."""
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
    installer it returns is the release changes.md names, with no
    configure() left to edit the fields line, and it installs every file
    the skin has."""
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
                 ['weectl', 'extension', 'uninstall', 'weatherboard']):
        result = loader_result(module, None, argv)
        if isinstance(result, str):
            failures.append('loader() refused `%s` with no loopdata: %r' % (' '.join(argv), result))
    # WeeWX 5.2 or later, by version tuple: 5.10 is newer than 5.2.
    import weewx
    for version, accepted in (('4.10.2', False), ('5.1.0', False), ('5.2.0', True),
                              ('5.10.0', True), ('6.0.0b1', True)):
        with mock.patch.object(weewx, '__version__', version):
            result = loader_result(module, '7.0')
        if accepted and isinstance(result, str):
            failures.append('loader() refused WeeWX %s: %r' % (version, result))
        if not accepted and (not isinstance(result, str) or '5.2' not in result):
            failures.append('loader() did not refuse WeeWX %s naming 5.2: %r' % (version, result))
    if installer is None:
        return failures
    if 'configure' in type(installer).__dict__:
        failures.append('the installer still defines configure()')
    if 'LoopData' in installer['config']:
        failures.append("the installer's stanza writes a [LoopData] section")
    # The version is the release: it must be the one changes.md's newest
    # heading names.
    heading = re.search(r'^##\s+(\d+(?:\.\d+)+)\s+\d{1,2}/\d{1,2}/\d{4}\s*$',
                        io.open(CHANGES, encoding='utf-8').read(), re.M)
    if not heading:
        failures.append('no release heading found in changes.md')
    elif heading.group(1) != installer['version']:
        failures.append('install.py says %s, changes.md says %s'
                        % (installer['version'], heading.group(1)))
    # weectl installs the files named, and only those: a skin file left off
    # the list is missing on every station, and nothing here would render
    # differently.  Each goes to its own directory.
    listed = set()
    for directory, names in installer['files']:
        for name in names:
            listed.add(name)
            if os.path.dirname(name) != directory:
                failures.append('install.py puts %s in %s' % (name, directory))
    present = set()
    for dirpath, _dirs, names in os.walk(SKIN):
        for name in names:
            present.add(os.path.relpath(os.path.join(dirpath, name), REPO))
    for name in sorted(present - listed):
        failures.append('install.py does not install %s' % name)
    for name in sorted(listed - present):
        failures.append('install.py installs %s, which does not exist' % name)
    return failures



# ---------------------------------------------------------------------------
# The installer's config stanza.
#
# weectl's merge fills in absent keys and never rewrites a present one, so an
# option written LIVE in the stanza freezes every fresh install on today's
# default for ever.  Options that only select a default are therefore written
# COMMENTED OUT, and these guards hold that arrangement in place.  The live
# set is NAMED here rather than derived: every attempt to state a rule for it
# has mis-sorted at least one key.
STANZA_LIVE = (
    # weectl needs these.
    'HTML_ROOT', 'enable', 'skin',
    # This site's own title, path and analytics ids, and the setting most
    # likely to be edited.  Master ships title and meta_title in neither
    # place; this branch writes them live, so a fresh install is turnkey.
    'title', 'meta_title',
    'loop_data_file', 'googleAnalyticsId', 'analytics_host', 'page_update_pwd',
    # The indoor board's sidecar files: this site's own paths.
    'in_temp_file', 'in_co2_file', 'in_aqi_file', 'solar_array_file',
)

# Every option that ships commented out, with the value shown beside it.
# Rule 1: each must equal the fallback that actually governs when the option
# is absent, or a fresh install silently behaves differently from what the
# line says.
STANZA_COMMENTED = {
    'max_age': '10',
    'expiration_time': '4',
    'refresh_rate': '2',
    'show_uv': 'auto',
    'show_radiation': 'auto',
    'show_aqi': 'auto',
    # The indoor board's sidecar limits (this branch only).
    'in_temp_max_age': '120',
    'in_co2_max_age': '120',
    'in_aqi_max_age': '120',
    'solar_array_max_age': '150',
}

# A realistic merge target: a weewx.conf that ALREADY HAS [StdReport].  A
# virgin file shows dedents; this one shows what a fresh install really does.
MERGE_TARGET = """
[Station]
    station_type = Simulator

[StdReport]
    SKIN_ROOT = skins
    HTML_ROOT = public_html
    [[SeasonsReport]]
        skin = Seasons
        enable = true
    [[Defaults]]
        [[[Units]]]
            [[[[Groups]]]]
                group_temperature = degree_F

[StdArchive]
    archive_interval = 300
"""


def commented_assignments():
    """The `#key = value` lines in install.py's CONFIG, as text.  Read from
    the TEXT because a commented option is absent from the parsed ConfigObj:
    anything that walks the parsed stanza stops covering these silently."""
    module = load_installer()
    found = {}
    for line in module.CONFIG.split('\n'):
        m = re.match(r'\s*#(\w+)\s*=\s*(\S.*?)\s*$', line)
        if m:
            found[m.group(1)] = m.group(2)
    return found


def skin_conf_defaults():
    """The [Extras] values skin.conf ships.  These are what actually govern a
    commented-out stanza option: build_skin_dict merges skin.conf BEFORE the
    report's own stanza, so an absent stanza key is answered by the skin --
    which is the point, since an upgrade replaces the skin and never rewrites
    weewx.conf.  The updater's own fallback is one further link down the
    chain, reached only if skin.conf drops the key too."""
    text = io.open(SKIN_CONF, encoding='utf-8').read()
    section = re.search(r'^\[Extras\]$(.*?)^\[', text, re.M | re.S)
    if not section:
        return {}
    found = {}
    for line in section.group(1).split('\n'):
        m = re.match(r"\s*(\w+)\s*=\s*'?\"?([^'\"#]*?)'?\"?\s*$", line)
        if m and not line.lstrip().startswith('#'):
            found[m.group(1)] = m.group(2).strip()
    return found


def js_fallbacks():
    """The default each setting falls back to when skin.conf drops it too:
    the numeric ones out of board.inc's numExtra() calls, each traced from
    the WB property it reads back to the Extra that fills it, and the show_
    ones out of their $Extras.get() defaults."""
    found = {}
    board = io.open(os.path.join(SKIN, 'board.inc'), encoding='utf-8').read()
    props = dict((prop, key) for prop, key in re.findall(
        r"(\w+): \$jsstr\(\$Extras\.get\('(\w+)', ''\)\)", board))
    for prop, dflt in re.findall(r"numExtra\(WB\.(\w+),\s*([\d.]+)\)", board):
        if prop in props:
            found[props[prop]] = dflt
    for key, dflt in re.findall(r"\$Extras\.get\('(show_\w+)',\s*'(\w+)'\)", board):
        found.setdefault(key, dflt)
    return found


def check_stanza():
    """Rule 1 (commented value == the fallback that governs), rule 3 (every
    comment block lands in its own section at its key's indent), and the count
    -- which is the only thing that catches a block dropped outright, since a
    dropped block leaves no line whose indent could be measured."""
    failures = []
    try:
        module = load_installer()
    except Exception as e:
        return ['install.py failed to load: %s' % e]

    # No live option may have been demoted, and nothing demoted may be live.
    parsed = module.installer_config()
    live = set()

    def walk(section):
        for k in section.scalars:
            live.add(k)
        for k in section.sections:
            walk(section[k])
    walk(parsed)
    for key in STANZA_LIVE:
        if key not in live:
            failures.append('%s must stay live in the stanza, and is not' % key)
    for key in STANZA_COMMENTED:
        if key in live:
            failures.append('%s is live in the stanza but is meant to be commented out' % key)
    # Master holds title and meta_title OUT of the stanza, since their
    # defaults are the station's location and the title.  This branch
    # writes the site's own, live, and STANZA_LIVE holds them there.

    # Rule 1.
    found = commented_assignments()
    if set(found) != set(STANZA_COMMENTED):
        failures.append('commented options are %s, expected %s'
                        % (sorted(found), sorted(STANZA_COMMENTED)))
    for key, want in sorted(STANZA_COMMENTED.items()):
        if found.get(key) != want:
            failures.append('#%s reads %r in install.py, expected %r'
                            % (key, found.get(key), want))
    # Rule 1, along the whole chain.  skin.conf answers first; the updater's
    # own fallback answers only if skin.conf has dropped the key as well.  A
    # commented value that disagrees with EITHER is a fresh install quietly
    # behaving differently from the line it shipped with.
    shipped = skin_conf_defaults()
    fallbacks = js_fallbacks()
    for key, shown in sorted(found.items()):
        governs = shipped.get(key)
        if governs is None:
            failures.append('#%s = %s is commented out and skin.conf does not ship %s'
                            ' either, so nothing between them answers -- the option falls'
                            " all the way through to the updater's own default"
                            % (key, shown, key))
        elif governs != shown:
            failures.append('#%s = %s but skin.conf ships %s = %s, and skin.conf is what'
                            ' answers an absent stanza key -- move whichever of the two is'
                            ' wrong, remembering the live value is what fresh installs'
                            ' were running' % (key, shown, key, governs))
        backstop = fallbacks.get(key)
        if backstop is not None and governs is not None and backstop != governs:
            failures.append("skin.conf ships %s = %s but the updater falls back to %s;"
                            ' they must agree, or a station whose skin.conf lost the key'
                            ' behaves differently again' % (key, governs, backstop))

    # Rule 3, and the count, through the real conditional_merge.
    try:
        import configobj
        import weeutil.config
        merged = configobj.ConfigObj(io.StringIO(MERGE_TARGET), encoding='utf-8')
        weeutil.config.conditional_merge(merged, module.installer_config())
        buf = io.BytesIO()
        merged.write(buf)
        out = buf.getvalue().decode('utf-8')
    except Exception as e:
        failures.append('the merge could not be measured: %s' % e)
        return failures

    seen = 0
    pending = []
    for line in out.split('\n'):
        stripped = line.strip()
        if not stripped:
            pending = []
            continue
        indent = len(line) - len(line.lstrip())
        if stripped.startswith('#'):
            pending.append((indent, stripped))
            m = re.match(r'#(\w+)\s*=', stripped)
            if m and m.group(1) in STANZA_COMMENTED:
                seen += 1
            continue
        is_section = stripped.startswith('[')
        for c_indent, text in pending:
            # A comment block is written at the indent of whatever key comes
            # next, so prose need only agree with that.
            if c_indent != indent:
                failures.append('a comment landed at column %d beside a key at column %d:'
                                ' %s' % (c_indent, indent, text))
            # A commented ASSIGNMENT is held to more than that.  Uncommenting
            # one has to put the option in the section it documents, and a
            # comment block that lands in front of a SECTION HEADER is written
            # at the header's indent -- one level out from the scalars it
            # belongs with.  #show_aqi left last in [[[Extras]]], before a
            # following section, comes out at that section's column, and
            # uncommenting it there sets show_aqi on [[WeatherBoardReport]],
            # where nothing reads it.
            # So every commented option needs a LIVE SCALAR after it, in its
            # own section.
            elif is_section and re.match(r'#\w+\s*=', text):
                failures.append('%s is the last thing in its section, so it is written at'
                                " the following section header's column (%d) -- uncommenting"
                                ' it would put the option in the parent section.  Order a'
                                ' live scalar after it.' % (text, indent))
        pending = []
    if seen != len(STANZA_COMMENTED):
        failures.append('%d of %d commented options reached the merged config -- a comment'
                        ' block attached to a key the target already has is DROPPED, and'
                        ' no indentation check can see that' % (seen, len(STANZA_COMMENTED)))
    # The stanza must not carry what skin.conf already governs.
    if 'Labels' in parsed['StdReport']['WeatherBoardReport']:
        failures.append('the stanza writes a [[[Labels]]] section, which skin.conf already'
                        ' carries -- writing it here freezes every fresh install on it')
    # Nor pin number formats: the boards fit whatever width they are given,
    # so a pin here would only freeze a fresh install on today's formats.
    if 'Units' in parsed['StdReport']['WeatherBoardReport']:
        failures.append('the stanza writes a [[[Units]]] section; the boards fit any format,'
                        ' so it can only freeze a fresh install on today\'s formats')
    return failures


LANGS = ('da', 'de', 'en', 'es', 'fr', 'it', 'nl', 'no', 'sv')
# Strings the boards draw in their own lettering, and on the split-flap
# board's flaps.  {n} at its widest for each: seconds and minutes run to
# 59, hours to 23, days as far as 99.
STATUS = {'{n} S AGO': 59, '{n} M AGO': 59, '{n} H AGO': 23, '{n} D AGO': 99,
          'NO CONNECT': None, 'EXPIRED TAP': None, 'WAITING': None}
FLAP_LIMITS = {'HI': 3, 'RH': 3, 'G': 1, '/HR': 3, 'CALM': 7,
               'GOOD': 8, 'MODERATE': 8, 'USG': 8, 'UNHLTHY': 8, 'V UNHLTH': 8, 'HAZARD': 8}


def gettext_keys():
    """Every string the pages hand to $gettext."""
    keys = set()
    for name in sorted(os.listdir(SKIN)):
        if not name.endswith(('.inc', '.tmpl')):
            continue
        src = io.open(os.path.join(SKIN, name), encoding='utf-8').read()
        for q, key in re.findall(r"""\$gettext\((["'])(.*?)\1\)""", src):
            keys.add(key)
    return keys


def check_langs():
    """en.conf is exactly the strings the pages render; every language has
    them all and nothing else; and what the boards draw in their own
    lettering fits."""
    failures = []
    rendered = gettext_keys()
    files = sorted(f[:-5] for f in os.listdir(os.path.join(SKIN, 'lang')) if f.endswith('.conf'))
    if files != sorted(LANGS):
        failures.append('lang/ holds %s, expected %s' % (files, sorted(LANGS)))
    en = lang_texts('en')['Texts']
    if set(en) != rendered:
        failures.append('en.conf is missing %s and carries unrendered %s'
                        % (sorted(rendered - set(en)), sorted(set(en) - rendered)))
    for key, value in en.items():
        if key != value:
            failures.append('en.conf translates %r as %r: English is its own key' % (key, value))
    for lang in LANGS:
        conf = lang_texts(lang)
        texts = conf['Texts']
        if set(texts) != set(en):
            failures.append('%s.conf is missing %s and carries unknown %s'
                            % (lang, sorted(set(en) - set(texts)), sorted(set(texts) - set(en))))
        for key, widest in STATUS.items():
            value = texts.get(key, '')
            if ('{n}' in key) != ('{n}' in value):
                failures.append('%s.conf %r: {n} must be kept exactly once' % (lang, key))
            shown = value.replace('{n}', str(widest)) if widest is not None else value
            if len(shown) > 12:
                failures.append('%s.conf %r reads %r, %d characters: the split-flap board has 12'
                                % (lang, key, shown, len(shown)))
        clock = texts.get('%-I:%M:%S %p', '')
        if re.sub(r'%-?[IHMSp]', '', clock).strip(': ') != '':
            failures.append('%s.conf clock format %r uses more than %%-I %%I %%H %%M %%S %%p'
                            % (lang, clock))
        for key, limit in FLAP_LIMITS.items():
            if len(texts.get(key, '')) > limit:
                failures.append('%s.conf %r reads %r: at most %d characters on a flap row'
                                % (lang, key, texts.get(key), limit))
        dirs = conf.get('Units', {}).get('Ordinates', {}).get('directions')
        if not isinstance(dirs, list) or len(dirs) != 17:
            failures.append('%s.conf needs [Units] [[Ordinates]] directions, 17 of them' % lang)
        else:
            for d in dirs[:16]:
                if len(d) > 3:
                    failures.append('%s.conf direction %r runs past the wind cell\'s three characters'
                                    % (lang, d))
    return failures


def check_css_fallbacks():
    """The stylesheet's fallbacks for older browsers, which no browser
    here can prove: every clip-path has a -webkit-clip-path twin of the
    same value (all Safari before 13.1 reads), and the root size is given
    plain before its min() (which Chrome before 79 cannot read)."""
    failures = []
    css = io.open(os.path.join(SKIN, 'weatherboard.css'), encoding='utf-8').read()
    css = re.sub(r'/\*.*?\*/', '', css, flags=re.S)
    # Each clip-path directly after its own twin: a value found elsewhere
    # in the file does not count, since two rules can share one.
    plain = re.findall(r'(?<!-webkit-)clip-path:([^;]+);', css)
    paired = re.findall(r'-webkit-clip-path:([^;]+);\s*clip-path:([^;]+);', css)
    if not plain:
        failures.append('no clip-path found: the check has lost its subject')
    if len(paired) != len(plain):
        failures.append('%d clip-paths, %d of them directly after a -webkit-clip-path twin'
                        % (len(plain), len(paired)))
    for w, p in paired:
        if re.sub(r'\s+', ' ', w) != re.sub(r'\s+', ' ', p):
            failures.append('clip-path:%s has a twin of a different value' % p[:60])
    if not re.search(r'html \{\s*font-size: 1vh;[^}]*font-size: min\(1vh, \.625vw\);', css):
        failures.append('the root font-size min() has no plain fallback before it')
    return failures


def report(name, failures):
    print('%s %s' % ('FAIL' if failures else 'ok  ', name))
    for f in failures:
        print('       - %s' % f)
    return not failures


def main():
    if esprima is None:
        print('WARNING: esprima not importable; skipping JS syntax checks.')
        print('         (pip install esprima to a dir on PYTHONPATH -- never into the venv.)')
    ok = True
    templates = ['index.html.tmpl', 'splitflap.html.tmpl']
    for tmpl in templates:
        for label, missing in (('every optional reading', ALL_PRESENT),
                               ('no optional reading', NONE_PRESENT)):
            name = '%s, %s' % (tmpl, label)
            try:
                failures = check(render(tmpl, missing), tmpl, missing)
            except Exception as e:
                failures = ['render error: %s' % e]
            ok = report(name, failures) and ok
        # Every language renders, and every script it produces still parses
        # and is still ASCII -- the translations reach the page through
        # $jsstr, which must escape them.
        failures = []
        for lang in LANGS:
            try:
                failures += ['%s: %s' % (lang, f) for f in check(render(tmpl, lang=lang), tmpl)]
            except Exception as e:
                failures.append('%s: render error: %s' % (lang, e))
        ok = report('%s in every language' % tmpl, failures) and ok
    # show_purple answers for show_aqi while show_aqi is auto, both ways,
    # and a forced show_ setting beats what the record carries.
    failures = []
    for overrides, missing, want in (
            ({'show_purple': 'False'}, ALL_PRESENT, 'false'),
            ({'show_purple': 'True'}, NONE_PRESENT, 'true'),
            ({'show_aqi': 'false', 'show_purple': 'True'}, ALL_PRESENT, 'false'),
            ({'show_uv': 'true'}, NONE_PRESENT, None),
            ({'show_aqi': 'nonsense'}, ALL_PRESENT, 'true')):
        html = render(templates[0], missing, overrides=overrides)
        m = re.search(r'show: \{ uv: (\w+), radiation: (\w+), aqi: (\w+),', html)
        if want is not None and (not m or m.group(3) != want):
            failures.append('%s with %s: aqi is %s, expected %s'
                            % (overrides, 'everything' if not missing else 'nothing',
                               m and m.group(3), want))
        if want is None and (not m or m.group(1) != 'true' or 'id="ro-uv"' not in html):
            failures.append('show_uv = true did not force the UV panel on a station without UV')
    # Feels like joins the temperatures across the top, and the panel is
    # marked for three, which sets them smaller; without it the two keep
    # the size for two.
    for missing, cells, cls in ((ALL_PRESENT, ['ro-t', 'ro-fl', 'ro-td'], 'ro-panel ro-three'),
                                (('appTemp',), ['ro-t', 'ro-td'], 'ro-panel')):
        html = render(templates[0], missing)
        panel = re.search(r'<section class="([^"]*)" id="ro-temp">(.*?)</section>', html, re.S)
        got = panel and re.findall(r'<div class="ro-c" id="([^"]+)"', panel.group(2))
        if not panel or panel.group(1) != cls or got != cells:
            failures.append('with %s: the temperature panel is %r holding %s, expected %r holding %s'
                            % ('feels like' if not missing else 'no feels like',
                               panel and panel.group(1), got, cls, cells))
    ok = report('the show_ settings, auto and forced, show_purple as show_aqi, and feels like on top', failures) and ok
    # The title: the title Extra, else the station's location; the tab:
    # meta_title, else the title.  The placeholders earlier installers wrote
    # live count as unset.
    failures = []
    for overrides, want_h1, want_tab in (
            ({'meta_title': ''}, 'Test Station', 'Test Station'),
            ({'title': 'Acme Weather WeatherBoard&trade;',
              'meta_title': 'Acme Weather at a Glance WeatherBoard&trade;'}, 'Test Station', 'Test Station'),
            ({'title': 'Casa Kline&trade;', 'meta_title': ''}, 'Casa Kline&trade;', 'Casa Kline&trade;'),
            ({'title': 'Casa Kline', 'meta_title': 'The Tab'}, 'Casa Kline', 'The Tab')):
        for tmpl, cls in ((templates[0], 'ro-title'), (templates[1], 'flap-title')):
            html = render(tmpl, overrides=overrides)
            h1 = re.search(r'<h1 class="%s"[^>]*>(.*?)</h1>' % cls, html)
            tab = re.search(r'<title>(.*?)</title>', html)
            if not h1 or h1.group(1) != want_h1:
                failures.append('%s with %s: the title reads %r, expected %r'
                                % (tmpl, overrides, h1 and h1.group(1), want_h1))
            if not tab or tab.group(1) != want_tab:
                failures.append('%s with %s: the tab reads %r, expected %r'
                                % (tmpl, overrides, tab and tab.group(1), want_tab))
    ok = report('the title: title, else the location; the tab: meta_title, else the title', failures) and ok
    # The split-flap lamps' thresholds in the report's own units.  The stub
    # station is metric: km/h and mbar.
    failures = []
    html = render(templates[1])
    for name, want in (('gustWarn', 40.2336), ('baroLow', 1005.76), ('baroHigh', 1022.69)):
        m = re.search(r'%s: ([\d.]+),' % name, html)
        if not m or abs(float(m.group(1)) - want) > 0.05:
            failures.append('%s is %s on a km/h and mbar station, expected about %s'
                            % (name, m and m.group(1), want))
    ok = report("the split-flap lamps' thresholds are in the report's units", failures) and ok

    # The no-analytics render, once: the #if in analytics.inc is the only
    # thing it changes, so one template covers it.  Three renders share one
    # line, so every failure names the render it came from.
    def analytics_render(what, overrides, assertions):
        try:
            html = render(templates[0], analytics=False, overrides=overrides)
        except Exception as e:
            return ['%s: render error: %s' % (what, e)]
        found = ['%s: %s' % (what, f) for f in check(html, templates[0])]
        for complaint, broken in assertions:
            if broken(html):
                found.append('%s: %s' % (what, complaint))
        return found

    failures = analytics_render(
        'no analytics keys', None,
        [('analytics block rendered with no googleAnalyticsId set',
          lambda html: 'googletagmanager' in html)])
    # The installer's stanza ships both analytics settings as EMPTY strings;
    # that must gate the block off exactly as absence does.  An empty
    # password would match every visitor's absent one and the page would
    # never expire, so it must fall back to the default too.
    failures += analytics_render(
        'empty analytics keys and password',
        {'googleAnalyticsId': '', 'analytics_host': '', 'page_update_pwd': ''},
        [('analytics block rendered with an empty googleAnalyticsId',
          lambda html: 'googletagmanager' in html),
         ('an empty page_update_pwd did not fall back to the default',
          lambda html: 'pwd: "foobar",' not in html)])
    # An id with an empty host must configure gtag with no host check: 4.0
    # wrapped it in a check against "", which no page ever matches.
    failures += analytics_render(
        'id with an empty analytics_host',
        {'googleAnalyticsId': 'G-HOSTLESS', 'analytics_host': ''},
        [('the analytics block did not render',
          lambda html: 'googletagmanager' not in html),
         ('the gtag calls were wrapped in a test against the empty host',
          lambda html: 'host == ""' in html),
         ('gtag was not configured with the id',
          lambda html: 'gtag(\'config\', "G-HOSTLESS")' not in html)])
    ok = report('%s analytics absent' % templates[0], failures) and ok
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
        'clock_format': '</script>',
    }
    # The report name is not an Extra, but it reaches the script the same
    # way and a [StdReport] section can be named anything.
    HOSTILE_REPORT = "Weather'Board\"</script>\\ Réport"
    failures = []
    for tmpl in templates:
        try:
            html = render(tmpl, overrides=HOSTILE, report_name=HOSTILE_REPORT)
            failures += ['%s: %s' % (tmpl, f) for f in check(html, tmpl)]
            expected = 'report: ' + json.dumps(HOSTILE_REPORT).replace('<', '\\u003c') + ','
            if expected not in html:
                failures.append('%s: the report name did not reach the page as an escaped literal'
                                % tmpl)
            if html.count('</script') != html.count('<script'):
                failures.append('%s: a script element ended early: %d <script vs %d </script'
                                % (tmpl, html.count('<script'), html.count('</script')))
        except Exception as e:
            failures.append('%s: render error: %s' % (tmpl, e))
    if not esprima:
        failures.append('esprima not importable: the hostile render cannot be parse-checked')
    html = render(templates[0], overrides=HOSTILE, report_name=HOSTILE_REPORT)
    # Exact bytes, deliberately: these pin how jsstr escapes, and a
    # near-miss is a real failure.
    for expected, what in (
            ('if (host == "h\',\\u003c/script>")',
             'a list-valued analytics_host was not joined back with commas'),
            ('gtag/js?id=G-1%27%262%223%3Cx%2Cy"',
             'the analytics src URL is not the percent-encoded list-valued id'),
            ('gtag(\'config\', "G-1\'&2\\"3\\u003cx,y")',
             'the gtag literal is not the escaped list-valued id')):
        if expected not in html:
            failures.append('%s; wanted %r' % (what, expected))
    ok = report('both boards, hostile Extras', failures) and ok
    ok = report('skin.conf declares the loopdata fields the boards read', check_declared_fields()) and ok
    ok = report("the stylesheet's fallbacks for older browsers", check_css_fallbacks()) and ok
    ok = report('the language files carry every string, and what the boards draw fits', check_langs()) and ok
    ok = report('install.py requires weewx-loopdata 7.0, is the release changes.md names'
                ' and installs every skin file',
                check_installer()) and ok
    ok = report("the installer's stanza writes its defaults commented out, and they survive the merge",
                check_stanza()) and ok
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
