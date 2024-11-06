"""
Taxi

Prepare:
pip install django-mathfilters (mathfilters => INSTALLED_APPS)

Help:
https://django.fun/docs/django/ru/3.1/ref/models/fields/
https://docs.djangoproject.com/en/4.0/ref/signals/#module-django.db.models.signals

Migrations:
https://django.fun/docs/django/ru/3.1/topics/migrations/

python manage.py makemigrations taxi
python manage.py migrate taxi
python manage.py migrate taxi --database bstore

SELECT *
FROM public.taxi_taxiuser
WHERE NAME LIKE '%locman%';

SELECT *
FROM taxi_cartaxi
WHERE taxist_id IN (SELECT id FROM taxi_taxiuser WHERE NAME LIKE '%locman%');

удаление таксиста
DELETE FROM taxi_offers WHERE taxist_id = 3;
DELETE FROM taxi_order WHERE taxist_id = 3;
DELETE FROM taxi_cartaxi WHERE taxist_id = 3;
DELETE FROM taxi_taxiuser WHERE id = 3;
DELETE FROM taxi_tevent WHERE taxiuser = 3;
"""
from __future__ import absolute_import
from __future__ import print_function
from django.contrib.auth.models import User, Group
from django.utils.translation import gettext as _
from django.contrib.gis.db import models
from django.db import connections
from django.db.models.signals import post_delete, post_save
from django.db.models import Manager as GeoManager
from django.dispatch import receiver
from django.template.response import TemplateResponse
from django.forms.models import model_to_dict
from django.contrib.postgres.fields import ArrayField
from django.contrib.gis.geos import Point
from django.conf import settings

from bustime.models import (rcache_get, rcache_set, sio_pub, City, CITY_MAP)
from taxi.get_request import current_request

import json
import traceback
import os
import urllib.parse

WEB_SOCKET_CHANNEL = "ru.bustime.taxi_%s"

TAXI_TYPE = [
    (0, _('Такси')),
    (1, _('Грузовое такси')),
    (2, _('Микроавтобус')),
    (3, _('Автобус')),
]

TAXI_CLASS = [
    (0, _('Эконом')),
    (1, _('Стандарт')),
    (2, _('Бизнес')),
    (3, _('VIP')),
]

CAR_STATE = [
    (0, _('Новая')),
    (1, _('Хорошее')),
    (2, _('Среднее')),
    (3, _('Ещё ездит')),
]

GENDER = [
    (0, _('Мужчина')),
    (1, _('Женщина')),
]

# при изменении проверить templatetags/order_extras.py и templates/taxi/orders_items_p.html
TRIP_STATUS = [
    (1, _('Такси выехало к пассажиру')),
    (2, _('Такси подано, ожидает пассажира')),
    (3, _('Поездка началась')),
    (4, _('Поездка окончена')), # нормально
    (5, _('Отказ водителя')),
    (6, _('Отказ пассажира')),
]


# Return all rows from a cursor as a dict
# use for cursor.execute()
# https://www.djbook.ru/rel3.0/topics/db/sql.html#executing-custom-sql-directly
def cursor_to_dict(cursor):
    columns = [col[0] for col in cursor.description]
    return [ dict(zip(columns, row)) for row in cursor.fetchall() ]


