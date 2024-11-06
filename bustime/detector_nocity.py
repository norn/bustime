# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function
from networkx import DiGraph

from bustime.models import *
import networkx as nx
import itertools
import operator
from collections import Counter
from six.moves import range
from six.moves import zip
from typing import Optional

DIRECTION_BUFFER_SIZE = 7

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
        '''
        если падает здесь, то обновите кэш:
        ./0shell
        from bustime.models import *
        city = CITY_MAPN[u'Южно-Сахалинск']
        get_busstop_points(city, force=True)

        и перезапустите windmill:
        sudo supervisorctl restart windmills:windmill_81
        или:
        sudo supervisorctl restart windmills:*
        '''
        # попытка автоматизации
        if not DD['BUSSTOPS_POINTS'].get(r.busstop_id):
            DD['BUSSTOPS_POINTS'] = dd_stops_get(bus.id, force=True)
            print("#######################")
            print("ERROR: outdated busstop cache!")
            print("see bustime/detector.py")
            print("#######################")
            #sys.exit()
            return None

        rbp_x, rbp_y = DD['BUSSTOPS_POINTS'][r.busstop_id]  # r.busstop.point
        didi = distance_meters(x, y, rbp_x, rbp_y)
        if didi < distance_limit:
            cands[r.direction][r.id] = didi
    cands[0] = sorted(list(cands[0].items()), key=operator.itemgetter(1))
    cands[1] = sorted(list(cands[1].items()), key=operator.itemgetter(1))
    cands = cands[0][:clim] + cands[1][:clim]

    return dict(cands)

def dot(x, y):
    return sum(x_i*y_i for x_i, y_i in zip(x, y))

def vector_length(dir_x, dir_y):
    return math.sqrt(dir_x * dir_x + dir_y * dir_y)

def normalize(dir_x, dir_y):
    length = vector_length(dir_x, dir_y)
    if (length <= 0.0):
        x, y = 1.0, 0.0
    else:
        x, y = dir_x / length, dir_y / length
    return x, y

def is_unidirectional(stop1, stop2, x_prev, y_prev, x, y, DD):
    if not stop1 or not stop2:
        return False
    r1 = DD['R'][stop1]
    rbp_x1, rbp_y1 = DD['BUSSTOPS_POINTS'][r1.busstop_id]
    r2 = DD['R'][stop2]
    rbp_x2, rbp_y2 = DD['BUSSTOPS_POINTS'][r2.busstop_id]
    dir1_x, dir1_y = normalize(rbp_x2 - rbp_x1, rbp_y2 - rbp_y1)
    dir2_x, dir2_y = normalize(x - x_prev, y - y_prev)
    product = dot([dir1_x, dir1_y], [dir2_x, dir2_y])
    # print("PRODUCT: %s" % product)
    return product > 0.2

def projection(v1_x, v1_y, v2_x, v2_y, p_x, p_y):
    v = [v2_x - v1_x, v2_y - v1_y]
    u = [p_x - v1_x, p_y - v1_y]
    dp = dot(v, u)
    if dp == 0:
        return p_x, p_y
    len1 = float(u[0] * u[0] + u[1] * u[1])
    len2 = float(v[0] * v[0] + v[1] * v[1])
    proj_x = v1_x + (dp * v[0]) / len2
    proj_y = v1_y + (dp * v[1]) / len2    
    # print("LENPROJ [%8.8f] ===PROJ [%s, %s]===" % (len1, proj_x, proj_y))
    return proj_x, proj_y

def cand_chooser(bus, candidates, nearest_now, weights={}, nearest_prev=None, DEBUG=None, DD=None):
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
            weight = weights.get(c, 1)
            if (nearest_now[c] * weight) < closest[1] * weight:
                warn = False
                closest = [c, nearest_now[c]]
    if warn:
        if DEBUG:
            print("WARN")
        return [None, None]

    return closest

def stopbuses_paths(G, source, target):
    return list(itertools.islice(nx.shortest_simple_paths(G, source, target), 1))

