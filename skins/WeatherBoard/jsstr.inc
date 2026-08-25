## Copyright (C)2020-2026 by John A Kline (john@johnkline.com)
## Distributed under the terms of the GNU Public License (GPLv3)
## See LICENSE for your rights.
##
## jsstr: an Extras value as a javascript string literal.  Every setting
## that reaches a <script> goes through this -- the keep-alive password,
## the loop-data URL, the numeric knobs, the analytics ids -- so that
## nothing a user types in weewx.conf can stop the page's javascript from
## parsing.  json.dumps escapes quotes, backslashes and newlines; the
## replace turns < into \u003c, which javascript reads identically but the
## HTML parser does not, so a value containing </script> cannot end the
## script element either.  Escaped, never stripped: the value reaches the
## page as typed.  An unquoted comma, which ConfigObj turns into a list, is
## joined back here minus the whitespace around it; quote such a value in
## weewx.conf to keep it verbatim.
##
## #set global, so the name is visible to every include on the page once
## any one of them has included this file; each consumer includes it
## itself, so a page template needs to know nothing about it.  (A #def in
## a sibling include is NOT visible to the others.)
#errorCatcher Echo
#from json import dumps
## extra_str: the value as one string -- a ConfigObj list joined back with
## the commas it was split on.  jsstr calls it through the placeholder,
## which resolves at call time.
#set global $extra_str = lambda v: ','.join(v) if isinstance(v, list) else str(v)
#set global $jsstr = lambda v: dumps($extra_str(v)).replace('<', '\\u003c')
