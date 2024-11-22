import json
import jsonpatch
import os
import shutil
import subprocess
import traceback
from bustime.models import *
from bustime import settings
from bustime.update_utils import turbo_mobile_update_v8, jamlines_export


'''
В модели Place есть поля:
    dump_version - версия базового дампа
    patch_version - версия патча

Базовый дамп:
    находится в папке /v8
    пример названия для Калининграда: 4-0.json (4 - это id place, 0 - это версия этого дампа)
    загружается на сайте (в base.html) и потом к нему применяется патч

Патч:
    находится в папке /v8
    пример названия для Калининграда: 4-0-21.json (4 - это id place, 0 - это версия базового дампа, 21 - это версия патча)
    загружается на сайте (в base.html) и применяется к базовому дампу
    содержит отличия между текущим и базовым дампом

Текущий дамп:
    находится в папке /v8/current
    пример названия: 4.json (4 - это id place)
    используется только в текущем скрипте для нахождения отличий с базовым дампом и на основе этого формируется патч


Патч и его версия перезаписываются, когда есть отличия между базовым и текущим дампом
Базовый дамп и его версия перезаписываются, когда размер патча становится 30% и больше от размера базового дампа


'''

def make_patch_for_json(place):
    #fff = open('/bustime/bustime/debug.txt', 'w')
    #fff.write(f'{__file__}:make_patch_for_json()\n')
    #fff.write(f'settings.PROJECT_DIR={settings.PROJECT_DIR}\n')
    # пути к файлам и версии
    path_dump = "%s/bustime/static/other/db/v8/%s-%s.json" % (settings.PROJECT_DIR, place.id, place.dump_version) # путь к базовому дампу
    path_diff = "%s/bustime/static/other/db/v8/current/%s.json" % (settings.PROJECT_DIR, place.id) # путь к новому дампу (с изменениями)
    #fff.write(f'path_dump={path_dump}\n')
    #fff.write(f'path_diff={path_diff}\n')

    ver = place.patch_version + 1 # номер новой версии
    path_patch = "%s/bustime/static/other/db/v8/%s-%s-%s.json.patch" % (settings.PROJECT_DIR, place.id, place.dump_version, ver) # путь к патчу новому
    #fff.write(f'ver={ver}\n')
    #fff.write(f'path_patch={path_patch}\n')

    # проверка на первый запуск
    folder1 = "%s/bustime/static/other/db/v8"  % settings.PROJECT_DIR
    folder2 = "%s/bustime/static/other/db/v8/current/" % settings.PROJECT_DIR
    if not os.path.exists(folder1):
        os.makedirs(folder1)
    if not os.path.exists(folder2):
        os.makedirs(folder2)
    #fff.write(f'folder1={folder1}\n')
    #fff.write(f'folder2={folder2}\n')

    # формирование текущего дампа в current
    #fff.write(f'turbo_mobile_update_v8()\n')
    info_data = turbo_mobile_update_v8(place, reload_signal=True)
    #fff.write(f'info_data={info_data}\n')


    # подготовка нужных файлов для сравнения

    #если основного дампа нет, копируем из /current
    if not os.path.exists(path_dump):
        #fff.write(f'shutil.copy({path_diff}, {path_dump})\n')
        #fff.flush()
        shutil.copy(path_diff, path_dump)

    # загружаем новую и старую бд
    with open(path_dump, "r") as file:
        data1 = json.load(file)
    with open(path_diff, "r") as file:
        data2 = json.load(file)

    # находим отличия
    diff = jsonpatch.JsonPatch.from_diff(data1, data2)
    diff_json = diff.to_string()

    # открываем старый патч
    path_patch_old = "%s/bustime/static/other/db/v8/%s-%s-%s.json.patch" % (settings.PROJECT_DIR, place.id, place.dump_version, place.patch_version) # путь к патчу старому
    #fff.write(f'path_patch_old={path_patch_old}\n')


    # сравнение старого и нового патча
    if os.path.exists(path_patch_old): # если старый патч есть
        # достаем данные из старого патча
        with open(path_patch_old, 'r') as file:
            old_patch = file.read()

        # если содержимое патча не поменялось
        if diff_json == old_patch:
            info_data.append("v8: patch не изменился %s" % (place.name))

        # если содержимое патча поменялось
        else:
            # удаляем старый патч
            if os.path.exists(path_patch_old):
                os.remove(path_patch_old)
            if os.path.exists(path_patch_old + '.br'):
                os.remove(path_patch_old + '.br')

            # записываем отличия в файл
            with open(path_patch, 'w') as file:
                file.write(diff_json)

            # меняем версию на новую
            place.patch_version += 1
            place.save()
            info_data.append("v8: patch перезаписан %s" % (place.name))
            try:
                sl = "%s/other/db/v8/%s-%s-%s.json.patch" % (settings.STATIC_ROOT, place.id, place.dump_version, ver-1)
                #fff.write(f'os.remove({sl})\n')
                os.remove(sl)
            except:
                info_data.append(traceback.format_exc(limit=1))
    else: # если старого патча нет
        # записываем отличия в файл
        with open(path_patch, 'w') as file:
            file.write(diff_json)

        # меняем версию на новую
        place.patch_version += 1
        place.save()
        info_data.append("v8: patch создан %s" % (place.name))

    # проверка размера нового патча
    if os.path.exists(path_patch): # если новый патч появился, то проверяем его размер
        size_dump = os.path.getsize(path_dump) # размер базового дампа
        size_patch = os.path.getsize(path_patch) # размер созданного патча

        # записываем новые значения версия дампа и патча, и пути к ним для дальнейшего создания, если размер окажется большим
        ver_dump = place.dump_version + 1
        ver_patch = 0 #обнуляется счетчик патчей
        path_dump_new = "%s/bustime/static/other/db/v8/%s-%s.json" % (settings.PROJECT_DIR, place.id, ver_dump)
        path_patch_new = "%s/bustime/static/other/db/v8/%s-%s-%s.json.patch" % (settings.PROJECT_DIR, place.id, ver_dump, ver_patch)
        #fff.write(f'path_dump_new={path_dump_new}\n')
        #fff.write(f'path_patch_new={path_patch_new}\n')

        if size_patch >= 0.3 * size_dump or size_patch > 1024000: # если патч по размеру 30% и больше от базового дампа
            # создаем новый базовый дамп (копируя содержимое из current)
            shutil.copy(path_diff, path_dump_new)

            # создаем новый пустой патч
            with open(path_patch_new, 'w') as file:
                file.write('[]')

            # удаляем старый базовый дамп с версией меньше текущей на 2
            path_dump_old = "%s/bustime/static/other/db/v8/%s-%s.json" % (settings.PROJECT_DIR, place.id, ver_dump-2)
            if os.path.exists(path_dump_old):
                os.remove(path_dump_old)
            if os.path.exists(path_dump_old + '.br'):
                os.remove(path_dump_old + '.br')

            #удаляем старый патч
            if os.path.exists(path_patch):
                os.remove(path_patch)

            # меняем версию дампа патча на новую в бд
            place.dump_version += 1
            place.patch_version = 0
            place.save()
            info_data.append("v8: базовый dump перезаписан %s" % (place.name))
            info_data.append("v8: patch перезаписан %s" % (place.name))

            # удаляем старые
            try:
                sl = "%s/other/db/v8/%s-%s.json" % (settings.STATIC_ROOT, place.id, place.dump_version-2)
                #fff.write(f'os.remove({sl})\n')
                os.remove(sl)

                sl = "%s/other/db/v8/%s-%s-%s.json.patch" % (settings.STATIC_ROOT, place.id, place.dump_version-1, ver)
                #fff.write(f'os.remove({sl})\n')
                os.remove(sl)
            except:
                info_data.append(traceback.format_exc(limit=1))

    #fff.close()
    # пробки
    is_lines_updated = jamlines_export(place)
    if is_lines_updated:
        info_data.append(u'Найдены изменения JamLines [%s]' % place.name)
    else:
        info_data.append(u'Нет изменений JamLines [%s]' % place.name)


    rcache_set(f"turbo_home__{place.slug}", None)
    sio_pub("ru.bustime.reload_soft__%s" % (place.id), {"reload_soft": True})
    return info_data
