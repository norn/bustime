# -*- coding: utf-8 -*-
from bustime.models import *
from update_lib import analyze_events


def update_moscow(city=CITY_MAPN[u'Москва'], debug=False):
    """
    Пример скрипта обновления.
    Добываем события любым способом и кормим в analyze_events.
    """
    events = []
    bus = Bus.objects.filter()[0]
    now = datetime.datetime.now()
    e = Event(uniqueid='u12345',
              timestamp=now,
              x=55.7,
              y=37.6,
              bus=bus,
              heading=90,
              speed=24,
              gosnum='А 777 АА')
    events.append(e)
    # и так далее


    analyze_events(city, events)
    return True
