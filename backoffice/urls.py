from __future__ import absolute_import
from django.conf.urls import include
from django.urls import re_path
import backoffice.views

urlpatterns = [
    re_path(r'^$', backoffice.views.dash, name='backoffice_dash'),
    re_path(r'^allevents/(?P<city_id>\d+)/$', backoffice.views.all_events, name='backoffice_allevents'),
    re_path(r'^timer/(?P<city_id>\d+)/$', backoffice.views.timer, name='backoffice_timer'),
    re_path(r'^bdata0/(?P<city_id>\d+)/$', backoffice.views.bdata0, name='backoffice_bdata0'),
    re_path(r'^bdata1/(?P<city_id>\d+)/$', backoffice.views.bdata1, name='backoffice_bdata1'),
    re_path(r'^bdata2/(?P<city_id>\d+)/$', backoffice.views.bdata2, name='backoffice_bdata2'),
    re_path(r'^bdata3/(?P<city_id>\d+)/$', backoffice.views.bdata3, name='backoffice_bdata3'),
    #re_path(r'^socket_serv_start/$', backoffice.views.socket_serv, {'what':'start'}, name="socket_serv_start"),
    #re_path(r'^socket_serv_stop/$', backoffice.views.socket_serv, {'what':'stop'}, name="socket_serv_stop"),
    #re_path(r'^socket_serv_restart/$', backoffice.views.socket_serv, {'what':'restart'}, name="socket_serv_restart"),
]
