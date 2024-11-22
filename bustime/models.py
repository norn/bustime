# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function

import codecs
import csv
import copy
import datetime
import hashlib
import io
import itertools
import logging
import math
import operator
import os
import random
import re
import string
# для корректной работы всякого вида encode/decode с utf-8
import sys
import time
import traceback
from base64 import b64decode, b64encode
from collections import namedtuple
from enum import IntEnum, Enum

from django.contrib.gis.measure import D
from django.utils.functional import SimpleLazyObject
import msgpack
import networkx as nx
import redis
import requests
import six
import six.moves.cPickle as pickle
import ujson as json
from bustime._cdistance import cdistance
from timezone_field import TimeZoneField
from timezonefinder import TimezoneFinder
import pytz
from phonenumber_field.modelfields import PhoneNumberField
from bustime.exceptions import BusNotFoundException, StopNotFoundException

from bustime.tcards import *
from bustime.utils import day_after_week, nslugify, dictfetchall, lava_sort_up    # nslugify('Loděnice (okres Beroun)')='loděnice-okres-beroun'
from pytils.translit import slugify # pip install pytils            # slugify('Loděnice (okres Beroun)')='lodnice-okres-beroun'
from bustime.validators import DateValidator
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import Group, User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.gis.db import models
from django.contrib.gis.geos import LineString, Point
from django.core import serializers
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files.storage import FileSystemStorage
from django.db import connections, connection
from django.db.models import Manager as GeoManager
from django.db.models import Q, Sum, Count, Manager, Subquery
from django.db.models.signals import (m2m_changed, post_delete, post_save,
                                      pre_delete)
from django.dispatch import receiver
from django.utils import timezone
from django.utils.encoding import force_str
from django.utils.formats import localize
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy
from django.utils.translation import override as translation_override
from django.utils.functional import SimpleLazyObject
from reversion.models import Revision
from six.moves import range
from sorl.thumbnail import ImageField, get_thumbnail

from .mytransliterate import mytransliterate

from django.utils import  translation
from warnings import warn
from functools import cmp_to_key
from collections import defaultdict
from django.contrib.postgres.aggregates import ArrayAgg
from zoneinfo import ZoneInfo

if settings.MASTER_HOSTNAME == 'f7':
    REDIS = redis.StrictRedis(unix_socket_path='/tmp/redis.sock', db=0)
    REDIS_W = redis.StrictRedis(unix_socket_path='/tmp/redis.sock', db=0)
    REDISU = redis.StrictRedis(unix_socket_path='/tmp/redis.sock', db=0)
else:
    REDIS = redis.StrictRedis(host=settings.REDIS_HOST, db=0, port=settings.REDIS_PORT)
    REDISU = redis.StrictRedis(host=settings.REDIS_HOST, db=0, port=settings.REDIS_PORT, charset="utf8", decode_responses=True)
    REDIS_W = redis.StrictRedis(host=settings.REDIS_HOST_W, db=0, port=settings.REDIS_PORT_W)

REDIS_IO = redis.StrictRedis(host=settings.REDIS_HOST_IO, db=0, port=settings.REDIS_PORT_IO)
REDISU_IO = redis.StrictRedis(host=settings.REDIS_HOST_IO, db=0, port=settings.REDIS_PORT_IO, charset="utf8", decode_responses=True)

distance_meters = cdistance # C or Python? 3x times
RouteNode = namedtuple('RouteNode', ['route_id', 'busstop_id', 'name', 'direction', 'bus_id'])
timezone_finder = SimpleLazyObject(lambda: TimezoneFinder(in_memory=True))

#
# mini cache
#
BUS_BY_NAME = {}  # it contains id of bus, to not take more memory
BUS_BY_ID = {}
BUS_BY_ID_UPDATE = None
ROUTE_BY_ID = {}
STOP_BY_ID = {}
CITY_MAP, CITY_MAPN = {}, {}
COUNTRY_MAP, COUNTRY_MAP_CODE = {}, {}
GRAPH_MAP = {}
DATASOURCE_CACHE = {}
PLACE_MAP = {}
PLACE_MAPN = {}

cur_lang = translation.get_language()
translation.activate(cur_lang)


class FileSystemStorageZ(FileSystemStorage):
    def url(self, name):
        return self.base_url+name.replace(settings.MEDIA_ROOT+"/", '')

fsZ = FileSystemStorageZ()

class TType(IntEnum):
    BUS = 0,
    TROLLEYBUS = 1,
    TRAMWAY = 2,
    SHUTTLE_BUS = 3,
    AQUA_BUS = 4,
    INTERCITY = 5,
    TRAIN = 6,
    METRO = 7,
    CAR_POOL = 8

CityUpdaterState = Enum("State", [
    "UPDATE",
    "POST_UPDATE",
    "POST_TURBINE_UPDATE",
    "IDLE",
    "ALERTS",
])


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
    (4, 'Водный'),
    (5, 'Междугородний'),
    (6, 'Поезд'),
    (7, 'Метро'),
    (8, 'Попутка'),
)

VF_VOICE_CHOICES = (
    (0, 'Анна'),
    (1, 'Мария'),
    (2, 'Лидия'),
    (3, 'Александр'),
    (4, 'Владимир'),
)

SOURCE_CHOICES = (
    (1, 'GTFS'),
    (2, 'Bustime'),
)

RECEIVER_CHOICES = (
    (9, 'default'),         # Будет создан пустой обработчик
)

GLONASSD_PROTOCOL = (
    (0, 'wialonips'),
    (1, 'egts'),
    (2, 'soap'),    # Олимпстрой
    (3, 'arnavi'),
    (4, 'arnavi5'),
    (5, 'galileo'),
    (6, 'gps103'),
)

GLONASSD_KEY = "clonassd.conf"

ZSUB = "tcp://127.0.0.1:15555"
ZPUB = "tcp://127.0.0.1:15556"
ZSUB = "ipc:///tmp/15555"
ZPUB = "ipc:///tmp/15556"
ZSUBGATE = "tcp://127.0.0.1:15557"
PROXIES = {
    'http': 'http://10.0.3.100:3128',
    'https': 'socks5://10.0.3.100:1080'
}

PROXY_RUS = {
    'http': 'http://10.0.3.65:3128',
    'https': 'socks5h://10.0.3.65:1080'
}

AES_KEY = "GLmiL5EufUt0vd3B"
UID_RE = re.compile('[A-Za-z0-9\-_]+$')


def get_admin_thumb(image):
    if image:
        return get_thumbnail(image, '162x100', quality=70)
    else:
        class A:
            pass
        a = A()
        a.url = ""
        return a


def aes_enc(s:str, iv) -> str:
    # pad from
    BS = 16

    pad = lambda s: s + (BS - len(s) % BS) * chr(BS - len(s) % BS)
    iv = iv[:16]
    if len(iv) < 16:
        iv = iv + " "*(16-len(iv))
    s = pad(s)
    cipher = Cipher(algorithms.AES(bytes(AES_KEY, 'utf-8')), modes.CBC(bytes(iv, 'utf-8')))
    encryptor = cipher.encryptor()
    obj = encryptor.update(bytes(s, 'utf-8')) + encryptor.finalize()
    return b64encode(obj).decode()


def aes_dec(s:str, iv) -> str:
    unpad = lambda s : s[0:-ord(s[-1])]
    iv = iv[:16]
    if len(iv) < 16:
        iv = iv + " "*(16-len(iv))
    cipher = Cipher(algorithms.AES(bytes(AES_KEY, 'utf-8')), modes.CBC(bytes(iv, 'utf-8')))
    decryptor = cipher.decryptor()
    data = decryptor.update(b64decode(s)) + decryptor.finalize()
    data = data[:-data[-1]]
    return data
    # return unpad(data)


def belongs_to_user(user, days=90):
    if not user: return
    ms_list, us_list = [], []
    for ms in MobileSettings.objects.filter(user=user):
        ms.ban = datetime.datetime.now() + datetime.timedelta(days=days)
        ms.save()
        ms_list.append(ms)
    for us in UserSettings.objects.filter(user=user):
        us.ban = datetime.datetime.now() + datetime.timedelta(days=days)
        us.save()
        us_list.append(us)
    return ms_list, us_list


def block_and_delete(us=None, ms=None, deleted_by=None, days=90):
    chats = []
    if ms:
        belongs_to_user(ms.user)
        for c in Chat.objects.filter(deleted=False, ms__user=ms.user):
            c.deleted_by = deleted_by
            c.deleted=True
            c.save()
            chats.append(c)
    if us:
        belongs_to_user(us.user)
        for c in Chat.objects.filter(deleted=False, us__user=us.user):
            c.deleted_by = deleted_by
            c.deleted=True
            c.save()
            chats.append(c)
    return chats


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


def now_at(lon, lat):
    try:
        t = timezone_finder.timezone_at(lng=lon, lat=lat)
        etz = pytz.timezone(t)
    except:
        return None
    now = datetime.datetime.now(etz)
    now = now.replace(tzinfo=None)
    return now

class URLMover(models.Model):
    ctime = models.DateTimeField(auto_now_add=True)
    url_old = models.CharField(max_length=255, unique=True)
    url_new = models.CharField(max_length=255)

    def __str__(self):
        return u"%s -> %s" % (self.url_old, self.url_new)


