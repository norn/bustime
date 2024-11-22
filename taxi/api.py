"""
Taxi API

settings.GH_SERVER =   'http://46.4.106.110:18082'
settings.NOMINATIM_SERVER = 'http://46.4.106.110:8008/nominatim'


f=open("/r/bustime/bustime/debug.txt", "w")
f.write("request.POST=%s\n" % json.dumps(request.POST.dict(), indent=3))
f.close()

https://stackoverflow.com/questions/15874233/output-django-queryset-as-json
"""
from django.contrib.auth.models import User, Group
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.translation import gettext as _
from django.http import HttpResponse, JsonResponse
from django.db.models import OuterRef, Subquery, Sum, Count, F, Q
from django.template.response import TemplateResponse, SimpleTemplateResponse
from django.contrib import messages
from django.db import connections
from django.conf import settings
from django.contrib.gis.geos import LineString, Point
from django.forms.models import model_to_dict

from bustime.models import (CITY_MAP, sio_pub, distance_by_line, rcache_get, rcache_set, sio_pub, distance_meters, wilson_rating)
from bustime.views import get_user_settings
from taxi.models import *

from datetime import datetime, timedelta
import json
import traceback
import calendar
import requests
import urllib.parse


# список улиц города
@require_http_methods(["POST"])
@login_required()
def city_streets(request):
    result = {
        "error": None,
        "result": None
    }

    try:
        city_id = request.POST.get('city_id', 0)
        result["result"] = list(Kladr_street.objects.filter(city__id=city_id).order_by('name').values(title=F('name')))
    except:
        result["error"] = traceback.format_exc(limit=1)

    return HttpResponse(json.dumps(result, default=str), content_type='application/json')
# city_streets


@require_http_methods(["POST"])
@login_required()
def get_trip_path(request):
    result = {
        "error": None,
        "result": None
    }

    points = json.loads(request.POST.get("points"))
    trip_type = request.POST.get("trip_type", "car")

    try:
        url = '%s/route?' % settings.GH_SERVER
        for p in points:
            url = url + 'point=%s,%s&' % (p['lat'], p['lng'])

        if trip_type == "foot":
            # пешком
            url += 'points_encoded=false&locale=ru-RU&profile=foot&elevation=false&instructions=false&type=json'
        else:
            # на машине
            url += 'points_encoded=false&locale=ru-RU&profile=car&elevation=false&instructions=false&type=json'

        headers = {
            'Referer': url
        }
        r = requests.get(url, timeout=5)

        js = r.json()
        paths = js.get('paths')

        if paths:
            points = paths[0]['points'] # GeoJSON
            distance = paths[0]['distance']  # distance_by_line(line)   # m
            travel_time = int(distance / ((40 * 1000) / 60))    # min, при средней скорости 40 км/ч

            result["result"] = {
                'geojson': points,
                'distance': round(distance / 1000, 1),
                'travel_time': '%02d:%02d' % (int(travel_time / 60), travel_time % 60)
            }
        # if paths
        elif js.get('message'):
            result["error"] = js.get('message')
        else:
            result["error"] = r.text
    except:
        result["error"] = traceback.format_exc(limit=1)

    return HttpResponse(json.dumps(result, default=str), content_type='application/json')
# get_trip_path


