#!/usr/bin/env python
# -*- coding: utf-8 -*-

from devinclude import *
from bustime.models import *
import graph_tool as gt
import functools
from graph_tool import topology as gt_tpl


_DISTANCE_LIMIT = 1000
_STATION_WAITING_TIME = 600  # 10min
_TICKET_COST = 300
_METER_PER_SECONDS = {
    "bus": 7,  # 10,  # 10 m/s average bus speed
    "metro": 20,
    "foot": 1  # 1 m/s average walking speed
}
_CO2_BUS_COST = 15 #kg
_CO2_TRAM_COST = 1 #kg
_CO2_WALK_COST = 5


def _get_busstops_query():
    return "SELECT bn.id, bn.name, 'busstop' AS type, ST_X(bn.point) AS x, ST_Y(bn.point) AS y " \
           "FROM bustime_nbusstop bn WHERE bn.id IN %s"


def _get_unistops_query():
    return "SELECT un.id, un.name, 'unistop' AS type, ST_X(un.centroid) AS x, ST_Y(un.centroid) AS y " \
           "FROM bustime_unistop un WHERE un.id IN %s"


def _get_routes_query():
    return "SELECT br.id, br.bus_id, br.direction, bn.id AS stop_id, bn.name as stop_name, " \
           "ST_X(bn.point) AS x, ST_Y(bn.point) AS y, bb.name as bus_name, 'route' AS type " \
           "FROM bustime_route br " \
           "INNER JOIN bustime_nbusstop bn ON br.busstop_id = bn.id " \
           "INNER JOIN bustime_bus bb ON br.bus_id = bb.id " \
           "WHERE br.id IN %s"


def _calc_route_seconds(didi, route_type=None) -> int:
    return round(didi / _METER_PER_SECONDS.get(route_type, 0))


def _calc_route_milliseconds(didi, route_type=None) -> int:
    return _seconds_to_millis(round(_calc_route_seconds(didi, route_type)))


def _calc_route_cost(didi, route_type=None) -> int:
    return round(_calc_route_seconds(didi, route_type))


def _seconds_to_millis(seconds) -> int:
    return seconds * 1000


def find_routes_with_times(graph: gt.Graph, from_stop_id, to_stop_id, vprop, mapping_dict):
    """
    Ищет маршруты между остановками и проводит постобработку для отдачи представлению
    graph: Граф маршрутов
    from_stop_id: Идентификатор UniStop отправки
    to_stop_id: Идентификатор UniStop назначения
    Возвращает: Список маршрутов с расстояниями, промежуточными остановками, временем ближайшего автобуса
    """

    def process_path(path, city_now=None):
        head, *tail = path
        while tail:
            index = 0
            collection = []
            item = next((x for x in tail if x['type'] != head['type']), None)
            if item is not None:
                index = tail.index(item)
                collection = list(itertools.chain([head], tail[:index]))
            elif head['name'] != tail[0]['name']:
                collection = list(itertools.chain([head], tail))
            stops = list([{"id": x['id'], "type": x['type'], "point": Point(x['x'], x['y']),
                           "time": x["time"], "distance": x["distance"],
                           "name": x['name'] if x['type'] == 'busstop' or x['type'] == 'unistop' else x['stop_name']}
                          for x in collection])
            if len(stops) > 1:
                cum_times = list(itertools.accumulate(stops, lambda x, y: x + y['time'], initial=0))
                route_item = {'type': "foot" if head['type'] == 'busstop' else "bus",
                              'distance': functools.reduce(lambda x, y: x + y['distance'], stops, 0),
                              'time': functools.reduce(lambda x, y: x + y['time'], stops, 0),
                              'stops': [stop['name'] for stop in stops],
                              'stops_id_for_map': [c['id'] if c['type'] == 'busstop' or c['type'] == 'unistop' else c['stop_id'] for c in collection]}
                if route_item['type'] == "bus" or route_item['type'] == "metro":
                    route_item["bus_id"] = head['bus_id']
                    route_item["direction"] = head['direction']
                    # times_bst_ts = rcache_get("time_bst_ts_%s" % city.id, {}).get(head['bus_id'], {})
                    # time_bst_ts = rcache_get("time_bst_ts_%s" % city.id, {}).get(head['bus_id'], {}).get(head['id'], 0)
                    # time_bst = datetime.fromtimestamp(time_bst_ts).strftime("%H:%M") if time_bst_ts > 0 else ''
                    # route_item["time_bst_ts"] = time_bst_ts
                    # route_item["time_bst"] = time_bst
                yield route_item
                if collection[-1] != tail[-1]:
                    head, tail = tail[index], tail[index + 1:]
                else:
                    break
            else:
                head, *tail = tail

    paths = _find_path(graph, from_stop_id, to_stop_id, vprop, mapping_dict)
    # for p in paths:
        # print("P", paths)
    return [process_path(path) for path in paths]


