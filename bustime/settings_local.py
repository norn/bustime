import socket

DEBUG = True
DEV = False

INTERNAL_IPS = ["127.0.0.1", "192.168.168.250"]
PROJECT_DIR = "/bustime/bustime"
SECRET_KEY = 'SECRET_KEY'
RECAPTCHA_SECRET = "RECAPTCHA_SECRET"

AWS_ACCESS_KEY_ID = "AWS_ACCESS_KEY_ID"
AWS_SECRET_ACCESS_KEY = "AWS_SECRET_ACCESS_KEY"
DIGITRANSIT_KEY = "DIGITRANSIT_KEY"
UID_PASSWD = 'UID_PASSWD'
TILE_SERVER_KEY = 'TILE_SERVER_KEY'

try:
    with open(PROJECT_DIR + "/hostname_master", 'r') as f:
        MASTER_HOSTNAME = f.read()
        WINDMILLS_HOSTNAME = MASTER_HOSTNAME
        UPDATERS_HOSTNAME = MASTER_HOSTNAME
        CRAWLERS_HOSTNAME = MASTER_HOSTNAME
        GTFS_HOSTNAME = MASTER_HOSTNAME
except FileNotFoundError:
    MASTER_HOSTNAME = socket.gethostname()
    WINDMILLS_HOSTNAME = socket.gethostname()
    UPDATERS_HOSTNAME = socket.gethostname()
    CRAWLERS_HOSTNAME = socket.gethostname()
    GTFS_HOSTNAME = socket.gethostname()

BUSTIME_REPLICA = MASTER_HOSTNAME in ["list", "names", "of", "servers"]
REDIS_REPLICA = MASTER_HOSTNAME in ["list", "names", "of", "servers"]

BUSTIME_HOSTS = {
    MASTER_HOSTNAME: "127.0.0.1",
    WINDMILLS_HOSTNAME: "127.0.0.1",
    UPDATERS_HOSTNAME: "127.0.0.1",
    CRAWLERS_HOSTNAME: "127.0.0.1",
    GTFS_HOSTNAME: "127.0.0.1",
}

DEFAULT_HOST = '127.0.0.1'
DEFAULT_PORT = '5432'
REPLICA_HOST = DEFAULT_HOST
REPLICA_PORT = DEFAULT_PORT

REDIS_HOST = '127.0.0.1'
REDIS_PORT = '6379'
REDIS_HOST_W = REDIS_HOST
REDIS_PORT_W = REDIS_PORT
REDIS_HOST_IO = REDIS_HOST
REDIS_PORT_IO = REDIS_PORT

#'DISABLE_SERVER_SIDE_CURSORS': True,
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'bustime',                                  # Or path to database file if using sqlite3.
        'USER': 'bustime',                                  # Not used with sqlite3.
        'PASSWORD': '',                     # Not used with sqlite3.
        'HOST': '127.0.0.1',                                         # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                                         # Set to empty string for default. Not used with sqlite3.
    },
    'replica': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',  # Add 'postgresql_psycopg2'
        'NAME': 'bustime',
        'USER': 'bustime',
        'PASSWORD': '',
        'HOST': REPLICA_HOST,
        'PORT': REPLICA_PORT,
        'OPTIONS': {
            'sslmode': 'disable',
        },
    },
    'bstore': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': 'bustime',
        'USER': 'bustime',
        'PASSWORD': '',
        'HOST': '127.0.0.1',
        'PORT': '',
    },
    'gtfs': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': "bustime",
        'USER': 'bustime',
        'PASSWORD': "",
        'HOST': '127.0.0.1',
        'PORT': '',
        'OPTIONS': {
            'sslmode': 'disable',
        },
        'DISABLE_SERVER_SIDE_CURSORS': True,
    },
}

DATABASE_ROUTERS = [
    'bustime.db_routers.BStoreRouter',
    'bustime.db_routers.ReplicaRouter'
]

MEDIA_ROOT = '/bustime/bustime/uploads'
MEDIA_URL = '/uploads/'
STATIC_HOST = ''
STATIC_ROOT = '/bustime/bustime/static'
STATIC_URL = STATIC_HOST + '/static/'

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'