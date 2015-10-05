# -*- coding: utf-8 -*-
from django.conf.urls import patterns, include, url
from django.views.generic import TemplateView
from django.contrib import admin
admin.autodiscover()
#from django.contrib.sitemaps.views import sitemap

urlpatterns = patterns('',
     url(r'^$', 'bustime.views.home', {'template_name':"index.html"}, name='home'),
     url(r'^radar/$', 'bustime.views.radar', name='radar'),
     # url(r'^mdl/$', 'bustime.views.home', {'template_name':"index-mdl.html"}, name='mdl'),

     url(u'^ajax/tcard/(?P<num>\d+)/$', 'bustime.views.ajax_tcard'),
     url(u'^ajax/card/(?P<num>\d+)/$', 'bustime.views.ajax_card'),
     url(u'^ajax/metric/$', 'bustime.views.ajax_metric'),
     url(u'^ajax/stop_ids/$', 'bustime.views.ajax_stop_ids'),
     url(u'^ajax/stops_by_gps/$', 'bustime.views.ajax_stops_by_gps'),
     url(u'^ajax/timer/$', 'bustime.views.ajax_timer'),
     url(u'^ajax/busfavor/$', 'bustime.views.ajax_busfavor'),
     url(u'^ajax/busdefavor/$', 'bustime.views.ajax_busdefavor'),
     url(u'^ajax/settings/$', 'bustime.views.ajax_settings'),
     url(u'^ajax/bootstrap_amounts/$', 'bustime.views.ajax_bootstrap_amounts'),
     url(u'^ajax/bus/$', 'bustime.views.ajax_bus'),
     url(u'^ajax/stop_destination/$', 'bustime.views.ajax_stop_destination'),
     url(u'^ajax/position_watch/$', 'bustime.views.ajax_position_watch'),
     url(u'^ajax/radio_position/$', 'bustime.views.ajax_radio_position'),
     url(u'^ajax/vk_like_pro/$', 'bustime.views.ajax_vk_like_pro'),
     url(u'^ajax/radar/$', 'bustime.views.ajax_radar'),
     url(u'^ajax/ava_change/$', 'bustime.views.ajax_ava_change'),
     url(u'^ajax/vote_comment/$', 'bustime.views.ajax_vote_comment'),
     url(u'^ajax/rate/$', 'bustime.views.ajax_rate'),
     url(u'^ajax/rating_get/$', 'bustime.views.ajax_rating_get'),

#     url(u'^us/turn-on-premium/$', 'bustime.views.us_turn_on_premium'),
     url(u'^us/reset-bus-favorites/$', 'bustime.views.reset_busfavor'),
     #url(u'^realtime-(?P<city_id>\d+).kml/$', 'bustime.views.realtime_km'),
    # url(u'^realtime-kml/(?P<city_id>\d+)/$', 'bustime.views.realtime_kml'),
     #url(u'^busstopedit/$', 'bustime.views.busstop_edit'),
     ##
     url(u'^about/$', 'bustime.views.about'),
     url(u'^help/$', 'bustime.views.help_view'),
     url(u'^contacts/$', 'bustime.views.contacts'),
     url(u'^pro/$', 'bustime.views.pro'),
     url(u'^pro-demo/$', 'bustime.views.pro_demo'),
     url(u'^pin/$', 'bustime.views.pin'),
     url(u'^icon-editor/$', 'bustime.views.icon_editor'),
     url(r'^classic/$', 'bustime.views.classic_index', name='classic_index'),
     url(r'^settings/$', 'bustime.views.settings_view'),

     # we love search engine optimization
     url(u'^(?P<city_name>[\w-]+)/rating/((?P<for_date>[0-9-]+)/)?(page-(?P<page>[0-9]+)/)?$', 'bustime.views.rating'),
     url(u'^(?P<city_name>[\w-]+)/monitor/$', 'bustime.views.monitor'),
     url(u'^(?P<city_name>[\w-]+)/schedule/$', 'bustime.views.schedule'),
     url(u'^(?P<city_name>[\w-]+)/schedule/(?P<bus_id>[\w-]+)/$', 'bustime.views.schedule_bus'),
     url(r'^(?P<city_name>[\w-]+)/classic/$', 'bustime.views.classic_routes', name='classic_routes'),
     url(r'^(?P<city_name>[\w-]+)/classic/(?P<bus_id>[\w-]+)/$', 'bustime.views.classic_bus'),

     # keep for month or two, from 18.08.2015
     url(u'^расписание/(?P<city_name>[\w-]+)/$', 'bustime.views.schedule_'),
     url(u'^расписание/(?P<city_name>[\w-]+)/(?P<bus_id>\d+)/$', 'bustime.views.schedule_bus_'),
     url(u'^rating/(?P<for_date>.+)/$', 'bustime.views.rating_'),
     url(u'^rating/$', 'bustime.views.rating_'),

     # keep for month or two, from 05.09.2015
     url(u'^(?P<city_name>[\w-]+)/расписание/(?P<bus_id>\d+)/$', 'bustime.views.schedule_bus', {'old_url':True}),
     url(u'^(?P<city_name>[\w-]+)/расписание/$', 'bustime.views.schedule', {'old_url':True}),
     url(u'^(?P<city_name>[\w-]+)/рейтинг/((?P<for_date>[0-9-]+)/)?$', 'bustime.views.rating', {'old_url':True}),
     url(u'^казань/$', 'bustime.views.city_slug_redir', {'force_city':10}),
     url(u'^калининград/$', 'bustime.views.city_slug_redir', {'force_city':4}),
     url(u'^кемерово/$', 'bustime.views.city_slug_redir', {'force_city':8}),
     url(u'^красноярск/$', 'bustime.views.city_slug_redir', {'force_city':3}),
     url(u'^пермь/$', 'bustime.views.city_slug_redir', {'force_city':9}),
     url(u'^санкт-петербург/$', 'bustime.views.city_slug_redir', {'force_city':5}),
     url(u'^томск/$', 'bustime.views.city_slug_redir', {'force_city':7}),
     url(u'^city-monitor/$', 'bustime.views.monitor'),
     url(r'^classic/b/(?P<bus_id>\d+)/$', 'bustime.views.classic_bus', {'old_url':True}),
     url(r'^classic/(?P<city_id>\d+)/$', 'bustime.views.classic_routes', name='classic_routes'),

     url(r'^MzsMi7n8W4/', include(admin.site.urls)),
     url(r'^MzsMi7n8W4/backoffice/', include('backoffice.urls')),
     url(r'^api/', include('api.urls')),
#     url(r'^sitemap2\.xml$', sitemap, {'sitemaps': sitemaps},
#         name='django.contrib.sitemaps.views.sitemap')
     
     # total recall
     url(u'^(?P<city_name>[\w-]+)/$', 'bustime.views.home'),
)