def _find_path(g: gt.Graph, from_stop_id, to_stop_id, vprop, mapping_dict):
    # time_map = g.edge_properties['time']
    # distance_map = g.edge_properties['distance']
    eweights = g.edge_properties['eweight']
    tweights = g.edge_properties['tweight']
    coweights = g.edge_properties['coweight']
    src = "u_{}".format(from_stop_id)
    dst = "u_{}".format(to_stop_id)
    src_vertex = mapping_dict[src]
    dst_vertex = mapping_dict[dst]
    results = []
    _, result = gt_tpl.shortest_path(g, src_vertex, dst_vertex, weights=eweights)
    results.append(result)
    _, result = gt_tpl.shortest_path(g, src_vertex, dst_vertex, weights=coweights)
    results.append(result)
    _, result = gt_tpl.shortest_path(g, src_vertex, dst_vertex, weights=tweights)
    results.append(result)

    # results = list(gt_tpl.all_shortest_paths(g, src_vertex, dst_vertex, epsilon=1e-8, edges=True, weights=eweights))
    if not results:
        return []
    # Отфильтровываем результат
    # paths = [[vprop[e.target()] for e in path if vprop[e.target()][0] != 'u'] for path in results]

    paths = [[vprop[e.target()] for e in path] for path in results]
    data = []
    stop_ids = set()
    ustop_ids = set()
    route_ids = []
    for path in results:
        r = []
        for e in path:
            if vprop[e.target()][0] == 'n':
                stop_ids.add(int(vprop[e.target()][2:]))
            elif vprop[e.target()][0] == 'r':
                r.append(int(vprop[e.target()][2:]))
            elif vprop[e.target()][0] == 'u':
                ustop_ids.add(int(vprop[e.target()][2:]))
        route_ids.append(r)
    with connection.cursor() as cursor:
        r_ids = tuple(route_id for row in route_ids for route_id in row)
        cursor.execute(_get_routes_query(), (r_ids,))
        route_map = {row['id']: row for row in dictfetchall(cursor)}

        cursor.execute(_get_busstops_query(), (tuple(stop_ids),))
        stop_map = {row['id']: row for row in dictfetchall(cursor)}

        cursor.execute(_get_unistops_query(), (tuple(ustop_ids),))
        ustop_map = {row['id']: row for row in dictfetchall(cursor)}
        for path in paths:
            r = []
            for item in path:
                if int(item[2:]) in stop_ids:
                    r.append(stop_map.get(int(item[2:]))) 
                elif int(item[2:]) in ustop_ids:
                    r.append(ustop_map.get(int(item[2:])))
                else:
                    r.append(route_map.get(int(item[2:])))
            data.append(r)
        dedup = {}
        # dedup = {tuple({route_map[x]['bus_name'] for x in r}): d for r, d in zip(route_ids, data)}
        for r, d in zip(route_ids, data):
            dedup[tuple({route_map[x]['bus_name'] for x in r})] = d

        unipaths = dedup.values()
        for path in unipaths:
            head, *tail = path
            head['time'] = 0
            head['distance'] = 0
            while tail:
                didi = distance_meters(head['x'], head['y'], tail[0]['x'], tail[0]['y'])
                if head['type'] == 'route' and tail[0]['type'] == 'route':
                    ttime = _calc_route_milliseconds(didi, "bus")
                else:
                    ttime = _calc_route_milliseconds(didi, "foot")
                tail[0]['time'] = ttime
                tail[0]['distance'] = didi
                head, *tail = tail
    return unipaths

# vertex_colors = {'r':"red", 'u':"yellow", 'n':"green"}

