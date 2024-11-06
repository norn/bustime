# -*- coding: utf-8 -*-
"""
После правки этого файла сделать ./1restart
"""
from __future__ import absolute_import
from bustime.models import *
from bustime.views import settings__gps_send_of, is_mat
from django.conf import settings
from django.db.models import Max
from django.db import connections
import os
import random
import requests
import re
import time
import geoip2.database
from django.utils.translation import gettext as _
import reversion
import six
from six.moves import range
from bustime.utils import get_paths_from_busstops, get_register_phone, get_gcity_from_ip
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.measure import D
from django.utils import translation


API_ERRORS = {
    1: "No method name",
    2: "No such method or method import error",
    3: "No such user or password incorrect",
}

def api_error(code, data=None):
    log_message(message=API_ERRORS[code], ttype="api error")
    d = dict(code=code, message=API_ERRORS[code])
    if data:
        d['data'] = data
    return dict(error=d)


def dump_version_():
    return '2016-10-19 15:26:36'

def get_local_ip():
    import socket
    s = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(1)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.settimeout(None)
    except:
        local_ip = socket.gethostbyname(socket.gethostname())
    if s:
        s.close()
    return local_ip


def ads_randomizer(ms):
    if ms.place and ms.place.now.weekday() in [6, 7]:
        is_weekday = True
        pfix = "_weekday"
    else:
        is_weekday = False
        pfix = ""
    if ms.os == "ios":
        ads = get_setting('app_ads_ios%s' % pfix) or []
    else:
        ads = get_setting('app_ads_android%s' % pfix) or []
    if ads and ms.version <= 157:
        ads = [x for x in ads if x.get('native') != True]
    ra = random.random()
    incro = 0
    ads_id, ads_force, ads_native, ads_express = None, None, None, None
    for ad in ads:
        # resistant code
        ads_id, ads_force, ads_native, ads_express = ad.get('id', None), ad.get('force', False), ad.get('native', False), ad.get('express', False)
        if ra >= incro and ra < incro + ad['percent']:
            break
        incro += ad['percent']
    return ads_id, ads_force, ads_native, ads_express


def ads_randomizer_default(ms):
    if ms.os == "ios":
        ads = get_setting('app_ads_ios_default') or []
    else:
        ads = get_setting('app_ads_android_default') or []
    ra = random.random()
    incro = 0
    ads_id = None
    for ad in ads:
        ads_id = ad.get('id')
        if ra >= incro and ra < incro + ad['percent']:
            break
        incro += ad['percent']
    return ads_id


def get_ads_advanced_apps(ms, params=None):
    if not ms.place:
        ads = None
    elif int(ms.version) >= 211 and ms.place.country_code not in ['ru', 'by']:
        ads = get_setting('ads_advanced_apps_int')
    elif int(ms.version) >= 210:
        ads = get_setting('ads_advanced_apps_locman')
    elif int(ms.version) >= 200:
        ads = get_setting('ads_advanced_apps_2')
    else:
        ads = get_setting('ads_advanced_apps')

    i = 0
    delay = 0
    if ads:
        if ms.os == "ios":
            ads = ads['ios']
        else:
            ads = ads['android']

        delay = ads.get('delay')
        ra = random.random()
        incro = 0
        for ad in ads['ads']:
            if ra >= incro and ra < incro + ad['percent']:
                break
            incro += ad['percent']
            i += 1

        # мутная тема
        extra = ads.get('default')
        if ms.os == "android":
            if type(extra) == list:
                ads['ads'] = ads['ads'][0:i+1] + extra + ads['ads'][i+1:]
            else:
                ads['ads'] = ads['ads'][0:i+1] + [extra] + ads['ads'][i+1:]
        elif ms.os == "ios":
            if type(extra) == list:
                ads['ads'] = ads['ads'][0:i+1] + extra + ads['ads'][i+1:]
            else:
                ads['ads'] = ads['ads'][0:i+1] + [extra] + ads['ads'][i+1:]

        retval = {"mobile_ads": ads['ads'], "mobile_ads_index": i, "mobile_ads_delay": delay}
    else:
        retval = {"mobile_ads": ads, "mobile_ads_index": i, "mobile_ads_delay": delay}

    return retval


