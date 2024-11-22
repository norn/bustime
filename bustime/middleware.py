from __future__ import absolute_import
from django.contrib.auth.models import User
from django.db import DataError
from django.http import Http404, HttpResponsePermanentRedirect
from django.middleware.common import CommonMiddleware
from django.utils import translation
from django.middleware.locale import LocaleMiddleware
from django.utils.deprecation import MiddlewareMixin
from bustime.views import get_user_settings, login_flowless
from django.utils.translation import activate as translation_activate


from django.contrib import auth
from django.contrib.sessions.models import Session


class BustimeLocaleMiddleware(LocaleMiddleware):
    def process_request(self, request):
        if 'User-Agent' in request.headers and request.headers['User-Agent'].startswith('okhttp/'):
            return
        if request.path.startswith("/api/"):
            return
        if request.path.startswith("/mapzen/vector/"):
            return
        code = request.subdomain
        if not code:
            translation_activate("en")
        else:
            translation_activate(code)
