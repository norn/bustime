#!/usr/bin/env python
# -*- coding: utf-8 -*-

from autobahn.twisted.wamp import ApplicationRunner
from autobahn.twisted.wamp import ApplicationSession
from autobahn.twisted.util import sleep
from txzmq import ZmqEndpoint, ZmqFactory, ZmqPullConnection, ZmqPushConnection #ZmqPubConnection, ZmqSubConnection
import datetime
import cPickle as pickle
import time

#
# ZMQ to Autobahn gate
#

# motherfuckers
#class nnZmqSubConnection(ZmqSubConnection):
#    def messageReceived(self, message):
#        self.gotMessage(message[0])


ZSUBGATE = "tcp://127.0.0.1:15557"
ZSUBGATE_SSL = "tcp://127.0.0.1:15559"
ZF = ZmqFactory()
ZFE = ZmqEndpoint("bind", ZSUBGATE)
ZFE_SSL = ZmqEndpoint("connect", ZSUBGATE_SSL)

class Component(ApplicationSession):
    def onJoin(self, details):
        s = ZmqPullConnection(ZF, ZFE)
        ss = ZmqPushConnection(ZF, ZFE_SSL )
        def go_pull(sr):
            ss.push(sr)
            chan, sr = sr[0].split(' ', 1)
            sr = pickle.loads(sr)
            #print chan
            #print chan, sr['bdata_mode0']['updated']
            self.publish(chan, sr)
        s.onPull = go_pull

if __name__ == '__main__':
    time.sleep(2) # for some reason it doesnt work after supervisor start
    runner = ApplicationRunner("ws://127.0.0.1:9002", "realm1")
    runner.run(Component)