class Country(models.Model):
    # Россия, Suomi, Lietuva, Latvija, Eesti,  Україна, Беларусь, Nederland
    # active = models.BooleanField(default=True)
    osm_id = models.BigIntegerField(null=True, blank=True)
    available = models.BooleanField(default=True)
    name = models.CharField(max_length=64)
    code = models.CharField(max_length=2)
    language = models.CharField(max_length=2, default="ru")
    domain = models.CharField(max_length=15)
    tags = models.JSONField(blank=True, null=True)
    register_phone = PhoneNumberField(blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name = gettext_lazy("страна")
        verbose_name_plural = gettext_lazy("страны")

    def __str__(self):
        return self.code


def monitor_counters(city, counters=None):
    # uevents = rcache_get("uevents_%s" % city.id, {})
    # allevents = rcache_get("allevents_%s" % city.id, {})
    log_counters = rcache_get('log_counters_%s' % city.id, {}) if not counters else counters
    # {'allevents_len': 2520,
    #  'nearest': 1836,
    #  'sleeping': 449,
    #  'uevents_len': 2520,
    #  'zombie': 173}
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

    log = {"ups": [], "errors": []}
    cc_key = "log_update_lib_%s" % city.id
    log['ups'] = rcache_get(cc_key, [])
    cc_key = "log_error_update_%s" % city.id
    log['errors'] = rcache_get(cc_key, [])

    return counter, log


class City(models.Model):
    active = models.BooleanField(default=True)
    available = models.BooleanField(default=True)
    name = models.CharField(max_length=64)
    name_gde = models.CharField(max_length=64, null=True, blank=True)
    name_o = models.CharField("Маршруты чего?", max_length=64, null=True, blank=True)
    timediffk = models.IntegerField(default=0)
    wunderground = models.CharField(max_length=64, null=True, blank=True)
    point = models.PointField(srid=4326, null=True, blank=True)
    slug = models.CharField(max_length=64, null=True, blank=True, unique=True)
    rev = models.SmallIntegerField(default=0)

    bus = models.BooleanField(default=True)
    trolleybus = models.BooleanField(default=True)
    tramway = models.BooleanField(default=True)
    bus_taxi = models.BooleanField(default=False)
    bus_intercity = models.BooleanField(default=False)
    water = models.BooleanField(default=False)
    bus_taxi_merged = models.BooleanField("Маршрутки внутри автобусов", default=False)
    car_passing = models.BooleanField("Попутки", default=False)

    gps_data_provider = models.CharField(max_length=66, null=True, blank=True)
    gps_data_provider_url = models.CharField(max_length=64, null=True, blank=True)
    check_url = models.CharField("URL проверка", max_length=64, null=True, blank=True)

    # default_transport = models.CharField(max_length=12, default="bus")
    default_ttype = models.IntegerField(choices=TTYPE_CHOICES, default=0)
    sat = models.BooleanField(default=False)  # is site is sattelite?
    noads = models.BooleanField(default=False)  # block ads in this city?
    # time of last success
    good_time = models.DateTimeField(null=True, blank=True)
    crawler = models.BooleanField(default=False)
    transport_card = models.BooleanField(default=False)
    tcard_provider = models.CharField(max_length=64, null=True, blank=True)
    source = models.SmallIntegerField(choices=SOURCE_CHOICES, default=0)
    country = models.ForeignKey(Country, default=1, on_delete=models.PROTECT)
    comment = models.TextField(null=True, blank=True)
    editors = models.ManyToManyField(User, related_name="reditors")
    dispatchers = models.ManyToManyField(User, related_name="rdisps")
    block_info = models.TextField(null=True, blank=True)
    skip_recalc = models.BooleanField(_("Activate to skip: recalc interstops, buses_get cache, fill jamline_list. Speed up edits."), default=False)
    staff_modify = models.BooleanField(_("Только редакторы и администраторы могут изменять связанную с городом информацию"), default=False)
    summer_time = models.BooleanField(default=False)

    objects = GeoManager()

    class Meta:
        ordering = ["name"]
        verbose_name = gettext_lazy("город")
        verbose_name_plural = gettext_lazy("города")
    # def natural_key(self):
    #     return (self.slug)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return u"/%s/" % self.slug

    def get_absolute_url_classic(self):
        return u"/%s/classic/" % self.slug

    def uevents(self):
        return rcache_get("uevents_%s" % self.id)

    def allevents(self):
        return rcache_get("allevents_%s" % self.id)

    @property
    def now(self):
        return datetime.datetime.now() + datetime.timedelta(hours=self.timediffk)

    def is_night(self):
        if self.now.hour >= 6 and self.now.hour < 23:
            return False
        else:
            night = True
        return night

    def transport_count(self):
        n = 0
        if self.bus:
            n += 1
        if self.trolleybus:
            n += 1
        if self.tramway:
            n += 1
        if self.bus_taxi:
            n += 1
        if self.bus_intercity:
            n += 1
        if self.water:
            n += 1
        if self.car_passing:
            n += 1
        # if self.id == 84: n+=1 # todo
        return n

    def set_transport(self):
        self.bus = Bus.objects.filter(ttype=0, active=True, city=self).exists()
        self.trolleybus = Bus.objects.filter(ttype=1, active=True, city=self).exists()
        self.tramway = Bus.objects.filter(ttype=2, active=True, city=self).exists()
        self.bus_taxi = Bus.objects.filter(ttype=3, active=True, city=self).exists()
        self.bus_intercity = Bus.objects.filter(ttype=5, active=True, city=self).exists()
        self.water = Bus.objects.filter(ttype=4, active=True, city=self).exists()

    def should_work(self):
        if self.now.hour >= 6 and self.now.hour < 23:
            return True
        else:
            return False

    def any_error(self):
        error_update = rcache_get("error_%s" % self.id, {})
        if error_update.get('panic') or (error_update.get('nearest_cnt', 0) == 0 and self.should_work()):
            return True
        else:
            return False

    def real_error(self):
        error_update = rcache_get("error_%s" % self.id, {})
        # выводить ошибку, даже если нам отправляют данные напрямую
        nc = error_update.get('nearest_cnt', 0)
        gc = error_update.get('gevents_cnt', 0)
        if nc - gc < 1 and self.should_work():
            return True
        else:
            return False

    def save(self, *args, **kwargs):
        new_flag = False
        if not self.pk:
            new_flag = True
        super(City, self).save(*args, **kwargs)
        cities_get(force=True)
        cities_get(force=True, country=self.country.code)
        # monkey is so monkey
        cities_get(force=True, as_list=True)
        cities_get(force=True, as_list=True, country=self.country.code)

        if self.pk:
            cc_key = "available_cities_ids"
            cities_ids = rcache_get(cc_key, [])
            if self.pk not in cities_ids:
                cities_ids = list(City.objects.filter(available=True).values_list("id", flat=True))
                rcache_set(cc_key, cities_ids, 60*15)
    # save

    def is_ut(self, *args, **kwargs):
        if self.id in [118, 29, 31, 34, 35, 42, 43,
                       49, 52, 56, 57, 60, 64, 68, 70,
                       83, 89]:
            return True
        return False


class Place(models.Model):
    osm_id = models.BigIntegerField(null=False, unique=True)
    osm_area_id = models.BigIntegerField(null=True, blank=True)
    osm_area_type = models.CharField(max_length=1, null=True, blank=True)
    name = models.TextField(blank=True, null=True)
    tags = models.JSONField(blank=True, null=True)
    place = models.TextField(blank=True, null=True)
    population = models.IntegerField(null=True, db_index=True)
    capital = models.TextField(blank=True, null=True)
    rank = models.IntegerField(null=True)
    point = models.PointField(srid=4326, null=True, blank=True)
    timezone = TimeZoneField(use_pytz=False, null=True, blank=True)
    source = models.SmallIntegerField(choices=SOURCE_CHOICES, default=0)
    stops_count = models.SmallIntegerField(default=0, blank=True, null=True)
    buses_count = models.SmallIntegerField(default=0, blank=True, null=True)
    slug = models.SlugField(max_length=256, allow_unicode=True, blank=True, null=True, unique=True)
    country_code = models.CharField(max_length=2, null=True, blank=True)
    editors = models.ManyToManyField(User, blank=True)
    dispatchers = models.ManyToManyField(User, blank=True, related_name='disp_place_set')
    block_info = models.TextField(null=True, blank=True)
    rev = models.SmallIntegerField(default=0, blank=True, null=True)
    dump_version = models.SmallIntegerField(default=0, blank=True, null=True)
    patch_version = models.SmallIntegerField(default=0, blank=True, null=True)
    weather = models.BigIntegerField(null=True, blank=True)
    objects = GeoManager()

    @property
    def now(self):
        return datetime.datetime.now(self.timezone).replace(tzinfo=None)

    @property
    def available(self):
        return self.bus_set.exists()

    @property
    def active(self):
        warn("Deprecated! All cities are active", DeprecationWarning, stacklevel=2)
        return True

    @property
    def timediffk(self):
        # Костыль вычисления смещения времени относительно Красноярска (+7 UTC)
        warn("Deprecated! Use timezone instead.", DeprecationWarning, stacklevel=2)
        return int(datetime.datetime.now(self.timezone).utcoffset().seconds / 3600) - 7

    @property
    def country(self):
        return Country.objects.get(code=self.country_code)

    @property
    def country_id(self):
        warn("Deprecated! Use country_code instead.", DeprecationWarning, stacklevel=2)
        return Country.objects.get(code=self.country_code).id

    @property
    def summer_time(self):
        return datetime.datetime.now(self.timezone).dst() > datetime.timedelta(seconds=0)

    def should_work(self):
        if self.now.hour >= 6 and self.now.hour < 23:
            return True
        else:
            return False

    def is_night(self):
        return not self.should_work()

    def get_absolute_url(self):
        return u"/%s/" % self.slug

    def get_absolute_url_classic(self):
        return u"/%s/classic/" % self.slug

    def __str__(self):
        return self.name

    def __repr__(self):
        return "{0}[{1}]: {2}[{3}]".format(self.id, self.osm_id, self.slug, self.country_code)

    class Meta:
        indexes = [
            models.Index(fields=["osm_area_id", "osm_area_type"]),
        ]


class PlaceArea(models.Model):
    # osm_id = models.CharField(max_length=255, null=True)  # todo unique=True
    osm_id = models.BigIntegerField(null=False)
    osm_type = models.CharField(max_length=1, null=False)
    name = models.TextField(blank=True, null=True)
    type = models.TextField(blank=True, null=True)
    admin_level = models.IntegerField(blank=True, null=True)
    place = models.TextField(blank=True, null=True)
    tags = models.JSONField(blank=True, null=True)
    rev = models.SmallIntegerField(default=0, blank=True, null=True)
    geometry = models.GeometryField(blank=True, null=True)
    timezone = TimeZoneField(use_pytz=False, null=True, blank=True)
    stops_count = models.SmallIntegerField(default=0, blank=True, null=True)
    buses_count = models.SmallIntegerField(default=0, blank=True, null=True)
    slug = models.SlugField(max_length=256, allow_unicode=True, blank=True, null=True, unique=True)
    objects = GeoManager()

    @property
    def now(self):
        return datetime.datetime.now(self.timezone).replace(tzinfo=None)

    def __str__(self):
        return "{0}[{1}]: {2}".format(self.osm_id, self.osm_type, self.name)

    class Meta:
        unique_together = ("osm_id", "osm_type")


class Glonassd(models.Model):
    city = models.ForeignKey(City, on_delete=models.CASCADE)
    port = models.SmallIntegerField(default=0)
    protocol = models.SmallIntegerField(choices=GLONASSD_PROTOCOL, default=0)

    def clean(self):
        # self - Glonassd object (record)
        if rcache_get(GLONASSD_KEY, None):
            raise ValidationError(_("Файл glonassd.conf занят, попробуйте через 5 сек."))

        rcache_set(GLONASSD_KEY, True, 5)

        #проверим, что нет повторения порта
        if self.pk:
            port_exists = Glonassd.objects.filter(~Q(id=self.pk)).filter(port=self.port).count() > 0
        else:
            port_exists = Glonassd.objects.filter(port=self.port).count() > 0

        if port_exists or self.port <= 1024 or self.port >= 65535:
            from bustime.glonassd import get_awail_glonassd_port
            free_port = get_awail_glonassd_port()
            rcache_set(GLONASSD_KEY, None)
            raise ValidationError(_("Порт %s неправильный или уже используется, попробуйте %s") % (self.port, free_port))
    # clean

    class Meta:
        verbose_name = _("Glonassd приёмник")
        verbose_name_plural = _("Glonassd приёмники")
# class Glonassd

# после создания или обновления записи переконфигурируем демон glonassd
@receiver(post_save, sender=Glonassd)
def glonassd_post_save(sender, **kwargs):
    from bustime.glonassd import daemon_reconfigure
    daemon_reconfigure()
    rcache_set(GLONASSD_KEY, None)

# перед удалением записи переконфигурируем демон glonassd
@receiver(pre_delete, sender=Glonassd)
def glonassd_pre_delete(sender, instance, using, **kwargs):
    # delete record
    if rcache_get(GLONASSD_KEY, None):
        raise ValidationError(_("Файл glonassd.conf занят, попробуйте через 5 сек."))

    rcache_set(GLONASSD_KEY, True, 5)

    from bustime.glonassd import daemon_reconfigure
    error = daemon_reconfigure()
    if error:
        rcache_set(GLONASSD_KEY, None)
        raise ValidationError(error)

    rcache_set(GLONASSD_KEY, None)
# glonassd_pre_delete


class Receiver(models.Model):
    city = models.ForeignKey(City, on_delete=models.CASCADE, verbose_name="Город")
    source = models.SmallIntegerField("Тип обработчика", choices=RECEIVER_CHOICES, default=0)
    handler = models.CharField("Обработчик", max_length=2084, null=True, blank=True)
    params = models.TextField("Параметры", null=True, blank=True)

    def clean(self):
        # self - Receiver object (record)
        source = list(filter(lambda x: self.source in x, RECEIVER_CHOICES))[0][1]
        if not source:
            raise ValidationError('Неправильно указан тип обработчика')

        handler = self.handler.strip() if self.handler else None
        if not handler:
            raise ValidationError('Не указан обработчик')
        elif not handler.endswith(".py"):
            raise ValidationError('Неправильно указан обработчик')

        params = self.params.strip()
        if self.source < 9 and not params:
            raise ValidationError('Не указаны параметры')

        try:
            if self.source == 0: # glonassd
                ports = params.replace(' ', '').split(',')
                for p in ports:
                    try:
                        if int(p) <= 1024 or int(p) >= 65535:
                            raise ValidationError('Неправильный порт %s' % p)
                    except Exception as ex:
                        raise ValidationError('Неправильный порт %s' % p)
            elif self.source == 1: # infopass
                params = json.loads(params)
                if not params.get('url'):
                    raise ValidationError('Не указан url')
                if not params.get('referer'):
                    raise ValidationError('Не указан referer')
            elif self.source == 2: # транснавигация
                params = json.loads(params)
                if 'ok_id' not in params:
                    raise ValidationError('Отсутствует ok_id, добавьте даже пустой')
                if not params.get('url'):
                    raise ValidationError('Не указан url')
                if not params.get('referer'):
                    raise ValidationError('Не указан referer')
            elif self.source == 3: # askglonass
                params = json.loads(params)
                if not params.get('url'):
                    raise ValidationError('Не указан url')
                if not params.get('auth_login'):
                    raise ValidationError('Не указан auth_login')
                if not params.get('auth_pass'):
                    raise ValidationError('Не указан auth_pass')
            elif self.source == 4: # wialon
                params = json.loads(params)
                if not params.get('url'):
                    raise ValidationError('Не указан url')
                if not params.get('token'):
                    raise ValidationError('Не указан token')
            elif self.source == 5: # nimbus
                params = json.loads(params)
                if not params.get('subs'):
                    raise ValidationError('Не указан subs')
                if not params.get('token'):
                    raise ValidationError('Не указан token')
            else: # пустой обработчик
                pass
        except Exception as ex:
            raise ValidationError(str(ex))
    # clean


    class Meta:
        verbose_name = _("Обработчик города")
        verbose_name_plural = _("Обработчики городов")
# class Receiver


"""
Примеры, обрабатываемые функцией:
'SUB1GAS' => SUB1GAS
'0123-556' => 0123-556
'01AB-55CD' => 01AB-55CD
'ABCD-EFGHJ' => ABCD-EFGHJ
'01-55' => 01-55
'1' => 1
'123' => 123
'12345' => 12345
'779 AP 12' => 779AP
'429 LVA 12' => 429LVA
'Паз - 544FSA12' => 544FSA
'kz 621 HAA 12' => KZ621HAA
'Паз - 851 MTA' => 851MTA
'439 КМА 12' => 439КМА
'439  МРА 12' => 439МРА
'У460МТ142' => У460МТ
'У 460 МТ 142' => У460МТ
'АУ559' => АУ559
'АУ 559' => АУ559
'К 46-01 УУ 45' => К46-01УУ

gosnum не должен превышать 12 символов
https://pythex.org/
https://regex101.com/
"""
def normalize_gosnum(source):
    if not source:
        return source

    text = source.replace("(", "").replace(")", "").strip().upper()

    res = re.findall(u'([0-9A-Z]{2,5}\s{0,2}-\s{0,2}[0-9A-Z]{2,5}|[A-ZА-Я]{0,2}\s{0,2}[0-9-]{3,5}\s{0,2}[A-ZА-Я]{0,3})', text, re.U)
    if len(res) > 0:
        text = res[0]

    text = text.replace(' ', '')[:10]

    return text
# def normalize_gosnum

"""
"105"
"А-К-А"
"А-Б-А"
"31."
"31 А"
"""
def normalize_bus_name(source):
    text = source.replace(' ', '').replace('-', '').replace('+', '').replace(':', '')
    text = text.replace('(', '').replace(')', '').replace('[', '').replace(']', '')

    while len(text) > 0 and (not text[len(text)-1].isalnum()):
        text = text[0:len(text)-1]

    if len(text) > 4:
        text = text[0:3]
    return text.upper()
# def normalize_bus_name


class BusProvider(models.Model):
    ctime = models.DateTimeField(auto_now_add=True)
    mtime = models.DateTimeField(auto_now=True, null=True, blank=True)
    name = models.CharField(u"Название", max_length=128)
    address = models.CharField("Адрес", max_length=128, null=True, blank=True)
    phone = models.CharField("Телефон", max_length=128, null=True, blank=True)
    email = models.CharField(u"Email", max_length=128, null=True, blank=True)
    www = models.URLField(u"Сайт", max_length=128, null=True, blank=True)
    logo = models.ImageField("Логотип", upload_to="provider", null=True, blank=True, storage=fsZ)
    point = models.PointField(srid=4326, null=True, blank=True)
    xeno_id = models.CharField(null=True, blank=True, max_length=100)

    class Meta:
        verbose_name = gettext_lazy("перевозчик")
        verbose_name_plural = gettext_lazy("перевозчики")
        ordering = ('name', )
        indexes = [
            models.Index(fields=['name',]),
            models.Index(fields=['phone',]),
            models.Index(fields=['email',]),
        ]

    @property
    def places(self):
        return list(Place.objects.filter(bus__in=self.bus_set.all()).distinct())

    def __str__(self):
        if len(self.name) > 20:
            return u"%s..." % self.name[:20]
        else:
            return u"%s" % self.name[:20]

    def get_absolute_url(self):
        return u"/company/%s/" % self.id

    def get_rating(self):
        return 0


class Bus(models.Model):
    ctime = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    mtime = models.DateTimeField(auto_now=True, null=True, blank=True)
    active = models.BooleanField("Активен", default=True)
    name = models.CharField("Название", max_length=256)
    price = models.CharField("Цена проезда", max_length=8, null=True, blank=True)
    discount = models.BooleanField("Скидка", default=False)
    description = models.CharField("Объявление", max_length=256, null=True, blank=True)
    order = models.IntegerField(_("Порядок"), null=True, blank=True, db_index=True, default=0)
    murl = models.CharField(null=True, blank=True, max_length=256)
    ttype = models.IntegerField(choices=TTYPE_CHOICES)
    napr_a = models.CharField(_("Направление") + " 0", max_length=256, null=True, blank=True)
    napr_b = models.CharField(_("Направление") + " 1", max_length=256, null=True, blank=True)
    only_season = models.BooleanField("Сезонный", default=False)
    only_holiday = models.BooleanField("Только праздники", default=False)
    only_working = models.BooleanField("Только рабочие", default=False)
    only_rush_hour = models.BooleanField("Только часы пик", default=False)
    only_special = models.BooleanField("Только специальный", default=False)
    city = models.ForeignKey(City, null=True, blank=True, related_name="buses", verbose_name="Город", on_delete=models.SET_NULL)
    xeno_id = models.CharField(null=True, blank=True, max_length=256)
    provider = models.ForeignKey(BusProvider, null=True, blank=True, verbose_name="Перевозчик", on_delete=models.SET_NULL)
    tt_xeno_reversed = models.BooleanField(null=True)
    slug = models.CharField(_("Ссылка"), max_length=64, null=True, blank=True)
    inter_stops = models.IntegerField("Межостановочное расстояние", null=True, blank=True)
    inter_stops_fixed = models.BooleanField("Межостановочное расстояние фиксировано", default=False)
    distance = models.FloatField("Расстояние", null=True, blank=True)
    distance0 = models.PositiveIntegerField("Расстояние0", null=True, blank=True)
    distance1 = models.PositiveIntegerField("Расстояние1", null=True, blank=True)
    travel_time = models.FloatField("Длительность рейса", null=True, blank=True)  # in minutes
    #  сериализованный JSON, который описывает начало движения транспорта с конечных по рабочим
    tt_start = models.TextField("Начало движения с конечной (JSON)", null=True, blank=True)
    # и праздничным дням
    tt_start_holiday = models.TextField("Начало движения в выходные (JSON)", null=True, blank=True)
    # Интервал движения
    interval = models.TextField("Интервал движения", null=True, blank=True)
    # способ оплаты, юзеры заполнят, типа наличные, по карте, по ТК
    payment_method = models.TextField("Способ оплаты", null=True, blank=True)
    # objects = caching.base.CachingManager()
    # - интервал движения (стринг),
    # - способы оплаты (предусмотреть мультивыбор из: наличные, транспортная карта, банковская карта, социальная карта, и сюда же можно скидку на пересадку добавить),
    # - время работы маршрута в обе стороны (типа расписание, но только старт и конец), чтобы юзеры заполнили.
    # https://gitlab.com/nornk/bustime/issues/1391
    routes = models.TextField(null=True, blank=True)
    onroute = models.CharField("Выпуск по будням", max_length=8, null=True, blank=True)
    onroute_weekend = models.CharField("Выпуск по выходным", max_length=8, null=True, blank=True)
    osm = models.ManyToManyField(PlaceArea, related_name="osms") # см. turbo_bus_osm_fill.py
    places = models.ManyToManyField(Place) # см. turbo_bus_osm_fill.py
    turbo = models.BooleanField("Turbo mode", default=True, editable=False)  # must not be here at all! todo: remove it
    gtfs_catalog = models.BigIntegerField("GtfsCatalog ID", null=True, blank=True)
    route_dir0 = models.GeometryField(blank=True, null=True)
    route_dir1 = models.GeometryField(blank=True, null=True)

    class Meta:
        verbose_name = gettext_lazy("маршрут")
        verbose_name_plural = gettext_lazy("маршруты")
        #unique_together = ("city", "name", "ttype")
        indexes = [
            models.Index(fields=['name',]),
            models.Index(fields=['ttype',]),
            models.Index(fields=['murl',]),
            models.Index(fields=['xeno_id',]),
            models.Index(fields=['gtfs_catalog',]),
        ]

    def __str__(self):
        if self.ttype == 1:
            prefix = u'Т'
        elif self.ttype == 2:
            prefix = u'ТВ'
        elif self.ttype == 3:
            prefix = u'МТ'
        elif self.ttype == 4:
            prefix = u'В'
        elif self.ttype == 5:
            prefix = u'МА'
        elif self.ttype == 6:
            prefix = u'П'
        elif self.ttype == 7:
            prefix = u'М'
        elif self.ttype == 8:
            prefix = u'ПП'
        else:
            prefix = ''
        return u"%s%s" % (prefix, self.name)

    def get_absolute_url(self, place=None):
        if not place:
            place = self.places.order_by("-population").first()
        if place:
            return u"/%s/%s/" % (place.slug, self.slug)
        else:
            return u"/%s/" % (self.slug)

    def get_online_url(self, place=None):
        if not place:
            place = self.places.order_by("-population").first()
        if place:
            return u"/%s/#%s" % (place.slug, self.slug)
        else:
            return u"/#%s/" % (self.slug)

    def get_absolute_url_classic(self, place=None):
        if not place:
            place = self.places.order_by("-population").first()
        if place:
            return u"/%s/%s/" % (place.slug, self.slug)
        else:
            return u"/%s/" % (self.slug)

    def get_absolute_url_schedule(self, place=None):
        if not place:
            place = self.places.order_by("-population").first()
        if place:
            return u"/%s/%s/" % (place.slug, self.slug)
        else:
            return u"/%s/" % (self.slug)

    def amount_a(self, direction=0):
        l = self.bdata_mode0()
        cnt = 0
        if l:
            for k in l['l']:
                if k.get('d') == direction and not k.get('sleep') and not k.get('zombie'):
                    cnt += 1
        return cnt

    def amount_b(self, direction=1):
        l = self.bdata_mode0()
        cnt = 0
        if l:
            for k in l['l']:
                if k.get('d') == direction and not k.get('sleep') and not k.get('zombie'):
                    cnt += 1
        return cnt

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
        cnt = 0
        if l:
            for k in l['l']:
                if not k.get('sleep') and not k.get('zombie') and k.get("bn"):
                    cnt += 1
        return cnt

    def bdata_mode0(self, direction=None):
        return self.bdata_mode(direction=direction)

    def bdata_mode(self, direction=None):
        uids = REDIS.smembers("bus__%s" % self.id)
        uids = list([x.decode('utf8') for x in uids])
        to_get = [f'event_{uid}' for uid in uids]
        now = datetime.datetime.now()
        routes = {r['id']: r for r in city_routes_get_turbo(self.pk)}
        bdata = {
            0: {'stops': []}, 1: {'stops': []}, 'updated': str(now), 'l': [],
            'bus_id':self.id
        }
        #serialized['time_bst'] = time_bst_diff
        for e in rcache_mget(to_get):
            # ev_id, uid = to_get.pop(0), uids.pop(0)
            if not e:
                continue
            if e.get('bus_id') != self.id:
                continue
            if e.zombie:
                e["busstop_nearest"] = None
                
            bdata['l'].append(e.get_lava())
            if e.get('busstop_nearest') and not e.zombie and not e.away and not e.sleeping:
                if not routes or not routes.get(e['busstop_nearest']):
                    continue
                bdata[e.direction]['stops'].append(e.get('busstop_nearest'))
        
        bdata['l'] = sorted(bdata['l'], key=cmp_to_key(lava_sort_up))

        """
        bdata = None
        if mode == 10:
            bdata = rcache_get("bdata_mode0_%s" % self.id)
            if bdata:
                del bdata[0]
                del bdata[1]
                l = []
                for e in bdata['l']:
                    if not e.get("z"):
                        if e.get("bn"):
                            del e['bn']
                        if e.get("order"):
                            del e['order']
                        if 'l' in e:
                            e['l'] = e['l'].strip('[]{}()*=.,:;_&?^%$#@!').strip()
                        l.append(e)
                bdata['l'] = l
        """
        if direction is not None:
            bdata = bdata[direction]
        return bdata

    @property
    def distance_km(self):
        if self.distance:
            return int(self.distance/1000)
        else:
            return 0
    @property
    def distance0_km(self):
        if self.distance0:
            return int(self.distance0/1000)
        else:
            return 0
    @property
    def distance1_km(self):
        if self.distance1:
            return int(self.distance1/1000)
        else:
            return 0

    def ttype_name(self):
        n = _("неизвестный")
        if self.ttype == 0:
            n = _("Автобус")
        elif self.ttype == 1:
            n = _("Троллейбус")
        elif self.ttype == 2:
            n = _("Трамвай")
        elif self.ttype == 3:
            n = _("Маршрутное такси")
        elif self.ttype == 4:
            n = _("Аквабус")
        elif self.ttype == 5:
            n = _("Междугородний")
        elif self.ttype == 6:
            n = _("Поезд")
        elif self.ttype == 7:
            n = _("Метро")
        elif self.ttype == 8:
            n = _("Попутка")
        return n

    def ttype_names(self):
        n = _("неизвестный")
        if self.ttype == 0:
            n = _("Автобусы")
        elif self.ttype == 1:
            n = _("Троллейбусы")
        elif self.ttype == 2:
            n = _("Трамваи")
        elif self.ttype == 3:
            n = _("Маршрутные такси")
        elif self.ttype == 4:
            n = _("Аквабусы")
        elif self.ttype == 5:
            n = _("Междугородние")
        elif self.ttype == 6:
            n = _("Поезд")
        elif self.ttype == 7:
            n = _("Метро")
        elif self.ttype == 8:
            n = _("Попутки")
        return n

    def ttype_slug(self):
        ttype_name = 0
        if self.ttype == 0:
            ttype_name = "bus"
        elif self.ttype == 1:
            ttype_name = "trolleybus"
        elif self.ttype == 2:
            ttype_name = "tramway"
        elif self.ttype == 3:
            ttype_name = "bus-taxi"
        elif self.ttype == 4:
            ttype_name = "water"
        elif self.ttype == 5:
            ttype_name = "bus-intercity"
        elif self.ttype == 6:
            ttype_name = "train"
        elif self.ttype == 7:
            ttype_name = "metro"
        elif self.ttype == 8:
            ttype_name = "carpool"
        return ttype_name

    def save(self, refresh_routes=False, *args, **kwargs):
        def flat_route(obj):
            record = obj["fields"]
            record["pk"] = obj["pk"]
            return record

        def serialize_routes(routes):
            raw = json.loads(serializers.serialize("json", routes))
            return json.dumps(list(map(flat_route, raw)))

        # slug
        slug = []
        # 1 place
        if self.id and self.city and self.city.id == 1:
            # primary_place = self.osm.order_by("-admin_level").first()   # self.id MUST HAVE value
            primary_place = self.places.order_by("-population").first()   # self.id MUST HAVE value
            if not primary_place and self.city:
                primary_place = Place.objects.filter(id=self.city.id).first()
            if primary_place:
                if primary_place.slug:
                    slug.append(primary_place.slug[:42])
                elif primary_place.osm_id:
                    slug.append( str(primary_place.osm_id)[:42] )
                elif slugify(primary_place.name):
                    slug.append(slugify(primary_place.name)[:42] )

        # 2 ttype
        slug.append( self.ttype_slug() )
        # 3 name
        ns = mytransliterate(self.name).replace("/", "-")
        ns = ns.replace("!", "new") # ???
        slug.append( slugify(ns) )

        ns = '-'.join(slug)
        self.slug = ns.lower().strip().rstrip('-').lstrip('-')
        self.slug = self.slug[:64]
        # extra proccessing, city depending
        if self.city_id == 5 and self.ttype != 7:
            self = pre_save_bus(self)

        if refresh_routes:
            routes = Route.objects.filter(bus=self).order_by('direction', 'order')
            self.routes = serialize_routes(routes)

        super(Bus, self).save(*args, **kwargs)
# class Bus

# after insert/update record, работает и при изменении записи в wiki
@receiver(post_save, sender=Bus)
def bus_post_save(sender, instance, **kwargs):
    cache_reset_bus(instance, deleted=False)

# before delete record, работает и при удалении записи в wiki
@receiver(pre_delete, sender=Bus)
def bus_pre_delete(sender, instance, using, **kwargs):
    # post_delete бесполезен, так как в нём у instance уже нет places и cache_reset_bus не сработает как надо
    places = []
    for place in instance.places.all():
        places.append(place)
    rcache_set(f"places_fresh_{instance.id}", places, 300)

@receiver(post_delete, sender=Bus)
def bus_post_delete(sender, instance, **kwargs):
    for place in rcache_get(f"places_fresh_{instance.id}", []):
        buses_get(place, force=True)
    REDIS_W.delete(f"places_fresh_{instance.id}")
    cache_reset_bus(instance, deleted=True)


class Tcard(models.Model):
    num = models.CharField(max_length=20)
    balance_rub = models.FloatField(null=True, blank=True)
    balance_trips = models.SmallIntegerField(null=True, blank=True)
    balance_trips_extra = models.SmallIntegerField(null=True, blank=True)
    black = models.BooleanField(default=0)  # black listed card
    created = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    # last time user requested this card
    checked = models.DateTimeField(null=True, blank=True)
    # last time update happened
    updated = models.DateTimeField(null=True, blank=True)
    response_raw = models.TextField(null=True, blank=True)
    social = models.BooleanField(default=False)
    provider = models.CharField(max_length=64)

    def __str__(self):
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

    def balance_text(self):
        if self.social:
            s = u"%s шт." % self.balance_trips  # 10 шт.
            if self.balance_trips_extra:
                s += u", %s доп." % self.balance_trips_extra  # 15 доп.
        elif self.balance is None:
            s = None
        else:
            s = u"%s ₽" % self.balance  # 134 ₽
        return s

    def warning(self):
        if self.social:
            if self.balance_trips is not None and self.balance_trips < 5:
                return True
            else:
                return False
        else:
            if self.balance_rub is not None and self.balance_rub < 5*26:
                return True
            else:
                return False


class Passenger(models.Model):
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE)
    name = models.CharField(max_length=128, null=True, blank=True)
    amount = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return self.name


class Conn(models.Model):
    ip = models.CharField(max_length=255, null=True, blank=True)
    ua = models.CharField(max_length=128, null=True, blank=True)
    ctime = models.DateTimeField(auto_now_add=True)
    etime = models.DateTimeField(auto_now=True, null=True, blank=True)

    def __str__(self):
        return self.ip


'''
Внимание: при определении поля любой модели как ForeignKey(UserSettings, ...)
проверить, что в файле utils/clean_usersettings.sql определяемая модель обрабатывается
(т.е. в таблице модели производится удаление записей или обнуление полей, ссылающихся на UserSettings).
Обнуление полей или удаление записей делать по образцу в utils/clean_usersettings.sql.
'''
class UserSettings(models.Model):
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    ctime = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    mtime = models.DateTimeField(auto_now=True, null=True, blank=True)
    ltime = models.DateTimeField(null=True, blank=True)
    session_key = models.CharField(
        max_length=32, null=True, blank=True, unique=True, db_index=True)
    name = models.CharField(max_length=24, null=True, blank=True)
    phone = models.CharField(max_length=16, null=True, blank=True)
    # password = models.CharField(max_length=32, null=True, blank=True)
    busfavor_amount = models.SmallIntegerField(default=5)
    busfav_hold = models.BooleanField(default=False)
    stars = models.SmallIntegerField(default=0, null=True, blank=True)
    noads = models.BooleanField(default=0)
    theme = models.SmallIntegerField(default=0, choices=THEME_CHOICES)
    theme_save = models.SmallIntegerField(null=True, blank=True)
    mode = models.SmallIntegerField(default=1, choices=MODE_CHOICES)
    sound = models.BooleanField(default=True)
    sound_plusone = models.BooleanField(default=False)

    gps_off = models.BooleanField(default=0)
    gps_send = models.BooleanField(default=0)
    gps_send_bus = models.ForeignKey(Bus, null=True, blank=True, on_delete=models.SET_NULL)
    gosnum = models.CharField(max_length=16, null=True, blank=True)
    gps_send_ramp = models.BooleanField(default=0)  # Аппарель
    gps_send_rampp = models.BooleanField(default=0) # Низкопольность
    gps_send_of = models.CharField(max_length=12, null=True, blank=True)
    tcolor = models.CharField(max_length=6, null=True, blank=True, default="F4C110")
    tface = models.CharField(max_length=8, null=True, blank=True)
    driver_ava = models.CharField(max_length=15, null=True, blank=True)
    #city = models.ForeignKey(City, null=True, blank=True, on_delete=models.SET_NULL)
    #country = models.ForeignKey(Country, null=True, blank=True, on_delete=models.SET_NULL)
    tcard = models.CharField(max_length=20, null=True, blank=True)

    ip = models.GenericIPAddressField(null=True, blank=True)
    ua = models.CharField(max_length=255, null=True, blank=True)

    vk_like_pro = models.SmallIntegerField(default=0)
    # theme_stripes = models.BooleanField(default=1)
    pro_demo = models.BooleanField(default=False)
    pro_demo_date = models.DateTimeField(null=True, blank=True)
    multi_all = models.BooleanField(default=False)
    matrix_show = models.BooleanField(default=True)
    map_show = models.BooleanField(default=False)
    speed_show = models.BooleanField(default=False)
    voice = models.BooleanField(default=False)
    font_big = models.BooleanField(default=False)
    show_gosnum = models.BooleanField(default=False)
    p2p_video = models.BooleanField(default=False)
    edit_mode = models.BooleanField(default=False)
    expert = models.BooleanField(default=False)
    color = None #  заглушечка
    ban = models.DateTimeField(null=True, blank=True)
    language = models.CharField(max_length=2, default="ru")
    radio = models.CharField(max_length=5, default="pop")
    driver_taxi = models.BooleanField(default=False)
    driver_bus = models.BooleanField(default=False)
    place = models.ForeignKey(Place, null=True, blank=True, on_delete=models.SET_NULL)
    attrs = models.JSONField(default=dict, blank=True, null=True)

    def tell_id(self):
        return "us_id=%s" % self.id

    def __str__(self):
        return "%s" % self.id

    def save(self, *args, **kwargs):
        super(UserSettings, self).save(*args, **kwargs)

        if self.id:
            us_get(self.id, force=True)

    def is_banned(self):
        ban = self.ban
        if ban and ban > datetime.datetime.now():
            return True
        else:
            return False


    @property
    def days_on(self):
        now = datetime.datetime.now()
        # now += datetime.timedelta(hours=self.city.timediffk)
        delta = (now - self.ctime).days
        return delta

    @property
    def days_veteran(self):
        if self.days_on > 30:
            return True
        else:
            return False

    @property
    def phone_dash(self):
        if len(self.phone) == len("+79291651337"):
            p = self.phone[2:]
            return "+7-%s-%s-%s" % (p[0:3], p[3:6], p[6:])
        return self.phone

    @property
    def no_ads(self):
        now = datetime.datetime.now()
        if self.user:
            delta = (now - self.user.date_joined).days
            if delta <= 30:
                return True
        else:
            return False

    def no_ads_for(self):
        now = datetime.datetime.now()
        if self.user:
            delta = (now - self.user.date_joined).days
            if delta <= 30:
                return self.user.date_joined+datetime.timedelta(days=30)
        else:
            return False

    @property
    def is_data_provider(self):
        if self.user and "data_provider" in get_groups(self.user):
            return True
        else:
            return False


    @property
    def l(self):
        return self.language
    @property
    def lang(self):
        return self.language
    # @property
    # def name(self):
    #     if self.user and self.user.first_name:
    #         return self.user.first_name
    #     elif self.name:
    #         return name
    #     else:
    #         return self.id
    @property
    def premium(self):
        if self.user:
            groups = get_groups(self.user)
            if 'editor' in groups or self.user.is_superuser:
                return True
        return False

    def get_groups(self):
        if self.user:
            return get_groups(self.user)
        return []


class Favorites(models.Model):
    us = models.ForeignKey(UserSettings, on_delete=models.CASCADE)
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE)
    counter = models.IntegerField(default=0)

    def save(self, *args, **kwargs):
        super(Favorites, self).save(*args, **kwargs)
        for p in self.bus.places.all():
            busfav_get(self.us, p, force=True)

def busfav_get(us, place, limit=5, force=False):
    cc_key = "busfav_%s_%s" % (us.id, place.id)
    busfavor = rcache_get(cc_key)
    if force or not busfavor:
        qs = Favorites.objects.filter(us=us, bus__places__id=place.id).values_list('bus_id', 'counter')
        busfavor = {}
        for k,v in qs:
            busfavor[k] = v
        busfavor = sorted(six.iteritems(busfavor), key=operator.itemgetter(1))
        busfavor.reverse()
        busfavor = busfavor[:30]
        busfavor = [x[0] for x in busfavor]
        rcache_set(cc_key, busfavor)

    busfavor = busfavor[:limit]
    bf = {}
    for b in busfavor:
        bus = bus_get(b)
        if bus:
            bf[bus] = bus.order or 0
    busfavor = sorted(six.iteritems(bf), key=operator.itemgetter(1))
    busfavor = [x[0] for x in busfavor]

    return busfavor


class MoTheme(models.Model):
    ctime = models.DateTimeField(auto_now_add=True, db_index=True)
    jdata = models.TextField(null=True, blank=True)
    counter = models.PositiveIntegerField(default=0)

    def __str__(self):
        return "id=%s, counter=%s, %s" % (self.id, self.counter, self.jdata)

    def as_dict(self):
        d = {
            "ctime": self.ctime,
            "jdata": self.jdata,
            "counter": self.counter,
        }
        return d

    def recount(self, *args, **kwargs):
        self.counter = MobileSettings.objects.filter(theme=self).count()
        self.save()


    class Meta:
        ordering = ('-counter', )

    # def recount(self, *args, **kwargs):
    #     self.counter = MobileSettings.objects.filter(theme=self).count()
    #     self.save()