def create_graph():
    g = gt.Graph(directed=True)
    eweight = g.new_ep("int")
    tweight = g.new_ep("int")
    coweight = g.new_ep("int")
    # edge_color_map = g.new_ep("int")
    # vertex_color_map = g.new_vp("string")

    processed = set()
    cnt = 0

    print('start', datetime.datetime.now())
    # all_routes = Route.objects.filter(bus__active=True).order_by('bus', 'direction', 'order').values_list("id", "bus_id", "busstop_id", "direction", 'order', "busstop__unistop")
    with connection.cursor() as cursor:
        cursor.execute("""SELECT br.id as rid, br.bus_id as bus, br.busstop_id as busstop, br.direction, br.order, bn.unistop_id as unistop, ST_X(bn.point) as x, ST_Y(bn.point) as y, bb.ttype FROM bustime_route br 
                    INNER JOIN bustime_nbusstop bn ON br.busstop_id = bn.id INNER JOIN bustime_bus bb ON br.bus_id = bb.id WHERE bb.active = TRUE ORDER BY br.bus_id, br.direction, br.order""")
        all_routes = cursor.fetchall()

    with connection.cursor() as cursor:
        cursor.execute("""SELECT bn.id AS bid, bn.name, ST_X(bn.point) AS x, ST_Y(bn.point) AS y, bn.ttype FROM bustime_nbusstop bn""")
        all_stops = dictfetchall(cursor, True)

    # all_buses = Bus.objects.filter(active=True, city_id=3).order_by('id').values_list('id')
    # stops = NBusStop.objects.all().values_list("id", "name", "unistop")
    # all_routes = Route.objects.filter(bus__active=True).order_by('bus', 'direction', 'order').select_related('busstop')
    print('django orm done', datetime.datetime.now())
    edge_list = set()
    eggs={}
    # for i in range(100):
    tic = time.perf_counter()
    if not REDIS.zcard("geo_stops"):
        print("Filling geo_stops...")
        fill_stops_geospatial()
    pipe = REDIS.pipeline()
    geo_keys = []
    print("Calculating nearest stops...")
    for rid,bus,busstop,direction,order,unistop,x,y,ttype in all_routes:
        if not eggs.get(busstop):
            eggs[ busstop ] = []
            try:
                pipe.georadius(name="geo_stops", longitude=x, latitude=y, radius=_DISTANCE_LIMIT, unit='m')
                geo_keys.append((x, y))
            except Exception as e:
                stop_ids = []
                print(traceback.format_exception(e))
        eggs[ busstop ].append(bus)

    eggs={}
    stops_by_radius = {k: p for k, p in zip(geo_keys, pipe.execute())}
    # step = int(int(0xFFFFFF)/len(all_buses))
    # bid_map = {bid:idx for idx,(bid,) in enumerate(all_buses)}
    for rid,bus,busstop,direction,order,unistop,x,y,ttype in all_routes:
        bus_dir_id = hex(bus << 4 | direction)
        if not eggs.get(busstop):
            eggs[ busstop ] = []
            edge_list.add((f"u_{unistop}", f"n_{busstop}", 1, 1, 1))
            edge_list.add((f"n_{busstop}", f"u_{unistop}", 1, 1, 1))
            try:
                stop_ids = stops_by_radius[(x, y)]
                for near_stop in stop_ids:
                    if busstop != int(near_stop):
                        data = all_stops[int(near_stop)]
                        if x != data['x'] and y != data['y']:
                            didi = distance_meters(x, y, data['x'], data['y'])
                        else:
                            didi = 0
                        if didi < 0:
                            raise ValueError(f"Distance between stops is Negative {x}, {y}, {data['x']}, {data['y']}")
                        route_cost = _calc_route_cost(didi, "foot") if didi > 1 else 1
                        edge_list.add((f"n_{busstop}", f"n_{int(near_stop)}", 5, route_cost, _CO2_WALK_COST))
            except Exception as e:
                stop_ids = []
                print(traceback.format_exception(e))
        eggs[ busstop ].append(bus)
        if bus_dir_id not in processed:
                if cnt%1000==0: print('%s: создаем маршрут для %s' % (cnt,bus))
                buf = [rid,bus,busstop,direction,order,unistop,x,y,ttype]
                first = True
                processed.add(bus_dir_id)
                continue
        src = f"r_{buf[0]}"
        dst = f"r_{rid}"
        if buf[6] != x and buf[7] != y:
            didi = distance_meters(buf[6], buf[7], x, y)
        else:
            # print(f"Routes {buf[0]}, {rid} has equal coordinates")
            didi = 0

        co_cost = _CO2_BUS_COST if ttype == TType.BUS or ttype == TType.SHUTTLE_BUS or ttype == TType.INTERCITY else _CO2_TRAM_COST
        route_cost = _calc_route_cost(didi, "bus") if didi > 1 else 1
        # edge_color = "#%06X" % (0xFFFFFF&(step*bus))
        # edge_color = 0xFFFFFF&(step*bid_map[bus])
        edge_list.add((src, dst, 1, route_cost, co_cost))

        if first:
            # cost = _BUS_COST if ttype == TType.BUS or ttype == TType.SHUTTLE_BUS or ttype == TType.INTERCITY else _TRAMWAY_COST
            edge_list.add((f"u_{unistop}", src, _TICKET_COST, _STATION_WAITING_TIME, 1))
            edge_list.add((src, f"u_{unistop}", 1, 1, 1))
            first = False

        edge_list.add((f"u_{unistop}", dst, _TICKET_COST, _STATION_WAITING_TIME, 1))
        edge_list.add((dst, f"u_{unistop}", 1, 1, 1))

        buf = [rid,bus,busstop,direction,order,unistop,x,y,ttype]
        cnt+=1
    print(f"Edges has filled {time.perf_counter()-tic:0.4}")

    print('list loaded', datetime.datetime.now())
    # vprop = g.add_edge_list(edge_list, eprops=[eweight, tweight, distance_map, time_map], hashed=True)
    vprop = g.add_edge_list(edge_list, eprops=[eweight, tweight, coweight], hashed=True)

    mapping_dict = {vprop[i]: i for i in range(g.num_vertices())}
    # for i in range(g.num_vertices()):
        # vertex_color_map[i] = vertex_colors[vprop[i][0]]

    g.edge_properties['eweight'] = eweight
    g.edge_properties['tweight'] = tweight
    g.edge_properties['coweight'] = coweight
    # g.edge_properties['distance'] = distance_map
    # g.edge_properties['time'] = time_map
    print('Graph ready', g, datetime.datetime.now())

    return g, vprop, mapping_dict


