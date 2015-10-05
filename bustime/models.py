# -*- coding: utf-8 -*-
import cPickle as pickle
import datetime
import math
import random
import redis
import requests
from django.contrib.gis.db import models
from django.core.cache import cache
from transliterate import transliterate
import logging
import pymorphy2
from django.utils.encoding import smart_unicode
# from django.contrib.sessions.models import Session
# from django.db.models import Avg
# from django.core.urlresolvers import reverse
# import ujson
#  StrictRedis vs Redis make no backwars compatibility
REDIS = redis.StrictRedis(db=0)
MORPH = pymorphy2.MorphAnalyzer()

"""
███████╗██╗00██╗██████╗0██╗██╗00000██╗00000███████╗██╗00██╗
██╔════╝██║0██╔╝██╔══██╗██║██║00000██║00000██╔════╝╚██╗██╔╝
███████╗█████╔╝0██████╔╝██║██║00000██║00000█████╗000╚███╔╝0
╚════██║██╔═██╗0██╔══██╗██║██║00000██║00000██╔══╝000██╔██╗0
███████║██║00██╗██║00██║██║███████╗███████╗███████╗██╔╝0██╗
╚══════╝╚═╝00╚═╝╚═╝00╚═╝╚═╝╚══════╝╚══════╝╚══════╝╚═╝00╚═
"""

THEME_CHOICES = (
    (0, 'Оригинальная'),
    (1, 'Оливковая'),
    (2, 'Хэллоуин'),
    (3, 'Карбон'),
    (4, 'Инкогнито'),
    (5, 'Ковбой Джо'),
    (6, 'Пижон'),
    (7, 'Кровь и Песок'),
    (8, '8 Бит'),
    (9, 'Sk8t kid'),
    (10, 'День Валентина'),
    (11, 'Новый Год 2015'),
    (12, 'Игры престолов'),
)

MODE_CHOICES = (
    (0, 'Я Пассажир'),
    (1, 'Мульти-пассажир'),
    (2, 'На Карте'),
)

TTYPE_CHOICES = (
    (0, 'Автобус'),
    (1, 'Троллейбус'),
    (2, 'Трамвай'),
    (3, 'Маршрутное такси'),
    (4, 'Аквабус'),
)

VF_VOICE_CHOICES = (
    (0, 'Анна'),
    (1, 'Мария'),
    (2, 'Лидия'),
    (3, 'Александр'),
    (4, 'Владимир'),
)

ZSUB = "tcp://127.0.0.1:15555"
ZPUB = "tcp://127.0.0.1:15556"
ZSUBGATE = "tcp://127.0.0.1:15557"


class City(models.Model):
    active = models.BooleanField(default=True)
    name = models.CharField(max_length=64)
    name_gde = models.CharField(max_length=64, null=True, blank=True)
    name_o = models.CharField(max_length=64, null=True, blank=True)
    timediffk = models.IntegerField(default=0)
    wunderground = models.CharField(max_length=64, null=True, blank=True)
    point = models.PointField(srid=4326, null=True, blank=True)
    slug = models.CharField(max_length=64, null=True, blank=True)
    objects = models.GeoManager()

    def __unicode__(self):
        return self.name
    def __unicode__(self):
        return self.name
    def get_absolute_url(self):
        return u"/%s/" % self.slug
    def get_absolute_url_classic(self):
        return u"/%s/classic/" % self.slug

