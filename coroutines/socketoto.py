#!/usr/bin/env python
from devinclude import *
import json
import argparse
import logging
import typing
import pickle

import asyncio
import engineio
import six
import uvicorn
import socketio
import aioredis
import operator
from socketio import packet as socketio_packet
from socketio import exceptions as socketio_exceptions
from engineio import packet as engineio_packet, asyncio_socket
from engineio import exceptions as engineio_exceptions
from functools import wraps, partial
from asgiref.sync import sync_to_async
from django.conf import settings
from coroutines.rpc_server import Gloria

# logging.basicConfig(
#     level=logging.NOTSET,
#     format="%(asctime)-15s %(levelname)-8s %(message)s"
# )
# logging.getLogger(__name__)

logger = logging.getLogger("socketoto")


class BustimeAsyncServer(socketio.AsyncServer):

    def __init__(self, client_manager=None, logger=None, json=None,
                 async_handlers=True, **kwargs):
        self.redis: typing.Optional[aioredis.Redis] = None
        self.gloria: Gloria = Gloria()
        super().__init__(client_manager=client_manager, logger=logger, 
                         json=json, async_handlers=async_handlers, **kwargs)

    def _engineio_server_class(self):
        return BustimeEngineIOAsyncServer

    # async def _emit_internal(self, sid, event, data, namespace=None, id=None):
    #     logger.debug(f"__EMIT_INTERNAL__ {event} {data}")
    #     await super()._emit_internal(sid, event, data, namespace, id)


class BustimeEngineIOAsyncServer(engineio.AsyncServer):
    is_mobile = False
    
    async def send(self, sid, data, binary=None):
        await super(BustimeEngineIOAsyncServer, self).send(sid, data, binary)

    async def _handle_connect(self, environ, transport, b64=False,
                              jsonp_index=None):
        """Handle a client connection request."""
        if self.start_service_task:
            # start the service task to monitor connected clients
            self.start_service_task = False
            self.start_background_task(self._service_task)

        sid = self._generate_id()
        if not self.is_mobile:
            s = asyncio_socket.AsyncSocket(self, sid)
        else:
            s = BustimeAsyncSocket(self, sid)
        self.sockets[sid] = s

        pkt = engineio_packet.Packet(
            engineio_packet.OPEN, {'sid': sid,
                          'upgrades': self._upgrades(sid, transport),
                          'pingTimeout': int(self.ping_timeout * 1000),
                          'pingInterval': int(self.ping_interval * 1000)})
        await s.send(pkt)

        ret = await self._trigger_event('connect', sid, environ,
                                        run_async=False)
        if ret is not None and ret is not True:
            del self.sockets[sid]
            self.logger.warning('Application rejected connection')
            return self._unauthorized(ret or None)

        if transport == 'websocket':
            ret = await s.handle_get_request(environ)
            if s.closed and sid in self.sockets:
                # websocket connection ended, so we are done
                del self.sockets[sid]
            return ret
        else:
            s.connected = True
            headers = None
            if self.cookie:
                if isinstance(self.cookie, dict):
                    headers = [(
                        'Set-Cookie',
                        self._generate_sid_cookie(sid, self.cookie)
                    )]
                else:
                    headers = [(
                        'Set-Cookie',
                        self._generate_sid_cookie(sid, {
                            'name': self.cookie, 'path': '/', 'SameSite': 'Lax'
                        })
                    )]
            try:
                return self._ok(await s.poll(), headers=headers, b64=b64,
                                jsonp_index=jsonp_index)
            except engineio_exceptions.QueueEmpty:
                return self._bad_request()


