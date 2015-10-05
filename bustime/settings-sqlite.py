# -*- coding: utf-8 -*-

from bustime.settings import *
import os

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # 'postgresql_psycopg2', '', 'mysql', 'sqlite3' 'oracle'
        'NAME': os.path.join(PROJECT_DIR+"/static/", 'sqlite3.db'),
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
        }
}