class MobileSettings(models.Model):
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    ctime = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    mtime = models.DateTimeField(auto_now=True, null=True, blank=True)
    ltime = models.DateTimeField(null=True, blank=True)
    os = models.CharField(max_length=8, null=True, blank=True)
    uuid = models.CharField(
        max_length=128, null=True, blank=True, db_index=True)
    jdata = models.TextField(null=True, blank=True)
    city = models.ForeignKey(City, null=True, blank=True, on_delete=models.SET_NULL)
    place = models.ForeignKey(Place, null=True, blank=True, on_delete=models.SET_NULL)
    theme = models.ForeignKey(MoTheme, null=True, blank=True, on_delete=models.SET_NULL)

    gps_send = models.BooleanField(default=False)
    gps_send_bus = models.ForeignKey(Bus, null=True, blank=True, on_delete=models.SET_NULL)
    gosnum = models.CharField(max_length=16, null=True, blank=True)
    phone = models.CharField(max_length=16, null=True, blank=True)
    gps_send_ramp = models.BooleanField(default=False)
    gps_send_approved = models.DateTimeField(null=True, blank=True)
    gps_send_of = models.CharField(max_length=12, null=True, blank=True)
    name = models.CharField(max_length=24, null=True, blank=True)
    # 0-passenger, 1-driver(depr), 2-driver mode, 3-external city app
    mode = models.SmallIntegerField(default=0)
    approved_driver = models.BooleanField(default=False)
    device_type = models.SmallIntegerField(default=0)  # 0-phone, 1-tablet
    version = models.SmallIntegerField(default=0)
    arch = models.CharField(max_length=12, null=True, blank=True)  # arm, x86
    startups = models.PositiveIntegerField(default=0)
    color = models.CharField(max_length=6, null=True, blank=True)
    tcard = models.CharField(max_length=20, null=True, blank=True)
    ban = models.DateTimeField(null=True, blank=True)
    ref = models.TextField(null=True, blank=True)
    ref_other = models.PositiveIntegerField(default=0)
    ref_date = models.DateTimeField(null=True, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    sys_help = models.BooleanField(default=True)
    language = models.CharField(max_length=2, default="en")
    orator = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "Mobile Settings"
        # readonly_fields = ('ctime', 'mtime', 'ltime', )

    def tell_id(self):
        return "ms_id=%s" % self.id

    def __str__(self):
        return u"%s" % self.id

    def save(self, *args, **kwargs):
        super(MobileSettings, self).save(*args, **kwargs)
        if self.id:
            ms_get(self.id, force=True)

    def is_banned(self):
        ban = self.ban
        if ban and ban > datetime.datetime.now():
            return True
        else:
            return False

    @property
    def ltime_localized(self):
        return self.place.now
        # return self.ltime + datetime.timedelta(hours=self.city.timediffk)
    @property
    def l(self):
        return self.language
    @property
    def lang(self):
        return self.language
    @property
    def premium(self):
        if self.user:
            groups = get_groups(self.user)
            if 'editor' in groups or self.user.is_superuser:
                return True
        return False

    def get_groups(self):
        if self.user:
            return get_groups(self.user)
        return []


class Log(models.Model):
    date = models.DateTimeField(auto_now_add=True, db_index=True)
    ttype = models.CharField(max_length=16, null=True, blank=True, db_index=True)
    message = models.TextField()
    user = models.ForeignKey(UserSettings, null=True, blank=True, on_delete=models.SET_NULL)
    ms = models.ForeignKey(MobileSettings, null=True, blank=True, on_delete=models.SET_NULL)
    city = models.ForeignKey(City, null=True, blank=True, on_delete=models.SET_NULL)
    place = models.ForeignKey(Place, null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return self.message

    def as_dict(self):
        d = dict()
        for k, v in self.__dict__.items():
            if k.startswith('_'):
                pass
            elif type(v) == datetime.datetime:
                d[k] = str(v).split(".")[0]
            elif type(v) == UserSettings or type(v) == MobileSettings:
                pass
            elif k=="message" and self.ttype=="weather" and 'error' not in v:
                t = int( float(v) )
                if t>0:
                    d[k] = "+%s"%v
                else:
                    d[k] = v
            else:
                d[k] = v
        return d

    def message_short(self):
        message_short = self.message
        if len(message_short) > 57:
            message_short = message_short[:57]+"..."
        return message_short


def gosnum_update(gosnum):
    city, uniqueid = gosnum.city, gosnum.uniqueid
    cc_key = "uid_info_%s" % city.id
    uid_info = rcache_get(cc_key, {})
    uid_info[uniqueid] = uid_info.get(uniqueid, {})
    uid_info[uniqueid]['gosnum'] = gosnum.gosnum
    uid_info[uniqueid]['label'] = gosnum.label
    if gosnum.ramp is not None:
        uid_info[uniqueid]['ramp'] = gosnum.ramp
    rcache_set(cc_key, uid_info, 60*60*24*30)


class Gosnum(models.Model):
    date = models.DateTimeField(auto_now_add=True)
    us = models.ForeignKey(
        UserSettings, null=True, blank=True, related_name="usgos", on_delete=models.SET_NULL)
    ms = models.ForeignKey(
        MobileSettings, null=True, blank=True, related_name="msgos", on_delete=models.SET_NULL)
    city = models.ForeignKey(City, on_delete=models.CASCADE)
    uniqueid = models.CharField(max_length=12, null=True, blank=True)
    gosnum = models.CharField(max_length=12, null=True, blank=True)
    label = models.CharField(max_length=12, null=True, blank=True)
    countable = models.BooleanField(default=True)
    gift = models.BooleanField(default=False)
    ramp = models.BooleanField(null=True)
    model = models.CharField(max_length=30, null=True, blank=True)
    gosnum_override = models.BooleanField(default=False)    # разрешение редактирования, True = разрешено
    label_override = models.BooleanField(default=False)

    def __str__(self):
        return "%s: %s, %s = %s" % (self.date, self.city, self.uniqueid, self.gosnum)

    # class Meta:
    #     unique_together = ("city", "uniqueid")

    def agent_comment(self):
        if self.us:
            tr = get_transaction(self.us)
            if tr and tr.bonus:
                return tr.bonus.agent_comment
            else:
                return "не доступен"
        return ""

    def save(self, *args, **kwargs):
        if self.pk is None:
            cr = True
        else:
            cr = False
        super(Gosnum, self).save(*args, **kwargs)
        if not cr:  # update only if new one
            gosnum_update(self)
    class Meta:
        verbose_name = gettext_lazy("гос.номер")
        verbose_name_plural = gettext_lazy("гос.номера")


@receiver(pre_delete, sender=Gosnum)
def gosnum_pre_delete(sender, instance, using, **kwargs):
    city = instance.city
    uniqueid = instance.uniqueid
    cc_key = "uid_info_%s" % city.id
    uid_info = rcache_get(cc_key, {})

    if uid_info.get(uniqueid):
        del uid_info[uniqueid]
        qs = Gosnum.objects.filter(city=city, uniqueid=uniqueid).exclude(id=instance.id).order_by('-id')[:1]
        if qs:
            gosnum_update(qs[0])


class Mbox(models.Model):
    ctime = models.DateTimeField(auto_now_add=True)
    hostname = models.CharField(max_length=16, null=True, blank=True)
    ip4 = models.GenericIPAddressField(protocol='IPv4')
    ip6 = models.GenericIPAddressField(protocol='IPv6')
    public_key = models.CharField(max_length=64)

    def __str__(self):
        return self.hostname


class Finance(models.Model):
    ctime = models.DateTimeField(auto_now_add=True)
    agent = models.CharField(
        max_length=16, null=True, blank=True, default="alex")
    fiat = models.SmallIntegerField(null=True, blank=True, default=-1200)

    def __str__(self):
        return "%s %s %s" % (self.ctime, self.agent, self.fiat)


class Bonus(models.Model):
    ctime = models.DateTimeField(auto_now_add=True)
    mtime = models.DateTimeField(auto_now=True)
    activated = models.BooleanField(default=False)
    pin = models.CharField(max_length=16, null=True, blank=True)
    days = models.SmallIntegerField(default=5)
    comment = models.TextField(null=True, blank=True)
    agent = models.CharField(max_length=16, null=True, blank=True)
    agent_comment = models.CharField(max_length=16, null=True, blank=True)
    fiat = models.SmallIntegerField(null=True, blank=True, default=0)
    key = models.CharField(
        max_length=16, null=True, blank=True, default="premium")

    def save(self, *args, **kwargs):
        if not self.pin:
            self.pin = gener_pin()
        super(Bonus, self).save(*args, **kwargs)

    @property
    def color_code(self):
        if self.days == 3:
            c = "violet"
        elif self.days == 30:
            c = "green"
        elif self.key == "premium":
            c = "orange"
        elif self.days == 365:
            c = "red"
        else:
            c = "grey"
        if self.key == "driver":
            c = "blue"
        return c

    @property
    def rname(self):
        if self.days == 3:
            c = _("тестовый")
        elif self.days == 30:
            c = _("продление +30")
        elif self.days == 64:
            c = _("премиум 2м")
        elif self.key == "standard":
            c = _("стандарт")
        elif self.key == "premium":
            c = _("премиум 6м")
        else:
            c = _("неизвестно")
        if self.key == "driver":
            c = _("водитель")
        return c


# class ActiveTransactionManager(models.Manager):
#     def get_queryset(self):
#         return super(ActiveTransactionManager, self).get_queryset().filter(end_time__gte=datetime.datetime.now())

class Transaction(models.Model):
    ctime = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(UserSettings, null=True, blank=True, on_delete=models.SET_NULL)
    ms = models.ForeignKey(MobileSettings, null=True, blank=True, on_delete=models.SET_NULL)
    bonus = models.ForeignKey(Bonus, null=True, blank=True, on_delete=models.SET_NULL)
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
    vip = models.BooleanField(default=False)
    vip_name = models.CharField(max_length=16, null=True, blank=True)
    vip_city = models.ForeignKey(City, null=True, blank=True, on_delete=models.SET_NULL)
    objects = models.Manager()
    # active_objects = ActiveTransactionManager()

    def __str__(self):
        return "%s_%s_%s" % (self.key, self.ctime, self.fiat)

    def save(self, *args, **kwargs):
        if not self.pin:
            self.pin = gener_pin()
        super(Transaction, self).save(*args, **kwargs)

    @property
    def days_left(self):
        delta = self.end_time - datetime.datetime.now()
        return delta.days + 1

    @property
    def hours_left(self):
        delta = self.end_time - datetime.datetime.now()
        return delta.days + 1

    @property
    def warning(self):
        delta = self.end_time - datetime.timedelta(days=2)
        if datetime.datetime.now() > delta:
            return True
        else:
            return False

    @property
    def countdown(self):
        import pymorphy2
        MORPH = pymorphy2.MorphAnalyzer()
        delta = self.end_time - datetime.datetime.now()
        delta_days = delta.days + 1
        # ed.inflect({'gent'})[0]
        # ed.lexeme
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
    us = models.ForeignKey(UserSettings, null=True, blank=True, on_delete=models.SET_NULL)
    # ms = models.ForeignKey(MobileSettings, null=True, blank=True)
    # transaction = models.ForeignKey(UserSettings, null=True, blank=True)
    gosnum = models.CharField(max_length=16, null=True, blank=True)
    active = models.BooleanField(default=True)
    img = models.CharField(max_length=80, null=True, blank=True)
    city = models.ForeignKey(City, null=True, blank=True, on_delete=models.SET_NULL)
    place = models.ForeignKey(Place, null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return self.gosnum or ""

    def save(self, *args, **kwargs):
        super(SpecialIcon, self).save(*args, **kwargs)
        specialicons_cget(force=True)

    class Meta:
        verbose_name = gettext_lazy("иконка транспорта")
        verbose_name_plural = gettext_lazy("иконки транспорта")


class GameTimeTap(models.Model):
    ctime = models.DateTimeField(auto_now_add=True)
    mtime = models.DateTimeField(auto_now=True)
    ms = models.OneToOneField(MobileSettings, on_delete=models.CASCADE)
    score = models.PositiveIntegerField(db_index=True, null=True, blank=True)

    def __str__(self):
        return "%s: %s" % (self.ms, self.score)


def gener_pin():
    pin = ""
    for i in range(1, 15):
        if i % 5 == 0:
            pin += "-"
        else:
            pin += random.choice(string.digits)
    return pin


class BusStopIconImage(models.Model):
    fname = models.CharField(null=True, blank=True, max_length=32)
    name = models.CharField(null=True, blank=True, max_length=16)
    order = models.IntegerField(default=1)


class Unistop(models.Model):
    name = models.CharField(max_length=128)
    centroid = models.PointField(srid=4326, null=True, blank=True)
    icon = models.ForeignKey(BusStopIconImage, default=46, on_delete=models.SET_DEFAULT)

    def save(self, *args, **kwargs):
        if self.icon.id == 46:
            self.icon = determine_bs_icon(self.name)
        super(Unistop, self).save(*args, **kwargs)

    class Meta:
        unique_together = ("name", "centroid")


# VBusStop, виртуальная группа остановок, например "Торговый центр", их может быть 2-3
# то есть одной VBusStop может соответствовать несколько остановок
class VBusStop(models.Model):
    city = models.ForeignKey(City, on_delete=models.CASCADE)
    name = models.CharField(max_length=128)
    name_alt = models.CharField(max_length=128, null=True, blank=True)
    icon = models.ForeignKey(BusStopIconImage, default=46, on_delete=models.SET_DEFAULT)

    class Meta:
        unique_together = ("city", "name")

    def save(self, *args, **kwargs):
        if self.icon.id == 46:
            self.icon = determine_bs_icon(self.name)
        super(VBusStop, self).save(*args, **kwargs)

'''
кэш city_buses_invalidate используется в utils/city_buses_invalidate.py, запускаемом из крона
'''
def fill_jamline_list(city_id, buses=[]):
    cityes = rcache_get("city_buses_invalidate", {})
    if city_id not in cityes:
        cityes[city_id] = buses
    else:
        for b in buses:
            if b not in cityes[city_id]:
                cityes[city_id].append(b)
    rcache_set("city_buses_invalidate", cityes, 60*60*24)


class Feature(models.Model):
    class FeatureType(models.IntegerChoices):
        VEHICLE_MODEL = 1, _("Vehicle Model")
        VEHICLE = 2, _("Vehicle")
        NBUS_STOP = 3, _("Bus Stop")    

    ttype = models.SmallIntegerField(choices=FeatureType.choices, null=True, blank=True, verbose_name='type of property') # TODO: convert to enum
    name = models.CharField(verbose_name='name', max_length=250)
    ctime = models.DateTimeField(auto_now_add=True)
    mtime = models.DateTimeField(auto_now=True, null=True, blank=True)

    def __str__(self) -> str:
        return self.name

    class Meta:
        verbose_name = _("feature")
        verbose_name_plural = _('features')


class NBusStop(models.Model):  # caching.base.CachingMixin,
    city = models.ForeignKey(City, null=True, blank=True, on_delete=models.SET_NULL)
    city_osm= models.BigIntegerField(null=True, blank=True)
    ttype = models.IntegerField(null=True, blank=True, choices=TTYPE_CHOICES, default=0)
    # vbusstop = models.ForeignKey(VBusStop, null=True, blank=True)
    name = models.CharField(max_length=128)
    name_alt = models.CharField(max_length=128, null=True, blank=True) # todel
    point = models.PointField(srid=4326, null=True, blank=True)
    moveto = models.CharField(max_length=128, null=True, blank=True)
    # xeno_id = models.BigIntegerField(null=True, blank=True)
    xeno_id = models.CharField(null=True, blank=True, max_length=100)
    osm_id = models.BigIntegerField(null=True, blank=True)  # см. turbo_stop_osm_fill.py
    tram_only = models.BooleanField(default=False) # pls upgrade to ttype
    slug = models.CharField(max_length=128, null=True, blank=True)
    unistop = models.ForeignKey(Unistop, null=True, blank=True, on_delete=models.SET_NULL)    
    timezone = TimeZoneField(use_pytz=False, null=True, blank=True)
    objects = GeoManager()

    class Meta:
        indexes = [
            models.Index(fields=['xeno_id',]),
        ]

    def __str__(self):
        return u"%s %s->%s" % (self.id, self.name, self.moveto)

    def __get_time_zone(self):
        if not self.point:
            return None
        try:
            tz_name = timezone_finder.timezone_at_land(lng=self.point.x, lat=self.point.y)
        except ValueError:
            return None
        return tz_name

    def save(self, *args, **kwargs):
        if "'" in self.name:  # don't allow, otherwise JS crashes
            self.name = self.name.replace("'", "")
        self.name = bus_stop_name_beauty(self.name)
        s = nslugify(self.name)
        if not self.slug:
            self.slug = s
        elif s != self.slug:
            url_old = self.get_slug_url()
            self.slug = s
            url_new = self.get_slug_url()
            um, cr = URLMover.objects.get_or_create(url_old=url_old)
            um.url_new = url_new
            um.save()
        tz_name = self.__get_time_zone()
        if self.timezone != tz_name:
            self.timezone = tz_name
        super(NBusStop, self).save(*args, **kwargs)
        # check for vbus
        # VBusStop.objects.get_or_create(city=self.city, name=self.name)
        # clean stalled vbusstops here?
        # get_busstop_points(self.city, force=True)
        if self.city and not self.city.skip_recalc:
            buses = list(Route.objects.filter(busstop_id=self.id).values_list('bus_id', flat=True))
            fill_jamline_list(self.city.id, buses)

    def get_slug_url(self):
        return "/stop/%s/" % (self.slug)
    def get_absolute_url(self):
        return "/stop/id/%s/" % (self.id)


@receiver(post_save, sender=NBusStop)
def nbusstop_post_save(sender, created, instance, **kwargs):
    def midpoint(p1, p2):
        if p1 is None:
            return p2
        elif p2 is None:
            return p1
        return Point((p1.x + p2.x) * 0.5, (p1.y + p2.y) * 0.5)

    if (created or instance.unistop is None) and instance.point:
        stop = instance
        busstops = NBusStop.objects.filter(Q(point__distance_lte=(stop.point, D(m=1000)), name=stop.name))
        unistops = Unistop.objects.filter(Q(centroid__distance_lte=(stop.point, D(m=1000)), name=stop.name))
        if not unistops:
            ustop = Unistop.objects.create(name=stop.name, centroid=stop.point)
        else:
            ustop = unistops.first()
        for s in busstops:
            ustop.centroid = midpoint(ustop.centroid, s.point)
        ustop.save()

        stop.unistop = ustop
        stop.save()
    # else:
    #     if instance.name != instance.unistop.name:
    #         instance.unistop.name = instance.name


"""
@receiver(post_delete, sender=NBusStop)
def NBusStop_post_delete(sender, instance, **kwargs):
    buses = list(Route.objects.filter(busstop_id=instance.id).values_list('bus_id', flat=True))
    fill_jamline_list(instance.city.id, buses)  # 'NoneType' object has no attribute 'id', TODO: fill_jamline_list py place
"""

class NBusStopFeature(models.Model):
    class NBusStopFeatureManager(Manager):
        def get_queryset(self):
            return super().get_queryset().filter(feature__ttype=Feature.FeatureType.NBUS_STOP)

    busstop = models.ForeignKey(NBusStop, on_delete=models.CASCADE)
    feature = models.ForeignKey(Feature, verbose_name="feature", on_delete=models.CASCADE)
    value = models.CharField(verbose_name='value', max_length=250)
    ctime = models.DateTimeField(auto_now_add=True)
    mtime = models.DateTimeField(auto_now=True, null=True, blank=True)

    objects: NBusStopFeatureManager()

    class Meta:
        verbose_name = _('nbusstop feature')
        verbose_name_plural = _('nbusstop features')


class GraphRouteVertex(models.Model):
    id = models.BigAutoField(primary_key=True)
    content_type = models.ForeignKey(ContentType, null=True, on_delete=models.SET_NULL)
    content_object = GenericForeignKey('content_type', 'object_id')
    object_id = models.PositiveIntegerField(null=True)
    type = models.IntegerField(null=True)
    city_id = models.IntegerField(null=True)


class GraphRouteEdge(models.Model):
    id = models.BigAutoField(primary_key=True)
    city = models.ForeignKey(City, on_delete=models.CASCADE)

    src_type = models.ForeignKey(ContentType, related_name='src_type', on_delete=models.CASCADE)
    src_object = GenericForeignKey('src_type', 'src')
    src = models.PositiveIntegerField(null=False)
    src_level = models.IntegerField(default=0)

    dst_type = models.ForeignKey(ContentType, related_name='dst_type', on_delete=models.CASCADE)
    dst_object = GenericForeignKey('dst_type', 'dst')
    dst = models.PositiveIntegerField(null=False)
    dst_level = models.IntegerField(default=0)

    source = models.ForeignKey(GraphRouteVertex, related_name='source', on_delete=models.SET_NULL, null=True, db_column="source")
    target = models.ForeignKey(GraphRouteVertex, related_name='target', on_delete=models.SET_NULL, null=True, db_column="target")
    # source = models.PositiveBigIntegerField()
    # target = models.PositiveBigIntegerField()

    cost = models.FloatField(null=True)
    static_cost = models.IntegerField(null=True)
    distance = models.FloatField(null=True)
    time = models.PositiveBigIntegerField(null=True)

    ttype = models.IntegerField(null=True)
    geom = models.GeometryField(null=False)

    class Meta:
        unique_together = [("src", "src_type", "dst", "dst_type"), ("source", "target")]


class Route(models.Model):
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE)
    busstop = models.ForeignKey(NBusStop, on_delete=models.CASCADE)
    endpoint = models.BooleanField(default=False)
    direction = models.SmallIntegerField(null=True, blank=True, db_index=True)
    order = models.SmallIntegerField(null=True, blank=True, db_index=True)
    # среднее время прохождения от предыдущей остановки
    # time_avg = models.IntegerField(null=True, blank=True)
    # xeno_id = models.BigIntegerField(null=True, blank=True)

    def __str__(self):
        return u"%s: %s, d=%s" % (self.bus, self.busstop, self.direction)

    def __str__(self):
        return u"%s: %s, d=%s" % (self.bus, self.busstop, self.direction)

    @staticmethod
    def as_dict(with_bus=False, with_busstop=False):
        with connection.cursor() as cursor:
            cursor.execute("SELECT br.id, br.bus_id, br.busstop_id, br.endpoint, br.order, br.direction, "
                           "bn.name, bn.name_alt, ST_X(bn.point) AS x, ST_Y(bn.point) AS y, bn.moveto, "
                           "bn.city_id, bn.xeno_id, bn.tram_only, bn.slug, bn.osm_id, bn.ttype, bn.timezone "
                           "FROM bustime_route br "
                           "INNER JOIN bustime_nbusstop bn ON br.busstop_id = bn.id "
                           "ORDER BY br.bus_id, br.direction, br.order")

    def save(self, skip_recalc=False, *args, **kwargs):
        super(Route, self).save(*args, **kwargs)
        if skip_recalc == False and (self.bus.city.skip_recalc if self.bus.city else False) == False:
            bus = self.bus
            fill_inter_stops_for_bus(bus)

            place = bus.places.order_by("-population").first()
            if place:
                bus.ctime = place.now

            bus.save()

            fill_bus_endpoints(bus)
            if place:
                fill_jamline_list(place.id, [bus.id])
        cc_key = f"turbo_{self.bus_id}"
        REDIS_W.publish(cc_key, pickle_dumps({"cmd": "reload"}))


@receiver(post_delete, sender=Route)
def Route_post_delete(sender, instance, **kwargs):
    place = instance.bus.places.order_by("-population").first()
    if place:
        fill_jamline_list(place.id, [instance.bus.id])


class RoutePreview(models.Model):
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE)
    busstop = models.ForeignKey(NBusStop, on_delete=models.CASCADE)
    endpoint = models.BooleanField(default=False)
    direction = models.SmallIntegerField(null=True, blank=True, db_index=True)
    order = models.SmallIntegerField(null=True, blank=True, db_index=True)
    def __str__(self):
        return u"%s: %s, d=%s" % (self.bus, self.busstop, self.direction)


class RouteLine(models.Model):
    ctime = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    mtime = models.DateTimeField(null=True, blank=True)
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE)
    direction = models.SmallIntegerField("Направление", null=True, blank=True)
    line = models.LineStringField(srid=4326, null=True, blank=True)
    autofill = models.BooleanField("Автозаполнение", default=True)

    class Meta:
        unique_together = ("bus", "direction")
    def __str__(self):
        return u"%s: d=%s" % (self.bus, self.direction)
    @property
    def bus_napr(self):
        if self.direction == 0:
            return self.bus.napr_a
        else:
            return self.bus.napr_b
    bus_napr.fget.short_description = _('Направление')
    class Meta:
        verbose_name = gettext_lazy("нить маршрута")
        verbose_name_plural = gettext_lazy("нити маршрутов")

class Uevent(models.Model):
    """
    as fresh as it can
    """
    id = models.BigAutoField(primary_key=True)
    uniqueid = models.TextField(db_index=True)
    timestamp = models.DateTimeField(db_index=True)
    # bus = models.ForeignKey(Bus, null=True, blank=True)
    bus_id = models.IntegerField(null=True, blank=True, db_index=True)
    heading = models.IntegerField(null=True, blank=True)
    speed = models.IntegerField(null=True, blank=True)
    x = models.FloatField(null=True, blank=True)
    y = models.FloatField(null=True, blank=True)
    direction = models.SmallIntegerField(null=True, blank=True)
    gosnum = models.TextField(null=True, blank=True, db_index=True)
    ramp = models.BooleanField(null=True)
    rampp = models.BooleanField(null=True)
    custom = models.BooleanField(default=False)
    objects = GeoManager()
    channel = models.CharField(max_length=255, null=True, blank=True)
    src = models.CharField(max_length=255, null=True, blank=True)

    def get_absolute_url(self):
        return "/uevent/%d/" % self.id

    def __str__(self):
        return u"%s: %s-%s-%s %s %s" % (self.timestamp, self.bus_id, self.uniqueid, self.gosnum, self.x, self.y)


