# weewx-weatherboard
WeatherBoard&trade; is a skin for WeeWX inspired by the RainWise LED Weather Oracle display.

It's perfect to display continuously on a low-cost tablet mounted on the wall.

WeatherBoard displays a small set of critical weather information that is easy to read from
accross the room.

* Does the wind sound ferocious?
  * Check the WeatherBoard to see how fast it is gusting.

* Is the rain coming down hard?
  * Check the WeatherBoard for the current rate of rainfall and today's total rain.

## Description

Copyright (C)2020 by John A Kline (john@johnkline.com)

**WeatherBoard 2.x requires LoopData 2.x.  It will not work with LoopData 1.x.**

The WeatherBoard&trade; sking provides a simple one page skin that shows:
* Current Outside Temperature
* Current Dew Point
* Current Wind Speed and Direction
* 10 Minute High Wind Gust
* Today's High Wind Gust
* Today's Total Rainfall
* Current Rain Rate
* Air Quality Indicator (If [weewx-purple](https://github.com/chaunceygardiner/weewx-purple) is installed.)

The inspiration for this skin is the RainWise LED Weather Oracle display.

Following is a screen shot of the WeatherBoard&trade; skin if a PurpleAir sensor is configured.

![WeatherBoard screen shot](WeatherBoard.png)

Following is a screen shot of the WeatherBoard&trade; skin if a PurpleAir sensor is *NOT* configured.

![WeatherBoard (no AQI) screen shot](WeatherBoard_no_aqi.png)

## Additional Requirements
* [WeeWX 4.x](https://github.com/weewx/weewx)
* [weewx-loopdata](https://github.com/chaunceygardiner/weewx-loopdata)
* Python 3.7 (because weewx-loopdata requires Python 3.7).

## Additional Requirements for Air Quality Indictator (AQI) Readings on the Report
* [weewx-purple](https://github.com/chaunceygardiner/weewx-purple)

## Additional Requirements to Display AQI Averages over the Report Interval and to Catchup on AQI Readings when WeeWX Starts
* [purple-proxy](https://github.com/chaunceygardiner/purple-proxy)

# Installation Instructions

1. Install [weewx-loopdata](https://github.com/chaunceygardiner/weewx-loopdata)
   per the installagtion instructions in the weewx-loopdata README.

1. The loopdata install defaults to a target report of `LoopDataReport`.
   Coveniently, `WeatherBoardReport` is similar to `LoopDataReport`.
   The loopdata install also adds all of the fields needed for
   WeatherBoard report.  As such you probably won't need to make the following
   changes:
      `[[LoopData]]`
          `target_report = WeatherBoardReport`
          `fields = current.dateTime.raw, current.windDir.ordinal_compass, day.rain.sum, current.dewpoint, current.outTemp, current.rainRate, current.windSpeed, current.windSpeed.raw, 10m.windGust.max, day.windGust.max`

1. Download the lastest release, weewx-weatherboard-2.0.zip, from the
   [GitHub Repository](https://github.com/chaunceygardiner/weewx-weatherboard).

1. Run the following command.

   `sudo /home/weewx/bin/wee_extension --install weewx-weatherboard-2.0.zip`

   Note: this command assumes weewx is installed in /home/weewx.  If it's installed
   elsewhere, adjust the path of wee_extension accordingly.

1. The install creates the following section in `weewx.conf`.

```
    [[WeatherBoardReport]]
        HTML_ROOT = public_html/weatherboard
        enable = true
        skin = WeatherBoard
        [[[Extras]]]
            title = my-weather-website.com WeatherBoard&trade;
            subtitle = Updated continuously
            logo = ""
            loop_data_file = ../loopdata/loop-data.txt
            contact_email = weatherguy@my-weather-website.com
            expiration_time = 4
            page_update_pwd = foobar
            googleAnalyticsId = ""
            analytics_host = ""
            show_purple = False
        [[[Units]]]
            [[[[StringFormats]]]]
                mile_per_hour = %.1f
                degree_C = %.1f
                km_per_hour = %.1f
                degree_F = %.1f
```

1. Edit the `Extras` section of the `WeatherBoard` section of `weewx.conf`.
   Update the `title`, `subtitle`, `loop_data_file`, `contact_email` and
   `page_udpate_pwd` as to appropriate values.  (Note: the `page_update_pwd` is
   used on the URL in order to keep WeatherBoard from timing out.)

1. If your site has a logo (image file), update `logo` with the path to the image.

1. If you with to wire up Google Analytics, fill in `googleAnalyticsId` and, optionally,
   `analytics_host`.

1. Restart WeeWx


## Licensing

weewx-loopdata is licensed under the GNU Public License v3.