def dump_city_version_(city, db_base="v4", ms_id=0):
    try:
        statbuf = os.stat('%s/bustime/static/other/db/%s/%s.dump.diff.bz2' % (settings.PROJECT_DIR, db_base, city.id))
        result = datetime.datetime.fromtimestamp(statbuf.st_mtime)
        result = lotime(result)
        diff = lotime(result)
    except:
        if db_base == "v7":
            diff=""
        else:
            return ""

    if db_base == "v7":
        try:
            statbuf = os.stat('%s/bustime/static/other/db/%s/%s.dump.bz2' % (settings.PROJECT_DIR, db_base, city.id))
            result = datetime.datetime.fromtimestamp(statbuf.st_mtime)
            base = str(result.date())
        except:
            base = str(datetime.datetime.now().date())
        return {"base": base, "diff": diff}

    return db_base+" "+result


def db_version(ms, params):
    resp = dict(result=dump_version_())
    return resp

def get_city_version(ms, params):
    city = params.get("city_id", 0)
    db_base = params.get("db_base")
    if city:
        place = PLACE_MAP[int(city)]
    else:
        place = ms.place
    resp = dict(result=dump_city_version_(place, db_base=db_base))
    return resp

def is_ads_enabled(ms):
    if ms.place and ms.place.country_code != 'ru':
        return False
    return True

def citynews_get(ms, params):
    city = params.get("city_id")
    if not city:
        return {}
    now = city.now
    cn = CityNews.objects.filter(place_id=city, etime__gt=now).order_by("-ctime")
    result = {}
    if cn:
        cn = cn[0]
        result['title'] = cn.title
        result['body'] = cn.body
    result = dict(result=result)
    return result