class TaxiUser(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True)
    gender = models.SmallIntegerField("Пол водителя", choices=GENDER, default=0)    # 0-М, 1-Ж
    agreement = models.DateTimeField("Согласие с условиями сервиса такси", null=True, blank=True)
    name = models.CharField("Имя", max_length=50, null=True, blank=True)
    phone = models.CharField("Тел.", max_length=16, null=True, blank=True, unique=True)
    driver = models.BooleanField("Водитель такси", default=False, null=True)
    driver_rating_cnt = models.SmallIntegerField("Кол-во оценок водителя", default=0)   # инкрементируется при окончании поездки, если выставлена оценка пассажиром
    driver_rating_pos = models.SmallIntegerField("Кол-во позитивных оценок водителя", default=0)    # инкрементируется при окончании поездки, если starts > 0
    driver_rating = models.DecimalField("Рейтинг водителя", max_digits=2, decimal_places=1, default=0.0) # рассчитывается при окончании поездки
    driver_trips_cnt = models.SmallIntegerField("Кол-во поездок", default=0)            # инкрементируется при окончании поездки, если trip_status=4
    passenger_rating_cnt = models.SmallIntegerField("Кол-во оценок пассажира", default=0)
    passenger_rating_pos = models.SmallIntegerField("Кол-во позитивных оценок пассажира", default=0)
    passenger_rating = models.DecimalField("Рейтинг пассажира", max_digits=2, decimal_places=1, default=0.0)
    last_join = models.DateTimeField("Последняя активность", null=True, blank=True) # вернее, последняя активность
    gps_on = models.BooleanField("Передача GPS", default=False, null=True) # True - активный (таксист или пассажир), False - не использует сервис сейчас
    avatar = models.CharField("Аватар", max_length=150, null=True, blank=True)
    gps_to = ArrayField(models.IntegerField(), default=list)  # массив TaxiUser.id, которым отправляются координаты этого пользователя

    def __str__(self):
        return "%s" % self.id

    class Meta:
        verbose_name = _("Пользователь сервиса")
        verbose_name_plural = _("Пользователи сервиса")

# эти методы не успевают сработать в условиях репликации REDIS
# поэтому после в коде .save() делать taxiuser_get(..., force=True)
"""
@receiver(post_save, sender=TaxiUser)
def taxiuser_post_save(sender, **kwargs):
    taxiuser = kwargs.get('instance')
    taxiuser_get(taxiuser.user.id, force=True)

@receiver(post_delete, sender=TaxiUser)
def taxiuser_post_delete(sender, **kwargs):
    taxiuser = kwargs.get('instance')
    taxiuser_get(taxiuser.user.id, force=True)
"""


"""
return:
{'id': 9,
 'user': 12,
 'gender': 0,
 'agreement': datetime.datetime(2022, 3, 6, 15, 23, 53, 157736),
 'name': 'locman',
 'phone': '111',
 'driver': True,
 'driver_rating_cnt': 0,
 'driver_rating': 0,
 'passenger_rating_cnt': 0,
 'passenger_rating': 0,
 'last_join': datetime.datetime(2022, 4, 1, 11, 10, 3, 615068),
 'gps_on': False,
 'avatar': None,
 'car_count': 1,
 'car': {'id': 24,
  'taxist': 9,
  'gos_num': 'sss',
  'model': {'id': 52, 'name': 'Alfa Romeo 145'},
  'color': {'id': 259, 'name': 'Бежево-жёлтый', 'rgb': None},
  'passengers': 4,
  'baby_seat': 0,
  'taxi_type': 0,
  'car_state': 1,
  'car_class': 1,
  'current': True,
  'photo': 'taxi/photo/e7db0cfe6467497c956fd54495a03741.jpg'}}
"""
def taxiuser_get(us_id, force=False):
    cc_key = "taxiuser_%s" % (us_id)
    taxiuser = rcache_get(cc_key)
    if not taxiuser or force:
        taxiuser = TaxiUser.objects.filter(user__id=us_id).first()
        if taxiuser:
            #cars = CarTaxi.objects.select_related('model', 'color').filter(taxist=taxiuser)
            cars = CarTaxi.objects.filter(taxist=taxiuser)
            taxiuser = model_to_dict(taxiuser)
            taxiuser['car_count'] = cars.count()
            car = cars.filter(current=True).first()
            if car:
                taxiuser['car'] = model_to_dict(car)
                #taxiuser['car']['model'] = model_to_dict(car.model)
                #taxiuser['car']['color'] = model_to_dict(car.color)

            order = Order.objects.filter(passenger=taxiuser['id'], trip_status__lt=3).order_by('data').last()
            if order:
                taxiuser['order_id'] = order.id
        # if taxiuser
        else:
            taxiuser = model_to_dict(TaxiUser())
            taxiuser['car_count'] = 0
        rcache_set(cc_key, taxiuser, 60*60*2)
    return taxiuser
# taxiuser_get


def taxiuser_update(request, response = None):
    taxiuser = taxiuser_get(request.user.id, force=True)    # update redis cache
    request.session['taxiuser'] = json.dumps(taxiuser, default=str)
    if response:
        response.set_cookie('taxi_user', request.session['taxiuser'], path='/', samesite='lax')   # session only live

    return taxiuser