@require_http_methods(["POST"])
@login_required()
def set_taxi_user(request):
    us = get_user_settings(request)

    result = {
        "error": None,
        "result": None
    }

    try:
        who = request.POST.get('who', 'passenger')
        active = int(request.POST.get('active', '0')) > 0

        taxiuser = TaxiUser.objects.filter(user=request.user).first()

        if taxiuser:
            # проверки
            if active:
                if who == 'driver':
                    if not taxiuser.name:
                        result["error"] = '%s <a href="/settings_profile/">%s</a>' % (_('Не заполнены данные (Имя).'), _('Заполнить'))
                    #elif not taxiuser.phone:
                    #    result["error"] = '%s <a href="/settings_profile/">%s</a>' % (_('Не заполнены данные (Телефон).'), _('Заполнить'))
                    else:
                        cars_count = CarTaxi.objects.filter(taxist=taxiuser).count()
                        if cars_count == 0:
                            result["error"] = '%s <a href="/settings_profile/">%s</a>' % (_('Не указана машина.'), _('Добавить'))
                else: # passenger
                    taxi_path = json.loads(request.POST.get('taxi_path', '{}'))
                    wf = taxi_path.get('wf')
                    wh = taxi_path.get('wh')

                    if not request.POST.get('passengers'):
                        result["error"] = _('Не указано количество пассажиров')
                    elif not request.POST.get('price'):
                        result["error"] = _('Не указана стоимость')
                    elif not wf or not wf.get('address'):
                        result["error"] = _('Не указан начальный пункт')
                    elif not wh or not wh.get('address'):
                        result["error"] = _('Не указан конечный пункт')
            # if active

            # действия
            if not result["error"]:
                if who == 'driver':
                    taxiuser.driver = active
                    taxiuser.gps_on = active
                    rcache_set("trips_%s" % request.user.id, {}, 3600)  # уничтожаем ранее искомые маршруты
                else:   # passenger
                    taxiuser.driver = False
                    taxiuser.gps_on = active

                taxiuser.save(update_fields=['driver', 'gps_on'])
                taxiuser = taxiuser_get(request.user.id, force=True)    # dict

                if who == 'driver':
                    if taxiuser['gps_on']:
                        data = {
                            "event": "car_add",
                            "data": json.dumps([taxiuser], default=str),
                            "html": TemplateResponse(request, 'taxi/taxi_item.html', {'taxi': taxiuser}).rendered_content
                        }
                        sio_pub("ru.bustime.taxi__%s" % us.city.id, {"taxi": data})
                    else:
                        cc_key = "tevents_%s" % us.city.id
                        tevents = rcache_get(cc_key, {})
                        e = tevents.get(taxiuser['id'])
                        if e:
                            del tevents[taxiuser['id']]
                            rcache_set(cc_key, tevents, 600)
                        data = {
                            "event": "car_del",
                            "data": json.dumps([taxiuser], default=str)
                        }
                        sio_pub("ru.bustime.taxi__%s" % us.city.id, {"taxi": data})
                else: # passenger
                    cc_key = "torders_%s" % us.city.id
                    torders = rcache_get(cc_key, {})
                    if taxiuser['gps_on']:
                        e = {
                            'passenger': taxiuser,
                            'trip': taxi_path,
                            'passengers': request.POST.get('passengers'),
                            'price': request.POST.get('price'),
                            'note': request.POST.get('note'),
                        }
                        torders[taxiuser['id']] = e
                        rcache_set(cc_key, torders, 3600)
                        data = {
                            "event": "order_add",
                            "data": json.dumps([e], default=str),
                            "html": TemplateResponse(request, 'taxi/order_item.html', {'order': e}).rendered_content
                        }
                        sio_pub("ru.bustime.taxi__%s" % us.city.id, {"taxi": data})
                    else:
                        e = torders.get(taxiuser['id'])
                        if e:
                            del torders[taxiuser['id']]
                            rcache_set(cc_key, torders, 3600)
                        data = {
                            "event": "order_del",
                            "data": json.dumps([e], default=str),
                        }
                        sio_pub("ru.bustime.taxi__%s" % us.city.id, {"taxi": data})
            # if not result["error"]
        # if taxiuser
        else:
            result["error"] = '%s <a href="/carpool/agreement/%s/">%s</a>' % (_('Вы не зарегистрированы в сервисе "Попутчик"'), who, _('Зарегистрироваться'))
    except:
        result["error"] = traceback.format_exc(limit=1)

    if not result["error"]:
        result["result"] = taxiuser # dict!

    return HttpResponse(json.dumps(result, default=str), content_type='application/json')
# set_taxi_user


