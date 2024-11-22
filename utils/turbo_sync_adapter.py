#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Синхронизирующий адаптер. Преобразовывает новый формат после турбин в совместимый со старыми клиентами.
# Также чистит старые события.
# busamounts__osm_id
# bdata_mode0 todo

from devinclude import *
from bustime.models import *
from functools import cmp_to_key
from collections import defaultdict

def lava_sort_up(lava_x, lava_y):
    if lava_x.get('d') == None:
        return 1
    if lava_y.get('d') == None:
        return -1

    if lava_x['d'] == lava_y['d']:
        return lava_x['order'] - lava_y['order']
    elif lava_x['d'] > lava_y['d']:
        return 1
    else:
        return -1


def remove_from_redis(uniqueid, *, pipeline: redis.Redis, bus_id=None, pids=None, reason=None):
    pipeline.srem('events', uniqueid)
    if pids:
        for pid in pids:
            pipeline.srem(f"place_{pid}", uniqueid)
    pipeline.delete(f'event_{uniqueid}')
    if bus_id:
        pipeline.srem(f'bus__{bus_id}', uniqueid)
        pipeline.publish(f"turbo_{bus_id}", 
            pickle_dumps({"cmd": "remove", "uid": uniqueid, 
                        "reason": reason}))


if __name__ == '__main__':
    print(datetime.datetime.now().replace(microsecond=0), 'Loading routes...')
    restart_key = "turbo_sync_restart"
    REDIS_W.delete(restart_key)
    start_time = datetime.datetime.now()
    all_routes = Route.objects.filter()
    R={}
    for r in all_routes:
        if not R.get(r.bus_id):
            R[r.bus_id] = {}
        R[r.bus_id][r.id] = r
    print(datetime.datetime.now().replace(microsecond=0), 'Done')
    print(datetime.datetime.now().replace(microsecond=0), 'Loading buses...')
    fill_bus_stata()
    print(datetime.datetime.now().replace(microsecond=0), 'Done')
    all_stops = {stop['id']: stop for stop in 
        NBusStop.objects.all().values("id", "moveto", "tram_only", "timezone")}
    pipe = REDIS_W.pipeline(transaction=False)
    pipe_io = REDIS_IO.pipeline(transaction=False)
    rpipe = REDIS.pipeline()
    bdata_mode1 = defaultdict(list)
    bdata_mode3 = {}
    amounts = {}
    time_bst = {}
    log_counters_prev = {}

    while 1:
        print(datetime.datetime.now().replace(microsecond=0), 'START')
        uids = REDIS.smembers("events")
        uids = list([x.decode('utf8') for x in uids])
        to_get = [f'event_{uid}' for uid in uids]
        # events = {}

        amounts_prev = copy.deepcopy(amounts)
        # bdata_mode3_prev = copy.deepcopy(bdata_mode3)
        time_bst_prev = copy.deepcopy(time_bst)
        amounts = {}
        bdata_mode1 = defaultdict(list)
        time_bst = {}
        log_counters = {}

        buses = set()
        cnt = 0

        turbine_inspector = get_setting("turbine_inspector")

        for e in rcache_mget(to_get):
            ev_id, uid = to_get.pop(0), uids.pop(0)
            if not e:
                remove_from_redis(uid, pipeline=pipe)
                continue

            if not e.bus_id:
                # not processed yet, semi-raw event
                continue
            # bus = bus_get_turbo(e.bus_id)
            bus = bus_get(e.bus_id)
            if not bus:
                # delete event if bus is not found for the second time
                # do we need it in scope of restart_key?
                remove_from_redis(uid, pipeline=pipe, bus_id=e.bus_id, reason=f"Bus {e.bus_id} is not found.")
                if turbine_inspector and e.bus_id in turbine_inspector:
                    ch =  f"bustime.turbine_inspector__{e.bus_id}"
                    sio_pub(ch, {'turbine_inspector': {'widget': 'clean_up', 'text': "rem from events: no bus", 'uid':e.uniqueid}}, pipe=pipe_io)
                continue

            if not R.get(e.bus_id): # dynamically load absent routes
                all_routes = Route.objects.filter(bus_id=e.bus_id)
                if all_routes:
                    R[e.bus_id] = {}
                    for r in all_routes:
                       R[r.bus_id][r.id] = r
                else:
                    remove_from_redis(uid, pipeline=pipe, bus_id=e.bus_id, pids=bus.places_all, reason=f"Route for bus_id {e.bus_id} is not found.")
                    if turbine_inspector and e.bus_id in turbine_inspector:
                        ch =  f"bustime.turbine_inspector__{e.bus_id}"
                        sio_pub(ch, {'turbine_inspector': {'widget': 'clean_up', 'text': "rem from events: no route", 'uid':e.uniqueid}}, pipe=pipe_io)
                    continue

            cnt += 1
            now = now_at(e.x, e.y)
            if not now:
                ch =  f"bustime.turbine_inspector"
                sio_pub(ch, {'turbine_inspector': {'widget': 'inspector', 'text': "not valid x, y %s" % e, 'uid':e.uniqueid}}, pipe=pipe_io)
                continue

            if e.timestamp < now-datetime.timedelta(seconds=60*15) or e.timestamp > now+datetime.timedelta(seconds=86400):
                remove_from_redis(uid, pipeline=pipe, bus_id=e.bus_id, pids=bus.places_all, reason=f"Remove an outdated event.")
                if turbine_inspector and e.bus_id in turbine_inspector:
                    ch =  f"bustime.turbine_inspector__{e.bus_id}"
                    sio_pub(ch, {'turbine_inspector': {'widget': 'clean_up', 'text': "rem from bus,events,places: old timestamp %s" % e, 'uid':e.uniqueid}}, pipe=pipe_io)

                continue
            # events[uid] = e

            # log_counters preparation
            for pid in bus.places_all:
                if not log_counters.get(pid):
                    log_counters[pid] = {
                        "allevents_len": 0,
                        "zombie": 0,
                        "away": 0,
                        "sleeping": 0,
                        "nearest": 0,
                        "uevents_len": 0
                    }

                log_counters[pid]['allevents_len'] += 1
                log_counters[pid]['uevents_len'] += 1 # todo?

                if e.zombie:
                    log_counters[pid]['zombie'] += 1
                if e.away:
                    log_counters[pid]['away'] += 1
                if e.sleeping:
                    log_counters[pid]['sleeping'] += 1

            #
            # sync bus_amounts
            #
            if e.get('busstop_nearest') and not e.zombie and not e.away and not e.sleeping:
                # for osm in bus.osm_as_list:
                #     cc_key = "busamounts_%s" % osm
                #     am = amounts.get(cc_key)
                #     if not am:
                #         amounts[cc_key] = {}
                #     a = amounts[cc_key].get("%s_d%s" % (e.bus_id, e.direction), 0)
                #     amounts[cc_key]["%s_d%s" % (e.bus_id, e.direction)] = a + 1
                for pid in bus.places_all:
                    cc_key = "busamounts_%s" % pid
                    am = amounts.get(cc_key)
                    if not am:
                        amounts[cc_key] = {}
                    a = amounts[cc_key].get("%s_d%s" % (e.bus_id, e.direction), 0)
                    amounts[cc_key]["%s_d%s" % (e.bus_id, e.direction)] = a + 1

                    log_counters[pid]['nearest'] += 1

            if e.zombie:
                ee = Event(e.copy())
                ee["busstop_nearest"] = None
                lava = ee.get_lava()
            else:
                lava = e.get_lava()

            if e.get('busstop_nearest') and not e.zombie and not e.away and not e.sleeping:
                if not R[e.bus_id].get(e['busstop_nearest']): continue
                stop_id = R[e.bus_id][e['busstop_nearest']].busstop_id
                mode1bus = {"id": e.bus_id}
                mode1bus.update(lava)
                bdata_mode1[stop_id].append(mode1bus)
            buses.add(e.bus_id)

        for cc_key, amounts in amounts.items():
            # amounts for every pa
            if amounts != amounts_prev.get(cc_key):
                pipe.set(cc_key, pickle_dumps(amounts), 60 * 10)

        # get all time_bst in one redis call
        to_get = []
        for _ in rpipe.execute():
            time_bst[to_get.pop(0)] = {int(kk.decode('utf8')): vv.decode('utf8') for kk, vv in _.items()}

        for bid in buses:
            tosend = {}
            for r in R[bid].values():
                sid = r.busstop_id
                zs = bdata_mode1.get(sid, [])
                if zs:
                    tosend[sid] = zs
            if tosend:
                #chan = "ru.bustime.bus_mode1__%s" % bid
                #serialized = {"bdata_mode1": tosend, "bus_id": bid}
                #sio_pub(chan, serialized, pipe=pipe_io) # we don't use mode1 anymore
                #todo remove obsolete code

                # здесь небольшие модификации для мобильных, bus_mode11
                # удлаляет номер остановки и название, так как там есть своя БД
                # todo: make it in turbomill?
                chan = "ru.bustime.bus_mode11__%s" % bid
                for k, v in tosend.items():
                    for vv in v:
                        if vv.get('bn'):
                            del vv['bn']
                            del vv['order']
                serialized = {"bdata_mode11": tosend, "bus_id": bid}
                sio_pub(chan, serialized, pipe=pipe_io)

        # log_counters save
        for k,v in log_counters.items():
            pipe.set("log_counters_%s" % k, pickle_dumps(v))
            if log_counters_prev.get(k) != v:
                chan = f"ru.bustime.status__{k}"
                data = {"status_counter": v}
                sio_pub(chan, data, pipe=pipe_io)
        log_counters_prev = copy.deepcopy(log_counters)

        pipe.execute()
        pipe_io.execute()

        print(datetime.datetime.now().replace(microsecond=0), 'STOP (%s events)' % cnt, flush=True)

        # Marker turbo_sync_restart means than routes has been changed
        # and we need to restart sync_adapter for all caches reload
        if REDIS.exists(restart_key):
            uptime = datetime.datetime.now() - start_time
            if uptime.seconds > 60*5: # alive for more then 5 mins
                if turbine_inspector and e.bus_id in turbine_inspector:
                    ch =  f"bustime.turbine_inspector__{e.bus_id}"
                    sio_pub(ch, {'turbine_inspector': {'widget': 'sync_adapter', 'text': "got restart_key: harakiri!", 'uid':e.uniqueid}})
                print("HARAKIRI")
                sys.exit()

        time.sleep(7)
