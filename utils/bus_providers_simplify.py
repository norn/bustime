#!/bustime/bustime/.venv/bin/python
# -*- coding: utf-8 -*-
"""
В модели BusProvider повторяются провайдеры: в одном городе несколько провайдеров с одним именем
Скрипт удаляет повторения провайдеров, заменяя в модели Bus и Vehicle удалённых на оставшегося.

Запуск:
python utils/bus_providers_simplify.py
"""
from __future__ import absolute_import
from devinclude import *
from bustime.models import *    # fill_routeline, fill_order, cache_reset_bus, fill_bus_endpoints
from django.db.models import Q, Subquery, Count

# формируем список на удаление дубликатов
providers_double = BusProvider.objects.values_list(
                                            'name', flat=True
                                        ).annotate(
                                            cnt=Count('name')
                                        ).filter(
                                            cnt__gt=1
                                        )

providers = BusProvider.objects.filter(
    name__in=Subquery(providers_double.values_list('name', flat=True))
).order_by('name')

replace_map = {}
for p in providers:
    if p.name not in replace_map:
        # первого сохраняем, остальных помещаем в список на удаление
        replace_map[p.name] = {"preserve": p.id, "delete":[]}
    else:
        replace_map[p.name]["delete"].append(p.id)

# удаляем повторяющихся провайдеров
for name, val in replace_map.items():
    print(f'{val["preserve"]} {name}')
    for id in val["delete"]:
        bus_mod = Bus.objects.filter(provider=id).update(provider=val["preserve"])
        veh_mod = Vehicle.objects.filter(provider=id).update(provider=val["preserve"])
        BusProvider.objects.filter(id=id).delete()
        print(f'deleted: {id}, updated: {bus_mod} Bus, {veh_mod} Vehicle')