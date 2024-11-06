from __future__ import absolute_import
from django.utils.log import AdminEmailHandler
import redis
REDIS = redis.StrictRedis(db=0)
#from bustime.models import *
import time

# http://stackoverflow.com/questions/2052284/how-to-throttle-django-error-emails
class MyAdminEmailHandler(AdminEmailHandler):
    def incr_counter(self):
        key = self._redis_key()
        res = REDIS.incr(key)
        REDIS.expire(key, 60)
        return res

    def _redis_key(self):
        return time.strftime('error_email_limiter:%Y-%m-%d_%H:%M',
                             datetime.datetime.now().timetuple())

    def emit(self, record):
        try:
            ctr = self.incr_counter()
        except Exception:
            pass
        else:
            if ctr >= 6:
                return
        super(MyAdminEmailHandler, self).emit(record)