# caching.base.CachingMixin,
class Bus(models.Model):
    active = models.BooleanField(default=True)
    name = models.CharField(max_length=128)
    distance = models.FloatField(null=True, blank=True)
    travel_time = models.FloatField(null=True, blank=True)  # in minutes
    description = models.CharField(max_length=128, null=True, blank=True)
    order = models.IntegerField(null=True, blank=True, db_index=True)
    murl = models.CharField(max_length=128, null=True, blank=True)
    ttype = models.IntegerField(null=True, blank=True, choices=TTYPE_CHOICES)
    napr_a = models.CharField(max_length=128, null=True, blank=True)
    napr_b = models.CharField(max_length=128, null=True, blank=True)
    route_start = models.CharField(max_length=64, null=True, blank=True)
    route_stop = models.CharField(max_length=64, null=True, blank=True)
    route_real_start = models.DateTimeField(null=True, blank=True)
    route_real_stop = models.DateTimeField(null=True, blank=True)
    route_length = models.CharField(max_length=64, null=True, blank=True)
    city = models.ForeignKey(City, null=True, blank=True)
    xeno_id = models.BigIntegerField(null=True, blank=True)
    discount = models.BooleanField(default=False)
    provider_name = models.CharField(max_length=128, null=True, blank=True)
    provider_contact = models.CharField(max_length=128, null=True, blank=True)
    provider_phone = models.CharField(max_length=128, null=True, blank=True)
    tt_xeno_reversed = models.NullBooleanField()
    slug = models.CharField(max_length=64, null=True, blank=True)
    # objects = caching.base.CachingManager()

    def __unicode__(self):
        if not self.ttype or self.ttype == 0:
            prefix = ''
        elif self.ttype == 1:
            prefix = u'Т'
        elif self.ttype == 2:
            prefix = u'ТВ'
        elif self.ttype == 3:
            prefix = ''
        return u"%s%s" % (prefix, self.name)

    def get_absolute_url(self):
        return u"/%s/%s/" % (self.city.slug, self.slug)
    def get_absolute_url_classic(self):
        return u"/%s/classic/%s/" % (self.city.slug, self.slug)
    def get_absolute_url_schedule(self):
        return u"/%s/schedule/%s/" % (self.city.slug, self.slug)

    def amount_a(self, direction=0):
        l = self.bdata_mode0(direction=direction)
        if l != None:
            l = len(set(l['stops']))
        return l

    def amount_b(self, direction=1):
        l = self.bdata_mode0(direction=direction)
        if l != None:
            l = len(set(l['stops']))
        return l

    def amount(self):
        a = self.amount_a()
        b = self.amount_b()
        if a == None and b == None:
            return None
        if a == None:
            a = "-"
        if b == None:
            b = "-"
        return "%s/%s" % (a, b)

    def amount_int(self):
        l = self.bdata_mode0()
        if not l:
            return 0
        s = len(l[0]['stops'])
        if l.has_key(1):
            s += len(l[1]['stops'])
        return s

    def bdata_mode0(self, direction=None):
        bdata = rcache_get("bdata_mode0_%s" % self.id)
        if not bdata:
            return None
        if direction is not None:
            bdata = bdata[direction]
        return bdata

    def ttype_name(self):
        n = "неизвестный"
        if self.ttype == 0:
            n = "Автобус"
        elif self.ttype == 1:
            n = "Троллейбус"
        elif self.ttype == 2:
            n = "Трамвай"
        elif self.ttype == 3:
            n = "Маршрутное такси"
        elif self.ttype == 4:
            n = "Аквабус"
        return n

    def ttype_names(self):
        n = "неизвестный"
        if self.ttype == 0:
            n = "Автобусы"
        elif self.ttype == 1:
            n = "Троллейбусы"
        elif self.ttype == 2:
            n = "Трамваи"
        elif self.ttype == 3:
            n = "Маршрутные такси"
        elif self.ttype == 4:
            n = "Аквабусы"
        return n

    def ttype_slug(self):
        if self.ttype == 0:
            ttype_name = "bus"
        elif self.ttype == 1:
            ttype_name = "trolleybus"
        elif self.ttype == 2:
            ttype_name = "tram"
        elif self.ttype == 3:
            ttype_name = "bus-taxi"
        elif self.ttype == 4:
            ttype_name = "aquabus"
        return ttype_name

    def save(self, *args, **kwargs):
        if not self.slug:
            n = transliterate(self.name)
            self.slug = u"%s-%s" % (self.ttype_slug(), n)
        super(Bus, self).save(*args, **kwargs)