def user_get(ms, params, ip=None):
    def is_secure(ms, params):
        if ms.os == "android":
            if int(params.get("os_version", 0)) == 0:
                return True
            return int(params.get("os_version", ANDROID_OS_VERSION_WITH_SSL)) >= ANDROID_OS_VERSION_WITH_SSL
        return True

    ANDROID_OS_VERSION_WITH_SSL = 25
    db_base = params.get("db_base", 'v2')

    user_get_start = datetime.datetime.now()
    if translation.get_language() != ms.language:
        translation.activate(ms.language)
    if ms.gps_send_approved:
        gps_send_approved = True
    else:
        gps_send_approved = False

    if ms.mode == 2 and not params.get('driver_city'):
        ms.mode = 0
        ms.save()

    pl = Place.objects.filter(id=ms.place_id).first()
    if ms.tcard and pl:
        tcard = tcard_get(ms.tcard, PLACE_TRANSPORT_CARD.get(pl.id)) if ms.tcard else None
        if tcard:
            tcard = {"balance": tcard.balance, "social": tcard.social, "num":tcard.num, "balance_text": tcard.balance_text()}
        else:
            tcard = None
    else:
        tcard = None
    now = datetime.datetime.now()
    user_get_step1 = now

    transaction = None
    ads_enabled = is_ads_enabled(ms) # enabled/disabled ads
    ads_list = []

    flash_msg, diagnostic_msg = None, None
    cc_key = "busamounts_%s" % ms.place_id
    busamounts = len(rcache_get(cc_key, {}).keys())
    if ms.place:
        if not busamounts and ms.place.should_work():
            diagnostic_msg = _(u"Данные, предоставляемые сервером в г.")
            diagnostic_msg += " " + ms.place.name + u", "
            diagnostic_msg += _(u"не актуальны")+u".\n"
            how_long = _(u'неизвестно когда')
            diagnostic_msg += _(u"Последний раз работало") + ": " + how_long
            if (how_long != _(u'неизвестно когда')):
                diagnostic_msg += u" %s.\n " % _(u"назад")
            else:
                diagnostic_msg += u".\n "
            diagnostic_msg += _(u"Мы не виноваты")
            diagnostic_msg += "!" # 🙁
        if (not busamounts and ms.place.should_work() and ms.place.id!=41):
            flash_msg = _(u"Данные общественного транспорта не предоставляются. Город:") + " %s" % ms.place.name

        if ms.place.id < 1000 and CITY_MAP.get(ms.place.id):
          bicity = City.objects.get(id=ms.place.id)
          if bicity.block_info:
              flash_msg = bicity.block_info

        data_sources = ms.place.datasource_set.all()
        for data_source in data_sources:
            if data_source.block_info and ms.place.id != 71:
                flash_msg += data_source.block_info + "\n"

    #сообщение для всех городов
    try:
        message_for_all = Settings.objects.get(key='message_for_all').value
    except:
        message_for_all = None
    if message_for_all:
        flash_msg = message_for_all

    user_get_step2 = datetime.datetime.now()

    ms.ltime = now
    ms.ip = ip
    city_diff = 0

    ms.device_type = params.get("device_type", 0)
    try:
        ms.version = int(re.split(r"[ _]", params.get("version",'0').replace(".",''))[0])
    except:
        ms.version = 0
    ms.arch = params.get("arch")
    if ms.arch: ms.arch = ms.arch[:12]
    ms.startups += 1
    if not ms.ref:
        ms.ref = word_fifo()
    ms.save()
    if ms.version == 0 and ms.os == "android":
        metric('version_0_android')
    elif ms.version == 0 and ms.os == "ios":
        metric('version_0_ios')
    scheme = 'https' if is_secure(ms, params) else 'http'
    url_server = 'https://bustime.loc' if is_secure(ms, params) else 'http://insecure.bustime.loc'

    ads_type = 'admob'
    user_get_step3 = datetime.datetime.now()
    weather = weather_detect(ms.place)
    if not weather or weather in ['clear', 'clouds']:
        if now.month in [4,5]:
            weather = "leaf_green"
        elif now.month in [10,11]:
            weather = "leaf_yellow"

    url_socketio = "http://api.bustime.ru:80"
    if ms.version >= 127:
        if is_secure(ms, params):
            url_socketio = 'https://api.bustime.loc'
        else:
            url_socketio = 'http://insecure.bustime.loc'

    if ms.mode == 2:
        adv = {"full_screen_timer": 0}
    else:
        adv = {"full_screen_timer": 0}

    if ms.os == "ios":
        adv['id'] = 'ads-key'
    else:
        adv['id'] = 'ads-key'
    ads_id, ads_force, ads_native, ads_express = ads_randomizer(ms)
    ads_default = ads_randomizer_default(ms)
    if not ads_id:
        ads_id = ads_default
        ads_force, ads_native, ads_express = False, False, False
    if not ads_default:
        ads_default = ads_id

    holiday = detect_holiday(ms.place)
    sys_help = ms.sys_help
    if ms.place_id == 45:
        sys_help = False

    ads_advanced = get_ads_advanced_apps(ms)
    djuser = {}
    name = ms.name
    if ms.user:
        if ms.name and not ms.user.first_name:
            ms.user.first_name = ms.name
            ms.user.save()
            ms.name = None
            ms.save()
        name = ms.user.first_name
        groups = get_groups(ms.user)
        if ms.user.is_superuser:
            groups.append('editor')
            groups.append('disp')

        # check for city's perms
        if 'editor' in groups and not ms.user.is_superuser:
            if not ms.user in ms.place.editors.all():
                groups.remove('editor')
        if 'disp' in groups and not ms.user.is_superuser:
            all_dispatchers = [data_source.dispatchers.all() for data_source in data_sources]
            if not ms.user in all_dispatchers:
                groups.remove('disp')

        # turn off ads via old
        if 'editor' in groups:
            transaction = {}
            transaction['end_time'] = datetime.datetime.now() + datetime.timedelta(days=90)
            transaction['key'] = "mobile_passenger" #tr.key # mobile_driver, mobile_passenger

        djuser = {"id": ms.user_id, "username": ms.user.username,
                  "date_joined": int(time.mktime(ms.user.date_joined.timetuple())),
                  "active": ms.user.is_active, 'groups': groups}

    db_city_version = dump_city_version_(ms.place, db_base=db_base, ms_id=ms.id)
    avg_jam_ratio = rcache_get('avg_jam_ratio__%s' % ms.place_id) or 0
    url_tile_pbf = {"dark": "https://demotiles.maplibre.org/style.json", "light":"https://demotiles.maplibre.org/style.json"}
    url_tile = 'https://tile.bustime.loc'
    result = {"id": ms.id, "jdata": ms.jdata,
              "city_id": ms.place_id,
              "gps_send": ms.gps_send, "gps_send_of": ms.gps_send_of,
              "gps_send_bus_id": ms.gps_send_bus_id,
              "gosnum": ms.gosnum, "phone": ms.phone,
              "gps_send_ramp": ms.gps_send_ramp,
              "approved_driver": ms.approved_driver,
              "gps_send_approved": ms.approved_driver,
              "name": name,
              "tcard": tcard,
              "db_version": dump_version_(),
              "db_city_version": db_city_version,
              'adgeo': ads_list, 'transaction': transaction,
              "mode":ms.mode,
              "flash_msg":flash_msg,
              "diagnostic_msg":diagnostic_msg,
              "server_url":"ws://bustime.loc:9002/socket/",
              "url_socketio": url_socketio,
              "url_server": url_server,
              "url_tile": url_tile,
              "url_tile_pbf": url_tile_pbf,
              "url_cdn": f'{scheme}://bustime.loc',
              "ads": ads_type, "snow":False,
              "support_email": "support@mail.address",
              "weather": weather,
              "sys_help": sys_help,
              "weather_temp": avg_temp(ms.place),
              "adv": adv,
              "db_version_active": 4,
              "datetime": str(ms.place.now if ms.place else datetime.datetime.now()).split('.')[0],
              "city_now": time.mktime(ms.place.now.timetuple() if ms.place else datetime.datetime.now().timetuple()),
              "city_diff": city_diff,
              "theme_id": ms.theme_id,
              "language": ms.language,
              "holiday": holiday,
              "orator": ms.orator,
              "ads_id": ads_id,
              "ads_force": ads_force,
              "ads_native": ads_native,
              "ads_default": ads_default,
              "ads_express": ads_express,
              "ads_advanced": ads_advanced,
              "user_pin": make_user_pin(ms.id),
              "register_phone": get_register_phone(ms).as_international,
              "djuser": djuser,
              "ban": ms.is_banned() and lotime(ms.ban),
              "new": bool(params.get("created")),
              "avg_jam_ratio": avg_jam_ratio,
              "db_v8_dump_version": pl.dump_version if pl else 0,
              "db_v8_patch_version": pl.patch_version if pl else 0,
              "ads_enabled": ads_enabled
              }

    user_get_step4 = datetime.datetime.now()
    result['ref'] = {"ref": ms.ref, "ref_other": ms.ref_other, "ref_date": lotime(ms.ref_date)}

    if ms.version < 165:
        result['ref'] = {"ref": ms.ref, "ref_other": 0, "ref_date": None}
    if ms.mode == 2:
        result['gps_send_timeout'] = 10  # интервал отправки GPS данных
        result['disp_phone'] = ''  # тел диспетчера
        del result['weather']
    elif ms.version:
        target_version = get_setting('app_production')
        if type(target_version) == dict:
            if ms.os in ["ios", "mac"]:
                target_version = target_version["ios"]
            else :
                target_version = target_version["android"]

    if ms.version > 191:
        busamounts = rcache_get("busamounts_%s" % ms.place_id, {})
        result['busamounts'] = busamounts

    delta = (now - ms.ctime).total_seconds() / 60 # mins
    delta = 60*24*1 - int(delta) # 3 days wo/ads
    if ms.user and ms.user.id == 2262:
        pass
    elif ms.user and 'editor' in groups:
        result["pro_demo"] = 60*24
        result["adv"]['full_screen_timer'] = 0
    elif delta > 0:
        result["pro_demo"] = delta
        result["adv"]['full_screen_timer'] = 0
    elif ms.ref_date and ms.ref_date > ms.place.now:
        result["pro_demo"] = 60*24
        result["adv"]['full_screen_timer'] = 0
    elif ms.user and ms.user.date_joined + datetime.timedelta(days=30) > ms.place.now:
        result["pro_demo"] = 60*24 # turn off ads
        result["adv"]['full_screen_timer'] = 0
    elif ms.version == 170 and ms.os == 'ios':
        result["pro_demo"] = 60*24 # turn off ads
        result["adv"]['full_screen_timer'] = 0

    try:
        gtt = GameTimeTap.objects.get(ms=ms)
        result['score'] = gtt.score
    except:
        pass

    result = dict(result=result)
    user_get_stop = datetime.datetime.now()
    delta = user_get_stop - user_get_start
    if delta.seconds > 1:
        f = open('/tmp/user_get.log', 'a')
        f.write("%s: ms.id=%s, delta=%s\n" % (user_get_stop, ms.id, delta.seconds))
        f.write("%s\n%s\n%s\n%s\n%s\n%s\n\n" % (user_get_start, user_get_step1, user_get_step2, user_get_step3, user_get_step4, user_get_stop))
        f.close()
    return result


