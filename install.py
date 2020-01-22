# Copyright 2020 by John A Kline <john@johnkline.com>
# Distributed under the terms of the GNU Public License (GPLv3)
# See LICENSE for your rights.

from setup import ExtensionInstaller

def loader():
    return WeatherBoardInstaller()

class WeatherBoardInstaller(ExtensionInstaller):
    def __init__(self):
        super(WeatherBoardInstaller, self).__init__(
            version = "1.0",
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
                'skins/WeatherBoard/common_updater.inc',
                'skins/WeatherBoard/contact.inc',
                'skins/WeatherBoard/footer.inc',
                'skins/WeatherBoard/index.html.tmpl',
                'skins/WeatherBoard/realtime_updater.inc',
                'skins/WeatherBoard/skin.conf',
                'skins/WeatherBoard/updater.txt.tmpl',
                'skins/WeatherBoard/weatherboard.css',
            ])]
        )
