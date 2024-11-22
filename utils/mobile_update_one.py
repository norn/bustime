#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
python utils/mobile_update_one.py
'''
from devinclude import *
from bustime.models import *
from bustime.update_utils import mobile_update_place
import subprocess
from django.db.models import Count
from turbo_json_dump_update import make_patch_for_json

#city_id = 12522
city_id = 143


# places_with_bus_count = Place.objects.annotate(bus_count=Count('bus'))
# places_with_more_than_one_bus = places_with_bus_count.filter(bus_count__gt=3).order_by("name")
# for place in Place.objects.filter(id=city_id, bus__gt=0, bus__active=True).distinct().order_by("name"):
# for place in places_with_bus_count.filter(id=city_id, bus_count__gt=7).order_by("name"):
for place in Place.objects.filter(id=city_id).order_by("name"):
    print('\n'.join(mobile_update_place(place, reload_signal=False)))
    print('\n'.join(make_patch_for_json(place)))


# for city in City.objects.filter(available=True, active=True,id=city_id).order_by("name"):
#     place = Place.objects.get(id=city.id)
#     print('\n'.join(mobile_update_place(place, reload_signal=False)))
#     # v8
#     print('\n'.join(make_patch_for_json(place)))

info_data = []
cmd = [
    "%s/bustime/static/other/db/v5/0diff.sh" % settings.PROJECT_DIR
]
p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
result, err = p.communicate("")
info_data.append(result.decode())
info_data.append(err.decode())
###
cmd = [
    "%s/bustime/static/other/db/v7/0diff.sh" % settings.PROJECT_DIR
]
p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
result, err = p.communicate("")
info_data.append(result.decode())
info_data.append(err.decode())

print('\n'.join(info_data))
