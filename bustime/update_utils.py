#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
import codecs
import datetime
import hashlib
import os
import shutil
import tempfile
import time
import traceback
import jsbeautifier
from collections import defaultdict
from zoneinfo import ZoneInfo
from django.db.models import Count
from django.db import connections
from bustime import settings
from bustime.models import (REDIS, Bus, BusProvider, City, Country, Event, NBusStop,
                            Route, RouteLine, get_thumbnail, json, lotime, places_filtered,
                            ms_get, rcache_mget, rcache_set, us_get, wsocket_cmd, get_jams_for_city,
                            JamLine, Place, Unistop, PLACE_STAFF_MODIFY, PLACE_TRANSPORT_CARD,
                            buses_get, DataSourcePlaceEventsCount, Sum)
from six.moves import map
import six


# v5 version is 200

def jamlines_export(city):
    jamlines_path = "%s/../bustime/static/js" % settings.STATIC_ROOT
    file_name = "%s/jamline_%s_%s.js" % (
        jamlines_path, city.id, city.rev
    )
    r = get_jams_for_city(city=city)
    busstops_to = [d['busstop_to'] for d in r if 'busstop_to' in d]
    busstops_from = [d['busstop_from'] for d in r if 'busstop_from' in d]
    lines_qs = JamLine.objects.filter(busstop_from__in=busstops_from, busstop_to__in=busstops_to)
    jamlines = { "%s_%s" % (line.busstop_from, line.busstop_to): line.line.coords for line in lines_qs }
    with (tempfile.TemporaryFile(mode='w+', encoding='utf-8')) as tf:
        tf.write("var JAM_LINES=%s;" % json.dumps(jamlines, ensure_ascii=False))
        tf.seek(0)
        new_hash = hashlib.sha224(tf.read().encode("utf8")).hexdigest()
        if not os.path.exists(jamlines_path):
            os.makedirs(jamlines_path)
        if not os.path.exists(file_name):
            open(file_name, 'w').close()
        with (open(file_name, 'r+')) as curr_file:
            base_hash = hashlib.sha224(curr_file.read().encode("utf8")).hexdigest()
            if new_hash != base_hash:
                tf.seek(0)
                curr_file.seek(0)
                curr_file.write(tf.read())
                curr_file.truncate()
                curr_file.close()
                try:
                    os.symlink(file_name, "%s/js/jamline-%s-%s.js" %
                        (settings.STATIC_ROOT, city.id, city.rev))
                except FileExistsError:
                    pass
                return True
    return False



