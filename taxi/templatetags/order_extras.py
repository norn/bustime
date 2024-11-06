"""
Use {% load order_extras %} in templates
"""
from django import template
from datetime import datetime, timedelta

register = template.Library()

# получить дату-время +munutes от присланного
@register.simple_tag
def new_order_date(now, munutes=15):
    return now + timedelta(minutes=munutes)


# получить значение dict по ключу
# usage: dict_value|get_item:dict_key
@register.filter
def get_item(dictionary, key):
    try:
        return dictionary.get(key)
    except Exception as ex:
        return str(ex)


# возвращает semantic-ui цвет для html-элементов заказа пассажира
@register.simple_tag
def order_pass_color(order, city):
    color = ''
    if order.get('trip_data').date() == city.now.date():  # сегодня
        if order.get('trip_status') in [1,2,3]:  # Поездка началась
            color = 'pink'
    elif order.get('trip_status') in [5,6]:  # Отказ водителя/пассажира
        color = 'grey'
    return color