class BustimeAsyncSocket(asyncio_socket.AsyncSocket):
    
    async def _websocket_handler(self, ws):
        """Engine.IO handler for websocket transport."""
        if self.connected:
            # the socket was already connected, so this is an upgrade
            self.upgrading = True  # hold packet sends during the upgrade

            # try:
            #     pkt = await ws.wait()
            # except IOError:  # pragma: no cover
            #     return
            # decoded_pkt = engineio_packet.Packet(encoded_packet=pkt)
            # logger.info(f"DECODED_PKT: {decoded_pkt.packet_type} {decoded_pkt.data}")
            # if decoded_pkt.packet_type != engineio_packet.PING or \
            #         decoded_pkt.data != 'probe':
            #     self.server.logger.info("DATA {}".format(decoded_pkt.data))
            #     self.server.logger.warning(
            #         '%s: Failed websocket upgrade, no PING packet', self.sid)
            #     self.upgrading = False
            #     return

            # await ws.send(engineio_packet.Packet(
            #     engineio_packet.PONG,
            #     data=six.text_type('probe')).encode(always_bytes=False))
            await self.queue.put(engineio_packet.Packet(engineio_packet.NOOP))  # end poll

            try:
                pkt = await ws.wait()
            except IOError:  # pragma: no cover
                self.upgrading = False
                return
            decoded_pkt = engineio_packet.Packet(encoded_packet=pkt)
            if decoded_pkt.packet_type != engineio_packet.UPGRADE:
                self.upgraded = False
                self.server.logger.info(
                    ('%s: Failed websocket upgrade, expected UPGRADE packet, '
                     'received %s instead.'),
                    self.sid, pkt)
                self.upgrading = False
                return
            self.upgraded = True
            self.upgrading = False
        else:
            self.connected = True
            self.upgraded = True

        # start separate writer thread
        async def writer():
            while True:
                packets = None
                try:
                    packets = await self.poll()
                except engineio_exceptions.QueueEmpty:
                    break
                if not packets:
                    # empty packet list returned -> connection closed
                    break
                try:
                    for pkt in packets:
                        await ws.send(pkt.encode(always_bytes=False))
                except:
                    break
        writer_task = asyncio.ensure_future(writer())

        self.server.logger.info(
            '%s: Upgrade to websocket successful', self.sid)

        # Send CONNECT Message again (Workaround for C++ mobile app)
        await ws.send(engineio_packet.Packet(engineio_packet.MESSAGE, data=0, binary=False).encode(always_bytes=True))

        while True:
            p = None
            wait_task = asyncio.ensure_future(ws.wait())
            try:
                p = await asyncio.wait_for(wait_task, self.server.ping_timeout)
            except asyncio.CancelledError:  # pragma: no cover
                # there is a bug (https://bugs.python.org/issue30508) in
                # asyncio that causes a "Task exception never retrieved" error
                # to appear when wait_task raises an exception before it gets
                # cancelled. Calling wait_task.exception() prevents the error
                # from being issued in Python 3.6, but causes other errors in
                # other versions, so we run it with all errors suppressed and
                # hope for the best.
                try:
                    wait_task.exception()
                except:
                    pass
                break
            except:
                break
            if p is None:
                # connection closed by client
                break
            if isinstance(p, six.text_type):  # pragma: no cover
                p = p.encode('utf-8')
            pkt = engineio_packet.Packet(encoded_packet=p)
            try:
                await self.receive(pkt)
            except engineio_exceptions.UnknownPacketError:  # pragma: no cover
                pass
            except engineio_exceptions.SocketIsClosedError:  # pragma: no cover
                self.server.logger.info('Receive error -- socket is closed')
                break
            except:  # pragma: no cover
                # if we get an unexpected exception we log the error and exit
                # the connection properly
                self.server.logger.exception('Unknown receive error')

        await self.queue.put(None)  # unlock the writer task so it can exit
        await asyncio.wait_for(writer_task, timeout=None)
        await self.close(wait=False, abort=True)

    # async def check_ping_timeout(self):
    #     """Make sure the client is still sending pings.

    #     This helps detect disconnections for long-polling clients.
    #     """
    #     if self.closed:
    #         raise engineio_exceptions.SocketIsClosedError()
    #     "Not send close packet by Timeout"
    #     return True
    


class AsyncReplicatedRedisManager(socketio.AsyncRedisManager):

    def __init__(self,
                 url_sub='redis://localhost:6379/',
                 url_pub='redis://localhost:6379/',
                 channel='socketio', logger=None):
        super().__init__(url=url_sub, channel=channel, write_only=False, logger=logger)
        (self.host_w, self.port_w, self.password_w, self.db_w, self.ssl_w) = \
            socketio.asyncio_redis_manager._parse_redis_url(url_pub)

    # def enter_room(self, sid, namespace, room):
    #     super(AsyncReplicatedRedisManager, self).enter_room(sid, namespace, room)

    # async def _thread(self):
    #     await super(AsyncReplicatedRedisManager, self)._thread()

    async def _publish(self, data):
        retry = True
        while True:
            try:
                if self.pub is None:
                    self.pub = await aioredis.create_redis(
                        (self.host_w, self.port_w), db=self.db_w,
                        password=self.password_w, ssl=self.ssl_w
                    )
                return await self.pub.publish(self.channel,
                                              pickle.dumps(data))
            except (aioredis.RedisError, OSError):
                if retry:
                    self._get_logger().error('Cannot publish to redis... '
                                             'retrying')
                    self.pub = None
                    retry = False
                else:
                    self._get_logger().error('Cannot publish to redis... '
                                             'giving up')
                    break


