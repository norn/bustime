# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function
import requests
import datetime
from bs4 import BeautifulSoup
from lxml import html


def tcard_update(tcard, provider):
    now = datetime.datetime.now()

    if tcard.updated + datetime.timedelta(hours=4) > now:
        return

    if provider in tcards_info:
        balance_start = now
        result = {}
        try:
            result = tcards_info[provider][0](tcard.num, tcard.social)
            balance_stop = datetime.datetime.now()
            delta = balance_stop - balance_start
            tcards_info[provider][1](tcard, result)
            f = open('/tmp/balance_get_%s.log' % provider, 'a')
            f.write('%s: good %s\n' % (balance_start, delta))
            f.close()
        except:
            f = open('/tmp/balance_get_%s_bad.log' % provider, 'a')
            f.write("%s: bad\n" % balance_start)
            f.close()

        tcard.provider = provider
        tcard.updated = now
        tcard.save()
    return tcard

tcards_info = {}
