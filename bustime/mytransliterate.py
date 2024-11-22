# -*- coding: utf-8 -*-


def mytransliterate(string, direction=0):
    #  ru + fi
    capital_letters = {u'А': u'A',
                       u'Б': u'B',
                       u'В': u'V',
                       u'Г': u'G',
                       u'Д': u'D',
                       u'Е': u'E',
                       u'Ё': u'E',
                       u'Ж': u'ZH',
                       u'З': u'Z',
                       u'И': u'I',
                       u'Й': u'Y',
                       u'К': u'K',
                       u'Л': u'L',
                       u'М': u'M',
                       u'Н': u'N',
                       u'О': u'O',
                       u'П': u'P',
                       u'Р': u'R',
                       u'С': u'S',
                       u'Т': u'T',
                       u'т': u't',
                       u'У': u'U',
                       u'Ф': u'F',
                       u'Х': u'H',
                       u'Ц': u'TC',
                       u'Ч': u'CH',
                       u'Ш': u'SH',
                       u'Щ': u'SCH',
                       u'Ъ': u'',
                       u'Ы': u'Y',
                       u'Ь': u'',
                       u'Э': u'EE',
                       u'Ю': u'YU',
                       u'Я': u'YA',
                       u'Ä': u'A',
                       u'Å': u'A',
                       u'Ö': u'O'}
    if direction:
        capital_letters = {v: k for k, v in capital_letters.items()}

    for k, v in capital_letters.items():
        string = string.replace(k, v)

    return string
