#!/usr/bin/env python
# -*- coding: utf-8 -*-
from devinclude import *
from bustime.models import *
from bustime.views import ajax_stop_id_f
from bustime.views import bus_last_f
import ujson
import time
# import six

# from twisted.python import log
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks
from twisted.internet.endpoints import serverFromString

from autobahn.wamp import types
from autobahn.twisted import wamp, websocket
# from twisted.internet.endpoints import clientFromString
import cPickle as pickle
import zmq
# import cProfile
# import logging
# LOGGER = logging.getLogger(__name__)

PORT = 9002

context = zmq.Context()
sock = context.socket(zmq.PUB)
sock.connect(ZSUB)
#
# --------------------- RPCs -------------------------------
#


def rpc_bdata(bus_id, mode, mobile):
    serialized = {}
    if mode == 0:
        bus = bus_get(int(bus_id))
        if mobile:
            mobile = True
        else:
            mobile = False
        serialized = bus_last_f(bus, raw=True, mobile=mobile)
    elif mode == 1:
        time.sleep(0.25)  # dirty hack to avoid loading data before bus stops
        serialized = REDIS.get("bdata_mode1_%s" % bus_id)
        if serialized:
            serialized = pickle.loads(serialized)
        else:
            serialized = {}
    return serialized


def rpc_bootstrap_amounts(city_id):
    busamounts = cache.get("busamounts_%s" % city_id)
    serialized = {"busamounts": busamounts}
    return serialized


def rpc_passenger(what, bus_id, r_id):
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
    #magic_box(PassengerProtocol, [bus_id, bp])

    return {}

# class PassengerProtocol(wamp.ApplicationSession):
# @inlineCallbacks
#     def onJoin(self, details):
#         bus_id, bp = self.config.extra
#         self.publish(
#             "ru.bustime.bus_mode0__%s" % bus_id, {'passenger': bp})
#         self.disconnect()


def rpc_tcard(tcard_num):
    tcard_num = str(tcard_num)[:20]
    #tcard_num = "%016d" % int(tcard_num)
    # f=open('/tmp/ffbb','a')
    # f.write("%s\n"%tcard_num)
    # f.close()
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


def rpc_stop_ids(ids):
    ids = ujson.loads(ids)
    serialized = ajax_stop_id_f(ids, raw=True)
    return serialized


#
# end RPC
#


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
    # log.startLogging(sys.stdout)

    router_factory = wamp.RouterFactory()
    session_factory = wamp.RouterSessionFactory(router_factory)
    component_config = types.ComponentConfig(realm="realm1")
    component_session = MyBackendComponent(component_config)
    session_factory.add(component_session)
    # self.setProtocolOptions(perMessageCompressionAccept = accept)
    # factory.setProtocolOptions(autoPingInterval = 1, autoPingTimeout = 3, autoPingSize = 20)
    transport_factory = websocket.WampWebSocketServerFactory(session_factory,
                                                             debug=False,
                                                             debug_wamp=False)
    server = serverFromString(reactor, "tcp:%s" % PORT)
    server.listen(transport_factory)
    reactor.run()