def city_data_export(city, reload_signal=True):
    """Export city data to JS file"""
    info_data = [u"Текущая ревизия = %s" % city.rev]

    fname = "%s/../bustime/static/js/city-%s-%s.js" % (settings.STATIC_ROOT, city.id, city.rev)
    try:
        f = open(fname, 'r')
        fhash = hashlib.sha224(f.read().encode("utf8")).hexdigest()
        f.close()
    except:
        fhash = "will rewrite for sure"
        info_data.append(traceback.format_exc(limit=1))

    tf = tempfile.TemporaryFile(mode='w+', encoding='utf-8')

    try:
        sdata = []

        '''
        names_done = {}
        for nb in NBusStop.objects.filter(city=city).order_by('name'):
            if not names_done.get(nb.name):
                ids = list(NBusStop.objects.filter(city=city, name=nb.name).order_by(
                                'id').values_list("id", flat=True))
                sdata.append({"value": nb.name, "ids": ids})
                names_done[nb.name] = 1

        время выполнения 24.020 seconds
        опитимизируем
        '''
        query = """SELECT name, array_agg(id) AS ids
                    FROM bustime_nbusstop
                    WHERE city_id = %s
                    GROUP BY name
                    ORDER BY name"""
        with connections['default'].cursor() as cursor:
            cursor.execute(query, [city.id])
            for row in cursor.fetchall():
                sdata.append({"value": row[0], "ids": sorted(row[1])})
        # время выполнения:  0.051 seconds

        tf.write("var stops=%s;" % json.dumps(sdata, ensure_ascii=False))

        bpdata = {}
        for bp in BusProvider.objects.filter(city=city).order_by('name'):
            bpdata[bp.id] = {"name": bp.name}
        tf.write("\nvar BUS_PROVIDERS=%s;" % json.dumps(bpdata, ensure_ascii=False))

        bdata = {}
        for b in Bus.objects.filter(city=city, active=True).order_by('order'):
            bdata[b.id] = {"name": b.name,
                           "slug": b.slug,
                           "ttype": b.ttype,
                           "price": b.price}
            if b.provider:
                bdata[b.id]['provider_id'] = b.provider_id
        # for b in Bus.objects.filter

        tf.write("\nvar BUSES=%s;" % json.dumps(bdata, ensure_ascii=False))
        tf.flush()
        tf.seek(0)
        tfhash = hashlib.sha224(tf.read().encode("utf8")).hexdigest()

        if fhash != tfhash:
            city.rev += 1
            print("REV PRE SAFE {}".format(city.rev))
            fname = "%s/../bustime/static/js/city-%s-%s.js" % (settings.STATIC_ROOT, city.id, city.rev)

            tf.seek(0)
            f = open(fname, 'w')
            f.write(tf.read())
            f.close()
            try:
                os.symlink(fname, "%s/js/city-%s-%s.js" % (settings.STATIC_ROOT, city.id, city.rev))
            except:
                pass

            city.save(update_fields=['rev'])
            info_data.append(u"Найдены и применены изменения для: %s" % city.name)
            info_data.append(u"Новая ревизия = %s" % city.rev)

            # auto reload connected clients
            if reload_signal:
                s = []
                us_onlines = REDIS.smembers("us_online")
                us_onlines = [us_id.decode('utf8') for us_id in us_onlines]
                for us_id in us_onlines:
                    us = us_get(us_id)
                    if us and us.city == city:
                        wsocket_cmd('reload', {}, us_id=us_id)
                        s.append(us_id)
                if len(s):
                    info_data.append(u"Перезагрузка мобильных клиентов: %s" % ", ".join(s))
            # if reload_signal

            # remove old:
            try:
                os.unlink("%s/js/city-%s-%s.js" % (settings.STATIC_ROOT, city.id, city.rev-2))
            except:
                pass
            try:
                os.remove("%s/../bustime/static/js/city-%s-%s.js" % (settings.STATIC_ROOT, city.id, city.rev-2))
            except:
                pass
        # if fhash != tfhash
        else:
            info_data.append(u"Нет изменений для: %s" % city.name)

        is_lines_updated = jamlines_export(city)
        if is_lines_updated:
            info_data.append(u'Найдены изменения JamLines [%s]' % city.name)
        else:
            info_data.append(u'Нет изменений JamLines [%s]' % city.name)
    except:
        info_data.append(traceback.format_exc(limit=2))
    finally:
        tf.close()

    return info_data
# city_data_export

