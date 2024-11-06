#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from devinclude import *
from bustime.models import *
from django.db.models import Q
from django.contrib.sessions.models import Session
from django.contrib.sessions.backends.db import SessionStore
import subprocess
from django import db
from bustime import settings
import glob
import os
import traceback
from django.db import transaction

# dont't run on virtual for better performance
if settings.DEV:
    print('dev env, exiting')
    sys.exit()

now = datetime.datetime.now()
year_ago = now - datetime.timedelta(days=365)
ms_then = now - datetime.timedelta(days=180)
then = now - datetime.timedelta(days=90)
yday = now - datetime.timedelta(days=1)
week_ago = now - datetime.timedelta(days=7)
two_weeks_ago = now - datetime.timedelta(days=14)
three_ago = now - datetime.timedelta(days=3)
month_ago = now - datetime.timedelta(days=32)

def flog(s):
    f = open('/tmp/clean.log','a')
    f.write("%s\n" % s)
    f.close()
    #print s


def sessions_remove(then):
    """
    Итерация по сессиям с обработкой по частям.
    """
    batch_size = 10000  # Размер одной партии для обработки
    last_pk = 0
    todel = []
    cnt, dcnt = 0, 0
    while True:
        with transaction.atomic():
            # expire_date limit to skip fresh invalid sessions with data={} (todo: investigate why)
            sessions = Session.objects.filter(pk__gt=last_pk, expire_date__lt=month_ago+datetime.timedelta(days=10*365)).order_by('pk')[:batch_size]
            if len(todel) >= batch_size or not sessions:
                #print(datetime.datetime.now(), '[DELETE]', cnt)
                d = Session.objects.filter(pk__in=todel).delete()
                #print(datetime.datetime.now(), '[DONE]')
                todel = []

            if not sessions:
                return dcnt
            for ses in sessions:
                key, data = ses.pk, SessionStore().decode(ses.session_data)
                cnt += 1
                if data and data.get('last_login'):
                    ll = datetime.datetime.strptime(data['last_login'], "%Y-%m-%d")
                    if ll < then:
                        data = None
                else:
                    #print("[BAD]", ses.session_key, data, ses.expire_date)
                    data = None
                if not data:
                    todel.append(key)
                    dcnt += 1
                last_pk = ses.pk


