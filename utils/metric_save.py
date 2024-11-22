#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import print_function
from devinclude import *
from bustime.models import *
from django import db

now = datetime.datetime.utcnow().date()
cc_key_prefix = "metric_%s_" % (now)
members = REDISU.smembers("metrics_%s" % now)

for m in members:
    val = REDIS.get(m)
    if not val: continue
    name = m.replace(cc_key_prefix, "")
    m, cr = Metric.objects.get_or_create(date=now, name=name)
    m.count = val
    m.save()

print("%s: %s" % (now, len(members)))
db.connection.close()