class Event(dict):

    """
    performance heaven
    """
    @property
    def uniqueid(self):
        return self.get("uniqueid")

    @property
    def bus(self):
        return self.get("bus")

    @property
    def bus_id(self):
        return self.get("bus_id")

    @property
    def time(self):
        return self.get("timestamp")

    @property
    def timestamp(self):
        return self.get("timestamp")

    @property
    def last_changed(self):
        return self.get("last_changed")

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
    def away(self):
        return self.get("away", False)

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

    @property
    def custom(self):
        return self.get("custom", False)

    @property
    def uid_original(self):
        return self.get("uid_original")

    @property
    def channel(self):
        return self.get("channel")

    @property
    def src(self):
        return self.get("src")

    def as_dict(self):
        d = dict()
        d["bus_id"] = self.bus_id or self.bus
        bus_name = bus_get(d["bus_id"])
        if bus_name:
            bus_name = bus_name.name
        d["bus_name"] =  bus_name
        for k, v in self.items():
            if type(v) == datetime.datetime:
                d[k] = str(v)
            elif k == "busstop_nearest" and self.busstop_nearest: # todo, norn check for nearest == id
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

    def as_json_friendly(self):
        d = dict()
        d["bus_id"] = self.bus_id or self.bus
        bus_name = bus_get(d["bus_id"])
        if bus_name:
            bus_name = bus_name.name
        d["bus_name"] =  bus_name
        for k, v in self.items():
            if type(v) == datetime.datetime:
                d[k] = str(v)
            elif type(v) == Bus or type(v) == Route:
                d[k] = str(v.id) + " " + str(v)
                if type(v) == Route:
                    d['direction'] = v.direction
            else:
                d[k] = v
        return d

    def as_mobile(self):
        d = dict()
        for k, v in self.items():
            if type(v) == datetime.datetime:
                d[k] = six.text_type(v)
            elif type(v) == str:
                d[k] = six.text_type(v)
            elif v and type(v) == Bus or type(v) == Route:
                d[k] = v.id
            else:
                d[k] = v
        # uniqueid 26578218 <type 'str'>
        return d

    def as_mobile_v2(self):
        lava = self.get_lava()
        if lava.get('bn'):
            del lava['bn']
            del lava['order']
        lava['id'] = self.bus_id
        #lava['g'] = unicode(str(lava['g']) if lava['g'] else '')
        return lava

    def get_lava(self):
        e = self
        # copy-paste from update_lib.py
        lava = {'x': e.x, 'y': e.y, 's': e.speed, 'r': e.ramp,
                'h': e.heading, 'u': six.text_type(e.uniqueid),
                'ts': int(time.mktime(e['timestamp'].timetuple()))}
        if e.busstop_nearest:
            if type(e.busstop_nearest) == int:
                lava['b'] = e.busstop_nearest
                lava['d'] = e['direction']
                lava['bn'] = e['nearest_name']
                lava['order'] = e['nearest_order']
            else:
                lava['d'] = e.busstop_nearest.direction
                lava['bn'] = e.busstop_nearest.busstop.name
                lava['b'] = e.busstop_nearest.id
                lava['order'] = e.busstop_nearest.order
        if e.gosnum:
            e['gosnum'] = str(e.gosnum)
            e['gosnum'] = e.gosnum.replace(" ", "")
            e['gosnum'] = e.gosnum.replace("(", "")
            e['gosnum'] = e.gosnum.replace(")", "")
            if not e.get("gosnum_override") and not e.get("custom"):
                e['gosnum'] = e['gosnum'][:8]
            lava['g'] = e.gosnum
        if e.get("gosnum_override"):
            lava['gosnum_override'] = True
        if e.x_prev:
            lava['px'], lava['py'] = e.x_prev, e.y_prev
        if e.sleeping:
            lava['sleep'] = 1
        if e.get('away'):
            lava['away'] = 1
        if e.get("tface"):
            lava['tface'] = e["tface"]
        if e.custom:
            lava['custom'] = 1
            lava['custom_src'] = e['custom_src']
            if e.get("tcolor") and e["tcolor"] != 'F4C110' and e["tcolor"] != 'f4c110':
                lava['tcolor'] = e["tcolor"]
            if e.get("tface"):
                lava['tface'] = e["tface"]
        if e.get("label"):
            lava['l'] = str(e["label"]).strip('"[]{}()*=.,:;_&?^%$#@! ').replace('None', '')
        if e.get('rampp'):
            lava['rr'] = True
        if e.get('driver_ava'):
            lava['driver_ava'] = e['driver_ava']
        if e.get('name'):
            lava['name'] = e['name']
        if e.get('zombie'):
            lava['z'] = True
        return lava

    def __init__(self, *args, **kwargs):
        if not self.get("uid_code"):
            super(Event, self).__init__(*args, **kwargs)
            self['uid_original'] = self['uniqueid']
            cs = sys._getframe().f_back.f_code.co_filename.split('/')[-2:]
            if not self.get('channel'):
                self['channel'] = cs[0]   # caller file folder name
            if not self.get('src'):
                self['src'] = cs[-1]   # caller file name
            self['uniqueid'] = make_uid_(self['uniqueid'], self['channel'], self['src'])
            self['uid_code'] = 2
# Event


class Sound(models.Model):
    text = models.TextField()
    voice = models.IntegerField(
        null=True, blank=True, choices=VF_VOICE_CHOICES)


class IPcity(models.Model):
    ctime = models.DateTimeField(auto_now_add=True)
    ip = models.GenericIPAddressField(unique=True, db_index=True)
    city = models.ForeignKey(City, on_delete=models.CASCADE)
    whois_results = models.TextField(blank=True, null=True)
    default_drop = models.BooleanField(default=False)

    def __str__(self):
        return "%s-%s" % (self.ip, self.city.slug)


class Song(models.Model):
    ctime = models.DateTimeField(auto_now_add=True)
    url = models.CharField(max_length=128, null=True, blank=True)
    name = models.CharField(max_length=128, null=True, blank=True)
    name_short = models.CharField(max_length=64, null=True, blank=True)
    lucky = models.BooleanField(default=False)
    skip_seconds = models.IntegerField(default=39, null=True, blank=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return "%s" % (self.name_short)


class VehicleBrand(models.Model):
    name = models.CharField(max_length=64, null=True)
    slug = models.SlugField(max_length=64, allow_unicode=True, blank=True, null=True, unique=True)
    ctime = models.DateTimeField(auto_now_add=True)
    mtime = models.DateTimeField(auto_now=True, null=True, blank=True)

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name

    class Meta:
        verbose_name = _('vehicle brand')
        verbose_name_plural = _('vehicle brands')


class VehicleModel(models.Model):
    name = models.CharField(max_length=64, null=True)
    brand = models.ForeignKey(VehicleBrand, models.CASCADE, null=True, blank=True, db_index=True)
    slug = models.SlugField(max_length=64, allow_unicode=True, blank=True, null=True, unique=True)
    ctime = models.DateTimeField(auto_now_add=True)
    mtime = models.DateTimeField(auto_now=True, null=True, blank=True)
    features = models.ManyToManyField(Feature, through='bustime.VehicleModelFeature', verbose_name='features'),

    def __str__(self) -> str:
        return f"{self.name} ({self.brand})"

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = _('vehicle model')
        verbose_name_plural = _('vehicle models')


class VehicleModelFeature(models.Model):
    class VehicleModelFeatureManager(Manager):
        def get_queryset(self):
            return super().get_queryset().filter(feature__ttype=Feature.FeatureType.VEHICLE_MODEL)

    vehicle_model = models.ForeignKey(VehicleModel, verbose_name="vehicle model", on_delete=models.CASCADE)
    feature = models.ForeignKey(Feature, verbose_name="feature", on_delete=models.CASCADE)
    value = models.CharField(verbose_name='value', max_length=250)
    ctime = models.DateTimeField(auto_now_add=True)
    mtime = models.DateTimeField(auto_now=True, null=True, blank=True)

    objects = VehicleModelFeatureManager()

    class Meta:
        verbose_name = _('vehicle model feature')
        verbose_name_plural = _('vehicle model features')


class Vehicle(models.Model):
    uniqueid = models.CharField("ID", max_length=12, primary_key=True)  # , description='ID'
    gosnum = models.CharField("Гос.№",max_length=12, null=True, blank=False,  db_index=True, help_text=u'Верхний регистр, без пробелов и дефисов')   # , description=u'Гос.№'
    gosnum_allow_edit = models.BooleanField("Разрешено ред. Гос.№ пользователю", default=True)    # , description=u'Разрешено ред. Гос.№ пользователю'
    bortnum = models.CharField("Борт.№", max_length=12, null=True, blank=True, help_text=u'Верхний регистр, без пробелов и дефисов')  # , description=u'Борт.№'
    bortnum_allow_edit = models.BooleanField("Разрешено ред. Борт.№ пользователю", default=True) # , description=u'Разрешено ред. Борт.№ пользователю'
    ramp = models.BooleanField("Низкопольность", default=False, db_index=True)   # , description=u'Есть лифт'
    model = models.CharField("Модель ТС", max_length=30, null=True, blank=True)  # , description=u'Модель ТС'
    vmodel = models.ForeignKey(VehicleModel, models.SET_NULL, null=True, blank=True, db_index=True)
    city = models.ForeignKey(City, models.SET_NULL, null=True, blank=True, db_index=True) # , description=u'Город'
    provider = models.ForeignKey(BusProvider, models.SET_NULL, null=True, blank=True)   # , description=u'Перевозчик'
    uid_provider = models.CharField("ID ТС от провайдера", max_length=100, null=True, blank=True, db_index=True)   # , description=u'ID ТС от провайдера'
    created_auto = models.BooleanField("ТС создано сервером",  default=False, db_index=True)   # , description=u'ТС создано сервером'
    created_date = models.DateTimeField("Дата создания ТС", auto_now_add=True, editable=False, db_index=True)  # , description=u'Дата создания ТС'
    modified_date = models.DateTimeField(editable=False, auto_now=True, null=True, blank=True)
    region = models.CharField("Регион", max_length=3, null=True, blank=True, db_index=True, help_text=u'Регион регистрации ТС')   # , description=u'Регион'
    channel = models.CharField(max_length=255, null=True, blank=True)
    src = models.CharField(max_length=255, null=True, blank=True)
    datasource = models.ForeignKey("DataSource", null=True, blank=True, on_delete=models.SET_NULL)
    ttype = models.IntegerField(choices=TTYPE_CHOICES, null=True, blank=True)
    features = models.ManyToManyField(Feature, through='bustime.VehicleFeature', verbose_name='features'),

    @staticmethod
    def format_bortnum(bortnum):
        return str(bortnum).strip('\\\'"[]{}()*=.,:;_&?^%$#@!/').upper().replace('NONE', '').strip()[:12] if bortnum else None

    @staticmethod
    def format_gosnum(gosnum):
        return str(gosnum).strip()[:8].upper() if gosnum else None

    @staticmethod
    def format_model(model):
        return str(model)[:30] if model else None

    @property
    def places(self):
        return list(self.datasource.places.all())

    def __str__(self):
        return "%s: %s, %s, %s, %s-created" % (self.uniqueid, self.gosnum, self.city, self.created_date, 'auto' if self.created_auto else 'user')

    '''
    Called with Model.create() & record.save()
    NOT CALLEND with Model.filter().update() ! NOT USE update()
    https://stackoverflow.com/questions/30449960/django-save-vs-update-to-update-the-database/30453181#30453181
    '''
    def save(self, user=None, is_citynews=True, *args, **kwargs):
        # vehicles = vehicles_cache(self.city)
        # gosnum_old = vehicles[self.uniqueid]['gosnum'] if vehicles.get(self.uniqueid) else None
        self.gosnum = Vehicle.format_gosnum(self.gosnum)
        self.bortnum = Vehicle.format_bortnum(self.bortnum)
        if (self.bortnum and len(self.bortnum) == 0) or self.bortnum == '' or self.bortnum == ' ':
            self.bortnum = None
        self.model = Vehicle.format_model(self.model)
        super(Vehicle, self).save(*args, **kwargs)

    def create_citynews(self, user, gosnum_old):
        from reversion import set_comment, is_active
        news = None
        if gosnum_old and gosnum_old != self.gosnum:
            if self.gosnum:
                news = _('Для ТС %s изменён гос.№ с %s на %s') % (self.uniqueid, gosnum_old, self.gosnum)
            else:
                news = _('У ТС %s удалён гос.№ %s') % (self.uniqueid, gosnum_old)
        elif self.gosnum:
            news = _('Для ТС %s установлен гос.№ %s') % (self.uniqueid, self.gosnum)
        news_link = '/wiki/bustime/vehicle/%s/change/' % (self.uniqueid)
        if news:
            if is_active():
                set_comment(news)
            CityNews.objects.create(title= _('Автоновость'), city=self.city, news_type=2,
                                    body=news, author=user, news_link=news_link)


    class Meta:
        verbose_name = gettext_lazy("Транспортное средство")
        verbose_name_plural = gettext_lazy("Транспортные средства")
# class Vehicle

@receiver(pre_delete, sender=Vehicle)
def vehicle_pre_delete(sender, instance, using, **kwargs):
    # удаление машины из кэша vehicles
    # vehicles = vehicles_cache(instance.city)
    # if vehicles.get(instance.uniqueid):
    #     del vehicles[instance.uniqueid]
    #     vehicles_cache(instance.city, vehicles)

    # удаление машины из кэша gosnums
    if not instance:
        return
    cc_gos_list = [f"gosnum_{p.id}" for p in instance.places]    # список уникальных гос№ города
    for cc_gos in cc_gos_list:
        gosnums = rcache_get(cc_gos, {})
        if instance.gosnum in gosnums and instance.uniqueid == gosnums[instance.gosnum].get('uniqueid'):
            del gosnums[instance.gosnum]
            rcache_set(cc_gos, gosnums, 60*60*24*30)
# def vehicle_pre_delete

def vehicles_cache(city, vehicles=None, force=False):
    cc_key = "vehicles_%s" % city.id
    cc_gos = "gosnums_%s" % city.id # список уникальных гос№ города

    if not vehicles:
        if force:
            vehicles = {}
            gosnums = {}
        else:
            vehicles = rcache_get(cc_key, {})
            gosnums = rcache_get(cc_gos, {})

        if not vehicles:
            # .order_by('gosnum', 'created_auto') нужен только для gosnums, чтобы
            # присылаемые пользователями были гарантированно в списке (для analyze_events)
            #Vehicle.objects.filter(datasource__places=place).order_by('gosnum', 'created_auto')
            for v in Vehicle.objects.filter(Q(datasource__places__id=city.id)|Q(city_id=city.id)).order_by('gosnum', 'created_auto'):
                vehicles[v.uniqueid] = {
                    'gosnum': v.gosnum,
                    'bortnum': v.bortnum,
                    'ramp': v.ramp,
                    'model': v.model,
                    'uid_provider': v.uid_provider,
                    'created_auto': v.created_auto,
                }
                # первый встреченный гос№ заносится в список, остальные игнорируются
                if v.gosnum:
                    if v.gosnum not in gosnums:
                        gosnums[v.gosnum] = {
                            'uniqueid': v.uniqueid, # этот ID всегда будет в эвентах этой машины
                            'bortnum': v.bortnum,
                            'ramp': v.ramp,
                            'model': v.model,
                            'uid_provider': [v.uid_provider],
                            'created_auto': v.created_auto,
                        }
                    else:
                        gosnums[v.gosnum]['uid_provider'].append(v.uid_provider)
            # for v in Vehicle.objects.all()
            rcache_set(cc_key, vehicles, 60*60*24*30)
            rcache_set(cc_gos, gosnums, 60*60*24*30)
    else:
        rcache_set(cc_key, vehicles, 60*60*24*30)

    return vehicles
# def vehicles_cache


class VehicleFeature(models.Model):
    class VehicleFeatureManager(Manager):
        def get_queryset(self):
            return super().get_queryset().filter(feature__ttype=Feature.FeatureType.VEHICLE)

    vehicle = models.ForeignKey(Vehicle, verbose_name="vehicle", on_delete=models.CASCADE)
    feature = models.ForeignKey(Feature, verbose_name="feature", on_delete=models.CASCADE)
    value = models.CharField(verbose_name='value', max_length=250)
    ctime = models.DateTimeField(auto_now_add=True)
    mtime = models.DateTimeField(auto_now=True, null=True, blank=True)

    objects: VehicleFeatureManager()

    class Meta:
        verbose_name = _('vehicle feature')
        verbose_name_plural = _('vehicle features')


class Vehicle1(models.Model):
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE)
    gosnum = models.CharField(max_length=16)
    driver_ava = models.CharField(
        max_length=16, null=True, blank=True)
    # ava_conductor = models.CharField(
    #     max_length=16, null=True, blank=True)
    rating_wilson = models.FloatField(default=0)
    votes_wilson = models.SmallIntegerField(default=0)
    rating_position = models.SmallIntegerField(default=999)

    comments = models.SmallIntegerField(
        default=0, null=True, blank=True)
    comments_driver = models.SmallIntegerField(
        default=0, null=True, blank=True)
    comments_conductor = models.SmallIntegerField(
        default=0, null=True, blank=True)

    class Meta:
        unique_together = ("bus", "gosnum")

    def __str__(self):
        return u"%s: %s - %s" % (self.bus, self.gosnum, self.rating_wilson)

    @property
    def rating_wilson_human(self):
        return round(self.rating_wilson * 5, 3)

    def save(self, *args, **kwargs):
        if not self.driver_ava:
            if self.bus.ttype == 2:
                vdict = {"females": True, "males": False}
            # elif self.ttype == 1:
            #     vdict = {"females": True, "males": True}
            else:
                vdict = {"males": True, "females": False}
            self.driver_ava = six.text_type(random.choice(get_ava_photos(**vdict)))
        super(Vehicle1, self).save(*args, **kwargs)


def star_wilson(votes):
    positives, totals = 0, 0
    for positive,stars in votes:
        if stars:
            positives += stars - 1
        elif positive:
            positives += 4
        totals += 4
    return wilson_rating(positives, totals)


def vote_recalc_rating(vehicle):
    votes = Vote.objects.filter(vehicle=vehicle)
    rating_ = star_wilson(votes.values_list('positive', 'stars'))
    vehicle.rating_wilson = float("%.3f" % rating_)
    vehicle.comments = votes.filter(comment__isnull=False) \
        .exclude(comment="").count()
    vehicle.save()
    pos = 1
    for v in Vehicle1.objects.filter(bus__city=vehicle.bus.city,
                                    rating_wilson__gt=0).order_by('-rating_wilson'):
        if v.rating_position != pos:
            v.rating_position = pos
            v.save()
        pos += 1


class Vote(models.Model):
    ctime = models.DateTimeField()
    us = models.ForeignKey(UserSettings, null=True, blank=True, on_delete=models.SET_NULL)
    ms = models.ForeignKey(MobileSettings, null=True, blank=True, on_delete=models.SET_NULL)
    vehicle = models.ForeignKey(Vehicle1, null=True, blank=True, on_delete=models.SET_NULL)
    # 0-driver, 1-conductor
    target = models.SmallIntegerField(default=0, null=True, blank=True)
    stars = models.SmallIntegerField(null=True, blank=True)
    positive = models.BooleanField(default=True)
    comment = models.CharField(max_length=200, null=True, blank=True)
    name = models.CharField(max_length=24, null=True, blank=True)
    color = models.CharField(max_length=6, null=True, blank=True)
    photo = models.ImageField(upload_to="vote", null=True, blank=True, storage=fsZ)

    def __str__(self):
        return u"%s-%s" % (self.vehicle, self.positive)
    class Meta:
        verbose_name = gettext_lazy("голос")
        verbose_name_plural = gettext_lazy("голоса")

    def stars_as_list(self):
        return list(range(0, self.stars))

    def save(self, *args, **kwargs):
        super(Vote, self).save(*args, **kwargs)
        vote_recalc_rating(self.vehicle)

    def as_dict(self):
        d = {"id": self.id, "positive": self.positive,
             "comment": self.comment, "name": self.name}
        d["ctime"] = lotime(self.ctime)
        d["stars"] = self.stars
        if self.ms:
            d["ms_id"] = self.ms_id
        else:
            d["us_id"] = self.us_id
        d["color"] = self.color
        d["likes"], d["dislikes"] = Like(content_type=ContentType.objects.get_for_model(self), object_id=self.id).get_likes()
        if self.photo:
            d["photo"] = six.text_type(self.photo.url)
            d["photo_thumbnail"] = six.text_type(get_thumbnail(self.photo, '427x320', quality=70).url)
        return d

    @property
    def user(self):
        if self.ms:
            return self.ms
        elif self.us:
            return self.us

    def photo_tag(self):
        return u'<img src="%s" />' % get_admin_thumb(self.photo).url
    photo_tag.short_description = 'Фото'
    photo_tag.allow_tags = True


class GVote(models.Model):
    ctime = models.DateTimeField(auto_now_add=True)
    mtime = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(UserSettings, on_delete=models.CASCADE)
    target = models.SmallIntegerField(default=0)
    positive = models.BooleanField(default=True)
    comment_time = models.DateTimeField(blank=True, null=True)
    comment = models.CharField(max_length=1024, blank=True, null=True)
    # target 0 is site itself

    def __str__(self):
        return u"%s-%s" % (self.user, self.positive)

    @property
    def show_comment(self):
        s = False
        d = datetime.timedelta(seconds=1)

        if self.positive == False:
            if self.comment_time == None:
                s = True
            elif self.mtime - self.comment_time > d:
                s = True

        return s


class Payment(models.Model):
    ctime = models.DateTimeField(auto_now_add=True)
    mtime = models.DateTimeField(auto_now=True)
    us = models.ForeignKey(UserSettings, blank=True, null=True, on_delete=models.SET_NULL)
    ms = models.ForeignKey(MobileSettings, blank=True, null=True, on_delete=models.SET_NULL)
    amount = models.SmallIntegerField(default=500)
    key = models.CharField(max_length=16, default="premium")
    value = models.CharField(max_length=16, default="")
    paid = models.BooleanField(default=False)
    paid_on = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        user = self.get_user()
        return u"%s=%s, %s rub." % (self.who(), self.get_user().id, self.amount)

    def who(self):
        if self.us:
            return "us"
        elif self.ms:
            return "ms"

    def get_user(self):
        if self.us:
            return self.us
        elif self.ms:
            return self.ms


class AdGeo(models.Model):
    ctime = models.DateTimeField(auto_now_add=True)
    mtime = models.DateTimeField(auto_now=True)
    name = models.CharField(max_length=64, null=True, blank=True)
    point = models.PointField(srid=4326, null=True, blank=True)
    img = models.CharField(max_length=128, null=True, blank=True)
    img_icon = models.CharField(max_length=128, null=True, blank=True)
    counter = models.IntegerField(default=0)
    link = models.CharField(max_length=128, null=True, blank=True)
    radius = models.SmallIntegerField(default=1500)
    active = models.BooleanField(default=True)
    city = models.ForeignKey(City, null=True, blank=True, on_delete=models.SET_NULL)
    once = models.BooleanField(default=False)
    ios = models.BooleanField(default=True)
    android = models.BooleanField(default=True)
    objects = GeoManager()

    def __str__(self):
        return u"%s" % (self.link)

    def as_dict(self):
        d = dict(id=self.id)
        if self.point:
            d['x'], d['y'] = self.point.x, self.point.y
        d["img"] = self.img
        if self.img == "https://bustime.loc/static/img/adgeo/baken_":
            d["img"] += "0"+str(random.randint(1,5))+".png"
        d["img_icon"] = self.img_icon
        d["link"] = self.link
        d["city_id"] = self.city_id
        d["radius"] = self.radius
        d["once"] = self.once
        d["ios"] = self.ios
        d["android"] = self.android
        return d


class PassengerStat(models.Model):
    ctime = models.DateTimeField(auto_now_add=True, db_index=True)
    ms_id = models.IntegerField(null=True, blank=True)
    us_id = models.IntegerField(null=True, blank=True)
    #city = models.ForeignKey(City, null=True, blank=True)
    city = models.SmallIntegerField(null=True, blank=True, db_index=True)
    lon = models.FloatField(null=True, blank=True)
    lat = models.FloatField(null=True, blank=True)
    psess = models.CharField(null=True, blank=True, max_length=8)
    bus_name = models.CharField(null=True, blank=True, max_length=7)
    nb_name = models.CharField(null=True, blank=True, max_length=32)
    nb_id = models.IntegerField(null=True, blank=True)
    os = models.SmallIntegerField(default=0)  # 1-android, 2-ios
    def __str__(self):
        return u"%s, %s, %s: %s" % (self.ctime, self.city, self.psess, self.os)


class Mapping(models.Model):
    ctime = models.DateTimeField(auto_now_add=True)
    mtime = models.DateTimeField(auto_now=True, null=True, blank=True)
    last_changed_by = models.ForeignKey(UserSettings, null=True, blank=True, on_delete=models.SET_NULL)
    city = models.ForeignKey(City, on_delete=models.SET_NULL, null=True, blank=True)
    place = models.ForeignKey(Place, on_delete=models.SET_NULL, null=True, blank=True)
    xeno_id = models.CharField(max_length=16, null=True, blank=True)
    gosnum = models.CharField(max_length=12, null=True, blank=True)
    bus = models.ForeignKey(Bus, null=True, blank=True, on_delete=models.SET_NULL)

    def save(self, *args, **kwargs):
        if self.place is None:
            self.place_id = self.city_id
        super(Mapping, self).save(*args, **kwargs)
        mapping_get(self.place, force=True)

    def __str__(self):
        return u"%s-%s" % (self.xeno_id, self.gosnum)

    class Meta:
        unique_together = ("city", "xeno_id")


