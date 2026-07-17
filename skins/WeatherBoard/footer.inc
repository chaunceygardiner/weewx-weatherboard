## Copyright (C)2019-2026 by John A Kline (john@johnkline.com)
## Distributed under the terms of the GNU Public License (GPLv3)
## See LICENSE for your rights.

#errorCatcher Echo

    <div id='identifier_widget' class="widget">
      <div class="widget_title">
      </div>
      <div class="widget_contents">
        <div class="footnote">
          <table class="board-footer">
            <tr>
              <td id="debug_info">
                $obs.label.outTemp - $obs.label.dewpoint<br>
                $obs.label.windSpeed - $obs.label.ten_min_max_gust - $obs.label.high_gust_today<br>
                $obs.label.UV - $obs.label.barometer<br>
## FIXME: Convert show_purple to boolean.
#if $Extras.has_key('show_purple') and ($Extras.show_purple == 'True' or $Extras.show_purple == 'true')
                $obs.label.rainToday - $obs.label.rain24h - $obs.label.rainRate<br>
                <span class="overline">$obs.label.legend - $obs.label.air_quality_index - $obs.label.time_of_day</span><br>
#else
                <span class="underline">$obs.label.rain24h - $obs.label.rainRate</span><br>
                $obs.label.legend - $obs.label.time_of_day<br>
#end if
                <span>&copy;2019-2026 by John A Kline.</span>
              </td>
              <td id="aqi"></td>
              <td id="activity-string"></td>
            </tr>
          </table>
        </div>
      </div>
    </div>
