#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import print_function
from devinclude import *
from bustime.models import *
from bustime.update_utils import mobile_update_place
import subprocess
import datetime
from django import db
from django.db.models import Count
from mobile_dump_update import DiffProcessor, DBVer
from turbo_json_dump_update import make_patch_for_json

# for cron log
print("\n%s" % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

places_with_bus_count = Place.objects.annotate(bus_count=Count('bus'))

# for place in Place.objects.filter(name__isnull=False, bus__gt=0, bus__active=True).distinct().order_by("name"):
# for place in places_with_bus_count.filter(name__isnull=False, bus_count__gt=7).distinct().order_by("name"):
for place in Place.objects.filter(id__in=places_filtered()).order_by("name"):
    print('\n'.join(mobile_update_place(place, reload_signal=False)))
    # v8
    print('\n'.join(make_patch_for_json(place)))

# for city in City.objects.filter(available=True, active=True).order_by("name"):
    # if city.available and city.active:
        # place = Place.objects.get(id=city.id)
        # print('\n'.join(mobile_update_place(place, reload_signal=False)))
        # v8
        # print('\n'.join(make_patch_for_json(place)))

info_data = []
###
"""
cmd = [
    "%s/bustime/static/other/db/v4/0diff.sh" % settings.PROJECT_DIR
]
p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
result, err = p.communicate("")
info_data.append(result)
info_data.append(err)
"""
##
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

processor = DiffProcessor(DBVer.v5)
processor.diff_all_google()

processor = DiffProcessor(DBVer.v7)
processor.diff_all_google()

db.connection.close()
print(info_data)
