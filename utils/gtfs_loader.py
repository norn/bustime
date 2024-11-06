#!/mnt/reliable/repos/bustime/bustime/.venv/bin/python
# -*- coding: utf-8 -*-
"""
Попытка автоматизации загрузки и парсинга маршрутов формата gtfs из ибщедоступных каталогов
Результат загрузки можно смотреть здесь (город любой):
    https://ru.bustime.loc/miass/admin/load-gtfs/

https://gtfs.org/ru/schedule/reference/

Загрузка данных gtfs:
Из каталога, по ID записи (ID=3):
    python utils/gtfs_loader.py 3 --debug
Из каталога, все записи (ID=0):
    python utils/gtfs_loader.py 0

Примечание:
    Данные schedule (расписание) будут обрабатываться по шагам в соответствии со значением в поле url_schedule:
        Если ссылка:
            1. загрузка (download) файла имя.zip
            2. распаковка в каталог WORK_DIR/<GtfsCatalog.id>/<имя> (с предварительным созданием каталогов/удалением содержимого существующих)
            3. запись в БД (с предварительным полным удалением данных для GtfsCatalog.id)
        Если /полный/путь/к/файлу/имя.zip: шаги 2 + 3
        Если /полный/путь/к/папке/с распакованным/zip: шаг 3

Из файла (архива):
    python utils/gtfs_loader.py -1 --zip /bustime/bustime/utils/automato/имя.zip
        ID=-1 означает: создать новую запись в каталоге. Запись создается, если ещё нет GtfsCatalog.name == имя.zip, иначе используется существующая.
        выполняются шаги 2 + 3

Из папки (с распакованными данными):
    python utils/gtfs_loader.py 10 --dir /bustime/bustime/utils/automato/папка
        ID=10 означает: значение GtfsCatalog.name для записи с GtfsCatalog.id == 10 будет заменено на <папка>
        и выполнится шаг 3

Удаление данных для GtfsCatalog.id=3:
    DELETE FROM bustime_gtfscalendardates where catalog_id = 3; -- GtfsCalendarDates
    DELETE FROM bustime_gtfscalendar where catalog_id = 3;      -- GtfsCalendar
    DELETE FROM bustime_gtfsstoptimes where catalog_id = 3;     -- GtfsStopTimes
    DELETE FROM bustime_gtfsstops where catalog_id = 3;         -- GtfsStops
    DELETE FROM bustime_gtfsshapes where catalog_id = 3;        -- GtfsShapes
    DELETE FROM bustime_gtfstrips where catalog_id = 3;         -- GtfsTrips
    DELETE FROM bustime_gtfsroutes where catalog_id = 3;        -- GtfsRoutes
    DELETE FROM bustime_gtfsagency where catalog_id = 3;        -- GtfsAgency
    DELETE FROM bustime_gtfscatalog where id=3;                 -- GtfsCatalog
Можно попытаться удалить запись каталога GtfsCatalog в админке и всё остальное должно удалиться по ForeignKey(GtfsCatalog, on_delete=models.CASCADE),
но, скорее всего, произойдёт timeout.
"""
from __future__ import absolute_import
from __future__ import print_function
from devinclude import *
from bustime.models import *    # fill_routeline
from coroutines.gtfs_update import EVENT_CHANNEL
from django.contrib.gis.geos import Point
import argparse
import traceback
import sys
import os
import logging
import requests
import pyrfc6266
from pathlib import Path
import shutil
import zipfile
import csv
from typing import NoReturn
import datetime
import codecs
from urllib.parse import urlparse
import json


LOG_FILE = 'gtfs_loader.log'
WORK_DIR = '/bustime/bustime/utils/automato'
SCRIPTS_DIR = '%s/scripts' % WORK_DIR
SCRIPTS_TEMPLATES = ['%s.postload.sql'] # шаблоны имён скриптов


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%d-%m-%y %H:%M:%S",
    handlers=[
        logging.FileHandler("%s/%s" % (WORK_DIR, LOG_FILE)),
        logging.StreamHandler()
    ]
)
#logging.addLevelName( logging.WARNING, "\033[1;31m%s\033[1;0m" % logging.getLevelName(logging.WARNING))
#logging.addLevelName( logging.ERROR, "\033[1;41m%s\033[1;0m" % logging.getLevelName(logging.ERROR))


