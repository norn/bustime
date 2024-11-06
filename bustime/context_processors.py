from django.conf import settings

def settings_dev(request):
    return {'settings_DEV': settings.DEV}
