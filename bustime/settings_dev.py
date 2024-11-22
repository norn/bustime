import os
import socket
DEV_HOSTNAME = socket.gethostname()
WINDMILLS_HOSTNAME = DEV_HOSTNAME

if os.environ.get("BUSTIME_PROJECT_DIR"):
    PROJECT_DIR = os.environ.get("BUSTIME_PROJECT_DIR")

if os.environ.get('BUSTIME_ALLOWED_HOSTS'):
    ALLOWED_HOSTS = os.environ.get('BUSTIME_ALLOWED_HOSTS').split(',')

DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'bustime',                                  # Or path to database file if using sqlite3.
        'USER': 'bustime',                                  # Not used with sqlite3.
        'PASSWORD': '',                     # Not used with sqlite3.
        'HOST': os.environ.get("POSTGRES_IP") or '127.0.0.1', # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                                         # Set to empty string for default. Not used with sqlite3.
    },
    'bstore': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': 'bustime',
        'USER': 'bustime',
        'PASSWORD': '',
        'HOST': os.environ.get("POSTGRES_IP") or '127.0.0.1',
        'PORT': '',
    },
    'gtfs': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': "bustime",
        'USER': 'bustime',
        'PASSWORD': "",
        'HOST': os.environ.get("POSTGRES_IP") or '127.0.0.1',
        'PORT': '',
        'OPTIONS': {
            'sslmode': 'disable',
        },
        'DISABLE_SERVER_SIDE_CURSORS': True,
    },
}

DATABASE_ROUTERS = [
    'bustime.db_routers.BStoreRouter'
]

REDIS_HOST = os.environ.get("REDIS_IP") or '127.0.0.1'
REDIS_PORT = 6379 # make it the same for the dev for simplicity
REDIS_HOST_W = os.environ.get("REDIS_IP") or '127.0.0.1'
REDIS_PORT_W = 6379
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

MEDIA_ROOT = os.environ.get('BUSTIME_MEDIA_ROOT') or '/bustime/bustime/uploads'
MEDIA_URL = os.environ.get('BUSTIME_MEDIA_URL') or '/uploads/'
STATIC_URL = os.environ.get('BUSTIME_STATIC_URL') or '/static/'

if not os.environ.get('BUSTIME_DOCKER_CONTAINER', False):
    STATIC_ROOT = os.environ.get('BUSTIME_STATIC_ROOT') or '/bustime/bustime/static'
else:
    STATICFILES_DIRS = (
        os.environ.get('BUSTIME_STATIC_ROOT') or '/bustime/bustime/static',
)

if DEV_HOSTNAME == "dev1":
    ADMINS = (('Dev Admin', 'dev1@mail.address'),)
elif DEV_HOSTNAME == "bustime-dev2":
    ADMINS = (('Main Admin', 'admin@mail.address'),)