class Plan(models.Model):
    ctime = models.DateTimeField(auto_now_add=True)
    mtime = models.DateTimeField(auto_now=True, null=True, blank=True)
    date = models.DateField(db_index=True)
    last_changed_by = models.ForeignKey(UserSettings, null=True, blank=True, on_delete=models.SET_NULL)
    xeno_id = models.CharField(max_length=16, null=True, blank=True)
    operator = models.SmallIntegerField(null=True, blank=True)
    gra = models.SmallIntegerField(null=True, blank=True)
    bus = models.ForeignKey(Bus, null=True, blank=True, on_delete=models.SET_NULL)

    def save(self, *args, **kwargs):
        super(Plan, self).save(*args, **kwargs)
        plan_get(self.bus.city, force=True)

    def __str__(self):
        return u"%s: %s-%s-%s" % (self.date, self.bus, self.gra, self.xeno_id)

    # class Meta:
    #     unique_together = ("date", "bus", "gra", "xeno_id")


class PollyCounter(models.Model):
    ctime = models.DateTimeField(auto_now_add=True)
    text = models.TextField()
    fname = models.TextField()
    chars = models.PositiveIntegerField()


class VoiceAnnouncer(models.Model):
    ctime = models.DateTimeField(auto_now_add=True)
    text = models.TextField(unique=True) # lowercase before!
    chars = models.PositiveIntegerField()
    exist = models.BooleanField(default=False)
    ama = models.BooleanField(default=False)
    ol = models.BooleanField(default=False)

    def __str__(self):
        return u"%s" % (self.text)

class Like(models.Model):
    ctime = models.DateTimeField(auto_now_add=True)
    mtime = models.DateTimeField(auto_now=True)
    us = models.ForeignKey(UserSettings, null=True, blank=True, on_delete=models.SET_NULL)
    ms = models.ForeignKey(MobileSettings, null=True, blank=True, on_delete=models.SET_NULL)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    like = models.SmallIntegerField(default=1)

    def get_likes(self, force=False):
        cc_key = "likes_%s_%s" % (self.content_type.model, self.object_id)
        l, d = rcache_get(cc_key, (None, None))
        if l == None or force:
            l, d = 0, 0
            for like in Like.objects.filter(content_type=self.content_type, object_id=self.object_id).values_list('like', flat=True):
                if like:
                    l+=1
                else:
                    d+=1
            rcache_set(cc_key, (l, d))
        return l,d

    def save(self, *args, **kwargs):
        super(Like, self).save(*args, **kwargs)
        self.get_likes(force=1)


class BusStopIcon(models.Model):
    vbusstop = models.ForeignKey(VBusStop, on_delete=models.CASCADE)
    icon = models.ForeignKey(BusStopIconImage, on_delete=models.CASCADE)


class Chat(models.Model):
    ctime = models.DateTimeField(auto_now_add=True, db_index=True)
    bus = models.ForeignKey(Bus, null=True, blank=True, db_index=True, on_delete=models.SET_NULL)
    us = models.ForeignKey(UserSettings, null=True, blank=True, on_delete=models.SET_NULL)
    ms = models.ForeignKey(MobileSettings, null=True, blank=True, on_delete=models.SET_NULL)
    color = models.CharField(max_length=6, null=True, blank=True)
    name = models.CharField(max_length=120)
    message = models.TextField(max_length=140)
    deleted = models.BooleanField(default=False, db_index=True)
    deleted_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    photo = models.CharField(max_length=255, null=True, blank=True)
    photo_thumbnail = models.CharField(max_length=255, null=True, blank=True)
    warnings = models.TextField(null=True, blank=True)
    warnings_count = models.SmallIntegerField(default=0)

    def __str__(self):
        return u"%s: %s" % (self.ctime, self.message)

    def save(self, *args, **kwargs):
        new_flag = False
        if not self.pk:
            new_flag = True
        super(Chat, self).save(*args, **kwargs)
        if not new_flag:
            if self.bus and self.bus.id:
                fill_chat_cache(self.bus.id, force=True)
                fill_chat_city_cache(self.bus.city_id, force=True)


class Metric(models.Model):
    date = models.DateField(null=True, blank=True, db_index=True)
    name = models.CharField(max_length=24, db_index=True)
    count = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ("date", "name")

    def __str__(self):
        return u"%s: %s %s" % (self.date, self.name, self.count)


class MetricTime(models.Model):
    date = models.DateTimeField(db_index=True)
    name = models.CharField(max_length=24, db_index=True)
    count = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ("date", "name")

    def __str__(self):
        return u"%s: %s %s" % (self.date, self.name, self.count)


class WorldBorder(models.Model):
    name = models.CharField(max_length=50)
    area = models.IntegerField()
    pop2005 = models.IntegerField('Population 2005')
    fips = models.CharField('FIPS Code', max_length=2)
    iso2 = models.CharField('2 Digit ISO', max_length=2)
    iso3 = models.CharField('3 Digit ISO', max_length=3)
    un = models.IntegerField('United Nations Code')
    region = models.IntegerField('Region Code')
    subregion = models.IntegerField('Sub-Region Code')
    lon = models.FloatField()
    lat = models.FloatField()

    # GeoDjango-specific: a geometry field (MultiPolygonField)
    mpoly = models.MultiPolygonField(srid=4326, null=True, blank=True)

    # Returns the string representation of the model.
    def __str__(self):
        return self.name


def metric(name):
    # d = datetime.datetime.utcnow().date()
    d = datetime.datetime.now().date()

    # sweet cache
    cc_key = "metric_%s_%s" % (d, name)
    cc_key_save = "%s_save" % cc_key

    count_ = REDIS_W.incr(cc_key)
    if count_ == 1:
        REDIS_W.expire(cc_key, 60*60*24+60) # so funny
        REDIS_W.sadd("metrics_%s" % d, cc_key)
        REDIS_W.expire("metrics_%s" % d, 60*60*24+60)

    save = REDIS.get(cc_key_save)
    if not save:
        m, cr = Metric.objects.get_or_create(date=d, name=name)
        if not cr:
            m.count = count_
            m.save()
        save = REDIS_W.set(cc_key_save, 1, 60*10) # save every 10 mins
    return count_


def backoffice_statlos(data=None):
    cc_key = "backoffice_stats"
    if data:
        cache.set(cc_key, data)
    else:
        return cache.get(cc_key, {})


def premium_activate(us, key=None):
    if key == "premium":
        us.premium = True
        us.pro_demo = False
        us.show_gosnum = True
        us.p2p_video = True
        us.save()
    elif key == "standard":
        us.premium = True
        us.pro_demo = False
        us.save()
    return True


def premium_deactivate(us):
    us.premium = False
    us.show_gosnum = False
    us.p2p_video = False
    us.save()
    return True


def pickle_dumps(x):
    return pickle.dumps(x, protocol=pickle.HIGHEST_PROTOCOL)


def rcache_get(key, *args):
    pdata = REDIS.get(key)
    if pdata:
        try:
            pdata = pickle.loads(pdata)
        except:
            if args:  # backup
                pdata = args[0]
            else:
                pdata = None
    elif args:
        pdata = args[0]
    return pdata

def rcache_mget(keys, sformat=None):
    pdata = []
    if keys:
        for p in REDIS.mget(keys):
            if p:
                if sformat == "json":
                    p = json.loads(p)
                else:
                    p = pickle.loads(p)
            pdata.append(p)
    return pdata


def rcache_set(key, value, *args):
    value = pickle_dumps(value)
    if args:
        REDIS_W.set(key, value, args[0])
    else:
        REDIS_W.set(key, value, 86400) # 60*60*24


def log_message(message, ttype=None, user=None, city=None, place=None, ms=None):
    if ttype == "update_lib" or ttype == "error_update":
        # micro cache to save last couple lines for display in web status page
        if place:
            city = place
        cc_key = "log_%s_%s" % (ttype, city.id)
        msgs = rcache_get(cc_key, [])
        l = {"message":message, "date":str(city.now)[:-4]}  # .split(".")[0]
        msgs.append(l)
        rcache_set(cc_key, msgs[-2:], 60*60*24)
    else:
        if type(user) == UserSettings:
            if place:
                Log.objects.create(message=message, ttype=ttype, user=user, place=place, ms=None)
            else:
                Log.objects.create(message=message, ttype=ttype, user=user, city=city, ms=None)

        elif type(user) == MobileSettings:
            if place:
                Log.objects.create(message=message, ttype=ttype, user=None, place=place, ms=user)
            else:
                Log.objects.create(message=message, ttype=ttype, user=None, city=city, ms=user)
        else:
            if place:
                Log.objects.create(message=message, ttype=ttype[:16], user=None, place=place)
            else:
                Log.objects.create(message=message, ttype=ttype[:16], user=None, city=city)
    return True


def wilson_rating(pos, n, human=False):
    """
    Lower bound of Wilson score confidence interval for a Bernoulli parameter
    pos is the number of positive votes, n is the total number of votes.
    https://gist.github.com/honza/5050540
    http://www.evanmiller.org/how-not-to-sort-by-average-rating.html
    http://amix.dk/blog/post/19588

    wilson_rating(600, 1000)
    wilson_rating(5500, 10000)
    """
    if not n:  # 0 if no votes
        return 0
    z = 1.44  # 1.44 = 85%, 1.96 = 95%
    phat = 1.0 * pos / n
    rating = (phat + z*z/(2*n) - z * math.sqrt((phat*(1-phat)+z*z/(4*n))/n))/(1+z*z/n)
    if human:
        rating = round(rating * 5, 3)
    return rating


def add_stop_geospatial(stop):
    lng_range = (-180, 180)
    lat_range = (-85.05112878, 85.05112878)
    if lng_range[0] <= stop.point.x <= lng_range[1] and lat_range[0] <= stop.point.y <= lat_range[1]:
        REDIS_W.geoadd("geo_stops", (stop.point.x, stop.point.y, stop.id))
        return True
    return False


def fill_stops_geospatial():
    tic = time.perf_counter()
    pipe = REDIS_W.pipeline()
    lng_range = (-180, 180)
    lat_range = (-85.05112878, 85.05112878)
    with connection.cursor() as cursor:
        cursor.execute("SELECT ST_X(bn.point) as x, ST_Y(bn.point) as y, bn.id "
                       "FROM bustime_nbusstop as bn")
        stops = [stop for stop in cursor.fetchall()
                 if lng_range[0] <= stop[0] <= lng_range[1]
                 and lat_range[0] <= stop[1] <= lat_range[1]]
    for stop in stops:
        pipe.geoadd("geo_stops", stop)
    pipe.execute()
    REDIS_W.expire("geo_stops", 60*60*24)
    # print("EXIT")
    # success = 0
    # failed = 0
    # for stop in stops:
    #     print(f"stop geospatial {stop}")
    #     try:
    #         REDIS.geoadd("geo_stops", stop)
    #         success += 1
    #     except Exception as e:
    #         print(traceback.format_exception(e))
    #         failed += 1
    #         sys.exit()
    # toc = time.perf_counter()
    # print(f"Stops points count: {success}. Loading time is {toc - tic:0.4f} sec")
    # tic = time.perf_counter()
    # REDISU.georadius(name='stops', latitude=56.01206, longitude=92.85203, radius=1000, unit='km')
    toc = time.perf_counter()
    print(f"Stops coords have taken by time: {toc - tic:0.4f} sec")


# https://koalatea.io/python-redis-geo/
def fill_places_geospatial(force=False, expire=3600, DEBUG=False):
    cc_key = "geo_places"
    if DEBUG:
        tic = time.perf_counter()

    if force or not REDIS_W.exists(cc_key):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT x, y, id
                FROM (
                    SELECT ST_X(bp.point) as x, ST_Y(bp.point) as y, bp.id
                    FROM bustime_place bp
                ) a
                WHERE x BETWEEN -180.0 AND 180.0
                AND y BETWEEN -86.0 AND 86.0
                """
            )

            pipe = REDIS_W.pipeline()
            for place in cursor:
                pipe.geoadd(cc_key, place)
            pipe.execute()
            REDIS_W.expire(cc_key, expire)
        # with connection.cursor()

    if DEBUG:
        toc = time.perf_counter()
        print(f"Places coords have taken by time: {toc - tic:0.4f} sec")

    return REDIS_W.zcard(cc_key)
# fill_places_geospatial


def fill_routes_data():
    for route in Route.objects.all():
        ROUTE_BY_ID[route.id] = vars(route)


def fill_bus_stata():
    """Fill caches to get fast access about bus info."""
    global BUS_BY_ID
    global BUS_BY_NAME
    global BUS_BY_ID_UPDATE
    qs = Bus.objects.filter().select_related().annotate(places_all=ArrayAgg('places__id'))
    BUS_BY_ID.update({bus.id: bus for bus in qs})
    BUS_BY_NAME.update({f"ts_{pid}_{ttype}_{name}": bid \
        for pid, bid, ttype, name in Bus.objects.filter(places__isnull=False, active=True) \
            .values_list("places", "id", "ttype", "name").order_by("places", "ttype")})
    BUS_BY_ID_UPDATE = datetime.datetime.now()


def bus_get(bus_id):
    # get bus quick by using in-memory cache
    # what about force update?
    global BUS_BY_ID
    global BUS_BY_ID_UPDATE
    # cache is outdated in 1 hour, just in case
    if not BUS_BY_ID_UPDATE or BUS_BY_ID_UPDATE < datetime.datetime.now() - datetime.timedelta(minutes=60):
        fill_bus_stata()
    bus = BUS_BY_ID.get(bus_id)
    if not bus and Bus.objects.filter(id=bus_id).exists(): # is it new one?
        fill_bus_stata()
        bus = BUS_BY_ID.get(bus_id)
    return bus

# def route_get(route_id):
#     cc_key = "route__%s" % route_id
#     route = rcache_get(cc_key, None)
#     if route == None:
#         try:
#             route = Route.objects.get(id=route_id)
#             rcache_set(cc_key, route)
#         except:
#             pass # no route no probs
#     return route


def chat_format_msg(chat, extra={}, lang="ru"):
    ctime = chat.ctime
    if chat.bus:
        place = chat.bus.places.first()
        if not place: return ""
        ctime += datetime.timedelta(hours=place.timediffk)
    ctime = lotime(ctime, lang=lang)
    msg = {"id": chat.id, "name": chat.name,
           "message": chat.message, "ctime": ctime, "color": chat.color}
    if extra:
        msg.update(extra)
    if chat.photo:
        msg['photo'] = chat.photo
        msg['photo_thumbnail'] = chat.photo_thumbnail
    if chat.ms_id:
        msg["ms_id"] = chat.ms_id
    elif chat.us_id:
        msg["us_id"] = chat.us_id
    return msg


def routes_get(bus_id, direction=None, force=False):
    cc_key = "busstops_%s" % bus_id
    if not force:
        routes = rcache_get(cc_key, None)
    if force or not routes:
        routes = list(Route.objects.filter(bus_id=bus_id).order_by(
            'direction', 'order').select_related('busstop'))
        rcache_set(cc_key, routes, 60 * 60 * 24)
    if direction != None:
        nl = []
        for r in routes:
            if r.direction == direction:
                nl.append(r)
        routes = nl
    return routes


def city_routes_get(city, force=False):
    cc_key = "city_routes_%s" % city.id
    city_routes = rcache_get(cc_key, {})
    if not city_routes or force:
        city_routes = {}
        buses = buses_get(city)
        routes = Route.objects.filter(bus__in=buses).order_by('bus', 'direction', 'order').select_related('busstop')
        routes = routes.values_list('id', 'bus_id', 'busstop_id', 'endpoint', 'direction', 'order',
                                    'busstop__moveto', 'busstop__tram_only')

        for r in routes:
            rd = {"id": r[0], "bus_id": r[1], "busstop_id": r[2], "endpoint": r[3], "direction": r[4], 'order': r[5],
                  'moveto': r[6], 'tram_only': r[7]}
            if not city_routes.get(rd['bus_id']):
                city_routes[rd['bus_id']] = []
            city_routes[rd['bus_id']].append(rd)
        rcache_set(cc_key, city_routes, 60 * 60 * 24)
    return city_routes


def city_routes_get_turbo(bus_id, force=False):
    cc_key = "turbo_route_%s" % bus_id
    city_routes = rcache_get(cc_key, [])
    if not city_routes or force:
        city_routes = []
        routes = Route.objects.filter(bus=bus_id).order_by('direction', 'order').select_related('busstop')
        routes = routes.values_list('id', 'bus_id', 'busstop_id', 'endpoint', 'direction', 'order',
                                    'busstop__moveto', 'busstop__tram_only', 'busstop__timezone')

        for r in routes:
            city_routes.append({"id": r[0], "bus_id": r[1], "busstop_id": r[2], "endpoint": r[3], "direction": r[4], 'order': r[5],
                  'moveto': r[6], 'tram_only': r[7], 'timezone': r[8]})
        rcache_set(cc_key, city_routes, 60 * 60 * 24)
    return city_routes


def rel_buses_get(bus_id, force=False):
    cc_key = "rel_bus__%s" % bus_id
    bids = rcache_get(cc_key)
    if not bids or force:
        pipe = REDIS_W.pipeline()
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT DISTINCT bus_id FROM bustime_route br WHERE busstop_id IN (
            	    SELECT busstop_id FROM bustime_route WHERE bus_id=%s
                )
            """, (bus_id,))
            bids = [bid for bid, in cursor.fetchall()]
        pipe.set(cc_key, pickle_dumps(bids), 86400)
        # for bid in bids:
        #     rel_bids = [bus_id for bus_id in bids if bus_id != bid]
        #     rel_bids.append(bus_id)
        #     pipe.set("rel_bus__%s" % bid, pickle_dumps(rel_bids), 86400)
        # pipe.execute()
    return bids


def stop_buses_get(sids, force=False) -> dict[int, list[tuple[int, int, str]]]:
    '''
    Get stop ids with corresponds bus informaion.
    ``sids`` - List of ``stop_id``
    ``force`` - Forcebly invalidate by ``sids``
    Return dict with ``stop_id`` as ``key`` and list of tuples ``(bus_id, ttype, name)`` as ``value``
    '''
    def invalidate(sids=None):
        '''Invalidate cache for corresponds stop ids.'''
        buses_by_stop = defaultdict(list)
        rids = Route.objects.filter(bus__active=True, busstop_id__in=sids).values_list('busstop_id', 'bus_id', 'bus__ttype', 'bus__name')
        for sid, bid, ttype, name in rids:
            buses_by_stop[sid].append((bid, ttype, name))
        for key, values in buses_by_stop.items():
            pipe.sadd(f"nstop_buses__{key}", *itertools.starmap(lambda bid, ttype, name: f"{bid}__{ttype}__{name}", values))
            pipe.expire(f"nstop_buses__{key}", 60*60*24)
        pipe.execute()
        return buses_by_stop

    pipe = REDIS_W.pipeline()
    rpipe = REDIS.pipeline()
    if not force:
        _ = [rpipe.smembers(f'nstop_buses__{sid}') for sid in sids]
        # sids_with_bids = dict(zip(sids, ([[(int(data[0]), int(data[1]), data[2]) for info in infos if (data := info.decode().split('__'))] for infos in rpipe.execute()])))
        all_infos = (infos for infos in rpipe.execute())
        data = ([(int(data[0]), int(data[1]), data[2]) for info in infos if (data := info.decode().split('__'))] for infos in all_infos)
        sids_with_bids = dict(zip(sids, data))

        empty_sids = [sid for sid, bids in sids_with_bids.items() if not bids]
        if empty_sids:
            sids_with_bids.update(invalidate(empty_sids))
    else:
        sids_with_bids = invalidate(sids)
    return sids_with_bids


def buses_get(place, force=False, as_dict=False):
    cc_key = "allbuses_%d" % place.id
    cc_key_as_dict = "allbuses_%d_as_dict" % place.id
    if as_dict:
        buses = rcache_get(cc_key_as_dict)
    else:
        buses = rcache_get(cc_key)
    if not buses or force:
        REDIS_W.delete(f"turbo_home__{place.slug}")

        if Bus.objects.filter(active=True, city_id=1, places__id=place.id).count() > 0 and place.id != 167:
            # в Талине я вручную загрузил маршруты и почему они должны скрыться, если из Германии подгрузился автобус который там останавливается?
            # gtfs - маршруты у которых есть дубликаты в городе Zero (1) и конкретных городах (например, 242 215)
            city_filter = 'and b.city_id=1'
        else:
            city_filter = ''

        query = """
            -- сортировка
            select id, "name", distance, travel_time, description, "order", murl, ttype, napr_a, napr_b, active, route_dir0, route_dir1, city_id, xeno_id, discount, tt_xeno_reversed, slug, only_holiday, only_season, only_rush_hour, only_special, only_working, inter_stops, ctime, mtime, price, provider_id, tt_start, tt_start_holiday, distance0, distance1, "interval", payment_method, routes, inter_stops_fixed, onroute, onroute_weekend, turbo
                ,coalesce(ascii(substring(a.n, '^\D')), 0) n1   -- буква перед номером
                ,coalesce(nullif(regexp_replace(a.n, '\D', '', 'g'), ''), '0')::numeric nn  -- номер
                ,coalesce(ascii(substring(a.n, '\d+(\D)')), 0) n2   -- буква после номера
                ,case when substring(a.n, '[0-9]+') is null then 1 else 0 end n3 -- 1 если нет номера, иначе 0
            from (
                -- подготовка полей
                select b.*,
                    upper(regexp_replace(b.name, '[ \-\(\)\[\]\{\}\*\+/\\\]', '', 'g')) n -- имя без мусорных символов
                from bustime_bus b
                inner join bustime_bus_places p on b.id = p.bus_id
                where b.active
                and p.place_id = %s city_filter
            ) a
            -- порядок маршрутов в выборке:
            -- сначала по типу (автобус/троллейбус...)
            -- потом по номеру или номер и надпись по алфавиту
            -- потом с надписью перед номером - по алфавиту и по номеру
            -- последние без номера по алфавиту
            order by ttype, n3, n1, nn, n2
        """.replace("city_filter", city_filter)

        qs = Bus.objects.raw(query, [place.id])
        buses = list(qs)
        rcache_set(cc_key, buses)

        buses_dict = []
        for b in qs:
            bus = {}
            bus["id"] = b.id
            bus["ttype"] = b.ttype
            bus["get_absolute_url"] = b.get_absolute_url()
            bus["discount"] = b.discount
            bus["name"] = b.name
            bus["napr_a"] = b.napr_a
            bus["slug"] = b.slug
            buses_dict.append(bus)
        rcache_set(cc_key_as_dict, buses_dict)

        if as_dict:
            buses = buses_dict
    # if not buses or force

    return buses
# buses_get


def places_filtered(force=False):
    cc_key = "places_filtered"
    places = rcache_get(cc_key, {})
    if not places or force:
        places_exclude = get_setting("places_exclude") or []
        # Выбираем места, где у автобусов один place - они должны войти обязательно
        buses_with_one_place = Bus.objects.annotate(place_count=Count('places')).filter(place_count=1)
        places = Place.objects.filter(name__isnull=False, bus__in=buses_with_one_place, bus__active=True).exclude(slug__in=places_exclude).distinct().values_list("id", flat=True)

        # Выбираем другие маршруты и места так, чтобы исключить уже перечисленные
        # (если в bus.places есть уже перечилсненный выше город, то не добавлять его)
        buses_other = Bus.objects.exclude(id__in=buses_with_one_place).exclude(places__in=places)
        other_places = Place.objects.filter(name_en__isnull=False, bus__in=buses_other, bus__active=True).exclude(slug__in=places_exclude).distinct().values_list("id", flat=True)

        places = list(places) +list(other_places)
        rcache_set(cc_key, places, 60*60)
    return places



def places_get(lang, force=False, as_list=False, country=None):
    cc_key = "allplaces_{}".format(lang)
    if as_list:
        cc_key += "_list"
    if country:
        cc_key += "_{}".format(country)
    places = rcache_get(cc_key, {})
    if not places or force:
        """
        в результате имеем кучу (allplaces_ru, allplaces_en, allplaces_pt,......) закешированных
        совершенно одинаковых наборов places, кажды из 2132 строк Place
        """
        # don't use places_filtered() to be sure every place is in place
        # не использовать name__isnull=False ибо языковые поля часто пустые и строки просто выпадают
        qs = Place.objects.filter(bus__isnull=False, name_en__isnull=False).distinct().order_by("country_code", "name")
        if country:
            qs = qs.filter(country_code=country)
        if as_list:
            places = list(qs)
        else:
            places = {p.id: p for p in qs}
        rcache_set(cc_key, places)
    return places


def cities_get(force=False, as_list=False, country=None):
    # country = "ru"
    cc_key = "allcities"
    if as_list:
        cc_key += "_list"
    if country:
        cc_key += "_%s" % country
    cities = rcache_get(cc_key, {})
    if not cities or force:
        qs = City.objects.filter(active=True).order_by("country", "name")
        if country:
            qs = qs.filter(country__code=country)
        if as_list:
            cities = list(qs)
        else:
            cities = {}
            for c in qs.select_related():
                cities[c.id] = c
        rcache_set(cc_key, cities)
    return cities


def stops_get(city, force=False):
    cc_key = "allstops_%s" % city.id
    STOPS = rcache_get(cc_key, {})
    if not STOPS or force:
        STOPS = {}
        buses = buses_get(city)
        for r in Route.objects.filter(bus__in=buses):
            if STOPS.get(r.bus_id):
                STOPS[r.bus_id].append(r.busstop_id)
            else:
                STOPS[r.bus_id] = [r.busstop_id]
        rcache_set(cc_key, STOPS, 60 * 60 * 24)
    return STOPS