def osm_data_export(city_id, reload_signal=True):
    """Export OSM data to JS file"""
    pa = Place.objects.get(id=city_id)
    info_data = [u"Текущая ревизия = %s" % pa.rev]

    fname = "%s/../bustime/static/js/city-%s-%s.js" % (settings.STATIC_ROOT, pa.id, pa.rev)
    try:
        f = open(fname, 'r')
        fhash = hashlib.sha224(f.read().encode("utf8")).hexdigest()
        f.close()
    except:
        fhash = "will rewrite for sure"
        info_data.append(traceback.format_exc(limit=1))

    tf = tempfile.TemporaryFile(mode='w+', encoding='utf-8')

    try:
        sdata = []
        query = """SELECT name, array_agg(id) AS ids
                    FROM bustime_nbusstop
                    WHERE city_id = %s
                    GROUP BY name
                    ORDER BY name"""
        with connections['default'].cursor() as cursor:
            cursor.execute(query, [city_id])
            for row in cursor.fetchall():
                sdata.append({"value": row[0], "ids": sorted(row[1])})
        tf.write("var stops=%s;" % json.dumps(sdata, ensure_ascii=False))

        bpdata = {}
        for bp in BusProvider.objects.filter(bus__places__id = str(city_id)).order_by('name'):
            bpdata[bp.id] = {"name": bp.name}
        tf.write("\nvar BUS_PROVIDERS=%s;" % json.dumps(bpdata, ensure_ascii=False))

        bdata = {}
        for b in buses_get(pa):
            bdata[b.id] = {"name": b.name,
                           "slug": b.slug,
                           "ttype": b.ttype,
                           "price": b.price}
            if b.provider:
                bdata[b.id]['provider_id'] = b.provider_id
        # for b in Bus.objects.filter

        tf.write("\nvar BUSES=%s;" % json.dumps(bdata, ensure_ascii=False))
        tf.flush()
        tf.seek(0)
        tfhash = hashlib.sha224(tf.read().encode("utf8")).hexdigest()

        if fhash != tfhash:
            pa.rev += 1
            print("REV PRE SAFE {}".format(pa.rev))
            fname = "%s/../bustime/static/js/city-%s-%s.js" % (settings.STATIC_ROOT, pa.id, pa.rev)

            tf.seek(0)
            f = open(fname, 'w')
            f.write(tf.read())
            f.close()
            try:
                os.symlink(fname, "%s/js/city-%s-%s.js" % (settings.STATIC_ROOT, pa.id, pa.rev))
            except:
                pass

            pa.save(update_fields=['rev'])
            info_data.append(u"Найдены и применены изменения для: %s" % pa.name)
            info_data.append(u"Новая ревизия = %s" % pa.rev)

            # auto reload connected clients
            # turbo todo
            """
            if reload_signal:
                s = []
                for us_id in REDISU.smembers("us_online"):
                    us = us_get(us_id)
                    if us and us.city == city:
                        wsocket_cmd('reload', {}, us_id=us_id)
                        s.append(us_id)
                if len(s):
                    info_data.append(u"Перезагрузка мобильных клиентов: %s" % ", ".join(s))
            # if reload_signal
            """
            # remove old:
            try:
                os.unlink("%s/js/city-%s-%s.js" % (settings.STATIC_ROOT, pa.id, city.rev-2))
            except:
                pass
            try:
                os.remove("%s/../bustime/static/js/city-%s-%s.js" % (settings.STATIC_ROOT, pa.id, pa.rev-2))
            except:
                pass
        # if fhash != tfhash
        else:
            info_data.append(u"Нет изменений для: %s" % pa.name)

        #is_lines_updated = jamlines_export(city)
        #if is_lines_updated:
        #    info_data.append(u'Найдены изменения JamLines [%s]' % city.name)
        #else:
        #    info_data.append(u'Нет изменений JamLines [%s]' % city.name)
    except:
        info_data.append(traceback.format_exc(limit=2))
    finally:
        tf.close()
    rcache_set(f"turbo_home__{pa.slug}", None)
    return info_data
# city_data_export


def boologic(a):
    if a:
        return 1
    else:
        return 0


def sqlitify(values, city=None):
    # values = map(lambda x: unicode(x.isoformat()) if type(x) == datetime.datetime else x, values)
    values = [int(time.mktime((x+datetime.timedelta(hours=city.timediffk)).timetuple())) if type(x) == datetime.datetime else x for x in values]
    values = [six.text_type(x.isoformat()) if type(x) == datetime.time else x for x in values]
    values = ["'%s'" % x.replace("'", "\"") if type(x) == six.text_type else x for x in values]
    values = [str(boologic(x)) if type(x) == bool else x for x in values]
    values = [str(x) if type(x) == int else x for x in values]
    values = [str(x) if type(x) == float else x for x in values]
    values = [x if x != None else "NULL" for x in values]
    return values


def sqlitify_turbo(values, tzinfo: ZoneInfo = None):
    values = [int(time.mktime((x.astimezone(tzinfo).replace(tzinfo=None)).timetuple())) if type(x) == datetime.datetime else x for x in values]
    values = [six.text_type(x.isoformat()) if type(x) == datetime.time else x for x in values]
    values = ["'%s'" % x.replace("'", "\"") if type(x) == six.text_type else x for x in values]
    values = [str(boologic(x)) if type(x) == bool else x for x in values]
    values = [str(x) if type(x) == int else x for x in values]
    values = [str(x) if type(x) == float else x for x in values]
    values = [x if x != None else "NULL" for x in values]
    return values


