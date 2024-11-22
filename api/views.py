# -*- coding: utf-8 -*-
"""
После правки этого файла сделать ./1restart
"""
from __future__ import absolute_import
import os
# для корректной работы всякого вида encode/decode с utf-8
import sys
import xml.etree.ElementTree as ET

import api.jsonrpc
import ujson
import json
from api.models import *
from django.conf import settings
from django.contrib.auth.models import Group
from django.contrib.gis.geos import Point
from django.http import HttpResponse, HttpResponseNotFound
from django.shortcuts import get_object_or_404
from django.http import Http404
from django.views.decorators.csrf import csrf_exempt
from six.moves.urllib.parse import unquote

from bustime.models import *
from bustime.views import ajax_stop_id_f, city_autodetect, get_avg_temp, get_user_settings, detect_place_by_ip
import traceback
import six
import datetime
import re
from collections import defaultdict

def db_version(request):
    statbuf = os.stat('%s/static/mobile.db' % settings.PROJECT_DIR)
    result = datetime.datetime.fromtimestamp(statbuf.st_mtime)
    result = str(result)
    return HttpResponse(result)


def dump_version(request):
    result = api.jsonrpc.dump_version_()
    return HttpResponse(result)


def detect_city(request):
    ip = get_client_ip(request)
    place = detect_place_by_ip(ip)
    return HttpResponse(place.id)


def ip(request):
    ip = get_client_ip(request)
    return HttpResponse(ip)


def weather(request, city_id):
    try:
        city_id = int(city_id)
    except Exception:
        city_id = "0"
    place = get_object_or_404(Place, id=city_id)
    return HttpResponse("%s" % get_avg_temp(place))


def ads_control(request):
    # Je ne mange pas six jours
    active_android, active_ios = True, True
    now = datetime.datetime.now()
    click_request = False

    data = {"start_from_session": 5,
            "active_android": active_android,
            "active_ios": active_ios,
            "click_request": click_request,
            "start_from_bus": 0}
    serialized = ujson.dumps(data)
    return HttpResponse(serialized)


@csrf_exempt
def upload(request, city_slug=None):
    d = request.POST.get("data", '')
    now = datetime.datetime.now()
    city = None
    if city_slug:
        try:
            if city_slug.endswith("/"):
                city_slug = city_slug[:-1]
            city = Place.objects.get(slug=city_slug)
        except:
            pass
    if not city:
        with open('/tmp/api.upload.log', 'a') as f:
            f.write("%s: no city %s\n" % (now, city_slug))
        return HttpResponse("no city")
    if not d and request.body:
        d = request.body
    #with open('/tmp/api.upload.log', 'a') as f:
    #    f.write("%s: upload city.id=%s len=%s\n" % (now, city.id, len(d)))
    metric("api_upload__%s" % city.id)
    rcache_set("api_upload__%s" % city.id, d)

    return HttpResponse("%s, len=%s" % (city.id, len(d)))
# upload


@csrf_exempt
def upload_yproto(request, city_slug=None):
    '''
    сюда направляет api/urls.py POST запросы вида
    https://domain/api/upload/yproto/test-city/
    form-data: xml-данные
    '''
    if not city_slug:
        return HttpResponse("no city")

    xml = request.POST.get("data", '')
    if not xml:
        return HttpResponse("No data")

    city_slug = city_slug.replace("/", "")
    REDIS_W.publish('yaproto_%s' % city_slug, ujson.dumps({'xml': xml}))
    # для контроля городов (для каждого city_slug нужно добавить запуск обработчика в супервизор)
    f = open("/tmp/upload_yaproto_%s.log" % city_slug, "w")
    f.write("%s\n\n" % ujson.dumps({'xml': xml}))
    f.close()
    # см. coroutines/yandex_proto.py

    return HttpResponse("<forwarded>true</forwarded>")
# def upload_yproto


