# Copyright (C)2026 by John A Kline <john@johnkline.com>
# Distributed under the terms of the GNU Public License (GPLv3)
# See LICENSE for your rights.
"""Offline check for inout.html, the indoor readout board (paloaltoweather
branch only).  check_templates.py holds the skin as a whole -- the fields
declared against what every page reads, the language files, the installer
-- and this renders inout.html.tmpl through the same stub searchList:

  - with every optional reading and with none, and in every language,
    through check_templates.check(): ids, placeholders, ASCII scripts, no
    inline styles, and every script parsing -- and the ids the page paints
    through its own inoutColored(), which check() does not know
  - its UV, radiation and outdoor air quality cells follow the show_
    settings, while the sidecar cells are always there
  - every sidecar setting reaches the page through jsstr, hostile values
    included, and an empty one falls back to its default

Run it as check_templates.py is run, from the WeeWX venv with esprima on
PYTHONPATH:

  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/path/with/esprima \\
      /home/weewx/weewx-venv/bin/python3 tests/check_inout.py

tests/browser_inout.py runs the page.
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_templates as ct                              # noqa: E402

TMPL = 'inout.html.tmpl'
SIDECAR_CELLS = ('ro-in', 'ro-sol', 'ro-co2', 'ro-iaq')


def check_renders():
    failures = []
    for label, missing in (('every optional reading', ct.ALL_PRESENT),
                           ('no optional reading', ct.NONE_PRESENT)):
        try:
            html = ct.render(TMPL, missing)
        except Exception as e:
            failures.append('%s: render error: %s' % (label, e))
            continue
        failures += ['%s: %s' % (label, f) for f in ct.check(html, TMPL, missing)]
        # check() finds the ids painted through readout.inc's helpers; the ids
        # this page paints through its own inoutColored() are checked here.
        declared = set(re.findall(r'id=["\']([^"\']+)["\']', html))
        for cid in re.findall(r"""inoutColored\(\s*'([^']+)'""", html):
            if cid not in declared:
                failures.append('%s: inoutColored paints %s, which the page does not have'
                                % (label, cid))
        present = {'ro-uv': 'UV' not in missing, 'ro-rad': 'radiation' not in missing,
                   'ro-aqi': 'pm2_5_aqi' not in missing}
        for cell in SIDECAR_CELLS:
            present[cell] = True
        for cell, want in sorted(present.items()):
            if ('id="%s"' % cell in html) != want:
                failures.append('%s: the %s cell is %s' % (label, cell, 'missing' if want else 'there'))
    for lang in ct.LANGS:
        try:
            failures += ['%s: %s' % (lang, f) for f in ct.check(ct.render(TMPL, lang=lang), TMPL)]
        except Exception as e:
            failures.append('%s: render error: %s' % (lang, e))
    return failures


SIDECAR_EXTRAS = (('in_temp_file', 'inTemp.txt'), ('in_co2_file', 'inCO2.txt'),
                  ('in_aqi_file', 'inAQI.txt'), ('solar_array_file', 'solar-array.json'),
                  ('in_temp_max_age', None), ('in_co2_max_age', None),
                  ('in_aqi_max_age', None), ('solar_array_max_age', None))


def literal(value):
    """What jsstr writes for a value: a JSON string with < escaped."""
    return json.dumps(value).replace('<', '\\u003c')


def check_settings():
    """Every sidecar setting reaches the script as an escaped literal, a
    hostile one included, and an empty path falls back to its default."""
    failures = []
    hostile = {}
    for i, (key, _dflt) in enumerate(SIDECAR_EXTRAS):
        hostile[key] = "%d'\"\\</script>\n%s" % (i, key)
    try:
        html = ct.render(TMPL, overrides=hostile)
    except Exception as e:
        return ['hostile sidecar settings: render error: %s' % e]
    failures += ['hostile sidecar settings: %s' % f for f in ct.check(html, TMPL)]
    if not ct.esprima:
        failures.append('esprima not importable: the hostile render cannot be parse-checked')
    for key, value in sorted(hostile.items()):
        if literal(value) not in html:
            failures.append('%s did not reach the page as an escaped literal' % key)
    if html.count('</script') != html.count('<script'):
        failures.append('a script element ended early')
    html = ct.render(TMPL, overrides=dict((k, '') for k, _d in SIDECAR_EXTRAS))
    for key, dflt in SIDECAR_EXTRAS:
        if dflt is not None and literal(dflt) not in html:
            failures.append('an empty %s did not fall back to %s' % (key, dflt))
    return failures


def main():
    if ct.esprima is None:
        print('WARNING: esprima not importable; skipping JS syntax checks.')
    ok = ct.report('%s, with and without the optional readings, in every language' % TMPL,
                   check_renders())
    ok = ct.report('%s: the sidecar settings, hostile and empty' % TMPL, check_settings()) and ok
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
