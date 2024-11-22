from __future__ import absolute_import
from django.conf.urls import include
from django.urls import re_path
import api.views

urlpatterns = [
     re_path(u'^db_version/$', api.views.db_version),
     re_path(u'^upload/yproto/(?P<city_slug>[\w-]+?/)?$', api.views.upload_yproto),
     re_path(u'^upload/(?P<city_slug>[\w-]+?/)?$', api.views.upload),
     re_path(u'^dump_version/$', api.views.dump_version),
     re_path(u'^ads_control/$', api.views.ads_control),
     re_path(u'^detect_city/$', api.views.detect_city),
     re_path(u'^weather/(?P<city_id>.+)/$', api.views.weather),
     re_path(u'^ip/$', api.views.ip),
     re_path(u'^git/$', api.views.git),
     re_path(u'^headers/$', api.views.headers),
     re_path(u'^jsonrpc/$', api.views.jsonrpc),
     re_path(u'^minime/$', api.views.minime),
     re_path(u'^stops_for_gps/$', api.views.stops_for_gps),
     re_path(u'^notify_stop/$', api.views.notify_stop),
     re_path(u'^bsmart/$', api.views.bsmart),
     re_path(u'^ostapon/$', api.views.ostapon),
     re_path(u'^sms/$', api.views.sms),
     re_path(u'^countries_with_places', api.views.countries_with_places)
]
