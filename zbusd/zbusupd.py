#!/usr/bin/env python
# -*- coding: utf-8 -*-
from devinclude import *
from bustime.models import *

import time
import threading

from bustime.update_krasnoyarsk import update_krasnoyarsk, update_krasnoyarsk2
from bustime.update_kaliningrad import update_kaliningrad
from bustime.update_speterburg import update_speterburg
from bustime.update_tomsk import update_tomsk
from bustime.update_kemerovo import update_kemerovo
from bustime.update_perm import update_perm
from bustime.update_kazan import update_kazan
import logging
import random
from django.core.mail import send_mail

def error_manager(city, now):
    cc_key = 'error_update_%s' % city.id
    error_update = cache.get(cc_key)
    if error_update:
        val = error_update
        delta = (now - val).total_seconds()
        if delta > 60 * 7 and not cache.get(cc_key+"_notified") and city.id != 4:
            send_mail('%s error %s' % (city.slug, str(now)), 'at: %s' % str(now), 'noreply@bustime.ru', ['andrey.perliev@gmail.com'], fail_silently=True)
            cache.set(cc_key+"_notified", 1, 60*60*3)
    else:
        val = now
    cache.set(cc_key, val, 60)
    logger = logging.getLogger(__name__)
    logger.error("%s: error updating %s" % (now, city.slug))
    return val


class CityUpdater(threading.Thread):

    def __init__(self, city):
        super(CityUpdater, self).__init__()
        self.city = city
        if city.id == 3:
            self.updater = update_krasnoyarsk
        elif city.id == 4:
            self.updater = update_kaliningrad
        elif city.id == 5:
            self.updater = update_speterburg
        elif city.id == 7:
            self.updater = update_tomsk
        elif city.id == 8:
            self.updater = update_kemerovo
        elif city.id == 9:
            self.updater = update_perm
        elif city.id == 10:
            self.updater = update_kazan

    def run(self):
        time.sleep(random.randint(0,10))
        while 1:
            d = datetime.datetime.now()
            d += datetime.timedelta(
                hours=self.city.timediffk)
            if d.hour >= 1 and d.hour < 5 and self.city.id != 5:
                time.sleep(60)
                continue
            elif d.hour == 4 and self.city.id == 5:
                time.sleep(60)
                continue
            """
            if self.city.id == 4:
                for server in ["89.190.255.130:15670"]:
            """
            try:
                result = self.updater()
            except:
                result = -1
            #print self.city, result
            if result == -1:
                time_ = error_manager(self.city, d)
                delta = (d - time_).total_seconds()
                if delta>60*5 and self.city.id == 3:
                    update_krasnoyarsk2()
            elif result == False:
                pass
            elif result == True:
                cc_key = 'error_update_%s' % self.city.id
                if cache.get(cc_key+"_notified"):
                    cache.set(cc_key+"_notified", None)
                    send_mail('%s ready %s' % (self.city.slug, str(d)), 'at: %s' % str(d), 'noreply@bustime.ru', ['andrey.perliev@gmail.com'], fail_silently=True)

            time.sleep(13)


if __name__ == '__main__':
    for k, city in CITY_MAP.items():
        if city.active:
            f = CityUpdater(city)
            f.daemon = True
            f.start()
    while 1:
        time.sleep(1)
