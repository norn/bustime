from __future__ import absolute_import
from django.conf.urls import include
from django.urls import re_path
from django.conf import settings
from django.conf.urls.static import static
import taxi.views
import taxi.api

app_name = 'taxi'   # это имя в шаблоне доступно как {{request.resolver_match.app_name}}

urlpatterns = [
    re_path(u'^agreement/(?P<whois>\w+)/$', taxi.views.agreement),
    re_path(u'^usage/(?P<whois>\w+)/$', taxi.views.usage),
    re_path(u'^profile/$', taxi.views.profile),
    re_path(u'^setcar/(?P<car_id>\d+)/$', taxi.views.setcar),
    re_path(u'^setcar/$', taxi.views.setcar),
    re_path(u'^selcar/$', taxi.views.selcar),
    re_path(u'^selcar/(?P<car_id>\d+)/$', taxi.views.selcar),
    re_path(u'^votes/$', taxi.views.votes), # список заказов (голосующих пасссажиров) (orders.html)

    re_path(u'^api/setuser/$', taxi.api.set_taxi_user),
    re_path(u'^api/order/create/$', taxi.api.order_create), # пассажир создал заказ (Нажал Голосовать, order_inputs.html)
    re_path(u'^api/order/delete/$', taxi.api.order_delete), # пассажир удаляет заказ (нажимает Прекратить голосовать, order_inputs.html)
    re_path(u'^api/order/close/$', taxi.api.order_close),   # Пассажир нажал Оценить поездку (trip_item_pass.html)
    re_path(u'^api/order/start/$', taxi.api.order_start), # такси выехало к пассажиру (пассажир нажал Выбрать на предложение водителя (offer_item.html)
    re_path(u'^api/offer/$', taxi.api.offer),           # водитель нажал Предложить/Отказать (order_item.html)
    re_path(u'^api/message/$', taxi.api.taxi_message),  # пассажир нажал Вижу автомобиль (trip_item_pass.html)
    re_path(u'^api/trip/start/$', taxi.api.trip_start), # пассажир нажал Поездка начата (trip_item_pass.html) или водитель нажал Пассажир сел (order_item.html)

    re_path(u'^api/city/streets/$', taxi.api.city_streets),
    re_path(u'^api/path/$', taxi.api.get_trip_path),
]