background_task_started = True
scheme = "http" if os.environ.get('SOCKETOTO_HTTP') else "https"
manager = AsyncReplicatedRedisManager(
    url_sub=f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}",
    url_pub=f"redis://{settings.REDIS_HOST_W}:{settings.REDIS_PORT_W}",
    # channel=f"socket.io#/#",
    channel="socketio",
    logger=logging.getLogger("socketio"))
sio = BustimeAsyncServer(client_manager=manager, async_mode='asgi',
                         logger=logger, engineio_logger=logger, ping_interval=300, 
                         cors_allowed_origins="*")


async def on_startup() -> None:
    logger.debug(f"Creating connection to redis://{settings.REDIS_HOST_W}:{settings.REDIS_PORT_W}")
    sio.redis = await aioredis.create_redis(f"redis://{settings.REDIS_HOST_W}:{settings.REDIS_PORT_W}")


async def on_shutdown() -> None:
    logger.debug("Disconnecting from Redis")
    sio.redis.close()


def user_settings(func=None, *, repack_to=None):
    if func is None:
        return partial(user_settings, repack_to=repack_to)

    @wraps(func)
    async def wrapper(sid, data):
        if repack_to:
            data = {repack_to: data}
        async with sio.session(sid) as session:
            os = session["os"] or "web"
            uid = session["uid"]
        if uid:
            if os != "web":
                data["ms_id"] = uid
            else:
                data["us_id"] = uid
        return await func(sid, data)

    return wrapper


def json_decode(func):
    @wraps(func)
    async def wrapper(sid, data):
        if isinstance(data, str):
            data = json.loads(data)
        return await func(sid, data)
    return wrapper


async def background_task():
    """Example of how to send server generated events to clients."""
    count = 0
    while True:
        await sio.sleep(10)
        count += 1
        await sio.emit('my_response', {'data': 'Server generated event'},
                       room="ru.bustime.taxi__4")


def update_online(city_id: int, os: str) -> None:
    if os == "web":
        rooms = sio.manager.rooms.get(f"cnt_online_{city_id}_web", [])
        sio.redis.set(f"counter_online_{city_id}_web", len(rooms), expire=60 * 60)
    elif os == "android" or os == "ios":
        rooms = sio.manager.rooms.get(f"cnt_online_{city_id}_app", [])
        sio.redis.set(f"counter_online_{city_id}_app", len(rooms), expire=60 * 60)
    else:
        logger.warning("Unknown OS")
    rooms = sio.manager.rooms.get(f"ru.bustime.bus_amounts__{city_id}", [])
    sio.redis.set(f"counter_online__{city_id}", len(rooms), expire=60 * 60)


async def update_online_chat(room: str) -> None:
    rooms = sio.manager.rooms.get(room, [])
    rooms_count = len(rooms)
    await sio.redis.set(f"{room}_cnt", rooms_count, expire=60 * 60)
    bus_id = int(room.split("__")[1])
    await sio.emit(event="", data={"chat_online": {"online": rooms_count, "bus_id": bus_id}}, room=room)


@sio.event
async def connect(sid: str, environ: dict) -> None:
    global background_task_started
    if not background_task_started:
        sio.start_background_task(background_task)
        background_task_started = True
    logger.info(f"connect: {sid}, {environ}")
    headers = environ.get('asgi.scope', {}).get('headers', {})
    client_ip = next(filter(lambda x: x[0] == b'x-forwarded-for', headers), None)
    if client_ip:
        sio.eio.client_ip = client_ip[1].decode('utf8')
    async with sio.session(sid) as session:
        session["headers"] = headers
    # await sio.emit(event="connect", to=sid)


