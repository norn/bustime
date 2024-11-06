# -*- coding: utf-8 -*-
from __future__ import absolute_import
import os
import traceback
from shutil import copyfile
import subprocess
from bustime.models import *

def daemon_reconfigure():
    retval = None
    try:
        # формирование conf-файла демона glonassd
        with open('/opt/glonassd/glonassd.conf', 'w') as f:
            # заголовок
            header = get_setting('glonassd_config_header')
            if header:
                f.write(header)
            # применики
            for record in Glonassd.objects.all().order_by('city'):
                section_name = "# %s:%s" % (record.city.id, record.city.name)
                f.write("\n")
                f.write("%s\n" % section_name)
                f.write("[%s]\n" % GLONASSD_PROTOCOL[record.protocol][1])
                f.write("protocol=TCP\n")
                f.write("port=%s\n" % record.port)
                f.write("enabled=1\n")
                f.write(";log_all=1\n")
                f.write(";log_err=1\n")
            f.close()

        # перезапуск демона glonassd
        cmd = ["sudo", "/usr/bin/supervisorctl", "restart", "glonassd"]
        msg = subprocess.check_output(cmd).decode()
    except Exception as ex:
        msg = str(ex)
        retval = msg

    log_message("save: %s" % msg, ttype="glonassd")
    return retval
# daemon_reconfigure()


# определение свободного порта
def get_awail_glonassd_port():
    port = 0
    avail_ports = get_setting("glonassd_ports")
    avail_ports = set(range(avail_ports[0], avail_ports[1]))
    # используем set, а не list, чтобы можно было легко вычесть
    used_ports = set(Glonassd.objects.all().values_list('port', flat=True))
    # вычитаем из общего списка портов исползуемые и превращаем в список
    ports = list(avail_ports-used_ports)
    if ports:
        port = ports[0]
    else:
        log_message("Свободных портов не осталось", ttype="glonassd")

    return port
# get_awail_glonassd_port()

