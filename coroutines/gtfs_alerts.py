#!/bustime/bustime/.venv/bin/python
# -*- coding: utf-8 -*-
'''
Тестирование:
python coroutines/gtfs_alerts.py DEBUG

help:
https://gtfs.org/ru/realtime/feed-entities/service-alerts/
https://developers.google.com/transit/gtfs-realtime/examples/python-sample?hl=ru
https://gtfs.org/ru/realtime/language-bindings/python/
https://developers.google.com/transit/gtfs-realtime/examples/alerts?hl=ru
'''
from __future__ import absolute_import
from devinclude import *
from bustime.models import *
from google.transit import gtfs_realtime_pb2
from google.protobuf.json_format import MessageToDict # pip install protobuf
import requests
import time
import json
import traceback
from timezonefinder import TimezoneFinder
from pytz import timezone, utc
from datetime import datetime, timedelta


CACHE_TIMEOUT_SEC = 86400
REQUEST_TIMEOUT_SEC = 3
fm = gtfs_realtime_pb2.FeedMessage()


def update(DEBUG=False):
    for catalog in GtfsCatalog.objects.filter(active=True)\
                                        .exclude(url_rt_alerts__isnull=True)\
                                        .exclude(url_rt_alerts__exact='')\
                                        .order_by('id'):
        if type(DEBUG) == int and catalog.id != DEBUG:
            continue
        if DEBUG: print(f'{catalog.id}:{catalog.name}: GET {catalog.url_rt_alerts}')

        content = None
        try:
            tic = time.monotonic()
            if catalog.request_auth:
                locals={"headers":None,"auth":None}
                exec(catalog.request_auth, None, locals)
                if locals["headers"] and locals["auth"]:
                    r = requests.get(catalog.url_rt_alerts, headers=locals["headers"], auth=locals["auth"], timeout=REQUEST_TIMEOUT_SEC)
                elif locals["headers"]:
                    r = requests.get(catalog.url_rt_alerts, headers=locals["headers"], timeout=REQUEST_TIMEOUT_SEC)
                elif locals["auth"]:
                    r = requests.get(catalog.url_rt_alerts, auth=locals["auth"], timeout=REQUEST_TIMEOUT_SEC)
            else:
                r = requests.get(catalog.url_rt_alerts, timeout=REQUEST_TIMEOUT_SEC)

            if r.status_code == requests.codes.ok:
                content = r.content
            else:
                if DEBUG: print(f'request status code [{r.status_code}]')
        except Exception as ex:
            if DEBUG: print(str(ex))

        if content:
            try:
                fm.ParseFromString(content)
                #if DEBUG: print(f'fm.entity', fm.entity)

                message = {
                    "state": CityUpdaterState.ALERTS.name.lower(),
                    "method": "alerts",
                    "provider_events_count": getattr(fm.entity, "__len__", lambda: 0)(),
                    "provider_delay": round(time.monotonic() - tic, 2)
                }
                sio_pub(f"ru.bustime.alerts_stat__{catalog.id}", {"updater": message})

                decode_pb2(catalog, fm.entity, DEBUG=DEBUG)
            except:
                if DEBUG:
                    print(traceback.format_exc(limit=2))
    # for c in GtfsCatalog
# update


