## analytics module weewx skins
## Copyright Tom Keffer, Matthew Wall
## See LICENSE.txt for your rights
#errorCatcher Echo

## Include the Google Analytics code if an Id has been specified

#if $Extras.has_key('googleAnalyticsId')
<!-- Global site tag (gtag.js) - Google Analytics -->
<script async src="https://www.googletagmanager.com/gtag/js?id=$Extras.googleAnalyticsId"></script>
<script>
  #if not($Extras.has_key('host'))
    var host = location.host;
    if (host == "$Extras.analytics_host") {
      window.dataLayer = window.dataLayer || [];
      function gtag(){dataLayer.push(arguments);}
      gtag('js', new Date());
      gtag('config', '$Extras.googleAnalyticsId');
    }
  #else
    window.dataLayer = window.dataLayer || [];
    function gtag(){dataLayer.push(arguments);}
    gtag('js', new Date());
  #end if
</script>
#end if
