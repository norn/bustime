#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from devinclude import *
from bustime.models import *
from bustime.views import *
import argparse

BLOCKED = {11: [3368, 3369, 3901, 8232, 8235]}
cc_key = "route_auto"

def route_updater(city, DEBUG=False):
    cnt_all = 0
    cnt = 0
    sort_order = ['direction', 'order']
    for b in Bus.objects.filter(city_id=city.id).order_by('order'):
        cnt_all += 1
        qs = Route.objects.filter(bus=b).order_by(*sort_order)
        bt = qs.values_list('direction', 'order', 'busstop')

        qsp = RoutePreview.objects.filter(bus=b).order_by(*sort_order)
        btp = qsp.values_list('direction', 'order', 'busstop')
        bt, btp = list(bt), list(btp)
        if btp and bt != btp and b.id not in BLOCKED.get(city.id, []):
            #print btp
            #print bt
            #sys.exit()
            logging.info("%s %s, changes found" % (b.ttype_slug(), b.name))
            qs.delete()
            cnt += 1
            for z in qsp:
                z.id = None
                z.__class__ = Route
                z.save() # nice hack
            fill_bus_endpoints(b)
            fill_moveto(b)
            cache_reset_bus(b)
            fill_routeline(b, True) # fill_routeline(bus, True)
        # if btp and bt != btp and b.id not in BLOCKED.get(city.id, [])
    # for b in Bus.objects.filter(city_id=city.id).order_by('order')

    return cnt, cnt_all
# def route_updater(city, DEBUG=False)


# call this if used from another script
def execute(city_id):
    # https://docs.python.org/2/library/logging.html#logging.Logger
    # https://stackoverflow.com/questions/13479295/python-using-basicconfig-method-to-log-to-console-and-file
    # set up logging to file
    logging.basicConfig(format='%(message)s',
                        level=logging.INFO,
                        filename="/bustime/bustime/static/logs/route_auto-%d.log" % city_id,
                        filemode="w")
    # set up logging to console
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)  #
    # set a format which is simpler for console use
    formatter = logging.Formatter('%(message)s')
    console.setFormatter(formatter)
    logging.getLogger().addHandler(console)
    # 
    startTime = datetime.datetime.now()
    logging.info("%s", startTime.strftime('%d.%m.%y %H:%M:%S'))

    city = cities_get()[city_id]
    logging.info("Route updater for: %s", city.name)

    cnt, cnt_all = route_updater(city, DEBUG=True)
    logging.info("Processed %d changes in %d buses (%d blocked)", cnt, cnt_all, len(BLOCKED.get(city.id, [])))

    logging.info("route_auto done")
    logging.info("%s", datetime.datetime.now().strftime('%d.%m.%y %H:%M:%S'))
    logging.info("runtime: %.2f", (datetime.datetime.now()-startTime).total_seconds())
    logging.shutdown()
# def execute(city_id)


# entry point for used from console
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Route updater. Update Route if any changes found in RoutePreview.')
    parser.add_argument('city_id', metavar='N', type=int, help='city id')
    args = parser.parse_args()
    execute(args.city_id)