def gps_send(ms, params):
    data = {
        "ms_id": ms.id,
        "lon": params["lon"],
        "lat": params["lat"],
        "speed": params["speed"],
        "heading": params["heading"],
        "accuracy": params["accuracy"]
    }
    return dict(result="")


def settings_set(ms, params):
    availables = ['city_id', 'gps_send', 'gps_send_approved',
                  'gps_send_bus_id',
                  'gosnum', 'phone', 'jdata', "gps_send_ramp", "tcard",
                  "gps_send_of", "name", "color",
                  "sys_help", "language", "orator"]

    for k in availables:
        if params.get(k, None) is not None:
            val = params[k]
            if k == "gps_send_bus_id":
                if val:
                    val = bus_get(val)
                    k = "gps_send_bus"
                else:
                    val = None
            elif k == "city_id":
                ms.place = places_get(lang=cur_lang).get(int(val))
                if not ms.place:
                    ms.place = places_get(lang=cur_lang, force=True).get(int(val))
            elif k == "tcard":
                val = val.get('num', "")[:20]
            elif k == "gps_send_approved":
                if val:
                    val = datetime.datetime.now()
                else:
                    val = None
            elif k in ["gosnum", "phone"]:
                val = val[:16]
            elif k == "name":
                val = val[:24].split("@")[0]
                val = val.replace("bustime", "")
                if is_mat(six.text_type(val)):
                    if ms.version > 89:
                        return dict(error=_(u"Ник не сохранён, так как содержит нецензурные слова."))
                    else:
                        val = 'xxx'
                if ms.user:
                    ms.user.first_name = val
                    ms.user.save()

            elif k in ["device_type"]:
                val = int(val)
            elif k == "language":
                oldlang = ms.language
                ms.language = val
                translation.activate(val)
                # _kitchen info
                dat = {"uuid": ms.uuid[0:5], "language":ms.language, "place":str(ms.place), 'ctime':str(ms.ctime.date()), 'version':ms.version, 'os':ms.os}
                if (datetime.datetime.now()-ms.ctime).total_seconds() < 10:
                    action = "language_auto"
                elif oldlang == ms.language:
                    action = "city_change"
                else:
                    action = "settings_language"
                    dat['prev'] = oldlang
                dat['action'] = action
                if action in ['language_auto', 'settings_language']:
                    sio_pub("_kitchen", dat)
            else:
                setattr(ms, k, val)
    ms.save()
    return dict(result=1)


