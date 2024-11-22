from django import template
from django.urls import reverse
from bustime.views import settings
import geoip2.models
import geoip2.database
register = template.Library()

@register.simple_tag()
def is_european_union(ip):
    with (geoip2.database.Reader(
        settings.PROJECT_DIR + '/addons/GeoLite2-City.mmdb')) as reader:
        try:
            country = reader.city(ip).country
        except:
            return False
        return country.is_in_european_union