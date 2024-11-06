#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Готовит данные о "пробках" для utils/jam_daily.py

Тест:
python coroutines/jam.py DEBUG

Управление:
sudo supervisorctl status jam
sudo supervisorctl restart jam
sudo supervisorctl stop jam
sudo supervisorctl start jam
'''
from __future__ import absolute_import
from devinclude import *
from bustime.views import *
import traceback
import gevent
import time

ROUTE_PAIRS = {}
SLEEP_TIME = 5 * 60

def JamCalculator(city, DEBUG=False):
    def clamp(num, min_value, max_value):
        return max(min(num, max_value), min_value)

    def is_pair(key):
        if key in ROUTE_PAIRS:
            pair = ROUTE_PAIRS.get(key)
        else:
            stop_from, stop_to = key.split('_')
            pair = route_test_stops_pair(city, int(stop_from), int(stop_to), DEBUG)
            # if DEBUG: print("NOT IN PAIR %s" % pair)
            ROUTE_PAIRS[key] = pair
        return pair

    def create(k, v, dailies):
        if DEBUG: print(k, v)
        timings = v
        stop_from, stop_to = k.split('_')
        # if DEBUG: print("in_pair")
        average_time = sum(timings) / len(timings)
        # jams = Jam.objects.filter(busstop_from_id=stop_from, busstop_to_id=stop_to)
        # average_times = [] if not jams else [x.average_time for x in jams]
        # average_times.append(average_time)
        # min_time = min(average_times)
        # max_time = max(average_times)
        # diff_time = max_time - min_time
        # ratio = (average_time - min_time) / diff_time if diff_time else 0
        # prev_date = current_time - datetime.timedelta(days=1)

        # dailies = JamDaily.objects.filter(busstop_from=stop_from, busstop_to=stop_to, date=prev_date.date())
        # dailies = get_jam_daily_map()
        jam_daily = dailies.get(k)
        if not dailies or not jam_daily:
            ratio = None
        else:
            # daily = dailies.first()
            daily = JamDaily(**jam_daily)
            diff_time = daily.max_time - daily.min_time
            ratio = int(9.0 * clamp((average_time - daily.min_time) / diff_time, 0.0, 1.0) if diff_time else 0.0)
        if DEBUG: print("%s: %s -> %s (%s secs) %s" % (current_time, stop_from, stop_to, average_time, ratio))
        return Jam(create_time=current_time,
                   average_time=average_time,
                   busstop_from=stop_from,
                   busstop_to=stop_to,
                   ratio=ratio)

    def get_avg_ratio(jams):
        if not jams:
            return 0
        total_ratio = sum(jam_info[3] or 0 for jam_info in jams if len(jam_info) > 3)
        avg_ratio = round(total_ratio / len(jams))
        return avg_ratio

    def get_jam_daily_map():
        jam_daily_map = rcache_get(f"jam_daily__{city.id}", {})
        if not jam_daily_map:
            # Время завтрашнего дня
            tomorrow_time = datetime.datetime.combine(city.now.date() + datetime.timedelta(days=1),
                                                      datetime.datetime.min.time())
            # Через сколько времени кэш должен очиститься
            expire_time = tomorrow_time - city.now
            # Забираем вчерашние JamDaily для города и кэшируем в Редис
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT bj.id, bj.busstop_from, bj.busstop_to, bj.date, bj.min_time, bj.max_time "
                    "FROM bustime_jamdaily bj "
                    "INNER JOIN bustime_nbusstop bn ON bj.busstop_from = bn.id "
                    "WHERE bj.date = DATE(%s - INTERVAL '1 day') AND "
                    "bn.city_id = %s;", (city.now.date(), city.id))
                columns = [col[0] for col in cursor.description]
                jam_daily_map = {f"{row[1]}_{row[2]}": dict(zip(columns, row)) for row in cursor.fetchall()}
                rcache_set(f"jam_daily__{city.id}", jam_daily_map, expire_time)
        return jam_daily_map

    while 1:
        try:
            cc_key = "jam__%s" % city.id
            timers = rcache_get("timer_bst_%s" % city.id)
            current_time = city.now

            jams, rjams = [], []
            if timers:
                dailies = get_jam_daily_map()
                for k, v in timers.items():
                    # if is_pair(k):  # В windmill все остановки парные, поэтому эта проверка не нужна
                    jam = create(k, v, dailies)
                    jams.append(jam)
                    rjams.append([jam.busstop_from, jam.busstop_to, jam.average_time, jam.ratio])
                rcache_set(cc_key, rjams)
                Jam.objects.bulk_create(jams)
                avg_ratio_key = "avg_jam_ratio__%s" % city.id
                avg_ratio = get_avg_ratio(rjams) + 1
                rcache_set(avg_ratio_key, avg_ratio)
                # with open('/tmp/jams.log', 'a') as f:
                #     f.write("City [%s] Jams count [%s] processed for [%s]\n" %
                #         (city.name, len(jams), city.now - current_time))
                if DEBUG: print("City [%s] Jams count [%s] processed for [%s]" % (city.name, len(jams),
                                                                                  city.now - current_time))
            else:
                if DEBUG: print("%s: timer_bst_%s is None" % (city.name, city.id))
                #else: log_message("timer_bst_%s is None" % city.id, ttype="jam.py", city=city)
        except Exception as e:
            if DEBUG: print("%s: %s" % (city.name, traceback.format_exc()))
            else: log_message(traceback.format_exc(), ttype="jam.py", city=city)
        time.sleep(SLEEP_TIME)

"""
Проверяет пару остановок на предмет:
существует ли маршрут, в котором эти остановки одна за другой в одном направлении
"""
def route_test_stops_pair(city, stop_id1, stop_id2, DEBUG):
    buses = buses_get(city)
    for bus in buses:
        #if DEBUG: print(bus.id, bus.name)
        cc_key = "qroute_%s" % (bus.id)
        busroutes = cache.get(cc_key)
        if not busroutes:
            busroutes = list(Route.objects.filter(bus=bus).order_by('direction', 'order'))
            cache.set(cc_key, busroutes)

        l = len(busroutes)
        for i in range(0, l):
            if busroutes[i].busstop_id not in [stop_id1, stop_id2]:
                continue

            if busroutes[i].busstop_id == stop_id1:
                id2 = stop_id2
            else:
                id2 = stop_id1

            if i > 0:   # есть предыдущая остановка
                if busroutes[i-1].busstop_id == id2 and busroutes[i-1].direction == busroutes[i].direction:
                    #if DEBUG: print(bus.name, busroutes[i], busroutes[i-1])
                    return True
                elif i + 1 < l:
                    if busroutes[i + 1].busstop_id == id2 and busroutes[i].direction == busroutes[i + 1].direction:
                        #if DEBUG: print(bus.name, busroutes[i], busroutes[i+1])
                        return True
    return False
# route_test_stops_pair

if __name__ == '__main__':
    DEBUG = 'DEBUG' in sys.argv
    # JamCalculator(CITY_MAP[3], True)
    glist = []
    for city in City.objects.filter(active=True).order_by("id"):
        glist.append(gevent.spawn(JamCalculator, city, DEBUG))
        if DEBUG: break
    gevent.joinall(glist)
