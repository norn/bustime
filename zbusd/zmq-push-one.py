#!/usr/bin/env python
# -*- coding: utf-8 -*-

import random, time
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks
from twisted.internet.endpoints import serverFromString

from autobahn.wamp import types
from autobahn.twisted import wamp, websocket
import cPickle as pickle
import zmq

context = zmq.Context()
sock = context.socket(zmq.PUB)
sock.connect("tcp://127.0.0.1:15557")
time.sleep(0.0005) # 0.001-0.0005

sr = {"busamounts":int(random.random()*100), "2":123}
sr = pickle.dumps(sr)
sock.send("ru.bustime.bus_amounts__3 %s"%sr)
print "done"
