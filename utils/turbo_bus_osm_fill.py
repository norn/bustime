#!/mnt/reliable/repos/bustime/bustime/.venv/bin/python
# -*- coding: utf-8 -*-
"""
Fill Bus data with city_osm ids

Запуск:
python utils/turbo_bus_osm_fill.py bus 0        # все маршруты всех городов
python utils/turbo_bus_osm_fill.py bus 1000     # маршрут с id=1000
python utils/turbo_bus_osm_fill.py city 0       # все маршруты всех городов
python utils/turbo_bus_osm_fill.py city 100     # все маршруты города с id=100
python utils/turbo_bus_osm_fill.py place 0      # все маршруты всех places
python utils/turbo_bus_osm_fill.py place 100    # все маршруты в places которых есть place с id=100
python utils/turbo_bus_osm_fill.py place -1     # все маршруты с пустым places
python utils/turbo_bus_osm_fill.py catalog 10   # все маршруты, импортированные из GtfsCatalog с id=10
Параметр --debug включает вывод отладочных сообщений
Параметр --turbo устанавливает поле turbo=True
"""

from devinclude import *
from bustime.models import *
from bustime.osm_utils import update_bus_places
import argparse
import time

excluded_city = [6, 183, 1674442]


def update(entity, id, turbo=False, DEBUG=False):
    update_bus_places(entity, id, turbo, DEBUG)
# update

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Назначение places маршрутам')
    parser.add_argument('entity', type=str, help='Сущность: bus|city|place|catalog, ID которой задаёт следующий параметр')
    parser.add_argument('id', type=int, help='ID Сущности')
    parser.add_argument("--turbo", help="Устанавливать поле turbo в True", action="store_true")
    parser.add_argument("--debug", help="Вывод отладочных сообщений", action="store_true")
    args = parser.parse_args()

    update(args.entity, args.id, args.turbo, args.debug)
