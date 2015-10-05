# -*- coding: utf-8 -*-
from bustime.models import *
import networkx as nx


ROUTES, ROUTES_NG, ROUTE_CACHE = {}, {}, {}
all_routes = Route.objects.select_related('busstop')
all_routes = all_routes.order_by('bus', 'direction', 'order')
for r in all_routes:
    ROUTE_CACHE[r.id] = r
    if ROUTES.get(r.bus_id):
        ROUTES[r.bus_id].append(r)
    else:
        ROUTES[r.bus_id] = [r]

    if not ROUTES_NG.get(r.bus_id):
        ROUTES_NG[r.bus_id] = {0: nx.DiGraph(), 1: nx.DiGraph()}
        buf = None
    if buf:
        ROUTES_NG[r.bus_id][r.direction].add_edge(buf.id, r.id)
    buf = r


def ng_nearest_busstops(bus, pnt_x, pnt_y):
    """
    return list of the nearest busstops according to this bus
    need to be optimized as much as possible
    """
    candidates = {}  # [busstop]=distance
    for r in ROUTES[bus.id]:
        rbp_x, rbp_y = BUSSTOPS_POINTS[r.busstop_id]  # r.busstop.point
        dis = distance_meters(pnt_x, pnt_y, rbp_x, rbp_y)
        if dis < 700:
            candidates[r.id] = dis
    return candidates


def ng_detector(bus, x_prev, y_prev, x, y, sleeping=False):
    """
    return id of the route object with nearest busstop
    """
    DEBUG = 0
    if not x_prev or not x:
        return None
    nrst_prev = ng_nearest_busstops(bus, x_prev, y_prev)
    nrst_cur = ng_nearest_busstops(bus, x, y)
    di_out, di_in = [], []
    for k, v in nrst_cur.items():
        if nrst_prev.has_key(k):
            # расстояние было больше, стало меньше - приблизились
            if nrst_prev[k] > v:
                di_in.append(k)
            elif nrst_prev[k] < v:  # было меньше, стало больше - удалились
                di_out.append(k)
        # в прошлом остановки вообще не было, значит к этой новой приблизились
        else:
            di_in.append(k)
    for k, v in nrst_prev.items():  # а тут наоборот
        if k not in di_in and k not in di_out:
            di_out.append(k)
    # got lists - coming and leaving
    if DEBUG:
        print ("di_out(leaving): ", di_out)
        for di_from in di_out:
            print (di_from, ROUTE_CACHE[di_from])
        print "di_in(coming): ", di_in
        for di_to in di_in:
            print (di_to, ROUTE_CACHE[di_to])

    candidates = []

    for di_from in di_out:
        for di_to in di_in:
            for dir_ in [0, 1]:
                if ROUTES_NG[bus.id][dir_].has_node(di_from) and \
                        ROUTES_NG[bus.id][dir_].has_node(di_to) and \
                        nx.has_path(ROUTES_NG[bus.id][dir_], di_from, di_to):
                    # num = nx.shortest_path(ROUTES_NG[bus.id][dir_], di_from, di_to)
                    # print di_from, di_to, num
                    candidates.append(di_to)
    # обслужим начало нового маршрута, которое не срабатывает на графах
    for r in ROUTES[bus.id]:
        if r.endpoint and r.order == 0 and r.id in di_in:
            candidates.append(r.id)
    if DEBUG:
        print "Candidates are: %s" % candidates
    candidate = None
    for cand in candidates:
        if DEBUG:
            print cand, ROUTE_CACHE[cand], nrst_cur[cand]
        if not candidate:
            candidate = cand
        elif nrst_cur[cand] < nrst_cur[candidate]:
            candidate = cand
    if DEBUG:
        print "Candidate is: %s" % candidate
    if candidate:
        return ROUTE_CACHE[candidate]