"""
пассажир создаёт заказ (нажимает Голосовать, order_inputs.html)
"""
@require_http_methods(["POST"])
#@login_required()
def order_create(request):
    result = {
        "error": None,
        "result": None
    }

    try:
        if not request.user.is_authenticated:
            result["error"] = '<a href="/settings/">%s</a> %s' % (_('Войдите или зарегистрируйтесь'), _('чтобы голосовать'))
            return HttpResponse(json.dumps(result, default=str), content_type='application/json')

        us = get_user_settings(request)

        taxiuser = TaxiUser.objects.filter(user=request.user).first()
        if taxiuser:
            taxi_path = json.loads( urllib.parse.unquote( request.COOKIES.get('taxi_path', request.POST.get('taxi_path', '{}')) ) )
            """
            формируется в bustime/views.py bus_trip()
            {"wf":{"address":"Каштановая Аллея (Карла Маркса)","point":[20.4657376,54.7245427],"id":1628},"wh":{"address":"Ивана Земнухова","point":[20.5505211,54.671261],"id":36431},"geojson":{"type":"LineString","coordinates":[[20.465742,54.724536],...]},"distance":10,"time":"14 мин."}
            """
            wf = taxi_path.get('wf')    # откуда
            wh = taxi_path.get('wh')    # куда

            # проверки
            if not request.POST.get('passengers'):
                result["error"] = _('Не указано количество пассажиров')
            elif not request.POST.get('price'):
                result["error"] = _('Не указана стоимость')
            elif not wf or not wf.get('address'):
                result["error"] = _('Не указан начальный пункт')
            elif not wh or not wh.get('address'):
                result["error"] = _('Не указан конечный пункт')

            # действия
            if not result["error"]:
                taxiuser.driver = False
                taxiuser.gps_on = True    # для отображения на карте
                taxiuser.save(update_fields=['driver', 'gps_on'])

                order = Order(data=us.city.now,
                                city=us.city,
                                trip_data=us.city.now,
                                wf=wf.get('address'),
                                wf_point=Point(wf.get('point')),
                                wh=wh.get('address'),
                                wh_point=Point(wh.get('point')),
                                passengers=request.POST.get('passengers'),
                                note=request.POST.get('note'),
                                price=request.POST.get('price'),
                                distance=taxi_path.get('distance'),
                                duration=taxi_path.get('time'),
                                trip_line=taxi_path.get('geojson'),
                                passenger=taxiuser)
                order.save()

                order = model_to_dict(order)
                order['passenger'] = taxiuser_get(request.user.id, force=True)
                order['passenger']['order_id'] = order['id'];

                rcache_set("taxiuser_%s" % (us.id), order['passenger'], 60*60*24*2)

                result["result"] = order # dict!

                cc_key = "torders_%s" % us.city.id
                torders = rcache_get(cc_key, {})
                torders[order['id']] = order   # dict!
                rcache_set(cc_key, torders, 3600)

                offers = rcache_get('offers_%s' % order['id'], {})

                data = {
                    "event": "order_add",
                    "data": json.dumps([order], default=str),
                    "html": TemplateResponse(request, 'taxi/order_item.html', {'order': order, 'offers': offers}).rendered_content
                }
                sio_pub("ru.bustime.taxi__%s" % us.city.id, {"taxi": data})

            # if not result["error"]
        # if taxiuser
        else:
            result["error"] = '%s <a href="/carpool/agreement/passenger/">%s</a>' % (_('Вы не зарегистрированы в сервисе "Попутчик"'), _('Зарегистрироваться'))
    except:
        result["error"] = traceback.format_exc(limit=1) # TODO: скрыть ибо выводится в диалог

    return HttpResponse(json.dumps(result, default=str), content_type='application/json')
# order_create