def find_point(x1, y1, x2,  
              y2, x, y) : 
    if (x > x1 and x < x2 and 
        y > y1 and y < y2) : 
        return True
    else : 
        return False

def is_between_stops(x, y, stop_min, stop_max, DEBUG=None, DD=None):
    thickness = 0.00024
    r = DD['R'][stop_min]
    rbp_x1, rbp_y1 = DD['BUSSTOPS_POINTS'][r.busstop_id]
    r = DD['R'][stop_max]
    rbp_x2, rbp_y2 = DD['BUSSTOPS_POINTS'][r.busstop_id]
    dir_x, dir_y = rbp_x2 - rbp_x1, rbp_y2 - rbp_y1
    dir_x, dir_y = normalize(dir_x, dir_y)
    dir_x, dir_y = dir_x * thickness, dir_y * thickness
    n1_x, n1_y = -dir_y, dir_x
    n2_x, n2_y = dir_y, -dir_x
    # dist = distance_meters(n1_x, n1_y, n2_x, n2_y)
    x1 = rbp_x1 + n1_x
    y1 = rbp_y1 + n1_y
    x2 = rbp_x2 + n2_x
    y2 = rbp_y2 + n2_y
    p1 = x1 if x1 <= x2 else x2
    p2 = y1 if y1 <= y2 else y2
    p3 = x2 if x2 > x1 else x1
    p4 = y2 if y2 > y1 else y1
    rect = (p1, p2, p3, p4)
    if DEBUG:
        print(("X %s Y %s" % (x, y)))
        print(("First %s [%s, %s]" % (stop_min, rbp_x1, rbp_y1)))
        print(("Second %s [%s, %s]" % (stop_max, rbp_x2, rbp_y2)))
        print(("RECT %s", rect))
    return find_point(rect[0], rect[1], rect[2], rect[3], x, y)

def find_between_stop(x, y, bus, candidates, DEBUG=None, DD=None):
    for stop in candidates:
        r = DD['R'][stop]
        route_graph = DD['ROUTES_NG'][bus.id][r.direction]

        next_stops = route_graph.successors(stop)
        if not next_stops: 
            continue 
        print(("STOP %s" % stop))
        result = is_between_stops(x, y, stop, next_stops[0], DEBUG, DD)
        if result:
            return [stop, next_stops[0]]
    return []

def nearest_info(x, y, x_prev, y_prev, path_delta, stop, nearest_was, nearest_now, DD):
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
    delta = v
    fx = abs(v)/float(path_delta)
    return delta, fx
#calc_nearest_info

def most_frequent(data): 
    return max(set(data), key = data.count) 

def rcache_direction_get(rcache_direction, uniqueid, DEBUG=False):
    if not rcache_direction.get(uniqueid):
        llen = 0
    else:
        llen = len(rcache_direction[uniqueid])
    if llen >= DIRECTION_BUFFER_SIZE:    
        data = list(filter(lambda x: x is not None, rcache_direction[uniqueid]))
        if DEBUG: print(("Bus %s[%s] directions %s" % (bus.name, uniqueid, data)))
        return most_frequent(data)
    return None

def rcache_direction_set(rcache_direction, uniqueid, direction):
    if type(rcache_direction.get(uniqueid)) == list:
        rcache_direction[uniqueid].append(direction)
    else:
        rcache_direction[uniqueid] = [direction]
    while len(rcache_direction[uniqueid]) > DIRECTION_BUFFER_SIZE:
        rcache_direction[uniqueid].pop(0)

def rcache_direction_clear(rcache_direction, uniqueid):
    if rcache_direction.get(uniqueid):
        rcache_direction[uniqueid].clear()


def get_closest_candidate(bus, candidates, nearest_now, nearest_prev, weights, DEBUG, DD):
    closest = [None, None]
    if nearest_prev:
        closest = cand_chooser(bus, candidates, nearest_now, weights, nearest_prev=nearest_prev, DEBUG=DEBUG, DD=DD)
    # попытка взять ближайшую без nearest_prev, это важно
    if closest[0] == None:
        closest = cand_chooser(bus, candidates, nearest_now, weights, DEBUG=DEBUG, DD=DD)
        if closest[0] == None:
            return None
    return closest[0]

