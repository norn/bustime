"""
Taxi

Настройки пользователя, устанавливаемые на странице settings:
us_gps_off - Выключить поиск остановок (по умолчанию включена)
us_gps_send - Отправлять координаты (по умолчанию выключена)

TODO: log_message(ttype="taxi", message=traceback.format_exc(limit=1), city=request.session.city)
"""
from django.shortcuts import render
from django.contrib.auth.models import User, Group
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.utils.translation import gettext as _
from django.template.response import TemplateResponse
from django.http import (Http404, HttpResponse, HttpResponseRedirect)
from django.contrib import messages
from django.db.models import OuterRef, Subquery, Sum, Count, F, Q
from django.db import IntegrityError
from django.db import connections
from django.conf import settings
from django.forms.models import model_to_dict
from django.views.decorators.cache import never_cache

from bustime.models import (CITY_MAP, log_message, distance_meters)
from bustime.views import (arender, get_user_settings)
from taxi.models import *

from datetime import datetime, timedelta
import json
import traceback
import base64
import os
import uuid
import subprocess


@login_required(login_url='/wiki/')
def usage(request, whois='passenger'):
    us = get_user_settings(request)
    if 'city' not in request.session:
        request.session.city = us.city

    taxiuser = TaxiUser.objects.filter(user=request.user).first()
    if not taxiuser or not taxiuser.agreement:
        return HttpResponseRedirect("/carpool/agreement/%s/" % whois)

    taxiuser.driver = (whois == 'driver')  # сейчас водитель или пассажир
    taxiuser.last_join = us.city.now
    taxiuser.save(update_fields=['driver', 'last_join'])

    if taxiuser.driver:
        # проверить заполнение личных данных
        if not taxiuser.name or not taxiuser.phone:
            # если нет - в профиль
            return HttpResponseRedirect("/carpool/profile/")
        # проверить наличие машины
        cars = CarTaxi.objects.filter(taxist=taxiuser).order_by('gos_num')
        cars_count = cars.count()
        if cars_count == 0:
            # если нет машин - в профиль
            return HttpResponseRedirect("/carpool/profile/")
        elif cars_count > 1:
            # если есть несколько - на форму выбора машины
            return HttpResponseRedirect("/carpool/selcar/")
        else:
            car = cars[0]
            car.current = True
            car.save()
    # if driver

    response = HttpResponseRedirect("/#taxi")
    taxiuser = taxiuser_update(request, response)
    return response
# usage


@login_required(login_url='/wiki/')
def profile(request, taxiuser_id=0):
    us = get_user_settings(request)
    if 'city' not in request.session:
        request.session.city = us.city

    taxiuser = TaxiUser.objects.filter(user=request.user).first()

    if not taxiuser:
        return HttpResponseRedirect("/")

    if request.POST:
        user_name = request.POST.get("user_name")
        user_phone = request.POST.get("user_phone")
        if user_name and user_phone:
            try:
                taxiuser.name = user_name
                taxiuser.gender = request.POST.get("user_gender", 0)
                taxiuser.phone = user_phone
                taxiuser.save(update_fields=['name', 'gender', 'phone'])

                response = HttpResponseRedirect("/carpool/usage/%s/" % ('driver' if taxiuser.driver else 'passenger'))
                taxiuser_update(request, response)  # in models.py
                return response
            except Exception as ex:
                msg = str(ex)
                if 'taxi_taxiuser_phone_key' in msg:
                    messages.error(request, _("Такой № телефона уже используется"))
                else:
                    messages.error(request, msg)
        else:
            messages.error(request, _("Поля должны быть заполнены"))
    # if request.POST

    ctx = {
        'taxi_type': dict(TAXI_TYPE),
        'car_class': dict(TAXI_CLASS),
        'taxiuser': taxiuser,
        'cars': CarTaxi.objects.filter(taxist=taxiuser).order_by('gos_num'),
        "languages": settings.LANGUAGES,
    }

    if taxiuser.driver and taxiuser.name and taxiuser.phone and len(ctx['cars']) == 0:
        messages.error(request, _("Необходимо добавить машину"))

    return arender(request, "taxi/profile.html", ctx)
# profile


@login_required(login_url='/wiki/')
def agreement(request, whois='passenger'):
    us = get_user_settings(request)
    if 'city' not in request.session:
        request.session.city = us.city

    ctx = {
        'city': us.city,
        'whois': whois,
        "languages": settings.LANGUAGES,
    }

    if request.POST.get("agreement") == "on" :
        taxiuser, created = TaxiUser.objects.get_or_create(user=request.user)
        taxiuser.name = ("%s %s" % (request.user.first_name, request.user.last_name)).strip()
        taxiuser.agreement = datetime.now()
        taxiuser.save(update_fields=['agreement', 'name'])
        if taxiuser.name:
            response = HttpResponseRedirect("/carpool/usage/%s/" % whois)
        else:
            response = HttpResponseRedirect("/carpool/profile/")
        taxiuser_update(request, response)
    else:
        response = arender(request, "taxi/agreement.html", ctx)

    return response
