# -*- coding: utf-8 -*-
# https://stackoverflow.com/questions/2052284/how-to-throttle-django-error-emails
from __future__ import absolute_import
from django.utils.log import AdminEmailHandler
from django.core.cache import cache


class ThrottledAdminEmailHandler(AdminEmailHandler):
    PERIOD_LENGTH_IN_SECONDS = 10
    MAX_EMAILS_IN_PERIOD = 1
    COUNTER_CACHE_KEY = "email_admins_counter"

    """
    cache.get(REDIS_HOST_W) сразу после cache.set(REDIS_HOST) не получает значение, так как репликация не успела сработать,
    функция возвращает None
    и на строке if counter > self.MAX_EMAILS_IN_PERIOD получаем исключение
    Exception Value: '>' not supported between instances of 'NoneType' and 'int'

    def increment_counter(self):
        try:
            cache.incr(self.COUNTER_CACHE_KEY)
        except ValueError:
            cache.set(self.COUNTER_CACHE_KEY, 1, self.PERIOD_LENGTH_IN_SECONDS)
        return cache.get(self.COUNTER_CACHE_KEY)
    """

    def increment_counter(self):
        try:
            cache.incr(self.COUNTER_CACHE_KEY)
            retval = cache.get(self.COUNTER_CACHE_KEY)
        except ValueError:
            retval = 1
            cache.set(self.COUNTER_CACHE_KEY, retval, self.PERIOD_LENGTH_IN_SECONDS)
        return retval

    def emit(self, record):
        try:
            counter = self.increment_counter()
        except Exception:
            return  # pass, if redis unavailable do nothing
        else:
            if counter > self.MAX_EMAILS_IN_PERIOD:
                return
        super(ThrottledAdminEmailHandler, self).emit(record)