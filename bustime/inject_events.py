#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
при изменении этого файла выдать комнду:
sudo supervisorctl restart rpc_servers:*
"""

from __future__ import absolute_import
from datetime import timedelta, datetime
from bustime.models import (Event, bus_get, us_get, ms_get, rcache_get,
                            rcache_set, REDIS_W, distance_meters, metric, log_message, sio_pub, pickle_dumps,
                            timezone_finder)
from zoneinfo import ZoneInfo
from taxi.models import taxiuser_get, Tevent
from django.forms.models import model_to_dict
import six
import traceback
import json
import sys


def to_bool(v):
    if not (type(v) is bool or v is None):
        if type(v) is int:
            return v > 0
        elif type(v) is six.text_type:
            return v.lower() == u'true'
        elif type(v) is str:
            return v.lower() == 'true'
    return False


def calc_delta(x, y, lon, lat):
    if x and lon:
        return int(distance_meters(x, y, lon, lat) * 1.05)
    return 0


def inject_custom(data):
    """
    Пример данных водителя при самостоятельной отправке:
    data={"lat": 55.755826, "lon": 37.6173, "accuracy": 300, "us_id": 347608048, "speed": 0,
            "heading": 0, "timestamp": 1649665785326.0, "gosnum": "Р850ХО:, "bus_id": 1371, "proto": 2}
    """

    def nearest_place_by_bus(places, x, y):
        distances = {p: distance_meters(x, y, p.point.x, p.point.y) for p in places}
        distances = dict(sorted(distances.items(), key=lambda item: item[1]))
        return next(iter(distances.keys()))

    ff = None
    place = None
    try:
        us_id = int(data.get('us_id')) if data.get('us_id') else None
        ms_id = int(data.get('ms_id')) if data.get('ms_id') else None
        if us_id:
            uniqueid = u'us_%s' % data['us_id']
            #uniqueid = unicode(data['us_id'])
            user = us_get(us_id)
            user_id = us_id
            channel = "inject_web"
        elif ms_id:
            uniqueid = u'ms_%s' % data['ms_id']
            #uniqueid = unicode(data['ms_id'])
            user = ms_get(ms_id)
            user_id = ms_id
            channel = "inject_app"
        else:
            raise ValueError(f"inject_custom: {data} doesn't contain ms_id or us_id")
        src = user_id
        # If user is banned or not exists, do nothing. All results is 0.
        if not user or user.is_banned():
            return 0, 0

        lng_range = (-180, 180)
        lat_range = (-90, 90)
        lon, lat = float(data['lon']), float(data['lat'])
        # if lon <= 0 or lat <= 0:
        #     raise ValueError("Lon and Lat values can't be less zero")
        if lng_range[0] > lon > lng_range[1]:
            raise ValueError(f"Longitude is out of range {lon}")
        if lat_range[0] > lat > lat_range[1]:
            raise ValueError(f"Latitude is out of range {lat}")

        accuracy = data.get('accuracy', 10)
        if accuracy:
            accuracy = int(float(accuracy))
            if accuracy > 300:
                # log_message("too big accuracy: %s" %
                #            accuracy, ttype="gps_send", user=user)
                return 0, 0
        speed = data.get('speed')
        if speed:
            speed = int(float(speed))
        else:
            speed = 24

        heading = data.get('heading', 0)
        if heading:
            heading = int(float(heading))

        # this test makes custom gps to duplicate any bus
        # if user.id in [56, 76920, 221037]:
        #    ae=rcache_get("allevents_11")
        #    ae = ae.get('event_11_1297392')
        #    if ae:
        #        lon, lat = ae.x, ae.y
        #        speed = ae.speed

        if not data.get('channel'):
            data['channel'] = channel
        if not data.get('src'):
            data['src'] = src

        if data.get('proto') and int(data.get('proto')) == 2:
            bus = bus_get(int(data['bus_id'])) if data.get('bus_id') else None
            if not bus:
                return -1, -1
            place = nearest_place_by_bus(bus.places.all(), x=lon, y=lat) # TODO (turbo) an old approach have to delete
            # now = place.now
            tz_info = timezone_finder.timezone_at(lng=lon, lat=lat)
            now = datetime.now(tz=ZoneInfo(tz_info)).replace(tzinfo=None)

            ramp = to_bool(data.get('ramp', None))
            rampp = to_bool(data.get('rampp', None))
            label = six.text_type(data.get('label'))
            if label:
                label = label.strip('\\\'"[]{}()*=.,:;_&?^%$#@!/').replace('None', '').strip()
                if len(label) == 0:
                    label = None

            e = Event(uniqueid=uniqueid,
                      timestamp=now,
                      x=lon, y=lat, bus=int(data['bus_id']),
                      heading=heading, speed=speed, custom=True,
                      gosnum=six.text_type(data.get('gosnum')),
                      label=label,
                      ramp=ramp,
                      rampp=rampp,
                      custom_src=user_id,
                      accuracy=accuracy,
                      channel=data['channel'],
                      src=data['src'])
        elif data.get('taxi'):
            # сохраняем отметку в БД
            odometer = 0
            return 0, 0
            # taxiuser = taxiuser_get(user.user.id)
            # if taxiuser and taxiuser['driver'] and 'car' in taxiuser:
            #     tevent = Tevent(taxiuser=taxiuser['id'],
            #                     gpstime=datetime.fromtimestamp( int(data['timestamp'] / 1000.0) ),
            #                     citytime=city.now,
            #                     x=lon,
            #                     y=lat,
            #                     speed=speed,
            #                     heading=heading,
            #                     accuracy=accuracy,
            #                     order=data.get('taxi_order')    # см. bustime_main.js, gps_send()
            #                     )
            #     tevent.save()
            #
            #     e = Event(uniqueid=taxiuser['id'],
            #               timestamp=city.now,
            #               x=lon, y=lat,
            #               heading=heading,
            #               speed=speed,
            #               custom=True,
            #               gosnum=taxiuser['car']['gos_num'],
            #               accuracy=accuracy,
            #               channel=data['channel'],
            #               src=data['src'])
            #     e['uniqueid'] = taxiuser['id']
            #     e['order'] = data.get('taxi_order')
            #
            #     cc_key = "tevents_%s" % city.id
            #     tevents = rcache_get(cc_key, {})
            #     prev = tevents.get(e.uniqueid, {})
            #     odometer = prev.get('odometer', 0) + calc_delta(prev.get('x', 0), prev.get('y', 0), lon, lat)
            #     if not odometer or odometer < 0:
            #         odometer = 0
            #     if prev.get('odometer_weekday', -1) != city.now.weekday():
            #         odometer = 0
            #     e['odometer'] = odometer
            #     e['odometer_weekday'] = city.now.weekday()
            #     e['taxi'] = taxiuser
            #     tevents[e.uniqueid] = e
            #     rcache_set(cc_key, tevents, 600)
            # return 0, odometer
        # if data.get('taxi')
        else:
            bus = user.gps_send_bus
            if not bus:
                return 0, 0
            place = nearest_place_by_bus(bus.places.all(), x=lon, y=lat) # TODO (turbo) an old approach have to delete
            # now = place.now
            tz_info = timezone_finder.timezone_at(lng=lon, lat=lat)
            now = datetime.now(tz=ZoneInfo(tz_info)).replace(tzinfo=None)

            ramp = to_bool(user.gps_send_ramp)

            e = Event(uniqueid=uniqueid,
                      timestamp=now,
                      x=lon,
                      y=lat,
                      bus=bus.id,
                      heading=heading,
                      speed=speed,
                      custom=True,
                      gosnum=six.text_type(user.gosnum),
                      ramp=user.gps_send_ramp,
                      custom_src=user.id,
                      accuracy=accuracy,
                      channel=data['channel'],
                      src=data['src'])

            tcolor = getattr(user, 'tcolor', None)
            tface = getattr(user, 'tface', None)
            driver_ava = getattr(user, 'driver_ava', None)
            name = getattr(user, 'name', None)
            rampp = getattr(user, 'gps_send_rampp', None)
            gps_send_of = getattr(user, 'gps_send_of', None)
            if tcolor:
                e['tcolor'] = tcolor
            if tface:
                e['tface'] = tface
            if driver_ava:
                e['driver_ava'] = driver_ava
            if name:
                e['name'] = name
            if rampp:
                e['rampp'] = rampp
            if gps_send_of:
                e['gps_send_of'] = gps_send_of  # uniqueid машины, которую заменяет эта машина
                # (см. process_list() in windmill.py & analyze_events() in update_lib.py)

        cc_key = f"turbo_{e.bus}"
        REDIS_W.publish(cc_key, pickle_dumps(e))

        REDIS_W.sadd('gevents_%s' % place.id, user_id)
        #ee = e.copy()
        cc_key = "gevent_%s" % e["custom_src"]
        prev = rcache_get(cc_key, {})
        if prev and prev.get('history'):
            e['history'] = [x for x in prev['history'] if x > now - timedelta(minutes=60)]
        else:
            e['history'] = []
        if user and user.gosnum and user.gosnum.strip():  # считать только если гос номер указан
            e['history'].append(e.timestamp)
        elif data.get('gosnum'):
            e['history'].append(e.timestamp)

        cnt = len(e['history'])
        rcache_set("gps_send_cnt_%s" % user_id, cnt, 60*60)
        metric('api_gps_send__%s' % place.id)
        odometer = prev.get('odometer', 0) + calc_delta(prev.get('x', 0), prev.get('y', 0), lon, lat)
        if not odometer or odometer < 0:
            odometer = 0
        if prev.get('odometer_weekday', -1) != now.weekday():
            odometer = 0
        e['odometer'] = odometer
        e['odometer_weekday'] = now.weekday()
        rcache_set(cc_key, e)
        rcache_set("gps_send_signal_%s" % bus.id, e.uniqueid, 60*60*24)  # notify
        chan = f"ru.bustime.bus_mode10__{bus.id}"
        sio_pub(chan, {"gps_send_signal": e.uniqueid})
    except:
        msg = "%s\ndata=%s" % (traceback.format_exc(), json.dumps(data, default=str))
        if place:
            log_message(msg, ttype="inject_custom", place=place)
        else:
            log_message(msg, ttype="inject_custom")
        return 0, 0
    return cnt, odometer
