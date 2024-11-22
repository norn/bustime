#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
После правки этого файла выполнить:
sudo supervisorctl restart bustime_rpc_servers:*
Проверка:
sudo supervisorctl status bustime_rpc_servers:*
'''
from __future__ import absolute_import
from __future__ import print_function
from devinclude import *
from bustime.models import *
from bustime.inject_events import *
import reversion
from bustime.views import (bus_last_f,
                           ajax_stop_id_f,
                           gosnum_set_py, is_mat,
                           monitor_counters,
                           get_busamounts)
import zerorpc
import ujson
import logging
import pprint
import hashlib
from subprocess import call
import time
import datetime
from django.utils.translation import gettext as _
from django.utils import  translation
import argparse
from sorl.thumbnail import ImageField, get_thumbnail
import traceback
import six
from collections import defaultdict


class PrintHandler(logging.Handler):
    def emit(self, record):
        print(record)


h = PrintHandler()
logging.getLogger("zerorpc.channel").addHandler(h)
logging.getLogger("zerorpc.core").addHandler(h)
logging.getLogger("zerorpc.gevent_zmq").addHandler(h)


def post_rating_to_chat(vote, user, vdict):
    # auto post to chat
    if not vote.stars:
        if vote.positive:
            stars = 5
        else:
            stars = 1
    else:
        stars = vote.stars

    user_name = _(u"Аноним") if not user or not user.user \
                        else user.user.first_name

    chat = Chat(message=vote.comment,
                bus=vote.vehicle.bus,
                ctime=vote.vehicle.bus.city.now,
                color=vote.user.color or None,
                name=u"%s★ %s, %s %s [%s]" % (
                    stars,
                    user_name,
                    vote.vehicle.bus.ttype_name() or u"",
                    vote.vehicle.bus.name or u"",
                    vote.vehicle.gosnum.upper(),
                ),
                **vdict)

    extra = {}
    if vote.photo:
        chat.photo = six.text_type(vote.photo.url)
        chat.photo_thumbnail = six.text_type(get_thumbnail(vote.photo, '427x320', quality=70).url)
    chat.save()

    msg = chat_format_msg(chat, lang=vote.user.lang)
    msgb = chat_format_msg(chat, extra={"bus_id": chat.bus_id}, lang=vote.user.lang)

    # cache regen
    fill_chat_cache(vote.vehicle.bus.id, force=True, lang=vote.user.lang)
    for place in chat.bus.places.all():
        fill_chat_city_cache(place.id, force=True, lang=vote.user.lang)
        sio_pub("ru.bustime.chat_city__%s" %
                (place.id), {"chat": msgb})
    sio_pub("ru.bustime.chat__%s" %
            (vote.vehicle.bus.id), {"chat": msg})


def pro_data(data):
    data = ujson.loads(data)
    us_id = data.get('us_id')
    ms_id = data.get('ms_id')
    if ms_id:
        ms = ms_get(ms_id)
        user = ms
        vdict = {"ms": ms}
    elif us_id:
        us = us_get(us_id)
        user = us
        vdict = {"us": us}
    else:
        user = None
        vdict = None
    return data, user, vdict


def vehicle_get(bus, gosnum):
    if not gosnum:
        return None
    vehicle, cr = Vehicle1.objects.get_or_create(bus=bus, gosnum=gosnum)
    return vehicle


def human_time(updated, city=None):
    updated += datetime.timedelta(hours=city.timediffk)
    updated = six.text_type(updated).split('.')[0]
    updated = updated.split(' ')[1]
    return updated


class Gloria(object):

    def rpc_bdata(self, bus_id, mode, mobile):
        def bus_turbo_mode1(bus_id):
            bdata_mode1 = defaultdict(list)
            pipe = REDIS.pipeline()
            bids = rel_buses_get(bus_id)
            for bid in bids:
                pipe.smembers(f"bus__{bid}")
            uids = [uid.decode("utf8") for ids in pipe.execute() for uid in ids]
            to_get = [f'event_{uid}' for uid in uids]
            R = {}
            for bid in bids:
                R[bid] = {r['id']: r for r in city_routes_get_turbo(bid)}

            for e in rcache_mget(to_get):
                if not e:
                    continue
                if e.get('bus_id') != bus_id:
                    continue
                if e.zombie:
                    ee = Event(e.copy())
                    ee["busstop_nearest"] = None
                    lava = ee.get_lava()
                else:
                    lava = e.get_lava()

                if e.get('busstop_nearest') and not e.zombie and not e.away and not e.sleeping:
                    if not R.get(e.bus_id) or not R.get(e.bus_id, {}).get(e['busstop_nearest']):
                        return {}
                    stop_id = R[e.bus_id][e['busstop_nearest']]['busstop_id']
                    mode1bus = {"id": e.bus_id}
                    mode1bus.update(lava)
                    bdata_mode1[stop_id].append(mode1bus)

            tosend = {}
            for bid in bids:
                for r in R[bid].values():
                    sid = r['busstop_id']
                    zs = bdata_mode1.get(sid, [])
                    if zs:
                        tosend[sid] = zs
            return tosend


        serialized = {}
        bus_id = int(bus_id)
        mode = int(mode)
        mobile = int(mobile)
        if mode == 0:
            bus = bus_get(bus_id)
            if mobile:
                mobile = True
            else:
                mobile = False
            serialized = bus_last_f(bus, raw=True, mobile=mobile)   # in models.py
            time_bst = serialized.get("time_bst", {})
            ntb = {}
            for k, v in time_bst.items():
                ntb[k] = u"%s" % v
            serialized['time_bst'] = ntb
        elif mode == 1:
            bus = bus_get(bus_id)
            if not bus.turbo:
                serialized = rcache_get("bdata_mode1_%s" % bus_id, {})
                serialized = {"bdata_mode1": serialized, "bus_id": bus_id}
            else: # turbo mode
                serialized = bus_turbo_mode1(bus_id)
                serialized = {"bdata_mode1": serialized, "bus_id": bus_id}
        elif mode == 10:  # mobile only bdata_mode0 minimized
            bus = bus_get(bus_id)
            serialized = bus_last_f(bus, raw=True, mobile=True, mode=10)
        elif mode == 11:
            bus = bus_get(bus_id)
            if not bus:
                return {}
            if not bus.turbo:
                serialized = rcache_get("bdata_mode1_%s" % bus_id, {})
            else:
                serialized = bus_turbo_mode1(bus_id)
            for k, v in serialized.items():
                for vv in v:
                    if vv.get('bn'):
                        del vv['bn']
                        del vv['order']
                    if 'l' in vv:
                        vv['l'] = str(vv['l']).strip('"[]{}()*=.,:;_&?^%$#@!').strip()
            serialized = {"bdata_mode11": serialized, "bus_id": bus_id}
        elif mode == 12:
            bus = bus_get(bus_id)
            serialized = bus_last_f(bus, raw=True, mobile=True, mode=10)
            serialized = {'bdata_mode12': serialized}
        return serialized

    def rpc_bootstrap_amounts(self, place_id):
        place = Place.objects.get(id=place_id)
        buses = buses_get(place)
        return {"busamounts": get_busamounts([b.id for b in buses])}

    def rpc_passenger(self, data):
        data, user, vdict = pro_data(data)
        if not user:
            return
        what = data['what']
        r_id = data['r_id']
        bus_id = data['bus_id']

        pi = pickle_dumps({"cmd": "passenger", "user_id":user.id, "r_id": r_id})
        REDIS_W.publish(f"turbo_{bus_id}", pi)

    def rpc_tcard(self, data):
        from bustime import tcards as tc
        if data:
            data, user, vdict = pro_data(data)
        tcard_num = data.get('tcard_num', "")
        tcard_num = str(tcard_num)[:20]
        serialized = {}

        if not tcard_num:
            return serialized

        try:
            if not tcards and user:
                provider = PLACE_TRANSPORT_CARD.get(user.place.id)
                if provider:
                    tcard = Tcard.objects.create(
                        num=tcard_num, updated=datetime.datetime(2014, 0o2, 11), provider=provider)
            else:
                tcard = tcards[0]
            tc.tcard_update(tcard, tcard.provider)
            serialized["balance"] = tcard.balance
            if tcard.social:
                s = 1
            else:
                s = 0
            serialized["social"] = s
            serialized["balance_text"] =tcard.balance_text()
            print((tcard.response_raw))
        except:
            tcard = None
        return serialized

    def rpc_stop_ids(self, ids, mobile):
        serialized = ajax_stop_id_f(ids, raw=True, mobile=mobile)
        return serialized

    def rpc_mobile_bootstrap(self, data=None):
        place_id = None
        if data:
            data, user, vdict = pro_data(data)
            place_id = data.get("city_id")
            if not place_id and user and user.place:
                place_id=user.place.id

        '''
        ostapos 20.11.20 12.07:
        сделай в ответ на rpc_mobile_bootstrap возврат пустого specialicons
        '''
        data = {
            "specialicons": {}  #specialicons_cget(as_dict=1, city_id=city_id),
        }
        return data

    '''
    get list of bus icons for city
    data: { ms_id: ..., us_id: ..., city_id ... }
    at least one field MUST be!
    '''
    def rpc_get_city_icons(self, data=None):
        place_id = None
        if data:
            data, user, vdict = pro_data(data)
            place_id = data.get("city_id")
            if not place_id and user and user.place:
                place_id=user.place.id

        data = {
            "specialicons": specialicons_cget(as_dict=1, place_id=place_id),
        }
        return data

    def rpc_gps_send(self, data):
        if not data.get('channel'):
            data['channel'] = 'rpc_gps_send'
        if not data.get('src'):
            if data.get('us_id'):
                data['src'] = "us %s" % data.get('us_id')
            elif data.get('ms_id'):
                data['src'] = "ms %s" % data.get('ms_id')

        cnt, odometer = inject_custom(data) # in bustime/inject_events.py
        odometer = odometer/1000
        return {'cnt': cnt, 'odometer': odometer}

    def rpc_download(self, data):
        data, user, vdict = pro_data(data)
        body = data["body"]
        link = data["link"]
        headers = data.get("headers")
        if user.version >= 93:
            body = aes_dec(body, user.uuid)
            link = aes_dec(link, user.uuid)
            if headers:
                headers = aes_dec(headers, user.uuid)
        response = data.get("response")
        now = str(datetime.datetime.now())
        print(link)
        try:
            link = link.encode('utf8')
        except:
            pass
        print("LINK@ %s" % link)
        m = hashlib.md5(link).hexdigest()[:10]
        cc_key = "download_%s_%s" % (user.id, m)
        print(cc_key)
        rcache_set(cc_key, {
                   "link": link, "body": body, 'rpc_date': now,
                   "response": response, 'date': data.get("date"), 'headers': headers}, 60)
        return {'result': 1}

    def rpc_buses_by_radius(self, city_id, x, y, buses, radius):
        pipe = REDIS.pipeline()
        place = PLACE_MAP[city_id]
        uids = [pipe.smembers(f"bus__{b.id}") for b in buses_get(place)]
        uids = [f"event_{uid.decode('utf8')}" for uids in pipe.execute() for uid in uids]
        allevents = {u['uniqueid']: u for u in rcache_mget(uids) if u is not None}

        serialized = []
        for k, e in allevents.items():
            add_buses = False
            add_radius = False

            if radius:
                d = distance_meters(x, y, e.x, e.y)
                if d < radius:
                    add_radius = True
            else:
                add_radius = True

            if buses:
                if e.bus_id in buses:
                    add_buses = True
            else:
                add_buses = True

            if add_buses and add_radius:
                serialized.append(e.as_mobile())
        serialized = {"buses_by_radius": serialized}
        return serialized

    def rpc_buses_by_radius_v2(self, city_id, x, y, buses, radius):
        pipe = REDIS.pipeline()
        place = PLACE_MAP[city_id]
        uids = [pipe.smembers(f"bus__{b.id}") for b in buses_get(place)]
        uids = [f"event_{uid.decode('utf8')}" for uids in pipe.execute() for uid in uids]
        allevents = {u['uniqueid']: u for u in rcache_mget(uids) if u is not None}

        serialized = []

        for k, e in allevents.items():
            add_buses = False
            add_radius = False

            if radius:
                d = distance_meters(x, y, e.x, e.y)
                if d < radius:
                    add_radius = True
            else:
                add_radius = True

            if buses:
                if e.bus_id in buses:
                    add_buses = True
            else:
                add_buses = True

            if add_buses and add_radius:
                serialized.append(e.as_mobile_v2())
        # for k, e in allevents.items

        serialized = {"buses_by_radius_v2": serialized}

        return serialized

    def rpc_city_monitor(self, city_id, sess, x, y, bus_name, bus_id, nb_id, nb_name, mob_os):
        place_id = city_id
        now = datetime.datetime.now()
        place = places_get(lang='en')[place_id]
        psess = ("%s%s" % (sess, eday_password())).encode('ascii')
        psess = (b64encode(hashlib.sha256(psess).digest(), b"-_")[:8]).decode('ascii')
        pdata = {
            "time": human_time(now, city=place),
            "sess": psess,
            "lon": x,
            "lat": y,
            "accuracy": 15,
            "bus_name": bus_name,
            "bus_id": bus_id,
            "nb_id": nb_id,
            "nb_name": nb_name,
            "os": mob_os}
        data = {"passenger_monitor": pdata}


        if mob_os == "android":
            os_id = 1
        elif mob_os == "ios":
            os_id = 2
        else:
            os_id = 7

        nb_name = force_str(nb_name)
        bus_name = force_str(bus_name)
        PassengerStat.objects.using('bstore').create(psess=psess, city=place.id, lon=x, lat=y,
                                     bus_name=bus_name[:6], nb_name=nb_name[:32], nb_id=nb_id, os=os_id)
        sio_pub("ru.bustime.city_monitor__%s" % (place_id), data)
        if bus_id:
            sio_pub("ru.bustime.bus_mode0__%s" % (bus_id), data)

    def rpc_rating_get(self, data):
        data, user, vdict = pro_data(data)
        if not user:
            return {}
        bus_id = int(data['bus_id'])
        g = data.get('g')
        page = data.get('page', 0)
        if not g:
            return {"rpc_rating_get": {"error": "no gosnum"}}
        bus = bus_get(bus_id)
        now = bus.places.first().now
        vehicle = vehicle_get(bus, g)
        serialized = {
            'gosnum': vehicle.gosnum,
            'driver_ava': vehicle.driver_ava,
            'rating_wilson': vehicle.rating_wilson_human,
            'votes_wilson': vehicle.votes_wilson,
            'comments_count': vehicle.comments,
            'rating_position': vehicle.rating_position,
        }
        comments = []
        for vote in Vote.objects.filter(vehicle=vehicle).order_by('-ctime')[page*10:(page+1)*10]:
            comments.append(vote.as_dict())
        comments.reverse()
        serialized['comments'] = comments
        votes = Vote.objects.filter(
            vehicle=vehicle, **vdict).order_by('-ctime')[:1]
        for v in votes:
            serialized['myvote'] = v.as_dict()
            serialized['myvote_id'] = v.id
            serialized['myvote_ctime'] = lotime(v.ctime, lang=user.lang)
            serialized['myvote_positive'] = v.positive
            serialized['stars'] = v.stars
            serialized['myvote_comment'] = v.comment
            serialized['myvote_name'] = v.name
        serialized = {"rpc_rating_get": serialized}
        return serialized

    def rpc_rating_set(self, data):
        data, user, vdict = pro_data(data)
        if not user or not user.user:
            return {"rpc_rating_set": {"error": _(u"Ошибка: необходима регистрация")}}
        bus_id = int(data['bus_id'])
        g = data.get('g')
        if not g:
            return {"error": "no gosnum"}
        comment = data.get('comment')
        now = user.place.now
        for_date = now.date()
        bus = bus_get(bus_id)
        if user.is_banned():
            repl = {"rpc_rating_set": {"error": u"Ошибка: отзывы запрещены до %s, причина: нецензурные слова" % lotime(user.ban)}}
            return repl
        if is_mat(six.text_type(comment), src=u"отзыв для %s, %s %s" % (bus.places.first(), bus, g)):
            return {"rpc_rating_set": {"error": _(u"Ошибка: нецензурная лексика")}}
        vehicle = vehicle_get(bus, g)
        if not vehicle:
            return {"rpc_rating_set": {"error": "no gosnum"}}
        rate = data.get('rate')
        photo = data.get('photo')
        if rate in ["1", 1]:
            rate = True
        else:
            rate = False
        stars = data.get('stars')
        if stars:
            stars = int(stars)

        vote = Vote.objects.filter(vehicle=vehicle, **vdict)
        if not vote:
            vdict_ = dict(vdict)
            vdict_['comment'] = comment[:200]
            vdict_['stars'] = stars
            vdict_['positive'] = rate
            vdict_['name']= _(u"Аноним") if not user or not user.user \
                        else user.user.first_name
            if user.color:
                vdict_['color'] = user.color
            vote = Vote.objects.create(vehicle=vehicle, ctime=now, **vdict_)
        else:
            vote = vote[0]
            vote.comment = comment[:200]
            vote.positive = rate
            vote.stars = stars
            vote.name = _(u"Аноним") if not user or not user.user \
                        else user.user.first_name
            if user.color:
                vote.color = user.color
            vote.save()

        vehicle = vehicle_get(bus, g)
        serialized = {
            'id': vote.id,
            'rating_wilson': vehicle.rating_wilson_human,
            'rate': rate,
            'stars': stars,
            'gosnum': g
        }
        sio_pub("ru.bustime.bus_mode0__%s" %
                (bus_id), {"rating_set": serialized})

        user_str = "%s, %s" % (user.tell_id(), user.name)
        t = u"%s, %s %s, %s:\n✏ " % (
            bus.id, bus.ttype_name(), bus.name, user_str)
        if stars:
            t += u'*' * stars
        else:
            if rate:
                t += _(u'позитивно')
            else:
                t += _(u'негативно')
        t += ": %s" % vote.comment
        REDIS_W.publish('_bot', t)
        if not photo:
            post_rating_to_chat(vote, user, vdict)

        return {"rpc_rating_set": serialized}

    def rpc_gosnum_set(self, data):
        data, user, vdict = pro_data(data)

        city_id = data['city_id']
        uniqueid = data['uniqueid']
        gosnum = data['gosnum']
        place = places_get()[int(city_id)]
        gresult = gosnum_set_py(place, uniqueid, gosnum, **vdict)    # in views.py
        f = open('/tmp/gosnum_set','a')
        f.write('rpc %s %s %s\n' % (city_id, uniqueid, gosnum))
        f.close()
        return {"rpc_gosnum_set": gresult}

    def rpc_chat_get(self, data):
        data, user, vdict = pro_data(data)
        if user:
            lang = user.language
        else:
            lang = "ru"
        bus_id = data.get('bus_id')
        city_id = data.get('city_id')
        page = data.get('page', 0)
        if page:
            page = int(page)
            history = []
            qs = Chat.objects.filter(deleted=False)
            if bus_id:
                qs = qs.filter(bus__id=bus_id)
            elif city_id:
                qs = qs.filter(bus__city_id=city_id)
            qs = qs.order_by("-ctime")[30*page:30*(page+1)]
            for chat in qs:
                if bus_id:
                    msg = chat_format_msg(chat, lang=lang)
                elif city_id:
                    msg = chat_format_msg(chat, extra={"bus_id": chat.bus_id}, lang=lang)
                history.insert(0, msg)
        else:
            if bus_id:
                history = fill_chat_cache(bus_id, lang=lang)
                bus = bus_get(bus_id)
                if bus:
                    metric('rpc_chat_bus_%s' % bus.city_id)
            elif city_id:
                history = fill_chat_city_cache(city_id, lang=lang)
                metric('rpc_chat_city_%s' % city_id)

        if bus_id:
            online = REDISU.get("ru.bustime.chat__%s_cnt" % bus_id)
        elif city_id:
            online = REDISU.get("ru.bustime.chat_city__%s_cnt" % city_id)

        if online is None:
            online = 0
        else:
            online = int(online)

        serialized = {"history": history, "online": online}
        if bus_id:
            serialized["bus_id"] = bus_id
        elif city_id:
            serialized["city_id"] = city_id
        return {"rpc_chat_get": serialized}

    def rpc_chat(self, data):
        data, user, vdict = pro_data(data)
        message, bus_id = data['message'], data['bus_id']
        if user and user.user and user.user.first_name:
            vdict['name'] = user.user.first_name
        elif user.name:
            vdict['name'] = user.name
        else:
            vdict['name'] = 'Anonimous'

        try:
            if isinstance(user, MobileSettings):
                vdict["color"] = user.color

            bus = bus_get(bus_id)
            if is_mat(force_str(message), src=u"чат для %s, %s" % (bus.city.name, bus)):
                if not user.ban or user.ban < datetime.datetime.now():
                    user.ban = datetime.datetime.now() + datetime.timedelta(days=3)
                    user.save()

            if user.ban and user.ban > datetime.datetime.now():
                translation.activate(user.l)
                s = _(u'Ваш аккаунт заблокирован в чате за нарушение правил до:')
                s += u" %s" % lotime(user.ban, lang=user.language)
                return {"rpc_chat": {'error': s}}
            
            chat = Chat.objects.create(message=message, bus=bus, **vdict)
            msg = chat_format_msg(chat)
            msgb = chat_format_msg(chat, extra={"bus_id": chat.bus_id})
            print(user)
            if user.user:
                print(user.user)

            fill_chat_cache(bus_id, force=True)
            fill_chat_city_cache(bus.city_id, force=True)

            sio_pub("ru.bustime.chat__%s" % (bus_id), {"chat": msg})
            sio_pub("ru.bustime.chat_city__%s" % (bus.city_id), {"chat": msgb})

            user_str = "%s, %s" % (user.tell_id(), user.name)
            t = u"%s, %s %s, %s:\n💬 %s" % (
                bus.city.name, bus.ttype_name(), bus.name, user_str, message)
            REDIS_W.publish('_bot', t)
        except Exception as e:
            log_message("rpc_chat: %s" % str(e), ttype="rpc_chat", user=user, city=(user.city if user else None))

        return {"rpc_chat": {}}

    def rpc_like(self, data):
        data, user, vdict = pro_data(data)
        like = data['like']  # 0 or r 1
        model_ = data['model']  # 'vote'
        object_id = data['id']
        vdict['content_type'] = ContentType.objects.get(model=model_)
        vdict['object_id'] = object_id
        like_obj, cr = Like.objects.get_or_create(**vdict)
        if like_obj.like != like:
            like_obj.like = like
            like_obj.save()
        l, d = like_obj.get_likes()
        user_str = "%s, %s" % (user.tell_id(), user.name)
        if like:
            like_str = u"👍"
        else:
            like_str = u"👎"
        city= like_obj.content_object.vehicle.bus.city
        t = u"%s %s id=%s %s (%s, %s)" % (user_str, like_str, object_id, like_obj.content_object.comment, like_obj.content_object, city.name)
        REDIS_W.publish('_bot', t)

        return {"rpc_like": {'likes': l, 'dislikes': d, 'model': model_, 'id': object_id}}

    def rpc_radio(self, data):
        data, user, vdict = pro_data(data)
        owner = list(vdict.keys())[0]
        sound = data['sound']
        city_id = data['city_id']
        sound = b64decode(sound)
        fname = '%s-%s-%s' % (int(time.time()), owner, user.id)
        fname_path = '%s/sounds/radio/%s' % (settings.PROJECT_ROOT, fname)
        with open("%s.mp4" % fname_path, 'wb+') as destination:
            destination.write(sound)

        opus = ['-codec:a', 'libopus', '-b:a', '16k', '-vbr', 'on',
                '-compression_level', '10', "%s.ogg" % fname_path]
        mp3 = ["-codec:a", "libmp3lame", "-qscale:a", "7",
               "-ac", "1", "-r", "22050", "%s.mp3" % fname_path]
        aac = ['-c:a', 'libfdk_aac', '-b:a', '16k', "%s.mp4" % fname_path]
        call(["ffmpeg", "-i", "%s.mp4" % fname_path] + opus)

        sio_pub("ru.bustime.radio__%s" % (city_id), {
                "radio": {"%s_id" % owner: user.id, "filename": fname}})
        return {"rpc_radio": {'result': 1}}

    def rpc_upload(self, data):
        data, user, vdict = pro_data(data)
        owner = list(vdict.keys())[0]
        file = data['file']
        content_type = data['content_type']
        content_id = data['content_id']
        file = b64decode(file)
        if content_type == 'vote':
            from django.core.files.images import ImageFile
            fname_path = '%s/vote/%s.jpg' % (settings.MEDIA_ROOT,
                                                     content_id)
            with open(fname_path, 'wb+') as destination:
                destination.write(file)
            vote = Vote.objects.get(id=content_id)
            vote.photo = ImageFile(open(fname_path, "rb"), name="{}.jpg".format(content_id))
            vote.save()
            post_rating_to_chat(vote, user, vdict)
            user_str = "%s, %s" % (user.tell_id(), user.name)
            t = u"%s загрузил фото %s" % (user_str, vote.photo.url)
            REDIS_W.publish('_bot', t)
        return {"rpc_upload": {'result': 1}}

    def rpc_set_my_bus(self, data):
        data, user, vdict = pro_data(data)
        owner = list(vdict.keys())[0]
        uniqueid = data['uniqueid']
        bus_id = data['bus_id']
        gosnum = data['gosnum']

        bus = bus_get(bus_id)
        user.gps_send_bus = bus
        user.gosnum = gosnum
        user.gps_send_of = uniqueid
        user.save()

        data = {'gosnum': user.gosnum,
                'bus_id': user.gps_send_bus.id,
                }
        wsocket_cmd('driver_data', data, ms_id=user.id)

        return {"rpc_set_my_bus": {'result': 1}}

    def rpc_status_server(self):
        status_server = rcache_get('status_server')
        if status_server:
            status_server['uptime'] = six.text_type(status_server['uptime'])
        return {"status_server": status_server}

    def rpc_city_error(self, place_id):
        cc_key = 'error_%s' % place_id
        error_update = rcache_get(cc_key, {})
        if error_update:
            if error_update.get('lasts'):
                del error_update['lasts']
            error_update['good_time'] = ''#c.good_time
            for k, v in error_update.items():
                if type(v) == datetime.datetime:
                    error_update[k] = six.text_type(v).split('.')[0]
        error_update['nearest_cnt'] = sum(rcache_get("busamounts_%s" % place_id, {}).values())
        return {"city_error": error_update}

    def rpc_status_counter(self, city_id):
        place = PLACE_MAP[int(city_id)]
        city_monitor = monitor_counters(place)
        if city_monitor:
            city_monitor = city_monitor[0]
        return {"status_counter": city_monitor}

    # Редактирование перевозчика
    def rpc_provider(self, data):
        data, user, vdict = pro_data(data)
        logo_size = '300x300'
        logo_quality = 70
        try:
            data = data.get("provider", {})
            len_data = len(data)

            if len_data == 1:   # get provider by id
                provider = None
                provider_id = int(data.get("id", '0'))
                provider = BusProvider.objects.filter(id=provider_id)
                if provider:
                    provider = provider[0]
                    retval = {"rpc_provider": {"status": u"OK",
                                            "id": provider.id,
                                            "name": provider.name,
                                            "address": provider.address if provider.address else u'',
                                            "phone": provider.phone if provider.phone else u'',
                                            "email": provider.email if provider.email else u'',
                                            "www": provider.www if provider.www else u'',
                                            "ctime": int(provider.ctime.strftime("%s")),
                                            "mtime": int(provider.mtime.strftime("%s")),
                                            "logo": six.text_type(get_thumbnail(provider.logo, logo_size, quality=logo_quality).url) if provider.logo else u'',
                                            }}
                else:
                    retval = {"rpc_provider": {"status": u"Перевозчик не найден"}}
            elif user.is_banned():
                retval = {"rpc_provider":
                    {"status": u"Редактирование провайдеров запрещено до %s, причина: нецензурные слова"}
                }
            elif len_data > 1:  # update or create provider
                provider = None
                provider_id = int(data.get("id", '0'))
                if provider_id: # update
                    provider = BusProvider.objects.filter(id=provider_id).first()
                    if provider:
                        modify_allowed = False
                        for p in provider.places:
                            modify_allowed = is_place_modify_allowed(p, user)
                            if modify_allowed:
                                break
                        # for p in provider.places
                        if not modify_allowed:
                            retval = {
                                "rpc_provider":
                                    {'status': u"Только редакторы и администраторы могут изменять связанную с городом информацию"}
                            }
                        else:
                            comment = None
                            with reversion.create_revision():
                                update_fields = []
                                for key, val in data.items():
                                    if key not in ["id", "ctime", "mtime", "city_id"]:
                                        if not comment: comment = _("Изменен перевозчик: ")
                                        comment += "{} [{} -> {}] \n".format(getattr(BusProvider, key).field.verbose_name, getattr(provider, key), val)
                                        setattr(provider, key, val)
                                        update_fields.append(key)
                                # for key, val in data.items()
                                provider.save(update_fields=update_fields)
                                if user:
                                    if getattr(user, 'user', None):
                                        reversion.set_user(user.user)
                                    else:
                                        reversion.set_user(user)
                                if comment:
                                    reversion.set_comment(comment)

                            # reread
                            provider = BusProvider.objects.get(id=provider_id)
                            # and return
                            retval = {"rpc_provider": {"status": u"OK",
                                                    "id": provider.id,
                                                    "city_id": 0,
                                                    "name": provider.name,
                                                    "address": provider.address if provider.address else u'',
                                                    "phone": provider.phone if provider.phone else u'',
                                                    "email": provider.email if provider.email else u'',
                                                    "www": provider.www if provider.www else u'',
                                                    "ctime": int(provider.ctime.strftime("%s")),
                                                    "mtime": int(provider.mtime.strftime("%s")),
                                                    "logo": six.text_type(get_thumbnail(provider.logo, logo_size, quality=logo_quality).url) if provider.logo else u'',
                                                    }}
                        # else if not modify_allowed
                    # if provider
                    else:
                        retval = {"rpc_provider": {"status": u"Перевозчик не найден"}}
                    # else if provider
                # if provider_id
                else:   # create
                    name = data.get("name").replace('--', '').replace('..', '').replace('..', '')
                    if not name or len(name) < 2 or name in ['-', '.', '.']:
                        retval = {"rpc_provider": {"status": u"Невозможно создать перевозчика без имени"}}
                    elif BusProvider.objects.filter(name=name).first():
                        retval = {"rpc_provider": {"status": u"Такой перевозчик уже есть"}}
                    else:
                        with reversion.create_revision():
                            comment = _("Добавлен перевозчик: ")
                            provider = BusProvider.objects.create(name=name)
                            update_fields = []
                            for key, val in data.items():
                                if key not in ["id", "name", "ctime", "mtime", "city_id"]:
                                    setattr(provider, key, val)
                                    update_fields.append(key)
                                    comment += "{}: {}".format(getattr(BusProvider, key).field.verbose_name, getattr(provider, key))
                            # for key, val in data.items()
                            provider.save(update_fields=update_fields)
                            if user:
                                if getattr(user, 'user', None):
                                    reversion.set_user(user.user)
                                else:
                                    reversion.set_user(user)
                            reversion.set_comment(comment)
                            provider_id = provider.id
                        # with reversion.create_revision()

                        retval = {"rpc_provider": {"status": u"OK",
                                                "id": provider.id,
                                                "city_id": 0,
                                                "name": provider.name,
                                                "address": provider.address if provider.address else u'',
                                                "phone": provider.phone if provider.phone else u'',
                                                "email": provider.email if provider.email else u'',
                                                "www": provider.www if provider.www else u'',
                                                "ctime": int(provider.ctime.strftime("%s")),
                                                "mtime": int(provider.mtime.strftime("%s")),
                                                "logo": six.text_type(get_thumbnail(provider.logo, logo_size, quality=logo_quality).url) if provider.logo else u'',
                                                }}
                    # else elif not name or len(name) == 0
                # else if provider_id
            # elif len_data > 1
            else:   # no data
                retval = {"rpc_provider": {"status": u"А где данные?"}}
        except Exception as e:
            log_message(traceback.format_exc(), ttype="rpc_provider", user=user, city=(user.city if user else None))
            retval = {"rpc_provider": {"status": six.text_type(e)}}
        return retval
    # def rpc_provider

    # маршрут (Bus)
    """
    получить данные:
    data = {"bus_id": 1, "get": ["field1",..."fieldn"]}
    записать данные:
    data = {"bus_id": 1, "set": {"field1":"val1",..."fieldn":"valn"}}
    ответ на оба запроса: {"rpc_bus": {"status": u"OK", "fields": {"field1":"val1",..."fieldn":"valn"}}}
    """
    def rpc_bus(self, data):
        data, user, vdict = pro_data(data)
        retval = {"rpc_bus": {"status": u"No data"}}

        try:
            bus_id = int(data.get("bus_id", "0"))
            if bus_id:
                bus = Bus.objects.get(id=bus_id)
                if bus:
                    if user.is_banned():
                        return {"rpc_gosnum": {
                            'status': u"Ошибка: редактирование маршрутов запрещено, причина: нецензурные слова"
                        }}

                    modify_allowed = False
                    for place in bus.places.all():
                        if is_place_modify_allowed(place, user):
                            modify_allowed = True
                            break

                    if not modify_allowed:
                        retval = {
                            "rpc_bus":
                                {'status': u"Только редакторы и администраторы могут изменять связанную с городом информацию"}
                        }                        

                    names = [f.name for f in bus._meta.get_fields()]
                    values = data.get("set")
                    if values and modify_allowed:
                        comment = None
                        # записать поля
                        fields = [] # возвращаемые поля
                        update_fields = []  # обновляемые поля
                        with reversion.create_revision():
                            for name, value in values.items():
                                field_type = bus._meta.get_field(name).get_internal_type()
                                if name not in ["id", "ctime", "mtime"] and name in names:
                                    if field_type == "ForeignKey":
                                        if not value or value in [0, "0", "null", "Null", "NULL", "none", "None", "NONE"]:
                                            comment = _('Удален маршрут: ')
                                            setattr(bus, name, None)
                                            comment += "{}: {}".format(getattr(Bus, name).field.verbose_name, getattr(bus, name))
                                            update_fields.append(name)
                                        else:
                                            if name == "provider":
                                                comment = _('Изменен перевозчик: ')
                                                setattr(bus, name, BusProvider.objects.get(id=int(value)))
                                                update_fields.append(name)
                                                comment += "{}: {}".format(getattr(Bus, name).field.verbose_name, getattr(bus, name))
                                    # if field_type == "ForeignKey"
                                    else:
                                        comment = _('Изменен маршрут: ')
                                        setattr(bus, name, value)
                                        comment += "{}".format(getattr(Bus, name).field.verbose_name)
                                        update_fields.append(name)
                                    # else if field_type == "ForeignKey"

                                    fields.append(name)
                            # for name, value in values.items()
                            bus.save(update_fields=update_fields)
                            if comment:
                                reversion.set_comment(comment)
                            # reversion.add_meta(VersionCity, city=bus.city) # TODO (turbo) Return this later
                            if user and user.user:
                                reversion.set_user(user.user)
                        # with reversion.create_revision()
                    else:
                        fields = data.get("get")

                    # получить поля
                    if fields and len(fields):
                        payload = {}

                        for field in fields:
                            if field in names:
                                if field == "provider":
                                    payload[field] = bus.provider.id if bus.provider else bus.provider
                                elif field == "city":
                                    payload[field] = bus.places.all().first().id
                                elif field == "mtime":
                                    payload[field] = int(bus.mtime.strftime("%s")) if bus.mtime else bus.mtime
                                elif field == "ctime":
                                    payload[field] = int(bus.ctime.strftime("%s")) if bus.ctime else bus.ctime
                                else:
                                    payload[field] = getattr(bus, field)
                            # if field in names
                        # for field in fields

                        payload["id"] = bus.id
                        payload["mtime"] = int(bus.mtime.strftime("%s")) if bus.mtime else bus.mtime
                        retval = {"rpc_bus": {"status": u"OK", "fields": payload}}
                    # if fields and len(fields)
                # if bus
                else:
                    retval = {"rpc_bus": {"status": u"Not found bus id"}}
            # if bus_id

        except Exception as e:
            log_message(traceback.format_exc(), ttype="rpc_bus", user=user, place=(user.place if user else None))
            retval = {"rpc_bus": {"status": six.text_type(e)}}

        return retval
    # def rpc_bus

    # Gosnum
    """
    запрос данных:
    data = {"gosnum": {"uniqueid": uniqueid}}
    запись данных:
    data = {"gosnum": {"uniqueid": uniqueid, "label": label, "model": model}}
    """
    def rpc_gosnum(self, data):
        data, user, vdict = pro_data(data)
        retval = {"rpc_gosnum": {"status": u"No data"}}
        events_update_need = False

        no_editable = []
        if not user or not user.user:
            return {"rpc_gosnum": {'status': u'Ошибка: Пользователь не авторизован'}}

        try:
            data = data.get("gosnum", {})
            len_data = len(data)

            uniqueid = data.get("uniqueid")
            if not uniqueid or len_data == 0:
                return retval
            cid = data.get("city_id") or data.get("place_id")
            place_id = int(cid) if cid else user.place_id if user and user.place else None
            if place_id:
                place: Place = places_get(cur_lang).get(place_id)
            else:
                return {"rpc_gosnum": {'status': u"Ошибка: Не указан город"}}

            if user.is_banned():
                return {"rpc_gosnum": {'status': u"Ошибка: редактирование номеров запрещено, причина: нецензурные слова"}}

            if not is_gosnum_modify_allowed(place, user):
                retval = {
                    "rpc_gosnum":
                        {'status': u"Только редакторы и администраторы могут изменять связанную с городом информацию"}
                }                        
                return retval

            gosnum = data.get("gosnum")
            label = data.get("label")
            ramp = data.get("ramp", False)
            model = data.get("model")
            region = data.get("region")

            if (gosnum and is_mat(gosnum, 'rpc_gosnum')) \
                    or (label and is_mat(label, 'rpc_gosnum')) \
                    or (model and is_mat(model, 'rpc_gosnum')) \
                    or (region and is_mat(region, 'rpc_gosnum')):
                return {"rpc_gosnum": {'status': u"Ошибка: Обнаружен мат"}}

            if gosnum:
                gosnum = gosnum.replace(" ", "").upper()[:12].strip()

            record: Vehicle = Vehicle.objects.filter(uniqueid=uniqueid)  #, city=city
            if record:  # get or update
                record = record[0]
                if len_data > 2:    # update
                    comment = ''
                    update_fields = []
                    if gosnum != None and record.gosnum_allow_edit and record.gosnum != gosnum and place.id not in no_editable:
                        comment += _('Изменен Гос№ ({} -> {})'.format(record.gosnum, gosnum))
                        record.gosnum = gosnum
                        update_fields.append('gosnum')
                    if label != None and record.bortnum_allow_edit and record.bortnum != label and place.id not in no_editable:
                        label = str(label).upper().strip('\'"[]{}()*=.,:;_&?^%$#@!').replace('None', '').strip()[:12]
                        comment += _('Изменен Борт№ ({} -> {})'.format(record.bortnum, label))
                        record.bortnum = (label if label else None)
                        update_fields.append('bortnum')
                    if record.ramp != ramp:
                        comment += _('Изменена низкопольность: {}'.format('Да' if ramp else 'Нет'))
                        record.ramp = ramp
                        update_fields.append('ramp')
                    if model != None and record.model != model:
                        comment += _('Изменена модель: ({} -> {})'.format(record.model, model.upper()[:30].strip()))
                        record.model = model.upper()[:30].strip()
                        update_fields.append('model')
                    if region != None and region != '' and record.region != region:
                        comment += _('Изменен регион: ({} -> {})'.format(record.region, region.upper()[:3].strip()))
                        record.region = region.upper()[:3].strip()
                        update_fields.append('region')

                    if len(update_fields):
                        with reversion.create_revision():
                            record.save(update_fields=update_fields, user = getattr(user, 'user', None) or user)   # cache updated inside
                            # reversion.add_meta(VersionCity, city=record.city) # TODO (turbo) VersionCity city to place
                            if len(comment) > 0:
                                reversion.set_comment(comment)
                            if user and user.user:
                                reversion.set_user(user.user)
                            events_update_need = True
                    # if len(update_fields)
                # if len_data > 2

            if record and place in record.places and events_update_need:
                event = rcache_get(f"event_{uniqueid}")
                if event:
                    event['gosnum'] = record.gosnum
                    event['label'] = record.bortnum
                    rcache_set(f"event_{uniqueid}", event)
                    bus = bus_get(event.bus_id)
                    if bus:
                        bm0 = bus.bdata_mode0()
                        for v in bm0.get('l', []):
                            if v['u'] == uniqueid:
                                v['g'] = record.gosnum
                                serialized = {"bdata_mode0": bm0}
                                serialized["bdata_mode0"]['updated'] = six.text_type(place.now).split(" ")[1]
                                serialized["bdata_mode0"]['bus_id'] = bus.id
                                chan = "ru.bustime.bus_mode0__%s" % bus.id
                                sio_pub(chan, serialized)
                    REDIS_W.publish(f"turbo_{event.bus_id}", pickle_dumps({"cmd": "reload_vehicles"}))

            if record:
                retval = {"rpc_gosnum": {"status": u"OK",
                                    "uniqueid": record.uniqueid,
                                    "city_id": place.id,
                                    "gosnum": record.gosnum if record.gosnum else u'',
                                    "label": record.bortnum if record.bortnum else u'',
                                    "model": record.model if record.model else u'',
                                    "ramp": True if record.ramp else False,
                                    "region": record.region if record.region else u'',
                                    "gosnum_override": record.gosnum_allow_edit and place.id not in no_editable,
                                    "label_override": record.bortnum_allow_edit and place.id not in no_editable
                                    }}

        except Exception as e:
            log_message(traceback.format_exc(), ttype="rpc_gosnum", user=user, place=(user.place if user else None))
            retval = {"rpc_gosnum": {"status": six.text_type(e)}}

        return retval
    # def rpc_gosnum

    '''
    https://gitlab.com/nornk/bustime/issues/1753
    запрос данных:
    data = {"city_id": city_id, "uniqueid": uniqueid [,"uid_provider": uid_provider]}
    должно быть хоть одно из полей uniqueid, uid_provider или оба
    '''
    def rpc_vehicle(self, data):
        data, user, vdict = pro_data(data)
        retval = {"rpc_vehicle": {"status": u"No data"}}
        try:
            city_id = data.get("city_id") or data.get("place_id")
            place: Place = places_get(cur_lang).get(int(city_id))
            if data.get("uniqueid"):
                vehicle = Vehicle.objects.filter(uniqueid=data.get("uniqueid"))
            elif data.get("uid_provider"):
                vehicle = Vehicle.objects.filter(uid_provider=data.get("uid_provider"))
                if vehicle.count() > 1:
                    vehicle = vehicle.filter(datasource__places=place)
                if not vehicle:
                    raise ValueError(f"rpc_vehicle Vehicle[uniqueid={data.get('uniqueid')}, uid_provider={data.get('uid_provider')}] Place[{place.id}]: Not found")
            else:
                vehicle = None

            if vehicle:
                vehicle: Vehicle = vehicle[0]
                retval = {"rpc_vehicle": {"status": u"OK",
                                            "vehicle": {"uniqueid": six.text_type(vehicle.uniqueid),
                                                        "uid_provider": six.text_type(vehicle.uid_provider),
                                                        # "city_id": vehicle.city.id if vehicle.city else vehicle.city,
                                                        "city_id": place.id,
                                                        "gosnum": vehicle.gosnum if vehicle.gosnum else u'',
                                                        "bortnum": vehicle.bortnum if vehicle.bortnum else u'',
                                                        "model": vehicle.model if vehicle.model else u'',
                                                        "ramp": vehicle.ramp,
                                                        "region": vehicle.region if vehicle.region else u'',
                                                        "gosnum_allow_edit": vehicle.gosnum_allow_edit,
                                                        "bortnum_allow_edit": vehicle.bortnum_allow_edit,
                                                        "provider_id": vehicle.provider.id if vehicle.provider else vehicle.provider,
                                                        "created_auto": vehicle.created_auto,
                                                        "created_date": six.text_type(vehicle.created_date.strftime("%Y-%m-%d %H:%M:%S"))
                                                        },
                                            "bus": None,
                                            "away": None,
                                            "sleeping": None,
                                            "zombie": None,
                                        }}

                need_bmapping = True
                event = rcache_get(f"event_{vehicle.uniqueid}")
                if event:
                    bus = bus_get(event.bus_id)
                    if bus:
                        retval["rpc_vehicle"]["bus"] = {"name": six.text_type(bus.name), "ttype": bus.ttype}
                        need_bmapping = False
                    retval["rpc_vehicle"]["away"] = event.get("away")
                    retval["rpc_vehicle"]["sleeping"] = event.get("sleeping")
                    retval["rpc_vehicle"]["zombie"] = event.get("zombie")

                if need_bmapping:
                    if data.get("uniqueid"):
                        mapping = Mapping.objects.filter(xeno_id=data.get("uniqueid"), city_id=place.id)
                    elif data.get("uid_provider"):
                        mapping = Vehicle.objects.filter(xeno_id=data.get("uid_provider"), city_id=place.id)
                    else:
                        mapping = None

                    if mapping and mapping[0].bus:
                        mapping = mapping[0]
                        retval["rpc_vehicle"]["bus"] = {"name": six.text_type(mapping.bus.name), "ttype": mapping.bus.ttype}
                # if need_bmapping
            # if vehicle
            else:
                retval = {"rpc_vehicle": {"status": u"Vehicle not found"}}
            # else if vehicle

        except Exception as err:
            retval = {"rpc_vehicle": {"status": six.text_type(err)}}

        return retval
    # def rpc_vehicle


    def rpc_busstop_info(self, data):
        """Get extended information about NBusStop by bst_id. 
        It includes information stop, and it's additional features"""
        data, user, vdict = pro_data(data)
        bst_id = data.get('bst_id')
        if not bst_id:
            return {"rpc_busstop_info": {"status": u"No data"}}
        try:
            stop = NBusStop.objects.prefetch_related("nbusstopfeature_set__feature").get(id=bst_id)
        except NBusStop.DoesNotExist:
            return {"rpc_busstop_info": {"status": u"NBusStop not found"}}
        info = model_to_dict(stop, ['ttype', 'name', 'name_alt', 'moveto', 'tram_only', 'slug'])
        info['timezone'] = str(stop.timezone)
        info['x'], info['y'] = stop.point.coords if stop.point else (-1, -1)
        info['features'] = [{"name": feature.feature.name, "value": feature.value} for feature in stop.nbusstopfeature_set.all()]
        return {"rpc_busstop_info": {"status": "OK", "busstop": info}}


    def rpc_vehicle_info(self, data):
        """Get extended information about Vehicle by uniqueid. 
        It includes information about model, brand and it's additional features"""
        data, user, vdict = pro_data(data)
        retval = {"rpc_vehicle_info": {"status": u"No data"}}
        uniqueid = data.get('uniqueid')
        if not uniqueid:
            return retval
        try:
            vehicle: Vehicle = Vehicle.objects.select_related().get(uniqueid=uniqueid)  # "00079ae1"
            features = vehicle.vehiclefeature_set.all()
            vmodel = vehicle.vmodel
            vmodel_features = vmodel.vehiclemodelfeature_set.all() if vmodel else None
        except Vehicle.DoesNotExist:
            retval = {"rpc_vehicle_info": {"status": u"Vehicle not found"}}
            return retval
        info = model_to_dict(vehicle, ["uniqueid", "gosnum", "bortnum", "ramp", "model", "vmodel_id", "provider", "uid_provider", "region", "ttype"])
        if vmodel is not None:
            info['vmodel'] = model_to_dict(vmodel, ["name", "slug"])
            if vmodel.brand:
                info['vmodel']['brand'] = model_to_dict(vmodel.brand, ['name', 'slug'])
        if vmodel_features is not None:
            info['vmodel']['features'] = [{"name": vfeature.feature.name, "value": vfeature.value} for vfeature in vmodel_features]
        if features is not None:
            info['features'] = [{"name": feature.feature.name, "value": feature.value} for feature in features]
        event = rcache_get(f"event_{uniqueid}")
        if event:
            info['l'] = event.get_lava()
            bus = bus_get(event.bus_id)
            rating = vehicle_rating_get(bus, event.gosnum, 0, user.lang, **vdict)
            info.update(rating)
        retval = {"rpc_vehicle_info": {"status": u"OK", "vehicle": info}}
        return retval


    def rpc_schedule(self, data):
        data, user, vdict = pro_data(data)
        retval = {"rpc_schedule": {"status": u"No data"}}

        try:
            bus = Bus.objects.get(id=int(data['bus_id']))

            if 'tt_start' not in data and 'tt_start_holiday' not in data:    # get data for bus id
                retval = {"rpc_schedule": {"status": u"OK",
                                            "bus_id": bus.id,
                                            "tt_start": six.text_type(bus.tt_start if bus.tt_start else ''),
                                            "tt_start_holiday": six.text_type(bus.tt_start_holiday if bus.tt_start_holiday else ''),
                                            }}
            else:
                # фун-я для проверки введённых значений на соответствие формату времени
                # конвертирует "06:10 06:30" => [timetuple(06:10), timetuple(06:30)] => ["06:10", "06:30"] или "" => None
                comment = None
                test = lambda a: [time.strftime('%H:%M', d) for d in [time.strptime(t, '%H:%M') for t in a.split(' ')]] if a else None
                update_fields = []
                tt_start = {}
                tt_start_holiday = {}

                if 'tt_start' in data:  # save field tt_start
                    for direction in ["0", "1"]:
                        d = data['tt_start'][direction].replace('\r', '').replace('\n', '').replace('\\r', '').replace('\\n', '').replace('[', '').replace(']', '').strip()
                        tt_start[direction] = six.text_type( test( d ) )
                        if 'tt_start' not in update_fields:
                            comment = _("Обновлено начало движения с конечной %s маршрут\n" % bus.name)
                            update_fields.append('tt_start')

                if 'tt_start_holiday' in data:  # save field tt_start_holiday
                    for direction in ["0", "1"]:
                        d = data['tt_start_holiday'][direction].replace('\r', '').replace('\n', '').replace('\\r', '').replace('\\n', '').replace('[', '').replace(']', '').strip()
                        tt_start_holiday[direction] = six.text_type( test( d ) )
                        if 'tt_start_holiday' not in update_fields:
                            comment = _("Обновлено начало движения в выходные %s маршрут\n" % bus.name)
                            update_fields.append('tt_start_holiday')

                if len(update_fields) > 0:
                    with reversion.create_revision():
                        bus.tt_start = tt_start
                        bus.tt_start_holiday = tt_start_holiday
                        bus.save(update_fields = update_fields)
                        if comment:
                            reversion.set_comment(comment)
                        reversion.set_user(user.user)
                    retval = {"rpc_schedule": {"status": u"Saved", "bus_id": bus.id}}

        except Exception as err:
            retval = {"rpc_schedule": {"status": six.text_type(traceback.format_exc())}}

        return retval
    # def rpc_schedule
# class Gloria

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='RPC Server Gloria')
    parser.add_argument('port', metavar='N', type=int, help='port')
    args = parser.parse_args()
    # To prevent a bug "LostRemote: Lost remote after 10s heartbeat" heartbeat was disabled
    # https://groups.google.com/g/zerorpc/c/ColAElOR7aE?pli=1
    s = zerorpc.Server(Gloria(), 3, heartbeat=None)
    s.bind("tcp://127.0.0.1:%s" % args.port)
    print("Love you. Gloria. port:%s" % args.port)
    s.run()