"""
# записать в поле TaxiUser.gps_to ID пользователя, которому надо отправлять свои координаты
# координаты отправляются через вебсокет функцией api.py::gps_send() автоматически всем из поля gps_to
# параметры - user.id, не taxiuser.id
def on_gps_to(sender_user_id, receiver_user_id):
    sender = TaxiUser.objects.filter(user__id=sender_user_id).first()
    if sender and sender_user_id != receiver_user_id:
        if receiver_user_id not in sender.gps_to:
            sender.gps_to.append(receiver_user_id)
            sender.save(update_fields=['gps_to'])
# on_gps_to


# удалить из поля TaxiUser.gps_to ID пользователя, которому уже не надо отправлять свои координаты
# параметры - user.id, не taxiuser.id
def off_gps_to(sender_user_id, receiver_user_id):
    sender = TaxiUser.objects.filter(user__id=sender_user_id).first()
    if sender:
        if receiver_user_id in sender.gps_to:
            sender.gps_to.remove(receiver_user_id)
            sender.save(update_fields=['gps_to'])
# off_gps_to


# очистить поле TaxiUser.gps_to
# параметры - user.id, не taxiuser.id
def clear_gps_to(sender_user_id):
    sender = TaxiUser.objects.filter(user__id=sender_user_id).first()
    if sender:
        sender.gps_to = []  # not {} !!!
        sender.save(update_fields=['gps_to'])
# off_gps_to
"""


# Не используется с 23.01.23
class CarModel(models.Model):
    name = models.CharField("Модель", max_length=50, unique=True)

    def __str__(self):
        return "%s" % self.name

    class Meta:
        verbose_name = _("Модель автомобиля")
        verbose_name_plural = _("Модели автомобилей")


# Не используется с 23.01.23
class CarColor(models.Model):
    name = models.CharField("Цвет автомобиля", max_length=50, unique=True)
    rgb = models.CharField("RGB", max_length=7, null=True)

    def __str__(self):
        return "%s" % self.name

    class Meta:
        verbose_name = _("Цвет автомобиля")
        verbose_name_plural = _("Цвета автомобилей")


class CarTaxi(models.Model):
    taxist = models.ForeignKey(TaxiUser, null=True, on_delete=models.CASCADE)
    gos_num = models.CharField("Гос. №", max_length=12, unique=True)
    #model = models.ForeignKey(CarModel, null=True, on_delete=models.SET_NULL)
    model = models.CharField("Марка", max_length=50, null=True)
    #color = models.ForeignKey(CarColor, null=True, on_delete=models.SET_NULL)
    color = models.CharField("Цвет", max_length=50, null=True)
    passengers = models.SmallIntegerField("Кол-во пассажиров", default=4)
    baby_seat = models.SmallIntegerField("Детские кресла", default=0)
    taxi_type = models.SmallIntegerField("Тип такси", choices=TAXI_TYPE, default=0)
    car_state = models.SmallIntegerField("Состояние машины", choices=CAR_STATE, default=1)
    car_class = models.SmallIntegerField("Класс такси", choices=TAXI_CLASS, default=1)
    current = models.BooleanField("Выбранная машина", default=False)
    photo = models.CharField("Фото", max_length=150, null=True, blank=True)

    def __str__(self):
        return "%s" % self.id

    class Meta:
        verbose_name = _("Машина такси")
        verbose_name_plural = _("Машины такси")

# https://docs.djangoproject.com/en/4.0/ref/signals/#post-delete
@receiver(post_delete, sender=CarTaxi)
def cartaxi_post_delete(sender, **kwargs):
    cartaxi = kwargs.get('instance')
    try:
        if cartaxi.photo:
            if settings.MASTER_HOSTNAME in ["s5", "s7"]:
                cmd = 'sudo -u linked_user ssh linked_user@%s -p 9922 "rm -f %s/%s"' % (settings.DEFAULT_HOST, settings.STATIC_ROOT, cartaxi.photo)
                os.system(cmd)
            else:
                path = "%s/%s" % (settings.STATIC_ROOT, cartaxi.photo)
                if os.path.isfile(path):
                    os.remove(path)
    except:
        log_message(ttype="taxi", message=traceback.format_exc(limit=1), city=request.session.city)