@sio.event
async def disconnect(sid: str) -> None:
    logger.info(f"disconnect: {sid}")
    async with sio.session(sid) as session:
        logger.info(f"Session {session}")
        os = session.get("os")
        uid = session.get("uid")
        city_id = session.get("city_id")
        chat_room = session.get("chat_room")
    if uid:
        if os != "web":
            sio.redis.srem("ms_online", uid)
            sio.redis.srem(f"ms_online_{os}", uid)
        else:
            sio.redis.srem("us_online", uid)
        if city_id:
            update_online(city_id, os)
        if chat_room:
            await update_online_chat(chat_room)


@sio.event
@json_decode
async def authentication(sid: str, data: dict) -> None:
    logger.info(f"authentication: [{sid}], {data}")
    uid = data.get('username')
    if not uid: uid = sio.eio.client_ip
    os = data.get('os')
    # password = data.get('password')
    async with sio.session(sid) as session:
        session["os"] = os
        session["uid"] = uid
    if os != "web":
        uid_chan = f"ru.bustime.ms__{uid}"
        sio.enter_room(sid=sid, room=uid_chan)
        await sio.emit(event="auth", data={"auth": 1}, room=uid_chan)
        sio.redis.sadd(f"ms_online_{os}", uid)
        sio.redis.sadd("ms_online", uid)
    else:
        sio.redis.sadd("us_online", uid)
    await sio.send(data={"authentication": data}, to=sid)


@sio.event
async def join(sid: str, room: str) -> None:
    if not room:
        logger.warning("Join to undefined room?")
        return

    logger.info(f"join: {sid} to {room}")
    sio.enter_room(sid=sid, room=room)
    await sio.send(data={"join": room}, to=sid)
    prefix = "ru.bustime.bus_amounts__"
    if room.startswith("prefix"):
        user_city_id = int(room.split(prefix)[1])
        async with sio.session(sid) as session:
            session["city_id"] = user_city_id
            os = session["os"]
            uid = session["uid"]
        if os == "web":
            room_name = f"cnt_online_{user_city_id}_{os}"
            sio.enter_room(sid=sid, room=room_name)
            await sio.send(data={"join": room_name}, to=sid)
        elif os == "android" or os == "ios" or os == "mac":
            room_name = f"cnt_online_{user_city_id}_app"
            sio.enter_room(sid=sid, room=room_name)
            await sio.send(data={"join": room_name}, to=sid)
        else:
            logger.warning(f"Unknown os for User: {uid}, SID: {sid}")
        update_online(user_city_id, os)
    prefix = "ru.bustime.chat__"
    if room.startswith(prefix):
        chat_room = room
        async with sio.session(sid) as session:
            session['chat_room'] = room
        await update_online_chat(chat_room)


@sio.event
async def leave(sid: str, room: str) -> None:
    if not room:
        logger.warning("Leave undefined room?")
        return
    logger.info(f"leave: {sid} from {room}")
    sio.leave_room(sid, room)
    prefix = "ru.bustime.chat__"
    if room.startswith(prefix):
        async with sio.session(sid) as session:
            del session['chat_room']
        await update_online_chat(room)


@sio.event
@json_decode
async def rpc_bdata(sid: str, data: dict) -> dict:
    logger.info(f"rpc_bdata: {sid}, {data}")
    bus_id = data.get("bus_id")
    mode = data.get("mode")
    mobile = data.get("mobile")
    return await sync_to_async(sio.gloria.rpc_bdata)(bus_id, mode, mobile)


@sio.event
@json_decode
@user_settings
async def rpc_passenger(sid: str, data: dict) -> dict:
    logger.info(f"rpc_passenger: {sid}, {data}")
    result = await sync_to_async(sio.gloria.rpc_passenger)(json.dumps(data))
    await sio.send(data={"rpc_passenger": result}, to=sid)    
    return result


@sio.event
@json_decode
@user_settings
async def rpc_gps_send(sid: str, data: dict) -> dict:
    logger.info(f"rpc_gps_send: {sid}, {data}")
    return await sync_to_async(sio.gloria.rpc_gps_send)(data)


@sio.event
@json_decode
async def rpc_download(sid: str, data: dict) -> dict:
    logger.info(f"rpc_download: {sid}, {data}")
    return await sync_to_async(sio.gloria.rpc_download)(data)


@sio.event
@json_decode
async def rpc_peer_set(sid: str, data: dict) -> None:
    logger.info(f"rpc_peer_set: {sid}, {data}")
    us_id = data["us_id"]
    peer_id = data["peer_id"]
    await sio.redis.set(f"us_{us_id}_peer", peer_id, expire=60 * 60 * 24)


