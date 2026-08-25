## analytics module weewx skins
## Based off of code Copyright Tom Keffer, Matthew Wall
## See LICENSE.txt for your rights
#errorCatcher Echo
#encoding UTF-8

## Include the Google Analytics code if an Id has been specified.  The test
## is a non-empty value, not presence: the installer's stanza ships both
## settings as empty strings, and gating on presence fetched Google's tag
## loader with an empty id on every page load of a default install.
#include "jsstr.inc"
#if $Extras.get('googleAnalyticsId', '')
## The id and host land inside javascript string literals, so they go
## through jsstr like every other Extras value that reaches a <script>.
## The <script src> URL is markup, not javascript, so it needs the other
## kind of escaping: percent-encoded for the query string, which also
## disposes of the & that would otherwise be an unescaped entity reference
## and fail the html validator.
#from urllib.parse import quote
#set $_ga_id_url = $quote($extra_str($Extras.googleAnalyticsId), safe='')
<!-- Global site tag (gtag.js) - Google Analytics -->
<script async src="https://www.googletagmanager.com/gtag/js?id=$_ga_id_url"></script>
<script>
  var host = location.host;
#if $Extras.get('analytics_host', '')
  if (host == $jsstr($Extras.analytics_host)) {
#end if
    window.dataLayer = window.dataLayer || [];
    function gtag(){dataLayer.push(arguments);}
    gtag('js', new Date());
    gtag('config', $jsstr($Extras.googleAnalyticsId));
#if $Extras.get('analytics_host', '')
  }
#end if
</script>
#end if