class GtfsLoader:
    """
    Так как:
    1 некоторые *_id (например, route_id) в bustime используются в полях xeno_id,
    2 происходит переход от деления маршрутов по городам к маршрутам без городов,
    3 в разных gtfs-фидах маршруты, сервися, остановки и т.д. могут иметь одинаковые *_id
    мы модифицируем исходные *_id, добавив им наш GtfsCatalog.id
    См. функцию make_value()
    """
    id_fields = ['agency_id', 'route_id', 'network_id', 'shape_id', 'trip_id', 'service_id', 'stop_id', 'zone_id', 'block_id', 'level_id']

    # corrupted stops id list
    corrupted_stops = []

    # Constructor
    def __init__(self, DEBUG: bool=False, channel: str=None):
        self.DEBUG = DEBUG
        self.shapes_exists = False
        self.channel = channel # имя redis-канала для вывода сообщений

    def publish(self, msg:str='', level:str='info') -> NoReturn:
        if level == 'info':
            logging.info(msg)
        elif level == 'error':
            logging.error(msg)
        elif level == 'warning':
            logging.warning(msg)
        # else: no log

        if self.channel:
            msg = "<br />".join(msg.split("\n"))
            if level in ['error', 'warning']:
                sio_pub(self.channel, {"element": "load_result", "note": "<span class='ui red text'>%s</span>" % msg})
            else:
                sio_pub(self.channel, {"element": "load_result", "note": msg})
    # publish

    def make_value(self, field_name: str, field_value: any, catalog_id: int) -> any:
        if field_name in self.id_fields and type(field_value) == str:
            return "%s*%s" % (catalog_id, field_value)
        else:
            return field_value
    # make_value

    def remove_bom_from_file(self, filename: str) -> None:
        s = open(filename, mode='r', encoding='utf-8-sig').read()
        open(filename, mode='w', encoding='utf-8').write(s)
    # remove_bom_from_file

    # удаление содержимого папки
    def delete_files(self, folder: str) -> bool:
        if self.DEBUG: self.publish('Clear folder %s' % folder)
        retval = True
        for filename in os.listdir(folder):
            file_path = os.path.join(folder, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as ex:
                self.publish('Failed to delete %s. Reason: %s' % (file_path, ex), 'error')
                retval = False
        # for filename in os.listdir(folder)
        return retval
    # delete_files


    # скачивание архива с данными gtfs (фида)
    def catalog_download(self, catalog_id:int, url_schedule:str, request_auth:str=None) -> str:
        catalog = os.path.join(WORK_DIR, str(catalog_id))
        Path(catalog).mkdir(parents=True, exist_ok=True)    # create if not exists

        self.publish('Request catalog data for %s' % url_schedule)

        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36'}
        auth = None

        if request_auth:
            # authorization needded
            locals={"headers":None,"auth":None}
            exec(request_auth, None, locals)
            if locals["headers"]:
                add_headers = locals["headers"]
                if 'url_schedule' in add_headers:
                    headers.update(add_headers['url_schedule'])
                else:
                    headers.update(add_headers)
            elif locals["auth"]:
                auth = locals["auth"]
        # if request_auth

        try:
            get_response = requests.get(url_schedule, stream=True, headers=headers, auth=auth, timeout=10)
            if get_response.status_code != requests.codes.ok:
                get_response.raise_for_status()

            file_name = 'catalog.zip'
            try:
                file_name = pyrfc6266.requests_response_to_filename(get_response)   # берём имя файла из headers
            except:
                if get_response.headers.get('Content-Type') == 'application/zip':
                    file_name = get_response.headers.get('content-disposition')
                    if file_name:
                        file_name = file_name.split('=')[-1]

            if not Path(file_name).suffix:
                file_name = "%s.zip" % file_name

            file_save = os.path.join(catalog, file_name)

            self.publish('Save catalog data to %s' % file_save)
            with open(file_save, 'wb') as f:
                for chunk in get_response.iter_content(chunk_size=1024):
                    if chunk: # filter out keep-alive new chunks
                        f.write(chunk)
        except Exception as e:
            #err = traceback.format_exc(limit=2)
            self.publish(str(e), 'error')
            file_save = None

        return file_save
    # catalog_download


    # разархивирование архива с данными gtfs (фида)
    def unpack_catalog(self, catalog_id: int, catalog_file: str) -> str:
        file_name = os.path.basename(catalog_file)
        file_prefix = file_name.split('.')[0]
        file_suffix = file_name.split('.')[-1]

        arc_dir = os.path.join(WORK_DIR, str(catalog_id), file_prefix)

        try:
            if self.DEBUG: self.publish('Check folder %s' % arc_dir)
            Path(arc_dir).mkdir(parents=True, exist_ok=True)    # create if not exists

            self.delete_files(arc_dir)

            if file_suffix.lower() == 'zip':
                self.publish('Unzip %s to %s' % (catalog_file, arc_dir))
                with zipfile.ZipFile(catalog_file, 'r') as zip_ref:
                    zip_ref.extractall(arc_dir)
            else:
                raise Exception('Archive type %s is not supported' % file_suffix)
        except Exception as ex:
            self.publish(ex, 'error')
            arc_dir = None

        return arc_dir
    # unpack_catalog


    # Загрузка данных gtfs из папки с файлами (*.txt | *.csv) в БД
    def read_catalog(self, catalog_id: int, catalog_dir: str) -> int:
        self.publish('read_catalog %s' % catalog_dir)

        processed_files = 0

        # 20.04.23 достаточный набор данных, больше которого пока грузить не будем
        # могут отсутствовать:
        # feed_info, shapes;
        # либо calendar либо calendar_dates, https://gtfs.org/schedule/reference/#calendar_datestxt
        # порядок важен для последующей обработки
        enough_names = {
            'feed_info':        {'required': False, 'exists': False, 'name': None},
            'agency':           {'required': False, 'exists': False, 'name': None},
            'routes':           {'required': True, 'exists': False, 'name': None},
            'trips':            {'required': True, 'exists': False, 'name': None},
            'stops':            {'required': True, 'exists': False, 'name': None},
            'stop_times':       {'required': True, 'exists': False, 'name': None},
            'calendar':         {'required': False, 'exists': False, 'name': None},
            'calendar_dates':   {'required': False, 'exists': False, 'name': None},
            'shapes':           {'required': False, 'exists': False, 'name': None},
        }

        # проверяем наличие файлов
        for filename in os.listdir(catalog_dir):
            file_parts = filename.split('.')
            name = file_parts[0]
            ext = file_parts[-1] if len(file_parts) > 1 else None

            if name not in enough_names:
                continue

            # разрешено только *.txt | *.csv | без расширения
            if ext and ext not in ['txt', 'csv']:
                continue

            enough_names[name]['exists'] = True
            enough_names[name]['name'] = filename
        # for filename in os.listdir(catalog_dir)

        # проверяем, достаточно ли нам файлов
        for key, val in enough_names.items():
            if val['required'] and val['exists'] == False:
                self.publish(f'Not exists required file {key}', 'error')
                return processed_files

        if not enough_names['calendar']['exists'] and not enough_names['calendar_dates']['exists']:
            self.publish(f'Not exists files calendar & calendar_dates', 'warning')

        # грузим данные
        for key, val in enough_names.items():
            if not val['exists']:
                if key == 'feed_info':
                    self.load_feed_info(catalog_id, key)  # force to fill fields gps_data_provider*
                continue

            full_name = os.path.join(catalog_dir, val['name'])
            self.publish('loading %s' % val['name'])

            try:
                if key == 'feed_info':
                    self.load_feed_info(catalog_id, full_name)
                    processed_files += 1
                elif key == 'agency':
                    self.load_agency(catalog_id, full_name)
                    processed_files += 1
                elif key == 'routes':
                    self.load_routes(catalog_id, full_name)
                    processed_files += 1
                elif key == 'trips':
                    self.load_trips(catalog_id, full_name)
                    processed_files += 1
                elif key == 'stops': # must be before 'stop_times' for remove corrupted stops
                    self.load_stops(catalog_id, full_name)
                    processed_files += 1
                elif key == 'stop_times':
                    self.load_stop_times(catalog_id, full_name)
                    processed_files += 1
                elif key == 'shapes':
                    self.load_shapes(catalog_id, full_name)
                    processed_files += 1
                elif key == 'calendar':
                    self.load_calendar(catalog_id, full_name)
                    processed_files += 1
                elif key == 'calendar_dates':
                    self.load_calendar_dates(catalog_id, full_name)
                    processed_files += 1
            except Exception as e:
                self.publish("%s: %s" % (key, str(e)), 'error')
                if 'duplicate key value violates unique constraint' in str(e):
                    self.remove_db_data(catalog_id)
                    processed_files = 0
        # for filename in os.listdir(catalog_dir)

        return processed_files
    # read_catalog


    # удаление всех данных фида каталога catalog_id из БД
    def remove_db_data(self, catalog_id: int) -> NoReturn:
        if self.DEBUG: self.publish(f'Remove data for catalog id {catalog_id}')
        GtfsCalendarDates.objects.filter(catalog=catalog_id).delete()
        GtfsCalendar.objects.filter(catalog=catalog_id).delete()
        GtfsStopTimes.objects.filter(catalog=catalog_id).delete()
        GtfsStops.objects.filter(catalog=catalog_id).delete()
        GtfsTrips.objects.filter(catalog=catalog_id).delete()
        GtfsShapes.objects.filter(catalog=catalog_id).delete()
        GtfsRoutes.objects.filter(catalog=catalog_id).delete()
        GtfsAgency.objects.filter(catalog=catalog_id).delete()
    # remove_db_data


    # загрузка calendar_dates
    def load_calendar_dates(self, catalog_id: int, file_name: str) -> NoReturn:
        # удаляем старые данные
        GtfsCalendarDates.objects.filter(catalog=catalog_id).delete()

        self.remove_bom_from_file(file_name)

        with open(file_name,  mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            objs = []
            len_objs = 0

            for row in reader:
                obj = GtfsCalendarDates(catalog_id=catalog_id)
                for field in reader.fieldnames:
                    if field == 'date':
                        setattr(obj, field, datetime.datetime.strptime(row[field], "%Y%m%d").date())
                    else:
                        setattr(obj, field, self.make_value(field, row[field], catalog_id))

                objs.append(obj)
                if len(objs) >= 100000:
                    len_objs += len(objs)
                    GtfsCalendarDates.objects.bulk_create(objs)
                    del objs[:]
                    if self.DEBUG: self.publish('calendar_dates: %s rows' % len_objs)
            # for row in reader

            if len(objs) > 0:
                len_objs += len(objs)
                GtfsCalendarDates.objects.bulk_create(objs)
        # with open(file_name,  mode='r', encoding='utf-8') as f

        if self.DEBUG: self.publish('calendar_dates: %s rows' % len_objs)
    # load_calendar_dates


    # загрузка calendar
    def load_calendar(self, catalog_id: int, file_name: str) -> NoReturn:
        # удаляем старые данные
        GtfsCalendar.objects.filter(catalog=catalog_id).delete()

        self.remove_bom_from_file(file_name)

        with open(file_name,  mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            objs = []

            for row in reader:
                obj = GtfsCalendar(catalog_id=catalog_id)
                for field in reader.fieldnames:
                    if field in ['start_date', 'end_date']:
                        setattr(obj, field, datetime.datetime.strptime(row[field], "%Y%m%d").date())
                    else:
                        setattr(obj, field, self.make_value(field, row[field], catalog_id))

                objs.append(obj)

            GtfsCalendar.objects.bulk_create(objs)
        # with open(file_name,  mode='r', encoding='utf-8') as f

        if self.DEBUG: self.publish('calendar: %s rows' % len(objs))
    # load_calendar


    # загрузка stop_times, сотни тысяч строк
    def load_stop_times(self, catalog_id: int, file_name: str) -> NoReturn:
        # удаляем старые данные
        GtfsStopTimes.objects.filter(catalog=catalog_id).delete()

        self.remove_bom_from_file(file_name)

        with open(file_name,  mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            objs = []
            len_objs = 0

            for row in reader:
                if row['stop_id'] in self.corrupted_stops:
                    continue
                obj = GtfsStopTimes(catalog_id=catalog_id)
                for field in reader.fieldnames:
                    setattr(obj, field, self.make_value(field, row[field] if row[field] else None, catalog_id))

                objs.append(obj)
                if len(objs) >= 100000:
                    len_objs += len(objs)
                    GtfsStopTimes.objects.bulk_create(objs)
                    del objs[:]
                    if self.DEBUG: self.publish('stop_times: %s rows' % len_objs)
            # for row in reader

            if len(objs) > 0:
                len_objs += len(objs)
                GtfsStopTimes.objects.bulk_create(objs)
        # with open(file_name,  mode='r', encoding='utf-8') as f

        if self.DEBUG: self.publish('stop_times: %s rows' % len_objs)
    # load_stop_times


    # загрузка stops
    def load_stops(self, catalog_id: int, file_name: str) -> NoReturn:
        # удаляем старые данные
        GtfsStops.objects.filter(catalog=catalog_id).delete()

        self.remove_bom_from_file(file_name)

        with open(file_name,  mode='r', encoding='utf-8') as f:
            # https://docs.python.org/3/library/csv.html#csv.DictReader
            reader = csv.DictReader(f)
            objs = []

            for row in reader:
                obj = GtfsStops(catalog_id=catalog_id)
                point = {}
                for field in reader.fieldnames:
                    if field == 'stop_lat':
                        try:
                            point['stop_lat'] = float(row[field])
                        except:
                            point['stop_lat'] = 0.0
                    elif field == 'stop_lon':
                        try:
                            point['stop_lon'] = float(row[field])
                        except:
                            point['stop_lon'] = 0.0
                    else:
                        setattr(obj, field, self.make_value(field, row[field], catalog_id))
                # for field in reader.fieldnames

                if point and math.isnan(point['stop_lon']) == False and math.isnan(point['stop_lat']) == False:
                    pt = Point(point['stop_lon'], point['stop_lat'])
                    setattr(obj, 'stop_pt_loc', pt)
                    tz_info = timezone_finder.timezone_at(lng=pt.x, lat=pt.y)
                    setattr(obj, 'stop_timezone', tz_info)
                    objs.append(obj)
                else:   # бъект остановки не добавляем в список, пропускаем
                    self.corrupted_stops.append(row['stop_id'])  # obj.stop_id
                    if self.DEBUG: self.publish('SKIP STOP: %s' % (", ".join(row.values())), 'error')
            # for row in reader

            if len(objs) > 0:
                GtfsStops.objects.bulk_create(objs)
        # with open(file_name,  mode='r', encoding='utf-8') as f

        if len(self.corrupted_stops) > 0:
            if self.DEBUG: self.publish('corrupted_stops(%s): %s' % (len(self.corrupted_stops), self.corrupted_stops), 'warning')
        if self.DEBUG: self.publish('stops: %s rows' % len(objs))
    # load_stops


    # загрузка trips
    def load_trips(self, catalog_id: int, file_name: str) -> NoReturn:
        # удаляем старые данные
        GtfsTrips.objects.filter(catalog=catalog_id).delete()

        self.remove_bom_from_file(file_name)

        with open(file_name,  mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            objs = []
            len_objs = 0

            for row in reader:
                obj = GtfsTrips(catalog_id=catalog_id)
                for field in reader.fieldnames:
                    setattr(obj, field, self.make_value(field, row[field], catalog_id))

                objs.append(obj)
                if len(objs) >= 100000:
                    len_objs += len(objs)
                    GtfsTrips.objects.bulk_create(objs)
                    del objs[:]
                    if self.DEBUG: self.publish('trips: %s rows' % len_objs)
            # for row in reader

            if len(objs) > 0:
                len_objs += len(objs)
                GtfsTrips.objects.bulk_create(objs)
        # with open(file_name,  mode='r', encoding='utf-8') as f

        if self.DEBUG: self.publish('trips: %s rows' % len_objs)
    # load_trips


    # загрузка shapes, сотни тысяч строк
    def load_shapes(self, catalog_id: int, file_name: str) -> NoReturn:
        # удаляем старые данные
        GtfsShapes.objects.filter(catalog=catalog_id).delete()

        self.shapes_exists = os.path.isfile(file_name)

        if self.shapes_exists:
            self.remove_bom_from_file(file_name)

            with open(file_name,  mode='r', encoding='utf-8') as f:
                # https://docs.python.org/3/library/csv.html#csv.DictReader
                reader = csv.DictReader(f)
                objs = []
                len_objs = 0
                point = {}

                for row in reader:
                    obj = GtfsShapes(catalog_id=catalog_id)
                    for field in reader.fieldnames:
                        if field == 'shape_pt_lat':
                            point['shape_pt_lat'] = float(row[field])
                        if field == 'shape_pt_lon':
                            point['shape_pt_lon'] = float(row[field])
                        else:
                            setattr(obj, field, self.make_value(field, row[field], catalog_id))

                    if point:
                        setattr(obj, 'shape_pt_loc', Point(point['shape_pt_lon'], point['shape_pt_lat']))

                    objs.append(obj)
                    if len(objs) >= 100000:
                        len_objs += len(objs)
                        GtfsShapes.objects.bulk_create(objs)
                        del objs[:]
                        if self.DEBUG: self.publish('shapes: %s rows' % len_objs)
                # for row in reader

                if len(objs) > 0:
                    len_objs += len(objs)
                    GtfsShapes.objects.bulk_create(objs)
            # with open(file_name,  mode='r', encoding='utf-8') as f

            if self.DEBUG: self.publish('shapes: %s rows' % len_objs)
        else:
            if self.DEBUG: self.publish('shapes not exists')
    # load_shapes


    # загрузка routes
    def load_routes(self, catalog_id: int, file_name: str) -> NoReturn:
        # удаляем старые данные
        GtfsRoutes.objects.filter(catalog=catalog_id).delete()

        self.remove_bom_from_file(file_name)

        with open(file_name,  mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            objs = []

            for row in reader:
                obj = GtfsRoutes(catalog_id=catalog_id)
                for field in reader.fieldnames:
                    setattr(obj, field, self.make_value(field, row[field], catalog_id))
                objs.append(obj)

            GtfsRoutes.objects.bulk_create(objs)
        # with open(file_name,  mode='r', encoding='utf-8') as f

        if self.DEBUG: self.publish('routes: %s rows' % len(objs))
    # load_routes


    # загрузка feed_info
    # https://gtfs.org/ru/schedule/reference/#feed_infotxt
    def load_feed_info(self, catalog_id: int, file_name: str) -> NoReturn:
        if os.path.isfile(file_name):
            # файл существует (бывает, что и нет :)
            self.remove_bom_from_file(file_name)

            fields = {
                'feed_publisher_name': {'ds_field': 'gps_data_provider', 'value': None},
                'feed_publisher_url': {'ds_field': 'gps_data_provider_url', 'value': None},
                'feed_contact_email': {'ds_field': 'comment', 'value': None},
                'feed_contact_url': {'ds_field': 'check_url', 'value': None},
            }
            update_fields = []
            with open(file_name,  mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    for field in reader.fieldnames:
                        f = fields.get(field)
                        if f and row[field]:
                            f['value'] = row[field]
                            update_fields.append(f['ds_field'])
                    break

            if update_fields:
                # channel MUST be identical with e.channel in zbusd/gtfs_update.py
                ds, cr = DataSource.objects.get_or_create(channel=EVENT_CHANNEL, src=str(catalog_id))
                for v in fields.values():
                    if v['ds_field'] in update_fields and v['value']:
                        setattr(ds, v['ds_field'], v['value'])
                ds.save(update_fields=update_fields)
        else:
            ds, cr = DataSource.objects.get_or_create(channel=EVENT_CHANNEL, src=str(catalog_id))
            if ds.gps_data_provider_url is None or ds.gps_data_provider is None:
                cl = GtfsCatalog.objects.get(id=catalog_id)
                url = urlparse(cl.url_schedule)
                ds.gps_data_provider_url = f'{url.scheme}://{url.netloc}/'
                ds.gps_data_provider = url.netloc
                ds.save(update_fields=['gps_data_provider_url', 'gps_data_provider'])
                if self.DEBUG: self.publish('Force gps_data_provider to %s' % ds.gps_data_provider)
    # load_feed_info


    # загрузка agency
    def load_agency(self, catalog_id: int, file_name: str) -> NoReturn:
        # удаляем старые данные
        GtfsAgency.objects.filter(catalog=catalog_id).delete()

        objs = []

        if os.path.isfile(file_name):
            # файл существует (бывает, что и нет :)
            self.remove_bom_from_file(file_name)

            with open(file_name,  mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)

                for row in reader:
                    obj = GtfsAgency(catalog_id=catalog_id)
                    for field in reader.fieldnames:
                        setattr(obj, field, self.make_value(field, row[field], catalog_id))
                    objs.append(obj)

                GtfsAgency.objects.bulk_create(objs)
            # with open(file_name,  mode='r', encoding='utf-8') as f

        if self.DEBUG: self.publish('agency: %s rows' % len(objs))
    # load_agency


    # выполнение sql скриптов
    def processing_sql_sripts(self, catalog_id:int)->bool:
        executed, script_cnt = 0, 0

        for name_template in SCRIPTS_TEMPLATES:
            script = '%s/%s' % (SCRIPTS_DIR, name_template) % catalog_id
            slqs = []

            if os.path.isfile(script) or os.path.islink(script):
                with open(script) as f:
                    slqs = f.read().split(';')

            if slqs:
                script_cnt = len(slqs)-1
                if self.DEBUG: self.publish('Run afterload %s scripts' % script_cnt)
                with connections["gtfs"].cursor() as cursor:
                    for i in range(script_cnt):
                        sql = slqs[i].strip()
                        if self.DEBUG: self.publish(f'{i}: {sql}')
                        if sql:
                            try:
                                cursor.execute(sql)
                                executed += 1
                            except Exception as ex:
                                self.publish(f'Afterload script {i} of {script_cnt} in {script} error:', level='error')
                                self.publish(str(ex))
                # with connections
            # if slqs
        # for name_template

        return executed == script_cnt
    # processing_sql_sripts


    def load_gtfs(self, catalog_id:int=-1, zip_file:str=None, dir_files:str=None, to:int=0, force:bool=False) -> int:
        if zip_file and dir_files:
            raise Exception('Должен быть только один из параметров zip или dir')
        elif catalog_id < 0 and ((not zip_file) and (not dir_files)):
            raise Exception('Нет данных для новой записи')
        elif catalog_id == 0 and (zip_file or dir_files):
            raise Exception('catalog_id=0 и внешние данные несовместимы')
        elif to:
            if to < catalog_id:
                raise Exception(f'to ({to}) < catalog_id ({catalog_id})')
            elif (zip_file or dir_files):
                raise Exception('Параметр to и внешние данные несовместимы')

        created = False
        if catalog_id < 0:
            if zip_file:
                name = zip_file.split("/")[-1]
                url_schedule = zip_file
            elif dir_files:
                name = dir_files.split("/")[-1]
                url_schedule = dir_files

            catalog, created = GtfsCatalog.objects.get_or_create(name=name)
            if created:
                catalog.active=True
            catalog.url_schedule = url_schedule
            catalog.save()
            catalog_id = catalog.id

            if created:
                self.publish("Catalog %s" % catalog_id)
        # if not catalog_id

        loaded_catalogs = 0

        if zip_file:
            # уже скаченный архив с данными gtfs

            gtfs_dir = self.unpack_catalog(catalog_id, zip_file)
            if gtfs_dir:
                if self.read_catalog(catalog_id, gtfs_dir) > 0:
                    loaded_catalogs += 1

        elif dir_files:
            # уже распакованные данные gtfs находятся в каталоге

            if self.read_catalog(catalog_id, dir_files) > 0:
                loaded_catalogs += 1

        else:
            # данные из БД
            if force:
                catalogs = GtfsCatalog.objects.all()
            else:
                catalogs = GtfsCatalog.objects.filter(active=True)

            if catalog_id:
                if to >= catalog_id:
                    self.publish(f'Load catalogs from {catalog_id} to {to} ids')
                    catalogs = catalogs.filter(id__range=(catalog_id, to))
                else:
                    catalogs = catalogs.filter(id=catalog_id)

            catalogs = catalogs.order_by('id')

            if catalogs.count():
                for catalog in catalogs:
                    self.publish()
                    self.publish('Catalog %s: %s' % (catalog.id, catalog.url_schedule))

                    if not catalog.url_schedule:
                        self.publish('Skip: empty url_schedule')
                        if catalog.active:
                            GtfsCatalog.objects.filter(id=catalog.id).update(active=False)
                        continue

                    catalog_file, gtfs_dir = None, None
                    if catalog.url_schedule.startswith('http://') or catalog.url_schedule.startswith('https://'):
                        catalog_file = self.catalog_download(catalog.id, catalog.url_schedule, catalog.request_auth)
                    elif os.path.isfile(catalog.url_schedule) or os.path.islink(catalog.url_schedule):
                        catalog_file = catalog.url_schedule
                    elif os.path.isdir(catalog.url_schedule):
                        gtfs_dir = catalog.url_schedule

                    if catalog_file:
                        gtfs_dir = self.unpack_catalog(catalog.id, catalog_file)

                    if gtfs_dir:
                        if self.read_catalog(catalog.id, gtfs_dir) > 0:
                            loaded_catalogs += 1
                            catalog.active = self.processing_sql_sripts(catalog.id)
                        else:
                            catalog.active = False
                        catalog.save()
                # for catalog in catalogs
            # if catalogs.count()
            elif catalog_id:
                self.publish('Id %s not found in ACTIVE catalog' % (catalog_id))
            else:
                self.publish('Not found "Active" records in catalog')

        self.publish("%s catalog's loaded" % loaded_catalogs)

        if self.channel:
            sio_pub(self.channel, {"call": "load_controls_disabled", "argument": False})
        return loaded_catalogs
    # load_gtfs
# class GtfsLoader

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Загрузка gtfs данных из каталогов')
    parser.add_argument('catalog_id', type=int, metavar='catalog_id', help='-1:создать запись и обработать архив или папку; 0:обработать все существующие записи; N:обработать запись с id=N')
    parser.add_argument("--to", type=int, default=0, help="Обработать записи, начиная с id=catalog_id по to")
    parser.add_argument("--zip", help="Архив с данными gtfs")
    parser.add_argument("--dir", help="Папка с данными gtfs")
    parser.add_argument("--ch", help="Имя redis-канала для вывода сообщений")
    parser.add_argument("--debug", help="Вывод отладочных сообщений", action="store_true")
    parser.add_argument("--force", help="Обрабатывать записи с active=False", action="store_true")
    args = parser.parse_args()

    try:
        loader = GtfsLoader(args.debug, args.ch)
        loader.load_gtfs(args.catalog_id, args.zip, args.dir, args.to, args.force)
    except:
        err = traceback.format_exc(limit=4)
        loader.publish(err, 'error')