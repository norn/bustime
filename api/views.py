import os
from django.conf import settings
from bustime.models import *
from bustime.views import city_autodetect, get_avg_temp
from django.http import HttpResponse
import sqlite3
from django.shortcuts import get_object_or_404
import ujson


def db_version(request):
    statbuf = os.stat('%s/static/mobile.db' % settings.PROJECT_DIR)
    result = datetime.datetime.fromtimestamp(statbuf.st_mtime)
    result = str(result)
    return HttpResponse(result)


def dump_version(request):
    statbuf = os.stat('%s/static/mobile.dump.gz' % settings.PROJECT_DIR)
    result = datetime.datetime.fromtimestamp(statbuf.st_mtime)
    result = str(result)
    return HttpResponse(result)


def boologic(a):
    if a:
        return 1
    else:
        return 0


def detect_city(request):
    city = city_autodetect(request.META['REMOTE_ADDR'])
    return HttpResponse(city.id)


def db_update():
    conn = sqlite3.connect(settings.PROJECT_DIR + '/static/mobile_new.db')
    c = conn.cursor()

    for city in City.objects.all():
        data = (city.id, boologic(city.active), city.name)
        c.execute("INSERT INTO bustime_city VALUES (%s, %s, '%s')" % data)
    conn.commit()
    print "city done"

    for bus in Bus.objects.all():
        values = {"id": bus.id,
                  "active": bus.active,
                  "name": bus.name,
                  "distance": bus.distance,
                  "travel_time": bus.travel_time,
                  "description": bus.description,
                  "ttype": bus.ttype,
                  "napr_a": bus.napr_a,
                  "napr_b": bus.napr_b,
                  "route_start": bus.route_start,
                  "route_stop": bus.route_stop,
                  "route_real_start": bus.route_real_start,
                  "route_real_stop": bus.route_real_stop,
                  "route_length": bus.route_length,
                  "city_id": bus.city_id,
                  "order_": bus.order,
                  "discount": bus.discount}

        SQL = 'INSERT INTO bustime_bus (%s) VALUES (%s);' % (
            ",".join(values.keys()), ":" + ", :".join(values.keys()))
        c.execute(SQL, values)
    conn.commit()
    print "bus done"

    for stop in NBusStop.objects.all():
        values = {'id': stop.id, 'name': stop.name, 'name_alt': stop.name_alt, 'point_x':
                  stop.point.x, 'point_y': stop.point.y, 'moveto': stop.moveto, 'city_id': stop.city_id, 'tram_only': stop.tram_only}
        SQL = 'INSERT INTO bustime_nbusstop (%s) VALUES (%s);' % (
            ",".join(values.keys()), ":" + ", :".join(values.keys()))
        c.execute(SQL, values)
    conn.commit()
    print "stop done"

    for route in Route.objects.all():
        values = {'id': route.id, 'bus_id': route.bus_id, 'busstop_id': route.busstop_id, 'endpoint':
                  route.endpoint, 'direction': route.direction, 'time_avg': route.time_avg, "order_": route.order}
        SQL = 'INSERT INTO bustime_route (%s) VALUES (%s);' % (
            ",".join(values.keys()), ":" + ", :".join(values.keys()))
        c.execute(SQL, values)
    conn.commit()
    print "route done"

    conn.close()
    return True


def weather(request, city_id):
    try:
        city_id = int(city_id)
    except:
        city_id = "0"
    city = get_object_or_404(City, id=city_id)
    return HttpResponse("%s" % get_avg_temp(city))


def ads_control(request):
    # Je ne mange pas six jours
    active_android, active_ios = True, True
    now = datetime.datetime.now()
    if now.date().day % 2 == 1:
        #active_android = False
        active_ios = False
    data = {"start_from_session": 5, "active_android": active_android, "active_ios": active_ios,
            "click_request": False, "start_from_bus": 0}
    serialized = ujson.dumps(data)
    return HttpResponse(serialized)
