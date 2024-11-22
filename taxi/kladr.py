"""
Импорт КЛАДР
"""
from zbusd.devinclude import *

from taxi.models import Kladr_street
from bustime.models import (rcache_get, rcache_set, City)

import traceback
from dbfread import DBF # pip install dbfread, https://dbfread.readthedocs.io/en/latest/


class Kladr(object):
    """docstring"""

    def __init__(self, debug:bool = False):
        """Constructor"""
        self.debug = debug
        self.error = ''

    def __del__(self):
        """Destructor"""
        self.verbose("__del__")
    # __del__

    def verbose(self, method:str = "", message:str = "", force:bool = False):
        if self.debug or force:
            if method:
                method = ".%s()" % method
            if message:
                message = ": %s" % message

            if method or message:
                print("%s%s%s" % (self.__class__.__name__, method, message))
            else:
                print()
    # verbose

    # https://www.sql.ru/forum/652974/pomogite-razobratsya-s-ulicami-v-bd-kladr
    def kladr_import(self, kladr_path:str = ""):
        self.verbose("kladr_import", kladr_path)

        inserted, updated = 0, 0
        places = "%s/KLADR.DBF" % kladr_path
        streets = "%s/STREET.DBF" % kladr_path

        for place in DBF(places):
            if self.debug: print(place['SOCR'], place['NAME'], place['CODE'])

            # город, деревня, село, посёлок
            if place['SOCR'] in ['г', 'п']:
                c = City.objects.filter(name=place['NAME']).first()
                if c:
                    if self.debug: print('\t', c.name)
                    for street in DBF(streets):
                        if street['CODE'][0:13] == place['CODE']:
                            if self.debug: print('\t\t', street['SOCR'], street['NAME'], street['INDEX'])

                            s = Kladr_street.objects.filter(city=c, socr=street['SOCR'], name=street['NAME']).first()
                            if not s:
                                Kladr_street(city=c, code=street['CODE'], socr=street['SOCR'], name=street['NAME'], index=street['INDEX']).save()
                                inserted += 1
                            else:
                                s.code = street['CODE']
                                s.index = street['INDEX']
                                s.save()
                                updated += 1
                    # for street in DBF(streets)
            # if place['SOCR'] in ['г', 'д', 'с', 'п']
        # for place in DBF(places)

        self.verbose("kladr_import", "END, inserted %s, updated %s" % (inserted, updated))
    # kladr_import

    def kladr_update(self, kladr_path:str = ""):
        self.verbose("kladr_update", "Not ready, sorry :)")
    # kladr_update


# python taxi/kladr.py
if __name__ == '__main__':
    kladr = Kladr(True)
    kladr.kladr_import("taxi/temp")
