# Copyright 2020-2026 by John A Kline <john@johnkline.com>
# Distributed under the terms of the GNU Public License (GPLv3)
# See LICENSE for your rights.

import sys
import weewx
from setup import ExtensionInstaller

def loader():
    if sys.version_info[0] < 3 or (sys.version_info[0] == 3 and sys.version_info[1] < 7):
        sys.exit("weewx-weatherboard requires Python 3.7 or later, found %s.%s" % (
            sys.version_info[0], sys.version_info[1]))

    if weewx.__version__ < "4":
        sys.exit("weewx-weatherboard requires WeeWX 4, found %s" % weewx.__version__)
    return WeatherBoardInstaller()

class WeatherBoardInstaller(ExtensionInstaller):
    def __init__(self):
        super(WeatherBoardInstaller, self).__init__(
            version = "3.0",
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
                            'subtitle'         : '<a style="color:#e51b23;" href="..">Full Site</a> | <a style="color:#e51b23;" href="../about_us.html">About Us</a>',
                            'logo'             : 'paw_logo.png',
                            'loop_data_file'   : '/gauge-data/loop-data.txt',
                            'in_temp_file'     : '/gauge-data/inTemp.txt',
                            'in_co2_file'      : '/gauge-data/inCO2.txt',
                            'in_aqi_file'      : '/gauge-data/inAQI.txt',
                            'in_file_max_age'  : 120,
                            'in_file_slow_host': 'www.paloaltoweather.com',
                            'in_file_slow_max_age': 360,
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
                'skins/WeatherBoard/paw_logo.png',
                'skins/WeatherBoard/realtime_updater.inc',
                'skins/WeatherBoard/realtime_updater2.inc',
                'skins/WeatherBoard/skin.conf',
                'skins/WeatherBoard/updater_common.inc',
                'skins/WeatherBoard/weatherboard.css',
            ])]
        )
