# Copyright 2020-2026 by John A Kline <john@johnkline.com>
# Distributed under the terms of the GNU Public License (GPLv3)
# See LICENSE for your rights.

import sys
import weewx
from setup import ExtensionInstaller
from weeutil.weeutil import to_bool

# The loopdata fields WeatherBoard reads.  configure() below adds any that
# are missing from [LoopData][[Include]] fields; it never removes or
# reorders what is already there.
#
# current.dateTime.raw is the epoch the age/LIVE math reads;
# current.dateTime.format("%X") is the clock shown in the lower right,
# rendered by loopdata through the target report's WeeWX formatter so it
# is the STATION's time, not the tablet's.  The board looks for this exact
# field name, so a different strftime string is not a substitute for it:
# pin one and the corner reads ??:??:?? instead.  A locale whose %X carries
# a timezone (the Indian subcontinent and Arabic locales, among others)
# renders wide enough to wrap onto a second line; the lever there is
# weewxd's LANG, not the fields line.
LOOP_DATA_FIELDS = [
    'current.dateTime.raw',
    'current.dateTime.format("%X")',
    'current.outTemp',
    'current.dewpoint',
    'current.windSpeed.formatted',
    'current.windSpeed.raw',
    'current.windDir.ordinal_compass',
    '10m.windGust.max.formatted',
    'day.windGust.max',
    'current.UV.formatted',
    'current.barometer.formatted',
    'trend.barometer.code',
    'day.rain.sum.formatted',
    '24h.rain.sum.formatted',
    'current.rainRate',
    # The indoor board (index2.html.tmpl) reads the same observations
    # through loopdata's .formatted names -- no unit label, so they fit the
    # narrower cells -- and it ships on this branch, so a fresh install has
    # to ask for both spellings or the indoor board comes up all question
    # marks.  current.radiation.formatted is the solar reading, which only
    # the indoor board carries.
    'current.outTemp.formatted',
    'current.dewpoint.formatted',
    'day.windGust.max.formatted',
    'current.rainRate.formatted',
    'current.radiation.formatted',
    # The live logo (logo.inc + paw_logo.js) repaints from the same poll:
    # sun and moon position for the sky it draws, humidity/rain/wind for the
    # weather over it.  These ship only on this branch.
    'almanac.sun.alt',
    'almanac.sun.az',
    'almanac.moon.alt',
    'almanac.moon.az',
    'almanac.moon.phase',
    'almanac.moon_index',
    'almanac.next_full_moon.unix_epoch.raw',
    'almanac.next_new_moon.unix_epoch.raw',
    'current.outHumidity.raw',
    'current.rainRate.raw',
]

# Read only when show_purple is set.  The 1m fields are purple-proxy's
# one-minute averages, which the board prefers when they are present;
# loopdata omits any field the station cannot supply, so naming all four
# costs a station without the proxy nothing.
# The show_purple this extension's own stanza installs.  configure() needs
# the same value: weectl merges the stanza AFTER configure() runs, so on a
# fresh install the setting is not in weewx.conf yet and configure() would
# otherwise fall back to False -- leaving a board whose stanza says True
# with none of the AQI fields, and a ??? in the corner until someone
# installed a second time.  Defined once so the two cannot drift.
STANZA_SHOW_PURPLE = True

PURPLE_FIELDS = [
    'current.pm2_5_1m_aqi.formatted',
    'current.pm2_5_1m_aqi_color.raw',
    'current.pm2_5_aqi.formatted',
    'current.pm2_5_aqi_color.raw',
]

def loader():
    if sys.version_info[0] < 3 or (sys.version_info[0] == 3 and sys.version_info[1] < 7):
        sys.exit("weewx-weatherboard requires Python 3.7 or later, found %s.%s" % (
            sys.version_info[0], sys.version_info[1]))

    if version_tuple(weewx.__version__) < (4, 6):
        sys.exit("weewx-weatherboard requires WeeWX 4.6 or later, found %s" % weewx.__version__)
    return WeatherBoardInstaller()

def version_tuple(version):
    """(4, 6), (4, 10), (5, 0) -- for comparing.  Not a string compare:
    "4.10" sorts BEFORE "4.5" that way.  Trailing non-digits are dropped so
    a pre-release such as 5.0.0b7 compares as (5, 0, 0)."""
    parts = []
    for chunk in version.split('.')[:3]:
        digits = ''
        for ch in chunk:
            if not ch.isdigit():
                break
            digits += ch
        parts.append(int(digits) if digits else 0)
    return tuple(parts)

