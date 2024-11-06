# -*- coding: utf-8 -*-
"""
Утилитки для проекта bustime
"""
from __future__ import absolute_import
from django.db import connections
from django.db.utils import OperationalError

"""
Просто чтение файла
"""
def readfile(path):
    try:
        handle = open(path, "r")
        ret = [None, handle.read()]
    except IOError:
        ret = [str(sys.exc_info()[1]), None]
    else:
        handle.close()
    return ret

"""
Ожидание подключения БД
(django подключается к БД автоматически при первом обращении, но
если до использования этих утилит не работали с моделями, то подключени нет,
и выборки не сработают)
"""
def db_test(db_alias):
    db_conn = None
    i = 0
    while i < 10 and (not db_conn):
        i = i + 1
        try:
            connections[db_alias].ensure_connection()
            db_conn = True
        except OperationalError:
            time.sleep(0.3)
    return db_conn


"""
Произвольная выборка данных из произвольной БД
db_alias - алиас БД, указанный в settings.py
query - текст запроса SELECT...
возвращает массив строк с числовыми индексами полей
"""
def db_select(db_alias, query):
    if db_test(db_alias):
        cursor = connections[db_alias].cursor()
        cursor.execute(query)
        ret = cursor.fetchall()
        cursor.close()
        return ret
    else:
        return None

"""
Произвольная выборка данных из произвольной БД
db_alias - алиас БД, указанный в settings.py
query - текст запроса SELECT...
возвращает массив строк с тестовыми индексами полей - именами полей из БД
https://stackoverflow.com/questions/3286525/return-sql-table-as-json-in-python/3287775#3287775
"""
def db_select2(db_alias, query, one=False):
    if db_test(db_alias):
        cursor = connections[db_alias].cursor()
        cursor.execute(query)
        r = [dict((cursor.description[i][0], value) \
                   for i, value in enumerate(row)) for row in cursor.fetchall()]
        cursor.close()
        return (r[0] if r else None) if one else r
    else:
        return None