def ng_detector(bus, x_prev, y_prev, x, y, DEBUG=False, nearest_prev=None, uniqueid:Optional[int] = None, DD=None, rcache_direction={}):
    """
    return id of the route object with nearest busstop
    """
    if not x_prev or not x or not bus:
        return None
    di_out, di_in = [], []
    if DEBUG: print("BUS: %s X: %s Y: %s X_PREV: %s Y_PREV: %s" % (bus.id, x, y, x_prev, y_prev))
    # определим ближайшие
    nearest_was = nearest_busstops(bus, x_prev, y_prev, DD=DD)
    nearest_now = nearest_busstops(bus, x, y, DD=DD)
    if not nearest_now or not nearest_was:
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
        route_graph = DD['ROUTES_NG'][bus.id][r.direction]
        next_stops = [] if not route_graph.has_node(stop) else list(route_graph.successors(stop))
        prev_stops = [] if not route_graph.has_node(stop) else list(route_graph.predecessors(stop))
        next_stop = None if not next_stops else next_stops[0]
        prev_stop = None if not prev_stops else prev_stops[0]
        if next_stop or prev_stop:
            if not is_unidirectional(stop, next_stop, x_prev, y_prev, x, y, DD) and \
                    not is_unidirectional(prev_stop, stop, x_prev, y_prev, x, y, DD):
                continue
        delta, fx = nearest_info(x, y, x_prev, y_prev, path_delta, stop, nearest_was, nearest_now, DD=DD)
        nearest_delta[stop] = delta
        nearest_fx[stop] = fx
        if nearest_fx[stop] < 0.333:
            if DEBUG:
                print("skipped fx=%s, %s" % (nearest_fx[stop], r.busstop.name))
            continue
        if delta < 0:
            di_in.append(r.id)
        else:
            di_out.append(r.id)
        if DEBUG:
            print("v=%5d, fx=%.3f %s" % (delta, nearest_fx[stop], r.busstop.name))

    if DEBUG:
        print("\ndi_in:", di_in)
        print("di_out:", di_out)

    # узнаем истину
    cdists = {}
    orders = {}
    candidates = []
    orders_was = {}
    candidates_was = []
    cc_key = "detector_bus_%s" % bus.id
    common_dir = False if not uniqueid else rcache_direction_get(rcache_direction, uniqueid, DEBUG)
    for di_from in di_out:
        for di_to in di_in:
            for dir_ in [0, 1]:
                if DD['ROUTES_NG'][bus.id][dir_].has_node(di_from) and \
                        DD['ROUTES_NG'][bus.id][dir_].has_node(di_to) and \
                        nx.has_path(DD['ROUTES_NG'][bus.id][dir_], di_from, di_to):
                    # print("F: %s, T: %s" % (di_from, di_to))
                    if di_to not in candidates:
                        r = DD['R'][di_to]
                        # if not common_dir or r.direction == common_dir:
                        orders[r.order] = di_to
                        candidates.append(di_to)
                    if di_from not in candidates_was:
                        r = DD['R'][di_from]
                        # if not common_dir or r.direction == common_dir:
                        orders[r.order] = di_to
                        candidates.append(di_to)
                        orders_was[r.order] = di_from
                        candidates_was.append(di_from)

    if not candidates:
        return None

    is_loop = False
    if len(candidates_was) > 0 and len(orders_was) > 0:        
        # ===== NEW ===== #
        weights = {}
        min_stop_order = min(orders)
        max_stop_order = max(orders_was)
        r_min = DD['R'][orders[min_stop_order]]
        r_max = DD['R'][orders_was[max_stop_order]]
        is_loop = min(orders) - max(orders_was) > 1
        if is_loop and r_min.direction == r_max.direction:
            stop_min = orders_was[max(orders_was)]
            stop_max = orders[min(orders)]
            r = DD['R'][stop_min]
            rbp1_x, rbp1_y = DD['BUSSTOPS_POINTS'][r.busstop_id]
            r = DD['R'][stop_max]
            rbp2_x, rbp2_y = DD['BUSSTOPS_POINTS'][r.busstop_id]
            route_graph = DD['ROUTES_NG'][bus.id][r.direction]
            paths = stopbuses_paths(route_graph, stop_min, stop_max)[0]
            # print("=====================", stop_min, stop_max)
            for stop in paths:
                r = DD['R'][stop]
                rbp_x, rbp_y = DD['BUSSTOPS_POINTS'][r.busstop_id]
                proj_x, proj_y = projection(rbp1_x, rbp1_y, rbp2_x, rbp2_y, rbp_x, rbp_y)
                didi = distance_meters(x, y, proj_x, proj_y)
                # print("DIDI %s\n=====================" % (didi))
                if stop not in candidates and stop not in candidates_was:
                    delta, fx = nearest_info(x, y, x_prev, y_prev, path_delta, stop, nearest_was, nearest_now, DD=DD)
                    nearest_delta[stop] = delta
                    nearest_fx[stop] = fx
                if stop not in candidates:
                    candidates.append(stop)
                if stop not in candidates_was:
                    candidates_was.append(stop)

                # 31.03.20
                float_nearest_now_stop = float(nearest_now[stop])
                float_didi = float(didi)
                if float_nearest_now_stop == 0:
                    weights[stop] = 1
                else:
                    weights[stop] = float_didi / float_nearest_now_stop  # 31.03.20 ZeroDivisionError: float division by zero
        # elif r_min.direction != r_max.direction:

        # ===== NEW ===== #

    if DEBUG:
        print("\nCandidates:", candidates)
        for c in candidates:
            r = DD['R'][c]
            print(" - %s [%sm (%sm, fx%s, ord=%s)] %s " % (c, nearest_now[c], nearest_delta[c], nearest_fx[c], r.order, r))
        print("\nCandidates Was:", candidates_was)
        for c in candidates_was:
            r = DD['R'][c]
            print(" - %s [%sm (%sm, fx%s, ord=%s)] %s " % (c, nearest_was[c], nearest_delta[c], nearest_fx[c], r.order, r))



    # сделать проверку чтобы точка, к приближение к финально точке было
    # как минимум в 2 раза больше чем приближение к другим точкам?    
    closest = get_closest_candidate(bus, candidates, nearest_now, nearest_prev, weights, DEBUG, DD)
    if closest == None: 
        return None

    el_heroe = DD['R'][closest]

    if el_heroe and uniqueid:
        route_graph = DD['ROUTES_NG'][bus.id][el_heroe.direction]
        prev_stops = list(route_graph.predecessors(el_heroe.id))
        if (len(prev_stops) > 0):
            prev_stops = list(route_graph.predecessors(prev_stops[0]))
        rcache_direction_set(rcache_direction, uniqueid, el_heroe.direction)
        if not prev_stops:
            rcache_direction_clear(rcache_direction, uniqueid)
        elif common_dir and el_heroe.direction != common_dir:
            #print(("REDIRECT %s %d %d PREV %s, %s" % (uniqueid, el_heroe.direction, common_dir, prev_stops, el_heroe.id)))
            candidates = [c for c in candidates if DD['R'][c].direction == common_dir]
            candidates_was = [c for c in candidates_was if DD['R'][c].direction == common_dir]
            closest = get_closest_candidate(bus, candidates, nearest_now, nearest_prev, weights, DEBUG, DD)
            if closest == None: 
                return None
            el_heroe = DD['R'][closest]

    if is_loop:
        closest_was = cand_chooser(bus, candidates_was, nearest_was, {}, nearest_prev=nearest_prev, DEBUG=DEBUG, DD=DD)
        if DEBUG:
            print("Closest candidate was is: ", str(closest_was))
        if closest_was[0] and closest[0] - closest_was[0] > 1:
            return None

    if DEBUG:
        print("Closest candidate is: ", closest, el_heroe.order)
        if nearest_prev:
            print("nearest_prev: %s" % nearest_prev, nearest_prev.order)

    return el_heroe
