#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import
import sys,os
from os.path import dirname, realpath
import django

os.environ['DJANGO_SETTINGS_MODULE'] = 'bustime.settings'

sys.path.insert(0, dirname(dirname(realpath(__file__))))
sys.path.insert(0, dirname(dirname(realpath(__file__)))+"/bustime/")
from django.conf import settings
sys.path.append(settings.PROJECT_DIR)
# При разработке выключает DEBUG режим Django, в результате никаких отладочных сообщений не поступает
settings.DEBUG=False

django.setup()