@sio.event
@json_decode
async def rpc_bootstrap_amounts(sid: str, data: dict) -> dict:
    logger.info(f"rpc_bootstrap_amounts: {sid}, {data}")
    return await sync_to_async(sio.gloria.rpc_bootstrap_amounts)(data)


@sio.event
@user_settings(repack_to="tcard_num")
async def rpc_tcard(sid: str, data: str) -> dict:
    logger.info(f"rpc_tcard: {sid}, {data}")
    return await sync_to_async(sio.gloria.rpc_tcard)(json.dumps(data))


@sio.event
@json_decode
async def rpc_stop_ids(sid: str, data: dict) -> dict:
    logger.info(f"rpc_stop_ids: {sid}, {data}")
    ids = data["ids"]
    mobile = data["mobile"]
    return await sync_to_async(sio.gloria.rpc_stop_ids)(ids, mobile)


@sio.event
async def rpc_status_server(sid: str, data: str) -> dict:
    logger.info(f"rpc_status_server: {sid}, {data}")
    return await sync_to_async(sio.gloria.rpc_status_server)()


@sio.event
@json_decode
async def rpc_buses_by_radius(sid: str, data: dict) -> dict:
    logger.info(f"rpc_buses_by_radius: {sid}, {data}")
    city_id = data['city_id']
    x, y = data['x'], data['y']
    buses, radius = data['buses'], data['radius']
    return await sync_to_async(sio.gloria.rpc_buses_by_radius)(city_id, x, y, buses, radius)


@sio.event
@json_decode
async def rpc_buses_by_radius_v2(sid: str, data: dict) -> dict:
    logger.info(f"rpc_buses_by_radius_v2: {sid}, {data}")
    city_id = data['city_id']
    x, y = data['x'], data['y']
    buses, radius = data['buses'], data['radius']
    return await sync_to_async(sio.gloria.rpc_buses_by_radius_v2)(city_id, x, y, buses, radius)


@sio.event
@json_decode
async def rpc_city_monitor(sid: str, data: dict) -> dict:
    logger.info(f"rpc_city_monitor: {sid}, {data}")
    city_id = data['city_id']
    sess = data['sess']
    x, y = data['x'], data['y']
    bus_id, bus_name = data['bus_id'], data['bus_name']
    nb_id, nb_name = data['nb_id'], data['nb_name']
    mob_os = data['mod_os']
    return await sync_to_async(sio.gloria.rpc_city_monitor)(city_id, sess, x, y, bus_name, bus_id, nb_id, nb_name, mob_os)


@sio.event
@json_decode
@user_settings
async def rpc_rating_get(sid: str, data: dict) -> dict:
    logger.info(f"rpc_rating_get: {sid}, {data}")
    return await sync_to_async(sio.gloria.rpc_rating_get)(json.dumps(data))


@sio.event
@json_decode
@user_settings
async def rpc_rating_set(sid: str, data: dict) -> dict:
    logger.info(f"rpc_rating_set: {sid}, {data}")
    return await sync_to_async(sio.gloria.rpc_rating_set)(json.dumps(data))


@sio.event
@json_decode
@user_settings
async def rpc_chat_get(sid: str, data: dict) -> dict:
    logger.info(f"rpc_chat_get: {sid}, {data}")
    return await sync_to_async(sio.gloria.rpc_chat_get)(json.dumps(data))


@sio.event
@json_decode
@user_settings
async def rpc_chat(sid: str, data: dict) -> dict:
    logger.info(f"rpc_chat: {sid}, {data}")
    return await sync_to_async(sio.gloria.rpc_chat)(json.dumps(data))


@sio.event
@json_decode
@user_settings
async def rpc_gosnum_set(sid: str, data: dict) -> dict:
    logger.info(f"rpc_gosnum_set: {sid}, {data}")
    return await sync_to_async(sio.gloria.rpc_gosnum_set)(json.dumps(data))


@sio.event
@json_decode
@user_settings
async def rpc_like(sid: str, data: dict) -> dict:
    logger.info(f"rpc_like: {sid}, {data}")
    return await sync_to_async(sio.gloria.rpc_like)(json.dumps(data))