def mobile_update_v4(city, reload_signal=True, dbver="v4"):
    info_data = [u'mobile_update_v4 start:']
    P = settings.PROJECT_DIR + "/bustime/static/other/db/%s/current/" % dbver
    shutil.copyfile(P+'mobile_clean.dump', P+'%s.dump' % city.id)
    f = codecs.open(P+'%s.dump' % city.id, 'a', 'utf8')
    f.write("BEGIN TRANSACTION;\n")

    qs = Country.objects.filter(available=True).order_by("name")
    for c in qs:
        data = (c.id, boologic(c.available),
                c.name, c.code, c.language,
                c.domain)
        f.write(u"INSERT INTO bustime_country VALUES (%s, %s, '%s', '%s', '%s', '%s');\n" % data)

    # 59 Севастополь под санкциями
    if city.id != 59 and city.id != 74:
        qs = City.objects.filter(available=True, active=True).exclude(id=59).order_by("id")
    else:
        qs = City.objects.filter(available=True, active=True).order_by("id")

    for c in qs:
        data = (c.id, boologic(c.active), c.name, c.point.x, c.point.y, boologic(c.bus), boologic(
            c.trolleybus), boologic(c.tramway), boologic(c.bus_taxi), c.slug, c.gps_data_provider, c.gps_data_provider_url, c.country_id, boologic(c.transport_card))
        f.write(u"INSERT INTO bustime_city VALUES (%s, %s, '%s', %s, %s, %s, %s, %s, %s, '%s', '%s', '%s', %s, %s);\n" % data)

    for bus in Bus.objects.filter(active=True, city=city).order_by("id"):
        provider_name, provider_address, provider_phone = None, None, None
        if bus.provider:
            provider_name = bus.provider.name
            provider_address = bus.provider.address
            provider_phone = bus.provider.phone
        values = sqlitify([bus.id,
                           bus.active,
                           bus.name,
                           bus.distance,
                           bus.travel_time,
                           bus.description,
                           bus.order,
                           bus.ttype,
                           bus.napr_a,
                           bus.napr_b,
                           None,
                           None,
                           None,
                           None,
                           None,
                           bus.city_id,
                           bus.discount,
                           provider_name,
                           provider_address,
                           provider_phone])
        SQL = 'INSERT INTO bustime_bus VALUES (%s);\n' % (",".join(values))
        f.write(SQL)
    info_data.append(u"%s выгрузка маршрутов завершена" % city.name)

    for stop in NBusStop.objects.filter(city=city).order_by('id'):
        values = sqlitify([stop.id, stop.name, stop.name_alt, stop.point.x,
                           stop.point.y, stop.moveto, stop.city_id, stop.tram_only])
        SQL = 'INSERT INTO bustime_nbusstop VALUES (%s);\n' % (
            ",".join(values))
        f.write(SQL)
    info_data.append(u"%s выгрузка остановок завершена" % city.name)

    for route in Route.objects.filter(bus__city=city).order_by('id'):
        values = sqlitify([route.id, route.bus_id, route.busstop_id,
                           route.endpoint, route.direction, route.order, 0])
        SQL = 'INSERT INTO bustime_route VALUES (%s);\n' % (",".join(values))
        f.write(SQL)

    f.write("COMMIT;\n")
    f.close()
    info_data.append(u"City local time: %s: %s %s выгрузка завершена" % (lotime(city.now),
                                                                            city.name, dbver))
    info_data.append(u"mobile_update_v4 end.")
    return info_data


def cshort(x):
    if type(x) == tuple:
        return (round(x[0], 5), round(x[1], 5))
    return x


