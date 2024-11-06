#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Заполнение поля order модели Bus
Запуск:
python utils/fill_order.py 84 --debug
"""
from __future__ import absolute_import
from devinclude import *
from bustime.models import *
import argparse


def fill(place_id, DEBUG=False):
    if place_id == 0:
        if DEBUG: print(f"All places with buses")
        places = Place.objects.filter(buses_count__gt=0)
    else:
        places = Place.objects.filter(id=place_id, buses_count__gt=0)

    if DEBUG and not places:
        print(f"Selected places has not buses")

    """
    Маршрут может принадлежать нескольким place,
    в таком случае он несколько раз получит новый order, для куаждого place разный.
    И при этом не факт, что в наборе маршрутов каждого place order этого маршрута будет
    правильным для этого конкретного набора.
    Для уменьшения такой вероятности надо отсортировать places по возрастанию кол-ва маршрутов.
    """
    for place in places.order_by('buses_count'):
        if DEBUG: print(f"id: {place.id}, {place.name}, buses: {place.buses_count} ", end='')
        msg = fill_order(place, DEBUG=DEBUG)
        rcache_set(f'turbo_home__{place.slug}', []) # reset cache
        buses_get(place, force=True)
        if DEBUG: print("; ".join(msg))

    if DEBUG: print(f"Done")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Импорт сырых gtfs данных в маршруты bustime.loc')
    parser.add_argument('p', type=int, help="Place ID")
    parser.add_argument("--debug", help="Вывод отладочных сообщений", action="store_true")
    args = parser.parse_args()

    fill(args.p, args.debug)
