# Copyright 2020 by John A Kline <john@johnkline.com>
# Distributed under the terms of the GNU Public License (GPLv3)
# See LICENSE for your rights.

from setup import ExtensionInstaller

def loader():
    return WeatherBoardInstaller()

class WeatherBoardInstaller(ExtensionInstaller):
    def __init__(self):
        super(WeatherBoardInstaller, self).__init__(
            version = "1.3",
            name = 'weatherboard',
            description = 'WeatherBoard skin.',
            author = "John A Kline",
            author_email = "john@johnkline.com",
            config = {
                'StdReport': {
                    'WeatherBoardReport': {
                        'HTML_ROOT':'public_html/weatherboard',
                        'enable': 'true',
                        'skin':'WeatherBoard',
                        'Extras': {
                            'meta_title'       : 'my-weather-website.com Weather at a Glance WeatherBoard&trade;',
                            'title'            : 'my-weather-website.com WeatherBoard&trade;',
                            'subtitle'         : 'Updated continuously.',
                            'logo'             : '',
                            'loop_data_file'   : '../loop-data.txt',
                            'contact_email'    : 'weatherguy@my-weather-website.com',
                            'expiration_time'  : 4,
                            'page_update_pwd'  : 'foobar',
                            'googleAnalyticsId': '',
                            'analytics_host'   : '',
                            'show_purple'      : False,
                        },
                        'Labels': {
                            'Generic': {
                                'air_quality_index': 'Air Quality Index',
                                'contact'          : 'Contact',
                                'legend'           : 'Legend',
                                'rain_today'       : 'Rain Today',
                                'ten_min_max_gust' : '10m Gust',
                                'time_of_day'      : 'Time',
                                'high_gust_today'  : "Today's High Gust",
                            },
                        },
                        'Units' : {
                            'StringFormats': {
                                'mile_per_hour': '%.1f',
                                'degree_C': '%.1f',
                                'km_per_hour': '%.1f',
                                'degree_F': '%.1f',
                            },
                        },
                    },
                },
            },
            files = [('skins/WeatherBoard', [
                'skins/WeatherBoard/analytics.inc',
                'skins/WeatherBoard/contact.inc',
                'skins/WeatherBoard/favicon.ico',
                'skins/WeatherBoard/footer.inc',
                'skins/WeatherBoard/index.html.tmpl',
                'skins/WeatherBoard/realtime_updater.inc',
                'skins/WeatherBoard/skin.conf',
                'skins/WeatherBoard/weatherboard.css',
            ])]
        )