def gosnum_set(ms, params):
    repl = {'error': _(u"FAIL: Deprecated API")}
    return dict(repl)

def adgeo_incr(ms, params):
    id_ = params['id']
    try:
        a = AdGeo.objects.get(id=id_)
    except AdGeo.DoesNotExist as e:
        return dict(result=0)
    a.counter = a.counter + 1
    a.save()
    log_message(ttype="adgeo", message="%s click by %s" % (a.id, ms.id), ms=ms, city=a.city)
    return dict(result=a.counter)

# todo move to rpc
def mobile_metric(ms, params):
    name = params['name']
    result = True
    metric('mobile_%s' % name) # mobile_adgeo_show
    return dict(result=1)


def call_request(ms, params):
    from django.core.mail import send_mail
    log_message(ttype="call_request", message="ms.id=%s" % ms.id)
    send_mail('bustime call request', "ms.id=%s, phone=%s, city=%s, approved=%s" % (ms.id, ms.phone, ms.place.name, ms.approved_driver),
              'noreply@mail.address', ['admin@mail.address'], fail_silently=True)
    return dict(result=1)


def timetap_score(ms, params):
    score = params['score']
    gtt, cr = GameTimeTap.objects.get_or_create(ms=ms)
    if not cr and gtt.score and score < gtt.score:
        pass
    elif score < 5000:
        gtt.score = score
        gtt.save()
    m = GameTimeTap.objects.all().aggregate(Max('score'))
    m = m['score__max']
    ms = GameTimeTap.objects.filter(score=m)[0].ms
    m = {'score':m, 'name':ms.name, 'date': lotime(ms.mtime, lang=ms.language)}
    metric('game_tap')
    return dict(result=m)


def driver_alert(ms, params):
    return dict(result=1)


def message_signal(ms, params):
    return dict(result=1)


def random_word_rus(num=1, max_length=7):
    words = ""
    ua = open('%s/addons/word_rus.txt' % settings.PROJECT_DIR,'r')
    ua = ua.read().splitlines()
    while num > 0:
        word = random.choice(ua)#.decode('utf8')
        if len(word) < max_length:
            words += word
            num -= 1
            if num > 0:
                words += " "
    return words


