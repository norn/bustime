import sys,os
from os.path import dirname, realpath

os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
import loadenv

sys.path.insert(0, dirname(dirname(realpath(__file__))))
from django.conf import settings
sys.path.append(settings.PROJECT_DIR)
settings.DEBUG=False

import django
django.setup()