class Tcard(models.Model):
    num = models.CharField(max_length=20)
    balance_rub = models.FloatField(null=True, blank=True)
    balance_trips = models.SmallIntegerField(null=True, blank=True)
    black = models.BooleanField(default=0)  # black listed card
    created = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    # last time user requested this card
    checked = models.DateTimeField(null=True, blank=True)
    # last time update happened
    updated = models.DateTimeField(null=True, blank=True)
    response_raw = models.TextField(null=True, blank=True)
    social = models.BooleanField(default=False)

    def __unicode__(self):
        return u"%s: %s %s" % (self.num, self.balance_rub, self.balance_trips)

    def save(self, *args, **kwargs):
        if len(self.num) == 12:
            self.social = True
        super(Tcard, self).save(*args, **kwargs)

    @property
    def balance(self):
        if self.social:
            return self.balance_trips
        else:
            return self.balance_rub

    def update(self):
        now = datetime.datetime.now()
        if now.date() == self.updated.date():
            return self.balance
        q = "get_tc_info"
        if self.social:
            q = "get_sc_info"
        payload = {"id": q, "params":
                   '{"card_num":"%s"}' % self.num, "username": "bustime"}
        try:
            r = requests.post(
                'https://api.krasinform.ru/gate/ki-transport-api/', payload, verify=False, timeout=5)
            j = r.json()
        except:
            return self.balance
        if j.get('err_code'):  # and j.get('err_code') == 1:
            self.black = True
        else:
            self.black = False
            self.response_raw = r.text
            if self.social:
                self.balance_trips = int(j['LEFT_BASE_TRIPS'])
            else:
                self.balance_rub = j['BALANCE'][0]['VAL']
                self.balance_rub = self.balance_rub.split(' ')[0]
                self.balance_rub = float(self.balance_rub)
        self.updated = now
        self.save()
        if self.black:
            return None
        return self.balance

    def warning(self):
        if self.social:
            if self.balance_trips<5:
                return True
            else:
                return False
        else:
            if self.balance_rub<5*19:
                return True
            else:
                return False


class Passenger(models.Model):
    bus = models.ForeignKey(Bus)
    name = models.CharField(max_length=128, null=True, blank=True)
    amount = models.IntegerField(null=True, blank=True)

    def __unicode__(self):
        return self.name


class Conn(models.Model):
    ip = models.CharField(max_length=255, null=True, blank=True)
    ua = models.CharField(max_length=128, null=True, blank=True)
    ctime = models.DateTimeField(auto_now_add=True)
    etime = models.DateTimeField(auto_now=True, null=True, blank=True)

    def __unicode__(self):
        return self.ip


class UserSettings(models.Model):
    ctime = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    mtime = models.DateTimeField(auto_now=True, null=True, blank=True)
    session_key = models.CharField(
        max_length=32, null=True, blank=True, unique=True, db_index=True)
    # session = models.ForeignKey(Session, null=True, blank=True)
    key = models.CharField(max_length=32, null=True, blank=True, db_index=True)
    username = models.CharField(max_length=32, null=True, blank=True)
    password = models.CharField(max_length=32, null=True, blank=True)
    level_date = models.TextField(null=True, blank=True)
    referral = models.CharField(max_length=32, null=True, blank=True)
    busfav = models.BinaryField(null=True, blank=True)
    busfavor_amount = models.SmallIntegerField(default=5)
    stars = models.SmallIntegerField(default=0, null=True, blank=True)
    comment = models.CharField(max_length=256, null=True, blank=True)
    premium = models.BooleanField(default=0)
    vip = models.BooleanField(default=0)

    noads = models.BooleanField(default=0)
    theme = models.SmallIntegerField(default=0, choices=THEME_CHOICES)
    theme_save = models.SmallIntegerField(null=True, blank=True)
    mode = models.SmallIntegerField(default=1, choices=MODE_CHOICES)
    sound = models.BooleanField(default=1)
    sound_plusone = models.BooleanField(default=False)
    gps_off = models.BooleanField(default=0)
    city = models.ForeignKey(City, null=True, blank=True)
    tcard = models.CharField(max_length=20, null=True, blank=True)

    ip = models.GenericIPAddressField(null=True, blank=True)
    ua = models.CharField(max_length=512, null=True, blank=True)

    vk_like_pro = models.SmallIntegerField(default=0)
    theme_stripes = models.BooleanField(default=1)
    pro_demo = models.BooleanField(default=False)
    pro_demo_date = models.DateTimeField(null=True, blank=True)
    multi_all = models.BooleanField(default=False)
    matrix_show = models.BooleanField(default=True)
    map_show = models.BooleanField(default=False)
    speed_show = models.BooleanField(default=False)
    font_big = models.BooleanField(default=False)

    def __unicode__(self):
        return "%s" % self.id

    def save(self, *args, **kwargs):
        if not self.premium and not self.pro_demo:
            self.busfavor_amount = 5
        super(UserSettings, self).save(*args, **kwargs)


