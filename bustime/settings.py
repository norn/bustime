from __future__ import absolute_import

import io
import os
import sys
import openai
import socket

from django.utils.translation import gettext_lazy as _
from bustime.settings_local import *

if not os.environ.get('BUSTIME_DOCKER_CONTAINER', False):
    from gevent import monkey
    monkey.patch_all(select=False, thread=False)

TIME_ZONE = 'Asia/Krasnoyarsk'
ALLOWED_HOSTS = ['192.168.168.250', 'bustime.loc']
LANGUAGE_CODE = 'ru'
SITE_ID = 1

SUBDOMAIN_DOMAIN = "192.168.168.250"
SUBDOMAIN_IGNORE_HOSTS = ["bustime.ru", "bustime.loc"]
LANGUAGE_COOKIE_NAME = "_language"
LANGUAGE_COOKIE_DOMAIN = ".192.168.168.250"
SESSION_COOKIE_DOMAIN = '.192.168.168.250'
CSRF_COOKIE_DOMAIN = ".192.168.168.250"
DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880   # 5mb, default 2621440 (2mb)

TEMPLATE_DEBUG = DEBUG
PROJECT_ROOT = PROJECT_DIR

ADMINS = (
    ('Main Admin', 'admin@mail.address'),
)
MANAGERS = ADMINS

REDIS_EVENTS_STREAM = "events_stream"


# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
#USE_I18N = False
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True
#USE_L10N = False
#DECIMAL_SEPARATOR = '.'

LANGUAGES = [
    ('en', 'English'),
    ('es', 'Español'),
    ('et', 'Eesti'),
    ('fi', 'Suomen'),
    ('it', 'Italiano'),
    ('pl', 'Polski'),
    ('pt', 'Português'),
    ('be', 'Беларуская'),
    ('ru', 'Русский'),
    ('uk', 'Українська'),
    ('lt', 'Lietuvių'),
    ('lv', 'Latviešu'),
    ('nl', 'Nederlands'),
    ('cs', 'Čeština'),
    ('hu', 'Magyar'),
    ('de', 'Deutsch'),
    ('fr', 'Français'),
    ('da', 'Dansk'),
]

EXCLUDED_PLACES = []

# If you set this to False, Django will not use timezone-aware datetimes.
#USE_TZ = True
USE_TZ = False

DATE_FORMAT = "Y-m-d"
TIME_FORMAT = "H:i"

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

MIDDLEWARE = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'subdomains.middleware.SubdomainURLRoutingMiddleware',
    'bustime.middleware.BustimeLocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    "debug_toolbar.middleware.DebugToolbarMiddleware",
)

SUBDOMAIN_URLCONFS = {
    None: "bustime.urls",
}

LEAFLET_CONFIG = {
    "PLUGINS": {
        "Leaflet.fullscreen": {
            "css": [STATIC_URL + "css/leaflet.fullscreen.css"],
            "js": [STATIC_URL + "js/Leaflet.fullscreen.min.js"],
            'auto-include': True,
        }
    }
}

LOCALE_PATHS = (
    PROJECT_DIR+'/locale',
)
ROOT_URLCONF = 'bustime.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'bustime.wsgi.application'

TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'APP_DIRS': True,
    'OPTIONS': {
        'context_processors': [
            'django.contrib.auth.context_processors.auth',
            "django.template.context_processors.debug",
            "django.template.context_processors.static",
            'django.template.context_processors.request',
            'django.contrib.messages.context_processors.messages',
            'bustime.context_processors.settings_dev'
        ],
    },
}]

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.staticfiles',
    'django.contrib.sitemaps',
    'modeltranslation',
    'django.contrib.admin',
    'django.contrib.messages',
    'django.contrib.gis',
    'bustime',
    'backoffice',
    'djantimat',
    'sorl.thumbnail',
    'leaflet',
    'reversion',
    'reversion_compare',
    'rosetta',
    'taxi',
    'debug_toolbar',
    "phonenumber_field",
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
)