def us_get(us_id, force=False):
    cc_key = "us_%s" % (us_id)
    us = None

    if not force:
        try:
            us = rcache_get(cc_key)
        except:
            us = None

    if force or us is None:
        try:
            us = UserSettings.objects.select_related('user').get(id=int(us_id))
            rcache_set(cc_key, us, 60*60*24*2)
        except:
            us = None

    return us


def ms_get(ms_id, force=False):
    cc_key = "ms_%s" % (ms_id)
    ms = None

    if not force:
        try:
            ms = rcache_get(cc_key)
            z = ms.orator
        except:
            ms = None

    if force or ms is None:
        try:
            ms = MobileSettings.objects.get(id=int(ms_id))
            rcache_set(cc_key, ms, 60*60*24*2)
        except:
            ms = None
    return ms


def tcard_get(tcard, provider=None):
    try:
        tcard = Tcard.objects.filter(num=tcard, provider=provider)[0]
        if not provider:
            return tcard
        else:
            tcard_update(tcard, provider)
    except:
        tcard = None
    return tcard


def get_bus_by_point(x, y, name, ttype, uniqueid=None, *, bus_or_bus_taxi=False, bus_or_intercity=False, ignore_nf=False):
    '''Find a bus by it's name and coordinates.'''

    def find_by_radius(radius):
        '''Try to find a bus within some area by coordinates and radius.'''
        sids = find_stop_ids_within(x=x, y=y, radius=radius)
        if not sids:
            return None
        bus_infos: list[tuple[int, int, str]] = list(itertools.chain.from_iterable(stop_buses_get(sids).values()))
        bids = (info[0] for info in bus_infos if info[1] == ttype and info[2] == name)
        if bid := next(bids, None):
            return bid
        if bus_or_bus_taxi:
            bids = (info[0] for info in bus_infos if info[1] == TType.SHUTTLE_BUS and info[2] == name)
            if bid := next(bids, None):
                return bid
        if bus_or_intercity:
            bids = (info[0] for info in bus_infos if info[1] == TType.INTERCITY and info[2] == name)
            if bid := next(bids, None):
                return bid
        return None

    if not name:
        return False
    cc_key = f"bus_{name}__{ttype}__{uniqueid}" if uniqueid else None
    bid = REDIS.get(cc_key) if uniqueid else None
    if not bid:
        radius = 1000
        for _ in range(5):
            bus = find_by_radius(radius)
            if not bus:
                radius *= 3
            else:
                if uniqueid:
                    REDIS_W.set(cc_key, int(bus), ex=datetime.timedelta(minutes=15))
                return bus
        if not bus:
            if uniqueid:
                REDIS_W.set(cc_key, -1, ex=datetime.timedelta(minutes=60))
                exists = False
                # average length of route is about 25 km
                for n in REDIS_W.georadius("not_found", radius=25, unit='km', longitude=x, latitude=y):
                    # compare name and ttype to not duplicate others of the same absent route
                    n, tt, _ = n.decode().replace("bus_", '').split("__", 3)
                    if name == n and str(ttype) == tt:
                        exists = True
                if not exists:
                    REDIS_W.geoadd("not_found", (x, y, cc_key))
            if ignore_nf:
                return False
            raise BusNotFoundException(f"Bus with name: {name}, type: {ttype} not found at point[{x}, {y}]")
    else:
        if int(bid) == -1:
            return False
        return int(bid)
    return False


def get_bus_by_name(place: City | Place, name, ttype, bus_or_bus_taxi=False, bus_or_intercity=False, ignore_nf=False):
    # warn("Deprecated method. Use get_bus_by_point instead", DeprecationWarning, stacklevel=2)
    ttype_orig = ttype
    if not BUS_BY_NAME:
        fill_bus_stata()
    cc_key = u"ts_%s_%s_%s" % (place.id, ttype, force_str(name))

    bus_id = BUS_BY_NAME.get(cc_key)
    if not bus_id and bus_or_bus_taxi:
        if ttype == 0:
            ttype = 3
        elif ttype == 3:
            ttype = 0
        cc_key = u"ts_%s_%s_%s" % (place.id, ttype, force_str(name))
        bus_id = BUS_BY_NAME.get(cc_key)

    if not bus_id and bus_or_intercity:
        if ttype == 0 or ttype == 3:
            ttype = 5
        elif ttype == 5:
            ttype = 0
        cc_key = u"ts_%s_%s_%s" % (place.id, ttype, force_str(name))
        bus_id = BUS_BY_NAME.get(cc_key)

    if not bus_id:
        if ignore_nf:
            return False
        cc_key = u"ts_%s_%s_%s" % (place.id, ttype_orig, force_str(name))
        notified = rcache_get(cc_key+"_nf")
        if not notified:
            rcache_set(cc_key+"_nf", 1, 60*60*24)
            if isinstance(place, City):
                log_message("not found: name=%s, type=%s" % (name, ttype_orig), ttype="get_bus_by_name", city=place)
            else:
                log_message("not found: name=%s, type=%s" % (name, ttype_orig), ttype="get_bus_by_name", place=place)
        bus = False
    else:
        bus = bus_get(bus_id)
    return bus


def specialicons_cget(as_dict=False, force=False, place_id=None):
    cc_key = "SpecialIcons"
    if place_id:
        cc_key += "_%s" % place_id
    specialicons = rcache_get(cc_key)
    if not specialicons or force:
        #qs = SpecialIcon.objects.filter(active=True)
        # active AND gosnum IS NOT NULL AND gosnum != '' AND '/static/' IN img
        qs = SpecialIcon.objects.filter(active=True) \
                .exclude(Q(gosnum__isnull=True) | Q(gosnum__exact='')) \
                .filter(Q(img__contains='/static/'))

        if place_id:
            qs = qs.filter(place_id=place_id)
        specialicons = list(qs)
        rcache_set(cc_key, specialicons, 60*60*24)
    if as_dict:
        return {s.gosnum: s.img for s in specialicons}
    return specialicons


def weekday_dicto(now):
    d = {now.strftime('%a').lower(): True}
    return d


def is_holiday(now):
    day_of_week = now.strftime('%a').lower()
    # depends on country?
    if day_of_week in ["sat", "sun"]:
        return True
    return False


def get_transaction(settings):
    if not settings:
        return None
    user = settings.user
    if not user:
        return None
    groups = get_groups(user)
    class A:  # just to hold some info
        pass
    vtr = A()
    vtr.bonus = False
    vtr.vip = False
    vtr.alex = False

    if 'editor' in groups or user.is_superuser:
        vtr.key = 'premium'
        vtr.end_time = datetime.datetime.now() + datetime.timedelta(days=90)
    if 'vip' in groups or user.is_superuser:
        vtr.vip = True
    if 'alex' in groups:
        vtr.alex = True

    if getattr(vtr, 'key', None):
        return vtr
    else:
        return None


def get_groups(user, force=False):
    cc_key = 'groups__%s' % user.id
    groups = rcache_get(cc_key)
    if groups == None or force:
        groups = list(user.groups.values_list('name', flat=True))
        rcache_set(cc_key, groups, 60*60*24)
    return groups


def get_busstop_points(city, force=False):
    cc_key = "busstops_points_%s" % city.id
    busstops_points = rcache_get(cc_key)
    if force or not busstops_points:
        busstops = NBusStop.objects.filter(point__isnull=False,
                                        id__in=Subquery(
                                            Route.objects.filter(
                                                bus__in=Subquery(
                                                    Bus.objects.filter(places__id=city.id, active=True).values('id')
                                                )
                                            ).values('busstop_id').distinct('busstop_id')
                                        )
                                    ).values('id', 'point')
        busstops_points = {stop['id']: (stop['point'].x, stop['point'].y) for stop in busstops}
        rcache_set(cc_key, busstops_points)
    if city.id == 27: # железногорск intercity workaround
        busstops_points.update(get_busstop_points(CITY_MAP[3]))
    return busstops_points


def dd_stops_get(bus_id, force=False):
    cc_key = u"dd_stops_get__%s" % (bus_id)
    stops = rcache_get(cc_key, {})
    if force or not stops:
        with connection.cursor() as cursor:
            sql_cmd = """SELECT "bustime_nbusstop"."id",
                           ST_X("bustime_nbusstop"."point") as x,
                           ST_Y("bustime_nbusstop"."point") as y FROM
                           "bustime_nbusstop" INNER JOIN "bustime_route"
                           ON ("bustime_nbusstop"."id" =
                           "bustime_route"."busstop_id") WHERE
                           "bustime_route"."bus_id" = %s"""
            cursor.execute(sql_cmd, (bus_id,))
            stops = {stop['id']: (stop['x'], stop['y']) for stop in dictfetchall(cursor)}
            rcache_set(cc_key, stops)
    return stops


def get_busstop_points_turbo(bus_id, force=False):
    cc_key = "turbo_busstops_points_%s" % bus_id
    busstops_points = rcache_get(cc_key)
    if force or not busstops_points:
        busstops_points = {}
        routes = Route.objects.filter(bus=bus_id).order_by('direction', 'order').select_related('busstop')
        for route in routes:
            if route.busstop and route.busstop.point:
                busstops_points[route.busstop_id] = (route.busstop.point.x, route.busstop.point.y)
        rcache_set(cc_key, busstops_points)
    return busstops_points


def get_busstops(force=False):
    cc_key = "allbusstops"
    busstops = rcache_get(cc_key)
    if force or not busstops:
        busstops = {}
        for stop in NBusStop.objects.iterator():
            busstops[stop.id] = json.dumps(stop)
        rcache_set(cc_key, busstops)
    return busstops


def mapping_get(place: City | Place, force=False):
    cc_key = "Mapping_%s" % place.id
    mapping = rcache_get(cc_key)
    if not mapping or force:
        mapping = Mapping.objects.filter(place_id=place.id).order_by("bus", "xeno_id").select_related()
        rcache_set(cc_key, mapping)
    return mapping


def plan_get(city, force=False):
    cc_key = "Plan_%s" % city.id
    plan = rcache_get(cc_key)
    if not plan or force:
        plan = list(Plan.objects.filter(bus__city=city).select_related())
        rcache_set(cc_key, plan)
    return plan


def get_detector_data(city):
    DD = {}
    ROUTES, ROUTES_NG, R = {}, {}, {}
    all_routes = Route.objects.filter(bus__city=city).select_related('busstop')
    all_routes = all_routes.order_by('bus', 'direction', 'order')
    for r in all_routes:
        R[r.id] = r
        if ROUTES.get(r.bus_id):
            ROUTES[r.bus_id].append(r)
        else:
            ROUTES[r.bus_id] = [r]

        if not ROUTES_NG.get(r.bus_id):
            ROUTES_NG[r.bus_id] = {0: nx.DiGraph(), 1: nx.DiGraph()}
            buf = None
        if buf and r.direction in [0, 1]:
            ROUTES_NG[r.bus_id][r.direction].add_edge(buf.id, r.id)
        buf = r
    DD['BUSSTOPS_POINTS'] = get_busstop_points(city)
    DD['R'] = R
    DD['ROUTES'] = ROUTES
    DD['ROUTES_NG'] = ROUTES_NG
    return DD


def vam_pub(uniqueid, data):
    import random
    counter = itertools.cycle(random.sample(list(range(0, 10)), 10))

    process_count = 1
    code = sum([ord(ch) for ch in uniqueid])
    mill_id = code % process_count
    REDIS_W.publish("vam_{}".format(mill_id), data)


def sio_pub(chan, data, pipe=None):
    uid = "emitter"
    packet = {'nsp': '/', 'data': [chan, data], 'type': 2}
    extra = {'flags': {}, 'rooms': [chan]}
    if pipe:
        dst = pipe
    else:
        dst = REDIS_IO
    # print("SIO_PUB", chan, data)
    dst.publish('socket.io#/#%s#' % chan, msgpack.packb([uid, packet, extra]))

    # Python Socket.IO Not needed
    # event = next(iter(data.keys()), None)
    # pkt = {"method": "emit", "event": event, "data": data, "namespace": "/", "room": chan}
    # dst.publish("socketio", json.dumps(pkt))
    return True


def wsocket_cmd(cmd, params, us_id=None, ms_id=None, channel=None):
    serialized = {"us_cmd": cmd, "params": params}
    if us_id:
        ch = "ru.bustime.us__%s" % us_id
    elif ms_id:
        ch = "ru.bustime.ms__%s" % ms_id
    elif channel:
        ch = "ru.bustime.%s" % channel

    sio_pub(ch, serialized)

def weather_detect(city, wind=False, weather=None):
    # convert plenty of weather conditions to the supported ones
    weather_, wind_ = "", 0
    if city:
        if not weather:
            weather = rcache_get("weather__%s" % city.id, {})
        if not weather:
            z = "clear"
        else:
            z = weather["weather"][0]["description"].lower()

        if "overcast" in z:
            weather_ = "dark_clouds"
        elif "rain" in z or "drizzle" in z:
            weather_ = "rain"
        elif "snow" in z:
            weather_ = "snow"
        elif "ice" in z:
            weather_ = "ice"
        elif "cloudy" in z or "clouds" in z:
            weather_ = "clouds"
        elif z in ["clear", "clear sky"]:
            weather_ = "clear"
        elif z in ["fog", "haze", "mist"]:
            weather_ = "fog"
        else:
            # fall back to https://openweathermap.org/weather-conditions
            weather_ = z

        if wind:
            wind_ = weather.get('wind', {})
            wind_ = wind_.get('speed', 0)
            wind_ = wind_ * 3.6 # mp/h to km/h
            return weather_, wind_

    return weather_



def refresh_temperature(place, lang='en'):
    if place and settings.OPENWEATHERMAP_KEY:
        avg_temp_key = "bustime__avg_temp_%s" % place.id
        coords = place.point.tuple
        request_url = f"https://api.openweathermap.org/data/2.5/weather?lon={coords[0]}&lat={coords[1]}&appid={settings.OPENWEATHERMAP_KEY}&units=metric&lang={lang}"
        try:
            r = requests.get(request_url, timeout=5)
            w = r.json()
        except:
            return 0
        if not w.get("id"):
            print('refresh_temperature json/id error:', j)
        rcache_set("weather__%s" % place.id, w, 60*60*4)
        temp = int(w['main']['temp'])
        weather = weather_detect(place, weather=w)
        wsocket_cmd('weather', {"temp": temp, 'weather': weather}, channel="city__%s" % place.id)
        rcache_set(avg_temp_key, temp, 60 * 60 * 4)
        if not place.weather and w.get("id"):
            place.weather = w["id"]
            place.save()
    else:
        temp = 0
    return temp


def get_avg_temp(city):
    warn("Deprecated method. Use avg_temp instead", DeprecationWarning, stacklevel=2)
    cc_key = "bustime__avg_temp_%s" % city.id
    return rcache_get(cc_key, 0)


def avg_temp(place):
    if place:
        cc_key = "bustime__avg_temp_%s" % place.id
        avg_temp = rcache_get(cc_key, 0)
    else:
        avg_temp = 0
    return avg_temp


def determine_bs_icon(name):
    n = name.lower()
    if u'завод' in n or u'фабрика' in n:
        z = 'завод'
    elif u'больница' in n or u'госпиталь' in n or \
         u'поликлиника' in n or u'аптека' in n:
        z = 'больница'
    elif u'трц' in n or u'магазин' in n \
            or u'универмаг' in n:
        z = 'магазин'
    elif u'торговый' in n:
        z = 'шопинг'
    elif u'ж/д' in n:
        z = 'ж/д вокзал'
    elif u'музей' in n or u'дк ' in n or u'дом ' in n or u'театр ' in n:
        z = 'музей'
    elif u'пл.' in n or u'площадь' in n:
        z = 'деревья'
    elif u'пожар' in n:
        z = 'гидрант'
    elif u'азс' in n:
        z = 'топливо'
    elif u'сад ' in n or u'сады' in n:
        z = 'деревья'
    elif u'рынок'in n:
        z = 'киоск с едой'
    elif u'школа'in n:
        z = 'светофоры'
    elif u'гостиница' in n or u'общежитие' in n:
        z = 'хостел'
    elif u'кафе' in n or u'ресторан' in n:
        z = 'кафе'
    elif u'парк' in n:
        z = 'парк отдыха'
    elif u'столовая' in n:
        z = 'еда'
    elif u'атс ' in n:
        z = 'телефон'
    elif u'стадион' in n:
        z = 'билет'
    elif u'ж/к' in n or u'микрорайон' in n:
        z = 'здания'
    else:
        z = 'остановка'
    return BusStopIconImage.objects.get(name=z)
############################

def bus_last_f(bus, raw=False, mobile=False, force=False, mode=0):
    if not bus:
        return {}

    place = bus.places.order_by("-population").first()
    serialized = {}
    first_last = {}
    if place and is_holiday(place.now):
        stimes = bus.tt_start_holiday
    else:
        stimes = bus.tt_start
    if stimes:
        try:
            stimes = json.loads(stimes)
        except:
            stimes = []
    if stimes:
        first_last["s0"], first_last["s1"] = [], []
        if stimes.get("0"):
            try:
                first_last["s0"] = [[int(x.split(":")[0]), int(x.split(":")[1])] for x in stimes["0"]]
            except:
                first_last["s0"] = []
        if stimes.get("1"):
            try:
                first_last["s1"] = [[int(x.split(":")[0]), int(x.split(":")[1])] for x in stimes["1"]]
            except:
                first_last["s1"] = []

    serialized['first_last'] = first_last

    bdata = bus.bdata_mode()
    if bdata:
        serialized['bdata_mode%s' % mode] = bdata
        serialized['bdata_mode%s' % mode]['updated'] = six.text_type(
            serialized['bdata_mode%s' % mode]['updated']).split('.')[0].split(' ')[1]
        serialized['bdata_mode%s' % mode]['bus_id'] = bus.id

    # для совместимого словаря - кол-во пассажиров
    passenger_serialized = rcache_get('passengers_%s' % bus.id, {})
    new_passenger_serialized = {}
    for k,v in passenger_serialized.items():
        if v:
            new_passenger_serialized[k] = len(v)
    serialized['passenger'] = new_passenger_serialized

    if mode == 10:
        time_bst = REDIS.hgetall("time_bst_ts__%s" % bus.id)
        time_bst = {bus.id: {int(k.decode('utf8')): int(v.decode('utf8')) for k, v in time_bst.items()}}
    else:
        time_bst = REDIS.hgetall("time_bst__%s" % bus.id)
        time_bst = {bus.id: {int(k.decode('utf8')): v.decode('utf8') for k, v in time_bst.items()}}

    serialized['time_bst']  = time_bst.get(bus.id, {})

    # todo check for city before
    resch = rcache_get("reschedule_3_%s" % bus.id)
    if resch:
        serialized.update(resch)

    if raw:
        return serialized
    else:
        return json.dumps(serialized)
####################

# the plan: fill_bus_endpoints, move_to, fix_route_order.py
def fill_bus_endpoints(b, DEBUG=False):
    # set endpoint flag on first and lst, fix route numbering (starts with 0 for every dir)
    info = []
    changes = 0
    napr_change = False
    for d in [0,1]:
        routes=Route.objects.filter(bus=b, direction=d).order_by('order')
        if not routes: continue
        i=0
        for r in routes:
            was_order, was_endpoint = r.order, r.endpoint
            r.order = i
            if r.order in [0, len(routes)-1]:
                r.endpoint = True
            else:
                r.endpoint = False

            if was_order != r.order or was_endpoint != r.endpoint:
                changes += 1
                r.save(update_fields=['order', 'endpoint'], skip_recalc=True)
            i+=1

        napr_change = False
        napr = routes[routes.count()-1].busstop.name
        if d==0 and napr != b.napr_a:
            b.napr_a = napr
            napr_change = True
        elif napr != b.napr_b:
            b.napr_b = napr
            napr_change = True
    # potential recursion from bus.save
    if napr_change:
        b.save(update_fields=['napr_a', 'napr_b'])
    if changes or napr_change: # cache update
        routes_get(b.id, force=True)
        REDIS_W.publish("bus_new", pickle_dumps({"data": b.id}))
    if DEBUG:
        info.append(u"fill_bus_endpoints: %s %s %s\n" % (b.id, b, changes))
    return info


# DEBUG, city, force - dummy parameters for backward compability
def fill_moveto(bus=None, place=None, DEBUG=False, city=None, force=False):
    changes = 0
    with connection.cursor() as cursor:
        if bus:
            # быстро, только для маршрута
            sql = """
                UPDATE bustime_nbusstop
                SET moveto = b."name"
                FROM (
                    SELECT r.*,
                        COALESCE(s."name", -- NULL если последняя в направлении
                            CASE -- ищем первую остановку в противоположном направлении
                                WHEN r.direction = 0 THEN
                                    (SELECT bs."name"
                                    FROM bustime_nbusstop bs
                                    WHERE bs.id = (SELECT br.busstop_id
                                                    FROM bustime_route br
                                                    WHERE br.bus_id = r.bus_id AND br.direction = 1 AND br."order" = 1)
                                    )
                                WHEN r.direction = 1 THEN
                                    (SELECT bs."name"
                                    FROM bustime_nbusstop bs
                                    WHERE bs.id = (SELECT br.busstop_id
                                                    FROM bustime_route br
                                                    WHERE br.bus_id = r.bus_id AND br.direction = 0 AND br."order" = 1)
                                    )
                                ELSE NULL
                            END
                        ) AS "name"
                    FROM (
                        -- all bus routes
                        SELECT r.*,
                            -- next stop
                            LEAD(r.busstop_id) over (partition BY r.bus_id, r.direction ORDER BY r."order") AS next_stop
                        FROM bustime_route r
                        WHERE r.bus_id = %s
                    ) r
                    LEFT JOIN bustime_nbusstop s ON s.id = r.next_stop
                ) b
                WHERE b.busstop_id = bustime_nbusstop.id
            """
            cursor.execute(sql, [bus.id])
        elif place:
            # медленней, все маршруты place
            sql = """
                UPDATE bustime_nbusstop
                SET moveto = b."name"
                FROM (
                    SELECT r.*,
                        COALESCE(s."name", -- NULL если последняя в направлении
                            CASE -- ищем первую остановку в противоположном направлении
                                WHEN r.direction = 0 THEN
                                    (SELECT bs."name"
                                    FROM bustime_nbusstop bs
                                    WHERE bs.id = (SELECT br.busstop_id
                                                    FROM bustime_route br
                                                    WHERE br.bus_id = r.bus_id AND br.direction = 1 AND br."order" = 1)
                                    )
                                WHEN r.direction = 1 THEN
                                    (SELECT bs."name"
                                    FROM bustime_nbusstop bs
                                    WHERE bs.id = (SELECT br.busstop_id
                                                    FROM bustime_route br
                                                    WHERE br.bus_id = r.bus_id AND br.direction = 0 AND br."order" = 1)
                                    )
                                ELSE NULL
                            END
                        ) AS "name"
                    FROM (
                        -- all bus routes
                        SELECT r.*,
                            -- next stop
                            LEAD(r.busstop_id) over (partition BY r.bus_id, r.direction ORDER BY r."order") AS next_stop
                        FROM bustime_route r
                        WHERE r.bus_id IN (SELECT bus_id FROM bustime_bus_places WHERE place_id = %s)
                    ) r
                    LEFT JOIN bustime_nbusstop s ON s.id = r.next_stop
                ) b
                WHERE b.busstop_id = bustime_nbusstop.id
            """
            cursor.execute(sql, [place.id])
        else:
            # медленно, все маршруты
            sql = """
                UPDATE bustime_nbusstop
                SET moveto = b."name"
                FROM (
                    SELECT r.*,
                        COALESCE(s."name", -- NULL если последняя в направлении
                            CASE -- ищем первую остановку в противоположном направлении
                                WHEN r.direction = 0 THEN
                                    (SELECT bs."name"
                                    FROM bustime_nbusstop bs
                                    WHERE bs.id = (SELECT br.busstop_id
                                                    FROM bustime_route br
                                                    WHERE br.bus_id = r.bus_id AND br.direction = 1 AND br."order" = 1)
                                    )
                                WHEN r.direction = 1 THEN
                                    (SELECT bs."name"
                                    FROM bustime_nbusstop bs
                                    WHERE bs.id = (SELECT br.busstop_id
                                                    FROM bustime_route br
                                                    WHERE br.bus_id = r.bus_id AND br.direction = 0 AND br."order" = 1)
                                    )
                                ELSE NULL
                            END
                        ) AS "name"
                    FROM (
                        -- all bus routes
                        SELECT r.*,
                            -- next stop
                            LEAD(r.busstop_id) over (partition BY r.bus_id, r.direction ORDER BY r."order") AS next_stop
                        FROM bustime_route r
                    ) r
                    LEFT JOIN bustime_nbusstop s ON s.id = r.next_stop
                ) b
                WHERE b.busstop_id = bustime_nbusstop.id
            """
            cursor.execute(sql)

        changes = cursor.rowcount
    # with connection
    return changes
# fill_moveto

# city или place
def fill_order(city, DEBUG=False):
    info = []

    with connection.cursor() as cursor:
        cursor.execute("""
            update bustime_bus
            set "order" = c.r * 10 + ttype * 10000
            from (
                SELECT
                    row_number() over (
                        ORDER BY b.ttype,
                        case
                        -- если имя начинается с цифры, удаляем из негё буквы и получаем число
                        when b.name ~ '^[0-9]' then NULLIF(regexp_replace(b.name, '\D', '', 'g'), '')::numeric
                        -- если имя начинается с буквы, формируем число заменяя буквы их кодом
                        else NULLIF(regexp_replace(b.name, '\D', TO_CHAR(10*ASCII(SUBSTRING(b.name, 1, 1)), 'FM99999999'), 'g'), '')::numeric
                        end
                    ) as r,
                    b.id --, b.name, b.ttype, b."order", b.city_id
                FROM bustime_bus b
                INNER JOIN bustime_bus_places p ON (b.id = p.bus_id)
                WHERE p.place_id = %s
            ) c
            where bustime_bus.id = c.id
        """, [city.id])

        info.append(f"Updated buses: {cursor.rowcount}")

    return info


