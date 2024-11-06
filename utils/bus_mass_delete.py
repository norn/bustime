#!/bustime/bustime/.venv/bin/python
# -*- coding: utf-8 -*-
"""
Быстрое удаление группы маршрутов (десятки тысяч)
Используется решение https://stackoverflow.com/a/42429429/6249350
но, требуется доступ к БД от имени postgres, а, значит должно выполняться на хосте БД

Пример эффективности: 15182 buses in 0:01:45.784867

На вход подается текст SQL-запроса, выбирающего ID удаляемых маршрутов, например:
    "SELECT id FROM bustime_bus where murl like '271*%%'"
в кавычках из-за пробелов, % экранирует символ % в строке

Пример:
    utils/bus_mass_delete.py "SELECT id FROM bustime_bus WHERE murl LIKE '271*%%'" --reset --debug
или
    python  utils/bus_mass_delete.py "SELECT id FROM bustime_bus WHERE city_id = 100" --reset --debug
или
    utils/bus_mass_delete.py "SELECT bus_id FROM bustime_bus_places WHERE place_id = 100" --reset --debug
"""
from __future__ import absolute_import
from devinclude import *
from bustime.models import *
import argparse
import traceback
import datetime
import subprocess
from django.db import connection
from typing import NoReturn


class BusRemover:
    # Constructor
    def __init__(self, DEBUG=False, channel=None):
        self.DEBUG = DEBUG
        self.channel = channel # имя redis-канала для вывода сообщений
        self.start_time = 0
        self.before_sqls = [
            # актуальный на 09.07.24 список зависимых таблиц, порядок важен
            "DELETE FROM bustime_busversionlog   WHERE bus_id IN (SELECT id from bus_list_for_delete);",
            "DELETE FROM bustime_busversion      WHERE bus_id IN (SELECT id from bus_list_for_delete);",
            "DELETE FROM bustime_favorites       WHERE bus_id IN (SELECT id from bus_list_for_delete);",
            "DELETE FROM bustime_passenger       WHERE bus_id IN (SELECT id from bus_list_for_delete);",
            "DELETE FROM bustime_vote            WHERE vehicle_id IN (SELECT id FROM bustime_vehicle1 WHERE bus_id IN (SELECT id from bus_list_for_delete));",
            "DELETE FROM bustime_vehicle1        WHERE bus_id IN (SELECT id from bus_list_for_delete);",
            "DELETE FROM bustime_routepreview    WHERE bus_id IN (SELECT id from bus_list_for_delete);",
            "DELETE FROM bustime_routeline       WHERE bus_id IN (SELECT id from bus_list_for_delete);",
            "DELETE FROM bustime_route           WHERE bus_id IN (SELECT id from bus_list_for_delete);",
            "DELETE FROM bustime_bus_places      WHERE bus_id IN (SELECT id from bus_list_for_delete);",
            "DELETE FROM bustime_bus_osm         WHERE bus_id IN (SELECT id from bus_list_for_delete);",
            "DELETE FROM bustime_passenger       WHERE bus_id IN (SELECT id from bus_list_for_delete);",
            "UPDATE bustime_chat                 SET bus_id=NULL          WHERE bus_id IN (SELECT id from bus_list_for_delete);",
            "UPDATE bustime_plan                 SET bus_id=NULL          WHERE bus_id IN (SELECT id from bus_list_for_delete);",
            "UPDATE bustime_mapping              SET bus_id=NULL          WHERE bus_id IN (SELECT id from bus_list_for_delete);",
            "UPDATE bustime_mobilesettings       SET gps_send_bus_id=NULL WHERE gps_send_bus_id IN (SELECT id from bus_list_for_delete);",
            "UPDATE bustime_usersettings         SET gps_send_bus_id=NULL WHERE gps_send_bus_id IN (SELECT id from bus_list_for_delete);",
        ]
        self.after_sqls = [
            # удаление провайдеров, которых нет в bustime_bus
            "DELETE FROM bustime_busprovider WHERE id NOT IN (SELECT DISTINCT provider_id FROM bustime_bus);",
            # удаление остановок, которых нет в bustime_route & bustime_routepreview
            """DELETE FROM bustime_nbusstop nb \
            WHERE NOT EXISTS (SELECT busstop_id FROM bustime_route WHERE busstop_id = nb.id) \
            AND NOT EXISTS (SELECT busstop_id FROM bustime_routepreview WHERE busstop_id = nb.id);"""
        ]
        self.places_to_update = []

    # для измерения времени операций
    def timer_start(self) -> NoReturn:
        self.start_time = datetime.datetime.now()

    def time_print(self, msg: str) -> NoReturn:
        self.publish('{} duration: {}'.format(msg, datetime.datetime.now() - self.start_time))
    # / для измерения времени операций

    def publish(self, msg: str='', end: str=None) -> None:
        print(msg, end=end)
        if self.channel:
            sio_pub(self.channel, msg)
    # publish

    def bus_remove(self, bus_to_delete_sql:str)->int:
        if self.DEBUG:
            self.publish(f'Bus select sql: {bus_to_delete_sql}')
            all_start_time = datetime.datetime.now()

        retval = 0

        try:
            with connections["default"].cursor() as cursor:
                cursor.execute("SET SEARCH_PATH TO public;")

                # save list of places of removing buses
                cursor.execute(f"SELECT DISTINCT place_id FROM bustime_bus_places WHERE bus_id IN ({bus_to_delete_sql});")
                self.places_to_update = cursor.fetchall()

                cursor.execute("DROP TABLE IF EXISTS bus_list_for_delete;")
                cursor.execute("CREATE UNLOGGED TABLE bus_list_for_delete (id int);")
                cursor.execute(f"INSERT INTO bus_list_for_delete {bus_to_delete_sql};")

                # before bus delete
                for sql in self.before_sqls:
                    if self.DEBUG:
                        self.publish(f'{sql}', end=' ')
                        self.timer_start()
                    cursor.execute(sql)
                    if self.DEBUG: self.time_print(f'done,')

                # bus delete
                if self.DEBUG: self.publish(f'DELETE FROM bustime_bus WHERE id IN (SELECT id from bus_list_for_delete)')
                # https://stackoverflow.com/a/42429429/6249350
                # требуется доступ к БД от имени postgres
                # DISABLE TRIGGER ALL не затрагивает UK & PK
                cmd = [
                    "sudo", "-u", "postgres",
                    "psql", "-d", "bustime",
                    "-c",
                    """SET SEARCH_PATH TO public;\
                    ALTER TABLE bustime_bus DISABLE TRIGGER ALL;\
                    DELETE FROM bustime_bus WHERE id IN (SELECT id FROM bus_list_for_delete);\
                    ALTER TABLE bustime_bus ENABLE TRIGGER ALL;"""
                ]
                result = subprocess.check_output(cmd).decode("utf8")
                if self.DEBUG: self.publish(result.strip())

                try:
                    retval = int(result.split("DELETE")[-1].split("ALTER")[0].strip())
                except:
                    pass

                # after bus delete
                for sql in self.after_sqls:
                    if self.DEBUG:
                        self.publish(f'{sql}', end=' ')
                        self.timer_start()
                    cursor.execute(sql)
                    if self.DEBUG: self.time_print(f'done,')

                #TODO: cache_reset_bus(bus, deleted=False)
                cursor.execute("DROP TABLE IF EXISTS bus_list_for_delete;")

        except Exception as ex:
            self.publish(traceback.format_exc(limit=1))

        if self.DEBUG:
            all_duration = datetime.datetime.now() - all_start_time
            self.publish(f'Done {retval} buses in {all_duration}')

        return retval
    # bus_remove


    def cache_reset(self, place: Place) -> NoReturn:
        buses_get(place, force=True)
        stops_get(place, force=True)
        get_busstop_points(place, force=True)
    # cache_reset
# class BusRemover


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Массовое удаление маршрутов')
    parser.add_argument('bus_sql', type=str,
                            help='"SQL запрос" фильтрации удаляемых маршрутов, возвращающий их список ID')
    parser.add_argument("--ch", help="Имя redis-канала для вывода сообщений")
    parser.add_argument("--reset", help="Выполнять сброс кэшей маршрутов/городов после импорта", action="store_true")
    parser.add_argument("--debug", help="Вывод отладочных сообщений", action="store_true")
    args = parser.parse_args()

    remover = BusRemover(args.debug, args.ch)
    deleted_buses_count = remover.bus_remove(args.bus_sql)

    if deleted_buses_count > 0 and args.reset:
        if remover.places_to_update:
            if args.debug: remover.publish(f'Clear cache for {len(remover.places_to_update)} places:')
            places_ids = [row[0] for row in remover.places_to_update]
            for id in places_ids:
                p = Place.objects.filter(id=id).first()
                if p:
                    if args.debug: remover.publish(f'{p.name}')
                    remover.cache_reset(p)
        # if remover.places_to_update
        fill_bus_stata()
    # if deleted_buses_count > 0

    remover.publish(f'Done')
    # if