def turbo_mobile_update_v5_new(place, reload_signal=True, dbver="v5"):
    def replace_apostrophe(name):
        return name.replace("'", '`')

    # sort data providers based on event count (utils/update_event_counts.py)
    def events_count(ds):
        dspec = DataSourcePlaceEventsCount.objects.filter(place=place, datasource=ds).aggregate(total=Sum('ecnt'))
        return dspec['total'] or 0

    lang_map = defaultdict(lambda: 'en', {'ru': 'ru', 'by': 'ru', 'kz': 'ru', 'uz': 'ru'})
    info_data = [u"turbo_mobile_update_v5 start:"]
    # now = datetime.datetime.now(tz=place.timezone).replace(tzinfo=None)
    info_data.append(u"%s %s local time: %s, Выгрузка данных из БД" % (place.id, place.name, lotime(place.now)))
    P = settings.PROJECT_DIR + "/bustime/static/other/db/%s/current/" % dbver
    shutil.copyfile(P+'mobile_clean.dump', P+'%s.dump' % place.id)
    f = codecs.open(P+'%s.dump' % place.id, 'a', 'utf8')
    f.write("BEGIN TRANSACTION;\n")
    
    qs = Place.objects.filter(id__in=places_filtered())
    qs_coutnries = Country.objects.filter(code__in=qs.values_list('country_code')).exclude(id=15).distinct()

    for c in qs_coutnries:
        name_country = "name_" + c.language if c.language in ['ru', 'en'] else "name_" + lang_map[c.code]
        data = (c.id, boologic(1),
                c.__getattribute__(name_country), c.code, lang_map[c.code],
                c.domain)
        f.write(u"INSERT INTO bustime_country VALUES (%s, %s, '%s', '%s', '%s', '%s');\n" % data)

    for p in qs:
        # TODO (turbo) remove available for unlock all countries
        country = Country.objects.filter(code=p.country_code).exclude(id=15)
        if not country: continue
        country = country.first()
        name_attr = "name_" + country.language if country.language in ['ru', 'en'] else "name_" + lang_map[country.code]
        if not p.__getattribute__(name_attr):
            name_city = p.__getattribute__("name") if p.__getattribute__("name") else p.tags['name']
        else:
            name_city = p.__getattribute__(name_attr)
        name_city = replace_apostrophe(name_city)
        data_sources = p.datasource_set.all()
        providers = [(ds.gps_data_provider, ds.gps_data_provider_url, events_count(ds)) for ds in data_sources if ds.gps_data_provider is not None]   
        providers.sort(key=lambda x: x[2], reverse=True)     
        provider = next(iter(providers), ('', ''))
        p.gps_data_provider = provider[0]
        p.gps_data_provider_url = provider[1]
        p.transport_card = p.id in PLACE_TRANSPORT_CARD.keys()
        p.staff_modify = p.id in PLACE_STAFF_MODIFY.keys()
        # p.summer_time = datetime.datetime.now(p.timezone).dst() > datetime.timedelta(seconds=0)
        data = (p.id, boologic(p.active), name_city, p.point.x, p.point.y, p.slug, p.gps_data_provider, p.gps_data_provider_url, p.country_id, boologic(p.transport_card), boologic(p.staff_modify), boologic(p.summer_time))
        f.write(u"INSERT INTO bustime_city VALUES (%s, %s, '%s', %s, %s, '%s', '%s', '%s', %s, %s, %s, %s);\n" % data)

    buses = buses_get(place)
    provider_ids = {bus.provider.id for bus in buses if bus.provider is not None}
    info_data.append(u"маршрутов: %s" % len(buses))

    qs = BusProvider.objects.filter(id__in=provider_ids).order_by('id')
    cnt = qs.count()
    for p in qs:
        point_x, point_y = None, None
        if p.point:
            point_x, point_y = p.point.x, p.point.y
        logo = None
        if p.logo:
            logo = six.text_type(get_thumbnail(p.logo, '640x480', quality=85).url)
        values = sqlitify_turbo([p.id,
                           p.ctime,
                           p.mtime,
                           place.id,
                           p.name,
                           p.address,
                           p.phone,
                           p.email,
                           p.www,
                           logo,
                           point_x, point_y], tzinfo=place.timezone)
        SQL = 'INSERT INTO bustime_busprovider VALUES (%s);\n' % (",".join(values))
        f.write(SQL)
    info_data.append(u"перевозчиков: %s" % (cnt))

    bus_order = 0
    for bus in buses:
        bus_order += 1
        routeline = {0: [], 1: []}
        for rl in RouteLine.objects.filter(bus=bus, line__isnull=False):
            routeline[rl.direction] = list(map(cshort, rl.line.coords))
            # if bus.id in [371, 431, 1592]:
            #     routeline[rl.direction] = map(cshort, rl.line.coords)

            """
            3000-7500 работает
            3000-7000 работает
            3500-7000 не работает
            """
            # if len(json.dumps(routeline[rl.direction])) > 3250 and len(json.dumps(routeline[rl.direction])) < 3275:
            #     print bus.id

            # if len(json.dumps(routeline[rl.direction])) > 3275:
            #     routeline[rl.direction] = []
            # if len(json.dumps(routeline[rl.direction])) > 3500:
            #     routeline[rl.direction] = []

        routeline_0 = six.text_type(json.dumps(routeline[0]))
        routeline_1 = six.text_type(json.dumps(routeline[1]))
        # make it diff friendly
        #routeline_0 = routeline_0.replace('],', "],\n")
        #routeline_1 = routeline_1.replace('],', "],\n")
        provider_name, provider_address, provider_phone = None, None, None
        if bus.provider:
            provider_name = bus.provider.name
            provider_address = bus.provider.address
            provider_phone = bus.provider.phone
        # if bus.city.id == 5:
        #     bus.tt_start = None
        #     bus.tt_start_holiday = None
        '''
        Внимание: при изменении набора полей изменять DML
        CREATE TABLE "bustime_bus"
        в файле /bustime/bustime/bustime/static/other/db/v5/current/mobile_clean.dump
        так, чтобы струткура таблицы bustime_bus соответствовала этому набору полей.
        '''
        values = sqlitify_turbo([bus.id,
                           bus.active,
                           bus.name,
                           bus.distance,
                           bus.ttype * 10000 + bus_order,
                           bus.ttype,
                           place.id,
                           bus.discount,
                           provider_name,
                           provider_address,
                           provider_phone,
                           bus.provider_id,
                           routeline_0,
                           routeline_1,
                           bus.tt_start,
                           bus.tt_start_holiday,
                           bus.interval,
                           bus.payment_method,
                           bus.description,
                           bus.price,
                           bus.ctime,
                           bus.mtime,
                           bus.onroute,
                           bus.onroute_weekend], tzinfo=place.timezone)
        SQL = 'INSERT INTO bustime_bus VALUES (%s);\n' % (",".join(values))
        f.write(SQL)

    qs = Route.objects.filter(bus__in=buses).order_by('id')
    cnt = qs.count()
    routes = list(qs)
    busstop_ids = {route.busstop_id for route in routes}

    qs = NBusStop.objects.filter(id__in=busstop_ids).order_by('id')
    # qs = NBusStop.objects.filter(city=city).order_by('id')
    cnt = qs.count()
    for stop in qs:
        values = sqlitify_turbo([stop.id, stop.name, stop.point.x,
                           stop.point.y, place.id, stop.tram_only])
        SQL = 'INSERT INTO bustime_nbusstop VALUES (%s);\n' % (
            ",".join(values))
        f.write(SQL)
    info_data.append(u"остановок: %s" % (cnt))

    for route in routes:
        values = sqlitify_turbo([route.id, route.bus_id, route.busstop_id,
                           route.direction, route.order])
        SQL = 'INSERT INTO bustime_route VALUES (%s);\n' % (",".join(values))
        f.write(SQL)
    info_data.append(u"остановко-маршрутов: %s" % (cnt))


    f.write("COMMIT;\n")
    f.close()

    info_data.append(P+'%s.dump' % place.id)

    # process v7 here also
    if dbver == "v5":
        P1 = settings.PROJECT_DIR + "/bustime/static/other/db/%s/current/" % dbver
        P2 = settings.PROJECT_DIR + "/bustime/static/other/db/%s/current/" % "v7"
        shutil.copyfile(P1+'%s.dump' % place.id, P2+'%s.dump' % place.id)
        info_data.append(P2+'%s.dump' % place.id)

    # auto reload connected clients
    # s = []
    #if reload_signal:
    #    for ms_id in REDISU.smembers("ms_online"):
    #        ms = ms_get(ms_id)
    #        if ms and ms.version >=150 and ms.city == city:
    #            wsocket_cmd('reload', {}, ms_id=ms_id)
    #            s.append(ms_id)
    #if reload_signal:
    #    info_data.append(u"Перезагрузка: %s" % ", ".join(s))
    now = datetime.datetime.now(tz=place.timezone).replace(tzinfo=None)
    info_data.append(u"%s local time: %s: выгрузка завершена" % (place.name, lotime(now)))
    info_data.append(u"mobile_update_v5 end.")
    return info_data
