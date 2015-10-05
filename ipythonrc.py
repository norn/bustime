from bustime.models import *
from bustime.views import *
#from django.db import connection
#print connection.queries
b=Bus.objects.get(name=2,ttype=0, city__id=3)
c=City.objects.get(id=3)


us=UserSettings.objects.get(id=7410909)
now=datetime.datetime.now()
ut=UserTimer.objects.filter(user=us, date=now.date())[0]

#%load_ext autoreload
#%autoreload 2
#%time realtime-kml()