class Log(models.Model):
    date = models.DateTimeField(auto_now_add=True)
    ttype = models.CharField(max_length=16, null=True, blank=True)
    message = models.CharField(max_length=140)
    user = models.ForeignKey(UserSettings, null=True, blank=True)

    def __unicode__(self):
        return self.message


class Transaction(models.Model):
    ctime = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(UserSettings)
    key = models.CharField(
        max_length=64, null=True, blank=True, default="premium")
    value = models.FloatField(null=True, blank=True, default=30)
    fiat = models.SmallIntegerField(null=True, blank=True, default=300)
    comment = models.TextField(null=True, blank=True)
    phone = models.CharField(max_length=80, null=True, blank=True)
    gosnum = models.CharField(max_length=16, null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    notified = models.BooleanField(default=False)
    pin = models.CharField(max_length=16, null=True, blank=True)
    vip = models.BooleanField(default=0)

    def __unicode__(self):
        return "%s_%s_%s" % (self.user.session_key[:6], self.ctime, self.fiat)

    def save(self, *args, **kwargs):
        if not self.pin:
            self.pin = "%d-%d-%d" % (
                random.randint(100, 999),
                random.randint(100, 999),
                random.randint(100, 999))
        super(Transaction, self).save(*args, **kwargs)

    @property
    def warning(self):
        delta = self.end_time - datetime.timedelta(days=2)
        if datetime.datetime.now() > delta:
            return True
        else:
            return False
    @property
    def countdown(self):
        delta = self.end_time - datetime.datetime.now()
        delta_days = delta.days + 1
        if delta_days > 1:
            ed = MORPH.parse(u'день')[0]
            amount = delta_days
        else:
            ed = MORPH.parse(u'час')[0]
            amount = int(delta.total_seconds() / 60 / 60)
        word = ed.make_agree_with_number(amount).word
        ost = MORPH.parse(u'осталось')[0]
        ost = ost.make_agree_with_number(amount).word
        return u"%s %s %s" % (ost, amount, word)

class SpecialIcon(models.Model):
    ctime = models.DateTimeField(auto_now_add=True)
    mtime = models.DateTimeField(auto_now=True)
    # user = models.ForeignKey(UserSettings, null=True, blank=True)
    # transaction = models.ForeignKey(UserSettings, null=True, blank=True)
    gosnum = models.CharField(max_length=16, null=True, blank=True)
    active = models.BooleanField(default=True)
    img = models.CharField(max_length=80, null=True, blank=True)

    def __unicode__(self):
        return self.gosnum

    def save(self, *args, **kwargs):
        super(SpecialIcon, self).save(*args, **kwargs)
        cc_key = "SpecialIcons"
        specialicons = list(SpecialIcon.objects.filter(active=True))
        cache.set(cc_key, specialicons)


class Bonus(models.Model):
    ctime = models.DateTimeField(auto_now_add=True)
    mtime = models.DateTimeField(auto_now=True)
    activated = models.BooleanField(default=False)
    pin = models.CharField(max_length=16, null=True, blank=True)
    days = models.SmallIntegerField(default=5)
    comment = models.TextField(null=True, blank=True)
    fiat = models.SmallIntegerField(null=True, blank=True, default=0)

    def save(self, *args, **kwargs):
        if not self.pin:
            self.pin = "%d-%d-%d" % (
                random.randint(100, 999),
                random.randint(100, 999),
                random.randint(100, 999))
        super(Bonus, self).save(*args, **kwargs)


class UserTimer(models.Model):
    user = models.ForeignKey(UserSettings)
    date = models.DateField(db_index=True)
    minutes = models.SmallIntegerField(default=0)
    pro_minutes = models.SmallIntegerField(default=0)

    def __unicode__(self):
        return "%s_%s_%s" % (self.user.session_key[:6], self.date, self.minutes)


class NBusStop(models.Model):  # caching.base.CachingMixin,
    city = models.ForeignKey(City, null=True, blank=True)
    name = models.CharField(max_length=128)
    name_alt = models.CharField(max_length=128, null=True, blank=True)
    point = models.PointField(srid=4326, null=True, blank=True)
    moveto = models.CharField(max_length=128, null=True, blank=True)
    xeno_id = models.BigIntegerField(null=True, blank=True)
    tram_only = models.BooleanField(default=False)
    #root = models.BooleanField(default=False)
    objects = models.GeoManager()

    def __unicode__(self):
        return u"%s_%s" % (self.name, self.id)


class Route(models.Model):
    bus = models.ForeignKey(Bus)
    busstop = models.ForeignKey(NBusStop)
    endpoint = models.BooleanField(default=False)
    direction = models.SmallIntegerField(null=True, blank=True)
    order = models.IntegerField(null=True, blank=True, db_index=True)
    # среднее время прохождения от предыдущей остановки
    time_avg = models.IntegerField(null=True, blank=True)
    xeno_id = models.BigIntegerField(null=True, blank=True)

    objects = models.GeoManager()

    def __unicode__(self):
        return u"%s: %s, d=%s" % (self.bus, self.busstop, self.direction)


# class Event(models.Model):

#     """
#     UniqueID;NRD_Title;NRD_Grafic;TimeNav;Latitude;Longitude;Speed;Azimuth
#     4951000;76;19;2012-12-03 07:06:26.000;56.102067;92.921612;8;242
#     """
#     uniqueid = models.CharField(
#         max_length=12, null=True, blank=True, db_index=True)
#     timestamp = models.DateTimeField(db_index=True)
#     last_changed = models.DateTimeField(null=True, blank=True)
#     point_prev = models.PointField(srid=4326, null=True, blank=True)
#     point = models.PointField(srid=4326)
#     bus = models.ForeignKey(Bus)
#     #number = models.IntegerField(null=True, blank=True)
#     heading = models.FloatField(null=True, blank=True)
#     speed = models.FloatField(null=True, blank=True)
#     busstop_next = models.ForeignKey(
#         Route, null=True, blank=True, related_name="busstop_next")
#     busstop_nearest = models.ForeignKey(Route, null=True, blank=True)
#     busstop_prev = models.ForeignKey(
#         Route, null=True, blank=True, related_name="busstop_prev")
#     direction = models.SmallIntegerField(null=True, blank=True)
#     dchange = models.SmallIntegerField(null=True, blank=True)
#     sleeping = models.BooleanField(default=False)
#     ramp = models.BooleanField(default=False)
#     zombie = models.BooleanField(default=False)
#     gosnum = models.CharField(max_length=12, null=True, blank=True)
#     x = models.FloatField(null=True, blank=True)
#     y = models.FloatField(null=True, blank=True)
#     x_prev = models.FloatField(null=True, blank=True)
#     y_prev = models.FloatField(null=True, blank=True)
#     last_point_update = models.DateTimeField(null=True, blank=True)
#     objects = models.GeoManager()

#     def __unicode__(self):
#         return u"#%s %s->%s" % (self.bus, self.busstop_prev, self.busstop_nearest)

#     def get_absolute_url(self):
#         return "/event/%d/" % self.id

#     def as_dict(self):
#         d = {}
#         d["bus_name"] = self.bus.name
#         for k, v in self.__dict__.items():
#             if not k.startswith('_'):
#                 if type(v) == datetime.datetime:
#                     d[k] = str(v)
#                 elif k == "busstop_nearest_id" and self.busstop_nearest:
#                     d["bn"] = self.busstop_nearest.busstop.name
#                 else:
#                     d[k] = v
#         if d.get("point"):
#             d["point_x"] = d['point'].x
#             d["point_y"] = d['point'].y
#             del d["point"]
#         if d.get("point_prev"):
#             d["point_prev_x"] = d['point_prev'].x
#             d["point_prev_y"] = d['point_prev'].y
#             del d["point_prev"]
#         return d


class Event(dict):
        """
        performance heaven
        """
        @property
        def uniqueid(self):
            return self.get("uniqueid")

        @property
        def timestamp(self):
            return self.get("timestamp")

        @property
        def last_changed(self):
            return self.get("last_changed")

        @property
        def bus(self):
            return self.get("bus")

        @property
        def bus_id(self):
            if self.bus:
                return self.bus.id
            else:
                return None

        @property
        def heading(self):
            return self.get("heading")

        @property
        def speed(self):
            return self.get("speed")

        @property
        def busstop_next(self):
            return self.get("busstop_next")

        @property
        def busstop_nearest(self):
            return self.get("busstop_nearest")

        @property
        def busstop_prev(self):
            return self.get("busstop_prev")

        @property
        def direction(self):
            return self.get("direction")

        @property
        def dchange(self):
            return self.get("dchange")

        @property
        def sleeping(self):
            return self.get("sleeping", False)

        @property
        def ramp(self):
            return self.get("ramp", False)

        @property
        def zombie(self):
            return self.get("zombie", False)

        @property
        def gosnum(self):
            return self.get("gosnum")

        @property
        def x(self):
            return self.get("x")

        @property
        def y(self):
            return self.get("y")

        @property
        def x_prev(self):
            return self.get("x_prev")

        @property
        def y_prev(self):
            return self.get("y_prev")

        @property
        def last_point_update(self):
            return self.get("last_point_update")

        def as_dict(self):
            d = dict()
            d["bus_name"] = self.bus.name
            d["bus_id"] = self.bus.id
            for k, v in self.items():
                if type(v) == datetime.datetime:
                    d[k] = str(v)
                elif k == "busstop_nearest" and self.busstop_nearest:
                    d["bn"] = self.busstop_nearest.busstop.name
                elif type(v) == Bus or type(v) == Route:
                    pass
                else:
                    d[k] = v
            if d.get("x"):
                d["point_x"] = self.x
                d["point_y"] = self.y
            if d.get("x_prev"):
                d["point_prev_x"] = self.x_prev
                d["point_prev_y"] = self.y_prev
            return d


class Timetable(models.Model):
    bus = models.ForeignKey(Bus)
    busstop = models.ForeignKey(NBusStop)
    direction = models.SmallIntegerField(null=True, blank=True)
    time = models.TimeField(db_index=True)
    holiday = models.BooleanField(default=False)
    xeno_title = models.CharField(max_length=128, null=True, blank=True)
    order = models.IntegerField(null=True, blank=True, db_index=True)

    mon = models.BooleanField(default=False)
    tue = models.BooleanField(default=False)
    wed = models.BooleanField(default=False)
    thu = models.BooleanField(default=False)
    fri = models.BooleanField(default=False)
    sat = models.BooleanField(default=False)
    sun = models.BooleanField(default=False)

    def __unicode__(self):
        return u"%s-%s-%s" % (self.bus, self.busstop, self.time)


class Sound(models.Model):
    text = models.TextField()
    voice = models.IntegerField(
        null=True, blank=True, choices=VF_VOICE_CHOICES)


class IPcity(models.Model):
    ctime = models.DateTimeField(auto_now_add=True)
    ip = models.GenericIPAddressField()
    city = models.ForeignKey(City)
    whois_results = models.TextField(blank=True, null=True)
    default_drop = models.BooleanField(default=False)

    def __unicode__(self):
        return "%s-%s" % (self.ip, self.city.name)


class Song(models.Model):
    ctime = models.DateTimeField(auto_now_add=True)
    url = models.CharField(max_length=128, null=True, blank=True)
    name = models.CharField(max_length=128, null=True, blank=True)
    name_short = models.CharField(max_length=64, null=True, blank=True)
    lucky = models.BooleanField(default=False)
    skip_seconds = models.IntegerField(default=39, null=True, blank=True)
    active = models.BooleanField(default=True)

    def __unicode__(self):
        return "%s" % (self.name_short)


class Status(models.Model):
    date = models.DateField()
    uniqueid = models.CharField(max_length=12, null=True, blank=True)
    gosnum = models.CharField(max_length=16, null=True, blank=True)
    bus = models.ForeignKey(Bus, null=True, blank=True)
    ava_driver = models.CharField(
        max_length=3, null=True, blank=True, default="001")
    ava_conductor = models.CharField(
        max_length=3, null=True, blank=True, default="500")
    # rating_driver = models.FloatField(default=0, null=True, blank=True)
    # rating_conductor = models.FloatField(default=0, null=True, blank=True)
    rating_wilson = models.FloatField(default=0, null=True, blank=True)
    votes_wilson = models.SmallIntegerField(default=0)
    # votes_driver = models.SmallIntegerField(default=0, null=True, blank=True)
    # votes_conductor = models.SmallIntegerField(default=0, null=True,
    #                                            blank=True)
    comments = models.SmallIntegerField(
        default=0, null=True, blank=True)
    comments_driver = models.SmallIntegerField(
        default=0, null=True, blank=True)
    comments_conductor = models.SmallIntegerField(
        default=0, null=True, blank=True)

    def __unicode__(self):
        return u"%s: %s - %s" % (self.date, self.gosnum, self.rating_wilson)

    @property
    def rating_wilson_human(self):
        if self.rating_wilson:
            return round(self.rating_wilson * 5, 3)
        else:
            return 0


class Vote(models.Model):
    ctime = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(UserSettings)
    status = models.ForeignKey(Status, null=True, blank=True)
    # 0-driver, 1-conductor
    target = models.SmallIntegerField(default=0, null=True, blank=True)
    positive = models.BooleanField(default=True)
    comment = models.CharField(max_length=80, null=True, blank=True)

    def __unicode__(self):
        return u"%s-%s-%s" % (self.status, self.user, self.positive)

    def save(self, *args, **kwargs):
        super(Vote, self).save(*args, **kwargs)

        votes = Vote.objects.filter(status=self.status)
        self.status.votes_wilson = votes.count()
        pos = votes.filter(positive=True).count()
        rating_ = wilson_rating(pos, self.status.votes_wilson)
        # print self.status.votes_wilson, pos, rating_
        self.status.rating_wilson = float("%.3f" % rating_)
        self.status.comments = votes.filter(comment__isnull=False) \
                                    .exclude(comment="").count()
        self.status.save()


# from math import radians, cos, sin, asin, sqrt
# def distance_meters2(pnt1, pnt2):
#         """
#         haversine formula
#         Calculate the great circle distance between two points
#         on the earth (specified in decimal degrees)
#         """
# convert decimal degrees to radians
#         lon1, lat1, lon2, lat2 = map(radians, [pnt1.x, pnt1.y, pnt2.x, pnt2.y])
#         dlon = lon2 - lon1
#         dlat = lat2 - lat1
#         a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
#         c = 2 * asin(sqrt(a))
#         return int(6378100 * c)


def distance_meters(lon1, lat1, lon2, lat2):
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])
    R = 6378100
    x = (lon2 - lon1) * math.cos(0.5 * (lat2 + lat1))
    y = lat2 - lat1
    return int(R * math.sqrt(x * x + y * y))


