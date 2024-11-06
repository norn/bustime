# -*- coding: utf-8 -*-
from __future__ import absolute_import
from django import template
import datetime
import six

register = template.Library()

#@register.simple_tag(takes_context=True)
@register.simple_tag
def timeorama(a, b):
    """Carefully checks if time > then given, 1:20 should be later then 18:00"""
    nd = False # next day

    if type(a) in [str, six.text_type]:
        if ":" in a:
            a = a.split(":")
            a = datetime.time(int(a[0]), int(a[1]))
        else:
            a = datetime.time(int(a))

    if type(b) in [str, six.text_type]:
        if ":" in b:
            b = b.split(":")
            b = datetime.time(int(b[0]), int(b[1]))
        else:
            b = datetime.time(int(b))

    if b <= datetime.time(23, 59) and a >= datetime.time(0, 0) and a < datetime.time(4, 0):
        nd = True

    if a < b and not nd:
        #return 'orange'
        return 'grey'
    else:
        return ''