def cache_reset_bus(bus, deleted=False):
    lock_key = f'cache_reset_bus_{bus.id}'
    if not rcache_get(lock_key):
        rcache_set(lock_key, 1, 60)
        if not deleted:
            # не нужно после удаления маршрута
            bus_last_f(bus, force=True)
            routes_get(bus.id, force=True)

        # не сработает, если cache_reset_bus вызвана из @receiver(post_delete) ибо никаких релейшенов уже нет
        for place in bus.places.all():
            buses_get(place, force=True)
            stops_get(place, force=True)
            get_busstop_points(place, force=True)
            #city_routes_get(place, force=True)

        REDIS_W.delete(f"turbo_route_{bus.id}")
        # Send signal to reload turbos
        REDIS_W.publish(f"turbo_{bus.id}", pickle_dumps({"cmd": "reload"}))

        # turned off for #3592, it doesn't help anyway, because thread specific
        # fill_bus_stata()
        REDIS_W.delete(lock_key)
# cache_reset_bus


class Diff(models.Model):
    """
    json serialized model. you know what it is...
    """
    us = models.ForeignKey(UserSettings, null=True, blank=True, on_delete=models.SET_NULL)
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    ctime = models.DateTimeField(auto_now_add=True)
    # 0 = modified, 1 added, 2 deleted, 3 request for change
    action = models.SmallIntegerField(default=3)
    # needs to be approved? approved stage
    status = models.SmallIntegerField(null=True, blank=True)
    # comment = models.CharField(max_length=80)
    model = models.CharField(max_length=16)
    model_pk = models.IntegerField(null=True, blank=True)
    data = models.TextField(null=True, blank=True)

    def __str__(self):
        return "%s: %s %s" % (self.id, self.model, self.model_pk)

    def deser(self):
        result = []
        for obj in serializers.deserialize("json", self.data):
            result.append(obj.object)
        return result


def get_city_graph(city_id):
    import graph_tool
    if not GRAPH_MAP.get(city_id):
        graph = graph_tool.Graph()
        try:
            city_graph = CityRouteGraph.objects.get(city_id=city_id)
            with io.BytesIO() as graph_file:
                graph_file.write(city_graph.graph)
                graph_file.seek(0)
                graph.load(graph_file, fmt="gt")
        except (OSError, IOError, CityRouteGraph.DoesNotExist):
            graph = None
        GRAPH_MAP[city_id] = graph
    return GRAPH_MAP.get(city_id)


def fill_chat_cache(bus_id, force=False, lang="ru"):
    cc_key = "rpc_chat_%s_%s" % (bus_id, lang)
    history = rcache_get(cc_key, False)
    if history is False or force:
        history = []
        for chat in Chat.objects.filter(bus=bus_get(bus_id), deleted=False).order_by("-ctime")[:30]:
            msg = chat_format_msg(chat, lang=lang)
            history.insert(0, msg)
        rcache_set(cc_key, history, 60*60*24)
    return history


def fill_chat_city_cache(place_id, force=False, lang="ru"):
    cc_key = "rpc_chat_city_%s_%s" % (place_id, lang)
    history = rcache_get(cc_key, False)
    if history is False or force:
        history = []
        for chat in Chat.objects.filter(bus__places__id=place_id, deleted=False).order_by("-ctime")[:30]:
            msg = chat_format_msg(chat, extra={"bus_id": chat.bus_id}, lang=lang)
            history.insert(0, msg)
        rcache_set(cc_key, history, 60*60*24)
    return history


def get_btc(currency='eur', force=False):
    """
    Возвращает стоимость 0.001 BTC.
    Берет из обменника, сохраняет в кэш, отправляет в канал если изменился.
    """
    cc_key = "btc_%s" % currency
    btc = rcache_get(cc_key, None)
    if force:
        btc_prev = btc
        try:
            params = {'ids': 'bitcoin', 'vs_currencies': currency}
            r = requests.get('https://api.coingecko.com/api/v3/simple/price', params=params)
            btc = r.json()['bitcoin'][currency]
        except:
            return btc
        btc = "%.1f" % round((float(btc)/1000), 2)
        rcache_set(cc_key, btc)
        if btc_prev != btc:
            sio_pub('ru.bustime.counters', {"btc_%s" % currency: btc})
    return btc

def get_ava_photos(males=True, females=False):
    female_names = ['driver_10', 'driver_11']
    photos_all = []
    for (dirpath, dirnames, filenames) in \
        os.walk('%s/bustime/static/img/ava/' % settings.PROJECT_ROOT):
        photos_all.extend(filenames)
        break
    photos_all = [x for x in photos_all if 'driver_' in x]
    photos_all = [x for x in photos_all if '.png' in x]
    photos_all = [x for x in photos_all if '_s.png' not in x]
    photos_all = [x.replace('.png','') for x in photos_all]
    photos = []
    for x in photos_all:
        female = False
        for f in female_names:
            if x.startswith(f):
                female = True
        if males and not female:
            photos.append(x)
        if females and female:
            photos.append(x)
    photos.sort()

    return photos


def lotime(t, lang='ru'):
    with translation_override(lang):
        return localize(t)


class Settings(models.Model):
    ctime = models.DateTimeField(auto_now_add=True, db_index=True)
    mtime = models.DateTimeField(auto_now=True, null=True, blank=True)
    key = models.CharField(max_length=32, unique=True)
    value_int = models.IntegerField(null=True, blank=True)
    value_string = models.TextField(null=True, blank=True)
    json = models.BooleanField(default=False)
    description = models.TextField("Описание", null=True, blank=True)

    def __str__(self):
        return self.key

    @property
    def value(self):
        value = None
        if self.value_int:
            value = self.value_int
        elif self.value_string:
            value = self.value_string
            if self.json:
                value = json.loads(value)
        return value

    def save(self, *args, **kwargs):
        if self.json:
            # check for valid
            value = json.loads(self.value_string)
        super(Settings, self).save(*args, **kwargs)
        get_setting(self.key, force=True)

    class Meta:
        verbose_name = gettext_lazy("настройка")
        verbose_name_plural = gettext_lazy("настройки")


def get_setting(cc_key, force=False):
    s = None
    if not force:
        try:
            s = rcache_get(cc_key)
        except:
            s = None
    if force or s is None:
        try:
            s = Settings.objects.get(key=cc_key).value
            rcache_set(cc_key, s, 60*60*24)
        except:
            s = None
    return s


TTYPE_STATUS = (
    (0, _('Есть данные по ТС')),
    (1, _('Нет данных по ТС')),
    (2, _('Установлен маршрут')),
    (3, _('Потерян маршрут')),
    (4, _('Пришел на конечную')),
    (5, _('Зомби')),
    (6, _('Стоянка на конечной')),
    (7, _('Сошел с маршрута')),
    (8, _('Изменен маршрут')),
    (9, _('Резерв')),
)

class VehicleStatus(models.Model):
    city_time = models.DateTimeField(auto_now_add=False, db_index=True, null=False, blank=False)
    city = models.IntegerField(null=True, blank=True, db_index=True)
    status = models.IntegerField(choices=TTYPE_STATUS, null=False, blank=False, db_index=True)
    event_time = models.DateTimeField(auto_now_add=False, null=True, blank=True)
    uniqueid = models.TextField(null=False, blank=False)   # corellate with Uevent(or REDIS 'uevents').uniqueid
    gosnum = models.CharField(max_length=16, null=True, blank=True)
    bus = models.IntegerField(null=True, blank=True)
    endpoint = models.IntegerField(null=True, blank=True)
    zombie = models.BooleanField(default=False)
    sleeping = models.BooleanField(default=False)
    away = models.BooleanField(default=False)
    custom = models.BooleanField(default=False)
    """
    def __str__(self):
        s = (self.city.name, self.uniqueid, self.city_time, self.status)
        return u"%s uid=%s time=%s, status=%d" % s
    """
    class Meta:
        verbose_name = _("Статус транспорта")
        verbose_name_plural = _("Статусы транспорта")
        indexes = [
            models.Index(fields=['uniqueid', 'city', 'event_time']),
        ]


class SmartUser(models.Model):
    ctime = models.DateTimeField(auto_now_add=True)
    uid = models.CharField(max_length=16, null=True, blank=True)
    city = models.CharField(max_length=32, null=True, blank=True)
    registered = models.BooleanField(default=False)
    # ''.join(random.choice('0123456789abcdef') for n in xrange(16))


class SMS(models.Model):
    ctime = models.DateTimeField(auto_now_add=True)
    received = models.DateTimeField(null=True, blank=True)
    src = models.CharField(max_length=15)
    dst = models.CharField(max_length=15)
    text = models.CharField(max_length=160, blank=True)

    def __str__(self):
        return self.src
    class Meta:
        verbose_name_plural = "SMS"


class CityNews(models.Model):
    ctime = models.DateTimeField(auto_now_add=True, db_index=True)
    city = models.ForeignKey(City, null=True, blank=True, on_delete=models.SET_NULL)
    title = models.CharField(max_length=255, blank=True)
    body = models.TextField()
    author = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    etime = models.DateTimeField(default=day_after_week, db_index=True, verbose_name='expiration time') # ExpirationTime
    NEWS_TYPE_CHOICES = [
        (1, _("Общие")),
        (2, _("Обновления")),
    ]
    news_type = models.IntegerField(choices=NEWS_TYPE_CHOICES, default=1, db_index=True)
    news_link = models.CharField(max_length=255, null=True, blank=True)
    place = models.ForeignKey(Place, null=True, blank=True, on_delete=models.CASCADE)

    @property
    def active(self):
        return self.city.now < self.etime

    def clean(self):
        time = self.ctime if self.ctime else datetime.datetime.now()
        DateValidator(time + datetime.timedelta(days=14))(self.etime)
        super().clean()

    def __str__(self):
        return u"%s: %s" % (self.city, self.body)

    def save(self, *args, **kwargs):
        super(CityNews, self).save(*args, **kwargs)
        if self.news_type == 1:
            cc_key = "citynews__%s" % self.city_id
            rcache_set(cc_key, self)

    class Meta:
        verbose_name = gettext_lazy("Городская новость")
        verbose_name_plural = gettext_lazy("Городские новости")


class Jam(models.Model):
    create_time = models.DateTimeField(auto_now_add=True, null=True, blank=True, db_index=True)
    busstop_from = models.IntegerField(db_index=True)
    busstop_to = models.IntegerField(db_index=True)
    average_time = models.IntegerField(null=True, blank=True)
    ratio = models.SmallIntegerField(null=True, blank=True)


def get_jams_for_city(city, busstops=None):
    if not busstops:
        query = '''SELECT ARRAY_AGG(DISTINCT busstop_id) from bustime_route br WHERE br.bus_id IN (
            SELECT id FROM bustime_bus bb WHERE bb.city_id = %s
        );'''
        with connections['default'].cursor() as cursor:
            cursor.execute(query, [city.id])
            busstops = cursor.fetchall()[0][0]

    if not busstops:
        return []
    # пары остановок берём из кэша (см. coroutines/jam.py)
    cc_key = "jam__%s" % city.id
    jam = rcache_get(cc_key)
    result = []
    if jam: # кэш есть
        result = [{'busstop_from': int(j[0]), 'busstop_to': int(j[1]), 'average_time': j[2], 'ratio': j[3]}
                for j in jam if int(j[0]) in busstops and int(j[1]) in busstops]
        # for j in jam
    elif len(busstops) > 0:
        # кэша нет или требуются данные "за вчера"
        # TODO: "за вчера" пока не обрабатываются
        busstopss = tuple(busstops)
        cursor = connections['bstore'].cursor()
        cursor.execute('''
            WITH a AS (
              SELECT busstop_from, busstop_to, MAX(create_time) AS create_time
              from bustime_jam
              WHERE create_time >= CURRENT_DATE -- здесь обработать требуемую дату
              and busstop_to IN %s and busstop_from IN %s
              GROUP BY busstop_from, busstop_to
            )
            SELECT b.busstop_from, a.busstop_to, b.ratio, b.average_time
            FROM a
            LEFT JOIN bustime_jam b ON b.busstop_to = a.busstop_to
                                        AND b.busstop_from = a.busstop_from
                                        AND b.create_time = a.create_time
        ''', [busstopss, busstopss])
        columns = [col[0] for col in cursor.description]
        result = [dict(zip(columns, row)) for row in cursor.fetchall()]
        cursor.close()
    else:
        result = []
    return result




class JamDaily(models.Model):
    date = models.DateField(null=True, blank=True, db_index=True)
    busstop_from = models.IntegerField(db_index=True, null=True, blank=True)
    busstop_to = models.IntegerField(db_index=True, null=True, blank=True)
    min_time = models.IntegerField(null=True, blank=True)
    max_time = models.IntegerField(null=True, blank=True)


class JamLine(models.Model):
    busstop_from = models.IntegerField()
    busstop_to = models.IntegerField()
    line = models.LineStringField(srid=4326, null=True, blank=True)
    class Meta:
        indexes = [
            models.Index(fields=['busstop_from', 'busstop_to',]),
        ]


def get_client_ip(request):
    ip = request.META.get('REMOTE_ADDR')
    PRIVATE_IPS_PREFIX = ('10.', '172.', '192.', )
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        proxies = x_forwarded_for.replace(" ", "").split(',')
        # remove the private ips from the beginning
        while (len(proxies) > 0 and proxies[0].startswith(PRIVATE_IPS_PREFIX)):
            proxies.pop(0)
        # take the first ip which is not a private one (of a proxy)
        if len(proxies) > 0:
            ip = proxies[0]
    # if x_forwarded_for

    if ip:
        ip = ip.strip()
        # check IP is valid address
        import socket
        try:
            socket.inet_aton(ip)
        except socket.error:
            ip = None

        # for ipv6
        # try:
        #     socket.inet_pton(socket.AF_INET6, ip)
        # except socket.error:
        #     ip = None

    return ip


def detect_holiday(city):
    holiday = ""
    if city:
        now = city.now.date()
    else:
        now = datetime.datetime.now().date()

    if now >= datetime.date(now.year, 10, 24) and \
       now <= datetime.date(now.year, 11, 1):
        holiday = "halloween"
    elif now >= datetime.date(now.year, 12, 15) or \
         now <= datetime.date(now.year, 1, 10):
        holiday = "new year"
    elif now == datetime.date(now.year, 2, 14):
        holiday = "valentine"
    elif now == datetime.date(now.year, 2, 23):
        holiday = "man"
    elif now == datetime.date(now.year, 3, 8):
        holiday = "woman"
    elif now == datetime.date(now.year, 4, 1):
        holiday = "joke"
    elif now == datetime.date(now.year, 4, 12):
        holiday = "cosmonautics"
    elif now == datetime.date(now.year, 4, 20):
        holiday = "weed"
    elif now == datetime.date(now.year, 10, 31):
        holiday = "bitcoin"

    return holiday


def fill_routeline(bus, force, DEBUG=False):
    bsave = False
    for direction in [0, 1]:
        if DEBUG: print(f'direction: {direction}')
        full_route = Route.objects.filter(bus=bus, direction=direction).order_by('order')
        if len(full_route) < 3 and direction == 1:
            # wipe out if it had 2 dir before
            if DEBUG: print('wipe out')
            RouteLine.objects.filter(bus=bus, direction=direction).delete()
        routeline = RouteLine.objects.filter(bus=bus, direction=direction)
        # if routeline and not force:
        #     return
        if routeline and not force:
            # todo: make it direction aware
            rl_orig = routeline[0]
            if rl_orig.mtime:
                mtime = rl_orig.mtime
            else:
                mtime = rl_orig.ctime
            if not bus.mtime or mtime >= bus.mtime:
                if DEBUG: print('skipping')
                return  # do nothing
        if routeline and not routeline[0].autofill:
            if DEBUG: print('no autofill')
            continue

        final_points = []

        iterations = [1]
        if len(full_route) == 0:
            if DEBUG: print('no routes')
            continue
        elif len(full_route) > 80:
            iterations.append(2)

        for i in iterations:
            if len(iterations) > 1:
                if i == 1:
                    route = full_route[:70]
                else:
                    route = full_route[70:]
            else:
                route = full_route

            points = []
            for r in route:
                stop = r.busstop
                point = {}
                point['y'] = stop.point[0]
                point['x'] = stop.point[1]
                points.append(point)

            url = '%s/route?' % settings.GH_SERVER
            for p in points:
                url = url + 'point=%s,%s&' % (p['x'], p['y'])
            # на машине
            url += 'points_encoded=false&locale=ru-RU&profile=car&elevation=false&instructions=false&type=json'
            # пешком
#            url += 'points_encoded=false&locale=ru-RU&profile=foot&elevation=false&instructions=false&type=json'

            if DEBUG:
                print(f'iteration {i}: {len(points)} points')
                print(f'GET: {url}')

            headers = {}
            headers['Referer'] = url

            try:
                # Replace web to local service
                #r = requests.get(url, headers=headers, timeout=15, proxies=PROXIES)
                r = requests.get(url, timeout=5)
                #if DEBUG: print(r.text)
            except Exception as ex:
                if DEBUG: print('Error: %s' % str(ex))
                return False

            try:
                js = r.json()
            except:
                if DEBUG: print('not json: %s' % r.text)
                return False

            if not js.get('paths'):
                if DEBUG: print('paths not exists for bus %s: %s' % (bus.name, r.text))
                return False

            paths = js['paths']
            points = paths[0]['points']
            coords = points['coordinates']

            #print '\npaths=', paths
            #print '\npoints=', points
            #print '\ncoords=', coords

            for p in coords:
                lon = p[0]
                lat = p[1]
                pnt = Point(lon, lat)
                final_points.append(pnt)
        # for i in iterations

        routeline, cr = RouteLine.objects.get_or_create(bus=bus, direction=direction)
        routeline.line = LineString(final_points)
        routeline.mtime = bus.places.order_by("-population").first().now
        routeline.save()
        dbl = distance_by_line(routeline.line)
        if direction == 0 and bus.distance0 != dbl:
            if DEBUG:
                print("Distance0=%s" % dbl)
            bus.distance0 = dbl
            bsave = True
        if direction == 1 and bus.distance1 != dbl:
            bus.distance1 = dbl
            bsave = True

    if bsave:
        if bus.distance0 == None:
            bus.distance0 = 0
        if bus.distance1 == None:
            bus.distance1 = 0
        bus.distance = bus.distance0 + bus.distance1
        bus.travel_time = int(bus.distance/1000.0 * 60.0 / 24.0)
        bus.save()

    return True


def pre_save_bus(bus):
    if bus.city.name == u'Санкт-Петербург' and not bus.xeno_id:
        f = open('%s/addons/feed/routes.txt' % settings.PROJECT_ROOT, 'r')
        greader = csv.reader(f, delimiter=',', quotechar='"')
        for s in greader:
            xeno_id, name, ttype = s[0], s[2], s[5]
            # xeno_id, name, ttype = s[0], s[2].decode('utf8'), s[5]
            name, ttype = spb_gtfs_namer(name, ttype)
            if ttype == bus.ttype and name == bus.name:
                bus.xeno_id = xeno_id
                break
        f.close()
    return bus


def spb_gtfs_namer(name, ttype):
    if ttype == "bus":
        ttype = 0
    elif ttype == "trolley":
        ttype = 1
    elif ttype == "tram":
        ttype = 2
    elif ttype == "ship":
        ttype = 4
    else:
        # print 'not such transport: %s' % ttype
        ttype = None

    name = name.strip().upper()
    if name.startswith(u'К-'):
        name = name.replace(u'К-', '')
        ttype = 3
    if u'МЕГА' in name:
        name = name.replace(' ', '')

    return name, ttype


def bus_stop_name_beauty(name):
    text = six.text_type(name)
    if '(' in text:
        # написать регэксп для удаления ул. внутри скобок
        text = re.sub(u"\(ул.?\ ?(.+)\)", r"(\1)", text)

    text = text.replace(u"Центральный парк культуры и отдыха ", u"ЦПКиО ")

    text = text.replace(u"Центр культуры и отдыха ", u"ЦКИО ")
    text = text.replace(u"Центр культуры и отдыха ", u"ЦКиО")

    text = text.replace(u"Спорт Комплекс ", u"СК ")
    text = text.replace(u"Спорт комплекс ", u"СК ")
    text = text.replace(u"спорт комплекс ", u"СК ")

    text = text.replace(u"Торгово-Развлекательный Комплекс ", u"ТРК ")
    text = text.replace(u"Торгово-развлекательный Комплекс ", u"ТРК ")
    text = text.replace(u"Торгово-развлекательный комплекс ", u"ТРК ")
    text = text.replace(u"торгово-развлекательный комплекс ", u"ТРК ")

    text = text.replace(u"Торгово-Развлекательный Центр ", u"ТРЦ ")
    text = text.replace(u"Торгово-развлекательный Центр ", u"ТРЦ ")
    text = text.replace(u"Торгово-развлекательный центр ", u"ТРЦ ")
    text = text.replace(u"торгово-развлекательный центр ", u"ТРЦ ")

    text = text.replace(u"Торговый Комплекс ", u"ТК ")
    text = text.replace(u"Торговый комплекс ", u"ТК ")
    text = text.replace(u"торговый комплекс ", u"ТК ")

    text = text.replace(u"Торговый Центр ", u"ТЦ ")
    text = text.replace(u"Торговый центр ", u"ТЦ ")
    text = text.replace(u"торговый центр ", u"ТЦ ")

    text = text.replace(u"Торговый Дом ", u"ТД ")
    text = text.replace(u"Торговый дом ", u"ТД ")
    text = text.replace(u"торговый дом ", u"ТД ")

    text = text.replace(u"имени ", u"им. ")
    text = text.replace(u"Имени ", u"им. ")
    text = text.replace(u"Им. ", u"им. ")
    text = text.replace(u"Им ", u"им. ")
    text = text.replace(u"им ", u"им. ")

    text = text.replace(u"переулок ", u"пер. ")
    text = text.replace(u"Переулок ", u"пер. ")
    text = text.replace(u"Пер ", u"пер. ")
    text = text.replace(u"пер ", u"пер. ")

    text = text.replace(u"Кинотеатр ", u"к-тр ")
    text = text.replace(u"кинотеатр ", u"к-тр ")

    text = text.replace(u"Киноцентр ", u"КЦ ")
    text = text.replace(u"киноцентр ", u"КЦ ")

    text = text.replace(u"Санаторий ", u"сан. ")
    text = text.replace(u"санаторий ", u"сан. ")

    text = text.replace(u"Жилой Комплекс ", u"ЖК ")
    text = text.replace(u"Жилой комплекс ", u"ЖК ")
    text = text.replace(u"жилой комплекс ", u"ЖК ")

    text = text.replace(u"Станция Метро ", u"ст. м. ")
    text = text.replace(u"Станция метро ", u"ст. м. ")
    text = text.replace(u"станция метро ", u"ст. м. ")
    text = text.replace(u"Станция ", u"ст. ")
    text = text.replace(u"станция ", u"ст. ")
    text = text.replace(u"ст ", u"ст. ")
    text = text.replace(u"Ст ", u"ст. ")
    text = text.replace(u"Ст. ", u"ст. ")

    text = text.replace(u"Железнодорожный ", u"Ж/д ")
    text = text.replace(u"железнодорожный ", u"Ж/д ")

    text = text.replace(u"посёлок ", u"пос. ")
    text = text.replace(u"Посёлок ", u"пос. ")
    text = text.replace(u"поселок ", u"пос. ")
    text = text.replace(u"Поселок ", u"пос. ")
    text = text.replace(u"Пос ", u"пос. ")
    text = text.replace(u"пос ", u"пос. ")

    text = text.replace(u"микрорайон ", u"мкр. ")
    text = text.replace(u"Микрорайон ", u"мкр. ")
    text = text.replace(u"М-н ", u"мкр. ")
    text = text.replace(u"м-н ", u"мкр. ")

    text = text.replace(u"Совхоз ", u"с/х ")
    text = text.replace(u"совхоз ", u"с/х ")

    text = text.replace(u"Дом Культуры ", u"ДК ")
    text = text.replace(u"Дом культуры ", u"ДК ")
    text = text.replace(u"дом культуры ", u"ДК ")

    text = text.replace(u"Площадь ", u"пл. ")
    text = text.replace(u"площадь ", u"пл. ")
    text = text.replace(u"Пл. ", u"пл. ")

    text = text.replace(u"Проспект ", u"пр-кт ")
    text = text.replace(u"проспект ", u"пр-кт ")
    text = text.replace(u"просп. ", u"пр-кт ")
    text = text.replace(u"Пр-кт ", u"пр-кт ")
    text = text.replace(u"пр-т ", u"пр-кт ")
    text = text.replace(u"Пр-т ", u"пр-кт ")
    text = text.replace(u"пр. ", u"пр-кт ")
    text = text.replace(u"Пр. ", u"пр-кт ")

    text = text.replace(u"Поворот ", u"пов. ")
    text = text.replace(u"поворот ", u"пов. ")

    text = text.replace(u"Улица ", u"ул. ")
    text = text.replace(u"улица ", u"ул. ")
    text = text.replace(u"Ул ", u"ул. ")
    text = text.replace(u"ул ", u"ул. ")

    text = text.replace(u"Село ", u"с. ")
    text = text.replace(u"село ", u"с. ")
    text = text.replace(u"Город ", u"г. ")
    text = text.replace(u"город ", u"г. ")
    text = text.replace(u"Деревня ", u"д. ")
    text = text.replace(u"деревня ", u"д. ")

    text = text.replace(u"Пионерский Лагерь", u"п/л ")
    text = text.replace(u"Пионерский лагерь", u"п/л ")
    text = text.replace(u"пионерский лагерь", u"п/л ")

    text = text.replace(u"Жилой Массив ", u"ж/м ")
    text = text.replace(u"Жилой массив ", u"ж/м ")
    text = text.replace(u"жилой массив ", u"ж/м ")

    text = text.replace(u"Садовое Товарищество ", u"СНТ ")
    text = text.replace(u"Садовое товарищество ", u"СНТ ")
    text = text.replace(u"садовое товарищество ", u"СНТ ")
    text = text.replace(u"с/т ", u"СНТ ")

    text = text.replace(u"Дворец Молодёжи ", u"ДМ ")
    text = text.replace(u"Дворец молодёжи ", u"ДМ ")
    text = text.replace(u"дворец молодёжи ", u"ДМ ")

    text = text.replace(u"База Отдыха ", u"б/о ")
    text = text.replace(u"База отдыха ", u"б/о ")
    text = text.replace(u"база отдыха ", u"б/о ")
    text = text.replace(u"БО ", u"б/о ")

    text = text.replace(u"Садоводческое Общество ", u"с.о. ")
    text = text.replace(u"Садоводческое общество ", u"с.о. ")
    text = text.replace(u"садоводческое общество ", u"с.о. ")

    text = text.replace(u"Сельский Округ ", u"с/о ")
    text = text.replace(u"Сельский округ ", u"с/о ")
    text = text.replace(u"сельский округ ", u"с/о ")

    text = text.replace(u"Дачный Посёлок ", u"ДП ")
    text = text.replace(u"Дачный посёлок ", u"ДП ")
    text = text.replace(u"дачный посёлок ", u"ДП ")

    text = text.replace(u"Социальный ", u"Соц. ")
    text = text.replace(u"социальный ", u"Соц. ")

    text = text.replace(u"(по требованию)", u"")
    text = text.replace(u"по требованию", u"")
    text = text.replace(u"(По требованию)", u"")
    text = text.replace(u"По требованию", u"")

    text = text.replace(u"Остановка ", u"")
    text = text.replace(u"остановка ", u"")

    text = text.replace(u'"', u"")
    text = text.replace(u"'", u"")
    text = text.replace(u"«", u"")
    text = text.replace(u"»", u"")
    text = text.replace(u"№", u"")
    text = text.replace(u'   ', u' ')
    text = text.replace(u'  ', u' ')
    text = text.replace(u'( ', u'(')
    text = text.replace(u' )', u')')

    text = text.strip()

    if len(text) > 2:
        return text
    else:
        return name