def backoffice_statlos(data=None):
    cc_key = "backoffice_stats"
    if data:
        cache.set(cc_key, data)
    else:
        return cache.get(cc_key, {})


def premium_activate(us):
    us.premium = True
    us.pro_demo = False
    us.busfavor_amount = 10
    us.gps_off = True
    us.speed_show = True
    us.save()
    return True


def premium_deactivate(us):
    us.premium = False
    us.busfavor_amount = 5
    us.gps_off = False
    us.speed_show = False
    us.multi_all = False
    us.save()
    return True


def pickle_dumps(x):
    return pickle.dumps(x, protocol=pickle.HIGHEST_PROTOCOL)


def rcache_get(key):
    pdata = REDIS.get(key)
    if pdata:
        pdata = pickle.loads(pdata)
    return pdata


def rcache_set(key, value, *args):
    value = pickle_dumps(value)
    if args:
        REDIS.set(key, value, args[0])
    else:
        REDIS.set(key, value)


def log_message(message, ttype=None, user=None):
    Log.objects.create(message=message[:140], ttype=ttype, user=user)
    return True


def wilson_rating(pos, n):
    """
    Lower bound of Wilson score confidence interval for a Bernoulli parameter
    pos is the number of positive votes, n is the total number of votes.
    https://gist.github.com/honza/5050540
    http://www.evanmiller.org/how-not-to-sort-by-average-rating.html
    http://amix.dk/blog/post/19588

    wilson_rating(600, 1000)
    wilson_rating(5500, 10000)
    """
    z = 1.44  # 1.44 = 85%, 1.96 = 95%
    phat = 1.0 * pos / n

    return (phat + z*z/(2*n) - z * math.sqrt((phat*(1-phat)+z*z/(4*n))/n))/(1+z*z/n)

