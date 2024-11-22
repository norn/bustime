#!/bustime/bustime/.venv/bin/python
# -*- coding: utf-8 -*-
"""
Сбор статистики о машинах города,
собираются и сохраняются события: появление онлайн, начало маршрута, зомби, окончание маршрута, исчезание онлайн

Тестирование:
все города:
python coroutines/statusv.py DEBUG
один город (city.id=45):
python coroutines/statusv.py DEBUG=45

Запуск/остановка:
sudo supervisorctl start statusv
sudo supervisorctl stop statusv
Перезапуск после редактирования:
sudo supervisorctl restart statusv
Проверка состояния:
sudo supervisorctl status statusv
"""
from __future__ import absolute_import
from __future__ import print_function
from devinclude import *
from bustime.models import *
from bustime.views import *
import datetime
import gevent
import signal
import traceback
import six
from gevent import monkey
monkey.patch_socket()
from django.db.models import Subquery, OuterRef, Max
from django.forms.models import model_to_dict
"""
Сбор статистики о машинах города,
собираются и сохраняются события: появление онлайн, начало маршрута, зомби, окончание маршрута, исчезание онлайн

Тестирование:
все города:
python coroutines/statusv.py DEBUG
один город (city.id=45):
python coroutines/statusv.py DEBUG=45

Запуск/остановка:
sudo supervisorctl start statusv
sudo supervisorctl stop statusv
Перезапуск после редактирования:
sudo supervisorctl restart statusv
Проверка состояния:
sudo supervisorctl status statusv
"""
# через столько секунд машина считается отключившейся (данных нет по ней)
OFF_DATA_INTREVAL = 60 * 10
# кэш событий
VEHICLESTATUS = 'VehicleStatus'
VEHICLESTATUS_SAVE_INTERVAL = 3600
veh_events = {}
# кэш places
try:
    all_places = {p.id: p for p in Place.objects.filter(id__in=places_filtered())}
except:
    # TypeError: 'NoneType' object is not iterable if Place empty
    all_places = {}


def get_vehicles()->dict:
    vehicles_info = {}
    for v in Vehicle.objects.all():
        vehicles_info[v.uniqueid] = {
            'gosnum': v.gosnum,
            'bortnum': v.bortnum,
            'ramp': v.ramp,
            'model': v.model,
            'uid_provider': v.uid_provider,
            'created_auto': v.created_auto,
        }
    return vehicles_info
# get_vehicles


def get_vehicles_status()->dict:
    '''
    Для каждой машины выбрать последнее состояние (т.е. строку с максимальным event_time для uniqueid)
    Запрос:
    SELECT vs.*
    FROM bustime_vehiclestatus vs
    WHERE vs.event_time = (SELECT MAX(event_time)
                            FROM bustime_vehiclestatus
                            WHERE uniqueid = vs.uniqueid
                            AND city = vs.city)

    ORM (работает дольше, чем RAW):
    vehs = VehicleStatus.objects.filter(
        event_time=Subquery(
            VehicleStatus.objects.filter(
                uniqueid=OuterRef('uniqueid'),
                city=OuterRef('city')
            ).values('uniqueid', 'city').annotate(
                max_event_time=Max('event_time')
            ).values('max_event_time')
        )
    )
    '''

    """ долго работает
    vehs = VehicleStatus.objects.raw('''SELECT vs.*
            FROM bustime_vehiclestatus vs
            WHERE vs.event_time = (SELECT MAX(event_time)
                                    FROM bustime_vehiclestatus
                                    WHERE uniqueid = vs.uniqueid
                                    AND city = vs.city)''')
    """

    # запрос отрабатывает очень долго, так как данных много, по этому
    # будем результат сохранять в редис 4 раза в сутки
    # TODO: вообще отказаться от восстановления состояния машины
    cached_statuses = rcache_get(VEHICLESTATUS, {})
    if not cached_statuses:
        # этот быстрее
        db_statuses = VehicleStatus.objects.raw('''SELECT *
               FROM (
                   SELECT *,
                          ROW_NUMBER() OVER (PARTITION BY uniqueid, city ORDER BY event_time DESC) as rnum
                   FROM bustime_vehiclestatus
                   WHERE city IS NOT null
               ) subquery
               WHERE rnum = 1''')


        if db_statuses:
            for r in db_statuses:
                if r.city:
                    v = cached_statuses.get(r.uniqueid)
                    if not v:
                        v = {
                            'places': set(),
                            'status': r.status,
                            'bus_id': r.bus,
                            'endpoint': r.endpoint,
                            'gosnum': r.gosnum,
                            'zombie': r.zombie,
                            'sleeping': r.sleeping,
                            'away': r.away,
                            'custom': r.custom,
                            'event_time': r.event_time,
                        }

                    v['places'].add(r.city)
                    cached_statuses[r.uniqueid] = v
                # if r.city
            # for r in db_statuses
            rcache_set(VEHICLESTATUS, cached_statuses, VEHICLESTATUS_SAVE_INTERVAL)
        # if db_statuses
    # if not cached_statuses

    return cached_statuses
