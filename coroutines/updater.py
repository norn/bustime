#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Тестирование:
python coroutines/updater.py 107 --debug

рестарт всех:
sudo supervisorctl restart updaters:*
'''
from __future__ import absolute_import
from __future__ import print_function
from devinclude import *
from bustime.models import *
from bustime.views import *
import argparse
import importlib
import six
from django import db
import os
import psutil


def error_manager(city, now, result):
    cc_key = 'error_%s' % city.id
    error_update = rcache_get(cc_key, {})
    ff = error_update.get('lasts', [])
    ff.append(result)
    ff = ff[-10:]
    error_update['lasts'] = ff

    if result is True:
        if error_update.get('panic'):
            now_str = str(now).split('.')[0]
            wsocket_cmd('error_update', {'status':0, "tm":now_str}, channel="city__%s" % city.id)
            message = u"Соединение восстановлено"
            if city.__class__.__name__ == "City":
                log_message(message, ttype="error_update", city=city)
            elif city.__class__.__name__ == "Place":
                log_message(message, ttype="error_update", place=city)
            else:
                log_message(message, ttype="error_update")
            l = {"message":message, "date":six.text_type(city.now)[:-4]}
            sio_pub("ru.bustime.status__%s" % city.id, {'status_log': {'errors':[l]}})
            REDIS_W.publish('_bot_status', u"✅ %s: %s" % (message, city.name))
            error_update['panic'] = False
            error_update['last_error'] = None
        else:
            if city.__class__.__name__ == "City":
                error_update['good_time'] = now
                city = City.objects.get(id=city.id)  # fresh one
                city.good_time = city.now
                city.save(update_fields=['good_time'])
    else:
        if not [x for x in error_update['lasts'] if x == True] and not error_update.get('panic'):
            if not error_update.get('last_error'):
                error_update['last_error'] = now
            error_update['panic'] = True
            now_str = str(now).split('.')[0]
            wsocket_cmd('error_update', {'status':1, "tm":now_str}, channel="city__%s" % city.id)
            message = u"Ошибка соединения с сервером данных"
            if city.__class__.__name__ == "City":
                log_message(message, ttype="error_update", city=city)
            elif city.__class__.__name__ == "Place":
                log_message(message, ttype="error_update", place=city)
            else:
                log_message(message, ttype="error_update")
            l = {"message":message, "date":six.text_type(city.now)[:-4]}
            sio_pub("ru.bustime.status__%s" % city.id, {'status_log': {'errors':[l]}})
            REDIS_W.publish('_bot_status', u"⚠️ %s: %s" % (message, city.name))
            error_update['notified'] = now

    rcache_set(cc_key, error_update, 60*60*24)
    return error_update


def CityUpdater(city, DEBUG=False):
    #p = psutil.Process(os.getpid())

    def update():
        now = city.now
        if DEBUG: print("%s: call updater()" % now)
        
        message = {"state": CityUpdaterState.UPDATE.name.lower()}
        if DEBUG: print(f"ru.bustime.updater__{city.id}", {"updater": message})
        sio_pub(f"ru.bustime.updater__{city.id}", {"updater": message})

        try:
            result = updater(DEBUG=DEBUG)
        except:
            result = -1

        delta = (city.now-now).total_seconds()
        delta = round(delta, 2)
        if DEBUG: print("delta=%s" % delta)
        '''
        if delta > 10:
            with open('/tmp/updater_over.log', 'a') as f:
                f.write("%s: start=%s, dur=%s, res=%s\n" % (city.id, now, delta, result))
        '''
        # @locman сказал можно комментировать
        # if delta > 10:
            # log_message("Большое время получения данных (%s сек.)" % delta, ttype="coroutines/updater.py", city=city)

        log_counters = rcache_get('log_counters_%s' % city.id, {})
        nearest_for_select = log_counters.get('nearest', 0)
        sio_pub("ru.bustime.nearest_for_select", {'nearest_for_select': {city.id: nearest_for_select}})


        sio_pub("ru.bustime.select", {'zbusupd': {city.id: [delta, result]}})
        sio_pub("ru.bustime.status__%s" % city.id, {'status_counter': {'api_duration': delta}})

        if result == -1:
            error_manager(city, now, False)
        elif result is True:
            error_manager(city, now, True)
        # process info
        # https://pypi.org/project/psutil/
        '''
        res = {}
        tmp = p.cpu_times()
        res['cpu'] = "%.1f %%" % (tmp[0] + tmp[1])
        tmp = p.memory_info()
        res['mem'] = "%.1f MB" % (tmp[0] / 1048576.0)
        res['fds'] = "%d" % (p.num_fds())
        res['con'] = len(p.connections(kind='tcp'))
        res['thr'] = "%d" % (p.num_threads())

        sio_pub("ru.bustime.status__%s" % city.id, {'status_counter': {'api_duration': delta}, 'resources': res})
        '''
        db.connection.close()

    def idle(value):
        '''Do nothing except publish events about timeout next update.'''
        updater = {'state': CityUpdaterState.IDLE.name.lower(), 'timeout': value}
        if DEBUG: print(f"ru.bustime.updater__{city.id}", {"updater": updater})
        sio_pub(f"ru.bustime.updater__{city.id}", {"updater": updater})
        

    city_module = importlib.import_module('bustime.update.c{}'.format(city.id))
    updater = getattr(city_module,  'update')
    timesleep = 10  # default
    if city.id in [9, 18, 104]:
        timesleep = 20

    while 1:
        update()
        for i in range(timesleep - 1, 0, -1):
            idle(i)  # just publish countdown events to sio_pub
            time.sleep(1)
        # if DEBUG: print("sleep %s" % 1)
    # while 1
# CityUpdater


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Updater for muti-city.')
    parser.add_argument('city_id', metavar='N', type=int, help='city id')
    parser.add_argument("--debug", help="debug mode", action="store_true")
    args = parser.parse_args()
    city = CITY_MAP.get(args.city_id)
    if not city:
        city = Place.objects.filter(id=args.city_id).first()
    print('%s: Updater %s' % (datetime.datetime.now(), city.id))
    CityUpdater(city, DEBUG=args.debug)