#
# mini cache
#

CITY_MAP, CITY_MAPN = {}, {}
for city in City.objects.all():  # active=True
    CITY_MAP[city.id] = city
    CITY_MAPN[city.name] = city


BUSSTOPS_POINTS = {}
for busstop in NBusStop.objects.all():  # city__id__in=[3,4]
    BUSSTOPS_POINTS[busstop.id] = (busstop.point.x, busstop.point.y)


BUS_BY_NAME = {}  # it contains id of bus, to not take more memory
BUS_BY_ID = {}
for bus in Bus.objects.all():  # filter(active=True, city__active=True):
    if bus.active and bus.city.active:
        cc_key = "ts_%s_%s_%s" % (bus.city_id, bus.ttype, bus.name)
        BUS_BY_NAME[cc_key] = bus.id
        BUS_BY_ID[bus.id] = bus


def bus_get(bus_id):
    return BUS_BY_ID.get(bus_id)
    # bus = rcache_get("bustime__b%s" % bus_id)
    # if not bus:
    #     try:
    #         bus = Bus.objects.get(id=bus_id)
    #         cache.set("bustime__b%s" % bus_id, bus, 60 * 60 * 24)
    #     except:
    #         return None  # no bus no probs
    # return bus


def get_bus_by_name(city, name, ttype):
    if city.id == 3 and ttype == 1 and name == "18":
        ttype = 0
    # if city.id == 5 and name.startswith('К-'):  # К-408
    #     ttype = 3
    #     name = name.split('-')[1]

    cc_key = u"ts_%s_%s_%s" % (city.id, ttype, smart_unicode(name))
    bus_id = BUS_BY_NAME.get(cc_key)
    if not bus_id:
        logger = logging.getLogger(__name__)
        logger.warn(
            "get_bus_by_name not found: name=%s, type=%s, city=%s" %
            (name, ttype, city.id))
        bus = False
    else:
        bus = BUS_BY_ID[bus_id]
    return bus
