#!/mnt/reliable/repos/bustime/bustime/.venv/bin/python
# -*- coding: utf-8 -*-
"""
Импорт сырых gtfs данных в маршруты bustime.loc
Загрузку данных смотри в /r/bustime/bustime/utils/gtfs_loader.py

Запуск:
    python utils/gtfs_importer.py 97 --upd --reset --dedup --debug
    python utils/gtfs_importer.py 97 --upd --reset --reroute --bus 10
    python utils/gtfs_importer.py 1-4 --upd --reset
    python utils/gtfs_importer.py 1,4,6 --reset

Параметры:
    Обязательные:
        ID записи таблицы https://ru.bustime.loc/wiki/bustime/gtfscatalog/
            можно задать в виде числа (N) (0 не сработает),
                                диапазона (N-M),
                                списка (N,M,K...)
    Необязательные:
        --dedup - для формирования команды удаления дубликатов (одноимённые однотипные в одном place) маршрутов (команду выполнять отдельно на f2)
        --reset - для обновления импортированного маршрута в системе (например, на странице - список остановок)
        --upd   - обновлять БД сайта после импорта (аналог кнопки "Обновить БД сайта" в админке города)
        --reroute - принудительно обновить Route/RouteLine
        --bus <name> - импортировать только маршрут с указанным именем (gtfs route_short_name)
        --debug - вывод подробностей

Пояснения:
Данные gtfs выбираться без учета дат, т.е. все существующие маршруты

Несуществующие в городе маршруты добавятся, существующие - сохранят свои ID, но остановки (NBusStop),
связки остановок (Routes), нити (RouteLine) и свойства маршрута (провайдер, длинна, время, description) могут измениться.

Безопасно делать импорт маршрутов в город несколько раз.
Существующие в городе маршруты и остановки не удаляются (кстати, возможно это проблема :).

Без параметра --upd необходимо после импорта в админке города нажать кнопки "Обновить БД сайта" и "Обновить БД приложений",
с параметром - только "Обновить БД приложений" (хотя, ночью само обновится).

После импорта необходимо перезапустить обработчик города, чтобы он увидел изменения в маршрутах.

Принцип работы:
Из gtfs-фида большим sql-запросом выбирается список маршрутов, уникальных по имени + тип маршрута
и для каждого маршрута выбираются самые длинные трипы (трип с макс. кол-вом остановок) для направлений (0/1)
например, из исходного фида:
    route_name  route_id    trip_id  type
    10          r1          t1          0
    10          r2          t2          0
получится выборка:
    route_name  type    route_ids   trip_ids  trip0       trip1
    10          0       [r1,r2]     [t1,t2]   {id, ...} {id, ...}

Из подготовленной выборки gtfs-маршруты записываются в bustime-маршруты
например, для place=242, существующие маршруты (пример с существованием дубликатов из-за прошлых ошибок)
bus.name    bus.id  bus.ttype
10          b1      0           <- первый найденный маршрут обновится данными из выборки (Bus, NBusStop, Routes, RouteLine)
10          b2      0           -> остальные попадут в [список дубликатов] при наличии флага --dedup

По окночанию импорта (при наличии флага --dedup) выведется команда для удаления дубликатов,
которую надо просто скопировать и выполнить (на хосте f2)

Хитрости:
Незаметно для пользователя удалить и снова создать маршруты в городе можно так (33853-Амстердам):
1 удаление всех маршрутов без флага --reset (маршруты останутся в кэше и на странице города):
    utils/bus_mass_delete.py "SELECT bus_id FROM bustime_bus_places WHERE place_id = 33853" --debug
2 импорт маршрутов с флагом --reset (маршруты обновятся в кэше и на странице города):
    python utils/gtfs_importer.py 7 --upd --reset --debug
3 перезапустить turbo_mill & turbo_sync (на f7)
4 перезапустить обработчик каталога gupdaters:gupdater_7 (на f3)

TODO: https://gitlab.com/nornk/bustime/-/issues/3586#note_1992159899
"""
from __future__ import absolute_import
from __future__ import print_function
from devinclude import *
from bustime.models import *    # fill_routeline, fill_order, cache_reset_bus, fill_bus_endpoints
from bustime.views import city_update_v8, city_update_mobile
from django.contrib.gis.geos import Point
from django.db.models import Q, Subquery, Count
from django.db import connections
from psycopg2.extras import NamedTupleCursor # DictCursor: row['field'], NamedTupleCursor: row.field
import argparse
import traceback
import logging
import requests
from typing import NoReturn
import datetime
import time
import json
import subprocess
from django.forms.models import model_to_dict
from bustime.osm_utils import update_bus_places


LOG_FILE = 'gtfs_importer.log'
WORK_DIR = '/bustime/bustime/utils/automato'


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%d-%m-%y %H:%M:%S",
    handlers=[
        logging.FileHandler("%s/%s" % (WORK_DIR, LOG_FILE), 'w'),
        logging.StreamHandler()
    ]
)
logging.addLevelName( logging.WARNING, "\033[1;31m%s\033[1;0m" % logging.getLevelName(logging.WARNING))
logging.addLevelName( logging.ERROR, "\033[1;41m%s\033[1;0m" % logging.getLevelName(logging.ERROR))


