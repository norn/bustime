from django import template
from django.urls import reverse
from bustime.views import settings
import geoip2.models
import geoip2.database
register = template.Library()

@register.simple_tag()
def russia_or_not(ip):
    with (geoip2.database.Reader(
        settings.PROJECT_DIR + '/addons/GeoLite2-City.mmdb')) as reader:
        try:
            country = reader.city(ip).country
            if country.iso_code == "RU":
                return True
            else:
                return False
        except:
            return False