# get_vehicles_status


def Citymon(DEBUG=False):
    global veh_events

    # загружаем машины
    if DEBUG: print(f'get_vehicles')
    vehicles_info = get_vehicles()
    # и их текущее состояние
    if DEBUG: print(f'get_vehicles_status')
    veh_events = get_vehicles_status()

    while 1:
        statuses = []

        try:
            # события
            uids = REDIS.smembers("events")
            uids = list([x.decode('utf8') for x in uids])
            to_get = [f'event_{uid}' for uid in uids]
            allevents = rcache_mget(to_get)
            if DEBUG: print(f'{len(allevents) if allevents else 0} events')

            if allevents:
                for e in allevents:
                    if not e:
                        continue

                    '''
                    e={'uniqueid': '_r-VaEH6',
                      'timestamp': datetime.datetime(2024, 7, 9, 15, 51, 46),
                      'x': 20.44512,
                      'y': 54.6777733333333,
                      'gosnum': 'Р477УК',          # Vehicle.format_gosnum(e['gosnum']) / Vehicle.format_bortnum(e['label'])
                      'heading': 41,
                      'speed': 24,
                      'channel': 'askglonass',
                      'src': '4',
                      'uid_original': '4Q9PNDr-',
                      'uid_code': 2,
                      'ramp': True,
                      'x_prev': 20.4449983333333,
                      'y_prev': 54.6777,
                      'last_point_update': datetime.datetime(2024, 7, 9, 15, 51, 32),
                      'timestamp_prev': datetime.datetime(2024, 7, 9, 15, 51, 32),
                      'sleeping': False,
                      'last_changed': datetime.datetime(2024, 7, 9, 15, 49, 13),
                      'dchange': 500,
                      'blast_x': 20.44512,
                      'blast_y': 54.6777733333333,
                      'busstop_nearest': 2727750,
                      'away': False,
                      'direction': 0,
                      'nearest_name': 'Можайский пер.',
                      'nearest_order': 9,
                      'zombie': False,
                      'bus_id': 1383},
                    '''
                    uid = e['uniqueid']
                    created_auto = not bool(e.get('custom', False))

                    bus_id = e.get('bus_id', e.get('bus'))
                    if type(bus_id) == Bus:
                        bus = bus_id
                        bus_id = bus.id
                    elif type(bus_id) == int:
                        bus = bus_get(bus_id)
                    else:
                        bus = None

                    if bus:
                        places = [p.id for p in bus.places.all()]
                    else:
                        places = []

                    vinfo = vehicles_info.get(uid)
                    if not vinfo:   # uid нет в Vehicle, машина должна создаваться в update_lib_turbo.py::mill_event()
                        vinfo = {
                            'gosnum': e.get('gosnum'),
                            'bortnum': e.get('label'),
                            'ramp': e.get('ramp', False),
                            'model': e.get('model'),
                            'uid_provider': e.get('uid_original'),
                            'created_auto': created_auto,
                        }
                        vehicles_info[uid] = vinfo
                    # if not vinfo

                    v = veh_events.get(uid)

                    if v: # события машины есть
                        v['places'].update(places)
                        need_save = False

                        if e['timestamp'] > v['event_time']:    # есть новое событие от машины в allevents

                            # проверяем, изменилось ли что-нибудь
                            if v['status'] == 1:    # машина была offline
                                need_save = True
                                v['status'] = 0 # стала online

                            # маршрут
                            elif v['bus_id'] != bus_id:
                                need_save = True
                                if not v['bus_id'] and bus_id:   # появился маршрут
                                    v['status'] = 2
                                elif v['bus_id'] and not bus_id: # исчез маршрут:
                                    v['status'] = 3
                                    if DEBUG in v['places'] or DEBUG == True:
                                        print(f'e=', e)
                                    statuses += saveEvent(v, uid, DEBUG=DEBUG)   # сохраним событие для старого маршрута
                                elif v['bus_id'] and bus_id:     # изменился маршрут:
                                    v['status'] = 8
                                    if DEBUG in v['places'] or DEBUG == True:
                                        print(f'e=', e)
                                    statuses += saveEvent(v, uid, DEBUG=DEBUG)   # сохраним событие для старого маршрута
                                v['bus_id'] = bus_id

                            # статус зомби
                            elif 'zombie' in e and v['zombie'] != e['zombie']:
                                need_save = True
                                v['zombie'] = e['zombie']
                                v['status'] = 5

                            # статус away (Сошел с маршрута)
                            elif 'away' in e and v['away'] != e['away']:
                                need_save = True
                                v['away'] = e['away']
                                v['status'] = 7

                            # изменилась ли конечная
                            elif 'busstop_nearest' in e and 'nearest_order' in e:
                                if e['busstop_nearest'] and e['nearest_order'] == 0 and v['endpoint'] != e['busstop_nearest']:
                                    need_save = True
                                    v['endpoint'] = e['busstop_nearest']
                                    v['status'] = 4

                            # независимо от любых изменений сохраняем время последнего события машины
                            v['event_time'] = e.get('timestamp')
                            v['gosnum'] = e.get('gosnum')
                            v['custom'] = e.get('custom', False)

                            # что-то изменилось, сохраняем событие
                            if need_save:
                                if DEBUG in v['places'] or DEBUG == True:
                                    print(f'e=', e)
                                statuses += saveEvent(v, uid, DEBUG=DEBUG)
                            # if need_save

                        # if e['timestamp'] > v['event_time']
                    # if v
                    else:   # событий машины нет
                        veh_events[uid] = {
                            'places': set(),
                            'status': 0,    # Есть данные по ТС
                            'bus_id': bus_id,
                            'endpoint': e.get('busstop_nearest'),
                            'gosnum': e.get('gosnum'),
                            'zombie': e.get('zombie', False),
                            'sleeping': e.get('sleeping', False),
                            'away': e.get('away', False),
                            'custom': e.get('custom', False),
                            'event_time': e.get('timestamp')
                        }
                        veh_events[uid]['places'].update(places)
                        if DEBUG in veh_events[uid]['places'] or DEBUG == True:
                            print(f'e=', e)
                        statuses += saveEvent(veh_events[uid], uid, DEBUG=DEBUG)
                    # else if v and v['status'] != 1
                # for e in events
            # if allevents

            # проверяем отсутствие событий машины
            # т.е в словаре veh_events машина есть (значит, события были),
            # а в allevents событий для машинны нет
            # или есть, но со времени последнего события прошло более OFF_DATA_INTREVAL сек. (старое)
            # не забываем, что время любого последнего события машины хранится у нас в поле event_time
            for uid, v in veh_events.items():
                for pid in v['places']:
                    place = all_places.get(pid)
                    if place:
                        now = place.now
                        # v['status'] != 1 нужно чтобы не записывать это событие много раз в БД
                        if v['status'] != 1 and (now - v['event_time']).total_seconds() >= OFF_DATA_INTREVAL:   # нет событий
                            v['status'] = 1
                            # если машина исчезла вчера, а обнаружено это сегодня, то время ставим вчера, чтоб в журнале было правильно
                            v['event_time'] = v['event_time'] + datetime.timedelta(seconds = OFF_DATA_INTREVAL)
                            statuses += saveEvent(v, uid, DEBUG=DEBUG)
                            break # по всем остальным place пройдётся saveEvent
            # for v in veh_events.items()

            if statuses:
                if DEBUG: print(f'Save {len(statuses)} statuses')
                VehicleStatus.objects.bulk_create(statuses)

        except Exception as ex:
            if DEBUG: print(traceback.format_exc(limit=2))
            else: log_message(traceback.format_exc(limit=2), ttype="statusv.py", city=None)


        # 4 раза в сутки сохраняем текущее состояние машин
        if not rcache_get(VEHICLESTATUS, {}):
            rcache_set(VEHICLESTATUS, veh_events, VEHICLESTATUS_SAVE_INTERVAL)

        sleep_seconds = 10 if DEBUG else 60
        if DEBUG: print('daemon sleep %d' % (sleep_seconds))
        gevent.sleep(sleep_seconds)
    # while 1

    if DEBUG: print('Citymon terminated')