# for cron log
print("%s" % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

flog("\n%s Start clean" % datetime.datetime.now())
REDIS_W.delete("not_found")
flog('metric_web')
cnt = 0
from_date = (now - datetime.timedelta(hours=24)).date()
places = Place.objects.filter(buses_count__gt=0)
dau_list_web = UserSettings.objects.filter(ltime__gte=from_date).values_list("place_id", flat=True)
dau_list_web = [x for x in dau_list_web]
dau_list_app = MobileSettings.objects.filter(ltime__gte=from_date).values_list("place_id", flat=True)
dau_list_app = [x for x in dau_list_app]
for place in places:
    dau_web = dau_list_web.count(place.id)
    dau_app = dau_list_app.count(place.id)
    metric_web, cr = Metric.objects.get_or_create(date=from_date, name="dau_web_%s" % place.id)
    metric_web.count = dau_web
    metric_web.save()
    metric_app, cr = Metric.objects.get_or_create(date=from_date, name="dau_app_%s" % place.id)
    metric_app.count = dau_app
    metric_app.save()
    cnt += 1
flog("%s updated\n" % cnt)

#ut_qs = UserTimer.objects.filter(date__lte=week_ago.date())
#print "usertimer: to delete %s, from %s" % ( ut_qs.count(), UserTimer.objects.all().count())

flog(datetime.datetime.now())
flog('Log')
lg_ul = Log.objects.filter(ttype__in=["update_lib", "get_bus_by_name", "dchange", "error_update", "gps_send", "weather"]).filter(date__lte=yday)
cnt, _ = lg_ul.delete()
flog("%s deleted\n" % cnt)

flog(datetime.datetime.now())
flog('Log-all')
log_all = Log.objects.filter().filter(date__lte=then)
cnt, _ = log_all.delete()
flog("%s deleted\n" % cnt)

flog(datetime.datetime.now())
flog('clean_usersettings.sql')
start=datetime.datetime.now()
cmd = [
    "psql",
    "postgresql://%s:%s@%s:%s/%s" %(settings.DATABASES['default']['USER'], settings.DATABASES['default']['PASSWORD'], settings.DATABASES['default']['HOST'], settings.DATABASES['default']['PORT'], settings.DATABASES['default']['NAME']),
    "-v",
    "ON_ERROR_STOP=ON",
    "-f",
    "/bustime/bustime/utils/clean_usersettings.sql"
]
try:
    result = subprocess.check_output(cmd).decode("utf8")
    flog("UserSettings: %s in %s\n" % (result.replace('\n', ''), datetime.datetime.now()-start))
except:
    flog(traceback.format_exc(limit=2))
    flog("UserSettings: in %s\n" % (datetime.datetime.now()-start))

flog(datetime.datetime.now())
flog('MoTheme')
mozero = MoTheme.objects.filter(counter=0)
cnt, _ = mozero.delete()
flog("%s deleted\n" % cnt)

flog(datetime.datetime.now())
flog('Uevent')
cmd = [
    "psql",
    "postgresql://%s:%s@%s:%s/%s" %(settings.DATABASES['bstore']['USER'], settings.DATABASES['bstore']['PASSWORD'], settings.DATABASES['bstore']['HOST'], settings.DATABASES['bstore']['PORT'], settings.DATABASES['bstore']['NAME']),
    "-v",
    "ON_ERROR_STOP=ON",
    "-c",
    "DELETE FROM bustime_uevent WHERE timestamp < '%s' or timestamp > current_timestamp + interval '86400' second;" % two_weeks_ago.date().strftime("%Y-%m-%d 00:00:00")
]
try:
    result = subprocess.check_output(cmd).decode("utf8")
    flog("Uevent: %s in %s\n" % (result.replace('\n', ''), datetime.datetime.now()-start))
except:
    flog(traceback.format_exc(limit=2))
    flog("Uevent: in %s\n" % (datetime.datetime.now()-start))


flog(datetime.datetime.now())
flog('Jams')
cmd = [
    "psql",
    "postgresql://%s:%s@%s:%s/%s" %(settings.DATABASES['bstore']['USER'], settings.DATABASES['bstore']['PASSWORD'], settings.DATABASES['bstore']['HOST'], settings.DATABASES['bstore']['PORT'], settings.DATABASES['bstore']['NAME']),
    "-v",
    "ON_ERROR_STOP=ON",
    "-c",
    "DELETE FROM bustime_jam WHERE create_time < '%s';" % week_ago.date().strftime("%Y-%m-%d 00:00:00")
]
try:
    result = subprocess.check_output(cmd).decode("utf8")
    flog("Jams: %s in %s\n" % (result.replace('\n', ''), datetime.datetime.now()-start))
except:
    flog(traceback.format_exc(limit=2))
    flog("Jams: in %s\n" % (datetime.datetime.now()-start))

flog(datetime.datetime.now())
flog('jams_daily')
jams_daily = JamDaily.objects.filter(date__lt=week_ago.date())
cnt, _ = jams_daily.delete()
flog("%s deleted\n" % cnt)

flog(datetime.datetime.now())
flog('VehicleStatus')
vs = VehicleStatus.objects.filter(city_time__lt=month_ago.date())
cnt, _ = vs.delete()
flog("%s deleted\n" % cnt)

flog(datetime.datetime.now())
flog('VehicleStatus 2')
query = """WITH VS_YDAY as (SELECT *, COUNT(uniqueid) over (partition by uniqueid, bus) AS cnt
                                FROM bustime_vehiclestatus
                                WHERE DATE_TRUNC('day', city_time) = TO_DATE('%s', 'YYYY-MM-DD')
                                ORDER BY uniqueid, city_time)
            SELECT id FROM VS_YDAY WHERE cnt <= %s""" % (yday, 5)
try:
    vs = VehicleStatus.objects.raw(query)
    cnt = 0
    for vehicle in vs.iterator():
        vehicle.delete()
        cnt += 1
    flog("%s deleted\n" % cnt)
except:
    flog(traceback.format_exc(limit=2))


flog(datetime.datetime.now())
flog('DataSourceStatus')
cs = DataSourceStatus.objects.filter(ctime__lt=then.date())
cnt, _ = cs.delete()
flog("%s deleted\n" % cnt)

flog(datetime.datetime.now())
flog('DataSourcePlaceEventsCount')
cs = DataSourcePlaceEventsCount.objects.filter(ctime__lt=two_weeks_ago.date())
cnt, _ = cs.delete()
flog("%s deleted\n" % cnt)

flog(datetime.datetime.now())
flog('PassengerStat')
cs = PassengerStat.objects.using('bstore').filter(ctime__lt=year_ago)
cnt, _ = cs.delete()
flog("%s deleted\n" % cnt)


# удаление старых сессий
# flog("clean_sessions.sql") # не работает, возможно в django изменили формат сериализации
start=datetime.datetime.now()
flog(start)
result = sessions_remove(then)
flog("Sessions: %s in %s\n" % (result, datetime.datetime.now()-start))

flog(datetime.datetime.now())
flog("Revision")
cnt, _ = Revision.objects.filter().filter(date_created__lt=year_ago).delete()
flog("%s deleted\n" % cnt)

# удаление старых city-*-*.js и jamline-*-*.js
flog(datetime.datetime.now())
flog("remove old city-*-*.js & jamline-*-*.js")
start=datetime.datetime.now()

city_cnt, jam_cnt = 0, 0
for city in City.objects.all().order_by('id'):
    current = "%s/../bustime/static/js/city-%s-%s.js" % (settings.STATIC_ROOT, city.id, city.rev)
    for fpath in glob.glob("%s/../bustime/static/js/city-%s-*.js" % (settings.STATIC_ROOT, city.id)):
        if fpath != current:
            flink = "%s/js/%s" % (settings.STATIC_ROOT, os.path.basename(fpath))
            try:
                os.unlink(flink)
            except:
                pass
            os.remove(fpath)
            city_cnt += 1

    current = "%s/../bustime/static/js/jamline_%s_%s.js" % (settings.STATIC_ROOT, city.id, city.rev)
    for fpath in glob.glob("%s/../bustime/static/js/jamline_%s_*.js" % (settings.STATIC_ROOT, city.id)):
        if fpath != current:
            flink = "%s/js/%s" % (settings.STATIC_ROOT, os.path.basename(fpath).replace("_", "-"))
            try:
                os.unlink(flink)
            except:
                pass
            os.remove(fpath)
            jam_cnt += 1
# for city in City.objects.all().order_by('id')
flog("Deleted city-*-*.js %d, jamline-*-*.js %d in %s\n" % (city_cnt, jam_cnt, datetime.datetime.now()-start))

db.connection.close()

flog(datetime.datetime.now())
flog("[clean done]\n")

flog("DB vacuum")
with connection.cursor() as cursor:
    cursor.execute("VACUUM;")
flog(datetime.datetime.now())
flog("[DB vacuum done]\n")

flog('Total: %s' % (datetime.datetime.now() - now))
