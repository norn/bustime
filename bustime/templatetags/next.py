from typing import Iterable
from django import template

register = template.Library()

@register.filter()
def next_item(iterable:Iterable):
    return next(iterable)