'''
see https://gtfs.org/ru/realtime/feed-entities/service-alerts/
https://developers.google.cn/transit/gtfs-realtime/examples/alerts?hl=ru
https://developers.google.com/transit/gtfs-realtime/examples/alerts?hl=ru

e = {
   "id": "3ec7de20-3425-413c-a186-c24099299aa9",
   "alert": {
      "activePeriod": [          # может не быть
         {
            "start": "1720411200",  # может не быть
            "end": "1724677200"     # может не быть
         }
      ],
      "informedEntity": [
         {
            "routeId": "0063"
         },
         {
            "routeId": "0065"
         }
      ],
      "cause": "OTHER_CAUSE",
      "effect": "DETOUR",
      "headerText": {
         "translation": [
            {
               "text": "Du 08/07 au 28/08 2024 : March\u00e9 hebdomadaire des Salins",
               "language": "fr"
            }
         ]
      },
      "descriptionText": {  # может не быть, может быть html на нексолько килобайт
         "translation": [
            {
               "text": "Tous les lundis de Juillet et Ao\u00fbt 2024 de 6h00 \u00e0 15h00, en raison du march\u00e9 hebdomadaire des Salins, la lignes 63 est d\u00e9vi\u00e9e dans les deux sens et n'effectuera pas la boucle des Salins et la ligne E65 en direction des Salins est d\u00e9vi\u00e9e par l'avenue de la Lib\u00e9ration et fera son terminus sur la Place Wolff.\n\nArr\u00eats non desservis : \"Les Salins\", \"Vieux Salins\" et \"Victoire\".\n\nMerci de votre compr\u00e9hension.",
               "language": "fr"
            }
         ]
      }
   }
}

e= {
   "id": "alert_3",
   "alert": {
      "informedEntity": [
         {
            "routeId": "34",
            "routeType": 3,
            "stopId": "1150"
         }
      ],
      "cause": "OTHER_CAUSE",
      "effect": "DETOUR",
      "url": {
         "translation": [
            {
               "text": "www.emtmalaga.es/emt-classic/home.html",
               "language": "es"
            }
         ]
      },
      "headerText": {
         "translation": [
            {
               "text": "Desv\u00edo l\u00ednea 34",
               "language": "es"
            }
         ]
      },
      "descriptionText": {
         "translation": [
            {
               "text": "L\u00ednea 34 desviada entre las paradas Eucaliptos - Viaducto y Amador de los R\u00edos - Manuel del Palacio - Paradas suprimidas: Eucaliptos - Bda. La Mosca, Amador de los R\u00edos - Eucaliptus",
               "language": "es"
            }
         ]
      }
   }
}
'''
def decode_pb2(catalog, entities, DEBUG=False):
    pdata = json.loads(catalog.pdata or {})
    if not pdata:
        return

    places = pdata.get("places")
    if not places:
        return

    catalog_now = catalog.now() # местное время фида
    if not catalog_now:
        raise ValueError(f'GTFS catalog {catalog.id} does not have a time zone')
    catalog_now = int(catalog_now.timestamp()) # to timestamp
    new_alerts = {}

    for entity in entities:
        """MessageToDict(message, ...): Converts protobuf message to a dictionary.
        Args:
        message: The protocol buffers message instance to serialize.
        including_default_value_fields: If True, singular primitive fields,
            repeated fields, and map fields will always be serialized.  If
            False, only serialize non-empty fields.  Singular message fields
            and oneof fields are not affected by this option.
        preserving_proto_field_name: If True, use the original proto field
            names as defined in the .proto file. If False, convert the field
            names to lowerCamelCase.
        use_integers_for_enums: If true, print integers instead of enum names.
        descriptor_pool: A Descriptor Pool for resolving types. If None use the
            default.
        float_precision: If set, use this to specify float field valid digits.

        Returns:
        A dict representation of the protocol buffer message.
        """
        e = MessageToDict(entity)
        #if type(DEBUG) == int: print("\ne=", json.dumps(e, default=str, indent=3))
        a = e.get("alert")

        active = a.get("activePeriod", True) # чтобы продолжить, если activePeriod вообще нет
        start, end = None, None
        for i in a.get("activePeriod", []):
            # время местное для фида
            start = int(i.get("start", 0)) # может не быть
            end = int(i.get("end", 0)) # может не быть
            if start and end:
                active = start <= catalog_now and catalog_now <= end
            elif start:
                active = start <= catalog_now
            elif end:
                active = catalog_now <= end
            if active:
                break
        if not active:
            continue

        id = e.get("id")
        new_alerts[id] = {}
        new_alerts[id]["start"] = datetime.fromtimestamp(start).strftime("%d.%m.%y %H:%M") if start else None
        new_alerts[id]["end"] = datetime.fromtimestamp(end).strftime("%d.%m.%y %H:%M") if end else None
        new_alerts[id]["created"] = datetime.fromtimestamp(catalog_now).strftime("%d.%m.%y %H:%M:%S")
        new_alerts[id]["header"] = a.get("headerText", {}).get("translation", [{}])[0].get("text", '').replace("\n", "<br>")
        new_alerts[id]["description"] = a.get("descriptionText", {}).get("translation", [{}])[0].get("text", '').replace("\n", "<br>")
        new_alerts[id]["cause"] = a.get("cause")
        new_alerts[id]["effect"] = a.get("effect")
        routes = set()
        for i in a.get("informedEntity", []):
            # здесь всё может быть гораздо сложней, но пока так
            rid = i.get("routeId")  # gtfs roite_id
            if rid:
                bid = pdata.get("route_id", {}).get(rid)    # gtfs route_id => bustime bis.id
                if bid:
                    # для передачи на страницу нужны поля Bus
                    bus = bus_get(bid)
                    if bus:
                        routes.add(bus)
        new_alerts[id]["routes"] = list(routes)
    # for entity in entities

    if DEBUG: print("new_alerts=", new_alerts)
    if new_alerts:
        if DEBUG: print(f'Alerts in places:')
        # TODO: правильней было бы определять place по id маршрута?
        for pid in places:
            if DEBUG:
                p = Place.objects.get(id=pid)
                print(f'{p.id}: {p.name}')

            cc_key = "alerts_%s" % pid
            '''
            # режим обновления существующих
            # TODO: придумать как удалять удалять неактуальные
            alerts = rcache_get(cc_key, {})
            if alerts != new_alerts:
                alerts.update(new_alerts)
                rcache_set(cc_key, alerts)
            '''
            # режим замены существующих
            rcache_set(cc_key, new_alerts)
        # for pid in places
# decode_pb2


if __name__ == '__main__':
    DEBUG = 'DEBUG' in sys.argv
    if DEBUG and len(sys.argv) == 3:
        try:
            DEBUG = int(sys.argv[-1])
        except:
            pass
    update(DEBUG=DEBUG)