"""
пассажир удаляет заказ (нажимает Прекратить голосовать, order_inputs.html)
"""
@require_http_methods(["POST"])
@login_required()
def order_delete(request):
    us = get_user_settings(request)

    result = {
        "error": None,
        "result": None
    }

    try:
        taxiuser = TaxiUser.objects.filter(user=request.user).first()
        if taxiuser:
            # проверки
            order_id = request.POST.get('order_id')
            if not order_id:
                result["error"] = _('Не указан заказ')
            else:
                order_id = int(order_id)

            """
            Заказ может быть в нескольких состояниях:
            1. Водитель ещё не взял заказ (поле taxist=None)
            2. Водитель уже выполняет заказ (даже если только начал движение к клиенту) (поле taxist=TaxiUser(водитель))
            3. Заказ уже выполнен водителем, поле taxist заполнено, оценки друг-другу заполнены
            """
            if order_id > 0:    # конкретный заказ
                orders = Order.objects.filter(id=order_id)
            else:   # -1, если удалить все неначатые водителями заказы
                orders = Order.objects.filter(taxist__isnull=True)

            # действия
            if not result["error"]:
                taxiuser.driver = False
                taxiuser.gps_on = False    # для отображения на карте
                taxiuser.save(update_fields=['driver', 'gps_on'])

                deleted_orders = []
                if orders:
                    cc_key = "torders_%s" % us.city.id
                    torders = rcache_get(cc_key, {})
                    for o in orders:
                        if o.taxist != None:    # это может произойти только при конкретном заказе, order_id > 0
                            """
                            закомментировано на время отладки выполения заказа так как страница окончания заказа ещё не сделана
                            TODO: доделать, а пока удалим заказ
                            result["error"] = _('Нельзя удалить выполненный заказ')
                            """
                            # на время отладки:
                            order = torders.get(o.id)   # если удаляются старые заказы, то в кэше их может не быть
                            o.delete()

                            if order:
                                order['passenger'] = taxiuser
                                deleted_orders.append(order)
                                del torders[order['id']]
                            # /на время отладки
                        else:   # это может произойти в любом случае
                            # заказ ещё не брался водителем
                            order = torders.get(o.id)   # если удаляются старые заказы, то в кэше их может не быть
                            o.delete()

                            if order:
                                order['passenger'] = taxiuser
                                deleted_orders.append(order)
                                del torders[order['id']]
                    # for o in orders

                    if deleted_orders:
                        rcache_set(cc_key, torders, 3600)
                        data = {
                            "event": "order_del",
                            "data": json.dumps(deleted_orders, default=str),
                        }
                        sio_pub("ru.bustime.taxi__%s" % us.city.id, {"taxi": data})
                # if orders

                taxiuser = taxiuser_get(request.user.id, force=True)

                if not result["error"]:
                    result["result"] = {
                        'passenger':taxiuser,
                        'orders': deleted_orders
                    }
            # if not result["error"]
        # if taxiuser
        else:
            result["error"] = '%s <a href="/carpool/agreement/passenger/">%s</a>' % (_('Вы не зарегистрированы в сервисе "Попутчик"'), _('Зарегистрироваться'))
    except:
        result["error"] = traceback.format_exc(limit=2) # TODO: скрыть ибо выводится в диалог

    return HttpResponse(json.dumps(result, default=str), content_type='application/json')
# order_delete


