#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Compare production and turbo results

from devinclude import *
from bustime.models import *
from zoneinfo import ZoneInfo
from pytz import timezone, utc

if __name__ == '__main__':
    t1=datetime.datetime.now()
    print('clang:', TimezoneFinder.using_clang_pip())
    print('numba:', TimezoneFinder.using_numba())
    for i in range(300000):
        x,y = random.random()*92, random.random()*90
        tz_name = timezone_finder.timezone_at(lng=x, lat=y)
        #etz = ZoneInfo(tz_name) #slower
        etz = timezone(tz_name)
    t2=datetime.datetime.now()
    print(tz_name, t2-t1)