# def turbo_mobile_update_v5(city, reload=True, dbver="v5")


def turbo_mobile_update_v8(place, reload_signal=True, dbver="v8"):
    def replace_apostrophe(name):
        return name.replace("'", '`')

    lang_map = defaultdict(lambda: 'en', {'ru': 'ru', 'by': 'ru', 'kz': 'ru', 'uz': 'ru'})

    info_data = [u"mobile_update_v8_turbo start:"]
    info_data.append(u"%s %s, Выгрузка данных из БД" % (place.id, place.name))
    P = settings.PROJECT_DIR + "/bustime/static/other/db/%s/current/" % dbver
    f = codecs.open(P+'%s.json' % place.id, 'w', 'utf8')

    data = {"country__meta": {"fields": []},
            "country": {},
            "place__meta":{"fields": []},
            "place": {},
            "datasource__meta":{"fields": []},
            "datasource": {},
            "busprovider__meta":{"fields": []},
            "busprovider": {},
            "bus__meta":{"fields": []},
            "bus": {},
            "nbusstop__meta":{"fields": []},
            "nbusstop": {},
            "route__meta":{"fields": []},
            "route": {}}

    #place
    p = Place.objects.get(id=place.id)
    country = Country.objects.filter(code=p.country_code).exclude(id=15)
    country = country.first()

    if country:
        name_attr = "name_" + country.language if country.language in ['ru', 'en'] else "name_" + lang_map[country.code]
        if not p.__getattribute__(name_attr):
            name_city = p.__getattribute__("name") if p.__getattribute__("name") else p.tags['name']
        else:
            name_city = p.__getattribute__(name_attr)
        name_city = replace_apostrophe(name_city)
    else:
        name_city = p.__getattribute__("name")

    data_sources = p.datasource_set.all()
    providers = [(ds.gps_data_provider, ds.gps_data_provider_url) for ds in data_sources if ds.gps_data_provider is not None]
    provider = next(iter(providers), ('', ''))
    p.gps_data_provider = provider[0]
    p.gps_data_provider_url = provider[1]
    p.transport_card = p.id in PLACE_TRANSPORT_CARD.keys()
    p.staff_modify = p.id in PLACE_STAFF_MODIFY.keys()
    # p.summer_time = datetime.datetime.now(p.timezone).dst() > datetime.timedelta(seconds=0)

    data_place_fields = ["active", "name", "point_x", "point_y", "slug", "gps_data_provider", "gps_data_provider_url", "country_id", "transport_card", "staff_modify", "summer_time" ]
    data["place__meta"]["fields"] = data_place_fields

    data_place = [boologic(p.active),
                  name_city,
                  p.point.x,
                  p.point.y,
                  p.slug,
                  p.gps_data_provider,
                  p.gps_data_provider_url,
                  p.country_id,
                  boologic(p.transport_card),
                  boologic(p.staff_modify),
                  boologic(p.summer_time)]
    data["place"][p.id] = data_place

    #country
    data_country_fields = ["available", "name", "code", "language", "domain"]
    data["country__meta"]["fields"] = data_country_fields
    if country:
        name_country = "name_" + country.language if country.language in ['ru', 'en'] else "name_" + lang_map[country.code]
        data_country = [boologic(1),
                        country.__getattribute__(name_country),
                        country.code,
                        lang_map[country.code],
                        country.domain]
        data["country"][country.id] = data_country


    #datasource
    data_sources = p.datasource_set.all()
    data_datasource_fields = ["active", "gps_data_provider", "gps_data_provider_url", "check_url", "block_info", "comment", "dispatchers", "bus_taxi_merged", "places"]
    data["datasource__meta"]["fields"] = data_datasource_fields

    for ds in data_sources:
        if ds.gps_data_provider: # только офиц источники
            datasource_dispatchers = [disp.id for disp in ds.dispatchers.all()] if ds.dispatchers.exists() else []
            datasource_places = [place.id for place in ds.places.all()] if ds.places.exists() else []
            data_datasource = [boologic(ds.active),
                               ds.gps_data_provider,
                               ds.gps_data_provider_url,
                               ds.check_url,
                               ds.block_info,
                               ds.comment,
                               datasource_dispatchers,
                               boologic(ds.bus_taxi_merged),
                               datasource_places]
            data["datasource"][ds.id] = data_datasource

    #busprovider
    buses = buses_get(place)
    provider_ids = {bus.provider.id for bus in buses if bus.provider is not None}

    qs = BusProvider.objects.filter(id__in=provider_ids).order_by('id')
    data_busprovider_fields = ["ctime", "mtime", "place_id", "name", "address", "phone", "email", "www", "logo", "point_x", "point_y"]
    data["busprovider__meta"]["fields"] = data_busprovider_fields
    cnt = qs.count()

    for p in qs:
        point_x, point_y = None, None
        if p.point:
            point_x, point_y = p.point.x, p.point.y
        logo = None
        if p.logo:
            logo = six.text_type(get_thumbnail(p.logo, '640x480', quality=85).url)
        data_busprovider = [p.ctime.isoformat(),
                            p.mtime.isoformat(),
                            place.id,
                            p.name,
                            p.address,
                            p.phone,
                            p.email,
                            p.www,
                            logo,
                            point_x,
                            point_y]
        data["busprovider"][p.id] = data_busprovider
    info_data.append(u"перевозчиков: %s" % (cnt))

    #bus
    data_bus_fields = ["active", "name", "slug", "distance", "order", "ttype", "place_id", "discount", "provider_name", "provider_address", "provider_phone", "provider_id",
                       "routeline_0", "routeline_1", "tt_start", "tt_start_holiday", "interval", "payment_method", "description", "price", "ctime", "mtime", "onroute", "onroute_weekend"]
    data["bus__meta"]["fields"] = data_bus_fields

    cnt = 0
    bus_order = 0
    for bus in buses:
        bus_order += 1
        cnt += 1
        routeline = {0: [], 1: []}
        for rl in RouteLine.objects.filter(bus=bus, line__isnull=False):
            # makes route line uglier, but give less of dump size
            rl.line = rl.line.simplify(tolerance=0.000002, preserve_topology=True)
            routeline[rl.direction] = list(map(cshort, rl.line.coords))
        routeline_0 = str(routeline[0])
        routeline_1 = str(routeline[1])

        provider_name, provider_address, provider_phone = None, None, None
        if bus.provider:
            provider_name = bus.provider.name
            provider_address = bus.provider.address
            provider_phone = bus.provider.phone
        if place.id == 5:
            bus.tt_start = None
            bus.tt_start_holiday = None

        try:
            bus.tt_start = str(json.loads(bus.tt_start))
        except:
            pass
        try:
            bus.tt_start_holiday = str(json.loads(bus.tt_start_holiday))
        except:
            pass

        data_bus = [bus.active,
                    bus.name,
                    bus.slug,
                    bus.distance,
                    bus.ttype * 10000 + bus_order,
                    bus.ttype,
                    place.id,
                    bus.discount,
                    provider_name,
                    provider_address,
                    provider_phone,
                    bus.provider_id,
                    routeline_0,
                    routeline_1,
                    bus.tt_start,
                    bus.tt_start_holiday,
                    bus.interval,
                    bus.payment_method,
                    bus.description,
                    bus.price,
                    bus.ctime.isoformat(),
                    bus.mtime.isoformat(),
                    bus.onroute,
                    bus.onroute_weekend]
        data["bus"][bus.id] = data_bus
    info_data.append(u"маршрутов: %s" % (cnt))

    #nbusstop
    qs = Route.objects.filter(bus__in=buses).order_by('id')
    cnt = qs.count()
    routes = list(qs)
    busstop_ids = {route.busstop_id for route in routes}

    qs = NBusStop.objects.filter(id__in=busstop_ids).order_by('id')
    data_nbusstop_fields = ["name", "point_x", "point_y", "slug", "place_id", "tram_only", "unistop"]
    data["nbusstop__meta"]["fields"] = data_nbusstop_fields
    cnt = qs.count()

    for stop in qs:
        data_nbusstop = [stop.name,
                         stop.point.x,
                         stop.point.y,
                         stop.slug,
                         place.id,
                         stop.tram_only,
                         stop.unistop_id]

        data["nbusstop"][stop.id] = data_nbusstop

    info_data.append(u"остановок: %s" % (cnt))

    #route
    data_route_fields = ["bus_id", "busstop_id", "direction", "order"]
    data["route__meta"]["fields"] = data_route_fields

    cnt = 0
    for route in routes:
        cnt += 1
        data_route = [route.bus_id,
                      route.busstop_id,
                      route.direction,
                      route.order]
        data["route"][route.id] = data_route
    info_data.append(u"остановко-маршрутов: %s" % (cnt))


    # json без отступов внутри ключа
    # https://beautifier.io/
    opts = jsbeautifier.default_options()
    opts.indent_size = 2
    opts.wrap_line_length=160
    data_json = jsbeautifier.beautify(json.dumps(data, ensure_ascii=False), opts)
    f.write(data_json)
    f.close()

    info_data.append(P+'%s.json' % place.id)
    info_data.append(u"%s: выгрузка завершена" % (place.name))
    info_data.append(u"mobile_update_v8_turbo end.")
    return info_data


def mobile_update_place(place, reload_signal=True):
    info_data = None
    info_data = turbo_mobile_update_v5_new(place, reload_signal=reload_signal)
    return info_data