# TODO: проверить taxi/api.py & taxi/views.py, возможно, эта функция уже не нужна:
@receiver(post_save, sender=CarTaxi)
def cartaxi_post_save(sender, **kwargs):
    cartaxi = kwargs.get('instance')
    taxiuser_get(cartaxi.taxist.user.id, force=True)


# заказы
# запись создаётся, когда пассажир делает заказ
# TODO: удалять заказы без таксиста ночами
class Order(models.Model):
    # id - № заказа
    # это часть "создание заказа"
    data = models.DateTimeField("Дата") # дата создания заказа
    city = models.ForeignKey(City, on_delete=models.CASCADE, null=True)
    trip_data = models.DateTimeField("Дата и время поездки")
    urgent = models.BooleanField("Срочно", default=False)
    wf = models.CharField("Откуда", max_length=100)
    wf_point = models.PointField(srid=4326, null=True, blank=True)
    wh = models.CharField("Куда", max_length=100)
    wh_point = models.PointField(srid=4326, null=True, blank=True)
    passengers = models.SmallIntegerField("Кол-во пассажиров", default=1)
    childs = models.SmallIntegerField("Кол-во детских кресел", default=0)
    bags = models.SmallIntegerField("Кол-во мест багажа", default=0)
    taxi_type = models.SmallIntegerField("Тип такси", choices=TAXI_TYPE, default=0)
    car_class = models.SmallIntegerField("Класс такси", choices=TAXI_CLASS, default=1)
    note = models.TextField("Дополнительно", null=True)
    price = models.SmallIntegerField("Ожидаемая стоимость", null=True)
    distance = models.FloatField("Расстояние", null=True, blank=True)
    duration = models.TextField("Продолжительность", null=True) # текстовое значение времени поездки, "14 мин".
    trip_line = models.JSONField(null=True, blank=True)    # предполагаемая трасса поездки в GeoJSON
    passenger = models.ForeignKey(TaxiUser, on_delete=models.CASCADE, null=True, related_name='order_passenger')
    passenger_rating = models.SmallIntegerField("Оценка поезки пассажиром", default=0)  # оценка водителя пассажиром, заполняется по окончанию поездки
    passenger_note = models.TextField("Комментарий пассажира", null=True)   # замечания о поездке
    #
    taxist = models.ForeignKey(TaxiUser, on_delete=models.CASCADE, null=True, related_name='order_taxist')
    taxist_rating = models.SmallIntegerField("Оценка пассажира водителем", default=0)   # оценка пассажира водителем, заполняется по окончанию поездки
    taxist_note = models.TextField("Комментарий водителя", null=True)
    car = models.ForeignKey(CarTaxi, null=True, on_delete=models.SET_NULL)
    #
    trip_price = models.SmallIntegerField("Договорная цена", null=True)
    trip_start = models.DateTimeField("Начало поездки", null=True)  # водитель нажал Поехал
    trip_end = models.DateTimeField("Окончание поездки", null=True) # водитель нажал Приехали + пассажир нажал Приехали или тот или другой отказались от поездки
    trip_status = models.SmallIntegerField("Состояние заказа", choices=TRIP_STATUS, default=0)
    # заказ не будет показан в истории пассажиру, если он его "удалил", так же с таксистом
    # заказ будет удалён из БД, если оба поля NOT NULL (возможно, не сразу, сколько хранить надо подумать)
    passenger_deleted = models.DateTimeField("Дата удаления пассажиром", null=True) # если пассажир удалил заказ, записать дату
    taxist_deleted = models.DateTimeField("Дата удаления таксистом", null=True)

    def __str__(self):
        return "%s" % self.id

    class Meta:
        verbose_name = _("Заказ такси")
        verbose_name_plural = _("Заказы такси")


