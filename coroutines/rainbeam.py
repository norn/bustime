from os import sync
import pickle
import datetime, time
from devinclude import *
from collections import defaultdict
from bustime.models import *
from django.core.serializers.json import DjangoJSONEncoder
import json

def timetable(delay=30):
    """ Accumulate forecasts from turbomills with a given delay, 
        do caclucation of total forecasts, prepare it for clients and send
    """
    def calculate(timetable):
        bids_to_delete = defaultdict(list)
        # tic = time.perf_counter()
        mode3values = []
        for sid, items in timetable.items():
            chan = f"ru.bustime.stop_id__{sid}"
            stop_id = int(sid)
            try:
                busstop = all_stops[stop_id]
            except KeyError:
                busstop = next(iter(NBusStop.objects.filter(id=stop_id).values("id", "moveto", "tram_only", "timezone")))
                all_stops[busstop['id']] = busstop
            now = datetime.datetime.now(busstop['timezone']).replace(tzinfo=None)
            move_to = busstop['moveto']
            tram_only = busstop['tram_only']
            stop_timetable = {}
            for bid, item in ((k, v) for k, v in items.items()):
                # Check outdated forecasts
                bus_id = int(bid)
                if (item.get('t', datetime.datetime.min) < now and 
                    item.get('t2', datetime.datetime.min) < now):
                    bids_to_delete[sid].append(bus_id)
                else:
                    if (mode3_prev := timetables_cache.get(sid, {}).get(bid)) is None or \
                        mode3_prev.get('t') != item.get('t') or mode3_prev.get('t2') != item.get('t2'):
                        timetables_cache[sid][bid] = copy.copy(item)
                        stop_timetable[bus_id] = pickle_dumps(item)
                    item['l'] = bdata_mode0.get(item['uid']) if item['uid'] else None
                    item['bid'] = bus_id
                    mode3values.append(item)
            if stop_timetable:
                pipe.hset(f"timetable__{sid}", mapping=stop_timetable)
            data = {"stops": [
                get_nstop_nearest_timing_bdata_mode3(
                    stop_id, move_to, tram_only, 
                    {stop_id: mode3values}, now.strftime('%H:%M:%S'))]}
            sio_pub(chan, data, pipe=pipe_io)
            mode3values.clear()
        # print(f"EXEC: {time.perf_counter() - tic:0.4f}")

        # if db_dump:
        pipe.execute()
        pipe_io.execute()

        # cleanup an outdated forecasts
        for sid, bids in bids_to_delete.items():
            for bid in bids:
                del timetable[sid][bid]
                if not timetable[sid]:
                    del timetable[sid]
        bids_to_delete.clear()

        now = datetime.datetime.now()
        to_delete = {uid for uid, dt in timestamps.items() if now - dt > datetime.timedelta(seconds = 60*15)}
        for uid in to_delete:
            del timestamps[uid]
            del bdata_mode0[uid]


    lifetime = time.monotonic()
    timetables_cache = defaultdict(dict)
    all_stops = {stop['id']: stop for stop in NBusStop.objects.values("id", "moveto", "tram_only", "timezone")}
    pipe = REDIS_W.pipeline()
    pipe_io = REDIS_IO.pipeline()
    timetable = defaultdict(dict)  # common dict of dict for all. dict[stop_id][bus_id] = forecast
    timestamps = {}
    bdata_mode0 = {}
    tts = REDIS.pubsub()
    tts.subscribe("timetable_update")
    print("START LISTENING")
    start = time.monotonic()
    for message in tts.listen():
        if message.get("type") == 'message':
            # Got a new predictions for a Route. Have to update timetable for that data
            # with open('/tmp/rainbeam_lite.log', 'wb') as f:
            #     f.write(message['data'])
            # sys.exit()
            # data = pickle.loads(message['data'])
            # for sid, entry in data.items():
            #     timetable[sid].update(entry)
            bus_id, bus_name, ttbs, lava = pickle.loads(message['data'])
            # with open('/tmp/rainbeam_info.log', 'w') as f:
            #     f.write(json.dumps(pickle.loads(message['data']), indent=1, cls=DjangoJSONEncoder))
            # sys.exit()
            now = datetime.datetime.now()
            for uid, ttb in ttbs.items():
                for sid, info in ttb.items():
                    info['n'] = bus_name
                    info['bid'] = bus_id
                    if uid == 'first':
                        info['first'] = True
                        info['uid'] = None
                    else:
                        info['uid'] = uid
                    timetable[sid][bus_id] = info
            bdata_mode0[lava['u']] = lava
            timestamps[lava['u']] = now

        if (time.monotonic() - start) > datetime.timedelta(seconds=delay).total_seconds():
            # with open('/tmp/timetable.log', 'a') as f:
            #     f.write(json.dumps(timetable, indent=2, cls=DjangoJSONEncoder))
            # sys.exit()
            start = time.monotonic()
            tic = time.perf_counter()
            calculate(timetable)
            print(f"EXEC TIME {time.perf_counter() - tic:0.4f} for {len(timetable)}")

        # supervisor reboot
        if (time.monotonic() - lifetime) > datetime.timedelta(hours=24).total_seconds():
            sys.exit()


if __name__ == "__main__":
    while True:
        timetable()
        time.sleep(1)
    