@csrf_exempt
def jsonrpc(request):
    ip = get_client_ip(request)
    PERFMON_START = datetime.datetime.now()
    jsonrpc = request.body
    if not jsonrpc:
        return HttpResponse("no data")
    else:
        jsonrpc = ujson.loads(jsonrpc)
        jsonrpc = JSONRPC(**jsonrpc)    # api/models.py, class JSONRPC

    error = None
    if not jsonrpc.method:  # если jsonrpc.method in ['', None, 0]
        error = api.jsonrpc.api_error(1)
        message = "%s\n%s" % (api.jsonrpc.API_ERRORS[1], request.body)
        log_message(message, ttype="jsonrpc")
    else:
        uuid = jsonrpc.params.get('uuid')
        os = jsonrpc.params.get('os')
        ms_id = jsonrpc.params.get('ms_id')
        driver_city = jsonrpc.params.get('driver_city')
        try:
            version = int(re.split(r"[ _]", jsonrpc.params.get("version",'0').replace(".",''))[0])
        except:
            version = 0
        os_version = jsonrpc.params.get("os_version")

        app_language_available = ["ru", "en", "fi", "es", "ua", "by", "et", "it", "cs", "de", "fr", "hu", "lt", "lv", "nl", "pl", "pt", "dk"]
        if os:
            if uuid:
                ms, cr = MobileSettings.objects.get_or_create(os=os, uuid=uuid)
            elif ms_id:
                ms, cr = MobileSettings.objects.get_or_create(os=os, id=ms_id)
            else:
                ms, cr = MobileSettings.objects.create(os=os), True
            jsonrpc.params['created'] = cr
            ms_save = False
            if driver_city:
                if cr:
                    ms.name = str(ms.id)
                    ms_save = True
                if cr or ms.mode != 2 or ms.place != PLACE_MAP[int(driver_city)]:
                    ms.place = PLACE_MAP[int(driver_city)]
                    if version < 211:
                        ms.language = ms.place.country.language
                    ms.mode = 2
                    ms_save = True
            elif not ms.place:
                ms.city = city_autodetect(ip)
                ms.place = detect_place_by_ip(ip)
                ms.language = "en"
                if ms.place:
                    if ms.os == "ios" and ms.place.country.language in ['en', 'ru', 'es', 'fi']:
                        ms.language = ms.place.country.language
                    elif ms.os == "android" and ms.place.country.language in app_language_available:
                        ms.language = ms.place.country.language
                if version < 211 and ms.language not in ['ru', 'es', 'fi']:
                    ms.language = "en"

                # sio_pub for special online report installs page
                dat = {"uuid": ms.uuid[0:5], 'action':"app_install", "language":ms.language, "place":str(ms.place), 'version':version, 'ctime':str(ms.ctime.date()), 'os':ms.os, "os_version": os_version}
                sio_pub("_kitchen", dat)

                ms_save = True
            if not ms.place or not ms.place.available:
                ms.city = None
                ms.place = None
                ms.language = "en"
                ms_save = True
            if ms_save:
                ms.save()
        else:
            try:
                if ms_id:
                    ms = MobileSettings.objects.get(id=ms_id)
                else:
                    ms = MobileSettings.objects.get(uuid=uuid)
            except Exception:
                error = api.jsonrpc.api_error(3)
    PERFMON_M = datetime.datetime.now()

    if not error:
        method = getattr(api.jsonrpc, jsonrpc.method, None)

        if method:
            if jsonrpc.method == "user_get":
                resp = method(ms, jsonrpc.params, ip=ip)
            else:
                resp = method(ms, jsonrpc.params)
            resp = JSONRPC(id=jsonrpc.id, **resp).render()
        else:   # если имя метода не найдено в jsonrpc.py
            error = api.jsonrpc.api_error(2)
            message = "%s\n%s" % (api.jsonrpc.API_ERRORS[2], request.body)
            log_message(message, ttype="jsonrpc")

    if error:
        resp = JSONRPC(id=jsonrpc.id, **error).render()

    PERFMON_STOP = datetime.datetime.now()
    d1 = (PERFMON_M - PERFMON_START).total_seconds()
    d2 = (PERFMON_STOP - PERFMON_M).total_seconds()
    d3 = (PERFMON_STOP - PERFMON_START).total_seconds()

    def default(o):
        if isinstance(o, (datetime.date, datetime.datetime)):
            return o.timestamp()
    return HttpResponse(json.dumps(resp, default=default), content_type="application/json")