"""
return:
{'id': 263,
 'data': datetime.datetime(2022, 4, 29, 14, 39, 42, 206415),
 'city': 4,
 'trip_data': datetime.datetime(2022, 4, 29, 14, 39, 42, 206440),
 'urgent': False,
 'wf': 'Каштановая Аллея (Карла Маркса)',
 'wf_point': <Point object at 0x7f421e4fe230>,
 'wh': 'Ивана Земнухова',
 'wh_point': <Point object at 0x7f421e4fe3c8>,
 'passengers': '1',
 'childs': 0,
 'bags': 0,
 'taxi_type': 0,
 'car_class': 1,
 'note': '',
 'price': '100',
 'distance': 10,
 'duration': '14 мин.',
 'trip_line': {
    'type': 'LineString',
    'coordinates': [[20.465742, 54.724536],...]
  },
 'passenger': {'id': 2,
  'user': 108660,
  'gender': 0,
  'agreement': datetime.datetime(2022, 4, 15, 19, 17, 28, 523962),
  'name': None,
  'phone': None,
  'driver': False,
  'driver_rating_cnt': 0,
  'driver_trips_cnt': 0,
  'driver_rating': 0,
  'passenger_rating_cnt': 0,
  'passenger_rating': 0,
  'last_join': datetime.datetime(2022, 4, 15, 14, 17, 29, 675424),
  'gps_on': True,
  'avatar': None,
  'car_count': 0,
  'order_id': 263},
 'passenger_rating': 0,
 'passenger_note': None,
 'taxist': None,
 'taxist_rating': 0,
 'taxist_note': None,
 'car': None,
 'trip_price': None,
 'trip_start': None,
 'trip_end': None,
 'trip_status': 0,
 'passenger_deleted': None,
 'taxist_deleted': None}
 """
def order_get(order_id, force=False):
    cc_key = "torder_%s" % (order_id)
    order = rcache_get(cc_key)
    if not order or force:
        order = Order.objects.filter(id=order_id).select_related('passenger', 'taxist', 'car').first()
        if order:
            car = model_to_dict(order.car) if order.car else None
            passenger = model_to_dict(order.passenger) if order.passenger else None
            taxist = model_to_dict(order.taxist) if order.taxist else None

            order = model_to_dict(order)
            order['car'] = car
            order['passenger'] = passenger
            order['taxist'] = taxist
            rcache_set(cc_key, order, 3600)
        else:
            order = None
    return order
# order_get

# https://docs.djangoproject.com/en/4.0/ref/signals/#post-save
"""
@receiver(post_save, sender=Order)
def order_post_save(sender, **kwargs):
    order = kwargs.get('instance')
    request = current_request() # это тот request, который в def view(request)
    order_get(order.id, force=True)
# order_post_save
"""

# https://docs.djangoproject.com/en/4.0/ref/signals/#post-delete
@receiver(post_delete, sender=Order)
def order_post_delete(sender, **kwargs):
    order = kwargs.get('instance')
# order_post_delete


