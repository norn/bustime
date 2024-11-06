#!/usr/bin/env python
# -*- coding: utf-8 -*-

import devinclude
from bustime.models import *
import psutil
import time, datetime
import argparse
import gevent
from collections import defaultdict, ChainMap
from bustime.update_lib_turbo import mill_event, VEHICLE_CACHE_STALE_INTERVAL
# import tracemalloc
# from sys import getsizeof


def get_detector_data(bus_id):
    DD = {}
    ROUTES, ROUTES_NG, R = {}, {}, {}
    all_routes = routes_get(bus_id)
    buf = None
    for r in all_routes:
        R[r.id] = r
        if ROUTES.get(r.bus_id):
            ROUTES[r.bus_id].append(r)
        else:
            ROUTES[r.bus_id] = [r]

        if not ROUTES_NG.get(r.bus_id):
            ROUTES_NG[r.bus_id] = {0: nx.DiGraph(), 1: nx.DiGraph()}
            buf = None
        if buf and r.direction in [0, 1]:
            ROUTES_NG[r.bus_id][r.direction].add_edge(buf.id, r.id)
        buf = r
    DD['BUSSTOPS_POINTS'] = dd_stops_get(bus_id)
    DD['R'] = R
    DD['ROUTES'] = ROUTES
    DD['ROUTES_NG'] = ROUTES_NG  # Координаты NetworkX Переезжает в Redis

    return DD


# temp for debug
def mem_usage():
    pid = psutil.Process()
    memory_info = pid.memory_info()
    memory_usage = memory_info.rss
    memory_usage_mb = memory_usage / 1024 / 1024
    return(f"mem={memory_usage_mb:.0f} MB")


# should I proccess this event?
def is_mine(bus_id, index, city):
    if city:
        return True
    else:
        return bus_id % settings.TURBO_MILL_COUNT == index


def hgetall_decoded_kint(cc_key):
    hgall = REDIS.hgetall(cc_key)
    return {bus_id: {int(k.decode('utf8')): v.decode('utf8') for k, v in hgall.items()}}


