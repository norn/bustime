import collections
from math import ceil
from django.core.paginator import Paginator
from django.core.cache import cache
from .models import *


# https://gist.github.com/e4c5/6852723
#
# To use the paginator, add the following to your model admin class:
# from bustime.caching_paginator import CachingPaginator
# ...
# class LogAdmin(admin.ModelAdmin):
#   ...
#   paginator = CachingPaginator

class CachingPaginator(Paginator):
    '''
    A custom paginator that helps to cut down on the number of
    SELECT COUNT(*) form table_name queries.
    '''
    _count = None

    def _get_count(self):
        """
        Returns the total number of objects, across all pages.
        """
        if self._count is None:
            try:
                key = "adm:{0}:count".format( hash(self.object_list.query.__str__()) )
                self._count = rcache_get(key, -1);

                if self._count == -1 :
                    if not self.object_list.query.where:
                        cursor = connection.cursor()
                        # postgresql version must be > 13
                        cursor.execute("SELECT reltuples FROM pg_class WHERE relname = %s",
                            [self.object_list.query.model._meta.db_table])
                        self._count = int(cursor.fetchone()[0])
                    else :
                        self._count = self.object_list.count()
                    rcache_set(key, self._count, 5)
            except (AttributeError, TypeError) as ex:
                # AttributeError: 'dict' object has no attribute 'count'
                # TypeError: list.count() takes exactly one argument (0 given)
                self._count = len(self.object_list)
                rcache_set(key, self._count, 5)
        # if self._count is None
        return self._count
    # _get_count

    count = property(_get_count)
# CachingPaginator