@csrf_exempt
def ostapon(request):
    ip = get_client_ip(request)
    jsonrpc = request.body
    if not jsonrpc:
        return HttpResponse("no data")
    else:
        jsonrpc = ujson.loads(str(jsonrpc))

    game_code = jsonrpc['params']['game_code']
    method = jsonrpc['method']
    json_response = {}

    key = ''
    if method == 'static':
        key = game_code + '_' + method
        data = get_setting(key)
    elif method == 'levels_get':
        key = game_code + '_' + 'levels'
        data = get_setting(key)
    elif method == 'levels_set':
        key = game_code + '_' + 'levels'
        levels = jsonrpc['params']['levels']

        try:
            setting = Settings.objects.filter(key=key)[0]
            setting.value_string = json.dumps(levels)
            setting.save()
            data = 'good!'
        except Exception as e:
            data = e

    json_response['data'] = data
    json_response['ip'] = ip
    json_response['server_time'] = datetime.datetime.now()

    return HttpResponse(ujson.dumps(json_response), content_type="application/json")

def headers(request):
    s = ""
    for k,v in request.META.items():
        if k.startswith("HTTP_"):
            s += "%s=%s<br/>" % (k,v)
    return HttpResponse(s)


def bsmart(request):
    h = request.GET.get("hash", "")
    d = float(request.GET.get("delta", 0))
    tm = datetime.datetime.now()
    ha = {"hash": h, "delta": d, "tm": tm}
    cc_key = "bsmart_hashes"
    a = rcache_get(cc_key, [])
    a.append(ha)
    rcache_set(cc_key, a, 60*10)
    return HttpResponse("")

def minime(request):
    x = request.GET.get('x')
    y = request.GET.get('y')
    x, y = float(x), float(y)
    pnt = Point(x,y)
    stops = NBusStop.objects.filter(point__distance_lte=(pnt, 1000))
    nearest = [500, None]
    for s in stops:
        dis = distance_meters(pnt.x, pnt.y, s.point.x, s.point.y)
        if dis < nearest[0]:
            nearest = [dis, s]
            
    send_data = {}
    if nearest[1]:
        serialized = ajax_stop_id_f([nearest[1].id], raw=True, mobile=True)
        good_data = []
        for bus in serialized['stops'][0]['data']:
            good_bus = {}
            db_bus = bus_get(bus['bid'])
            good_bus['type'] = db_bus.ttype
            good_bus['name'] = db_bus.name
            good_bus['time'] = bus['t']
            
            if 'l' in bus:
                if 'g' in bus['l']:
                    good_bus['gosnum'] = bus['l'].get('g', '')
                good_bus['ramp'] = bus['l']['r']
                good_bus['speed'] = bus['l']['s']
                good_bus['now_on'] = bus['l']['bn']
            good_data.append(good_bus)
        send_data['updated'] = serialized['stops'][0]['updated']
        send_data['stop_name'] = nearest[1].name
        send_data['stop_name_next'] = nearest[1].moveto
        send_data['buses'] = good_data

    data = json.dumps(send_data)
    return HttpResponse(data)#"%s %s %s" % (s.name, bus.name, jsonarray))