class GtfsImporter:

    # Constructor
    def __init__(self, DEBUG=False, channel=None):
        self.channel = channel # имя redis-канала для вывода сообщений
        self.DEBUG = DEBUG or channel != None
        # GTFS_ROUTE_TYPE => TTYPE_CHOICES
        self.ttype = {
            "0": 2,   # "Трамвай",
            "1": 7,   # "Метро",
            "2": 6,   # "Поезд",
            "3": 0,   # "Автобус",
            "4": 4,   # "Водный",
            "11": 1   # "Троллейбус",
        }
        self.start_time = 0
    # __init__


    # для импорта эти функции не нужны, используются для измерения времени операций при отладке
    def timer_start(self) -> NoReturn:
        self.start_time = time.perf_counter()

    def time_print(self, msg: str) -> NoReturn:
        i = time.perf_counter() - self.start_time
        self.publish(f'{msg} duration: {i}')
    # /для импорта эти функции не нужны, используются для измерения времени операций при отладке


    def publish(self, msg: str='', level: str='info') -> None:
        if level == 'info':
            logging.info(msg)
        elif level == 'error':
            logging.error(msg)
        elif level == 'warning':
            logging.warning(msg)
        # else: no log

        if self.channel:
            msg = "<br />".join(msg.split("\n"))
            if level in ['error', 'warning']:
                sio_pub(self.channel, {"element": "import_result", "note": "<span class='ui red text'>%s</span>" % msg})
            else:
                sio_pub(self.channel, {"element": "import_result", "note": msg})
    # publish


    # check the field for equality to the value, assign a value if it is not equal to
    def test_set(self, entity, field_name, value, list_fields=None):
        update = getattr(entity, field_name) != value
        if update:
            setattr(entity, field_name, value)
            if list_fields != None:
                if type(list_fields) == set:
                    list_fields.add(field_name)
                elif type(list_fields) == list and field_name not in list_fields:
                    list_fields.append(field_name)
        return update
    # test_set


    def catalog_filter(self, catalog:str):
        if self.DEBUG: self.publish(f'GtfsCatalog.objects.filter')

        if "-" in catalog:
            fr, to = list(map(int, catalog.split("-")))
            self.publish(f'Import catalogs from {fr} to {to} ids')
            catalogs = GtfsCatalog.objects.filter(id__range=(fr, to), active=True)
        elif "," in catalog:
            fr = list(map(int, catalog.split(",")))
            self.publish(f'Import catalogs {catalog} ids')
            catalogs = GtfsCatalog.objects.filter(id__in=fr, active=True)
        elif int(catalog) > 0:
            self.publish(f'Import catalog {catalog}')
            catalogs = GtfsCatalog.objects.filter(id=int(catalog))
        elif int(catalog) == 0:
            self.publish(f'Import all active catalogs')
            catalogs = GtfsCatalog.objects.filter(active=True).exclude(id=271).order_by('?')
        else:
            catalogs = None

        return catalogs
    # catalog_filter


    # преобразование имени и типа маршрута
    def processing_name_type(self, catalog, gtfs_route, eval_route, route_type_mapping):
        try:
            if eval_route:
                # имя или тип преобразуется кодом в поле GtfsCatalog.eval_route
                # https://docs-python.ru/tutorial/vstroennye-funktsii-interpretatora-python/funktsija-exec/
                ldict = {
                    'route': gtfs_route,
                    'route_type_mapping': route_type_mapping,
                    'route_name': None,
                    'ttype': None
                }
                exec(eval_route, globals(), ldict)
                route_name = ldict['route_name']
                route_type = ldict['ttype']
            else:
                route_name = gtfs_route.route_short_name or gtfs_route.route_long_name
                route_type = route_type_mapping.get(str(gtfs_route.route_type))

            if route_type == None:
                raise ValueError(f'Unknown route_type {gtfs_route.route_type}, short_name "{gtfs_route.route_short_name}", long_name "{gtfs_route.route_long_name}"')
            if self.DEBUG:
                self.publish(f'Route: name: {gtfs_route.route_short_name}=>{route_name}, type: {gtfs_route.route_type}=>{route_type}')
        except Exception as ex:
            route_name, route_type = None, None
            self.publish(str(ex))

        return route_name, route_type
    # processing_name_type


    # создание провайдера из агенства
    def processing_provider(self, catalog, gtfs_route):
        agency = GtfsAgency.objects.filter(catalog=catalog, agency_id=gtfs_route.agency_id).first()
        if not agency and 'GEN:' in gtfs_route.agency_id:
            # 'GEN:' - признак генерации agency_id
            agency = GtfsAgency.objects.filter(catalog=catalog).first()

        if agency:
            busprovider, created = BusProvider.objects.get_or_create(xeno_id=gtfs_route.agency_id)

            update_fields = []

            if agency.agency_name:
                self.test_set(busprovider, 'name', agency.agency_name, update_fields)

            if agency.agency_phone:
                self.test_set(busprovider, 'phone', agency.agency_phone, update_fields)

            if agency.agency_email:
                self.test_set(busprovider, 'email', agency.agency_email, update_fields)

            if agency.agency_url:
                self.test_set(busprovider, 'www', agency.agency_url, update_fields)

            if update_fields:
                busprovider.save(update_fields=update_fields)

            if self.DEBUG:
                self.publish(f"Agency: id:{agency.agency_id or gtfs_route.agency_id}, name:{agency.agency_name}")
                self.publish(f"BusProvider({busprovider.id}:{busprovider.name}) {'created' if created else 'exists'}")
        else:
            busprovider = None
            if self.DEBUG: self.publish(f"Agency: None")

        return busprovider
    # processing_provider


    def processing_bus(self, catalog, gtfs_route, bus_name, bus_type, busprovider=None):
        #bus, created = Bus.objects.get_or_create(name=bus_name, ttype=bus_type, gtfs_catalog=catalog.id)
        # MultipleObjectsReturned: get() returned more than one Bus -- it returned 2!

        bus = Bus.objects.filter(name=bus_name, ttype=bus_type, gtfs_catalog=catalog.id).first()
        if bus:
            created = False
        else:
            created = True
            bus = Bus.objects.create(name=bus_name, ttype=bus_type, gtfs_catalog=catalog.id)

        if self.DEBUG: self.publish(f"Bus({bus.id}:{bus.ttype}:{bus.name}) {'created' if created else 'exists'}")

        update_fields = set()

        self.test_set(bus, 'city_id', 1, update_fields) # TODO: необязательно, но тогда не появится в сетке маршрутов

        # необязательно, для совместимости с предыдущей версией импорта
        if gtfs_route.route_ids:
            self.test_set(bus, 'murl', f'{gtfs_route.route_ids[0]}', update_fields)
        else:
            self.test_set(bus, 'murl', f'{catalog.id}*', update_fields)

        if busprovider:
            self.test_set(bus, 'provider_id', busprovider.id, update_fields)

        if gtfs_route.route_long_name:
            self.test_set(bus, 'description', gtfs_route.route_long_name, update_fields)

        #if update_fields:
        #    bus.save(update_fields=list(update_fields))

        return bus, update_fields
    # processing_bus


    def processing_stops(self, catalog, gtfs_route, bus, stops_all, eval_stops, reroute):
        bus_routes_changed = [[], []]
        tt_start = {}   # bus schedule

        for direction in [0, 1]:
            trip = getattr(gtfs_route, f'impoprt_trip_direction_{direction}') # it's dict
            if not trip:
                continue

            sdirection = str(direction)
            tt_start[sdirection] = []

            # сохраняем остановки только для трипа (маршрута), чтоб не плодить лишних
            # проверка stop_id__in=stops_all для фидов, в которых в stop_times.txt может быть остановка, которой нет в stops.txt (Catalog 162)
            stop_times = GtfsStopTimes.objects.filter(catalog=catalog.id, trip_id=trip.get('trip_id'), stop_id__in=stops_all)
            stops = GtfsStops.objects.filter(catalog=catalog.id, stop_id__in=Subquery(stop_times.values('stop_id').distinct('stop_id')))
            if self.DEBUG: self.publish(f"Direction: {direction}, import trip: {trip.get('trip_id')}, stops: {len(stops)}")

            bulk_create, bulk_update, update_fields = [], [], []
            exists = 0

            # import stops into system
            for stop in stops:
                stop_name = self.processing_stop_name(catalog, gtfs_route, eval_stops, stop)
                nbusstop = NBusStop.objects.filter(xeno_id=stop.stop_id).first()
                if nbusstop:
                    exists += 1
                    update = self.test_set(nbusstop, 'ttype', bus.ttype, update_fields)
                    update |= self.test_set(nbusstop, 'name', stop_name, update_fields)
                    update |= self.test_set(nbusstop, 'point', stop.stop_pt_loc, update_fields)
                    if update:
                        bulk_update.append(nbusstop)
                else:
                    bulk_create.append(NBusStop(xeno_id=stop.stop_id,
                                                ttype=bus.ttype,
                                                name=stop_name,
                                                point=stop.stop_pt_loc))
            # for stop in stops

            if bulk_create:
                NBusStop.objects.bulk_create(bulk_create)
            if bulk_update:
                NBusStop.objects.bulk_update(bulk_update, update_fields)
            if self.DEBUG: self.publish(f"Stops: {exists} exists, {len(bulk_create)} created, {len(bulk_update)} updated")

            # import stops into bus
            # prepare new route sequence
            new_routes = []
            for order, stop in enumerate(stop_times.order_by('stop_sequence')):
                nbusstop = NBusStop.objects.filter(xeno_id=stop.stop_id).first()
                if nbusstop:
                    new_routes.append((direction, nbusstop.id, order))

            # get old route sequence
            #Route.objects.filter(bus=bus, direction=direction).delete() # !!! DEBUG ONLY !!! THIS LINE MUST BE REMOVED AFTER DEBUG !!!
            exists_routes = []
            if reroute == False:    # reroute=True, когда надо принудительно обновить Route/RouteLine
                for r in Route.objects.filter(bus=bus, direction=direction).order_by('order').values_list('direction', 'busstop_id', 'order'):
                    exists_routes.append(r)

            # compare route sequenses
            if new_routes != exists_routes:
                # delete old sequence
                routes_deleted, _ = Route.objects.filter(bus=bus, direction=direction).delete()
                # and create new
                len_new_routes = len(new_routes)
                bulk_routes = []
                for i in range(len_new_routes):
                    d, id, o = new_routes[i]
                    endpoint = (i == 0 or i == len_new_routes - 1)
                    bulk_routes.append(Route(bus=bus, busstop_id=id, direction=d, order=o, endpoint=endpoint))
                # for i in range(len_new_routes)
                bus_routes_changed[direction] = Route.objects.bulk_create(bulk_routes) # bulk_create returns created objects as a list

                if self.DEBUG: self.publish(f"Bus route {direction} stops: {routes_deleted} deleted, {len_new_routes} created")
            elif self.DEBUG:
                self.publish(f"Bus route {direction} stops: not changed")

            # заполнить расписание для остановки new_routes[0]
            if new_routes:
                nbusstop = NBusStop.objects.filter(id=new_routes[0][1]).first()
                for stop in stop_times.order_by('stop_sequence'):
                    if stop.stop_id == nbusstop.xeno_id:
                        tt_start[sdirection].append( "%02d:%02d" % (stop.arrival_time.seconds/3600, stop.arrival_time.seconds%3600/60) )

        # for direction in [0, 1]

        #if self.DEBUG: self.publish(f"Bus schedule: {json.dumps(tt_start)}")

        if bus_routes_changed[1] and not bus_routes_changed[0]:
            # изменился набор остановок направления 1, а направления 0 нет
            # если вернуть только bus_routes_changed[1], дальнейший расчет всяких дистанций будет неверным
            # по этому заполняем bus_routes_changed[0]
            for r in Route.objects.filter(bus=bus, direction=0).order_by('order'):
                bus_routes_changed[0].append(r)

        return bus_routes_changed, json.dumps(tt_start, default=str)
    # processing_stops


    def processing_stop_name(self, catalog, gtfs_route, eval_stops, stop):
        if eval_stops:
            # имя остановки преобразуется кодом в поле GtfsCatalog.eval_stops
            # https://docs-python.ru/tutorial/vstroennye-funktsii-interpretatora-python/funktsija-exec/
            ldict = {
                'stop': stop,
                'stop_name': stop.stop_name
            }
            exec(eval_stops, globals(), ldict)
            stop_name = ldict['stop_name']
        else:
            stop_name = stop.stop_name.strip().title()
        return stop_name
    # processing_stop_name


    # постоение линий маршрута
    def processing_bus_lines(self, catalog, gtfs_route, bus, bus_routes, noshape):
        distances = [0, 0]

        for direction in [0, 1]:
            trip = getattr(gtfs_route, f'impoprt_trip_direction_{direction}') # it's dict
            points = None

            if noshape == False and trip and trip.get('shape_id'):
                # build routelines with shapes
                if self.DEBUG: self.publish(f"RouteLine {direction}: trying to build based on shapes")
                shapes = GtfsShapes.objects.filter(catalog=catalog.id,
                                                    shape_id=trip.get('shape_id')).order_by('shape_pt_sequence')
                points = [shape.shape_pt_loc for shape in shapes]

            if not points:
                # указан флаг --noshape или не существует шейпов трипа
                # build routelines with grapphopper by stops points
                if bus_routes[direction]:
                    if self.DEBUG: self.publish(f'RouteLine {direction}: trying to build with graphopper')
                    url = f'{settings.GH_SERVER}/route?points_encoded=false&locale=ru-RU&profile=car&elevation=false&instructions=false&type=json'
                    for r in bus_routes[direction]:
                        url += f'&point={r.busstop.point[1]},{r.busstop.point[0]}'
                    try:
                        r = requests.get(url, timeout=5)
                        js = r.json()
                        points = js.get('paths', [{}])[0].get('points', {}).get('coordinates', [])
                    except Exception as ex:
                        self.publish(f"RouteLine {direction}: graphopper server error: {str(ex)}")

            if points:
                linestring = LineString(points, srid=4326)
                RouteLine.objects.filter(bus=bus, direction=direction).delete()
                RouteLine.objects.create(bus=bus, direction=direction, line=linestring, mtime=datetime.datetime.now())
                """
                distance_by_line(routeline.line) на "замкнутых" шейпах даёт отрицательный результат
                есть следующий способ получения длинны линии:
                """
                linestring.transform(22186) # distance = linestring.length, meters, float
                distances[direction] = int(linestring.length)
                if self.DEBUG: self.publish(f"RouteLine {direction}: distance {distances[direction]} m")
            elif self.DEBUG:
                self.publish(f"RouteLine {direction}: no points for building")
        # for direction in [0, 1]
        return distances
    # processing_bus_lines


    # пакетное обновление маршрутов, ВНИМАНИЕ: Bus.save() не вызывается при таком обновлении
    def buses_save(self, set_buses_to_update, set_update_fields):
        if self.DEBUG: self.publish(f'Save {len(set_buses_to_update)} buses')
        Bus.objects.bulk_update(list(set_buses_to_update), list(set_update_fields))
        set_buses_to_update.clear()
        set_update_fields.clear()
    # buses_save


    def find_bus_duplicates(self, catalog, gtfs_route, bus):
        places = bus.places.all()
        buses = Bus.objects.filter(name=bus.name, ttype=bus.ttype, places__id__in=places).exclude(id=bus.id) # active=True, city_id=1,
        bus_duplicates = [b.id for b in buses] # id дубликатов
        if self.DEBUG: self.publish(f'{len(bus_duplicates)} duplicates found for bus {bus.id}:{bus.ttype}:"{bus.name}"')
        return bus_duplicates
    # find_bus_duplicates


    def remove_bus_duplicates(self, bus_duplicates):
        # bus_mass_delete.py требуется доступ к БД от имени postgres, а, значит, должно выполняться на хосте БД
        ids = ','.join(str(i) for i in bus_duplicates)
        sql = f"SELECT id FROM bustime_bus WHERE id IN ({ids})"
        cmd = f'python utils/bus_mass_delete.py "{sql}" --reset'
        if self.DEBUG:
            cmd += ' --debug'
        self.publish('=============================================================================')
        self.publish(f'To remove {len(bus_duplicates)} buses duplicates run this command on the host "f2", please:')
        self.publish(cmd)
        self.publish('=============================================================================')
        with open('/tmp/dedup.sh', 'a') as file:
           file.write(cmd + '\n')
    # remove_bus_duplicates


    def import_gtfs(self, pcatalog:str, reset:bool=False, noshape:bool=False, dedup:bool=False, reroute:bool=False, bus_only:str=None) -> int:
        catalogs = self.catalog_filter(pcatalog)    # обрабатываемые каталоги
        raw_routes_sql = self.getQueryRoutes()      # текст SQL-запроса предварительной подготовки gtfs-данных

        self.imported_bus_ids = set()
        self.old_places = set() # старые place маршрута, для обновления кэша place, если маршруты удалены

        imported_cnt = {}    # импортировано маршрутов
        bus_duplicates = []  # список id дубликатов маршрутов (маршрутов одного place с одинаковым именем)

        # import by catalog
        for catalog in catalogs:
            self.publish(f"========= catalog.id {catalog.id} begin =========")
            cid = str(catalog.id)
            imported_cnt[cid] = []
            # словарь для gtfs_updater'а
            pdata = {
                "route_id": {}, # "key": value = "gtfs.route_id": bus.id
                "trip_id": {}   # "key": value = "gtfs.trip_id": bus.id
            }

            # инструкции преобразования
            # https://docs-python.ru/tutorial/vstroennye-funktsii-interpretatora-python/funktsija-compile/
            eval_agency = compile(catalog.eval_agency, '', 'exec') if catalog.eval_agency else None
            eval_route = compile(catalog.eval_route, '', 'exec') if catalog.eval_route else None
            eval_stops = compile(catalog.eval_stops, '', 'exec') if catalog.eval_stops else None

            # dictionary for route type conversion
            route_type_mapping = json.loads(json.dumps(self.ttype))
            try:
                route_type_mapping.update(json.loads(catalog.route_type_mapping))
            except Exception as ex:
                if catalog.route_type_mapping:
                    self.publish(f'ERROR: Catalog {catalog.id} "route_type_mapping" is not valid value, must by a dict.')

            # все остановки фида
            stops_all = GtfsStops.objects.filter(catalog=catalog.id).values('stop_id').distinct('stop_id')

            # connection for raw sql
            with connections["gtfs"].connection.cursor(cursor_factory=NamedTupleCursor) as cursor_routes:
                # get gtfs routes list
                if self.DEBUG: self.publish(f'Prepare gtfs data...')
                cursor_routes.execute(raw_routes_sql, [catalog.id])

                bus_bulk_update = set()
                bus_update_fields = set()

                timezones = set()
                places = set()

                # scan routes list
                if self.DEBUG: self.publish(f'Read gtfs data')
                for gr in cursor_routes: # gr - gtfs route
                    if bus_only and gr.route_short_name != bus_only:
                        continue

                    if not self.DEBUG: self.publish(f'Import route {gr.route_short_name}')

                    if (not gr.impoprt_trip_direction_0) and (not gr.impoprt_trip_direction_0):
                        # catalog 306
                        self.publish(f'SKIPPING DUE TO TRIPS NOT FOUND')
                        continue

                    # converting the route name and type
                    bus_name, bus_type = self.processing_name_type(catalog, gr, eval_route, route_type_mapping)
                    if bus_type == None or not bus_name:
                        self.publish(f"SKIPPING DUE TO UNKNOWN TYPE/EMPTY NAME")
                        if self.DEBUG: self.publish("---")
                        continue

                    # agency/busprovider
                    busprovider = self.processing_provider(catalog, gr)

                    # route/bus
                    bus, tmp_update_fields = self.processing_bus(catalog, gr, bus_name, bus_type, busprovider)
                    imported_cnt[cid].append(bus.id)
                    if len(tmp_update_fields) > 0:
                        bus_bulk_update.add(bus)
                        bus_update_fields.update(tmp_update_fields)

                    # stops/stops + routes
                    bus_routes_changed, tt_start = self.processing_stops(catalog, gr, bus, stops_all, eval_stops, reroute)
                    # bus schedule
                    if tt_start and self.test_set(bus, 'tt_start', tt_start, bus_update_fields):
                        self.test_set(bus, 'tt_start_holiday', tt_start, bus_update_fields)
                        bus_bulk_update.add(bus)

                    #print("bus_routes_changed=", bus_routes_changed)
                    if bus_routes_changed[0] or bus_routes_changed[1]:  # [[Route0], [Route1]]
                        distances = self.processing_bus_lines(catalog, gr, bus, bus_routes_changed, noshape)
                        self.test_set(bus, 'distance0', distances[0], bus_update_fields)
                        self.test_set(bus, 'distance1', distances[1], bus_update_fields)
                        self.test_set(bus, 'distance', bus.distance0 + bus.distance1, bus_update_fields)
                        self.test_set(bus, 'travel_time', int(max(bus.distance0, bus.distance1)/1000.0 * 60.0 / 24.0), bus_update_fields)

                        # так как Bus.save() не вызывается, извращаемся здесь с полями, которые вычисляются там
                        bus_routes = []
                        if bus_routes_changed[0]:
                            # json.loads(json.dumps(model_to_dict(r)).replace('id', 'pk')) меняет ключ 'id' на 'pk'
                            bus_routes = [json.loads(json.dumps(model_to_dict(r)).replace('id', 'pk')) for r in bus_routes_changed[0]]
                        if bus_routes_changed[1]:
                            bus_routes += [json.loads(json.dumps(model_to_dict(r)).replace('id', 'pk')) for r in bus_routes_changed[1]]
                        if not bus_routes:
                            bus_routes = None
                        self.test_set(bus, 'routes', bus_routes, bus_update_fields)

                        if gr.impoprt_trip_direction_0:
                            self.test_set(bus, 'napr_a', gr.impoprt_trip_direction_0.get('trip_headsign'), bus_update_fields)
                        if gr.impoprt_trip_direction_1:
                            self.test_set(bus, 'napr_b', gr.impoprt_trip_direction_1.get('trip_headsign'), bus_update_fields)

                        # add bus to update list
                        bus_bulk_update.add(bus)

                        # bus places
                        self.old_places.update(list(bus.places.all()))
                        bus_places = update_bus_places('bus', bus.id, turbo=False, DEBUG=self.DEBUG) # in bustime.osm_utils.py
                        places.update(bus_places)
                        if self.channel: self.publish("Update bus places: " + str(bus_places))

                        if reset:
                            routes_get(bus.id, force=True)
                    # if bus_routes_changed
                    else:
                        places.update(
                            [p.id for p in bus.places.all()]
                        )

                    # save updated buses
                    if len(bus_bulk_update) > 9 and len(bus_update_fields) > 0:
                        self.buses_save(bus_bulk_update, bus_update_fields)

                    if dedup:
                        # ищем дубликаты маршрута
                        bus_duplicates += self.find_bus_duplicates(catalog, gr, bus)

                    # строим словарь для gtfs_updater'а, просто по всем маршрутам, независимо от импортированности
                    timezones.update(gr.timezones)
                    if gr.route_ids:
                        for route_id in gr.route_ids:
                            native = route_id.replace(f'{catalog.id}*', '')
                            if native:
                                pdata["route_id"][native] = bus.id
                    if gr.trip_ids:
                        for trip_id in gr.trip_ids:
                            native = trip_id.replace(f'{catalog.id}*', '')
                            if native:
                                pdata["trip_id"][native] = bus.id

                    if self.DEBUG: self.publish("---")
                # for gr in cursor_routes

                if len(bus_bulk_update) > 0 and len(bus_update_fields) > 0:
                    self.buses_save(bus_bulk_update, bus_update_fields)
            # with connections

            if len(imported_cnt[cid]) > 0:  # что-то импортировали
                self.imported_bus_ids.update(imported_cnt[cid]) # накапливаем id импортированных маршрутов


            catalog.cnt_buses = Bus.objects.filter(gtfs_catalog=catalog.id).count() # пересчитываем кол-во маршрутов в каталоге
            if bus_only and len(imported_cnt[cid]) > 0 and len(catalog.pdata) > 0:
                # импортировали 1 маршрут, надо обновить словарь, а не перезаписывать
                tmp = json.loads(catalog.pdata)
                tmp.update(pdata)
                pdata = tmp
            pdata["timezones"] = list(timezones)
            pdata["places"] = list(places)
            catalog.pdata = json.dumps(pdata)
            catalog.save(update_fields=['cnt_buses', 'pdata'])

            if self.DEBUG: self.publish(f"========= catalog.id {catalog.id} end ===========")
            if self.DEBUG: self.publish()
        # for catalog in catalogs


        # вывод итогов
        if self.DEBUG:
            if imported_cnt:
                self.publish(f"Statistic:")
                for k, v in imported_cnt.items():
                    self.publish(f"Catalog {k}: {len(v)} routes")

        # удаление дубликатов маршрутов
        if bus_duplicates:
            self.remove_bus_duplicates(bus_duplicates)

        if self.DEBUG: self.publish("---")
        return len(self.imported_bus_ids)
    # import_gtfs


    # вспомогательне методы
    @staticmethod
    def cache_reset(place: Place, routes_changed:bool=False) -> NoReturn:
        buses_get(place, force=True)
        if routes_changed:
            stops_get(place, force=True)
            get_busstop_points(place, force=True)
    # cache_reset


    @staticmethod
    def getQueryRoutes():
        # подготовка маршрутов
        return """
                WITH
                catalog AS (
                    SELECT %s AS id
                )
                /* берём все маршруты не взирая на дату. ALARM: смешаются одноименные маршруты разных сервисов
                ,services AS (
                    -- актуальные сегодня сервисы
                    -- ALARM: если calendar и calendar_dates пусты, импорта не произойдет
                    SELECT DISTINCT service_id
                    FROM (
                        SELECT service_id
                                FROM bustime_gtfscalendar
                                WHERE catalog_id = (SELECT id FROM catalog)
                                AND CURRENT_DATE BETWEEN start_date AND end_date
                        UNION
                        SELECT service_id
                                FROM bustime_gtfscalendardates
                                WHERE catalog_id = (SELECT id FROM catalog)
                                AND "date" = CURRENT_DATE AND exception_type=1
                    ) s
                )*/
                , agency_prepared AS (
                    SELECT catalog_id,
                        -- agency_id может не быть (catalog 119,120) :)
                        CASE
                            WHEN LENGTH(agency_id) > 0 THEN agency_id
                            -- берем первые буквы каждого слова в названии агенства, 'GEN:' - признак генерации agency_id
                            ELSE (SELECT catalog_id::text || '*GEN:' || STRING_AGG(arr[1], '') FROM REGEXP_MATCHES(agency_name, '\y\w', 'gi') arr)
                            -- или генерируем рандомную строку
                            --ELSE (SELECT catalog_id::text || '*GEN:' || SUBSTR(MD5(RANDOM()::TEXT), 1, 25))
                        END AS agency_id,
                        agency_name, agency_url, agency_timezone, agency_lang, agency_phone, agency_fare_url, agency_email
                    FROM bustime_gtfsagency
                    WHERE catalog_id = (SELECT id FROM catalog)
                )
                , routes_prepared AS (
                    -- бывает, что нет route_short_name, заменим на route_long_name, если и того нет, то на route_id
                    SELECT r.catalog_id,
                        -- agency_id может не быть, если агенство единственное в agency.txt или agency.txt пустое или agency.txt вообще нет :)
                        CASE
                            WHEN LENGTH(r.agency_id) > 0 THEN r.agency_id
                            ELSE (SELECT agency_id FROM agency_prepared WHERE catalog_id = r.catalog_id LIMIT 1)
                        END AS agency_id,
                        r.route_id, r.route_type,
                        CASE
                            WHEN LENGTH(r.route_short_name) > 0 THEN r.route_short_name
                            WHEN LENGTH(r.route_long_name) > 0 THEN r.route_long_name
                            ELSE r.route_id
                        END AS route_short_name,
                        r.route_long_name,
                        r.route_desc,
                        r.route_url
                    FROM bustime_gtfsroutes r
                    WHERE r.catalog_id = (SELECT id FROM catalog)
                )
                , trips AS (
                    -- убираем дубликаты и добавляем имя маршрута
                    SELECT DISTINCT
                        t.service_id, t.route_id, r.route_type, r.route_short_name, t.trip_id,
                        -- direction_id может не быть :)
                        CASE
                            WHEN LENGTH(t.direction_id) > 0 THEN t.direction_id ELSE '0'
                        END AS direction_id,
                        t.shape_id,
                        -- и считаем кол-во остановок в трипах
                        (
                            SELECT COUNT(s.stop_id)
                            FROM bustime_gtfsstoptimes s
                            WHERE s.catalog_id = t.catalog_id
                            AND s.trip_id = t.trip_id
                        ) AS stops_cnt,
                        -- REGEXP_REPLACE preventing Character with value 0xNN must be escaped
                        -- & trip_headsign не должен быть NULL
                        REGEXP_REPLACE(COALESCE(t.trip_headsign, r.route_long_name, ''), '[\t\\\]', ' ', 'g') as trip_headsign
                    FROM bustime_gtfstrips t
                    LEFT JOIN routes_prepared r ON r.route_id = t.route_id
                    WHERE t.catalog_id = (SELECT id FROM catalog)
                    /* AND t.service_id IN (SELECT service_id FROM services) берём все маршруты не взирая на дату */
                )
                , routes_r AS (
                    -- может быть много маршрутов с одним route_short_name и разными route_id
                    -- собираем все route_id одного маршрута route_short_name в массив
                    SELECT rp.catalog_id, rp.agency_id, rp.route_type, rp.route_short_name,
                        array_agg(rp.route_id ORDER BY route_id) AS route_ids,
                        array_agg(distinct(a.agency_timezone)) AS timezones
                    FROM routes_prepared rp
                    LEFT JOIN agency_prepared a ON a.agency_id = rp.agency_id
                    GROUP BY rp.catalog_id, rp.agency_id, rp.route_type, rp.route_short_name
                )
                , routes_t AS (
                    -- может быть много трипов для одного route_id
                    -- собираем все trip_id одного маршрута route_short_name в массив
                    SELECT catalog_id, agency_id, route_type, route_short_name, route_ids, timezones,
                        (
                            SELECT array_agg(trip_id ORDER BY route_id)
                            FROM trips
                            WHERE route_id = ANY(routes_r.route_ids) -- для всех route_id маршрута
                        ) AS trip_ids
                    FROM routes_r
                )
                , routes_stops AS (
                    -- вычисляем максимальное кол-во остановок для каждого направления маршрута
                    SELECT service_id, route_short_name, route_type, direction_id, MAX(stops_cnt) AS stops_max
                    FROM  trips
                    GROUP BY service_id, route_short_name, route_type, direction_id
                )
                -- итог
                SELECT t.catalog_id, t.agency_id, t.route_type, t.route_short_name,
                    t.route_ids, -- массив route_id для поиска маршрута по реалтайм-данным trip.route_id
                    t.trip_ids,  -- массив trip_id для поиска маршрута по реалтайм-данным trip.trip_id
                    t.timezones,
                    (   -- если хоть одно из полей будет NULL, весь результат будет NULL
                        SELECT ('{"trip_id":"'||tn.trip_id||'", "shape_id":"'||COALESCE(tn.shape_id, '')||'", "trip_headsign":"'||COALESCE(tn.trip_headsign, '')||'"}')::json
                        FROM trips tn
                        WHERE tn.route_short_name = t.route_short_name
                        AND tn.route_type = t.route_type
                        AND tn.direction_id = '0'
                        AND tn.stops_cnt = (SELECT s.stops_max
                                            FROM routes_stops s
                                            WHERE s.service_id = tn.service_id
                                            AND s.route_short_name = tn.route_short_name
                                            AND s.route_type = tn.route_type
                                            AND s.direction_id = tn.direction_id)
                        LIMIT 1
                    ) AS impoprt_trip_direction_0, -- трип с макс кол-вом остановок для направления 0
                    (
                        SELECT ('{"trip_id":"'||tn.trip_id||'", "shape_id":"'||COALESCE(tn.shape_id, '')||'", "trip_headsign":"'||COALESCE(tn.trip_headsign, '')||'"}')::json
                        FROM trips tn
                        WHERE tn.route_short_name = t.route_short_name
                        AND tn.route_type = t.route_type
                        AND tn.direction_id = '1'
                        AND tn.stops_cnt = (SELECT s.stops_max
                                            FROM routes_stops s
                                            WHERE s.service_id = tn.service_id
                                            AND s.route_short_name = tn.route_short_name
                                            AND s.route_type = tn.route_type
                                            AND s.direction_id = tn.direction_id)
                        LIMIT 1
                    ) AS impoprt_trip_direction_1, -- трип с макс кол-вом остановок для направления 1
                    -- добавляем информацию по маршруту
                    r.route_long_name, r.route_desc, r.route_url
                FROM routes_t t
                LEFT JOIN routes_prepared r ON r.catalog_id = t.catalog_id
                                                AND r.route_id = t.route_ids[1] -- нумерация с 1
                                                AND r.route_type = t.route_type
                WHERE t.trip_ids IS NOT NULL -- есть route_id не имеющие трипов
                ORDER BY t.catalog_id, t.agency_id, t.route_type, t.route_short_name
        """
    # getQueryRoutes
