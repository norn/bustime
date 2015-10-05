#!/usr/bin/env python
# -*- coding: utf-8 -*-


from devinclude import *
from bustime.models import *
import socket
import zmq
import cPickle as pickle
import time
import base64

context = zmq.Context()
socket = context.socket(zmq.SUB)
socket.connect("tcp://127.0.0.1:15556")
#socket.connect("ipc://bustime_out")
#socket.connect("ipc://bustime_in")
#socket.setsockopt_string(zmq.SUBSCRIBE, u"")
socket.setsockopt(zmq.SUBSCRIBE, "")
#socket.setsockopt(zmq.SUBSCRIBE, "bdata_mode0")
#socket.setsockopt_string(zmq.SUBSCRIBE, u"busamounts_4")

while 1:
    sr = socket.recv()
    what, p = sr.split(' ', 1)
    p = pickle.loads(p)
    #p = pickle.loads(base64.b64decode(p))
    print what
    #print p
    print ""
