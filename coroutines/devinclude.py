#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import absolute_import
import sys,os
from os.path import dirname, realpath

os.environ['DJANGO_SETTINGS_MODULE'] = 'bustime.settings'
if not os.environ.get('BUSTIME_DOCKER_CONTAINER', False):
    from loadenv import *

sys.path.insert(0, dirname(dirname(realpath(__file__))))
from django.conf import settings
sys.path.append(settings.PROJECT_DIR)
settings.DEBUG=False

import django
django.setup()
