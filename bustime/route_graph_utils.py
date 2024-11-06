import networkx as nx
from functools import partial
from django.db.models import Q
from bustime.models import distance_meters, Route, RouteNode, get_busstop_points, NBusStop, REDIS, pickle_dumps
from bustime.utils import get_paths_from_busstops


def get_detector_data_multi(city):
    distance_limit = 600
    TICKET_PRICE = 23

    # Функция фильтрации ближайших остановок по радиусу
    def nearest_radius_filter(item, head):
        didi = distance_meters(head[1][0], head[1][1], item[1][0], item[1][1])
        return didi < distance_limit

    # Функция фильтрации ближайших остановок по расстояниям из GraphHopper
    def nearest_busstops_filter(item, head, paths):
        path = paths[f"{head[0]}_{item[0]}"]
        didi = path['distance']
        return didi < distance_limit

    # Функция обсчета расстояний между остановок через GraphHopper
    def create_busstops_distances(head, item):
        stops = [
            {'point': [head[1][0], head[1][1]]},
            {'point': [item[1][0], item[1][1]]}
        ]
        path = get_paths_from_busstops(stops, 'foot')[0]
        return (f"{head[0]}_{item[0]}", path)

    # формирования графа для поиска проезда с пересадками
    all_routes = Route.objects.filter(bus__city=city, bus__active=True).select_related('busstop')
    all_routes = all_routes.order_by('bus', 'direction', 'order')
    G = nx.DiGraph()
    processed = set()
    for r in all_routes:
        bus_dir_id = hex(r.bus.id << 4 | r.direction)
        if bus_dir_id not in processed:
            # print('создаем маршрут для %s' % r.bus)
            buf = r
            first = True
            processed.add(bus_dir_id)
            continue

        src = RouteNode(buf.id, buf.busstop.id, buf.busstop.name, buf.direction, buf.bus.id)
        dst = RouteNode(r.id, r.busstop.id, r.busstop.name, r.direction, r.bus.id)
        G.add_edge(src, dst,  weight=1, walk_weight=1)

        # формируем точки входа и выхода, вход платный, выход бесплатный
        if first: # для первой позаботимся о buf
            G.add_edge(r.busstop.name, src, weight=TICKET_PRICE, walk_weight=TICKET_PRICE) # вход
            G.add_edge(src, r.busstop.name, weight=0, walk_weight=0) # выход
            first = False
        G.add_edge(r.busstop.name, src, weight=TICKET_PRICE, walk_weight=TICKET_PRICE) # вход
        G.add_edge(dst, r.busstop.name, weight=0, walk_weight=0) # выход
        buf = r

    # Формируем переходы между остановками, которые расположены рядом (Рядом это меньше переменной distance_limit)
    head, *tail = get_busstop_points(city).items()
    while tail:
        items = filter(partial(nearest_radius_filter, head=head), tail)
        # items_by_radius = filter(partial(nearest_radius_filter, head=head), tail)
        # path_map = dict(map(partial(create_busstops_distances, head), items_by_radius))
        # items = filter(partial(nearest_busstops_filter, head=head, paths=path_map), items_by_radius)
        for item in items:
            didi = distance_meters(head[1][0], head[1][1], item[1][0], item[1][1])
            # didi = path_map[f"{head[0]}_{item[0]}"]["distance"]
            # print(didi)
            busstops = NBusStop.objects.filter(Q(id=head[0]) | Q(id=item[0]))
            if busstops[0].name != busstops[1].name:
                # Добавляем переход между остановками. Стоимость перехода (20м = 1балл) и (40м = 1балл)
                G.add_edge(busstops[0].name, busstops[1].name, weight=didi / 20, walk_weight=didi / 40)
        head, *tail = tail
    return G


def update_city_route_graph(city):
    if city.available and city.active:
        print("Считаем маршруты %s" % city.name)
        # почему здесь нельзя было rcache_set использовать?
        REDIS_W.set("nx__di_graph__%s" % city.id, pickle_dumps(get_detector_data_multi(city)))
    else:
        print("Город %s не активен" % city.name)
