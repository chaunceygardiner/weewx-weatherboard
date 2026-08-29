# Copyright 2020-2026 by John A Kline <john@johnkline.com>
# Distributed under the terms of the GNU Public License (GPLv3)
# See LICENSE for your rights.

import io
import sys

import configobj

import weewx
from setup import ExtensionInstaller

# The oldest weewx-loopdata whose loop-data.txt carries this report's own
# entry: since 7.0 a report declares the fields it needs in its skin.conf
# ([LoopData] [[fields]] there) and loopdata writes them under the report's
# name.  The pages read that entry and nothing else, so an older loopdata
# -- which writes only the flat keys of the [[Include]] fields line -- would
# leave every reading at question marks.  Refuse to install instead.
LOOP_DATA_REQUIRED = (7, 0)

def loader():
    if sys.version_info[0] < 3 or (sys.version_info[0] == 3 and sys.version_info[1] < 7):
        sys.exit("weewx-weatherboard requires Python 3.7 or later, found %s.%s" % (
            sys.version_info[0], sys.version_info[1]))

    if version_tuple(weewx.__version__) < (4, 6):
        sys.exit("weewx-weatherboard requires WeeWX 4.6 or later, found %s" % weewx.__version__)

    # Only an INSTALL is gated on loopdata.  WeeWX runs an installed
    # extension's loader() again for `weectl extension list` and `weectl
    # extension uninstall` (wee_extension's --list and --uninstall), from
    # the copy of this file it keeps under user/installer/, and catches
    # only its own ExtensionError -- so a refusal there would leave the
    # board unlistable and unremovable once loopdata had been removed or
    # downgraded.  The two checks above cannot regress after an install
    # (the same Python and WeeWX run weectl afterwards); this one can.
    if installing():
        # weectl (WeeWX 5) and wee_extension (WeeWX 4) both have the
        # station's user directory on sys.path by the time they call
        # loader(), so user.loopdata is importable exactly when loopdata is
        # installed.
        try:
            from user.loopdata import LOOP_DATA_VERSION
        except ImportError as e:
            # Only a missing module means loopdata is not installed.  An
            # ImportError raised from INSIDE an installed loopdata -- a
            # dependency of its own it cannot find, a half-finished upgrade
            # -- would otherwise be reported as "not installed", telling
            # the user to install what they already have.
            if isinstance(e, ModuleNotFoundError) and e.name in ('user', 'user.loopdata'):
                sys.exit("weewx-weatherboard requires weewx-loopdata %s or later, which is not"
                         " installed (%s).  Install weewx-loopdata first, then install"
                         " weewx-weatherboard."
                         % ('.'.join(str(n) for n in LOOP_DATA_REQUIRED), e))
            sys.exit("weewx-weatherboard requires weewx-loopdata %s or later.  It is installed,"
                     " but importing it failed: %s.  Fix that, then install weewx-weatherboard."
                     % ('.'.join(str(n) for n in LOOP_DATA_REQUIRED), e))
        if version_tuple(LOOP_DATA_VERSION) < LOOP_DATA_REQUIRED:
            sys.exit("weewx-weatherboard requires weewx-loopdata %s or later, found %s."
                     "  Upgrade weewx-loopdata first, then install weewx-weatherboard."
                     % ('.'.join(str(n) for n in LOOP_DATA_REQUIRED), LOOP_DATA_VERSION))
    return WeatherBoardInstaller()

def installing():
    """True when the command line is installing an extension.  weectl spells
    it `extension install`; wee_extension (optparse) takes `--install FILE`,
    `--install=FILE`, and any unambiguous prefix of the option, `--inst`
    included -- so anything starting with `--i` counts, there being no other
    wee_extension option that starts that way."""
    return any(arg == 'install' or arg.startswith('--i') for arg in sys.argv)

def version_tuple(version):
    """(4, 6, 0), (4, 10, 0), (5, 0, 0) -- for comparing.  Not a string
    compare: "4.10" sorts BEFORE "4.5" that way.  Trailing non-digits are
    dropped so a pre-release such as 5.0.0b7 compares as (5, 0, 0), and the
    tuple is always three long so that a bare "7" is (7, 0, 0), which is
    not less than (7, 0) -- (7,) would be."""
    parts = []
    for chunk in version.split('.')[:3]:
        digits = ''
        for ch in chunk:
            if not ch.isdigit():
                break
            digits += ch
        parts.append(int(digits) if digits else 0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts)