DEFAULT_FROM_EMAIL="noreply@mail.address"
SERVER_EMAIL="noreply@mail.address"
EMAIL_HOST = DEFAULT_HOST

VACUUM_MILL_COUNT = 1

BROKER_URL = "redis://{}:{}/1".format(REDIS_HOST_W, REDIS_PORT_W)

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": [
            "redis://{}:{}/2".format(REDIS_HOST_W, REDIS_PORT_W), # master for writes
            "redis://{}:{}/2".format(REDIS_HOST, REDIS_PORT), # read-replica 1
        ],
        'TIMEOUT': 60*60*24,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}

SESSION_COOKIE_AGE=60*60*24*365*10 # 365 days in seconds

# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
PATH_TO_LOG = '/var/log/bustime'
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'fmt': {
            'format':'%(asctime)s %(levelname)s (%(name)s) %(message)s',
            'datefmt':'%Y-%m-%d %H:%M:%S'
        }
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'loggers': {
        'django': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
        'bustime.update_lib': {
            'handlers': ['informator', 'warnator', 'errormator'],
            'level': 'INFO',
            'propagate': True,
        },
        'bustime.models': {
            'handlers': ['informator', 'warnator', 'errormator'],
            'level': 'INFO',
            'propagate': True,
        },
        'utils.mobile_dump_update': {
            'handlers': ["console"],
            'level': 'INFO',
            'propagate': True,
        },
        'socketoto': {
            'handlers': ["console"],
            'level': 'WARNING',
            'propagate': True
        },
        '__main__': {
            'handlers': ['informator', 'warnator', 'errormator'],
            'level': 'INFO',
            'propagate': True,
        },
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'class': 'bustime.limit_email.ThrottledAdminEmailHandler'
        },
        'informator': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename':'%s/info.log'%PATH_TO_LOG,
            'formatter':'fmt'
        },
        'warnator': {
            'level': 'WARNING',
            'class': 'logging.FileHandler',
            'filename':'%s/warning.log'%PATH_TO_LOG,
            'formatter':'fmt'
        },
        'errormator': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename':'%s/error.log'%PATH_TO_LOG,
            'formatter':'fmt'
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'stream': sys.stdout,
            'formatter': 'fmt'
        },
        'memory_buffer': {
            'level': 'INFO',
            'class': 'logging.handlers.MemoryHandler',
            'capacity': 1024 * 10,
            'formatter': 'fmt'
        },
    }
}

# QIWI
QIWI_PULL_PASS = "QIWI_PULL_PASS"
QIWI_PROJECT_ID = 000000

# MAP SERVERS, register please
TILE_SERVER = 'https://tile.nextzen.org'
NOMINATIM_SERVER = 'https://nominatim.openstreetmap.org'
GH_SERVER =   'https://www.graphhopper.com/products/'
GRAPH_PATH = f"{PROJECT_DIR}/bustime/static/other/graph/"
GRAPH_SERVER_PATH = "https://www.graphhopper.com/products/"

# LOGIN
LOGIN_URL = '/register/'
LOGIN_REDIRECT_URL = '/'

# REGISTER_PHONE
DEFAULT_REGISTER_PHONE = '+71111111111'
DEFAULT_REGISTER_PHONE_EUROPE = '+31111111111'
PHONENUMBER_DEFAULT_REGION = 'RU'

# Model translations
TRANSLATABLE_MODEL_MODULES = ["bustime.models"]

# Rosetta
ROSETTA_MESSAGES_PER_PAGE = 50

TURBO_MILL_COUNT = 12

GIT_WEBHOOK_MF = '111111111111'

OPENAI_API_KEY = 'OPENAI_API_KEY'
openai.api_key = OPENAI_API_KEY

OPENWEATHERMAP_KEY = 'OPENWEATHERMAP_KEY'

if DEV:
    from bustime.settings_dev import *