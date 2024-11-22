#!/usr/bin/env python
# -*- coding: utf-8 -*-

from devinclude import *
from bustime.models import *
from collections import defaultdict
import datetime
"""
Тестирование:
python coroutines/statusd.py debug

Проверка состояния:
sudo supervisorctl status statusd

Перезапуск после редактирования:
sudo supervisorctl restart statusd
"""

def fresh_bus_places(DEBUG=False):
    if DEBUG: print("fresh_bus_places:", end=" ", flush=True)
    bus_places = {}
    for b in Bus.objects.filter(active=True):
        primary_place = b.places.order_by("-population").first()
        if primary_place:
            bus_places[b.id] = primary_place.id
    if DEBUG: print(len(bus_places), flush=True)
    return bus_places
# fresh_bus_places


def smon(DEBUG=False):
    bus_places = {}
    fresh_bus_places_counter = 0

    while 1:
        t1 = datetime.datetime.now()

        if fresh_bus_places_counter == 0:
            bus_places = fresh_bus_places(DEBUG)
            fresh_bus_places_counter = 10
        else:
            fresh_bus_places_counter -= 1

        uids = REDIS.smembers("events")
        if DEBUG: print("uids:", len(uids), flush=True)
        uids = list([x.decode('utf8') for x in uids])
        to_get = [f'event_{uid}' for uid in uids]
        allevents = rcache_mget(to_get)

        #log_counters = rcache_get('log_counters_%s' % city.id, {})

        all_places = places_get("ru")   # models.py, also: PLACE_MAP

        work_places = {}
        work_datasources = {}
        for e in allevents:
            if not e or not e.bus: continue
            if e.get('busstop_nearest') and not e.get('zombie') and not e.get('sleeping'):

                if type(e.bus) != int:
                    bus_id = e.bus.id
                else:
                    bus_id = e.bus
                bus_place_id = bus_places.get(bus_id, 0)
                #if bus_place_id == 0:
                #    fresh_bus_places_counter -= 1
                bus_place = all_places.get(bus_place_id)
                if bus_place:
                    d = bus_place.now - e.timestamp
                    """
                    Дата опрережает текущую
                    bus_place.now= 2024-03-21 09:20:36.323052
                    e= {'uniqueid': '_GPkSlwp', 'timestamp': datetime.datetime(2029, 5, 22, 6, 13, 49), 'bus_id': 4627, ...}
                    d= -1888 days, 3:06:47.323045
                    d.total_seconds()= -163111992.676955
                    d.seconds= 11207
                    """
                    if d.total_seconds() < 0:
                        continue

                    """
                    Почему используется d.seconds, а не d.total_seconds()
                    При разнице во времени более суток d.seconds = 0, а d.total_seconds() = число секунд хоть за месяц
                    Но, в данных часто присылаются машины с датами, отстающими от текущей на несколько дней:
                        d.seconds = 0, а d.total_seconds() = 3600 * 24 * дни
                    или часов:
                        d.seconds = d.total_seconds() = 3600 * часы
                    Это означает, что либо с машиной, либо с источником неполадки.
                    Но такие данные не должны влиять на все остальные за счет огромного кол-ва секунд в разнице.
                    В мельнице отбрасываются данные, устаревшие на 15 минут:
                        timestamp < now - datetime.timedelta(seconds=15*60)
                    Но, если и здесь отбросить такие данные, сложнее будет определить причины отсутствия машин
                    при наличии самих данных.
                    Поэтому отбросим данные, устаревшие на сутки и более.
                    """
                    if d.total_seconds() >= 86400:   # 3600 * 24
                        continue

                    if bus_place_id not in work_places:
                        work_places[bus_place_id] = []
                    work_places[bus_place_id].append(d.seconds)

                    ds = DataSource.objects.filter(channel=e.channel, src=e.src).first()
                    if ds:
                        if ds.id not in work_datasources:
                            work_datasources[ds.id] = {"nearest": 0, "delay_avg": []}
                        work_datasources[ds.id]["nearest"] += 1
                        work_datasources[ds.id]["delay_avg"].append(d.seconds)
                elif DEBUG:
                    print(f'Place id {bus_place_id} not found')
        # for e in allevents

        for ds_id, values in work_datasources.items():
            if values["nearest"] > 0:
                delay_avg = round(sum(values["delay_avg"])/values["nearest"], 2)
            else:
                delay_avg = 0
            if DEBUG: print(f'{ds_id}: delay_avg={delay_avg}, nearest={values["nearest"]}')
            DataSourceStatus.objects.create(
                ctime=datetime.datetime.now(),
                datasource_id=ds_id,
                nearest=values["nearest"],
                delay_avg=delay_avg)
        # for ds_id, values in work_datasources.items()

        for place_id, delays in work_places.items():
            cnt = len(delays)
            if cnt > 0:
                delay_avg = round(sum(delays)/cnt, 2)
                if DEBUG: print(f'{place_id}: delay_avg={delay_avg}')
                rcache_set("delay_avg_%s" % place_id, delay_avg)
        # for place_id, delays in work_places.items()

        # sleep
        t2 = datetime.datetime.now()
        etime = (t2 - t1).total_seconds()
        if DEBUG: print(f"{etime}s. Now sleeping for", 60-etime)
        time.sleep(60-etime)
# smon


if __name__ == '__main__':
    DEBUG = 'debug' in sys.argv
    smon(DEBUG=DEBUG)