# -*- coding: utf-8 -*-

from itertools import pairwise
from bustime.models import *
from bustime.detector_nocity import ng_detector
from django.contrib.gis.geos import Point
from django.forms.models import model_to_dict
from operator import itemgetter, attrgetter
from functools import cmp_to_key
from bustime.utils import dictfetchall
from collections import defaultdict
from statistics import mean

import logging
import copy
import time
import json

'''
Отладка:
python coroutines/turbomill.py -c <city.id>

После отладки запустить:
sudo supervisorctl restart turbos:*
'''


VEHICLE_CACHE_STALE_INTERVAL = 20
def is_valid_lon_lat(lon, lat):
    try:
        lat, lon = float(lat), float(lon)
    except ValueError:
        return False
    if lat < -90 or lat > 90:
        return False
    if lon < -180 or lon > 180:
        return False
    return True

def fill_bmapping(city):
    # заполняет таблицу соответствия
    bmapping = {}
    mapping = mapping_get(city)
    if type(mapping) is dict:
        for k, m in mapping.items():
            bmapping[k] = (m['bus'], m['gosnum'])
    else:
        for m in mapping:
            bmapping[m.xeno_id] = (m.bus, m.gosnum)
    return bmapping


def lava_sort_up(lava_x, lava_y):
    if lava_x.get('d') == None:
        return 1
    if lava_y.get('d') == None:
        return -1

    if lava_x['d'] == lava_y['d']:
        return lava_x['order'] - lava_y['order']
    elif lava_x['d'] > lava_y['d']:
        return 1
    else:
        return -1


def hour_rounder(dt):
    return dt + datetime.timedelta(seconds=(60 - dt.second) % 60)    


def calc_timetable(bus, busstops, timer_bst, bdata_mode0, now):
    """ Generator function. Parameters: 
        bus: Processable Bus
        busstops: All Route stops
        timer_bst: list of times that have to move from busstop A to B
        bdata_mode0: main data about current Route
        now: current time in the Route
    Return an iterator of (current_busstop, timetable_forecast, lava, delta_time)
        delta_time: Time that was added to the forecast
    """
    def make_mode3_entry(uid, btime, btime_prev=None, first=False):
        """ Forecasts factory function. Parameters:
            uid: UniqueID of a vehicle that have to arrive at that forecast 
            btime: Forecast time
            btime_prev: Forecast time for vehicle next after current
            first: Does it first busstop from timetable (bus.tt_start)
        """
        entry = {
            # "bid": bus.id,
            "uid": uid, 
            # "n": str(bus), 
            "t": btime.replace(second=0, microsecond=0),
        }
        if btime_prev:
            entry['t2'] = btime_prev.replace(second=0, microsecond=0)
        if first:
            entry['first'] = first
        return entry

    def vehicle_at_the_busstop_now(bst):
        "Return lava of the vehicle that at the busstop (bst) now or None"
        if bst["id"] in bdata_mode0[bus.id][bst["direction"]]["stops"]:
            return next((l for l in bdata_mode0[bus.id]["l"] if l.get('u') and l['b'] == bst["id"]), None)
        return None


    _default_secs = 90
    btime = None
    btime_prev = None
    bdata_mode0_l = None
    for bst_prev, bst in pairwise(busstops):
        # получим список интервалов движения от предыдущей до этой
        cc_key = "%s_%s" % (bst_prev['busstop_id'], bst['busstop_id'])
        # рассчитаем среднее время движения от неё до текущей
        secs = int(mean(timer_bst.setdefault(cc_key, [_default_secs])))
        if secs < 0:
            continue  # Something wrong with that time. It can't be less than zero
            # raise Exception(timer_bst.setdefault(cc_key, [_default_secs]))

        # если на этой остановке находится ТС, то время прихода - сейчас
        if l := vehicle_at_the_busstop_now(bst):  # is_vehicle_at_the_busstop_now(bst):
            bdata_mode0_l = l
            btime_prev = btime
            btime = now
            # узнаем какие конкретно ТС маршрута на этой остановке
            # и сохраним их id и другие данные в bdata_mode3
            mode3_entry = make_mode3_entry(bdata_mode0_l['u'], btime, btime_prev=btime_prev)
            yield bst, mode3_entry, None
        elif btime:
            # прогноз прибытия машины на остановку (на ней нет сейчас ТС)
            # if btime == now:
            #     """
            #     Отматывает назад прогноз прибытия, чтобы компенсировать
            #     задержки передачи и обработки. Психологически людям легче,
            #     когда они успевают на автобус, который вот-вот уезжает.
            #     Срабатывает один раз.
            #     """
            #     btime -= datetime.timedelta(seconds=45)

            # прибавляем время к прошлому накопившемуся прогнозу
            dt = datetime.timedelta(seconds=secs)
            btime += dt
            if btime_prev:
                btime_prev += dt
            # исключает прогноз на прошлое
            if btime < now:
                btime = now
            mode3_entry = make_mode3_entry(bdata_mode0_l['u'], btime, btime_prev=btime_prev)
            yield bst, mode3_entry, secs
        elif bst['order'] == 0 or (bst_prev and bst['direction'] != bst_prev['direction']):
            # начальная (конечная) остановка, на которой сейчас нет ТС
            # прогноз берется из JSON расписания (выходного или обычного)
            # btime = None
            bdata_mode0_l = None
            if is_holiday(now):
                stimes = bus.tt_start_holiday or []
            else:
                stimes = bus.tt_start or []

            if stimes:
                # всякое может быть, поэтому лучше подстраховаться
                try:
                    stimes = json.loads(stimes)
                    stimes = (stime for stime in stimes[str(bst['direction'])] if stime)
                    stimes = [datetime.time(*map(int, stime.split(":"))) for stime in stimes]
                except:
                    stimes = []
            # так как отправка с конечной это список времен, то берем ближайшее будущее
            mode3_entry = next((
                make_mode3_entry(None, datetime.datetime(now.year, now.month, now.day, z.hour, z.minute), first=True) 
                for z in stimes 
                if z >= now.time()
            ), None)
            yield bst, mode3_entry, None
        else:
            # нет вариантов, поэтому обнулим, чтобы затереть предыдущие
            btime = None
            btime_prev = None
            bdata_mode0_l = None
            yield bst, None, None



