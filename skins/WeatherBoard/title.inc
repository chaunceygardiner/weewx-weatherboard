## Copyright (C)2020-2026 by John A Kline (john@johnkline.com)
## Distributed under the terms of the GNU Public License (GPLv3)
## See LICENSE for your rights.
##
## title.inc -- the board's title, and the browser tab's.  Included at the
## top of each page, before its <head>, and writes nothing itself.
##
## The title is the title Extra when it is set, else the station's location
## from weewx.conf.  The browser tab reads meta_title when it is set, else
## the title.  Both may carry HTML entities (&trade;, &amp;), as they always
## have; the title is set in the page as written.
##
## Earlier releases' installers wrote an Acme Weather placeholder into both
## settings, live.  A station that never edited it gets its location, not
## the placeholder.
#errorCatcher Echo
#def wb_setting($name, $placeholders)
#set $v = $Extras.get($name, '')
#if isinstance($v, list)
#set $v = ','.join($v)
#end if
#set $v = str($v).strip()
#if $v == '' or $v in $placeholders
#return ''
#end if
#return $v
#end def
#set global $wb_title = $wb_setting('title', ('Acme Weather WeatherBoard&trade;', 'Acme Weather WeatherBoard™')) or str($station.location)
#set global $wb_tab = $wb_setting('meta_title', ('Acme Weather at a Glance WeatherBoard&trade;', 'Acme Weather at a Glance WeatherBoard™', 'Acme Weather at a Glance')) or $wb_title