"""
закрытие заказа (юзер нажимает Оценить поездку, taxi_order_close() в trip_item_pass.html, orders.html)
"""
@require_http_methods(["POST"])
@login_required()
def order_close(request):
    us = get_user_settings(request) # либо водитель, либо пассажир

    result = {
        "error": None,
        "result": None
    }

    try:
        taxiuser = TaxiUser.objects.filter(user=request.user).first()
        if taxiuser:
            # проверки
            order_id = int(request.POST.get('order_id', 0))
            order = Order.objects.filter(id=order_id).first()

            if not order:
                result["error"] = _('Не найден заказ')
            elif not request.POST.get('who'):
                result["error"] = _('Не указан статус пользователя')
            else:
                is_driver = request.POST.get('who') == 'driver'
                trip_status = int(request.POST.get('trip_status', 0))

                if is_driver:   # заказ закрывает водитель
                    order.taxist_rating = int(request.POST.get('rating', 0))    # оценка пассажира водителем
                    order.taxist_note = request.POST.get('note')                # замечания водителя
                    order.trip_end = us.city.now
                    if order.trip_status < 4: # нет отказов
                        order.trip_status = trip_status
                    order.save()

                    if order.trip_status == 4:  # Поездка окончена нормально
                        taxiuser.driver_trips_cnt += 1  # увеличить счетчик поездок
                    taxiuser.save()

                    # рассчитать рейтинг пассажира
                    passenger = TaxiUser.objects.filter(id=order.passenger.id).first()
                    if passenger:
                        passenger.passenger_rating_cnt += 1 # общее кол-во выставленных оценок пассажиру
                        # order.taxist_rating - оценка, выставленная водителем пассажиру за поездку
                        if order.taxist_rating > 0: # поездка оценена положительно
                            passenger.passenger_rating_pos += 1
                        # https://gitlab.com/nornk/bustime/-/issues/2730#note_956270513
                        passenger.passenger_rating = round(wilson_rating(passenger.passenger_rating_pos, passenger.passenger_rating_cnt, human=True), 1)
                        passenger.save(update_fields=['passenger_rating_cnt', 'passenger_rating_pos', 'passenger_rating'])

                    # таксисту воозвращаем заказ для его уничтожения на экране
                    result["result"] = order_get(order.id, force=True)

                else:           # заказ закрывает пассажир
                    # рассчитать рейтинг водителя
                    if trip_status != 6:    # отказ пассажира от поездки, не давать оценку водителю
                        order.passenger_rating = int(request.POST.get('rating', 0)) # оценка водителя пассажиром
                        order.passenger_note = request.POST.get('note')             # замечания пассажира

                        taxist = TaxiUser.objects.filter(id=order.taxist.id).first()
                        if taxist:
                            taxist.driver_rating_cnt += 1   # общее кол-во выставленных оценок водителю
                            # order.passenger_rating - оценка, выставленная пассажиром водителю за поездку
                            if order.passenger_rating > 0:
                                taxist.driver_rating_pos += 1
                            taxist.driver_rating = round(wilson_rating(taxist.driver_rating_pos, taxist.driver_rating_cnt, human=True), 1)
                            taxist.save(update_fields=['driver_rating_cnt', 'driver_rating_pos', 'driver_rating'])
                    # if trip_status != 6

                    order.trip_end = us.city.now
                    order.trip_status = trip_status
                    order.save()

                    # пассажиру надо прекратить голосовать, вернуться на страницу наденного маршрута, на вкладку голосования
                    taxiuser.gps_on = False    # для отображения на карте
                    taxiuser.save()
                    # для этого надо восстановить следующие вещи
                    taxiuser = taxiuser_get(request.user.id, force=True)
                    tevents = rcache_get("tevents_%s" % us.city.id, {})
                    trips = rcache_get("trips_%s" % request.user.id, [])
                    taxi_path = json.loads( urllib.parse.unquote( request.COOKIES.get('taxi_path', '{}') ) )
                    # и вернуть результат
                    result["result"] = {
                        'taxiuser': taxiuser,
                        "html": TemplateResponse(request, 'from-to4.html', {
                                                                            'us': us,
                                                                            'tevents': tevents,
                                                                            'trips': trips,
                                                                            'taxiuser': taxiuser,
                                                                            'taxi_path': taxi_path,
                                                                            'tab_active': 'taxi_trip'}).rendered_content
                    }
                # else if is_driver

                # удалить заказ из кэша
                cc_key = "torders_%s" % us.city.id
                torders = rcache_get(cc_key, {})
                if torders.get(order.id):
                    del torders[order.id]
                    rcache_set(cc_key, torders, 3600)
                # и сообщить всем о его закрытии
                data = {
                    "event": "order_close",
                    "data": json.dumps(order_get(order.id, force=True), default=str),
                }
                sio_pub("ru.bustime.taxi__%s" % us.city.id, {"taxi": data})

            # else if not order

        # if taxiuser
        else:
            result["error"] = '%s <a href="/carpool/agreement/passenger/">%s</a>' % (_('Вы не зарегистрированы в сервисе "Попутчик"'), _('Зарегистрироваться'))
    except:
        result["error"] = traceback.format_exc(limit=1) # TODO: скрыть ибо выводится в диалог

    return HttpResponse(json.dumps(result, default=str), content_type='application/json')
# order_close