def word_fifo():
    cc_key = 'word_fifo'
    fname = '%s/addons/word_list_fifo_1.txt' % settings.PROJECT_DIR
    while rcache_get(cc_key):
        time.sleep(0.05)
    rcache_set(cc_key, 1, 2)
    try:
        ua = open(fname, 'r')
        ua = ua.read().splitlines()
        word = ua.pop()
    except:
        ua = []
        word = ""
    if ua:
        f = open(fname, 'w')
        f.write("\n".join(ua))
        f.close()
    rcache_set(cc_key, 0, 2)
    if ua and len(ua) % 10000 == 0:
        bot_txt = "⚠️ осталось %s слов" % len(ua)
    return word


def ref_activate(ms, params):
    ref = params['ref']
    mss = MobileSettings.objects.filter(ref__iexact=ref).exclude(id=ms.id)
    if not mss:
        return dict(result=False)

    ms_ref = mss[0]
    ms.ref_other = ms_ref.id
    if not ms.ref_date or ms.ref_date < ms.city.now:
        ms.ref_date = ms.city.now
    ms.ref_date += datetime.timedelta(days=30)
    ms.save()

    if not ms_ref.ref_date or ms_ref.ref_date < ms_ref.place.now:
        ms_ref.ref_date = ms_ref.place.now
    ms_ref.ref_date += datetime.timedelta(days=30)
    ms_ref.save()

    wsocket_cmd('ads_off', {}, ms_id=ms_ref.id)
    m = {'ref_date': lotime(ms.ref_date), 'ref_other': ms.ref_other}
    return dict(result=m)


def ref_new(ms, params):
    ms.ref = word_fifo()
    ms.save()
    m = {'ref': ms.ref}
    return dict(result=m)


def theme_get(ms, params):
    qs = MoTheme.objects.all()
    id_ = params.get('id')
    if id_:
        qs = qs.filter(id=id_)
    qs = qs.order_by('-counter').values_list('id', 'jdata', 'counter')
    themes = []
    for t in qs:
        themes.append({'id': t[0], 'jdata': json.loads(t[1]), 'counter': t[2]})
    m = {'themes': themes}
    return dict(result=m)

def theme_get_v2(ms, params):
    qs = MoTheme.objects.all()
    id_ = params.get('id')
    if id_:
        qs = qs.filter(id=id_)
    qs = qs.exclude(counter=0).order_by('-counter').values_list('id', 'jdata', 'counter')
    themes = []

    for t in qs:
        jd = json.loads(t[1])
        jd['m'] = jd['yellow']
        jd['t'] = jd['dark_text']
        if jd.get('yellow_icon'):
            del jd["yellow_icon"]
        if jd.get('dark_back'):
            del jd["dark_back"]
        if jd.get('yellow'):
            del jd["yellow"]
        if jd.get('dark_text'):
            del jd["dark_text"]
        themes.append({'id': t[0], 'jdata': jd, 'c': t[2]})

    rethemes = []
    tl = len(themes) - 1
    for i in range(0, tl):
        if i < tl/2+1:
            rethemes.append(themes[i])
            if tl-i > i:
                rethemes.append(themes[tl-i])

    m = {'themes': rethemes}
    return dict(result=m)


def theme_set(ms, params):
    reset = params.get('reset')
    if reset:
        if ms.theme:
            theme = ms.theme
        else:
            theme = None
        ms.theme = None
        ms.save()
        if theme: theme.recount()
        return dict(result={})
    jdata = params['jdata'].strip()
    theme = MoTheme.objects.filter(jdata=jdata)
    if not theme:
        theme = MoTheme.objects.create(jdata=jdata)
    else:
        theme = theme[0]
    if ms.theme:
        theme_old = ms.theme
    else:
        theme_old = None
    ms.theme = theme
    ms.save()
    if theme_old:
        theme_old.recount()
    ms.theme.recount()
    m = {'theme_id': ms.theme_id, 'counter': ms.theme.counter}
    return dict(result=m)


