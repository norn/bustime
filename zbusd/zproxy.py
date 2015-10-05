#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading
import zmq
import time

ZSUB = "tcp://127.0.0.1:15555"
ZPUB = "tcp://127.0.0.1:15556"

class ZServer(threading.Thread):

    def run(self):
        ZCONTEXT = zmq.Context()
        xsub = ZCONTEXT.socket(zmq.XSUB)
        xsub.bind(ZSUB)
        xpub = ZCONTEXT.socket(zmq.XPUB)
        xpub.bind(ZPUB)
        zmq.proxy(xsub, xpub)

if __name__ == '__main__':
    f = ZServer()
    f.daemon = True
    f.start()

    while 1:
        time.sleep(1)
