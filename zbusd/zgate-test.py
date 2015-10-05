#!/usr/bin/env python
# -*- coding: utf-8 -*-

from autobahn.twisted.wamp import ApplicationRunner
from autobahn.twisted.wamp import ApplicationSession
from autobahn.twisted.util import sleep
from txzmq import ZmqEndpoint, ZmqFactory, ZmqPullConnection #ZmqPubConnection, ZmqSubConnection
import datetime
import cPickle as pickle

#
# ZMQ to Autobahn gate
#

# motherfuckers
#class nnZmqSubConnection(ZmqSubConnection):
#    def messageReceived(self, message):
#        self.gotMessage(message[0])


ZSUBGATE = "tcp://127.0.0.1:15558"
ZF = ZmqFactory()
ZFE = ZmqEndpoint("bind", ZSUBGATE)

class Component(ApplicationSession):
    def onJoin(self, details):
        s = ZmqPullConnection(ZF, ZFE)
        def go_pull(sr):
            chan, sr = sr[0].split(' ', 1)
            sr = pickle.loads(sr)
            print chan
            #self.publish(chan, sr)
        s.onPull = go_pull

if __name__ == '__main__':
    runner = ApplicationRunner("ws://127.0.0.1:9002", "realm1")
    runner.run(Component)
