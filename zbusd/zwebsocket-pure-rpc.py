#!/usr/bin/env python
# -*- coding: utf-8 -*-
from devinclude import *
# from bustime.models import *

from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks
from twisted.internet.endpoints import serverFromString

from autobahn.wamp import types
from autobahn.twisted import wamp, websocket
import zmq
import zerorpc

PORT = 9002
RC = "tcp://127.0.0.1:9001"
C = zerorpc.Client

def rpc_bdata(*args, **kwargs):
    c = C()
    c.connect(RC)
    r = c.rpc_bdata(*args, **kwargs)
    c.close()
    return r


def rpc_bootstrap_amounts(*args, **kwargs):
    c = C()
    c.connect(RC)
    r = c.rpc_bootstrap_amounts(*args, **kwargs)
    c.close()
    return r


def rpc_passenger(*args, **kwargs):
    c = C()
    c.connect(RC)
    r = c.rpc_passenger(*args, **kwargs)
    c.close()
    return r


def rpc_tcard(*args, **kwargs):
    c = C()
    c.connect(RC)
    r = c.rpc_tcard(*args, **kwargs)
    c.close()
    return r

 
def rpc_stop_ids(ids):
    c = C()
    c.connect(RC)
    r = c.rpc_stop_ids(*args, **kwargs)
    c.close()
    return r


class MyBackendComponent(wamp.ApplicationSession):

    @inlineCallbacks
    def onJoin(self, details):
        # regs = []
        yield self.register(rpc_bdata, u'ru.bustime.rpc_bdata')
        yield self.register(rpc_passenger, u'ru.bustime.rpc_passenger')
        # mobile support only
        yield self.register(rpc_bootstrap_amounts,
                            u'ru.bustime.rpc_bootstrap_amounts')
        yield self.register(rpc_tcard, u'ru.bustime.rpc_tcard')
        yield self.register(rpc_stop_ids, u'ru.bustime.rpc_stop_ids')


def accept(offers):
    for offer in offers:
        if isinstance(offer, PerMessageDeflateOffer):
            return PerMessageDeflateOfferAccept(offer)

if __name__ == '__main__':
    router_factory = wamp.RouterFactory()
    session_factory = wamp.RouterSessionFactory(router_factory)
    component_config = types.ComponentConfig(realm="realm1")
    component_session = MyBackendComponent(component_config)
    session_factory.add(component_session)

    transport_factory = websocket.WampWebSocketServerFactory(session_factory,
                                                             debug=False,
                                                             debug_wamp=False)
    server = serverFromString(reactor, "tcp:%s" % PORT)
    server.listen(transport_factory)
    reactor.run()
