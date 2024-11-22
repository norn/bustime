#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Usage:
    python utils/bus_napr_fill.py -p 165
'''
from __future__ import absolute_import
from devinclude import *
from bustime.models import *
from django.db import connections, connection
import argparse


def napr_fill(all:bool=False, place:int=None, bus:int=None, reset:bool=False, debug:bool=False):
    if bus:
        filter = f'WHERE b.id = {bus}'
    elif place:
        filter = f'LEFT JOIN bustime_bus_places bp ON bp.bus_id = b.id WHERE bp.place_id = {place}'
    else:
        filter = ''
        if debug: print('Update all buses')

    sql = f"""
        UPDATE bustime_bus SET
            napr_a = b.napr_a,
            napr_b = b.napr_b
        FROM (
            SELECT b.id, b.name
                , (
                    SELECT s."name"
                    FROM bustime_route r
                    LEFT JOIN bustime_nbusstop s ON s.id = r.busstop_id
                    WHERE r.bus_id = b.id AND r.direction = 0
                    ORDER BY r."order" DESC
                    LIMIT 1
                ) AS napr_a
                , (
                    SELECT s."name"
                    FROM bustime_route r
                    LEFT JOIN bustime_nbusstop s ON s.id = r.busstop_id
                    WHERE r.bus_id = b.id AND r.direction = 0
                    ORDER BY r."order" ASC
                    LIMIT 1
                ) AS napr_b
            FROM bustime_bus b
            {filter}
        ) b
        WHERE b.id = bustime_bus.id
    """
    changes = 0
    with connection.cursor() as cursor:
        cursor.execute(sql)
    changes = cursor.rowcount

    if debug: print(f'Updated {changes} buses')

    if reset:
        if all:
            places = Place.objects.all()
        elif bus:
            places = Place.objects.filter(bus__id=bus).distinct()
        elif place:
            places = [Place.objects.filter(id=place).first()]
        for p in places:
            if buses_get(p):
                if debug: print(f'Reset cache for place {p.id}:{p.name}')
                buses_get(p, force=True)
# fill


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Заполнение bus.napr_a & bus.napr_b')
    parser.add_argument("-a", "--all", help="все маршруты")
    parser.add_argument("-p", "--place", type=int, help="place.id")
    parser.add_argument("-b", "--bus", type=int, help="bus.id")
    parser.add_argument("-r", "--reset", help="Выполнять сброс кэшей маршрутов", action="store_true")
    parser.add_argument("--debug", help="Вывод отладочных сообщений", action="store_true")

    args = parser.parse_args()
    napr_fill(**vars(args))