# class GtfsImporter


def main(args):
    try:
        loader = GtfsImporter(args.debug, args.ch)

        tic = time.perf_counter()
        imported_cnt = loader.import_gtfs(pcatalog=args.catalog,
                                            reset=args.reset,
                                            noshape=args.noshape,
                                            dedup=args.dedup,
                                            reroute=args.reroute,
                                            bus_only=args.bus)

        if imported_cnt > 0:
            places = Place.objects.filter(bus__id__in=loader.imported_bus_ids).distinct()
            uplaces = set()
            uplaces.update(list(places))
            uplaces.update(loader.old_places)
            places = list(uplaces)

            if args.upd:
                loader.publish()
                loader.publish(f"Обновляем БД сайта...")

                places_cnt = len(places)    # https://stackoverflow.com/a/14327315
                i = 0
                for p in places:
                    i += 1
                    loader.publish(f"   place({i}/{places_cnt}): {p.id}")

                    # формируем v8
                    loader.publish(f"city_update_v8()")
                    info_data = city_update_v8(p)
                    if info_data:
                        message = ", ".join(info_data[-2:])
                        loader.publish(f"      {message}")
                # for p in places

                """
                loader.publish()
                loader.publish(f"Обновляем БД приложений...")
                info_data = city_update_mobile(city)
                if info_data:
                    message = ", ".join(info_data[-2:])
                    loader.publish(f"   {message}")
                """

            if args.reset:
                loader.publish(f"Caches reset")
                # для обновления списка городов на странице выбора
                places_filtered(force=True)
                # сбрасываем кэш маршрутов города (см. views.py, turbo_home())
                for p in places:
                    GtfsImporter.cache_reset(p, True)
        # if imported_cnt > 0
        loader.publish(f"Импортировано маршрутов {imported_cnt}, время: {datetime.timedelta(seconds=time.perf_counter()-tic)}")

        if args.ch:
            sio_pub(args.ch, {"call": "import_controls_disabled", "argument": False})
    except:
        err = traceback.format_exc(limit=4)
        logging.error(err)
        loader.publish(err, 'error')
# main


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Импорт сырых gtfs данных в маршруты bustime.loc v.2')
    parser.add_argument('catalog', type=str,
                            help='''0:обработать все существующие записи;
                                    N[,N1,N2...]:обработать записи с указанными id;
                                    N-M:обработать записи с id от N до M''')
    parser.add_argument("-u", "--upd", help="Обновлять БД сайта и приложений", action="store_true")
    parser.add_argument("-r", "--reset", help="Выполнять сброс кэшей маршрутов/городов после импорта", action="store_true")
    parser.add_argument("-n", "--noshape", help="Не использовать shape фидов, строить путь по остановкам", action="store_true")
    parser.add_argument("-d", "--dedup", help="Удалять дубликаты маршрутов", action="store_true")
    parser.add_argument("-o", "--reroute", help="Пересчитывать Route/RouteLine даже если не изменились", action="store_true")
    parser.add_argument("--bus", help="Имя единственного импортируемого маршрута (действует только для одного каталога)")
    parser.add_argument("--ch", help="Имя redis-канала для вывода сообщений")
    parser.add_argument("--debug", help="Вывод отладочных сообщений", action="store_true")
    args = parser.parse_args()
    main(args)