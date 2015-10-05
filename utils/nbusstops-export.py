#!/usr/bin/python
# -*- coding: utf-8 -*-

from devinclude import *
from bustime.models import *
import time
import urllib
import socket
import random
from django.contrib.sessions.models import Session
import csv
from django.contrib.gis.geos import Point

import codecs
import json
import pickle

#city=City.objects.get(name="Красноярск")
#city=City.objects.get(name="Калининград")
#city=City.objects.get(name="Санкт-Петербург")
#city=City.objects.get(name="Томск")
#city=City.objects.get(name="Кемерово")
#city=City.objects.get(name="Пермь")
city=City.objects.get(name="Казань")

names=[]
names_done={}
BEG="var stops=["
END="];"

NBusStop.objects.filter(city=city)

for nb in NBusStop.objects.filter(city=city).order_by('name'):#.distinct('name')
    if not names_done.get(nb.name):
        ids = NBusStop.objects.filter(city=city, name=nb.name).order_by('id').values_list("id", flat=True)
        names.append("{value:'%s',ids:%s}"%(nb.name, ids))
        names_done[nb.name]=1

print "%s%s%s"%(BEG, ",".join(names).encode('utf8'), END)
