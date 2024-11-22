#!/usr/bin/env python

from devinclude import *
from bustime.models import *
from bustime.views import *
from bustime.update.krasnoyarsk_reschedule import update_krasnoyarsk_reschedule
from contextlib import closing
from psycopg2.extras import DictCursor
from django.core.serializers.json import DjangoJSONEncoder
import psycopg2
import random
import subprocess
import os
import time
import re
import psutil
import importlib
import json
import datetime
requests.packages.urllib3.disable_warnings()
import gevent
from gevent import monkey
monkey.patch_socket()
monkey.patch_ssl()
# print "PID=%s" % os.getpid()

# Zerg Bus version

def ScheduleUpdater(city):
    while 1:
        d = city.now
        if d.hour >= 1 and d.hour < 5:
            gevent.sleep(600)
            continue
        try:
            update_krasnoyarsk_reschedule()
        except:
            pass
        gevent.sleep(20)


def WeatherUpdaters():
    places = list(Place.objects.filter(id__in=places_filtered()))
    while True:
        for place in places:
            avg_temp = refresh_temperature(place)
            #print(place.name, avg_temp)
            gevent.sleep(1) # max 60/per minute
        now = datetime.datetime.now()
        seconds_until_next_hour = (60 - now.minute) * 60
        # sleeps for 2 hours longer to avoid current monthly api limit temporary! todo buy subscription?
        gevent.sleep(seconds_until_next_hour+60*60*2)


def BtcUpdater():
    while 1:
        get_btc(force=True)
        gevent.sleep(600)  # refresh each 10 minutes


def active_city_updater():
    # fill buses dict with resolved places
    def fill_b():
        Bfoo = {}
        for b in Bus.objects.all():
            b.all_places = list(b.places.all().values_list("id", flat=True))
            Bfoo[b.id] = b
        return Bfoo
    hour_prev = datetime.datetime.now().hour
    B = fill_b()

    while 1:
        uids = REDIS.smembers("events")
        uids = list([x.decode('utf8') for x in uids])
        to_get = [f'event_{uid}' for uid in uids]

        num = set()
        for e in rcache_mget(to_get):
            ev_id, uid = to_get.pop(0), uids.pop(0)
            if e and e.busstop_nearest and not e.zombie and not e.sleeping:
                if not B.get(e.bus_id):
                    # update B if bus not found
                    B = fill_b()
                if B.get(e.bus_id):
                    for place in B[e.bus_id].all_places:
                      num.add(place)

        sio_pub("ru.bustime.status_server", {"status_server": {"active_cities": len(num)}})
        # put to db here for per hour stats on /status/
        d = datetime.datetime.now()
        d = d.replace(second=0, microsecond=0)
        if d.hour != hour_prev:
            MetricTime.objects.create(date=d, name="active_cities", count=len(num))
            hour_prev = d.hour

        gevent.sleep(60*5)

def timedelta_converter(delta):
    if isinstance(delta, datetime.timedelta):
        return delta.total_seconds()


def redis_status_prepare():
    info = REDIS_W.info() # get real redis instance, not replica
    keys = ['connected_clients', 'used_memory_human', 'role',
    'connected_slaves', 'slave0', 'slave1', 'db0']
    a = {k: v for k, v in info.items() if k in keys}
    if "db0" in a:
        a["db0_keys"] = a["db0"]["keys"]
        del a["db0"]
    if "slave0" in a:
        a["slave0"] = "%s/%s/%s" % (a["slave0"]["ip"], a["slave0"]["state"], a["slave0"]["lag"])
    if "slave1" in a:
        a["slave0"] += "<br/>%s/%s/%s" % (a["slave1"]["ip"], a["slave1"]["state"], a["slave1"]["lag"])
        del a["slave1"]
    return a


def StatusServer():
    last = {}
    while 1:
        update = {}
        with open('/proc/uptime', 'r') as f:
            uptime_seconds = float(f.readline().split()[0])
            # uptime_string = str(datetime.timedelta(seconds = uptime_seconds)).split(' ')[0]
            uptime_days = datetime.timedelta(seconds=uptime_seconds).days
        with closing(psycopg2.connect(host='127.0.0.1', dbname='postgres', user='spectator', password='EikQdaE2PzJxAD')) as conn:
            with conn.cursor(cursor_factory=DictCursor) as cursor:
                cursor.execute("SELECT client_addr,state,write_lag,flush_lag,replay_lag FROM pg_catalog.pg_stat_replication;")
                result = [ [ data if not isinstance(data, datetime.timedelta) else data.total_seconds() for data in status ] for status in cursor.fetchall() ]
                update['stat_replication'] = result
        update['cpu'] = int(psutil.cpu_percent())
        update['mem'] = psutil.virtual_memory().percent
        update['uptime'] = uptime_days
        update['disk'] = psutil.disk_usage('/').percent
        update['pids'] = len(psutil.pids())
        update['ms_online'] = len(REDISU_IO.smembers("ms_online"))
        update['us_online'] = len(REDISU_IO.smembers("us_online"))
        update['redis'] = redis_status_prepare()
        rcache_set('status_server', update)
        if last:
            to_update = {}
            for k, v in update.items():
                if update[k] != last[k]:
                    to_update[k] = v
            last = copy.deepcopy(update)
            update = copy.deepcopy(to_update)
        else:
            last = copy.deepcopy(update)
        if update:
            sio_pub("ru.bustime.status_server", {"status_server": update})
            # {'mem': 29.2, 'uptime': '20 days, 13:40:22', 'cpu': 21.2}
        gevent.sleep(3)


def online_monitor(city, os):
    cnt_last = 0
    cnt_last_time = datetime.datetime.now()
    ps = REDISU_IO.pubsub()
    ch = "counter_online_%s_%s" % (city.id, os)
    ps.subscribe("__keyspace@0__:%s" % ch)
    chan = f"ru.bustime.counters__{city.id}"
    
    for sr in ps.listen():
        if sr['type'] == 'subscribe':
            continue
        cnt = REDIS_IO.get(ch)
        if not cnt:
            cnt = 0
        else:
            cnt = int(cnt)
        if cnt != cnt_last and cnt_last_time < datetime.datetime.now() - datetime.timedelta(seconds=3):
            data = {"counter_online_city_web": cnt} if os == "web" else {"counter_online_city_app": cnt}
            cnt_last = cnt
            cnt_last_time = datetime.datetime.now()
            sio_pub(chan, data)


if __name__ == '__main__':
    glist = [gevent.spawn(StatusServer),
             gevent.spawn(BtcUpdater),
             gevent.spawn(active_city_updater)]

    for k, city in CITY_MAP.items():
        if city.active:
            glist.append(gevent.spawn(online_monitor, city, "web"))
            glist.append(gevent.spawn(online_monitor, city, "app"))
            if city.id == 3:
                glist.append(gevent.spawn(ScheduleUpdater, city))

    glist.append(gevent.spawn(WeatherUpdaters))
    print(len(glist), 'threads')
    gevent.joinall(glist)
