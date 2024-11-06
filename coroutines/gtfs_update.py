#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Запуск обработчика gtfs данных реального времени

Тестирование:
python coroutines/gtfs_update.py 1 --debug

рестарт всех:
sudo supervisorctl restart gtfs_updaters:*
'''
from __future__ import absolute_import
from __future__ import print_function
from devinclude import *
from bustime.models import *
from bustime.views import *
import argparse
import importlib
import six
import random
import requests
import csv
from google.transit import gtfs_realtime_pb2
import traceback
import pyrfc6266
from pathlib import Path
from timezonefinder import TimezoneFinder
from pytz import timezone, utc
from datetime import datetime, timedelta
from django.db.models import Q, Subquery, Count
import codecs
CACHE_TIMEOUT_SEC = 86400
fm = gtfs_realtime_pb2.FeedMessage()

# https://developers.google.com/transit/gtfs-realtime/reference?hl=ru#enum-vehiclestopstatus
VehicleStopStatus = {
    '0': 'INCOMING_AT',      # Транспортное средство прибывает на остановку
    '1': 'STOPPED_AT',       # Транспортное средство находится на остановке
    '2': 'IN_TRANSIT_TO'     # Транспортное средство отправилось с предыдущей остановки и находится в пути
}
CACHE_TIMEOUT_SEC = 86400
EVENT_CHANNEL = 'gtfs_updater'

# вызывается из g_update или gtfs_update.py
def update(catalog, trip_dict, pids, route_dict, DEBUG=False, tz_offset=None):
    if DEBUG: print("update(%s)" % (catalog.id))

    retval = 1

    if not REDIS.sismember("updaters", f"gtfs_updater_{catalog.id}"):
        REDIS_W.sadd("updaters", f"gtfs_updater_{catalog.id}")

    for pid in pids:
        updater = {"state": CityUpdaterState.UPDATE.name.lower()}
        sio_pub(f"ru.bustime.updater__{pid}", {"updater": updater})

    try:
        if DEBUG:
            print(f"{catalog.id}: GET {catalog.url_rt_positions}")
            print(f"request_auth={catalog.request_auth}")

        tic = time.monotonic()
        if catalog.request_auth:
            locals={"headers":None,"auth":None}
            exec(catalog.request_auth, None, locals)
            if locals["headers"] and locals["auth"]:
                r = requests.get(catalog.url_rt_positions, headers=locals["headers"], auth=locals["auth"], timeout=10)
            elif locals["headers"]:
                r = requests.get(catalog.url_rt_positions, headers=locals["headers"], timeout=10)
            elif locals["auth"]:
                r = requests.get(catalog.url_rt_positions, auth=locals["auth"], timeout=10)
        else:
            r = requests.get(catalog.url_rt_positions, timeout=10)
        delay = time.monotonic() - tic
        if r.status_code == requests.codes.ok:
            fm.ParseFromString(r.content)
            message = {
                "state": CityUpdaterState.POST_UPDATE.name.lower(),
                "method": "g_update",
                "provider_events_count": getattr(fm.entity, "__len__", lambda: 0)(),
                "provider_delay": round(delay, 2)
            }
            for pid in pids:
                sio_pub(f"ru.bustime.updater__{pid}", {"updater": message})
            tz_offset = decode_pb2(catalog, fm.entity, trip_dict, route_dict, tz_offset=tz_offset, DEBUG=DEBUG)
        else:
            retval = -1
            if DEBUG:
                print(f"BAD request status code [{r.status_code}]")
            # 429 Too Many Requests — сервер получает слишком много запросов с одного IP-адреса в течение определённого периода времени
            time.sleep(61)
    except Exception as ex:
        if DEBUG: print(str(ex))
        time.sleep(61)
    return retval, tz_offset
# update


def decode_pb2(catalog, entities, trip_dict, route_dict, DEBUG=False, tz_offset=None):
    stat_key = f"gtfs_updater_{catalog.id}"
    stat_info = {}  #rcache_get(stat_key, {})
    stat_info['channel'] = EVENT_CHANNEL
    stat_info['src'] = catalog.id
    stat_info['fire'] = datetime.utcnow().strftime("%d.%m.%y %H:%M:%S")
    stat_info["entities"] = 0
    stat_info['events'] = 0
    stat_info["route_found"] = set()
    stat_info["route_none"] = set()
    stat_info["trip_found"] = set()
    stat_info["trip_none"] = set()

    pipe = REDIS_W.pipeline()

    for entity in entities:
        # структуру entity см. ниже
        #if DEBUG: print("entity=", entity)

        vp = entity.vehicle
        #if DEBUG: print("vp=", vp)

        if not vp.trip: # не сможем найти маршрут
            continue
        if vp.position.longitude == 0 or vp.position.latitude == 0: # bad coordinates
            #if DEBUG: print('SKIP 0.0 lon/lat')
            continue
        elif (not vp.trip.route_id) and (not vp.trip.trip_id):
            # нет никаких идентификаторов маршрута
            if DEBUG: print("*** Not found key 'trip_id' or 'route_id' in vp.trip")
            continue

        stat_info["entities"] += 1

        # маршрут
        bus_id = None
        if vp.trip.route_id:
            bus_id = route_dict.get(vp.trip.route_id)
            if bus_id:
                stat_info["route_found"].add(vp.trip.route_id)

        if not bus_id and vp.trip.trip_id:
            # по trip_id находим route_id, по route_id находим bus_id
            bus_id = trip_dict.get(vp.trip.trip_id)
            if bus_id:
                stat_info["trip_found"].add(vp.trip.trip_id)

        if not bus_id:
            if vp.trip.route_id:
                stat_info["route_none"].add(vp.trip.route_id)
                if DEBUG: print("*** Not found bus for route_id: %s" % vp.trip.route_id)
            if vp.trip.trip_id:
                stat_info["trip_none"].add(vp.trip.trip_id)
                if DEBUG: print("*** Not found bus for trip_id: %s" % vp.trip.trip_id)
            continue

        # time
        # temporary set once per dataset for performance reasons
        # must be recalced on every point to support interzone routes!
        if not tz_offset:
            tz_offset = get_offset(lng=vp.position.longitude, lat=vp.position.latitude, DEBUG=DEBUG)
            if DEBUG: print("tz_offset", tz_offset, flush=True)
        stat_info['tz_offset'] = tz_offset/60
        timestamp = datetime.utcfromtimestamp(vp.timestamp) + timedelta(minutes=tz_offset)

        # навигационные данные
        if vp.position.speed != None:
            speed = int(float(vp.position.speed))
        else:
            speed=24

        if vp.position.bearing != None:
            bearing = int(float(vp.position.bearing))
        else:
            bearing=0

        gosnum = vp.vehicle.label.strip() if vp.vehicle.label else None

        # навигационное событие
        if vp.vehicle.id:
            vehicle_id = vp.vehicle.id
        elif vp.vehicle.label:
            vehicle_id = vp.vehicle.label
        else:
            if DEBUG: print("No vehicle.id/vehicle.label")
            continue

        e = Event(uniqueid=vehicle_id,
                    timestamp=timestamp,
                    x=round(vp.position.longitude, 6),
                    y=round(vp.position.latitude, 6),
                    bus=bus_id,
                    speed=speed,
                    heading=bearing,
                    gosnum=gosnum,
                    channel=EVENT_CHANNEL,
                    src=str(catalog.id))
        stat_info['events'] += 1
        #if DEBUG: print(e)

        # текущая остановка, эти данные могут отсутствовать
        """
        current_stop_sequence, int
        Индекс текущей остановки в последовательности остановок.
        Значение current_stop_sequence определяется значением current_status.
        Если поле current_status не заполнено, предполагается, что транспортное средство находится в пути (IN_TRANSIT_TO)

        current_status, VehicleStopStatus, см. выше
        Точный статус транспортного средства относительно текущей остановки.
        Игнорируется, если параметр current_stop_sequence отсутствует.

        stop_id, string
        Остановка, на которой находится транспортное средство.
        Значение должно быть таким же, как в файле stops.txt соответствующего фида GTFS

        Внимание: любой из этих параметров может отсутствовать в любой их комбинации, например:
        в фиде 7: есть current_stop_sequence и current_status, но нет stop_id
        в фиде 11: есть current_status и stop_id, нет current_stop_sequence
        """
        if vp.stop_id:
            stop_xeno_id = "%s*%s" % (catalog.id, vp.stop_id)
            e['xeno_nearest'] = route_dict.get(str(bus_id), {}).get(stop_xeno_id, {}).get('route_id')
            e['xeno_nearest_status'] = VehicleStopStatus.get(str(vp.current_status))
        elif type(vp.current_stop_sequence) == int: # ибо может быть 0 или None
            if vp.trip and vp.trip.trip_id and vp.trip.trip_id.strip(): # трипа тоже может не быть
                routes = route_dict.get(str(bus_id), {})    # упорядочены по direction,order
                if routes:
                    trip_id = "%s*%s" % (catalog.id, vp.trip.trip_id) # см. utils/gtfs_loader.py стр. 88-105
                    direction_id = int(trip_dict.get(trip_id, {}).get('direction_id', '-1'))
                    if direction_id > -1:
                        for busstop__xeno_id, route in routes.items():
                            if route['direction'] == direction_id and route['order'] == vp.current_stop_sequence:
                                e['xeno_nearest'] = route['route_id']
                                e['xeno_nearest_status'] = VehicleStopStatus.get(str(vp.current_status))
                                break

        pipe.publish(f"turbo_{e.bus}", pickle_dumps(e))

        if DEBUG:
            bus = bus_get(bus_id)
            print("%4s" % bus, "%6s" % e.bus, f'{datetime.utcfromtimestamp(vp.timestamp)}+{tz_offset}={e.timestamp}', e.uniqueid, "%5s" % vp.vehicle.id, "%6s" % e.gosnum, "%2.6f" % e.x, e.y)
    # for entity in entities

    if stat_info['events'] > 0:
        pipe.execute()

    stat_info["route_found"] = len(stat_info["route_found"])
    stat_info["route_none"] = len(stat_info["route_none"])
    stat_info["trip_found"] = len(stat_info["trip_found"])
    stat_info["trip_none"] = len(stat_info["trip_none"])
    if DEBUG: print('stat_info:', stat_info)
    rcache_set(stat_key, stat_info, 60)
    return tz_offset
# decode_pb2


# returns a location's time zone offset from UTC in minutes
# https://timezonefinder.readthedocs.io/en/latest/2_use_cases.html#getting-a-location-s-time-zone-offset
# now_at(lon, lat) # models.py
def get_offset(lng, lat, DEBUG=False):
    # critical for correct detection
    tf = TimezoneFinder()
    tz_name = tf.timezone_at(lng=lng, lat=lat)
    tz = timezone(tz_name)
    now = datetime.now()
    today_target = tz.localize(now)
    today_utc = utc.localize(now)
    retval = (today_utc - today_target).total_seconds() / 60
    retval = int(retval)
    if DEBUG: print(f'.get_offset({lng}, {lat})={retval} ({tz_name})')
    return retval


def error_manager(catalog, now, result, DEBUG=False):
    cc_key = 'error_gtfs_%s' % catalog.id
    error_update = rcache_get(cc_key, {})
    ff = error_update.get('lasts', [])
    ff.append(result)
    ff = ff[-10:]
    error_update['lasts'] = ff

    if result is True:
        if error_update.get('panic'):
            now_str = str(now).split('.')[0]
            wsocket_cmd('error_update', {'status':0, "tm":now_str}, channel="gtfs__%s" % catalog.id)
            message = u"Соединение восстановлено"
            if not DEBUG: log_message(message, ttype="coroutines/gtfs_update.py")
            l = {"message":message, "date":six.text_type(datetime.now())[:-4]}
            sio_pub("ru.bustime.status_gtfs__%s" % catalog.id, {'status_log': {'errors':[l]}})
            REDIS_W.publish('_bot_status', u"✅ %s: %s" % (message, catalog.name))
            error_update['panic'] = False
            error_update['last_error'] = None
        else:
            error_update['good_time'] = now
    else:
        if not [x for x in error_update['lasts'] if x == True] and not error_update.get('panic'):
            if not error_update.get('last_error'):
                error_update['last_error'] = now
            error_update['panic'] = True
            now_str = str(now).split('.')[0]
            wsocket_cmd('error_update', {'status':1, "tm":now_str}, channel="gtfs__%s" % catalog.id)
            message = u"Ошибка соединения с сервером данных"
            if not DEBUG: log_message(message, ttype="coroutines/gtfs_update.py")
            l = {"message":message, "date":six.text_type(datetime.now())[:-4]}
            sio_pub("ru.bustime.status_gtfs__%s" % catalog.id, {'status_log': {'errors':[l]}})
            REDIS_W.publish('_bot_status', u"⚠️ %s: %s" % (message, catalog.name))
            error_update['notified'] = now

    rcache_set(cc_key, error_update, 60*60*24)
    return error_update
# error_manager


def FeedUpdater(catalog_id, DEBUG=False):
    if DEBUG: print(f"Load catalog {catalog_id}")
    catalog = GtfsCatalog.objects.filter(id=catalog_id).exclude(url_rt_positions__isnull=True).exclude(url_rt_positions__exact='').first()
    if catalog:
        pdata = json.loads(catalog.pdata)
        route_dict, trip_dict, pids = pdata['route_id'], pdata['trip_id'], pdata['places']
        tz_offset = None    # TODO: pdata['timezones'], https://stackoverflow.com/a/5537942/6249350
        while 1:
            now = datetime.now()
            if DEBUG: print("%s: call updater()" % now)
            result, tz_offset = update(catalog, trip_dict, pids, route_dict, DEBUG=DEBUG, tz_offset=tz_offset)
            delta = (datetime.now()-now).total_seconds()
            delta = round(delta, 2)
            if DEBUG: print("delta=%s" % delta)

            log_counters = rcache_get('log_counters_gtfs_%s' % catalog_id, {})
            nearest_for_select = log_counters.get('nearest', 0)
            sio_pub("ru.bustime.nearest_for_select", {'nearest_for_select_gtfs': {catalog_id: nearest_for_select}})


            sio_pub("ru.bustime.select", {'zbusupd_gtfs': {catalog_id: [delta, result]}})
            sio_pub("ru.bustime.status_gtfs__%s" % catalog_id, {'status_counter': {'api_duration': delta}})

            if result == -1:
                error_manager(catalog, now, False, DEBUG)
            elif result is True:
                error_manager(catalog, now, True, DEBUG)

            timesleep = 13
            if DEBUG: print("sleep %s" % timesleep)
            for i in range(timesleep - 1, 0, -1):
                # publish countdown events to sio_pub
                updater = {'state': CityUpdaterState.IDLE.name.lower(), 'timeout': i}
                for pid in pids:
                    # don't multiply loader for multi gtfscatalog for one city
                    # temporary solution, todo longterm auto detect
                    if catalog.id != 97:
                        sio_pub(f"ru.bustime.updater__{pid}", {"updater": updater})
                time.sleep(1)
        # while 1
    # if catalog
    else:
        message = "GtfsCatalog[%s] not found or its 'url_rt_positions' is empty" % catalog_id
        if DEBUG:
            print(message)
        else:
            log_message(message, ttype="coroutines/gtfs_update.py")
# FeedUpdater


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Updater for gtfs')
    parser.add_argument('catalog_id', metavar='N', type=int, help='catalog id')
    parser.add_argument("--debug", help="debug mode", action="store_true")
    args = parser.parse_args()

    if not args.debug:
        time.sleep(10+random.random()*10)

    print('%s: Updater %s' % (datetime.now(), args.catalog_id))
    FeedUpdater(args.catalog_id, DEBUG=args.debug)
