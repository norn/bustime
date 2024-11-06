# -*- coding: utf-8 -*-

from __future__ import absolute_import
import re
#from transliterate import translit
# from .mytransliterate import *
from bustime.mytransliterate import *
from bustime.models import * 
from django.utils.encoding import force_str
from urllib.parse import urlparse
from xmlrpc.client import ServerProxy
from django.conf import settings
from phonenumber_field.phonenumber import PhoneNumber
import geoip2.models
import geoip2.database
import datetime


def nslugify(value, min_char=None):
    p = re.compile('[^\w\s-]', re.UNICODE)
    value = re.sub(p, '', value).strip()
    value = re.sub('[-\s]+', '-', value).lower()
    # take care of non unicode stupid chars.
    if min_char and len(value) > min_char:
        nvalue = [x for x in value.split(
            '-') if x.isdigit() or len(x) >= min_char]
        nvalue = "-".join(nvalue)
        if len(nvalue):
            value = nvalue
    value = force_str(value)
    value = mytransliterate(value.upper()).lower()
    return value

def get_route_coords_from_busstops(stops, vehicle='foot'):
    paths = get_paths_from_busstops(stops, vehicle)
    points = paths[0]['points']
    return points['coordinates']


def get_paths_from_busstops(stops, vehicle='foot'):
    from django.conf import settings
    import requests
    points = []
    for stop in stops:
        if isinstance(stop, dict):
            p = stop['point']
        else:
            p = stop.point
        points.append({'x': p[1], 'y': p[0]})

    url = '%s/route?' % settings.GH_SERVER
    for p in points:
        url = url + 'point=%s,%s&' % (p['x'], p['y'])

    url += 'points_encoded=false&locale=ru-RU&profile=%s&elevation=false&instructions=false&type=json' % vehicle
    # with (open('/tmp/route_from_busstops.log', 'a')) as f:
    #     f.write(url)
    # print("url=%s" % url)

    try:
        data = requests.get(url, timeout=5).json()
        paths = data['paths']
        if not paths:
            raise ValueError('%s->%s (%s) путь не найден' % (str(points)))
        return paths
    except Exception as ex:
        print('\n%s\n' % str(ex))


def find_routes_with_times(from_unistop_id, to_unistop_id):
    with ServerProxy(settings.GRAPH_SERVER_PATH) as graph_service:
        try:
            routes = graph_service.find_routes_with_times(from_unistop_id, to_unistop_id)
        except:
            routes = []
    return routes


def find_path(from_unistop_id, to_unistop_id):
    with ServerProxy(settings.GRAPH_SERVER_PATH) as graph_service:
        try:
            paths = graph_service.find_path(from_unistop_id, to_unistop_id)
        except:
            paths = []
    return paths


def day_after_week(city=None):
    if not city:
        return datetime.datetime.utcnow() + datetime.timedelta(days=7)
    return city.now + datetime.timedelta(days=7)


def dictfetchall(cursor, as_dict=False):
    """Return all rows from a cursor as a dict"""
    columns = [col[0] for col in cursor.description]
    if as_dict:
        return {row[0]: dict(zip(columns, row))
                    for row in cursor.fetchall() }
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def dictfetchone(cursor, as_dict=False):
    """Return one row from a cursor as a dict"""
    columns = [col[0] for col in cursor.description]
    if as_dict:
        return dict(zip(columns, cursor.fetchone()))
    return dict(zip(columns, cursor.fetchone()))


def init_curl(crl, url, output, headers=None, timeout=None, use_tls_1_2=True, proxy=None):
    crl.setopt(crl.URL, url)
    if use_tls_1_2:
        crl.setopt(crl.SSLVERSION, crl.SSLVERSION_TLSv1_2)
        crl.setopt(crl.SSL_CIPHER_LIST, "DEFAULT@SECLEVEL=0")
    if proxy:
        proxy_info = urlparse(proxy)
        crl.setopt(crl.PROXY, '{}://{}'.format(proxy_info.scheme, proxy_info.hostname))
        crl.setopt(crl.PROXYPORT, proxy_info.port)
        crl.setopt(crl.PROXYTYPE, crl.PROXYTYPE_SOCKS5 if proxy_info == "socks5" else crl.PROXYTYPE_HTTP)
    if headers:
        crl.setopt(crl.HTTPHEADER, headers)
    if timeout and timeout > 0:
        crl.setopt(crl.TIMEOUT, timeout)
    crl.setopt(crl.WRITEDATA, output)    

def get_gcity_from_ip(ip):
    """
    Returns a `geoip2.models.City` object
    Returns None if there is an exception or the IP is empty.
    https://github.com/maxmind/GeoIP2-python
    """

    if not ip:
        return None
    try:
        with geoip2.database.Reader(
            settings.PROJECT_DIR + '/addons/GeoLite2-City.mmdb') as reader:
            return reader.city(ip)
    except:
        return None


def get_default_register_phone(ip) -> PhoneNumber:
    """
    - Returns defaults using `geoip2.records.Country.is_in_european_union` value
    - True DEFAULT_REGISTER_PHONE_EUROPE (EU)
    - False DEFAULT_REGISTER_PHONE (Non-EU) 
    - If region is empty library reads PHONENUMBER_DEFAULT_REGION ('RU')
    """

    gcity = get_gcity_from_ip(ip)
    def_rp = getattr(settings, "DEFAULT_REGISTER_PHONE", settings.DEFAULT_REGISTER_PHONE)
    region = None

    if gcity:
        region = gcity.country.iso_code
        if  gcity.country.is_in_european_union:
            def_rp = getattr(settings, "DEFAULT_REGISTER_PHONE_EUROPE", settings.DEFAULT_REGISTER_PHONE_EUROPE)

    return PhoneNumber.from_string(def_rp, region)


def get_register_phone(setting) -> PhoneNumber:
    """
    Given an object with a city returns a nationalized register phone.
    If empty for the object provided gets default using the object ip value
    """

    return get_default_register_phone(setting.ip)


def lava_sort_up(lava_x, lava_y):
    if lava_x.get('d') == None:
        return 1
    if lava_y.get('d') == None:
        return -1

    if lava_x['d'] == lava_y['d']:
        return lava_x['order'] - lava_y['order']
    elif lava_x['d'] > lava_y['d']:
        return 1
    else:
        return -1

def datetime_seconds_round_up(dt: datetime.datetime):
    "Return datetime rounded up"
    return dt + datetime.timedelta(seconds=(60 - dt.second) % 60)    

# def nslugify_iterate(value):
#<------>lakmus=re.match('(.+)-(\d+)$',value)
#<------>if lakmus:
#<------><------>return lakmus.groups()[0]+"-"+str(int(lakmus.groups()[1])+1)
#<------>else:
#<------><------>return value+"-1"
