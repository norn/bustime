# -*- coding: utf-8 -*-
from bustime.models import *
from django.core.cache import cache
import logging
import zmq
from bustime.detector import *


def analyze_events(city, events, debug=False):
    # import yappi; yappi.start()
    context = zmq.Context()
    sock = context.socket(zmq.PUB)
    sock.connect(ZSUB)
    REDISP = REDIS.pipeline()
    # datetime.datetime.now(pytz.timezone('Europe/Kaliningrad'))
    changed_buses, now = [], datetime.datetime.now()
    start_time = now
    now += datetime.timedelta(hours=city.timediffk)
    logger = logging.getLogger(__name__)
    logger.info("updating city %2d: events=%4d" % (city.id, len(events)))
    bdata_mode0 = {}  # old bdata, the most hard
    bdata_mode1 = {}  # I am bus, hello alex
    # bdata_mode2 = {}  # on the map
    bdata_mode3 = {}  # by busstop, [nbusstop] = "#79 2 min<br/>#2 4 min" etc
    cache_many = {}
    cb_last_changed = {}
    #prev_cached = cache.get_many(["event_%s_%s" % (city.id, e.uniqueid) for e in events])
    if city.id == 3:
        uniqueid_to_gosnum = cache.get("uniqueid_to_gosnum", {})
    prev_cached = REDIS.get("allevents_%s" % city.id)
    if prev_cached:
        prev_cached = pickle.loads(prev_cached)
    else:
        prev_cached = {}
    # print "total events", len(events)
    cnt_fresh, cnt_old = 0, 0
    for e in events:
        # if e.timestamp < now - datetime.timedelta(minutes=15): # krsk shit
        #     continue
        cache_key = "event_%s_%s" % (city.id, e.uniqueid)
        prev = prev_cached.get(cache_key)
        # prev = REDIS.get(cache_key)
        if city.id == 3 and e.uniqueid in uniqueid_to_gosnum:
            e["gosnum"] = uniqueid_to_gosnum[e.uniqueid]

        if prev and e.timestamp == prev.timestamp:  # the same data
            fresh = False
            cnt_old += 1
        else:
            fresh = True
            cnt_fresh += 1

        # fill out prev
        if fresh and prev:
            if prev.x != e.x:
                # e.point_prev = prev.point
                e["x_prev"], e["y_prev"] = prev.x, prev.y
                e["last_point_update"] = e.timestamp
            else:
                # e.point_prev = prev.point_prev
                e["x_prev"], e["y_prev"] = prev.x_prev, prev.y_prev
                e["last_point_update"] = prev.last_point_update
            e["busstop_prev"] = prev.busstop_nearest
            e["timestamp_prev"] = prev.timestamp
            e["direction"] = prev.direction
            e["sleeping"] = prev.sleeping
            e["last_changed"] = prev.last_changed
            e["dchange"] = prev.dchange
            e["speed"] = int((e.speed + prev.speed) / 2.0)

        # check dchange shit
        # if city.id==3 and e.bus.name in ["49", "6", "76", "92"] and ttype==0:
        #     f = open('/tmp/btest.csv','a')
        #     f.write("%s;%s;%s;%s;%s;\n"%(e.uniqueid, e.bus_id, e.timestamp, e.point.x, e.point.y))
        #     f.close()
        if fresh:
            e['busstop_nearest'] = ng_detector(e.bus, e.x_prev, e.y_prev, e.x, e.y)
            if e.busstop_nearest:
                e["direction"] = e.busstop_nearest.direction
            elif prev and prev.busstop_nearest:
                e["busstop_nearest"] = prev.busstop_nearest
                e["direction"] = e.busstop_nearest.direction

            # если остановка сменилась, то запомним !!!
            if e.busstop_nearest != e.busstop_prev:
                real_change = True
                if e.busstop_nearest and e.busstop_prev and \
                   e.busstop_nearest.direction != e.busstop_prev.direction and not \
                   e.busstop_nearest.endpoint:
                    delta = 1 if e.busstop_nearest.direction else -1
                    if e.dchange is None:
                        e["dchange"] = 500
                    e["dchange"] += 250 * delta
                    if e.dchange not in [0, 1000]:
                        e["busstop_nearest"] = e.busstop_prev
                        real_change = False
                    # f=open('/tmp/dchange','a')
                    # f.write("city%s %s [%s]\n"%(city.id, now, real_change))
                    # f.close()
                if real_change:
                    cb_last_changed[e.uniqueid] = e.last_changed
                    e["last_changed"] = e.timestamp
                    e["dchange"] = 500
                    changed_buses.append(e)
        else:
            e = prev

        e["zombie"] = False
        if e.busstop_nearest and not e.busstop_nearest.endpoint:
            # последнее изменение точки > 5 мин
            if e.last_point_update and (e.timestamp - e.last_point_update).total_seconds() > 60 * 5:
                e["zombie"] = True
            # последнее изменение остановки > 15 мин
            if e.last_changed and (e.timestamp - e.last_changed).total_seconds() > 60 * 15:
                e["zombie"] = True
            # последнее событие из прошлого > 5 мин
            if (now - e.timestamp).total_seconds() > 60 * 5:
                e["zombie"] = True

        cache_many[cache_key] = e

        # save for rendering
        # не учитывать стоящие автобусы на конечных
        # and not (e.speed < 10 and e.busstop_nearest.endpoint)

        if e.direction is not None and e.busstop_nearest and not e.zombie:
            # create if not
            if not bdata_mode0.get(e.bus_id):
                bdata_mode0[e.bus_id] = {
                    0: {'stops': []}, 1: {'stops': []}, 'updated': now, 'l': []
                }
            if e.speed < 10 and e.busstop_nearest.endpoint:
                e["sleeping"] = True
                if e.busstop_nearest.order != 0:  # мы хотим видеть его первым
                    if e.direction == 1:
                        ndir = 0
                    else:
                        ndir = 1
                    # кэш + вдрг если нет второго направления
                    for r in ROUTES[e.bus_id]:
                        if r.order == 0:
                            e["busstop_nearest"] = r
                            e["direction"] = r.direction
                            if r.direction == ndir:
                                break
            else:
                e["sleeping"] = False

            if not e.sleeping and not e.zombie:
                bdata_mode0[e.bus_id][e.direction][
                    'stops'].append(e.busstop_nearest.id)
            lava = {'s': e.speed, 'b': e.busstop_nearest.id, 'r': e.ramp, 'd': e.direction,
                    'h': e.heading, 'u': e.uniqueid}  # 'bi':e.busstop_nearest.busstop.id,
            if e.gosnum:
                lava['g'] = e.gosnum
            #'t':str(e.timestamp), 'g':e.gosnum, 'u':e.uniqueid,
            if e.x:
                lava['x'], lava['y'] = e.x, e.y
                lava['bn'] = e.busstop_nearest.busstop.name
            if e.x_prev:
                lava['px'], lava['py'] = e.x_prev, e.y_prev
            if e.sleeping:
                lava['sleep'] = 1

            if not e.zombie:
                bdata_mode0[e.bus_id]['l'].append(lava)
                # для мультипасса
                if not bdata_mode1.get(e.busstop_nearest.busstop_id):
                    bdata_mode1[e.busstop_nearest.busstop_id] = []

                mode1bus = [e.bus_id, lava.get('g', ''), lava.get('s', ''),
                            lava.get('sleep', 0), lava.get('u', ''),
                            lava.get('r', '')]
                bdata_mode1[e.busstop_nearest.busstop_id].append(mode1bus)

    pi = pickle_dumps(cache_many)
    REDIS.set("allevents_%s" % city.id, pi, ex=60 * 5)
    cache_many = {}
    busamounts = {}
    logger.info("city=%2d, fresh = %4d, old=%4d" % (city.id, cnt_fresh, cnt_old))

    for bus_id, v in bdata_mode0.iteritems():
        # cache.set("bdata_mode0_%s" % (bus_id), v, 60 * 10)
        # cache_many["bdata_mode0_%s" % (bus_id)] = v # wow!
        pi = pickle_dumps(v)
        REDISP.set("bdata_mode0_%s" % (bus_id), pi, ex=60 * 10)
        sock.send("bdata_mode0_%s %s" % (bus_id, pi))
        busamounts["%s_d0" % bus_id] = len(
            filter(lambda(x): x['d'] == 0, v['l']))
        busamounts["%s_d1" % bus_id] = len(
            filter(lambda(x): x['d'] == 1, v['l']))
        cats = cache.get('bustime_passenger_%s' % bus_id, {})
        if cats:
            flag = 0
            stops = v[0]['stops'] + v[1]['stops']
            for d in cats.keys():
                try:
                    if int(d) in stops:
                        cats.pop(d)
                        flag = 1
                except:
                    pass
            if flag:
                cache.set('bustime_passenger_%s' % bus_id, cats)
    REDISP.execute()
    cache.set("busamounts_%s" % city.id, busamounts, 60 * 10)
    pi = pickle_dumps(busamounts)
    sock.send("busamounts_%s %s" % (city.id, pi))
    pi = pickle_dumps(bdata_mode1)
    sock.send("bdata_mode1_%s %s" % (city.id, pi))

    # detect time amount tp get from busstop b1 to busstop b2
    #timer_bst = cache.get("timer_bst_%s" % city.id, {})
    timer_bst = REDIS.get("timer_bst_%s" % city.id)
    if not timer_bst:
        timer_bst = {}
    else:
        timer_bst = pickle.loads(timer_bst)
    for e in changed_buses:
        # если поменялась остановка, а она точно
        # поменялась тк changed_buses содержит только поменяные
        if e.busstop_nearest and \
           e.busstop_prev and \
           e.busstop_nearest.order - e.busstop_prev.order == 1 and \
           e.busstop_nearest.direction == e.busstop_prev.direction:
            dsecs = int(
                (e.timestamp - cb_last_changed[e.uniqueid]).total_seconds())
            if dsecs < 60 * 20:  # cut off the shits > 20 minutes
                cc_key = "%s_%s" % (
                    e.busstop_prev.busstop_id, e.busstop_nearest.busstop_id)
                prev = timer_bst.get(cc_key, [])
                prev.append(dsecs)
                timer_bst[cc_key] = prev[-10:]  # last 10 values
                # print cc_key, prev[-5:]
    #cache.set("timer_bst_%s" % city.id, timer_bst)
    pi = pickle_dumps(timer_bst)
    REDIS.set("timer_bst_%s" % city.id, pi)
    #time_bst = cache.get("time_bst_%s" % city.id, {})
    time_bst = REDIS.get("time_bst_%s" % city.id)
    if not time_bst:
        time_bst = {}
    else:
        time_bst = pickle.loads(time_bst)
    allbuses = Bus.objects.filter(active=True, city=city)
    for bus in allbuses:
        cc_key = "busstops_%s" % bus.id
        bstops = cache.get(cc_key)
        if not bstops:
            bstops = Route.objects.filter(bus=bus).order_by('direction',
                                                            'order').select_related('busstop')
            cache.set(cc_key, bstops, 60 * 60 * 24)
        bst_prev, btime = None, None
        if not time_bst.get(bus.id):
            time_bst[bus.id] = {}
        for bst in bstops:
            if bst_prev:
                cc_key = "%s_%s" % (bst_prev.busstop_id, bst.busstop_id)
                secs = timer_bst.get(cc_key)
                if secs:
                    secs = sum(secs) / len(secs)
            else:
                secs = None
            stime = ""
            if bdata_mode0.get(bus.id) and bst.id in bdata_mode0[bus.id][bst.direction]['stops']:
                btime = now
                time_bst[bus.id][bst.id] = ""
            elif btime and secs:
                btime += datetime.timedelta(seconds=secs)
                stime = "%02d:%02d" % (btime.hour, btime.minute)
                time_bst[bus.id][bst.id] = stime
                bdata_mode3_entry = {
                    "bid": bus.id, "n": str(bus), "t": btime.replace(second=0, microsecond=0)}
                if bdata_mode3.get(bst.busstop_id):
                    bdata_mode3[bst.busstop_id].append(bdata_mode3_entry)
                else:
                    bdata_mode3[bst.busstop_id] = [bdata_mode3_entry]
            else:
                btime = None
                time_bst[bus.id][bst.id] = ""
            bst_prev = bst
    #cache.set("time_bst_%s" % city.id, time_bst, 15 * 60)
    pi = pickle_dumps(time_bst)
    REDIS.set("time_bst_%s" % city.id, pi, 60 * 15)

    #cache.set("bdata_mode3_%s" % city.id, bdata_mode3, 60 * 10)
    pi = pickle_dumps(bdata_mode3)
    REDIS.set("bdata_mode3_%s" % city.id, pi, ex=60 * 10)
    pi = pickle_dumps(bdata_mode3)
    sock.send("bdata_mode3_%s %s" % (city.id, pi))

    took_seconds = (datetime.datetime.now()-start_time).total_seconds()
    logger.info("update city %2d: done, took=%.2f seconds" % (city.id, took_seconds))
    stats = backoffice_statlos()
    if not stats.get('last_updates'):
        stats['last_updates'] = {}
    stats['last_updates'][city.id] = (now, len(events))
    backoffice_statlos(data=stats)
    # yappi.get_func_stats().print_all(columns={0:("name",70), 1:("ncall", 5), 2:("tsub", 8), 3:("ttot", 8), 4:("tavg",8)})
    return len(events)