"""
Водитель нажал кнопку Предложить/Откзать (orders.html)
вызывается из orders.html set_offer()
формируется список предложений на заказ № order_id
if Предложить - добавляется новый offer
if Откзать - удаляется существующий
"""
@require_http_methods(["POST"])
@login_required()
def offer(request):
    us = get_user_settings(request) # таксист

    result = {
        "error": None,
        "result": None
    }

    try:
        torders = rcache_get("torders_%s" % us.city.id, {})
        order_id = int(request.POST.get('order_id', 0))
        order = torders.get(order_id)

        if order:
            driver = taxiuser_get(request.user.id)    # таксист

            # предложения водителей на конкретный заказ
            cc_key = 'offers_%s' % order_id
            offers = rcache_get(cc_key, {}) # это offers (предложения водителей) на заказ № order_id
            offer = offers.get(request.user.id)
            if offer:
                # мой отклик на этот заказ уже есть - удалить из списка
                del offers[request.user.id]
                # сообщаем об отзыве своего предложения
                data = {
                    "event": "offer_del",
                    "data": json.dumps([offer], default=str),
                }
            else:
                # моего отклика на этот заказ ещё нет - добавить
                distance = {
                    'meters': 0,
                    'time': 0
                }

                tevents = rcache_get("tevents_%s" % us.city.id, {}) # bustime/inject_events.py inject_custom()
                my_pos = tevents.get(driver['id'], {})
                if my_pos:
                    hi_pos = rcache_get('passenger_%s' % order['passenger']['user'], {})  # bustime.views.ajax_stops_by_gps()
                    if hi_pos:
                        distance['meters'] = round(distance_meters(my_pos.get('x', 0), my_pos.get('y', 0), hi_pos.get('lon', 0), hi_pos.get('lat', 0)) / 1000, 1)
                        distance['time'] = int(distance['meters'] / 40 * 1.3 * 3600)
                        h = int(distance['time'] / 3600)
                        m = int(distance['time'] % 3600 / 60)
                        s = distance['time'] - (h * 3600 + m * 60)
                        if h:
                            if s:
                                m += 1
                            distance['time'] = "%d ч %d м." % (h, m)
                        elif m:
                            if s:
                                m += 1
                            distance['time'] = "%d мин." % m
                        else:
                            distance['time'] = "%d сек." % s

                # это offer на заказ
                offer = {
                    'order': order,
                    'taxi': driver,
                    'distance': distance,
                    'timestamp': us.city.now.strftime("%s"),   # unix timestamp для отсчета времени действия предложения
                }
                # записываем оффер в список
                offers[request.user.id] = offer
                # сообщаем о новом предложении
                data = {
                    "event": "offer_add",
                    "data": json.dumps([offer], default=str),
                    "html": TemplateResponse(request, 'taxi/offer_item.html', {'taxi': driver, 'distance': distance}).rendered_content
                }

            rcache_set(cc_key, offers, 600)   # действительно 30 минут
            sio_pub("ru.bustime.taxi__%s" % us.city.id, {"taxi": data})
            result["result"] = {'offer': offer, 'status': data["event"]}
        else:
            result["error"] = _('Нет заказа')

    except:
        result["error"] = traceback.format_exc(limit=1)

    return HttpResponse(json.dumps(result, default=str), content_type='application/json')
# offer


