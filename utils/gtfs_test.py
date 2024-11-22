#!/bustime/bustime/.venv/bin/python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from devinclude import *
from bustime.models import *
from bustime.views import *
import argparse
from pathlib import Path
import zipfile
import csv
import shutil
import pyrfc6266


def remove_bom_from_file(filename):
    s = open(filename, mode='r', encoding='utf-8-sig').read()
    open(filename, mode='w', encoding='utf-8').write(s)
# remove_bom_from_file


def test_feed(url, file):
    WORK_DIR = '/bustime/bustime/utils/automato/test'
    #fff = open('/bustime/bustime/utils/automato/test/debug.txt', 'w')
    #fff.write("views.ajax_gtfs_test_trip()\n")

    res = {
        "error": None,
        "result": 0
    }

    # https://gtfs.org/ru/schedule/reference/
    try:
        # загрузка gtfs данных
        downloaded = 0
        if url:
            # download from url
            sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "url: %s" % url})

            get_response = requests.get(url, stream=True)

            #file_name  = url.split("/")[-1]    # в ссылке не всегда есть имя файла в явном/удобном виде
            file_name = pyrfc6266.requests_response_to_filename(get_response)   # берём имя файла из headers
            sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "feed name: %s" % file_name})

            if not Path(file_name).suffix:
                file_name = "%s.zip" % file_name

            file_name = os.path.join(WORK_DIR, file_name)
            sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "file: %s" % file_name})

            # удаление содержимого рабочей папки
            for filename in os.listdir(WORK_DIR):
                file_path = os.path.join(WORK_DIR, filename)
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)

            with open(file_name, 'wb') as f:
                for chunk in get_response.iter_content(chunk_size=1024*1024):
                    if chunk: # filter out keep-alive new chunks
                        f.write(chunk)
                        downloaded += len(chunk)
                        sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "downloaded: %s Kb" % round(downloaded / 1024, 1)})
        elif file:
            # uploaded file
            file_name = file
            sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "file: %s" % file_name})

            # удаление содержимого рабочей папки
            for filename in os.listdir(WORK_DIR):
                file_path = os.path.join(WORK_DIR, filename)
                if (os.path.isfile(file_path) or os.path.islink(file_path)) and file_path != file_name:
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
        else:
            raise ValueError('Нет данных для анализа')

        # разархивирование архива с данными gtfs
        file_suffix = file_name.split('.')[-1]
        if file_suffix.lower() == 'zip':
            sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "unzip..."})
            with zipfile.ZipFile(file_name, 'r') as zip_ref:
                zip_ref.extractall(WORK_DIR)
        else:
            raise ValueError('Архив %s не поддерживается' % file_suffix)

        # Загрузка данных gtfs
        sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "sorting..."})
        ordered_items = ['trips', 'calendar', 'calendar_dates', 'stops', 'stop_times', 'routes', 'shapes', 'agency']
        # сортируем файлы в папке в нужный нам порядок
        for filename in os.listdir(WORK_DIR):
            file_parts = filename.split('.')

            prefix = file_parts[0]
            if prefix not in ordered_items:
                continue

            # разрешено только *.txt | *.csv | без расширения
            if len(file_parts) > 1 and file_parts[-1] not in ['txt', 'csv']:
                continue

            if prefix in ordered_items:
                # заменяем именем файла
                ordered_items[ordered_items.index(prefix)] = filename
        # for filename in os.listdir(WORK_DIR)

        # грузим данные
        services = []
        trips = []
        routes = []
        stops = []
        date_min = datetime.datetime.now().date()
        date_max = datetime.datetime.strptime('1970-01-01', '%Y-%m-%d').date()

        calendar_services_exists = 0
        calendar_services_not_exists = 0
        stops_in_trips = 0
        routes_in_trips = 0
        routes_valid_in_trips = 0
        routes_by_types = {
            '0': {'type': 'Трамвай', 'count': 0},
            '3': {'type': 'Автобус', 'count': 0},
            '11': {'type': 'Троллейбус', 'count': 0},
        }
        route_valid_types = list(GTFS_ROUTE_TYPE.keys())
        route_invalid_types = []

        warning_errors = 0  # ошибки, могущие повлиять на импорт маршрутов
        trips_breaked = False   # флаг: загрузка трипов прервана, так как их слишком много

        for filename in ordered_items:
            prefix = filename.split('.')[0]
            full_name = os.path.join(WORK_DIR, filename)

            if not os.path.isfile(full_name):
                sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "<br><span class='ui red text'><b>%s</b> not exists!</span>" % filename})
                if prefix in ['trips', 'stops', 'stop_times', 'routes']:
                    sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "<span class='ui red text'>ATTENTION: GTFS DATA IS CORRUPTED!</span>"})
                elif prefix == 'shapes':
                    sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "<span class='ui red text'>WARNING</span>: the route paths will be built by stops"})
                elif prefix == 'agency':
                    sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "<span class='ui red text'>WARNING</span>: routes will be loaded without agencies"})
                continue
            # if not os.path.isfile(full_name)

            sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "<br><b>loading %s</b><br>readed 0 rows" % filename})
            remove_bom_from_file(full_name)

            with open(full_name,  mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = 0

                if prefix == 'trips':
                    for row in reader:
                        rows += 1
                        if row['service_id'] not in services:
                            services.append(row['service_id'])
                        if row['trip_id'] not in trips:
                            trips.append(row['trip_id'])
                        if row['route_id'] not in routes:
                            routes.append(row['route_id'])
                        if rows % 1000 == 0:
                            sio_pub("ru.bustime.gtfs_test", {
                                    "element": "test_result",
                                    "note": "readed %s rows: %s services, %s routes" % (rows, len(services), len(routes))
                                }
                            )

                        if rows > 100000 and len(services) > 0 and len(routes) > 0:
                            sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "too many rows, break"})
                            trips_breaked = True
                            break   # слишком долго ждать все строки, ясно, что данные есть
                    # for row in reader

                    if trips_breaked:
                        note = "break over %s rows: %s services, %s routes" % (rows, len(services), len(routes))
                    else:
                        note = "readed %s rows: %s services, %s routes" % (rows, len(services), len(routes))
                    sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": note})

                    if len(services) == 0:
                        sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "<span class='ui red text'>ERROR</span>: services not found"})
                        raise ValueError('GTFS DATA IS CORRUPTED')
                    elif len(trips) == 0:
                        sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "<span class='ui red text'>ERROR</span>: trips not found"})
                        raise ValueError('GTFS DATA IS CORRUPTED')
                    elif len(routes) == 0:
                        sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "<span class='ui red text'>ERROR</span>: routes not found"})
                        raise ValueError('GTFS DATA IS CORRUPTED')

                elif prefix == 'calendar':
                    for row in reader:
                        rows += 1

                        if row['service_id'] in services:
                            calendar_services_exists += 1

                            start_date = datetime.datetime.strptime(row['start_date'], "%Y%m%d").date()
                            if date_min > start_date:
                                date_min = start_date

                            end_date = datetime.datetime.strptime(row['end_date'], "%Y%m%d").date()
                            if date_max < end_date:
                                date_max = end_date
                        elif not trips_breaked:
                            calendar_services_not_exists += 1

                        if rows % 1000 == 0:
                            sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "readed %s rows" % rows})
                    # for row in reader
                    sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "readed %s rows" % rows})

                    if not trips_breaked:
                        sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "corrupted services: %s" % calendar_services_not_exists})
                    sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "<b>correct services: %s</b>" % calendar_services_exists})

                elif prefix == 'calendar_dates':
                    if calendar_services_exists == 0:
                        for row in reader:
                            rows += 1

                            if row['exception_type'] == '1':    # Услуга была добавлена на указанную дату
                                if row['service_id'] in services:
                                    calendar_services_exists += 1
                                    start_date = datetime.datetime.strptime(row['date'], "%Y%m%d").date()

                                    if date_min > start_date:
                                        date_min = start_date
                                    if date_max < start_date:
                                        date_max = start_date
                                # if row['service_id'] in services
                                elif not trips_breaked:
                                    calendar_services_not_exists += 1
                            # if row['exception_type'] == '1'

                            if rows % 1000 == 0:
                                sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "readed %s rows" % rows})

                            if rows > 50000:
                                sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "too many rows, break"})
                                break   # слишком долго ждать все строки, ясно, что данные есть
                        # for row in reader

                        if rows > 50000:
                            sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "break over %s rows, its OK" % rows})
                        else:
                            sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "readed %s rows" % rows})
                    # if calendar_services_exists == 0
                    else:
                        sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "we skip it because the services are found in calendar"})

                elif prefix == 'stops':
                    stops_errors = []
                    for row in reader:
                        rows += 1
                        if row['stop_id'] not in stops:
                            location_type = row.get('location_type', '0')   # бывает, что поля location_type нет
                            if location_type not in ['2', '3', '4'] and row.get('stop_lat', 'NaN') != 'NaN' and row.get('stop_lon', 'NaN') != 'NaN':
                                stops.append(row['stop_id'])
                            else:
                                stops_errors.append( ", ".join(row.values()) )

                        if rows % 1000 == 0:
                            sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "readed %s rows" % rows})
                    # for row in reader
                    sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "readed %s rows" % rows})
                    sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "<b>valid stops found: %s</b>" % len(stops)})

                    if stops_errors:
                        sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "<span class='ui red text'><b>invalid stops found: %s</b></span>" % len(stops_errors)})
                        for s in stops_errors:
                            sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": s})
                        sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "<span class='ui red text'><b>trips with this stops is not valid!</b></span>"})
                        warning_errors += len(stops_errors)

                elif prefix == 'stop_times':
                    trips_invalid_by_lost = []
                    trips_invalid_by_stop = []

                    for row in reader:
                        rows += 1

                        if row['trip_id'] in trips:
                            if row['stop_id'] in stops:
                                stops_in_trips += 1
                            else:
                                trips_invalid_by_stop.append( ", ".join(row.values()) )
                        elif not trips_breaked:
                            trips_invalid_by_lost.append( ", ".join(row.values()) )

                        if rows % 1000 == 0:
                            sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "readed %s rows" % rows})

                        if rows > 50000:
                            sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "too many rows, break"})
                            break   # слишком долго ждать все строки, ясно, что данные есть
                    # for row in reader

                    if rows > 50000:
                        sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "break over %s rows, its OK" % rows})
                        sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "<b>stops on routes: over %s</b>" % stops_in_trips})
                    else:
                        sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "readed %s rows" % rows})
                        sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "<b>stops on routes: %s</b>" % stops_in_trips})

                    if trips_invalid_by_stop:
                        sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "<span class='ui red text'><b>trips invalid by stops: %s</b></span>" % len(trips_invalid_by_stop)})
                        warning_errors += len(trips_invalid_by_stop)
                    if (not trips_breaked) and trips_invalid_by_lost:
                        sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "<span class='ui red text'><b>trips invalid by lost: %s</b></span>" % len(trips_invalid_by_lost)})
                        warning_errors += len(trips_invalid_by_lost)

                elif prefix == 'routes':
                    for row in reader:
                        rows += 1

                        if row['route_id'] in routes:
                            routes_in_trips += 1

                        if row['route_type'] in ['0', '3', '11']:
                            if row['route_id'] in routes:
                                routes_valid_in_trips += 1
                                routes_by_types[row['route_type']]['count'] += 1
                        elif row['route_type'] not in route_invalid_types and int(row['route_type']) not in route_valid_types:
                            route_invalid_types.append(row['route_type'])

                        if rows % 1000 == 0:
                            sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "readed %s rows" % rows})
                    # for row in reader
                    sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "readed %s rows" % rows})

                    sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "<b>routes: %s</b>" % routes_in_trips})
                    for k, v in routes_by_types.items():
                        sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "%s %s: %s" % (k, v['type'], v['count'])})

                    if len(route_invalid_types) > 0:
                        sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "<span class='ui red text'>WARNING</span>: undocumented route types: %s" % ', '.join(str(x) for x in route_invalid_types)})

                    if routes_valid_in_trips == 0:
                        sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "<span class='ui red text'>WARNING</span>: routes for types 0, 3, 11 were not found, perhaps the type is undocumented"})

                elif prefix == 'shapes':
                    """
                    for row in reader:
                        rows += 1
                        if rows % 1000 == 0:
                            sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "readed %s rows" % rows})
                    # for row in reader
                    sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "readed %s rows" % rows})
                    """
                    f.seek(0, os.SEEK_END)
                    if f.tell() > 100:  # bytes
                        sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "<b>shapes exists</b>"})
                    else:
                        sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "<b>shapes not exists</b>"})

                elif prefix == 'agency':
                    for row in reader:
                        rows += 1
                        if rows % 1000 == 0:
                            sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "readed %s rows" % rows})
                    # for row in reader
                    sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "readed %s rows" % rows})

                    sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "<b>agencies: %s</b>" % rows})
                    if rows == 0:
                        sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "<span class='ui red text'>WARNING</span>: routes will be loaded without agencies"})

            # with open(full_name
        # for filename in ordered_items

        sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "<br><b>Results</b>"})
        if calendar_services_not_exists >= len(services):
            sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "<span class='ui red text'>ATTENTION: corrupted services &gt; correct services</span>"})
        elif stops_in_trips == 0:
            sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "<span class='ui red text'>ERROR: stops in routes not found</span>"})
            raise ValueError('GTFS DATA IS CORRUPTED')
        elif routes_in_trips == 0:
            sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "<span class='ui red text'>ERROR: worked routes not found</span>"})
            raise ValueError('GTFS DATA IS CORRUPTED')

        sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "min. date: %s" % datetime.datetime.strftime(date_min, '%Y-%m-%d')})
        sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "<b>max date: %s</b>" % datetime.datetime.strftime(date_max, '%Y-%m-%d')})

        if date_max < datetime.datetime.now().date():
            sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "<span class='ui red text'>WARNING</span>: the GTFS data is outdated, use '-d %s' parameter for import" % datetime.datetime.strftime(date_max, '%Y-%m-%d')})

        if routes_valid_in_trips == 0:
            sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "<span class='ui red text'>WARNING</span>: routes types is undocumented"})
        elif routes_valid_in_trips > 0 and routes_valid_in_trips < routes_in_trips:
            sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "<span class='ui red text'>WARNING</span>: exists routes with types is undocumented"})

        if warning_errors > 0:
            sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "<span class='ui orange text'><b>GTFS data may by imported, but with errors</b></span>"})
            sio_pub("ru.bustime.gtfs_test", {"element": "test_result_header", "note": "<span class='ui yellow text'><b>Schedule OK</b></span>"})
        else:
            sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "<span class='ui green text'><b>GTFS data may by imported</b></span>"})
            sio_pub("ru.bustime.gtfs_test", {"element": "test_result_header", "note": "<span class='ui green text'><b>Schedule OK</b></span>"})

        ############

    except ValueError as er:
        #res["error"] = str(er)
        res["error"] = "<br />".join(traceback.format_exc(limit=2).split("\n"))
        sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "<span class='ui red text'><b>ATTENTION: GTFS DATA IS CORRUPTED!</b></span>"})
        sio_pub("ru.bustime.gtfs_test", {"element": "test_result_header", "note": "<span class='ui red text'><b>Schedule ERROR</b></span>"})
    except:
        res["error"] = "<br />".join(traceback.format_exc(limit=2).split("\n"))
        sio_pub("ru.bustime.gtfs_test", {"element": "test_result", "note": "<span class='ui red text'><b>ATTENTION: GTFS DATA IS CORRUPTED!</b></span>"})
        sio_pub("ru.bustime.gtfs_test", {"element": "test_result_header", "note": "<span class='ui red text'><b>Schedule ERROR</b></span>"})

    sio_pub("ru.bustime.gtfs_test", {"call": "tools_controls_disabled", "argument": False})
    return res
# test_feed


# entry point for used from console
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='GTFS data test')
    parser.add_argument('method', type=str, help='test method')
    parser.add_argument('-u', '--url', type=str, help='data url', default=None)
    parser.add_argument('-f', '--file', type=str, help='data file', default=None)
    args = parser.parse_args()
    #print(args)

    if args.method in locals():
        locals()[args.method](args.url, args.file)
    else:
        print('Method "%s" not found')
