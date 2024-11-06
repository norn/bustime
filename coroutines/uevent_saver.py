#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
sudo supervisorctl status uevent_saver
sudo supervisorctl restart uevent_saver
'''
from __future__ import absolute_import
from __future__ import print_function
from devinclude import *
import datetime
import time
import traceback
from enum import Enum
from bustime.models import *
from typing import Dict, Optional
from itertools import chain
from django.core.exceptions import ValidationError
from collections import namedtuple
import six
from django.db import transaction, connection, connections
from django import db
from bustime.utils import dictfetchall
import psycopg2
import psycopg2.extras

#DEBUG = False
DEBUG = True


def flog(s):
    f = open('/tmp/uevent_saver.log', 'a')
    f.write("%s\n" % s)
    f.close()
    if DEBUG: print(s)

def eval_bus_id(e:Dict[str, any]) -> int:
    return e['bus'].id if type(e['bus']) != int else e['bus']

if __name__ == '__main__':

    # двое суток вперёд достаточный интервал для любого часового пояса
    future_max = 3600 * 24 * 2

    while 1:
        t1 = datetime.datetime.now()
        blist = []

        # достаем все uid для которых будем записывать данные
        uids = REDIS.smembers("events")
        #uids = REDIS.smembers("place__3")
        uids = list([x.decode('utf8') for x in uids])
        to_get = [f'event_{uid}' for uid in uids]


        # получаем данные для этих uid
        data = rcache_mget(to_get)
        for d in data:
            if not d: continue
            timestamp = d['timestamp']
            if timestamp > t1 + datetime.timedelta(seconds=future_max):
                continue
            uniqueid = d['uniqueid']
            heading = d.get('heading', 0)
            speed = d.get('speed', 0)
            direction = int(d.get('direction') or 0)
            gosnum = d.get('gosnum', 0)
            ramp = bool(d.get('ramp', False))
            rampp = bool(d.get('rampp', False))
            custom = d.get('custom', False)
            if 'bus' in d:
                bus_id = eval_bus_id(d)
            elif 'bus_id' in d:
                bus_id = d['bus_id']
            else:
                continue
            channel = d.get('channel', 0)
            src = d.get('src', 0)
            x = d.get('x', 0.0)
            y = d.get('y', 0.0)

            blist.append([uniqueid, timestamp, heading, speed, direction, gosnum, ramp, rampp, custom, bus_id, channel, src, x, y])

        try:

            blist = list(blist)
            #if DEBUG: print(blist)
            with connections['bstore'].cursor() as cursor:
                psycopg2.extras.execute_values(cursor, '''
                    INSERT INTO bustime_uevent (
                        uniqueid, timestamp, heading, speed,
                        direction, gosnum, ramp, rampp, custom,
                        bus_id, channel, src, x, y
                    ) VALUES %s;''', (ue for ue in blist), page_size=10000)
        except:
            if DEBUG:
                print(traceback.format_exc())
                break
            else:
                msg = traceback.format_exc(limit=1)
                log_message(msg, ttype="uevent_saver")
        finally:
            db.connection.close()

        d = (datetime.datetime.now() - t1).total_seconds()
        cnt = len(blist)
        flog("%s: saved %s events in %s seconds" % (t1, cnt, int(d)))
        if d < 60:
            time.sleep(60-d)
    # while 1
