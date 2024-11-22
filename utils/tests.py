#!/usr/bin/env python
# -*- coding: utf-8 -*-

from devinclude import *
from django.test import RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from django.http import JsonResponse
from api.views import jsonrpc
from bustime.views import turbo_home, turbo_select
import json


def check_response(response, url):
    if response.status_code == 200:
        print("Check", url, "[ok]")
    else:
        print(f"Status code is {response.status_code}")
        exit(1)


def add_session_to_request(request):
    middleware = SessionMiddleware(lambda x: x)
    middleware.process_request(request)
    request.session.save()

factory = RequestFactory()

###
url = '/api/jsonrpc/'
method = "user_get"
params = {"uuid": "test", "os": "android"}
body_content = json.dumps({"method": method, "params": params})
request = factory.post(url, data=body_content, content_type='application/json')
response = jsonrpc(request) # fire it up
check_response(response, url)

###
url = "/"
request = factory.get(url)
add_session_to_request(request)
response = turbo_select(request)
check_response(response, url)