# The stanza weectl merges into weewx.conf, as text rather than a dict so
# that these comments travel with it.  weectl's merge fills in absent keys
# and never rewrites a present one, so an option written LIVE here freezes
# every fresh install on today's default for ever, while one written
# COMMENTED OUT leaves the skin's own value -- skin.conf, which an upgrade
# replaces -- to answer, so a later release can improve a default and have
# it reach every station.  The options that stay live are HTML_ROOT, enable
# and skin (weectl needs them), the branding and the two analytics keys
# (placeholders to fill in), loop_data_file and page_update_pwd.
#
# A commented option needs a live key after it in the same section: weectl
# attaches a comment block to the NEXT key and drops it entirely if the
# target already has that key.  page_update_pwd anchors [[[Extras]]].
CONFIG = """
[StdReport]
    [[WeatherBoardReport]]
        HTML_ROOT = weatherboard
        enable = true
        skin = WeatherBoard
        [[[Extras]]]
            # NOTE (paloaltoweather branch): these are John's SITE values so
            # a fresh install comes up as PaloAltoWeather.com turnkey -- only
            # page_update_pwd needs editing.  Master carries generic public
            # defaults here instead.
            #
            # The branding across the top of the board and in the browser's
            # title bar.  HTML entities are allowed.  The subtitle's links
            # inherit the subtitle gray from weatherboard.css (.lastupdate a);
            # no inline styles.
            meta_title = PaloAltoWeather.com Weather at a Glance&mdash;WeatherBoard&trade;
            title = PaloAltoWeather.com WeatherBoard&trade;
            subtitle = <a href="..">Full Site</a> | <a href="../about_us.html">About Us</a>
            # 'mono' for the monochrome title band; anything else is the
            # color logo.
            title_theme = color
            # Where the page fetches loop data from, as a URL the browser
            # resolves.  These are this site's paths, served from the web
            # server's own /loop-data, not relative to HTML_ROOT.
            loop_data_file = /loop-data/loop-data.txt
            # The indoor board's four sidecar files, each a single reading
            # written outside this skin: the AirGradient trio and the solar
            # array's production.  URL params inTempFile / inCO2File /
            # inAQIFile override the first three.
            in_temp_file = /loop-data/inTemp.txt
            in_co2_file = /loop-data/inCO2.txt
            in_aqi_file = /loop-data/inAQI.txt
            solar_array_file = /loop-data/solar-array.json
            # How stale each sidecar reading may be, in seconds, before it
            # shows question marks.  The AirGradient trio is written by a
            # ~30 s cron; the solar file is rewritten every 15 s but carries
            # Enphase data already a minute old, hence its larger limit.
            in_temp_max_age = 120
            in_co2_max_age = 120
            in_aqi_max_age = 120
            solar_array_max_age = 150
            # The four settings below only select the value skin.conf
            # already ships, so they ship commented out with that value
            # shown.  Uncomment one and change it to override it.
            #
            # How old the loop record may be, in seconds, before the
            # readings it feeds show question marks instead.  The default
            # suits a station emitting loop packets every couple of
            # seconds; raise it for a slower one.
            #max_age = 10
            # The clock's own, longer threshold, in seconds: a temperature
            # a minute old is a stale reading, while a clock a minute slow
            # is still a clock.  Never sits below max_age.
            #clock_max_age = 120
            # Hours before a page WITHOUT the keep-alive password on its
            # URL stops polling.  It then shows Expired, and a click starts
            # it again.
            #expiration_time = 4
            # Seconds between polls.  A good choice is the rate at which
            # your station's driver emits loop packets.  Never armed faster
            # than once a second, whatever is set.
            #refresh_rate = 2
            # Live, not commented, unlike the four above: skin.conf ships
            # False and this site's boards want the air quality reading, so
            # the value here is the one that has to answer.
            show_purple = True
            # With an ID set, the board loads Google Analytics.
            # analytics_host restricts that to one hostname, which keeps a
            # development copy of the page out of the statistics.
            googleAnalyticsId = G-C2EGLPRF51
            analytics_host = www.paloaltoweather.com
            # Put this on the URL as ?page_update_pwd=... and the page
            # never expires -- what a wall-mounted tablet wants.  Change it
            # from the shipped placeholder.  It is visible in the page
            # source by design: a keep-alive gate, not a secret.
            page_update_pwd = foobar
        # These four are the formats the board's fixed-width columns are
        # built around, and they are pinned HERE, live, on purpose.  They
        # match WeeWX's own defaults, so on an ordinary station they change
        # nothing; what they do is keep a station that set different
        # formats site-wide in [[Defaults]] from widening a column past the
        # room the layout gives it.  A report's own stanza is the only
        # place that can hold that pin -- skin.conf loses to [[Defaults]].
        [[[Units]]]
            [[[[StringFormats]]]]
                mile_per_hour = %.0f
                degree_C = %.1f
                km_per_hour = %.0f
                degree_F = %.1f
"""


def installer_config():
    """The stanza as weectl wants it: a ConfigObj, comments and all."""
    return configobj.ConfigObj(io.StringIO(CONFIG), encoding='utf-8')


class WeatherBoardInstaller(ExtensionInstaller):
    def __init__(self):
        super(WeatherBoardInstaller, self).__init__(
            version = "4.2",
            name = 'weatherboard',
            description = 'WeatherBoard skin.',
            author = "John A Kline",
            author_email = "john@johnkline.com",
            config = installer_config(),
            files = [('skins/WeatherBoard', [
                'skins/WeatherBoard/analytics.inc',
                'skins/WeatherBoard/apple-touch-icon-180x180.png',
                'skins/WeatherBoard/favicon.ico',
                'skins/WeatherBoard/footer.inc',
                'skins/WeatherBoard/footer2.inc',
                'skins/WeatherBoard/index.html.tmpl',
                'skins/WeatherBoard/index2.html.tmpl',
                'skins/WeatherBoard/jsstr.inc',
                'skins/WeatherBoard/logo.inc',
                'skins/WeatherBoard/paw_logo.js',
                'skins/WeatherBoard/paw_logo_mono.js',
                'skins/WeatherBoard/realtime_updater.inc',
                'skins/WeatherBoard/realtime_updater2.inc',
                'skins/WeatherBoard/skin.conf',
                'skins/WeatherBoard/updater_common.inc',
                'skins/WeatherBoard/weatherboard.css',
            ])]
        )