# agreement


@login_required(login_url='/wiki/')
def setcar(request, car_id=0):
    us = get_user_settings(request)
    if 'city' not in request.session:
        request.session.city = us.city

    taxiuser = TaxiUser.objects.filter(user=request.user).first()
    if not taxiuser:
        return HttpResponseRedirect("/settings_profile/")

    if request.POST:
        car_id = request.POST.get("car_id")

        if 'save' in request.POST:
            gos_num = request.POST.get("gos_num")

            try:
                if gos_num and gos_num.strip():
                    if int(car_id) == 0:
                        # новая машина
                        cars = CarTaxi.objects.filter(taxist=taxiuser).order_by('gos_num')
                        cars_count = cars.count()
                        car = CarTaxi(taxist=taxiuser, current=(cars_count == 0))
                    else:
                        # существующая машина
                        car = CarTaxi.objects.filter(id=int(car_id), taxist=taxiuser).first()
                        if not car:
                            return HttpResponseRedirect("/settings_profile/")

                    car.gos_num = gos_num.strip()
                    #car.model_id = int(request.POST.get("model_id"))
                    #car.color_id = int(request.POST.get("color_id"))
                    car.model = request.POST.get("model").strip()
                    car.color = request.POST.get("color").strip()
                    car.passengers = int(request.POST.get("passengers", 4))
                    car.baby_seat = int(request.POST.get("baby_seat", 0))
                    if "taxi_type" in request.POST:
                        car.taxi_type = int(request.POST.get("taxi_type"))
                    if "car_state" in request.POST:
                        car.car_state = int(request.POST.get("car_state"))
                    if "car_class" in request.POST:
                        car.car_class = int(request.POST.get("car_class"))

                    photo = request.FILES.get('photo')
                    if photo:
                        ext = photo.name.split('.')[-1]
                        if ext.lower() not in ['jpg', 'png']:
                            raise ValueError(_("Разрешены только JPG и PNG файлы"))
                        car.photo = handle_uploaded_file(photo, car.photo)
                    # if photo

                    car.save()
                    car_id = car.id
                    taxiuser_get(request.user.id, force=True)   # update redis cache
                else:
                    messages.error(request, _("Поля должны быть заполнены"))
                # if gos_num and gos_num.strip()
            except IntegrityError:
                messages.error(request, _("Гос.№ %s уже существует") % gos_num)
            except Exception as ex:
                messages.error(request, str(ex))
        # if 'save' in request.POST
        elif 'delete' in request.POST:
            CarTaxi.objects.filter(id=int(car_id)).delete()

        response = HttpResponseRedirect("/settings_profile/")
        taxiuser_update(request, response)  # in models.py
        return response
    # if request.POST

    #car = CarTaxi.objects.filter(id=int(car_id), taxist=taxiuser).select_related('color').first()
    car = CarTaxi.objects.filter(id=int(car_id), taxist=taxiuser).first()
    if car_id and not car:  # чужая машина
        return HttpResponseRedirect("/settings_profile/")

    ctx = {
        'us': us,
        'taxiuser': taxiuser,
        'models': CarModel.objects.all().order_by('name'),
        'colors': CarColor.objects.all().order_by('name'),
        'taxi_type': TAXI_TYPE,
        'car_class': TAXI_CLASS,
        'car_state': CAR_STATE,
        'car': car,
        'next': next,
        "languages": settings.LANGUAGES,
    }

    return arender(request, "taxi/setcar.html", ctx)
# setcar


"""
Для передачи загружаемых на сервер S7 фоток на сервер S2 надо выполнить:
1 создать пользователя для выполнения копирования между серверами на обоих серверах:
echo "thIs_iS_verY_stRong_paSswOrd_089" | md5sum
---
74ae6064c0b7e1c1376be4e890f4b475  -

sudo useradd -m -p $(openssl passwd -1 74ae6064c0b7e1c1376be4e890f4b475) -s /bin/bash -G www-data linked_user

2 сгенерировать закрытый и открытый ключи на S7
sudo -i -u linked_user
ssh-keygen -t ed25519
---
key (/home/linked_user/.ssh/id_ed25519)
Your identification has been saved in /home/linked_user/.ssh/id_ed25519
Your public key has been saved in /home/linked_user/.ssh/id_ed25519.pub

2 передать открытый ключ на сервер S2
создать каталог для ключей на S2:
sudo -i -u linked_user
mkdir ~/.ssh
chmod 700 ~/.ssh

скопировать открытый ключ с S7 на S2:
scp -2 -P 9922 /home/linked_user/.ssh/id_ed25519.pub linked_user@95.216.39.207:/home/linked_user/.ssh/authorized_keys

3 Проверка передачи файла с S7 на S2 без запроса пароля:
на S7:
scp -2 -P 9922 /mnt/reliable/repos/bustime/bustime/static/taxi/photo/25114d3605724e6892dc12d9a449dd4d.png linked_user@95.216.39.207:/mnt/reliable/repos/bustime/bustime/static/taxi/photo/
успех

4 На сервере S2 в каталоге settings.STATIC_ROOT создать папки taxi/photo с овнером/группой www-data

5 настроить файл /etc/sudoers (использовать: sudo sudoedit /etc/sudoers для редактирования):
добавить запись:
www-data ALL=(ALL:ALL) NOPASSWD:/usr/bin/supervisorctl,/usr/bin/sudo,/usr/bin/scp,/usr/bin/ssh
"""


