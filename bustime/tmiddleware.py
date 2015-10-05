# -*- coding: utf-8 -*-

class TestoMiddleware(object):
    def process_response(self, request, response):
        if request.GET.get('test'):
            pass
        return response