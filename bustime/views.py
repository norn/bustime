# -*- coding: utf-8 -*-

# import logging
# import re
# import hashlib
import datetime
import operator
import time
import pygeoip
import requests
import zmq
import calendar
import ujson
import random
from dateutil.relativedelta import relativedelta
from ipwhois import IPWhois
from app_metrics.utils import Timer, create_metric, metric, timing  # , gauge

from django.conf import settings
from django.contrib.gis.geos import Point
# from django.contrib.sessions.models import Session
from django.core.cache import cache
from django.http import (Http404, HttpResponse, HttpResponsePermanentRedirect,
                         HttpResponseRedirect)
from django.shortcuts import get_object_or_404, render
from django.template import RequestContext
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q

from bustime import gemy
from bustime.models import *
from bustime.wsocket_cmd import wsocket_cmd
import pymorphy2
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
import glob
from django.core.mail import send_mail

context = zmq.Context()
SOCK = context.socket(zmq.PUSH)
SOCK.connect(ZSUBGATE)

EDEN = [0, 1, 2, 2, 2, 2, 2, 2, 2, 3]
DELTA_SECS = datetime.timedelta(seconds=15)
DELTA_AMOUNT_AGE = datetime.timedelta(minutes=15)

MORPH = pymorphy2.MorphAnalyzer()
# metrics setup
# create_metric(name='Visit: Perm', slug='visit_9')
# create_metric(name='New user: Perm', slug='new_user_9')


def arender(request, template, ctx):
    if request.GET.get('t', -1) != -1:
        template = template.replace(".html", "-test.html")
        ctx['test'] = True
    return render(request, template, ctx)