"""
21/06/2022
С материнской машины s7 по sshfs монтирую папку uploads из s2 (Монтирование прописал в rc.local).
Далее операции с копированием файлов осуществляются как обычно, но не из папки static/taxi, а из папки uploads/taxi
"""
def handle_uploaded_file(new_photo, old_photo):
    # принимаем загружаемый файл, генерируя ему уникальное имя fname
    ext = new_photo.name.split('.')[-1]
    fname = '%s.%s' % (str(uuid.uuid4().hex), ext)
    initial_path = "%s/taxi/photo/%s" % (settings.STATIC_ROOT, fname)  # STATIC_ROOT=/mnt/reliable/repos/bustime/bustime/static
    # dirname(initial_path) = /mnt/reliable/repos/bustime/bustime/static/taxi
    if not os.path.exists(os.path.dirname(initial_path)):
        os.makedirs(os.path.dirname(initial_path))

    with open(initial_path, 'wb+') as destination:
        for chunk in new_photo.chunks():
            destination.write(chunk)
            # / принимаем загружаемый файл

    # сохраняем новый файл
    if settings.MASTER_HOSTNAME in ["s5", "s7"]:
        # передаём файл на сервер S2
        cmd = "sudo -u linked_user scp -2 -P 9922 %s linked_user@%s:%s/taxi/photo/" % (initial_path, settings.DEFAULT_HOST, settings.STATIC_ROOT)
        os.system(cmd)
        os.remove(initial_path) # удаляем принятый файл

        # удаляем старй файл, если он есть
        if old_photo:
            cmd = 'sudo -u linked_user ssh linked_user@%s -p 9922 "rm -f %s/%s"' % (settings.DEFAULT_HOST, settings.STATIC_ROOT, old_photo)
            os.system(cmd)
    else:
        # если мы на S2, то копируем в нужную папку
        new_path = "%s/taxi/photo/%s" % (settings.STATIC_ROOT, fname)   # STATIC_ROOT=/mnt/reliable/repos/bustime/bustime/static
        # dirname(new_path) = /mnt/reliable/repos/bustime/bustime/static/taxi/photo
        if not os.path.exists(os.path.dirname(new_path)):
            os.makedirs(os.path.dirname(new_path))

        os.rename(initial_path, new_path)

    # удаляем старй файл, если он есть
    if old_photo:
        old_path = "%s/%s" % (settings.STATIC_ROOT, old_photo)
        if os.path.isfile(old_path):
            os.remove(old_path)

    url = "taxi/photo/%s" % fname
    return url


@login_required(login_url='/wiki/')
def selcar(request, car_id=0):
    us = get_user_settings(request)
    if 'city' not in request.session:
        request.session.city = us.city

    taxiuser = TaxiUser.objects.filter(user=request.user).first()

    if car_id:
        CarTaxi.objects.filter(taxist=taxiuser).update(current=False)
        CarTaxi.objects.filter(id=car_id).update(current=True)
        # перейти на форму просмотра заказов
        return HttpResponseRedirect("/")

    ctx = {
        'cars': CarTaxi.objects.filter(taxist=taxiuser).order_by('gos_num'),
        'taxi_type': dict(TAXI_TYPE),
        'car_class': dict(TAXI_CLASS),
        "languages": settings.LANGUAGES,
    }

    return arender(request, "taxi/selcar.html", ctx)
# selcar


