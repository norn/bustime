# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function
from bustime.models import *
import networkx as nx
import operator


def nearest_busstops(bus, x, y, distance_limit=1200, clim=3, DD=None):
    """
    return list of the nearest busstops of the bus
    need to be optimized as much as possible
    """
    if bus.inter_stops:
        distance_limit = bus.inter_stops
    cands = {0:{}, 1:{}}  # [busstop]=distance
    dd_routes = DD['ROUTES'].get(bus.id)
    if not dd_routes:
        return None
    for r in dd_routes:
        rbp_x, rbp_y = DD['BUSSTOPS_POINTS'][r.busstop_id]  # r.busstop.point
        didi = distance_meters(x, y, rbp_x, rbp_y)
        if didi < distance_limit:
            cands[r.direction][r.id] = didi
    cands[0] = sorted(list(cands[0].items()), key=operator.itemgetter(1))
    cands[1] = sorted(list(cands[1].items()), key=operator.itemgetter(1))
    cands = cands[0][:clim] + cands[1][:clim]

    return dict(cands)


def cand_chooser(bus, candidates, nearest_now, nearest_prev=None, DEBUG=None, DD=None):
    warn = False
    if nearest_prev:
        closest = [None, 999]
        for c in candidates:
            r = DD['R'][c]
            if r.order < closest[1] and \
               r.order >= nearest_prev.order and \
               nearest_prev.direction == r.direction:
                    closest = [c, r.order]
    else:
        closest = [None, 99999]
        alldir = None
        for c in candidates:
            r = DD['R'][c]
            if alldir == None:
                alldir = r.direction
            elif alldir != r.direction:
                warn = True
            if nearest_now[c] < closest[1]:
                closest = [c, nearest_now[c]]

    if warn:
        if DEBUG:
            print("Different directions in candidates")
        el_nearest_now = min(nearest_now, key=nearest_now.get)
        return [el_nearest_now, None]

    return closest


def ng_detector(bus, x_prev, y_prev, x, y, DEBUG=False, nearest_prev=None, DD=None):
    """
    return id of the route object with nearest busstop
    """
    if not x_prev or not x:
        return None
    di_out, di_in = [], []

    # определим ближайшие
    nearest_was = nearest_busstops(bus, x_prev, y_prev, DD=DD)
    nearest_now = nearest_busstops(bus, x, y, DD=DD)
    if not nearest_now and not nearest_was:
        return -1
    path_delta = distance_meters(x_prev, y_prev, x, y)
    nearest_delta, nearest_fx = {}, {}
    if DEBUG:
        print("nearest_was: ", nearest_was)
        print("nearest_now: ", nearest_now)
        print("delta(m) = %.2f\n" % path_delta)
    if path_delta < 15:
        return

    # проведем предварительные вычисления
    # какие покидаем, куда приближаемся
    for stop in set(list(nearest_was.keys())+list(nearest_now.keys())):
        r = DD['R'][stop]
        rbp_x, rbp_y = DD['BUSSTOPS_POINTS'][r.busstop_id]

        dis_prev = nearest_was.get(stop)
        if not dis_prev:
            dis_prev = distance_meters(rbp_x, rbp_y, x_prev, y_prev)
            nearest_was[stop] = dis_prev
        dis_now = nearest_now.get(stop)
        if not dis_now:
            dis_now = distance_meters(rbp_x, rbp_y, x, y)
            nearest_now[stop] = dis_now
        v = dis_now - dis_prev

        nearest_delta[stop] = v
        nearest_fx[stop] = abs(v)/float(path_delta)
        if nearest_fx[stop] < 0.333:
            if DEBUG:
                print("skipped fx=%s, %s" % (nearest_fx[stop], r.busstop.name))
            continue
        if v < 0:
            di_in.append(r.id)
        else:
            di_out.append(r.id)
        if DEBUG:
            print("v=%5d, fx=%.3f %s" % (v, nearest_fx[stop], r.busstop.name))

    if DEBUG:
        print("\ndi_in:", di_in)
        print("di_out:", di_out)

    # узнаем истину
    cdists = {}
    candidates = []
    for di_from in di_out:
        for di_to in di_in:
            for dir_ in [0, 1]:
                if DD['ROUTES_NG'][bus.id][dir_].has_node(di_from) and \
                        DD['ROUTES_NG'][bus.id][dir_].has_node(di_to) and \
                        nx.has_path(DD['ROUTES_NG'][bus.id][dir_], di_from, di_to):
                    if di_to not in candidates:
                        candidates.append(di_to)
    # а если не можем, то берем ближайшую и думаем что мы в домике
    if nearest_now:
        if nearest_prev:
            forward_nearest = {}
            for k, v in nearest_now.items():
                if DD['R'][k].direction == nearest_prev.direction:
                    forward_nearest[k] = v
            if forward_nearest:
                el_nearest_now = min(forward_nearest, key=forward_nearest.get)
                if DEBUG:
                    print("el_nearest forward added:", el_nearest_now)
                candidates.append( el_nearest_now )
        elif not candidates:
            el_nearest_now = min(nearest_now, key=nearest_now.get)
            if DEBUG:
                print("el_nearest backup added:", el_nearest_now)
            candidates.append( el_nearest_now )

    if DEBUG:
        print("\nCandidates:", candidates)
        for c in candidates:
            r = DD['R'][c]
            print(" - %s [%sm (%sm, fx%s, ord=%s)] %s " % (c, nearest_now[c], nearest_delta[c], nearest_fx[c], r.order, r))

    # сделать проверку чтобы точка, к приближение к финально точке было
    # как минимум в 2 раза больше чем приближение к другим точкам?
    if not candidates:
        return None

    closest = [None, None]
    if nearest_prev:
        closest = cand_chooser(bus, candidates, nearest_now, nearest_prev=nearest_prev, DEBUG=DEBUG, DD=DD)
    # попытка взять ближайшую без nearest_prev, это важно
    if closest[0] == None:
        closest = cand_chooser(bus, candidates, nearest_now, DEBUG=DEBUG, DD=DD)
        if closest[0] == None:
            return None

    el_heroe = DD['R'][closest[0]]

    if DEBUG:
        print("Closest candidate is: ", closest, el_heroe.order)
        if nearest_prev:
            print("nearest_prev: %s" % nearest_prev, nearest_prev.order)

    if el_heroe.order == 1:
        # todo check for distance
        idx = DD['ROUTES'][bus.id].index(el_heroe)
        over = DD['ROUTES'][bus.id][idx-1]
        dx, dy = el_heroe.busstop.point.coords
        dist_de_el_heroe = distance_meters(x, y, dx, dy)
        dx, dy = over.busstop.point.coords
        dist_de_el_over =  distance_meters(x, y, dx, dy)
        if dist_de_el_over < dist_de_el_heroe:
            el_heroe = over
            if DEBUG:
                print("Pre-start override.")

    return el_heroe
