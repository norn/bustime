#!/usr/bin/env python
# -*- coding: utf-8 -*-
from devinclude import *
from bustime.models import *
from bustime.views import bus_last_f
from bustime.views import ajax_stop_id_f
import time
import ujson
import cPickle as pickle
import zerorpc
import zmq

PORT = 9001
context = zmq.Context()
sock = context.socket(zmq.PUB)
sock.connect(ZSUB)


class Gloria(object):

    def rpc_bdata(self, bus_id, mode, mobile):
        serialized = {}
        if mode == 0:
            bus = bus_get(int(bus_id))
            if mobile:
                mobile = True
            else:
                mobile = False
            serialized = bus_last_f(bus, raw=True, mobile=mobile)
        elif mode == 1:
            # dirty hack to avoid loading data before bus stops
            # time.sleep(0.25)
            serialized = REDIS.get("bdata_mode1_%s" % bus_id)
            if serialized:
                serialized = pickle.loads(serialized)
            else:
                serialized = {}
        return serialized

    def rpc_bootstrap_amounts(self, city_id):
        busamounts = cache.get("busamounts_%s" % city_id)
        serialized = {"busamounts": busamounts}
        return serialized

    def rpc_passenger(self, what, bus_id, r_id):
        r_id = int(r_id)
        bp = cache.get('bustime_passenger_%s' % bus_id, {})
        bp[r_id] = bp.get(r_id, 0)
        if what > 0:
            bp[r_id] += 1
        elif bp[r_id] > 0:
            bp[r_id] -= 1
        cache.set('bustime_passenger_%s' % bus_id, bp, 60 * 60)
        pi = pickle.dumps({'passenger': bp}, protocol=pickle.HIGHEST_PROTOCOL)
        sock.send("bdata_mode0_%s %s" % (str(bus_id), pi))

    def rpc_tcard(self, tcard_num):
        tcard_num = str(tcard_num)
        serialized = {}
        try:
            tcards = Tcard.objects.filter(num=tcard_num)
            # f.write("%s\n"%tcards)
            if not tcards:
                tcard = Tcard.objects.create(
                    num=tcard_num, updated=datetime.datetime(2014, 02, 11))
            else:
                tcard = tcards[0]
            tcard.update()
            serialized["balance"] = tcard.balance
            if tcard.social:
                s = 1
            else:
                s = 0
            serialized["social"] = s
            # f.write("%s\n"%serialized)
        except:
            tcard = None
        return serialized

    def rpc_stop_ids(self, ids):
        ids = ujson.loads(ids)
        serialized = ajax_stop_id_f(ids, raw=True)
        return serialized


s = zerorpc.Server(Gloria())
s.bind("tcp://127.0.0.1:%s" % PORT)
print "Love you. Gloria."
s.run()