def random_advice():
    advices = ["Удачи в дороге, хороших пассажиров!",
               "Удачи в дороге, хороших пассажиров!",
               "Без приключений!",
               "Без штрафов и бешеных бабулек!",
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


class Weather():
    temperature = None
    weather = None
    updated = None


def get_user_settings(request, force_city=None):
    session_key = request.session.session_key

    if session_key is None:
        request.session.create()
        session_key = request.session.session_key
        us, cr = UserSettings.objects.get_or_create(session_key=session_key)
        us.ip = request.META['REMOTE_ADDR']
        us.ua = request.META.get('HTTP_USER_AGENT', "")
        if force_city:
            us.city = CITY_MAP[force_city]
        else:
            us.city = city_autodetect(us.ip)
        us.save()

        if 'http://www.proximic.com/info/spider.php' not in us.ua and \
           'http://www.majestic12.co.uk/bot.php?+' not in us.ua and \
           'YandexBot/3.0' not in us.ua and \
           'http://www.google.com/bot.html' not in us.ua and \
           'Mediapartners-Google' not in us.ua and \
           'AhrefsBot/5.0' not in us.ua and \
           'http://help.naver.com/robots' not in us.ua and \
           'http://www.bing.com/bingbot.htm' not in us.ua:
            metric('new_user_%s' % us.city.id)
            now = datetime.datetime.now()
            f = open('/tmp/bustime_new_users.csv', 'a')
            f.write("%s %s %s %s\n" %
                    (now, request.META['REMOTE_ADDR'],
                     us.city, request.META.get('HTTP_USER_AGENT', "")))
            f.close()
    else:
        us, cr = UserSettings.objects.get_or_create(session_key=session_key)
        if force_city:
            us.city = CITY_MAP[force_city]
            us.save()
        elif us.city is None:
            us.ip = request.META['REMOTE_ADDR']
            us.ua = request.META.get('HTTP_USER_AGENT', "")
            us.city = city_autodetect(us.ip)
            us.save()

    return us


def get_transaction(us, key="premium"):
    now = datetime.datetime.now()
    transes = Transaction.objects.filter(
        user=us, key=key, end_time__gte=now).order_by('-end_time')
    if transes:
        return transes[0]
    else:
        return None


def human_time(updated, city=None):
    updated += datetime.timedelta(hours=city.timediffk)
    updated = str(updated).split('.')[0]
    updated = updated.split(' ')[1]
    return updated


def detect_ads_show(request, us):
    show = True
    # ip = request.META.get('REMOTE_ADDR', '0.0.0.0')
    ua = request.META.get('HTTP_USER_AGENT', "").lower()

    if us.premium or us.noads:
        show = False
    elif "opera mini" in ua or "opera" in ua:
        show = False

    # if request.session.get('level_10_date') and request.session.get('level_10_date') + datetime.timedelta(days=30) > datetime.datetime.now():
    #     noads = True
    # if us.id == 7410909:
    #     show = False

    return show


def date_prefix(today):
    key = 'date_%s_%s_%s' % (today.year, today.month, today.day)
    return key


def city_autodetect(ip):
    # {'area_code': 0,
    #  'city': u'Kaliningrad',
    #  'continent': 'EU',
    #  'country_code': 'RU',
    #  'country_code3': 'RUS',
    #  'country_name': 'Russian Federation',
    #  'dma_code': 0,
    #  'latitude': 54.706500000000005,
    #  'longitude': 20.510999999999996,
    #  'metro_code': None,
    #  'postal_code': u'236000',
    #  'region_code': u'23',
    #  'time_zone': 'Europe/Kaliningrad'}
    GI = pygeoip.GeoIP(settings.PROJECT_DIR + '/addons/GeoLiteCity.dat')
    city = GI.record_by_addr(ip)
    # if city and city.get('country_code') == "KE":
    #     return -1
    if city is None or city.get('city', False) is None:
        try:  # micro cache
            ipcity = IPcity.objects.get(ip=ip)
            return ipcity.city
        except:
            pass
        obj = IPWhois(ip)
        results = str(obj.lookup())
        default_drop = False
        if 'Krasnoyarsk' in results or 'Novosibirsk' in results:
            city = CITY_MAPN[u'Красноярск']
        # elif 'Kaliningrad' in results:
        #     city = CITY_MAPN[u'Калининград']
        elif 'Tomsk' in results:
            city = CITY_MAPN[u'Томск']
        elif 'Saint Petersburg' in results:
            city = CITY_MAPN[u'Санкт-Петербург']
        elif 'Perm' in results:
            city = CITY_MAPN[u'Пермь']
        elif 'Kazan' in results:
            city = CITY_MAPN[u'Казань']
        else:
            city = CITY_MAPN[u'Санкт-Петербург']
            default_drop = True
        IPcity.objects.get_or_create(ip=ip,
                                     city=CITY_MAPN[u'Красноярск'],
                                     whois_results=results,
                                     default_drop=default_drop)

    # elif city['city'] == "Kaliningrad":
    #     city = CITY_MAPN[u'Калининград']
    elif city['city'] == "Saint Petersburg":
        city = CITY_MAPN[u'Санкт-Петербург']
    elif city['city'] == "Tomsk":
        city = CITY_MAPN[u'Томск']
    elif city['city'] == "Krasnoyarsk" or city['city'] == "Novosibirsk":
        city = CITY_MAPN[u'Красноярск']
    elif city['city'] == "Perm":
        city = CITY_MAPN[u'Пермь']
    elif city['city'] == "Kazan":
        city = CITY_MAPN[u'Казань']
    else:
        city = CITY_MAPN[u'Санкт-Петербург']
    return city


def classic_index(request):
    us = get_user_settings(request)
    ctx = {"cities": City.objects.filter(active=True).order_by('name'),
           "us": us, "classic": True}
    return arender(request, "index-classic.html", ctx)


def classic_routes(request, city_id=None, city_name=True):
    us = get_user_settings(request)
    if city_id:
        city_id = int(city_id)
        city = get_object_or_404(City, id=city_id)
        return HttpResponsePermanentRedirect("/%s/classic/" % city.slug)
    city = get_object_or_404(City, slug=city_name)
    cc_key = "allbuses_%d" % city.id
    buses = cache.get(cc_key)
    if not buses:
        buses = list(
            Bus.objects.filter(active=True, city=city).order_by('order'))
        cache.set(cc_key, buses)
    ctx = {"city": city, "buses": buses, "us": us, "classic": True}
    return arender(request, "index-classic-routes.html", ctx)


def special_theme_selector(now):
    special_theme = None
    if now.month == 5 and now.day == 9:
        special_theme = "9may"
    return special_theme


def home(request, template_name='index.html', force_city=None, city_name=None):
    c = request.GET.get('c')
    if c:
        city = CITY_MAP.get(int(c))
        if city:
            return HttpResponsePermanentRedirect(u"/%s/" % city.name.lower())
        else:
            return HttpResponseRedirect("/")

    if not request.session.session_key:
        first_time = True
    else:
        first_time = False

    now = datetime.datetime.now()
    if city_name:
        city = get_object_or_404(City, slug=city_name)
        force_city = city.id
    us = get_user_settings(request, force_city=force_city)
    # if force_city and request.scheme == "http":
    #     return HttpResponsePermanentRedirect("https://www.bustime.ru%s" % us.city.get_absolute_url())
    transaction = get_transaction(us)

    if (us.pro_demo
            and us.pro_demo_date + datetime.timedelta(minutes=10) <= now):
        # Since both conditions are true, we can frobnicate.
        premium_deactivate(us)
        us.pro_demo = False
        us.save()

    if us.premium and not us.pro_demo:
        if not transaction:
            premium_deactivate(us)
        else:
            if not transaction.notified:
                transaction.notified = True
                transaction.save()
                template_name = "pro-notification.html"

    # check if he used ref before
    # r = request.GET.get('r')
    # if r and not us.referral and r != us.session_key[:6] and r != us.id and request.META.get('HTTP_USER_AGENT') != "Mediapartners-Google" and us.ua:
    #     us.referral = r[:16]
    #     us.save()
    #     metric('referral_used')
    #     try:
    #         if us.referral.isdigit():
    #             rowner = UserSettings.objects.get(id=us.referral)
    #         else:
    #             rowner = UserSettings.objects.get(
    #                 session_key__startswith=us.referral)
    #         rowner.stars += 1
    #         rowner.save()
    #     except:
    #         pass
    #     return HttpResponseRedirect("/")

    now += datetime.timedelta(hours=us.city.timediffk)

    if not first_time:
        metric('visit_%s' % us.city.id)

    if now.hour >= 1 and now.hour < 5:
        otto = True
    else:
        otto = False

    device = mobile_detect(request)
    ads_show = detect_ads_show(request, us)
    if first_time: # or us.ctime.date() == now.date():
        ads_show = False

    luck = False
    # 1 день в неделю будут удачным
    digest = now.year * 365 + now.month * 12 + now.day + us.id
    if digest % 7 == 0 and 0:
        luck = True
        ads_show = False

    if us.busfav:
        busfavor = pickle.loads(str(us.busfav))
        busfavor = busfavor.get(us.city_id, {})
        busfavor = sorted(busfavor.iteritems(), key=operator.itemgetter(1))
        busfavor.reverse()
        busfavor = busfavor[:us.busfavor_amount]
        busfavor = map(lambda x: x[0], busfavor)
        # [28, 23, 22, 57, 85] top ids of the most used
        bf = {}
        for b in busfavor:
            bus = bus_get(b)
            if bus:
                bf[bus] = bus.order
        busfavor = sorted(bf.iteritems(), key=operator.itemgetter(1))
        busfavor = map(lambda x: x[0], busfavor)
    else:
        busfavor = []

    if us.tcard:
        try:
            tcard = Tcard.objects.filter(num=us.tcard)[0]
            tcard.update()
        except:
            tcard = None
    else:
        tcard = None

    cc_key = "SpecialIcons"
    specialicons = cache.get(cc_key)
    if not specialicons:
        specialicons = list(SpecialIcon.objects.filter(active=True))
        cache.set(cc_key, specialicons)

    cc_key = "allbuses_%d" % us.city_id
    buses = cache.get(cc_key)
    if not buses:
        buses = list(
            Bus.objects.filter(active=True, city=us.city).order_by('order'))
        cache.set(cc_key, buses)
    avg_temp = get_avg_temp(us.city)
    # hint = HINTS[random.randint(0, len(HINTS) - 1)]

    error_update = cache.get("error_update_%s" % us.city_id)
    if error_update:
        error_update_img = glob.glob("/r/bustime/bustime/bustime/static/img/sur/*.png")
        error_update_img = random.choice(error_update_img)
        error_update_img = error_update_img.replace('/r/bustime/bustime/bustime/static/img/sur/', '')
    else:
        error_update_img = ""

    ut = UserTimer.objects.filter(user=us, date=now.date())
    if ut:
        ut = ut[0]
    else:
        ut = UserTimer.objects.create(user=us, date=now.date())

    if not first_time and us.vk_like_pro == 0 and (us.ctime + datetime.timedelta(minutes=5)) < now - datetime.timedelta(hours=us.city.timediffk):
        vk_like_pro = True
    else:
        vk_like_pro = False

    qs = Song.objects.filter(active=True, lucky=True)
    if qs.exists():
        radio = qs.order_by("?")[0]
    else:
        radio = Song.objects.filter(active=True).order_by("?")[0]

    ctx = {
        "buses": buses, 'avg_temp': avg_temp, 'busfavor': busfavor,
        'us': us, "eden": EDEN,
        "timer_bst_avg_osd": cache.get("timer_bst_avg_osd"),
        "otto": otto, 'tcard': tcard, 'ads_show': ads_show,
        'device': device, 'first_time': first_time,
        'error_update': error_update,
        "error_update_img": error_update_img,
        'luck': luck, 'transaction': transaction,
        'vk_like_pro': vk_like_pro, 'now': now,
        'ut_minutes': ut.minutes, 'specialicons': specialicons,
        "special_theme": special_theme_selector(now),
        "main_page": True,
        "random_advice": random_advice(),
        "force_city": force_city,
        "radio": radio
    }

    if us.city_id == 3 and ut.minutes >= 110 and not us.pro_demo and not us.premium:
        return arender(request, "overtime.html", ctx)

    # yappi.get_func_stats().print_all()
    return arender(request, template_name, ctx)


def refresh_temperature_wunderground(city):
    # see also https://developer.forecast.io/
    try:
        r = requests.get(
            'http://api.wunderground.com/api/24811da8f62613bf/conditions/lang:RU/q/RU/%s.json' % city.wunderground, timeout=5)
        j = r.json()
        avg_tmp = j['current_observation']['temp_c']
    except:
        avg_tmp = False
    return avg_tmp


def get_avg_temp(city):
    cc_key = "bustime__avg_temp_%s" % city.id
    w = cache.get(cc_key)
    if w is None:
        w = refresh_temperature_wunderground(city)
        cache.set(cc_key, w, 60 * 60)
    return w


# def qroute_opti(bus, name, direction):
#     """
#     Возвращает текущий маршрутную остановку и следующую
#     """
#     cc_key = "qroute_%s" % (bus.id)
#     busroutes = cache.get(cc_key)
#     if not busroutes:
#         busroutes = Route.objects.filter(bus=bus).order_by(
#             'direction', 'order').select_related('busstop')
#         cache.set(cc_key, busroutes)

#     curent, next_ = None, None
#     for r in busroutes:
#         if r.busstop.name == name and r.direction == direction:
#             curent = r
#         elif curent != None and next_ == None and r.direction == direction:
#             next_ = r
#     return curent, next_


def ajax_busfavor(request):
    try:
        bus_id = request.GET.get('bus_id')
        bus_id = int(bus_id)
    except:
        return HttpResponse("")
    us = get_user_settings(request)
    bus = bus_get(bus_id)
    if not bus:
        return HttpResponse("")

    if us.busfav:
        busfavor = pickle.loads(str(us.busfav))
    else:
        busfavor = {}

    if not busfavor.get(bus.city_id):
        busfavor[bus.city_id] = {}

    if busfavor[bus.city_id].get(bus_id):
        busfavor[bus.city_id][bus_id] += 1
    else:
        busfavor[bus.city_id][bus_id] = 1

    us.busfav = pickle_dumps(busfavor)
    us.save()
    return HttpResponse(busfavor[bus.city_id][bus_id])


def ajax_busdefavor(request):
    try:
        bus_id = request.GET.get('bus_id')
        bus_id = int(bus_id)
    except:
        return HttpResponse("")
    us = get_user_settings(request)

    if us.busfav:
        busfavor = pickle.loads(str(us.busfav))
    else:
        busfavor = {}

    try:
        busfavor[us.city_id].pop(bus_id)
    except:
        return HttpResponse("123")

    us.busfav = pickle_dumps(busfavor)
    us.save()
    return HttpResponse("")


def ajax_timer(request):
    us = get_user_settings(request)
    now = datetime.datetime.now() + datetime.timedelta(hours=us.city.timediffk)
    ut = UserTimer.objects.filter(user=us, date=now.date())
    if ut:
        ut = ut[0]
    else:
        ut = UserTimer.objects.create(user=us, date=now.date())

    if us.pro_demo:
        ut.pro_minutes += 1
    else:
        ut.minutes += 1

    ip = request.META.get('REMOTE_ADDR', '0.0.0.0')
    ua = request.META.get('HTTP_USER_AGENT', "").lower()
    if ip.startswith('80.255.132.') or us.id == 3136937000:  # kgt
        ut.minutes = 77
        us.ip = ip
        us.ua = ua
        us.save()

    if ut.minutes == 60 * 2:
        us.ip = ip
        us.ua = ua
        us.save()
        metric('timer_warning')

    if ut.minutes < 32000:  # what the hell?
        ut.save()
    serialized = {'minutes': ut.minutes, "pro_minutes": ut.pro_minutes}
    serialized = ujson.dumps(serialized)
    return HttpResponse(serialized)


def status_get(now_date, u, g, city_id):
    if not g:
        return None
    for_date = datetime.date(now_date.year, now_date.month, 1)

    status = Status.objects.filter(
        date=for_date, gosnum=g, bus__city__id=city_id)

    if not status:
        bus_event = uniqueid_to_event(city_id, u)
        if not bus_event:
            return None
        status, cr = Status.objects.get_or_create(
            date=for_date,
            gosnum=g)
        if cr:
            status.bus = bus_event.bus
            status.save()
    else:
        status = status[0]

    return status


@csrf_exempt
def ajax_ava_change(request):
    us = get_user_settings(request)
    now = datetime.datetime.now() + datetime.timedelta(hours=us.city.timediffk)
    if not us.premium or us.pro_demo:
        return HttpResponse("-1")

    what = request.POST.get('what')
    ava = request.POST.get('ava')
    g = request.POST.get('g')
    u = request.POST.get('u')

    status = status_get(now.date(), u, g, us.city_id)
    if not status:
        return HttpResponse("no gosnum")

    setattr(status, "ava_%s" % what, ava)
    status.save()
    metric('ava_change')
    log_message("%s, %s" % (status, ava), ttype="ava_change_%s" % what, user=us)

    return HttpResponse("1")


@csrf_exempt
def ajax_rate(request):
    us = get_user_settings(request)
    now = datetime.datetime.now() + datetime.timedelta(hours=us.city.timediffk)
    for_date = now.date()
    rate = request.POST.get('rate')
    if rate == "1":
        rate = True
    else:
        rate = False
    u = request.POST.get('u')
    g = request.POST.get('g')

    status = status_get(for_date, u, g, us.city_id)
    if not status:
        return HttpResponse(ujson.dumps({"error": "no gosnum"}))

    vote = Vote.objects.filter(ctime__contains=for_date,
                               user=us,
                               status=status)
    if not vote:
        vote = Vote.objects.create(ctime=now,
            user=us, status=status, positive=rate)
        vote.ctime = now
        vote.save()
        metric('vote')
    else:
        vote = vote[0]
        vote.positive = rate
        vote.save()

    return ajax_rating_get(request)


@csrf_exempt
def ajax_vote_comment(request):
    us = get_user_settings(request)
    now = datetime.datetime.now() + datetime.timedelta(hours=us.city.timediffk)
    for_date = now.date()

    u = request.POST.get('u')
    g = request.POST.get('g')
    comment = request.POST.get('comment')
    rate = request.POST.get('rate')
    status = status_get(for_date, u, g, us.city_id)
    if rate == "1":
        rate = True
    else:
        rate = False

    if not status:
        return HttpResponse(ujson.dumps({"error": "no gosnum"}))

    vote = Vote.objects.filter(ctime__contains=for_date,
                               user=us,
                               status=status)
    if not vote:  # как?
        vote = Vote.objects.create(user=us, status=status)
        vote.ctime = now
        metric('vote')
    else:
        vote = vote[0]
    vote.comment = comment
    vote.positive = rate
    vote.save()

    return ajax_rating_get(request)


@csrf_exempt
def ajax_rating_get(request):
    us = get_user_settings(request)
    now = datetime.datetime.now() + datetime.timedelta(hours=us.city.timediffk)
    for_date = now.date()
    u = request.POST.get('u')
    g = request.POST.get('g')

    status = status_get(for_date, u, g, us.city_id)
    if not status:
        return HttpResponse(ujson.dumps({"error": "no gosnum"}))

    serialized = {
        'date': str(status.date),
        'gosnum': status.gosnum,
        'ava_driver': status.ava_driver,
        'ava_conductor': status.ava_conductor,
        'rating_wilson': status.rating_wilson_human,
        'votes_wilson': status.votes_wilson,
        'comments': status.comments,
        'status_id': status.id
    }

    votes = Vote.objects.filter(status=status, user=us,
                                ctime__year=for_date.year,
                                ctime__month=for_date.month,
                                ctime__day=for_date.day)
    for v in votes:
        serialized['myvote_ctime'] = str(v.ctime)
        serialized['myvote_positive'] = v.positive
        serialized['myvote_comment'] = v.comment

    return HttpResponse(ujson.dumps(serialized))


def uniqueid_to_event(city_id, u):
    bus_event = REDIS.get("allevents_%s" % city_id)
    if bus_event:
        bus_event = pickle.loads(bus_event)
        bus_event = bus_event.get('event_%s_%s' % (city_id, u))
    return bus_event


def bus_last_f(bus, raw=False, mobile=False):
    now = datetime.datetime.now()
    if not bus:
        return False
    now += datetime.timedelta(hours=bus.city.timediffk)
    weekday = weekday_dicto(now)

    serialized = {}
    cc_key = "Route_bus_%s" % bus.id
    routes = cache.get(cc_key)
    if not routes:
        routes = []
        for r in Route.objects.filter(bus=bus).order_by('order'):
            routes.append(
                {"id": r.id, "name": r.busstop.name, "d": r.direction, "bst": r.busstop_id})
        cache.set(cc_key, routes, 60 * 60 * 24)
    if not mobile:
        serialized['routes'] = routes
    serialized['napr'] = [bus.napr_a, bus.napr_b]
    serialized['ttype'] = bus.ttype

    cc_key = "first_last_%s_%s" % (bus.id, weekday.keys()[0])
    first_last = cache.get(cc_key)
    if not first_last:  # this is schedule in real
        first_last = {}
        td0 = Timetable.objects.filter(
            bus=bus, direction=0, **weekday).order_by('order', 'time')
        td1 = Timetable.objects.filter(
            bus=bus, direction=1, **weekday).order_by('order', 'time')
        first_last["s0"] = map(
            lambda(x): [x.hour, x.minute], td0.values_list('time', flat=True))
        first_last["s1"] = map(
            lambda(x): [x.hour, x.minute], td1.values_list('time', flat=True))
        cache.set(cc_key, first_last, 60 * 60 * 24)
    if first_last:
        serialized['first_last'] = first_last

    bdata = bus.bdata_mode0()
    if bdata:
        if mobile:
            for i in bdata['l']:
                if i.has_key('g'):
                    del i['g']
        serialized['bdata_mode0'] = bdata
        serialized['bdata_mode0']['updated'] = str(
            serialized['bdata_mode0']['updated']).split('.')[0].split(' ')[1]
        serialized['bdata_mode0']['bus_id'] = bus.id

    serialized['passenger'] = cache.get('bustime_passenger_%s' % bus.id, {})
    time_bst = REDIS.get("time_bst_%s" % bus.city_id)

    if time_bst:
        time_bst = pickle.loads(time_bst)
        serialized['time_bst'] = time_bst.get(bus.id, {})

    if raw:
        return serialized
    else:
        return ujson.dumps(serialized)


def bdata_mode2_f(events, raw=False):
    tosend = events
    if raw:
        return tosend
    else:
        return ujson.dumps(tosend)


def ajax_bus(request):
    bus_id = request.GET.get('bus_id', '0')
    try:
        bus = Bus.objects.get(id=int(bus_id))
    except:
        return HttpResponse("")
    serialized = bus_last_f(bus)
    return HttpResponse(serialized)


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
    ctx = {"city": bus.city, "classic":True}
    route0 = Route.objects.filter(bus=bus, direction=0).order_by(
        'order').select_related('busstop')
    route1 = Route.objects.filter(bus=bus, direction=1).order_by(
        'order').select_related('busstop')
    time_bst = REDIS.get("time_bst_%s" % bus.city_id)
    if time_bst:
        time_bst = pickle.loads(time_bst)
    else:
        time_bst = {}
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
    if len(num) < 12:
        return HttpResponse("неправ. формат!")
    if len(num) > 18:
        return HttpResponse("неправ. формат!")

    us = get_user_settings(request)
    tcards = Tcard.objects.filter(num=num)
    if not tcards:
        tcard = Tcard.objects.create(
            num=num, updated=datetime.datetime(2014, 02, 11))
    else:
        tcard = tcards[0]
    tcard.update()
    if tcard.black:
        return HttpResponse("несущ. номер")
    else:
        us.tcard = num
        us.save()
        return HttpResponse(tcard.balance)

def ajax_card(request, num):
    if len(num) < 12:
        return HttpResponse("неправ. формат!")
    if len(num) > 18:
        return HttpResponse("неправ. формат!")

    us = get_user_settings(request)
    tcards = Tcard.objects.filter(num=num)
    if not tcards:
        tcard = Tcard.objects.create(
            num=num, updated=datetime.datetime(2014, 02, 11))
    else:
        tcard = tcards[0]
    tcard.update()
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
    busamounts = cache.get("busamounts")
    serialized = ujson.dumps({"busamounts": busamounts})
    return HttpResponse(serialized)


def ajax_metric(request, metric_=None):
    if not metric_:
        metric_ = request.GET.get('metric')
    if metric_ == "wsocket_off":
        value = request.GET.get('value')
        us = get_user_settings(request)
        log_message(value, ttype="wsocket_off", user=us)
    metric(metric_)
    return HttpResponse("")


def ajax_settings(request):
    setting = request.GET.get('setting')
    value = request.GET.get('value')
    if setting:
        us = get_user_settings(request)
        if setting in ["theme", "mode"]:
            value = int(value)
        elif setting == "city":
            value = City.objects.get(id=int(value))
        elif setting in ["matrix_show", "map_show"]:
            if value == "true":
                value = True
            else:
                value = False
        setattr(us, setting, value)
        us.save()
    return HttpResponse("")

def ajax_stop_id_f(ids, raw=False, data=None, single=False):
    serialized = {"stops": []}
    if single:
        nstops = ids
        bdata_mode3 = {nstops[0].id: data}
    else:
        cache_key = "nbusstop_ids_%s" % str(ids).replace(' ', '')
        nstops = cache.get(cache_key, None)
        if nstops == None:
            nstops = NBusStop.objects.filter(id__in=ids).order_by('moveto')
            cache.set(cache_key, nstops)
    if nstops:
        city_id = nstops[0].city_id
        if not single:
            bdata_mode3 = REDIS.get("bdata_mode3_%s" % city_id)
            if bdata_mode3:
                bdata_mode3 = pickle.loads(bdata_mode3)
            else:
                bdata_mode3 = {}

    for nb in nstops:
        preds = bdata_mode3.get(nb.id, [])
        preds = sorted(preds, key=lambda p: p['t'])
        nbdata = []
        for pred in preds:
            stime = "%02d:%02d" % (pred['t'].hour, pred['t'].minute)
            nbdata.append({"n": pred['n'], "t": stime})
        if nb.tram_only:
            tram_only = 1
        else:
            tram_only = 0
        serialized[
            'stops'].append({"nbid": nb.id, "tram_only": tram_only, "data": nbdata, "nbname": nb.moveto,
                             "updated": human_time(datetime.datetime.now(), city=CITY_MAP[city_id])})
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
def ajax_stops_by_gps(request, metric_=None):
    us = get_user_settings(request)
    lat = request.POST.get('lat', "56.0029")
    lon = request.POST.get('lon', "92.93163")
    # bus_id = request.POST.get('bus_id', "")
    bus_name = request.POST.get('bus_name', "")
    accuracy = request.POST.get('accuracy', "100000")
    try:
        accuracy = float(accuracy)
    except:
        accuracy = 1000 * 1000
    if accuracy > 1000:
        return HttpResponse(ujson.dumps([]))
    now = datetime.datetime.now()

    if us:  # a
        sess = us.id
    else:
        sess = 'mobile'

    lon, lat = float(lon), float(lat)
    pnt = Point(lon, lat)

    nstops = NBusStop.objects.filter(point__distance_lte=(pnt, 600))
    current_nbusstop = nstops[:1]
    nstops = nstops.distinct('name')
    l = []
    pnt_x, pnt_y = pnt.x, pnt.y
    for q in nstops:
        dis = distance_meters(pnt_x, pnt_y, q.point.x, q.point.y)
        dis = dis / 10 * 10  # pretty number better
        ids = NBusStop.objects.filter(
            name=q.name, city=us.city).values_list('id', flat=True)
        # fuck this django.contrib.gis.db.models.query.GeoValuesListQuerySet
        ids = list(ids)
        l.append({"d": dis, "name": q.name, "ids": ids})
    l = sorted(l, key=lambda k: k['d'])
    l = l[:10]
    if current_nbusstop:
        current_nbusstop = current_nbusstop[0]
        l[0]['current_nbusstop'] = current_nbusstop.id
    serialized = ujson.dumps(l)

    data = [human_time(now, city=us.city), sess, lon, lat, accuracy, bus_name]
    if current_nbusstop:
        data.append(current_nbusstop.id)
        data.append(current_nbusstop.name)
    else:
        data.append(0)
        data.append("")
    data = {"city_monitor": data}
    pi = pickle_dumps(data)
    SOCK.send("ru.bustime.city_monitor__%s %s" % (us.city_id, pi))
    # change to rpc

    return HttpResponse(serialized)


# def realtime_km(request, city_id):
#     city = get_object_or_404(City, id=city_id)
#     ctx = {"city": city}
#     # response = HttpResponse(mimetype='application/vnd.google-earth.kml+xml')
#     response = HttpResponse()
#     response[
#         'Content-Disposition'] = 'attachment; filename=realtime-%s.kml' % city.id
#     response.write(render_to_string('realtime.kml', ctx))
#     return response


# def realtime_kml(request, city_id):
#     city_id = int(city_id)
#     kml = gemy.kml_render()
#     events = Event.objects.filter(bus__city__id=city_id).order_by("bus")
#     for event in events:
#         cache_key = "event_%s_%s" % (event.bus.city_id, event.uniqueid)
#         e = cache.get(cache_key)
#         if e:
#             ebd = e.busstop_nearest
#             if ebd:
#                 ebd = ebd.direction
#             p = kml.ggpoint(
#                 "bus-style", u"%s" % (e.busstop_nearest), u"%s\n%s\n%s->%s\n\n%skm/h, dir:%s" %
#                 (str(e.timestamp).split('.')[0], e.uniqueid, e.busstop_prev, e.busstop_nearest, e.speed, ebd), e.point.x, e.point.y)
#             kml.add_pnt(p)
#     response = HttpResponse()
#     for l in kml.write_xml():
#         response.write(l.encode('utf8'))
#     return response


def timer_bst_avg():
    timer_bst = cache.get("timer_bst")
    total = 0
    for k, v in timer_bst.iteritems():
        a, b = k.split('_')
        a = NBusStop.objects.get(id=a)
        b = NBusStop.objects.get(id=b)
        total += sum(v) / len(v)
    # print "Total AVG=", total/len(timer_bst)
    secs = total / len(timer_bst)
    cache.set("timer_bst_avg", secs)

    secs = 90 - secs
    if secs > 0:
        secs = "+%s" % secs
    else:
        secs = "%s" % secs
    cache.set("timer_bst_avg_osd", secs)
    return secs


def busstop_edit(request):
    page = request.GET.get('page', '1')
    us = get_user_settings(request)
    page = int(page)
    if request.POST:
        busstop, name, x, y, moveto = request.POST['busstop'], request.POST[
            'name'], request.POST['coord_x'], request.POST['coord_y'], request.POST['moveto']
        busstop = NBusStop.objects.get(id=int(busstop))
        x, y = float(x), float(y)
        #busstop.name = name
        busstop.moveto = moveto
        # busstop.point=Point(x,y,srid=4326)
        busstop.save()
        return HttpResponse("done")
    busstops = NBusStop.objects.filter(city=CITY_MAPN[u'Красноярск']).order_by(
        'id')[100 * (page - 1):100 * page]
    first = busstops[0]
    ctx = {"busstops": busstops, "first": first, "page": page + 1, "us": us}
    return arender(request, 'busstop_edit.html', ctx)


def reset_busfavor(request):
    us = get_user_settings(request)
    us.busfav = pickle_dumps({})
    us.save()
    return HttpResponseRedirect("/")


def help_view(request):
    us = get_user_settings(request)
    ctx = {'us': us}
    return arender(request, "help.html", ctx)


def contacts(request):
    us = get_user_settings(request)
    msg = request.POST.get('msg')
    if msg:
        log_message(msg, ttype="feedback", user=us)
        send_mail('msg from bustime.ru, us.id=%s' % us.id, msg[:1000], 'noreply@bustime.ru', ['andrey.perliev@gmail.com'], fail_silently=True)

    ctx = {'us': us, "msg": msg}
    return arender(request, "contacts.html", ctx)


def about(request):
    us = get_user_settings(request)
    ctx = {'us': us}
    return arender(request, "about.html", ctx)


def icon_editor(request):
    us = get_user_settings(request)
    now = datetime.datetime.now()
    trans = get_transaction(us)

    access = False
    if trans and trans.vip:
        access = True
    if not access:
        return HttpResponse("нет прав")

    icons = SpecialIcon.objects.all().order_by("id")
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
            if gosnum != i.gosnum:
                i.gosnum = gosnum
                i.save()

    ctx = {'us': us, "icons": icons}
    return arender(request, "icon_editor.html", ctx)


def pro(request):
    now = datetime.datetime.now()
    us = get_user_settings(request)
    transaction = get_transaction(us)

    ctx = {'us': us, "transaction": transaction}
    return arender(request, "pro.html", ctx)


def rating_(request, for_date=None):
    if not for_date:
        for_date = ""
    else:
        for_date="%s/" % for_date
    return HttpResponsePermanentRedirect(u"/spb/rating/%s" % for_date)



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
        for_date = map(int, for_date)
        for_date = datetime.date(for_date[0], for_date[1], 1)
        if for_date < datetime.date(2015, 6, 1):
            return HttpResponsePermanentRedirect(u"/%s/rating/" % city.slug)
    if old_url:
        return HttpResponsePermanentRedirect(u"/%s/rating/" % city.slug)

    vehicles = Status.objects.filter(
        bus__city=city, date__month=for_date.month)
    vehicles = vehicles.filter(rating_wilson__gt=0).order_by("-rating_wilson")
    comments = request.GET.get('comments')
    if comments:
        vehicles = vehicles.filter(comments__gt=0)

    pl = 1
    for v in vehicles:
        v.place = pl
        pl += 1

    paginator = Paginator(vehicles, 100)
    if request.GET.get('page'):
        return HttpResponsePermanentRedirect(u"./page-%s/" % request.GET.get('page'))
    try:
        vehicles = paginator.page(page)
    except PageNotAnInteger:
        vehicles = paginator.page(1)
    except EmptyPage:
        vehicles = paginator.page(paginator.num_pages)

    for v in vehicles.object_list:
        if v.comments > 0:
            v.messages = v.vote_set.filter(
                comment__isnull=False).exclude(comment="").order_by("id")

    ctx = {'us': us, "vehicles": vehicles,
           'now': now, 'city': city,
           'for_date': for_date,
           'page': page,
           'comments': comments
           }

    prev_month, next_month = None, None
    if now.date().month != for_date.month and for_date < now.date():
        next_month = for_date + relativedelta(months=1)
        ctx['next_month'] = next_month
    if for_date.year >= 2015 and for_date.month > 6:
        prev_month = for_date - relativedelta(months=1)
        ctx['prev_month'] = prev_month

    until = calendar.monthrange(now.year, now.month)[1] - now.day
    days = MORPH.parse(u'день')[0]
    until_day_word = days.make_agree_with_number(until).word
    ctx['until'] = until
    ctx['until_day_word'] = until_day_word

    return arender(request, "rating.html", ctx)


def schedule_(request, city_name):
    city = get_object_or_404(City, name__iexact=city_name)
    return HttpResponsePermanentRedirect(u"/%s/schedule/" %
                                         city.slug)


def schedule_bus_(request, city_name, bus_id):
    city = get_object_or_404(City, name__iexact=city_name)
    bus = get_object_or_404(Bus, id=bus_id)
    return HttpResponsePermanentRedirect(bus.get_absolute_url_schedule())


def schedule(request, city_name, old_url=None):
    us = get_user_settings(request)
    if old_url:
        city = get_object_or_404(City, name__iexact=city_name)
        return HttpResponsePermanentRedirect("/%s/schedule/" % (city.slug))
    else:
        city = get_object_or_404(City, slug=city_name)
    cc_key = "allbuses_%d" % city.id
    buses = cache.get(cc_key)
    if not buses:
        buses = list(
            Bus.objects.filter(active=True, city=city).order_by('order'))
    ctx = {'us': us, "city": city, "buses": buses}
    return arender(request, "schedule.html", ctx)


def weekday_dicto(now):
    d = {now.strftime('%a').lower(): True}
    return d


def schedule_bus(request, city_name, bus_id, old_url=None):
    us = get_user_settings(request)
    try:
        bus = get_object_or_404(Bus, id=int(bus_id))
        return HttpResponsePermanentRedirect(bus.get_absolute_url_schedule())
    except:
        bus = get_object_or_404(Bus, slug=bus_id, city__slug=city_name)
    if old_url:
        city = get_object_or_404(City, name__iexact=city_name)
        return HttpResponsePermanentRedirect("/%s/schedule/%s/" % (city.slug, bus_id))
    else:
        city = get_object_or_404(City, slug=city_name)
    now = datetime.datetime.now()
    now += datetime.timedelta(hours=bus.city.timediffk)
    weekday = weekday_dicto(now)

    route0 = Route.objects.filter(bus=bus, direction=0).order_by(
        'order').select_related('busstop')
    route1 = Route.objects.filter(bus=bus, direction=1).order_by(
        'order').select_related('busstop')

    for r in route0:
        r.times = Timetable.objects.filter(bus=bus, busstop=r.busstop,
                                           direction=0, **weekday).order_by('order', 'time').values_list('time', flat=True)

    for r in route1:
        r.times = Timetable.objects.filter(bus=bus, busstop=r.busstop,
                                           direction=1, **weekday).order_by('order', 'time').values_list('time', flat=True)

    ctx = {'us': us, "bus": bus, "city": bus.city}
    ctx['route0'] = route0
    ctx['route1'] = route1

    return arender(request, "schedule-bus.html", ctx)


def mobile_detect(request):
    # device = {}
    dos = None
    ua = request.META.get('HTTP_USER_AGENT', '').lower()
    if ua.find("iphone") > 0:
        #device['iphone'] = "iphone" + re.search("iphone os (\d)", ua).groups(0)[0]
        dos = "ios"
    if ua.find("ipad") > 0:
        #device['ipad'] = "ipad"
        dos = "ios"
    if ua.find("android") > 0:
        #device['android'] = "android" + re.search("android (\d\.\d)", ua).groups(0)[0].translate(None, '.')
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
def ajax_position_watch(request):
    lat = request.POST.get('lat')
    lon = request.POST.get('lon')
    try:
        us = get_user_settings(request)
        lon, lat = float(lon), float(lat)
        # pnt = Point(lon, lat)
    except:
        return HttpResponse("")

    events = REDIS.get("bdata_mode0_534")
    if events:
        events = pickle.loads(events)  # 2bus
    else:
        return HttpResponse("0")

    f = open('/tmp/position_watch.txt', 'a')
    f.write("%s;\n" % (datetime.datetime.now()))
    f.close()

    if events:
        dst_best = 1000
        events = events['l']
        candidate = ""
        uniqueid_to_gosnum = cache.get("uniqueid_to_gosnum", {})
        for e in events:
            dst = distance_meters(lon, lat, e['x'], e['y'])
            if dst < dst_best:
                dst_best = dst
                candidate = e['u']
        if candidate:
            old = uniqueid_to_gosnum.get('ЕК428', [])
            if len(old) == 3 and len(set(old)) == 1 and candidate == old[0]:
                for k, v in uniqueid_to_gosnum.items():
                    if v == 'ЕК428':
                        del uniqueid_to_gosnum[k]
                uniqueid_to_gosnum[candidate] = 'ЕК428'
            else:
                old.append(candidate)
                uniqueid_to_gosnum['ЕК428'] = old[-3:]
        cache.set("uniqueid_to_gosnum", uniqueid_to_gosnum)

    f = open('/tmp/position_watch.txt', 'a')
    f.write("%s;%s;%s;%s\n" % (
        datetime.datetime.now(), us.id, candidate, uniqueid_to_gosnum.get('ЕК428')))
    f.close()
    return HttpResponse("1")


@csrf_exempt
def ajax_radio_position(request):
    now = int(time.time() * 1000)
    curtrack = (now / 60 * 60 * 1000) % 26
    curtrack = 26 - curtrack
    # curtime = now%3610330
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
    # if us.busfavor:
    #     busfavor = pickle.loads(str(us.busfav))
    #     busfavor = sorted(busfavor.iteritems(), key=operator.itemgetter(1))
    #     busfavor.reverse()
    #     busfavor = busfavor[:us.busfavor_amount]
    #     busfavor = map(lambda x: x[0], busfavor)

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
    now = datetime.datetime.now()
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


def monitor(request, city_name=None):
    if not city_name:
        return HttpResponsePermanentRedirect(u"/spb/monitor/")

    city = City.objects.filter(name__iexact=city_name)
    if city:
        city = city[0]
        return HttpResponsePermanentRedirect("/%s/monitor/" % city.slug)
    city = get_object_or_404(City, slug=city_name)
    us = get_user_settings(request)
    us.city = city
    ctx = {'us': us, "city": city, "main_page": True}
    return arender(request, "monitor.html", ctx)


@csrf_exempt
def pin(request):
    now = datetime.datetime.now()
    us = get_user_settings(request)
    pin = request.POST.get('pin', '')

    tr = Transaction.objects.filter(pin=pin).order_by('-id')
    if tr:
        tr = tr[0]
    else:
        return bonus_activate(request, us, pin)

    f = open('/tmp/bustime_pin.csv', 'a')
    f.write("%s %s -> %s\n" % (now, tr.user.id, us.id))
    f.close()

    premium_deactivate(tr.user)
    wsocket_cmd(tr.user_id, 'reload', {})
    tr.user = us
    tr.notified = False
    tr.save()

    premium_activate(us)
    wsocket_cmd(us.id, 'reload', {})

    return HttpResponseRedirect("/")


def bonus_activate(request, us, pin):
    b = Bonus.objects.filter(pin=pin).order_by('-id')
    if not b:
        return arender(request, "message.html", {"message": u"Неверный пин код %s"%pin})
    else:
        b = b[0]

    if b.activated:
        msg = "Пин код уже был активирован %s, %s:%s" % (
            b.mtime.date(), b.mtime.hour, b.mtime.minute)
        return arender(request, "message.html", {"message": msg})

    comment = "bonus, id=%s, comment=%s" % (b.id, b.comment)

    now = datetime.datetime.now()
    transaction = get_transaction(us)
    if transaction:
        end_time = transaction.end_time + datetime.timedelta(days=b.days)
        comment = comment + ", extended"
    else:
        end_time = now + datetime.timedelta(days=b.days)
        premium_activate(us)

    Transaction.objects.create(
        user=us, key="premium",
        value=b.days, fiat=b.fiat,
        comment=comment,
        end_time=end_time)

    b.activated = True
    b.save()

    return HttpResponseRedirect("/")


def city_slug_redir(request, force_city):
    city = CITY_MAP[force_city]
    return HttpResponsePermanentRedirect(u"/%s/" % city.slug)


def settings_view(request):
    us = get_user_settings(request)
    transaction = get_transaction(us)
    ctx = {"us": us, "transaction": transaction}

    if not request.POST:
        return render(request, "settings.html", ctx)

    for k in ["sound", "sound_plusone", "gps_off", "speed_show", "multi_all", "font_big"]:
        setting, value = k, request.POST.get(k)
        if value:
            value = True
        else:
            value = False
        setattr(us, setting, value)
    busfavor_amount = request.POST.get("busfavor_amount", "10")
    busfavor_amount = int(busfavor_amount)
    if busfavor_amount in [5, 10, 20, 30]:
        us.busfavor_amount = busfavor_amount
    us.save()

    return HttpResponseRedirect("/")


def radar(request):
    us = get_user_settings(request)
    transaction = get_transaction(us)
    ctx = {"us": us, "transaction": transaction, "main_page": True}
    return arender(request, "radar.html", ctx)