# def Citymon(city)

def saveEvent(ev, uid, DEBUG=False)->list:
    retval = []
    for pid in ev['places']:
        place = all_places.get(pid)
        if place:
            now = place.now
            gosnum = ev.get('gosnum')
            retval.append(
                VehicleStatus(
                    city = pid,
                    # если машина исчезла вчера, а обнаружено это сегодня, то время ставим вчера, чтоб в журнале было правильно
                    city_time = now if ev['status'] != 1 else ev.get('event_time', now),
                    status = ev['status'],
                    event_time = ev.get('event_time', now),
                    uniqueid = uid,
                    gosnum = gosnum[:16] if gosnum else gosnum,
                    bus = ev.get('bus_id'),
                    endpoint = ev['endpoint'],
                    zombie = ev['zombie'],
                    sleeping = ev['sleeping'],
                    away = ev['away']
                )
            )
            if DEBUG in ev['places'] or DEBUG == True:
                print('saveEvent:', model_to_dict(retval[-1]))
        # if place
    # for pid in ev['places']

    # если статус = 'Нет данных по ТС', то пусть в следующий раз ТС появляется в плейсах,
    # в которых реально работает, а не во всех, которых был когда-то
    if ev['status'] == 1:
        ev['places'].clear()
    return retval
# def saveEvent(ev, city)


def term_handler(DEBUG=False):
    if DEBUG: print("SIGTERM")
    global veh_events
    if veh_events:
        if DEBUG: print("Save statuses")
        rcache_set(VEHICLESTATUS, veh_events, 86400)    # здесь на сутки
    if DEBUG: print('EXIT')
    else: log_message('EXIT', ttype="statusv.py")
    sys.exit() # MUST BE!


if __name__ == '__main__':
    DEBUG = False
    if len(sys.argv) > 1:
        dbg = sys.argv[1].split('=')
        if dbg[0] == 'DEBUG':
            DEBUG = int(dbg[1]) if len(dbg) > 1 else True

    glist = []
    glist.append(gevent.spawn(Citymon, DEBUG))
    msg = "%s greenlets started" % len(glist)
    if DEBUG: print(msg)
    else: log_message(msg, ttype="statusv.py", city=None)

    gevent.signal_handler(signal.SIGTERM, term_handler, DEBUG)
    gevent.signal_handler(signal.SIGKILL, term_handler, DEBUG)
    gevent.signal_handler(signal.SIGINT, term_handler, DEBUG) # CTRL + C

    gevent.joinall(glist)

    if DEBUG: print('EXIT')
    else: log_message('EXIT', ttype="statusv.py")