# пассажир нажал кнопку Выбрать на предложение водителя (offer_item.html), начало поездки водителя к пасссажиру
# вызывается из bustime_main.js take_offer()
@require_http_methods(["POST"])
@login_required()
def order_start(request):
    result = {
        "error": None,
        "result": None
    }

    try:
        us = get_user_settings(request) # пассажир

        passenger = TaxiUser.objects.filter(user=request.user).first()
        driver = TaxiUser.objects.filter( user__id=int(request.POST.get('taxi_id', 0)) ).first()
        order = Order.objects.filter(id=int(request.POST.get('order_id', 0))).first()

        if not passenger:
            result["error"] = _('Указан отсутствующий пассажир')
        elif not driver:
            result["error"] = _('Указан отсутствующий водитель')
        elif not order:
            result["error"] = _('Указан отсутствующий заказ')

        if not result["error"]:
            # включаем GPS (у водителя он должен быть уже включен, но пофиг)
            passenger.gps_on = True
            passenger.save(update_fields=['gps_on'])
            passenger = taxiuser_get(passenger.user.id, force=True)  # => dict

            driver.gps_on = True
            driver.save(update_fields=['gps_on'])
            driver = taxiuser_get(driver.user.id, force=True)        # => dict

            # заполнить поля заказа
            order.taxist_id = driver['id']
            order.car_id = driver['car']['id']
            order.trip_price = order.price  # заглушка пока не ввели торг за цену поездки
            order.trip_start = us.city.now
            order.trip_status = 1   # 'Такси выехало к пассажиру' (taxi/models.py, TRIP_STATUS)
            order.save()

            order = model_to_dict(order)
            order['passenger'] = passenger  # <= dict
            order['taxist'] = driver

            #car = CarTaxi.objects.select_related('model', 'color').filter(taxist__id=driver['id'], current=True).first()
            car = CarTaxi.objects.filter(taxist__id=driver['id'], current=True).first()
            order['car'] = model_to_dict(car)
            #order['car']['model'] = model_to_dict(car.model)
            #order['car']['color'] = model_to_dict(car.color)

            cc_key = "torders_%s" % us.city.id
            torders = rcache_get(cc_key, {})
            torders[order['id']] = order   # dict!
            rcache_set(cc_key, torders, 3600)

            result["result"] = {
                'order': order, # dict!
                'html': TemplateResponse(request, 'taxi/trip_item_pass.html', {'order': order}).rendered_content
            }

            # сообщение водителю о принятии его предложения
            data = {
                "event": "order_start",
                "data": json.dumps(order, default=str),
            }
            sio_pub("ru.bustime.taxi__%s" % us.city.id, {"taxi": data})

        # if not result["error"]

    except:
        result["error"] = traceback.format_exc(limit=1)

    return HttpResponse(json.dumps(result, default=str), content_type='application/json')
# order_start


# пассажир нажал Поездка начата (trip_item_pass.html) или водитель нажал Пассажир сел (order_item.html)
@require_http_methods(["POST"])
@login_required()
def trip_start(request):
    result = {
        "error": None,
        "result": None
    }

    try:
        us = get_user_settings(request)
        who = request.POST.get('who', 'passenger')  # or driver
        taxiuser = taxiuser_get(request.user.id)    # dict
        order = Order.objects.filter(id=int(request.POST.get('order_id', 0))).first()
        if not taxiuser:
            result["error"] = '%s <a href="/carpool/agreement/%s/">%s</a>' % (_('Вы не зарегистрированы в сервисе "Попутчик"'), who, _('Зарегистрироваться'))
        elif not order:
            result["error"] = _('Указан отсутствующий заказ')
        else:
            order.trip_status = 3   # 'Поездка началась' (taxi/models.py, TRIP_STATUS)
            order.save()
            order = order_get(order.id, force=True)

            cc_key = "torders_%s" % us.city.id
            torders = rcache_get(cc_key, {})
            torders[order['id']] = order   # dict!
            rcache_set(cc_key, torders, 3600)

            result["result"] = order

            data = {
                "event": "trip_start",  # поездка начата
                "data": json.dumps(order, default=str),
            }
            sio_pub("ru.bustime.taxi__%s" % us.city.id, {"taxi": data})
    except:
        result["error"] = traceback.format_exc(limit=1)

    return HttpResponse(json.dumps(result, default=str), content_type='application/json')
# trip_start


# сообщение пользователю
@require_http_methods(["POST"])
@login_required()
def taxi_message(request):
    result = {
        "error": None,
        "result": None
    }

    try:
        us = get_user_settings(request) # пассажир

        taxiuser_from = taxiuser_get(request.user.id)    # dict
        taxiuser_to = taxiuser_get(request.POST.get('to', 0))    # dict
        msg = request.POST.get('msg')

        if not taxiuser_from:
            result["error"] = _('Нет отправителя')
        elif not taxiuser_to:
            result["error"] = _('Нет получателя')
        elif not msg:
            result["error"] = _('Нет сообщения')
        else:
            message = {
                'from': taxiuser_from['user'],
                'to': taxiuser_to['user'],
                'msg': msg,
                'order_id': int(request.POST.get('order_id', 0)),
            }
            data = {
                "event": "chat",
                "data": json.dumps(message, default=str),
            }
            sio_pub("ru.bustime.taxi__%s" % us.city.id, {"taxi": data})

            result["result"] = True
    except:
        result["error"] = traceback.format_exc(limit=1)

    return HttpResponse(json.dumps(result, default=str), content_type='application/json')
# message