#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from devinclude import *
from bustime.models import *
import time
import six.moves.urllib.request, six.moves.urllib.parse, six.moves.urllib.error
import socket
import random
from django.contrib.sessions.models import Session
from django.contrib.sessions.models import *
from django.contrib.sessions.backends.db import SessionStore

bus=bus_get(3750)

fill_bus_endpoints(bus, DEBUG=True)
fill_moveto(bus)
cache_reset_bus(bus)