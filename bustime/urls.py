# -*- coding: utf-8 -*-
from __future__ import absolute_import
from django.conf.urls import include
from django.urls import re_path
from django.views.generic import TemplateView
from django.contrib import admin
from django.conf.urls import handler404
from debug_toolbar.toolbar import debug_toolbar_urls
admin.autodiscover()
import bustime.views

admin.site.site_header = 'Bustime'
admin.site.index_title = 'Bustime'
admin.site.site_title = 'Bustime'
handler404 = bustime.views.custom_handler404


urlpatterns = [
     re_path(r'^api/', include('api.urls')),
     re_path(r'^$', bustime.views.turbo_select, name='turbo_select'),
     re_path(r'^wiki/rosetta/', include('rosetta.urls')),
     re_path(r'^wiki/backoffice/', include('backoffice.urls')),
     re_path(r'^wiki/', admin.site.urls),
     re_path(r'^radar/$', bustime.views.radar, name='radar'),
     re_path(r'^(?P<place_slug>[\w-]+)/settings/(?P<other>[\d]+)/$', bustime.views.settings_view),
     # taxi
     re_path(r'^carpool/', include('taxi.urls')),
     re_path(u'^ajax/tcard/(?P<num>\d+)/$', bustime.views.ajax_tcard),
     re_path(u'^ajax/card/(?P<num>\d+)/$', bustime.views.ajax_card),
     re_path(u'^ajax/metric/$', bustime.views.ajax_metric),
     re_path(u'^ajax/stop_ids/$', bustime.views.ajax_stop_ids),
     re_path(u'^ajax/stops_by_gps/$', bustime.views.ajax_stops_by_gps),
     re_path(u'^ajax/timer/$', bustime.views.ajax_timer),
     re_path(u'^ajax/busfavor/$', bustime.views.ajax_busfavor),
     re_path(u'^ajax/busdefavor/$', bustime.views.ajax_busdefavor),
     re_path(u'^ajax/settings/$', bustime.views.ajax_settings),
     re_path(u'^ajax/ajax_settings1/$', bustime.views.ajax_settings1),
     re_path(u'^ajax/bootstrap_amounts/$', bustime.views.ajax_bootstrap_amounts),
     re_path(u'^ajax/bus/$', bustime.views.ajax_bus),
     re_path(u'^ajax/stop_destination/$', bustime.views.ajax_stop_destination),
     re_path(u'^ajax/radio_position/$', bustime.views.ajax_radio_position),
     re_path(u'^ajax/vk_like_pro/$', bustime.views.ajax_vk_like_pro),
     re_path(u'^ajax/radar/$', bustime.views.ajax_radar),
     re_path(u'^ajax/busstop_resolver/$', bustime.views.ajax_busstop_resolver),
     re_path(u'^ajax/gvote/$', bustime.views.ajax_gvote),
     re_path(u'^ajax/gvote/comment/$', bustime.views.ajax_gvote_comment),
     re_path(u'^ajax/bus/monitor/$', bustime.views.ajax_bus_monitor),
     re_path(u'^ajax/anomalies/$', bustime.views.ajax_anomalies),
     re_path(u'^ajax/gosnum/$', bustime.views.ajax_gosnum),
     re_path(u'^ajax/route-line/$', bustime.views.ajax_route_line),
     re_path(u'^ajax/route_lines_calc/$', bustime.views.ajax_route_lines_calc),
     re_path(u'^ajax/route_edit_save/$', bustime.views.ajax_route_edit_save),
     re_path(u'^ajax/peer_get/$', bustime.views.ajax_peer_get),
     re_path(u'^ajax/plan_change/$', bustime.views.ajax_plan_change),
     re_path(u'^ajax/stop_id_set_map_center/$', bustime.views.ajax_stop_id_set_map_center),
     re_path(u'^ajax/detector/$', bustime.views.ajax_detector),
     re_path(u'^ajax/mapping/$', bustime.views.ajax_mapping),
     re_path(u'^ajax/admin_vehicle_get_events/$', bustime.views.admin_vehicle_get_events),
     re_path(u'^ajax/admin_vehicle_del_vehicle/$', bustime.views.admin_vehicle_del_vehicle),
     re_path(u'^ajax/admin_gtfs_supervisor_config/$', bustime.views.admin_gtfs_supervisor_config),
     re_path(u'^ajax/ajax_get_alerts/$', bustime.views.ajax_get_alerts),
     re_path(u'^ajax/ajax_get_weather/$', bustime.views.ajax_get_weather),

     # для копирования маршрута страницы редактирования маршрута
     re_path(u'^ajax/ajax_route_get_bus_city/$', bustime.views.ajax_route_get_bus_city),
     # для city_admin
     re_path(u'^ajax/ajax_get_log_file/$', bustime.views.ajax_get_log_file),
     re_path(u'^ajax/ajax_start_job/$', bustime.views.ajax_start_job),
     re_path(u'^ajax/ajax_status_job/$', bustime.views.ajax_status_job),
     re_path(u'^ajax/ajax_get_gosnums_admin/$', bustime.views.ajax_get_gosnums_admin),
     re_path(u'^ajax/ajax_get_supervisor_status/$', bustime.views.ajax_get_supervisor_status),
     re_path(u'^ajax/ajax_message_for_all/$', bustime.views.ajax_message_for_all),

     re_path(u'^ajax/status_data/$', bustime.views.ajax_status_data),
     re_path(u'^ajax/transport/$', bustime.views.ajax_transport),
     re_path(u'^ajax/uevents-on-map/$', bustime.views.ajax_uevents_on_map),
     re_path(u'^ajax/jam/$', bustime.views.ajax_jam),
     re_path(u'^(?P<city_name>[\w-]+)/bus_trip/$', bustime.views.bus_trip),
     re_path(u'^(?P<city_name>[\w-]+)/busstops_trip/$', bustime.views.busstops_trip),
     re_path(u'^ajax/find_trips/$', bustime.views.find_trips),
     re_path(u'^ajax/nominatim/$', bustime.views.ajax_nominatim),
     re_path(u'^ajax/nominatim/(?P<mode>\w+)/$', bustime.views.ajax_nominatim),
     re_path(u'^ajax/test_proxy/$', bustime.views.ajax_test_proxy),

     re_path(u'^ajax/citynews_watched/$', bustime.views.ajax_citynews_watched),

     re_path(u'^ajax/chat_message/$', bustime.views.ajax_chat_message),

     re_path(u'^ajax/ajax_censored/$', bustime.views.ajax_censored),
     re_path(u'^ajax/gtfs_get_route/$', bustime.views.ajax_gtfs_get_route),
     re_path(u'^ajax/gtfs_get_service/$', bustime.views.ajax_gtfs_get_service),
     re_path(u'^ajax/gtfs_get_trip/$', bustime.views.ajax_gtfs_get_trip),
     re_path(u'^ajax/gtfs_get_feed/$', bustime.views.ajax_gtfs_get_feed),
     re_path(u'^ajax/gtfs_test_trip/$', bustime.views.ajax_gtfs_test_trip),
     re_path(u'^ajax/gtfs_test_rt/$', bustime.views.ajax_gtfs_test_rt),
     re_path(u'^ajax/gtfs_append_feed/$', bustime.views.ajax_gtfs_append_feed),
     re_path(u'^ajax/gtfs_load_schedule/$', bustime.views.ajax_gtfs_load_schedule),
     re_path(u'^ajax/gtfs_import_schedule/$', bustime.views.ajax_gtfs_import_schedule),
     re_path(u'^ajax/gtfs_stat_refresh/$', bustime.views.ajax_gtfs_stat_refresh),

     re_path(u'^ajax/from_to/$', bustime.views.ajax_from_to),
     re_path(u'^ajax/all_stops_map/$', bustime.views.ajax_all_stops_map),
     re_path(u'^ajax/stops_by_area/$', bustime.views.ajax_stops_by_area),

     re_path(u'^ajax/not_found/$', bustime.views.ajax_not_found),

     re_path(u'^go/$', bustime.views.go),
     re_path(u'^go$', bustime.views.go),
     re_path(u'^us/reset-bus-favorites/$', bustime.views.reset_busfavor),

     re_path(r'^mapzen/vector/v1/all/(?P<zoom>\d+)/(?P<x>\d+)/(?P<y>\d+).json', bustime.views.mapzen),
     re_path(u'^about/$', bustime.views.about),
     re_path(u'^open-letter-for-transport-data/$', bustime.views.open_letter),
     re_path(u'^blog/$', bustime.views.blog),
     re_path(u'^blog/better-data/$', bustime.views.blog, {'template_name':"blog_better-data.html"}),
     re_path(u'^blog/10-tips-for-comfortable-public-transport/$', bustime.views.blog, {'template_name':"blog_10-tips.html"}),
     re_path(u'^noadblock/$', bustime.views.noadblock),
     re_path(u'^help/(?P<topic>[\w-]+)/$', bustime.views.handbook),
     re_path(u'^help/(?P<topic>[\w-]+)/(?P<model>[\w-]+)/$', bustime.views.handbook_model),
     re_path(u'^help/$', bustime.views.help_view),
     re_path(u'^services/$', bustime.views.services), # Нет перевода
     re_path(u'^contacts/$', bustime.views.contacts),
     re_path(u'^pro/$', bustime.views.pro),
     re_path(u'^pro-demo/$', bustime.views.pro_demo),
     re_path(u'^voice-query/$', bustime.views.voice_query),

     re_path(r'^classic/$', bustime.views.classic_index, name='classic_index'), # Не добавил canonical
     re_path(r'^settings/$', bustime.views.settings_view),
     re_path(r'^(?P<city_name>[\w-]+)/settings_profile/$', bustime.views.settings_profile),
     re_path(r'^(?P<place_slug>[\w-]+)/settings/$', bustime.views.settings_view),
     re_path(r'^settings/photo/$', bustime.views.settings_photo),

     re_path(r'^settings/(?P<us_id>[\d]+)/gban/$', bustime.views.gban),  # todo refact
     re_path(r'^explorer/MobileSettings/(?P<id_>[\d]+)/$', bustime.views.explorer),
     re_path(r'^explorer/MobileSettings/(?P<id_>[\d]+)/gban/$', bustime.views.explorer_gban),  # todo refact
     re_path(r'^explorer/events/(?P<city_id>[\d]+)/(?P<ttype>[\w-]+)/$', bustime.views.explorer_events),
     re_path(u'^qiwi/notify/$', bustime.views.qiwi_notify),
     re_path(r'^show/$', bustime.views.home, {'template_name':"demo_show.html"}, name='show'),
     re_path(r'^demo/$', bustime.views.home, {'template_name':"demo_show.html"}, name='demo_show'),
     re_path(r'^classic/(?P<city_id>\d+)/$', bustime.views.classic_routes, name='classic_routes'),
     re_path(u'^tablo/$', bustime.views.stop_info_turbo),
     re_path(u'^work/$', bustime.views.work),
     re_path(u'^(?P<city_name>[\w-]+)/feedback/(?P<uid>[\_\w-]+)/$$', bustime.views.feedback_ts),
     re_path(u'^(?P<city_name>[\w-]+)/jam/$', bustime.views.jam),
     re_path(u'^error/$', bustime.views.error),
     re_path(u'^redirector/$', bustime.views.redirector),
     re_path(u'^select/$', bustime.views.select_admin),
     re_path(u'^register/$', bustime.views.register),
     re_path(u'^terms/$', bustime.views.terms),
     re_path(u'^logout/$', bustime.views.logout_view),
     re_path(u'^nursultan/(?P<ourl>.+)?$', bustime.views.nursultan_back_astana),
     re_path(u'^account_deletion/$', bustime.views.account_deletion),

     re_path(u'^(?P<city_name>[\w-]+)/rating/((?P<for_date>[0-9-]+)/)?(page-(?P<page>[0-9]+)/)?$', bustime.views.rating), # Проблемы с п
     re_path(u'^(?P<city_name>[\w-]+)/top/((?P<for_year>[\d]+)/)?(page-(?P<page>[\d]+)/)?$', bustime.views.top),
     re_path(u'^(?P<city_name>[\w-]+)/monitor/anomalies/$', bustime.views.anomalies),
     re_path(u'^(?P<city_name>[\w-]+)/monitor/$', bustime.views.monitor_old),
     re_path(u'^(?P<city_name>[\w-]+)/status/sheet/$', bustime.views.status_sheet),
     re_path(u'^(?P<city_name>[\w-]+)/status/offline/$', bustime.views.status_offline),

     re_path(u'^(?P<city_name>[\w-]+)/passengers/(?P<d>[\d-]+)/$', bustime.views.status_passengers),
     re_path(u'^(?P<city_name>[\w-]+)/passengers/(?P<d>[\d-]+)/passengers.js$', bustime.views.status_day_passengers_js),

     re_path(u'^(?P<city_name>[\w-]+)/transport/$', bustime.views.status_data),
     re_path(u'^(?P<city_name>[\w-]+)/transport/(?P<day>[\d-]+)/$', bustime.views.status_data),
     re_path(u'^(?P<city_name>[\w-]+)/transport/(?P<day>[\d-]+)/(?:page-(?P<page>[0-9]+)/)$', bustime.views.status_data),
     re_path(u'^(?P<city_name>[\w-]+)/transport/(?P<day>[\d-]+)/(?:search_gn=(?P<search_gn>[\w-]+)/)$', bustime.views.status_data),
     re_path(u'^(?P<city_name>[\w-]+)/transport/(?P<day>[\d-]+)/(?:search_bn=(?P<search_bn>[\w-]+)/)$', bustime.views.status_data),

     re_path(u'^(?P<city_name>[\w-]+)/transport/(?P<day>[\d-]+)/(?P<uid>[\_\w-]+)/$', bustime.views.transport),

     re_path(u'^(?P<city_name>[\w-]+)/status/$', bustime.views.status),

     re_path(u'^(?P<city_name>[\w-]+)/schedule/$', bustime.views.schedule, {'old_url_two':True}),
     re_path(u'^(?P<city_name>[\w-]+)/timetable/$', bustime.views.schedule),
     re_path(u'^(?P<city_name>[\w-]+)/schedule/(?P<bus_id>[\w-]+)/$', bustime.views.schedule_bus, {'old_url_two':True}),
     re_path(u'^(?P<city_name>[\w-]+)/stop/$', bustime.views.stops),
     re_path(r'^(?P<city_name>[\w-]+)/classic/$', bustime.views.classic_routes, name='classic_routes'),
     re_path(r'^(?P<city_name>[\w-]+)/classic/(?P<bus_id>[\w-]+)/$', bustime.views.classic_bus),
     re_path(u'^(?P<city_name>[\w-]+)/stop/new/$', bustime.views.stop_new),
     re_path(u'^(?P<city_name>[\w-]+)/new/$', bustime.views.bus_new),
     re_path(u'^(?P<city_name>[\w-]+)/stop/id/(?P<stop_id>[\d]+)/edit/$', bustime.views.edit_stop),
     re_path(u'^(?P<city_name>[\w-]+)/stop/(?P<stop_slug>[\w-]+)/$', bustime.views.stop),
     re_path(u'^(?P<city_name>[\w-]+)/stop/id/(?P<stop_id>[\d]+)/$', bustime.views.stop_info_turbo),
     re_path(u'^(?P<city_name>[\w-]+)/stop/(?P<tmc>[\w]+)/id/(?P<stop_id>[\d]+)/$', bustime.views.stop_info_turbo), # Не везде

     re_path(r'^(?P<city_name>[\w-]+)/(?P<bus_name>[\d\w-]+)/edit/$', bustime.views.route_edit, name="route_edit"),
     re_path(r'^(?P<city_name>[\w-]+)/(?P<bus_name>[\d\w-]+)/delete/$', bustime.views.route_delete, name="route_delete"),
     re_path(r'^(?P<city_name>[\w-]+)/(?P<bus_name>[\d\w-]+)/delete/yes/$', bustime.views.route_delete, {'yes':True}, name="route_delete"),
     re_path(u'^(?P<city_name>[\w-]+)/(?P<bus_name>[\d\w-]+)/monitor/$', bustime.views.monitor_bus, name="monitor_bus"),

     re_path(u'^(?P<city_name>[\w-]+)/admin/$', bustime.views.city_admin, name="city_admin"),
     re_path(u'^(?P<city_name>[\w-]+)/admin/mapping/$', bustime.views.city_mapping, name="city_mapping"),
     re_path(u'^(?P<city_name>[\w-]+)/admin/mapping-table/$', bustime.views.city_mapping_table, name="city_mapping_table"),
     re_path(u'^(?P<city_name>[\w-]+)/admin/plan/((?P<provider_id>[0-9]+)/)?$', bustime.views.plan, name="plan"),
     # re_path(u'^(?P<city_name>[\w-]+)/admin/plan/((?P<provider_id>[0-9]+)/)/download$', bustime.views.plan_download, name="plan_download"),
     # re_path(u'^(?P<city_name>[\w-]+)/admin/plan/((?P<provider_id>[0-9]+)/)/send$', bustime.views.plan_send, name="plan_send"),
     re_path(u'^(?P<city_name>[\w-]+)/admin/devices/$', bustime.views.devices, name="devices"),
     re_path(u'^(?P<city_name>[\w-]+)/admin/broadcast/$', bustime.views.broadcast, name="broadcast"),
     re_path(u'^(?P<city_name>[\w-]+)/admin/update-js/$', bustime.views.city_admin_update_js, name="city_admin_update_js"),
    re_path(u'^(?P<city_name>[\w-]+)/admin/update-v8/$', bustime.views.city_admin_update_v8, name="city_admin_update_v8"),
     re_path(u'^(?P<city_name>[\w-]+)/admin/update-mobile/$', bustime.views.city_admin_update_mobile, name="city_admin_update_mobile"),
     re_path(u'^(?P<city_name>[\w-]+)/admin/load-bus/$', bustime.views.city_admin_load_bus, name="load_bus"),
     re_path(u'^(?P<city_name>[\w-]+)/admin/load-gtfs/$', bustime.views.city_admin_load_gtfs, name="load_gtfs"),
     re_path(u'^(?P<city_name>[\w-]+)/admin/windmill-restart/$', bustime.views.city_admin_windmill_restart, name="city_admin_windmill_restart"),
     re_path(u'^(?P<city_name>[\w-]+)/admin/city-new/$', bustime.views.city_admin_city_new, name="city_admin_city_new"),
     re_path(u'^(?P<city_name>[\w-]+)/admin/uevents-on-map/$', bustime.views.uevents_on_map, name="uevents_on_map"),
     re_path(u'^(?P<city_name>[\w-]+)/admin/fill-inter-stops/$', bustime.views.city_admin_fill_inter_stops, name="fill_inter_stops"),
     re_path(u'^(?P<place_name>[\w-]+)/admin/icon-editor/$', bustime.views.icon_editor, name="icon_editor"),
     re_path(u'^(?P<city_name>[\w-]+)/admin/dev-refresh/$', bustime.views.dev_refresh, name="dev_refresh"),
     re_path(u'^(?P<city_name>[\w-]+)/admin/tests_rpc/$', bustime.views.tests_rpc, name="tests_rpc"),
     re_path(u'^(?P<city_name>[\w-]+)/admin/censored/$', bustime.views.censored, name="censored"),
     re_path(r'^(?P<city_name>[\w-]+)/admin/censored/(page-(?P<page>[0-9]+)/)?$', bustime.views.censored),
     re_path(u'^(?P<city_name>[\w-]+)/admin/turbine_inspector/$', bustime.views.turbine_inspector, name="turbine_inspector"),
     re_path(u'^(?P<city_name>[\w-]+)/admin/logs_on_map/$', bustime.views.logs_on_map, name="logs_on_map"),
     re_path(r'^(?P<city_name>[\w-]+)/(?P<bus_name>[\d\w-]+)/detector/$', bustime.views.detector, name="detector"),
     re_path(r'^(?P<city_name>[\w-]+)/company/(?P<provider_id>\d+)/$', bustime.views.provider, name="provider"),
     re_path(r'^(?P<city_name>[\w-]+)/company/$', bustime.views.provider, name="provider"),
     re_path(u'^admin/vehicle/$', bustime.views.admin_vehicle, name="admin_vehicle"),
     re_path(r'^(?P<city_slug>[\w-]+)/history/(page-(?P<page>[0-9]+)/)?$', bustime.views.history),
     re_path(r'^(?P<city_slug>[\w-]+)/history/$', bustime.views.history),
     re_path(r'^(?P<city_slug>[\w-]+)/history1/(page-(?P<page>[0-9]+)/)?$', bustime.views.history1),
     re_path(r'^(?P<city_slug>[\w-]+)/history1/$', bustime.views.history1),
     re_path(r'^(?P<city_name>[\w-]+)/chat/$', bustime.views.chat_web, name="chat_web"),
     re_path(r'^(?P<city_name>[\w-]+)/chat/(?P<bus_slug>[\_\w-]+)/$', bustime.views.chat_web, name="chat_web"),
     re_path(r'^(?P<city_name>[\w-]+)/new_ui/$', bustime.views.new_ui_home, name='new_ui_home'),

     re_path(u'^bot/say/$', bustime.views.bot_say),
     re_path(u'^agreement/$', bustime.views.agreement),
     re_path(u'^cookies-policy/$', bustime.views.cookies_policy),
     re_path(u'^radio/say/$', bustime.views.radio_say),
     re_path(u'^336x280/$', bustime.views.ad336x280),
     re_path(u'^app/$', bustime.views.app),
     # total recall
     re_path(u'^(?P<city_name>[\w-]+)/(?P<bus_id>[\w-]+)/$', bustime.views.schedule_bus),
     re_path(u'^(?P<city_slug>[\w-]+)/(?P<bus_id>[\w-]+)/edit-schedule/(?P<direction>[\w-]+)/$', bustime.views.schedule_bus_edit),
     re_path(u'^(?P<city_slug>[\w-]+)/(?P<bus_id>[\w-]+)/edit-schedule/$', bustime.views.schedule_bus_edit),
     re_path(u'^(?P<city_name>[\w-]{3,})/$', bustime.views.turbo_home, name='home'),
] + debug_toolbar_urls()


'''
https://stackoverflow.com/questions/6791911/execute-code-when-django-starts-once-only
That module is imported and executed once
so this init code executed once
'''
from bustime.models import *
try:
    for d in DataSource.objects.all():
        DATASOURCE_CACHE[d.get_hash(d.channel, d.src)] = d.id

    for c in City.objects.all():  # active=True
        CITY_MAP[c.id] = c
        CITY_MAPN[c.name] = c

    for c in Country.objects.all():
        COUNTRY_MAP[c.id] = c
        COUNTRY_MAP_CODE[c.code] = c

    PLACE_MAP = SimpleLazyObject(lambda: {k: p for k, p in places_get("ru", False).items()})
    PLACE_MAPN = SimpleLazyObject(lambda: {p.name: p for k, p in PLACE_MAP.items() if k < 1000})
except Exception as ex:
    print(str(ex))
