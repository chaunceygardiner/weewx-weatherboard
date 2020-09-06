## Copyright (C)2020 by John A Kline (john@johnkline.com)
## Distributed under the terms of the GNU Public License (GPLv3)
## See LICENSE for your rights.

#errorCatcher Echo

    <div id='identifier_widget' class="widget">
      <div class="widget_title">
      </div>
      <div class="widget_contents">
        <div class="footnote" style="color:red;width:100%;">
          <table style="width:95%;">
            <tr>
              <td id="debug_info" style="width:26%;text-align:left;">
                $obs.label.outTemp - $obs.label.dewpoint<br/>
                $obs.label.windSpeed - $obs.label.ten_min_max_gust - $obs.label.high_gust_today<br/>
                $obs.label.UV - $obs.label.barometer<br/>
## FIXME: Convert show_purple to boolean.
#if $Extras.has_key('show_purple') and ($Extras.show_purple == 'True' or $Extras.show_purple == 'true')
                $obs.label.rain_today - $obs.label.rainRate<br/>
                <span style="border-top:1px solid;">$obs.label.legend - $obs.label.air_quality_index - $obs.label.time_of_day</span><br/>
#else
                <span style="border-bottom:1px solid;">$obs.label.rain_today - $obs.label.rainRate</span><br/>
                $obs.label.legend - $obs.label.time_of_day<br/>
#end if
                #include "contact.inc"
              </td>
              <td id="aqi" style="width:9%;font-family:monospace;font-style:normal;font-size:95px;"></td>
              <td id="activity-string" style="width:65%;font-family:monospace;font-style:normal;font-size:95px;text-align:right;"></td>
            </tr>
          </table>
        </div>
      </div>
    </div>