def stops_for_gps(request):
    x = request.GET.get('x')
    y = request.GET.get('y')
    x, y = float(x), float(y)
    pnt = Point(x,y)
    stops = NBusStop.objects.filter(point__distance_lte=(pnt, 1000))
    nearest = [500, None]

    nearest_array = []
    i = 0
    for s in stops:
        dis = distance_meters(pnt.x, pnt.y, s.point.x, s.point.y)
        nearest_array.append([i, dis])
        i = i + 1

    nearest_array.sort(key=lambda x: x[1])  # сорт по расстоянию
    nearest_array = nearest_array[:5]       # берём первые 5

    sorted_stops_ids = []
    for pair in nearest_array:
        index = pair[0]
        sorted_stops_ids.append(stops[index].id)

    send_data = []
    if len(sorted_stops_ids) > 0:
        serialized = ajax_stop_id_f(sorted_stops_ids, raw=True, mobile=True)
        i = 0
        for stop in serialized['stops']:
            bus_data = []
            for bus in stop['data']:
                good_bus = {}
                db_bus = bus_get(bus['bid'])
                good_bus['type'] = db_bus.ttype
                good_bus['name'] = db_bus.name
                good_bus['time'] = bus['t']

                if 'l' in bus:
                    if 'g' in bus['l']:
                        good_bus['gosnum'] = bus['l'].get('g', '')
                    good_bus['ramp'] = bus['l']['r']
                    good_bus['speed'] = bus['l']['s']
                    good_bus['now_on'] = bus['l']['bn']
                bus_data.append(good_bus)

            stop_data = {}
            stop_data['updated'] = stop['updated']

            stop_vo = stops[nearest_array[i][0]]
            stop_data['stop_name'] = stop_vo.name
            stop_data['stop_name_next'] = stop_vo.moveto
            stop_data['buses'] = bus_data
            send_data.append(stop_data)
            i = i + 1

    data = json.dumps(send_data)
    return HttpResponse(data)#"%s %s %s" % (s.name, bus.name, jsonarray))


def notify_stop(request): # подписка на остановку маршрута, возвращает прогноз
    try:
        stop_id = int(request.GET.get('stop_id', 0))
    except:
        stop_id = 0
    try:
        bus_id = int(request.GET.get('bus_id', 0))
    except:
        bus_id = 0

    if stop_id <= 0:
        data = {"detail": f"Wrong stop_id: {stop_id}"}
        return HttpResponse(json.dumps(data), status=HttpResponseNotFound.status_code)
    if bus_id <= 0:
        data = {"detail": f"Wrong bus_id: {bus_id}"}
        return HttpResponse(json.dumps(data), status=HttpResponseNotFound.status_code)

    serialized = ajax_stop_id_f([stop_id], raw=True, mobile=True)

    send_data = {}
    if serialized and len(serialized['stops']) > 0:
        for bus in serialized['stops'][0]['data']:
            db_bus = bus_get(bus['bid'])
            if not db_bus:
                continue
            if db_bus.id != bus_id:
                continue
            if 'bn' not in bus['l']:
                continue

            send_data['type'] = db_bus.ttype
            send_data['name'] = db_bus.name
            send_data['time'] = bus['t']
            if 'l' in bus:
                if 'g' in bus['l']: # госномер
                    send_data['gosnum'] = bus['l'].get('g', '')

                if 'u' in bus['l']: # уид
                    send_data['uid'] = bus['l'].get('u', '')

                send_data['ramp'] = bus['l']['r']
                send_data['speed'] = bus['l']['s']
                send_data['x'] = bus['l']['x']
                send_data['y'] = bus['l']['y']
                send_data['stop_name'] = ''

            break
        if not send_data:
            data = {"detail": f"Can't find info"}
            return HttpResponse(json.dumps(data), status = HttpResponseNotFound.status_code)
        send_data['updated'] = serialized['stops'][0]['updated']

    data = json.dumps(send_data)
    metric('api_notify_stop')
    return HttpResponse(data)#"%s %s %s" % (s.name, bus.name, jsonarray))


