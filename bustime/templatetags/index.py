'''
https://stackoverflow.com/a/29664945
custom template filter,
get my_list[x] in templates
Usage:
in template:
{% load index %}

{{ my_list|index:x }}

if my_list = [['a','b','c'], ['d','e','f']],
you can use {{ my_list|index:x|index:y }} in template to get my_list[x][y]

It works fine with "for":
{{ my_list|index:forloop.counter0 }}
'''
from __future__ import absolute_import
from django import template
register = template.Library()

def index(indexable, i):
    return indexable[i]

register.filter(index)