class WeatherBoardInstaller(ExtensionInstaller):
    def __init__(self):
        super(WeatherBoardInstaller, self).__init__(
            version = "4.0",
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
                            'show_purple'      : STANZA_SHOW_PURPLE,
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

    def configure(self, engine):
        """Add the loopdata fields the board reads to [LoopData][[Include]]
        fields, leaving whatever is already there untouched.

        weectl (WeeWX 5) and wee_extension (WeeWX 4) both call this before
        merging this extension's own stanza, and save weewx.conf only if it
        returns True.  Fields are added, never removed or reordered: the
        fields line is the user's, shared with every other page loopdata
        feeds."""
        config_dict = engine.config_dict
        wanted = self.loop_data_fields(config_dict)
        if 'LoopData' not in config_dict:
            # loopdata isn't installed.  Nothing to add to, so say what the
            # board will need once it is.
            print('weatherboard: [LoopData] not found in weewx.conf.')
            print('weatherboard: Install weewx-loopdata 6.0 or later, then install')
            print('weatherboard: weatherboard again -- this step adds the fields the')
            print('weatherboard: board reads.  Installing loopdata SECOND matters:')
            print('weatherboard: its installer writes a fields line of its own, and')
            print('weatherboard: weectl will not overwrite one that already exists,')
            print('weatherboard: so the board\'s fields would be left out.')
            print('weatherboard: The fields, should you prefer to add them by hand:')
            print('weatherboard:     %s' % ', '.join(wanted))
            return False
        loop_data_dict = config_dict['LoopData']
        include_dict = loop_data_dict.get('Include')
        if not isinstance(include_dict, dict):
            # [LoopData] is there but [[Include]] is missing -- or, absurdly,
            # is a scalar.  A scalar is not something to guess at: say so and
            # leave it alone rather than overwriting whatever it means.  The
            # guard is here because weectl copies the skin files before it
            # calls configure(), so raising would leave the extension
            # installed and weewx.conf untouched.  Config shapes absurd
            # enough to be unreachable in practice (a scalar [LoopData], a
            # scalar Extras) are not guarded.
            if include_dict is not None:
                print('weatherboard: [LoopData] Include is not a section; leaving it alone.')
                print('weatherboard: Add these fields to [LoopData] [[Include]] fields:')
                print('weatherboard:     %s' % ', '.join(wanted))
                return False
            if engine.dry_run:
                print('weatherboard: Would create [LoopData] [[Include]] in'
                      ' weewx.conf with fields: %s' % ', '.join(wanted))
                return False
            print('weatherboard: Creating [LoopData] [[Include]] in weewx.conf.')
            loop_data_dict['Include'] = {'fields': list(wanted)}
            print('weatherboard: Added to [LoopData] [[Include]] fields: %s' % ', '.join(wanted))
            return True
        fields = include_dict.get('fields', [])
        if not isinstance(fields, list):
            # ConfigObj hands back a plain string for a one-entry list.
            fields = [fields] if fields else []
        missing = [f for f in wanted if f not in fields]
        if not missing:
            return False
        if engine.dry_run:
            print('weatherboard: Would add to [LoopData] [[Include]] fields: %s'
                  % ', '.join(missing))
            return False
        include_dict['fields'] = fields + missing
        print('weatherboard: Added to [LoopData] [[Include]] fields: %s' % ', '.join(missing))
        return True

    @staticmethod
    def loop_data_fields(config_dict):
        """The fields to require of loopdata.  The AQI fields are included
        for a station that has already turned show_purple on -- and, on a
        fresh install, for the value this extension's own stanza is about
        to install, since weectl merges that stanza only after configure()
        has run."""
        fields = list(LOOP_DATA_FIELDS)
        try:
            extras = config_dict['StdReport']['WeatherBoardReport']['Extras']
        except KeyError:
            # No stanza at all: a fresh install, and weectl merges this
            # extension's own stanza only after configure() has run.  Use
            # the value that stanza is about to write, or the AQI fields
            # would be left out of a board whose config says to show them.
            show_purple = STANZA_SHOW_PURPLE
        else:
            # A stanza is already there.  A missing show_purple means the
            # user removed it or predates it, and skin.conf's default --
            # False -- is what the report will render with, so match that
            # rather than assuming this branch's stanza value.
            show_purple = extras.get('show_purple', False)
        try:
            show_purple = to_bool(show_purple)
        except ValueError:
            show_purple = False
        if show_purple:
            fields += PURPLE_FIELDS
        return fields