@sio.event
@json_decode
@user_settings
async def rpc_radio(sid: str, data: dict) -> dict:
    logger.info(f"rpc_radio: {sid}, {data}")
    return await sync_to_async(sio.gloria.rpc_radio)(json.dumps(data))


@sio.event
@json_decode
@user_settings
async def rpc_upload(sid: str, data: dict) -> dict:
    logger.info(f"rpc_upload: {sid}, {data}")
    return await sync_to_async(sio.gloria.rpc_upload)(json.dumps(data))


@sio.event
@json_decode
@user_settings
async def rpc_set_my_bus(sid: str, data: dict) -> dict:
    logger.info(f"rpc_set_my_bus: {sid}, {data}")
    return await sync_to_async(sio.gloria.rpc_set_my_bus)(json.dumps(data))


@sio.event
@json_decode
async def rpc_city_error(sid: str, data: dict) -> dict:
    logger.info(f"rpc_city_error: {sid}, {data}")
    return await sync_to_async(sio.gloria.rpc_city_error)(data)


@sio.event
@json_decode
async def rpc_status_counter(sid: str, data: dict) -> dict:
    logger.info(f"rpc_status_counter: {sid}, {data}")
    return await sync_to_async(sio.gloria.rpc_status_counter)(data)


@sio.event
@json_decode
@user_settings
async def rpc_provider(sid: str, data: dict) -> dict:
    logger.info(f"rpc_status_counter: {sid}, {data}")
    return await sync_to_async(sio.gloria.rpc_provider)(json.dumps(data))


@sio.event
@json_decode
@user_settings
async def rpc_bus(sid: str, data: dict) -> dict:
    logger.info(f"rpc_bus: {sid}, {data}")
    return await sync_to_async(sio.gloria.rpc_bus)(json.dumps(data))


@sio.event
@json_decode
@user_settings
async def rpc_gosnum(sid: str, data: dict) -> dict:
    logger.info(f"rpc_gosnum: {sid}, {data}")
    return await sync_to_async(sio.gloria.rpc_gosnum)(json.dumps(data))


@sio.event
async def rpc_mobile_bootstrap(sid: str) -> dict:
    logger.info(f"rpc_mobile_bootstrap: {sid}, {data}")
    return await sync_to_async(sio.gloria.rpc_mobile_bootstrap)()


@sio.event
@json_decode
@user_settings
async def rpc_get_city_icons(sid: str, data: dict) -> dict:
    logger.info(f"rpc_get_city_icons: {sid}, {data}")
    return await sync_to_async(sio.gloria.rpc_get_city_icons)(json.dumps(data))


@sio.event
@json_decode
@user_settings
async def rpc_vehicle(sid: str, data: dict) -> dict:
    logger.info(f"rpc_vehicle: {sid}, {data}")
    return await sync_to_async(sio.gloria.rpc_vehicle)(json.dumps(data))


@sio.event
@json_decode
@user_settings
async def rpc_schedule(sid: str, data: dict) -> dict:
    logger.info(f"rpc_schedule: {sid}, {data}")
    return await sync_to_async(sio.gloria.rpc_schedule)(json.dumps(data))


app = socketio.ASGIApp(sio, on_startup=on_startup, on_shutdown=on_shutdown)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Socketoto service for WebSocket communications "
                                                 "between devices over Socket.IO protocol")
    parser.add_argument("-H", "--host", dest="host", type=str, help="Server hostname (default: 127.0.0.1",
                        action="store", default="127.0.0.1")
    parser.add_argument("-P", "--port", dest="port", type=int, help="Server port (default: 9003)",
                        action="store", default=9003)
    parser.add_argument("--debug", help="debug mode", action="store_true")
    parser.add_argument("--mobile", help="mobile mode", action="store_true")
    args = parser.parse_args()
    if args.debug:
        logger.setLevel(logging.DEBUG)
    is_mobile = args.mobile
    ssl_keyfile = '/etc/letsencrypt/live/bustime.ru/privkey.pem' if scheme == "https" else None
    ssl_certfile = '/etc/letsencrypt/live/bustime.ru/cert.pem' if scheme == "https" else None
    sio.eio.is_mobile = is_mobile
    # Workaround for mobile devices    
    if is_mobile:
        sio.eio.ping_interval = 180
        sio.eio.ping_timeout = 300
    uvicorn.run(app, host=args.host, port=args.port, ssl_keyfile=ssl_keyfile, ssl_certfile=ssl_certfile)