# водитель, список заказов (голосующих пассажиров)
@login_required(login_url='/wiki/')
@never_cache
def votes(request):
    us = get_user_settings(request)
    if 'city' not in request.session:
        request.session.city = us.city

    taxiuser = taxiuser_get(request.user.id, force=True)
    torders = rcache_get("torders_%s" % us.city.id, {})
    offers = {}
    near_distance = 3000    # 3 км
    near_pass_count = 0 # Пассажиров поблизости
    tevents = rcache_get("tevents_%s" % us.city.id, {})
    my_event = tevents.get(taxiuser['id'])

    for order_id, order in torders.items():
        # ищем свои предложения пассажирам
        order_offers = rcache_get('offers_%s' % order_id, {}) # это offers (предложения водителей) на заказ
        my_offer = order_offers.get(request.user.id)   # ищем свои предложения (время жизни предложения 10 минут (api.py offer()))
        if my_offer or order['trip_status'] in [1,2,3]: # models.py TRIP_STATUS
            # есть моё предложение или начатый заказ
            offers[order_id] = order

        # вычисляем пассажиров поблизости
        if my_event:  # может и не быть, если не успел прислать координаты
            if distance_meters(my_event['x'], my_event['y'], order['wf_point'].x, order['wf_point'].y) <= near_distance:
                near_pass_count += 1
    # for order_id, order in torders.items()

    ctx = {
        'us': us,
        'taxiuser': taxiuser,
        'torders': torders, # заказы (голосующие пассажиры)
        'offers': offers,   # мои предложения на заказы
        'offers_json': json.dumps(offers, default=str), # для восстановления карты/таймера (orders.html, order_item.html)
        'near_distance': int(near_distance / 1000),
        'near_pass_count': near_pass_count,
        "languages": settings.LANGUAGES,
    }

    return arender(request, "taxi/orders.html", ctx)
"""
order={'id': 398,
  'data': datetime.datetime(2022, 5, 5, 8, 28, 28, 130052),
  'city': 4,
  'trip_data': datetime.datetime(2022, 5, 5, 8, 28, 28, 130091),
  'urgent': False,
  'wf': 'Каштановая Аллея (Карла Маркса)',
  'wf_point': <Point object at 0x7f0f67b4b120>, (доступно как order['wf_point'].x, order['wf_point'].y)
  'wh': 'Ивана Земнухова',
  'wh_point': <Point object at 0x7f0f67b4b2b8>,
  'passengers': '1',
  'childs': 0,
  'bags': 0,
  'taxi_type': 0,
  'car_class': 1,
  'note': '',
  'price': '100',
  'distance': 10,
  'duration': '14 мин.',
  'trip_line': {'type': 'LineString',
    'coordinates': [[20.465742, 54.724536], ...]
   },
  'passenger': {
    'id': 2,
    'user': 108660,
    'gender': 0,
    'agreement': datetime.datetime(2022, 4, 15, 19, 17, 28, 523962),
    'name': None,
    'phone': None,
    'driver': False,
    'driver_rating_cnt': 0,
    'driver_trips_cnt': 0,
    'driver_rating': 0,
    'passenger_rating_cnt': 38,
    'passenger_rating': 0,
    'last_join': datetime.datetime(2022, 4, 15, 14, 17, 29, 675424),
    'gps_on': True,
    'avatar': None,
    'car_count': 0,
    'order_id': 398
   },
  'passenger_rating': 0,
  'passenger_note': None,
  'taxist': None,   в выполняющемся заказе выглядит примерно так же, как пассажир
  'taxist_rating': 0,
  'taxist_note': None,
  'car': None,
  'trip_price': None,
  'trip_start': None,
  'trip_end': None,
  'trip_status': 0,
  'passenger_deleted': None,
  'taxist_deleted': None
}

event = {'uniqueid': 1,
  'timestamp': datetime.datetime(2022, 5, 5, 8, 35, 31, 366334),
  'x': 20.46048,
  'y': 54.72035,
  'heading': 87,
  'speed': 393191,
  'custom': True,
  'gosnum': '111',
  'accuracy': 300,
  'uid_original': 1,
  'uid_code': 1,
  'channel': 'bustime',
  'src': 'inject_events.py',
  'order': None,
  'odometer': 0,
  'odometer_weekday': 3,
  'taxi': {
       'id': 1,
       'user': 12,
       'gender': 0,
       'agreement': datetime.datetime(2022, 4, 15, 19, 14, 54, 663563),
       'name': 'locman',
       'phone': '111',
       'driver': True,
       'driver_rating_cnt': 43,
       'driver_trips_cnt': 16,
       'driver_rating': 0,
       'passenger_rating_cnt': 0,
       'passenger_rating': 0,
       'last_join': datetime.datetime(2022, 4, 15, 14, 15, 27, 221232),
       'gps_on': True,
       'avatar': None,
       'car_count': 1,
       'car': {'id': 1,
        'taxist': 1,
        'gos_num': '111',
        'model': {'id': 52, 'name': 'Alfa Romeo 145'},
        'color': {'id': 1, 'name': 'Бежево-жёлтый', 'rgb': None},
        'passengers': 4,
        'baby_seat': 0,
        'taxi_type': 0,
        'car_state': 1,
        'car_class': 1,
        'current': True,
        'photo': 'taxi/photo/cc29b8e154c64402a2ca7f4e5d9776e8.jpg'}
    }
}
"""