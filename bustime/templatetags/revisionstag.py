from django import template
from django.urls import reverse
from django.utils.safestring import mark_safe
from reversion.models import Version
from bustime.models import Bus
register = template.Library()

@register.filter()
def get_object_link(obj):
    if issubclass(obj._model, Bus):
        bus = Bus.objects.get(id=obj.object_id)
        city = bus.city
        display_text = "/{}/bus-{}/edit".format(city.slug, bus.slug)
    else:
        display_text = "{}".format(
                    reverse('admin:{}_{}_change'.format(obj._model._meta.app_label, obj._model._meta.model_name), 
                    args=(obj.object_id,)))
    if display_text:
        return mark_safe(display_text)
    return "-"

