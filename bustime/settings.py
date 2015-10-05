DEBUG = False

from bustime.local_settings import *

TEMPLATE_DEBUG = DEBUG
PROJECT_ROOT = PROJECT_DIR

import djcelery
djcelery.setup_loader()

ADMINS = (
    ('Andrey Perliev', 'andrey.perliev@gmail.com'),
)

MANAGERS = ADMINS
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'bustime',                      # Or path to database file if using sqlite3.
        'USER': 'norn',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '10.0.3.12',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

TIME_ZONE = 'Asia/Krasnoyarsk'
ALLOWED_HOSTS = ['www.bustime.ru']
LANGUAGE_CODE = 'ru-ru'
SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
#USE_I18N = False
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True
#USE_L10N = False
#DECIMAL_SEPARATOR = '.'

# If you set this to False, Django will not use timezone-aware datetimes.
#USE_TZ = True
USE_TZ = False

DATE_FORMAT = "Y-m-d"
TIME_FORMAT = "H:i"


MEDIA_ROOT = '/mnt/reliable/repos/bustime/bustime/static_user'
MEDIA_URL = '/media/'
STATIC_ROOT = '/mnt/reliable/repos/bustime/bustime/static'
STATIC_URL = '/static/'

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
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
#    'djangobower.finders.BowerFinder',
)

# Make this unique, and don't share it with anybody.
# SECRET_KEY = ''

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    #'bustime.tmiddleware.TestoMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'bustime.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'bustime.wsgi.application'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    '/mnt/reliable/repos/bustime/lib/python2.7/site-packages/django/contrib/gis/templates/',
)

INSTALLED_APPS = (
#    'admin_tools.theming',
#    'admin_tools.menu',
#    'admin_tools.dashboard',

    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    #'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sitemaps',
    'django.contrib.admin',
    #'django.contrib.gis',
    'bustime',
    'djcelery',
    'app_metrics',
    'backoffice',
#    'djangobower',  

#    'sape',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.

DEFAULT_FROM_EMAIL="noreply@bustime.ru"
SERVER_EMAIL="noreply@bustime.ru"
EMAIL_HOST="10.0.3.16"
CELERY_ACCEPT_CONTENT = ['pickle', 'json', 'msgpack', 'yaml']

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/2",
        'TIMEOUT': 60*60*24,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            # "IGNORE_EXCEPTIONS": True,
            # "COMPRESS_MIN_LEN": 10,
            
        }
    }
}
#SESSION_SAVE_EVERY_REQUEST=True
SESSION_COOKIE_AGE=60*60*24*365*10 # 365 days in seconds
# http://niwinz.github.io/django-redis/latest/
#SESSION_ENGINE = "django.contrib.sessions.backends.cache"
#SESSION_CACHE_ALIAS = "default"

#POSTGIS_VERSION = (2, 0, 3)
BROKER_URL = 'redis://localhost:6379/1'

PATH_TO_LOG = '/var/log/bustime'
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'fmt': {
            'format':'%(asctime)s %(levelname)-5s (%(name)s) %(message)s',
            'datefmt':'%Y-%m-%d %H:%M:%S'
        }
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'loggers': {
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
        '__main__': {
            'handlers': ['informator', 'warnator', 'errormator'],
            'level': 'INFO',
            'propagate': True,
        },
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
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

    }
}
# How to throttle Django error emails
# http://stackoverflow.com/questions/2052284/how-to-throttle-django-error-emails

# Specifie path to components root (you need to use absolute path)
#BOWER_COMPONENTS_ROOT = os.path.join(PROJECT_DIR, 'components')
#BOWER_INSTALLED_APPS = (
#    'jquery#2.0.3',
#    'jquery-ui#~1.10.3',
#    'd3#3.3.6',
#    'nvd3#1.1.12-beta',
#)