#!/usr/bin/env python
# -*- coding: utf-8 -*-

from devinclude import *
from bustime.models import *
from bustime.views import ajax_stop_id_f

import gevent
#from gevent import monkey; monkey.patch_socket()
from autobahn.asyncio import wamp, websocket
from autobahn.wamp import types
from zmq import green as zmq

try:
    import asyncio
except ImportError:
    import trollius as asyncio

STOPS={}
for r in Route.objects.all(): #select_related('busstop'):
    if STOPS.get(r.bus_id):
        STOPS[r.bus_id].append(r.busstop_id)
    else:
        STOPS[r.bus_id] = [r.busstop_id]

#
# Система Дождь
#

ZCONTEXT = zmq.Context()
ZCONTEXT.set(zmq.MAX_SOCKETS, 1023*5)
ZSUBGATE = "tcp://127.0.0.1:15557"

def pickle_dumps(x):
    return pickle.dumps(x, protocol=pickle.HIGHEST_PROTOCOL)

def magic_box(sproto, extra):
    sock = ZCONTEXT.socket(zmq.PUSH)
    sock.connect(ZSUBGATE)
    #gevent.sleep(0.001) # tcp min for 100% messages

    if sproto == "mode0_monitor":
        #print datetime.datetime.now(), "mon0"
        bus, bdata, updated = extra
        serialized = {"bdata_mode0": bdata}
        serialized["bdata_mode0"]['updated'] = updated
        serialized["bdata_mode0"]['bus_id'] = bus.id
        time_bst = REDIS.get("time_bst_%s" % bus.city_id)
        if time_bst:
            time_bst = pickle.loads(time_bst)
            serialized['time_bst'] = time_bst.get(bus.id, {})
        sock.send("ru.bustime.bus_mode0__%s %s" % (bus.id, pickle_dumps(serialized)))
        #sock.send_pyobj(obj, flags=0, protocol=2)
    elif sproto == "mode1_monitor":
        bus, tosend = extra
        sock.send("ru.bustime.bus_mode1__%s %s" % (bus.id, tosend))
    elif sproto == "modep_proto":
        bus, pdata = extra
        sock.send("ru.bustime.bus_mode0__%s %s" % (bus.id, pickle_dumps(pdata)))
    elif sproto == "amount_monitor":
        city, update = extra
        pi = pickle_dumps({"busamounts": update})
        sock.send("ru.bustime.bus_amounts__%s %s" % (city.id, pi))
    elif sproto == "stop_monitor":
        to_send = extra
        for nb, dataz in to_send:
             serialized = ajax_stop_id_f([nb], raw=True, data=dataz, single=True)
             pi = pickle_dumps(serialized)
             sock.send("ru.bustime.stop_id__%s %s" % (nb.id, pi))

    sock.close()
    return True

#
# ------------------------------- monitors -------------------------
#


def amount_monitor(city):
    last_amounts = None
    sock = ZCONTEXT.socket(zmq.SUB)
    sock.connect(ZPUB)
    sock.setsockopt(zmq.SUBSCRIBE, "busamounts_%s " % city.id)

    while 1:
        sr = sock.recv()
        b, sr = sr.split(' ', 1)
        amounts = pickle.loads(sr)
        update = {}
        if not last_amounts or not amounts:
            last_amounts = amounts
            continue
        for k, v in amounts.iteritems():
            if last_amounts.get(k) != v:
                if v == None:
                    update[k] = '-'
                else:
                    update[k] = v
        if update:
            #print city, len(amounts)
            # f=open('/tmp/abc.txt','a')
            # f.write("%s %s\n"%(city, len(amounts)))
            # f.close()
            magic_box("amount_monitor", [city, update])
            last_amounts = amounts

def mode0_monitor(bus):
        last_bdata0 = None
        sock = ZCONTEXT.socket(zmq.SUB)
        sock.connect(ZPUB)
        sock.setsockopt(zmq.SUBSCRIBE, "bdata_mode0_%s " % bus.id)

        while 1:
            sr = sock.recv()
            b, sr = sr.split(' ', 1)
            bdata0 = pickle.loads(sr)
            if bdata0 and bdata0.get('updated'):
                updated = str(bdata0['updated']).split('.')[0]
                updated = updated.split(" ")[1]
                if last_bdata0 and bdata0 and last_bdata0['l'] != bdata0['l']:
                    magic_box("mode0_monitor", [bus, bdata0, updated])
            elif bdata0 and bdata0.get('passenger'):
                magic_box("modep_proto", [bus, bdata0])
                continue
            last_bdata0 = bdata0

def mode1_monitor(bus):
        sock = ZCONTEXT.socket(zmq.SUB)
        sock.connect(ZPUB)
        sock.setsockopt(zmq.SUBSCRIBE, "bdata_mode1_%s " % bus.city_id)
        tosend_last = None

        while 1:
            sr = sock.recv()
            b, sr = sr.split(' ', 1)
            bdata_mode1 = pickle.loads(sr)
            tosend = {}
            for s in STOPS[bus.id]:
                zs = bdata_mode1.get(s, [])
                if zs:
                    tosend[s] = zs
            if tosend and tosend != tosend_last:
                pi = pickle_dumps({"bdata_mode1": tosend})
                REDIS.set("bdata_mode1_%s" % (bus.id), pi, ex=60*10)
                magic_box("mode1_monitor", [bus, pi])
                tosend_last = tosend


def stop_monitor(city, nstops):
        sock = ZCONTEXT.socket(zmq.SUB)
        sock.connect(ZPUB)
        sock.setsockopt(zmq.SUBSCRIBE, "bdata_mode3_%s " % city.id)
        last_bdata_mode3 = {}
        # nstops = list(NBusStop.objects.filter(city=city))
        while 1:
            sr = sock.recv()
            b, sr = sr.split(' ', 1)
            bdata_mode3 = pickle.loads(sr)
            to_send = []
            for nb in nstops:
                bnb = bdata_mode3.get(nb.id)
                if bnb and bnb != last_bdata_mode3.get(nb.id):
                    to_send.append([nb, bnb])
            magic_box("stop_monitor", to_send)
            last_bdata_mode3 = bdata_mode3


#
# ------------------------------- main -------------------------
#
if __name__ == '__main__':
    glist = []

    for b in Bus.objects.filter(active=True, city__active=True):
        glist.append(gevent.spawn(mode0_monitor, b))
        glist.append(gevent.spawn(mode1_monitor, b))

    for city in City.objects.filter(active=True):
        glist.append(gevent.spawn(amount_monitor, city))
        glist.append(gevent.spawn(stop_monitor, city, list(NBusStop.objects.filter(city=city))))
    gevent.joinall(glist)

    print "READY!"
    r = raw_input()