if __name__ == "__main__":
    g, vprop, mapping_dict = create_graph()
    # gt_drw.graph_draw(g, vertex_text=vprop, vertex_fill_color=vertex_color_map, edge_color=edge_color_map, output_size=(4000,4000),output="/home/skincat/routes-graph.pdf")
    tic = time.perf_counter()
    # kalip = _find_path_k(g, 33521, 104470)
    # kalip = gt_tpl.shortest_path(g, mapping_dict["u_33521"], mapping_dict["u_104470"])

    # kalip = list(gt_tpl.all_shortest_paths(g, mapping_dict['u_33521'], mapping_dict['u_104470'], weights=eweight, epsilon=1e-3))
    # result = _find_path(g, 45546, 104470, vprop, mapping_dict)
    # result = _find_path(g, 45546, 39551, vprop, mapping_dict)
    # result = find_routes_with_times(g, 45546, 39551, vprop, mapping_dict)
    # result = find_routes_with_times(g, 45546, 104470, vprop, mapping_dict)
    # result = _find_path(g, 35153, 105875, vprop, mapping_dict)
    # result = find_routes_with_times(g, 35153, 105875, vprop, mapping_dict)
    result = find_routes_with_times(g, 39906, 109191, vprop, mapping_dict)
    # result = find_routes_with_times(g, 33622, 30556, vprop, mapping_dict)
    # result = _find_path(g, 33622, 30556, vprop, mapping_dict)

    toc = time.perf_counter()
    # print(result)
    for r in result:
        print(list(r))
    print(f"Search path {toc-tic:0.4}")
    # kalip = gt.shortest_path(g, mapping_dict['u_33521'], mapping_dict['u_39551'], weights=eweight)
    cnt = 0 
    # print("kalip", kalip)
    # for path in kalip:
    #     for v in path:
    #         if vprop[v][0] == 'n':
    #             nb = NBusStop.objects.get(id=int(vprop[v][3:]))
    #             print('%s' % nb.name)
    #         elif vprop[v][0] != 'n' and vprop[v][0] != 'u':
    #             nbusstop, dir, bus = str(vprop[v]).split("_")
    #             nb = NBusStop.objects.get(id=int(nbusstop))
    #             direction = int(dir)
    #             bus = bus_get(int(bus))
    #             print("%s %s(%s) -> " % (nb.name, bus, direction), end='')

    # for vertex in kalip:
    #     print(cnt, [vprop[v] for v in vertex])
    #     cnt+=1