def fill_inter_stops(city, force=False):
    changes_cnt = 0
    qs = Bus.objects.filter(places=city).order_by("order")
    if not force:
        qs = qs.filter(inter_stops__isnull=True)
    for bus in qs:
        changes_cnt += fill_inter_stops_for_bus(bus)
    return changes_cnt

def fill_inter_stops_for_bus(bus):
    if bus.inter_stops_fixed:
        return 0

    changes_cnt = 0
    px, py = None, None
    max_ = 1200
    for r in Route.objects.filter(bus=bus, direction=0).order_by('order').select_related('busstop'):
        x, y = r.busstop.point.coords
        if px:
            dis = int(distance_meters(x, y, px, py) * 1.1)
            if dis > max_:
                max_ = dis
                max_dirty = True
        px, py = x, y
    if max_ > 1200:
        if bus.inter_stops != max_:
            bus.inter_stops = max_
            bus.save()
            changes_cnt += 1
    return changes_cnt


def is_place_modify_allowed(place, us: UserSettings | MobileSettings):
    if not us or not us.user:
        return False
    if not place:
        return False
    modify_allowed = place.id in PLACE_STAFF_MODIFY.keys() or (us.user.id in [user.id for user in place.editors.all()])
    return modify_allowed


def is_gosnum_modify_allowed(place, us: UserSettings | MobileSettings):
    if not us or not us.user:
        return False
    if not place:
        return False
    modify_allowed = us.user.is_active and (us.user.is_superuser or 
                        us.user.id in [user.id for user in place.editors.all()] or
                        us.user.id in [user.id for user in place.dispatchers.all()])
    return modify_allowed


def make_uid(uid, city_id="", force=False):
    return uid


# generate unique string (within all the system)
def make_uid_(uid, channel, src):
    uid = ("%s_%s_%s_%s" % (settings.UID_PASSWD, uid, channel, src)).encode('utf8')
    uid = b64encode( hashlib.sha256(uid).digest(), b"-_")[:8]
    uid = uid.decode('utf8')
    return uid

def make_user_pin(s):
    passw = "12345"
    s = ("%s_%s" % (passw, s)).encode('utf8')
    s = int(hashlib.md5(s).hexdigest()[:3], 16)
    s = "%03d" % (s % 999)
    return s


def get_user_settings_mini(request):
    cc_key = "sess_%s" % (request.session.session_key)
    sess = rcache_get(cc_key)
    return us_get(sess)


def eday_password():
    # every day password
    s = "%s" % datetime.datetime.now().date()
    cc_key = "every_day_password_%s" % s
    pw = rcache_get(cc_key)
    if not pw:
        pw = str(random.random())
        rcache_set(cc_key, pw)
    return pw


def distance_by_line(line):
    d = 0
    prev = None
    for c in line.coords:
        if prev:
            d += distance_meters(prev[0], prev[1], c[0], c[1])
        prev = c
    return d

# получение прокси-сервера, назначаемого динамически в coroutines/dynproxy.py
def get_dyn_proxy(DEBUG=False):
    proxies = rcache_get("dinamyc_proxies", [])
    if DEBUG: print("get_dyn_proxy:", proxies)
    if proxies:
        proxy = proxies[random.randint(0, len(proxies)-1)]
        return {"http": 'http://%s' % proxy, "https": 'https://%s' % proxy}
    else:
        return None
# def get_dyn_proxy


def find_stop_ids_within(x, y, radius):
    if not REDIS.exists("geo_stops"):
        fill_stops_geospatial()
    return [int(sid.decode('utf-8')) for sid in REDIS_W.georadius("geo_stops", longitude=x, latitude=y, radius=radius, unit='m')]


def groups_cache_reset(sender, **kwargs):
    if kwargs['action'] in ['post_add', 'post_remove'] and \
        type(kwargs['instance']) == User:
        get_groups(kwargs['instance'], force=True)
        # print kwargs


m2m_changed.connect(groups_cache_reset, sender=User.groups.through)


'''
Версионирование Route
см. views.py: ajax_route_edit_save()
'''
# Версии маршрута
class BusVersion(models.Model):
    bus = models.ForeignKey(Bus, on_delete = models.CASCADE)    # ссылка на оригинальный Bus
    city = models.ForeignKey(City, on_delete = models.CASCADE, null=True)  # ссылка на оригинальный City
    user = models.ForeignKey(User, null=True, blank=True, on_delete = models.SET_NULL) # кто менял маршрут
    ctime = models.DateTimeField(auto_now_add=True, null=True, blank=True)  # дата создания версии
    stops_before = models.TextField(null=True, blank=True)  # NBusStop до редактирования
    stops_after = models.TextField(null=True, blank=True)   # NBusStop после редактирования
    routes_before = models.TextField(null=True, blank=True) # Route до редактирования
    routes_after = models.TextField(null=True, blank=True)  # Route после редактирования
    place = models.ForeignKey(Place, on_delete = models.CASCADE, null=True)

    def __str__(self):
        return u"%s %s %s" % (self.bus, self.ctime, self.user)

    class Meta:
        default_permissions = ('delete', 'view')
        verbose_name = gettext_lazy("Версия маршрута")
        verbose_name_plural = gettext_lazy("Версии маршрутов")

# Лог действий пользователя
class BusVersionLog(models.Model):
    busversion = models.ForeignKey(BusVersion, null=True, on_delete = models.SET_NULL) # ссылка на BusVersion
    bus = models.ForeignKey(Bus, null=True, on_delete = models.SET_NULL)    # ссылка на оригинальный Bus
    city = models.ForeignKey(City, null=True, on_delete = models.SET_NULL)  # ссылка на оригинальный City
    user = models.ForeignKey(User, null=True, blank=True, on_delete = models.SET_NULL) # кто менял маршрут
    ctime = models.DateTimeField(auto_now_add=True, null=True, blank=True)  # дата создания версии
    note = models.CharField(max_length=256, null=True, blank=True) # действие (добавление/удаление/перемещение/редактирование остановки...)
    nbusstop_id = models.IntegerField(null=True, blank=True) # NBusStop.id !!!
    name = models.CharField(max_length=128, null=True, blank=True)
    direction = models.SmallIntegerField(null=True, blank=True)
    order = models.SmallIntegerField(null=True, blank=True)
    place = models.ForeignKey(Place, null=True, on_delete = models.SET_NULL)

    def __str__(self):
        return u"%s %s" % (self.note, self.name)

    class Meta:
        default_permissions = ('delete', 'view')
        verbose_name = _("Лог редактирования маршрута")
        verbose_name_plural = _("Лог редактирования маршрута")
'''
/ Версионирование Route
'''


class VersionCity(models.Model):
    revision = models.OneToOneField(Revision, on_delete=models.CASCADE)
    place = models.ForeignKey(Place, on_delete=models.CASCADE)
    city = models.ForeignKey(City, null=True, blank=True, on_delete=models.CASCADE)


class CityRouteGraph(models.Model):
    """
    Модель хранит построенные графы маршрутов городов и
    таблицу соответствия id-(NBusStop,Route,VBusStop): id-Вершины графа
    """
    city = models.ForeignKey(City, on_delete=models.CASCADE)
    ctime = models.DateTimeField(auto_now_add=True)
    mtime = models.DateTimeField(auto_now=True, null=True, blank=True)
    graph = models.BinaryField()
    vertices = models.JSONField(null=True, blank=True)


"""
Источники данных gtfs
Примеры данных:
    https://transport.orgp.spb.ru/Portal/transport/internalapi/gtfs
    http://gtfs.bigbluebus.com/
"""
# Список gtfs-хранилищ, НЕ относится к данным gtfs (к шейпам)
class GtfsCatalog(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(_("Имя"), max_length=50, null=True, blank=True)
    active = models.BooleanField(_("Активен"), default=False)
    # https://gtfs.org/ru/schedule/reference/
    url_schedule = models.CharField(_("Schedule"), max_length=2000, null=True, blank=True)
    # https://gtfs.org/ru/realtime/
    # https://gtfs.org/ru/realtime/feed-entities/
    url_rt_alerts = models.CharField(_("RT:Alerts"), max_length=2000, null=True, blank=True)
    url_rt_positions = models.CharField(_("RT:Positions"), max_length=2000, null=True, blank=True)
    url_rt_updates = models.CharField(_("RT:Updates"), max_length=2000, null=True, blank=True)
    description = models.TextField(_("Примечание"), null=True, blank=True)
    ctime = models.DateTimeField(_("Добавлен"), auto_now_add=True)
    route_type_mapping = models.TextField(_("Маппинг route_type"), null=True, blank=True)
    eval_agency = models.TextField(_("Преобразование имени агенства"), null=True, blank=True)
    eval_route = models.TextField(_("Преобразование имени маршрута"), null=True, blank=True)
    eval_stops = models.TextField(_("Преобразование имени остановки"), null=True, blank=True)
    user_id = models.IntegerField(_("Пользователь"), null=True, blank=True, default=None)
    timediffk = models.IntegerField(default=0)
    cnt_buses = models.SmallIntegerField(null=True, blank=True, default=0)
    REQUEST_METHOD_CHOICES = [("get", "get"), ("post", "post")]
    request_method = models.CharField(max_length=4, choices=REQUEST_METHOD_CHOICES, default="get")
    request_auth = models.TextField(_("Авторизация"), null=True, blank=True, help_text="headers={'Authorization': 'access_token'} | auth=(user, password)")
    REQUEST_RESULT_CHOICES = [("json","json"), ("xml", "xml"), ("csv", "csv")]
    request_result_type = models.CharField(_("Метод"), max_length=4, choices=REQUEST_RESULT_CHOICES, default="json")
    pdata = models.TextField(_("Для разных нужд"), null=True, blank=True)

    class Meta:
        verbose_name = _("Каталог данных gtfs")
        verbose_name_plural = _("gtfs: Каталоги данных")

        constraints = [
            models.UniqueConstraint(fields=['url_schedule'], name="gtfscatalog_unique_url_schedule"),
        ]

    def now(self):
        retval = None
        try:
            pdata = json.loads(self.pdata or {})
            timezone = pdata.get("timezones", [''])[0] # first element without error if not exists
            if not timezone:
                pid = pdata.get("places", [0])[0]
                if pid:
                    p = Place.objects.filter(id=pid).first()
                    if p:
                        timezone = p.timezone
            if timezone:
                retval = datetime.datetime.now(tz=ZoneInfo(timezone))
        except:
            pass
        return retval
    # now
"""
Данные gtfs
Эти модели нужны для преобразования данных gtfs в нашу структуру данных маршрута
НЕ служат для хранения данных, используются только во время импорта данных gtfs

Подсмотреть структуру таблиц:
    https://github.com/public-transport/gtfs-via-postgres/tree/main/lib
Help:
    https://gtfs.org/ru/schedule/reference/
    https://gtfs.org/ru/realtime/feed-entities/

Примеры данных:
    https://transport.orgp.spb.ru/Portal/transport/internalapi/gtfs
    http://gtfs.bigbluebus.com/
"""
# Агенство - владелец набора данных, наш аналог - BusProvider
# https://gtfs.org/ru/schedule/reference/#agencytxt
class GtfsAgency(models.Model):
    id = models.BigAutoField(primary_key=True)
    catalog = models.ForeignKey(GtfsCatalog, on_delete=models.CASCADE)
    agency_id = models.TextField()
    agency_name = models.TextField()
    agency_url = models.TextField()
    agency_timezone = models.TextField(blank=True, null=True)
    agency_lang = models.TextField(blank=True, null=True)
    agency_phone = models.TextField(blank=True, null=True)
    agency_fare_url = models.TextField(blank=True, null=True)
    agency_email = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = _("gtfs: Агенство")
        verbose_name_plural = _("gtfs: Агенства")
        constraints = [
            models.UniqueConstraint(fields=['catalog', 'agency_id'], name='bustime_gtfsagency_unique')
        ]


GTFS_ROUTE_TYPE = {
    0: "Трамвай",
    1: "Метро",
    2: "Поезд",
    3: "Автобус",
    4: "Паром",
    5: "Канатный трамвай",
    6: "Подвесной подъемник",
    7: "Фуникулер",
    11: "Троллейбус",
    12: "Монорельс",
}
# Транзитные маршруты. Маршрут - это группа поездок, которые отображаются для пассажиров как единая услуга
# https://gtfs.org/ru/schedule/reference/#routestxt
class GtfsRoutes(models.Model):
    id = models.BigAutoField(primary_key=True)
    catalog = models.ForeignKey(GtfsCatalog, on_delete=models.CASCADE)
    route_id = models.TextField()
    agency_id = models.TextField(blank=True, null=True)
    route_short_name = models.TextField(blank=True, null=True)
    route_long_name = models.TextField(blank=True, null=True)
    route_desc = models.TextField(blank=True, null=True)
    route_type = models.IntegerField()  # 0 - Трамвай, 3 - Автобус ближнего и дальнего следования, 11 - Троллейбус
    route_url = models.TextField(blank=True, null=True)
    route_color = models.TextField(blank=True, null=True)
    route_text_color = models.TextField(blank=True, null=True)
    route_sort_order = models.TextField(blank=True, null=True)
    route_sort_order = models.TextField(blank=True, null=True)
    continuous_pickup = models.TextField(blank=True, null=True)
    continuous_drop_off = models.TextField(blank=True, null=True)
    network_id = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = _("gtfs: Маршрут")
        verbose_name_plural = _("gtfs: Маршруты")
        constraints = [
            models.UniqueConstraint(fields=['catalog', 'route_id'], name='bustime_gtfsroutes_unique')
        ]


# Правила составления схемы маршрутов движения транспортных средств
# https://gtfs.org/ru/schedule/reference/#shapestxt
class GtfsShapes(models.Model):
    id = models.BigAutoField(primary_key=True)
    catalog = models.ForeignKey(GtfsCatalog, on_delete=models.CASCADE)
    shape_id = models.TextField()
    shape_pt_sequence = models.IntegerField()
    #shape_pt_lat = models.FloatField()
    #shape_pt_lon = models.FloatField()
    shape_pt_loc = models.PointField(srid=4326, blank=True, null=True)
    shape_dist_traveled = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = _("gtfs: Схема маршрута")
        verbose_name_plural = _("gtfs: Схемы маршрутов")
        constraints = [
            models.UniqueConstraint(fields=['catalog', 'shape_id', 'shape_pt_sequence'], name='bustime_gtfsshapes_unique')
        ]


#  Поездки (последовательность из двух или более остановок) для каждого маршрута
#  https://gtfs.org/ru/schedule/reference/#tripstxt
class GtfsTrips(models.Model):
    id = models.BigAutoField(primary_key=True)
    catalog = models.ForeignKey(GtfsCatalog, on_delete=models.CASCADE)
    trip_id = models.TextField()
    route_id = models.TextField()
    service_id = models.TextField()
    trip_headsign = models.TextField(blank=True, null=True)     # Текст, место назначения поездки
    trip_short_name = models.TextField(blank=True, null=True)
    direction_id = models.TextField(blank=True, null=True)      # направление движения для поездки, Необязательно
    block_id = models.TextField(blank=True, null=True)
    shape_id = models.TextField(blank=True, null=True)
    wheelchair_accessible = models.TextField(blank=True, null=True)
    bikes_allowed = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = _("gtfs: Поездка")
        verbose_name_plural = _("gtfs: Поездки")
        constraints = [
            models.UniqueConstraint(fields=['catalog', 'trip_id'], name='bustime_gtfstrips_unique')
        ]


# Даты обслуживания
WEEK_DAYS = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
# https://gtfs.org/ru/schedule/reference/#calendartxt
class GtfsCalendar(models.Model):
    id = models.BigAutoField(primary_key=True)
    catalog = models.ForeignKey(GtfsCatalog, on_delete=models.CASCADE)
    service_id = models.TextField()
    monday = models.IntegerField()
    tuesday = models.IntegerField()
    wednesday = models.IntegerField()
    thursday = models.IntegerField()
    friday = models.IntegerField()
    saturday = models.IntegerField()
    sunday = models.IntegerField()
    start_date = models.DateField()
    end_date = models.DateField()

    class Meta:
        verbose_name = _("gtfs: Календарь")
        verbose_name_plural = _("gtfs: Календари")
        constraints = [
            models.UniqueConstraint(fields=['catalog', 'service_id'], name='bustime_gtfscalendar_unique')
        ]


# Исключения для услуг, определенных в calendar
# https://gtfs.org/ru/schedule/reference/#calendar_datestxt
class GtfsCalendarDates(models.Model):
    id = models.BigAutoField(primary_key=True)
    catalog = models.ForeignKey(GtfsCatalog, on_delete=models.CASCADE)
    service_id = models.TextField()
    date = models.DateField()
    exception_type = models.IntegerField()

    class Meta:
        verbose_name = _("gtfs: Исключение календаря")
        verbose_name_plural = _("gtfs: Исключения календаря")
        constraints = [
            models.UniqueConstraint(fields=['catalog', 'service_id', 'date'], name='bustime_gtfscalendardates_unique')
        ]


# Остановки, станции и входы на станции
# https://gtfs.org/ru/schedule/reference/#stopstxt
GTFS_LOCATION_TYPE = (
    ('0', 'Остановка'),
    ('1', 'Станция'),
    ('2', 'Вход/выход'),
    ('3', 'Общий узел'),
    ('4', 'Зона посадки'),
)

class GtfsStops(models.Model):
    id = models.BigAutoField(primary_key=True)
    catalog = models.ForeignKey(GtfsCatalog, on_delete=models.CASCADE)
    stop_id = models.TextField()
    stop_code = models.TextField(blank=True, null=True)
    stop_name = models.TextField(blank=True, null=True)
    stop_desc = models.TextField(blank=True, null=True)
    #stop_lat = models.FloatField(blank=True, null=True)
    #stop_lon = models.FloatField(blank=True, null=True)
    stop_pt_loc = models.PointField(srid=4326, blank=True, null=True)
    zone_id = models.TextField(blank=True, null=True)
    stop_url = models.TextField(blank=True, null=True)
    location_type = models.TextField(choices=GTFS_LOCATION_TYPE, null=True, blank=True, default='0')
    parent_station = models.TextField(blank=True, null=True)
    stop_timezone = models.TextField(blank=True, null=True)
    wheelchair_boarding = models.TextField(blank=True, null=True)
    level_id = models.TextField(blank=True, null=True)
    platform_code = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = _("gtfs: Остановка")
        verbose_name_plural = _("gtfs: Остановки")
        constraints = [
            models.UniqueConstraint(fields=['catalog', 'stop_id'], name='bustime_gtfsstops_unique')
        ]


# Время прибытия транспортного средства на остановки и отправления с них
# https://gtfs.org/documentation/schedule/reference/#stop_timestxt
class GtfsStopTimes(models.Model):
    id = models.BigAutoField(primary_key=True)
    catalog = models.ForeignKey(GtfsCatalog, on_delete=models.CASCADE)
    trip_id = models.TextField()
    arrival_time = models.DurationField(blank=True, null=True)
    departure_time = models.DurationField(blank=True, null=True)
    stop_id = models.TextField()
    stop_sequence = models.IntegerField()
    stop_headsign = models.TextField(blank=True, null=True)
    pickup_type = models.TextField(blank=True, null=True)
    drop_off_type = models.TextField(blank=True, null=True)
    shape_dist_traveled = models.TextField(blank=True, null=True)
    timepoint = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = _("gtfs: Расписание")
        verbose_name_plural = _("gtfs: Расписания")
        constraints = [
            models.UniqueConstraint(fields=['catalog', 'trip_id', 'stop_sequence'], name='bustime_gtfsstoptimes_unique')
        ]


class DataSource(models.Model):
    active = models.BooleanField(default=True)
    channel = models.CharField(max_length=50)
    src = models.CharField(max_length=50)
    gps_data_provider = models.CharField(max_length=100, null=True, blank=True)
    gps_data_provider_url = models.CharField(max_length=100, null=True, blank=True)
    check_url = models.CharField("URL проверка", max_length=100, null=True, blank=True)
    block_info = models.TextField(null=True, blank=True)
    comment = models.TextField(null=True, blank=True)
    dispatchers = models.ManyToManyField(User, related_name="ddisps")
    # time of last success
    # TODO (turbo) good_time = models.DateTimeField(null=True, blank=True)

    bus_taxi_merged = models.BooleanField("Маршрутки внутри автобусов", default=False)
    places = models.ManyToManyField(Place) # см. turbo_bus_osm_fill.py

    def __str__(self):
        s = (self.channel, self.src)
        return "%s %s" % s

    @staticmethod
    def get_hash(channel, src):
        return "%s*%s" % (channel, src)

    @staticmethod
    def get_source_id(channel, src):
        return DATASOURCE_CACHE.get(DataSource.get_hash(channel, src))

    class Meta:
        verbose_name = _("Источник данных")
        verbose_name_plural = _("Источники данных")
        constraints = [
            models.UniqueConstraint(fields=['channel', 'src'], name='bustime_datasource_unique')
        ]


class DataSourceStatus(models.Model):
    datasource = models.ForeignKey(DataSource, on_delete=models.CASCADE)
    ctime = models.DateTimeField(auto_now_add=False, db_index=True)
    nearest = models.IntegerField(null=True, blank=True)
    delay_avg = models.IntegerField(null=True, blank=True)

    def __str__(self):
        s = (self.datasource, self.ctime, self.nearest, self.delay_avg)
        return u"%s %s: nearest=%s, delay=%s" % s

    class Meta:
        verbose_name = _("Статус источника данных")
        verbose_name_plural = _("Статусы источников данных")


# after insert/update record
@receiver(post_save, sender=DataSource)
def datasource_post_save(sender, instance, **kwargs):
    DATASOURCE_CACHE[instance.get_hash(instance.channel, instance.src)] = instance.id

# after delete record
@receiver(post_delete, sender=DataSource)
def datasource_post_delete(sender, instance, **kwargs):
    del DATASOURCE_CACHE[instance.get_hash(instance.channel, instance.src)]


class DataSourcePlaceEventsCount(models.Model):
    """
    Stores events count for each provider and place.
    Created to sort providers by event count and useful metrics
    https://git.bustime.loc/norn/bustime/pulls/2859
    """

    ctime = models.DateTimeField(auto_now_add=False, db_index=True)
    ecnt = models.IntegerField(null=True, blank=True)
    datasource = models.ForeignKey(DataSource, on_delete=models.CASCADE)
    place = models.ForeignKey(Place, on_delete=models.CASCADE)

    class Meta:
        verbose_name = _("Events count for a place datasource")
        verbose_name_plural = _("Events counts for a place datasource")


PLACE_STAFF_MODIFY = {
    4: 'Калининград',
    30: 'Барнаул',
    58: 'Нижний Новгород',
    160: 'Бобруйск',
    165: 'Могилёв'
}

PLACE_TRANSPORT_CARD = {
    3: 'krasinform',
    20: 'krasinform',
    27: 'krasinform',
    61: 'tts'
}