def chat_mark(ms, params):
    chat_id = params.get('chat_id')
    chat_list = Chat.objects.filter(id=int(chat_id))
    if not chat_list:
        return {'chat_id': chat_id, 'warnings': 0}
    chat = chat_list[0]

    if chat.ms and chat.ms.user == ms.user:
        chat.deleted_by = chat.ms.user
        chat.deleted = True
        chat.save()
        fill_chat_cache(chat.bus.id, force=True)
        for place in chat.bus.places.all():
            fill_chat_city_cache(place.id, force=True)
    elif ms.premium and ms.user in ms.place.editors.all():
        # city perm check here
        if ms.user not in ms.place.editors.all():
            return dict(error={"message": u"not editor in city"})
        chats = block_and_delete(chat.us, chat.ms, ms.user)
        for chat in chats:
            fill_chat_cache(chat.bus.id, force=True)
            for place in chat.bus.places.all():
                fill_chat_city_cache(place.id, force=True)
    else:
        if not chat.warnings:
            chat.warnings = []
        else:
            chat.warnings = json.loads(chat.warnings)
        chat.warnings.append(ms.id)
        chat.warnings = list(set(chat.warnings))
        chat.warnings_count = len(chat.warnings)
        chat.warnings = json.dumps(chat.warnings)
        chat.save()

    m = {'chat_id': chat.id, 'warnings': chat.warnings_count} # c.warnings
    return dict(result=m)

# Получить маршрут с пересадками из точки point_from в точку point_to
def get_bus_trip(ms, params):
    point_from = params['point_from']
    point_to = params['point_to']
    p1 = Point(point_from[0], point_from[1])
    p2 = Point(point_to[0], point_to[1])
    stop_from = NBusStop.objects.filter(Q(point__distance_lte=(p1, D(km=100)))).annotate(distance=Distance('point', p1)).order_by('distance')[0]
    stop_to = NBusStop.objects.filter(Q(point__distance_lte=(p2, D(km=100)))).annotate(distance=Distance('point', p2)).order_by('distance')[0]
    city = ms.city
    di_graph = REDIS.get("nx__di_graph__%s" % city.id)
    if not di_graph:
        return dict(result=[])
    G = pickle.loads(di_graph)

    m = []
    paths = nx.all_shortest_paths(G, stop_from.name, stop_to.name, weight='weight')

    for path in paths:
        result = []
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
                    index = tail.index(item) + 1
                head, tail = tail[index], tail[index+1:]
            # Нити маршрутов мобилка посторит сама, нам нужны только начальная -> конечная остановки. 
            # Но для поиска времени в пути и дистанции нужен графхоппер
            elif isinstance(head, RouteNode):
                nbusstop_id, name, direction, bus = head
                item = next((x for x in tail if not isinstance(x, RouteNode)), None)
                index = tail.index(item)
                item = tail[index - 1]
                route_stops = [head]
                route_stops.extend(tail[:index])
                bus_stops = [stops[stop.name] for stop in route_stops]
                path = get_paths_from_busstops(bus_stops)[0]
                result.append({"type":"bus", "bus_id": bus, "direction": direction, "distance": path['distance'], "time": path['time'], "stop_start": head.busstop_id, "stop_end": item.busstop_id})
                head, tail = tail[index], tail[index+1:]
            # Считаем маршруты пешком через графхоппер
            elif isinstance(head, str) and isinstance(tail[0], str):
                path = get_paths_from_busstops([stops[head], stops[tail[0]]])[0]
                points = path['points']
                line = points['coordinates']
                result.append({"type":"foot", "distance": path['distance'], "time": path['time'], "line": line})
                head, *tail = tail
            else:
                head, *tail = tail
        m.append(result)
    return dict(result=m)

def get_jam(ms, params):
    # {"id":-1824821393,"jsonrpc":"2.0","method":"get_jam","params":{"bus_ids":[3338],"ms_id":1072920,"uuid":"E3ED4ECA-A947-511D-93DD-33B42937BA3B"}}
    bus_ids = params.get('bus_ids')
    if not bus_ids:
        bus_ids = list(Bus.objects.filter(places=ms.place).values_list('id', flat=True))
    busstops = list(Route.objects.filter(bus_id__in=bus_ids).values_list('busstop_id', flat=True).distinct())

    # пары остановок берём из кэша (см. coroutines/jam.py)
    cc_key = "jam__%s" % ms.place.id
    jam = rcache_get(cc_key) or []
    m = []
    for j in jam:
        j0 = int(j[0])
        j1 = int(j[1])
        if j0 in busstops and j1 in busstops:
            m.append({
                'busstop_from': j0,
                'busstop_to': j1,
                'average_time': j[2],
                'ratio': j[3],
            })
    # for j in jam
    return dict(result=m)
# def get_jam
