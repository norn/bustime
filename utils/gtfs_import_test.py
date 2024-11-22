from devinclude import *
from bustime.models import *    # fill_routeline, fill_order, cache_reset_bus, fill_bus_endpoints
from django.db.models import Q, Subquery, Count

LOG_FILE = 'gtfs_import_test.log'
WORK_DIR = '/tmp/'
#WORK_DIR = '/bustime/bustime/utils/automato'


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%d-%m-%y %H:%M:%S",
    handlers=[
        logging.FileHandler("%s/%s" % (WORK_DIR, LOG_FILE), 'w'),
        logging.StreamHandler()
    ]
)
logging.addLevelName( logging.WARNING, "\033[1;31m%s\033[1;0m" % logging.getLevelName(logging.WARNING))
logging.addLevelName( logging.ERROR, "\033[1;41m%s\033[1;0m" % logging.getLevelName(logging.ERROR))


def get_actual_services(catalog_id:int) -> django.db.models.query.QuerySet:
    date = datetime.datetime.now().date()

    # TODO: GtfsCalendar может быть пустым, тогда сервисы берутся из GtfsCalendarDates
    calendar = GtfsCalendar.objects.filter(catalog_id=catalog_id)

    logging.info(f"actual date is {date}")

    if len(calendar) > 0:   # есть календарь
        max_date_record = calendar.latest('end_date')
        if max_date_record.end_date < date:
            # фид просрочен - даты в календаре старые
            logging.info(f"maximum data date is {max_date_record.end_date}")
            date = max_date_record.end_date # берём данные на последнюю дату

        weekday = date.weekday()
        logging.info(f"{date} is {WEEK_DAYS[weekday]}")

        # exception_type
        # 1 - Услуга была добавлена на указанную дату
        # 2 - Услуга была удалена для указанной даты
        actual_services1 = calendar.filter(
                                Q(start_date__lte=date) & Q(end_date__gte=date) # дата в промежутке start_date and end_date
                                &Q(**{WEEK_DAYS[weekday]:1})                    # и день недели соостветствует дате
                            ).exclude(
                                # и сервис не выключен в указанную дату
                                service_id__in=Subquery(GtfsCalendarDates.objects.filter(
                                                                                            catalog=catalog_id,
                                                                                            date=date,
                                                                                            exception_type=2
                                                                                        ).values('service_id').distinct('service_id'))
                            ).values('service_id').distinct('service_id')

        # исключения из расписания
        # сервисы добавленные на указанную дату и которых нет в actual_services1
        actual_services2 = GtfsCalendarDates.objects.filter(catalog=catalog_id, date=date, exception_type=1).exclude(catalog=catalog_id, service_id__in=actual_services1).values('service_id').distinct('service_id')

        # union: сервисы действующие на указанную дату + сервисы добавленные на указанную дату
        actual_services = actual_services1.union(actual_services2)
    # if len(calendar) > 0
    else:
        # нет календаря
        logging.info(f"calendar is empty")
        # попытаемся получить актуальные сервисы из CalendarDates
        actual_services1 = GtfsCalendarDates.objects.filter(
                                                        catalog=catalog_id,
                                                        exception_type=1
                                                    ).filter(
                                                        Q(date__lte=date)
                                                    ).values('service_id').distinct('service_id')
        if actual_services1:
            logging.info(f"get services from calendardates")
            # есть актуальные сервисы
            actual_services = actual_services1.exclude(
                                # сервис не выключен в указанную дату
                                service_id__in=Subquery(GtfsCalendarDates.objects.filter(catalog=catalog_id, date=date, exception_type=2).values('service_id').distinct('service_id'))
                            ).values('service_id')
        else:
            # CalendarDates, похоже, пуст
            logging.info(f"get services from trips")
            actual_services1 = GtfsTrips.objects.filter(catalog=catalog_id).values('service_id', 'route_id').distinct()
            actual_services =  actual_services1.values('service_id').distinct('service_id')


    logging.info(f"{len(actual_services)} actual services")

    return actual_services
# get_actual_services


catalog_id = 272
actual_services = get_actual_services(catalog_id)

actual_trips = GtfsTrips.objects.filter(catalog=catalog_id, service_id__in=actual_services)

logging.info(f"{len(actual_trips)} actual trips")

routes = GtfsRoutes.objects.filter(catalog=catalog_id, route_id__in=Subquery(actual_trips.values('route_id').distinct('route_id'))).order_by('route_short_name')

services = GtfsTrips.objects.filter(catalog=catalog_id, route_id__in=map(operator.attrgetter('id'), routes))

print(f"SERVICES {services} {list(map(operator.attrgetter('id'), routes))}")

agency_ids = set(map(operator.attrgetter('agency_id'), routes))

print(f"AGENCY_IDS {agency_ids}")

agencies = {key: val for key, val in itertools.zip_longest(agency_ids, GtfsAgency.objects.filter(agency_id__in=agency_ids))}

print(f"AGENCIES {agencies}")


# TODO: make a dict
bus_providers = BusProvider.objects.filter(
    name__in=(agency.agency_name for agency in agencies.values() if agency is not None),
    phone__in=(agency.agency_name for agency in agencies.values() if agency is not None),
    email__in=(agency.agency_email for agency in agencies.values() if agency is not None))


# # выбираем сервисы маршрута: должен быть 1 на каждую дату, но, если больше, берём первый
# service = GtfsTrips.objects.filter(catalog=catalog_id, route_id=route.route_id, service_id__in=actual_services).first()
# # if not service: continue
# logging.info(f"      service: id:{service.service_id}")

# # выбираем трипы маршрута-сервиса, может быть много, берём по одному с direction_id='0'  и direction_id='1'
# trips0 = GtfsTrips.objects.filter(catalog=catalog.id, route_id=route.route_id, service_id=service.service_id, direction_id='0').first()
# trips1 = GtfsTrips.objects.filter(catalog=catalog.id, route_id=route.route_id, service_id=service.service_id, direction_id='1').first()
# if not trips0 and not trips1:   #  direction_id=NULL
#     trips0 = GtfsTrips.objects.filter(catalog=catalog.id, route_id=route.route_id, service_id=service.service_id).first()
# trips = [trips0, trips1]

# # запись маршрута
# #startswith = "%s*" % catalog.id
