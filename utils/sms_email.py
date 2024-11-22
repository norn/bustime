#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import
from devinclude import *
from bustime.models import SMS
from datetime import datetime, timedelta
from django.core.mail import send_mail
import socket
import traceback
from django import db

# for cron log
print("%s" % (datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

HOSTNAME = socket.gethostname()

if not settings.DEV and HOSTNAME == "bustime":
    current_datetime = datetime.now()
    try:
        sms_current_datetime = SMS.objects.all().last().ctime

        three_hour = timedelta(hours=3)
        message = 'Последнее SMS было получено больше 3 часов назад. Возможно SMS сервис сломан. Последнее сообщение отправлено в : {}  \n  текущее время: {}'.format(sms_current_datetime, current_datetime)

        if (current_datetime - sms_current_datetime) > three_hour:
            send_mail('SMS сервис', message, 'noreply@mail.address', ['admin@mail.address', 'admin2@mail.address'])
    except:
        print(traceback.format_exc(limit=2))
    finally:
        db.connection.close()
