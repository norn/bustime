from django.conf.urls import patterns, include, url

urlpatterns = patterns('',
    url(r'^$', 'backoffice.views.dash', name='backoffice_dash'),
    url(r'^allevents/(?P<city_id>\d+)/$', 'backoffice.views.all_events', name='backoffice_allevents'),
    url(r'^timer/(?P<city_id>\d+)/$', 'backoffice.views.timer', name='backoffice_timer'),
    url(r'^bdata0/(?P<city_id>\d+)/$', 'backoffice.views.bdata0', name='backoffice_bdata0'),
    url(r'^bdata1/(?P<city_id>\d+)/$', 'backoffice.views.bdata1', name='backoffice_bdata1'),
    url(r'^bdata2/(?P<city_id>\d+)/$', 'backoffice.views.bdata2', name='backoffice_bdata2'),
    url(r'^bdata3/(?P<city_id>\d+)/$', 'backoffice.views.bdata3', name='backoffice_bdata3'),
    url(r'^socket_serv_start/$', 'backoffice.views.socket_serv', {'what':'start'}, name="socket_serv_start"),
    url(r'^socket_serv_stop/$', 'backoffice.views.socket_serv', {'what':'stop'}, name="socket_serv_stop"),
    url(r'^socket_serv_restart/$', 'backoffice.views.socket_serv', {'what':'restart'}, name="socket_serv_restart"),
)
