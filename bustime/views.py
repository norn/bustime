# -*- coding: utf-8 -*-
from __future__ import absolute_import

import calendar
import collections
import copy
import datetime
import glob
import hashlib
import io as StringIO
import ipaddress
import itertools
import logging
import math
import os
import random
import re
import subprocess
import sys
import time
import urllib.parse
from ftplib import FTP
from functools import partial
from hashlib import md5
from typing import Dict, List, Optional
from stat import *

import pymorphy2
import requests
import reversion
import six
import ujson
import tempfile
import threading
import gevent

from bustime import gemy
from bustime.algorithms import all_shortest_paths
from bustime.models import *
from bustime.tcards import *
from bustime.update_utils import city_data_export, mobile_update_place
from bustime.utils import get_paths_from_busstops, get_gcity_from_ip, get_register_phone, find_routes_with_times, datetime_seconds_round_up
from dateutil.relativedelta import relativedelta
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.signals import user_logged_in
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.contrib import messages
from django.core import serializers
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured, PermissionDenied
from django.core.mail import send_mail
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db import connections, connection
from django.db.models import Q, Sum, Subquery, Count
from django.db.models.query import QuerySet
from django.dispatch import receiver
from django.forms.models import model_to_dict
from django.http import (Http404, HttpResponse, HttpResponseBadRequest,
                         HttpResponsePermanentRedirect, HttpResponseRedirect, JsonResponse)
from django.shortcuts import get_object_or_404, redirect, render
from django.template import RequestContext
from django.template.loader import render_to_string
from django.utils.translation import activate as translation_activate, get_language_info
from django.utils.translation import check_for_language
from django.utils.translation import gettext as _
from django.views.decorators.cache import cache_page
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import MultipleObjectsReturned
from django_user_agents.utils import get_user_agent
from djantimat.helpers import PymorphyProc, RegexpProc
from ipwhois import IPWhois
from PIL import Image
from reversion.models import Revision, Version
from six.moves import map, range
from taxi.models import *
from subdomains.utils import reverse
from pathlib import Path
from collections import defaultdict
from bustime.osm_utils import update_bus_places

from .forms import BusNewForm, BusStopNewForm

LANGUAGE_SESSION_KEY = '_language'
EDEN = [0, 1, 2, 2, 2, 2, 2, 2, 2, 3]
DELTA_SECS = datetime.timedelta(seconds=15)
DELTA_AMOUNT_AGE = datetime.timedelta(minutes=15)
MORPH = pymorphy2.MorphAnalyzer()


def arender(request, template, ctx):
    if request.GET.get('t', -1) != -1:
        template = template.replace(".html", "-test.html")
        ctx['test'] = True
        ctx['noga'] = True
    if os.environ.get('DEBUG_JS'):
        ctx['test'] = True
        ctx['noga'] = True
    if os.environ.get('SOCKETOTO_PORT'):
        ctx['io_port'] = os.environ.get('SOCKETOTO_PORT')

    request.session['last_login'] = str(datetime.datetime.now().date())

    ctx['request'] = request
    ctx['domain'] = request.META.get("HTTP_HOST")  # .replace("www.", "")
    ctx['languages'] = sorted(settings.LANGUAGES, key=lambda x: x[1])

    # включить режим отладки
    if request.COOKIES.get('debug'):
        ctx['test'] = True
    if "user" in request:
      ctx['taxiuser'] = taxiuser_get(request.user.id)
      request.session['taxiuser'] = json.dumps(ctx['taxiuser'], default=str)

    return render(request, template, ctx)


def random_advice():
    advices = ["Удачи в дороге, хороших пассажиров!",
               "Без приключений!",
               "Быстрого пути!",
               "В добрый путь!",
               "Всегда зелёного света!",
               "Доброго пути!",
               "Желаю вылета без задержек!",
               "Интересных попутчиков!",
               "Комфортной езды!",
               "Красивых видов за окном :)",
               "Ни гвоздя, ни жезла!",
               "Попутного ветра!",
               "Приятного путешествия!",
               "Пусть не будет на пути ни заторов, ни пробок, ни аварий!",
               "Сухого асфальта!",
               "Счастливо добраться!",
               "Счастливого пути!",
               "Тебе добраться и багажу не потеряться!",
               "Удачи на дорогах!",
               "Хорошей погоды в пути!"
               ]
    return advices[random.randint(0, len(advices)-1)]

@receiver(user_logged_in)
def post_login(sender, user, request, **kwargs):
    us = None
    session_key = request.session.session_key
    cc_key = "sess_%s" % (session_key)
    if session_key:
        sess = rcache_get(cc_key)
        if sess:
            us = us_get(sess)
        if not us:
            us, cr = UserSettings.objects.get_or_create(
                session_key=session_key)
            if cr:
                us.ip = get_client_ip(request)
                us.save()
            rcache_set(cc_key, us.id, 60*60*24)
        if not us.user and user.is_authenticated:
            us.user = user
            us.save()

def login_flowless(request, user, backend=None):
    from django.utils.module_loading import import_string
    from django.middleware.csrf import rotate_token
    from django.contrib.auth.signals import user_logged_in

    def load_backend(path):
        return import_string(path)()

    def _get_backends(return_tuples=False):
        backends = []
        for backend_path in settings.AUTHENTICATION_BACKENDS:
            backend = load_backend(backend_path)
            backends.append((backend, backend_path)
                            if return_tuples else backend)
        if not backends:
            raise ImproperlyConfigured(
                'No authentication backends have been defined. Does '
                'AUTHENTICATION_BACKENDS contain anything?'
            )
        return backends
    SESSION_KEY = '_auth_user_id'
    BACKEND_SESSION_KEY = '_auth_user_backend'
    HASH_SESSION_KEY = '_auth_user_hash'
    session_auth_hash = ''
    if user is None:
        user = request.user
    if hasattr(user, 'get_session_auth_hash'):
        session_auth_hash = user.get_session_auth_hash()

    try:
        backend = backend or user.backend
    except AttributeError:
        backends = _get_backends(return_tuples=True)
        if len(backends) == 1:
            _, backend = backends[0]
        else:
            raise ValueError(
                'You have multiple authentication backends configured and '
                'therefore must provide the `backend` argument or set the '
                '`backend` attribute on the user.'
            )

    request.session[SESSION_KEY] = user._meta.pk.value_to_string(user)
    request.session[BACKEND_SESSION_KEY] = backend
    request.session[HASH_SESSION_KEY] = session_auth_hash
    if hasattr(request, 'user'):
        request.user = user
    rotate_token(request)
    user_logged_in.send(sender=user.__class__, request=request, user=user)


def detect_bot_ua(ua):
    cua = '/addons/crawler-user-agents/crawler-user-agents.json'
    with open(settings.PROJECT_DIR + cua, 'r') as f:
        js = json.loads(f.read())
    for cua in js:
        if re.search(cua['pattern'], ua):
            return True
    if ua in ["www.ru", "", " "]:
        return True
    return False


def get_user_settings(request):
    now = datetime.datetime.now()
    user_agent = get_user_agent(request)
    session_key = request.session.session_key

    if session_key is None:
        request.session.create()
        session_key = request.session.session_key
        cc_key = "sess_%s" % (session_key)
        us, cr = UserSettings.objects.get_or_create(session_key=session_key)
        us.ip = get_client_ip(request)
        us.ua = request.META.get('HTTP_USER_AGENT', "")[:255]
        if cr:
            us.language = get_language_info(request.META.get('HTTP_ACCEPT_LANGUAGE', 'en')).get('code', 'en')
        us.ltime = now
        us.place = detect_place_by_request(request)
        us.save()
        rcache_set(cc_key, us.id, 60*60*24)

        if us.place:
            metric('new_user_%s' % us.place.id)
    else:
        cc_key = "sess_%s" % (session_key)
        sess = rcache_get(cc_key)

        if sess:
            us = us_get(sess)
        else:
            us = None

        if not us:
            try:
                us, cr = UserSettings.objects.get_or_create(session_key=session_key)
            except MultipleObjectsReturned:
                uss = UserSettings.objects.filter(session_key=session_key)
                us = uss[0]
                for i in uss[1:]:
                    i.delete()
                cr = False
            if cr:
                us.ip = get_client_ip(request)
                us.language = get_language_info(request.META.get('HTTP_ACCEPT_LANGUAGE', 'en')).get('code', 'en')
                us.ltime = now
                us.place = detect_place_by_request(request)
                us.save()
            rcache_set(cc_key, us.id, 60*60*24)

    if not us.place_id:
        us.place = detect_place_by_request(request)
        us.save()

    if us.user and us.user != request.user:
        login_flowless(request, us.user)

    return us


def human_time(updated, city=None):
    updated += datetime.timedelta(hours=city.timediffk)
    updated = six.text_type(updated).split('.')[0]
    updated = updated.split(' ')[1]
    return updated


def detect_ads_show(request, us):
    show = True
    # ip = request.META.get('REMOTE_ADDR', '0.0.0.0')
    ua = request.META.get('HTTP_USER_AGENT', "").upper()

    if us.premium or us.noads:
        show = False

    return show


def date_prefix(today):
    key = 'date_%s_%s_%s' % (today.year, today.month, today.day)
    return key


def city_autodetect(ip, country=None):
    city = None
    cities = None

    query = Q(active=True) & Q(available=True)
    if country:
        query &= Q(country=country)

    if ip:
        try:
            ipaddress.ip_address(ip)
            gcity = get_gcity_from_ip(ip)
            if gcity:
                p = Point(gcity.location.longitude, gcity.location.latitude)
                query &= Q(point__distance_lte=(p, D(km=1000)))
                cities = City.objects.filter(query).annotate(distance=Distance('point', p)).order_by('distance')
        except:
            pass

    if not cities:
        cities = City.objects.filter(query)

    try:
        city = cities.first()
    except:
        pass

    return city


def detect_place_by_ip(ip):
    try:
        ipaddress.ip_address(ip)
    except:
        return None
    gcity = get_gcity_from_ip(ip)
    if not gcity:
        return None

    p = Point(gcity.location.longitude, gcity.location.latitude)
    query = Q(point__distance_lte=(p, D(km=1000))) & Q(bus__isnull=False) & Q(id__in=places_filtered())
    place = Place.objects.filter(query).annotate(distance=Distance('point', p)).order_by('distance')
    place = place.first()

    return place


def detect_place_by_request(request):
    if len(request.META['PATH_INFO']) < 3:
        return None
    city_name = request.META['PATH_INFO'].split("/")[1] if len(request.META['PATH_INFO'].split("/")) > 1 else None
    path_info = request.META['PATH_INFO'].split("/")
    if len(path_info) > 1:
        return Place.objects.filter(slug=path_info[1]).first()
    else:
        return None


def classic_index(request):
    return HttpResponsePermanentRedirect("/")

# deprecated


def classic_routes(request, city_id=None, city_name=True):
    us = get_user_settings(request)
    if city_id:
        city = get_object_or_404(City, id=int(city_id))
    else:
        city = get_object_or_404(City, slug=city_name)
    return HttpResponsePermanentRedirect("/%s/schedule/" % (city.slug))

    buses = buses_get(city)
    counters_by_type = rcache_get("counters_by_type__%s" % city.id, {})
    for b in buses:
        b.gcnt = counters_by_type.get(b.ttype, 0)

    ctx = {"city": city, "buses": buses, "us": us,
           "classic": True, "counters_by_type": counters_by_type}
    return arender(request, "index-classic-routes.html", ctx)


def special_theme_selector(now):
    special_theme = None
    if now.month == 5 and now.day == 9:
        special_theme = "9may"
    return special_theme


def turbo_select(request):
    us = get_user_settings(request)
    if not us.place:
        place = detect_place_by_ip(get_client_ip(request))
    else:
        place = us.place

    countries = {}
    country_cities = defaultdict(list)
    places = {p.id: p for p in Place.objects.filter(id__in=places_filtered()).order_by("name")}

    pipe = REDIS.pipeline()
    amounts = []
    for pid in places.keys():
        cc_key = "busamounts_%s" % pid
        busamounts = rcache_get(cc_key, {})
        amount = sum(busamounts.values())
        amounts.append(amount)

    for p in places.values():
        p.amount = amounts.pop(0)
        p.avg_temp = avg_temp(p)
        country_cities[p.country_code].append(p)

    for c in Country.objects.filter().exclude(id=15):
        countries[c.code] = c.__dict__
        countries[c.code]['name'] = c.name
        countries[c.code]['cities'] = country_cities[c.code]

    first_one = None

    to_del=[]
    for k,v in countries.items():
        # print(k, len(v['cities']))
        if v['cities']:
            v['cities'] = sorted(v['cities'], key=lambda x: x.amount, reverse=True)
            if us.place:
                for pl in v['cities']:
                    if pl.id == us.place.id:
                        v['cities'].remove(pl)
                        v['cities'].insert(0, pl)
            countries[k]['cities'] = list(chunks(v['cities'], int(math.ceil(len(v['cities'])/4.0))))
        else:
            to_del.append(k)

    # удалим пустые страны
    for k in to_del:
        del countries[k]

    # make the user's country first
    if place and countries.get(place.country_code):
        first_one = countries[place.country_code]
        del countries[place.country_code]
    countries_list = list(countries.values())
    countries_list.sort(key=lambda item: item.get("name"))
    if first_one:
        countries_list.insert(0, first_one)

    us.city = place
    if us.city:
        us.city.transport_count = 0
    ctx = {'us': us, 'place_default': place, 'countries_list': countries_list}
    ctx['select'] = True
    return arender(request, "turbo_select.html", ctx)


def get_busamounts(bus_ids):
    rpipe = REDIS.pipeline()
    total_uids = []
    for bid in bus_ids:
        rpipe.smembers(f"bus__{bid}")
    for uids in rpipe.execute():
        total_uids += [x.decode('utf8') for x in uids]
    to_get = [f'event_{uid}' for uid in total_uids]
    amounts = defaultdict(list)
    for ev in rcache_mget(to_get):
        if ev and ev.busstop_nearest and not ev.zombie and not ev.away and not ev.sleeping:
            amounts["%s_d%s" % (ev.bus_id, ev.direction)].append(ev.uniqueid)
    busamounts = {}
    for k,v in amounts.items():
        busamounts[k] = len(v)
    return busamounts


def place_n_buses(city_name, force=False):
    cc_key = f'turbo_home__{city_name}'
    data = rcache_get(cc_key)
    if not data or force:
        p = get_object_or_404(Place, slug=city_name)
        buses = buses_get(p, force=force)
        rcache_set(cc_key, [p, buses])
    else:
        p, buses = data
    return p, buses


def turbo_home(request, city_name=None, template_name='turbo_index.html'):
    if request.GET.get('s') == "pwa":
        metric("pwa")   # s=pwa from manifest for android/ios

    p, buses = place_n_buses(city_name)

    if not request.session.session_key:
        first_time = True
    else:
        first_time = False

    us = get_user_settings(request)

    if first_time:
        ads_show = False
    else:
        metric('visit_%s' % p.id)
        ads_show = detect_ads_show(request, us)

    busamounts = get_busamounts([b.id for b in buses])
    busfavor = busfav_get(us, p, limit=us.busfavor_amount)
    for b in busfavor:
        b.ba_a = busamounts.get("%s_d%s" % (b.id, 0), 0)
        b.ba_b = busamounts.get("%s_d%s" % (b.id, 1), 0)
        b.amount_int = b.ba_a + b.ba_b

    counters_by_type = {}
    for b in buses:
        b.ba_a = busamounts.get("%s_d%s" % (b.id, 0), 0)
        b.ba_b = busamounts.get("%s_d%s" % (b.id, 1), 0)
        b.amount_int = b.ba_a + b.ba_b
        if not counters_by_type.get(b.ttype):
            counters_by_type[b.ttype] = 0
        counters_by_type[b.ttype] += b.amount_int

    default_ttype = None
    for k,v in counters_by_type.items():
        if default_ttype == None or counters_by_type[default_ttype] < v:
            default_ttype = k

    us.place = p
    us.save()

    us.city = p
    us.city.default_ttype = default_ttype
    us.city.transport_count = len(counters_by_type)

    transaction = get_transaction(us)
    temp = avg_temp(p)

    gps_send_enough, gps_send_cnt, odometer = False, 0, None
    if us.gps_send:
        gevent = rcache_get("gevent_%s" % us.id, {})
        if gevent:
            history = gevent.get('history', [])
            gps_send_cnt = len(history)
            if gps_send_cnt >= 50:
                gps_send_enough = True
                if not transaction:
                    us.show_gosnum = True
                    ads_show = False
            odometer = gevent.get('odometer', 0)
            odometer = odometer/1000
    coins = 3
    driver_warning = False
    if us.gps_send and not us.gosnum:
        driver_warning = True
    try:
        dump_size = os.path.getsize(f'{settings.PROJECT_DIR}/bustime/static/other/db/v8/{p.id}-{p.dump_version}.json')
    except:
        dump_size = 1
    try:
        diff_size = os.path.getsize(f'{settings.PROJECT_DIR}/bustime/static/other/db/v8/{p.id}-{p.dump_version}-{p.patch_version}.json.patch')
    except:
        diff_size = 1

    #сообщение для всех городов
    try:
        message_for_all = Settings.objects.get(key='message_for_all').value
    except:
        message_for_all = None

    tcard_available = us.place.id in PLACE_TRANSPORT_CARD.keys()

    if us.tcard:
        tcard = tcard_get(us.tcard, PLACE_TRANSPORT_CARD.get(us.place.id))
    else:
        tcard = None

    # counters
    user_ip = get_client_ip(request)
    now = p.now
    cc_key = "counter_today_%s_%s" % (p.id, now.date())
    counter_today = rcache_get(cc_key, [])
    if user_ip and not user_ip in counter_today:
        counter_today.append(user_ip)
        rcache_set(cc_key, counter_today, 604800) # 60*60*24*7
        sio_pub("ru.bustime.counters__%s" % (p.id), {"counter_today": len(counter_today)})
    counter_today = len(counter_today)

    cc_key = "counter_today_%s_%s" % (p.id, (now - datetime.timedelta(days=1)).date())
    counter_yesterday = rcache_get(cc_key, 0)
    if type(counter_yesterday) == list:
        counter_yesterday = len(counter_yesterday)
        rcache_set(cc_key, counter_yesterday, 604800)   # 60*60*24*7

    cc_key = "counter_online_%s_web" % p.id
    counter_online_city_web = REDIS_IO.get(cc_key)
    if not counter_online_city_web:
        counter_online_city_web = 0
    else:
        counter_online_city_web = counter_online_city_web.decode('utf8')
    cc_key = "counter_online_%s_app" % p.id
    counter_online_city_app = REDIS_IO.get(cc_key)
    if not counter_online_city_app:
        counter_online_city_app = 0
    else:
        counter_online_city_app = counter_online_city_app.decode('utf8')

    device = mobile_detect(request)
    specialicons = specialicons_cget(place_id=p.id)
    gtfs_alerts = rcache_get("alerts_%s" % p.id, {}).values()

    ctx = {
        "place": p,
        "buses": buses,
        "main_page": True,
        "us": us,
        'device': device,
        'first_time': first_time,
        "currentPath": request.path.strip("/").split("/"),
        "currentGet": dict(request.GET),
        "ttypes": counters_by_type.keys(),
        "default_ttype": default_ttype,
        "counters_by_type": counters_by_type,
        "counter_today": counter_today,
        "counter_yesterday": counter_yesterday,
        "counter_online_city_web": counter_online_city_web,
        "counter_online_city_app": counter_online_city_app,
        "busfavor": busfavor,
        "transaction": transaction,
        "avg_temp": temp,
        "btc_price": get_btc(),
        "ads_show": ads_show,
        "dump_size": dump_size,
        "diff_size": diff_size,
        'ut_minutes': 0,
        "ut_minutes_left": 110,
        "gps_send_enough": gps_send_enough,
        "gps_send_cnt": gps_send_cnt,
        "coins": coins,
        "driver_warning": driver_warning,
        "odometer": odometer,
        "specialicons": specialicons,
        "message_for_all": message_for_all,
        "tcard_available": tcard_available,
        "tcard": tcard,
        'weather': weather_detect(p),
        'gtfs_alerts': gtfs_alerts,
    }
    if p.id < 1000: # used for data_provider, todo
        city=City.objects.get(id=p.id)
        us.city.block_info = city.block_info
        ctx['city'] = city

    return arender(request, template_name, ctx)
# turbo_home


def new_ui_home(request, city_name=None, template_name='new_ui_index.html'):
    if request.GET.get('s') == "pwa":
        metric("pwa")   # s=pwa from manifest for android/ios

    p, buses = place_n_buses(city_name)

    if not request.session.session_key:
        first_time = True
    else:
        first_time = False

    us = get_user_settings(request)

    if first_time:
        ads_show = False
    else:
        metric('visit_%s' % p.id)
        ads_show = detect_ads_show(request, us)

    busamounts = rcache_get("busamounts_%s" % p.id, {})

    busfavor = busfav_get(us, p, limit=us.busfavor_amount)
    for b in busfavor:
        b.ba_a = busamounts.get("%s_d%s" % (b.id, 0), 0)
        b.ba_b = busamounts.get("%s_d%s" % (b.id, 1), 0)
        b.amount_int = b.ba_a + b.ba_b

    counters_by_type = {}
    for b in buses:
        b.ba_a = busamounts.get("%s_d%s" % (b.id, 0), 0)
        b.ba_b = busamounts.get("%s_d%s" % (b.id, 1), 0)
        b.amount_int = b.ba_a + b.ba_b
        if not counters_by_type.get(b.ttype):
            counters_by_type[b.ttype] = 0
        counters_by_type[b.ttype] += b.amount_int
            
    default_ttype = None
    for k,v in counters_by_type.items():
        if default_ttype == None or counters_by_type[default_ttype] < v:
            default_ttype = k
        
    us.place = p
    us.save()
    # todo
    us.city = p
    us.city.default_ttype = default_ttype
    us.city.transport_count = len(counters_by_type)
    
    transaction = get_transaction(us)
    temp = avg_temp(p)

    gps_send_enough, gps_send_cnt, odometer = False, 0, None
    if us.gps_send:
        gevent = rcache_get("gevent_%s" % us.id, {})
        if gevent:
            history = gevent.get('history', [])
            gps_send_cnt = len(history)
            if gps_send_cnt >= 50:
                gps_send_enough = True
                if not transaction:
                    us.show_gosnum = True
                    ads_show = False
            odometer = gevent.get('odometer', 0)
            odometer = odometer/1000
    coins = 3
    driver_warning = False
    if us.gps_send and not us.gosnum:
        driver_warning = True
    try:
        dump_size = os.path.getsize(f'{settings.PROJECT_DIR}/bustime/static/other/db/v8/{p.id}-{p.dump_version}.json')
    except:
        dump_size = 1
    try:
        diff_size = os.path.getsize(f'{settings.PROJECT_DIR}/bustime/static/other/db/v8/{p.id}_ver_{p.patch_version}.json.patch')
    except:
        diff_size = 1

    #сообщение для всех городов
    try:
        message_for_all = Settings.objects.get(key='message_for_all').value
    except:
        message_for_all = None

    tcard_available = us.place.id in PLACE_TRANSPORT_CARD.keys()

    if us.tcard:
        tcard = tcard_get(us.tcard, PLACE_TRANSPORT_CARD.get(us.place.id))
    else:
        tcard = None

    # counters
    user_ip = get_client_ip(request)
    now = p.now
    cc_key = "counter_today_%s_%s" % (p.id, now.date())
    counter_today = rcache_get(cc_key, [])
    if user_ip and not user_ip in counter_today:
        counter_today.append(user_ip)
        rcache_set(cc_key, counter_today, 604800) # 60*60*24*7
        sio_pub("ru.bustime.counters__%s" % (p.id), {"counter_today": len(counter_today)})
    counter_today = len(counter_today)

    cc_key = "counter_today_%s_%s" % (p.id, (now - datetime.timedelta(days=1)).date())
    counter_yesterday = rcache_get(cc_key, 0)
    if type(counter_yesterday) == list:
        counter_yesterday = len(counter_yesterday)
        rcache_set(cc_key, counter_yesterday, 604800)   # 60*60*24*7

    cc_key = "counter_online_%s_web" % p.id
    counter_online_city_web = REDIS_IO.get(cc_key)
    if not counter_online_city_web:
        counter_online_city_web = 0
    else:
        counter_online_city_web = counter_online_city_web.decode('utf8')
    cc_key = "counter_online_%s_app" % p.id
    counter_online_city_app = REDIS_IO.get(cc_key)
    if not counter_online_city_app:
        counter_online_city_app = 0
    else:
        counter_online_city_app = counter_online_city_app.decode('utf8')

    device = mobile_detect(request)

    ctx = {
        "place": p,
        "buses": buses,
        "main_page": True,
        "us": us,
        'device': device,
        'first_time': first_time,
        "currentPath": request.path.strip("/").split("/"),
        "currentGet": dict(request.GET),
        "ttypes": counters_by_type.keys(),
        "default_ttype": default_ttype,
        "counters_by_type": counters_by_type,
        "counter_today": counter_today,
        "counter_yesterday": counter_yesterday,
        "counter_online_city_web": counter_online_city_web,
        "counter_online_city_app": counter_online_city_app,
        "busfavor": busfavor,
        "transaction": transaction,
        "avg_temp": temp,
        "btc_price": get_btc(),
        "ads_show": ads_show,
        "dump_size": dump_size,
        "diff_size": diff_size,
        'ut_minutes': 0,
        "ut_minutes_left": 110,
        "gps_send_enough": gps_send_enough,
        "gps_send_cnt": gps_send_cnt,
        "coins": coins,
        "driver_warning": driver_warning,
        "odometer": odometer,
        "message_for_all": message_for_all,
        "tcard_available": tcard_available,
        "tcard": tcard
    }
    if p.id < 1000: # used for data_provider, todo
        city=City.objects.get(id=p.id)
        us.city.block_info = City.objects.get(id=p.id).block_info
        weather = weather_detect(CITY_MAP[p.id])
        ctx['city'] = city
    else:
        weather = None
    ctx['weather'] = weather

    return arender(request, template_name, ctx)
# new_ui_home


def home(request, template_name='index.html', force_city=None, city_name=None, PERFMON=False):
    if PERFMON:
        PERFMON_START = datetime.datetime.now()
    user_ip = get_client_ip(request)
    c = request.GET.get('c')  # city selector shortcut by id
    if c:
        try:
            city = CITY_MAP.get(int(c))
        except:
            city = None
        if city:
            return HttpResponsePermanentRedirect(u"/%s/" % city.slug)
        else:
            raise Http404
    s = request.GET.get('s')  # s=pwa from manifest for android/ios
    if s and s == "pwa":
        metric("pwa")

    if not request.session.session_key:
        first_time = True
    else:
        first_time = False
    city = None
    if city_name:
        try:
            if request.user.is_staff:
                city = City.objects.get(slug=city_name)
            else:
                city = City.objects.get(slug=city_name, available=True)
        except:
            return HttpResponseRedirect("/")
        force_city = city.id

    sat = request.GET.get('sat')
    us = get_user_settings(request, force_city=force_city)
    transaction = get_transaction(us)

    # welcome
    if request.user.is_staff and us.id != 1:
        if us.country:
            cities = City.objects.filter(country=us.country)
        else:
            cities = City.objects.filter()

    # поменять город если не доступен
    cc_key = "available_cities_ids"
    cities_ids = rcache_get(cc_key)
    if not cities_ids:
        cities_ids = City.objects.filter(available=True).values_list("id", flat=True)
        rcache_set(cc_key, cities_ids, 60*15)

    if not us.city_id:
        return HttpResponseRedirect(f"/")

    if us.city_id not in cities_ids:
        if request.user.is_staff:
            us.city = city if city else City.objects.get(id=us.city_id)
        else:
            us.city = city_autodetect(us.ip, us.country)
        us.save()
    else:
        us.city = City.objects.get(id=us.city_id)  # to prevent version caching

    if not force_city:
        return HttpResponseRedirect(f"/{us.city.slug}/")
    now = us.city.now

    # counters
    cc_key = "counter_today_%s_%s" % (us.city_id, now.date())
    counter_today = rcache_get(cc_key, [])
    if user_ip and not user_ip in counter_today:
        counter_today.append(user_ip)
        rcache_set(cc_key, counter_today, 604800) # 60*60*24*7
        sio_pub("ru.bustime.counters__%s" % (us.city_id),
                {"counter_today": len(counter_today)})
    counter_today = len(counter_today)

    cc_key = "counter_today_%s_%s" % (
        us.city_id, (now - datetime.timedelta(days=1)).date())
    counter_yesterday = rcache_get(cc_key, 0)
    if type(counter_yesterday) == list:
        counter_yesterday = len(counter_yesterday)
        rcache_set(cc_key, counter_yesterday, 604800)   # 60*60*24*7

    cc_key = "counter_online_%s_web" % us.city_id
    counter_online_city_web = REDIS_IO.get(cc_key)
    if not counter_online_city_web:
        counter_online_city_web = 0
    else:
        counter_online_city_web = counter_online_city_web.decode('utf8')
    cc_key = "counter_online_%s_app" % us.city_id
    counter_online_city_app = REDIS_IO.get(cc_key)
    if not counter_online_city_app:
        counter_online_city_app = 0
    else:
        counter_online_city_app = counter_online_city_app.decode('utf8')

    counters_by_type = rcache_get("counters_by_type__%s" % us.city.id, {})

    if not first_time:
        metric('visit_%s' % us.city.id)

    device = mobile_detect(request)
    if first_time:
        ads_show = False
    else:
        ads_show = detect_ads_show(request, us)

    busamounts = rcache_get("busamounts_%s" % us.city_id, {})
    busfavor = busfav_get(us, us.city, limit=us.busfavor_amount)
    for b in busfavor:
        b.ba_a = busamounts.get("%s_d%s" % (b.id, 0), 0)
        b.ba_b = busamounts.get("%s_d%s" % (b.id, 1), 0)
    if us.tcard:
        city = CITY_MAP[us.city_id]
        tcard = tcard_get(us.tcard, city)
    else:
        tcard = None

    if PERFMON:
        PERFMON_M = datetime.datetime.now()
    specialicons = specialicons_cget(city_id=us.city_id)
    buses = buses_get(us.city, as_dict=True, force=True)    # 26.09.23: убрать force=True после 03.10.23 (кэши уже обновятся)
    for b in buses:
        b["ba_a"] = busamounts.get("%s_d%s" % (b["id"], 0), 0)
        b["ba_b"] = busamounts.get("%s_d%s" % (b["id"], 1), 0)
        b["amount_int"] = b["ba_a"]+b["ba_b"]
    main_page = True
    temp = avg_temp(us.city)
    weather = weather_detect(us.city)
    error_update = rcache_get("error_%s" % us.city_id, {})
    if template_name == "demo_show.html":
        ads_show = False

    # don't save often to save CPU and decrease response time
    if not us.ltime or (now-us.ltime).days > 0:
        us.ltime = now
        us.save()

    gps_send_enough, gps_send_cnt, odometer = False, 0, None
    if us.gps_send:
        gevent = rcache_get("gevent_%s" % us.id, {})
        if gevent:
            history = gevent.get('history', [])
            gps_send_cnt = len(history)
            if gps_send_cnt >= 50:
                gps_send_enough = True
                if not transaction:
                    us.show_gosnum = True
                    ads_show = False
            odometer = gevent.get('odometer', 0)
            odometer = odometer/1000
    coins = 3
    driver_warning = False
    if us.gps_send and not us.gosnum:
        driver_warning = True

    cc_key = "citynews__%s" % us.city_id
    cn = rcache_get(cc_key)
    if cn == None:
        cn = CityNews.objects.filter(place_id=us.city.id, etime__gt=now, news_type=1).order_by("-ctime")[:1]
        if not cn:
            rcache_set(cc_key, False)
        else:
            rcache_set(cc_key, cn)
    if cn:
        try:
            watched = REDIS.sismember(f"citynews_{cn.id}_watched", us.id)
        except:
            watched = None
        cn = None if watched else cn

    avg_jam_ratio = rcache_get('avg_jam_ratio__%s' % us.city.id) or 0

    #сообщение для всех городов
    try:
        message_for_all = Settings.objects.get(key='message_for_all').value
    except:
        message_for_all = None

    ctx = {
        "real_error": us.city.real_error(),
        "buses": buses,
        'busfavor': busfavor,
        'us': us,
        "eden": EDEN,
        'tcard': tcard, 'ads_show': ads_show,
        'device': device,
        'first_time': first_time,
        'error_update': error_update,
        'transaction': transaction,
        'now': now,
        'ut_minutes': 0,
        "ut_minutes_left": 110,
        'specialicons': specialicons,
        "special_theme": special_theme_selector(now),
        "main_page": main_page,
        "force_city": force_city,
        "counter_today": counter_today,
        "counter_yesterday": counter_yesterday,
        "counter_online_city_web": counter_online_city_web,
        "counter_online_city_app": counter_online_city_app,
        "counters_by_type": counters_by_type,
        "template_name": template_name,
        "gps_send_enough": gps_send_enough,
        "gps_send_cnt": gps_send_cnt,
        "coins": coins,
        "ban": us.is_banned() and lotime(us.ban),
        "driver_warning": driver_warning,
        "odometer": odometer,
        'avg_temp': avg_temp,
        "weather": weather,
        "btc_price": get_btc(),
        "holiday": detect_holiday(us.city),
        "sat": sat,
        "cn": cn,
        "avg_jam_ratio": avg_jam_ratio,
        "hostname": settings.MASTER_HOSTNAME,
        "message_for_all": message_for_all,
        "currentPath": request.path.strip("/").split("/"),
        "currentGet": dict(request.GET),
        #"pa": PlaceArea.objects.filter(name=us.city.name).order_by("-admin_level").first()  # TODO: use rcache
    }

    if request.user.is_staff and us.id != 1:
        ctx["cities"] = cities
    if transaction and transaction.vip:
        ctx["not_found"] = Log.objects.filter(
            city=us.city, ttype="get_bus_by_name").count()

    # taxi, восстановление состояния
    # из кук восстанавливать так:
    # json.loads( urllib.parse.unquote( request.COOKIES.get('taxi_user', "{}") ) )
    try:
        taxiuser = json.loads( urllib.parse.unquote( request.COOKIES.get('taxi_user', "{}") ) )
    except Exception as ex:
        taxiuser = taxiuser_get(request.user.id)

    if not taxiuser or taxiuser['user'] != request.user.id: # последнее условие - следствие использования браузера разными людьми
        taxiuser = taxiuser_get(request.user.id)

    ctx['taxiuser'] = taxiuser
    request.session['taxiuser'] = json.dumps(ctx['taxiuser'], default=str)

    ctx["tevents"] = rcache_get("tevents_%s" % us.city.id, {})
    if taxiuser and taxiuser.get('user'):
        taxi_path = rcache_get("taxi_path_%s" % request.user.id, {})
        ctx["taxi_path"] = json.dumps(taxi_path, default=str)
        ctx["stop_from"] = taxi_path.get('wf', {}).get('address', '')
        ctx["stop_to"] = taxi_path.get('wh', {}).get('address', '')
        ctx["trips"] = rcache_get("trips_%s" % request.user.id, [])

        if taxiuser.get('gps_on'):
            # таксист работает или пассажир голосует
            ctx["torders"] = rcache_get("torders_%s" % us.city.id, {})

            if taxiuser.get('driver') and taxiuser.get('car_count') > 0:
                # таксист
                return HttpResponseRedirect("/carpool/votes/")    # на страницу голосующих пассажиров
            else:
                # пассажир, восстановить заказ и показать страницу с заказом
                if taxiuser.get('order_id'):
                    orders = rcache_get('torders_%s' % us.city.id, {})
                    if orders:
                        ctx["order"] = orders.get(taxiuser.get('order_id'), {})
                    ctx["offers"] = rcache_get('offers_%s' % taxiuser.get('order_id'), {})
                    if ctx["offers"]:
                        ctx["tab_active"] = "taxi_trip"    # голосует
        # taxiuser.get('gps_on')
    # if taxiuser

    if PERFMON:
        PERFMON_STOP = datetime.datetime.now()
        d1 = (PERFMON_M - PERFMON_START).total_seconds()
        d2 = (PERFMON_STOP - PERFMON_M).total_seconds()
        d3 = (PERFMON_STOP - PERFMON_START).total_seconds()
        f = open('/tmp/views.py__home_%s' % us.city_id, 'a')
        f.write('%s %s [%s+%s]\n' % (d3, us.id, d1, d2))
        f.close()
    return arender(request, template_name, ctx)
# home


def ajax_busfavor(request):
    try:
        bus_id = request.GET.get('bus_id')
        bus_id = int(bus_id)
    except:
        return HttpResponse("")
    us = get_user_settings(request)
    if us.busfav_hold:
        return HttpResponse("")

    bus = bus_get(bus_id)
    if not bus:
        return HttpResponse("")

    f = Favorites.objects.filter(us=us, bus=bus)
    if f:
        f = f[0]
        f.counter += 1
        f.save()
    else:
        # check if bus still exists
        try:
            f, cr = Favorites.objects.get_or_create(us=us, bus=bus, counter=1)
        except:
            return HttpResponse("")

    return HttpResponse(f.counter)


def ajax_busdefavor(request):
    try:
        bus_id = request.GET.get('bus_id')
        bus_id = int(bus_id)
        bus = bus_get(bus_id)
    except:
        return HttpResponse("")

    us = get_user_settings(request)
    if us.busfav_hold:
        return HttpResponse("")

    f = Favorites.objects.filter(us=us, bus=bus).delete()
    if us.place:
        busfav_get(us, us.place, force=True)

    return HttpResponse("")


def ajax_detector(request):
    bus_id = request.GET.get('bus_id')
    bus_id = int(bus_id)
    bus = bus_get(bus_id)
    p1_lon = float(request.GET.get('p1_lon'))
    p1_lat = float(request.GET.get('p1_lat'))
    p2_lon = float(request.GET.get('p2_lon'))
    p2_lat = float(request.GET.get('p2_lat'))
    from bustime.detector import ng_detector
    DD = get_detector_data(bus.city)
    r = ng_detector(bus, p1_lon, p1_lat, p2_lon,
                    p2_lat, nearest_prev=None, DD=DD)
    return HttpResponse(str(r))


def ajax_mapping(request):
    us = get_user_settings(request)
    city_id = request.GET.get("city_id")
    if city_id:
        city_id = int(city_id)
        place = Place.objects.get(id=city_id)
    # добавить запись
    add = request.GET.get("add")
    if add:
        try:
            m = Mapping.objects.create(
                place=place, xeno_id=add, gosnum="нет_номера")
            sio_pub("ru.bustime.city_mapping_table_%s" % (city_id), {
                    "cmd": "add", "id": m.id, "fields": {"xeno_id": add, "gosnum": "нет_номера", "bus_id": ""}})
            return HttpResponse(m.id)
        except Exception as e:
            return HttpResponse(json.dumps(str(e)))
    # очистить все маршруты
    clear = request.GET.get("clear")
    if clear:
        Mapping.objects.filter(place=place).update(bus=None)
        sio_pub("ru.bustime.city_mapping_table_%s" %
                (city_id), {"cmd": "clear", "id": 0})
        return HttpResponse("")
    # изменить значение записи
    mapping_id = request.GET.get('mapping_id')
    if mapping_id == None:
        return HttpResponse("")

    mapping_id = int(mapping_id)
    try:
        m = Mapping.objects.get(id=mapping_id)
    except Mapping.DoesNotExist as e:
        raise Http404("Mapping does not exist")

    # эти параметры со страницы city_mapping_table
    cmd = request.GET.get('cmd', False)
    if not cmd:
        # эти параметры со страницы city_mapping
        bus_id = request.GET.get('bus_id')
        gosnum = request.GET.get('gosnum')
        delete = request.GET.get('delete')
    else:
        bus_id = gosnum = xeno_id = delete = False
        if cmd == 'bus_id':
            bus_id = request.GET.get('val')
        elif cmd == 'gosnum':
            gosnum = request.GET.get('val')
        elif cmd == 'xeno_id':
            xeno_id = request.GET.get('val')
        elif cmd == 'delete':
            delete = True

    try:
        if bus_id:
            m.bus = bus_get(int(bus_id))
            m.last_changed_by = us
            m.save()
            sio_pub("ru.bustime.city_mapping_table_%s" % (city_id), {
                    "cmd": "edit", "id": mapping_id, "field": cmd, "value": bus_id})
        if gosnum or cmd == 'gosnum':
            gosnum = gosnum.upper().replace(" ", "")
            m.gosnum = gosnum
            m.last_changed_by = us
            m.save()
            sio_pub("ru.bustime.city_mapping_table_%s" % (city_id), {
                    "cmd": "edit", "id": mapping_id, "field": cmd, "value": gosnum})
        if xeno_id:
            m.xeno_id = xeno_id.replace(" ", "")
            m.last_changed_by = us
            m.save()
            sio_pub("ru.bustime.city_mapping_table_%s" % (city_id), {
                    "cmd": "edit", "id": mapping_id, "field": cmd, "value": xeno_id})
        if delete:
            m.delete()
            sio_pub("ru.bustime.city_mapping_table_%s" %
                    (city_id), {"cmd": "delete", "id": mapping_id})

        mapping_get(place, force=True)
    except Exception as e:
        return HttpResponse(json.dumps(str(e)))

    return HttpResponse("")


def ajax_route_line(request):
    def cshort(t):
        return (round(t[0], 5), round(t[1], 5))
    try:
        bus_id = request.GET.get('bus_id')
        bus_id = int(bus_id)
        bus = bus_get(bus_id)
    except:
        return HttpResponse("")

    lines = RouteLine.objects.filter(bus=bus, line__isnull=False)
    res = {}
    for l in lines:
        l.line = l.line.simplify(tolerance=0.000002, preserve_topology=True)
        res[l.direction] = list(map(cshort, l.line.coords))

    return HttpResponse(json.dumps(res))


@csrf_exempt
def ajax_route_lines_calc(request):
    responce = {"result": 0}
    try:
        bus_id = request.POST.get('bus_id')
        bus_id = int(bus_id)
        if bus_id > 0:
            bus = bus_get(bus_id)
            if fill_routeline(bus, force = True):
                responce["result"] = 1
        else:
            city_id = request.POST.get('city_id')
            city_id = int(city_id)
            buses = Bus.objects.filter(places__id=city_id, active=True)
            for b in buses:
                responce["result"] += 1 if fill_routeline(b, force=True) else 0
    except Exception as ex:
        responce["error"] = str(ex)

    return HttpResponse(json.dumps(responce))


def place_routelines_cals(city_id, force=False):
    buses = Bus.objects.filter(places__id=city_id, active=True)
    for b in buses:
        fill_routeline(b, force)


def ajax_timer(request):
    us = get_user_settings(request)
    now = us.city.now
    cc_key = "%s_%s" % (us.id, now.date())
    if us.pro_demo:
        cc_key += "_pro"

    mins = REDIS_W.incr(cc_key)
    if mins == 1:
        REDIS_W.expire(cc_key, 60*60*24)
    if mins == 10 and us.pro_demo:
        metric('timer_warning')

    if us.pro_demo:
        serialized = {"pro_minutes": mins}
    else:
        serialized = {'minutes': mins}

    serialized = ujson.dumps(serialized)
    return HttpResponse(serialized)


@csrf_exempt
def ajax_gvote(request):
    us = get_user_settings(request)
    positive = request.GET.get('positive')
    if positive == "1":
        positive = True
    else:
        positive = False
    gvotes = gvote_set(us, positive)
    return HttpResponse(ujson.dumps(gvotes))


@csrf_exempt
def ajax_plan_change(request):
    us = get_user_settings(request)
    transaction = get_transaction(us)
    if not transaction:
        return HttpResponse(_(u"нет прав доступа"))

    city_id = request.POST.get('city_id')
    plan_id = request.POST.get('plan_id')
    gra = request.POST.get('gra')
    gnum = request.POST.get('gnum')

    city = get_object_or_404(City, id=int(city_id))
    plan = Plan.objects.get(id=plan_id)
    gra = int(gra)
    plan.gra = gra
    if gnum:
        plan.xeno_id = gnum
    else:
        plan.xeno_id = None
    plan.save()

    return HttpResponse("")


@csrf_exempt
def ajax_gvote_comment(request):
    us = get_user_settings(request)
    now = datetime.datetime.now()
    try:
        gv = GVote.objects.get(user=us)
    except:
        return HttpResponse("0")
    cmnt = request.POST.get('comment', "")[:1024]
    gv.comment = cmnt
    gv.comment_time = now
    gv.save()
    log_message(cmnt, ttype="gvote.comment", user=us)
    return HttpResponse("1")


@csrf_exempt
def ajax_peer_get(request):
    us_id = request.POST.get("us_id")
    peer_id = REDIS.get("us_%s_peer" % us_id)
    if peer_id:
        peer_id = peer_id.decode('utf8')

    serialized = {
        'us_id': us_id,
        'peer_id': peer_id,
    }

    return HttpResponse(ujson.dumps(serialized))


@csrf_exempt
def ajax_busstop_resolver(request):
    ids = request.POST.get('ids')
    busstops = []
    for nb in NBusStop.objects.filter(id__in=ids):
        busstops.append({'id': nb.id, 'name': nb.name, 'moveto':
                         nb.moveto, 'lon': nb.point.x, 'lat': nb.point.y})

    serialized = {
        'busstops': busstops,
    }

    return HttpResponse(ujson.dumps(serialized))


def bdata_mode2_f(events, raw=False):
    tosend = events
    if raw:
        return tosend
    else:
        return ujson.dumps(tosend)


def ajax_bus(request):
    bus_id = request.GET.get('bus_id', '0')
    try:
        bus = bus_get(int(bus_id))
    except:
        return HttpResponse("")
    serialized = bus_last_f(bus)    # in models.py
    return HttpResponse(serialized)


@csrf_exempt
def ajax_bus_monitor(request):
    bus_id = request.POST.get('bus_id', '0')
    try:
        bus = bus_get(int(bus_id))
    except:
        return HttpResponse("")
    if not bus:
        return HttpResponse("")
    req_key = request.POST.get('req_key', None)

    events = []
    allevents = rcache_get("allevents_%s" % bus.city_id, {})
    for k, v in allevents.items():
        if v.bus == bus:
            if req_key and k != req_key:
                continue
            z = v.as_json_friendly()
            z['k'] = k
            events.append(z)

    serialized = ujson.dumps(events)
    return HttpResponse(serialized)


@csrf_exempt
def ajax_anomalies(request):
    city_id = request.POST.get('city_id', '3')
    city = City.objects.get(id=int(city_id))

    events = []
    allevents = rcache_get("anomalies__%s" % city.id)
    if not allevents:
        allevents = []
    for v in allevents:
        events.append(v.as_json_friendly())
    serialized = ujson.dumps(events)
    return HttpResponse(serialized)


# deprecated
def classic_bus(request, bus_id, old_url=None, city_name=None):
    us = get_user_settings(request)
    if bus_id:
        try:
            bus_id = int(bus_id)
            bus = get_object_or_404(Bus, id=bus_id)
        except:
            bus = get_object_or_404(Bus, slug=bus_id, city__slug=city_name)
    if old_url:
        return HttpResponsePermanentRedirect("/%s/classic/%s/" % (bus.city.slug, bus.slug))

    return HttpResponsePermanentRedirect(bus.get_absolute_url_schedule())

    ctx = {"city": bus.city, "classic": True}
    route0 = Route.objects.filter(bus=bus, direction=0).order_by(
        'order').select_related('busstop')
    route1 = Route.objects.filter(bus=bus, direction=1).order_by(
        'order').select_related('busstop')
    time_bst = rcache_get("time_bst_%s" % bus.city_id, {})
    ctx['time_bst'] = time_bst.get(bus.id, {})
    ctx['bus'] = bus
    ctx['bdata_mode0'] = bus.bdata_mode0()
    ctx['route0'] = route0
    ctx['route1'] = route1
    ctx["eden"] = EDEN
    ctx["us"] = us
    ctx["device"] = mobile_detect(request)

    return arender(request, "bus-classic.html", ctx)


def ajax_tcard(request, num):
    if len(num) < 10:
        return HttpResponse("неправ. формат!")
    if len(num) > 18:
        return HttpResponse("неправ. формат!")

    us = get_user_settings(request)
    city = us.city
    tcards = Tcard.objects.filter(num=num, provider=city.tcard_provider)
    if not tcards:
        tcard = Tcard.objects.create(
            num=num, updated=datetime.datetime(2014, 0o2, 11), provider=city.tcard_provider)
    else:
        tcard = tcards[0]
    if not city.tcard_provider:
        return HttpResponse("Данные не предоставляются")
    tcard_update(tcard, city.tcard_provider)
    if tcard.black:
        return HttpResponse("несущ. номер")
    else:
        us.tcard = num
        us.save()
        return HttpResponse(tcard.balance)


def ajax_card(request, num):
    if len(num) < 10:
        return HttpResponse("неправ. формат!")
    if len(num) > 18:
        return HttpResponse("неправ. формат!")

    us = get_user_settings(request)
    place = us.place
    place_id = request.GET.get('place_id')

    if not place_id:
        place = us.place
    else:
        place = Place.objects.get(id=place_id)

    if not place.id in PLACE_TRANSPORT_CARD:
        return HttpResponse("Данные не предоставляются")

    tcards = Tcard.objects.filter(num=num, provider=PLACE_TRANSPORT_CARD[place.id])
    if not tcards:
        tcard = Tcard.objects.create(
            num=num, updated=datetime.datetime(2014, 0o2, 11), provider=PLACE_TRANSPORT_CARD[place.id])
    else:
        tcard = tcards[0]
    tcard_update(tcard, PLACE_TRANSPORT_CARD[place.id])
    if tcard.black:
        return HttpResponse("несущ. номер")
    else:
        us.tcard = num
        us.save()
        if tcard.social:
            s = 1
        else:
            s = 0
        result = ujson.dumps({"balance": tcard.balance, "social": s})
        return HttpResponse(result)


def ajax_bootstrap_amounts(request):
    busamounts = rcache_get("busamounts")
    serialized = ujson.dumps({"busamounts": busamounts})
    return HttpResponse(serialized)


def ajax_metric(request, metric_=None):
    if not metric_:
        metric_ = request.GET.get('metric')
    if metric_ == "wsocket_off":
        value = request.GET.get('value')
    metric(metric_)
    return HttpResponse("")


def ajax_settings(request):
    setting = request.GET.get('setting')
    value = request.GET.get('value')
    us = get_user_settings(request)
    rtrn = ""

    if setting == "gps_send_of":
        us.gps_send_of = value
        settings__gps_send_of(us)
    elif setting == "matrix_show":
        if value == "true":
            us.matrix_show = True
        else:
            us.matrix_show = False
    elif setting == "map_show":
        if value == "true":
            us.map_show = True
        else:
            us.map_show = False

    elif setting == "name":
        value = value[:80].strip()
        if not value:
            value = "¯\_(ツ)_/¯"
        setattr(us, setting, value)
        rtrn = value

    us.save()
    return HttpResponse(rtrn)
# def ajax_settings


def ajax_settings1(request):
    http_response = HttpResponse(1)
    us = get_user_settings(request)

    name_check = ["sound", "sound_plusone", "voice", "gps_off", "speed_show", "multi_all", "font_big",
                  "busfav_hold", "gps_send", "gps_send_ramp", "si_active", "show_gosnum", "p2p_video", "edit_mode",
                  "gps_send_rampp", "expert", "driver_taxi", "driver_bus"]

    checked = request.GET.get("checked")
    name = request.GET.get("name")
    if name in name_check:
        if name == "si_active":
            SpecialIcon.objects.filter(us=us).update(
                active=checked.capitalize())
        else:
            setattr(us, name, checked.capitalize())

    aname_check_bool = ["live_indicator", "plusone", "bigsticker"]
    if name in aname_check_bool:
        if checked == "false":
            us.attrs[name] = False
        else:
            us.attrs[name] = True

    name = request.GET.get("name")
    value = request.GET.get("value")

    if name == "name":
        if us.user:
            us.user.first_name = value
            if us.user.first_name:
                if is_mat(value):
                    value_name = 'xxx'
            us.user.save()

    if name == "gosnum":
        us.gosnum = value
        if us.gosnum:
            us.gosnum = us.gosnum.replace(" ", "").strip().upper()[:12]
            if is_mat(us.gosnum):
                us.gosnum = 'xxx'
        else:
            us.gosnum = None

    if name == "gps_send_of":
        us.gps_send_of = value
        if us.gps_send_of:
            us.gps_send_of = us.gps_send_of[:12]
        settings__gps_send_of(us)

    if name == "busfavor_amount":
        busfavor_amount = value
        busfavor_amount = int(busfavor_amount)
        if busfavor_amount in [0, 5, 10, 20, 30]:
            us.busfavor_amount = busfavor_amount

    if name == "gps_send_bus":
        bus = value
        if bus:
            us.gps_send_bus = bus_get(int(bus))
            bus = us.gps_send_bus
            us.tface = None
            if us.gosnum:
                vhs = Vehicle1.objects.filter(
                    gosnum=us.gosnum, bus=us.gps_send_bus).update(driver_ava=us.driver_ava)
        else:
            us.gps_send_bus = None

    if name == "select_radio":
        us.radio = value

    if name == "select_dark_theme":
        us.attrs["dark_theme"] = value

    if name == "reset":
        us.tcolor = value

    if name == "select_country":
        if value and COUNTRY_MAP_CODE.get(value):
            country = COUNTRY_MAP_CODE[value]
            if us.country != country:
                us.country = country
                us.city = None

    if name == "select_language":
        if value and check_for_language(value):
            path = request.GET.get("path", '/')
            url = reverse('index', subdomain=value, scheme='https')[:-1] + path
            data = json.dumps({"returnUrl": url})
            http_response = HttpResponse(data)
            # http_response = HttpResponseRedirect(
            #     reverse('index', subdomain=value, scheme='https'))
                # request.META.get('HTTP_REFERER', '/'))
                
            if hasattr(request, 'session'):
                request.session[LANGUAGE_SESSION_KEY] = value
            # else:
            #     http_response.set_cookie(settings.LANGUAGE_COOKIE_NAME, value)
            http_response.set_cookie(
                settings.LANGUAGE_COOKIE_NAME,
                value,
                domain=settings.LANGUAGE_COOKIE_DOMAIN,
            )

        # translation_activate(value)
        us.language = value

    if us.user:
        from taxi.models import TaxiUser, taxiuser_update
        taxiuser = TaxiUser.objects.filter(user=request.user).first()
        if name == "taxi_agreement" and checked in ['True', 'true']:
            if not taxiuser:
                taxiuser, created = TaxiUser.objects.get_or_create(user=us.user)
                taxiuser.name = request.GET.get("taxi_user_name", us.user.first_name)
                taxiuser.agreement = datetime.datetime.now()
                taxiuser.driver = us.driver_taxi
                taxiuser.save(update_fields=['agreement', 'name', 'driver'])
                taxiuser_update(request, http_response)

        if taxiuser:
            if name == "taxi_user_name":
                taxiuser.name = value
                taxiuser.save(update_fields=['name'])
                taxiuser_update(request, http_response)
            elif name == "taxi_user_phone":
                taxiuser.phone = value
                taxiuser.save(update_fields=['phone'])
                taxiuser_update(request, http_response)
            elif name == "taxi_user_gender":
                taxiuser.gender = value
                taxiuser.save(update_fields=['gender'])
                taxiuser_update(request, http_response)


    us.tface = request.GET.get("value_tface",  us.tface)
    us.tcolor = request.GET.get("value_tcolor", us.tcolor)
    bus = us.gps_send_bus
    if bus:
        tface = bus.ttype_slug()
    if us.gps_send_bus and us.tface:
        tface = us.tface

    if bus:
        fin = "%s/bustime/static/img/theme/modern/%s.svg" % (
            settings.PROJECT_DIR, tface)
        fout = "%s/bustime/static/img/theme/modern/%s_%s.png" % (
            settings.PROJECT_DIR, tface, us.tcolor)

        if not os.path.isfile(fout):
            with open(fin, "r") as sources:
                lines = sources.readlines()
            tmpsvg = "/tmp/%s_%s.svg" % (tface, us.tcolor)
            with open(tmpsvg, "w") as sources:
                for line in lines:
                    sources.write(re.sub(r'#f4c110', '#'+us.tcolor, line))
            # запись файла локально
            subprocess.call(["inkscape", "-o", fout,
                             '-w', '76', '-h', '76', tmpsvg])
            try:
                # создаём локальный симлинк на файл в каталоге STATIC_ROOT
                static_fout = "%s/static/img/theme/modern/%s_%s.png" % (
                    settings.PROJECT_DIR, tface, us.tcolor)
                os.symlink(fout, static_fout)
            except:
                pass
        # if not os.path.isfile(fout)
    # if bus
    us.save()

    if request.FILES.get("photo"):
        r = handle_uploaded_file(request, us)
        if r != False:
            sis = SpecialIcon.objects.filter(us=us)
            if sis:
                sis = sis[0]
            else:
                sis = SpecialIcon.objects.create(us=us, place_id=us.place_id)
            if us.gosnum != "":
                sis.gosnum = us.gosnum
            else:
                sis.gosnum = "xxx"
            sis.img = "/static/img/si/%s" % r
            SpecialIcon.objects.filter(
                gosnum=sis.gosnum, place_id=us.place_id).update(active=False)
            sis.save()
            specialicons_cget(place_id=us.place_id, force=True)
            return HttpResponse(sis.img)
        else:
            ctx = {"message": _(u"Ошибка, неправильный формат изображения")}
            return arender(request, "message.html", ctx)

    return http_response
# def ajax_settings1


def gosnum_set_py(place, uniqueid, gosnum, ms=None, us=None):
    if ms:
        user = ms
        vdict = {"ms": ms}
    else:
        user = us
        vdict = {"us": us}
    if user.user:
        groups = get_groups(user.user)
    else:
        groups = []
    uniqueid = six.text_type(uniqueid)
    now = place.now
    if place.id == 37:
        repl = {
            'error': u"Ошибка: редактирование номеров запрещено, причина: нецензурные слова"}
        return repl


    if not user or not user.user:
        repl = {
            'error': u"Ошибка: редактирование номеров запрещено, причина: Пользователь не авторизован"}
        return repl

    ban = user.is_banned()
    # trans = get_transaction(us)
    if ban:
        repl = {
            'error': u"Ошибка: редактирование номеров запрещено до %s, причина: нецензурные слова" % lotime(user.ban)}
        return repl

    modify_allowed = is_gosnum_modify_allowed(place, user)
    if not modify_allowed:
        repl = {
            'error': u"Ошибка: Только редакторы и администраторы могут изменять связанную с городом информацию"
        }
        return repl

    gosnum = six.text_type(gosnum.replace(" ", "").upper().strip()[:12])
    if gosnum == "":
        repl = {'error': u"Ошибка: номер пустой"}
        return repl
    elif len(gosnum) < 3:
        repl = {'error': u"Ошибка: номер слишком короткий"}
        return repl
    elif len(gosnum) > 6 and 'editor' not in groups:
        repl = {'error': u"Ошибка: номер слишком длинный, введите в формате А123БВ"}
        return repl
    elif not re.match(u"[А-Я0-9]+$", force_str(gosnum)):
        repl = {'error': u"Ошибка: номер содержит недопустимые символы"}
        return repl
    elif is_mat(gosnum):
        repl = {'error': u"Ошибка: нецензурные слова"}
        return repl

    gosnum = gosnum[:12]

    ev = rcache_get(f"event_{uniqueid}")
    if ev and ev.custom:
        repl = {'error': u"Ошибка: номер защищён"}
        return repl

    dupe_check = Vehicle.objects.filter(gosnum=gosnum) #, city=city)

    if dupe_check:
        if 'editor' not in groups:
            return {'error': u"Этот номер уже используется"}

    counter = 0

    record = Vehicle.objects.filter(uniqueid=uniqueid, gosnum_allow_edit=True)
    record = record[0] if record else None
    if not record:
        repl = {'error': u"Редактирование запрещено"}
        return repl

    usr = user.user if user and user.user else None
    comment = ""
    if record:  # get or update
        record.gosnum = gosnum
    else:
        bus = bus_get(ev.bus) if type(ev.bus) is int else ev.bus
        record = Vehicle(
            uniqueid=uniqueid,
            gosnum=gosnum,
            gosnum_allow_edit=True,
            bortnum_allow_edit=True,
            # city=city,
            created_auto=False,
            channel='gosnum_set_py',
            src='views.py',
            ttype=bus.ttype
        )

    with reversion.create_revision():
        record.save(usr)
        if user and user.user:
            reversion.set_user(usr)

    e = rcache_get(f"event_{uniqueid}")
    if e:
        e['gosnum'] = gosnum
        rcache_set(f"event_{uniqueid}", e)
        bus = bus_get(e.bus_id)
        bm0 = bus.bdata_mode()
        for v in bm0.get('l', []):
            if v['u'] == uniqueid:
                v['g'] = gosnum
                serialized = {"bdata_mode10": bm0}
                # serialized["bdata_mode0"]['updated'] = six.text_type(now).split(" ")[
                #     1]
                serialized["bdata_mode10"]['bus_id'] = bus.id
                chan = "ru.bustime.bus_mode10__%s" % bus.id
                REDIS_W.publish(f"turbo_{e.bus_id}", pickle_dumps({"cmd": "reload_vehicles"}))
                print(chan, serialized)
                sio_pub(chan, serialized)

    gift = 0
    repl = {'result': {'counter': counter, 'gift': gift}}
    return repl


def ajax_gosnum(request):
    us = get_user_settings(request)
    uniqueid = request.GET.get('uniqueid')
    gosnum = request.GET.get('gosnum')
    city_id = request.GET.get('city_id')
    if not city_id:
        place = us.place
    else:
        place = places_get(lang=cur_lang)[int(city_id)]
    f = open('/tmp/gosnum_set','a')
    f.write('json_gosnum %s %s %s\n' % (city_id, uniqueid, gosnum))
    f.close()
    gresult = gosnum_set_py(place, uniqueid, gosnum, us=us)

    return HttpResponse(ujson.dumps(gresult))


def ajax_stop_id_set_map_center(request):
    us = get_user_settings(request)
    stop_id = request.GET.get("stop_id")
    x = request.GET.get("x")
    y = request.GET.get("y")
    z = request.GET.get("z")
    s = "%s,%s,%s" % (x, y, z)
    # request.session['stop_id_set_map_center'] = s
    request.session['stop_%s_set_map_center' % stop_id] = s
    return HttpResponse(s)


def get_nstop_nearest_timing_bdata_mode3(stop_id, move_to, tram_only, bdata_mode3, timestamp):
    preds = bdata_mode3.get(stop_id, [])
    preds = sorted(preds, key=lambda p: p.get('t'))
    nbdata = []
    for pred in preds:
        pq = copy.copy(pred)
        pq['t'] = u"%02d:%02d" % (pred['t'].hour, pred['t'].minute)
        pq['tt'] = int(time.mktime(pred['t'].timetuple()))
        pq['t2'] = (u"%02d:%02d" % (pred['t2'].hour,
                                    pred['t2'].minute)) if pred.get('t2') else None
        pq['t2t'] = int(time.mktime(pred['t2'].timetuple())
                        ) if pred.get('t2') else None
        nbdata.append(pq)
    result = {
        "nbid": stop_id,
        "tram_only": 0 if not tram_only else 1,
        "data": nbdata,
        "nbname": move_to,
        "updated": timestamp
    }
    return result


def get_nbusstop_nearest_timing_bdata_mode3(nstops, bdata_mode3, timestamp):
    return [get_nstop_nearest_timing_bdata_mode3(nb.id,
                                                 nb.moveto,
                                                 nb.tram_only,
                                                 bdata_mode3,
                                                 timestamp) for nb in nstops]


def ajax_stop_id_f(ids, raw=False, data=None, single=False, mobile=False):
    serialized = {"stops": []}
    if single:
        nstops = ids
        bdata_mode3 = {nstops[0].id: data}
    else:
        pipe = REDIS_W.pipeline()
        rpipe = REDIS.pipeline()
        cc_key = "nbusstop_ids_%s" % str(ids).replace(' ', '')
        all_stops = rcache_get(cc_key, None)
        if all_stops is None:
            all_stops = {s['id']: s for s in NBusStop.objects.filter(id__in=ids).values("id", "moveto", "tram_only", "timezone")}
            rcache_set(cc_key, all_stops)

        cc_key = "bus_names_ids_%s" % str(ids).replace(' ', '')
        all_buses_names = rcache_get(cc_key, None)
        if all_buses_names is None:
            all_buses_names = {r["bus"]: r["bus__name"] for r in Route.objects.filter(busstop_id__in=ids).values("bus", "bus__name")}
            rcache_set(cc_key, all_buses_names)

        for sid in all_stops.keys():
            rpipe.hgetall(f"timetable__{sid}")

        timetables = list(zip(all_stops.keys(), rpipe.execute()))
        all_uids = [f"event_{entry['uid']}" for _, timetable in timetables for v in timetable.values() if (entry := pickle.loads(v))]
        events = {}
        for e in rcache_mget(all_uids):
            if e: events[e.uniqueid] = e


        for sid, items in timetables:
            stop_id = int(sid)
            stop_info = all_stops[stop_id]
            now = datetime.datetime.now(stop_info['timezone']).replace(tzinfo=None)
            move_to = stop_info['moveto']
            tram_only = stop_info['tram_only']
            mode3values = []
            for k, v in items.items():
                bid = int(k)
                entry = pickle.loads(v)
                event = events.get(entry['uid'])
                if event:
                    bdata_mode0_l = event.get_lava()
                    entry['uid'] = event['uniqueid']
                    entry['l'] = bdata_mode0_l
                    # Lazy Cleanup. If Predicted time Less than Current time Delete it.
                    if (entry.get('t', datetime.datetime.min) < now and 
                        entry.get('t2', datetime.datetime.min) < now):
                            pipe.hdel(f"timetable__{sid}", bid)
                    else:
                        mode3values.append(entry)
            serialized['stops'].append(get_nstop_nearest_timing_bdata_mode3(
                stop_id, move_to, tram_only, 
                {stop_id: mode3values}, datetime_seconds_round_up(now).strftime('%H:%M:%S')))
        pipe.execute()
        if raw:
            return serialized
        else:
            return ujson.dumps(serialized)


def ajax_stop_ids(request):
    ids = request.GET.get('ids', "[]")
    try:
        ids = ujson.loads(ids)
    except:
        return HttpResponse("")

    serialized = ajax_stop_id_f(ids)
    return HttpResponse(serialized)


@csrf_exempt
def ajax_route_edit_save(request):
    us = get_user_settings(request)
    transaction = get_transaction(us)
    place_id = int(request.POST.get('place_id', "0"))
    bus_id = request.POST.get('bus_id', "0")
    route = request.POST.get('route', "[]")
    bus = bus_get(int(bus_id))
    userlog = request.POST.get('userlog', "[]")
    retval = {"error":"", "result":""}

    try:
        route = ujson.loads(route)
        userlog = ujson.loads(userlog)

        if place_id:
            place = Place.objects.filter(id=place_id).first()
        else:
            place = None

        version = bus_route_version(
            bus, user=us.user if us.user else request.user, userlog=userlog, place_id=place_id)

        if place:
            bus.mtime = place.now
            if not bus.places.filter(id=place_id).first():
                bus.places.add(place)

        qs = Route.objects.filter(bus=bus).delete()

        bulk_routes = []
        for direction, stops in route.items():
            d = int(direction)
            for i in range(len(stops)):
                bulk_routes.append( Route(bus=bus, busstop_id=stops[i], direction=d, order=i) )
        Route.objects.bulk_create(bulk_routes)

        if not bus.turbo:
            bus.turbo = True

        with reversion.create_revision():
            bus.save(refresh_routes=True)
            comment = ""
            for l in userlog:
                note = l.get('note')
                if note.startswith('Добавление остановки'):
                    comment += 'В %s маршрут (направление %s) добавлена остановка %s\n' % (bus.name, l.get('direction'), l.get('name'))
                elif note.startswith('Удаление остановки'):
                    comment += 'Из маршрута %s (направление %s) удалена остановка %s\n' % (bus.name, l.get('direction'), l.get('name'))
            if len(comment) > 0:
                reversion.set_comment(comment)
            if us.user:
                reversion.set_user(us.user)

        bus_route_version(
            bus, user=us.user if us.user else request.user, version=version, place_id=place_id)

        fill_inter_stops_for_bus(bus)

        fill_bus_endpoints(bus)  # , DEBUG=True

        fill_moveto(bus)

        fill_routeline(bus, True)

        update_bus_places('bus', bus.id, turbo=False, DEBUG=False) # in bustime.osm_utils.py

        cache_reset_bus(bus)

        cc_key = f"turbo_{bus.id}"
        REDIS_W.publish(cc_key, pickle_dumps({"cmd": "reload"}))

        if place:
            fill_jamline_list(place.id, [bus.id])

        retval["result"] = 1
    except Exception as ex:
        retval["result"] = 0
        retval["error"] = str(ex)
        #retval["error"] = traceback.format_exc(limit=3)

    return HttpResponse(ujson.dumps(retval))
# ajax_route_edit_save


# Версионирование Route
def bus_route_version(bus, user=None, version=None, userlog=None, delete=False, place_id=None):
    if not bus:
        return

    if place_id:
        place = Place.objects.get(id=place_id)
        # все остановки place
        buses_ids = [b.id for b in buses_get(place, True)]  # маршруты города
        stops_ids = list(Route.objects.filter(bus_id__in=buses_ids).distinct('busstop_id').values_list('busstop_id', flat=True))
    else:
        place = None
        # все остановки маршрута
        stops_ids = list(Route.objects.filter(bus_id=bus.id).distinct('busstop_id').values_list('busstop_id', flat=True))

    stops = NBusStop.objects.filter(id__in=stops_ids).order_by('id')

    try:
        # новая запись об изменении маршрута
        if version:
            busversion = BusVersion.objects.get(id=version)
        else:
            busversion = BusVersion.objects.create(
                bus=bus, place=place, user=user, ctime=datetime.datetime.now())

        # сохраняем состояние маршрута
        update_fields = []
        tmp_str = serializers.serialize("json", stops)
        tmp_json = json.loads(tmp_str)
        tmp_list = []
        for obj in tmp_json:
            record = obj["fields"]
            record["pk"] = obj["pk"]
            tmp_list.append(record)
        tmp_json = json.dumps(tmp_list)

        if not version:  # перед изменением маршрута
            busversion.stops_before = tmp_json
            update_fields.append('stops_before')
        else:   # после изменения маршрута
            busversion.stops_after = tmp_json
            update_fields.append('stops_after')

        routes = Route.objects.filter(bus=bus).order_by('direction', 'order')
        tmp_str = serializers.serialize("json", routes)
        tmp_json = json.loads(tmp_str)
        tmp_list = []
        for obj in tmp_json:
            record = obj["fields"]
            record["pk"] = obj["pk"]
            tmp_list.append(record)
        tmp_json = json.dumps(tmp_list)

        if not version:  # перед изменением маршрута
            busversion.routes_before = tmp_json
            update_fields.append('routes_before')
        else:   # после изменения маршрута
            busversion.routes_after = tmp_json
            update_fields.append('routes_after')

        if len(update_fields):
            busversion.save(update_fields=update_fields)

        # пишем лог действий пользователя во время изменения
        news = []   # новости
        if userlog:
            bulk = []
            tm = datetime.datetime.now()

            for l in userlog:
                note = l.get('note')
                bulk.append(
                    BusVersionLog(busversion=busversion, bus=bus, place=place, user=user, ctime=tm,
                                  note=note, nbusstop_id=l.get('nbusstop_id'), direction=l.get('direction'),
                                  order=l.get('order'), name=l.get('name'))
                )

                if note.startswith('Добавление остановки'):
                    news.append({
                        'body': 'В %s маршрут (направление %s) добавлена остановка %s' % (bus.name, l.get('direction'), l.get('name')),
                        'news_link': '/%s/bus-%s/edit/' % (place.slug, bus.slug)
                    })
                elif note.startswith('Удаление остановки'):
                    news.append({
                        'body': 'Из маршрута %s (направление %s) удалена остановка %s' % (bus.name, l.get('direction'), l.get('name')),
                        'news_link': '/%s/bus-%s/edit/' % (place.slug, bus.slug)
                    })
            # for l in userlog

            BusVersionLog.objects.bulk_create(bulk)

            if news:
                for n in news:
                    CityNews.objects.create(title='Автоновость', place=place, news_type=2,
                                            body=n['body'], news_link=n['news_link'], author=user)
        # if userlog

        if delete:
            note = "Удаление маршрута '%s' (%s)" % (bus.name, bus.id)
            BusVersionLog.objects.create(busversion=busversion, bus=bus, place=place, user=user,
                                         ctime=datetime.datetime.now(), note=note)

            CityNews.objects.create(title='Автоновость', place=place, news_type=2,
                                    body='Удалён маршрут %s (%s)' % (
                                        bus.name, TTYPE_CHOICES[bus.ttype][1]),
                                    news_link='/wiki/bustime/busversion/%s/change/' % busversion.id,
                                    author=user)

        version = busversion.id
    except Exception as err:
        version = None
        log_message(str(err), ttype="bus_route_version", place=place)

    return version
# def bus_route_version


'''
Восстановление маршрута из таблицы версий BusVersion
на 06.05.20 нет восстановления удалённого маршрута, только изменённого
хотя, кажется, ни что не мешает восстановить и удалённый маршрут
'''


@csrf_exempt
def bus_route_revert(request, bus_id=0, version_id=0):

    logs = []
    # получаем версию из которой будем восстанавливать
    # в полях stops_before и routes_before хранятся остановки и routes (связи остановок) до момента изменения маршрута
    bv = BusVersion.objects.get(id=version_id)
    bus = bv.bus

    if bv.place:
        place = bv.place
    else:
        place = Place.objects.get(id=bv.city.id)
        bv.place = place
        bv.save()

    logs.append('Восстановление маршрута %s (%s), версия %s от %s' % (
        bus.name, place.name, version_id, bv.ctime.strftime("%d.%m.%y %H:%M:%S")))

    # восстанавливаем остановки города
    logs.append('Сканирование остановок')
    stops = json.loads(bv.stops_before)
    for s in stops:
        try:
            nbs = NBusStop.objects.get(id=s["pk"])
        except:
            nbs = NBusStop(
                id=s["pk"],
                ttype=s["ttype"],
                name=s["name"],
                name_alt=s["name_alt"],
                point=s["point"],
                moveto=s["moveto"],
                xeno_id=s["xeno_id"],
                osm_id=s["osm_id"],
                tram_only=s["tram_only"],
                slug=s["slug"],
            )
            nbs.save()
            logs.append('Восстановлена остановка %s "%s"' % (nbs.id, nbs.name))
    # for s in stops

    # восстанавливаем routes (связи остановок) города
    logs.append('Сканирование связей остановок')
    routes = json.loads(bv.routes_before)
    if len(routes):
        Route.objects.filter(bus=bus).delete()
        for r in routes:
            nb = NBusStop.objects.get(id=r["busstop"])
            ro = Route(
                id=r["pk"],
                bus=bus,
                busstop=nb,
                endpoint=r["endpoint"],
                direction=r["direction"],
                order=r["order"]
            )
            ro.save()
        # for r in routes

        logs.append('Рассчет конечных')
        fill_bus_endpoints(bus)  # , DEBUG=True

        logs.append('Рассчет связей остановок')
        fill_moveto(bus)

        logs.append('Рассчет линии маршрута')
        fill_routeline(bus, True)

        logs.append('Отметка о времени изменения маршрута')
        bus.mtime = place.now
        bus.save()

        logs.append('Сброс кэша маршрута')
        cache_reset_bus(bus)
    # if len(routes)

    logs.append('Восстановление маршрута закончено')
    logs.append('<hr>')
    logs.append(
        '<a href="/wiki/bustime/busversion/">Вернуться к списку версий маршрутов</a>')
    logs.append('<a href="/wiki/bustime/busversion/%s/change/">Вернуться на страницу версии %s маршрута %s</a>' %
                (version_id, version_id, bus.name))
    logs.append('<a href="/%s/%s/edit/">Перейти на страницу редактирования маршрута %s</a>' %
                (place.slug, bus.slug, bus.name))
    logs.append('<a href="/%s/#%s">Перейти на страницу маршрута %s</a>' %
                (place.slug, bus.slug, bus.name))

    html = '<br>'.join(logs)

    return HttpResponse(html)
# def bus_route_revert


@csrf_exempt
def ajax_stops_by_gps(request, metric_=None):
    us = get_user_settings(request)
    lat = request.POST.get('lat', "56.0029")
    lon = request.POST.get('lon', "92.93163")
    bus_name = request.POST.get('bus_name', "")
    bus_id = request.POST.get('bus_id')
    accuracy = request.POST.get('accuracy', "100000")
    try:
        accuracy = float(accuracy)
    except:
        accuracy = 1000 * 1000
    if accuracy > 1000:
        return HttpResponse(ujson.dumps([]))
    now = datetime.datetime.now()

    psess = (u"%s%s" % (us.id, eday_password())).encode()
    psess = b64encode(hashlib.sha256(psess).digest(), b"-_").decode()[:8]

    lon, lat = float(lon), float(lat)
    pnt = Point(lon, lat)

    nstops = NBusStop.objects.filter(
        point__distance_lte=(pnt, 600)).distinct('name')
    l = []
    pnt_x, pnt_y = pnt.x, pnt.y
    for q in nstops:
        dis = distance_meters(pnt_x, pnt_y, q.point.x, q.point.y)
        dis = dis / 10 * 10  # pretty number better
        ids = NBusStop.objects.filter(
            name=q.name).values_list('id', flat=True)

        ids = list(ids)
        l.append({"d": dis, "name": q.name, "ids": ids})
    l = sorted(l, key=lambda k: k['d'])
    l = l[:10]
    current_nbusstop = None
    current_nbusstop_dis = 1000
    if l:
        for candi in NBusStop.objects.filter(id__in=l[0]['ids']):
            dis = distance_meters(pnt_x, pnt_y, candi.point.x, candi.point.y)
            if not current_nbusstop or dis < current_nbusstop_dis:
                current_nbusstop = candi
                current_nbusstop_dis = dis
        l[0]['current_nbusstop'] = current_nbusstop.id
    serialized = ujson.dumps(l)
    
    ht = str(now_at(lon, lat)).split('.')[0].split(' ')[1]
    data = [ht, psess, lon, lat, accuracy, bus_name]
    pdata = {
        "time": ht,
        "sess": psess,
        "lon": lon,
        "lat": lat,
        "accuracy": accuracy,
        "bus_name": bus_name,
        "nb_id": "",
        "nb_name": "",
        "os": "web"}
    if current_nbusstop:
        data.append(current_nbusstop.id)
        data.append(current_nbusstop.name)
        pdata["nb_id"] = current_nbusstop.id
        pdata["nb_name"] = current_nbusstop.name
    else:
        data.append(0)
        data.append("")
    data.append("web")
    nb_id = pdata["nb_id"]
    if not nb_id:
        nb_id = None

    if us.place:
        PassengerStat.objects.using('bstore').create(psess=psess, city=us.place.id, lon=lon,
                                                 lat=lat, bus_name=bus_name[:7], nb_name=pdata["nb_name"][:32], nb_id=nb_id, os=0)

    data = {"city_monitor": data, "passenger_monitor": pdata}
    if us.place:
        sio_pub("ru.bustime.city_monitor__%s" % (us.place_id), data)
    if bus_id:
        sio_pub("ru.bustime.bus_mode0__%s" % (bus_id), data)

    # taxi
    if us.user_id:
        order = request.POST.get('taxi_order')
        timestamp = request.POST.get('timestamp')
        tdata = {
            "user_id": us.user_id,
            "lon": lon,
            "lat": lat,
            "timestamp": int(timestamp) if timestamp else None,
            "taxi_order": int(order) if order else None,
        }
        sio_pub("ru.bustime.taxi__%s" % us.place_id, {"taxi": {"event": "passenger", "data": json.dumps(tdata, default=str)} })
        rcache_set('passenger_%s' % us.user_id, tdata, 3600)

    return HttpResponse(serialized)


def reset_busfavor(request):
    us = get_user_settings(request)
    Favorites.objects.filter(us=us, bus__places=us.place).delete()
    if us and us.place:
        busfav_get(us, us.place, force=True)
    return HttpResponseRedirect("/")


def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i:i + n]


def help_view(request):
    us = get_user_settings(request)
    ctx = {'us': us}
    return arender(request, "help.html", ctx)


def services(request):
    us = get_user_settings(request)
    ctx = {'us': us}
    return arender(request, "services.html", ctx)


def select(request):
    us = get_user_settings(request)
    countries = {}
    cities = cities_get()
    for c in Country.objects.filter(available=True).exclude(id=15):
        countries[c.code] = c.__dict__
        countries[c.code]['name'] = c.name
        countries[c.code]['cities'] = []

    l = []
    for city_id, city in cities.items():
        l.append('log_counters_%s' % city_id)
        l.append("error_%s" % city_id)
    log_counters = rcache_mget(l)

    for city_id, city in cities.items():
        z = city.country.code
        c = city.__dict__
        c['name'] = city.name
        lc = log_counters.pop(0)
        if not lc: lc = {}
        c['nearest'] = lc.get('nearest', 0)
        c['error_update'] = log_counters.pop(0)
        # don't add if not avail, log_counters must be poped before!
        if not city.available:
            continue
        c['avg_temp'] = get_avg_temp(city)
        c['now'] = lotime(city.now.time)
        c['country_code'] = z
        if countries.get(z):
            countries[z]["cities"].append(c)
    # make it columno
    first_one = None
    for k,v in countries.items():
        countries[k]['cities'] = chunks(v['cities'], int(math.ceil(len(v['cities'])/4.0)))
    # make the user's country first
    countries_list = list(countries.values())
    countries_list.sort(key=lambda item: item.get("name"))
    if first_one:
        countries_list.insert(0, first_one)

    ctx = {'us': us, 'countries_list': countries_list}
    return arender(request, "select.html", ctx)


def ci_st():
    csdata = {}
    qs = DataSourceStatus.objects.all().order_by('datasource_id', '-ctime').distinct('datasource_id')
    qs = qs.values_list('datasource', 'delay_avg')
    for i in qs:
        csdata[i[0]] = i[1]


def select_admin(request):
    us = get_user_settings(request)
    transaction = get_transaction(us)
    if not request.user.is_staff or not transaction or not transaction.key:
        return HttpResponse(_(u"нет прав доступа"))

    midnight = datetime.datetime.combine(
        datetime.datetime.today(), datetime.time.min)
    yesterday_midnight = midnight - datetime.timedelta(days=1)
    now = midnight
    from_date = yesterday_midnight
    yday = datetime.datetime.now() - datetime.timedelta(days=1)
    cities = list(Place.objects.filter(id__in=places_filtered()))

    query_web = Q()
    query_app = Q()
    query_visits = Q()
    query_inst = Q()
    for city in cities:
        query_web |= Q(name="dau_web_%s" % city.id)
        query_app |= Q(name="dau_app_%s" % city.id)
        query_visits |= Q(name="visit_%s" % city.id)
        query_inst |= Q(place=city)
    query_web &= Q(date=from_date)
    query_app &= Q(date=from_date)
    query_visits &= Q(date=from_date)
    query_inst &= Q(ctime__gte=from_date) & Q(ctime__lt=now)

    dau_web_qs = Metric.objects.filter(query_web).values_list("name", "count")
    dau_web_qs = dict(dau_web_qs)
    dau_app_qs = Metric.objects.filter(query_app).values_list("name", "count")
    dau_app_qs = dict(dau_app_qs)
    visits_qs = Metric.objects.filter(query_visits)
    mob_qs = MobileSettings.objects.filter(
        query_inst).values_list("place_id", flat=True)
    mob_qs = list(mob_qs)

    ci = []
    for city in cities:
        now = city.now

        cc_key = "counter_today_%s_%s" % (
            city.id, (now - datetime.timedelta(days=1)).date())
        counter_yesterday = rcache_get(cc_key, 0)
        if type(counter_yesterday) == list:
            counter_yesterday = len(counter_yesterday)

        cc_key = "counter_today_%s_%s" % (
            city.id, (now - datetime.timedelta(days=2)).date())
        counter_yyday = rcache_get(cc_key, 0)
        if type(counter_yyday) == list:
            counter_yyday = len(counter_yyday)

        c = city.__dict__
        c['counter_yesterday'] = dau_web_qs.get("dau_web_%s" % city.id, 0)
        c['counter_yyday'] = counter_yyday
        log_counters = rcache_get('log_counters_%s' % c['id'], {})
        c['nearest'] = log_counters.get('nearest', 0)
        c['away'] = log_counters.get('away', 0)
        c['allevents_len'] = log_counters.get('allevents_len', 0)
        c['device_connected'] = REDIS.get("counter_online__%s" % c['id'])
        if not c['device_connected']:
            c['device_connected'] = 0
        else:
            c['device_connected'] = c['device_connected'].decode('utf8')
        c['counters_by_type'] = rcache_get(
            "counters_by_type__%s" % c['id'], {})
        c['avg_temp'] = avg_temp(city)
        c['weather'] = weather_detect(city)
        c['error_update'] = rcache_get("error_%s" % c['id'], {})
        c['avg_jam_ratio'] = rcache_get('avg_jam_ratio__%s' % city.id) or 0


        c['mob'] = dau_app_qs.get("dau_app_%s" % city.id, 0)
        xia = (now - datetime.timedelta(days=1)).date()
        xib = now.date()
        c['mob_installs'] = mob_qs.count(city.id)

        c['now'] = lotime(now.time)
        if c['nearest']:
            c['love_web'] = math.trunc(c['counter_yesterday']*10 / c['nearest'])
            c['love_app'] = math.trunc(c['mob']*10 / c['nearest'])
        else:
            c['love_web'] = '-'
            c['love_app'] = '-'
        delay_avg = rcache_get('delay_avg_%s' % city.id)
        if delay_avg is None:
            c['delay_avg'] = delay_avg
        else:
            c['delay_avg'] = math.trunc(delay_avg)

        c['real_error'] = False #city.real_error()
        ci.append(c)

    cities = sorted(ci, key=lambda x: x['nearest'], reverse=True)
    mob_active = MobileSettings.objects.filter(ltime__gte=yday).count()
    ctx = {'us': us, 'cities': cities,
           'mob_active': mob_active, 'transaction': transaction}
    return arender(request, "select-admin.html", ctx)


def buy(request):
    return HttpResponsePermanentRedirect("/")


def contacts(request):
    return HttpResponsePermanentRedirect("/")


def about(request):
    us = get_user_settings(request)
    ctx = {'us': us}
    return arender(request, "about.html", ctx)


def noadblock(request):
    us = get_user_settings(request)
    ctx = {}
    return arender(request, "noadblock.html", ctx)


def icon_editor(request, place_name):
    us = get_user_settings(request)
    now = datetime.datetime.now()
    trans = get_transaction(us)
    place = get_object_or_404(Place, slug=place_name)

    access = False
    if trans and trans.vip:
        access = True
    if not access:
        return HttpResponse("нет прав")

    icons = SpecialIcon.objects.filter(place_id=place).order_by("id")
    if request.POST:
        for i in icons:
            active = request.POST.get("%s_active" % i.id, "off")
            gosnum = request.POST.get("%s_gosnum" % i.id)
            if active == "on":
                active = True
            else:
                active = False
            if i.active != active:
                i.active = active
                i.save()
            if gosnum != i.gosnum and gosnum != "":
                i.gosnum = gosnum
                i.save()
    ctx = {'us': us, "icons": icons, "place": place}
    return arender(request, "icon_editor.html", ctx)


def pro(request):
    return HttpResponseRedirect("/")
    now = datetime.datetime.now()
    us = get_user_settings(request)
    transaction = get_transaction(us)
    if request.POST:
        phone = request.POST.get("phone")
        phone = "+7"+phone.replace(" ", '').replace("-", '')
        if len(phone) != len("+71111111111"):
            ctx = {"message": _(
                u"Ошибка, неправильный формат номера телефона!")}
            return arender(request, "message.html", ctx)
        us.phone = phone
        us.save()
        st = request.POST.get("st")
        if st == "s100":
            amount = 100
            key = "standard"
        elif st == "p500":
            amount = 500
            key = "premium"
        log_message("create bill: %s, %s" % (phone, st),
                    ttype="qiwi", user=us, city=us.city)
        pay = Payment.objects.create(
            us=us, amount=amount, key=key, value=amount)
#        r = qiwi.create_bill(phone, amount, account="us=%s" %
#                             us.id, bill_id=pay.id)
        if r != 0:
            log_message("create bill error: %s" %
                        (r), ttype="qiwi", user=us, city=us.city)

        # redirect
        from six.moves.urllib.parse import urlencode
        params = {
            "shop": str(settings.QIWI_PROJECT_ID),
            "transaction": pay.id,
            "successUrl": "/",
            "failUrl": "/"
        }
        return HttpResponseRedirect("https://qiwi.com/order/external/main.action?%s" % urlencode(params))


    ctx = {'us': us, "transaction": transaction}
    return arender(request, "pro.html", ctx)


def rating(request, city_name, for_date=None, old_url=None, page=None):
    us = get_user_settings(request)
    now = datetime.datetime.now()
    if old_url:
        city = get_object_or_404(City, name__iexact=city_name)
    else:
        city = get_object_or_404(City, slug=city_name)
    if not for_date:
        for_date = now.date()
    else:
        for_date = for_date.split('-')
        for_date = list(map(int, for_date))
        for_date = datetime.date(for_date[0], for_date[1], 1)
    if for_date.year < 2016:
        raise Http404("No data for this year")
    for_year = for_date.year
    return HttpResponsePermanentRedirect(u"/%s/top/%s/" % (city.slug, for_year))

def top(request, city_name, for_year=None, page=None):
    us = get_user_settings(request)
    now = datetime.datetime.now()
    place = get_object_or_404(Place, slug=city_name)
    if not for_year:
        for_year = now.year
    else:
        for_year = int(for_year)
    if for_year < 2016 or for_year > now.year:
        raise Http404("No data for this year")

    votes = Vote.objects.filter(vehicle__bus__places__id=place.id, ctime__year=for_year)
    votes = votes.values_list(
        'vehicle', 'ctime', 'positive', 'comment', 'name', 'stars')
    vh = {}

    for vehicle, ctime, positive, comment, name, stars in votes:
        if not vh.get(vehicle):
            vh[vehicle] = {'messages': [], 'votes': 0, 'place': 0,
                           'positive': 0, 'gosnum_img': None, 'vegavotes': []}
        micromsg = {'ctime': ctime, 'comment': comment,
                    'name': name, 'positive': positive, 'stars': stars}
        if stars:
            micromsg['stars_as_list'] = list(range(0, stars))
        vh[vehicle]['messages'].append(micromsg)
        vh[vehicle]['vegavotes'].append((positive, stars))
        vh[vehicle]['votes'] += 1

    vehicles_map, vehicles = {}, []
    for v in Vehicle1.objects.filter(id__in=list(vh.keys())).select_related():
        vehicles_map[v.id] = v
    for veh_id, dat in vh.items():
        dat['bus'] = vehicles_map[veh_id].bus
        dat['gosnum'] = vehicles_map[veh_id].gosnum
        dat['driver_ava'] = vehicles_map[veh_id].driver_ava
        wr = float("%.3f" % star_wilson(dat['vegavotes']))
        wr = round(wr * 5, 3)
        dat['rating_wilson_human'] = float("%.1f" % wr)
        vehicles.append(dat)
    vehicles = sorted(vehicles, key=lambda p: p.get('rating_wilson_human'))
    vehicles.reverse()

    pl = 1
    specialicons = specialicons_cget(as_dict=True)

    online = {}
    allevents = rcache_get("allevents_%s" % place.id, {})
    for e in allevents.values():
        if e.gosnum:
            online[e.gosnum] = e.zombie, e.sleeping, e.last_point_update

    for v in vehicles:
        v['place'] = pl
        pl += 1
        if specialicons.get(v['gosnum']):
            v['gosnum_img'] = specialicons[v['gosnum']]
        v['status'] = online.get(v['gosnum'], 'offline')
        if v['status'] != 'offline':
            zombie, sleeping, last_point_update = v['status']
            if zombie:
                v['status'] = 'zombie'
            elif sleeping:
                v['status'] = 'sleeping'
            # take into account last_point_update?
            elif last_point_update and last_point_update > place.now - datetime.timedelta(seconds=90):
                v['status'] = 'online'

    paginator = Paginator(vehicles, 50)
    if not page:
        page = 1
    try:
        vehicles = paginator.page(page)
    except:
        raise Http404("Error")

    ctx = {'us': us, "vehicles": vehicles,
           'now': now, 'place': place,
           'for_year': for_year,
           'page': page
           }

    if for_year < now.year:
        ctx['next_year'] = for_year + 1
    if for_year > 2016:
        ctx['prev_year'] = for_year - 1

    return arender(request, "top.html", ctx)


def schedule(request, city_name, old_url=None, old_url_two=None):
    us = get_user_settings(request)
    if old_url:
        place = get_object_or_404(Place, name__iexact=city_name)
        return HttpResponsePermanentRedirect("/%s/schedule/" % (place.slug))
    place = get_object_or_404(Place, slug=city_name)
    if old_url_two:
        return HttpResponsePermanentRedirect("/%s/timetable/" % (place.slug))

    buses = buses_get(place)
    busamounts = rcache_get("busamounts_%s" % place.id, {})
    counters_by_type = defaultdict(int)
    for b in buses:
        b.ba_a = busamounts.get("%s_d%s" % (b.id, 0), 0)
        b.ba_b = busamounts.get("%s_d%s" % (b.id, 1), 0)
        b.ba_sum = b.ba_a + b.ba_b
        counters_by_type[b.ttype] += b.ba_sum
    for b in buses:
        b.gcnt = counters_by_type.get(b.ttype, 0)

    #upd = Log.objects.filter(ttype="schedule", place=place).order_by("-date")[:1]
    upd = []
    if upd:
        upd = upd[0]
    us.city = place
    ctx = {'us': us, "buses": buses,
           "counters_by_type": counters_by_type, 'upd': upd,
           "ads_show": detect_ads_show(request, us), 'place': place}
    return arender(request, "schedule.html", ctx)


def schedule_bus(request, city_name, bus_id, old_url=None, old_url_two=None):
    us = get_user_settings(request)
    placearea = None
    place = get_object_or_404(Place, slug=city_name)

    try:
        bus = Bus.objects.get(id=int(bus_id))
        return HttpResponsePermanentRedirect(bus.get_absolute_url_schedule())
    except:
        if 'tram-' in bus_id:
            bus_id = bus_id.replace("tram-", 'tramway-')
            bus = get_object_or_404(Bus, slug=bus_id, city__slug=city_name)
            return HttpResponsePermanentRedirect(bus.get_absolute_url_schedule())
        if old_url_two:
            try:
                bus = Bus.objects.get(slug=bus_id, city__slug=city_name)
                return HttpResponsePermanentRedirect(bus.get_absolute_url_schedule())
            except:
                return HttpResponseRedirect("/%s/schedule/" % (city_name))

        bus = Bus.objects.filter(slug=bus_id, places=place).first()
        if not bus:
            return HttpResponseRedirect("/%s/schedule/" % (city_name))
    # except

    if old_url:
        return HttpResponsePermanentRedirect("/%s/schedule/%s/" % (place.slug, bus_id))

    now = place.now
    weekday = weekday_dicto(now)
    str_weekday = str(weekday).replace(" ", "_")

    route0 = routes_get(bus.id, direction=0)
    route1 = routes_get(bus.id, direction=1)

    # расписание хранится в полях tt_start и tt_start_holiday модели Bus
    try:
        tt_times = json.loads((bus.tt_start_holiday if now.weekday() in [
                              5, 6] else bus.tt_start).replace('\\r', '').replace('\\n', '').strip())
    except:
        tt_times = None

    if route0:
        direction = 0
        cc_key = "times_%s_%s_%s" % (bus.id, direction, str_weekday)
        times = rcache_get(cc_key)
        if not times:
            sdirection = str(direction)  # просто для скорости
            if tt_times and tt_times.get(sdirection):
                # для полной совместимости со старым кодом, конвертируем list of strings в list of datetime.time
                times = [datetime.time(*time.strptime((x if int(x[:2]) < 24 else str(int(
                    x[:2])-24)+":"+x[3:]), "%H:%M")[3:5]) for x in tt_times[sdirection] if len(x) > 0]

            if times:
                rcache_set(cc_key, times)
        # if not times
        route0[0].times = times

    if route1:
        direction = 1
        cc_key = "times_%s_%s_%s" % (bus.id, direction, str_weekday)
        times = rcache_get(cc_key)
        if not times:
            sdirection = str(direction)
            if tt_times and tt_times.get(sdirection):
                times = [datetime.time(*time.strptime((x if int(x[:2]) < 24 else str(int(
                    x[:2])-24)+":"+x[3:]), "%H:%M")[3:5]) for x in tt_times[sdirection] if len(x) > 0]

            if times:
                rcache_set(cc_key, times)
        # if not times
        route1[0].times = times

    busstops = []
    for i in route0:
        busstops.append(i.busstop)
    for i in route1:
        busstops.append(i.busstop)

    time_bst = rcache_get("time_bst_%s" % place.id, {})
    time_bst = time_bst.get(bus.id, {})
    bdata_mode0 = bus.bdata_mode0()
    if bdata_mode0:
        bdata_mode0[0]['ramp_stops'] = []
        if not bdata_mode0.get(1):
            bdata_mode0[1] = {}
        bdata_mode0[1]['ramp_stops'] = []

        for l in bdata_mode0['l']:
            if l['r'] and l.get('d'):
                bdata_mode0[l['d']]['ramp_stops'].append(l['b'])
    us.city = place

    ctx = {
        'us': us,
        "bus": bus,
        "place": place,
        "now": now,
        "bdata_mode0": bdata_mode0,
        "busstops": busstops,
        "route0": route0,
        "route1": route1,
        "time_bst": time_bst,
        "route0": route0,
        "route1": route1,
        "ads_show": detect_ads_show(request, us),
        "currentPath": request.path.strip("/").split("/"),
    }

    return arender(request, "schedule-bus.html", ctx)
# def schedule_bus


@login_required
def schedule_bus_edit(request, city_slug, bus_id, direction=0):
    if not request.user.is_authenticated:  # юзер залогинен?:
        return HttpResponse(_(u"нет прав доступа"))
    us = get_user_settings(request)
    if us.is_banned():
        return HttpResponse("Запрет на редактирование номеров до %s" % us.ban)
    place = get_object_or_404(Place, slug=city_slug)
    
    if place.id in PLACE_STAFF_MODIFY.keys():
        modify_allowed = modify_allowed = (request.user.id in [user.id for user in place.editors.all()]) or request.user.is_superuser
        if not modify_allowed:
            raise PermissionDenied("You don't have any access rights to this page")

    if 'tram-' in bus_id:
        bus_id = bus_id.replace("tram-", 'tramway-')
    bus = get_object_or_404(Bus, slug=bus_id, places=place, active=True)

    error, okey = '', ''

    try:
        tt_start = json.loads(bus.tt_start)
    except:
        tt_start = {"0": None, "1": None}

    try:
        tt_start_holiday = json.loads(bus.tt_start_holiday)
    except:
        tt_start_holiday = {"0": None, "1": None}

    button = request.POST.get("btn")
    if button:
        # фун-я для проверки введённых значений на соответствие формату времени
        # конвертирует "06:10 06:30" => [timetuple(06:10), timetuple(06:30)] => ["06:10", "06:30"] или "" => None
        def test(a): return [time.strftime('%H:%M', d) for d in [time.strptime(
            t, '%H:%M') for t in a.strip().replace('[', '').replace(']', '').strip().split(' ')]] if a else None
        # TODO: не проверяется, что каждое следующее время должно быть больше предыдущего (если не заполночь)

        button = button.split('.')
        update_fields = []

        # сохранить одно поле одного направления
        if button[0] == 'tt_start':

            try:
                tt_start[button[1]] = test(request.POST.get('%s[%s]' % (button[0], button[1])))
                bus.tt_start = json.dumps(tt_start)
                update_fields.append('tt_start')
            except:
                error = 'Ошибка в поле Направление %s: Рабочий день' % (int(button[1])+1)
                # если хотим дать пользователю доделать изменения, то:
                tt_start[button[1]] = (request.POST.get('%s[%s]' % (button[0], button[1]))).strip().split(' ')
                # если убрать эту строку, то в поле загрузтся содержимое БД до редактирования

        elif button[0] == 'holiday':

            try:
                tt_start_holiday[button[1]] = test(request.POST.get('%s[%s]' % (button[0], button[1])))
                bus.tt_start_holiday = json.dumps(tt_start_holiday)
                update_fields.append('tt_start_holiday')
            except:
                error = 'Ошибка в поле Направление %s: Выходной день' % (int(button[1])+1)
                tt_start_holiday[button[1]] = (request.POST.get('%s[%s]' % (button[0], button[1]))).strip().split(' ')

        elif button[0] == 'route' and button[1] != "2":

            # сохранить все поля одного направления
            try:
                tt_start[button[1]] = test(request.POST.get('tt_start[%s]' % button[1]))
                bus.tt_start = json.dumps(tt_start)
                update_fields.append('tt_start')
            except:
                error = 'Ошибка в поле Направление %s: Рабочий день' % (int(button[1])+1)
                tt_start[button[1]] = (request.POST.get('tt_start[%s]' % button[1])).strip().split(' ')

            try:
                tt_start_holiday[button[1]] = test(request.POST.get('holiday[%s]' % button[1]))
                bus.tt_start_holiday = json.dumps(tt_start_holiday)
                update_fields.append('tt_start_holiday')
            except:
                if len(error) > 0:
                    error += '<br>\n'
                error += 'Ошибка в поле Направление %s: Выходной день' % (int(button[1])+1)
                tt_start_holiday[button[1]] = (request.POST.get('holiday[%s]' % button[1])).strip().split(' ')

        elif button[0] == 'route' and button[1] == "2":
                # сохранить все поля всех направлений
                tt_start_save = {"0": None, "1": None}
                tt_start_holiday_save = {"0": None, "1": None}

                for dir in [0, 1]:
                    sdirection = str(dir)
                    try:
                        tt_start_save[sdirection] = test(request.POST.get('tt_start[%s]' % sdirection))
                        tt_start[sdirection] = tt_start_save[sdirection]
                        if 'tt_start' not in update_fields:
                            update_fields.append('tt_start')
                    except:
                        if len(error) > 0:
                            error += '<br>\n'
                        error += 'Ошибка в поле Направление %s: Рабочий день' % (int(sdirection)+1)
                        tt_start[sdirection] = (request.POST.get('tt_start[%s]' % sdirection)).strip().split(' ')
                        tt_start_save[sdirection] = None

                    try:
                        tt_start_holiday_save[sdirection] = test(request.POST.get('holiday[%s]' % sdirection))
                        tt_start_holiday[sdirection] = tt_start_holiday_save[sdirection]
                        if 'tt_start_holiday' not in update_fields:
                            update_fields.append('tt_start_holiday')
                    except:
                        if len(error) > 0:
                            error += '<br>\n'
                        error += 'Ошибка в поле Направление %s: Выходной день' % (int(sdirection)+1)
                        tt_start_holiday[sdirection] = (request.POST.get('holiday[%s]' % sdirection)).strip().split(' ')
                        tt_start_holiday_save[sdirection] = None
                # for dir in [0, 1]

                if len(update_fields) > 0:
                    bus.tt_start = json.dumps(tt_start_save)
                    bus.tt_start_holiday = json.dumps(tt_start_holiday_save)
        # elif button[0] == 'route' and button[1] == "2"

        if len(update_fields) > 0:
            with reversion.create_revision():
                bus.save(update_fields=update_fields)
                reversion.add_meta(VersionCity, place=place)
                reversion.set_user(us.user)
            okey = 'Изменения сохранены'
            if len(error) > 0:
                okey += ' кроме полей с ошибками'

    # if request.POST.get("btn")

    busstops = []
    for dir in [0, 1]:
        route = routes_get(bus.id, direction=dir)
        busstops.append(route[0].busstop if route else None)
    # for dir in [0, 1]

    tt_start0_textarea = ' '.join(tt_start["0"]) if tt_start.get("0", None) else ''
    tt_start1_textarea = ' '.join(tt_start["1"]) if tt_start.get("1", None) else ''
    holiday0_textarea = ' '.join(tt_start_holiday["0"]) if tt_start_holiday.get("0", None) else ''
    holiday1_textarea = ' '.join(tt_start_holiday["1"]) if tt_start_holiday.get("1", None) else ''

    ctx = {
        'us': us,
        "place": place,
        "bus": bus,
        "busstops": busstops,
        "tt_start0": tt_start.get("0", []),
        "tt_start1": tt_start.get("1", []),
        "tt_start_holiday0": tt_start_holiday.get("0", []),
        "tt_start_holiday1": tt_start_holiday.get("1", []),
        "tt_start0_textarea": tt_start0_textarea,
        "tt_start1_textarea": tt_start1_textarea,
        "holiday0_textarea": holiday0_textarea,
        "holiday1_textarea": holiday1_textarea,
        "error": error,
        "okey": okey,
    }
    return arender(request, "schedule-bus-edit.html", ctx)
# def schedule_bus_edit


def mobile_detect(request):
    # device = {}
    dos = None
    ua = request.META.get('HTTP_USER_AGENT', '').lower()
    if ua.find("iphone") > 0:
        dos = "ios"
    if ua.find("ipad") > 0:
        dos = "ios"
    if ua.find("android") > 0:
        dos = "android"
    if ua.find("opera mini") > 0:
        dos = "opera_mini"
    return dos


@csrf_exempt
def ajax_stop_destination(request):
    try:
        src = request.POST.get('ids')
        dst = request.POST.get('destination')
        src = ujson.loads(src)
        dst = ujson.loads(dst)
        src = NBusStop.objects.filter(id__in=src)
        dst = NBusStop.objects.filter(id__in=dst)
    except:
        return HttpResponse("")
    metric('stop_destination')
    buses = Bus.objects.filter(route__busstop__in=src).filter(
        route__busstop__in=dst).distinct().order_by('order')
    serialized = []
    for b in buses:
        serialized.append({'id': b.id, 'name': str(b)})
    if not serialized:
        serialized = [{'id': "", "name": 'нет доступных маршрутов'}]
    serialized = ujson.dumps(serialized)
    return HttpResponse(serialized)


@csrf_exempt
def ajax_radio_position(request):
    now = int(time.time() * 1000)
    curtrack = (now / 60 * 60 * 1000) % 26
    curtrack = 26 - curtrack
    curtime = now % 3597000
    serialized = {"curtime": curtime, "curtrack": curtrack}
    serialized = ujson.dumps(serialized)
    return HttpResponse(serialized)


def ajax_vk_like_pro(request):
    us = get_user_settings(request)
    x = request.GET.get('x', '-1')
    us.vk_like_pro = int(x)
    us.save()
    return HttpResponse({})


@csrf_exempt
def ajax_radar(request):
    us = get_user_settings(request)
    lat = request.POST.get('lat', '55.9964')
    lon = request.POST.get('lon', '92.9230')
    x, y = float(lon), float(lat)

    allevents = rcache_get("allevents_%s" % us.city_id)
    if not allevents:
        return HttpResponse("")
    serialized = []
    for k, e in allevents.items():
        d = distance_meters(x, y, e.x, e.y)
        if d < 1500:  # and e.bus_id in busfavor:
            serialized.append(e.as_dict())
    return HttpResponse(ujson.dumps(serialized))


def pro_demo(request):
    us = get_user_settings(request)
    now = us.city.now
    if us.pro_demo_date and us.pro_demo_date.date() == now.date():
        return HttpResponseRedirect("/")

    us.pro_demo = True
    us.pro_demo_date = now
    us.busfavor_amount = 10
    us.premium = True
    us.multi_all = True
    us.save()
    metric('pro_demo')
    return HttpResponseRedirect("/")


def monitor_old(request, city_name=None):
    return HttpResponsePermanentRedirect(u"/%s/status/" % city_name)


def monitor_counters(city):
    log_counters = rcache_get('log_counters_%s' % city.id, {})
    counter = {}
    if log_counters:
        counter['uevents'] = log_counters['uevents_len']
        counter['allevents'] = log_counters['allevents_len']
        counter['sleeping'] = log_counters['sleeping']
        counter['zombie'] = log_counters['zombie']
        counter['nearest'] = log_counters['nearest']
        counter['away'] = log_counters.get('away', 0)
    counter['device_connected'] = REDIS_IO.get("counter_online__%s" % city.id)
    if counter['device_connected']:
        counter['device_connected'] = int(counter['device_connected'].decode('utf8'))
    else:
        counter['device_connected'] = 0

    log = {"ups": [], "errors": []}
    cc_key = "log_update_lib_%s" % city.id
    log['ups'] = rcache_get(cc_key, [])
    cc_key = "log_error_update_%s" % city.id
    log['errors'] = rcache_get(cc_key, [])

    return (counter, log)


def status(request, city_name=None):
    city = City.objects.filter(slug=city_name).first()
    place = get_object_or_404(Place, slug=city_name)
    if request.GET.get('date'):
        request_date = request.GET.get('date')
    elif request.POST.get('date'):
        request_date = request.POST.get('date')
    else:
        request_date = None

    today_day = place.now
    if request_date:
        try:
            today_day = datetime.datetime.strptime(request_date, '%Y-%m-%d')
        except ValueError:
            pass

    prev_day = today_day - datetime.timedelta(days=1)

    us = get_user_settings(request)
    transaction = get_transaction(us)
    us.place = place

    counter, log = monitor_counters(place)
    status_server = rcache_get('status_server')
    from_date = place.now - datetime.timedelta(days=90)
    visits_qs = Metric.objects.filter(
        name="visit_%s" % place.id, date__gte=from_date).order_by('id')
    dau_web_qs = Metric.objects.filter(
        name="dau_web_%s" % place.id, date__gte=from_date).values_list("date", "count")
    dau_web_qs = dict(dau_web_qs)
    dau_app_qs = Metric.objects.filter(
        name="dau_app_%s" % place.id, date__gte=from_date).values_list("date", "count")
    dau_app_qs = dict(dau_app_qs)

    mob_qs = MobileSettings.objects.filter(
        place=place, ctime__gte=from_date).values_list("ctime", flat=True)
    mob_qs = [x.date() for x in mob_qs]
    visits = []
    for v in visits_qs:
        vv = v.__dict__
        vv['daily_web_count'] = dau_web_qs.get(v.date, 0)
        vv['daily_app_count'] = dau_app_qs.get(v.date, 0)
        vv['app_installs'] = mob_qs.count(v.date)
        visits.append(vv)

    ms_online = len(REDIS_IO.smembers("ms_online"))
    us_online = len(REDIS_IO.smembers("us_online"))

    # задержки передачи данных для города
    # за период: сегодня-30 дней - сегодня
    if (datetime.date.today() - today_day.date()) > datetime.timedelta(days=15):
        date_from =today_day.date() - datetime.timedelta(days=14)
        date_to = today_day.date() + datetime.timedelta(days=15)
    else:
        date_from = today_day.date() - datetime.timedelta(days=30)
        date_to = today_day.date() + datetime.timedelta(days=1)
    dates = [date_from + datetime.timedelta(days=x)
             for x in range(0, (date_to-date_from).days)]
    statMonth = {'date': today_day.strftime('%d.%m.%y'), 'data': [
        {'date': x.strftime('%d.%m.%y')} for x in dates]}
    delay_avg = 0
    nearest = 0
    cnt_per_day = 0
    old_day = 0

    # за день
    statDay = {'date': today_day.strftime('%d.%m.%y'), 'data': [
        {'hour': x} for x in range(1, 25, 1)]}
    today = today_day.day
    cnt_per_hour = 0
    old_hour = -1
    delay_avg_hour = 0
    nearest_hour = 0

    # данные
    statusMonth = DataSourceStatus.objects.filter(datasource__places=place,
                                            ctime__range=[date_from, date_to],
                                            delay_avg__isnull=False).order_by('ctime')
    for v in statusMonth:
        # статистика за месяц
        if old_day != v.ctime.day:
            if old_day != 0:
                delay_avg = int(delay_avg / cnt_per_day) if cnt_per_day else 0
                nearest = int(nearest / cnt_per_day) if cnt_per_day else 0
                index = 0
                for i in range(0, len(statMonth['data'])):
                    if int(statMonth['data'][i]['date'][0:2]) == old_day:
                        index = i
                        break
                statMonth['data'][index]['delay_avg'] = delay_avg
                statMonth['data'][index]['nearest'] = nearest
            old_day = v.ctime.day
            delay_avg = v.delay_avg
            nearest = v.nearest
            cnt_per_day = 1
        else:
            delay_avg += v.delay_avg
            nearest += v.nearest
            cnt_per_day += 1

        if v.ctime.day == today and v.ctime.month == today_day.month:
            # статистика за день
            if old_hour != v.ctime.hour:
                if old_hour != -1:
                    delay_avg_hour = int(
                        delay_avg_hour / cnt_per_hour) if cnt_per_hour else 0
                    nearest_hour = int(
                        nearest_hour / cnt_per_hour) if cnt_per_hour else 0
                    statDay['data'][old_hour]['delay_avg'] = delay_avg_hour
                    statDay['data'][old_hour]['nearest'] = nearest_hour
                old_hour = v.ctime.hour
                delay_avg_hour = v.delay_avg
                nearest_hour = v.nearest
                cnt_per_hour = 1
            else:
                delay_avg_hour += v.delay_avg
                nearest_hour += v.nearest
                cnt_per_hour += 1
        # if v.ctime.day == today
    # for v in statusMonth

    if cnt_per_day:
        delay_avg = int(delay_avg / cnt_per_day) if cnt_per_day else 0
        nearest = int(nearest / cnt_per_day) if cnt_per_day else 0
        index = 0
        for i in range(0, len(statMonth['data'])):
            if int(statMonth['data'][i]['date'][0:2]) == old_day:
                index = i
                break
        statMonth['data'][index]['delay_avg'] = delay_avg
        statMonth['data'][index]['nearest'] = nearest

    if cnt_per_hour:
        delay_avg_hour = int(
            delay_avg_hour / cnt_per_hour) if cnt_per_hour else 0
        nearest_hour = int(nearest_hour / cnt_per_hour) if cnt_per_hour else 0
        statDay['data'][old_hour]['delay_avg'] = delay_avg_hour
        statDay['data'][old_hour]['nearest'] = nearest_hour
    # заполним 0 часы, данных в которых нет
    for i in range(0, old_hour):
        if not statDay['data'][i].get('delay_avg'):
            statDay['data'][i]['delay_avg'] = 0
        if not statDay['data'][i].get('nearest'):
            statDay['data'][i]['nearest'] = 0
    # END задержки передачи данных для города

    # активных городов сейчас
    l = []
    for c in cities_get(as_list=True):
        l.append('log_counters_%s' % c.id)
    status_server_cities = 0
    log_counters = rcache_mget(l)
    for cnt in log_counters:
        if cnt and 'nearest' in cnt and cnt['nearest'] > 0:
            status_server_cities += 1

    from_date = datetime.datetime.now() - datetime.timedelta(days=14)
    active_cities = MetricTime.objects.filter(name="active_cities", date__gte=from_date).order_by("id")

    try:
        dump_size = os.path.getsize(f'{settings.PROJECT_DIR}/bustime/static/other/db/v8/{p.id}-{p.dump_version}.json')
    except:
        dump_size = 1
    try:
        diff_size = os.path.getsize(f'{settings.PROJECT_DIR}/bustime/static/other/db/v8/{p.id}_ver_{p.patch_version}.json.patch')
    except:
        diff_size = 1

    ctx = {
        'us': us,
        "city": city,
        "place": place,
        "main_page": True,
        "status_page": True,
        "counter": counter,
        "log": log,
        'prev_day': prev_day, 'today_day': today_day,
        'status_server': status_server,
        'status_server_cities': status_server_cities,
        'visits': visits,
        "ms_online": ms_online, "us_online": us_online,
        "transaction": transaction,
        'statMonth': statMonth, 'statDay': statDay,
        'active_cities': active_cities,
        "dump_size": dump_size,
        "diff_size": diff_size,
    }

    return arender(request, "status.html", ctx)
# def status(request, city_name=None)


def status_data(request, city_name=None, day=None, page=None, search_gn=None, search_bn=None):
    place = get_object_or_404(Place, slug=city_name)
    if not day:
        return HttpResponseRedirect("./%s/" % place.now.date())
    us = get_user_settings(request)
    device = mobile_detect(request)
    search_gn = request.GET.get("search_gn")
    search_bn = request.GET.get("search_bn")

    bus_id = request.GET.get("bus_id")
    if not search_gn and not search_bn and bus_id:
        try:
            bus_id = int(bus_id)
            bus = bus_get(bus_id)
        except:
            bus = None
    else:
        bus = None
    now = place.now
    r = re.compile('^\d{4}-\d{2}-\d{2}$')
    if not r.match(day):
        raise Http404("Wrong Date Format")
    day = datetime.datetime.strptime(day, "%Y-%m-%d")
    old_day = None
    if day:
        if request.user.is_authenticated or us.is_data_provider:
            hday = now - datetime.timedelta(days=30)
        else:
            hday = now - datetime.timedelta(days=7)
        if day < hday:
            old_day = hday
    day_start = day.replace(hour=3, minute=0, second=0, microsecond=0)
    day_stop = day_start + datetime.timedelta(hours=24)
    # состояние машин города за день
    statCars = {}
    # разобьём сутки на 15-и минутные интервалы
    INTERVAL = 900  # кол-во секунд в 1 интервале
    INTERVALS = int(1440 * 60 / INTERVAL)  # кол-во интервалов в сутках
    # в таком порядке будем хранить данные по интервалам:
    # потеря сигнала: {'1':[INTERVALS]}, все значения инициализируем 0 (в случае пропуска будет 0 разрывов)

    """
    если нужно показывать все машины, включая те, событий для которых нет
    # выбираем все машины города и заполняем словарь statCars
    if bus:
        cars = Vehicle1.objects.filter(bus=bus, bus__city=city)
    else:
        cars = Vehicle1.objects.filter(bus__city=city)

    for v in cars:
        if len(v.gosnum) == 0:  continue
        gosnum = v.gosnum.replace('  ', '').replace(' ', '').strip()    # пишется всяко :(
        statCars[gosnum] = {"uid": '',
                            "1":[-1 for x in range(INTERVALS)], # -1 = событий нет
                            "4":[0 for x in range(INTERVALS)],   # посчитаем остановки на конечных
                            "7":[0 for x in range(INTERVALS)]   # и сходы с маршрута
                            }
    # for v in Vehicle1.objects.filter(bus__city=city)
    """

    # выбираем все события машин за день
    if bus:
        statusVeh = VehicleStatus.objects.filter(city=place.id,
                                                 bus=bus.id,
                                                 city_time__range=(day_start, day_stop)
                                                 ).order_by('uniqueid', 'city_time')
    elif search_gn:
        statusVeh = VehicleStatus.objects.filter(city=place.id,
                                                 city_time__range=(day_start, day_stop),
                                                 gosnum__icontains=search_gn).order_by('uniqueid', 'city_time')
    elif search_bn:
        statusVeh = VehicleStatus.objects.filter(city=place.id,
                                                 city_time__range=(day_start, day_stop)
                                                 ).order_by('uniqueid', 'city_time')
        vehs = Vehicle.objects.filter(uniqueid__in=statusVeh.values('uniqueid'),
                                        bortnum__icontains=search_bn).values_list('uniqueid', flat=True)
        statusVeh = VehicleStatus.objects.filter(city=place.id,
                                                 city_time__range=(day_start, day_stop),
                                                 uniqueid__in=list(vehs)).order_by('uniqueid', 'city_time')
    else:
        statusVeh = VehicleStatus.objects.filter(city=place.id,
                                                 city_time__range=(day_start, day_stop)
                                                 ).order_by('uniqueid', 'city_time')

    vehs = Vehicle.objects.filter(uniqueid__in=statusVeh.values('uniqueid')) #.values('uniqueid', 'gosnum', 'bortnum')
    vehicles_info = {}
    for v in vehs:
        vehicles_info[v.uniqueid] = {'gosnum': v.gosnum, 'bortnum': v.bortnum}

    if old_day:
        statusVeh = []

    uevents = {}
    if statusVeh:
        uids = REDIS.smembers("place__%s" % place.id)
        uids = list([x.decode('utf8') for x in uids])
        to_get = [f'event_{uid}' for uid in uids]
        for e in rcache_mget(to_get):
            if e:
                uevents[e['uniqueid']] = e

    # считаем события:
    for v in statusVeh:
        gosnum = v.gosnum
        if gosnum:
            gosnum = gosnum.replace('  ', '').replace(' ', '').strip()    # пишется всяко :(
        else:
            gosnum = v.uniqueid.replace(' ', '').strip()[:15]

        status = vehicles_info.get(v.uniqueid, {})
        uevent = uevents.get(v.uniqueid, {})
        bortnum = status.get('bortnum', None)
        label = uevent.get('label', None)
        if not statCars.get(gosnum):
            statCars[gosnum] = {"uid": v.uniqueid,
                                "1": [-1 for x in range(INTERVALS)],      # -1 = событий нет, 0 = Отключений нет, 1 = Нет данных по ТС
                                "4": [0 for x in range(INTERVALS)],       # остановки на конечных
                                "7": [0 for x in range(INTERVALS)],       # сходы с маршрута
                                "label": bortnum if not label else label
                                }
        # рудимент от "выбираем все машины города" (см. выше)
        elif statCars[gosnum]["uid"] == '':
            statCars[gosnum]["uid"] = v.uniqueid

        # рассчитаем № интервала, в который попадает запись
        if v.event_time.hour <= 3:
            hour = 24 + v.event_time.hour
        else:
            hour = v.event_time.hour

        # шкала интервалов начинается не с 0ч, а 3ч, время надо сдвинуть назад
        index = int(( (hour - 3) * 3600 +
                     v.event_time.minute * 60 + v.event_time.second) / INTERVAL)
        # инкрементриуем счетчик событий
        if index < INTERVALS:   # просто чтоб не выпасть в осадок
            if v.status == 1:   # "Нет данных по ТС"
                if statCars[gosnum]["1"][index] < 0:
                    statCars[gosnum]["1"][index] = 1
                else:
                    statCars[gosnum]["1"][index] += 1
                # здесь можно все значения до конца массива '1' установить в -1
                if index+1 < INTERVALS:
                    for i in range(index+1, INTERVALS, 1):
                        statCars[gosnum]["1"][i] = -1
            elif v.status == 4:   # "Пришел на конечную"
                statCars[gosnum]["4"][index] += 1
            elif v.status == 7:   # "Сошел с маршрута"
                statCars[gosnum]["7"][index] += 1
            elif v.status == 8 and bus and uevent.get('bus_id') != bus.id:   # "изменился маршрут"
                for i in range(index, INTERVALS, 1):
                    statCars[gosnum]["1"][i] = -1   # событий нет
            else:
                if bus and uevent.get('bus_id') != bus.id:
                    for i in range(index, INTERVALS, 1):
                        statCars[gosnum]["1"][i] = -1
                else:
                    if statCars[gosnum]["1"][index] < 0:
                        for i in range(index, INTERVALS, 1):
                            statCars[gosnum]["1"][i] = 0

    # for v in statusVeh
    # END состояние машин города за день
    paginator = Paginator(list(statCars.items()), 40)
    if request.GET.get('page'):
        if bus_id:
            return HttpResponsePermanentRedirect(u"./%s/?bus_id=%s/page-%s/" % (day.strftime("%Y-%m-%d"), bus_id, request.GET.get('page')))
        else:
            return HttpResponsePermanentRedirect(u"./%s/page-%s/" % (day.strftime("%Y-%m-%d"), request.GET.get('page')))

    try:
        statCars = paginator.page(page)
    except PageNotAnInteger:
        statCars = paginator.page(1)
    except EmptyPage:
        statCars = paginator.page(paginator.num_pages)

    intervals_range = range(0, INTERVALS * 5, 5)
    iterator = itertools.cycle(intervals_range)
    if now.date() == day.date():
        gray_value = int(((now.hour - 3) * 3600 + now.minute *
                          60 + now.second) / INTERVAL)
    else:
        gray_value = int((25 * 3600) / INTERVAL)

    buses = buses_get(place)

    ctx = {'us': us, "place": place, 'day': day.strftime("%Y-%m-%d"), 'date': day,
           'statCars': statCars, 'iterator': iterator, 'page': page,
           'secInInterval': INTERVAL, 'gray_value': gray_value,
           "buses": buses, "bus": bus, "search_gn": search_gn, "old_day": old_day, "device": device}
    return arender(request, "status-data.html", ctx)
# def status_data(request, city_name=None)


@csrf_exempt
def transport(request, city_name=None, day=None, bid=None, uid=None, time=None):
    us = get_user_settings(request)
    if not city_name:
        city_name = request.POST.get("city_name", "")
    place = get_object_or_404(Place, slug=city_name)

    # ID машины
    if not uid:
        uid = request.POST.get("uid", "2b677443")

    if re.search(u'[ЙЦУКЕНГШЩЗХЪФЫВАПРОЛДЖЭЯЧСМИТЬБЮЁ]', uid.upper()):  # uid is gosnum
        gos = uid
    else:
        gos = None
    old_day = None
    r = re.compile('\d{4}-\d{2}-\d{2}')
    if day and r.match(day):
        try:
            day = datetime.datetime.strptime(day, "%Y-%m-%d")
        except:
            url = f"/{city_name}/transport/{datetime.datetime.now().date().strftime('%Y-%m-%d')}"
            if uid:
                url += f"/{uid}"
            return HttpResponseRedirect(url)
        if request.user.is_authenticated or us.is_data_provider:
            hday = place.now - datetime.timedelta(days=7)
        else:
            hday = place.now - datetime.timedelta(days=3)
        if day < hday:
            old_day = hday
    elif request.POST.get("day") and r.match(request.POST.get("day")):
        day = datetime.datetime.strptime(request.POST.get("day"), "%Y-%m-%d")
    else:
        day = place.now

    if not time:
        time = request.POST.get("time", request.GET.get("time", ""))


    day_start = day.replace(hour=3, minute=0, second=0, microsecond=0)
    day_stop = day_start + datetime.timedelta(hours=24)
    # список ID маршрутов города
    city_ids = Bus.objects.filter(places__id=place.id).values_list('id', flat=True)

    if gos:
        statuses = VehicleStatus.objects.filter(city_time__range=(day_start, day_stop),
                                                city=place.id,
                                                gosnum=gos).order_by('city_time')
        uevents = Uevent.objects.using('bstore').filter(bus_id__in=list(city_ids),
                                                        gosnum=gos,
                                                        timestamp__range=(day_start, day_stop)).order_by('timestamp')
    elif uid:
        statuses = VehicleStatus.objects.filter(city_time__range=(day_start, day_stop),
                                                city=place.id,
                                                uniqueid=uid).order_by('city_time')
        uevents = Uevent.objects.using('bstore').filter(bus_id__in=list(city_ids),
                                                        uniqueid=uid,
                                                        timestamp__range=(day_start, day_stop)).order_by('timestamp')
    elif bid:   # конкретный маршрут
        statuses = VehicleStatus.objects.filter(city_time__range=(day_start, day_stop),
                                                city=place.id,
                                                bus_id=bid).order_by('city_time')
        uevents = Uevent.objects.using('bstore').filter(bus_id=bid,
                                                        timestamp__range=(day_start, day_stop)).order_by('timestamp')
    else:
        statuses = None
        uevents = None
    # else if gos
    for status in statuses:
        if status.endpoint:
            try:
                status.endpoint = Route.objects.get(id=status.endpoint)
            except:
                status.enpoint = None
        if status.bus:
            status.bus = bus_get(status.bus)

    if statuses:
        bus = bus_get(statuses.latest('city_time').bus)
        endpoint_cnt = statuses.filter(status=4).count()/2
        statuses_cnt = statuses.count()
        sstatuses = chunks(statuses, int(math.ceil(statuses_cnt/4.0)))
    else:
        bus = None
        endpoint_cnt = 0
        statuses_cnt = 0
        sstatuses = statuses

    events = []
    uevents_cache = rcache_get("uevents_%s" % place.id, {})
    px, py = None, None  # предыдущие координаты
    pt = None   # предыдущее время
    dis = 0  # текущий пробег
    probeg = 0  # нарастающий пробег
    if uevents:
        for u in uevents:
            if getattr(u, 'x', None) and getattr(u, 'y', None):
                x, y = u.x, u.y
                # calc probeg
                if px:
                    t = int(u.timestamp.strftime('%s'))  # время отметки
                    deltatime = t - pt
                    if deltatime > 0:
                        dis = int(distance_meters(x, y, px, py) * 1.05)
                        speed = round(dis / deltatime * 3.6, 0)   # м/с => км/ч
                        if dis > 0 and speed > 0 and speed < 140:
                            probeg += dis
                # if px
                # store prev values:
                px, py = x, y
                pt = int(u.timestamp.strftime('%s'))
                uevent_cache = uevents_cache.get(u.uniqueid, {})
                try:
                    bortnum = Vehicle.objects.get(uniqueid=u.uniqueid).bortnum
                except:
                    bortnum = None
                label = uevent_cache.get('label', None)
                events.append({
                    "uniqueid": u.uniqueid,
                    "timestamp": u.timestamp.strftime("%H:%M:%S"),
                    "bus_id": u.bus_id,
                    "heading": u.heading if u.heading != None else 0,
                    "speed": u.speed if u.speed else 0,
                    "lon": x,
                    "lat": y,
                    "direction": u.direction if u.direction != None else -1,
                    "gosnum": u.gosnum if u.gosnum else statuses[0].gosnum if statuses else u.uniqueid[:15],
                    "bortnum": bortnum,
                    "probeg": dis,
                    "label": bortnum if not label else label,
                })
            # if u.get('point', False)
        # for u in uevents

        if gos and len(events):  # by gosnom
            uid = events[0]["uniqueid"]

        probeg = str(round(probeg/1000.0, 1))
    # if uevents

    ctx = {"bus": bus, "uid": uid, "gos": gos if gos else '', "day": day, "time": time,
           "place": place, "statuses": sstatuses, "statuses_cnt": statuses_cnt,
           "uevents": events, "endpoint_cnt": endpoint_cnt, "us": us,
           "probeg": probeg, "old_day": old_day}

    return arender(request, "transport.html", ctx)
# def transport(request, city_name=None, day=None, uid=None)


@csrf_exempt
def ajax_transport(request):
    place_slug = request.POST.get("place_slug", "")
    place = get_object_or_404(Place, slug=place_slug)
    uid = request.POST.get("uid", "")
    bus_id = request.POST.get("bus_id", 0)
    day = datetime.datetime.strptime(request.POST.get("day"), "%Y-%m-%d")
    day_start = day.replace(hour=3, minute=0, second=0, microsecond=0)
    day_stop = day_start + datetime.timedelta(hours=24)

    if len(uid):
        city_ids = Bus.objects.filter(places__id=place.id).values_list('id', flat=True)
        uevents = Uevent.objects.using('bstore').filter(
            bus_id__in=list(city_ids),
            uniqueid=uid,
            timestamp__range=(day_start, day_stop)).order_by('timestamp')
    else:
        uevents = Uevent.objects.using('bstore').filter(
            timestamp__range=(day_start, day_stop),
            bus_id=bus_id).order_by('timestamp')

    events = []
    uevents_cache = rcache_get("uevents_%s" % place.id, {})
    px, py = None, None  # предыдущие координаты
    dis = 0  # текущий пробег
    probeg = 0  # нарастающий пробег
    if uevents:
        for u in uevents:
            if getattr(u, 'x', None) and getattr(u, 'y', None):
                x, y = u.x, u.y
                try:
                    bortnum = Vehicle.objects.get(uniqueid=u.uniqueid).bortnum
                except:
                    bortnum = None
                events.append({
                    "uniqueid": u.uniqueid,
                    "timestamp": u.timestamp.strftime("%H:%M:%S"),
                    "bus_id": u.bus_id,
                    "heading": u.heading,
                    "speed": u.speed if u.speed else 0,
                    "lon": x,
                    "lat": y,
                    "direction": u.direction if u.direction != None else -1,
                    "gosnum": u.gosnum if u.gosnum else u.uniqueid[:15],
                    "bortnum": bortnum,
                    "probeg": dis
                })
            # if getattr(u, "point", None)
        # for u in uevents
    # if uevents

    return HttpResponse(ujson.dumps(events))
# def ajax_transport(request)


# обработчик запроса статистики города
@csrf_exempt
def ajax_status_data(request):
    city_id = request.POST.get('city_id', None)
    date = request.POST.get('date')
    if not date:
        return HttpResponse("")

    response = []

    if city_id:
        place = get_object_or_404(Place, id=int(city_id))
    else:
        place = None

    now = datetime.datetime.strptime(date, "%d.%m.%y").date()

    # за день
    statDay = {'date': now.strftime('%d.%m.%y'), 'data': [
        {'hor': x} for x in range(1, 25, 1)]}
    today = place.now.day
    cnt_per_hour = 0
    old_hour = -1
    delay_avg_hour = 0
    nearest_hour = 0

    # данные
    statusMonth = DataSourceStatus.objects.filter(datasource__places=place,
                                            ctime__year=now.year,
                                            ctime__month=now.month,
                                            ctime__day=now.day,
                                            delay_avg__isnull=False).order_by('ctime')
    for v in statusMonth:
        # статистика за день
        if old_hour != v.ctime.hour:
            if old_hour != -1:
                delay_avg_hour = int(
                    delay_avg_hour / cnt_per_hour) if cnt_per_hour else 0
                nearest_hour = int(
                    nearest_hour / cnt_per_hour) if cnt_per_hour else 0
                statDay['data'][old_hour]['delay_avg'] = delay_avg_hour
                statDay['data'][old_hour]['nearest'] = nearest_hour
            old_hour = v.ctime.hour
            delay_avg_hour = v.delay_avg
            nearest_hour = v.nearest
            cnt_per_hour = 1
        else:
            delay_avg_hour += v.delay_avg
            nearest_hour += v.nearest
            cnt_per_hour += 1
    # for v in statusMonth

    if cnt_per_hour:
        delay_avg_hour = int(
            delay_avg_hour / cnt_per_hour) if cnt_per_hour else 0
        nearest_hour = int(nearest_hour / cnt_per_hour) if cnt_per_hour else 0
        statDay['data'][old_hour]['delay_avg'] = delay_avg_hour
        statDay['data'][old_hour]['nearest'] = nearest_hour

    response.append(statDay)

    return HttpResponse(ujson.dumps(response))
# def ajax_status_data(request)


def status_sheet(request, city_name=None):
    city = get_object_or_404(City, slug=city_name)
    us = get_user_settings(request)
    us.city = city
    ctx = {'us': us, "city": city}
    return arender(request, "status-sheet.html", ctx)


def monitor_bus(request, city_name=None, bus_name=None):
    us = get_user_settings(request)
    city = get_object_or_404(City, slug=city_name)
    bus = get_object_or_404(Bus, slug=bus_name, city=city)
    us.city = city  # dirty hack
    ctx = {'us': us, "city": city, 'bus': bus}

    route0 = routes_get(bus.id, direction=0)
    route1 = routes_get(bus.id, direction=1)
    ctx['route0'] = route0
    ctx['route1'] = route1

    busstops = []
    for i in route0:
        busstops.append(i.busstop)
    for i in route1:
        busstops.append(i.busstop)
    ctx['busstops'] = busstops

    return arender(request, "monitor_bus.html", ctx)


def anomalies(request, city_name=None):
    city = get_object_or_404(City, slug=city_name)
    us = get_user_settings(request)
    ctx = {'us': us, "city": city}

    return arender(request, "anomalies.html", ctx)


@csrf_exempt
def pin(request):
    now = datetime.datetime.now()
    us = get_user_settings(request)
    pin = request.POST.get('pin', '')
    if not pin.replace("-", '').isdigit():
        return HttpResponse(u"Ошибка: ПИН может содержать только цифры")
    f = open('/tmp/pin_check.txt', 'a')
    f.write("\n%s: %s %s " % (now, us.id, pin))

    tr = Transaction.objects.filter(pin=pin).order_by('-id')
    if tr:
        tr = tr[0]
        f.write("ok")
        f.close()
    else:
        return bonus_activate(request, us, pin)
        f.close()

    f = open('/tmp/bustime_pin.csv', 'a')  # !!!
    f.write("%s %s:%s %s->%s\n" % (now, tr.id, tr.pin, tr.user, us.id))
    f.close()

    if tr.user:
        premium_deactivate(tr.user)
        wsocket_cmd('reload', {}, us_id=tr.user_id)
    tr.user = us
    tr.notified = False
    tr.save()

    premium_activate(us, key=tr.key)
    wsocket_cmd('reload', {}, us.id)

    return HttpResponseRedirect("/")


def bonus_activate(request, us, pin):
    b = Bonus.objects.filter(pin=pin).order_by('-id')
    if not b:
        return arender(request, "message.html", {"message": _(u"Неверный пин код") + u" %s" % pin})
    else:
        b = b[0]

    if b.activated:
        msg = _(u"Пин код уже был активирован") + u" %s, %s:%s" % (
            b.mtime.date(), b.mtime.hour, b.mtime.minute)
        return arender(request, "message.html", {"message": msg})

    comment = "bonus, id=%s, comment=%s" % (b.id, b.comment)

    now = datetime.datetime.now()
    transaction = get_transaction(us)
    if transaction and transaction.key == b.key:
        end_time = transaction.end_time + datetime.timedelta(days=b.days)
        comment = comment + ", extended"
    else:
        end_time = now + datetime.timedelta(days=b.days)
        premium_activate(us, key=b.key)

    if b.key == "premium":
        pin = None
    else:
        pin = b.pin

    Transaction.objects.create(
        user=us, key=b.key,
        value=b.days, fiat=b.fiat,
        comment=comment,
        end_time=end_time,
        pin=pin,
        bonus=b)

    b.activated = True
    b.save()

    return HttpResponseRedirect("/")


def city_slug_redir(request, force_city):
    city = CITY_MAP[force_city]
    return HttpResponsePermanentRedirect(u"/%s/" % city.slug)


def settings__gps_send_of(us):
    to_ignore = rcache_get("to_ignore_%s" % us.place.id, {})
    now = us.place.now
    uniqueid = 'us_%s' % us.id

    # не дадим выстрелить себе в ногу
    if us.gps_send and us.gps_send_of and us.gps_send_of != str(us.id):
        to_ignore[uniqueid] = us.gps_send_of
    elif to_ignore.get(us.id):
        del to_ignore[uniqueid]

    rcache_set("to_ignore_%s" % us.place.id, to_ignore, 60*60*24)


def settings_view(request, other=None, place_slug=None):
    us = get_user_settings(request)
    transaction = get_transaction(us)
    place = get_object_or_404(Place, slug=place_slug)
    noga = None
    ban = None
    if other:
        if not transaction or not transaction.vip:
            return HttpResponse(f"{other}, {transaction}")
        us = us_get(other)
        transaction = get_transaction(us)
        noga = True
        if us:
            ban = us.is_banned()#ban = rcache_get("ban_%s" % us.id)

    countries = Country.objects.filter(available=True).order_by("name")
    tcard = place.id in PLACE_TRANSPORT_CARD.keys()

    # defaults for extra attrs
    if not 'live_indicator' in us.attrs:
        us.attrs['live_indicator'] = True
    if not 'plusone' in us.attrs:
        us.attrs['plusone'] = True
    if not 'dark_theme' in us.attrs:
        us.attrs['dark_theme'] = "off"

    ctx = {"us": us, "place": place, "transaction": transaction,
           "countries": countries,
           "other": other, "noga": noga,
           "ban": ban, "request": request, "tcard": tcard}

    if not request.POST:
        return arender(request, "settings.html", ctx)

    for k in ["sound", "sound_plusone",
              "voice", "multi_all",
              "font_big", "busfav_hold",
              "p2p_video", "edit_mode",
              "expert"]:
        setting, value = k, request.POST.get(k)
        if value:
            value = True
        else:
            value = False

    busfavor_amount = request.POST.get("busfavor_amount", "10")
    busfavor_amount = int(busfavor_amount)
    if busfavor_amount in [0, 5, 10, 20, 30]:
        us.busfavor_amount = busfavor_amount

    us.save()
    return HttpResponseRedirect("/")


def settings_profile(request, city_name=None, other=None):
    if not request.user.is_authenticated:
        return HttpResponseRedirect("/register/")
    place = get_object_or_404(Place, slug=city_name)
    us = get_user_settings(request)
    transaction = get_transaction(us)
    noga = None
    ban = None
    if other:
        if not transaction or not transaction.vip:
            return HttpResponseRedirect("/")
        us = us_get(other)
        transaction = get_transaction(us)
        noga = True
        if us:
            ban = us.is_banned()#ban = rcache_get("ban_%s" % us.id)
    buses = buses_get(place)

    si = SpecialIcon.objects.filter(us=us)
    if si:
        si = si[0]
    beauty_phone = None
    if us.user and us.user.groups.filter(name="sms"):
        u = us.user.username
        beauty_phone = "+%s-%s-%s-%s" % (u[0], u[1:4], u[4:7], u[7:])


    from taxi.models import TaxiUser, CarTaxi, TAXI_TYPE, TAXI_CLASS
    taxiuser = TaxiUser.objects.filter(user=request.user).first()

    us.city = place
    ctx = {
        "us": us,
        "place": place,
        "transaction": transaction,
        "buses": buses,
        "si": si,
        "other": other,
        "noga": noga,
        "ban": ban,
        "request": request,
        "beauty_phone": beauty_phone,
        'taxi_type': dict(TAXI_TYPE),
        'car_class': dict(TAXI_CLASS),
        'taxiuser': taxiuser,
        'cars': CarTaxi.objects.filter(taxist=taxiuser).order_by('gos_num'),
    }

    if taxiuser and taxiuser.driver and taxiuser.name and taxiuser.phone and len(ctx['cars']) == 0:
        messages.error(request, _("Необходимо добавить машину"))

    return arender(request, "settings_profile.html", ctx)


def settings_photo(request, other=None):
    us = get_user_settings(request)
    transaction = get_transaction(us)
    photos_all = get_ava_photos()
    person = request.GET.get('person')

    class A:
        pass
    persons = []
    variants = []
    last_person = None
    for p in photos_all:
        a = A()
        a.src = p+".png"
        _, a.person, variant = p.split("_")
        if person and a.person == person:
            variants.append(a)
        if last_person != a.person:
            persons.append(a)
        last_person = a.person

    ctx = {"us": us, "transaction": transaction,
           'variants': variants, 'persons': persons}

    driver_ava = request.GET.get('src', '').replace('.png', '')

    if not driver_ava:
        return arender(request, "settings_photo.html", ctx)
    else:
        us.driver_ava = driver_ava
        if us.driver_ava in photos_all:
            us.save()
        if us.gosnum and us.gps_send_bus:
            vhs = Vehicle1.objects.filter(
                gosnum=us.gosnum, bus=us.gps_send_bus).update(driver_ava=us.driver_ava)

        return HttpResponseRedirect("/settings_profile/")


def gban(request, us_id=None):
    us = get_user_settings(request)
    transaction = get_transaction(us)
    if us_id and transaction.vip:
        z = us_get(us_id)
        until = z.city.now+datetime.timedelta(days=1)
        z.ban = until
        z.save()
        send_mail('gban by %s for %s' % (us.id, z.id), "until: %s" % until,
                  'noreply@mail.address', ['admin@mail.address'], fail_silently=True)
    return HttpResponseRedirect("/settings/%s/" % us_id)


def explorer_gban(request, id_=None):
    us = get_user_settings(request)
    ms = ms_get(id_)
    until = ms.city.now+datetime.timedelta(days=90)
    ms.ban = until
    ms.save()
    send_mail('gban by %s for ms=%s' % (us.id, ms.id), "until: %s" % until,
              'noreply@mail.address', ['admin@mail.address'], fail_silently=True)
    return HttpResponseRedirect("../")


def radar(request):
    us = get_user_settings(request)
    transaction = get_transaction(us)
    ctx = {"us": us, "transaction": transaction, "main_page": True,}
    return arender(request, "radar.html", ctx)


def agreement(request):
    return arender(request, "agreement.html", {})


def cookies_policy(request):
    return arender(request, "cookies.html", {})


@login_required
def route_edit(request, city_name, bus_name):
    place = get_object_or_404(Place, slug=city_name)
    if bus_name.isdigit():
        buses = Bus.objects.filter(id=int(bus_name))
    else: # for backward compat
        buses = Bus.objects.filter(slug=bus_name, places=place, active=True)
    buses_count = buses.count()
    if not buses_count:
        raise Http404("Route does not exist")
    if buses_count > 1:
        bus_ids = buses.values_list('id', flat=True)
        bus_ids = ','.join(map(str, bus_ids))
        return HttpResponse("Delete duplicate! ID: [%s]" % bus_ids)
    bus = buses.first()
    us = get_user_settings(request)
    transaction = get_transaction(us)

    ctx_place = {
        'id': place.id,
        'name': place.name,
        'slug': place.slug,
        'point': {
            'x': place.point.x,
            'y': place.point.y,
        },
        'osm_id': place.osm_id,
        'osm_area_id': place.osm_area_id,
        'country_code': place.country_code,
    }   #, default=str, ensure_ascii=False)

    ctx = {"us": us, "bus": bus, 'place':ctx_place}

    if request.method == 'POST':
        form = BusStopNewForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            point = form.cleaned_data['point']
            with reversion.create_revision():
                stop = NBusStop.objects.create(name=name, point=point)
                reversion.set_user(us.user)
                add_stop_geospatial(stop)
            jdata = serializers.serialize("json", [stop])
            Diff.objects.create(us=us, action=1, status=1,
                                data=jdata, model="nbusstop",
                                model_pk=stop.pk)
            ctx['new_stop'] = json.dumps(
                {'nbusstop_id': stop.id, 'name': name})

            return HttpResponse(json.dumps({
                "data": {
                    "id": stop.id,
                    "ttype": stop.ttype,
                    "name": stop.name,
                    "name_alt": stop.name_alt,
                    "x": stop.point.x,
                    "y": stop.point.y,
                    "moveto": stop.moveto,
                    "tram_only": stop.tram_only,
                    "slug": stop.slug
                },
                "status": "success"
            }), content_type="application/json")
        else:
            return HttpResponse(json.dumps({
                "data": form.errors,
                "status": "error"
            }), content_type="application/json")
    else:
        form = BusStopNewForm()

    route0 = routes_get(bus.id, direction=0)
    route1 = routes_get(bus.id, direction=1)

    ctx['route0'] = route0
    ctx['route1'] = route1
    ctx["form"] = form

    # нужно собрать все остановки всех маршрутов в данном place
    buses_ids = [b.id for b in buses_get(place, True)]  # маршруты города
    stops_ids = list(Route.objects.filter(bus_id__in=buses_ids).distinct('busstop_id').values_list('busstop_id', flat=True))
    ctx['busstops'] = NBusStop.objects.filter(id__in=stops_ids)

    return arender(request, "route_edit.html", ctx)
# def route_edit

def uevents_on_map(request, city_name):
    place = get_object_or_404(Place, slug=city_name)
    us = get_user_settings(request)
    transaction = get_transaction(us)

    uids = REDIS.smembers("place__%s" % place.id)
    uids = list([x.decode('utf8') for x in uids])
    to_get = [f'event_{uid}' for uid in uids]
    uevents = rcache_mget(to_get)
    uevents_json = []

    for u in uevents:
        if u is not None:
            if 'bus' in u:
                if u['bus'] == None:
                    continue
                elif type(u['bus']) != int:
                    u['bus'] = u['bus'].id
            elif 'bus_id' in u:
                if u['bus_id'] == None:
                    continue
                else:
                    u['bus'] = u['bus_id']

            if 'history' in u:
                del u['history']

            bus = bus_get(u['bus'])
            u['bus_name'] = six.text_type(bus.name if bus else '')
            u['bus_city'] = six.text_type(
            bus.city.name if bus and bus.city else '')
            timestamp = six.text_type(u['timestamp']).split('.')[0]
            timestamp = timestamp.split(' ')[1]
            u['timestamp'] = timestamp
            uevents_json.append(u)

    import json as not_ujson
    def myconverter(o):
        if isinstance(o, datetime.datetime):
            return o.__str__()
    uevents = not_ujson.dumps(uevents_json, default = myconverter)
    ctx = {"place": place, "us": us, "uevents": uevents, "uevents_on_map_page": True}
    return arender(request, "uevents-on-map.html", ctx)
# uevents_on_map

@csrf_exempt
def ajax_uevents_on_map(request):
    place_id = int(request.POST.get("place_id", 0))
    place = Place.objects.get(id=place_id)
    if place:
        uids = REDIS.smembers("place__%s" % place.id)
        uids = list([x.decode('utf8') for x in uids])
        to_get = [f'event_{uid}' for uid in uids]
        uevents = rcache_mget(to_get)
        uevents_json = []

        for u in uevents:
            if u:
                if 'bus' in u:
                    if u['bus'] == None:
                        continue
                    elif type(u['bus']) != int:
                        u['bus'] = u['bus'].id
                elif 'bus_id' in u:
                    if u['bus_id'] == None:
                        continue
                    else:
                        u['bus'] = u['bus_id']

                if 'history' in u:
                    del u['history']

                bus = bus_get(u['bus'])
                u['bus_name'] = six.text_type(bus.name if bus else '')
                u['bus_city'] = six.text_type(
                    bus.city.name if bus and bus.city else '')
                timestamp = six.text_type(u['timestamp']).split('.')[0]
                timestamp = timestamp.split(' ')[1]
                u['timestamp'] = timestamp
                uevents_json.append(u)

        import json as not_ujson
        def myconverter(o):
            if isinstance(o, datetime.datetime):
                return o.__str__()
        uevents = not_ujson.dumps(uevents_json, default = myconverter)
    else:
        uevents = {}
    return HttpResponse(ujson.dumps(uevents))
# ajax_uevents_on_map

@login_required
def detector(request, city_name, bus_name):
    city = get_object_or_404(City, slug=city_name)
    bus = get_object_or_404(Bus, slug=bus_name, city=city)
    us = get_user_settings(request)
    transaction = get_transaction(us)
    ctx = {"city": bus.city, "us": us, "bus": bus}

    route0 = routes_get(bus.id, direction=0)
    route1 = routes_get(bus.id, direction=1)

    ctx['route0'] = route0
    ctx['route1'] = route1

    busstops = []
    for busstop in NBusStop.objects.filter(city=bus.city).order_by("name"):
        busstops.append(busstop)
    ctx['busstops'] = busstops

    return arender(request, "detector.html", ctx)


@login_required
def route_delete(request, city_name, bus_name, yes=None):
    place = get_object_or_404(Place, slug=city_name)
    bus = get_object_or_404(Bus, slug=bus_name, places__id=place.id)
    us = get_user_settings(request)
    # check permissions!
    if request.user.id not in [user.id for user in place.editors.all()] and \
       not request.user.is_superuser:
        return HttpResponse(_(u"нет прав доступа"))
    ctx = {"place": place, "bus": bus, "us": us}
    confirmation = request.POST.get('confirmation')
    if yes:
        bus_route_version(bus, user=(us.user if us.user else request.user),
                            delete=True, place_id=place.id)
        with reversion.create_revision():
            bus.active = False
            bus.save(refresh_routes=True)   # вызовет buses_get(place, force=True)
            reversion.set_comment('Удалён маршрут %s' % bus.name)
            if us.user:
                reversion.set_user(us.user)
        return HttpResponseRedirect(place.get_absolute_url())
    return arender(request, "route_delete.html", ctx)
# route_delete


def gvotes_get():
    gvotes = rcache_get("gvotes")
    if gvotes is None:
        a = GVote.objects.filter(positive=False).count()
        b = GVote.objects.filter(positive=True).count()
        gvotes = [a, b]
        rcache_set("gvotes", gvotes, 60*60*24)
    return gvotes


def gvote_set(us, positive):
    gvotes = gvotes_get()

    try:
        gv = GVote.objects.get(user=us)
        if gv.positive == positive:
            return gvotes
        else:
            gv.positive = positive
            gv.save()
            if positive == True:
                gvotes = [gvotes[0]-1, gvotes[1]+1]
            else:
                gvotes = [gvotes[0]+1, gvotes[1]-1]
    except GVote.DoesNotExist:
        gv = GVote.objects.create(user=us, positive=positive)
        if positive == True:
            gvotes = [gvotes[0], gvotes[1]+1]
        else:
            gvotes = [gvotes[0]+1, gvotes[1]]

    rcache_set("gvotes", gvotes, 60*60*24)
    wsocket_cmd(
        'gvotes', {'down': gvotes[0], 'up': gvotes[1]}, channel="city__%s" % us.city.id)
    return gvotes


def qiwi_notify_reply():
    return HttpResponse("""<?xml version="1.0"?>
        <result><result_code>0</result_code>
        </result>
        """, content_type="text/xml")


@csrf_exempt
def qiwi_notify(request):
    import base64
    auth = request.META.get('HTTP_AUTHORIZATION', "").split()
    if len(auth) == 2 and auth[0].lower() == "basic":
        uname, passwd = base64.b64decode(auth[1]).split(':')
        if uname != str(settings.QIWI_PROJECT_ID) or passwd != settings.QIWI_PULL_PASS:
            response = HttpResponse("")
            response.status_code = 401
            return response
    else:
        log_message("qiwi_notify password incorrect", ttype="qiwi")
        return HttpResponse("wtf?")

    command = request.POST.get("command")  # should be 'bill'
    bill_id = request.POST.get("bill_id")
    status = request.POST.get("status")
    phone = request.POST.get("user").replace("tel:", '')

    if status == "expired":
        return qiwi_notify_reply()
    pay = Payment.objects.get(id=int(bill_id))
    us = pay.get_user()

    if status == "paid":
        if pay.paid:
            return qiwi_notify_reply()

        pay.paid = True
        pay.paid_on = datetime.datetime.now()
        pay.save()

        if pay.key == "standard":
            DAYS = 183
        elif pay.key == "premium":
            DAYS = 63

        transes = Transaction.objects.filter(
            user=us, key=pay.key, end_time__gte=pay.paid_on).order_by('-end_time')
        if transes:
            trans = transes[0]
            end_time = trans.end_time + datetime.timedelta(days=DAYS)
        else:
            end_time = pay.paid_on + datetime.timedelta(days=DAYS)
        trans = Transaction.objects.create(
            user=us, key=pay.key, value=DAYS, fiat=pay.amount, end_time=end_time, phone=phone)
        premium_activate(us, key=pay.key)

    log_message("%s %s, %s" % (bill_id, status, phone),
                ttype="qiwi", user=us, city=us.city)
    return qiwi_notify_reply()


def handle_uploaded_file(request, us):
    # запись файла локально
    f = request.FILES['photo']
    f_name = "%s/si/%s" % (
        settings.MEDIA_ROOT, us.id)
    with open(f_name, 'wb+') as destination:
        for chunk in f.chunks():
            destination.write(chunk)

    # преобразования
    file_name, file_path = user_photo_scaler(us)
    os.remove(f_name) # удаляем принятый файл

    return file_name


def makeit_icon(img, height):
    """Makes transport icon from any image."""

    img = img.convert("RGBA")
    src_width, src_height = img.size
    ratio = float(src_height) / height
    width = src_width / ratio

    datas = img.getdata()
    newData = []
    img.putdata(datas)
    img.thumbnail((width, height), Image.ANTIALIAS)

    if width > height:
        box = (0, 0, height, height)
        img = img.crop(box)

    return img


def user_photo_scaler(us):
    f_name = "%s/si/%s" % (
        settings.MEDIA_ROOT, us.id)
    try:
        with open(f_name, 'rb') as f:
            photo_hash = hashlib.sha224(f.read()).hexdigest()
    except:
        return False
    img = Image.open(f_name)
    sip = f'{settings.PROJECT_DIR}/bustime/static/img/si'
    for wh in [76]:
        ex = ""
        f_name = "%s_%s%s.png" % (us.id, photo_hash[:5], ex)
        img1 = makeit_icon(img, wh)
        f = open("%s/%s" % (sip, f_name), 'wb')
        img1.save(f, 'PNG')
        f.close()
        try:
            os.symlink("%s/%s" % (sip, f_name), "%s/img/si/%s" %
                       (settings.STATIC_ROOT, f_name))
        except:
            pass

    return f_name, sip


def city_admin(request, city_name=None):
    place = get_object_or_404(Place, slug=city_name)
    us = get_user_settings(request)
    transaction = get_transaction(us)
    now = place.now
    error_msg = ''

    us.city = place

    if not request.user.is_authenticated:
        return HttpResponse("access denied")

    groups = list(request.user.groups.values_list('name', flat=True))

    if 'data_provider' in groups:
        # ekaterinburg_dp_admin
        name = request.user.username.split("_dp")[0]
        place_dp = get_object_or_404(Place, slug=name)

        if place != place_dp:
            return HttpResponse("Your are the admin of the other city: %s" % place_dp.slug)

        log_counters = rcache_get('log_counters_%s' % place.id, {})
        nearest = log_counters.get('nearest', 0)

        if request.POST:
            flash = request.POST.get("dp_flash")
            flash_del = request.POST.get("flash_del", False)
            news = request.POST.get("dp_news")
            news_del = request.POST.get("news_del", False)
            src = 'c' + str(place.id) + '.py'
            data_source = DataSource.objects.get(src=src)

            if flash:
                data_source.block_info = flash
                data_source.save(update_fields=['block_info'])
            if flash_del != False:
                data_source.block_info = None
                data_source.save(update_fields=['block_info'])
            if news:
                cn = CityNews.objects.create(
                    body=news, author=request.user, news_type=1, place=place)

        ctx = {"us": us,
               "place": place,
               "noga": True,
               "now": now,
               "nearest": nearest}
        return arender(request, "city_provider.html", ctx)

    if request.POST and request.FILES.get('ar'):
        v = get_setting('app_driver_test')
        f = request.FILES['ar']
        with open('%s/static/other/app/bustime-fl-%s.apk' % (settings.PROJECT_ROOT, v+1), 'wb+') as destination:
            for chunk in f.chunks():
                destination.write(chunk)
        #subprocess.call(["/bustime/bustime/4collect_static.sh"])
        s = Settings.objects.get(key='app_driver_test')
        s.value_int = s.value_int + 1
        s.save()

    if request.POST and request.user.is_superuser and request.POST.get('premium_us_id'):
        us_id = request.POST.get('premium_us_id')
        vip_name = request.POST.get('premium_vip_name')
        now = datetime.datetime.now()
        us = UserSettings.objects.get(id=us_id)
        DAYS = 365
        end_time = now + datetime.timedelta(days=DAYS)
        Transaction.objects.create(user=us, key="premium", value=DAYS,
                                   fiat=0, comment="", end_time=end_time,
                                   phone="", vip=True, vip_name=vip_name)
        premium_activate(us, key="premium")
        wsocket_cmd('reload', {}, us_id=us.id)
        return HttpResponseRedirect("./")

    adt = get_setting('app_driver_test')

    # проверка наличия файла gtfs-ID.py (ID города)
    gtfs_py_file = {
        'path': "/bustime/bustime/utils/gtfs-%d.py" % place.id,
        'exists': False,
        'modified': None
    }
    if os.path.isfile(gtfs_py_file['path']):
        gtfs_py_file['exists'] = True
        gtfs_py_file['modified'] = os.path.getmtime(gtfs_py_file['path'])

    # проверка наличия файла route_auto.py
    route_auto_py_file = {
        'path': "/bustime/bustime/utils/route_auto.py",
        'exists': False,
        'modified': None
    }
    if os.path.isfile(route_auto_py_file['path']):
        route_auto_py_file['exists'] = True
        route_auto_py_file['modified'] = os.path.getmtime(
            route_auto_py_file['path'])

    # проверка наличия файла gtfs-ID.log (ID города)
    gtfs_log_file = {
        'path': "%s/static/logs/gtfs-%d.log" % (settings.PROJECT_DIR, place.id),
        'exists': False,
        'modified': None
    }
    if os.path.isfile(gtfs_log_file['path']):
        gtfs_log_file['exists'] = True
        gtfs_log_file['modified'] = os.path.getmtime(gtfs_log_file['path'])

    # проверка наличия файла route_auto-ID.log (ID города)
    route_auto_log_file = {
        'path': "%s/static/logs/route_auto-%d.log" % (settings.PROJECT_DIR, place.id),
        'exists': False,
        'modified': None
    }
    if os.path.isfile(route_auto_log_file['path']):
        route_auto_log_file['exists'] = True
        route_auto_log_file['modified'] = os.path.getmtime(
            route_auto_log_file['path'])

    # проверка загрузки маршрутов
    load_bus_log_file = {
        'path': "%s/static/logs/load_bus-%d.log" % (settings.PROJECT_DIR, place.id),
        'exists': False,
        'modified': None
    }
    if os.path.isfile(load_bus_log_file['path']):
        load_bus_log_file['exists'] = True
        load_bus_log_file['modified'] = os.path.getmtime(
            load_bus_log_file['path'])

    # проверка наличия файла update_js-%d.log (ID города)
    update_js_log_file = {
        'path': "%s/static/logs/update_js-%d.log" % (settings.PROJECT_DIR, place.id),
        'exists': False,
        'modified': None
    }
    if os.path.isfile(update_js_log_file['path']):
        update_js_log_file['exists'] = True
        update_js_log_file['modified'] = os.path.getmtime(
            update_js_log_file['path'])

    # проверка наличия файла update_mobile-%d.log (ID города)
    update_mobile_log_file = {
        'path': "%s/static/logs/update_mobile-%d.log" % (settings.PROJECT_DIR, place.id),
        'exists': False,
        'modified': None
    }
    if os.path.isfile(update_mobile_log_file['path']):
        update_mobile_log_file['exists'] = True
        update_mobile_log_file['modified'] = os.path.getmtime(
            update_mobile_log_file['path'])

    # проверка файла JS для города
    # todo v8
    city_js_file = {
        'path': "%s/../bustime/static/js/city-%s-%s.js" % (settings.STATIC_ROOT, place.id, place.rev),
        'exists': False,
        'modified': None,
        'class': '',
        'message': ''
    }
    if os.path.isfile(city_js_file['path']):
        city_js_file['exists'] = True
        city_js_file['modified'] = os.path.getmtime(city_js_file['path'])

    # проверка файла мобильных для города
    city_mobile_file = {
        'path': "%s/bustime/static/other/db/v7/%d.dump.diff.bz2" % (settings.PROJECT_DIR, place.id),
        'dump_path': "%s/bustime/static/other/db/v7/%d.dump.bz2" % (settings.PROJECT_DIR, place.id),
        'exists': False,
        'modified': None,
        'class': '',
        'message': ''
    }
    city_mobile_file['exists'] = os.path.isfile(city_mobile_file['path']) or os.path.isfile(city_mobile_file['dump_path'])
    if os.path.isfile(city_mobile_file['path']):
        city_mobile_file['modified'] = os.path.getmtime(city_mobile_file['path'])
    elif os.path.isfile(city_mobile_file['dump_path']):
        city_mobile_file['modified'] = os.path.getmtime(city_mobile_file['dump_path'])

    # определяем мерцания кнопок
    # Обновить БД сайта
    if not city_js_file['exists']:
        city_js_file['class'] = 'blink_me'
        city_js_file['message'] = 'JS-файлов нет'
    elif gtfs_log_file['exists'] and gtfs_log_file['modified'] > city_js_file['modified']:
        city_js_file['class'] = 'blink_me'
        t1 = time.strftime('%d.%m.%y %H:%M:%S', time.localtime(gtfs_log_file['modified']))
        t2 = time.strftime('%d.%m.%y %H:%M:%S', time.localtime(city_js_file['modified']))
        city_js_file['message'] = 'Маршруты обновлены %s, дата JS-файлов %s' % (t1, t2)
    elif load_bus_log_file['exists'] and load_bus_log_file['modified'] > city_js_file['modified']:
        city_js_file['class'] = 'blink_me'
        t1 = time.strftime('%d.%m.%y %H:%M:%S', time.localtime(load_bus_log_file['modified']))
        t2 = time.strftime('%d.%m.%y %H:%M:%S', time.localtime(city_js_file['modified']))
        city_js_file['message'] = 'Маршруты добавлены %s, дата JS-файлов %s' % (t1, t2)

    # Обновить БД приложений
    if not city_mobile_file['exists']:
        city_mobile_file['class'] = 'blink_me'
        city_mobile_file['message'] = 'БД мобильных нет'
    elif city_js_file['exists'] and city_js_file['modified'] > city_mobile_file['modified']:
        city_mobile_file['class'] = 'blink_me'
        t1 = time.strftime('%d.%m.%y %H:%M:%S', time.localtime(city_js_file['modified']))
        t2 = time.strftime('%d.%m.%y %H:%M:%S', time.localtime(city_mobile_file['modified']))
        city_mobile_file['message'] = 'Дата JS-файлов %s > дата мобильной БД %s' % (t1, t2)

    # Госномера, Госномера (авто), обрабатываются ajax_get_gosnums_admin
    gosnums = []
    gosnums_auto = []

    # Прямая отправка GPS и счетчик bustime
    gps_send_raw_list = []
    gevents = REDIS.smembers('gevents_%s' % us.place.id)
    if gevents:
        gevents = ["gevent_%s" % x.decode('utf8') for x in gevents]
        gevents = rcache_mget(gevents)

    for v in gevents:
        if not v:
            continue
        v['us'] = us_get(v['custom_src'])
        v['transaction'] = None
        v['event'] = rcache_get("event_%s" % v['uniqueid'])
        v['history'] = len(v.get('history', []))
        v['bus'] = bus_get(v['bus'])
        v['peer_id'] = REDIS.get("us_%s_peer" % v['custom_src'])
        if v['peer_id']:
            v['peer_id'] = v['peer_id'].decode('utf8')
        v['odometer'] = v.get('odometer', 0)/1000
        gps_send_raw_list.append(v)
    gps_send_raw_list = sorted(gps_send_raw_list, key=lambda x: x.timestamp, reverse=True)
    # /Прямая отправка GPS и счетчик bustime

    # revisions = Revision.objects.filter(user__isnull=False).order_by("-date_created")[:20]
    revisions = None

    # счетчики событий
    ecnt = []
    # 0 uevents
    uevents = rcache_get("uevents_%s" % place.id, {})
    ecnt.append(len(uevents))
    # 1 yproto
    ecnt.append(len(REDIS.smembers('upload_events_%s' % place.id)))
    # 2 nimbus
    cc_key_nimbus = "uevents_%s_raw" % place.id
    n = REDIS.get(cc_key_nimbus)
    if n:
        n = json.loads(n.decode('utf8'))
    else:
        n = []
    ecnt.append(len(n))
    # 3 glonassd
    g_cnt = 0
    ports = list(Glonassd.objects.filter(city__id=place.id).values_list('port', flat=True))
    for p in ports:
        g_cnt += len( REDIS.smembers('gd_port__' + str(p)) )
    ecnt.append(g_cnt)
    # 4 tevents
    tevents = rcache_get("tevents_%s" % place.id, {})
    ecnt.append(len(tevents))
    # todo - remove uevents and others after full transition

    # 5 events
    events = REDIS.smembers("events")
    ecnt.append(len(events))
    # 6 events
    pevents = REDIS.smembers("place__%s" % place.id)
    ecnt.append(len(pevents))
    # /счетчики событий

    uids = list([x.decode('utf8') for x in pevents])
    to_get = [f'event_{uid}' for uid in uids]
    sources_cnt = defaultdict(int)
    for e in rcache_mget(to_get):
        if not e or not e['channel'] or not e['src']: continue
        cc_key = "%s*%s" % (e['channel'], e['src'])
        sources_cnt[cc_key] += 1
    sources = []
    for k, v in sources_cnt.items():
        ch, src = k.split("*")
        sources.append([ch, src, v])

    #сообщение для всех городов
    try:
        message_for_all = Settings.objects.get(key='message_for_all').value
    except:
        message_for_all = None

    ctx = {
        'us': us,
        "place": place,
        "adt": adt,
        "noga": True,
        "now": now,
        'gtfs_py_file': gtfs_py_file,
        'route_auto_py_file': route_auto_py_file,
        'gtfs_log_file': gtfs_log_file,
        'route_auto_log_file': route_auto_log_file,
        'load_bus_log_file': load_bus_log_file,
        'city_js_file': city_js_file,
        'city_mobile_file': city_mobile_file,
        'update_js_log_file': update_js_log_file,
        'update_mobile_log_file': update_mobile_log_file,
        'error_msg': error_msg,
        "gosnums": gosnums,
        "gosnums_auto": gosnums_auto,
        "gps_send_raw_list": gps_send_raw_list,
        "revisions": revisions,
        "ecnt": ecnt,
        "message_for_all": message_for_all,
        "sources": sources
    }

    return arender(request, "city_admin.html", ctx)
# def city_admin(request, city_name=None)

def tests_rpc(request, city_name=None):
    us = get_user_settings(request)
    place = Place.objects.filter(slug=city_name).first()
    buses = Bus.objects.filter(places=place).order_by('ttype', 'name')
    prov_id_list = set(
        buses.filter(provider__isnull=False).values_list('provider', flat=True)
    )
    provs = BusProvider.objects.filter(id__in=list(prov_id_list)).order_by("name")
    vehs = Vehicle.objects.filter(provider__in=provs).order_by('gosnum')

    city = get_object_or_404(City, slug=city_name)
    allevents = rcache_get("allevents_%s" % city.id, {})
    ctx = {
        'us': us,
        'us_': model_to_dict(us),
        'place': place,
        "city": city,
        "city_": model_to_dict(city),
        'buses': buses,
        'vehs': vehs,
        'provs': provs,
        "allevents": allevents,
        "tile_server": settings.TILE_SERVER,
        "nominatim_server": settings.NOMINATIM_SERVER,
        "gh_server": settings.GH_SERVER,
    }
    return arender(request, "tests_rpc.html", ctx)
# tests_rpc

@csrf_exempt
def ajax_get_supervisor_status(request):
    cmd = ["sudo", "/usr/bin/supervisorctl", "status"]
    super_status = subprocess.check_output(cmd).decode("utf8")
    return HttpResponse(super_status)
# ajax_get_supervisor_status

@csrf_exempt
def ajax_get_gosnums_admin(request):
    city_id = request.POST.get('city_id', None)

    cc_key = 'city_admin_response_%s' % city_id
    response = rcache_get(cc_key, {'error': '', 'gosnums': [], 'gosnums_auto': []})
    if len(response['gosnums']) == 0 or len(response['error']) > 0:
        response['error'] = ''
        try:
            allevents = rcache_get("allevents_%s" % city_id, {})
            cursor = connections['default'].cursor()
            cursor.execute('''WITH ver AS (
               SELECT object_id, MAX(revision_id) AS revision_id
               FROM reversion_version
               WHERE object_id IN  (SELECT uniqueid FROM bustime_vehicle WHERE city_id = %s)
               GROUP BY object_id
            )
            SELECT
               veh.uniqueid, veh.gosnum, veh.created_auto,
               to_char(veh.created_date, 'dd.mm.yy HH24:MI:SS') AS created_date,
               veh.uid_provider, veh.model, veh.bortnum,
               to_char(rev.date_created, 'dd.mm.yy HH24:MI:SS') AS date_created,
               rev.user_id, rev."comment",
               bp.name AS provider_name
            FROM bustime_vehicle veh
            LEFT JOIN ver ON ver.object_id = veh.uniqueid
            LEFT JOIN reversion_revision rev ON rev.id = ver.revision_id
            LEFT JOIN bustime_busprovider bp ON bp.id = veh.provider_id
            WHERE veh.city_id = %s
            ORDER BY veh.created_date DESC''', [city_id, city_id])

            # convert raw records to array of dict {field_name: field_value...}
            gns = [dict((cursor.description[i][0], value)
                        for i, value in enumerate(row)) for row in cursor.fetchall()]
            cursor.close()
            for g in gns:
                ev = allevents.get("event_%s_%s" % (city_id, g['uniqueid']))

                if g['created_auto']:
                    # Госномера (авто)
                    g['bus'] = {'id': ev.bus.id, 'name': ev.bus.name} if ev and ev.bus else None
                    g['last_point_update'] = ev.last_point_update.strftime("%d.%m.%y %H:%M:%S") if ev and ev.last_point_update else None
                    response['gosnums_auto'].append(g)
                else:
                    # Госномера
                    response['gosnums'].append({'uniqueid': g['uniqueid'],
                                'gosnum': g['gosnum'],
                                'bortnum': g['bortnum'],
                                'model': g['model'],
                                'created_date': g['date_created'] if g['date_created'] else g['created_date'],
                                'uid_provider': g['uid_provider'],
                                'user': g['user_id'],
                                'bus': {'id': ev.bus.id, 'name': ev.bus.name} if ev and ev.bus else None,
                                'last_point_update': ev.last_point_update.strftime("%d.%m.%y %H:%M:%S") if ev and ev.last_point_update else None})
            # for g in gns
            rcache_set(cc_key, response, 60*60)
            json.dumps(response)
        except Exception as ex:
            response['error'] = str(ex)

    return HttpResponse(json.dumps(response))
# def ajax_get_gosnums_admin(request)


def admin_vehicle(request):
    us = get_user_settings(request)
    uniqueid = request.GET.get('u', request.GET.get('uniqueid'))
    gosnum = request.GET.get('g', request.GET.get('gosnum'))
    city_slug = request.GET.get('s', request.GET.get(
        'slug', request.GET.get('city_slug')))
    city = vehicle = gosnum_vehicles = mapping = bus_uevent = bus_gevent = distance = city_vehicles = None
    vehicle_versions = None

    if uniqueid:
        veh = Vehicle.objects.filter(
            Q(uniqueid=uniqueid) | Q(uid_provider=uniqueid))
        if len(veh) > 0:
            vehicle = veh[0]
            # request.GET.get('uniqueid') = vehicle.uid_provider
            if uniqueid != vehicle.uniqueid:
                uniqueid = vehicle.uniqueid
            gosnum = vehicle.gosnum
            gosnum_vehicles = Vehicle.objects.filter(
                gosnum=gosnum).order_by('gosnum', 'created_date')
    elif gosnum:
        gosnum_vehicles = Vehicle.objects.filter(
            gosnum=gosnum).order_by('gosnum', 'created_date')
        if len(gosnum_vehicles) > 0:
            vehicle = gosnum_vehicles[0]
            if vehicle:
                uniqueid = vehicle.uniqueid
        else:
            veh = Mapping.objects.filter(gosnum=gosnum)
            if len(veh) > 0:
                bus = None if not veh[0].bus else veh[0].bus
                vehicle = Vehicle()
                vehicle.uniqueid = veh[0].xeno_id,
                vehicle.gosnum = veh[0].gosnum,
                vehicle.city = veh[0].city
                vehicle.ttype = bus.ttype if bus else None
                uniqueid = vehicle.uniqueid
    elif city_slug:
        city = get_object_or_404(City, slug=city_slug)
        city_vehicles = Vehicle.objects.filter(
            city=city).order_by('gosnum', 'created_date')
        if len(city_vehicles) > 0:
            vehicle = city_vehicles[0]
            uniqueid = vehicle.uniqueid
            gosnum = vehicle.gosnum
            gosnum_vehicles = Vehicle.objects.filter(
                gosnum=gosnum).order_by('gosnum', 'created_date')

    if not city:
        if vehicle:
            city = vehicle.city
        elif us.city:
            city = us.city
    # if not city

    edit_level = 0
    auth = request.user.is_authenticated  # юзер залогинен?
    if auth:
        # проверяем группы юзера
        if us.premium and us.show_gosnum:
            edit_level = 2  # must by >= max level so is admin
        elif request.user.id in [12]:   # locman, где остальные хз
            edit_level = 2
        elif request.user.is_superuser:
            edit_level = 2
        else:
            """
            это проверка по группам пользователей django
            u = User.objects.get(id=request.user.id)
            readonly = not u.groups.filter(name=city.slug).exists()  # группа = sity.slug
            readonly = (not readonly) and (not u.groups.filter(name='disp').exists())
            """
            # это проверка по группам пользователей города
            if city:
                if request.user.id in [user.id for user in city.dispatchers.all()]:
                    edit_level += 1
                if request.user.id in [user.id for user in city.editors.all()]:
                    edit_level += 1
    # if auth

    buses = buses_get(city) if city else []
    uevents = rcache_get("uevents_%s" % city.id, {}) if city else {}
    gevents = REDIS.smembers('gevents_%s' % city.id) if city else {}
    gevents = set([_.decode('utf8') for _ in gevents])
    allevents = rcache_get("allevents_%s" % city.id, {}) if city else {}
    vehicles_info = vehicles_cache(city) if city else {}

    if not city_vehicles:
        city_vehicles = Vehicle.objects.filter(
            city=city).order_by('gosnum', 'created_date')

    if uniqueid:
        # vehicle_info
        vehicle_info = vehicles_info.get(uniqueid) if vehicles_info else None
        # event in uevents
        uevent = uevents.get(uniqueid) if uevents else None
        if uevent and uevent.bus:
            if type(uevent.bus) is int:
                bus_uevent = bus_get(uevent.bus)
            else:
                bus_uevent = bus_get(uevent.bus.id)
        # gevent
        gevents:List[Optional[dict]] = rcache_mget("gevent_%s" % uniqueid)
        for gevent in gevents:
            if gevent and 'bus' in gevent:
                if type(gevent['bus']) is int:
                    bus_gevent = bus_get(gevent['bus'])
        # mapping & versions
        if vehicle:
            mapping = Mapping.objects.filter(Q(city=city) & Q(
                xeno_id=vehicle.uniqueid) | Q(xeno_id=vehicle.uid_provider))
            vehicle_versions = Version.objects.get_for_object(vehicle)
        else:
            mapping = Mapping.objects.filter(city=city, xeno_id=uniqueid)
        mapping = mapping[0] if len(mapping) > 0 else None
        # event in allevents
        allevent = allevents.get("event_%s_%s" % (
            city.id, uniqueid)) if allevents else None
        if allevent:
            distance = int(distance_meters(allevent.x, allevent.y,
                                           allevent.x_prev, allevent.y_prev) * 1.1)

        # stored statuses
        day = datetime.datetime.now()
        # список ID маршрутов города
        city_ids = Bus.objects.filter(city=city).values_list('id', flat=True)

        statuses = VehicleStatus.objects.filter(city_time__year=day.year,
                                                city_time__month=day.month,
                                                city_time__day=day.day,
                                                city=city.id,
                                                uniqueid=uniqueid).order_by('-city_time')
        # stored events
        sevents = Uevent.objects.using('bstore').filter(bus_id__in=list(city_ids),
                                                        uniqueid=uniqueid,
                                                        timestamp__date=day.date()).order_by('-timestamp')[:20]
    # if uniqueid
    else:
        uevent = None
        gevent = None
        vehicle_info = None
        allevent = None
        statuses = None
        sevents = None

    cities = City.objects.filter(active=True, available=True).order_by('name')

    ctx = {'us': us,
           "edit_level": edit_level,
           "city": city,
           "cities": cities,
           "buses": buses,
           "uniqueid": uniqueid,
           "gosnum": gosnum,
           "city_vehicles": city_vehicles,
           "vehicle": vehicle,
           "vehicle_versions": vehicle_versions,
           "uevent": uevent,
           "bus_uevent": bus_uevent,
           "gevent": gevent,
           "bus_gevent": bus_gevent,
           "mapping": mapping,
           "vehicle_info": vehicle_info,
           "allevent": allevent,
           "gosnum_vehicles": gosnum_vehicles,
           "statuses": statuses,
           "sevents": sevents,
           "distance": distance,
           "time_server": int(datetime.datetime.now().strftime('%s')),
           "time_city": int(city.now.strftime('%s'))
           }
    return arender(request, "admin_vehicle.html", ctx)
# def admin_vehicle


def city_mapping(request, city_name=None):
    city = get_object_or_404(City, slug=city_name)
    us = get_user_settings(request)
    buses = buses_get(city)
    mapping = mapping_get(city)

    ctx = {'us': us, "city": city, "buses": buses,
           "mapping": mapping, "noga": True}
    return arender(request, "city_mapping.html", ctx)


def city_mapping_table(request, city_name=None):
    place = get_object_or_404(Place, slug=city_name)
    us = get_user_settings(request)
    #us = UserSettings.objects.filter(user_id=8899).order_by('-ctime').first()
    buses = buses_get(place)
    # чтобы строки не прыгали в таблице и нумерация сохранялась
    mapping = mapping_get(place, force=True).order_by("xeno_id")

    edit_level = 0
    auth = request.user.is_authenticated  # юзер залогинен?
    if auth:
        # проверяем группы юзера
        if us.premium and us.show_gosnum:
            edit_level = 2  # must by >= max level so is admin
        if request.user.is_superuser:
            edit_level = 2
        else:
            """
            это проверка по группам пользователей django
            u = User.objects.get(id=request.user.id)
            readonly = not u.groups.filter(name=city.slug).exists()  # группа = sity.slug
            readonly = (not readonly) and (not u.groups.filter(name='disp').exists())
            """
            # это проверка по группам пользователей города
            if us.user.id in [user.id for user in place.dispatchers.all()]:
                edit_level += 1
            if us.user.id in [user.id for user in place.editors.all()]:
                edit_level += 1
    # if auth
    ctx = {'us': us, "city": place, "buses": buses, "mapping": mapping,
           "edit_level": edit_level}

    return arender(request, "city_mapping_table.html", ctx)


def plan_export_xml(city, date, provider_id):
    s = '<?xml version="1.0" encoding="UTF-8"?>'
    plans = Plan.objects.filter(
        bus__city=city, date=date, operator=provider_id)
    for plan in plans:
        s += """
<transport>
<date>%s</date>
<route_type>%s</route_type>
<route_name>%s</route_name>
<operator>%s</operator>
<schedule>%s</schedule>
<vehicle>%s</vehicle>
</transport>""" % (date, plan.bus.ttype_slug(), plan.bus.name, provider_id, plan.gra, plan.xeno_id)
    filename = '%s.xml' % provider_id
    f = open('/tmp/%s' % filename, 'w')
    f.write(s.encode('utf8'))
    f.close()
    return filename


def plan(request, city_name=None, provider_id=None):
    class A:
        pass
    city = get_object_or_404(City, slug=city_name)
    us = get_user_settings(request)
    buses = buses_get(city)
    now = city.now

    # берём операторов - предприятия
    cc_key = "plan_%s_operators" % city.id
    orgs_dict = rcache_get(cc_key, {})
    if not orgs_dict:
        ftp = FTP('80.80.98.215')
        ftp.login('atplist', 'he723&9k@mz')
        output = StringIO.StringIO()
        ftp.retrbinary('RETR operators.txt', output.write)
        output.seek(0)
        orgs_dict = {}
        for op in output.readlines():
            # id_, name = op.decode('utf8').strip().split(",")
            id_, name = op.strip().split(",")
            if not id_[0].isdigit():
                id_ = id_[1:]
            orgs_dict[int(id_)] = name
        rcache_set(cc_key, orgs_dict, 60*60*1)
    cc_key = "plan_%s_vehicles" % city.id
    vehicles = rcache_get(cc_key, {})
    if not vehicles:
        ftp = FTP('80.80.98.215')
        ftp.login('atplist', 'he723&9k@mz')
        output = StringIO.StringIO()
        ftp.retrbinary('RETR vehicles.txt', output.write)
        output.seek(0)
        for op in output.readlines():
            id_, garage_num, gosnum = op.strip().split(",")
            if not id_[0].isdigit():
                id_ = id_[1:]
            pid = int(id_)
            data = vehicles.get(pid, [])
            data.append((pid, garage_num, gosnum))
            data = sorted(data, key=lambda p: p[1])
            vehicles[pid] = data
        rcache_set(cc_key, vehicles, 60*60*1)

    is_del = request.GET.get("del")
    if is_del:
        plan = Plan.objects.get(id=int(is_del))
        plan.delete()
        return HttpResponseRedirect("./")

    ctx = {'us': us, "city": city, "noga": True, 'now': now}

    if request.POST:
        is_send = request.POST.get("send")
        if is_send:
            ftp = FTP('80.80.98.215')
            ftp.login('schedules', 'jde*923ekr#')
            filename = plan_export_xml(city, city.now.date(), provider_id)
            myfile = open('/tmp/%s' % filename, 'r')
            ftp.storlines('STOR ' + filename, myfile)
            myfile.close()
            ctx['msg'] = u'План-наряд успешно отправлен в ЦУПП, дата: %s' % city.now.date()

        is_down = request.POST.get("download")
        if is_down:
            pass

        if request.POST.get("add"):
            bus_id = request.POST.get("bus_id")
            gra_range = request.POST.get("gra_range", "1")
            gra_range = int(gra_range)
            for gra in range(1, gra_range+1):
                Plan.objects.create(date=city.now.date(),
                                    bus_id=bus_id,
                                    operator=provider_id,
                                    gra=gra)
            return HttpResponseRedirect("./")

    if provider_id:
        provider_id = int(provider_id)
        ctx['org'] = orgs_dict[provider_id]
        ctx['org_id'] = provider_id
        vehicles = vehicles.get(provider_id, [])
        ctx['vehicles'] = vehicles
        ctx['buses'] = buses
        plans = Plan.objects.filter(date=city.now.date(),
                                    operator=provider_id).order_by("bus__order", "gra")
        if not plans:
            # recreate yesterday basis
            yday = city.now - datetime.timedelta(days=1)
            buses_id = Plan.objects.filter(
                date=yday, operator=76).values_list('bus', flat=True)
            for bus_id in buses_id:
                Plan.objects.create(date=city.now.date(),
                                    bus_id=bus_id,
                                    operator=provider_id)
            plans = Plan.objects.filter(date=city.now.date(),
                                        operator=provider_id).order_by("bus__order", "gra")
        if plans:
            ctx['plans'] = plans
            ctx['cplans'] = chunks(plans, int(math.ceil(len(plans)/2.0)))

        ctx['gra_range'] = list(range(1, 50))
        return arender(request, "plan.html", ctx)
    else:
        orgs = []
        for k, v in orgs_dict.items():
            a = A()
            a.id, a.name = k, v
            orgs.append(a)
        orgs = sorted(orgs, key=lambda p: p.name)
        corgs = chunks(orgs, int(math.ceil(len(orgs)/4.0)))
        ctx['corgs'] = corgs
        return arender(request, "plan_select.html", ctx)


# @cache_page(60 * 60 * 3)
def stops(request, city_name):
    us = get_user_settings(request)
    place = get_object_or_404(Place, slug=city_name)
    us.city = place
    ctx = {'us': us, "place": place}
    bid = request.GET.get('id')
    if bid:
        bs = get_object_or_404(NBusStop, id=bid)
        return HttpResponseRedirect("./%s/" % bs.slug)

    cc_key = "stops__%s_%s" % (place.id, getattr(us.user, 'is_staff', False))
    stops = rcache_get(cc_key)
    if not stops:
        stops = list(NBusStop.objects.filter(route__bus__places=place).order_by("name").distinct("name"))
        last_letter = ""
        for stop in stops:
            if not stop.slug:
                continue
            if stop.slug[0].upper() != last_letter:
                stop.divider = True
                last_letter = stop.slug[0].upper()

        if len(stops):
            stops = list(chunks(stops, int(math.ceil(len(stops)/4.0))))

        rcache_set(cc_key, stops, 60*60)
    # if not stops

    ctx["sstops"] = stops
    return arender(request, "stops.html", ctx)


def stop(request, city_name, stop_slug=None):
    us = get_user_settings(request)
    transaction = get_transaction(us)
    place = get_object_or_404(Place, slug=city_name)
    ctx = {'us': us, "place": place, 'transaction': transaction}

    cc_key = "stop__%s_%s" % (place.id, stop_slug)
    stops = rcache_get(cc_key)
    if stops == None:
        stops = list(NBusStop.objects.filter(route__bus__places=place, slug=stop_slug).distinct('id').order_by('id'))
        rcache_set(cc_key, stops, 60*60)
    if stops == []:
        return HttpResponsePermanentRedirect("/%s/stop/" % place.slug)

    cc_key = "stop_buses__%s_%s" % (place.id, stop_slug)
    buses = rcache_get(cc_key)
    if not buses:
        buses = list(Bus.objects.filter(active=True, route__busstop__in=stops).distinct().order_by("ttype", "name"))
        rcache_set(cc_key, buses, 60*60)

    pipe = REDIS.pipeline()
    bdata_mode3 = {}
    stops_id = set()
    for s in stops:
        stops_id.add(s.id)
        pipe.hgetall(f"stop__{s.id}")

    for stop_id, items in zip(stops_id, pipe.execute()):
        bdata_mode3[stop_id] = [pickle.loads(v) for v in items.values()]
        # = [{'bid': 546, 'uid': 'G1pCQVJP', 'n': 'ТВ7', 't': datetime.datetime(2024, 4, 24, 19, 14), 't2': datetime.datetime(2024, 4, 24, 19, 14)},...]

    stop = None
    for stop in stops:
        preds = bdata_mode3.get(stop.id, [])
        preds = sorted(preds, key=lambda p: p.get('t'))
        nbdata = []
        for pred in preds:
            bus = bus_get(pred['bid'])
            if bus:
                pq = copy.copy(pred)
                pq['t'] = "%02d:%02d" % (pred['t'].hour, pred['t'].minute)
                pq['bus_url'] = bus.get_absolute_url()
                nbdata.append(pq)
        stop.bdata = nbdata

    ub = stop.unistop
    icon = ub.icon if ub else None

    ctx["ustop"] = ub
    ctx["icon"] = icon
    ctx['now'] = datetime.datetime.now(tz=stop.timezone).replace(tzinfo=None)
    ctx["stop"] = stop
    ctx["stops"] = stops
    ctx["buses"] = buses
    ctx["ads_show"] = detect_ads_show(request, us)

    return arender(request, "stop.html", ctx)


def stop_info_turbo(request, city_name, stop_id, tmc=None):
    tmpl = None
    mode = request.GET.get('mode')
    g_stop_id = request.GET.get("stop_id")
    if g_stop_id:
        try:
            stop_id = int(g_stop_id)
        except:
            if g_stop_id == "Tablo1":
                stop_id = 20619
            elif g_stop_id == "Tablo2":
                stop_id = 20623
            else:
                raise Http404
        mode = "dt"
        stop = get_object_or_404(NBusStop, id=stop_id)
        pls = Place.objects.raw("""SELECT bp.id FROM bustime_place bp 
            INNER JOIN bustime_placearea bpa ON (bp.osm_area_id = bpa.osm_id AND bp.osm_area_type = bpa.osm_type) 
            WHERE ST_Contains(bpa.geometry, ST_SetSRID(ST_GeomFromWkb(%s), 4326)) LIMIT 1""", [stop.point.wkb,])
        try:
            pa = pls[0]
        except:
            raise Http404("No Place matches the given stop [%s]." % stop_id)
    else:
        stop = get_object_or_404(NBusStop, id=stop_id)
        pa = get_object_or_404(Place, slug=city_name)

    ctx = {"city": pa, "stop": stop, "noga": True}
    if request.GET.get("a") is not None:
        stops = [7685, 7657, 8580, 13763, 13764]
        next_step = int(request.GET.get("a")) + 1
        stop_id = stops[next_step % 5]
        stop = get_object_or_404(NBusStop, id=stop_id)
        ctx["stop"] = stop
        ctx['set_map_center'] = request.session.get(
            'stop_%s_set_map_center' % stop.id)
        ctx['next_step'] = next_step
        tmpl = "stop_info_3.html"

    bdata_mode3 = ajax_stop_id_f([stop_id], raw=True)
    filt = filter(lambda item: item['nbid'] == int(stop_id), bdata_mode3.get('stops', []))
    preds = next(filt, None) or {}
    preds = preds.get('data', [])
    preds = sorted(preds, key=lambda p: p.get('tt'))

    stop.bdata = preds
    ctx['now'] = pa.now
    ctx['tz_offset'] = int(time.mktime(pa.now.timetuple()) - time.mktime(datetime.datetime.utcnow().timetuple()))
    ctx['avg_temp'] = avg_temp(pa) or 0
    if mode == "dt":
        s = render_to_string("stop_info_dt.html", ctx)
        s = s.encode("cp1251")
        return HttpResponse(s)
    ctx['us'] = get_user_settings(request)
    ctx['weather'] = weather_detect(pa)

    if request.GET.get("v") == "2":
        ctx['set_map_center'] = request.session.get(
            'stop_%s_set_map_center' % stop.id)
        tmpl = "stop_info_2.html"
    elif tmc:
        tmpl = "stop_info_black.html"
    elif not tmpl:
        tmpl = "turbo_stop_info.html"

    return arender(request, tmpl, ctx)
    

def stop_info(request, city_name=None, stop_id=None, tmc=None):
    # low level tablo render
    tmpl = None
    mode = request.GET.get('mode')
    g_stop_id = request.GET.get("stop_id")

    if g_stop_id:
        try:
            stop_id = int(g_stop_id)
        except:
            if g_stop_id == "Tablo1":
                stop_id = 20619
            elif g_stop_id == "Tablo2":
                stop_id = 20623
            else:
                raise Http404
        mode = "dt"
        stop = get_object_or_404(NBusStop, id=stop_id)
        city = stop.city
    else:
        city = get_object_or_404(City, slug=city_name)
        stop = get_object_or_404(NBusStop, id=stop_id, city=city)

    ctx = {"city": city, "stop": stop, "noga": True}
    if request.GET.get("a") is not None:
        stops = [7685, 7657, 8580, 13763, 13764]
        next_step = int(request.GET.get("a")) + 1
        stop_id = stops[next_step % 5]
        stop = get_object_or_404(NBusStop, id=stop_id, city=city)
        ctx["stop"] = stop
        ctx['set_map_center'] = request.session.get(
            'stop_%s_set_map_center' % stop.id)
        ctx['next_step'] = next_step
        tmpl = "stop_info_3.html"

    now = city.now

    bdata_mode3 = rcache_get("bdata_mode3_%s" % city.id, {})
    preds = bdata_mode3.get(stop.id, [])
    preds = sorted(preds, key=lambda p: p.get('t'))
    nbdata = []
    for pred in preds:
        bus = bus_get(pred['bid'])
        pq = copy.copy(pred)
        pq['cdown'] = int((pred['t']-now).total_seconds()/60)
        pq['t'] = "%02d:%02d" % (pred['t'].hour, pred['t'].minute)
        pq['t2'] = (u"%02d:%02d" % (pred['t2'].hour,
                                    pred['t2'].minute)) if pred.get('t2') else ''
        pq['ttype_slug'] = bus.ttype_slug
        pq['konec'] = ''
        if 'l' in pred:  # если для какого-то маршрута текущая остановка конечная,
            # то конкретного ТС (ключа l) не будет, потому что неизвестно какое ТС выйдет
            # с конечной сейчас. поэтому там просто время
            if pred['l']['d'] == 0 and bus.napr_a:
                pq['konec'] = bus.napr_a.split(' - ')[-1]
            elif pred['l']['d'] == 1 and bus.napr_b:
                pq['konec'] = bus.napr_b.split(' - ')[-1]

        nbdata.append(pq)
    # for pred in preds

    stop.bdata = nbdata
    ctx['now'] = now
    ctx['avg_temp'] = avg_temp(city)
    if mode == "dt":
        s = render_to_string("stop_info_dt.html", ctx)
        s = s.encode("cp1251")
        return HttpResponse(s)
    ctx['us'] = get_user_settings(request)
    ctx['weather'] = weather_detect(city)

    if request.GET.get("v") == "2":
        ctx['set_map_center'] = request.session.get(
            'stop_%s_set_map_center' % stop.id)
        tmpl = "stop_info_2.html"
    elif tmc:
        tmpl = "stop_info_black.html"
    elif not tmpl:
        tmpl = "stop_info.html"

    return arender(request, tmpl, ctx)
# def stop_info


def status_passengers(request, city_name, d=None):
    us = get_user_settings(request)

    city = get_object_or_404(Place, slug=city_name)
    delta = datetime.timedelta(hours=city.timediffk)
    if d:
        tm = datetime.datetime.strptime(d, "%Y-%m-%d") - delta
    else:
        tm = city.now
    next_day = tm+datetime.timedelta(days=1)
    ctx = {'us': us, "city": city, "tm": tm}
    passengers = PassengerStat.objects.using('bstore').filter(
        city=city.id, ctime__range=(tm, next_day))
    # ctx['passengers'] = passengers
    upassengers = passengers.distinct('ms_id', 'us_id', 'psess')
    ctx['passengers_cnt'] = upassengers.count()
    ctx['passengers_cnt_web'] = upassengers.filter(os=0).count()
    ctx['passengers_cnt_android'] = upassengers.filter(os=1).count()
    ctx['passengers_cnt_ios'] = upassengers.filter(os=2).count()

    return arender(request, "status_passengers.html", ctx)


def status_day_passengers_js(request, city_name, d):
    city = get_object_or_404(Place, slug=city_name)
    delta = datetime.timedelta(hours=city.timediffk)
    tm = datetime.datetime.strptime(d, "%Y-%m-%d") - delta
    next_day = tm+datetime.timedelta(days=1)
    passengers = PassengerStat.objects.using('bstore').filter(
        city=city.id, ctime__range=(tm, next_day)).order_by("ctime")
    serialized = []
    unique_passengers = {}
    unique_cnt = 0
    for p in passengers:
        if p.ms_id:
            id_ = "ms_%s" % p.ms_id
        elif p.us_id:
            id_ = "us_%s" % p.us_id
        else:
            id_ = p.psess

        if not unique_passengers.get(id_):
            unique_cnt += 1
            unique_passengers[id_] = unique_cnt

        id_ = unique_passengers[id_]
        # id_ = hashlib.sha224(id_).hexdigest()[:6]
        ctime = p.ctime + delta  # compensate back time zone
        if not math.isnan(p.lat):
            p.lon = round(p.lon, 6)  # 5 is ~1m
            p.lat = round(p.lat, 6)
            serialized.append({"x": p.lon, 'y': p.lat, 't': str(
                ctime.time()).split(".")[0], 'i': id_, 'o': p.os})
    serialized = ujson.dumps(serialized)
    return HttpResponse(serialized)


def status_offline(request, city_name):
    us = get_user_settings(request)

    city = get_object_or_404(City, slug=city_name)
    now = city.now
    # yday = now - datetime.timedelta(days=1)
    cc_key = "uevents_offline_%s" % city.id
    offline_events = list(rcache_get(cc_key, {}).values())
    offline_events = sorted(
        offline_events, key=lambda x: x['timestamp'], reverse=True)
    for e in offline_events:
        e['bus'] = bus_get(e['bus'])
    ctx = {'us': us, "city": city, "offline_events": offline_events}
    return arender(request, "status_offline.html", ctx)


def edit_stop(request, city_name, stop_id):
    us = get_user_settings(request)

    transaction = get_transaction(us)
    place = get_object_or_404(Place, slug=city_name)

    if not transaction:
        return HttpResponse(_(u"нет прав доступа"))
    stop = get_object_or_404(NBusStop, id=stop_id)
    ustop = stop.unistop
    routes = Bus.objects.filter(
        route__busstop=stop).order_by('order').distinct()
    ctx = {'us': us, 'stop': stop, 'ustop': ustop, \
           'routes': routes, 'place': place}
    if request.POST:
        # round 1
        name = request.POST.get("name")
        name_alt = request.POST.get("name_alt")
        if name != stop.name or name_alt != stop.name_alt:
            stops = NBusStop.objects.filter(
                name=stop.name, point__distance_lte=(stop.point, 500))
            for s in stops:
                jdata = serializers.serialize("json", [s])
                Diff.objects.create(user=request.user, us=us, action=0,
                                    data=jdata, model="nbusstop",
                                    model_pk=s.pk)
                s.name = name
                s.name_alt = name_alt
                s.save()
                # refresh caches involved
                buses = Bus.objects.filter(route__busstop=s)
                for b in buses:
                    bus_last_f(b, force=True)   # in models.py
        # round 2
        stop = NBusStop.objects.get(id=stop_id)  # if changed above
        point_x = request.POST.get("point_x")
        point_y = request.POST.get("point_y")
        if point_x:
            stop.point = Point(float(point_x), float(point_y))
            jdata = serializers.serialize("json", [stop])
            Diff.objects.create(user=request.user, us=us, action=3,
                                data=jdata, model="nbusstop",
                                model_pk=stop.pk)
            stop.save()
            for bus in Bus.objects.filter(route__busstop=stop, places__slug=city_name):
                bus.mtime = place.now
                bus.save()
                fill_routeline(bus, True)
        ctx['stop'] = stop

    return arender(request, "edit_stop.html", ctx)


def work(request):
    us = get_user_settings(request)

    ctx = {'us': us}
    return arender(request, "work.html", ctx)


def feedback_ts(request, city_name, uid):
    #данные по конкретному тс
    city = get_object_or_404(City, slug=city_name)
    us = get_user_settings(request)

    bus_id = uid

    vehicle = Vehicle.objects.filter(uniqueid=bus_id).first()
    #статус тс за сегодня
    vehicle_status = VehicleStatus.objects.filter(city=city.id, uniqueid=bus_id).order_by('-city_time')[:10]

    #обрабатываем статусы и формируем список чтоб отправить для отображения
    if vehicle_status:
        last_status = vehicle_status[0]
        bus = bus_get(last_status.bus)
        statuses_cnt = vehicle_status.count()
    else:
        bus = None
        statuses_cnt = 0
        last_status = None
    statuses = vehicle_status

    #отзывы
    votes = []
    try:
        if vehicle:
            vehicle1 = Vehicle1.objects.filter(gosnum = vehicle.gosnum, bus = bus).first()
        if vehicle1:
            votes = Vote.objects.filter(vehicle = vehicle1).order_by('-ctime')
    except:
        votes = []

    allevents = rcache_get("allevents_%s" % city.id, {})
    event = allevents.get("event_%s_%s" % (city.id, bus_id))

    ctx = {'us': us, 'city': city, 'vehicle': vehicle, 'statuses': statuses,
           'bus': bus,  'votes': votes, 'last_status': last_status,
           'event': event}
    return arender(request, "feedback_ts.html", ctx)


def broadcast(request, city_name):
    city = get_object_or_404(City, slug=city_name)
    us = get_user_settings(request)

    transaction = get_transaction(us)
    now = city.now
    ctx = {'us': us, 'city': city}
    return arender(request, "broadcast.html", ctx)


def devices(request, city_name):
    city = get_object_or_404(City, slug=city_name)
    us = get_user_settings(request)
    transaction = get_transaction(us)

    now = city.now
    message = request.GET.get('message')
    if message:
        ms_id = request.GET.get('ms_id')
        dialog = [(u"Запрос звонка"), u"OK"]
        # u"Авария на ул. Декабристов, объезд по Мурманской не доезжая до Братской"
        params = {'message': message, 'message_id': 1, "dialog": dialog}
        wsocket_cmd('driver_message', params, ms_id=ms_id)
        return HttpResponse("1")

    ms_id = request.GET.get('reload')
    if ms_id:
        wsocket_cmd('reload', {}, ms_id=ms_id)
        return HttpResponse("1")

    ms_id = request.GET.get('kiosk_off')
    if ms_id:
        wsocket_cmd('kiosk_off', {}, ms_id=ms_id)
        return HttpResponse("1")

    ms_id = request.GET.get('remove')
    if ms_id:
        ms = MobileSettings.objects.get(id=int(ms_id))
        ms.delete()
        return HttpResponse("1")

    if request.POST:
        for k, v in request.POST.items():
            if "__device" not in k:
                continue
            mod = False
            ms_id, _ = k.split("__")
            ms = ms_get(int(ms_id))

            v = request.POST.get('%s__bus' % ms.id)
            if v:
                v = bus_get(int(v))
            else:
                v = None
            if ms.gps_send_bus != v:
                ms.gps_send_bus = v
                mod = True

            v = request.POST.get('%s__gosnum' % ms.id)
            if ms.gosnum != v:
                ms.gosnum = v
                mod = True

            v = request.POST.get('%s__phone' % ms.id)
            if ms.phone != v:
                ms.phone = v
                mod = True

            v = request.POST.get('%s__name' % ms.id)
            if ms.name != v:
                ms.name = v
                mod = True

            v = request.POST.get('%s__ramp' % ms.id)
            if v == "on":
                v = True
            else:
                v = False
            if ms.gps_send_ramp != v:
                ms.gps_send_ramp = v
                mod = True

            v = request.POST.get('%s__send' % ms.id)
            if v == "on":
                v = True
            else:
                v = False
            if ms.gps_send != v:
                ms.gps_send = v
                mod = True

            if mod:
                ms.save()
                data = {
                    'gosnum': ms.gosnum,
                    'phone': ms.phone,
                    'name': ms.name,
                    'ramp': ms.gps_send_ramp,
                    'send': ms.gps_send}
                if ms.gps_send_bus:
                    data['bus_id'] = ms.gps_send_bus.id
                wsocket_cmd('driver_data', data, ms_id=ms.id)
    ms_online = REDIS.smembers('ms_online')
    ms_online = set([_.decode('utf8') for _ in ms_online])
    devices = MobileSettings.objects.filter(
        mode=2, city=city).order_by('-ltime')
    for d in devices:
        d.gevent = rcache_get("gevent_%s" % d.id, {})
        d.gevent.pop('history', None)
        d.gevent['odometer'] = d.gevent.get('odometer', 0)/1000
        if str(d.id) in ms_online:
            d.gevent['online'] = True
    pagi = Paginator(devices, 30)
    page = request.GET.get('page', "1")
    paginator = pagi.page(int(page))
    buses = buses_get(city)

    ctx = {'city': city, "us": us, 'buses': buses,
           "devices": devices, 'noga': True,
           "APK_LAST_DRIVER": get_setting('app_driver'),
           "paginator": paginator,
           "pagi": pagi}
    return arender(request, "devices.html", ctx)


def error(request):
    return HttpResponse("error")


def stop_new(request, city_name):
    us = get_user_settings(request)
    transaction = get_transaction(us)
    city = get_object_or_404(City, slug=city_name)


    if request.method == 'POST':
        form = BusStopNewForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            point = form.cleaned_data['point']
            stop = NBusStop.objects.create(city=city, name=name, point=point)
            jdata = serializers.serialize("json", [stop])
            add_stop_geospatial(stop)
            Diff.objects.create(us=us, action=1, status=1,
                                data=jdata, model="nbusstop",
                                model_pk=stop.pk)
            return HttpResponseRedirect(stop.get_absolute_url()+"edit/")
    else:
        form = BusStopNewForm()
    ctx = {'us': us, 'form': form, 'city': city}

    return arender(request, "stop_new.html", ctx)


def bus_new(request, city_name):
    us = get_user_settings(request)
    transaction = get_transaction(us)
    place = get_object_or_404(Place, slug=city_name)


    if not transaction:
        return HttpResponse("Нет прав доступа. Активируйте пин-код или свяжитесь с администратором.")

    if request.method == 'POST':
        form = BusNewForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            type_ = int(form.cleaned_data['type'])
            if Bus.objects.filter(places__id=place.id, name=name, ttype=type_):
                return arender(request, "message.html", {"message": "Такой маршрут уже существует!"})
            else:
                bus = Bus.objects.create(name=name, ttype=type_)
                bus.places.add(place)
                jdata = serializers.serialize("json", [bus])
                Diff.objects.create(us=us, action=1, status=1,
                                    data=jdata, model="bus",
                                    model_pk=bus.pk)
                buses_get(place, force=True)
                return HttpResponseRedirect(bus.get_absolute_url()+"edit/")
    else:
        form = BusNewForm()
    ctx = {'us': us, 'form': form, 'place': place}

    return arender(request, "bus_new.html", ctx)


def voice_query(request):
    us = get_user_settings(request)
    transaction = get_transaction(us)

    ctx = {'noga': True}
    if request.POST:
        n = request.POST.get('name')
        ctx['stops'] = NBusStop.objects.filter(name__iexact=n)
    return arender(request, "voice_query.html", ctx)


def mapzen(request, zoom, x, y, mode="json"):
    tile_server = settings.TILE_SERVER
    nextzen_prefix = 'tilezen/vector/v1'
    api_key = settings.TILE_SERVER_KEY
    url = "%s/%s/all/%s/%s/%s.%s?api_key=%s" % (tile_server, nextzen_prefix, zoom, x, y, mode, api_key)

    try:
        r = requests.get(url, timeout=(1, 90))
    except:
        return HttpResponse("error 12")

    if not r or r.status_code != 200 or len(r.content) == 0:
        return HttpResponse("error")

    file_path = '/mnt/fast/tile_bustime/vector/v1/all/%s/%s/%s.%s' % (zoom, x, y, mode)
    directory = os.path.dirname(file_path)
    try:
        if not os.path.exists(directory):
            os.makedirs(directory)
    except:
        pass

    with open(file_path, 'wb') as output:
        output.write(r.content)

    if mode == "json":
        content_type = 'application/json'
    else:
        content_type = 'application/x-protobuf'

    response = HttpResponse(r.content, content_type=content_type)
    return response


def explorer(request, id_=None):
    us = get_user_settings(request)
    transaction = get_transaction(us)


    allow = False
    if transaction and transaction.vip:
        allow = True

    if not allow:
        return HttpResponse(_(u"нет прав доступа"))

    if not id_:
        return HttpResponseRedirect("please choose id")
    ms = MobileSettings.objects.get(id=id_)
    try:
        ps = PassengerStat.objects.using(
            'bstore').filter(psess=ms.id).latest('id')
    except:
        ps = None

    fields = dict(ms.__dict__)
    for k, v in ms.__dict__.items():
        if k.startswith('_'):
            del fields[k]
        if k == 'city_id':
            fields[k] = CITY_MAP[v].name

    ctx = {"us": us, "transaction": transaction,
           "noga": 1, "ms": ms, "fields": fields, "ps": ps}
    return arender(request, "explorer.html", ctx)


def explorer_events(request, city_id=None, ttype=None):
    us = get_user_settings(request)

    city = get_object_or_404(Place, id=int(city_id))
    if not request.user.is_superuser:
        return HttpResponse(_(u"нет прав доступа"))
    events = {}

    # get glonassd data
    glonassd = {}
    ports = list(Glonassd.objects.filter(city__id=city.id).values_list('port', flat=True))
    for p in ports:
        for r in REDIS.smembers('gd_port__%s' % p):    # get value
            r = r.decode('utf8')
            events = rcache_mget(r, sformat="json")[0]
            for e in events:
                if e.get('imei') and e.get('imei') not in glonassd:
                    glonassd[e.get('imei')] = e

    if ttype == "uevents":
        events = rcache_get("uevents_%s" % city.id, {})

    elif ttype == "glonassd":
        events = glonassd

    elif ttype == "bustime":
        upload_event_list = REDIS.smembers("gevents_%s" % city.id)
        upload_event_list = set([_.decode('utf8') for _ in upload_event_list])
        keys = ["gevent_%s" % x for x in upload_event_list]
        raw_events = rcache_mget(keys)
        events = {}
        for e in raw_events:
            if e:
                events[e['uniqueid']] = e
                del events[e['uniqueid']]['history']

    elif ttype == "yproto":
        upload_event_list = REDIS.smembers("upload_events_%s" % city.id)
        upload_event_list = set([_.decode('utf8') for _ in upload_event_list])
        keys = ["upload_event_%s" % x for x in upload_event_list]
        raw_events = rcache_mget(keys)
        events = {}
        for e in raw_events:
            if e:
                events[e['uniqueid']] = e
                del events[e['uniqueid']]['history']

    elif ttype == "nimbus":
        cc_key_nimbus = "uevents_%s_raw" % city.id
        r = REDIS.get(cc_key_nimbus)
        if r:
            events = json.loads(r)

    elif ttype == "taxi":
        events = rcache_get("tevents_%s" % city_id, {})

    elif ttype == "place":
        uids = REDIS.smembers(f"place__{city.id}")
        uids = list([x.decode('utf8') for x in uids])
        to_get = [f'event_{uid}' for uid in uids]
        events = {}
        for ev in rcache_mget(to_get):
            if not ev: continue
            events[ev.uniqueid] = ev

    # postfilters
    for k, v in events.items():
        # json doesn't like django objects
        if ttype == "nimbus":
            v['msg']['t_'] = str(datetime.datetime.fromtimestamp(
                v['msg']['t']) + datetime.timedelta(hours=city.timediffk))
            v['tm_'] = str(datetime.datetime.fromtimestamp(
                v['tm']) + datetime.timedelta(hours=city.timediffk))
            v['x'] = v['msg']['pos']['x']
            v['y'] = v['msg']['pos']['y']
        if v.get('timestamp'):
            if type(v['timestamp']) == int:
                v['timestamp_'] = str(
                    datetime.datetime.fromtimestamp(v['timestamp']))
            else:
                v['timestamp_'] = str(v['timestamp'])
            v['timestamp'] = str(v['timestamp'])
        if v.get("history"):
            del v['history']
        events[k]['json'] = json.dumps(v, indent=4, sort_keys=True, ensure_ascii=False, default=str)
        if v.get('bus'):
            if isinstance(v['bus'], Bus):
                v['bus'] = v['bus'].id
            v["bus_"] = bus_get(v['bus'])

        # insert glonassd info:
        uid_original = v.get('uid_original')
        if uid_original in glonassd:
            events[k]['glonassd'] = json.dumps( glonassd[uid_original], indent=4, sort_keys=False, ensure_ascii=False)
        else:
            events[k]['glonassd'] = None
    # for k, v in events.items()

    ctx = {"us": us, "noga": 1, "city": city, "ttype": ttype, "events": events}
    return arender(request, "explorer_events.html", ctx)


def ad336x280(request):
    metric('ad336x280')
    link = "https://parabarter.ru"
    ver = random.choice(['para_01'])
    ctx = {'ver': ver, "link": link}
    return render(request, "ad336x280.html", ctx)


def app(request):
    metric('ad336x280_app')
    dos = mobile_detect(request)
    if dos == "ios":
        return HttpResponseRedirect("https://itunes.apple.com/ru/app/bustime-vrema-avtobusa!/id879310530")
    else:
        return HttpResponseRedirect("https://play.google.com/store/apps/details?id=com.indie.bustime")


def redirector(request):
    url = request.GET.get('url', 'https://bustime.loc/')
    ip = get_client_ip(request)
    log_message(ttype="adgeo", message="redirect %s by %s" % (url, ip))
    return HttpResponseRedirect(url)


@csrf_exempt
def bot_say(request):
    text = request.POST.get("text")
    room = request.POST.get("room")
    if not text:
        text = request.GET.get("text", 'no text')
        room = request.GET.get("room")

    if room == "bustime":  # main
        channel = "_bot_dev"
    if room == "reviews":  # reviews
        channel = "_bot_reviews"
    else:  # events
        channel = '_bot'

    REDIS_W.publish(channel, text)
    return HttpResponse(text)


def is_mat(s, src=None):
    r = PymorphyProc.test(s)
    sl = s.lower()
    if not r and u'ебанн' in sl or \
        u'ахуй' in sl or \
            u'ахуе' in sl:
        r = True
    if r:
        bot_txt = u"мат обнаружен: %s" % s
        if src:
            bot_txt += u"\n%s" % src
        REDIS_W.publish('_bot', bot_txt)
    return r


@csrf_exempt
def radio_say(request):
    us = get_user_settings(request)
    city_id = request.POST.get('city_id', "11")
    city_id = int(city_id)
    ms_id = request.POST.get('ms_id')
    fogg = request.FILES.get('voiceBlob')
    fmp3 = request.FILES.get('mp3file')
    if fogg:
        voiceBlob = fogg
    if fmp3:
        voiceBlob = fmp3

    fname = '%s-us-%s' % (int(time.time()), us.id)
    fname_path = '%s/sounds/radio/%s' % (settings.PROJECT_ROOT, fname)
    with open("%s" % fname_path, 'wb+') as destination:
        for chunk in voiceBlob.chunks():
            destination.write(chunk)
    mp3 = ['-ac', '2', '-ab', '32k', '-f', 'mp3', "%s.mp3" % fname_path]
    subprocess.call(["ffmpeg", "-i", "%s" % fname_path] + mp3)

    opus = ['-codec:a', 'libopus', '-b:a', '16k', '-vbr', 'on',
            '-compression_level', '10', "%s.ogg" % fname_path]
    subprocess.call(["ffmpeg", "-i", "%s" % fname_path] + opus)

    aac = ['-c:a', 'aac', '-b:a', '16k', "%s.mp4" % fname_path]
    subprocess.call(["ffmpeg", "-i", "%s.ogg" % fname_path] + aac)

    extension = "mp3"
    if ms_id:
        try:
            ms = ms_get(int(ms_id))
        except:
            return HttpResponse(u"Терминал с id=%s не найден" % (ms_id))
        chan = "ru.bustime.ms__%s" % (ms_id)
    else:
        chan = "ru.bustime.radio__%s" % (city_id)
    sio_pub(chan, {"radio": {
            "us_id": us.id, "filename": fname,
            "extension": extension, "emergency_warning": True}})
    return HttpResponse("%s; %s; %s" % (fname, city_id, ms_id))


def city_admin_fill_inter_stops(request, city_name=None):
    city = get_object_or_404(Place, slug=city_name)
    us = get_user_settings(request)

    transaction = get_transaction(us)
    if not transaction:
        return HttpResponse("нет прав доступа")
    cnt = fill_inter_stops(city, force=True)
    ctx = {"us": us,"noga": 1, "message": "%s изменений" % cnt, 'back_button': True}

    return arender(request, "message.html", ctx)


def city_admin_update_js(request, city_name=None):
    city = get_object_or_404(City, slug=city_name)
    us = get_user_settings(request)
    transaction = get_transaction(us)

    if not transaction:  # 'NoneType' object has no attribute 'vip'
        return HttpResponse("нет прав доступа")

    cc_key = "city_admin_update_js_%s" % city.id
    us1 = rcache_get(cc_key, {})
    if not us1:
        rcache_set(cc_key, us, 60)
        fill_order(city)
        info_data = city_update_js(city)
        message = "<br/>".join(info_data)
        rcache_set(cc_key, {}, 60)
    else:
        message = "Операция выполняется пользователем %s (%s), попробуйте позже." % (us1.name, us1.city.name)
    ctx = {"us": us,"noga": 1, "message": message, 'back_button': True}

    return arender(request, "message.html", ctx)


def city_update_js(city):
    buses_get(city, force=1)
    info_data = city_data_export(city, reload_signal=False)

    f = open("%s/static/logs/update_js-%d.log" %
             (settings.PROJECT_DIR, city.id), 'w')
    f.write('%s\n' % datetime.datetime.now().strftime('%d.%m.%y %H:%M:%S'))
    for line in info_data:
        f.write('%s\n' % line)
    f.close()

    return info_data
# def city_update_js(city)

def city_admin_update_v8(request, city_name=None):
    place = get_object_or_404(Place, slug=city_name)
    us = get_user_settings(request)
    transaction = get_transaction(us)

    if not transaction:  # 'NoneType' object has no attribute 'vip'
        return HttpResponse("нет прав доступа")

    cc_key = "city_admin_update_v8_%s" % place.id
    us1 = rcache_get(cc_key, {})
    if not us1:
        rcache_set(cc_key, us, 60)
        info_data = city_update_v8(place)
        message = "<br/>".join(info_data)
        rcache_set(cc_key, {}, 60)
    else:
        message = "Операция выполняется пользователем %s (%s), попробуйте позже." % (us1.name, us1.place.name)
    ctx = {"us": us,"noga": 1, "message": message, 'back_button': True}

    return arender(request, "message.html", ctx)

def city_update_v8(place):
    try:
        # call city_update_v8() from web interface
        from utils.turbo_json_dump_update import make_patch_for_json
    except:
        # call city_update_v8() from utils/* scripts
        from turbo_json_dump_update import make_patch_for_json
    info_data = make_patch_for_json(place)

    f = open("%s/static/logs/update_v8-%d.log" %
             (settings.PROJECT_DIR, place.id), 'w')
    f.write('%s\n' % datetime.datetime.now().strftime('%d.%m.%y %H:%M:%S'))
    for line in info_data:
        f.write('%s\n' % line)
    f.close()

    return info_data



def city_admin_update_mobile(request, city_name=None):
    place = get_object_or_404(Place, slug=city_name)
    us = get_user_settings(request)
    transaction = get_transaction(us)

    if not transaction:
        return HttpResponse("нет прав доступа")

    cc_key = "city_admin_update_mobile_%s" % place.id
    us1 = rcache_get(cc_key, {})
    if not us1:
        rcache_set(cc_key, us, 60)
        info_data = city_update_mobile(place)

        message = "<br/>".join(info_data)
        rcache_set(cc_key, {}, 60)
    else:
        message = "Операция выполняется пользователем %s, попробуйте позже." % (us1.name)
    ctx = {"us": us,"noga": 1, "message": message, 'back_button': True}

    return arender(request, "message.html", ctx)

# def city_admin_update_mobile(request, city_name=None)


def city_update_mobile(place):
    from utils.mobile_dump_update import DiffProcessor, DBVer, logger as diff_logger
    from logging.handlers import MemoryHandler
    from utils.turbo_json_dump_update import make_patch_for_json
    # mobile_update_v5: Выгрузка данных из БД

    info_data = mobile_update_place(place, reload_signal=False)  # update_utils.py
    info_data.append('')
    handler = MemoryHandler(1024*10, target=logging.NullHandler(), flushOnClose=False)
    handler.setLevel(logging.INFO)
    diff_logger.addHandler(handler)

    # settings.PROJECT_DIR = /bustime/bustime
    cmd = [
        u"%s/bustime/static/other/db/v5/0diff_one.sh" % settings.PROJECT_DIR,
        str(place.id)
    ]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    result, err = p.communicate()
    for line in result.decode().split('\n'):
        if line:
            info_data.append(line)
    for line in err.decode().split('\n'):
        if line:
            info_data.append(line)
    info_data.append('')

    cmd = [
        u"%s/bustime/static/other/db/v7/0diff_one.sh" % settings.PROJECT_DIR,
        str(place.id)
    ]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    result, err = p.communicate()
    for line in result.decode().split('\n'):
        if line:
            info_data.append(line)
    for line in err.decode().split('\n'):
        if line:
            info_data.append(line)

    processor = DiffProcessor(DBVer.v5)
    processor.diff_one_google(place.id)

    processor = DiffProcessor(DBVer.v7)
    processor.diff_one_google(place.id)
    info_data = info_data + [record.msg for record in handler.buffer]

    # auto reload connected clients
    reload_signal = False

    s = []
    if reload_signal:
        for ms_id in REDIS.smembers("ms_online"):
            ms_id = ms_id.decode('utf8')
            ms = ms_get(ms_id)
            if ms and ms.version >= 150 and ms.place == place:
                wsocket_cmd('reload', {}, ms_id=ms_id)
                s.append(ms_id)
    if reload_signal:
        info_data.append(u"Перезагрузка: %s" % ", ".join(s))

    f = open("%s/static/logs/update_mobile-%d.log" %
             (settings.PROJECT_DIR, place.id), 'w')
    f.write('%s\n' % datetime.datetime.now().strftime('%d.%m.%y %H:%M:%S'))
    for line in info_data:
        f.write('%s\n' % line)
    f.close()
    handler.flush()
    return info_data
# def city_update_mobile(place)


def city_admin_windmill_restart(request, city_name=None):
    place = get_object_or_404(Place, slug=city_name)
    us = get_user_settings(request)
    transaction = get_transaction(us)

    if not transaction:
        return HttpResponse("нет прав доступа")

    info_data = []
    todo = []

    if os.path.isfile("%s/bustime/update/c%s.py" % (settings.PROJECT_DIR, place.id)):
        todo.append("updaters:updater_%s" % place.id)

    if os.path.isfile("%s/coroutines/c%s.py" % (settings.PROJECT_DIR, place.id)): #
        todo.append("crawlers:c%s" % place.id)

    try:
        if settings.UPDATERS_HOSTNAME != settings.MASTER_HOSTNAME:
            cmd = [f"sudo -u supervarius ssh -p 9922 -o \"StrictHostKeyChecking no\" supervarius@{settings.BUSTIME_HOSTS[settings.UPDATERS_HOSTNAME]} "
                    f"\"sudo /usr/bin/supervisorctl status nimbuses:nimbus_{place.id}\""]
            subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT).decode()
        else:
            cmd = ["sudo", "/usr/bin/supervisorctl", "status", "nimbuses:nimbus_{}".format(place.id)]
            subprocess.check_output(cmd).decode()
        todo.append("nimbuses:nimbus_{}".format(place.id))
    except subprocess.CalledProcessError as e:
        pass


    pevents = REDIS.smembers("place__%s" % place.id)
    uids = list([x.decode('utf8') for x in pevents])
    to_get = [f'event_{uid}' for uid in uids]
    sources = {}
    for e in rcache_mget(to_get):
        if not e or not e['channel'] or not e['src']: continue
        if e['channel'] not in sources:
            sources[e['channel']] = []
        if e['src'] not in sources[e['channel']]:
            sources[e['channel']].append(e['src'])

    for channel, src in sources.items():
        if channel == 'gtfs_updater':
            for id in src:
                todo.append("gupdaters:gupdater_%s" % id)   # f3.bustime.loc
        elif channel == 'yandex_proto':
            for id in src:
                todo.append("yproto:yproto_%s" % id)   # f2.bustime.loc/localhost


    for daemon in todo:
        try:
            cmd = ''
            output = ''

            if re.match(r"updaters:updater_\d+", daemon) or re.match(r"nimbuses:nimbus_\d+", daemon) or re.match(r"crawlers:c\d+", daemon):

                if settings.UPDATERS_HOSTNAME != settings.MASTER_HOSTNAME:
                    cmd = [f"sudo -u supervarius ssh -p 9922 -o \"StrictHostKeyChecking no\" supervarius@{settings.BUSTIME_HOSTS[settings.UPDATERS_HOSTNAME]} "
                            f"\"sudo /usr/bin/supervisorctl restart {daemon}\""]
                    output = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT).decode()
                else:
                    cmd = ["sudo", "/usr/bin/supervisorctl", "restart", daemon]
                    output = subprocess.check_output(cmd).decode()

            elif re.match(r"gupdaters:gupdater_\d+", daemon):

                cmd = [f"sudo -u supervarius ssh -p 9922 -o \"StrictHostKeyChecking no\" supervarius@{settings.BUSTIME_HOSTS[settings.GTFS_HOSTNAME]} "
                        f"\"sudo /usr/bin/supervisorctl restart {daemon}\""]
                output = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT).decode()

            elif "yproto:yproto_" in daemon:

                cmd = ["sudo", "/usr/bin/supervisorctl", "restart", daemon]
                output = subprocess.check_output(cmd).decode()
            #

            if not cmd:
                info_data.append(f"No cmd for daemon '{daemon}'")
            else:
                info_data.append(output)
        except subprocess.CalledProcessError as e:
            info_data.append(e.output.decode())
        except Exception as ex:
            info_data.append(str(ex))
    # for daemon in todo

    info_data = "\n".join(info_data)
    message = "<pre>%s</pre>" % info_data
    ctx = {"us": us,"noga": 1, "message": message, 'back_button': True}

    return arender(request, "message.html", ctx)



def city_admin_city_new(request, city_name=None):
    city = get_object_or_404(City, slug=city_name)

    try:
        us = get_user_settings(request)
        transaction = get_transaction(us)
        if not request.user.is_superuser:
            return HttpResponse("нет прав доступа")

        # http://supervisord.org/configuration.html
        wconf, rconf, cconf, uconf = '', '', '', ''

        template = """[program:windmill_XXX]
command = /bustime/bustime/.venv/bin/python /bustime/bustime/coroutines/windmill.py XXX
user = www-data
autorestart = true
"""
        template3 = """[program:cXXX]
command = /bustime/bustime/.venv/bin/python /bustime/bustime/coroutines/cXXX.py
user = www-data
autorestart = true
"""
        template4 = """[program:updater_XXX]
command = /bustime/bustime/.venv/bin/python /bustime/bustime/coroutines/updater.py XXX
user = www-data
autorestart = true
"""
        gnames, cnames, unames = [], [], []
        for c in City.objects.filter(active=True).order_by('id'):
            cid = str(c.id)
            wconf += template.replace("XXX", cid)
            # rconf += template2.replace("XXX", cid)
            gnames.append(cid)
            if os.path.isfile("%s/bustime/update/c%s.py" % (settings.PROJECT_DIR, cid)):
                uconf += template4.replace("XXX", cid)
                unames.append(cid)
            if c.crawler:
                cconf += template3.replace("XXX", cid)
                cnames.append(cid)

        wconf += """[group:windmills]
programs=%s
priority=799""" % ",".join(["windmill_%s" % x for x in gnames])
        uconf += """[group:updaters]
programs=%s
priority=790""" % ",".join(["updater_%s" % x for x in unames])
        cconf += """[group:crawlers]
programs=%s
priority=811""" % ",".join(["c%s" % x for x in cnames])
        if settings.WINDMILLS_HOSTNAME != settings.MASTER_HOSTNAME:
            fd, path = tempfile.mkstemp(suffix=".conf", text=True)
            with open(path, 'w') as tmp_file:
                tmp_file.write(wconf)
            os.chmod(path, 0o775)
            cmd = [f"sudo -u supervarius scp -P9922 -o \"StrictHostKeyChecking no\" "
                   f"{path} supervarius@{settings.BUSTIME_HOSTS['s7']}:/etc/supervisor/conf.d/windmills.conf"]
            try:
                output = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT).decode()
            except subprocess.CalledProcessError as e:
                output = e.output.decode()
                raise ValueError(output)
            os.close(fd)
            os.unlink(path)
        else:
            with open('/etc/supervisor/conf.d/windmills.conf', 'w') as f:
                f.write(wconf)
        
        with open('/etc/supervisor/conf.d/crawlers.conf', 'w') as f:
            f.write(cconf)
        with open('/etc/supervisor/conf.d/updaters.conf', 'w') as f:
            f.write(uconf)

        info_data = []
        for action in ["reread", "update"]:
            cmd = ["sudo", "/usr/bin/supervisorctl", action]
            info_data.append(
                subprocess.check_output(cmd).decode()
            )
            if settings.WINDMILLS_HOSTNAME != settings.MASTER_HOSTNAME:
                try:
                    cmd = [f"sudo -u supervarius ssh -p 9922 -o \"StrictHostKeyChecking no\" supervarius@{settings.BUSTIME_HOSTS['s7']} "
                            f"\"sudo /usr/bin/supervisorctl {action}\""]
                    output = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT).decode()
                    info_data.append(output)
                except subprocess.CalledProcessError as e:
                    output = e.output.decode()
                    info_data.append(output)
        for c in City.objects.filter(active=True):
            abcd = [c.bus, c.trolleybus, c.tramway, c.bus_taxi, c.bus_intercity, c.water]
            c.set_transport()
            if abcd != [c.bus, c.trolleybus, c.tramway, c.bus_taxi, c.bus_intercity, c.water]:
                info_data.append("%s city transport update" % c.id)
                c.save()
        for daemon in ["statusd", "statusv", "uevent_saver"]:
            cmd = ["sudo", "/usr/bin/supervisorctl", "restart", daemon]
            info_data.append(
                subprocess.check_output(cmd).decode()
            )
        info_data = "\n".join(info_data)
        message = "<pre>%s</pre>" % info_data
    except:
        message = traceback.format_exc(limit=2)
        log_message(message, ttype="city_new", city=city)

    ctx = {"us": us,"noga": 1, "message": message, 'back_button': True}
    return arender(request, "message.html", ctx)


def city_admin_load_bus(request, city_name=None):
    place = get_object_or_404(Place, slug=city_name)
    us = get_user_settings(request)

    transaction = get_transaction(us)
    if not transaction:
        return HttpResponse("Нет подписки для доступа")

    ctx = {"us": us, "city": place}
    overwrite = request.POST.get('overwrite', '')  # on
    stop_from_1 = request.POST.get('stop_from_1', '')
    stop_to_1 = request.POST.get('stop_to_1', '')
    stop_from_2 = request.POST.get('stop_from_2', '')
    stop_to_2 = request.POST.get('stop_to_2', '')
    if overwrite:
        overwrite = True
    s = request.POST.get('s')

    if s:
        from bustime.load_bus import load_bus
        route_1 = None if not stop_from_1 or not stop_to_1 else {stop_from_1, stop_to_1}
        route_2 = None if not stop_from_2 or not stop_to_2 else {stop_from_2, stop_to_2}

        result = load_bus(s, city_id=place.id, overwrite=overwrite, route_1=route_1, route_2=route_2)

        # логируем событие загрузки маршрута
        if ('Load_bus_1: complete' in result) or ('Load_bus_2: complete' in result):
            news = None
            # если маршрут успешно загружен
            log_file = open(
                "/bustime/bustime/static/logs/load_bus-%d.log" % place.id, "w")
            log_file.write(
                '%s\n' % datetime.datetime.now().strftime('%d.%m.%y %H:%M:%S'))
            for l in result:
                log_file.write('%s\n' % l)
                # Добавлен маршрут 11 (Автобус), id=12624, city=Сыктывкар
                if l.startswith(u'Добавлен'):
                    news = l.split(',')
                # Обновлён маршрут 47 (Троллейбус), id=822, city=Санкт-Петербург
                if l.startswith(u'Обновлён'):
                    news = l.split(',')
                # if l.startswith(u'Добавлен')
            # for l in result
            log_file.close()

            if news:
                if u'Добавлен' in news[0]:
                    r = re.compile(
                        r'^Добавлен маршрут (.+) \((.+)\)$', re.UNICODE)
                else:
                    r = re.compile(
                        r'^Обновлён маршрут (.+) \((.+)\)$', re.UNICODE)
                rs = r.split(news[0])    # [u'', u'11', u'Автобус', u'']

                CityNews.objects.create(title='Автоновость', place_id=place.id, news_type=2,
                                        body=news[0],
                                        news_link='/%s/bus-%s/edit/' % (
                                            place.slug, rs[1]),
                                        author=us.user if us.user else request.user)

        result = "\n".join(result)
        result = result.replace("\n", '<br/>')
        ctx['result'] = result
    return arender(request, "load_bus.html", ctx)
# def city_admin_load_bus


def go(request):
    device = mobile_detect(request)
    if device == "android":
        url = 'https://play.google.com/store/apps/details?id=com.indie.bustime'
    elif device == "ios":
        url = 'https://itunes.apple.com/ru/app/bustime-vrema-avtobusa!/id879310530'
    else:
        url = "/"
    return HttpResponseRedirect(url)


def provider(request, city_name=None, provider_id=0):
    us = get_user_settings(request)
    transaction = get_transaction(us)


    provider_id = int(provider_id)
    place = Place.objects.filter(slug=city_name).first()

    if not provider_id:
        if place:
            providers = BusProvider.objects.filter(
               bus__places=place, bus__provider__isnull=False, bus__active=True).annotate(\
                cnt=Count('bus', filter=Q(bus__places=place, bus__active=True), distinct=True)
               ).distinct().order_by('name')
        else:
            providers = None
        ctx = {"place": place, "providers": providers, "us": us}
        return arender(request, "providers.html", ctx)

    provider = get_object_or_404(BusProvider, id=provider_id)

    buses = Bus.objects.filter(provider=provider, active=True, places=place).order_by('ttype', "name")
    ctx = {"place": place, "provider": provider, "buses": buses, "us": us}
    return arender(request, "provider.html", ctx)


# обработчик запроса на выбор маршрутов города
@csrf_exempt
def ajax_route_get_bus_city(request):
    place_id = request.POST.get('place_id', None)
    place_name = request.POST.get('place_name', None)

    response = []

    if place_name:
        place = get_object_or_404(Place, slug=place_name)
    elif place_id:
        place = get_object_or_404(Place, id=int(place_id))
    else:
        place = None

    if place:
        buses = buses_get(place, True)  # маршруты города
        for bus in buses:
            # routes
            rout0 = []  # список ID остановок
            route0 = routes_get(bus.id, direction=0)
            for r in route0:
                rout0.append(r.busstop.id)

            rout1 = []  # список ID остановок
            route1 = routes_get(bus.id, direction=1)
            for r in route1:
                rout1.append(r.busstop.id)

            if len(rout0) > 0 or len(rout1):
                response.append([bus.id, bus.name, bus.slug, rout0, rout1])

    return HttpResponse(ujson.dumps(response))


def register(request):
    if request.POST.get("email") or request.GET.get("email"):
        #  antispam
        raise Http404
    us = get_user_settings(request)

    transaction = get_transaction(us)
    pin = make_user_pin(us.id)
    us_id = "%s" % us.id
    us_id = us_id[0:4]+" " + us_id[4:]
    register_phone = get_register_phone(us).as_international # just in case, but as_national is a good choice
    ctx = {"us_id": us_id, "pin": pin, "us": us, "register_phone" : register_phone}

    return arender(request, "register.html", ctx)


def terms(request):
    us = get_user_settings(request)

    pin = make_user_pin(us.id)
    ctx = {"us": us}

    return arender(request, "terms.html", ctx)


def logout_view(request):
    logout(request)
    return HttpResponseRedirect("/")


def nursultan_back_astana(request, ourl=""):
    hl = request.GET.get("hl")
    if hl: ourl += "?hl=%s" % hl
    return HttpResponsePermanentRedirect("/astana/%s" % ourl)


# 14.03.19
# обработчик запроса на выдачу лог-файла
@csrf_exempt
def ajax_get_log_file(request):
    filename = request.POST.get('filename', None)
    city_id = request.POST.get('city_id', None)

    response = ''
    if filename and city_id:
        try:
            f = open("/bustime/bustime/static/logs/%s-%d.log" %
                     (filename, int(city_id)), 'r')
            response = f.read()
            f.close()
        except Exception as e:
            response = str(e)
    return HttpResponse(response)
# def ajax_get_gtfs_log_file(request)


# обработчик запроса на запуск задания
@csrf_exempt
def ajax_start_job(request):
    job = request.POST.get('job', None)
    city_id = request.POST.get('city_id', None)

    response = ''
    if city_id:
        if job == 'route_auto':
            cmd = ["/bustime/bustime/utils/route_auto.py", city_id]
        elif job == 'gtfs':
            cmd = ["/bustime/bustime/utils/gtfs-%s.py" % city_id]
        elif job == 'route_line_filler':
            cmd = ["/bustime/bustime/utils/route_line_filler.py", city_id, "--force", "--key", job]
        else:
            cmd = None

        if cmd:
            try:
                # чистим кэш
                while(REDIS.llen(job) != 0):
                    REDIS_W.lpop(job)

                # запускаем процесс
                subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                response = f'Job "{job}" started\n'
            except Exception as ex:
                REDIS_W.rpush(job, "worker_job:" + str(ex))
        else:
            response = 'Not found job name\n'
    else:
        response = 'No place ID\n'
    return HttpResponse(response)
# def ajax_start_job(request)


# обработчик запроса на состояние задания
@csrf_exempt
def ajax_status_job(request):
    job = request.POST.get('job', None)

    response = ''
    i = 0
    if job:
        try:
            while(i < 50 and REDIS.llen(job) != 0):
                s = REDIS_W.lpop(job)
                if s:
                    response += s.decode('utf-8')
                i += 1
        except Exception as e:
            response = "ajax_status_job: %s\n" % (str(e))
    return HttpResponse(response)
# def ajax_status_job(request)


# https://djbook.ru/rel1.7/ref/contrib/csrf.html
@csrf_exempt
def admin_vehicle_get_events(request):
    city_id = int(request.POST.get("city_id", "0"))

    '''
    Функция JavaScript Date() с одним аргументом (number or string) считает, что переданное время UTC
    и преобразует его в локальное браузера. Избежать можно, передавая строку без Z
    '''
    retval = {
        "time_server": datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
        "time_city": u'',
        "uevents": [],
        "allevent": {},
        "gevents": []
    }
    if city_id:  # and request.user.is_authenticated

        city = City.objects.filter(id=city_id)
        if city:
            retval["time_city"] = city[0].now.strftime('%Y-%m-%dT%H:%M:%S')

        uniques = request.POST.get("events", "[]")  # list of all ids on page

        try:
            uniques = ujson.loads(uniques)
        except:
            uniques = []

        if uniques and len(uniques):
            cc_key = "uevents_%s" % city_id
            events = rcache_get(cc_key, {})
            gevents = REDIS.smembers('gevents_%s' % city_id)
            gevents = set([_.decode('utf8') for _ in gevents])

            for u in uniques:
                e = events.get(u)
                if e:
                    e['timestamp'] = e['timestamp'].strftime(
                        '%Y-%m-%dT%H:%M:%S')
                    if e.get('bus'):
                        if type(e['bus']) is int:
                            bus = bus_get(e['bus'])
                        else:
                            bus = e['bus']

                        if bus:
                            e['bus'] = bus.id
                            e['bus_name'] = six.text_type(bus.name)
                            e['bus_bame'] = six.text_type(str(bus))
                            if bus.city:
                                e['bus_city_id'] = bus.city.id
                                e['bus_city_name'] = six.text_type(
                                    bus.city.name)
                            else:
                                e['bus_city_id'] = u''
                                e['bus_city_name'] = u''
                        # if bus
                    # if e.get('bus')

                    retval["uevents"].append(e)
                # if e
            # for u in uniques

            if gevents and u in gevents:
                g = rcache_get("gevent_%s" % u)
                if g:
                    g['timestamp'] = g['timestamp'].strftime('%Y-%m-%dT%H:%M:%S')
                    if g.get('bus'):
                        if type(g['bus']) is int:
                            bus = bus_get(g['bus'])
                        else:
                            bus = None
                        if bus:
                            g['bus'] = bus.id
                            g['bus_name'] = six.text_type(bus.name)
                            g['bus_bame'] = six.text_type(str(bus))
                            if bus.city:
                                g['bus_city_id'] = bus.city.id
                                g['bus_city_name'] = six.text_type(
                                    bus.city.name)
                            else:
                                g['bus_city_id'] = u''
                                g['bus_city_name'] = u''
                    retval["gevents"].append(g)

            allevents = rcache_get("allevents_%s" % city_id, {})
            retval["allevent"] = allevents.get("event_%s_%s" % (
                city_id, uniques[0])) if allevents else None
            if retval["allevent"]:
                retval["allevent"]['timestamp'] = retval["allevent"]['timestamp'].strftime(
                    '%Y-%m-%dT%H:%M:%S')
                if 'timestamp_prev' in retval["allevent"] and retval["allevent"]['timestamp_prev']:
                    retval["allevent"]['timestamp_prev'] = retval["allevent"]['timestamp_prev'].strftime(
                        '%Y-%m-%dT%H:%M:%S')
                if 'last_point_update' in retval["allevent"] and retval["allevent"]['last_point_update']:
                    retval["allevent"]['last_point_update'] = retval["allevent"]['last_point_update'].strftime(
                        '%Y-%m-%dT%H:%M:%S')
                if 'last_changed' in retval["allevent"] and retval["allevent"]['last_changed']:
                    retval["allevent"]['last_changed'] = retval["allevent"]['last_changed'].strftime(
                        '%Y-%m-%dT%H:%M:%S')

                try:
                    distance = int(distance_meters(
                        retval["allevent"]["x"], retval["allevent"]["y"], retval["allevent"]["x_prev"], retval["allevent"]["y_prev"]) * 1.1)
                    retval["allevent"]["distance"] = distance
                except:
                    retval["allevent"]["distance"] = 0

                if retval["allevent"]["busstop_nearest"]:
                    retval["allevent"]["busstop_nearest"] = {"busstop_id": retval["allevent"]["busstop_nearest"].busstop_id,
                                                             "direction": retval["allevent"]["busstop_nearest"].direction,
                                                             "busstop_name": retval["allevent"]["busstop_nearest"].busstop.name if retval["allevent"]["busstop_nearest"].busstop else None,
                                                             "bus_id": retval["allevent"]["busstop_nearest"].bus_id,
                                                             "bus_name": retval["allevent"]["busstop_nearest"].bus.name if retval["allevent"]["busstop_nearest"].bus else None,
                                                             }
                bus = retval["allevent"]['bus']
                if bus:
                    retval["allevent"]['bus'] = bus.id
                    retval["allevent"]['bus_bame'] = six.text_type(str(bus))
                    retval["allevent"]['bus_name'] = six.text_type(bus.name)
                    if bus.city:
                        retval["allevent"]['bus_city_id'] = bus.city.id
                        retval["allevent"]['bus_city_name'] = six.text_type(
                            bus.city.name)
                    else:
                        retval["allevent"]['bus_city_id'] = u''
                        retval["allevent"]['bus_city_name'] = u''
            # if retval["allevent"]
        # if uniques and len(uniques)

        retval["to_ignore"] = rcache_get("to_ignore_%s" % city_id, {})
        retval["anomalies"] = rcache_get("anomalies__%s" % city_id, {})
    # if city_id and request.user.is_authenticated

    return HttpResponse(ujson.dumps(retval))
# def admin_vehicle_get_events


@csrf_exempt
def admin_vehicle_del_vehicle(request):
    city_id = int(request.POST.get("city_id", "0"))
    uniqueid = request.POST.get("uniqueid")

    if city_id > 0 and uniqueid:
        try:
            Vehicle.objects.filter(uniqueid=uniqueid).delete()
            retval = {u"result": six.text_type(
                "vehicle id %s deleted" % uniqueid)}
        except Exception as e:
            retval = {u"error": six.text_type(str(e))}
    else:
        retval = {u"error": six.text_type(
            "City id %s or vehicle id %s not found" % (city_id, uniqueid))}

    return HttpResponse(ujson.dumps(retval))
# def admin_vehicle_del_vehicle

def history1(request, city_slug=None, page=None):
    from django.db.models.expressions import RawSQL

    us = get_user_settings(request)

    city = get_object_or_404(City, slug=city_slug)
    content_type_ids = [110, 111, 8]
    # last 30 days records desc order
    news = Version.objects.annotate(city_id=RawSQL(
                  '''SELECT bustime_versioncity.city_id
                      FROM bustime_versioncity
                     WHERE reversion_version.revision_id = bustime_versioncity.revision_id''', []
                     )).filter(city_id=city.id,
                        content_type_id__in=content_type_ids,
                        revision__date_created__lte=datetime.datetime.today(),
                        revision__date_created__gt=datetime.datetime.today()-datetime.timedelta(days=30)
                        ).exclude(
                            revision__comment__exact=''
                        ).order_by('-revision__date_created')

    paginator = Paginator(news, 30)
    if request.GET.get('page'):
        return HttpResponsePermanentRedirect(u"./page-%s/" % request.GET.get('page'))
    try:
        news = paginator.page(page)
    except PageNotAnInteger:
        news = paginator.page(1)
    except EmptyPage:
        news = paginator.page(paginator.num_pages)

    ctx = {
        "city": city,
        "news": news,
        "page": page,
        "user": request.user,
        "us": us
    }
    return arender(request, "history1.html", ctx)


def history(request, city_slug=None, page=None):
    us = get_user_settings(request)

    place = get_object_or_404(Place, slug=city_slug)
    content_type_ids = [110, 111, 8]
    device = mobile_detect(request)
    # last 30 days records desc order
    news = CityNews.objects.filter(place=place, news_type=2, etime__gt=datetime.datetime.now(),
                                   ctime__lte=datetime.datetime.today(), ctime__gt=datetime.datetime.today()-datetime.timedelta(days=30)
                                   ).order_by('-ctime')

    paginator = Paginator(news, 30)
    if request.GET.get('page'):
        return HttpResponsePermanentRedirect(u"./page-%s/" % request.GET.get('page'))
    try:
        news = paginator.page(page)
    except PageNotAnInteger:
        news = paginator.page(1)
    except EmptyPage:
        news = paginator.page(paginator.num_pages)

    ctx = {
        "place": place,
        "news": news,
        "page": page,
        "user": request.user,
        "us": us,
        "device": device
    }
    return arender(request, "history.html", ctx)


def dev_refresh(request, city_name=None):
    us = get_user_settings(request)
    if not request.user.is_superuser:
        return HttpResponse("нет прав доступа")
    n = int(request.GET.get('n', 0))
    if not n:
        return HttpResponse("не указан номер")

    log_message("dev%s reset from ip %s" % (n, us.ip), ttype="admin", user=us)
    path = '/addons/lxc-dev-auto/dev%s' % n
    path = settings.PROJECT_DIR + path
    cmd = ["touch", path]
    cmd = subprocess.check_output(cmd)

    ports = {1:[9923, 444], 2:[9924, 442], 3:[9925, 446], 4:[9926, 447], 5:[9927, 448]}
    message = "<pre>Virtual machine dev%s will be ready in 5 minutes.\n" % n
    message += "SSH пport: %s, WWW port: %s\n" % (ports[n][0], ports[n][1])
    message += "</pre>"
    ctx = {"us": us, "noga": 1, "message": message, 'back_button': True}

    return arender(request, "message.html", ctx)


def jam(request, city_name):
    us = get_user_settings(request)

    city = get_object_or_404(City, slug=city_name)
    ctx = {'us': us, 'city': city}
    return arender(request, "jam.html", ctx)


def ajax_jam(request):
    us = get_user_settings(request)

    city_id = request.GET.get('city_id')
    if not city_id:
        city = us.place
    else:
        try:
            city = cities_get()[int(city_id)]
        except: # city.active == False
            return HttpResponse('{}')

    busstops = []
    bus_ids = request.GET.get('bus_ids', [])

    if bus_ids:
        bus_ids = json.loads(bus_ids)
        bus_ids = [x for x in bus_ids if x]

    if not bus_ids:
        query = '''SELECT ARRAY_AGG(DISTINCT busstop_id) from bustime_route br WHERE br.bus_id IN (
            SELECT id FROM bustime_bus bb WHERE bb.city_id = %s
        );'''
        with connections['default'].cursor() as cursor:
            cursor.execute(query, [city.id])
            busstops = cursor.fetchall()[0][0] or []
    elif bus_ids:
        query = '''SELECT ARRAY_AGG(DISTINCT busstop_id) from bustime_route br WHERE br.bus_id IN %s;'''
        with connections['default'].cursor() as cursor:
            cursor.execute(query, [tuple(bus_ids)])
            busstops = cursor.fetchall()[0][0] or []

    result = get_jams_for_city(city, busstops)
    if not result:
        return HttpResponse('{}')

    return HttpResponse(ujson.dumps(result))

'''
https://nominatim.org/release-docs/develop/api/Overview/
'''
def ajax_nominatim(request, mode=None):
    us = get_user_settings(request)
    from six.moves.urllib.parse import urlencode
    try:
        url = settings.NOMINATIM_SERVER
        if mode:
            url = url + '/' + mode
        url = url + '/?' + urlencode(request.GET)
        # connect and the read timeouts
        r = requests.get(url, timeout=(1, 10))
        response = r.content
        if mode == 'search':
            metric('api_nominatim_search')
        elif mode == 'reverse':
            metric('api_nominatim_reverse')
        elif mode == 'lookup':
            metric('api_nominatim_lookup')
        else:
            metric('api_nominatim')
    except Exception as ex:
        log_message(str(ex), ttype="ajax_nominatim", place=us.place)
        response = {"Exception": str(ex)}
    return HttpResponse(json.dumps(response, default=str), content_type='application/json')


def ajax_test_proxy(request):
    us = get_user_settings(request)
    method = request.GET.get('method')
    url = request.GET.get('url', "http://example.org/")
    timeout = int(request.GET.get('timeout', "5"))

    if method == "PROXIES":
        proxies = PROXIES
    else:
        proxies = get_dyn_proxy()

    result = {"url": url, "status_code": ''}

    try:
        t = requests.get(url, proxies=proxies, timeout=timeout)
        if t:
            result["status_code"] = t.status_code
        else:
            result["status_code"] = ""
            result["error"] = "Timeout"
    except ConnectionError as ex:
        result["error"] = str(ex)
    except Exception as ex:
        result["error"] = str(ex)

    return HttpResponse(ujson.dumps(result))


def ajax_citynews_watched(request):
    us = get_user_settings(request)
    cn_id = request.GET.get('cn_id')
    cc_key = 'citynews_%s_watched' % cn_id
    try:
        news = CityNews.objects.get(id=cn_id)
        dt = news.etime - news.city.now
        is_exist = REDIS.exists(cc_key)
        REDIS_W.sadd(cc_key, us.id)
        if not is_exist:
            secs = int(dt.total_seconds() + 60)
            REDIS_W.expire(cc_key, secs)
    except CityNews.DoesNotExist:
        pass
    return HttpResponse("")


def find_trips(request, on_map=None):
    trips = []
    result = []
    error = None
    route_title = None

    # city = get_object_or_404(City, slug=city_name)

    stop_from = request.GET.get('stop_from', None)
    stop_to = request.GET.get('stop_to', None)

    try:
        if not stop_from:
            raise ValidationError(_('Отсутствует начало маршрута'))
        elif not stop_to:
            raise ValidationError(_('Отсутствует конец маршрута'))
        busstop_from = Unistop.objects.filter(id=int(stop_from))
        if not busstop_from:
            raise ValidationError(_('Остановка "%s" не найдена' % stop_from))
        busstop_to = Unistop.objects.filter(id=int(stop_to))
        if not busstop_to:
            raise ValidationError(_('Остановка "%s" не найдена' % stop_to))

        busstop_from = busstop_from.first()
        busstop_to = busstop_to.first()
        cc_key = "trips_%s_%s" % (busstop_from.id, busstop_to.id)  # trips_4_50639_69832
        trips = rcache_get(cc_key, [])
        route_title = rcache_get("%s_title" % cc_key)

        if not trips:
            try:
                result = list(find_routes_with_times(busstop_from.id, busstop_to.id))
            except ValueError:
                raise ValidationError(_("Маршрут не найден"))
            if not result:
                raise ValidationError(_("Маршрут <b>{} - {}</b> не найден".format(busstop_from.name, busstop_to.name)))
            else:
                for variant in result:
                    var = list(variant)
                    route_len = 0
                    obj = {}
                    obj['peresadka'] = 0
                    obj['transfer'] = 0
                    obj['variant_time'] = 0
                    obj['segments'] = var

                    for segment in var:
                        route_len += segment['distance']    # полный путь
                        # время
                        stime = int(round(segment['time'] / 1000, 0))  # время в миллисекундах => в секундах

                        seconds, milliseconds = divmod(segment['time'], 1000)  # время в миллисекундах => в секундах
                        minutes, seconds = divmod(seconds, 60)
                        hours, minutes = divmod(minutes, 60)
                        obj['variant_time'] += int(stime / 60)    # полное время

                        # время отрезка - в текст
                        if hours:
                            segment['time_s'] = "%s ч. %s мин." % (hours, minutes)
                        else:
                            segment['time_s'] = "%s мин." % minutes

                        if segment['type'] == "foot":
                            segment['icon'] = "/static/img/Union.png"
                        elif segment['type'] == "bus":
                            obj['peresadka'] += 1
                            obj['transfer'] += 1
                            bus = bus_get(segment['bus_id'])

                            segment['bus_name'] = bus.name
                            if segment['direction'] == 0 and bus.napr_a:
                                try:
                                    segment['direction_s'] = bus.napr_a.split('-')[1].strip()
                                except:
                                    continue
                            elif bus.napr_b:
                                try:
                                    segment['direction_s'] = bus.napr_b.split('-')[1].strip()
                                except:
                                    continue

                            if bus.ttype == 1:
                                segment['icon'] = "/static/img/trollbus_route.png"
                            elif bus.ttype == 2:
                                segment['icon'] = "/static/img/tram_route.png"
                            elif bus.ttype == 3:
                                segment['icon'] = "/static/img/taxi_route.png"
                            elif bus.ttype == 7:
                                segment['icon'] = "/static/img/metro_route.png"
                            else:
                                segment['icon'] = "/static/img/bus_route.png"
                        else:
                            segment['icon'] = "/static/img/bus_route.png"
                    # for segment in variant

                    if obj['variant_time'] < 60:
                        obj['title'] = '%s мин.' % obj['variant_time']
                    elif obj['variant_time'] % 60:
                        obj['title'] = '%d ч. %d мин.' % (obj['variant_time'] / 60, obj['variant_time'] % 60)
                    else:
                        obj['title'] = '%d ч.' % (obj['variant_time'] / 60)

                    if obj['peresadka'] > 0:
                        obj['peresadka'] -= 1
                    if obj['peresadka'] == 0:
                        obj['peresadka'] = 'Без пересадок'
                    elif obj['peresadka'] in [1, 21, 31, 41, 51, 61, 71, 81, 91, 101]:
                        obj['peresadka'] = '%s пересадка' % obj['peresadka']
                    elif obj['peresadka'] in [2,3,4]:
                        obj['peresadka'] = '%s пересадки' % obj['peresadka']
                    else:
                        obj['peresadka'] = '%s пересадок' % obj['peresadka']

                    trips.append(obj)
                # for variant in result

                if route_len > 1000:
                    route_title = 'Маршрут ~%.1f км.' % (route_len / 1000)
                else:
                    route_title = 'Маршрут ~%.0f м.' % route_len

                trips = sorted(trips, key=lambda t: (t['transfer'], t['variant_time']))
                rcache_set(cc_key, trips, 60)
                rcache_set("%s_title" % cc_key, route_title, 60)
    except ValidationError as e:
        error = e.message
    except Exception as e:
        error = str(e)
    finally:
        taxi_path = {}
        trip = int(request.GET.get('trip', '-1'))
        if trip >= 0 and trip < len(trips):
            trip = trips[trip]
            trip['distance'] = 0
            if len(trip['segments']) > 0 and len(trip['segments'][-1]['stops']) > 0:
                trip['end'] = trip['segments'][-1]['stops'][-1]
                for segment in trip['segments']:
                    trip['distance'] += segment['distance']
                trip['distance'] = round(trip['distance'] / 1000, 1)    # км.
            else:
                trip['end'] = ''
        else:
            trip = None
            # для такси (попутчика)
            if trips:
                rcache_set("trips_%s" % request.user.id, trips, 3600)   # такое же время, как у куки taxi_path (form_to3.html, request_bus_trip())

            s1 = NBusStop.objects.filter(unistop_id=stop_from).first()
            s2 = NBusStop.objects.filter(unistop_id=stop_to).first()
            if s1 and s2:
                path = get_paths_from_busstops([s1, s2], 'car')
                if path:
                    path = path[0]
                    taxi_path['wf'] = {'address': s1.name, 'point': [s1.point.x, s1.point.y], 'id': s1.id}
                    taxi_path['wh'] = {'address': s2.name, 'point': [s2.point.x, s2.point.y], 'id': s2.id}
                    taxi_path['geojson'] = path['points']
                    taxi_path['distance'] = round(path['distance'] / 1000, 1)    # км.
                    stime = int(round(int(path['time']) / 1000 / 60, 0))  # время в миллисекундах => в минутах
                    if stime < 60:
                        taxi_path['time'] = '%s мин.' % stime
                    elif stime % 60:
                        taxi_path['time'] = '%dч.%dмин.' % (stime / 60, stime % 60)
                    else:
                        taxi_path['time'] = '%d ч.' % (stime / 60)
                    rcache_set("taxi_path_%s" % request.user.id, taxi_path, 3600)
                # if path
            # if s1 and s2
        # else if trip >= 0 and trip < len(trips)

        us = get_user_settings(request)

        ctx = {
            'stop_from': stop_from,
            'stop_to': stop_to,
            'error': error,
            'result': result,
            'route_title': route_title,
            'trips': trips,
            'trip': trip,
            'taxiuser': taxiuser_get(request.user.id),
            'taxi_path': taxi_path,
            'us': us
        }

        if on_map:
            if trips:
                return trips[0]
            else:
                return False

        if request.GET.get('json'):
            # html для вывода на страницу (чтоб не рисовать в JS)
            ctx["html"] = TemplateResponse(request, 'from-to4.html', ctx).rendered_content.replace('\n', '').replace('  ', '')
            return HttpResponse(json.dumps(ctx, default=str, ensure_ascii=False), content_type='application/json')
        else:
            # for index-menu:
            country = us.country or us.city.country
            ctx.update({
                'avg_temp': avg_temp(us.city),
                "weather": weather_detect(us.city),
                "btc_rub": get_btc(),
                "avg_jam_ratio": rcache_get('avg_jam_ratio__%s' % us.city.id, 0),
                "real_error": us.city.real_error(),
                "transaction": get_transaction(us),
                "cities": [x for x in cities_get(as_list=True, country=country) if x.available],
                "tcard": tcard_get(us.tcard, us.city)
            })
            return arender(request, "from-to2.html", ctx)



def busstops_trip(request, city_name, on_map=None):
    trips = []
    result = []
    error = None
    route_title = None

    city = get_object_or_404(City, slug=city_name)

    stop_from = request.GET.get('stop_from', None)
    stop_to = request.GET.get('stop_to', None)

    try:
        if not stop_from:
            raise ValidationError(_('Отсутствует начало маршрута'))
        elif not stop_to:
            raise ValidationError(_('Отсутствует конец маршрута'))

        busstop_from = VBusStop.objects.filter(name=stop_from, city=city)
        if not busstop_from:
            raise ValidationError(_('Остановка "%s" не найдена' % stop_from))
        busstop_to = VBusStop.objects.filter(name=stop_to, city=city)
        if not busstop_to:
            raise ValidationError(_('Остановка "%s" не найдена' % stop_to))

        busstop_from = busstop_from.first()
        busstop_to = busstop_to.first()
        cc_key = "trips_%s_%s_%s" % (city.id, busstop_from.id, busstop_to.id)  # trips_4_50639_69832
        trips = rcache_get(cc_key, [])
        route_title = rcache_get("%s_title" % cc_key)

        if not trips:
            graph = get_city_graph(city.id)
            if not graph:
                msg_err = _("Нет графа маршрутов города %s" % city.name)  # python utils/fill_cities_route_graphs.py -c CITY_ID
                if request.user.is_staff:
                    msg_err = "%s<br>%s 'python utils/fill_gt_route_graphs.py -c %s' %s" % (
                        msg_err, _("Выполните"), city.id, _("для расчета графов"))
                raise ValidationError(msg_err)
            try:
                result = list(find_routes_with_times(graph, city.id, busstop_from.id, busstop_to.id))
            except ValueError:
                raise ValidationError(_("Маршрут не найден"))
            if not result:
                raise ValidationError(_("Маршрут <b>{} - {}</b> не найден".format(busstop_from.name, busstop_to.name)))
            else:
                for variant in result:
                    var = list(variant)
                    route_len = 0
                    obj = {}
                    obj['peresadka'] = 0
                    obj['transfer'] = 0
                    obj['variant_time'] = 0
                    obj['segments'] = var

                    for segment in var:
                        route_len += segment['distance']    # полный путь
                        # время
                        stime = int(round(segment['time'] / 1000, 0))  # время в миллисекундах => в секундах

                        seconds, milliseconds = divmod(segment['time'], 1000)  # время в миллисекундах => в секундах
                        minutes, seconds = divmod(seconds, 60)
                        hours, minutes = divmod(minutes, 60)
                        obj['variant_time'] += int(stime / 60)    # полное время

                        # время отрезка - в текст
                        if hours:
                            segment['time_s'] = "%s ч. %s мин." % (hours, minutes)
                        else:
                            segment['time_s'] = "%s мин." % minutes

                        if segment['type'] == "foot":
                            segment['icon'] = "/static/img/Union.png"
                        elif segment['type'] == "bus":
                            obj['peresadka'] += 1
                            obj['transfer'] += 1
                            bus = bus_get(segment['bus_id'])

                            segment['bus_name'] = bus.name
                            if segment['direction'] == 0 and bus.napr_a:
                                segment['direction_s'] = bus.napr_a.split('-')[1].strip()
                            elif bus.napr_b:
                                segment['direction_s'] = bus.napr_b.split('-')[1].strip()

                            if bus.ttype == 1:
                                segment['icon'] = "/static/img/trollbus_route.png"
                            elif bus.ttype == 2:
                                segment['icon'] = "/static/img/tram_route.png"
                            elif bus.ttype == 3:
                                segment['icon'] = "/static/img/taxi_route.png"
                            elif bus.ttype == 7:
                                segment['icon'] = "/static/img/metro_route.png"
                            else:
                                segment['icon'] = "/static/img/bus_route.png"
                        else:
                            segment['icon'] = "/static/img/bus_route.png"
                    # for segment in variant

                    if obj['variant_time'] < 60:
                        obj['title'] = '%s мин.' % obj['variant_time']
                    elif obj['variant_time'] % 60:
                        obj['title'] = '%d ч. %d мин.' % (obj['variant_time'] / 60, obj['variant_time'] % 60)
                    else:
                        obj['title'] = '%d ч.' % (obj['variant_time'] / 60)

                    if obj['peresadka'] > 0:
                        obj['peresadka'] -= 1
                    if obj['peresadka'] == 0:
                        obj['peresadka'] = 'Без пересадок'
                    elif obj['peresadka'] in [1, 21, 31, 41, 51, 61, 71, 81, 91, 101]:
                        obj['peresadka'] = '%s пересадка' % obj['peresadka']
                    elif obj['peresadka'] in [2,3,4]:
                        obj['peresadka'] = '%s пересадки' % obj['peresadka']
                    else:
                        obj['peresadka'] = '%s пересадок' % obj['peresadka']

                    trips.append(obj)
                # for variant in result

                if route_len > 1000:
                    route_title = 'Маршрут ~%.1f км.' % (route_len / 1000)
                else:
                    route_title = 'Маршрут ~%.0f м.' % route_len

                trips = sorted(trips, key=lambda t: (t['transfer'], t['variant_time']))
                rcache_set(cc_key, trips, 60)
                rcache_set("%s_title" % cc_key, route_title, 60)
    except ValidationError as e:
        error = e.message
    except Exception as e:
        error = str(e)
    finally:
        taxi_path = {}
        trip = int(request.GET.get('trip', '-1'))
        if trip >= 0 and trip < len(trips):
            trip = trips[trip]
            trip['distance'] = 0
            if len(trip['segments']) > 0 and len(trip['segments'][-1]['stops']) > 0:
                trip['end'] = trip['segments'][-1]['stops'][-1]
                for segment in trip['segments']:
                    trip['distance'] += segment['distance']
                trip['distance'] = round(trip['distance'] / 1000, 1)    # км.
            else:
                trip['end'] = ''
        else:
            trip = None
            # для такси (попутчика)
            if trips:
                rcache_set("trips_%s" % request.user.id, trips, 3600)   # такое же время, как у куки taxi_path (form_to3.html, request_bus_trip())

            s1 = NBusStop.objects.filter(name=stop_from, city=city).first()
            s2 = NBusStop.objects.filter(name=stop_to, city=city).first()
            if s1 and s2:
                path = get_paths_from_busstops([s1, s2], 'car')
                if path:
                    path = path[0]
                    taxi_path['wf'] = {'address': s1.name, 'point': [s1.point.x, s1.point.y], 'id': s1.id}
                    taxi_path['wh'] = {'address': s2.name, 'point': [s2.point.x, s2.point.y], 'id': s2.id}
                    taxi_path['geojson'] = path['points']
                    taxi_path['distance'] = round(path['distance'] / 1000, 1)    # км.
                    stime = int(round(int(path['time']) / 1000 / 60, 0))  # время в миллисекундах => в минутах
                    if stime < 60:
                        taxi_path['time'] = '%s мин.' % stime
                    elif stime % 60:
                        taxi_path['time'] = '%dч.%dмин.' % (stime / 60, stime % 60)
                    else:
                        taxi_path['time'] = '%d ч.' % (stime / 60)
                    rcache_set("taxi_path_%s" % request.user.id, taxi_path, 3600)
                # if path
            # if s1 and s2
        # else if trip >= 0 and trip < len(trips)

        us = get_user_settings(request)
        tevents = rcache_get("tevents_%s" % us.city.id, {})

        ctx = {
            'stop_from': stop_from,
            'stop_to': stop_to,
            'error': error,
            'result': result,
            'route_title': route_title,
            'trips': trips,
            'trip': trip,
            'taxiuser': taxiuser_get(request.user.id),
            'taxi_path': taxi_path,
            "tevents": tevents.values(),
            'us': us
        }

        if on_map:
            if trips:
                return trips[0]
            else:
                return False

        if request.GET.get('json'):
            # html для вывода на страницу (чтоб не рисовать в JS)
            ctx["html"] = TemplateResponse(request, 'from-to4.html', ctx).rendered_content.replace('\n', '').replace('  ', '')
            return HttpResponse(json.dumps(ctx, default=str, ensure_ascii=False), content_type='application/json')
        else:
            # for index-menu:
            country = us.country or us.city.country
            ctx.update({
                'avg_temp': avg_temp(us.city),
                "weather": weather_detect(us.city),
                "btc_rub": get_btc(),
                "avg_jam_ratio": rcache_get('avg_jam_ratio__%s' % us.city.id, 0),
                "real_error": us.city.real_error(),
                "transaction": get_transaction(us),
                "cities": [x for x in cities_get(as_list=True, country=country) if x.available],
                "tcard": tcard_get(us.tcard, us.city),
            })
            return arender(request, "from-to2.html", ctx)


def bus_trip(request, city_name):
    def is_similar(items1, items2):
        if len(items1) != len(items2):
            return False
        values1 = list([item['bus_id'] for item in items1 if item.get('bus_id', None)])
        values2 = list([item['bus_id'] for item in items2 if item.get('bus_id', None)])
        if len(values1) != len(values2):
            return False
        return all(ids[0] == ids[1] for ids in zip(values1, values2))
    # def is_similar

    error = None
    result = []
    trips = []
    route_title = None

    city = get_object_or_404(City, slug=city_name)


    stop_from = request.GET.get('stop_from', None)
    stop_to = request.GET.get('stop_to', None)
    if not stop_from:
        error = _('Отсутствует начало маршрута')
    elif not stop_to:
        error = _('Отсутствует конец маршрута')

    if not error:
        busstop_from = VBusStop.objects.filter(name=stop_from, city=city)
        if not busstop_from:
            error = _('Остановка "%s" не найдена' % stop_from)

    if not error:
        busstop_to = VBusStop.objects.filter(name=stop_to, city=city)
        if not busstop_to:
            error = _('Остановка "%s" не найдена' % stop_to)

    if not error:
        busstop_from = busstop_from[0]
        busstop_to = busstop_to[0]
        cc_key = "trips_%s_%s_%s" % (city.id, busstop_from.id, busstop_to.id)   # trips_4_50639_69832
        trips = rcache_get(cc_key, [])
        route_title = rcache_get("%s_title" % cc_key)

    if (not error) and (not trips):
        di_graph = REDIS.get("nx__di_graph__%s" % city.id)
        if not di_graph:
            error = _("Нет графа маршрутов города %s" % city.name)  # python utils/fill_cities_route_graphs.py -c CITY_ID
            if request.user.is_staff:
                error = "%s<br>%s 'python utils/fill_cities_route_graphs.py -c %s' %s" % (error, _("Выполните"), city.id, _("для рассчета графов"))
        else:
            try:
                G = pickle.loads(di_graph)  # if: __new__() missing 1 required positional argument: 'bus_id'
                #                             do: python utils/fill_cities_route_graphs.py --city=<CITY_ID>
                paths_1 = all_shortest_paths(G, busstop_from.name, busstop_to.name, weight='weight')
                paths_2 = all_shortest_paths(G, busstop_from.name, busstop_to.name, weight='walk_weight')
                unique_paths = collections.OrderedDict()
                paths = itertools.chain(paths_1, paths_2)
                for path in paths:  # Target ... cannot be reached from Source ...
                    keys = frozenset([item.bus_id for item in path if isinstance(item, RouteNode)])
                    if not unique_paths.get(keys, None) \
                            and not any(keys.issuperset(k) for k in unique_paths.keys()):
                        unique_paths.setdefault(keys, path)
            except nx.NetworkXNoPath as e:
                error = _("Маршрут <b>{} - {}</b> не найден".format(busstop_from.name, busstop_to.name))
            except nx.NodeNotFound as e:
                error = _("Остановка не найдена")
            except Exception as ex:
                error = str(ex)

    if (not error) and (not trips):
        try:
            paths = unique_paths.values()
            for path in paths:
                result_route = []
                # Фильтруем остановки вне маршрутов
                busstops = list(filter(lambda x: isinstance(x, str), path))
                # Фильтруем остановки входящие в маршруты
                route_stops = filter(lambda x: isinstance(x, RouteNode), path)
                # Делаем запрос в БД и формируем словарь для удобного получения инфомации по всем остановкам
                busstops = busstops + list(map(lambda x: x.name, route_stops))
                stops = NBusStop.objects.filter(name__in=busstops, city=city)
                stops = dict([(stop.name, stop) for stop in stops])
                head, *tail = path
                while tail:
                    # Остановки в маршрутах и без. Могут дублироваться. Для построения нитей это не удобно, поэтому исключаем повторы
                    if isinstance(head, str) and isinstance(tail[0], RouteNode):
                        index = 1
                        if head != tail[0].name:
                            item = next((x for x in tail if isinstance(x, RouteNode) and x.name == head), None)
                            index = 1 if not item else tail.index(item)
                        head, tail = tail[index], tail[index+1:]
                    # Считаем маршруты на автобусе через графхоппер
                    elif isinstance(head, RouteNode):
                        route_id, nbusstop_id, name, direction, bus = head
                        if bus_get(int(bus)):
                            item = next((x for x in tail if not isinstance(x, RouteNode)), None)
                            index = tail.index(item)
                            item = tail[index - 1]
                            route_stops = [head]
                            route_stops.extend(tail[:index])
                            bus_stops = [stops[stop.name] for stop in route_stops]
                            path = next(iter(get_paths_from_busstops(bus_stops, 'car') or []), None)
                            if not path:
                                break
                            route_time = sum(res['time'] for res in result_route) * 0.001 or 0
                            time_bst_ts = next(filter(lambda t: t and t > datetime.datetime.timestamp(city.now) + route_time, rcache_get("time_bst_ts_%s" % city.id, {}).get(bus, {}).values()), 0)
                            time_bst = datetime.datetime.fromtimestamp(time_bst_ts).strftime("%H:%M") if time_bst_ts > 0 else ''
                            result_route.append({"type": "bus", "bus_id": bus, "direction": direction, "distance": path['distance'],
                                                "time": path['time'] + path['time'], "time_bst_ts": time_bst_ts, "time_bst": time_bst, "stops": [stop.name for stop in route_stops]})
                        head, tail = tail[index], tail[index+1:]
                    # Считаем маршруты пешком через графхоппер
                    elif isinstance(head, str) and isinstance(tail[0], str):
                        foot_stops = [stops[head], stops[tail[0]]]
                        path = get_paths_from_busstops(foot_stops, 'foot')[0]
                        distance = path['distance']
                        time = path['time']
                        result_route.append({"type": "foot", "distance": path['distance'], "time": path['time'], "stops": [head, tail[0]]})
                        head, *tail = tail
                    else:
                        head, *tail = tail
                # while tail

                if result_route and not list(filter(partial(is_similar, result_route), result)):
                    result.append(result_route)
            # for path in paths
        except Exception as ex:
            error = str(ex)

        if not result:
            error = _("Маршрут <b>{} - {}</b> не найден".format(busstop_from.name, busstop_to.name))
        else:
            for variant in result:
                route_len = 0
                obj = {}
                obj['peresadka'] = 0
                obj['variant_time'] = 0
                for segment in variant:
                    route_len += segment['distance']    # полный путь
                    # время
                    stime = int(round(segment['time'] / 1000, 0))  # время в миллисекундах => в секундах

                    seconds, milliseconds = divmod(segment['time'], 1000)  # время в миллисекундах => в секундах
                    minutes, seconds = divmod(seconds, 60)
                    hours, minutes = divmod(minutes, 60)
                    obj['variant_time'] += int(stime / 60)    # полное время

                    # время отрезка - в текст
                    if hours:
                        segment['time_s'] = "%s ч. %s мин." % (hours, minutes)
                    else:
                        segment['time_s'] = "%s мин." % minutes

                    if segment['type'] == "foot":
                        segment['icon'] = "/static/img/Union.png"
                    elif segment['type'] == "bus":
                        obj['peresadka'] += 1
                        bus = bus_get(segment['bus_id'])

                        segment['bus_name'] = bus.name
                        if segment['direction'] == 0 and bus.napr_a:
                            segment['direction_s'] = bus.napr_a.split('-')[1].strip()
                        elif bus.napr_b:
                            segment['direction_s'] = bus.napr_b.split('-')[1].strip()

                        if bus.ttype == 1:
                            segment['icon'] = "/static/img/trollbus_route.png"
                        elif bus.ttype == 2:
                            segment['icon'] = "/static/img/tram_route.png"
                        elif bus.ttype == 3:
                            segment['icon'] = "/static/img/taxi_route.png"
                        else:
                            segment['icon'] = "/static/img/bus_route.png"
                    else:
                        segment['icon'] = "/static/img/bus_route.png"
                # for segment in variant

                if obj['variant_time'] < 60:
                    obj['title'] = '%s мин.' % obj['variant_time']
                elif obj['variant_time'] % 60:
                    obj['title'] = '%d ч. %d мин.' % (obj['variant_time'] / 60, obj['variant_time'] % 60)
                else:
                    obj['title'] = '%d ч.' % (obj['variant_time'] / 60)

                if obj['peresadka'] > 0:
                    obj['peresadka'] -= 1
                if obj['peresadka'] == 0:
                    obj['peresadka'] = 'Без пересадок'
                elif obj['peresadka'] in [1, 21, 31, 41, 51, 61, 71, 81, 91, 101]:
                    obj['peresadka'] = '%s пересадка' % obj['peresadka']
                elif obj['peresadka'] in [2,3,4]:
                    obj['peresadka'] = '%s пересадки' % obj['peresadka']
                else:
                    obj['peresadka'] = '%s пересадок' % obj['peresadka']

                obj['segments'] = variant

                trips.append(obj)
            # for variant in result

            if route_len > 1000:
                route_title = 'Маршрут ~%.1f км.' % (route_len / 1000)
            else:
                route_title = 'Маршрут ~%.0f м.' % route_len

            rcache_set(cc_key, trips, 60)
            rcache_set("%s_title" % cc_key, route_title, 60)
        # else if not result
    # if (not error) and (not trips)


    taxi_path = {}
    trip = int(request.GET.get('trip', '-1'))
    if trip >= 0 and trip < len(trips):
        trip = trips[trip]
        trip['distance'] = 0
        if len(trip['segments']) > 0 and len(trip['segments'][-1]['stops']) > 0:
            trip['end'] = trip['segments'][-1]['stops'][-1]
            for segment in trip['segments']:
                trip['distance'] += segment['distance']
            trip['distance'] = round(trip['distance'] / 1000, 1)    # км.
        else:
            trip['end'] = ''
    else:
        trip = None
        # для такси (попутчика)
        if trips:
            rcache_set("trips_%s" % request.user.id, trips, 3600)   # такое же время, как у taxi_path

        s1 = NBusStop.objects.filter(name=stop_from, city=city).first()
        s2 = NBusStop.objects.filter(name=stop_to, city=city).first()
        if s1 and s2:
            path = get_paths_from_busstops([s1, s2], 'car')
            if path:
                path = path[0]
                taxi_path['wf'] = {'address': s1.name, 'point': [s1.point.x, s1.point.y], 'id': s1.id}
                taxi_path['wh'] = {'address': s2.name, 'point': [s2.point.x, s2.point.y], 'id': s2.id}
                taxi_path['geojson'] = path['points']
                taxi_path['distance'] = round(path['distance'] / 1000, 1)    # км.
                stime = int(round(int(path['time']) / 1000 / 60, 0))  # время в миллисекундах => в минутах
                if stime < 60:
                    taxi_path['time'] = '%s мин.' % stime
                elif stime % 60:
                    taxi_path['time'] = '%dч.%dмин.' % (stime / 60, stime % 60)
                else:
                    taxi_path['time'] = '%d ч.' % (stime / 60)
                rcache_set("taxi_path_%s" % request.user.id, taxi_path, 3600)
            # if path
        # if s1 and s2
    # else if trip >= 0 and trip < len(trips)

    us = get_user_settings(request)
    tevents = rcache_get("tevents_%s" % us.place_id, {})

    ctx = {
        'stop_from': stop_from,
        'stop_to': stop_to,
        'error': error,
        'route_title': route_title,
        'trips': trips,
        'trip': trip,
        'taxiuser': taxiuser_get(request.user.id),
        'taxi_path': taxi_path,
        "tevents": tevents.values(),
        'us': us,
    }

    if request.GET.get('json'):
        # html для вывода на страницу (чтоб не рисовать в JS)
        ctx["html"] = TemplateResponse(request, 'from-to4.html', ctx).rendered_content.replace('\n', '').replace('  ', '')
        return HttpResponse(json.dumps(ctx, default=str, ensure_ascii=False), content_type='application/json')
    else:
        # for index-menu:
        #country = us.country or us.city.country
        ctx.update({
            'avg_temp': avg_temp(us.place),
            "weather": weather_detect(us.place),
            "btc_rub": get_btc(),
            "avg_jam_ratio": rcache_get('avg_jam_ratio__%s' % us.place.id, 0),
            "real_error": False,    #us.city.real_error(),
            "transaction": get_transaction(us),
            "cities": [],   #[x for x in cities_get(as_list=True, country=country) if x.available],
            "tcard": tcard_get(us.tcard, PLACE_TRANSPORT_CARD.get(us.place.id)),
        })
        return arender(request, "from-to2.html", ctx)
# bus_trip


def chat_web(request, city_name = None, bus_slug = None):
    place = get_object_or_404(Place, slug=city_name)
    us = get_user_settings(request)

    bus = None

    if bus_slug: #чат конкретного маршрута
        try:
            chat = Chat.objects.filter(bus__slug=bus_slug, bus__places__id=place.id).order_by("-ctime")
            bus = Bus.objects.get(slug=bus_slug, places__id=place.id)
        except:
            chat = []
    else: #городской чат
        try:
            chat = Chat.objects.filter(bus__places__id=place.id).order_by("-ctime")
        except:
            chat = []

    #пагинатор для вывода по 30 постов при скролинге
    paginator = Paginator(chat, 30)
    first_page = paginator.page(1).object_list
    page_range = paginator.page_range

    if request.method == 'POST':
        page_n = request.POST.get('page_n', None)
        try:
            results = list(paginator.page(page_n).object_list.values('id', 'bus__slug', 'ctime', 'photo', 'name', 'message'))
            for r in results:
                r['ctime'] = r['ctime'].strftime('%d.%m.%y %H:%M')
        except:
            results = {}
        return HttpResponse(json.dumps(results))

    us.place = place
    us.save()

    ctx = {"us": us, "place": place, "bus_slug": bus_slug, "first_page": first_page, "bus": bus}
    return arender(request, "chat.html", ctx)


def ajax_chat_message(request):
    us = get_user_settings(request)
    text_message = request.GET.get("text_message")
    bus_slug = request.GET.get("bus_slug")
    lang = us.language

    if not text_message:
        return HttpResponse("ошибка 'No text'")
    else:
        try:
            bus = Bus.objects.get(slug=bus_slug, places__id=us.place.id)
            if us.user.first_name:
                name = us.user.first_name
            else:
                name = "Без имени"
            chat = Chat.objects.create(bus=bus, us=us, name=name, message=text_message)

            msg = chat_format_msg(chat, lang=lang)
            msgb = chat_format_msg(chat, extra={"bus_id": chat.bus_id}, lang=lang)
            fill_chat_cache(bus.id, force=True)
            fill_chat_city_cache(us.place.id, force=True)

            msg["ctime"] = chat.ctime.strftime('%d.%m.%y %H:%M')
            msgb["ctime"] = chat.ctime.strftime('%d.%m.%y %H:%M')

            sio_pub("ru.bustime.chat__%s" % (bus.id), {"chat": msg})
            sio_pub("ru.bustime.chat_city__%s" % (us.place.id), {"chat": msgb})

            return HttpResponse("")
        except:
            return HttpResponse("ошибка")


def censored(request, city_name, page=None):
    place = get_object_or_404(Place, slug=city_name)
    us = get_user_settings(request)

    photo = []

    #папки, в которых хранятся фотки, присылаемые пользователями
    paths = ['/bustime/bustime/uploads/', '/bustime/bustime/static/img/si/']
    for path in paths:
        for address, dirs, files in os.walk(path):
            for name in files:
                ph = os.path.join(address, name) #извлекаем имя каждого файла
            photo.append(ph) #добавляем это имя в список, где будут все имена файлов из всех папок

    if photo:
        photo_with_date = [[x, os.path.getctime(x)] for x in photo] #делаем список "фотка\дата ее последнего изменения"
        sorted_photo = sorted(photo_with_date, key=lambda x: x[1], reverse=True) #сортируем фото по дате последнего изменения
        del sorted_photo[499:-1] #берем первые 500 фоток
        #добавляем ссылку на фото в виде, в котором фото сможет отобразиться на сайте и дату его последнего изменения приводим в нормальный вид
        for sp in sorted_photo:
            sp[0] = sp[0].replace('/bustime/bustime/uploads/', '/static/uploads/').replace('/bustime/bustime/static/img/si/', '/static/img/si/')
            sp[1] = time.ctime(sp[1])

    #пагинатор с 100 фотками на страницк
    paginator = Paginator(sorted_photo, 100)
    if request.GET.get('page'):
        return HttpResponsePermanentRedirect(u"./page-%s/" % request.GET.get('page'))
    try:
        sorted_photo = paginator.page(page)
    except PageNotAnInteger:
        sorted_photo = paginator.page(1)
    except EmptyPage:
        sorted_photo = paginator.page(paginator.num_pages)

    ctx = {'us': us, 'place': place, 'page': page, 'photo': sorted_photo}
    return arender(request, "censored.html", ctx)

def ajax_censored(request):
    us = get_user_settings(request)
    dir_photo = request.GET.get("dir_photo")

    if not dir_photo:
        return HttpResponse("ошибка")
    else:
        try:
            if dir_photo.startswith('/static/uploads/'):
                dir_photo = dir_photo.replace('/static', '')
            elif dir_photo.startswith('/static/img/'):
                #удаляем из папки {settings.PROJECT_DIR}/bustime/static/img/si/
                os.remove(settings.PROJECT_DIR + "/bustime" + dir_photo)
                if settings.MASTER_HOSTNAME in ["s5", "s7"]:#удаление с s2
                    cmd = 'sudo -u linked_user ssh linked_user@%s -p 9922 "rm %s"' % (settings.DEFAULT_HOST, settings.PROJECT_DIR + "/bustime" + dir_photo)
                    os.system(cmd)

            os.remove(settings.PROJECT_DIR + dir_photo)#удаляем из папки /bustime/bustime/static/img/si/, либо из /bustime/bustime/uploads/
            if settings.MASTER_HOSTNAME in ["s5", "s7"]:#удаление с s2
                cmd = 'sudo -u linked_user ssh linked_user@%s -p 9922 "rm %s"' % (settings.DEFAULT_HOST, settings.PROJECT_DIR + dir_photo)
                os.system(cmd)
            return HttpResponse("")
        except:
            return HttpResponse("Такого файла нет")


def ajax_from_to(request):
    us = get_user_settings(request)
    address_from = request.GET.get("address_from")
    address_to = request.GET.get("address_to")
    stop_from = request.GET.get("stop_from")
    stop_to = request.GET.get("stop_to")
    transport = request.GET.get("transport")

    result = {}
    url = '%s/route?' % (settings.GH_SERVER)

    if stop_from and stop_to:# если тип транпорта автобус, то поиск по остановкам

        trip = find_trips(request, True) #находим путь между остановками
        if trip:
            result['type_transport'] = 'bus'
            all_stops_trip = []
            coords_stop_trip = []
            for t in trip['segments']: #достаем координаты остановок и их названия
                for s in t['stops_id_for_map']:
                    obj = {}
                    stop = NBusStop.objects.get(id=s)
                    obj['points'] = [stop.point.x, stop.point.y]
                    obj['name'] = stop.name
                    coords_stop_trip.append(obj['points'])
                    all_stops_trip.append(obj)
            result['all_stops_trip'] = all_stops_trip


            for c in coords_stop_trip:
                #coords_for_gh = c[1], c[0]
                url += 'point=%s,%s&' % (c[1], c[0])
            url += 'points_encoded=false&locale=ru-RU&profile=car&elevation=false&instructions=false&type=json'
        else:
            return HttpResponse("")

    elif address_from and address_to:#если тип транспорта машина\велосипед\пешком, то поиск по адресу
        result['type_transport'] = transport

        url += 'point=%s&point=%s&' % (address_from, address_to)

        if transport == "car":
            url += 'points_encoded=false&locale=ru-RU&profile=car&elevation=false&instructions=false&type=json'
        elif transport == "foot":
            url += 'points_encoded=false&locale=ru-RU&profile=foot&elevation=false&instructions=false&type=json'
        elif transport == "bike":
            url += 'points_encoded=false&locale=ru-RU&profile=bike&elevation=false&instructions=false&type=json'
    else:
        return HttpResponse("")

    try:
        r = requests.get(url, timeout=5)
    except:
        return HttpResponse("")

    try:
        js = r.json()
    except:
        return HttpResponse("")

    if not js.get('paths'):
        return HttpResponse("")

    paths = js['paths']
    points = paths[0]['points']
    result['coords'] = points['coordinates']

    return HttpResponse(json.dumps(result))

def ajax_all_stops_map(request):
    place_id = request.GET.get("us_city")
    place = next(iter(Place.objects.raw("""
        SELECT bp.id, bpa.geometry FROM bustime_place bp 
        INNER JOIN bustime_placearea bpa 
        ON (bp.osm_area_id = bpa.osm_id AND bp.osm_area_type = bpa.osm_type) 
        WHERE bp.id = %s
    """, (place_id,))), None)
    all_stops = []
    if place:
        all_stopss = NBusStop.objects.filter(point__within=place.geometry)
        for s in all_stopss:
            all_stops.append({'name': s.name, 'point_x': s.point.x, 'point_y': s.point.y, 'points': [s.point.x, s.point.y]})
    return HttpResponse(json.dumps(all_stops))

def ajax_stops_by_area(request):
    west = float(request.GET.get("west", 0))
    south = float(request.GET.get("south", 0))
    east = float(request.GET.get("east", 0))
    north = float(request.GET.get("north", 0))
    if not any((west, south, east, north)):
        return JsonResponse({
            "status": "error",
            "data": "Bad request parameters"
        })
    cx = cdistance(east, south, west, south)
    cy = cdistance(east, north, east, south)
    radius = min(int((cx ** 2 + cy ** 2) ** 0.5), 10000)
    x = (east + west) * 0.5
    y = (south + north) * 0.5
    sids = find_stop_ids_within(x, y, radius)
    all_stops = [dict(**{key: val for key, val in s.items() if key != "point"}, **{"x": s['point'].coords[0], "y": s['point'].coords[1]})
                    for s in NBusStop.objects.filter(id__in=sids).values("id", "name", "moveto", "point")]
    return JsonResponse({"radius": radius, "x": cx, "y": cy, "stops": all_stops})


def city_admin_load_gtfs(request, city_name=None):
    city = get_object_or_404(Place, slug=city_name)
    us = get_user_settings(request)

    data_tab = request.POST.get('data_tab', 'view')
    catalog_id = int(request.POST.get('catalog_id', '0'))

    date = datetime.datetime.now().date()
    feeds = GtfsCatalog.objects.all().order_by("id")
    if not catalog_id:
        catalog_id = feeds[0].id if feeds else None
    agency = GtfsAgency.objects.filter(catalog=catalog_id).order_by('agency_name')
    # только актуальные даты
    calendar = GtfsCalendar.objects.filter(Q(catalog=catalog_id)&Q(start_date__lte=date)&Q(end_date__gte=date))
    calendar_dates = GtfsCalendarDates.objects.filter(Q(catalog=catalog_id)&Q(date__gte=date))
    # маршруты первого агенства
    # если агенство в фиде единственное, то в полях agency_id файлов фида может быть NULL, подразумевая единственное агенство
    if len(agency) <= 1:
        routes = GtfsRoutes.objects.filter(catalog=catalog_id).filter(Q(agency_id=agency[0].agency_id)|Q(agency_id__isnull=True))
    else:
        routes = GtfsRoutes.objects.filter(catalog=catalog_id, agency_id=agency[0].agency_id)

    updaters = rcache_mget(REDIS.smembers("updaters"))
    updaters = [k for k in updaters if k is not None]
    updaters.sort(key=lambda k : k['src'])

    ctx = {
        'us': us,
        'city': city,
        'feeds': list(feeds),
        'agency': list(agency),
        'calendar': list(calendar.order_by('start_date')),
        'calendar_dates': list(calendar_dates.order_by('date', 'service_id')),
        'routes': list(routes.order_by('route_short_name', 'route_long_name')),
        'data_tab': data_tab,
        'catalog_id': catalog_id,
        'routes': routes,
        'updaters': [json.dumps(x,default=str,ensure_ascii=False,indent=3) for x in updaters],
    }

    if catalog_id:
        if data_tab == 'tools':
            feed = feeds.filter(id=catalog_id).first()
            if feed:
                ctx['url_schedule'] = feed.url_schedule
                ctx['url_rt_positions'] = feed.url_rt_positions

    return arender(request, "admin_load_gtfs.html", ctx)
# city_admin_load_gtfs


@csrf_exempt
def ajax_gtfs_get_feed(request):
    res = {
        "error": None,
        "result": {}
    }

    # https://gtfs.org/ru/schedule/reference/
    try:
        date = request.POST.get('date')
        if date:
            date = datetime.datetime.strptime(date, "%Y-%m-%d").date()
        else:
            date = datetime.datetime.now().date()

        catalog_id = int(request.POST.get('catalog_id'))

        agencyes = GtfsAgency.objects.filter(catalog=catalog_id)
        # только актуальные даты
        calendar = GtfsCalendar.objects.filter(Q(catalog=catalog_id)&Q(start_date__lte=date)&Q(end_date__gte=date))
        calendar_dates = GtfsCalendarDates.objects.filter(Q(catalog=catalog_id)&Q(date__gte=date))

        res["result"]["agencyes"] = list(agencyes.order_by('agency_name').values())
        res["result"]["calendar"] = list(calendar.order_by('start_date').values())
        res["result"]["calendar_dates"] = list(calendar_dates.order_by('date', 'service_id').values())

        if len(agencyes) == 0:
            # бывает, что агенств нет в фиде
            # выбрать маршруты, актуальные на дату
            weekday = date.weekday()    # day of the week as an integer, where Monday is 0 and Sunday is 6

            # сервисы действующие на указанную дату
            actual_services1 = GtfsCalendar.objects.filter(
                                    Q(catalog=catalog_id)
                                    &Q(start_date__lte=date) & Q(end_date__gte=date) # дата в промежутке start_date and end_date
                                    &Q(**{WEEK_DAYS[weekday]:1})                    # и день недели соостветствует дате
                                ).exclude(
                                    # и сервис не выключен в указанную дату
                                    service_id__in=Subquery(GtfsCalendarDates.objects.filter(catalog=catalog_id, date=date, exception_type=2).values('service_id').distinct('service_id'))
                                ).values('service_id').distinct('service_id')

            # исключения из расписания
            # сервисы добавленные на указанную дату и которых нет в actual_services1
            actual_services2 = GtfsCalendarDates.objects.filter(catalog=catalog_id, date=date, exception_type=1).exclude(catalog=catalog_id, service_id__in=actual_services1).values('service_id').distinct('service_id')

           	# union: сервисы действующие на указанную дату + сервисы добавленные на указанную дату
            actual_services = actual_services1.union(actual_services2)

            # все трипы на указанную дату
            actual_trips = GtfsTrips.objects.filter(catalog=catalog_id, service_id__in=actual_services)

            if len(actual_services) > 0:
                # маршруты, содержащие трипы актуальных сервисов
                routes = GtfsRoutes.objects.filter(catalog=catalog_id, route_id__in=Subquery(actual_trips.values('route_id').distinct('route_id')))
            else:
                # ещё и календарь кончился
                # выбрать все маршруты
                routes = GtfsRoutes.objects.filter(catalog=catalog_id)
            res["result"]["routes"] = list(routes.order_by('route_short_name', 'route_long_name').values())
        # if len(agencyes) == 0
    except:
        res["error"] = traceback.format_exc(limit=2)

    return HttpResponse(json.dumps(res, default=ser_gtfs))
#


# функция для сериализации таблиц gtfs
def ser_gtfs(obj):
    if isinstance(obj, Point):  # поле PointField
        return [obj.x, obj.y]   # [lon, lat]
    return str(obj)             # date, etc...
# ser_gtfs


@csrf_exempt
def ajax_gtfs_get_route(request):
    res = {
        "error": None,
        "result": {}
    }

    # https://gtfs.org/ru/schedule/reference/
    try:
        date = request.POST.get('date')
        catalog_id = int(request.POST.get('catalog_id'))

        # должен быть только один из этих параметров:
        agency_id = request.POST.get('agency')
        route_id = request.POST.get('route')

        if agency_id:
            agencyes_cnt = int(request.POST.get('agencyes_cnt', "0"))
            if date:
                date = datetime.datetime.strptime(date, "%Y-%m-%d").date()
                # выбрать маршруты агенства, актуальные на дату
                weekday = date.weekday()    # day of the week as an integer, where Monday is 0 and Sunday is 6
                # расписание
                # сервисы действующие на указанную дату
                actual_services1 = GtfsCalendar.objects.filter(
                                        Q(catalog=catalog_id)
                                        &Q(start_date__lte=date) & Q(end_date__gte=date) # дата в промежутке start_date and end_date
                                        &Q(**{WEEK_DAYS[weekday]:1})                    # и день недели соостветствует дате
                                    ).exclude(
                                        # и сервис не выключен в указанную дату
                                        service_id__in=Subquery(GtfsCalendarDates.objects.filter(catalog=catalog_id, date=date, exception_type=2).values('service_id').distinct('service_id'))
                                    ).values('service_id').distinct('service_id')

                # исключения из расписания
                # сервисы добавленные на указанную дату и которых нет в actual_services1
                actual_services2 = GtfsCalendarDates.objects.filter(catalog=catalog_id, date=date, exception_type=1).exclude(catalog=catalog_id, service_id__in=actual_services1).values('service_id').distinct('service_id')

               	# union: сервисы действующие на указанную дату + сервисы добавленные на указанную дату
                actual_services = actual_services1.union(actual_services2)

                # все трипы на указанную дату
                actual_trips = GtfsTrips.objects.filter(catalog=catalog_id, service_id__in=actual_services)

                # маршруты, содержащие трипы актуальных сервисов
                if agencyes_cnt <= 1:
                    routes = GtfsRoutes.objects.filter(catalog=catalog_id, route_id__in=Subquery(actual_trips.values('route_id').distinct('route_id'))).filter(Q(agency_id=agency_id)|Q(agency_id__isnull=True))
                else:
                    routes = GtfsRoutes.objects.filter(catalog=catalog_id, route_id__in=Subquery(actual_trips.values('route_id').distinct('route_id')), agency_id=agency_id)
            else:
                # выбрать все маршруты агенства
                if agencyes_cnt <= 1:
                    # если агенство в фиде единственное, то в полях agency_id файлов фида может быть NULL, подразумевая единственное агенство
                    routes = GtfsRoutes.objects.filter(catalog=catalog_id).filter(Q(agency_id=agency_id)|Q(agency_id__isnull=True))
                else:
                    routes = GtfsRoutes.objects.filter(catalog=catalog_id, agency_id=agency_id)

            res["result"]["routes"] = list(routes.order_by('route_short_name', 'route_long_name').values())

        elif route_id:
            if date:
                date = datetime.datetime.strptime(date, "%Y-%m-%d").date()
                # выбрать маршруты агенства, актуальные на дату
                weekday = date.weekday()    # day of the week as an integer, where Monday is 0 and Sunday is 6

                # сервисы действующие на указанную дату
                actual_services1 = GtfsCalendar.objects.filter(
                                        Q(catalog=catalog_id)
                                        &Q(start_date__lte=date) & Q(end_date__gte=date) # дата в промежутке start_date and end_date
                                        &Q(**{WEEK_DAYS[weekday]:1})                    # и день недели соостветствует дате
                                    ).exclude(
                                        # и сервис не выключен в указанную дату
                                        service_id__in=Subquery(GtfsCalendarDates.objects.filter(catalog=catalog_id, date=date, exception_type=2).values('service_id').distinct('service_id'))
                                    ).values('service_id').distinct('service_id')

                # исключения из расписания
                # сервисы добавленные на указанную дату и которых нет в actual_services1
                actual_services2 = GtfsCalendarDates.objects.filter(catalog=catalog_id, date=date, exception_type=1).exclude(catalog=catalog_id, service_id__in=actual_services1).values('service_id').distinct('service_id')

               	# union: сервисы действующие на указанную дату + сервисы добавленные на указанную дату
                actual_services = actual_services1.union(actual_services2)

                services = GtfsTrips.objects.filter(catalog=catalog_id, route_id=route_id, service_id__in=actual_services).distinct('service_id')
            else:
                # выбираем все сервисы маршрута
                services = GtfsTrips.objects.filter(catalog=catalog_id, route_id=route_id).distinct('service_id')

            # выбираем все трипы первого сервиса
            if services.count():
                trips0 = GtfsTrips.objects.filter(catalog=catalog_id, route_id=route_id, service_id=services[0].service_id, direction_id='0')
                trips1 = GtfsTrips.objects.filter(catalog=catalog_id, route_id=route_id, service_id=services[0].service_id, direction_id='1')
                if not trips0 and not trips1:  # direction_id = NULL
                    trips0 = GtfsTrips.objects.filter(catalog=catalog_id, route_id=route_id, service_id=services[0].service_id)
            else:
                trips0 = GtfsTrips.objects.none()   # empty QuerySet
                trips1 = GtfsTrips.objects.none()

            # выбираем shapes
            shapes0 = GtfsShapes.objects.filter(catalog=catalog_id, shape_id__in=Subquery(trips0.values('shape_id').distinct('shape_id'))).order_by('shape_id', 'shape_pt_sequence')
            shapes1 = GtfsShapes.objects.filter(catalog=catalog_id, shape_id__in=Subquery(trips1.values('shape_id').distinct('shape_id'))).order_by('shape_id', 'shape_pt_sequence')

            # выбираем остановки
            stops0 = GtfsStops.objects.filter(catalog=catalog_id, stop_id__in=Subquery(GtfsStopTimes.objects.filter(catalog=catalog_id, trip_id__in=Subquery(trips0.values('trip_id').distinct('trip_id'))).values('stop_id')))
            stops1 = GtfsStops.objects.filter(catalog=catalog_id, stop_id__in=Subquery(GtfsStopTimes.objects.filter(catalog=catalog_id, trip_id__in=Subquery(trips1.values('trip_id').distinct('trip_id'))).values('stop_id')))

            # формируем ответ
            res["result"]["services"] = list(services.values('service_id'))

            res["result"]["trips"] = {
                "0": {
                    "trip_headsign": trips0.first().trip_headsign if len(trips0) > 0 else '',
                    "trips": list(trips0.order_by('trip_id').values('trip_id', 'route_id', 'service_id', 'trip_headsign', 'direction_id', 'block_id', 'shape_id') if len(trips0) > 0 else trips0)
                },
                "1": {
                    "trip_headsign": trips1.first().trip_headsign if len(trips1) > 0 else '',
                    "trips": list(trips1.order_by('trip_id').values('trip_id', 'route_id', 'service_id', 'trip_headsign', 'direction_id', 'block_id', 'shape_id') if len(trips1) > 0 else trips1)
                }
            }

            res["result"]["shapes"] = {
                "0": list(shapes0.values('shape_id', 'shape_pt_sequence', 'shape_pt_loc') if len(shapes0) > 0 else shapes0),
                "1": list(shapes1.values('shape_id', 'shape_pt_sequence', 'shape_pt_loc') if len(shapes1) > 0 else shapes1)
            }

            res["result"]["stops"] = {
                "0": list(stops0.values('stop_id', 'stop_name', 'stop_pt_loc', 'location_type', 'wheelchair_boarding') if len(stops0) > 0 else stops0),
                "1": list(stops1.values('stop_id', 'stop_name', 'stop_pt_loc', 'location_type', 'wheelchair_boarding') if len(stops1) > 0 else stops1)
            }

        else:
            routes = GtfsRoutes.objects.filter(catalog=catalog_id)
            res["result"]["routes"] = list(routes.order_by('route_short_name', 'route_long_name').values())

    except ValueError as er:
        res["error"] = str(er)
    except:
        res["error"] = traceback.format_exc(limit=2)

    return HttpResponse(json.dumps(res, default=ser_gtfs))
# ajax_gtfs_get_route


@csrf_exempt
def ajax_gtfs_get_service(request):
    res = {
        "error": None,
        "result": {}
    }

    # https://gtfs.org/ru/schedule/reference/
    try:
        catalog_id = int(request.POST.get('catalog_id'))
        date = request.POST.get('date')
        service_id = request.POST.get('service_id')
        route_id = request.POST.get('route_id')

        services = GtfsTrips.objects.filter(catalog=catalog_id, route_id=route_id, service_id=service_id).distinct('service_id')

        # выбираем все трипы первого сервиса
        trips0 = GtfsTrips.objects.filter(catalog=catalog_id, route_id=route_id, service_id=service_id, direction_id='0')
        trips1 = GtfsTrips.objects.filter(catalog=catalog_id, route_id=route_id, service_id=service_id, direction_id='1')
        if not trips0 and not trips1:   # direction_id=NULL
            trips0 = GtfsTrips.objects.filter(catalog=catalog_id, route_id=route_id, service_id=service_id)

        # выбираем shapes
        shapes0 = GtfsShapes.objects.filter(catalog=catalog_id, shape_id__in=Subquery(trips0.values('shape_id').distinct('shape_id'))).order_by('shape_id', 'shape_pt_sequence')
        shapes1 = GtfsShapes.objects.filter(catalog=catalog_id, shape_id__in=Subquery(trips1.values('shape_id').distinct('shape_id'))).order_by('shape_id', 'shape_pt_sequence')

        # выбираем остановки
        stops0 = GtfsStops.objects.filter(catalog=catalog_id, stop_id__in=Subquery(GtfsStopTimes.objects.filter(trip_id__in=Subquery(trips0.values('trip_id').distinct('trip_id'))).values('stop_id')))
        stops1 = GtfsStops.objects.filter(catalog=catalog_id, stop_id__in=Subquery(GtfsStopTimes.objects.filter(trip_id__in=Subquery(trips1.values('trip_id').distinct('trip_id'))).values('stop_id')))

        # формируем ответ
        res["result"]["services"] = list(services.values('service_id'))

        res["result"]["trips"] = {
            "0": {
                "trip_headsign": trips0.first().trip_headsign if trips0.count() else '',
                "trips": list(trips0.order_by('trip_id').values('trip_id', 'route_id', 'service_id', 'trip_headsign', 'direction_id', 'block_id', 'shape_id'))
            },
            "1": {
                "trip_headsign": trips1.first().trip_headsign if trips1.count() else '',
                "trips": list(trips1.order_by('trip_id').values('trip_id', 'route_id', 'service_id', 'trip_headsign', 'direction_id', 'block_id', 'shape_id'))
            }
        }

        res["result"]["shapes"] = {
            "0": list(shapes0.values('shape_id', 'shape_pt_sequence', 'shape_pt_loc')),
            "1": list(shapes1.values('shape_id', 'shape_pt_sequence', 'shape_pt_loc'))
        }

        res["result"]["stops"] = {
            "0": list(stops0.values('stop_id', 'stop_name', 'stop_pt_loc', 'location_type', 'wheelchair_boarding')),
            "1": list(stops1.values('stop_id', 'stop_name', 'stop_pt_loc', 'location_type', 'wheelchair_boarding'))
        }

    except ValueError as er:
        res["error"] = str(er)
    except:
        res["error"] = traceback.format_exc(limit=2)

    return HttpResponse(json.dumps(res, default=ser_gtfs))
# ajax_gtfs_get_service


@csrf_exempt
def ajax_gtfs_get_trip(request):
    res = {
        "error": None,
        "result": {}
    }

    # https://gtfs.org/ru/schedule/reference/
    try:
        catalog_id = int(request.POST.get('catalog_id'))
        date = request.POST.get('date')
        trip_id = request.POST.get('trip_id')
        route_id = request.POST.get('route_id')

        trips0 = GtfsTrips.objects.filter(catalog=catalog_id, route_id=route_id, trip_id=trip_id, direction_id='0')
        trips1 = GtfsTrips.objects.filter(catalog=catalog_id, route_id=route_id, trip_id=trip_id, direction_id='1')
        if not trips0 and not trips1:   #  direction_id=NULL
            trips0 = GtfsTrips.objects.filter(catalog=catalog_id, route_id=route_id, trip_id=trip_id)

        # выбираем shapes
        if len(trips0) + len(trips1) > 0:
            shapes0 = GtfsShapes.objects.filter(catalog=catalog_id, shape_id__in=Subquery(trips0.values('shape_id').distinct('shape_id'))).order_by('shape_id', 'shape_pt_sequence')
            shapes1 = GtfsShapes.objects.filter(catalog=catalog_id, shape_id__in=Subquery(trips1.values('shape_id').distinct('shape_id'))).order_by('shape_id', 'shape_pt_sequence')
        else:
            shapes0 = []
            shapes1 = []

        # выбираем остановки
        stops0 = GtfsStops.objects.filter(catalog=catalog_id, stop_id__in=Subquery(GtfsStopTimes.objects.filter(catalog=catalog_id, trip_id__in=Subquery(trips0.values('trip_id').distinct('trip_id'))).values('stop_id')))
        stops1 = GtfsStops.objects.filter(catalog=catalog_id, stop_id__in=Subquery(GtfsStopTimes.objects.filter(catalog=catalog_id, trip_id__in=Subquery(trips1.values('trip_id').distinct('trip_id'))).values('stop_id')))

        res["result"]["shapes"] = {
            "0": list(shapes0.values('shape_id', 'shape_pt_sequence', 'shape_pt_loc')),
            "1": list(shapes1.values('shape_id', 'shape_pt_sequence', 'shape_pt_loc'))
        }

        res["result"]["stops"] = {
            "0": list(stops0.values('stop_id', 'stop_name', 'stop_pt_loc', 'location_type', 'wheelchair_boarding')),
            "1": list(stops1.values('stop_id', 'stop_name', 'stop_pt_loc', 'location_type', 'wheelchair_boarding'))
        }

    except ValueError as er:
        res["error"] = str(er)
    except:
        res["error"] = traceback.format_exc(limit=2)

    return HttpResponse(json.dumps(res, default=ser_gtfs))
# ajax_gtfs_get_trip


# тестирование gtfs schedule
# вызывается из admin_load_gtfs.html
@csrf_exempt
def ajax_gtfs_test_trip(request):
    WORK_DIR = '/bustime/bustime/utils/automato/test'
    res = {
        "error": None,
        "result": 0
    }

    try:
        url = request.POST.get('url')
        file = request.FILES.get('file')    # TemporaryUploadedFile

        if url:
            # start without waiting end
            subprocess.Popen(["/bustime/bustime/utils/gtfs_test.py", "test_feed", "-u", url])
        elif file:
            # upload file здесь, так как нельзя передать TemporaryUploadedFile в subprocess.Popen
            sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "file: %s" % file.name})

            file_name  = file.name
            if not Path(file_name).suffix:
                file_name = "%s.zip" % file_name
            file_name = os.path.join(WORK_DIR, file_name)

            downloaded = 0
            with open(file_name, "wb+") as destination:
                for chunk in file.chunks(chunk_size=1024*1024):
                    destination.write(chunk)
                    downloaded += len(chunk)
                    sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "uploaded: %s Kb" % round(downloaded / 1024, 1)})

            subprocess.Popen(["/bustime/bustime/utils/gtfs_test.py", "test_feed", "-f", file_name])
        else:
            res["error"] = "Provide URL or FILE for test"
    except Exception as ex:
        #res["error"] = str(ex)
        res["error"] = "<br />".join(traceback.format_exc(limit=1).split("\n"))

    return HttpResponse(json.dumps(res, default=ser_gtfs))
# ajax_gtfs_test_trip


# тестирование GTFS Realtime
# https://gtfs.org/ru/realtime/
# вызывается из admin_load_gtfs.html
@csrf_exempt
def ajax_gtfs_test_rt(request):
    import pyrfc6266
    import csv
    from google.transit import gtfs_realtime_pb2

    WORK_DIR = '/bustime/bustime/utils/automato/test'
    #fff = open('/bustime/bustime/utils/automato/test/debug.txt', 'w')
    #fff.write("views.ajax_gtfs_test_rt()\n")

    res = {
        "error": None,
        "result": 0
    }

    url = request.POST.get('url')
    file = request.FILES.get('file')    # TemporaryUploadedFile

    # https://gtfs.org/ru/realtime/
    try:
        # загрузка gtfs данных
        downloaded = 0
        if url:
            # download from url
            sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "url: %s" % url})
            sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "Download..."})

            get_response = requests.get(url, stream=True)

            try:
                file_name = pyrfc6266.requests_response_to_filename(get_response)   # берём имя файла из headers
            except Exception as e1:
                sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "<span class='ui red text'>Not found file name: %s</span>" % str(e1)})
                file_name  = None
            if not file_name:
                file_name = 'gtfs.rt.test'
            sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "feed name: %s" % file_name})

            file_name = os.path.join(WORK_DIR, file_name)
            sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "file: %s" % file_name})

            with open(file_name, 'wb') as f:
                for chunk in get_response.iter_content(chunk_size=1024*1024):
                    if chunk: # filter out keep-alive new chunks
                        f.write(chunk)
                        downloaded += len(chunk)
                        sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "downloaded: %s Kb" % round(downloaded / 1024, 1)})
        elif file:
            # upload file
            sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "file: %s" % file.name})
            sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "Upload..."})

            file_name = os.path.join(WORK_DIR, file.name)

            with open(file_name, "wb+") as destination:
                for chunk in file.chunks(chunk_size=1024*1024):
                    destination.write(chunk)
                    downloaded += len(chunk)
                    sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "uploaded: %s Kb" % round(downloaded / 1024, 1)})
        else:
            raise ValueError('Нет данных для анализа')

        sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "Unpack..."})
        sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": " "})
        entity_count = 0
        first_entity = None

        if Path(file_name).suffix == '.csv':
            with open(file_name, "r") as data:
                csv_reader = csv.reader(data.read().split("\n"), delimiter=',', quotechar='"')
                cnt = 0
                for veh in csv_reader:
                    cnt += 1
                    if cnt == 1: continue
                    if not first_entity:
                        first_entity = veh
                    try:
                        codBus, codLinea, sentido, lon, lat, codParIni, last_update = veh
                        if entity_count < 5:
                            sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "<b>entity:</b> %s" % veh})
                            sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": " "})
                        entity_count += 1
                    except:
                        pass
                # for veh in csv_reader
            # with open(file_name, "r") as data
        else:
            with open(file_name, "rb") as data:
                fm = gtfs_realtime_pb2.FeedMessage()
                fm.ParseFromString(data.read())

                for entity in fm.entity:
                    if not first_entity:
                        first_entity = entity
                    try:
                        vp = entity.vehicle
                        if vp and vp.trip and vp.position and vp.timestamp:
                            if entity_count < 5:
                                sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "<b>entity:</b> %s" % vp})
                                sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": " "})
                            entity_count += 1
                    except:
                        pass
                # for entity in fm.entity
            # with open(file_name, "rb") as data

        if entity_count > 0:
            if entity_count - 5 > 0:
                sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "...and <b>%s records</b> also" % (entity_count - 5)})
                sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": " "})
            sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "<span class='ui green text'><b>This is real-time gtfs data</b></span>"})
            sio_pub("ru.bustime.gtfs_test", {"element": "test_result_header", "note": "<span class='ui green text'><b>Realtime OK</b></span>"})
        else:
            if first_entity:
                sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "<b>entity:</b> %s" % first_entity})
                sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": " "})
            sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "<span class='ui red text'><b>This is not real-time gtfs data</b></span>"})
            sio_pub("ru.bustime.gtfs_test", {"element": "test_result_header", "note": "<span class='ui red text'><b>Realtime ERROR</b></span>"})

    except ValueError as er:
        res["error"] = str(er)
        sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "<span class='ui red text'>ATTENTION: GTFS DATA IS CORRUPTED!</span>"})
        sio_pub("ru.bustime.gtfs_test", {"element": "test_result_header", "note": "<span class='ui red text'><b>Realtime ERROR</b></span>"})
    except:
        res["error"] = traceback.format_exc(limit=2)
        sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "<span class='ui red text'>ATTENTION: GTFS DATA IS CORRUPTED!</span>"})
        sio_pub("ru.bustime.gtfs_test", {"element": "test_result_header", "note": "<span class='ui red text'><b>Realtime ERROR</b></span>"})

    sio_pub("ru.bustime.gtfs_test", {"call": "tools_controls_disabled", "argument": False})

    #fff.close()
    return HttpResponse(json.dumps(res, default=ser_gtfs))
# ajax_gtfs_test_rt


# добавление записи в GtfsCatalog
# вызывается из admin_load_gtfs.html
@csrf_exempt
def ajax_gtfs_append_feed(request):
    res = {
        "error": None,
        "result": 0
    }

    try:
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        active = request.POST.get('active', False)
        url_schedule = request.POST.get('url_schedule', '').strip()
        url_rt_positions = request.POST.get('url_rt_positions', '').strip()

        if not name:
            raise ValueError("name is empty")
        if not url_schedule:
            raise ValueError("url_schedule is empty")
        if not url_rt_positions:
            raise ValueError("url_rt_positions is empty")

        test = GtfsCatalog.objects.filter(name=name).first()
        if test:
            raise ValueError("name exists in feed id %s" % test.id)

        test = GtfsCatalog.objects.filter(url_schedule=url_schedule).first()
        if test:
            raise ValueError("url_schedule exists in feed id %s (%s)" % (test.id, test.name))

        test = GtfsCatalog.objects.filter(url_rt_positions=url_rt_positions).first()
        if test:
            raise ValueError("url_rt_positions exists in feed id %s (%s)" % (test.id, test.name))

        active = active in ['on', 'true', '1', 'ON', 'TRUE', 'On', 'True', True]

        test = GtfsCatalog(name=name, active=active, url_schedule=url_schedule, url_rt_positions=url_rt_positions, description=description)
        test.save()
        res["result"] = {
            "id": test.id,
            "url_schedule": test.url_schedule,
            "name": test.name
        }
    except ValueError as er:
        res["error"] = str(er)
    except:
        res["error"] = traceback.format_exc(limit=2)

    return HttpResponse(json.dumps(res, default=str))
# ajax_gtfs_append_feed


# загрузка данных gtfs schedule в БД
# вызывается из admin_load_gtfs.html
@csrf_exempt
def ajax_gtfs_load_schedule(request):
    res = {
        "error": None,
        "result": 0
    }

    catalog_id = int(request.POST.get('catalog_id', '0'))
    '''
    gtfs_loader.py <catalog_id> --zip z | --dir d
        catalog_id:
            0 - грузить все url_schedule из GtfsCatalog
            -1 - грузить указанный zip или dir и сохранить в новой записи GtfsCatalog (имя - имя файла/каталога)
            N - грузить url_schedule для GtfsCatalog.id = catalog_id

    Для начала сделаем загрузку только для N
    '''

    if catalog_id > 0:
        try:
            cmd = ["/bustime/bustime/utils/gtfs_loader.py", str(catalog_id)]

            msg = " ".join(cmd)
            sio_pub("ru.bustime.gtfs_test", {"element": "load_result", "note": "<b>%s</b><br>" % msg})

            # для публикации в канал
            cmd.append('--ch')
            cmd.append('ru.bustime.gtfs_test')

            # start without waiting end
            subprocess.Popen(cmd)
        except Exception as ex:
            #res["error"] = traceback.format_exc(limit=2)
            res["error"] = str(ex)
    else:
        res["error"] = 'Неверный параметр catalog_id (%s)' % catalog_id

    return HttpResponse(json.dumps(res, default=ser_gtfs))
# ajax_gtfs_load_schedule


# импорт данных gtfs schedule в маршруты bustime.loc
# вызывается из admin_load_gtfs.html
@csrf_exempt
def ajax_gtfs_import_schedule(request):
    res = {
        "error": None,
        "result": 0
    }

    catalog_id = int(request.POST.get('catalog_id', '0'))
    bus = request.POST.get('bus')
    opt = request.POST.get('opt')

    if catalog_id > 0:
        try:
            cmd = ["/bustime/bustime/utils/gtfs_importer.py", str(catalog_id)]
            if bus:
                cmd.append('--bus')
                cmd.append(bus)

            if opt:
                for o in opt.split(" "):
                    cmd.append(o)

            msg = " ".join(cmd)
            sio_pub("ru.bustime.gtfs_test", {"element": "import_result", "note": "<b>%s</b><br>" % msg})

            # для публикации в канал
            cmd.append('--ch')
            cmd.append('ru.bustime.gtfs_test')

            # start without waiting end
            subprocess.Popen(cmd)
        except Exception as ex:
            #res["error"] = traceback.format_exc(limit=2)
            res["error"] = str(ex)
    elif catalog_id <= 0:
        res["error"] = 'Неверный параметр catalog_id (%s)' % catalog_id

    return HttpResponse(json.dumps(res, default=ser_gtfs))
# ajax_gtfs_import_schedule


def remove_bom_from_file(filename):
    s = open(filename, mode='r', encoding='utf-8-sig').read()
    open(filename, mode='w', encoding='utf-8').write(s)
# remove_bom_from_file


@csrf_exempt
def ajax_message_for_all(request): # сообщение на сайте для всех городов
    key = "message_for_all"
    text_message = request.POST.get('text_message', None)
    delete_message = request.POST.get('delete_message', None)

    try:
        mesagge, cr = Settings.objects.get_or_create(key=key)# получаем или создаем запись с сообщением

        if delete_message: # если пользователь удаляет сообщение
            mesagge.value_string = "" #то записываем пустое значение
            res = 'delete' # и посылаем в ответе флажок удаления
        else: # если пользователь постит сообщение
            mesagge.value_string = text_message # записываем это сообщение в базу
            res = 'posted' # и посылаем в ответе флажок поста

        mesagge.save()

    except:
        res = 'error'

    return HttpResponse(res)
# ajax_message_for_all


@csrf_exempt
def admin_gtfs_supervisor_config(request):
    #city_id = int(request.POST.get("city_id", "0"))
    res = {
        "result": None
    }

    try:
        wconf = ""
        template4 = """[program:gupdater_%s]
command = /bustime/bustime/.venv/bin/python /bustime/bustime/coroutines/gtfs_update.py %s
user = www-data
autorestart = true

"""
        groups = []
        #for c in GtfsCatalog.objects.filter(active=True, url_rt_positions__isnull=False, cnt_buses__gt=0).order_by("id"):
        for c in GtfsCatalog.objects.filter(active=True, url_rt_positions__isnull=False).order_by("id"):
            wconf += (template4 % (c.id, c.id))
            groups.append("gupdater_%s" % c.id)

        s = """[group:gupdaters]
programs=%s
priority=790
""" % ','.join(groups)

        wconf += s

        dst = '/etc/supervisor/conf.d/gupdaters.conf'
        with open(dst, 'w') as f:
            f.write(wconf)

        os.chmod(dst, 0o644)

        if settings.WINDMILLS_HOSTNAME != settings.MASTER_HOSTNAME:
            cmd = [f"sudo -u supervarius scp -P9922 -o \"StrictHostKeyChecking no\" "
                   f"{dst} supervarius@{settings.BUSTIME_HOSTS[settings.GTFS_HOSTNAME]}:{dst}"]
            try:
                output = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT).decode()
            except subprocess.CalledProcessError as e:
                output = e.output.decode()
                raise ValueError(output)
            os.unlink(dst)

        """
        sudo supervisorctl reread
        sudo supervisorctl update gupdaters
        sudo supervisorctl status gupdaters:*
        """
        if settings.WINDMILLS_HOSTNAME != settings.MASTER_HOSTNAME:
            cmd = [f"sudo -u supervarius ssh -p 9922 -o \"StrictHostKeyChecking no\" supervarius@{settings.BUSTIME_HOSTS[settings.GTFS_HOSTNAME]} "
                    f"\"sudo /usr/bin/supervisorctl reread\""]
            subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT).decode()
        else:
            cmd = ["sudo", "/usr/bin/supervisorctl", "reread"]
            output = subprocess.check_output(cmd).decode()

        if settings.WINDMILLS_HOSTNAME != settings.MASTER_HOSTNAME:
            cmd = [f"sudo -u supervarius ssh -p 9922 -o \"StrictHostKeyChecking no\" supervarius@{settings.BUSTIME_HOSTS[settings.GTFS_HOSTNAME]} "
                    f"\"sudo /usr/bin/supervisorctl update gupdaters\""]
            subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT).decode()
        else:
            cmd = ["sudo", "/usr/bin/supervisorctl", "update", "gupdaters"]
            output += subprocess.check_output(cmd).decode()

        res["result"] = "%s обработчиков создано:\nSupervisor:\n%s" % (len(groups), output)
    except Exception as e:
        res["result"] = "(%s): %s" % (settings.MASTER_HOSTNAME, str(e))

    return HttpResponse(json.dumps(res, default=str))

# вызывается из admin_load_gtfs.html
@csrf_exempt
def ajax_gtfs_stat_refresh(request):
    updaters = rcache_mget(REDIS.smembers("updaters"))
    updaters = [k for k in updaters if k is not None]
    updaters.sort(key=lambda k : k['src'])
    res = {
        "error": None,
        "result": [json.dumps(x,default=str,ensure_ascii=False,indent=3) for x in updaters]
    }

    return HttpResponse(json.dumps(res, default=str))
# ajax_gtfs_stat_refresh

def turbine_inspector(request, city_name):
    place = get_object_or_404(Place, slug=city_name)
    us = get_user_settings(request)

    bus_ids = get_setting("turbine_inspector", force=True)

    ctx = {'us': us, "place": place, "bus_ids": bus_ids, "turbomill_count": settings.TURBO_MILL_COUNT}
    return arender(request, "turbine_inspector.html", ctx)

def open_letter(request):
    us = get_user_settings(request)
    ctx = {'us': us}
    template = "open-letter-for-transport-data.html"
    lang_code = translation.get_language()
    if lang_code in ['ru', 'es', 'pt']:
        template = template.replace("-data", f"-data-{lang_code}")
    return arender(request, template, ctx)

# CMS needed
def blog(request, template_name="blog.html"):
    us = get_user_settings(request)
    ctx = {'us': us}
    return arender(request, template_name, ctx)


def handbook(request, topic):
    us = get_user_settings(request)
    ctx = {'us': us}
    if topic == "bus":
        qs = VehicleModel.objects.all().order_by('name').values("name", "slug")
        lang_code = translation.get_language()
        if lang_code != "ru":
            qs = qs.exclude(name__regex=r'[А-яЁё]')
        ctx['models'] = qs
    if topic not in ["airplane", "bus", "bus-intercity", "bus-taxi",
                     "carpool", "metro", "model", "taxi", "train",
                     "tramway", "trolleybus", "water"]:
        return HttpResponsePermanentRedirect("/help/")
    return arender(request, f"handbook/{topic}.html", ctx)


def handbook_model(request, topic, model):
    us = get_user_settings(request)
    ctx = {'us': us}
    try:
        ctx['model'] = VehicleModel.objects.prefetch_related('vehiclemodelfeature_set', 'vehiclemodelfeature_set__feature').get(slug=model)
    except VehicleModel.DoesNotExist:
        raise Http404
    return arender(request, f"handbook/model.html", ctx)

def custom_handler404(request, exception):
    return HttpResponsePermanentRedirect('/')

def account_deletion(request):
    us = get_user_settings(request)
    ctx = {'us': us}
    return arender(request, "account_deletion.html", ctx)

def logs_on_map(request, city_name):
    place = get_object_or_404(Place, slug=city_name)
    us = get_user_settings(request)

    ctx = {'us': us, "place": place}
    return arender(request, "logs_on_map.html", ctx)

def ajax_not_found(request):
    logs = Log.objects.filter(
        date__gt=(datetime.datetime.now() - datetime.timedelta(days=1)), 
        ttype='get_bus_by_name'
    )
    result = []
    for idx, log in enumerate(logs):
        if log.place:
            x = log.place.point.x 
            y = log.place.point.y 
        elif log.city:
            x = log.city.point.x 
            y = log.city.point.y 
        else:
            x, y = 0, 0
        # random offset to get clickable cloud of points
        meter_in_degree = 111320 # average
        x += random.uniform(-500, 500) / meter_in_degree
        y += random.uniform(-500, 500) / meter_in_degree
        msg = log.message.split(':')[1]
        result.append({
            "id": idx,
            "x": x,
            "y": y,
            "msg": msg
        })
    all_by_point = REDIS_W.georadius('not_found', radius=21000, unit='km', longitude=0, latitude=0, withcoord=True)
    for idx, (name, (ln, lt)) in enumerate(all_by_point, start=idx+1):
        n, tt, uid = name.decode().split('__')
        n = n.replace('bus_', '')
        msg = f"name={n}, type={tt}, uid={uid}"
        result.append({
            "id": idx,
            "x": ln,
            "y": lt,
            "msg": msg
        })
    return HttpResponse(json.dumps(result))


def ajax_get_alerts(request):
    retval = {
        'gtfs_alerts_buses': [],
        'html': []
    }

    try:
        place_id = request.GET.get('place_id')
        if place_id:
            bus_id = int(request.GET.get('bus_id', '0'))
            retval['error'] = bus_id
            gtfs_alerts = rcache_get("alerts_%s" % place_id, {}).values()
            buses = set()

            for a in gtfs_alerts:
                add_row = False
                row = f'''<tr><td data-label="start">{a['start']} - {a['end']}<br/>
                        <p style="font-weight: bold">{a['header']}</p><br/>
                        <span class="ui blue tag label">{a['cause']}</span>
                        <span class="ui pink tag label">{a['effect']}</span>
                        </td><td data-label="description">{a['description']}<br/><br/>'''
                for b in a['routes']:
                    buses.add(b.id)
                    row += f'''<a class="ui basic small button" href="{b.get_absolute_url()}" target="_blank">{b.ttype_name()} {b.name}</a>'''
                    if not add_row:
                        add_row = bus_id == b.id if bus_id else True
                # for b in a['routes']
                row += '</td></tr>'
                if add_row:
                    retval['html'].append(row)
            # for a in gtfs_alerts
            retval['gtfs_alerts_buses'] = list(buses)
        # if place_id
    except Exception as ex:
        retval['html'] = f'<tr><td>{str(ex)}</td></tr>'

    return HttpResponse(json.dumps(retval))
# ajax_get_alerts

def ajax_get_weather(request):
    retval = {
        'weather': '',
        'avg_temp': '',
        'error': '',
    }

    try:
        place_id = int(request.GET.get('place_id', "0"))
        place = Place.objects.filter(id=place_id).first()
        if place:
            retval['avg_temp'] = avg_temp(place) or 0
            weather = weather_detect(place)

            if weather == "rain":
                retval['weather'] = '''<i class="fa fa-tint" title="'''+_('дождь')+'''"></i>'''
            elif weather == "snow":
                retval['weather'] = '''<i class="fa fa-snowflake-o" title="'''+_('снег')+'''"></i>'''
            elif weather == "ice":
                retval['weather'] = '''<i class="fa fa-snowflake-o" title="'''+_('град')+'''"></i>'''
            elif weather == "smoke":
                retval['weather'] = '''<i class="fa fa-recycle" title="'''+_('черное небо')+'''"></i>'''
            elif weather == "clear":
                retval['weather'] = '''<i class="fa fa-sun-o" title="'''+_('ясно')+'''"></i>'''
            elif weather == "clouds":
                retval['weather'] = '''<i class="fa fa-mixcloud" title="'''+_('облачно')+'''"></i>'''
            elif weather == "dark_clouds":
                retval['weather'] = '''<i class="fa fa-cloud" title="'''+_('пасмурно')+'''"></i>'''
            elif weather == "fog":
                retval['weather'] = '''<i class="fa fa-tree" title="'''+_('туман')+'''"></i>'''
    except Exception as ex:
        retval['error'] = str(ex)

    return HttpResponse(json.dumps(retval))