def turbine(bus_id: int, index: int):
    global all_vehicles
    pubsub = REDIS.pubsub()
    pubsub.subscribe(f'turbo_{bus_id}')
    pipe = REDIS_W.pipeline(transaction=False)
    pipe_io = REDIS_IO.pipeline(transaction=False)
    bdata_mode0, bdata_mode1, bdata_mode3, bdata_mode_10 = {}, {}, {}, {}
    # reload all route info on reload cmd!
    while 1:
        # prepare
        bus = bus_get(bus_id)
        # ids for inspection
        turbine_inspector = False
        if bus_id in (get_setting("turbine_inspector") or []):
            turbine_inspector = f"bustime.turbine_inspector__{bus_id}"

        cnt = 0
        DD = get_detector_data(bus_id)
        if not DD['R']: break
        last = {}
        time_bst = hgetall_decoded_kint("time_bst__%s" % bus_id)
        timer_bst = rcache_get("timer_bst_%s" % bus_id, {})
        time_bst_ts = hgetall_decoded_kint("time_bst_ts__%s" % bus_id)
        timetable = {}
        # passengers = rcache_get("passengers_%s" % bus_id, defaultdict(list))
        # temporary disabled until we resolve autocollect first stop passengers
        passengers = defaultdict(list)
        bstops = city_routes_get_turbo(bus_id)
        amounts = {0: set(), 1: set()}
        datasources = {}
        ignores = set()


        # bdata_mode3_trb = defaultdict(dict)
        # for r in bstops:
        #     stop_id = r['busstop_id']
        #     bdata_mode3_trb[int(stop_id)] = {k.decode('utf-8'): entity
        #         for k, v in REDIS.hgetall(f"busstop__{int(stop_id)}").items()
        #         if (entity := pickle.loads(v)) and entity['bid'] == bus_id
        #     }
        

        # bdata_mode3 has relations stop_id => uniqueid, 
        # this is opposite mapping uniqueid => stop_id.
        # It needs for removing an old forecasts
        # evt_mode3_map = defaultdict(list)
        # for k,v in bdata_mode3_trb.items():
        #     for key, val in v.items():
        #         evt_mode3_map[key].append((k, val['t']))

        # filter out old events: 1. determine time tzone and get current time
        # do we need now var?

        uids = REDIS.smembers(f"bus__{bus_id}")
        uids = list([x.decode('utf8') for x in uids])
        to_get = [f'event_{uid}' for uid in uids]
        for ev in rcache_mget(to_get):
            ev_id, uid = to_get.pop(0), uids.pop(0)
            if not ev:
                pipe.srem("bus__%s" % bus_id, uid)
            elif ev.bus_id != bus_id:
                # you feed me with nonsense!
                pipe.srem("bus__%s" % bus_id, uid) # delete from bus memebers
                for pid in bus.places_all:
                    pipe.srem(f"place__{pid}", uid) # and places
            else:
                last[uid] = ev
                if ev.busstop_nearest and not ev.zombie and not ev.away and not ev.sleeping:
                    amounts[ev.direction].add(uid)

        if len(pipe):
            pipe.execute()

        rcache_direction = {}
        
        chan = f"bus_{bus_id}"
        # process
        snapshot_old = None

        for message in pubsub.listen():
            if message.get("type") == 'message':
                tick = time.perf_counter()
                perfmon_start_time = time.time()
                data = pickle.loads(message['data'])
                if type(data) == Event:
                    if turbine_inspector and data.get('uniqueid'):
                        sio_pub(turbine_inspector, {'turbine_inspector': {'widget': 'input', 'text': str(data), 'uid':data['uniqueid']}})
                    for pid in bus.places_all:
                        cc_key = f"eps_{pid}_{datetime.datetime.now().second}"
                        pipe.incr(cc_key)
                        pipe.expire(cc_key, 3)
                    prev_passengers = passengers.copy()
                    result = mill_event(data, DD=DD, last=last, passengers=passengers, \
                                pipe=pipe, pipe_io=pipe_io, bus=bus, rcache_direction=rcache_direction, \
                                bdata_mode0=bdata_mode0, bdata_mode1=bdata_mode1, \
                                bdata_mode_10=bdata_mode_10, \
                                timer_bst=timer_bst, amounts=amounts, \
                                time_bst=time_bst, time_bst_ts=time_bst_ts, \
                                bstops=bstops, vehicles_info=all_vehicles,
                                timetable=timetable,
                                datasources=datasources, turbine_inspector=turbine_inspector,
                                ignores=ignores)

                    if turbine_inspector and data.get('uniqueid'):
                        sio_pub(turbine_inspector, {'turbine_inspector': {'widget': 'results', 'text': data.get('uniqueid')+": "+str(result), 'uid':data['uniqueid']}})

                    pass_update = {}
                    for k, v in passengers.items():
                        if len(prev_passengers.get(k,[])) != len(v):
                            pass_update[f"{k}"] = len(v)
                    if pass_update:
                        sio_pub(f"ru.bustime.bus_mode10__{bus_id}", {'passenger': pass_update})
                        rcache_set("passengers_%s" % bus_id, passengers)
                    cnt += 1
                elif type(data) == dict:
                    cmd = data.get("cmd")
                    if cmd == "reload":
                        print(f"{bus_id} reload requested: BREAK")
                        # Route has been changed, tells restart to turbo_sync
                        pipe.set("turbo_sync_restart", 1, nx=True)
                        break
                    elif cmd == "reload_vehicles":
                        print(f"{bus_id} reload_vehicles requested...")
                        all_vehicles = {v['uniqueid']: \
                            {**v, **{"stale_time": stale_time}} for v in Vehicle.objects.values()}
                    elif cmd == 'sync_cache':
                        print(f"{bus_id} sync_cache requested...")
                        cached_keys = {uid.decode('utf-8') for uid in REDIS.smembers(f'bus__{bus_id}')}
                        to_remove = set(last.keys()) - cached_keys
                        for key in to_remove:
                            del last[key]
                    elif cmd == 'remove':
                        # and how are we going to notify sio_pub with updated busamounts?
                        uniqueid = data.get('uid')
                        print(f"{bus_id} remove uid {uniqueid} from cache. Reason [{data.get('reason')}]")
                        if uniqueid in last:
                            del last[uniqueid]
                    elif cmd == "passenger":
                        # updates passengers and notify clients
                        user_id = int(data["user_id"])
                        r_id = data["r_id"]
                        was = None
                        bp = {}
                        for k,v in passengers.items():
                            if user_id in v:
                                passengers[k].remove(user_id)
                                was = k
                                bp[f"{k}"] = len(passengers[k])
                        if was != r_id:
                            passengers[r_id].append(user_id)
                            bp[f"{r_id}"] = len(passengers[r_id])
                        # no pipe here!
                        sio_pub(f"ru.bustime.bus_mode10__{bus_id}", {'passenger': bp})
                        rcache_set("passengers_%s" % bus_id, passengers)
                    continue # if got dict and still here (unknown cmd)

                ### end of story
                if len(pipe):
                    # tnow = datetime.datetime.now()
                    # pipe.incr(f"turbo_count_{tnow.minute}:{tnow.second}")
                    if bus_id == 1370:
                        # print("redis pipe stack : %s" % (pipe.command_stack))
                        z1 = time.time()
                        pipe.execute()
                        dta = time.time() - z1
                        print("redis pipe delay: %.4f secs" % (dta))
                    else:
                        pipe.execute()
                if len(pipe_io):
                    pipe_io.execute()

                if bus_id == 1370:
                    dta = time.time() - perfmon_start_time
                    print("%s [%s]: %.4f secs" % (cnt, data.uniqueid, dta))
                tock = time.perf_counter()

                if cnt % 1024 == 5: # some stats
                    mem = mem_usage()
                    len_last=len(last)
                    print(f"bus={bus_id} [{data.uniqueid}], {mem}, processed={cnt}, len(last)={len_last},  time: {tock - tick:0.4f}", flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--index', type=int, help="Turbo index (total from settings.TURBO_MILL_COUNT)", required=True)
    parser.add_argument('-c', '--city', type=str, help="Listen events for buses from city & place ID only", required=False)
    args = parser.parse_args()
    greenlets = []

    # what time is it now?
    start_time = datetime.datetime.now()
    # oudate time is?
    stale_time = start_time + datetime.timedelta(minutes=VEHICLE_CACHE_STALE_INTERVAL)
    tic = time.perf_counter()
    # all_vehicles = {v['uniqueid']: ChainMap(v, {"stale_time": stale_time}) for v in Vehicle.objects.values()}
    all_vehicles = {v['uniqueid']: {**v, **{"stale_time": stale_time}} for v in Vehicle.objects.values()}
    toc = time.perf_counter()
    print(f"All vehicles info has been taken for {toc-tic:0.4} secs")
    fill_bus_stata() # warm up bus_get cache
    tic = time.perf_counter()
    print(f"bus_get cache warm up for {tic-toc:0.4} secs")

    # we don't use it right now
    # if not REDIS.exists("geo_stops"):
    #     fill_stops_geospatial() # one time run

    # start for all interested routes beforehand
    if args.city:
        print(f"Loading buses only for city/place {args.city.upper()}")
        if args.city.isdigit():
            id = int(args.city)
        else:
            id = Place.objects.get(slug=args.city).id
        turbo_bus_ids = Bus.objects.filter(places__id = id, active=True).union(
            Bus.objects.filter(city_id = id, active=True)).values_list("id", flat=True)
    else:
        turbo_bus_ids = Bus.objects.filter(active=True).values_list("id", flat=True)

    for bus_id in turbo_bus_ids:
        if is_mine(bus_id, args.index, args.city):
            greenlet = gevent.spawn(turbine, bus_id, args.index)
            greenlets.append(greenlet)

    # Listen for updates
    print ("Ready and listening for bus_new")
    pubsub = REDIS.pubsub()
    pubsub.subscribe("bus_new")
    for message in pubsub.listen():
        if message.get("type") == 'message':
            # spawn new one on request
            data = pickle.loads(message['data'])
            bus_id = data['data']
            bus_id = int(bus_id)
            print(f"requested bus_new, bus_id={bus_id}")
            if is_mine(bus_id, args.index, args.city):
                try:
                    greenlet = gevent.spawn(turbine, bus_id, args.index)
                    greenlets.append(greenlet)
                    print(f"new greenlet started for bus_id={bus_id}")
                except:
                    print("some unexpected error")
