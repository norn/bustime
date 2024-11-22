#!/mnt/reliable/repos/bustime/bustime/.venv/bin/python
# -*- coding: utf-8 -*-
"""
Обновление счетчиков модели Place
вызывается из крона

Запуск:
python utils/places_fresh_counters.py
"""

from devinclude import *
from bustime.models import *

qs = Place.objects.raw("""
    SELECT DISTINCT bp.id, bpa.geometry FROM bustime_place bp
    INNER JOIN bustime_placearea bpa ON (bp.osm_area_id = bpa.osm_id AND bp.osm_area_type = bpa.osm_type)
    CROSS JOIN bustime_bus_places bbp WHERE bp.id = bbp.place_id
""")
for pa in qs:
    pa.stops_count= NBusStop.objects.filter(point__contained=pa.geometry).count()
    pa.buses_count = Bus.objects.filter(places=pa).distinct().count()
    pa.save()
