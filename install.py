# Copyright 2020-2026 by John A Kline <john@johnkline.com>
# Distributed under the terms of the GNU Public License (GPLv3)
# See LICENSE for your rights.

import sys
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

class WeatherBoardInstaller(ExtensionInstaller):
    def __init__(self):
        super(WeatherBoardInstaller, self).__init__(
            version = "4.1",
            name = 'weatherboard',
            description = 'WeatherBoard skin.',
            author = "John A Kline",
            author_email = "john@johnkline.com",
            config = {
                'StdReport': {
                    'WeatherBoardReport': {
                        'HTML_ROOT':'weatherboard',
                        'enable': 'true',
                        'skin':'WeatherBoard',
                        # NOTE (paloaltoweather branch): these are John's SITE values so
                        # a fresh install comes up as PaloAltoWeather.com turnkey (only
                        # page_update_pwd needs editing in weewx.conf).  The master
                        # branch carries generic public defaults here instead.
                        'Extras': {
                            'meta_title'       : 'PaloAltoWeather.com Weather at a Glance&mdash;WeatherBoard&trade;',
                            'title'            : 'PaloAltoWeather.com WeatherBoard&trade;',
                            # Subtitle links inherit the subtitle gray via
                            # weatherboard.css (.lastupdate a) -- no inline
                            # styles here.
                            'subtitle'         : '<a href="..">Full Site</a> | <a href="../about_us.html">About Us</a>',
                            'title_theme'      : 'color',
                            'loop_data_file'   : '/loop-data/loop-data.txt',
                            'max_age'          : 10,
                            'clock_max_age'    : 120,
                            'in_temp_file'     : '/loop-data/inTemp.txt',
                            'in_co2_file'      : '/loop-data/inCO2.txt',
                            'in_aqi_file'      : '/loop-data/inAQI.txt',
                            'solar_array_file' : '/loop-data/solar-array.json',
                            'in_temp_max_age'  : 120,
                            'in_co2_max_age'   : 120,
                            'in_aqi_max_age'   : 120,
                            'solar_array_max_age': 150,
                            'expiration_time'  : 4,
                            'page_update_pwd'  : 'foobar',
                            'googleAnalyticsId': 'G-C2EGLPRF51',
                            'analytics_host'   : 'www.paloaltoweather.com',
                            'show_purple'      : True,
                            'refresh_rate'     : 2,
                        },
                        'Labels': {
                            'Generic': {
                                'air_quality_index': 'Air Quality Index',
                                'legend'           : 'Legend',
                                'rainToday'        : 'Rain Today',
                                'rain24h'          : 'Rain 24h',
                                'ten_min_max_gust' : '10m Gust',
                                'time_of_day'      : 'Time',
                                'high_gust_today'  : "Today's High Gust",
                            },
                        },
                        'Units' : {
                            'StringFormats': {
                                'mile_per_hour': '%.0f',
                                'degree_C': '%.1f',
                                'km_per_hour': '%.0f',
                                'degree_F': '%.1f',
                            },
                        },
                    },
                },
            },
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
