#!/usr/bin/env python
# -*- coding: utf-8 -*-

from autobahn.asyncio import wamp, websocket
from autobahn.wamp import types

try:
    import asyncio
except ImportError:
    import trollius as asyncio


def magic_box(sproto, extra):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    component_config = types.ComponentConfig(realm="realm1", extra=extra)
    session_factory = wamp.ApplicationSessionFactory(config=component_config)
    session_factory.session = sproto
    transport_factory = websocket.WampWebSocketClientFactory(session_factory)
    coro = loop.create_connection(transport_factory, '127.0.0.1', 9002)
    loop.run_until_complete(coro)
    loop.run_forever()
    loop.close()
    return


class CommandProtocol(wamp.ApplicationSession):

    @asyncio.coroutine
    def onJoin(self, details):
        us_id, cmd, params = self.config.extra
        serialized = {"us_cmd": cmd, "params":params}
        channel = "ru.bustime.us__%s" % us_id
        if us_id == "public":
            channel = "ru.bustime.public"
        self.publish(channel, serialized)
        self.disconnect()

    def onDisconnect(self):
        asyncio.get_event_loop().stop()


def wsocket_cmd(us_id, cmd, params):
    magic_box(CommandProtocol, [us_id, cmd, params])
