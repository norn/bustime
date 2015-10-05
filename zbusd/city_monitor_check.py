#!/usr/bin/env python
# -*- coding: utf-8 -*-

from devinclude import *
from bustime.models import *
from bustime.views import ajax_stop_id_f
import time
import random
import cPickle as pickle
try:
   import asyncio
except ImportError:
   import trollius as asyncio
from autobahn.asyncio import wamp, websocket
from autobahn.wamp import types
import zmq
import threading
# import gevent
# from zmq import green as zmq

import cProfile
import yappi

# Система Дождь

PORT = 9002
ZCONTEXT = zmq.Context()
ZCONTEXT.set(zmq.MAX_SOCKETS, 1023*5)

sock = ZCONTEXT.socket(zmq.SUB)
sock.connect(ZPUB)
sock.setsockopt(zmq.SUBSCRIBE, "city_monitor__%s " % 3)

while 1:
    print "listen"
    sr = sock.recv()
    b, sr = sr.split(' ', 1)
    # [now, sess, lon, lat, accuracy]
    data = pickle.loads(sr)
    now, sess, lon, lat, accuracy = data
    data = [now, lon, lat, accuracy]
    print data
    #exit()