# ответы (предложения) водителей на заказ
# запись создаётся, когда водитель нажал Беру
class Offers(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    taxist = models.ForeignKey(TaxiUser, on_delete=models.CASCADE, null=True, related_name='offer_taxist')
    data = models.DateTimeField("Время предложения", auto_now_add=True, null=True)
    price = models.SmallIntegerField("Стоимость водителя")
    passenger_acceptance = models.BooleanField("Согласие пассажира", default=False) # True - пассажир выбрал водителя
    taxist_acceptance = models.BooleanField("Согласие водителя", default=False)     # True - водитель нажал Поехал

    def __str__(self):
        return "%s" % self.id

    class Meta:
        constraints = [ models.UniqueConstraint(fields=['order', 'taxist'], name="order-taxist") ]
        verbose_name = _("Предложение водителя")
        verbose_name_plural = _("Предложения водителей")


@receiver(post_save, sender=Offers)
def offers_post_save(sender, **kwargs):
    offer = kwargs.get('instance')
    created = kwargs.get('created', False)
    request = current_request() # это тот request, который в def view(request)

    if created:
        # водитель откликнулся на заказ
        # сформируем HTML для вставки в список откликов на странице order_wait.html
        ctx = {
            'taxi_type': dict(TAXI_TYPE),
            'car_class': dict(TAXI_CLASS),
            'order': Order.objects.filter(id=offer.order.id).first(),
            'offer': get_offers_by(offer.id, 'id')[0],
        }
        html = TemplateResponse(request, 'taxi/order_wait_offer.html', ctx).rendered_content.replace("\n", "").replace("   ", "")
        # отправим сообщение клиенту
        data = {
            "app": "taxi",
            "to": [offer.order.passenger.user.id],
            "cmd": "offer_new",
            "data": {
                "html": html,
                "json": json.dumps(model_to_dict(offer), default=str),
            },
        }
        sio_pub(WEB_SOCKET_CHANNEL % (offer.order.city.id), data)
    # if created
    else:   # updated
        if offer.passenger_acceptance:  # пассажир согласился на предложение таксиста
            pass
        if offer.taxist_acceptance:  # таксиста нажал кнопку Поехали
            pass
    # else if created
# offers_post_save


# происходит и при удалении заказа по ForeignKey(Order
@receiver(post_delete, sender=Offers)
def offers_post_delete(sender, **kwargs):
    offer = kwargs.get('instance')
    # отправляем сообщение об удалении предложения водителя и водителю и пассажиру
    data = {
        "app": "taxi",
        "to": [offer.order.passenger.user.id, offer.taxist.user.id],
        "cmd": "offer_del",
        "data": {
            "json": json.dumps(model_to_dict(offer), default=str),
        },
    }
    sio_pub(WEB_SOCKET_CHANNEL % (offer.order.city.id), data)
# offers_post_delete


def get_offers_by(field_value, field_name='order_id'):
    cursor=connections['default'].cursor()
    query = '''SELECT
        offer.*,
        taxist.gender AS taxist_gender,
        taxist.name AS taxist_name,
        taxist.phone AS taxist_phone,
        taxist.driver_rating AS taxist_driver_rating,
        car.gos_num AS car_gos_num,
        car.passengers AS car_passengers,
        car.baby_seat AS car_baby_seat,
        car.taxi_type AS car_taxi_type,
        car.car_state AS car_state,
        car.car_class AS car_class,
        car.model AS car_model_name,
        car.color AS car_color_name
    FROM taxi_offers offer
    LEFT JOIN taxi_taxiuser taxist ON taxist.id = offer.taxist_id
    LEFT JOIN taxi_cartaxi car ON car.taxist_id = taxist.id AND car.current
    WHERE offer.%s = %s
    ORDER BY offer.data DESC''' % (field_name, "%s")
    cursor.execute(query, [field_value])
    return cursor_to_dict(cursor)
# get_offers_by


# города, посёлки и т.п.
"""
class Kladr_place(models.Model):
    city = models.ForeignKey(City, on_delete=models.SET_NULL, null=True)
    code = models.CharField("KLADR CODE", max_length=20)
    socr = models.CharField("KLADR SOCR", max_length=10)
    name = models.CharField("Место", max_length=50)
"""

# улицы
class Kladr_street(models.Model):
    #place = models.ForeignKey(Kladr_place, on_delete=models.CASCADE)
    city = models.ForeignKey(City, on_delete=models.CASCADE)
    code = models.CharField("KLADR CODE", max_length=20)
    socr = models.CharField("KLADR SOCR", max_length=10)
    name = models.CharField("Улица", max_length=50)
    index = models.CharField("Индекс", max_length=6, null=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Улица")
        verbose_name_plural = _("Улицы")


# отметки GPS, database=bstore (bustime/db_routes.py)
# https://docs.djangoproject.com/en/4.0/topics/db/multi-db/
class Tevent(models.Model):
    id = models.BigAutoField(primary_key=True)
    taxiuser = models.IntegerField(db_index=True)
    systime = models.DateTimeField(auto_now_add=True)
    gpstime = models.DateTimeField(db_index=True)
    citytime = models.DateTimeField(db_index=True, null=True, blank=True)
    x = models.FloatField(null=True, blank=True)
    y = models.FloatField(null=True, blank=True)
    heading = models.IntegerField(null=True, blank=True)
    speed = models.IntegerField(null=True, blank=True)
    accuracy = models.FloatField(null=True, blank=True)
    objects = GeoManager()
    order = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return u"%s: %s-%s-%s %s %s" % (self.timestamp, self.bus_id, self.uniqueid, self.gosnum, self.x, self.y)

    class Meta:
        verbose_name = _("GPS отметка")
        verbose_name_plural = _("GPS отметки")