@csrf_exempt
def sms(request):
    """
    Это от андроид-приложения SMS Forwarder
    http://lanrensms.com/en/
    request.body = b'{"body":"5155960 110-From- +71111111111 ---2022-09-02 13:40:30","deviceId":"VFJXVgNeU1MHBlwABVVWUQ\\u003d\\u003d","otherProps":{"webUserName":"null"},"smsFrom":"+71111111111","smsId":"286","smsRecvTime":1662115230106}'

    Это от андроид-приложения Incoming SMS to URL forwarder
    https://github.com/bogkonstantin/android_income_sms_gateway_webhook
    request.body=b'{"from":"+71111111111","text":"4389 82229 308"}'
    или
    request.body=b'{\n  "from":"+71111111111",\n  "text":"5681 58244 600",\n  "sentStamp":1706085882000,\n  "receivedStamp":1706085884443,\n  "sim":"sim1"\n}'

    ff = open('/bustime/bustime/debug.txt', 'w')
    ff.write('api/views.py/sms()\n')
    ff.write('request.body=%s\n' % request.body)
    ff.close()
    """

    rcache_set("api_sms", request.body)
    try:
        js = json.loads(request.body)
    except:
        return HttpResponse("No body")

    if js.get('smsRecvTime'):   # SMS Forwarder
        rcv = js['smsRecvTime']
        rcv = datetime.datetime.fromtimestamp(rcv/1000.0)
        src = js['smsFrom'].replace("+", "")
        #dst = js['deviceId']
        dst = "71111111111"  # we don't care, solo
        text = js['body'].split("-From-")[0]    # 5155960 110
    else:   # Incoming SMS to URL forwarder
        rcv = datetime.datetime.now()
        src = js["from"].replace("+", "")
        dst = "71111111111"  # we don't care, solo
        text = js['text']

    text = text[:160]

    SMS.objects.create(
        received=rcv,
        src=src,
        dst=dst,
        text=text
        )

    # check if user exists
    user = User.objects.filter(username=src).first()
    if not user:
        user = User.objects.create_user(
            username=src, is_staff=True
        )
        sms_group = Group.objects.get(name='sms')
        sms_group.user_set.add(user)
    else:
        if not user.is_active:
            return HttpResponse("{}")
    # clear input - only digits
    text = re.sub("\D", "", text)   # 5155960110
    try:
        uid, pin = text[:-3], text[-3:] # 5155960, 110
        uid = int(uid)
    except:
        uid = None

    # make it connected with pin verify
    for ms in MobileSettings.objects.filter(id=uid):
        pin_real = make_user_pin(ms.id) # bustime/models.py
        if pin == pin_real:
            if not ms.is_banned():
                ms.user = user
                ms.save()
                wsocket_cmd('reload', {}, ms_id=ms.id)

    for us in UserSettings.objects.filter(id=uid):
        pin_real = make_user_pin(us.id)
        if pin == pin_real:
            if not us.is_banned():
                us.user = user
                us.save()
                wsocket_cmd('reload', {}, us_id=us.id)  # bustime/models.py

    metric('api_sms')
    return HttpResponse("{}")


def git(request):
    now = datetime.datetime.now()
    with open('/tmp/api.git.log', 'a') as f:
        f.write("%s\n" % (now))

    xgt = 'X-Gitlab-Token'
    if request.headers.get(xgt) == settings.GIT_WEBHOOK_MF:
        event = request.headers['X-Gitlab-Event']
        js = json.loads(request.body.decode('utf-8'))
        prj = js['project']['web_url']
        REDIS_W.publish('_bot_dev', '%s: %s pushed %s commits to %s' % (prj, js.get('user_username'), js.get('total_commits_count'), js['ref']))

    return HttpResponse("ok")


def countries_with_places(request):
    countries = {}
    country_cities = defaultdict(list)
    places = {p['id']: p for p in Place.objects.filter(id__in=places_filtered())\
        .values().order_by("name")}
    pipe = REDIS.pipeline()
    amounts = []
    for pid in places.keys():
        cc_key = "busamounts_%s" % pid
        busamounts = rcache_get(cc_key, {})
        amount = sum(busamounts.values())
        amounts.append(amount)

    for p in places.values():
        x, y = p['point'].x, p['point'].y
        p['bus_amounts'] = amounts.pop(0)
        p['name'] = p['tags'].get('name') or p['name']
        p['timezone'] = str(p['timezone'])
        p['point'] = {"x": x, "y": y}
        del p['tags']
        country_cities[p['country_code']].append(p)
    for c in Country.objects.filter().exclude(id=15).values():
        lang = c['language']
        name = c['tags'].get(f'name:{lang}') or c['tags']['name']
        countries[c['code']] = c
        countries[c['code']]['name'] = name
        countries[c['code']]['cities'] = country_cities[c['code']]
        del c['register_phone']
        del c['tags']
    return HttpResponse(json.dumps({k: v for k, v in countries.items() if v['cities']}))