def mill_event(e, DEBUG=False, PERFMON=False,
               DD=None, last=None, passengers={},
               pipe=None, pipe_io=None, STOPS=None, bus=None,
               rcache_direction=None,
               bdata_mode0={}, bdata_mode1={},
               bdata_mode_10={},
               time_bst={}, amounts={},
               timer_bst={}, time_bst_ts={}, bstops=[], vehicles_info={},
               timetable={},
               datasources={}, turbine_inspector=None, ignores=set()):
    """
    Обрабатывает сырые события, определяет направление транспорта,
    заполняет кэши для различных отображений, отправляет обновления.

    принимает в параметрах:
      DEBUG - отладка
      PERFMON - замеритель скорости обработки
      DD - подготовленные данные get_detector_data(city) от turbo_m, который их держит в памяти
      prev_cached - прошлые уже обработанные данные, чтобы не дергать кэш лишний раз
    """
    if PERFMON:
        perfmon_time = time.time()
    # без координат сразу отбрасываем
    if not e.x or not e.y:
        return False
    if not is_valid_lon_lat(e.x, e.y):
        ch =  f"bustime.turbine_inspector"
        sio_pub(ch, {'turbine_inspector': {'widget': 'inspector', 'text': "not valid lon, lat: %s" % e, 'uid':e.uniqueid}}, pipe=pipe_io)
        return False

    uid = e['uniqueid']
    bus_id = e.bus
    now = now_at(e.x, e.y)
    if not now: return -9
    if e.timestamp < now - datetime.timedelta(seconds=15*60):
        return -5

    # 16.08.24 locman
    if e.timestamp > now + datetime.timedelta(seconds=86400):
        # событие "из будущего", происходит из-за сбоя навигационного оборудования
        # либо из-за ПО ретранслятора
        try:
            with open(f'/tmp/future_events_{now.strftime("%Y.%m.%d")}.log', 'a') as f:
                s = json.dumps(e, default=str, ensure_ascii=False)
                f.write(f'{s}\n')
        except:
            pass
        e['timestamp'] = now

    # clean up old events, which are not updated automatically
    # move to sync adapter?
    last_amounts = len(amounts[0]), len(amounts[1])

    to_remove = set()
    for k,v in last.items():
        # if k != uid and v.timestamp < now - datetime.timedelta(seconds=15*60):
        if v.timestamp < now - datetime.timedelta(minutes=15):
            to_remove.add(k)
            if k in amounts[0]: amounts[0].remove(k)
            if k in amounts[1]: amounts[1].remove(k)
    for _ in to_remove:
        pipe.srem(f'events', _)
        pipe.srem(f'bus__{last[_].bus_id}', _)
        for pid in bus.places_all:
            pipe.srem(f'place__{pid}', uid)
        del last[_]
    
    to_remove = set()
    # for stop in sorted(evt_mode3_map.get(e.uniqueid, {}), key=lambda x: x[1]):
    # for stop in evt_mode3_map.get(uid, []):
    #     if stop[1] < now or e.zombie or e.away or e.sleeping:
    #         to_remove.add(stop)
    # for stop in to_remove:
    #     (stop_id, _) = stop
    #     evt_mode3_map[uid].remove(stop)
    #     # if bdata_mode3_trb.get(e.uniqueid):
    #     #     del bdata_mode3_trb[stop_id][e.uniqueid]
    #     pipe.hdel(f"stop__{stop_id}", uid)
    #     # if not bdata_mode3_trb[stop_id]:
    #     # pipe.delete(f"stop__{stop_id}")
    #     # pipe.srem("bstops_mode3", stop_id)

    # последний выключает свет в аэропорту

    prev = last.get(uid)
    # do nothing if this one is the first
    # todo continue proccessing for status=undetermined ghost buses
    if not prev:
        last[uid] = e
        #0. remove from old buses and places
        oldevent = rcache_get("event_%s" % uid)
        if oldevent and oldevent.bus_id != bus_id:
            pipe.srem(f"bus__{oldevent.bus_id}", uid)
            obus = bus_get(oldevent.bus_id)
            if obus:
                for pid in obus.places_all:
                    pipe.srem(f"place__{pid}", uid)
        # add uid to redis sets once
        # 1. to the bus_id
        pipe.sadd(f"bus__{bus_id}", uid)
        # 2. to the involved osms
        for pid in bus.places_all:
            pipe.sadd(f"place__{pid}", uid)
        # 3. to the all (temporary?)
        pipe.sadd("events", uid)
        pipe.set(f"event_{uid}", pickle_dumps(e), 86400) # 24h expiration
        # there is no point to work with one event only
        return None

    # skip if the same coords
    if prev and prev.x == e.x and prev.y == e.y:
        # warning here, and pass further to spread info
        e["busstop_nearest"] = prev.get("busstop_nearest")
        return -1

    # skip events that comes to frequently
    if prev and e.timestamp < prev.timestamp + datetime.timedelta(seconds=10):
        return -10


    # todo рефакторинг + перенести в redis
    # доп. информация о транспорте
    # vehicles_info = vehicles_cache(city)

    # todo
    # такси, только машины
    # cc_key = "tevents_%s" % city.id
    # tevents = rcache_get(cc_key, {})

    # check for multi_timezone flag
    # zone determine costs 0.242s!
    # отсечка событий из прошлого, не учитывать данные старее 10 минут
    # clim = city.now - datetime.timedelta(seconds=600)

    # todo refactor
    # список уникальных гос№ города
    # cc_gos = "gosnums_%s" % city.id
    # gosnums = rcache_get(cc_gos, {})
    # gosnums_changed = False

    # to move to turbo (redis free checking)
    # customs = rcache_get("customs_%s" % city.id,
    #                      [])  # список гос№ города у которых поле custom == True (см. turbo_ms.py, def process_list)
    # ignores = rcache_get("ignores_%s" % city.id,
    #                      [])  # список uniqueid города, которые должны игнорироваться, так как передаются вручную юзером (нажал кнопку Это моя)

    # начинаем перебирать каждое сырое событие и обрабатывать

    # todo
    # переключаемся на уникальную информацию о машине
    # if gos and not e.get('custom'):

    if not e.get('custom'):
        vehicle_info = vehicles_info.get(e.uniqueid)
        if vehicle_info:
            if vehicle_info['stale_time'] < datetime.datetime.now() or vehicle_info is None:
                # Cache has been outdated
                vinfo = Vehicle.objects.filter(uniqueid=e.uniqueid).values().first() or {'uniqueid': e.uniqueid}
                vinfo['stale_time'] = datetime.datetime.now() + datetime.timedelta(minutes=VEHICLE_CACHE_STALE_INTERVAL)
                vehicles_info[e.uniqueid] = vinfo
                vehicle_info = vinfo
            if vehicle_info:
                # Looks like good cache with data
                if gn := vehicle_info.get('gosnum'):
                    e['gosnum'] = gn
                if lb := vehicle_info.get('bortnum'):
                    e['label'] = lb
                if rmp := vehicle_info.get('ramp'):
                    e['ramp'] = rmp                
                # e["gosnum"] = vehicle_info.get('gosnum', e.get('gosnum'))
                # e["label"] = vehicle_info.get('bortnum', e.get('label'))
                # e["ramp"] = vehicle_info.get('ramp', e.get('ramp', False))
            if e.uniqueid in ignores:
                # чтобы при прекращении ручной передачи восстановилась машина без custom
                clim = now - datetime.timedelta(minutes=1)
                found = 0
                for k,v in last.items():
                    if v.get("gps_send_of") == e.uniqueid:
                        found += 1
                        if v.timestamp < clim:
                            found -= 1
                            print(f"clim of gps_send_of is out of limits: ", e.uniqueid)
                if not found:
                    ignores.remove(e.uniqueid)
                    del last[e.uniqueid] # add it again to events next loop
                    print(f"Deignore gps_send_of: ", e.uniqueid)
                else:
                    return -11
    # custom event, what a pleasure!
    elif e.get("gps_send_of") and e["gps_send_of"] not in ignores:
        _ = e["gps_send_of"]
        ignores.add(_)
        pipe.srem(f'events', _)
        pipe.srem(f'bus__{bus_id}', _)
        for pid in bus.places_all:
            pipe.srem(f'place__{pid}', _)
        # don't delete from last to prevent loop!
        print(f"Ignore gps_send_of: ", e["gps_send_of"])

    # check by data source
    if e.get('src'):
        if e["src"] == "c18.py":
            e["gosnum"] = None

    # ключ для события, немного избыточный чтобы хранить в одном словаре для всех городов,
    # но сейчас в этом уже нет необходимости, так что можно сократить при желании
    # флаг fresh определяет если событие новее прошлого (по дате), старые не пересчитываем
    if prev:
        # если событие уже было обработано, то ничего делать не будем
        if e.timestamp <= prev.timestamp:
            return -2
        nearest_prev = prev.get("busstop_nearest")
        if nearest_prev:
            nearest_prev = DD["R"].get(nearest_prev)

    e["x_prev"], e["y_prev"] = prev.x, prev.y
    e["last_point_update"] = e.timestamp
    # наследуем некоторые характеристики от предыдущего события
    e["timestamp_prev"] = prev.timestamp
    e["sleeping"] = prev.sleeping
    e["last_changed"] = prev.last_changed
    e["dchange"] = prev.dchange

    # если событие свежее, то прогоняем через обработку (ресурсоемко)
    cb_last_changed = None # это что вообще? время последнего изменения текущей остановки

    """
     сохраним предыдущее положение в переменных словаря, они понадобятся

     если предыдущих значений нет, то подставим текущие координаты, чтобы далее
     дистанция перемещения была 0 и CPU будет нагружаться зря, так как
     ng_detector не сможет определить (достоверно) направление без перемещений
    """
    # if not e.get("blast_x"):
    #     if prev:
    #         e["blast_x"], e["blast_y"] = prev.x, prev.y
    #     else:
    #         e["blast_x"], e["blast_y"] = e.x, e.y

    """
    Если расстояние между прошлой позицией и текущей небольшое, то пропускаем это событие.
    30 метров выбрано потому, что у стоящего на месте ТС координаты могут
    передаваться с небольщим смещением из-за погрешности GPS.
    Между двумя событиями ТС должно успевать проезжать более 30 метров при нормальных условиях.

    Если события отправляются и обновляются слишком часто, например каждую секунду, то
    нужно создавать исскуственные задержки в updater, чтобы расстояние между прошлой и текущей позицией
    было более 30 метров. Пример в Helskinki, где данные по протоколу mqtt
    каждую секунду обновляются непрерывным потоком. Демон их сам придерживает в памяти и
    записывает в REDIS раз в 6 секунд, по причине того, что обновлять сериализованный словарь
    с 1000 событий это ресурсоемко. Ограничение частоты обновлений позволяет уменьшить
    количество операций записи и снизить нагрузку.

    В старом добром uevents_%s все события хранятся в одном большом сериализованном
    словаре и для обновления одного события нужно перезаписывать все. В новом поколении
    формата хранения мы перешли на gevents_%s, где одно событие - это
    одно поле ключ/значение в Redis, а все точки берутся массовым взятием перечня ключей.
    Это позволяет обновлять данные по одной точке с минимальной нагрузкой CPU в асинхронном режиме,
    События собирает и объединяет перед отправкой в этот обработчик turbo_m.

    В turbo_m стоит еще одна принудительная задержка в 10с. Эта задержка - баланс
    между нагрузкой на сервер и скоростью обновлениях данных.
    """
    # mdist = distance_meters(e["blast_x"], e["blast_y"], e.x, e.y)
    # if mdist < 30:
    #     e['busstop_nearest'] = None
    # else:
    #     # непонятный код от @locman
    #     # uid = e.uniqueid if e.get("rcache", False) else None
    #     # по 2 точкам выдает остановку, куда направляется ТС
    #     e['busstop_nearest'] = ng_detector(e.bus, e["blast_x"], e["blast_y"], e.x, e.y, DEBUG=False,
    #                                        nearest_prev=nearest_prev, uniqueid=uid, DD=DD)
    e["blast_x"], e["blast_y"] = prev.x, prev.y
    mdist = distance_meters(e["blast_x"], e["blast_y"], e.x, e.y)
    if mdist < 30:
        e["busstop_nearest"] = prev.get("busstop_nearest")
    else:
        e['busstop_nearest'] = ng_detector(bus, e["blast_x"],
                                       e["blast_y"], e.x, e.y,
                                       DEBUG=False, nearest_prev=nearest_prev,
                                       uniqueid=e["uniqueid"], DD=DD, rcache_direction=rcache_direction)
    if e["busstop_nearest"] == -1:
        e["busstop_nearest"] = None
        e["away"] = True  # съехал с маршрута
    elif e.busstop_nearest:
        e["blast_x"], e["blast_y"] = e.x, e.y
        e["away"] = False
        e['last_point_update'] = prev.timestamp
        if type(e.busstop_nearest) != int:
            e['busstop_nearest'] = e['busstop_nearest'].id
    # если определитель остановки не справился, то будем считать что он там же, где был в прошлый раз
    elif prev and prev.busstop_nearest:
        e["busstop_nearest"] = prev.busstop_nearest
        e["away"] = False

    if e.busstop_nearest:
        nearest = DD['R'].get(e.busstop_nearest)
        if not nearest: return False
        e['direction'] = nearest.direction
        e['nearest_name'] = nearest.busstop.name
        e['nearest_order'] = nearest.order
    else:
        nearest = None

    """
    Если направление изменилось, то не сразу его меняем, а ждем второго подтверждения,
    потому что иначе ТС может скакать туда-сюда на поворотах и сложных моментах.
    Такой подход увеличивает время реакции на разворот транспорта, но снижает
    вероятность неправильного определения направления и/или ближайшей остановки.
    """
    if prev and e.busstop_nearest != prev.busstop_nearest:
        real_change = True
        if e.busstop_nearest and prev.busstop_nearest and DD['R'].get(prev.busstop_nearest) and \
                nearest.direction != DD['R'][prev.busstop_nearest].direction and not \
                DD['R'][prev.busstop_nearest].endpoint and not nearest.endpoint:
            delta = 1 if nearest.direction else -1
            if e["dchange"] is None:
                e["dchange"] = 500
            e["dchange"] += 250 * delta
            if e["dchange"] not in [0, 1000]:
                e["busstop_nearest"] = prev.busstop_nearest
                nearest = DD['R'][prev.busstop_nearest]
                real_change = False
        # real_change здесь может отмениться выше если ТС меняет направление впервые
        if real_change:
            cb_last_changed = e.last_changed
            e["last_changed"] = e.timestamp
            e["dchange"] = 500

    e["zombie"] = False
    if e.busstop_nearest and not e.sleeping:
        # последнее изменение точки > 5 мин
        if e.last_point_update and (e.timestamp - e.last_point_update).total_seconds() > 60 * 5:
            e["zombie"] = True
        # последнее изменение остановки > 15 мин
        if e.last_changed and (e.timestamp - e.last_changed).total_seconds() > 60 * 15:
            # ослабляет требования, если межостановочное расстояние у маршрута большое
            if bus.inter_stops and bus.inter_stops > 4000:
                if (e.timestamp - e.last_changed).total_seconds() > 60 * 30:
                    e["zombie"] = True
            else:
                e["zombie"] = True
        # последнее событие из прошлого > 5 мин
        if (now - e.timestamp).total_seconds() > 60 * 5:
            e["zombie"] = True
            # if DEBUG: print("zombie by total_seconds > 300")
        if e["zombie"]:
            e["away"] = True
        # if any passengers on this stop
        if passengers.get(e.busstop_nearest) and not e["zombie"]:
            passengers[e.busstop_nearest] = []  # clears waiting list



    prev_bdata_mode0 = copy.deepcopy(bdata_mode0) # bdata_mode0.copy() ?
    if not bdata_mode0.get(bus_id):
        bdata_mode0[bus_id] = {
            0: {'stops': []}, 1: {'stops': []}, 'updated': str(now), 'l': []
        }

    for _ in bdata_mode0[bus_id]['l']:
        tsdt = datetime.datetime.fromtimestamp(_['ts'])
        if _['u'] == uid or tsdt < now - datetime.timedelta(seconds=15*60):
            bdata_mode0[bus_id]['l'].remove(_)


    if e.busstop_nearest and nearest:
        prev_mdist = 1000
        start_from_endpoint = False
        # делает чтобы у ТС на конечных был sleep=True
        if e.get("x_prev") and nearest.endpoint:
            prev_mdist = distance_meters(e["x_prev"], e["y_prev"], e.x, e.y)
            end_dist1 = distance_meters(e.x, e.y, nearest.busstop.point.x,
                                        nearest.busstop.point.y)
            end_dist2 = distance_meters(e['x_prev'], e['y_prev'], nearest.busstop.point.x,
                                        nearest.busstop.point.y)
            end_delta = end_dist2 - end_dist1
            # сдвинулся на 60, до остановки стало меньше 300м
            if end_delta > 60 and end_dist1 < 300:
                start_from_endpoint = True
        if nearest.endpoint and prev_mdist < 70 and not start_from_endpoint:
            e["sleeping"] = True
            # код от @skincat определяет в каком направлении должна быть
            # остановка для спящего автобуса
            route_graph = DD['ROUTES_NG'][bus_id][nearest.direction]
            next_stops = [] if not route_graph.has_node(e.busstop_nearest) else list(
                route_graph.successors(e.busstop_nearest))
            prev_stops = [] if not route_graph.has_node(e.busstop_nearest) else list(
                route_graph.predecessors(e.busstop_nearest))
            next_stop = None if not next_stops else next_stops[0]
            prev_stop = None if not prev_stops else prev_stops[0]
            if not next_stop and prev_stop:
                if nearest.direction == 1:
                    ndir = 0
                else:
                    ndir = 1
                # кэш + вдруг нет второго направления
                prev_r = None
                for r in DD['ROUTES'][bus_id]:
                    if r.order == 0 or (r.endpoint and prev_r and \
                                        r.direction != prev_r.direction):
                        if r.direction == ndir:
                            nearest = r
                            e["busstop_nearest"] = r.id
                            e['direction'] = nearest.direction
                            e['nearest_name'] = nearest.busstop.name
                            e['nearest_order'] = nearest.order
                            break
                    prev_r = r
        else:
            e["sleeping"] = False

        """
        lava - подготовленный для выдачи, краткий формат данных ТС
        Описание находится в models.py (в том числе короткие имена и значения словаря)
        Возвращает готовый для выдачи простой словарь, без python объектов,
        готовый для сериализации в JS
        Внимание! есть пост-обработка, например gosnum
        """
        lava = e.get_lava()

        # пакует в словарь busamounts кол-во ТС в каждом направлении
        # по хорошему нужен словарь в словаре, но исторически так сложилось
        # ba_key = "%s_d%s" % (bus_id, e.busstop_nearest.direction)
        # busamounts[ba_key] = busamounts.get(ba_key, 0)

        # если зомби, то убирает лишние данные о направлении, ближайшей остановке и др, см. models.py
        if e.zombie:
            ee = Event(e.copy())
            ee["busstop_nearest"] = None
            lava = ee.get_lava()

        # добавляет инфу в список всех ТС маршрута и обновляет счетчики
        bdata_mode0[bus_id]['l'].append(lava)

        # если ТС активный, то добавляет остановку на которой ТС в список bdata_mode0

        # для формата мультипассажира, bdata_mode1
        # TODO Наверное этот код уже не нужен т.к. mode1 считается на месте
        if not e.zombie and nearest:
            if not bdata_mode1.get(nearest.busstop_id):
                bdata_mode1[nearest.busstop_id] = []
            # словарь для добавление в информацию об остановке маршрута
            # странно что id сам не устанавливается  через lava
            mode1bus = {'id': bus_id}
            # все остальные данные заполняет lava
            # наверное это чтобы сделать копию python словаря не используя .copy()
            mode1bus.update(lava)
            bdata_mode1[nearest.busstop_id].append(mode1bus)
    else:
        lava = e.get_lava()
        bdata_mode0[bus_id]['l'].append(lava)




    if uid in amounts[0]: amounts[0].remove(uid) # remove old ones
    if uid in amounts[1]: amounts[1].remove(uid)
    if nearest and not e.zombie and not e.away and not e.sleeping:
        amounts[nearest.direction].add(uid)

    """
    Сортирует список машин маршрута по направлению и номеру остановок.
    Зачем нужна такая сортировка - точно неизвестно, возможно чтобы порядок
    сохранялся при каждом обороте мельницы и они не мелькали при обновлении
    в каком-то режиме или для мобильных. Правка была внесена 2019-10-11,
    и может быть есть релевантная задача с номером в районе ~1480
    """
    bdata_mode0[bus_id]['l'] = sorted(bdata_mode0[bus_id]['l'], key=cmp_to_key(lava_sort_up))

    for dir_ in [0,1]:
        bdata_mode0[bus_id][dir_]['stops'] = []
    for l in bdata_mode0[bus_id]['l']:
        if l.get('b') and not l.get("sleep") and not l.get("away") and not l.get("z"):
            bdata_mode0[bus_id][l['d']]['stops'].append(l['b'])

    # if gosnums_changed:
    #     rcache_set(cc_gos, gosnums, 60 * 60 * 24 * 30)

    if PERFMON:  # выжный этап для замера времени исполнения, после ресурсоемкого ng_detector
        print("2 : %s seconds" % (time.time() - perfmon_time))
        perfmon_time = time.time()

    last[uid] = e

    # сериализуем и сохраняем все события в allevents
    e['bus_id'] = bus_id
    if e.get("bus"):
        del e['bus']
    pe = pickle_dumps(e)
    pipe.set(f"event_{uid}", pe)

    # pass event to the next processing unit
    # pipe.publish(f"bus_{bus_id}", pe)
    # or
    # another_function(e)




    # pi = pickle_dumps(cache_many)
    # REDIS_W.set("allevents_%s" % city.id, pi, ex=60 * 5)

    """
    Вычисляет оранжевые маркеры общего числа машин (Автобусы, Троллейбусы, Трамваи, Маршрутки и т.д.).
    Отображается на Вкладках (Табах) на главной странице
    """
    # counters_by_type_prev = rcache_get(f"counters_by_type__{city.id}")
    # if counters_by_type != counters_by_type_prev:
    #     new_counters = {}
    #     if counters_by_type_prev:
    #         for key, value in counters_by_type.items():
    #             if counters_by_type[key] != counters_by_type_prev[key]:
    #                 new_counters[key] = value
    #     else:
    #         new_counters = counters_by_type
    #     data = {"counters_by_type": new_counters}
    #     sio_pub(f"ru.bustime.counters__{city.id}", data)

    # REDIS_W.set("counters_by_type__%s" % city.id, pi, ex=60 * 5)

    # сообщение для веб-логов, надо переписать на словарь, чтобы локализовать нормально
    # это плохой стиль программирования, так делать не следует
    # message = u"received: %s, updated: %d" % (len(events), cnt_fresh)
    # log_message(message, ttype="update_lib", city=city)
    # l = {"message": message, "date": str(now)[:-4]}
    # sio_pub("bustime/status__%s" % osm_id, {'status_log': {'ups': [l]}})
    # if DEBUG: print(message)



    if PERFMON:
        print("3 : %s seconds" % (time.time() - perfmon_time))
        perfmon_time = time.time()

    """
    Эти онлайн обновления bdata_mode0 переехали из rainsys.
    Задача: сформировать изменившиеся события и отправть в релевантный редис канал,
    на который подписаны пользователи.
    Шаг 1. Берет предыдущие значения из кэша, чтобы понять если надо транслировать обновление
           Take prev cache to understand if we need to broadcast update.
    """
    # if bdata_mode0:
    #     bdata_mode0_keys = list(bdata_mode0.keys())
    #     crowd = ["bdata_mode0_%s" % x for x in bdata_mode0_keys]
    #     crowd = rcache_mget(crowd)
    #     bdata0_prev = {}
    #     bdata_mode0_keys.reverse()
    #     for _ in bdata_mode0_keys:
    #         bdata0_prev[_] = crowd.pop()

    # pipe.set("bdata_mode0_%s" % (bus_id), pickle_dumps(bdata_mode0[bus_id]), ex=60 * 10)

    if PERFMON:
        print("4 : %s seconds" % (time.time() - perfmon_time))
        perfmon_time = time.time()

    # сериализуем и записываем в буфер изменений кэша pipe, который можно позже пакетно запустить
    # здесь же работаем с пассажирами на остановках (можно оптимизировать через rcache_mget)
    # если автобус на остановке где были пассажиры, то обнуляет их
    # пассажиры хранятся как список/сет id пользователей, чтобы не дублировались



    """
    Обновление busamounts (количество ТС на линии) через redis publish.
    Раньше определялось через сигналы redis и рассылалось rainsys.
    Теперь все делается здесь.
    Сначала берем прошлые для сравнения данные и обнаружаем разницу,
    собираем словарь того, что изменилось и отправляем в канал.
    """
    baupdate = {}
    for dir_ in [0,1]:
        if last_amounts[dir_] != len(amounts[dir_]):
            baupdate[f'{bus_id}_d{dir_}'] = len(amounts[dir_])
    if baupdate:
        for pid in bus.places_all:
            sio_pub("ru.bustime.bus_amounts__%s" % pid, {"busamounts": baupdate}, pipe=pipe_io)
            if turbine_inspector:
                sio_pub(turbine_inspector, {'turbine_inspector': {'widget': 'socket_io', 'text': str(baupdate), 'uid':e.uniqueid}}, pipe=pipe_io)


    # Повторяем для bdata_mode1
    # buses_of_city = buses_get(city)
    # bdata_mode1_keys = [x.id for x in buses_of_city]
    # crowd = ["bdata_mode1_%s" % x for x in bdata_mode1_keys]
    # crowd = rcache_mget(crowd)
    # bdata1_prev = {}
    # bdata3_prev = rcache_get("bdata_mode3_%s" % city.id, {})
    # bdata_mode1_keys.reverse()
    # for _ in bdata_mode1_keys:
    #     bdata1_prev[_] = crowd.pop()

    # if PERFMON:
    #     print("5 : %s seconds" % (time.time() - perfmon_time))
    #     perfmon_time = time.time()

    # for bus in buses_of_city:
    #     tosend = {}
    #     for s in STOPS.get(bus.id, {}):
    #         zs = bdata_mode1.get(s, [])
    #         if zs:
    #             tosend[s] = zs

    #     if tosend:
    #         pi = pickle_dumps(tosend)
    #         pipe.set("bdata_mode1_%s" % bus.id, pi, ex=60 * 10)
    #         # определяет если есть изменения и только в таком случае рассылает
    #         # тут даже sio_pub делается через pipe, что должно быть быстрее
    #         if tosend != bdata1_prev.get(bus.id):
    #             chan = "ru.bustime.bus_mode1__%s" % bus.id
    #             serialized = {"bdata_mode1": tosend, "bus_id": bus.id}
    #             sio_pub(chan, serialized, pipe=pipe)
    #             # здесь небольшие модификации для мобильных, bus_mode11
    #             # удлаляет номер остановки и название, так как там есть своя БД
    #             chan = "ru.bustime.bus_mode11__%s" % bus.id
    #             for k, v in tosend.items():
    #                 for vv in v:
    #                     if vv.get('bn'):
    #                         del vv['bn']
    #                         del vv['order']
    #             serialized = {"bdata_mode11": tosend, "bus_id": bus.id}
    #             sio_pub(chan, serialized, pipe=pipe)
    # pipe.execute()

    if PERFMON:
        print("6 : %s seconds" % (time.time() - perfmon_time))
        perfmon_time = time.time()

    # Фундамент для асинхронного протокола на клиентах
    if nearest_prev != nearest:
        if nearest_prev and nearest_prev.busstop_id:
            sio_pub(f"bustime.stop.now.{nearest_prev.busstop_id}", {})
        if nearest and nearest.busstop_id:
            sio_pub(f"bustime.stop.now.{nearest.busstop_id}", lava)

    """
    timer_bst хранит массив времени, необходимого чтобы доехать от остановки A до B
    Используется для прогнозов прибытия машины и в табло.
    Иногда, если источник не часто обновляется, то автобус может
    проскочить две остановки и это никак не обрабатывается.
    detect time amount to get from busstop b1 to busstop b2

    Так как данные собираются с разных маршрутов, то выбрано хранить последние
    10 как разумное среднее. Структура:
    <id_остановка1>_<id_остановка2>: [ехал 10 сек, ехал 15 сек, ...]
    пример:
    {'49374_49187': [80, 75, 63, 80, 45, 87, 60, 60, 60, 105],
     '83772_83705': [76, 105, 75, 90, 156, 75, 76, 111, 105, 112]
    }
    """

    # timer_bst = rcache_get("timer_bst_%s" % city.id, {})
    # пробегает по ТС у которых изменилась остановка, а значит можно посчитать

    # prev = last.get(e.uniqueid)
    # проверяет, чтобы остановки были соседними, иначе кэш
    # разрастается ненужными данными
    if nearest_prev and nearest and \
            nearest.order - nearest_prev.order == 1 and \
            nearest.direction == nearest_prev.direction and \
            cb_last_changed:
        dsecs = int(
            (e.timestamp - cb_last_changed).total_seconds())
        # не позволяет проходить грязным данным, когда время > 20 минут
        if dsecs < 60 * 20 and dsecs > 0:
            # cc_key = "%s_%s" % (
            #     prev.busstop_nearest.busstop_id, e.busstop_nearest.busstop_id)
            cc_key = "%s_%s" % (nearest_prev.busstop_id, nearest.busstop_id)
            prevt = timer_bst.get(cc_key, [])
            prevt.append(dsecs)
            timer_bst[cc_key] = prevt[-10:]  # last 10 values
    if PERFMON:
        print("7 : %s seconds" % (time.time() - perfmon_time))
        perfmon_time = time.time()

    # if e.busstop_nearest:
    #     nearest = DD['R'].get(e.busstop_nearest)
    #     pipe.publish("timetable_event", pickle_dumps((e, nearest)))

    """
    тут похожее название, но данные не о времени между остановками, а о прогнозе.
    time_bst - формат для web (строка)
    time_bst_ts - формат для мобильных (unix timestamp, поэтому название _ts)
    """
    # time_bst = rcache_get("time_bst_%s" % city.id, {})
    # time_bst_ts = rcache_get("time_bst_ts_%s" % city.id, {})
    # # словарь со списком остановок маршрута, порядком и направлением
    # # пример: { 16172: [{'id': 2038067,'bus_id': 16172,'busstop_id': 1803,'endpoint': True,'direction': 0,'order': 0}}
    # city_routes = city_routes_get(city)
    # if PERFMON:
    #     print("8 : %s seconds" % (time.time() - perfmon_time))
    #     perfmon_time = time.time()


    """
    Расчет времени прибытия на каждую остановку.
    Для каждого маршрута своя обработка.
    """
    busstop_timer = {bus.id: {}}

    if not time_bst.get(bus.id):
        time_bst[bus.id] = {}
    if not time_bst_ts.get(bus.id):
        time_bst_ts[bus.id] = {}
    time_bst_prev = copy.deepcopy(time_bst)

    if PERFMON:
        print("8 : %s seconds" % (time.time() - perfmon_time))
        perfmon_time = time.time()

    timetable_prev = copy.deepcopy(timetable)
    timetable.clear()
    route_stops = bstops + bstops[:1]
    # bdata_mode0_r = {}
    for bst, mode3_entry, secs in calc_timetable(bus, route_stops, timer_bst, bdata_mode0, now):
        if bst['direction'] == 2:
            print("!!! direction=2 %s", uid)
            return -3
        sid = bst['busstop_id']

        # pipe.hdel(f"busstop__{bst['busstop_id']}", uid)
        # занесём в таймер "сколько осталось до прихода следующего автобуса этого маршрута"
        if secs:
            busstop_timer[bus_id][bst['id']] = secs
        if mode3_entry:
            if (mode3_uid := mode3_entry.get('uid', 'first')) == "first" or mode3_uid == uid:
                timetable.setdefault(mode3_uid, {}).setdefault(sid, {})['t'] = mode3_entry['t']
                if mode3_entry.get('t2'):
                    timetable[mode3_uid][sid]['t2'] = mode3_entry['t2']
            btime = mode3_entry['t']
            if btime < now:
                stime = u"%02d:%02d" % (now.hour, now.minute)
            else:
                stime = u"%02d:%02d" % (btime.hour, btime.minute)
            time_bst[bus_id][bst['id']] = stime  # Best time in human readable format
            time_bst_ts[bus_id][bst['id']] = int(btime.timestamp()) # Best time in Unix timestamp
        else:
            time_bst[bus.id][bst['id']] = u""
            time_bst_ts[bus.id][bst['id']] = 0

    if timetable_prev != timetable:
        pipe.publish("timetable_update", pickle_dumps((bus_id, bus.name, timetable, e.get_lava())))
    # pipe.sadd(f"turbo_forecasts_sync", bus_id)

    if PERFMON:
        print("9 : %s seconds" % (time.time() - perfmon_time))
        perfmon_time = time.time()

    time_bst_diff = {}
    time_bst_ts_diff = {}
    for k,v in time_bst[bus_id].items():
        if time_bst_prev.get(bus_id, {}).get(k) != v:
            time_bst_diff[k] = v
            time_bst_ts_diff[k] = time_bst_ts[bus_id][k]
    # todo keep only one!, refactor web client to adopt timestamps
    if time_bst_diff:
        pipe.hset("time_bst__%s" % bus_id, mapping=time_bst_diff)
        pipe.hset("time_bst_ts__%s" % bus_id, mapping=time_bst_ts_diff)
        pipe.expire("time_bst__%s" % bus_id, 60*15)
        pipe.expire("time_bst_ts__%s" % bus_id, 60*15)

    # 1th/1024 chance to save to semi-permanent, turbine reload resistant cache
    if random.randint(1,1024) == 1:
        pipe.set("timer_bst_%s" % bus_id, pickle_dumps(timer_bst))
        # pipe.set("bdata_mode3_%s" % bus_id, pickle_dumps(bdata_mode3))

    if PERFMON:
        print("10: %s seconds" % (time.time() - perfmon_time))
        perfmon_time = time.time()


    # sio bdata0 upgrade, no rainsys anymore - performance enhancement
    # Шаг 2. Сравниваем и отправляем подписанным на redis канал.

    # исключает влияние updated при сравнении
    dea = copy.deepcopy(bdata_mode0.get(bus_id))
    deb = copy.deepcopy(prev_bdata_mode0.get(bus_id))
    if dea.get("updated"):
        updated = dea['updated'].split('.')[0]
        del dea['updated']
    if deb and deb.get('updated'):
        del deb['updated']

    # если данные изменились, то сериализуем и отправляем
    if dea != deb:
        serialized = {"bdata_mode0": copy.deepcopy(bdata_mode0[bus_id])}
        serialized["bdata_mode0"]['updated'] = updated.split(" ")[1]
        serialized["bdata_mode0"]['bus_id'] = bus_id
        serialized['time_bst'] = time_bst_diff

        # bus_mode0 sio disabled
        # chan = "ru.bustime.bus_mode0__%s" % bus_id
        # sio_pub(chan, serialized, pipe=pipe_io)

        # формат для мобильных
        bdata10 = {"bdata_mode10": serialized["bdata_mode0"], 'time_bst': time_bst_ts.get(bus_id, {})}
        del bdata10["bdata_mode10"][0]
        del bdata10["bdata_mode10"][1]
        l = []
        for be in bdata10["bdata_mode10"]['l']:
            if not be.get("z"):
                if be.get('bn'):
                    del be['bn']
                if be.get('order'):
                    del be['order']
                l.append(be)
        bdata10["bdata_mode10"]['l'] = l
        sio_pub("ru.bustime.bus_mode10__%s" % bus_id, bdata10, pipe=pipe_io)
        # странный код, наверное какое-то забытое наследие - закоментирую, 2022-10-14 (norn)
        # используется в мобильных
        if busstop_timer:
            sio_pub("ru.bustime.bus_mode5__%s" % bus_id, {"busstop_timer": {str(bus_id): busstop_timer[bus_id]}}, pipe=pipe_io)

    # check if DataSource exists
    if e.get('channel') and e.get('src'):
        cc_key = "%s*%s" % (e['channel'], e['src'])
        if not datasources.get(cc_key):
            ds, cr = DataSource.objects.get_or_create(channel=e['channel'], src=e['src'])
            datasources[cc_key] = [ds, ds.places.all().values_list("id", flat=True)]
        ds, ds.places_all = datasources[cc_key]

        # check if this places are listed in DataSource
        for place in bus.places_all:
            if not place:
                # some strange thing to debug
                print(bus.id, bus, "No places in places_all!", bus.places_all)
            if place and place not in ds.places_all:
                ds.places.add(place)
                datasources[cc_key] = [ds, ds.places.all().values_list("id", flat=True)]

        # Trying to create or update Vehicle with valid gosnum, bornum, ramp and datasource
        vehicle = None
        if not vehicles_info.get(e['uniqueid']):
            vehicle, cr = Vehicle.objects.get_or_create(uniqueid=e['uniqueid'])
            vinfo = model_to_dict(vehicle) # Convert vehicle to dict
            vinfo['stale_time'] = datetime.datetime.now() + datetime.timedelta(minutes=VEHICLE_CACHE_STALE_INTERVAL)
            vehicles_info[e['uniqueid']] = vinfo
        # We have Vehicle but may be it has empty gosnum, bortnum, ramp or datasource
        vinfo = vehicles_info[e['uniqueid']]
        update_fields = {}
        if not vinfo.get('channel') or not vinfo.get('src'):
            update_fields['channel'] = e.get('channel')
            update_fields['src'] = e.get('src')
        if not vinfo.get('uid_provider') and e.get('uid_original'):
            update_fields['uid_provider'] = e['uid_original']
        if not vinfo.get('gosnum') and e.get('gosnum'):
            update_fields['gosnum'] = Vehicle.format_gosnum(e['gosnum'])
        if not vinfo.get('bortnum') and e.get('label'):
            bortnum = Vehicle.format_bortnum(e['label'])
            if bortnum:
                update_fields['bortnum'] = e['label']
        if not vinfo.get('ramp') and e.get('ramp'):
            update_fields['ramp'] = e['ramp']
        if not vinfo.get('datasource'):
            update_fields['datasource'] = ds.id
        # Update fields if we fill something
        if update_fields:
            vinfo.update(update_fields)
            vehicles_info[vinfo['uniqueid']] = vinfo
            Vehicle.objects.filter(uniqueid=vinfo['uniqueid']).update(**update_fields)


    # if counters_prev != counters_curr:
    #     data = {"status_counter": counters_curr}
    #     chan = f"ru.bustime.status__{city.id}"
    #     sio_pub(chan, data)
    if PERFMON:
        print("12: %s seconds" % (time.time() - perfmon_time))
    return e
