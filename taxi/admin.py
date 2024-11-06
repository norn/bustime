from django.contrib import admin
from django.contrib.auth.models import User

from taxi.models import *

class TaxiUserAdmin(admin.ModelAdmin):
    list_display = ('user', 'name', 'phone', 'gender', 'driver_rating_cnt', 'last_join', 'gps_on')
    list_filter = ('driver', 'gender', 'gps_on')
    raw_id_fields = ('user', )

admin.site.register(TaxiUser,TaxiUserAdmin)

class CarTaxiAdmin(admin.ModelAdmin):
    list_display = ('gos_num', 'model', 'baby_seat', 'taxi_type', 'car_class', 'taxist', )
    list_filter = ('passengers', 'baby_seat', 'taxi_type', 'car_class', )
    ordering = ('gos_num', )

admin.site.register(CarTaxi, CarTaxiAdmin)


class OrderAdmin(admin.ModelAdmin):
    list_display = ('data', 'get_passenger', 'passengers', 'price', 'passenger_rating', 'passenger_note', 'taxist_note', )
    list_filter = ('city', 'data', )
    ordering = ('data', )

    def get_queryset(self, request):
        return super(OrderAdmin, self).get_queryset(request).select_related('passenger')

    def get_passenger(self, obj):
        return obj.passenger.name
    get_passenger.short_description = 'Пассажир'
    get_passenger.admin_order_field = 'order__passenger'

admin.site.register(Order, OrderAdmin)


"""
class DriverAdmin(admin.ModelAdmin):
    list_display = ('user', 'name', 'phone', 'stars',)
    list_filter = ('city',)
    ordering = ('city', )

admin.site.register(Driver, DriverAdmin)
"""