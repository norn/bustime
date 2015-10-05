from django.conf.urls import patterns, include, url

urlpatterns = patterns('',
     url(u'^db_version/$', 'api.views.db_version'),
     url(u'^dump_version/$', 'api.views.dump_version'),
     url(u'^ads_control/$', 'api.views.ads_control'),
     url(u'^detect_city/$', 'api.views.detect_city'),
     url(u'^weather/(?P<city_id>.+)/$', 'api.views.weather'),
)
